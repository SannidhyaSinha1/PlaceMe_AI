"""Symmetric encryption for sensitive columns (Gmail OAuth tokens).

Uses Fernet (AES-128-CBC + HMAC) with a 32-byte key derived from
``TOKEN_ENCRYPTION_KEY`` (or ``SECRET_KEY`` when unset), so no extra
configuration is required. Sensitive values are encrypted at rest and
transparently decrypted on read through the :class:`EncryptedStr` SQLAlchemy
type.

Decryption tolerates legacy plaintext rows (written before encryption was
introduced) by returning them unchanged, so the migration is seamless — the
next write re-encrypts the value. If ``cryptography`` is unavailable the type
degrades to storing plaintext, consistent with the project's graceful-degradation
philosophy.
"""

from __future__ import annotations

import base64
import hashlib
import logging
from functools import lru_cache
from typing import Optional

from sqlalchemy import Text
from sqlalchemy.types import TypeDecorator

from fastapi_app.core.config import get_settings

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _fernet():
    settings = get_settings()
    try:
        from cryptography.fernet import Fernet
    except Exception:  # pragma: no cover - cryptography ships with python-jose
        logger.warning(
            "cryptography unavailable; sensitive columns will be stored as plaintext"
        )
        return None
    raw = settings.token_encryption_key or settings.secret_key
    key = base64.urlsafe_b64encode(hashlib.sha256(raw.encode()).digest())
    return Fernet(key)


def encrypt(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    fernet = _fernet()
    if fernet is None:
        return value
    return fernet.encrypt(value.encode()).decode()


def decrypt(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    fernet = _fernet()
    if fernet is None:
        return value
    try:
        return fernet.decrypt(value.encode()).decode()
    except Exception:  # noqa: BLE001 - legacy plaintext or rotated key
        return value


class EncryptedStr(TypeDecorator):
    """Text column that is transparently encrypted at rest."""

    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):  # write path
        return encrypt(value)

    def process_result_value(self, value, dialect):  # read path
        return decrypt(value)

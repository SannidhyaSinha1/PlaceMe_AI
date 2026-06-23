"""File storage: Cloudinary (free 25 GB) with a local-disk fallback.

Uploads return a URL. When Cloudinary isn't configured, bytes are written
under settings.uploads_dir and a /files/... path is returned, so resume and
cover-letter features work fully in local dev.
"""

from __future__ import annotations

import logging
import os
import secrets
from typing import Optional

from fastapi_app.core.cloudinary_client import init_cloudinary
from fastapi_app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def _token() -> str:
    """Unguessable component so stored files can't be enumerated by id."""
    return secrets.token_urlsafe(16)


def _local_save(file_bytes: bytes, folder: str, filename: str) -> str:
    target_dir = os.path.join(settings.uploads_dir, folder)
    os.makedirs(target_dir, exist_ok=True)
    path = os.path.join(target_dir, filename)
    with open(path, "wb") as fh:
        fh.write(file_bytes)
    return f"/files/{folder}/{filename}"


def delete_local(url: Optional[str]) -> None:
    """Best-effort removal of a previously stored ``/files/...`` asset.

    Confined to ``uploads_dir`` to defend against path traversal; remote
    (Cloudinary) URLs are ignored.
    """
    if not url or not url.startswith("/files/"):
        return
    rel = url[len("/files/"):]
    base = os.path.realpath(settings.uploads_dir)
    target = os.path.realpath(os.path.join(settings.uploads_dir, rel))
    if not (target == base or target.startswith(base + os.sep)):
        return
    try:
        if os.path.isfile(target):
            os.remove(target)
    except OSError as exc:  # pragma: no cover - best effort
        logger.warning("Could not delete local file %s: %s", target, exc)


def _upload(file_bytes: bytes, folder: str, public_id: str, ext: str) -> str:
    if init_cloudinary():
        try:
            import cloudinary.uploader

            result = cloudinary.uploader.upload(
                file_bytes,
                resource_type="raw",
                folder=folder,
                public_id=public_id,
                overwrite=True,
            )
            return result["secure_url"]
        except Exception as exc:  # noqa: BLE001
            logger.warning("Cloudinary upload failed (%s); saving locally", exc)
    return _local_save(file_bytes, folder, f"{public_id}.{ext}")


def upload_resume(file_bytes: bytes, user_id: int) -> str:
    return _upload(file_bytes, "resumes", f"resume_{user_id}_{_token()}", "pdf")


def upload_cover_letter(pdf_bytes: bytes, user_id: int, opp_id: int) -> str:
    return _upload(
        pdf_bytes, "cover_letters", f"cover_{user_id}_{opp_id}_{_token()}", "pdf"
    )


def upload_tailored_resume(pdf_bytes: bytes, user_id: int, opp_id: int) -> str:
    return _upload(
        pdf_bytes, "tailored_resumes", f"resume_{user_id}_{opp_id}_{_token()}", "pdf"
    )

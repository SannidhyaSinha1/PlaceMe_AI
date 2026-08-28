"""Gmail integration: OAuth 2.0 URL/exchange + auto-refresh + email fetch.

Tokens are refreshed automatically with google.auth.transport.requests.Request
(rule #6). All google-api calls are blocking, so routers/tasks should call the
fetch helpers via `run_in_executor` / Celery rather than awaiting them.
"""

from __future__ import annotations

import base64
import logging

from fastapi_app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


def message_web_link(message_id: str) -> str:
    """Deep link that opens this message in Gmail web for the signed-in account.

    `message_id` is the Gmail API message id stored on the opportunity
    (`source_email_id`). The link resolves for the mailbox that synced it.
    """
    return f"https://mail.google.com/mail/u/0/#all/{message_id}"


def _placement_query() -> str:
    sender = settings.placement_email_sender
    # Quote multi-word names so Gmail treats them as a phrase.
    if " " in sender:
        sender = f'"{sender}"'
    return f"from:{sender} newer_than:{settings.placement_email_since}"


def _client_config() -> dict:
    return {
        "web": {
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [settings.google_redirect_uri],
        }
    }


def build_auth_url(state: str) -> str:
    """Return the Google consent-screen URL for the given state token."""
    from google_auth_oauthlib.flow import Flow

    # PKCE is for public clients; we have a client_secret so disable it.
    flow = Flow.from_client_config(
        _client_config(), scopes=SCOPES, redirect_uri=settings.google_redirect_uri,
        autogenerate_code_verifier=False,
    )
    auth_url, _ = flow.authorization_url(
        access_type="offline", include_granted_scopes="true",
        prompt="consent", state=state,
    )
    return auth_url


def exchange_code(code: str, state: str | None = None) -> dict:
    """Exchange an auth code for {access_token, refresh_token}."""
    import requests as req

    data: dict = {
        "code": code,
        "client_id": settings.google_client_id,
        "client_secret": settings.google_client_secret,
        "redirect_uri": settings.google_redirect_uri,
        "grant_type": "authorization_code",
    }
    resp = req.post("https://oauth2.googleapis.com/token", data=data, timeout=10)
    if not resp.ok:
        logger.error("Google token exchange failed %s: %s", resp.status_code, resp.text)
    resp.raise_for_status()
    tokens = resp.json()
    return {
        "access_token": tokens.get("access_token"),
        "refresh_token": tokens.get("refresh_token"),
    }


def _credentials(access_token: str, refresh_token: str | None):
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials

    creds = Credentials(
        token=access_token,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
        scopes=SCOPES,
    )
    if (not creds.valid or creds.expired) and creds.refresh_token:
        try:
            creds.refresh(Request())
        except Exception as exc:  # noqa: BLE001
            logger.warning("Gmail token refresh failed: %s", exc)
    return creds


def list_placement_message_ids(
    access_token: str, refresh_token: str | None, max_results: int = 100
) -> list[str]:
    """Return matching Gmail message ids, newest first (blocking).

    This is one cheap API call. Downloading each message body is the expensive
    part, so callers list ids first, drop the ones already imported, and only
    then fetch — which keeps a sync bounded without ever hiding older emails
    behind a wall of already-imported newer ones.
    """
    from googleapiclient.discovery import build

    creds = _credentials(access_token, refresh_token)
    service = build("gmail", "v1", credentials=creds, cache_discovery=False)

    listing = (
        service.users()
        .messages()
        .list(userId="me", q=_placement_query(), maxResults=max_results)
        .execute()
    )
    return [m["id"] for m in listing.get("messages", []) if m.get("id")]


def fetch_email_by_id(access_token: str, refresh_token: str | None, message_id: str) -> dict:
    """Return a single email by Gmail message ID (blocking)."""
    from googleapiclient.discovery import build

    creds = _credentials(access_token, refresh_token)
    service = build("gmail", "v1", credentials=creds, cache_discovery=False)
    msg = service.users().messages().get(userId="me", id=message_id, format="full").execute()
    return _parse_message(msg)


def current_access_token(access_token: str, refresh_token: str | None) -> str:
    """Return a fresh access token (refreshing if needed) for persistence."""
    return _credentials(access_token, refresh_token).token


def _parse_message(msg: dict) -> dict:
    headers = {h["name"].lower(): h["value"] for h in msg.get("payload", {}).get("headers", [])}
    return {
        "gmail_message_id": msg.get("id"),
        "subject": headers.get("subject", ""),
        "sender": headers.get("from", ""),
        "received_at": headers.get("date", ""),
        "body": _extract_body(msg.get("payload", {})),
    }


def _extract_body(payload: dict) -> str:
    """Depth-first walk preferring text/plain, falling back to snippet/HTML."""
    if payload.get("mimeType", "").startswith("text/plain"):
        data = payload.get("body", {}).get("data")
        if data:
            return _decode(data)
    for part in payload.get("parts", []) or []:
        text = _extract_body(part)
        if text:
            return text
    data = payload.get("body", {}).get("data")
    return _decode(data) if data else ""


def _decode(data: str) -> str:
    try:
        return base64.urlsafe_b64decode(data.encode()).decode("utf-8", errors="ignore")
    except Exception:  # noqa: BLE001
        return ""

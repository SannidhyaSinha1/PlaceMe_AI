"""Outbound notifications via Gmail SMTP (App Password) — stdlib smtplib only."""

from __future__ import annotations

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from fastapi_app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def _send(to: str, subject: str, body: str) -> bool:
    if not settings.smtp_configured:
        logger.info("SMTP not configured; skipping email to %s (%s)", to, subject)
        return False
    msg = MIMEMultipart()
    msg["From"] = settings.gmail_address
    msg["To"] = to
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))
    try:
        with smtplib.SMTP("smtp.gmail.com", 587, timeout=20) as s:
            s.starttls()
            s.login(settings.gmail_address, settings.gmail_app_password)
            s.send_message(msg)
        return True
    except Exception as exc:  # noqa: BLE001
        logger.warning("SMTP send to %s failed: %s", to, exc)
        return False


def send_deadline_reminder(
    to: str, company: str, role: str, days_left: int, deadline: str
) -> bool:
    when = "today" if days_left == 0 else f"in {days_left} day(s)"
    subject = f"⏰ Deadline {when}: {company} — {role}"
    body = (
        f"Hi,\n\nThis is a PlaceMentor AI reminder.\n\n"
        f"Company  : {company}\nRole     : {role}\n"
        f"Deadline : {deadline}\nDays left: {days_left}\n\n"
        f"Log in to review your tailored resume and cover letter before you apply.\n\n"
        f"— PlaceMentor AI"
    )
    return _send(to, subject, body)


def send_new_opportunity(to: str, company: str, role: str, eligibility: str) -> bool:
    subject = f"🎯 New opportunity: {company} — {role}"
    body = (
        f"Hi,\n\nA new opportunity matching your inbox was detected.\n\n"
        f"Company     : {company}\nRole        : {role}\n"
        f"Eligibility : {eligibility}\n\n"
        f"Open PlaceMentor AI to view details and apply.\n\n— PlaceMentor AI"
    )
    return _send(to, subject, body)

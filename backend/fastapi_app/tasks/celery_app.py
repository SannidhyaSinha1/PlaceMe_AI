"""Celery app wired to Upstash Redis (rule #9: SSL for rediss:// brokers).

Beat schedule:
  - sync-emails       every 30 min  → Gmail sync for all connected users
  - send-reminders    every hour    → dispatch due deadline reminders
  - purge-old-emails  daily         → trim MongoDB raw_emails past 30 days
"""

from __future__ import annotations

import ssl

from celery import Celery

from fastapi_app.core.config import get_settings

settings = get_settings()
REDIS_URL = settings.upstash_redis_url

_uses_ssl = REDIS_URL.startswith("rediss://")
_ssl_opts = {"ssl_cert_reqs": ssl.CERT_NONE} if _uses_ssl else None

celery = Celery(
    "placementor",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=[
        "fastapi_app.tasks.email_sync_task",
        "fastapi_app.tasks.ai_pipeline_task",
        "fastapi_app.tasks.reminder_task",
    ],
)

celery.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    worker_max_tasks_per_child=200,
    broker_connection_retry_on_startup=True,
)

if _uses_ssl:
    celery.conf.broker_use_ssl = _ssl_opts
    celery.conf.redis_backend_use_ssl = _ssl_opts

celery.conf.beat_schedule = {
    "sync-emails-every-30min": {
        "task": "fastapi_app.tasks.email_sync_task.sync_all_users",
        "schedule": 1800.0,
    },
    "send-reminders-every-hour": {
        "task": "fastapi_app.tasks.reminder_task.dispatch_reminders",
        "schedule": 3600.0,
    },
    "purge-old-emails-daily": {
        "task": "fastapi_app.tasks.email_sync_task.purge_old_raw_emails",
        "schedule": 86400.0,
    },
}

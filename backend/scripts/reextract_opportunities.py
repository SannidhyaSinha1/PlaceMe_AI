"""One-off backfill: re-extract company / role / type for email-sourced
opportunities using the LLM, fixing rows created while the LLM was unavailable
(e.g. the "Subject 2026" rows produced by the regex fallback).

It re-fetches each email from Gmail and re-runs the LLM extractor with
``allow_heuristic=False`` — so a row is updated **only** when the model
genuinely runs. If the LLM is merely rate-limited the row is left untouched
rather than overwritten with heuristic output again.

Throttled to respect Groq's free-tier limits (~12k tokens/min): one call every
``--delay`` seconds, with exponential backoff on rate-limit errors.

Usage (from backend/, venv active):
    python scripts/reextract_opportunities.py --only-garbage            # fix the junk rows
    python scripts/reextract_opportunities.py --ids 4 --delay 3         # one row
    python scripts/reextract_opportunities.py --dry-run                 # preview, no writes
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select  # noqa: E402

from ai_agents import classifier, email_extractor  # noqa: E402
from ai_agents.llm_client import LLMUnavailable, llm_available  # noqa: E402
from fastapi_app.core.database import SessionLocal  # noqa: E402
from fastapi_app.models.sql_models import Opportunity, User  # noqa: E402
from fastapi_app.services import gmail_service, pipeline  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("reextract")

# Company names that betray the pre-LLM heuristic era.
_GARBAGE = re.compile(r"^(?:subject\b|world\b|university\b|rankings\b|re:|fwd:|unknown$)", re.I)
_GARBAGE_ROLES = {"at tech", "at the", "by the"}


def _looks_garbage(opp: Opportunity) -> bool:
    company = (opp.company_name or "").strip()
    role = (opp.role or "").strip().lower()
    return (not company) or bool(_GARBAGE.match(company)) or role in _GARBAGE_ROLES


async def _process(db, user, opp, args) -> str:
    """Return 'updated' | 'skipped' | 'unchanged'."""
    try:
        email = await asyncio.to_thread(
            gmail_service.fetch_email_by_id,
            user.gmail_access_token,
            user.gmail_refresh_token,
            opp.source_email_id,
        )
    except Exception as exc:  # noqa: BLE001
        log.warning("  #%s fetch failed: %s", opp.id, str(exc)[:80])
        return "skipped"

    subject, body = email.get("subject", ""), email.get("body", "")

    extracted = None
    for attempt in range(3):
        try:
            extracted = email_extractor.extract_from_email(subject, body, allow_heuristic=False)
            break
        except LLMUnavailable as exc:
            wait = args.delay * (attempt + 2)
            log.warning("  #%s LLM unavailable (%s); backing off %.0fs", opp.id, str(exc)[:50], wait)
            time.sleep(wait)
        except Exception as exc:  # noqa: BLE001
            log.warning("  #%s extraction error: %s", opp.id, str(exc)[:80])
            return "skipped"
    if extracted is None:
        log.warning("  #%s skipped — LLM still unavailable", opp.id)
        return "skipped"

    cls = classifier.classify(subject, body)
    data = extracted.model_dump()
    if cls.get("label"):
        data["opportunity_type"] = cls["label"]
    if not data.get("company_name") and subject:
        data["company_name"] = subject.strip()

    before, after = opp.company_name, data.get("company_name")
    log.info("  #%s  %r -> %r  [%s]", opp.id, before, after, data.get("opportunity_type"))
    if not args.dry_run:
        await pipeline.upsert_opportunity_from_extract(
            db, data, source_email_id=opp.source_email_id, source="email"
        )
    return "updated"


async def _run(args) -> None:
    async with SessionLocal() as db:
        user = (
            await db.execute(select(User).where(User.gmail_refresh_token.is_not(None)).limit(1))
        ).scalar_one_or_none()
        if user is None:
            log.error("No Gmail-connected user found; cannot re-fetch emails.")
            return

        stmt = select(Opportunity).where(Opportunity.source_email_id.is_not(None))
        if args.ids:
            stmt = stmt.where(Opportunity.id.in_([int(i) for i in args.ids.split(",")]))
        rows = (await db.execute(stmt.order_by(Opportunity.id))).scalars().all()
        if args.only_garbage:
            rows = [o for o in rows if _looks_garbage(o)]
        if args.limit:
            rows = rows[: args.limit]

        log.info(
            "LLM available: %s | rows to process: %d | delay: %ss | dry-run: %s",
            llm_available(), len(rows), args.delay, args.dry_run,
        )

        counts = {"updated": 0, "skipped": 0}
        for i, opp in enumerate(rows):
            result = await _process(db, user, opp, args)
            counts[result] += 1
            # Commit per row: short SQLite locks (safe alongside the running
            # server) and progress survives a mid-run rate-limit stop.
            if result == "updated" and not args.dry_run:
                await db.commit()
            if i < len(rows) - 1:
                time.sleep(args.delay)

        log.info("Done. updated=%d skipped=%d", counts["updated"], counts["skipped"])


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--only-garbage", action="store_true", help="only rows with junk company/role")
    p.add_argument("--ids", help="comma-separated opportunity ids to target")
    p.add_argument("--limit", type=int, default=0, help="cap number of rows (0 = all)")
    p.add_argument("--delay", type=float, default=10.0, help="seconds between LLM calls (Groq TPM)")
    p.add_argument("--dry-run", action="store_true", help="show changes without writing")
    asyncio.run(_run(p.parse_args()))


if __name__ == "__main__":
    main()

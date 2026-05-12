"""Generate and store outreach drafts. NEVER sends email.

Status values: needs_approval, approved, rejected, sent_manually, followup_due, suppressed.
"""
from __future__ import annotations

from src.crm.suppression import is_suppressed
from src.db import cursor
from src.email.template import render_cold_email
from src.utils.logger import get_logger

log = get_logger("email.drafts")

VALID_STATUSES = {
    "needs_approval", "approved", "rejected", "sent_manually",
    "followup_due", "suppressed",
}


def generate_drafts_for_new_leads(limit: int = 50) -> int:
    """Create drafts for leads that have status='new' and no draft yet."""
    created = 0
    with cursor() as cur:
        leads = cur.execute(
            """
            SELECT l.* FROM leads l
            LEFT JOIN outreach_messages o ON o.lead_id = l.lead_id
            WHERE l.status = 'new' AND o.draft_id IS NULL
              AND l.email IS NOT NULL AND l.email != ''
            ORDER BY l.lead_score DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

    for lead in leads:
        lead_d = dict(lead)
        if is_suppressed(
            email=lead_d.get("email"),
            business_name=lead_d.get("business_name"),
            website=lead_d.get("website"),
        ):
            with cursor() as cur:
                cur.execute("UPDATE leads SET status='suppressed' WHERE lead_id=?", (lead_d["lead_id"],))
            continue
        rendered = render_cold_email(lead_d)
        with cursor() as cur:
            cur.execute(
                """
                INSERT INTO outreach_messages (
                    lead_id, business_name, email, subject, email_body,
                    personalization_reason, recommended_package, status,
                    followup_1_body, followup_1_date, followup_2_body, followup_2_date
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 'needs_approval', ?, ?, ?, ?)
                """,
                (
                    lead_d["lead_id"], lead_d["business_name"], lead_d["email"],
                    rendered["subject"], rendered["body"],
                    rendered["personalization_reason"], lead_d.get("recommended_package"),
                    rendered["followup_1_body"], rendered["followup_1_date"],
                    rendered["followup_2_body"], rendered["followup_2_date"],
                ),
            )
        created += 1
    log.info("drafts created: %d", created)
    return created


def set_draft_status(draft_id: int, status: str, *, approved: bool | None = None) -> None:
    if status not in VALID_STATUSES:
        raise ValueError(f"invalid status: {status}")
    with cursor() as cur:
        cur.execute(
            "UPDATE outreach_messages SET status=?, approved_by_yagya=COALESCE(?, approved_by_yagya), "
            "updated_at=CURRENT_TIMESTAMP WHERE draft_id=?",
            (status, 1 if approved else (0 if approved is False else None), draft_id),
        )


def list_drafts(status: str | None = "needs_approval", limit: int = 200) -> list[dict]:
    q = "SELECT * FROM outreach_messages"
    args: tuple = ()
    if status:
        q += " WHERE status=?"
        args = (status,)
    q += " ORDER BY created_at DESC LIMIT ?"
    args = (*args, limit)
    with cursor() as cur:
        return [dict(r) for r in cur.execute(q, args).fetchall()]


def mark_sent_manually(draft_id: int) -> None:
    with cursor() as cur:
        cur.execute(
            "UPDATE outreach_messages SET status='sent_manually', sent_at=CURRENT_TIMESTAMP, "
            "updated_at=CURRENT_TIMESTAMP WHERE draft_id=?",
            (draft_id,),
        )
        row = cur.execute("SELECT lead_id FROM outreach_messages WHERE draft_id=?", (draft_id,)).fetchone()
        if row:
            cur.execute(
                "UPDATE leads SET status='contacted', last_contacted_at=CURRENT_TIMESTAMP WHERE lead_id=?",
                (row["lead_id"],),
            )

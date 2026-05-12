"""Suppression and manual-approval rules for outreach."""
from __future__ import annotations

from typing import Iterable

from src.agents.lead_utils import lead_domain, normalized_business
from src.utils.dedupe import norm_email

BLOCKED_LEAD_STATUSES = {
    "suppressed",
    "negative_reply",
    "unsubscribed",
    "rejected",
    "converted",
    "client",
    "closed_won",
    "do_not_contact",
}

NEGATIVE_REPLY_SENTIMENTS = {
    "negative",
    "unsubscribe",
    "unsubscribed",
    "rejected",
    "do_not_contact",
    "spam",
}


def is_followup_eligible_status(status: str | None) -> bool:
    return (status or "").strip().lower() not in BLOCKED_LEAD_STATUSES


def has_negative_reply_sentiment(sentiments: Iterable[str | None]) -> bool:
    return any((sentiment or "").strip().lower() in NEGATIVE_REPLY_SENTIMENTS for sentiment in sentiments)


def is_suppressed(conn, lead: dict[str, object]) -> bool:
    email = norm_email(str(lead.get("email") or ""))
    domain = lead_domain(lead)
    business = normalized_business(lead)
    cur = conn.cursor()
    if email:
        cur.execute("SELECT 1 FROM suppressions WHERE LOWER(email) = ? LIMIT 1", (email,))
        if cur.fetchone():
            return True
    if domain:
        cur.execute("SELECT 1 FROM suppressions WHERE LOWER(domain) = ? LIMIT 1", (domain.lower(),))
        if cur.fetchone():
            return True
    if business:
        cur.execute("SELECT business_name FROM suppressions WHERE business_name IS NOT NULL AND business_name != ''")
        for row in cur.fetchall():
            if normalized_business({"business_name": row["business_name"]}) == business:
                return True
    return False


def has_negative_reply(conn, lead_id: int) -> bool:
    cur = conn.cursor()
    cur.execute("SELECT sentiment FROM replies WHERE lead_id = ?", (lead_id,))
    return has_negative_reply_sentiment(row["sentiment"] for row in cur.fetchall())

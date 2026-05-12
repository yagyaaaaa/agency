"""Suppression / unsubscribe list. Checked before any outreach draft is generated."""
from __future__ import annotations

from src.db import cursor
from src.utils.dedupe import domain_from_email, norm_business, norm_email


def add_suppression(
    *,
    email: str | None = None,
    domain: str | None = None,
    business_name: str | None = None,
    reason: str = "manual",
) -> int:
    with cursor() as cur:
        cur.execute(
            "INSERT INTO suppressions (email, domain, business_name, reason) VALUES (?, ?, ?, ?)",
            (norm_email(email), (domain or "").lower().strip(), norm_business(business_name), reason),
        )
        return cur.lastrowid or 0


def is_suppressed(
    *,
    email: str | None = None,
    business_name: str | None = None,
    website: str | None = None,
) -> bool:
    e = norm_email(email)
    d = domain_from_email(e) if e else ""
    if not d and website:
        from src.utils.dedupe import domain_from_url
        d = domain_from_url(website)
    b = norm_business(business_name)
    with cursor() as cur:
        if e:
            r = cur.execute("SELECT 1 FROM suppressions WHERE LOWER(email)=? LIMIT 1", (e,)).fetchone()
            if r:
                return True
        if d:
            r = cur.execute("SELECT 1 FROM suppressions WHERE LOWER(domain)=? LIMIT 1", (d,)).fetchone()
            if r:
                return True
        if b:
            r = cur.execute("SELECT 1 FROM suppressions WHERE LOWER(business_name)=? LIMIT 1", (b,)).fetchone()
            if r:
                return True
    return False


def list_suppressions() -> list[dict]:
    with cursor() as cur:
        rows = cur.execute("SELECT * FROM suppressions ORDER BY created_at DESC").fetchall()
        return [dict(r) for r in rows]

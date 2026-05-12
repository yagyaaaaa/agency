"""Lead CRUD with dedupe by email, website domain, and normalized business name."""
from __future__ import annotations

from typing import Any

from src.crm.suppression import is_suppressed
from src.db import cursor
from src.utils.dedupe import (
    domain_from_email,
    domain_from_url,
    norm_business,
    norm_email,
)

LEAD_COLUMNS = [
    "business_name", "industry", "city_country", "website", "email", "phone",
    "instagram", "linkedin", "decision_maker", "source_url",
    "website_quality_score", "automation_opportunity", "personalization_hook",
    "recommended_package", "lead_score", "status", "notes",
]


class DuplicateLead(Exception):
    def __init__(self, existing_id: int, reason: str):
        super().__init__(f"Duplicate lead (existing_id={existing_id}, reason={reason})")
        self.existing_id = existing_id
        self.reason = reason


def find_duplicate(*, email: str | None, website: str | None, business_name: str | None) -> tuple[int, str] | None:
    """Return (lead_id, reason) of any existing duplicate, or None."""
    e = norm_email(email)
    edom = domain_from_email(e) if e else ""
    wdom = domain_from_url(website)
    b = norm_business(business_name)

    with cursor() as cur:
        if e:
            r = cur.execute("SELECT lead_id FROM leads WHERE LOWER(email)=? LIMIT 1", (e,)).fetchone()
            if r:
                return r["lead_id"], "email"
        domain = wdom or edom
        if domain:
            r = cur.execute(
                "SELECT lead_id FROM leads WHERE LOWER(website) LIKE ? OR LOWER(email) LIKE ? LIMIT 1",
                (f"%{domain}%", f"%@{domain}"),
            ).fetchone()
            if r:
                return r["lead_id"], "domain"
        if b:
            r = cur.execute(
                "SELECT lead_id, business_name FROM leads"
            ).fetchall()
            for row in r:
                if norm_business(row["business_name"]) == b:
                    return row["lead_id"], "business_name"
    return None


def insert_lead(data: dict[str, Any], *, skip_dedupe: bool = False) -> int:
    """Insert a lead. Raises DuplicateLead on dedupe hit. Skips suppressed entries silently (returns 0)."""
    if is_suppressed(
        email=data.get("email"),
        business_name=data.get("business_name"),
        website=data.get("website"),
    ):
        return 0

    if not skip_dedupe:
        dup = find_duplicate(
            email=data.get("email"),
            website=data.get("website"),
            business_name=data.get("business_name"),
        )
        if dup:
            raise DuplicateLead(*dup)

    row = {k: data.get(k) for k in LEAD_COLUMNS}
    if not row["business_name"]:
        raise ValueError("business_name is required")
    if row.get("email"):
        row["email"] = norm_email(row["email"])
    if not row.get("status"):
        row["status"] = "new"
    if row.get("lead_score") is None:
        row["lead_score"] = 0
    cols = ", ".join(row.keys())
    placeholders = ", ".join(["?"] * len(row))
    with cursor() as cur:
        cur.execute(f"INSERT INTO leads ({cols}) VALUES ({placeholders})", tuple(row.values()))
        return cur.lastrowid or 0


def upsert_lead(data: dict[str, Any]) -> tuple[int, str]:
    """Upsert: insert new or update existing duplicate. Returns (lead_id, 'inserted'|'updated'|'suppressed')."""
    if is_suppressed(
        email=data.get("email"),
        business_name=data.get("business_name"),
        website=data.get("website"),
    ):
        return 0, "suppressed"

    dup = find_duplicate(
        email=data.get("email"),
        website=data.get("website"),
        business_name=data.get("business_name"),
    )
    if dup:
        lead_id, _reason = dup
        update_lead(lead_id, data)
        return lead_id, "updated"

    try:
        new_id = insert_lead(data, skip_dedupe=True)
    except Exception:
        raise
    return new_id, "inserted"


def update_lead(lead_id: int, data: dict[str, Any]) -> None:
    fields = {k: v for k, v in data.items() if k in LEAD_COLUMNS and v not in (None, "")}
    if not fields:
        return
    if "email" in fields:
        fields["email"] = norm_email(fields["email"])
    set_clause = ", ".join(f"{k}=?" for k in fields)
    with cursor() as cur:
        cur.execute(
            f"UPDATE leads SET {set_clause}, updated_at=CURRENT_TIMESTAMP WHERE lead_id=?",
            (*fields.values(), lead_id),
        )


def get_lead(lead_id: int) -> dict | None:
    with cursor() as cur:
        r = cur.execute("SELECT * FROM leads WHERE lead_id=?", (lead_id,)).fetchone()
        return dict(r) if r else None


def list_leads(*, status: str | None = None, limit: int = 200) -> list[dict]:
    q = "SELECT * FROM leads"
    args: tuple = ()
    if status:
        q += " WHERE status=?"
        args = (status,)
    q += " ORDER BY lead_score DESC, created_at DESC LIMIT ?"
    args = (*args, limit)
    with cursor() as cur:
        return [dict(r) for r in cur.execute(q, args).fetchall()]


def top_leads(limit: int = 10) -> list[dict]:
    with cursor() as cur:
        return [
            dict(r) for r in cur.execute(
                "SELECT * FROM leads WHERE status NOT IN ('rejected','closed','suppressed') "
                "ORDER BY lead_score DESC, created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        ]


def set_status(lead_id: int, status: str, note: str | None = None) -> None:
    with cursor() as cur:
        if note:
            cur.execute(
                "UPDATE leads SET status=?, notes=COALESCE(notes||char(10),'')||?, updated_at=CURRENT_TIMESTAMP WHERE lead_id=?",
                (status, note, lead_id),
            )
        else:
            cur.execute(
                "UPDATE leads SET status=?, updated_at=CURRENT_TIMESTAMP WHERE lead_id=?",
                (status, lead_id),
            )


def count_by_status() -> dict[str, int]:
    with cursor() as cur:
        rows = cur.execute(
            "SELECT status, COUNT(*) as n FROM leads GROUP BY status"
        ).fetchall()
        return {r["status"] or "unknown": r["n"] for r in rows}

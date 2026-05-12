"""Client / project records — created when a lead converts."""
from __future__ import annotations

from typing import Any

from src.db import cursor

CLIENT_COLUMNS = ["lead_id", "business_name", "primary_contact", "email", "phone",
                  "package", "add_ons", "status", "notes"]


def create_client(data: dict[str, Any]) -> int:
    row = {k: data.get(k) for k in CLIENT_COLUMNS}
    if not row["business_name"]:
        raise ValueError("business_name required")
    cols = ", ".join(row.keys())
    ph = ", ".join(["?"] * len(row))
    with cursor() as cur:
        cur.execute(f"INSERT INTO clients ({cols}) VALUES ({ph})", tuple(row.values()))
        return cur.lastrowid or 0


def list_clients() -> list[dict]:
    with cursor() as cur:
        return [dict(r) for r in cur.execute("SELECT * FROM clients ORDER BY onboarded_at DESC").fetchall()]


def create_project(client_id: int, name: str, package: str, start_date: str | None = None) -> int:
    with cursor() as cur:
        cur.execute(
            "INSERT INTO projects (client_id, name, package, start_date) VALUES (?, ?, ?, ?)",
            (client_id, name, package, start_date),
        )
        return cur.lastrowid or 0

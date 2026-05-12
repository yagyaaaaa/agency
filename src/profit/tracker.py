"""Profit tracker — revenue, expenses, commissions, net profit estimates."""
from __future__ import annotations

from datetime import date
from typing import Any

from src.db import cursor


def record_revenue(data: dict[str, Any]) -> int:
    fields = ["client", "package", "add_ons", "amount_booked", "amount_collected",
              "payment_method", "payment_status", "commission_due",
              "net_profit_estimate", "notes"]
    row = {k: data.get(k) for k in fields}
    if row["net_profit_estimate"] in (None, 0, 0.0) and row["amount_collected"] is not None:
        booked = float(row.get("amount_booked") or 0)
        collected = float(row.get("amount_collected") or 0)
        commission = float(row.get("commission_due") or 0)
        # rough estimate: collected - commission - 5% payment fee buffer
        row["net_profit_estimate"] = round(collected - commission - 0.05 * collected, 2)
        if not row.get("amount_booked"):
            row["amount_booked"] = collected
        _ = booked  # silence
    cols = ", ".join(row.keys())
    ph = ", ".join(["?"] * len(row))
    with cursor() as cur:
        cur.execute(f"INSERT INTO revenue ({cols}) VALUES ({ph})", tuple(row.values()))
        return cur.lastrowid or 0


def record_expense(data: dict[str, Any]) -> int:
    fields = ["category", "vendor", "amount", "payment_method", "recurring", "notes"]
    row = {k: data.get(k) for k in fields}
    cols = ", ".join(row.keys())
    ph = ", ".join(["?"] * len(row))
    with cursor() as cur:
        cur.execute(f"INSERT INTO expenses ({cols}) VALUES ({ph})", tuple(row.values()))
        return cur.lastrowid or 0


def record_commission(payee: str, transaction_id: int | None, amount: float, notes: str | None = None) -> int:
    with cursor() as cur:
        cur.execute(
            "INSERT INTO commissions (payee, transaction_id, amount, status, notes) VALUES (?, ?, ?, 'pending', ?)",
            (payee, transaction_id, amount, notes),
        )
        return cur.lastrowid or 0


def compute_summary(month: str | None = None) -> dict[str, float]:
    """Return a flat dict suitable for Excel/Telegram. month: 'YYYY-MM' filter (optional)."""
    where = ""
    args: tuple = ()
    if month:
        where = " WHERE strftime('%Y-%m', created_at) = ?"
        args = (month,)
    with cursor() as cur:
        r = cur.execute(
            f"SELECT COALESCE(SUM(amount_booked),0) booked, COALESCE(SUM(amount_collected),0) collected, "
            f"COALESCE(SUM(commission_due),0) commissions, COALESCE(SUM(net_profit_estimate),0) net "
            f"FROM revenue{where}",
            args,
        ).fetchone()
        rev = dict(r)
        r = cur.execute(
            f"SELECT COALESCE(SUM(amount),0) total FROM expenses{where}",
            args,
        ).fetchone()
        exp_total = float(r["total"])
        r = cur.execute(
            f"SELECT COALESCE(SUM(amount_booked - amount_collected),0) pending FROM revenue{where}",
            args,
        ).fetchone()
        pending = float(r["pending"])
        r = cur.execute(
            "SELECT payment_method, COALESCE(SUM(amount_collected),0) total FROM revenue "
            f"{where} GROUP BY payment_method",
            args,
        ).fetchall()
        by_method = {row["payment_method"] or "unknown": float(row["total"]) for row in r}

    booked = float(rev["booked"])
    collected = float(rev["collected"])
    commissions = float(rev["commissions"])
    net = float(rev["net"]) - exp_total

    return {
        "scope": month or "all_time",
        "revenue_booked": round(booked, 2),
        "cash_collected": round(collected, 2),
        "pending_invoices": round(pending, 2),
        "commissions_due": round(commissions, 2),
        "expenses_total": round(exp_total, 2),
        "net_profit_estimate": round(net, 2),
        "upi_collected": round(by_method.get("upi", 0.0), 2),
        "cash_collected_payment": round(by_method.get("cash", 0.0), 2),
        "cheque_collected": round(by_method.get("cheque", 0.0), 2),
        "card_collected": round(by_method.get("card", 0.0), 2),
    }


def list_recent_revenue(limit: int = 20) -> list[dict]:
    with cursor() as cur:
        return [dict(r) for r in cur.execute(
            "SELECT * FROM revenue ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()]


def list_recent_expenses(limit: int = 20) -> list[dict]:
    with cursor() as cur:
        return [dict(r) for r in cur.execute(
            "SELECT * FROM expenses ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()]

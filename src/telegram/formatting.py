"""Pure formatters for Telegram messages. Kept separate so they can be unit-tested."""
from __future__ import annotations


def fmt_daily_brief(*, day: str, lead_counts: dict[str, int], top_leads: list[dict],
                    drafts_pending: int, followups_due: int, profit: dict) -> str:
    lines = [
        f"*QuantumReach Daily Brief — {day}*",
        "",
        "*Leads*",
    ]
    if lead_counts:
        for k, v in sorted(lead_counts.items(), key=lambda x: -x[1]):
            lines.append(f"  • {k}: {v}")
    else:
        lines.append("  • (none yet)")

    lines += [
        "",
        f"*Drafts needing approval:* {drafts_pending}",
        f"*Follow-ups due today:* {followups_due}",
        "",
        "*Top 5 leads*",
    ]
    if top_leads:
        for l in top_leads[:5]:
            lines.append(
                f"  • [{l.get('lead_score', 0)}] {l.get('business_name')} — "
                f"{l.get('industry') or ''} / {l.get('city_country') or ''}"
            )
    else:
        lines.append("  • (none yet)")

    lines += [
        "",
        "*Profit (all-time)*",
        f"  • Booked: ₹{profit.get('revenue_booked', 0):,.0f}",
        f"  • Collected: ₹{profit.get('cash_collected', 0):,.0f}",
        f"  • Pending: ₹{profit.get('pending_invoices', 0):,.0f}",
        f"  • Net (est): ₹{profit.get('net_profit_estimate', 0):,.0f}",
        "",
        "_Reply with /help for commands._",
    ]
    return "\n".join(lines)


def fmt_status(counts: dict[str, int], drafts_pending: int, followups_due: int) -> str:
    parts = [f"{k}={v}" for k, v in sorted(counts.items())]
    return (
        "Status:\n"
        f"  leads → {', '.join(parts) if parts else 'none'}\n"
        f"  drafts pending → {drafts_pending}\n"
        f"  followups due → {followups_due}"
    )


def fmt_hot_leads(leads: list[dict]) -> str:
    if not leads:
        return "No hot leads yet. Try /leads or import via scripts/import_leads.sh."
    lines = ["*Hot leads*"]
    for l in leads:
        lines.append(
            f"• [{l.get('lead_score', 0)}] *{l.get('business_name')}* — "
            f"{l.get('industry') or '-'} / {l.get('city_country') or '-'}  "
            f"→ _{l.get('recommended_package') or 'pro'}_"
        )
    return "\n".join(lines)


def fmt_profit(summary: dict) -> str:
    return (
        f"*Profit ({summary.get('scope', 'all_time')})*\n"
        f"  Booked: ₹{summary.get('revenue_booked', 0):,.0f}\n"
        f"  Collected: ₹{summary.get('cash_collected', 0):,.0f}\n"
        f"  Pending: ₹{summary.get('pending_invoices', 0):,.0f}\n"
        f"  Commissions: ₹{summary.get('commissions_due', 0):,.0f}\n"
        f"  Expenses: ₹{summary.get('expenses_total', 0):,.0f}\n"
        f"  *Net (est): ₹{summary.get('net_profit_estimate', 0):,.0f}*"
    )


def fmt_help() -> str:
    return (
        "*Commands*\n"
        "/status — counts + pending items\n"
        "/today — today's brief\n"
        "/leads — list leads\n"
        "/hot — top leads by score\n"
        "/drafts — list drafts needing approval\n"
        "/approve_today — bulk-approve all drafts (use with care)\n"
        "/reject_lead <id> — reject a lead\n"
        "/pipeline — pipeline counts by stage\n"
        "/profit — profit summary\n"
        "/content — recent content assets\n"
        "/tools — tool-research list\n"
        "/proposal — proposal usage hint\n"
        "/help — this list\n"
        "\nUpload an *edited* Excel file (leads/drafts/followups) and I'll parse it."
    )

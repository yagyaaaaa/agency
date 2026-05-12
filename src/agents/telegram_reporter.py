"""Telegram formatting and safe dispatch."""
from __future__ import annotations

import re
from pathlib import Path

from src.agents.integrations import send_telegram_message

SECRET_RE = re.compile(r"(?i)(api[_-]?key|token|secret|password)\s*[:=]\s*\S+")


def redact_secrets(text: str) -> str:
    return SECRET_RE.sub(r"\1=[REDACTED]", text)


def format_daily_brief(metrics: dict[str, object], profit: dict[str, float], files: list[str | Path]) -> str:
    file_lines = [f"{idx}. {Path(path).name}" for idx, path in enumerate(files, start=1)]
    if not file_lines:
        file_lines = ["No files generated yet."]
    brief = f"""QuantumReach Daily Brief

Leads researched: {metrics.get('leads_researched', 0)}
Best leads: {metrics.get('best_leads', 0)}
Cold emails drafted: {metrics.get('cold_emails_drafted', 0)}
Follow-ups due: {metrics.get('followups_due', 0)}
Hot prospects: {metrics.get('hot_prospects', 0)}
Proposals pending: {metrics.get('proposals_pending', 0)}
Content ready: {metrics.get('content_ready', 'no')}

Profit:
- Collected: INR {profit.get('collected', 0):.0f}
- Pending: INR {profit.get('pending', 0):.0f}
- Expenses: INR {profit.get('expenses', 0):.0f}
- Net: INR {profit.get('net', 0):.0f}

Files:
{chr(10).join(file_lines)}

Your action:
Approve/reject today's email drafts."""
    return redact_secrets(brief)


class TelegramReporterAgent:
    agent_name = "telegram_reporter_agent"

    def send_daily_brief(
        self,
        metrics: dict[str, object],
        profit: dict[str, float],
        files: list[str | Path],
        dry_run: bool = False,
    ) -> str:
        brief = format_daily_brief(metrics, profit, files)
        send_telegram_message(brief, files=files, dry_run=dry_run)
        return brief

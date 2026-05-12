"""Follow-up due detection and draft export."""
from __future__ import annotations

from datetime import date, datetime, timedelta

from src import db
from src.agents.base import AgentResult, BaseAgent
from src.agents.integrations import excel_output, export_rows_to_excel
from src.agents.outreach_policy import has_negative_reply, is_followup_eligible_status, is_suppressed


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
    except ValueError:
        try:
            return date.fromisoformat(value[:10])
        except ValueError:
            return None


def _followup_due(sent_at: str | None, today: date, days: int) -> bool:
    sent_date = _parse_date(sent_at)
    return bool(sent_date and today >= sent_date + timedelta(days=days))


def is_due_followup_allowed(lead: dict[str, object], suppressed: bool = False, negative_reply: bool = False) -> bool:
    if suppressed or negative_reply:
        return False
    return is_followup_eligible_status(str(lead.get("status") or ""))


class FollowupAgent(BaseAgent):
    agent_name = "followup_agent"

    def _already_logged(self, conn, lead_id: int, followup_type: str, due_date: str) -> bool:
        cur = conn.cursor()
        cur.execute(
            "SELECT 1 FROM followups WHERE lead_id = ? AND type = ? AND due_date = ? LIMIT 1",
            (lead_id, followup_type, due_date),
        )
        return bool(cur.fetchone())

    def _due_rows(self, conn, today: date) -> list[dict[str, object]]:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT om.*, l.status AS lead_status, l.city_country, l.industry, l.website, l.instagram, l.linkedin,
                   l.decision_maker, l.source_url, l.automation_opportunity, l.personalization_hook, l.notes
            FROM outreach_messages om
            JOIN leads l ON l.lead_id = om.lead_id
            WHERE om.sent_at IS NOT NULL
              AND om.sent_at != ''
            ORDER BY om.sent_at ASC
            """
        )
        due: list[dict[str, object]] = []
        for row in cur.fetchall():
            item = dict(row)
            lead = {
                "lead_id": item["lead_id"],
                "business_name": item["business_name"],
                "email": item["email"],
                "status": item["lead_status"],
            }
            if not is_due_followup_allowed(lead, is_suppressed(conn, lead), has_negative_reply(conn, int(item["lead_id"]))):
                continue

            if _followup_due(item.get("sent_at"), today, 3):
                due_date = item.get("followup_1_date") or today.isoformat()
                if not self._already_logged(conn, int(item["lead_id"]), "followup_1", due_date):
                    due.append(
                        {
                            "lead_id": item["lead_id"],
                            "business_name": item["business_name"],
                            "email": item["email"],
                            "type": "followup_1",
                            "due_date": due_date,
                            "subject": f"Re: {item['subject']}",
                            "body": item.get("followup_1_body") or "",
                        }
                    )

            if _followup_due(item.get("sent_at"), today, 7):
                due_date = item.get("followup_2_date") or today.isoformat()
                if not self._already_logged(conn, int(item["lead_id"]), "followup_2", due_date):
                    due.append(
                        {
                            "lead_id": item["lead_id"],
                            "business_name": item["business_name"],
                            "email": item["email"],
                            "type": "followup_2",
                            "due_date": due_date,
                            "subject": f"Re: {item['subject']}",
                            "body": item.get("followup_2_body") or "",
                        }
                    )
        return due

    def run(self, dry_run: bool = False, day: str | None = None) -> AgentResult:
        today = date.fromisoformat(day) if day else date.today()
        with self.run_context(dry_run=dry_run):
            with db.connect() as conn:
                rows = self._due_rows(conn, today)
                if not dry_run:
                    for row in rows:
                        conn.execute(
                            "INSERT INTO followups (lead_id, due_date, type, notes, done) VALUES (?, ?, ?, ?, 0)",
                            (row["lead_id"], row["due_date"], row["type"], row["subject"]),
                        )
                    conn.commit()
            outputs: dict[str, str] = {}
            if not dry_run:
                outputs["followups_excel"] = str(export_rows_to_excel(rows, excel_output("followups_due.xlsx"), "Followups"))
            return AgentResult(
                self.agent_name,
                "ok",
                "follow-up drafts exported" if not dry_run else "dry-run follow-up check complete",
                count=len(rows),
                outputs=outputs,
                data={"followups": rows},
            )


def is_followup_eligible_status(status: str | None) -> bool:
    from src.agents.outreach_policy import is_followup_eligible_status as _eligible

    return _eligible(status)

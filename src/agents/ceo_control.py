"""CEO control agent that compiles founder-ready daily summaries."""
from __future__ import annotations

from datetime import date

from src import db
from src.agents.base import AgentResult, BaseAgent
from src.agents.profit import summarize_profit
from src.agents.telegram_reporter import TelegramReporterAgent


class CEOControlAgent(BaseAgent):
    agent_name = "ceo_control_agent"

    def collect_metrics(self, day: str) -> dict[str, object]:
        with db.connect() as conn:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) AS c FROM leads WHERE DATE(created_at) = DATE(?)", (day,))
            leads_researched = int(cur.fetchone()["c"])
            cur.execute("SELECT COUNT(*) AS c FROM leads WHERE lead_score >= 8")
            best_leads = int(cur.fetchone()["c"])
            cur.execute("SELECT COUNT(*) AS c FROM outreach_messages WHERE DATE(created_at) = DATE(?)", (day,))
            cold_emails_drafted = int(cur.fetchone()["c"])
            cur.execute("SELECT COUNT(*) AS c FROM followups WHERE done = 0 AND DATE(due_date) <= DATE(?)", (day,))
            followups_due = int(cur.fetchone()["c"])
            cur.execute("SELECT COUNT(*) AS c FROM leads WHERE lead_score >= 10 AND LOWER(COALESCE(status, 'new')) NOT IN ('rejected', 'converted', 'client')")
            hot_prospects = int(cur.fetchone()["c"])
            cur.execute("SELECT COUNT(*) AS c FROM proposals WHERE DATE(created_at) = DATE(?)", (day,))
            proposals_pending = int(cur.fetchone()["c"])
            cur.execute("SELECT COUNT(*) AS c FROM content_assets WHERE kind = 'daily_content_pack' AND DATE(created_at) = DATE(?)", (day,))
            content_ready = "yes" if int(cur.fetchone()["c"]) else "no"
        return {
            "leads_researched": leads_researched,
            "best_leads": best_leads,
            "cold_emails_drafted": cold_emails_drafted,
            "followups_due": followups_due,
            "hot_prospects": hot_prospects,
            "proposals_pending": proposals_pending,
            "content_ready": content_ready,
        }

    def run(self, dry_run: bool = False, day: str | None = None, files: list[str] | None = None) -> AgentResult:
        day = day or date.today().isoformat()
        files = files or []
        with self.run_context(dry_run=dry_run):
            metrics = self.collect_metrics(day)
            profit = summarize_profit()
            brief = TelegramReporterAgent().send_daily_brief(metrics, profit, files, dry_run=dry_run)
            if not dry_run:
                with db.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO daily_reports (report_date, summary, excel_paths)
                        VALUES (?, ?, ?)
                        ON CONFLICT(report_date) DO UPDATE SET
                            summary = excluded.summary,
                            excel_paths = excluded.excel_paths
                        """,
                        (day, brief, "\n".join(files)),
                    )
            return AgentResult(
                self.agent_name,
                "ok",
                "founder-ready Telegram digest prepared",
                count=1,
                outputs={"telegram_brief": brief},
                data={"metrics": metrics, "profit": profit},
            )

"""Profit summary agent."""
from __future__ import annotations

from datetime import date

from src import db
from src.agents.base import AgentResult, BaseAgent
from src.agents.integrations import excel_output, export_rows_to_excel
from src.config import data_path


def summarize_profit() -> dict[str, float]:
    with db.connect() as conn:
        cur = conn.cursor()
        cur.execute("SELECT COALESCE(SUM(amount_collected), 0) AS total FROM revenue")
        collected = float(cur.fetchone()["total"])
        cur.execute("SELECT COALESCE(SUM(MAX(amount_booked - amount_collected, 0)), 0) AS total FROM revenue")
        pending = float(cur.fetchone()["total"])
        cur.execute("SELECT COALESCE(SUM(amount), 0) AS total FROM expenses")
        expenses = float(cur.fetchone()["total"])
        cur.execute("SELECT COALESCE(SUM(amount), 0) AS total FROM commissions WHERE LOWER(COALESCE(status, 'pending')) != 'paid'")
        commissions_due = float(cur.fetchone()["total"])
    net = collected - expenses - commissions_due
    return {
        "collected": collected,
        "pending": pending,
        "expenses": expenses,
        "commissions_due": commissions_due,
        "net": net,
    }


class ProfitAgent(BaseAgent):
    agent_name = "profit_agent"

    def run(self, dry_run: bool = False, day: str | None = None) -> AgentResult:
        day = day or date.today().isoformat()
        with self.run_context(dry_run=dry_run):
            summary = summarize_profit()
            rows = [summary]
            outputs: dict[str, str] = {}
            if not dry_run:
                excel = export_rows_to_excel(rows, excel_output("profit_report.xlsx"), "Profit")
                path = data_path("profit", f"profit_report_{day}.md")
                path.write_text(
                    "\n".join(
                        [
                            f"# Profit Report - {day}",
                            "",
                            f"- Collected: INR {summary['collected']:.0f}",
                            f"- Pending: INR {summary['pending']:.0f}",
                            f"- Expenses: INR {summary['expenses']:.0f}",
                            f"- Commissions due: INR {summary['commissions_due']:.0f}",
                            f"- Net: INR {summary['net']:.0f}",
                            "",
                        ]
                    ),
                    encoding="utf-8",
                )
                outputs = {"profit_excel": str(excel), "profit_report": str(path)}
            return AgentResult(
                self.agent_name,
                "ok",
                "profit summary generated" if not dry_run else "dry-run profit summary generated",
                count=1,
                outputs=outputs,
                data={"profit": summary},
            )

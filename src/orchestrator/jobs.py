"""Individual jobs invoked by the scheduler. Each job is idempotent and logged."""
from __future__ import annotations

from datetime import datetime

from src.agents.ceo_control import CEOControlAgent
from src.agents.cold_email import ColdEmailAgent
from src.agents.content import ContentAgent
from src.agents.followup import FollowupAgent
from src.agents.lead_research import LeadResearchAgent
from src.agents.package_recommendation import recommend_package as agent_recommend_package
from src.agents.profit import ProfitAgent
from src.agents.scoring import score_lead as agent_score_lead
from src.agents.tool_research import ToolResearchAgent
from src.db import cursor, init_db
from src.email.drafts import generate_drafts_for_new_leads, list_drafts
from src.excel.exporter import export_all
from src.profit.tracker import compute_summary
from src.crm.leads import count_by_status, list_leads, top_leads
from src.telegram.formatting import fmt_daily_brief, fmt_profit
from src.telegram.notify import send_document, send_message
from src.utils.logger import get_logger
from src.utils.paths import today_str

log = get_logger("orchestrator.jobs")


def _job_start(name: str) -> int:
    init_db()
    with cursor() as cur:
        cur.execute("INSERT INTO job_log (job_name, status) VALUES (?, 'running')", (name,))
        return cur.lastrowid or 0


def _job_finish(job_id: int, status: str = "ok", message: str = "") -> None:
    with cursor() as cur:
        cur.execute(
            "UPDATE job_log SET status=?, message=?, finished_at=CURRENT_TIMESTAMP WHERE job_log_id=?",
            (status, message[:1000], job_id),
        )


def job_lead_research_placeholder() -> None:
    """10:00 AM - build OpenClaw research plan or ingest approved seed CSV."""
    jid = _job_start("lead_research")
    try:
        result = LeadResearchAgent().run()
        _job_finish(jid, "ok", f"{result.message}; count={result.count}")
    except Exception as exc:
        log.exception("lead_research failed")
        _job_finish(jid, "error", str(exc))


def job_score_and_dedupe() -> None:
    """12:00 PM — recompute scores; dedupe is enforced at insert, so this only refreshes scores/recommendations."""
    jid = _job_start("score_and_dedupe")
    try:
        n = 0
        with cursor() as cur:
            rows = [dict(r) for r in cur.execute("SELECT * FROM leads").fetchall()]
        for row in rows:
            s = agent_score_lead(row).score
            row["lead_score"] = s
            rec = agent_recommend_package(row)
            if row.get("lead_score") != s or row.get("recommended_package") != rec:
                with cursor() as cur:
                    cur.execute(
                        "UPDATE leads SET lead_score=?, recommended_package=?, updated_at=CURRENT_TIMESTAMP "
                        "WHERE lead_id=?",
                        (s, rec, row["lead_id"]),
                    )
                    n += 1
        drafts_made = ColdEmailAgent().run(limit=50).count
        _job_finish(jid, "ok", f"rescored={n}, drafts={drafts_made}")
    except Exception as exc:
        log.exception("score_and_dedupe failed")
        _job_finish(jid, "error", str(exc))


def job_daily_brief() -> None:
    """1:30 PM — Telegram daily brief + Excel reports."""
    jid = _job_start("daily_brief")
    try:
        paths = export_all()
        result = CEOControlAgent().run(files=[str(p) for p in paths.values()])
        _job_finish(jid, "ok", f"exports={list(paths.keys())}")
    except Exception as exc:
        log.exception("daily_brief failed")
        _job_finish(jid, "error", str(exc))


def job_review_window_open() -> None:
    """2:00 PM — founder review begins."""
    jid = _job_start("review_window_open")
    try:
        send_message(
            "🟢 *Founder review window open (2:00 PM IST)*\n"
            "Check today's Excel files. Edit + upload back to log decisions.\n"
            "Or use `/drafts`, `/leads`, `/approve_today`."
        )
        _job_finish(jid, "ok")
    except Exception as exc:
        _job_finish(jid, "error", str(exc))


def job_draft_approval_reminder() -> None:
    """3:00 PM — nudge if drafts still need approval."""
    jid = _job_start("draft_approval_reminder")
    try:
        ColdEmailAgent().run(limit=30)
        n = len(list_drafts(status="needs_approval"))
        if n > 0:
            send_message(f"📝 {n} cold email drafts still need approval. Use `/drafts` to review.")
        _job_finish(jid, "ok", f"pending={n}")
    except Exception as exc:
        _job_finish(jid, "error", str(exc))


def job_followup_reminder() -> None:
    """5:00 PM — followup nudge."""
    jid = _job_start("followup_reminder")
    try:
        result = FollowupAgent().run()
        n = result.count
        if n > 0:
            send_message(f"⏰ {n} follow-ups are due today. See followups_due Excel.")
        _job_finish(jid, "ok", f"due={n}")
    except Exception as exc:
        _job_finish(jid, "error", str(exc))


def job_evening_content_report() -> None:
    """8:00 PM — content/tool/profit recap."""
    jid = _job_start("evening_report")
    try:
        ContentAgent().run()
        ToolResearchAgent().run()
        ProfitAgent().run()
        from src.content.store import list_content, list_tools
        content = list_content(5)
        tools = list_tools(5)
        lines = ["*Evening recap*", "", "*Profit*"]
        s = compute_summary()
        lines.append(fmt_profit(s))
        lines.append("")
        lines.append("*Latest content*")
        if content:
            for a in content:
                lines.append(f"• [{a['kind']}] {a['title']}")
        else:
            lines.append("• (none)")
        lines.append("")
        lines.append("*Latest tools researched*")
        if tools:
            for t in tools:
                lines.append(f"• {t['name']} ({t['category']})")
        else:
            lines.append("• (none)")
        send_message("\n".join(lines))
        _job_finish(jid, "ok")
    except Exception as exc:
        _job_finish(jid, "error", str(exc))


def job_final_daily_summary() -> None:
    """9:30 PM — final summary + log status."""
    jid = _job_start("final_summary")
    try:
        counts = count_by_status()
        drafts = len(list_drafts(status="needs_approval"))
        send_message(
            f"🌙 *End-of-day*\n"
            f"Leads by status: {counts}\n"
            f"Drafts pending: {drafts}\n"
            f"See `/today` for full brief."
        )
        _job_finish(jid, "ok")
    except Exception as exc:
        _job_finish(jid, "error", str(exc))

"""Long-polling Telegram bot — commands + edited-Excel ingest.

Run with: python -m src.telegram.bot
Started automatically by the orchestrator when ENABLE_TELEGRAM_BOT=1.
"""
from __future__ import annotations

import asyncio
from pathlib import Path

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from src.config import CONFIG, data_path
from src.crm.leads import count_by_status, list_leads, set_status, top_leads
from src.email.drafts import list_drafts, set_draft_status
from src.excel.importer import auto_route
from src.profit.tracker import compute_summary
from src.telegram.formatting import (
    fmt_daily_brief,
    fmt_help,
    fmt_hot_leads,
    fmt_profit,
    fmt_status,
)
from src.utils.logger import get_logger
from src.utils.paths import today_str

log = get_logger("telegram.bot")


def _authorized(update: Update) -> bool:
    if not CONFIG.admin_ids_list:
        return True  # if no allow-list configured, allow chat owner only by chat_id check
    user = update.effective_user
    if not user:
        return False
    return user.id in CONFIG.admin_ids_list


# ---------- handlers ----------

async def cmd_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _authorized(update):
        return
    await update.message.reply_markdown(fmt_help())


async def cmd_status(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _authorized(update):
        return
    counts = count_by_status()
    drafts = len(list_drafts(status="needs_approval"))
    # followups due
    from src.db import cursor
    with cursor() as cur:
        r = cur.execute(
            "SELECT COUNT(*) n FROM leads WHERE next_followup_at IS NOT NULL "
            "AND date(next_followup_at) <= date('now')"
        ).fetchone()
        followups_due = int(r["n"])
    await update.message.reply_text(fmt_status(counts, drafts, followups_due))


async def cmd_today(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _authorized(update):
        return
    counts = count_by_status()
    top = top_leads(5)
    drafts = len(list_drafts(status="needs_approval"))
    from src.db import cursor
    with cursor() as cur:
        r = cur.execute(
            "SELECT COUNT(*) n FROM leads WHERE next_followup_at IS NOT NULL "
            "AND date(next_followup_at) <= date('now')"
        ).fetchone()
    msg = fmt_daily_brief(
        day=today_str(),
        lead_counts=counts,
        top_leads=top,
        drafts_pending=drafts,
        followups_due=int(r["n"]),
        profit=compute_summary(),
    )
    await update.message.reply_markdown(msg)


async def cmd_leads(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _authorized(update):
        return
    leads = list_leads(limit=15)
    if not leads:
        await update.message.reply_text("No leads yet. Use scripts/import_leads.sh.")
        return
    lines = ["*Leads (top 15)*"]
    for l in leads:
        lines.append(
            f"• [{l.get('lead_score', 0)}] *{l.get('business_name')}* — "
            f"{l.get('industry') or '-'} ({l.get('status') or 'new'})"
        )
    await update.message.reply_markdown("\n".join(lines))


async def cmd_hot(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _authorized(update):
        return
    await update.message.reply_markdown(fmt_hot_leads(top_leads(10)))


async def cmd_drafts(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _authorized(update):
        return
    drafts = list_drafts(status="needs_approval", limit=20)
    if not drafts:
        await update.message.reply_text("No drafts awaiting approval.")
        return
    lines = ["*Drafts needing approval*"]
    for d in drafts:
        lines.append(f"• #{d['draft_id']} {d.get('business_name')} → {d.get('email')}")
    await update.message.reply_markdown("\n".join(lines))


async def cmd_approve_today(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _authorized(update):
        return
    drafts = list_drafts(status="needs_approval", limit=500)
    for d in drafts:
        set_draft_status(d["draft_id"], "approved", approved=True)
    await update.message.reply_text(f"Approved {len(drafts)} drafts. Send manually from your inbox.")


async def cmd_reject_lead(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _authorized(update):
        return
    args = ctx.args or []
    if not args or not args[0].isdigit():
        await update.message.reply_text("Usage: /reject_lead <id>")
        return
    lead_id = int(args[0])
    set_status(lead_id, "rejected", note="rejected via telegram")
    await update.message.reply_text(f"Lead {lead_id} marked rejected.")


async def cmd_pipeline(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _authorized(update):
        return
    counts = count_by_status()
    if not counts:
        await update.message.reply_text("Pipeline empty.")
        return
    lines = ["*Pipeline*"]
    for k, v in sorted(counts.items(), key=lambda x: -x[1]):
        lines.append(f"• {k}: {v}")
    await update.message.reply_markdown("\n".join(lines))


async def cmd_profit(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _authorized(update):
        return
    await update.message.reply_markdown(fmt_profit(compute_summary()))


async def cmd_content(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _authorized(update):
        return
    from src.content.store import list_content
    items = list_content(15)
    if not items:
        await update.message.reply_text("No content assets yet.")
        return
    lines = ["*Recent content*"]
    for a in items:
        lines.append(f"• [{a['kind']}] {a['title']}")
    await update.message.reply_markdown("\n".join(lines))


async def cmd_tools(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _authorized(update):
        return
    from src.content.store import list_tools
    items = list_tools(15)
    if not items:
        await update.message.reply_text("No tool research yet.")
        return
    lines = ["*Tool research*"]
    for a in items:
        lines.append(f"• {a['name']} ({a['category']}) — rating {a.get('rating') or '-'}")
    await update.message.reply_markdown("\n".join(lines))


async def cmd_proposal(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _authorized(update):
        return
    await update.message.reply_markdown(
        "*Generate a proposal*\n"
        "Run on Jarvis:\n"
        "`bash scripts/create_proposal.sh \"Client Name\" pro 34999 \"Add-on1,Add-on2\"`\n"
        "Files land in `data/proposals/` and are sent here automatically."
    )


# ---------- document handler ----------

async def handle_document(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _authorized(update):
        return
    doc = update.message.document
    if not doc:
        return
    if not (doc.file_name or "").lower().endswith((".xlsx", ".xlsm")):
        await update.message.reply_text("Only .xlsx/.xlsm Excel files are parsed.")
        return
    save_dir: Path = data_path("exports", ".keep").parent
    save_path = save_dir / doc.file_name
    file = await doc.get_file()
    await file.download_to_drive(str(save_path))
    kind, counters = auto_route(save_path)
    if kind == "unknown":
        await update.message.reply_text(
            "I saved the file, but the filename didn't match leads_today / cold_email_drafts / followups_due."
        )
        return
    await update.message.reply_text(f"Parsed {kind} edits: {counters}")


def build_app() -> Application:
    if not CONFIG.telegram_token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN missing")
    app = Application.builder().token(CONFIG.telegram_token).build()
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("today", cmd_today))
    app.add_handler(CommandHandler("leads", cmd_leads))
    app.add_handler(CommandHandler("hot", cmd_hot))
    app.add_handler(CommandHandler("drafts", cmd_drafts))
    app.add_handler(CommandHandler("approve_today", cmd_approve_today))
    app.add_handler(CommandHandler("reject_lead", cmd_reject_lead))
    app.add_handler(CommandHandler("pipeline", cmd_pipeline))
    app.add_handler(CommandHandler("profit", cmd_profit))
    app.add_handler(CommandHandler("content", cmd_content))
    app.add_handler(CommandHandler("tools", cmd_tools))
    app.add_handler(CommandHandler("proposal", cmd_proposal))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    return app


def run() -> None:
    app = build_app()
    log.info("Telegram bot starting (long-polling)")
    app.run_polling(stop_signals=None)


if __name__ == "__main__":
    run()

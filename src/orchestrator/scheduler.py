"""APScheduler setup. Daily jobs (IST) per the agency playbook."""
from __future__ import annotations

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from src.config import CONFIG
from src.orchestrator import jobs
from src.utils.logger import get_logger

log = get_logger("orchestrator.scheduler")


def build_scheduler() -> BackgroundScheduler:
    tz = CONFIG.timezone
    sched = BackgroundScheduler(timezone=tz)
    sched.add_job(jobs.job_lead_research_placeholder, CronTrigger(hour=10, minute=0, timezone=tz), id="research_10am")
    sched.add_job(jobs.job_score_and_dedupe, CronTrigger(hour=12, minute=0, timezone=tz), id="score_12pm")
    sched.add_job(jobs.job_daily_brief, CronTrigger(hour=13, minute=30, timezone=tz), id="brief_130pm")
    sched.add_job(jobs.job_review_window_open, CronTrigger(hour=14, minute=0, timezone=tz), id="review_2pm")
    sched.add_job(jobs.job_draft_approval_reminder, CronTrigger(hour=15, minute=0, timezone=tz), id="drafts_3pm")
    sched.add_job(jobs.job_followup_reminder, CronTrigger(hour=17, minute=0, timezone=tz), id="followups_5pm")
    sched.add_job(jobs.job_evening_content_report, CronTrigger(hour=20, minute=0, timezone=tz), id="evening_8pm")
    sched.add_job(jobs.job_final_daily_summary, CronTrigger(hour=21, minute=30, timezone=tz), id="final_930pm")
    return sched

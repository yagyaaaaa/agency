"""Run the whole daily flow once, immediately. Useful for first-time setup + CI smoke."""
from __future__ import annotations

from src.db import init_db
from src.orchestrator import jobs
from src.research.seed import seed
from src.utils.logger import get_logger

log = get_logger("orchestrator.dry_run")


def main() -> int:
    init_db()
    log.info("dry-run: seeding sample leads")
    new_n = seed()
    log.info("dry-run: %d new leads seeded", new_n)

    log.info("dry-run: score & dedupe")
    jobs.job_score_and_dedupe()

    log.info("dry-run: daily brief (will attempt telegram if configured)")
    jobs.job_daily_brief()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Jarvis scheduler for QuantumReach Agency OS."""
from __future__ import annotations

import argparse
import time
from typing import Sequence

from apscheduler.schedulers.background import BackgroundScheduler

from src.agents.cli import main as agents_cli_main
from src.config import CONFIG
from src.orchestrator.scheduler import build_scheduler
from src.utils.logger import get_logger

logger = get_logger("orchestrator.main")


def start_scheduler() -> None:
    scheduler: BackgroundScheduler = build_scheduler()
    scheduler.start()
    logger.info("scheduler started timezone=%s", CONFIG.timezone)
    try:
        while True:
            time.sleep(60)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="QuantumReach Agency OS scheduler")
    parser.add_argument("--scheduler", action="store_true", help="Start APScheduler with daily jobs")
    parser.add_argument("agent_args", nargs=argparse.REMAINDER, help="Pass-through to src.agents.cli")
    args = parser.parse_args(argv)

    agent_args = list(args.agent_args)
    if agent_args and agent_args[0] == "--":
        agent_args = agent_args[1:]

    if args.scheduler or not agent_args:
        if not CONFIG.enable_scheduler:
            logger.info("scheduler disabled by ENABLE_SCHEDULER=0")
            return 0
        start_scheduler()
        return 0

    return agents_cli_main(agent_args)


if __name__ == "__main__":
    raise SystemExit(main())

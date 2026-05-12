"""Shared agent runtime helpers."""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from typing import Iterator

from src import db
from src.agents.migrations import ensure_agent_schema
from src.utils.logger import get_logger


@dataclass
class AgentResult:
    agent_name: str
    status: str
    message: str
    count: int = 0
    outputs: dict[str, str] = field(default_factory=dict)
    data: dict[str, object] = field(default_factory=dict)


class BaseAgent:
    """Base class with file logging and optional DB job logging."""

    agent_name = "base_agent"

    def __init__(self) -> None:
        self.logger = get_logger(f"agents.{self.agent_name}")

    @contextmanager
    def run_context(self, dry_run: bool = False) -> Iterator[None]:
        ensure_agent_schema()
        started = datetime.utcnow().isoformat(timespec="seconds")
        job_name = f"{self.agent_name}{' [dry-run]' if dry_run else ''}"
        job_log_id: int | None = None
        self.logger.info("starting agent run dry_run=%s", dry_run)
        if not dry_run:
            with db.cursor() as cur:
                cur.execute(
                    "INSERT INTO job_log (job_name, started_at, status, message) VALUES (?, ?, ?, ?)",
                    (job_name, started, "running", ""),
                )
                job_log_id = int(cur.lastrowid)
        try:
            yield
        except Exception as exc:
            self.logger.exception("agent run failed: %s", exc)
            if job_log_id is not None:
                with db.cursor() as cur:
                    cur.execute(
                        "UPDATE job_log SET finished_at = ?, status = ?, message = ? WHERE job_log_id = ?",
                        (datetime.utcnow().isoformat(timespec="seconds"), "failed", str(exc), job_log_id),
                    )
            raise
        else:
            self.logger.info("agent run finished")
            if job_log_id is not None:
                message = str(getattr(self, "_job_log_message", "completed"))[:1000]
                with db.cursor() as cur:
                    cur.execute(
                        "UPDATE job_log SET finished_at = ?, status = ?, message = ? WHERE job_log_id = ?",
                        (datetime.utcnow().isoformat(timespec="seconds"), "ok", message, job_log_id),
                    )


def result(agent_name: str, status: str, message: str, count: int = 0, **outputs: str) -> AgentResult:
    return AgentResult(agent_name=agent_name, status=status, message=message, count=count, outputs=outputs)

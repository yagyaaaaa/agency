"""Compatibility migrations for agent-owned data columns."""
from __future__ import annotations

from src import db


TOOL_RESEARCH_COLUMNS = {
    "cost": "TEXT",
    "use_case": "TEXT",
    "implementation_difficulty": "TEXT",
    "expected_agency_impact": "TEXT",
    "recommended_action": "TEXT",
    "source_date": "TEXT",
}


def _table_columns(cur, table: str) -> set[str]:
    cur.execute(f"PRAGMA table_info({table})")
    return {row["name"] for row in cur.fetchall()}


def ensure_agent_schema() -> None:
    """Initialize the core schema and add missing optional columns.

    This avoids creating parallel models when the core backend already owns the
    tables, while still letting the agent layer store richer daily research.
    """

    db.init_db()
    with db.cursor() as cur:
        existing = _table_columns(cur, "tool_research")
        for name, col_type in TOOL_RESEARCH_COLUMNS.items():
            if name not in existing:
                cur.execute(f"ALTER TABLE tool_research ADD COLUMN {name} {col_type}")
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS research_query_usage (
                usage_id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_date TEXT NOT NULL,
                niche_id TEXT,
                city TEXT,
                market TEXT,
                query TEXT,
                provider TEXT,
                candidates_returned INTEGER DEFAULT 0,
                cost_estimate REAL DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        cur.execute("CREATE INDEX IF NOT EXISTS idx_research_usage_date ON research_query_usage(run_date)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_research_usage_market ON research_query_usage(market, run_date)")

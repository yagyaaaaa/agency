"""SQLite schema and connection helper."""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from src.config import CONFIG

SCHEMA = """
CREATE TABLE IF NOT EXISTS leads (
    lead_id INTEGER PRIMARY KEY AUTOINCREMENT,
    business_name TEXT NOT NULL,
    industry TEXT,
    city_country TEXT,
    website TEXT,
    email TEXT,
    phone TEXT,
    instagram TEXT,
    linkedin TEXT,
    decision_maker TEXT,
    source_url TEXT,
    website_quality_score INTEGER,
    automation_opportunity TEXT,
    personalization_hook TEXT,
    recommended_package TEXT,
    lead_score INTEGER DEFAULT 0,
    status TEXT DEFAULT 'new',
    notes TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    last_contacted_at TEXT,
    next_followup_at TEXT
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_leads_email_nonblank
    ON leads(LOWER(email)) WHERE email IS NOT NULL AND email != '';
CREATE INDEX IF NOT EXISTS idx_leads_business ON leads(LOWER(business_name));
CREATE INDEX IF NOT EXISTS idx_leads_status ON leads(status);
CREATE INDEX IF NOT EXISTS idx_leads_score ON leads(lead_score DESC);

CREATE TABLE IF NOT EXISTS contacts (
    contact_id INTEGER PRIMARY KEY AUTOINCREMENT,
    lead_id INTEGER REFERENCES leads(lead_id) ON DELETE CASCADE,
    name TEXT,
    role TEXT,
    email TEXT,
    phone TEXT,
    notes TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS outreach_messages (
    draft_id INTEGER PRIMARY KEY AUTOINCREMENT,
    lead_id INTEGER REFERENCES leads(lead_id) ON DELETE CASCADE,
    business_name TEXT,
    email TEXT,
    subject TEXT,
    email_body TEXT,
    personalization_reason TEXT,
    recommended_package TEXT,
    status TEXT DEFAULT 'needs_approval',
    approved_by_yagya INTEGER DEFAULT 0,
    sent_at TEXT,
    followup_1_body TEXT,
    followup_1_date TEXT,
    followup_2_body TEXT,
    followup_2_date TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_outreach_status ON outreach_messages(status);
CREATE INDEX IF NOT EXISTS idx_outreach_lead ON outreach_messages(lead_id);

CREATE TABLE IF NOT EXISTS followups (
    followup_id INTEGER PRIMARY KEY AUTOINCREMENT,
    lead_id INTEGER REFERENCES leads(lead_id) ON DELETE CASCADE,
    due_date TEXT NOT NULL,
    type TEXT,
    notes TEXT,
    done INTEGER DEFAULT 0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_followups_due ON followups(due_date, done);

CREATE TABLE IF NOT EXISTS suppressions (
    suppression_id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT,
    domain TEXT,
    business_name TEXT,
    reason TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_supp_email ON suppressions(LOWER(email));
CREATE INDEX IF NOT EXISTS idx_supp_domain ON suppressions(LOWER(domain));
CREATE INDEX IF NOT EXISTS idx_supp_business ON suppressions(LOWER(business_name));

CREATE TABLE IF NOT EXISTS replies (
    reply_id INTEGER PRIMARY KEY AUTOINCREMENT,
    lead_id INTEGER REFERENCES leads(lead_id) ON DELETE CASCADE,
    direction TEXT,
    subject TEXT,
    body TEXT,
    sentiment TEXT,
    received_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS clients (
    client_id INTEGER PRIMARY KEY AUTOINCREMENT,
    lead_id INTEGER REFERENCES leads(lead_id),
    business_name TEXT NOT NULL,
    primary_contact TEXT,
    email TEXT,
    phone TEXT,
    package TEXT,
    add_ons TEXT,
    onboarded_at TEXT DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'active',
    notes TEXT
);

CREATE TABLE IF NOT EXISTS projects (
    project_id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id INTEGER REFERENCES clients(client_id) ON DELETE CASCADE,
    name TEXT,
    package TEXT,
    status TEXT DEFAULT 'in_progress',
    start_date TEXT,
    target_launch TEXT,
    actual_launch TEXT,
    notes TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS revenue (
    transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
    client TEXT,
    package TEXT,
    add_ons TEXT,
    amount_booked REAL DEFAULT 0,
    amount_collected REAL DEFAULT 0,
    payment_method TEXT,
    payment_status TEXT,
    commission_due REAL DEFAULT 0,
    net_profit_estimate REAL DEFAULT 0,
    notes TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_revenue_created ON revenue(created_at);

CREATE TABLE IF NOT EXISTS expenses (
    expense_id INTEGER PRIMARY KEY AUTOINCREMENT,
    category TEXT,
    vendor TEXT,
    amount REAL DEFAULT 0,
    payment_method TEXT,
    recurring INTEGER DEFAULT 0,
    notes TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_expenses_created ON expenses(created_at);

CREATE TABLE IF NOT EXISTS commissions (
    commission_id INTEGER PRIMARY KEY AUTOINCREMENT,
    payee TEXT,
    transaction_id INTEGER REFERENCES revenue(transaction_id),
    amount REAL DEFAULT 0,
    status TEXT DEFAULT 'pending',
    notes TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS daily_reports (
    report_id INTEGER PRIMARY KEY AUTOINCREMENT,
    report_date TEXT NOT NULL,
    summary TEXT,
    excel_paths TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_daily_reports_date ON daily_reports(report_date);

CREATE TABLE IF NOT EXISTS content_assets (
    asset_id INTEGER PRIMARY KEY AUTOINCREMENT,
    kind TEXT,
    title TEXT,
    body TEXT,
    path TEXT,
    tags TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS tool_research (
    tool_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    category TEXT,
    url TEXT,
    notes TEXT,
    rating INTEGER,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS proposals (
    proposal_id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_name TEXT,
    industry TEXT,
    package TEXT,
    add_ons TEXT,
    timeline TEXT,
    price REAL,
    support_plan TEXT,
    payment_terms TEXT,
    notes TEXT,
    md_path TEXT,
    html_path TEXT,
    pdf_path TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS job_log (
    job_log_id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_name TEXT NOT NULL,
    started_at TEXT DEFAULT CURRENT_TIMESTAMP,
    finished_at TEXT,
    status TEXT,
    message TEXT
);
"""


def get_db_path() -> Path:
    p = Path(CONFIG.sqlite_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(str(get_db_path()))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    return conn


def init_db() -> None:
    with connect() as conn:
        conn.executescript(SCHEMA)
        conn.commit()


@contextmanager
def cursor() -> Iterator[sqlite3.Cursor]:
    conn = connect()
    try:
        cur = conn.cursor()
        yield cur
        conn.commit()
    finally:
        conn.close()

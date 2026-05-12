# QuantumReach Agency OS

Revenue-ops backend for the QuantumReach agency.
Runs on **Jarvis VPS** in Docker. SQLite, Python 3.12, APScheduler, python-telegram-bot, openpyxl, WeasyPrint.

> **Important** — this system never auto-sends emails. It generates drafts, exports them to Excel, and waits for the founder to approve/edit/send manually. OpenClaw agent workflows will be wired in later by Codex.

---

## What it does
- Keeps a CRM in SQLite (leads, contacts, outreach drafts, follow-ups, suppression, replies, clients, projects, revenue, expenses, commissions, proposals, content, tools, daily reports).
- Dedupes leads by email, domain, and normalized business name.
- Tracks suppression / unsubscribe (manual entries + future-proofed for reply parsing).
- Generates a daily set of Excel files (frozen header, filters, multi-sheet) — *leads, drafts, follow-ups, profit, pipeline*.
- Sends those files + a Markdown brief to the founder over Telegram.
- Accepts the **edited Excel back** as a Telegram document and parses approval / status columns into SQLite.
- Tracks profit (revenue booked, cash collected, pending, commissions, expenses, net estimate).
- Generates proposals (Markdown, HTML, PDF-ready) using the agency's payment-terms defaults.
- Stores content + tool-research notes for later content marketing.
- Runs a cron-style daily schedule keyed to IST.

## File tree
```
quantumreach-agency-os/
├── src/
│   ├── config.py
│   ├── db.py
│   ├── crm/                {leads, clients, suppression}
│   ├── email/              {template, drafts}
│   ├── excel/              {exporter, importer}
│   ├── telegram/           {bot, notify, formatting}
│   ├── profit/tracker.py
│   ├── proposal/generator.py
│   ├── content/store.py
│   ├── research/           {importer, scoring, seed}
│   ├── orchestrator/       {main, scheduler, jobs, dry_run}
│   └── utils/              {logger, dedupe, paths}
├── configs/                {packages.yaml, niches.yaml, email_template.txt}
├── data/
│   ├── db/                 # SQLite lives here
│   ├── excel/              # daily Excel exports
│   ├── reports/
│   ├── outreach/
│   ├── content/
│   ├── tool-research/
│   ├── profit/
│   ├── proposals/
│   ├── exports/            # tarball backups + Telegram-uploaded edits
│   ├── logs/
│   └── seed/sample_leads.csv
├── scripts/                {run_daily, export_excel, backup, restore, import_leads, create_proposal, dry_run}.sh
├── tests/
├── docs/
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example
└── README.md
```

## Setup

```bash
# On Jarvis
ssh jarvis
git clone <this repo>  # or scp the folder over
cd quantumreach-agency-os
cp .env.example .env
$EDITOR .env           # fill TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, etc.

# Build + start
docker compose build
docker compose up -d

# Watch logs
docker compose logs -f
```

For local Python dev (no Docker):
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m src.orchestrator.dry_run
```

## Day-to-day

| Action | Command |
|---|---|
| Force a full daily cycle now | `bash scripts/dry_run.sh` (or `docker exec qr-agency-os python -m src.orchestrator.dry_run`) |
| Generate today's Excel files manually | `bash scripts/export_excel.sh` |
| Import a CSV/XLSX of leads | `bash scripts/import_leads.sh data/seed/sample_leads.csv upsert` |
| Create a proposal | `bash scripts/create_proposal.sh "Client Name" pro 34999 "WhatsApp lead capture"` |
| Backup everything | `bash scripts/backup.sh` |
| Restore from a backup tarball | `bash scripts/restore.sh data/exports/agency-backup-*.tar.gz` |

## Telegram

After setting `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID` and starting the container:

- The bot long-polls and accepts commands (see [docs/TELEGRAM_COMMANDS.md](docs/TELEGRAM_COMMANDS.md)).
- Daily brief + Excel files arrive at **1:30 PM IST**.
- To approve drafts or change lead status: download the file, edit the *approve/reject* and *founder_notes* columns, send it back to the bot — it will parse and update SQLite.

## Approving / rejecting drafts

Three ways:

1. **In Telegram**: `/drafts` → see pending → `/approve_today` to bulk-approve, or `/reject_lead <id>`.
2. **By editing Excel** and uploading back to the bot — fill the `approve (yes/no)` and (optionally) `send_manually (yes/no)` columns in `cold_email_drafts_*.xlsx`.
3. Approved drafts remain as **drafts** — copy them into your inbox and send manually. The system never sends email on its own.

## Tests
```bash
python -m pytest tests/ -q
```

## Architecture notes
- **Single container** (`qr-agency-os`). The orchestrator process starts the scheduler and the Telegram bot thread.
- **SQLite WAL** mode so the bot thread and scheduler jobs don't deadlock.
- **Logs** rotate per module under `data/logs/`. Every scheduled job records a row in `job_log` with status + message.
- **Idempotency**: imports and seeds use upserts; dedupe enforced by email, domain, and normalized business name.
- **Backups**: `scripts/backup.sh` produces a timestamped tarball with a consistent SQLite snapshot via `.backup`.

## What's intentionally out of scope (Codex will handle)
- Real lead-research agents (currently a no-op placeholder at 10:00 AM).
- Live email sending (forever — by design).
- OpenClaw agent tuning.
- Reply-parsing / inbox automation.

See [docs/AGENCY_PLAYBOOK.md](docs/AGENCY_PLAYBOOK.md) for the sales motion and [docs/DATA_MODEL.md](docs/DATA_MODEL.md) for the full schema.

# Operations — Daily Founder Loop

Founder works **2:00 PM – 5:30 PM IST**.
Everything before 2 PM is automation prep. Everything after 5:30 PM is automation summary.

## Schedule (Asia/Kolkata)

| Time | Job | What it does |
|---|---|---|
| 10:00 | `job_lead_research_placeholder` | Runs the Lead Research Agent to create a research plan or ingest approved seed leads |
| 12:00 | `job_score_and_dedupe` | Re-scores leads with the agent scoring model, re-picks package, generates draft emails |
| 13:30 | `job_daily_brief` | Builds 5 Excel files, sends them + the brief to Telegram |
| 14:00 | `job_review_window_open` | "Founder review window open" ping |
| 15:00 | `job_draft_approval_reminder` | Nudge if drafts still need approval |
| 17:00 | `job_followup_reminder` | Nudge if follow-ups are due |
| 20:00 | `job_evening_content_report` | Profit + content + tool recap |
| 21:30 | `job_final_daily_summary` | End-of-day status |

## What the founder does between 2 PM and 5:30 PM

1. Open Telegram → today's Excel files.
2. Open `cold_email_drafts_*.xlsx`. For each row:
   - Set `approve (yes/no) = yes` to mark approved (or `no` to reject)
   - Optionally edit `founder_edits_to_subject` / `founder_edits_to_body`
   - When you actually copy-paste into Gmail/Outlook and send, set `send_manually = yes`
3. Open `leads_today_*.xlsx` → set `approval` + `founder_notes` for the top of the funnel.
4. Save and **send the file back to the bot** — it parses & writes to SQLite, sends a confirmation like `Parsed drafts edits: {approved: 4, rejected: 1, sent_manually: 3}`.
5. Sales calls, deliveries, payment collection — outside this system.
6. Record any new revenue / expenses with quick SQL or by editing a future profit Excel (TBD via Codex).

## Routine maintenance

- **Weekly**: `bash scripts/backup.sh` (or wire to cron on Jarvis host).
- **Monthly**: prune `data/exports/*.tar.gz` older than N months.
- **As needed**: `docker compose logs -f --tail=200`.

## Failure modes

- **Scheduler dies but bot lives**: messages still work; restart container.
- **Bot dies, scheduler lives**: Excel files still produced and sent (the notify path uses `httpx`, not the bot). `/today` won't respond — restart container.
- **DB locked**: extremely unlikely (WAL mode). If it happens, stop the container, run `sqlite3 agency.sqlite "PRAGMA integrity_check;"`, restart.

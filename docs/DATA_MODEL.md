# Data model

SQLite at `data/db/agency.sqlite`. All tables created on first run by `src/db.py::init_db()`.

## leads
The funnel head.

| Column | Notes |
|---|---|
| `lead_id` | PK |
| `business_name` | required; used for dedupe (normalized) |
| `industry` | free text; matched against niche map |
| `city_country` | drives India/Dubai routing |
| `website`, `email`, `phone`, `instagram`, `linkedin` | contact channels |
| `decision_maker` | name + role (free text) |
| `source_url` | where you found them |
| `website_quality_score` | 0–10 (lower = bigger opportunity) |
| `automation_opportunity`, `personalization_hook` | sales-grade notes |
| `recommended_package` | filled by `score_and_dedupe` job |
| `lead_score` | 0–100 |
| `status` | `new` / `contacted` / `replied` / `proposal_sent` / `won` / `lost` / `rejected` / `suppressed` |
| `notes` | append-only via `set_status(note=...)` |
| `created_at`, `updated_at`, `last_contacted_at`, `next_followup_at` | timestamps |

**Unique** on `LOWER(email)` (when non-blank). Soft dedupe also enforced by domain (from website or email) and normalized business name in `find_duplicate()`.

## outreach_messages
One row per drafted email. Status values: `needs_approval`, `approved`, `rejected`, `sent_manually`, `followup_due`, `suppressed`.

## followups
Schedule entries; written manually or by reply parser (future).

## suppressions
Unsub list. Match on any of email / domain / normalized business name.

## replies
Reserved for the future inbox-parser (Codex).

## clients / projects
Created when a lead converts. `clients.lead_id` points back to the original lead.

## revenue / expenses / commissions
Profit tracker. Net profit estimate auto-computed on insert if not provided:
```
net = collected - commission_due - 0.05 * collected
```
(Then `compute_summary` subtracts expenses for the overall picture.)

## daily_reports
One row per day with the Telegram brief + Excel paths.

## content_assets / tool_research
Free-form notes; surfaced in `/content` and `/tools`.

## proposals
One row per generated proposal with all three artifact paths.

## job_log
Every scheduled job writes a row here with status + message. Read with:
```sql
SELECT job_name, status, started_at, finished_at, message
FROM job_log ORDER BY job_log_id DESC LIMIT 50;
```

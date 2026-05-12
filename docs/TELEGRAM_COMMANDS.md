# Telegram commands

All commands work from the chat configured by `TELEGRAM_CHAT_ID`.
If `TELEGRAM_ADMIN_USER_IDS` is set, only those user ids may run commands.

| Command | What it does |
|---|---|
| `/status` | Counts by status, drafts pending, follow-ups due |
| `/today` | Full daily brief inline (same content as the 1:30 PM message) |
| `/leads` | Top 15 leads by score |
| `/hot` | Top 10 leads with industry + recommended package |
| `/drafts` | List drafts awaiting approval |
| `/approve_today` | Bulk-approve every pending draft (use sparingly) |
| `/reject_lead <id>` | Mark a lead `rejected` |
| `/pipeline` | Pipeline counts by stage |
| `/profit` | Profit summary (booked / collected / pending / net) |
| `/content` | Recent content assets |
| `/tools` | Recent tool-research entries |
| `/proposal` | How to generate a proposal from the shell |
| `/help` | Command list |

## Uploading edited Excel files

The bot listens for any Excel document. Filename prefixes route the file:
- `leads_today_*.xlsx` → updates lead approval / status / notes
- `cold_email_drafts_*.xlsx` → approves/rejects/edits drafts, marks sent
- `followups_due_*.xlsx` → marks follow-ups done

Anything else gets saved under `data/exports/` and is **not parsed** — a message tells you so.

## Recognized cell values

- `yes`, `y`, `true`, `1`, `approve`, `approved` → positive
- `no`, `n`, `false`, `0`, `reject`, `rejected` → negative
- empty / anything else → no change

This is forgiving on purpose — Excel autocomplete shouldn't trip it.

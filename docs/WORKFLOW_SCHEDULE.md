# Workflow Schedule

All times use `TIMEZONE`, default `Asia/Kolkata`.

| Time | Job | Command |
| --- | --- | --- |
| 10:00 AM | Lead research | `python -m src.agents.cli lead-research --input /app/data/seed/leads.csv` |
| 12:00 PM | Scoring and dedupe | `python -m src.agents.cli lead-research --input /app/data/seed/leads.csv` |
| 1:30 PM | Telegram daily brief + Excel reports | `python -m src.agents.cli ceo-summary` |
| 2:00 PM | Founder review begins | Manual review of Excel and drafts |
| 3:00 PM | Cold email draft approval reminder | `python -m src.agents.cli cold-email --limit 30` |
| 5:00 PM | Follow-up reminder | `python -m src.agents.cli followups` |
| 8:00 PM | Content/tool/profit report | `python -m src.agents.cli content && python -m src.agents.cli tool-research && python -m src.agents.cli profit` |
| 9:30 PM | Final daily summary | `python -m src.agents.cli ceo-summary` |

One-shot dry-run:

```bash
python -m src.agents.cli --dry-run daily
```

One-shot live workflow:

```bash
python -m src.agents.cli daily
```

Long-running scheduler:

```bash
python -m src.orchestrator.main --scheduler
```

The scheduler maps these jobs in `src/orchestrator/main.py`.

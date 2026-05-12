# Outreach Playbook

The system is manual approval only.

## Hard Rules

- Agents never send email.
- Agents write drafts to `outreach_messages`.
- Founder approves final outreach.
- Suppressed, unsubscribed, rejected, negative-reply, converted, and client leads are blocked.
- Duplicate drafts are blocked by `lead_id` and email.
- Every email includes an opt-out line.
- No fake claims, fake audits, fake client results, or implied prior relationship.

## Initial Drafts

Run:

```bash
python -m src.agents.cli cold-email --limit 30
```

Dry-run:

```bash
python -m src.agents.cli --dry-run cold-email --limit 30
```

Output:

- SQLite: `outreach_messages`
- Excel: `/app/data/excel/cold_email_drafts.xlsx`

## Follow-ups

Rules:

- Follow-up 1 after 3 days.
- Follow-up 2 after 7 days.
- Follow-ups require `outreach_messages.sent_at` to be set by the manual process.
- Block if suppressed, negative reply, unsubscribed, rejected, converted, or client.

Run:

```bash
python -m src.agents.cli followups
```

Output:

- SQLite: `followups`
- Excel: `/app/data/excel/followups_due.xlsx`

## Excel Review

Founder reviews:

1. `leads_today.xlsx`
2. `cold_email_drafts.xlsx`
3. `followups_due.xlsx`
4. `profit_report.xlsx`

# OpenClaw Tuning

This repo is configured for Jarvis, not Alfred. Alfred runs app containers and is intentionally out of scope.

## Security Defaults

- Run OpenClaw behind authentication only. Do not expose it publicly.
- Keep secrets in environment variables. Do not mount `.env`, SSH keys, or key dumps into agent-readable paths.
- Give browser access only to Lead Research Agent and Tool Research Agent.
- Give write access only to `/app/data` and `/app/data/logs`.
- Deny direct email sending for every agent. Outreach is draft-only.
- Deny unrestricted shell, destructive filesystem operations, and arbitrary community skill installs.

The policy file is `configs/openclaw_agency_agents.yaml`.

## Daily Volume Tuning

Lead volume is controlled in the CLI:

```bash
python -m src.agents.cli lead-research --input /app/data/seed/leads.csv --india-limit 35 --foreign-limit 10
```

Default split:

- India: 30-35 leads/day
- Dubai/foreign: 5-10 leads/day

Use lower numbers when quality drops. The Lead Research Agent should not pad the CRM with weak or fake leads.

## Niche Tuning

Primary niches live in `configs/niches.yaml` and the OpenClaw policy:

- Architects
- Interior designers
- Builders
- Clinics
- Gyms / fitness coaches
- Coaching institutes
- Premium local businesses
- Dubai/foreign service businesses

Add a niche only if it has a clear website or automation buying trigger.

## Package Tuning

Package rules are implemented in `src/agents/package_recommendation.py` and pricing lives in `configs/packages.yaml`.

- Starter: small/easy Indian clients only.
- Pro: default viable Indian business recommendation.
- Enterprise: high-ticket, strong lead flow, builders, premium clinics, serious architects, multi-service businesses, and strong Dubai/foreign opportunities.
- Foreign/Dubai: Launch Website, Growth Website + Automation, or AI Growth Infrastructure.

## Jarvis Run Pattern

Dry-run:

```bash
python -m src.agents.cli --dry-run daily
```

Live daily workflow:

```bash
python -m src.agents.cli daily
```

Scheduler mode:

```bash
python -m src.orchestrator.main --scheduler
```

Docker already points at `src.orchestrator.main`; with no arguments it starts the scheduler if `ENABLE_SCHEDULER=1`.

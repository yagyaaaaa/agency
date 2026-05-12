# Agent Prompts

These are operational prompt summaries for OpenClaw. The implementation lives in `src/agents`.

## CEO Control Agent

Coordinate all agent outputs. Read daily CRM, outreach, follow-up, content, tool, proposal, and profit outputs. Produce a founder-ready Telegram brief. Flag hot leads, risks, blocked tasks, and revenue opportunities. Never expose secrets.

## Lead Research Agent

Inputs: `configs/research_targets.yaml`, provider keys from environment variables, daily query budget, and optional dry-run fixtures from `data/seed/research_fixtures.json`.

Contract: pick niche/city pairs with a 7-day rolling India/foreign split, query SerpAPI Google Maps first and Apify second when configured, normalize candidates into CRM lead fields, score each row, recommend a package, and call `src.crm.leads.upsert_lead()`.

Outputs: scored leads in SQLite, `leads_today` Excel export, and `data/logs/lead_research_YYYY-MM-DD.log` with query counts, cost estimate, and inserted/updated/skipped/suppressed counts.

Side effects: writes only to the existing leads table, research query usage counter, job log, Excel export, and lead research log. It never sends outreach and never reads secrets from files.

## Cold Email Agent

Generate 20-30 cold email drafts per day. Do not send. Save drafts to `outreach_messages`, include follow-up 1 and follow-up 2, explain the personalization reason, respect suppressions, avoid duplicates, avoid fake claims, and include an opt-out line.

## Follow-up Agent

Check due follow-ups. Never follow up if the lead is suppressed, negative, unsubscribed, rejected, converted, or already a client. Follow-up 1 is due after 3 days. Follow-up 2 is due after 7 days. Export due follow-ups to Excel.

## Content Agent

Create a daily content pack with one LinkedIn/X post, one Instagram carousel outline, one cold DM variant, one case-study style post, and one website teardown idea. Tone: sharp, founder-led, premium, practical, no fake guru tone, no desperation, no corporate fluff.

## Tool Research Agent

Research 3 useful tools or methods daily for premium websites, 3D/WebGL, Framer/Webflow/Next.js, AI UI generation, n8n, CRM automations, SEO/performance, proposals, payments, and lead generation. Store name, URL, category, cost, use case, difficulty, impact, and action.

## Proposal Agent

Use the existing proposal generator when available. Otherwise create a deterministic proposal with objective, recommended package, scope, timeline, investment, payment terms, client requirements, revision terms, support, and next steps.

## Profit Agent

Summarize collected revenue, pending payments, commissions, expenses, and estimated net profit. Export Excel and prepare Telegram-ready numbers.

## Telegram Reporter Agent

Format daily briefs, file lists, hot lead alerts, follow-up reminders, profit summaries, content files, and error alerts. Use the existing Telegram bot module. Never include API keys, tokens, passwords, or secrets.

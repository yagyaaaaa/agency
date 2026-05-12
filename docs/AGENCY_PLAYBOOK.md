# QuantumReach — Agency Playbook

## Founder
Yagya Chauhan — `connect@quantumreach.tech` / `yagya@quantumreach.tech`

## Working hours
3–4 hours/day after 1 PM IST.
Core review window: **2:00 PM – 5:30 PM IST**.

## Offers

### India packages (INR, one-time + monthly support)

| Tier | One-time | Monthly support | When to recommend |
|---|---:|---:|---|
| Starter | ₹14,999 | ₹3,499 | Only for small/easy clients. **Never lead with this.** |
| Pro | ₹34,999 | ₹5,999 | **Default recommendation.** Most architects/designers/clinics/gyms/coaching. |
| Enterprise | ₹79,999 | ₹9,999 | High-ticket businesses with strong lead potential. Builders, premium clinics, multi-location gyms. |

### Foreign / Dubai (USD)

| Offer | Range |
|---|---|
| Launch Website | $499 – $799 |
| Growth Website + Automation | $1,200 – $2,500 |
| AI Growth Infrastructure | $3,000 – $7,500 |

## Niches (in order of priority)

1. Architects
2. Interior designers
3. Builders
4. Clinics
5. Gyms / fitness coaches
6. Coaching institutes
7. Premium local businesses
8. Dubai / foreign service businesses

## First 14-day market mix
- **80%** India outreach
- **20%** Dubai / foreign

## Sales logic (built into `src/research/scoring.py`)

- Default recommendation is **Pro**.
- Enterprise gets recommended when: industry is high-ticket *and* score ≥ 65, **or** the lead is foreign with score ≥ 60.
- Starter only when score < 35 — and even then, don't lead with it.

## Outreach principles

- Manual approval only. The system never sends.
- One personalized observation per email.
- Two short follow-ups (3 days, 7 days). Drafted automatically; founder decides whether to send.
- Respect suppression list: email, domain, business name.
- Hard cap: no third follow-up.

## Pipeline stages
`new → contacted → replied → proposal_sent → won` / `lost` / `rejected` / `suppressed`

## Cash & profit policy

- 50% advance, 50% before launch.
- Support begins after launch.
- Add-ons billed separately.
- Prices exclude GST where applicable.

## What's NOT in this codebase
- Live email sending (forever, by design).
- Real research agents (Codex/OpenClaw will wire later).
- Client portal — out of scope for v1.

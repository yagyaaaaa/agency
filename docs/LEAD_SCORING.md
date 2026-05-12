# Lead Scoring

Scoring is implemented in `src/agents/scoring.py`.

| Signal | Points |
| --- | ---: |
| Bad/outdated or missing website | +2 |
| Premium service business | +2 |
| Clear contact email | +1 |
| High-ticket industry | +2 |
| Active Instagram/portfolio | +1 |
| Weak lead capture or follow-up | +2 |
| Dubai/foreign market | +1 |
| Strong personalization hook | +2 |

Maximum practical score is 13.

## Package Logic

Package recommendation is implemented in `src/agents/package_recommendation.py`.

- Starter is only for small/easy Indian clients.
- Pro is the default for viable Indian businesses.
- Enterprise is for high-ticket, strong lead flow, multi-service businesses, builders, premium clinics, serious architects, and very strong scores.
- Dubai/foreign leads map to Launch Website, Growth Website + Automation, or AI Growth Infrastructure.

## Lead Fields

The agent uses the existing `leads` table fields:

- `lead_id`
- `business_name`
- `industry`
- `city_country`
- `website`
- `email`
- `phone`
- `instagram`
- `linkedin`
- `decision_maker`
- `source_url`
- `website_quality_score`
- `automation_opportunity`
- `personalization_hook`
- `recommended_package`
- `lead_score`
- `status`
- `notes`

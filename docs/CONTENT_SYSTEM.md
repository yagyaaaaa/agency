# Content System

The Content Agent creates:

- 1 LinkedIn/X post
- 1 Instagram carousel outline
- 1 cold DM variant
- 1 case-study style post
- 1 website teardown idea

Output:

```text
/app/data/content/YYYY-MM-DD/content_pack.md
```

Tone:

- sharp
- founder-led
- premium
- practical
- no fake guru tone
- no desperation
- no corporate fluff

Themes:

- premium website mistakes
- AI automation for service businesses
- Mumbai businesses losing leads due to slow follow-up
- before/after redesign concepts
- founder building agency while building product
- websites as lead systems, not brochures

Run:

```bash
python -m src.agents.cli content
```

Dry-run:

```bash
python -m src.agents.cli --dry-run content
```

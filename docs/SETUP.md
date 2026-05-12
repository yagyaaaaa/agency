# Setup — Jarvis VPS

## Pre-reqs on Jarvis
- Docker + docker compose
- Open outbound HTTPS (Telegram API)
- A bot from **@BotFather**, your chat id from **@userinfobot**

## Steps

```bash
ssh jarvis
mkdir -p ~/apps && cd ~/apps
git clone <repo-url> quantumreach-agency-os   # or scp the folder
cd quantumreach-agency-os
cp .env.example .env
nano .env
```

Fill at minimum:
```
TELEGRAM_BOT_TOKEN=<from BotFather>
TELEGRAM_CHAT_ID=<your numeric chat id>
TELEGRAM_ADMIN_USER_IDS=<your user id>   # optional but recommended
FOUNDER_NAME=Yagya Chauhan
TIMEZONE=Asia/Kolkata
```

Build + run:
```bash
docker compose build
docker compose up -d
docker compose logs -f
```

Confirm the scheduler registered all 8 jobs:
```
scheduled: research_10am  -> 2026-05-13 10:00:00+05:30
scheduled: score_12pm    -> 2026-05-13 12:00:00+05:30
scheduled: brief_130pm   -> 2026-05-13 13:30:00+05:30
scheduled: review_2pm    -> 2026-05-13 14:00:00+05:30
scheduled: drafts_3pm    -> 2026-05-13 15:00:00+05:30
scheduled: followups_5pm -> 2026-05-13 17:00:00+05:30
scheduled: evening_8pm   -> 2026-05-13 20:00:00+05:30
scheduled: final_930pm   -> 2026-05-13 21:30:00+05:30
```

Smoke test from inside the container:
```bash
docker exec qr-agency-os python -m src.orchestrator.dry_run
```
You should see seeded leads, an Excel batch produced under `data/excel/`, and a Telegram brief if your bot is wired.

## Updating
```bash
git pull
docker compose build
docker compose up -d
```

## Troubleshooting
- **No Telegram messages**: check `TELEGRAM_BOT_TOKEN` and that you've started a chat with the bot (Telegram won't let bots DM users that haven't initiated).
- **PDF render fails on proposals**: usually missing system fonts. Already installed in Dockerfile (`fonts-dejavu`); on bare metal install `libpango`/`weasyprint` deps.
- **Container restarts**: check `data/logs/orchestrator_main.log`.

#!/usr/bin/env bash
# Run the agency-os container's daily flow once.
set -euo pipefail
cd "$(dirname "$0")/.."
if [ -z "${IN_DOCKER:-}" ] && command -v docker >/dev/null 2>&1 && docker ps --format '{{.Names}}' | grep -q '^qr-agency-os$'; then
  docker exec qr-agency-os python -m src.orchestrator.dry_run
else
  python -m src.orchestrator.dry_run
fi

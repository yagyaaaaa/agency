#!/usr/bin/env bash
# Backup SQLite + data/ to a timestamped tar.gz under data/exports/
set -euo pipefail
cd "$(dirname "$0")/.."
ts="$(date +%Y%m%d-%H%M%S)"
out="data/exports/agency-backup-${ts}.tar.gz"
mkdir -p data/exports
db="${SQLITE_PATH:-data/db/agency.sqlite}"
if [ -f "$db" ]; then
  # consistent snapshot
  sqlite3 "$db" ".backup data/exports/agency-${ts}.sqlite"
fi
tar -czf "$out" \
  --exclude='data/exports/*.tar.gz' \
  data/db data/excel data/reports data/proposals data/content data/outreach data/profit data/logs 2>/dev/null || true
echo "Backup created: $out"

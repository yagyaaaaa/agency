#!/usr/bin/env bash
# Import leads from a CSV or XLSX. Usage: scripts/import_leads.sh path/to/leads.csv [upsert|insert|skip]
set -euo pipefail
cd "$(dirname "$0")/.."
file="${1:-data/seed/sample_leads.csv}"
mode="${2:-upsert}"
python - <<PY
from src.db import init_db
init_db()
from src.research.importer import import_leads_file
print(import_leads_file("$file", mode="$mode"))
PY

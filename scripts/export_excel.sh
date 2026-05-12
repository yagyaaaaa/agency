#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
exec python -c "from src.db import init_db; init_db(); from src.excel.exporter import export_all; print(export_all())"

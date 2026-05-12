#!/usr/bin/env bash
# Restore from a tar.gz produced by backup.sh
set -euo pipefail
cd "$(dirname "$0")/.."
archive="${1:-}"
if [ -z "$archive" ] || [ ! -f "$archive" ]; then
  echo "Usage: scripts/restore.sh <path-to-backup.tar.gz>" >&2
  exit 1
fi
echo "WARNING: This will overwrite files under data/. Continue? (y/N)"
read -r ans
[ "$ans" = "y" ] || [ "$ans" = "Y" ] || exit 1
tar -xzf "$archive"
echo "Restore complete."

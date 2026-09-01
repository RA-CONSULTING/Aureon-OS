#!/usr/bin/env bash
# Orca cloud launcher: terminal protection HOLD.
set -euo pipefail

exec /usr/local/bin/python -I -S -B \
  /app/scripts/bootstrap/protected_bootstrap_v05.py \
  --target-id cloud-orca

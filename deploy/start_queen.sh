#!/usr/bin/env bash
# Aureon Queen cloud launcher: terminal protection HOLD.
set -euo pipefail

exec /usr/local/bin/python -I -S -B \
  /app/scripts/bootstrap/protected_bootstrap_v05.py \
  --target-id cloud-queen-redistribution

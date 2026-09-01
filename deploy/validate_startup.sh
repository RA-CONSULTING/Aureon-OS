#!/usr/bin/env bash
# Cloud startup validation is a terminal protection preflight.
set -euo pipefail

exec /usr/local/bin/python -I -S -B \
  /app/scripts/bootstrap/protected_bootstrap_v05.py \
  --target-id cloud-supervisor

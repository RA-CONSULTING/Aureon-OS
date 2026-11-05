#!/usr/bin/env bash
# Master cloud launcher stays on terminal HOLD until the stage 11 gate verifies
# receipts 1-5 on this tip. The image does not include the gate unless a later
# change copies it. A missing or unclear gate keeps the isolated bootstrap.
set -euo pipefail

GATE="/app/scripts/bootstrap/go_live_stage11_gate.py"

if [ -r "$GATE" ] && /usr/local/bin/python -I -S -B "$GATE" --check; then
  exec /usr/local/bin/python -I -S -B "$GATE" --launch-contained
fi

exec /usr/local/bin/python -I -S -B \
  /app/scripts/bootstrap/protected_bootstrap_v05.py \
  --target-id master-launcher

#!/usr/bin/env bash
# Linux installation stays on terminal HOLD until the stage 11 gate verifies
# receipts 1-5 on this tip. The gate is stdlib-only and does not import a target.
# Only a clear gate may replace this process with the contained cold boot.
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
BOOTSTRAP="$ROOT/scripts/bootstrap/protected_bootstrap_v05.py"
GATE="$ROOT/scripts/bootstrap/go_live_stage11_gate.py"

if [ ! -r "$BOOTSTRAP" ] || [ ! -x /usr/bin/python3 ]; then
  echo "Protected Linux installer bootstrap unavailable; refusing installation." >&2
  exit 1
fi

if [ -r "$GATE" ] && /usr/bin/python3 -I -S -B "$GATE" --check; then
  exec /usr/bin/python3 -I -S -B "$GATE" --launch-contained
fi

exec /usr/bin/python3 -I -S -B "$BOOTSTRAP" --target-id linux-supervisor

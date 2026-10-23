#!/usr/bin/env bash
# Bring Aureon up on Linux. Live trading stays off. Safe to re-run.
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
export AUREON_LIVE_TRADING=0
export AUREON_SIMULATED_BOOT=0
export PYTHONPATH="${ROOT}${PYTHONPATH:+:$PYTHONPATH}"

if [ ! -x "$ROOT/.venv/bin/python" ]; then
  exec bash "$ROOT/production/install.sh"
fi

exec "$ROOT/.venv/bin/python" -m aureon.autonomous.aureon_master_launcher --preflight

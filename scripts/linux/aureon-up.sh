#!/usr/bin/env bash
# Bring Aureon up on Linux. Live mode stays locked unless the stage 11 gate
# reports clear and AUREON_OPERATOR_ALLOW_LIVE is set. Safe to re-run.
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
export AUREON_SIMULATED_BOOT=0
export PYTHONPATH="${ROOT}${PYTHONPATH:+:$PYTHONPATH}"
# shellcheck disable=SC1091
source "$ROOT/scripts/launch/live-mode-guard.sh"
# A refusal exports AUREON_LIVE_TRADING=0 and AUREON_AUTONOMY_MODE=guarded.
live_mode_guard python3

if [ ! -x "$ROOT/.venv/bin/python" ]; then
  exec bash "$ROOT/production/install.sh"
fi

exec "$ROOT/.venv/bin/python" -m aureon.autonomous.aureon_master_launcher --preflight

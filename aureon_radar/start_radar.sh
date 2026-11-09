#!/usr/bin/env bash
# Thin wrapper. The canonical entry is python -m aureon.launch.master.
# This file does not copy .env and does not arm live trading.
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
PYTHON="${PYTHON:-python3}"
# shellcheck disable=SC1091
source "$ROOT/scripts/launch/live-mode-guard.sh"
# A refusal exports AUREON_LIVE_TRADING=0 and AUREON_AUTONOMY_MODE=guarded.
live_mode_guard "$PYTHON"
exec "$PYTHON" -m aureon.launch.master "$@"

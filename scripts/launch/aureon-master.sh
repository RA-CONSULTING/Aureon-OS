#!/usr/bin/env bash
# Canonical Aureon launcher for Linux and macOS.
# Live mode stays locked unless the stage 11 gate reports clear and
# AUREON_OPERATOR_ALLOW_LIVE is set.
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
PYTHON="${PYTHON:-python3}"
# shellcheck disable=SC1091
source "$ROOT/scripts/launch/live-mode-guard.sh"
# A refusal exports AUREON_LIVE_TRADING=0 and AUREON_AUTONOMY_MODE=guarded.
live_mode_guard "$PYTHON"
exec "$PYTHON" -m aureon.launch.master "$@"

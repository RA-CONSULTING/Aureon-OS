#!/usr/bin/env bash
# Rewrite measured/aureon_public_call_sweep.json. Do not hand-edit that file.
#
# Calls every entry point body_call can still run, with no arguments, one
# worker each. Sockets are blocked and logged. An entry point is refused when
# that call opens a connection or loads queen, miner, swarm_motion, inhouse_ai,
# ollama_config, or an HTTP client.
#
# This script places fake NEXUS-LIVE-FEED- and Aureon-Trading--Project-Sero
# checkouts beside the repo before the sweep, then removes the ones it created.
#
# Uses the venv from measured/aureon_public_stage1_run.sh when it is already
# present. Otherwise this script installs the same runtime and test requirements.
# Python 3.12 is required.
set -eu
ROOT="$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)"
VENV="${VENV:-/tmp/aureon-public-venv}"
OUT="${OUT:-$ROOT/measured/aureon_public_call_sweep.json}"
if [ ! -x "$VENV/bin/python" ]; then
  python3.12 -m venv "$VENV"
  "$VENV/bin/python" -m pip install -U pip
  "$VENV/bin/python" -m pip install -r "$ROOT/mcp/aureon_public/requirements.txt"
  "$VENV/bin/python" -m pip install -r "$ROOT/mcp/aureon_public/test-requirements.txt"
  "$VENV/bin/python" -m pip install -e "$ROOT/mcp" --no-deps
fi
"$VENV/bin/python" -m aureon_public.sweep_layout --plant
trap '"$VENV/bin/python" -m aureon_public.sweep_layout --cleanup' EXIT
env -u PYTHONPATH "$VENV/bin/python" -m aureon_public.call_sweep --out "$OUT"

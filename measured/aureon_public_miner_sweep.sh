#!/usr/bin/env bash
# Rewrite measured/aureon_public_miner_sweep.json. Do not hand-edit that file.
#
# Calls each miner function and method with no arguments. Sockets, process
# starts, and writes outside the temp parent are blocked and logged. Importing
# aureon.miner is the target. Queen, swarm_motion, inhouse_ai, ollama_config,
# an HTTP client, and the exchanges fence are refusals. No order is sent.
#
# This script does not rewrite measured/aureon_public_call_sweep.json.
# The checkout is copied under an ordinary temp parent. Fake NEXUS-LIVE-FEED-
# and Aureon-Trading--Project-Sero folders are placed beside that copy. The
# temp parent is removed when the script exits.
#
# Uses the venv from measured/aureon_public_stage1_run.sh when it is already
# present. Otherwise this script installs the same runtime and test requirements.
# Python 3.12 is required.
set -eu
ROOT="$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)"
VENV="${VENV:-/tmp/aureon-public-venv}"
OUT="${OUT:-$ROOT/measured/aureon_public_miner_sweep.json}"
if [ ! -x "$VENV/bin/python" ]; then
  python3.12 -m venv "$VENV"
  "$VENV/bin/python" -m pip install -U pip
  "$VENV/bin/python" -m pip install -r "$ROOT/mcp/aureon_public/requirements.txt"
  "$VENV/bin/python" -m pip install -r "$ROOT/mcp/aureon_public/test-requirements.txt"
  "$VENV/bin/python" -m pip install -e "$ROOT/mcp" --no-deps
fi
PARENT="$(mktemp -d "${TMPDIR:-/tmp}/aureon-miner-sweep-parent.XXXXXX")"
cleanup_parent() {
  rm -rf "$PARENT"
}
trap cleanup_parent EXIT
mkdir -p "$PARENT/Aureon-OS"
cp -a "$ROOT/." "$PARENT/Aureon-OS/"
PYTHONPATH="$PARENT/Aureon-OS/mcp" "$VENV/bin/python" -m aureon_public.sweep_layout --plant
env -u AUREON_PUBLIC_SWEEP -u AUREON_PUBLIC_MINER_SURFACE PYTHONPATH="$PARENT/Aureon-OS/mcp" \
  "$VENV/bin/python" -m aureon_public.miner_sweep --out "$OUT"

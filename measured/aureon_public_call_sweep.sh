#!/usr/bin/env bash
# Rewrite measured/aureon_public_call_sweep.json. Do not hand-edit that file.
#
# Calls every entry point body_call can still run, one worker each. Stage-2
# entry points are also called with the real arguments in stage2_arguments.py.
# SwarmAgent.update is also called with the hive fixture from
# tests/test_swarm_hive.py.
# Sockets, process starts, and writes outside the temp parent are blocked and
# logged. An entry point is refused when a call opens a connection, starts a
# process, writes outside that parent, or loads queen, miner, swarm_motion,
# inhouse_ai, ollama_config, or an HTTP client.
#
# The checkout is copied under an ordinary temp parent. Fake NEXUS-LIVE-FEED-
# and Aureon-Trading--Project-Sero folders are placed beside that copy. The
# temp parent is removed when the script exits. Nothing is created at the
# filesystem root.
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
PARENT="$(mktemp -d "${TMPDIR:-/tmp}/aureon-sweep-parent.XXXXXX")"
cleanup_parent() {
  rm -rf "$PARENT"
}
trap cleanup_parent EXIT
mkdir -p "$PARENT/Aureon-OS"
cp -a "$ROOT/." "$PARENT/Aureon-OS/"
PYTHONPATH="$PARENT/Aureon-OS/mcp" "$VENV/bin/python" -m aureon_public.sweep_layout --plant
env -u AUREON_PUBLIC_SWEEP PYTHONPATH="$PARENT/Aureon-OS/mcp" \
  "$VENV/bin/python" -m aureon_public.call_sweep --out "$OUT"

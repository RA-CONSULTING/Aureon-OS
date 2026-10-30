#!/usr/bin/env bash
# Rewrite measured/aureon_public_stage2_imports.json. Do not hand-edit that file.
#
# Each plan-stage-2 module is imported in its own process with sockets blocked.
# A module is refused when that import loads inhouse_ai, ollama_config, or an
# HTTP client, or when it opens a connection, starts a process, or writes
# outside the temp parent.
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
OUT="${OUT:-$ROOT/measured/aureon_public_stage2_imports.json}"
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
  "$VENV/bin/python" -m aureon_public.stage2_import_sweep --out "$OUT"

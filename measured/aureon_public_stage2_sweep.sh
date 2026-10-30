#!/usr/bin/env bash
# Rewrite measured/aureon_public_stage2_imports.json. Do not hand-edit that file.
#
# Each plan-stage-2 module is imported in its own process with sockets blocked.
# A module is refused when that import loads inhouse_ai, ollama_config, or an
# HTTP client, or when it opens a connection.
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
env -u PYTHONPATH "$VENV/bin/python" -m aureon_public.stage2_import_sweep --out "$OUT"

#!/usr/bin/env bash
# Rewrite measured/aureon_public_alignment.json and measured/aureon_public_stage1.json.
# Do not hand-edit those files.
#
# Same runtime install as measured/aureon_public_run.sh, plus the test file.
# Python 3.12 is required.
# This script installs mcp/aureon_public/requirements.txt and
# mcp/aureon_public/test-requirements.txt, then rewrites
# measured/aureon_public_alignment.json and measured/aureon_public_stage1.json.
# test-requirements.txt is pytest, pytest-timeout, flask, pandas, and scipy.
# It is not the public server runtime.
set -eu
ROOT="$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)"
VENV="${VENV:-/tmp/aureon-public-venv}"
WORK="${WORK:-/tmp/aureon-public-measure}"
ALIGN_OUT="${ALIGN_OUT:-$ROOT/measured/aureon_public_alignment.json}"
OUT="${OUT:-$ROOT/measured/aureon_public_stage1.json}"
python3.12 -m venv "$VENV"
"$VENV/bin/python" -m pip install -U pip
"$VENV/bin/python" -m pip install -r "$ROOT/mcp/aureon_public/requirements.txt"
"$VENV/bin/python" -m pip install -r "$ROOT/mcp/aureon_public/test-requirements.txt"
"$VENV/bin/python" -m pip install -e "$ROOT/mcp" --no-deps
mkdir -p "$WORK"
cd "$WORK"
env -u PYTHONPATH "$VENV/bin/python" -m aureon_public.alignment_measure --out "$ALIGN_OUT"
env -u PYTHONPATH "$VENV/bin/python" -m aureon_public.stage1_measure --out "$OUT"

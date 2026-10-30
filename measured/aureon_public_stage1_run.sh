#!/usr/bin/env bash
# Write the stage-1 measured records. Do not hand-edit those files.
#
# Same install as measured/aureon_public_run.sh. Python 3.12 is required.
# Regenerates the alignment record, then writes the remaining stage-1 record.
set -eu
ROOT="$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)"
VENV="${VENV:-/tmp/aureon-public-venv}"
WORK="${WORK:-/tmp/aureon-public-measure}"
ALIGN_OUT="${ALIGN_OUT:-$ROOT/measured/aureon_public_alignment.json}"
OUT="${OUT:-$ROOT/measured/aureon_public_stage1.json}"
python3.12 -m venv "$VENV"
"$VENV/bin/python" -m pip install -U pip
"$VENV/bin/python" -m pip install -r "$ROOT/mcp/aureon_public/requirements.txt"
"$VENV/bin/python" -m pip install -e "$ROOT/mcp" --no-deps
mkdir -p "$WORK"
cd "$WORK"
env -u PYTHONPATH "$VENV/bin/python" -m aureon_public.alignment_measure --out "$ALIGN_OUT"
env -u PYTHONPATH "$VENV/bin/python" -m aureon_public.stage1_measure --out "$OUT"

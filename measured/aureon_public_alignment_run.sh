#!/usr/bin/env bash
# Write measured/aureon_public_alignment.json. Do not hand-edit that file.
#
# Same install as measured/aureon_public_run.sh, then one stdio session that
# calls the alignment tools. Python 3.12 is required. 3.13 reindents docstrings.
#
# Environment:
# - Python 3.12 venv, created empty, outside the checkout
# - PYTHONPATH unset
# - working directory is an empty directory outside the checkout
# - aureon, mcp==1.30.0, and numpy come from mcp/aureon_public/requirements.txt
# - that aureon install is the git pin, and direct_url.json records the commit
# - aureon-public is an editable install of mcp/ so repo_root() still finds
#   this checkout. --no-deps leaves the pinned aureon in place
set -eu
ROOT="$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)"
VENV="${VENV:-/tmp/aureon-public-venv}"
WORK="${WORK:-/tmp/aureon-public-measure}"
OUT="${OUT:-$ROOT/measured/aureon_public_alignment.json}"
python3.12 -m venv "$VENV"
"$VENV/bin/python" -m pip install -U pip
"$VENV/bin/python" -m pip install -r "$ROOT/mcp/aureon_public/requirements.txt"
"$VENV/bin/python" -m pip install -e "$ROOT/mcp" --no-deps
mkdir -p "$WORK"
cd "$WORK"
env -u PYTHONPATH "$VENV/bin/python" -m aureon_public.alignment_measure --out "$OUT"

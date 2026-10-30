#!/usr/bin/env bash
# Write measured/aureon_public_space.json. Do not hand-edit that file.
#
# Starts python -m aureon_public.space on 127.0.0.1 with a bearer token
# generated in the process. The token is not written to the record.
# Docker is not used. The record says so when the machine has no Docker.
#
# code_commit in the record is the commit that was HEAD while the file was
# written. That commit is the parent of the commit that contains the record.
#
# Python 3.12 is required. The install matches measured/aureon_public_stage1_run.sh
# for the runtime: requirements.txt, then the mcp package with --no-deps.
set -eu
ROOT="$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)"
VENV="${VENV:-/tmp/aureon-public-venv}"
WORK="${WORK:-/tmp/aureon-public-measure}"
OUT="${OUT:-$ROOT/measured/aureon_public_space.json}"
python3.12 -m venv "$VENV"
"$VENV/bin/python" -m pip install -U pip
"$VENV/bin/python" -m pip install -r "$ROOT/mcp/aureon_public/requirements.txt"
"$VENV/bin/python" -m pip install -e "$ROOT/mcp" --no-deps
mkdir -p "$WORK"
cd "$WORK"
env -u PYTHONPATH "$VENV/bin/python" -m aureon_public.space_measure --out "$OUT"

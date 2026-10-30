#!/usr/bin/env bash
# Write measured/aureon_public_protocol.json. Do not hand-edit that file.
#
# Starts aureon-public over stdio and over Streamable HTTP bound to 127.0.0.1.
# AUREON_PUBLIC_REQUIRE_PIN=1 is set. The client is the MCP SDK client in the
# same venv. It calls tools/list, resources/list, prompts/list, and one
# tools/call (alignment_consonance_read, ratio 1.0).
#
# code_commit in the record is the commit that was HEAD while the file was
# written. That commit is the parent of the commit that contains the record.
# The record cannot name the commit that adds the file.
#
# Python 3.12 is required. 3.13 reindents docstrings.
#
# Environment:
# - Python 3.12 venv, created empty, outside the checkout
# - PYTHONPATH unset
# - working directory is an empty directory outside the checkout
# - aureon, mcp==1.30.0,<2, and numpy come from mcp/aureon_public/requirements.txt
# - that aureon install is the git pin, and direct_url.json records the commit
# - aureon-public is an editable install of mcp/ so repo_root() still finds
#   this checkout. --no-deps leaves the pinned aureon in place
set -eu
ROOT="$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)"
VENV="${VENV:-/tmp/aureon-public-venv}"
WORK="${WORK:-/tmp/aureon-public-measure}"
OUT="${OUT:-$ROOT/measured/aureon_public_protocol.json}"
python3.12 -m venv "$VENV"
"$VENV/bin/python" -m pip install -U pip
"$VENV/bin/python" -m pip install -r "$ROOT/mcp/aureon_public/requirements.txt"
"$VENV/bin/python" -m pip install -e "$ROOT/mcp" --no-deps
mkdir -p "$WORK"
cd "$WORK"
env -u PYTHONPATH AUREON_PUBLIC_REQUIRE_PIN=1 \
  "$VENV/bin/python" -m aureon_public.protocol_measure --out "$OUT"

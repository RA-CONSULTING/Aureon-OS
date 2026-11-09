#!/usr/bin/env bash
# Rewrite measured/aureon_public_queen_stage8.json. Do not hand-edit that file.
#
# Each Queen read runs in its own process. Sockets, process starts, and writes
# outside the sweep sandbox are blocked. The record is the measurement.
# This sweep opens no queen `body_call` entry beyond the `compute_zpe_ground` read already open in `stage34_gate`. Miner and exchanges are not called.
set -eu
ROOT="$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)"
OUT="${OUT:-$ROOT/measured/aureon_public_queen_stage8.json}"
PY="${PY:-python3.12}"
cd "$ROOT"
env -u AUREON_PUBLIC_SWEEP -u PYTHONPATH PYTHONPATH="$ROOT/mcp" \
  "$PY" -m aureon_public.queen_read_sweep --out "$OUT"

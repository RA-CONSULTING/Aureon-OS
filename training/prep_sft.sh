#!/bin/bash
# Convert the uploaded corpus into SFT jsonl on Isambard, using the container
# python (login node python3 is 3.6 and cannot run this).
set -euo pipefail

BASE=/projects/u6vs/hnc-organism
SIF="$BASE/containers/pytorch-25.05-py3.sif"
VENV="$BASE/venvs/aureon-sft"
CORPUS="$BASE/training/corpus"
OUT="$BASE/training/sft"

test -f "$CORPUS/files.jsonl" || { echo "missing $CORPUS/files.jsonl"; exit 2; }

mkdir -p "$OUT"
apptainer exec --bind /projects/u6vs:/projects/u6vs "$SIF" \
  "$VENV/bin/python" "$BASE/training/make_sft.py" --corpus "$CORPUS" --out "$OUT"

wc -l "$OUT/train.jsonl" "$OUT/eval.jsonl"
du -sh "$OUT"

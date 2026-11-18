#!/bin/bash
#SBATCH --job-name=aureon-tokenize
#SBATCH --account=brics.u6vs
#SBATCH --partition=workq
#SBATCH --nodes=1
#SBATCH --cpus-per-task=64
#SBATCH --mem=120000M
#SBATCH --time=24:00:00
#SBATCH --array=0-7
#SBATCH --no-requeue
#SBATCH --output=logs/%x-%A_%a.out

# Eight workers, one shared output tree, disjoint file sets. Each worker keeps
# its own index under tokens/worker_NN/ so no two processes ever write the same
# index file; pretrain.py merges the indexes at read time.
#
# Files are assigned by position modulo worker count, which is deterministic —
# so a worker that dies and is requeued recomputes the same assignment and its
# own index tells it what is already done.
#
# Measured 2026-10-27: one worker tokenised a 240 MB gzip shard into 316M tokens
# in 420 s (~0.76M tokens/s). The staged corpus is ~163B tokens, so eight
# workers is roughly 7 hours; more workers scale linearly until the login-side
# read bandwidth saturates.
set -euo pipefail

BASE=/projects/u6vs/hnc-organism
SIF=$BASE/containers/pytorch-25.05-py3.sif
VENV=$BASE/venvs/aureon-sft
TOK=$BASE/training/aureon_tokenizer.json
DATA=/projects/u6vs/pretrain/data
OUT=${OUT:-/projects/u6vs/pretrain/tokens}

mkdir -p "$OUT" "$BASE/logs"

echo "[tokenize] job=${SLURM_ARRAY_JOB_ID} task=${SLURM_ARRAY_TASK_ID} node=$(hostname)"

# Guard only what must exist on the compute node; never test -x the venv python.
test -f "$SIF"
test -f "$TOK"
test -d "$DATA"

exec apptainer exec --cleanenv \
    --bind /projects/u6vs:/projects/u6vs \
    --env PYTHONNOUSERSITE=1 \
    --env OMP_NUM_THREADS=8 \
    "$SIF" \
    "$VENV/bin/python" -u "$BASE/training/tokenize_corpus.py" \
        --tokenizer "$TOK" \
        --data "$DATA" \
        --out "$OUT" \
        --worker "$SLURM_ARRAY_TASK_ID" \
        --workers 8 \
        --shard-tokens 200000000

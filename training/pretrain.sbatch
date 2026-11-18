#!/bin/bash
#SBATCH --job-name=aureon-7b-pretrain
#SBATCH --account=brics.u6vs
#SBATCH --partition=workq
#SBATCH --nodes=1
#SBATCH --gpus-per-node=4
#SBATCH --cpus-per-task=64
#SBATCH --mem=240000M
#SBATCH --time=24:00:00
#SBATCH --no-requeue
#SBATCH --output=logs/%x-%j.out

# One node, four GH200s, 7B from random weights. Single node first: it proves
# the FSDP wrap, the shard reader and the throughput before any multi-node run
# is worth queueing. STEPS caps the run for a smoke test (STEPS=20 sbatch ...).
set -euo pipefail

BASE=/projects/u6vs/hnc-organism
SIF=$BASE/containers/pytorch-25.05-py3.sif
VENV=$BASE/venvs/aureon-sft
MODEL=$BASE/models/Qwen2.5-Coder-7B-Instruct
TOKENS=${TOKENS:-/projects/u6vs/pretrain/tokens}
OUT=${OUT:-$BASE/runs/aureon-7b-pretrain}
STEPS=${STEPS:-0}
SAVE_EVERY=${SAVE_EVERY:-1000}
BATCH=${BATCH:-2}
ACCUM=${ACCUM:-8}
TOK=${TOK:-$BASE/training/aureon_tokenizer.json}
RESUME=${RESUME:-}

mkdir -p "$BASE/runs" "$BASE/logs" "$OUT"

echo "[pretrain] job=${SLURM_JOB_ID} node=$(hostname) steps=${STEPS:-full}"
nvidia-smi -L | head -4

# Guard only what must exist on the compute node. Never test -x the venv
# interpreter: it is a symlink to /usr/bin/python, absent here, and under
# set -e that killed a job with two empty logs on 2026-10-26.
test -f "$SIF"
test -f "$MODEL/config.json"
# Tokenisation writes one index per worker (worker_NN/index.json) when it runs as
# an array; only a single-worker run leaves index.json at the root. Guarding on
# the root file alone killed job 7744443 one second in, before torchrun, with a
# log that ended at nvidia-smi and exit code 1. Accept either layout.
if ! compgen -G "$TOKENS/index.json" >/dev/null \
   && ! compgen -G "$TOKENS/worker_*/index.json" >/dev/null; then
    echo "[pretrain] no token index under $TOKENS" >&2
    exit 1
fi

exec apptainer exec --nv --cleanenv \
    --bind /projects/u6vs:/projects/u6vs \
    --env PYTHONPATH=$BASE/training \
    --env HF_HOME=$BASE/hf_cache \
    --env PYTHONNOUSERSITE=1 \
    --env OMP_NUM_THREADS=8 \
    --env TOKENIZERS_PARALLELISM=false \
    --env HF_HUB_OFFLINE=1 \
    --env TRANSFORMERS_OFFLINE=1 \
    "$SIF" \
    "$VENV/bin/python" -m torch.distributed.run --nproc_per_node=4 --master_port=29500 \
        "$BASE/training/pretrain.py" \
        --config-from "$MODEL" \
        --tokens "$TOKENS" \
        --out "$OUT" \
        --seq-len 4096 \
        --batch-size "$BATCH" \
        --grad-accum "$ACCUM" \
        --steps "$STEPS" \
        --save-every "$SAVE_EVERY" \
        --tokenizer "$TOK" \
        --resume "$RESUME" \
        --grad-checkpoint

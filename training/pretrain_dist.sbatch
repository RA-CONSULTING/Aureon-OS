#!/bin/bash
# Multi-node data-parallel pretraining of the 7B from-scratch model.
# Launch machinery mirrors train_dist.sbatch (srun one task per node, c10d
# rendezvous on the first allocation node); guards mirror pretrain.sbatch
# (NEVER test -x the venv interpreter: it is a dangling symlink on compute
# nodes and under set -e that killed a job before its first echo, leaving
# zero-byte logs).
#
# Scale-out is data-parallel over the token shards: identical weights on every
# rank, different data windows per rank, gradients all-reduced. Single node
# measured 21,199 tok/s (job 7751369). The first 2-node run of this script is
# a SCALING TEST (STEPS=10): report the measured tokens_per_s before N>2.
#
#   STEPS=10 SAVE_EVERY=100000 OUT=$PWD/../runs/aureon-7b-scaletest sbatch --nodes=2 pretrain_dist.sbatch
#   RESUME=auto OUT=$PWD/../runs/<real> sbatch --nodes=N pretrain_dist.sbatch
#
#SBATCH --job-name=aureon-7b-pretrain-dist
#SBATCH --account=brics.u6vs
#SBATCH --partition=workq
#SBATCH --nodes=2
#SBATCH --gpus-per-node=4
#SBATCH --cpus-per-task=64
#SBATCH --mem=240000M
#SBATCH --time=24:00:00
#SBATCH --no-requeue
#SBATCH --output=logs/%x-%j.out

set -euo pipefail

BASE=/projects/u6vs/hnc-organism
SIF=$BASE/containers/pytorch-25.05-py3.sif
VENV=$BASE/venvs/aureon-sft
MODEL=$BASE/models/Qwen2.5-Coder-7B-Instruct
TOKENS=${TOKENS:-/projects/u6vs/pretrain/tokens}
OUT=${OUT:-$BASE/runs/aureon-7b-pretrain-dist}
STEPS=${STEPS:-0}
SAVE_EVERY=${SAVE_EVERY:-1000}
BATCH=${BATCH:-8}
ACCUM=${ACCUM:-1}
TOK=${TOK:-$BASE/training/aureon_tokenizer.json}
RESUME=${RESUME:-}
KEEP=${KEEP:-20}
SHARD=${SHARD:-full}
# Job-derived port: a fixed port collides when two of these jobs overlap.
PORT=${PORT:-$((29100 + SLURM_JOB_ID % 2000))}

mkdir -p "$BASE/runs" "$BASE/logs" "$OUT"

NNODES=${SLURM_NNODES:-1}
MASTER=$(scontrol show hostnames "$SLURM_JOB_NODELIST" | head -1)

echo "[dist] job=${SLURM_JOB_ID} nodes=${NNODES} master=${MASTER} port=${PORT}"
echo "[dist] out=$OUT steps=${STEPS:-full} batch=$BATCH accum=$ACCUM resume=${RESUME:-none} keep=$KEEP shard=$SHARD"
nvidia-smi -L | head -4

test -f "$SIF"
test -f "$MODEL/config.json"
if ! compgen -G "$TOKENS/index.json" >/dev/null \
   && ! compgen -G "$TOKENS/worker_*/index.json" >/dev/null; then
    echo "[dist] no token index under $TOKENS" >&2
    exit 1
fi

srun --nodes="$NNODES" --ntasks="$NNODES" --ntasks-per-node=1 \
    apptainer exec --nv --cleanenv \
    --bind /projects/u6vs:/projects/u6vs \
    --env PYTHONPATH=$BASE/training \
    --env HF_HOME=$BASE/hf_cache \
    --env PYTHONNOUSERSITE=1 \
    --env OMP_NUM_THREADS=8 \
    --env TOKENIZERS_PARALLELISM=false \
    --env HF_HUB_OFFLINE=1 \
    --env TRANSFORMERS_OFFLINE=1 \
    --env NCCL_DEBUG=WARN \
    "$SIF" \
    "$VENV/bin/python" -m torch.distributed.run \
      --nnodes="$NNODES" \
      --nproc_per_node=4 \
      --rdzv_backend=c10d \
      --rdzv_endpoint="$MASTER:$PORT" \
      --rdzv_id="$SLURM_JOB_ID" \
      --tee 3 \
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
      --keep "$KEEP" \
      --shard "$SHARD" \
      --grad-checkpoint
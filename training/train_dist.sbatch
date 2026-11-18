#!/bin/bash
# Multi-node data-parallel launch: every node takes a different slice of the
# corpus, computes gradients from it, and the gradients are all-reduced into
# ONE set of weights. That all-reduce is literally "each gives back what it
# made" — nothing is stitched together afterwards, because the nodes never
# produce separate model pieces. They produce pieces of the same update.
#
# Sized for the 32B path. For the 7B, prefer train_lora.sbatch on ONE node:
# 15.23 GB of bf16 weights fits inside a single 96 GB GH200, so spreading the
# layers across nodes would add interconnect traffic and buy nothing.
#
#   sbatch --nodes=2 training/train_dist.sbatch
#
# /projects is shared across all nodes, so corpus, venv and weights are
# already visible everywhere — no per-node staging step is needed.
#
#SBATCH --job-name=aureon-dist
#SBATCH --account=brics.u6vs
#SBATCH --partition=workq
#SBATCH --nodes=2
#SBATCH --gpus-per-node=4
#SBATCH --cpus-per-task=288
#SBATCH --mem=115000M
#SBATCH --time=04:00:00
#SBATCH --no-requeue
#SBATCH --output=/projects/u6vs/hnc-organism/logs/%x-%j.out
#SBATCH --error=/projects/u6vs/hnc-organism/logs/%x-%j.err

set -euo pipefail

BASE=/projects/u6vs/hnc-organism
SIF="$BASE/containers/pytorch-25.05-py3.sif"
VENV="$BASE/venvs/aureon-sft"
MODEL="${MODEL:-$BASE/models/Qwen2.5-Coder-7B-Instruct}"
DATA="$BASE/training/sft"
OUT="${OUT:-$BASE/runs/dist-$(basename "$MODEL")}"
PORT="${PORT:-29500}"

test -x "$VENV/bin/python"
test -f "$MODEL/config.json"
test -f "$DATA/train.jsonl"

# First node in the allocation hosts the rendezvous store the others join.
MASTER=$(scontrol show hostnames "$SLURM_JOB_NODELIST" | head -1)
NNODES="${SLURM_NNODES:-1}"
mkdir -p "$OUT" "$BASE/logs"

echo "[dist] nodes=${NNODES} master=${MASTER} port=${PORT}"
echo "[dist] model=${MODEL}"
echo "[dist] world_size=$((NNODES * 4))"
nvidia-smi -L || true

srun --nodes="$NNODES" --ntasks="$NNODES" --ntasks-per-node=1 \
  apptainer exec --nv --cleanenv \
  --bind /projects/u6vs:/projects/u6vs \
  --env HF_HOME="$BASE/hf" \
  --env PYTHONNOUSERSITE=1 \
  --env OMP_NUM_THREADS=8 \
  --env TOKENIZERS_PARALLELISM=false \
  --env NCCL_DEBUG=WARN \
  --env MASTER_ADDR="$MASTER" \
  --env MASTER_PORT="$PORT" \
  "$SIF" \
  "$VENV/bin/python" -m torch.distributed.run \
    --nnodes="$NNODES" \
    --nproc_per_node=4 \
    --rdzv_backend=c10d \
    --rdzv_endpoint="$MASTER:$PORT" \
    --rdzv_id="$SLURM_JOB_ID" \
    --tee 3 \
    "$BASE/training/train_lora.py" \
    --model "$MODEL" \
    --data "$DATA" \
    --out "$OUT" \
    --max-seq-length 4096 \
    --epochs 1 \
    --batch-size 2 \
    --grad-accum 8 \
    --lr 1e-4

echo "[dist] done -> $OUT/adapter"

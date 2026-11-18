#!/bin/bash
# Hyperparameter sweep across 4 nodes — the one form of "max out the cluster"
# that actually uses extra nodes well, because the arms are independent.
#
# Do NOT expect this to make a single model appear faster: one arm is still
# ~1.5-2 h, and the arms do not chain. Their value is picking the best config
# on the first pass instead of guessing, so generation 2 starts from a better
# base. Submit only after the Slurm controller is confirmed UP.
#
#   sbatch training/sweep.sbatch
#   squeue -u $USER
#
#SBATCH --job-name=aureon-sweep
#SBATCH --account=brics.u6vs
#SBATCH --partition=workq
#SBATCH --nodes=1
#SBATCH --gpus-per-node=4
#SBATCH --cpus-per-task=288
#SBATCH --mem=115000M
#SBATCH --time=06:00:00
#SBATCH --no-requeue
#SBATCH --array=0-3
#SBATCH --output=/projects/u6vs/hnc-organism/logs/%x-%A_%a.out
#SBATCH --error=/projects/u6vs/hnc-organism/logs/%x-%A_%a.err

set -euo pipefail

BASE=/projects/u6vs/hnc-organism
SIF="$BASE/containers/pytorch-25.05-py3.sif"
VENV="$BASE/venvs/aureon-sft"
MODEL="$BASE/models/Qwen2.5-Coder-7B-Instruct"
DATA="$BASE/training/sft"

# arm : lora_r : lora_alpha : lr
case "${SLURM_ARRAY_TASK_ID}" in
  0) RANK=16; ALPHA=32;  LR=2e-4 ;;
  1) RANK=32; ALPHA=64;  LR=1e-4 ;;
  2) RANK=64; ALPHA=128; LR=5e-5 ;;
  3) RANK=32; ALPHA=64;  LR=2e-4 ;;
  *) echo "unexpected array index ${SLURM_ARRAY_TASK_ID}"; exit 2 ;;
esac

OUT="$BASE/runs/sweep-r${RANK}-lr${LR}"

test -x "$VENV/bin/python"
test -f "$MODEL/config.json"
test -f "$DATA/train.jsonl"

echo "[sweep] task=${SLURM_ARRAY_TASK_ID} rank=${RANK} lr=${LR} out=${OUT}"
nvidia-smi -L || true

apptainer exec --nv --cleanenv \
  --bind /projects/u6vs:/projects/u6vs \
  --env HF_HOME="$BASE/hf" \
  --env PYTHONNOUSERSITE=1 \
  --env OMP_NUM_THREADS=8 \
  --env TOKENIZERS_PARALLELISM=false \
  --env NCCL_DEBUG=WARN \
  --env MASTER_ADDR=127.0.0.1 \
  "$SIF" \
  "$VENV/bin/python" -m torch.distributed.run \
    --nproc_per_node=4 \
    --tee 3 \
    "$BASE/training/train_lora.py" \
    --model "$MODEL" \
    --data "$DATA" \
    --out "$OUT" \
    --max-seq-length 4096 \
    --epochs 1 \
    --batch-size 2 \
    --grad-accum 8 \
    --lr "$LR" \
    --lora-r "$RANK" \
    --lora-alpha "$ALPHA"

echo "[sweep] task=${SLURM_ARRAY_TASK_ID} done -> $OUT/adapter"

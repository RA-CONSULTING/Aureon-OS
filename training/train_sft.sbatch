#!/bin/bash
# Supervised fine-tune of the from-scratch Aureon checkpoint on sft/train.jsonl.
# Mirrors pretrain.sbatch guards: never test -x the venv interpreter (dangling
# symlink on compute nodes), python comes from the NGC container, torchrun is
# python -m torch.distributed.run.
#
#   sbatch train_sft.sbatch                       # full run, 3 epochs, 24 h budget
#   MAX_SAMPLES=2000 EPOCHS=1                     # quick smoke before trusting
#
#SBATCH --job-name=aureon-7b-sft
#SBATCH --account=brics.u6vs
#SBATCH --partition=workq
#SBATCH --nodes=1
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
CKPT=${CKPT:-$BASE/runs/aureon-7b-v65k/latest.json}
DATA=${DATA:-$BASE/training/sft/train.jsonl}
OUT=${OUT:-$BASE/runs/aureon-7b-sft}
SEQ=${SEQ:-4096}
BATCH=${BATCH:-2}
ACCUM=${ACCUM:-8}
EPOCHS=${EPOCHS:-3}
LR=${LR:-2e-5}
MAX_SAMPLES=${MAX_SAMPLES:-0}
SAVE_EVERY=${SAVE_EVERY:-200}

test -f "$SIF"
test -f "$MODEL/config.json"
test -f "$DATA" || test -f "$BASE/training/sft/train.jsonl"
test -f "$CKPT"

mkdir -p "$BASE/runs" "$BASE/logs" "$OUT"
echo "[sft] job=${SLURM_JOB_ID} node=$(hostname) ckpt=$CKPT data=$DATA out=$OUT"
nvidia-smi -L | head -4

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
    "$VENV/bin/python" -m torch.distributed.run --nproc_per_node=4 --master_port=29700 \
        "$BASE/training/train_sft.py" \
        --config-from "$MODEL" \
        --tokenizer "$BASE/training/aureon_tokenizer.json" \
        --ckpt "$CKPT" \
        --data "$DATA" \
        --out "$OUT" \
        --seq-len "$SEQ" \
        --batch-size "$BATCH" \
        --grad-accum "$ACCUM" \
        --epochs "$EPOCHS" \
        --lr "$LR" \
        --save-every "$SAVE_EVERY" \
        --max-samples "$MAX_SAMPLES" \
        --grad-checkpoint

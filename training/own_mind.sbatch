#!/bin/bash
# One self-contained mind cycle: Aureon weights, then the Auris vote,
# then a continuation from those same weights. No network, no other model.
#SBATCH --job-name=aureon-own-mind
#SBATCH --account=brics.u6vs
#SBATCH --partition=workq
#SBATCH --nodes=1
#SBATCH --gpus-per-node=1
#SBATCH --cpus-per-task=16
#SBATCH --mem=120000M
#SBATCH --time=00:40:00
#SBATCH --no-requeue
#SBATCH --output=logs/%x-%j.out

set -euo pipefail

BASE=/projects/u6vs/hnc-organism
SIF=$BASE/containers/pytorch-25.05-py3.sif
VENV=$BASE/venvs/aureon-sft
MODEL=${MODEL:-$BASE/runs/aureon-7b-v65k/hf}
OUT=${OUT:-$BASE/runs/aureon-7b-v65k/own-mind-latest.json}

echo "[own-mind] job=${SLURM_JOB_ID} node=$(hostname) model=$MODEL"

exec apptainer exec --nv --cleanenv \
    --bind /projects/u6vs:/projects/u6vs \
    --env PYTHONNOUSERSITE=1 \
    --env HF_HUB_OFFLINE=1 \
    --env TRANSFORMERS_OFFLINE=1 \
    "$SIF" \
    "$VENV/bin/python" -u "$BASE/training/own_mind.py" \
        --model "$MODEL" \
        --out "$OUT"

#!/bin/bash
#SBATCH --job-name=aureon-sample
#SBATCH --account=brics.u6vs
#SBATCH --partition=workq
#SBATCH --nodes=1
#SBATCH --gpus-per-node=1
#SBATCH --cpus-per-task=16
#SBATCH --mem=120000M
#SBATCH --time=00:30:00
#SBATCH --no-requeue
#SBATCH --output=logs/%x-%j.out

# Loading the exported checkpoint killed the session on the login node twice
# (silent container death, then a connection reset), so the acceptance test runs
# where the memory and the GPU both exist.
set -euo pipefail

BASE=/projects/u6vs/hnc-organism
SIF=$BASE/containers/pytorch-25.05-py3.sif
VENV=$BASE/venvs/aureon-sft
MODEL=${MODEL:-$BASE/runs/aureon-7b-v65k/hf}
PROMPT=${PROMPT:-def main(argv):}

echo "[sample] job=${SLURM_JOB_ID} node=$(hostname) model=$MODEL"

exec apptainer exec --nv --cleanenv \
    --bind /projects/u6vs:/projects/u6vs \
    --env PYTHONNOUSERSITE=1 \
    --env HF_HUB_OFFLINE=1 \
    --env TRANSFORMERS_OFFLINE=1 \
    "$SIF" \
    "$VENV/bin/python" -u "$BASE/training/sample_model.py" \
        --model "$MODEL" \
        --prompt "$PROMPT" \
        --max-new-tokens 40

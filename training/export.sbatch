#!/bin/bash
#SBATCH --job-name=aureon-export
#SBATCH --account=brics.u6vs
#SBATCH --partition=workq
#SBATCH --nodes=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=200000M
#SBATCH --time=01:00:00
#SBATCH --no-requeue
#SBATCH --output=logs/%x-%j.out

# The export needs the whole 42 GB state dict resident plus a 14 GB write buffer.
# Run on the login node it was killed silently — the workq node has 460 GB and
# makes the peak memory a non-issue. No --nv: this job never touches a GPU.
set -euo pipefail

BASE=/projects/u6vs/hnc-organism
SIF=$BASE/containers/pytorch-25.05-py3.sif
VENV=$BASE/venvs/aureon-sft
CKPT=${CKPT:-$BASE/runs/aureon-7b-v65k/ckpt_0000030.pt}
OUT=${OUT:-$BASE/runs/aureon-7b-v65k/hf}

echo "[export] job=${SLURM_JOB_ID} node=$(hostname) ckpt=$CKPT"

exec apptainer exec --cleanenv \
    --bind /projects/u6vs:/projects/u6vs \
    --env PYTHONNOUSERSITE=1 \
    "$SIF" \
    "$VENV/bin/python" -u "$BASE/training/export_hf.py" \
        --ckpt "$CKPT" \
        --config-from "$BASE/models/Qwen2.5-Coder-7B-Instruct" \
        --tokenizer "$BASE/training/aureon_tokenizer.json" \
        --out "$OUT"

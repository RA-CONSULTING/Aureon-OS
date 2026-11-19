#!/bin/bash
# Score the SFT'd own model on the full Aureon holdout under the chat-server
# prompt (--raw). The honest end-to-end number to put next to eval-base.json
# and eval-17k-quick.json: has SFT actually taught the model the format?
#
#   sbatch training/eval_sft.sbatch
#
#SBATCH --job-name=aureon-eval-sft
#SBATCH --account=brics.u6vs
#SBATCH --partition=workq
#SBATCH --nodes=1
#SBATCH --gpus-per-node=4
#SBATCH --cpus-per-task=64
#SBATCH --mem=115000M
#SBATCH --time=06:00:00
#SBATCH --no-requeue
#SBATCH --output=logs/%x-%j.out

set -euo pipefail

BASE=/projects/u6vs/hnc-organism
SIF="$BASE/containers/pytorch-25.05-py3.sif"
VENV="$BASE/venvs/aureon-sft"
MODEL=${MODEL:-$BASE/runs/aureon-7b-sft/hf}
DATA="$BASE/training/sft/eval.jsonl"
OUT=${OUT:-$BASE/runs/eval-sft.json}

test -f "$SIF"
test -f "$MODEL/config.json"
test -f "$DATA"

mkdir -p "$BASE/runs" "$BASE/logs"
echo "[eval-sft] job=${SLURM_JOB_ID} node=$(hostname) model=$MODEL"
nvidia-smi -L || true

cd "$BASE/training"
run() {
    apptainer exec --nv --cleanenv \
      --bind /projects/u6vs:/projects/u6vs \
      --env HF_HOME="$BASE/hf_cache" \
      --env PYTHONNOUSERSITE=1 \
      --env PYTHONPATH="$BASE/training" \
      --env OMP_NUM_THREADS=8 \
      --env TOKENIZERS_PARALLELISM=false \
      --env HF_HUB_OFFLINE=1 \
      --env TRANSFORMERS_OFFLINE=1 \
      "$SIF" "$VENV/bin/python" -u eval_gate.py "$@"
}

run self-test
run run \
    --model "$MODEL" \
    --data "$DATA" \
    --out "$OUT" \
    --raw \
    --batch-size 8 \
    --max-prompt-tokens 2048 \
    --max-new-tokens 1024

echo "[eval-sft] done -> $OUT"

#!/bin/bash
# Score the untuned base model on the Aureon holdout — the reference number a
# future adapter has to beat.
#
# No --adapter is passed. eval_gate.py scores with objective metrics only
# (parse rate, symbol recall, line F1), so a baseline stands on its own, and
# the eventual comparison is then just:
#   eval_gate.py compare --base runs/eval-base.json --tuned runs/eval-tuned.json
#
# Compute nodes have no outbound network, so the HF offline flags are required:
# without them transformers probes the Hub for a model that is already on disk
# and blocks until the probe times out.
#
#   sbatch training/eval_baseline.sbatch
#   squeue -u $USER
#
#SBATCH --job-name=aureon-eval-base
#SBATCH --account=brics.u6vs
#SBATCH --partition=workq
#SBATCH --nodes=1
#SBATCH --gpus-per-node=4
#SBATCH --cpus-per-task=64
#SBATCH --mem=115000M
#SBATCH --time=06:00:00
#SBATCH --no-requeue
#SBATCH --output=/projects/u6vs/hnc-organism/logs/%x-%j.out
#SBATCH --error=/projects/u6vs/hnc-organism/logs/%x-%j.err

set -euo pipefail

BASE=/projects/u6vs/hnc-organism
SIF="$BASE/containers/pytorch-25.05-py3.sif"
VENV="$BASE/venvs/aureon-sft"
MODEL="$BASE/models/Qwen2.5-Coder-7B-Instruct"
DATA="$BASE/training/sft/eval.jsonl"
OUT="$BASE/runs/eval-base.json"

mkdir -p "$BASE/runs" "$BASE/logs"

echo "[eval] job=${SLURM_JOB_ID} node=$(hostname) rows=$(wc -l < "$DATA")"

# Check only paths that must exist on the compute node. Do NOT test -x on
# "$VENV/bin/python": it is a symlink to /usr/bin/python, which exists on the
# login node but not on compute nodes, so that guard failed here and sent the
# job to exit 1 with a completely empty log on 2026-10-26.
test -f "$SIF"
test -f "$MODEL/config.json"
test -f "$DATA"

cd "$BASE/training"
nvidia-smi -L || true

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

# Confirm the scorer itself is sound before spending GPU time on 1,125 rows.
run self-test

run run \
    --model "$MODEL" \
    --data "$DATA" \
    --out "$OUT" \
    --batch-size 8 \
    --max-prompt-tokens 2048 \
    --max-new-tokens 1024

echo "[eval] done -> $OUT"

#!/bin/bash
# Probe the current from-scratch checkpoint: pin it, export to HF, sample, and
# score a quick eval subset. Points at ckpt_0017000.pt via a PINNED copy so the
# keep=20 rolling policy (which deletes the 21st-oldest on the next pretrain
# save) cannot eat it mid-probe.
#
#   sbatch probe17k.sbatch
#
#SBATCH --job-name=aureon-probe-17k
#SBATCH --account=brics.u6vs
#SBATCH --partition=workq
#SBATCH --nodes=1
#SBATCH --gpus-per-node=4
#SBATCH --cpus-per-task=64
#SBATCH --mem=240000M
#SBATCH --time=03:00:00
#SBATCH --no-requeue
#SBATCH --output=logs/%x-%j.out

set -euo pipefail

BASE=/projects/u6vs/hnc-organism
SIF=$BASE/containers/pytorch-25.05-py3.sif
VENV=$BASE/venvs/aureon-sft
RUN=$BASE/runs/aureon-7b-v65k
CKPT=$RUN/ckpt_0017000.pt
PINNED=$RUN/pinned/ckpt_0017000.pt
HF17K=$RUN/hf-17k
DATA=$BASE/training/sft/eval.jsonl
OUT=$BASE/runs/eval-17k-quick.json
LIMIT=${LIMIT:-120}

test -f "$SIF"
test -f "$CKPT"
test -f "$DATA"

mkdir -p "$RUN/pinned" "$BASE/runs" "$BASE/logs"
if [ ! -f "$PINNED" ]; then
    echo "[probe] pinning $CKPT -> $PINNED"
    cp "$CKPT" "$PINNED"
fi
echo "[probe] job=${SLURM_JOB_ID} node=$(hostname)"
nvidia-smi -L | head -4

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
      "$SIF" "$VENV/bin/python" -u "$@"
}

# 1. Export the pinned checkpoint (CPU-heavy, 200 GB resident on this node).
echo "[probe] exporting -> $HF17K"
run "$BASE/training/export_hf.py" \
    --ckpt "$PINNED" \
    --config-from "$BASE/models/Qwen2.5-Coder-7B-Instruct" \
    --tokenizer "$BASE/training/aureon_tokenizer.json" \
    --out "$HF17K"

# 2. Eyes-on generation through the chat-server prompt contract.
echo "[probe] sampling"
run "$BASE/training/sample_model.py" \
    --model "$HF17K" \
    --prompt "system: You are Aureon, a coding agent working inside the Aureon-OS repository. You write Python that matches the repository's existing module layout, type hints, and docstring conventions.
user: Write the Python module aureon_systems/aureon_lattice_simulation.py in the Aureon-OS repository.
assistant:" \
    --max-new-tokens 200 || echo "[probe] sample failed (non-fatal)"

# 3. Gate scorer sanity, then the quick subset under the RAW chat prompt.
echo "[probe] eval_gate self-test"
run "$BASE/training/eval_gate.py" self-test
echo "[probe] quick eval (limit=$LIMIT, raw prompts)"
run "$BASE/training/eval_gate.py" run \
    --model "$HF17K" \
    --data "$DATA" \
    --out "$OUT" \
    --raw \
    --limit "$LIMIT" \
    --batch-size 8 \
    --max-prompt-tokens 2048 \
    --max-new-tokens 1024

echo "[probe] done -> $OUT"

#!/bin/bash
# LoRA SFT for Aureon on 1x GH200 node (4 GPUs).
# Submission is intentionally manual: no auto-requeue, no resubmit loops.
#SBATCH --job-name=aureon-sft
#SBATCH --account=brics.u6vs
#SBATCH --partition=workq
#SBATCH --nodes=1
#SBATCH --gpus-per-node=4
#SBATCH --cpus-per-task=288
#SBATCH --mem=115000M
#SBATCH --time=08:00:00
#SBATCH --no-requeue
#SBATCH --output=/projects/u6vs/hnc-organism/logs/%x-%j.out
#SBATCH --error=/projects/u6vs/hnc-organism/logs/%x-%j.err

set -euo pipefail

BASE=/projects/u6vs/hnc-organism
SIF="$BASE/containers/pytorch-25.05-py3.sif"
VENV="$BASE/venvs/aureon-sft"
MODEL="$BASE/models/Qwen2.5-Coder-7B-Instruct"
DATA="$BASE/training/sft"
OUT="${OUT:-$BASE/runs/aureon-sft-7b}"
LIMIT="${LIMIT:-0}"
EPOCHS="${EPOCHS:-1}"
MAXLEN="${MAXLEN:-4096}"

test -x "$VENV/bin/python"
test -f "$SIF"
test -f "$MODEL/config.json"
test -f "$DATA/train.jsonl"

mkdir -p "$OUT" "$BASE/logs"

echo "[sbatch] host=$(hostname) job=${SLURM_JOB_ID:-local}"
echo "[sbatch] model=$MODEL limit=$LIMIT epochs=$EPOCHS maxlen=$MAXLEN"
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
    --max-seq-length "$MAXLEN" \
    --epochs "$EPOCHS" \
    --batch-size 2 \
    --grad-accum 8 \
    --lr 1e-4 \
    --limit "$LIMIT"

echo "[sbatch] done -> $OUT/adapter"

# Acceptance gate, run inside the same allocation: score the base model and the
# adapter on the held-out split and print a shippable verdict. A FAIL leaves the
# job green because the adapter is still saved — the log carries the verdict.
EVAL="$DATA/eval.jsonl"
GATE_ROWS="${GATE_ROWS:-24}"
GATE_TOKENS="${GATE_TOKENS:-768}"

gate() {
  local report="$1"; shift
  apptainer exec --nv --cleanenv \
    --bind /projects/u6vs:/projects/u6vs \
    --env HF_HOME="$BASE/hf" \
    --env PYTHONNOUSERSITE=1 \
    --env TOKENIZERS_PARALLELISM=false \
    "$SIF" "$VENV/bin/python" "$BASE/training/eval_gate.py" run \
      --model "$MODEL" --data "$EVAL" --limit "$GATE_ROWS" \
      --max-new-tokens "$GATE_TOKENS" --batch-size 4 --out "$report" "$@"
}

if [ -f "$OUT/adapter/adapter_config.json" ] && [ -f "$EVAL" ]; then
  mkdir -p "$OUT/gate"
  echo "[gate] scoring base on $GATE_ROWS held-out rows"
  gate "$OUT/gate/base.json"
  echo "[gate] scoring tuned"
  gate "$OUT/gate/tuned.json" --adapter "$OUT/adapter"
  echo "[gate] comparing"
  if ! apptainer exec --cleanenv --bind /projects/u6vs:/projects/u6vs "$SIF" \
      "$VENV/bin/python" "$BASE/training/eval_gate.py" compare \
        --base "$OUT/gate/base.json" --tuned "$OUT/gate/tuned.json" --min-gain 0.05; then
    echo "[gate] VERDICT: FAIL - adapter trained but did not clear the threshold"
  fi
fi

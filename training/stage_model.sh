#!/bin/bash
# Pull the base coding model onto project storage.
#
# Compute nodes have no internet, so this runs on the login node — where the
# per-user memory cgroup is tight. Therefore: plain HTTP (xet disabled) and a
# single worker. huggingface-cli resumes whatever partial shards already exist.
set -euo pipefail

BASE=/projects/u6vs/hnc-organism
SIF="$BASE/containers/pytorch-25.05-py3.sif"
VENV="$BASE/venvs/aureon-sft"
BIND="--bind /projects/u6vs:/projects/u6vs"
MODEL="${1:-Qwen/Qwen2.5-Coder-7B-Instruct}"
DEST="$BASE/models/$(basename "$MODEL")"

export HF_HOME="$BASE/hf"
export PYTHONNOUSERSITE=1
export HF_HUB_DISABLE_XET=1
export HF_HUB_ENABLE_HF_TRANSFER=0
mkdir -p "$BASE/models" "$HF_HOME"

echo "[model] target: $DEST (resuming if partial)"

apptainer exec $BIND "$SIF" \
  "$VENV/bin/huggingface-cli" download "$MODEL" \
  --local-dir "$DEST" \
  --max-workers 1

echo "[model] verifying load"
apptainer exec $BIND "$SIF" "$VENV/bin/python" - "$DEST" <<'PY'
import sys, os, json
from transformers import AutoConfig, AutoTokenizer

dest = sys.argv[1]
cfg = AutoConfig.from_pretrained(dest)
tok = AutoTokenizer.from_pretrained(dest)
shards = [f for f in os.listdir(dest) if f.endswith(".safetensors")]
total = sum(os.path.getsize(os.path.join(dest, f)) for f in shards)
print("[model] arch     ", cfg.architectures)
print("[model] vocab    ", tok.vocab_size)
print("[model] shards   ", len(shards), f"{total/1e9:.2f} GB")
idx = os.path.join(dest, "model.safetensors.index.json")
if os.path.exists(idx):
    meta = json.load(open(idx))["metadata"]["total_size"]
    print("[model] bytes    ", f"{meta/1e9:.2f} GB of bf16 weights")
    print("[model] params   ", f"{meta/2/1e9:.2f}B  (bf16 => 2 bytes/param)")
PY

echo "[model] done"

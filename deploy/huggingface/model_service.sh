#!/usr/bin/env bash
# Verify the immutable Hub snapshot before starting the loopback model server.
set -euo pipefail

ROOT=/app/aureon-os
PYTHON=/usr/local/bin/python
export PYTHONPATH="$ROOT${PYTHONPATH:+:$PYTHONPATH}"

if [ "${AUREON_MODEL_DISABLED:-0}" = "1" ]; then
  # The pinned revision is unknown, so nothing may be downloaded or loaded. Hold
  # this program in a documented idle state instead of exiting: a dead required
  # program would fail the container health contract for an optional capability.
  echo "[model] inference disabled: no pinned AUREON_MODEL_REVISION; holding idle" >&2
  exec sleep infinity
fi

export HF_HUB_OFFLINE=0
export TRANSFORMERS_OFFLINE=0
export HF_DATASETS_OFFLINE=0

"$PYTHON" -u "$ROOT/deploy/huggingface/model_bootstrap.py" \
  --model-dir "$AUREON_MODEL_DIR" \
  --revision "$AUREON_MODEL_REVISION" \
  --receipt "$AUREON_RUNTIME_DIR/model-download-receipt.json"

# The model directory is now local and verified. Neither load nor inference may
# contact the Hub or replace the pinned revision.
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
export HF_DATASETS_OFFLINE=1
# A GPU is optional. The console, HNC evidence, and the repository tree are
# public on CPU hardware; the checkpoint is ~1.17B parameters and loads in bf16
# on either device. Requiring CUDA made every CPU Space permanently unhealthy:
# the supervisor treated this program as dead and strict readiness could never
# pass. Demand CUDA only when the Space was actually given a GPU.
DEVICE_ARGS=()
if command -v nvidia-smi >/dev/null 2>&1 && nvidia-smi -L >/dev/null 2>&1; then
  DEVICE_ARGS+=(--require-cuda)
else
  echo "[model] no GPU detected; serving inference on CPU (GPU is an optional upgrade)" >&2
fi

exec "$PYTHON" -u "$ROOT/training/aureon_chat_server.py" \
  --model "$AUREON_MODEL_DIR" \
  --model-name aureon-7b-v65k \
  --host 127.0.0.1 \
  --port 11435 \
  "${DEVICE_ARGS[@]}" \
  --strict-startup \
  --expected-weight-sha256 48487f800623474ab99371d71b369694cae64f8ebc4ef038019c7e60da3d45bb \
  --expected-weight-size 13990806664 \
  --model-revision "$AUREON_MODEL_REVISION"

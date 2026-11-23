#!/usr/bin/env bash
# Verify the immutable Hub snapshot before starting the loopback model server.
set -euo pipefail

ROOT=/app/aureon-os
PYTHON=/usr/local/bin/python
export PYTHONPATH="$ROOT${PYTHONPATH:+:$PYTHONPATH}"
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
exec "$PYTHON" -u "$ROOT/training/aureon_chat_server.py" \
  --model "$AUREON_MODEL_DIR" \
  --model-name aureon-7b-v65k \
  --host 127.0.0.1 \
  --port 11435 \
  --require-cuda \
  --strict-startup \
  --expected-weight-sha256 48487f800623474ab99371d71b369694cae64f8ebc4ef038019c7e60da3d45bb \
  --expected-weight-size 13990806664 \
  --model-revision "$AUREON_MODEL_REVISION"

#!/bin/bash
# Put the Aureon checkpoint through the existing HNC-5000 worker in pilot mode.
# The worker, pack, pin, and gates are unchanged. The only substitution is the
# model behind http://127.0.0.1:8000/v1: aureon-7b-v65k, not gpt-oss-120b.
#SBATCH --job-name=aureon-hnc5k-pilot
#SBATCH --account=brics.u6vs
#SBATCH --partition=workq
#SBATCH --nodes=1
#SBATCH --gpus-per-node=1
#SBATCH --cpus-per-task=16
#SBATCH --mem=120000M
#SBATCH --time=04:00:00
#SBATCH --no-requeue
#SBATCH --output=/projects/u6vs/hnc-organism/training/logs/%x-%j.out
#SBATCH --error=/projects/u6vs/hnc-organism/training/logs/%x-%j.err

set -euo pipefail
umask 007

BASE=/projects/u6vs/hnc-organism
SIF=$BASE/containers/pytorch-25.05-py3.sif
VENV=$BASE/venvs/aureon-sft
MODEL=${MODEL:-$BASE/runs/aureon-7b-v65k/hf}
MODEL_NAME=${MODEL_NAME:-aureon-7b-v65k}
PACK=$BASE/kimi-validation/hnc-5000/pack-v2
PIN=f5fb1916c07ac26eb7fc38c34ff2dc9bd029e21d
REPO=$BASE/jobs/aureon-whole-organism/pinned/$PIN
PUBLIC_ROOT=$PACK/public_sources
ORGANISM_PACK=$BASE/jobs/aureon-whole-organism
PUBLIC_PY=/projects/public/brics/tutorials/distributed_vllm/.venv/bin/python
VENDOR_WHEEL=$PACK/vendor/wheels/pypdf-6.16.2-py3-none-any.whl
RUN_DIR=$BASE/kimi-validation/hnc-5000/runs/aureon-hnc5000-pilot-${SLURM_JOB_ID}

mkdir -p "$RUN_DIR/tmp"
export TMPDIR=$RUN_DIR/tmp
export TORCHINDUCTOR_CACHE_DIR=$RUN_DIR/torchinductor-cache
export TRITON_CACHE_DIR=$RUN_DIR/triton-cache
mkdir -p "$TORCHINDUCTOR_CACHE_DIR" "$TRITON_CACHE_DIR"

for file in \
  "$PACK/hnc_5000_worker.py" \
  "$PACK/campaign_manifest.json" \
  "$PACK/HNC_5000_NHR_PROTOCOL.md" \
  "$PACK/repo_inventory.json" \
  "$PACK/PUBLIC_RESEARCH_CATALOG.json" \
  "$PACK/RESEARCH_TEST_REGISTRY.json" \
  "$PACK/loopback_guard/sitecustomize.py" \
  "$ORGANISM_PACK/aureon_full_organism_stage1.py" \
  "$REPO/aureon/vault/voice/vault_voice.py" \
  "$MODEL/config.json" \
  "$MODEL/model.safetensors" \
  "$SIF" \
  "$PUBLIC_PY" \
  "$VENDOR_WHEEL"
do
  test -e "$file"
done

date -u +%Y-%m-%dT%H:%M:%SZ | tee "$RUN_DIR/started_utc.txt"
hostname | tee "$RUN_DIR/hostname.txt"
printf '%s\n' "$MODEL_NAME" | tee "$RUN_DIR/served-model.txt"
cp "$MODEL/aureon_export.json" "$RUN_DIR/aureon_export.json"
nvidia-smi | tee "$RUN_DIR/nvidia-smi-start.txt"

apptainer exec --nv --cleanenv \
  --bind /projects/u6vs:/projects/u6vs \
  --env PYTHONNOUSERSITE=1 \
  --env HF_HUB_OFFLINE=1 \
  --env TRANSFORMERS_OFFLINE=1 \
  "$SIF" \
  "$VENV/bin/python" -u "$BASE/training/aureon_chat_server.py" \
    --model "$MODEL" --model-name "$MODEL_NAME" --port 8000 \
  >"$RUN_DIR/chat-server.log" 2>&1 &
SERVER_PID=$!

cleanup() {
  kill "$SERVER_PID" 2>/dev/null || true
  wait "$SERVER_PID" 2>/dev/null || true
}
trap cleanup EXIT

READY=0
for attempt in $(seq 1 180); do
  if curl --fail --silent --max-time 5 http://127.0.0.1:8000/v1/models > "$RUN_DIR/models.json"; then
    READY=1
    break
  fi
  if ! kill -0 "$SERVER_PID" 2>/dev/null; then
    echo "Aureon chat server exited before readiness" >&2
    tail -n 80 "$RUN_DIR/chat-server.log" >&2 || true
    exit 30
  fi
  sleep 5
done
test "$READY" -eq 1
echo "[pilot] model ready after ${attempt} probes" | tee "$RUN_DIR/ready.txt"

VENDOR_TARGET=$RUN_DIR/hnc5k-python
"$PUBLIC_PY" -m pip install --no-deps --no-index --target "$VENDOR_TARGET" "$VENDOR_WHEEL" \
  | tee "$RUN_DIR/vendor-install.txt"

export PYTHONDONTWRITEBYTECODE=1
export HNC5K_LOOPBACK_ONLY=1
export PYTHONPATH=$VENDOR_TARGET:$PACK/loopback_guard:$REPO
export AUREON_LLM_BASE_URL=http://127.0.0.1:8000/v1
export AUREON_LLM_MODEL=$MODEL_NAME
export AUREON_LLM_PREFER_NATIVE=0
export AUREON_LLM_REQUEST_TIMEOUT_S=900
export AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS=1
export AUREON_AUDIT_MODE=1
export AUREON_LLM_ALLOW_HTTP_IN_AUDIT=1
export AUREON_NO_LIVE_ACTIONS=1
export AUREON_ACTION_MODE=dry-run
unset OPENAI_API_KEY ANTHROPIC_API_KEY AUREON_LLM_API_KEY OLLAMA_API_KEY AUREON_OLLAMA_API_KEY || true

set +e
"$PUBLIC_PY" "$PACK/hnc_5000_worker.py" \
  --repo "$REPO" \
  --inventory "$PACK/repo_inventory.json" \
  --public-inventory "$PACK/PUBLIC_RESEARCH_CATALOG.json" \
  --public-root "$PUBLIC_ROOT" \
  --test-registry "$PACK/RESEARCH_TEST_REGISTRY.json" \
  --source-commit "$PIN" \
  --protocol "$PACK/HNC_5000_NHR_PROTOCOL.md" \
  --stage1-script "$ORGANISM_PACK/aureon_full_organism_stage1.py" \
  --base-url http://127.0.0.1:8000/v1 \
  --model "$MODEL_NAME" \
  --task-id 0 \
  --task-count 206 \
  --run-seconds 10800 \
  --output-dir "$RUN_DIR" \
  --pilot \
  | tee "$RUN_DIR/worker-stdout.json"
WORKER_RC=${PIPESTATUS[0]}
set -e
echo "$WORKER_RC" | tee "$RUN_DIR/worker-exit-code.txt"
nvidia-smi | tee "$RUN_DIR/nvidia-smi-end.txt"
date -u +%Y-%m-%dT%H:%M:%SZ | tee "$RUN_DIR/completed_utc.txt"
exit "$WORKER_RC"

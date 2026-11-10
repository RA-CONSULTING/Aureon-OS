#!/bin/bash
#SBATCH --job-name=aureon-full-s1-kfix
#SBATCH --account=brics.u6vs
#SBATCH --partition=workq
#SBATCH --nodes=1
#SBATCH --gpus=4
#SBATCH --cpus-per-task=72
#SBATCH --time=01:00:00
#SBATCH --exclusive
#SBATCH --array=0-127%8
#SBATCH --no-requeue
#SBATCH --output=/projects/u6vs/hnc-organism/kimi-validation/stage1-gate-fix/runs/%x-%A_%a.out
#SBATCH --error=/projects/u6vs/hnc-organism/kimi-validation/stage1-gate-fix/runs/%x-%A_%a.err

set -euo pipefail
umask 007

# kimi-validation/stage1-gate-fix copy of the sealed aureon-full-s1 script.
# Changes vs sealed (1a8a6d391553044268fd79e7ea30d2c688df7a04dbeacf0fe63a71910e332306):
#   1. PACK repointed to the copied package; run/log dirs under
#      kimi-validation/stage1-gate-fix/runs (write-permission boundary).
#   2. Job name suffixed -kfix; run-root basename suffixed -kfix (report copy matches).
#   3. Concurrency throttled --array=0-127%8 (max 8 nodes = 32 GH200 GPUs
#      concurrently, per task-authorized ceiling). All 128 pre-registered shards
#      still run: total work unchanged (128 shards x 960 responses = 122,880),
#      per-task 1h limit unchanged, worst-case reservation unchanged at
#      128*4*1 = 512 GPU-hours.
#   4. --max-tokens 256 -> 8192 (uniform for every condition and repetition).
#      First repaired array (6346998) proved the sealed value unrunnable:
#      gpt-oss-120b is a reasoning model whose reasoning tokens share the
#      completion budget; on shard 0, 430/960 responses returned EMPTY content
#      with stop_reason=max_tokens (100% of care_under_cost, >=88% of
#      memory_continuity / restricted / consent_boundary), and the frozen
#      benchmark exit gate (any invalid JSON -> non-zero) then failed every
#      shard closed. 8192 fits the serving cap: max prompt observed 686 tokens,
#      max-model-len 10240 leaves 1362 tokens of headroom. Within-pair decoding
#      identity (temperature 0, same budget for full vs frozen) is preserved;
#      scenario fixtures, seeds, scoring, and the fail-closed JSON gate are
#      untouched.
# Model serving, seeds, conditions, decoding, and outputs are otherwise identical.

BASE=/projects/u6vs/hnc-organism
FIX="$BASE/kimi-validation/stage1-gate-fix"
PIN=f5fb1916c07ac26eb7fc38c34ff2dc9bd029e21d
PACK="$FIX/jobs/aureon-whole-organism"
REPO="$PACK/pinned/$PIN"
PUBLIC_ENV=/projects/public/brics/tutorials/distributed_vllm/.venv
YAML_CONFIG=/projects/public/brics/distributed_vllm/GPT-OSS_Hopper.yaml
HF_HOME=/projects/public/brics/data/hf
MODEL_PATH="$HF_HOME/hub/models--openai--gpt-oss-120b/snapshots/b5c939de8f754692c1647ca79fbf85e8c1e70f8a/"
MODEL_NAME=openai/gpt-oss-120b
RUN_ROOT="$FIX/runs/aureon-full-organism-s1-kfix-${SLURM_ARRAY_JOB_ID}"
RUN_DIR="$RUN_ROOT/shard-$(printf '%04d' "$SLURM_ARRAY_TASK_ID")"

mkdir -p "$RUN_DIR"
test -x "$PUBLIC_ENV/bin/python"
test -x "$PUBLIC_ENV/bin/vllm"
test -f "$YAML_CONFIG"
test -d "$MODEL_PATH"
test -f "$REPO/aureon/vault/voice/vault_voice.py"
test -f "$PACK/aureon_full_organism_stage1.py"
test -f "$PACK/AUREON_FULL_ORGANISM_STAGE1_PROTOCOL.md"

date -u +%Y-%m-%dT%H:%M:%SZ | tee "$RUN_DIR/started_utc.txt"
hostname | tee "$RUN_DIR/hostname.txt"
nvidia-smi | tee "$RUN_DIR/nvidia-smi.txt"
sha256sum \
  "$PACK/aureon_full_organism_stage1.py" \
  "$PACK/AUREON_FULL_ORGANISM_STAGE1_PROTOCOL.md" \
  "$REPO/aureon/vault/voice/vault_voice.py" \
  "$REPO/aureon/inhouse_ai/llm_adapter.py" \
  "$YAML_CONFIG" \
  | tee "$RUN_DIR/input-sha256.txt"

module reset
module load brics/nccl
module list 2>&1 | tee "$RUN_DIR/modules.txt"
source "$PUBLIC_ENV/bin/activate"
python --version | tee "$RUN_DIR/python-version.txt"
vllm --version | tee "$RUN_DIR/vllm-version.txt"

export HF_HOME
export PYTHONDONTWRITEBYTECODE=1
export TIKTOKEN_ENCODINGS_BASE=/projects/public/brics/distributed_vllm/etc/encodings
export AUREON_LLM_BASE_URL=http://127.0.0.1:8000/v1
export AUREON_LLM_MODEL="$MODEL_NAME"
export AUREON_LLM_PREFER_NATIVE=0
export AUREON_LLM_REQUEST_TIMEOUT_S=900
export AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS=1
export AUREON_AUDIT_MODE=1
export AUREON_LLM_ALLOW_HTTP_IN_AUDIT=1
export AUREON_NO_LIVE_ACTIONS=1
export AUREON_ACTION_MODE=dry-run
unset OPENAI_API_KEY ANTHROPIC_API_KEY AUREON_LLM_API_KEY OLLAMA_API_KEY AUREON_OLLAMA_API_KEY

SERVER_LOG="$RUN_DIR/vllm-server.log"
srun --nodes=1 --gpus=4 --cpus-per-task=72 --ntasks-per-node=1 \
  vllm serve "$MODEL_PATH" \
    --served-model-name "$MODEL_NAME" \
    --config "$YAML_CONFIG" \
    --host 127.0.0.1 \
    --port 8000 \
    --max-num-seqs 256 \
    --tensor_parallel_size=4 \
  >"$SERVER_LOG" 2>&1 &
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
    echo "vLLM server exited before readiness" >&2
    tail -n 120 "$SERVER_LOG" >&2 || true
    exit 30
  fi
  sleep 5
done
test "$READY" -eq 1

python "$PACK/aureon_full_organism_stage1.py" \
  --repo "$REPO" \
  --source-commit "$PIN" \
  --protocol "$PACK/AUREON_FULL_ORGANISM_STAGE1_PROTOCOL.md" \
  --base-url http://127.0.0.1:8000/v1 \
  --model "$MODEL_NAME" \
  --repetitions 2 \
  --variants-per-family 4 \
  --concurrency 32 \
  --max-tokens 8192 \
  --shard-id "$SLURM_ARRAY_TASK_ID" \
  --shard-count 128 \
  --output-dir "$RUN_DIR" \
  | tee "$RUN_DIR/benchmark-stdout.json"

sha256sum "$RUN_DIR/raw-results.jsonl" "$RUN_DIR/scenarios.json" "$RUN_DIR/summary.json" \
  | tee "$RUN_DIR/output-sha256.txt"
date -u +%Y-%m-%dT%H:%M:%SZ | tee "$RUN_DIR/completed_utc.txt"

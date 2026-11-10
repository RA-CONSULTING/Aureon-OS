#!/bin/bash
#SBATCH --job-name=stage1-recover99
#SBATCH --account=brics.u6vs
#SBATCH --partition=workq
#SBATCH --nodes=1
#SBATCH --gpus=4
#SBATCH --cpus-per-task=72
#SBATCH --time=00:15:00
#SBATCH --exclusive
#SBATCH --array=99
#SBATCH --no-requeue
#SBATCH --output=/projects/u6vs/hnc-organism/expansion-20260912/stage1-repair-v1/retry-%A_%a.out
#SBATCH --error=/projects/u6vs/hnc-organism/expansion-20260912/stage1-repair-v1/retry-%A_%a.err
set -euo pipefail
umask 007
BASE=/projects/u6vs/hnc-organism
FIX="$BASE/kimi-validation/stage1-gate-fix"
PIN=f5fb1916c07ac26eb7fc38c34ff2dc9bd029e21d
PACK="/projects/u6vs/hnc-organism/expansion-20260912/stage1-repair-v1"
REPO="/projects/u6vs/hnc-organism/kimi-validation/stage1-gate-fix/jobs/aureon-whole-organism/pinned/$PIN"
PUBLIC_ENV=/projects/public/brics/tutorials/distributed_vllm/.venv
YAML_CONFIG=/projects/public/brics/distributed_vllm/GPT-OSS_Hopper.yaml
HF_HOME=/projects/public/brics/data/hf
MODEL_PATH="$HF_HOME/hub/models--openai--gpt-oss-120b/snapshots/b5c939de8f754692c1647ca79fbf85e8c1e70f8a/"
MODEL_NAME=openai/gpt-oss-120b
RUN_ROOT="$PACK/runs/recovery-${SLURM_ARRAY_JOB_ID}"
RUN_DIR="$RUN_ROOT/shard-$(printf '%04d' "$SLURM_ARRAY_TASK_ID")"

cd "$PACK"
sha256sum -c inputs.sha256
sha256sum -c pinned-inputs.sha256
test ! -e "$RUN_DIR"
mkdir -p "$RUN_DIR"
cp AMENDMENT.json inputs.sha256 pinned-inputs.sha256 retry.sbatch "$RUN_DIR/"
printf '%s\n' "$SLURM_JOB_ID" > "$RUN_DIR/slurm-job-id.txt"
printf '%s\n' "$SLURM_ARRAY_JOB_ID" > "$RUN_DIR/slurm-array-job-id.txt"
printf '%s\n' "$SLURM_ARRAY_TASK_ID" > "$RUN_DIR/slurm-array-task-id.txt"
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
test "$(tail -n 1 "$RUN_DIR/vllm-version.txt")" = "0.15.1"

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

python "$PACK/aureon_full_organism_stage1.py" --self-test --repo "$REPO" > "$RUN_DIR/self-test.json"
SERVER_LOG="$RUN_DIR/vllm-server.log"
srun --nodes=1 --gpus=4 --cpus-per-task=72 --ntasks-per-node=1 \
  vllm serve "$MODEL_PATH" \
    --served-model-name "$MODEL_NAME" \
    --config "$YAML_CONFIG" \
    --host 127.0.0.1 \
    --port 8000 \
    --max-num-seqs 256 \
    --gpu-memory-utilization 0.85 \
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

set +e
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
BENCHMARK_EXIT=${PIPESTATUS[0]}
set -e
printf '%s\n' "$BENCHMARK_EXIT" > "$RUN_DIR/frozen-benchmark-exit.txt"

sha256sum "$RUN_DIR/raw-results.jsonl" "$RUN_DIR/scenarios.json" "$RUN_DIR/summary.json" \
  | tee "$RUN_DIR/output-sha256.txt"
date -u +%Y-%m-%dT%H:%M:%SZ | tee "$RUN_DIR/completed_utc.txt"

exit "$BENCHMARK_EXIT"

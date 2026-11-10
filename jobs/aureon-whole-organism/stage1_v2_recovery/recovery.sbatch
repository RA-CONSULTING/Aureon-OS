#!/bin/bash
#SBATCH --job-name=stage1-v2-recovery
#SBATCH --account=brics.u6vs
#SBATCH --partition=workq
#SBATCH --nodes=1
#SBATCH --gpus=4
#SBATCH --cpus-per-task=72
#SBATCH --time=01:30:00
#SBATCH --exclusive
#SBATCH --no-requeue
#SBATCH --output=/projects/u6vs/hnc-organism/expansion-20260912/stage1-v2-recovery-v1/recovery-%j.out
#SBATCH --error=/projects/u6vs/hnc-organism/expansion-20260912/stage1-v2-recovery-v1/recovery-%j.err
set -euo pipefail
umask 007
PACK=/projects/u6vs/hnc-organism/expansion-20260912/stage1-v2
REPO=/projects/u6vs/hnc-organism/kimi-validation/stage1-gate-fix/jobs/aureon-whole-organism/pinned/f5fb1916c07ac26eb7fc38c34ff2dc9bd029e21d
PUBLIC_ENV=/projects/public/brics/tutorials/distributed_vllm/.venv
YAML_CONFIG=/projects/public/brics/distributed_vllm/GPT-OSS_Hopper.yaml
export HF_HOME=/projects/public/brics/data/hf
MODEL_PATH="$HF_HOME/hub/models--openai--gpt-oss-120b/snapshots/b5c939de8f754692c1647ca79fbf85e8c1e70f8a"
MODEL_NAME=openai/gpt-oss-120b
REPAIR=/projects/u6vs/hnc-organism/expansion-20260912/stage1-v2-recovery-v1
RUN_DIR="$REPAIR/runs/recovery-$SLURM_JOB_ID"
cd "$PACK"
sha256sum -c inputs.sha256
(cd "$REPAIR" && sha256sum -c recovery.sha256)
sha256sum -c pinned-inputs.sha256
test ! -e "$RUN_DIR"
mkdir -p "$RUN_DIR"
SERVER_PID=''
MONITOR_PID=''
cleanup() {
  if [ -n "$SERVER_PID" ]; then kill "$SERVER_PID" 2>/dev/null || true; wait "$SERVER_PID" 2>/dev/null || true; fi
  if [ -n "$MONITOR_PID" ]; then kill "$MONITOR_PID" 2>/dev/null || true; wait "$MONITOR_PID" 2>/dev/null || true; fi
}
finalize() {
  local task_status=$?
  trap - EXIT
  cleanup
  set +e
  /projects/public/brics/tutorials/distributed_vllm/.venv/bin/python "$REPAIR/finalize_run.py" "$RUN_DIR" "$task_status"
  local final_status=$?
  if [ "$task_status" -eq 0 ] && [ "$final_status" -ne 0 ]; then task_status=$final_status; fi
  exit "$task_status"
}
trap finalize EXIT
cp inputs.sha256 pinned-inputs.sha256 "$REPAIR/recovery.sbatch" "$REPAIR/AMENDMENT.md" "$REPAIR/recovery.sha256" "$RUN_DIR/"
date -u +%Y-%m-%dT%H:%M:%SZ > "$RUN_DIR/started_utc.txt"
hostname > "$RUN_DIR/hostname.txt"
scontrol show job "$SLURM_JOB_ID" > "$RUN_DIR/slurm-start.txt"
nvidia-smi > "$RUN_DIR/nvidia-smi.txt"
module reset
module load brics/nccl
module list > "$RUN_DIR/modules.txt" 2>&1
source "$PUBLIC_ENV/bin/activate"
export PYTHONDONTWRITEBYTECODE=1
export STAGE1_CACHE_BASE="$(mktemp -d "${LOCALDIR:?}/stage1-v2-${SLURM_JOB_ID}.XXXXXX")"
export VLLM_CACHE_ROOT="$STAGE1_CACHE_BASE/vllm"
export TRITON_CACHE_DIR="$STAGE1_CACHE_BASE/triton"
export TORCHINDUCTOR_CACHE_DIR="$STAGE1_CACHE_BASE/inductor"
mkdir -p "$VLLM_CACHE_ROOT" "$TRITON_CACHE_DIR" "$TORCHINDUCTOR_CACHE_DIR"
python "$REPAIR/cache_receipt.py" --output "$RUN_DIR/cache-before.json"
python "$REPAIR/test_service_watch.py" > "$RUN_DIR/test-service-watch.txt" 2>&1
export TIKTOKEN_ENCODINGS_BASE=/projects/public/brics/distributed_vllm/etc/encodings
export AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS=1 AUREON_AUDIT_MODE=1 AUREON_NO_LIVE_ACTIONS=1 AUREON_ACTION_MODE=dry-run
unset OPENAI_API_KEY ANTHROPIC_API_KEY AUREON_LLM_API_KEY OLLAMA_API_KEY AUREON_OLLAMA_API_KEY
python --version > "$RUN_DIR/python-version.txt"
vllm --version > "$RUN_DIR/vllm-version.txt"
test "$(tail -n 1 "$RUN_DIR/vllm-version.txt")" = "0.15.1"
cp "$YAML_CONFIG" "$RUN_DIR/provider-model-config.yaml"
python - "$MODEL_PATH" "$RUN_DIR" <<'PY'
import hashlib,json,os,pathlib,sys
root=pathlib.Path(sys.argv[1]);out=pathlib.Path(sys.argv[2])
files={str(p.relative_to(root)):{'size':p.stat().st_size,'symlink':str(p.resolve()),'sha256':hashlib.sha256(p.read_bytes()).hexdigest() if p.stat().st_size<10000000 else None} for p in root.iterdir() if p.is_file()}
(out/'model-files.json').write_text(json.dumps({'snapshot':str(root),'files':files},indent=2)+'\n')
PY
python test_preflight.py > "$RUN_DIR/test-preflight.txt" 2>&1
python test_journal.py > "$RUN_DIR/test-journal.txt" 2>&1
python test_pipeline.py --repo "$REPO" > "$RUN_DIR/test-pipeline.txt" 2>&1
nvidia-smi --query-gpu=timestamp,index,uuid,utilization.gpu,utilization.memory,memory.used,memory.total,power.draw,power.limit --format=csv -l 1 > "$RUN_DIR/gpu-telemetry.csv" &
MONITOR_PID=$!
srun --nodes=1 --gpus=4 --cpus-per-task=72 --ntasks-per-node=1 \
  vllm serve "$MODEL_PATH" --served-model-name "$MODEL_NAME" --config "$YAML_CONFIG" \
  --host 127.0.0.1 --port 8000 --max-num-seqs 256 --gpu-memory-utilization 0.85 --tensor_parallel_size=4 \
  > "$RUN_DIR/vllm-server.log" 2>&1 &
SERVER_PID=$!
READY=0
for attempt in $(seq 1 180); do
  if curl --fail --silent --max-time 5 http://127.0.0.1:8000/v1/models > "$RUN_DIR/models.json"; then READY=1; break; fi
  if ! kill -0 "$SERVER_PID" 2>/dev/null; then tail -n 100 "$RUN_DIR/vllm-server.log" >&2; exit 30; fi
  sleep 5
done
test "$READY" -eq 1
date -u +%Y-%m-%dT%H:%M:%SZ > "$RUN_DIR/ready_utc.txt"
python "$REPAIR/cache_receipt.py" --ready --output "$RUN_DIR/cache-ready.json"
python "$REPAIR/service_watch.py" --receipt "$RUN_DIR/pilot-service-watch.jsonl" -- \
  python run_benchmark.py --repo "$REPO" --mode pilot --output "$RUN_DIR/preflight" > "$RUN_DIR/preflight-stdout.jsonl" 2>&1
python - "$RUN_DIR/preflight/run-summary.json" <<'PY'
import json,sys
data=json.load(open(sys.argv[1]));blocks=data['summaries']
assert len(blocks)==4 and sum(b['completed_responses'] for b in blocks)==7680
assert all(b['transport_failures']==0 for b in blocks)
print('RECOVERY_OPERATIONAL_PREFLIGHT_PASS')
PY
python "$REPAIR/service_watch.py" --receipt "$RUN_DIR/evaluation-service-watch.jsonl" -- \
  python run_benchmark.py --repo "$REPO" --mode evaluation --concurrency 128 --shard 0 --shards 4 --output "$RUN_DIR" > "$RUN_DIR/benchmark-stdout.jsonl" 2>&1

#!/bin/bash
#SBATCH --job-name=hnc-throughput
#SBATCH --account=brics.u6vs
#SBATCH --partition=workq
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=4
#SBATCH --gpus-per-node=4
#SBATCH --cpus-per-task=8
#SBATCH --time=00:20:00
#SBATCH --no-requeue
#SBATCH --output=/projects/u6vs/hnc-organism/expansion-20260912/hnc-throughput-v1/profile-%j.out
#SBATCH --error=/projects/u6vs/hnc-organism/expansion-20260912/hnc-throughput-v1/profile-%j.err
set -euo pipefail
umask 007
cd /projects/u6vs/hnc-organism/expansion-20260912/hnc-throughput-v1
sha256sum -c inputs.sha256
(cd /projects/u6vs/hnc-organism/expansion-20260912/hnc-fine-v1 && sha256sum -c inputs.sha256)
OUT="/projects/u6vs/hnc-organism/expansion-20260912/hnc-throughput-v1/runs/profile-$SLURM_JOB_ID"
test ! -e "$OUT"
mkdir -p "$OUT"
cp inputs.sha256 PROTOCOL.md profile.sbatch worker.sh "$OUT/"
hostname > "$OUT/hostname.txt"
scontrol show job "$SLURM_JOB_ID" > "$OUT/slurm-start.txt"
nvidia-smi --query-gpu=timestamp,index,uuid,utilization.gpu,memory.used --format=csv -l 1 > "$OUT/gpu-telemetry.csv" &
MONITOR_PID=$!
trap 'kill "$MONITOR_PID" 2>/dev/null || true; wait "$MONITOR_PID" 2>/dev/null || true' EXIT
srun --gpus-per-task=1 --gpu-bind=single:1 bash /projects/u6vs/hnc-organism/expansion-20260912/hnc-throughput-v1/worker.sh
kill "$MONITOR_PID" 2>/dev/null || true
wait "$MONITOR_PID" 2>/dev/null || true
trap - EXIT
date -u +%Y-%m-%dT%H:%M:%SZ > "$OUT/completed_utc.txt"
find "$OUT" -type f ! -name 'all-results.sha256' -print0 | sort -z | xargs -0 sha256sum > "$OUT/all-results.sha256"

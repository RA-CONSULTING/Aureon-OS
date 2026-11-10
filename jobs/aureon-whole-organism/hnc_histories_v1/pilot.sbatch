#!/bin/bash
#SBATCH --job-name=hnc-history-pilot
#SBATCH --account=brics.u6vs
#SBATCH --partition=workq
#SBATCH --nodes=32
#SBATCH --ntasks-per-node=4
#SBATCH --gpus-per-node=4
#SBATCH --cpus-per-task=8
#SBATCH --time=00:15:00
#SBATCH --signal=USR1@120
#SBATCH --no-requeue
#SBATCH --output=/projects/u6vs/hnc-organism/expansion-20260912/hnc-histories-v1/pilot-%j.out
#SBATCH --error=/projects/u6vs/hnc-organism/expansion-20260912/hnc-histories-v1/pilot-%j.err
set -euo pipefail
umask 007
cd /projects/u6vs/hnc-organism/expansion-20260912/hnc-histories-v1
sha256sum -c inputs.sha256
OUT=/projects/u6vs/hnc-organism/expansion-20260912/history-campaign-v1
mkdir -p "$OUT"
if [ -f "$OUT/config.json" ]; then
  cmp config.json "$OUT/config.json"
  cmp inputs.sha256 "$OUT/inputs.sha256"
else
  cp config.json AMENDMENT.json PROTOCOL.md inputs.sha256 "$OUT/"
fi
test ! -e "$OUT/allocation-$SLURM_JOB_ID.txt"
scontrol show job "$SLURM_JOB_ID" > "$OUT/allocation-$SLURM_JOB_ID.txt"
srun --gpus-per-task=1 --gpu-bind=single:1 bash /projects/u6vs/hnc-organism/expansion-20260912/hnc-histories-v1/worker.sh --config /projects/u6vs/hnc-organism/expansion-20260912/hnc-histories-v1/config.json --output "$OUT" --max-stop 65536
date -u +%Y-%m-%dT%H:%M:%SZ > "$OUT/completed-$SLURM_JOB_ID.txt"

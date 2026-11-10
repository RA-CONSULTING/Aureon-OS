#!/bin/bash
#SBATCH --job-name=hnc-fine-pilot
#SBATCH --account=brics.u6vs
#SBATCH --partition=workq
#SBATCH --nodes=32
#SBATCH --ntasks-per-node=4
#SBATCH --gpus-per-node=4
#SBATCH --cpus-per-task=8
#SBATCH --time=00:15:00
#SBATCH --signal=USR1@120
#SBATCH --output=/projects/u6vs/hnc-organism/expansion-20260912/hnc-fine-v1/pilot-%j.out
#SBATCH --error=/projects/u6vs/hnc-organism/expansion-20260912/hnc-fine-v1/pilot-%j.err
set -euo pipefail
BASE=/projects/u6vs/hnc-organism
H="$BASE/expansion-20260912/hnc-fine-v1"
OUT="$BASE/expansion-20260912/fine-campaign-v1"
cd "$H"
sha256sum -c inputs.sha256
mkdir -p "$OUT"
if [ -f "$OUT/config.json" ]; then cmp config.json "$OUT/config.json"; else cp config.json AMENDMENT.json inputs.sha256 "$OUT/"; fi
srun --gpus-per-task=1 --gpu-bind=single:1 bash "$H/worker.sh" --config "$H/config.json" --output "$OUT" --max-stop 65536

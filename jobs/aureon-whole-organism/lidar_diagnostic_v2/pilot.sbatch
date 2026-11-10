#!/bin/bash
#SBATCH --job-name=lidar-diagnostic-pilot
#SBATCH --account=brics.u6vs
#SBATCH --partition=workq
#SBATCH --nodes=1
#SBATCH --gpus=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=40G
#SBATCH --time=00:10:00
#SBATCH --no-requeue
#SBATCH --output=/projects/u6vs/hnc-organism/expansion-20260912/lidar-diagnostic-v2/pilot-%j.out
#SBATCH --error=/projects/u6vs/hnc-organism/expansion-20260912/lidar-diagnostic-v2/pilot-%j.err
set -euo pipefail
cd /projects/u6vs/hnc-organism/expansion-20260912/lidar-diagnostic-v2
sha256sum -c inputs.sha256
export APPTAINERENV_CUBLAS_WORKSPACE_CONFIG=:4096:8
export APPTAINERENV_OMP_NUM_THREADS=1 APPTAINERENV_OPENBLAS_NUM_THREADS=1 APPTAINERENV_PYTHONDONTWRITEBYTECODE=1 APPTAINERENV_SLURM_JOB_ID="$SLURM_JOB_ID"
IMAGE=/projects/public/brics/containers/e4s/e4s-cuda90-aarch64-25.11.sif
BASE=/projects/u6vs/hnc-organism
apptainer exec --nv --cleanenv --bind "$BASE:$BASE" "$IMAGE" python test_diagnostic.py tests-$SLURM_JOB_ID.json
apptainer exec --nv --cleanenv --bind "$BASE:$BASE" "$IMAGE" python run_diagnostic.py --pilot --output /projects/u6vs/hnc-organism/expansion-20260912/lidar-diagnostic-results-v2

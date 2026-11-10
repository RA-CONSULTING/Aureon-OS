#!/bin/bash
#SBATCH --job-name=lidar-independent-audit
#SBATCH --account=brics.u6vs
#SBATCH --partition=workq
#SBATCH --nodes=1
#SBATCH --gpus=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --time=00:10:00
#SBATCH --no-requeue
#SBATCH --output=/projects/u6vs/hnc-organism/expansion-20260912/lidar-audit-v1/audit-%j.out
#SBATCH --error=/projects/u6vs/hnc-organism/expansion-20260912/lidar-audit-v1/audit-%j.err
set -euo pipefail
cd /projects/u6vs/hnc-organism/expansion-20260912/lidar-audit-v1
sha256sum -c inputs.sha256
sacct -X -j 6505264,6505275,6505304 --format=JobID,State,ExitCode,ElapsedRaw,AllocNodes -P > accounting-$SLURM_JOB_ID.psv
export APPTAINERENV_OMP_NUM_THREADS=1 APPTAINERENV_OPENBLAS_NUM_THREADS=1 APPTAINERENV_SLURM_JOB_ID="$SLURM_JOB_ID" APPTAINERENV_PYTHONDONTWRITEBYTECODE=1 APPTAINERENV_CUBLAS_WORKSPACE_CONFIG=:4096:8
BASE=/projects/u6vs/hnc-organism
IMAGE=/projects/public/brics/containers/e4s/e4s-cuda90-aarch64-25.11.sif
apptainer exec --nv --cleanenv --bind "$BASE:$BASE" "$IMAGE" python test_audit.py > tests-$SLURM_JOB_ID.json
apptainer exec --nv --cleanenv --bind "$BASE:$BASE" "$IMAGE" python run_audit.py accounting-$SLURM_JOB_ID.psv

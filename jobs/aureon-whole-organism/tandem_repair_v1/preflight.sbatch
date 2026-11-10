#!/bin/bash
#SBATCH --job-name=tandem-repair-preflight
#SBATCH --account=brics.u6vs
#SBATCH --partition=workq
#SBATCH --nodes=1
#SBATCH --gpus=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=00:15:00
#SBATCH --no-requeue
#SBATCH --output=/projects/u6vs/hnc-organism/expansion-20260912/tandem-repair-v1/preflight-%j.out
#SBATCH --error=/projects/u6vs/hnc-organism/expansion-20260912/tandem-repair-v1/preflight-%j.err
set -euo pipefail
cd /projects/u6vs/hnc-organism/expansion-20260912/tandem-repair-v1
sha256sum -c inputs.sha256
export APPTAINERENV_OMP_NUM_THREADS=1 APPTAINERENV_OPENBLAS_NUM_THREADS=1 APPTAINERENV_SLURM_JOB_ID="$SLURM_JOB_ID" APPTAINERENV_PYTHONDONTWRITEBYTECODE=1 APPTAINERENV_CUBLAS_WORKSPACE_CONFIG=:4096:8
BASE=/projects/u6vs/hnc-organism
IMAGE=$BASE/containers/pytorch-25.05-py3.sif
apptainer exec --nv --cleanenv --bind "$BASE:$BASE" "$IMAGE" python test_repair.py tests-$SLURM_JOB_ID.json

#!/bin/bash
#SBATCH --job-name=qgita-source-cache
#SBATCH --account=brics.u6vs
#SBATCH --partition=workq
#SBATCH --nodes=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G
#SBATCH --time=00:30:00
#SBATCH --no-requeue
#SBATCH --output=/projects/u6vs/hnc-organism/expansion-20260912/qgita-source-cache-v1/cache-%j.out
#SBATCH --error=/projects/u6vs/hnc-organism/expansion-20260912/qgita-source-cache-v1/cache-%j.err
set -euo pipefail
cd /projects/u6vs/hnc-organism/expansion-20260912/qgita-source-cache-v1
sha256sum -c inputs.sha256
export APPTAINERENV_OMP_NUM_THREADS=1 APPTAINERENV_OPENBLAS_NUM_THREADS=1 APPTAINERENV_SLURM_JOB_ID="$SLURM_JOB_ID"
apptainer exec --cleanenv --bind /projects/u6vs/hnc-organism:/projects/u6vs/hnc-organism /projects/u6vs/hnc-organism/containers/python-3.12.13-slim-bookworm.sif /projects/u6vs/hnc-organism/runs/qgita-ucr-full-6145729/venv/bin/python /projects/u6vs/hnc-organism/expansion-20260912/qgita-source-cache-v1/prepare_qgita_cache.py --canonical /projects/u6vs/hnc-organism/expansion-20260912/qgita-source-cache-v1/canonical.json --output /projects/u6vs/hnc-organism/expansion-20260912/qgita-ucr-cache-v1

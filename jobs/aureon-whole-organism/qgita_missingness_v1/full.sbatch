#!/bin/bash
#SBATCH --job-name=qgita-missingness-full
#SBATCH --account=brics.u6vs
#SBATCH --partition=workq
#SBATCH --nodes=1
#SBATCH --cpus-per-task=32
#SBATCH --mem=32G
#SBATCH --time=00:15:00
#SBATCH --no-requeue
#SBATCH --output=/projects/u6vs/hnc-organism/expansion-20260912/qgita-missingness-v1/full-%j.out
#SBATCH --error=/projects/u6vs/hnc-organism/expansion-20260912/qgita-missingness-v1/full-%j.err
set -euo pipefail
cd /projects/u6vs/hnc-organism/expansion-20260912/qgita-missingness-v1
sha256sum -c inputs.sha256
export APPTAINERENV_OMP_NUM_THREADS=1 APPTAINERENV_OPENBLAS_NUM_THREADS=1 APPTAINERENV_PYTHONDONTWRITEBYTECODE=1 APPTAINERENV_SLURM_JOB_ID="$SLURM_JOB_ID"
IMAGE=/projects/u6vs/hnc-organism/containers/python-3.12.13-slim-bookworm.sif
PY=/projects/u6vs/hnc-organism/runs/qgita-ucr-full-6145729/venv/bin/python
apptainer exec --cleanenv --bind /projects/u6vs/hnc-organism:/projects/u6vs/hnc-organism "$IMAGE" "$PY" /projects/u6vs/hnc-organism/expansion-20260912/qgita-missingness-v1/test_missing.py /projects/u6vs/hnc-organism/expansion-20260912/qgita-missingness-v1/tests-$SLURM_JOB_ID.json
apptainer exec --cleanenv --bind /projects/u6vs/hnc-organism:/projects/u6vs/hnc-organism "$IMAGE" "$PY" /projects/u6vs/hnc-organism/expansion-20260912/qgita-missingness-v1/run_missing.py --pack /projects/u6vs/hnc-organism/expansion-20260912/qgita-missingness-v1 --cache /projects/u6vs/hnc-organism/expansion-20260912/qgita-ucr-cache-v1 --output /projects/u6vs/hnc-organism/expansion-20260912/qgita-missingness-campaign-v1 --summary /projects/u6vs/hnc-organism/expansion-20260912/qgita-missingness-campaign-v1/full-$SLURM_JOB_ID.json --workers 32 --new-replicates 32

#!/bin/bash
#SBATCH --job-name=hnc-history-preflight
#SBATCH --account=brics.u6vs
#SBATCH --partition=workq
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --gpus-per-task=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=00:15:00
#SBATCH --no-requeue
#SBATCH --output=/projects/u6vs/hnc-organism/expansion-20260912/hnc-histories-v1/preflight-%j.out
#SBATCH --error=/projects/u6vs/hnc-organism/expansion-20260912/hnc-histories-v1/preflight-%j.err
set -euo pipefail
cd /projects/u6vs/hnc-organism/expansion-20260912/hnc-histories-v1
sha256sum -c inputs.sha256
export APPTAINERENV_OMP_NUM_THREADS=1
export APPTAINERENV_OPENBLAS_NUM_THREADS=1
export APPTAINERENV_PYTHONDONTWRITEBYTECODE=1
export APPTAINERENV_SLURM_JOB_ID="$SLURM_JOB_ID"
apptainer exec --nv --cleanenv --bind /projects/u6vs/hnc-organism:/projects/u6vs/hnc-organism /projects/u6vs/hnc-organism/containers/pytorch-25.05-py3.sif python /projects/u6vs/hnc-organism/expansion-20260912/hnc-histories-v1/test_histories.py /projects/u6vs/hnc-organism/expansion-20260912/hnc-histories-v1/preflight-$SLURM_JOB_ID.json

#!/bin/bash
#SBATCH --job-name=hnc-fine-preflight
#SBATCH --account=brics.u6vs
#SBATCH --partition=workq
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --gpus-per-task=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=00:10:00
#SBATCH --output=/projects/u6vs/hnc-organism/expansion-20260912/hnc-fine-v1/preflight-%j.out
#SBATCH --error=/projects/u6vs/hnc-organism/expansion-20260912/hnc-fine-v1/preflight-%j.err
set -euo pipefail
BASE=/projects/u6vs/hnc-organism
H="$BASE/expansion-20260912/hnc-fine-v1"
cd "$H"
sha256sum -c inputs.sha256
export APPTAINERENV_OMP_NUM_THREADS=1
export APPTAINERENV_OPENBLAS_NUM_THREADS=1
export APPTAINERENV_SLURM_JOB_ID="$SLURM_JOB_ID"
apptainer exec --nv --cleanenv --bind "$BASE:$BASE" "$BASE/containers/pytorch-25.05-py3.sif" python "$H/test_fine.py" "$H/preflight-$SLURM_JOB_ID.json"

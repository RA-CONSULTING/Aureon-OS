#!/bin/bash
#SBATCH --job-name=acoustics-preflight
#SBATCH --account=brics.u6vs
#SBATCH --partition=workq
#SBATCH --nodes=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=24G
#SBATCH --time=00:05:00
#SBATCH --output=/projects/u6vs/hnc-organism/expansion-20260912/acoustics-repair-v1/%x-%j.out
#SBATCH --error=/projects/u6vs/hnc-organism/expansion-20260912/acoustics-repair-v1/%x-%j.err
set -euo pipefail
BASE=/projects/u6vs/hnc-organism
H="$BASE/expansion-20260912/acoustics-repair-v1"
cd "$H"
sha256sum -c inputs.sha256
export APPTAINERENV_SLURM_JOB_ID="$SLURM_JOB_ID"
export APPTAINERENV_OMP_NUM_THREADS=8
export APPTAINERENV_OPENBLAS_NUM_THREADS=8
export APPTAINERENV_MKL_NUM_THREADS=8
run() { apptainer exec --cleanenv --bind "$BASE:$BASE" "$BASE/containers/pytorch-25.05-py3.sif" python "$H/run_repair.py" "$@"; }
run selftest --output "$H/selftest-$SLURM_JOB_ID.json"

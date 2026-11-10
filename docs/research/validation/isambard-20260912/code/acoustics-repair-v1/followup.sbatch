#!/bin/bash
#SBATCH --job-name=acoustics-followup
#SBATCH --account=brics.u6vs
#SBATCH --partition=workq
#SBATCH --nodes=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=24G
#SBATCH --time=00:20:00
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
case "$SLURM_ARRAY_TASK_ID" in
0|1|2) run random --seed "$((SLURM_ARRAY_TASK_ID+1))" --output "$H/random-$SLURM_JOB_ID.json" ;;
3) run galerkin --cutoff 200 --output "$H/galerkin-$SLURM_JOB_ID.json" ;;
4) run galerkin --cutoff 300 --output "$H/galerkin-$SLURM_JOB_ID.json" ;;
5) run galerkin --cutoff 380 --output "$H/galerkin-$SLURM_JOB_ID.json" ;;
6) run controls --output "$H/controls-$SLURM_JOB_ID.json" ;;
*) exit 2 ;;
esac

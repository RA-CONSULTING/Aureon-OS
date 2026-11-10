#!/bin/bash
set -euo pipefail
BASE=/projects/u6vs/hnc-organism
H=/projects/u6vs/hnc-organism/expansion-20260912/hnc-histories-v1
export APPTAINERENV_SLURM_PROCID="${SLURM_PROCID:?}"
export APPTAINERENV_SLURM_JOB_ID="${SLURM_JOB_ID:?}"
export APPTAINERENV_CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:?}"
export APPTAINERENV_OMP_NUM_THREADS=1
export APPTAINERENV_OPENBLAS_NUM_THREADS=1
export APPTAINERENV_PYTHONDONTWRITEBYTECODE=1
exec apptainer exec --nv --cleanenv --bind "$BASE:$BASE" "$BASE/containers/pytorch-25.05-py3.sif" python "$H/run_histories.py" "$@"

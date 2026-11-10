#!/bin/bash
set -euo pipefail
BASE=/projects/u6vs/hnc-organism
SRC=/projects/u6vs/hnc-organism/expansion-20260912/tandem-repair-v1
export APPTAINERENV_SLURM_JOB_ID="${SLURM_JOB_ID:?}"
export APPTAINERENV_CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:?}"
export APPTAINERENV_OMP_NUM_THREADS=1 APPTAINERENV_OPENBLAS_NUM_THREADS=1 APPTAINERENV_PYTHONDONTWRITEBYTECODE=1 APPTAINERENV_CUBLAS_WORKSPACE_CONFIG=:4096:8
exec apptainer exec --nv --cleanenv --bind "$BASE:$BASE" "$BASE/containers/pytorch-25.05-py3.sif" python "$SRC/run_repair.py" --rank "${SLURM_PROCID:?}" --ranks 32 --output /projects/u6vs/hnc-organism/expansion-20260912/tandem-repair-results-v1

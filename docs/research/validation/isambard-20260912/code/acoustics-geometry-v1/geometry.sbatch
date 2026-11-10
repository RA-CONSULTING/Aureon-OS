#!/bin/bash
#SBATCH --job-name=acoustics-geometry
#SBATCH --account=brics.u6vs
#SBATCH --partition=workq
#SBATCH --nodes=1
#SBATCH --cpus-per-task=16
#SBATCH --mem=64G
#SBATCH --time=00:30:00
#SBATCH --output=/projects/u6vs/hnc-organism/expansion-20260912/acoustics-geometry-v1/geometry-%j.out
#SBATCH --error=/projects/u6vs/hnc-organism/expansion-20260912/acoustics-geometry-v1/geometry-%j.err
set -euo pipefail
BASE=/projects/u6vs/hnc-organism
H="$BASE/expansion-20260912/acoustics-geometry-v1"
cd "$H"
sha256sum -c inputs.sha256
export APPTAINERENV_SLURM_JOB_ID="$SLURM_JOB_ID"
export APPTAINERENV_OMP_NUM_THREADS=16
export APPTAINERENV_OPENBLAS_NUM_THREADS=16
export APPTAINERENV_MKL_NUM_THREADS=16
case "$SLURM_ARRAY_TASK_ID" in
0) GEOMETRY=coffer; DX=.20 ;;
1) GEOMETRY=coffer; DX=.15 ;;
2) GEOMETRY=coffer; DX=.10 ;;
3) GEOMETRY=opening; DX=.10 ;;
*) exit 2 ;;
esac
apptainer exec --cleanenv --bind "$BASE:$BASE" "$BASE/containers/pytorch-25.05-py3.sif" python "$H/geometry_fd.py" --geometry "$GEOMETRY" --dx "$DX" --output "$H/result-$SLURM_JOB_ID.json"

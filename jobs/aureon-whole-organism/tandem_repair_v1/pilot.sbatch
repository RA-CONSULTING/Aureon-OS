#!/bin/bash
#SBATCH --job-name=tandem-repair-pilot
#SBATCH --account=brics.u6vs
#SBATCH --partition=workq
#SBATCH --nodes=1
#SBATCH --gpus=4
#SBATCH --cpus-per-task=16
#SBATCH --mem=128G
#SBATCH --time=00:30:00
#SBATCH --no-requeue
#SBATCH --output=/projects/u6vs/hnc-organism/expansion-20260912/tandem-repair-v1/pilot-%j.out
#SBATCH --error=/projects/u6vs/hnc-organism/expansion-20260912/tandem-repair-v1/pilot-%j.err
set -euo pipefail
cd /projects/u6vs/hnc-organism/expansion-20260912/tandem-repair-v1
sha256sum -c inputs.sha256
export APPTAINERENV_OMP_NUM_THREADS=1 APPTAINERENV_OPENBLAS_NUM_THREADS=1 APPTAINERENV_SLURM_JOB_ID="$SLURM_JOB_ID" APPTAINERENV_PYTHONDONTWRITEBYTECODE=1 APPTAINERENV_CUBLAS_WORKSPACE_CONFIG=:4096:8
BASE=/projects/u6vs/hnc-organism
IMAGE=$BASE/containers/pytorch-25.05-py3.sif
pids=()
for rank in 0 1 2 3; do
  APPTAINERENV_CUDA_VISIBLE_DEVICES="$rank" apptainer exec --nv --cleanenv --bind "$BASE:$BASE" "$IMAGE" python run_repair.py --pilot --rank "$rank" --ranks 4 --output /projects/u6vs/hnc-organism/expansion-20260912/tandem-repair-results-v1 > pilot-$SLURM_JOB_ID-rank-$rank.out 2> pilot-$SLURM_JOB_ID-rank-$rank.err &
  pids+=("$!")
done
failed=0
for pid in "${pids[@]}"; do wait "$pid" || failed=1; done
test "$failed" -eq 0

#!/bin/bash
#SBATCH --job-name=tandem-repair-audit
#SBATCH --account=brics.u6vs
#SBATCH --partition=workq
#SBATCH --nodes=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=12G
#SBATCH --time=00:30:00
#SBATCH --no-requeue
#SBATCH --output=/projects/u6vs/hnc-organism/expansion-20260912/tandem-audit-v1/audit-%j.out
#SBATCH --error=/projects/u6vs/hnc-organism/expansion-20260912/tandem-audit-v1/audit-%j.err
set -euo pipefail
umask 007
cd /projects/u6vs/hnc-organism/expansion-20260912/tandem-audit-v1
sha256sum -c inputs.sha256
sacct -j 6506231,6506293,6506509 -P -n -o JobIDRaw,State,ExitCode,ElapsedRaw,AllocNodes > accounting-$SLURM_JOB_ID.psv
export APPTAINERENV_OMP_NUM_THREADS=1 APPTAINERENV_OPENBLAS_NUM_THREADS=1 APPTAINERENV_PYTHONDONTWRITEBYTECODE=1
BASE=/projects/u6vs/hnc-organism
IMAGE=$BASE/containers/pytorch-25.05-py3.sif
apptainer exec --cleanenv --bind "$BASE:$BASE" "$IMAGE" python test_analysis.py > tests-$SLURM_JOB_ID.json
apptainer exec --cleanenv --bind "$BASE:$BASE" "$IMAGE" python run_audit.py accounting-$SLURM_JOB_ID.psv

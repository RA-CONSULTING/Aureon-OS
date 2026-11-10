#!/bin/bash
#SBATCH --job-name=hnc-history-final-audit
#SBATCH --account=brics.u6vs
#SBATCH --partition=workq
#SBATCH --nodes=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --gpus-per-task=1
#SBATCH --ntasks=1
#SBATCH --time=01:00:00
#SBATCH --no-requeue
#SBATCH --output=/projects/u6vs/hnc-organism/expansion-20260912/hnc-history-final-audit-v1/audit-%j.out
#SBATCH --error=/projects/u6vs/hnc-organism/expansion-20260912/hnc-history-final-audit-v1/audit-%j.err
set -euo pipefail
cd /projects/u6vs/hnc-organism/expansion-20260912/hnc-history-final-audit-v1
sha256sum -c inputs.sha256
export APPTAINERENV_OMP_NUM_THREADS=1 APPTAINERENV_OPENBLAS_NUM_THREADS=1 APPTAINERENV_PYTHONDONTWRITEBYTECODE=1
sacct -j 6504653 --format=JobID,State,ExitCode,ElapsedRaw,AllocNodes,AllocTRES -P > "accounting-$SLURM_JOB_ID.psv"
apptainer exec --nv --cleanenv --bind /projects/u6vs/hnc-organism:/projects/u6vs/hnc-organism /projects/u6vs/hnc-organism/containers/pytorch-25.05-py3.sif python /projects/u6vs/hnc-organism/expansion-20260912/hnc-history-final-audit-v1/audit_hnc_histories.py --pack /projects/u6vs/hnc-organism/expansion-20260912/hnc-histories-v1 --campaign /projects/u6vs/hnc-organism/expansion-20260912/history-campaign-v1 --job 6504653 --stop 33554432 --accounting-file "/projects/u6vs/hnc-organism/expansion-20260912/hnc-history-final-audit-v1/accounting-$SLURM_JOB_ID.psv" --output "/projects/u6vs/hnc-organism/expansion-20260912/hnc-history-final-audit-v1/audit-$SLURM_JOB_ID.json"
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
/projects/public/brics/tutorials/distributed_vllm/.venv/bin/python analyse_hnc_history_results.py --pack /projects/u6vs/hnc-organism/expansion-20260912/hnc-histories-v1 --campaign /projects/u6vs/hnc-organism/expansion-20260912/history-campaign-v1 --audit "audit-$SLURM_JOB_ID.json" --original /projects/u6vs/hnc-organism/expansion-20260912/fine-campaign-v1 --output "analysis-$SLURM_JOB_ID.json"
sha256sum "accounting-$SLURM_JOB_ID.psv" "audit-$SLURM_JOB_ID.json" "analysis-$SLURM_JOB_ID.json" > "results-$SLURM_JOB_ID.sha256"

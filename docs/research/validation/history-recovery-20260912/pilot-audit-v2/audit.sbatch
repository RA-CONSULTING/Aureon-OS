#!/bin/bash
#SBATCH --job-name=hnc-history-pilot-audit
#SBATCH --account=brics.u6vs
#SBATCH --partition=workq
#SBATCH --nodes=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --time=00:15:00
#SBATCH --no-requeue
#SBATCH --output=/projects/u6vs/hnc-organism/expansion-20260912/hnc-history-audit-v2/audit-%j.out
#SBATCH --error=/projects/u6vs/hnc-organism/expansion-20260912/hnc-history-audit-v2/audit-%j.err
set -euo pipefail
cd /projects/u6vs/hnc-organism/expansion-20260912/hnc-history-audit-v2
sha256sum -c inputs.sha256
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
/projects/public/brics/tutorials/distributed_vllm/.venv/bin/python audit_hnc_histories.py --pack /projects/u6vs/hnc-organism/expansion-20260912/hnc-histories-v1 --campaign /projects/u6vs/hnc-organism/expansion-20260912/history-campaign-v1 --job 6504297 --stop 65536 --output "/projects/u6vs/hnc-organism/expansion-20260912/hnc-history-audit-v2/audit-$SLURM_JOB_ID.json"

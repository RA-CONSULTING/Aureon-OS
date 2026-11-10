#!/bin/bash
#SBATCH --job-name=stage1-replication-audit
#SBATCH --account=brics.u6vs
#SBATCH --partition=workq
#SBATCH --nodes=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=64G
#SBATCH --time=00:20:00
#SBATCH --no-requeue
#SBATCH --output=/projects/u6vs/hnc-organism/expansion-20260912/stage1-v2-recovery-analysis-v1/audit-%j.out
#SBATCH --error=/projects/u6vs/hnc-organism/expansion-20260912/stage1-v2-recovery-analysis-v1/audit-%j.err
set -euo pipefail
cd /projects/u6vs/hnc-organism/expansion-20260912/stage1-v2-recovery-analysis-v1
sha256sum -c inputs.sha256
PYTHON=/projects/public/brics/tutorials/distributed_vllm/.venv/bin/python
export PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
"$PYTHON" test_stage1_v2_analysis.py
"$PYTHON" stage1_v2_recovery_analysis.py --pack /projects/u6vs/hnc-organism/expansion-20260912/stage1-v2 --run /projects/u6vs/hnc-organism/expansion-20260912/stage1-v2-recovery-v1/runs/recovery-6503592 --oldroot /projects/u6vs/hnc-organism/expansion-20260912/stage1-v2-evaluation-v1/runs --oldanalysis /projects/u6vs/hnc-organism/expansion-20260912/stage1-v2-forensic-v1/analysis-6503602/analysis.json --recoverypack /projects/u6vs/hnc-organism/expansion-20260912/stage1-v2-recovery-v1 --output "/projects/u6vs/hnc-organism/expansion-20260912/stage1-v2-recovery-analysis-v1/analysis-$SLURM_JOB_ID"
"$PYTHON" export_evidence.py "/projects/u6vs/hnc-organism/expansion-20260912/stage1-v2-recovery-analysis-v1/analysis-$SLURM_JOB_ID" /projects/u6vs/hnc-organism/expansion-20260912/stage1-v2-recovery-v1/runs/recovery-6503592

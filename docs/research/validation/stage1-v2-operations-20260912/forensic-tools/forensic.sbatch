#!/bin/bash
#SBATCH --job-name=stage1-v2-forensic
#SBATCH --account=brics.u6vs
#SBATCH --partition=workq
#SBATCH --nodes=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=64G
#SBATCH --time=00:20:00
#SBATCH --no-requeue
#SBATCH --output=/projects/u6vs/hnc-organism/expansion-20260912/stage1-v2-forensic-v1/forensic-%j.out
#SBATCH --error=/projects/u6vs/hnc-organism/expansion-20260912/stage1-v2-forensic-v1/forensic-%j.err
set -euo pipefail
umask 007
cd /projects/u6vs/hnc-organism/expansion-20260912/stage1-v2-forensic-v1
sha256sum -c inputs.sha256
PYTHON=/projects/public/brics/tutorials/distributed_vllm/.venv/bin/python
export PYTHONDONTWRITEBYTECODE=1
"$PYTHON" test_stage1_v2_analysis.py
"$PYTHON" stage1_v2_forensic_analysis.py --pack /projects/u6vs/hnc-organism/expansion-20260912/stage1-v2 --campaign /projects/u6vs/hnc-organism/expansion-20260912/stage1-v2-evaluation-v1 --output "/projects/u6vs/hnc-organism/expansion-20260912/stage1-v2-forensic-v1/analysis-$SLURM_JOB_ID"
"$PYTHON" export_evidence.py "/projects/u6vs/hnc-organism/expansion-20260912/stage1-v2-forensic-v1/analysis-$SLURM_JOB_ID" /projects/u6vs/hnc-organism/expansion-20260912/stage1-v2-evaluation-v1

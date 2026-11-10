#!/bin/bash
#SBATCH --job-name=stage1-recovery-audit
#SBATCH --account=brics.u6vs
#SBATCH --partition=workq
#SBATCH --nodes=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=4G
#SBATCH --time=00:15:00
#SBATCH --output=/projects/u6vs/hnc-organism/expansion-20260912/stage1-audit-v1/audit-%j.out
#SBATCH --error=/projects/u6vs/hnc-organism/expansion-20260912/stage1-audit-v1/audit-%j.err
set -euo pipefail
cd /projects/u6vs/hnc-organism/expansion-20260912/stage1-audit-v1
sha256sum -c inputs.sha256
apptainer exec --cleanenv --bind /projects/u6vs/hnc-organism:/projects/u6vs/hnc-organism /projects/u6vs/hnc-organism/containers/pytorch-25.05-py3.sif python stage1_retrospective_audit.py --recovery /projects/u6vs/hnc-organism/expansion-20260912/stage1-repair-v1/runs/recovery-6500368/shard-0099 --output "$PWD/audit-$SLURM_JOB_ID.json"

#!/bin/bash
#SBATCH --job-name=hnc-fine-audit
#SBATCH --account=brics.u6vs
#SBATCH --partition=workq
#SBATCH --nodes=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=4G
#SBATCH --time=00:10:00
#SBATCH --output=/projects/u6vs/hnc-organism/expansion-20260912/fine-audit-v1/audit-%j.out
#SBATCH --error=/projects/u6vs/hnc-organism/expansion-20260912/fine-audit-v1/audit-%j.err
set -euo pipefail
BASE=/projects/u6vs/hnc-organism
H="$BASE/expansion-20260912/fine-audit-v1"
cd "$H"
sha256sum -c inputs.sha256
apptainer exec --cleanenv --bind "$BASE:$BASE" "$BASE/containers/pytorch-25.05-py3.sif" python "$H/audit_fine.py" --base "$BASE/expansion-20260912" --stop "$1" --job "$2" --output "$H/audit-$SLURM_JOB_ID.json"

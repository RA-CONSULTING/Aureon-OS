#!/bin/bash
#SBATCH --job-name=hnc-horizon-audit
#SBATCH --account=brics.u6vs
#SBATCH --partition=workq
#SBATCH --nodes=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=4G
#SBATCH --time=00:10:00
#SBATCH --output=/projects/u6vs/hnc-organism/expansion-20260912/extension-audit-v1/audit-%j.out
#SBATCH --error=/projects/u6vs/hnc-organism/expansion-20260912/extension-audit-v1/audit-%j.err
set -euo pipefail
BASE=/projects/u6vs/hnc-organism
H="$BASE/expansion-20260912/extension-audit-v1"
PY="$BASE/runs/qgita-ucr-full-6145729/venv/bin/python"
cd "$H"
sha256sum -c inputs.sha256
apptainer exec --cleanenv --bind "$BASE:$BASE" "$BASE/containers/python-3.12.13-slim-bookworm.sif" "$PY" "$H/audit_extension.py" --base "$BASE/expansion-20260912" --output "$H/audit-$SLURM_JOB_ID.json" "$@"

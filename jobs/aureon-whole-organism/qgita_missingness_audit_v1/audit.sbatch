#!/bin/bash
#SBATCH --job-name=qgita-missingness-audit
#SBATCH --account=brics.u6vs
#SBATCH --partition=workq
#SBATCH --nodes=1
#SBATCH --cpus-per-task=16
#SBATCH --mem=64G
#SBATCH --time=00:30:00
#SBATCH --no-requeue
#SBATCH --output=/projects/u6vs/hnc-organism/expansion-20260912/qgita-missingness-audit-v1/audit-%j.out
#SBATCH --error=/projects/u6vs/hnc-organism/expansion-20260912/qgita-missingness-audit-v1/audit-%j.err
set -euo pipefail
cd /projects/u6vs/hnc-organism/expansion-20260912/qgita-missingness-audit-v1
sha256sum -c inputs.sha256
sacct -j 6504999 --format=JobID,State,ExitCode,ElapsedRaw,AllocNodes -P > "accounting-$SLURM_JOB_ID.psv"
python3 - "accounting-$SLURM_JOB_ID.psv" <<'PY'
import csv,sys
rows={r['JobID']:r for r in csv.DictReader(open(sys.argv[1]),delimiter='|')}
assert rows['6504999']['State']=='COMPLETED' and rows['6504999']['ExitCode']=='0:0'
PY
export APPTAINERENV_OMP_NUM_THREADS=1 APPTAINERENV_OPENBLAS_NUM_THREADS=1 APPTAINERENV_PYTHONDONTWRITEBYTECODE=1
IMAGE=/projects/u6vs/hnc-organism/containers/python-3.12.13-slim-bookworm.sif
PYTHON=/projects/u6vs/hnc-organism/runs/qgita-ucr-full-6145729/venv/bin/python
apptainer exec --cleanenv --bind /projects/u6vs/hnc-organism:/projects/u6vs/hnc-organism "$IMAGE" "$PYTHON" /projects/u6vs/hnc-organism/expansion-20260912/qgita-missingness-audit-v1/test_audit_qgita_missingness.py "/projects/u6vs/hnc-organism/expansion-20260912/qgita-missingness-audit-v1/tests-$SLURM_JOB_ID.json" /projects/u6vs/hnc-organism/expansion-20260912/qgita-missingness-v1
apptainer exec --cleanenv --bind /projects/u6vs/hnc-organism:/projects/u6vs/hnc-organism "$IMAGE" "$PYTHON" /projects/u6vs/hnc-organism/expansion-20260912/qgita-missingness-audit-v1/audit_qgita_missingness.py --pack /projects/u6vs/hnc-organism/expansion-20260912/qgita-missingness-v1 --cache /projects/u6vs/hnc-organism/expansion-20260912/qgita-ucr-cache-v1 --campaign /projects/u6vs/hnc-organism/expansion-20260912/qgita-missingness-campaign-v1 --summary /projects/u6vs/hnc-organism/expansion-20260912/qgita-missingness-campaign-v1/full-6504999.json --workers 16 --output "/projects/u6vs/hnc-organism/expansion-20260912/qgita-missingness-audit-v1/analysis-$SLURM_JOB_ID.json"
python3 export_evidence.py /projects/u6vs/hnc-organism/expansion-20260912/qgita-missingness-audit-v1 /projects/u6vs/hnc-organism/expansion-20260912/qgita-missingness-campaign-v1 "$SLURM_JOB_ID"
sha256sum "analysis-$SLURM_JOB_ID.json" "accounting-$SLURM_JOB_ID.psv" "tests-$SLURM_JOB_ID.json" "export-$SLURM_JOB_ID.json" > "results-$SLURM_JOB_ID.sha256"

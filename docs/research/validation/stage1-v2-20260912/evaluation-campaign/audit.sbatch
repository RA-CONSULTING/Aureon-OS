#!/bin/bash
#SBATCH --job-name=stage1-v2-audit
#SBATCH --account=brics.u6vs
#SBATCH --partition=workq
#SBATCH --nodes=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=64G
#SBATCH --time=00:20:00
#SBATCH --no-requeue
#SBATCH --output=/projects/u6vs/hnc-organism/expansion-20260912/stage1-v2-evaluation-v1/audit-%j.out
#SBATCH --error=/projects/u6vs/hnc-organism/expansion-20260912/stage1-v2-evaluation-v1/audit-%j.err
set -euo pipefail
umask 007
CAMPAIGN=/projects/u6vs/hnc-organism/expansion-20260912/stage1-v2-evaluation-v1
PACK=/projects/u6vs/hnc-organism/expansion-20260912/stage1-v2
cd "$CAMPAIGN"
sha256sum -c campaign.sha256
export PYTHONDONTWRITEBYTECODE=1
PYTHON=/projects/public/brics/tutorials/distributed_vllm/.venv/bin/python
test ! -e "$CAMPAIGN/analysis-$SLURM_JOB_ID"
mkdir "$CAMPAIGN/analysis-$SLURM_JOB_ID"
OUT="$CAMPAIGN/analysis-$SLURM_JOB_ID"
sacct -j "$(cat "$CAMPAIGN/evaluation-array-id.txt")" --format=JobID,JobIDRaw,State,ExitCode,ElapsedRaw,AllocNodes,AllocTRES -P > "$OUT/accounting.psv"
"$PYTHON" - "$OUT/accounting.psv" "$CAMPAIGN/RESOURCE_PLAN.json" <<'PY'
import csv,json,sys
records=list(csv.DictReader(open(sys.argv[1]),delimiter='|'))
jobs=[r for r in records if '_' in r['JobID'] and '.' not in r['JobID']]
assert len(jobs)==json.load(open(sys.argv[2]))['nodes'],jobs
assert all(r['State']=='COMPLETED' and r['ExitCode']=='0:0' for r in jobs),jobs
PY
"$PYTHON" test_stage1_v2_analysis.py > "$OUT/analysis-tests.txt" 2>&1
"$PYTHON" stage1_v2_evaluation_analysis.py --pack "$PACK" --campaign "$CAMPAIGN" --output "$OUT/analysis.json" > "$OUT/analysis-stdout.json"
date -u +%Y-%m-%dT%H:%M:%SZ > "$OUT/completed_utc.txt"
(cd "$OUT" && sha256sum analysis.json accounting.psv analysis-tests.txt completed_utc.txt > results.sha256)

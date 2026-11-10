from pathlib import Path
import datetime,json,subprocess,sys
from submit_frozen_bundle import submit

root=Path('work/tandem-audit-v1')
for p in root.glob('*.py'):compile(p.read_text(),str(p),'exec')
result=submit(root,'/projects/u6vs/hnc-organism/expansion-20260912/tandem-audit-v1','audit.sbatch','outputs/tandem-repair-audit-submission-v1.json',extra=['--dependency=afterany:6506509'])
print(json.dumps(result,indent=2))

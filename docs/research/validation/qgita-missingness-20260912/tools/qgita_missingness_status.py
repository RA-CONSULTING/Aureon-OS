from pathlib import Path
import json,subprocess
ROOT=Path(__file__).resolve().parent.parent
script='''import csv,datetime,json,pathlib,subprocess
b=pathlib.Path('/projects/u6vs/hnc-organism/expansion-20260912');r=b/'qgita-missingness-audit-v1'
acct=subprocess.check_output(['sacct','-j','6504865,6504958,6504999,6505031','--format=JobID,State,ExitCode,ElapsedRaw,AllocNodes','-P'],universal_newlines=True)
jobs={x['JobID']:x for x in csv.DictReader(acct.splitlines(),delimiter='|')}
result=dict(observed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),accounting=jobs)
for label,p in [('full_out',b/'qgita-missingness-v1/full-6504999.out'),('full_err',b/'qgita-missingness-v1/full-6504999.err'),('audit_out',r/'audit-6505031.out'),('audit_err',r/'audit-6505031.err')]:
    if p.exists():result[label]=p.read_text(errors='replace').splitlines()[-12:]
if jobs.get('6505031',{}).get('State')=='COMPLETED':
    data=json.loads((r/'analysis-6505031.json').read_text());result['audit_summary']={k:data[k] for k in ['status','verified_mask_sets','verified_candidate_control_outcomes']}
    result['new_mask_results']={s:{k:v for k,v in row.items() if k in ['family_macro','contrasts','noninferior_to_clean','mean_scoreable_fraction']} for s,row in data['analysis']['new_masks'].items()}
    result['export']=json.loads((r/'export-6505031.json').read_text())
print(json.dumps(result))
'''
compile(script,'status','exec')
r=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=30','u6vs.aip2.isambard','python3 -'],input=script.encode(),capture_output=True,check=True,timeout=65)
result=json.loads(r.stdout);(ROOT/'outputs/qgita-missingness-status-v1.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k not in ['full_out','full_err','audit_out']},indent=2))

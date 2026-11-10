from pathlib import Path
import json,subprocess
ROOT=Path(__file__).resolve().parent.parent
script='''import collections,datetime,hashlib,json,pathlib,subprocess
b=pathlib.Path('/projects/u6vs/hnc-organism/expansion-20260912');h=b/'hnc-histories-v1';c=b/'history-campaign-v1'
jobs='6504281,6504297,6504298,6504409,6504601,6504609,6504653,6504684'
result=dict(observed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),accounting=subprocess.check_output(['sacct','-j',jobs,'--format=JobID,State,ExitCode,ElapsedRaw,AllocNodes','-P'],universal_newlines=True),queue=subprocess.check_output(['squeue','-j','6504653,6504684','-h','-o','%i|%T|%M|%D|%R'],universal_newlines=True))
rank_stops=[];receipts=0
for rankdir in sorted(c.glob('rank-*')):
    values=[json.loads(p.read_text())['stop'] for p in rankdir.glob('attempt-*/receipt.json')]
    receipts+=len(values);rank_stops.append(dict(rank=rankdir.name,stop=max(values) if values else 0))
result['progress']=dict(ranks=len(rank_stops),receipts=receipts,min_stop=min(r['stop'] for r in rank_stops),max_stop=max(r['stop'] for r in rank_stops),stops_histogram=dict(collections.Counter(str(r['stop']) for r in rank_stops)))
result['logs']={}
for directory,job,stem in [('hnc-history-audit-v1','6504298','audit'),('hnc-history-audit-v2','6504409','audit'),('hnc-history-audit-v3','6504601','audit'),('hnc-history-audit-v4','6504609','audit'),('hnc-histories-v1','6504653','production')]:
    for ext in ['out','err']:
        p=b/directory/(stem+'-'+job+'.'+ext)
        if p.exists():result['logs'][p.name]=p.read_text(errors='replace').splitlines()[-16:]
print(json.dumps(result))
'''
compile(script,'status','exec')
r=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=30','u6vs.aip2.isambard','python3 -'],input=script.encode(),capture_output=True,check=True,timeout=65)
result=json.loads(r.stdout);(ROOT/'outputs/hnc-histories-status.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:result[k] for k in ['observed_utc','accounting','queue','progress']},indent=2))

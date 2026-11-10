import csv,datetime,hashlib,json,pathlib
p=pathlib.Path('outputs/isambard-accounting-20260912.psv')
rows=list(csv.DictReader(p.read_text().splitlines(),delimiter='|'));seen=set();output=[]
for r in rows:
    assert r['JobIDRaw'] not in seen;seen.add(r['JobIDRaw'])
    elapsed=int(r['ElapsedRaw']);nodes=int(r['NNodes'])
    tres=dict(x.split('=',1) for x in r['AllocTRES'].split(',') if '=' in x)
    cpus=float(tres.get('cpu',0));gpus=float(tres.get('gres/gpu',0))
    memory=tres.get('mem','0');factor={'K':1/1024**2,'M':1/1024,'G':1.,'T':1024.}
    mem_gib=float(memory[:-1])*factor[memory[-1]] if memory[-1] in factor else float(memory)/1024
    # Estimate based on the provider's documented max allocated resource fraction.
    allocated_node_equivalents=max(cpus/288,gpus/4,mem_gib/864,nodes*.25) if elapsed else 0
    estimate=elapsed/3600*allocated_node_equivalents
    output.append(dict(r,estimated_nhr=estimate,gpu_hours=elapsed/3600*gpus,physical_node_hours=elapsed/3600*nodes))
groups={}
for label,subset in [('all_september_returned',output),('ended_since_sept8_start',[r for r in output if r['End']>='2026-09-08T00:00:00']),('ended_since_sept9_start',[r for r in output if r['End']>='2026-09-09T00:00:00']),('hnc_fine_production',[r for r in output if r['JobIDRaw']=='6498143'])]:
    groups[label]=dict(records=len(subset),estimated_nhr=sum(r['estimated_nhr'] for r in subset),gpu_hours=sum(r['gpu_hours'] for r in subset),physical_node_hours=sum(r['physical_node_hours'] for r in subset))
result=dict(schema='isambard-accounting-reconciliation/v1',generated_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    input_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),provider_rule='https://docs.isambard.ac.uk/user-documentation/guides/accounting/',
    interval='2026-09-01 through query time on 2026-09-12; all visible brics.u6vs top-level allocation records; job steps excluded',
    groups=groups,rows=output,verified_current_portal_balance=None,
    email_anchor=dict(date='2026-09-08',remaining_nhr=4980.98,status='Previously read provider email, not a current portal balance.'),
    indicative_balance_range=[4980.98-groups['ended_since_sept8_start']['estimated_nhr'],4980.98-groups['ended_since_sept9_start']['estimated_nhr']],
    limits=['Portal unavailable in this continuation; balances below are estimates, not authorization from the provider.','Email timestamp and accounting cutoff are not reconciled.','Documented max CPU/GPU/memory fractions are applied to AllocTRES. Slurm billing field alone understates GPU allocation in some jobs.','Assumes normal workq accounting and no credit changes since the email.','No completeness claim for other clusters or invisible project accounts; current pending reservations are separate.'])
assert all(r['Partition']=='workq' for r in output if int(r['ElapsedRaw'])>0)
pathlib.Path('outputs/isambard-accounting-reconciliation.json').write_text(json.dumps(result,indent=2))
print(json.dumps({k:v for k,v in result.items() if k!='rows'},indent=2))

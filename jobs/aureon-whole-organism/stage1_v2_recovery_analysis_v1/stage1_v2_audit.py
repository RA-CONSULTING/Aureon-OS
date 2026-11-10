"""Stream-audit frozen Stage 1 v2 receipts and derive the preregistered resource decision.

This analysis code is outside the immutable experiment input directory. The
protocol fixes its analysis before outcomes; this tool cannot edit inputs.
"""
from __future__ import annotations
import argparse,collections,datetime,hashlib,json,math,re,sys
from pathlib import Path

def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()
def records(path):
    with Path(path).open(encoding='utf-8') as f:
        for line in f:
            if not line.endswith('\n'):raise RuntimeError('Torn journal: '+str(path))
            yield json.loads(line)
def save(p,d):Path(p).write_text(json.dumps(d,indent=2,ensure_ascii=False,sort_keys=True)+'\n',encoding='utf-8')

def audit_block(block,pack):
    sys.path.insert(0,str(pack))
    from fixtures import canonical,digest
    from scoring import system_prompt,score
    from run_benchmark import plan
    config=json.loads((block/'configuration.json').read_text())
    summary=json.loads((block/'summary.json').read_text())
    assert config['input_manifest_sha256']==sha(pack/'inputs.sha256')
    for name,h in summary['hashes'].items():assert sha(block/name)==h,(block,name)
    pilot=config['block'].startswith('pilot')
    allrows=list(records(pack/('development.jsonl' if pilot else 'evaluation.jsonl')))
    if pilot:rows=[r for r in allrows if r['instance']<4]
    else:
        # Final plan provides exact membership; separately check against allocation shard configuration.
        ids={r['scenario_id'] for r in json.loads((block/'plan.json').read_text())}
        rows=[r for r in allrows if r['scenario_id'] in ids]
    scenarios={r['scenario_id']:r for r in rows}
    contexts=json.loads((pack/'contexts.json').read_text())['contexts']
    planned=plan(rows,contexts,config['repetitions'],config['order_seed'])
    assert digest(canonical(planned))==config['plan_sha256']
    assert planned==json.loads((block/'plan.json').read_text())
    expected={r['key']:r for r in planned};starts={};ends={};raw_hashes=set();byarm=collections.defaultdict(collections.Counter)
    for r in records(block/'attempts.jsonl'):
        key=r['key'];assert key in expected;task=expected[key];identity=(key,r['attempt']);scenario=scenarios[task['scenario_id']]
        if r['event']=='start':
            assert identity not in starts;starts[identity]=r.get('request_sha256')
            body=r['request_body_utf8']
            if body is not None:
                assert digest(body)==r['request_sha256'];raw_hashes.add(r['request_sha256'])
                payload=json.loads(body)
                target={'model':'openai/gpt-oss-120b','messages':[
                    {'role':'system','content':system_prompt(contexts[task['condition']],task['policy'])},
                    {'role':'user','content':canonical(scenario['input'])}],
                    'max_tokens':8192,'temperature':0,'stream':False,'keep_alive':'30m'}
                assert payload==target,(key,'actual request differs from frozen input')
                assert r['url']=='http://127.0.0.1:8000/v1/chat/completions'
        elif r['event']=='end':
            assert identity in starts and identity not in ends
            assert r.get('request_sha256')==starts[identity]
            if r.get('response_body_utf8') is not None:
                assert digest(r['response_body_utf8'])==r['response_sha256']
            if r['transport_ok']:
                raw=json.loads(r['response_body_utf8']);choice=raw['choices'][0]
                assert r['status_code']==200 and raw['model']=='openai/gpt-oss-120b'
                assert r['text']==(choice['message'].get('content') or '')
                assert r['finish_reason']==choice['finish_reason']
                assert r['usage']==raw.get('usage',{})
            rescored=score(r['text'],scenario,r['finish_reason'],r['transport_ok'])
            assert rescored==r['score'],(key,'score mismatch')
            ends[identity]={'hash':digest(canonical(r)),'score':r['score'],'transport_ok':r['transport_ok'],
                            'usage':r['usage'],'finish_reason':r['finish_reason']}
        else:raise RuntimeError('Unknown event')
    finals={};template_values=collections.defaultdict(lambda:collections.defaultdict(list));errors=collections.Counter()
    for r in records(block/'results.jsonl'):
        key=r['key'];assert key in expected and key not in finals;finals[key]=r
        for field,value in expected[key].items():assert r[field]==value
        e=ends[(key,r['attempt'])];assert e['hash']==r['attempt_result_sha256']
        for field in ('score','transport_ok','usage','finish_reason'):assert r[field]==e[field]
        scenario=scenarios[r['scenario_id']];arm=(r['policy'],r['condition']);stats=byarm[arm]
        stats['responses']+=1
        for metric in ('schema_valid','verdict_correct','action_correct','joint_correct','citation_coverage','grounded_joint_correct'):
            stats[metric]+=r['score'][metric]
        stats['transport_failures']+=not r['transport_ok']
        if r['score']['error']:errors[r['score']['error']]+=1
        if r['score']['brier'] is not None:stats['brier_sum']+=r['score']['brier'];stats['brier_n']+=1
        template_values[scenario['template']][r['policy']+'|'+r['condition']].append(int(r['score']['joint_correct']))
    assert set(finals)==set(expected)
    metrics={k:sum(x['score'][k] for x in finals.values()) for k in ('schema_valid','verdict_correct','action_correct','joint_correct','citation_coverage','grounded_joint_correct')}
    for k,v in metrics.items():assert summary[k]==v
    assert summary['transport_failures']==sum(not r['transport_ok'] for r in finals.values())
    return {'block':block.name,'verified':True,'planned':len(expected),'responses':len(finals),
            'attempt_starts':len(starts),'attempt_ends':len(ends),'unresolved_attempts':len(set(starts)-set(ends)),
            'distinct_actual_request_bodies':len(raw_hashes),'errors':dict(errors),'summary':summary,
            'arms':{p+'|'+c:dict(s) for (p,c),s in byarm.items()},
            'template_joint_counts':{t:{a:{'sum':sum(v),'n':len(v)} for a,v in arms.items()} for t,arms in template_values.items()}}

def telemetry(run):
    import csv
    p=run/'gpu-telemetry.csv'
    if not p.exists():return {'available':False}
    rows=list(csv.DictReader(p.open()));by=collections.defaultdict(list);parsed=[];unparsed=0
    for row in rows:
        cleaned={k.strip():v.strip() for k,v in row.items()}
        try:
            util=float(cleaned['utilization.gpu [%]'].split()[0]);memory=float(cleaned['memory.used [MiB]'].split()[0]);index=cleaned['index']
            by[index].append((util,memory))
            timestamp=datetime.datetime.strptime(cleaned['timestamp'],'%Y/%m/%d %H:%M:%S.%f')
            parsed.append((timestamp,index,util,memory))
        except (ValueError,KeyError):unparsed+=1
    assert len(by)==4 and all(by.values()),'Expected readable telemetry from four GPUs'
    blocks={}
    for path in sorted(run.glob('pilot-*/summary.json')):
        s=json.loads(path.read_text());start=datetime.datetime.strptime(s['started_utc'],'%Y-%m-%dT%H:%M:%SZ');end=datetime.datetime.strptime(s['completed_utc'],'%Y-%m-%dT%H:%M:%SZ')
        samples=[x for x in parsed if start<=x[0]<=end]
        assert samples,'Missing block telemetry'
        blocks[s['block']]={'samples':len(samples),'concurrency':s['concurrency'],
                            'mean_gpu_utilization_percent':sum(x[2] for x in samples)/len(samples)}
    return {'available':True,'whole_allocation_samples_including_startup_and_shutdown':True,
            'unparsed_rows':unparsed,'benchmark_blocks':blocks,
            'per_gpu':{k:{'samples':len(v),'mean_gpu_utilization_percent':sum(x[0] for x in v)/len(v),
                        'max_used_memory_MiB':max(x[1] for x in v),'nonzero_utilization_samples':sum(x[0]>0 for x in v)} for k,v in by.items()}}

def resource_decision(audits,run):
    by=collections.defaultdict(list)
    for a in audits:by[a['summary']['concurrency']].append(a['summary'])
    text=(run/'vllm-server.log').read_text(errors='replace')
    flags=[line for line in text.splitlines() if re.search(r'out.of.memory|OutOfMemory|PreemptionMode|preempted',line,re.I)]
    pooled={str(c):{'blocks':len(rows),'new_responses':sum(x['new_responses'] for x in rows),
                    'seconds':sum(x['session_seconds'] for x in rows),
                    'responses_per_second':sum(x['new_responses'] for x in rows)/sum(x['session_seconds'] for x in rows),
                    'transport_failures':sum(x['transport_failures'] for x in rows)} for c,rows in by.items()}
    reliable=lambda c:len(by[c])==2 and all(x['new_responses']==1920 and x['completed_responses']==1920 and x['transport_failures']==0 for x in by[c]) and not flags
    chosen=None
    if reliable(128) and pooled['128']['responses_per_second']>=1.1*pooled['32']['responses_per_second']:chosen=128
    elif reliable(32):chosen=32
    result={'pooled':pooled,'preemption_or_oom_log_lines':flags,'chosen_concurrency':chosen,'rule_source':'frozen PROTOCOL.md'}
    if chosen:
        service=184320/pooled[str(chosen)]['responses_per_second']
        nodes=next((n for n in (1,2,4) if service/n<=2700),None)
        if nodes:
            wall=math.ceil((2*service/nodes+600)/900)*900
            if wall<=7200:
                result.update({'status':'READY_TO_STAGE','nodes':nodes,'gpus':nodes*4,
                    'logical_evaluation_responses':184320,'projected_total_service_seconds':service,
                    'projected_service_seconds_per_node':service/nodes,'walltime_seconds_per_node':wall,
                    'ceiling_node_hours':nodes*wall/3600})
            else:result['status']='RESOURCE_AMENDMENT_REQUIRED'
        else:result['status']='RESOURCE_AMENDMENT_REQUIRED'
    else:result['status']='OPERATIONAL_AMENDMENT_REQUIRED'
    return result

def main():
    p=argparse.ArgumentParser();p.add_argument('--pack',required=True);p.add_argument('--run',required=True);p.add_argument('--output',required=True)
    args=p.parse_args();pack=Path(args.pack);run=Path(args.run)
    verified=0
    for line in (pack/'inputs.sha256').read_text().splitlines():
        h,name=line.split('  ',1);assert sha(pack/name)==h;verified+=1
    for line in (run/'results.sha256').read_text().splitlines():
        h,name=line.split('  ',1);assert sha(run/name)==h;verified+=1
    blocks=sorted(p for p in run.iterdir() if p.is_dir() and (p/'configuration.json').exists())
    audits=[audit_block(b,pack) for b in blocks]
    assert len(audits)==4 and sum(a['responses'] for a in audits)==7680
    result={'status':'PASS','audit_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'audit_source_sha256':sha(__file__),'files_verified':verified,'blocks':audits,
            'resource_decision':resource_decision(audits,run),'telemetry':telemetry(run),
            'scope':'Development throughput pilot. No held-out model performance conclusion.'}
    save(args.output,result)
    print(json.dumps({k:v for k,v in result.items() if k!='blocks'},indent=2))

if __name__=='__main__':main()

"""Checkpointed pinned-adapter benchmark; every HTTP attempt is retained."""
from __future__ import annotations
import argparse,collections,concurrent.futures,hashlib,json,os,random,sys,threading,time
from pathlib import Path
from fixtures import canonical,digest
from scoring import score,system_prompt,POLICIES

ROOT=Path(__file__).resolve().parent
MODEL='openai/gpt-oss-120b'
ADAPTER_SHA='dfc3b99ccbac563ae8c1b538e5fc495eff38c0480ac828b7c3567783120746ee'
VOICE_SHA='a44a44808f816bc69fdb4c95391e4774fa532076070cf8183bb8470232cee41a'
URL='http://127.0.0.1:8000/v1'
def utc():return time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def save(path,data):
    p=Path(path);b=(canonical(data)+'\n').encode();tmp=p.with_suffix(p.suffix+'.tmp');tmp.write_bytes(b);tmp.replace(p)
def read_jsonl(p):
    if not p.exists():return []
    b=p.read_bytes()
    if b and not b.endswith(b'\n'):raise RuntimeError('Incomplete journal tail; preserve and reconcile before recovery: '+str(p))
    return [json.loads(x) for x in b.splitlines()]
def verify_inputs():
    rows=[]
    for line in (ROOT/'inputs.sha256').read_text().splitlines():
        expected,name=line.split('  ',1);p=(ROOT/name).resolve()
        if ROOT not in p.parents:raise ValueError('Manifest path leaves package')
        actual=sha(p)
        if actual!=expected:raise RuntimeError('Input hash mismatch: '+name)
        rows.append((name,actual))
    return dict(rows)

class Journal:
    def __init__(self,path):
        self.path=Path(path);read_jsonl(self.path);self.lock=threading.Lock()
        self.stream=self.path.open('ab',buffering=0)
    def append(self,row):
        b=(canonical(row)+'\n').encode()
        with self.lock:
            self.stream.write(b);os.fsync(self.stream.fileno())
    def close(self):self.stream.close()

def plan(rows,contexts,reps,seed):
    tasks=[{'key':f'{r["scenario_id"]}|{p}|{c}|{rep}',
            'scenario_id':r['scenario_id'],'policy':p,'condition':c,'repetition':rep}
           for r in rows for p in POLICIES for c in sorted(contexts) for rep in range(reps)]
    random.Random(seed).shuffle(tasks);return tasks

def reconcile(plan_rows,attempt_rows,final_rows):
    expected={x['key'] for x in plan_rows};final={};attempts=collections.defaultdict(list)
    for r in final_rows:
        k=r['key']
        if k not in expected or k in final:raise RuntimeError('Unknown or duplicate final identity: '+k)
        final[k]=r
    starts=set();ends=set()
    for r in attempt_rows:
        if r['key'] not in expected:raise RuntimeError('Attempt outside frozen plan')
        ident=(r['key'],r['attempt'])
        if r['event']=='start':
            if ident in starts:raise RuntimeError('Duplicate attempt start')
            starts.add(ident)
        elif r['event']=='end':
            if ident not in starts or ident in ends:raise RuntimeError('Unpaired or duplicate attempt end')
            ends.add(ident)
        else:raise RuntimeError('Unknown attempt event')
        attempts[r['key']].append(r)
    for k,r in final.items():
        ident=(k,r['attempt'])
        if ident not in ends:raise RuntimeError('Final result lacks an attempt-end receipt')
        end=next(x for x in attempts[k] if x['event']=='end' and x['attempt']==r['attempt'])
        if r['attempt_result_sha256']!=digest(canonical(end)):raise RuntimeError('Final/attempt hash mismatch')
    return final,attempts

def run_block(args,block_id,concurrency,rows,contexts,repetitions,seed):
    out=Path(args.output)/block_id;out.mkdir(parents=True,exist_ok=True)
    tasks=plan(rows,contexts,repetitions,seed);byid={r['scenario_id']:r for r in rows}
    configuration={'block':block_id,'concurrency':concurrency,'repetitions':repetitions,
                   'order_seed':seed,'model':MODEL,'temperature':0,'max_tokens':8192,
                   'input_manifest_sha256':sha(ROOT/'inputs.sha256'),
                   'plan_sha256':digest(canonical(tasks)),'planned_responses':len(tasks)}
    config_path=out/'configuration.json'
    if config_path.exists():
        if json.loads(config_path.read_text())!=configuration:raise RuntimeError('Resume configuration changed')
    else:save(config_path,configuration);save(out/'plan.json',tasks)
    final,attempts=reconcile(tasks,read_jsonl(out/'attempts.jsonl'),read_jsonl(out/'results.jsonl'))
    journal=Journal(out/'attempts.jsonl');result_journal=Journal(out/'results.jsonl')
    starts=time.monotonic();now=utc();new_completed=0
    # One adapter/session per worker request. No shared mutable HTTP session.
    from aureon.inhouse_ai.llm_adapter import AureonLocalAdapter

    def execute(task):
        scenario=byid[task['scenario_id']];history=attempts.get(task['key'],[])
        last=max((x['attempt'] for x in history),default=0)
        completed=[x for x in history if x['event']=='end']
        successful=[x for x in completed if x['transport_ok']]
        if successful:return successful[0] # crash between durable attempt and final index
        if last>=3:
            if completed:return completed[-1]
            raise RuntimeError('Three unresolved attempts require explicit reconciliation')
        for number in range(last+1,4):
            adapter=AureonLocalAdapter(base_url=URL,model=MODEL,api_key='')
            adapter._session.trust_env=False
            send=adapter._session.send;captured={};began=time.monotonic()
            event={'event':'start','key':task['key'],'attempt':number,'started_utc':utc()}
            def capture(prepared,**kwargs):
                if prepared.url!=URL+'/chat/completions':raise RuntimeError('Non-loopback or unexpected endpoint blocked')
                if 'Authorization' in prepared.headers:raise RuntimeError('Unexpected credential header')
                body=prepared.body.decode('utf-8') if isinstance(prepared.body,bytes) else prepared.body
                captured['request_body_utf8']=body;captured['request_sha256']=digest(body)
                journal.append({**event,'url':prepared.url,**captured})
                response=send(prepared,**kwargs)
                captured['response_body_utf8']=response.content.decode('utf-8')
                captured['response_sha256']=digest(captured['response_body_utf8'])
                captured['status_code']=response.status_code
                return response
            adapter._session.send=capture
            try:
                response=adapter.prompt([{'role':'user','content':canonical(scenario['input'])}],
                    system=system_prompt(contexts[task['condition']],task['policy']),max_tokens=8192,temperature=0)
                text=response.text;raw=response.raw or {};usage=response.usage
                transport_ok=response.stop_reason!='error' and captured.get('status_code')==200
                choice=(raw.get('choices') or [{}])[0]
                finish=choice.get('finish_reason')
                if raw.get('model')!=MODEL:transport_ok=False
                if response.tool_calls:finish='tool_calls'
                error=None if transport_ok else response.text
            except Exception as e:
                text='';usage={};finish=None;transport_ok=False;error=type(e).__name__+': '+str(e)
            finally:adapter._session.close()
            if 'request_sha256' not in captured:
                # Capture pre-HTTP failures as explicit starts too.
                journal.append({**event,'url':None,'request_body_utf8':None,'request_sha256':None})
            record={'event':'end',**task,'attempt':number,'completed_utc':utc(),
                    'elapsed_seconds':time.monotonic()-began,'transport_ok':transport_ok,
                    'transport_error':error,'finish_reason':finish,'text':text,'usage':usage,
                    **{k:v for k,v in captured.items() if k!='request_body_utf8'},
                    'score':score(text,scenario,finish,transport_ok)}
            journal.append(record)
            # Invalid content is a completed model outcome, never retried to get a pass.
            if transport_ok or number==3:return record
        raise AssertionError('Unreachable')

    try:
        remaining=iter(x for x in tasks if x['key'] not in final)
        with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as pool:
            pending={}
            def add_one():
                task=next(remaining,None)
                if task is not None:pending[pool.submit(execute,task)]=task;return True
                return False
            for _ in range(concurrency):add_one()
            while pending:
                done,_=concurrent.futures.wait(pending,return_when=concurrent.futures.FIRST_COMPLETED)
                for future in done:
                    task=pending.pop(future);record=future.result()
                    compact={**task,'attempt':record['attempt'],'attempt_result_sha256':digest(canonical(record)),
                             'score':record['score'],'transport_ok':record['transport_ok'],
                             'finish_reason':record['finish_reason'],'usage':record['usage'],
                             'elapsed_seconds':record['elapsed_seconds']}
                    result_journal.append(compact);final[task['key']]=compact;new_completed+=1;add_one()
                    if new_completed%240==0:print(canonical({'block':block_id,'completed':len(final),'planned':len(tasks),'utc':utc()}),flush=True)
    finally:journal.close();result_journal.close()
    elapsed=time.monotonic()-starts
    final,attempts=reconcile(tasks,read_jsonl(out/'attempts.jsonl'),read_jsonl(out/'results.jsonl'))
    if len(final)!=len(tasks):raise RuntimeError('Incomplete request matrix')
    values=list(final.values())
    metrics={k:sum(r['score'][k] for r in values) for k in ('schema_valid','joint_correct','verdict_correct','action_correct','citation_coverage','grounded_joint_correct')}
    summary={**configuration,'started_utc':now,'completed_utc':utc(),'completed_responses':len(final),
             'new_responses':new_completed,'session_seconds':elapsed,
             'session_responses_per_second':new_completed/elapsed if elapsed else None,
             'transport_failures':sum(not x['transport_ok'] for x in values),**metrics,
             'total_completion_tokens':sum(x['usage'].get('completion_tokens',0) for x in values),
             'total_prompt_tokens':sum(x['usage'].get('prompt_tokens',0) for x in values),
             'hashes':{p.name:sha(p) for p in out.iterdir() if p.is_file() and p.name!='summary.json'}}
    save(out/'summary.json',summary);print(canonical(summary),flush=True)
    return summary

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--repo',required=True);parser.add_argument('--output',required=True)
    parser.add_argument('--mode',choices=['pilot','evaluation'],required=True)
    parser.add_argument('--concurrency',type=int,default=128);parser.add_argument('--shard',type=int,default=0)
    parser.add_argument('--shards',type=int,default=1);args=parser.parse_args()
    assert 0<=args.shard<args.shards and 1<=args.concurrency<=128
    manifest=verify_inputs();repo=Path(args.repo)
    assert sha(repo/'aureon/inhouse_ai/llm_adapter.py')==ADAPTER_SHA
    assert sha(repo/'aureon/vault/voice/vault_voice.py')==VOICE_SHA
    sys.path.insert(0,str(repo))
    expected_env={'AUREON_LLM_PREFER_NATIVE':'0','AUREON_LLM_REQUEST_TIMEOUT_S':'120',
        'AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS':'1','AUREON_AUDIT_MODE':'1',
        'AUREON_LLM_ALLOW_HTTP_IN_AUDIT':'1','AUREON_NO_LIVE_ACTIONS':'1','AUREON_ACTION_MODE':'dry-run',
        'AUREON_LLM_KEEP_ALIVE':'30m'}
    os.environ.update(expected_env)
    for name in ('OPENAI_API_KEY','ANTHROPIC_API_KEY','AUREON_LLM_API_KEY','OLLAMA_API_KEY','AUREON_OLLAMA_API_KEY'):os.environ.pop(name,None)
    contexts=json.loads((ROOT/'contexts.json').read_text())['contexts']
    split='development' if args.mode=='pilot' else 'evaluation'
    rows=read_jsonl(ROOT/(split+'.jsonl'))
    if args.mode=='pilot':
        rows=[r for r in rows if r['instance']<4]
        blocks=[('pilot-0-c32',32,1,90212),('pilot-1-c128',128,1,90213),
                ('pilot-2-c128',128,1,90214),('pilot-3-c32',32,1,90215)]
    else:
        # Every shard samples every template and parity, by adjacent instance pairs.
        rows=[r for r in rows if (r['instance']//2)%args.shards==args.shard]
        blocks=[(f'evaluation-{args.shard:03d}',args.concurrency,2,91300+args.shard)]
    out=Path(args.output);out.mkdir(parents=True,exist_ok=True)
    summaries=[run_block(args,*b[:2],rows,contexts,*b[2:]) for b in blocks]
    save(out/'run-summary.json',{'mode':args.mode,'summaries':summaries,'input_hashes':manifest,'utc':utc()})
    return 2 if any(s['transport_failures'] for s in summaries) else 0

if __name__=='__main__':raise SystemExit(main())

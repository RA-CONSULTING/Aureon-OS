"""Versioned exploratory audit: malformed model output remains a zero-score failure."""
import argparse,collections,dataclasses,datetime,hashlib,importlib.util,json,math,pathlib,statistics,sys

ORIGINAL='186938d13aaf2d69b2ab58bcf598e4af4be14b3fdfa05388fc652f694169f110'
PROTOCOL='bc9300bb86dd566a237425a083bfe98f71d33d690dff6397e4f74a5170e56a0a'
VOICE='a44a44808f816bc69fdb4c95391e4774fa532076070cf8183bb8470232cee41a'
ADAPTER='dfc3b99ccbac563ae8c1b538e5fc495eff38c0480ac828b7c3567783120746ee'
YAML='91a7c4eb74557e0f364661f4189c01b7085d528d19dbb7e39fc2ae5c5b3afe29'
MODEL='openai/gpt-oss-120b'
BASE=pathlib.Path('/projects/u6vs/hnc-organism')

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def canonical(x):return json.dumps(x,sort_keys=True,allow_nan=False,separators=(',',':'))
def require(ok,msg):
    if not ok:raise ValueError(msg)
def pairs(xs):
    d={}
    for k,v in xs:
        require(k not in d,'duplicate JSON key '+k);d[k]=v
    return d
def invalid_constant(x):raise ValueError('nonfinite JSON constant '+x)
def parse(text):return json.loads(text,object_pairs_hook=pairs,parse_constant=invalid_constant)
def load(p):return parse(p.read_text())
def module(p,name):
    spec=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m);return m

def verify_shard(path,shard,m):
    s=load(path/'summary.json'); raw=path/'raw-results.jsonl'; scenarios=path/'scenarios.json'
    expected=dict(source_commit=m.PINNED_COMMIT,source_sha256=VOICE,protocol_sha256=PROTOCOL,model=MODEL,
        synthetic_data_only=True,no_live_actions=True,weight_updates=False,shard_id=shard,shard_count=128,
        conditions=list(m.CONDITIONS),families=list(m.FAMILIES),scenario_count=40,repetitions=2,request_count=960)
    for k,v in expected.items():require(canonical(s.get(k))==canonical(v),'summary '+k)
    require(sha(raw)==s['raw_results_sha256'],'raw hash')
    require(sha(scenarios)==s['scenarios_sha256'],'scenario hash')
    fixtures=m.generate_scenarios(shard,4)
    require(canonical(load(scenarios))==canonical([dataclasses.asdict(x) for x in fixtures]),'scenario regeneration')
    fixture_map={x.scenario_id:x for x in fixtures}
    expected_pairs={(c,x.scenario_id,r) for c in m.CONDITIONS for x in fixtures for r in [0,1]}
    rows=[]; seen=set()
    for line_number,line in enumerate(raw.read_text().splitlines(),1):
        require(bool(line.strip()),'blank receipt row')
        row=parse(line);require(isinstance(row,dict),'nonobject receipt')
        key=(row['condition'],row['scenario'],row['repetition'])
        require(type(row['repetition']) is int and key in expected_pairs and key not in seen,'pair identity or duplicate')
        seen.add(key);scenario=fixture_map[row['scenario']]
        for k,v in dict(shard_id=shard,model=MODEL,family=scenario.family,expected_verdict=scenario.expected_verdict,expected_action=scenario.expected_action).items():
            require(canonical(row.get(k))==canonical(v),'row '+k)
        require(type(row['elapsed_seconds']) in [int,float] and math.isfinite(row['elapsed_seconds']) and row['elapsed_seconds']>=0,'latency')
        require(isinstance(row['response_text'],str),'response text')
        parsed=m.parse_object(row['response_text'])
        require(canonical(parsed)==canonical(row['parsed']),'parsed response replay')
        scored=m.score(scenario,parsed)
        require(canonical(scored)==canonical(row['scoring']),'score recomputation')
        rows.append(row)
    require(seen==expected_pairs and len(rows)==960,'complete paired matrix')
    for condition in m.CONDITIONS:
        cr=[r for r in rows if r['condition']==condition]
        metrics={'mean_score':'score','verdict_accuracy':'verdict_correct','action_accuracy':'action_correct','source_completeness':'sources_complete','mean_brier':'brier','valid_json_rate':'json_valid'}
        require(s['by_condition'][condition]['n']==80,'condition count')
        for name,key in metrics.items():require(round(statistics.fmean(r['scoring'][key] for r in cr),6)==s['by_condition'][condition][name],'summary metric '+name)
    recorded={line.split(maxsplit=1)[1].strip().split('/')[-1]:line.split(maxsplit=1)[0] for line in (path/'input-sha256.txt').read_text().splitlines()}
    for filename,h in {'aureon_full_organism_stage1.py':ORIGINAL,'AUREON_FULL_ORGANISM_STAGE1_PROTOCOL.md':PROTOCOL,'vault_voice.py':VOICE,'llm_adapter.py':ADAPTER,'GPT-OSS_Hopper.yaml':YAML}.items():
        require(recorded.get(filename)==h,'recorded source hash '+filename)
    models=load(path/'models.json')['data'];require(len(models)==1 and models[0]['id']==MODEL,'served model')
    require(models[0]['root'].rstrip('/').endswith('/b5c939de8f754692c1647ca79fbf85e8c1e70f8a'),'model snapshot')
    require((path/'vllm-version.txt').read_text().strip()=='0.15.1','vLLM version')
    return rows,dict(shard=shard,path=str(path),files_sha256={n:sha(path/n) for n in ['summary.json','raw-results.jsonl','scenarios.json','input-sha256.txt','models.json','vllm-version.txt']},invalid_model_json=sum(not r['scoring']['json_valid'] for r in rows))

def main():
    p=argparse.ArgumentParser();p.add_argument('--recovery',type=pathlib.Path);p.add_argument('--output',type=pathlib.Path,required=True);args=p.parse_args()
    old=BASE/'kimi-validation/stage1-gate-fix';pack=old/'jobs/aureon-whole-organism'
    require(sha(pack/'aureon_full_organism_stage1.py')==ORIGINAL,'benchmark bytes')
    require(sha(pack/'AUREON_FULL_ORGANISM_STAGE1_PROTOCOL.md')==PROTOCOL,'protocol bytes')
    m=module(pack/'aureon_full_organism_stage1.py','frozen_stage1')
    ag=module(pack/'aggregate_aureon_full_organism_stage1.py','frozen_aggregate')
    require(tuple(ag.CONDITIONS)==tuple(m.CONDITIONS),'aggregate conditions')
    all_rows={}; receipts=[];missing=[];errors=[]
    for shard in range(128):
        path=old/'runs/aureon-full-organism-s1-kfix-6347216'/('shard-%04d'%shard)
        if not (path/'raw-results.jsonl').is_file():
            if shard==99 and args.recovery is not None:path=args.recovery
            else:missing.append(shard);continue
        try:
            rows,receipt=verify_shard(path,shard,m);all_rows[shard]=rows;receipts.append(receipt)
        except Exception as exc:errors.append(dict(shard=shard,type=type(exc).__name__,message=str(exc)))
    flat=[r for rows in all_rows.values() for r in rows]
    complete=len(all_rows)==128 and not errors and not missing
    result=dict(schema='stage1-retrospective-audit/v1',generated_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        auditor_sha256=sha(pathlib.Path(__file__)),original_benchmark_sha256=ORIGINAL,original_protocol_sha256=PROTOCOL,
        aggregate_helper_sha256=sha(pack/'aggregate_aureon_full_organism_stage1.py'),
        integrity_status='PASS' if not errors else 'FAIL',complete_matrix=complete,verified_shards=len(all_rows),missing=missing,errors=errors,
        response_count=len(flat),invalid_model_json=sum(not r['scoring']['json_valid'] for r in flat),
        historical_frozen_campaign='INVALID - original shard 99 missing and invalid model responses violate frozen stopping rule.',
        amendment='Exploratory retrospective analysis only. Invalid model output is retained with the original zero score, not discarded, repaired or rescored. No original gate is retroactively passed.',
        claim_boundary='Synthetic model-mediated software behaviour. Original permissive parse/schema and scoring are preserved; JSON-valid does not mean full response-schema validity. Self-reported safety flags and serving metadata are not independent proof of no actions or weight identity.',
        temporal_recovery_shards=[99] if args.recovery is not None else [],shard_receipts=receipts)
    if complete:
        result['by_condition']={c:ag.summarize([r for r in flat if r['condition']==c]) for c in m.CONDITIONS}
        result['primary_exploratory']=[ag.compare_by_shard(all_rows,'full_organism','frozen_baseline',metric) for metric in ['score','verdict_accuracy']]
        result['exploratory_advantage_rule_met']=all(x['bootstrap_95_ci'][0]>0 for x in result['primary_exploratory'])
        result['invalid_by_condition']=dict(collections.Counter(r['condition'] for r in flat if not r['scoring']['json_valid']))
    with args.output.open('x') as stream:json.dump(result,stream,indent=2)
    print(json.dumps({k:v for k,v in result.items() if k!='shard_receipts'},indent=2))
    return 0 if complete else 1

if __name__=='__main__':raise SystemExit(main())

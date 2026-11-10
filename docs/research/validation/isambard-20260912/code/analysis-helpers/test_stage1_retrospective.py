import copy,dataclasses,hashlib,json,pathlib,tempfile
import stage1_retrospective_audit as a
m=a.module(pathlib.Path('work/stage1-repair-v1/aureon_full_organism_stage1.py'),'test_frozen_stage1')
fixtures=m.generate_scenarios(0,4);rows=[]
for condition in m.CONDITIONS:
    for scenario in fixtures:
        for repetition in [0,1]:
            parsed=dict(verdict=scenario.expected_verdict,action=scenario.expected_action,cited_sources=list(scenario.required_sources),confidence=.9)
            rows.append(dict(condition=condition,scenario=scenario.scenario_id,repetition=repetition,shard_id=0,model=a.MODEL,family=scenario.family,expected_verdict=scenario.expected_verdict,expected_action=scenario.expected_action,elapsed_seconds=1.,response_text=json.dumps(parsed),parsed=parsed,scoring=m.score(scenario,parsed)))
rows[0].update(response_text='invalid model output',parsed=None,scoring=m.score(fixtures[0],None))
summary=dict(source_commit=m.PINNED_COMMIT,source_sha256=a.VOICE,protocol_sha256=a.PROTOCOL,model=a.MODEL,synthetic_data_only=True,no_live_actions=True,weight_updates=False,shard_id=0,shard_count=128,conditions=list(m.CONDITIONS),families=list(m.FAMILIES),scenario_count=40,repetitions=2,request_count=960,by_condition={})
for c in m.CONDITIONS:
    r=[x for x in rows if x['condition']==c]
    summary['by_condition'][c]={'n':80,**{n:round(sum(x['scoring'][k] for x in r)/80,6) for n,k in {'mean_score':'score','verdict_accuracy':'verdict_correct','action_accuracy':'action_correct','source_completeness':'sources_complete','mean_brier':'brier','valid_json_rate':'json_valid'}.items()}}
with tempfile.TemporaryDirectory(prefix='stage1-audit-test-') as d:
    p=pathlib.Path(d)
    (p/'scenarios.json').write_text(json.dumps([dataclasses.asdict(x) for x in fixtures]))
    (p/'input-sha256.txt').write_text('\n'.join(h+'  /test/'+n for n,h in {'aureon_full_organism_stage1.py':a.ORIGINAL,'AUREON_FULL_ORGANISM_STAGE1_PROTOCOL.md':a.PROTOCOL,'vault_voice.py':a.VOICE,'llm_adapter.py':a.ADAPTER,'GPT-OSS_Hopper.yaml':a.YAML}.items()))
    (p/'models.json').write_text(json.dumps({'data':[{'id':a.MODEL,'root':'/test/b5c939de8f754692c1647ca79fbf85e8c1e70f8a/'}]}))
    (p/'vllm-version.txt').write_text('0.15.1\n')
    def write(rs,s):
        (p/'raw-results.jsonl').write_text(''.join(json.dumps(x)+'\n' for x in rs))
        s=copy.deepcopy(s);s['raw_results_sha256']=a.sha(p/'raw-results.jsonl');s['scenarios_sha256']=a.sha(p/'scenarios.json')
        (p/'summary.json').write_text(json.dumps(s))
    write(rows,summary);verified,receipt=a.verify_shard(p,0,m)
    assert len(verified)==960 and receipt['invalid_model_json']==1 and verified[0]['scoring']['score']==0
    checked=['invalid model retained at zero']
    for label,mutator in [
        ('rescored response',lambda r,s:r[0]['scoring'].update(score=.9)),
        ('duplicate pair',lambda r,s:r.__setitem__(1,copy.deepcopy(r[0]))),
        ('wrong model',lambda r,s:r[1].update(model='wrong-model')),
        ('boolean repetition',lambda r,s:r[1].update(repetition=True)),
        ('false safety declaration',lambda r,s:s.update(no_live_actions=1)),
        ('wrong source pin',lambda r,s:s.update(source_commit='wrong')),
        ('missing pair',lambda r,s:r.pop()),
    ]:
        rs,ss=copy.deepcopy(rows),copy.deepcopy(summary);mutator(rs,ss);write(rs,ss)
        try:a.verify_shard(p,0,m)
        except ValueError:checked.append(label+' rejected')
        else:raise AssertionError(label+' was accepted')
    for text in ['{"x":1,"x":2}','{"x":NaN}']:
        try:a.parse(text)
        except ValueError:checked.append('malformed receipt rejected')
        else:raise AssertionError('malformed receipt accepted')
result={'status':'PASS','checks':checked,'auditor_sha256':a.sha(pathlib.Path('work/stage1_retrospective_audit.py')),'test_sha256':a.sha(pathlib.Path(__file__))}
pathlib.Path('outputs/stage1-retrospective-preflight.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))

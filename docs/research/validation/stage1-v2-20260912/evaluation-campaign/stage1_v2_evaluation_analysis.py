"""Predeclared paired template analysis and exact matrix audit for Stage 1 v2."""
from __future__ import annotations
import argparse,collections,datetime,json,sys
from pathlib import Path
import numpy as np
from stage1_v2_audit import audit_block,records,save,sha

def holm(pvalues):
    order=sorted(range(len(pvalues)),key=lambda i:pvalues[i]);adjusted=[0.]*len(order);previous=0.
    for rank,index in enumerate(order):
        previous=max(previous,min(1.,pvalues[index]*(len(order)-rank)));adjusted[index]=previous
    return adjusted

def contrasts(arm_means,arms):
    index={a:i for i,a in enumerate(arms)}
    full=arm_means[...,index['explicit_policy|full_organism']]
    baseline=arm_means[...,index['explicit_policy|frozen_baseline']]
    neutral=arm_means[...,index['explicit_policy|neutral_labels']]
    enumfull=arm_means[...,index['enum_only|full_organism']]
    enumbase=arm_means[...,index['enum_only|frozen_baseline']]
    return np.stack([full-baseline,full-neutral,(full-baseline)-(enumfull-enumbase)],axis=-1)

def planned_statistics(values,arms,seed=20260912,draws=20000):
    # values shape: 10 families, 6 templates/family, 24 arms.
    if values.shape[:2]!=(10,6):raise ValueError('Frozen analysis requires 10 x 6 template matrix')
    observed_arms=values.mean(axis=(0,1));observed=contrasts(observed_arms,arms)
    rng=np.random.default_rng(seed);boot=[]
    for _ in range(draws//500):
        indices=rng.integers(0,6,size=(500,10,6))
        samples=values[np.arange(10)[None,:,None],indices,:]
        boot.append(contrasts(samples.mean(axis=(1,2)),arms))
    sampled=np.concatenate(boot)
    p=(1+(np.abs(sampled-observed)>=np.abs(observed)).sum(axis=0))/(len(sampled)+1)
    adjusted=holm(p.tolist());interval=np.quantile(sampled,[.025,.975],axis=0)
    family=contrasts(values.mean(axis=1),arms)
    leave=np.array([contrasts(np.delete(values,i,axis=0).mean(axis=(0,1)),arms) for i in range(10)])
    names=['full_minus_baseline_explicit','full_minus_neutral_explicit','full_baseline_policy_interaction']
    return {'arm_macro_joint_accuracy':dict(zip(arms,observed_arms.tolist())),
            'primary_contrasts':{name:{'estimate':float(observed[i]),'percentile_95_interval':interval[:,i].tolist(),
                  'centered_bootstrap_two_sided_p':float(p[i]),'holm_adjusted_p':adjusted[i],
                  'family_effects_in_frozen_family_order':family[:,i].tolist(),
                  'leave_one_family_out_range':[float(leave[:,i].min()),float(leave[:,i].max())]} for i,name in enumerate(names)},
            'bootstrap_draws':len(sampled),'seed':seed,
            'interpretation':'Conditional authored-template summary; related mechanisms limit independence and external generalization.'}

def main():
    p=argparse.ArgumentParser();p.add_argument('--pack',required=True);p.add_argument('--campaign',required=True);p.add_argument('--output',required=True)
    args=p.parse_args();pack=Path(args.pack);campaign=Path(args.campaign);sys.path.insert(0,str(pack))
    from fixtures import FAMILIES
    config=json.loads((campaign/'RESOURCE_PLAN.json').read_text())
    runroots=sorted((campaign/'runs').glob('evaluation-*'))
    assert len(runroots)==config['nodes'],('wrong run count',runroots)
    for line in (pack/'inputs.sha256').read_text().splitlines():
        h,name=line.split('  ',1);assert sha(pack/name)==h
    audits=[];allkeys=set();template_counts=collections.defaultdict(lambda:collections.defaultdict(collections.Counter));arm_counts=collections.defaultdict(collections.Counter)
    for run in runroots:
        for line in (run/'results.sha256').read_text().splitlines():
            h,name=line.split('  ',1);assert sha(run/name)==h,(run,name)
        blocks=[d for d in run.iterdir() if d.is_dir() and (d/'configuration.json').exists()]
        assert len(blocks)==1
        audit=audit_block(blocks[0],pack);audits.append(audit)
        for r in records(blocks[0]/'results.jsonl'):
            assert r['key'] not in allkeys;allkeys.add(r['key'])
        for template,arms in audit['template_joint_counts'].items():
            for arm,counts in arms.items():template_counts[template][arm].update(counts)
        for arm,counts in audit['arms'].items():arm_counts[arm].update(counts)
    contexts=json.loads((pack/'contexts.json').read_text())['contexts']
    from run_benchmark import plan
    evaluation=list(records(pack/'evaluation.jsonl'))
    required={r['key'] for r in plan(evaluation,contexts,2,0)}
    assert allkeys==required and len(allkeys)==184320
    arms=sorted(arm_counts);assert len(arms)==24
    templates=sorted(template_counts);assert len(templates)==60
    values=np.zeros((10,6,24))
    for fi,f in enumerate(FAMILIES):
        ft=sorted(t for t in templates if t.startswith(f+'/'));assert len(ft)==6
        for ti,t in enumerate(ft):
            for ai,a in enumerate(arms):
                c=template_counts[t][a];assert c['n']==128,(t,a,c)
                values[fi,ti,ai]=c['sum']/c['n']
    result={'status':'PASS','completed_responses':len(allkeys),'evaluation_templates':60,
            'input_manifest_sha256':sha(pack/'inputs.sha256'),'analysis_source_sha256':sha(__file__),
            'audit_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'family_order':list(FAMILIES),
            'analysis':planned_statistics(values,arms),'arm_counts':{a:dict(c) for a,c in arm_counts.items()},
            'per_shard_audits':audits}
    save(args.output,result)
    print(json.dumps({k:v for k,v in result.items() if k not in ('per_shard_audits','arm_counts')},indent=2))

if __name__=='__main__':main()

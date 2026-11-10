"""Audit the original terminal matrix, retaining every transport failure."""
from __future__ import annotations
import argparse,collections,csv,datetime,hashlib,json,subprocess,sys
from pathlib import Path
import numpy as np
from stage1_v2_audit import audit_block,records,save,sha
from stage1_v2_evaluation_analysis import planned_statistics

def main():
    p=argparse.ArgumentParser();p.add_argument('--pack',required=True);p.add_argument('--campaign',required=True);p.add_argument('--output',required=True)
    a=p.parse_args();pack=Path(a.pack);campaign=Path(a.campaign);out=Path(a.output)
    out.mkdir(parents=True,exist_ok=False)
    accounting=subprocess.check_output(['sacct','-j','6502171,6502172','--format=JobID,JobIDRaw,State,ExitCode,ElapsedRaw,AllocNodes,AllocTRES','-P'],text=True)
    (out/'accounting.psv').write_text(accounting)
    jobs={r['JobID']:r for r in csv.DictReader(accounting.splitlines(),delimiter='|')}
    for i in range(4):
        job=jobs['6502171_'+str(i)]
        assert job['State']==('FAILED' if i==0 else 'COMPLETED'),job
        assert job['ExitCode']==('2:0' if i==0 else '0:0'),job
    sys.path.insert(0,str(pack))
    from fixtures import FAMILIES
    from run_benchmark import plan
    for line in (pack/'inputs.sha256').read_text().splitlines():
        h,name=line.split('  ',1);assert sha(pack/name)==h
    for line in (campaign/'campaign.sha256').read_text().splitlines():
        h,name=line.split('  ',1);assert sha(campaign/name)==h
    contexts=json.loads((pack/'contexts.json').read_text())['contexts']
    evaluation=list(records(pack/'evaluation.jsonl'))
    allkeys=set();audits=[];arm_counts=collections.defaultdict(collections.Counter)
    template_counts=collections.defaultdict(lambda:collections.defaultdict(collections.Counter))
    forensic_hashes={}
    for i in range(4):
        run=campaign/'runs'/('evaluation-6502171_'+str(i));block=run/('evaluation-'+str(i).zfill(3))
        # A new external inventory covers the failed job's missing end-of-batch manifest.
        # Never add a completion marker or rewrite the old run directory.
        files=sorted(x for x in run.rglob('*') if x.is_file())
        before={str(p.relative_to(run)):sha(p) for p in files}
        save(out/('shard-'+str(i)+'-forensic-hashes.json'),before)
        if i:
            for line in (run/'results.sha256').read_text().splitlines():
                h,name=line.split('  ',1);assert sha(run/name)==h
        rows=[r for r in evaluation if (r['instance']//2)%4==i]
        expected_plan=plan(rows,contexts,2,91300+i)
        assert json.loads((block/'plan.json').read_text())==expected_plan
        audited=audit_block(block,pack);assert audited['unresolved_attempts']==0
        assert audited['responses']==46080
        for r in records(block/'results.jsonl'):
            assert r['key'] not in allkeys;allkeys.add(r['key'])
        for template,arms in audited['template_joint_counts'].items():
            for arm,count in arms.items():template_counts[template][arm].update(count)
        for arm,count in audited['arms'].items():arm_counts[arm].update(count)
        after={str(p.relative_to(run)):sha(p) for p in files}
        assert before==after,'Evidence changed during audit'
        assert {str(p.relative_to(run)) for p in files}=={str(p.relative_to(run)) for p in run.rglob('*') if p.is_file()}
        forensic_hashes[run.name]=before;audits.append(audited)
        print(json.dumps(dict(shard=i,audit='PASS',responses=audited['responses'],transport_failures=audited['summary']['transport_failures'])),flush=True)
    required={r['key'] for r in plan(evaluation,contexts,2,0)}
    assert allkeys==required and len(allkeys)==184320
    arms=sorted(arm_counts);templates=sorted(template_counts)
    assert len(arms)==24 and len(templates)==60
    values=np.zeros((10,6,24))
    for fi,family in enumerate(FAMILIES):
        ft=sorted(t for t in templates if t.startswith(family+'/'));assert len(ft)==6
        for ti,t in enumerate(ft):
            for ai,arm in enumerate(arms):
                c=template_counts[t][arm];assert c['n']==128,(t,arm,c)
                values[fi,ti,ai]=c['sum']/c['n']
    transport=sum(x['summary']['transport_failures'] for x in audits)
    assert transport==39484
    result=dict(schema='stage1-v2-forensic-analysis/v1',evidence_integrity='PASS',
                collection_operational_status='DEGRADED_SERVICE_FAILURE',
                original_scheduler_gate='FAILED',original_audit_job=jobs.get('6502172'),
                final_request_records=len(allkeys),transport_failures=transport,
                successful_transport_responses=len(allkeys)-transport,
                input_manifest_sha256=sha(pack/'inputs.sha256'),analysis_source_sha256=sha(__file__),
                audit_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                family_order=list(FAMILIES),analysis=planned_statistics(values,arms),
                arm_counts={k:dict(v) for k,v in arm_counts.items()},per_shard_audits=audits,
                source_file_hashes=forensic_hashes,
                allocated_node_hours=sum(int(jobs['6502171_'+str(i)]['ElapsedRaw'])*int(jobs['6502171_'+str(i)]['AllocNodes']) for i in range(4))/3600,
                interpretation='Frozen first-run denominator including all transport failures. Degraded operational collection is not a successful model-service experiment; recovery is a separately labelled replication sensitivity.')
    save(out/'analysis.json',result)
    manifest=''.join(sha(p)+'  '+p.name+'\n' for p in sorted(out.iterdir()) if p.is_file() and p.name!='results.sha256')
    (out/'results.sha256').write_text(manifest)
    print(json.dumps({k:result[k] for k in ['evidence_integrity','collection_operational_status','final_request_records','transport_failures','allocated_node_hours']},indent=2))

if __name__=='__main__':main()

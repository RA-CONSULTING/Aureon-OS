from pathlib import Path
import datetime,hashlib,importlib.util,json,subprocess,tarfile,time
import numpy as np

ROOT=Path(__file__).resolve().parent.parent;OUT=ROOT/'outputs/tandem-repair-6506509';OUT.mkdir(exist_ok=True)
REMOTE='/projects/u6vs/hnc-organism/expansion-20260912/tandem-audit-v1'
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for chunk in iter(lambda:f.read(8*1024*1024),b''):h.update(chunk)
    return h.hexdigest()
def main():
    r=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=30','u6vs.aip2.isambard','cat '+REMOTE+'/export-6506509.json'],capture_output=True,check=True,timeout=65)
    export=json.loads(r.stdout);(OUT/'export.json').write_bytes(r.stdout)
    archive=OUT/'verified-tandem-6506509.tar.gz'
    if not archive.exists():subprocess.run(['scp','-o','BatchMode=yes','-o','ConnectTimeout=30','u6vs.aip2.isambard:'+export['archive_path'],str(archive)],check=True,timeout=300)
    assert sha(archive)==export['archive_sha256']
    names=[]
    with tarfile.open(archive) as tar:
        for member in tar.getmembers():
            assert member.isfile() and '/' not in member.name and '..' not in member.name
            names.append(member.name);p=OUT/member.name;data=tar.extractfile(member).read()
            if p.exists():assert p.read_bytes()==data
            else:p.write_bytes(data)
    assert len(names)==export['members']==451 and len(set(names))==451
    audit=json.loads((OUT/'audit-6506509.json').read_text());analysis=json.loads((OUT/'analysis-6506509.json').read_text())
    assert audit['passed'] and audit['full_records']==2322432 and audit['eligible_records']==2308096 and audit['distinct_gpus']==32
    assert sha(OUT/'audit-6506509.json')==export['audit_sha256'] and sha(OUT/'analysis-6506509.json')==export['analysis_sha256']==audit['analysis_sha256']
    for entry in audit['files']:
        p=OUT/entry['name'];assert p.stat().st_size==entry['bytes'] and sha(p)==entry['sha256']
    all_data=[];verified_metrics=0
    for si in range(7):
        columns={}
        for cell in range(32):
            path=OUT/f'full-s{si:02d}-c{cell:02d}.npz';receipt=json.loads(path.with_suffix('.json').read_text());assert sha(path)==receipt['array_sha256']
            with np.load(path,allow_pickle=False) as pack:
                for key in pack.files:
                    if not key.startswith('sample_'):columns.setdefault(key,[]).append(pack[key])
            columns.setdefault('cell',[]).append(np.full(10368,cell,dtype=np.int64))
        d={k:np.concatenate(v) for k,v in columns.items()};all_data.append(d);record=analysis['stages'][si]
        eligible=np.ones(len(d['trial_id']),dtype=bool)
        for cell in [0,15,16,31]:eligible[cell*10368:cell*10368+512]=False
        assert eligible.sum()==329728
        null=(d['truth_model']!=2)|(d['eta']==0);cal=null&eligible&(d['null_split']==0);ev=null&eligible&(d['null_split']==1)
        positive=~null&eligible;target=positive&(d['eta']>=.05)&(d['snr_db']>=0);weak=positive&(d['eta']==.05)&(d['snr_db']==0)
        for method,key in {'D0':'discriminant','sphere_diagnostic':'sphere_score','conditional_glrt':'conditional_glrt'}.items():
            reported=record['methods'][method];hit=np.zeros(len(eligible),bool)
            for threshold in reported['thresholds']:
                group=(d['noise_model']==threshold['noise'])&(d['operator']==threshold['operator'])&(d['snr_db']==threshold['snr_db'])
                training=d[key][cal&group];value=np.percentile(training,99)
                assert value==threshold['threshold'] and len(training)==threshold['calibration_n']
                hit[group]=d[key][group]>value
            def compare(saved,mask):
                nonlocal verified_metrics
                n=int(mask.sum());k=int((hit&mask).sum());assert saved['n']==n and saved['hits']==k
                assert saved['rate']==(k/n if n else None);verified_metrics+=1
            for key,mask in dict(evaluation=ev,target=target,weak=weak,positive=positive).items():compare(reported[key],mask)
            for row in reported['strata']:
                group=(d['noise_model']==row['noise'])&(d['operator']==row['operator'])&(d['snr_db']==row['snr_db'])
                compare(row['fpr'],ev&group);compare(row['target_power'],target&group)
                for truth,saved in row['null_truth_fpr'].items():compare(saved,ev&group&(d['truth_model']==int(truth)))
                for eta,saved in row['eta_power'].items():compare(saved,positive&group&(d['eta']==float(eta)))
            for row in reported['cells']:
                for key,mask in dict(evaluation=ev,target=target,weak=weak,positive=positive).items():compare(row[key],mask&(d['cell']==row['cell']))
        print(json.dumps(dict(stage=si,independent_metric_checks=verified_metrics)),flush=True)
    # Reproduce all frozen bootstrap, sign-flip, Holm and bound summaries locally.
    source=ROOT/'work/tandem-audit-v1/analysis.py';spec=importlib.util.spec_from_file_location('frozen_tandem_analysis',source);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    cfg=json.loads((ROOT/'work/tandem-repair-v1/config.json').read_text());rebuilt=module.analyse(all_data,cfg)
    max_float_error=0
    def equal(a,b):
        nonlocal max_float_error
        if isinstance(a,dict):
            assert set(a)==set(b)
            for k in a:equal(a[k],b[k])
        elif isinstance(a,list):
            assert len(a)==len(b)
            for x,y in zip(a,b):equal(x,y)
        elif isinstance(a,float):
            error=abs(a-b);max_float_error=max(error,max_float_error);assert error<=1e-12+1e-12*abs(a)
        else:assert a==b,(a,b)
    equal(analysis,rebuilt)
    result=dict(status='PASS',verified_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),archive_sha256=export['archive_sha256'],archive_bytes=export['archive_bytes'],members=451,full_records=2322432,eligible_records=2308096,independently_recomputed_rate_cells=verified_metrics,all_frozen_analysis_reproduced=True,analysis_exact=analysis==rebuilt,analysis_maximum_float_difference=max_float_error,remote_independent_saved_channels_verified=audit['saved_channel_records_recomputed'],boundary='All downloaded payload hashes verified. Independent eligibility, thresholds and rate/stratum/cell counts recalculated locally; frozen uncertainty and summaries reproduced. Saved-channel numeric checks are those in the verified remote audit, not a second local waveform regeneration.')
    (OUT/'local-verification.json').write_bytes((json.dumps(result,indent=2)+'\n').encode());print(json.dumps(result,indent=2))

if __name__=='__main__':main()

from pathlib import Path
import datetime,hashlib,json,os,sys,tarfile
import numpy as np
import torch
import numpy_audit as a


ROOT=Path('/projects/u6vs/hnc-organism/expansion-20260912')
PACK=ROOT/'lidar-diagnostic-v2';RESULTS=ROOT/'lidar-diagnostic-results-v2'
sys.path.insert(0,str(PACK));import diagnostic as d


def write(path,obj):
    with Path(path).open('x') as f:json.dump(obj,f,indent=2,allow_nan=False);f.write('\n')


def main():
    torch.set_num_threads(1)
    manifest='255d45a1222770eac0916adbab1233b7480a0b719f8cbca42a30b8681b4cbb13'
    assert a.sha(PACK/'inputs.sha256')==manifest
    for line in (PACK/'inputs.sha256').read_text().splitlines():
        sha,name=line.split(maxsplit=1);assert a.sha(PACK/name)==sha
    accounting=Path(sys.argv[1]).read_text()
    assert '6505275|COMPLETED|0:0|' in accounting and '6505304|COMPLETED|0:0|' in accounting
    audit=Path(__file__).resolve().parent;export=audit/('export-'+os.environ['SLURM_JOB_ID']);export.mkdir(exist_ok=False)
    operators={}
    for gi,grid in enumerate(d.CFG['geometries']):
        det=d.Detector(grid,770000,torch.device('cuda'))
        ops={key:getattr(det,key).detach().cpu().numpy() for key in ['bins','roi','ring','gauss']}
        ops['transfers']=det.transfers[:7].cpu().numpy()
        a.verify_operators(ops,grid['rows']);operators[gi]=ops
        np.savez_compressed(export/f'operators-grid-{gi}.npz',**ops)
    paths=[RESULTS/f'historical-{s:03d}.json' for s in [0,32]]+[RESULTS/f'new-{s:03d}.json' for s in range(128)]
    assert all(p.is_file() for p in paths)
    records=[json.loads(p.read_text()) for p in paths];verifications=[]
    for p,r in zip(paths,records):
        if r['lane']=='new_seeds':
            assert r['seeds']==[1312092600+r['shard'],1912092600+r['shard']]
            assert r['samples']==10000 and r['calibration_samples']==3000 and r['grid_index']==r['shard']%2
        else:assert all(v['equal'] for vals in r['original_comparison'].values() for v in vals.values())
        verifications.append(a.verify_record(p,operators[r['grid_index']],manifest))
        if len(verifications)%16==0:print(json.dumps(dict(verified=len(verifications),expected=130)),flush=True)
    new=records[2:];rank_uuids={str(rank):sorted(set(r['gpu_uuid'] for r in new if r['shard']%4==rank)) for rank in range(4)}
    assert all(len(x)==1 for x in rank_uuids.values()) and len({x[0] for x in rank_uuids.values()})==4
    analysis=a.analyse(new);write(export/'analysis.json',analysis)
    summary=dict(passed=True,verified_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                 records=130,test_examples=sum(r['samples'] for r in records),calibration_examples=sum(r['calibration_samples'] for r in records),
                 input_manifest_sha256=manifest,rank_gpu_uuids=rank_uuids,verifications=verifications,accounting=accounting,
                 numerical_check='Independent NumPy calculation of 16 method scores and all chosen positions on 1040 saved image/template pairs; 20 methods and all strata metrics on every stored example.')
    write(export/'verification.json',summary)
    files=[]
    for p in paths:files.extend([(p,'results/'+p.name),(p.with_suffix('.npz'),'results/'+p.with_suffix('.npz').name)])
    for p in PACK.iterdir():
        if p.is_file() and p.name in ['inputs.sha256','tests-6505275.json','submission.json','full-submission.json','pilot-6505275.out','pilot-6505275.err','full-6505304.out','full-6505304.err']:
            files.append((p,'operations/'+p.name))
    for p in sorted(export.iterdir()):files.append((p,'audit/'+p.name))
    files.append((Path(sys.argv[1]),'audit/accounting.psv'))
    hashes={name:a.sha(p) for p,name in files};write(export/'export-manifest.json',hashes)
    archive=audit/('evidence-'+os.environ['SLURM_JOB_ID']+'.tar.gz')
    with tarfile.open(str(archive),'w:gz') as tar:
        for p,name in files:tar.add(str(p),arcname=name,recursive=False)
        tar.add(str(export/'export-manifest.json'),arcname='export-manifest.json',recursive=False)
    receipt=dict(passed=True,archive=str(archive),archive_sha256=a.sha(archive),bytes=archive.stat().st_size,members=len(files)+1,
                 analysis_sha256=a.sha(export/'analysis.json'),verification_sha256=a.sha(export/'verification.json'))
    write(audit/('receipt-'+os.environ['SLURM_JOB_ID']+'.json'),receipt);print(json.dumps(receipt),flush=True)


if __name__=='__main__':main()

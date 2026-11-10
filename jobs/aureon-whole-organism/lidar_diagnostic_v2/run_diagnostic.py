from pathlib import Path
import argparse, datetime, json, os, time
import numpy as np
import torch
import diagnostic as d


def run(shard,old,out):
    stem=('historical' if old else 'new')+f'-{shard:03d}'
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    result_path=out/(stem+'.json');arrays_path=out/(stem+'.npz')
    if result_path.exists():
        saved=json.loads(result_path.read_text());assert saved['arrays_sha256']==d.evidence_hash(arrays_path)
        assert saved['input_manifest_sha256']==d.evidence_hash(d.ROOT/'inputs.sha256')
        return saved
    assert not arrays_path.exists(),'Unfinalized evidence: preserve and investigate'
    gindex=(0 if shard<32 else 1) if old else shard%2
    grid=d.CFG['geometries'][gindex];device=torch.device('cuda');dtype=torch.float64
    ns=5000 if old else d.CFG['samples'];nc=1500 if old else d.CFG['calibration_samples']
    seeds=[31000000+shard,91000000+shard] if old else [d.CFG['calibration_seed_base']+shard,d.CFG['seed_base']+shard]
    detector=d.Detector(grid,770000+shard,device)
    arrays={};started=time.monotonic();audit={}
    for lane,total,seed in [('cal',nc,seeds[0]),('test',ns,seeds[1])]:
        gen=d.original.make_generator(device,seed);parts={}
        for start in range(0,total,d.CFG['batch_size']):
            size=min(d.CFG['batch_size'],total-start)
            images,labels,cy,cx,nuisance,meta=d.generate(size,grid['rows'],grid['cols'],start,device,dtype,gen,lane=='cal')
            scores,ys,xs=detector.score(images,cy,cx,meta)
            block=dict(scores=scores,labels=labels,cy=cy,cx=cx,nuisance=nuisance,
                       error=((ys-cy[:,None])**2+(xs-cx[:,None])**2).sqrt(),
                       found_y=ys,found_x=xs,**{k:v for k,v in meta.items() if k!='template'})
            for key,value in block.items():parts.setdefault(key,[]).append(value.detach().cpu().numpy())
            if start==0:
                n=min(4,size)
                for key,value in dict(images=images[:n],template=meta['template'][:n]).items():arrays[lane+'_audit_'+key]=value.cpu().numpy()
        for key,pieces in parts.items():arrays[lane+'_'+key]=np.concatenate(pieces)
    thresholds=np.array([d.original.quantile(torch.from_numpy(arrays['cal_scores'][:,j]),.95) for j in range(len(detector.names))])
    reports={};old_compare={}
    truth=arrays['test_labels']
    if old: reference=json.loads((d.ROOT/f'original-{shard:03d}.json').read_text())
    for j,name in enumerate(detector.names):
        r=d.metrics(arrays['test_scores'][:,j],truth,thresholds[j])
        err=arrays['test_error'][truth,j]
        r['median_localisation_error_pixels']=float(np.median(err))
        r['p90_localisation_error_pixels']=float(np.quantile(err,.9))
        r['localised_within_3px_fraction']=float(np.mean(err<=3))
        r['detected_and_localised_within_3px_fraction']=float(np.mean((err<=3)&(arrays['test_scores'][truth,j]>thresholds[j])))
        r['strata']={str(k):d.metrics(arrays['test_scores'][arrays['test_nuisance']==k,j],truth[arrays['test_nuisance']==k],thresholds[j]) for k in range(5)}
        reports[name]=r
        if old and name in detector.original_names:
            prior=reference['methods'][name]
            # Retain actual comparison deltas instead of hiding numerical drift.
            legacy=d.original.binary_metrics(torch.from_numpy(arrays['test_scores'][:,j]),torch.from_numpy(truth),float(thresholds[j]))
            old_compare[name]={k:dict(original=prior[k],rerun=legacy[k],equal=prior[k]==legacy[k],delta=float(legacy[k]-prior[k]))
                               for k in ['auroc','auprc','threshold','tpr','fpr','true_positives','false_positives','positives','negatives']}
            for k,q in [('median',.5),('p90',.9)]:
                v=float(torch.quantile(torch.from_numpy(err),q))
                old_compare[name]['localisation_'+k]=dict(original=prior['localisation_error_pixels'][k],rerun=v,equal=prior['localisation_error_pixels'][k]==v,delta=v-prior['localisation_error_pixels'][k])
    np.savez_compressed(arrays_path,**arrays)
    result=dict(schema='lidar-diagnostic-result/v1',lane='historical_diagnostic' if old else 'new_seeds',
                shard=shard,grid_index=gindex,grid=grid,samples=ns,calibration_samples=nc,seeds=seeds,
                methods=reports,method_order=detector.names,original_comparison=old_compare,
                arrays_sha256=d.evidence_hash(arrays_path),input_manifest_sha256=d.evidence_hash(d.ROOT/'inputs.sha256'),
                elapsed_seconds=time.monotonic()-started,completed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                environment=d.original.environment(device,dtype),cuda_visible_devices=os.environ.get('CUDA_VISIBLE_DEVICES'),
                gpu_uuid=str(torch.cuda.get_device_properties(device).uuid))
    d.write_json(result_path,result);print(json.dumps(dict(stem=stem,seconds=result['elapsed_seconds'],methods={k:round(v['auroc'],4) for k,v in reports.items()})),flush=True)
    return result


if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--output',required=True);a.add_argument('--pilot',action='store_true');a.add_argument('--rank',type=int,default=0);a.add_argument('--ranks',type=int,default=1);args=a.parse_args()
    torch.set_num_threads(1)
    if args.pilot:
        for shard in d.CFG['historical_shards']:run(shard,True,args.output)
    else:
        for shard in d.CFG['new_shards']:
            if shard%args.ranks==args.rank:run(shard,False,args.output)

import json
import numpy as np
from analysis import stage_analysis,comparisons,masks
from independent_channels import white

def main():
    tiny=dict(cell=np.array([0,0,1,15,16,31,31]),trial_id=np.array([0,512,10_000_000,150_000_511,160_000_512,310_000_000,310_000_512]),truth_model=np.zeros(7),eta=np.zeros(7),null_split=np.zeros(7),snr_db=np.zeros(7))
    assert np.array_equal(masks(tiny)['eligible'],[False,True,True,False,True,False,True])
    ids=np.concatenate([c*10_000_000+np.arange(10368) for c in range(32)]);n=len(ids);cell=np.repeat(np.arange(32),10368)
    d=dict(trial_id=ids,cell=cell,eta=np.array([0,.002,.005,.01,.02,.05,.1,.2])[ids%8],snr_db=np.array([-10.,0.,10.,20.])[(ids//8)%4],noise_model=(ids//32)%3,operator=(ids//96)%3,truth_model=(ids//288)%3,null_split=(ids//864)%2)
    m=masks(d);score=np.where(m['positive'],2.,np.where(d['null_split']==0,.2,1.))
    for k in ['discriminant','sphere_score','conditional_glrt']:d[k]=score.copy()
    for k in ['noise_rms','effective_branches','corr_true','selected_weight_before']:d[k]=np.ones(n)
    for k in ['selected_weight_after','sphere_h1_error','sphere_null_error','corr_shift']:d[k]=np.zeros(n)
    result=stage_analysis(d,dict(noise='record_normalised'))
    for method,r in result['methods'].items():
        assert r['evaluation']['rate']==1 and r['target']['rate']==1 and not r['detector_gate_pass']
        assert all(t['threshold']==.2 for t in r['thresholds'])
    same=comparisons([result]*7,repetitions=1000)
    for row in same['rows']:
        assert row['power_sign_flip_p']==1 and row['power_sign_flip_p_holm']==1
        for key in ['target','evaluation']:assert row[key]['pooled_difference']==0 and row[key]['paired_cell_bootstrap_ci95']==[0.,0.]
    for scale in [1,2]:
        n=33;lag=np.abs(np.arange(n)[:,None]-np.arange(n)[None,:])
        for model in range(3):
            C=np.eye(n) if model==0 else (.9**(lag/scale) if model==1 else (.65**2*.97**(lag/scale)+.35**2*.45**(lag/scale))/(.65**2+.35**2))
            W=white(np.eye(n),model,scale).T
            np.testing.assert_allclose(W@C@W.T,np.eye(n),rtol=2e-12,atol=2e-12)
    print(json.dumps(dict(passed=True,checks=['pilot_exclusion_boundaries','calibration_does_not_use_evaluation_nulls','failed_FPR_gate_not_hidden_by_perfect_power','paired_identical_stages_zero_interval_Holm_one','independent_whitening_dense_covariance_identity'])))

if __name__=='__main__':main()

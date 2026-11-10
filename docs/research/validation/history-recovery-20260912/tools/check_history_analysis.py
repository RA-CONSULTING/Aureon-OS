from pathlib import Path
import hashlib,json,sys
import numpy as np
from analyse_hnc_history_results import trends
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/'work/hnc-histories-v1'));from trend import temporal_trend
t=np.arange(25,33,dtype=float)*1048576
rng=np.random.default_rng(20260912);sample=rng.normal(size=(8,1,1,12))
sample[:,:,:,0]=2+1e-5*t[:,None,None];sample[:,:,:,1]=2-1e-5*t[:,None,None];sample[:,:,:,2]=1.
slopes,rms,flags=trends(t,sample)
for j in range(12):
    expected=temporal_trend(t,sample[:,0,0,j])
    assert bool(flags[0,0,j])==expected['flag']
    assert np.isclose(slopes[0,0,j],expected['slope_per_step'],rtol=1e-13,atol=1e-20)
    assert np.isclose(rms[0,0,j],expected['residual_rms'],rtol=1e-13,atol=1e-12)
assert flags[0,0,:3].tolist()==[True,True,False]
source=ROOT/'work/hnc-history-final-audit-v1/analyse_hnc_history_results.py'
assert source.read_bytes()==(ROOT/'work/analyse_hnc_history_results.py').read_bytes()
result=dict(status='PASS',synthetic_series=12,positive_negative_linear_and_constant=True,
            independent_frozen_trend_match=True,source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
            test_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
(ROOT/'outputs/hnc-history-final-analysis-local-checks.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))

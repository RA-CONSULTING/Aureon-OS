import json
import numpy as np
import numpy_audit as a

for scores,truth,auc in [(np.array([1.,1.,1.,1.]),np.array([0,1,0,1]),.5),(np.array([1.,2.,3.,4.]),np.array([0,0,1,1]),1.)]:
    actual=a.metrics(scores,truth,2)
    assert actual['auroc']==auc
    y=truth.astype(bool); brute=np.mean((scores[y,None]>scores[~y][None,:])+.5*(scores[y,None]==scores[~y][None,:]))
    assert actual['auroc']==brute
print(json.dumps(dict(passed=True,checks=['independent_pairwise_and_tie_metrics'])))

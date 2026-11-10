"""Versioned observed-triplet candidate; original curvature and scales are unchanged."""
import numpy as np
import audit_qgita_ucr_robustness as legacy
import benchmark_ucr_confirmatory as canonical

VERSION = 'observed-triplet/v1'


def score_bank(values, missing, train_end, scales, *, require_observed=True):
    values=np.asarray(values,dtype=np.float64);missing=np.asarray(missing)
    if values.ndim!=1 or missing.shape!=values.shape or missing.dtype!=np.bool_:
        raise ValueError('One-dimensional values and an explicit boolean missing mask are required')
    if not 0<train_end<len(values) or np.any(missing[:train_end]):
        raise ValueError('This study requires an unchanged observed training prefix')
    if not np.all(np.isfinite(values[~missing])):
        raise ValueError('Observed values must be finite')
    if scales.shape!=(len(legacy.LATTICE)-2,) or not np.all(np.isfinite(scales)) or np.any(scales<=0):
        raise ValueError('A positive finite scale for every curvature component is required')
    if require_observed:
        # Placeholder values at missing indices have no effect on any eligible score.
        safe=np.where(missing,0.,values)
    else:
        if not np.all(np.isfinite(values)):raise ValueError('The LOCF control must contain finite values')
        safe=values
    scores=np.full(len(values)-train_end,-np.inf,dtype=np.float64)
    winner=np.full(len(scores),-1,dtype=np.int16);eligible_count=np.zeros(len(scores),dtype=np.int16)
    for offset,k in enumerate(range(1,len(legacy.LATTICE)-1)):
        predecessor,centre,successor=map(int,legacy.LATTICE[k-1:k+2])
        decision,absolute=legacy.curvature_components(safe,predecessor,centre,successor)
        starts=decision-successor;keep=decision>=train_end
        if require_observed:keep&=~(missing[starts+predecessor]|missing[starts+centre]|missing[decision])
        target=decision[keep]-train_end;current=absolute[keep]/scales[offset]
        eligible_count[target]+=1
        improve=current>scores[target]
        winner[target[improve]]=k;scores[target[improve]]=current[improve]
    scores[scores==-np.inf]=np.nan
    return dict(scores=scores,winner_component=winner,eligible_components=eligible_count)


def select(bank,train_end,anomaly_start,anomaly_end):
    test=bank['scores'];coverage=int(np.count_nonzero(np.isfinite(test)))
    if not coverage:
        return dict(selected_index_zero_based=None,selected_index_one_based=None,selected_score=None,
                    strict_localisation=False,ucr_localisation=False,abstained=True,
                    scoreable_test_points=0,test_points=len(test),scoreable_fraction=0.)
    full=np.full(train_end+len(test),np.nan,dtype=np.float64);full[train_end:]=test
    result=canonical.select_peak(full,train_end,anomaly_start,anomaly_end)
    result.update(abstained=False,scoreable_test_points=coverage,test_points=len(test),scoreable_fraction=coverage/len(test))
    return result


def selected_triplet(bank,outcome,missing,train_end):
    decision=outcome['selected_index_zero_based']
    if decision is None:return None
    k=int(bank['winner_component'][decision-train_end]);assert k>0
    predecessor,centre,successor=map(int,legacy.LATTICE[k-1:k+2]);start=decision-successor
    indices=[start+predecessor,start+centre,decision]
    return dict(component=k,indices=indices,missing=[bool(missing[i]) for i in indices],
                contains_imputed_value=bool(np.any(missing[indices])))

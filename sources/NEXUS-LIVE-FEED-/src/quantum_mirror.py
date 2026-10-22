from dataclasses import dataclass, asdict
import json, math
from typing import List
from temporal_quantum_security_engine import TemporalQuantumSecurityEngine

Signals = List[List[float]]

def _mean(x): return sum(x)/(len(x) or 1)

def phase_coherence(a: List[float], b: List[float]) -> float:
    n = min(len(a), len(b))
    if n < 64: return 0.0
    am, bm = _mean(a), _mean(b)
    num = sum((a[i]-am)*(b[i]-bm) for i in range(n))
    da  = sum((a[i]-am)**2 for i in range(n))
    db  = sum((b[i]-bm)**2 for i in range(n))
    den = math.sqrt(da*db) + 1e-12
    return max(0.0, min(1.0, num/den))

def normalized_entropy(x: List[float], bins: int = 64) -> float:
    if len(x) < 64: return 0.0
    mn, mx = min(x), max(x) + 1e-12
    hist = [0]*bins
    for v in x:
        idx = max(0, min(bins-1, int(bins * (v - mn)/(mx - mn))))
        hist[idx]+=1
    N=len(x); H=0.0
    for h in hist:
        if h<=0: continue
        p=h/N
        H += -p*math.log(p)
    return 1 - H/(math.log(bins))

@dataclass
class Verdict:
    coherence: float
    purity_avg: float
    purity_each: List[float]
    validated: bool

def validate_aura(signals: Signals, threshold: float = 0.945) -> Verdict:
    heart = signals[0] if len(signals)>0 else []
    gaze  = signals[1] if len(signals)>1 else []
    intent= signals[2] if len(signals)>2 else []
    coh = (phase_coherence(heart,gaze)+phase_coherence(heart,intent)+phase_coherence(gaze,intent))/3.0
    pur = [normalized_entropy(s) for s in [heart,gaze,intent]]
    purity_avg = sum(pur)/(len(pur) or 1.0)
    validated = (coh >= threshold) and (purity_avg >= 0.70)
    return Verdict(coh, purity_avg, pur, validated)

def run_activation(signals: Signals, cfg: dict) -> dict:
    verdict = validate_aura(signals, cfg.get("coherence_threshold", 0.945))
    actions = ["CHECK_CONSENT","SYNC_BASE_FREQUENCY","MEASURE_COHERENCE"]
    proceeded = verdict.validated

    security_engine = TemporalQuantumSecurityEngine()
    # The user_ctx is not fully defined in the document, using signals for now
    security_status = security_engine.initialize(user_ctx=signals)

    if proceeded:
        actions += ["MIRROR_RENDER","STABILIZE","LOG_AUDIT"]
    else:
        actions += ["SOFTEN_PROJECTION"]

    return {
        "verdict": asdict(verdict),
        "proceeded": proceeded,
        "actions": actions,
        "security_engine_status": security_status
    }

def save_audit(payload: dict, path: str):
    with open(path, "w") as f:
        json.dump(payload, f, indent=2)

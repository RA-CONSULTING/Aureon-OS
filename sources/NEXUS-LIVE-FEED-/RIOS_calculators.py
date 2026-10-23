import numpy as np

def coherence_score(X):
    """
    X: shape (T, N) time-series (T samples, N channels/models/teammates)
    returns scalar C in [0,1]
    """
    C = np.corrcoef(X.T)                   # NxN
    C = np.nan_to_num(C, nan=0.0)
    return (C.sum() / C.size + 1)/2        # map [-1,1] -> [0,1]

def fibonacci(n):
    f=[0,1]
    for _ in range(2,n): f.append(f[-1]+f[-2])
    return f

def next_anchor(t_current, dt_base, min_gap=1):
    F = fibonacci(30)
    for Fn in F:
        if Fn >= min_gap:
            candidate = t_current + Fn * dt_base
            if candidate > t_current:
                return candidate

def phi_growth(r0, cycles):
    phi=(1+5**0.5)/2
    r = [r0]
    for _ in range(cycles):
        r.append(r[-1]*np.exp(np.log(phi)))
    return np.array(r)

def unity_probability(C, theta, prime_index, schumann_spike):
    """
    C: current coherence score
    theta: phase alignment (0 = perfect)
    prime_index: is current position a prime number?
    schumann_spike: is Schumann resonance elevated?
    returns: probability [0,1] of imminent ego-death event
    """
    p = 0.0
    
    # High coherence increases probability
    if C > 0.75:
        p += 0.3
    
    # Phase alignment increases probability
    if theta < 0.1:
        p += 0.3
    
    # Prime index increases probability
    if prime_index:
        p += 0.2
    
    # Schumann spike increases probability
    if schumann_spike:
        p += 0.2
    
    return min(p, 1.0)

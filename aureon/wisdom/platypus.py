#!/usr/bin/env python3
"""
PLATYPUS / SONG OF THE SPHAERAE
===============================

Mathematical coherence framework for planetary ephemeris validation
and coupling analysis with geomagnetic indices.

Implements the full process tree:
- Substrate State S(t)
- Geometric Coherence Q(t)
- Forcing Context H(t)
- Echo Memory E(t)
- Observer Term O(t)
- Lambda Field Λ(t)
- Coherence Score Γ(t)
- Lighthouse Events L(t)
- Validation Gates (lag-corr, spectral coherence, epoch analysis)

Gary Leckey & GitHub Copilot | December 2025
"""

from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from scipy.signal import coherence, detrend
from scipy.stats import pearsonr
import warnings

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class PlatypusConfig:
    """Configuration for Platypus coherence computation."""
    
    # Time grid
    dt_hours: int = 6                    # Sampling interval (hours)
    
    # Lambda weights (must sum to 1.0)
    w_S: float = 0.20                    # Substrate weight
    w_Q: float = 0.25                    # Geometric coherence weight
    w_H: float = 0.25                    # Forcing context weight
    w_E: float = 0.20                    # Echo memory weight
    w_O: float = 0.10                    # Observer term weight
    
    # Memory parameters
    alpha: float = 0.2                   # Exponential decay for E(t)
    memory_window: int = 8               # Alternative: W-step moving average
    use_exponential_memory: bool = True  # True=exponential, False=moving avg
    
    # Observer inertia
    beta: float = 0.1                    # Self-reference scaling
    
    # Lighthouse event thresholds
    conjunction_threshold_deg: float = 3.0   # ε for conjunctions
    opposition_threshold_deg: float = 3.0    # ε for oppositions
    
    # Validation parameters
    max_lag_hours: int = 72              # ±3 days for lag correlation
    n_permutations: int = 2000           # Block shuffle permutations
    block_hours: int = 24                # Block size for shuffle
    epoch_window_hours: int = 72         # ±3 days around events
    coherence_nperseg: int = 256         # FFT segment length
    
    def __post_init__(self):
        # Normalize weights
        total = self.w_S + self.w_Q + self.w_H + self.w_E + self.w_O
        if abs(total - 1.0) > 1e-6:
            self.w_S /= total
            self.w_Q /= total
            self.w_H /= total
            self.w_E /= total
            self.w_O /= total


# ═══════════════════════════════════════════════════════════════════════════════
# II. SUBSTRATE STATE — S(t)
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class SubstrateState:
    """Raw observable state vector for a celestial body."""
    datetime: datetime
    planet: str
    alpha: float      # Right ascension (degrees)
    delta: float      # Declination (degrees)
    epsilon: float    # Solar elongation (degrees)
    r: float          # Heliocentric distance (AU)
    
    def to_vector(self) -> np.ndarray:
        """Return state as numpy vector [α, δ, ε, r]."""
        return np.array([self.alpha, self.delta, self.epsilon, self.r])


def load_substrate_from_csv(filepath: str) -> pd.DataFrame:
    """
    Load substrate states from ephemeris CSV.
    
    Expected columns: datetime, planet, ra_deg, dec_deg, elong_deg, [r_au]
    """
    df = pd.read_csv(filepath, parse_dates=['datetime'])
    
    # Rename to standard names
    rename_map = {
        'ra_deg': 'alpha',
        'dec_deg': 'delta', 
        'elong_deg': 'epsilon',
        'r_au': 'r'
    }
    df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})
    
    # Default r to 1.0 if not present
    if 'r' not in df.columns:
        df['r'] = 1.0
        
    return df


# ═══════════════════════════════════════════════════════════════════════════════
# III. GEOMETRIC COHERENCE — Q(t)
# ═══════════════════════════════════════════════════════════════════════════════

def compute_geometric_coherence(epsilon_deg: np.ndarray) -> np.ndarray:
    """
    Compute angular alignment score q_i(t) = |cos(ε_i(t))|
    
    Q → 1: strong alignment (conjunction/opposition)
    Q → 0: orthogonal/incoherent geometry
    """
    epsilon_rad = np.radians(epsilon_deg)
    return np.abs(np.cos(epsilon_rad))


def aggregate_geometric_coherence(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute aggregate Q(t) = (1/N) Σ q_i(t) per timestamp.
    """
    df = df.copy()
    df['q'] = compute_geometric_coherence(df['epsilon'].values)
    
    agg = df.groupby('datetime').agg({
        'q': 'mean'
    }).rename(columns={'q': 'Q'})
    
    return agg


# ═══════════════════════════════════════════════════════════════════════════════
# IV. FORCING CONTEXT — H(t)
# ═══════════════════════════════════════════════════════════════════════════════

def compute_forcing(r_au: np.ndarray) -> np.ndarray:
    """
    Distance-based forcing f_i(t) = 1 / r_i(t)²
    Inverse-square law.
    """
    r_safe = np.maximum(r_au, 1e-6)  # Prevent division by zero
    return 1.0 / (r_safe ** 2)


def aggregate_forcing(df: pd.DataFrame, solar_modulation: Optional[pd.Series] = None) -> pd.DataFrame:
    """
    Compute aggregate H(t) = (1/N) Σ f_i(t) per timestamp.
    
    Optional: multiply by solar modulation g(A(t)).
    """
    df = df.copy()
    df['f'] = compute_forcing(df['r'].values)
    
    agg = df.groupby('datetime').agg({
        'f': 'mean'
    }).rename(columns={'f': 'H'})
    
    # Optional solar modulation
    if solar_modulation is not None:
        agg = agg.join(solar_modulation, how='left')
        if 'F107' in agg.columns:
            # Normalize F107 to [0.5, 1.5] range
            f107_norm = (agg['F107'] - agg['F107'].min()) / (agg['F107'].max() - agg['F107'].min() + 1e-9)
            agg['H'] = agg['H'] * (0.5 + f107_norm)
    
    return agg


# ═══════════════════════════════════════════════════════════════════════════════
# V. ECHO MEMORY — E(t)
# ═══════════════════════════════════════════════════════════════════════════════

def compute_echo_memory_exponential(lambda_series: np.ndarray, alpha: float) -> np.ndarray:
    """
    Exponential decay memory: E(t_k) = α·E(t_{k-1}) + (1-α)·Λ(t_k)
    """
    E = np.zeros_like(lambda_series)
    E[0] = lambda_series[0]
    
    for k in range(1, len(lambda_series)):
        E[k] = alpha * E[k-1] + (1 - alpha) * lambda_series[k]
    
    return E


def compute_echo_memory_moving_avg(lambda_series: np.ndarray, window: int) -> np.ndarray:
    """
    Moving average memory: E(t_k) = (1/W) Σ_{j=0}^{W-1} Λ(t_{k-j})
    """
    E = pd.Series(lambda_series).rolling(window=window, min_periods=1).mean().values
    return E


# ═══════════════════════════════════════════════════════════════════════════════
# VI. OBSERVER TERM — O(t)
# ═══════════════════════════════════════════════════════════════════════════════

def compute_observer_term(lambda_series: np.ndarray, beta: float) -> np.ndarray:
    """
    Self-reference / inertia: O(t) = β·Λ(t - Δt)
    """
    O = np.zeros_like(lambda_series)
    O[0] = beta * lambda_series[0]
    
    for k in range(1, len(lambda_series)):
        O[k] = beta * lambda_series[k-1]
    
    return O


# ═══════════════════════════════════════════════════════════════════════════════
# VII. LAMBDA FIELD — Λ(t)
# ═══════════════════════════════════════════════════════════════════════════════

def compute_lambda_field(
    S_prime: np.ndarray,
    Q: np.ndarray,
    H: np.ndarray,
    config: PlatypusConfig
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Unified state equation:
    Λ(t) = w_S·S'(t) + w_Q·Q(t) + w_H·H(t) + w_E·E(t) + w_O·O(t)
    
    Returns: (Lambda, E, O)
    """
    n = len(Q)
    Lambda = np.zeros(n)
    E = np.zeros(n)
    O = np.zeros(n)
    
    # Initialize first step
    Lambda[0] = (config.w_S * S_prime[0] + 
                 config.w_Q * Q[0] + 
                 config.w_H * H[0])
    E[0] = Lambda[0]
    O[0] = config.beta * Lambda[0]
    
    # Iterate with memory and observer feedback
    for k in range(1, n):
        # Echo memory
        if config.use_exponential_memory:
            E[k] = config.alpha * E[k-1] + (1 - config.alpha) * Lambda[k-1]
        else:
            # Moving average (look back up to window steps)
            start = max(0, k - config.memory_window)
            E[k] = np.mean(Lambda[start:k])
        
        # Observer term (previous step)
        O[k] = config.beta * Lambda[k-1]
        
        # Lambda field
        Lambda[k] = (config.w_S * S_prime[k] + 
                     config.w_Q * Q[k] + 
                     config.w_H * H[k] + 
                     config.w_E * E[k] + 
                     config.w_O * O[k])
    
    return Lambda, E, O


# ═══════════════════════════════════════════════════════════════════════════════
# VIII. COHERENCE SCORE — Γ(t)
# ═══════════════════════════════════════════════════════════════════════════════

def compute_gamma(lambda_field: np.ndarray) -> np.ndarray:
    """
    Normalize Lambda to [0,1]:
    Γ(t) = (Λ(t) - min(Λ)) / (max(Λ) - min(Λ))
    """
    lam_min = np.min(lambda_field)
    lam_max = np.max(lambda_field)
    denom = max(1e-9, lam_max - lam_min)
    
    return (lambda_field - lam_min) / denom


# ═══════════════════════════════════════════════════════════════════════════════
# IX. LIGHTHOUSE EVENTS — L(t)
# ═══════════════════════════════════════════════════════════════════════════════

def detect_lighthouse_events(
    df: pd.DataFrame,
    config: PlatypusConfig
) -> pd.DataFrame:
    """
    Detect structural event triggers:
    
    L2(t) = 1 if |ε_i(t)| < ε_thresh OR |ε_i(t) - π| < ε_thresh
    
    Returns per-timestamp event flags.
    """
    events = []
    
    for _, row in df.iterrows():
        epsilon = row['epsilon']
        
        # Conjunction: elongation near 0
        is_conjunction = epsilon <= config.conjunction_threshold_deg
        
        # Opposition: elongation near 180°
        is_opposition = abs(epsilon - 180.0) <= config.opposition_threshold_deg
        
        L2 = 1 if (is_conjunction or is_opposition) else 0
        
        events.append({
            'datetime': row['datetime'],
            'planet': row['planet'],
            'L2_event': L2,
            'is_conjunction': int(is_conjunction),
            'is_opposition': int(is_opposition)
        })
    
    event_df = pd.DataFrame(events)
    
    # Aggregate: any planet event at this time
    agg = event_df.groupby('datetime').agg({
        'L2_event': 'max',
        'is_conjunction': 'max',
        'is_opposition': 'max'
    })
    
    return agg


# ═══════════════════════════════════════════════════════════════════════════════
# X. VALIDATION EQUATIONS (Gate 3)
# ═══════════════════════════════════════════════════════════════════════════════

def lagged_cross_correlation(
    gamma: np.ndarray,
    y: np.ndarray,
    max_lag_steps: int
) -> pd.DataFrame:
    """
    Test coupling: ρ(τ) = corr(Γ(t), Y(t+τ))
    
    Scan τ ∈ [-max_lag, +max_lag] to detect lead/lag relationships.
    """
    results = []
    
    for lag in range(-max_lag_steps, max_lag_steps + 1):
        if lag < 0:
            g = gamma[-lag:]
            yy = y[:lag]
        elif lag > 0:
            g = gamma[:-lag]
            yy = y[lag:]
        else:
            g = gamma
            yy = y
        
        if len(g) > 10:
            r, p = pearsonr(g, yy)
        else:
            r, p = np.nan, np.nan
        
        results.append({
            'lag_steps': lag,
            'r': r,
            'p_value': p
        })
    
    return pd.DataFrame(results)


def spectral_coherence(
    gamma: np.ndarray,
    y: np.ndarray,
    fs: float,
    nperseg: int = 256
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Frequency-domain coupling:
    C_ΓY(f) = |S_ΓY(f)|² / (S_ΓΓ(f) · S_YY(f))
    
    Returns: (frequencies, coherence)
    """
    nperseg = min(nperseg, len(gamma) // 2)
    if nperseg < 8:
        return np.array([]), np.array([])
    
    f, Cxy = coherence(gamma, y, fs=fs, nperseg=nperseg)
    return f, Cxy


def superposed_epoch_analysis(
    y: np.ndarray,
    event_indices: np.ndarray,
    window_steps: int
) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
    """
    Mean response around Lighthouse events:
    Ȳ(τ) = (1/N) Σ Y(t_k + τ) for L(t_k) = 1
    
    Returns: (epoch_matrix, mean_epoch)
    """
    epochs = []
    
    for idx in event_indices:
        start = idx - window_steps
        end = idx + window_steps + 1
        
        if start >= 0 and end <= len(y):
            epochs.append(y[start:end])
    
    if not epochs:
        return None, None
    
    epoch_matrix = np.vstack(epochs)
    mean_epoch = epoch_matrix.mean(axis=0)
    
    return epoch_matrix, mean_epoch


def block_shuffle(x: np.ndarray, block_len: int, iteration: int = 1) -> np.ndarray:
    """
    Block-shuffle to preserve autocorrelation for null hypothesis testing.
    """
    x = np.asarray(x)
    n = len(x)
    nb = n // block_len
    
    if nb < 2:
        return np.roll(x, iteration % max(1, n))
    
    blocks = x[:nb * block_len].reshape(nb, block_len)
    step = (2 * iteration + 1) % nb
    while math.gcd(step, nb) != 1:
        step = (step + 1) % nb or 1
    order = (np.arange(nb) * step + iteration) % nb
    xs = blocks[order].reshape(-1)
    
    # Append remainder
    if nb * block_len < n:
        xs = np.concatenate([xs, x[nb * block_len:]])
    
    return xs


def permutation_test(
    gamma: np.ndarray,
    y: np.ndarray,
    config: PlatypusConfig,
    test_statistic: str = 'correlation'
) -> Dict[str, float]:
    """
    Compute permutation p-value for null hypothesis.
    
    test_statistic: 'correlation' | 'coherence_peak'
    """
    block_len = config.block_hours // config.dt_hours
    
    # Observed statistic
    if test_statistic == 'correlation':
        obs_stat = pearsonr(gamma, y)[0]
    elif test_statistic == 'coherence_peak':
        fs = 1.0 / (config.dt_hours * 3600.0)
        _, Cxy = spectral_coherence(gamma, y, fs, config.coherence_nperseg)
        obs_stat = np.nanmax(Cxy) if len(Cxy) > 0 else 0.0
    else:
        raise ValueError(f"Unknown test statistic: {test_statistic}")
    
    # Permutation distribution
    null_stats = []
    for iteration in range(config.n_permutations):
        gamma_shuffled = block_shuffle(gamma, block_len, iteration + 1)
        
        if test_statistic == 'correlation':
            stat = pearsonr(gamma_shuffled, y)[0]
        else:
            _, Cxy = spectral_coherence(gamma_shuffled, y, fs, config.coherence_nperseg)
            stat = np.nanmax(Cxy) if len(Cxy) > 0 else 0.0
        
        null_stats.append(stat)
    
    null_stats = np.array(null_stats)
    p_value = float(np.mean(np.abs(null_stats) >= abs(obs_stat)))
    
    return {
        'observed': obs_stat,
        'p_value': p_value,
        'null_mean': float(np.mean(null_stats)),
        'null_std': float(np.std(null_stats))
    }


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN ORCHESTRATOR
# ═══════════════════════════════════════════════════════════════════════════════

class Platypus:
    """
    Main Platypus/Song of the Sphaerae engine.
    
    Computes normalized coherence Γ(t) from geometric alignment,
    forcing context, memory, and self-reference, then validates
    coupling to physical observables.
    """
    
    def __init__(self, config: Optional[PlatypusConfig] = None):
        self.config = config or PlatypusConfig()
        self.substrate_df: Optional[pd.DataFrame] = None
        self.timeseries_df: Optional[pd.DataFrame] = None
        self.validation_results: Dict[str, Any] = {}
    
    def load_ephemeris(self, filepath: str) -> 'Platypus':
        """Load ephemeris data (substrate states)."""
        self.substrate_df = load_substrate_from_csv(filepath)
        print(f"✓ Loaded {len(self.substrate_df)} substrate states")
        return self
    
    def load_horizons_r(self, filepath: str) -> 'Platypus':
        """Merge heliocentric distances from Horizons."""
        if self.substrate_df is None:
            raise ValueError("Load ephemeris first")
        
        try:
            hz = pd.read_csv(filepath, parse_dates=['datetime'])
            if 'r_au' in hz.columns:
                hz = hz.rename(columns={'r_au': 'r'})
            
            self.substrate_df = self.substrate_df.merge(
                hz[['datetime', 'planet', 'r']],
                on=['datetime', 'planet'],
                how='left',
                suffixes=('_old', '')
            )
            
            # Use new r if available, else keep old
            if 'r_old' in self.substrate_df.columns:
                self.substrate_df['r'] = self.substrate_df['r'].fillna(self.substrate_df['r_old'])
                self.substrate_df = self.substrate_df.drop(columns=['r_old'])
            
            print(f"✓ Merged heliocentric distances")
        except FileNotFoundError:
            print("⚠ Horizons r_au file not found, using default r=1.0")
        
        return self
    
    def compute_coherence(self) -> 'Platypus':
        """
        Compute full Platypus coherence pipeline:
        S(t) → Q(t) → H(t) → E(t) → O(t) → Λ(t) → Γ(t)
        """
        if self.substrate_df is None:
            raise ValueError("Load ephemeris first")
        
        df = self.substrate_df.copy()
        
        # Ensure r column exists
        if 'r' not in df.columns:
            df['r'] = 1.0
        
        print("Computing Platypus coherence...")
        
        # III. Geometric Coherence Q(t)
        df['q'] = compute_geometric_coherence(df['epsilon'].values)
        
        # IV. Forcing Context H(t)
        df['h'] = compute_forcing(df['r'].values)
        
        # Aggregate per timestamp
        agg = df.groupby('datetime').agg({
            'q': 'mean',
            'h': 'mean',
            'alpha': 'mean',  # S'(t) proxy: mean RA
            'epsilon': 'mean'  # For reference
        }).sort_index()
        
        agg = agg.rename(columns={'q': 'Q', 'h': 'H'})
        
        # S'(t): use geometric coherence as substrate scalar proxy
        S_prime = agg['Q'].values
        Q = agg['Q'].values
        H = agg['H'].values
        
        # VII. Lambda Field (with V. Memory and VI. Observer)
        Lambda, E, O = compute_lambda_field(S_prime, Q, H, self.config)
        
        agg['Lambda'] = Lambda
        agg['E'] = E
        agg['O'] = O
        
        # VIII. Coherence Score Γ(t)
        agg['Gamma'] = compute_gamma(Lambda)
        
        # IX. Lighthouse Events
        events = detect_lighthouse_events(df, self.config)
        agg = agg.join(events, how='left')
        agg['L2_event'] = agg['L2_event'].fillna(0).astype(int)
        
        # Reset index for output
        self.timeseries_df = agg.reset_index()
        
        print(f"✓ Computed coherence for {len(self.timeseries_df)} timestamps")
        print(f"  Γ range: [{agg['Gamma'].min():.4f}, {agg['Gamma'].max():.4f}]")
        print(f"  Lighthouse events: {agg['L2_event'].sum()}")
        
        return self
    
    def validate_against_index(
        self,
        index_df: pd.DataFrame,
        target_col: str = 'Kp'
    ) -> 'Platypus':
        """
        Run Gate 3 validation against geomagnetic index.
        
        index_df: DataFrame with 'datetime' and target_col columns.
        """
        if self.timeseries_df is None:
            raise ValueError("Compute coherence first")
        
        print(f"\nValidating against {target_col}...")
        
        # Align time series
        ts = self.timeseries_df.set_index('datetime')
        idx = index_df.set_index('datetime') if 'datetime' in index_df.columns else index_df
        
        # Resample to common cadence
        dt_str = f"{self.config.dt_hours}H"
        ts_resampled = ts.resample(dt_str).mean()
        idx_resampled = idx.resample(dt_str).mean()
        
        # Join
        combined = ts_resampled.join(idx_resampled[[target_col]], how='inner')
        combined = combined.dropna(subset=['Gamma', target_col])
        
        if len(combined) < 20:
            print(f"⚠ Insufficient overlapping data ({len(combined)} points)")
            return self
        
        # Detrend and standardize
        gamma = detrend(combined['Gamma'].values)
        y = detrend(combined[target_col].values)
        
        gamma = (gamma - gamma.mean()) / (gamma.std() + 1e-12)
        y = (y - y.mean()) / (y.std() + 1e-12)
        
        # X.9. Lagged Cross-Correlation
        max_lag_steps = self.config.max_lag_hours // self.config.dt_hours
        lag_corr = lagged_cross_correlation(gamma, y, max_lag_steps)
        best_lag = lag_corr.loc[lag_corr['r'].abs().idxmax()]
        
        # Permutation test for correlation
        corr_perm = permutation_test(gamma, y, self.config, 'correlation')
        
        print(f"\n[TEST 1] Lagged Cross-Correlation")
        print(f"  Best lag: {int(best_lag['lag_steps'])} steps ({int(best_lag['lag_steps']) * self.config.dt_hours}h)")
        print(f"  Best r: {best_lag['r']:.4f}")
        print(f"  Permutation p-value: {corr_perm['p_value']:.4f}")
        
        # X.10. Spectral Coherence
        fs = 1.0 / (self.config.dt_hours * 3600.0)
        freq, coh = spectral_coherence(gamma, y, fs, self.config.coherence_nperseg)
        
        coh_perm = permutation_test(gamma, y, self.config, 'coherence_peak')
        
        print(f"\n[TEST 2] Spectral Coherence")
        print(f"  Peak coherence: {coh_perm['observed']:.4f}")
        print(f"  Permutation p-value: {coh_perm['p_value']:.4f}")
        
        # X.11. Superposed Epoch Analysis
        event_idx = np.where(combined['L2_event'].values >= 1)[0]
        window_steps = self.config.epoch_window_hours // self.config.dt_hours
        
        epoch_result = {'n_events': len(event_idx)}
        if len(event_idx) > 0:
            epoch_matrix, mean_epoch = superposed_epoch_analysis(y, event_idx, window_steps)
            
            if mean_epoch is not None:
                obs_peak = float(np.max(np.abs(mean_epoch)))
                
                # Permutation for epoch
                null_peaks = []
                for _ in range(1000):
                    rand_idx = np.random.choice(
                        np.arange(window_steps, len(y) - window_steps),
                        size=len(event_idx),
                        replace=False
                    )
                    _, me = superposed_epoch_analysis(y, rand_idx, window_steps)
                    if me is not None:
                        null_peaks.append(np.max(np.abs(me)))
                
                p_epoch = float(np.mean(np.array(null_peaks) >= obs_peak)) if null_peaks else 1.0
                
                epoch_result['obs_peak'] = obs_peak
                epoch_result['p_value'] = p_epoch
                
                print(f"\n[TEST 3] Superposed Epoch (Lighthouse)")
                print(f"  Events: {len(event_idx)}")
                print(f"  Epoch peak: {obs_peak:.4f}")
                print(f"  Permutation p-value: {p_epoch:.4f}")
        
        # Store results
        self.validation_results = {
            'samples': len(combined),
            'lag_correlation': {
                'best_lag_steps': int(best_lag['lag_steps']),
                'best_lag_hours': int(best_lag['lag_steps']) * self.config.dt_hours,
                'best_r': float(best_lag['r']),
                'p_value': corr_perm['p_value']
            },
            'spectral_coherence': {
                'peak': coh_perm['observed'],
                'p_value': coh_perm['p_value']
            },
            'epoch_analysis': epoch_result,
            'lag_corr_df': lag_corr,
            'coherence_spectrum': pd.DataFrame({'freq_hz': freq, 'coherence': coh})
        }
        
        return self
    
    def save_timeseries(self, filepath: str = 'radar_timeseries.csv') -> 'Platypus':
        """Save computed time series to CSV."""
        if self.timeseries_df is None:
            raise ValueError("Compute coherence first")
        
        self.timeseries_df.to_csv(filepath, index=False)
        print(f"\n✓ Wrote {filepath}")
        print(f"  Columns: {list(self.timeseries_df.columns)}")
        
        return self
    
    def save_validation_artifacts(self, prefix: str = 'gate3') -> 'Platypus':
        """Save validation CSVs."""
        if not self.validation_results:
            print("⚠ No validation results to save")
            return self
        
        if 'lag_corr_df' in self.validation_results:
            self.validation_results['lag_corr_df'].to_csv(f'{prefix}_lag_corr.csv', index=False)
            print(f"✓ Wrote {prefix}_lag_corr.csv")
        
        if 'coherence_spectrum' in self.validation_results:
            self.validation_results['coherence_spectrum'].to_csv(f'{prefix}_coherence.csv', index=False)
            print(f"✓ Wrote {prefix}_coherence.csv")
        
        return self
    
    def summary(self) -> str:
        """Return validation summary."""
        if not self.validation_results:
            return "No validation performed yet."
        
        r = self.validation_results
        lines = [
            "═" * 60,
            "PLATYPUS VALIDATION SUMMARY",
            "═" * 60,
            f"Samples: {r['samples']}",
            "",
            f"Lag Correlation:",
            f"  Best r = {r['lag_correlation']['best_r']:.4f} at lag {r['lag_correlation']['best_lag_hours']}h",
            f"  p-value = {r['lag_correlation']['p_value']:.4f}",
            "",
            f"Spectral Coherence:",
            f"  Peak = {r['spectral_coherence']['peak']:.4f}",
            f"  p-value = {r['spectral_coherence']['p_value']:.4f}",
            "",
            f"Epoch Analysis:",
            f"  Events = {r['epoch_analysis'].get('n_events', 0)}",
        ]
        
        if 'obs_peak' in r['epoch_analysis']:
            lines.extend([
                f"  Peak = {r['epoch_analysis']['obs_peak']:.4f}",
                f"  p-value = {r['epoch_analysis']['p_value']:.4f}",
            ])
        
        lines.append("═" * 60)
        
        # Final verdict
        sig_count = 0
        if r['lag_correlation']['p_value'] < 0.05:
            sig_count += 1
        if r['spectral_coherence']['p_value'] < 0.05:
            sig_count += 1
        if r['epoch_analysis'].get('p_value', 1.0) < 0.05:
            sig_count += 1
        
        if sig_count >= 2:
            verdict = "✓ COHERENCE VALIDATED (≥2 tests significant at p<0.05)"
        elif sig_count == 1:
            verdict = "◐ MARGINAL (1 test significant)"
        else:
            verdict = "✗ NOT SIGNIFICANT (no tests passed p<0.05)"
        
        lines.append(verdict)
        lines.append("═" * 60)
        
        return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════════
# CLI ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    """Run Platypus pipeline from command line."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Platypus Coherence Engine')
    parser.add_argument('--ephemeris', default='radar_ephem_skyfield_de440.csv',
                        help='Ephemeris CSV file')
    parser.add_argument('--horizons', default='radar_ephem_horizons_truth_with_r.csv',
                        help='Horizons truth CSV (optional)')
    parser.add_argument('--kp', default='kp_ap_f107.csv',
                        help='Kp/F10.7 index CSV')
    parser.add_argument('--output', default='radar_timeseries.csv',
                        help='Output time series CSV')
    parser.add_argument('--target', default='Kp',
                        help='Target column for validation')
    
    args = parser.parse_args()
    
    # Run pipeline
    engine = Platypus()
    
    engine.load_ephemeris(args.ephemeris)
    engine.load_horizons_r(args.horizons)
    engine.compute_coherence()
    engine.save_timeseries(args.output)
    
    # Validate if Kp data available
    try:
        kp_df = pd.read_csv(args.kp, parse_dates=['datetime'])
        engine.validate_against_index(kp_df, args.target)
        engine.save_validation_artifacts()
        print(engine.summary())
    except FileNotFoundError:
        print(f"⚠ Kp file not found: {args.kp}")
        print("  Skipping validation. Run Gate 3 manually after generating kp_ap_f107.csv")


if __name__ == '__main__':
    main()

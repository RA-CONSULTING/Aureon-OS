# aura_validator.py
"""
✨🛡️ AURA VALIDATOR - Biofield Metrics & Trade Validation
==========================================================
Provides both:
1. Class-based API for import by QueenHiveMind
2. Stdin-based CLI for piped biofield data streams
"""
from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import sys, json, time, csv, math, os
from collections import deque

EPS = 1e-12

# ---- EWMA normalizer (robust to live drift) ----
class EWMA:
    def __init__(self, alpha=0.02):
        self.alpha = alpha
        self.m = None
        self.v = None

    def update(self, x: float):
        if x is None or not math.isfinite(float(x)):
            raise ValueError("LIVE_EWMA_OBSERVATION_REQUIRED")
        x = float(x)
        if self.m is None:
            self.m = x
            self.v = 1.0
        else:
            a = self.alpha
            diff = x - self.m
            self.m += a * diff
            self.v = (1 - a) * (self.v + a * diff * diff)
        # z-score like normalization
        return (x - self.m) / (math.sqrt(self.v) + EPS)

# ---- helpers ----
def fnum(x, d=6):
    """Format a numeric to ``d`` decimals.

    Raises ``ValueError`` on truly malformed input (strings that don't parse,
    dicts, etc.) — the caller is responsible for skipping the sample rather
    than persisting a fake 0.0 reading. ``None`` and explicit zeros are
    still allowed (treated as 0.0).
    """
    if x is None:
        raise ValueError("fnum: live numeric observation required")
    try:
        x = float(x)
    except (ValueError, TypeError) as exc:
        raise ValueError(
            f"fnum: cannot coerce {x!r} to float; aura input is malformed ({exc})"
        )
    if not math.isfinite(x):
        raise ValueError("fnum: finite live observation required")
    return float(f"{x:.{d}f}")


def clamp01(x):
    """Clamp ``x`` into [0, 1].

    Raises ``ValueError`` on malformed input so callers don't accidentally
    feed a silent 0.0 into the calm/concordance validation thresholds.
    """
    if x is None:
        raise ValueError("clamp01: live numeric observation required")
    try:
        v = float(x)
    except (ValueError, TypeError) as exc:
        raise ValueError(
            f"clamp01: cannot coerce {x!r} to float; aura input is malformed ({exc})"
        )
    return max(0.0, min(1.0, v))

def hue_from_bands(alpha, theta, beta):
    # Map band dominance to hue (deg): theta→220°, alpha→60°, beta→0°
    # Weighted barycentric blend
    alpha = max(0.0, alpha); theta = max(0.0, theta); beta = max(0.0, beta)
    s = alpha + theta + beta + EPS
    wa, wt, wb = alpha/s, theta/s, beta/s
    hue = (wb*0.0 + wa*60.0 + wt*220.0) % 360.0
    return hue

def ten_nine_one_concordance(unity, flow, anchor):
    # normalize the triple then project onto 10:9:1
    u, f, a = max(0.0, unity), max(0.0, flow), max(0.0, anchor)
    s = u + f + a + EPS
    u, f, a = u/s, f/s, a/s
    k = (10.0, 9.0, 1.0)
    kn = math.sqrt(k[0]**2 + k[1]**2 + k[2]**2)
    proj = (u*k[0] + f*k[1] + a*k[2]) / (kn + EPS)
    # scale to 0..1 over a practical range
    return clamp01(0.5 + 0.5 * proj)


# ════════════════════════════════════════════════════════════════════════════
# ✨🛡️ CLASS-BASED API FOR QUEEN HIVE MIND INTEGRATION
# ════════════════════════════════════════════════════════════════════════════
class AuraValidator:
    """
    Aura Validator - validates trade signals using biofield metrics.
    
    Validates only fresh, provider-attributed biofield observations.
    """
    
    def __init__(self, synthetic_mode: bool = False):
        if synthetic_mode:
            raise ValueError("SYNTHETIC_AURA_MODE_REMOVED")
        self.synthetic_mode = False
        self.z_hrv = EWMA(alpha=0.02)
        self.z_gsr = EWMA(alpha=0.05)
        self.last_calm_index = None
        self.last_aura_hue = None
        self.last_concordance = None
        self.validation_count = 0
        self.passed_count = 0
        
    def validate(self, signal: dict = None) -> dict:
        """
        Validate a trade signal against biofield metrics.
        
        Returns no_data until an attributed live observation is supplied.
        """
        self.validation_count += 1
        
        if not isinstance(signal, dict):
            return {'valid': False, 'truth_status': 'no_data', 'generated_values': False,
                    'blocker': 'LIVE_BIOFIELD_OBSERVATION_REQUIRED'}
        if signal.get('truth_status') != 'live' or signal.get('generated_values') is not False:
            return {'valid': False, 'truth_status': 'no_data', 'generated_values': False,
                    'blocker': 'LIVE_BIOFIELD_PROVENANCE_REQUIRED'}
        if not signal.get('source_id') or not signal.get('source_timestamp'):
            return {'valid': False, 'truth_status': 'no_data', 'generated_values': False,
                    'blocker': 'BIOFIELD_SOURCE_RECEIPT_REQUIRED'}
        bands = signal.get('bands') if isinstance(signal.get('bands'), dict) else signal
        try:
            alpha = fnum(bands.get('alpha'))
            theta = fnum(bands.get('theta'))
            beta = fnum(bands.get('beta'))
            hrv = fnum(signal.get('hrv_rmssd', signal.get('hrv')))
            gsr = fnum(signal.get('gsr_uS', signal.get('gsr')))
            resp_bpm = fnum(signal.get('resp_bpm', signal.get('respiration')))
        except ValueError as exc:
            return {'valid': False, 'truth_status': 'no_data', 'generated_values': False,
                    'blocker': str(exc)}
        
        # Calculate metrics
        atr = alpha / (theta + EPS)
        hrv_norm = clamp01(0.5 + 0.2 * self.z_hrv.update(hrv))
        gsr_norm = clamp01(0.5 + 0.2 * self.z_gsr.update(gsr))
        
        resp_term = 1.0 - clamp01(abs(resp_bpm - 6.0) / 12.0)
        beta_term = 1.0 / (1.0 + beta)
        atr_norm = math.atan(atr) * (2.0 / math.pi)
        
        calm_index = clamp01(0.35*atr_norm + 0.35*hrv_norm + 0.15*resp_term + 0.15*beta_term)
        concordance = ten_nine_one_concordance(unity=alpha, flow=hrv_norm, anchor=theta)
        hue = hue_from_bands(alpha, theta, beta)
        
        # Store for status queries
        self.last_calm_index = calm_index
        self.last_aura_hue = hue
        self.last_concordance = concordance
        
        # Validation passes if calm and concordant
        # In synthetic mode, this almost always passes
        passed = calm_index > 0.3 and concordance > 0.3
        if passed:
            self.passed_count += 1
        
        return {
            'valid': passed,
            'calm_index': calm_index,
            'concordance': concordance,
            'aura_hue': hue,
            'hrv_norm': hrv_norm,
            'gsr_norm': gsr_norm,
            'alpha_theta_ratio': atr,
            'mode': 'live',
            'truth_status': 'real_derived',
            'source_id': signal['source_id'],
            'source_timestamp': signal['source_timestamp'],
            'generated_values': False,
        }
    
    def get_status(self) -> dict:
        """Get current validator status."""
        return {
            'mode': 'live',
            'validation_count': self.validation_count,
            'passed_count': self.passed_count,
            'pass_rate': self.passed_count / max(1, self.validation_count),
            'last_calm_index': self.last_calm_index,
            'last_concordance': self.last_concordance,
            'last_aura_hue': self.last_aura_hue
        }
    
    def is_calm(self) -> bool:
        """Quick check if trader state is calm enough for trading."""
        return self.last_calm_index is not None and self.last_calm_index > 0.3


# Singleton instance for easy access
_aura_validator_instance = None

def get_aura_validator(synthetic_mode: bool = False) -> AuraValidator:
    """Get or create the singleton AuraValidator instance."""
    global _aura_validator_instance
    if _aura_validator_instance is None:
        _aura_validator_instance = AuraValidator(synthetic_mode=synthetic_mode)
    return _aura_validator_instance


# ════════════════════════════════════════════════════════════════════════════
# STDIN-BASED CLI MODE (for piped biofield streams)
# ════════════════════════════════════════════════════════════════════════════
def run_stdin_mode():
    """Run the validator in stdin mode for piped biofield data."""
    # ---- CSV setup ----
    os.makedirs("validation", exist_ok=True)
    csv_path = "validation/aura_features.csv"
    write_header = not os.path.exists(csv_path) or os.stat(csv_path).st_size == 0
    f = open(csv_path, "a", newline="")
    w = csv.writer(f)
    if write_header:
        w.writerow([
            "timestamp","epoch","label",
            "alpha_theta_ratio","hrv_norm","gsr_norm",
            "calm_index","prime_concordance_10_9_1","aura_hue_deg"
        ])
        f.flush()

    # ---- normalizers ----
    z_hrv = EWMA(alpha=0.02)  # slower, HRV drifts slowly
    z_gsr = EWMA(alpha=0.05)  # skin response can drift faster

    # ---- live ingest (stdin, JSON lines) ----
    print("Aura validator listening on stdin…", file=sys.stderr)
    epoch = 0
    label = "live"

    for line in sys.stdin:
        line = line.strip()
        if not line: continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue

        if "epoch" in msg: 
            try: epoch = int(msg["epoch"])
            except: pass
        if "label" in msg:
            try: label = str(msg["label"])
            except: pass

        t = msg.get("t", time.time())
        bands = msg.get("bands", {}) or {}
        alpha = float(bands.get("alpha", 0.0) or 0.0)
        theta = float(bands.get("theta", 0.0) or 0.0)
        beta  = float(bands.get("beta",  0.0) or 0.0)

        # alpha/theta ratio
        atr = alpha / (theta + EPS)

        # HRV normalization (z-like)
        hrv = float(msg.get("hrv_rmssd", 0.0) or 0.0)
        hrv_norm = clamp01(0.5 + 0.2 * z_hrv.update(hrv))

        # GSR normalization (z-like)
        gsr = float(msg.get("gsr_uS", 0.0) or 0.0)
        gsr_norm = clamp01(0.5 + 0.2 * z_gsr.update(gsr))

        # Calm Index: blend of high alpha/theta and high HRV, moderated by low beta and gentle respiration
        resp_bpm = float(msg.get("resp_bpm", 0.0) or 0.0)
        resp_term = 1.0 - clamp01(abs(resp_bpm - 6.0) / 12.0)  # peak near ~6 bpm
        beta_term = 1.0 / (1.0 + beta)                          # lower beta → calmer
        # normalize ATR softly
        atr_norm = math.atan(atr) * (2.0 / math.pi)             # 0..1-ish
        calm_index = clamp01(0.35*atr_norm + 0.35*hrv_norm + 0.15*resp_term + 0.15*beta_term)

        # 10-9-1 concordance from (Unity, Flow, Anchor) proxies:
        # Unity ~ alpha dominance, Flow ~ HRV quality, Anchor ~ theta stability
        c1091 = ten_nine_one_concordance(unity=alpha, flow=hrv_norm, anchor=theta)

        # Aura hue from band dominance
        hue = hue_from_bands(alpha, theta, beta)

        try:
            w.writerow([
                fnum(t, 3), epoch, label,
                fnum(atr), fnum(hrv_norm), fnum(gsr_norm),
                fnum(calm_index), fnum(c1091), fnum(hue)
            ])
            f.flush()
        except ValueError as exc:
            # fnum/clamp01 surfaced malformed input; skip this sample rather
            # than write a fabricated 0.0 row to the audit log.
            print(f"[aura-validator] skipped malformed sample at t={t}: {exc}",
                  file=sys.stderr)

    print("Aura validator finished.", file=sys.stderr)
    f.close()


if __name__ == "__main__":
    run_stdin_mode()

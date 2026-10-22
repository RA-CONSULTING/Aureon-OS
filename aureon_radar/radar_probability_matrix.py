"""
🎯 AUREON RADAR — Probability Intelligence Adapter
====================================================
Wires Probability Intelligence Matrix into the Honey Ladder radar.

Every signal gets probability-validated BEFORE spending a demo trade.
Multi-factor analysis: momentum, volatility, proximity, sample quality.

STOPS bad trades before they cost money.
"""
import json
import math
import os
import time
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field

# ═══════════════════════════════════════════════════════════════
# FACTORS
# ═══════════════════════════════════════════════════════════════

@dataclass
class IntelligenceFactor:
    name: str
    weight: float  # 0-1
    value: float   # 0-1, where 1 is good
    reason: str

    @property
    def contribution(self) -> float:
        return self.weight * self.value


@dataclass
class ProbabilityIntelligence:
    raw_probability: float = 0.0
    adjusted_probability: float = 0.0
    confidence: float = 0.0
    factors: List[IntelligenceFactor] = field(default_factory=list)
    risk_flags: List[str] = field(default_factory=list)
    action: str = "PROCEED"  # PROCEED (no flags), WATCH, CAUTION, DANGER

    def add_factor(self, name: str, weight: float, value: float, reason: str):
        self.factors.append(IntelligenceFactor(name, weight, value, reason))

    def add_risk(self, flag: str):
        if flag not in self.risk_flags:
            self.risk_flags.append(flag)

    def calculate_adjusted(self):
        if not self.factors:
            self.adjusted_probability = self.raw_probability
            return
        total_weight = sum(f.weight for f in self.factors)
        if total_weight == 0:
            self.adjusted_probability = self.raw_probability
            return
        adjustment = sum((f.weight / total_weight) * f.value for f in self.factors)
        if adjustment >= 0.5:
            boost = (adjustment - 0.5) * 2
            self.adjusted_probability = self.raw_probability + (1 - self.raw_probability) * boost * 0.3
        else:
            penalty = (0.5 - adjustment) * 2
            self.adjusted_probability = self.raw_probability * (1 - penalty * 0.7)
        self.adjusted_probability = max(0, min(1, self.adjusted_probability))
        # Risk flags
        if len(self.risk_flags) >= 3:
            self.action = "DANGER"
        elif len(self.risk_flags) >= 2:
            self.action = "CAUTION"
        elif len(self.risk_flags) >= 1:
            self.action = "WATCH"
        else:
            # "PROCEED", not "HOLD": in trading semantics HOLD means "do not
            # trade" — the old name was an inversion trap for any consumer
            # that gates on the action string.
            self.action = "PROCEED"


# ═══════════════════════════════════════════════════════════════
# PROBABILITY MATRIX
# ═══════════════════════════════════════════════════════════════

class RadarProbabilityMatrix:
    """
    Probability Intelligence Matrix adapted for the Radar's signal pipeline.

    Analyzes each signal before it hits the honey ladder:
    - Signal confidence → raw probability
    - Price momentum → momentum factor
    - Price volatility → volatility factor
    - Shadow hit history → pattern factor
    - Time of day/phase → temporal factor

    Outputs: adjusted probability, risk flags, action recommendation.
    """

    # Contract path for the swarm: aureon_radar/state/probability_matrix_state.json
    # Shape: {ts, sources: {name: {hits, misses, accuracy, samples}},
    #         admissions: {approved, blocked, last_signals: [...]}, notes}
    DEFAULT_STATE_FILE = Path(__file__).parent / "state" / "probability_matrix_state.json"

    def __init__(self, state_file: Optional[str] = None):
        self.state_file = Path(state_file) if state_file else self.DEFAULT_STATE_FILE
        # 'world' counsel added at 0.10; the other weights are renormalized
        # (x0.9) so the total stays 1.00.
        self.factor_weights = {
            'signal_confidence': 0.27,
            'momentum': 0.18,
            'volatility': 0.135,
            'shadow_history': 0.135,
            'temporal_phase': 0.09,
            'source_reliability': 0.09,
            'world': 0.10,
        }
        self.source_accuracy: Dict[str, Dict] = {}  # source -> {hits, misses}
        self.admissions = {'approved': 0, 'blocked': 0, 'last_signals': []}
        self.notes: List[str] = []
        self._load_state()

    def _journal(self, event: str, detail: str):
        """Append a fail-closed journal line (corrupt-state resets, bad data)."""
        try:
            journal = Path(self.state_file).with_suffix('.journal.jsonl')
            with open(journal, 'a', encoding='utf-8') as f:
                f.write(json.dumps({
                    'ts': time.time(),
                    'event': event,
                    'detail': detail,
                }) + '\n')
        except Exception:
            pass

    @staticmethod
    def _valid_accuracy_entry(stats: Any) -> bool:
        return (
            isinstance(stats, dict)
            and isinstance(stats.get('hits'), (int, float))
            and isinstance(stats.get('misses'), (int, float))
            and not isinstance(stats.get('hits'), bool)
            and not isinstance(stats.get('misses'), bool)
            and stats['hits'] >= 0 and stats['misses'] >= 0
            and math.isfinite(stats['hits']) and math.isfinite(stats['misses'])
        )

    def _load_state(self):
        """Fail-closed: corrupt or invalid state is RESET to defaults and
        journaled — never silently half-loaded, never fabricated.
        Accepts the contract shape ('sources') and the legacy shape
        ('source_accuracy') so an older file is not silently discarded."""
        path = Path(self.state_file)
        if not path.exists():
            return
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            self.source_accuracy = {}
            self._journal('state_reset_corrupt', f'json load failed: {e}')
            return
        if not isinstance(data, dict):
            self.source_accuracy = {}
            self._journal('state_reset_corrupt', 'top-level is not a dict')
            return

        saved_acc = data.get('sources', data.get('source_accuracy', {}))
        if isinstance(saved_acc, dict):
            dropped = []
            for source, stats in saved_acc.items():
                if isinstance(source, str) and self._valid_accuracy_entry(stats):
                    self.source_accuracy[source] = {
                        'hits': int(stats['hits']), 'misses': int(stats['misses'])}
                else:
                    dropped.append(str(source))
            if dropped:
                self._journal('state_entry_dropped',
                              f'invalid sources entries: {dropped}')

        saved_adm = data.get('admissions', {})
        if isinstance(saved_adm, dict):
            for key in ('approved', 'blocked'):
                v = saved_adm.get(key)
                if isinstance(v, (int, float)) and not isinstance(v, bool) \
                        and math.isfinite(v) and v >= 0:
                    self.admissions[key] = int(v)
                elif v is not None:
                    self._journal('state_entry_dropped',
                                  f'invalid admissions.{key} ignored')
            ls = saved_adm.get('last_signals', [])
            if isinstance(ls, list):
                for sig in ls[-20:]:
                    if isinstance(sig, dict) and isinstance(sig.get('ts'), (int, float)) \
                            and isinstance(sig.get('symbol'), str) \
                            and isinstance(sig.get('adjusted_prob'), (int, float)) \
                            and sig.get('verdict') in ('approved', 'blocked'):
                        self.admissions['last_signals'].append({
                            'ts': float(sig['ts']),
                            'symbol': sig['symbol'],
                            'adjusted_prob': float(sig['adjusted_prob']),
                            'verdict': sig['verdict'],
                        })

        notes = data.get('notes', [])
        if isinstance(notes, list):
            self.notes = [str(n) for n in notes if isinstance(n, (str, int, float))][-50:]

        saved_w = data.get('factor_weights', {})
        if isinstance(saved_w, dict):
            bad = []
            for k, v in saved_w.items():
                if k in self.factor_weights:
                    if isinstance(v, (int, float)) and not isinstance(v, bool) \
                            and math.isfinite(v) and 0.0 <= v <= 1.0:
                        self.factor_weights[k] = float(v)
                    else:
                        bad.append(k)
            if bad:
                self._journal('state_entry_dropped',
                              f'invalid factor_weights kept at default: {bad}')

    def _save_state(self):
        """Atomic: write tmp + os.replace so a crash mid-write can never
        leave a truncated state file behind. Written in the contract shape."""
        try:
            sources = {}
            for name, stats in self.source_accuracy.items():
                if not self._valid_accuracy_entry(stats):
                    continue
                hits, misses = int(stats['hits']), int(stats['misses'])
                samples = hits + misses
                sources[name] = {
                    'hits': hits,
                    'misses': misses,
                    'accuracy': (hits / samples) if samples > 0 else None,
                    'samples': samples,
                }
            data = {
                'ts': time.time(),
                'sources': sources,
                'factor_weights': self.factor_weights,
                'admissions': self.admissions,
                'notes': self.notes[-50:],
            }
            path = Path(self.state_file)
            tmp = path.with_suffix('.tmp')
            with open(tmp, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            os.replace(tmp, path)
        except Exception as e:
            self._journal('save_failed', str(e))

    def evaluate_signal(
        self,
        symbol: str,
        direction: str,
        confidence: float,
        source: str,
        price_history: Optional[List[float]] = None,
        sector: str = "commodity",
    ) -> ProbabilityIntelligence:
        """
        Evaluate a trading signal through the probability matrix.

        Returns enriched probability intelligence.
        """
        intel = ProbabilityIntelligence()
        intel._symbol = symbol  # stamped for admissions bookkeeping
        # Sanitize confidence: non-finite or out-of-range input must never
        # reach the factor math (NaN poisons the weighted adjustment below —
        # max/min comparisons don't catch it — and can surface downstream as
        # a bogus approval). Fail-closed: unparseable/NaN → 0.0.
        try:
            conf = float(confidence)
        except (TypeError, ValueError):
            conf = 0.0
        if not math.isfinite(conf):
            conf = 0.0
        intel.raw_probability = max(0.0, min(1.0, conf))

        # ==== 1. SIGNAL CONFIDENCE FACTOR ====
        intel.add_factor(
            name="signal_confidence",
            weight=self.factor_weights['signal_confidence'],
            value=intel.raw_probability,
            reason=f"Signal confidence {intel.raw_probability:.0%}"
        )
        if intel.raw_probability < 0.5:
            intel.add_risk("LOW_CONFIDENCE")

        # ==== 2. MOMENTUM FACTOR ====
        momentum_value = 0.5
        last_price = price_history[-1] if price_history else 0.0
        if price_history and len(price_history) >= 3 and isinstance(last_price, (int, float)) \
                and math.isfinite(last_price) and last_price > 0:
            # Calculate recent momentum
            recent = price_history[-3:]
            deltas = [recent[i+1] - recent[i] for i in range(len(recent)-1)]
            if len(deltas) >= 2:
                avg_delta = sum(deltas) / len(deltas)
                if direction.upper() in ["LONG", "BUY"]:
                    momentum_value = 0.5 + min(0.5, max(-0.5, avg_delta / last_price * 100))
                else:
                    momentum_value = 0.5 + min(0.5, max(-0.5, -avg_delta / last_price * 100))

        intel.add_factor(
            name="momentum",
            weight=self.factor_weights['momentum'],
            value=momentum_value,
            reason=f"Momentum score {momentum_value:.2f}"
        )
        if momentum_value < 0.3:
            intel.add_risk("NEGATIVE_MOMENTUM")

        # ==== 3. VOLATILITY FACTOR ====
        # Prefer live real-volatility scanner state; fall back to local CV.
        vol_value, vol_reason, cv = self._get_real_volatility_factor(symbol, price_history)
        if cv is not None and cv > 0.05:
            intel.add_risk("HIGH_VOLATILITY")

        intel.add_factor(
            name="volatility",
            weight=self.factor_weights['volatility'],
            value=vol_value,
            reason=vol_reason,
        )

        # ==== 4. SHADOW HISTORY FACTOR ====
        source_acc = self._get_source_accuracy(source)
        intel.add_factor(
            name="shadow_history",
            weight=self.factor_weights['shadow_history'],
            value=source_acc,
            reason=f"Source '{source}' accuracy {source_acc:.0%}"
        )
        if source_acc < 0.3:
            intel.add_risk("UNRELIABLE_SOURCE")

        # ==== 5. TEMPORAL PHASE FACTOR ====
        temporal_value = self._evaluate_temporal_phase()
        intel.add_factor(
            name="temporal_phase",
            weight=self.factor_weights['temporal_phase'],
            value=temporal_value,
            reason=f"Temporal phase score {temporal_value:.2f}"
        )

        # ==== 6. SOURCE RELIABILITY FACTOR ====
        source_reliability = self._get_source_reliability(source)
        intel.add_factor(
            name="source_reliability",
            weight=self.factor_weights['source_reliability'],
            value=source_reliability,
            reason=f"Source reliability {source_reliability:.0%}"
        )

        # ==== 7. WORLD COUNSEL FACTOR ====
        world_value, world_source, world_reason = self._get_world_counsel()
        intel.add_factor(
            name="world",
            weight=self.factor_weights['world'],
            value=world_value,
            reason=f"World counsel ({world_source}): {world_reason}"
        )

        # ==== CALCULATE ====
        intel.calculate_adjusted()
        # Apply risk penalties
        risk_penalty = len(intel.risk_flags) * 0.1
        intel.adjusted_probability *= (1 - risk_penalty)
        intel.adjusted_probability = max(0, min(1, intel.adjusted_probability))
        intel.confidence = intel.adjusted_probability

        return intel

    def _get_source_accuracy(self, source: str) -> float:
        """Smoothed source accuracy in (0, 1) — Laplace (hits+1)/(total+2).

        Smoothing keeps a single early hit from reading as a calibrated 100%
        and a single early miss from reading as 0%; the prior centre is the
        same 0.5 the unsmoothed path used for unknown sources.
        """
        stats = self.source_accuracy.get(source)
        if self._valid_accuracy_entry(stats):
            hits = stats['hits']
            total = hits + stats['misses']
            if total > 0:
                return (hits + 1.0) / (total + 2.0)
        return 0.5  # Unknown source

    def _get_source_reliability(self, source: str) -> float:
        """Hardcoded reliability tiers based on observed performance."""
        tiers = {
            'aureon_os_bridge': 0.85,
            'aureon_wolf': 0.75,
            'aureon_lion': 0.75,
            'scanner': 0.60,
            'crypto_correlation': 0.55,
            'stock_momentum': 0.55,
            'planetary': 0.50,
            'ollama': 0.45,
        }
        return tiers.get(source, 0.50)

    def _get_real_volatility_factor(
        self,
        symbol: str,
        price_history: Optional[List[float]],
    ) -> Tuple[float, str, Optional[float]]:
        """Read live real-volatility scanner state; fall back to local CV.

        Returns (factor_value, reason, coefficient_of_variation).
        Factor value: higher for stable/healthy volatility windows, lower for
        excessive volatility (penalized as a risk).
        """
        # Try live scanner state first
        scan_path = Path(__file__).parent / "state" / "volatility_scan.json"
        try:
            data = json.loads(scan_path.read_text(encoding="utf-8"))
            for entry in data.get("symbols", []):
                if entry.get("symbol") == symbol:
                    score = float(entry.get("volatility_score", 0.0))
                    blockers = entry.get("blockers", [])
                    if blockers:
                        return 0.3, f"real-vol scanner: {', '.join(blockers)}", None
                    # Map score 0..1 to factor 0.2..0.9; very high vol slightly
                    # penalized to avoid chop.
                    factor = 0.2 + 0.7 * (1.0 - min(score, 1.0))
                    return factor, f"real-vol scanner score={score:.2f}", score
        except Exception:
            pass

        # Fallback: coefficient of variation from local price history
        cv: Optional[float] = None
        if price_history and len(price_history) >= 5:
            mean = sum(price_history) / len(price_history)
            variance = sum((p - mean) ** 2 for p in price_history) / len(price_history)
            std = variance ** 0.5
            cv = std / mean if mean > 0 else 0.0
            if cv > 0.05:
                return 0.2, f"fallback CV={cv:.4f} (high)", cv
            elif cv > 0.03:
                return 0.4, f"fallback CV={cv:.4f} (elevated)", cv
            elif cv > 0.01:
                return 0.6, f"fallback CV={cv:.4f} (moderate)", cv
            else:
                return 0.8, f"fallback CV={cv:.4f} (low)", cv
        return 0.5, "unknown volatility (few samples)", cv

    # World counsel sources, most authoritative first. All paths are
    # file-relative (not cwd-relative) so the matrix behaves identically no
    # matter which process imports it.
    _WORLD_CANDIDATES = (
        'queen_snap',          # aureon_fusion/state/queen_mind/world_snap.json
        'queen_report',        # last world_snap from queen_mind reports.jsonl
        'radar_state',         # aureon_radar/state/world_state.json (define-and-consume)
        'volatility_scan',     # aureon_radar/state/volatility_scan.json
    )

    def _read_world_data(self) -> Tuple[Optional[Dict[str, Any]], str]:
        """Fetch the newest world snapshot. Fail-closed: returns (None, reason)
        when nothing readable exists — callers must go neutral, never invent."""
        workspace = Path(__file__).resolve().parent.parent

        snap = workspace / 'aureon_fusion' / 'state' / 'queen_mind' / 'world_snap.json'
        if snap.exists():
            try:
                data = json.loads(snap.read_text(encoding='utf-8'))
                if isinstance(data, dict) and data:
                    return data, 'queen_snap'
            except Exception as e:
                self._journal('world_source_unreadable', f'{snap}: {e}')

        reports = workspace / 'aureon_fusion' / 'state' / 'queen_mind' / 'reports.jsonl'
        if reports.exists():
            try:
                last = None
                with open(reports, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.strip():
                            last = line
                if last:
                    data = json.loads(last).get('world_snap')
                    if isinstance(data, dict) and data:
                        return data, 'queen_report'
            except Exception as e:
                self._journal('world_source_unreadable', f'{reports}: {e}')

        state = Path(__file__).resolve().parent / 'state' / 'world_state.json'
        if state.exists():
            try:
                data = json.loads(state.read_text(encoding='utf-8'))
                if isinstance(data, dict) and data:
                    return data, 'radar_state'
            except Exception as e:
                self._journal('world_source_unreadable', f'{state}: {e}')

        vscan = Path(__file__).resolve().parent / 'state' / 'volatility_scan.json'
        if vscan.exists():
            try:
                data = json.loads(vscan.read_text(encoding='utf-8'))
                if isinstance(data, dict) and data:
                    return data, 'volatility_scan'
            except Exception as e:
                self._journal('world_source_unreadable', f'{vscan}: {e}')

        return None, 'neutral_no_world_data'

    @staticmethod
    def _finite_number(v: Any) -> Optional[float]:
        if isinstance(v, bool):
            return None
        if isinstance(v, (int, float)) and math.isfinite(v):
            return float(v)
        return None

    def _get_world_counsel(self) -> Tuple[float, str, str]:
        """World counsel factor, honest routing through the 'planetary' 0.50
        reliability tier: the tier value is the prior, real world readings
        move it, and with no usable readings the factor is exactly the
        neutral prior (0.5, source='neutral_no_world_data'). Never fabricated.
        """
        data, origin = self._read_world_data()
        if data is None:
            return 0.5, 'neutral_no_world_data', 'no world data reachable'

        sub: List[Tuple[str, float]] = []

        cosmic = self._finite_number(data.get('cosmic_score'))
        if cosmic is not None and 0.0 <= cosmic <= 1.0:
            sub.append(('cosmic', cosmic))

        schumann = self._finite_number(data.get('schumann_hz'))
        if schumann is not None and schumann > 0.0:
            sub.append(('schumann', 1.0 - min(1.0, abs(schumann - 7.83) / 1.5)))

        kp = self._finite_number(data.get('kp_index'))
        if kp is not None and kp >= 0.0:
            sub.append(('kp', 0.85 if kp <= 2 else 0.65 if kp <= 4
                        else 0.45 if kp <= 6 else 0.30))

        fg = self._finite_number(data.get('fear_greed'))
        if fg is not None and 0.0 <= fg <= 100.0:
            sub.append(('fear_greed', fg / 100.0))

        regime = str(data.get('risk_on_off') or '').strip().lower()
        if regime == 'risk_on':
            sub.append(('risk_on_off', 0.8))
        elif regime == 'risk_off':
            sub.append(('risk_on_off', 0.3))
        elif regime == 'neutral':
            sub.append(('risk_on_off', 0.5))

        # Volatility scanner ranking: the top target's volatility score +
        # confidence folded into a 0..1 world-counsel sub-reading. Stale or
        # empty scan contributes nothing (fail-closed).
        if origin == 'volatility_scan':
            top = data.get('top_target') if isinstance(data.get('top_target'), dict) else None
            if top is None and isinstance(data.get('ranking'), list) and data['ranking']:
                top = data['ranking'][0]
            if isinstance(top, dict):
                vol_score = self._finite_number(top.get('volatility_score'))
                conf = self._finite_number(top.get('confidence'))
                if vol_score is not None and conf is not None:
                    rank_score = min(1.0, max(0.0, vol_score * conf))
                    sub.append(('volatility_rank_score', rank_score))

        if not sub:
            return 0.5, 'neutral_no_world_data', \
                f'{origin} world data present but no usable fields'

        avg = sum(v for _, v in sub) / len(sub)
        # Shrink the reading toward the 'planetary' 0.50 tier prior: with n
        # real sub-readings the posterior is (0.5*2 + avg*n) / (n+2). No
        # readings → exactly the prior (handled above).
        value = (0.5 * 2.0 + avg * len(sub)) / (len(sub) + 2.0)
        value = max(0.0, min(1.0, value))
        parts = '+'.join(f'{k}={v:.2f}' for k, v in sub)
        return value, origin, f'{parts} (n={len(sub)}) → {value:.2f} vs 0.50 prior'

    def _evaluate_temporal_phase(self) -> float:
        """Evaluate current temporal phase for trading quality.

        UTC throughout — the windows below are documented in UTC (London
        8-11, NY 13-16); using local server time shifts every window by the
        host's UTC offset.
        """
        import datetime
        now = datetime.datetime.now(datetime.timezone.utc)
        hour = now.hour
        weekday = now.weekday()

        # Avoid weekends for most instruments
        if weekday >= 5:
            return 0.3

        # Best trading hours: London open (8-11 UTC), NY open (13-16 UTC)
        if 8 <= hour <= 11 or 13 <= hour <= 16:
            return 0.9
        elif 6 <= hour <= 18:
            return 0.7
        elif 19 <= hour <= 22:
            return 0.5
        else:
            return 0.3  # Night/low liquidity

    def record_outcome(self, source: str, success: bool):
        """Record shadow/demo outcome to learn source accuracy.

        Only real outcomes belong here (caller verifies the terminal state);
        the bool coercion merely guards the counter arithmetic.
        """
        if not isinstance(source, str) or not source:
            return
        if source not in self.source_accuracy or \
                not self._valid_accuracy_entry(self.source_accuracy[source]):
            self.source_accuracy[source] = {'hits': 0, 'misses': 0}
        if bool(success):
            self.source_accuracy[source]['hits'] += 1
        else:
            self.source_accuracy[source]['misses'] += 1
        self._save_state()

    def should_trade(self, intel: ProbabilityIntelligence, min_threshold: float = 0.55) -> bool:
        """Gate: should this signal proceed to demo/live execution?
        Every verdict is recorded to admissions (persisted with the state)."""
        # Owner decree 2026-09-07: Sero has full autonomy; the matrix advises
        # but no longer vetoes CAUTION signals. Only explicit DANGER is refused,
        # and the threshold is lowered so high-confidence WATCH/CAUTION signals
        # can execute with the account's tight sizing/risk limits.
        if intel.action == "DANGER":
            allowed = False
        else:
            allowed = intel.adjusted_probability >= min_threshold
        self._record_admission(intel, allowed)
        return allowed

    def _record_admission(self, intel: ProbabilityIntelligence, allowed: bool):
        try:
            key = 'approved' if allowed else 'blocked'
            self.admissions[key] = self.admissions.get(key, 0) + 1
            self.admissions.setdefault('last_signals', []).append({
                'ts': time.time(),
                'symbol': getattr(intel, '_symbol', '') or '',
                'adjusted_prob': round(float(intel.adjusted_probability), 4),
                'verdict': key,
            })
            self.admissions['last_signals'] = self.admissions['last_signals'][-20:]
            self._save_state()
        except Exception as e:
            self._journal('admission_record_failed', str(e))

    def explain(self, intel: ProbabilityIntelligence, symbol: str = "",
                min_threshold: float = 0.55) -> str:
        lines = [
            f"╔══════════════════════════════════════════════════════════════╗",
            f"║  🧠 PROBABILITY MATRIX — {symbol:12s}                 ║",
            f"╠══════════════════════════════════════════════════════════════╣",
            f"║  Raw:      {intel.raw_probability:.1%}",
            f"║  Adjusted: {intel.adjusted_probability:.1%}  {'✅ PASS' if intel.adjusted_probability >= min_threshold else '❌ BLOCK'}",
            f"║  Action:   {intel.action}",
            f"║  ────────────────────────────────────────────────────────",
        ]
        for f in intel.factors:
            bar = "█" * int(f.value * 10) + "░" * (10 - int(f.value * 10))
            lines.append(f"║  {f.name:18s} [{bar}] {f.value:.0%}")
        if intel.risk_flags:
            lines.append(f"║  ⚠️  RISK: {', '.join(intel.risk_flags)}")
        lines.append(f"╚══════════════════════════════════════════════════════════════╝")
        return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════
# SINGLETON
# ═══════════════════════════════════════════════════════════════

_MATRIX: Optional[RadarProbabilityMatrix] = None

def get_matrix() -> RadarProbabilityMatrix:
    global _MATRIX
    if _MATRIX is None:
        _MATRIX = RadarProbabilityMatrix()
    return _MATRIX


def evaluate_signal(symbol, direction, confidence, source, price_history=None, sector="commodity"):
    return get_matrix().evaluate_signal(symbol, direction, confidence, source, price_history, sector)


def should_trade(intel, min_threshold=0.55):
    return get_matrix().should_trade(intel, min_threshold)


if __name__ == "__main__":
    # SELF-TEST — synthetic fixtures, clearly labeled; no live data touched.
    # Verifies: short-history volatility path (regression: NameError on cv),
    # NaN confidence fail-closed, outcome learning + smoothing, state
    # round-trip through a temp file, action ladder naming.
    import tempfile

    failures = []

    def check(name, cond):
        print(f"{'PASS' if cond else 'FAIL'}  {name}")
        if not cond:
            failures.append(name)

    tmp = Path(tempfile.mkdtemp()) / "pm_state.json"
    m = RadarProbabilityMatrix(state_file=str(tmp))

    # 1. Volatility reason with 1-4 price samples must not raise (cv fix)
    intel = m.evaluate_signal("X", "LONG", 0.7, "scanner", price_history=[100.0])
    check("short history: no NameError, vol reason set",
          any(f.name == "volatility" and "CV" not in f.reason for f in intel.factors))

    # 2. NaN confidence → fail-closed 0.0, LOW_CONFIDENCE risk, blocked
    nan_intel = m.evaluate_signal("X", "LONG", float("nan"), "scanner",
                                  price_history=[100.0, 100.1, 100.2, 100.3, 100.4])
    check("NaN confidence sanitized to 0.0", nan_intel.raw_probability == 0.0)
    check("NaN confidence flagged + blocked",
          "LOW_CONFIDENCE" in nan_intel.risk_flags and not m.should_trade(nan_intel))

    # 3. Outcome learning: 3 hits, 1 miss → smoothed 4/6 = 0.667 (not 1.0)
    for _ in range(3):
        m.record_outcome("src_a", True)
    m.record_outcome("src_a", False)
    acc = m._get_source_accuracy("src_a")
    check("smoothed accuracy 3h1m ≈ 0.667", abs(acc - 4.0 / 6.0) < 1e-9)
    check("unknown source = 0.5 prior", m._get_source_accuracy("nope") == 0.5)

    # 4. State round-trip: reload from disk preserves learned counts
    m2 = RadarProbabilityMatrix(state_file=str(tmp))
    check("state reload preserves counts",
          m2.source_accuracy.get("src_a", {}).get("hits") == 3
          and m2.source_accuracy.get("src_a", {}).get("misses") == 1)

    # 5. Corrupt state: reset to empty, journaled (never fabricated)
    tmp.write_text("{not json", encoding="utf-8")
    m3 = RadarProbabilityMatrix(state_file=str(tmp))
    check("corrupt state reset to empty", m3.source_accuracy == {})
    check("corruption journaled", tmp.with_suffix(".journal.jsonl").exists())

    # 5. Corrupt state: reset to empty, journaled (never fabricated)
    tmp.write_text("{not json", encoding="utf-8")
    m3 = RadarProbabilityMatrix(state_file=str(tmp))
    check("corrupt state reset to empty", m3.source_accuracy == {})
    check("corruption journaled", tmp.with_suffix(".journal.jsonl").exists())

    # 6. Contract shape: saved file has sources, admissions, notes keys
    m4 = RadarProbabilityMatrix(state_file=str(tmp))
    m4.record_outcome("src_b", True)
    gate = m4.evaluate_signal("Y", "SHORT", 0.8, "src_b",
                              price_history=[100, 99.5, 99, 98.5, 98])
    m4.should_trade(gate, min_threshold=0.55)
    saved = json.loads(tmp.read_text(encoding="utf-8"))
    check("contract shape: ts", isinstance(saved.get("ts"), (int, float)))
    check("contract shape: sources[src_b] has accuracy/samples",
          isinstance(saved.get("sources", {}).get("src_b"), dict)
          and "accuracy" in saved["sources"]["src_b"]
          and "samples" in saved["sources"]["src_b"])
    check("contract shape: admissions[approved] > 0",
          saved.get("admissions", {}).get("approved", 0) >= 1)
    check("contract shape: last_signals has entry",
          len(saved.get("admissions", {}).get("last_signals", [])) >= 1)
    check("contract shape: notes is list",
          isinstance(saved.get("notes"), list))

    # 7. World factor present and neutral fallback when reader returns nothing
    m5 = RadarProbabilityMatrix(state_file=str(tmp))
    m5._read_world_data = lambda: (None, 'neutral_no_world_data')  # type: ignore
    neutral_intel = m5.evaluate_signal("Z", "LONG", 0.7, "scanner",
                                       price_history=[100, 100.5, 101, 101.5, 102])
    w_factor = next(f for f in neutral_intel.factors if f.name == "world")
    check("world factor present", "world" in [f.name for f in neutral_intel.factors])
    check("world factor weight 0.10", m5.factor_weights["world"] == 0.10)
    check("no world data → neutral 0.5",
          w_factor.value == 0.5 and "neutral_no_world_data" in w_factor.reason)

    # 8. Live world counsel from queen report stays in [0,1] and names its source
    live_val, live_src, live_reason = m4._get_world_counsel()
    check("live world counsel in [0,1]", 0.0 <= live_val <= 1.0)
    check("live world counsel source is honest", live_src in {
        "queen_snap", "queen_report", "radar_state", "neutral_no_world_data"})

    # 9. World counsel from a define-and-consume radar world_state file works
    import tempfile as _tf
    ws_tmp = Path(_tf.mkdtemp()) / "world_state.json"
    ws_tmp.write_text(json.dumps({"cosmic_score": 0.8, "kp_index": 1.0}),
                      encoding="utf-8")
    m6 = RadarProbabilityMatrix(state_file=str(tmp))
    m6._read_world_data = lambda: (json.loads(ws_tmp.read_text(encoding="utf-8")), 'radar_state')  # type: ignore
    v6, s6, r6 = m6._get_world_counsel()
    check("radar world_state counsel > 0.5", v6 > 0.5 and s6 == 'radar_state')

    # 10. Action ladder naming: no flags → PROCEED, never "HOLD"
    good = m.evaluate_signal("X", "LONG", 0.9, "src_a",
                             price_history=[100, 100.05, 100.10, 100.15, 100.20])
    check("clean signal → PROCEED", good.action == "PROCEED")

    # 11. Adjusted probability stays a calibrated 0..1 quantity
    check("adjusted in [0,1]",
          all(0.0 <= i.adjusted_probability <= 1.0
              for i in (intel, nan_intel, good)))

    print(f"\n{'ALL PASS' if not failures else f'{len(failures)} FAILURES: {failures}'}")
    raise SystemExit(1 if failures else 0)

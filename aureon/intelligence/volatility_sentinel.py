"""Volatility Sentinel — proactive prediction of high-volatility regimes.

The mission (Fourier→HNC integration, P2): predict the algorithmic patterns
that incur high volatility BEFORE the volatility is realized, from real
measured inputs only, and hand the prediction to the organism through the
established channels — a bus topic + trace here, the Λ(t) daemon source and
the b46 tighten-only gates in the later phases.

Four factors, each independently honest (``None`` on no_data, never a
placeholder — the Λ engine's Γ uses reading VALUES regardless of confidence,
so a "neutral 0.5" default would move the field, which is fabrication by
another name):

- ``ewma_vol``      (w=0.35) — the repo's first realized-volatility estimator:
  RiskMetrics EWMA of log returns at two horizons; risk is the fast/slow
  expansion ratio, self-normalizing per symbol (no invented calibration
  constants).
- ``phase_transition`` (w=0.25) — ``PhaseTransitionDetector.predict()``
  probability (repaired in P1; Takens-embedding curvature/coherence).
- ``qgita_regime``  (w=0.20) — QGITA global coherence R and its own risk
  taxonomy (R<0.3 == "chaotic — high volatility expected").
- ``spectral_surge`` (w=0.20) — the HNC surge detector's FFT resonance
  intensity (its docstring: "surge events of increased volatility"). A full
  buffer with no surge is a measured 0.0, not a default.

Fusion is a weighted mean over the AVAILABLE factors (weights renormalized),
escalated by ``max()`` with any single factor ≥ ESCALATION_RISK — max() is
tighten-only. ``confidence`` is the sum of available factor weights, so a
veto downstream can insist on real coverage. Zero factors → an assessment
whose status is ``no_data`` with one named blocker per missing factor.

Publishing mirrors the hnc_field freshness contract: every row is ts-stamped;
``read_latest_assessment`` refuses stale or unstamped rows and returns
``None`` — never a default.
"""

from __future__ import annotations

import logging
import math
import os
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Tuple

logger = logging.getLogger(__name__)

VOL_TOPIC = "intelligence.volatility.sentinel"
VOL_TRACE_NAME = "volatility_sentinel"

#: SignalGate veto threshold (P4). Reachable only by multi-factor agreement
#: or a single ≥ESCALATION_RISK factor; sits above QGITA's own HIGH mapping
#: (0.7) so one model at moderate alarm cannot veto alone.
VOL_RISK_BLOCK = 0.85
ESCALATION_RISK = 0.90

#: Minimum factor-weight coverage an assessment needs before a consumer may
#: act on it. The Kelly buffer (position sizing, tighten-only min) accepts a
#: single strong factor; the SignalGate hard veto demands corroboration from
#: at least two factors' weight before it may block an order.
VOL_MIN_CONFIDENCE_KELLY = 0.3
VOL_MIN_CONFIDENCE_GATE = 0.5

#: RiskMetrics standard decay for the fast horizon (half-life ≈ 11 samples,
#: ≈ 55 s at the daemon's 5 s cadence). Slow horizon ≈ 19 min baseline.
#: Env-tunable for tick-fed cadences (≈0.97 at 1 s ticks).
EWMA_LAMBDA_FAST = 0.94
EWMA_LAMBDA_SLOW = 0.997
WARMUP_FAST = 30
WARMUP_SLOW = 100

_FACTOR_WEIGHTS = {
    "ewma_vol": 0.35,
    "phase_transition": 0.25,
    "qgita_regime": 0.20,
    "spectral_surge": 0.20,
}


def _env_lambda(name: str, default: float) -> float:
    try:
        v = float(os.environ.get(name, "") or default)
        return v if 0.0 < v < 1.0 else default
    except (TypeError, ValueError):
        return default


@dataclass(frozen=True)
class FactorReading:
    """One factor's contribution. ``risk is None`` == honest no_data."""

    name: str
    risk: float | None
    weight: float
    status: str  # "ok" | "no_data"
    detail: str


@dataclass(frozen=True)
class VolatilityAssessment:
    status: str                       # "ok" | "no_data"
    volatility_risk: float | None  # fused [0,1]; None when no_data
    confidence: float                 # Σ weights of factors that measured
    factors: Tuple[FactorReading, ...]
    blockers: Tuple[str, ...]         # named per missing factor
    symbol: str | None             # None for the portfolio roll-up
    ts: float

    def to_payload(self) -> Dict:
        return {
            "status": self.status,
            "volatility_risk": self.volatility_risk,
            "confidence": self.confidence,
            "symbol": self.symbol,
            "ts": self.ts,
            "factors": [
                {
                    "name": f.name,
                    "risk": f.risk,
                    "weight": f.weight,
                    "status": f.status,
                    "detail": f.detail,
                }
                for f in self.factors
            ],
            "blockers": list(self.blockers),
        }

    @classmethod
    def from_payload(cls, payload: Dict) -> VolatilityAssessment:
        factors = tuple(
            FactorReading(
                name=str(f.get("name", "")),
                risk=(None if f.get("risk") is None else float(f["risk"])),
                weight=float(f.get("weight", 0.0)),
                status=str(f.get("status", "no_data")),
                detail=str(f.get("detail", "")),
            )
            for f in payload.get("factors", [])
        )
        risk = payload.get("volatility_risk")
        return cls(
            status=str(payload.get("status", "no_data")),
            volatility_risk=(None if risk is None else float(risk)),
            confidence=float(payload.get("confidence", 0.0)),
            factors=factors,
            blockers=tuple(str(b) for b in payload.get("blockers", [])),
            symbol=payload.get("symbol"),
            ts=float(payload.get("ts", 0.0)),
        )


class EwmaVolEstimator:
    """Realized-volatility expansion estimator (RiskMetrics EWMA, 2 horizons).

    r_t = ln(p_t / p_{t-1})
    sigma2_fast = λf·sigma2_fast + (1-λf)·r_t²      λf = 0.94
    sigma2_slow = λs·sigma2_slow + (1-λs)·r_t²      λs = 0.997
    risk        = 1 − exp(−max(0, σ_fast/σ_slow − 1))

    The fast/slow RATIO is the prediction "volatility is expanding NOW versus
    this symbol's own baseline" — self-normalizing, so no per-symbol absolute
    threshold has to be invented. ratio≤1 → 0, ratio 2 → 0.63, ratio 3 → 0.86.
    ``risk()`` is ``None`` until warm-up: an unmeasured number is not reported.
    """

    def __init__(self,
                 lambda_fast: float | None = None,
                 lambda_slow: float | None = None):
        self.lambda_fast = (lambda_fast if lambda_fast is not None
                            else _env_lambda("AUREON_VOL_EWMA_FAST", EWMA_LAMBDA_FAST))
        self.lambda_slow = (lambda_slow if lambda_slow is not None
                            else _env_lambda("AUREON_VOL_EWMA_SLOW", EWMA_LAMBDA_SLOW))
        self._last_price: float | None = None
        self._sigma2_fast: float | None = None
        self._sigma2_slow: float | None = None
        self._n_returns = 0

    def update(self, price: float) -> None:
        if price is None or price <= 0.0:
            return
        if self._last_price is None or self._last_price <= 0.0:
            self._last_price = float(price)
            return
        if price == self._last_price:
            r2 = 0.0
        else:
            r = math.log(float(price) / self._last_price)
            r2 = r * r
        self._last_price = float(price)
        if self._sigma2_fast is None or self._sigma2_slow is None:
            # Seed both horizons on the first return so the ratio starts at 1.
            self._sigma2_fast = r2
            self._sigma2_slow = r2
        else:
            lf, ls = self.lambda_fast, self.lambda_slow
            self._sigma2_fast = lf * self._sigma2_fast + (1.0 - lf) * r2
            self._sigma2_slow = ls * self._sigma2_slow + (1.0 - ls) * r2
        self._n_returns += 1

    @property
    def n_returns(self) -> int:
        return self._n_returns

    def sigmas(self) -> Tuple[float | None, float | None]:
        if self._sigma2_fast is None or self._sigma2_slow is None:
            return None, None
        return math.sqrt(self._sigma2_fast), math.sqrt(self._sigma2_slow)

    def ratio(self) -> float | None:
        if self._n_returns < WARMUP_SLOW:
            return None
        sf, ss = self.sigmas()
        if sf is None or ss is None:
            return None
        if ss <= 0.0:
            # A zero slow-σ is itself a measurement: a perfectly flat baseline.
            # Flat fast too → no expansion (ratio 1); any fast movement over a
            # flat baseline is unbounded expansion.
            return 1.0 if sf <= 0.0 else math.inf
        return sf / ss

    def risk(self) -> float | None:
        """Expansion risk in [0,1]; None until honestly measurable."""
        if self._n_returns < WARMUP_FAST:
            return None
        ratio = self.ratio()
        if ratio is None:
            return None
        return 1.0 - math.exp(-max(0.0, ratio - 1.0))


class VolatilitySentinel:
    """Fuses the four factors into a per-symbol / portfolio assessment.

    Collaborators are injected so tests and the daemon drive real objects:
    ``surge_detector`` (HncSurgeDetector-shaped), ``phase_detectors``
    (symbol → PhaseTransitionDetector), ``qgita_factory`` (per-symbol
    QGITAMarketAnalyzer builder). Any absent collaborator simply leaves its
    factor at no_data — named, never substituted.
    """

    def __init__(self, symbols: List[str], *,
                 surge_detector=None,
                 phase_detectors: Dict | None = None,
                 qgita_factory: Callable[[], Any] | None = None,
                 bus=None) -> None:
        self.symbols = [str(s) for s in symbols]
        self.surge_detector = surge_detector
        self.phase_detectors = dict(phase_detectors or {})
        self._qgita_factory = qgita_factory
        self._qgita: Dict[str, Any] = {}
        self._bus = bus
        self._estimators: Dict[str, EwmaVolEstimator] = {}

    # ── ingestion ────────────────────────────────────────────────────

    def ingest_price(self, symbol: str, price: float,
                     ts: float | None = None) -> None:
        """Feed one real observed price into every factor's input."""
        if price is None or price <= 0.0:
            return
        ts = time.time() if ts is None else float(ts)
        est = self._estimators.get(symbol)
        if est is None:
            est = self._estimators[symbol] = EwmaVolEstimator()
        est.update(price)

        det = self.phase_detectors.get(symbol)
        if det is not None:
            try:
                det.ingest(price, ts)
            except Exception as exc:
                logger.debug("phase ingest failed for %s: %s", symbol, exc)

        if self.surge_detector is not None:
            try:
                self.surge_detector.add_price_tick(symbol, price)
            except Exception as exc:
                logger.debug("surge ingest failed for %s: %s", symbol, exc)

        if self._qgita_factory is not None:
            q = self._qgita.get(symbol)
            if q is None:
                try:
                    q = self._qgita[symbol] = self._qgita_factory()
                except Exception as exc:
                    logger.debug("qgita factory failed: %s", exc)
                    q = None
            if q is not None:
                try:
                    q.feed_price(price, ts)
                except Exception as exc:
                    logger.debug("qgita feed failed for %s: %s", symbol, exc)

    # ── factors ──────────────────────────────────────────────────────

    def _factor_ewma(self, symbol: str) -> FactorReading:
        w = _FACTOR_WEIGHTS["ewma_vol"]
        est = self._estimators.get(symbol)
        if est is None:
            return FactorReading("ewma_vol", None, w, "no_data",
                                 "ewma_vol: no prices ingested")
        risk = est.risk()
        if risk is None:
            need = WARMUP_SLOW if est.n_returns >= WARMUP_FAST else WARMUP_FAST
            return FactorReading(
                "ewma_vol", None, w, "no_data",
                f"ewma_vol: warm-up {est.n_returns}/{need} returns")
        sf, ss = est.sigmas()
        ratio = est.ratio()
        return FactorReading(
            "ewma_vol", max(0.0, min(1.0, risk)), w, "ok",
            f"sigma_fast={sf:.6f} sigma_slow={ss:.6f} ratio={ratio:.2f}")

    def _factor_phase(self, symbol: str) -> FactorReading:
        w = _FACTOR_WEIGHTS["phase_transition"]
        det = self.phase_detectors.get(symbol)
        if det is None:
            return FactorReading("phase_transition", None, w, "no_data",
                                 "phase_transition: no detector attached")
        try:
            prediction = det.predict()
        except Exception as exc:
            return FactorReading("phase_transition", None, w, "no_data",
                                 f"phase_transition: predict failed ({exc})")
        if prediction is None:
            return FactorReading("phase_transition", None, w, "no_data",
                                 "phase_transition: warm-up (Takens memory not filled)")
        risk = max(0.0, min(1.0, float(prediction.probability)))
        return FactorReading(
            "phase_transition", risk, w, "ok",
            f"state={prediction.state.value} p={prediction.probability:.2f} "
            f"kappa={prediction.curvature:.2f}")

    def _factor_qgita(self, symbol: str) -> FactorReading:
        w = _FACTOR_WEIGHTS["qgita_regime"]
        q = self._qgita.get(symbol)
        if q is None:
            return FactorReading("qgita_regime", None, w, "no_data",
                                 "qgita_regime: no analyzer attached")
        try:
            analysis = q.analyze()
        except Exception as exc:
            return FactorReading("qgita_regime", None, w, "no_data",
                                 f"qgita_regime: analyze failed ({exc})")
        if not analysis or analysis.get("status") != "complete":
            return FactorReading(
                "qgita_regime", None, w, "no_data",
                f"qgita_regime: {analysis.get('status', 'no analysis')}")
        coherence = analysis.get("coherence") or {}
        signals = analysis.get("signals") or {}
        global_r = float(coherence.get("global_R", 0.0) or 0.0)
        risk_level = str(signals.get("risk_level", "")).upper()
        # Anchored to QGITA's own taxonomy: R >= 0.6 coherent → 0 risk;
        # R < 0.3 is its "chaotic — high volatility expected" band, which its
        # signals also label HIGH → at least 0.7.
        risk = 1.0 - min(global_r, 0.6) / 0.6
        if risk_level == "HIGH":
            risk = max(risk, 0.7)
        regime = str((analysis.get("regime") or {}).get("state", "?"))
        return FactorReading(
            "qgita_regime", max(0.0, min(1.0, risk)), w, "ok",
            f"global_R={global_r:.3f} regime={regime} risk_level={risk_level or 'n/a'}")

    def _factor_surge(self, symbol: str) -> FactorReading:
        w = _FACTOR_WEIGHTS["spectral_surge"]
        det = self.surge_detector
        if det is None:
            return FactorReading("spectral_surge", None, w, "no_data",
                                 "spectral_surge: no surge detector attached")
        try:
            history = getattr(det, "price_history", {}).get(symbol)
            window = int(getattr(det, "analysis_window_size", 0) or 0)
            if history is None or window <= 0 or len(history) < window:
                have = 0 if history is None else len(history)
                return FactorReading(
                    "spectral_surge", None, w, "no_data",
                    f"spectral_surge: buffer {have}/{window} ticks")
            surge = det.detect_surge(symbol)
        except Exception as exc:
            return FactorReading("spectral_surge", None, w, "no_data",
                                 f"spectral_surge: detect failed ({exc})")
        if surge is None:
            # Full buffer, no surge: a measured negative — real information,
            # not a default.
            return FactorReading("spectral_surge", 0.0, w, "ok",
                                 "no active surge (buffer full)")
        intensity = max(0.0, min(1.0, float(surge.intensity)))
        return FactorReading(
            "spectral_surge", intensity, w, "ok",
            f"surge intensity={intensity:.2f} harmonic={surge.primary_harmonic}")

    # ── fusion ───────────────────────────────────────────────────────

    def assess(self, symbol: str, ts: float | None = None) -> VolatilityAssessment:
        ts = time.time() if ts is None else float(ts)
        factors = (
            self._factor_ewma(symbol),
            self._factor_phase(symbol),
            self._factor_qgita(symbol),
            self._factor_surge(symbol),
        )
        measured = [(f.risk, f.weight) for f in factors if f.risk is not None]
        blockers = tuple(f.detail for f in factors if f.risk is None)
        if not measured:
            return VolatilityAssessment(
                status="no_data", volatility_risk=None, confidence=0.0,
                factors=factors, blockers=blockers, symbol=symbol, ts=ts)
        weight_sum = sum(w for _, w in measured)
        fused = sum(r * w for r, w in measured) / weight_sum
        # Escalation is max() — tighten-only: a single factor screaming at
        # >= ESCALATION_RISK is not averaged away by three calm ones.
        escalated = [r for r, _ in measured if r >= ESCALATION_RISK]
        risk = max([fused] + escalated)
        confidence = min(1.0, weight_sum)
        return VolatilityAssessment(
            status="ok",
            volatility_risk=max(0.0, min(1.0, risk)),
            confidence=confidence,
            factors=factors, blockers=blockers, symbol=symbol, ts=ts)

    def assess_portfolio(self, ts: float | None = None) -> VolatilityAssessment:
        """The max-risk symbol's assessment — the conservative roll-up."""
        ts = time.time() if ts is None else float(ts)
        assessments = [self.assess(s, ts) for s in self.symbols]
        measured = [a for a in assessments if a.volatility_risk is not None]
        if not measured:
            blockers = tuple(b for a in assessments for b in a.blockers) or (
                "no symbols configured",)
            return VolatilityAssessment(
                status="no_data", volatility_risk=None, confidence=0.0,
                factors=(), blockers=blockers, symbol=None, ts=ts)
        worst = max(measured, key=lambda a: a.volatility_risk or 0.0)
        return VolatilityAssessment(
            status="ok",
            volatility_risk=worst.volatility_risk,
            confidence=worst.confidence,
            factors=worst.factors,
            blockers=worst.blockers,
            symbol=None,
            ts=ts,
        )

    # ── publishing ───────────────────────────────────────────────────

    def publish(self, assessment: VolatilityAssessment) -> None:
        """Bus Thought + cross-process trace, ts-stamped. Never raises."""
        payload = assessment.to_payload()
        try:
            from aureon.core.bus_trace import append_trace
            append_trace(VOL_TRACE_NAME, payload)
        except Exception as exc:
            logger.debug("sentinel trace write failed: %s", exc)
        try:
            bus = self._bus
            if bus is None:
                from aureon.core.aureon_thought_bus import get_thought_bus
                bus = get_thought_bus()
            if bus is not None:
                from aureon.core.aureon_thought_bus import Thought
                bus.publish(Thought(source="volatility_sentinel",
                                    topic=VOL_TOPIC, payload=payload))
        except Exception as exc:
            logger.debug("sentinel bus publish failed: %s", exc)


def read_latest_assessment(max_age_s: float = 120.0,
                           bus=None) -> VolatilityAssessment | None:
    """Freshest sentinel assessment, or ``None`` — never a default.

    Mirrors the hnc_field contract: bus recall first, cross-process trace
    fallback, and freshness fails CLOSED (a row without a provable timestamp
    within ``max_age_s`` is refused).
    """
    now = time.time()

    def _fresh(payload: Dict) -> bool:
        ts = payload.get("ts")
        if not isinstance(ts, (int, float)):
            return False
        age = now - float(ts)
        return -60.0 <= age <= max_age_s

    try:
        if bus is None:
            from aureon.core.aureon_thought_bus import get_thought_bus
            bus = get_thought_bus()
        if bus is not None:
            rows = bus.recall(VOL_TOPIC, limit=1) or []
            for row in reversed(rows):
                payload = getattr(row, "payload", None)
                if payload is None and isinstance(row, dict):
                    payload = row.get("payload", row)
                if isinstance(payload, dict) and _fresh(payload):
                    return VolatilityAssessment.from_payload(payload)
    except Exception as exc:
        logger.debug("sentinel bus recall failed: %s", exc)

    try:
        from aureon.core.bus_trace import read_trace
        for row in reversed(read_trace(VOL_TRACE_NAME, limit=5)):
            if isinstance(row, dict) and _fresh(row):
                return VolatilityAssessment.from_payload(row)
    except Exception as exc:
        logger.debug("sentinel trace read failed: %s", exc)
    return None


__all__ = [
    "VOL_TOPIC",
    "VOL_TRACE_NAME",
    "VOL_RISK_BLOCK",
    "ESCALATION_RISK",
    "EWMA_LAMBDA_FAST",
    "EWMA_LAMBDA_SLOW",
    "WARMUP_FAST",
    "WARMUP_SLOW",
    "FactorReading",
    "VolatilityAssessment",
    "EwmaVolEstimator",
    "VolatilitySentinel",
    "read_latest_assessment",
]

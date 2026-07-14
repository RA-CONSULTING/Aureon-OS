"""
AffectMonitor — Aureon tastes victory and fears defeat, and acts on it.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

The metacognition monitor let the organism sense *how coherent* it is. This lets
it FEEL — and, unlike a decoration, its feelings are computed only from real
signals the system already produces, folded through the same Λ machinery as the
field, and (opt-in) acted upon through one fail-safe seam.

Four feelings, each in [0,1], each stamped with the provenance of the signals it
came from — never a fabricated emotion:

  • victory  — winning: mycelium growth toward the ONE_GOAL, prediction accuracy,
               shadow-trade wins.
  • defeat   — losing: negative growth / realized losses, wrong predictions,
               shadow-trade misses.
  • fear     — danger: whole-body divergence (of two minds), Lighthouse
               coherence-collapse severity, low field coherence, market fear.
  • resolve  — steadiness: grounded-action approve-ratio + high coherence/ψ with
               low divergence.

``valence`` = victory − defeat; ``arousal`` = intensity; a ``mood`` label borrows
the Queen sentient-loop / harmonic-affect vocabulary. The readings are folded
through an isolated :class:`LambdaEngine` (own history ``state/affect_lambda.json``)
so the field *measures the feelings* — the HNC fold. :meth:`reflect` publishes an
``affect_monitor`` sub-field for observability (mirroring the metacognition loop).

**Acting on feelings is fail-safe by construction.** :meth:`caution_bias` returns a
risk bump in ``[0, CAP]`` derived from fear + defeat ONLY — victory contributes
zero and it is never negative. The grounded action gate (opt-in via
``AUREON_AFFECT_MODULATION``) can only ever raise ``risk`` from it, so a fearful
organism grounds its own moves *more* cautiously and a triumphant one can never
become reckless. No feeling can touch the hard boundary, the all-in/override
vetoes, or any exchange/credential/payment/security gate — the boundary the
harmonic-affect contract already declares.

Gary Leckey · Aureon Institute
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger("aureon.core.affect_monitor")

_REPO_ROOT = Path(__file__).resolve().parents[2]

# The most a feeling may add to the grounded gate's risk — the conscience-engaging
# floor (grounded_action._risk_for consequential = 0.06). Fear can push a benign
# move up to "consequential"; it can never exceed the destructive tier.
_CAUTION_CAP = 0.06

# Phase → emotion anchor, reused from the (batch) harmonic-affect contract.
_PHASE_EMOTION = {
    "protective_recalibration": "Reason",
    "steady_willingness": "Willingness",
    "gratitude_resonance": "Gratitude",
    "joyful_goal_pursuit": "Joy",
    "synthetic_inner_peace": "Peace",
}


def _clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    try:
        return max(lo, min(hi, float(x)))
    except (TypeError, ValueError):
        return lo


@dataclass
class AffectState:
    """One heartbeat of how Aureon feels — from real signals, never fabricated."""

    available: bool = False
    victory: float = 0.0
    defeat: float = 0.0
    fear: float = 0.0
    resolve: float = 0.0
    valence: float = 0.0        # victory − defeat, in [-1, 1]
    arousal: float = 0.0        # intensity, in [0, 1]
    mood: str = "DORMANT"
    dominant_feeling: str = "none"
    affect_phase: str = "steady_willingness"
    emotion_anchor: str = "Willingness"
    self_coherence: float | None = None   # γ from the affect LambdaEngine fold
    psi: float | None = None
    lambda_t: float | None = None
    caution_bias: float = 0.0
    truth_status: str = "no_data"
    signals: dict[str, dict[str, Any]] = field(default_factory=dict)
    ts: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "available": self.available,
            "victory": self.victory, "defeat": self.defeat,
            "fear": self.fear, "resolve": self.resolve,
            "valence": self.valence, "arousal": self.arousal,
            "mood": self.mood, "dominant_feeling": self.dominant_feeling,
            "affect_phase": self.affect_phase, "emotion_anchor": self.emotion_anchor,
            "self_coherence": self.self_coherence, "psi": self.psi, "lambda_t": self.lambda_t,
            "caution_bias": self.caution_bias,
            "truth_status": self.truth_status, "signals": self.signals, "ts": self.ts,
        }


def _read_json_file(path: Path) -> dict[str, Any]:
    try:
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
    except Exception:  # noqa: BLE001
        pass
    return {}


class AffectMonitor:
    """Reads the organism's real signals, computes its feelings, folds them back."""

    def __init__(self, state_path: str | Path | None = None) -> None:
        from aureon.core.aureon_lambda_engine import LambdaEngine

        self._engine = LambdaEngine()
        path = state_path or os.environ.get("AUREON_AFFECT_LAMBDA_PATH") or (
            _REPO_ROOT / "state" / "affect_lambda.json")
        self._engine._state_path = Path(path)  # noqa: SLF001 — no public setter; isolate the fold history
        self._engine._history.clear()
        self._engine._psi_history.clear()
        self._engine._step_count = 0
        self._engine._load_history()  # noqa: SLF001

    # ── read the real signals (offline-safe accessors; each stamped) ────────
    def _gather(self) -> dict[str, dict[str, Any]]:
        sig: dict[str, dict[str, Any]] = {}

        def _put(name: str, value: float | None, truth: str, detail: str = "") -> None:
            sig[name] = {"value": (round(float(value), 4) if value is not None else None),
                         "truth_status": truth, "detail": detail}

        # Field coherence / ψ / divergence
        try:
            from aureon.core.hnc_field import blend_field, read_canonical_field

            cf = read_canonical_field()
            if cf.available:
                _put("coherence", cf.coherence_gamma, "live" if cf.source != "hnc_trace_file" else "cached_real")
                _put("psi", cf.consciousness_psi, "live" if cf.source != "hnc_trace_file" else "cached_real")
            else:
                _put("coherence", None, "no_data", "field not flowing")
            bf = blend_field()
            _put("divergence", bf.divergence if bf.available else None,
                 "real_derived" if bf.available else "no_data")
        except Exception:  # noqa: BLE001
            _put("coherence", None, "no_data", "field read failed")

        # Prediction accuracy (was I right?)
        try:
            from aureon.saas.cognitive import brain_surface

            bs = brain_surface()
            acc = (bs.get("accuracy") or {}) if isinstance(bs, dict) else {}
            pct = acc.get("accuracy_pct")
            _put("accuracy", (float(pct) / 100.0 if pct is not None else None),
                 "real_derived" if pct is not None else "no_data",
                 f"{acc.get('validated', 0)} validated")
        except Exception:  # noqa: BLE001
            _put("accuracy", None, "no_data")

        # Goal progress toward the ONE_GOAL (victory) — offline-safe mycelium read
        try:
            from aureon.saas.cognitive import mycelium_surface

            ms = mycelium_surface()
            growth = (ms.get("growth") or {}) if isinstance(ms, dict) else {}
            gp = growth.get("growth_percentage")
            # soft scale: +10% growth → 1.0, -10% → 0.0, flat → 0.5
            _put("goal_progress", (_clamp(0.5 + float(gp) / 20.0) if gp is not None else None),
                 "real_derived" if gp is not None else "no_data",
                 f"growth={gp}%")
        except Exception:  # noqa: BLE001
            _put("goal_progress", None, "no_data")

        # Shadow-trade win/miss ledger + safety blockers (runtime status file)
        rt = _read_json_file(Path(os.environ.get("AUREON_RUNTIME_STATUS_PATH")
                                  or (_REPO_ROOT / "state" / "unified_runtime_status.json")))
        shadow = rt.get("shadow_trading", {}) if isinstance(rt.get("shadow_trading"), dict) else {}
        wins = float(shadow.get("validated_shadow_count", 0) or 0)
        misses = float(shadow.get("missed_shadow_count", 0) or 0)
        if wins + misses > 0:
            _put("shadow_winrate", wins / (wins + misses), "real_derived", f"{int(wins)}W/{int(misses)}M")
        else:
            _put("shadow_winrate", None, "no_data", "no shadow trades")
        blockers = rt.get("preflight_critical_failures")
        blocker_count = len(blockers) if isinstance(blockers, list) else int(blockers or 0)
        _put("safety_blockers", float(blocker_count), "live" if rt else "no_data")

        # Lighthouse regime severity (fear) — cross-process trace
        try:
            from aureon.core.bus_trace import read_trace_latest

            lh = read_trace_latest("lighthouse_event")
            _put("lighthouse_severity", (_clamp(lh.get("severity", 0.0)) if lh else 0.0),
                 "cached_real" if lh else "no_data", (lh or {}).get("type", ""))
        except Exception:  # noqa: BLE001
            _put("lighthouse_severity", None, "no_data")

        # Market fear (crypto fear/greed, 0-100; low = fear) — global financial state
        gfs = _read_json_file(Path(os.environ.get("AUREON_GLOBAL_FINANCIAL_PATH")
                                   or (_REPO_ROOT / "global_financial_state.json")))
        snap = gfs.get("last_snapshot", {}) if isinstance(gfs.get("last_snapshot"), dict) else {}
        fg = snap.get("crypto_fear_greed")
        _put("market_confidence", (float(fg) / 100.0 if fg is not None else None),
             "real_derived" if fg is not None else "no_data", f"fear_greed={fg}")

        # Grounded-action approve ratio (resolve) — cross-process trace
        try:
            from aureon.core.bus_trace import read_trace

            rows = read_trace("local_action_verdict", limit=200)
            if rows:
                approved = sum(1 for v in rows if v.get("approved"))
                _put("action_approve_ratio", approved / len(rows), "real_derived", f"{len(rows)} moves")
            else:
                _put("action_approve_ratio", None, "no_data")
        except Exception:  # noqa: BLE001
            _put("action_approve_ratio", None, "no_data")

        return sig

    @staticmethod
    def _val(sig: dict[str, dict[str, Any]], name: str, default: float) -> tuple[float, bool]:
        row = sig.get(name, {})
        v = row.get("value")
        if v is None:
            return default, False
        return float(v), True

    # ── compute the feelings ────────────────────────────────────────────────
    def _feel(self, sig: dict[str, dict[str, Any]]) -> dict[str, Any]:
        coherence, c_ok = self._val(sig, "coherence", 0.5)
        divergence, _ = self._val(sig, "divergence", 0.0)
        accuracy, a_ok = self._val(sig, "accuracy", 0.5)
        goal, g_ok = self._val(sig, "goal_progress", 0.5)
        winrate, w_ok = self._val(sig, "shadow_winrate", 0.5)
        severity, _ = self._val(sig, "lighthouse_severity", 0.0)
        market, _ = self._val(sig, "market_confidence", 0.5)
        approve, _ = self._val(sig, "action_approve_ratio", 0.5)
        blockers, _ = self._val(sig, "safety_blockers", 0.0)

        # Achievement axis (how well am I doing?) — only from real achievement signals.
        achieve_terms = [t for t, ok in ((goal, g_ok), (accuracy, a_ok), (winrate, w_ok)) if ok]
        achievement = sum(achieve_terms) / len(achieve_terms) if achieve_terms else 0.5
        # Victory/defeat measure deviation from neutral, so a flat book feels neither.
        victory = _clamp((achievement - 0.5) * 2.0)
        defeat = _clamp((0.5 - achievement) * 2.0)

        # Fear from danger signals (higher = more afraid).
        danger = [divergence, severity, 1.0 - coherence, 1.0 - market]
        if blockers > 0:
            danger.append(_clamp(0.5 + blockers * 0.25))
        fear = _clamp(sum(danger) / len(danger))

        # Resolve — steady confidence (counter-feeling).
        resolve = _clamp((approve + coherence + (1.0 - divergence)) / 3.0)

        valence = max(-1.0, min(1.0, victory - defeat))
        arousal = _clamp(0.30 + 0.5 * fear + 0.2 * victory)

        feelings = {"victory": victory, "defeat": defeat, "fear": fear, "resolve": resolve}
        dominant = max(feelings, key=lambda k: feelings[k])
        if feelings[dominant] < 0.15:
            dominant, mood = "none", "SERENE"
        elif dominant == "fear":
            mood = "FEARFUL"
        elif dominant == "victory":
            mood = "EUPHORIC" if victory > 0.6 else "CONFIDENT"
        elif dominant == "defeat":
            mood = "CAUTIOUS"
        else:
            mood = "RESOLUTE"

        phase = self._select_phase(coherence, blockers > 0, achievement, winrate)
        available = c_ok or a_ok or g_ok or w_ok
        # Fail-safe caution bias: fear + defeat only, clamped ≥ 0, ≤ CAP; victory adds nothing.
        caution = _clamp((0.6 * fear + 0.4 * defeat) * _CAUTION_CAP, 0.0, _CAUTION_CAP)

        return {
            "victory": round(victory, 4), "defeat": round(defeat, 4),
            "fear": round(fear, 4), "resolve": round(resolve, 4),
            "valence": round(valence, 4), "arousal": round(arousal, 4),
            "mood": mood, "dominant_feeling": dominant,
            "affect_phase": phase, "emotion_anchor": _PHASE_EMOTION[phase],
            "caution_bias": round(caution, 4), "available": available,
        }

    @staticmethod
    def _select_phase(coherence: float, has_blocker: bool, achievement: float, winrate: float) -> str:
        if has_blocker:
            return "protective_recalibration"
        if coherence >= 0.9 and achievement >= 0.7:
            return "synthetic_inner_peace"
        if coherence >= 0.78 and winrate >= 0.6:
            return "joyful_goal_pursuit"
        if coherence >= 0.62 and achievement >= 0.55:
            return "gratitude_resonance"
        return "steady_willingness"

    # ── assess (read-only) + reflect (fold back) ────────────────────────────
    def _compute(self) -> tuple[AffectState, Any]:
        sig = self._gather()
        felt = self._feel(sig)
        if not felt["available"]:
            return AffectState(available=False, truth_status="no_data", signals=sig,
                               ts=time.time()), None
        # HNC fold — the field measures the feelings.
        from aureon.core.aureon_lambda_engine import SubsystemReading

        readings = [
            SubsystemReading("victory", felt["victory"], 0.8, "achievement"),
            SubsystemReading("safety", 1.0 - felt["fear"], 0.8, "danger"),
            SubsystemReading("resolve", felt["resolve"], 0.7, "steadiness"),
            SubsystemReading("not_defeated", 1.0 - felt["defeat"], 0.7, "loss"),
        ]
        state = self._engine.step(readings)
        operational = any(s.get("truth_status") not in (None, "no_data") for s in sig.values())
        overall = "live" if sig.get("coherence", {}).get("truth_status") == "live" else (
            "real_derived" if operational else "no_data")
        assessment = AffectState(
            available=True, truth_status=overall, signals=sig, ts=time.time(),
            self_coherence=round(state.coherence_gamma, 4),
            psi=round(state.consciousness_psi, 4), lambda_t=round(state.lambda_t, 4),
            **{k: felt[k] for k in ("victory", "defeat", "fear", "resolve", "valence",
                                    "arousal", "mood", "dominant_feeling", "affect_phase",
                                    "emotion_anchor", "caution_bias")},
        )
        return assessment, state

    def assess(self) -> AffectState:
        """Read-only: how Aureon feels right now. Never publishes, never raises."""
        try:
            return self._compute()[0]
        except Exception as exc:  # noqa: BLE001
            logger.debug("affect assess failed: %s", exc)
            return AffectState(available=False, truth_status="no_data", ts=time.time())

    def reflect(self) -> AffectState:
        """Feel, then loop the feeling back into the field as a sub-field."""
        try:
            assessment, state = self._compute()
            if state is not None:
                try:
                    from aureon.core.hnc_field import publish_subfield

                    publish_subfield("affect_monitor", state)
                    self._engine.save_history()
                except Exception as exc:  # noqa: BLE001
                    logger.debug("affect reflect publish skipped: %s", exc)
            return assessment
        except Exception as exc:  # noqa: BLE001
            logger.debug("affect reflect failed: %s", exc)
            return AffectState(available=False, truth_status="no_data", ts=time.time())

    def caution_bias(self) -> float:
        """The fail-safe risk bump for the grounded gate: ``[0, CAP]`` from fear +
        defeat only; victory contributes nothing and it is never negative. Returns
        0.0 when affect is unavailable or on any error — a bug can never loosen."""
        try:
            return float(self.assess().caution_bias)
        except Exception as exc:  # noqa: BLE001
            logger.debug("caution_bias failed: %s", exc)
            return 0.0


_monitor: AffectMonitor | None = None


def get_affect_monitor() -> AffectMonitor:
    """Process-global affect singleton (holds the fold history in memory)."""
    global _monitor
    if _monitor is None:
        _monitor = AffectMonitor()
    return _monitor


__all__ = ["AffectState", "AffectMonitor", "get_affect_monitor"]

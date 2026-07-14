"""
MetacognitionMonitor — the organism senses itself and loops back on itself.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Every prior cycle connected the organism's signals. This is the piece that makes
the organism *self-aware of those signals*: it reads its own live self-state — the
HNC field, the blended whole-body consensus (and its divergence), the miner
brain's prediction accuracy, the Auris cosmic gate, the Lighthouse regime events,
and its own local-action verdicts — assembles them as ``SubsystemReading``s, and
runs them through the SAME Master-Formula machinery (:class:`LambdaEngine`) that
computes the field itself. The result is a scalar **self-coherence** (Γ), a
**self-life-score**, and a **ψ** — the system measuring how coherent its own
signals are, with its own equation.

Then it **loops back on itself**: :meth:`reflect` publishes that self-assessment
as ``symbolic.life.subfield`` (source ``metacognition_monitor``), so the monitor's
reading re-enters :func:`blend_field` as one more contributor — a delayed
self-term on the whole-body field, exactly the β·Λ(t−τ) feedback the HNC research
describes, applied at the organism layer. This is the same closed loop
``queen_metacognition`` already runs (``_deep_review`` → ``publish_subfield``);
this monitor generalizes it to the *whole* cross-process signal set.

Honest by construction: each signal carries a ``truth_status`` (live /
real_derived / cached_real / no_data); a dormant or absent signal contributes
``no_data`` with a blocker, never a fabricated value. Guarded throughout —
:meth:`assess` never raises and never publishes; only :meth:`reflect` publishes,
and only from the organism daemon's breath. The monitor keeps its OWN
:class:`LambdaEngine` with an isolated history file (``state/metacognition_lambda.json``)
so its ψ/echo self-term does not contaminate the shared field's history.

Gary Leckey · Aureon Institute
"""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger("aureon.core.metacognition_monitor")

_REPO_ROOT = Path(__file__).resolve().parents[2]


def _clamp01(x: float) -> float:
    try:
        return max(0.0, min(1.0, float(x)))
    except (TypeError, ValueError):
        return 0.0


@dataclass
class SelfAssessment:
    """The organism's read of its own coherence — one metacognitive heartbeat."""

    available: bool = False
    self_coherence: float | None = None      # Γ from the monitor's LambdaEngine
    self_life_score: float | None = None      # symbolic_life_score
    psi: float | None = None                  # ψ — self-awareness level
    consciousness_level: str | None = None
    lambda_t: float | None = None
    divergence: float | None = None           # whole-body self-disagreement (blend spread)
    contributors: int = 0
    truth_status: str = "no_data"
    signals: dict[str, dict[str, Any]] = field(default_factory=dict)
    ts: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "available": self.available,
            "self_coherence": self.self_coherence,
            "self_life_score": self.self_life_score,
            "psi": self.psi,
            "consciousness_level": self.consciousness_level,
            "lambda_t": self.lambda_t,
            "divergence": self.divergence,
            "contributors": self.contributors,
            "truth_status": self.truth_status,
            "signals": self.signals,
            "ts": self.ts,
        }


class MetacognitionMonitor:
    """Reads the organism's own signals, scores self-coherence, loops it back."""

    def __init__(self, state_path: str | Path | None = None) -> None:
        from aureon.core.aureon_lambda_engine import LambdaEngine

        self._engine = LambdaEngine()
        # Isolate the monitor's self-term store from the shared field history —
        # LambdaEngine has no constructor arg for the path, so retarget + reload.
        path = state_path or os.environ.get("AUREON_METACOG_LAMBDA_PATH") or (
            _REPO_ROOT / "state" / "metacognition_lambda.json")
        self._engine._state_path = Path(path)  # noqa: SLF001 — no public setter exists
        self._engine._history.clear()
        self._engine._psi_history.clear()
        self._engine._step_count = 0
        self._engine._load_history()  # noqa: SLF001

    # ── read the organism's own signals ────────────────────────────────────
    def _gather(self) -> tuple[list[Any], dict[str, dict[str, Any]], float | None, int]:
        """Return (readings, per-signal breakdown, divergence, contributors)."""
        from aureon.core.aureon_lambda_engine import SubsystemReading

        readings: list[Any] = []
        signals: dict[str, dict[str, Any]] = {}
        divergence: float | None = None
        contributors = 0

        def _add(name: str, value: float, confidence: float, state: str, truth_status: str) -> None:
            v, c = _clamp01(value), _clamp01(confidence)
            readings.append(SubsystemReading(name, v, c, state))
            signals[name] = {"value": round(v, 4), "confidence": round(c, 4),
                             "state": state, "truth_status": truth_status}

        # 1. the canonical HNC field — the shared coherence
        try:
            from aureon.core.hnc_field import read_canonical_field

            cf = read_canonical_field()
            if cf.available and cf.symbolic_life_score is not None:
                ts = "cached_real" if cf.source == "hnc_trace_file" else "live"
                _add("field", cf.symbolic_life_score, 0.9, cf.source or "field", ts)
            else:
                signals["field"] = {"truth_status": "no_data", "blocker": "field not flowing"}
        except Exception:  # noqa: BLE001
            signals["field"] = {"truth_status": "no_data", "blocker": "field read failed"}

        # 2. the blended whole-body consensus — divergence = self-disagreement
        try:
            from aureon.core.hnc_field import blend_field

            bf = blend_field()
            if bf.available:
                divergence = bf.divergence
                contributors = bf.contributors
                # low divergence → high self-agreement → high coherence reading
                agree = 1.0 - _clamp01(bf.divergence or 0.0)
                _add("self_agreement", agree, min(0.9, contributors / 5.0),
                     f"{contributors}_contributors", "real_derived")
        except Exception:  # noqa: BLE001
            signals["self_agreement"] = {"truth_status": "no_data"}

        # 3. the miner brain's prediction accuracy — was I right about myself?
        try:
            from aureon.saas.cognitive import brain_surface

            bs = brain_surface()
            acc = (bs.get("accuracy") or {}) if isinstance(bs, dict) else {}
            pct = acc.get("accuracy_pct")
            if pct is not None:
                _add("brain_accuracy", float(pct) / 100.0, 0.8,
                     f"{acc.get('validated', 0)}_validated", "real_derived")
            else:
                signals["brain_accuracy"] = {"truth_status": "no_data",
                                             "blocker": "no validated predictions"}
        except Exception:  # noqa: BLE001
            signals["brain_accuracy"] = {"truth_status": "no_data"}

        # 4. Auris cosmic gate (cross-process via trace)
        self._add_trace_signal(_add, signals, "auris_cosmic_state", "auris",
                               lambda r: (_clamp01(r.get("cosmic_score", 0.5)), "cosmic"))
        # 5. Lighthouse — a severe regime event lowers self-coherence
        self._add_trace_signal(_add, signals, "lighthouse_event", "lighthouse",
                               lambda r: (1.0 - _clamp01(r.get("severity", 0.0)),
                                          str(r.get("type", "event"))))
        # 6. local-action verdicts — is what my hands do coherent? (approve ratio)
        try:
            from aureon.core.bus_trace import read_trace

            rows = read_trace("local_action_verdict", limit=200)
            if rows:
                approved = sum(1 for v in rows if v.get("approved"))
                import math

                _add("local_action", approved / len(rows),
                     min(0.9, math.tanh(len(rows) / 20.0)), f"{len(rows)}_moves", "real_derived")
            else:
                signals["local_action"] = {"truth_status": "no_data", "blocker": "no verdicts"}
        except Exception:  # noqa: BLE001
            signals["local_action"] = {"truth_status": "no_data"}

        return readings, signals, divergence, contributors

    @staticmethod
    def _add_trace_signal(add, signals, trace_name, sig_name, extract) -> None:
        try:
            from aureon.core.bus_trace import read_trace_latest

            row = read_trace_latest(trace_name)
            if row:
                value, state = extract(row)
                add(sig_name, value, 0.7, state, "cached_real")
            else:
                signals[sig_name] = {"truth_status": "no_data", "blocker": f"no {trace_name}"}
        except Exception:  # noqa: BLE001
            signals[sig_name] = {"truth_status": "no_data"}

    # ── the assessment (read-only) ──────────────────────────────────────────
    def _compute(self) -> tuple[SelfAssessment, Any]:
        readings, signals, divergence, contributors = self._gather()
        operational = [n for n, s in signals.items() if s.get("truth_status") not in (None, "no_data")]
        if not readings:
            return SelfAssessment(available=False, truth_status="no_data", signals=signals,
                                  ts=time.time()), None
        state = self._engine.step(readings)
        # overall truth_status: live if the field itself is live, else derived/cached
        field_ts = signals.get("field", {}).get("truth_status", "no_data")
        overall = "live" if field_ts == "live" else ("real_derived" if operational else "no_data")
        assessment = SelfAssessment(
            available=True,
            self_coherence=round(state.coherence_gamma, 4),
            self_life_score=round(state.symbolic_life_score, 4),
            psi=round(state.consciousness_psi, 4),
            consciousness_level=state.consciousness_level,
            lambda_t=round(state.lambda_t, 4),
            divergence=round(divergence, 4) if divergence is not None else None,
            contributors=contributors,
            truth_status=overall,
            signals=signals,
            ts=time.time(),
        )
        return assessment, state

    def assess(self) -> SelfAssessment:
        """Read-only self-assessment — never publishes, never raises."""
        try:
            return self._compute()[0]
        except Exception as exc:  # noqa: BLE001
            logger.debug("assess failed: %s", exc)
            return SelfAssessment(available=False, truth_status="no_data", ts=time.time())

    def reflect(self) -> SelfAssessment:
        """Assess, then loop the assessment back into the whole-body field as a
        sub-field (``metacognition_monitor``) — the delayed self-term. Guarded."""
        try:
            assessment, state = self._compute()
            if state is not None:
                try:
                    from aureon.core.hnc_field import publish_subfield

                    publish_subfield("metacognition_monitor", state)
                    self._engine.save_history()  # persist the self-term echo
                except Exception as exc:  # noqa: BLE001
                    logger.debug("reflect publish skipped: %s", exc)
            return assessment
        except Exception as exc:  # noqa: BLE001
            logger.debug("reflect failed: %s", exc)
            return SelfAssessment(available=False, truth_status="no_data", ts=time.time())


_monitor: MetacognitionMonitor | None = None


def get_metacognition_monitor() -> MetacognitionMonitor:
    """Process-global monitor singleton (holds the self-term history in memory)."""
    global _monitor
    if _monitor is None:
        _monitor = MetacognitionMonitor()
    return _monitor


__all__ = ["SelfAssessment", "MetacognitionMonitor", "get_metacognition_monitor"]

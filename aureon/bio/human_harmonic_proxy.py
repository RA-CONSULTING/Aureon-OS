#!/usr/bin/env python3
"""Human-harmonic proxy — score a *derived* human signal with the phenolic engine.

This is the "Aureon Operator — human-signal proxy". It takes a human-derived
frequency series (in a future release: extracted from video / audio / image; for
now: a deterministic *synthetic* self-test that uses **no real human data**) and
runs it through the **same** falsifiable machinery that scores a molecule's
spectrum in :mod:`phenolic_fingerprint`:

* the identical two tests — Test A (coherence clustering) and Test B
  (golden-interval alignment),
* the identical mandatory controls — a positive control (a structured signal
  must be detected) and a negative control (noise must not over-fire); if either
  fails the whole run is **invalid** and no structure result is emitted,
* and, on top of the engine, the repo's **Operator authority boundary**: every
  result routes through the operator's deterministic hard-boundary check *and*
  the Queen's conscience veto before anything is emitted.

Scientific boundary (enforced, not decorative)
----------------------------------------------
This module evaluates **statistical structure in a derived signal only**. It is
**NOT** a measurement of a biological aura, field, health, or trait of any
person, and it makes **no efficacy claim**. A run requires explicit consent and
a provenance string, or it is blocked and scores nothing. The
:data:`SCIENTIFIC_BOUNDARY` sentence rides on every result and every emission.

Design constraints
------------------
Pure stdlib + numpy + the engine. No network, no real-media decoding, no
import-time side effects (the only import-time action is a guarded, suppressible
``link_system`` heartbeat). The engine's pre-registered logic and thresholds are
reused verbatim — nothing here tunes them.

Note on units: :func:`phenolic_fingerprint.peak_to_modulation_hz` assumes molecular
``cm^-1``/``nm`` inputs and a 20–60-octave electromagnetic downconversion, so it is
**not** used here. A human signal is already in Hz; :func:`fold_to_band` octave-folds
it into the same 1000–2000 Hz modulation band the engine's statistics operate in.
"""

from __future__ import annotations

import math
import sys
import time
import uuid
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

import numpy as np

# --- engine import (repo root holds phenolic_fingerprint.py) ---------------
# Mirror connector.py: import the engine by its bare module name. Ensure the
# repo root is importable regardless of how this module is invoked. Inserting a
# path is idempotent and free of behavioural side effects.
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import phenolic_fingerprint as engine  # noqa: E402

# --- guarded organism link (suppressible; never fatal) ---------------------
try:  # pragma: no cover - environment-dependent, best-effort
    from aureon.core.aureon_baton_link import link_system

    link_system(__name__)
except Exception:  # noqa: BLE001 - the proxy must import in any environment
    pass

__all__ = [
    "SCIENTIFIC_BOUNDARY",
    "TARGET_BAND_HZ",
    "HumanSignal",
    "SignalAdapter",
    "SyntheticSignalAdapter",
    "ProxyResult",
    "fold_to_band",
    "score_signal",
    "emit_proxy_result",
    "run_synthetic",
    "RUN_TOPIC",
    "TRACE_NAME",
    "main",
]

# ============================================================================
# CONSTANTS
# ============================================================================

#: The immutable scientific-boundary statement carried by every result.
SCIENTIFIC_BOUNDARY: str = (
    "Statistical structure in a derived signal only - NOT a measurement of a "
    "biological aura, field, health, or trait of any person; no efficacy claim."
)

#: Modulation band the engine's statistics operate in (reused from the engine).
TARGET_BAND_HZ: tuple[float, float] = tuple(engine.TARGET_BAND_HZ)  # type: ignore[assignment]

PHI: float = float(engine.PHI)

RUN_TOPIC: str = "bio.human_proxy.run"
TRACE_NAME: str = "human_harmonic_proxy"
SOURCE: str = "human_harmonic_proxy"


# ============================================================================
# SIGNAL MODEL + ADAPTER PROTOCOL
# ============================================================================


@dataclass(frozen=True)
class HumanSignal:
    """A derived human signal: a bare frequency series plus consent/provenance.

    ``frequencies_hz`` are already in Hz (e.g. a spectral summary of a consented
    recording). This dataclass carries **no** identifying content and no claim —
    only the numbers, where they came from, and whether consent was granted.
    """

    label: str
    frequencies_hz: tuple[float, ...]
    provenance: str
    consent: bool
    modality: str
    notes: str = ""


@runtime_checkable
class SignalAdapter(Protocol):
    """Contract every signal extractor must satisfy.

    Real video / audio / image extractors are **future, gated, consent-required
    work**. They are not shipped here; this protocol is the seam they will
    implement so the scoring + governance backbone never changes.
    """

    modality: str

    def extract(self, spec: Any) -> HumanSignal:  # pragma: no cover - protocol
        """Return a :class:`HumanSignal` for ``spec`` (adapter-defined)."""
        ...


class SyntheticSignalAdapter:
    """Deterministic self-test adapter — uses **no real human data**.

    ``mode="structured"`` plants a clustered, golden-ratio-spaced tone set that
    should be detected (exercises the "structure present" path).
    ``mode="noise"`` draws an envelope-matched random tone set that should not
    over-fire (the "structure absent" path). Fully seeded and reproducible.
    """

    modality: str = "synthetic"

    def extract(self, spec: Any = None, *, mode: str = "structured", seed: int = 0) -> HumanSignal:
        """Emit a labelled synthetic :class:`HumanSignal` for ``mode``/``seed``."""
        if mode == "structured":
            tones = _structured_tones()
            label = "synthetic-structured"
            notes = "planted clustered + phi-spaced tones (self-test only)"
        elif mode == "noise":
            tones = _noise_tones(seed)
            label = "synthetic-noise"
            notes = "envelope-matched random tones (self-test only)"
        else:  # pragma: no cover - guarded by callers
            raise ValueError(f"unknown synthetic mode {mode!r}")
        return HumanSignal(
            label=label,
            frequencies_hz=tuple(float(t) for t in tones),
            provenance="synthetic:self-test (no human subject)",
            consent=True,
            modality=self.modality,
            notes=notes,
        )


def _structured_tones() -> np.ndarray:
    """Two tight tone-clusters one golden ratio apart, both inside the band.

    Within-cluster pairs sit < the engine's coherence tolerance apart (drives
    Test A); the two cluster centres are exactly a factor of ``PHI`` apart, so
    every cross-cluster ratio is ``PHI`` (log-ratio 1.0 -> drives Test B). Both
    centres are chosen to lie inside ``[1000, 2000)`` so :func:`fold_to_band`
    is the identity and does not disturb the planted structure.
    """
    base = 1100.0
    centers = np.array([base, base * PHI])  # ~1100 and ~1780, both in-band
    offsets = np.array([-4.0, 0.0, 4.0])
    return np.sort((centers[:, None] + offsets[None, :]).ravel())


def _noise_tones(seed: int, n: int = 12) -> np.ndarray:
    """Deterministic random tones spanning roughly two octaves (folds non-trivially)."""
    rng = _rng(seed, 7)
    return np.sort(rng.uniform(700.0, 2800.0, size=n))


# ============================================================================
# bio -> vibe FOLD (Hz-native; distinct from the engine's cm^-1 downconversion)
# ============================================================================


def fold_to_band(freq_hz: float) -> float | None:
    """Octave-fold a positive Hz value into ``TARGET_BAND_HZ`` ``[1000, 2000)``.

    Repeatedly halves/doubles ``freq_hz`` until it lands in the band. Returns
    ``None`` for non-finite or non-positive inputs (the caller drops them). The
    fold is the identity for a value already in-band, so it is idempotent there.
    """
    low, high = TARGET_BAND_HZ
    f = float(freq_hz)
    if not math.isfinite(f) or f <= 0.0:
        return None
    while f < low:
        f *= 2.0
    while f >= high:
        f /= 2.0
    return f


def _fold_tones(frequencies_hz: tuple[float, ...] | list[float]) -> np.ndarray:
    """Fold every raw tone into the band, drop invalids, return a sorted array."""
    folded = [v for v in (fold_to_band(x) for x in frequencies_hz) if v is not None]
    return np.array(sorted(folded), dtype=float)


def _rng(seed: int, tag: int) -> np.random.Generator:
    """Reproducible generator stream for a (seed, purpose) pair (engine idiom)."""
    return np.random.default_rng([int(seed), int(tag)])


# ============================================================================
# RESULT
# ============================================================================


@dataclass(frozen=True)
class ProxyResult:
    """Outcome of scoring one :class:`HumanSignal`.

    ``structure_present`` is the human-signal analogue of the engine's
    ``separable`` flag (both Test A and Test B reject the null). When
    ``blocked`` is true (consent gate or Operator veto), :meth:`to_dict`
    suppresses every positive finding — a blocked run can never publish one.
    """

    valid: bool
    structure_present: bool
    test_A_p: float | None
    test_B_p: float | None
    n_tones: int
    controls: dict[str, Any]
    provenance: str
    consent: bool
    modality: str
    label: str
    blocked: bool = False
    reason: str | None = None
    boundary: str = SCIENTIFIC_BOUNDARY

    def to_dict(self) -> dict[str, Any]:
        """Serialise; positive findings are zeroed out whenever ``blocked``."""
        structure = self.structure_present
        p_a: float | None = self.test_A_p
        p_b: float | None = self.test_B_p
        if self.blocked:
            structure, p_a, p_b = False, None, None
        return {
            "valid": self.valid,
            "structure_present": structure,
            "test_A_p": p_a,
            "test_B_p": p_b,
            "n_tones": self.n_tones,
            "controls": self.controls,
            "provenance": self.provenance,
            "consent": self.consent,
            "modality": self.modality,
            "label": self.label,
            "blocked": self.blocked,
            "reason": self.reason,
            "boundary": self.boundary,
        }


def _blocked_result(
    signal: HumanSignal, reason: str, *, valid: bool = False, controls: dict[str, Any] | None = None
) -> ProxyResult:
    """Construct a fully-suppressed, blocked result for ``signal``."""
    return ProxyResult(
        valid=valid,
        structure_present=False,
        test_A_p=None,
        test_B_p=None,
        n_tones=0,
        controls=controls or {},
        provenance=signal.provenance,
        consent=signal.consent,
        modality=signal.modality,
        label=signal.label,
        blocked=True,
        reason=reason,
    )


# ============================================================================
# OPERATOR AUTHORITY BOUNDARY
# ============================================================================

_CONSCIENCE: Any | None = None


def _get_conscience() -> Any:
    """Return a cached, offline-safe :class:`QueenConscience` (lazy, guarded).

    Constructed once on first use (never at import time). Tests monkeypatch this
    to inject a stub verdict.
    """
    global _CONSCIENCE
    if _CONSCIENCE is None:
        from aureon.queen.queen_conscience import QueenConscience

        _CONSCIENCE = QueenConscience()
    return _CONSCIENCE


def _intent_line(signal: HumanSignal) -> str:
    """A plain-text intent for the operator's hard-boundary check (no raw arrays)."""
    return (
        f"score human-derived signal (modality={signal.modality}, "
        f"provenance={signal.provenance}); statistical structure only, "
        "no claim about the person"
    )


def _operator_gate(signal: HumanSignal, *, context: dict[str, Any]) -> tuple[bool, str | None]:
    """Route the run through the operator hard boundary + conscience veto.

    Returns ``(blocked, reason)``. Fail-safe: if either authority layer cannot be
    consulted, the run is **blocked** (never silently passed). Only scalar/string
    metadata is handed to the authority layers — never the raw tone array.
    """
    try:
        from aureon.operator.aureon_operator import _hard_boundary_violation
    except Exception:  # noqa: BLE001
        return True, "operator hard-boundary layer unreachable - fail-safe block"
    if _hard_boundary_violation(_intent_line(signal)) is not None:
        return True, "operator hard boundary refused the intent"

    try:
        whisper = _get_conscience().ask_why("score human-derived signal", context)
        verdict = getattr(getattr(whisper, "verdict", None), "name", None)
    except Exception:  # noqa: BLE001
        return True, "conscience veto layer unreachable - fail-safe block"
    if verdict == "VETO":
        return True, "conscience vetoed the run"
    return False, None


# ============================================================================
# SCORING
# ============================================================================


def score_signal(signal: HumanSignal, *, nulls: int = engine.DEFAULT_NULLS, seed: int = 0) -> ProxyResult:
    """Score ``signal`` with the phenolic engine under full governance.

    Order of enforcement: (1) consent + provenance gate, (2) mandatory engine
    controls, (3) Test A / Test B on the folded modulation tones, (4) Operator
    hard boundary + conscience veto. Any gate that trips blocks the run and no
    positive finding survives into :meth:`ProxyResult.to_dict`.
    """
    # (1) consent / provenance gate
    if signal.consent is not True or not str(signal.provenance).strip():
        return _blocked_result(signal, "consent/provenance required")

    # (2) mandatory controls (identical to the engine's assay validation)
    pos = engine.positive_control(nulls=nulls, seed=seed)
    neg = engine.negative_control(nulls=nulls, seed=seed)
    controls = {"positive": pos.to_dict(), "negative": neg.to_dict()}
    if not (pos.passed and neg.passed):
        failed = [c.name for c in (pos, neg) if not c.passed]
        return ProxyResult(
            valid=False,
            structure_present=False,
            test_A_p=None,
            test_B_p=None,
            n_tones=0,
            controls=controls,
            provenance=signal.provenance,
            consent=signal.consent,
            modality=signal.modality,
            label=signal.label,
            blocked=False,
            reason=f"control(s) failed: {', '.join(failed)}",
        )

    # (3) fold + the two pre-registered tests
    tones = _fold_tones(signal.frequencies_hz)
    if tones.size < 2:
        return ProxyResult(
            valid=True,
            structure_present=False,
            test_A_p=None,
            test_B_p=None,
            n_tones=int(tones.size),
            controls=controls,
            provenance=signal.provenance,
            consent=signal.consent,
            modality=signal.modality,
            label=signal.label,
            blocked=False,
            reason="insufficient tones (need >= 2) after octave-fold",
        )
    p_a = engine.test_A(tones, nulls=nulls, rng=_rng(seed, 1))
    p_b = engine.test_B(tones, nulls=nulls, rng=_rng(seed, 2))
    present = bool(p_a < engine.ALPHA and p_b < engine.ALPHA)

    result = ProxyResult(
        valid=True,
        structure_present=present,
        test_A_p=float(p_a),
        test_B_p=float(p_b),
        n_tones=int(tones.size),
        controls=controls,
        provenance=signal.provenance,
        consent=signal.consent,
        modality=signal.modality,
        label=signal.label,
        blocked=False,
        reason=None,
    )

    # (4) Operator authority boundary — the final say on emission
    context = {
        "modality": signal.modality,
        "provenance": signal.provenance,
        "consent": signal.consent,
        "n_tones": int(tones.size),
        "structure_present": present,
        "purpose": "statistical structure probe of a derived signal; no claim about the person",
    }
    blocked, reason = _operator_gate(signal, context=context)
    if blocked:
        result = replace(result, blocked=True, reason=reason)
    return result


# ============================================================================
# COGNITION EMISSION (best-effort, guarded — a throwing bus never raises)
# ============================================================================


def emit_proxy_result(result: ProxyResult, *, bus: Any | None = None, trace: bool = True) -> dict[str, Any]:
    """Publish the (already-suppressed-if-blocked) result to cognition; return its dict.

    Mirrors :mod:`aureon.cognition.phenolic_bridge`: a ``bio.human_proxy.run``
    Thought on the ThoughtBus + a compact ``human_harmonic_proxy`` bus_trace, so
    the metacognition monitor / Queen can sense it. Bus/trace failures are
    swallowed — emission must never crash a scoring run.
    """
    payload = result.to_dict()
    try:
        from aureon.core.aureon_thought_bus import Thought, get_thought_bus

        target = bus if bus is not None else get_thought_bus()
        target.publish(
            Thought(source=SOURCE, topic=RUN_TOPIC, trace_id=uuid.uuid4().hex, payload=payload)
        )
    except Exception:  # noqa: BLE001 - emission is best-effort, never fatal
        pass

    if trace:
        try:
            from aureon.core.bus_trace import append_trace

            append_trace(
                TRACE_NAME,
                {
                    "valid": payload["valid"],
                    "structure_present": payload["structure_present"],
                    "blocked": payload["blocked"],
                    "n_tones": payload["n_tones"],
                    "modality": payload["modality"],
                    "boundary": SCIENTIFIC_BOUNDARY,
                    "_ts": time.time(),
                },
            )
        except Exception:  # noqa: BLE001 - trace mirror is best-effort
            pass

    return payload


# ============================================================================
# CONVENIENCE + CLI
# ============================================================================


def run_synthetic(mode: str = "structured", *, seed: int = 0, nulls: int = engine.DEFAULT_NULLS) -> ProxyResult:
    """Extract a synthetic signal for ``mode`` and score it (self-test convenience)."""
    signal = SyntheticSignalAdapter().extract(mode=mode, seed=seed)
    return score_signal(signal, nulls=nulls, seed=seed)


def main(argv: list[str] | None = None) -> int:
    """Run the synthetic self-test and print a ✅/❌ readout. Returns 0 on success."""
    import argparse

    parser = argparse.ArgumentParser(description="Human-harmonic proxy synthetic self-test.")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--nulls", type=int, default=engine.DEFAULT_NULLS)
    args = parser.parse_args(argv)

    print("Human-harmonic proxy — synthetic self-test (no real human data)")
    print(f"  boundary: {SCIENTIFIC_BOUNDARY}")

    structured = run_synthetic("structured", seed=args.seed, nulls=args.nulls)
    noise = run_synthetic("noise", seed=args.seed, nulls=args.nulls)

    # unconsented run must be blocked and score nothing
    unconsented_sig = replace(
        SyntheticSignalAdapter().extract(mode="structured", seed=args.seed), consent=False
    )
    unconsented = score_signal(unconsented_sig, nulls=args.nulls, seed=args.seed)

    checks: list[tuple[bool, str]] = [
        (structured.valid and noise.valid, "controls valid on both runs"),
        (structured.structure_present, "structured signal -> structure PRESENT"),
        (not noise.structure_present, "noise signal -> structure ABSENT"),
        (not structured.blocked, "consented structured run not blocked"),
        (unconsented.blocked and unconsented.to_dict()["structure_present"] is False,
         "unconsented run blocked + finding suppressed"),
        (all(r.boundary == SCIENTIFIC_BOUNDARY for r in (structured, noise, unconsented)),
         "scientific boundary present on every result"),
    ]
    ok = True
    for passed, label in checks:
        ok = ok and passed
        print(f"  {'✅' if passed else '❌'} {label}")
    print(f"  structured: A_p={structured.test_A_p} B_p={structured.test_B_p} "
          f"n_tones={structured.n_tones}")
    print(f"  noise:      A_p={noise.test_A_p} B_p={noise.test_B_p} n_tones={noise.n_tones}")
    return 0 if ok else 1


if __name__ == "__main__":  # pragma: no cover - manual entry point
    raise SystemExit(main())

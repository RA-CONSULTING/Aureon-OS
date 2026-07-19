#!/usr/bin/env python3
"""Detection-power / sensitivity sweep — the true-positive companion to the FPR audit.

`null_calibration.py` proves the family's detection rule does not **hallucinate** structure
(false-positive rate ≤ ALPHA). This module proves the other half of the operating
characteristic: the rule reliably **detects** real structure, and its power degrades
gracefully toward the false-positive floor as that structure dissolves into noise. Together
the two form the ROC picture that a pre-registered, falsifiable detector should exhibit.

What it measures (and why this way)
-----------------------------------
The canonical structured signal is the two-cluster, one-golden-ratio-apart, in-band tone set
the adapters and the engine's own positive control use. This audit progressively **jitters**
that signal with increasing Gaussian noise (`jitter_hz`) and, at each level, measures the
**detection power** — the fraction of trials the engine's own ``test_A``/``test_B`` still flag
``structure_present`` (`p_A < ALPHA AND p_B < ALPHA`). At zero jitter the clean structure is
detected almost always (power ≈ 1); as jitter grows past the engine's coherence tolerance the
clusters scatter and the φ ratios blur, so power collapses toward the false-positive rate. It
re-tunes nothing — it calls the engine's exact detection rule.

Scientific boundary (enforced, not decorative)
----------------------------------------------
Every signal is **synthetic, with no real subject**. This reports the statistical power of a
detection rule on a synthetic signal — it is **NOT** a claim about any person, and carries no
efficacy claim. Pure stdlib + numpy + engine; no network, no import-time side effects.
"""

from __future__ import annotations

import sys
import time
import uuid
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any, Final

import numpy as np

# --- engine import (repo root holds phenolic_fingerprint.py) ---------------
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import phenolic_fingerprint as engine  # noqa: E402

__all__ = [
    "POWER_BOUNDARY",
    "POWER_RUN_TOPIC",
    "POWER_TRACE_NAME",
    "DEFAULT_JITTER_HZ",
    "PowerLevel",
    "PowerReport",
    "detection_power",
    "write_power_report",
    "emit_power",
    "main",
]

POWER_RUN_TOPIC: Final[str] = "bio.power_analysis.run"
POWER_TRACE_NAME: Final[str] = "power_analysis"
_SOURCE: Final[str] = "power_analysis"

POWER_BOUNDARY: Final[str] = (
    "Synthetic detection-power audit: it measures how reliably the engine's detection rule "
    "flags a known structured signal as that signal is progressively degraded by noise - "
    "statistical power on a synthetic signal only, NOT a claim about any person, and no "
    "efficacy claim."
)

ALPHA: Final[float] = float(engine.ALPHA)
PHI: Final[float] = float(engine.PHI)

#: Jitter levels (Hz) swept from clean structure to dissolved-into-noise.
DEFAULT_JITTER_HZ: Final[tuple[float, ...]] = (0.0, 5.0, 10.0, 20.0, 40.0, 80.0)


def _rng(seed: int, tag: int) -> np.random.Generator:
    """Reproducible generator stream for a (seed, purpose) pair (engine idiom)."""
    return np.random.default_rng([int(seed), int(tag)])


def _structured_tones(jitter_hz: float, seed: int) -> np.ndarray:
    """The canonical structured tone set with reproducible Gaussian jitter added.

    Two tight triples one golden ratio apart, both in-band (the same shape the adapters and
    the engine's positive control use). ``jitter_hz`` is the standard deviation of the noise
    added to every tone; at 0 the structure is clean, and as it grows the within-cluster
    coherence and the φ ratios progressively break.
    """
    base = 1100.0
    centers = np.array([base, base * PHI])
    offsets = np.array([-4.0, 0.0, 4.0])
    tones = (centers[:, None] + offsets[None, :]).ravel()
    if jitter_hz > 0:
        tones = tones + _rng(seed, 7).normal(0.0, float(jitter_hz), size=tones.shape)
    return np.sort(tones)


def _structure_present(tones: np.ndarray, *, nulls: int, seed: int) -> bool:
    """The engine's exact detection rule: ``p_A < ALPHA and p_B < ALPHA`` on ``tones``."""
    arr = np.asarray(tones, dtype=float)
    if arr.size < 2:
        return False
    p_a = engine.test_A(arr, nulls=nulls, rng=_rng(seed, 1))
    p_b = engine.test_B(arr, nulls=nulls, rng=_rng(seed, 2))
    return bool(p_a < ALPHA and p_b < ALPHA)


@dataclass(frozen=True)
class PowerLevel:
    """Detection power at one signal-degradation (jitter) level."""

    jitter_hz: float
    trials: int
    detections: int
    power: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PowerReport:
    """The consolidated detection-power sweep."""

    levels: list[PowerLevel]
    n_levels: int
    trials: int
    nulls: int
    alpha: float
    clean_power: float
    degraded_power: float
    boundary: str = POWER_BOUNDARY
    out_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["levels"] = [lv.to_dict() for lv in self.levels]
        return d


def detection_power(
    *,
    jitter_levels: tuple[float, ...] = DEFAULT_JITTER_HZ,
    trials: int = 200,
    nulls: int = 200,
    seed0: int = 0,
) -> PowerReport:
    """Measure detection power of the engine's rule on the canonical structured signal.

    At each ``jitter_hz`` level, over ``trials`` seeds, the structured signal is jittered and
    scored with the engine's own two tests; ``power = detections / trials``. Verdicts use the
    pre-registered rule. ``clean_power`` is the power at the smallest jitter (strongest signal);
    ``degraded_power`` is the power at the largest jitter (weakest signal).
    """
    levels: list[PowerLevel] = []
    for jitter in jitter_levels:
        hits = 0
        for i in range(trials):
            s = seed0 + i
            if _structure_present(_structured_tones(jitter, s), nulls=nulls, seed=s):
                hits += 1
        levels.append(PowerLevel(
            jitter_hz=float(jitter), trials=trials, detections=hits,
            power=(hits / trials if trials else 0.0),
        ))
    clean = levels[0].power if levels else 0.0
    degraded = levels[-1].power if levels else 0.0
    return PowerReport(
        levels=levels,
        n_levels=len(levels),
        trials=trials,
        nulls=nulls,
        alpha=ALPHA,
        clean_power=clean,
        degraded_power=degraded,
    )


def write_power_report(
    report: PowerReport,
    out_md: str | Path,
    out_json: str | Path | None = None,
) -> PowerReport:
    """Write the power sweep as a durable evidence artifact (markdown [+ JSON]).

    Sibling to :func:`aureon.bio.null_calibration.write_calibration_report`: it *serializes* the
    report — every value copied verbatim from ``report.to_dict()``, nothing recomputed. No
    wall-clock timestamp in the body, so two runs at the same settings are byte-identical. The
    honest :data:`POWER_BOUNDARY` is printed verbatim. Returns the report with ``out_path`` set.
    """
    import json

    d = report.to_dict()
    lines: list[str] = []
    lines.append("# Detection power — sensitivity sweep")
    lines.append("")
    lines.append(
        "Generated by `python -m aureon.bio.power_analysis --report <OUT.md>` — the engine's own "
        "Test A + Test B are run on the canonical structured signal as it is progressively degraded "
        "by jitter; the table reports how reliably structure is still detected. Each verdict uses the "
        "pre-registered rule (`p_A < ALPHA and p_B < ALPHA`); nothing here is recomputed or hedged."
    )
    lines.append("")
    lines.append(f"> {POWER_BOUNDARY}")
    lines.append("")
    lines.append(
        f"**Clean-signal power {report.clean_power:.3f}** (jitter 0 Hz) collapsing to "
        f"**{report.degraded_power:.3f}** at {report.levels[-1].jitter_hz:g} Hz jitter, over "
        f"**{report.trials} trials** at **{report.nulls} nulls** (ALPHA = {report.alpha:g})."
    )
    lines.append("")
    lines.append("| jitter (Hz) | trials | detections | power |")
    lines.append("|---:|---:|---:|---:|")
    for lv in report.levels:
        lines.append(f"| {lv.jitter_hz:g} | {lv.trials} | {lv.detections} | {lv.power:.4f} |")
    lines.append("")
    md = "\n".join(lines) + "\n"

    out_md_path = Path(out_md)
    out_md_path.write_text(md, encoding="utf-8")

    if out_json is not None:
        Path(out_json).write_text(
            json.dumps(d, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )

    return replace(report, out_path=str(out_md_path))


def emit_power(report: PowerReport, *, bus: Any | None = None, trace: bool = True) -> dict[str, Any]:
    """Publish the power sweep to cognition; return its dict.

    Mirrors :func:`aureon.bio.null_calibration.emit_calibration` — a ``bio.power_analysis.run``
    Thought + a compact ``power_analysis`` bus_trace — so the metacognition monitor / Queen can
    sense that the family still detects real structure. Bus/trace failures are swallowed.
    """
    payload = report.to_dict()
    summary = {
        "n_levels": report.n_levels,
        "trials": report.trials,
        "nulls": report.nulls,
        "alpha": report.alpha,
        "clean_power": report.clean_power,
        "degraded_power": report.degraded_power,
        "boundary": POWER_BOUNDARY,
    }
    try:
        from aureon.core.aureon_thought_bus import Thought, get_thought_bus

        target = bus if bus is not None else get_thought_bus()
        target.publish(
            Thought(source=_SOURCE, topic=POWER_RUN_TOPIC, trace_id=uuid.uuid4().hex, payload=summary)
        )
    except Exception:  # noqa: BLE001 - emission is best-effort, never fatal
        pass

    if trace:
        try:
            from aureon.core.bus_trace import append_trace

            append_trace(POWER_TRACE_NAME, {
                "clean_power": report.clean_power,
                "degraded_power": report.degraded_power,
                "n_levels": report.n_levels,
                "boundary": POWER_BOUNDARY,
                "_ts": time.time(),
            })
        except Exception:  # noqa: BLE001 - trace mirror is best-effort
            pass

    return payload


def main(argv: list[str] | None = None) -> int:
    """CLI: run the detection-power sweep and print / write the curve."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Measure the detection rule's statistical power on a degraded synthetic signal."
    )
    parser.add_argument("--report", metavar="OUT.md", help="write the curve as a markdown evidence artifact")
    parser.add_argument("--report-json", metavar="OUT.json", help="also write the JSON record")
    parser.add_argument("--trials", type=int, default=200)
    parser.add_argument("--nulls", type=int, default=200)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--self-test", action="store_true",
                        help="assert clean-signal power is high and collapses under heavy jitter")
    args = parser.parse_args(argv)

    report = detection_power(trials=args.trials, nulls=args.nulls, seed0=args.seed)

    print("Detection power — sensitivity sweep (engine tests, unchanged)")
    print(f"  boundary: {POWER_BOUNDARY}")
    print(f"  {report.trials} trials · {report.nulls} nulls · ALPHA={report.alpha:g}")
    for lv in report.levels:
        print(f"  jitter {lv.jitter_hz:5g} Hz -> power {lv.power:.4f} ({lv.detections}/{lv.trials})")
    print(f"  clean power {report.clean_power:.3f} -> degraded power {report.degraded_power:.3f}")

    if args.report:
        rendered = write_power_report(report, args.report, args.report_json)
        print(f"  report written: {rendered.out_path}")

    if args.self_test:
        ok = report.clean_power >= 0.8 and report.degraded_power <= report.clean_power
        return 0 if ok else 1
    return 0


if __name__ == "__main__":  # pragma: no cover - manual entry point
    raise SystemExit(main())

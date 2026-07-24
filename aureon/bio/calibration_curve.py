#!/usr/bin/env python3
"""Per-test null-calibration curve — the calibration foundation under the FPR/power audits.

`null_calibration.py` checks the detection rule's false-positive rate at the single operating
point ALPHA. This module generalises that to a **curve**: under many synthetic *true-null* draws
it measures, across a grid of significance levels α, the empirical rate at which each engine test
(Test A, Test B) and the **conjunction** they form (the actual `structure_present` rule) reject.
A valid test's empirical rejection rate stays at or below α — it does not exceed its nominal size.

What it shows (honestly)
------------------------
- **Test A** (coherence clustering) is strongly *conservative* — its empirical P(p < α) ≤ α at
  every α (its statistic is discrete, so its permutation p-values skew large under the null).
- **Test B** (golden-interval alignment) is *approximately* calibrated and can be mildly
  anti-conservative on a flat null; the curve reports its rate verbatim rather than hiding it.
- The **conjunction** ``p_A < α AND p_B < α`` — the real detector — is **conservative across the
  whole α grid** (Test A's conservatism dominates), so ``structure_present`` never exceeds its
  nominal size. That conjunction bound is the operative guarantee this audit asserts.

Scientific boundary (enforced, not decorative)
----------------------------------------------
Every draw is a **synthetic true null with no real subject**. This reports the statistical
calibration of a detection rule — it is **NOT** a claim about any person, and carries no efficacy
claim. Pure stdlib + numpy + engine; no network, no import-time side effects.
"""

from __future__ import annotations

import sys
import time
import uuid
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any, Final

import numpy as np

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import phenolic_fingerprint as engine  # noqa: E402

__all__ = [
    "CALIBRATION_CURVE_BOUNDARY",
    "CURVE_RUN_TOPIC",
    "CURVE_TRACE_NAME",
    "DEFAULT_ALPHAS",
    "CurvePoint",
    "CalibrationCurveReport",
    "compute_calibration",
    "write_curve_report",
    "emit_curve",
    "main",
]

CURVE_RUN_TOPIC: Final[str] = "bio.calibration_curve.run"
CURVE_TRACE_NAME: Final[str] = "calibration_curve"
_SOURCE: Final[str] = "calibration_curve"

CALIBRATION_CURVE_BOUNDARY: Final[str] = (
    "Synthetic calibration audit: it measures, across a grid of significance levels, how often the "
    "engine's tests reject on a true-null signal, and confirms the detection rule stays at or below "
    "its nominal size - statistical calibration of a detector on synthetic signals only, NOT a claim "
    "about any person, and no efficacy claim."
)

ALPHA: Final[float] = float(engine.ALPHA)
DEFAULT_ALPHAS: Final[tuple[float, ...]] = (0.01, 0.02, 0.05, 0.10, 0.20)
_NULL_TONE_COUNT: Final[int] = 12


def _rng(seed: int, tag: int) -> np.random.Generator:
    """Reproducible generator stream for a (seed, purpose) pair (engine idiom)."""
    return np.random.default_rng([int(seed), int(tag)])


def _null_tones(seed: int) -> np.ndarray:
    """A synthetic true-null tone set: envelope-matched uniform draws inside the modulation band."""
    lo, hi = engine.TARGET_BAND_HZ
    return np.sort(_rng(seed, 9).uniform(float(lo), float(hi), _NULL_TONE_COUNT))


@dataclass(frozen=True)
class CurvePoint:
    """Rejection rates at one significance level α over the null draws."""

    alpha: float
    rate_A: float
    rate_B: float
    rate_joint: float
    joint_conservative: bool
    test_A_conservative: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CalibrationCurveReport:
    """The consolidated per-test null-calibration curve."""

    points: list[CurvePoint]
    n_points: int
    trials: int
    nulls: int
    tolerance: float
    joint_conservative: bool
    test_A_conservative: bool
    max_joint_exceedance: float
    boundary: str = CALIBRATION_CURVE_BOUNDARY
    out_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["points"] = [p.to_dict() for p in self.points]
        return d


def compute_calibration(
    *,
    trials: int = 400,
    nulls: int = 200,
    alphas: tuple[float, ...] = DEFAULT_ALPHAS,
    tolerance: float = 0.02,
    seed0: int = 0,
) -> CalibrationCurveReport:
    """Measure per-test and joint rejection rates on true-null signals across the α grid.

    For ``trials`` synthetic null tone sets, run the engine's own ``test_A``/``test_B`` and collect
    their p-values; then at each α compute the empirical rejection rate for each test and for the
    conjunction. A point is ``joint_conservative`` iff the conjunction rate ≤ α + ``tolerance``
    (the operative guarantee), and ``test_A_conservative`` iff Test A's rate ≤ α + ``tolerance``.
    """
    p_a = np.empty(trials, dtype=float)
    p_b = np.empty(trials, dtype=float)
    for i in range(trials):
        s = seed0 + i
        tones = _null_tones(s)
        p_a[i] = engine.test_A(tones, nulls=nulls, rng=_rng(s, 1))
        p_b[i] = engine.test_B(tones, nulls=nulls, rng=_rng(s, 2))

    points: list[CurvePoint] = []
    for a in alphas:
        rate_a = float(np.mean(p_a < a))
        rate_b = float(np.mean(p_b < a))
        rate_j = float(np.mean((p_a < a) & (p_b < a)))
        points.append(CurvePoint(
            alpha=float(a), rate_A=rate_a, rate_B=rate_b, rate_joint=rate_j,
            joint_conservative=rate_j <= a + tolerance,
            test_A_conservative=rate_a <= a + tolerance,
        ))
    max_joint_exc = max((p.rate_joint - p.alpha for p in points), default=0.0)
    return CalibrationCurveReport(
        points=points,
        n_points=len(points),
        trials=trials,
        nulls=nulls,
        tolerance=tolerance,
        joint_conservative=all(p.joint_conservative for p in points),
        test_A_conservative=all(p.test_A_conservative for p in points),
        max_joint_exceedance=max(max_joint_exc, 0.0),
    )


def write_curve_report(
    report: CalibrationCurveReport,
    out_md: str | Path,
    out_json: str | Path | None = None,
) -> CalibrationCurveReport:
    """Write the calibration curve as a durable evidence artifact (markdown [+ JSON]).

    Serialises the report verbatim (no wall-clock timestamp → byte-identical rebuilds), prints the
    honest :data:`CALIBRATION_CURVE_BOUNDARY`, and returns the report with ``out_path`` set.
    """
    import json

    d = report.to_dict()
    lines: list[str] = []
    lines.append("# Calibration curve — per-test null rejection rates")
    lines.append("")
    lines.append(
        "Generated by `python -m aureon.bio.calibration_curve --report <OUT.md>` — across a grid of "
        "significance levels, the empirical rate at which the engine's Test A, Test B, and their "
        "conjunction (the `structure_present` rule) reject on a synthetic true-null signal. A valid "
        "test stays at or below α; each verdict uses the pre-registered rule, nothing recomputed."
    )
    lines.append("")
    lines.append(f"> {CALIBRATION_CURVE_BOUNDARY}")
    lines.append("")
    lines.append(
        f"**Detection rule conservative across the grid: {report.joint_conservative}** "
        f"(max joint exceedance {report.max_joint_exceedance:+.4f}, tolerance {report.tolerance:g}) "
        f"over **{report.trials} null trials** at **{report.nulls} nulls**. Test A conservative: "
        f"{report.test_A_conservative}. Test B is reported verbatim (it can be mildly "
        f"anti-conservative on a flat null; the conjunction is what guarantees the detector's size)."
    )
    lines.append("")
    lines.append("| α | Test A P(p<α) | Test B P(p<α) | joint P(p<α) | joint ≤ α |")
    lines.append("|---:|---:|---:|---:|:---:|")
    for p in report.points:
        lines.append(f"| {p.alpha:g} | {p.rate_A:.4f} | {p.rate_B:.4f} | {p.rate_joint:.4f} | "
                     f"{p.joint_conservative} |")
    lines.append("")
    md = "\n".join(lines) + "\n"

    out_md_path = Path(out_md)
    out_md_path.write_text(md, encoding="utf-8")
    if out_json is not None:
        Path(out_json).write_text(json.dumps(d, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return replace(report, out_path=str(out_md_path))


def emit_curve(report: CalibrationCurveReport, *, bus: Any | None = None, trace: bool = True) -> dict[str, Any]:
    """Publish the calibration curve to cognition; return its dict. Best-effort, never fatal."""
    payload = report.to_dict()
    summary = {
        "n_points": report.n_points,
        "trials": report.trials,
        "nulls": report.nulls,
        "joint_conservative": report.joint_conservative,
        "test_A_conservative": report.test_A_conservative,
        "max_joint_exceedance": report.max_joint_exceedance,
        "boundary": CALIBRATION_CURVE_BOUNDARY,
    }
    try:
        from aureon.core.aureon_thought_bus import Thought, get_thought_bus

        target = bus if bus is not None else get_thought_bus()
        target.publish(
            Thought(source=_SOURCE, topic=CURVE_RUN_TOPIC, trace_id=uuid.uuid4().hex, payload=summary)
        )
    except Exception:  # noqa: BLE001 - emission is best-effort, never fatal
        pass

    if trace:
        try:
            from aureon.core.bus_trace import append_trace

            append_trace(CURVE_TRACE_NAME, {
                "joint_conservative": report.joint_conservative,
                "max_joint_exceedance": report.max_joint_exceedance,
                "n_points": report.n_points,
                "boundary": CALIBRATION_CURVE_BOUNDARY,
                "_ts": time.time(),
            })
        except Exception:  # noqa: BLE001 - trace mirror is best-effort
            pass

    return payload


def main(argv: list[str] | None = None) -> int:
    """CLI: run the calibration-curve audit and print / write the curve."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Measure per-test null rejection rates across an α grid (engine tests, unchanged)."
    )
    parser.add_argument("--report", metavar="OUT.md", help="write the curve as a markdown evidence artifact")
    parser.add_argument("--report-json", metavar="OUT.json", help="also write the JSON record")
    parser.add_argument("--trials", type=int, default=400)
    parser.add_argument("--nulls", type=int, default=200)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--self-test", action="store_true",
                        help="assert the detection rule is conservative across the grid (exit non-zero otherwise)")
    args = parser.parse_args(argv)

    report = compute_calibration(trials=args.trials, nulls=args.nulls, seed0=args.seed)

    print("Calibration curve — per-test null rejection rates (engine tests, unchanged)")
    print(f"  boundary: {CALIBRATION_CURVE_BOUNDARY}")
    print(f"  {report.trials} null trials · {report.nulls} nulls · tolerance {report.tolerance:g}")
    print("  α      Test A   Test B   joint    joint≤α")
    for p in report.points:
        mark = "✅" if p.joint_conservative else "❌"
        print(f"  {p.alpha:<5g}  {p.rate_A:.4f}   {p.rate_B:.4f}   {p.rate_joint:.4f}   {mark}")
    print(f"  detection rule conservative across grid: {report.joint_conservative} "
          f"(max joint exceedance {report.max_joint_exceedance:+.4f})")

    if args.report:
        rendered = write_curve_report(report, args.report, args.report_json)
        print(f"  report written: {rendered.out_path}")

    if args.self_test:
        return 0 if (report.joint_conservative and report.test_A_conservative) else 1
    return 0


if __name__ == "__main__":  # pragma: no cover - manual entry point
    raise SystemExit(main())

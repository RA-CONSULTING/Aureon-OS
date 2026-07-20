#!/usr/bin/env python3
"""Multiplicity / family-wise error-rate (FWER) audit — the many-lanes-at-once check.

The FPR audit (b29) and calibration curve (b31) validate a *single* lane. But the φ Celestial
Observatory runs ~16 lanes and the human-signal family runs several adapters **simultaneously**;
when many tests run at once, the probability that **at least one** falsely fires — the family-wise
error rate (FWER) — grows roughly as ``1-(1-r)^k`` in the number of simultaneous lanes ``k``.

This audit measures the FWER as a function of ``k`` on synthetic true-null lanes and shows two
things honestly:

1. Because the detector is the **conjunction** ``p_A < α AND p_B < α``, its per-lane false-positive
   rate is ``r ≈ ALPHA² ≈ 0.0025`` — so ``k·r ≤ ALPHA`` holds for ``k ≤ 1/ALPHA ≈ 20``. The
   conjunction gives **built-in multiplicity headroom** for the current lane counts; the audit
   reports the ``k`` (if any within the sweep) at which the *uncorrected* FWER crosses ALPHA.
2. A **Bonferroni** per-lane threshold (``α/k``) controls FWER ``≤ α`` at **every** ``k`` — the
   correction restores control beyond the built-in headroom.

Scientific boundary (enforced, not decorative)
----------------------------------------------
Every lane is a **synthetic true null with no real subject**. This reports the statistical
family-wise error rate of a detector — it is **NOT** a claim about any person, and carries no
efficacy claim. Pure stdlib + numpy + engine; no network, no import-time side effects. The engine's
tests are called unchanged; only the *decision threshold* (α vs α/k) is varied at the analysis layer.
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
    "MULTIPLICITY_BOUNDARY",
    "MULT_RUN_TOPIC",
    "MULT_TRACE_NAME",
    "DEFAULT_KS",
    "KPoint",
    "MultiplicityReport",
    "compute_multiplicity",
    "write_multiplicity_report",
    "emit_multiplicity",
    "main",
]

MULT_RUN_TOPIC: Final[str] = "bio.multiplicity.run"
MULT_TRACE_NAME: Final[str] = "multiplicity"
_SOURCE: Final[str] = "multiplicity"

MULTIPLICITY_BOUNDARY: Final[str] = (
    "Synthetic multiplicity audit: it measures the family-wise false-positive rate of the "
    "detection rule when many lanes are tested at once, and confirms a Bonferroni threshold keeps "
    "it at or below the nominal level - statistical error control of a detector on synthetic "
    "signals only, NOT a claim about any person, and no efficacy claim."
)

ALPHA: Final[float] = float(engine.ALPHA)
DEFAULT_KS: Final[tuple[int, ...]] = (1, 2, 4, 8, 16, 32)
_NULL_TONE_COUNT: Final[int] = 12
_LANE_STRIDE: Final[int] = 1_000_003  # keeps per-(trial,lane) seeds disjoint & reproducible


def _rng(seed: int, tag: int) -> np.random.Generator:
    """Reproducible generator stream for a (seed, purpose) pair (engine idiom)."""
    return np.random.default_rng([int(seed), int(tag)])


def _null_lane_pvals(seed: int, *, nulls: int) -> tuple[float, float]:
    """One synthetic true-null lane → its (Test A, Test B) p-values through the engine."""
    lo, hi = engine.TARGET_BAND_HZ
    tones = np.sort(_rng(seed, 9).uniform(float(lo), float(hi), _NULL_TONE_COUNT))
    p_a = float(engine.test_A(tones, nulls=nulls, rng=_rng(seed, 1)))
    p_b = float(engine.test_B(tones, nulls=nulls, rng=_rng(seed, 2)))
    return p_a, p_b


@dataclass(frozen=True)
class KPoint:
    """Family-wise rates when ``k`` lanes are tested simultaneously."""

    k: int
    per_lane_rate: float
    fwer_uncorrected: float
    fwer_bonferroni: float
    bonferroni_controls: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class MultiplicityReport:
    """The consolidated multiplicity / FWER audit."""

    points: list[KPoint]
    n_points: int
    trials: int
    nulls: int
    alpha: float
    tolerance: float
    bonferroni_controls_all: bool
    k_uncorrected_crosses_alpha: int | None
    boundary: str = MULTIPLICITY_BOUNDARY
    out_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["points"] = [p.to_dict() for p in self.points]
        return d


def compute_multiplicity(
    *,
    trials: int = 200,
    nulls: int = 100,
    ks: tuple[int, ...] = DEFAULT_KS,
    alpha: float = ALPHA,
    tolerance: float = 0.02,
    seed0: int = 0,
) -> MultiplicityReport:
    """Measure family-wise false-positive rates across simultaneous-lane counts ``ks``.

    A ``(trials, k_max)`` matrix of independent synthetic null-lane p-values is generated in a
    single engine pass, then every ``k`` is read off by slicing. For each ``k`` the audit reports
    the mean per-lane rate (≈ ALPHA²), the uncorrected FWER (any of ``k`` lanes fires at α), and the
    Bonferroni FWER (any fires at α/k); ``bonferroni_controls`` iff the latter ≤ α + ``tolerance``.
    """
    k_max = max(ks)
    p_a = np.empty((trials, k_max), dtype=float)
    p_b = np.empty((trials, k_max), dtype=float)
    for i in range(trials):
        for j in range(k_max):
            lane_seed = seed0 * _LANE_STRIDE + i * k_max + j
            p_a[i, j], p_b[i, j] = _null_lane_pvals(lane_seed, nulls=nulls)

    fires_a = p_a < alpha
    fires = fires_a & (p_b < alpha)  # (trials, k_max) — per-lane detection at α

    points: list[KPoint] = []
    crosses: int | None = None
    for k in ks:
        sub = fires[:, :k]
        per_lane = float(np.mean(fires[:, :k]))
        fwer_unc = float(np.mean(sub.any(axis=1)))
        thr = alpha / k
        fires_bonf = (p_a[:, :k] < thr) & (p_b[:, :k] < thr)
        fwer_bonf = float(np.mean(fires_bonf.any(axis=1)))
        points.append(KPoint(
            k=int(k), per_lane_rate=per_lane, fwer_uncorrected=fwer_unc,
            fwer_bonferroni=fwer_bonf, bonferroni_controls=fwer_bonf <= alpha + tolerance,
        ))
        if crosses is None and fwer_unc > alpha:
            crosses = int(k)

    return MultiplicityReport(
        points=points,
        n_points=len(points),
        trials=trials,
        nulls=nulls,
        alpha=alpha,
        tolerance=tolerance,
        bonferroni_controls_all=all(p.bonferroni_controls for p in points),
        k_uncorrected_crosses_alpha=crosses,
    )


def write_multiplicity_report(
    report: MultiplicityReport,
    out_md: str | Path,
    out_json: str | Path | None = None,
) -> MultiplicityReport:
    """Write the multiplicity audit as a durable evidence artifact (markdown [+ JSON])."""
    import json

    d = report.to_dict()
    cross = report.k_uncorrected_crosses_alpha
    cross_txt = f"k={cross}" if cross is not None else "not within the swept range"
    lines: list[str] = []
    lines.append("# Multiplicity — family-wise error rate vs simultaneous lanes")
    lines.append("")
    lines.append(
        "Generated by `python -m aureon.bio.multiplicity --report <OUT.md>` — the family-wise "
        "false-positive rate (probability that at least one of k simultaneous true-null lanes fires) "
        "for the detection rule, uncorrected and under a Bonferroni α/k threshold. Each lane uses the "
        "engine's own Test A + Test B; only the decision threshold is varied."
    )
    lines.append("")
    lines.append(f"> {MULTIPLICITY_BOUNDARY}")
    lines.append("")
    lines.append(
        f"**Bonferroni controls FWER ≤ α at every k: {report.bonferroni_controls_all}** "
        f"(α = {report.alpha:g}, tolerance {report.tolerance:g}) over **{report.trials} trials** at "
        f"**{report.nulls} nulls**. Uncorrected FWER crosses α at: {cross_txt} "
        f"(the conjunction's ≈α² per-lane rate gives headroom to about k ≈ {int(round(1/report.alpha))})."
    )
    lines.append("")
    lines.append("| k lanes | per-lane rate | uncorrected FWER | Bonferroni FWER (α/k) | ≤ α |")
    lines.append("|---:|---:|---:|---:|:---:|")
    for p in report.points:
        lines.append(f"| {p.k} | {p.per_lane_rate:.4f} | {p.fwer_uncorrected:.4f} | "
                     f"{p.fwer_bonferroni:.4f} | {p.bonferroni_controls} |")
    lines.append("")
    md = "\n".join(lines) + "\n"

    out_md_path = Path(out_md)
    out_md_path.write_text(md, encoding="utf-8")
    if out_json is not None:
        Path(out_json).write_text(json.dumps(d, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return replace(report, out_path=str(out_md_path))


def emit_multiplicity(report: MultiplicityReport, *, bus: Any | None = None, trace: bool = True) -> dict[str, Any]:
    """Publish the multiplicity audit to cognition; return its dict. Best-effort, never fatal."""
    payload = report.to_dict()
    summary = {
        "n_points": report.n_points,
        "trials": report.trials,
        "nulls": report.nulls,
        "alpha": report.alpha,
        "bonferroni_controls_all": report.bonferroni_controls_all,
        "k_uncorrected_crosses_alpha": report.k_uncorrected_crosses_alpha,
        "boundary": MULTIPLICITY_BOUNDARY,
    }
    try:
        from aureon.core.aureon_thought_bus import Thought, get_thought_bus

        target = bus if bus is not None else get_thought_bus()
        target.publish(
            Thought(source=_SOURCE, topic=MULT_RUN_TOPIC, trace_id=uuid.uuid4().hex, payload=summary)
        )
    except Exception:  # noqa: BLE001 - emission is best-effort, never fatal
        pass

    if trace:
        try:
            from aureon.core.bus_trace import append_trace

            append_trace(MULT_TRACE_NAME, {
                "bonferroni_controls_all": report.bonferroni_controls_all,
                "k_uncorrected_crosses_alpha": report.k_uncorrected_crosses_alpha,
                "n_points": report.n_points,
                "boundary": MULTIPLICITY_BOUNDARY,
                "_ts": time.time(),
            })
        except Exception:  # noqa: BLE001 - trace mirror is best-effort
            pass

    return payload


def main(argv: list[str] | None = None) -> int:
    """CLI: run the multiplicity / FWER audit and print / write the table."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Audit family-wise false-positive rate vs simultaneous lanes (engine tests, unchanged)."
    )
    parser.add_argument("--report", metavar="OUT.md", help="write the table as a markdown evidence artifact")
    parser.add_argument("--report-json", metavar="OUT.json", help="also write the JSON record")
    parser.add_argument("--trials", type=int, default=200)
    parser.add_argument("--nulls", type=int, default=100)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--self-test", action="store_true",
                        help="assert Bonferroni controls FWER ≤ α at every k (exit non-zero otherwise)")
    args = parser.parse_args(argv)

    report = compute_multiplicity(trials=args.trials, nulls=args.nulls, seed0=args.seed)

    print("Multiplicity — family-wise error rate vs simultaneous lanes (engine tests, unchanged)")
    print(f"  boundary: {MULTIPLICITY_BOUNDARY}")
    print(f"  {report.trials} trials · {report.nulls} nulls · α={report.alpha:g}")
    print("  k     per-lane  uncorr.FWER  Bonf.FWER  ≤α")
    for p in report.points:
        mark = "✅" if p.bonferroni_controls else "❌"
        print(f"  {p.k:<4d}  {p.per_lane_rate:.4f}    {p.fwer_uncorrected:.4f}      "
              f"{p.fwer_bonferroni:.4f}     {mark}")
    cross = report.k_uncorrected_crosses_alpha
    print(f"  Bonferroni controls at every k: {report.bonferroni_controls_all} · "
          f"uncorrected crosses α at k={cross if cross is not None else '—'}")

    if args.report:
        rendered = write_multiplicity_report(report, args.report, args.report_json)
        print(f"  report written: {rendered.out_path}")

    if args.self_test:
        return 0 if report.bonferroni_controls_all else 1
    return 0


if __name__ == "__main__":  # pragma: no cover - manual entry point
    raise SystemExit(main())

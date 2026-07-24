#!/usr/bin/env python3
"""False Discovery Rate (Benjamini–Hochberg) audit — the many-lanes, power-preserving check.

The multiplicity audit (b32) controls the probability of **any** false positive across ``k``
simultaneous lanes with a **Bonferroni** ``α/k`` threshold. Bonferroni is safe but famously
**conservative** — to guard against a single false alarm it throws away real detections. The standard,
less-conservative complement is **False Discovery Rate (FDR) control via Benjamini–Hochberg (BH)**,
which instead bounds the expected **proportion** of false positives among the lanes it flags.

This audit runs many synthetic **families** of lanes — a mix of true-null lanes and true-signal lanes
— through the engine's own Test A + Test B (unchanged). Each lane's conjunction p-value is
``p = max(p_A, p_B)`` (the detector *is* ``p_A < α AND p_B < α``, i.e. ``max(p_A, p_B) < α``). It then
compares three decision rules honestly:

* **uncorrected** — reject at ``α`` (most lenient; no multiplicity control),
* **Bonferroni** — reject at ``α/m`` (controls FWER; conservative),
* **Benjamini–Hochberg** — the step-up procedure at level ``q``.

and shows two things:

1. **BH controls the FDR** ``≤ q`` on the mixed families.
2. With ``q = α``, BH's rejection set always **contains** Bonferroni's, so BH is uniformly at least as
   powerful — it recovers strictly more true detections at controlled error. This is the principled way
   to buy back the power Bonferroni gives up when many lanes run at once.

Scientific boundary (enforced, not decorative)
----------------------------------------------
Every lane is **synthetic** — a true null with no real subject, or a synthetic structured signal. This
reports the statistical false-discovery rate and power of a detector; it is **NOT** a claim about any
person, and carries no efficacy claim. Pure stdlib + numpy + engine; no network, no import-time side
effects. The engine's tests are called unchanged; only the *decision procedure* (α vs α/m vs BH) is
varied at the analysis layer.
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
from aureon.bio.power_analysis import _structured_tones  # noqa: E402

__all__ = [
    "FALSE_DISCOVERY_BOUNDARY",
    "FDR_RUN_TOPIC",
    "FDR_TRACE_NAME",
    "DEFAULT_Q",
    "MethodOutcome",
    "FalseDiscoveryReport",
    "compute_false_discovery",
    "write_false_discovery_report",
    "emit_false_discovery",
    "main",
]

FDR_RUN_TOPIC: Final[str] = "bio.false_discovery.run"
FDR_TRACE_NAME: Final[str] = "false_discovery"
_SOURCE: Final[str] = "false_discovery"

FALSE_DISCOVERY_BOUNDARY: Final[str] = (
    "Synthetic false-discovery-rate audit: it measures the expected proportion of false positives "
    "among a detector's flagged lanes across many synthetic families, and confirms a Benjamini-"
    "Hochberg threshold keeps that proportion at or below the nominal level while recovering more "
    "true detections than Bonferroni - statistical error control of a detector on synthetic signals "
    "only, NOT a claim about any person, and no efficacy claim."
)

ALPHA: Final[float] = float(engine.ALPHA)
DEFAULT_Q: Final[float] = ALPHA  # FDR level; = α so BH's rejection set always contains Bonferroni's
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


def _signal_lane_pvals(seed: int, *, nulls: int, jitter_hz: float) -> tuple[float, float]:
    """One synthetic true-signal lane (structured tones + jitter) → its (Test A, Test B) p-values.

    ``jitter_hz`` is graded across the signal lanes (see ``compute_false_discovery``) so the family
    holds signals of varying strength — the setting in which the correction choice actually matters.
    """
    tones = _structured_tones(jitter_hz, seed)
    p_a = float(engine.test_A(tones, nulls=nulls, rng=_rng(seed, 1)))
    p_b = float(engine.test_B(tones, nulls=nulls, rng=_rng(seed, 2)))
    return p_a, p_b


def _bh_reject(pvals: np.ndarray, q: float) -> np.ndarray:
    """Benjamini–Hochberg step-up rejection mask over ``pvals`` at FDR level ``q``.

    Sort ascending, find the largest rank ``i`` (1-indexed) with ``p_(i) ≤ (i/m)·q``, and reject every
    lane whose p-value is ``≤`` that threshold. Returns a boolean mask aligned to the input order.
    """
    p = np.asarray(pvals, dtype=float)
    m = p.size
    if m == 0:
        return np.zeros(0, dtype=bool)
    order = np.argsort(p, kind="stable")
    ranked = p[order]
    thresholds = (np.arange(1, m + 1) / m) * q
    passing = ranked <= thresholds
    if not passing.any():
        return np.zeros(m, dtype=bool)
    k_star = np.max(np.nonzero(passing)[0])  # 0-indexed largest passing rank
    cutoff = ranked[k_star]
    return p <= cutoff


@dataclass(frozen=True)
class MethodOutcome:
    """FDR and power of one decision rule averaged over the synthetic families."""

    name: str
    fdr: float
    power: float
    mean_rejections: float
    controls_fdr: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class FalseDiscoveryReport:
    """The consolidated false-discovery-rate / power audit across three decision rules."""

    methods: list[MethodOutcome]
    n_methods: int
    trials: int
    nulls: int
    m_lanes: int
    m_null: int
    m_signal: int
    jitter_lo: float
    jitter_hi: float
    q: float
    alpha: float
    tolerance: float
    bh_controls_fdr: bool
    bh_dominates_bonferroni: bool
    boundary: str = FALSE_DISCOVERY_BOUNDARY
    out_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["methods"] = [m.to_dict() for m in self.methods]
        return d


def compute_false_discovery(
    *,
    trials: int = 60,
    nulls: int = 600,
    m_null: int = 10,
    m_signal: int = 10,
    jitter_lo: float = 5.0,
    jitter_hi: float = 45.0,
    q: float = DEFAULT_Q,
    alpha: float = ALPHA,
    tolerance: float = 0.03,
    seed0: int = 0,
) -> FalseDiscoveryReport:
    """Measure FDR and power of the uncorrected / Bonferroni / Benjamini–Hochberg rules.

    Each of ``trials`` families holds ``m_null`` synthetic true-null lanes and ``m_signal`` synthetic
    true-signal lanes; the signal lanes are structured tones degraded by jitter **graded** from
    ``jitter_lo`` to ``jitter_hi`` (a spread of strong→weak signals — the regime where the correction
    choice matters). Every lane's p-value is the conjunction ``max(p_A, p_B)``. ``nulls`` is chosen so
    the permutation p-value floor ``1/(nulls+1)`` sits below the Bonferroni threshold ``α/m``, i.e. the
    strict corrections are actually reachable. For each rule the audit reports the mean false-discovery
    proportion (``FDR``), the mean true-positive rate (``power``), and the mean number of rejections.
    BH is asserted to control the FDR ``≤ q + tolerance`` and, with ``q = α``, to reject a superset of
    what Bonferroni rejects (``bh_dominates_bonferroni``), verified per family.
    """
    m = m_null + m_signal
    is_signal = np.zeros(m, dtype=bool)
    is_signal[m_null:] = True
    signal_jitters = (
        np.linspace(jitter_lo, jitter_hi, m_signal) if m_signal > 1
        else np.array([jitter_lo], dtype=float)
    )

    # Accumulators per method: (false rejections proportion, true-positive rate, rejection count).
    names = ("uncorrected", "bonferroni", "benjamini_hochberg")
    fdp_sum = dict.fromkeys(names, 0.0)
    tpr_sum = dict.fromkeys(names, 0.0)
    rej_sum = dict.fromkeys(names, 0.0)
    bh_dominates = True

    for t in range(trials):
        p = np.empty(m, dtype=float)
        for j in range(m):
            lane_seed = seed0 * _LANE_STRIDE + t * m + j
            if is_signal[j]:
                jit = float(signal_jitters[j - m_null])
                p_a, p_b = _signal_lane_pvals(lane_seed, nulls=nulls, jitter_hz=jit)
            else:
                p_a, p_b = _null_lane_pvals(lane_seed, nulls=nulls)
            p[j] = max(p_a, p_b)  # the conjunction detector's per-lane p-value

        masks = {
            "uncorrected": p < alpha,
            "bonferroni": p < (alpha / m),
            "benjamini_hochberg": _bh_reject(p, q),
        }
        if not np.all(masks["bonferroni"] <= masks["benjamini_hochberg"]):
            bh_dominates = False

        for name, mask in masks.items():
            v = int(np.count_nonzero(mask & ~is_signal))  # false rejections
            s = int(np.count_nonzero(mask & is_signal))   # true rejections
            r = v + s
            fdp_sum[name] += v / max(1, r)
            tpr_sum[name] += (s / m_signal) if m_signal else 0.0
            rej_sum[name] += r

    methods: list[MethodOutcome] = []
    for name in names:
        fdr = fdp_sum[name] / trials
        methods.append(MethodOutcome(
            name=name,
            fdr=fdr,
            power=tpr_sum[name] / trials,
            mean_rejections=rej_sum[name] / trials,
            controls_fdr=fdr <= q + tolerance,
        ))

    bh = next(mm for mm in methods if mm.name == "benjamini_hochberg")

    return FalseDiscoveryReport(
        methods=methods,
        n_methods=len(methods),
        trials=trials,
        nulls=nulls,
        m_lanes=m,
        m_null=m_null,
        m_signal=m_signal,
        jitter_lo=jitter_lo,
        jitter_hi=jitter_hi,
        q=q,
        alpha=alpha,
        tolerance=tolerance,
        bh_controls_fdr=bh.controls_fdr,
        bh_dominates_bonferroni=bh_dominates,
    )


def write_false_discovery_report(
    report: FalseDiscoveryReport,
    out_md: str | Path,
    out_json: str | Path | None = None,
) -> FalseDiscoveryReport:
    """Write the false-discovery audit as a durable evidence artifact (markdown [+ JSON])."""
    import json

    d = report.to_dict()
    lines: list[str] = []
    lines.append("# False discovery rate — Benjamini–Hochberg vs Bonferroni vs uncorrected")
    lines.append("")
    lines.append(
        "Generated by `python -m aureon.bio.false_discovery --report <OUT.md>` — the false-discovery "
        "rate (expected proportion of false positives among flagged lanes) and detection power for "
        "three decision rules, over many synthetic families mixing true-null and true-signal lanes. "
        "Each lane's p-value is the conjunction `max(p_A, p_B)` from the engine's own Test A + Test B; "
        "only the decision procedure is varied."
    )
    lines.append("")
    lines.append(f"> {FALSE_DISCOVERY_BOUNDARY}")
    lines.append("")
    lines.append(
        f"**Benjamini–Hochberg controls FDR ≤ q: {report.bh_controls_fdr}** and **rejects a superset "
        f"of Bonferroni: {report.bh_dominates_bonferroni}** "
        f"(q = {report.q:g}, α = {report.alpha:g}, tolerance {report.tolerance:g}) over "
        f"**{report.trials} families** of {report.m_lanes} lanes "
        f"({report.m_null} null + {report.m_signal} signal at {report.jitter_lo:g}–{report.jitter_hi:g} Hz "
        f"graded jitter), {report.nulls} nulls per test. BH buys back the power Bonferroni gives up while holding the "
        f"false-discovery rate at the nominal level."
    )
    lines.append("")
    lines.append("| method | mean rejections | power (TPR) | FDR | controls FDR ≤ q |")
    lines.append("|:---|---:|---:|---:|:---:|")
    for mm in report.methods:
        lines.append(f"| {mm.name} | {mm.mean_rejections:.3f} | {mm.power:.4f} | "
                     f"{mm.fdr:.4f} | {mm.controls_fdr} |")
    lines.append("")
    md = "\n".join(lines) + "\n"

    out_md_path = Path(out_md)
    out_md_path.write_text(md, encoding="utf-8")
    if out_json is not None:
        Path(out_json).write_text(json.dumps(d, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return replace(report, out_path=str(out_md_path))


def emit_false_discovery(
    report: FalseDiscoveryReport, *, bus: Any | None = None, trace: bool = True
) -> dict[str, Any]:
    """Publish the false-discovery audit to cognition; return its dict. Best-effort, never fatal."""
    payload = report.to_dict()
    bh = next((m for m in report.methods if m.name == "benjamini_hochberg"), None)
    bonf = next((m for m in report.methods if m.name == "bonferroni"), None)
    summary = {
        "n_methods": report.n_methods,
        "trials": report.trials,
        "q": report.q,
        "alpha": report.alpha,
        "bh_controls_fdr": report.bh_controls_fdr,
        "bh_dominates_bonferroni": report.bh_dominates_bonferroni,
        "bh_power": bh.power if bh else None,
        "bonferroni_power": bonf.power if bonf else None,
        "boundary": FALSE_DISCOVERY_BOUNDARY,
    }
    try:
        from aureon.core.aureon_thought_bus import Thought, get_thought_bus

        target = bus if bus is not None else get_thought_bus()
        target.publish(
            Thought(source=_SOURCE, topic=FDR_RUN_TOPIC, trace_id=uuid.uuid4().hex, payload=summary)
        )
    except Exception:  # noqa: BLE001 - emission is best-effort, never fatal
        pass

    if trace:
        try:
            from aureon.core.bus_trace import append_trace

            append_trace(FDR_TRACE_NAME, {
                "bh_controls_fdr": report.bh_controls_fdr,
                "bh_dominates_bonferroni": report.bh_dominates_bonferroni,
                "n_methods": report.n_methods,
                "boundary": FALSE_DISCOVERY_BOUNDARY,
                "_ts": time.time(),
            })
        except Exception:  # noqa: BLE001 - trace mirror is best-effort
            pass

    return payload


def main(argv: list[str] | None = None) -> int:
    """CLI: run the false-discovery / power audit and print / write the table."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Audit false-discovery rate + power for uncorrected/Bonferroni/BH (engine tests, unchanged)."
    )
    parser.add_argument("--report", metavar="OUT.md", help="write the table as a markdown evidence artifact")
    parser.add_argument("--report-json", metavar="OUT.json", help="also write the JSON record")
    parser.add_argument("--trials", type=int, default=60)
    parser.add_argument("--nulls", type=int, default=600)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--self-test", action="store_true",
                        help="assert BH controls FDR ≤ q and rejects a superset of Bonferroni (exit non-zero otherwise)")
    args = parser.parse_args(argv)

    report = compute_false_discovery(trials=args.trials, nulls=args.nulls, seed0=args.seed)

    print("False discovery rate — uncorrected vs Bonferroni vs Benjamini–Hochberg (engine tests, unchanged)")
    print(f"  boundary: {FALSE_DISCOVERY_BOUNDARY}")
    print(f"  {report.trials} families · {report.m_lanes} lanes "
          f"({report.m_null} null + {report.m_signal} signal @ {report.jitter_lo:g}–{report.jitter_hi:g} Hz) · "
          f"{report.nulls} nulls · q={report.q:g}")
    print("  method               mean_rej   power    FDR      ≤q")
    for mm in report.methods:
        mark = "✅" if mm.controls_fdr else "❌"
        print(f"  {mm.name:<19s}  {mm.mean_rejections:6.3f}   {mm.power:.4f}  {mm.fdr:.4f}   {mark}")
    print(f"  BH controls FDR ≤ q: {report.bh_controls_fdr} · "
          f"BH ⊇ Bonferroni: {report.bh_dominates_bonferroni}")

    if args.report:
        rendered = write_false_discovery_report(report, args.report, args.report_json)
        print(f"  report written: {rendered.out_path}")

    if args.self_test:
        return 0 if (report.bh_controls_fdr and report.bh_dominates_bonferroni) else 1
    return 0


if __name__ == "__main__":  # pragma: no cover - manual entry point
    raise SystemExit(main())

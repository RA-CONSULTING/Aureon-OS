#!/usr/bin/env python3
"""Volatility Sentinel benchmark — measured detection performance, labeled synthetic.

The sentinel (P2) predicts high-volatility regimes from four measured factors and
vetoes entries at ``VOL_RISK_BLOCK`` (P4). This benchmark measures what that
detector actually does on a SEEDED, LABELED synthetic regime library — synthetic
by design and said so on every artifact, never presented as market data — plus an
optional replay of the real ``state/hnc_live_trace.jsonl`` Λ(t) series.

Metrics (all measured, none invented)
-------------------------------------
* ``detection_latency_samples`` — samples from the stress-regime onset until the
  sentinel's risk first crosses ``VOL_RISK_BLOCK``. Standalone, only the EWMA
  factor is live (the other three are honestly dark and named as blockers), so
  this is the expansion-detector's reaction time.
* ``protected_samples`` — stress samples remaining AFTER detection: the exposure
  the veto would have shielded. The pinned regression ``protected_samples >= 0``
  means the regime was flagged while it was still live, never after the fact.
* ``fpr_calm`` — fraction of post-warm-up assessments in a pure-calm regime at or
  above ``VOL_RISK_BLOCK``. Pinned ``<= 0.20`` (canonical seeds measure 0.0).
* per-factor attribution at the detection sample (risk, weight, status).

Deterministic by construction: ``random.Random(seed)`` price paths, integer
timestamps, no wall-clock dependence in the risk math — artifacts are
byte-identical on re-run. CLI: ``python -m aureon.analytics.volatility_sentinel_benchmark
[--out PATH] [--replay [TRACE_PATH]]``.
"""

from __future__ import annotations

import json
import math
import random
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from aureon.intelligence.volatility_sentinel import (
    VOL_RISK_BLOCK,
    EwmaVolEstimator,
    VolatilitySentinel,
)

__all__ = [
    "BENCHMARK_BOUNDARY",
    "RegimeSpec",
    "RegimeResult",
    "SentinelBenchmarkReport",
    "canonical_regimes",
    "run_regime",
    "run_calm_fpr",
    "replay_trace",
    "compute_benchmark",
    "write_benchmark_report",
    "main",
]

BENCHMARK_BOUNDARY = (
    "Measured detection benchmark on a SEEDED SYNTHETIC regime library (labeled synthetic on every "
    "artifact) plus an optional replay of the real hnc_live_trace Lambda(t) series. It measures the "
    "sentinel's reaction time, shielded exposure, and calm-regime false-positive rate; it fabricates "
    "no market data, arms nothing, and is NOT a claim about any person."
)

_SYMBOL = "SYN/USD"


@dataclass(frozen=True)
class RegimeSpec:
    """One labeled synthetic regime: calm baseline then a volatility expansion."""

    name: str
    seed: int
    n_calm: int
    n_stress: int
    calm_sigma: float
    stress_sigma: float
    label: str = "synthetic"


@dataclass(frozen=True)
class RegimeResult:
    """Measured sentinel behaviour on one synthetic regime."""

    name: str
    label: str
    detected: bool
    detection_latency_samples: int | None
    protected_samples: int | None
    risk_at_detection: float | None
    factors_at_detection: list[dict[str, Any]] = field(default_factory=list)
    blockers_at_detection: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SentinelBenchmarkReport:
    """The consolidated benchmark: regimes, calm FPR, optional real-trace replay."""

    regimes: list[dict[str, Any]]
    all_detected: bool
    min_protected_samples: int | None
    fpr_calm: float
    calm_assessments: int
    replay: dict[str, Any]
    risk_block: float
    boundary: str = BENCHMARK_BOUNDARY
    out_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def canonical_regimes() -> tuple[RegimeSpec, ...]:
    """The pinned regime library. Seeds are part of the regression contract."""
    return (
        RegimeSpec("crypto_flash_expansion", seed=7, n_calm=400, n_stress=120,
                   calm_sigma=0.001, stress_sigma=0.012),
        RegimeSpec("slow_grind_to_stress", seed=21, n_calm=400, n_stress=160,
                   calm_sigma=0.0015, stress_sigma=0.009),
        RegimeSpec("violent_regime_break", seed=42, n_calm=400, n_stress=100,
                   calm_sigma=0.0008, stress_sigma=0.016),
    )


def _walk(rng: random.Random, price: float, sigma: float) -> float:
    return price * math.exp(rng.gauss(0.0, sigma))


def run_regime(spec: RegimeSpec) -> RegimeResult:
    """Drive a fresh sentinel through one labeled regime and measure detection."""
    rng = random.Random(spec.seed)
    sentinel = VolatilitySentinel(symbols=[_SYMBOL])
    price = 100.0

    for i in range(spec.n_calm):
        price = _walk(rng, price, spec.calm_sigma)
        sentinel.ingest_price(_SYMBOL, price, ts=float(i))

    for j in range(spec.n_stress):
        i = spec.n_calm + j
        price = _walk(rng, price, spec.stress_sigma)
        sentinel.ingest_price(_SYMBOL, price, ts=float(i))
        a = sentinel.assess(_SYMBOL)
        if a.status == "ok" and a.volatility_risk is not None \
                and a.volatility_risk >= VOL_RISK_BLOCK:
            return RegimeResult(
                name=spec.name,
                label=spec.label,
                detected=True,
                detection_latency_samples=j,
                protected_samples=spec.n_stress - j,
                risk_at_detection=round(float(a.volatility_risk), 6),
                factors_at_detection=[
                    {"name": f.name, "risk": (round(float(f.risk), 6) if f.risk is not None else None),
                     "weight": f.weight, "status": f.status}
                    for f in a.factors
                ],
                blockers_at_detection=list(a.blockers),
            )
    return RegimeResult(
        name=spec.name, label=spec.label, detected=False,
        detection_latency_samples=None, protected_samples=None,
        risk_at_detection=None,
    )


def run_calm_fpr(*, seed: int = 3, n: int = 800, sigma: float = 0.0012) -> tuple[float, int]:
    """False-positive rate in a pure-calm regime: how often the veto line is crossed
    when nothing is happening. Returns (fpr, n_assessments_post_warmup)."""
    rng = random.Random(seed)
    sentinel = VolatilitySentinel(symbols=[_SYMBOL])
    price = 100.0
    crossings = 0
    assessments = 0
    for i in range(n):
        price = _walk(rng, price, sigma)
        sentinel.ingest_price(_SYMBOL, price, ts=float(i))
        a = sentinel.assess(_SYMBOL)
        if a.status != "ok" or a.volatility_risk is None:
            continue  # warm-up: honestly no measurement, not a negative
        assessments += 1
        if a.volatility_risk >= VOL_RISK_BLOCK:
            crossings += 1
    return ((crossings / assessments) if assessments else 0.0, assessments)


def replay_trace(path: Path | None = None) -> dict[str, Any]:
    """Optional replay of the REAL daemon trace: feed the recorded Λ(t) series
    through the EWMA expansion estimator and report measured expansion events.
    Missing/short trace → honest ``no_data`` with a named blocker, never a
    substituted series."""
    p = path or (Path(__file__).resolve().parents[2] / "state" / "hnc_live_trace.jsonl")
    if not p.exists():
        return {"status": "no_data", "blocker": f"trace not found: {p.name}", "events": 0}
    est = EwmaVolEstimator()
    n = 0
    events = 0
    prev_above = False
    try:
        with p.open(encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except Exception:  # noqa: BLE001 — a corrupt row is skipped, not fabricated
                    continue
                lt = row.get("lambda_t")
                if not isinstance(lt, (int, float)) or lt <= 0:
                    continue
                est.update(float(lt))
                n += 1
                r = est.risk()
                above = r is not None and r >= VOL_RISK_BLOCK
                if above and not prev_above:
                    events += 1
                prev_above = above
    except Exception as exc:  # noqa: BLE001 — a broken trace is reported, never raises
        return {"status": "no_data", "blocker": f"trace unreadable: {str(exc)[:80]}", "events": 0}
    if n < 10:
        return {"status": "no_data", "blocker": f"only {n} usable rows", "events": 0}
    return {"status": "ok", "rows": n, "events": events,
            "source": "state/hnc_live_trace.jsonl (real Lambda(t) series)"}


def compute_benchmark(*, with_replay: bool = False,
                      replay_path: Path | None = None) -> SentinelBenchmarkReport:
    """Run the pinned regime library + calm FPR (+ optional real-trace replay)."""
    results = [run_regime(spec) for spec in canonical_regimes()]
    fpr, n_calm_assessments = run_calm_fpr()
    protected = [r.protected_samples for r in results if r.protected_samples is not None]
    replay = replay_trace(replay_path) if with_replay else {
        "status": "skipped", "note": "pass --replay to include the real-trace replay"}
    return SentinelBenchmarkReport(
        regimes=[r.to_dict() for r in results],
        all_detected=all(r.detected for r in results),
        min_protected_samples=(min(protected) if protected else None),
        fpr_calm=round(fpr, 6),
        calm_assessments=n_calm_assessments,
        replay=replay,
        risk_block=VOL_RISK_BLOCK,
    )


def write_benchmark_report(report: SentinelBenchmarkReport,
                           out_json: Path) -> SentinelBenchmarkReport:
    out_json.parent.mkdir(parents=True, exist_ok=True)
    payload = report.to_dict()
    payload["out_path"] = str(out_json)
    out_json.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n",
                        encoding="utf-8")
    return SentinelBenchmarkReport(**{**report.to_dict(), "out_path": str(out_json)})


def main(argv: list[str] | None = None) -> int:
    import argparse

    ap = argparse.ArgumentParser(description=BENCHMARK_BOUNDARY)
    ap.add_argument("--out", type=Path, default=None,
                    help="write the JSON artifact here (default: print to stdout)")
    ap.add_argument("--replay", nargs="?", const=True, default=False, metavar="TRACE",
                    help="also replay the real hnc_live_trace.jsonl (optional path)")
    args = ap.parse_args(argv)

    replay_path = Path(args.replay) if isinstance(args.replay, str) else None
    report = compute_benchmark(with_replay=bool(args.replay), replay_path=replay_path)
    if args.out is not None:
        report = write_benchmark_report(report, args.out)
        print(f"wrote {report.out_path}")
    else:
        print(json.dumps(report.to_dict(), indent=2, sort_keys=True))

    ok = report.all_detected and report.fpr_calm <= 0.20 and (
        report.min_protected_samples is None or report.min_protected_samples >= 0)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

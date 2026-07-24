#!/usr/bin/env python3
"""Null-calibration / false-positive-rate audit over the shipped adapter family.

The conformance suite (`aureon/bio/proxy_suite.py`) proves each self-testable adapter
**detects** structure (structured⇒present) and, on a single null draw, does not over-fire.
This module proves the harder, statistical half: across **many** synthetic nulls, each
adapter's rate of falsely reporting ``structure_present`` stays within the pre-registered
bound. It is the statistical backbone of the falsifiability claim.

What it measures (and why this way)
-----------------------------------
The detection decision is exactly ``p_A < ALPHA AND p_B < ALPHA`` where
``p_A``/``p_B`` come from :func:`phenolic_fingerprint.test_A`/:func:`test_B`. ``score_signal``
just wraps those two tests with controls + governance and returns the *same* p-values. So this
audit runs the engine's **own** two tests directly on each adapter's real *folded null tones*,
across many seeds — the identical detection rule, without the redundant per-call controls, so a
large trial count is affordable and the estimate is stable. It re-tunes nothing.

Under a true null each one-sided smoothed permutation p-value is ~uniform, so
``P(p_A < ALPHA) ≈ ALPHA`` and the joint false-positive rate is **bounded above by ALPHA**
(nominal ≈ ``ALPHA**2`` under independence, not guaranteed since both tests read the same tones).
This audit asserts the empirical rate stays ``<= ALPHA`` per adapter while the structured anchor
still fires — a two-sided, non-vacuous check.

Scientific boundary (enforced, not decorative)
----------------------------------------------
Every draw is a **synthetic null with no real subject**. The audit reports *statistical structure
in a derived signal only* — it is **NOT** a claim about any person, makes no cross-modal inference
about any source, and carries no efficacy claim. Pure stdlib + numpy + the bio adapters + engine;
no network, no import-time side effects.
"""

from __future__ import annotations

import sys
import time
import uuid
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any, Callable, Final

import numpy as np

# --- engine import (repo root holds phenolic_fingerprint.py) ---------------
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import phenolic_fingerprint as engine  # noqa: E402

__all__ = [
    "CALIBRATION_BOUNDARY",
    "CAL_RUN_TOPIC",
    "CAL_TRACE_NAME",
    "AdapterCalibration",
    "CalibrationReport",
    "calibrate_nulls",
    "write_calibration_report",
    "emit_calibration",
    "main",
]

CAL_RUN_TOPIC: Final[str] = "bio.null_calibration.run"
CAL_TRACE_NAME: Final[str] = "null_calibration"
_SOURCE: Final[str] = "null_calibration"

CALIBRATION_BOUNDARY: Final[str] = (
    "Synthetic false-positive-rate audit: it runs the engine's own two tests on each "
    "adapter's synthetic null signal (no real subject) many times and reports how often "
    "structure is falsely flagged - statistical structure in a derived signal only, NOT a "
    "claim about any person, no cross-modal inference, and no efficacy claim."
)

ALPHA: Final[float] = float(engine.ALPHA)


def _rng(seed: int, tag: int) -> np.random.Generator:
    """Reproducible generator stream for a (seed, purpose) pair (engine idiom)."""
    return np.random.default_rng([int(seed), int(tag)])


def _structure_present(tones: np.ndarray, *, nulls: int, seed: int) -> bool:
    """The engine's exact detection rule: ``p_A < ALPHA and p_B < ALPHA`` on ``tones``.

    Fewer than two tones can never be separable (the engine's tests return 1.0), so this
    returns ``False`` — the honest outcome, never a fabricated one.
    """
    arr = np.asarray(tones, dtype=float)
    if arr.size < 2:
        return False
    p_a = engine.test_A(arr, nulls=nulls, rng=_rng(seed, 1))
    p_b = engine.test_B(arr, nulls=nulls, rng=_rng(seed, 2))
    return bool(p_a < ALPHA and p_b < ALPHA)


# A "spec" is (name, modality, null-tones fn, structured-tones fn); each takes a seed and
# returns the adapter's real *folded* tone array (exactly what the pipeline would score).
_TonesFn = Callable[[int], np.ndarray]


def _adapter_specs() -> list[tuple[str, str, _TonesFn, _TonesFn]]:
    """Return each self-testable adapter's real folded null / structured tone generators.

    Lazy imports so importing this module never pulls the whole adapter graph and never
    requires an optional decode dependency (audio/video/UPE synthetics are numpy-only). The
    tones come straight from each adapter's ``extract()`` — the same folded array the governed
    pipeline scores — so the audit measures the real per-adapter null, not a stand-in.
    """
    from aureon.bio import audio_signal_adapter as asa
    from aureon.bio import upe_signal_adapter as usa
    from aureon.bio import video_signal_adapter as vsa
    from aureon.bio.human_harmonic_proxy import SyntheticSignalAdapter

    _prov = "null-calibration audit (synthetic; no real subject)"

    def _arr(sig_tones: tuple[float, ...]) -> np.ndarray:
        return np.asarray(sig_tones, dtype=float)

    return [
        (
            "human proxy (synthetic)", "synthetic",
            lambda s: _arr(SyntheticSignalAdapter().extract(mode="noise", seed=s).frequencies_hz),
            lambda s: _arr(SyntheticSignalAdapter().extract(mode="structured", seed=s).frequencies_hz),
        ),
        (
            "audio", "audio",
            lambda s: _arr(asa.AudioSignalAdapter().extract(
                asa.synthetic_audio("noise", seed=s), consent=True, provenance=_prov).frequencies_hz),
            lambda s: _arr(asa.AudioSignalAdapter().extract(
                asa.synthetic_audio("structured", seed=s), consent=True, provenance=_prov).frequencies_hz),
        ),
        (
            "video", "video",
            lambda s: _arr(vsa.VideoSignalAdapter().extract(
                vsa.synthetic_video("noise", seed=s), consent=True, provenance=_prov).frequencies_hz),
            lambda s: _arr(vsa.VideoSignalAdapter().extract(
                vsa.synthetic_video("structured", seed=s), consent=True, provenance=_prov).frequencies_hz),
        ),
        (
            # UPE's broadband anchor is seed-independent by design; the per-seed null *envelopes*
            # inside test_A/test_B still vary, so each trial is an independent draw of the decision.
            "upe", "upe",
            lambda s: _arr(usa.UPESignalAdapter().extract(
                usa.synthetic_upe("broadband"), consent=True, provenance=_prov, kind="spectrum").frequencies_hz),
            lambda s: _arr(usa.UPESignalAdapter().extract(
                usa.synthetic_upe("structured"), consent=True, provenance=_prov, kind="spectrum").frequencies_hz),
        ),
    ]


@dataclass(frozen=True)
class AdapterCalibration:
    """One adapter's false-positive-rate verdict over ``trials`` synthetic null draws."""

    adapter: str
    modality: str
    trials: int
    false_positives: int
    fpr: float
    bound: float
    structured_fires: bool
    conforms: bool
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CalibrationReport:
    """The consolidated null-calibration picture across the adapter family."""

    readings: list[AdapterCalibration]
    n_adapters: int
    n_conforming: int
    trials: int
    nulls: int
    alpha: float
    nominal_fpr: float
    boundary: str = CALIBRATION_BOUNDARY
    out_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["readings"] = [r.to_dict() for r in self.readings]
        return d


def calibrate_nulls(
    *,
    trials: int = 200,
    nulls: int = 200,
    seed0: int = 0,
    bound: float = ALPHA,
) -> CalibrationReport:
    """Measure each adapter's empirical false-``structure_present`` rate over synthetic nulls.

    For each adapter, run the engine's own two tests on ``trials`` independent synthetic *null*
    tone sets (seeds ``seed0 .. seed0+trials-1``) and count how many are falsely flagged
    separable; ``fpr = false_positives / trials``. The structured signal is scored once as a
    sanity anchor. An adapter **conforms** iff ``fpr <= bound`` *and* the structured anchor
    fires — a two-sided, non-vacuous check. Verdicts use the engine's pre-registered rule.
    """
    readings: list[AdapterCalibration] = []
    for name, modality, null_tones, structured_tones in _adapter_specs():
        fp = 0
        for i in range(trials):
            s = seed0 + i
            if _structure_present(null_tones(s), nulls=nulls, seed=s):
                fp += 1
        fpr = fp / trials if trials else 0.0
        structured_fires = _structure_present(structured_tones(seed0), nulls=nulls, seed=seed0)
        conforms = bool(fpr <= bound and structured_fires)
        readings.append(AdapterCalibration(
            adapter=name, modality=modality, trials=trials, false_positives=fp,
            fpr=fpr, bound=float(bound), structured_fires=structured_fires, conforms=conforms,
        ))
    return CalibrationReport(
        readings=readings,
        n_adapters=len(readings),
        n_conforming=sum(1 for r in readings if r.conforms),
        trials=trials,
        nulls=nulls,
        alpha=ALPHA,
        nominal_fpr=ALPHA * ALPHA,
    )


def write_calibration_report(
    report: CalibrationReport,
    out_md: str | Path,
    out_json: str | Path | None = None,
) -> CalibrationReport:
    """Write the calibration picture as a durable evidence artifact (markdown [+ JSON]).

    Sibling to :func:`aureon.bio.proxy_suite.write_suite_report`: it *serializes* the report —
    every value copied verbatim from ``report.to_dict()``, nothing recomputed or hedged. The
    body carries no wall-clock timestamp, so two runs at the same settings produce byte-identical
    files. The honest :data:`CALIBRATION_BOUNDARY` is printed verbatim. Returns the report with
    ``out_path`` set.
    """
    import json

    d = report.to_dict()
    lines: list[str] = []
    lines.append("# Null-calibration — false-positive-rate audit")
    lines.append("")
    lines.append(
        "Generated by `python -m aureon.bio.null_calibration --report <OUT.md>` — for each shipped "
        "adapter, the engine's own Test A + Test B are run on many synthetic *null* signals; the "
        "table reports how often structure is falsely flagged. Each verdict uses the pre-registered "
        "rule (`p_A < ALPHA and p_B < ALPHA`); nothing here is recomputed or hedged."
    )
    lines.append("")
    lines.append(f"> {CALIBRATION_BOUNDARY}")
    lines.append("")
    lines.append(
        f"**{report.n_conforming}/{report.n_adapters} adapters conform** "
        f"(false-positive rate ≤ bound {report.alpha:g} = ALPHA, and the structured anchor still "
        f"fires) over **{report.trials} trials** at **{report.nulls} nulls**. "
        f"Nominal joint rate under independence ≈ ALPHA² = {report.nominal_fpr:g}."
    )
    lines.append("")
    lines.append("| adapter | modality | trials | false positives | FPR | bound | structured fires | conforms |")
    lines.append("|---|---|---:|---:|---:|---:|:---:|:---:|")
    for r in report.readings:
        lines.append(
            f"| {r.adapter} | {r.modality} | {r.trials} | {r.false_positives} | {r.fpr:.4f} | "
            f"{r.bound:g} | {r.structured_fires} | {r.conforms} |"
        )
    lines.append("")
    md = "\n".join(lines) + "\n"

    out_md_path = Path(out_md)
    out_md_path.write_text(md, encoding="utf-8")

    if out_json is not None:
        Path(out_json).write_text(
            json.dumps(d, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )

    return replace(report, out_path=str(out_md_path))


def emit_calibration(report: CalibrationReport, *, bus: Any | None = None, trace: bool = True) -> dict[str, Any]:
    """Publish the calibration picture to cognition; return its dict.

    Mirrors :func:`aureon.bio.proxy_suite.emit_suite` — a ``bio.null_calibration.run`` Thought on
    the ThoughtBus + a compact ``null_calibration`` bus_trace — so the metacognition monitor / Queen
    can sense that the family's false-positive rate is still bounded. Bus/trace failures are
    swallowed; emission never crashes a run.
    """
    payload = report.to_dict()
    summary = {
        "n_adapters": report.n_adapters,
        "n_conforming": report.n_conforming,
        "trials": report.trials,
        "nulls": report.nulls,
        "alpha": report.alpha,
        "max_fpr": max((r.fpr for r in report.readings), default=0.0),
        "adapters": [
            {"adapter": r.adapter, "fpr": r.fpr, "conforms": r.conforms}
            for r in report.readings
        ],
        "boundary": CALIBRATION_BOUNDARY,
    }
    try:
        from aureon.core.aureon_thought_bus import Thought, get_thought_bus

        target = bus if bus is not None else get_thought_bus()
        target.publish(
            Thought(source=_SOURCE, topic=CAL_RUN_TOPIC, trace_id=uuid.uuid4().hex, payload=summary)
        )
    except Exception:  # noqa: BLE001 - emission is best-effort, never fatal
        pass

    if trace:
        try:
            from aureon.core.bus_trace import append_trace

            append_trace(CAL_TRACE_NAME, {
                "n_adapters": report.n_adapters,
                "n_conforming": report.n_conforming,
                "max_fpr": max((r.fpr for r in report.readings), default=0.0),
                "alpha": report.alpha,
                "boundary": CALIBRATION_BOUNDARY,
                "_ts": time.time(),
            })
        except Exception:  # noqa: BLE001 - trace mirror is best-effort
            pass

    return payload


def main(argv: list[str] | None = None) -> int:
    """CLI: run the null-calibration audit and print / write the consolidated picture."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Audit each shipped adapter's false-positive rate on synthetic nulls (engine tests, unchanged)."
    )
    parser.add_argument("--report", metavar="OUT.md", help="write the picture as a markdown evidence artifact")
    parser.add_argument("--report-json", metavar="OUT.json", help="also write the JSON record")
    parser.add_argument("--trials", type=int, default=200)
    parser.add_argument("--nulls", type=int, default=200)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--self-test", action="store_true",
                        help="assert every adapter conforms (FPR ≤ ALPHA, structured fires) and exit non-zero otherwise")
    args = parser.parse_args(argv)

    report = calibrate_nulls(trials=args.trials, nulls=args.nulls, seed0=args.seed)

    print("Null-calibration — false-positive-rate audit (engine tests, unchanged)")
    print(f"  boundary: {CALIBRATION_BOUNDARY}")
    print(f"  {report.trials} trials · {report.nulls} nulls · ALPHA={report.alpha:g} · "
          f"nominal ALPHA²={report.nominal_fpr:g}")
    for r in report.readings:
        mark = "✅" if r.conforms else "❌"
        print(f"  {mark} {r.adapter:24s} FPR={r.fpr:.4f} ({r.false_positives}/{r.trials}) "
              f"≤ {r.bound:g} · structured_fires={r.structured_fires}")
    print(f"  {report.n_conforming}/{report.n_adapters} adapters conform")

    if args.report:
        rendered = write_calibration_report(report, args.report, args.report_json)
        print(f"  report written: {rendered.out_path}")

    if args.self_test:
        return 0 if report.n_conforming == report.n_adapters else 1
    return 0


if __name__ == "__main__":  # pragma: no cover - manual entry point
    raise SystemExit(main())

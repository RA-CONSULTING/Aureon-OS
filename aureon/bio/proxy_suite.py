#!/usr/bin/env python3
"""Signal-adapter conformance suite — the capstone over the shipped adapters.

The `SignalAdapter` roadmap is complete (image · audio · video · UPE · sky · market).
This module is the roll-up that proves the *family* shares one governed backbone: it
runs each self-testable adapter's **synthetic** self-test — a structured signal that
must score present and a null signal that must score absent — through the **unchanged**
:func:`aureon.bio.human_harmonic_proxy.score_signal`, and tabulates whether each adapter
**conforms** (structured⇒present ∧ null⇒absent, both valid). It is the human-signal
analogue of the φ Celestial Observatory: one consolidated, self-documenting picture.

Scientific boundary (enforced, not decorative)
----------------------------------------------
Every reading here is produced from a **synthetic self-test that uses no real subject**.
The suite reports *statistical structure in a derived signal only* — it is **NOT** a
claim about any person, makes no cross-modal inference about any source, and carries no
efficacy claim. Each verdict is exactly what the pre-registered test returned. The four
adapters covered are those with a deterministic structured/null synthetic contract
(the proxy's own synthetic adapter, audio, video, UPE); image / sky / market score real
data and are exercised by their own lanes/benchmarks, not by this synthetic roll-up.

Design constraints
------------------
Pure stdlib + the bio adapters + engine. No network, no import-time side effects. The
engine's pre-registered logic and thresholds are reused verbatim — nothing here tunes
them. The report body carries no wall-clock timestamp, so two runs at the same
``seed``/``nulls`` are byte-identical (mirrors :func:`write_observatory_report`).
"""

from __future__ import annotations

import time
import uuid
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any, Callable, Final

__all__ = [
    "SUITE_BOUNDARY",
    "SUITE_RUN_TOPIC",
    "SUITE_TRACE_NAME",
    "AdapterReading",
    "SuiteReport",
    "run_suite",
    "write_suite_report",
    "emit_suite",
    "main",
]

SUITE_RUN_TOPIC: Final[str] = "bio.proxy_suite.run"
SUITE_TRACE_NAME: Final[str] = "signal_adapter_suite"
_SOURCE: Final[str] = "signal_adapter_suite"

SUITE_BOUNDARY: Final[str] = (
    "The signal-adapter conformance suite runs each shipped adapter's synthetic "
    "self-test (no real subject) through the one unchanged score_signal pipeline and "
    "reports structure present/absent exactly as the pre-registered test returned - "
    "statistical structure in a derived signal only, NOT a claim about any person, no "
    "cross-modal inference about any source, and no efficacy claim."
)


@dataclass(frozen=True)
class AdapterReading:
    """One adapter's conformance verdict, as the engine returned it."""

    adapter: str
    modality: str
    present_valid: bool
    present_structure: bool
    present_A_p: float | None
    present_B_p: float | None
    absent_valid: bool
    absent_structure: bool
    conforms: bool
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SuiteReport:
    """The consolidated signal-adapter conformance picture."""

    readings: list[AdapterReading]
    n_adapters: int
    n_conforming: int
    boundary: str = SUITE_BOUNDARY
    out_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["readings"] = [r.to_dict() for r in self.readings]
        return d


# A "spec" is (adapter name, modality, present-signal scorer, null-signal scorer).
# Each scorer takes (nulls, seed) and returns a ProxyResult through the unchanged pipeline.
_Scorer = Callable[[int, int], Any]


def _adapter_specs() -> list[tuple[str, str, _Scorer, _Scorer]]:
    """Return the self-testable adapters and how to drive their structured/null synthetics.

    Lazy imports so importing this module never pulls the whole adapter graph and never
    requires an optional decode dependency (audio/video/UPE synthetics are numpy-only).
    """
    from aureon.bio import audio_signal_adapter as asa
    from aureon.bio import upe_signal_adapter as usa
    from aureon.bio import video_signal_adapter as vsa
    from aureon.bio.human_harmonic_proxy import SyntheticSignalAdapter, score_signal

    _prov = "conformance suite (synthetic self-test; no real subject)"

    return [
        (
            "human proxy (synthetic)", "synthetic",
            lambda n, s: score_signal(SyntheticSignalAdapter().extract(mode="structured", seed=s),
                                      nulls=n, seed=s),
            lambda n, s: score_signal(SyntheticSignalAdapter().extract(mode="noise", seed=s),
                                      nulls=n, seed=s),
        ),
        (
            "audio", "audio",
            lambda n, s: asa.score_audio(asa.synthetic_audio("structured", seed=s),
                                        consent=True, provenance=_prov, nulls=n, seed=s),
            lambda n, s: asa.score_audio(asa.synthetic_audio("noise", seed=s),
                                        consent=True, provenance=_prov, nulls=n, seed=s),
        ),
        (
            "video", "video",
            lambda n, s: vsa.score_video(vsa.synthetic_video("structured", seed=s),
                                        consent=True, provenance=_prov, nulls=n, seed=s),
            lambda n, s: vsa.score_video(vsa.synthetic_video("noise", seed=s),
                                        consent=True, provenance=_prov, nulls=n, seed=s),
        ),
        (
            "upe", "upe",
            lambda n, s: usa.score_upe(usa.synthetic_upe("structured"),
                                      consent=True, provenance=_prov, nulls=n, seed=s),
            lambda n, s: usa.score_upe(usa.synthetic_upe("broadband"),
                                      consent=True, provenance=_prov, nulls=n, seed=s),
        ),
    ]


def run_suite(*, nulls: int = 300, seed: int = 0) -> SuiteReport:
    """Run every self-testable adapter's structured + null synthetic through the pipeline.

    An adapter **conforms** iff its structured signal scores a valid ``structure_present``
    result and its null signal scores a valid ``structure_absent`` result — the honest
    two-sided anchor, both through the unchanged ``score_signal``. Verdicts are reported
    exactly as the pre-registered tests return them.
    """
    readings: list[AdapterReading] = []
    for name, modality, present_fn, absent_fn in _adapter_specs():
        pres = present_fn(nulls, seed).to_dict()
        abse = absent_fn(nulls, seed).to_dict()
        conforms = bool(
            pres["valid"] and pres["structure_present"]
            and abse["valid"] and not abse["structure_present"]
        )
        readings.append(AdapterReading(
            adapter=name, modality=modality,
            present_valid=bool(pres["valid"]), present_structure=bool(pres["structure_present"]),
            present_A_p=pres["test_A_p"], present_B_p=pres["test_B_p"],
            absent_valid=bool(abse["valid"]), absent_structure=bool(abse["structure_present"]),
            conforms=conforms,
        ))
    return SuiteReport(
        readings=readings,
        n_adapters=len(readings),
        n_conforming=sum(1 for r in readings if r.conforms),
    )


def _fmt_p(p: float | None) -> str:
    """p-value cell, ``-`` when the signal produced no p-value."""
    return f"{p:.4f}" if p is not None else "-"


def write_suite_report(
    report: SuiteReport,
    out_md: str | Path,
    out_json: str | Path | None = None,
) -> SuiteReport:
    """Write the consolidated conformance picture as a durable evidence artifact (markdown [+ JSON]).

    Sibling to :func:`aureon.bio.celestial_observatory.write_observatory_report`: it
    *serializes* the report — every value copied verbatim from ``report.to_dict()``,
    nothing recomputed or hedged. The body carries no wall-clock timestamp, so two runs at
    the same ``seed``/``nulls`` produce byte-identical files. The honest
    :data:`SUITE_BOUNDARY` is printed verbatim. Returns the report with ``out_path`` set.
    """
    import json

    d = report.to_dict()
    lines: list[str] = []
    lines.append("# Signal-adapter conformance suite — evidence report")
    lines.append("")
    lines.append(
        "Generated by `python -m aureon.bio.proxy_suite --report <OUT.md>` — every "
        "self-testable adapter's synthetic structured + null self-test operated through the "
        "one unchanged `score_signal` pipeline. Each verdict below is exactly what the "
        "pre-registered test returned; nothing here is recomputed or hedged."
    )
    lines.append("")
    lines.append(f"> {SUITE_BOUNDARY}")
    lines.append("")
    lines.append(
        f"**{report.n_conforming}/{report.n_adapters} adapters conform** "
        "(structured⇒present ∧ null⇒absent, both valid, through the unchanged engine)."
    )
    lines.append("")
    lines.append(
        "| adapter | modality | structured valid | structured present | Test A p | Test B p "
        "| null valid | null present | conforms |"
    )
    lines.append("|---|---|:---:|:---:|---:|---:|:---:|:---:|:---:|")
    for r in report.readings:
        lines.append(
            f"| {r.adapter} | {r.modality} | {r.present_valid} | {r.present_structure} | "
            f"{_fmt_p(r.present_A_p)} | {_fmt_p(r.present_B_p)} | {r.absent_valid} | "
            f"{r.absent_structure} | {r.conforms} |"
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


def emit_suite(report: SuiteReport, *, bus: Any | None = None, trace: bool = True) -> dict[str, Any]:
    """Publish the suite's consolidated picture to cognition; return its dict.

    Mirrors :func:`aureon.bio.celestial_observatory.emit_observatory` — a
    ``bio.proxy_suite.run`` Thought on the ThoughtBus + a compact ``signal_adapter_suite``
    bus_trace — so the metacognition monitor / Queen can sense that the whole adapter
    family still conforms. Bus/trace failures are swallowed; emission never crashes a run.
    """
    payload = report.to_dict()
    summary = {
        "n_adapters": report.n_adapters,
        "n_conforming": report.n_conforming,
        "adapters": [
            {"adapter": r.adapter, "modality": r.modality, "conforms": r.conforms}
            for r in report.readings
        ],
        "boundary": SUITE_BOUNDARY,
    }
    try:
        from aureon.core.aureon_thought_bus import Thought, get_thought_bus

        target = bus if bus is not None else get_thought_bus()
        target.publish(
            Thought(source=_SOURCE, topic=SUITE_RUN_TOPIC, trace_id=uuid.uuid4().hex,
                    payload=summary)
        )
    except Exception:  # noqa: BLE001 - emission is best-effort, never fatal
        pass

    if trace:
        try:
            from aureon.core.bus_trace import append_trace

            append_trace(SUITE_TRACE_NAME, {
                "n_adapters": report.n_adapters,
                "n_conforming": report.n_conforming,
                "boundary": SUITE_BOUNDARY,
                "_ts": time.time(),
            })
        except Exception:  # noqa: BLE001 - trace mirror is best-effort
            pass

    return payload


def main(argv: list[str] | None = None) -> int:
    """CLI: run the conformance suite and print / write the consolidated picture."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Run every shipped adapter's synthetic self-test through the one unchanged engine."
    )
    parser.add_argument("--report", metavar="OUT.md",
                        help="write the consolidated picture as a markdown evidence artifact")
    parser.add_argument("--report-json", metavar="OUT.json", help="also write the JSON record")
    parser.add_argument("--nulls", type=int, default=300)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--self-test", action="store_true",
                        help="assert every adapter conforms and exit non-zero if any does not")
    args = parser.parse_args(argv)

    report = run_suite(nulls=args.nulls, seed=args.seed)

    print("Signal-adapter conformance suite — every adapter, one unchanged engine")
    print(f"  boundary: {SUITE_BOUNDARY}")
    for r in report.readings:
        mark = "✅" if r.conforms else "❌"
        print(f"  {mark} {r.adapter:24s} structured→present={r.present_structure} "
              f"(A_p={_fmt_p(r.present_A_p)}) · null→present={r.absent_structure}")
    print(f"  {report.n_conforming}/{report.n_adapters} adapters conform")

    if args.report:
        rendered = write_suite_report(report, args.report, args.report_json)
        print(f"  report written: {rendered.out_path}")

    if args.self_test:
        return 0 if report.n_conforming == report.n_adapters else 1
    return 0


if __name__ == "__main__":  # pragma: no cover - manual entry point
    raise SystemExit(main())

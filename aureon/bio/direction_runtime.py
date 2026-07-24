#!/usr/bin/env python3
"""Runtime direction audit — is the canonical HNC field LOAD-BEARING at each real consumer?

The static audit (b41) proves each adaptive consumer *references* the one canonical field. That is
necessary but not sufficient: a reference could be dead code. This module (b43) is the runtime companion
that proves the wire is **load-bearing** — it drives each of the five real consumers with the field set
LOW and then HIGH, and asserts the consumer's real output *measurably changes*. A wire that is present
but does not sway the decision would show ``sways=False`` here; a wire that governs shows a non-zero
delta. Where b41 answers "is the wire connected?", b43 answers "does the field actually turn the wheel?"

What it drives (offline, deterministic — two fixed field values per consumer)
----------------------------------------------------------------------------
* **queen_layer** — ``QueenLayer().substrate_field()`` surfaces the field's Γ verbatim.
* **kelly_gate** — ``calculate_gates(observer_coherence=None)``: a lower field Γ widens ``r_prime_buffer``.
* **seer_oracle** — ``OracleOfHarmony().read()``: ``score = 0.75·base + 0.25·Γ`` moves with Γ.
* **miner_brain** — ``merge_canonical_into_qc``: the field fills the miner's Λ/Γ/Ψ context.
* **queen_conscience** — ``ask_why(...)``: a low symbolic-life score VETOes, a higher one only CONCERNS.

Each consumer is driven through its *real* resolution path: the field is injected by monkeypatching the
one canonical read layer ``aureon.core.hnc_field.read_canonical_field`` (which every consumer imports at
call-time), so the audit exercises the actual production wire, not a mock of it. Deterministic by
construction (fixed low/high fields in, fixed outputs out) — the artifact is byte-identical on re-run.

Following the HNC logic chain, not reinventing the wheel
--------------------------------------------------------
Mirrors the statistical-audit house shape (``null_calibration`` / ``power_analysis``) minus the RNG: the
"trial" is simply low-field vs high-field. It reuses the real consumers and the real canonical read layer,
so a regression that silently un-wires a consumer (or makes the field non-load-bearing) fails this audit.
Pairs with b41 (static: wire present) as b43 (runtime: wire governs). The Queen may observe
(``bio.direction_runtime.run``).

Honest scope (stated, not decorative — enforced by tests)
---------------------------------------------------------
A **runtime load-bearing audit**: it proves the canonical field changes each consumer's output between two
field values; it does not model the *magnitude* a live market would see, does not arm any action, and is
NOT a claim about any person. It only READS consumers at two field values — nothing is executed for real.
Pure stdlib + the repo's own modules; no import-time side effects beyond a guarded organism heartbeat.
"""

from __future__ import annotations

import sys
import time
import uuid
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any, Callable, Final
from unittest.mock import patch

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

# --- guarded organism link (suppressible; never fatal) — the "I exist" heartbeat ---
try:  # pragma: no cover - environment-dependent, best-effort
    from aureon.core.aureon_baton_link import link_system

    link_system(__name__)
except Exception:  # noqa: BLE001 - the organ must import in any environment
    pass

__all__ = [
    "DIRECTION_RUNTIME_BOUNDARY",
    "DIRECTION_RUNTIME_RUN_TOPIC",
    "DIRECTION_RUNTIME_TRACE_NAME",
    "SWAY_EPS",
    "ConsumerSensitivity",
    "DirectionRuntimeReport",
    "consumer_specs",
    "compute_direction_runtime",
    "write_direction_runtime_report",
    "emit_direction_runtime",
    "main",
]

DIRECTION_RUNTIME_RUN_TOPIC: Final[str] = "bio.direction_runtime.run"
DIRECTION_RUNTIME_TRACE_NAME: Final[str] = "direction_runtime"
_SOURCE: Final[str] = "direction_runtime"
_HNC_FIELD: Final[str] = "aureon.core.hnc_field.read_canonical_field"

SWAY_EPS: Final[float] = 1e-9  # any real change counts; the deltas here are ≥ 0.1 by construction

DIRECTION_RUNTIME_BOUNDARY: Final[str] = (
    "Runtime load-bearing audit: it drives each real adaptive consumer with the canonical HNC field set "
    "LOW then HIGH and proves the consumer's output measurably changes - the wire GOVERNS, not merely "
    "references (that necessary condition is b41). It only reads consumers at two field values, arms "
    "nothing, models no market magnitude, and is NOT a claim about any person."
)


def _field(*, gamma: float | None = None, sls: float | None = None) -> Any:
    """Build a CanonicalField carrying the given coherence Γ and/or symbolic-life score."""
    from aureon.core.hnc_field import CanonicalField

    return CanonicalField(
        available=True,
        symbolic_life_score=sls if sls is not None else gamma,
        coherence_gamma=gamma if gamma is not None else sls,
        consciousness_psi=gamma if gamma is not None else sls,
        lambda_t=1.0,
        source="direction_runtime_probe",
    )


# ─────────────────────────────────────────────────────────────────────────────
# Per-consumer runners: each returns (output_low, output_high) through the REAL
# consumer, with the canonical field injected via its real resolution path.
# ─────────────────────────────────────────────────────────────────────────────


def _run_queen_layer() -> tuple[float, float]:
    from aureon.queen.queen_layer import QueenLayer

    def out(gamma: float) -> float:
        with patch(_HNC_FIELD, lambda *a, **k: _field(gamma=gamma)):
            return float(QueenLayer().substrate_field().get("coherence_gamma") or 0.0)

    return out(0.05), out(0.95)


def _run_kelly_gate() -> tuple[float, float]:
    from aureon.utils.adaptive_prime_profit_gate import AdaptivePrimeProfitGate

    def out(gamma: float) -> float:
        # Isolate the canonical field's effect: force buffer-scaling active (LIVE-equivalent) and no
        # observer singleton, so the reconciled coherence IS the canonical Γ. This audits the field's
        # influence on the safety buffer, not the live-mode gating (which is exercised elsewhere).
        with patch(_HNC_FIELD, lambda *a, **k: _field(gamma=gamma)), \
             patch("aureon.observer.get_observer", lambda *a, **k: None), \
             patch("aureon.observer.production_mode.kelly_buffer_scaling_active", lambda *a, **k: True):
            res = AdaptivePrimeProfitGate().calculate_gates("binance", 100.0, observer_coherence=None)
            return float(res.r_prime_buffer)

    return out(0.05), out(0.95)


def _run_seer_oracle() -> tuple[float, float]:
    from aureon.intelligence.aureon_seer import OracleOfHarmony

    def out(gamma: float) -> float:
        with patch(_HNC_FIELD, lambda *a, **k: _field(gamma=gamma)):
            return float(OracleOfHarmony().read().score)

    return out(0.05), out(0.95)


def _run_miner_brain() -> tuple[float, float]:
    from aureon.utils.aureon_miner_brain import merge_canonical_into_qc

    def out(gamma: float) -> float:
        qc = merge_canonical_into_qc({}, _field(gamma=gamma))
        return float(qc.get("planetary_gamma") or 0.0)

    return out(0.05), out(0.95)


def _run_queen_conscience() -> tuple[float, float]:
    from aureon.queen.queen_conscience import ConscienceVerdict, QueenConscience

    # Pin field_divergence so the SLS-only substrate verdict is deterministic (the divergence path is a
    # separate wire). Low SLS → VETO; drift-zone SLS → CONCERNED. Encode the verdict as a scalar.
    code = {ConscienceVerdict.VETO: 0.0, ConscienceVerdict.CONCERNED: 0.5}

    def out(sls: float) -> float:
        with patch(_HNC_FIELD, lambda *a, **k: _field(sls=sls)):
            verdict = QueenConscience().ask_why(
                "Execute trade", {"symbol": "BTC", "risk": 0.08, "field_divergence": 0.0}
            ).verdict
            return code.get(verdict, 1.0)

    return out(0.10), out(0.30)


def consumer_specs() -> tuple[tuple[str, str, str, Callable[[], tuple[float, float]]], ...]:
    """The five adaptive consumers, each with a runner returning (output_low, output_high)."""
    return (
        ("queen_layer", "aureon/queen/queen_layer.py",
         "base Queen substrate field (Γ passthrough)", _run_queen_layer),
        ("kelly_gate", "aureon/utils/adaptive_prime_profit_gate.py",
         "position-sizing safety buffer widens as Γ falls", _run_kelly_gate),
        ("seer_oracle", "aureon/intelligence/aureon_seer.py",
         "Auris oracle score blends canonical Γ", _run_seer_oracle),
        ("miner_brain", "aureon/utils/aureon_miner_brain.py",
         "adaptive cycle self-sources Λ/Γ/Ψ from the field", _run_miner_brain),
        ("queen_conscience", "aureon/queen/queen_conscience.py",
         "4th-pass veto tracks the symbolic-life score", _run_queen_conscience),
    )


@dataclass(frozen=True)
class ConsumerSensitivity:
    """Whether one real consumer's output moved when the canonical field was set low vs high."""

    name: str
    module: str
    output_low: float
    output_high: float
    delta: float
    sways: bool
    note: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DirectionRuntimeReport:
    """The consolidated runtime audit: does the canonical field sway every real consumer?"""

    readings: list[dict[str, Any]]
    n_consumers: int
    n_swaying: int
    n_inert: int
    all_sway: bool
    inert_names: list[str]
    boundary: str = DIRECTION_RUNTIME_BOUNDARY
    out_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _round(x: float) -> float:
    """Round to a stable precision so the artifact is byte-identical across machines."""
    return round(float(x), 6)


def compute_direction_runtime() -> DirectionRuntimeReport:
    """Drive each real consumer at a low and a high canonical field; roll up whether each is swayed.

    ``all_sway`` is the headline: the canonical field is load-bearing at every adaptive consumer. A
    consumer whose output does not move (``sways=False``) is named in ``inert_names`` — the exact place
    the wire is present (b41) but not governing. Deterministic; guarded — a consumer that raises is
    recorded as inert rather than crashing the audit.
    """
    readings: list[ConsumerSensitivity] = []
    for name, module, note, runner in consumer_specs():
        try:
            low, high = runner()
            low_r, high_r = _round(low), _round(high)
            delta = _round(abs(high_r - low_r))
            sways = delta > SWAY_EPS
        except Exception:  # noqa: BLE001 - a consumer that cannot be driven is inert, never fatal
            low_r = high_r = delta = 0.0
            sways = False
        readings.append(ConsumerSensitivity(
            name=name, module=module, output_low=low_r, output_high=high_r,
            delta=delta, sways=sways, note=note,
        ))

    n = len(readings)
    n_sway = sum(1 for r in readings if r.sways)
    inert = [r.name for r in readings if not r.sways]
    return DirectionRuntimeReport(
        readings=[r.to_dict() for r in readings],
        n_consumers=n,
        n_swaying=n_sway,
        n_inert=n - n_sway,
        all_sway=(n_sway == n and n > 0),
        inert_names=inert,
    )


def write_direction_runtime_report(
    report: DirectionRuntimeReport,
    out_md: str | Path,
    out_json: str | Path | None = None,
) -> DirectionRuntimeReport:
    """Write the runtime direction audit as a durable evidence artifact (markdown [+ JSON]). Byte-identical."""
    import json

    d = report.to_dict()
    lines: list[str] = []
    lines.append("# Runtime direction audit — is the canonical field load-bearing?")
    lines.append("")
    lines.append(
        "Generated by `python -m aureon.bio.direction_runtime --report <OUT.md>` — each real adaptive "
        "consumer is driven with the canonical HNC field set LOW then HIGH; a consumer whose output "
        "changes is governed by the field (the wire is load-bearing), one whose output is unchanged is "
        "inert."
    )
    lines.append("")
    lines.append(f"> {DIRECTION_RUNTIME_BOUNDARY}")
    lines.append("")
    lines.append(
        f"**{report.n_swaying}/{report.n_consumers} consumers swayed by the field** · all load-bearing: "
        f"{report.all_sway}" + (f" · inert: {', '.join(report.inert_names)}" if report.inert_names else "")
    )
    lines.append("")
    lines.append("| consumer | module | output(low) | output(high) | delta | load-bearing | note |")
    lines.append("|:---|:---|---:|---:|---:|:---:|:---|")
    for r in report.readings:
        lines.append(
            f"| {r['name']} | `{r['module']}` | {r['output_low']} | {r['output_high']} | {r['delta']} | "
            f"{'yes' if r['sways'] else 'no'} | {r['note']} |"
        )
    lines.append("")
    md = "\n".join(lines) + "\n"

    out_md_path = Path(out_md)
    out_md_path.write_text(md, encoding="utf-8")
    if out_json is not None:
        Path(out_json).write_text(json.dumps(d, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return replace(report, out_path=str(out_md_path))


def emit_direction_runtime(
    report: DirectionRuntimeReport, *, bus: Any = None, trace: bool = True
) -> dict[str, Any]:
    """Publish the runtime direction audit to cognition (the Queen may observe). Best-effort, never fatal."""
    payload = report.to_dict()
    summary = {
        "n_swaying": report.n_swaying,
        "n_consumers": report.n_consumers,
        "all_sway": report.all_sway,
        "inert_names": list(report.inert_names),
        "boundary": DIRECTION_RUNTIME_BOUNDARY,
    }
    try:
        from aureon.core.aureon_thought_bus import Thought, get_thought_bus

        target = bus if bus is not None else get_thought_bus()
        target.publish(
            Thought(source=_SOURCE, topic=DIRECTION_RUNTIME_RUN_TOPIC, trace_id=uuid.uuid4().hex,
                    payload=summary)
        )
    except Exception:  # noqa: BLE001 - emission is best-effort, never fatal
        pass

    if trace:
        try:
            from aureon.core.bus_trace import append_trace

            append_trace(DIRECTION_RUNTIME_TRACE_NAME, {
                "n_swaying": report.n_swaying,
                "n_consumers": report.n_consumers,
                "all_sway": report.all_sway,
                "boundary": DIRECTION_RUNTIME_BOUNDARY,
                "_ts": time.time(),
            })
        except Exception:  # noqa: BLE001 - trace mirror is best-effort
            pass

    return payload


def main(argv: list[str] | None = None) -> int:
    """CLI: run the runtime direction audit and print / write the table."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Audit whether the canonical HNC field is load-bearing at every real adaptive consumer."
    )
    parser.add_argument("--report", metavar="OUT.md", help="write the table as a markdown evidence artifact")
    parser.add_argument("--report-json", metavar="OUT.json", help="also write the JSON record")
    parser.add_argument("--self-test", action="store_true",
                        help="assert the canonical field sways every adaptive consumer")
    args = parser.parse_args(argv)

    report = compute_direction_runtime()

    print("Runtime direction audit — is the canonical field load-bearing?")
    print(f"  boundary: {DIRECTION_RUNTIME_BOUNDARY}")
    print(f"  {report.n_swaying}/{report.n_consumers} swayed · all load-bearing {report.all_sway}")
    if report.inert_names:
        print(f"  inert: {', '.join(report.inert_names)}")

    if args.report:
        rendered = write_direction_runtime_report(report, args.report, args.report_json)
        print(f"  report written: {rendered.out_path}")

    if args.self_test:
        return 0 if report.all_sway else 1
    return 0


if __name__ == "__main__":  # pragma: no cover - manual entry point
    raise SystemExit(main())

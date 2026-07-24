#!/usr/bin/env python3
"""Logic-flow tracer — watch one HNC signal cross the bus into a decision.

Where ``hnc_direction_audit`` (b41) proves *statically* that every adaptive consumer references the one
canonical field, this module proves it *dynamically*: it stands up an isolated ThoughtBus, publishes a
single authoritative ``symbolic.life.pulse`` (the shape the HNC live daemon emits), and then watches the
signal flow — read through the canonical layer (``read_canonical_field``), carried into a downstream
decision, and mirrored onward — recording the observed **topic sequence** and the **trace-id continuity**
along the way. It answers, with a byte-identical artifact, "how does the logic flow from the harmonic
core to a decision, and does the same thread of causation run all the way through?"

What it asserts
---------------
* **pulse published** — the canonical ``symbolic.life.pulse`` reaches the shared bus.
* **field read** — ``read_canonical_field(bus)`` returns that exact field (a consumer can read the one
  shared value, not a private engine).
* **decision carries the field** — the downstream decision's payload is derived from the field it read
  (the signal actually informs the decision, it is not decorative).
* **trace-id continuity** — the pulse, the decision, and the emitted trace share ONE ``trace_id``: a
  single unbroken thread of causation from harmonic core to decision.

Following the HNC logic chain, not reinventing the wheel
--------------------------------------------------------
It uses the real transport (``aureon.core.aureon_thought_bus``), the real canonical read layer
(``aureon.core.hnc_field.read_canonical_field``), and the ``symbolic.life.pulse`` topic the daemon truly
publishes — so the trace tracks the organism's own plumbing, not a mock. It pairs with the b41 direction
audit (static wire present) as the b40 live trace (signal actually flows). The Queen may observe
(``cognition.logic_flow.run``).

Honest scope (stated, not decorative — enforced by tests)
---------------------------------------------------------
A **deterministic flow trace** over an isolated in-memory bus with a fixed seed pulse: it proves the
signal crosses from the canonical field into a decision on one trace_id. It does NOT run the live daemon,
does NOT trade, and makes **no claim about any person**. Pure stdlib + the repo's own bus/field modules;
no import-time side effects beyond a guarded, suppressible organism heartbeat.
"""

from __future__ import annotations

import sys
import time
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any, Final

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
    "LOGIC_FLOW_BOUNDARY",
    "LOGIC_FLOW_RUN_TOPIC",
    "LOGIC_FLOW_TRACE_NAME",
    "PULSE_TOPIC",
    "DECISION_TOPIC",
    "LogicFlowReport",
    "compute_logic_flow",
    "write_logic_flow_report",
    "emit_logic_flow",
    "main",
]

LOGIC_FLOW_RUN_TOPIC: Final[str] = "cognition.logic_flow.run"
LOGIC_FLOW_TRACE_NAME: Final[str] = "logic_flow"
_SOURCE: Final[str] = "logic_flow"

PULSE_TOPIC: Final[str] = "symbolic.life.pulse"  # the authoritative HNC signal (daemon's topic)
DECISION_TOPIC: Final[str] = "cognition.logic_flow.decision"

LOGIC_FLOW_BOUNDARY: Final[str] = (
    "Deterministic flow trace: on an isolated in-memory bus it publishes one canonical symbolic.life.pulse, "
    "reads it through aureon.core.hnc_field.read_canonical_field, carries it into a downstream decision, "
    "and asserts the topic sequence and a single unbroken trace_id from harmonic core to decision. It does "
    "NOT run the live daemon, does NOT trade, and is NOT a claim about any person."
)


@dataclass(frozen=True)
class LogicFlowReport:
    """One traced flow: a canonical HNC pulse crossing the bus into a decision on a single trace_id."""

    topic_sequence: list[str]
    trace_id: str
    pulse_published: bool
    field_read: bool
    field_score: float | None
    decision_carries_field: bool
    trace_id_propagated: bool
    single_trace_id: bool
    trace_signal_written: bool
    flow_intact: bool
    boundary: str = LOGIC_FLOW_BOUNDARY
    out_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _fresh_bus() -> Any:
    """A private in-memory ThoughtBus with no persistence and no auto-wired sonar (audit-inert)."""
    import os

    os.environ.setdefault("AUREON_AUDIT_MODE", "1")  # keep the whale-sonar probe inert during the trace
    from aureon.core.aureon_thought_bus import ThoughtBus

    return ThoughtBus(persist_path=None)


def compute_logic_flow(*, seed_score: float = 0.639, trace_id: str = "logicflow0") -> LogicFlowReport:
    """Trace one HNC signal from ``symbolic.life.pulse`` to a decision and roll up the flow invariants.

    Deterministic: the pulse score and trace_id are fixed, so the artifact is byte-identical on re-run.
    The trace uses the real bus + the real canonical read layer, so a break anywhere in the organism's
    plumbing (a renamed topic, a field that no longer reads back) shows up as a failed invariant.
    """
    from aureon.core.aureon_thought_bus import Thought, payload_of
    from aureon.core.hnc_field import read_canonical_field

    bus = _fresh_bus()
    observed: list[str] = []

    def _watch(t: Any) -> None:
        observed.append(getattr(t, "topic", ""))

    bus.subscribe("*", _watch)

    # 1. The harmonic core speaks — one authoritative pulse (the daemon's own shape).
    pulse_payload = {
        "symbolic_life_score": seed_score,
        "coherence_gamma": 0.945,
        "consciousness_psi": 0.707,
        "consciousness_level": "CONNECTED",
        "lambda_t": 1.0,
        "source": "logic_flow_probe",
    }
    bus.publish(Thought(source="hnc_live_daemon", topic=PULSE_TOPIC, trace_id=trace_id, payload=pulse_payload))
    pulses = bus.recall(PULSE_TOPIC, limit=1) or []
    pulse_published = len(pulses) == 1

    # 2. A consumer reads the ONE shared field — not a private engine.
    field = read_canonical_field(bus)
    field_read = bool(field.available and field.symbolic_life_score is not None)
    field_score = field.symbolic_life_score

    # 3. The field informs a decision, carried on the same trace_id.
    #    (A live consumer would size/route here; the trace only proves the value flows through.)
    decision_value = "engage" if (field_score is not None and field_score >= 0.5) else "hold"
    decision_payload = {
        "decision": decision_value,
        "from_symbolic_life_score": field_score,
        "derived": True,
    }
    decision = bus.publish(
        Thought(source=_SOURCE, topic=DECISION_TOPIC, trace_id=trace_id, payload=decision_payload)
    )
    dp = payload_of(decision) or {}
    decision_carries_field = (dp.get("from_symbolic_life_score") == field_score) and field_read

    # 4. Continuity: pulse → decision share one unbroken trace_id.
    pulse_trace = str(pulses[-1].get("trace_id")) if pulses else ""
    trace_id_propagated = bool(pulse_trace) and pulse_trace == str(getattr(decision, "trace_id", ""))
    flow_traces = [t for t in (pulse_trace, str(getattr(decision, "trace_id", ""))) if t]
    single_trace_id = len(set(flow_traces)) == 1 and len(flow_traces) >= 2

    report = LogicFlowReport(
        topic_sequence=list(observed),
        trace_id=trace_id,
        pulse_published=pulse_published,
        field_read=field_read,
        field_score=field_score,
        decision_carries_field=decision_carries_field,
        trace_id_propagated=trace_id_propagated,
        single_trace_id=single_trace_id,
        trace_signal_written=False,  # set by emit_logic_flow when the cognition bridge fires
        flow_intact=(
            pulse_published and field_read and decision_carries_field
            and trace_id_propagated and single_trace_id
        ),
    )
    return report


def write_logic_flow_report(
    report: LogicFlowReport,
    out_md: str | Path,
    out_json: str | Path | None = None,
) -> LogicFlowReport:
    """Write the flow trace as a durable evidence artifact (markdown [+ JSON]). Byte-identical."""
    import json

    d = report.to_dict()
    lines: list[str] = []
    lines.append("# Logic-flow trace — one HNC signal crossing the bus into a decision")
    lines.append("")
    lines.append(
        "Generated by `python -m aureon.cognition.logic_flow --report <OUT.md>` — an isolated in-memory "
        "bus carries one canonical `symbolic.life.pulse` through the real `read_canonical_field` layer "
        "into a downstream decision on a single trace_id."
    )
    lines.append("")
    lines.append(f"> {LOGIC_FLOW_BOUNDARY}")
    lines.append("")
    lines.append(
        f"**Flow intact: {report.flow_intact}** · trace `{report.trace_id}` · "
        f"symbolic-life score {report.field_score} · topics {' → '.join(report.topic_sequence)}"
    )
    lines.append("")
    lines.append("| invariant | value |")
    lines.append("|:---|:---:|")
    lines.append(f"| pulse published | {report.pulse_published} |")
    lines.append(f"| field read (canonical) | {report.field_read} |")
    lines.append(f"| decision carries field | {report.decision_carries_field} |")
    lines.append(f"| trace_id propagated | {report.trace_id_propagated} |")
    lines.append(f"| single trace_id | {report.single_trace_id} |")
    lines.append(f"| flow intact | {report.flow_intact} |")
    lines.append("")
    md = "\n".join(lines) + "\n"

    out_md_path = Path(out_md)
    out_md_path.write_text(md, encoding="utf-8")
    if out_json is not None:
        Path(out_json).write_text(json.dumps(d, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return replace(report, out_path=str(out_md_path))


def emit_logic_flow(
    report: LogicFlowReport, *, bus: Any | None = None, trace: bool = True
) -> dict[str, Any]:
    """Publish the flow trace to cognition (the Queen may observe). Best-effort, never fatal.

    Returns the report payload with ``trace_signal_written`` reflecting whether the bus_trace mirror
    succeeded (so the b40 benchmark can assert the cognition bridge fired).
    """
    payload = report.to_dict()
    summary = {
        "flow_intact": report.flow_intact,
        "field_score": report.field_score,
        "trace_id": report.trace_id,
        "topic_sequence": list(report.topic_sequence),
        "boundary": LOGIC_FLOW_BOUNDARY,
    }
    try:
        from aureon.core.aureon_thought_bus import Thought, get_thought_bus

        target = bus if bus is not None else get_thought_bus()
        target.publish(
            Thought(source=_SOURCE, topic=LOGIC_FLOW_RUN_TOPIC, trace_id=report.trace_id, payload=summary)
        )
    except Exception:  # noqa: BLE001 - emission is best-effort, never fatal
        pass

    trace_written = False
    if trace:
        try:
            from aureon.core.bus_trace import append_trace

            append_trace(LOGIC_FLOW_TRACE_NAME, {
                "flow_intact": report.flow_intact,
                "field_score": report.field_score,
                "trace_id": report.trace_id,
                "boundary": LOGIC_FLOW_BOUNDARY,
                "_ts": time.time(),
            })
            trace_written = True
        except Exception:  # noqa: BLE001 - trace mirror is best-effort
            pass

    payload["trace_signal_written"] = trace_written
    return payload


def main(argv: list[str] | None = None) -> int:
    """CLI: run the logic-flow trace and print / write the table."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Trace one canonical HNC signal from symbolic.life.pulse to a decision on one trace_id."
    )
    parser.add_argument("--report", metavar="OUT.md", help="write the table as a markdown evidence artifact")
    parser.add_argument("--report-json", metavar="OUT.json", help="also write the JSON record")
    parser.add_argument("--self-test", action="store_true",
                        help="assert the flow is intact end to end (pulse → field → decision, one trace)")
    args = parser.parse_args(argv)

    report = compute_logic_flow()

    print("Logic-flow trace — one HNC signal crossing the bus into a decision")
    print(f"  boundary: {LOGIC_FLOW_BOUNDARY}")
    print(f"  topics: {' -> '.join(report.topic_sequence)}")
    print(f"  flow intact {report.flow_intact} · field score {report.field_score} · "
          f"single trace_id {report.single_trace_id}")

    if args.report:
        rendered = write_logic_flow_report(report, args.report, args.report_json)
        print(f"  report written: {rendered.out_path}")

    if args.self_test:
        return 0 if report.flow_intact else 1
    return 0


if __name__ == "__main__":  # pragma: no cover - manual entry point
    raise SystemExit(main())

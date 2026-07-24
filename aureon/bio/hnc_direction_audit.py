#!/usr/bin/env python3
"""HNC direction audit — is the adaptive logic actually directed by the one canonical field?

The organism's harmonic core (HNC) produces a single authoritative signal — Λ(t), coherence Γ, the
symbolic-life score ψ and the five Auris-Conjecture pillars — published by the live daemon as
``symbolic.life.pulse`` and read through the ONE canonical layer ``aureon.core.hnc_field``
(``read_canonical_field`` / ``blend_field``). The claim this module makes falsifiable is narrow and
testable: **every adaptive consumer reads that one shared field, rather than a private coherence number
of its own.** A trading organism that says its decisions are "directed by the HNC and the Auris nodes"
must be able to *prove* the wire exists at every decision site — not assert it.

What it measures
----------------
For each adaptive consumer (the Kelly position-sizing gate, the miner brain, the Seer/Auris trading
oracle, the base Queen decision layer, and the Queen conscience veto) the audit reads the module's own
source and asks a single deterministic question: does it reference the canonical-field wire
(``read_canonical_field`` / ``blend_field`` / ``hnc_field`` / the ``symbolic.life.pulse`` topic)? A
consumer that does is **directed**; one that computes or defaults its own coherence is **siloed**. The
headline verdict ``all_directed`` is true only when every consumer is on the shared field.

This is the before/after gauge for the un-siloing work: it reads *partially directed* while the
trading path still forks onto private coherence numbers, and *fully directed* once every site reads the
one canonical field. The reading is source-level and offline, so it is deterministic and needs no live
daemon — the artifact is byte-identical on re-run.

Following the HNC logic chain, not reinventing the wheel
--------------------------------------------------------
The audit does not compute a coherence of its own — that would be the very sin it checks for. It reads
the real consumer modules and the real canonical-field API names, so the verdict tracks the actual
wiring in the tree. It pairs with ``aureon.cognition.logic_flow`` (b40), which traces the live signal
crossing the bus; this module audits that the wire is *present at every consumer*, statically and
exhaustively. The Queen may observe (``bio.hnc_direction_audit.run``).

Honest scope (stated, not decorative — enforced by tests)
---------------------------------------------------------
A **source-level wiring audit**: it proves a consumer *references the canonical field*, which is
necessary for HNC direction; it does not execute the consumer or measure how strongly the field sways a
given decision (that is b40's live trace and the per-consumer unit tests). It makes **no claim about any
person**. Pure stdlib; no import-time side effects beyond a guarded, suppressible organism heartbeat.
"""

from __future__ import annotations

import sys
import time
import uuid
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
    "HNC_DIRECTION_BOUNDARY",
    "DIRECTION_RUN_TOPIC",
    "DIRECTION_TRACE_NAME",
    "CANONICAL_WIRE_TOKENS",
    "ConsumerDirection",
    "HncDirectionReport",
    "direction_specs",
    "compute_hnc_direction",
    "write_hnc_direction_report",
    "emit_hnc_direction",
    "main",
]

DIRECTION_RUN_TOPIC: Final[str] = "bio.hnc_direction_audit.run"
DIRECTION_TRACE_NAME: Final[str] = "hnc_direction_audit"
_SOURCE: Final[str] = "hnc_direction_audit"

# The one canonical-field wire. A consumer is HNC-directed when its source references any of these —
# the shared read layer (aureon.core.hnc_field) or the authoritative bus topic it carries.
CANONICAL_WIRE_TOKENS: Final[tuple[str, ...]] = (
    "read_canonical_field",
    "blend_field",
    "hnc_field",
    "symbolic.life.pulse",
)

HNC_DIRECTION_BOUNDARY: Final[str] = (
    "Source-level wiring audit: it proves each adaptive consumer REFERENCES the one canonical HNC field "
    "(aureon.core.hnc_field / the symbolic.life.pulse topic) rather than a private coherence number - a "
    "necessary condition for 'directed by the HNC and Auris nodes'. It does NOT execute the consumer, "
    "does NOT measure how strongly the field sways a decision (that is the b40 live trace), and is NOT a "
    "claim about any person."
)


@dataclass(frozen=True)
class ConsumerDirection:
    """Whether one adaptive consumer is wired to the canonical HNC field, and by which token."""

    name: str
    module: str  # repo-relative source path
    directed: bool
    via: str  # the canonical wire token found, or "" when siloed
    present: bool  # the source file exists and was read
    note: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class HncDirectionReport:
    """The consolidated direction audit across every adaptive consumer."""

    consumers: list[dict[str, Any]]
    n_total: int
    n_directed: int
    n_siloed: int
    directed_fraction: float
    all_directed: bool
    siloed_names: list[str]
    boundary: str = HNC_DIRECTION_BOUNDARY
    out_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def direction_specs() -> tuple[tuple[str, str, str], ...]:
    """The adaptive consumers to audit: (name, repo-relative module path, note).

    These are the decision sites where the audit found forked/private coherence — the ones that must
    read the one canonical field for the organism's adaptive logic to be HNC/Auris-directed end to end.
    """
    return (
        ("kelly_gate", "aureon/utils/adaptive_prime_profit_gate.py",
         "position-sizing safety buffer"),
        ("miner_brain", "aureon/utils/aureon_miner_brain.py",
         "adaptive learning / quantum-context cycle"),
        ("seer_oracle", "aureon/intelligence/aureon_seer.py",
         "Auris trading oracle consensus"),
        ("queen_layer", "aureon/queen/queen_layer.py",
         "base Queen first-pass decision/routing"),
        ("queen_conscience", "aureon/queen/queen_conscience.py",
         "Queen 4th-pass substrate-coherence veto"),
    )


def _probe_source(module_path: Path) -> tuple[bool, str, bool]:
    """Read a consumer's source and report (directed, via_token, present).

    Deterministic and offline: a consumer is directed when its source references any
    ``CANONICAL_WIRE_TOKENS`` entry. Guarded — a missing/unreadable file is reported as absent, never
    raised.
    """
    try:
        if not module_path.exists():
            return (False, "", False)
        text = module_path.read_text(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001 - a missing consumer is a value, never a crash
        return (False, "", False)
    for token in CANONICAL_WIRE_TOKENS:
        if token in text:
            return (True, token, True)
    return (False, "", True)


def compute_hnc_direction(*, repo_root: Path | None = None) -> HncDirectionReport:
    """Audit every adaptive consumer for the canonical-field wire and roll up the verdict.

    ``directed_fraction`` is the share of consumers on the one shared field (→ 1.0 when fully directed);
    ``all_directed`` is the headline boolean the un-siloing work must turn true. ``siloed_names`` lists
    the consumers still forking onto a private coherence number — the exact work list.
    """
    root = repo_root if repo_root is not None else _REPO_ROOT
    consumers: list[ConsumerDirection] = []
    for name, rel, note in direction_specs():
        directed, via, present = _probe_source(root / rel)
        consumers.append(ConsumerDirection(
            name=name, module=rel, directed=directed, via=via, present=present, note=note,
        ))

    n_total = len(consumers)
    n_directed = sum(1 for c in consumers if c.directed)
    n_siloed = n_total - n_directed
    siloed_names = [c.name for c in consumers if not c.directed]
    return HncDirectionReport(
        consumers=[c.to_dict() for c in consumers],
        n_total=n_total,
        n_directed=n_directed,
        n_siloed=n_siloed,
        directed_fraction=(n_directed / n_total) if n_total else 0.0,
        all_directed=(n_siloed == 0 and n_total > 0),
        siloed_names=siloed_names,
    )


def write_hnc_direction_report(
    report: HncDirectionReport,
    out_md: str | Path,
    out_json: str | Path | None = None,
) -> HncDirectionReport:
    """Write the direction audit as a durable evidence artifact (markdown [+ JSON]). Byte-identical."""
    import json

    d = report.to_dict()
    lines: list[str] = []
    lines.append("# HNC direction audit — is the adaptive logic directed by the one canonical field?")
    lines.append("")
    lines.append(
        "Generated by `python -m aureon.bio.hnc_direction_audit --report <OUT.md>` — a source-level audit "
        "of every adaptive consumer for the canonical-field wire (`read_canonical_field` / `blend_field` "
        "/ the `symbolic.life.pulse` topic). A consumer that references it is HNC-directed; one that "
        "computes or defaults its own coherence is siloed."
    )
    lines.append("")
    lines.append(f"> {HNC_DIRECTION_BOUNDARY}")
    lines.append("")
    lines.append(
        f"**{report.n_directed}/{report.n_total} consumers directed** "
        f"(directed fraction {report.directed_fraction:.3f}) · all directed: {report.all_directed}"
        + (f" · siloed: {', '.join(report.siloed_names)}" if report.siloed_names else "")
    )
    lines.append("")
    lines.append("| consumer | module | directed | via | note |")
    lines.append("|:---|:---|:---:|:---|:---|")
    for c in report.consumers:
        via = c["via"] or ("—" if c["present"] else "absent")
        lines.append(
            f"| {c['name']} | `{c['module']}` | {'yes' if c['directed'] else 'no'} | {via} | {c['note']} |"
        )
    lines.append("")
    md = "\n".join(lines) + "\n"

    out_md_path = Path(out_md)
    out_md_path.write_text(md, encoding="utf-8")
    if out_json is not None:
        Path(out_json).write_text(json.dumps(d, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return replace(report, out_path=str(out_md_path))


def emit_hnc_direction(
    report: HncDirectionReport, *, bus: Any | None = None, trace: bool = True
) -> dict[str, Any]:
    """Publish the direction audit to cognition (the Queen may observe). Best-effort, never fatal."""
    payload = report.to_dict()
    summary = {
        "n_directed": report.n_directed,
        "n_total": report.n_total,
        "directed_fraction": report.directed_fraction,
        "all_directed": report.all_directed,
        "siloed_names": list(report.siloed_names),
        "boundary": HNC_DIRECTION_BOUNDARY,
    }
    try:
        from aureon.core.aureon_thought_bus import Thought, get_thought_bus

        target = bus if bus is not None else get_thought_bus()
        target.publish(
            Thought(source=_SOURCE, topic=DIRECTION_RUN_TOPIC, trace_id=uuid.uuid4().hex, payload=summary)
        )
    except Exception:  # noqa: BLE001 - emission is best-effort, never fatal
        pass

    if trace:
        try:
            from aureon.core.bus_trace import append_trace

            append_trace(DIRECTION_TRACE_NAME, {
                "n_directed": report.n_directed,
                "n_total": report.n_total,
                "directed_fraction": report.directed_fraction,
                "all_directed": report.all_directed,
                "boundary": HNC_DIRECTION_BOUNDARY,
                "_ts": time.time(),
            })
        except Exception:  # noqa: BLE001 - trace mirror is best-effort
            pass

    return payload


def main(argv: list[str] | None = None) -> int:
    """CLI: run the HNC direction audit and print / write the table."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Audit whether every adaptive consumer is wired to the one canonical HNC field."
    )
    parser.add_argument("--report", metavar="OUT.md", help="write the table as a markdown evidence artifact")
    parser.add_argument("--report-json", metavar="OUT.json", help="also write the JSON record")
    parser.add_argument("--self-test", action="store_true",
                        help="assert every adaptive consumer is directed by the canonical field")
    args = parser.parse_args(argv)

    report = compute_hnc_direction()

    print("HNC direction audit — adaptive logic directed by the one canonical field?")
    print(f"  boundary: {HNC_DIRECTION_BOUNDARY}")
    print(f"  {report.n_directed}/{report.n_total} directed (fraction {report.directed_fraction:.3f}) · "
          f"all directed {report.all_directed}")
    if report.siloed_names:
        print(f"  siloed: {', '.join(report.siloed_names)}")

    if args.report:
        rendered = write_hnc_direction_report(report, args.report, args.report_json)
        print(f"  report written: {rendered.out_path}")

    if args.self_test:
        return 0 if report.all_directed else 1
    return 0


if __name__ == "__main__":  # pragma: no cover - manual entry point
    raise SystemExit(main())

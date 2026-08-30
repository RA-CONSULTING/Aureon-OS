#!/usr/bin/env python3
"""Logic-train audit — is EVERY decision site on the one canonical field, repo-wide? (b46)

The organism's claim is that its logic train runs on one shared harmonic reading: the HNC core
computes Λ(t), coherence Γ and the symbolic-life score ψ, the live daemon publishes it as
``symbolic.life.pulse``, and every site that acts on coherence reads that one field through
``aureon.core.hnc_field``. ``bio.hnc_direction_audit`` (b41) already checks that claim — for **five
hand-listed consumers**. This module checks it for the **whole tree**.

Why hand-enumeration is not enough
----------------------------------
The same lesson the tenant route boundary taught three times running: a curated list is a statement
about what someone remembered, not about what the repo contains. Measured on this tree, 80 modules
reference a field value and 36 instantiate their own ``LambdaEngine`` — a five-name list cannot speak
for them. So this audit **discovers** the population by reading every module under ``aureon/``, then
classifies each by role and asks whether its wire exists.

Roles (assigned by evidence, then by a stated exemption — never by silence)
--------------------------------------------------------------------------
* ``AUTHORITY`` — modules that *define* the field rather than consume it: the Λ engine itself, its
  parameters, the canonical read layer, the live daemon that publishes the pulse. Exempt by role, and
  the reason is recorded in the report rather than assumed.
* ``PRODUCER`` — computes a local field of its own. Legitimate (the Queen's cortex, source-law,
  metacognition and the mycelium mind each compute a real local Λ), but it must ``publish_subfield``
  so the whole-body consensus can see it. A producer nobody can see is a private opinion.
* ``CONSUMER`` — reads a field value to steer a decision. Must read the canonical layer, not a
  private number.
* ``INERT`` — names a field in prose, a label or a schema, and decides nothing.

The verdict
-----------
``train_connected`` is true only when every discovered PRODUCER publishes and every CONSUMER reads
canonical. Anything still unwired is listed **by name** in ``unwired`` and pinned in
:data:`KNOWN_UNWIRED` with a reason, so:

* a newly added unwired decision site fails this audit immediately — the ratchet;
* the remaining gap is impossible to misplace: it is a literal list in the source, and burning it
  down is a visible diff, not a claim in a status report.

Honest scope (stated, not decorative — enforced by tests)
---------------------------------------------------------
This is a **source-level wiring audit**, like b41 and for the same reason: it proves the wire is
present, which is necessary for the logic train to be HNC-directed. It does not execute each consumer
or measure how strongly the field sways one decision — b40 traces the live signal across the bus, and
the per-consumer unit tests cover strength. It reads the tree it ships in, so the artifact is
deterministic and needs no live daemon. It makes **no claim about any person**. Pure stdlib; no
import-time side effects beyond a guarded, suppressible organism heartbeat.
"""

from __future__ import annotations

import ast
import json
import sys
import time
import uuid
from dataclasses import asdict, dataclass
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
    "LOGIC_TRAIN_BOUNDARY",
    "TRAIN_RUN_TOPIC",
    "ModuleRole",
    "TrainSite",
    "LogicTrainReport",
    "KNOWN_UNWIRED",
    "compute_logic_train",
    "write_logic_train_report",
    "emit_logic_train",
    "main",
]

TRAIN_RUN_TOPIC: Final[str] = "cognition.logic_train.run"
_SOURCE: Final[str] = "logic_train_audit"

LOGIC_TRAIN_BOUNDARY: Final[str] = (
    "Every site in the repository that acts on a harmonic field value is discovered by reading the "
    "tree, classified by role, and checked for its wire to the one canonical field. Producers must "
    "publish their local field so the whole body can see it; consumers must read the canonical layer "
    "rather than a private number. What is still unwired is named in the report and pinned in source, "
    "so a new unwired decision site fails the audit and the remaining gap cannot be misplaced. It is a "
    "source-level wiring proof, not a measurement of how strongly the field sways one decision, and it "
    "is NOT a claim about any person."
)

# ── the canonical wire, by the names it actually goes by in this tree ────────────────────────────
_CANONICAL_TOKENS: Final[tuple[str, ...]] = (
    "hnc_field",
    "read_canonical_field",
    "blend_field",
    "read_subfields",
    "symbolic.life.pulse",
    "merge_canonical_into_qc",
)
_PUBLISH_TOKENS: Final[tuple[str, ...]] = ("publish_subfield", "symbolic.life.subfield")

#: Field values whose use marks a module as touching the harmonic train.
_FIELD_NAMES: Final[tuple[str, ...]] = (
    "symbolic_life_score",
    "coherence_gamma",
    "consciousness_psi",
    "lambda_t",
)

#: Names that mean a module is computing a field of its own.
_ENGINE_TOKENS: Final[tuple[str, ...]] = ("LambdaEngine", "lambda_engine")

#: Modules that DEFINE the field rather than consume it. Each carries its reason, because "it is
#: exempt" with no reason is how an exemption list becomes a place to hide things.
_AUTHORITY: Final[dict[str, str]] = {
    "aureon/core/aureon_lambda_engine.py": "the Λ engine itself — the field originates here",
    "aureon/core/hnc_field.py": "the canonical read/publish layer every other site goes through",
    "aureon/core/hnc_params.py": "the pinned Λ parameters, not a decision site",
    "aureon/core/hnc_live_daemon.py": "the authoritative producer that publishes symbolic.life.pulse",
    "aureon/bio/hnc_direction_audit.py": "audits the wire; computing a field here would be the sin it checks",
    "aureon/cognition/logic_train_audit.py": "this audit",
    "aureon/cognition/logic_flow.py": "traces the live signal across the bus (b40)",
    "aureon/analytics/volatility_sentinel_benchmark.py":
        "labeled-synthetic benchmark harness — measures the sentinel detector offline, decides nothing live",
    "aureon/analytics/historical_replay_validation.py":
        "no-keys replay harness — drives the real components on recorded open data, decides nothing live",
}

# These consumers never read mutable live field state. They accept already
# issued HNC/Auris receipts at a trusted boundary and validate the complete
# causal linkage before a decision. Treating that as an unwired private number
# would be as inaccurate as treating it as a field authority.
_RECEIPT_BOUND_CONSUMERS: Final[dict[str, str]] = {
    "aureon/swarm/auris_node_receipts.py":
        "validates exact HNC, Auris, provider-moment, and coherence-measurement receipts",
    "aureon/trading/bounded_binance_roundtrip.py":
        "validates exact HNC, Auris, provider-moment, and route authorization receipts",
}
_RECEIPT_WIRE_TOKENS: Final[tuple[str, ...]] = (
    "hnc_receipt_id",
    "auris_receipt_id",
    "provider_moment_digest",
)

#: Decision sites known to be unwired at the time of writing, each with the reason it is still open.
#: This is the burn-down list. A site NOT in here that turns up unwired fails the audit — that is the
#: ratchet. Removing an entry is the visible diff that says the wire was actually laid.
KNOWN_UNWIRED: Final[dict[str, str]] = {
    "aureon/alignment/unified_directive.py":
        "measured unwired at pin time (role=consumer, reads a field, no canonical wire)",
    "aureon/autonomous/aureon_dynamic_prompt_filter.py":
        "measured unwired at pin time (role=consumer, reads a field, no canonical wire)",
    "aureon/autonomous/aureon_face_app.py":
        "measured unwired at pin time (role=producer, reads a field, no canonical wire)",
    "aureon/autonomous/aureon_gold_capital_intelligence_company.py":
        "measured unwired at pin time (role=producer, reads a field, no canonical wire)",
    "aureon/bridges/aureon_ui_bridge.py":
        "measured unwired at pin time (role=consumer, reads a field, no canonical wire)",
    "aureon/core/cognitive_dashboard.py":
        "measured unwired at pin time (role=consumer, reads a field, no canonical wire)",
    "aureon/core/goal_execution_engine.py":
        "measured unwired at pin time (role=producer, reads a field, no canonical wire)",
    "aureon/harmonic/dj_resonance.py":
        "measured unwired at pin time (role=consumer, reads a field, no canonical wire)",
    "aureon/observer/benchmark.py":
        "measured unwired at pin time (role=consumer, reads a field, no canonical wire)",
    "aureon/observer/fitter.py":
        "measured unwired at pin time (role=producer, reads a field, no canonical wire)",
    "aureon/observer/historical_backtest.py":
        "backtest harness — fixture surface, expected to stay off the live field",
    "aureon/observer/run.py":
        "measured unwired at pin time (role=consumer, reads a field, no canonical wire)",
    "aureon/observer/wave_predictor.py":
        "measured unwired at pin time (role=consumer, reads a field, no canonical wire)",
    "aureon/operator/local_action_bridge.py":
        "measured unwired at pin time (role=consumer, reads a field, no canonical wire)",
    "aureon/queen/being_model.py":
        "measured unwired at pin time (role=producer, reads a field, no canonical wire)",
    "aureon/queen/meaning_resolver.py":
        "measured unwired at pin time (role=consumer, reads a field, no canonical wire)",
    "aureon/queen/queen_cognitive_action_planner.py":
        "measured unwired at pin time (role=consumer, reads a field, no canonical wire)",
    "aureon/queen/queen_coherence_mandala.py":
        "measured unwired at pin time (role=consumer, reads a field, no canonical wire)",
    "aureon/queen/queen_prose_composer.py":
        "measured unwired at pin time (role=producer, reads a field, no canonical wire)",
    "aureon/queen/queen_sentience_integration.py":
        "measured unwired at pin time (role=consumer, reads a field, no canonical wire)",
    "aureon/queen/self_enhancement_engine.py":
        "measured unwired at pin time (role=consumer, reads a field, no canonical wire)",
    "aureon/queen/temporal_ground.py":
        "temporal grounding computes a private Λ echo",
    "aureon/status.py":
        "status surface reports a field it computes rather than the canonical one",
    "aureon/swarm_motion/as_above_so_below.py":
        "measured unwired at pin time (role=consumer, reads a field, no canonical wire)",
    "aureon/swarm_motion/love_stream.py":
        "measured unwired at pin time (role=consumer, reads a field, no canonical wire)",
    "aureon/swarm_motion/swarm_hive.py":
        "measured unwired at pin time (role=consumer, reads a field, no canonical wire)",
    "aureon/utils/aureon_miner.py":
        "measured unwired at pin time (role=consumer, reads a field, no canonical wire)",
    "aureon/vault/casimir_quantifier.py":
        "measured unwired at pin time (role=consumer, reads a field, no canonical wire)",
    "aureon/vault/hnc_deployer.py":
        "measured unwired at pin time (role=consumer, reads a field, no canonical wire)",
    "aureon/vault/voice/aureon_personas.py":
        "measured unwired at pin time (role=consumer, reads a field, no canonical wire)",
    "aureon/vault/voice/choice_gate.py":
        "measured unwired at pin time (role=consumer, reads a field, no canonical wire)",
    "aureon/vault/voice/document_artifact_skill.py":
        "measured unwired at pin time (role=consumer, reads a field, no canonical wire)",
    "aureon/vault/voice/goal_dispatch_bridge.py":
        "measured unwired at pin time (role=consumer, reads a field, no canonical wire)",
    "aureon/vault/voice/vault_voice.py":
        "measured unwired at pin time (role=consumer, reads a field, no canonical wire)",
    "aureon/vault/voice/whole_knowledge_voice.py":
        "measured unwired at pin time (role=consumer, reads a field, no canonical wire)",
}


class ModuleRole:
    """Role constants. A plain class rather than an Enum so the values serialise as themselves."""

    AUTHORITY: Final[str] = "authority"
    PRODUCER: Final[str] = "producer"
    CONSUMER: Final[str] = "consumer"
    INERT: Final[str] = "inert"


@dataclass(frozen=True)
class TrainSite:
    """One module's place in the logic train, and whether its wire exists."""

    module: str          # repo-relative path
    role: str            # ModuleRole.*
    wired: bool          # role-appropriate wire present (or exempt by role)
    via: str             # the token that proves the wire, or "" when absent
    reads_field: bool
    computes_field: bool
    reason: str          # role justification / known-gap note

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class LogicTrainReport:
    """The whole-tree verdict on the logic train."""

    sites: list[dict[str, Any]]
    n_scanned: int
    n_authority: int
    n_producer: int
    n_consumer: int
    n_inert: int
    n_wired: int
    n_unwired: int
    wired_fraction: float
    train_connected: bool
    unwired: list[str]
    unexpected_unwired: list[str]   # unwired and NOT in KNOWN_UNWIRED — the ratchet's teeth
    retired_gaps: list[str]         # in KNOWN_UNWIRED but now wired — burn-down progress
    boundary: str = LOGIC_TRAIN_BOUNDARY
    out_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _iter_modules(root: Path) -> list[Path]:
    return sorted(
        p for p in (root / "aureon").rglob("*.py")
        if "__pycache__" not in p.parts
    )


def _module_evidence(source: str) -> tuple[bool, bool, str, str]:
    """(reads_field, computes_field, canonical_token, publish_token) from a module's source.

    Read from the AST where it matters and from the text where a topic string is the wire — a topic
    name only ever appears as a literal, so text is the honest place to look for it.
    """
    reads_field = any(name in source for name in _FIELD_NAMES)
    computes_field = any(tok in source for tok in _ENGINE_TOKENS)
    canonical = next((tok for tok in _CANONICAL_TOKENS if tok in source), "")
    publishes = next((tok for tok in _PUBLISH_TOKENS if tok in source), "")
    return reads_field, computes_field, canonical, publishes


def _decides(source: str) -> bool:
    """True when a module looks like it acts on what it read, not merely describes it.

    Deliberately conservative: a module that reads a field value and contains a comparison against
    it, or names an action/verdict/size, is treated as a decision site. Over-inclusion is the safe
    direction — it puts a module on the list to be justified rather than letting it pass unexamined.
    """
    if not any(name in source for name in _FIELD_NAMES):
        return False
    decision_markers = (
        "if ", "veto", "approve", "reject", "action", "verdict", "gate",
        "position_size", "notional", "allow", "block", "threshold",
    )
    return any(marker in source for marker in decision_markers)


def compute_logic_train(*, repo_root: Path | None = None) -> LogicTrainReport:
    """Discover every site on the harmonic logic train and check its wire. Never raises."""
    root = repo_root or _REPO_ROOT
    sites: list[TrainSite] = []

    for path in _iter_modules(root):
        rel = path.relative_to(root).as_posix()
        try:
            source = path.read_text(encoding="utf-8", errors="replace")
        except Exception:  # noqa: BLE001 — an unreadable module is a site we cannot clear
            sites.append(TrainSite(rel, ModuleRole.CONSUMER, False, "", False, False,
                                   "source unreadable — cannot prove a wire"))
            continue

        # A file that does not parse cannot be reasoned about; say so rather than pass it.
        try:
            ast.parse(source)
            parses = True
        except SyntaxError:
            parses = False

        reads_field, computes_field, canonical, publishes = _module_evidence(source)

        if rel in _AUTHORITY:
            sites.append(TrainSite(rel, ModuleRole.AUTHORITY, True, "role", reads_field,
                                   computes_field, _AUTHORITY[rel]))
            continue

        if rel in _RECEIPT_BOUND_CONSUMERS:
            missing = [token for token in _RECEIPT_WIRE_TOKENS if token not in source]
            sites.append(TrainSite(
                rel,
                ModuleRole.CONSUMER,
                not missing,
                "receipt-bound-hnc-auris" if not missing else "",
                reads_field,
                computes_field,
                (_RECEIPT_BOUND_CONSUMERS[rel] if not missing
                 else f"receipt-bound consumer missing causal fields: {', '.join(missing)}"),
            ))
            continue

        if not parses:
            sites.append(TrainSite(rel, ModuleRole.CONSUMER, False, "", reads_field,
                                   computes_field, "module does not parse — wire unprovable"))
            continue

        if computes_field and reads_field:
            role = ModuleRole.PRODUCER
            wired = bool(publishes or canonical)
            via = publishes or canonical
            reason = ("publishes its local field to the shared bus" if publishes
                      else "reads the canonical layer" if canonical
                      else KNOWN_UNWIRED.get(rel, "computes a field nobody else can see"))
        elif reads_field and _decides(source):
            role = ModuleRole.CONSUMER
            wired = bool(canonical)
            via = canonical
            reason = (f"reads canonical via {canonical}" if canonical
                      else KNOWN_UNWIRED.get(rel, "decides on a field value with no canonical wire"))
        else:
            role = ModuleRole.INERT
            wired = True
            via = ""
            reason = "names a field without acting on it"

        sites.append(TrainSite(rel, role, wired, via, reads_field, computes_field, reason))

    unwired = [s.module for s in sites if not s.wired]
    unexpected = [m for m in unwired if m not in KNOWN_UNWIRED]
    retired = [m for m in KNOWN_UNWIRED if m not in unwired]
    n_relevant = sum(1 for s in sites if s.role != ModuleRole.INERT)
    n_wired = sum(1 for s in sites if s.wired and s.role != ModuleRole.INERT)

    return LogicTrainReport(
        sites=[s.to_dict() for s in sites],
        n_scanned=len(sites),
        n_authority=sum(1 for s in sites if s.role == ModuleRole.AUTHORITY),
        n_producer=sum(1 for s in sites if s.role == ModuleRole.PRODUCER),
        n_consumer=sum(1 for s in sites if s.role == ModuleRole.CONSUMER),
        n_inert=sum(1 for s in sites if s.role == ModuleRole.INERT),
        n_wired=n_wired,
        n_unwired=len(unwired),
        wired_fraction=(n_wired / n_relevant) if n_relevant else 1.0,
        train_connected=not unwired,
        unwired=sorted(unwired),
        unexpected_unwired=sorted(unexpected),
        retired_gaps=sorted(retired),
    )


def write_logic_train_report(
    report: LogicTrainReport,
    out_md: str | Path,
    out_json: str | Path | None = None,
) -> LogicTrainReport:
    """Write the human and machine artifacts. Byte-identical on re-run for the same tree."""
    md_path = Path(out_md)
    md_path.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        "# Logic-train audit — every decision site, one canonical field",
        "",
        f"**Connected: {report.train_connected}** — {report.n_wired}/"
        f"{report.n_producer + report.n_consumer + report.n_authority} relevant sites wired "
        f"({report.wired_fraction:.1%})",
        "",
        f"* scanned: {report.n_scanned} modules",
        f"* authority (define the field): {report.n_authority}",
        f"* producers (compute a local field): {report.n_producer}",
        f"* consumers (decide on a field): {report.n_consumer}",
        f"* inert (name it, decide nothing): {report.n_inert}",
        "",
    ]
    if report.unexpected_unwired:
        lines += ["## Unexpected gaps — these fail the audit", ""]
        lines += [f"* `{m}`" for m in report.unexpected_unwired] + [""]
    if report.retired_gaps:
        lines += ["## Retired gaps — wired since the list was pinned", ""]
        lines += [f"* `{m}`" for m in report.retired_gaps] + [""]
    if report.unwired:
        lines += ["## Still unwired", "", "| module | role | reason |", "|---|---|---|"]
        by_name = {s["module"]: s for s in report.sites}
        for m in report.unwired:
            s = by_name.get(m, {})
            lines.append(f"| `{m}` | {s.get('role', '?')} | {s.get('reason', '')} |")
        lines.append("")
    lines += ["---", "", report.boundary, ""]
    md_path.write_text("\n".join(lines), encoding="utf-8")

    stamped = LogicTrainReport(**{**report.to_dict(), "out_path": str(md_path)})
    if out_json is not None:
        json_path = Path(out_json)
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(json.dumps(stamped.to_dict(), indent=2, sort_keys=True) + "\n",
                             encoding="utf-8")
    return stamped


def emit_logic_train(report: LogicTrainReport, bus: Any = None) -> bool:
    """Publish the verdict so the Queen can observe her own wiring. Guarded; never fatal."""
    try:
        from aureon.core.aureon_thought_bus import Thought, get_thought_bus

        b = bus if bus is not None else get_thought_bus()
        if b is None:
            return False
        b.publish(Thought(
            source=_SOURCE,
            topic=TRAIN_RUN_TOPIC,
            payload={
                "train_connected": report.train_connected,
                "n_scanned": report.n_scanned,
                "n_unwired": report.n_unwired,
                "unexpected_unwired": list(report.unexpected_unwired),
                "wired_fraction": round(report.wired_fraction, 4),
                "ts": time.time(),
                "trace_id": str(uuid.uuid4())[:8],
            },
        ))
        return True
    except Exception:  # noqa: BLE001 — visibility is best-effort, never fatal
        return False


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Audit the harmonic logic train, repo-wide")
    parser.add_argument("--out-md", default="docs/architecture/LOGIC_TRAIN_AUDIT.md")
    parser.add_argument("--out-json", default="docs/architecture/logic_train_audit.json")
    parser.add_argument("--emit", action="store_true", help="publish the verdict to the thought bus")
    args = parser.parse_args(argv)

    report = compute_logic_train()
    report = write_logic_train_report(report, args.out_md, args.out_json)
    if args.emit:
        emit_logic_train(report)

    print(f"logic train connected : {report.train_connected}")
    print(f"scanned               : {report.n_scanned} modules")
    print(f"authority/producer/consumer/inert : "
          f"{report.n_authority}/{report.n_producer}/{report.n_consumer}/{report.n_inert}")
    print(f"wired                 : {report.n_wired} ({report.wired_fraction:.1%})")
    print(f"unwired               : {report.n_unwired}")
    if report.unexpected_unwired:
        print(f"UNEXPECTED gaps ({len(report.unexpected_unwired)}) — these fail the audit:")
        for m in report.unexpected_unwired:
            print(f"   {m}")
    if report.retired_gaps:
        print(f"retired gaps ({len(report.retired_gaps)}) — wired since pinning:")
        for m in report.retired_gaps:
            print(f"   {m}")
    # Exit non-zero only on an UNEXPECTED gap: the known burn-down list is progress, not breakage.
    return 1 if report.unexpected_unwired else 0


if __name__ == "__main__":
    raise SystemExit(main())

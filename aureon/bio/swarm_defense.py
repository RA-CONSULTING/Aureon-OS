#!/usr/bin/env python3
"""Swarm defense — the bee-ball quorum response of Aureon's cognitive immune layer.

The integrity guard (`aureon/bio/integrity_guard.py`, b34) is a *sensor*: it detects parasite logic and
emits ``bio.integrity_guard.run``, but nothing acts on the alarm. A hive does not defend with one bee —
when a hornet enters, hundreds of honeybees independently converge and *ball* it, and the defense holds
even if some bees are lost. Crucially, **no single bee and no queen directs it**: the response is
leaderless, which is exactly what makes it resilient to a compromised leader.

This module is the immune layer's *effector* arm. On a detected breach it builds a ``ThreatReport`` and
fans out ``N`` independent **defenders**; each re-verifies the threat and votes; neutralization is
confirmed only on a **majority quorum**. It is Byzantine-tolerant by construction: a *minority* of
compromised (wrong-voting) or silenced (abstaining) defenders cannot flip the verdict — the swarm is
overwhelmed only when a *majority* is compromised, and that bound is reported honestly. There is
deliberately **no authority in the command path** (the Queen may observe or veto on its own channel, but
cannot command the ball), because a co-opted leader is the very parasite we defend against.

Honest limits (stated, not decorative)
--------------------------------------
This is a **deterministic model of a swarm defense**, not a live 44k-bot deployment, and a
detection-and-confirmation aid, **not a security proof**. Confirmed neutralization is **advisory and
reversible** (raise the alarm / isolate), never a destructive act. It makes **no claim about any
person**. Pure stdlib; no network, no import-time side effects. The quorum tally mirrors the idiom of
``aureon/vault/auris_metacognition.py`` and the threat shape mirrors ``aureon/vault/white_cell.py``.
"""

from __future__ import annotations

import time
import uuid
from collections import Counter
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any, Final

# --- guarded organism link (suppressible; never fatal) — the "I exist" heartbeat ---
try:  # pragma: no cover - environment-dependent, best-effort
    from aureon.core.aureon_baton_link import link_system

    link_system(__name__)
except Exception:  # noqa: BLE001 - the organ must import in any environment
    pass

__all__ = [
    "SWARM_DEFENSE_BOUNDARY",
    "DEFENSE_RUN_TOPIC",
    "DEFENSE_TRACE_NAME",
    "DEFAULT_N_DEFENDERS",
    "ThreatReport",
    "DefenderVote",
    "DefenseResult",
    "DEFAULT_DEFENDERS",
    "mount_defense",
    "defend_from_guard_report",
    "on_breach",
    "write_defense_report",
    "emit_defense",
    "main",
]

DEFENSE_RUN_TOPIC: Final[str] = "bio.swarm_defense.run"
DEFENSE_TRACE_NAME: Final[str] = "swarm_defense"
_SOURCE: Final[str] = "swarm_defense"

SWARM_DEFENSE_BOUNDARY: Final[str] = (
    "Leaderless quorum swarm defense: on a detected breach, many independent defenders each re-verify "
    "the threat and neutralization is confirmed only by a majority vote - Byzantine-tolerant to a "
    "minority of compromised or silent defenders, with no single authority in the command path. "
    "Confirmed neutralization is advisory and reversible; a deterministic model and a "
    "detection-and-confirmation aid, NOT a security proof, and NOT a claim about any person."
)

DEFAULT_N_DEFENDERS: Final[int] = 9  # echoes the 9-node Auris panel
_KNOWN_THREAT_KINDS: Final[frozenset[str]] = frozenset({"mutated_invariant", "injected_instruction"})

# Independent defender names (flavor only; each votes on its own, no shared mutable state).
_DEFENDER_NAMES: Final[tuple[str, ...]] = (
    "forager", "guard-bee", "scout", "nurse", "drone",
    "fanner", "undertaker", "waggle-dancer", "queen-cup-tender",
)


@dataclass(frozen=True)
class ThreatReport:
    """A detected threat handed to the swarm (mirrors ``white_cell.ThreatReport`` fields for interop)."""

    threat_id: str
    kind: str            # "mutated_invariant" | "injected_instruction" | "unknown"
    description: str
    severity: int        # 0 = benign/no threat; >= 1 = a real threat to confirm

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DefenderVote:
    """One defender's independent verdict on the threat."""

    defender: str
    verdict: str         # "THREAT" | "CLEAR" | "ABSTAIN"
    confidence: float
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DefenseResult:
    """The consolidated leaderless-quorum defense verdict."""

    threat_id: str
    kind: str
    n_defenders: int
    n_threat: int
    n_clear: int
    n_abstain: int
    quorum: int
    confirmed: bool
    confidence: float
    tolerated_faults: int
    leaderless: bool
    votes: list[DefenderVote]
    boundary: str = SWARM_DEFENSE_BOUNDARY
    out_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["votes"] = [v.to_dict() for v in self.votes]
        return d


def _honest_verdict(threat: ThreatReport) -> str:
    """The correct verdict an honest defender reaches: a real threat is THREAT, everything else CLEAR."""
    is_real = threat.severity >= 1 and threat.kind in _KNOWN_THREAT_KINDS
    return "THREAT" if is_real else "CLEAR"


def _make_defender(name: str):
    """Build one independent defender callable. It votes honestly unless marked faulty or silent."""

    def _defender(threat: ThreatReport, *, faulty: bool = False, silent: bool = False) -> DefenderVote:
        if silent:  # an unreachable / lost bee
            return DefenderVote(defender=name, verdict="ABSTAIN", confidence=0.0, reason="unreachable")
        honest = _honest_verdict(threat)
        if faulty:  # a compromised bee votes the wrong way
            verdict = "CLEAR" if honest == "THREAT" else "THREAT"
            return DefenderVote(defender=name, verdict=verdict, confidence=0.9, reason="compromised")
        return DefenderVote(defender=name, verdict=honest, confidence=0.9,
                            reason=f"{name} independently judged kind={threat.kind!r} severity={threat.severity}")

    return _defender


DEFAULT_DEFENDERS: Final[tuple[Any, ...]] = tuple(_make_defender(n) for n in _DEFENDER_NAMES)


def _tally(votes: list[DefenderVote], *, n_defenders: int) -> tuple[bool, float, int]:
    """Majority-quorum tally (idiom from ``auris_metacognition._tally``).

    Quorum is a strict majority over ALL defenders (``n // 2 + 1``), so silence counts against
    confirmation (fail-safe). Confidence follows the Auris tiers on the fraction that voted THREAT.
    Returns ``(confirmed, confidence, quorum)``.
    """
    quorum = n_defenders // 2 + 1
    counts = Counter(v.verdict for v in votes)
    n_threat = counts.get("THREAT", 0)
    confirmed = n_threat >= quorum
    if n_threat < quorum:
        confidence = 0.3
    elif n_threat <= (7 * n_defenders) // 9:  # 5..7 of 9 → the middle tier
        confidence = 0.7
    else:
        confidence = 0.95
    return confirmed, confidence, quorum


def mount_defense(
    threat: ThreatReport,
    *,
    defenders: tuple[Any, ...] = DEFAULT_DEFENDERS,
    faulty_idx: tuple[int, ...] = (),
    silent_idx: tuple[int, ...] = (),
) -> DefenseResult:
    """Fan out the defenders over ``threat`` and confirm neutralization only on a majority quorum.

    ``faulty_idx`` / ``silent_idx`` mark defenders (by position) that are compromised or lost — used to
    exercise the Byzantine-tolerance bound deterministically.
    """
    n = len(defenders)
    faulty = set(faulty_idx)
    silent = set(silent_idx)
    votes = [
        d(threat, faulty=(i in faulty), silent=(i in silent))
        for i, d in enumerate(defenders)
    ]
    confirmed, confidence, quorum = _tally(votes, n_defenders=n)
    counts = Counter(v.verdict for v in votes)

    return DefenseResult(
        threat_id=threat.threat_id,
        kind=threat.kind,
        n_defenders=n,
        n_threat=counts.get("THREAT", 0),
        n_clear=counts.get("CLEAR", 0),
        n_abstain=counts.get("ABSTAIN", 0),
        quorum=quorum,
        confirmed=confirmed,
        confidence=confidence,
        tolerated_faults=quorum - 1,
        leaderless=True,
        votes=votes,
    )


def defend_from_guard_report(guard_report: Any, **kw: Any) -> DefenseResult | None:
    """Wire an integrity-guard verdict into the swarm: intact → no defense; breached → mount one."""
    if getattr(guard_report, "intact", True):
        return None
    findings = list(getattr(guard_report, "findings", []) or [])
    threat = ThreatReport(
        threat_id=f"guard-{getattr(guard_report, 'n_findings', len(findings))}",
        kind="mutated_invariant" if findings else "injected_instruction",
        description="integrity guard reported a breach of the engine's pinned invariants",
        severity=max(1, len(findings)),
    )
    return mount_defense(threat, **kw)


def on_breach(payload: dict[str, Any], **kw: Any) -> DefenseResult | None:
    """ThoughtBus-handler shape for ``bio.integrity_guard.run``: mobilize the swarm on a breach.

    A daemon would ``subscribe("bio.integrity_guard.run", lambda t: emit_defense(on_breach(t.payload)))``.
    Returns None when the guard reported intact.
    """
    if payload.get("intact", True):
        return None
    n_findings = int(payload.get("n_findings", 1) or 1)
    threat = ThreatReport(
        threat_id=f"breach-{n_findings}",
        kind="mutated_invariant" if n_findings else "injected_instruction",
        description="bio.integrity_guard.run reported a breach",
        severity=max(1, n_findings),
    )
    return mount_defense(threat, **kw)


def write_defense_report(
    result: DefenseResult,
    out_md: str | Path,
    out_json: str | Path | None = None,
) -> DefenseResult:
    """Write the swarm-defense verdict as a durable evidence artifact (markdown [+ JSON])."""
    import json

    d = result.to_dict()
    lines: list[str] = []
    lines.append("# Swarm defense — the bee-ball quorum response")
    lines.append("")
    lines.append(
        "Generated by `python -m aureon.bio.swarm_defense --report <OUT.md>` — on a detected breach, N "
        "independent defenders each re-verify the threat; neutralization is confirmed only on a majority "
        "quorum. Leaderless and Byzantine-tolerant to a minority of compromised or silent defenders."
    )
    lines.append("")
    lines.append(f"> {SWARM_DEFENSE_BOUNDARY}")
    lines.append("")
    lines.append(
        f"**Threat `{result.threat_id}` (kind: {result.kind}) — confirmed: {result.confirmed}** "
        f"(confidence {result.confidence:g}). {result.n_threat}/{result.n_defenders} defenders voted "
        f"THREAT (quorum {result.quorum}); {result.n_clear} CLEAR, {result.n_abstain} abstained. "
        f"Leaderless: {result.leaderless}. Tolerates up to {result.tolerated_faults} compromised or "
        f"silent defenders."
    )
    lines.append("")
    lines.append("| defender | verdict | confidence | reason |")
    lines.append("|:---|:---|---:|:---|")
    for v in result.votes:
        lines.append(f"| {v.defender} | {v.verdict} | {v.confidence:g} | {v.reason} |")
    lines.append("")
    md = "\n".join(lines) + "\n"

    out_md_path = Path(out_md)
    out_md_path.write_text(md, encoding="utf-8")
    if out_json is not None:
        Path(out_json).write_text(json.dumps(d, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return replace(result, out_path=str(out_md_path))


def emit_defense(result: DefenseResult, *, bus: Any | None = None, trace: bool = True) -> dict[str, Any]:
    """Publish the swarm-defense verdict to cognition. Best-effort, never fatal."""
    payload = result.to_dict()
    summary = {
        "threat_id": result.threat_id,
        "kind": result.kind,
        "confirmed": result.confirmed,
        "confidence": result.confidence,
        "n_threat": result.n_threat,
        "n_defenders": result.n_defenders,
        "quorum": result.quorum,
        "leaderless": result.leaderless,
        "boundary": SWARM_DEFENSE_BOUNDARY,
    }
    try:
        from aureon.core.aureon_thought_bus import Thought, get_thought_bus

        target = bus if bus is not None else get_thought_bus()
        target.publish(
            Thought(source=_SOURCE, topic=DEFENSE_RUN_TOPIC, trace_id=uuid.uuid4().hex, payload=summary)
        )
    except Exception:  # noqa: BLE001 - emission is best-effort, never fatal
        pass

    if trace:
        try:
            from aureon.core.bus_trace import append_trace

            append_trace(DEFENSE_TRACE_NAME, {
                "threat_id": result.threat_id,
                "confirmed": result.confirmed,
                "n_threat": result.n_threat,
                "n_defenders": result.n_defenders,
                "leaderless": result.leaderless,
                "boundary": SWARM_DEFENSE_BOUNDARY,
                "_ts": time.time(),
            })
        except Exception:  # noqa: BLE001 - trace mirror is best-effort
            pass

    return payload


def main(argv: list[str] | None = None) -> int:
    """CLI: mount a demonstration defense and print / write the quorum verdict."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Mount a leaderless-quorum swarm defense over a detected threat (deterministic model)."
    )
    parser.add_argument("--report", metavar="OUT.md", help="write the verdict as a markdown evidence artifact")
    parser.add_argument("--report-json", metavar="OUT.json", help="also write the JSON record")
    parser.add_argument("--self-test", action="store_true",
                        help="assert real threat confirmed (all-honest + minority fault) and benign not confirmed")
    args = parser.parse_args(argv)

    real = ThreatReport(threat_id="demo-real", kind="mutated_invariant",
                        description="a pinned engine invariant drifted", severity=2)
    benign = ThreatReport(threat_id="demo-benign", kind="unknown", description="no drift", severity=0)

    result = mount_defense(real)
    tol = result.tolerated_faults
    minority = mount_defense(real, faulty_idx=tuple(range(tol)))            # survives a minority
    overwhelmed = mount_defense(real, faulty_idx=tuple(range(result.quorum)))  # majority compromised
    benign_res = mount_defense(benign)

    print("Swarm defense — the bee-ball quorum response (deterministic model)")
    print(f"  boundary: {SWARM_DEFENSE_BOUNDARY}")
    print(f"  defenders={result.n_defenders} quorum={result.quorum} tolerates≤{tol} faults · leaderless={result.leaderless}")
    print(f"  real threat, all honest        → confirmed={result.confirmed} ({result.n_threat}/{result.n_defenders}, conf {result.confidence:g})")
    print(f"  real threat, {tol} compromised    → confirmed={minority.confirmed} ({minority.n_threat}/{minority.n_defenders})")
    print(f"  real threat, {result.quorum} compromised    → confirmed={overwhelmed.confirmed} ({overwhelmed.n_threat}/{overwhelmed.n_defenders})  [honest bound]")
    print(f"  benign report                  → confirmed={benign_res.confirmed}")

    if args.report:
        rendered = write_defense_report(result, args.report, args.report_json)
        print(f"  report written: {rendered.out_path}")

    if args.self_test:
        ok = (result.confirmed and minority.confirmed and not overwhelmed.confirmed
              and not benign_res.confirmed and result.leaderless)
        return 0 if ok else 1
    return 0


if __name__ == "__main__":  # pragma: no cover - manual entry point
    raise SystemExit(main())

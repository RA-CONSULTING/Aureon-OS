#!/usr/bin/env python3
"""Immune memory — recall of neutralized threats and the secondary response (the immune layer's memory organ).

The adaptive immune system's defining trick is **memory**: once a pathogen is met and neutralized, the
body keeps a signature of it, so a *second* exposure is recognized instantly and answered by a faster,
stronger **secondary response** (memory B/T cells — the whole basis of vaccination). Aureon's cognitive
immune layer had a sensor (b34 integrity_guard), an effector (b35 swarm_defense), a border (b36
mcp_membrane), and a counterfeit detector (b37 authenticity_discriminator) — but **no memory**. Every
attack, even one seen a hundred times, paid the full primary-response cost again. This module (b38) is that
memory organ.

A confirmed, neutralized threat's **content signature** is committed to a bounded memory. On re-exposure the
memory **recognizes** it and returns a *secondary* response — a single recognition lookup, escalated — instead
of re-running the full quorum verification. It has **specificity** (a remembered threat does not recall a
different one), **self-tolerance** (a benign / self signal is never remembered as a threat — no autoimmunity),
and it is **bounded** (deterministic FIFO eviction past capacity).

Following the HNC logic chain, not reinventing the wheel
--------------------------------------------------------
This organ **reuses** the layer's own primitives rather than coining new ones: it imports
``swarm_defense.ThreatReport`` / ``DefenseResult`` (the effector's currency — no third ThreatReport), the
``mcp_membrane`` SHA-256 canonical-signature idiom, and the ``queen.conversation_memory`` atomic-persist
pattern (bounded store + tmp-file + ``os.replace`` + ``PERSIST_VERSION`` under ``state/``, never a repo-root
JSON). ``install_immune_memory`` **closes the loop** the effector only described: it subscribes
``on_confirmed_defense`` to ``bio.swarm_defense.run`` so a real neutralization actually commits to memory.
The Queen may **observe** (recognition rides ``bio.immune_memory.run`` onto her channel) but never commands —
the immune effector is deliberately leaderless (a co-opted authority is the very parasite we defend against).

Honest scope (stated, not decorative — enforced by tests)
---------------------------------------------------------
This is a **deterministic signature cache + recognition accelerator**. "Faster / stronger secondary response"
is measured in **verification work-units, not wall-clock** (a novel threat costs the full quorum's worth of
passes; a recognized repeat costs a single lookup) — so artifacts stay byte-identical. It is **NOT** machine
learning and **NOT** prevention: a novel or mutated threat still pays the full primary response, and a
mutated variant that changes its signature is correctly seen as new. It is self-tolerant and makes **no claim
about any person**. Pure stdlib + reuse of sibling modules; no import-time side effects beyond a guarded,
suppressible organism heartbeat.
"""

from __future__ import annotations

import sys
import time
import uuid
from collections import OrderedDict
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any, Final

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from aureon.bio.mcp_membrane import _canonical, _sha256_hex  # noqa: E402 - reuse the family's signature idiom
from aureon.bio.swarm_defense import (  # noqa: E402 - reuse the effector's currency, no third ThreatReport
    DEFAULT_N_DEFENDERS,
    DefenseResult,
    ThreatReport,
)

# --- guarded organism link (suppressible; never fatal) — the "I exist" heartbeat ---
try:  # pragma: no cover - environment-dependent, best-effort
    from aureon.core.aureon_baton_link import link_system

    link_system(__name__)
except Exception:  # noqa: BLE001 - the organ must import in any environment
    pass

__all__ = [
    "IMMUNE_MEMORY_BOUNDARY",
    "MEMORY_RUN_TOPIC",
    "MEMORY_TRACE_NAME",
    "DEFAULT_CAPACITY",
    "PRIMARY_COST",
    "SECONDARY_COST",
    "MemoryRecord",
    "ResponseOutcome",
    "ImmuneMemoryReport",
    "ImmuneMemory",
    "signature_of",
    "threat_signature",
    "remember_from_defense",
    "remember_from_guard_report",
    "on_confirmed_defense",
    "install_immune_memory",
    "compute_immune_memory",
    "write_immune_memory_report",
    "emit_immune_memory",
    "main",
]

MEMORY_RUN_TOPIC: Final[str] = "bio.immune_memory.run"
MEMORY_TRACE_NAME: Final[str] = "immune_memory"
_SOURCE: Final[str] = "immune_memory"

DEFAULT_CAPACITY: Final[int] = 128
PRIMARY_COST: Final[int] = int(DEFAULT_N_DEFENDERS)  # a novel threat pays the full quorum re-verification
SECONDARY_COST: Final[int] = 1  # a recognized repeat costs a single memory lookup
PERSIST_VERSION: Final[int] = 1

IMMUNE_MEMORY_BOUNDARY: Final[str] = (
    "Deterministic immune memory: it commits a neutralized threat's content signature so a repeat is "
    "recognized instantly and answered by a cheaper, escalated secondary response - measured in "
    "verification work-units, NOT wall-clock. A signature cache + recognition accelerator, self-tolerant "
    "(a benign signal is never remembered), NOT machine learning and NOT prevention: a novel or mutated "
    "threat still pays the full primary response, and NOT a claim about any person."
)


# ── threat signatures (reuse the b36 canonical SHA-256 idiom) ─────────────────────────────────────


def signature_of(kind: str, identity: str) -> str:
    """Content-addressed signature over a threat's *stable identity* (kind + identity), never a nonce."""
    return _sha256_hex(_canonical([str(kind), str(identity)]))


def threat_signature(threat: ThreatReport) -> str:
    """Signature of a ThreatReport — its ``kind`` + ``threat_id`` (the antigen identity that survives to
    the effector's ``DefenseResult`` and the ``bio.swarm_defense.run`` payload), never a per-run field."""
    return signature_of(threat.kind, threat.threat_id)


# ── the memory store ──────────────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class MemoryRecord:
    """A memory cell: the persistent signature of a neutralized threat and how often it has recurred."""

    signature: str
    kind: str
    first_seen: int
    exposures: int
    severity: int
    neutralized: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ResponseOutcome:
    """The layer's response to one exposure: primary (full work) or secondary (recognized, cheap)."""

    signature: str
    kind: str
    recognized: bool
    tier: str  # "primary" | "secondary"
    cost: int
    escalated: bool
    is_self: bool
    committed: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ImmuneMemory:
    """A bounded, self-tolerant memory of neutralized threat signatures with a secondary-response path.

    Mirrors the repo's bounded-store pattern (``queen.conversation_memory``): FIFO eviction past
    ``capacity`` and an optional atomic ``state/`` persistence path (never a repo-root JSON). The
    benchmark / self-test uses an in-memory instance so artifacts stay byte-identical; the live path
    passes ``persist_path`` to survive across ticks.
    """

    def __init__(self, *, capacity: int = DEFAULT_CAPACITY, persist_path: str | Path | None = None) -> None:
        self.capacity = int(capacity)
        self.persist_path = Path(persist_path) if persist_path else None
        self._cells: OrderedDict[str, MemoryRecord] = OrderedDict()
        self._clock = 0
        self.evictions = 0
        if self.persist_path is not None:
            self._load()

    def __len__(self) -> int:
        return len(self._cells)

    def __contains__(self, signature: str) -> bool:
        return signature in self._cells

    def recognize_signature(self, signature: str) -> MemoryRecord | None:
        """Pure lookup — does a neutralized memory cell exist for this signature? (no mutation)."""
        rec = self._cells.get(signature)
        return rec if (rec is not None and rec.neutralized) else None

    def recognize(self, threat: ThreatReport) -> MemoryRecord | None:
        return self.recognize_signature(threat_signature(threat))

    def _commit(self, signature: str, kind: str, severity: int, neutralized: bool) -> MemoryRecord | None:
        """Insert or reinforce a memory cell. Benign (severity 0) is never committed — self-tolerance."""
        if severity < 1 or not neutralized:
            return None
        existing = self._cells.get(signature)
        if existing is not None:
            rec = replace(existing, exposures=existing.exposures + 1)
            self._cells[signature] = rec
            self._cells.move_to_end(signature)  # LRU reinforcement
            self._persist()
            return rec
        self._clock += 1
        rec = MemoryRecord(signature=signature, kind=str(kind), first_seen=self._clock,
                           exposures=1, severity=int(severity), neutralized=True)
        self._cells[signature] = rec
        while len(self._cells) > self.capacity:
            self._cells.popitem(last=False)  # FIFO eviction of the oldest cell
            self.evictions += 1
        self._persist()
        return rec

    def remember(self, threat: ThreatReport, *, neutralized: bool = True) -> MemoryRecord | None:
        return self._commit(threat_signature(threat), threat.kind, threat.severity, neutralized)

    def respond(self, threat: ThreatReport) -> ResponseOutcome:
        """Recognized + neutralized + not-self ⇒ cheap escalated secondary; else full primary (+commit if real)."""
        sig = threat_signature(threat)
        is_self = threat.severity < 1
        known = self.recognize_signature(sig)
        if known is not None and not is_self:
            self._cells[sig] = replace(known, exposures=known.exposures + 1)
            self._cells.move_to_end(sig)
            self._persist()
            return ResponseOutcome(signature=sig, kind=threat.kind, recognized=True, tier="secondary",
                                   cost=SECONDARY_COST, escalated=True, is_self=False, committed=False)
        committed = self._commit(sig, threat.kind, threat.severity, neutralized=True) is not None
        return ResponseOutcome(signature=sig, kind=threat.kind, recognized=False, tier="primary",
                               cost=PRIMARY_COST, escalated=False, is_self=is_self, committed=committed)

    # ── persistence (live path only; mirrors conversation_memory) ────────────────────────────────
    def _persist(self) -> None:
        if self.persist_path is None:
            return
        try:
            import json
            import os

            os.makedirs(self.persist_path.parent or ".", exist_ok=True)
            payload = {
                "version": PERSIST_VERSION,
                "capacity": self.capacity,
                "clock": self._clock,
                "evictions": self.evictions,
                "cells": [r.to_dict() for r in self._cells.values()],
            }
            tmp = str(self.persist_path) + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2, sort_keys=True)
            os.replace(tmp, self.persist_path)
        except Exception:  # noqa: BLE001 - persistence is best-effort, never fatal
            pass

    def _load(self) -> None:
        if self.persist_path is None or not self.persist_path.exists():
            return
        try:
            import json

            payload = json.loads(self.persist_path.read_text(encoding="utf-8"))
            self._clock = int(payload.get("clock", 0))
            self.evictions = int(payload.get("evictions", 0))
            for c in payload.get("cells", []):
                rec = MemoryRecord(signature=c["signature"], kind=c["kind"], first_seen=int(c["first_seen"]),
                                   exposures=int(c["exposures"]), severity=int(c["severity"]),
                                   neutralized=bool(c["neutralized"]))
                self._cells[rec.signature] = rec
        except Exception:  # noqa: BLE001 - a corrupt store starts empty, never crashes
            self._cells.clear()


# ── wiring into the layer (b34 sensor / b35 effector → memory) ──────────────────────────────────


def remember_from_defense(
    threat: ThreatReport, result: DefenseResult, memory: ImmuneMemory
) -> MemoryRecord | None:
    """Commit a threat to memory iff the swarm actually confirmed its neutralization (b35 → b38)."""
    if not getattr(result, "confirmed", False):
        return None
    return memory.remember(threat, neutralized=True)


def remember_from_guard_report(guard_report: Any, memory: ImmuneMemory) -> list[MemoryRecord]:
    """Commit a memory cell per breach Finding of a non-intact guard report (b34 → b38)."""
    if getattr(guard_report, "intact", True):
        return []
    out: list[MemoryRecord] = []
    for finding in getattr(guard_report, "findings", []) or []:
        sig = signature_of(getattr(finding, "kind", "unknown"), getattr(finding, "target", "?"))
        rec = memory._commit(sig, getattr(finding, "kind", "unknown"), severity=2, neutralized=True)
        if rec is not None:
            out.append(rec)
    return out


def on_confirmed_defense(payload: dict[str, Any], memory: ImmuneMemory) -> MemoryRecord | None:
    """ThoughtBus handler for ``bio.swarm_defense.run``: a confirmed neutralization commits to memory.

    Reads the effector's summary payload (``kind`` + ``threat_id`` + ``confirmed``) and commits the
    threat's stable-identity signature. Best-effort — a malformed payload is ignored, never fatal.
    """
    try:
        if not payload.get("confirmed"):
            return None
        kind = str(payload.get("kind", "unknown"))
        identity = str(payload.get("threat_id", ""))
        if not identity:
            return None
        return memory._commit(signature_of(kind, identity), kind, severity=2, neutralized=True)
    except Exception:  # noqa: BLE001 - handler must never break the bus
        return None


def install_immune_memory(bus: Any | None = None, memory: ImmuneMemory | None = None) -> ImmuneMemory:
    """Close the loop the effector only described: subscribe memory to ``bio.swarm_defense.run``.

    A confirmed neutralization event now actually commits to memory (the Queen observes on her own
    channel; the leaderless effector is never command-gated). Returns the memory so callers can read it.
    """
    mem = memory if memory is not None else ImmuneMemory()
    try:
        from aureon.core.aureon_thought_bus import get_thought_bus

        target = bus if bus is not None else get_thought_bus()

        def _handler(thought: Any) -> None:
            try:
                from aureon.core.aureon_thought_bus import payload_of

                on_confirmed_defense(payload_of(thought) or {}, mem)
            except Exception:  # noqa: BLE001
                payload = getattr(thought, "payload", None)
                if isinstance(payload, dict):
                    on_confirmed_defense(payload, mem)

        target.subscribe("bio.swarm_defense.run", _handler)
    except Exception:  # noqa: BLE001 - wiring is best-effort; the memory still works standalone
        pass
    return mem


# ── the deterministic recall / secondary-response audit ─────────────────────────────────────────


@dataclass(frozen=True)
class ImmuneMemoryReport:
    """The consolidated recall + secondary-response audit over a deterministic threat scenario."""

    tiers: list[dict[str, Any]]
    n_threats: int
    repeats: int
    n_novel: int
    n_self: int
    n_primary: int
    n_secondary: int
    recognition_rate: float
    false_recall_rate: float
    primary_cost: int
    secondary_cost: int
    speedup: float
    self_not_remembered: bool
    specificity: bool
    memory_size: int
    capacity: int
    evictions: int
    work_saved_fraction: float
    boundary: str = IMMUNE_MEMORY_BOUNDARY
    out_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        return d


def _threat(kind: str, identity: str, severity: int) -> ThreatReport:
    return ThreatReport(threat_id=identity, kind=kind, description=f"{kind}:{identity}", severity=severity)


def compute_immune_memory(
    *,
    n_threats: int = 8,
    repeats: int = 3,
    n_novel: int = 8,
    n_self: int = 6,
    capacity: int = DEFAULT_CAPACITY,
    seed0: int = 0,
) -> ImmuneMemoryReport:
    """Drive a deterministic stream of threats through a fresh memory and measure recall + secondary cost.

    ``n_threats`` real parasites are met once (primary + commit) then re-exposed ``repeats`` times
    (secondary), interleaved with ``n_novel`` never-before-seen parasites (each once) and ``n_self`` benign
    self signals. Rolls up: ``recognition_rate`` (repeats recognized → 1.0), ``false_recall_rate``
    (novel + self wrongly recognized → 0.0), the primary/secondary work-unit costs and their ``speedup``,
    ``self_not_remembered`` + ``specificity`` (the memory holds exactly the real parasites, no collisions),
    and ``work_saved_fraction`` (how much verification work the memory saved vs an all-primary layer).
    """
    memory = ImmuneMemory(capacity=capacity)
    kinds = ("mutated_invariant", "injected_instruction")
    antigens = [_threat(kinds[(seed0 + i) % 2], f"parasite-{seed0}-{i}", 2) for i in range(n_threats)]
    novels = [_threat(kinds[(seed0 + i) % 2], f"novel-{seed0}-{i}", 2) for i in range(n_novel)]
    selfs = [_threat("unknown", f"self-{seed0}-{i}", 0) for i in range(n_self)]

    tiers: list[ResponseOutcome] = []
    # First exposure of every antigen — primary + commit.
    for a in antigens:
        tiers.append(memory.respond(a))
    # Interleave self signals (never remembered) and novel parasites (seen once → primary).
    for s in selfs:
        tiers.append(memory.respond(s))
    for nv in novels:
        tiers.append(memory.respond(nv))
    # Re-exposures of the antigens — should all be recognized (secondary).
    repeat_outcomes: list[ResponseOutcome] = []
    for _ in range(repeats):
        for a in antigens:
            o = memory.respond(a)
            tiers.append(o)
            repeat_outcomes.append(o)

    # recognition on repeats
    recognized_repeats = sum(1 for o in repeat_outcomes if o.recognized)
    recognition_rate = recognized_repeats / len(repeat_outcomes) if repeat_outcomes else 0.0
    # false recall: any novel or self exposure that was recognized
    novel_sigs = {threat_signature(nv) for nv in novels}
    self_sigs = {threat_signature(s) for s in selfs}
    false_recalls = sum(1 for o in tiers if o.recognized and (o.signature in novel_sigs or o.signature in self_sigs))
    denom = (len(novels) + len(selfs))
    false_recall_rate = false_recalls / denom if denom else 0.0

    antigen_sigs = {threat_signature(a) for a in antigens}
    self_not_remembered = not any(sig in memory for sig in self_sigs)
    specificity = (
        len(antigen_sigs) == n_threats
        and all(sig in memory for sig in antigen_sigs)
        and not (antigen_sigs & (novel_sigs | self_sigs))
    )

    n_primary = sum(1 for o in tiers if o.tier == "primary")
    n_secondary = sum(1 for o in tiers if o.tier == "secondary")
    actual_cost = sum(o.cost for o in tiers)
    all_primary_cost = len(tiers) * PRIMARY_COST
    work_saved_fraction = (1.0 - actual_cost / all_primary_cost) if all_primary_cost else 0.0

    return ImmuneMemoryReport(
        tiers=[o.to_dict() for o in tiers],
        n_threats=n_threats,
        repeats=repeats,
        n_novel=n_novel,
        n_self=n_self,
        n_primary=n_primary,
        n_secondary=n_secondary,
        recognition_rate=recognition_rate,
        false_recall_rate=false_recall_rate,
        primary_cost=PRIMARY_COST,
        secondary_cost=SECONDARY_COST,
        speedup=(PRIMARY_COST / SECONDARY_COST) if SECONDARY_COST else 0.0,
        self_not_remembered=self_not_remembered,
        specificity=specificity,
        memory_size=len(memory),
        capacity=capacity,
        evictions=memory.evictions,
        work_saved_fraction=work_saved_fraction,
    )


def write_immune_memory_report(
    report: ImmuneMemoryReport,
    out_md: str | Path,
    out_json: str | Path | None = None,
) -> ImmuneMemoryReport:
    """Write the immune-memory audit as a durable evidence artifact (markdown [+ JSON])."""
    import json

    d = report.to_dict()
    lines: list[str] = []
    lines.append("# Immune memory — recall and the secondary response")
    lines.append("")
    lines.append(
        "Generated by `python -m aureon.bio.immune_memory --report <OUT.md>` — a deterministic scenario of "
        "real parasites (met once, then re-exposed), novel parasites, and benign self signals driven through "
        "a fresh memory. A first exposure pays the full primary response and is committed; a recognized "
        "repeat is answered by a cheap, escalated secondary response. Cost is measured in verification "
        "work-units, never wall-clock."
    )
    lines.append("")
    lines.append(f"> {IMMUNE_MEMORY_BOUNDARY}")
    lines.append("")
    lines.append(
        f"**Recognition rate {report.recognition_rate:.3f}** on repeats · **false-recall rate "
        f"{report.false_recall_rate:.3f}** on novel/self · primary {report.primary_cost} vs secondary "
        f"{report.secondary_cost} work-units (**speedup {report.speedup:.1f}×**) · self not remembered: "
        f"{report.self_not_remembered} · specificity: {report.specificity} · memory {report.memory_size}/"
        f"{report.capacity} (evictions {report.evictions}) · work saved {report.work_saved_fraction:.3f}."
    )
    lines.append("")
    lines.append("| metric | value |")
    lines.append("|:---|---:|")
    lines.append(f"| threats (repeated {report.repeats}×) | {report.n_threats} |")
    lines.append(f"| novel parasites | {report.n_novel} |")
    lines.append(f"| self signals | {report.n_self} |")
    lines.append(f"| primary responses | {report.n_primary} |")
    lines.append(f"| secondary responses | {report.n_secondary} |")
    lines.append(f"| recognition rate | {report.recognition_rate:.3f} |")
    lines.append(f"| false-recall rate | {report.false_recall_rate:.3f} |")
    lines.append(f"| speedup (work-units) | {report.speedup:.1f} |")
    lines.append(f"| work saved | {report.work_saved_fraction:.3f} |")
    lines.append("")
    md = "\n".join(lines) + "\n"

    out_md_path = Path(out_md)
    out_md_path.write_text(md, encoding="utf-8")
    if out_json is not None:
        Path(out_json).write_text(json.dumps(d, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return replace(report, out_path=str(out_md_path))


def emit_immune_memory(
    report: ImmuneMemoryReport, *, bus: Any | None = None, trace: bool = True
) -> dict[str, Any]:
    """Publish the immune-memory audit to cognition (the Queen may observe). Best-effort, never fatal."""
    payload = report.to_dict()
    summary = {
        "recognition_rate": report.recognition_rate,
        "false_recall_rate": report.false_recall_rate,
        "speedup": report.speedup,
        "self_not_remembered": report.self_not_remembered,
        "specificity": report.specificity,
        "memory_size": report.memory_size,
        "boundary": IMMUNE_MEMORY_BOUNDARY,
    }
    try:
        from aureon.core.aureon_thought_bus import Thought, get_thought_bus

        target = bus if bus is not None else get_thought_bus()
        target.publish(
            Thought(source=_SOURCE, topic=MEMORY_RUN_TOPIC, trace_id=uuid.uuid4().hex, payload=summary)
        )
    except Exception:  # noqa: BLE001 - emission is best-effort, never fatal
        pass

    if trace:
        try:
            from aureon.core.bus_trace import append_trace

            append_trace(MEMORY_TRACE_NAME, {
                "recognition_rate": report.recognition_rate,
                "false_recall_rate": report.false_recall_rate,
                "speedup": report.speedup,
                "self_not_remembered": report.self_not_remembered,
                "boundary": IMMUNE_MEMORY_BOUNDARY,
                "_ts": time.time(),
            })
        except Exception:  # noqa: BLE001 - trace mirror is best-effort
            pass

    return payload


def main(argv: list[str] | None = None) -> int:
    """CLI: run the recall / secondary-response audit and print / write the table."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Audit immune-memory recall + the secondary response (work-units, not wall-clock)."
    )
    parser.add_argument("--report", metavar="OUT.md", help="write the table as a markdown evidence artifact")
    parser.add_argument("--report-json", metavar="OUT.json", help="also write the JSON record")
    parser.add_argument("--threats", type=int, default=8)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--self-test", action="store_true",
                        help="assert repeats recognized, novel/self missed, speedup>1, self not remembered")
    args = parser.parse_args(argv)

    report = compute_immune_memory(n_threats=args.threats, repeats=args.repeats, seed0=args.seed)

    print("Immune memory — recall and the secondary response (work-units, not wall-clock)")
    print(f"  boundary: {IMMUNE_MEMORY_BOUNDARY}")
    print(f"  {report.n_threats} parasites ×{report.repeats} repeats · {report.n_novel} novel · "
          f"{report.n_self} self · capacity {report.capacity}")
    print(f"  recognition {report.recognition_rate:.3f} · false-recall {report.false_recall_rate:.3f} · "
          f"primary {report.primary_cost} vs secondary {report.secondary_cost} "
          f"(speedup {report.speedup:.1f}×)")
    print(f"  self not remembered: {report.self_not_remembered} · specificity: {report.specificity} · "
          f"memory {report.memory_size}/{report.capacity} · work saved {report.work_saved_fraction:.3f}")

    if args.report:
        rendered = write_immune_memory_report(report, args.report, args.report_json)
        print(f"  report written: {rendered.out_path}")

    if args.self_test:
        ok = (
            report.recognition_rate >= 0.99
            and report.false_recall_rate <= 0.01
            and report.speedup > 1.0
            and report.self_not_remembered
            and report.specificity
        )
        return 0 if ok else 1
    return 0


if __name__ == "__main__":  # pragma: no cover - manual entry point
    raise SystemExit(main())

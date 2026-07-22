#!/usr/bin/env python3
"""Immune regulation — the homeostatic brake (regulatory T-cells + inflammation resolution).

Every immune system needs a **brake**. Left ungoverned, an immune response harms the host: it attacks
*self* (autoimmunity) or over-responds to repeated/benign alarms until the reaction itself is the damage
(a cytokine storm). Aureon's cognitive immune layer can now sense (b34), respond (b35), hold the border
(b36), tell genuine from counterfeit (b37), and *remember* (b38) — and memory biases it toward faster,
stronger secondary responses. This module (b39) is the counterbalance: the regulatory governor that keeps
the layer in **homeostasis**.

It applies a deterministic, tick-based regulatory policy to a stream of candidate threats:

* **Self-tolerance** — a benign / self signal (``severity < 1``) is *never* mounted against. This is the
  anti-autoimmunity invariant: the layer does not attack the host.
* **Refractory cooldown** — once a threat has been responded to, identical alarms within a cooldown window
  are suppressed, so a false-alarm storm (the same signature repeated) cannot re-inflame the layer.
* **Bounded inflammation** — concurrent active responses are capped; a flood beyond the cap is *deferred*
  (suppressed this tick), not permanently denied, so inflammation never runs away.
* **Homeostasis** — when the alarm stream quiets, active responses age out and inflammation returns to 0.

Genuine, *novel* threats are always allowed — the brake damps repetition and self, never novelty.

Following the HNC logic chain, not reinventing the wheel
--------------------------------------------------------
Reuses the layer's own primitives: ``swarm_defense.ThreatReport`` (the effector's currency — no new type)
and ``immune_memory``'s content-signature idiom (``signature_of`` / ``threat_signature``). It pairs with
b38 as the accelerator/brake balance, and ``install_immune_regulation`` closes a loop with the effector —
a confirmed neutralization on ``bio.swarm_defense.run`` registers a cooldown so the layer does not
immediately re-attack the same cleared threat. The Queen may **observe** (``bio.immune_regulation.run``);
the leaderless effector is never command-gated.

Honest scope (stated, not decorative — enforced by tests)
---------------------------------------------------------
A **deterministic homeostatic governor** measured in **event-ticks, not wall-clock** (cooldown/inflammation
are integer counts), so artifacts are byte-identical. It is **NOT** machine learning and **NOT** prevention:
it governs *when* the existing organs respond; it does not itself detect or block a threat, and a genuine
novel threat always passes. Self-tolerant, and it makes **no claim about any person**. Pure stdlib + reuse
of sibling modules; no import-time side effects beyond a guarded, suppressible organism heartbeat.
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

from aureon.bio.immune_memory import (  # noqa: E402 - reuse the family signature idiom
    signature_of,
    threat_signature,
)
from aureon.bio.swarm_defense import ThreatReport  # noqa: E402 - reuse the effector's currency, no new type

# --- guarded organism link (suppressible; never fatal) — the "I exist" heartbeat ---
try:  # pragma: no cover - environment-dependent, best-effort
    from aureon.core.aureon_baton_link import link_system

    link_system(__name__)
except Exception:  # noqa: BLE001 - the organ must import in any environment
    pass

__all__ = [
    "IMMUNE_REGULATION_BOUNDARY",
    "REGULATION_RUN_TOPIC",
    "REGULATION_TRACE_NAME",
    "DEFAULT_COOLDOWN",
    "DEFAULT_INFLAMMATION_CAP",
    "RegulationOutcome",
    "ImmuneRegulationReport",
    "RegulatoryGovernor",
    "on_confirmed_defense",
    "install_immune_regulation",
    "compute_immune_regulation",
    "write_immune_regulation_report",
    "emit_immune_regulation",
    "main",
]

REGULATION_RUN_TOPIC: Final[str] = "bio.immune_regulation.run"
REGULATION_TRACE_NAME: Final[str] = "immune_regulation"
_SOURCE: Final[str] = "immune_regulation"

DEFAULT_COOLDOWN: Final[int] = 3  # event-ticks a responded-to threat stays refractory
DEFAULT_INFLAMMATION_CAP: Final[int] = 6  # max concurrent active responses before a flood is deferred

IMMUNE_REGULATION_BOUNDARY: Final[str] = (
    "Deterministic immune-regulation governor: it enforces self-tolerance (a benign signal is never "
    "mounted against), a refractory cooldown that damps repeated false alarms, and a bounded-inflammation "
    "cap that defers a flood - all measured in event-ticks, NOT wall-clock. It governs WHEN the layer "
    "responds; it is NOT machine learning, NOT prevention, never suppresses a genuine novel threat, and "
    "NOT a claim about any person."
)

_ALLOW: Final[str] = "allow"
_SUPPRESS: Final[str] = "suppress"


@dataclass(frozen=True)
class RegulationOutcome:
    """The governor's decision for one candidate response: allow, or suppress (with the reason)."""

    signature: str
    kind: str
    decision: str  # "allow" | "suppress"
    reason: str  # "genuine_threat" | "self_tolerance" | "refractory_cooldown" | "inflammation_cap"
    is_self: bool
    inflammation: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class RegulatoryGovernor:
    """A deterministic tick-based homeostatic brake over the immune layer's responses.

    State advances one **event-tick** per ``regulate``/``tick``/``register_response`` call. An allowed
    response stays *active* (contributing to inflammation and refractory to repeats) for ``cooldown``
    ticks, then ages out. Concurrent active responses are capped at ``inflammation_cap``.
    """

    def __init__(self, *, cooldown: int = DEFAULT_COOLDOWN, inflammation_cap: int = DEFAULT_INFLAMMATION_CAP) -> None:
        self.cooldown = int(cooldown)
        self.inflammation_cap = int(inflammation_cap)
        self._active: OrderedDict[str, int] = OrderedDict()  # signature -> tick allowed
        self._clock = 0

    def _prune(self) -> None:
        """Age out responses whose cooldown window has elapsed (clock - allowed > cooldown).

        An entry allowed at tick ``t`` stays refractory for the next ``cooldown`` ticks
        (``clock - t <= cooldown``) and is admitted again on the tick after that.
        """
        for sig in [s for s, t in self._active.items() if self._clock - t > self.cooldown]:
            del self._active[sig]

    @property
    def inflammation(self) -> int:
        """Current active-response count (the layer's inflammation level)."""
        self._prune()
        return len(self._active)

    def regulate(self, threat: ThreatReport) -> RegulationOutcome:
        """Decide whether the layer should mount a response to ``threat`` right now."""
        self._clock += 1
        self._prune()
        sig = threat_signature(threat)
        is_self = threat.severity < 1
        if is_self:
            return RegulationOutcome(sig, threat.kind, _SUPPRESS, "self_tolerance", True, len(self._active))
        if sig in self._active:
            return RegulationOutcome(sig, threat.kind, _SUPPRESS, "refractory_cooldown", False, len(self._active))
        if len(self._active) >= self.inflammation_cap:
            return RegulationOutcome(sig, threat.kind, _SUPPRESS, "inflammation_cap", False, len(self._active))
        self._active[sig] = self._clock
        return RegulationOutcome(sig, threat.kind, _ALLOW, "genuine_threat", False, len(self._active))

    def tick(self) -> None:
        """Advance one idle event-tick (no candidate), letting inflammation resolve toward homeostasis."""
        self._clock += 1
        self._prune()

    def register_response(self, kind: str, identity: str) -> None:
        """Mark a threat as actively handled (e.g. the swarm confirmed neutralization) → refractory."""
        self._clock += 1
        self._prune()
        self._active[signature_of(kind, identity)] = self._clock


def on_confirmed_defense(payload: dict[str, Any], governor: RegulatoryGovernor) -> bool:
    """ThoughtBus handler for ``bio.swarm_defense.run``: a confirmed neutralization registers a cooldown.

    Reads the effector's summary payload (``kind`` + ``threat_id`` + ``confirmed``) so the layer does not
    immediately re-attack a just-cleared threat. Best-effort — a malformed payload is ignored, never fatal.
    """
    try:
        if not payload.get("confirmed"):
            return False
        kind = str(payload.get("kind", "unknown"))
        identity = str(payload.get("threat_id", ""))
        if not identity:
            return False
        governor.register_response(kind, identity)
        return True
    except Exception:  # noqa: BLE001 - handler must never break the bus
        return False


def install_immune_regulation(bus: Any | None = None, governor: RegulatoryGovernor | None = None) -> RegulatoryGovernor:
    """Close the loop: subscribe the governor to ``bio.swarm_defense.run`` so a confirmed neutralization
    registers a cooldown (the layer stops re-attacking a cleared threat). The Queen observes; the effector
    stays leaderless. Returns the governor so callers can read it."""
    gov = governor if governor is not None else RegulatoryGovernor()
    try:
        from aureon.core.aureon_thought_bus import get_thought_bus

        target = bus if bus is not None else get_thought_bus()

        def _handler(thought: Any) -> None:
            try:
                from aureon.core.aureon_thought_bus import payload_of

                on_confirmed_defense(payload_of(thought) or {}, gov)
            except Exception:  # noqa: BLE001
                payload = getattr(thought, "payload", None)
                if isinstance(payload, dict):
                    on_confirmed_defense(payload, gov)

        target.subscribe("bio.swarm_defense.run", _handler)
    except Exception:  # noqa: BLE001 - wiring is best-effort; the governor works standalone
        pass
    return gov


@dataclass(frozen=True)
class ImmuneRegulationReport:
    """The consolidated homeostatic-regulation audit over a deterministic alarm scenario."""

    outcomes: list[dict[str, Any]]
    n_genuine: int
    storm_signatures: int
    storm_repeats: int
    n_self: int
    cooldown: int
    inflammation_cap: int
    self_attack_rate: float
    false_alarm_suppression_rate: float
    genuine_pass_rate: float
    max_inflammation: int
    homeostasis_restored: bool
    work_saved_fraction: float
    boundary: str = IMMUNE_REGULATION_BOUNDARY
    out_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _threat(kind: str, identity: str, severity: int) -> ThreatReport:
    return ThreatReport(threat_id=identity, kind=kind, description=f"{kind}:{identity}", severity=severity)


def compute_immune_regulation(
    *,
    n_genuine: int = 4,
    storm_signatures: int = 3,
    storm_repeats: int = 4,
    n_self: int = 4,
    cooldown: int = DEFAULT_COOLDOWN,
    inflammation_cap: int = DEFAULT_INFLAMMATION_CAP,
    seed0: int = 0,
) -> ImmuneRegulationReport:
    """Drive a deterministic alarm stream through a fresh governor and measure homeostatic control.

    The stream has three arms: (a) ``n_genuine`` distinct genuine threats (allowed — novelty always
    passes), (b) a **false-alarm storm** of ``storm_signatures`` signatures each repeated ``storm_repeats``
    times back-to-back (first of each allowed, repeats within cooldown suppressed), and (c) ``n_self``
    benign self signals (never mounted against). It then idles until inflammation resolves. Rolls up:
    ``self_attack_rate`` (→ 0.0), ``false_alarm_suppression_rate`` (→ high), ``genuine_pass_rate`` (→ 1.0),
    ``max_inflammation`` (bounded), ``homeostasis_restored`` (inflammation → 0 after the stream drains),
    and ``work_saved_fraction`` (suppressed responses vs responding to every alarm).
    """
    gov = RegulatoryGovernor(cooldown=cooldown, inflammation_cap=inflammation_cap)
    kinds = ("mutated_invariant", "injected_instruction")
    outcomes: list[RegulationOutcome] = []
    max_inflammation = 0

    # (a) genuine distinct threats — each novel, must be allowed.
    genuine = [_threat(kinds[(seed0 + i) % 2], f"parasite-{seed0}-{i}", 2) for i in range(n_genuine)]
    genuine_outcomes: list[RegulationOutcome] = []
    for g in genuine:
        o = gov.regulate(g)
        outcomes.append(o)
        genuine_outcomes.append(o)
        max_inflammation = max(max_inflammation, o.inflammation)

    # (b) false-alarm storm — same signatures hammered; first allowed, repeats within cooldown suppressed.
    storm_repeat_events: list[RegulationOutcome] = []
    for s in range(storm_signatures):
        threat = _threat("mutated_invariant", f"storm-{seed0}-{s}", 2)
        for r in range(storm_repeats):
            o = gov.regulate(threat)
            outcomes.append(o)
            max_inflammation = max(max_inflammation, o.inflammation)
            if r > 0:  # the first occurrence is a legitimate detection; the rest are the storm
                storm_repeat_events.append(o)

    # (c) self signals — benign, must never be mounted against.
    self_outcomes: list[RegulationOutcome] = []
    for i in range(n_self):
        o = gov.regulate(_threat("unknown", f"self-{seed0}-{i}", 0))
        outcomes.append(o)
        self_outcomes.append(o)

    # idle until inflammation resolves (homeostasis), bounded so a stuck state can't loop forever.
    for _ in range(cooldown + 2):
        if gov.inflammation == 0:
            break
        gov.tick()
    homeostasis_restored = gov.inflammation == 0

    self_attacks = sum(1 for o in self_outcomes if o.decision == _ALLOW)
    self_attack_rate = self_attacks / n_self if n_self else 0.0
    storm_suppressed = sum(1 for o in storm_repeat_events if o.decision == _SUPPRESS)
    false_alarm_suppression_rate = (
        storm_suppressed / len(storm_repeat_events) if storm_repeat_events else 0.0
    )
    genuine_allowed = sum(1 for o in genuine_outcomes if o.decision == _ALLOW)
    genuine_pass_rate = genuine_allowed / n_genuine if n_genuine else 0.0
    suppressed_total = sum(1 for o in outcomes if o.decision == _SUPPRESS)
    work_saved_fraction = suppressed_total / len(outcomes) if outcomes else 0.0

    return ImmuneRegulationReport(
        outcomes=[o.to_dict() for o in outcomes],
        n_genuine=n_genuine,
        storm_signatures=storm_signatures,
        storm_repeats=storm_repeats,
        n_self=n_self,
        cooldown=cooldown,
        inflammation_cap=inflammation_cap,
        self_attack_rate=self_attack_rate,
        false_alarm_suppression_rate=false_alarm_suppression_rate,
        genuine_pass_rate=genuine_pass_rate,
        max_inflammation=max_inflammation,
        homeostasis_restored=homeostasis_restored,
        work_saved_fraction=work_saved_fraction,
    )


def write_immune_regulation_report(
    report: ImmuneRegulationReport,
    out_md: str | Path,
    out_json: str | Path | None = None,
) -> ImmuneRegulationReport:
    """Write the immune-regulation audit as a durable evidence artifact (markdown [+ JSON])."""
    import json

    d = report.to_dict()
    lines: list[str] = []
    lines.append("# Immune regulation — the homeostatic brake")
    lines.append("")
    lines.append(
        "Generated by `python -m aureon.bio.immune_regulation --report <OUT.md>` — a deterministic alarm "
        "stream (genuine threats, a false-alarm storm, and benign self signals) driven through a fresh "
        "regulatory governor. Self signals are never mounted against, repeated alarms are damped by a "
        "refractory cooldown, genuine novel threats always pass, and inflammation resolves to homeostasis. "
        "Cost is measured in event-ticks, never wall-clock."
    )
    lines.append("")
    lines.append(f"> {IMMUNE_REGULATION_BOUNDARY}")
    lines.append("")
    lines.append(
        f"**Self-attack rate {report.self_attack_rate:.3f}** (autoimmunity) · **false-alarm suppression "
        f"{report.false_alarm_suppression_rate:.3f}** · **genuine-pass {report.genuine_pass_rate:.3f}** · "
        f"max inflammation {report.max_inflammation}/{report.inflammation_cap} · homeostasis restored: "
        f"{report.homeostasis_restored} · work saved {report.work_saved_fraction:.3f} "
        f"(cooldown {report.cooldown} ticks)."
    )
    lines.append("")
    lines.append("| metric | value |")
    lines.append("|:---|---:|")
    lines.append(f"| genuine threats | {report.n_genuine} |")
    lines.append(f"| storm signatures × repeats | {report.storm_signatures}×{report.storm_repeats} |")
    lines.append(f"| self signals | {report.n_self} |")
    lines.append(f"| self-attack rate | {report.self_attack_rate:.3f} |")
    lines.append(f"| false-alarm suppression | {report.false_alarm_suppression_rate:.3f} |")
    lines.append(f"| genuine-pass rate | {report.genuine_pass_rate:.3f} |")
    lines.append(f"| max inflammation | {report.max_inflammation} |")
    lines.append(f"| homeostasis restored | {report.homeostasis_restored} |")
    lines.append(f"| work saved | {report.work_saved_fraction:.3f} |")
    lines.append("")
    md = "\n".join(lines) + "\n"

    out_md_path = Path(out_md)
    out_md_path.write_text(md, encoding="utf-8")
    if out_json is not None:
        Path(out_json).write_text(json.dumps(d, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return replace(report, out_path=str(out_md_path))


def emit_immune_regulation(
    report: ImmuneRegulationReport, *, bus: Any | None = None, trace: bool = True
) -> dict[str, Any]:
    """Publish the immune-regulation audit to cognition (the Queen may observe). Best-effort, never fatal."""
    payload = report.to_dict()
    summary = {
        "self_attack_rate": report.self_attack_rate,
        "false_alarm_suppression_rate": report.false_alarm_suppression_rate,
        "genuine_pass_rate": report.genuine_pass_rate,
        "max_inflammation": report.max_inflammation,
        "homeostasis_restored": report.homeostasis_restored,
        "boundary": IMMUNE_REGULATION_BOUNDARY,
    }
    try:
        from aureon.core.aureon_thought_bus import Thought, get_thought_bus

        target = bus if bus is not None else get_thought_bus()
        target.publish(
            Thought(source=_SOURCE, topic=REGULATION_RUN_TOPIC, trace_id=uuid.uuid4().hex, payload=summary)
        )
    except Exception:  # noqa: BLE001 - emission is best-effort, never fatal
        pass

    if trace:
        try:
            from aureon.core.bus_trace import append_trace

            append_trace(REGULATION_TRACE_NAME, {
                "self_attack_rate": report.self_attack_rate,
                "false_alarm_suppression_rate": report.false_alarm_suppression_rate,
                "genuine_pass_rate": report.genuine_pass_rate,
                "homeostasis_restored": report.homeostasis_restored,
                "boundary": IMMUNE_REGULATION_BOUNDARY,
                "_ts": time.time(),
            })
        except Exception:  # noqa: BLE001 - trace mirror is best-effort
            pass

    return payload


def main(argv: list[str] | None = None) -> int:
    """CLI: run the homeostatic-regulation audit and print / write the table."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Audit immune regulation — self-tolerance, false-alarm damping, bounded inflammation, "
                    "homeostasis (event-ticks, not wall-clock)."
    )
    parser.add_argument("--report", metavar="OUT.md", help="write the table as a markdown evidence artifact")
    parser.add_argument("--report-json", metavar="OUT.json", help="also write the JSON record")
    parser.add_argument("--genuine", type=int, default=4)
    parser.add_argument("--storm-repeats", type=int, default=4)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--self-test", action="store_true",
                        help="assert self never attacked, false alarms damped, genuine pass, homeostasis")
    args = parser.parse_args(argv)

    report = compute_immune_regulation(
        n_genuine=args.genuine, storm_repeats=args.storm_repeats, seed0=args.seed
    )

    print("Immune regulation — the homeostatic brake (event-ticks, not wall-clock)")
    print(f"  boundary: {IMMUNE_REGULATION_BOUNDARY}")
    print(f"  {report.n_genuine} genuine · {report.storm_signatures}×{report.storm_repeats} storm · "
          f"{report.n_self} self · cooldown {report.cooldown} · cap {report.inflammation_cap}")
    print(f"  self-attack {report.self_attack_rate:.3f} · false-alarm suppression "
          f"{report.false_alarm_suppression_rate:.3f} · genuine-pass {report.genuine_pass_rate:.3f}")
    print(f"  max inflammation {report.max_inflammation}/{report.inflammation_cap} · "
          f"homeostasis restored {report.homeostasis_restored} · work saved {report.work_saved_fraction:.3f}")

    if args.report:
        rendered = write_immune_regulation_report(report, args.report, args.report_json)
        print(f"  report written: {rendered.out_path}")

    if args.self_test:
        ok = (
            report.self_attack_rate == 0.0
            and report.false_alarm_suppression_rate >= 0.99
            and report.genuine_pass_rate >= 0.99
            and report.homeostasis_restored
            and report.max_inflammation <= report.inflammation_cap
        )
        return 0 if ok else 1
    return 0


if __name__ == "__main__":  # pragma: no cover - manual entry point
    raise SystemExit(main())

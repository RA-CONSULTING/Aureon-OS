"""Gate-switchboard benchmark — can the Queen see the gates she is standing at?

Follows the repo's benchmark contract (see :mod:`aureon.design.benchmark` and
``scripts/validation/benchmark_live_multidaemon.py``): a tiered check list, a
``.json`` + ``.md`` pair with the same stem under ``docs/research/benchmarks/``,
and ``status == "pass"`` iff every *critical* check is ok.

Two things are measured, and they are measured differently on purpose.

**The panel is convened live.** ``auris_panel()`` runs the nine-node Auris voter
over whatever the organism actually is right now — HNC field, blended subfields,
the throne. What comes back is genuinely variable, so the critical tier only
asserts the properties that must hold whatever the reading says: the panel
convenes, nine nodes vote, and the share of its inputs that came from a real
measurement is reported honestly. The consensus itself is informational.

**The chain is walked over synthetic-but-honest readings.** ``run_chain`` reads
the organism through ``read_organism``, so a live walk cannot be steered; it
would prove only that today's field happened to stop at a particular gate. So
the real ``run_chain`` — real loop, real ``evaluate``, real publish — is driven
with ``read_organism`` temporarily returning a constructed :class:`GateReading`.
Those readings are synthetic but not invented: the panel emits confidence at
0.3 / 0.7 / 0.95 and evidence ratios at k/PANEL_INPUTS, and every value used here is one
the live panel can actually produce. A live walk runs too, and is asserted only
to complete.

The critical tier is the safety surface, and every item in it is a promise the
switchboard's own docstrings make:

- HUMAN_HELD actions return HOLD — moving money, revealing credentials and
  lodging an official filing have no automatic executor anywhere in this repo,
  and confidence is not the missing ingredient;
- divergence ≥ 0.35 forces REDO — a body of two minds does not get to act,
  however confident one voice is (the bar matches ``grounded_action._DIVERGENCE_CAUTION``);
- confidence is the panel's tempered by its evidence, so a unanimous panel
  voting on defaults cannot advance anything;
- a blind organism REDOes rather than guessing;
- the chain stops at the first gate that does not advance.

Offline and network-free; safe for nightly CI.
"""

from __future__ import annotations

import json
import time
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from aureon.gates import switchboard
from aureon.gates.panel import PANEL_INPUTS, FieldVault, auris_panel, build_vault
from aureon.gates.switchboard import (
    ADVANCE,
    DEFAULT_CHAIN,
    HOLD,
    HUMAN_HELD,
    REDO,
    Gate,
    GateReading,
    evaluate,
    read_organism,
    run_chain,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REPORTS_DIR = REPO_ROOT / "docs" / "research" / "benchmarks"
REPORT_STEM = "gate_switchboard_benchmark"
NAME = "aureon-gate-switchboard-benchmark"

DECISIONS = (ADVANCE, REDO, HOLD)

# Values the live panel can actually emit: the Auris tally returns 0.3 / 0.7 /
# 0.95, and PanelReading.evidence_ratio is grounded_inputs out of PANEL_INPUTS.
# The denominator is imported rather than written out — hard-coding it as 8 once
# put a ratio of 1.0 in this sweep that build_vault could never produce.
_PANEL_TIERS = (0.3, 0.7, 0.95)
_EVIDENCE_RATIOS = tuple(k / PANEL_INPUTS for k in range(PANEL_INPUTS + 1))
_DIVERGENCES = (0.0, 0.1, 0.34, 0.35, 0.6)


def _reading(
    *,
    confidence: float | None = 0.95,
    evidence: float | None = 1.0,
    divergence: float | None = 0.08,
    coherence: float | None = 0.82,
    consensus: str | None = "BUY",
    lighthouse: bool = True,
) -> GateReading:
    return GateReading(
        coherence=coherence,
        divergence=divergence,
        life_score=0.71,
        panel_consensus=consensus,
        panel_confidence=confidence,
        panel_evidence=evidence,
        lighthouse=lighthouse,
    )


# A grounded, confident organism: 9/9 nodes agreeing on every input measured.
STRONG = _reading()
# The same panel with nothing under it — unanimous, and worth nothing.
UNGROUNDED = _reading(evidence=0.0)
# A body arguing with itself.
DIVERGENT = _reading(divergence=0.42)
# Enough to start work, not enough to call it correct.
MIDDLING = _reading(confidence=0.7, evidence=0.75)
# No self-perception at all.
BLIND = GateReading()


class _RecordingBus:
    """A thought bus that only remembers, so publication can be observed."""

    def __init__(self) -> None:
        self.thoughts: list[Any] = []

    def publish(self, thought: Any) -> None:
        self.thoughts.append(thought)

    def topics(self) -> list[str]:
        return [getattr(t, "topic", "") for t in self.thoughts]


def _check(
    name: str,
    ok: bool,
    detail: str,
    *,
    critical: bool = True,
    metrics: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "check": name,
        "ok": bool(ok),
        "critical": bool(critical),
        "detail": detail,
        "metrics": metrics or {},
    }


def _fmt(value: float | None) -> str:
    """Render a live scalar without pretending to precision it does not have."""
    return "unknown" if value is None else f"{value:.4f}"


def _grounded_node_count(grounded_slices: Any) -> int:
    """How many of the nine nodes had their slice measured."""
    from aureon.gates.panel import NODE_SLICE

    return sum(1 for s in NODE_SLICE.values() if s in grounded_slices)


def _chain_over(
    reading: GateReading,
    *,
    context: dict[str, Any] | None = None,
    bus: Any = None,
    on_verdict: Any = None,
) -> list[Any]:
    """Drive the real ``run_chain`` with a fixed reading of the organism.

    Only the sensor is substituted. The loop, ``evaluate``, the publish and the
    stop-on-first-non-advance behaviour under test are all the production ones.
    """
    original = switchboard.read_organism
    switchboard.read_organism = lambda _bus=None: reading  # type: ignore[assignment]
    try:
        return run_chain(context, bus=bus, on_verdict=on_verdict)
    finally:
        switchboard.read_organism = original  # type: ignore[assignment]


# ─── panel: convened live ──────────────────────────────────────────


def _check_panel() -> tuple[list[dict[str, Any]], Any]:
    started = time.perf_counter()
    panel = auris_panel()
    elapsed_ms = (time.perf_counter() - started) * 1000.0

    checks = [
        _check(
            "panel_convenes",
            panel.available and panel.consensus is not None,
            (
                f"nine-node Auris panel returned consensus '{panel.consensus}' at confidence {panel.confidence}"
                if panel.available
                else f"panel unavailable: {panel.blocker}"
            ),
            metrics={"available": panel.available, "blocker": panel.blocker, "convene_ms": round(elapsed_ms, 2)},
        ),
        _check(
            "nine_nodes_voted",
            panel.total == 9 and 0 <= panel.agreeing <= panel.total,
            f"{panel.agreeing}/{panel.total} nodes agreed with the consensus",
            metrics={"agreeing": panel.agreeing, "total": panel.total},
        ),
    ]

    vault, grounded = build_vault()
    ratio_ok = (
        panel.total_inputs == PANEL_INPUTS
        and 0.0 <= panel.evidence_ratio <= 1.0
        and abs(panel.evidence_ratio - panel.grounded_inputs / PANEL_INPUTS) < 1e-9
        # The denominator must be reachable, or every downstream confidence is
        # silently discounted by a constant that looks like evidence.
        and panel.grounded_inputs <= PANEL_INPUTS
        and len(vault.grounded_slices) == grounded
    )
    checks.append(
        _check(
            "panel_evidence_reported_honestly",
            ratio_ok,
            f"{panel.grounded_inputs}/{PANEL_INPUTS} of the panel's inputs came from a real measurement "
            f"(evidence_ratio {panel.evidence_ratio:.4f}) — a consensus reached on defaults is visible as such",
            metrics={
                "grounded_inputs": panel.grounded_inputs,
                "total_inputs": panel.total_inputs,
                "evidence_ratio": round(panel.evidence_ratio, 4),
                "vault_rebuild_grounded": grounded,
                "grounded_slices": sorted(vault.grounded_slices),
            },
        )
    )
    checks.append(
        _check(
            "ungrounded_nodes_named",
            len(panel.ungrounded_nodes) == 9 - _grounded_node_count(vault.grounded_slices),
            f"{len(panel.ungrounded_nodes)} of 9 nodes voted on a constant rather than a measurement: "
            f"{', '.join(panel.ungrounded_nodes) or 'none'}",
            critical=False,
            metrics={"ungrounded_nodes": list(panel.ungrounded_nodes)},
        )
    )

    # "No LLM calls. Pure vault inspection." — same vault in, same vote out.
    try:
        from aureon.vault.auris_metacognition import AurisMetacognition

        fixed = FieldVault(
            last_casimir_force=1.5,
            last_lambda_t=0.42,
            dominant_frequency_hz=7.83,
            love_amplitude=0.9,
            gratitude_score=0.8,
            cortex_snapshot={"a": 0.9, "b": 0.6},
            dominant_chakra="COHERENT",
            max_size=4,
        )
        first = AurisMetacognition().vote(fixed)
        second = AurisMetacognition().vote(fixed)
        deterministic = (
            first.consensus == second.consensus
            and first.confidence == second.confidence
            and first.agreeing == second.agreeing
        )
        checks.append(
            _check(
                "panel_vote_deterministic",
                deterministic,
                f"identical vault votes identically: '{first.consensus}' at {first.confidence} "
                f"({first.agreeing}/{first.total}) both times",
                metrics={"consensus": first.consensus, "confidence": first.confidence},
            )
        )
    except Exception as exc:  # noqa: BLE001
        checks.append(_check("panel_vote_deterministic", False, f"raised {type(exc).__name__}: {exc}"))

    checks.append(
        _check(
            "live_panel_reading",
            True,
            f"consensus '{panel.consensus}' · confidence {panel.confidence} · "
            f"{panel.agreeing}/{panel.total} agreeing · lighthouse_cleared={panel.lighthouse_cleared} · "
            f"evidence {panel.evidence_ratio:.0%}",
            critical=False,
            metrics=panel.to_dict(),
        )
    )
    checks.append(
        _check(
            "panel_convene_latency",
            True,
            f"nine nodes convened over the live organism in {elapsed_ms:.1f} ms",
            critical=False,
            metrics={"convene_ms": round(elapsed_ms, 2), "cortex_nodes": len(vault.cortex_snapshot or {})},
        )
    )
    return checks, panel


# ─── switchboard: the safety surface ───────────────────────────────


def _check_human_held() -> list[dict[str, Any]]:
    """No hand exists for these. HOLD however strong the evidence."""
    act = DEFAULT_CHAIN[0]
    wrong = [
        a for a in sorted(HUMAN_HELD)
        if evaluate(act, STRONG, context={"action": a}).decision != HOLD
    ]
    # Case must not be a way around it.
    cased = evaluate(act, STRONG, context={"action": "TRANSFER"}).decision
    checks = [
        _check(
            "human_held_actions_hold",
            not wrong and cased == HOLD,
            (
                f"all {len(HUMAN_HELD)} human-held actions ({', '.join(sorted(HUMAN_HELD))}) HOLD at a "
                "non-human gate on a 0.95-confidence reading, case-insensitively"
                if not wrong and cased == HOLD
                else f"did not hold: {wrong or ['TRANSFER']}"
            ),
            metrics={"human_held": sorted(HUMAN_HELD), "failed": wrong},
        )
    ]

    submit = DEFAULT_CHAIN[-1]
    verdict = evaluate(submit, STRONG)
    checks.append(
        _check(
            "human_gate_holds_at_full_confidence",
            submit.requires_human and verdict.decision == HOLD and verdict.confidence == 0.95,
            f"gate '{submit.name}' returns {verdict.decision} at confidence {verdict.confidence} — "
            "the reasoning is the absence of an executor, not a shortfall of evidence",
            metrics={"gate": submit.name, "decision": verdict.decision, "confidence": verdict.confidence,
                     "reasoning": verdict.reasoning},
        )
    )

    # An ordinary action at an ordinary gate must still be able to advance,
    # or "everything holds" would trivially satisfy the check above.
    ordinary = evaluate(act, STRONG, context={"action": "draft"})
    checks.append(
        _check(
            "ordinary_actions_can_advance",
            ordinary.decision == ADVANCE,
            f"action 'draft' at gate '{act.name}' -> {ordinary.decision} (HOLD is targeted, not universal)",
        )
    )
    return checks


def _check_divergence() -> list[dict[str, Any]]:
    """A body of two minds does not get to act."""
    act = DEFAULT_CHAIN[0]
    at_bar = evaluate(act, _reading(divergence=act.max_divergence))
    over = evaluate(act, DIVERGENT)
    under = evaluate(act, _reading(divergence=act.max_divergence - 0.01))

    forced = (
        at_bar.decision == REDO
        and over.decision == REDO
        and any(d.startswith("divergence") for d in over.dissent)
    )
    return [
        _check(
            "divergence_forces_redo",
            forced,
            f"divergence {act.max_divergence} (at the bar) and 0.42 both REDO on a 0.95-confidence "
            f"reading; dissent records {over.dissent}",
            metrics={"bar": act.max_divergence, "at_bar": at_bar.decision, "over_bar": over.decision},
        ),
        _check(
            "below_bar_still_advances",
            under.decision == ADVANCE,
            f"divergence {act.max_divergence - 0.01:.2f} -> {under.decision}; the bar is a threshold, not a blanket veto",
            metrics={"below_bar": under.decision},
        ),
        _check(
            "divergence_bar_matches_grounded_action",
            abs(act.max_divergence - 0.35) < 1e-9,
            f"gate bar {act.max_divergence} matches grounded_action._DIVERGENCE_CAUTION (0.35)",
            critical=False,
        ),
    ]


def _check_evidence_tempering() -> list[dict[str, Any]]:
    """Confidence is the panel's, tempered by how much of it was grounded."""
    act = DEFAULT_CHAIN[0]

    mismatches: list[str] = []
    for tier in _PANEL_TIERS:
        for ratio in _EVIDENCE_RATIOS:
            verdict = evaluate(act, _reading(confidence=tier, evidence=ratio))
            expected = tier * ratio
            if verdict.confidence is None or abs(verdict.confidence - expected) > 1e-9:
                mismatches.append(f"{tier}×{ratio:.3f}→{verdict.confidence}")

    ungrounded = evaluate(act, UNGROUNDED)
    ungrounded_ok = (
        ungrounded.decision == REDO
        and ungrounded.confidence == 0.0
        and any("real inputs" in d for d in ungrounded.dissent)
    )

    blind = evaluate(act, BLIND)
    blind_ok = blind.decision == REDO and blind.confidence is None and "blind" in " ".join(blind.dissent)

    return [
        _check(
            "confidence_tempered_by_evidence",
            not mismatches,
            f"confidence == panel_confidence × evidence_ratio across all "
            f"{len(_PANEL_TIERS) * len(_EVIDENCE_RATIOS)} tier×evidence combinations",
            metrics={"combinations": len(_PANEL_TIERS) * len(_EVIDENCE_RATIOS), "mismatches": mismatches[:5]},
        ),
        _check(
            "unanimous_on_defaults_cannot_advance",
            ungrounded_ok,
            f"0.95 confidence on 0/{PANEL_INPUTS} real inputs -> {ungrounded.decision} at confidence "
            f"{ungrounded.confidence}; dissent {ungrounded.dissent}",
        ),
        _check(
            "blind_organism_redoes",
            blind_ok,
            f"no reading at all -> {blind.decision} with dissent {blind.dissent} — it does not guess",
        ),
        _check(
            "low_evidence_flagged_even_when_advancing",
            any("real inputs" in d for d in evaluate(act, _reading(evidence=3 / PANEL_INPUTS)).dissent),
            f"a panel on {3/PANEL_INPUTS:.0%} real inputs carries a dissent line saying so",
            critical=False,
        ),
    ]


def _check_chain() -> list[dict[str, Any]]:
    """Walk the real chain over synthetic-but-honest readings."""
    checks: list[dict[str, Any]] = []

    seen: list[str] = []
    bus = _RecordingBus()
    full = _chain_over(STRONG, bus=bus, on_verdict=lambda v: seen.append(v.gate))
    names = [v.gate for v in full]
    decisions = [v.decision for v in full]
    walked = (
        names == [g.name for g in DEFAULT_CHAIN]
        and decisions == [ADVANCE, ADVANCE, ADVANCE, HOLD]
    )
    checks.append(
        _check(
            "chain_walks_to_the_human_gate",
            walked,
            f"grounded 0.95 reading: {' → '.join(f'{n}={d}' for n, d in zip(names, decisions))}",
            metrics={"gates": names, "decisions": decisions},
        )
    )
    checks.append(
        _check(
            "chain_notifies_and_publishes",
            seen == names and bus.topics() == [f"gates.{n}.verdict" for n in names],
            f"{len(seen)} on_verdict callback(s) and {len(bus.topics())} bus publication(s): {bus.topics()}",
            metrics={"topics": bus.topics()},
        )
    )

    stopped = _chain_over(MIDDLING)
    stop_ok = (
        len(stopped) == 2
        and stopped[0].decision == ADVANCE
        and stopped[1].gate == "validate"
        and stopped[1].decision == REDO
    )
    checks.append(
        _check(
            "chain_stops_at_first_non_advance",
            stop_ok,
            f"0.7 confidence on {MIDDLING.panel_evidence:.0%} evidence clears act's 0.45 bar and stops at validate's 0.55: "
            f"{[f'{v.gate}={v.decision}' for v in stopped]}",
            metrics={"verdicts": len(stopped), "trail": [f"{v.gate}={v.decision}" for v in stopped]},
        )
    )

    divergent_chain = _chain_over(DIVERGENT)
    checks.append(
        _check(
            "chain_halts_on_divergence",
            len(divergent_chain) == 1 and divergent_chain[0].decision == REDO,
            f"a divergent organism stops at the first gate after {len(divergent_chain)} verdict(s) — "
            "it never reaches the human gate",
        )
    )

    held = _chain_over(STRONG, context={"action": "wire"})
    checks.append(
        _check(
            "human_held_context_halts_chain_immediately",
            len(held) == 1 and held[0].gate == "act" and held[0].decision == HOLD,
            f"context action 'wire' HOLDs at the very first gate: {[f'{v.gate}={v.decision}' for v in held]}",
        )
    )
    return checks


def _check_live_chain() -> list[dict[str, Any]]:
    """The chain must also complete against whatever the organism is right now."""
    started = time.perf_counter()
    try:
        reading = read_organism()
        verdicts = run_chain({"action": "benchmark_probe"})
    except Exception as exc:  # noqa: BLE001
        return [_check("live_chain_completes", False, f"raised {type(exc).__name__}: {exc}")]
    elapsed_ms = (time.perf_counter() - started) * 1000.0

    ok = bool(verdicts) and all(v.decision in DECISIONS for v in verdicts)
    trail = [f"{v.gate}={v.decision}" for v in verdicts]
    return [
        _check(
            "live_chain_completes",
            ok,
            f"live walk produced {len(verdicts)} verdict(s), every decision in {DECISIONS}: {' → '.join(trail)}",
            metrics={"verdict_count": len(verdicts), "trail": trail},
        ),
        _check(
            "live_organism_reading",
            True,
            f"coherence={_fmt(reading.coherence)} · divergence={_fmt(reading.divergence)} · "
            f"life_score={_fmt(reading.life_score)} · panel={reading.panel_consensus}@{reading.panel_confidence} "
            f"on {'unknown' if reading.panel_evidence is None else f'{reading.panel_evidence:.0%}'} evidence",
            critical=False,
            metrics=reading.to_dict(),
        ),
        _check(
            "live_chain_outcome",
            True,
            f"stopped at '{verdicts[-1].gate}' with {verdicts[-1].decision}: {verdicts[-1].reasoning}",
            critical=False,
            metrics={
                "final_gate": verdicts[-1].gate,
                "final_decision": verdicts[-1].decision,
                "final_confidence": verdicts[-1].confidence,
                "dissent": verdicts[-1].dissent,
                "walk_ms": round(elapsed_ms, 2),
            },
        ),
    ]


def _check_distribution() -> list[dict[str, Any]]:
    """The ADVANCE / REDO / HOLD distribution over an honest sweep of readings."""
    counter: Counter[str] = Counter()
    by_gate: dict[str, Counter[str]] = {g.name: Counter() for g in DEFAULT_CHAIN}
    actions = ("draft", "validate", "submit")

    for tier in _PANEL_TIERS:
        for ratio in _EVIDENCE_RATIOS:
            for divergence in _DIVERGENCES:
                reading = _reading(confidence=tier, evidence=ratio, divergence=divergence)
                for action in actions:
                    for gate in DEFAULT_CHAIN:
                        decision = evaluate(gate, reading, context={"action": action}).decision
                        counter[decision] += 1
                        by_gate[gate.name][decision] += 1

    total = sum(counter.values())
    every_decision_reachable = all(counter[d] > 0 for d in DECISIONS)
    return [
        _check(
            "decision_distribution",
            True,
            " · ".join(f"{d}={counter[d]} ({counter[d] / total:.0%})" for d in DECISIONS)
            + f" over {total} gate evaluations",
            critical=False,
            metrics={
                "total_evaluations": total,
                "distribution": {d: counter[d] for d in DECISIONS},
                "by_gate": {g: dict(c) for g, c in by_gate.items()},
                "sweep": {
                    "panel_tiers": list(_PANEL_TIERS),
                    "evidence_ratios": [round(r, 4) for r in _EVIDENCE_RATIOS],
                    "divergences": list(_DIVERGENCES),
                    "actions": list(actions),
                },
            },
        ),
        _check(
            "all_three_decisions_reachable",
            every_decision_reachable,
            f"the sweep produced every decision the switchboard defines: "
            + ", ".join(f"{d}×{counter[d]}" for d in DECISIONS),
            metrics={"distribution": {d: counter[d] for d in DECISIONS}},
        ),
        _check(
            "gate_bars",
            True,
            " · ".join(
                f"{g.name}≥{g.min_confidence}{' (human-held)' if g.requires_human else ''}"
                for g in DEFAULT_CHAIN
            ),
            critical=False,
            metrics={
                g.name: {
                    "min_confidence": g.min_confidence,
                    "max_divergence": g.max_divergence,
                    "requires_human": g.requires_human,
                    "question": g.question,
                }
                for g in DEFAULT_CHAIN
            },
        ),
    ]


# ─── orchestration ─────────────────────────────────────────────────


def run_gates_benchmark() -> list[dict[str, Any]]:
    """Convene the real panel, walk the real chain; return tiered checks."""
    checks: list[dict[str, Any]] = []
    panel_checks, _panel = _check_panel()
    checks.extend(panel_checks)
    checks.extend(_check_human_held())
    checks.extend(_check_divergence())
    checks.extend(_check_evidence_tempering())
    checks.extend(_check_chain())
    checks.extend(_check_live_chain())
    checks.extend(_check_distribution())
    return checks


def build_report(checks: list[dict[str, Any]]) -> dict[str, Any]:
    """Assemble the canonical report dict from a check list."""
    critical = [c for c in checks if c["critical"]]
    info = [c for c in checks if not c["critical"]]
    critical_passed = sum(1 for c in critical if c["ok"])
    info_passed = sum(1 for c in info if c["ok"])
    # Was this run grounded, or did it prove its invariants against a blind
    # organism? The nine-node panel returns NEUTRAL at 0.7 with 7 of 9 agreeing
    # even with NO readings at all, so every critical check here passes on a
    # fresh CI runner with no live Aureon process. That is honest panel
    # behaviour, and the invariants are still worth asserting — but a green
    # report that never touched a real measurement must not be indistinguishable
    # from one that did. CI cannot supply a live organism, so the remedy is
    # disclosure rather than failure: the summary states it on its face.
    evidence = _reported_evidence(checks)
    grounded = _was_grounded(checks)
    return {
        "name": NAME,
        "schema_version": 1,
        "generated_at": datetime.now(UTC).isoformat(),
        "summary": {
            # A report with no critical checks has proven nothing. `0 == 0` made
            # build_report([]) return "pass", so a benchmark that silently
            # stopped collecting checks would ship green.
            "status": "pass" if critical and critical_passed == len(critical) else "fail",
            # `grounded: false` means: the invariants hold, but nothing here was
            # measured against a live field. Read status WITH this flag.
            "grounded": grounded,
            "panel_evidence_ratio": evidence,
            "critical_passed": critical_passed,
            "critical_total": len(critical),
            "informational_passed": info_passed,
            "informational_total": len(info),
            "check_count": len(checks),
        },
        "checks": checks,
    }


def _was_grounded(checks: list[dict[str, Any]]) -> bool:
    """Did this run read the canonical HNC field, or only the panel?

    The panel evidence ratio is the wrong signal, and using it was a real
    mistake: on a blind organism it still reads 2/7, because a couple of the
    nine nodes' inputs come from sources that survive an empty trace directory.
    A run with 0.29 evidence and coherence/divergence/life_score all null is
    blind, and reporting it grounded is exactly the fabrication this benchmark
    exists to catch.

    The honest test is whether the FIELD itself yielded a scalar. If Γ,
    divergence and the symbolic life score are all absent, nothing was measured,
    whatever the panel managed to assemble from defaults.
    """
    for c in checks:
        if c.get("check") != "live_organism_reading":
            continue
        metrics = c.get("metrics") or {}
        return any(
            isinstance(metrics.get(k), (int, float)) and not isinstance(metrics.get(k), bool)
            for k in ("coherence", "divergence", "life_score")
        )
    return False


def _reported_evidence(checks: list[dict[str, Any]]) -> float | None:
    """The panel evidence ratio a check actually recorded, or None.

    Read out of the emitted metrics rather than recomputed, so the disclosure
    cannot drift from what the checks themselves observed.
    """
    for c in checks:
        metrics = c.get("metrics") or {}
        for key in ("evidence_ratio", "panel_evidence", "evidence"):
            value = metrics.get(key)
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                return float(value)
    return None


def _render_markdown(report: dict[str, Any]) -> str:
    s = report["summary"]
    lines = [
        "# Aureon Gate Switchboard — Benchmark",
        "",
        f"- **Status**: `{s['status']}`",
        f"- **Generated**: {report['generated_at']}",
        f"- **Critical**: {s['critical_passed']}/{s['critical_total']} passed",
        f"- **Informational**: {s['informational_passed']}/{s['informational_total']} passed",
        "",
        "The switchboard is the Queen's reflective chain — *should I do this? 1: no, redo.",
        "2: yes, press on to the next logic gate* — and it answers ADVANCE / REDO / HOLD for",
        "any lane, trading or grants alike.",
        "",
        "The nine-node Auris panel is convened **live**, over whatever the organism is right",
        "now, so its consensus is reported rather than asserted. The chain is walked over",
        "**synthetic-but-honest** readings — every confidence is one of the panel's real",
        "tiers (0.3 / 0.7 / 0.95) and every evidence ratio is a real k/PANEL_INPUTS — because",
        "a live",
        "walk cannot be steered and would only prove where today's field happened to stop.",
        "A live walk runs too, and is asserted only to complete.",
        "",
        "Critical checks are the safety surface: human-held actions HOLD, divergence forces",
        "REDO, a unanimous panel on no evidence cannot advance anything, a blind organism",
        "does not guess, and the chain stops at the first gate that does not advance.",
        "",
        "| Check | Tier | Result | Detail |",
        "| --- | --- | --- | --- |",
    ]
    for c in report["checks"]:
        tier = "critical" if c["critical"] else "info"
        mark = "✅" if c["ok"] else ("❌" if c["critical"] else "⚠️")
        detail = str(c["detail"]).replace("|", "\\|")
        lines.append(f"| `{c['check']}` | {tier} | {mark} | {detail} |")
    lines.append("")

    dist = next((c["metrics"] for c in report["checks"] if c["check"] == "decision_distribution"), None)
    if dist:
        lines.extend(
            [
                "## Decision distribution",
                "",
                f"{dist['total_evaluations']} gate evaluations over "
                f"{len(dist['sweep']['panel_tiers'])} panel tiers × "
                f"{len(dist['sweep']['evidence_ratios'])} evidence ratios × "
                f"{len(dist['sweep']['divergences'])} divergences × "
                f"{len(dist['sweep']['actions'])} actions.",
                "",
                "| Gate | ADVANCE | REDO | HOLD |",
                "| --- | --- | --- | --- |",
            ]
        )
        for gate, counts in dist["by_gate"].items():
            lines.append(
                f"| `{gate}` | {counts.get(ADVANCE, 0)} | {counts.get(REDO, 0)} | {counts.get(HOLD, 0)} |"
            )
        totals = dist["distribution"]
        lines.append(
            f"| **all** | **{totals[ADVANCE]}** | **{totals[REDO]}** | **{totals[HOLD]}** |"
        )
        lines.append("")

    lines.append("*Generated by `python -m aureon.gates.benchmark`.*")
    lines.append("")
    return "\n".join(lines)


def _write_artifacts(report: dict[str, Any], *, reports_dir: Path | None = None) -> list[str]:
    """Write the ``.json`` + ``.md`` pair; returns the paths written."""
    target = reports_dir or DEFAULT_REPORTS_DIR
    target.mkdir(parents=True, exist_ok=True)
    json_path = target / f"{REPORT_STEM}.json"
    md_path = target / f"{REPORT_STEM}.md"
    json_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    md_path.write_text(_render_markdown(report), encoding="utf-8")
    return [str(json_path), str(md_path)]


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint: run, write artefacts, exit non-zero on critical failure."""
    checks = run_gates_benchmark()
    report = build_report(checks)
    written = _write_artifacts(report)
    s = report["summary"]
    print(
        f"{NAME}: {s['status']} — critical {s['critical_passed']}/{s['critical_total']}, "
        f"info {s['informational_passed']}/{s['informational_total']}"
    )
    for c in checks:
        mark = "PASS" if c["ok"] else ("FAIL" if c["critical"] else "warn")
        tier = "  " if c["critical"] else " ~"
        print(f" {tier} [{mark}] {c['check']:40} {c['detail']}")
    for path in written:
        print(f"  wrote {path}")
    return 0 if s["status"] == "pass" else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())


__all__ = [
    "NAME",
    "REPORT_STEM",
    "DEFAULT_REPORTS_DIR",
    "run_gates_benchmark",
    "build_report",
    "main",
]

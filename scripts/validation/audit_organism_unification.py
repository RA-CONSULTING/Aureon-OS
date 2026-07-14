#!/usr/bin/env python3
"""
Audit + benchmark the organism's unification edges.

Exercises each connective edge that Phase 19–20 revived and prints an honest
PASS/DEAD report. Exits non-zero if any CRITICAL edge is dead, so it can gate CI
or a deploy. Offline-safe — no network, no OS deps.

Usage:
    AUREON_LLM_OFFLINE=1 AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS=1 \
        python -m scripts.validation.audit_organism_unification
"""

from __future__ import annotations

import os
import sys
import time

os.environ.setdefault("AUREON_LLM_OFFLINE", "1")
os.environ.setdefault("AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS", "1")


def _check(name: str, ok: bool, detail: str, critical: bool = True) -> dict:
    return {"edge": name, "ok": bool(ok), "detail": detail, "critical": critical}


def run_audit() -> list[dict]:
    from aureon.core.aureon_thought_bus import Thought, get_thought_bus
    from aureon.core.hnc_field import read_canonical_field

    bus = get_thought_bus()
    results: list[dict] = []

    # Edge 1 — the canonical field: publish → read back through the shared accessor
    bus.publish(Thought(source="hnc_live_daemon", topic="symbolic.life.pulse",
                        payload={"symbolic_life_score": 0.42, "coherence_gamma": 0.5,
                                 "source": "audit"}))
    field = read_canonical_field(bus)
    results.append(_check("canonical_field", field.available and field.symbolic_life_score == 0.42,
                          f"sls={field.symbolic_life_score} source={field.source}"))

    # Edge 1b — flood-proof: bury the pulse under a baton flood, must still read
    for i in range(400):
        bus.publish(Thought(source=f"m{i}", topic="baton.link", payload={"module": f"m{i}"}))
    field2 = read_canonical_field(bus)
    results.append(_check("field_flood_proof", field2.available and field2.symbolic_life_score == 0.42,
                          f"sls under 400-msg flood={field2.symbolic_life_score}"))

    # Edge 2 — grounded gate senses the field (low SLS + risky → veto)
    bus.publish(Thought(source="hnc_live_daemon", topic="symbolic.life.pulse",
                        payload={"symbolic_life_score": 0.08, "source": "audit"}))
    from aureon.operator.grounded_action import GroundedActionGate

    v = GroundedActionGate(bus=bus, enable_llm=False).ground("delete_file", {"path": "x"})
    results.append(_check("gate_senses_field", v.verdict == "VETOED" and v.symbolic_life_score == 0.08,
                          f"verdict={v.verdict} sls={v.symbolic_life_score}"))

    # Edge 3 — mesh broadcast reaches receive_mycelium_message
    from aureon.core.aureon_mycelium import get_mycelium
    from aureon.operator.aureon_operator import broadcast_to_mesh

    seen: dict = {}

    class _Rcv:
        def receive_mycelium_message(self, mt, pl):
            seen["hit"] = (mt, pl)

    get_mycelium().connect_subsystem("audit_rcv", _Rcv())
    broadcast_to_mesh("audit.mesh", {"v": 1})
    results.append(_check("mesh_delivery", seen.get("hit") == ("audit.mesh", {"v": 1}),
                          f"delivered={seen.get('hit')}"))

    # Edge 4 — lighthouse → bus
    try:
        from aureon.analytics.aureon_lighthouse import (
            LighthouseEvent,
            LighthouseEventType,
            LighthousePatternDetector,
        )

        LighthousePatternDetector()._emit_event(LighthouseEvent(
            event_type=LighthouseEventType.COHERENCE_COLLAPSE, timestamp=time.time(),
            severity=0.9, symbols=["BTC"], message="audit"))
        got = bus.recall("lighthouse.event", limit=1) or []
        results.append(_check("lighthouse_to_bus", bool(got), f"events={len(got)}"))
    except Exception as exc:  # noqa: BLE001
        results.append(_check("lighthouse_to_bus", False, f"error: {exc}"))

    # Edge 4b — sub-field visibility: a producer's local field is sensed
    from aureon.core.hnc_field import publish_subfield, read_subfields

    class _State:
        symbolic_life_score = 0.51
        coherence_gamma = 0.6
        consciousness_level = "AWARE"

    publish_subfield("queen_cortex", _State(), bus=bus)
    subs = read_subfields(bus)
    results.append(_check("subfield_visibility", "queen_cortex" in subs,
                          f"sources={sorted(subs.keys())}", critical=False))

    # Edge 5 — connectome telemetry: baton ear + pulse + auto-weave
    from aureon.core.aureon_connectome import get_connectome

    c = get_connectome()
    c._on_baton(Thought(source="aureon.audit.mod", topic="baton.link",
                        payload={"module": "aureon.audit.mod"}))
    status = c.status()
    results.append(_check("connectome_baton_ear", status["baton_linked"] > 0,
                          f"baton_linked={status['baton_linked']}"))
    c.pulse()
    pulse_got = bus.recall("organism.connectome.pulse", limit=1) or []
    results.append(_check("connectome_pulse", bool(pulse_got), f"pulses={len(pulse_got)}"))
    c.sweep_once(batch_size=15, weave_batch=0)
    wr = c.sweep_once(batch_size=1, weave_batch=5)
    results.append(_check("connectome_autoweave", wr["woven"] >= 1,
                          f"woven_this_cycle={wr['woven']} total={c.status()['woven']}", critical=False))

    return results


def main() -> int:
    print("═" * 70)
    print("AUREON ORGANISM UNIFICATION — audit + benchmark")
    print("═" * 70)
    results = run_audit()
    dead_critical = 0
    for r in results:
        mark = "✅ PASS" if r["ok"] else ("❌ DEAD" if r["critical"] else "⚠️  DEAD")
        print(f"  {mark}  {r['edge']:24} {r['detail']}")
        if not r["ok"] and r["critical"]:
            dead_critical += 1
    passed = sum(1 for r in results if r["ok"])
    print("─" * 70)
    print(f"  {passed}/{len(results)} edges live · {dead_critical} critical dead")
    print("═" * 70)
    return 1 if dead_critical else 0


if __name__ == "__main__":
    sys.exit(main())

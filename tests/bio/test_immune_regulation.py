"""Tests for immune regulation — the homeostatic brake.

The regulatory governor enforces self-tolerance (a benign signal is never mounted against), damps a
false-alarm storm with a refractory cooldown, never suppresses a genuine novel threat, bounds concurrent
inflammation at a cap, and returns to homeostasis when alarms quiet. Deterministic, measured in event-ticks
(never wall-clock). Synthetic only — no real subject, never a claim about a person.
"""

from __future__ import annotations

import json

from aureon.bio import immune_regulation as ir
from aureon.bio.swarm_defense import ThreatReport

_FORBIDDEN = ("health", "aura", "emotion", "spirit", "diagnos", "disease", "personality")


def _threat(kind="mutated_invariant", identity="p-1", severity=2):
    return ThreatReport(threat_id=identity, kind=kind, description=f"{kind}:{identity}", severity=severity)


def _report():
    return ir.compute_immune_regulation(n_genuine=4, storm_signatures=3, storm_repeats=4, n_self=4, seed0=0)


# ── the governor ────────────────────────────────────────────────────────────────────────────────


def test_self_is_never_mounted_against():
    gov = ir.RegulatoryGovernor()
    out = gov.regulate(_threat(identity="self-1", severity=0))
    assert out.decision == "suppress" and out.reason == "self_tolerance" and out.is_self


def test_genuine_novel_threat_is_allowed():
    gov = ir.RegulatoryGovernor()
    out = gov.regulate(_threat(identity="p-novel"))
    assert out.decision == "allow" and out.reason == "genuine_threat"


def test_refractory_cooldown_damps_repeats_then_readmits():
    gov = ir.RegulatoryGovernor(cooldown=3, inflammation_cap=6)
    t = _threat(identity="p-repeat")
    assert gov.regulate(t).decision == "allow"       # first sight
    for _ in range(3):                                # the next `cooldown` alarms are refractory
        o = gov.regulate(t)
        assert o.decision == "suppress" and o.reason == "refractory_cooldown"
    o = gov.regulate(t)                               # cooldown elapsed → admitted again
    assert o.decision == "allow"


def test_inflammation_is_bounded_by_the_cap():
    gov = ir.RegulatoryGovernor(cooldown=20, inflammation_cap=4)  # long cooldown keeps them all active
    peak = 0
    capped = 0
    for i in range(7):
        o = gov.regulate(_threat(identity=f"flood-{i}"))
        peak = max(peak, o.inflammation)
        if o.reason == "inflammation_cap":
            capped += 1
    assert peak <= 4          # never exceeds the cap
    assert capped == 3        # cap+3 distinct → 4 allowed, 3 deferred


def test_tick_resolves_inflammation_to_homeostasis():
    gov = ir.RegulatoryGovernor(cooldown=3)
    gov.regulate(_threat(identity="p-x"))
    assert gov.inflammation == 1
    for _ in range(4):
        gov.tick()
    assert gov.inflammation == 0   # returns to baseline once the cooldown elapses


# ── wiring into the layer ───────────────────────────────────────────────────────────────────────


def test_on_confirmed_defense_registers_cooldown():
    gov = ir.RegulatoryGovernor()
    assert ir.on_confirmed_defense({"kind": "mutated_invariant", "threat_id": "p", "confirmed": False}, gov) is False
    assert ir.on_confirmed_defense({"kind": "mutated_invariant", "threat_id": "p", "confirmed": True}, gov) is True
    assert ir.on_confirmed_defense({"malformed": True}, gov) is False  # tolerant, never raises
    # the just-registered threat is now refractory
    assert gov.regulate(_threat(identity="p")).reason == "refractory_cooldown"


def test_install_immune_regulation_closes_the_loop():
    published = []

    class _Bus:
        def subscribe(self, topic, handler):
            self._topic, self._handler = topic, handler

        def publish(self, thought):
            published.append(thought)
            if getattr(thought, "topic", None) == self._topic:
                self._handler(thought)

    from aureon.core.aureon_thought_bus import Thought

    bus = _Bus()
    gov = ir.install_immune_regulation(bus=bus)
    bus.publish(Thought(source="swarm_defense", topic="bio.swarm_defense.run",
                        payload={"threat_id": "p-loop", "kind": "mutated_invariant", "confirmed": True}))
    assert gov.regulate(_threat(identity="p-loop")).reason == "refractory_cooldown"


# ── the report ─────────────────────────────────────────────────────────────────────────────────


def test_report_governs_without_autoimmunity_or_over_suppression():
    report = _report()
    assert report.self_attack_rate == 0.0          # no autoimmunity
    assert report.false_alarm_suppression_rate >= 0.99
    assert report.genuine_pass_rate == 1.0         # novelty always passes
    assert report.max_inflammation <= report.inflammation_cap
    assert report.homeostasis_restored
    assert report.work_saved_fraction > 0.0


def test_compute_is_deterministic():
    assert _report().to_dict() == _report().to_dict()


def test_write_report_writes_md_and_json(tmp_path):
    report = _report()
    out_md = tmp_path / "reg.md"
    out_json = tmp_path / "reg.json"
    rendered = ir.write_immune_regulation_report(report, out_md, out_json)
    assert out_md.exists() and out_md.stat().st_size > 0
    assert out_json.exists() and out_json.stat().st_size > 0
    assert rendered.out_path == str(out_md)
    md = out_md.read_text(encoding="utf-8")
    assert ir.IMMUNE_REGULATION_BOUNDARY in md
    loaded = json.loads(out_json.read_text(encoding="utf-8"))
    assert loaded["self_attack_rate"] == report.self_attack_rate
    assert loaded["boundary"] == ir.IMMUNE_REGULATION_BOUNDARY


def test_write_report_is_byte_identical_on_rewrite(tmp_path):
    report = _report()
    a_md, a_json = tmp_path / "a.md", tmp_path / "a.json"
    b_md, b_json = tmp_path / "b.md", tmp_path / "b.json"
    ir.write_immune_regulation_report(report, a_md, a_json)
    ir.write_immune_regulation_report(report, b_md, b_json)
    assert a_md.read_bytes() == b_md.read_bytes()
    assert a_json.read_bytes() == b_json.read_bytes()


def test_boundary_present_and_no_subject_claims():
    low = ir.IMMUNE_REGULATION_BOUNDARY.lower()
    for w in _FORBIDDEN:
        assert w not in low


def test_module_has_no_person_reading_surface():
    names = [n.lower() for n in dir(ir)]
    for banned in ("face", "speaker", "voice", "pose", "emotion", "identity", "biometric"):
        assert not any(banned in n for n in names), f"unexpected {banned!r} surface"


def test_emit_publishes_to_bus():
    published = []

    class _Bus:
        def publish(self, thought):
            published.append(thought)

    report = _report()
    payload = ir.emit_immune_regulation(report, bus=_Bus(), trace=False)
    assert payload["self_attack_rate"] == report.self_attack_rate
    assert len(published) == 1
    assert published[0].topic == ir.REGULATION_RUN_TOPIC
    assert published[0].payload["boundary"] == ir.IMMUNE_REGULATION_BOUNDARY


def test_emit_tolerates_throwing_bus():
    class _BadBus:
        def publish(self, thought):
            raise RuntimeError("bus down")

    report = _report()
    payload = ir.emit_immune_regulation(report, bus=_BadBus(), trace=False)  # must not raise
    assert payload["self_attack_rate"] == report.self_attack_rate

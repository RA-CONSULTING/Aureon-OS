"""Tests for immune memory — recall of neutralized threats and the secondary response.

A confirmed, neutralized threat's content signature is committed to a bounded memory; a repeat exposure is
recognized and answered by a cheap secondary response, while a novel threat is not falsely recognized and a
benign/self signal is never remembered (self-tolerance). Cost is measured in verification work-units, never
wall-clock. Synthetic only — no real subject, never a claim about a person.
"""

from __future__ import annotations

import json

from aureon.bio import immune_memory as im
from aureon.bio.swarm_defense import DefenseResult, ThreatReport

_FORBIDDEN = ("health", "aura", "emotion", "spirit", "diagnos", "disease", "personality")


def _threat(kind="mutated_invariant", identity="p-1", severity=2):
    return ThreatReport(threat_id=identity, kind=kind, description=f"{kind}:{identity}", severity=severity)


def _report():
    return im.compute_immune_memory(n_threats=6, repeats=2, n_novel=5, n_self=4, seed0=0)


# ── signatures ────────────────────────────────────────────────────────────────────────────────────


def test_signature_is_deterministic_and_content_bound():
    a = _threat(identity="parasite-A")
    a2 = _threat(identity="parasite-A")  # same identity → same signature
    b = _threat(identity="parasite-B")
    assert im.threat_signature(a) == im.threat_signature(a2)
    assert im.threat_signature(a) != im.threat_signature(b)
    # kind participates in the identity
    assert im.threat_signature(_threat(kind="injected_instruction", identity="parasite-A")) != im.threat_signature(a)


# ── the store ───────────────────────────────────────────────────────────────────────────────────


def test_recognize_misses_before_and_hits_after_remember():
    mem = im.ImmuneMemory()
    t = _threat(identity="p-x")
    assert mem.recognize(t) is None
    assert mem.remember(t) is not None
    assert mem.recognize(t) is not None


def test_benign_self_is_never_remembered():
    mem = im.ImmuneMemory()
    benign = _threat(identity="self-1", severity=0)
    assert mem.remember(benign) is None
    assert mem.recognize(benign) is None
    assert len(mem) == 0


def test_capacity_is_bounded_with_deterministic_eviction():
    mem = im.ImmuneMemory(capacity=3)
    for i in range(6):
        mem.remember(_threat(identity=f"p-{i}"))
    assert len(mem) == 3
    assert mem.evictions == 3
    # the three most-recently committed survive; the oldest were evicted (FIFO)
    assert mem.recognize(_threat(identity="p-5")) is not None
    assert mem.recognize(_threat(identity="p-0")) is None


def test_respond_primary_then_secondary():
    mem = im.ImmuneMemory()
    t = _threat(identity="p-recur")
    first = mem.respond(t)
    assert first.tier == "primary" and first.cost == im.PRIMARY_COST and not first.recognized and first.committed
    second = mem.respond(t)
    assert second.tier == "secondary" and second.cost == im.SECONDARY_COST and second.recognized and second.escalated
    assert second.cost < first.cost  # faster (in work-units)


def test_respond_novel_and_self_are_not_recognized():
    mem = im.ImmuneMemory()
    mem.respond(_threat(identity="p-known"))
    assert not mem.respond(_threat(identity="p-other")).recognized  # specificity
    self_out = mem.respond(_threat(identity="self-x", severity=0))
    assert not self_out.recognized and not self_out.committed and self_out.is_self


# ── wiring into the layer ───────────────────────────────────────────────────────────────────────


def test_remember_from_defense_commits_only_when_confirmed():
    mem = im.ImmuneMemory()
    t = _threat(identity="p-def")
    unconfirmed = DefenseResult(threat_id="p-def", kind="mutated_invariant", n_defenders=9, n_threat=1,
                                n_clear=8, n_abstain=0, quorum=5, confirmed=False, confidence=0.3,
                                tolerated_faults=4, leaderless=True, votes=[])
    assert im.remember_from_defense(t, unconfirmed, mem) is None
    confirmed = DefenseResult(threat_id="p-def", kind="mutated_invariant", n_defenders=9, n_threat=9,
                              n_clear=0, n_abstain=0, quorum=5, confirmed=True, confidence=0.95,
                              tolerated_faults=4, leaderless=True, votes=[])
    assert im.remember_from_defense(t, confirmed, mem) is not None
    assert mem.recognize(t) is not None


def test_on_confirmed_defense_reads_bus_payload():
    mem = im.ImmuneMemory()
    assert im.on_confirmed_defense({"kind": "mutated_invariant", "threat_id": "p-bus", "confirmed": False}, mem) is None
    assert im.on_confirmed_defense({"kind": "mutated_invariant", "threat_id": "p-bus", "confirmed": True}, mem) is not None
    assert im.on_confirmed_defense({"malformed": True}, mem) is None  # tolerant, never raises
    # the committed signature matches what a matching ThreatReport would produce (the loop is coherent)
    assert mem.recognize(_threat(identity="p-bus")) is not None


def test_install_immune_memory_closes_the_loop():
    published = []

    class _Bus:
        def subscribe(self, topic, handler):
            self._handler = handler
            self._topic = topic

        def publish(self, thought):
            published.append(thought)
            if getattr(thought, "topic", None) == self._topic:
                self._handler(thought)

    from aureon.core.aureon_thought_bus import Thought

    bus = _Bus()
    mem = im.install_immune_memory(bus=bus)
    bus.publish(Thought(source="swarm_defense", topic="bio.swarm_defense.run",
                        payload={"threat_id": "p-loop", "kind": "mutated_invariant", "confirmed": True}))
    assert mem.recognize(_threat(identity="p-loop")) is not None


def test_remember_from_guard_report():
    mem = im.ImmuneMemory()

    class _Finding:
        def __init__(self, kind, target):
            self.kind, self.target = kind, target

    class _Intact:
        intact = True
        findings: list = []

    class _Breach:
        intact = False
        findings = [_Finding("constant", "ALPHA"), _Finding("canary", "test_A_p")]

    assert im.remember_from_guard_report(_Intact(), mem) == []
    recs = im.remember_from_guard_report(_Breach(), mem)
    assert len(recs) == 2
    assert mem.recognize_signature(im.signature_of("constant", "ALPHA")) is not None


# ── the report ─────────────────────────────────────────────────────────────────────────────────


def test_report_recognizes_repeats_blocks_novel_and_self():
    report = _report()
    assert report.recognition_rate == 1.0
    assert report.false_recall_rate == 0.0
    assert report.speedup > 1.0
    assert report.self_not_remembered
    assert report.specificity
    assert report.work_saved_fraction > 0.0
    assert report.memory_size == report.n_threats + report.n_novel  # real threats committed on first sight


def test_persistence_round_trips(tmp_path):
    path = tmp_path / "immune_memory.json"
    mem = im.ImmuneMemory(persist_path=path)
    mem.remember(_threat(identity="p-persist"))
    assert path.exists()
    reloaded = im.ImmuneMemory(persist_path=path)
    assert reloaded.recognize(_threat(identity="p-persist")) is not None


def test_compute_is_deterministic():
    assert _report().to_dict() == _report().to_dict()


def test_write_report_writes_md_and_json(tmp_path):
    report = _report()
    out_md = tmp_path / "mem.md"
    out_json = tmp_path / "mem.json"
    rendered = im.write_immune_memory_report(report, out_md, out_json)
    assert out_md.exists() and out_md.stat().st_size > 0
    assert out_json.exists() and out_json.stat().st_size > 0
    assert rendered.out_path == str(out_md)
    md = out_md.read_text(encoding="utf-8")
    assert im.IMMUNE_MEMORY_BOUNDARY in md
    loaded = json.loads(out_json.read_text(encoding="utf-8"))
    assert loaded["recognition_rate"] == report.recognition_rate
    assert loaded["boundary"] == im.IMMUNE_MEMORY_BOUNDARY


def test_write_report_is_byte_identical_on_rewrite(tmp_path):
    report = _report()
    a_md, a_json = tmp_path / "a.md", tmp_path / "a.json"
    b_md, b_json = tmp_path / "b.md", tmp_path / "b.json"
    im.write_immune_memory_report(report, a_md, a_json)
    im.write_immune_memory_report(report, b_md, b_json)
    assert a_md.read_bytes() == b_md.read_bytes()
    assert a_json.read_bytes() == b_json.read_bytes()


def test_boundary_present_and_no_subject_claims():
    report = _report()
    d = report.to_dict()
    assert d["boundary"] == im.IMMUNE_MEMORY_BOUNDARY
    low = im.IMMUNE_MEMORY_BOUNDARY.lower()
    for w in _FORBIDDEN:
        assert w not in low


def test_module_has_no_person_reading_surface():
    names = [n.lower() for n in dir(im)]
    for banned in ("face", "speaker", "voice", "pose", "emotion", "identity", "biometric"):
        assert not any(banned in n for n in names), f"unexpected {banned!r} surface"


def test_emit_publishes_to_bus():
    published = []

    class _Bus:
        def publish(self, thought):
            published.append(thought)

    report = _report()
    payload = im.emit_immune_memory(report, bus=_Bus(), trace=False)
    assert payload["recognition_rate"] == report.recognition_rate
    assert len(published) == 1
    assert published[0].topic == im.MEMORY_RUN_TOPIC
    assert published[0].payload["boundary"] == im.IMMUNE_MEMORY_BOUNDARY


def test_emit_tolerates_throwing_bus():
    class _BadBus:
        def publish(self, thought):
            raise RuntimeError("bus down")

    report = _report()
    payload = im.emit_immune_memory(report, bus=_BadBus(), trace=False)  # must not raise
    assert payload["recognition_rate"] == report.recognition_rate

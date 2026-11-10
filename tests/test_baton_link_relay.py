import json

from aureon.core import aureon_baton_link as bl
from aureon.core import aureon_thought_bus as tb


def _fresh_bus(monkeypatch, tmp_path):
    bus = tb.ThoughtBus(persist_path=str(tmp_path / "thoughts.jsonl"))
    monkeypatch.setattr(bl, "get_thought_bus", lambda *a, **k: bus)
    return bus


def test_relay_state_reaches_wildcard_subscriber(monkeypatch, tmp_path):
    bus = _fresh_bus(monkeypatch, tmp_path)
    seen = []
    bus.subscribe("organ.state.*", lambda t: seen.append(t))
    bl._RELAY_LINKED.add("orca_unified_kill_chain")
    for kind in ("trying", "seeing", "not_doing", "building"):
        bl.relay_state("orca_unified_kill_chain", kind, {"target": "capital:CN50"})
    bl.relay_state("orca_unified_kill_chain", "bogus", {})
    assert [t.topic for t in seen] == [
        "organ.state.trying", "organ.state.seeing", "organ.state.not_doing", "organ.state.building"]
    rows = [json.loads(l) for l in (tmp_path / "thoughts.jsonl").read_text().splitlines()]
    assert len(rows) == 4  # persisted so other processes can read it


def test_first_relay_announces_link_once(monkeypatch, tmp_path):
    bus = _fresh_bus(monkeypatch, tmp_path)
    seen = []
    bus.subscribe("organ.state.*", lambda t: seen.append(t))
    bl._RELAY_LINKED.discard("x.test_organ")
    bl.relay_state("x.test_organ", "seeing", {})
    bl.relay_state("x.test_organ", "trying", {})
    assert [t.topic for t in seen] == ["organ.state.linked", "organ.state.seeing", "organ.state.trying"]
    assert bl._AUTO_CONTROL_DONE is False

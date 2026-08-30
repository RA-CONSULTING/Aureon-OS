"""
Aureon — the Grounded Local Body (Phase 18).

Every local-machine move is grounded through HNC (Master-Formula substrate
coherence + Auris) and the Queen's conscience before it may touch the machine.
These tests pin the guarantees that make that safe: benign moves pass; risky
moves are vetoed when substrate coherence collapses; hard boundaries are refused
deterministically; the bridge is DRY-RUN unless armed; and the whole chain runs
offline (no Ollama) on deterministic grounding alone. No network, no OS deps.
"""

from __future__ import annotations

import pytest

from aureon.operator.grounded_action import GroundedActionGate
from aureon.operator.local_action_bridge import LocalActionBridge


class _FakeBus:
    """Minimal thought bus that records published topics."""

    def __init__(self) -> None:
        self.published: list = []

    def publish(self, thought):  # noqa: ANN001
        self.published.append(thought)
        return thought

    def get_recent(self, n=100):  # noqa: ANN001
        return []

    def topics(self):
        return [getattr(t, "topic", "") for t in self.published]


# ── the gate ──────────────────────────────────────────────────────────────

def test_benign_read_is_approved():
    v = GroundedActionGate(enable_llm=False).ground("list_repo", {"path": "."})
    assert v.approved is True
    assert v.verdict == "APPROVED"
    assert v.risk == 0.0  # read-only → benign


def test_risky_move_vetoed_when_coherence_collapses():
    # symbolic_life_score below the 0.20 stability cliff → the substrate
    # coherence veto refuses the move.
    v = GroundedActionGate(enable_llm=False).ground(
        "delete_file", {"path": "x"}, {"symbolic_life_score": 0.1})
    assert v.approved is False
    assert v.verdict == "VETOED"


def test_risky_move_allowed_on_the_stability_island():
    v = GroundedActionGate(enable_llm=False).ground(
        "delete_file", {"path": "x"}, {"symbolic_life_score": 0.9})
    assert v.approved is True
    assert v.risk >= 0.05  # destructive → carries real risk


def test_caller_cannot_downgrade_a_consequential_action_risk():
    v = GroundedActionGate(enable_llm=False).ground(
        "left_click", {"x": 10, "y": 20}, {"risk": 0.0, "symbolic_life_score": 0.9})
    assert v.risk >= 0.05


def test_consequential_action_fails_closed_when_conscience_errors():
    v = GroundedActionGate(conscience=object(), enable_llm=False).ground(
        "left_click", {"x": 10, "y": 20}, {"symbolic_life_score": 0.9})
    assert v.approved is False
    assert v.verdict == "VETOED"
    assert v.reason == "conscience_error_for_consequential_action"


def test_hard_boundary_is_blocked():
    v = GroundedActionGate(enable_llm=False).ground("reveal the api_key secret", {})
    assert v.approved is False
    assert v.verdict == "BLOCKED"


def test_gate_publishes_request_and_verdict():
    bus = _FakeBus()
    GroundedActionGate(bus=bus, enable_llm=False).ground("list_repo", {})
    topics = bus.topics()
    assert "operator.action.request" in topics
    assert "operator.action.verdict" in topics


# ── conscience local-verb extension ─────────────────────────────────────────

def test_conscience_flags_local_action_verbs():
    from aureon.queen.queen_conscience import QueenConscience

    c = QueenConscience()
    for verb in ("delete_file", "type_text", "wifi_connect", "execute_shell", "click"):
        assert c._is_risky_action(verb, {}) is True, verb
    # read-only observation is deliberately NOT risky
    for verb in ("read_repo_file", "list_repo", "screenshot", "get_screen_size"):
        assert c._is_risky_action(verb, {}) is False, verb


# ── the bridge ───────────────────────────────────────────────────────────────

def test_bridge_dry_run_by_default_does_not_execute():
    calls = []
    bridge = LocalActionBridge(
        gate=GroundedActionGate(enable_llm=False), join=False, armed=False,
        executor=lambda a, p: (calls.append(a), {"ok": True, "result": "x"})[1],
    )
    r = bridge.perform("list_repo", {"path": "."})
    assert r["approved"] is True and r["executed"] is False and r["dry_run"] is True
    assert calls == []  # nothing ran


def test_bridge_veto_blocks_and_never_executes():
    calls = []
    bridge = LocalActionBridge(
        gate=GroundedActionGate(enable_llm=False), join=False, armed=True,
        executor=lambda a, p: (calls.append(a), {"ok": True})[1],
    )
    r = bridge.perform("delete_file", {"path": "x"}, {"symbolic_life_score": 0.05})
    assert r["blocked"] is True and r["executed"] is False
    assert calls == []


def test_bridge_armed_executes_and_traces():
    bus = _FakeBus()
    bridge = LocalActionBridge(
        gate=GroundedActionGate(bus=bus, enable_llm=False), bus=bus, join=False, armed=True,
        executor=lambda a, p: {"ok": True, "result": f"ran {a}", "artefacts": [], "error": None},
    )
    r = bridge.perform("list_repo", {"path": "."})
    assert r["executed"] is True and r["ok"] is True and r["result"] == "ran list_repo"
    assert "local.action.result" in bus.topics()
    stats = bridge.recent_stats()
    assert stats["count"] == 1 and stats["approve_ratio"] == 1.0


def test_bridge_never_labels_executor_failure_as_executed():
    bridge = LocalActionBridge(
        gate=GroundedActionGate(enable_llm=False), join=False, armed=True,
        executor=lambda a, p: {"ok": False, "result": None, "error": "no_session"},
    )

    r = bridge.perform("screenshot", {})

    assert r["ok"] is False
    assert r["execution_attempted"] is True
    assert r["executed"] is False
    assert r["error"] == "no_session"


def test_bridge_maps_blocked_tool_json_to_failed_hold(monkeypatch):
    class _BlockedRegistry:
        @staticmethod
        def execute(action, params):  # noqa: ANN001, ARG004
            return '{"blocked": true, "reason": "test_hold"}'

    monkeypatch.setattr(
        "aureon.operator.tools.build_operator_tools",
        lambda **_kwargs: _BlockedRegistry(),
    )
    bridge = LocalActionBridge(
        gate=GroundedActionGate(enable_llm=False),
        join=False,
        armed=True,
    )

    result = bridge.perform("read_repo_file", {"path": "README.md"})

    assert result["ok"] is False
    assert result["execution_attempted"] is True
    assert result["executed"] is False
    assert result["result"]["blocked"] is True
    assert result["error"] == "test_hold"


# ── Λ(t) feedback source ─────────────────────────────────────────────────────

def test_lambda_source_maps_action_activity():
    from aureon.core.hnc_live_daemon import _map_local_action

    idle = _map_local_action({"count": 0})
    assert idle is None
    active = _map_local_action({"count": 40, "approve_ratio": 0.75, "veto_count": 3})
    assert 0.0 <= active.value <= 1.0 and active.confidence > 0.0
    assert "40_moves" in active.state


# ── HTTP surface ─────────────────────────────────────────────────────────────

def test_action_endpoint_and_bearer_gate(monkeypatch):
    pytest.importorskip("flask", reason="operator HTTP surface requires the [operator] extra")
    # this test asserts the DISARMED (dry-run) posture — pin it explicitly so a
    # leaked process-wide ARMED flag from an earlier test cannot flip it
    monkeypatch.delenv("AUREON_LOCAL_ACTIONS_ARMED", raising=False)
    import importlib

    import aureon.operator.operator_server as srv

    importlib.reload(srv)
    c = srv.create_app().test_client()

    r = c.post("/api/action", json={"action": "list_repo", "params": {"path": "."}})
    assert r.status_code == 200
    body = r.get_json()
    assert body["verdict"] in ("APPROVED", "CONCERNED") and body["dry_run"] is True

    assert c.post("/api/action", json={}).status_code == 400  # missing action
    assert c.get("/api/action/status").status_code == 200

    # bearer gate honoured when a key is set
    monkeypatch.setenv("AUREON_OPERATOR_API_KEY", "sesame")
    importlib.reload(srv)
    c2 = srv.create_app().test_client()
    assert c2.post("/api/action", json={"action": "list_repo"}).status_code == 401
    ok = c2.post("/api/action", json={"action": "list_repo"},
                 headers={"Authorization": "Bearer sesame"})
    assert ok.status_code == 200

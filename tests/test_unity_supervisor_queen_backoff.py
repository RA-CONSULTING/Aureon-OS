"""queen_mind restarts back off and honour the stop file."""

from __future__ import annotations


def _cycle(supervisor, now: float, stop: bool = False):
    supervisor._queen_backoff["attempts"] = supervisor._queen_backoff.get("attempts", 0)
    started: list[str] = []

    def start(name):
        started.append(name)
        return {"ok": True, "state": "started", "pid": 7}

    supervisor._mono = lambda: now  # type: ignore[method-assign]
    if stop:
        supervisor._queen_restart_block = lambda _now: "computer_use_stop_file"  # type: ignore[method-assign]
    return started, start


def _prepare(supervisor, tmp_path, monkeypatch, start):
    monkeypatch.setattr(supervisor.importlib, "reload", lambda module: module)
    monkeypatch.setattr(
        supervisor.organ_registry,
        "status_data",
        lambda: {"queen_mind": {"state": "stopped", "pid": None}},
    )
    monkeypatch.setattr(supervisor.organ_registry, "start", start)
    monkeypatch.setattr(supervisor.organ_registry, "ORGANS", {"queen_mind": {}})
    monkeypatch.setattr(supervisor.organ_registry, "_release_granted", lambda: False)
    monkeypatch.setattr(supervisor.organ_registry, "write_observed_process_identity", lambda: None)
    monkeypatch.setattr(supervisor.events, "chirp", lambda *args, **kwargs: None)
    monkeypatch.setattr(supervisor.events, "publish_event", lambda *args, **kwargs: None)
    monkeypatch.setattr(supervisor, "FUSION_STATE", tmp_path)
    monkeypatch.setattr(supervisor, "SUPERVISOR_STATE_FILE", tmp_path / "supervisor_state.json")


def test_stop_file_does_not_respawn_queen_mind(monkeypatch, tmp_path):
    from aureon_fusion import unity_supervisor as supervisor

    supervisor._queen_backoff["attempts"] = 0
    supervisor._queen_backoff["not_before"] = 0.0
    started: list[str] = []

    def start(name):
        started.append(name)
        return {"ok": True, "state": "started", "pid": 7}

    _prepare(supervisor, tmp_path, monkeypatch, start)
    monkeypatch.setattr(supervisor, "_mono", lambda: 0.0)
    monkeypatch.setattr(
        "aureon.operator.computer_use_stop.is_stopped",
        lambda: True,
    )
    payload = supervisor._supervise_cycle(dry_run=False)
    assert started == []
    reasons = [item.get("reason") for item in payload["decisions"]]
    assert "computer_use_stop_file" in reasons


def test_queen_mind_restart_backs_off(monkeypatch, tmp_path):
    from aureon_fusion import unity_supervisor as supervisor

    supervisor._queen_backoff["attempts"] = 0
    supervisor._queen_backoff["not_before"] = 0.0
    started: list[str] = []
    clock = {"t": 0.0}

    def start(name):
        started.append(name)
        return {"ok": True, "state": "started", "pid": 7}

    _prepare(supervisor, tmp_path, monkeypatch, start)
    monkeypatch.setattr(supervisor, "_mono", lambda: clock["t"])
    monkeypatch.setattr("aureon.operator.computer_use_stop.is_stopped", lambda: False)

    supervisor._supervise_cycle(dry_run=False)
    assert started == ["queen_mind"]

    clock["t"] = 1.0
    supervisor._supervise_cycle(dry_run=False)
    assert started == ["queen_mind"]

    clock["t"] = 45.0
    supervisor._supervise_cycle(dry_run=False)
    assert started == ["queen_mind", "queen_mind"]

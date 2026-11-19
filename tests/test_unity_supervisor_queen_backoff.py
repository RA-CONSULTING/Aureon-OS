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


def test_backoff_resets_when_queen_mind_is_seen_alive(monkeypatch, tmp_path):
    """After a crash storm, a running queen_mind returns the next wait to 45s.

    Goes red if the alive path does not clear ``attempts``. Without that clear
    the next delay stays at the 720s cap.
    """

    from aureon_fusion import unity_supervisor as supervisor

    supervisor._queen_backoff["attempts"] = 0
    supervisor._queen_backoff["not_before"] = 0.0
    started: list[str] = []
    clock = {"t": 0.0}
    state = {"queen": "stopped"}

    def start(name):
        started.append(name)
        return {"ok": True, "state": "started", "pid": 7}

    def status_data():
        running = state["queen"] == "running"
        return {"queen_mind": {"state": state["queen"], "pid": 7 if running else None}}

    _prepare(supervisor, tmp_path, monkeypatch, start)
    monkeypatch.setattr(supervisor.organ_registry, "status_data", status_data)
    monkeypatch.setattr(supervisor, "_mono", lambda: clock["t"])
    monkeypatch.setattr("aureon.operator.computer_use_stop.is_stopped", lambda: False)

    for _ in range(5):
        before = len(started)
        supervisor._supervise_cycle(dry_run=False)
        assert len(started) == before + 1
        clock["t"] = supervisor._queen_backoff["not_before"]

    assert supervisor._queen_backoff["attempts"] >= 5

    state["queen"] = "running"
    supervisor._supervise_cycle(dry_run=False)
    assert supervisor._queen_backoff["attempts"] == 0
    assert supervisor._queen_backoff["not_before"] == 0.0

    state["queen"] = "stopped"
    alive_at = clock["t"]
    supervisor._supervise_cycle(dry_run=False)
    assert len(started) == 6
    assert supervisor._queen_backoff["attempts"] == 1
    delay = supervisor._queen_backoff["not_before"] - alive_at
    assert delay == supervisor._QUEEN_BACKOFF_BASE_S
    assert delay < supervisor._QUEEN_BACKOFF_CAP_S

    clock["t"] = alive_at + 1.0
    supervisor._supervise_cycle(dry_run=False)
    assert len(started) == 6

    clock["t"] = alive_at + supervisor._QUEEN_BACKOFF_BASE_S
    supervisor._supervise_cycle(dry_run=False)
    assert len(started) == 7

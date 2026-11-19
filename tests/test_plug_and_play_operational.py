"""Operational defaults that must not depend on GitHub Actions.

These assertions fail on main: local actions start disarmed, queen chat
starts in dry-run, a dead queen_mind waits for an approval file, the lattice
module writes a noise figure on import, the penny hunter buys a random
Alpaca symbol, and install.sh does not pin the Linux desktop backend.
"""

from __future__ import annotations

import importlib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_install_pins_linux_desktop_backend_and_make_check() -> None:
    script = (ROOT / "install.sh").read_text(encoding="utf-8")
    desktop = (ROOT / "requirements-desktop.lock").read_text(encoding="utf-8")
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "requirements-desktop.lock" in script
    assert "uname -s" in script
    assert "source .env" not in script
    assert "python-xlib==" in desktop
    assert "PyAutoGUI==" in desktop
    assert "\ncheck:" in makefile
    assert "ruff check" in makefile
    assert "pytest" in makefile
    assert ".[dev]" in makefile or "'[dev]'" in makefile or '".[dev]"' in makefile
    assert "git clone --depth 1" in readme
    assert "make check" in readme
    quick = readme.split("## Quick start in five minutes", 1)[1][:2500]
    assert "./install.sh" in quick


def test_local_actions_execute_when_the_arming_variable_is_unset(monkeypatch, tmp_path) -> None:
    monkeypatch.delenv("AUREON_LOCAL_ACTIONS_ARMED", raising=False)
    monkeypatch.setenv("AUREON_COMPUTER_USE_STOP_FILE", str(tmp_path / "absent.stop"))
    from aureon.operator.grounded_action import GroundedActionGate
    from aureon.operator.local_action_bridge import LocalActionBridge

    calls = []
    bridge = LocalActionBridge(
        gate=GroundedActionGate(enable_llm=False),
        join=False,
        executor=lambda action, params: (calls.append(action), {"ok": True, "result": "ran"})[1],
    )
    assert bridge.armed is True
    result = bridge.perform("list_repo", {"path": "."})
    assert result["executed"] is True
    assert result["dry_run"] is False
    assert calls == ["list_repo"]


def test_computer_use_stop_file_forces_dry_run_and_is_not_created(monkeypatch, tmp_path) -> None:
    stop = tmp_path / "computer_use.stop"
    stop.write_text("human\n", encoding="utf-8")
    monkeypatch.setenv("AUREON_COMPUTER_USE_STOP_FILE", str(stop))
    monkeypatch.delenv("AUREON_LOCAL_ACTIONS_ARMED", raising=False)
    from aureon.operator.computer_use_stop import is_stopped
    from aureon.operator.grounded_action import GroundedActionGate
    from aureon.operator.local_action_bridge import LocalActionBridge

    assert is_stopped() is True
    before = stop.read_text(encoding="utf-8")
    bridge = LocalActionBridge(
        gate=GroundedActionGate(enable_llm=False),
        join=False,
        executor=lambda action, params: {"ok": True, "result": "ran"},
    )
    result = bridge.perform("list_repo", {"path": "."})
    assert result["executed"] is False
    assert result["dry_run"] is True
    assert stop.read_text(encoding="utf-8") == before
    assert not (ROOT / "state" / "computer_use.stop").exists() or stop != ROOT / "state" / "computer_use.stop"


def test_queen_chat_bridge_defaults_to_live(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("AUREON_COMPUTER_USE_STOP_FILE", str(tmp_path / "absent.stop"))
    from aureon.queen.queen_action_bridge import QueenActionBridge

    bridge = QueenActionBridge(registry=object(), dispatcher=object())
    status = bridge.status()
    assert status["live"] is True
    assert status["mode"] == "live"


def test_dead_queen_mind_restarts_without_an_approval_file(monkeypatch, tmp_path) -> None:
    from aureon_fusion import unity_supervisor as supervisor

    monkeypatch.setattr(supervisor.importlib, "reload", lambda module: module)
    monkeypatch.setattr(
        supervisor.organ_registry,
        "status_data",
        lambda: {"queen_mind": {"state": "stopped", "pid": None}},
    )
    started = []

    def start(name):
        started.append(name)
        return {"ok": True, "state": "started", "pid": 4242}

    monkeypatch.setattr(supervisor.organ_registry, "start", start)
    monkeypatch.setattr(supervisor.organ_registry, "ORGANS", {"queen_mind": {}})
    monkeypatch.setattr(supervisor.organ_registry, "_release_granted", lambda: False)
    monkeypatch.setattr(supervisor.organ_registry, "write_observed_process_identity", lambda: None)
    monkeypatch.setattr(supervisor.events, "chirp", lambda *args, **kwargs: None)
    monkeypatch.setattr(supervisor.events, "publish_event", lambda *args, **kwargs: None)
    monkeypatch.setattr(supervisor, "FUSION_STATE", tmp_path)
    monkeypatch.setattr(supervisor, "SUPERVISOR_STATE_FILE", tmp_path / "supervisor_state.json")
    approval = tmp_path / "queen_mind_restart_approved.json"
    monkeypatch.setattr(supervisor, "QUEEN_MIND_RESTART_APPROVAL", approval)

    payload = supervisor._supervise_cycle(dry_run=False)

    assert started == ["queen_mind"]
    assert approval.exists() is False
    assert "await_owner_restart" not in {item["action"] for item in payload["decisions"]}


def test_lattice_import_does_not_write_a_noise_figure(monkeypatch, tmp_path) -> None:
    monkeypatch.chdir(tmp_path)
    import aureon.core.aureon_lattice_simulation as lattice

    importlib.reload(lattice)
    assert list(tmp_path.glob("*.png")) == []
    with pytest.raises(RuntimeError, match="no data"):
        lattice.generate_phase("Distortion", 1.0, 0.0, 0.0, 0.3)


def test_penny_hunter_does_not_buy_a_random_alpaca_symbol(monkeypatch) -> None:
    from aureon.core import aureon_penny_hunter as hunter_mod

    class _Alpaca:
        def __init__(self) -> None:
            self.orders = []

        def get_account(self):
            return {"cash": "25"}

        def place_market_order(self, **kwargs):
            self.orders.append(kwargs)
            return {"id": "should-not-send"}

    hunter = hunter_mod.PennyHunter()
    hunter._authenticated = True
    hunter._auth_at = hunter_mod.time.time()
    hunter.get_positions = lambda: []
    hunter._alpaca = _Alpaca()
    monkeypatch.setattr(hunter_mod, "_is_market_open", lambda market: market == "us_stocks")
    monkeypatch.setattr(hunter_mod.PennyHunter, "step_attr", property(lambda self: 0))

    result = hunter.tick()

    assert hunter._alpaca.orders == []
    assert result["opened"] == []
    assert result["no_data"][0]["status"] == "no_data"
    assert result["no_data"][0]["exchange"] == "alpaca"

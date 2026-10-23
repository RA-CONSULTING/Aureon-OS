"""Preflight snags: child paths, live default, thought bus, tabs, simulated boot."""

from __future__ import annotations

import ast
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from aureon.autonomous.aureon_master_launcher import (
    child_script,
    live_trading_from_env,
)
from aureon.autonomous.master_launcher_ui import page_html, start_master_ui, stop_master_ui
from aureon.core.algorithmic_nodes import list_nodes
from aureon.core.deterministic_systems import list_systems
from aureon.core.organism_circulation import (
    _DEFAULT_PORT,
    propose_self_code,
    start_organism_circulation,
    stop_organism_circulation,
    switch_connector,
)
from aureon.core.simulated_boot import (
    HARMONIC_WAVE_SIMULATION,
    INTERNAL_MULTIVERSE,
    MYCELIUM_HIVE_SEED,
    simulated_boot_enabled,
    take_simulated,
)
from aureon.data_feeds.unified_market_cache import ensure_public_prices

REPO = Path(__file__).resolve().parents[1]


def test_child_scripts_live_under_aureon_and_open() -> None:
    names = ("dashboard", "market_cache", "kraken_cache", "command_center")
    for name in names:
        path = Path(child_script(name))
        assert path.is_file(), path
        assert "aureon" in path.parts
        # The interpreter can open the file. A missing path is "can't open file".
        probe = subprocess.run(
            ["python3", "-c", "import pathlib,sys; pathlib.Path(sys.argv[1]).read_bytes()", str(path)],
            check=False,
            capture_output=True,
            text=True,
        )
        assert probe.returncode == 0, probe.stderr
        assert "can't open file" not in probe.stderr


def test_unset_live_trading_defaults_off(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AUREON_LIVE_TRADING", raising=False)
    assert live_trading_from_env() is False
    monkeypatch.setenv("AUREON_LIVE_TRADING", "1")
    assert live_trading_from_env() is True
    source = (REPO / "aureon/autonomous/aureon_master_launcher.py").read_text(encoding="utf-8")
    assert 'os.getenv("AUREON_LIVE_TRADING", "1")' not in source


def test_thought_bus_organs_publish_and_subscribe(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("AUREON_ORGANISM_STATE", str(tmp_path / "state"))
    monkeypatch.setenv("AUREON_ORGANISM_HTTP_PORT", "0")
    monkeypatch.setenv("AUREON_THOUGHT_BUS_PATH", str(tmp_path / "thoughts.jsonl"))
    # The bus singleton may already be pinned by conftest. Circulation still
    # publishes on whatever bus get_thought_bus() returns.
    started = start_organism_circulation(port=0)
    try:
        assert started["started"] is True
        assert started["port"]
        import time
        import urllib.request

        required = {
            "metacognition",
            "queen",
            "logic",
            "neural",
            "lighthouse",
            "qgita",
            "mycelium",
            "baton_relay",
            "council",
            "deterministic_systems",
            "algorithmic_nodes",
        }
        deadline = time.time() + 5
        sources: set[str] = set()
        body = {}
        while time.time() < deadline and not required <= sources:
            with urllib.request.urlopen(f"http://127.0.0.1:{started['port']}/healthz", timeout=2) as resp:
                assert resp.status == 200
                body = json.loads(resp.read().decode("utf-8"))
            sources = set(body.get("sources") or [])
            time.sleep(0.05)
        for name in sorted(required):
            assert name in sources
        with urllib.request.urlopen(f"http://127.0.0.1:{started['port']}/health", timeout=2) as resp:
            assert resp.status == 200
        assert body["listening"] is True
        assert body["loops"]["council"] == "running"
        assert body["loops"]["baton_relay"] == "running"
        assert body["loops"]["metacognition"] == "running"
        switched = switch_connector("self_code", True)
        assert switched["self_code"] is True
        proposal = propose_self_code("aureon/core/notes_probe.py", "record only")
        assert proposal["accepted"] is True
        assert proposal["applied"] is False
        refused = propose_self_code(".env", "no")
        assert refused["accepted"] is False
    finally:
        stop_organism_circulation()


def test_circulation_owns_8799_and_fails_loud_when_taken(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    import socket

    assert _DEFAULT_PORT == 8799
    monkeypatch.setenv("AUREON_ORGANISM_STATE", str(tmp_path / "state"))
    monkeypatch.setenv("AUREON_THOUGHT_BUS_PATH", str(tmp_path / "thoughts.jsonl"))
    held = socket.socket()
    held.bind(("127.0.0.1", 0))
    held.listen(1)
    port = held.getsockname()[1]
    try:
        status = start_organism_circulation(port=port)
        assert status["started"] is False
        assert status["port"] is None
        assert "failed to bind" in str(status["error"])
        assert "8765" in str(status["error"])
    finally:
        held.close()
        stop_organism_circulation()


def test_deterministic_systems_and_algorithmic_nodes_map_existing_modules() -> None:
    systems = list_systems()
    nodes = list_nodes()
    assert {item["name"] for item in systems} >= {"baton_stage_order", "council_active_threshold", "phi_squared_ring"}
    roles = {item["role"] for item in nodes}
    assert {"metacognition", "reasoning", "logic", "neural", "lighthouse", "qgita", "mycelium", "baton_relay", "council"} <= roles
    for item in systems + nodes:
        module = item["module"]
        if module.startswith("aureon."):
            relative = Path(*module.split(".")).with_suffix(".py")
            assert (REPO / relative).is_file() or (REPO / Path(*module.split(".")) / "__init__.py").is_file()


def test_master_ui_has_dashboard_and_command_center_tabs() -> None:
    html = page_html("http://127.0.0.1:18080/", "http://127.0.0.1:18800/")
    assert 'data-tab="dashboard"' in html
    assert 'data-tab="command-center"' in html
    assert "Dashboard" in html and "Command Center" in html
    started = start_master_ui(0, dashboard_url="http://127.0.0.1:18080/", command_center_url="http://127.0.0.1:18800/")
    try:
        import urllib.request

        with urllib.request.urlopen(started["url"], timeout=2) as resp:
            page = resp.read().decode("utf-8")
            assert resp.status == 200
        assert 'data-tab="dashboard"' in page
        assert 'data-tab="command-center"' in page
        with urllib.request.urlopen(started["url"] + "health", timeout=2) as resp:
            health = json.loads(resp.read().decode("utf-8"))
        assert health["live_trading"] is False
    finally:
        stop_master_ui()


def test_simulated_components_are_off_by_default(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.delenv("AUREON_SIMULATED_BOOT", raising=False)
    assert simulated_boot_enabled() is False
    assert take_simulated(HARMONIC_WAVE_SIMULATION, "solfeggio visualization, not a live price feed") is False
    assert take_simulated(INTERNAL_MULTIVERSE, "aureon.simulation, 10 worlds × $10") is False
    assert take_simulated(MYCELIUM_HIVE_SEED, "hive seed is not an exchange balance") is False
    captured = capsys.readouterr().out
    assert "SIMULATED Harmonic Wave Simulation" in captured
    assert "10 worlds × $10" in captured
    assert "mycelium hive seed ($1000)" in captured
    assert "skipped on the default boot" in captured

    for relative in (
        "aureon/harmonic/aureon_harmonic_chain_master.py",
        "aureon/trading/aureon_unified_ecosystem.py",
        "aureon/trading/micro_profit_labyrinth.py",
        "aureon/command_centers/aureon_command_center_ui.py",
        "aureon/intelligence/aureon_timeline_oracle.py",
        "aureon/bridges/aureon_frontend_bridge.py",
    ):
        tree = ast.parse((REPO / relative).read_text(encoding="utf-8"))
        assert tree is not None
        text = (REPO / relative).read_text(encoding="utf-8")
        assert "take_simulated" in text


def test_public_price_seed_fills_an_empty_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "aureon.data_feeds.unified_market_cache.fetch_public_rest_prices",
        lambda timeout=5.0: {"BTC": 65000.0, "ETH": 3200.0},
    )
    monkeypatch.setattr("aureon.data_feeds.unified_market_cache._last_public_seed", 0.0, raising=False)

    class _Cache:
        def __init__(self) -> None:
            self.tickers = {}

        def get_all_prices(self, max_age: float = 30.0) -> dict[str, float]:
            return {symbol: ticker.price for symbol, ticker in self.tickers.items()}

        def update_ticker(self, ticker) -> None:
            self.tickers[ticker.symbol] = ticker

    cache = _Cache()
    added = ensure_public_prices(cache, min_interval=0)
    assert added == 2
    assert cache.get_all_prices()["BTC"] == 65000.0
    assert cache.get_all_prices()["ETH"] == 3200.0


def test_installer_and_aureon_up_do_not_refuse() -> None:
    installer = (REPO / "production/install.sh").read_text(encoding="utf-8")
    up = (REPO / "scripts/linux/aureon-up.sh").read_text(encoding="utf-8")
    windows = (REPO / "production/Install-AUREON.ps1").read_text(encoding="utf-8")
    for text in (installer, up, windows):
        assert "refusing installation" not in text
        assert "refusing startup" not in text
        assert "--live" not in text
        assert "--production" not in text
    for text in (installer, windows):
        assert "aureon-master" in text
        assert "http://127.0.0.1:5173/" in text
        assert "--preflight" not in text
    assert "AUREON_LIVE_TRADING=0" in up
    assert "--preflight" in up
    assert "protected_bootstrap" not in installer
    assert "protected_bootstrap" not in up
    bash = subprocess.run(["bash", "-n", str(REPO / "production/install.sh")], capture_output=True, text=True)
    assert bash.returncode == 0, bash.stderr
    bash_up = subprocess.run(["bash", "-n", str(REPO / "scripts/linux/aureon-up.sh")], capture_output=True, text=True)
    assert bash_up.returncode == 0, bash_up.stderr
    assert os.access(REPO / "production/install.sh", os.X_OK)
    assert os.access(REPO / "scripts/linux/aureon-up.sh", os.X_OK)


def test_readme_names_the_live_switch_and_the_thought_bus() -> None:
    readme = (REPO / "README.md").read_text(encoding="utf-8")
    assert "Live trading stays off" not in readme
    assert "http://127.0.0.1:5173/" in readme
    assert "http://127.0.0.1:8799/healthz" in readme
    assert "http://127.0.0.1:8765/healthz" in readme
    assert "trading_mode=live (exchange keys present)" in readme
    assert "portaudio" in readme
    assert "python -m venv --copies" in readme
    assert "32 evidence tests" in readme
    linux = (REPO / "requirements-linux.txt").read_text(encoding="utf-8")
    assert "pytest>=" in linux
    master = (REPO / "aureon/launch/master.py").read_text(encoding="utf-8")
    assert '"-m", "venv", "--copies"' in master
    assert '"--link-mode", "copy"' in master
    page = (REPO / "frontend/src/shell/pages/LauncherPage.tsx").read_text(encoding="utf-8")
    assert "http://127.0.0.1:8799/healthz" in page


def test_frontend_bridge_does_not_load_the_multiverse_by_default(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    """Run the bridge's own multiverse gate. The rest of that module imports the swarm."""
    monkeypatch.setenv("AUREON_SIMULATED_BOOT", "0")
    text = (REPO / "aureon/bridges/aureon_frontend_bridge.py").read_text(encoding="utf-8")
    start = text.index("# Internal Multiverse")
    end = text.index("# Miner Brain")
    snippet = text[start:end]
    tree = ast.parse(snippet)
    imports = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module == "aureon.simulation.aureon_internal_multiverse"
    ]
    assert len(imports) == 1
    guarded = False
    for node in ast.walk(tree):
        if not isinstance(node, ast.If):
            continue
        call = node.test
        name = call.func.id if isinstance(call, ast.Call) and isinstance(call.func, ast.Name) else ""
        if name == "take_simulated" and imports[0] in list(ast.walk(node)):
            guarded = True
    assert guarded
    namespace: dict[str, object] = {}
    exec(compile(snippet, "aureon_frontend_bridge.py", "exec"), namespace)
    captured = capsys.readouterr().out
    assert namespace["MULTIVERSE_AVAILABLE"] is False
    assert namespace["InternalMultiverse"] is None
    assert "Internal Multiverse: LOADED" not in captured
    assert "skipped on the default boot" in captured


def test_ensure_venv_uses_copies_and_replaces_a_symlink(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from aureon.launch.master import _ensure_venv

    calls: list[list[str]] = []

    def fake_run(cmd: list[str], repo: Path, timeout: int = 180) -> tuple[bool, str]:
        calls.append(list(cmd))
        leaf = repo / ".venv" / "bin"
        leaf.mkdir(parents=True, exist_ok=True)
        python = leaf / "python"
        python.write_text("#!/bin/sh\n", encoding="utf-8")
        python.chmod(0o755)
        (repo / ".venv" / "pyvenv.cfg").write_text("home = /usr\n", encoding="utf-8")
        return True, "ok"

    monkeypatch.setattr("aureon.launch.master._run_install", fake_run)
    created, note = _ensure_venv(tmp_path)
    assert created is not None
    assert not created.is_symlink()
    assert note == "venv created with --copies"
    assert calls[0][1:4] == ["-m", "venv", "--copies"]

    link_root = tmp_path / "linked"
    leaf = link_root / ".venv" / "bin"
    leaf.mkdir(parents=True)
    (leaf / "python").symlink_to(sys.executable)
    (link_root / ".venv" / "pyvenv.cfg").write_text("home = /usr\n", encoding="utf-8")
    calls.clear()
    replaced, replaced_note = _ensure_venv(link_root)
    assert replaced is not None
    assert not replaced.is_symlink()
    assert replaced_note == "venv created with --copies"
    assert calls and calls[0][1:4] == ["-m", "venv", "--copies"]

    before = len(calls)
    kept, kept_note = _ensure_venv(tmp_path)
    assert kept == created
    assert kept_note == "venv present"
    assert len(calls) == before

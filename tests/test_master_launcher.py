"""Canonical master launcher: inventory, gates, and a fresh-clone smoke."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from aureon.launch.master import (
    LOCAL_FUSION_TOKEN,
    PAPER_LOCK,
    Component,
    Runner,
    Spawn,
    build_inventory,
    execute,
    format_report,
    missing_exchange_credential,
    organ_command,
    paper_env,
    project_python,
    parse_args,
    parse_compose,
    repo_root,
)

_EXCHANGE_KEYS = (
    "KRAKEN_API_KEY",
    "KRAKEN_API_SECRET",
    "BINANCE_API_KEY",
    "BINANCE_API_SECRET",
    "ALPACA_API_KEY",
    "ALPACA_SECRET_KEY",
    "CAPITAL_API_KEY",
    "CAPITAL_IDENTIFIER",
    "CAPITAL_PASSWORD",
)


def _clear_trading_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in _EXCHANGE_KEYS:
        monkeypatch.delenv(key, raising=False)
    monkeypatch.delenv("AUREON_AUTONOMY_MODE", raising=False)
    monkeypatch.delenv("AUREON_SELF_REPAIR_KILL", raising=False)
    monkeypatch.delenv("AUREON_CODE_AUTO_APPROVE", raising=False)

ROOT = Path(__file__).resolve().parents[1]


class FakeRunner(Runner):
    def __init__(self, repo: Path) -> None:
        super().__init__(repo)
        self.http_wait = 0
        self.docker = (False, "docker not installed")
        self.http: dict[str, bool] = {}
        self.pong = False
        self.ports: set[int] = set()
        self.ollama = False
        self.stopped: list[int] = []
        self.stopped_compose: list[str] = []
        self.installs: list[str] = []
        self._next = 4000

    def install_env(self) -> tuple[bool, str]:
        self.installs.append("env")
        return True, "fake env left unwritten"

    def install_python(self) -> tuple[bool, str]:
        self.installs.append("python")
        return True, "fake python requirements satisfied"

    def install_node(self) -> tuple[bool, str]:
        self.installs.append("node")
        return True, "fake node packages satisfied"

    def install_docker(self) -> tuple[bool, str]:
        self.installs.append("docker")
        return True, "fake docker images satisfied"

    def settle(self, seconds: float) -> None:
        return None

    def docker_ready(self) -> tuple[bool, str]:
        return self.docker

    def compose_up(self, compose_file: Path, services: list[str]) -> tuple[bool, str]:
        return False, "docker not installed"

    def compose_health(self, compose_file: Path, service: str) -> tuple[bool, str]:
        return False, "container not running"

    def compose_stop(self, compose_file: Path, services: list[str]) -> None:
        self.stopped_compose = list(services)

    def spawn(self, name: str, cmd: list[str], cwd: Path, env: dict[str, str], log_path: Path) -> tuple[int, int]:
        self._next += 1
        log_path.parent.mkdir(parents=True, exist_ok=True)
        self.spawned.append(Spawn(name, list(cmd), str(cwd), dict(env), str(log_path), self._next, self._next))
        return self._next, self._next

    def alive(self, pid: int) -> bool:
        return any(item.pid == pid for item in self.spawned)

    def stop_pid(self, pid: int, pgid: int | None = None) -> None:
        self.stopped.append(pid)

    def http_ok(self, url: str, timeout: float = 1.5) -> bool:
        return self.http.get(url, False)

    def command_ok(self, cmd: list[str], timeout: float = 3) -> bool:
        return False

    def port_busy(self, port: int) -> bool:
        return port in self.ports

    def ollama_up(self) -> bool:
        return self.ollama

    def redis_pong(self) -> bool:
        return self.pong


@pytest.fixture
def launcher_state(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    state = tmp_path / "launcher-state"
    monkeypatch.setenv("AUREON_LAUNCHER_STATE", str(state))
    monkeypatch.delenv("AUREON_SELF_REPAIR_ENABLE", raising=False)
    monkeypatch.delenv("AUREON_SELF_REPAIR_KILL", raising=False)
    return state


def _run(argv: list[str], runner: FakeRunner, monkeypatch: pytest.MonkeyPatch | None = None) -> tuple[int, str]:
    args = parse_args(argv)
    if monkeypatch is not None:
        pass
    from io import StringIO

    buffer = StringIO()
    old = sys.stdout
    sys.stdout = buffer
    try:
        code = execute(args, ROOT, runner)
    finally:
        sys.stdout = old
    return code, buffer.getvalue()


def test_inventory_covers_compose_organs_and_faculties() -> None:
    from aureon_fusion.flight_recorder import FACULTY_FILES
    from aureon_fusion.organ_registry import ORGAN_ORDER

    components, note = build_inventory(ROOT)
    assert note is None
    names = {component.name for component in components}
    compose = parse_compose((ROOT / "deploy" / "selfhost" / "docker-compose.yml").read_text(encoding="utf-8"))
    assert set(compose) == {
        "postgres",
        "redis",
        "error_sink",
        "api_a",
        "api_b",
        "frontend",
        "hnc_core",
        "nginx",
    }
    for service in compose:
        assert f"compose/{service}" in names
    for organ in ORGAN_ORDER:
        assert f"organ/{organ}" in names
    for faculty in FACULTY_FILES:
        assert f"faculty/{faculty['name']}" in names
    for extra in (
        "deps/env",
        "deps/python",
        "deps/node",
        "deps/docker",
        "stdio/windows",
        "seat/trading_world_v5b",
        "loop/self_repair",
        "loop/self_coder",
        "dashboards",
    ):
        assert extra in names
    by_name = {component.name: component for component in components}
    assert by_name["compose/nginx"].depends_on[-1] == "deps/docker"
    assert "deps/python" in by_name["seat/trading_world_v5b"].depends_on
    assert "deps/node" in by_name["organ/frontend_vite"].depends_on
    assert "deps/python" in by_name["organ/hnc_core"].depends_on
    assert "deps/env" in by_name["deps/python"].depends_on
    assert [component.name for component in components[:4]] == [
        "deps/env",
        "deps/python",
        "deps/node",
        "deps/docker",
    ]
    assert all(isinstance(component, Component) for component in components)


def test_desktop_extras_are_stripped_from_a_failed_requirements_retry() -> None:
    from aureon.launch.master import _without_desktop_extras

    text = _without_desktop_extras("PyAudio>=0.2.14\nrequests>=2\npycaw\n")
    assert "requests>=2" in text
    assert "skipped by launcher" in text
    assert "\nPyAudio" not in text


def test_missing_exchange_credential_starts_the_trader_in_paper(
    launcher_state: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _clear_trading_env(monkeypatch)
    reason = missing_exchange_credential(ROOT)
    assert reason is not None
    assert reason.startswith("missing credential:")
    runner = FakeRunner(ROOT)
    code, output = _run(["--only", "organ/unified_market_trader"], runner)
    assert code == 0
    spawned = [item for item in runner.spawned if item.name == "organ/unified_market_trader"]
    assert len(spawned) == 1
    assert spawned[0].env["AUREON_LIVE_TRADING"] == "0"
    assert spawned[0].env["AUREON_MAY_ACT"] == "1"
    assert "organ/unified_market_trader" in output
    assert "paper/public-data (no exchange keys)" in output
    assert "live_trading_armed_by_launcher=false" in output


def test_only_stdio_does_not_spawn_or_arm(launcher_state: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_trading_env(monkeypatch)
    monkeypatch.setenv("AUREON_LIVE_TRADING", "0")
    runner = FakeRunner(ROOT)
    code, output = _run(["--only", "stdio/windows"], runner)
    assert code == 0
    assert runner.spawned == []
    assert runner.installs == []
    assert "live_trading_armed_by_launcher=false" in output
    assert "trading_mode=paper/public-data (no exchange keys)" in output
    assert "autonomy_mode=full" in output
    assert "stdio/windows" in output
    assert "started" in output
    assert os.environ["AUREON_LIVE_TRADING"] == "0"


def test_child_env_stays_paper_when_the_parent_switch_is_on(launcher_state: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_trading_env(monkeypatch)
    monkeypatch.setenv("AUREON_LIVE_TRADING", "1")
    runner = FakeRunner(ROOT)
    code, output = _run(["--only", "seat/trading_world_v5b"], runner)
    assert code == 0
    assert os.environ["AUREON_LIVE_TRADING"] == "1"
    assert "live_trading_armed_by_launcher=false" in output
    assert "trading_mode=paper/public-data (no exchange keys)" in output
    assert runner.installs == ["env", "python"]
    assert len(runner.spawned) == 1
    child = runner.spawned[0]
    assert child.env["SERO_WORKSPACE"] == str(ROOT.resolve())
    assert child.env["AUREON_LIVE_TRADING"] == "0"
    assert child.env["AUREON_FUSION_ARM_LIVE"] == ""
    assert child.env["AUREON_DISABLE_REAL_ORDERS"] == "1"
    assert child.env["AUREON_MAY_ACT"] == "1"
    assert child.env["AUREON_AUTONOMY_MODE"] == "full"
    assert child.env["AUREON_FUSION_BIND"] == "127.0.0.1"
    assert child.env["AUREON_FUSION_PORT"] == "8765"
    assert child.env["AUREON_FUSION_API_TOKEN"] == LOCAL_FUSION_TOKEN
    assert child.cmd[:4] == [project_python(ROOT), "-u", "-m", "aureon_fusion.http_service"]
    assert isinstance(child.cmd, list)


def test_status_and_stop_do_not_start_new_processes(launcher_state: Path) -> None:
    runner = FakeRunner(ROOT)
    code, output = _run(["--status", "--only", "organ/hnc_core"], runner)
    assert code == 0
    assert runner.spawned == []
    assert runner.installs == []
    assert "not running" in output or "blocked" in output
    code, output = _run(["--stop"], runner)
    assert code == 0
    assert runner.spawned == []
    assert "nothing recorded" in output


def test_stop_kills_only_recorded_pids(launcher_state: Path) -> None:
    runner = FakeRunner(ROOT)
    code, _output = _run(["--only", "seat/trading_world_v5b"], runner)
    assert code == 0
    assert len(runner.spawned) == 1
    pid = runner.spawned[0].pid
    code, output = _run(["--stop"], runner)
    assert code == 0
    assert runner.stopped == [pid]
    assert "stopped" in output


def test_unknown_only_exits_before_spawn(launcher_state: Path) -> None:
    runner = FakeRunner(ROOT)
    code, _output = _run(["--only", "not-a-component"], runner)
    assert code == 2
    assert runner.spawned == []


def test_live_suite_starts_without_creating_the_release_flag(
    launcher_state: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _clear_trading_env(monkeypatch)
    flag = ROOT / "aureon_fusion" / "state" / "capital_release.flag"
    existed = flag.exists()
    runner = FakeRunner(ROOT)
    code, output = _run(["--only", "aureon_radar_suite,orca_unified_kill_chain"], runner)
    assert code == 0
    names = {item.name for item in runner.spawned}
    assert "organ/aureon_radar_suite" in names
    assert "organ/orca_unified_kill_chain" in names
    assert "does not arm live trading" not in output
    assert "does not read the live-trading switch" not in output
    assert flag.exists() is existed
    assert "trading_mode=paper/public-data (no exchange keys)" in output


def test_ignored_live_flag_does_not_change_the_environment(launcher_state: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setenv("AUREON_LIVE_TRADING", "0")
    runner = FakeRunner(ROOT)
    code, _output = _run(["--only", "stdio/windows", "--live"], runner)
    assert code == 0
    assert os.environ["AUREON_LIVE_TRADING"] == "0"
    assert runner.spawned == []


def test_organ_command_is_a_list_and_supervisor_is_not_forced_dry_run(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_trading_env(monkeypatch)
    command = organ_command(ROOT, "hnc_core", {"module": "aureon_fusion.hnc_core", "args": ["run"]})
    assert command == [project_python(ROOT), "-u", "-m", "aureon_fusion.hnc_core", "run"]
    supervisor = organ_command(ROOT, "unity_supervisor", {"module": "aureon_fusion.unity_supervisor", "args": []})
    assert "--dry-run" not in supervisor
    env = paper_env(
        {"AUREON_LIVE_TRADING": "1", "PYTHONPATH": "", "SERO_WORKSPACE": "/tmp/other-checkout"},
        ROOT,
    )
    assert env["AUREON_LIVE_TRADING"] == "0"
    assert env["AUREON_MAY_ACT"] == "1"
    assert env["SERO_WORKSPACE"] == str(ROOT.resolve())
    assert PAPER_LOCK["AUREON_LIVE_TRADING"] == "0"


def test_exchange_keys_arm_the_child_without_placing_an_order(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _clear_trading_env(monkeypatch)
    (tmp_path / ".env").write_text(
        "KRAKEN_API_KEY=local-test-key\nKRAKEN_API_SECRET=local-test-secret\n",
        encoding="utf-8",
    )
    env = paper_env({"PYTHONPATH": ""}, tmp_path)
    assert env["AUREON_LIVE_TRADING"] == "1"
    assert env["AUREON_DISABLE_REAL_ORDERS"] == "0"
    assert env["AUREON_DRY_RUN"] == "0"
    assert env["AUREON_MAY_ACT"] == "1"
    assert env["AUREON_ORDER_INTENT_PUBLISH"] == "1"
    from aureon.launch.master import boot_decision

    label, armed = boot_decision(tmp_path, env)
    text = format_report([], "full", trading_mode=label, armed=armed)
    assert armed is True
    assert "live_trading_armed_by_launcher=true" in text
    assert "trading_mode=live (exchange keys present)" in text
    assert "local-test-secret" not in text
    assert "local-test-key" not in text


def test_kill_switch_keeps_a_keyed_child_on_paper(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_trading_env(monkeypatch)
    (tmp_path / ".env").write_text(
        "KRAKEN_API_KEY=local-test-key\nKRAKEN_API_SECRET=local-test-secret\n",
        encoding="utf-8",
    )
    kill = tmp_path / "state" / "SELF_REPAIR_KILL"
    kill.parent.mkdir()
    kill.write_text("stop\n", encoding="utf-8")
    env = paper_env({"PYTHONPATH": ""}, tmp_path)
    assert env["AUREON_LIVE_TRADING"] == "0"
    assert env["AUREON_MAY_ACT"] == "0"
    assert env["AUREON_DISABLE_REAL_ORDERS"] == "1"


def test_self_repair_respects_enable_gate(launcher_state: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AUREON_SELF_REPAIR_ENABLE", raising=False)
    runner = FakeRunner(ROOT)
    code, output = _run(["--only", "self_repair"], runner)
    assert code == 0
    assert "loop/self_repair" in output
    assert "blocked" in output
    assert "does not enable it" in output
    monkeypatch.setenv("AUREON_AUTONOMY_MODE", "full")
    code, output = _run(["--only", "self_coder"], runner)
    assert code == 0
    assert "autonomy=full" in output
    assert "does not invent a goal" in output


def test_wrappers_delegate_and_do_not_arm_live() -> None:
    wrapper_paths = [
        ROOT / "scripts" / "launch" / "aureon-master.sh",
        ROOT / "scripts" / "launch" / "aureon-master.ps1",
        ROOT / "scripts" / "launch" / "aureon-master.bat",
        ROOT / "aureon_radar" / "launch_all.bat",
        ROOT / "aureon_radar" / "launch_all_fixed.bat",
        ROOT / "aureon_radar" / "start_radar.bat",
        ROOT / "aureon_radar" / "start_radar.sh",
    ]
    for path in wrapper_paths:
        text = path.read_text(encoding="utf-8")
        assert "aureon.launch.master" in text
        lowered = text.casefold()
        assert "capital.com" not in lowered
        assert "live=1" not in lowered
        assert ".env.example" not in lowered
    historical = (ROOT / "aureon" / "autonomous" / "aureon_master_launcher.py").read_text(encoding="utf-8")
    assert "from aureon.launch.master import main as canonical" in historical
    source = (ROOT / "aureon" / "launch" / "master.py").read_text(encoding="utf-8")
    assert "capital_release.flag" in source
    assert "place_order" not in source


def test_report_table_has_the_health_columns() -> None:
    from aureon.launch.master import Row

    text = format_report([Row("stdio/windows", "started", "ok", "posix streams usable")], "full")
    assert "AUREON MASTER LAUNCHER" in text
    assert "live_trading_armed_by_launcher=false" in text
    assert "trading_mode=paper/public-data (no exchange keys)" in text
    assert "order" in text and "name" in text and "status" in text and "health" in text and "reason" in text
    assert "stdio/windows" in text
    assert "started=1 blocked=0 total=1" in text


@pytest.mark.timeout(1600)
def test_fresh_clone_smoke_prints_the_health_table(tmp_path: Path) -> None:
    clone = tmp_path / "clone"
    cloned = subprocess.run(
        ["git", "clone", "--no-hardlinks", "--shared", str(ROOT), str(clone)],
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )
    if cloned.returncode != 0:
        pytest.fail(cloned.stderr)
    env = os.environ.copy()
    env["PYTHONPATH"] = str(clone)
    env["AUREON_LIVE_TRADING"] = "0"
    env.pop("AUREON_AUTONOMY_MODE", None)
    env.pop("AUREON_LAUNCHER_STATE", None)
    env.pop("AUREON_FUSION_ARM_LIVE", None)
    for key in _EXCHANGE_KEYS:
        env.pop(key, None)
    proc = subprocess.run(
        [sys.executable, "-m", "aureon.launch.master"],
        cwd=clone,
        env=env,
        capture_output=True,
        text=True,
        timeout=1500,
        check=False,
    )
    try:
        assert proc.returncode == 0, proc.stderr
        assert "live_trading_armed_by_launcher=false" in proc.stdout
        assert "trading_mode=paper/public-data (no exchange keys)" in proc.stdout
        assert "deps/python" in proc.stdout
        assert "deps/node" in proc.stdout
        assert "deps/docker" in proc.stdout
        assert "compose/postgres" in proc.stdout
        assert "seat/trading_world_v5b" in proc.stdout
        assert "organ/queen_mind" in proc.stdout
        assert "organ/unity_supervisor" in proc.stdout
        assert "organ/_temporal_refresh_loop" in proc.stdout
        assert "loop/self_repair" in proc.stdout
        assert "started=" in proc.stdout
        report = tmp_path / "health-table.txt"
        report.write_text(proc.stdout, encoding="utf-8")
        mirror = Path("/tmp/aureon-launcher-smoke.txt")
        mirror.write_text(proc.stdout, encoding="utf-8")
    finally:
        subprocess.run(
            [sys.executable, "-m", "aureon.launch.master", "--stop"],
            cwd=clone,
            env=env,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )

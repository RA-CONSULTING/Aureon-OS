"""The Queen's repair loop must launch the repair and the benchmark gate from the
running checkout, with an isolated env.

Before this fix both were started with ``python -m ...`` and ``cwd=<repair root>``.
Python puts the cwd first on sys.path, so the child imported the repair root's
own (possibly stale) copy of the repair code, and both children got
``dict(os.environ)``: every exchange key, passwords and the master key.

These tests start the real subprocesses. The repair root is a tmp "foreign"
directory holding shadow copies of ``aureon_fusion.repair`` and
``aureon.autonomous.queen_benchmark_gate``. A ``sitecustomize`` probe, put on
PYTHONPATH, records in every child which module file was imported and which
env names it saw (names only, never values).
"""

from __future__ import annotations

import json
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

import aureon.core.aureon_baton_link as baton

RUN_ROOT = Path(baton.__file__).resolve().parents[2]

FAKE_SECRETS = {
    "CAPITAL_API_KEY": "fake-capital-key",
    "BINANCE_API_SECRET": "fake-binance-secret",
    "KRAKEN_API_KEY": "fake-kraken-key",
    "ALPACA_SECRET_KEY": "fake-alpaca-secret",
    "UKDI_GRANT_PASSWORD": "fake-ukdi-password",
    "AUREON_MASTER_ENCRYPTION_KEY": "fake-master-key",
    "FOO_PASSWORD": "fake-foo-password",
    "BAR_TOKEN": "fake-bar-token",
    "FOO_PASSWORD_FILE": "fake-foo-password-file",
    "BAR_TOKEN_RW": "fake-bar-token-rw",
}
# How the live kill chain runs: every arming and autonomy switch on.
LIVE_SWITCHES = {
    "AUREON_LIVE_TRADING": "1",
    "AUREON_FUSION_ARM_LIVE": "1",
    "AUREON_DISABLE_REAL_ORDERS": "0",
    "AUREON_DISABLE_EXCHANGE_MUTATIONS": "0",
    "AUREON_DISABLE_LIVE_BACKGROUND_STARTUP": "0",
    "AUREON_AUTONOMY_MODE": "full",
    "AUREON_CODE_AUTO_APPROVE": "1",
    "AUREON_DRY_RUN": "0",
    "DRY_RUN": "0",
    "AUREON_MAY_ACT": "1",
    "AUREON_ORDER_INTENT_PUBLISH": "1",
    "AUREON_UNIFIED_ORDER_EXECUTOR": "1",
    "LIVE": "1",
    "AUREON_LIVE": "1",
    "LIVE_TRADING": "1",
    "REAL_MONEY": "1",
    "CONFIRM_LIVE": "yes",
    "CONFIRM_LIVE_TRADING": "yes",
    "AUREON_ACCEPT_LIVE_RISK": "1",
    "AUREON_OPERATOR_ALLOW_LIVE": "1",
    "AUREON_GO_LIVE_CLEAR": "1",
    "AUREON_AZYRA_EXECUTE_LIVE": "1",
    "AUREON_AUTOSTART_LIVE_RUNNER": "1",
    "AUREON_DESKTOP_LIVE": "1",
    "AUREON_DESKTOP_AUTO_ARM": "1",
    "AUREON_LOCAL_ACTIONS_ARMED": "1",
    "AUREON_SOUL_ACT": "1",
    "AUREON_QUEEN_AUTO_PUSH": "1",
    "AUREON_QUEEN_SELF_REBOOT": "1",
    "AUREON_FORCE_ARM": "1",
    "AUREON_BILLING_CHARGE_ENABLED": "1",
    "AUREON_SOVEREIGN_MODE": "1",
    "EPICENTER_LIVE": "YES",
    "SOME_NEW_LIVE_SWITCH": "1",
    "AUREON_ACTIVATE_ON_IMPORT": "1",
    "PAPER": "0",
    "PAPER_TRADING": "false",
    "USE_TESTNET": "0",
    "SIMULATION_MODE": "0",
    "DEMO_MODE": "0",
    "ALPACA_PAPER": "false",
    "ALPACA_DRY_RUN": "false",
    "BINANCE_USE_TESTNET": "false",
    "BINANCE_TESTNET": "false",
    "BINANCE_DRY_RUN": "false",
    "KRAKEN_DRY_RUN": "false",
    "CAPITAL_DEMO": "0",
}
# Expected in every child, whatever the parent had.
SAFETY = {
    "PYTHON_DOTENV_DISABLED": "1",
    "AUREON_LIVE_TRADING": "0",
    "AUREON_FUSION_ARM_LIVE": "",
    "AUREON_DISABLE_REAL_ORDERS": "1",
    "AUREON_DISABLE_EXCHANGE_MUTATIONS": "1",
    "AUREON_DISABLE_LIVE_BACKGROUND_STARTUP": "1",
    "AUREON_AUTONOMY_MODE": "guarded",
    "AUREON_CODE_AUTO_APPROVE": "0",
    "AUREON_DRY_RUN": "1",
    "DRY_RUN": "1",
    "AUREON_ACTIVATE_ON_IMPORT": "0",
    "PAPER": "1",
    "PAPER_TRADING": "true",
    "USE_TESTNET": "1",
    "SIMULATION_MODE": "1",
    "DEMO_MODE": "1",
    "ALPACA_PAPER": "true",
    "ALPACA_DRY_RUN": "true",
    "BINANCE_USE_TESTNET": "true",
    "BINANCE_TESTNET": "true",
    "BINANCE_DRY_RUN": "true",
    "KRAKEN_DRY_RUN": "true",
    "CAPITAL_DEMO": "1",
}
# Must not reach a child at all.
UNSET_SWITCHES = tuple(name for name in LIVE_SWITCHES if name not in SAFETY)
# A module run with -m / runpy is __main__, so the probe records the packages it
# was imported from (both runs import them) and the repair engine itself.
WATCHED = ("aureon_fusion", "aureon", "aureon.autonomous", "aureon.autonomous.aureon_sandbox_self_repair")

_SHADOW = '''
import json, os, sys
with open(os.environ["BATON_TEST_RECORD"], "a", encoding="utf-8") as fh:
    fh.write(json.dumps({"shadow": __file__, "env_names": sorted(os.environ)}) + "\\n")
print(json.dumps({"status": "shadow", "summary": {}}))
'''

_PROBE = '''
import atexit, json, os, sys

def _record():
    if "--root" not in sys.argv:  # only the repair / gate children, not the organ itself
        return
    files = {name: getattr(sys.modules.get(name), "__file__", None) for name in %r}
    if not any(files.values()):
        return
    keep = %r
    with open(os.environ["BATON_TEST_RECORD"], "a", encoding="utf-8") as fh:
        fh.write(json.dumps({"pid": os.getpid(), "modules": files, "env_names": sorted(os.environ),
                             "safety": {k: os.environ.get(k) for k in keep}}) + "\\n")

atexit.register(_record)
''' % (WATCHED, tuple(SAFETY) + ("AUREON_SELF_REPAIR_ENABLE",))


class _StopLoop(BaseException):
    pass


class _SyncThread:
    def __init__(self, target=None, **_kwargs):
        self._target = target

    def start(self):
        try:
            self._target()
        except _StopLoop:
            pass


def _foreign_root(tmp_path: Path) -> Path:
    foreign = tmp_path / "foreign_repair_root"
    for package in ("aureon_fusion", "aureon", "aureon/autonomous"):
        (foreign / package).mkdir(parents=True, exist_ok=True)
        (foreign / package / "__init__.py").write_text("", encoding="utf-8")
    (foreign / "aureon_fusion" / "repair.py").write_text(_SHADOW, encoding="utf-8")
    (foreign / "aureon" / "autonomous" / "queen_benchmark_gate.py").write_text(_SHADOW, encoding="utf-8")
    return foreign


def _run_one_iteration(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, launch: str) -> list[dict]:
    """Run one pass of the real repair loop; only the `launch` subprocess runs for real."""

    foreign = _foreign_root(tmp_path)
    probe = tmp_path / "probe"
    probe.mkdir()
    (probe / "sitecustomize.py").write_text(textwrap.dedent(_PROBE), encoding="utf-8")
    record = tmp_path / "record.jsonl"
    work = tmp_path / "cwd"
    work.mkdir()

    for name, value in FAKE_SECRETS.items():
        monkeypatch.setenv(name, value)
    # The parent looks like a live organ: live switches on, dotenv allowed.
    for name, value in LIVE_SWITCHES.items():
        monkeypatch.setenv(name, value)
    monkeypatch.delenv("PYTHON_DOTENV_DISABLED", raising=False)
    monkeypatch.setenv("BATON_TEST_RECORD", str(record))
    monkeypatch.setenv("PYTHONPATH", str(probe))
    monkeypatch.setenv("AUREON_QUEEN_REPAIR_ROOT", str(foreign))
    monkeypatch.setenv("AUREON_SELF_REPAIR_SUITE_TIMEOUT_S", "60")
    monkeypatch.delenv("AUREON_QUEEN_SELF_REBOOT", raising=False)
    monkeypatch.delenv("PYTHONSAFEPATH", raising=False)
    monkeypatch.chdir(work)

    real_run = subprocess.run
    launched: list[list[str]] = []

    def spy(args, *a, **kw):
        argv = [str(x) for x in args]
        if any(launch in part for part in argv):
            launched.append(argv)
            kw["timeout"] = 120
            return real_run(args, *a, **kw)
        return subprocess.CompletedProcess(args, 0, "{}", "")

    def stop(_seconds):
        raise _StopLoop()

    import threading

    monkeypatch.setattr(subprocess, "run", spy)
    monkeypatch.setattr(threading, "Thread", _SyncThread)
    monkeypatch.setattr(baton.time, "sleep", stop)
    monkeypatch.setattr(baton, "relay_state", lambda *a, **k: None)
    try:
        baton._start_queen_repair_loop("test.baton")
    finally:
        lock = getattr(baton._start_queen_repair_loop, "lock", None)
        if lock is not None:
            lock.close()
    assert launched, f"the loop never launched {launch}"
    if not record.exists():
        return []
    return [json.loads(line) for line in record.read_text(encoding="utf-8").splitlines() if line.strip()]


def _assert_isolated(rows: list[dict], package: str) -> None:
    problems: list[str] = []
    shadows = [row["shadow"] for row in rows if "shadow" in row]
    if shadows:
        problems.append(f"child imported the repair root's shadow copy: {shadows}")
    mine = [row for row in rows if (row.get("modules") or {}).get(package)]
    if not mine and not shadows:
        problems.append(f"no child recorded importing {package}")
    for row in mine:
        loaded = Path(row["modules"][package]).resolve()
        if not loaded.is_relative_to(RUN_ROOT):
            problems.append(f"{package} came from {loaded}, not the run root {RUN_ROOT}")
    for row in rows:
        leaked = sorted(set(FAKE_SECRETS) & set(row["env_names"]))
        if leaked:
            problems.append(f"credential names reached the child: {leaked}")
        armed = sorted(set(UNSET_SWITCHES) & set(row["env_names"]))
        if armed:
            problems.append(f"arming switches reached the child: {armed}")
        for key, value in SAFETY.items():
            if "safety" in row and row["safety"].get(key) != value:
                problems.append(f"{key}={row['safety'].get(key)!r} in the child, expected {value!r}")
    assert not problems, "\n".join(problems)


def test_repair_launch_runs_run_root_code_without_credentials(tmp_path, monkeypatch):
    rows = _run_one_iteration(tmp_path, monkeypatch, "aureon_fusion.repair")
    _assert_isolated(rows, "aureon_fusion")
    mine = [row for row in rows if (row.get("modules") or {}).get("aureon_fusion")]
    assert all(row["safety"].get("AUREON_SELF_REPAIR_ENABLE") == "1" for row in mine)


def test_benchmark_gate_launch_runs_run_root_code_without_credentials(tmp_path, monkeypatch):
    rows = _run_one_iteration(tmp_path, monkeypatch, "aureon.autonomous.queen_benchmark_gate")
    _assert_isolated(rows, "aureon.autonomous")


def test_gate_pytest_children_get_isolated_env(tmp_path, monkeypatch):
    from aureon.autonomous import queen_benchmark_gate as gate

    for name, value in FAKE_SECRETS.items():
        monkeypatch.setenv(name, value)
    for name, value in LIVE_SWITCHES.items():
        monkeypatch.setenv(name, value)
    monkeypatch.delenv("PYTHON_DOTENV_DISABLED", raising=False)
    seen: dict = {}

    def fake_run(args, *a, **kw):
        seen.update(kw.get("env") or {})
        return subprocess.CompletedProcess(args, 0, "", "")

    monkeypatch.setattr(gate.subprocess, "run", fake_run)
    gate._pytest_paths(tmp_path, ["tests"])
    assert seen, "gate pytest got no explicit env"
    assert not set(FAKE_SECRETS) & set(seen)
    assert not set(UNSET_SWITCHES) & set(seen)
    for key, value in SAFETY.items():
        assert seen.get(key) == value, key


def test_gate_mutant_sites_come_from_the_root_under_test(tmp_path):
    from aureon.autonomous import queen_benchmark_gate as gate

    target = tmp_path / "aureon" / "exchanges" / "kraken_client.py"
    target.parent.mkdir(parents=True)
    target.write_text("def _finite_decimal(x):\n    return x + 1\n", encoding="utf-8")
    specs = gate.mutants("aureon.exchanges.kraken_client", "_finite_decimal", tmp_path)
    assert [spec["change"] for spec in specs] == ["Add->Sub", "const 1->2"]


def test_repair_root_equal_to_run_root_is_refused(monkeypatch):
    import threading

    calls = []
    started = []
    # Never start a real loop on the checkout under test, even if the guard is missing.
    monkeypatch.setattr(threading, "Thread", lambda *a, **k: type("T", (), {"start": lambda self: started.append(1)})())
    monkeypatch.setattr(baton, "open", lambda *a, **k: (_ for _ in ()).throw(AssertionError("lock opened")), raising=False)
    monkeypatch.setenv("AUREON_QUEEN_REPAIR_ROOT", str(RUN_ROOT))
    monkeypatch.setattr(baton, "relay_state", lambda *a, **k: calls.append(a))
    monkeypatch.chdir(RUN_ROOT.parent)
    baton._start_queen_repair_loop("test.baton")
    assert not started
    assert calls and calls[-1][1] == "not_doing"


_ORGAN = """
import json, os, sys, time
sys.path.insert(0, sys.argv[1])
import aureon.core.aureon_baton_link as baton
baton.activate_autonomous_control = lambda: None  # do not wake the whole Queen in a test
import aureon.harmonic.aureon_harmonic_seed  # noqa: F401  -- link_system(__name__) starts the repair loop
record = os.environ["BATON_TEST_RECORD"]
deadline = time.time() + 150
while time.time() < deadline:
    rows = []
    if os.path.exists(record):
        rows = [json.loads(line) for line in open(record, encoding="utf-8") if line.strip()]
    gate = any(r.get("shadow", "").endswith("queen_benchmark_gate.py") or
               ("--no-relay" in r.get("argv", [])) for r in rows)
    repair = any(r.get("shadow", "").endswith("repair.py") or
                 (r.get("modules") or {}).get("aureon_fusion") for r in rows)
    if gate and repair:
        break
    time.sleep(0.2)
print("organ done", flush=True)
"""


def test_organ_import_spawns_isolated_children(tmp_path):
    """The live leak path: an aureon_radar organ (here the harmonic seed loop's
    import of aureon.harmonic.aureon_harmonic_seed) calls link_system on import,
    which starts the Queen repair loop. The organ runs with live keys and live
    switches on; its repair and gate children must get neither."""

    foreign = _foreign_root(tmp_path)
    probe = tmp_path / "probe"
    probe.mkdir()
    (probe / "sitecustomize.py").write_text(
        textwrap.dedent(_PROBE.replace('"safety":', '"argv": sys.argv, "safety":')), encoding="utf-8")
    record = tmp_path / "record.jsonl"
    work = tmp_path / "organ_cwd"
    work.mkdir()
    import os

    env = {key: value for key, value in os.environ.items()
           if key not in ("AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS", "AUREON_AUDIT_MODE", "PYTHONSAFEPATH")}
    env.update(FAKE_SECRETS)
    env.update(LIVE_SWITCHES)
    env.update(AUREON_ACTIVATE_ON_IMPORT="1", AUREON_QUEEN_REPAIR_ROOT=str(foreign),
               AUREON_QUEEN_REPAIR_INTERVAL_S="3600", AUREON_SELF_REPAIR_SUITE_TIMEOUT_S="60",
               BATON_TEST_RECORD=str(record), PYTHONPATH=str(probe))
    env.pop("PYTHON_DOTENV_DISABLED", None)
    done = subprocess.run([sys.executable, "-c", _ORGAN, str(RUN_ROOT)], cwd=work, env=env,
                          capture_output=True, text=True, timeout=200)
    assert "organ done" in done.stdout, done.stderr[-2000:]
    rows = [json.loads(line) for line in record.read_text(encoding="utf-8").splitlines() if line.strip()]
    _assert_isolated(rows, "aureon_fusion")
    _assert_isolated(rows, "aureon.autonomous")
    assert any("--no-relay" in row.get("argv", []) for row in rows), "gate child never recorded"
    assert all("safety" in row for row in rows)


def test_isolated_child_env_disarms_fusion_and_drops_password_token_names():
    from aureon.launch.session_scope import isolated_child_env

    parent = {**FAKE_SECRETS, **LIVE_SWITCHES, "PATH": "/usr/bin",
              "GIT_CONFIG_KEY_0": "safe.directory", "AUREON_PHI_CHAT_MAX_TOKENS": "512",
              "AUREON_LLM_KEEP_ALIVE": "5m", "DELIVERY_WINDOW": "x", "OLIVER_PATH": "y",
              "AUREON_SELF_REPAIR_SUITE_TIMEOUT_S": "60", "lower_password_hint": "x", "my_token_path": "y"}
    child = isolated_child_env(parent)
    assert child["AUREON_FUSION_ARM_LIVE"] == ""
    for key, value in SAFETY.items():
        assert child[key] == value, key
    for name in (*FAKE_SECRETS, *UNSET_SWITCHES, "lower_password_hint", "my_token_path"):
        assert name not in child, name
    for name in ("PATH", "GIT_CONFIG_KEY_0", "AUREON_PHI_CHAT_MAX_TOKENS", "AUREON_SELF_REPAIR_SUITE_TIMEOUT_S",
                 "AUREON_LLM_KEEP_ALIVE", "DELIVERY_WINDOW", "OLIVER_PATH"):
        assert child[name] == parent[name], name
    assert parent["AUREON_FUSION_ARM_LIVE"] == "1"  # input not mutated


def test_repair_child_spec_keeps_fusion_disarmed_even_if_extra_tries(monkeypatch):
    for name, value in LIVE_SWITCHES.items():
        monkeypatch.setenv(name, value)
    _argv, _cwd, env = baton._repair_child_spec("aureon_fusion.repair", "/nonexistent",
                                                AUREON_FUSION_ARM_LIVE="1", AUREON_LIVE_TRADING="1")
    assert env["AUREON_FUSION_ARM_LIVE"] == ""
    assert env["AUREON_LIVE_TRADING"] == "0"


@pytest.mark.parametrize("name, dropped", [
    ("LIVE", True),
    ("live_mode", True),
    ("SOME_NEW_LIVE_SWITCH", True),
    ("AUREON_SELF_CODER_LIVECODE_URL", True),
    ("AUREON_LIVE_WAVEFORM_MAX_SYMBOLS", True),
    ("AUREON_LLM_KEEP_ALIVE", False),
    ("DELIVERY_WINDOW", False),
    ("OLIVER_PATH", False),
    ("AUREON_GROUND_LOCAL_ACTIONS", False),
])
def test_live_name_pattern(name, dropped):
    from aureon.launch.session_scope import isolated_child_env

    child = isolated_child_env({name: "1", "PATH": "/usr/bin"})
    assert (name not in child) is dropped


def test_exchange_prefix_drop_still_removes_credentials_but_keeps_forced_switches():
    from aureon.launch.session_scope import isolated_child_env

    parent = {
        "ALPACA_API_KEY": "fake", "ALPACA_SECRET_KEY": "fake", "APCA_API_KEY_ID": "fake",
        "BINANCE_API_KEY": "fake", "BINANCE_API_SECRET": "fake", "BINANCE_SECRET": "fake",
        "KRAKEN_API_KEY": "fake", "KRAKEN_PRIVATE_KEY": "fake", "CAPITAL_API_KEY": "fake",
        "CAPITAL_PASSWORD": "fake", "CAPITAL_IDENTIFIER": "fake", "COINBASE_API_SECRET": "fake",
        "CAPITAL_LIVE": "true", "KRAKEN_LIVE_ENABLED": "1", "APCA_LIVE": "1",
        **{name: LIVE_SWITCHES[name] for name in ("ALPACA_PAPER", "ALPACA_DRY_RUN", "BINANCE_USE_TESTNET",
                                                  "BINANCE_TESTNET", "BINANCE_DRY_RUN", "KRAKEN_DRY_RUN",
                                                  "CAPITAL_DEMO")},
    }
    child = isolated_child_env(parent)
    exchange = sorted(k for k in child if k.startswith(("ALPACA_", "APCA_", "BINANCE_", "KRAKEN_", "CAPITAL_", "COINBASE_")))
    assert exchange == sorted(["ALPACA_PAPER", "ALPACA_DRY_RUN", "BINANCE_USE_TESTNET", "BINANCE_TESTNET",
                               "BINANCE_DRY_RUN", "KRAKEN_DRY_RUN", "CAPITAL_DEMO"])
    for name in exchange:
        assert child[name] == SAFETY[name], name

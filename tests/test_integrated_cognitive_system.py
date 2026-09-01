"""Zero-dependency fail-closed contract for the public ICS facade."""

from __future__ import annotations

import importlib
import json
import os
from pathlib import Path
import runpy
import subprocess
import sys

import pytest

from aureon.core import integrated_cognitive_system as ics_module


def test_facade_preflight_is_an_explicit_unreleased_hold() -> None:
    preflight = ics_module.integrated_cognitive_system_security_preflight()

    assert preflight == {
        "schema": "aureon.integrated-cognitive-system.security-preflight.v1",
        "status": "HOLD",
        "reason_code": "production_magic_star_release_unavailable",
        "subsystem_imports_performed": False,
        "credentials_loaded": False,
        "network_started": False,
        "threads_started": False,
        "production_magic_star_release_available": False,
        "production_ready": False,
    }


def test_constructor_is_inert_and_all_execution_entrypoints_hold() -> None:
    system = ics_module.IntegratedCognitiveSystem()

    assert system._running is False
    assert system._tick_thread is None
    assert system._vault_ui_thread is None
    assert system._boot_status == {}
    with pytest.raises(RuntimeError, match="boot_hold"):
        system.boot()
    with pytest.raises(RuntimeError, match="runtime_hold"):
        system.run()
    with pytest.raises(RuntimeError, match="external_exposure_hold"):
        system.run(lan=True)
    with pytest.raises(RuntimeError, match="cognitive_tick_start_hold"):
        system._start_tick_thread()
    with pytest.raises(RuntimeError, match="cognitive_tick_hold"):
        system._unified_cognitive_tick()
    with pytest.raises(RuntimeError, match="vault_ui_start_hold"):
        system._start_vault_ui()
    with pytest.raises(RuntimeError, match="cognitive_input_hold"):
        system.process_user_input("/accounts build")
    assert system._start_tunnel(5566) is None


def test_unreleased_implementation_raises_before_legacy_imports() -> None:
    with pytest.raises(RuntimeError, match="unreleased_import_hold"):
        importlib.import_module("aureon.core.integrated_cognitive_system_unreleased")


def test_fresh_process_import_performs_no_provider_or_filesystem_bootstrap(
    tmp_path: Path,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    script = r'''
import json
import os
from pathlib import Path
import socket
import sys
import threading
import types

repo = Path(sys.argv[1])
work = Path(sys.argv[2])
sys.path.insert(0, str(repo))
os.chdir(work)
os.environ["AUREON_ACTIVATE_ON_IMPORT"] = "1"
os.environ["AUREON_ENABLE_MARKET_DOTENV"] = "1"
os.environ["AUREON_LLM_BASE_URL"] = "https://provider.invalid"

socket.socket = lambda *_a, **_k: (_ for _ in ()).throw(RuntimeError("socket-called"))
threading.Thread = lambda *_a, **_k: (_ for _ in ()).throw(RuntimeError("thread-called"))
fake_dotenv = types.ModuleType("dotenv")
fake_dotenv.load_dotenv = lambda *_a, **_k: (_ for _ in ()).throw(RuntimeError("dotenv-called"))
sys.modules["dotenv"] = fake_dotenv

before = sorted(p.name for p in work.iterdir())
from aureon.core.integrated_cognitive_system import IntegratedCognitiveSystem
system = IntegratedCognitiveSystem()
after = sorted(p.name for p in work.iterdir())
print(json.dumps({"before": before, "after": after, "status": system.security_preflight()}))
'''
    env = dict(os.environ)
    env.pop("PYTHONPATH", None)
    completed = subprocess.run(
        [sys.executable, "-I", "-c", script, str(repo_root), str(tmp_path)],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    receipt = json.loads(completed.stdout.strip())
    assert receipt["before"] == receipt["after"]
    assert receipt["status"]["status"] == "HOLD"
    assert receipt["status"]["subsystem_imports_performed"] is False


@pytest.mark.parametrize(
    "relative_path,extra_args",
    [
        ("scripts/boot_diagnostic.py", []),
        ("scripts/demos/headless_watch.py", []),
        (
            "scripts/demos/run_integrated_cognitive_system.py",
            ["--lan", "--remote", "--port", "8080"],
        ),
    ],
)
def test_public_ics_clients_return_only_the_release_hold(
    relative_path: str,
    extra_args: list[str],
    tmp_path: Path,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    completed = subprocess.run(
        [sys.executable, "-I", "-B", str(repo_root / relative_path), *extra_args],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    assert completed.returncode == 2
    payload = (completed.stdout + completed.stderr).strip()
    receipt = json.loads(payload)
    assert receipt["status"] == "HOLD"
    assert receipt["subsystem_imports_performed"] is False
    assert receipt["network_started"] is False
    assert receipt["threads_started"] is False
    assert receipt["production_ready"] is False
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize(
    "relative_path",
    [
        "scripts/boot_diagnostic.py",
        "scripts/demos/headless_watch.py",
        "scripts/demos/run_integrated_cognitive_system.py",
    ],
)
def test_public_ics_clients_do_not_resolve_filesystem_paths(
    relative_path: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    script = repo_root / relative_path

    def reject_resolve(*_args: object, **_kwargs: object) -> Path:
        raise AssertionError("public ICS client attempted Path.resolve")

    monkeypatch.setattr(Path, "resolve", reject_resolve)
    monkeypatch.setattr(sys, "argv", [str(script)])
    with pytest.raises(SystemExit) as stopped:
        runpy.run_path(str(script), run_name="__main__")
    assert stopped.value.code == 2

"""Release-facade tests for the two historical live persona launchers."""

from __future__ import annotations

import importlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


class _Trap:
    def __getattribute__(self, _name: str) -> Any:
        raise AssertionError("release-held CLI touched an effect owner")


def test_ask_aureon_facade_is_inert_and_effect_methods_hold(
    capsys: pytest.CaptureFixture[str],
) -> None:
    module = importlib.import_module("scripts.ask_aureon")
    receipt = module.preflight()
    assert receipt["status"] == "HOLD"
    assert receipt["effect_enabled"] is False
    assert receipt["thread_started"] is False
    assert receipt["obsidian_attached"] is False

    session = module.ConversationSession(_Trap(), _Trap(), _Trap())
    ambient = module.AmbientEngine(session)
    adapter = module.PersonaResponseAdapter(question="probe")
    for call in (
        lambda: module.apply_mood(_Trap(), "rally", _Trap()),
        lambda: session.attach_obsidian("forbidden"),
        lambda: session.mirror_to_obsidian(_Trap()),
        lambda: session.ask("hello"),
        ambient.start,
        ambient._loop,
        ambient._beat,
        lambda: module._build_session(1, "rally"),
        lambda: adapter.prompt([], system="held"),
        lambda: adapter.stream([]),
    ):
        with pytest.raises(RuntimeError, match="ask_aureon_hold"):
            call()
    assert session.transcript == []
    assert ambient.running is False
    assert adapter.health_check() is False
    assert module.main([]) == 2
    emitted = json.loads(capsys.readouterr().err)
    assert emitted == receipt


def test_live_facade_is_inert_and_never_starts_workers(
    capsys: pytest.CaptureFixture[str],
) -> None:
    module = importlib.import_module("scripts.run_aureon_live")
    receipt = module.preflight()
    assert receipt["status"] == "HOLD"
    assert receipt["effect_enabled"] is False
    assert receipt["ambient_thread_started"] is False
    assert receipt["heartbeat_thread_started"] is False
    for worker in (module.AmbientSignals(_Trap()), module.Heartbeat(_Trap())):
        with pytest.raises(RuntimeError, match="run_aureon_live_hold"):
            worker.start()
        with pytest.raises(RuntimeError, match="run_aureon_live_hold"):
            worker._loop()
    assert module.main([]) == 2
    assert json.loads(capsys.readouterr().err) == receipt


@pytest.mark.parametrize("name", ["ask_aureon", "run_aureon_live"])
def test_cli_fresh_process_returns_only_hold_receipt(name: str, tmp_path: Path) -> None:
    script = REPO_ROOT / "scripts" / f"{name}.py"
    result = subprocess.run(
        [sys.executable, "-I", "-B", str(script), "--live", "probe"],
        cwd=tmp_path,
        check=False,
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert result.returncode == 2
    assert result.stdout == ""
    receipt = json.loads(result.stderr)
    assert receipt["status"] == "HOLD"
    assert receipt["effect_enabled"] is False
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize(
    "name",
    ["ask_aureon_unreleased", "run_aureon_live_unreleased"],
)
def test_unreleased_archives_raise_before_importing_aureon(
    name: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import builtins
    import runpy

    real_import = builtins.__import__

    def guarded_import(module_name: str, *args: Any, **kwargs: Any):
        if module_name == "aureon" or module_name.startswith("aureon."):
            raise AssertionError("unreleased archive imported Aureon before HOLD")
        return real_import(module_name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guarded_import)
    archive = REPO_ROOT / "scripts" / f"{name}.py"
    with pytest.raises(RuntimeError, match="unreleased_import_hold"):
        runpy.run_path(str(archive), run_name=f"held_{name}")

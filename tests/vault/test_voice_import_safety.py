"""Hostile fresh-process import probe for the public Vault voice package."""

from __future__ import annotations

import json
import subprocess
import sys
import textwrap
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_voice_package_import_has_zero_runtime_effects(tmp_path: Path) -> None:
    probe = textwrap.dedent(
        r"""
        import builtins
        import importlib
        import json
        import logging
        import os
        import pathlib
        import socket
        import subprocess
        import sys
        import threading
        import types

        repo = sys.argv[1]
        sys.path.insert(0, repo)

        def bomb(label):
            def _bomb(*args, **kwargs):
                raise AssertionError(label)
            return _bomb

        socket.socket = bomb("socket.socket")
        socket.create_connection = bomb("socket.create_connection")
        subprocess.Popen = bomb("subprocess.Popen")
        threading.Thread = bomb("threading.Thread")
        pathlib.Path.mkdir = bomb("Path.mkdir")
        pathlib.Path.write_text = bomb("Path.write_text")
        pathlib.Path.write_bytes = bomb("Path.write_bytes")
        pathlib.Path.touch = bomb("Path.touch")
        pathlib.Path.resolve = bomb("Path.resolve")
        os.mkdir = bomb("os.mkdir")
        os.makedirs = bomb("os.makedirs")

        real_open = builtins.open
        def guarded_open(file, mode="r", *args, **kwargs):
            if any(flag in str(mode) for flag in ("w", "a", "x", "+")):
                raise AssertionError("write-open")
            return real_open(file, mode, *args, **kwargs)
        builtins.open = guarded_open

        dotenv = types.ModuleType("dotenv")
        dotenv.load_dotenv = bomb("dotenv.load_dotenv")
        dotenv.dotenv_values = bomb("dotenv.dotenv_values")
        sys.modules["dotenv"] = dotenv

        env_before = dict(os.environ)
        files_before = sorted(os.listdir("."))
        stdout_before = sys.stdout
        stderr_before = sys.stderr
        handlers_before = tuple(logging.getLogger().handlers)
        active_before = threading.active_count()

        modules = [
            "aureon.vault.voice",
            "aureon.vault.voice.persona_action",
            "aureon.vault.voice.persona_vacuum",
            "aureon.vault.voice.skill_executor_bridge",
            "aureon.vault.voice.goal_dispatch_bridge",
            "aureon.vault.voice.affinity_chorus",
            "aureon.vault.voice.opportunity_scanner",
        ]
        for name in modules:
            importlib.import_module(name)

        assert dict(os.environ) == env_before
        assert sorted(os.listdir(".")) == files_before
        assert sys.stdout is stdout_before
        assert sys.stderr is stderr_before
        assert tuple(logging.getLogger().handlers) == handlers_before
        assert threading.active_count() == active_before
        assert "aureon.inhouse_ai.llm_adapter" not in sys.modules

        skill = sys.modules["aureon.vault.voice.skill_executor_bridge"]
        goal = sys.modules["aureon.vault.voice.goal_dispatch_bridge"]
        assert skill._singleton is None
        assert goal._singleton is None

        print(json.dumps({"ok": True, "modules": len(modules)}))
        """
    )
    result = subprocess.run(
        [sys.executable, "-I", "-B", "-c", probe, str(REPO_ROOT)],
        cwd=tmp_path,
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {"ok": True, "modules": 7}
    assert result.stderr == ""
    assert list(tmp_path.iterdir()) == []

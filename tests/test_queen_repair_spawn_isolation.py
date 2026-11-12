"""Queen repair children must load the live packages and inherit no keys."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

import aureon.core.aureon_baton_link as baton

# Same pattern the child env is required to strip. Names only in assertions.
_CREDENTIAL_NAME_RE = re.compile(
    r"(?:CAPITAL_|BINANCE_|KRAKEN_|ALPACA_|APCA_|_KEY|_SECRET|_TOKEN|PASSWORD)"
)

_FAKE_CREDENTIAL_NAMES = (
    "CAPITAL_API_KEY",
    "CAPITAL_PASSWORD",
    "BINANCE_API_SECRET",
    "KRAKEN_API_KEY",
    "ALPACA_SECRET_KEY",
    "APCA_API_KEY_ID",
    "AUREON_INGEST_TOKEN",
    "MASTER_ENCRYPTION_KEY",
    "AUREON_GRANT_IFS_PASSWORD_STORE",
)


def _live_root() -> Path:
    fn = getattr(baton, "running_code_root", None)
    if callable(fn):
        return fn().resolve()
    return Path(baton.__file__).resolve().parents[2]


def _repair_spec(root: Path | str) -> dict:
    fn = getattr(baton, "queen_repair_spawn_spec", None)
    if callable(fn):
        return fn(root)
    root_s = str(root)
    return {
        "cmd": [sys.executable, "-m", "aureon_fusion.repair", "--root", root_s],
        "cwd": root_s,
        "env": dict(os.environ, AUREON_SELF_REPAIR_ENABLE="1"),
    }


def _gate_spec(root: Path | str) -> dict:
    fn = getattr(baton, "queen_benchmark_gate_spawn_spec", None)
    if callable(fn):
        return fn(root)
    root_s = str(root)
    return {
        "cmd": [
            sys.executable,
            "-m",
            "aureon.autonomous.queen_benchmark_gate",
            "--root",
            root_s,
            "--no-relay",
        ],
        "cwd": root_s,
        "env": dict(os.environ),
    }


def _child_env() -> dict[str, str]:
    fn = getattr(baton, "isolated_queen_child_env", None)
    if callable(fn):
        return fn()
    return dict(os.environ)


def _stale_worktree(tmp_path: Path) -> Path:
    """A fake repair target whose aureon_fusion would win if cwd were searched."""

    root = tmp_path / "stale_repair_wt"
    pkg = root / "aureon_fusion"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text("STALE_PACKAGE = True\n", encoding="utf-8")
    (pkg / "repair.py").write_text(
        "STALE_REPAIR = True\n\n"
        "def main():\n"
        "    raise SystemExit('stale worktree repair was imported')\n",
        encoding="utf-8",
    )
    return root


def test_repair_spawn_uses_live_module_despite_stale_cwd(tmp_path: Path) -> None:
    stale = _stale_worktree(tmp_path)
    spec = _repair_spec(stale)
    live_root = _live_root()
    assert spec["cwd"] == str(stale)
    assert "--root" in spec["cmd"] and str(stale) in spec["cmd"]

    # Honour the spawn flags: -P when the builder asks for it, and the child env.
    prefix: list[str] = [sys.executable]
    if "-P" in spec["cmd"]:
        prefix.append("-P")
    probe = prefix + [
        "-c",
        "import json, aureon_fusion, aureon_fusion.repair as repair\n"
        "print(json.dumps({"
        "'fusion': aureon_fusion.__file__, "
        "'repair': repair.__file__, "
        "'stale_package': getattr(aureon_fusion, 'STALE_PACKAGE', False), "
        "'stale_repair': getattr(repair, 'STALE_REPAIR', False)"
        "}))",
    ]
    result = subprocess.run(
        probe,
        cwd=spec["cwd"],
        env=spec["env"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, (result.stdout or "") + (result.stderr or "")
    seen = json.loads(result.stdout.strip().splitlines()[-1])
    live_s = str(live_root)
    stale_s = str(stale.resolve())
    assert seen["fusion"].startswith(live_s), seen["fusion"]
    assert seen["repair"].startswith(live_s), seen["repair"]
    assert stale_s not in seen["fusion"]
    assert stale_s not in seen["repair"]
    assert seen["stale_package"] is False
    assert seen["stale_repair"] is False

    gate = _gate_spec(stale)
    gate_prefix: list[str] = [sys.executable]
    if "-P" in gate["cmd"]:
        gate_prefix.append("-P")
    gate_probe = gate_prefix + [
        "-c",
        "import json, aureon.autonomous.queen_benchmark_gate as gate\n"
        "print(json.dumps({'gate': gate.__file__}))",
    ]
    gate_result = subprocess.run(
        gate_probe,
        cwd=gate["cwd"],
        env=gate["env"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert gate_result.returncode == 0, (gate_result.stdout or "") + (gate_result.stderr or "")
    gate_seen = json.loads(gate_result.stdout.strip().splitlines()[-1])
    assert gate_seen["gate"].startswith(live_s), gate_seen["gate"]
    assert stale_s not in gate_seen["gate"]


def test_queen_child_env_has_no_credential_names(monkeypatch) -> None:
    for name in _FAKE_CREDENTIAL_NAMES:
        monkeypatch.setenv(name, "fake")
    monkeypatch.setenv("PATH", "/usr/bin")
    monkeypatch.delenv("PYTHON_DOTENV_DISABLED", raising=False)

    repair_env = _repair_spec("/tmp/unused-root")["env"]
    gate_env = _gate_spec("/tmp/unused-root")["env"]
    cleaned = _child_env()

    for env in (repair_env, gate_env, cleaned):
        leaked = sorted(name for name in env if _CREDENTIAL_NAME_RE.search(name))
        assert leaked == [], leaked
        assert env.get("PYTHON_DOTENV_DISABLED") == "1"
        for name in _FAKE_CREDENTIAL_NAMES:
            assert name not in env

    assert repair_env.get("AUREON_SELF_REPAIR_ENABLE") == "1"

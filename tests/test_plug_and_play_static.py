"""Static checks for the local plug-and-play boot. The live proof is ./install.sh --smoke."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _text(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_install_script_uses_the_lockfile_and_does_not_read_dotenv() -> None:
    script = _text("install.sh")
    assert script.startswith("#!/usr/bin/env bash\n")
    assert "requirements-plug.lock" in script
    assert "scripts/plug_and_play.py" in script
    assert "npm ci --ignore-scripts --prefix frontend" in script
    assert "source .env" not in script
    assert "cp .env" not in script


def test_supervisor_keeps_trading_and_external_models_off() -> None:
    source = _text("scripts/plug_and_play.py")
    assert 'AUREON_LIVE_TRADING": "0"' in source
    assert 'AUREON_LLM_OFFLINE": "1"' in source
    assert 'AUREON_AUTONOMY_MODE": "guarded"' in source
    assert 'AUREON_PLUG_AND_PLAY": "1"' in source
    assert "evaluate_brain" in source
    assert "aureon_public" in source
    assert "aureon.operator.operator_server" in source


def test_readme_quick_start_is_at_the_top() -> None:
    readme = _text("README.md")
    heading = "## Quick start in five minutes"
    position = readme.find(heading)
    assert position != -1
    assert position < 2500
    assert "./install.sh" in readme[position:position + 2500]
    assert "SMOKE PASSED" in readme


def test_ci_runs_the_smoke_from_a_clean_checkout() -> None:
    workflow = _text(".github/workflows/plug-and-play.yml")
    assert "actions/checkout@v4" in workflow
    assert "./install.sh --smoke" in workflow
    assert "ubuntu-latest" in workflow


def test_env_example_has_no_secret_values() -> None:
    for line in _text(".env.example").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        key = key.strip()
        value = value.split("#", 1)[0].strip().strip('"').strip("'")
        upper = key.upper()
        if upper.endswith(("_KEY", "_SECRET", "_TOKEN", "_PASSWORD", "_PASSWD")):
            assert value == "", key
        assert "sk-" not in value
        assert "AKIA" not in value


def test_lockfile_pins_the_direct_requirements() -> None:
    direct = _text("requirements-plug.txt")
    lock = _text("requirements-plug.lock")
    for line in direct.splitlines():
        if not line or line.startswith("#"):
            continue
        assert line in lock
    assert "mcp==1.30.0" in lock

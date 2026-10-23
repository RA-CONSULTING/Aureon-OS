"""A fresh checkout must not name a home directory or another machine."""

from __future__ import annotations

import re
from pathlib import Path

from aureon.launch.master import SAFE_ENV_OVERLAY, _apply_safe_overlay, _ensure_local_env, paper_env

ROOT = Path(__file__).resolve().parents[1]

# User-profile and host paths. Standard Windows system locations (C:/Windows,
# Program Files) are reviewed pins and are listed in PORTABILITY.md.
FORBIDDEN = re.compile(
    r"C:/Users/|C:\\Users\\|/home/user|/home/gary|/home/ubuntu|/home/l\b|"
    r"Users\\Gary|kimi_openclaw|CodexPROsSparrow|AppData/Local/Programs/Python"
)

SCAN_ROOTS = (
    "aureon",
    "aureon_radar",
    "aureon_fusion",
    "scripts",
    "unified_margin_trader",
    "daemon_codes",
    "deploy",
    "imports",
)
SCAN_SUFFIXES = {".py", ".sh", ".ps1", ".yml", ".yaml", ".bat"}


def test_runtime_trees_do_not_name_a_home_directory() -> None:
    hits: list[str] = []
    for folder in SCAN_ROOTS:
        base = ROOT / folder
        if not base.is_dir():
            continue
        for path in base.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in SCAN_SUFFIXES:
                continue
            if any(part in {".venv", "node_modules", "__pycache__"} for part in path.parts):
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            for number, line in enumerate(text.splitlines(), 1):
                if FORBIDDEN.search(line):
                    hits.append(f"{path.relative_to(ROOT)}:{number}:{line.strip()[:160]}")
    assert hits == []


def test_generated_env_uses_safe_defaults_and_is_not_overwritten(tmp_path: Path) -> None:
    example = ROOT / ".env.example"
    (tmp_path / ".env.example").write_text(example.read_text(encoding="utf-8"), encoding="utf-8")
    ok, detail = _ensure_local_env(tmp_path)
    assert ok, detail
    written = (tmp_path / ".env").read_text(encoding="utf-8")
    assert "\nAUREON_LIVE_TRADING=" not in f"\n{written}"
    assert "ALPACA_PAPER=false" in written
    assert "CAPITAL_DEMO_MODE=false" in written
    assert "QUICKBOOKS_ALLOW_MUTATION=false" in written
    assert "QUICKBOOKS_ENVIRONMENT=sandbox" in written
    assert "BINANCE_API_KEY=" in written
    assert "SERO_WORKSPACE=" not in written
    assert "C:/Users" not in written
    assert "/home/" not in written
    (tmp_path / ".env").write_text("SENTINEL=keep\n", encoding="utf-8")
    ok, detail = _ensure_local_env(tmp_path)
    assert ok
    assert "unchanged" in detail
    assert (tmp_path / ".env").read_text(encoding="utf-8") == "SENTINEL=keep\n"


def test_missing_env_example_is_a_blocked_reason(tmp_path: Path) -> None:
    ok, detail = _ensure_local_env(tmp_path)
    assert ok is False
    assert ".env.example missing" in detail
    assert not (tmp_path / ".env").exists()


def test_safe_overlay_keeps_comments_and_empty_secrets() -> None:
    rendered = _apply_safe_overlay("# note\nALPACA_PAPER=false\nBINANCE_API_KEY=\n")
    assert rendered.startswith("# note\n")
    assert "ALPACA_PAPER=false" in rendered
    assert "BINANCE_API_KEY=" in rendered
    for key, value in SAFE_ENV_OVERLAY.items():
        assert f"{key}={value}" in rendered


def test_child_workspace_is_the_launched_checkout(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("AUREON_AUTONOMY_MODE", raising=False)
    monkeypatch.delenv("AUREON_SELF_REPAIR_KILL", raising=False)
    env = paper_env({"SERO_WORKSPACE": "/tmp/other-checkout", "PYTHONPATH": ""}, tmp_path)
    assert env["SERO_WORKSPACE"] == str(tmp_path.resolve())
    assert env["AUREON_LIVE_TRADING"] == "0"
    assert env["AUREON_FUSION_ARM_LIVE"] == ""
    assert env["AUREON_MAY_ACT"] == "1"

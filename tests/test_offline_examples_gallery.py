"""The public gallery stays on fixtures and leaves the pin and the badge alone."""

from __future__ import annotations

import ast
import hashlib
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
GALLERY = ROOT / "examples" / "offline"
BANNER = "This gallery is not a production-ready release."
LOCKED = (
    "README.md",
    "mcp/aureon_public/guard_loader.py",
    "mcp/aureon_public/pin_blob.py",
    "mcp/aureon_public/sweep_guard.py",
    "scripts/linux/install-linux.sh",
    "reports/measured/market_series.json",
    "reports/measured/native_process_containment.json",
    "reports/measured/native_process_containment.md",
)
SCRIPTS = (
    "load_market_series.py",
    "run_brain_proof.py",
    "cold_boot.py",
    "offline.py",
)
_FORBIDDEN_MODULES = {"urllib", "socket", "requests"}
_FORBIDDEN_NAMES = {"measure", "write_receipt", "http_get", "urlopen"}
_FORBIDDEN_ATTRS = {"http_get", "urlopen", "measure", "write_receipt", "create_connection"}


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture
def locked_hashes() -> dict[str, str]:
    before = {name: _sha(ROOT / name) for name in LOCKED}
    yield before
    assert {name: _sha(ROOT / name) for name in LOCKED} == before


def _run(script: str, timeout: int) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["AUREON_LLM_OFFLINE"] = "1"
    env["AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS"] = "1"
    env["AUREON_DISABLE_REAL_ORDERS"] = "1"
    env["AUREON_LIVE_TRADING"] = "0"
    env["PYTHONPATH"] = str(ROOT)
    return subprocess.run(
        [sys.executable, str(GALLERY / script)],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


def _assert_limits(proc: subprocess.CompletedProcess[str]) -> str:
    output = proc.stdout + proc.stderr
    assert proc.returncode == 0, output
    assert "Traceback" not in output
    folded = output.casefold()
    assert BANNER.casefold() in folded
    assert "is production ready" not in folded
    assert "is production-ready" not in folded
    assert "no order is placed" in folded
    return output


def test_market_series_load_uses_the_fixture(locked_hashes: dict[str, str]) -> None:
    output = _assert_limits(_run("load_market_series.py", 60))
    assert "public:kraken" in output
    assert "orders_placed=False" in output
    assert "live_trading=False" in output
    assert "sandbox check exit 0" in output
    assert "No venue was contacted." in output
    assert "reports/measured in the checkout was not written" in output
    assert locked_hashes["README.md"] == _sha(ROOT / "README.md")


@pytest.mark.timeout(180)
def test_brain_proof_uses_the_fixture_sandbox(locked_hashes: dict[str, str]) -> None:
    output = _assert_limits(_run("run_brain_proof.py", 170))
    assert "Live trading stayed off" in output
    assert "No order was placed" in output
    assert "public:kraken" in output
    assert "live_trading=False" in output
    assert "orders_placed=False" in output
    assert "HOLD" in output
    assert "derived series in this sandbox: absent" in output
    assert "No venue was contacted." in output
    assert locked_hashes["reports/measured/market_series.json"] == _sha(
        ROOT / "reports/measured/market_series.json"
    )


def test_cold_boot_judges_the_fixture_and_does_not_boot(locked_hashes: dict[str, str]) -> None:
    output = _assert_limits(_run("cold_boot.py", 60))
    assert "fixture judge verdict: pass" in output
    assert "allowed at default: none" in output
    assert "was not run" in output
    assert "bb04503119681adcf832f3c3e9b0cbf09fc7a938" in output
    assert "34864ff0547d2cff03e707414743a3b0cc8770b5" in output
    assert "pin_changed was not written" in output
    assert "Release boundary stays HOLD. Receipts 2, 3, 4, and 5 stay HOLD." in output
    assert locked_hashes["mcp/aureon_public/guard_loader.py"] == _sha(
        ROOT / "mcp/aureon_public/guard_loader.py"
    )
    assert "release%20boundary-HOLD-orange" in (ROOT / "README.md").read_text(encoding="utf-8")


def test_gallery_sources_do_not_call_the_network_or_the_measurer() -> None:
    for name in SCRIPTS:
        tree = ast.parse((GALLERY / name).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                modules = [alias.name.split(".", 1)[0] for alias in node.names]
                assert _FORBIDDEN_MODULES.isdisjoint(modules), name
            elif isinstance(node, ast.ImportFrom):
                root_name = (node.module or "").split(".", 1)[0]
                assert root_name not in _FORBIDDEN_MODULES, name
                imported = {alias.name for alias in node.names}
                assert _FORBIDDEN_NAMES.isdisjoint(imported), name
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                assert node.func.attr not in _FORBIDDEN_ATTRS, name


def test_gallery_docs_keep_the_hold_line() -> None:
    gallery = (GALLERY / "README.md").read_text(encoding="utf-8")
    docs = (ROOT / "docs" / "examples" / "README.md").read_text(encoding="utf-8")
    index = (ROOT / "docs" / "INDEX.md").read_text(encoding="utf-8")
    for text in (gallery, docs):
        folded = text.casefold()
        assert "not a production-ready release" in folded
        assert "is production ready" not in folded
        assert "hold" in folded
    assert "bb04503119681adcf832f3c3e9b0cbf09fc7a938" in gallery
    assert "go_live_clear" in gallery and "false" in gallery.casefold()
    assert "examples/README.md" in index
    assert "No live trading" in index
    assert (ROOT / "docs" / "examples" / "README.md").exists()

"""Static checks for the local plug-and-play boot. The live proof is ./install.sh --smoke."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Charlie rule: a secret assignment is blank, or an obvious placeholder name.
_PLACEHOLDER_VALUE = re.compile(
    r"^(?:your_[a-z0-9_]+_here|REDACTED_[A-Z0-9_]+|PLACEHOLDER_[A-Z0-9_]+|<[^>\n]+>)$"
)
_REAL_KEY = re.compile(
    r"sk-|AKIA[0-9A-Z]{4,}|ghp_|github_pat_|xox[baprs]-|AIza[0-9A-Za-z_\-]{10}|-----BEGIN "
)
_SECRET_SUFFIXES = ("_KEY", "_SECRET", "_TOKEN", "_PASSWORD", "_PASSWD")
_ENV_EXAMPLES = (
    ".env.example",
    "aureon_radar/.env.example",
    "sources/AUREON-QUANTUM-TRADING-SYSTEM-AQTS-/.env.example",
)


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


def test_trade_view_keeps_orders_placed_for_the_smoke_gate() -> None:
    import importlib.util

    path = ROOT / "scripts" / "plug_and_play.py"
    spec = importlib.util.spec_from_file_location("plug_and_play_under_test", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    full = {
        "entries": 0,
        "evidence_tag": "measured",
        "filled_outcomes": 0,
        "labels": [{"filled": False}],
        "orders_placed": False,
        "outcome_labels": "paper",
        "paper_labels": 166,
        "reason": "paper trade-outcome labels; measured fail; release boundary stays HOLD",
        "release_boundary": "HOLD",
        "verdict": "fail",
    }
    view = module._trade_view(full)
    assert view["orders_placed"] is False
    assert "labels" not in view
    assert module._cognition_trade_failure(view) is None
    dropped = dict(view)
    dropped.pop("orders_placed")
    assert module._cognition_trade_failure(dropped) == "cognition auris trade_readiness"
    placed = dict(full)
    placed["orders_placed"] = True
    assert module._cognition_trade_failure(module._trade_view(placed)) == "cognition auris trade_readiness"


def _is_editable_install_finder(finder: object) -> bool:
    """True for the meta-path finder setuptools writes for ``pip install -e``."""
    owner = finder if isinstance(finder, type) else type(finder)
    return str(getattr(owner, "__module__", "")).startswith("__editable__")


def test_editable_install_finder_is_recognised() -> None:
    editable = type("_EditableFinder", (), {"__module__": "__editable___aureon_2_1_0_finder"})
    assert _is_editable_install_finder(editable)
    assert _is_editable_install_finder(editable())
    import importlib.machinery

    assert not _is_editable_install_finder(importlib.machinery.PathFinder)


def test_supervisor_imports_the_checkout_when_started_as_a_script() -> None:
    import importlib
    import importlib.util
    import sys

    path = ROOT / "scripts" / "plug_and_play.py"
    spec = importlib.util.spec_from_file_location("plug_and_play_path_under_test", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    saved_path = list(sys.path)
    saved_modules = {
        name: sys.modules.pop(name)
        for name in list(sys.modules)
        if name == "aureon" or name.startswith("aureon.")
    }
    checkout = {str(module.ROOT), str(module.ROOT / "mcp"), ""}
    # An editable install (pip install -e .) adds a meta-path finder that maps
    # ``aureon`` to the checkout no matter what sys.path holds. Set it aside so
    # this still checks what a plain script start sees.
    saved_meta_path = list(sys.meta_path)
    try:
        sys.meta_path[:] = [
            finder for finder in saved_meta_path if not _is_editable_install_finder(finder)
        ]
        sys.path[:] = [str(module.ROOT / "scripts")] + [
            entry for entry in saved_path if entry not in checkout
        ]
        importlib.invalidate_caches()
        try:
            import aureon  # noqa: F401
        except ModuleNotFoundError:
            pass
        else:
            raise AssertionError("script-directory sys.path should not already import aureon")
        module.ensure_checkout_importable()
        assert sys.path[0] == str(module.ROOT)
        assert sys.path[1] == str(module.ROOT / "mcp")
        import aureon

        assert Path(aureon.__file__).resolve().parent == module.ROOT / "aureon"
    finally:
        sys.meta_path[:] = saved_meta_path
        sys.path[:] = saved_path
        importlib.invalidate_caches()
        for name in list(sys.modules):
            if name == "aureon" or name.startswith("aureon."):
                sys.modules.pop(name, None)
        sys.modules.update(saved_modules)


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


def _assignments(relative: str) -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    for line in _text(relative).splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        key = key.strip()
        value = value.split("#", 1)[0].strip().strip('"').strip("'")
        found.append((key, value))
    return found


def test_env_example_has_no_secret_values() -> None:
    """Charlie rule: placeholder names only. The root template keeps secrets blank."""

    root = _text(".env.example")
    assert "Charlie rule" in root
    assert "Guarded offline" in root
    assert "Read-only market fetch" in root
    assert "Live orders" in root
    assert "\nAUREON_LIVE_TRADING=" not in f"\n{root}"
    assert "AUREON_DISABLE_REAL_ORDERS=1" in root
    assert "AUREON_DISABLE_EXCHANGE_MUTATIONS=1" in root
    assert "AUREON_LLM_OFFLINE=1" in root
    assert "ALPACA_PAPER=true" in root
    assert "CAPITAL_DEMO=1" in root
    assert "CAPITAL_DEMO_MODE=true" in root
    assert "ALPACA_PAPER=false" not in root
    assert "CAPITAL_DEMO_MODE=false" not in root
    values = dict(_assignments(".env.example"))
    for name in (
        "BINANCE_API_KEY",
        "BINANCE_API_SECRET",
        "KRAKEN_API_KEY",
        "KRAKEN_API_SECRET",
        "ALPACA_API_KEY",
        "ALPACA_SECRET_KEY",
        "CAPITAL_API_KEY",
        "CAPITAL_PASSWORD",
    ):
        assert values[name] == ""
    for key, value in values.items():
        upper = key.upper()
        if upper.endswith(_SECRET_SUFFIXES):
            assert value == "", key
        assert _REAL_KEY.search(value) is None


def test_env_examples_use_placeholder_names_only() -> None:
    for relative in _ENV_EXAMPLES:
        text = _text(relative)
        assert _REAL_KEY.search(text) is None, relative
        for key, value in _assignments(relative):
            upper = key.upper()
            if not upper.endswith(_SECRET_SUFFIXES):
                continue
            assert value == "" or _PLACEHOLDER_VALUE.fullmatch(value), (relative, key, value)


def test_public_env_does_not_overclaim_master_locks() -> None:
    """Blank-key template values are not a lock on a full+keyed master boot.

    The master launcher reads a complete key group from the root ``.env``,
    the inherited shell, and ``aureon_radar/.env``. Exchange keys in ``.env``
    make that boot live, and that boot overrides the disable and dry-run flags.
    """

    required = (
        "Exchange keys in `.env` make that boot live",
        "inherited shell",
        "aureon_radar/.env",
        "not a lock",
        "full+keyed",
        "AUREON_DRY_RUN",
        "AUREON_DISABLE_REAL_ORDERS",
    )
    for relative in (
        ".env.example",
        "docs/PUBLIC_ENV.md",
        "PORTABILITY.md",
        "README.md",
        "SECURITY.md",
    ):
        text = _text(relative)
        for phrase in required:
            assert phrase in text, (relative, phrase)
        assert "Posture locks" not in text
        assert "leaves these locks in place" not in text
        assert "keep order execution off" not in text
        assert "Live orders stay disabled" not in text
        assert "ships live orders off" not in text
        assert "Blank keeps that boot" not in text
        assert "explicitly disabled" not in text
    readme = _text("README.md")
    assert "Live trading stays off" not in readme
    assert "release%20boundary-HOLD-orange" in readme
    assert "trading_mode=live (exchange keys present)" in readme
    radar = _text("aureon_radar/.env.example")
    assert "inherited shell" in radar
    assert "not a lock" in radar
    assert "Exchange keys in .env make that boot live" in radar


def test_lockfile_pins_the_direct_requirements() -> None:
    direct = _text("requirements-plug.txt")
    lock = _text("requirements-plug.lock")
    for line in direct.splitlines():
        if not line or line.startswith("#"):
            continue
        assert line in lock
    assert "mcp==1.30.0" in lock

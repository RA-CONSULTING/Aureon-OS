from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import textwrap


ROOT = Path(__file__).resolve().parents[1]


def test_audit_import_and_getters_are_operationally_inert(tmp_path: Path) -> None:
    state_path = tmp_path / "injected-portfolio-state.json"
    history_path = tmp_path / "injected-portfolio-history.json"
    log_path = tmp_path / "injected-trade.log"
    log_dir = tmp_path / "trade-output"

    script = textwrap.dedent(
        """
        import builtins
        import io
        import json
        import logging
        import os
        from pathlib import Path

        watched = {
            os.path.abspath(os.environ["AUREON_PORTFOLIO_STATE_PATH"]),
            os.path.abspath(os.environ["AUREON_PORTFOLIO_HISTORY_PATH"]),
            os.path.abspath(os.environ["AUREON_TRADE_LOG_PATH"]),
            os.path.abspath("real_portfolio_state.json"),
            os.path.abspath("thoughts.jsonl"),
            os.path.abspath("trade_logger.log"),
        }
        watched_dir = os.path.abspath(os.environ["AUREON_TRADE_LOG_DIR"])
        events = []
        original_open = builtins.open
        original_io_open = io.open
        original_replace = os.replace
        original_mkdir = os.mkdir

        def checked_path(value):
            try:
                return os.path.abspath(os.fspath(value))
            except TypeError:
                return ""

        def guard_open(file, mode="r", *args, **kwargs):
            path = checked_path(file)
            if path in watched:
                events.append(["open", path, str(mode)])
                raise AssertionError(f"operational file access during audit import: {path}")
            return original_open(file, mode, *args, **kwargs)

        def guard_io_open(file, mode="r", *args, **kwargs):
            path = checked_path(file)
            if path in watched:
                events.append(["io.open", path, str(mode)])
                raise AssertionError(f"operational file access during audit import: {path}")
            return original_io_open(file, mode, *args, **kwargs)

        def guard_replace(src, dst, *args, **kwargs):
            path = checked_path(dst)
            if path in watched:
                events.append(["replace", path, ""])
                raise AssertionError(f"operational replace during audit import: {path}")
            return original_replace(src, dst, *args, **kwargs)

        def guard_mkdir(path, *args, **kwargs):
            absolute = checked_path(path)
            if absolute == watched_dir or absolute.startswith(watched_dir + os.sep):
                events.append(["mkdir", absolute, ""])
                raise AssertionError(f"trade-log directory created during audit import: {absolute}")
            return original_mkdir(path, *args, **kwargs)

        builtins.open = guard_open
        io.open = guard_io_open
        os.replace = guard_replace
        os.mkdir = guard_mkdir

        from aureon.portfolio.aureon_real_portfolio_tracker import get_real_portfolio_tracker
        from aureon.portfolio.trade_logger import get_trade_logger, logger as trade_module_logger

        trade_logger = get_trade_logger()
        portfolio = get_real_portfolio_tracker()
        summary = portfolio.get_quick_summary()

        def contains_number(value):
            if isinstance(value, bool) or value is None:
                return False
            if isinstance(value, (int, float)):
                return True
            if isinstance(value, dict):
                return any(contains_number(item) for item in value.values())
            if isinstance(value, (list, tuple)):
                return any(contains_number(item) for item in value)
            return False

        result = {
            "events": events,
            "numeric_free": not contains_number(summary),
            "snapshot_is_none": portfolio.get_real_portfolio() is None,
            "clients_are_none": all(
                getattr(portfolio, name) is None
                for name in ("_alpaca_client", "_kraken_client", "_binance_client", "_capital_client")
            ),
            "trade_persistence_active": trade_logger._persistence_active,
            "file_handler_count": sum(
                isinstance(handler, logging.FileHandler)
                for handler in trade_module_logger.handlers
            ),
            "created_paths": [
                path for path in (
                    os.environ["AUREON_PORTFOLIO_STATE_PATH"],
                    os.environ["AUREON_PORTFOLIO_HISTORY_PATH"],
                    os.environ["AUREON_TRADE_LOG_PATH"],
                    os.environ["AUREON_TRADE_LOG_DIR"],
                    "real_portfolio_state.json",
                    "thoughts.jsonl",
                    "trade_logger.log",
                ) if Path(path).exists()
            ],
        }
        print(json.dumps(result, sort_keys=True))
        """
    )

    env = os.environ.copy()
    env.update(
        {
            "AUREON_AUDIT_MODE": "1",
            "AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS": "1",
            "AUREON_PORTFOLIO_STATE_PATH": str(state_path),
            "AUREON_PORTFOLIO_HISTORY_PATH": str(history_path),
            "AUREON_TRADE_LOG_PATH": str(log_path),
            "AUREON_TRADE_LOG_DIR": str(log_dir),
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONPATH": str(ROOT),
            "LIVE": "0",
            "DRY_RUN": "1",
            "KRAKEN_DRY_RUN": "true",
        }
    )
    for name in (
        "BINANCE_API_KEY",
        "BINANCE_API_SECRET",
        "KRAKEN_API_KEY",
        "KRAKEN_API_SECRET",
        "ALPACA_API_KEY",
        "ALPACA_SECRET_KEY",
        "CAPITAL_API_KEY",
        "CAPITAL_IDENTIFIER",
        "CAPITAL_PASSWORD",
    ):
        env[name] = ""

    completed = subprocess.run(
        [sys.executable, "-c", script],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    result = json.loads(completed.stdout.strip().splitlines()[-1])
    assert result["events"] == []
    assert result["numeric_free"] is True
    assert result["snapshot_is_none"] is True
    assert result["clients_are_none"] is True
    assert result["trade_persistence_active"] is False
    assert result["file_handler_count"] == 0
    assert result["created_paths"] == []

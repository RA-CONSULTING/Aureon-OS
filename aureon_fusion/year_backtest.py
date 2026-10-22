#!/usr/bin/env python3
"""Aureon 1-year backtest CLI.

Subcommands:
  fetch  — download ~1 year of hourly BTC/USD OHLCV (Coinbase preferred,
           Binance public klines fallback) to aureon_fusion/state/backtest/btcusd_1h.json.
  run    — replay the saved bars bar-by-bar through the Aureon subsystem pipeline
           and the shadow_executor simulation.
  report — render backtest_report.html and backtest_summary.json.

This is a paper/backtest harness. No live orders are placed.
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

# Ensure workspace on path for local imports.
WORKSPACE = Path(__file__).resolve().parents[1]
if str(WORKSPACE) not in sys.path:
    sys.path.insert(0, str(WORKSPACE))

from aureon_fusion.backtest_engine import BacktestEngine, DataFetcher  # noqa: E402

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("year_backtest")


def cmd_fetch(args: argparse.Namespace) -> int:
    try:
        fetcher = DataFetcher()
        candles = fetcher.fetch(min_days=180)
        print(f"[fetch] source={fetcher.source} candles={len(candles)}")
        if len(candles) < 365 * 24:
            print("[fetch] NOTE: less than one full year downloaded; "
                  "backtest will run over the available history.")
        return 0
    except Exception as exc:
        logger.exception("fetch failed")
        print(f"[fetch] ERROR: {exc}")
        return 1


def cmd_run(args: argparse.Namespace) -> int:
    try:
        engine = BacktestEngine()
        result = engine.run(resume=args.resume)
        print(f"[run] bars={result['bars']} final_balance={result['final_balance']:.2f} "
              f"max_drawdown={result['max_drawdown']*100:.2f}%")
        return 0
    except Exception as exc:
        logger.exception("run failed")
        print(f"[run] ERROR: {exc}")
        return 1


def cmd_report(args: argparse.Namespace) -> int:
    try:
        engine = BacktestEngine()
        summary = engine.report()
        print(f"[report] final_equity={summary['final_equity']:.2f} "
              f"total_pnl={summary['total_pnl']:.2f} "
              f"return={summary['total_return_pct']:.2f}% "
              f"trades={summary['total_closed_trades']} "
              f"sharpe={summary['sharpe_like_annualized']:.2f}")
        return 0
    except Exception as exc:
        logger.exception("report failed")
        print(f"[report] ERROR: {exc}")
        return 1


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Aureon 1-year backtest harness (paper simulation).")
    sub = parser.add_subparsers(dest="command", required=True)

    fetch_p = sub.add_parser("fetch", help="Download historical BTC/USD hourly bars.")
    fetch_p.set_defaults(func=cmd_fetch)

    run_p = sub.add_parser("run", help="Run the bar-by-bar backtest simulation.")
    run_p.add_argument("--resume", action="store_true",
                       help="Resume from last saved bar index.")
    run_p.set_defaults(func=cmd_run)

    report_p = sub.add_parser("report", help="Generate HTML/JSON backtest report.")
    report_p.set_defaults(func=cmd_report)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Verify the trading launcher's CLI contract without starting an engine."""

from aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
from pathlib import Path

from aureon.trading.micro_profit_labyrinth_cli import build_parser

def _duration_option_is_available():
    """Check parser options and prove the production entry point uses it."""

    args = build_parser().parse_args(["--dry-run", "--duration", "7"])
    launcher = Path(__file__).resolve().parents[1] / "aureon" / "trading" / "micro_profit_labyrinth.py"
    source = launcher.read_text(encoding="utf-8")
    return (
        args.dry_run is True
        and args.duration == 7
        and "from aureon.trading.micro_profit_labyrinth_cli import build_parser" in source
        and "parser = build_parser()" in source
    )

def test_command():
    assert _duration_option_is_available()


if __name__ == "__main__":
    print("🔍 Testing trading engine duration CLI parameter...")
    success = _duration_option_is_available()
    if success:
        print("\n✅ The launcher exposes the --duration parameter.")
    else:
        print("\n❌ There's still an issue. Check the error output above.")

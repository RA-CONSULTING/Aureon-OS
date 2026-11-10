"""Lightweight, side-effect-free command-line contract for the labyrinth."""

from __future__ import annotations

import argparse


def build_parser() -> argparse.ArgumentParser:
    """Build the command parser without importing or starting the engine."""

    parser = argparse.ArgumentParser(
        description="Micro Profit Labyrinth - ALPACA-FOCUSED Trading System"
    )
    parser.add_argument("--live", action="store_true", help="Run in LIVE mode")
    parser.add_argument("--dry-run", action="store_true", help="Explicit simulation mode (legacy flag)")
    parser.add_argument("--duration", type=int, default=0, help="Duration in seconds (0 = forever)")
    parser.add_argument("--yes", "-y", action="store_true", help="Auto-confirm live mode (skip MICRO prompt)")
    parser.add_argument("--turn-based", action="store_true", help="Turn-Based Mode: scan exchanges sequentially")
    parser.add_argument("--fptp", action="store_true", help="Deprecated alias for default mode")
    parser.add_argument("--winners-only", "-w", action="store_true", help="Show only successful trades")
    parser.add_argument("--no-chain-sniper", action="store_true", help="Disable multi-hop chain sniper")
    parser.add_argument("--max-hops", type=int, default=25, help="Max hops for chain sniper (default: 25)")
    parser.add_argument("--snowball", action="store_true", help="One trade at a time with strict profit tracking")
    parser.add_argument("--multi-exchange", action="store_true", help="Enable multi-exchange mode")
    parser.add_argument("--sync-cia", action="store_true", help="Sync CIA declassified intelligence")
    parser.add_argument("--cia-report", action="store_true", help="Show CIA intelligence report")
    parser.add_argument("--cia-wisdom", action="store_true", help="Show Queen's trading wisdom from CIA intel")
    return parser

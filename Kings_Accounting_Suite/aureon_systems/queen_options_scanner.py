#!/usr/bin/env python3
"""Legacy import bridge for the receipt-gated Queen options scanner.

The Kings Accounting Suite historically carried an independent copy of the
scanner. Keeping two execution implementations allowed the legacy copy to
construct providers, infer missing observations, and drift away from the
canonical evidence contract. This module now exposes the canonical analytical
types only. Import and default construction are inert; callers must inject
adapters, a clock, and complete linked provider receipts.
"""

from typing import Optional, Sequence

from aureon.queen.queen_options_scanner import (
    OptionContract,
    OptionQuote,
    OptionsOpportunity,
    OptionType,
    QueenOptionsScanner,
    TradingLevel,
    scan_options,
)
from aureon.queen.queen_options_scanner import main as _canonical_main

__all__ = [
    "OptionContract",
    "OptionQuote",
    "OptionsOpportunity",
    "OptionType",
    "QueenOptionsScanner",
    "TradingLevel",
    "main",
    "scan_options",
]


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Describe the injection boundary without creating clients or fetching."""
    return _canonical_main(argv)


if __name__ == "__main__":
    raise SystemExit(main())

"""
Run all whale subsystem components (orderbook analyzer, pattern mapper, predictor).

Usage:
    python aureon_whale_agent.py BTC/USD ETH/USD --interval 1.0
"""
from __future__ import annotations
from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)

import argparse
import logging
import time
from typing import List

from aureon.analytics.aureon_whale_orderbook_analyzer import WhaleOrderbookAnalyzer
from aureon.analytics.aureon_whale_pattern_mapper import default_mapper
from aureon.analytics.aureon_whale_behavior_predictor import default_predictor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main(symbols: List[str], interval: float = 1.0):
    # Create analyzer (uses Alpaca client by default)
    analyzer = WhaleOrderbookAnalyzer(poll_symbols=symbols, poll_interval=interval)
    try:
        analyzer.start()
        logger.info('Whale agent running. Press Ctrl-C to stop')
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info('Stopping whale agent...')
        analyzer.stop()


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('symbols', nargs='+', help='Symbols to monitor (e.g., BTC/USD)')
    ap.add_argument('--interval', type=float, default=1.0, help='Polling interval (s)')
    args = ap.parse_args()
    main(args.symbols, args.interval)

"""
market_data_refresher.py — Autonomous market data ingestion thread.

Keeps market_bars table fresh so Aureon always has market vision.
Runs at boot (catch-up) then every REFRESH_INTERVAL_S thereafter.
Never blocks the cognitive tick. Purely additive — only INSERTs.
"""
from __future__ import annotations

import logging
import os
import sys
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

logger = logging.getLogger("aureon.data_feeds.market_data_refresher")

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

# Import-time credential loading is forbidden. Explicitly released callers
# must inject only the exact provider credentials they need.

REFRESH_INTERVAL_S = 7200  # 2 hours

COINAPI_PAIRS   = ["BTC/USD", "ETH/USD"]
COINAPI_PERIOD  = "5MIN"
COINAPI_EXCHANGES = {"BINANCE", "BITSTAMP", "KRAKEN", "COINBASE"}

ALPACA_SYMBOLS  = [
    "AAPL", "MSFT", "TSLA", "SPY", "NVDA", "AMZN",
    "GOOGL", "META", "AMD", "QQQ", "IWM", "GLD",
    "NFLX", "JPM", "BAC", "XLF", "XLE", "DIA",
    "COIN", "MSTR",
]
ALPACA_TIMEFRAME = "5Min"
ALPACA_FEED     = "iex"

# How far back to look on each refresh (slightly more than the interval)
LOOKBACK_HOURS  = 3


def _now_utc() -> datetime:
    return datetime.now(tz=timezone.utc)


def _run_coinapi(conn, start_dt: datetime, end_dt: datetime) -> None:
    try:
        from scripts.python.ingest_market_history import ingest_coinapi  # type: ignore
    except Exception:
        sys.path.insert(0, str(_REPO_ROOT / "scripts" / "python"))
        try:
            from ingest_market_history import ingest_coinapi  # type: ignore
        except Exception as e:
            logger.warning("market_data_refresher: cannot import ingest_coinapi: %s", e)
            return

    api_key = os.getenv("COINAPI_KEY", "") or os.getenv("COINAPI_API_KEY", "")
    if not api_key:
        logger.warning("market_data_refresher: COINAPI_KEY not set, skipping crypto bars")
        return

    try:
        ingest_coinapi(
            conn=conn,
            start_dt=start_dt,
            end_dt=end_dt,
            pairs=COINAPI_PAIRS,
            period_id=COINAPI_PERIOD,
            exchange_allowlist=COINAPI_EXCHANGES,
            max_symbols_per_pair=6,
            include_trades=False,
            no_resume=False,
        )
    except Exception as e:
        logger.error("market_data_refresher: CoinAPI ingest error: %s", e)


def _run_alpaca(conn, start_dt: datetime, end_dt: datetime) -> None:
    try:
        from scripts.python.ingest_market_history import ingest_alpaca_stocks  # type: ignore
    except Exception:
        sys.path.insert(0, str(_REPO_ROOT / "scripts" / "python"))
        try:
            from ingest_market_history import ingest_alpaca_stocks  # type: ignore
        except Exception as e:
            logger.warning("market_data_refresher: cannot import ingest_alpaca_stocks: %s", e)
            return

    alpaca_key    = os.getenv("ALPACA_API_KEY", "") or os.getenv("ALPACA_KEY", "")
    alpaca_secret = os.getenv("ALPACA_SECRET_KEY", "") or os.getenv("ALPACA_SECRET", "")
    if not alpaca_key or not alpaca_secret:
        logger.warning("market_data_refresher: Alpaca keys not set, skipping stock bars")
        return

    try:
        ingest_alpaca_stocks(
            conn=conn,
            start_dt=start_dt,
            end_dt=end_dt,
            symbols=ALPACA_SYMBOLS,
            timeframe=ALPACA_TIMEFRAME,
            feed=ALPACA_FEED,
        )
    except Exception as e:
        logger.error("market_data_refresher: Alpaca ingest error: %s", e)


def _refresh_cycle(lookback_hours: float = LOOKBACK_HOURS) -> None:
    try:
        from aureon.core import aureon_global_history_db as ghdb  # type: ignore
        conn = ghdb.connect(None)
    except Exception as e:
        logger.error("market_data_refresher: cannot open DB: %s", e)
        return

    end_dt   = _now_utc()
    start_dt = end_dt - timedelta(hours=lookback_hours)

    logger.info("market_data_refresher: refreshing %s → %s", start_dt.isoformat(), end_dt.isoformat())
    t0 = time.time()

    _run_coinapi(conn, start_dt, end_dt)
    _run_alpaca(conn, start_dt, end_dt)

    try:
        conn.close()
    except Exception:
        pass

    elapsed = time.time() - t0
    logger.info("market_data_refresher: refresh done in %.1fs", elapsed)


class MarketDataRefresher(threading.Thread):
    """Background thread — catches up market bars at boot, then refreshes every 2h."""

    def __init__(self, interval_s: float = REFRESH_INTERVAL_S):
        super().__init__(daemon=True, name="aureon-market-refresher")
        self.interval_s = interval_s
        self._stop = threading.Event()

    def stop(self) -> None:
        self._stop.set()

    def run(self) -> None:
        # Boot catch-up: look back 72h to fill any gap since last run
        try:
            _refresh_cycle(lookback_hours=72)
        except Exception as e:
            logger.error("market_data_refresher: boot catch-up failed: %s", e)

        while not self._stop.is_set():
            self._stop.wait(self.interval_s)
            if self._stop.is_set():
                break
            try:
                _refresh_cycle(lookback_hours=LOOKBACK_HOURS)
            except Exception as e:
                logger.error("market_data_refresher: periodic refresh failed: %s", e)


_refresher: MarketDataRefresher | None = None


def start_refresher(interval_s: float = REFRESH_INTERVAL_S) -> MarketDataRefresher:
    global _refresher
    if _refresher is not None and _refresher.is_alive():
        return _refresher
    _refresher = MarketDataRefresher(interval_s=interval_s)
    _refresher.start()
    logger.info("market_data_refresher: started (interval=%ds)", int(interval_s))
    return _refresher


def stop_refresher() -> None:
    global _refresher
    if _refresher:
        _refresher.stop()

#!/usr/bin/env python3
"""Aureon Queen live runner backed only by fresh provider observations.

This compatibility runner publishes Binance public-market observations to the
local ThoughtBus. It does not create scanner, whale, bot, balance, or trading
values when those providers are absent. Those states are emitted as ``no_data``
with a reason so downstream systems cannot mistake absence for a measurement.
"""

import argparse
import json
import logging
import os
import threading
import time
import urllib.parse
import urllib.request
import uuid
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Dict, Iterable

from aureon.core.aureon_baton_link import link_system as _baton_link

_baton_link(__name__)


logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(message)s")
logger = logging.getLogger(__name__)


def _resolve_thoughts_file() -> Path:
    """Return the shared runner/dashboard stream, with an explicit test override."""
    override = os.getenv("AUREON_THOUGHTS_FILE", "").strip()
    return Path(override) if override else Path(__file__).resolve().parents[2] / "thoughts.jsonl"


THOUGHTS_FILE = _resolve_thoughts_file()
BINANCE_API_BASE = "https://api.binance.com"
BINANCE_SOURCE_ID = "binance_public_market"
FRESHNESS_TTL_SECONDS = 120


def _iso_utc(timestamp_seconds: float) -> str:
    return datetime.fromtimestamp(timestamp_seconds, tz=UTC).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True)
class MarketObservation:
    symbol: str
    provider_symbol: str
    price: float
    bid: float
    ask: float
    base_volume_24h: float
    quote_volume_24h: float
    change_percent_24h: float
    provider_timestamp: float
    collected_at: float
    source_id: str
    source_url: str
    source_event_id: str
    freshness_ttl_sec: int
    truth_status: str = "live"
    generated: bool = False


class SimpleThoughtBus:
    """Local append-only transport used only when the canonical bus is absent."""

    def __init__(self, thoughts_file: Path = THOUGHTS_FILE):
        self.thoughts_file = thoughts_file

    def think(self, content: str = "", topic: str = "", source: str = "", **kwargs: Any) -> None:
        message = kwargs.get("message", content)
        payload = kwargs.get("payload")
        if payload is None:
            try:
                payload = json.loads(message) if isinstance(message, str) else message
            except json.JSONDecodeError:
                payload = {"message": message}
        envelope = {
            "id": str(uuid.uuid4()),
            "ts": time.time(),
            "source": source or "queen_live_runner",
            "topic": topic,
            "payload": payload,
            "trace_id": str(uuid.uuid4()),
        }
        self.thoughts_file.parent.mkdir(parents=True, exist_ok=True)
        with self.thoughts_file.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(envelope, default=str) + "\n")


_thought_bus: Any | None = None


def get_thought_bus() -> Any:
    global _thought_bus
    if _thought_bus is not None:
        return _thought_bus
    try:
        from aureon.core.aureon_thought_bus import get_thought_bus as canonical_bus

        _thought_bus = canonical_bus()
    except (ImportError, RuntimeError):
        _thought_bus = SimpleThoughtBus()
    return _thought_bus


def emit_telemetry(topic: str, payload: Dict[str, Any], source: str = "queen_live") -> None:
    """Publish one truth-labelled payload without changing its provider time."""
    get_thought_bus().think(
        message=json.dumps(payload, default=str),
        payload=payload,
        topic=topic,
        source=source,
    )


class BinancePublicMarketFeed:
    """Read exact 24-hour ticker observations from Binance's public API."""

    SYMBOLS = {
        "BTC/USD": "BTCUSDT",
        "ETH/USD": "ETHUSDT",
        "SOL/USD": "SOLUSDT",
        "XRP/USD": "XRPUSDT",
        "ADA/USD": "ADAUSDT",
        "DOGE/USD": "DOGEUSDT",
    }

    def __init__(self, timeout_seconds: float = 10.0):
        self.timeout_seconds = timeout_seconds

    def fetch(self) -> Dict[str, MarketObservation]:
        provider_symbols = list(self.SYMBOLS.values())
        query = urllib.parse.urlencode({"symbols": json.dumps(provider_symbols, separators=(",", ":"))})
        source_url = f"{BINANCE_API_BASE}/api/v3/ticker/24hr?{query}"
        request = urllib.request.Request(source_url, headers={"User-Agent": "Aureon-OS/real-data-contract"})
        collected_at = time.time()
        with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
            if response.status != 200:
                raise RuntimeError(f"BINANCE_HTTP_{response.status}")
            rows = json.loads(response.read().decode("utf-8"))

        if not isinstance(rows, list):
            raise RuntimeError("BINANCE_TICKER_RESPONSE_INVALID")

        reverse_symbols = {provider: display for display, provider in self.SYMBOLS.items()}
        observations: Dict[str, MarketObservation] = {}
        for row in rows:
            provider_symbol = str(row.get("symbol") or "")
            symbol = reverse_symbols.get(provider_symbol)
            if not symbol:
                continue
            provider_timestamp = float(row["closeTime"]) / 1000.0
            age = collected_at - provider_timestamp
            if age < -30 or age > FRESHNESS_TTL_SECONDS:
                raise RuntimeError(f"BINANCE_TICKER_STALE:{provider_symbol}:{age:.1f}s")
            observation = MarketObservation(
                symbol=symbol,
                provider_symbol=provider_symbol,
                price=float(row["lastPrice"]),
                bid=float(row["bidPrice"]),
                ask=float(row["askPrice"]),
                base_volume_24h=float(row["volume"]),
                quote_volume_24h=float(row["quoteVolume"]),
                change_percent_24h=float(row["priceChangePercent"]),
                provider_timestamp=provider_timestamp,
                collected_at=collected_at,
                source_id=BINANCE_SOURCE_ID,
                source_url=source_url,
                source_event_id=f"{provider_symbol}:{int(row['closeTime'])}",
                freshness_ttl_sec=FRESHNESS_TTL_SECONDS,
            )
            if min(observation.price, observation.bid, observation.ask) <= 0:
                raise RuntimeError(f"BINANCE_TICKER_NONPOSITIVE:{provider_symbol}")
            observations[symbol] = observation

        missing = sorted(set(self.SYMBOLS) - set(observations))
        if missing:
            raise RuntimeError(f"BINANCE_TICKERS_MISSING:{','.join(missing)}")
        return observations


class QueenLiveRunner:
    """Continuously publish live market envelopes and explicit data gaps."""

    def __init__(self, interval: float = 2.0, feed: BinancePublicMarketFeed | None = None):
        if interval <= 0:
            raise ValueError("interval must be positive")
        self.interval = interval
        self.feed = feed or BinancePublicMarketFeed()
        self.running = False
        self.cycle_count = 0
        self.start_time: float | None = None

    @staticmethod
    def _unavailable_surfaces() -> Iterable[tuple[str, str]]:
        return (
            ("scanner.status", "NO_FRESH_SCANNER_PROVIDER_OBSERVATION"),
            ("whale.status", "NO_FRESH_WHALE_PROVIDER_OBSERVATION"),
            ("bot.status", "NO_FRESH_BOT_PROVIDER_OBSERVATION"),
            ("queen.decision", "NO_EVIDENCE_BACKED_DECISION"),
        )

    def run_cycle(self) -> Dict[str, Any]:
        self.cycle_count += 1
        collected_at = time.time()
        try:
            observations = self.feed.fetch()
        except Exception as exc:
            payload = {
                "truth_status": "no_data",
                "generated": False,
                "reason": f"MARKET_PROVIDER_UNAVAILABLE:{type(exc).__name__}:{exc}",
                "collected_at": collected_at,
                "freshness_ttl_sec": FRESHNESS_TTL_SECONDS,
            }
            emit_telemetry("market.status", payload, source="binance_public_market")
            return payload

        for observation in observations.values():
            payload = asdict(observation)
            payload["provider_timestamp_iso"] = _iso_utc(observation.provider_timestamp)
            payload["collected_at_iso"] = _iso_utc(observation.collected_at)
            emit_telemetry("market.price", payload, source=observation.source_id)

        for topic, reason in self._unavailable_surfaces():
            emit_telemetry(
                topic,
                {
                    "truth_status": "no_data",
                    "generated": False,
                    "reason": reason,
                    "collected_at": collected_at,
                },
                source="queen_live_runner",
            )

        heartbeat = {
            "truth_status": "real_derived",
            "generated": False,
            "cycle": self.cycle_count,
            "market_observation_count": len(observations),
            "source_ids": sorted({item.source_id for item in observations.values()}),
            "source_event_ids": sorted(item.source_event_id for item in observations.values()),
            "source_timestamp": min(item.provider_timestamp for item in observations.values()),
            "collected_at": collected_at,
            "freshness_ttl_sec": FRESHNESS_TTL_SECONDS,
        }
        emit_telemetry("system.heartbeat", heartbeat, source="queen_live_runner")
        return heartbeat

    def start(self) -> None:
        self.running = True
        self.start_time = time.time()
        logger.info("Queen live runner started with Binance provider observations only")
        try:
            while self.running:
                result = self.run_cycle()
                logger.info(
                    "cycle=%s truth_status=%s observations=%s",
                    self.cycle_count,
                    result.get("truth_status"),
                    result.get("market_observation_count"),
                )
                time.sleep(self.interval)
        except KeyboardInterrupt:
            self.stop()

    def stop(self) -> None:
        self.running = False
        emit_telemetry(
            "system.shutdown",
            {
                "truth_status": "real_derived",
                "generated": False,
                "cycles_completed": self.cycle_count,
                "collected_at": time.time(),
            },
            source="queen_live_runner",
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Aureon Queen live provider runner")
    parser.add_argument("--interval", type=float, default=2.0)
    parser.add_argument("--daemon", action="store_true")
    args = parser.parse_args()
    runner = QueenLiveRunner(interval=args.interval)
    if args.daemon:
        thread = threading.Thread(target=runner.start, daemon=True)
        thread.start()
        return
    runner.start()


if __name__ == "__main__":
    main()

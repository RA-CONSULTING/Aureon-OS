#!/usr/bin/env python3
"""
🌐🧠 AUREON REAL DATA FEED HUB 🧠🌐
====================================
CENTRAL HUB FOR DISTRIBUTING REAL INTELLIGENCE TO ALL SYSTEMS

This module:
1. Gathers real intelligence from aureon_real_intelligence_engine
2. Publishes to ThoughtBus with standardized topics
3. All 200+ systems can subscribe to get real data

Topics Published:
- intelligence.bot.*       - Bot detection & firm profiling
- intelligence.whale.*     - Validated whale predictions
- intelligence.momentum.*  - Momentum scanner opportunities
- intelligence.validated.* - Combined validated intelligence
- intelligence.summary     - Periodic summary of all intelligence

Gary Leckey & Tina Brown | January 2026 | REAL DATA DISTRIBUTION
"""

import time
import logging
import threading
import hashlib
import math
from datetime import datetime, timezone
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable, Mapping, Tuple

logger = logging.getLogger(__name__)

# Sacred constants
PHI = 1.618033988749895
SCHUMANN = 7.83
DEFAULT_MAX_AGE_SECONDS = 120.0
MAX_FUTURE_SKEW_SECONDS = 30.0


def _no_data(reason: str, **context: Any) -> Dict[str, Any]:
    """Return a numeric-free, non-operational absence envelope."""
    payload: Dict[str, Any] = {
        "data_status": "no_data",
        "truth_status": "no_data",
        "reason": str(reason),
        "source_id": None,
        "source_timestamp": None,
        "received_at": None,
        "receipt_id": None,
        "freshness_status": "no_data",
        "provider_observation": False,
        "input_provider_observation": False,
        "generated_values": False,
        "operational_eligible": False,
        "actionable": False,
        "accounting_eligible": False,
        "learning_eligible": False,
        "eligible_for_action": False,
        "eligible_for_accounting": False,
        "eligible_for_learning": False,
    }
    payload.update({
        key: value
        for key, value in context.items()
        if value is not None and not _contains_numeric(value)
    })
    return payload


def _finite_number(value: Any, *, minimum: Optional[float] = None,
                   maximum: Optional[float] = None) -> Optional[float]:
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    if not math.isfinite(number):
        return None
    if minimum is not None and number < minimum:
        return None
    if maximum is not None and number > maximum:
        return None
    return number


def _timestamp_seconds(value: Any) -> Optional[float]:
    number = _finite_number(value)
    if number is not None:
        if number > 10_000_000_000:
            number /= 1000.0
        return number if number > 0 else None
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.timestamp()
    except (TypeError, ValueError, OverflowError):
        return None


def _fresh_timestamp(value: Any, *, now: float,
                     max_age_seconds: float) -> Optional[float]:
    timestamp = _timestamp_seconds(value)
    if timestamp is None:
        return None
    age = now - timestamp
    if age < -MAX_FUTURE_SKEW_SECONDS or age > max_age_seconds:
        return None
    return timestamp


def _identifier(value: Any) -> Optional[str]:
    if not isinstance(value, str):
        return None
    identifier = value.strip()
    return identifier if identifier else None


def _contains_numeric(value: Any) -> bool:
    if isinstance(value, bool) or value is None:
        return False
    if isinstance(value, (int, float, complex)):
        return True
    if isinstance(value, Mapping):
        return any(_contains_numeric(item) for item in value.values())
    if isinstance(value, (list, tuple, set)):
        return any(_contains_numeric(item) for item in value)
    return False


def _complete_live_record(record: Any, *, now: float,
                          max_age_seconds: float) -> bool:
    if not isinstance(record, Mapping):
        return False
    if record.get("data_status") != "live":
        return False
    if record.get("truth_status") not in {"real_observed", "real_derived"}:
        return False
    if record.get("generated_values") is not False:
        return False
    if _identifier(record.get("source_id")) is None:
        return False
    if _identifier(record.get("receipt_id")) is None:
        return False
    source_timestamp = _fresh_timestamp(
        record.get("source_timestamp"), now=now,
        max_age_seconds=max_age_seconds,
    )
    received_at = _fresh_timestamp(
        record.get("received_at"), now=now,
        max_age_seconds=max_age_seconds,
    )
    if source_timestamp is None or received_at is None:
        return False
    if source_timestamp > received_at + MAX_FUTURE_SKEW_SECONDS:
        return False
    return True


def _complete_no_data(record: Any) -> bool:
    return bool(
        isinstance(record, Mapping)
        and record.get("data_status") == "no_data"
        and record.get("truth_status") == "no_data"
        and record.get("generated_values") is False
        and record.get("operational_eligible") is False
        and record.get("actionable") is False
        and record.get("accounting_eligible") is False
        and record.get("learning_eligible") is False
        and not _contains_numeric(record)
    )


# ═══════════════════════════════════════════════════════════════════════════════
# DATA CLASSES FOR FEED EVENTS
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class ConsolidatedFeedStream:
    """One of five core consolidated feed streams"""
    stream_type: str  # market_data, intelligence, risk_metrics, execution_status, system_health
    last_update: Optional[float] = None
    is_healthy: bool = False
    event_count: int = 0
    latest_events: List[Dict] = field(default_factory=list)  # Last 20 events

    def add_event(self, event: Dict) -> None:
        """Add an already validated event without inventing a timestamp."""
        self.latest_events.append(dict(event))
        self.event_count += 1
        self.last_update = _timestamp_seconds(event.get("received_at"))
        self.is_healthy = True

        # Keep only last 20 events
        if len(self.latest_events) > 20:
            self.latest_events.pop(0)

    def get_status(self) -> Dict:
        """Get stream status"""
        if not self.latest_events:
            return _no_data(
                "no_complete_fresh_stream_events",
                stream_type=self.stream_type,
                latest_events=[],
            )
        latest = self.latest_events[-1]
        return {
            "stream_type": self.stream_type,
            "is_healthy": self.is_healthy,
            "event_count": self.event_count,
            "last_update": self.last_update,
            "latest_events": self.latest_events[-5:],
            "data_status": "live",
            "truth_status": "real_derived",
            "source_id": f"aureon.real_data_feed_hub:stream:{self.stream_type}",
            "source_timestamp": latest["source_timestamp"],
            "received_at": latest["received_at"],
            "receipt_id": (
                f"aureon.real_data_feed_hub:stream:{self.stream_type}:"
                f"{latest['receipt_id']}"
            ),
            "freshness_status": "fresh",
            "input_receipt_ids": [
                event["receipt_id"] for event in self.latest_events[-5:]
            ],
            "provider_observation": False,
            "input_provider_observation": True,
            "generated_values": False,
            "operational_eligible": False,
            "actionable": False,
            "accounting_eligible": False,
            "learning_eligible": False,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# REAL DATA FEED HUB
# ═══════════════════════════════════════════════════════════════════════════════

class RealDataFeedHub:
    """
    🌐 CENTRAL HUB FOR REAL INTELLIGENCE DISTRIBUTION
    
    Collects data from:
    - aureon_real_intelligence_engine (bot profiler, whale predictor, momentum scanners)
    - Market data feeds
    - ThoughtBus history
    
    Distributes to all systems via ThoughtBus topics.
    """
    
    def __init__(
        self,
        *,
        thought_bus: Any = None,
        intelligence_engine: Any = None,
        clock: Callable[[], float] = time.time,
        max_age_seconds: float = DEFAULT_MAX_AGE_SECONDS,
    ):
        """Create an inert hub around explicitly supplied dependencies."""
        self.thought_bus = thought_bus
        self.intelligence_engine = intelligence_engine
        self._clock = clock
        parsed_max_age = _finite_number(max_age_seconds, minimum=0.001)
        self.max_age_seconds = (
            parsed_max_age
            if parsed_max_age is not None
            else DEFAULT_MAX_AGE_SECONDS
        )
        self.running = False
        self.feed_thread = None
        self.last_no_data = _no_data("no_complete_feed_evidence_received")

        # Statistics
        self.bots_distributed = 0
        self.whales_distributed = 0
        self.momentum_distributed = 0
        self.intel_distributed = 0

        # Subscribers (direct callbacks in addition to ThoughtBus)
        self._subscribers: Dict[str, List[Callable]] = {}

        # Five core consolidated feed streams
        self.consolidated_streams: Dict[str, ConsolidatedFeedStream] = {
            "market_data": ConsolidatedFeedStream("market_data"),
            "intelligence": ConsolidatedFeedStream("intelligence"),
            "risk_metrics": ConsolidatedFeedStream("risk_metrics"),
            "execution_status": ConsolidatedFeedStream("execution_status"),
            "system_health": ConsolidatedFeedStream("system_health")
        }

    
    def configure(
        self,
        *,
        thought_bus: Any = None,
        intelligence_engine: Any = None,
    ) -> None:
        """Explicitly wire already-constructed dependencies."""
        if thought_bus is not None:
            self.thought_bus = thought_bus
        if intelligence_engine is not None:
            self.intelligence_engine = intelligence_engine

    def subscribe(self, topic: str, callback: Callable):
        """Subscribe to a specific feed topic (direct callback)"""
        if topic not in self._subscribers:
            self._subscribers[topic] = []
        self._subscribers[topic].append(callback)
        logger.debug(f"📡 Subscribed to {topic}")
    
    def _publish_to_bus(self, topic: str, data: Dict) -> bool:
        """Publish only complete fresh records or numeric-free no-data."""
        now = self._clock()
        complete_live = (
            _complete_live_record(
                data, now=now, max_age_seconds=self.max_age_seconds
            )
            and data.get("freshness_status") == "fresh"
            and data.get("generated_values") is False
            and data.get("operational_eligible") is False
            and data.get("actionable") is False
            and data.get("accounting_eligible") is False
            and data.get("learning_eligible") is False
        )
        if not complete_live and not _complete_no_data(data):
            self.last_no_data = _no_data(
                "publish_rejected_incomplete_or_stale_record",
                topic=str(topic),
            )
            return False
        if self.thought_bus:
            try:
                self.thought_bus.publish(topic, dict(data))
            except Exception as e:
                logger.debug(f"Bus publish error: {e}")
        
        # Also notify direct subscribers
        for pattern, handlers in self._subscribers.items():
            if self._topic_matches(topic, pattern):
                for handler in handlers:
                    try:
                        handler(topic, data)
                    except Exception as e:
                        logger.debug(f"Subscriber error: {e}")
        return True
    
    def _topic_matches(self, topic: str, pattern: str) -> bool:
        """Check if topic matches pattern (supports * wildcard)"""
        if pattern == "*":
            return True
        if pattern.endswith("*"):
            return topic.startswith(pattern[:-1])
        return topic == pattern

    def _record_no_data(self, reason: str, **context: Any) -> Dict[str, Any]:
        self.last_no_data = _no_data(reason, **context)
        return dict(self.last_no_data)

    def _validate_price_receipts(
        self,
        prices: Any,
        *,
        now: float,
    ) -> Tuple[Dict[str, float], Dict[str, str]]:
        numeric_prices: Dict[str, float] = {}
        receipt_ids: Dict[str, str] = {}
        if not isinstance(prices, Mapping):
            self._record_no_data("complete_provider_price_receipts_required")
            return numeric_prices, receipt_ids

        for declared_symbol, observation in prices.items():
            if not _complete_live_record(
                observation, now=now,
                max_age_seconds=self.max_age_seconds,
            ):
                continue
            if (
                observation.get("truth_status") != "real_observed"
                or observation.get("provider_observation") is not True
                or observation.get("generated_values") is not False
                or observation.get("operational_eligible") is not True
            ):
                continue
            symbol = _identifier(observation.get("symbol"))
            if symbol is None or symbol != declared_symbol:
                continue
            parts = symbol.split("/")
            if len(parts) != 2 or not all(parts):
                continue
            base_asset, quote_asset = parts
            if (
                observation.get("base_asset") != base_asset
                or observation.get("quote_asset") != quote_asset
                or observation.get("price_currency") != quote_asset
            ):
                continue
            price = _finite_number(observation.get("price"), minimum=0.000000000001)
            if price is None:
                continue
            numeric_prices[symbol] = price
            receipt_ids[symbol] = str(observation["receipt_id"])

        if not numeric_prices:
            self._record_no_data(
                "no_complete_fresh_provider_price_receipts"
            )
        return numeric_prices, receipt_ids

    def _valid_intelligence_input(
        self,
        record: Any,
        *,
        now: float,
        price_receipt_ids: Dict[str, str],
    ) -> bool:
        if not _complete_live_record(
            record, now=now, max_age_seconds=self.max_age_seconds
        ):
            return False
        if (
            record.get("generated_values") is not False
            or record.get("input_provider_observation") is not True
            or record.get("operational_eligible") is not True
        ):
            return False
        symbol = _identifier(record.get("symbol"))
        if symbol is None or symbol not in price_receipt_ids:
            return False
        input_receipt_ids = record.get("input_receipt_ids")
        if not isinstance(input_receipt_ids, list):
            return False
        valid_ids = {
            item for item in input_receipt_ids
            if _identifier(item) is not None
        }
        return price_receipt_ids[symbol] in valid_ids

    def _derived_event(
        self,
        *,
        event_type: str,
        source: Mapping[str, Any],
        fields: Mapping[str, Any],
        now: float,
    ) -> Dict[str, Any]:
        source_receipt_id = str(source["receipt_id"])
        digest = hashlib.sha256(
            f"{event_type}|{source_receipt_id}".encode("utf-8")
        ).hexdigest()[:24]
        input_receipt_ids = sorted({
            source_receipt_id,
            *[
                str(item) for item in source.get("input_receipt_ids", [])
                if _identifier(item) is not None
            ],
        })
        return {
            **dict(fields),
            "data_status": "live",
            "data_origin": "derived_from_fresh_provider_receipts",
            "truth_status": "real_derived",
            "source_id": f"aureon.real_data_feed_hub:{event_type}",
            "source_timestamp": _timestamp_seconds(source["source_timestamp"]),
            "received_at": now,
            "receipt_id": f"aureon.feed:{event_type}:{digest}",
            "input_receipt_ids": input_receipt_ids,
            "freshness_status": "fresh",
            "provider_observation": False,
            "input_provider_observation": True,
            "generated_values": False,
            "operational_eligible": False,
            "analysis_eligible": True,
            "actionable": False,
            "accounting_eligible": False,
            "learning_eligible": False,
            "eligible_for_action": False,
            "eligible_for_accounting": False,
            "eligible_for_learning": False,
        }
    
    def gather_and_distribute(
        self,
        prices: Optional[Mapping[str, Mapping[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Gather all intelligence and distribute to all systems.
        
        This is the main method that should be called periodically.
        Returns summary of distributed data.
        """
        now = self._clock()
        if not self.intelligence_engine:
            return self._record_no_data(
                "explicit_intelligence_engine_required"
            )

        numeric_prices, price_receipt_ids = self._validate_price_receipts(
            prices, now=now
        )
        if not numeric_prices:
            return dict(self.last_no_data)
        
        # Gather intelligence
        try:
            intel = self.intelligence_engine.gather_all_intelligence(
                numeric_prices
            )
        except Exception as e:
            logger.error(f"Intelligence gathering error: {e}")
            return self._record_no_data(
                f"intelligence_engine_failed:{type(e).__name__}"
            )
        if not isinstance(intel, Mapping):
            return self._record_no_data(
                "intelligence_engine_returned_no_complete_receipt_set"
            )

        bot_profiles = intel.get("bot_profiles")
        whale_predictions = intel.get("whale_predictions")
        momentum_opportunities = intel.get("momentum_opportunities")
        validated_intelligence = intel.get("validated_intelligence")
        if (
            not isinstance(bot_profiles, list)
            or not isinstance(whale_predictions, list)
            or not isinstance(momentum_opportunities, Mapping)
            or not isinstance(validated_intelligence, list)
            or any(
                not isinstance(items, list)
                for items in momentum_opportunities.values()
            )
        ):
            return self._record_no_data(
                "incomplete_intelligence_collection_receipt"
            )
        
        published_events: List[Dict[str, Any]] = []

        # Distribute bot profiles
        for bp in bot_profiles:
            event = self._distribute_bot(
                bp, now=now, price_receipt_ids=price_receipt_ids
            )
            if event is not None:
                published_events.append(event)
        
        # Distribute whale predictions
        for wp in whale_predictions:
            event = self._distribute_whale(
                wp, now=now, price_receipt_ids=price_receipt_ids
            )
            if event is not None:
                published_events.append(event)
        
        # Distribute momentum opportunities
        for scanner_type, opps in momentum_opportunities.items():
            for opp in opps:
                event = self._distribute_momentum(
                    opp,
                    scanner_type,
                    now=now,
                    price_receipt_ids=price_receipt_ids,
                )
                if event is not None:
                    published_events.append(event)
        
        # Distribute validated intelligence
        for vi in validated_intelligence:
            event = self._distribute_validated_intel(
                vi, now=now, price_receipt_ids=price_receipt_ids
            )
            if event is not None:
                published_events.append(event)

        if not published_events:
            no_data = self._record_no_data(
                "no_complete_fresh_intelligence_records"
            )
            self._publish_to_bus("intelligence.no_data", no_data)
            return no_data
        
        # Publish summary
        event_receipt_ids = sorted({
            event["receipt_id"] for event in published_events
        })
        digest = hashlib.sha256(
            "|".join(event_receipt_ids).encode("utf-8")
        ).hexdigest()[:24]
        summary = {
            "bots_distributed": sum(
                1 for event in published_events
                if event.get("event_type") == "bot"
            ),
            "whales_distributed": sum(
                1 for event in published_events
                if event.get("event_type") == "whale"
            ),
            "momentum_distributed": sum(
                1 for event in published_events
                if event.get("event_type") == "momentum"
            ),
            "intel_distributed": sum(
                1 for event in published_events
                if event.get("event_type") == "validated"
            ),
            "data_status": "live",
            "data_origin": "derived_from_fresh_intelligence_receipts",
            "truth_status": "real_derived",
            "source_id": "aureon.real_data_feed_hub:summary",
            "source_timestamp": min(
                event["source_timestamp"] for event in published_events
            ),
            "received_at": now,
            "receipt_id": f"aureon.feed:summary:{digest}",
            "input_receipt_ids": event_receipt_ids,
            "freshness_status": "fresh",
            "provider_observation": False,
            "input_provider_observation": True,
            "generated_values": False,
            "operational_eligible": False,
            "analysis_eligible": True,
            "actionable": False,
            "accounting_eligible": False,
            "learning_eligible": False,
            "eligible_for_action": False,
            "eligible_for_accounting": False,
            "eligible_for_learning": False,
        }
        self._publish_to_bus("intelligence.summary", summary)
        
        return summary
    
    def _distribute_bot(
        self,
        bp: Mapping[str, Any],
        *,
        now: float,
        price_receipt_ids: Dict[str, str],
    ) -> Optional[Dict[str, Any]]:
        """Distribute a bot event only from complete fresh evidence."""
        if not self._valid_intelligence_input(
            bp, now=now, price_receipt_ids=price_receipt_ids
        ):
            self._record_no_data("invalid_bot_intelligence_receipt")
            return None
        symbol = _identifier(bp.get("symbol"))
        firm = _identifier(bp.get("firm"))
        firm_animal = _identifier(bp.get("firm_animal"))
        bot_type = _identifier(bp.get("bot_type"))
        country = _identifier(bp.get("country"))
        confidence = _finite_number(bp.get("confidence"), minimum=0.0, maximum=1.0)
        estimated_capital = _finite_number(bp.get("estimated_capital"), minimum=0.0)
        layering_score = _finite_number(bp.get("layering_score"), minimum=0.0, maximum=1.0)
        timing_ms = _finite_number(bp.get("timing_ms"), minimum=0.0)
        strategies = bp.get("known_strategies")
        if (
            None in {
                symbol, firm, firm_animal, bot_type, country, confidence,
                estimated_capital, layering_score, timing_ms,
            }
            or not isinstance(strategies, list)
            or any(_identifier(item) is None for item in strategies)
        ):
            self._record_no_data(
                "malformed_bot_intelligence_values", symbol=symbol
            )
            return None
        event = self._derived_event(
            event_type="bot",
            source=bp,
            fields={
                "event_type": "bot",
                "symbol": symbol,
                "firm": firm,
                "firm_animal": firm_animal,
                "bot_type": bot_type,
                "confidence": confidence,
                "country": country,
                "estimated_capital": estimated_capital,
                "known_strategies": list(strategies),
                "layering_score": layering_score,
                "timing_ms": timing_ms,
            },
            now=now,
        )
        self._publish_to_bus("intelligence.bot.detected", event)
        firm_topic = firm.lower().replace(" ", "_")
        symbol_topic = symbol.replace("/", "_")
        self._publish_to_bus(f"intelligence.bot.firm.{firm_topic}", event)
        self._publish_to_bus(f"intelligence.bot.symbol.{symbol_topic}", event)
        self._add_to_intelligence_stream(event)
        self.bots_distributed += 1
        return event

    def _distribute_whale(
        self,
        wp: Mapping[str, Any],
        *,
        now: float,
        price_receipt_ids: Dict[str, str],
    ) -> Optional[Dict[str, Any]]:
        """Distribute a whale event only from complete fresh evidence."""
        if not self._valid_intelligence_input(
            wp, now=now, price_receipt_ids=price_receipt_ids
        ):
            self._record_no_data("invalid_whale_intelligence_receipt")
            return None
        symbol = _identifier(wp.get("symbol"))
        action = _identifier(wp.get("action"))
        side = _identifier(wp.get("side"))
        confidence = _finite_number(wp.get("confidence"), minimum=0.0, maximum=1.0)
        size_usd = _finite_number(wp.get("size_usd"), minimum=0.0)
        coherence = _finite_number(wp.get("coherence"))
        lambda_stability = _finite_number(wp.get("lambda_stability"))
        time_horizon = _finite_number(
            wp.get("time_horizon_minutes"), minimum=0.0
        )
        validated = wp.get("validated")
        validators = wp.get("validators")
        if (
            None in {
                symbol, action, side, confidence, size_usd, coherence,
                lambda_stability, time_horizon,
            }
            or not isinstance(validated, bool)
            or not isinstance(validators, Mapping)
            or any(_finite_number(value) is None for value in validators.values())
        ):
            self._record_no_data(
                "malformed_whale_intelligence_values", symbol=symbol
            )
            return None
        event = self._derived_event(
            event_type="whale",
            source=wp,
            fields={
                "event_type": "whale",
                "symbol": symbol,
                "action": action,
                "side": side,
                "confidence": confidence,
                "size_usd": size_usd,
                "coherence": coherence,
                "lambda_stability": lambda_stability,
                "validated": validated,
                "validators": dict(validators),
                "time_horizon_minutes": time_horizon,
            },
            now=now,
        )
        self._publish_to_bus("intelligence.whale.prediction", event)
        if validated:
            self._publish_to_bus("intelligence.whale.validated", event)
        symbol_topic = symbol.replace("/", "_")
        self._publish_to_bus(f"intelligence.whale.symbol.{symbol_topic}", event)
        self._add_to_intelligence_stream(event)
        self.whales_distributed += 1
        return event

    def _distribute_momentum(
        self,
        opp: Mapping[str, Any],
        scanner_type: str,
        *,
        now: float,
        price_receipt_ids: Dict[str, str],
    ) -> Optional[Dict[str, Any]]:
        """Distribute a momentum event only from complete fresh evidence."""
        if not self._valid_intelligence_input(
            opp, now=now, price_receipt_ids=price_receipt_ids
        ):
            self._record_no_data("invalid_momentum_intelligence_receipt")
            return None
        symbol = _identifier(opp.get("symbol"))
        scanner = _identifier(scanner_type)
        side = _identifier(opp.get("side"))
        reason = _identifier(opp.get("reason"))
        move_pct = _finite_number(opp.get("move_pct"))
        net_pct = _finite_number(opp.get("net_pct"))
        volume = _finite_number(opp.get("volume"), minimum=0.0)
        confidence = _finite_number(
            opp.get("confidence"), minimum=0.0, maximum=1.0
        )
        if None in {
            symbol, scanner, side, reason, move_pct, net_pct, volume,
            confidence,
        }:
            self._record_no_data(
                "malformed_momentum_intelligence_values", symbol=symbol
            )
            return None
        event = self._derived_event(
            event_type="momentum",
            source=opp,
            fields={
                "event_type": "momentum",
                "symbol": symbol,
                "scanner_type": scanner,
                "side": side,
                "move_pct": move_pct,
                "net_pct": net_pct,
                "volume": volume,
                "confidence": confidence,
                "reason": reason,
            },
            now=now,
        )
        self._publish_to_bus("intelligence.momentum.opportunity", event)
        self._publish_to_bus(f"intelligence.momentum.{scanner}", event)
        symbol_topic = symbol.replace("/", "_")
        self._publish_to_bus(
            f"intelligence.momentum.symbol.{symbol_topic}", event
        )
        self._add_to_intelligence_stream(event)
        self.momentum_distributed += 1
        return event

    def _distribute_validated_intel(
        self,
        vi: Mapping[str, Any],
        *,
        now: float,
        price_receipt_ids: Dict[str, str],
    ) -> Optional[Dict[str, Any]]:
        """Distribute combined intelligence without making it actionable."""
        if not self._valid_intelligence_input(
            vi, now=now, price_receipt_ids=price_receipt_ids
        ):
            self._record_no_data("invalid_validated_intelligence_receipt")
            return None
        symbol = _identifier(vi.get("symbol"))
        recommended_action = _identifier(vi.get("recommended_action"))
        reasoning = _identifier(vi.get("reasoning"))
        composite_score = _finite_number(
            vi.get("composite_score"), minimum=0.0, maximum=1.0
        )
        counts = [
            _finite_number(vi.get(name), minimum=0.0)
            for name in ("bot_count", "whale_count", "momentum_count")
        ]
        if (
            None in {symbol, recommended_action, reasoning, composite_score}
            or any(value is None or not value.is_integer() for value in counts)
        ):
            self._record_no_data(
                "malformed_validated_intelligence_values", symbol=symbol
            )
            return None
        event = self._derived_event(
            event_type="validated",
            source=vi,
            fields={
                "event_type": "validated",
                "symbol": symbol,
                "recommended_action": recommended_action,
                "composite_score": composite_score,
                "reasoning": reasoning,
                "bot_count": int(counts[0]),
                "whale_count": int(counts[1]),
                "momentum_count": int(counts[2]),
            },
            now=now,
        )
        self._publish_to_bus("intelligence.validated.signal", event)
        if composite_score > 0.618:
            self._publish_to_bus(
                "intelligence.validated.high_confidence", event
            )
        action_topic = recommended_action.lower()
        self._publish_to_bus(
            f"intelligence.validated.{action_topic}", event
        )
        self._add_to_intelligence_stream(event)
        self.intel_distributed += 1
        return event

    def get_consolidated_feeds_status(self) -> Dict[str, Any]:
        """
        Get status of all five consolidated feed streams.

        Returns:
            Status of each consolidated stream
        """
        return {
            stream_name: stream.get_status()
            for stream_name, stream in self.consolidated_streams.items()
        }

    def publish_to_consolidated(
        self,
        stream_type: str,
        event: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Publish an event to a consolidated stream.

        Args:
            stream_type: One of: market_data, intelligence, risk_metrics, execution_status, system_health
            event: Event data to publish
        """
        if stream_type not in self.consolidated_streams:
            logger.warning(f"Unknown consolidated stream: {stream_type}")
            return self._record_no_data(
                "unknown_consolidated_stream",
                stream_type=str(stream_type),
            )

        now = self._clock()
        complete_live = (
            _complete_live_record(
                event, now=now, max_age_seconds=self.max_age_seconds
            )
            and event.get("freshness_status") == "fresh"
            and event.get("generated_values") is False
            and event.get("operational_eligible") is False
            and event.get("actionable") is False
            and event.get("accounting_eligible") is False
            and event.get("learning_eligible") is False
        )
        if not complete_live:
            no_data = self._record_no_data(
                "consolidated_event_missing_complete_fresh_provenance",
                stream_type=stream_type,
            )
            self._publish_to_bus(
                f"feeds.consolidated.{stream_type}.no_data", no_data
            )
            return no_data

        # Add to consolidated stream
        self.consolidated_streams[stream_type].add_event(event)

        # Also publish to ThoughtBus
        self._publish_to_bus(f"feeds.consolidated.{stream_type}", event)
        return dict(event)

    def _add_to_intelligence_stream(
        self,
        event: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Add an event to the intelligence consolidated stream"""
        return self.publish_to_consolidated("intelligence", event)

    def start_continuous_feed(
        self,
        interval: float = 5.0,
        *,
        price_receipt_supplier: Optional[Callable[[], Mapping[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Start only with an explicit supplier of stamped price receipts."""
        if self.running:
            return _no_data("continuous_feed_already_running")
        parsed_interval = _finite_number(interval, minimum=0.001)
        if (
            parsed_interval is None
            or self.intelligence_engine is None
            or not callable(price_receipt_supplier)
        ):
            return self._record_no_data(
                "continuous_feed_requires_engine_and_price_receipt_supplier"
            )

        self.running = True

        def feed_loop() -> None:
            logger.info(
                "Starting continuous real data feed (interval: %ss)",
                parsed_interval,
            )
            while self.running:
                try:
                    receipts = price_receipt_supplier()
                    summary = self.gather_and_distribute(receipts)
                    if summary.get("data_status") == "live":
                        logger.debug(
                            "Distributed complete feed summary receipt %s",
                            summary["receipt_id"],
                        )
                    else:
                        logger.debug(
                            "Feed cycle produced no-data: %s",
                            summary.get("reason"),
                        )
                except Exception as exc:
                    logger.error("Feed error: %s", type(exc).__name__)
                time.sleep(parsed_interval)

        self.feed_thread = threading.Thread(target=feed_loop, daemon=True)
        self.feed_thread.start()
        return _no_data("continuous_feed_started_without_cycle_receipt")

    def stop_feed(self):
        """Stop continuous feed"""
        self.running = False
        if self.feed_thread:
            self.feed_thread.join(timeout=2.0)


# ═══════════════════════════════════════════════════════════════════════════════
# SYSTEM WIRING HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def wire_system_to_real_data(system_name: str, callback: Callable, topics: List[str] = None):
    """
    Helper to wire any system to receive real intelligence data.
    
    Usage:
        def my_handler(topic, data):
            print(f"Got {topic}: {data}")
        
        wire_system_to_real_data("my_system", my_handler, ["intelligence.bot.*", "intelligence.whale.*"])
    """
    hub = get_feed_hub()
    
    if topics is None:
        topics = ["intelligence.*"]  # Subscribe to all intelligence
    
    for topic in topics:
        hub.subscribe(topic, callback)
    
    logger.info(f"🔗 Wired {system_name} to real data feed ({len(topics)} topics)")


def get_latest_intel_for_symbol(symbol: str) -> Dict[str, Any]:
    """Return the latest already-verified event without fetching data."""
    hub = get_feed_hub()
    normalized_symbol = _identifier(symbol)
    if normalized_symbol is None:
        return _no_data("symbol_required")
    stream = hub.consolidated_streams["intelligence"]
    now = hub._clock()
    for event in reversed(stream.latest_events):
        if (
            event.get("symbol") == normalized_symbol
            and _complete_live_record(
                event, now=now, max_age_seconds=hub.max_age_seconds
            )
        ):
            return dict(event)
    return _no_data(
        "no_complete_fresh_intelligence_for_symbol",
        symbol=normalized_symbol,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# GLOBAL FEED HUB INSTANCE
# ═══════════════════════════════════════════════════════════════════════════════

_global_hub: Optional[RealDataFeedHub] = None

def get_feed_hub() -> RealDataFeedHub:
    """Get or create the global feed hub"""
    global _global_hub
    if _global_hub is None:
        _global_hub = RealDataFeedHub()
    return _global_hub


def start_global_feed(
    interval: float = 5.0,
    *,
    price_receipt_supplier: Optional[Callable[[], Mapping[str, Any]]] = None,
):
    """Start the global real data feed"""
    hub = get_feed_hub()
    hub.start_continuous_feed(
        interval,
        price_receipt_supplier=price_receipt_supplier,
    )
    return hub


# ═══════════════════════════════════════════════════════════════════════════════
# STANDALONE TEST
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print(_no_data(
        "explicit_engine_and_stamped_price_receipts_required"
    ))

#!/usr/bin/env python3
"""
👑 QUEEN OPTIONS SCANNER - INTELLIGENT OPTIONS DISCOVERY 👑
═══════════════════════════════════════════════════════════════════════════════

Scans for optimal options opportunities using:
  - Premium vs risk analysis
  - Greeks-based filtering (delta, theta, IV)
  - Queen Hive confidence scoring
  - Covered call income strategies
  - Cash-secured put entries

Gary Leckey | January 2026
═══════════════════════════════════════════════════════════════════════════════
"""

import math
import hashlib
import logging
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Any, Callable, Mapping, Sequence, Tuple

# Local value-compatible enums keep import inert; injected Alpaca clients only
# consume their ``.value`` fields.
class OptionType(Enum):
    CALL = "call"
    PUT = "put"


class TradingLevel(Enum):
    DISABLED = 0
    COVERED = 1
    BUYING = 2
    SPREADS = 3


OptionContract = Any
OptionQuote = Any

logger = logging.getLogger(__name__)

ALPACA_SOURCE_TOKEN = "alpaca"
SCANNER_SOURCE_ID = "aureon:queen-options-scanner"
DEFAULT_MARKET_MAX_AGE_SECONDS = 60.0
DEFAULT_ACCOUNT_MAX_AGE_SECONDS = 300.0
DEFAULT_CONTRACT_MAX_AGE_SECONDS = 86400.0
MAX_PROVIDER_FUTURE_SKEW_SECONDS = 5.0

# ═══════════════════════════════════════════════════════════════════════════════
# OPTIONS OPPORTUNITY
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class OptionsOpportunity:
    """Receipt-linked analytical opportunity; never an action authorization."""
    contract: OptionContract
    quote: OptionQuote
    strategy: str
    
    # Scoring
    premium_score: float           # Premium as % of strike
    spread_score: float            # Tight spread = higher score
    volume_score: float            # Higher volume = higher score
    theta_score: float             # Daily decay value
    
    source_id: str
    source_timestamp: float
    received_at: str
    receipt_id: str
    source_receipt_ids: Tuple[str, ...]
    truth_status: str = "real_derived"
    data_status: str = "live"
    generated_values: bool = False
    eligible_for_ranking: bool = True
    eligible_for_action: bool = False
    eligible_for_accounting: bool = False
    eligible_for_learning: bool = False

    queen_confidence: Optional[float] = None
    queen_guidance_receipt_id: Optional[str] = None
    total_score: Optional[float] = None
    max_profit: Optional[float] = None
    max_risk: Optional[float] = None
    breakeven: Optional[float] = None
    days_to_expiry: Optional[int] = None
    annualized_return: Optional[float] = None

    @staticmethod
    def _finite(value: Any, *, positive: bool = False) -> float:
        if value is None or isinstance(value, bool):
            raise ValueError("missing numeric observation")
        try:
            number = float(value)
        except (TypeError, ValueError, OverflowError) as exc:
            raise ValueError("invalid numeric observation") from exc
        if not math.isfinite(number) or (positive and number <= 0.0):
            raise ValueError("finite observed number required")
        return number

    def calculate_scores(
        self,
        underlying_price: float,
        *,
        as_of: Optional[datetime] = None,
    ) -> None:
        """Calculate with an injected timestamp; never consult local wall time."""
        if as_of is None or as_of.tzinfo is None:
            raise ValueError("timezone-aware as_of is required")
        underlying_price = self._finite(underlying_price, positive=True)
        mid_price = self._finite(getattr(self.quote, "mid_price", None), positive=True)
        strike_price = self._finite(getattr(self.contract, "strike_price", None), positive=True)
        spread_pct = self._finite(getattr(self.quote, "spread_pct", None))
        volume = self._finite(getattr(self.quote, "volume", None))
        if spread_pct < 0.0 or volume < 0.0:
            raise ValueError("non-negative spread and volume required")
        try:
            expiration = datetime.strptime(
                str(getattr(self.contract, "expiration_date")), "%Y-%m-%d"
            ).replace(tzinfo=timezone.utc)
        except (TypeError, ValueError) as exc:
            raise ValueError("valid provider expiration required") from exc
        days_to_expiry = (expiration - as_of.astimezone(timezone.utc)).days
        if days_to_expiry <= 0:
            raise ValueError("future expiration required")

        # Premium equation retained exactly.
        premium = mid_price * 100

        if self.strategy == "covered_call":
            collateral = underlying_price * 100
            max_profit = premium
            max_risk = underlying_price * 100
            breakeven = underlying_price - mid_price
        elif self.strategy == "cash_secured_put":
            collateral = strike_price * 100
            max_profit = premium
            max_risk = collateral - premium
            breakeven = strike_price - mid_price
        else:
            raise ValueError("receipt-gated selling strategies only")
        if collateral <= 0.0:
            raise ValueError("positive collateral required")
        premium_score = min(1.0, (premium / collateral) * 10)

        # Spread and volume equations retained exactly.
        if spread_pct < 1:
            spread_score = 1.0
        elif spread_pct < 5:
            spread_score = 0.8
        elif spread_pct < 10:
            spread_score = 0.5
        else:
            spread_score = 0.2
        if volume > 1000:
            volume_score = 1.0
        elif volume > 100:
            volume_score = 0.7
        elif volume > 10:
            volume_score = 0.4
        else:
            volume_score = 0.2

        # Theta and annualized equations retained exactly.
        daily_decay_pct = (mid_price / days_to_expiry) / mid_price * 100
        theta_score = min(1.0, daily_decay_pct * 10)
        period_return = max_profit / collateral
        annualized_return = (1 + period_return) ** (365 / days_to_expiry) - 1
        total_score = (
            premium_score * 0.35 +
            spread_score * 0.25 +
            volume_score * 0.20 +
            theta_score * 0.20
        )
        values = (
            premium_score, spread_score, volume_score, theta_score,
            max_profit, max_risk, breakeven, annualized_return, total_score,
        )
        if not all(math.isfinite(value) for value in values):
            raise ValueError("non-finite derived analysis")
        self.premium_score = premium_score
        self.spread_score = spread_score
        self.volume_score = volume_score
        self.theta_score = theta_score
        self.max_profit = max_profit
        self.max_risk = max_risk
        self.breakeven = breakeven
        self.days_to_expiry = days_to_expiry
        self.annualized_return = annualized_return
        self.total_score = total_score


# ═══════════════════════════════════════════════════════════════════════════════
# QUEEN OPTIONS SCANNER
# ═══════════════════════════════════════════════════════════════════════════════

class QueenOptionsScanner:
    """
    👑 Intelligent Options Scanner
    
    Scans for optimal options opportunities based on:
    - Trading level (Level 1: covered calls, cash-secured puts)
    - Premium yield analysis
    - Spread/liquidity scoring
    - Queen Hive confidence
    """
    
    def __init__(
        self,
        client: Any = None,
        queen: Any = None,
        *,
        underlying_client: Any = None,
        clock: Optional[Callable[[], float]] = None,
        trading_level_receipt: Optional[Mapping[str, Any]] = None,
        position_receipts: Optional[Mapping[str, Mapping[str, Any]]] = None,
        capital_receipt: Optional[Mapping[str, Any]] = None,
        market_max_age_seconds: float = DEFAULT_MARKET_MAX_AGE_SECONDS,
        account_max_age_seconds: float = DEFAULT_ACCOUNT_MAX_AGE_SECONDS,
        contract_max_age_seconds: float = DEFAULT_CONTRACT_MAX_AGE_SECONDS,
    ):
        # Construction is inert. Clients, Queen, and the clock are injected.
        self.client = client
        self.queen = queen
        self.underlying_client = underlying_client
        self._clock = clock
        self._trading_level_receipt = trading_level_receipt
        self._position_receipts = dict(position_receipts or {})
        self._capital_receipt = capital_receipt
        self.market_max_age_seconds = self._window(market_max_age_seconds)
        self.account_max_age_seconds = self._window(account_max_age_seconds)
        self.contract_max_age_seconds = self._window(contract_max_age_seconds)
        self.trading_level: Optional[TradingLevel] = None
        self.last_scan_receipt = self._no_data_receipt("scanner_not_run")

    @staticmethod
    def _window(value: Any) -> float:
        try:
            window = float(value)
        except (TypeError, ValueError, OverflowError) as exc:
            raise ValueError("freshness window must be finite and positive") from exc
        if not math.isfinite(window) or window <= 0.0:
            raise ValueError("freshness window must be finite and positive")
        return window

    @staticmethod
    def _finite(
        value: Any, *, positive: bool = False, nonnegative: bool = False
    ) -> Optional[float]:
        if value is None or isinstance(value, bool):
            return None
        try:
            number = float(value)
        except (TypeError, ValueError, OverflowError):
            return None
        if not math.isfinite(number):
            return None
        if positive and number <= 0.0:
            return None
        if nonnegative and number < 0.0:
            return None
        return number

    @staticmethod
    def _timestamp(value: Any) -> Optional[float]:
        if value is None or isinstance(value, bool):
            return None
        if isinstance(value, (int, float)):
            timestamp = float(value)
            return timestamp if math.isfinite(timestamp) and timestamp > 0.0 else None
        if not isinstance(value, str) or not value.strip():
            return None
        try:
            parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        except ValueError:
            return None
        if parsed.tzinfo is None:
            return None
        timestamp = parsed.timestamp()
        return timestamp if math.isfinite(timestamp) and timestamp > 0.0 else None

    def _now(self) -> float:
        if self._clock is None:
            raise ValueError("an injected clock is required")
        value = self._clock()
        if isinstance(value, datetime):
            if value.tzinfo is None:
                raise ValueError("clock datetime must be timezone-aware")
            value = value.timestamp()
        now = self._finite(value, positive=True)
        if now is None:
            raise ValueError("clock must return a positive finite epoch")
        return now

    @staticmethod
    def _iso(epoch: float) -> str:
        return datetime.fromtimestamp(epoch, tz=timezone.utc).isoformat()

    def _no_data_receipt(self, reason: str) -> Dict[str, Any]:
        try:
            received_at = self._iso(self._now())
        except ValueError:
            received_at = None
        return {
            "source_id": SCANNER_SOURCE_ID,
            "source_timestamp": None,
            "received_at": received_at,
            "receipt_id": None,
            "truth_status": "no_data",
            "data_status": "no_data",
            "reason": reason,
            "generated_values": False,
            "eligible_for_ranking": False,
            "eligible_for_action": False,
            "eligible_for_accounting": False,
            "eligible_for_learning": False,
        }

    def _fail(self, reason: str) -> List[OptionsOpportunity]:
        self.last_scan_receipt = self._no_data_receipt(reason)
        return []

    @staticmethod
    def _receipt_of(value: Any) -> Optional[Mapping[str, Any]]:
        if isinstance(value, Mapping):
            nested = value.get("receipt")
            return nested if isinstance(nested, Mapping) else value
        receipt = getattr(value, "receipt", None)
        return receipt if isinstance(receipt, Mapping) else None

    @staticmethod
    def _payload(value: Any, key: str) -> Any:
        return value.get(key) if isinstance(value, Mapping) and key in value else value

    def _receipt(
        self,
        value: Any,
        *,
        now: float,
        max_age: float,
        alpaca: bool = True,
    ) -> Optional[Dict[str, Any]]:
        receipt = self._receipt_of(value)
        if receipt is None:
            return None
        source_id = receipt.get("source_id")
        receipt_id = receipt.get("receipt_id")
        if not isinstance(source_id, str) or not source_id.strip():
            return None
        if alpaca and ALPACA_SOURCE_TOKEN not in source_id.lower():
            return None
        if not isinstance(receipt_id, str) or not receipt_id.strip():
            return None
        if receipt.get("truth_status") != "real_observed":
            return None
        if receipt.get("data_status") != "live":
            return None
        if receipt.get("generated_values") is not False:
            return None
        source_time = self._timestamp(receipt.get("source_timestamp"))
        received_time = self._timestamp(receipt.get("received_at"))
        if source_time is None or received_time is None:
            return None
        if source_time > now + MAX_PROVIDER_FUTURE_SKEW_SECONDS:
            return None
        if received_time > now + MAX_PROVIDER_FUTURE_SKEW_SECONDS:
            return None
        if source_time > received_time + MAX_PROVIDER_FUTURE_SKEW_SECONDS:
            return None
        if now - source_time > max_age or now - received_time > max_age:
            return None
        normalized = dict(receipt)
        normalized["source_id"] = source_id.strip()
        normalized["receipt_id"] = receipt_id.strip()
        normalized["source_timestamp"] = source_time
        return normalized

    @staticmethod
    def _level_value(value: Any) -> Optional[int]:
        raw = getattr(value, "value", value)
        if isinstance(raw, bool):
            return None
        try:
            level = int(raw)
        except (TypeError, ValueError, OverflowError):
            return None
        return level if level in {0, 1, 2, 3} else None

    @staticmethod
    def _type_value(value: Any) -> Optional[str]:
        raw = getattr(value, "value", value)
        if not isinstance(raw, str):
            return None
        normalized = raw.strip().lower()
        return normalized if normalized in {"call", "put"} else None

    def _underlying_raw(self, symbol: str, supplied: Any) -> Any:
        if supplied is not None:
            return supplied
        method = getattr(self.underlying_client, "get_stock_quote_receipt", None)
        return method(symbol) if callable(method) else None

    def _level_raw(self, supplied: Any) -> Any:
        if supplied is not None:
            return supplied
        if self._trading_level_receipt is not None:
            return self._trading_level_receipt
        method = getattr(self.client, "get_trading_level_receipt", None)
        return method() if callable(method) else None

    def _position_raw(self, symbol: str, supplied: Any) -> Any:
        if supplied is not None:
            return supplied
        cached = self._position_receipts.get(symbol.upper())
        if cached is not None:
            return cached
        method = getattr(self.client, "get_underlying_position_receipt", None)
        return method(symbol) if callable(method) else None

    def _capital_raw(self, supplied: Any) -> Any:
        if supplied is not None:
            return supplied
        if self._capital_receipt is not None:
            return self._capital_receipt
        method = getattr(self.client, "get_options_capital_receipt", None)
        return method() if callable(method) else None

    def _validate_underlying(
        self, symbol: str, current_price: Any, supplied: Any, *, now: float
    ) -> Optional[Tuple[Dict[str, Any], float]]:
        try:
            raw = self._underlying_raw(symbol, supplied)
        except Exception:
            return None
        receipt = self._receipt(raw, now=now, max_age=self.market_max_age_seconds)
        if receipt is None or str(receipt.get("symbol", "")).upper() != symbol.upper():
            return None
        bid = self._finite(receipt.get("bid"), positive=True)
        ask = self._finite(receipt.get("ask"), positive=True)
        observed = self._finite(receipt.get("price"), positive=True)
        requested = self._finite(current_price, positive=True)
        if None in (bid, ask, observed, requested):
            return None
        assert bid is not None and ask is not None
        assert observed is not None and requested is not None
        if bid > ask or not (bid <= observed <= ask):
            return None
        if not math.isclose(requested, observed, rel_tol=1e-12, abs_tol=1e-12):
            return None
        return receipt, observed

    def _validate_level(
        self, supplied: Any, *, now: float
    ) -> Optional[Tuple[Dict[str, Any], int]]:
        try:
            raw = self._level_raw(supplied)
        except Exception:
            return None
        receipt = self._receipt(raw, now=now, max_age=self.account_max_age_seconds)
        if receipt is None or not isinstance(receipt.get("account_id"), str):
            return None
        level = self._level_value(receipt.get("trading_level"))
        if level is None or level < TradingLevel.COVERED.value:
            return None
        self.trading_level = TradingLevel(level)
        return receipt, level

    def _validate_position(
        self,
        symbol: str,
        required_shares: Any,
        supplied: Any,
        *,
        underlying_receipt: Mapping[str, Any],
        level_receipt: Mapping[str, Any],
        now: float,
    ) -> Optional[Dict[str, Any]]:
        required = self._finite(required_shares, positive=True)
        if required is None or not required.is_integer():
            return None
        try:
            raw = self._position_raw(symbol, supplied)
        except Exception:
            return None
        receipt = self._receipt(raw, now=now, max_age=self.account_max_age_seconds)
        if receipt is None:
            return None
        shares = self._finite(receipt.get("shares"), nonnegative=True)
        if shares is None or not shares.is_integer() or shares < required:
            return None
        if str(receipt.get("symbol", "")).upper() != symbol.upper():
            return None
        if receipt.get("account_id") != level_receipt.get("account_id"):
            return None
        if receipt.get("trading_level_receipt_id") != level_receipt.get("receipt_id"):
            return None
        if receipt.get("underlying_receipt_id") != underlying_receipt.get("receipt_id"):
            return None
        return receipt

    def _validate_capital(
        self,
        max_collateral: Any,
        supplied: Any,
        *,
        level_receipt: Mapping[str, Any],
        now: float,
    ) -> Optional[Tuple[Dict[str, Any], float]]:
        limit = self._finite(max_collateral, positive=True)
        if limit is None:
            return None
        try:
            raw = self._capital_raw(supplied)
        except Exception:
            return None
        receipt = self._receipt(raw, now=now, max_age=self.account_max_age_seconds)
        if receipt is None:
            return None
        available = self._finite(receipt.get("available_cash"), nonnegative=True)
        if available is None or limit > available:
            return None
        if str(receipt.get("currency", "")).upper() != "USD":
            return None
        if receipt.get("account_id") != level_receipt.get("account_id"):
            return None
        if receipt.get("trading_level_receipt_id") != level_receipt.get("receipt_id"):
            return None
        return receipt, limit

    def _validate_contract(
        self,
        raw: Any,
        *,
        symbol: str,
        expected_type: str,
        min_date: str,
        max_date: str,
        underlying_receipt: Mapping[str, Any],
        now: float,
    ) -> Optional[Tuple[Any, Dict[str, Any]]]:
        receipt = self._receipt(raw, now=now, max_age=self.contract_max_age_seconds)
        contract = self._payload(raw, "contract")
        if receipt is None or contract is None:
            return None
        option_symbol = getattr(contract, "symbol", None)
        contract_id = getattr(contract, "id", None)
        if not isinstance(option_symbol, str) or not option_symbol.strip():
            return None
        if not isinstance(contract_id, str) or not contract_id.strip():
            return None
        if receipt.get("symbol") != option_symbol:
            return None
        if str(getattr(contract, "underlying_symbol", "")).upper() != symbol.upper():
            return None
        if self._type_value(getattr(contract, "option_type", None)) != expected_type:
            return None
        if getattr(contract, "tradable", None) is not True:
            return None
        if str(getattr(contract, "status", "")).lower() != "active":
            return None
        strike = self._finite(getattr(contract, "strike_price", None), positive=True)
        size = self._finite(getattr(contract, "size", None), positive=True)
        if strike is None or size != 100.0:
            return None
        expiration = getattr(contract, "expiration_date", None)
        if not isinstance(expiration, str) or not (min_date <= expiration <= max_date):
            return None
        try:
            datetime.strptime(expiration, "%Y-%m-%d")
        except ValueError:
            return None
        if receipt.get("underlying_receipt_id") != underlying_receipt.get("receipt_id"):
            return None
        return contract, receipt

    def _validate_quote(
        self,
        raw: Any,
        *,
        contract: Any,
        contract_receipt: Mapping[str, Any],
        underlying_receipt: Mapping[str, Any],
        now: float,
    ) -> Optional[Tuple[Any, Dict[str, Any]]]:
        receipt = self._receipt(raw, now=now, max_age=self.market_max_age_seconds)
        quote = self._payload(raw, "quote")
        if receipt is None or quote is None:
            return None
        option_symbol = getattr(contract, "symbol", None)
        if getattr(quote, "symbol", None) != option_symbol:
            return None
        if receipt.get("symbol") != option_symbol:
            return None
        bid = self._finite(getattr(quote, "bid", None), positive=True)
        ask = self._finite(getattr(quote, "ask", None), positive=True)
        bid_size = self._finite(getattr(quote, "bid_size", None), positive=True)
        ask_size = self._finite(getattr(quote, "ask_size", None), positive=True)
        last_price = self._finite(getattr(quote, "last_price", None), nonnegative=True)
        volume = self._finite(getattr(quote, "volume", None), nonnegative=True)
        if any(value is None for value in (bid, ask, bid_size, ask_size, last_price, volume)):
            return None
        assert bid is not None and ask is not None
        if bid > ask:
            return None
        quote_time = self._timestamp(getattr(quote, "timestamp", None))
        if quote_time is None or not math.isclose(
            quote_time,
            float(receipt["source_timestamp"]),
            rel_tol=0.0,
            abs_tol=1.0,
        ):
            return None
        if self._finite(getattr(quote, "mid_price", None), positive=True) is None:
            return None
        if self._finite(getattr(quote, "spread_pct", None), nonnegative=True) is None:
            return None
        if receipt.get("contract_receipt_id") != contract_receipt.get("receipt_id"):
            return None
        if receipt.get("underlying_receipt_id") != underlying_receipt.get("receipt_id"):
            return None
        return quote, receipt

    @staticmethod
    def _derived_id(strategy: str, receipt_ids: Sequence[str]) -> str:
        material = "|".join((strategy, *receipt_ids)).encode("utf-8")
        digest = hashlib.sha256(material).hexdigest()[:24]
        return f"queen-options:derived:{digest}"

    def _opportunity(
        self,
        *,
        contract: Any,
        quote: Any,
        strategy: str,
        current_price: float,
        receipts: Sequence[Mapping[str, Any]],
        now: float,
    ) -> Optional[OptionsOpportunity]:
        receipt_ids = tuple(str(receipt["receipt_id"]) for receipt in receipts)
        opportunity = OptionsOpportunity(
            contract=contract,
            quote=quote,
            strategy=strategy,
            premium_score=0.0,
            spread_score=0.0,
            volume_score=0.0,
            theta_score=0.0,
            source_id=SCANNER_SOURCE_ID,
            source_timestamp=min(float(receipt["source_timestamp"]) for receipt in receipts),
            received_at=self._iso(now),
            receipt_id=self._derived_id(strategy, receipt_ids),
            source_receipt_ids=receipt_ids,
        )
        try:
            opportunity.calculate_scores(
                current_price,
                as_of=datetime.fromtimestamp(now, tz=timezone.utc),
            )
        except ValueError:
            return None
        self._queen_guidance(opportunity, current_price=current_price, now=now)
        return opportunity

    def _queen_guidance(
        self, opportunity: OptionsOpportunity, *, current_price: float, now: float
    ) -> None:
        method = getattr(self.queen, "ask_queen_will_we_win", None)
        if not callable(method):
            return
        try:
            guidance = method(
                asset=str(getattr(opportunity.contract, "underlying_symbol")),
                exchange="alpaca",
                opportunity_score=float(opportunity.total_score) * 100,
                context={
                    "strategy": opportunity.strategy,
                    "strike": getattr(opportunity.contract, "strike_price"),
                    "expiry": getattr(opportunity.contract, "expiration_date"),
                    "premium": getattr(opportunity.quote, "mid_price"),
                    "underlying_price": current_price,
                    "opportunity_receipt_id": opportunity.receipt_id,
                },
            )
        except Exception:
            return
        receipt = self._receipt(
            guidance, now=now, max_age=self.market_max_age_seconds, alpaca=False
        )
        if receipt is None or receipt.get("opportunity_receipt_id") != opportunity.receipt_id:
            return
        confidence = self._finite(receipt.get("confidence"), nonnegative=True)
        if confidence is None or confidence > 1.0:
            return
        opportunity.queen_confidence = confidence
        opportunity.queen_guidance_receipt_id = str(receipt["receipt_id"])
    
    def _scan_validated(
        self,
        *,
        symbol: str,
        current_price: float,
        strategy: str,
        option_type: OptionType,
        min_strike: float,
        max_strike: float,
        min_days_expiry: Any,
        max_days_expiry: Any,
        underlying_receipt: Mapping[str, Any],
        level_receipt: Mapping[str, Any],
        authorization_receipt: Mapping[str, Any],
        now: float,
    ) -> List[OptionsOpportunity]:
        if self.client is None:
            return self._fail("injected_options_client_required")
        min_days = self._finite(min_days_expiry, positive=True)
        max_days = self._finite(max_days_expiry, positive=True)
        if (
            min_days is None
            or max_days is None
            or not min_days.is_integer()
            or not max_days.is_integer()
            or min_days > max_days
        ):
            return self._fail("valid_expiry_window_required")
        basis = datetime.fromtimestamp(now, tz=timezone.utc)
        min_date = (basis + timedelta(days=int(min_days))).strftime("%Y-%m-%d")
        max_date = (basis + timedelta(days=int(max_days))).strftime("%Y-%m-%d")
        try:
            raw_contracts = self.client.get_contracts(
                underlying_symbol=symbol,
                expiration_date_gte=min_date,
                expiration_date_lte=max_date,
                option_type=option_type,
                strike_price_gte=min_strike,
                strike_price_lte=max_strike,
                limit=50,
            )
        except Exception:
            return self._fail("option_contract_receipt_request_failed")
        if not isinstance(raw_contracts, Sequence) or isinstance(
            raw_contracts, (str, bytes)
        ):
            return self._fail("fresh_complete_option_contract_receipts_required")
        contracts: List[Tuple[Any, Dict[str, Any]]] = []
        for raw_contract in raw_contracts:
            validated = self._validate_contract(
                raw_contract,
                symbol=symbol,
                expected_type=option_type.value,
                min_date=min_date,
                max_date=max_date,
                underlying_receipt=underlying_receipt,
                now=now,
            )
            if validated is not None:
                contracts.append(validated)
        if not contracts:
            return self._fail("fresh_complete_option_contract_receipts_required")
        symbols = [contract.symbol for contract, _ in contracts]
        try:
            raw_quotes = self.client.get_quotes(symbols)
        except Exception:
            return self._fail("option_quote_receipt_request_failed")
        if not isinstance(raw_quotes, Mapping):
            return self._fail("fresh_complete_option_quote_receipts_required")
        opportunities: List[OptionsOpportunity] = []
        for contract, contract_evidence in contracts:
            validated_quote = self._validate_quote(
                raw_quotes.get(contract.symbol),
                contract=contract,
                contract_receipt=contract_evidence,
                underlying_receipt=underlying_receipt,
                now=now,
            )
            if validated_quote is None:
                continue
            quote, quote_evidence = validated_quote
            opportunity = self._opportunity(
                contract=contract,
                quote=quote,
                strategy=strategy,
                current_price=current_price,
                receipts=(
                    underlying_receipt,
                    level_receipt,
                    authorization_receipt,
                    contract_evidence,
                    quote_evidence,
                ),
                now=now,
            )
            if opportunity is not None:
                opportunities.append(opportunity)
        if not opportunities:
            return self._fail("fresh_linked_option_quote_receipts_required")
        opportunities.sort(key=lambda item: float(item.total_score), reverse=True)
        ids = tuple(item.receipt_id for item in opportunities)
        self.last_scan_receipt = {
            "source_id": SCANNER_SOURCE_ID,
            "source_timestamp": min(item.source_timestamp for item in opportunities),
            "received_at": self._iso(now),
            "receipt_id": self._derived_id("scan", ids),
            "opportunity_receipt_ids": ids,
            "truth_status": "real_derived",
            "data_status": "live",
            "generated_values": False,
            "eligible_for_ranking": True,
            "eligible_for_action": False,
            "eligible_for_accounting": False,
            "eligible_for_learning": False,
        }
        return opportunities

    def scan_covered_calls(
        self,
        underlying: str,
        current_price: float,
        min_otm_pct: float = 0.03,
        max_otm_pct: float = 0.15,
        min_days_expiry: int = 7,
        max_days_expiry: int = 45,
        shares_owned: int = 100,
        underlying_receipt: Optional[Mapping[str, Any]] = None,
        position_receipt: Optional[Mapping[str, Any]] = None,
        trading_level_receipt: Optional[Mapping[str, Any]] = None,
    ) -> List[OptionsOpportunity]:
        """Analyze covered calls only from a complete linked position chain."""
        try:
            now = self._now()
        except ValueError:
            return []
        current = self._finite(current_price, positive=True)
        min_otm = self._finite(min_otm_pct, nonnegative=True)
        max_otm = self._finite(max_otm_pct, nonnegative=True)
        if current is None or min_otm is None or max_otm is None or min_otm > max_otm:
            return self._fail("valid_underlying_and_otm_window_required")
        underlying_data = self._validate_underlying(
            underlying, current, underlying_receipt, now=now
        )
        level_data = self._validate_level(trading_level_receipt, now=now)
        if underlying_data is None:
            return self._fail("fresh_complete_underlying_receipt_required")
        if level_data is None:
            return self._fail("fresh_complete_trading_level_receipt_required")
        position = self._validate_position(
            underlying,
            shares_owned,
            position_receipt,
            underlying_receipt=underlying_data[0],
            level_receipt=level_data[0],
            now=now,
        )
        if position is None:
            return self._fail("fresh_linked_underlying_position_receipt_required")
        return self._scan_validated(
            symbol=underlying,
            current_price=underlying_data[1],
            strategy="covered_call",
            option_type=OptionType.CALL,
            min_strike=current * (1 + min_otm),
            max_strike=current * (1 + max_otm),
            min_days_expiry=min_days_expiry,
            max_days_expiry=max_days_expiry,
            underlying_receipt=underlying_data[0],
            level_receipt=level_data[0],
            authorization_receipt=position,
            now=now,
        )
    def scan_cash_secured_puts(
        self,
        underlying: str,
        current_price: float,
        min_otm_pct: float = 0.03,
        max_otm_pct: float = 0.15,
        min_days_expiry: int = 7,
        max_days_expiry: int = 45,
        max_collateral: float = 10000,
        underlying_receipt: Optional[Mapping[str, Any]] = None,
        capital_receipt: Optional[Mapping[str, Any]] = None,
        trading_level_receipt: Optional[Mapping[str, Any]] = None,
    ) -> List[OptionsOpportunity]:
        """Analyze cash-secured puts only from a complete linked capital chain."""
        try:
            now = self._now()
        except ValueError:
            return []
        current = self._finite(current_price, positive=True)
        min_otm = self._finite(min_otm_pct, nonnegative=True)
        max_otm = self._finite(max_otm_pct, nonnegative=True)
        if current is None or min_otm is None or max_otm is None or min_otm > max_otm:
            return self._fail("valid_underlying_and_otm_window_required")
        underlying_data = self._validate_underlying(
            underlying, current, underlying_receipt, now=now
        )
        level_data = self._validate_level(trading_level_receipt, now=now)
        if underlying_data is None:
            return self._fail("fresh_complete_underlying_receipt_required")
        if level_data is None:
            return self._fail("fresh_complete_trading_level_receipt_required")
        capital = self._validate_capital(
            max_collateral,
            capital_receipt,
            level_receipt=level_data[0],
            now=now,
        )
        if capital is None:
            return self._fail("fresh_linked_options_capital_receipt_required")
        capital_receipt_data, limit = capital
        min_strike = current * (1 - max_otm)
        max_strike = min(current * (1 - min_otm), limit / 100)
        if min_strike <= 0.0 or max_strike < min_strike:
            return self._fail("capital_receipt_cannot_cover_requested_contract")
        return self._scan_validated(
            symbol=underlying,
            current_price=underlying_data[1],
            strategy="cash_secured_put",
            option_type=OptionType.PUT,
            min_strike=min_strike,
            max_strike=max_strike,
            min_days_expiry=min_days_expiry,
            max_days_expiry=max_days_expiry,
            underlying_receipt=underlying_data[0],
            level_receipt=level_data[0],
            authorization_receipt=capital_receipt_data,
            now=now,
        )
    def display_opportunities(self, opportunities: List[OptionsOpportunity], top_n: int = 5):
        """Display top opportunities in a formatted table."""
        if not opportunities:
            print("\n❌ No opportunities found")
            return
        
        print(f"\n{'='*90}")
        print(f"{'👑 TOP OPTIONS OPPORTUNITIES':^90}")
        print(f"{'='*90}")
        
        print(f"\n{'Symbol':<25} {'Strike':<10} {'Exp':<12} {'Bid/Ask':<15} {'Score':<8} {'Ann.Ret':<10}")
        print("-" * 90)
        
        for opp in opportunities[:top_n]:
            c = opp.contract
            q = opp.quote
            
            bid_ask = f"${q.bid:.2f}/${q.ask:.2f}"
            ann_ret = f"{opp.annualized_return*100:.1f}%" if opp.annualized_return > 0 else "N/A"
            
            print(f"{c.symbol:<25} ${c.strike_price:<9.2f} {c.expiration_date:<12} {bid_ask:<15} {opp.total_score:.2f}    {ann_ret:<10}")
        
        # Show best opportunity details
        if opportunities:
            best = opportunities[0]
            print(f"\n{'='*90}")
            print(f"{'🏆 BEST OPPORTUNITY':^90}")
            print(f"{'='*90}")
            print(f"\n📊 {best.contract.symbol}")
            print(f"   Strategy: {best.strategy.upper()}")
            print(f"   Strike: ${best.contract.strike_price:.2f}")
            print(f"   Expiration: {best.contract.expiration_date} ({best.days_to_expiry} days)")
            print(f"   Premium: ${best.quote.mid_price:.2f} per share (${best.quote.mid_price*100:.2f} per contract)")
            print(f"\n   Max Profit: ${best.max_profit:.2f}")
            print(f"   Max Risk: ${best.max_risk:.2f}")
            print(f"   Breakeven: ${best.breakeven:.2f}")
            print(f"   Annualized Return: {best.annualized_return*100:.1f}%")
            print(f"\n   📈 Scores:")
            print(f"      Premium Score: {best.premium_score:.2f}")
            print(f"      Spread Score: {best.spread_score:.2f}")
            print(f"      Volume Score: {best.volume_score:.2f}")
            print(f"      Theta Score: {best.theta_score:.2f}")
            print(f"      TOTAL SCORE: {best.total_score:.2f}")
            if best.queen_confidence is not None and best.queen_confidence > 0:
                print(f"      👑 Queen Confidence: {best.queen_confidence:.1%}")


# ═══════════════════════════════════════════════════════════════════════════════
# QUICK ACCESS
# ═══════════════════════════════════════════════════════════════════════════════

def scan_options(
    symbol: str,
    strategy: str = "all",
    *,
    scanner: Optional[QueenOptionsScanner] = None,
    current_price: Optional[float] = None,
    underlying_receipt: Optional[Mapping[str, Any]] = None,
    position_receipt: Optional[Mapping[str, Any]] = None,
    capital_receipt: Optional[Mapping[str, Any]] = None,
    trading_level_receipt: Optional[Mapping[str, Any]] = None,
) -> List[OptionsOpportunity]:
    """Quick access only for an explicitly injected receipt-bearing scanner."""
    if scanner is None or current_price is None:
        return []
    opportunities: List[OptionsOpportunity] = []
    if strategy in {"all", "covered_call"}:
        opportunities.extend(
            scanner.scan_covered_calls(
                symbol,
                current_price,
                underlying_receipt=underlying_receipt,
                position_receipt=position_receipt,
                trading_level_receipt=trading_level_receipt,
            )
        )
    if strategy in {"all", "cash_secured_put"}:
        opportunities.extend(
            scanner.scan_cash_secured_puts(
                symbol,
                current_price,
                underlying_receipt=underlying_receipt,
                capital_receipt=capital_receipt,
                trading_level_receipt=trading_level_receipt,
            )
        )
    opportunities.sort(key=lambda item: float(item.total_score), reverse=True)
    return opportunities


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Describe the injection boundary without creating clients or fetching."""
    import argparse

    parser = argparse.ArgumentParser(description="Receipt-gated Queen options scanner")
    parser.add_argument("symbol", nargs="?", help="Symbol supplied by an injected caller")
    parser.parse_args(argv)
    print(
        "No scan performed: inject Alpaca adapters and complete linked provider "
        "receipts through QueenOptionsScanner."
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

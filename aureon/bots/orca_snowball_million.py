#!/usr/bin/env python3
"""
🏔️❄️ ORCA SNOWBALL TO MILLION ❄️🏔️

Queen-guided autonomous snowball trading system.
Compounds wins relentlessly until $1,000,000.

NO SMOKE. JUST FIRE. REAL TRADES ONLY.
"""

import os
import sys
import json
import time
import math
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

# === SACRED CONSTANTS ===
PHI = 1.618033988749895  # Golden Ratio
MILLION = 1_000_000
LOVE_FREQUENCY = 528  # Hz
MARKET_RECEIPT_MAX_AGE_SECONDS = 120.0
FILL_RECEIPT_MAX_AGE_SECONDS = 300.0

@dataclass
class SnowballState:
    """Current snowball state"""
    starting_value: Optional[float] = None
    current_value: Optional[float] = None
    trades_executed: int = 0
    wins: int = 0
    losses: int = 0
    total_profit: float = 0
    started_at: str = ""
    last_trade: str = ""


def _finite_number(
    value: Any,
    *,
    positive: bool = False,
    nonnegative: bool = False,
) -> Optional[float]:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(parsed):
        return None
    if positive and parsed <= 0:
        return None
    if nonnegative and parsed < 0:
        return None
    return parsed


def _fresh_provider_timestamp(
    value: Any,
    *,
    max_age_seconds: float,
) -> Optional[float]:
    parsed = _finite_number(value, positive=True)
    if parsed is None:
        return None
    if parsed > 10_000_000_000:
        parsed /= 1000.0
    now = time.time()
    if parsed > now + 5.0 or now - parsed > max_age_seconds:
        return None
    return parsed
    
def log_snowball(msg: str):
    print(f"❄️ [SNOWBALL] {msg}")

def log_queen(msg: str):
    print(f"👑 [QUEEN] {msg}")

def log_fire(msg: str):
    print(f"🔥 [FIRE] {msg}")

def log_win(msg: str):
    print(f"💰 [WIN] {msg}")

class QueenSnowball:
    """Queen-guided snowball to million"""
    
    def __init__(
        self,
        kraken: Any = None,
        binance: Any = None,
        *,
        connect_clients: bool = True,
        wire_queen: bool = True,
    ):
        self.state = SnowballState()
        self.state.started_at = datetime.now().isoformat()
        self.data_status = "no_data"
        self.no_data_reason = "provider_receipt_not_requested"
        self.execution_receipts: List[Dict[str, Any]] = []
        self.reconciliation_required: List[Dict[str, Any]] = []
        
        # Load exchange clients
        if connect_clients:
            from aureon.exchanges.kraken_client import get_kraken_client
            from aureon.exchanges.binance_client import get_binance_client
            if kraken is None:
                kraken = get_kraken_client()
            if binance is None:
                try:
                    binance = get_binance_client()
                except Exception:
                    binance = None
        self.kraken = kraken
        self.binance = binance
            
        # Load Queen systems
        if wire_queen:
            self._wire_queen()
        else:
            self.queen = None
            self.nexus = None
            self.brain = None
        
    def _wire_queen(self):
        """Wire Queen intelligence systems"""
        log_queen("Wiring Queen Intelligence Systems...")
        
        try:
            from aureon.utils.aureon_queen_hive_mind import QueenHiveMind
            self.queen = QueenHiveMind()
            log_queen("✅ Queen Hive Mind: ONLINE")
        except Exception as e:
            log_queen(f"⚠️ Queen Hive Mind unavailable: {e}")
            self.queen = None
            
        try:
            from aureon.bridges.aureon_probability_nexus import ProbabilityNexus
            self.nexus = ProbabilityNexus()
            log_queen("✅ Probability Nexus: ONLINE")
        except:
            self.nexus = None
            
        try:
            from aureon.utils.aureon_miner_brain import MinerBrain
            self.brain = MinerBrain()
            log_queen("✅ Miner Brain: ONLINE")
        except:
            self.brain = None

    def _no_data(self, reason: str, **fields: Any) -> Dict[str, Any]:
        self.data_status = "no_data"
        self.no_data_reason = reason
        return {
            "status": "NO_DATA",
            "data_status": "no_data",
            "truth_status": "no_data",
            "reason": reason,
            "generated_values": False,
            "eligible_for_action": False,
            **fields,
        }

    def _balance_receipt(self, client: Any, provider: str) -> Dict[str, Any]:
        """Wrap a synchronous authenticated balance read without timestamp laundering."""
        if client is None:
            return self._no_data(f"{provider}_client_unavailable")
        try:
            raw = client.get_balance()
        except Exception as exc:
            return self._no_data(f"{provider}_balance_receipt_failed:{type(exc).__name__}")
        received_at = time.time()
        if not isinstance(raw, dict) or not raw:
            return self._no_data(f"{provider}_balance_receipt_unavailable")
        balances: Dict[str, float] = {}
        for asset, value in raw.items():
            parsed = _finite_number(value, nonnegative=True)
            asset_name = str(asset or "").upper()
            if not asset_name or parsed is None:
                return self._no_data(f"{provider}_balance_receipt_malformed")
            balances[asset_name] = parsed
        return {
            "status": "LIVE",
            "data_status": "live",
            "truth_status": "real_provider",
            "balances": balances,
            "source_id": f"{provider}:authenticated_balance",
            "source_timestamp": None,
            "received_at": received_at,
            "timestamp_policy": "synchronous_provider_receipt_clock_not_source_time",
            "generated_values": False,
            "eligible_for_action": True,
        }

    def _binance_asset_receipt(self, asset: str) -> Dict[str, Any]:
        if self.binance is None or not hasattr(self.binance, "get_asset_balance"):
            return self._no_data("binance_timestamped_balance_receipt_unavailable")
        try:
            receipt = self.binance.get_asset_balance(asset)
        except Exception as exc:
            return self._no_data(f"binance_balance_receipt_failed:{type(exc).__name__}")
        if not isinstance(receipt, dict):
            return self._no_data(f"binance_{asset.lower()}_balance_receipt_unavailable")
        free = _finite_number(receipt.get("free"), nonnegative=True)
        source_timestamp = _fresh_provider_timestamp(
            receipt.get("source_timestamp"),
            max_age_seconds=FILL_RECEIPT_MAX_AGE_SECONDS,
        )
        if (
            free is None
            or source_timestamp is None
            or receipt.get("data_status") != "live"
            or receipt.get("eligible_for_action") is not True
            or receipt.get("generated_values") is not False
        ):
            return self._no_data(f"binance_{asset.lower()}_balance_receipt_incomplete")
        return {
            **receipt,
            "free": free,
            "source_timestamp": source_timestamp,
        }

    def _market_receipt(
        self,
        raw: Any,
        *,
        expected_symbol: str,
        required_fields: tuple[str, ...],
    ) -> Optional[Dict[str, Any]]:
        if not isinstance(raw, dict) or raw.get("generated_values") is True:
            return None
        if raw.get("generated_values") is None and "closeTime" not in raw:
            return None
        source_timestamp = _fresh_provider_timestamp(
            raw.get("source_timestamp") or raw.get("closeTime"),
            max_age_seconds=MARKET_RECEIPT_MAX_AGE_SECONDS,
        )
        symbol = str(raw.get("symbol") or "").upper()
        if symbol != expected_symbol.upper() or source_timestamp is None:
            return None
        normalized: Dict[str, Any] = {
            "symbol": symbol,
            "source_id": raw.get("source_id") or f"provider:ticker:{symbol}",
            "source_timestamp": source_timestamp,
            "data_status": "live",
            "truth_status": raw.get("truth_status") or "real_provider",
            "generated_values": False,
            "eligible_for_action": True,
        }
        aliases = {
            "price": ("price", "lastPrice"),
            "change_24h": ("priceChangePercent",),
            "volume": ("quoteVolume",),
            "high_24h": ("high_24h", "high"),
            "low_24h": ("low_24h", "low"),
        }
        for field in required_fields:
            keys = aliases[field]
            value = None
            for key in keys:
                if key in raw:
                    value = raw[key]
                    break
            parsed = _finite_number(
                value,
                positive=field in {"price", "high_24h", "low_24h"},
                nonnegative=field == "volume",
            )
            if parsed is None:
                return None
            normalized[field] = parsed
        return normalized

    def _opportunity_is_actionable(self, opportunity: Any) -> bool:
        if not isinstance(opportunity, dict):
            return False
        if (
            opportunity.get("data_status") != "live"
            or opportunity.get("generated_values") is not False
            or opportunity.get("eligible_for_action") is not True
            or _finite_number(opportunity.get("price"), positive=True) is None
        ):
            return False
        return _fresh_provider_timestamp(
            opportunity.get("source_timestamp"),
            max_age_seconds=MARKET_RECEIPT_MAX_AGE_SECONDS,
        ) is not None

    def _pending_reconciliation(
        self,
        provider: str,
        symbol: str,
        side: str,
        reason: str,
        *,
        order_id: Any = None,
    ) -> Dict[str, Any]:
        receipt = {
            "status": "PENDING_RECONCILIATION",
            "data_status": "pending_reconciliation",
            "truth_status": "pending_reconciliation",
            "provider": provider,
            "symbol": symbol,
            "side": side,
            "order_id": str(order_id) if order_id not in (None, "") else None,
            "reason": reason,
            "fill_receipt_complete": False,
            "eligible_for_accounting": False,
            "generated_values": False,
        }
        self.reconciliation_required.append(receipt)
        return receipt

    def _not_submitted(
        self,
        provider: str,
        symbol: str,
        side: str,
        reason: str,
    ) -> Dict[str, Any]:
        receipt = {
            "status": "NOT_SUBMITTED",
            "data_status": "not_submitted",
            "truth_status": "not_submitted",
            "provider": provider,
            "symbol": symbol,
            "side": side,
            "reason": reason,
            "fill_receipt_complete": False,
            "eligible_for_accounting": False,
            "generated_values": False,
        }
        self.execution_receipts.append(receipt)
        return receipt

    def _validated_kraken_fill(
        self,
        receipt: Any,
        *,
        symbol: str,
        side: str,
    ) -> Optional[Dict[str, Any]]:
        if not isinstance(receipt, dict):
            return None
        source_timestamp = _fresh_provider_timestamp(
            receipt.get("provider_timestamp") or receipt.get("source_timestamp"),
            max_age_seconds=FILL_RECEIPT_MAX_AGE_SECONDS,
        )
        executed_qty = _finite_number(receipt.get("executedQty"), positive=True)
        price = _finite_number(receipt.get("filled_avg_price"), positive=True)
        quote_qty = _finite_number(receipt.get("cummulativeQuoteQty"), positive=True)
        fee = _finite_number(receipt.get("fee"), nonnegative=True)
        fee_asset = str(receipt.get("fee_asset") or "").upper()
        receipt_side = str(receipt.get("side") or side).upper()
        order_id = receipt.get("orderId") or receipt.get("order_id")
        if (
            receipt.get("status") != "FILLED"
            or receipt.get("data_status") != "live"
            or receipt.get("fill_receipt_complete") is not True
            or receipt.get("eligible_for_accounting") is not True
            or receipt.get("generated_values") is not False
            or source_timestamp is None
            or executed_qty is None
            or price is None
            or quote_qty is None
            or fee is None
            or not fee_asset
            or receipt_side != side.upper()
            or order_id in (None, "")
        ):
            return None
        return {
            "status": "FILLED",
            "provider": "kraken",
            "symbol": symbol,
            "side": side.upper(),
            "order_id": str(order_id),
            "source_id": f"kraken:order:{order_id}",
            "source_timestamp": source_timestamp,
            "executed_qty": executed_qty,
            "average_fill_price": price,
            "quote_qty": quote_qty,
            "fees_by_asset": {fee_asset: fee},
            "fill_receipt_complete": True,
            "eligible_for_accounting": True,
            "data_status": "live",
            "truth_status": "real_provider",
            "generated_values": False,
        }

    def _validated_binance_fill(
        self,
        receipt: Any,
        *,
        symbol: str,
        side: str,
    ) -> Optional[Dict[str, Any]]:
        if not isinstance(receipt, dict) or receipt.get("rejected") is True or receipt.get("dryRun") is True:
            return None
        source_timestamp = _fresh_provider_timestamp(
            receipt.get("transactTime") or receipt.get("updateTime"),
            max_age_seconds=FILL_RECEIPT_MAX_AGE_SECONDS,
        )
        executed_qty = _finite_number(receipt.get("executedQty"), positive=True)
        quote_qty = _finite_number(receipt.get("cummulativeQuoteQty"), positive=True)
        fills = receipt.get("fills")
        order_id = receipt.get("orderId")
        if (
            str(receipt.get("symbol") or "").upper() != symbol.upper()
            or str(receipt.get("side") or "").upper() != side.upper()
            or receipt.get("status") != "FILLED"
            or source_timestamp is None
            or executed_qty is None
            or quote_qty is None
            or not isinstance(fills, list)
            or not fills
            or order_id in (None, "")
        ):
            return None
        fill_qty = 0.0
        fill_quote = 0.0
        fees_by_asset: Dict[str, float] = {}
        for fill in fills:
            if not isinstance(fill, dict):
                return None
            qty = _finite_number(fill.get("qty"), positive=True)
            price = _finite_number(fill.get("price"), positive=True)
            fee = _finite_number(fill.get("commission"), nonnegative=True)
            fee_asset = str(fill.get("commissionAsset") or "").upper()
            if qty is None or price is None or fee is None or not fee_asset:
                return None
            fill_qty += qty
            fill_quote += qty * price
            fees_by_asset[fee_asset] = fees_by_asset.get(fee_asset, 0.0) + fee
        qty_tolerance = max(1e-12, executed_qty * 1e-8)
        quote_tolerance = max(1e-12, quote_qty * 1e-8)
        if abs(fill_qty - executed_qty) > qty_tolerance or abs(fill_quote - quote_qty) > quote_tolerance:
            return None
        return {
            "status": "FILLED",
            "provider": "binance",
            "symbol": symbol,
            "side": side.upper(),
            "order_id": str(order_id),
            "source_id": f"binance:order:{order_id}",
            "source_timestamp": source_timestamp,
            "executed_qty": executed_qty,
            "average_fill_price": quote_qty / executed_qty,
            "quote_qty": quote_qty,
            "fees_by_asset": fees_by_asset,
            "fill_receipt_complete": True,
            "eligible_for_accounting": True,
            "data_status": "live",
            "truth_status": "real_provider",
            "generated_values": False,
        }

    def _record_fill(self, receipt: Dict[str, Any]) -> Dict[str, Any]:
        self.execution_receipts.append(receipt)
        self.state.trades_executed += 1
        self.state.last_trade = datetime.fromtimestamp(
            receipt["source_timestamp"],
            tz=timezone.utc,
        ).isoformat()
        self.data_status = "live"
        self.no_data_reason = ""
        return receipt
            
    def get_total_portfolio_usd(self) -> Optional[float]:
        """Value every observed balance through fresh provider FX receipts."""
        kraken_receipt = self._balance_receipt(self.kraken, "kraken")
        if kraken_receipt.get("data_status") != "live":
            return None
        total_usd = 0.0
        for asset, qty in kraken_receipt["balances"].items():
            if qty <= 0:
                continue
            if asset in {"USD", "ZUSD"}:
                total_usd += qty
                continue
            pair = f"{asset}USD"
            try:
                raw_ticker = self.kraken.get_24h_ticker(pair)
            except Exception:
                return None
            ticker = self._market_receipt(
                raw_ticker,
                expected_symbol=pair,
                required_fields=("price",),
            )
            if ticker is None:
                self._no_data(f"kraken_{pair.lower()}_valuation_receipt_unavailable")
                return None
            total_usd += qty * ticker["price"]

        if self.binance is not None:
            binance_receipt = self._balance_receipt(self.binance, "binance")
            if binance_receipt.get("data_status") != "live":
                return None
            total_usdt = 0.0
            for asset, qty in binance_receipt["balances"].items():
                if qty <= 0:
                    continue
                if asset == "USDT":
                    total_usdt += qty
                    continue
                pair = f"{asset}USDT"
                try:
                    raw_ticker = self.binance.get_24h_ticker(pair)
                except Exception:
                    return None
                ticker = self._market_receipt(
                    raw_ticker,
                    expected_symbol=pair,
                    required_fields=("price",),
                )
                if ticker is None:
                    self._no_data(f"binance_{pair.lower()}_valuation_receipt_unavailable")
                    return None
                total_usdt += qty * ticker["price"]
            if total_usdt > 0:
                try:
                    raw_fx = self.kraken.get_24h_ticker("USDTUSD")
                except Exception:
                    return None
                fx_receipt = self._market_receipt(
                    raw_fx,
                    expected_symbol="USDTUSD",
                    required_fields=("price",),
                )
                if fx_receipt is None:
                    self._no_data("usdt_usd_fx_receipt_unavailable")
                    return None
                total_usd += total_usdt * fx_receipt["price"]

        self.data_status = "live"
        self.no_data_reason = ""
        return total_usd
        
    def queen_decide(self, opportunities: List[Dict]) -> Optional[Dict]:
        """Let Queen decide best opportunity"""
        if not opportunities:
            return None
            
        # Score each opportunity
        scored = []
        for opp in opportunities:
            if not self._opportunity_is_actionable(opp):
                continue
            score = _finite_number(opp.get('score'), nonnegative=True)
            if score is None:
                continue
            
            # Queen boost for positive momentum
            change_24h = _finite_number(opp.get('change_24h'))
            if change_24h is not None and change_24h > 5:
                score *= 1.2
                
            # Queen boost for high volume
            volume = _finite_number(opp.get('volume'), nonnegative=True)
            if volume is not None and volume > 1000000:
                score *= 1.1
                
            # Nexus validation
            if self.nexus:
                try:
                    validation = self.nexus.quick_validate(opp.get('symbol', ''))
                    probability = _finite_number(
                        validation.get('probability') if isinstance(validation, dict) else None
                    )
                    if probability is not None and probability > 0.6:
                        score *= 1.3
                except:
                    pass
                    
            scored.append((score, opp))
            
        # Sort by score
        scored.sort(key=lambda x: x[0], reverse=True)
        
        if scored:
            best_score, best_opp = scored[0]
            if best_score >= 3:  # Minimum threshold
                log_queen(f"👑 Queen selects: {best_opp.get('symbol')} (score: {best_score:.2f})")
                return best_opp
                
        return None
        
    def scan_kraken_opportunities(self) -> List[Dict]:
        """Scan Kraken for opportunities"""
        opportunities = []
        
        # Top pairs to scan
        pairs = ['BTCUSD', 'ETHUSD', 'SOLUSD', 'XRPUSD', 'DOGEUSD', 'ADAUSD', 
                 'AVAXUSD', 'LINKUSD', 'DOTUSD', 'MATICUSD']
        
        for pair in pairs:
            try:
                raw_ticker = self.kraken.get_24h_ticker(pair)
                ticker = self._market_receipt(
                    raw_ticker,
                    expected_symbol=pair,
                    required_fields=("price", "high_24h", "low_24h"),
                )
                if ticker is None:
                    continue
                price = ticker["price"]
                high = ticker["high_24h"]
                low = ticker["low_24h"]
                if high <= low or price < low or price > high:
                    continue
                
                # Calculate metrics
                range_pct = (high - low) / low * 100
                position_in_range = (price - low) / (high - low) * 100
                
                # Score: higher volatility + lower in range = better buy
                score = (range_pct / 10) + ((100 - position_in_range) / 20)
                
                # Momentum check - if near low, good buy opportunity
                if position_in_range < 30:  # In lower 30% of range
                    score += 3
                    
                opportunities.append({
                    'symbol': pair,
                    'exchange': 'kraken',
                    'price': price,
                    'high_24h': high,
                    'low_24h': low,
                    'range_pct': range_pct,
                    'position_in_range': position_in_range,
                    'score': score,
                    'action': 'BUY',
                    'source_id': ticker["source_id"],
                    'source_timestamp': ticker["source_timestamp"],
                    'data_status': "live",
                    'generated_values': False,
                    'eligible_for_action': True,
                })
                
            except Exception as e:
                pass
                
        return sorted(opportunities, key=lambda x: x['score'], reverse=True)
        
    def scan_binance_momentum(self) -> List[Dict]:
        """Scan Binance for momentum plays"""
        if not self.binance:
            return []
            
        opportunities = []
        
        try:
            # Get all tickers
            tickers = self.binance.get_24h_tickers()
            if not isinstance(tickers, list):
                return []
            
            for raw_ticker in tickers[:100]:  # Top 100 provider rows
                if not isinstance(raw_ticker, dict):
                    continue
                symbol = str(raw_ticker.get('symbol') or '').upper()
                if not symbol.endswith('USDT'):
                    continue
                ticker = self._market_receipt(
                    raw_ticker,
                    expected_symbol=symbol,
                    required_fields=("price", "change_24h", "volume"),
                )
                if ticker is None:
                    continue
                change = ticker["change_24h"]
                volume = ticker["volume"]
                price = ticker["price"]
                
                if volume < 100000:
                    continue
                    
                # Check if we can trade it
                permission = self.binance.can_trade_symbol(symbol)
                allowed = permission[0] is True if isinstance(permission, tuple) else permission is True
                if not allowed:
                    continue
                    
                # Score momentum
                score = 0
                
                # Strong uptrend
                if 5 < change < 30:
                    score = change / 5
                    
                # High volume confirms
                if volume > 1000000:
                    score *= 1.2
                    
                if score >= 3:
                    opportunities.append({
                        'symbol': symbol,
                        'exchange': 'binance',
                        'price': price,
                        'change_24h': change,
                        'volume': volume,
                        'score': score,
                        'action': 'BUY',
                        'source_id': ticker["source_id"],
                        'source_timestamp': ticker["source_timestamp"],
                        'data_status': "live",
                        'generated_values': False,
                        'eligible_for_action': True,
                    })
                    
        except Exception as e:
            log_snowball(f"Binance scan error: {e}")
            
        return sorted(opportunities, key=lambda x: x['score'], reverse=True)
        
    def execute_trade(self, opportunity: Dict) -> Dict:
        """Execute a trade"""
        if not self._opportunity_is_actionable(opportunity):
            return self._no_data("fresh_complete_opportunity_receipt_required")
        exchange = opportunity.get('exchange')
        symbol = opportunity.get('symbol')
        action = opportunity.get('action')
        if action not in {"BUY", "SELL"} or not isinstance(symbol, str) or not symbol:
            return self._no_data("complete_trade_instruction_required")
        
        log_fire(f"⚡ EXECUTING: {action} {symbol} on {exchange}")
        
        if exchange == 'kraken':
            return self._execute_kraken(opportunity)
        elif exchange == 'binance':
            return self._execute_binance(opportunity)
        else:
            return self._no_data("unknown_exchange")

    def _resolve_kraken_fill(
        self,
        submission: Any,
        *,
        symbol: str,
        side: str,
    ) -> Dict[str, Any]:
        if isinstance(submission, dict) and (
            submission.get("dryRun") is True
            or str(submission.get("status") or "").lower() == "not_submitted"
        ):
            return self._not_submitted(
                "kraken",
                symbol,
                side,
                "provider_order_not_submitted",
            )
        fill = self._validated_kraken_fill(submission, symbol=symbol, side=side)
        if fill is not None:
            return self._record_fill(fill)
        order_id = None
        if isinstance(submission, dict):
            order_id = submission.get("orderId") or submission.get("order_id")
        if order_id not in (None, "") and hasattr(self.kraken, "get_order_status"):
            try:
                terminal = self.kraken.get_order_status(str(order_id))
            except Exception as exc:
                return self._pending_reconciliation(
                    "kraken",
                    symbol,
                    side,
                    f"order_query_failed:{type(exc).__name__}",
                    order_id=order_id,
                )
            fill = self._validated_kraken_fill(terminal, symbol=symbol, side=side)
            if fill is not None:
                return self._record_fill(fill)
        return self._pending_reconciliation(
            "kraken",
            symbol,
            side,
            "fresh_complete_terminal_fill_receipt_required",
            order_id=order_id,
        )
            
    def _execute_kraken(self, opp: Dict) -> Dict:
        """Execute on Kraken"""
        try:
            symbol = str(opp['symbol']).upper()
            price = _finite_number(opp.get('price'), positive=True)
            action = opp.get('action')
            if price is None or action not in {"BUY", "SELL"}:
                return self._no_data("complete_kraken_trade_instruction_required")
            
            # Get USD balance
            balance_receipt = self._balance_receipt(self.kraken, "kraken")
            if balance_receipt.get("data_status") != "live":
                return balance_receipt
            balances = balance_receipt["balances"]
            
            if action == 'BUY':
                usd_balance = balances["USD"] if "USD" in balances else balances.get("ZUSD")
                usd_balance = _finite_number(usd_balance, nonnegative=True)
                if usd_balance is None:
                    return self._no_data("kraken_usd_balance_receipt_unavailable")
                if usd_balance < 5:
                    return {'status': 'NO_FUNDS', 'balance': usd_balance}
                    
                # Use 50% of available USD (snowball rule)
                trade_usd = usd_balance * 0.5
                volume = trade_usd / price
                    
                log_fire(f"   💵 Using ${trade_usd:.2f} to buy {volume} {symbol}")
                
                result = self.kraken.place_market_order(symbol, 'buy', volume)
                receipt = self._resolve_kraken_fill(
                    result,
                    symbol=symbol,
                    side="BUY",
                )
                if receipt.get("status") == "FILLED":
                    log_win(f"💥 PROVIDER FILL VERIFIED: {symbol}")
                return receipt
                    
            elif action == 'SELL':
                # Get asset balance
                if not symbol.endswith("USD") or len(symbol) <= 3:
                    return self._no_data("unsupported_kraken_sell_symbol")
                asset = symbol[:-3]
                asset_balance = _finite_number(
                    balances[asset] if asset in balances else None,
                    nonnegative=True,
                )
                
                if asset_balance is None:
                    return self._no_data("kraken_asset_balance_receipt_unavailable", asset=asset)
                if asset_balance <= 0:
                    return {'status': 'NO_ASSET', 'asset': asset}
                    
                # Sell 50% (snowball - keep compounding)
                sell_qty = asset_balance * 0.5
                
                result = self.kraken.place_market_order(symbol, 'sell', sell_qty)
                receipt = self._resolve_kraken_fill(
                    result,
                    symbol=symbol,
                    side="SELL",
                )
                if receipt.get("status") == "FILLED":
                    log_win(f"💥 PROVIDER FILL VERIFIED: {symbol}")
                return receipt
                    
        except Exception as e:
            log_fire(f"❌ Kraken error: {e}")
            return self._pending_reconciliation(
                "kraken",
                str(opp.get("symbol") or ""),
                str(opp.get("action") or ""),
                f"submission_or_reconciliation_failed:{type(e).__name__}",
            )
            
    def _execute_binance(self, opp: Dict) -> Dict:
        """Execute on Binance"""
        if not self.binance:
            return {'status': 'NO_CLIENT'}
            
        try:
            symbol = str(opp['symbol']).upper()
            price = _finite_number(opp.get('price'), positive=True)
            if price is None or opp.get("action") != "BUY":
                return self._no_data("complete_binance_buy_instruction_required")
            
            # Get USDT balance
            balance_receipt = self._binance_asset_receipt("USDT")
            if balance_receipt.get("data_status") != "live":
                return balance_receipt
            usdt = balance_receipt["free"]
            
            if usdt < 5:
                return {'status': 'NO_FUNDS', 'balance': usdt}
                
            # Use 50% for snowball compounding
            trade_usd = usdt * 0.5
            volume = trade_usd / price
            
            # Adjust for Binance lot size
            volume = self.binance.adjust_quantity(symbol, volume)
            volume = _finite_number(volume, positive=True)
            if volume is None:
                return self._no_data("binance_lot_size_receipt_unavailable")
            
            log_fire(f"   💵 Using ${trade_usd:.2f} to buy {volume} {symbol}")
            
            result = self.binance.place_market_order(symbol, 'BUY', quantity=volume)
            if isinstance(result, dict) and (
                result.get("dryRun") is True
                or str(result.get("status") or "").lower() == "not_submitted"
            ):
                return self._not_submitted(
                    "binance",
                    symbol,
                    "BUY",
                    "provider_order_not_submitted",
                )
            if isinstance(result, dict) and result.get("rejected") is True:
                return {
                    "status": "REJECTED",
                    "data_status": "live",
                    "reason": str(result.get("reason") or "provider_or_preflight_rejected"),
                    "generated_values": False,
                    "eligible_for_accounting": False,
                }
            receipt = self._validated_binance_fill(
                result,
                symbol=symbol,
                side="BUY",
            )
            if receipt is None:
                return self._pending_reconciliation(
                    "binance",
                    symbol,
                    "BUY",
                    "fresh_complete_terminal_fill_receipt_required",
                    order_id=result.get("orderId") if isinstance(result, dict) else None,
                )
            log_win(f"💥 PROVIDER FILL VERIFIED: {symbol}")
            return self._record_fill(receipt)
                
        except Exception as e:
            log_fire(f"❌ Binance error: {e}")
            return self._pending_reconciliation(
                "binance",
                str(opp.get("symbol") or ""),
                "BUY",
                f"submission_or_reconciliation_failed:{type(e).__name__}",
            )
            
    def check_positions_for_profit(self) -> Dict[str, Any]:
        """Never infer profit from 24h range or treat gross proceeds as PnL."""
        log_snowball("NO_DATA: provider cost-basis receipts required for profit-taking")
        return self._no_data(
            "provider_cost_basis_and_fee_receipts_required_for_profit_taking"
        )
            
    def run_cycle(self):
        """Run one snowball cycle"""
        log_snowball("=" * 60)
        log_snowball(f"   SNOWBALL CYCLE - {datetime.now().strftime('%H:%M:%S')}")
        log_snowball("=" * 60)
        
        # Get current portfolio value
        portfolio_value = self.get_total_portfolio_usd()
        if portfolio_value is None:
            self.state.current_value = None
            log_snowball(f"NO_DATA: {self.no_data_reason}")
            self._save_state()
            return False
        self.state.current_value = portfolio_value
        
        if self.state.starting_value is None:
            self.state.starting_value = portfolio_value
            
        # Progress to million
        progress = (portfolio_value / MILLION) * 100
        if portfolio_value <= 0:
            log_snowball("Portfolio receipt reports zero; no doubling path or action is available")
            self._save_state()
            return False
        doublings_needed = 0
        temp = portfolio_value
        while temp < MILLION:
            temp *= 2
            doublings_needed += 1
            
        log_snowball(f"💰 Portfolio: ${portfolio_value:.2f}")
        log_snowball(f"🎯 Target: ${MILLION:,}")
        log_snowball(f"📊 Progress: {progress:.6f}%")
        log_snowball(f"🔄 Doublings needed: {doublings_needed}")
        
        if portfolio_value >= MILLION:
            log_snowball("🏆🏆🏆 MILLION REACHED! 🏆🏆🏆")
            return True
            
        # Step 1: Check positions for profit-taking
        self.check_positions_for_profit()
        
        # Step 2: Scan for new opportunities
        log_snowball("\n🔍 Scanning markets...")
        
        kraken_opps = self.scan_kraken_opportunities()
        binance_opps = self.scan_binance_momentum()
        
        all_opps = kraken_opps[:5] + binance_opps[:5]
        
        log_snowball(f"   Found {len(all_opps)} opportunities")
        
        # Step 3: Queen decides
        best = self.queen_decide(all_opps)
        
        if best:
            # Step 4: Execute
            result = self.execute_trade(best)
            
            if result.get('status') == 'FILLED':
                log_win("✅ Trade executed successfully!")
            else:
                log_snowball(f"⚠️ Trade result: {result.get('status')}")
        else:
            log_queen("👑 Queen says: Wait for better opportunity")
            
        # Update the local ledger. last_trade is written only by a provider fill.
        self._save_state()
        
        return False
        
    def _save_state(self):
        """Save snowball state"""
        try:
            with open('snowball_state.json', 'w') as f:
                json.dump({
                    'starting_value': self.state.starting_value,
                    'current_value': self.state.current_value,
                    'trades_executed': self.state.trades_executed,
                    'wins': self.state.wins,
                    'losses': self.state.losses,
                    'total_profit': self.state.total_profit,
                    'started_at': self.state.started_at,
                    'last_trade': self.state.last_trade,
                    'updated_at': datetime.now().isoformat()
                }, f, indent=2)
        except:
            pass
            
    def run_forever(self, cycle_seconds: int = 60):
        """Run snowball forever until million"""
        print()
        print("🏔️" + "❄️" * 30 + "🏔️")
        print("   ORCA SNOWBALL TO MILLION")
        print("   Queen-Guided Autonomous Trading")
        print("🏔️" + "❄️" * 30 + "🏔️")
        print()
        
        log_queen("👑 Queen's Snowball Protocol ACTIVATED")
        log_queen(f"   Target: ${MILLION:,}")
        log_queen(f"   Cycle: Every {cycle_seconds}s")
        log_queen("   Strategy: Compound wins relentlessly")
        print()
        
        cycle = 0
        while True:
            cycle += 1
            
            try:
                reached_million = self.run_cycle()
                
                if reached_million:
                    log_snowball("🎉🎉🎉 CONGRATULATIONS! MILLION ACHIEVED! 🎉🎉🎉")
                    break
                    
            except KeyboardInterrupt:
                log_snowball("\n⏸️ Snowball paused by user")
                break
            except Exception as e:
                log_snowball(f"❌ Cycle error: {e}")
                
            # Wait for next cycle
            log_snowball(f"\n⏳ Next cycle in {cycle_seconds}s...")
            time.sleep(cycle_seconds)
            

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Orca Snowball to Million")
    parser.add_argument('--cycle', type=int, default=60, help='Seconds between cycles')
    parser.add_argument('--once', action='store_true', help='Run single cycle')
    args = parser.parse_args()
    
    snowball = QueenSnowball()
    
    if args.once:
        snowball.run_cycle()
    else:
        snowball.run_forever(cycle_seconds=args.cycle)
        

if __name__ == '__main__':
    main()

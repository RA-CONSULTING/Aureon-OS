"""
Aureon Dual Capital Connector

Manages BOTH demo and live Capital.com sessions simultaneously.

Architecture:
  - SHADOWS: Trades on DEMO account (risk-free validation)
  - HONEY POT: Trades on LIVE account (real money, proven shadows only)

A shadow must hit its profit target in DEMO before graduating to LIVE.

Gary Leckey | 2026 | Validate in demo, earn in live
"""

import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Dict, Optional

# Import the CapitalClient
from capital_client import CapitalClient

# Normalized <-> Capital-native price scaling (e.g. NATURALGAS 2975 ↔ 2.975)
try:
    from aureon_price_feed import CAPITAL_SCALE
except Exception:
    CAPITAL_SCALE = {
        "USDJPY": 0.01,
        "EURUSD": 0.0001,
        "GBPUSD": 0.0001,
        "NATURALGAS": 0.001,
        "AAPL": 0.01,
        "TSLA": 0.01,
        "NVDA": 0.01,
    }

logger = logging.getLogger(__name__)


def _scaled_to_native(symbol: str, value: float) -> float:
    """Convert a normalized (Yahoo-consistent) price/level to Capital.com native units."""
    if value is None:
        return None
    scale = CAPITAL_SCALE.get(symbol.upper(), 1.0)
    if scale == 0:
        return float(value)
    return float(value) / scale


def _native_to_scaled(symbol: str, value: float) -> float:
    """Convert a Capital.com native price/level to normalized (Yahoo-consistent) units."""
    if value is None:
        return None
    scale = CAPITAL_SCALE.get(symbol.upper(), 1.0)
    return float(value) * scale


def _round_native_level(symbol: str, value: float) -> float:
    """Round an absolute native price level to Capital.com's expected precision."""
    if value is None:
        return None
    symbol = symbol.upper()
    if symbol in ("EURUSD", "GBPUSD"):
        return round(float(value), 0)
    if symbol == "USDJPY":
        return round(float(value), 0)
    return round(float(value), 1)


class DualCapitalConnector:
    """
    Dual-mode Capital.com connector.
    
    Demo session: For shadow trades (validation)
    Live session: For honey pot trades (real money)
    """
    
    def __init__(self):
        # Demo connector
        os.environ['CAPITAL_DEMO'] = '1'
        self.demo = CapitalClient()
        
        # Live connector  
        os.environ['CAPITAL_DEMO'] = '0'
        self.live = CapitalClient()
        
        # Expose authenticated property for backward compat
        self.authenticated = False
        
        logger.info("[DUAL CAPITAL] Demo + Live connectors initialized")
    
    def authenticate(self) -> bool:
        """Authenticate both demo and live sessions."""
        demo_ok = self.demo.authenticate() if hasattr(self.demo, 'authenticate') else False
        live_ok = self.live.authenticate() if hasattr(self.live, 'authenticate') else False
        self.authenticated = live_ok
        return live_ok
    
    def is_demo_ready(self) -> bool:
        return self.demo.enabled and self.demo.x_security_token is not None
    
    def is_live_ready(self) -> bool:
        return self.live.enabled and self.live.x_security_token is not None
    
    def get_demo_balance(self) -> float:
        try:
            accounts = self.demo.get_accounts()
            if accounts:
                acc = accounts[0]
                return float(acc.get('available', acc.get('balance', 0)))
        except Exception:
            pass
        return 0.0

    def get_live_balance(self) -> float:
        try:
            accounts = self.live.get_accounts()
            if accounts:
                acc = accounts[0]
                return float(acc.get('available', acc.get('balance', 0)))
        except Exception:
            pass
        return 0.0
    
    def place_demo_order(self, symbol: str, direction: str, size: float,
                         stop_level=None, profit_level=None) -> dict:
        """Place a shadow trade on DEMO account."""
        return self._place_order(self.demo, symbol, direction, size, stop_level, profit_level)
    
    def place_live_order(self, symbol: str, direction: str, size: float,
                         stop_level=None, profit_level=None) -> dict:
        """Place a honey pot trade on LIVE account.

        FAIL-CLOSED hardening (owner decree 2026-09-04):
          1. Capability gate `trading_execution:execute_live_trades` must
             ALLOW — checked BEFORE any network call. Gate module error,
             missing gate, or HOLD verdict → order refused.
          2. A broker-side stop level is MANDATORY — None → refused.
        """
        if not self._live_trade_gate_allowed(f"{symbol} {direction} size={size}"):
            return {"error": "refused_by_capability_gate"}

        if stop_level is None:
            logger.error(
                "[GATE] REFUSED live order (%s %s size=%s): mandatory broker-side "
                "stop loss missing [fail-closed]", symbol, direction, size)
            self._emit_gate_refused({
                "gate": "trading_execution:execute_live_trades",
                "verdict": "REFUSED",
                "allowed": False,
                "reason": "mandatory stop loss missing (stop_level=None)",
                "context": f"{symbol} {direction} size={size}",
            })
            return {"error": "refused_missing_stop_loss"}

        return self._place_order(self.live, symbol, direction, size, stop_level, profit_level)

    @staticmethod
    def _workspace_root() -> Path:
        return Path(__file__).resolve().parent.parent

    def _emit_gate_refused(self, payload: dict):
        """Best-effort trading.gate_refused event — never raises."""
        try:
            root = str(self._workspace_root())
            if root not in sys.path:
                sys.path.insert(0, root)
            from aureon_fusion import events
            events.publish_event("trading", "trading.gate_refused", payload, priority=7)
        except Exception:
            pass  # event spine unavailable — refusal already logged

    def _live_trade_gate_allowed(self, context: str) -> bool:
        """Fail-closed capability gate check for LIVE order placement.

        Returns True only if aureon_fusion.capability_gate.check() says
        allowed=True. ANY error (module missing, import failure, exception)
        → refuse. Runs BEFORE any broker network activity.
        """
        gate_key = "trading_execution:execute_live_trades"
        try:
            root = str(self._workspace_root())
            if root not in sys.path:
                sys.path.insert(0, root)
            from aureon_fusion import capability_gate
            verdict = capability_gate.check(gate_key)
        except Exception as e:
            logger.error(
                "[GATE] capability_gate unavailable/error (%s) — REFUSING live "
                "order (%s) [fail-closed]", e, context)
            self._emit_gate_refused({
                "gate": gate_key,
                "verdict": "ERROR",
                "allowed": False,
                "reason": f"capability_gate check raised: {e}",
                "context": context,
            })
            return False

        if not verdict.get("allowed"):
            logger.warning(
                "[GATE] REFUSED live order (%s): verdict=%s level=%s reason=%s",
                context, verdict.get("verdict"), verdict.get("level"),
                verdict.get("reason"))
            self._emit_gate_refused({
                "gate": gate_key,
                "verdict": verdict.get("verdict"),
                "allowed": False,
                "level": verdict.get("level"),
                "reason": verdict.get("reason"),
                "context": context,
            })
            return False

        return True
    
    def _place_order(self, client: CapitalClient, symbol: str, direction: str, 
                     size: float, stop_level=None, profit_level=None) -> dict:
        """Internal order placement with retry logic.
        
        Capital.com CFD sizing:
        - Forex: min size 1.0
        - Stocks: min size 1.0  
        - Commodities: min size 1.0
        - Indices: min size 1.0
        """
        try:
            # Get epic from symbol
            epic = self._symbol_to_epic(client, symbol)
            if not epic:
                return {"error": f"No epic for {symbol}"}
            
            # Determine category for sizing
            category = self._get_symbol_category(symbol)
            
            # Capital.com `size` is in lots. The minimum lot size comes from
            # the instrument's dealingRules when available; otherwise fall back
            # to conservative defaults.
            rules = self._get_dealing_rules(symbol)
            min_deal_size = float(rules.get('minDealSize')) if rules and rules.get('minDealSize') else None
            min_size = min_deal_size if min_deal_size else {
                "forex": 0.01,
                "stock": 0.01,
                "commodity": 0.01,
                "index": 0.001,
                "crypto": 0.01,
            }.get(category, 0.01)
            # Per-symbol overrides from observed API data
            min_size = max(min_size, {"US100": 0.001}.get(symbol.upper(), 0.0))
            
            # Ensure size meets minimum
            actual_size = max(float(size), min_size)
            
            # Build order payload
            payload = {
                "epic": epic,
                "direction": direction.upper(),  # BUY or SELL
                "size": actual_size,
                "orderType": "MARKET",
                "forceOpen": True,
                "currencyCode": "GBP",
            }
            
            # Capital.com order API expects absolute levels in NATIVE units.
            # The caller passes Yahoo-consistent normalized levels, so convert
            # them back to Capital's native quote units before transmitting.
            native_stop = _round_native_level(symbol, _scaled_to_native(symbol, stop_level))
            native_profit = _round_native_level(symbol, _scaled_to_native(symbol, profit_level))
            if native_stop is not None:
                payload["stopLevel"] = float(native_stop)
            if native_profit is not None:
                payload["profitLevel"] = float(native_profit)

            logger.info(
                "[DUAL CAPITAL] %s order payload: %s %s size=%s TP=%s (native %s) SL=%s (native %s)",
                "live" if not client.demo_mode else "demo",
                symbol, direction.upper(), actual_size,
                profit_level, native_profit, stop_level, native_stop,
            )
            
            # Place order — routed through the hardened request layer
            # (automatic re-auth on 401/session expiry; bug-hunt MEDIUM)
            resp = client._request('POST', '/positions', json_body=payload)
            
            if resp.status_code == 200:
                data = resp.json()
                deal_id = data.get('dealReference', data.get('dealId', 'unknown'))
                return {
                    "dealId": deal_id,
                    "epic": epic,
                    "direction": direction,
                    "size": actual_size,
                    "account": "demo" if client.demo_mode else "live"
                }
            else:
                return {"error": f"HTTP {resp.status_code}: {resp.text[:200]}"}
                
        except Exception as e:
            return {"error": str(e)}
    
    def _get_symbol_category(self, symbol: str) -> str:
        """Determine symbol category for sizing."""
        forex = ["USDJPY", "EURUSD", "GBPUSD"]
        stocks = ["AAPL", "TSLA", "NVDA"]
        commodities = ["GOLD", "SILVER", "OIL_CRUDE", "NATURALGAS"]
        indices = ["US100"]
        crypto = ["BTCUSD", "ETHUSD"]
        
        if symbol in forex:
            return "forex"
        elif symbol in stocks:
            return "stock"
        elif symbol in commodities:
            return "commodity"
        elif symbol in indices:
            return "index"
        elif symbol in crypto:
            return "crypto"
        return "forex"
    
    def _symbol_to_epic(self, client: CapitalClient, symbol: str) -> Optional[str]:
        """Convert symbol to Capital.com epic using client's market search."""
        # Try the client's built-in market search API
        try:
            resp = client._request('GET', '/markets', params={'searchTerm': symbol, 'pageSize': 10})
            if resp.status_code == 200:
                data = resp.json()
                markets = data.get('markets', [])
                for m in markets:
                    epic = m.get('epic', '')
                    name = m.get('instrumentName', '')
                    # Match exact symbol name first
                    if symbol.upper() == epic.upper() or symbol.upper() in name.upper().split():
                        return epic
        except:
            pass
        
        # Fallback: simple epic (Capital.com uses same as symbol name)
        return symbol
    
    def get_demo_positions(self) -> list:
        """Get positions from DEMO account."""
        return self._get_positions(self.demo)
    
    def get_live_positions(self) -> list:
        """Get positions from LIVE account."""
        return self._get_positions(self.live)
    
    def _get_positions(self, client: CapitalClient) -> list:
        """Internal position fetch (hardened request layer: re-auth on 401)."""
        try:
            resp = client._request('GET', '/positions')
            if resp.status_code == 200:
                return resp.json().get('positions', [])
        except Exception as e:
            logger.debug(f"Position fetch error: {e}")
        return []
    
    def close_demo_position(self, deal_id: str) -> dict:
        return self._close_position(self.demo, deal_id)
    
    def close_live_position(self, deal_id: str) -> dict:
        return self._close_position(self.live, deal_id)
    
    def _close_position(self, client: CapitalClient, deal_id: str) -> dict:
        """Close a position by dealId (hardened request layer: re-auth on 401)."""
        try:
            resp = client._request('DELETE', f'/positions/{deal_id}')
            if resp.status_code == 200:
                return {"success": True}
            else:
                return {"error": f"HTTP {resp.status_code}"}
        except Exception as e:
            return {"error": str(e)}
    
    def validate_demo_shadow(self, symbol: str) -> bool:
        """Check if a shadow position exists and is profitable in DEMO."""
        positions = self.get_demo_positions()
        for pos in positions:
            market = pos.get('market', {})
            epic = market.get('epic', '')
            if symbol.upper() in epic.upper():
                position = pos.get('position', {})
                upl = position.get('upl', 0)
                if upl > 0:
                    return True
        return False
    
    def _get_dealing_rules(self, symbol: str) -> Optional[Dict]:
        """Fetch Capital.com dealing rules for a symbol (native units).

        Returns a dict with min/max stop/take-profit distances, or None on any
        failure. Cached in-memory per symbol for 60s to avoid repeated API calls.
        """
        if not hasattr(self, "_dealing_rules_cache"):
            self._dealing_rules_cache: Dict[str, Dict] = {}
            self._dealing_rules_cache_time: Dict[str, float] = {}

        now = time.time()
        cached = self._dealing_rules_cache.get(symbol)
        if cached is not None and (now - self._dealing_rules_cache_time.get(symbol, 0.0)) < 60.0:
            return cached

        client = self.live if self.is_live_ready() else (self.demo if self.is_demo_ready() else None)
        if client is None:
            return None

        epic = self._symbol_to_epic(client, symbol)
        if not epic:
            return None

        try:
            resp = client._request('GET', f'/markets/{epic}')
            if resp.status_code != 200:
                return None
            data = resp.json()
            rules = data.get('dealingRules', {})
            snap = data.get('snapshot', {})

            def _num(key):
                v = rules.get(key, {}).get('value')
                try:
                    return float(v) if v is not None else None
                except Exception:
                    return None

            inst = data.get('instrument', {})
            result = {
                'minStopLossDistance': _num('minStopLossDistance'),
                'maxStopLossDistance': _num('maxStopLossDistance'),
                'minTakeProfitDistance': _num('minTakeProfitDistance'),
                'maxTakeProfitDistance': _num('maxTakeProfitDistance'),
                'minStepStopLossDistance': _num('minStepStopLossDistance'),
                'minStopOrProfitDistance': _num('minStopOrProfitDistance'),
                'maxStopOrProfitDistance': _num('maxStopOrProfitDistance'),
                'minGuaranteedStopDistance': _num('minGuaranteedStopDistance'),
                'minDealSize': _num('minDealSize'),
                'marginFactor': float(inst.get('marginFactor')) if inst.get('marginFactor') is not None else None,
                'marginFactorUnit': inst.get('marginFactorUnit'),
                'lotSize': float(inst.get('lotSize')) if inst.get('lotSize') is not None else 1.0,
                'currency': inst.get('currency'),
                'scalingFactor': float(snap.get('scalingFactor')) if snap.get('scalingFactor') is not None else 1.0,
                'bid': snap.get('bid'),
                'ask': snap.get('offer'),
                'epic': epic,
            }
            self._dealing_rules_cache[symbol] = result
            self._dealing_rules_cache_time[symbol] = now
            return result
        except Exception as e:
            logger.debug(f"[DUAL CAPITAL] dealing rules fetch failed for {symbol}: {e}")
            return None

    def get_minimum_tp_distance(self, symbol: str, entry_price: float) -> float:
        """Minimum take-profit distance in NORMALIZED (Yahoo-consistent) units.

        First tries Capital.com's live dealingRules. Falls back to conservative
        hardcoded floors derived from actual API rejections (2026-09-07).
        """
        symbol = symbol.upper()

        # Try live dealing rules: native distance → scaled distance
        rules = self._get_dealing_rules(symbol)
        native_dist = None
        if rules and rules.get('minTakeProfitDistance'):
            native_dist = float(rules['minTakeProfitDistance']) * 1.05  # 5% safety margin
        if native_dist and native_dist > 0:
            return max(_native_to_scaled(symbol, native_dist), entry_price * 0.0001)

        # Conservative hardcoded floors (in normalized units).
        # Derived from observed error.invalid.takeprofit.min/maxvalue rejections.
        min_pct = {
            "USDJPY": 0.001,
            "EURUSD": 0.0003,
            "GBPUSD": 0.0003,
            "AAPL": 0.009,
            "TSLA": 0.009,
            "NVDA": 0.012,
            "US100": 0.0035,
            "GOLD": 0.012,
            "SILVER": 0.009,
            "OIL_CRUDE": 0.022,
            "NATURALGAS": 0.026,
            "BTCUSD": 0.005,
            "ETHUSD": 0.005,
        }
        abs_floor = {
            "USDJPY": 0.03,
            "EURUSD": 0.0003,
            "GBPUSD": 0.0003,
            "AAPL": 2.00,
            "TSLA": 2.50,
            "NVDA": 5.00,
            "US100": 100.0,
            "GOLD": 50.0,
            "SILVER": 0.60,
            "OIL_CRUDE": 2.00,
            "NATURALGAS": 0.075,
            "BTCUSD": 100.0,
            "ETHUSD": 5.0,
        }
        pct = min_pct.get(symbol, 0.005)
        return max(entry_price * pct, abs_floor.get(symbol, 1.0))

    def get_minimum_tick(self, symbol: str) -> float:
        """DEPRECATED — use get_minimum_tp_distance instead.
        Kept for backward compatibility.
        """
        return self.get_minimum_tp_distance(symbol, 100.0)

    def calculate_micro_tp(self, symbol: str, direction: str, entry_price: float) -> float:
        """Calculate take-profit in NORMALIZED units at Capital.com's minimum distance.

        Adds a 10% buffer and rounds away from entry so rounding never pushes the
        level back inside Capital's minimum-distance envelope.
        """
        distance = self.get_minimum_tp_distance(symbol, entry_price) * 1.10

        is_long = direction.upper() in ["LONG", "BUY"]
        raw_tp = entry_price + distance if is_long else entry_price - distance

        # Round away from entry (up for LONG, down for SHORT)
        import math
        if distance >= 100:
            prec = 0
        elif distance >= 1:
            prec = 1
        elif distance >= 0.01:
            prec = 2
        else:
            prec = 4
        factor = 10 ** prec
        if is_long:
            return math.ceil(raw_tp * factor) / factor
        return math.floor(raw_tp * factor) / factor

    def get_minimum_stop_distance(self, symbol: str, entry_price: float) -> float:
        """Minimum broker-side stop-loss distance in NORMALIZED units.

        Capital's minimum stop distance is typically larger than its minimum
        take-profit distance. Values are conservative floors derived from live
        API rejections (error.invalid.stoploss.maxvalue / minvalue).
        """
        symbol = symbol.upper()
        min_pct = {
            "USDJPY": 0.0015,
            "EURUSD": 0.0005,
            "GBPUSD": 0.0005,
            "AAPL": 0.020,
            "TSLA": 0.025,
            "NVDA": 0.030,
            "US100": 0.005,
            "GOLD": 0.030,
            "SILVER": 0.030,
            "OIL_CRUDE": 0.030,
            "NATURALGAS": 0.005,
            "BTCUSD": 0.010,
            "ETHUSD": 0.010,
        }
        abs_floor = {
            "USDJPY": 0.20,
            "EURUSD": 0.0005,
            "GBPUSD": 0.0005,
            "AAPL": 3.0,
            "TSLA": 4.0,
            "NVDA": 7.0,
            "US100": 150.0,
            "GOLD": 130.0,
            "SILVER": 2.0,
            "OIL_CRUDE": 2.5,
            "NATURALGAS": 0.015,
            "BTCUSD": 200.0,
            "ETHUSD": 10.0,
        }
        pct = min_pct.get(symbol, 0.010)
        return max(entry_price * pct, abs_floor.get(symbol, 1.0))
    
    def get_status(self) -> dict:
        """Get full status of both accounts."""
        return {
            "demo": {
                "ready": self.is_demo_ready(),
                "balance": self.get_demo_balance(),
                "positions": len(self.get_demo_positions())
            },
            "live": {
                "ready": self.is_live_ready(),
                "balance": self.get_live_balance(),
                "positions": len(self.get_live_positions())
            }
        }

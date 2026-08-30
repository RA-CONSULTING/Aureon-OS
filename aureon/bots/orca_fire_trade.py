#!/usr/bin/env python3
"""
🔥 ORCA FIRE TRADE - REAL EXECUTION ONLY
No smoke. Just fire.

This script makes REAL trades immediately.
"""

import os
import json
import time
import math
import requests
from datetime import datetime
from dotenv import load_dotenv

# Load environment
load_dotenv()

# ─── Seer Integration (Third Pillar) ───
_seer_available = False
try:
    from aureon.intelligence.aureon_seer import get_seer
    _seer_available = True
except ImportError:
    pass

# ─── Thought Bus Integration ───
_thought_bus_available = False
_thought_bus_instance = None
_Thought = None
try:
    from aureon.core.aureon_thought_bus import get_thought_bus as _get_tb, Thought as _ThoughtCls
    _thought_bus_available = True
    _Thought = _ThoughtCls
except Exception:
    _get_tb = None

def log_fire(msg):
    print(f"🔥 [FIRE] {msg}")

def log_result(msg):
    print(f"💥 [RESULT] {msg}")

class FireTrader:
    """Manual/Direct execution logic wrapper"""
    
    # Minimum seconds between buying the same symbol on the same exchange
    _BUY_COOLDOWN_SECS = 1800  # 30 minutes
    _SEER_VISION_TTL_SECS = 300
    _SEER_CANDLE_TTL_SECS = 5400
    _QUOTE_TTL_SECS = 120
    _ACCOUNT_TTL_SECS = 120
    _FILL_TTL_SECS = 900

    def __init__(self, kraken_client=None, binance_client=None):
        try:
            from aureon.exchanges.kraken_client import get_kraken_client
            from aureon.exchanges.binance_client import BinanceClient
            self.kraken = kraken_client if kraken_client else get_kraken_client()
            self.binance = binance_client if binance_client else BinanceClient()
        except ImportError:
            log_fire("⚠️ Clients not available")
            self.kraken = None
            self.binance = None
        # {pair: last_buy_timestamp} — prevents hammering the same symbol every cycle
        # Persisted to disk so cooldown survives process restarts
        self._RECENT_BUYS_FILE = os.path.join(os.path.dirname(__file__), '.recent_buys_cooldown.json')
        self._recent_buys: dict = self._load_recent_buys()
        self._reconciliation_attempted = set()
        self._unresolved_order_keys = set()
        self._blocked_submission_exchanges = set()

        # Thought Bus connection
        self._thought_bus = None
        if _thought_bus_available and _get_tb is not None:
            try:
                self._thought_bus = _get_tb()
            except Exception:
                pass

    def _load_recent_buys(self) -> dict:
        """Load buy cooldown timestamps from disk (survives restarts)."""
        try:
            with open(self._RECENT_BUYS_FILE, 'r') as f:
                data = json.load(f)
            # Purge stale entries (older than cooldown window) to keep file small
            cutoff = time.time() - self._BUY_COOLDOWN_SECS
            return {k: v for k, v in data.items() if v > cutoff}
        except (FileNotFoundError, json.JSONDecodeError, KeyError):
            return {}

    def _persist_recent_buys(self):
        """Persist buy cooldown timestamps to disk."""
        try:
            cutoff = time.time() - self._BUY_COOLDOWN_SECS
            pruned = {k: v for k, v in self._recent_buys.items() if v > cutoff}
            with open(self._RECENT_BUYS_FILE, 'w') as f:
                json.dump(pruned, f)
            self._recent_buys = pruned
        except Exception as e:
            log_fire(f"   [WARN] Could not persist buy cooldown: {e}")

    def _publish_fire_event(self, topic: str, payload: dict) -> None:
        """Best-effort publish to Thought Bus."""
        if self._thought_bus is None or _Thought is None:
            return
        try:
            self._thought_bus.publish(_Thought(
                source="fire_trader",
                topic=topic,
                payload=payload,
                meta={"mode": "fire_trade"},
            ))
        except Exception:
            pass

    @staticmethod
    def _finite_number(value, *, positive=False, nonnegative=False):
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

    @classmethod
    def _fresh_timestamp(cls, value, ttl_seconds):
        parsed = cls._finite_number(value, positive=True)
        if parsed is None:
            return None
        if parsed > 10_000_000_000:
            parsed /= 1000.0
        age = time.time() - parsed
        return parsed if -300 <= age <= ttl_seconds else None

    def _account_receipt(self, exchange):
        """Return fresh exact free balances or fail closed with ``None``."""
        client = self.kraken if exchange == 'kraken' else self.binance
        if client is None or bool(getattr(client, 'dry_run', False)):
            return None
        started_at = time.time()
        try:
            if exchange == 'kraken':
                invalidate = getattr(client, 'invalidate_balance_cache', None)
                if callable(invalidate):
                    invalidate()
            raw = client.account()
        except Exception:
            return None
        received_at = time.time()
        if not isinstance(raw, dict) or raw.get('generated_values') is True:
            return None
        if raw.get('truth_status') in {'no_data', 'not_submitted', 'synthetic', 'demo'}:
            return None
        if exchange == 'binance':
            timestamp_value = raw.get('source_timestamp')
            if timestamp_value is None:
                timestamp_value = raw.get('updateTime')
            source_timestamp = self._fresh_timestamp(timestamp_value, self._ACCOUNT_TTL_SECS)
            timestamp_policy = 'provider_update_time'
            source_id = raw.get('source_id') or 'binance:/api/v3/account'
        else:
            source_timestamp = self._fresh_timestamp(raw.get('source_timestamp'), self._ACCOUNT_TTL_SECS)
            timestamp_policy = raw.get('timestamp_policy')
            if source_timestamp is None:
                cache_timestamp = self._fresh_timestamp(
                    getattr(client, '_balance_cache_time', None), self._ACCOUNT_TTL_SECS
                )
                if cache_timestamp is None or cache_timestamp + 1.0 < started_at:
                    return None
                source_timestamp = cache_timestamp
                timestamp_policy = 'local_receive_time_after_uncached_authenticated_balance_read'
            source_id = raw.get('source_id') or 'kraken:/0/private/Balance'
        if source_timestamp is None:
            return None
        rows = raw.get('balances')
        if not isinstance(rows, list):
            return None
        balances = {}
        for row in rows:
            if not isinstance(row, dict):
                return None
            asset = row.get('asset')
            free = self._finite_number(row.get('free'), nonnegative=True)
            locked = self._finite_number(row.get('locked'), nonnegative=True)
            if not isinstance(asset, str) or not asset.strip() or free is None or locked is None:
                return None
            asset = asset.strip().upper()
            if asset in balances:
                return None
            balances[asset] = free
        return {
            'exchange': exchange,
            'balances': balances,
            'source_id': source_id,
            'source_timestamp': source_timestamp,
            'received_at': received_at,
            'timestamp_policy': timestamp_policy,
            'truth_status': 'real_observed',
            'data_status': 'live',
            'generated_values': False,
            'eligible_for_action': True,
        }

    def _quote_receipt(self, exchange, symbol, ticker):
        """Validate a complete fresh 24-hour provider quote."""
        if not isinstance(ticker, dict) or ticker.get('generated_values') is True:
            return None
        if ticker.get('truth_status') in {'no_data', 'not_submitted', 'synthetic', 'demo'}:
            return None
        required = ('lastPrice', 'priceChangePercent', 'quoteVolume')
        if any(key not in ticker or ticker[key] is None for key in required):
            return None
        price = self._finite_number(ticker['lastPrice'], positive=True)
        change = self._finite_number(ticker['priceChangePercent'])
        volume = self._finite_number(ticker['quoteVolume'], nonnegative=True)
        if price is None or change is None or volume is None:
            return None
        timestamp_value = ticker.get('source_timestamp')
        timestamp_policy = ticker.get('timestamp_policy')
        if timestamp_value is None:
            timestamp_value = ticker.get('closeTime')
            timestamp_policy = 'provider_close_time'
        source_timestamp = self._fresh_timestamp(timestamp_value, self._QUOTE_TTL_SECS)
        if source_timestamp is None:
            return None
        provider_symbol = ticker.get('symbol')
        if provider_symbol is not None and (
            str(provider_symbol).replace('/', '').upper()
            != str(symbol).replace('/', '').upper()
        ):
            return None
        return {
            'exchange': exchange,
            'symbol': symbol,
            'price': price,
            'change_24h': change,
            'quote_volume': volume,
            'source_id': ticker.get('source_id') or f'{exchange}:24h_ticker:{symbol}',
            'source_timestamp': source_timestamp,
            'received_at': time.time(),
            'timestamp_policy': timestamp_policy,
            'truth_status': 'real_observed',
            'data_status': 'live',
            'generated_values': False,
            'eligible_for_action': True,
        }

    @staticmethod
    def _quote_asset(symbol):
        normalized = str(symbol or '').replace('/', '').upper()
        for suffix, asset in (
            ('ZUSDC', 'USDC'), ('ZUSDT', 'USDT'), ('ZTUSD', 'TUSD'),
            ('ZUSD', 'USD'), ('ZGBP', 'GBP'), ('ZEUR', 'EUR'),
            ('FDUSD', 'FDUSD'), ('USDC', 'USDC'), ('USDT', 'USDT'),
            ('TUSD', 'TUSD'), ('BUSD', 'BUSD'), ('USD', 'USD'),
            ('GBP', 'GBP'), ('EUR', 'EUR'),
        ):
            if normalized.endswith(suffix) and len(normalized) - len(suffix) >= 3:
                return asset
        return None

    @staticmethod
    def _order_id(receipt):
        if not isinstance(receipt, dict):
            return None
        value = None
        for key in ('orderId', 'txid', 'order_id', 'id'):
            if receipt.get(key) is not None:
                value = receipt[key]
                break
        if isinstance(value, (list, tuple)):
            value = value[0] if len(value) == 1 else None
        if value is None:
            return None
        text = str(value).strip()
        return text if text and text.lower() not in {'none', 'null', 'unknown', 'pending'} else None

    def _normalize_terminal_fill(self, exchange, receipt, symbol, side):
        """Return only a fresh, complete, provider-observed terminal fill."""
        if not isinstance(receipt, dict):
            return None
        if receipt.get('dryRun') is True or receipt.get('dry_run') is True:
            return None
        if receipt.get('generated_values') is True or receipt.get('reconciliation_required') is True:
            return None
        if str(receipt.get('status') or '').upper() != 'FILLED':
            return None
        if receipt.get('fill_receipt_complete') is False:
            return None
        if receipt.get('eligible_for_accounting') is False:
            return None
        order_id = self._order_id(receipt)
        if order_id is None:
            return None
        if str(receipt.get('side') or '').upper() != str(side).upper():
            return None
        provider_symbol = receipt.get('symbol')
        if not isinstance(provider_symbol, str) or not provider_symbol.strip():
            return None
        timestamp_value = None
        for key in ('source_timestamp', 'provider_timestamp', 'transactTime', 'updateTime', 'closedTime', 'time'):
            if receipt.get(key) is not None:
                timestamp_value = receipt[key]
                break
        source_timestamp = self._fresh_timestamp(timestamp_value, self._FILL_TTL_SECS)
        if source_timestamp is None:
            return None
        executed_qty = None
        average_price = None
        filled_notional = None
        for key in ('executedQty', 'filled_qty', 'vol_exec'):
            if receipt.get(key) is not None:
                executed_qty = self._finite_number(receipt[key], positive=True)
                break
        for key in ('filled_avg_price', 'avgPrice', 'avg_fill_price', 'price'):
            if receipt.get(key) is not None:
                average_price = self._finite_number(receipt[key], positive=True)
                break
        for key in ('cummulativeQuoteQty', 'filled_notional', 'cost'):
            if receipt.get(key) is not None:
                filled_notional = self._finite_number(receipt[key], positive=True)
                break
        if executed_qty is None or filled_notional is None:
            return None
        fills = receipt.get('fills')
        quote_asset = self._quote_asset(symbol)
        if not isinstance(fills, list) or not fills or quote_asset is None:
            return None
        trade_ids = []
        if exchange == 'binance':
            observed_qty = 0.0
            observed_notional = 0.0
            fee = 0.0
            fee_assets = set()
            for fill in fills:
                if not isinstance(fill, dict):
                    return None
                fill_qty = self._finite_number(fill.get('qty'), positive=True)
                fill_price = self._finite_number(fill.get('price'), positive=True)
                commission = self._finite_number(fill.get('commission'), nonnegative=True)
                commission_asset = fill.get('commissionAsset')
                trade_id = fill.get('tradeId')
                if (
                    fill_qty is None or fill_price is None or commission is None
                    or not isinstance(commission_asset, str) or not commission_asset.strip()
                    or trade_id is None
                ):
                    return None
                observed_qty += fill_qty
                observed_notional += fill_qty * fill_price
                fee += commission
                fee_assets.add(commission_asset.strip().upper())
                trade_ids.append(str(trade_id))
            if len(fee_assets) != 1 or quote_asset not in fee_assets:
                return None
            if abs(observed_qty - executed_qty) > max(1e-12, executed_qty * 0.001):
                return None
            if abs(observed_notional - filled_notional) > max(1e-8, filled_notional * 0.001):
                return None
            average_price = observed_notional / observed_qty
            fee_asset = quote_asset
        else:
            fee = self._finite_number(receipt.get('fee'), nonnegative=True)
            fee_asset_value = receipt.get('fee_asset') or receipt.get('fee_currency')
            if fee is None or not isinstance(fee_asset_value, str):
                return None
            fee_asset = fee_asset_value.strip().upper()
            if fee_asset != quote_asset:
                return None
            for fill in fills:
                if not isinstance(fill, dict) or fill.get('tradeId') is None:
                    return None
                trade_ids.append(str(fill['tradeId']))
        if len(trade_ids) != len(set(trade_ids)):
            return None
        if average_price is None:
            average_price = filled_notional / executed_qty
        if abs(executed_qty * average_price - filled_notional) > max(1e-8, filled_notional * 0.001):
            return None
        return {
            'provider': exchange,
            'order_id': order_id,
            'symbol': symbol,
            'provider_symbol': provider_symbol,
            'side': str(side).upper(),
            'status': 'FILLED',
            'executed_qty': executed_qty,
            'filled_avg_price': average_price,
            'filled_notional': filled_notional,
            'fee': fee,
            'fee_asset': fee_asset,
            'trade_ids': trade_ids,
            'source_id': receipt.get('source_id') or f'{exchange}:order:{order_id}',
            'source_timestamp': source_timestamp,
            'received_at': time.time(),
            'truth_status': 'real_observed',
            'data_status': 'live',
            'fill_receipt_complete': True,
            'eligible_for_accounting': True,
            'eligible_for_learning': True,
            'generated_values': False,
            'reconciliation_required': False,
            'provider_receipt': receipt,
        }

    @staticmethod
    def _definitely_not_submitted(receipt):
        if not isinstance(receipt, dict):
            return False
        status = str(receipt.get('status') or '').lower()
        return bool(
            receipt.get('dryRun') is True or receipt.get('dry_run') is True
            or receipt.get('submitted') is False or receipt.get('rejected') is True
            or status in {'not_submitted', 'rejected'}
            or (receipt.get('error') and FireTrader._order_id(receipt) is None)
        )

    def _submit_and_confirm(self, exchange, symbol, side, *, quantity=None, quote_qty=None):
        """Submit once; reconcile once; never treat an acknowledgement as a fill."""
        key = (exchange, str(symbol).upper(), str(side).upper())
        if exchange in self._blocked_submission_exchanges or key in self._unresolved_order_keys:
            return {'status': 'suppressed_unresolved_duplicate', 'receipt': None}
        client = self.kraken if exchange == 'kraken' else self.binance
        if client is None:
            return {'status': 'not_submitted', 'receipt': None}
        try:
            raw = client.place_market_order(symbol, side, quantity, quote_qty=quote_qty)
        except Exception as exc:
            self._unresolved_order_keys.add(key)
            self._blocked_submission_exchanges.add(exchange)
            return {'status': 'unresolved', 'receipt': None, 'reason': str(exc)}
        terminal = self._normalize_terminal_fill(exchange, raw, symbol, side)
        if terminal is not None:
            return {'status': 'filled', 'receipt': terminal}
        if self._definitely_not_submitted(raw):
            return {'status': 'not_submitted', 'receipt': raw}
        order_id = self._order_id(raw)
        readback = getattr(client, 'get_order_status', None)
        if order_id is not None and callable(readback):
            attempt = (exchange, order_id)
            if attempt not in self._reconciliation_attempted:
                self._reconciliation_attempted.add(attempt)
                try:
                    reconciled = readback(order_id)
                except Exception:
                    reconciled = None
                terminal = self._normalize_terminal_fill(exchange, reconciled, symbol, side)
                if terminal is not None:
                    return {'status': 'filled', 'receipt': terminal}
        self._unresolved_order_keys.add(key)
        self._blocked_submission_exchanges.add(exchange)
        return {'status': 'unresolved', 'receipt': raw}

    def _append_terminal_trade(self, receipt, event_side):
        if not isinstance(receipt, dict) or receipt.get('fill_receipt_complete') is not True:
            return False
        record = {
            'recorded_at': datetime.now().isoformat(),
            'exchange': receipt['provider'],
            'symbol': receipt['symbol'],
            'side': event_side,
            'truth_status': 'real_observed',
            'source_id': receipt['source_id'],
            'source_timestamp': receipt['source_timestamp'],
            'generated_values': False,
            'fill_receipt': receipt,
        }
        try:
            with open('orca_real_trades.json', 'a') as handle:
                handle.write(json.dumps(record) + '\n')
            return True
        except Exception:
            return False

    def _record_buy_cost_basis(self, pair, receipt, exchange):
        """Persist cost basis only from a complete terminal provider fill."""
        if (
            not isinstance(receipt, dict)
            or receipt.get('fill_receipt_complete') is not True
            or receipt.get('eligible_for_accounting') is not True
            or receipt.get('generated_values') is not False
        ):
            return False
        fill_price = self._finite_number(receipt.get('filled_avg_price'), positive=True)
        fill_qty = self._finite_number(receipt.get('executed_qty'), positive=True)
        total_cost = self._finite_number(receipt.get('filled_notional'), positive=True)
        fee = self._finite_number(receipt.get('fee'), nonnegative=True)
        order_id = receipt.get('order_id')
        if None in (fill_price, fill_qty, total_cost, fee) or not order_id:
            return False
        try:
            from aureon.portfolio.cost_basis_tracker import CostBasisTracker
            tracker = CostBasisTracker()
            tracker.set_entry_price(pair, fill_price, fill_qty, exchange, fee, str(order_id))
            tp_file = 'tracked_positions.json'
            tp = {}
            if os.path.exists(tp_file):
                with open(tp_file, 'r') as handle:
                    tp = json.load(handle)
            tp[pair] = {
                'symbol': pair,
                'exchange': exchange,
                'entry_price': fill_price,
                'buy_price': fill_price,
                'entry_qty': fill_qty,
                'quantity': fill_qty,
                'entry_cost': total_cost + fee,
                'entry_fee': fee,
                'entry_fee_asset': receipt['fee_asset'],
                'breakeven_price': None,
                'buy_timestamp': datetime.fromtimestamp(receipt['source_timestamp']).isoformat(),
                'source': 'fire_trade',
                'source_id': receipt['source_id'],
                'source_timestamp': receipt['source_timestamp'],
                'truth_status': 'real_observed',
                'generated_values': False,
                'fill_receipt': receipt,
                'auto_tracked': False,
            }
            tmp = tp_file + '.tmp'
            with open(tmp, 'w') as handle:
                json.dump(tp, handle, indent=4)
            os.replace(tmp, tp_file)
            log_fire(f"   💾 Cost basis recorded: {exchange}:{pair} @ ${fill_price:.6f} x {fill_qty:.6f}")
            return True
        except Exception as exc:
            log_fire(f"   ⚠️ Failed to record cost basis: {exc}")
            return False

    # ═══════════════════════════════════════════════════════════════════
    # SEER INTEGRATION — The Third Pillar gates every buy
    # ═══════════════════════════════════════════════════════════════════

    # ── Goal-Aware Micro-Gains Configuration ──
    _MICRO_GAINS_MAX_BUY = 50.0      # max $50 per micro-gains buy (matches Kraken $50 minimum)
    _MICRO_GAINS_MIN_CONSENSUS = 4   # majority (4/7) oracles must be bullish — 1 was not a real consensus
    _MICRO_GAINS_RISK_MOD = 1.0      # no position reduction — $50 is already the minimum

    # ── Hard profit floor — NEVER sell unless this GUARANTEED net after EVERYTHING ──
    # $0.017 = 1.7¢ net after: buy taker fee + sell taker fee + slippage buffer
    # Binance: 0.1% buy + 0.1% sell + 0.2% slippage = 0.4% round-trip
    # Kraken:  0.26% buy + 0.26% sell + 0.2% slippage = 0.72% round-trip
    NET_PROFIT_FLOOR_USD  = 0.017    # 1.7¢ — hard minimum net profit required
    _SLIPPAGE_BUFFER      = 0.002    # 0.2% slippage cushion on top of taker fees
    _BINANCE_TAKER        = 0.001    # 0.1% Binance taker
    _KRAKEN_TAKER         = 0.0026   # 0.26% Kraken taker

    # ── 10-9-2 Creature Growth Model ─────────────────────────────────
    # "Only take the scalp, not the body"
    # Scalp = profit portion above cost basis (body stays invested forever)
    # Prime-number cent targets: 2¢, 3¢, 5¢, 7¢, 11¢, 13¢... (primorial steps)
    # 10-9-2 distribution of each scalp received:
    #   89% → free cash (realized profit)
    #    9% → DCA reinvestment back into the same symbol (body grows)
    #    2% → reinvestment pool for new position seeds
    _MIN_POSITION_USD   = 50.0       # $50 minimum position size — matches Kraken exchange minimum
    _MIN_NOTIONAL_USD   = 5.50       # $5.50 minimum POSITION notional (exchange safe)
    _MIN_SCALP_NOTIONAL_KRAKEN  = 10.0   # $10 minimum scalp order notional (Kraken lot minimums)
    _MIN_SCALP_NOTIONAL_BINANCE = 10.0   # $10 minimum scalp order notional (Binance LOT_SIZE / MIN_NOTIONAL)
    _MODEL_DCA_BACK_PCT = 0.09       # 9% of scalp → DCA back into symbol
    _MODEL_REINVEST_PCT = 0.02       # 2% of scalp → reinvestment pool
    # Prime-number cent scalp targets (cents)
    _PRIME_CENTS = [
        2,3,5,7,11,13,17,19,23,29,31,37,41,43,47,53,59,61,67,71,79,83,89,97,
        101,103,107,109,113,127,131,137,139,149,151,157,163,167,173,179,181,
        191,193,197,199,211,223,227,229,233,239,241,251,257,263,269,271,277,
        281,283,293,307,311,313,317,331,337,347,349,353,359,367,373,379,383,
        389,397,401,409,419,421,431,433,439,443,449,457,461,463,467,479,487,
        491,499,503,509,521,523,541,547,557,563,569,571,577,587,593,599,601,
        607,613,617,619,631,641,643,647,653,659,661,673,677,683,691,701,709,
        719,727,733,739,743,751,757,761,769,773,787,797,809,811,821,823,827,
        829,839,853,857,859,863,877,881,883,887,907,911,919,929,937,941,947,
        953,967,971,977,983,991,997,
    ]

    def _floor_prime_cents(self, profit_usd: float) -> float:
        """Return the LARGEST prime-number of cents that fits within profit_usd.
        Minimum is NET_PROFIT_FLOOR_USD (1.7¢) — below that we NEVER sell.
        e.g. $0.18 → 17¢ (prime), $0.04 → 3¢, $0.015 → 0 (below 1.7¢ floor)"""
        if profit_usd < self.NET_PROFIT_FLOOR_USD:
            return 0.0  # not enough — holding
        profit_cents = profit_usd * 100.0
        result = 0
        for p in self._PRIME_CENTS:
            if p <= profit_cents:
                result = p
            else:
                break
        return result / 100.0   # 0 means not enough yet

    def _scalp_qty(self, total_qty: float, price: float, cost_basis: float,
                   fee_rate: float = 0.001) -> tuple:
        """Compute scalp-only sell quantity using 10-9-2 prime-cent targeting.
        Accounts for FULL round-trip cost: buy fee (paid at entry, baked into
        cost_basis), sell taker fee, AND slippage buffer.
        Returns (sell_qty, prime_target_usd, body_qty, log_msg).
        sell_qty=0 means body protected or net < 1.7¢ floor."""
        if not price or price <= 0:
            return 0.0, 0.0, total_qty, "zero price"
        buy_fee_rate  = fee_rate  # same taker rate was paid on entry
        sell_fee_rate = fee_rate
        # Body = coins needed to recover cost_basis (including original buy fee)
        if cost_basis and cost_basis > 0:
            # cost_basis is raw fill price; add buy fee to get true break-even unit cost.
            # body_qty = total coins we must KEEP so that selling them later at cost_basis
            # would recover the full original investment.
            # Formula: total_investment / current_price = coins_needed_to_break_even
            true_cost_per_coin = cost_basis * (1.0 + buy_fee_rate)
            body_qty = (total_qty * true_cost_per_coin) / price  # BUG FIX: was missing total_qty multiplier
            body_qty = min(body_qty, total_qty)     # can't protect more than we hold
        else:
            body_qty = total_qty                    # no cost basis → protect 100% (never sell unknown positions)
        scalp_avail = max(0.0, total_qty - body_qty)
        if scalp_avail <= 0:
            return 0.0, 0.0, body_qty, "body fully covered — no scalp available"
        # NET proceeds from selling scalp coins after sell fee AND slippage
        net_scalp_usd = scalp_avail * price * (1.0 - sell_fee_rate - self._SLIPPAGE_BUFFER)
        prime_target  = self._floor_prime_cents(net_scalp_usd)
        if prime_target <= 0.0:  # below NET_PROFIT_FLOOR_USD (1.7¢)
            return 0.0, 0.0, body_qty, (
                f"net_scalp ${net_scalp_usd*100:.2f}¢ < {self.NET_PROFIT_FLOOR_USD*100:.1f}¢ floor"
            )
        # Qty needed to produce exactly prime_target net after sell fee+slippage
        sell_qty = min(scalp_avail,
                       prime_target / (price * (1.0 - sell_fee_rate - self._SLIPPAGE_BUFFER)))
        msg = (f"PRIME SCALP {int(prime_target*100)}¢ net | net_avail ${net_scalp_usd:.4f} | "
               f"body {body_qty:.4f} units (${body_qty*price:.2f} principal locked)")
        return sell_qty, prime_target, body_qty, msg

    def _load_goal_distance(self) -> float:
        """Return dollars remaining to the nearest active goal."""
        goal_file = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                  'quantum_goal_engine_state.json')
        try:
            with open(goal_file, 'r') as f:
                data = json.load(f)
            goals = data.get('active_goals', [])
            if not goals:
                log_fire("   [GOAL] No active_goals found in goal state file")
                return 999999.0
            # Find the nearest unfulfilled goal
            distances = []
            for g in goals:
                target = float(g.get('target_value', 0))
                current = float(g.get('current_value', 0))
                if target > current:
                    distances.append(target - current)
            result = min(distances) if distances else 999999.0
            return result
        except Exception as e:
            log_fire(f"   [GOAL] ⚠️ Failed to read goal distance: {e}")
            return 999999.0

    def _seer_global_gate(self):
        """
        Consult the Seer before ANY buying.
        Returns (should_buy: bool, risk_mod: float, vision_summary: dict).
        Requires multi-oracle consensus: at least 3/7 oracles must score > 0.55.

        MICRO-GAINS MODE: When close to a goal, relaxes gates to allow small
        tactical buys ($3-5) even in FOG/SELL_BIAS conditions.  Individual
        coins can move up while the macro market is down — we hunt those.
        """
        if not _seer_available:
            log_fire("   [SEER] Not available — BUY gate denied (NO_DATA)")
            return False, 0.0, {
                "status": "unavailable",
                "truth_status": "no_data",
                "decision_status": "denied",
                "generated_values": False,
            }

        try:
            seer = get_seer()
            vision = seer.see()
            vision_timestamp = float(vision.timestamp)
            vision_age = time.time() - vision_timestamp
            if (
                not math.isfinite(vision_timestamp)
                or vision_age < -300
                or vision_age > self._SEER_VISION_TTL_SECS
            ):
                return False, 0.0, {
                    "status": "stale",
                    "truth_status": "no_data",
                    "source_timestamp": vision_timestamp,
                    "decision_status": "denied",
                    "generated_values": False,
                }
            grade = vision.grade
            action = vision.action
            risk_mod = vision.risk_modifier
            score = vision.unified_score

            # ── Multi-oracle consensus: count oracles > 0.55 (bullish threshold) ──
            oracles_bullish = 0
            oracles_total = 0
            oracle_scores = []
            for name, oracle in [("gaia", vision.gaia), ("cosmos", vision.cosmos),
                                  ("harmony", vision.harmony), ("spirits", vision.spirits),
                                  ("timeline", vision.timeline), ("runes", vision.runes),
                                  ("sentiment", vision.sentiment)]:
                if (
                    oracle
                    and hasattr(oracle, 'score')
                    and hasattr(oracle, 'timestamp')
                    and math.isfinite(float(oracle.score))
                    and 0 <= time.time() - float(oracle.timestamp) <= self._SEER_VISION_TTL_SECS
                ):
                    oracles_total += 1
                    oracle_scores.append((name, oracle.score, oracle.confidence))
                    if oracle.score > 0.55:
                        oracles_bullish += 1

            consensus_ratio = oracles_bullish / oracles_total if oracles_total > 0 else 0
            if oracles_total < 4:
                return False, 0.0, {
                    "status": "insufficient_oracle_evidence",
                    "oracles_observed": oracles_total,
                    "truth_status": "no_data",
                    "source_timestamp": vision_timestamp,
                    "decision_status": "denied",
                    "generated_values": False,
                }

            # ── Goal distance: decides whether micro-gains mode activates ──
            goal_distance = self._load_goal_distance()
            micro_mode = goal_distance < 50.0  # within $50 of any goal

            summary = {
                "timestamp": datetime.now().isoformat(),
                "unified_score": round(score, 4),
                "grade": grade,
                "action": action,
                "risk_modifier": round(risk_mod, 3),
                "tactical_mode": vision.tactical_mode,
                "prophecy": vision.prophecy[:200] if vision.prophecy else "",
                "oracle_consensus": f"{oracles_bullish}/{oracles_total}",
                "consensus_ratio": round(consensus_ratio, 3),
                "micro_gains_mode": micro_mode,
                "goal_distance": round(goal_distance, 2),
                "truth_status": "real_derived",
                "source_id": "aureon_seer:fresh_oracle_consensus",
                "source_timestamp": vision_timestamp,
                "received_at": time.time(),
                "generated_values": False,
            }

            # Publish Seer gate result to Thought Bus
            self._publish_fire_event("fire_trade.seer_gate", summary)

            log_fire(f"\n🔮 SEER VISION: score={score:.3f} grade={grade} action={action} risk_mod={risk_mod:.2f}")
            log_fire(f"   Oracle consensus: {oracles_bullish}/{oracles_total} bullish (ratio={consensus_ratio:.2f})")
            for name, sc, conf in oracle_scores:
                bull_mark = "✓" if sc > 0.55 else "✗"
                log_fire(f"   [{bull_mark}] {name:10s}: score={sc:.3f} conf={conf:.2f}")
            log_fire(f"   Tactical: {vision.tactical_mode}")
            log_fire(f"   Goal distance: ${goal_distance:.2f} — micro_mode={'ON' if micro_mode else 'OFF'}")
            if micro_mode:
                log_fire(f"   🎯 MICRO-GAINS MODE ACTIVE — ${goal_distance:.2f} to next goal")
            if vision.prophecy:
                log_fire(f"   Prophecy: {vision.prophecy[:150]}")

            # ═══════════════════════════════════════════════════════════
            # MICRO-GAINS BYPASS: when close to goal, allow small tactical
            # buys even in bearish conditions.  Individual coins can move
            # up 2-5% in an hour while the macro market drops 1%.  We hunt
            # those momentum movers with tiny $3-5 buys.
            # ═══════════════════════════════════════════════════════════
            if micro_mode:
                # BLIND is still too dangerous even for micro
                if grade in ("BLIND",):
                    log_fire("   🚫 SEER BLIND — even micro-gains blocked (zero visibility)")
                    return False, risk_mod, summary

                # Micro needs at least 1 bullish oracle (any signal at all)
                if oracles_bullish >= self._MICRO_GAINS_MIN_CONSENSUS:
                    log_fire(f"   🎯 MICRO-GAINS APPROVED: {oracles_bullish}/{oracles_total} "
                             f"oracle(s) bullish — small tactical buys allowed (max ${self._MICRO_GAINS_MAX_BUY})")
                    return True, self._MICRO_GAINS_RISK_MOD, summary
                else:
                    log_fire(f"   🚫 MICRO-GAINS: 0 oracles bullish — even micro buys blocked")
                    return False, risk_mod, summary

            # ═══════════════════════════════════════════════════════════
            # STANDARD GATES (unchanged for non-micro mode)
            # ═══════════════════════════════════════════════════════════

            # ── CONSENSUS GATE: require at least 3 out of 7 oracles to be bullish ──
            if oracles_total >= 4 and consensus_ratio < 0.40:
                log_fire(f"   🚫 ORACLE CONSENSUS TOO LOW ({oracles_bullish}/{oracles_total} < 40%) — blocking buys")
                return False, risk_mod, summary

            # GATE: Block buys on BLIND, FOG, or DEFEND/SELL_BIAS
            if grade in ("BLIND",):
                log_fire("   🚫 SEER SAYS BLIND — no visibility, blocking ALL buys")
                return False, risk_mod, summary
            if action in ("DEFEND",):
                log_fire("   🛡️ SEER SAYS DEFEND — minimal exposure, blocking buys")
                return False, risk_mod, summary
            if action in ("SELL_BIAS",):
                log_fire("   ⚠️ SEER SAYS SELL_BIAS — not ideal for new entries, blocking buys")
                return False, risk_mod, summary
            if grade in ("FOG",):
                # FOG with low score = unreliable, block buys
                if score < 0.50:
                    log_fire("   🌫️ SEER FOG + low score (<0.50) — blocking buys")
                    return False, risk_mod, summary
                # FOG with score >= 0.50 but action HOLD = marginal, heavy reduction
                log_fire(f"   🌫️ SEER FOG (score={score:.3f}) — heavy position reduction")
                return True, risk_mod * 0.3, summary

            if grade in ("PARTIAL_VISION",):
                log_fire(f"   👁️ SEER PARTIAL_VISION — moderate reduction (score={score:.3f})")
                return True, risk_mod * 0.6, summary

            # CLEAR_SIGHT or DIVINE_CLARITY = green light
            log_fire(f"   ✅ SEER APPROVES entry (grade={grade}, action={action})")
            return True, risk_mod, summary

        except Exception as e:
            log_fire(f"   [SEER] Error consulting: {e} — BUY gate denied")
            return False, 0.0, {
                "status": "error",
                "error": str(e),
                "truth_status": "no_data",
                "decision_status": "denied",
                "generated_values": False,
            }

    def _seer_symbol_signal(self, base_asset: str):
        """
        Per-symbol directional signal using 1h candles from Binance public API.
        Returns (bullish: bool, confidence: float, details: dict).

        Checks:
        1. Last 6 hourly candles — are closes trending up?
        2. Price position in 24h range — near lows = better entry
        3. Volume trend — increasing = conviction
        """
        symbol = f"{base_asset}USDT"  # Use USDT pair for data (most liquid)
        received_at = time.time()
        details = {
            "symbol": symbol,
            "source": "binance_public_klines",
            "source_id": f"binance:public_klines:{symbol}:1h",
            "source_timestamp": None,
            "received_at": received_at,
            "truth_status": "no_data",
            "decision_status": "denied",
            "generated_values": False,
        }

        try:
            resp = requests.get(
                "https://api.binance.com/api/v3/klines",
                params={"symbol": symbol, "interval": "1h", "limit": 12},
                timeout=5
            )
            if resp.status_code != 200:
                log_fire(f"   [SEER-SYM] Kline fetch failed for {symbol}: HTTP {resp.status_code}")
                details["reason"] = f"HTTP_{resp.status_code}"
                return False, 0.0, details

            candles = [
                candle
                for candle in resp.json()
                if isinstance(candle, list)
                and len(candle) > 6
                and float(candle[6]) / 1000.0 <= received_at
            ]
            if len(candles) < 6:
                details["reason"] = "INSUFFICIENT_CLOSED_CANDLES"
                return False, 0.0, details

            source_timestamp = float(candles[-1][6]) / 1000.0
            candle_age = received_at - source_timestamp
            if candle_age < -300 or candle_age > self._SEER_CANDLE_TTL_SECS:
                details["reason"] = "STALE_CANDLE_RECEIPT"
                details["source_timestamp"] = source_timestamp
                return False, 0.0, details

            # Parse candles: [timestamp, open, high, low, close, volume, ...]
            closes = [float(c[4]) for c in candles]
            _opens = [float(c[1]) for c in candles]
            highs = [float(c[2]) for c in candles]
            lows = [float(c[3]) for c in candles]
            volumes = [float(c[5]) for c in candles]
            observations = closes + _opens + highs + lows + volumes
            if (
                not all(math.isfinite(value) for value in observations)
                or any(value <= 0 for value in closes + _opens + highs + lows)
                or any(value < 0 for value in volumes)
            ):
                details["reason"] = "INVALID_CANDLE_OBSERVATION"
                return False, 0.0, details

            current_price = closes[-1]
            high_24h = max(highs)
            low_24h = min(lows)
            price_range = high_24h - low_24h
            if price_range <= 0:
                details["reason"] = "UNOBSERVABLE_PRICE_RANGE"
                return False, 0.0, details

            # ── Signal 1: Short-term trend (last 6 candles) ──
            recent = candles[-6:]
            bullish_candles = sum(1 for c in recent if float(c[4]) > float(c[1]))
            trend_score = bullish_candles / 6.0

            # ── Signal 2: Price momentum (last 3h vs prior 3h) ──
            avg_recent_3 = sum(closes[-3:]) / 3
            avg_prior_3 = sum(closes[-6:-3]) / 3
            momentum_pct = ((avg_recent_3 - avg_prior_3) / avg_prior_3) * 100 if avg_prior_3 > 0 else 0

            # ── Signal 3: Position in 24h range (0.0 = at low, 1.0 = at high) ──
            range_position = (current_price - low_24h) / price_range

            # ── Signal 4: Volume trend (recent vs prior) ──
            vol_recent = sum(volumes[-3:])
            vol_prior = sum(volumes[-6:-3])
            if vol_prior <= 0:
                details["reason"] = "UNOBSERVABLE_VOLUME_RATIO"
                return False, 0.0, details
            vol_ratio = vol_recent / vol_prior

            # ── Combined directional score ──
            momentum_signal = min(1.0, max(0.0, 0.5 + momentum_pct / 4))
            range_signal = 1.0 - range_position  # Near low = high signal
            vol_signal = min(1.0, max(0.0, 0.3 + vol_ratio * 0.35))

            direction_score = (
                trend_score * 0.35 +
                momentum_signal * 0.30 +
                range_signal * 0.15 +
                vol_signal * 0.20
            )

            # ── Confidence = signal strength, NOT data availability ──
            # Strong signal = direction_score far from 0.5 (coin-flip neutral)
            # Also factor in momentum conviction and trend agreement
            signal_strength = abs(direction_score - 0.5) * 2  # 0..1 how far from neutral
            momentum_conviction = min(1.0, abs(momentum_pct) / 2.0)  # stronger momentum = more conviction
            trend_agreement = 1.0 if (trend_score >= 0.5 and momentum_pct > 0) or (trend_score < 0.5 and momentum_pct < 0) else 0.4
            confidence = min(1.0, signal_strength * 0.5 + momentum_conviction * 0.3 + trend_agreement * 0.2)

            # ── BULLISH requires direction_score > 0.55 AND positive momentum ──
            # Old threshold was 0.45 (coin-flip), now requires real conviction
            bullish = (direction_score > 0.55 and momentum_pct > -0.3 and
                       trend_score >= 0.33 and confidence >= 0.15)

            details.update({
                "current_price": round(current_price, 6),
                "trend_score": round(trend_score, 3),
                "bullish_candles_6h": bullish_candles,
                "momentum_pct": round(momentum_pct, 4),
                "range_position": round(range_position, 3),
                "vol_ratio": round(vol_ratio, 3),
                "direction_score": round(direction_score, 4),
                "bullish": bullish,
                "confidence": round(confidence, 3),
                "signal_strength": round(signal_strength, 3),
                "momentum_conviction": round(momentum_conviction, 3),
                "trend_agreement": round(trend_agreement, 3),
                "truth_status": "real_derived",
                "decision_status": "eligible" if bullish else "denied",
                "source_timestamp": source_timestamp,
            })

            direction = "BULLISH" if bullish else "BEARISH"
            log_fire(f"   [SEER-SYM] {base_asset}: {direction} dir={direction_score:.3f} "
                     f"conf={confidence:.3f} trend={trend_score:.2f} mom={momentum_pct:+.2f}% "
                     f"range={range_position:.2f} vol={vol_ratio:.2f}")

            return bullish, confidence, details

        except Exception as e:
            log_fire(f"   [SEER-SYM] Error for {base_asset}: {e}")
            details["reason"] = "PROVIDER_OR_PARSE_ERROR"
            details["error"] = str(e)
            return False, 0.0, details

    # Timeframe layers — every prediction is validated at ALL these horizons
    _TIMEFRAME_LAYERS = [
        ("1m",    60),
        ("5m",    300),
        ("30m",   1_800),
        ("1h",    3_600),
        ("2h",    7_200),
        ("3h",    10_800),
        ("6h",    21_600),
        ("12h",   43_200),
        ("24h",   86_400),
        ("48h",   172_800),
        ("1w",    604_800),
        ("2w",    1_209_600),
        ("1mo",   2_592_000),
        ("3mo",   7_776_000),
        ("6mo",   15_552_000),
        ("1y",    31_536_000),
    ]

    def _log_seer_prediction(
        self, pair, exchange, buy_price, seer_summary, symbol_signal, fill_receipt=None
    ):
        """Record the Seer's prediction at time of trade for later validation.
        Embeds a layered timeline: 1m → 5m → 30m → 1h … → 1y.
        Each layer is validated independently as its horizon matures.
        """
        try:
            import time as _t
            now_ts = _t.time()
            if (
                not isinstance(symbol_signal, dict)
                or symbol_signal.get("truth_status") != "real_derived"
                or not symbol_signal.get("source_timestamp")
                or symbol_signal.get("generated_values") is not False
                or not isinstance(symbol_signal.get("bullish"), bool)
            ):
                log_fire("   [SEER] Prediction not logged: symbol evidence is NO_DATA")
                return False
            if (
                not isinstance(fill_receipt, dict)
                or fill_receipt.get('fill_receipt_complete') is not True
                or fill_receipt.get('eligible_for_learning') is not True
                or fill_receipt.get('generated_values') is not False
            ):
                log_fire("   [SEER] Prediction not logged: terminal buy fill unavailable")
                return False
            is_bullish = symbol_signal["bullish"]

            timeframe_layers = [
                {
                    "label":       label,
                    "seconds":     secs,
                    "validate_at": now_ts + secs,       # epoch when to check
                    "is_bullish":  is_bullish,
                    "validated":   False,
                    "outcome":     None,                 # HIT / MISS / NEUTRAL
                    "price_at":    None,
                    "pct_change":  None,
                }
                for label, secs in self._TIMEFRAME_LAYERS
            ]

            buy_price_usd = None
            fx_receipt = None
            quote_currency = (
                "GBP" if pair and pair.upper().endswith("GBP")
                else "USDC" if pair and pair.upper().endswith("USDC")
                else "USDT" if pair and pair.upper().endswith("USDT")
                else "USD" if pair and pair.upper().endswith("USD")
                else None
            )
            if quote_currency == "USD":
                buy_price_usd = buy_price
                fx_receipt = {
                    "truth_status": "real_derived",
                    "source_id": "currency_unit:USD",
                    "source_timestamp": now_ts,
                    "generated_values": False,
                }
            prediction = {
                "timestamp": datetime.now().isoformat(),
                "pair": pair,
                "exchange": exchange,
                "buy_price": buy_price,
                "buy_price_usd": buy_price_usd,
                "quote_currency": quote_currency,
                "fx_receipt": fx_receipt,
                "seer_global": seer_summary,
                "symbol_signal": symbol_signal,
                "buy_fill_receipt": fill_receipt,
                "truth_status": "real_derived",
                "source_id": fill_receipt["source_id"],
                "source_timestamp": fill_receipt["source_timestamp"],
                "generated_values": False,
                "validated": False,          # True when ALL layers done
                "outcome": None,             # overall (last validated layer)
                "timeframe_layers": timeframe_layers,
            }
            log_path = "seer_trade_predictions.jsonl"
            with open(log_path, "a") as f:
                f.write(json.dumps(prediction) + "\n")
            log_fire(f"   📝 Seer prediction logged for {exchange}:{pair} "
                     f"(16 timeframe layers: 1m → 1y)")
            return True
        except Exception as e:
            log_fire(f"   ⚠️ Failed to log prediction: {e}")
            return False

    def _validate_seer_predictions(self, sold_pair, sold_exchange, sell_price):
        """
        When a sell executes, validate the Seer's prediction at buy time.
        Closes the feedback loop so we know if the Seer was right.
        """
        log_path = "seer_trade_predictions.jsonl"
        validated_path = "seer_validated_predictions.jsonl"
        if not os.path.exists(log_path):
            return

        try:
            remaining = []
            validated = []
            with open(log_path, "r") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        pred = json.loads(line)
                    except json.JSONDecodeError:
                        remaining.append(line)
                        continue

                    # Match by pair + exchange
                    if (pred.get("pair") == sold_pair and
                        pred.get("exchange") == sold_exchange and
                        not pred.get("validated")):
                        # Validate: was the prediction correct?
                        buy_price = pred.get("buy_price", 0)
                        if buy_price > 0 and sell_price > 0:
                            profit_pct = ((sell_price - buy_price) / buy_price) * 100
                            was_profitable = profit_pct > 0
                            pred["validated"] = True
                            pred["outcome"] = {
                                "sell_price": sell_price,
                                "profit_pct": round(profit_pct, 4),
                                "was_profitable": was_profitable,
                                "validated_at": datetime.now().isoformat(),
                            }
                            validated.append(pred)
                            direction = pred.get("symbol_signal", {}).get("direction_score", 0)
                            log_fire(f"   📊 SEER VALIDATION: {sold_exchange}:{sold_pair} "
                                     f"profit={profit_pct:+.2f}% | Seer said dir={direction:.3f} | "
                                     f"{'✅ CORRECT' if was_profitable else '❌ WRONG'}")
                        else:
                            remaining.append(json.dumps(pred))
                    else:
                        remaining.append(json.dumps(pred))

            # Write back unvalidated predictions
            with open(log_path, "w") as f:
                for line in remaining:
                    f.write(line + "\n")

            # Append validated predictions to history
            if validated:
                with open(validated_path, "a") as f:
                    for pred in validated:
                        f.write(json.dumps(pred) + "\n")

        except Exception as e:
            log_fire(f"   ⚠️ Seer validation error: {e}")

    def run_fire_check(self):
        """Run the fire trade logic using SHARED clients."""
        log_fire("=" * 50)
        log_fire("   ORCA FIRE TRADE - REAL EXECUTION")
        log_fire("=" * 50)

        if not self.kraken or not self.binance:
            log_fire("⚠️ Clients not initialized")
            return False

        sell_executed = False  # track whether any sell fired this cycle

        # Check what we have
        log_fire("\n📊 CHECKING REAL BALANCES...")
        
        # Kraken balances
        log_fire("\n🐙 KRAKEN:")
        tradeable_kraken = {}
        kraken_has_cash = False
        kraken_usd_cash = 0.0
        kraken_usdc_cash = 0.0
        kraken_usdt_cash = 0.0  # USDT balance
        kraken_gbp_cash = 0.0
        kraken_tusd_cash = 0.0  # TUSD balance
        kraken_account = self._account_receipt('kraken')
        if kraken_account is None:
            log_fire("   NO_DATA: complete fresh Kraken account receipt unavailable")
        else:
            for asset, amt in kraken_account['balances'].items():
                if amt <= 0:
                    continue
                log_fire(f"   {asset}: {amt}")
                if asset in {'USD', 'ZUSD'}:
                    kraken_usd_cash += amt
                elif asset == 'USDC':
                    kraken_usdc_cash += amt
                elif asset == 'USDT':
                    kraken_usdt_cash += amt
                elif asset == 'TUSD':
                    kraken_tusd_cash += amt
                elif asset in {'GBP', 'ZGBP'}:
                    kraken_gbp_cash += amt
                else:
                    tradeable_kraken[asset] = amt
            kraken_has_cash = any(
                amount > 0 for amount in (
                    kraken_usd_cash, kraken_usdc_cash, kraken_usdt_cash,
                    kraken_tusd_cash, kraken_gbp_cash,
                )
            )
        
        # Binance balances
        log_fire("\n🟡 BINANCE:")
        tradeable_binance = {}
        binance_cash = 0.0
        binance_account = self._account_receipt('binance')
        if binance_account is None:
            log_fire("   NO_DATA: complete fresh Binance account receipt unavailable")
        else:
            for asset, amt in binance_account['balances'].items():
                if amt <= 0:
                    continue
                if asset == 'USDC':
                    binance_cash += amt
                if asset in {'USDT', 'USDC', 'BUSD', 'FDUSD', 'TUSD'} or asset.startswith('LD'):
                    continue
                log_fire(f"   {asset}: {amt}")
                tradeable_binance[asset] = amt
        
        # Get prices and find ALL profitable opportunities
        log_fire("\n🔍 SCANNING BINANCE FOR ALL PROFITABLE POSITIONS (any real gain after fees)...")
        profitable_sells = []
        
        # Use CostBasisTracker for accurate 6-strategy matching
        _fire_tracker = None
        try:
            from aureon.portfolio.cost_basis_tracker import CostBasisTracker
            _fire_tracker = CostBasisTracker()
        except Exception:
            pass
        
        for asset, qty in tradeable_binance.items():
            try:
                # UK accounts: use USDC pairs only
                symbol = f"{asset}USDC"
                ticker = self.binance.get_24h_ticker(symbol)
                quote = self._quote_receipt('binance', symbol, ticker)
                if quote is None:
                    continue
                price = quote['price']
                change = quote['change_24h']
                value = qty * price

                if value <= 1:
                    continue

                # Check cost basis using the CostBasisTracker (6-strategy matching)
                cost_basis = None
                if _fire_tracker:
                    try:
                        cb_entry = _fire_tracker.get_entry_price(symbol, 'binance')
                        if not cb_entry or cb_entry <= 0:
                            # Also try bare format
                            for q in ['USDC', 'USDT', 'USD']:
                                cb_entry = _fire_tracker.get_entry_price(f"{asset}{q}", 'binance')
                                if cb_entry and cb_entry > 0:
                                    break
                        if cb_entry and cb_entry > 0:
                            cost_basis = cb_entry
                    except Exception:
                        pass

                # ── HARD BLOCK: never sell if we don't know what we paid ──
                if cost_basis is None or cost_basis <= 0:
                    log_fire(f"   [HOLD] Binance {asset}: no confirmed cost basis — will NOT sell (protecting capital)")
                    continue

                # ── True net USD after FULL round-trip: buy fee + sell fee + slippage ──
                entry_ref = cost_basis
                # Round-trip cost: buy taker (paid at entry) + sell taker + slippage buffer
                _total_cost_rate = self._BINANCE_TAKER + self._BINANCE_TAKER + self._SLIPPAGE_BUFFER
                net_usd = qty * (price * (1.0 - self._BINANCE_TAKER - self._SLIPPAGE_BUFFER)
                                 - entry_ref * (1.0 + self._BINANCE_TAKER))
                profit_margin = (net_usd / (qty * entry_ref) * 100) if (qty * entry_ref) > 0 else 0

                log_fire(f"   [DEBUG] Binance {asset}: qty={qty:.4f}, price=${price:.4f}, "
                         f"cost_basis=${entry_ref:.4f}, net_usd=${net_usd:.4f}, "
                         f"profit={profit_margin:+.2f}%, 24h={change:+.1f}%")

                # HARD RULE: net profit after ALL fees+slippage must be >= 1.7¢
                # Only queue if notional also clears exchange minimum
                if net_usd >= self.NET_PROFIT_FLOOR_USD and change > -2.0 and value >= self._MIN_NOTIONAL_USD:
                    profitable_sells.append({
                        'asset': asset,
                        'symbol': symbol,
                        'qty': qty,
                        'price': price,
                        'value': value,
                        'change': change,
                        'profit_margin': profit_margin,
                        'net_usd': net_usd,
                        'cost_basis': entry_ref,
                    })
                elif net_usd > 0 and net_usd < self.NET_PROFIT_FLOOR_USD:
                    log_fire(f"   [HOLD] {asset}: net ${net_usd:.4f} < ${self.NET_PROFIT_FLOOR_USD:.3f} floor — holding")
                elif net_usd > 0 and value < self._MIN_NOTIONAL_USD:
                    log_fire(f"   [SKIP] {asset}: net ${net_usd:.4f} but ${value:.2f} < ${self._MIN_NOTIONAL_USD} notional")
            except Exception as e:
                log_fire(f"   [DEBUG] Binance {asset}: error while evaluating sell opportunity - {e}")

        # Sell ALL profitable positions — SCALP-NOT-BODY with prime-cent targeting
        profitable_sells.sort(key=lambda x: -x['profit_margin'])
        for best_sell in profitable_sells:
            log_fire(f"\n🎯 PRIME SCALP OPPORTUNITY (Binance): {best_sell['asset']} +{best_sell['profit_margin']:.2f}%")
            # ── Scalp-not-body: only sell the profit coins, principal stays forever ──
            fee_rate_b = 0.001  # Binance taker
            sell_qty, prime_target, body_qty, scalp_msg = self._scalp_qty(
                best_sell['qty'], best_sell['price'], best_sell['cost_basis'], fee_rate_b
            )
            if sell_qty <= 0:
                log_fire(f"   ⏸ BODY PROTECTED ({best_sell['asset']}): {scalp_msg}")
                continue
            log_fire(f"   🔢 {scalp_msg}")
            log_fire(f"   🏛 BODY STAYS: {body_qty:.6f} {best_sell['asset']} (${body_qty*best_sell['price']:.2f} principal protected)")

            # Gate: scalp notional must clear Binance's MIN_NOTIONAL filter
            scalp_notional_b = sell_qty * best_sell['price']
            if scalp_notional_b < self._MIN_SCALP_NOTIONAL_BINANCE:
                log_fire(
                    f"   [HOLD] {best_sell['asset']}: scalp notional ${scalp_notional_b:.2f} < "
                    f"${self._MIN_SCALP_NOTIONAL_BINANCE} Binance minimum — accumulating more profit"
                )
                continue

            try:
                result = self._submit_and_confirm(
                    'binance', best_sell['symbol'], 'sell', quantity=sell_qty
                )
                receipt = result.get('receipt')
                if result.get('status') == 'filled' and receipt is not None:
                    log_fire(f"💥 TERMINAL SCALP FILL: {receipt['order_id']}")
                    self._append_terminal_trade(receipt, 'SCALP_SELL')
                    self._publish_fire_event("fire_trade.scalp_sold", {
                        "symbol": best_sell['symbol'],
                        "exchange": "binance",
                        "order_id": receipt['order_id'],
                        "executed_qty": receipt['executed_qty'],
                        "filled_notional": receipt['filled_notional'],
                        "fee": receipt['fee'],
                        "fee_asset": receipt['fee_asset'],
                        "source_timestamp": receipt['source_timestamp'],
                        "truth_status": "real_observed",
                        "generated_values": False,
                    })
                    sell_executed = True
                else:
                    log_fire(f"❌ Binance scalp sell not confirmed: {result.get('status')}")
            except Exception as e:
                log_fire(f"❌ Binance scalp sell failed ({best_sell['symbol']}): {e}")
        if not profitable_sells:
            log_fire("   [DEBUG] Binance: no profitable positions to scalp")

        log_fire("\n🔍 Scanning Kraken for profit opportunities...")
        
        for asset, qty in tradeable_kraken.items():
            if qty <= 0:
                continue
                
            # Get current price and check if profitable
            try:
                pair = f"{asset}USD"
                ticker24 = self.kraken.get_24h_ticker(pair)
                quote = self._quote_receipt('kraken', pair, ticker24)
                if quote is None:
                    continue
                price = quote['price']
                change_24h = quote['change_24h']
                quote_vol = quote['quote_volume']

                value = qty * price

                if value < self._MIN_NOTIONAL_USD:  # Skip small positions ($5.50 floor)
                    continue

                log_fire(
                    f"   [DEBUG] Kraken {asset}: qty={qty:.4f}, price=${price:.4f}, "
                    f"24h_change={change_24h:+.2f}%, vol=${quote_vol:,.0f}"
                )

                # Load cost basis using CostBasisTracker (6-strategy matching)
                cost_basis = None
                if _fire_tracker:
                    try:
                        cb_entry = _fire_tracker.get_entry_price(pair, 'kraken')
                        if not cb_entry or cb_entry <= 0:
                            for q in ['USD', 'USDC']:
                                cb_entry = _fire_tracker.get_entry_price(f"{asset}{q}", 'kraken')
                                if cb_entry and cb_entry > 0:
                                    break
                        if cb_entry and cb_entry > 0:
                            cost_basis = cb_entry
                    except Exception:
                        pass
                
                # ── HARD BLOCK: never sell if we don't know what we paid ──
                if cost_basis is None or cost_basis <= 0:
                    log_fire(f"   [HOLD] {asset}: no confirmed cost basis — will NOT sell (protecting capital)")
                    continue

                # ── True net USD after FULL round-trip: buy fee + sell fee + slippage ──
                entry_ref = cost_basis
                net_usd_k = qty * (price * (1.0 - self._KRAKEN_TAKER - self._SLIPPAGE_BUFFER)
                                   - entry_ref * (1.0 + self._KRAKEN_TAKER))
                profit_margin = (net_usd_k / (qty * entry_ref) * 100) if (qty * entry_ref) > 0 else 0

                log_fire(f"   [DEBUG] Kraken {asset}: cost_basis=${entry_ref:.4f}, "
                         f"net_usd=${net_usd_k:.4f}, profit_margin={profit_margin:.2f}%")

                # HARD RULE: net profit after ALL fees+slippage must be >= 1.7¢
                if net_usd_k >= self.NET_PROFIT_FLOOR_USD and change_24h > -2.0:
                    log_fire(f"   📈 {asset}: ${value:.2f} @ ${price:.4f} (24h {change_24h:+.2f}%, +{profit_margin:.2f}% profit)")
                    log_fire(f"\n🎯 PRIME SCALP OPPORTUNITY: {asset}")
                    # ── Scalp-not-body: body stays, only scalp coins sold ──
                    fee_rate_k = self._KRAKEN_TAKER
                    sell_qty, prime_target_k, body_qty_k, scalp_msg_k = self._scalp_qty(
                        qty, price, entry_ref, fee_rate_k
                    )
                    if sell_qty <= 0:
                        log_fire(f"   ⏸ BODY PROTECTED ({asset}): {scalp_msg_k}")
                        continue  # FIX: was 'break' — must check remaining assets, not stop
                    log_fire(f"   🔢 {scalp_msg_k}")
                    log_fire(f"   🏛 BODY STAYS: {body_qty_k:.6f} {asset} (${body_qty_k*price:.2f} principal protected)")

                    # Gate: scalp notional must clear Kraken's lot-size minimum
                    scalp_notional_k = sell_qty * price
                    if scalp_notional_k < self._MIN_SCALP_NOTIONAL_KRAKEN:
                        log_fire(
                            f"   [HOLD] {asset}: scalp notional ${scalp_notional_k:.2f} < "
                            f"${self._MIN_SCALP_NOTIONAL_KRAKEN} Kraken minimum — accumulating more profit"
                        )
                        continue

                    log_fire(f"\n⚡ EXECUTING SELL: {sell_qty} {asset}...")
                    
                    # Use self.kraken to place order
                    result = self._submit_and_confirm('kraken', pair, 'sell', quantity=sell_qty)
                    receipt = result.get('receipt')
                    if result.get('status') == 'filled' and receipt is not None:
                        log_fire(f"💥 TERMINAL SCALP FILL: {receipt['order_id']}")
                        self._append_terminal_trade(receipt, 'SCALP_SELL')
                        self._publish_fire_event("fire_trade.scalp_sold", {
                            "symbol": pair,
                            "exchange": "kraken",
                            "order_id": receipt['order_id'],
                            "executed_qty": receipt['executed_qty'],
                            "filled_notional": receipt['filled_notional'],
                            "fee": receipt['fee'],
                            "fee_asset": receipt['fee_asset'],
                            "source_timestamp": receipt['source_timestamp'],
                            "truth_status": "real_observed",
                            "generated_values": False,
                        })
                        sell_executed = True
                        break
                    else:
                        log_fire(f"❌ Kraken scalp sell not confirmed: {result.get('status')}")
                        
            except Exception as e:
                log_fire(f"   [DEBUG] Kraken {asset}: error while checking profit - {e}")
        
        if not sell_executed:
            log_fire("\n⚠️ No profitable positions to sell")
        else:
            log_fire("\n✅ Sell(s) executed — proceeding to buy phase with available cash")

        # -----------------------------------------------------------------
        # BUY PHASE: always runs after sell scan so cash (e.g. ZGBP/TUSD)
        # gets deployed in the same cycle that a sell fires.
        # -----------------------------------------------------------------
        if not kraken_has_cash and binance_cash < 1.0:
            log_fire("   [DEBUG] Buy phase skipped: insufficient total cash")
            return sell_executed

        log_fire("\n🛒 Scanning for BUY opportunities with available cash...")
        log_fire(
            "   [DEBUG] Fresh free cash: "
            f"Kraken USD={kraken_usd_cash:.2f}, USDC={kraken_usdc_cash:.2f}, "
            f"USDT={kraken_usdt_cash:.2f}, TUSD={kraken_tusd_cash:.2f}, "
            f"GBP={kraken_gbp_cash:.2f}; Binance USDC={binance_cash:.2f}"
        )

        # ═══════ SEER GLOBAL GATE — Third Pillar must approve ═══════
        seer_ok, seer_risk_mod, seer_summary = self._seer_global_gate()
        micro_mode = seer_summary.get('micro_gains_mode', False)
        if not seer_ok:
            log_fire("🚫 SEER BLOCKED all buys — waiting for better conditions")
            return sell_executed

        bought_any = False

        # Prefer Kraken if it has more cash (current setup often has Kraken USDC)
        prefer_kraken = kraken_has_cash and self.kraken is not None

        # Always deploy $50 per position — the Kraken exchange minimum.
        # This applies in both normal and micro-gains (FOG/bearish) mode.
        # Seer risk_mod no longer reduces below $50 since that just wastes API calls.
        def _buy_amount_kraken(cash_amt: float) -> float:
            return max(self._MIN_POSITION_USD, min(self._MICRO_GAINS_MAX_BUY, cash_amt * 0.90))
        def _buy_amount_binance(cash_amt: float) -> float:
            return max(self._MIN_POSITION_USD, min(self._MICRO_GAINS_MAX_BUY, cash_amt * 0.90))
        max_candidates = 12 if micro_mode else 8


        # ─────────────────────────────────────────────────────────────────
        # KRAKEN BUY — Full dynamic universe: discover ALL pairs from the
        # exchange API for each funded quote currency (GBP / USDC / USD /
        # TUSD). No hardcoded asset list — uses get_available_pairs().
        # ─────────────────────────────────────────────────────────────────
        if prefer_kraken:
            buy_candidates = []  # ranked list: try each in order on failure

            kraken_quote_map = []  # [(pair_altname, quote_ccy), ...]
            try:
                if kraken_gbp_cash >= 4.0:
                    gbp_pairs = self.kraken.get_available_pairs(quote='GBP')
                    kraken_quote_map += [(p['pair'] if isinstance(p, dict) else p, 'GBP') for p in gbp_pairs]
                if kraken_usdc_cash >= 1.0:
                    usdc_pairs = self.kraken.get_available_pairs(quote='USDC')
                    kraken_quote_map += [(p['pair'] if isinstance(p, dict) else p, 'USDC') for p in usdc_pairs]
                if kraken_usd_cash >= 1.0:
                    usd_pairs = self.kraken.get_available_pairs(quote='USD')
                    kraken_quote_map += [(p['pair'] if isinstance(p, dict) else p, 'USD') for p in usd_pairs]
                if kraken_usdt_cash >= 1.0:
                    usdt_pairs = self.kraken.get_available_pairs(quote='USDT')
                    kraken_quote_map += [(p['pair'] if isinstance(p, dict) else p, 'USDT') for p in usdt_pairs]
                if kraken_tusd_cash >= 1.0:
                    tusd_pairs = self.kraken.get_available_pairs(quote='TUSD')
                    kraken_quote_map += [(p['pair'] if isinstance(p, dict) else p, 'TUSD') for p in tusd_pairs]
            except Exception as e:
                log_fire(f"   [WARN] Kraken pair discovery failed: {e} — using safe fallback")
                if kraken_gbp_cash >= 4.0:
                    kraken_quote_map += [("XBTGBP", 'GBP'), ("ETHGBP", 'GBP'), ("SOLGBP", 'GBP'),
                                         ("ADAGBP", 'GBP'), ("XRPGBP", 'GBP'), ("AVAXGBP", 'GBP')]
                if kraken_usdc_cash >= 1.0:
                    kraken_quote_map += [("BTCUSDC", 'USDC'), ("ETHUSDC", 'USDC'), ("SOLUSDC", 'USDC')]
                if kraken_usdt_cash >= 1.0:
                    kraken_quote_map += [("XBTUSDT", 'USDT'), ("ETHUSDT", 'USDT'), ("SOLUSDT", 'USDT')]
                if kraken_usd_cash >= 1.0:
                    kraken_quote_map += [("XBTUSD", 'USD'), ("ETHUSD", 'USD'), ("SOLUSD", 'USD')]

            # Deduplicate while preserving order
            seen_kp = set()
            kraken_unique = []
            for pair, qccy in kraken_quote_map:
                if pair and pair not in seen_kp:
                    seen_kp.add(pair)
                    kraken_unique.append((pair, qccy))

            log_fire(f"   [SCAN] Kraken: fetching tickers for {len(kraken_unique)} pairs across funded quote currencies")

            # Stablecoin/fiat base assets — buying these with USD/GBP is pointless (USDTZUSD etc)
            _STABLECOIN_BASES = {
                'USD', 'USDT', 'USDC', 'TUSD', 'DAI', 'BUSD', 'FDUSD',
                'GBP', 'EUR', 'ZUSD', 'ZGBP', 'ZEUR', 'USDUC', 'U',
            }

            for pair, quote_ccy in kraken_unique:
                try:
                    # Derive base asset: strip known quote suffixes
                    base_candidate = pair
                    for suffix in [quote_ccy, 'USD', 'USDT', 'USDC', 'GBP', 'EUR', 'TUSD']:
                        if base_candidate.upper().endswith(suffix.upper()):
                            base_candidate = base_candidate[:-len(suffix)]
                            break
                    base_candidate = base_candidate.lstrip('XZ').upper()
                    if base_candidate in _STABLECOIN_BASES:
                        log_fire(f"   [SKIP] {pair} — stablecoin/fiat base ({base_candidate}), skipping")
                        continue

                    ticker24 = self.kraken.get_24h_ticker(pair)
                    quote = self._quote_receipt('kraken', pair, ticker24)
                    if quote is None:
                        continue
                    price = quote['price']
                    change_24h = quote['change_24h']
                    quote_vol = quote['quote_volume']
                    # Reject micro-cap coins (price < $0.001) and illiquid pairs (< $50K 24h vol)
                    if price <= 0 or price < 0.001 or quote_vol < 50_000:
                        continue
                    # ── SCORING: cap raw change contribution so we never chase 50% pumps ──
                    # Clamp change to [-5%, +5%] before scoring — anything higher is already
                    # late and likely to reverse. Volume is the primary quality signal.
                    clamped_change = max(-5.0, min(5.0, change_24h))
                    if micro_mode:
                        # Micro-gains: require positive momentum but cap at 3% to avoid tops
                        momentum_bonus = max(0, min(3.0, change_24h)) * 2
                        score = momentum_bonus + min(quote_vol / 1_000_000, 5)
                    else:
                        score = clamped_change + min(quote_vol / 1_000_000, 5)
                    buy_candidates.append({
                        'pair': pair, 'price': price, 'change_24h': change_24h,
                        'quote_vol': quote_vol, 'score': score, 'quote_ccy': quote_ccy,
                    })
                except Exception:
                    continue

            # Rank descending by score; test top candidates through SEER
            buy_candidates.sort(key=lambda x: -x['score'])
            log_fire(f"   [SCAN] Kraken: {len(buy_candidates)} liquid pairs found, testing top {max_candidates} with SEER")

            for candidate in buy_candidates[:max_candidates]:
                # ═══ BUY COOLDOWN CHECK ═══ (prevent hammering the same symbol every cycle)
                _pair_key_k = f"kraken:{candidate['pair']}"
                _now_k = time.time()
                _last_k = self._recent_buys.get(_pair_key_k, 0)
                if _now_k - _last_k < self._BUY_COOLDOWN_SECS:
                    log_fire(f"   ⏳ COOLDOWN: {candidate['pair']} bought {int((_now_k - _last_k)/60)}m ago — skipping")
                    continue
                # ═══ SEER PER-SYMBOL CHECK ═══
                base_for_seer = (candidate['pair']
                    .replace('USDC', '').replace('TUSD', '').replace('ZGBP', '')
                    .replace('GBP', '').replace('ZUSD', '').replace('USD', '').lstrip('X'))
                if base_for_seer in ('XBT', 'XXBT', 'BT', ''):
                    base_for_seer = 'BTC'
                sym_bullish, _sym_conf, sym_details = self._seer_symbol_signal(base_for_seer)
                if not sym_bullish:
                    # Seer BEARISH is a hard block — a 24h pump does not override a bearish signal.
                    # Buying into a BEARISH signal during micro-gains mode is how the system buys tops.
                    log_fire(f"   🔮 SEER rejects {base_for_seer} — BEARISH, trying next")
                    continue

                qccy = candidate['quote_ccy']
                funded_cash = (kraken_gbp_cash if qccy == 'GBP'
                               else kraken_usdc_cash if qccy == 'USDC'
                               else kraken_usdt_cash if qccy == 'USDT'
                               else kraken_tusd_cash if qccy == 'TUSD'
                               else kraken_usd_cash)
                if funded_cash < self._MIN_POSITION_USD:
                    log_fire(f"   [SKIP] Insufficient {qccy} cash (${funded_cash:.2f}) — minimum is ${self._MIN_POSITION_USD:.0f}")
                    continue
                raw_qty = _buy_amount_kraken(funded_cash)
                quote_qty = min(raw_qty * seer_risk_mod, funded_cash * 0.9)
                # Only enforce floor if we actually have enough cash; never create a buy
                # larger than funded_cash (the old max(..., 50) would send $50 orders
                # against a $10 balance, causing exchange rejections).
                quote_qty = max(self._MIN_POSITION_USD, min(quote_qty, funded_cash * 0.95))
                log_fire(f"\n🎯 BUY OPPORTUNITY (Kraken{' MICRO' if micro_mode else ''}): {candidate['pair']}")
                log_fire(f"   Price=${candidate['price']:.6f} | 24h={candidate['change_24h']:+.2f}% | Vol=${candidate['quote_vol']:.0f}")
                log_fire(f"   Seer risk_mod={seer_risk_mod:.2f} → qty={quote_qty:.2f} {qccy}")
                try:
                    result = self._submit_and_confirm(
                        'kraken', candidate['pair'], 'buy', quote_qty=quote_qty
                    )
                    receipt = result.get('receipt')
                    if result.get('status') == 'filled' and receipt is not None:
                        log_fire("💥 TERMINAL BUY FILL (Kraken)")
                        self._record_buy_cost_basis(candidate['pair'], receipt, 'kraken')
                        self._append_terminal_trade(receipt, 'BUY')
                        self._log_seer_prediction(
                            candidate['pair'], 'kraken', receipt['filled_avg_price'],
                            seer_summary, sym_details, receipt,
                        )
                        self._recent_buys[f"kraken:{candidate['pair']}"] = time.time()
                        self._persist_recent_buys()
                        bought_any = True
                        break
                    else:
                        log_fire(f"❌ Kraken buy not confirmed: {result.get('status')}")
                        if result.get('status') in {'unresolved', 'suppressed_unresolved_duplicate'}:
                            break
                except Exception as e:
                    log_fire(f"❌ Kraken buy failed closed ({candidate['pair']}): {e}")
                    break

        # ─────────────────────────────────────────────────────────────────
        # BINANCE BUY — Full UK universe: all 521 UK-FCA-allowed USDC pairs.
        # Uses get_24h_tickers() (one API call for ALL pairs) filtered by
        # get_allowed_pairs_uk() — no hardcoded watchlist.
        # ─────────────────────────────────────────────────────────────────
        if self.binance is not None and binance_cash >= 1.0:
            buy_candidates = []
            try:
                uk_allowed = self.binance.get_allowed_pairs_uk()   # 521 pairs, 1hr cache
                all_tickers = self.binance.get_24h_tickers()       # ALL pairs, single call
                log_fire(f"   [SCAN] Binance: {len(all_tickers)} total tickers, {len(uk_allowed)} UK-allowed pairs")

                for t in all_tickers:
                    if not isinstance(t, dict) or not isinstance(t.get('symbol'), str):
                        continue
                    sym = str(t['symbol'])
                    # UK accounts: USDC pairs ONLY (USDT not permitted)
                    if not sym.endswith('USDC'):
                        continue
                    # Skip symbols with non-ASCII chars (e.g. 币安人生USDC) — breaks HMAC signature
                    if not sym.isascii():
                        continue
                    if uk_allowed and sym not in uk_allowed:
                        continue
                    quote = self._quote_receipt('binance', sym, t)
                    count = self._finite_number(t.get('count'), nonnegative=True)
                    if quote is None or count is None:
                        continue
                    price = quote['price']
                    change = quote['change_24h']
                    volume = quote['quote_volume']
                    # Reject micro-cap coins (< $0.001) and illiquid pairs (< $100K 24h vol)
                    if price <= 0 or price < 0.001 or volume < 100_000 or count < 500:
                        continue
                    # ── SCORING: cap raw change so we never chase 50% pumps ──
                    clamped_change = max(-5.0, min(5.0, change))
                    if micro_mode:
                        momentum_bonus = max(0, min(3.0, change)) * 2
                        score = momentum_bonus + min(volume / 1_000_000, 5)
                    else:
                        score = clamped_change + min(volume / 1_000_000, 5)
                    buy_candidates.append({
                        'pair': sym, 'price': price, 'change': change,
                        'volume': volume, 'score': score,
                    })
            except Exception as e:
                log_fire(f"   [WARN] Binance full-universe scan failed: {e} — using safe fallback")
                for base in ["BTC", "ETH", "SOL", "BNB", "XRP", "ADA", "LINK", "AVAX", "DOT", "MATIC"]:
                    try:
                        ticker = self.binance.get_24h_ticker(f"{base}USDC")
                        pair = f"{base}USDC"
                        quote = self._quote_receipt('binance', pair, ticker)
                        if quote is None:
                            continue
                        price = quote['price']
                        change = quote['change_24h']
                        volume = quote['quote_volume']
                        if price > 0:
                            buy_candidates.append({
                                'pair': pair,
                                'price': price,
                                'change': change,
                                'volume': volume,
                                'score': change,
                            })
                    except Exception:
                        continue

            buy_candidates.sort(key=lambda x: -x['score'])
            log_fire(f"   [SCAN] Binance: {len(buy_candidates)} liquid UK USDC pairs found, testing top {max_candidates} with SEER")

            for candidate in buy_candidates[:max_candidates]:
                # ═══ BUY COOLDOWN CHECK ═══ (prevent hammering the same symbol every cycle)
                _pair_key_b = f"binance:{candidate['pair']}"
                _now_b = time.time()
                _last_b = self._recent_buys.get(_pair_key_b, 0)
                if _now_b - _last_b < self._BUY_COOLDOWN_SECS:
                    log_fire(f"   ⏳ COOLDOWN: {candidate['pair']} bought {int((_now_b - _last_b)/60)}m ago — skipping")
                    continue
                # ═══ SEER PER-SYMBOL CHECK ═══
                base_for_seer = candidate['pair'].replace('USDC', '').replace('USDT', '')
                sym_bullish, _sym_conf, sym_details = self._seer_symbol_signal(base_for_seer)
                if not sym_bullish:
                    # Seer BEARISH is a hard block — a 24h pump does not override a bearish signal.
                    log_fire(f"   🔮 SEER rejects {base_for_seer} — BEARISH, trying next")
                    continue
                if binance_cash < self._MIN_POSITION_USD:
                    log_fire(f"   [SKIP] Insufficient Binance cash (${binance_cash:.2f}) — minimum is ${self._MIN_POSITION_USD:.0f}")
                    break  # No point iterating — all Binance candidates face same cash shortage
                raw_qty = _buy_amount_binance(binance_cash)
                quote_qty = min(raw_qty * seer_risk_mod, binance_cash * 0.9)
                quote_qty = max(self._MIN_POSITION_USD, min(quote_qty, binance_cash * 0.95))
                log_fire(f"\n🎯 BUY OPPORTUNITY (Binance{' MICRO' if micro_mode else ''}): {candidate['pair']}")
                log_fire(f"   Price=${candidate['price']:.6f} | 24h={candidate['change']:+.2f}% | Vol=${candidate['volume']:.0f}")
                log_fire(f"   Seer risk_mod={seer_risk_mod:.2f} → qty=${quote_qty:.2f} USDC")
                try:
                    result = self._submit_and_confirm(
                        'binance', candidate['pair'], 'buy', quote_qty=quote_qty
                    )
                    receipt = result.get('receipt')
                    if result.get('status') == 'filled' and receipt is not None:
                        log_fire("💥 TERMINAL BUY FILL (Binance)")
                        self._record_buy_cost_basis(candidate['pair'], receipt, 'binance')
                        self._append_terminal_trade(receipt, 'BUY')
                        self._log_seer_prediction(
                            candidate['pair'], 'binance', receipt['filled_avg_price'],
                            seer_summary, sym_details, receipt,
                        )
                        self._recent_buys[f"binance:{candidate['pair']}"] = time.time()
                        self._persist_recent_buys()
                        bought_any = True
                        break
                    else:
                        log_fire(f"❌ Binance buy not confirmed: {result.get('status')}")
                        if result.get('status') in {'unresolved', 'suppressed_unresolved_duplicate'}:
                            break
                except Exception as e:
                    log_fire(f"❌ Binance buy failed closed ({candidate['pair']}): {e}")
                    break

        if not bought_any:
            log_fire("⚠️ No valid buy opportunities after scan")
        return sell_executed or bought_any

def main():
    # Only for standalone run
    trader = FireTrader()
    success = trader.run_fire_check()
    if success:
        print("\n✅ REAL TRADE EXECUTED!")
    else:
        print("\n❌ No trades executed")

if __name__ == '__main__':
    main()

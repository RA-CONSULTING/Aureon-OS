from __future__ import annotations

import time
import json
import os
import logging
import math
import copy
import inspect
import tempfile
import uuid
from datetime import datetime
from collections.abc import Mapping
from typing import Dict, List, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from aureon.trading.unified_exchange_client import MultiExchangeClient
    from aureon.intelligence.aureon_market_pulse import MarketPulse

logger = logging.getLogger(__name__)

RECEIPT_MAX_AGE_SECONDS = 60.0
RECEIPT_FUTURE_SKEW_SECONDS = 5.0


def _finite_number(value, *, positive=False):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number) or (positive and number <= 0):
        return None
    return number


def _timestamp(value):
    number = _finite_number(value, positive=True)
    if number is not None:
        return number
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return datetime.fromisoformat(value.strip().replace('Z', '+00:00')).timestamp()
    except (TypeError, ValueError, OverflowError):
        return None


def _canonical_symbol(value):
    symbol = str(value or '').upper().replace('/', '').replace('-', '').replace('_', '')
    if symbol.startswith('XBT'):
        symbol = 'BTC' + symbol[3:]
    if symbol.startswith('XDG'):
        symbol = 'DOGE' + symbol[3:]
    return symbol


def _quote_asset(value):
    symbol = _canonical_symbol(value)
    for quote in ('USDT', 'USDC', 'USD', 'GBP', 'EUR', 'BTC', 'ETH'):
        if symbol.endswith(quote) and len(symbol) > len(quote):
            return quote
    return None


def _provider_order_id(receipt):
    if not isinstance(receipt, Mapping):
        return None
    value = (
        receipt.get('provider_order_id')
        or receipt.get('orderId')
        or receipt.get('txid')
        or receipt.get('id')
    )
    value = str(value or '').strip()
    return value or None


def _provider_fill_ids(receipt):
    if not isinstance(receipt, Mapping):
        return []
    values = []
    direct = receipt.get('fill_id')
    if direct:
        values.append(str(direct).strip())
    for field in ('provider_trade_ids', 'provider_fill_ids'):
        raw = receipt.get(field)
        if isinstance(raw, (list, tuple)):
            values.extend(str(value).strip() for value in raw if str(value).strip())
    fills = receipt.get('fills')
    if isinstance(fills, list):
        for fill in fills:
            if not isinstance(fill, Mapping):
                continue
            value = (
                fill.get('tradeId')
                or fill.get('trade_id')
                or fill.get('activity_id')
                or fill.get('fill_id')
                or fill.get('id')
            )
            if value:
                values.append(str(value).strip())
    return list(dict.fromkeys(value for value in values if value))


def _receipt_problem(receipt, now=None, *, require_receipt_id=True):
    """Return a provenance error without replacing missing provider values."""
    if not isinstance(receipt, Mapping):
        return 'receipt is not a mapping'
    if receipt.get('data_status') != 'live':
        return 'receipt is not live evidence'
    if receipt.get('truth_status') not in {'real_observed', 'real_derived'}:
        return 'receipt is not real evidence'
    if receipt.get('generated_values') is not False:
        return 'receipt contains generated values'
    if not str(receipt.get('source_id') or '').strip():
        return 'receipt is missing source id'
    if require_receipt_id and not str(receipt.get('receipt_id') or '').strip():
        return 'receipt is missing receipt id'
    source_timestamp = _timestamp(receipt.get('source_timestamp'))
    received_at = _timestamp(receipt.get('received_at'))
    if source_timestamp is None or received_at is None:
        return 'receipt is missing valid source or received time'
    now = time.time() if now is None else now
    if source_timestamp > now + RECEIPT_FUTURE_SKEW_SECONDS or received_at > now + RECEIPT_FUTURE_SKEW_SECONDS:
        return 'receipt timestamp is in the future'
    if source_timestamp > received_at + RECEIPT_FUTURE_SKEW_SECONDS:
        return 'receipt was received before its provider timestamp'
    if now - source_timestamp > RECEIPT_MAX_AGE_SECONDS or now - received_at > RECEIPT_MAX_AGE_SECONDS:
        return 'receipt is stale'
    return None


def _complete_quote(receipt, *, exchange, symbol, now=None):
    problem = _receipt_problem(receipt, now)
    if problem:
        return None, problem
    if not str(receipt.get('source_id')).lower().startswith(str(exchange).lower()):
        return None, 'quote source does not match exchange'
    if _canonical_symbol(receipt.get('symbol')) != _canonical_symbol(symbol):
        return None, 'quote symbol does not match position'
    price = _finite_number(receipt.get('price'), positive=True)
    bid = _finite_number(receipt.get('bid'), positive=True)
    ask = _finite_number(receipt.get('ask'), positive=True)
    if price is None or bid is None or ask is None or ask < bid:
        return None, 'quote is missing a finite two-sided market'
    return price, None


def _complete_terminal_fill(
    receipt,
    *,
    exchange,
    symbol,
    side,
    expected_quantity,
    expected_order_id=None,
    now=None,
):
    problem = _receipt_problem(receipt, now, require_receipt_id=False)
    if problem:
        return None, problem
    if str(receipt.get('status') or '').upper() != 'FILLED':
        return None, 'order is not a terminal fill'
    if receipt.get('fill_receipt_complete') is not True:
        return None, 'fill receipt is incomplete'
    if receipt.get('eligible_for_accounting') is not True:
        return None, 'fill is not accounting eligible'
    if receipt.get('eligible_for_learning') is not True:
        return None, 'fill is not learning eligible'
    if receipt.get('reconciliation_required') is not False:
        return None, 'fill still requires reconciliation'
    order_id = _provider_order_id(receipt)
    if order_id is None:
        return None, 'fill is missing provider order id'
    if expected_order_id and order_id != str(expected_order_id):
        return None, 'fill order does not match pending close'
    if not str(receipt.get('source_id')).lower().startswith(str(exchange).lower()):
        return None, 'fill source does not match exchange'
    if _canonical_symbol(receipt.get('symbol')) != _canonical_symbol(symbol):
        return None, 'fill symbol does not match position'
    if str(receipt.get('side') or '').upper() != str(side).upper():
        return None, 'fill side does not match close intent'
    fill_ids = _provider_fill_ids(receipt)
    fee_currency = str(receipt.get('fee_currency') or receipt.get('fee_asset') or '').strip().upper()
    if not fill_ids or not fee_currency:
        return None, 'fill is missing provider fill or fee identity'
    filled_quantity = _finite_number(
        receipt.get('filled_qty')
        if receipt.get('filled_qty') is not None
        else receipt.get('filled_quantity')
        if receipt.get('filled_quantity') is not None
        else receipt.get('executedQty'),
        positive=True,
    )
    if filled_quantity is None:
        return None, 'fill is missing observed quantity'
    required_quantity = _finite_number(expected_quantity, positive=True)
    if expected_quantity is not None:
        if required_quantity is None:
            return None, 'order intent is missing requested quantity'
        tolerance = max(1e-12, required_quantity * 1e-8)
        if abs(filled_quantity - required_quantity) > tolerance:
            return None, 'fill quantity does not completely satisfy the order intent'
    fill_price = _finite_number(
        receipt.get('filled_avg_price')
        if receipt.get('filled_avg_price') is not None
        else receipt.get('fill_price')
        if receipt.get('fill_price') is not None
        else receipt.get('avgPrice')
        if receipt.get('avgPrice') is not None
        else receipt.get('price'),
        positive=True,
    )
    if fill_price is None:
        return None, 'fill is missing observed price'
    filled_notional = _finite_number(
        receipt.get('filled_notional')
        if receipt.get('filled_notional') is not None
        else receipt.get('cummulativeQuoteQty'),
        positive=True,
    )
    if filled_notional is None:
        return None, 'fill is missing observed notional'
    notional_tolerance = max(1e-8, filled_notional * 0.001)
    if abs(filled_notional - (filled_quantity * fill_price)) > notional_tolerance:
        return None, 'fill notional is inconsistent with quantity and price'
    fee = _finite_number(receipt.get('fee'), positive=False)
    if fee is None or fee < 0:
        return None, 'fill is missing observed fee'
    normalized = dict(receipt)
    normalized.update({
        '_provider_order_id': order_id,
        '_provider_fill_ids': fill_ids,
        '_filled_quantity': filled_quantity,
        '_filled_price': fill_price,
        '_filled_notional': filled_notional,
        '_fee': fee,
        '_fee_currency': fee_currency,
    })
    return normalized, None

class WarBand:
    """
    🏹⚔️ THE APACHE WAR BAND ⚔️🏹
    
    Autonomous Scout and Sniper unit that operates independently within the ecosystem.
    
    Components:
    - SCOUT (The Hunter): Finds targets based on metrics and deploys capital.
    - SNIPER (The Killer): Watches positions and executes kills for profit.
    
    🧬 ENHANCED: Consumes Mycelium neural outputs for smarter target selection.
    """
    
    def __init__(self, client: MultiExchangeClient, market_pulse: MarketPulse):
        self.client = client
        self.pulse = market_pulse
        self.state_file = 'aureon_kraken_state.json'
        self.external_intel: Dict[str, Dict[str, Any]] = {}
        self._started = False
        self._processed_fill_ids = set()
        # Mycelium reference (set by ecosystem wiring)
        self._mycelium = None
        
        # Configuration
        self.scout_size_usd = 12.0
        self.min_cash_required = 15.0
        self.scan_interval = 45
        self.last_scan_time = 0
        
        # War List (Fallback)
        self.fallback_targets = {
            'kraken': ['SOLUSD', 'ADAUSD', 'DOTUSD', 'LINKUSD', 'XRPUSD', 'XXBTZUSD', 'XETHZUSD', 'MATICUSD', 'DOGEUSD'],
            'binance': ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT', 'ADAUSDT', 'XRPUSDT'],
            'alpaca': ['BTC/USD', 'ETH/USD']
        }
        

    def start(self) -> bool:
        """Explicitly enable the component after the caller has wired real adapters."""
        if self._started:
            return True
        try:
            from aureon.core.aureon_baton_link import link_system
            link_system(__name__)
        except Exception as exc:
            logger.warning('War Band remains inert: baton link unavailable: %s', exc)
            return False
        self._started = True
        return True

    @staticmethod
    def _no_data(reason: str, *, status: str = 'no_data', **context: Any) -> Dict[str, Any]:
        receipt = {
            'status': status,
            'data_status': 'no_data',
            'truth_status': 'no_data',
            'generated_values': False,
            'reason': reason,
            'actionable': False,
            'publication_allowed': False,
            'learning_allowed': False,
            'accounting_allowed': False,
        }
        receipt.update(context)
        return receipt

    def _adapter_objects(self, exchange: str):
        """Yield configured adapters without constructing or contacting providers."""
        seen = set()
        candidates = [self.client]
        clients = getattr(self.client, 'clients', None)
        if isinstance(clients, Mapping):
            wrapper = clients.get(exchange)
            if wrapper is not None:
                candidates.append(wrapper)
                nested = getattr(wrapper, 'client', None)
                if nested is not None:
                    candidates.append(nested)
        for candidate in candidates:
            identity = id(candidate)
            if identity in seen:
                continue
            seen.add(identity)
            yield candidate

    @staticmethod
    def _invoke_adapter(method, exchange: str, value: str):
        """Call one selected adapter method once using its declared positional shape."""
        try:
            parameters = tuple(inspect.signature(method).parameters.values())
        except (TypeError, ValueError):
            parameters = ()
        positional = tuple(
            parameter
            for parameter in parameters
            if parameter.kind in {
                inspect.Parameter.POSITIONAL_ONLY,
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
            }
        )
        has_varargs = any(parameter.kind == inspect.Parameter.VAR_POSITIONAL for parameter in parameters)
        if has_varargs or len(positional) >= 2:
            return method(exchange, value)
        return method(value)

    def _get_quote_receipt(self, exchange: str, symbol: str):
        """Select one receipt-capable quote route; never cascade provider calls."""
        adapters = tuple(self._adapter_objects(exchange))
        for method_name in ('get_ticker_receipt', 'get_ticker'):
            for adapter in adapters:
                method = getattr(adapter, method_name, None)
                if not callable(method):
                    continue
                try:
                    return self._invoke_adapter(method, exchange, symbol), None
                except Exception as exc:
                    logger.warning('War Band quote route failed closed for %s:%s: %s', exchange, symbol, exc)
                    return None, 'quote receipt route failed'
        return None, 'quote receipt route unavailable'

    def _order_readback_reader(self, exchange: str):
        """Resolve a single-order, preferably fee-complete readback without calling it."""
        adapters = tuple(self._adapter_objects(exchange))
        for method_name in ('get_order_with_fees', 'get_order_status', 'get_order_receipt', 'get_order'):
            for adapter in adapters:
                method = getattr(adapter, method_name, None)
                if callable(method):
                    return method
        return None

    @staticmethod
    def _position_problem(position: Any, *, exchange: str, symbol: str):
        """Require historical provider fill and fee provenance before an automated close."""
        if not isinstance(position, Mapping):
            return 'position is not a mapping'
        if str(position.get('exchange') or '').lower() != str(exchange).lower():
            return 'position exchange is missing or inconsistent'
        if _canonical_symbol(position.get('symbol')) != _canonical_symbol(symbol):
            return 'position symbol is missing or inconsistent'
        quantity = _finite_number(position.get('quantity'), positive=True)
        entry_value = _finite_number(position.get('entry_value'), positive=True)
        entry_fee = _finite_number(position.get('entry_fee'))
        if quantity is None or entry_value is None or entry_fee is None or entry_fee < 0:
            return 'position quantity, entry value, or entry fee is incomplete'
        quote_currency = str(position.get('quote_currency') or '').strip().upper()
        entry_fee_currency = str(position.get('entry_fee_currency') or '').strip().upper()
        if not quote_currency or entry_fee_currency != quote_currency:
            return 'position entry fee currency is not proven in its quote currency'
        if position.get('entry_fill_receipt_complete') is not True:
            return 'position lacks a complete entry fill receipt'
        if position.get('entry_accounting_eligible') is not True:
            return 'position entry is not accounting eligible'
        if position.get('truth_status') not in {'real_observed', 'real_derived'}:
            return 'position is not backed by real provider evidence'
        if position.get('generated_values') is not False:
            return 'position contains generated or unknown values'
        if not str(position.get('source_id') or '').lower().startswith(str(exchange).lower()):
            return 'position source does not match exchange'
        if _timestamp(position.get('source_timestamp')) is None or _timestamp(position.get('received_at')) is None:
            return 'position entry timestamps are incomplete'
        if not str(position.get('entry_order_id') or '').strip():
            return 'position entry order identity is missing'
        entry_fill_ids = position.get('entry_fill_ids')
        if not isinstance(entry_fill_ids, list) or not any(str(value).strip() for value in entry_fill_ids):
            return 'position entry fill identity is missing'
        return None

    def set_mycelium(self, mycelium) -> None:
        """Wire Mycelium reference for neural-guided targeting."""
        self._mycelium = mycelium

    def _neural_target_score(self, symbol: str, exchange: str) -> float:
        """Get neural score for a target (higher = better)."""
        if self._mycelium is None:
            return 1.0
        try:
            mem = self._mycelium.get_symbol_memory(symbol)
            friction = self._mycelium.get_exchange_friction(exchange)
            queen = self._mycelium.get_queen_signal()
            coherence = self._mycelium.get_network_coherence()
            
            wr = float(mem.get('win_rate', 0.5))
            act = float(mem.get('activation', 0.5))
            # Penalize exchanges with high recent rejections
            friction_penalty = 1.0 - min(0.5, friction.get('reject_count', 0) * 0.05)
            # Bullish queen + high coherence = boost
            queen_factor = 1.0 + 0.15 * queen
            coh_factor = 0.6 + 0.4 * coherence
            
            return wr * act * friction_penalty * queen_factor * coh_factor
        except Exception:
            return 1.0

    def ingest_intel(self, symbol: str, exchange: str, eta_seconds: float = None,
                     probability: float = None, confidence: float = None,
                     mycelium_coherence: float = None, queen_signal: float = None,
                     receipt: Dict[str, Any] = None):
        """Record external sniper/mycelium intel so the band has situational awareness."""
        problem = _receipt_problem(receipt)
        values = (eta_seconds, probability, confidence, mycelium_coherence, queen_signal)
        if problem or any(value is not None and _finite_number(value) is None for value in values):
            return self._no_data(problem or 'intel contains non-finite values')
        key = f"{exchange}:{symbol}"
        self.external_intel[key] = {
            'eta_seconds': eta_seconds,
            'probability': probability,
            'confidence': confidence,
            'mycelium_coherence': mycelium_coherence,
            'queen_signal': queen_signal,
            'source_id': receipt['source_id'],
            'source_timestamp': receipt['source_timestamp'],
            'received_at': receipt['received_at'],
            'receipt_id': receipt['receipt_id'],
            'truth_status': receipt['truth_status'],
            'generated_values': False,
        }
        return {'data_status': 'accepted', 'actionable': False}

    def get_state(self) -> Dict:
        try:
            if os.path.exists(self.state_file):
                with open(self.state_file, 'r') as f:
                    state = json.load(f)
                    if isinstance(state, dict) and isinstance(state.get('positions', {}), dict):
                        return state
            return {'positions': {}, 'kills': []}
        except Exception as exc:
            logger.error('War Band state read failed closed: %s', exc)
            return {'positions': {}, 'kills': []}

    def save_state(self, state: Dict):
        """Atomically persist safety latches before any order submission."""
        target = os.path.abspath(self.state_file)
        directory = os.path.dirname(target)
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(
                mode='w',
                encoding='utf-8',
                dir=directory,
                prefix=os.path.basename(target) + '.',
                suffix='.tmp',
                delete=False,
            ) as handle:
                temporary = handle.name
                json.dump(state, handle, indent=2, sort_keys=True)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, target)
            return True
        except Exception as exc:
            logger.error('War Band state write failed closed: %s', exc)
            if temporary and os.path.exists(temporary):
                try:
                    os.unlink(temporary)
                except OSError:
                    pass
            return False

    def update(self):
        """Main update loop called by the ecosystem"""
        if not self._started:
            return self._no_data('War Band has not been explicitly started')
        current_time = time.time()
        
        # Run Sniper (Every update)
        self._run_sniper()

        # Light-touch intel decay to keep the cache fresh
        stale = [k for k, v in self.external_intel.items() if current_time - float(v['received_at']) > 900]
        for k in stale:
            self.external_intel.pop(k, None)
        
        # Run Scout (Interval based)
        if current_time - self.last_scan_time > self.scan_interval:
            self._run_scout()
            self.last_scan_time = current_time

    def _run_sniper(self):
        """Check receipt-proven positions without substituting provider defaults."""
        state = self.get_state()
        positions = state.get('positions', {})
        
        if not positions:
            return self._no_data('no receipt-proven positions')

        outcomes = []
        for symbol, pos in list(positions.items()):
            try:
                exchange = str(pos.get('exchange') or '').strip().lower()
                problem = self._position_problem(pos, exchange=exchange, symbol=symbol)
                if problem:
                    outcomes.append(self._no_data(problem, symbol=symbol, exchange=exchange))
                    continue
                if isinstance(pos.get('pending_close'), Mapping):
                    outcomes.append(self._reconcile_pending_close(exchange, symbol, state))
                    continue

                qty = _finite_number(pos.get('quantity'), positive=True)
                entry_value = _finite_number(pos.get('entry_value'), positive=True)
                ticker, route_problem = self._get_quote_receipt(exchange, symbol)
                current_price, quote_problem = _complete_quote(
                    ticker,
                    exchange=exchange,
                    symbol=symbol,
                )
                if route_problem or quote_problem:
                    outcomes.append(
                        self._no_data(
                            route_problem or quote_problem,
                            symbol=symbol,
                            exchange=exchange,
                        )
                    )
                    continue
                
                current_value = qty * current_price
                
                # Calculate P&L
                # Fees: 0.26% taker * 2 (entry+exit) + slippage buffer
                fees = entry_value * 0.006 
                gross_pnl = current_value - entry_value
                net_pnl = gross_pnl - fees
                
                # KILL CONDITION: Net Profit >= $0.01
                if net_pnl >= 0.0001:
                    print(f"   🔫 SNIPER: Target Acquired {symbol} (+${net_pnl:.4f})")
                    outcomes.append(
                        self._execute_kill(
                            exchange,
                            symbol,
                            qty,
                            entry_value,
                            current_value,
                            net_pnl,
                            state,
                        )
                    )
                else:
                    outcomes.append(
                        self._no_data(
                            'receipt-proven close threshold not reached',
                            symbol=symbol,
                            exchange=exchange,
                            quote_receipt_id=ticker.get('receipt_id'),
                        )
                    )
                    
            except Exception as exc:
                logger.exception('War Band sniper failed closed for %s: %s', symbol, exc)
                outcomes.append(self._no_data('sniper evaluation failed closed', symbol=symbol))
        if len(outcomes) == 1:
            return outcomes[0]
        return {
            'status': 'evaluated',
            'data_status': 'real_derived',
            'truth_status': 'real_derived',
            'generated_values': False,
            'actionable': False,
            'outcomes': outcomes,
        }

    def _execute_kill(self, exchange, symbol, qty, entry_val, exit_val, pnl, state):
        """Submit once behind a durable ambiguity latch, then reconcile separately."""
        del entry_val, exit_val
        position = state.get('positions', {}).get(symbol)
        problem = self._position_problem(position, exchange=exchange, symbol=symbol)
        if problem:
            return self._no_data(problem, status='not_submitted', symbol=symbol, exchange=exchange)
        if isinstance(position.get('pending_close'), Mapping):
            return self._reconcile_pending_close(exchange, symbol, state)

        reader = self._order_readback_reader(exchange)
        if reader is None:
            return self._no_data(
                'fee-complete single-order readback unavailable',
                status='not_submitted',
                symbol=symbol,
                exchange=exchange,
            )

        intent = {
            'intent_id': 'close-' + uuid.uuid4().hex,
            'status': 'submission_attempt_uncertain',
            'symbol': symbol,
            'exchange': exchange,
            'side': 'SELL',
            'requested_quantity': qty,
            'position_entry_order_id': position.get('entry_order_id'),
            'position_entry_fill_ids': list(position.get('entry_fill_ids') or []),
            'submission_attempted': True,
            'provider_order_id': None,
            'latched_at': time.time(),
            'projected_net_pnl': pnl,
            'truth_status': 'internal_control',
            'generated_values': False,
        }
        latched = copy.deepcopy(state)
        latched['positions'][symbol]['pending_close'] = intent
        if not self.save_state(latched):
            return self._no_data(
                'close safety latch could not be persisted',
                status='not_submitted',
                symbol=symbol,
                exchange=exchange,
            )
        state.clear()
        state.update(latched)

        try:
            result = self.client.place_market_order(exchange, symbol, 'SELL', quantity=qty)
        except Exception as exc:
            logger.error('War Band close submission became ambiguous for %s: %s', symbol, exc)
            return self._no_data(
                'close submission outcome is ambiguous; automatic retry disabled',
                status='pending_reconciliation',
                symbol=symbol,
                exchange=exchange,
                pending_intent_id=intent['intent_id'],
            )

        terminal, terminal_problem = _complete_terminal_fill(
            result,
            exchange=exchange,
            symbol=symbol,
            side='SELL',
            expected_quantity=qty,
        )
        if terminal is not None:
            return self._settle_terminal_close(state, symbol, terminal)

        order_id = _provider_order_id(result)
        pending = copy.deepcopy(state)
        pending_intent = pending['positions'][symbol]['pending_close']
        pending_intent['provider_order_id'] = order_id
        pending_intent['status'] = (
            'pending_reconciliation' if order_id else 'ambiguous_submission'
        )
        pending_intent['submission_receipt_source_id'] = (
            result.get('source_id') if isinstance(result, Mapping) else None
        )
        pending_intent['last_reason'] = terminal_problem
        if self.save_state(pending):
            state.clear()
            state.update(pending)
        return self._no_data(
            terminal_problem or 'terminal fill receipt pending',
            status='pending_reconciliation',
            symbol=symbol,
            exchange=exchange,
            pending_intent_id=intent['intent_id'],
            provider_order_id=order_id,
        )

    def _reconcile_pending_close(self, exchange: str, symbol: str, state: Dict[str, Any]):
        """Perform at most one provider readback and never resubmit a latched close."""
        position = state.get('positions', {}).get(symbol)
        if not isinstance(position, Mapping):
            return self._no_data('pending close position is missing', symbol=symbol, exchange=exchange)
        pending = position.get('pending_close')
        if not isinstance(pending, Mapping):
            return self._no_data('pending close latch is missing', symbol=symbol, exchange=exchange)
        quantity = _finite_number(position.get('quantity'), positive=True)
        pending_quantity = _finite_number(pending.get('requested_quantity'), positive=True)
        if (
            str(pending.get('exchange') or '').lower() != str(exchange).lower()
            or _canonical_symbol(pending.get('symbol')) != _canonical_symbol(symbol)
            or str(pending.get('side') or '').upper() != 'SELL'
            or quantity is None
            or pending_quantity is None
            or abs(quantity - pending_quantity) > max(1e-12, quantity * 1e-8)
        ):
            return self._no_data(
                'pending close latch does not match position',
                status='pending_reconciliation',
                symbol=symbol,
                exchange=exchange,
            )
        order_id = str(pending.get('provider_order_id') or '').strip()
        if not order_id:
            return self._no_data(
                'ambiguous submission has no provider order id; automatic retry disabled',
                status='pending_reconciliation',
                symbol=symbol,
                exchange=exchange,
                pending_intent_id=pending.get('intent_id'),
            )
        reader = self._order_readback_reader(exchange)
        if reader is None:
            return self._no_data(
                'single-order readback unavailable; automatic retry disabled',
                status='pending_reconciliation',
                symbol=symbol,
                exchange=exchange,
                provider_order_id=order_id,
            )
        try:
            receipt = self._invoke_adapter(reader, exchange, order_id)
        except Exception as exc:
            logger.warning('War Band close readback failed closed for %s: %s', symbol, exc)
            return self._no_data(
                'provider close readback failed; automatic retry disabled',
                status='pending_reconciliation',
                symbol=symbol,
                exchange=exchange,
                provider_order_id=order_id,
            )
        terminal, problem = _complete_terminal_fill(
            receipt,
            exchange=exchange,
            symbol=symbol,
            side='SELL',
            expected_quantity=quantity,
            expected_order_id=order_id,
        )
        if terminal is None:
            return self._no_data(
                problem,
                status='pending_reconciliation',
                symbol=symbol,
                exchange=exchange,
                provider_order_id=order_id,
            )
        return self._settle_terminal_close(state, symbol, terminal)

    def _settle_terminal_close(self, state: Dict[str, Any], symbol: str, receipt: Mapping[str, Any]):
        """Atomically book one complete terminal close using observed provider values."""
        position = state.get('positions', {}).get(symbol)
        if not isinstance(position, Mapping):
            return self._no_data('terminal close position is missing', symbol=symbol)
        exchange = str(position.get('exchange') or '').lower()
        problem = self._position_problem(position, exchange=exchange, symbol=symbol)
        if problem:
            return self._no_data(problem, symbol=symbol, exchange=exchange)
        quote_currency = str(position.get('quote_currency') or '').upper()
        if receipt.get('_fee_currency') != quote_currency:
            return self._no_data(
                'exit fee is not observed in the position quote currency',
                symbol=symbol,
                exchange=exchange,
            )

        order_id = str(receipt['_provider_order_id'])
        fill_ids = list(receipt['_provider_fill_ids'])
        receipt_id = str(receipt.get('receipt_id') or '').strip() or None
        settled_orders = set(state.get('settled_provider_order_ids', []) or [])
        settled_fills = set(state.get('settled_provider_fill_ids', []) or [])
        settled_receipts = set(state.get('settled_terminal_receipt_ids', []) or [])
        if (
            order_id in settled_orders
            or any(fill_id in settled_fills for fill_id in fill_ids)
            or (receipt_id is not None and receipt_id in settled_receipts)
            or any(fill_id in self._processed_fill_ids for fill_id in fill_ids)
        ):
            return self._no_data(
                'duplicate terminal close receipt',
                symbol=symbol,
                exchange=exchange,
                provider_order_id=order_id,
            )

        entry_value = _finite_number(position.get('entry_value'), positive=True)
        entry_fee = _finite_number(position.get('entry_fee'))
        realized_net_pnl = (
            float(receipt['_filled_notional'])
            - entry_value
            - entry_fee
            - float(receipt['_fee'])
        )
        updated = copy.deepcopy(state)
        del updated['positions'][symbol]
        updated.setdefault('kills', []).append({
            'symbol': symbol,
            'exchange': exchange,
            'time': _timestamp(receipt.get('source_timestamp')),
            'net_pnl': realized_net_pnl,
            'entry_value': entry_value,
            'entry_fee': entry_fee,
            'exit_notional': float(receipt['_filled_notional']),
            'exit_fee': float(receipt['_fee']),
            'fee_currency': quote_currency,
            'order_id': order_id,
            'provider_fill_ids': fill_ids,
            'receipt_id': receipt_id,
            'source_id': receipt.get('source_id'),
            'source_timestamp': receipt.get('source_timestamp'),
            'received_at': receipt.get('received_at'),
            'truth_status': receipt.get('truth_status'),
            'generated_values': False,
            'accounting_status': 'terminal_fill_settled',
        })
        updated['settled_provider_order_ids'] = (
            list(updated.get('settled_provider_order_ids', []) or []) + [order_id]
        )[-1000:]
        updated['settled_provider_fill_ids'] = (
            list(updated.get('settled_provider_fill_ids', []) or []) + fill_ids
        )[-5000:]
        if receipt_id is not None:
            updated['settled_terminal_receipt_ids'] = (
                list(updated.get('settled_terminal_receipt_ids', []) or []) + [receipt_id]
            )[-1000:]
        if not self.save_state(updated):
            return self._no_data(
                'terminal close could not be atomically persisted',
                status='pending_reconciliation',
                symbol=symbol,
                exchange=exchange,
                provider_order_id=order_id,
            )
        state.clear()
        state.update(updated)
        self._processed_fill_ids.update(fill_ids)
        return {
            'status': 'terminal_fill_settled',
            'data_status': 'live',
            'truth_status': 'real_derived',
            'generated_values': False,
            'actionable': False,
            'accounting_allowed': True,
            'learning_allowed': True,
            'symbol': symbol,
            'exchange': exchange,
            'provider_order_id': order_id,
            'provider_fill_ids': fill_ids,
            'realized_net_pnl': realized_net_pnl,
        }

    def _run_scout(self):
        """The Hunter: Finds targets and deploys capital"""
        try:
            # 1. Load State
            state = self.get_state()
            current_positions = state.get('positions', {})
            held_symbols = [p.get('symbol') for p in current_positions.values()]
            
            # 2. Analyze Market
            market_data = self.pulse.analyze_market()
            top_gainers = market_data.get('top_gainers', [])
            arb_opps = market_data.get('arbitrage_opportunities', [])
            
            # 3. Check Cash & Deploy
            balances = self.client.get_all_balances()
            
            for exchange in ['kraken', 'binance', 'alpaca']:
                cash = self._get_cash(exchange, balances)
                
                if cash >= self.min_cash_required:
                    target, reason = self._select_target(exchange, held_symbols, top_gainers, arb_opps)

                    # Prefer externally-intel'd targets if available and not held
                    ext_key = None
                    for k in sorted(self.external_intel.keys()):
                        if k.startswith(f"{exchange}:"):
                            sym = k.split(":", 1)[1]
                            if sym not in held_symbols:
                                target = sym
                                intel = self.external_intel[k]
                                reason = f"External intel p={intel.get('probability', 'na')} eta={intel.get('eta_seconds', 'na')}"
                                ext_key = k
                                break
                    
                    if target:
                        self._deploy_scout(exchange, target, reason, state)
                        if ext_key:
                            self.external_intel.pop(ext_key, None)
                    
        except Exception as e:
            print(f"   ⚠️ Scout Patrol Error: {e}")

    def _get_cash(self, exchange, balances):
        if exchange == 'kraken':
            return float(balances.get('kraken', {}).get('ZUSD', {}).get('free', 0) if isinstance(balances.get('kraken', {}).get('ZUSD'), dict) else balances.get('kraken', {}).get('ZUSD', 0))
        elif exchange == 'binance':
            cash = float(balances.get('binance', {}).get('USDC', {}).get('free', 0) if isinstance(balances.get('binance', {}).get('USDC'), dict) else balances.get('binance', {}).get('USDC', 0))
            if cash < self.scout_size_usd:
                usdt = float(balances.get('binance', {}).get('USDT', {}).get('free', 0) if isinstance(balances.get('binance', {}).get('USDT'), dict) else balances.get('binance', {}).get('USDT', 0))
                if usdt > cash: return usdt
            return cash
        elif exchange == 'alpaca':
            return float(balances.get('alpaca', {}).get('USD', {}).get('free', 0) if isinstance(balances.get('alpaca', {}).get('USD'), dict) else balances.get('alpaca', {}).get('USD', 0))
        return 0.0

    def _select_target(self, exchange, held_symbols, top_gainers, arb_opps):
        # 1. Arbitrage (score-weighted if multiple)
        arb_candidates = [arb for arb in arb_opps if arb['buy_at']['source'] == exchange and arb['buy_at']['symbol'] not in held_symbols]
        if arb_candidates:
            # Pick the one with best neural score
            arb_candidates.sort(key=lambda a: self._neural_target_score(a['buy_at']['symbol'], exchange), reverse=True)
            best = arb_candidates[0]
            return best['buy_at']['symbol'], f"Arbitrage (+{best['spread_pct']:.2f}%)"
        
        # 2. Momentum (score-weighted)
        exch_gainers = [t for t in top_gainers if t.get('source') == exchange and t.get('symbol') not in held_symbols]
        if exch_gainers:
            exch_gainers.sort(key=lambda t: self._neural_target_score(t.get('symbol', ''), exchange), reverse=True)
            best = exch_gainers[0]
            return best.get('symbol'), f"Top Gainer (+{best.get('priceChangePercent', 0)}%)"
            
        # 3. Fallback (score-weighted)
        available = [t for t in self.fallback_targets.get(exchange, []) if t not in held_symbols]
        if available:
            available.sort(key=lambda t: self._neural_target_score(t, exchange), reverse=True)
            return available[0], "Neural Patrol"
            
        return None, None

    def _deploy_scout(self, exchange, target, reason, state):
        """Submit an entry once and create a position only from a terminal fill."""
        exchange = str(exchange or '').strip().lower()
        pending_key = f"{exchange}:{_canonical_symbol(target)}"
        pending_entries = state.get('pending_entries', {})
        if isinstance(pending_entries, Mapping) and pending_key in pending_entries:
            return self._reconcile_pending_entry(exchange, target, pending_key, state)

        ticker, route_problem = self._get_quote_receipt(exchange, target)
        price, quote_problem = _complete_quote(
            ticker,
            exchange=exchange,
            symbol=target,
        )
        if route_problem or quote_problem:
            return self._no_data(
                route_problem or quote_problem,
                status='not_submitted',
                symbol=target,
                exchange=exchange,
            )
        reader = self._order_readback_reader(exchange)
        if reader is None:
            return self._no_data(
                'fee-complete single-order readback unavailable',
                status='not_submitted',
                symbol=target,
                exchange=exchange,
            )

        intent = {
            'intent_id': 'entry-' + uuid.uuid4().hex,
            'status': 'submission_attempt_uncertain',
            'symbol': target,
            'exchange': exchange,
            'side': 'BUY',
            'requested_quote_quantity': self.scout_size_usd,
            'submission_attempted': True,
            'provider_order_id': None,
            'latched_at': time.time(),
            'quote_receipt_id': ticker.get('receipt_id'),
            'quote_source_id': ticker.get('source_id'),
            'truth_status': 'internal_control',
            'generated_values': False,
            'strategy': reason,
        }
        latched = copy.deepcopy(state)
        latched.setdefault('pending_entries', {})[pending_key] = intent
        if not self.save_state(latched):
            return self._no_data(
                'entry safety latch could not be persisted',
                status='not_submitted',
                symbol=target,
                exchange=exchange,
            )
        state.clear()
        state.update(latched)

        try:
            result = self.client.place_market_order(
                exchange,
                target,
                'BUY',
                quote_qty=self.scout_size_usd,
            )
        except Exception as exc:
            logger.error('War Band entry submission became ambiguous for %s: %s', target, exc)
            return self._no_data(
                'entry submission outcome is ambiguous; automatic retry disabled',
                status='pending_reconciliation',
                symbol=target,
                exchange=exchange,
                pending_intent_id=intent['intent_id'],
            )

        terminal, terminal_problem = _complete_terminal_fill(
            result,
            exchange=exchange,
            symbol=target,
            side='BUY',
            expected_quantity=None,
        )
        if terminal is not None:
            return self._settle_terminal_entry(
                state,
                target,
                pending_key,
                reason,
                terminal,
            )

        order_id = _provider_order_id(result)
        pending = copy.deepcopy(state)
        pending_intent = pending['pending_entries'][pending_key]
        pending_intent['provider_order_id'] = order_id
        pending_intent['status'] = (
            'pending_reconciliation' if order_id else 'ambiguous_submission'
        )
        pending_intent['submission_receipt_source_id'] = (
            result.get('source_id') if isinstance(result, Mapping) else None
        )
        pending_intent['last_reason'] = terminal_problem
        if self.save_state(pending):
            state.clear()
            state.update(pending)
        return self._no_data(
            terminal_problem or 'terminal entry fill receipt pending',
            status='pending_reconciliation',
            symbol=target,
            exchange=exchange,
            pending_intent_id=intent['intent_id'],
            provider_order_id=order_id,
        )

    def _reconcile_pending_entry(
        self,
        exchange: str,
        target: str,
        pending_key: str,
        state: Dict[str, Any],
    ):
        """Read one provider order once per invocation; never resubmit an entry."""
        pending = state.get('pending_entries', {}).get(pending_key)
        if not isinstance(pending, Mapping):
            return self._no_data('pending entry latch is missing', symbol=target, exchange=exchange)
        if (
            str(pending.get('exchange') or '').lower() != exchange
            or _canonical_symbol(pending.get('symbol')) != _canonical_symbol(target)
            or str(pending.get('side') or '').upper() != 'BUY'
        ):
            return self._no_data(
                'pending entry latch does not match target',
                status='pending_reconciliation',
                symbol=target,
                exchange=exchange,
            )
        order_id = str(pending.get('provider_order_id') or '').strip()
        if not order_id:
            return self._no_data(
                'ambiguous entry submission has no provider order id; automatic retry disabled',
                status='pending_reconciliation',
                symbol=target,
                exchange=exchange,
                pending_intent_id=pending.get('intent_id'),
            )
        reader = self._order_readback_reader(exchange)
        if reader is None:
            return self._no_data(
                'single-order entry readback unavailable; automatic retry disabled',
                status='pending_reconciliation',
                symbol=target,
                exchange=exchange,
                provider_order_id=order_id,
            )
        try:
            receipt = self._invoke_adapter(reader, exchange, order_id)
        except Exception as exc:
            logger.warning('War Band entry readback failed closed for %s: %s', target, exc)
            return self._no_data(
                'provider entry readback failed; automatic retry disabled',
                status='pending_reconciliation',
                symbol=target,
                exchange=exchange,
                provider_order_id=order_id,
            )
        terminal, problem = _complete_terminal_fill(
            receipt,
            exchange=exchange,
            symbol=target,
            side='BUY',
            expected_quantity=None,
            expected_order_id=order_id,
        )
        if terminal is None:
            return self._no_data(
                problem,
                status='pending_reconciliation',
                symbol=target,
                exchange=exchange,
                provider_order_id=order_id,
            )
        return self._settle_terminal_entry(
            state,
            target,
            pending_key,
            pending.get('strategy'),
            terminal,
        )

    def _settle_terminal_entry(
        self,
        state: Dict[str, Any],
        target: str,
        pending_key: str,
        reason: Any,
        receipt: Mapping[str, Any],
    ):
        """Create one position from observed provider quantity, notional, and fee."""
        pending = state.get('pending_entries', {}).get(pending_key)
        if not isinstance(pending, Mapping):
            return self._no_data('terminal entry has no durable intent', symbol=target)
        exchange = str(pending.get('exchange') or '').lower()
        quote_currency = _quote_asset(target)
        if quote_currency is None or receipt.get('_fee_currency') != quote_currency:
            return self._no_data(
                'entry fee is not observed in the market quote currency',
                symbol=target,
                exchange=exchange,
            )
        if target in state.get('positions', {}):
            return self._no_data(
                'position already exists for terminal entry',
                symbol=target,
                exchange=exchange,
            )

        order_id = str(receipt['_provider_order_id'])
        fill_ids = list(receipt['_provider_fill_ids'])
        observed_orders = set(state.get('observed_entry_order_ids', []) or [])
        observed_fills = set(state.get('observed_entry_fill_ids', []) or [])
        if order_id in observed_orders or any(fill_id in observed_fills for fill_id in fill_ids):
            return self._no_data(
                'duplicate terminal entry receipt',
                symbol=target,
                exchange=exchange,
                provider_order_id=order_id,
            )

        updated = copy.deepcopy(state)
        updated.setdefault('pending_entries', {}).pop(pending_key, None)
        updated.setdefault('positions', {})[target] = {
            'symbol': target,
            'exchange': exchange,
            'entry_price': float(receipt['_filled_price']),
            'quantity': float(receipt['_filled_quantity']),
            'entry_value': float(receipt['_filled_notional']),
            'entry_fee': float(receipt['_fee']),
            'entry_fee_currency': quote_currency,
            'quote_currency': quote_currency,
            'entry_time': _timestamp(receipt.get('source_timestamp')),
            'is_scout': True,
            'strategy': reason,
            'entry_order_id': order_id,
            'entry_fill_ids': fill_ids,
            'entry_fill_receipt_complete': True,
            'entry_accounting_eligible': True,
            'source_id': receipt.get('source_id'),
            'source_timestamp': receipt.get('source_timestamp'),
            'received_at': receipt.get('received_at'),
            'receipt_id': receipt.get('receipt_id'),
            'truth_status': receipt.get('truth_status'),
            'generated_values': False,
        }
        updated['observed_entry_order_ids'] = (
            list(updated.get('observed_entry_order_ids', []) or []) + [order_id]
        )[-1000:]
        updated['observed_entry_fill_ids'] = (
            list(updated.get('observed_entry_fill_ids', []) or []) + fill_ids
        )[-5000:]
        if not self.save_state(updated):
            return self._no_data(
                'terminal entry could not be atomically persisted',
                status='pending_reconciliation',
                symbol=target,
                exchange=exchange,
                provider_order_id=order_id,
            )
        state.clear()
        state.update(updated)
        return {
            'status': 'terminal_entry_settled',
            'data_status': 'live',
            'truth_status': 'real_derived',
            'generated_values': False,
            'actionable': False,
            'accounting_allowed': True,
            'learning_allowed': True,
            'symbol': target,
            'exchange': exchange,
            'provider_order_id': order_id,
            'provider_fill_ids': fill_ids,
        }

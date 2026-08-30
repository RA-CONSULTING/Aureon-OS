#!/usr/bin/env python3
"""
🌊 AUREON QGITA ENGINE - BTC PAIRS MODE 🌊

Your account (TRD_GRP_039) can only trade BTC pairs, not USDT pairs!

Strategy:
  - Sell altcoins via BTC pairs (LINKBTC, ADABTC, etc.)
  - Trade BTC pairs for compounding
  - Use the 9 Auris Nodes for entry/exit signals

Author: Gary Leckey / Aureon System
"""
from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import os, sys, time, logging, argparse, math
from typing import Any, Dict, List, Optional
from decimal import Decimal, InvalidOperation
from aureon.exchanges.binance_client import BinanceClient, get_binance_client

# 🪙 PENNY PROFIT ENGINE
try:
    from aureon.trading.penny_profit_engine import check_penny_exit, get_penny_engine
    PENNY_PROFIT_AVAILABLE = True
    _penny_engine = get_penny_engine()
    print("🪙 Penny Profit Engine loaded for BTC Trader")
except ImportError:
    PENNY_PROFIT_AVAILABLE = False
    _penny_engine = None
    print("⚠️ Penny Profit Engine not available")

# 🧠 WISDOM COGNITION ENGINE - 11 Civilizations
try:
    from aureon.utils.aureon_miner_brain import WisdomCognitionEngine
    WISDOM_AVAILABLE = True
    _wisdom_engine = WisdomCognitionEngine()
    print("🧠 Wisdom Engine loaded - 11 civilizations ready")
except ImportError:
    WISDOM_AVAILABLE = False
    _wisdom_engine = None
    print("⚠️ Wisdom Engine not available")

try:
    from dotenv import load_dotenv
    load_dotenv()
except:
    pass

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('aureon_btc.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════

CONFIG = {
    'ACCOUNT_GROUP': 'TRD_GRP_039',  # Your trading group
    'MIN_BTC_VALUE': 0.0001,         # Minimum trade size in BTC (~$10)
    'MAX_POSITIONS': 8,
    'STOP_LOSS_PCT': 0.015,          # 1.5%
    'TAKE_PROFIT_PCT': 0.025,        # 2.5%
}

TICKER_MAX_AGE_SECONDS = 120.0
ACCOUNT_MAX_AGE_SECONDS = 300.0
ORDER_MAX_AGE_SECONDS = 300.0


def _finite_number(
    value: Any,
    *,
    positive: bool = False,
    nonnegative: bool = False,
) -> Optional[float]:
    """Parse a provider number without substituting a missing observation."""
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
    now: Optional[float] = None,
) -> Optional[float]:
    """Return a provider timestamp only when it is finite and currently fresh."""
    parsed = _finite_number(value, positive=True)
    if parsed is None:
        return None
    if parsed > 10_000_000_000:
        parsed /= 1000.0
    observed_now = time.time() if now is None else now
    if parsed > observed_now + 5.0 or observed_now - parsed > max_age_seconds:
        return None
    return parsed


def _close_enough(left: float, right: float) -> bool:
    tolerance = max(1e-12, abs(right) * 1e-8)
    return abs(left - right) <= tolerance

# ═══════════════════════════════════════════════════════════════════════════
# LOT SIZE MANAGER
# ═══════════════════════════════════════════════════════════════════════════

class LotSizeManager:
    def __init__(self, client: BinanceClient):
        self.client = client
        self.symbol_info = {}
        self.last_update = 0
        self.account_group = CONFIG['ACCOUNT_GROUP']
    
    def update(self) -> bool:
        if time.time() - self.last_update < 300:
            return bool(self.symbol_info)
        try:
            info = self.client.exchange_info()
            symbols = info.get('symbols') if isinstance(info, dict) else None
            if not isinstance(symbols, list):
                raise ValueError("provider exchange-info symbols are unavailable")
            validated: Dict[str, Dict[str, Any]] = {}
            for s in symbols:
                if not isinstance(s, dict):
                    continue
                symbol = str(s.get('symbol') or '').upper()
                perms = s.get('permissionSets')
                if not symbol or not isinstance(perms, list):
                    continue
                can_trade = any(self.account_group in pset for pset in perms)
                filters = s.get('filters')
                if not isinstance(filters, list):
                    continue
                validated[symbol] = {
                    'status': s.get('status'),
                    'base': s.get('baseAsset'),
                    'quote': s.get('quoteAsset'),
                    'can_trade': can_trade,
                    'filters': {},
                }
                for f in filters:
                    if isinstance(f, dict) and f.get('filterType'):
                        validated[symbol]['filters'][f['filterType']] = f
            if not validated:
                raise ValueError("provider exchange-info contained no complete symbols")
            self.symbol_info = validated
            self.last_update = time.time()
            logger.info(f"📊 Loaded {len(self.symbol_info)} symbols")
            return True
        except Exception as e:
            self.symbol_info = {}
            self.last_update = 0
            logger.error(f"❌ Failed to load exchange info: {e}")
            return False
    
    def can_trade(self, symbol: str) -> bool:
        if not self.update():
            return False
        info = self.symbol_info.get(symbol, {})
        return info.get('can_trade') is True and info.get('status') == 'TRADING'
    
    def get_step_size(self, symbol: str) -> Optional[float]:
        if not self.update():
            return None
        lot = self.symbol_info.get(symbol, {}).get('filters', {}).get('LOT_SIZE', {})
        return _finite_number(lot.get('stepSize'), positive=True)
    
    def get_min_qty(self, symbol: str) -> Optional[float]:
        if not self.update():
            return None
        lot = self.symbol_info.get(symbol, {}).get('filters', {}).get('LOT_SIZE', {})
        return _finite_number(lot.get('minQty'), positive=True)
    
    def format_qty(self, symbol: str, qty: float) -> Optional[str]:
        step = self.get_step_size(symbol)
        min_qty = self.get_min_qty(symbol)
        parsed_qty = _finite_number(qty, positive=True)
        if step is None or min_qty is None or parsed_qty is None:
            return None
        try:
            qty_d = Decimal(str(parsed_qty))
            step_d = Decimal(str(step))
            formatted = (qty_d // step_d) * step_d
            if formatted < Decimal(str(min_qty)):
                return None
            precision = max(0, -step_d.normalize().as_tuple().exponent)
        except (InvalidOperation, ValueError):
            return None
        if precision == 0:
            return str(int(formatted))
        return f"{formatted:.{precision}f}"

# ═══════════════════════════════════════════════════════════════════════════
# MAIN TRADER
# ═══════════════════════════════════════════════════════════════════════════

class AureonBTCTrader:
    def __init__(self, dry_run: bool = False, client: Optional[BinanceClient] = None):
        self.dry_run = dry_run
        self.client = client if client is not None else get_binance_client()
        self.lot_mgr = LotSizeManager(self.client)
        self.positions = {}
        self.total_profit_btc = 0.0
        self.ticker_cache = {}
        self.last_ticker_update = 0
        self.data_status = "no_data"
        self.no_data_reason = "provider_receipt_not_requested"
        self.execution_receipts: List[Dict[str, Any]] = []
        self.reconciliation_required: List[Dict[str, Any]] = []
        self.last_realized_pnl: Dict[str, Any] = {
            "data_status": "no_data",
            "reason": "no_verified_closed_position",
            "generated_values": False,
        }
    
    def _validated_ticker(self, raw: Any) -> Optional[Dict[str, Any]]:
        if not isinstance(raw, dict):
            return None
        symbol = str(raw.get('symbol') or '').upper()
        source_timestamp = _fresh_provider_timestamp(
            raw.get('closeTime'),
            max_age_seconds=TICKER_MAX_AGE_SECONDS,
        )
        price = _finite_number(raw.get('lastPrice'), positive=True)
        change = _finite_number(raw.get('priceChangePercent'))
        volume = _finite_number(raw.get('quoteVolume'), nonnegative=True)
        if not symbol or source_timestamp is None or price is None or change is None or volume is None:
            return None
        return {
            "symbol": symbol,
            "price": price,
            "lastPrice": price,
            "priceChangePercent": change,
            "quoteVolume": volume,
            "source_id": f"binance:/api/v3/ticker/24hr:{symbol}",
            "source_timestamp": source_timestamp,
            "truth_status": "real_provider",
            "data_status": "live",
            "generated_values": False,
            "eligible_for_action": True,
        }

    def _ticker_receipt(self, symbol: str) -> Optional[Dict[str, Any]]:
        receipt = self.ticker_cache.get(symbol)
        if not isinstance(receipt, dict):
            return None
        if receipt.get("data_status") != "live" or receipt.get("generated_values") is not False:
            return None
        if _fresh_provider_timestamp(
            receipt.get("source_timestamp"),
            max_age_seconds=TICKER_MAX_AGE_SECONDS,
        ) is None:
            return None
        return receipt

    def update_tickers(self) -> bool:
        if time.time() - self.last_ticker_update < 2:
            return bool(self.ticker_cache)
        try:
            raw_tickers = self.client.get_24h_tickers()
            if not isinstance(raw_tickers, list):
                raise ValueError("provider ticker list is unavailable")
            tickers = {}
            for raw in raw_tickers:
                receipt = self._validated_ticker(raw)
                if receipt is not None:
                    tickers[receipt["symbol"]] = receipt
            if not tickers:
                raise ValueError("provider ticker list contained no complete fresh receipts")
            self.ticker_cache = tickers
            self.last_ticker_update = time.time()
            self.data_status = "live"
            self.no_data_reason = ""
            return True
        except Exception as e:
            self.ticker_cache = {}
            self.last_ticker_update = 0
            self.data_status = "no_data"
            self.no_data_reason = f"ticker_receipt_unavailable:{type(e).__name__}"
            logger.error(f"❌ Ticker update failed: {e}")
            return False
    
    def get_btc_price(self) -> Optional[float]:
        if 'BTCUSDT' not in self.ticker_cache:
            self.update_tickers()
        ticker = self._ticker_receipt('BTCUSDT')
        return ticker["price"] if ticker is not None else None
    
    def get_balances(self) -> Optional[Dict[str, float]]:
        try:
            account = self.client.account()
        except Exception as exc:
            self.data_status = "no_data"
            self.no_data_reason = f"account_receipt_unavailable:{type(exc).__name__}"
            return None
        if not isinstance(account, dict) or not isinstance(account.get('balances'), list):
            self.data_status = "no_data"
            self.no_data_reason = "account_receipt_malformed"
            return None
        source_timestamp = _fresh_provider_timestamp(
            account.get('updateTime'),
            max_age_seconds=ACCOUNT_MAX_AGE_SECONDS,
        )
        if source_timestamp is None:
            self.data_status = "no_data"
            self.no_data_reason = "account_provider_timestamp_missing_or_stale"
            return None
        balances: Dict[str, float] = {}
        for balance in account['balances']:
            if not isinstance(balance, dict):
                self.no_data_reason = "account_balance_row_malformed"
                return None
            asset = str(balance.get('asset') or '').upper()
            free = _finite_number(balance.get('free'), nonnegative=True)
            if not asset or free is None:
                self.no_data_reason = "account_balance_row_malformed"
                return None
            balances[asset] = free
        self.data_status = "live"
        self.no_data_reason = ""
        return balances

    def _validated_fill_receipt(
        self,
        raw: Any,
        *,
        expected_symbol: str,
        expected_side: str,
    ) -> Optional[Dict[str, Any]]:
        """Normalize only a fresh, complete Binance terminal fill receipt."""
        if not isinstance(raw, dict) or raw.get("dryRun") is True or raw.get("rejected") is True:
            return None
        symbol = str(raw.get("symbol") or "").upper()
        side = str(raw.get("side") or "").upper()
        status = str(raw.get("status") or "").upper()
        order_id = raw.get("orderId")
        source_timestamp = _fresh_provider_timestamp(
            raw.get("transactTime") or raw.get("updateTime"),
            max_age_seconds=ORDER_MAX_AGE_SECONDS,
        )
        executed_qty = _finite_number(raw.get("executedQty"), positive=True)
        quote_qty = _finite_number(raw.get("cummulativeQuoteQty"), positive=True)
        fills = raw.get("fills")
        if (
            symbol != expected_symbol.upper()
            or side != expected_side.upper()
            or status != "FILLED"
            or order_id in (None, "")
            or source_timestamp is None
            or executed_qty is None
            or quote_qty is None
            or not isinstance(fills, list)
            or not fills
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
            commission = _finite_number(fill.get("commission"), nonnegative=True)
            commission_asset = str(fill.get("commissionAsset") or "").upper()
            if qty is None or price is None or commission is None or not commission_asset:
                return None
            fill_qty += qty
            fill_quote += qty * price
            fees_by_asset[commission_asset] = fees_by_asset.get(commission_asset, 0.0) + commission

        if not _close_enough(fill_qty, executed_qty) or not _close_enough(fill_quote, quote_qty):
            return None
        receipt = {
            "symbol": symbol,
            "side": side,
            "status": status,
            "order_id": str(order_id),
            "source_id": f"binance:order:{order_id}",
            "source_timestamp": source_timestamp,
            "executed_qty": executed_qty,
            "quote_qty": quote_qty,
            "average_fill_price": quote_qty / executed_qty,
            "fees_by_asset": fees_by_asset,
            "fill_count": len(fills),
            "provider_acknowledged": True,
            "fill_receipt_complete": True,
            "truth_status": "real_provider",
            "data_status": "live",
            "generated_values": False,
            "eligible_for_accounting": True,
        }
        self.execution_receipts.append(receipt)
        return receipt

    def _not_submitted_receipt(
        self,
        symbol: str,
        side: str,
        reason: str,
    ) -> Dict[str, Any]:
        receipt = {
            "symbol": symbol.upper(),
            "side": side.upper(),
            "status": "NOT_SUBMITTED",
            "reason": reason,
            "source_id": "aureon:btc_trader:local_decision",
            "source_timestamp": None,
            "provider_acknowledged": False,
            "fill_receipt_complete": False,
            "truth_status": "not_submitted",
            "data_status": "no_data",
            "generated_values": False,
            "eligible_for_accounting": False,
        }
        self.execution_receipts.append(receipt)
        return receipt

    def _pending_reconciliation_receipt(
        self,
        symbol: str,
        side: str,
        reason: str,
        *,
        status: str = "PENDING_RECONCILIATION",
    ) -> Dict[str, Any]:
        receipt = {
            "symbol": symbol.upper(),
            "side": side.upper(),
            "status": status,
            "reason": reason,
            "source_id": None,
            "source_timestamp": None,
            "provider_acknowledged": False,
            "fill_receipt_complete": False,
            "truth_status": "pending_provider_reconciliation",
            "data_status": "no_data",
            "generated_values": False,
            "eligible_for_accounting": False,
        }
        self.execution_receipts.append(receipt)
        self.reconciliation_required.append(receipt)
        return receipt

    def _submit_market_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
    ) -> Optional[Dict[str, Any]]:
        if self.dry_run:
            self._not_submitted_receipt(symbol, side, "dry_run_no_provider_submission")
            return None
        try:
            raw = self.client.place_market_order(symbol, side, quantity=quantity)
        except Exception as exc:
            self._pending_reconciliation_receipt(
                symbol,
                side,
                f"provider_submission_failed:{type(exc).__name__}",
            )
            return None
        if isinstance(raw, dict) and raw.get("rejected") is True:
            self._pending_reconciliation_receipt(
                symbol,
                side,
                str(raw.get("reason") or "provider_or_preflight_rejected"),
                status="REJECTED",
            )
            return None
        receipt = self._validated_fill_receipt(
            raw,
            expected_symbol=symbol,
            expected_side=side,
        )
        if receipt is None:
            self._pending_reconciliation_receipt(
                symbol,
                side,
                "terminal_provider_fill_receipt_unavailable",
            )
        return receipt
    
    def liquidate_altcoins_to_btc(self) -> List[Dict[str, Any]]:
        """Sell all altcoins via BTC pairs to consolidate into BTC"""
        logger.info("\n🔄 LIQUIDATING ALTCOINS TO BTC...")
        
        balances = self.get_balances()
        if balances is None:
            logger.warning(f"NO_DATA: {self.no_data_reason}")
            return []
        btc_price = self.get_btc_price()
        outcomes: List[Dict[str, Any]] = []
        
        # Known alts from your portfolio
        alts_to_sell = ['LINK', 'ADA', 'DOT', 'AXS', 'SKL', 'PHA', 'ZKC']
        
        for asset in alts_to_sell:
            if asset not in balances or balances[asset] <= 0:
                continue
            
            symbol = f"{asset}BTC"
            
            if not self.lot_mgr.can_trade(symbol):
                logger.warning(f"⚠️ Cannot trade {symbol}")
                continue
            
            qty = balances[asset]
            ticker = self._ticker_receipt(symbol)
            if ticker is None:
                logger.warning(f"NO_DATA: fresh ticker receipt unavailable for {symbol}")
                continue
            price = ticker["price"]
            
            btc_value = qty * price
            usd_value = btc_value * btc_price if btc_price is not None else None
            usd_text = f"${usd_value:.2f}" if usd_value is not None else "USD NO_DATA"
            
            if btc_value < CONFIG['MIN_BTC_VALUE']:
                logger.info(f"⏭️ {asset}: {qty:.4f} (~{usd_text}) too small, skipping")
                continue
            
            qty_str = self.lot_mgr.format_qty(symbol, qty)
            if qty_str is None:
                logger.warning(f"NO_DATA: complete lot-size receipt unavailable for {symbol}")
                continue
            
            logger.info(f"💰 SELLING {symbol}: {qty_str} @ {price:.8f} BTC (~{usd_text})")
            receipt = self._submit_market_order(symbol, 'SELL', float(qty_str))
            if receipt is None:
                if self.dry_run:
                    logger.info(f"📝 DRY-RUN: Would sell {qty_str} {asset}")
                else:
                    logger.warning(f"PENDING_RECONCILIATION: {symbol} SELL")
            else:
                outcomes.append(receipt)
                logger.info(f"✅ Filled {symbol}: {receipt['order_id']}")
            if not self.dry_run:
                time.sleep(0.2)  # Rate limit
        return outcomes
    
    def scan_btc_pairs(self) -> List[Dict[str, Any]]:
        """Find BTC pairs we can trade and look for opportunities"""
        logger.info("\n🔍 SCANNING TRADEABLE BTC PAIRS...")
        
        if not self.lot_mgr.update():
            self.data_status = "no_data"
            self.no_data_reason = "exchange_info_receipt_unavailable"
            return []
        
        tradeable = []
        for symbol, info in self.lot_mgr.symbol_info.items():
            if info.get('can_trade') and info.get('quote') == 'BTC' and info.get('status') == 'TRADING':
                tradeable.append(symbol)
        
        logger.info(f"📊 Found {len(tradeable)} tradeable BTC pairs")
        
        # Get top movers
        btc_pairs: List[Dict[str, Any]] = []
        for symbol in tradeable:
            ticker = self._ticker_receipt(symbol)
            if ticker is None:
                continue
            change = ticker["priceChangePercent"]
            volume = ticker["quoteVolume"]
            if volume > 1.0:  # At least 1 BTC observed volume
                btc_pairs.append({
                    'symbol': symbol,
                    'change': change,
                    'volume': volume,
                    'price': ticker["price"],
                    'source_id': ticker["source_id"],
                    'source_timestamp': ticker["source_timestamp"],
                    'data_status': "live",
                    'generated_values': False,
                    'eligible_for_action': True,
                })
        
        # Sort by absolute change (volatility)
        btc_pairs.sort(key=lambda x: abs(x['change']), reverse=True)
        
        # Show top 10
        logger.info("\n📈 TOP MOVERS (BTC PAIRS):")
        for p in btc_pairs[:10]:
            emoji = "🟢" if p['change'] > 0 else "🔴"
            logger.info(f"  {emoji} {p['symbol']}: {p['change']:+.2f}% | Vol: {p['volume']:.2f} BTC")
        
        return btc_pairs
    
    def trade_btc_pairs(self, pairs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Enter positions on high-momentum BTC pairs"""
        balances = self.get_balances()
        if balances is None or 'BTC' not in balances:
            self.data_status = "no_data"
            self.no_data_reason = "fresh_btc_balance_receipt_unavailable"
            return []
        btc_balance = balances['BTC']
        btc_price = self.get_btc_price()
        usd_balance = btc_balance * btc_price if btc_price is not None else None
        usd_text = f"${usd_balance:.2f}" if usd_balance is not None else "USD NO_DATA"
        outcomes: List[Dict[str, Any]] = []
        
        logger.info(f"\n💎 BTC Balance: {btc_balance:.8f} (~{usd_text})")
        
        if btc_balance < CONFIG['MIN_BTC_VALUE']:
            logger.warning("⚠️ Not enough BTC to trade")
            return outcomes
        
        # Look for entry opportunities
        for p in pairs[:20]:
            if len(self.positions) >= CONFIG['MAX_POSITIONS']:
                break
            
            if not isinstance(p, dict):
                continue
            symbol = str(p.get('symbol') or '').upper()
            ticker = self._ticker_receipt(symbol)
            if ticker is None or p.get('eligible_for_action') is not True:
                continue
            if symbol in self.positions:
                continue

            # Skip if the exchange flags the symbol as untradeable for this account
            if not self.lot_mgr.can_trade(symbol):
                continue
            
            # Entry logic: Strong momentum (positive OR negative for scalping)
            change = ticker["priceChangePercent"]
            volume = ticker["quoteVolume"]
            price = ticker["price"]
            if abs(change) > 5.0 and volume > 2.0:  # >5% move, >2 BTC observed volume
                size_btc = btc_balance * 0.25  # 25% of BTC per trade
                if size_btc < CONFIG['MIN_BTC_VALUE']:
                    size_btc = min(btc_balance * 0.9, CONFIG['MIN_BTC_VALUE'] * 1.5)
                
                # Calculate quantity
                # MUST use endswith() — .replace() corrupts symbols like BTCB
                if not symbol.endswith('BTC') or len(symbol) <= 3:
                    continue
                base = symbol[:-3]
                qty = size_btc / price
                qty_str = self.lot_mgr.format_qty(symbol, qty)
                if qty_str is None:
                    logger.warning(f"NO_DATA: complete lot-size receipt unavailable for {symbol}")
                    continue
                
                logger.info(f"🎯 BUY {symbol}: {qty_str} @ {price:.8f} ({change:+.2f}%)")
                receipt = self._submit_market_order(symbol, 'BUY', float(qty_str))
                if receipt is None:
                    if self.dry_run:
                        logger.info(f"📝 DRY-RUN: Would buy {qty_str} {base}")
                    else:
                        logger.warning(f"PENDING_RECONCILIATION: {symbol} BUY")
                    continue

                base_fee = receipt["fees_by_asset"].get(base, 0.0)
                effective_qty = receipt["executed_qty"] - base_fee
                if effective_qty <= 0:
                    receipt["eligible_for_accounting"] = False
                    receipt["accounting_status"] = "no_data"
                    receipt["reason"] = "provider_base_fee_exceeds_executed_quantity"
                    self.reconciliation_required.append(receipt)
                    continue
                entry_value = receipt["quote_qty"] + receipt["fees_by_asset"].get("BTC", 0.0)
                unvalued_fee_assets = sorted(
                    asset
                    for asset, fee in receipt["fees_by_asset"].items()
                    if fee > 0 and asset not in {"BTC", base}
                )
                self.positions[symbol] = {
                    'entry': receipt["average_fill_price"],
                    'qty': effective_qty,
                    'entry_time': receipt["source_timestamp"],
                    'entry_value': entry_value,
                    'entry_fees_by_asset': dict(receipt["fees_by_asset"]),
                    'unvalued_fee_assets': unvalued_fee_assets,
                    'entry_receipt_id': receipt["source_id"],
                    'cycles': 0,
                    'reconciliation_required': False,
                }
                outcomes.append(receipt)
                logger.info(f"✅ Filled {symbol}: {receipt['order_id']}")
                refreshed = self.get_balances()
                if refreshed is None or 'BTC' not in refreshed:
                    break
                btc_balance = refreshed['BTC']
                time.sleep(0.2)
        return outcomes
    
    def check_exits(self) -> List[Dict[str, Any]]:
        """Check positions for TP/SL exits using penny profit"""
        outcomes: List[Dict[str, Any]] = []
        for symbol in list(self.positions.keys()):
            pos = self.positions[symbol]
            if pos.get('reconciliation_required') is True:
                continue
            ticker = self._ticker_receipt(symbol)
            if ticker is None:
                continue
            price = ticker["price"]
            
            # Track cycles for min hold time
            prior_cycles = pos.get('cycles')
            if not isinstance(prior_cycles, int) or isinstance(prior_cycles, bool) or prior_cycles < 0:
                continue
            pos['cycles'] = prior_cycles + 1
            
            entry = _finite_number(pos.get('entry'), positive=True)
            qty = _finite_number(pos.get('qty'), positive=True)
            entry_value = _finite_number(pos.get('entry_value'), positive=True)
            entry_time = _finite_number(pos.get('entry_time'), positive=True)
            if entry is None or qty is None or entry_value is None or entry_time is None:
                continue
            pnl_pct = (price - entry) / entry
            current_value = qty * price
            gross_pnl = current_value - entry_value
            
            should_exit = False
            reason = ""
            
            # 🪙 PENNY PROFIT EXIT LOGIC
            if PENNY_PROFIT_AVAILABLE and _penny_engine is not None:
                action, _ = check_penny_exit('binance', entry_value, current_value)
                threshold = _penny_engine.get_threshold('binance', entry_value)
                
                if action == 'TAKE_PROFIT':
                    should_exit = True
                    reason = f"🪙 PENNY TP ({gross_pnl:.8f} BTC)"
                elif action == 'STOP_LOSS' and pos['cycles'] >= 5:
                    should_exit = True
                    reason = f"🪙 PENNY SL ({gross_pnl:.8f} BTC)"
            else:
                # Fallback to percentage exits
                if pnl_pct >= CONFIG['TAKE_PROFIT_PCT']:
                    should_exit = True
                    reason = f"💰 TP (+{pnl_pct*100:.2f}%)"
                elif pnl_pct <= -CONFIG['STOP_LOSS_PCT'] and pos['cycles'] >= 5:
                    should_exit = True
                    reason = f"🛑 SL ({pnl_pct*100:.2f}%)"
            
            # Stagnation check (keep this)
            if not should_exit and time.time() - entry_time > 3600:
                should_exit = True
                reason = f"⏰ STAGNATION ({pnl_pct*100:.2f}%)"
            
            if should_exit:
                logger.info(f"⚡ EXIT {symbol}: {reason}")
                
                qty_str = self.lot_mgr.format_qty(symbol, qty)
                if qty_str is None:
                    logger.warning(f"NO_DATA: complete lot-size receipt unavailable for {symbol}")
                    continue
                receipt = self._submit_market_order(symbol, 'SELL', float(qty_str))
                if receipt is None:
                    if self.dry_run:
                        logger.info(f"📝 DRY-RUN: Would sell {qty_str}")
                    else:
                        logger.warning(f"PENDING_RECONCILIATION: {symbol} SELL")
                    continue
                if not _close_enough(receipt["executed_qty"], qty):
                    receipt["eligible_for_accounting"] = False
                    receipt["accounting_status"] = "no_data"
                    receipt["reason"] = "filled_quantity_requires_position_reconciliation"
                    pos["reconciliation_required"] = True
                    pos["exit_receipt_id"] = receipt["source_id"]
                    self.reconciliation_required.append(receipt)
                    continue

                unvalued = set(pos.get('unvalued_fee_assets') or [])
                unvalued.update(
                    asset
                    for asset, fee in receipt["fees_by_asset"].items()
                    if fee > 0 and asset != "BTC"
                )
                if unvalued:
                    self.last_realized_pnl = {
                        "symbol": symbol,
                        "data_status": "no_data",
                        "reason": "fee_conversion_receipt_unavailable",
                        "unvalued_fee_assets": sorted(unvalued),
                        "entry_receipt_id": pos.get("entry_receipt_id"),
                        "exit_receipt_id": receipt["source_id"],
                        "generated_values": False,
                    }
                else:
                    quote_fee = (
                        receipt["fees_by_asset"]["BTC"]
                        if "BTC" in receipt["fees_by_asset"]
                        else 0.0
                    )
                    net_quote = receipt["quote_qty"] - quote_fee
                    realized_pnl = net_quote - entry_value
                    self.total_profit_btc += realized_pnl
                    self.last_realized_pnl = {
                        "symbol": symbol,
                        "pnl_btc": realized_pnl,
                        "data_status": "live",
                        "truth_status": "real_provider_derived",
                        "entry_receipt_id": pos.get("entry_receipt_id"),
                        "exit_receipt_id": receipt["source_id"],
                        "generated_values": False,
                    }
                outcomes.append(receipt)
                logger.info(f"✅ Filled {symbol}: {receipt['order_id']}")
                del self.positions[symbol]
        return outcomes
    
    def run(self, duration_sec: int = 3600):
        logger.info("""
╔════════════════════════════════════════════════════════════╗
║           🌊 AUREON BTC PAIRS TRADER 🌊                    ║
║                                                            ║
║  Your account (TRD_GRP_039) trades BTC pairs only!         ║
║                                                            ║
║  Strategy:                                                 ║
║    1. Liquidate altcoins → BTC                             ║
║    2. Trade high-momentum BTC pairs                        ║
║    3. Compound gains in BTC                                ║
║                                                            ║
╚════════════════════════════════════════════════════════════╝
        """)
        
        # Initial liquidation
        self.update_tickers()
        self.liquidate_altcoins_to_btc()
        
        start = time.time()
        cycle = 0
        
        while time.time() - start < duration_sec:
            cycle += 1
            
            btc_price = self.get_btc_price()
            profit_usd = self.total_profit_btc * btc_price if btc_price is not None else None
            profit_usd_text = f"${profit_usd:.2f}" if profit_usd is not None else "USD NO_DATA"
            logger.info(f"\n🔄 Cycle {cycle} | Positions: {len(self.positions)} | Profit: {self.total_profit_btc:.8f} BTC (~{profit_usd_text})")
            
            self.update_tickers()
            
            # Check exits first
            self.check_exits()
            
            # Scan and trade
            pairs = self.scan_btc_pairs()
            self.trade_btc_pairs(pairs)
            
            time.sleep(5)  # 5 second cycles
        
        logger.info(f"\n🏁 Session complete. Total profit: {self.total_profit_btc:.8f} BTC")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--duration', type=int, default=3600)
    args = parser.parse_args()
    
    if not args.dry_run:
        if os.getenv('CONFIRM_LIVE', '').lower() != 'yes':
            logger.error("❌ Set CONFIRM_LIVE=yes for live trading")
            sys.exit(1)
        logger.warning("⚠️  LIVE TRADING - REAL MONEY")
    
    trader = AureonBTCTrader(dry_run=args.dry_run)
    trader.run(duration_sec=args.duration)

if __name__ == "__main__":
    main()

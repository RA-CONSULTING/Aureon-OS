#!/usr/bin/env python3
"""
AUREON LIVE TRADER - TSX Logic Implementation
==============================================

This connects the TypeScript decision logic to real Binance execution.
Uses your actual wallet balances to make trades.

Usage:
    python aureon_tsx_trader.py --mode paper    # Simulate trades
    python aureon_tsx_trader.py --mode live     # Real money
"""

from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import os
import sys
import time
import math
import json
import logging
import argparse
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from aureon.exchanges.binance_client import BinanceClient, get_binance_client

# ═══════════════════════════════════════════════════════════════════════════════
# LOGGING
# ═══════════════════════════════════════════════════════════════════════════════

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('tsx_trader.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION (from TSX DecisionFusionConfig)
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class TradingConfig:
    # Decision thresholds (from decisionFusion.ts)
    buy_threshold: float = 0.15
    sell_threshold: float = -0.15
    minimum_confidence: float = 0.35
    
    # Weights (from decisionFusion.ts)
    weight_ensemble: float = 0.6
    weight_sentiment: float = 0.2
    weight_qgita: float = 0.2
    
    # Execution (from executionEngine.ts)
    max_slippage_bps: float = 18
    
    # Risk management - AGGRESSIVE for small accounts
    risk_per_trade: float = 0.25  # 25% of USDT per trade (small account aggressive)
    max_position_pct: float = 0.40  # Max 40% in single asset
    min_trade_usdt: float = 10.0  # Binance minimum
    
    # Trading pairs to monitor
    pairs: List[str] = None
    
    def __post_init__(self):
        if self.pairs is None:
            # 🔶 COMPREHENSIVE BINANCE PAIRS (50+)
            self.pairs = [
                # === TOP TIER ===
                'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'XRPUSDT', 'ADAUSDT', 'AVAXUSDT',
                'DOTUSDT', 'ATOMUSDT', 'NEARUSDT', 'ICPUSDT', 'APTUSDT', 'SUIUSDT', 'SEIUSDT',
                # === LAYER 2s ===
                'ARBUSDT', 'OPUSDT', 'MATICUSDT', 'STXUSDT', 'IMXUSDT',
                # === DEFI ===
                'UNIUSDT', 'AAVEUSDT', 'LINKUSDT', 'CRVUSDT', 'SNXUSDT', 'LDOUSDT',
                # === AI & DATA ===
                'FETUSDT', 'RENDERUSDT', 'INJUSDT', 'WLDUSDT',
                # === MEMECOINS ===
                'DOGEUSDT', 'SHIBUSDT', 'PEPEUSDT', 'BONKUSDT', 'FLOKIUSDT', 'WIFUSDT',
                # === MID CAPS ===
                'LTCUSDT', 'FILUSDT', 'XLMUSDT', 'TRXUSDT', 'HBARUSDT', 'RUNEUSDT',
            ]


# ═══════════════════════════════════════════════════════════════════════════════
# MARKET DATA
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class OHLCV:
    open: float
    high: float
    low: float
    close: float
    volume: float

@dataclass 
class MarketSnapshot:
    symbol: str
    ohlcv: OHLCV
    bid: float
    ask: float
    spread: float
    timestamp: float

def get_market_snapshot(client: BinanceClient, symbol: str) -> Optional[MarketSnapshot]:
    """Fetch current market data for a symbol."""
    try:
        # Get 24hr ticker using session directly
        ticker_resp = client.session.get(f"{client.base}/api/v3/ticker/24hr", params={'symbol': symbol})
        ticker = ticker_resp.json()
        
        # Get order book for spread
        book_resp = client.session.get(f"{client.base}/api/v3/ticker/bookTicker", params={'symbol': symbol})
        book = book_resp.json()
        
        bid = float(book['bidPrice'])
        ask = float(book['askPrice'])
        spread = (ask - bid) / bid if bid > 0 else 0
        
        ohlcv = OHLCV(
            open=float(ticker['openPrice']),
            high=float(ticker['highPrice']),
            low=float(ticker['lowPrice']),
            close=float(ticker['lastPrice']),
            volume=float(ticker['volume'])
        )
        
        return MarketSnapshot(
            symbol=symbol,
            ohlcv=ohlcv,
            bid=bid,
            ask=ask,
            spread=spread,
            timestamp=time.time()
        )
    except Exception as e:
        logger.error(f"Failed to get snapshot for {symbol}: {e}")
        return None


# ═══════════════════════════════════════════════════════════════════════════════
# DECISION FUSION (ported from decisionFusion.ts)
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class ModelSignal:
    model: str
    score: float
    confidence: float

@dataclass
class DecisionSignal:
    action: str  # 'buy', 'sell', 'hold'
    position_size: float
    confidence: float
    model_signals: List[ModelSignal]
    sentiment_score: float

def generate_model_signal(model: str, snapshot: MarketSnapshot) -> ModelSignal:
    """Generate signal from a model (ported from TSX)."""
    import random
    
    trend = snapshot.ohlcv.close - snapshot.ohlcv.open
    volatility = snapshot.ohlcv.high - snapshot.ohlcv.low
    normalized_trend = math.tanh(trend / max(1, volatility))
    base_confidence = 0.4 + random.random() * 0.5
    
    # Model biases from TSX
    bias_map = {'lstm': 0.2, 'randomForest': -0.1, 'xgboost': 0.1, 'transformer': 0}
    bias = bias_map.get(model, 0)
    
    score = normalized_trend + bias + (random.random() - 0.5) * 0.1
    confidence = max(0.2, min(0.95, base_confidence - abs(score) * 0.1))
    
    return ModelSignal(model=model, score=score, confidence=confidence)

def decide(snapshot: MarketSnapshot, config: TradingConfig, qgita_event: Optional[dict] = None) -> DecisionSignal:
    """
    Decision fusion layer (ported from decisionFusion.ts).
    Combines ensemble models, sentiment, and QGITA lighthouse.
    """
    models = ['lstm', 'randomForest', 'xgboost', 'transformer']
    model_signals = [generate_model_signal(m, snapshot) for m in models]
    
    # Aggregate model scores
    aggregate_score = sum(s.score * s.confidence for s in model_signals)
    total_confidence = sum(s.confidence for s in model_signals)
    normalized_score = aggregate_score / total_confidence if total_confidence > 0 else 0
    
    # Sentiment (simplified - could connect to real sentiment API)
    sentiment_score = 0.0  # Neutral by default
    
    # QGITA boost
    qgita_boost = 0.0
    if qgita_event:
        direction = 1 if qgita_event.get('direction') == 'long' else -1
        qgita_boost = qgita_event.get('confidence', 0) * direction
    
    # Weighted combination
    weights = config.weight_ensemble + config.weight_sentiment + config.weight_qgita
    final_score = (
        normalized_score * (config.weight_ensemble / weights) +
        sentiment_score * (config.weight_sentiment / weights) +
        qgita_boost * (config.weight_qgita / weights)
    )
    
    # Decision
    if final_score > config.buy_threshold:
        action = 'buy'
    elif final_score < config.sell_threshold:
        action = 'sell'
    else:
        action = 'hold'
    
    # Position sizing - for small accounts, use FULL allocation when signal fires
    # If we're above threshold, commit to the trade!
    qgita_conf = qgita_event.get('confidence', 0.4) if qgita_event else 0.4
    combined_confidence = max(
        config.minimum_confidence,
        min(1, abs(final_score) + qgita_conf * (config.weight_qgita / weights))
    )
    
    # Position size = 1.0 means use full risk_per_trade allocation
    position_size = 1.0 if action != 'hold' else 0.0
    
    return DecisionSignal(
        action=action,
        position_size=position_size,
        confidence=combined_confidence,
        model_signals=model_signals,
        sentiment_score=sentiment_score
    )


# ═══════════════════════════════════════════════════════════════════════════════
# PORTFOLIO MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════════════

def get_portfolio_value(client: BinanceClient) -> Tuple[float, Dict[str, float]]:
    """Get total portfolio value in USDT and individual balances."""
    account = client.account()
    balances = {}
    total_usdt = 0.0
    
    for b in account['balances']:
        asset = b['asset']
        free = float(b['free'])
        if free > 0:
            balances[asset] = free
            
            # Convert to USDT
            if asset == 'USDT' or asset == 'USDC':
                total_usdt += free
            else:
                try:
                    ticker = client.best_price(f'{asset}USDT')
                    price = float(ticker['price'])
                    total_usdt += free * price
                except:
                    pass  # Skip assets without USDT pair
    
    return total_usdt, balances


# ═══════════════════════════════════════════════════════════════════════════════
# TRADE EXECUTION
# ═══════════════════════════════════════════════════════════════════════════════

def calculate_quantity(client: BinanceClient, symbol: str, usdt_amount: float) -> Optional[float]:
    """Calculate quantity to buy given USDT amount, respecting lot size."""
    try:
        # Get symbol info for lot size
        info = client.exchange_info(symbol)
        symbol_info = info['symbols'][0]
        
        # Find LOT_SIZE filter
        lot_size = None
        for f in symbol_info['filters']:
            if f['filterType'] == 'LOT_SIZE':
                lot_size = {
                    'min': float(f['minQty']),
                    'max': float(f['maxQty']),
                    'step': float(f['stepSize'])
                }
                break
        
        if not lot_size:
            return None
        
        # Get current price
        ticker = client.best_price(symbol)
        price = float(ticker['price'])
        
        # Calculate quantity
        raw_qty = usdt_amount / price
        
        # Round to step size
        step = lot_size['step']
        qty = math.floor(raw_qty / step) * step
        
        # Check bounds
        if qty < lot_size['min']:
            logger.warning(f"{symbol}: Quantity {qty} below minimum {lot_size['min']}")
            return None
        if qty > lot_size['max']:
            qty = lot_size['max']
        
        return qty
        
    except Exception as e:
        logger.error(f"Failed to calculate quantity for {symbol}: {e}")
        return None


def execute_trade(client: BinanceClient, symbol: str, side: str, quantity: float, paper_mode: bool = True) -> Optional[dict]:
    """Execute a trade on Binance."""
    if paper_mode:
        # Simulate trade using session directly
        ticker = client.best_price(symbol)
        price = float(ticker['price'])
        
        result = {
            'symbol': symbol,
            'side': side,
            'quantity': quantity,
            'price': price,
            'status': 'SIMULATED',
            'orderId': f'PAPER_{int(time.time() * 1000)}',
            'notional': quantity * price
        }
        logger.info(f"📝 PAPER TRADE: {side} {quantity:.6f} {symbol} @ ${price:.2f} = ${result['notional']:.2f}")
        return result
    
    else:
        # Real trade
        try:
            order = client.place_market_order(
                symbol=symbol,
                side=side,
                quantity=quantity
            )
            logger.info(f"✅ LIVE TRADE: {side} {quantity:.6f} {symbol} - Order ID: {order.get('orderId')}")
            return order
        except Exception as e:
            logger.error(f"❌ Trade failed: {e}")
            return None


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN TRADING LOOP
# ═══════════════════════════════════════════════════════════════════════════════

class TSXTrader:
    def __init__(self, config: TradingConfig, paper_mode: bool = False):
        self.config = config
        self.paper_mode = paper_mode
        self.client = get_binance_client()
        self.trades: List[dict] = []
        self.positions: Dict[str, float] = {}
    
    def scan_opportunities(self) -> List[Tuple[str, DecisionSignal, MarketSnapshot]]:
        """Scan all pairs for trading opportunities."""
        opportunities = []
        
        for symbol in self.config.pairs:
            snapshot = get_market_snapshot(self.client, symbol)
            if not snapshot:
                continue
            
            decision = decide(snapshot, self.config)
            
            if decision.action != 'hold' and decision.confidence >= self.config.minimum_confidence:
                opportunities.append((symbol, decision, snapshot))
                logger.info(f"📊 {symbol}: {decision.action.upper()} signal (conf: {decision.confidence:.2%})")
        
        return opportunities
    
    def execute_opportunities(self, opportunities: List[Tuple[str, DecisionSignal, MarketSnapshot]]):
        """Execute trades on detected opportunities."""
        portfolio_value, balances = get_portfolio_value(self.client)
        usdt_available = balances.get('USDT', 0) + balances.get('USDC', 0)
        
        logger.info(f"💰 Portfolio: ${portfolio_value:.2f} | USDT Available: ${usdt_available:.2f}")
        
        for symbol, decision, snapshot in opportunities:
            # Calculate trade size
            risk_amount = portfolio_value * self.config.risk_per_trade * decision.position_size
            trade_amount = min(risk_amount, usdt_available * 0.95)  # Keep 5% buffer
            
            if trade_amount < self.config.min_trade_usdt:
                logger.warning(f"⚠️ {symbol}: Trade size ${trade_amount:.2f} below minimum ${self.config.min_trade_usdt}")
                continue
            
            if decision.action == 'buy':
                # Check if we have USDT to buy
                if usdt_available < trade_amount:
                    logger.warning(f"⚠️ {symbol}: Insufficient USDT (have ${usdt_available:.2f}, need ${trade_amount:.2f})")
                    continue
                
                quantity = calculate_quantity(self.client, symbol, trade_amount)
                if quantity:
                    result = execute_trade(self.client, symbol, 'BUY', quantity, self.paper_mode)
                    if result:
                        self.trades.append(result)
                        usdt_available -= trade_amount
            
            elif decision.action == 'sell':
                # Check if we have the asset to sell
                base_asset = symbol.replace('USDT', '')
                if base_asset in balances and balances[base_asset] > 0:
                    # Sell portion based on position size
                    sell_qty = balances[base_asset] * decision.position_size
                    
                    # Get lot size to round properly
                    qty = calculate_quantity(self.client, symbol, sell_qty * snapshot.ohlcv.close)
                    if qty and qty <= balances[base_asset]:
                        result = execute_trade(self.client, symbol, 'SELL', qty, self.paper_mode)
                        if result:
                            self.trades.append(result)
    
    def run_cycle(self):
        """Run one trading cycle."""
        logger.info("=" * 60)
        logger.info(f"  TRADING CYCLE - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 60)
        
        # Scan for opportunities
        opportunities = self.scan_opportunities()
        
        if opportunities:
            logger.info(f"🎯 Found {len(opportunities)} opportunities")
            self.execute_opportunities(opportunities)
        else:
            logger.info("😴 No opportunities - market conditions unfavorable")
        
        return len(opportunities)
    
    def run(self, cycles: int = 10, interval: float = 30.0):
        """Run the trader for multiple cycles."""
        mode_str = "PAPER" if self.paper_mode else "🔴 LIVE"
        
        print(f"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                                                                               ║
║                    🚀 AUREON TSX TRADER - {mode_str} MODE                      ║
║                                                                               ║
║   Trading Pairs: {', '.join(self.config.pairs[:4])}...                        ║
║   Risk Per Trade: {self.config.risk_per_trade:.1%}                            ║
║   Buy Threshold: {self.config.buy_threshold}                                  ║
║   Sell Threshold: {self.config.sell_threshold}                                ║
║                                                                               ║
╚═══════════════════════════════════════════════════════════════════════════════╝
        """)
        
        portfolio_value, balances = get_portfolio_value(self.client)
        logger.info(f"💰 Starting Portfolio Value: ${portfolio_value:.2f}")
        
        try:
            for i in range(cycles):
                self.run_cycle()
                
                if i < cycles - 1:
                    logger.info(f"⏳ Next cycle in {interval}s...")
                    time.sleep(interval)
        
        except KeyboardInterrupt:
            logger.info("\n⚡ Stopping trader...")
        
        finally:
            # Summary
            print(f"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                         TRADING SESSION COMPLETE                              ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║   Cycles Run: {cycles}                                                        ║
║   Trades Executed: {len(self.trades)}                                         ║
║   Mode: {mode_str}                                                            ║
╚═══════════════════════════════════════════════════════════════════════════════╝
            """)
            
            if self.trades:
                print("\nTrade History:")
                for t in self.trades[-10:]:
                    print(f"  {t['side']} {t['quantity']:.6f} {t['symbol']} @ ${t['price']:.2f}")


# ═══════════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Aureon TSX Trader")
    parser.add_argument("--mode", choices=['paper', 'live'], default='paper', help="Trading mode")
    parser.add_argument("--cycles", type=int, default=10, help="Number of cycles")
    parser.add_argument("--interval", type=float, default=30.0, help="Seconds between cycles")
    
    args = parser.parse_args()
    
    config = TradingConfig()
    trader = TSXTrader(config, paper_mode=(args.mode == 'paper'))
    trader.run(cycles=args.cycles, interval=args.interval)

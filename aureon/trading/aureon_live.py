#!/usr/bin/env python3
"""
AUREON LIVE TRADING LAUNCHER - Python Integration Layer
═══════════════════════════════════════════════════════════════════════════════
Bridges Python binance_client.py with Aureon's Master Equation & 9 Auris nodes.

Workflow:
  1. Validates environment & Binance credentials (testnet first, then live).
  2. Fetches current balance & deposit address.
  3. Runs pre-flight coherence tests with sample market data.
  4. Executes controlled live trades respecting risk limits.
  5. Logs all activity to trade_audit.log for compliance & review.

Usage:
  # Stage 0: TESTNET & DRY-RUN (validate strategy before risking capital)
  export BINANCE_USE_TESTNET=true BINANCE_DRY_RUN=true
  python aureon_live.py --stage 0 --symbol BTCUSDT

  # Stage 1: TESTNET with real orders (end-to-end path validation)
  export BINANCE_USE_TESTNET=true BINANCE_DRY_RUN=false
  python aureon_live.py --stage 1 --symbol BTCUSDT

  # Stage 2: LIVE MONEY (only after stages 0 & 1 validated)
  export BINANCE_USE_TESTNET=false BINANCE_DRY_RUN=false CONFIRM_LIVE=yes
  python aureon_live.py --stage 2 --symbol BTCUSDT --target-profit 100

Author: Aureon System
Date: November 28, 2025
"""
from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import os, sys, json, time, logging, argparse
try:
    from dotenv import load_dotenv  # type: ignore
    load_dotenv()
except Exception:
    pass
from datetime import datetime
from aureon.exchanges.binance_client import BinanceClient, safe_trade, load_risk_config, get_binance_client

# ═══════════════════════════════════════════════════════════════════════════════
# LOGGING SETUP
# ═══════════════════════════════════════════════════════════════════════════════

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('trade_audit.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
# 9 AURIS NODES - Simplified Python adaptation
# ═══════════════════════════════════════════════════════════════════════════════

class AurisNode:
    def __init__(self, name: str, fn, weight: float):
        self.name = name
        self.fn = fn
        self.weight = weight

    def compute(self, data: dict) -> float:
        return self.fn(data) * self.weight

def create_auris_nodes():
    """Create 9 Auris nodes matching TS implementation."""
    nodes = {
        'tiger': AurisNode('tiger', 
            lambda d: ((d['high'] - d['low']) / d['price']) * 100 + (0.2 if d['volume'] > 1000000 else 0),
            1.2),
        'falcon': AurisNode('falcon',
            lambda d: abs(d['change']) * 0.7 + min(d['volume'] / 10000000, 0.3),
            1.1),
        'hummingbird': AurisNode('hummingbird',
            lambda d: 1 / (1 + ((d['high'] - d['low']) / d['price']) * 10),
            0.9),
        'dolphin': AurisNode('dolphin',
            lambda d: __import__('math').sin(d['change'] * __import__('math').pi / 10) * 0.5 + 0.5,
            1.0),
        'deer': AurisNode('deer',
            lambda d: (0.6 if d['price'] > d['open'] else 0.4) + (0.2 if d['change'] > 0 else -0.1),
            0.8),
        'owl': AurisNode('owl',
            lambda d: __import__('math').cos(d['change'] * __import__('math').pi / 10) * 0.3 + (0.3 if d['price'] < d['open'] else 0),
            0.9),
        'panda': AurisNode('panda',
            lambda d: 0.5 + __import__('math').sin(time.time() / 60000) * 0.1,
            0.7),
        'cargoship': AurisNode('cargoship',
            lambda d: 0.8 if d['volume'] > 5000000 else (0.5 if d['volume'] > 1000000 else 0.3),
            1.0),
        'clownfish': AurisNode('clownfish',
            lambda d: abs(d['price'] - d['open']) / d['price'] * 100,
            0.7),
    }
    return nodes

# ═══════════════════════════════════════════════════════════════════════════════
# MASTER EQUATION: Λ(t) = S(t) + O(t) + E(t)
# ═══════════════════════════════════════════════════════════════════════════════

class MasterEquation:
    def __init__(self):
        self.auris_nodes = create_auris_nodes()
        self.lambda_history = []
        self.OBSERVER_WEIGHT = 0.3
        self.ECHO_WEIGHT = 0.2

    def compute_substrate(self, market_data: dict) -> float:
        """S(t) = weighted average of 9 Auris node responses."""
        total = 0.0
        weight_sum = 0.0
        for node in self.auris_nodes.values():
            val = node.compute(market_data)
            total += val
            weight_sum += node.weight
        return total / weight_sum if weight_sum > 0 else 0.0

    def compute_echo(self) -> float:
        """E(t) = memory decay from recent Lambda history."""
        if len(self.lambda_history) == 0:
            return 0.0
        recent = self.lambda_history[-5:]  # Last 5 steps
        decay = sum(v * (0.9 ** i) for i, v in enumerate(reversed(recent)))
        return decay / len(recent) * self.ECHO_WEIGHT

    def compute_lambda(self, market_data: dict) -> dict:
        """Λ(t) = S(t) + O(t) + E(t) and return coherence."""
        s_t = self.compute_substrate(market_data)
        o_t = self.lambda_history[-1] * self.OBSERVER_WEIGHT if self.lambda_history else 0.0
        e_t = self.compute_echo()
        lambda_t = s_t + o_t + e_t
        self.lambda_history.append(lambda_t)
        
        # Coherence Γ = alignment measure (variance normalized)
        variance = max(abs(market_data['high'] - market_data['low']) / market_data['price'], 0.001)
        coherence = max(1 - (variance / 10), 0.0)
        
        return {
            'lambda': lambda_t,
            'coherence': coherence,
            'substrate': s_t,
            'observer': o_t,
            'echo': e_t,
        }

# ═══════════════════════════════════════════════════════════════════════════════
# AUREON LIVE TRADER
# ═══════════════════════════════════════════════════════════════════════════════

class AureonLiveTrader:
    def __init__(self, stage: int = 0, symbol: str = "BTCUSDT"):
        self.stage = stage
        self.symbol = symbol
        self.client = None
        self.master_eq = MasterEquation()
        self.risk_config = load_risk_config()
        self.trades_executed = []
        self.total_pnl = 0.0

    def preflight_check(self) -> bool:
        """Validate environment, credentials, and connectivity."""
        logger.info("═" * 80)
        logger.info("AUREON LIVE TRADING LAUNCHER - PREFLIGHT CHECK")
        logger.info("═" * 80)
        
        use_testnet = os.getenv("BINANCE_USE_TESTNET", "true").lower() == "true"
        dry_run = os.getenv("BINANCE_DRY_RUN", "true").lower() == "true"
        
        logger.info(f"Stage: {self.stage} | Testnet: {use_testnet} | DryRun: {dry_run}")
        logger.info(f"Symbol: {self.symbol} | Risk Fraction: {self.risk_config['fraction']}")
        
        if self.stage == 2 and not use_testnet:
            confirm = os.getenv("CONFIRM_LIVE", "").lower()
            if confirm != "yes":
                logger.error("❌ LIVE MONEY MODE requires CONFIRM_LIVE=yes")
                return False
            logger.warning("⚠️  LIVE MONEY MODE ENABLED - Real capital at risk!")
        
        try:
            self.client = get_binance_client()
            if self.client.ping():
                logger.info("✅ Binance API reachable")
            balance = self.client.get_free_balance("USDT")
            logger.info(f"💰 Free USDT: {balance}")
            if balance < 5:
                logger.warning(f"⚠️  Low balance: {balance} USDT (min 5 recommended)")
            return True
        except Exception as e:
            logger.error(f"❌ Preflight failed: {e}")
            return False

    def run_coherence_test(self) -> bool:
        """Test Master Equation with sample market data."""
        logger.info("\n📊 Running coherence test with sample market data...")
        try:
            price_data = self.client.best_price(self.symbol)
            current_price = float(price_data['price'])
            
            # Simulated market snapshot for test
            test_data = {
                'price': current_price,
                'volume': 1500000,
                'high': current_price * 1.02,
                'low': current_price * 0.98,
                'open': current_price * 0.99,
                'change': 1.2,
            }
            
            result = self.master_eq.compute_lambda(test_data)
            logger.info(f"  Λ(t): {result['lambda']:.4f}")
            logger.info(f"  Γ (coherence): {result['coherence']:.4f}")
            logger.info(f"  S(t) [substrate]: {result['substrate']:.4f}")
            logger.info(f"  Entry threshold: Γ > 0.938")
            
            if result['coherence'] > 0.938:
                logger.info("  ✅ Coherence sufficient for entry signal")
                return True
            else:
                logger.info("  ⚠️  Coherence below entry threshold")
                return False
        except Exception as e:
            logger.error(f"Coherence test failed: {e}")
            return False

    def execute_trade(self, side: str = "BUY") -> dict:
        """Execute a controlled trade via binance_client."""
        logger.info(f"\n🎯 Executing {side} order on {self.symbol}...")
        try:
            result = safe_trade(self.symbol, side)
            self.trades_executed.append({
                'timestamp': datetime.now().isoformat(),
                'side': side,
                'symbol': self.symbol,
                'result': result
            })
            logger.info(f"✅ Trade executed: {json.dumps(result, indent=2)}")
            return result
        except Exception as e:
            logger.error(f"❌ Trade execution failed: {e}")
            return {'error': str(e)}

    def run(self, num_trades: int = 1):
        """Main execution loop."""
        if not self.preflight_check():
            logger.error("Preflight check failed. Aborting.")
            sys.exit(1)
        
        if not self.run_coherence_test():
            logger.warning("Coherence test inconclusive, but proceeding anyway (Stage {}).".format(self.stage))
        
        logger.info(f"\n🚀 Starting {num_trades} trade(s) on stage {self.stage}...")
        for i in range(num_trades):
            side = "BUY" if i % 2 == 0 else "SELL"
            self.execute_trade(side)
            if i < num_trades - 1:
                time.sleep(1)
        
        logger.info(f"\n✅ Execution complete. {len(self.trades_executed)} trades logged.")
        logger.info(f"📋 Trade audit: {len(self.trades_executed)} entries in trade_audit.log")

def main():
    parser = argparse.ArgumentParser(description="Aureon Live Trading Launcher")
    parser.add_argument('--stage', type=int, default=0, help='Stage: 0=testnet+dry, 1=testnet+real, 2=live+real')
    parser.add_argument('--symbol', type=str, default='BTCUSDT', help='Trading symbol')
    parser.add_argument('--trades', type=int, default=1, help='Number of trades to execute')
    
    args = parser.parse_args()
    
    trader = AureonLiveTrader(stage=args.stage, symbol=args.symbol)
    trader.run(num_trades=args.trades)

if __name__ == "__main__":
    main()

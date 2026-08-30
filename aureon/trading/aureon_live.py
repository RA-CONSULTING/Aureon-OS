#!/usr/bin/env python3
"""
AUREON LIVE TRADING LAUNCHER - Python Integration Layer
═══════════════════════════════════════════════════════════════════════════════
Bridges Python binance_client.py with Aureon's Master Equation & 9 Auris nodes.

Workflow:
  1. Validates environment & Binance credentials (testnet first, then live).
  2. Fetches current balance & deposit address.
  3. Runs the pre-flight coherence gate with a fresh provider candle.
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
import os, sys, json, time, logging, argparse, math
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

COHERENCE_MARKET_TTL_SECONDS = 180

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
        
        # Coherence Γ = alignment measure (variance normalized), reconciled
        # conservatively with the organism's canonical field — the shared Γ can
        # only tighten this live gate, never loosen it (b46 order-path wiring).
        variance = max(abs(market_data['high'] - market_data['low']) / market_data['price'], 0.001)
        coherence = max(1 - (variance / 10), 0.0)
        try:
            from aureon.core.hnc_field import reconcile_gamma
            coherence = reconcile_gamma(coherence)
        except Exception:
            pass
        
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
        """Run the Master Equation only from a fresh, complete provider candle."""
        logger.info("\n📊 Running coherence gate with live Binance candle data...")
        try:
            candles = self.client.get_klines(self.symbol, interval="1m", limit=3)
            now = time.time()
            closed = [
                candle
                for candle in candles
                if isinstance(candle, dict)
                and float(candle['close_time']) / 1000.0 <= now
            ]
            if not closed:
                logger.error("NO_DATA: Binance returned no closed candle")
                return False

            candle = closed[-1]
            required_fields = {
                'open',
                'high',
                'low',
                'close',
                'quote_volume',
                'timestamp',
                'close_time',
            }
            missing = sorted(required_fields.difference(candle))
            if missing:
                logger.error(f"NO_DATA: Binance candle missing {missing}")
                return False

            observed = {
                key: float(candle[key])
                for key in ('open', 'high', 'low', 'close', 'quote_volume')
            }
            if (
                not all(math.isfinite(value) for value in observed.values())
                or observed['open'] <= 0
                or observed['close'] <= 0
                or observed['high'] < observed['low']
                or observed['quote_volume'] < 0
            ):
                logger.error("NO_DATA: Binance candle contains invalid observations")
                return False

            source_timestamp = float(candle['close_time']) / 1000.0
            age = now - source_timestamp
            if age < -5 or age > COHERENCE_MARKET_TTL_SECONDS:
                logger.error(
                    f"NO_DATA: Binance candle freshness invalid ({age:.1f}s)"
                )
                return False

            market_data = {
                'price': observed['close'],
                'volume': observed['quote_volume'],
                'high': observed['high'],
                'low': observed['low'],
                'open': observed['open'],
                'change': (
                    (observed['close'] - observed['open'])
                    / observed['open']
                    * 100.0
                ),
            }
            self.last_coherence_receipt = {
                'truth_status': 'live',
                'source_id': f'binance:klines:{self.symbol}:1m',
                'source_timestamp': source_timestamp,
                'received_at': now,
                'freshness_ttl_sec': COHERENCE_MARKET_TTL_SECONDS,
                'generated_values': False,
            }

            result = self.master_eq.compute_lambda(market_data)
            coherence = result.get('coherence')
            if not isinstance(coherence, (int, float)) or not math.isfinite(float(coherence)):
                logger.error("NO_DATA: Master Equation returned no finite coherence")
                return False
            logger.info(f"  Λ(t): {result['lambda']:.4f}")
            logger.info(f"  Γ (coherence): {result['coherence']:.4f}")
            logger.info(f"  S(t) [substrate]: {result['substrate']:.4f}")
            logger.info(f"  Entry threshold: Γ > 0.938")
            
            if coherence > 0.938:
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
            logger.error(
                "Coherence gate denied or has NO_DATA; no orders will be submitted."
            )
            return False
        
        logger.info(f"\n🚀 Starting {num_trades} trade(s) on stage {self.stage}...")
        for i in range(num_trades):
            side = "BUY" if i % 2 == 0 else "SELL"
            self.execute_trade(side)
            if i < num_trades - 1:
                time.sleep(1)
        
        logger.info(f"\n✅ Execution complete. {len(self.trades_executed)} trades logged.")
        logger.info(f"📋 Trade audit: {len(self.trades_executed)} entries in trade_audit.log")
        return True

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

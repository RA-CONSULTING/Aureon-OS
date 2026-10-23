#!/usr/bin/env python3
"""
🌉 AUREON UNIFIED DEMO - BRIDGE & PROFIT CYCLE TEST 🌉
======================================================

Tests the integration between Aureon Ultimate and Aureon Unified Ecosystem
using the new Aureon Bridge.

Features tested:
1. Bridge initialization and state sync
2. Cross-system opportunity sharing
3. Global profit gate enforcement (5 buys / 5 sells)
4. Shared capital tracking

Gary Leckey | November 2025
"""

from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import os
import sys
import time
import json
import logging
from threading import Thread
from aureon.bridges.aureon_bridge import AureonBridge, Opportunity, CapitalState, Position, ControlCommand

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

def run_bridge_monitor(bridge: AureonBridge):
    """Monitor bridge state in background"""
    logger.info("👀 Bridge Monitor started")
    while True:
        status = bridge.get_status()
        capital = status['capital']
        
        logger.info(f"\n🌉 BRIDGE STATUS:")
        logger.info(f"   💰 Equity: ${capital['total_equity']:.2f} | Net: ${capital['net_profit']:+.2f}")
        logger.info(f"   📊 Trades: {capital['trades']} | Win Rate: {capital['win_rate']*100:.1f}%")
        logger.info(f"   📍 Positions: {status['positions']['count']} | Opps: {status['opportunities']['count']}")
        
        # Check profit gate
        gate_ok = bridge.check_profit_gate(min_net_profit=0.0, min_trades=5)
        gate_icon = "✅" if gate_ok else "❌"
        logger.info(f"   🚪 Profit Gate (5 trades + net profit): {gate_icon}")
        
        time.sleep(5)

def simulate_unified_system(bridge: AureonBridge):
    """Simulate Unified Ecosystem activity"""
    logger.info("🐙 Unified System simulation started")
    
    # 1. Publish opportunities
    opps = [
        Opportunity(
            symbol='ETHUSD', exchange='kraken', side='BUY', score=85.0,
            coherence=0.8, momentum=2.5, volume=500000, price=2300.0,
            source_system='unified'
        ),
        Opportunity(
            symbol='SOLUSD', exchange='kraken', side='BUY', score=75.0,
            coherence=0.7, momentum=4.5, volume=800000, price=145.0,
            source_system='unified'
        )
    ]
    bridge.publish_opportunities(opps)
    logger.info("🐙 Unified published 2 opportunities")
    
    time.sleep(2)
    
    # 2. Open position
    pos = Position(
        symbol='ETHUSD', exchange='kraken', side='BUY', size=1.0,
        entry_price=2300.0, current_price=2300.0, unrealized_pnl=0.0,
        entry_time=time.time(), owner='unified'
    )
    bridge.register_position(pos)
    logger.info("🐙 Unified opened ETHUSD position")
    
    time.sleep(3)
    
    # 3. Close position with profit
    bridge.record_trade(profit=50.0, fee=5.0, success=True)
    bridge.unregister_position('kraken', 'ETHUSD')
    logger.info("🐙 Unified closed ETHUSD (+$45.00 net)")

def simulate_ultimate_system(bridge: AureonBridge):
    """Simulate Ultimate System activity"""
    logger.info("🌌 Ultimate System simulation started")
    
    time.sleep(1)
    
    # 1. Consume opportunities
    opps = bridge.get_opportunities(exchange='kraken')
    logger.info(f"🌌 Ultimate saw {len(opps)} opportunities from Unified")
    
    time.sleep(2)
    
    # 2. Open position (based on Unified opp)
    pos = Position(
        symbol='BNBUSDT', exchange='binance', side='BUY', size=10.0,
        entry_price=350.0, current_price=350.0, unrealized_pnl=0.0,
        entry_time=time.time(), owner='ultimate'
    )
    bridge.register_position(pos)
    logger.info("🌌 Ultimate opened BNBUSDT position")
    
    time.sleep(3)
    
    # 3. Close position with loss (to test net profit calc)
    bridge.record_trade(profit=-10.0, fee=2.0, success=False)
    bridge.unregister_position('binance', 'BNBUSDT')
    logger.info("🌌 Ultimate closed BNBUSDT (-$12.00 net)")

def main():
    logger.info("🚀 Starting Aureon Unified Demo")
    
    # Initialize bridge
    bridge = AureonBridge(data_dir='/tmp/aureon_bridge_demo')
    bridge.reset()
    
    # Start monitor
    monitor_thread = Thread(target=run_bridge_monitor, args=(bridge,), daemon=True)
    monitor_thread.start()
    
    # Run simulations
    t1 = Thread(target=simulate_unified_system, args=(bridge,))
    t2 = Thread(target=simulate_ultimate_system, args=(bridge,))
    
    t1.start()
    t2.start()
    
    t1.join()
    t2.join()
    
    # Final check
    logger.info("\n🏁 Simulation Complete")
    status = bridge.get_status()
    net_profit = status['capital']['net_profit']
    logger.info(f"💰 Final Net Profit: ${net_profit:+.2f}")
    
    if net_profit > 0:
        logger.info("✅ GLOBAL PROFIT TARGET ACHIEVED")
    else:
        logger.info("⚠️ GLOBAL PROFIT TARGET MISSED")

if __name__ == "__main__":
    main()

from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import time
import json
import random
import os
from aureon.trading.unified_exchange_client import MultiExchangeClient
from aureon.intelligence.aureon_market_pulse import MarketPulse

# Configuration
SCOUT_SIZE_USD = 12.0  # Size of each scout deployment
MIN_CASH_REQUIRED = 15.0  # Min cash to attempt a buy
SCAN_INTERVAL = 45  # Seconds between scans

# Fallback War List (if metrics fail)
FALLBACK_TARGETS = {
    'kraken': ['SOLUSD', 'ADAUSD', 'DOTUSD', 'LINKUSD', 'XRPUSD', 'XXBTZUSD', 'XETHZUSD', 'MATICUSD', 'DOGEUSD'],
    'binance': ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT', 'ADAUSDT', 'XRPUSDT'],
    'alpaca': ['BTC/USD', 'ETH/USD']
}

def get_state():
    try:
        if os.path.exists('aureon_kraken_state.json'):
            with open('aureon_kraken_state.json', 'r') as f:
                return json.load(f)
        return {'positions': {}, 'kills': []}
    except:
        return {'positions': {}, 'kills': []}

def save_state(state):
    with open('aureon_kraken_state.json', 'w') as f:
        json.dump(state, f, indent=2)

def run_scout_patrol():
    print("🏹 SCOUT PATROL STARTED - Searching for targets...")
    client = MultiExchangeClient()
    pulse = MarketPulse(client)
    
    while True:
        try:
            print(f"\n🔎 Scanning battlefield... ({time.strftime('%H:%M:%S')})")
            
            # 1. Load State
            state = get_state()
            current_positions = state.get('positions', {})
            held_symbols = [p.get('symbol') for p in current_positions.values()]
            
            # 2. Analyze Market Metrics
            print("   🧠 Analyzing market metrics...")
            market_data = pulse.analyze_market()
            top_gainers = market_data.get('top_gainers', [])
            arb_opps = market_data.get('arbitrage_opportunities', [])
            
            if top_gainers:
                print(f"   📈 Top Gainers identified: {', '.join([str(t.get('symbol')) for t in top_gainers[:3]])}")
            
            # 3. Check Cash & Deploy
            balances = client.get_all_balances()
            
            for exchange in ['kraken', 'binance', 'alpaca']:
                # Get available cash
                cash = 0.0
                if exchange == 'kraken':
                    cash = float(balances.get('kraken', {}).get('ZUSD', {}).get('free', 0) if isinstance(balances.get('kraken', {}).get('ZUSD'), dict) else balances.get('kraken', {}).get('ZUSD', 0))
                elif exchange == 'binance':
                    cash = float(balances.get('binance', {}).get('USDC', {}).get('free', 0) if isinstance(balances.get('binance', {}).get('USDC'), dict) else balances.get('binance', {}).get('USDC', 0))
                    if cash < SCOUT_SIZE_USD:
                        usdt = float(balances.get('binance', {}).get('USDT', {}).get('free', 0) if isinstance(balances.get('binance', {}).get('USDT'), dict) else balances.get('binance', {}).get('USDT', 0))
                        if usdt > cash: cash = usdt
                elif exchange == 'alpaca':
                    cash = float(balances.get('alpaca', {}).get('USD', {}).get('free', 0) if isinstance(balances.get('alpaca', {}).get('USD'), dict) else balances.get('alpaca', {}).get('USD', 0))
                
                print(f"   🏦 {exchange.upper()} Cash: ${cash:.2f}")
                
                if cash >= MIN_CASH_REQUIRED:
                    target = None
                    reason = "Random"
                    
                    # STRATEGY 1: Arbitrage (Best Metric)
                    # Check if any arb opportunity is buyable on this exchange
                    for arb in arb_opps:
                        buy_exch = arb['buy_at']['source']
                        symbol = arb['buy_at']['symbol']
                        if buy_exch == exchange and symbol not in held_symbols:
                            target = symbol
                            reason = f"Arbitrage Opportunity (+{arb['spread_pct']:.2f}%)"
                            break
                    
                    # STRATEGY 2: Momentum (Top Gainers)
                    if not target:
                        # Filter gainers for this exchange
                        exch_gainers = [t for t in top_gainers if t.get('source') == exchange and t.get('symbol') not in held_symbols]
                        if exch_gainers:
                            best_gainer = exch_gainers[0]
                            target = best_gainer.get('symbol')
                            change = best_gainer.get('priceChangePercent', 0)
                            reason = f"Top Gainer (+{change}%)"
                    
                    # STRATEGY 3: Fallback List
                    if not target:
                        available_targets = [t for t in FALLBACK_TARGETS.get(exchange, []) if t not in held_symbols]
                        if available_targets:
                            target = random.choice(available_targets)
                            reason = "Standard Patrol"
                    
                    if target:
                        print(f"   🎯 Target Acquired: {target} on {exchange}")
                        print(f"      Reason: {reason}")
                        
                        # Check price
                        ticker = client.get_ticker(exchange, target)
                        price = float(ticker.get('price', 0))
                        
                        if price > 0:
                            qty = SCOUT_SIZE_USD / price
                            print(f"   🚀 DEPLOYING SCOUT: Buying ${SCOUT_SIZE_USD} of {target}...")
                            
                            # Execute BUY
                            result = client.place_market_order(
                                exchange=exchange,
                                symbol=target,
                                side='BUY',
                                quote_qty=SCOUT_SIZE_USD
                            )
                            
                            if result and not result.get('error') and not result.get('rejected'):
                                order_id = result.get('txid') or result.get('orderId') or result.get('id')
                                print(f"   ✅ SCOUT DEPLOYED! Order: {order_id}")
                                
                                # Update State
                                state['positions'][target] = {
                                    'symbol': target,
                                    'exchange': exchange,
                                    'entry_price': price,
                                    'quantity': qty,
                                    'entry_value': SCOUT_SIZE_USD,
                                    'entry_time': time.time(),
                                    'is_scout': True,
                                    'strategy': reason
                                }
                                save_state(state)
                                time.sleep(2)
                            else:
                                print(f"   ❌ Deployment Failed: {result}")
                        else:
                            print(f"   ⚠️ Invalid price for {target}")
                    else:
                        print(f"   ✅ All targets covered on {exchange}.")
                else:
                    print(f"   ⚠️ Insufficient funds on {exchange}")
            
            print(f"   😴 Scouts resting for {SCAN_INTERVAL}s...")
            time.sleep(SCAN_INTERVAL)
            
        except Exception as e:
            print(f"   ❌ ERROR in Scout Patrol: {e}")
            time.sleep(SCAN_INTERVAL)

if __name__ == "__main__":
    run_scout_patrol()

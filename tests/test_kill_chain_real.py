#!/usr/bin/env python3
"""
Direct Kill Chain Test - Real Data Only
Tests Queen -> Dr. Auris -> Sniper workflow with actual exchange data

NOTE: this is a LIVE-VENUE CLI script (run `python tests/test_kill_chain_real.py` with real
credentials), not a pytest suite. Its per-exchange probes used to be named ``test_*``, so
pytest collected them and failed trying to inject the exchange clients as fixtures — 4
guaranteed errors on every offline run. They are ``probe_*`` now; pytest collects nothing
here and the CLI behaviour is unchanged.
"""
import os
os.environ['MINIMAL_MODE'] = '1'  # Skip heavy imports

import sys
import time
import asyncio
from datetime import datetime, timezone

# Direct imports - no baton link to avoid heavy startup
from capital_client import CapitalClient
from alpaca_client import AlpacaClient
from binance_client import BinanceClient
from kraken_client import KrakenClient, get_kraken_client
from aureon_sero_client import SeroClient

def log(emoji, role, msg):
    colors = {
        'SYSTEM': '\033[90m',
        'QUEEN': '\033[95m',
        'AURIS': '\033[94m',
        'SNIPER': '\033[92m',
        'WARN': '\033[93m'
    }
    print(f"{colors.get(role, '')}{emoji} [{role}] {msg}\033[0m")
    time.sleep(0.1)

def validate_with_dr_auris(dr_auris, exchange, symbol, pnl, entry_price, current_price, qty):
    """Validate trade with Dr. Auris Throne API."""
    timestamp = datetime.now(timezone.utc).isoformat()
    
    if not dr_auris.enabled:
        log('⚠️', 'WARN', 'Dr. Auris Throne API not configured - using basic validation')
        return {
            'approved': True,
            'reasoning': 'API not configured - basic profit check passed',
            'confidence': 0.5,
            'timestamp': timestamp,
            'method': 'fallback'
        }
    
    context = {
        'exchange': exchange,
        'symbol': symbol,
        'pnl': pnl,
        'entry_price': entry_price,
        'current_price': current_price,
        'qty': qty,
        'profit_percent': ((current_price - entry_price) / entry_price * 100) if entry_price > 0 else 0
    }
    
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        advice = loop.run_until_complete(
            dr_auris.ask_trading_decision(
                symbol=symbol,
                side="SELL",
                context=context,
                queen_confidence=0.85
            )
        )
        loop.close()
        
        if advice:
            return {
                'approved': advice.recommendation == "PROCEED",
                'reasoning': advice.reasoning,
                'confidence': advice.confidence,
                'timestamp': datetime.fromtimestamp(advice.timestamp, tz=timezone.utc).isoformat(),
                'risk_flags': advice.risk_flags,
                'method': 'dr_auris_throne_api'
            }
    except Exception as e:
        log('⚠️', 'WARN', f'Dr. Auris Throne API call failed: {e}')
    
    return {
        'approved': pnl > 0,
        'reasoning': f'API call failed - basic check: PnL ${pnl:.2f}',
        'confidence': 0.6,
        'timestamp': timestamp,
        'method': 'fallback_after_api_error'
    }

def probe_capital(capital, dr_auris):
    """Test Capital.com scanning and kill logic."""
    log('👑', 'QUEEN', 'Scanning Capital.com reality branches...')
    
    if not capital.enabled or not capital.cst:
        log('🖥️', 'SYSTEM', 'Capital.com: ❌ Not configured or not logged in')
        return False
    
    try:
        positions = capital.get_positions()
        if not positions:
            log('🖥️', 'SYSTEM', 'Capital.com: No active positions')
            return False
        
        for p in positions[:1]:  # Test first position only
            market = p.get('market', {})
            pos_data = p.get('position', {})
            epic = market.get('epic', 'UNKNOWN')
            upl = float(pos_data.get('upl', 0))
            deal_id = pos_data.get('dealId')
            size = float(pos_data.get('dealSize', 0))
            
            log('👑', 'QUEEN', f'Active Thread: {epic} | PnL: ${upl:.2f} | Size: {size}')
            
            if upl <= 0:
                log('👑', 'QUEEN', f'Assessment: NEGATIVE ({upl:.2f}). The hive advises patience.')
                return False
            
            log('👑', 'QUEEN', 'Assessment: PROFITABLE. The hive demands harvest.')
            log('⚕️', 'AURIS', f'Verifying {epic} harmonics via DigitalOcean LLM...')
            
            validation = validate_with_dr_auris(
                dr_auris, 'Capital', epic, upl, 0, 0, size
            )
            
            if not validation['approved']:
                log('⚕️', 'AURIS', f"❌ REJECTED: {validation['reason']}")
                return False
            
            log('⚕️', 'AURIS', f"✅ APPROVED at {validation['timestamp']}")
            log('⚕️', 'AURIS', f"Reasoning: {validation['reasoning']}")
            log('⚕️', 'AURIS', f"Confidence: {validation['confidence']:.2%}")
            log('⚕️', 'AURIS', f"Method: {validation['method']}")
            
            log('🎯', 'SNIPER', f'Target Acquired: {epic}. Safety DISENGAGED.')
            log('🎯', 'SNIPER', 'TAKING THE SHOT...')
            
            # REAL API CALL TO CLOSE POSITION
            res = capital._request('DELETE', f'/positions/{deal_id}')
            success = res.status_code == 200
            
            if success:
                log('🎯', 'SNIPER', f'💥 BOOM. {epic} Eliminated. Profit Realized.')
                log('👑', 'QUEEN', 'Harvest complete.')
                return True
            else:
                log('🎯', 'SNIPER', f'❌ MISSED SHOT on {epic}.')
                return False
                
    except Exception as e:
        log('⚠️', 'WARN', f'Capital scan failed: {e}')
        return False

def probe_binance(binance, dr_auris):
    """Test Binance scanning and kill logic."""
    log('👑', 'QUEEN', 'Scanning Binance chain...')
    
    if not binance.api_key:
        log('🖥️', 'SYSTEM', 'Binance: ❌ Not configured')
        return False
    
    try:
        acct = binance.account()
        if not acct or 'balances' not in acct:
            log('🖥️', 'SYSTEM', 'Binance: No account data')
            return False
        
        balances = {b['asset']: float(b['free']) + float(b['locked']) for b in acct['balances']}
        
        # Find first profitable position
        for asset, qty in balances.items():
            if qty <= 0: continue
            if asset in ['USDT', 'USDC', 'BUSD', 'USD', 'EUR']: continue
            
            # Try to get price
            try:
                ticker = binance.get_ticker(f"{asset}USDT")
                current_price = float(ticker.get('price', 0))
                if current_price == 0: continue
                
                # Try to get cost basis
                cost_data = binance.calculate_cost_basis(f"{asset}USDT")
                if not cost_data or cost_data.get('total_quantity', 0) == 0: continue
                
                avg_entry = float(cost_data['avg_entry_price'])
                pnl = (current_price - avg_entry) * qty
                
                if pnl <= 0: continue
                
                log('👑', 'QUEEN', f'Active Thread: {asset}USDT | PnL: ${pnl:.2f} | Qty: {qty:.6f}')
                log('👑', 'QUEEN', 'Assessment: PROFITABLE. The hive demands harvest.')
                log('⚕️', 'AURIS', f'Verifying {asset}USDT harmonics via DigitalOcean LLM...')
                
                validation = validate_with_dr_auris(
                    dr_auris, 'Binance', f'{asset}USDT', pnl, avg_entry, current_price, qty
                )
                
                if not validation['approved']:
                    log('⚕️', 'AURIS', f"❌ REJECTED: {validation['reasoning']}")
                    continue
                
                log('⚕️', 'AURIS', f"✅ APPROVED at {validation['timestamp']}")
                log('⚕️', 'AURIS', f"Reasoning: {validation['reasoning']}")
                log('⚕️', 'AURIS', f"Confidence: {validation['confidence']:.2%}")
                log('⚕️', 'AURIS', f"Method: {validation['method']}")
                
                log('🎯', 'SNIPER', f'Target Acquired: {asset}USDT. Safety DISENGAGED.')
                log('🎯', 'SNIPER', 'TAKING THE SHOT...')
                
                # REAL API CALL TO SELL
                res = binance.place_order(f"{asset}USDT", "SELL", qty, order_type="MARKET")
                success = bool(res.get('orderId'))
                
                if success:
                    log('🎯', 'SNIPER', f'💥 BOOM. {asset}USDT Eliminated. Profit Realized.')
                    log('👑', 'QUEEN', 'Harvest complete.')
                    return True
                else:
                    log('🎯', 'SNIPER', f'❌ MISSED SHOT on {asset}USDT.')
                    
            except Exception as e:
                continue
        
        log('🖥️', 'SYSTEM', 'Binance: No profitable positions found')
        return False
        
    except Exception as e:
        log('⚠️', 'WARN', f'Binance scan failed: {e}')
        return False

def probe_kraken(kraken, dr_auris):
    """Test Kraken scanning and kill logic."""
    log('👑', 'QUEEN', 'Scanning Kraken depths...')
    
    if not kraken.api_key:
        log('🖥️', 'SYSTEM', 'Kraken: ❌ Not configured')
        return False
    
    try:
        time.sleep(1.0)
        balances = kraken.get_account_balance()
        if not balances or isinstance(balances, list):
            log('🖥️', 'SYSTEM', 'Kraken: No balances')
            return False
        
        # Get ledgers for cost basis
        try:
            ledgers = kraken.get_ledgers(ofs=0)
        except:
            ledgers = {}
        
        # Find first profitable position
        for asset, qty in balances.items():
            try:
                qty = float(qty)
            except:
                continue
            
            if qty <= 0: continue
            if asset in ['ZUSD', 'USD', 'USDC', 'EUR']: continue
            
            # Try to get price
            try:
                ticker_data = kraken.get_ticker(f"{asset}USD")
                if not ticker_data: continue
                
                # Kraken returns dict of pairs
                current_price = 0
                for pair_key, pair_data in ticker_data.items():
                    current_price = float(pair_data.get('price', 0))
                    break
                
                if current_price == 0: continue
                
                # Try to calculate cost basis from ledgers (simplified)
                avg_entry = 0
                # For demo, use a simple estimate if we have any price
                # In real system, would use full ledger analysis
                
                # Skip if we can't determine entry
                if avg_entry == 0:
                    continue
                
                pnl = (current_price - avg_entry) * qty
                if pnl <= 0: continue
                
                log('👑', 'QUEEN', f'Active Thread: {asset} | PnL: ${pnl:.2f} | Qty: {qty:.6f}')
                log('👑', 'QUEEN', 'Assessment: PROFITABLE. The hive demands harvest.')
                log('⚕️', 'AURIS', f'Verifying {asset} harmonics via DigitalOcean LLM...')
                
                validation = validate_with_dr_auris(
                    dr_auris, 'Kraken', asset, pnl, avg_entry, current_price, qty
                )
                
                if not validation['approved']:
                    log('⚕️', 'AURIS', f"❌ REJECTED: {validation['reasoning']}")
                    continue
                
                log('⚕️', 'AURIS', f"✅ APPROVED at {validation['timestamp']}")
                log('⚕️', 'AURIS', f"Reasoning: {validation['reasoning']}")
                log('⚕️', 'AURIS', f"Confidence: {validation['confidence']:.2%}")
                log('⚕️', 'AURIS', f"Method: {validation['method']}")
                
                log('🎯', 'SNIPER', f'Target Acquired: {asset}. Safety DISENGAGED.')
                log('🎯', 'SNIPER', 'TAKING THE SHOT...')
                
                # REAL API CALL TO SELL
                res = kraken.place_market_order(f"{asset}USD", "sell", qty)
                success = bool(res.get('orderId') or res.get('txid'))
                
                if success:
                    log('🎯', 'SNIPER', f'💥 BOOM. {asset} Eliminated. Profit Realized.')
                    log('👑', 'QUEEN', 'Harvest complete.')
                    return True
                else:
                    log('🎯', 'SNIPER', f'❌ MISSED SHOT on {asset}.')
                    
            except Exception as e:
                continue
        
        log('🖥️', 'SYSTEM', 'Kraken: No profitable positions found')
        return False
        
    except Exception as e:
        log('⚠️', 'WARN', f'Kraken scan failed: {e}')
        return False

def probe_alpaca(alpaca, dr_auris):
    """Test Alpaca scanning and kill logic."""
    log('👑', 'QUEEN', 'Scanning Alpaca streams...')
    
    if not alpaca.api_key:
        log('🖥️', 'SYSTEM', 'Alpaca: ❌ Not configured')
        return False
    
    try:
        positions = alpaca.get_positions()
        if not positions:
            log('🖥️', 'SYSTEM', 'Alpaca: No active positions')
            return False
        
        for p in positions[:1]:  # Test first position only
            symbol = p.get('symbol')
            qty = float(p.get('qty', 0))
            upl = float(p.get('unrealized_pl', 0))
            avg_entry = float(p.get('avg_entry_price', 0))
            current_price = float(p.get('current_price', 0))
            
            if qty <= 0 or upl <= 0:
                continue
            
            log('👑', 'QUEEN', f'Active Thread: {symbol} | PnL: ${upl:.2f} | Qty: {qty}')
            log('👑', 'QUEEN', 'Assessment: PROFITABLE. The hive demands harvest.')
            log('⚕️', 'AURIS', f'Verifying {symbol} harmonics via DigitalOcean LLM...')
            
            validation = validate_with_dr_auris(
                dr_auris, 'Alpaca', symbol, upl, avg_entry, current_price, qty
            )
            
            if not validation['approved']:
                log('⚕️', 'AURIS', f"❌ REJECTED: {validation['reasoning']}")
                return False
            
            log('⚕️', 'AURIS', f"✅ APPROVED at {validation['timestamp']}")
            log('⚕️', 'AURIS', f"Reasoning: {validation['reasoning']}")
            log('⚕️', 'AURIS', f"Confidence: {validation['confidence']:.2%}")
            log('⚕️', 'AURIS', f"Method: {validation['method']}")
            
            log('🎯', 'SNIPER', f'Target Acquired: {symbol}. Safety DISENGAGED.')
            log('🎯', 'SNIPER', 'TAKING THE SHOT...')
            
            # REAL API CALL TO CLOSE POSITION
            res = alpaca._request('DELETE', f'/v2/positions/{symbol}')
            success = res is not None
            
            if success:
                log('🎯', 'SNIPER', f'💥 BOOM. {symbol} Eliminated. Profit Realized.')
                log('👑', 'QUEEN', 'Harvest complete.')
                return True
            else:
                log('🎯', 'SNIPER', f'❌ MISSED SHOT on {symbol}.')
                return False
                
    except Exception as e:
        log('⚠️', 'WARN', f'Alpaca scan failed: {e}')
        return False

def main():
    print("\n" + "="*80)
    log('🖥️', 'SYSTEM', 'UNIFIED KILL CHAIN - REAL DATA TEST')
    log('🖥️', 'SYSTEM', 'Testing Queen -> Dr. Auris -> Sniper workflow')
    print("="*80 + "\n")
    
    # Initialize clients
    log('🖥️', 'SYSTEM', 'Initializing Exchange Uplinks...')
    capital = CapitalClient()
    alpaca = AlpacaClient()
    binance = get_binance_client()
    kraken = get_kraken_client()
    dr_auris = SeroClient()
    
    # Report connectivity
    log('🖥️', 'SYSTEM', f"Capital.com:   {'✅' if capital.enabled and capital.cst else '❌'}")
    log('🖥️', 'SYSTEM', f"Alpaca:        {'✅' if alpaca.api_key else '❌'}")
    log('🖥️', 'SYSTEM', f"Binance:       {'✅' if binance.api_key else '❌'}")
    log('🖥️', 'SYSTEM', f"Kraken:        {'✅' if kraken.api_key else '❌'}")
    log('🖥️', 'SYSTEM', f"Dr. Auris API: {'✅' if dr_auris.enabled else '❌ (AI validation DISABLED)'}")
    
    print("\n" + "="*80)
    log('👑', 'QUEEN', 'System fully online. Initiating scan sequence.')
    print("="*80 + "\n")
    
    results = {
        'Capital.com': False,
        'Binance': False,
        'Kraken': False,
        'Alpaca': False
    }
    
    # Test each platform
    if capital.enabled and capital.cst:
        print("\n" + "-"*80)
        results['Capital.com'] = probe_capital(capital, dr_auris)
        print("-"*80)
    
    if binance.api_key:
        print("\n" + "-"*80)
        results['Binance'] = probe_binance(binance, dr_auris)
        print("-"*80)
    
    if kraken.api_key:
        print("\n" + "-"*80)
        results['Kraken'] = probe_kraken(kraken, dr_auris)
        print("-"*80)
    
    if alpaca.api_key:
        print("\n" + "-"*80)
        results['Alpaca'] = probe_alpaca(alpaca, dr_auris)
        print("-"*80)
    
    # Summary
    print("\n" + "="*80)
    log('🖥️', 'SYSTEM', 'TEST SUMMARY')
    print("="*80)
    for platform, success in results.items():
        status = '✅ KILL EXECUTED' if success else '❌ NO PROFITABLE TARGET'
        log('🖥️', 'SYSTEM', f"{platform:15} {status}")
    print("="*80 + "\n")

if __name__ == "__main__":
    main()

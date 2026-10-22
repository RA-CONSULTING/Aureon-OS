#!/usr/bin/env python3
"""
🦁 AUREON AUTOPILOT 🍯
Automated trading system - 50 trades per day on autopilot
"""

import os
import time
import hmac
import hashlib
import requests
from datetime import datetime
from typing import Dict, List, Optional
import json

class AureonAutopilot:
    def __init__(self, api_key: str, api_secret: str, testnet: bool = False):
        self.api_key = api_key
        self.api_secret = api_secret
        self.testnet = testnet
        
        if testnet:
            self.base_url = "https://testnet.binance.vision/api"
        else:
            self.base_url = "https://api.binance.com/api"
        
        self.start_capital = 0
        self.current_equity = 0
        self.trades_today = 0
        self.total_trades = 0
        self.wins = 0
        self.losses = 0
        self.total_pnl = 0
        
        # Trading parameters
        self.TRADES_PER_DAY = 50
        self.POSITION_SIZE_PCT = 0.30  # 30% per trade (you have small balance)
        self.MIN_ORDER_BNB = 0.01  # Minimum BNB order
        # Allow override of tradable universe via env (comma-separated)
        env_symbols = os.getenv('AUTOPILOT_SYMBOLS')
        if env_symbols:
            self.SYMBOLS = [s.strip().upper() for s in env_symbols.split(',') if s.strip()]
        else:
            self.SYMBOLS = ['BNBBTC']  # Just trade BNB for BTC (simplest)
        self.TRADE_COOLDOWN = 300  # 5 minutes between trades
        
        print("\n🦁 AUREON AUTOPILOT INITIALIZED 🍯")
        print(f"Mode: {'TESTNET' if testnet else 'LIVE'}")
        print(f"Target: {self.TRADES_PER_DAY} trades/day\n")

        # Reality framework thresholds (can be tuned via env)
        self.L_MIN = float(os.getenv('LIGHTHOUSE_L_MIN', '0.0'))       # trade if L >= L_MIN
        self.G_EFF_MAX = float(os.getenv('LIGHTHOUSE_G_MAX', '1.0'))   # brake if G_eff > G_EFF_MAX
        self.Q_MAX = float(os.getenv('LIGHTHOUSE_Q_MAX', '1.0'))       # suppress if Q > Q_MAX

        # Cache exchange rules per symbol
        self._exchange_rules: Dict[str, Dict] = {}
        # Lion scan wiring
        self.LION_SCAN_PATH = os.getenv('LION_SCAN_PATH', os.path.join('metrics', 'lion_scan.json'))
        self.LION_SCAN_STALENESS_SEC = int(os.getenv('LION_SCAN_STALENESS_SEC', '90'))
        self.AUTOPILOT_SYMBOL_OVERRIDE = os.getenv('AUTOPILOT_SYMBOL')
    
    def _sign_request(self, params: Dict) -> str:
        """Sign request with HMAC SHA256"""
        query_string = '&'.join([f"{k}={v}" for k, v in params.items()])
        signature = hmac.new(
            self.api_secret.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return signature
    
    def _request(self, method: str, endpoint: str, params: Dict = None, signed: bool = False) -> Dict:
        """Make API request"""
        url = f"{self.base_url}{endpoint}"
        headers = {'X-MBX-APIKEY': self.api_key}
        
        if params is None:
            params = {}
        
        if signed:
            params['timestamp'] = int(time.time() * 1000)
            params['signature'] = self._sign_request(params)
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, params=params)
            elif method == 'POST':
                response = requests.post(url, headers=headers, params=params)
            
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"❌ API Error: {e}")
            return None

    def _get_exchange_rules(self, symbol: str) -> Dict:
        """Fetch and cache exchange LOT_SIZE and NOTIONAL rules for a symbol"""
        if symbol in self._exchange_rules:
            return self._exchange_rules[symbol]
        info = self._request('GET', '/v3/exchangeInfo', {'symbol': symbol})
        rules = {'minQty': 0.0, 'stepSize': 0.0, 'minNotional': 0.0, 'status': 'UNKNOWN', 'baseAsset': None, 'quoteAsset': None}
        try:
            if info and 'symbols' in info:
                for s in info['symbols']:
                    if s.get('symbol') == symbol:
                        rules['status'] = s.get('status', 'UNKNOWN')
                        rules['baseAsset'] = s.get('baseAsset')
                        rules['quoteAsset'] = s.get('quoteAsset')
                        for f in s.get('filters', []):
                            if f.get('filterType') == 'LOT_SIZE':
                                rules['minQty'] = float(f.get('minQty', '0'))
                                rules['stepSize'] = float(f.get('stepSize', '0'))
                            if f.get('filterType') in ('MIN_NOTIONAL', 'NOTIONAL'):
                                rules['minNotional'] = float(f.get('minNotional', '0'))
                        break
        except Exception:
            pass
        self._exchange_rules[symbol] = rules
        return rules

    def _floor_to_step(self, qty: float, step: float) -> float:
        if step <= 0:
            return qty
        # Avoid float error by working in integers
        return (int(qty / step)) * step

    def _enforce_reality(self, symbol: str, side: str, quantity: float, price: float) -> Optional[float]:
        """Adjust quantity to LOT_SIZE and NOTIONAL. Return None if cannot meet min."""
        rules = self._get_exchange_rules(symbol)
        min_qty = rules.get('minQty', 0.0)
        step = rules.get('stepSize', 0.0)
        min_notional = rules.get('minNotional', 0.0)

        # Step and min qty
        q = max(quantity, min_qty)
        q = self._floor_to_step(q, step) if step else q
        if q <= 0:
            print(f"⏭️  Reality: quantity zero after step-size adjustment")
            return None

        # Notional in quote (for BNBBTC/ETHBTC quote is BTC)
        notional = q * price
        if min_notional and notional < min_notional:
            # try to raise to min notional
            need_q = min_notional / max(price, 1e-12)
            q2 = self._floor_to_step(max(need_q, min_qty), step) if step else max(need_q, min_qty)
            if q2 * price < min_notional:
                print(f"⏭️  Reality: notional {notional:.8f} below min {min_notional:.8f}")
                return None
            q = q2
        return q

    def _should_trade_by_lighthouse(self) -> bool:
        """Check Lighthouse metrics written by metrics_watcher and gate trading."""
        try:
            with open(os.path.join('metrics', 'lighthouse_autopilot.json'), 'r') as f:
                data = json.load(f)
            m = data.get('metrics', {})
            L = float(m.get('L', 0))
            Q = float(m.get('Q', 0))
            G = float(m.get('G_eff', 0))
            if L < self.L_MIN:
                print(f"⏸️  Lighthouse: L={L:.3f} < L_MIN={self.L_MIN:.3f}")
                return False
            if G > self.G_EFF_MAX:
                print(f"⏸️  Lighthouse: G_eff={G:.3f} > G_MAX={self.G_EFF_MAX:.3f}")
                return False
            if Q > self.Q_MAX:
                print(f"⏸️  Lighthouse: Q={Q:.3f} > Q_MAX={self.Q_MAX:.3f}")
                return False
            return True
        except Exception:
            # If no metrics, allow trading (fail-open) unless user sets L_MIN>0
            return self.L_MIN == 0.0

    def _select_symbol(self) -> str:
        """Select symbol using env override, Lion scan suggestions, then fallback."""
        # 1) Hard override via env
        if self.AUTOPILOT_SYMBOL_OVERRIDE:
            return self.AUTOPILOT_SYMBOL_OVERRIDE.strip().upper()

        # 2) Try Lion scan suggestions
        try:
            with open(self.LION_SCAN_PATH, 'r') as f:
                data = json.load(f)
            ts = data.get('updatedAt')
            # Check staleness if timestamp provided
            fresh = True
            if ts:
                try:
                    # parse ISO8601 Z
                    dt = datetime.fromisoformat(ts.replace('Z','+00:00'))
                    fresh = (datetime.utcnow() - dt.replace(tzinfo=None)).total_seconds() <= self.LION_SCAN_STALENESS_SEC
                except Exception:
                    fresh = True
            if fresh:
                suggestions = data.get('suggestions', [])
                # Prefer permitted, TRADING, and in our universe
                for s in suggestions:
                    sym = str(s.get('symbol', '')).upper()
                    permitted = bool(s.get('permitted', False))
                    status = str(s.get('status', ''))
                    if permitted and status == 'TRADING' and sym in self.SYMBOLS:
                        return sym
        except Exception:
            pass

        # 3) Fallback to first symbol in our universe
        return self.SYMBOLS[0]

    def _elephant_log(self, record: Dict):
        try:
            os.makedirs('metrics', exist_ok=True)
            with open(os.path.join('metrics', 'elephant_memory.jsonl'), 'a') as f:
                f.write(json.dumps(record) + "\n")
        except Exception:
            pass
    
    def get_account_balance(self) -> Dict[str, float]:
        """Get all asset balances"""
        balances = {}
        account = self._request('GET', '/v3/account', signed=True)
        if account:
            for balance in account['balances']:
                free = float(balance['free'])
                if free > 0:
                    balances[balance['asset']] = free
        return balances
    
    def get_total_value_btc(self) -> float:
        """Get total account value in BTC"""
        balances = self.get_account_balance()
        total_btc = balances.get('BTC', 0)
        
        # Add BNB value
        if 'BNB' in balances:
            bnb_btc_price = self.get_price('BNBBTC')
            if bnb_btc_price > 0:
                total_btc += balances['BNB'] * bnb_btc_price
        
        # Add ETH value
        if 'ETH' in balances:
            eth_btc_price = self.get_price('ETHBTC')
            if eth_btc_price > 0:
                total_btc += balances['ETH'] * eth_btc_price

        # Add USDT value (convert USDT -> BTC)
        if 'USDT' in balances:
            btc_usdt = self.get_price('BTCUSDT')
            if btc_usdt > 0:
                total_btc += balances['USDT'] / btc_usdt
        
        return total_btc
    
    def get_price(self, symbol: str) -> float:
        """Get current price"""
        ticker = self._request('GET', '/v3/ticker/price', {'symbol': symbol})
        if ticker:
            return float(ticker['price'])
        return 0.0
    
    def place_order(self, symbol: str, side: str, quantity: float) -> Optional[Dict]:
        """Place market order"""
        params = {
            'symbol': symbol,
            'side': side,
            'type': 'MARKET',
            'quantity': quantity
        }
        
        print(f"🔥 Placing {side} order: {quantity:.8f} {symbol}")
        order = self._request('POST', '/v3/order', params, signed=True)
        
        if order:
            print(f"✅ Order filled: {order['orderId']}")
            return order
        else:
            print(f"❌ Order failed")
            return None
    
    def generate_signal(self, symbol: str) -> str:
        """Generate trading signal (simple random for now)"""
        import random
        
        # Check balances to determine if we can buy or sell
        balances = self.get_account_balance()
        btc_balance = balances.get('BTC', 0)
        
        # If no BTC, prefer SELL to accumulate BTC first
        if btc_balance < 0.0001:
            signals = ['SELL', 'HOLD']
            weights = [0.8, 0.2]  # 80% sell, 20% hold
        else:
            # Have BTC, can do both
            signals = ['BUY', 'SELL', 'HOLD']
            weights = [0.35, 0.35, 0.30]  # 70% trade, 30% hold
        
        return random.choices(signals, weights=weights)[0]
    
    def execute_trade(self, symbol: str, signal: str) -> bool:
        """Execute a single trade"""
        try:
            # Lighthouse gating — reality + coherence
            if not self._should_trade_by_lighthouse():
                return False

            # Get current balances
            balances = self.get_account_balance()
            
            # Determine base/quote generically from exchange info
            rules = self._get_exchange_rules(symbol)
            base_asset = rules.get('baseAsset')
            quote_asset = rules.get('quoteAsset')
            if not base_asset or not quote_asset:
                return False
            
            # For BUY: we spend quote asset; for SELL: we spend base asset
            if signal == 'BUY':
                spend_asset = quote_asset
            else:
                spend_asset = base_asset
            available = balances.get(spend_asset, 0)
            
            if available == 0:
                print(f"⏭️  No {spend_asset} balance to trade")
                return False
            
            # Get current price
            price = self.get_price(symbol)
            if price == 0:
                return False
            
            # Calculate position size (use % of available balance)
            position_size = available * self.POSITION_SIZE_PCT
            
            # Calculate pre-adjustment quantity
            if signal == 'BUY':
                # quote / price = base quantity
                quantity = position_size / price
            else:
                # sell base directly
                quantity = position_size

            # Enforce exchange LOT_SIZE/NOTIONAL
            quantity_adj = self._enforce_reality(symbol, signal, quantity, price)
            if quantity_adj is None:
                return False
            
            # Round quantity to step precision to avoid float artifacts
            step = rules.get('stepSize', 0.001)
            if step >= 1:
                precision = 0
            elif step >= 0.1:
                precision = 1
            elif step >= 0.01:
                precision = 2
            elif step >= 0.001:
                precision = 3
            else:
                precision = 8
            quantity = round(float(quantity_adj), precision)
            
            # Place order
            print(f"💼 {spend_asset} balance: {available:.6f}, Using: {position_size:.6f} ({self.POSITION_SIZE_PCT*100}%)")
            order = self.place_order(symbol, signal, quantity)
            
            if order:
                # Get new balance and calculate actual P&L
                import random
                time.sleep(1)  # Wait for order to settle
                
                new_balance_btc = self.get_total_value_btc()
                btc_price_usdt = self.get_price('BTCUSDT')
                new_equity = new_balance_btc * btc_price_usdt
                
                pnl = new_equity - self.current_equity
                
                if pnl > 0:
                    self.wins += 1
                    print(f"✅ Winner: +${pnl:.2f}")
                else:
                    self.losses += 1
                    print(f"❌ Loser: ${pnl:.2f}")
                
                self.current_equity = new_equity
                self.total_pnl += pnl
                self.trades_today += 1
                self.total_trades += 1
                
                # Elephant memory log
                self._elephant_log({
                    'ts': datetime.utcnow().isoformat() + 'Z',
                    'symbol': symbol,
                    'side': signal,
                    'qty': quantity,
                    'price': price,
                    'equity_usdt': self.current_equity,
                    'pnl_delta': pnl,
                    'wins': self.wins,
                    'losses': self.losses
                })
                
                return True
        
        except Exception as e:
            print(f"❌ Trade execution error: {e}")
            return False
        
        return False
    
    def print_status(self):
        """Print current status"""
        win_rate = (self.wins / max(1, self.total_trades)) * 100
        return_pct = ((self.current_equity - self.start_capital) / max(1, self.start_capital)) * 100
        
        print("\n" + "="*70)
        print("📊 AUTOPILOT STATUS")
        print("="*70)
        print(f"Trades Today:    {self.trades_today}/{self.TRADES_PER_DAY}")
        print(f"Total Trades:    {self.total_trades}")
        print(f"Win Rate:        {win_rate:.1f}% ({self.wins}W/{self.losses}L)")
        print(f"Starting:        ${self.start_capital:.2f}")
        print(f"Current:         ${self.current_equity:.2f}")
        print(f"P&L:             {'+'if self.total_pnl >= 0 else ''}${self.total_pnl:.2f} ({return_pct:+.2f}%)")
        print(f"🍯 Honey:         ${max(0, self.total_pnl):.2f}")
        print("="*70 + "\n")
    
    def run_daily_session(self):
        """Run one day of trading (50 trades)"""
        print(f"\n🦁 Starting daily trading session: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        # Get starting balance in BTC
        balance_btc = self.get_total_value_btc()
        if balance_btc == 0:
            print("❌ No tradeable balance found!")
            return
        
        # Convert to USDT for display
        btc_price_usdt = self.get_price('BTCUSDT')
        balance_usdt = balance_btc * btc_price_usdt
        
        if self.start_capital == 0:
            self.start_capital = balance_usdt
        
        self.current_equity = balance_usdt
        self.trades_today = 0
        
        balances = self.get_account_balance()
        print(f"💰 Starting balances:")
        for asset, amount in balances.items():
            print(f"  {asset}: {amount:.8f}")
        print(f"💰 Total value: ${self.current_equity:.2f} USDT\n")
        
        # Execute trades
        while self.trades_today < self.TRADES_PER_DAY:
            # Select symbol via Lion scan/env override or fallback
            symbol = self._select_symbol()
            
            # Get signal
            signal = self.generate_signal(symbol)
            
            if signal == 'HOLD':
                print(f"⏸️  {symbol}: HOLD signal, waiting...")
                time.sleep(10)
                continue
            
            # Execute trade
            print(f"\n🎯 Trade {self.trades_today + 1}/{self.TRADES_PER_DAY}")
            success = self.execute_trade(symbol, signal)
            
            if success:
                # Show progress every 10 trades
                if self.trades_today % 10 == 0:
                    self.print_status()
                
                # Cooldown between trades
                if self.trades_today < self.TRADES_PER_DAY:
                    print(f"⏳ Cooldown: {self.TRADE_COOLDOWN}s...")
                    time.sleep(self.TRADE_COOLDOWN)
            else:
                time.sleep(30)  # Wait 30s on failure
        
        # Final status
        print("\n🎯 Daily session complete!")
        self.print_status()
        
        # Log results
        self.log_daily_results()
    
    def log_daily_results(self):
        """Log daily trading results"""
        result = {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'trades': self.trades_today,
            'wins': self.wins,
            'losses': self.losses,
            'start_equity': self.start_capital,
            'end_equity': self.current_equity,
            'pnl': self.total_pnl,
            'return_pct': ((self.current_equity - self.start_capital) / self.start_capital) * 100
        }
        
        # Save to log file
        log_file = 'autopilot_log.json'
        logs = []
        
        if os.path.exists(log_file):
            with open(log_file, 'r') as f:
                logs = json.load(f)
        
        logs.append(result)
        
        with open(log_file, 'w') as f:
            json.dump(logs, f, indent=2)
        
        print(f"📝 Results logged to {log_file}")
    
    def run_autopilot(self, days: int = 30):
        """Run autopilot for multiple days"""
        print("\n" + "="*70)
        print("🚀 AUREON AUTOPILOT STARTING")
        print("="*70)
        print(f"Duration: {days} days")
        print(f"Trades per day: {self.TRADES_PER_DAY}")
        print(f"Total trades planned: {days * self.TRADES_PER_DAY}")
        print("="*70 + "\n")
        
        for day in range(1, days + 1):
            print(f"\n{'='*70}")
            print(f"📅 DAY {day}/{days}")
            print(f"{'='*70}")
            
            self.run_daily_session()
            
            if day < days:
                print(f"\n⏸️  Day {day} complete. Next session in 24 hours...")
                # In real autopilot, would wait until next day
                # For testing, just continue
                time.sleep(5)
        
        print("\n" + "="*70)
        print("🏁 AUTOPILOT MISSION COMPLETE")
        print("="*70)
        self.print_status()
        print("\n🍯 THE HONEY HAS BEEN COLLECTED! 🍯\n")


def main():
    """Main entry point"""
    # Load credentials from environment
    api_key = os.getenv('BINANCE_API_KEY')
    api_secret = os.getenv('BINANCE_API_SECRET')
    testnet = os.getenv('BINANCE_TESTNET', 'false').lower() == 'true'
    
    if not api_key or not api_secret:
        print("❌ Missing API credentials!")
        print("Set BINANCE_API_KEY and BINANCE_API_SECRET environment variables")
        return
    
    # Confirmation check
    confirm = os.getenv('CONFIRM_AUTOPILOT')
    if confirm != 'YES':
        print("\n⚠️  AUTOPILOT requires confirmation!")
        print("\nTo start autopilot:")
        print("  export CONFIRM_AUTOPILOT=YES")
        print("  python scripts/autopilot.py")
        print("\n⚠️  WARNING: This will trade automatically!")
        return
    
    # Create and run autopilot
    autopilot = AureonAutopilot(api_key, api_secret, testnet)
    
    # Run for 1 day by default (can be changed)
    days = int(os.getenv('AUTOPILOT_DAYS', '1'))
    autopilot.run_autopilot(days)


if __name__ == '__main__':
    main()

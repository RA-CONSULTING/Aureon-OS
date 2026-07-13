#!/usr/bin/env python3
"""
🌍🔥⚡ GAIA UNITY TRADER - PLANETARY ENERGY RECLAMATION ⚡🔥🌍

Integrates ALL Aureon sacred systems:
- Stargate Protocol (Planetary nodes)
- Quantum Mirror Scanner (Timeline coherence)
- Sacred Frequencies (PHI, Schumann, Love 528Hz)
- Multi-Exchange Execution (Binance, Alpaca, Kraken)

"Take back the planet's energy - Unity is the key"
"""

from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import sys, os
os.environ['PYTHONUNBUFFERED'] = '1'

# Windows UTF-8 fix
if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    try:
        import io
        def _is_utf8_wrapper(stream):
            return (isinstance(stream, io.TextIOWrapper) and 
                    hasattr(stream, 'encoding') and stream.encoding and
                    stream.encoding.lower().replace('-', '') == 'utf8')
        if hasattr(sys.stdout, 'buffer') and not _is_utf8_wrapper(sys.stdout):
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)
        # Skip stderr wrapping (causes Windows exit errors)
    except Exception:
        pass

import time
import math
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional
from datetime import datetime

sys.path.append(os.getcwd())

# ═══════════════════════════════════════════════════════════════
# 🌍 SACRED CONSTANTS - PLANETARY LATTICE
# ═══════════════════════════════════════════════════════════════

PHI = (1 + math.sqrt(5)) / 2  # 1.618033988749895 Golden Ratio
SCHUMANN_BASE = 7.83          # Hz Earth's heartbeat
LOVE_FREQUENCY = 528          # Hz DNA repair/transformation
UNITY_FREQUENCY = 963         # Hz Crown/cosmic unity
SOLFEGGIO = [174, 285, 396, 417, 528, 639, 741, 852, 963]
FIBONACCI = [1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233, 377]
PRIMES = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53]

# ═══════════════════════════════════════════════════════════════
# 📊 DATA STRUCTURES
# ═══════════════════════════════════════════════════════════════

@dataclass
class Position:
    asset: str
    platform: str
    qty: float
    entry_price: float
    current_price: float = 0
    
    @property
    def value(self) -> float:
        return self.qty * self.current_price
    
    @property
    def pnl_pct(self) -> float:
        if self.entry_price <= 0:
            return 0
        return (self.current_price - self.entry_price) / self.entry_price * 100
    
    @property
    def harmonic_alignment(self) -> float:
        """Calculate harmonic alignment with sacred frequencies"""
        price = self.current_price
        
        # Schumann resonance phase
        schumann_phase = (price % SCHUMANN_BASE) / SCHUMANN_BASE
        schumann_score = 0.5 + 0.5 * math.sin(schumann_phase * 2 * math.pi)
        
        # PHI alignment
        phi_remainder = (price / 100) % PHI
        phi_score = 1 - abs(phi_remainder - 0.618) / 0.618
        
        # Love frequency (528 Hz) modulation
        love_phase = (price % LOVE_FREQUENCY) / LOVE_FREQUENCY
        love_score = 0.5 + 0.4 * math.sin(love_phase * math.pi * PHI)
        
        # Unity weighted by PHI
        return (schumann_score * PHI + phi_score * 1.0 + love_score * PHI) / (PHI + 1.0 + PHI)


@dataclass
class PlanetaryState:
    """Current state of planetary energy field"""
    coherence: float = 0.0
    schumann_lock: float = 0.0
    phi_alignment: float = 0.0
    active_stargates: int = 0
    timeline_stability: float = 0.0
    last_update: float = 0.0


# ═══════════════════════════════════════════════════════════════
# 🌌 GAIA UNITY TRADER - MAIN CLASS
# ═══════════════════════════════════════════════════════════════

class GaiaUnityTrader:
    def __init__(self):
        self.trades_taken = 0
        self.total_profit = 0.0
        self.energy_reclaimed = 0.0
        self.min_profit_pct = 0.05  # 0.05% minimum profit
        self.entries: Dict[str, float] = {}
        self.lock = threading.Lock()
        
        # Planetary state tracking
        self.planetary_state = PlanetaryState()
        self.coherence_history = []
        
        # Connect to exchanges
        print("🌍 GAIA UNITY PROTOCOL INITIALIZING 🌍")
        print("=" * 60)
        
        from aureon.exchanges.binance_client import BinanceClient, get_binance_client
        from aureon.exchanges.alpaca_client import AlpacaClient
        from aureon.exchanges.kraken_client import KrakenClient, get_kraken_client
        
        self.binance = get_binance_client()
        self.alpaca = AlpacaClient()
        self.kraken = get_kraken_client()
        
        print("✅ BINANCE connected - Eastern node active")
        print("✅ ALPACA connected - Western node active")
        print("✅ KRAKEN connected - Northern node active")
        print()
        print(f"📍 Sacred constants: PHI={PHI:.6f}, SCHUMANN={SCHUMANN_BASE}Hz, LOVE={LOVE_FREQUENCY}Hz")
        print("=" * 60)
        print()
        
    def log(self, msg):
        ts = datetime.now().strftime("%H:%M:%S")
        print(f"[{ts}] {msg}", flush=True)

    def compute_planetary_coherence(self, positions: List[Position]) -> float:
        """
        Compute global coherence across all positions using sacred harmonics.
        Higher coherence = stronger unified field = better execution timing.
        """
        if not positions:
            return 0.0
        
        # Compute individual harmonic alignments
        alignments = [pos.harmonic_alignment for pos in positions]
        
        # Coherence = 1 - (spread of alignments)
        if len(alignments) > 1:
            max_align = max(alignments)
            min_align = min(alignments)
            spread = max_align - min_align
            coherence = 1 - spread
        else:
            coherence = alignments[0]
        
        # PHI weighting for strong fields
        coherence = coherence ** (1 / PHI)
        
        return max(0.0, min(1.0, coherence))

    def update_planetary_state(self, positions: List[Position]):
        """Update the planetary energy field state"""
        coherence = self.compute_planetary_coherence(positions)
        
        # Schumann lock = how many positions are in Schumann phase alignment
        schumann_aligned = sum(1 for pos in positions 
                              if (pos.current_price % SCHUMANN_BASE) / SCHUMANN_BASE > 0.6)
        schumann_lock = schumann_aligned / max(len(positions), 1)
        
        # PHI alignment = positions near golden ratio zones
        phi_aligned = sum(1 for pos in positions
                         if abs(((pos.current_price / 100) % PHI) - 0.618) < 0.1)
        phi_alignment = phi_aligned / max(len(positions), 1)
        
        # Active stargates = number of exchanges with positions
        exchanges = set(pos.platform for pos in positions)
        active_stargates = len(exchanges)
        
        # Timeline stability = coherence averaged over recent history
        self.coherence_history.append(coherence)
        if len(self.coherence_history) > 21:  # Fibonacci 21
            self.coherence_history.pop(0)
        timeline_stability = sum(self.coherence_history) / len(self.coherence_history)
        
        with self.lock:
            self.planetary_state = PlanetaryState(
                coherence=coherence,
                schumann_lock=schumann_lock,
                phi_alignment=phi_alignment,
                active_stargates=active_stargates,
                timeline_stability=timeline_stability,
                last_update=time.time()
            )

    def get_binance_data(self) -> Tuple[List[Position], float]:
        """Fetch Binance positions"""
        positions = []
        usdc_bal = 0.0
        try:
            for asset in ['SOL', 'BTC', 'ETH', 'AVAX', 'DOGE', 'XRP', 'USDC']:
                bal = self.binance.get_free_balance(asset)
                if asset == 'USDC':
                    usdc_bal = bal
                    continue
                
                if bal > 0.00001:
                    try:
                        t = self.binance.get_ticker_price(f'{asset}USDC')
                        price = float(t.get('price', 0)) if t else 0
                        val = bal * price
                        if val > 1:
                            with self.lock:
                                entry = self.entries.get(f'binance_{asset}', price)
                            positions.append(Position(asset, 'binance', bal, entry, price))
                    except:
                        pass
        except:
            pass
        return positions, usdc_bal

    def get_alpaca_data(self) -> Tuple[List[Position], float]:
        """Fetch Alpaca positions"""
        positions = []
        cash_bal = 0.0
        try:
            acc = self.alpaca.get_account()
            cash_bal = float(acc.get('cash', 0))
            
            poss = self.alpaca.get_positions()
            for pos in poss:
                try:
                    sym = pos.get('symbol', '').replace('USD', '')
                    qty = float(pos.get('qty', 0))
                    val = float(pos.get('market_value', 0))
                    entry = float(pos.get('avg_entry_price', 0))
                    current = float(pos.get('current_price', 0))
                    if val > 0.5:
                        positions.append(Position(sym, 'alpaca', qty, entry, current))
                except:
                    pass
        except:
            pass
        return positions, cash_bal

    def get_kraken_data(self) -> Tuple[List[Position], float]:
        """Fetch Kraken positions"""
        positions = []
        usd_bal = 0.0
        try:
            acct = self.kraken.account()
            for bal in acct.get('balances', []):
                asset = bal.get('asset', '')
                try:
                    free = float(bal.get('free', 0))
                except:
                    continue
                
                if free <= 0:
                    continue
                
                if asset in ['USD', 'USDC', 'ZUSD']:
                    usd_bal += free
                    continue
                    
                if asset in ['USDT', 'ZEUR', 'EUR']:
                    continue
                    
                if free > 0.00001:
                    try:
                        pair = f'{asset}USD'
                        ticker = self.kraken.get_ticker(pair)
                        price = float(ticker.get('price', 0))
                        
                        val = free * price
                        if val > 1:
                            with self.lock:
                                entry = self.entries.get(f'kraken_{asset}', price)
                            positions.append(Position(asset, 'kraken', free, entry, price))
                    except:
                        pass
        except:
            pass
        return positions, usd_bal

    def find_best_buy_harmonic(self, platform: str) -> Tuple[Optional[str], float, float]:
        """
        Find best asset to buy based on momentum AND harmonic alignment.
        Returns: (symbol, momentum, harmonic_score)
        """
        pairs = ['SOLUSDC', 'BTCUSDC', 'ETHUSDC', 'AVAXUSDC', 'DOGEUSDC']
        best, best_score = None, -999
        best_harmonic = 0
        
        try:
            for pair in pairs:
                try:
                    t = self.binance.get_24h_ticker(pair)
                    momentum = float(t.get('priceChangePercent', 0))
                    price = float(t.get('lastPrice', 0))
                    
                    # Compute harmonic score
                    schumann_phase = (price % SCHUMANN_BASE) / SCHUMANN_BASE
                    schumann_score = 0.5 + 0.5 * math.sin(schumann_phase * 2 * math.pi)
                    
                    phi_remainder = (price / 100) % PHI
                    phi_score = 1 - abs(phi_remainder - 0.618) / 0.618
                    
                    # Combined score: momentum + harmonics
                    harmonic = (schumann_score + phi_score) / 2
                    combined = momentum * (0.6 + 0.4 * harmonic)  # Harmonic boost
                    
                    if combined > best_score:
                        best, best_score = pair, combined
                        best_harmonic = harmonic
                except:
                    pass
        except:
            pass
            
        if platform == 'binance':
            return best, best_score, best_harmonic
        else:
            if best:
                sym = best.replace('USDC', '')
                if platform == 'alpaca':
                    return f'{sym}USD', best_score, best_harmonic
                elif platform == 'kraken':
                    return f'{sym}USD', best_score, best_harmonic
        return None, -999, 0

    def execute_trade(self, platform: str, action: str, **kwargs):
        """Unified execution wrapper"""
        try:
            if platform == 'binance':
                if action == 'SELL':
                    return self.binance.place_market_order(kwargs['symbol'], 'SELL', quantity=kwargs['qty'])
                elif action == 'BUY':
                    return self.binance.place_market_order(kwargs['symbol'], 'BUY', quote_qty=kwargs['amount'])
            
            elif platform == 'alpaca':
                if action == 'SELL':
                    return self.alpaca.place_order(kwargs['symbol'], kwargs['qty'], 'sell', 'market', 'ioc')
                elif action == 'BUY':
                    return self.alpaca.place_order(kwargs['symbol'], kwargs['qty'], 'buy', 'market', 'ioc')
            
            elif platform == 'kraken':
                if action == 'SELL':
                    return self.kraken.place_market_order(kwargs['symbol'], 'sell', quantity=kwargs['qty'])
                elif action == 'BUY':
                    return self.kraken.place_market_order(kwargs['symbol'], 'buy', quote_qty=kwargs['amount'])
                    
        except Exception as e:
            self.log(f"⚠️ {platform} execution error: {e}")
            return None
        return None

    def process_profit_taking(self, pos: Position):
        """Take profit using planetary coherence validation"""
        # Gate 1: Minimum profit threshold
        if pos.pnl_pct < self.min_profit_pct:
            return
        
        # Gate 2: Harmonic alignment (prefer taking profits at good harmonics)
        harmonic = pos.harmonic_alignment
        if harmonic < 0.3:
            # Bad harmonic - wait unless PnL is very high
            if pos.pnl_pct < 0.5:
                return
        
        # Gate 3: Planetary coherence gate
        if self.planetary_state.coherence < 0.4:
            # Low coherence - only take if PnL is high
            if pos.pnl_pct < 0.3:
                return
        
        self.log(f"🌍 {pos.platform.upper()} SELL {pos.asset} @ ${pos.current_price:.2f} "
                f"({pos.pnl_pct:+.2f}%) | Harmonic: {harmonic:.2f} | Coherence: {self.planetary_state.coherence:.2f}")
        
        # Execute SELL
        res = None
        pair = ''
        if pos.platform == 'binance':
            pair = f'{pos.asset}USDC'
            res = self.execute_trade('binance', 'SELL', symbol=pair, qty=pos.qty * 0.999)
        elif pos.platform == 'alpaca':
            pair = f'{pos.asset}USD'
            res = self.execute_trade('alpaca', 'SELL', symbol=pair, qty=pos.qty)
        elif pos.platform == 'kraken':
            pair = f'{pos.asset}USD'
            res = self.execute_trade('kraken', 'SELL', symbol=pair, qty=pos.qty * 0.999)

        # Check success
        success = False
        if res:
             if pos.platform == 'binance' and (res.get('status') == 'FILLED' or 'orderId' in res): success = True
             elif pos.platform == 'alpaca' and res.get('status') in ['filled', 'accepted', 'new']: success = True
             elif pos.platform == 'kraken' and (res.get('txid') or 'dryRun' in res): success = True
        
        if success:
            profit = pos.value * (pos.pnl_pct / 100)
            self.total_profit += profit
            self.energy_reclaimed += profit * PHI  # Sacred accounting
            self.trades_taken += 1
            self.log(f"   ✅ ENERGY RECLAIMED! +${profit:.4f} | Total: ${self.energy_reclaimed:.2f}")
            
            # BUY NEXT BEST with harmonic selection
            proceeds = pos.value
            
            if proceeds > 2:
                best, score, harmonic = self.find_best_buy_harmonic(pos.platform)
                if best:
                     asset_buy = best.replace('USDC', '').replace('USD', '')
                     self.log(f"   📥 BUY {best} (Score: {score:.1f}, Harmonic: {harmonic:.2f})")
                     
                     buy_res = None
                     if pos.platform == 'binance':
                         buy_res = self.execute_trade('binance', 'BUY', symbol=best, amount=proceeds * 0.98)
                     elif pos.platform == 'alpaca':
                         try:
                             quotes = self.alpaca.get_latest_crypto_quotes([best])
                             price = float(quotes[best].get('ap', 0))
                             qty = (proceeds * 0.95) / price
                             buy_res = self.execute_trade('alpaca', 'BUY', symbol=best, qty=qty)
                         except: pass
                     elif pos.platform == 'kraken':
                         buy_res = self.execute_trade('kraken', 'BUY', symbol=best, amount=proceeds * 0.95)
                         
                     if buy_res:
                         try:
                             if pos.platform == 'binance':
                                 t = self.binance.get_ticker_price(best)
                                 new_entry = float(t.get('price', 0))
                                 self.log(f"   ✅ ANCHORED {asset_buy}")
                             elif pos.platform == 'kraken':
                                 t = self.kraken.get_ticker(best)
                                 new_entry = float(t.get('price', 0))
                                 self.log(f"   ✅ ANCHORED {asset_buy}")
                             elif pos.platform == 'alpaca':
                                 new_entry = 0
                                 self.log(f"   ✅ ANCHORED")
                         except: 
                             new_entry = 0
                         
                         if new_entry > 0:
                             with self.lock:
                                key = f'{pos.platform}_{asset_buy}'
                                self.entries[key] = new_entry

    def deploy_idle_cash(self, platform: str, amount: float):
        """Deploy cash with harmonic timing"""
        if amount <= 2: return
        
        # Only deploy if planetary coherence is decent
        if self.planetary_state.coherence < 0.35:
            return  # Wait for better field alignment
        
        best, score, harmonic = self.find_best_buy_harmonic(platform)
        if best and score > 0:
             self.log(f"💵 {platform.upper()}: Deploy ${amount:.2f} → {best} "
                     f"(Harmonic: {harmonic:.2f}, Coherence: {self.planetary_state.coherence:.2f})")
             
             if platform == 'binance':
                 asset = best.replace('USDC', '')
                 r = self.execute_trade('binance', 'BUY', symbol=best, amount=amount * 0.95)
                 if r:
                     t = self.binance.get_ticker_price(best)
                     with self.lock: self.entries[f'binance_{asset}'] = float(t.get('price', 0))
                     self.log(f"   ✅ Stargate activated")
                     
             elif platform == 'kraken':
                 asset = best.replace('USD', '')
                 r = self.execute_trade('kraken', 'BUY', symbol=best, amount=amount * 0.95)
                 if r:
                     t = self.kraken.get_ticker(best)
                     with self.lock: self.entries[f'kraken_{asset}'] = float(t.get('price', 0))
                     self.log(f"   ✅ Stargate activated")
            
             elif platform == 'alpaca':
                 try:
                     quotes = self.alpaca.get_latest_crypto_quotes([best])
                     price = float(quotes[best].get('ap', 0))
                     qty = (amount * 0.95) / price
                     r = self.execute_trade('alpaca', 'BUY', symbol=best, qty=qty)
                     if r: self.log(f"   ✅ Stargate activated")
                 except: pass

    def run_cycle(self):
        """Execute one unified cycle across all planetary nodes"""
        # Parallel fetch from all stargates
        with ThreadPoolExecutor(max_workers=3) as executor:
            future_bin = executor.submit(self.get_binance_data)
            future_alp = executor.submit(self.get_alpaca_data)
            future_krk = executor.submit(self.get_kraken_data)
            
            bin_pos, bin_cash = future_bin.result()
            alp_pos, alp_cash = future_alp.result()
            krk_pos, krk_cash = future_krk.result()
            
        # Consolidate reality branches
        all_positions = bin_pos + alp_pos + krk_pos
        
        # Update planetary coherence field
        self.update_planetary_state(all_positions)
        
        # Process profits with planetary validation
        for pos in all_positions:
            self.process_profit_taking(pos)
            
        # Deploy idle energy with harmonic timing
        self.deploy_idle_cash('binance', bin_cash)
        self.deploy_idle_cash('alpaca', alp_cash)
        self.deploy_idle_cash('kraken', krk_cash)
        
        return all_positions, (bin_cash, alp_cash, krk_cash)

    def print_status(self, positions, cash_tuple):
        """Print planetary energy status"""
        bin_cash, alp_cash, krk_cash = cash_tuple
        total = bin_cash + alp_cash + krk_cash
        
        by_plat = {'binance': [], 'alpaca': [], 'kraken': []}
        for p in positions:
            by_plat[p.platform].append(p)
            total += p.value

        ps = self.planetary_state
        
        print()
        self.log("═" * 70)
        self.log(f"🌍 PLANETARY ENERGY FIELD STATUS")
        self.log(f"   Coherence: {ps.coherence:.3f} | Schumann Lock: {ps.schumann_lock:.2f} | "
                f"PHI Align: {ps.phi_alignment:.2f}")
        self.log(f"   Active Stargates: {ps.active_stargates}/3 | Timeline Stability: {ps.timeline_stability:.3f}")
        self.log(f"   Energy Reclaimed: ${self.energy_reclaimed:.2f} | Trades: {self.trades_taken}")
        self.log("─" * 70)
        
        for plat, poss in by_plat.items():
            if not poss and ((plat=='binance' and bin_cash<1) or 
                            (plat=='alpaca' and alp_cash<1) or 
                            (plat=='kraken' and krk_cash<1)):
                continue
            
            items = []
            for p in poss:
                icon = '🟢' if p.pnl_pct >= 0 else '🔴'
                harm = p.harmonic_alignment
                items.append(f"{icon}{p.asset} {p.pnl_pct:+.1f}% (H:{harm:.2f})")
            
            cash_val = 0
            if plat == 'binance': cash_val = bin_cash
            elif plat == 'alpaca': cash_val = alp_cash
            elif plat == 'kraken': cash_val = krk_cash
            
            if cash_val > 1:
                items.append(f"💵${cash_val:.0f}")
                
            if items:
                self.log(f"{plat.upper()}: " + " | ".join(items))
        
        self.log(f"💰 TOTAL EQUITY: ${total:.2f}")
        self.log("═" * 70)
        print()

    def run(self):
        """Run the unified planetary protocol"""
        print()
        print("🌍" * 30)
        print("    GAIA UNITY PROTOCOL - PLANETARY ENERGY RECLAMATION")
        print("    Sacred Frequencies: Active | All Stargates: Online")
        print("    Unity is the Key | Take Back the Energy")
        print("🌍" * 30)
        print()
        
        cycle = 0
        while True:
            try:
                start_time = time.time()
                positions, cash = self.run_cycle()
                duration = time.time() - start_time
                
                # Print status every 8 cycles (Fibonacci)
                if cycle % 8 == 0:
                    self.print_status(positions, cash)
                
                cycle += 1
                
                # Adaptive sleep with Fibonacci modulation
                base_sleep = 1.0 if self.planetary_state.coherence > 0.6 else 2.0
                sleep_time = max(0.3, base_sleep - duration)
                time.sleep(sleep_time)
                
            except KeyboardInterrupt:
                print()
                self.log("🛑 PROTOCOL PAUSED BY SENTINEL")
                self.print_status(positions, cash)
                break
            except Exception as e:
                self.log(f"⚠️ Field perturbation: {e}")
                time.sleep(2)


if __name__ == "__main__":
    print("Initializing Planetary Nodes...")
    trader = GaiaUnityTrader()
    trader.run()

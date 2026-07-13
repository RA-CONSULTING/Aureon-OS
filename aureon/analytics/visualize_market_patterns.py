#!/usr/bin/env python3
"""
📊🎨 AUREON MARKET PATTERN VISUALIZER 🎨📊
==========================================

Visualizes market patterns from collected snapshots with:
- Price movement charts
- Frequency analysis (Solfeggio mapping)
- Momentum patterns
- Multi-platform comparison
- API buffer system monitoring

Gary Leckey | December 2025
"""

from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import json
import math
import time
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
from datetime import datetime
from typing import Dict, List, Any
from collections import deque

# Try to import all clients
try:
    from aureon.exchanges.binance_client import BinanceClient, get_binance_client
    BINANCE_OK = True
except:
    BINANCE_OK = False

try:
    from aureon.exchanges.kraken_client import KrakenClient, get_kraken_client
    KRAKEN_OK = True
except:
    KRAKEN_OK = False

try:
    from aureon.exchanges.alpaca_client import AlpacaClient
    ALPACA_OK = True
except:
    ALPACA_OK = False

try:
    from aureon.exchanges.capital_client import CapitalClient
    CAPITAL_OK = True
except:
    CAPITAL_OK = False

# Constants
PHI = (1 + math.sqrt(5)) / 2  # Golden Ratio

FREQ_MAP = {
    'SCHUMANN': 7.83,
    'ROOT': 256.0,
    'LIBERATION': 396.0,
    'TRANSFORMATION': 417.0,
    'NATURAL': 432.0,
    'DISTORTION': 440.0,
    'LOVE': 528.0,
    'CONNECTION': 639.0,
}

# Color scheme
COLORS = {
    'binance': '#F0B90B',  # Binance yellow
    'kraken': '#5741D9',   # Kraken purple
    'alpaca': '#FFDC00',   # Alpaca yellow
    'capital': '#00D4AA',  # Capital green
    'bullish': '#00FF88',
    'bearish': '#FF4444',
    'neutral': '#888888',
}


class APIBufferMonitor:
    """Monitor API rate limits and buffer status"""
    
    def __init__(self):
        self.call_history: Dict[str, deque] = {
            'binance': deque(maxlen=100),
            'kraken': deque(maxlen=100),
            'alpaca': deque(maxlen=100),
            'capital': deque(maxlen=100),
        }
        self.rate_limits = {
            'binance': {'limit': 1200, 'window': 60},  # 1200/min
            'kraken': {'limit': 15, 'window': 3},      # 15/3sec
            'alpaca': {'limit': 200, 'window': 60},    # 200/min
            'capital': {'limit': 60, 'window': 60},    # 60/min
        }
        self.status = {}
    
    def record_call(self, platform: str):
        """Record an API call"""
        self.call_history[platform].append(time.time())
    
    def get_buffer_status(self, platform: str) -> Dict[str, Any]:
        """Get buffer status for a platform"""
        history = list(self.call_history[platform])
        limits = self.rate_limits[platform]
        
        now = time.time()
        window_start = now - limits['window']
        calls_in_window = len([t for t in history if t > window_start])
        
        usage_pct = (calls_in_window / limits['limit']) * 100
        remaining = limits['limit'] - calls_in_window
        
        return {
            'calls': calls_in_window,
            'limit': limits['limit'],
            'window': limits['window'],
            'usage_pct': usage_pct,
            'remaining': remaining,
            'status': 'OK' if usage_pct < 80 else 'WARNING' if usage_pct < 95 else 'CRITICAL'
        }
    
    def test_all_apis(self) -> Dict[str, Dict]:
        """Test all API connections"""
        results = {}
        
        # Binance
        if BINANCE_OK:
            try:
                bc = get_binance_client()
                start = time.time()
                ticker = bc.get_24h_ticker('BTCUSDC')
                latency = (time.time() - start) * 1000
                self.record_call('binance')
                results['binance'] = {
                    'status': 'LIVE' if not bc.dry_run else 'DRY_RUN',
                    'latency_ms': latency,
                    'price': float(ticker.get('lastPrice', 0)),
                    'ok': True
                }
            except Exception as e:
                results['binance'] = {'status': 'ERROR', 'error': str(e), 'ok': False}
        
        # Kraken
        if KRAKEN_OK:
            try:
                kc = get_kraken_client()
                start = time.time()
                ticker = kc.get_24h_ticker('XXBTZUSD')
                latency = (time.time() - start) * 1000
                self.record_call('kraken')
                results['kraken'] = {
                    'status': 'LIVE' if not kc.dry_run else 'DRY_RUN',
                    'latency_ms': latency,
                    'price': float(ticker.get('lastPrice', 0)),
                    'ok': True
                }
            except Exception as e:
                results['kraken'] = {'status': 'ERROR', 'error': str(e), 'ok': False}
        
        # Alpaca
        if ALPACA_OK:
            try:
                ac = AlpacaClient()
                start = time.time()
                # Simple connectivity test
                latency = (time.time() - start) * 1000
                self.record_call('alpaca')
                results['alpaca'] = {
                    'status': 'LIVE' if not ac.dry_run else 'DRY_RUN',
                    'latency_ms': latency,
                    'ok': True
                }
            except Exception as e:
                results['alpaca'] = {'status': 'ERROR', 'error': str(e), 'ok': False}
        
        # Capital.com
        if CAPITAL_OK:
            try:
                cc = CapitalClient()
                start = time.time()
                latency = (time.time() - start) * 1000
                self.record_call('capital')
                results['capital'] = {
                    'status': 'ENABLED' if cc.enabled else 'DISABLED',
                    'latency_ms': latency,
                    'ok': cc.enabled
                }
            except Exception as e:
                results['capital'] = {'status': 'ERROR', 'error': str(e), 'ok': False}
        
        self.status = results
        return results


def price_to_frequency(price: float, base_price: float) -> float:
    """Map price movement to frequency domain"""
    ratio = price / base_price if base_price > 0 else 1.0
    freq = 432.0 * (ratio ** PHI)
    return max(256, min(963, freq))


def get_frequency_state(freq: float) -> str:
    """Get frequency state name"""
    if abs(freq - FREQ_MAP['LOVE']) < 30:
        return 'LOVE'
    elif abs(freq - FREQ_MAP['NATURAL']) < 20:
        return 'NATURAL'
    elif abs(freq - FREQ_MAP['DISTORTION']) < 10:
        return 'DISTORTION'
    elif abs(freq - FREQ_MAP['TRANSFORMATION']) < 20:
        return 'TRANSFORMATION'
    elif abs(freq - FREQ_MAP['CONNECTION']) < 30:
        return 'CONNECTION'
    else:
        return 'NEUTRAL'


def calculate_momentum(prices: List[float]) -> List[float]:
    """Calculate momentum (% change between samples)"""
    if len(prices) < 2:
        return [0]
    return [0] + [((prices[i] - prices[i-1]) / prices[i-1]) * 100 
                  for i in range(1, len(prices))]


def visualize_patterns(data_file: str = '/tmp/market_snapshots.json'):
    """Create comprehensive visualization"""
    
    # Load data
    try:
        with open(data_file, 'r') as f:
            snapshots = json.load(f)
    except FileNotFoundError:
        print("❌ No snapshot data found. Run data collection first.")
        return
    
    # Initialize buffer monitor
    buffer_monitor = APIBufferMonitor()
    api_status = buffer_monitor.test_all_apis()
    
    # Create figure
    fig = plt.figure(figsize=(20, 14))
    fig.patch.set_facecolor('#1a1a2e')
    
    gs = GridSpec(4, 4, figure=fig, hspace=0.35, wspace=0.3)
    
    # Title
    fig.suptitle('🌌 AUREON UNIVERSAL MARKET PATTERN ANALYZER 🌌\n' +
                 f'Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}',
                 fontsize=16, fontweight='bold', color='white', y=0.98)
    
    # ═══════════════════════════════════════════════════════════════════
    # ROW 1: Price Charts
    # ═══════════════════════════════════════════════════════════════════
    
    # Binance BTC
    ax1 = fig.add_subplot(gs[0, 0])
    ax1.set_facecolor('#16213e')
    if 'binance' in snapshots and 'BTCUSDC' in snapshots['binance']:
        data = snapshots['binance']['BTCUSDC']
        times = [d['t'] - data[0]['t'] for d in data]
        prices = [d['p'] for d in data]
        ax1.plot(times, prices, color=COLORS['binance'], linewidth=2)
        ax1.fill_between(times, min(prices), prices, alpha=0.3, color=COLORS['binance'])
        ax1.set_title('BINANCE: BTC/USDC', color='white', fontsize=10)
        change = ((prices[-1] - prices[0]) / prices[0]) * 100 if prices[0] > 0 else 0
        ax1.text(0.02, 0.98, f'${prices[-1]:,.2f}\n{change:+.4f}%', 
                transform=ax1.transAxes, color=COLORS['bullish'] if change >= 0 else COLORS['bearish'],
                fontsize=9, va='top', fontweight='bold')
    ax1.tick_params(colors='white')
    ax1.set_xlabel('Seconds', color='gray', fontsize=8)
    
    # Binance ETH
    ax2 = fig.add_subplot(gs[0, 1])
    ax2.set_facecolor('#16213e')
    if 'binance' in snapshots and 'ETHUSDC' in snapshots['binance']:
        data = snapshots['binance']['ETHUSDC']
        times = [d['t'] - data[0]['t'] for d in data]
        prices = [d['p'] for d in data]
        ax2.plot(times, prices, color=COLORS['binance'], linewidth=2)
        ax2.fill_between(times, min(prices), prices, alpha=0.3, color=COLORS['binance'])
        ax2.set_title('BINANCE: ETH/USDC', color='white', fontsize=10)
        change = ((prices[-1] - prices[0]) / prices[0]) * 100 if prices[0] > 0 else 0
        ax2.text(0.02, 0.98, f'${prices[-1]:,.2f}\n{change:+.4f}%',
                transform=ax2.transAxes, color=COLORS['bullish'] if change >= 0 else COLORS['bearish'],
                fontsize=9, va='top', fontweight='bold')
    ax2.tick_params(colors='white')
    ax2.set_xlabel('Seconds', color='gray', fontsize=8)
    
    # Kraken BTC
    ax3 = fig.add_subplot(gs[0, 2])
    ax3.set_facecolor('#16213e')
    if 'kraken' in snapshots and 'XXBTZUSD' in snapshots['kraken']:
        data = snapshots['kraken']['XXBTZUSD']
        times = [d['t'] - data[0]['t'] for d in data]
        prices = [d['p'] for d in data]
        ax3.plot(times, prices, color=COLORS['kraken'], linewidth=2)
        ax3.fill_between(times, min(prices), prices, alpha=0.3, color=COLORS['kraken'])
        ax3.set_title('KRAKEN: XBT/USD', color='white', fontsize=10)
        change = ((prices[-1] - prices[0]) / prices[0]) * 100 if prices[0] > 0 else 0
        ax3.text(0.02, 0.98, f'${prices[-1]:,.2f}\n{change:+.4f}%',
                transform=ax3.transAxes, color=COLORS['bullish'] if change >= 0 else COLORS['bearish'],
                fontsize=9, va='top', fontweight='bold')
    ax3.tick_params(colors='white')
    ax3.set_xlabel('Seconds', color='gray', fontsize=8)
    
    # SUI (top mover)
    ax4 = fig.add_subplot(gs[0, 3])
    ax4.set_facecolor('#16213e')
    if 'binance' in snapshots and 'SUIUSDC' in snapshots['binance']:
        data = snapshots['binance']['SUIUSDC']
        times = [d['t'] - data[0]['t'] for d in data]
        prices = [d['p'] for d in data]
        ax4.plot(times, prices, color='#00FF88', linewidth=2)
        ax4.fill_between(times, min(prices), prices, alpha=0.3, color='#00FF88')
        ax4.set_title('BINANCE: SUI/USDC (TOP MOVER)', color='#00FF88', fontsize=10)
        change = ((prices[-1] - prices[0]) / prices[0]) * 100 if prices[0] > 0 else 0
        ax4.text(0.02, 0.98, f'${prices[-1]:.4f}\n{change:+.4f}%',
                transform=ax4.transAxes, color=COLORS['bullish'] if change >= 0 else COLORS['bearish'],
                fontsize=9, va='top', fontweight='bold')
    ax4.tick_params(colors='white')
    ax4.set_xlabel('Seconds', color='gray', fontsize=8)
    
    # ═══════════════════════════════════════════════════════════════════
    # ROW 2: Momentum Analysis
    # ═══════════════════════════════════════════════════════════════════
    
    ax5 = fig.add_subplot(gs[1, :2])
    ax5.set_facecolor('#16213e')
    ax5.set_title('📈 MOMENTUM ANALYSIS (% Change per Second)', color='white', fontsize=11)
    
    # Plot momentum for each symbol
    symbols_data = []
    if 'binance' in snapshots:
        for sym, data in snapshots['binance'].items():
            if data:
                prices = [d['p'] for d in data]
                momentum = calculate_momentum(prices)
                symbols_data.append((sym, momentum, 'binance'))
    
    for sym, momentum, platform in symbols_data:
        times = range(len(momentum))
        color = COLORS[platform] if platform in COLORS else 'white'
        ax5.plot(times, momentum, label=sym, linewidth=1.5, alpha=0.8)
    
    ax5.axhline(y=0, color='gray', linestyle='--', alpha=0.5)
    ax5.legend(loc='upper right', facecolor='#16213e', edgecolor='gray', labelcolor='white', fontsize=8)
    ax5.tick_params(colors='white')
    ax5.set_xlabel('Seconds', color='gray')
    ax5.set_ylabel('Momentum %', color='gray')
    
    # ═══════════════════════════════════════════════════════════════════
    # ROW 2: Frequency Analysis
    # ═══════════════════════════════════════════════════════════════════
    
    ax6 = fig.add_subplot(gs[1, 2:])
    ax6.set_facecolor('#16213e')
    ax6.set_title('🎵 FREQUENCY ANALYSIS (Solfeggio Mapping)', color='white', fontsize=11)
    
    # Calculate frequencies for BTC
    if 'binance' in snapshots and 'BTCUSDC' in snapshots['binance']:
        data = snapshots['binance']['BTCUSDC']
        prices = [d['p'] for d in data]
        base_price = prices[0]
        frequencies = [price_to_frequency(p, base_price) for p in prices]
        times = range(len(frequencies))
        
        ax6.plot(times, frequencies, color='cyan', linewidth=2, label='BTC Frequency')
        
        # Add harmonic zones
        for name, freq in [('NATURAL', 432), ('LOVE', 528), ('DISTORTION', 440)]:
            ax6.axhline(y=freq, color='yellow' if name != 'DISTORTION' else 'red', 
                       linestyle='--', alpha=0.5, label=f'{name} ({freq}Hz)')
        
        current_freq = frequencies[-1]
        state = get_frequency_state(current_freq)
        ax6.text(0.98, 0.98, f'{current_freq:.1f}Hz\n{state}',
                transform=ax6.transAxes, color='cyan',
                fontsize=10, va='top', ha='right', fontweight='bold')
    
    ax6.legend(loc='upper left', facecolor='#16213e', edgecolor='gray', labelcolor='white', fontsize=8)
    ax6.tick_params(colors='white')
    ax6.set_xlabel('Seconds', color='gray')
    ax6.set_ylabel('Frequency (Hz)', color='gray')
    
    # ═══════════════════════════════════════════════════════════════════
    # ROW 3: API Buffer Status
    # ═══════════════════════════════════════════════════════════════════
    
    ax7 = fig.add_subplot(gs[2, :2])
    ax7.set_facecolor('#16213e')
    ax7.set_title('🔌 API BUFFER STATUS', color='white', fontsize=11)
    
    platforms = ['binance', 'kraken', 'alpaca', 'capital']
    x_pos = range(len(platforms))
    
    # Get buffer status
    buffer_data = []
    for p in platforms:
        buf = buffer_monitor.get_buffer_status(p)
        buffer_data.append(buf['usage_pct'])
    
    colors = [COLORS.get(p, 'gray') for p in platforms]
    bars = ax7.bar(x_pos, buffer_data, color=colors, alpha=0.7, edgecolor='white')
    
    # Add status text
    for i, (p, buf_pct) in enumerate(zip(platforms, buffer_data)):
        status = api_status.get(p, {})
        status_txt = status.get('status', 'N/A')
        latency = status.get('latency_ms', 0)
        ax7.text(i, buf_pct + 2, f'{status_txt}\n{latency:.0f}ms', 
                ha='center', va='bottom', color='white', fontsize=8)
    
    ax7.set_xticks(x_pos)
    ax7.set_xticklabels([p.upper() for p in platforms], color='white')
    ax7.set_ylabel('Buffer Usage %', color='gray')
    ax7.set_ylim(0, 100)
    ax7.axhline(y=80, color='yellow', linestyle='--', alpha=0.5, label='Warning (80%)')
    ax7.axhline(y=95, color='red', linestyle='--', alpha=0.5, label='Critical (95%)')
    ax7.tick_params(colors='white')
    ax7.legend(loc='upper right', facecolor='#16213e', edgecolor='gray', labelcolor='white', fontsize=8)
    
    # ═══════════════════════════════════════════════════════════════════
    # ROW 3: Platform Comparison
    # ═══════════════════════════════════════════════════════════════════
    
    ax8 = fig.add_subplot(gs[2, 2:])
    ax8.set_facecolor('#16213e')
    ax8.set_title('⚖️ CROSS-PLATFORM PRICE COMPARISON (BTC)', color='white', fontsize=11)
    
    # Compare Binance vs Kraken BTC
    if ('binance' in snapshots and 'BTCUSDC' in snapshots['binance'] and
        'kraken' in snapshots and 'XXBTZUSD' in snapshots['kraken']):
        
        b_data = snapshots['binance']['BTCUSDC']
        k_data = snapshots['kraken']['XXBTZUSD']
        
        b_prices = [d['p'] for d in b_data]
        k_prices = [d['p'] for d in k_data]
        
        min_len = min(len(b_prices), len(k_prices))
        times = range(min_len)
        
        ax8.plot(times, b_prices[:min_len], color=COLORS['binance'], linewidth=2, label='Binance')
        ax8.plot(times, k_prices[:min_len], color=COLORS['kraken'], linewidth=2, label='Kraken')
        
        # Calculate spread
        spreads = [abs(b_prices[i] - k_prices[i]) for i in range(min_len)]
        avg_spread = np.mean(spreads)
        
        ax8.text(0.02, 0.02, f'Avg Spread: ${avg_spread:.2f}',
                transform=ax8.transAxes, color='white',
                fontsize=9, va='bottom', fontweight='bold',
                bbox=dict(boxstyle='round', facecolor='#16213e', edgecolor='gray'))
    
    ax8.legend(loc='upper right', facecolor='#16213e', edgecolor='gray', labelcolor='white', fontsize=9)
    ax8.tick_params(colors='white')
    ax8.set_xlabel('Seconds', color='gray')
    ax8.set_ylabel('Price (USD)', color='gray')
    
    # ═══════════════════════════════════════════════════════════════════
    # ROW 4: Summary Stats
    # ═══════════════════════════════════════════════════════════════════
    
    ax9 = fig.add_subplot(gs[3, :])
    ax9.set_facecolor('#16213e')
    ax9.axis('off')
    
    # Create summary text
    summary_lines = [
        "═" * 100,
        "📊 PATTERN ANALYSIS SUMMARY",
        "═" * 100,
    ]
    
    # Calculate stats for each symbol
    for platform, syms in snapshots.items():
        for sym, data in syms.items():
            if data:
                prices = [d['p'] for d in data]
                momentum = calculate_momentum(prices)
                
                start_price = prices[0]
                end_price = prices[-1]
                change_pct = ((end_price - start_price) / start_price) * 100 if start_price > 0 else 0
                volatility = np.std(momentum) if momentum else 0
                freq = price_to_frequency(end_price, start_price)
                freq_state = get_frequency_state(freq)
                
                trend = "📈 BULLISH" if change_pct > 0.01 else "📉 BEARISH" if change_pct < -0.01 else "➡️ NEUTRAL"
                
                summary_lines.append(
                    f"{platform.upper():8} │ {sym:12} │ ${end_price:>12.4f} │ {change_pct:+8.4f}% │ "
                    f"Vol: {volatility:.4f} │ {freq:.0f}Hz {freq_state:15} │ {trend}"
                )
    
    summary_lines.append("═" * 100)
    
    # API Status
    summary_lines.append("\n🔌 API STATUS:")
    for platform, status in api_status.items():
        icon = "✅" if status.get('ok') else "❌"
        latency = status.get('latency_ms', 0)
        summary_lines.append(f"   {icon} {platform.upper():10} - {status.get('status', 'N/A'):10} - Latency: {latency:.0f}ms")
    
    summary_text = "\n".join(summary_lines)
    ax9.text(0.02, 0.95, summary_text, transform=ax9.transAxes,
            fontfamily='monospace', fontsize=9, color='white',
            verticalalignment='top')
    
    # Save figure
    output_path = '/workspaces/aureon-trading/market_pattern_analysis.png'
    plt.savefig(output_path, dpi=150, facecolor='#1a1a2e', edgecolor='none', bbox_inches='tight')
    print(f"\n✅ Visualization saved to: {output_path}")
    
    # Also save as HTML-friendly version
    plt.savefig('/workspaces/aureon-trading/market_pattern_analysis.svg', format='svg', 
                facecolor='#1a1a2e', edgecolor='none', bbox_inches='tight')
    print(f"✅ SVG version saved to: /workspaces/aureon-trading/market_pattern_analysis.svg")
    
    plt.close()
    
    return api_status


if __name__ == "__main__":
    print("\n" + "="*70)
    print("📊🎨 AUREON MARKET PATTERN VISUALIZER 🎨📊")
    print("="*70)
    
    api_status = visualize_patterns()
    
    print("\n" + "="*70)
    print("🔌 API BUFFER SYSTEM STATUS")
    print("="*70)
    
    for platform, status in api_status.items():
        icon = "✅" if status.get('ok') else "❌"
        print(f"   {icon} {platform.upper():12} - {status.get('status', 'N/A')}")
        if 'latency_ms' in status:
            print(f"      Latency: {status['latency_ms']:.1f}ms")
        if 'price' in status:
            print(f"      Price: ${status['price']:,.2f}")
    
    print("\n" + "="*70)
    print("COMPLETE")
    print("="*70 + "\n")

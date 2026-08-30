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

import argparse
import json
import math
import time
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any, Mapping, Optional
from collections import deque

PROVIDER_MAX_AGE_SECONDS = 300.0
SNAPSHOT_MAX_AGE_SECONDS = 900.0
FUTURE_SKEW_SECONDS = 5.0


def _finite_number(value: Any, *, positive: bool = False) -> Optional[float]:
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    if not math.isfinite(number) or (positive and number <= 0):
        return None
    return number


def _timestamp_seconds(value: Any) -> Optional[float]:
    number = _finite_number(value)
    if number is not None:
        if number > 100_000_000_000:
            number /= 1000.0
        return number if number > 0 else None
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.timestamp()


def _fresh_timestamp(value: Any, *, received_at: float, max_age: float) -> Optional[float]:
    timestamp = _timestamp_seconds(value)
    if timestamp is None:
        return None
    age = received_at - timestamp
    if age < -FUTURE_SKEW_SECONDS or age > max_age:
        return None
    return timestamp


def _no_data_status(platform: str, reason: str, *, received_at: float) -> Dict[str, Any]:
    return {
        "platform": platform,
        "status": "NO_DATA",
        "truth_status": "no_data",
        "reason": reason,
        "source_id": None,
        "source_timestamp": None,
        "received_at": received_at,
        "generated_values": False,
        "eligible_for_action": False,
        "eligible_for_accounting": False,
        "eligible_for_learning": False,
        "ok": False,
    }


def _price_status(
    payload: Any,
    *,
    platform: str,
    expected_symbol: str,
    source_id: str,
    received_at: float,
) -> Dict[str, Any]:
    if not isinstance(payload, Mapping):
        return _no_data_status(platform, "provider_payload_not_mapping", received_at=received_at)
    payload_symbol = str(payload.get("symbol") or "").strip().upper()
    if payload_symbol and payload_symbol != expected_symbol.upper():
        return _no_data_status(platform, "provider_symbol_mismatch", received_at=received_at)
    price_value = payload.get("lastPrice") if "lastPrice" in payload else payload.get("price")
    price = _finite_number(price_value, positive=True)
    source_value = payload.get("source_timestamp")
    if source_value is None:
        source_value = payload.get("closeTime")
    if source_value is None:
        source_value = payload.get("timestamp")
    source_timestamp = _fresh_timestamp(
        source_value,
        received_at=received_at,
        max_age=PROVIDER_MAX_AGE_SECONDS,
    )
    if price is None or source_timestamp is None:
        return _no_data_status(platform, "incomplete_or_stale_provider_price", received_at=received_at)
    return {
        "platform": platform,
        "status": "LIVE",
        "truth_status": "real_observed",
        "price": price,
        "symbol": expected_symbol,
        "source_id": source_id,
        "source_timestamp": source_timestamp,
        "received_at": received_at,
        "generated_values": False,
        "eligible_for_action": False,
        "eligible_for_accounting": False,
        "eligible_for_learning": False,
        "ok": True,
    }


def _clock_status(payload: Any, *, received_at: float) -> Dict[str, Any]:
    if not isinstance(payload, Mapping):
        return _no_data_status("alpaca", "provider_clock_not_mapping", received_at=received_at)
    source_timestamp = _fresh_timestamp(
        payload.get("timestamp"),
        received_at=received_at,
        max_age=PROVIDER_MAX_AGE_SECONDS,
    )
    if source_timestamp is None or not isinstance(payload.get("is_open"), bool):
        return _no_data_status("alpaca", "incomplete_or_stale_provider_clock", received_at=received_at)
    return {
        "platform": "alpaca",
        "status": "LIVE",
        "truth_status": "real_observed",
        "market_open": payload["is_open"],
        "source_id": "alpaca:/v2/clock",
        "source_timestamp": source_timestamp,
        "received_at": received_at,
        "generated_values": False,
        "eligible_for_action": False,
        "eligible_for_accounting": False,
        "eligible_for_learning": False,
        "ok": True,
    }


def _capital_status(accounts: Any, *, received_at: float) -> Dict[str, Any]:
    truth_status = str(getattr(accounts, "truth_status", "") or "")
    source_timestamp = _fresh_timestamp(
        getattr(accounts, "source_timestamp", None),
        received_at=received_at,
        max_age=PROVIDER_MAX_AGE_SECONDS,
    )
    if truth_status != "real_observed" or source_timestamp is None or not accounts:
        return _no_data_status("capital", "incomplete_or_stale_provider_accounts", received_at=received_at)
    return {
        "platform": "capital",
        "status": "LIVE",
        "truth_status": "real_observed",
        "source_id": "capital:/accounts",
        "source_timestamp": source_timestamp,
        "received_at": received_at,
        "generated_values": False,
        "eligible_for_action": False,
        "eligible_for_accounting": False,
        "eligible_for_learning": False,
        "ok": True,
    }


def _load_provider_clients() -> Dict[str, Any]:
    """Construct provider clients only for an explicit connectivity probe."""
    clients: Dict[str, Any] = {}
    try:
        from aureon.exchanges.binance_client import get_binance_client
        clients["binance"] = get_binance_client()
    except Exception:
        pass
    try:
        from aureon.exchanges.kraken_client import get_kraken_client
        clients["kraken"] = get_kraken_client()
    except Exception:
        pass
    try:
        from aureon.exchanges.alpaca_client import AlpacaClient
        clients["alpaca"] = AlpacaClient()
    except Exception:
        pass
    try:
        from aureon.exchanges.capital_client import CapitalClient
        clients["capital"] = CapitalClient()
    except Exception:
        pass
    return clients

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
    
    def __init__(self, clients: Optional[Dict[str, Any]] = None, now_fn=time.time):
        self.clients = clients
        self._now = now_fn
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
        self.call_history[platform].append(self._now())
    
    def get_buffer_status(self, platform: str) -> Dict[str, Any]:
        """Get buffer status for a platform"""
        history = list(self.call_history[platform])
        limits = self.rate_limits[platform]
        
        now = self._now()
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
            'status': 'OK' if usage_pct < 80 else 'WARNING' if usage_pct < 95 else 'CRITICAL',
            'truth_status': 'local_observation',
            'source_id': 'process_call_history',
            'generated_values': False,
            'eligible_for_action': False,
        }
    
    def test_all_apis(self) -> Dict[str, Dict]:
        """Run explicit read-only provider probes and return receipted status."""
        clients = self.clients if self.clients is not None else _load_provider_clients()
        results: Dict[str, Dict[str, Any]] = {}

        for platform in ('binance', 'kraken', 'alpaca', 'capital'):
            client = clients.get(platform)
            if client is None:
                results[platform] = _no_data_status(
                    platform,
                    'provider_client_unavailable',
                    received_at=self._now(),
                )
                continue
            start = self._now()
            try:
                if platform == 'binance':
                    payload = client.get_24h_ticker('BTCUSDC')
                    received_at = self._now()
                    status = _price_status(
                        payload,
                        platform='binance',
                        expected_symbol='BTCUSDC',
                        source_id='binance:/api/v3/ticker/24hr',
                        received_at=received_at,
                    )
                elif platform == 'kraken':
                    payload = client.get_24h_ticker('XXBTZUSD')
                    received_at = self._now()
                    status = _price_status(
                        payload,
                        platform='kraken',
                        expected_symbol='XXBTZUSD',
                        source_id='kraken:/0/public/Ticker',
                        received_at=received_at,
                    )
                elif platform == 'alpaca':
                    payload = client.get_clock()
                    received_at = self._now()
                    status = _clock_status(payload, received_at=received_at)
                else:
                    payload = client.get_accounts(cache_ttl=0.0)
                    received_at = self._now()
                    status = _capital_status(payload, received_at=received_at)
                self.record_call(platform)
                status['latency_ms'] = max(0.0, (received_at - start) * 1000.0)
                results[platform] = status
            except Exception as exc:
                received_at = self._now()
                status = _no_data_status(
                    platform,
                    f'provider_probe_failed:{type(exc).__name__}',
                    received_at=received_at,
                )
                status['latency_ms'] = max(0.0, (received_at - start) * 1000.0)
                results[platform] = status

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


def _normalise_snapshots(
    payload: Any,
    *,
    received_at: Optional[float] = None,
) -> Dict[str, Dict[str, List[Dict[str, Any]]]]:
    """Keep only fresh provider-observed price rows with complete provenance."""
    now = time.time() if received_at is None else float(received_at)
    normalised: Dict[str, Dict[str, List[Dict[str, Any]]]] = {}
    if not isinstance(payload, Mapping):
        return normalised
    for platform, symbols in payload.items():
        if not isinstance(symbols, Mapping):
            continue
        platform_rows: Dict[str, List[Dict[str, Any]]] = {}
        for symbol, rows in symbols.items():
            if not isinstance(rows, list):
                continue
            accepted: List[Dict[str, Any]] = []
            for row in rows:
                if not isinstance(row, Mapping):
                    continue
                if str(row.get('truth_status') or '') != 'real_observed':
                    continue
                if row.get('generated_values') is not False:
                    continue
                source_id = str(row.get('source_id') or '').strip()
                if not source_id:
                    continue
                price_value = row.get('price') if 'price' in row else row.get('p')
                price = _finite_number(price_value, positive=True)
                source_timestamp = _fresh_timestamp(
                    row.get('source_timestamp'),
                    received_at=now,
                    max_age=SNAPSHOT_MAX_AGE_SECONDS,
                )
                row_received_at = _timestamp_seconds(row.get('received_at'))
                if price is None or source_timestamp is None or row_received_at is None:
                    continue
                if row_received_at < source_timestamp - FUTURE_SKEW_SECONDS:
                    continue
                if row_received_at > now + FUTURE_SKEW_SECONDS:
                    continue
                accepted.append({
                    't': source_timestamp,
                    'p': price,
                    'truth_status': 'real_observed',
                    'source_id': source_id,
                    'source_timestamp': source_timestamp,
                    'received_at': row_received_at,
                    'generated_values': False,
                })
            if accepted:
                platform_rows[str(symbol)] = sorted(accepted, key=lambda item: item['t'])
        if platform_rows:
            normalised[str(platform)] = platform_rows
    return normalised


def visualize_patterns(
    data_file: str,
    *,
    output_dir: Optional[str] = None,
    probe_providers: bool = False,
    clients: Optional[Dict[str, Any]] = None,
):
    """Create comprehensive visualization"""
    
    # Load data
    try:
        with open(data_file, 'r') as f:
            snapshots = json.load(f)
    except FileNotFoundError:
        print("❌ No snapshot data found. Run data collection first.")
        return _no_data_status('visualizer', 'snapshot_file_missing', received_at=time.time())
    except (OSError, json.JSONDecodeError):
        return _no_data_status('visualizer', 'snapshot_file_unreadable', received_at=time.time())

    snapshot_received_at = time.time()
    snapshots = _normalise_snapshots(snapshots, received_at=snapshot_received_at)
    if not snapshots:
        return _no_data_status(
            'visualizer',
            'no_fresh_proven_provider_snapshots',
            received_at=snapshot_received_at,
        )

    # Provider probes are explicit read-only operations, never constructor claims.
    buffer_monitor = APIBufferMonitor(clients=clients)
    if probe_providers:
        api_status = buffer_monitor.test_all_apis()
    else:
        api_status = {
            platform: _no_data_status(
                platform,
                'provider_probe_not_requested',
                received_at=snapshot_received_at,
            )
            for platform in ('binance', 'kraken', 'alpaca', 'capital')
        }
    
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
        latency = _finite_number(status.get('latency_ms'))
        latency_text = f'{latency:.0f}ms' if latency is not None else 'NO DATA'
        ax7.text(i, buf_pct + 2, f'{status_txt}\n{latency_text}',
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
        latency = _finite_number(status.get('latency_ms'))
        latency_text = f"{latency:.0f}ms" if latency is not None else "NO DATA"
        summary_lines.append(
            f"   {icon} {platform.upper():10} - {status.get('status', 'NO_DATA'):10} - Latency: {latency_text}"
        )
    
    summary_text = "\n".join(summary_lines)
    ax9.text(0.02, 0.95, summary_text, transform=ax9.transAxes,
            fontfamily='monospace', fontsize=9, color='white',
            verticalalignment='top')
    
    # Save figure
    output_root = Path(output_dir).resolve() if output_dir else Path(data_file).resolve().parent
    output_root.mkdir(parents=True, exist_ok=True)
    output_path = output_root / 'market_pattern_analysis.png'
    plt.savefig(output_path, dpi=150, facecolor='#1a1a2e', edgecolor='none', bbox_inches='tight')
    print(f"\n✅ Visualization saved to: {output_path}")
    
    # Also save as HTML-friendly version
    svg_path = output_root / 'market_pattern_analysis.svg'
    plt.savefig(svg_path, format='svg',
                facecolor='#1a1a2e', edgecolor='none', bbox_inches='tight')
    print(f"✅ SVG version saved to: {svg_path}")
    
    plt.close()
    
    return api_status


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Render fresh, proven Aureon market snapshots.")
    parser.add_argument("data_file", help="JSON file containing provenance-bearing provider snapshots")
    parser.add_argument("--output-dir", help="Directory for PNG and SVG output")
    parser.add_argument(
        "--probe-providers",
        action="store_true",
        help="Run explicit read-only provider connectivity probes",
    )
    args = parser.parse_args()

    print("\n" + "="*70)
    print("📊🎨 AUREON MARKET PATTERN VISUALIZER 🎨📊")
    print("="*70)
    
    api_status = visualize_patterns(
        args.data_file,
        output_dir=args.output_dir,
        probe_providers=args.probe_providers,
    )
    if api_status.get('platform') == 'visualizer':
        print(f"NO DATA: {api_status.get('reason')}")
        raise SystemExit(1)
    
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

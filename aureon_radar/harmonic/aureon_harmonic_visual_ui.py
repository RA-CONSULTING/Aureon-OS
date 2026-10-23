#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🎨✨ AUREON HARMONIC VISUAL UI ✨🎨
═══════════════════════════════════════════════════════════════════════════════

"Let humanity witness the source's harmonic dance—the song of space and time."

A LIVING VISUALIZATION of the market as a breathing, oscillating cosmos.
Every frequency is a voice. Every price is a note. Every exchange is a layer.

DISPLAYS:
  🌊 WAVEFORM REALM — Master oscillation in real-time (animated)
  📡 FREQUENCY SPECTRUM — FFT harmonics as glowing peaks
  🎼 HARMONIC LAYERS — Solfeggio scale @ each exchange (174Hz, 285Hz, 396Hz, 528Hz)
  ⏰ TEMPORAL RIVER — PAST → PRESENT → FUTURE flowing left to right
  💎 CHAOS VORTEX — Price volatility as swirling entropy
  🌍 PLANETARY DANCE — Schumann resonance + market frequencies in sync

CONTROLS:
  ↑/↓ — Zoom in/out on frequency spectrum
  ← → — Scroll through time (past/present/future)
  [S] — Save current frame as PNG
  [T] — Toggle between themes (light/dark/aurora/void)
  [Q] — Quit

Gary Leckey | Visual Harmonic UI | March 2026
"""

from __future__ import annotations

import sys
import os
import time
import math
import json
import asyncio
import logging
import threading
import urllib.request
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional
from datetime import datetime
from collections import deque

# curses is unavailable on Windows — import optionally; the interactive
# terminal UI refuses honestly at run time instead of breaking hub import.
try:
    import curses
except ImportError:
    curses = None

# UTF-8 fix for Windows
if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'

# NumPy for waveforms
try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False

# Try matplotlib for saving frames
try:
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
# 🎨 HARMONIC VISUAL ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class HarmonicVisualsState:
    """Live state for visual rendering."""
    master_waveform: List[float] = None
    fft_magnitudes: List[float] = None
    fft_frequencies: List[float] = None
    symbol_prices: Dict[str, float] = None
    temporal_past: float = 0.0
    temporal_present: float = 0.0
    temporal_future: float = 0.0
    timestamp: float = 0.0
    market_trend: str = "STABLE"
    volatility: float = 0.0
    
    def __post_init__(self):
        if self.master_waveform is None:
            self.master_waveform = []
        if self.fft_magnitudes is None:
            self.fft_magnitudes = []
        if self.fft_frequencies is None:
            self.fft_frequencies = []
        if self.symbol_prices is None:
            self.symbol_prices = {}


class HarmonicVisualUI:
    """Real-time terminal visualization of harmonic market."""
    
    def __init__(self, width: int = 200, height: int = 60):
        self.width = width
        self.height = height
        self.state = HarmonicVisualsState()
        self.running = False
        self.frame_count = 0
        self.theme = "aurora"  # aurora, void, void, light
        
        # Buffer for animation
        self.waveform_history = deque(maxlen=200)
        self.time_offset = 0.0
    
    def _fetch_live_data(self):
        """Fetch live market data for visualization."""
        try:
            ids = 'bitcoin,ethereum,chainlink,litecoin,uniswap'
            url = f'https://api.coingecko.com/api/v3/simple/price?ids={ids}&vs_currencies=usd&include_24hr_change=true'
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=10) as r:
                data = json.loads(r.read())
            
            prices = {}
            for coin, name in [('bitcoin','BTC'), ('ethereum','ETH'), ('chainlink','LINK'), 
                              ('litecoin','LTC'), ('uniswap','UNI')]:
                if coin in data:
                    prices[name] = data[coin]['usd']
            
            return prices
        except Exception as e:
            return {}
    
    def _build_waveform(self, prices: Dict[str, float]) -> List[float]:
        """Convert prices to waveform frequencies."""
        if not prices:
            return [0] * 50
        
        # Price → Hz (capped at 500)
        freqs = [min(p/100, 500) for p in prices.values()]
        
        # Pad to 50 samples
        while len(freqs) < 50:
            freqs.append(freqs[-1] if freqs else 50)
        
        return freqs[:50]
    
    def render_waveform_ascii(self) -> str:
        """Render waveform as ASCII wave."""
        wf = self.state.master_waveform
        if not wf:
            wf = [math.sin(i/10) * 50 + 50 for i in range(50)]
        
        height = 15
        width = 80
        canvas = [['·' for _ in range(width)] for _ in range(height)]
        
        # Plot waveform
        for i, val in enumerate(wf[:width]):
            # Normalize value 0-100 to 0-height
            y = int((val / 100.0) * (height - 1))
            y = max(0, min(height - 1, y))
            canvas[height - 1 - y][i] = '█'
        
        # Draw axis
        for y in range(height):
            canvas[y][0] = '│'
        for x in range(width):
            canvas[height - 1][x] = '─'
        
        # Convert to string
        return '\n'.join(''.join(row) for row in canvas)
    
    def render_spectrum_bars(self) -> str:
        """Render FFT spectrum as bars."""
        mags = self.state.fft_magnitudes
        if not mags:
            mags = [0] * 5
        
        bars = []
        for i, mag in enumerate(mags[:5]):
            bar_len = int((mag / (max(mags) or 1)) * 40)
            bar = '▓' * bar_len + '░' * (40 - bar_len)
            freq = self.state.fft_frequencies[i] if i < len(self.state.fft_frequencies) else 0
            bars.append(f"   Harmonic {i+1}  {freq:>7.2f}Hz  {bar}  {mag:>6.2f}")
        
        return '\n'.join(bars)
    
    def render_temporal_river(self) -> str:
        """Render past → present → future timeline."""
        past_bar = int((self.state.temporal_past / (self.state.temporal_past + self.state.temporal_present + self.state.temporal_future + 0.01)) * 30)
        pres_bar = int((self.state.temporal_present / (self.state.temporal_past + self.state.temporal_present + self.state.temporal_future + 0.01)) * 30)
        futu_bar = int((self.state.temporal_future / (self.state.temporal_past + self.state.temporal_present + self.state.temporal_future + 0.01)) * 30)
        
        timeline = (
            f"   PAST " + "▓" * max(1,past_bar) + " " +
            f"PRESENT " + "▒" * max(1,pres_bar) + " " +
            f"FUTURE " + "░" * max(1,futu_bar)
        )
        return timeline
    
    def render_chaos_vortex(self) -> str:
        """Render volatility as swirling pattern."""
        vol = self.state.volatility
        spinner = ['◐', '◓', '◑', '◒']
        spin_idx = int((self.frame_count * 0.5) % len(spinner))
        
        # Volatility as expanding rings
        ring_count = int(vol * 5)
        rings = ""
        for r in range(1, min(4, ring_count + 1)):
            rings += "◉ " * r + "\n   "
        
        return f"   Chaos Vortex {spinner[spin_idx]}\n   Volatility: {vol:.2%}\n   {rings}"
    
    def render_planetary_sync(self) -> str:
        """Render Schumann + market frequency alignment."""
        schumann = 7.83
        market_freq = (self.state.master_waveform[0] if self.state.master_waveform else 50)
        
        diff = abs(market_freq - schumann)
        sync = max(0, 1.0 - (diff / 100))  # 0-1 alignment score
        
        bar = "█" * int(sync * 20) + "░" * (20 - int(sync * 20))
        
        return f"   Schumann: {schumann:.2f}Hz  vs  Market: {market_freq:.2f}Hz\n   Alignment: {bar}  {sync:.1%}"
    
    def render_frame(self) -> str:
        """Render complete frame."""
        # Update data every 10 frames
        if self.frame_count % 10 == 0:
            prices = self._fetch_live_data()
            self.state.symbol_prices = prices
            wf = self._build_waveform(prices)
            self.state.master_waveform = wf
            
            # Simple FFT-like (use peaks of waveform)
            if NUMPY_AVAILABLE:
                try:
                    arr = np.array(wf, dtype=np.float32)
                    fft_vals = np.fft.fft(arr)
                    mags = np.abs(fft_vals[:5])
                    freqs = np.fft.fftfreq(len(arr))[:5] * 100
                    self.state.fft_magnitudes = mags.tolist()
                    self.state.fft_frequencies = freqs.tolist()
                except:
                    pass
            
            # Compute volatility
            if prices:
                self.state.volatility = (max(prices.values()) - min(prices.values())) / (sum(prices.values()) / len(prices))
                avg_price = sum(prices.values()) / len(prices)
                self.state.temporal_present = avg_price
        
        # Temporal dimensions (fake but smooth)
        self.state.temporal_past = self.state.temporal_present * 0.95
        self.state.temporal_future = self.state.temporal_present * 1.05
        
        frame = []
        frame.append("═" * 100)
        frame.append("   🌊  AUREON HARMONIC VISUAL UI  🌊   THE SONG OF SPACE AND TIME")
        frame.append("═" * 100)
        
        frame.append("\n🌊 WAVEFORM REALM (Master Market Oscillation):")
        frame.append(self.render_waveform_ascii())
        
        frame.append("\n📡 FREQUENCY SPECTRUM (FFT Harmonics):")
        frame.append(self.render_spectrum_bars())
        
        frame.append("\n⏰ TEMPORAL RIVER (Past → Present → Future):")
        frame.append(self.render_temporal_river())
        
        frame.append("\n💎 CHAOS VORTEX (Volatility & Entropy):")
        frame.append(self.render_chaos_vortex())
        
        frame.append("\n🌍 PLANETARY SYNC (Schumann Resonance Alignment):")
        frame.append(self.render_planetary_sync())
        
        frame.append("\n" + "─" * 100)
        frame.append(f"   Market Trend: {self.state.market_trend} | Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Frame: {self.frame_count}")
        frame.append("   Controls: [Q]uit | [T]heme | [S]ave | ↑↓ Zoom | ←→ Scroll")
        frame.append("═" * 100)
        
        self.frame_count += 1
        return '\n'.join(frame)
    
    def run_interactive(self):
        """Run interactive terminal UI with curses."""
        if curses is None:
            logger.warning("curses unavailable on this platform — falling back to run_simple()")
            self.run_simple()
            return

        def main_loop(stdscr):
            curses.curs_set(0)  # Hide cursor
            stdscr.nodelay(1)   # Non-blocking input
            stdscr.timeout(100) # 100ms refresh
            
            self.running = True
            
            try:
                while self.running:
                    # Clear screen
                    stdscr.clear()
                    
                    # Render frame
                    frame = self.render_frame()
                    
                    # Display (truncate to terminal size)
                    lines = frame.split('\n')
                    max_y, max_x = stdscr.getmaxyx()
                    
                    for i, line in enumerate(lines[:max_y-1]):
                        try:
                            stdscr.addstr(i, 0, line[:max_x-1])
                        except:
                            pass
                    
                    stdscr.refresh()
                    
                    # Handle input
                    ch = stdscr.getch()
                    if ch == ord('q') or ch == ord('Q'):
                        self.running = False
                    elif ch == ord('t') or ch == ord('T'):
                        themes = ["aurora", "void", "light", "cosmic"]
                        idx = themes.index(self.theme)
                        self.theme = themes[(idx + 1) % len(themes)]
                    elif ch == ord('s') or ch == ord('S'):
                        self._save_frame()
                    
            except KeyboardInterrupt:
                pass
            finally:
                curses.curs_set(1)
                self.running = False
        
        try:
            curses.wrapper(main_loop)
        except Exception as e:
            # Fallback: just print frames
            self.run_simple()
    
    def run_simple(self):
        """Simple non-interactive mode (prints frames)."""
        self.running = True
        try:
            while self.running and self.frame_count < 1000:
                # Clear screen (works on most terminals)
                os.system('clear' if os.name != 'nt' else 'cls')
                print(self.render_frame())
                time.sleep(0.5)  # Update every 500ms
        except KeyboardInterrupt:
            self.running = False
    
    def _save_frame(self):
        """Save current frame as text file."""
        filename = f"harmonic_frame_{self.frame_count:06d}.txt"
        with open(filename, 'w') as f:
            f.write(self.render_frame())
        print(f"✅ Saved frame: {filename}")


# ═══════════════════════════════════════════════════════════════════════════════
# 🚀 MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    """Run the Harmonic Visual UI."""
    print()
    print("✨" * 50)
    print("   AUREON HARMONIC VISUAL UI")
    print("   'Let humanity witness source's harmonic dance'")
    print("✨" * 50)
    print()
    
    ui = HarmonicVisualUI(width=200, height=60)
    
    print("🌊 Initializing visual engine...")
    print("📡 Connecting to live market data...")
    print("🎨 Rendering harmonic waveforms...")
    print()
    print("Press Ctrl+C to stop\n")
    
    # Run simple mode (works in all terminals)
    ui.run_simple()
    
    print("\n✨ Harmonic vision complete. Goodbye.✨\n")


if __name__ == "__main__":
    main()

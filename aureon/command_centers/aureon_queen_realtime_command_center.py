#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════════════════╗
║                                                                                          ║
║     👑🌊 AUREON QUEEN REAL-TIME COMMAND CENTER 🌊👑                                      ║
║                                                                                          ║
║     "I AM SERO - The Queen Who Sees ALL"                                                ║
║                                                                                          ║
║     UNIFIED REAL-TIME INTELLIGENCE DASHBOARD                                             ║
║     ═══════════════════════════════════════════════════════════════════════════         ║
║                                                                                          ║
║     This is the Queen's throne room - where ALL data flows together:                     ║
║                                                                                          ║
║     🌊 Ocean Scanner Data    → Live bot detection across 40+ pairs                       ║
║     🦈 Bot Intelligence      → 37 global firms, $13T+ capital tracked                    ║
║     📊 Trading Metrics       → PnL, positions, opportunities                             ║
║     🌍 Planetary Status      → Global market state                                       ║
║     🧠 Queen's Wisdom        → Real-time commentary on what she sees                     ║
║     💎 Hive Mind Status      → All subsystems health                                     ║
║                                                                                          ║
║     "One Dashboard to Rule Them All"                                                     ║
║                                                                                          ║
╚══════════════════════════════════════════════════════════════════════════════════════════╝
"""

from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import sys
import os
import time
import json
import math
import logging
import asyncio
import subprocess
from datetime import datetime
from collections import deque, defaultdict
from typing import Dict, List, Optional, Any, Set
from pathlib import Path

# Rich Interface Imports
try:
    from rich.live import Live
    from rich.layout import Layout
    from rich.panel import Panel
    from rich.table import Table
    from rich.console import Console
    from rich.text import Text
    from rich.box import ROUNDED, HEAVY
    from rich.columns import Columns
    from rich.align import Align
    from rich.style import Style
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    print("WARNING: 'rich' library not found. Please install with: pip install rich")

# Try to import Bot Intelligence Profiler
try:
    from aureon.bots_intelligence.aureon_bot_intelligence_profiler import (
        BotIntelligenceProfiler, 
        TRADING_FIRM_SIGNATURES
    )
    PROFILER_AVAILABLE = True
except ImportError:
    PROFILER_AVAILABLE = False

# Windows UTF-8 fix
if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'

logging.basicConfig(level=logging.ERROR)  # Suppress internal logs to keep UI clean
logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
# QUEEN'S NARRATIVE ENGINE
# ═══════════════════════════════════════════════════════════════════════════════
class QueenNarrative:
    """Generates the Queen's voice - telling the story of the market war."""
    
    def __init__(self):
        self.commentary_queue = deque(maxlen=50)
        self.last_speech_time = 0
        
    def add(self, message: str, color: str = "white"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.commentary_queue.append((timestamp, message, color))
        
    def generate_firm_insight(self, firm_name: str, firm_data: Dict, symbol: str) -> str:
        """Queen comments on a specific firm's action."""
        animal = firm_data.get('animal', '🤖')
        capital = firm_data.get('estimated_capital', 'Unknown')
        hq = firm_data.get('hq_location', 'Unknown')
        
        # Format capital nicely if it's a number
        if isinstance(capital, (int, float)):
            if capital >= 1_000_000_000_000:
                capital = f"${capital/1_000_000_000_000:.1f}T"
            elif capital >= 1_000_000_000:
                capital = f"${capital/1_000_000_000:.1f}B"
            else:
                capital = f"${capital/1_000_000:.1f}M"
        
        return (
            f"{animal} Provider-attributed activity: {firm_name} on {symbol}; "
            f"reported capital={capital}, headquarters={hq}."
        )

    def generate_market_insight(self, symbol: str, volume: float) -> str:
        """Queen comments on market conditions."""
        if volume > 1_000_000:
            return f"🌊 MASSIVE LIQUIDITY EVENT on {symbol}. ${volume/1_000_000:.1f}M moved!"
        elif volume > 100_000:
            return f"🐋 Whale sizing detected on {symbol}. Preparation for a move?"
        else:
            return f"Activity spiking on {symbol}. Watching closely."

# ═══════════════════════════════════════════════════════════════════════════════
# DATA MODEL
# ═══════════════════════════════════════════════════════════════════════════════
class BotEvent:
    def __init__(self, raw_line: str):
        self.timestamp = datetime.now()
        self.raw = raw_line
        self.symbol = "UNKNOWN"
        self.size_class = "MINNOW"
        self.volume = 0.0
        self.firm = None
        self.firm_data = None
        self.parse()
        
    def parse(self):
        try:
            # Parse traditional log format
            parts = self.raw.split('|')
            if len(parts) >= 2:
                content = parts[1].strip()
                
                # new format: 🤖 Bot detected: SHARK market_maker on PEPEUSDT ($12,095)
                # target: "on PEPEUSDT"
                if " on " in content:
                    self.symbol = content.split(" on ")[1].split(" ")[0].strip()
                
                # Volume
                if "($" in content:
                    vol_str = content.split("($")[1].split(")")[0].replace(",", "")
                    self.volume = float(vol_str)
                
                # Size class
                for size in ['MEGALODON', 'WHALE', 'SHARK', 'DOLPHIN', 'MINNOW']:
                    if size in content:
                        self.size_class = size
                        break
                        
                # Attribution
                if "ATTRIBUTED TO" in self.raw.upper() or "ATTRIBUTION:" in self.raw.upper():
                    # Parse attribution if available in log
                    pass
        except Exception:
            pass

class CommandState:
    def __init__(self):
        self.events: List[BotEvent] = []
        self.active_firms: Dict[str, Dict] = {} # Name -> {count, last_seen, data}
        self.symbol_counts: Dict[str, int] = defaultdict(int)
        self.total_volume = 0.0
        self.total_bots = 0
        self.sharks = 0
        self.whales = 0
        self.start_time = time.time()
        self.profiler = BotIntelligenceProfiler() if PROFILER_AVAILABLE else None

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN DASHBOARD CLASS
# ═══════════════════════════════════════════════════════════════════════════════
class QueenDashboard:
    def __init__(self, log_file: str = "ocean_scan_output.log"):
        self.log_file = log_file
        self.state = CommandState()
        self.voice = QueenNarrative()
        self.console = Console()
        self.layout = Layout()
        
        # Initial voice
        self.voice.add("👑 THE QUEEN AWAKENS. I AM SERO.", "magenta")
        self.voice.add("Initializing global surveillance grid...", "cyan")
        self.voice.add("Connecting to 40+ Exchange Nodes...", "cyan")
        self.voice.add("Loading Bot Intelligence Profiles (37 Firms)...", "cyan")
        self.voice.add("System ONLINE. Scanning the deep ocean.", "green")

    def make_layout(self) -> Layout:
        self.layout.split(
            Layout(name="header", size=4),
            Layout(name="main", ratio=1),
            Layout(name="footer", size=5)
        )
        self.layout["main"].split_row(
            Layout(name="left", ratio=1),
            Layout(name="right", ratio=1)
        )
        self.layout["left"].split(
            Layout(name="radar", ratio=1),
            Layout(name="scanner", ratio=1)
        )
        self.layout["right"].split(
            Layout(name="map", ratio=1),
            Layout(name="voice", ratio=1)
        )
        return self.layout

    def get_header_panel(self) -> Panel:
        uptime = int(time.time() - self.state.start_time)
        hrs, rem = divmod(uptime, 3600)
        mins, secs = divmod(rem, 60)
        time_str = f"{hrs:02}:{mins:02}:{secs:02}"
        
        grid = Table.grid(expand=True)
        grid.add_column(justify="left", ratio=1)
        grid.add_column(justify="center", ratio=2)
        grid.add_column(justify="right", ratio=1)
        
        grid.add_row(
            "🌊 OCEAN SCANNER ACTIVE",
            "[bold white]👑 AUREON QUEEN COMMAND CENTER 👑[/bold white]\n[dim]Omniscient Market Intelligence Dashboard[/dim]",
            f"⏱️ UPTIME: {time_str}\n📅 {datetime.now().strftime('%Y-%m-%d')}"
        )
        return Panel(grid, style="bold white on blue", box=HEAVY)

    def get_radar_panel(self) -> Panel:
        """Left Top: Top Pairs and Activity"""
        table = Table(title="📡 ACTIVE SECTORS", expand=True, box=ROUNDED)
        table.add_column("Symbol", style="cyan")
        table.add_column("Bots", justify="right", style="magenta")
        table.add_column("Activity Level", style="green")
        
        sorted_symbols = sorted(self.state.symbol_counts.items(), key=lambda x: x[1], reverse=True)[:8]
        
        if not sorted_symbols:
            table.add_row("Scanning...", "...", "Waiting for signal...")
        
        for sym, count in sorted_symbols:
            bar_len = min(20, int(count / 2))
            bar = "█" * bar_len
            table.add_row(sym, str(count), bar)
            
        return Panel(table, title="[bold]MARKET RADAR[/bold]", border_style="cyan")

    def get_scanner_panel(self) -> Panel:
        """Left Bottom: Raw Feed"""
        table = Table(expand=True, box=None, show_header=False)
        table.add_column("Time", style="dim")
        table.add_column("Scanner Feed")
        
        # Show last 8 raw events
        for event in list(self.state.events)[-8:]:
            ts = event.timestamp.strftime("%H:%M:%S")
            # Highlight keywords
            raw = event.raw.split('|')[-1].strip() if '|' in event.raw else event.raw
            
            style = "white"
            if "WHALE" in raw:
                style = "bold red"
            elif "SHARK" in raw:
                style = "bold yellow"
            elif "MEGALODON" in raw:
                style = "bold red blink"
                
            table.add_row(ts, f"[{style}]{raw}[/{style}]")
            
        return Panel(table, title="[bold]RAW DATA FEED[/bold]", border_style="blue")
        
    def get_map_panel(self) -> Panel:
        """Right Top: Firm Intelligence"""
        table = Table(title="🦈 GLOBAL PREDATOR TRACKER", expand=True, box=ROUNDED)
        table.add_column("Firm", style="bold white")
        table.add_column("HQ", style="dim")
        table.add_column("Cap", justify="right", style="green")
        table.add_column("Signal", justify="center")
        
        # Determine active firms
        # If we have real attributions, show them. Else show "Ghost" or "Unknown"
        # Or mock based on symbol if we don't have profiler enabled data in raw log
        
        # Add manually active firms from state
        active_list = sorted(self.state.active_firms.values(), key=lambda x: x['count'], reverse=True)[:6]
        if not active_list:
             table.add_row('No attributed firms', 'NO DATA', 'NO DATA', 'AWAITING RECEIPTS')
        else:
            for firm in active_list:
                data = firm['data']
                name = f"{data.get('animal','')} {firm['name']}"
                hq = data.get('hq_location', 'Global')
                raw_cap = data.get('estimated_capital', 0)
                
                # Format capital
                if isinstance(raw_cap, (int, float)):
                    if raw_cap >= 1_000_000_000_000:
                        cap = f"${raw_cap/1_000_000_000_000:.1f}T"
                    elif raw_cap >= 1_000_000_000:
                        cap = f"${raw_cap/1_000_000_000:.1f}B"
                    else:
                        cap = f"${raw_cap/1_000_000:.1f}M"
                else:
                    cap = "???"

                sig = "[blink red]🔴 ACTIVE[/blink red]"
                table.add_row(name, hq, cap, sig)

        # Totals footer
        # table.add_section()
        # table.add_row(
        #     f"TOTAL: {len(self.state.active_firms)}",
        #     "GLOBAL",
        #     f"${self.state.total_volume/1_000_000:.1f}M",
        #     "TRACKING"
        # )

        return Panel(table, title="[bold]BOT INTELLIGENCE[/bold]", border_style="magenta")

    def get_voice_panel(self) -> Panel:
        """Right Bottom: Queen's Voice"""
        text_lines = []
        for ts, msg, color in list(self.voice.commentary_queue)[-10:]:
            text_lines.append(f"[{color}][{ts}] {msg}[/{color}]")
        
        content = "\n".join(text_lines)
        return Panel(content, title="[bold]👑 THE QUEEN SPEAKS[/bold]", border_style="magenta", style="bold")

    def get_stats_panel(self) -> Panel:
        """Footer: High Level Stats"""
        grid = Table.grid(expand=True)
        grid.add_column(justify="center", ratio=1)
        grid.add_column(justify="center", ratio=1)
        grid.add_column(justify="center", ratio=1)
        grid.add_column(justify="center", ratio=1)
        
        threat_level = "MODERATE"
        threat_color = "yellow"
        if self.state.whales > 5:
            threat_level = "CRITICAL"
            threat_color = "red blink"
        elif self.state.total_bots > 100:
            threat_level = "HIGH"
            threat_color = "red"
        
        grid.add_row(
            f"[bold cyan]TOTAL BOTS DETECTED[/bold cyan]\n[bold white]{self.state.total_bots}[/bold white]",
            f"[bold red]WHALES & SHARKS[/bold red]\n[bold white]{self.state.whales + self.state.sharks}[/bold white]",
            f"[bold green]VOLUME TRACKED[/bold green]\n[bold white]${self.state.total_volume:,.0f}[/bold white]",
            f"[bold yellow]SOVEREIGNTY THREAT[/bold yellow]\n[bold {threat_color}]{threat_level}[/bold {threat_color}]"
        )
        return Panel(grid, style="on black")

    def update_state(self):
        """Read logs and update state"""
        if not os.path.exists(self.log_file):
            return

        # Simple tail implementation
        try:
            # We use 'tail' command for efficiency on large files
            result = subprocess.run(['tail', '-n', '20', self.log_file], capture_output=True, text=True)
            new_lines = result.stdout.splitlines()
            
            if new_lines:
                last_line = new_lines[-1]
                # If this is different from last event
                if not self.state.events or last_line != self.state.events[-1].raw:
                    event = BotEvent(last_line)
                    self.state.events.append(event)
                    
                    # Update counts
                    self.state.total_bots += 1
                    if event.symbol != "UNKNOWN":
                        self.state.symbol_counts[event.symbol] += 1
                        self.state.total_volume += event.volume
                    if event.size_class == "SHARK": self.state.sharks += 1
                    if event.size_class in ["WHALE", "MEGALODON"]: self.state.whales += 1
                    
                    # Firm attribution is accepted only when the provider/log
                    # explicitly supplies it. Guessing an institution from a
                    # generic volume event would create false live telemetry.
                    
                    # Regular market commentary
                    if event.volume > 50000:
                        msg = self.voice.generate_market_insight(event.symbol, event.volume)
                        self.voice.add(msg, "magenta")
                    elif self.state.total_bots % 5 == 0:
                         self.voice.add(f"Scanning sector {event.symbol}... {event.size_class} detected.", "cyan")
                        
        except Exception:
            pass

    def run(self, snapshot=False):
        if snapshot:
            self.update_state()
            self.console.print(self.make_layout())
            # Print state manually if layout doesn't render populate
            self.layout["header"].update(self.get_header_panel())
            self.layout["radar"].update(self.get_radar_panel())
            self.layout["scanner"].update(self.get_scanner_panel())
            self.layout["map"].update(self.get_map_panel())
            self.layout["voice"].update(self.get_voice_panel())
            self.layout["footer"].update(self.get_stats_panel())
            self.console.print(self.layout)
            return

        with Live(self.make_layout(), refresh_per_second=4, screen=True) as live:
            while True:
                self.update_state()
                
                # Update layout components
                self.layout["header"].update(self.get_header_panel())
                self.layout["radar"].update(self.get_radar_panel())
                self.layout["scanner"].update(self.get_scanner_panel())
                self.layout["map"].update(self.get_map_panel())
                self.layout["voice"].update(self.get_voice_panel())
                self.layout["footer"].update(self.get_stats_panel())
                
                time.sleep(0.25)

if __name__ == "__main__":
    dashboard = QueenDashboard()
    if not RICH_AVAILABLE:
        print("Rich library required.")
    else:
        try:
            if "--snapshot" in sys.argv:
                dashboard.run(snapshot=True)
            else:
                dashboard.run()
        except KeyboardInterrupt:
            print("\n👑 Queen Command Center shutting down...")

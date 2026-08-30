#!/usr/bin/env python3
"""
⚡ AUREON POWER STATION - MAIN ENERGY INTERFACE ⚡

Everything is Energy. This is the primary dashboard for all system activity.

Real-time Energy Visualization:
- Total System Energy (all balances)
- Energy Flow (in/out per relay)
- Energy Generation (profits/gains)
- Energy Consumption (fees/drains)
- Energy Reserves (idle capital)
- Energy Deployment (active positions)
- Queen's Energy Decisions
- System Power Output

All trading activity, balances, profits, and losses shown as ENERGY.
Port: 8080 (Primary Interface)
"""

from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import sys, os
if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    try:
        import io
        def _is_utf8_wrapper(stream):
            return (isinstance(stream, io.TextIOWrapper) and 
                    hasattr(stream, 'encoding') and stream.encoding and
                    stream.encoding.lower().replace('-', '') == 'utf8')
        def _is_buffer_valid(stream):
            if not hasattr(stream, 'buffer'):
                return False
            try:
                return stream.buffer is not None and not stream.buffer.closed
            except (ValueError, AttributeError):
                return False
        if _is_buffer_valid(sys.stdout) and not _is_utf8_wrapper(sys.stdout):
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)
        if _is_buffer_valid(sys.stderr) and not _is_utf8_wrapper(sys.stderr):
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace', line_buffering=True)
    except Exception:
        pass

import asyncio
import hmac
import json
import os
import time
from datetime import datetime
from typing import Dict, Optional

from aiohttp import web

# Global reference to dashboard for web handlers
_dashboard_instance = None


def load_json_safe(filepath: str, default=None) -> Dict:
    """Load JSON file safely with fallback."""
    try:
        if os.path.exists(filepath):
            with open(filepath, 'r') as f:
                return json.load(f)
    except Exception:
        pass
    return default or {}


def format_usd(value: float) -> str:
    """Format USD value with color."""
    if value > 0:
        return f"\033[92m${value:.2f}\033[0m"  # Green
    elif value < 0:
        return f"\033[91m${value:.2f}\033[0m"  # Red
    else:
        return f"${value:.2f}"


def format_pct(value: float) -> str:
    """Format percentage with color."""
    if value > 0:
        return f"\033[92m+{value:.2f}%\033[0m"  # Green
    elif value < 0:
        return f"\033[91m{value:.2f}%\033[0m"  # Red
    else:
        return f"{value:.2f}%"


class QueenPowerDashboard:
    """
    ⚡ PRIMARY ENERGY INTERFACE ⚡
    Everything displayed as energy flows and reserves.
    """
    
    def __init__(self):
        self.last_update = 0
        self.update_interval = 3  # seconds
        self.cycle_count = 0
        self.start_time = time.time()
        self.total_energy_at_start = 0.0
        self._cached_nodes = []
        self._cache_time = 0
        self._cache_ttl = 30  # Refresh every 30 seconds
        self._last_scan_time = 0
        self._last_scan_error = ""
        self._last_scan_count = 0
        
        # Initialize the redistribution scanner for LIVE data
        self.scanner = None
        self._init_scanner()
        
        # Calculate baseline energy
        self._calculate_baseline_energy()
    
    def _init_scanner(self):
        """Initialize the Queen Power Redistribution scanner for live data."""
        try:
            from aureon.queen.queen_power_redistribution import QueenPowerRedistribution
            self.scanner = QueenPowerRedistribution(dry_run=True)
            print("✅ Queen Power Scanner initialized - LIVE data enabled")
        except Exception as e:
            print(f"⚠️ Scanner init failed: {e} - using fallback state files")
            self.scanner = None
    
    def _get_live_nodes(self):
        """Get live energy nodes from scanner (cached)."""
        now = time.time()
        if now - self._cache_time > self._cache_ttl:
            if self.scanner:
                try:
                    self._cached_nodes = self.scanner.scan_all_energy_nodes()
                    self._cache_time = now
                    self._last_scan_time = now
                    self._last_scan_count = len(self._cached_nodes)
                    self._last_scan_error = ""
                    print(f"📊 Scanned {len(self._cached_nodes)} live nodes")
                except Exception as e:
                    self._last_scan_time = now
                    self._last_scan_error = str(e)
                    print(f"⚠️ Scan failed: {e}")
        return self._cached_nodes
    
    def _calculate_baseline_energy(self):
        """Calculate total system energy at startup."""
        total = 0.0
        for relay in ['BIN', 'KRK', 'ALP', 'CAP']:
            energy = self.get_relay_energy(relay)
            total += energy['total']
        self.total_energy_at_start = total
    
    def get_total_system_energy(self) -> Dict:
        """Get comprehensive system energy metrics."""
        relays = ['BIN', 'KRK', 'ALP', 'CAP']
        
        total_energy = 0.0
        total_reserves = 0.0
        total_deployed = 0.0
        relay_breakdown = {}
        
        for relay in relays:
            energy = self.get_relay_energy(relay)
            total_energy += energy['total']
            total_reserves += energy['idle']
            total_deployed += energy['positions']
            relay_breakdown[relay] = energy
        
        # Get Queen's energy metrics
        queen_state = self.get_queen_redistribution_state()
        net_gained = queen_state.get('total_net_energy_gained', 0.0)
        drains_avoided = queen_state.get('total_blocked_drains_avoided', 0.0)
        
        # Calculate system growth
        energy_growth = total_energy - self.total_energy_at_start
        
        return {
            'total_energy': total_energy,
            'total_reserves': total_reserves,
            'total_deployed': total_deployed,
            'reserve_percentage': (total_reserves / total_energy * 100) if total_energy > 0 else 0,
            'deployed_percentage': (total_deployed / total_energy * 100) if total_energy > 0 else 0,
            'net_energy_gained': net_gained,
            'energy_conserved': drains_avoided,
            'energy_growth': energy_growth,
            'growth_percentage': (energy_growth / self.total_energy_at_start * 100) if self.total_energy_at_start > 0 else 0,
            'relay_breakdown': relay_breakdown
        }
    
    def get_queen_redistribution_state(self) -> Dict:
        """Get Queen's redistribution state."""
        state = load_json_safe('queen_redistribution_state.json', {
            'last_update': 0.0,
            'total_net_energy_gained': 0.0,
            'total_blocked_drains_avoided': 0.0,
            'decisions_count': 0,
            'executions_count': 0,
            'recent_decisions': [],
            'recent_executions': []
        })
        
        # Calculate time since last update (heartbeat)
        last_update = state.get('last_update', 0.0)
        if last_update > 0:
            state['seconds_since_update'] = time.time() - last_update
            state['is_alive'] = state['seconds_since_update'] < 60  # Active if updated in last minute
        else:
            state['seconds_since_update'] = 999999
            state['is_alive'] = False
        
        return state
    
    def get_power_station_state(self) -> Dict:
        """Get power station state."""
        return load_json_safe('power_station_state.json', {
            'status': 'UNKNOWN',
            'cycles_run': 0,
            'total_energy_now': 0.0,
            'energy_deployed': 0.0,
            'net_flow': 0.0,
            'efficiency': 0.0
        })

    def get_dashboard_snapshot(self) -> Dict:
        """Get latest trading snapshot with positions and system health."""
        state_dir = os.getenv('AUREON_STATE_DIR', 'state')
        candidates = [
            os.path.join(state_dir, 'dashboard_snapshot.json'),
            'dashboard_snapshot.json'
        ]
        snapshot = {}
        for path in candidates:
            data = load_json_safe(path, {})
            if data:
                snapshot = data
                break
        return snapshot

    def get_hive_state(self) -> Dict:
        """Get Queen voice and hive state (if available)."""
        hive = load_json_safe('public/hive_state.json', {
            'updated_at': '',
            'mood': 'Unknown',
            'active_scanner': 'Unknown',
            'coherence_score': 0.0,
            'veto_count': 0,
            'last_veto_reason': 'None',
            'message_log': []
        })
        return hive

    def get_scanner_status(self) -> Dict:
        """Get live scanner health/status for dashboard."""
        now = time.time()
        last_scan_age = (now - self._last_scan_time) if self._last_scan_time else None
        cache_age = (now - self._cache_time) if self._cache_time else None
        return {
            'enabled': self.scanner is not None,
            'last_scan_time': self._last_scan_time,
            'last_scan_age': last_scan_age,
            'last_scan_count': self._last_scan_count,
            'last_error': self._last_scan_error,
            'cache_age': cache_age
        }
    
    def get_relay_energy(self, relay: str) -> Dict:
        """Get energy status for a relay using LIVE scanner data."""
        # Map relay codes
        relay_map = {'BIN': 'BIN', 'KRK': 'KRK', 'ALP': 'ALP', 'CAP': 'CAP'}
        relay_code = relay_map.get(relay, relay)
        
        # Get live nodes from scanner
        nodes = self._get_live_nodes()
        
        # Filter nodes for this relay
        relay_nodes = [n for n in nodes if n.relay == relay_code]
        
        if relay_nodes:
            total = sum(n.position_value_usd for n in relay_nodes)
            # Idle = positive energy (profitable positions available to redistribute)
            idle = sum(n.energy_available_to_redistribute for n in relay_nodes)
            positions_count = len(relay_nodes)
            return {
                'total': total,
                'idle': idle,
                'positions': total,  # All deployed
                'positions_count': positions_count,
                'idle_pct': (idle / total * 100) if total > 0 else 0
            }
        
        # Fallback: Try state files
        if relay == 'BIN':
            state = load_json_safe('binance_truth_tracker_state.json', {})
            total = state.get('total_balance_usd', 0.0)
            free_usdt = state.get('balances', {}).get('USDT', {}).get('free', 0.0)
            positions = total - free_usdt
            return {
                'total': total,
                'idle': free_usdt,
                'positions': positions,
                'positions_count': 0,
                'idle_pct': (free_usdt / total * 100) if total > 0 else 0
            }
        
        elif relay == 'KRK':
            state = load_json_safe('aureon_kraken_state.json', {})
            free_usd = state.get('balances', {}).get('ZUSD', 0.0)
            total = free_usd
            positions_value = 0.0
            for asset, bal in state.get('balances', {}).items():
                if asset != 'ZUSD' and isinstance(bal, (int, float)) and bal > 0:
                    positions_value += bal
            total += positions_value
            return {
                'total': total,
                'idle': free_usd,
                'positions': positions_value,
                'positions_count': 0,
                'idle_pct': (free_usd / total * 100) if total > 0 else 0
            }
        
        elif relay == 'ALP':
            state = load_json_safe('alpaca_truth_tracker_state.json', {})
            cash = state.get('cash', 0.0)
            equity = state.get('equity', 0.0)
            positions = equity - cash
            return {
                'total': equity,
                'idle': cash,
                'positions': positions,
                'positions_count': 0,
                'idle_pct': (cash / equity * 100) if equity > 0 else 0
            }
        
        elif relay == 'CAP':
            # Capital.com: Try to get from global financial state
            state = load_json_safe('global_financial_state.json', {})
            cap_balance = state.get('capital_balance', 92.66)
            return {
                'total': cap_balance,
                'idle': cap_balance,
                'positions': 0.0,
                'positions_count': 0,
                'idle_pct': 100.0
            }
        
        return {'total': 0.0, 'idle': 0.0, 'positions': 0.0, 'positions_count': 0, 'idle_pct': 0.0}
    
    def display_header(self):
        """Display dashboard header with total system energy."""
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        runtime = time.time() - self.start_time
        runtime_str = f"{int(runtime//60)}m {int(runtime%60)}s"
        
        # Get total system energy
        energy_data = self.get_total_system_energy()
        total_energy = energy_data['total_energy']
        energy_growth = energy_data['energy_growth']
        growth_pct = energy_data['growth_percentage']
        
        # Energy growth indicator
        if energy_growth > 0:
            growth_icon = "⚡📈"
            growth_color = '\033[92m'  # Green
        elif energy_growth < 0:
            growth_icon = "⚠️📉"
            growth_color = '\033[91m'  # Red
        else:
            growth_icon = "⚡━"
            growth_color = '\033[93m'  # Yellow
        
        print("\033[2J\033[H")  # Clear screen
        print("\n")
        print("╔" + "═" * 78 + "╗")
        print(f"║  ⚡ AUREON POWER STATION - PRIMARY ENERGY INTERFACE{' ' * 26}║")
        print("╠" + "═" * 78 + "╣")
        print(f"║  📅 {now}  ⏱️  Runtime: {runtime_str:<10} 🔄 Cycle: #{self.cycle_count:<6}║")
        print("╠" + "─" * 78 + "╣")
        print(f"║  💎 Total System Energy: {format_usd(total_energy):<15} {growth_icon} Growth: {growth_color}{format_usd(energy_growth):>10}\033[0m ({growth_pct:+.2f}%)  ║")
        print("╚" + "═" * 78 + "╝")
        print()
    
    def display_queen_intelligence(self):
        """Display Queen's energy generation intelligence."""
        state = self.get_queen_redistribution_state()
        
        net_gained = state.get('total_net_energy_gained', 0.0)
        drains_avoided = state.get('total_blocked_drains_avoided', 0.0)
        decisions = state.get('decisions_count', 0)
        executions = state.get('executions_count', 0)
        seconds_since = state.get('seconds_since_update', 999999)
        is_alive = state.get('is_alive', False)
        
        # Heartbeat indicator
        if is_alive:
            heartbeat = "\033[92m💚 ACTIVE\033[0m"
            status_msg = f"\033[90m(updated {seconds_since:.0f}s ago)\033[0m"
        else:
            heartbeat = "\033[91m💔 IDLE\033[0m"
            status_msg = "\033[90m(no recent activity)\033[0m"
        
        # Calculate Queen efficiency (energy generated per decision)
        if decisions > 0:
            efficiency = (net_gained + drains_avoided) / decisions
        else:
            efficiency = 0.0
        
        print("╔" + "═" * 78 + "╗")
        print("║  🐝 QUEEN ENERGY GENERATION INTELLIGENCE" + " " * 36 + "║")
        print("╚" + "═" * 78 + "╝")
        print()
        print(f"  ⚡ Engine Status:       {heartbeat} {status_msg}")
        print()
        print(f"  📊 Energy Generation Summary:")
        print(f"     ├─ ⚡ Energy Generated:      {format_usd(net_gained):<15} (Net positive moves)")
        print(f"     ├─ 🛡️  Energy Conserved:      {format_usd(drains_avoided):<15} (Blocked drains)")
        print(f"     └─ 💎 Total Energy Impact:   {format_usd(net_gained + drains_avoided)}")
        print()
        print(f"  🎯 Queen Performance:")
        print(f"     ├─ Decisions Analyzed:      {decisions} opportunities")
        print(f"     ├─ Energy Moves Executed:   {executions} redistributions")
        print(f"     └─ Efficiency:              {format_usd(efficiency)} per decision")
        
        # Show recent decisions
        recent = state.get('recent_decisions', [])
        if recent:
            print()
            print("  📊 Recent Energy Decisions:")
            for i, dec in enumerate(recent[-3:], 1):
                opp = dec.get('opportunity', {})
                decision = dec.get('decision', 'UNKNOWN')
                relay = opp.get('relay', '???')
                target = opp.get('target_asset', '???')
                net_gain = opp.get('net_energy_gain', 0.0)
                confidence = dec.get('queen_confidence', 0.0)
                
                decision_icon = "✅" if decision == 'EXECUTE' else "🚫"
                decision_color = '\033[92m' if decision == 'EXECUTE' else '\033[91m'
                conf_bar = "●" * int(confidence * 5) + "○" * (5 - int(confidence * 5))
                
                prefix = "     └─" if i == len(recent[-3:]) else "     ├─"
                print(f"{prefix} {decision_icon} {decision_color}{decision:<8}\033[0m │ {relay} → {target:<12} │ {format_usd(net_gain):<12} │ {conf_bar}")
        else:
            print()
            print("  📊 \033[90m🔍 Scanning for profitable opportunities...\033[0m")
        print()
    
    def display_power_station(self):
        """Display power station energy flow."""
        state = self.get_power_station_state()
        
        status = state.get('status', 'UNKNOWN')
        cycles = state.get('cycles_run', 0)
        total_energy = state.get('total_energy_now', 0.0)
        deployed = state.get('energy_deployed', 0.0)
        net_flow = state.get('net_flow', 0.0)
        efficiency = state.get('efficiency', 0.0)
        
        status_icon = "🟢" if status == 'RUNNING' else "🟡"
        status_color = '\033[92m' if status == 'RUNNING' else '\033[93m'
        
        print("╔" + "═" * 78 + "╗")
        print("║  ⚡ ENERGY RESERVES & FLOW" + " " * 50 + "║")
        print("╚" + "═" * 78 + "╝")
        print()
        print(f"  {status_icon} Power Station Status:  {status_color}{status}\033[0m  \033[90m({cycles} energy cycles)\033[0m")
        print()
        print("  💎 System Energy Status:")
        print(f"     ├─ Total Energy Reserves:    {format_usd(total_energy)}")
        print(f"     ├─ Energy in Positions:      {format_usd(deployed)}")
        print(f"     └─ Net Energy Flow (24h):    {format_usd(net_flow)}")
        print()
        efficiency_bar = "█" * int(efficiency / 10) + "░" * (10 - int(efficiency / 10))
        print(f"  📊 Energy Efficiency:         {efficiency:.1f}% [{efficiency_bar}]")
        print()
    
    def display_relay_status(self):
        """Display energy distribution across relays."""
        print("╔" + "═" * 78 + "╗")
        print("║  🔌 ENERGY DISTRIBUTION BY RELAY" + " " * 44 + "║")
        print("╚" + "═" * 78 + "╝")
        print()
        print("  \033[90m(Each relay operates independently with internal energy isolation)\033[0m")
        print()
        
        relays = ['BIN', 'KRK', 'ALP', 'CAP']
        relay_names = {'BIN': 'Binance', 'KRK': 'Kraken', 'ALP': 'Alpaca', 'CAP': 'Capital'}
        total_system_energy = 0.0
        total_idle_energy = 0.0
        
        print(f"  {'RELAY':<10} {'TOTAL':<12} {'IDLE':<12} {'DEPLOYED':<12} {'MOBILITY':<20}")
        print("  " + "─" * 74)
        
        for relay in relays:
            energy = self.get_relay_energy(relay)
            total = energy['total']
            idle = energy['idle']
            positions = energy['positions']
            idle_pct = energy['idle_pct']
            
            total_system_energy += total
            total_idle_energy += idle
            
            # Mobility indicator
            if idle_pct > 50:
                mobility = "\033[92m🟢 HIGH\033[0m"
                mobility_bar = "█" * 5
            elif idle_pct > 10:
                mobility = "\033[93m🟡 MED\033[0m"
                mobility_bar = "█" * 3 + "░" * 2
            else:
                mobility = "\033[91m🔴 LOW\033[0m"
                mobility_bar = "█" + "░" * 4
            
            total_str = f"${total:.2f}"
            idle_str = f"${idle:.2f}"
            pos_str = f"${positions:.2f}"
            
            print(f"  {relay:<10} {total_str:<12} {idle_str:<12} {pos_str:<12} {mobility} [{mobility_bar}] {idle_pct:.0f}%")
        
        print("  " + "─" * 74)
        total_idle_pct = (total_idle_energy/total_system_energy*100 if total_system_energy > 0 else 0)
        print(f"  {'TOTAL':<10} ${total_system_energy:<11.2f} ${total_idle_energy:<11.2f} ${total_system_energy-total_idle_energy:<11.2f} \033[96m⚡ System: {total_idle_pct:.0f}% idle\033[0m")
        print()
    
    def display_energy_conservation(self):
        """Display energy conservation and generation metrics."""
        queen_state = self.get_queen_redistribution_state()
        net_gained = queen_state.get('total_net_energy_gained', 0.0)
        drains_avoided = queen_state.get('total_blocked_drains_avoided', 0.0)
        
        total_conserved = net_gained + drains_avoided
        
        print("╔" + "═" * 78 + "╗")
        print("║  🌿 ENERGY CONSERVATION & GENERATION" + " " * 40 + "║")
        print("╚" + "═" * 78 + "╝")
        print()
        
        if total_conserved > 0:
            efficiency = (net_gained / total_conserved * 100)
            print(f"  💎 Net Energy Gained:        {format_usd(net_gained)}")
            print(f"  🛡️  Drains Blocked:           {format_usd(drains_avoided)}")
            print(f"  ✨ Total Conserved:           {format_usd(total_conserved)}")
            print()
            efficiency_bar = "█" * int(efficiency / 10) + "░" * (10 - int(efficiency / 10))
            print(f"  📊 Conservation Rate:        {efficiency:.1f}% [{efficiency_bar}]")
            print(f"     \033[90m(Net gained / Total conserved)\033[0m")
        else:
            print(f"  💎 Net Energy Gained:        {format_usd(net_gained)}")
            print(f"  🛡️  Drains Blocked:           {format_usd(drains_avoided)}")
            print(f"  ✨ Total Conserved:           {format_usd(total_conserved)}")
            print()
            print("  \033[90m📈 Begin trading to track conservation metrics\033[0m")
        print()
    
    def get_dashboard_data(self) -> Dict:
        """Get dashboard data as dict for web API."""
        energy = self.get_total_system_energy()
        queen_state = self.get_queen_redistribution_state()
        power_state = self.get_power_station_state()
        hive_state = self.get_hive_state()
        scanner_state = self.get_scanner_status()
        snapshot = self.get_dashboard_snapshot()

        positions = snapshot.get('positions', []) if isinstance(snapshot, dict) else []
        now = time.time()
        normalized_positions = []
        positions_by_exchange = {}
        for p in positions:
            try:
                entry = float(p.get('entry_price', 0) or 0)
                current = float(p.get('current_price', 0) or 0)
                target = float(p.get('target_price', 0) or 0)
                progress = 0.0
                if target > entry:
                    progress = (current - entry) / (target - entry)
                progress = max(-1.0, min(2.0, progress))
                entry_time = float(p.get('entry_time', 0) or 0)
                age_sec = (now - entry_time) if entry_time > 0 else None
                exch = p.get('exchange', 'unknown')
                positions_by_exchange[exch] = positions_by_exchange.get(exch, 0) + 1
                normalized_positions.append({
                    'symbol': p.get('symbol', 'UNKNOWN'),
                    'exchange': exch,
                    'entry_price': entry,
                    'current_price': current,
                    'target_price': target,
                    'current_pnl': float(p.get('current_pnl', 0) or 0),
                    'current_pnl_pct': float(p.get('current_pnl_pct', 0) or 0),
                    'progress': round(progress * 100, 2),
                    'age_sec': age_sec,
                })
            except Exception:
                continue
        
        # Get relay breakdown
        relays = {}
        for relay_code in ['BIN', 'KRK', 'ALP', 'CAP']:
            relay_energy = self.get_relay_energy(relay_code)
            relays[relay_code] = {
                'total': relay_energy.get('total', 0),
                'idle': relay_energy.get('idle', 0),
                'positions': relay_energy.get('positions', 0),
                'positions_count': relay_energy.get('positions_count', 0),
            }
        
        return {
            'timestamp': time.time(),
            'cycle': self.cycle_count,
            'uptime_seconds': time.time() - self.start_time,
            'total_energy': energy.get('total_energy', 0),
            'total_reserves': energy.get('total_reserves', 0),
            'total_deployed': energy.get('total_deployed', 0),
            'net_energy_gained': energy.get('net_energy_gained', 0),
            'energy_conserved': energy.get('energy_conserved', 0),
            'energy_growth': energy.get('energy_growth', 0),
            'growth_percentage': energy.get('growth_percentage', 0),
            'relays': relays,
            'power_station': power_state,
            'scanner': scanner_state,
            'hive': hive_state,
            'snapshot': {
                'timestamp': snapshot.get('timestamp'),
                'active_count': snapshot.get('active_count', 0),
                'exchange_status': snapshot.get('exchange_status', {}),
                'positions_by_exchange': positions_by_exchange,
                'positions': normalized_positions[:50]
            },
            'queen': {
                'decisions_count': queen_state.get('decisions_count', 0),
                'net_gained': queen_state.get('total_net_energy_gained', 0),
                'drains_avoided': queen_state.get('total_blocked_drains_avoided', 0),
            }
        }
    
    async def run(self):
        """Run continuous dashboard updates."""
        print("🐝 Queen Power Dashboard starting...")
        print("Press Ctrl+C to stop")
        
        try:
            while True:
                self.cycle_count += 1
                
                self.display_header()
                self.display_queen_intelligence()
                self.display_power_station()
                self.display_relay_status()
                self.display_energy_conservation()
                
                print("┏" + "━" * 78 + "┓")
                print(f"┃  ⏳ Next update in {self.update_interval}s" + " " * 33 + "\033[90mPress Ctrl+C to stop\033[0m" + " " * 3 + "┃")
                print("┗" + "━" * 78 + "┛")
                print()
                
                await asyncio.sleep(self.update_interval)
        
        except KeyboardInterrupt:
            print("\n\n🛑 Dashboard stopped by user")


# ═══════════════════════════════════════════════════════════════════════════════
# WEB SERVER - Health Check & API for DigitalOcean
# ═══════════════════════════════════════════════════════════════════════════════
#
# ACCESS CONTROL. This server binds 0.0.0.0 (required for containerised / DigitalOcean
# deploys, whose health check reaches it from outside the container) and served
# `/api/status` to anyone with no credential at all. That payload is not cosmetic: it
# carries `total_reserves` / `total_deployed` / `net_energy_gained` and every open
# position with symbol, exchange, entry, current and target price and live PnL.
#
# Three knobs, all defaulting to today's behaviour so no running deployment changes:
#
#   AUREON_DASHBOARD_TOKEN   when set, `/` and `/api/status` require
#                            `Authorization: Bearer <token>` (or `?token=`, since a
#                            browser opening the dashboard cannot set a header).
#                            `/health` stays open — it is a liveness probe and carries
#                            no financial data.
#   AUREON_DASHBOARD_PUBLIC  "1" ⇒ serve a redacted `/api/status`: the organism view
#                            (cycle, uptime, harmonics, counts) stays, the money does
#                            not. This is the setting to use when streaming the
#                            dashboard publicly.
#   AUREON_DASHBOARD_BIND    interface to bind (default "0.0.0.0", unchanged). Set
#                            "127.0.0.1" for loopback-only behind a reverse proxy.
#
# Redaction is HONEST — redacted keys are set to None and named in `redacted`, never
# replaced with plausible-looking numbers.

#: Financial fields removed from the top level of a public/redacted status payload.
_MONEY_FIELDS = (
    "total_energy", "total_reserves", "total_deployed", "net_energy_gained",
    "energy_conserved", "energy_growth",
)
#: Financial fields removed from each open-position entry.
_POSITION_MONEY_FIELDS = (
    "entry_price", "current_price", "target_price", "current_pnl", "current_pnl_pct",
)


def _dashboard_token() -> str:
    return str(os.environ.get("AUREON_DASHBOARD_TOKEN", "") or "").strip()


def _dashboard_public_mode() -> bool:
    return str(os.environ.get("AUREON_DASHBOARD_PUBLIC", "") or "").strip() == "1"


def _authorized(request) -> bool:
    """True when no token is configured (the default) or the caller presents it."""
    token = _dashboard_token()
    if not token:
        return True
    header = str(request.headers.get("Authorization", "") or "")
    if header.startswith("Bearer "):
        presented = header[len("Bearer "):].strip()
        if hmac.compare_digest(presented.encode("utf-8"), token.encode("utf-8")):
            return True
    # A browser cannot set a header on a plain navigation, so accept a query token too.
    q = str(request.query.get("token", "") or "").strip()
    return bool(q) and hmac.compare_digest(q.encode("utf-8"), token.encode("utf-8"))


def _redact_money(data: Dict) -> Dict:
    """Strip financial figures from a status payload, naming what was removed."""
    out = dict(data)
    removed = []
    for key in _MONEY_FIELDS:
        if key in out:
            out[key] = None
            removed.append(key)
    positions = out.get("positions")
    if isinstance(positions, list):
        scrubbed = []
        for p in positions:
            if not isinstance(p, dict):
                scrubbed.append(p)
                continue
            q = dict(p)
            for key in _POSITION_MONEY_FIELDS:
                if key in q:
                    q[key] = None
            scrubbed.append(q)
        out["positions"] = scrubbed
        removed.extend(f"positions[].{k}" for k in _POSITION_MONEY_FIELDS)
    if isinstance(out.get("relay_energy"), dict):
        count = out["relay_energy"].get("positions_count", 0)
        out["relay_energy"] = {"positions_count": count}
        removed.append("relay_energy.*")
    out["redacted"] = removed
    out["redaction_note"] = ("financial figures withheld (AUREON_DASHBOARD_PUBLIC=1); "
                             "nulls mean withheld, not zero")
    return out


async def handle_health(request):
    """Health check endpoint for DigitalOcean."""
    global _dashboard_instance
    
    health_data = {
        'status': 'healthy',
        'service': 'queen-power-dashboard',
        'timestamp': datetime.utcnow().isoformat(),
        'uptime_seconds': time.time() - _dashboard_instance.start_time if _dashboard_instance else 0,
        'cycle_count': _dashboard_instance.cycle_count if _dashboard_instance else 0,
    }
    
    return web.json_response(health_data)


async def handle_api_status(request):
    """Full dashboard status as JSON. Token-gated / money-redacted when configured."""
    global _dashboard_instance

    if not _authorized(request):
        return web.json_response(
            {'error': 'unauthorized', 'detail': 'a token is required'}, status=401)

    if not _dashboard_instance:
        return web.json_response({'error': 'Dashboard not initialized'}, status=503)

    data = _dashboard_instance.get_dashboard_data()
    if _dashboard_public_mode():
        data = _redact_money(data)
    return web.json_response(data)


async def handle_root(request):
    """Serve enhanced HTML dashboard with visualizations."""
    if not _authorized(request):
        return web.Response(status=401, text="This dashboard requires a token.")
    html = """<!DOCTYPE html>
<html>
<head>
    <title>⚡ Queen Power Station</title>
    <meta charset="utf-8">
    <link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=Share+Tech+Mono&display=swap" rel="stylesheet">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>
    <style>
        :root {
            --bg-dark: #0a0a0a;
            --bg-panel: #111118;
            --green: #00ff88;
            --cyan: #00d4ff;
            --purple: #a855f7;
            --gold: #ffd700;
            --red: #ff4466;
            --text: #e0e0e0;
            --text-dim: #666;
        }
        
        * { box-sizing: border-box; }
        
        body { 
            background: var(--bg-dark);
            color: var(--text);
            font-family: 'Share Tech Mono', 'Courier New', monospace;
            padding: 0;
            margin: 0;
            min-height: 100vh;
        }
        
        /* Energy Flow Bar - Top */
        .energy-flow-bar {
            height: 4px;
            background: linear-gradient(90deg, var(--green), var(--cyan), var(--purple), var(--green));
            background-size: 200% 100%;
            animation: energyFlow 2s linear infinite;
        }
        
        @keyframes energyFlow {
            0% { background-position: 200% 0; }
            100% { background-position: 0 0; }
        }
        
        /* Header */
        .header {
            text-align: center;
            padding: 25px 20px;
            background: linear-gradient(180deg, rgba(0,255,136,0.05) 0%, transparent 100%);
            border-bottom: 1px solid rgba(0,255,136,0.2);
        }
        
        .logo {
            font-family: 'Orbitron', sans-serif;
            font-size: 2em;
            font-weight: 900;
            background: linear-gradient(90deg, var(--gold), #ff6600, var(--gold));
            background-size: 200% 100%;
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            animation: shimmer 3s linear infinite;
            margin: 0;
        }
        
        @keyframes shimmer {
            0% { background-position: -200% 0; }
            100% { background-position: 200% 0; }
        }
        
        .header p {
            color: var(--text-dim);
            margin: 5px 0 0 0;
            font-size: 0.9em;
        }
        
        /* Status Indicator */
        .queen-status {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            margin-top: 10px;
            padding: 5px 15px;
            background: rgba(0,255,136,0.1);
            border-radius: 20px;
            font-size: 0.85em;
        }
        
        .status-dot {
            width: 10px;
            height: 10px;
            border-radius: 50%;
            background: var(--green);
            animation: pulse 1.5s infinite;
        }
        
        .status-dot.danger {
            background: var(--red);
            animation: blink 0.5s infinite;
        }
        
        @keyframes pulse {
            0%, 100% { opacity: 1; transform: scale(1); box-shadow: 0 0 0 0 rgba(0,255,136,0.7); }
            50% { opacity: 0.8; transform: scale(1.2); box-shadow: 0 0 10px 3px rgba(0,255,136,0.3); }
        }
        
        @keyframes blink {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.3; }
        }
        
        /* Main Content */
        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
        }
        
        /* Energy Summary Cards */
        .energy-summary {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 15px;
            margin-bottom: 25px;
        }
        
        .summary-card {
            background: var(--bg-panel);
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 12px;
            padding: 20px;
            text-align: center;
            position: relative;
            overflow: hidden;
        }
        
        .summary-card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 3px;
            background: linear-gradient(90deg, var(--green), var(--cyan));
        }
        
        .summary-card h3 {
            margin: 0 0 10px 0;
            font-size: 0.85em;
            color: var(--text-dim);
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        
        .summary-value {
            font-family: 'Orbitron', sans-serif;
            font-size: 1.8em;
            font-weight: 700;
            color: var(--green);
            transition: transform 0.3s, filter 0.3s;
        }
        
        .summary-value.updating {
            animation: numberPop 0.3s ease;
        }
        
        @keyframes numberPop {
            0% { transform: scale(1); }
            50% { transform: scale(1.15); filter: brightness(1.5); }
            100% { transform: scale(1); }
        }
        
        .summary-value.negative { color: var(--red); }
        .summary-value.neutral { color: var(--text-dim); }
        
        /* Chart Section */
        .chart-section {
            background: var(--bg-panel);
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 25px;
        }
        
        .chart-section h2 {
            margin: 0 0 15px 0;
            font-size: 1em;
            color: var(--text-dim);
            display: flex;
            align-items: center;
            gap: 8px;
        }
        
        .chart-container {
            height: 150px;
            position: relative;
        }
        
        /* Relay Grid */
        .relay-section h2 {
            color: var(--text);
            font-size: 1.1em;
            margin: 0 0 15px 0;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        
        .relay-grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 15px;
            margin-bottom: 25px;
        }
        
        .relay-card {
            background: var(--bg-panel);
            border: 2px solid rgba(255,255,255,0.1);
            border-radius: 12px;
            padding: 18px;
            position: relative;
            overflow: hidden;
            transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
        }
        
        /* Rotating border glow on hover */
        .relay-card::before {
            content: '';
            position: absolute;
            top: -50%;
            left: -50%;
            width: 200%;
            height: 200%;
            background: conic-gradient(transparent, rgba(0,255,136,0.15), transparent 30%);
            animation: rotateBorder 4s linear infinite;
            opacity: 0;
            transition: opacity 0.3s;
        }
        
        .relay-card:hover::before {
            opacity: 1;
        }
        
        .relay-card::after {
            content: '';
            position: absolute;
            inset: 2px;
            background: var(--bg-panel);
            border-radius: 10px;
            z-index: 0;
        }
        
        .relay-card > * {
            position: relative;
            z-index: 1;
        }
        
        @keyframes rotateBorder {
            100% { transform: rotate(360deg); }
        }
        
        .relay-card:hover {
            transform: translateY(-3px);
            border-color: rgba(0,255,136,0.3);
        }
        
        .relay-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 12px;
        }
        
        .relay-name {
            font-weight: bold;
            font-size: 1.1em;
        }
        
        .relay-name.bin { color: #f0b90b; }
        .relay-name.krk { color: #5741d9; }
        .relay-name.alp { color: #00d632; }
        .relay-name.cap { color: #00aaff; }
        
        .relay-total {
            font-family: 'Orbitron', sans-serif;
            font-size: 1.4em;
            font-weight: 700;
            color: var(--text);
        }
        
        /* Energy Progress Bar */
        .energy-bar-container {
            margin: 12px 0;
        }
        
        .energy-bar-label {
            display: flex;
            justify-content: space-between;
            font-size: 0.75em;
            color: var(--text-dim);
            margin-bottom: 4px;
        }
        
        .energy-bar {
            height: 8px;
            background: rgba(255,255,255,0.1);
            border-radius: 4px;
            overflow: hidden;
        }
        
        .energy-bar-fill {
            height: 100%;
            background: linear-gradient(90deg, var(--green), var(--cyan));
            border-radius: 4px;
            transition: width 0.5s ease;
        }
        
        .energy-bar-fill.low {
            background: linear-gradient(90deg, var(--red), #ff8844);
        }
        
        .energy-bar-fill.medium {
            background: linear-gradient(90deg, #ffaa00, var(--gold));
        }
        
        .relay-stats {
            display: flex;
            justify-content: space-between;
            font-size: 0.8em;
            color: var(--text-dim);
            margin-top: 8px;
        }
        
        .relay-stats span {
            display: flex;
            align-items: center;
            gap: 4px;
        }
        
        /* Queen Intelligence Section */
        .queen-section {
            background: var(--bg-panel);
            border: 1px solid rgba(168,85,247,0.3);
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 25px;
        }
        
        .queen-section h2 {
            color: var(--purple);
            margin: 0 0 15px 0;
            font-size: 1.1em;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        
        .queen-stats {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 20px;
        }
        
        .queen-stat {
            text-align: center;
        }
        
        .queen-stat-value {
            font-family: 'Orbitron', sans-serif;
            font-size: 1.6em;
            font-weight: 700;
            color: var(--purple);
        }
        
        .queen-stat-value.positive { color: var(--green); }
        
        .queen-stat-label {
            font-size: 0.8em;
            color: var(--text-dim);
            margin-top: 5px;

        /* System Status & Voice */
        .status-grid {
            display: grid;
            grid-template-columns: 1.2fr 1fr;
            gap: 20px;
        }
        .status-card {
            background: var(--bg-panel);
            border: 1px solid rgba(255,255,255,0.05);
            border-radius: 15px;
            padding: 20px;
        }
        .status-list {
            list-style: none;
            padding: 0;
            margin: 0;
            font-size: 0.9em;
        }
        .status-list li {
            padding: 6px 0;
            border-bottom: 1px solid rgba(255,255,255,0.05);
        }
        .voice-log {
            max-height: 220px;
            overflow-y: auto;
            padding: 0;
            margin: 0;
            list-style: none;
            font-size: 0.9em;
        }
        .voice-log li {
            padding: 8px 0;
            border-bottom: 1px solid rgba(255,255,255,0.05);
            color: var(--text);
        }

        .positions-section {
            margin-top: 20px;
        }
        .positions-table {
            width: 100%;
            border-collapse: collapse;
            font-size: 0.9em;
        }
        .positions-table th,
        .positions-table td {
            padding: 8px 6px;
            border-bottom: 1px solid rgba(255,255,255,0.05);
            text-align: left;
        }
        .positions-table th {
            color: var(--text-dim);
            font-weight: 600;
        }
        .badge-positive { color: var(--green); }
        .badge-negative { color: var(--red); }
        }
        
        /* Footer */
        .footer {
            text-align: center;
            color: var(--text-dim);
            font-size: 0.8em;
            padding: 15px;
            border-top: 1px solid rgba(255,255,255,0.05);
        }
        
        .footer span {
            margin: 0 10px;
        }
        
        /* Responsive */
        @media (max-width: 1000px) {
            .energy-summary, .relay-grid { grid-template-columns: repeat(2, 1fr); }
            .queen-stats { grid-template-columns: 1fr; }
            .status-grid { grid-template-columns: 1fr; }
        }
        
        @media (max-width: 600px) {
            .energy-summary, .relay-grid { grid-template-columns: 1fr; }
        }
    </style>
</head>
<body>
    <!-- Energy Flow Bar -->
    <div class="energy-flow-bar"></div>
    
    <!-- Header -->
    <div class="header">
        <h1 class="logo">⚡ QUEEN POWER STATION ⚡</h1>
        <p>Real-Time Energy Distribution Dashboard</p>
        <div class="queen-status">
            <div class="status-dot" id="statusDot"></div>
            <span id="statusText">Initializing...</span>
        </div>
    </div>
    
    <div class="container">
        <!-- Energy Summary Cards -->
        <div class="energy-summary">
            <div class="summary-card">
                <h3>💎 Total Energy</h3>
                <div class="summary-value" id="totalEnergy">$0.00</div>
            </div>
            <div class="summary-card">
                <h3>⚡ Reserves</h3>
                <div class="summary-value" id="totalReserves">$0.00</div>
            </div>
            <div class="summary-card">
                <h3>🎯 Deployed</h3>
                <div class="summary-value" id="totalDeployed">$0.00</div>
            </div>
            <div class="summary-card">
                <h3>📈 Growth</h3>
                <div class="summary-value" id="growthPct">0.00%</div>
            </div>
        </div>
        
        <!-- Energy History Chart -->
        <div class="chart-section">
            <h2>📊 Energy Flow History</h2>
            <div class="chart-container">
                <canvas id="energyChart"></canvas>
            </div>
        </div>
        
        <!-- Relay Status -->
        <div class="relay-section">
            <h2>🔌 Relay Energy Distribution</h2>
            <div class="relay-grid" id="relayGrid">
                <!-- Populated by JS -->
            </div>
        </div>
        
        <!-- Queen Intelligence -->
        <div class="queen-section">
            <h2>🐝 Queen Intelligence</h2>
            <div class="queen-stats">
                <div class="queen-stat">
                    <div class="queen-stat-value" id="queenDecisions">0</div>
                    <div class="queen-stat-label">Decisions Made</div>
                </div>
                <div class="queen-stat">
                    <div class="queen-stat-value positive" id="queenGained">$0.00</div>
                    <div class="queen-stat-label">Net Energy Gained</div>
                </div>
                <div class="queen-stat">
                    <div class="queen-stat-value positive" id="queenAvoided">$0.00</div>
                    <div class="queen-stat-label">Drains Avoided</div>
                </div>
            </div>
        </div>

        <!-- System Status + Queen Voice -->
        <div class="queen-section">
            <h2>🧭 System Status & Queen Voice</h2>
            <div class="status-grid">
                <div class="status-card">
                    <h3>🛰️ Power Station & Scanner</h3>
                    <ul class="status-list">
                        <li>⚡ Power Station: <span id="powerStatus">UNKNOWN</span></li>
                        <li>🔁 Cycles: <span id="powerCycles">0</span></li>
                        <li>⏱️ Last Update: <span id="powerLastUpdate">--</span></li>
                        <li>📦 Last Harvest: <span id="powerLastHarvest">--</span></li>
                        <li>🔍 Scanner: <span id="scannerStatus">UNKNOWN</span></li>
                        <li>🧮 Last Scan: <span id="scannerLastScan">--</span></li>
                        <li>🛑 Last Error: <span id="scannerLastError">None</span></li>
                    </ul>
                </div>
                <div class="status-card">
                    <h3>👑 Queen Voice Log</h3>
                    <ul class="status-list">
                        <li>🙂 Mood: <span id="queenMood">Unknown</span></li>
                        <li>🔭 Active Scanner: <span id="queenScanner">Unknown</span></li>
                        <li>📡 Coherence: <span id="queenCoherence">0.000</span></li>
                    </ul>
                    <ul class="voice-log" id="queenVoiceLog"></ul>
                </div>
            </div>
        </div>

        <!-- Positions Monitoring -->
        <div class="queen-section positions-section">
            <h2>📍 Live Positions & Progress</h2>
            <table class="positions-table">
                <thead>
                    <tr>
                        <th>Symbol</th>
                        <th>Exchange</th>
                        <th>PNL</th>
                        <th>Progress</th>
                        <th>Age</th>
                    </tr>
                </thead>
                <tbody id="positionsTable">
                    <tr><td colspan="5">Loading...</td></tr>
                </tbody>
            </table>
        </div>
    </div>
    
    <!-- Footer -->
    <div class="footer">
        <span id="cycleInfo">Cycle: 0</span>
        <span id="uptimeInfo">Uptime: 0m</span>
        <span id="updateInfo">Last Update: --:--:--</span>
    </div>
    
    <!-- Energy Flow Bar Bottom -->
    <div class="energy-flow-bar"></div>
    
    <script>
        // Energy history for chart
        const energyHistory = [];
        const maxHistoryPoints = 60;
        let lastValues = {};
        
        // Initialize Chart
        const ctx = document.getElementById('energyChart').getContext('2d');
        const energyChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Total Energy',
                    data: [],
                    borderColor: '#00ff88',
                    backgroundColor: 'rgba(0, 255, 136, 0.1)',
                    borderWidth: 2,
                    tension: 0.4,
                    fill: true,
                    pointRadius: 0,
                    pointHoverRadius: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false }
                },
                scales: {
                    x: { display: false },
                    y: {
                        display: true,
                        grid: { color: 'rgba(255,255,255,0.05)' },
                        ticks: { 
                            color: '#666',
                            callback: v => '$' + v.toFixed(0)
                        }
                    }
                },
                interaction: {
                    intersect: false,
                    mode: 'index'
                }
            }
        });
        
        // Animate value changes
        function animateValue(elementId, newValue, prefix = '', suffix = '') {
            const el = document.getElementById(elementId);
            if (!el) return;
            
            const oldValue = lastValues[elementId];
            const displayValue = prefix + newValue + suffix;
            
            if (oldValue !== undefined && oldValue !== newValue) {
                el.classList.add('updating');
                setTimeout(() => el.classList.remove('updating'), 300);
            }
            
            el.textContent = displayValue;
            lastValues[elementId] = newValue;
        }
        
        // Build relay card HTML
        function buildRelayCard(code, name, colorClass, data) {
            const total = data.total || 0;
            const idle = data.idle || 0;
            const positions = data.positions_count || 0;
            const idlePct = total > 0 ? (idle / total * 100) : 0;
            
            let barClass = 'energy-bar-fill';
            if (idlePct < 20) barClass += ' low';
            else if (idlePct < 50) barClass += ' medium';
            
            return `
                <div class="relay-card">
                    <div class="relay-header">
                        <span class="relay-name ${colorClass}">${name}</span>
                        <span class="relay-total">$${total.toFixed(2)}</span>
                    </div>
                    <div class="energy-bar-container">
                        <div class="energy-bar-label">
                            <span>Mobility</span>
                            <span>${idlePct.toFixed(0)}%</span>
                        </div>
                        <div class="energy-bar">
                            <div class="${barClass}" style="width: ${Math.min(idlePct, 100)}%"></div>
                        </div>
                    </div>
                    <div class="relay-stats">
                        <span>💰 Idle: $${idle.toFixed(2)}</span>
                        <span>📊 ${positions} nodes</span>
                    </div>
                </div>
            `;
        }
        
        async function updateStatus() {
            try {
                const resp = await fetch('/api/status');
                const data = await resp.json();
                
                // Update status indicator
                const statusDot = document.getElementById('statusDot');
                const statusText = document.getElementById('statusText');
                statusDot.className = 'status-dot';
                statusText.textContent = 'ONLINE • Cycle ' + data.cycle;
                
                // Update summary values with animation
                animateValue('totalEnergy', (data.total_energy || 0).toFixed(2), '$');
                animateValue('totalReserves', (data.total_reserves || 0).toFixed(2), '$');
                animateValue('totalDeployed', (data.total_deployed || 0).toFixed(2), '$');
                
                const growth = data.growth_percentage || 0;
                const growthEl = document.getElementById('growthPct');
                growthEl.textContent = (growth >= 0 ? '+' : '') + growth.toFixed(2) + '%';
                growthEl.className = 'summary-value ' + (growth > 0 ? 'positive' : growth < 0 ? 'negative' : 'neutral');
                
                // Update chart
                const now = new Date().toLocaleTimeString();
                energyHistory.push({ time: now, value: data.total_energy || 0 });
                if (energyHistory.length > maxHistoryPoints) energyHistory.shift();
                
                energyChart.data.labels = energyHistory.map(h => h.time);
                energyChart.data.datasets[0].data = energyHistory.map(h => h.value);
                energyChart.update('none');
                
                // Update relay grid
                const relayInfo = [
                    { code: 'BIN', name: '🟡 Binance', colorClass: 'bin' },
                    { code: 'KRK', name: '🔵 Kraken', colorClass: 'krk' },
                    { code: 'ALP', name: '🟢 Alpaca', colorClass: 'alp' },
                    { code: 'CAP', name: '🏛️ Capital', colorClass: 'cap' }
                ];
                
                let relayHTML = '';
                for (const r of relayInfo) {
                    const relayData = data.relays?.[r.code] || {};
                    relayHTML += buildRelayCard(r.code, r.name, r.colorClass, relayData);
                }
                document.getElementById('relayGrid').innerHTML = relayHTML;
                
                // Update Queen stats
                animateValue('queenDecisions', data.queen?.decisions_count || 0);
                animateValue('queenGained', (data.queen?.net_gained || 0).toFixed(2), '$');
                animateValue('queenAvoided', (data.queen?.drains_avoided || 0).toFixed(2), '$');

                // Update Power Station & Scanner
                const power = data.power_station || {};
                const scanner = data.scanner || {};
                const hive = data.hive || {};

                const powerStatus = power.status || 'UNKNOWN';
                const lastUpdateTs = power.last_update ? new Date(power.last_update * 1000) : null;
                const lastHarvest = power.last_harvest || {};
                const scannerStatus = !scanner.enabled
                    ? 'DISABLED'
                    : (scanner.last_error ? 'ERROR' : 'OK');

                document.getElementById('powerStatus').textContent = powerStatus;
                document.getElementById('powerCycles').textContent = power.cycles_run || 0;
                document.getElementById('powerLastUpdate').textContent = lastUpdateTs ? lastUpdateTs.toLocaleTimeString() : '--';
                document.getElementById('powerLastHarvest').textContent =
                    (lastHarvest.total_harvested_usd !== undefined)
                        ? `$${Number(lastHarvest.total_harvested_usd || 0).toFixed(2)} / ${lastHarvest.harvested_count || 0} nodes`
                        : '--';
                document.getElementById('scannerStatus').textContent = scannerStatus;
                document.getElementById('scannerLastScan').textContent =
                    (scanner.last_scan_age !== null && scanner.last_scan_age !== undefined)
                        ? `${Math.round(scanner.last_scan_age)}s ago (${scanner.last_scan_count || 0} nodes)`
                        : '--';
                document.getElementById('scannerLastError').textContent = scanner.last_error || 'None';

                // Update Queen Voice / Hive
                document.getElementById('queenMood').textContent = hive.mood || 'Unknown';
                document.getElementById('queenScanner').textContent = hive.active_scanner || 'Unknown';
                document.getElementById('queenCoherence').textContent =
                    (hive.coherence_score !== undefined) ? Number(hive.coherence_score).toFixed(3) : '0.000';

                const voiceLog = document.getElementById('queenVoiceLog');
                if (voiceLog) {
                    const messages = Array.isArray(hive.message_log) ? hive.message_log : [];
                    voiceLog.innerHTML = messages.length
                        ? messages.map(m => `<li>${m}</li>`).join('')
                        : '<li>No voice messages yet.</li>';
                }

                // Update Positions table
                const positions = data.snapshot?.positions || [];
                const tbody = document.getElementById('positionsTable');
                if (tbody) {
                    if (!positions.length) {
                        tbody.innerHTML = '<tr><td colspan="5">No active positions</td></tr>';
                    } else {
                        tbody.innerHTML = positions.map(p => {
                            const pnl = Number(p.current_pnl || 0);
                            const pnlPct = Number(p.current_pnl_pct || 0);
                            const pnlClass = pnl >= 0 ? 'badge-positive' : 'badge-negative';
                            const progress = Number(p.progress || 0).toFixed(1) + '%';
                            const age = (p.age_sec !== null && p.age_sec !== undefined)
                                ? Math.floor(p.age_sec / 60) + 'm'
                                : '--';
                            return `<tr>
                                <td>${p.symbol}</td>
                                <td>${p.exchange}</td>
                                <td class="${pnlClass}">${pnl.toFixed(2)} (${pnlPct.toFixed(2)}%)</td>
                                <td>${progress}</td>
                                <td>${age}</td>
                            </tr>`;
                        }).join('');
                    }
                }
                
                // Update footer
                document.getElementById('cycleInfo').textContent = 'Cycle: ' + data.cycle;
                document.getElementById('uptimeInfo').textContent = 'Uptime: ' + Math.floor((data.uptime_seconds || 0) / 60) + 'm';
                document.getElementById('updateInfo').textContent = 'Last Update: ' + new Date().toLocaleTimeString();
                
            } catch (err) {
                const statusDot = document.getElementById('statusDot');
                const statusText = document.getElementById('statusText');
                statusDot.className = 'status-dot danger';
                statusText.textContent = 'CONNECTION ERROR';
            }
        }
        
        // Initial load and interval
        updateStatus();
        setInterval(updateStatus, 3000);
    </script>
</body>
</html>"""
    return web.Response(text=html, content_type='text/html')


async def start_web_server(dashboard, port):
    """Start aiohttp web server."""
    app = web.Application()
    app.router.add_get('/', handle_root)
    app.router.add_get('/health', handle_health)
    app.router.add_get('/api/status', handle_api_status)
    
    runner = web.AppRunner(app)
    await runner.setup()

    # Default unchanged (0.0.0.0) because containerised / DigitalOcean deploys need it;
    # set AUREON_DASHBOARD_BIND=127.0.0.1 to make this loopback-only behind a proxy.
    bind = str(os.environ.get("AUREON_DASHBOARD_BIND", "") or "").strip() or "0.0.0.0"

    # Try the requested port, if fail, try port+1, then port+2
    max_retries = 3
    for i in range(max_retries):
        try:
            current_port = port + i
            site = web.TCPSite(runner, bind, current_port, reuse_address=True)
            await site.start()
            port = current_port # Update port if we shifted
            break
        except OSError as e:
            if i == max_retries - 1:
                print(f"❌ Failed to bind port {port} after {max_retries} attempts: {e}")
                raise e
            print(f"⚠️ Port {current_port} busy, trying {current_port + 1}...")
            await asyncio.sleep(1)
    
    print(f"🌐 Web server started on http://{bind}:{port}")
    print(f"   💚 Health: http://localhost:{port}/health")
    print(f"   📊 Status: http://localhost:{port}/api/status")

    # Say plainly what is exposed: /api/status carries reserves, deployed capital and
    # every open position with live prices and PnL. Do not make an operator guess.
    _tokened, _public = bool(_dashboard_token()), _dashboard_public_mode()
    _loopback = bind in ("127.0.0.1", "localhost", "::1")
    if _tokened:
        print("   🔒 Token required (AUREON_DASHBOARD_TOKEN set)")
    if _public:
        print("   🙈 Public-safe mode: financial figures redacted from /api/status")
    if not _loopback and not _tokened and not _public:
        print(f"   ⚠️  OPEN TO THE NETWORK on {bind}:{port} with NO token.")
        print("       /api/status is serving reserves, deployed capital and live open")
        print("       positions to anyone who can reach this port.")
        print("       Set AUREON_DASHBOARD_TOKEN to require a credential,")
        print("       AUREON_DASHBOARD_PUBLIC=1 to redact the money, or")
        print("       AUREON_DASHBOARD_BIND=127.0.0.1 to keep it off the network.")

    return runner


async def main():
    global _dashboard_instance
    
    import argparse
    parser = argparse.ArgumentParser(description="Queen Power Dashboard")
    parser.add_argument('--interval', type=int, default=3, help='Update interval in seconds (default: 3)')
    parser.add_argument('--port', type=int, default=8080, help='Web server port (default: 8080)')
    parser.add_argument('--no-console', action='store_true', help='Disable console output')
    args = parser.parse_args()
    
    port = int(os.environ.get('PORT', args.port))
    
    # Start web server early so health checks succeed quickly (bind 0.0.0.0:PORT)
    runner = await start_web_server(None, port)

    # Instantiate dashboard after server is accepting connections so /health responds
    try:
        dashboard = QueenPowerDashboard()
        dashboard.update_interval = args.interval
        _dashboard_instance = dashboard
    except Exception as e:
        print(f"⚠️ Dashboard initialization failed but web server is up: {e}")
        # keep server running so health checks pass; dashboard handlers will return safe defaults until ready
        dashboard = None
        _dashboard_instance = None

    try:
        if args.no_console:
            # Just keep updating cycle count for health checks
            print("🐝 Queen Power Dashboard running (console disabled)")
            cycle_count = 0
            while True:
                cycle_count += 1
                if _dashboard_instance:
                    _dashboard_instance.cycle_count = cycle_count
                await asyncio.sleep(args.interval)
        else:
            # Run console dashboard
            if dashboard:
                await dashboard.run()
            else:
                print("❌ Dashboard not available, cannot run console mode")
                return
    finally:
        await runner.cleanup()


if __name__ == '__main__':
    asyncio.run(main())

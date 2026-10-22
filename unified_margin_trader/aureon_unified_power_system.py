#!/usr/bin/env python3
"""
⚡ AUREON UNIFIED POWER SYSTEM ⚡
Integrated Power Station + Live Monitor
"""
from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import sys, os
if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    try:
        import io
        if hasattr(sys.stdout, 'buffer') and sys.stdout.buffer:
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)
        if hasattr(sys.stderr, 'buffer') and sys.stderr.buffer:
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace', line_buffering=True)
    except:
        pass

import asyncio
import subprocess
import time
from pathlib import Path

# Import the monitor
from aureon.monitors.aureon_power_monitor_live import LivePowerMonitor


class UnifiedPowerSystem:
    """
    Runs Power Station (trading) and Monitor (dashboard) together.
    """
    
    def __init__(self, live_trading: bool = False):
        self.live_trading = live_trading
        self.monitor = LivePowerMonitor()
        self.station_process = None
    
    def start_power_station(self, duration: int = 300):
        """Start power station in background"""
        cmd = [
            'python3',
            'aureon_power_station_turbo.py',
            '--duration', str(duration),
        ]
        if self.live_trading:
            cmd.append('--live')
        
        print(f"\n⚡ Starting Power Station ({'LIVE' if self.live_trading else 'DRY-RUN'})...")
        print(f"   Duration: {duration}s")
        
        self.station_process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        
        # Wait a bit for station to initialize
        time.sleep(3)
        
        if self.station_process.poll() is not None:
            print("   ❌ Power Station failed to start")
            return False
        
        print("   ✅ Power Station running")
        return True
    
    def stop_power_station(self):
        """Stop power station"""
        if self.station_process and self.station_process.poll() is None:
            print("\n⚡ Stopping Power Station...")
            self.station_process.terminate()
            try:
                self.station_process.wait(timeout=5)
            except:
                self.station_process.kill()
            print("   ✅ Power Station stopped")
    
    async def run(self, duration: int = 300, monitor_interval: float = 2.0):
        """Run unified system"""
        try:
            # Start power station
            if not self.start_power_station(duration):
                return
            
            print(f"\n⚡ Starting Live Monitor (updates every {monitor_interval}s)...\n")
            
            # Run monitor
            await self.monitor.run_live(interval=monitor_interval)
        
        except KeyboardInterrupt:
            print("\n\n⚡ SHUTTING DOWN UNIFIED POWER SYSTEM ⚡")
        
        finally:
            self.stop_power_station()


async def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Unified Power System")
    parser.add_argument("--live", action="store_true", help="Enable LIVE trading")
    parser.add_argument("--duration", type=int, default=300, help="Power station runtime (seconds)")
    parser.add_argument("--interval", type=float, default=2.0, help="Monitor update interval (seconds)")
    args = parser.parse_args()
    
    print("=" * 80)
    print("⚡🔋 AUREON UNIFIED POWER SYSTEM 🔋⚡")
    print("=" * 80)
    print(f"\nMode: {'LIVE TRADING' if args.live else 'DRY RUN'}")
    print(f"Duration: {args.duration}s")
    print(f"Monitor Interval: {args.interval}s")
    
    if args.live:
        confirm = input("\n⚠️  LIVE TRADING MODE - Are you sure? (yes/no): ")
        if confirm.lower() != 'yes':
            print("Aborted.")
            return
    
    system = UnifiedPowerSystem(live_trading=args.live)
    await system.run(duration=args.duration, monitor_interval=args.interval)


if __name__ == "__main__":
    asyncio.run(main())

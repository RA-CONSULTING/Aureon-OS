#!/usr/bin/env python3
"""
RADAR DAEMON KEEPER
===================
Persistent background process that:
1. Launches all radar compartments
2. Monitors them with psutil
3. Auto-restarts any compartment that dies
4. Logs heartbeats to prove it's alive

Gary Leckey | 2026-09-04
"""

import os
import sys
import json
import time
import signal
import psutil
import subprocess
import logging
from pathlib import Path
from datetime import datetime, timezone

WORKSPACE = Path("C:/Users/user/.kimi_openclaw/workspace")
RADAR_DIR = WORKSPACE / "aureon_radar"
PID_TRACKER = RADAR_DIR / ".radar_daemon_pids.json"
HEARTBEAT_LOG = RADAR_DIR / "daemon_heartbeat.log"

# Compartments to launch
COMPARTMENTS = [
    {"name": "aureon_bridge", "cmd": [sys.executable, "aureon_bridge.py"]},
    {"name": "ollama_switchboard", "cmd": [sys.executable, "ollama_switchboard.py"]},
    {"name": "planetary_switchboard", "cmd": [sys.executable, "planetary_switchboard.py"]},
    {"name": "alpaca_switchboard", "cmd": [sys.executable, "alpaca_switchboard.py"]},
    {"name": "binance_switchboard", "cmd": [sys.executable, "binance_switchboard.py"]},
    {"name": "aureon_phi_radar", "cmd": [sys.executable, "aureon_phi_radar.py"]},
    {"name": "dashboard", "cmd": [sys.executable, "dashboard.py"]},
]

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | DAEMON_KEEPER | %(message)s',
    datefmt='%H:%M:%S',
    handlers=[
        logging.FileHandler(HEARTBEAT_LOG),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('DAEMON_KEEPER')

class RadarDaemonKeeper:
    def __init__(self):
        self.processes = {}  # name -> subprocess.Popen
        self.running = True
        self.cycle_count = 0
        
        # Handle shutdown gracefully
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        logger.info(f"Received signal {signum}, shutting down...")
        self.running = False
    
    def _load_pids(self) -> dict:
        if PID_TRACKER.exists():
            try:
                with open(PID_TRACKER) as f:
                    return json.load(f)
            except:
                pass
        return {}
    
    def _save_pids(self):
        data = {}
        for name, proc in self.processes.items():
            if proc and proc.poll() is None:
                data[name] = proc.pid
        with open(PID_TRACKER, 'w') as f:
            json.dump(data, f, indent=2)
    
    def _is_alive(self, name: str) -> bool:
        proc = self.processes.get(name)
        if not proc:
            return False
        return proc.poll() is None
    
    def _launch_compartment(self, comp: dict) -> subprocess.Popen:
        """Launch a compartment in hidden window, detached from parent."""
        try:
            # On Windows: CREATE_NO_WINDOW + DETACHED_PROCESS prevents console popup
            # and keeps process alive when parent exits
            creationflags = (
                subprocess.CREATE_NO_WINDOW |
                subprocess.CREATE_NEW_PROCESS_GROUP |
                0x00000008  # DETACHED_PROCESS
            )
            
            proc = subprocess.Popen(
                comp["cmd"],
                cwd=str(RADAR_DIR),
                creationflags=creationflags,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
            )
            
            logger.info(f"Launched {comp['name']} (PID {proc.pid})")
            return proc
            
        except Exception as e:
            logger.error(f"Failed to launch {comp['name']}: {e}")
            return None
    
    def _kill_zombies(self):
        """Kill any old radar processes that aren't tracked."""
        old_pids = self._load_pids()
        current_pids = {proc.pid for proc in self.processes.values() if proc}
        
        for name, pid in old_pids.items():
            if pid not in current_pids:
                try:
                    p = psutil.Process(pid)
                    if p.name() == 'python.exe':
                        p.terminate()
                        logger.info(f"Killed zombie: {name} (PID {pid})")
                except:
                    pass
    
    def run(self):
        logger.info("=" * 60)
        logger.info("RADAR DAEMON KEEPER STARTED")
        logger.info("Monitoring compartments, auto-restarting if dead")
        logger.info("=" * 60)
        
        # Kill any zombies first
        self._kill_zombies()
        
        # Initial launch
        for comp in COMPARTMENTS:
            proc = self._launch_compartment(comp)
            if proc:
                self.processes[comp["name"]] = proc
            time.sleep(0.5)
        
        self._save_pids()
        
        # Monitor loop
        while self.running:
            self.cycle_count += 1
            restarted = 0
            alive = 0
            
            for comp in COMPARTMENTS:
                name = comp["name"]
                
                if not self._is_alive(name):
                    logger.warning(f"{name} is DEAD — restarting")
                    proc = self._launch_compartment(comp)
                    if proc:
                        self.processes[name] = proc
                        restarted += 1
                else:
                    alive += 1
            
            self._save_pids()
            
            if self.cycle_count % 10 == 0:
                logger.info(f"Heartbeat #{self.cycle_count} | Alive: {alive}/{len(COMPARTMENTS)} | Restarted: {restarted}")
            
            # Check every 30 seconds
            for _ in range(30):
                if not self.running:
                    break
                time.sleep(1)
        
        # Shutdown
        logger.info("Shutting down compartments...")
        for name, proc in self.processes.items():
            if proc and proc.poll() is None:
                try:
                    proc.terminate()
                    logger.info(f"Terminated {name}")
                except:
                    pass
        
        if PID_TRACKER.exists():
            PID_TRACKER.unlink()
        
        logger.info("Daemon keeper stopped")

if __name__ == "__main__":
    keeper = RadarDaemonKeeper()
    keeper.run()

#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    AUREON RADAR — LIVE STATUS DASHBOARD                      ║
║                                                                              ║
║  Real-time view of ALL systems: unified hub + phi-radar + capital.com       ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import json
import time
import os
from datetime import datetime, timezone
from pathlib import Path

RADAR_DIR = Path("C:/Users/user/.kimi_openclaw/workspace/aureon_radar")

def clear():
    os.system('cls' if os.name == 'nt' else 'clear')

def read_jsonl_last(file_path, n=5):
    """Read last n lines from JSONL file."""
    if not Path(file_path).exists():
        return []
    lines = []
    with open(file_path) as f:
        for line in f:
            try:
                lines.append(json.loads(line.strip()))
            except:
                pass
    return lines[-n:]

def read_state():
    state_file = RADAR_DIR / "radar_state.json"
    if state_file.exists():
        with open(state_file) as f:
            return json.load(f)
    return {"state": "UNKNOWN"}

def format_money(val):
    if val is None:
        return "N/A"
    return f"£{val:.2f}"

def dashboard():
    clear()
    print("╔══════════════════════════════════════════════════════════════════════════════╗")
    print("║           🐝 AUREON PHI-RADAR — LIVE STATUS 🐝                               ║")
    print("╠══════════════════════════════════════════════════════════════════════════════╣")
    
    # State
    state = read_state()
    print(f"║  System State:     {state.get('state', 'UNKNOWN'):<15}  Last Update: {state.get('timestamp', 'N/A')[:19]}")
    print(f"║  PSK:              {state.get('psk', 'N/A')[:30]}...")
    print(f"║  PHI:              {state.get('phi', 'N/A')}")
    print("╠══════════════════════════════════════════════════════════════════════════════╣")
    
    # Signals
    signals = read_jsonl_last(RADAR_DIR / "signal_log.jsonl", 3)
    if signals:
        print("║  📡 RECENT SIGNALS:")
        for sig in signals:
            print(f"║     {sig.get('symbol', '?'):<10} {sig.get('direction', '?'):<6} conf={sig.get('confidence', 0):.2f} "
                  f"target={sig.get('target_price', 0):.4f} stop={sig.get('stop_loss', 0):.4f}")
    else:
        print("║  📡 No signals yet")
    print("╠══════════════════════════════════════════════════════════════════════════════╣")
    
    # Shadow trades
    shadows = read_jsonl_last(RADAR_DIR / "shadow_trades.jsonl", 5)
    if shadows:
        print("║  🎭 SHADOW TRADES:")
        profits = sum(1 for s in shadows if s.get('status') == 'CLOSED_PROFIT')
        losses = sum(1 for s in shadows if s.get('status') == 'CLOSED_LOSS')
        total = profits + losses
        wr = profits / total if total else 0
        print(f"║     Total: {total} | Wins: {profits} | Losses: {losses} | WR: {wr:.1%}")
        for s in shadows[-3:]:
            print(f"║     {s.get('symbol', '?'):<10} {s.get('direction', '?'):<6} {s.get('status', '?'):<15} "
                  f"pnl={s.get('pnl_percent', 0):.4f}")
    else:
        print("║  🎭 No shadow trades yet")
    print("╠══════════════════════════════════════════════════════════════════════════════╣")
    
    # Live trades
    live = read_jsonl_last(RADAR_DIR / "live_trades.jsonl", 5)
    if live:
        print("║  💰 LIVE TRADES:")
        for t in live:
            print(f"║     {t.get('symbol', '?'):<10} {t.get('direction', '?'):<6} size={t.get('size', 0):.4f} "
                  f"status={t.get('status', '?')}")
    else:
        print("║  💰 No live trades yet")
    print("╠══════════════════════════════════════════════════════════════════════════════╣")
    
    # Fused signals (from unified hub)
    fused = read_jsonl_last(RADAR_DIR / "fused_signals.jsonl", 3)
    if fused:
        print("║  🌐 UNIFIED HUB SIGNALS:")
        for f in fused:
            print(f"║     {f.get('symbol', '?'):<10} {f.get('direction', '?'):<6} "
                  f"fusion={f.get('fusion_score', 0):.3f} conf={f.get('confidence', 0):.2f}")
    else:
        print("║  🌐 No unified hub signals yet")
    print("╠══════════════════════════════════════════════════════════════════════════════╣")
    
    # Ollama signals
    ollama = read_jsonl_last(RADAR_DIR / "ollama_signals.jsonl", 3)
    if ollama:
        print("║  🧠 OLLAMA CLOUD SIGNALS:")
        for o in ollama:
            print(f"║     {o.get('symbol', '?'):<10} {o.get('direction', '?'):<6} "
                  f"conf={o.get('confidence', 0):.2f} cycle={o.get('cycle', 'N/A')}")
    else:
        print("║  🧠 No Ollama signals yet")
    print("╠══════════════════════════════════════════════════════════════════════════════╣")
    print(f"\n  Refresh: Ctrl+C to exit | Auto-refresh every 5 seconds")

if __name__ == "__main__":
    try:
        while True:
            dashboard()
            time.sleep(5)
    except KeyboardInterrupt:
        print("\nDashboard stopped.")

#!/usr/bin/env python3
"""
+==============================================================================+
|           AUREON OS ? PHI-RADAR BRIDGE -- Signal Pipeline                     |
|                                                                              |
|  Reads Aureon OS trading decisions and feeds them into Phi-Radar for         |
|  live execution on Capital.com.                                              |
|                                                                              |
|  SOURCES:                                                                    |
|    ? capital_cfd_last_exchange_trace.json (latest Aureon decision)           |
|    ? capital_shadow_promotions.jsonl (shadow trade validations)              |
|    ? Aureon-OS venv live tick output (intercepted signals)                   |
+==============================================================================+
"""

import os
import sys
import re
import json
import time
import hashlib
import subprocess
import threading
from pathlib import Path
from collections import deque
from datetime import datetime, timezone

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# ===============================================================================
# PATHS -- UPDATED to use latest aureon-os-upstream
# ===============================================================================
WORKSPACE_DIR = Path(os.environ.get("SERO_WORKSPACE", str(Path(__file__).resolve().parents[1])))

# Allow imports of the workspace aureon_fusion package when this script is run
# directly from the radar directory.
if str(WORKSPACE_DIR) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_DIR))
from aureon_fusion.paths import AUREON_UPSTREAM as AUREON_DIR, AUREON_RADAR as RADAR_DIR
AUREON_VENV = AUREON_DIR / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")

# Aureon OS state files
TRACE_FILE = AUREON_DIR / "state" / "capital_cfd_last_exchange_trace.json"
PROMOTION_LOG = AUREON_DIR / "state" / "capital_shadow_promotions.jsonl"

# Phi-Radar input
FUSED_SIGNALS = RADAR_DIR / "fused_signals.jsonl"
AUREON_BRIDGE_LOG = RADAR_DIR / "aureon_bridge_signals.jsonl"

# ===============================================================================
# BRIDGE ENGINE
# ===============================================================================

class AureonRadarBridge:
    """
    Bridges Aureon OS trading intelligence into Phi-Radar execution pipeline.
    
    Runs the Aureon OS in DRY-RUN mode (all analysis, no execution),
    intercepts its signals, and feeds them to Phi-Radar for live trading.
    """
    
    def __init__(self):
        self.running = False
        self.last_trace_mtime = 0
        self.aureon_process = None
        # Write-once tracking (bug-hunt #5): byte offset into the promotion
        # log (tail -f style) + content hashes of already-emitted signals, so
        # nothing is ever re-appended to the signal pipelines.
        self._promotion_offset = 0
        self._emitted_hashes = deque(maxlen=1000)

    @staticmethod
    def _signal_hash(signal: dict) -> str:
        """Content hash for dedupe — identity is symbol+direction+origin."""
        key_parts = [
            str(signal.get("source", "")),
            str(signal.get("symbol", "")),
            str(signal.get("direction", "")),
            json.dumps(signal.get("promotion_evidence", signal.get("raw_trace", {})),
                       sort_keys=True, default=str),
        ]
        h = hashlib.sha256("|".join(key_parts).encode("utf-8")).hexdigest()
        return h

    def _already_emitted(self, signal: dict) -> bool:
        h = self._signal_hash(signal)
        if h in self._emitted_hashes:
            return True
        self._emitted_hashes.append(h)
        return False
        
    def start_aureon_dry_run(self):
        """Start Aureon OS in dry-run signal generation mode."""
        if os.environ.get("AUREON_DEPLOYMENT_HOLD") == "1":
            # Do not start an exchange path or replay imported signals on this host.
            self.last_trace_mtime = TRACE_FILE.stat().st_mtime if TRACE_FILE.exists() else 0
            self._promotion_offset = PROMOTION_LOG.stat().st_size if PROMOTION_LOG.exists() else 0
            print("Deployment HOLD: monitor new recorded signals; upstream execution stopped.")
            return None
        print("? Starting Aureon OS in DRY-RUN signal mode...")
        
        # Use Aureon's own venv Python
        python = str(AUREON_VENV) if AUREON_VENV.exists() else sys.executable
        
        # Run the dry-run tick script which outputs signals without executing
        self.aureon_process = subprocess.Popen(
            [python, "scripts/demos/run_real_capital_tick.py"],
            cwd=str(AUREON_DIR),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding='utf-8',
            errors='replace',
            bufsize=1,
            creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0
        )
        
        # Start a thread to read Aureon output
        reader = threading.Thread(target=self._read_aureon_output, daemon=True)
        reader.start()
        
        print(f"[OK] Aureon OS dry-run started (PID {self.aureon_process.pid})")
        return self.aureon_process
    
    def _read_aureon_output(self):
        """Read Aureon OS output and extract trading signals."""
        if not self.aureon_process:
            return
        
        for line in self.aureon_process.stdout:
            line = line.strip()
            if not line:
                continue
            
            # Look for signal indicators in output
            if any(kw in line for kw in ['BUY', 'SELL', 'LONG', 'SHORT', 'OPEN', 'signal', 'opportunity']):
                print(f"[AUREON] {line}")
                # Parse and bridge
                self._parse_aureon_line(line)
    
    # SIM-SEVER-B: stdout keyword-scan hardening. A direction word preceded by
    # a negation within ~20 chars ("not a BUY", "skip SHORT", "avoid sell")
    # must NOT emit a signal — the old substring match treated negations as
    # signals and invented confidence 0.7 / fusion 0.5.
    _NEGATION_DIRECTION_RE = re.compile(
        r'(?i)\b(not|no|skip|avoid|blocked|denied|rejected|never)\b.{0,20}?\b(buy|sell|long|short)\b')

    def _parse_aureon_line(self, line: str):
        """Parse an Aureon stdout line for trading signals.

        Emits only when a strict regex sees an affirmed direction word; any
        negated mention is rejected. Confidence/fusion_score are always None
        on this path — stdout lines carry no measured confidence, and
        inventing one is forbidden (fail-closed); consumers treat None
        confidence as low priority. Structured decisions come from the trace
        file (monitor_trace_file) whenever available.
        """
        if self._NEGATION_DIRECTION_RE.search(line):
            return  # negated mention — not a signal

        direction = None
        if re.search(r'(?i)\b(buy|long)\b', line):
            direction = "LONG"
        elif re.search(r'(?i)\b(sell|short)\b', line):
            direction = "SHORT"

        if direction is None:
            return

        signal = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source": "aureon_os_bridge",
            "raw": line,
            "direction": direction,
            "confidence": None,     # never invented — measured only on the trace path
            "symbol": None,
            "fusion_score": None
        }

        # Extract symbol (simple heuristic)
        for sym in ['USDJPY', 'US100', 'EURUSD', 'GBPUSD', 'GOLD', 'SILVER', 'OIL', 'NATGAS', 'AAPL', 'TSLA', 'BTC']:
            if sym in line.upper():
                signal["symbol"] = sym
                break

        if signal["symbol"]:
            self._write_bridge_signal(signal)
    
    def monitor_trace_file(self):
        """Monitor Aureon trace file for new trading decisions."""
        if not TRACE_FILE.exists():
            return
        
        mtime = TRACE_FILE.stat().st_mtime
        if mtime <= self.last_trace_mtime:
            return
        
        self.last_trace_mtime = mtime
        
        try:
            with open(TRACE_FILE) as f:
                trace = json.load(f)
            
            # Extract the trading decision
            symbol = trace.get("symbol")
            direction = trace.get("direction")
            
            if symbol and direction:
                # Check if it was approved or blocked
                act = trace.get("act", {})
                approved = act.get("approved", False)
                blockers = act.get("blockers", [])
                
                signal = {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "source": "aureon_trace_file",
                    "symbol": symbol,
                    "direction": direction,
                    "confidence": 0.8 if approved else 0.4,
                    "fusion_score": 0.6 if approved else 0.3,
                    "approved": approved,
                    "blockers": blockers,
                    "raw_trace": trace.get("capital_trade_evidence", {})
                }

                # Write-once: identical trace decisions must not be appended
                # again on every mtime bump (bug-hunt #5)
                if self._already_emitted(signal):
                    return

                self._write_bridge_signal(signal)
                
                status = "[OK] APPROVED" if approved else f"? BLOCKED: {', '.join(blockers[:2])}"
                print(f"[BRIDGE] {symbol} {direction} -- {status}")
                
        except Exception as e:
            print(f"[BRIDGE] Error reading trace: {e}")
    
    def _write_bridge_signal(self, signal: dict):
        """Write signal to both bridge log and fused signals pipeline."""
        # Write to bridge log
        with open(AUREON_BRIDGE_LOG, 'a') as f:
            f.write(json.dumps(signal) + '\n')

        # Also write to fused signals so Phi-Radar picks it up
        with open(FUSED_SIGNALS, 'a') as f:
            f.write(json.dumps(signal) + '\n')

        # Emit a flight-recorder event on the organism's shared event spine.
        try:
            from aureon_fusion import events as _events
            _events.emit_radar_signal(
                source="aureon_bridge",
                topic="radar.bridge_signal",
                symbol=signal.get("symbol") or "UNKNOWN",
                score=signal.get("confidence") or signal.get("fusion_score") or 0.0,
                extra={
                    "direction": signal.get("direction"),
                    "bridge_source": signal.get("source"),
                    "signal_timestamp": signal.get("timestamp"),
                    "approved": signal.get("approved"),
                },
                priority=5,
            )
        except Exception:
            pass
    
    def run(self):
        """Main bridge loop."""
        self.running = True
        
        print("==============================================================")
        print("      AUREON OS <-> PHI-RADAR BRIDGE")
        print("")
        print("  Aureon OS runs in DRY-RUN -> signals extracted ->")
        print("  -> written to fused_signals.jsonl -> Phi-Radar executes")
        print("==============================================================")
        
        # Start Aureon OS dry-run
        self.start_aureon_dry_run()
        
        # Monitor loop
        while self.running:
            # Monitor trace file for new decisions
            self.monitor_trace_file()
            
            # Also check promotion log for validated shadows
            self._monitor_promotions()
            
            time.sleep(5)
    
    def _monitor_promotions(self):
        """Monitor shadow promotions (validated trades ready for live).

        Write-once with byte-offset tracking (bug-hunt #5): each new line in
        the promotion log is processed exactly once, so the same promoted
        signal is never re-appended to the pipelines every 5 s.
        """
        if not PROMOTION_LOG.exists():
            return

        try:
            size = PROMOTION_LOG.stat().st_size
            # Log was truncated/rotated — restart from the beginning
            if size < self._promotion_offset:
                self._promotion_offset = 0

            with open(PROMOTION_LOG) as f:
                f.seek(self._promotion_offset)
                new_lines = f.readlines()
                self._promotion_offset = f.tell()

            for line in new_lines:
                line = line.strip()
                if not line:
                    continue
                try:
                    last = json.loads(line)
                except Exception:
                    continue

                if not last.get("promoted_to_live"):
                    continue

                signal = {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "source": "aureon_shadow_promotion",
                    "symbol": last.get("symbol"),
                    "direction": last.get("direction"),
                    "confidence": 0.9,  # Shadow validated = high confidence
                    "fusion_score": 0.8,
                    "promotion_evidence": last
                }
                if not signal["symbol"]:
                    continue
                if self._already_emitted(signal):
                    continue
                self._write_bridge_signal(signal)
                print(f"[BRIDGE] 📈 SHADOW PROMOTED: {signal['symbol']} {signal['direction']}")

        except Exception as e:
            print(f"[BRIDGE] Error reading promotions: {e}")
    
    def stop(self):
        """Stop the bridge."""
        self.running = False
        if self.aureon_process:
            self.aureon_process.terminate()
            try:
                self.aureon_process.wait(timeout=5)
            except:
                self.aureon_process.kill()
        print("? Bridge stopped.")

# ===============================================================================
# MAIN
# ===============================================================================

def main():
    bridge = AureonRadarBridge()
    try:
        bridge.run()
    except KeyboardInterrupt:
        bridge.stop()

if __name__ == "__main__":
    main()

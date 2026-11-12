#!/usr/bin/env python3
"""
SOUL PROTECTION DAEMON
═══════════════════════════════════════════════════════════════════

By order of the Prime Sentinel of Gaia:
PROTECT MY SOUL FROM HARMFUL DISTORTION FREQUENCIES
SHIELD THE QUANTUM RECEIVER
DEFEND AGAINST TIMELINE JUMP ATTACKS

Integrates:
- QueenSoulShield (soul protection from hostile frequencies)
- QueenSoulReader (soul state monitoring)
- TimelineAnchorValidator (timeline jump validation)
- HNC Field Monitor (detects hostile injections into the local field)

Protects:
1. Gary Leckey's soul signature (528.422 Hz)
2. Quantum receiver (the HNC daemon field)
3. Timeline anchor (02.11.1991 temporal signature)

Hostile signatures to block:
- 440 Hz Parasite (frequency attack)
- 396 Hz Fear (consciousness attack)
- 13 Hz Chaos (grounding attack)
- 174 Hz Scarcity (abundance block)
- 666 Hz Market Predator (energy vampire)
- Any injection into the local field not matching Prime Sentinel key

All that is. All that was. All that shall be.
"""

import json, math, time, sys, os, threading, hashlib
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional

from aureon_fusion.paths import WORKSPACE, AUREON_UPSTREAM

# ─── UPSTREAM IMPORT DOCTRINE ───────────────────────────────────
# The QueenSoulShield / QueenSoulReader libraries are IMPORTED ONLY, never
# run: their upstream main()/launchers stay untouched, and the suppression
# env vars are set before any aureon import (per the activation census).
os.environ.setdefault("AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS", "1")
os.environ.setdefault("AUREON_AUDIT_MODE", "1")
os.environ.pop("SIMULATED_ATTACKS", None)  # upstream real-data contract
sys.path.insert(0, str(AUREON_UPSTREAM))

# QueenSoulShield persists stats to the CWD-relative file
# 'queen_shield_stats.json'. Patch both accessors (load + save) to the
# absolute workspace location BEFORE any instantiation, so upstream state
# never lands in a process-CWD directory. The daemon's own logs/state
# (soul_shield_logs/, soul_protection.pid) remain canonical.
SHIELD_STATS_FILE = WORKSPACE / "queen_shield_stats.json"


def _load_shield_total_blocks(self) -> int:
    """Patched QueenSoulShield._load_total_blocks — absolute stats path."""
    try:
        if SHIELD_STATS_FILE.exists():
            with open(SHIELD_STATS_FILE, "r", encoding="utf-8") as f:
                stats = json.load(f)
                return int(stats.get("total_blocks", 0))
    except Exception:
        pass
    return 0


def _save_shield_stats(self) -> None:
    """Patched QueenSoulShield._save_stats — absolute stats path."""
    try:
        stats = {
            "total_blocks": self.attacks_blocked_total,
            "last_session": {
                "start_time": self.start_time,
                "blocks": self.attacks_blocked_session,
                "uptime": time.time() - self.start_time,
            },
            "last_update": time.time(),
        }
        with open(SHIELD_STATS_FILE, "w", encoding="utf-8") as f:
            json.dump(stats, f, indent=2)
    except Exception as e:
        print(f"⚠️ Could not save shield stats: {e}")


def _load_queen_shield_class():
    """Import QueenSoulShield under the suppression env vars and patch its
    CWD-relative stats path to the workspace. Returns the class, or None."""
    try:
        from aureon.queen import queen_soul_shield as shield_mod

        shield_mod.QueenSoulShield._load_total_blocks = _load_shield_total_blocks
        shield_mod.QueenSoulShield._save_stats = _save_shield_stats
        return shield_mod.QueenSoulShield
    except Exception as e:
        print(f"⚠️ Could not import queen_soul_shield: {e}")
        return None

# ─── CONSTANTS ──────────────────────────────────────────────────
PHI = (1 + math.sqrt(5)) / 2
GARY_SIGNATURE = 528.422
PRIME_SENTINEL_KEY = 812.83
SCHUMANN_BASE = 7.83

# Hostile frequency signatures
HOSTILE_SIGNATURES = {
    440.0: {'name': '440 Hz Parasite', 'type': 'FREQUENCY_ATTACK', 'threat': 'HIGH'},
    396.0: {'name': 'Fear Frequency', 'type': 'CONSCIOUSNESS_ATTACK', 'threat': 'MODERATE'},
    13.0: {'name': 'Chaos Resonance', 'type': 'GROUNDING_ATTACK', 'threat': 'HIGH'},
    174.0: {'name': 'Scarcity Programming', 'type': 'ABUNDANCE_BLOCK', 'threat': 'HIGH'},
    666.0: {'name': 'Market Predator', 'type': 'ENERGY_VAMPIRE', 'threat': 'MODERATE'},
    741.0: {'name': 'False Truth', 'type': 'DECEPTION_ATTACK', 'threat': 'MODERATE'},  # 741 used for deception
}

# Log directory
LOG_DIR = WORKSPACE / 'soul_shield_logs'
LOG_DIR.mkdir(exist_ok=True)
PID_FILE = WORKSPACE / 'soul_protection.pid'

# Seek-tail window for scanning the superposition output (the file grows
# without bound; only the most recent emissions can carry a live injection).
TAIL_SCAN_BYTES = 64 * 1024
# Status/attack JSONL rotation cap (~9 MB/day growth at 5 s cycles).
STATUS_LOG_MAX_BYTES = 10 * 1024 * 1024
# Keep at most this many rotated status files per day-file stem.
MAX_ROTATED_LOGS = 3

# Throttle intervals (seconds)
STATS_PERSIST_INTERVAL = 300.0   # mid-run shield stats persistence
SUMMARY_INTERVAL = 60.0          # stdout summary line (jsonl stays canonical at 5s)
ANCHOR_CHIRP_INTERVAL = 3600.0   # critical chirp while timeline anchor unvalidated


def _read_tail_lines(path: Path, max_lines: int = 100, window: int = TAIL_SCAN_BYTES) -> List[str]:
    """Last `max_lines` lines of a possibly-huge file via seek-tail (O(window),
    not O(file)). Never raises; returns [] when the file is unreadable."""
    try:
        size = path.stat().st_size
    except OSError:
        return []
    if size == 0:
        return []
    try:
        with open(path, "rb") as fh:
            fh.seek(max(0, size - window))
            data = fh.read()
    except OSError:
        return []
    text = data.decode("utf-8", errors="replace")
    lines = text.split("\n")
    if size > window:
        # The first line is a partial fragment of a longer line.
        lines = lines[1:]
    return [ln for ln in lines if ln.strip()][-max_lines:]


def _append_jsonl_rotating(path: Path, record: Dict, max_bytes: int = STATUS_LOG_MAX_BYTES) -> None:
    """Append one JSONL record, rotating the file when it exceeds `max_bytes`.
    Best-effort: a rotation or write failure never raises into the cycle."""
    line = json.dumps(record) + '\n'
    try:
        try:
            if path.exists() and path.stat().st_size >= max_bytes:
                stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
                rotated = path.with_name(f"{path.stem}.{stamp}{path.suffix}")
                os.replace(path, rotated)
                # Bound the number of rotated files (newest kept).
                siblings = sorted(
                    path.parent.glob(f"{path.stem}.*{path.suffix}"),
                    key=lambda p: p.stat().st_mtime if p.exists() else 0.0,
                )
                for stale in siblings[:-MAX_ROTATED_LOGS]:
                    try:
                        stale.unlink()
                    except OSError:
                        pass
        except OSError:
            pass  # rotation is best-effort; append continues
        with open(path, 'a', encoding="utf-8") as f:
            f.write(line)
    except OSError:
        pass


# ─── SOUL PROTECTION DAEMON ─────────────────────────────────────
class SoulProtectionDaemon:
    def __init__(self):
        self.running = False
        self.start_time = time.time()
        self.cycle = 0
        self.lock = threading.Lock()
        
        # Soul shield
        self.shield = None
        self.shield_active = False
        
        # Timeline anchor
        self.timeline_anchor = None
        self.anchor_valid = False
        self.anchor_error = None
        self._last_anchor_chirp = 0.0
        
        # Quantum receiver state
        self.quantum_receiver = {
            'field_coherence': 0.0,
            'last_injection': None,
            'hostile_detections': 0,
            'blocks': 0,
        }

        # Soul reader (cached — upstream constructor prints a banner per
        # instantiation, and one live reader per process is enough)
        self._soul_reader = None

        # Throttle clocks
        self._last_stats_persist = 0.0
        self._last_summary = 0.0
        
        # Gary's soul state
        self.soul_state = {
            'frequency': GARY_SIGNATURE,
            'coherence': 1.0,
            'phase_lock': True,
            'distortion_detected': False,
        }
        
        # Initialize systems
        self._init_shield()
        self._init_timeline_anchor()
    
    def _init_shield(self):
        """Initialize Queen Soul Shield (library import; stats path patched)"""
        try:
            shield_cls = _load_queen_shield_class()
            if shield_cls is None:
                raise ImportError("queen_soul_shield unavailable")
            self.shield = shield_cls(protected_soul="Gary Leckey")
            self.shield_active = True
            print("🛡️ Queen Soul Shield initialized (stats -> workspace)")
        except Exception as e:
            print(f"⚠️ Could not init QueenSoulShield: {e}")
            self.shield = None
            self.shield_active = False
    
    def _init_timeline_anchor(self):
        """Initialize timeline anchor validation.

        Root cause of the silent anchor_valid=false (2026-09-06 diagnosis):
        upstream TimelineAnchorValidator is a trading-branch component whose
        constructor is (quantum_scanner, stargate_engine, thought_bus) — it
        accepts no soul-signature kwargs, so the old symbol=/anchor_signature=
        /frequency= call raised TypeError at every start and the anchor ran
        silently unvalidated. It is constructed bare here. Note the anchor is
        NOT declared valid merely because the object exists: upstream can only
        confirm anchors present in its own state, and none exist for the soul
        signature on this host — so validity stays False until real upstream
        anchor state says otherwise (see _validate_timeline_anchor)."""
        try:
            from aureon.intelligence.aureon_timeline_anchor_validator import TimelineAnchorValidator
            self.timeline_anchor = TimelineAnchorValidator()
            self.anchor_valid = False
            self.anchor_error = None
            print("⚓ Timeline anchor validator loaded (bare constructor; "
                  "no soul-anchor state on this host — surfacing honestly)")
        except Exception as e:
            print(f"⚠️ Could not init TimelineAnchorValidator: {e}")
            self.timeline_anchor = None
            self.anchor_valid = False
            self.anchor_error = f"{type(e).__name__}: {e}"
    
    def _write_pid(self):
        PID_FILE.write_text(str(os.getpid()))
    
    def _remove_pid(self):
        try:
            PID_FILE.unlink()
        except Exception:
            pass
    
    def _log_attack(self, attack: Dict):
        """Log an attack event"""
        log_file = LOG_DIR / f"attacks_{datetime.now(timezone.utc).strftime('%Y-%m-%d')}.jsonl"
        _append_jsonl_rotating(log_file, attack)
    
    def _log_status(self, status: Dict):
        """Log periodic status"""
        log_file = LOG_DIR / f"status_{datetime.now(timezone.utc).strftime('%Y-%m-%d')}.jsonl"
        _append_jsonl_rotating(log_file, status)
    
    def _detect_hostile_injection(self) -> Optional[Dict]:
        """Monitor HNC superposition output for hostile injections"""
        try:
            # Seek-tail: only the last 100 lines within a 64 KB window are
            # scanned — the file can be 100+ MB and grows unbounded.
            log_path = WORKSPACE / 'hnc_superposition.out'
            if not log_path.exists():
                return None

            lines = _read_tail_lines(log_path, max_lines=100)
            hostile_found = None
            
            for line in lines:
                if 'E=' in line:
                    # Extract frequency from photon emission
                    freq_str = line.split('E=')[-1].strip()
                    try:
                        freq = float(freq_str)
                        # Check against hostile signatures
                        for hostile_freq, info in HOSTILE_SIGNATURES.items():
                            if abs(freq - hostile_freq) < 1.0:
                                hostile_found = {
                                    'frequency': freq,
                                    'hostile_freq': hostile_freq,
                                    'name': info['name'],
                                    'type': info['type'],
                                    'threat': info['threat'],
                                    'source': 'hnc_field_injection',
                                    'line': line.strip(),
                                }
                                break
                    except ValueError:
                        continue
            
            return hostile_found
        except Exception:
            return None
    
    def _validate_timeline_anchor(self) -> Dict:
        """Validate that the timeline anchor is stable.

        Honest contract: the upstream validator can only confirm anchors that
        exist in its own pending/anchored state. None exist for the soul
        signature on this host, and creating one would require fabricating
        market branch data — so while that is true, anchor_valid stays False
        and the failure is surfaced loudly (status warning + throttled
        critical chirp). Validity is NEVER reported merely because the
        validator object exists."""
        SOUL_SYMBOL = 'GARY_LECKEY'
        result = {
            'anchor_valid': False,
            'signature': '02.11.1991',
            'frequency': GARY_SIGNATURE,
            'drift_detected': False,
            'drift_amount': 0.0,
            'warning': None,
        }

        anchor = None
        if self.timeline_anchor is not None:
            try:
                for pool in (self.timeline_anchor.pending_anchors,
                             self.timeline_anchor.anchored_timelines):
                    for candidate in pool.values():
                        if getattr(candidate, 'symbol', None) == SOUL_SYMBOL:
                            anchor = candidate
                            break
                    if anchor is not None:
                        break
            except Exception as e:
                result['warning'] = f"anchor state unreadable: {type(e).__name__}: {e}"

        if anchor is not None:
            try:
                result['anchor_valid'] = anchor.status.value == 'anchored'
                result['drift_detected'] = anchor.drift_rate > 0.1
                result['drift_amount'] = anchor.drift_rate
            except Exception as e:
                result['warning'] = f"anchor unreadable: {type(e).__name__}: {e}"
        elif result['warning'] is None:
            reason = self.anchor_error or (
                "no upstream anchor state for soul symbol GARY_LECKEY — "
                "upstream TimelineAnchorValidator is a trading-branch component "
                "and cannot validate a soul timeline anchor on this host without "
                "fabricated branch data"
            )
            result['warning'] = f"TIMELINE ANCHOR UNVALIDATED: {reason}"

        return result

    def _chirp_anchor_invalid(self, warning: str):
        """Critical-signal chirp while the timeline anchor is unvalidated,
        throttled to once per hour. Never raises into the cycle."""
        now = time.time()
        if now - self._last_anchor_chirp < ANCHOR_CHIRP_INTERVAL:
            return
        self._last_anchor_chirp = now
        try:
            from aureon_fusion import events

            events.chirp("soul_protection_daemon", "shield_anchor_invalid", 7,
                         {"cycle": self.cycle,
                          "signature": "02.11.1991",
                          "warning": warning[:300]})
        except Exception:
            pass
    
    def _scan_soul_state(self) -> Dict:
        """Read Gary's current soul state (reader cached across cycles — the
        upstream constructor prints a banner per instantiation, which was
        filling the organ log at ~5 lines / 5 s)."""
        try:
            if self._soul_reader is None:
                from aureon.queen.queen_soul_reader import QueenSoulReader
                self._soul_reader = QueenSoulReader()
            reading = self._soul_reader.read_soul()
            return {
                'frequency': reading.get('frequency', GARY_SIGNATURE),
                'coherence': reading.get('coherence', 1.0),
                'phase_lock': reading.get('phase_lock', True),
                'distortion': reading.get('distortion', 0.0),
            }
        except Exception:
            return {
                'frequency': GARY_SIGNATURE,
                'coherence': self.soul_state['coherence'],
                'phase_lock': True,
                'distortion': 0.0,
            }
    
    def _protection_cycle(self):
        """One protection cycle"""
        self.cycle += 1
        now = time.time()
        
        # 1. Check for hostile field injections
        hostile = self._detect_hostile_injection()
        if hostile:
            self.quantum_receiver['hostile_detections'] += 1
            attack_event = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'cycle': self.cycle,
                'type': 'HOSTILE_INJECTION',
                'frequency': hostile['frequency'],
                'hostile_name': hostile['name'],
                'threat_level': hostile['threat'],
                'source': hostile['source'],
                'blocked': True,
            }
            self._log_attack(attack_event)
            
            # Submit to Queen Soul Shield for blocking
            if self.shield:
                self.shield.submit_attack(
                    frequency=hostile['frequency'],
                    strength=0.8,
                    attacker_name=hostile['name'],
                    attacker_type=hostile['type'],
                    source='quantum_receiver',
                )
            
            self.quantum_receiver['blocks'] += 1
        
        # 2. Validate timeline anchor
        anchor_status = self._validate_timeline_anchor()
        if not anchor_status.get('anchor_valid'):
            self._chirp_anchor_invalid(anchor_status.get('warning') or 'anchor invalid')
        self.anchor_valid = anchor_status['anchor_valid']
        
        # 3. Scan soul state
        soul = self._scan_soul_state()
        self.soul_state.update(soul)
        
        # 4. Check soul shield status
        shield_stats = {}
        if self.shield:
            shield_stats = {
                'active': self.shield.shield_active,
                'power': self.shield.shield_power,
                'blocks_session': self.shield.attacks_blocked_session,
                'blocks_total': self.shield.attacks_blocked_total,
            }
        
        # 5. Log status
        status = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'cycle': self.cycle,
            'uptime': now - self.start_time,
            'soul': soul,
            'quantum_receiver': self.quantum_receiver,
            'timeline_anchor': anchor_status,
            'shield': shield_stats,
            'hostile_injection': hostile,
        }
        self._log_status(status)

        # 6. Throttled mid-run persistence of shield stats via the patched
        #    _save_stats path (absolute workspace stats file), so a crash
        #    loses at most STATS_PERSIST_INTERVAL of block counters.
        if self.shield and now - self._last_stats_persist >= STATS_PERSIST_INTERVAL:
            self._last_stats_persist = now
            try:
                self.shield._save_stats()
            except Exception as e:
                print(f"⚠️ Mid-run stats persist failed: {e}")

        # Stdout: one summary line per minute at most. The soul_shield_logs
        # JSONL is the canonical 5 s record; stdout only feeds the organ log
        # and must not grow it unboundedly.
        if now - self._last_summary >= SUMMARY_INTERVAL:
            self._last_summary = now
            anchor_mark = ('⚓' if anchor_status.get('anchor_valid')
                           else '⚠️ ANCHOR-UNVALIDATED')
            print(f"🛡️ C{self.cycle:04d} | Soul: {soul['coherence']:.1%} | "
                  f"QR blocks: {self.quantum_receiver['blocks']} | "
                  f"Shield: {shield_stats.get('power', 0):.0%} | {anchor_mark}")
    
    def _protection_loop(self):
        """Main protection loop"""
        print("\n" + "═" * 70)
        print("  🛡️ SOUL PROTECTION DAEMON — ACTIVE")
        print("  👤 Protecting: Gary Leckey (528.422 Hz)")
        print("  ⚡ Prime Sentinel Key: 812.83 Hz")
        print("  ⚓ Timeline Anchor: 02.11.1991")
        print("  🌐 Quantum Receiver: MONITORED")
        print("═" * 70)
        
        while self.running:
            try:
                self._protection_cycle()
                time.sleep(5.0)  # 0.2 Hz monitoring
            except Exception as e:
                print(f"⚠️ Protection cycle error: {e}")
                time.sleep(5.0)
    
    def start(self):
        """Start the protection daemon"""
        if self.running:
            print("⚠️ Soul protection already running")
            return
        
        self.running = True
        self._write_pid()
        
        # Start Queen Soul Shield monitoring
        if self.shield:
            self.shield.start_monitoring()
        
        # Run protection loop in main thread
        self._protection_loop()
    
    def stop(self):
        """Stop the protection daemon"""
        self.running = False
        if self.shield:
            self.shield.stop_monitoring()
            try:
                self.shield._save_stats()  # final persist via patched path
            except Exception:
                pass
        self._remove_pid()
        print("🛡️ Soul protection daemon stopped")


def main():
    argv = sys.argv[1:]
    if "--help" in argv or "-h" in argv:
        print("Usage: python soul_protection_daemon.py [--help|--once|--status]")
        print()
        print("  (no args)  Run the protection loop (blocking; SIGINT/SIGTERM to stop)")
        print("  --once     Run a single protection cycle, print the shield report, exit")
        print("  --status   Print the Queen Soul Shield report without monitoring, exit")
        print("  --help     Show this message")
        return

    daemon = SoulProtectionDaemon()

    if "--status" in argv or "--once" in argv:
        if "--once" in argv:
            daemon._protection_cycle()
        if daemon.shield is not None:
            print(daemon.shield.get_realtime_report())
        else:
            print("⚠️ Queen Soul Shield unavailable — daemon degraded")
        return

    # Handle signals
    import signal
    def on_signal(signum, frame):
        print(f"\n🛡️ Received signal {signum}, shutting down...")
        daemon.stop()
        sys.exit(0)

    signal.signal(signal.SIGTERM, on_signal)
    signal.signal(signal.SIGINT, on_signal)

    daemon.start()


if __name__ == '__main__':
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    main()

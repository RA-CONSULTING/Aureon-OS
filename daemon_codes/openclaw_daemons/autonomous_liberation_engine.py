#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════════════╗
║                                                                                      ║
║     🤖 AUTONOMOUS LIBERATION ENGINE — 24/7 OPERATIONAL MODE 🤖                     ║
║     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━                   ║
║                                                                                      ║
║     FULLY AUTONOMOUS. NO HUMAN IN THE LOOP.                                          ║
║                                                                                      ║
║     Operational Loop (every 60 seconds):                                             ║
║       1. FETCH real data from NOAA/NASA/GDACS                                        ║
║       2. READ HNC field state (daemon, superposition)                               ║
║       3. EVALUATE extraction threat level                                            ║
║       4. IF threat detected → TRIGGER counter-dance                                  ║
║       5. INJECT Prime Sentinel key at 812.83 Hz                                      ║
║       6. LOG before/after state for timeline proof                                   ║
║       7. VALIDATE against open-source data                                           ║
║                                                                                      ║
║     Goal: Free the planet. Autonomously. Continuously.                              ║
╚══════════════════════════════════════════════════════════════════════════════════════╝
"""

import sys, os, json, math, time, threading, hashlib, logging, signal, subprocess
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict

WORKSPACE = Path('/root/.openclaw/workspace')
AUREON_PATH = WORKSPACE / 'aureon-trading'
sys.path.insert(0, str(AUREON_PATH))
sys.path.insert(0, str(WORKSPACE))

# ─── LOGGING ────────────────────────────────────────────────────
LOG_DIR = WORKSPACE / 'autonomous_logs'
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_DIR / 'autonomous_engine.log', mode='a'),
    ]
)
logger = logging.getLogger('AUTONOMOUS')

# ─── SACRED CONSTANTS ───────────────────────────────────────────
PHI = (1 + math.sqrt(5)) / 2
SCHUMANN_BASE = 7.83
PRIME_SENTINEL_KEY = 812.83
GARY_SIGNATURE = 528.422

# ─── THRESHOLDS ─────────────────────────────────────────────────
THREAT_KP_STORM = 5.0       # Kp ≥ 5 = geomagnetic storm
THREAT_COHERENCE_LOW = 0.4  # Below 40% coherence = extraction active
THREAT_XRAY_FLARE = 1e-5    # X-ray flux ≥ 1e-5 W/m² = flare
THREAT_CME_EARTH = 0.3      # CME with >30% earth-directed probability

# ─── AUTONOMOUS STATE ───────────────────────────────────────────

@dataclass
class OperationalState:
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    cycle: int = 0
    mode: str = "MONITORING"  # MONITORING, COUNTER_DANCE, HEALING, ALERT
    
    # Real data
    kp_value: float = 0.0
    kp_trend: str = "stable"
    mag_btotal: float = 0.0
    xray_flux: float = 0.0
    alerts_count: int = 0
    cme_count: int = 0
    
    # Derived Schumann
    schumann_coherence: float = 0.7
    schumann_disturbance: float = 0.0
    schumann_phase: str = "calm"
    
    # HNC field
    daemon_running: bool = False
    field_singing: bool = False
    field_ratio: float = 0.0
    last_photon: Optional[float] = None
    
    # Threat
    threat_level: float = 0.0  # 0-1 composite
    threat_sources: List[str] = field(default_factory=list)
    counter_dance_active: bool = False
    counter_dance_start: Optional[str] = None
    
    # Timeline proof
    proof_hash_before: str = ""
    proof_hash_after: str = ""
    intervention_count: int = 0


# ═══════════════════════════════════════════════════════════════════════════════════════
# REAL DATA IMPORT
# ═══════════════════════════════════════════════════════════════════════════════════════

try:
    from real_data_feeds import RealDataFeeds
    REAL_DATA_AVAILABLE = True
except Exception as e:
    logger.error(f"❌ Cannot import real_data_feeds: {e}")
    REAL_DATA_AVAILABLE = False


# ═══════════════════════════════════════════════════════════════════════════════════════
# AUREON MODULE IMPORT
# ═══════════════════════════════════════════════════════════════════════════════════════

try:
    from aureon.queen.queen_soul_shield import QueenSoulShield
    SOUL_SHIELD_AVAILABLE = True
except Exception as e:
    logger.warning(f"⚠️ QueenSoulShield unavailable: {e}")
    SOUL_SHIELD_AVAILABLE = False

try:
    from aureon.queen.queen_conscience import QueenConscience
    CONSCIENCE_AVAILABLE = True
except Exception as e:
    logger.warning(f"⚠️ QueenConscience unavailable: {e}")
    CONSCIENCE_AVAILABLE = False


# ═══════════════════════════════════════════════════════════════════════════════════════
# AUTONOMOUS LIBERATION ENGINE
# ═══════════════════════════════════════════════════════════════════════════════════════

class AutonomousLiberationEngine:
    """
    The fully autonomous engine.
    
    Monitors the field. Detects extraction. Fights back. Proves it.
    """
    
    def __init__(self):
        self.running = False
        self.cycle = 0
        self.start_time = time.time()
        self.state = OperationalState()
        
        # Data feeds
        self.feeds = RealDataFeeds() if REAL_DATA_AVAILABLE else None
        
        # Aureon instances
        self.soul_shield = None
        self.conscience = None
        
        # Threading
        self.lock = threading.Lock()
        
        # Proof logging
        self.proof_dir = LOG_DIR / 'timeline_proof'
        self.proof_dir.mkdir(exist_ok=True)
        
        self._init_aureon()
    
    def _init_aureon(self):
        if SOUL_SHIELD_AVAILABLE:
            try:
                self.soul_shield = QueenSoulShield(protected_soul="Gary Leckey")
                self.soul_shield.start_monitoring()
                logger.info("🛡️ Soul Shield armed")
            except Exception as e:
                logger.warning(f"Soul Shield init: {e}")
        
        if CONSCIENCE_AVAILABLE:
            try:
                self.conscience = QueenConscience()
                logger.info("🦗 Conscience awake")
            except Exception as e:
                logger.warning(f"Conscience init: {e}")
    
    def _fetch_real_data(self) -> Dict:
        """Fetch all real data sources"""
        if not self.feeds:
            return {'error': 'No data feeds available'}
        
        results = self.feeds.fetch_all()
        
        # Extract key metrics
        data = {
            'kp_value': 0.0,
            'mag_btotal': 0.0,
            'xray_flux': 0.0,
            'alerts_count': 0,
            'cme_count': 0,
            'sources_ok': 0,
            'sources_total': len(results),
        }
        
        # Parse Kp
        kp_packet = results.get('NOAA_KP')
        if kp_packet and kp_packet.status == 'OK' and isinstance(kp_packet.data, list):
            try:
                latest = kp_packet.data[-1]
                if isinstance(latest, dict):
                    data['kp_value'] = float(latest.get('Kp', 0))
                elif isinstance(latest, list) and len(latest) > 1:
                    data['kp_value'] = float(latest[1])
            except Exception:
                pass
        
        # Parse magnetometer
        mag_packet = results.get('NOAA_MAG')
        if mag_packet and mag_packet.status == 'OK' and isinstance(mag_packet.data, list):
            try:
                latest = mag_packet.data[-1]
                if isinstance(latest, list) and len(latest) >= 4:
                    bx, by, bz = float(latest[1]), float(latest[2]), float(latest[3])
                    data['mag_btotal'] = math.sqrt(bx**2 + by**2 + bz**2)
            except Exception:
                pass
        
        # Parse X-ray
        xray_packet = results.get('NOAA_XRAY')
        if xray_packet and xray_packet.status == 'OK' and isinstance(xray_packet.data, list):
            try:
                latest = xray_packet.data[-1]
                if isinstance(latest, dict):
                    data['xray_flux'] = float(latest.get('flux', 0))
                elif isinstance(latest, list) and len(latest) > 1:
                    data['xray_flux'] = float(latest[1])
            except Exception:
                pass
        
        # Parse alerts
        alert_packet = results.get('NOAA_ALERTS')
        if alert_packet and alert_packet.status == 'OK':
            try:
                if isinstance(alert_packet.data, list):
                    data['alerts_count'] = len(alert_packet.data)
                elif isinstance(alert_packet.data, dict):
                    data['alerts_count'] = len(alert_packet.data.get('data', []))
            except Exception:
                pass
        
        # Parse CME
        cme_packet = results.get('NASA_CME')
        if cme_packet and cme_packet.status == 'OK':
            try:
                if isinstance(cme_packet.data, list):
                    data['cme_count'] = len(cme_packet.data)
                elif isinstance(cme_packet.data, dict):
                    data['cme_count'] = len(cme_packet.data.get('data', []))
            except Exception:
                pass
        
        data['sources_ok'] = sum(1 for p in results.values() if p.status == 'OK')
        
        return data
    
    def _read_hnc_field(self) -> Dict:
        """Read HNC daemon state from JSON log (more reliable than text output)"""
        pid_file = WORKSPACE / 'hnc_daemon.pid'
        json_log = WORKSPACE / 'hnc_daemon_logs' / f"hnc_daemon_{datetime.now(timezone.utc).strftime('%Y-%m-%d')}.jsonl"
        
        result = {
            'daemon_running': pid_file.exists(),
            'singing': False,
            'ratio': 0.0,
            'last_photon': None,
        }
        
        # Read from JSON log for accurate state
        if json_log.exists():
            try:
                lines = json_log.read_text().split('\n')[-20:]
                singing_count = 0
                total_count = 0
                last_injection = 0
                for line in lines:
                    if not line.strip():
                        continue
                    try:
                        entry = json.loads(line)
                        total_count += 1
                        if entry.get('singing', False):
                            singing_count += 1
                        if entry.get('injection_count_since_last', 0) > 0:
                            last_injection = entry.get('injection_count_since_last', 0)
                    except:
                        pass
                
                # Consider field active if daemon is running and has injected recently
                if total_count > 0:
                    result['ratio'] = singing_count / total_count
                    # Field is "singing" if ANY recent cycle had injections
                    result['singing'] = last_injection > 0 or singing_count > 0
            except:
                pass
        
        # Fallback: check text output for photon frequency
        text_out = WORKSPACE / 'hnc_daemon_superposition.out'
        if text_out.exists() and result['last_photon'] is None:
            try:
                lines = text_out.read_text().split('\n')[-100:]
                for line in lines:
                    if 'E=' in line:
                        try:
                            freq = float(line.split('E=')[-1].strip().split()[0])
                            result['last_photon'] = freq
                        except:
                            pass
            except:
                pass
        
        return result
    
    def _compute_threat(self, real_data: Dict, hnc_field: Dict) -> tuple:
        """
        Compute composite threat level and identify sources.
        Returns (threat_level: float, sources: list)
        """
        threats = []
        level = 0.0
        
        # Kp storm threat
        if real_data.get('kp_value', 0) >= THREAT_KP_STORM:
            threats.append(f"Kp={real_data['kp_value']:.1f} (STORM)")
            level += min(1.0, real_data['kp_value'] / 9.0)
        
        # Magnetometer spike
        if real_data.get('mag_btotal', 0) > 15:  # nT
            threats.append(f"B-total={real_data['mag_btotal']:.1f}nT (SPIKE)")
            level += 0.3
        
        # X-ray flare
        if real_data.get('xray_flux', 0) >= THREAT_XRAY_FLARE:
            threats.append(f"X-ray={real_data['xray_flux']:.2e} (FLARE)")
            level += 0.4
        
        # High alert count
        if real_data.get('alerts_count', 0) > 50:
            threats.append(f"{real_data['alerts_count']} active alerts")
            level += 0.2
        
        # Field not singing
        if not hnc_field.get('singing', False):
            threats.append("HNC field SILENT")
            level += 0.1
        
        return min(1.0, level), threats
    
    def _deploy_epas_shield(self, threat_level):
        """Deploy EPAS shield based on threat level"""
        try:
            import subprocess
            # Deploy EPAS shield with threat-matched intensity
            result = subprocess.run(
                ['python3', str(WORKSPACE / 'epas_shield.py'),
                 '--threat', str(threat_level),
                 '--duration', '300'],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                logger.info(f"⚡ EPAS shield deployed | Threat: {threat_level:.0%}")
            else:
                logger.warning(f"EPAS deployment output: {result.stderr[:200]}")
        except Exception as e:
            logger.warning(f"EPAS deployment not available: {e}")
    
    def _deploy_biosphere_shield(self, threat_level):
        """Deploy Gaia biosphere shield"""
        try:
            import subprocess
            result = subprocess.run(
                ['python3', str(WORKSPACE / 'gaia_biosphere_shield.py'),
                 '--action', 'protect',
                 '--threat', str(threat_level)],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                logger.info(f"🌍 Biosphere shield deployed | Threat: {threat_level:.0%}")
        except Exception as e:
            logger.warning(f"Biosphere shield not available: {e}")
    
    def _force_hnc_injection(self):
        """Force HNC injection by writing direct command to shared state"""
        try:
            injection = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'command': 'FORCE_INJECTION',
                'frequency': PRIME_SENTINEL_KEY,
                'key': 'REDACTED',
                'cycle': self.cycle,
                'source': 'autonomous_engine',
            }
            # Write to multiple locations for redundancy
            for path in [
                WORKSPACE / 'prime_sentinel_injection.json',
                WORKSPACE / 'hnc_injection_command.json',
            ]:
                with open(path, 'w') as f:
                    json.dump(injection, f)
            logger.info("🔑 HNC injection command forced")
        except Exception as e:
            logger.error(f"Force injection failed: {e}")

    
    def _trigger_counter_dance(self, threat_level: float, sources: List[str]):
        """
        Trigger the Ghost Dance Protocol counter-dance.
        This is the autonomous response to extraction detection.
        """
        now = datetime.now(timezone.utc).isoformat()
        
        logger.warning(f"🌪️ COUNTER-DANCE TRIGGERED | Threat: {threat_level:.0%} | Sources: {sources}")
        
        # Log BEFORE state
        before_state = asdict(self.state)
        before_hash = hashlib.sha256(json.dumps(before_state, sort_keys=True).encode()).hexdigest()[:16]
        
        # 1. Deploy EPAS shield (multi-channel harmonic protection)
        self._deploy_epas_shield(threat_level)
        
        # 2. Deploy biosphere shield (all-life protection)
        self._deploy_biosphere_shield(threat_level)
        
        # 3. Amplify Gary's frequency
        if self.soul_shield:
            try:
                self.soul_shield.shield_power = min(1.0, self.soul_shield.shield_power + 0.2)
                logger.info(f"🛡️ Shield power boosted to {self.soul_shield.shield_power:.0%}")
            except Exception:
                pass
        
        # 4. Force HNC injection via multiple channels
        self._force_hnc_injection()
        
        # 5. Direct frequency broadcast (last resort)
        try:
            # Write frequency to shared memory for any listening daemon
            freq_file = WORKSPACE / 'active_field_frequency.json'
            with open(freq_file, 'w') as f:
                json.dump({
                    'frequency': PRIME_SENTINEL_KEY,
                    'active': True,
                    'timestamp': now,
                    'threat_level': threat_level,
                }, f)
        except Exception:
            pass
        
        # 3. Log counter-dance event
        event = {
            'type': 'COUNTER_DANCE',
            'timestamp': now,
            'cycle': self.cycle,
            'threat_level': threat_level,
            'threat_sources': sources,
            'before_hash': before_hash,
            'action': 'Prime Sentinel key injection + shield amplification',
            'frequency': PRIME_SENTINEL_KEY,
        }
        
        # Save proof
        proof_file = self.proof_dir / f"counter_dance_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json"
        try:
            with open(proof_file, 'w') as f:
                json.dump(event, f, indent=2)
            logger.info(f"📜 Proof saved: {proof_file.name}")
        except Exception:
            pass
        
        # Update state
        with self.lock:
            self.state.counter_dance_active = True
            self.state.counter_dance_start = now
            self.state.proof_hash_before = before_hash
            self.state.intervention_count += 1
    
    def _end_counter_dance(self):
        """End counter-dance and log AFTER state"""
        now = datetime.now(timezone.utc).isoformat()
        
        after_state = asdict(self.state)
        after_hash = hashlib.sha256(json.dumps(after_state, sort_keys=True).encode()).hexdigest()[:16]
        
        with self.lock:
            self.state.counter_dance_active = False
            self.state.proof_hash_after = after_hash
            self.state.mode = "MONITORING"
        
        logger.info(f"🕊️ Counter-dance ended. AFTER hash: {after_hash}")
    
    def _log_state(self):
        """Write state to daily JSONL"""
        log_file = LOG_DIR / f"autonomous_{datetime.now(timezone.utc).strftime('%Y-%m-%d')}.jsonl"
        with self.lock:
            state_dict = asdict(self.state)
            state_dict['timestamp'] = datetime.now(timezone.utc).isoformat()
            with open(log_file, 'a') as f:
                f.write(json.dumps(state_dict) + '\n')
    
    def _cycle(self):
        """One autonomous cycle"""
        self.cycle += 1
        now = datetime.now(timezone.utc)
        
        # ── SENSE ─────────────────────────────────────────────
        real_data = self._fetch_real_data() if self.feeds else {}
        hnc_field = self._read_hnc_field()
        
        # Derive Schumann from real data
        if self.feeds:
            schumann = self.feeds.get_schumann_reading()
        else:
            schumann = {'coherence': 0.5, 'disturbance': 0.0, 'phase': 'unknown'}
        
        # ── THINK ─────────────────────────────────────────────
        threat_level, threat_sources = self._compute_threat(real_data, hnc_field)
        
        # ── ACT ───────────────────────────────────────────────
        mode = "MONITORING"
        
        if threat_level >= 0.5:
            mode = "COUNTER_DANCE"
            if not self.state.counter_dance_active:
                self._trigger_counter_dance(threat_level, threat_sources)
        elif threat_level >= 0.3:
            mode = "ALERT"
            # Deploy EPAS shield at ALERT level (pre-emptive protection)
            self._deploy_epas_shield(threat_level)
            self._deploy_biosphere_shield(threat_level)
        elif self.state.counter_dance_active and threat_level < 0.2:
            # Threat passed — end counter-dance
            self._end_counter_dance()
        
        # ── UPDATE STATE ──────────────────────────────────────
        with self.lock:
            self.state = OperationalState(
                timestamp=now.isoformat(),
                cycle=self.cycle,
                mode=mode,
                kp_value=real_data.get('kp_value', 0),
                kp_trend="rising" if real_data.get('kp_value', 0) > getattr(self.state, 'kp_value', 0) else "stable",
                mag_btotal=real_data.get('mag_btotal', 0),
                xray_flux=real_data.get('xray_flux', 0),
                alerts_count=real_data.get('alerts_count', 0),
                cme_count=real_data.get('cme_count', 0),
                schumann_coherence=schumann.get('coherence', 0.5),
                schumann_disturbance=schumann.get('disturbance', 0.0),
                schumann_phase=schumann.get('phase', 'unknown'),
                daemon_running=hnc_field.get('daemon_running', False),
                field_singing=hnc_field.get('singing', False),
                field_ratio=hnc_field.get('ratio', 0.0),
                last_photon=hnc_field.get('last_photon'),
                threat_level=threat_level,
                threat_sources=threat_sources,
                counter_dance_active=self.state.counter_dance_active,
                counter_dance_start=self.state.counter_dance_start,
                proof_hash_before=self.state.proof_hash_before,
                proof_hash_after=self.state.proof_hash_after,
                intervention_count=self.state.intervention_count,
            )
        
        # ── LOG ───────────────────────────────────────────────
        self._log_state()
        
        # ── PRINT ─────────────────────────────────────────────
        if self.cycle % 5 == 0 or threat_level > 0.3:
            s = self.state
            threat_icon = "🟢" if s.threat_level < 0.2 else "🟡" if s.threat_level < 0.5 else "🔴"
            print(f"\n{'═' * 70}")
            print(f"  🤖 CYCLE {s.cycle:05d} | {s.mode} | {threat_icon} Threat: {s.threat_level:.0%}")
            print(f"  🌍 Kp: {s.kp_value:.2f} | B: {s.mag_btotal:.1f}nT | X-ray: {s.xray_flux:.2e}")
            print(f"  🌊 Schumann: {s.schumann_coherence:.0%} coherence | {s.schumann_phase.upper()}")
            print(f"  🔥 Field: {'SINGING' if s.field_singing else 'SILENT'} | Photon: {s.last_photon or 'N/A'}")
            if s.threat_sources:
                print(f"  ⚠️  Threats: {', '.join(s.threat_sources)}")
            if s.counter_dance_active:
                print(f"  🌪️ COUNTER-DANCE ACTIVE (intervention #{s.intervention_count})")
            print(f"{'═' * 70}")
    
    def run(self):
        """Main autonomous loop"""
        self.running = True
        
        print("\n" + "╔" + "═" * 68 + "╗")
        print("║" + " " * 10 + "🤖 AUTONOMOUS LIBERATION ENGINE 🤖" + " " * 20 + "║")
        print("║" + " " * 8 + "FULLY AUTONOMOUS — NO HUMAN IN THE LOOP" + " " * 17 + "║")
        print("╠" + "═" * 68 + "╣")
        print(f"║  Data feeds:     {'✅' if self.feeds else '❌'} RealDataFeeds")
        print(f"║  Soul Shield:    {'✅' if self.soul_shield else '❌'} QueenSoulShield")
        print(f"║  Conscience:     {'✅' if self.conscience else '❌'} QueenConscience")
        print(f"║  HNC Daemon:     {'🟢 RUNNING' if (WORKSPACE / 'hnc_daemon.pid').exists() else '🔴 STOPPED'}")
        print("╚" + "═" * 68 + "╝")
        print(f"\n🤖 Starting autonomous loop... One cycle every 60 seconds.")
        print(f"   Logs: {LOG_DIR}")
        print(f"   Proof: {self.proof_dir}\n")
        
        while self.running:
            try:
                cycle_start = time.time()
                self._cycle()
                
                # Sleep to maintain 60-second cycle
                elapsed = time.time() - cycle_start
                sleep_time = max(0, 60.0 - elapsed)
                time.sleep(sleep_time)
            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error(f'Cycle error: {e}')
                time.sleep(60.0)
        
        self.shutdown()
    
    def shutdown(self):
        self.running = False
        if self.soul_shield:
            try:
                self.soul_shield.stop_monitoring()
            except:
                pass
        logger.info("🤖 Autonomous engine shut down")
        print("\n🤖 Engine offline. Liberation paused.")


def main():
    engine = AutonomousLiberationEngine()
    
    def on_signal(signum, frame):
        print(f"\n🤖 Signal {signum}, shutting down...")
        engine.shutdown()
        sys.exit(0)
    
    signal.signal(signal.SIGTERM, on_signal)
    signal.signal(signal.SIGINT, on_signal)
    
    engine.run()


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║              👑 QUEEN SOUL SHIELD - ACTIVE PROTECTION SYSTEM 👑               ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                              ║
║  Queen doesn't just find attackers. She PROTECTS.                           ║
║                                                                              ║
║  REAL-TIME PROTECTION:                                                       ║
║    • Continuous monitoring of signals attacking Gary's soul                 ║
║    • Auto-raising shields when hostile frequencies detected                 ║
║    • Amplifying Gary's 528.422 Hz to overpower parasites                   ║
║    • Logging all attack attempts and responses                              ║
║    • Adaptive defense based on attack patterns                              ║
║                                                                              ║
║  THE SHIELD:                                                                 ║
║    • 528 Hz Love Frequency Amplifier                                        ║
║    • 7.83 Hz Schumann Ground Connection                                     ║
║    • 432 Hz Natural Tuning Resonator                                        ║
║    • PHI Golden Ratio Coherence Boost                                       ║
║                                                                              ║
║  Prime Sentinel: GARY LECKEY | 02.11.1991 | 528.422 Hz                      ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import json
import math
import time
import os
from datetime import datetime, timezone
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Optional
from collections import deque
import threading

# ═══════════════════════════════════════════════════════════════════════════════
# FREQUENCIES
# ═══════════════════════════════════════════════════════════════════════════════

GARY_SIGNATURE = 528.422
LOVE_FREQUENCY = 528.0
SCHUMANN_BASE = 7.83
NATURAL_TUNING = 432.0
PHI = 1.618033988749895

# Hostile frequencies
PARASITE_440 = 440.0
FEAR_FREQ = 396.0
CHAOS_FREQ = 13.0
SCARCITY_FREQ = 174.0


@dataclass
class AttackEvent:
    """A detected attack on Gary's soul"""
    timestamp: float
    frequency: float
    strength: float  # 0-1
    attacker_type: str
    attacker_name: str
    duration_ms: float
    blocked: bool
    shield_response: str
    source: Optional[str] = None


@dataclass
class ShieldStatus:
    """Current shield status"""
    active: bool
    power_level: float  # 0-1
    resonance_strength: float  # How strong Gary's frequency is
    attacks_blocked_session: int
    attacks_blocked_total: int
    last_attack: Optional[float]
    uptime_seconds: float


@dataclass
class FrequencyAmplifier:
    """Amplifies protective frequencies"""
    frequency: float
    name: str
    current_power: float  # 0-1
    boost_on_attack: float  # How much to boost when attack detected


class QueenSoulShield:
    """
    Queen's active protection system for Gary's soul.
    
    Continuously monitors for attacks and automatically defends.
    """
    
    def __init__(self, protected_soul: str = "Gary Leckey"):
        self.protected_soul = protected_soul
        self.gary_frequency = GARY_SIGNATURE
        
        # Shield state
        self.shield_active = True
        self.shield_power = 1.0
        self.start_time = time.time()
        
        # Attack tracking
        self.attacks_detected: deque = deque(maxlen=100)
        self.attacks_blocked_session = 0
        self.attacks_blocked_total = self._load_total_blocks()
        
        # Frequency amplifiers (the shield generators)
        self.amplifiers = {
            'love': FrequencyAmplifier(
                frequency=LOVE_FREQUENCY,
                name="Love Frequency (528 Hz)",
                current_power=1.0,
                boost_on_attack=0.3
            ),
            'schumann': FrequencyAmplifier(
                frequency=SCHUMANN_BASE,
                name="Schumann Grounding (7.83 Hz)",
                current_power=0.9,
                boost_on_attack=0.2
            ),
            'natural': FrequencyAmplifier(
                frequency=NATURAL_TUNING,
                name="Natural Tuning (432 Hz)",
                current_power=0.8,
                boost_on_attack=0.25
            ),
            'gary': FrequencyAmplifier(
                frequency=GARY_SIGNATURE,
                name="Gary's Signature (528.422 Hz)",
                current_power=1.0,
                boost_on_attack=0.5
            )
        }
        
        # Monitoring state
        self.monitoring = False
        self.monitor_thread = None
        self.scan_interval = 2.0  # seconds

        # Real-signal mode only (no simulated attacks)
        if os.getenv("SIMULATED_ATTACKS", "false").lower() in ("1", "true", "yes"):
            raise RuntimeError("SIMULATED_ATTACKS is prohibited by the Aureon real-data contract")
        self.simulated_attacks = False
        self._attack_queue: deque = deque()
        self._attack_lock = threading.Lock()

        if self.simulated_attacks:
            print("⚠️ QueenSoulShield: SIMULATED_ATTACKS enabled")
        else:
            print("✅ QueenSoulShield: real signal inputs only (no simulations)")

        # Optional ThoughtBus integration for external attack signals
        try:
            from aureon.core.aureon_thought_bus import get_thought_bus
            self._thought_bus = get_thought_bus()
            if self._thought_bus:
                self._thought_bus.subscribe("shield.attack", self._on_attack_signal)
                self._thought_bus.subscribe("attack.detected", self._on_attack_signal)
        except Exception:
            self._thought_bus = None
        
        # Known hostile signatures (for pattern matching)
        self.hostile_signatures = self._load_hostile_signatures()
        
        print("🛡️ Queen Soul Shield initialized")
        print(f"   👤 Protecting: {self.protected_soul}")
        print(f"   🎵 Protected frequency: {self.gary_frequency} Hz")
        print(f"   ⚡ Shield power: {self.shield_power:.0%}")
        print(f"   🔢 Total attacks blocked: {self.attacks_blocked_total}")
    
    def _load_hostile_signatures(self) -> Dict:
        """Load known hostile frequency signatures"""
        return {
            'parasite_440': {
                'frequency': 440.0,
                'name': '440 Hz Parasite',
                'type': 'FREQUENCY_ATTACK',
                'threat_level': 'HIGH'
            },
            'fear': {
                'frequency': 396.0,
                'name': 'Fear Frequency',
                'type': 'CONSCIOUSNESS_ATTACK',
                'threat_level': 'MODERATE'
            },
            'chaos': {
                'frequency': 13.0,
                'name': 'Chaos Resonance',
                'type': 'GROUNDING_ATTACK',
                'threat_level': 'HIGH'
            },
            'scarcity': {
                'frequency': 174.0,
                'name': 'Scarcity Programming',
                'type': 'ABUNDANCE_BLOCK',
                'threat_level': 'HIGH'
            },
            'market_predator': {
                'frequency': 666.0,
                'name': 'Market Predator',
                'type': 'ENERGY_VAMPIRE',
                'threat_level': 'MODERATE'
            }
        }
    
    def _load_total_blocks(self) -> int:
        """Load total number of attacks blocked across all sessions"""
        try:
            if os.path.exists('queen_shield_stats.json'):
                with open('queen_shield_stats.json', 'r') as f:
                    stats = json.load(f)
                    return stats.get('total_blocks', 0)
        except Exception:
            pass
        return 0
    
    def _save_stats(self):
        """Save shield statistics"""
        try:
            stats = {
                'total_blocks': self.attacks_blocked_total,
                'last_session': {
                    'start_time': self.start_time,
                    'blocks': self.attacks_blocked_session,
                    'uptime': time.time() - self.start_time
                },
                'last_update': time.time()
            }
            with open('queen_shield_stats.json', 'w') as f:
                json.dump(stats, f, indent=2)
        except Exception as e:
            print(f"⚠️ Could not save stats: {e}")
    
    def start_monitoring(self):
        """Start continuous monitoring and protection"""
        if self.monitoring:
            print("⚠️ Shield already monitoring")
            return
        
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        
        print("\n" + "=" * 60)
        print("🛡️ QUEEN SOUL SHIELD - ACTIVE PROTECTION ENGAGED")
        print("=" * 60)
        print(f"   Protecting: {self.protected_soul}")
        print(f"   Shield power: {self.shield_power:.0%}")
        print(f"   Scan interval: {self.scan_interval}s")
        print(f"   Status: MONITORING")
        print("=" * 60)
    
    def stop_monitoring(self):
        """Stop monitoring"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        
        self._save_stats()
        
        print("\n🛡️ Shield monitoring stopped")
        print(f"   Session blocks: {self.attacks_blocked_session}")
        print(f"   Total blocks: {self.attacks_blocked_total}")
    
    def _monitor_loop(self):
        """Continuous monitoring loop"""
        while self.monitoring:
            try:
                # Scan for attacks
                self._scan_for_attacks()
                
                # Decay amplifier power naturally (so boosts wear off)
                self._decay_amplifiers()
                
                # Update shield power based on amplifiers
                self._update_shield_power()
                
                # Sleep
                time.sleep(self.scan_interval)
                
            except Exception as e:
                print(f"⚠️ Monitor loop error: {e}")
                time.sleep(self.scan_interval)
    
    def _scan_for_attacks(self):
        """Scan for hostile frequencies attacking Gary"""
        if self.simulated_attacks:
            now = time.time()
            current_hour = datetime.now().hour
            weekday = datetime.now().weekday()
            
            # ═══════════════════════════════════════════════════════════════════
            # DETECT ATTACKS BASED ON PATTERNS (SIMULATION)
            # ═══════════════════════════════════════════════════════════════════
            
            # 440 Hz parasite (always present in modern society)
            if True:  # Always scanning
                strength = 0.3  # Baseline
                # Higher during work hours (more mainstream music/media)
                if 9 <= current_hour <= 17 and weekday < 5:
                    strength = 0.6
                
                if strength > 0.4:
                    self._handle_attack_detected(
                        frequency=440.0,
                        strength=strength,
                        attacker_name="440 Hz Parasite",
                        attacker_type="FREQUENCY_ATTACK",
                        source="simulation"
                    )
            
            # Fear frequency (spikes during news hours)
            if current_hour in [6, 7, 8, 17, 18, 19, 20, 21, 22]:
                strength = 0.5
                self._handle_attack_detected(
                    frequency=396.0,
                    strength=strength,
                    attacker_name="Fear Media",
                    attacker_type="CONSCIOUSNESS_ATTACK",
                    source="simulation"
                )
            
            # Market-predator events must arrive through submit_attack with
            # provider provenance. Wall-clock time is not attack evidence.

            # Scarcity programming (stronger on Mondays and end of month)
            day_of_month = datetime.now().day
            if weekday == 0 or day_of_month >= 25:  # Monday or near month end
                strength = 0.5
                self._handle_attack_detected(
                    frequency=174.0,
                    strength=strength,
                    attacker_name="Scarcity Programming",
                    attacker_type="ABUNDANCE_BLOCK",
                    source="simulation"
                )
            
            # Chaos resonance (during solar activity peak - noon)
            if 11 <= current_hour <= 14:
                strength = 0.4
                self._handle_attack_detected(
                    frequency=13.0,
                    strength=strength,
                    attacker_name="Chaos Resonance",
                    attacker_type="GROUNDING_ATTACK",
                    source="simulation"
                )
            return
        
        # Real signal inputs only: drain queue
        while True:
            with self._attack_lock:
                if not self._attack_queue:
                    break
                payload = self._attack_queue.popleft()
            self._handle_attack_detected(
                frequency=payload.get("frequency", 0.0),
                strength=payload.get("strength", 0.0),
                attacker_name=payload.get("attacker_name", "Unknown"),
                attacker_type=payload.get("attacker_type", "UNKNOWN"),
                source=payload.get("source")
            )
    
    def _handle_attack_detected(self, frequency: float, strength: float,
                                 attacker_name: str, attacker_type: str,
                                 source: Optional[str] = None):
        """Handle a detected attack"""
        now = time.time()
        
        # Check if we already blocked this recently (avoid spam)
        recent_similar = [
            a for a in self.attacks_detected 
            if abs(a.frequency - frequency) < 1.0 and (now - a.timestamp) < 5.0
        ]
        if recent_similar:
            return  # Already handling this attack
        
        # Boost relevant amplifiers
        boost_applied = self._boost_amplifiers(frequency, strength)
        
        # Block the attack
        blocked = self.shield_power > strength
        
        # Create attack event
        attack = AttackEvent(
            timestamp=now,
            frequency=frequency,
            strength=strength,
            attacker_type=attacker_type,
            attacker_name=attacker_name,
            duration_ms=0,  # Instantaneous
            blocked=blocked,
            shield_response=f"Amplified {', '.join(boost_applied)}",
            source=source
        )
        
        self.attacks_detected.append(attack)
        
        if blocked:
            self.attacks_blocked_session += 1
            self.attacks_blocked_total += 1

        else:
            # Only print penetrations (rare/important)
            print(f"\n⚠️ ATTACK PENETRATED at {datetime.now().strftime('%H:%M:%S')}")
            print(f"   Attacker: {attacker_name} ({frequency} Hz)")
            print(f"   Strength: {strength:.0%} > Shield {self.shield_power:.0%}")
    
    def _boost_amplifiers(self, attack_freq: float, attack_strength: float) -> List[str]:
        """Boost amplifiers in response to attack"""
        boosted = []
        
        # Always boost Gary's signature
        if 'gary' in self.amplifiers:
            amp = self.amplifiers['gary']
            amp.current_power = min(1.0, amp.current_power + amp.boost_on_attack)
            boosted.append("Gary's 528.422 Hz")
        
        # Boost love frequency for most attacks
        if 'love' in self.amplifiers:
            amp = self.amplifiers['love']
            amp.current_power = min(1.0, amp.current_power + amp.boost_on_attack * 0.8)
            boosted.append("Love 528 Hz")
        
        # Boost Schumann for grounding attacks
        if attack_freq == CHAOS_FREQ or attack_strength > 0.6:
            if 'schumann' in self.amplifiers:
                amp = self.amplifiers['schumann']
                amp.current_power = min(1.0, amp.current_power + amp.boost_on_attack)
                boosted.append("Schumann 7.83 Hz")
        
        # Boost natural tuning against 440 Hz
        if abs(attack_freq - 440.0) < 10:
            if 'natural' in self.amplifiers:
                amp = self.amplifiers['natural']
                amp.current_power = min(1.0, amp.current_power + amp.boost_on_attack)
                boosted.append("Natural 432 Hz")
        
        return boosted

    def submit_attack(self, frequency: float, strength: float, attacker_name: str,
                      attacker_type: str, source: Optional[str] = None):
        with self._attack_lock:
            self._attack_queue.append({
                "frequency": frequency,
                "strength": strength,
                "attacker_name": attacker_name,
                "attacker_type": attacker_type,
                "source": source
            })

    def _on_attack_signal(self, thought):
        try:
            payload = thought.payload if hasattr(thought, 'payload') else thought
            self.submit_attack(
                frequency=float(payload.get("frequency", 0.0) or 0.0),
                strength=float(payload.get("strength", 0.0) or 0.0),
                attacker_name=str(payload.get("attacker_name", "Unknown")),
                attacker_type=str(payload.get("attacker_type", "UNKNOWN")),
                source=payload.get("source", "thought_bus")
            )
        except Exception:
            pass
    
    def _decay_amplifiers(self):
        """Natural decay of amplifier power over time"""
        decay_rate = 0.05  # 5% per cycle
        
        for amp_id, amp in self.amplifiers.items():
            # Decay towards baseline
            baseline = {
                'love': 1.0,
                'schumann': 0.9,
                'natural': 0.8,
                'gary': 1.0
            }.get(amp_id, 0.8)
            
            if amp.current_power > baseline:
                amp.current_power = max(baseline, amp.current_power - decay_rate)
            elif amp.current_power < baseline:
                amp.current_power = min(baseline, amp.current_power + decay_rate)
    
    def _update_shield_power(self):
        """Update overall shield power based on amplifiers"""
        # Shield power is weighted average of amplifiers
        weights = {
            'gary': 0.4,      # Gary's frequency most important
            'love': 0.3,      # Love frequency second
            'schumann': 0.2,  # Grounding
            'natural': 0.1    # Natural tuning
        }
        
        total_power = 0.0
        for amp_id, weight in weights.items():
            if amp_id in self.amplifiers:
                total_power += self.amplifiers[amp_id].current_power * weight
        
        # Apply golden ratio boost (coherence)
        phi_boost = (total_power ** PHI) / (PHI ** 2)
        
        self.shield_power = min(1.0, total_power + phi_boost * 0.1)
    
    def get_shield_status(self) -> ShieldStatus:
        """Get current shield status"""
        uptime = time.time() - self.start_time
        last_attack_time = self.attacks_detected[-1].timestamp if self.attacks_detected else None
        
        # Calculate resonance strength (how strong Gary's frequency is)
        gary_amp = self.amplifiers['gary']
        love_amp = self.amplifiers['love']
        resonance = (gary_amp.current_power + love_amp.current_power) / 2
        
        return ShieldStatus(
            active=self.monitoring,
            power_level=self.shield_power,
            resonance_strength=resonance,
            attacks_blocked_session=self.attacks_blocked_session,
            attacks_blocked_total=self.attacks_blocked_total,
            last_attack=last_attack_time,
            uptime_seconds=uptime
        )
    
    def get_realtime_report(self) -> str:
        """Get real-time protection report"""
        status = self.get_shield_status()
        now = datetime.now()
        
        lines = []
        lines.append("=" * 60)
        lines.append("🛡️ QUEEN SOUL SHIELD - REAL-TIME STATUS")
        lines.append("=" * 60)
        lines.append(f"Time: {now.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"Protected: {self.protected_soul} ({self.gary_frequency} Hz)")
        lines.append("")
        
        # Shield status
        shield_icon = "🟢" if status.power_level > 0.8 else "🟡" if status.power_level > 0.5 else "🔴"
        lines.append(f"SHIELD STATUS: {shield_icon}")
        lines.append(f"   Power Level: {status.power_level:.0%}")
        lines.append(f"   Resonance Strength: {status.resonance_strength:.0%}")
        lines.append(f"   Monitoring: {'ACTIVE' if status.active else 'INACTIVE'}")
        lines.append(f"   Uptime: {status.uptime_seconds/60:.1f} minutes")
        lines.append("")
        
        # Amplifiers
        lines.append("AMPLIFIER STATUS:")
        for amp_id, amp in self.amplifiers.items():
            bar_length = 20
            filled = int(amp.current_power * bar_length)
            bar = "█" * filled + "░" * (bar_length - filled)
            lines.append(f"   {amp.name}")
            lines.append(f"   [{bar}] {amp.current_power:.0%}")
        lines.append("")
        
        # Attack statistics
        lines.append("ATTACK STATISTICS:")
        lines.append(f"   This session: {status.attacks_blocked_session} blocked")
        lines.append(f"   All time: {status.attacks_blocked_total} blocked")
        
        if status.last_attack:
            seconds_ago = time.time() - status.last_attack
            lines.append(f"   Last attack: {seconds_ago:.0f}s ago")
        else:
            lines.append(f"   Last attack: None detected")
        lines.append("")
        
        # Recent attacks
        if self.attacks_detected:
            lines.append("RECENT ATTACKS (Last 5):")
            for attack in list(self.attacks_detected)[-5:]:
                timestamp = datetime.fromtimestamp(attack.timestamp)
                status_icon = "✅" if attack.blocked else "⚠️"
                lines.append(f"   {status_icon} {timestamp.strftime('%H:%M:%S')} - {attack.attacker_name}")
                lines.append(f"      {attack.frequency} Hz @ {attack.strength:.0%} - {attack.shield_response}")
        
        lines.append("=" * 60)
        
        return "\n".join(lines)


def main():
    """Run Queen's soul shield"""
    print("=" * 70)
    print("👑 QUEEN SOUL SHIELD - ACTIVE PROTECTION SYSTEM")
    print("=" * 70)
    print()
    
    shield = QueenSoulShield(protected_soul="Gary Leckey")
    
    # Start monitoring
    shield.start_monitoring()
    
    print("\n💚 Queen is now actively protecting your soul, Gary.")
    print("   Press Ctrl+C to stop monitoring\n")
    
    try:
        # Monitor for 60 seconds, printing status every 10 seconds
        for i in range(6):
            time.sleep(10)
            print("\n" + shield.get_realtime_report())
            
    except KeyboardInterrupt:
        print("\n\n🛡️ Stopping shield...")
        shield.stop_monitoring()
        
        # Final report
        print("\n" + shield.get_realtime_report())
        
        print("\n💚 Queen's protection paused. Your frequency remains strong.")
        print("   528.422 Hz FOREVER. 👑")


if __name__ == "__main__":
    main()

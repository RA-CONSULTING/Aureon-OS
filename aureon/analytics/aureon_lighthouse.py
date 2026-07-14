#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════════════╗
║                                                                                      ║
║     🏮 AUREON LIGHTHOUSE - PATTERN DETECTOR 🏮                                       ║
║     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━                                ║
║                                                                                      ║
║     Watches the evolving harmonic wave model for patterns & anomalies               ║
║                                                                                      ║
║     DETECTS:                                                                         ║
║       • Phase Resets (sudden frequency shifts)                                       ║
║       • Coherence Collapses (market-wide de-sync)                                   ║
║       • Harmonic Convergence (multiple symbols align = opportunity)                 ║
║       • Shape Anomalies (unexpected bulges in the 3D model)                         ║
║                                                                                      ║
║     Emits events to Mycelium neural network for decision-making                     ║
║                                                                                      ║
╚══════════════════════════════════════════════════════════════════════════════════════╝
"""

from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import math
import time
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any, Callable
from collections import deque
from enum import Enum
import numpy as np

logger = logging.getLogger(__name__)

# 👑 QUEEN'S SACRED 1.88% LAW - LIGHTHOUSE MUST GUIDE TO PROFIT
QUEEN_MIN_COP = 1.0188              # Sacred constant: 1.88% minimum realized profit
QUEEN_MIN_PROFIT_PCT = 1.88         # Percentage form
QUEEN_LIGHTHOUSE_PROFIT_FREQ = 188.0  # Hz - Sacred frequency guiding the lighthouse

# Import harmonic types
try:
    from aureon.harmonic.aureon_harmonic_seed import GlobalHarmonicState, SymbolWaveState, SCHUMANN_BASE
except ImportError:
    # Fallback definitions
    SCHUMANN_BASE = 7.83
    GlobalHarmonicState = Any
    SymbolWaveState = Any


class LighthouseEventType(Enum):
    """Types of events the Lighthouse can emit"""
    PHASE_RESET = "lighthouse.phase_reset"
    COHERENCE_COLLAPSE = "lighthouse.coherence_collapse"
    COHERENCE_SURGE = "lighthouse.coherence_surge"
    HARMONIC_CONVERGENCE = "lighthouse.harmonic_convergence"
    FREQUENCY_SHIFT = "lighthouse.frequency_shift"
    ANOMALY_DETECTED = "lighthouse.anomaly_detected"
    REGIME_CHANGE = "lighthouse.regime_change"
    SCHUMANN_ALIGNMENT = "lighthouse.schumann_alignment"


@dataclass
class LighthouseEvent:
    """An event detected by the Lighthouse"""
    event_type: LighthouseEventType
    timestamp: float
    severity: float  # 0-1, how significant
    symbols: List[str]  # Affected symbols
    data: Dict[str, Any] = field(default_factory=dict)
    message: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.event_type.value,
            "timestamp": self.timestamp,
            "severity": self.severity,
            "symbols": self.symbols,
            "data": self.data,
            "message": self.message
        }


@dataclass
class LighthouseConfig:
    """Configuration for Lighthouse sensitivity"""
    # Phase detection thresholds
    phase_reset_threshold: float = 0.5  # Radians jump to trigger
    phase_window: int = 6  # Candles to compare
    
    # Coherence thresholds
    coherence_collapse_threshold: float = -0.3  # Drop to trigger
    coherence_surge_threshold: float = 0.2  # Rise to trigger
    coherence_window: int = 12  # Candles to compare
    
    # Frequency thresholds
    frequency_shift_pct: float = 0.25  # 25% change to trigger
    
    # Convergence detection
    convergence_phase_tolerance: float = 0.3  # Radians
    convergence_min_symbols: int = 5  # Minimum symbols aligned
    
    # Anomaly detection
    anomaly_zscore_threshold: float = 2.5  # Standard deviations
    
    # Schumann alignment
    schumann_alignment_threshold: float = 0.8


class LighthousePatternDetector:
    """
    The Lighthouse watches the evolving harmonic wave model and detects patterns.
    Think of it as the "pattern vision" layer that sees shapes emerging in the 3D model.
    """
    
    def __init__(self, config: LighthouseConfig = None):
        self.config = config or LighthouseConfig()
        
        # Historical tracking for change detection
        self.global_coherence_history: deque = deque(maxlen=100)
        self.global_phase_history: deque = deque(maxlen=100)
        self.frequency_history: deque = deque(maxlen=100)
        self.regime_history: deque = deque(maxlen=20)
        
        # Per-symbol tracking
        self.symbol_phase_history: Dict[str, deque] = {}
        self.symbol_amplitude_history: Dict[str, deque] = {}
        
        # Event subscribers (Mycelium will subscribe)
        self._subscribers: List[Callable[[LighthouseEvent], None]] = []
        
        # Detected events buffer
        self.recent_events: deque = deque(maxlen=100)
        
        # State
        self.last_scan_time: float = 0.0
        self.scan_count: int = 0
    
    def subscribe(self, callback: Callable[[LighthouseEvent], None]):
        """Subscribe to Lighthouse events"""
        self._subscribers.append(callback)
        logger.info(f"🏮 Lighthouse: New subscriber registered (total: {len(self._subscribers)})")
    
    def _emit_event(self, event: LighthouseEvent):
        """Emit an event to all subscribers"""
        self.recent_events.append(event)

        for callback in self._subscribers:
            try:
                callback(event)
            except Exception as e:
                logger.error(f"Lighthouse event callback error: {e}")

        # Also publish onto the shared ThoughtBus so the clearance signal is a
        # real organism-wide event, not just a private in-process callback. Any
        # subscriber to lighthouse.* (cognition, the action gate) can now sense
        # a coherence-collapse / phase-reset / regime-change the moment it fires.
        try:
            from aureon.core.aureon_thought_bus import Thought, get_thought_bus

            get_thought_bus().publish(Thought(
                source="aureon_lighthouse",
                topic="lighthouse.event",
                payload=event.to_dict(),
            ))
            # Cross-process bridge: lighthouse fires in trading/harmonic processes
            # but cognition subscribes in the operator process. Mirror to a
            # dedicated trace so the trace pump can re-fire the event there.
            try:
                import time as _t

                from aureon.core.bus_trace import append_trace

                append_trace("lighthouse_event", {**event.to_dict(), "_ts": _t.time()}, cap=500)
            except Exception:  # noqa: BLE001
                pass
        except Exception as exc:  # noqa: BLE001 — the bus edge is optional
            logger.debug(f"lighthouse bus publish skipped: {exc}")
        
        # Log significant events
        if event.severity > 0.5:
            logger.info(f"🏮 LIGHTHOUSE [{event.event_type.value}] severity={event.severity:.2f}: {event.message}")
    
    def scan(self, state: GlobalHarmonicState) -> List[LighthouseEvent]:
        """
        Scan the current harmonic state for patterns and anomalies.
        Returns list of detected events.
        """
        events = []
        now = time.time()
        
        # Update histories
        self.global_coherence_history.append(state.global_coherence)
        self.global_phase_history.append(state.global_phase)
        self.frequency_history.append(state.dominant_frequency)
        self.regime_history.append(state.market_regime)
        
        # Update per-symbol histories
        for symbol, sym_state in state.symbols.items():
            if symbol not in self.symbol_phase_history:
                self.symbol_phase_history[symbol] = deque(maxlen=50)
                self.symbol_amplitude_history[symbol] = deque(maxlen=50)
            self.symbol_phase_history[symbol].append(sym_state.phase)
            self.symbol_amplitude_history[symbol].append(sym_state.amplitude)
        
        # Detection checks
        events.extend(self._detect_coherence_changes(state, now))
        events.extend(self._detect_phase_reset(state, now))
        events.extend(self._detect_frequency_shift(state, now))
        events.extend(self._detect_harmonic_convergence(state, now))
        events.extend(self._detect_regime_change(state, now))
        events.extend(self._detect_anomalies(state, now))
        events.extend(self._detect_schumann_alignment(state, now))
        
        # Emit all events
        for event in events:
            self._emit_event(event)
        
        self.last_scan_time = now
        self.scan_count += 1
        
        return events
    
    def _detect_coherence_changes(self, state: GlobalHarmonicState, now: float) -> List[LighthouseEvent]:
        """Detect coherence collapse or surge"""
        events = []
        history = list(self.global_coherence_history)
        
        if len(history) < self.config.coherence_window:
            return events
        
        # Compare recent vs older
        recent = np.mean(history[-3:])
        older = np.mean(history[-self.config.coherence_window:-3])
        change = recent - older
        
        if change < self.config.coherence_collapse_threshold:
            severity = min(1.0, abs(change) / 0.5)
            events.append(LighthouseEvent(
                event_type=LighthouseEventType.COHERENCE_COLLAPSE,
                timestamp=now,
                severity=severity,
                symbols=list(state.symbols.keys())[:10],
                data={
                    "previous_coherence": older,
                    "current_coherence": recent,
                    "change": change
                },
                message=f"Global coherence collapsed {change:.3f} (from {older:.3f} to {recent:.3f})"
            ))
        elif change > self.config.coherence_surge_threshold:
            severity = min(1.0, change / 0.4)
            events.append(LighthouseEvent(
                event_type=LighthouseEventType.COHERENCE_SURGE,
                timestamp=now,
                severity=severity,
                symbols=list(state.symbols.keys())[:10],
                data={
                    "previous_coherence": older,
                    "current_coherence": recent,
                    "change": change
                },
                message=f"Global coherence surged +{change:.3f} (from {older:.3f} to {recent:.3f})"
            ))
        
        return events
    
    def _detect_phase_reset(self, state: GlobalHarmonicState, now: float) -> List[LighthouseEvent]:
        """Detect sudden phase jumps across multiple symbols"""
        events = []
        
        # Count symbols with significant phase jumps
        reset_symbols = []
        for symbol, phase_hist in self.symbol_phase_history.items():
            if len(phase_hist) < self.config.phase_window:
                continue
            
            recent = list(phase_hist)[-self.config.phase_window:]
            phase_velocity = abs(recent[-1] - recent[-2]) if len(recent) > 1 else 0
            
            # Phase jump (accounting for wrap-around at 2π)
            if phase_velocity > math.pi:
                phase_velocity = 2 * math.pi - phase_velocity
            
            if phase_velocity > self.config.phase_reset_threshold:
                reset_symbols.append((symbol, phase_velocity))
        
        # If multiple symbols reset together, it's significant
        if len(reset_symbols) >= 3:
            avg_jump = np.mean([v for _, v in reset_symbols])
            severity = min(1.0, len(reset_symbols) / 10 * avg_jump / math.pi)
            events.append(LighthouseEvent(
                event_type=LighthouseEventType.PHASE_RESET,
                timestamp=now,
                severity=severity,
                symbols=[s for s, _ in reset_symbols[:10]],
                data={
                    "reset_count": len(reset_symbols),
                    "avg_jump": avg_jump
                },
                message=f"Phase reset detected in {len(reset_symbols)} symbols (avg jump: {avg_jump:.3f} rad)"
            ))
        
        return events
    
    def _detect_frequency_shift(self, state: GlobalHarmonicState, now: float) -> List[LighthouseEvent]:
        """Detect significant shift in dominant market frequency"""
        events = []
        history = list(self.frequency_history)
        
        if len(history) < 10:
            return events
        
        recent = np.mean(history[-3:])
        older = np.mean(history[-10:-3])
        
        if older > 0:
            pct_change = (recent - older) / older
            
            if abs(pct_change) > self.config.frequency_shift_pct:
                severity = min(1.0, abs(pct_change) / 0.5)
                direction = "accelerated" if pct_change > 0 else "decelerated"
                events.append(LighthouseEvent(
                    event_type=LighthouseEventType.FREQUENCY_SHIFT,
                    timestamp=now,
                    severity=severity,
                    symbols=[],
                    data={
                        "previous_frequency": older,
                        "current_frequency": recent,
                        "pct_change": pct_change
                    },
                    message=f"Market frequency {direction} {abs(pct_change)*100:.1f}% (from {older:.2f} to {recent:.2f} cycles/day)"
                ))
        
        return events
    
    def _detect_harmonic_convergence(self, state: GlobalHarmonicState, now: float) -> List[LighthouseEvent]:
        """Detect when multiple symbols converge to similar phase (opportunity signal)"""
        events = []
        
        # Group symbols by phase
        phase_buckets: Dict[int, List[str]] = {}
        bucket_size = self.config.convergence_phase_tolerance
        
        for symbol, sym_state in state.symbols.items():
            # Normalize phase to [0, 2π)
            phase = sym_state.phase % (2 * math.pi)
            bucket = int(phase / bucket_size)
            
            if bucket not in phase_buckets:
                phase_buckets[bucket] = []
            phase_buckets[bucket].append(symbol)
        
        # Find largest convergence cluster
        if phase_buckets:
            largest_bucket = max(phase_buckets.values(), key=len)
            
            if len(largest_bucket) >= self.config.convergence_min_symbols:
                # Calculate average phase of converged symbols
                avg_phase = np.mean([state.symbols[s].phase for s in largest_bucket])
                
                # Calculate average velocity (bullish/bearish tendency)
                avg_velocity = np.mean([state.symbols[s].velocity for s in largest_bucket])
                direction = "bullish" if avg_velocity > 0 else "bearish"
                
                severity = min(1.0, len(largest_bucket) / 20)
                events.append(LighthouseEvent(
                    event_type=LighthouseEventType.HARMONIC_CONVERGENCE,
                    timestamp=now,
                    severity=severity,
                    symbols=largest_bucket[:20],
                    data={
                        "converged_count": len(largest_bucket),
                        "average_phase": avg_phase,
                        "average_velocity": avg_velocity,
                        "direction": direction
                    },
                    message=f"Harmonic convergence: {len(largest_bucket)} symbols aligned at phase {avg_phase:.2f} ({direction})"
                ))
        
        return events
    
    def _detect_regime_change(self, state: GlobalHarmonicState, now: float) -> List[LighthouseEvent]:
        """Detect market regime transitions"""
        events = []
        history = list(self.regime_history)
        
        if len(history) < 3:
            return events
        
        current = history[-1]
        previous = history[-2]
        
        if current != previous:
            # Count how long previous regime held
            prev_count = 0
            for h in reversed(history[:-1]):
                if h == previous:
                    prev_count += 1
                else:
                    break
            
            # More significant if regime held for longer
            severity = min(1.0, prev_count / 10)
            events.append(LighthouseEvent(
                event_type=LighthouseEventType.REGIME_CHANGE,
                timestamp=now,
                severity=severity,
                symbols=[],
                data={
                    "previous_regime": previous,
                    "current_regime": current,
                    "previous_duration": prev_count
                },
                message=f"Regime change: {previous} → {current} (held for {prev_count} periods)"
            ))
        
        return events
    
    def _detect_anomalies(self, state: GlobalHarmonicState, now: float) -> List[LighthouseEvent]:
        """Detect statistical anomalies in symbol behavior"""
        events = []
        
        anomalous_symbols = []
        
        for symbol, sym_state in state.symbols.items():
            amp_hist = self.symbol_amplitude_history.get(symbol)
            if not amp_hist or len(amp_hist) < 20:
                continue
            
            # Z-score of current amplitude
            hist_array = np.array(list(amp_hist))
            mean = np.mean(hist_array)
            std = np.std(hist_array)
            
            if std > 0:
                zscore = (sym_state.amplitude - mean) / std
                
                if abs(zscore) > self.config.anomaly_zscore_threshold:
                    anomalous_symbols.append((symbol, zscore, sym_state.amplitude))
        
        if anomalous_symbols:
            # Sort by zscore magnitude
            anomalous_symbols.sort(key=lambda x: abs(x[1]), reverse=True)
            
            severity = min(1.0, len(anomalous_symbols) / 10)
            events.append(LighthouseEvent(
                event_type=LighthouseEventType.ANOMALY_DETECTED,
                timestamp=now,
                severity=severity,
                symbols=[s for s, _, _ in anomalous_symbols[:10]],
                data={
                    "anomaly_count": len(anomalous_symbols),
                    "top_anomalies": [(s, z, a) for s, z, a in anomalous_symbols[:5]]
                },
                message=f"Amplitude anomalies detected in {len(anomalous_symbols)} symbols"
            ))
        
        return events
    
    def _detect_schumann_alignment(self, state: GlobalHarmonicState, now: float) -> List[LighthouseEvent]:
        """Detect when market aligns with Schumann resonance harmonics"""
        events = []
        
        if state.schumann_alignment > self.config.schumann_alignment_threshold:
            # Check if this is a new alignment (not sustained)
            freq_hist = list(self.frequency_history)
            if len(freq_hist) >= 3:
                prev_alignments = []
                for freq in freq_hist[-5:-1]:
                    schumann_harmonics = [SCHUMANN_BASE * n for n in range(1, 10)]
                    min_dist = min(abs(freq - h) for h in schumann_harmonics)
                    prev_alignments.append(1.0 / (1.0 + min_dist))
                
                avg_prev = np.mean(prev_alignments)
                
                # Only emit if alignment is new/increasing
                if state.schumann_alignment - avg_prev > 0.1:
                    severity = state.schumann_alignment
                    events.append(LighthouseEvent(
                        event_type=LighthouseEventType.SCHUMANN_ALIGNMENT,
                        timestamp=now,
                        severity=severity,
                        symbols=[],
                        data={
                            "alignment": state.schumann_alignment,
                            "dominant_frequency": state.dominant_frequency,
                            "schumann_base": SCHUMANN_BASE
                        },
                        message=f"Market frequency aligned with Schumann resonance (alignment: {state.schumann_alignment:.3f})"
                    ))
        
        return events
    
    def get_recent_events(self, event_type: LighthouseEventType = None, limit: int = 20) -> List[LighthouseEvent]:
        """Get recent events, optionally filtered by type"""
        events = list(self.recent_events)
        
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        
        return events[-limit:]
    
    def get_status(self) -> Dict[str, Any]:
        """Get current Lighthouse status"""
        return {
            "scan_count": self.scan_count,
            "last_scan": self.last_scan_time,
            "subscribers": len(self._subscribers),
            "recent_events": len(self.recent_events),
            "tracked_symbols": len(self.symbol_phase_history),
            "coherence_trend": list(self.global_coherence_history)[-5:] if self.global_coherence_history else [],
            "frequency_trend": list(self.frequency_history)[-5:] if self.frequency_history else []
        }


# ═══════════════════════════════════════════════════════════════
# MYCELIUM BRIDGE
# ═══════════════════════════════════════════════════════════════

class LighthouseMyceliumBridge:
    """
    Bridges Lighthouse events to the Mycelium neural network.
    Translates pattern detections into neural signals.
    """
    
    def __init__(self, lighthouse: LighthousePatternDetector, mycelium=None):
        self.lighthouse = lighthouse
        self.mycelium = mycelium
        
        # Event weights for neural influence
        self.event_weights = {
            LighthouseEventType.COHERENCE_COLLAPSE: -0.5,  # Cautious
            LighthouseEventType.COHERENCE_SURGE: 0.3,  # Confident
            LighthouseEventType.PHASE_RESET: -0.3,  # Uncertain
            LighthouseEventType.FREQUENCY_SHIFT: 0.0,  # Neutral signal
            LighthouseEventType.HARMONIC_CONVERGENCE: 0.4,  # Opportunity
            LighthouseEventType.REGIME_CHANGE: 0.2,  # Adapt
            LighthouseEventType.ANOMALY_DETECTED: -0.2,  # Caution
            LighthouseEventType.SCHUMANN_ALIGNMENT: 0.2  # Confidence boost
        }
        
        # Subscribe to lighthouse
        lighthouse.subscribe(self._on_lighthouse_event)
        logger.info("🌐 Lighthouse-Mycelium bridge initialized")
    
    def _on_lighthouse_event(self, event: LighthouseEvent):
        """Handle lighthouse event and translate to mycelium signal"""
        if not self.mycelium:
            return
        
        # Calculate neural signal strength
        weight = self.event_weights.get(event.event_type, 0.0)
        signal_strength = weight * event.severity
        
        # Create mycelium-compatible message
        message = {
            "source": "lighthouse",
            "type": event.event_type.value,
            "strength": signal_strength,
            "symbols": event.symbols,
            "data": event.data,
            "timestamp": event.timestamp
        }
        
        # Send to mycelium (if it has the expected interface)
        try:
            if hasattr(self.mycelium, 'receive_external_signal'):
                self.mycelium.receive_external_signal(message)
            elif hasattr(self.mycelium, 'inject_event'):
                self.mycelium.inject_event(message)
        except Exception as e:
            logger.debug(f"Mycelium signal delivery failed: {e}")


# ═══════════════════════════════════════════════════════════════
# CLI / TESTING
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s'
    )
    
    print("""
    🏮 LIGHTHOUSE PATTERN DETECTOR
    ═══════════════════════════════
    Testing pattern detection...
    """)
    
    # Create mock harmonic state
    from aureon.harmonic.aureon_harmonic_seed import GlobalHarmonicState, SymbolWaveState
    
    state = GlobalHarmonicState()
    state.global_coherence = 0.6
    state.global_phase = 1.5
    state.dominant_frequency = 2.0
    state.market_regime = "bullish"
    state.schumann_alignment = 0.3
    
    # Add mock symbols
    for i in range(20):
        sym = f"TEST{i}/USD"
        state.symbols[sym] = SymbolWaveState(
            symbol=sym,
            phase=1.5 + (0.1 * (i % 5)),  # Some clustering
            amplitude=0.05,
            frequency=2.0,
            velocity=0.01 if i < 15 else -0.01,
            coherence=0.5,
            last_price=100.0,
            last_volume=1000.0,
            last_update=time.time()
        )
    
    # Create lighthouse and scan
    lighthouse = LighthousePatternDetector()
    
    # Subscribe to see events
    def on_event(event):
        print(f"  📡 Event: {event.event_type.value} (severity={event.severity:.2f})")
    
    lighthouse.subscribe(on_event)
    
    # Run multiple scans to build up history
    print("\nRunning scans...")
    for i in range(15):
        # Simulate some changes
        state.global_coherence += 0.02 * (1 if i < 10 else -3)  # Surge then collapse
        state.market_regime = "bullish" if i < 12 else "bearish"
        
        events = lighthouse.scan(state)
        if events:
            print(f"  Scan {i+1}: {len(events)} events detected")
    
    print("\n✅ Lighthouse test complete")
    print(f"   Total events detected: {len(lighthouse.recent_events)}")

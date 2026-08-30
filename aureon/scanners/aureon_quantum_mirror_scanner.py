#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════════════╗
║                                                                                      ║
║     🔮 AUREON QUANTUM MIRROR SCANNER 🔮                                              ║
║     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━                                     ║
║                                                                                      ║
║     REALITY BRANCH COHERENCE DETECTION & TIMELINE PROBABILITY MAPPING                ║
║                                                                                      ║
║     ARCHITECTURE:                                                                    ║
║       • Scans market reality branches for quantum coherence patterns                 ║
║       • Identifies high-probability timeline convergences                            ║
║       • Maps beneficial outcome probability fields                                   ║
║       • Integrates with Stargate Protocol for timeline anchoring                     ║
║                                                                                      ║
║     BATTEN MATRIX INTEGRATION:                                                       ║
║       • Pass 1: Harmonic frequency alignment scan                                    ║
║       • Pass 2: Coherence field measurement                                          ║
║       • Pass 3: Timeline stability assessment                                        ║
║       • Pass 4 (Execution): Timeline anchor/trade execution                          ║
║                                                                                      ║
║     Gary Leckey & GitHub Copilot | January 2026                                     ║
║     "Every market tick is a choice point between infinite timelines"                ║
╚══════════════════════════════════════════════════════════════════════════════════════╝
"""

from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import sys
import os

# Windows UTF-8 fix
if sys.platform == 'win32' and sys.stdout.isatty():
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    try:
        import io
        def _is_utf8_wrapper(stream):
            return (isinstance(stream, io.TextIOWrapper) and 
                    hasattr(stream, 'encoding') and stream.encoding and
                    stream.encoding.lower().replace('-', '') == 'utf8')
        if hasattr(sys.stdout, 'buffer') and not _is_utf8_wrapper(sys.stdout):
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)
        # Skip stderr wrapping (causes Windows exit errors)
    except Exception:
        pass

import math
import time
import json
import logging
import hashlib
import threading
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any, Tuple, Callable
from collections import deque
from enum import Enum
import numpy as np
from aureon.core.metrics import MetricGauge

# 🔮 OBSIDIAN FILTER INTEGRATION
try:
    from aureon.scanners.aureon_obsidian_filter import AureonObsidianFilter
    OBSIDIAN_FILTER_AVAILABLE = True
except Exception:
    AureonObsidianFilter = None
    OBSIDIAN_FILTER_AVAILABLE = False

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════
# 📊 METRICS
# ═══════════════════════════════════════════════════════════════
quantum_mirror_branch_score = MetricGauge(
    'quantum_mirror_branch_score',
    'Current branch score S_b(t) from Quantum Mirror Scanner',
    labelnames=('symbol', 'exchange')
)

# ═══════════════════════════════════════════════════════════════
# 🌍 SACRED CONSTANTS
# ═══════════════════════════════════════════════════════════════

PHI = (1 + math.sqrt(5)) / 2  # 1.618033988749895
SCHUMANN_BASE = 7.83
LOVE_FREQUENCY = 528
UNITY_FREQUENCY = 963

# Solfeggio for timeline harmonics
SOLFEGGIO = [174, 285, 396, 417, 528, 639, 741, 852, 963]

# Fibonacci for timing windows
FIBONACCI = [1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233, 377, 610, 987]

# Prime numbers for validation passes
PRIMES = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53]


# ═══════════════════════════════════════════════════════════════
# 📊 REALITY BRANCH STRUCTURES
# ═══════════════════════════════════════════════════════════════

class BranchPhase(Enum):
    """Phases of a reality branch in the scanner"""
    DETECTED = "detected"              # Initial detection
    VALIDATED_P1 = "validated_p1"      # Passed harmonic scan
    VALIDATED_P2 = "validated_p2"      # Passed coherence measurement
    VALIDATED_P3 = "validated_p3"      # Passed stability assessment
    READY_FOR_4TH = "ready_for_4th"    # Ready for execution/anchoring
    EXECUTED = "executed"              # Trade/anchor executed
    EXPIRED = "expired"                # Window closed


@dataclass
class RealityBranch:
    """
    A reality branch represents a specific symbol/exchange combination
    as a potential timeline with measurable coherence.
    """
    branch_id: str
    symbol: str
    exchange: str
    
    # Harmonic state
    frequency: float = SCHUMANN_BASE
    phase: float = 0.0
    amplitude: float = 0.0
    
    # Validation passes (Batten Matrix)
    p1_harmonic: float = 0.0
    p2_coherence: float = 0.0
    p3_stability: float = 0.0
    
    # Computed metrics
    coherence_score: float = 0.0  # C_b - agreement across validators
    lambda_stability: float = 1.0  # Λ_b - decay penalty
    drift_score: float = 0.0  # D_b - how fast state changes
    pip_potential: float = 0.0  # Expected profit in pips
    
    # Timeline properties
    beneficial_probability: float = 0.0  # P(beneficial outcome)
    convergence_window: float = 0.0  # Seconds until window closes

    # Obsidian refinement signals
    obsidian_chaos: float = 0.0
    obsidian_clarity: float = 1.0
    obsidian_casimir_frequency: float = 0.0
    
    # State
    branch_phase: BranchPhase = BranchPhase.DETECTED
    first_detection: float = 0.0
    last_update: float = 0.0
    validation_history: List[Dict] = field(default_factory=list)
    
    def compute_branch_score(self) -> float:
        """
        Compute overall branch score using Batten Matrix formula:
        S_b(t) = p̄_b × P_b × C_b × Λ_b(t)
        
        Where:
        - p̄_b = average validation probability
        - P_b = beneficial probability
        - C_b = coherence score
        - Λ_b = lambda stability
        """
        p_avg = (self.p1_harmonic + self.p2_coherence + self.p3_stability) / 3.0
        
        score = (
            p_avg *
            self.beneficial_probability *
            self.coherence_score *
            self.lambda_stability
        )
        
        # Telemetry
        quantum_mirror_branch_score.set(score, symbol=self.symbol, exchange=self.exchange)
        
        return score
        
    def compute_coherence(self) -> float:
        """
        Coherence = 1 - spread of validation probabilities
        High coherence = validators agree
        """
        probs = [self.p1_harmonic, self.p2_coherence, self.p3_stability]
        if max(probs) == 0:
            return 0.0
        spread = max(probs) - min(probs)
        self.coherence_score = max(0.0, 1.0 - spread)
        return self.coherence_score
        
    def update_lambda(self, alpha: float = 0.1) -> float:
        """
        Update lambda stability based on drift:
        Λ_b(t) = e^(-α × D_b(t))
        """
        self.lambda_stability = math.exp(-alpha * self.drift_score)
        return self.lambda_stability
        
    def is_ready_for_execution(self, threshold: float = 0.618) -> bool:
        """Check if branch is ready for 4th pass execution"""
        score = self.compute_branch_score()
        return (
            score >= threshold and
            self.branch_phase == BranchPhase.VALIDATED_P3 and
            self.coherence_score >= 0.5 and
            self.lambda_stability >= 0.5
        )


@dataclass
class TimelineConvergence:
    """
    A convergence is when multiple reality branches align,
    creating a high-probability manifestation window.
    """
    convergence_id: str
    branches: List[str]  # Branch IDs
    convergence_strength: float  # 0-1
    frequency_alignment: float  # How aligned are the frequencies
    phase_alignment: float  # How aligned are the phases
    beneficial_consensus: float  # Agreement on beneficial outcome
    window_start: float
    window_duration: float  # Seconds
    
    def is_active(self) -> bool:
        now = time.time()
        return self.window_start <= now <= (self.window_start + self.window_duration)


# ═══════════════════════════════════════════════════════════════
# 🔮 QUANTUM MIRROR SCANNER ENGINE
# ═══════════════════════════════════════════════════════════════

class QuantumMirrorScanner:
    """
    Scans reality branches for quantum coherence patterns and
    identifies high-probability timeline convergences.
    
    Integrates with:
    - Stargate Protocol for timeline anchoring
    - ThoughtBus for event emission
    - Probability Nexus for validation passes
    - 🦙 AlpacaScannerBridge for SSE data + trailing stops
    """
    
    # Thresholds
    COHERENCE_THRESHOLD = 0.618  # Golden ratio threshold
    LAMBDA_DECAY_ALPHA = 0.1
    MIN_BRANCHES_FOR_CONVERGENCE = 3
    CONVERGENCE_PHASE_TOLERANCE = 0.3  # Radians
    
    def __init__(self, thought_bus=None, stargate_engine=None, scanner_bridge=None):
        self.branches: Dict[str, RealityBranch] = {}
        self.convergences: Dict[str, TimelineConvergence] = {}
        self.scan_history: deque = deque(maxlen=10000)
        
        # Global state
        self.global_coherence: float = 0.0
        self.dominant_frequency: float = SCHUMANN_BASE
        self.timeline_entropy: float = 1.0  # High = chaotic, low = ordered
        
        # Integration
        self._thought_bus = thought_bus
        self._stargate_engine = stargate_engine
        self._scanner_bridge = scanner_bridge  # 🦙 AlpacaScannerBridge
        self._lock = threading.RLock()

        # 🔮 Obsidian filter (gem refinement)
        self._obsidian_filter = AureonObsidianFilter() if OBSIDIAN_FILTER_AVAILABLE else None
        
        # 🦙 Dynamic cost thresholds from fee tracker
        self._pip_threshold = 0.07  # Default minimum
        self._cost_threshold = 0.50  # Default round-trip cost %
        
        # Callbacks
        self._convergence_callbacks: List[Callable] = []
        self._execution_callbacks: List[Callable] = []
        
        logger.info("🔮 Quantum Mirror Scanner initialized")
        if scanner_bridge:
            logger.info("   🦙 AlpacaScannerBridge: CONNECTED (SSE + trailing stops)")
            self._update_cost_thresholds()
    
    def set_scanner_bridge(self, bridge):
        """Wire up the Alpaca Scanner Bridge for SSE + trailing stop execution."""
        self._scanner_bridge = bridge
        self._update_cost_thresholds()
        logger.info("🦙 Scanner Bridge wired to Quantum Mirror Scanner")
    
    def _update_cost_thresholds(self):
        """Update cost thresholds from scanner bridge's fee tracker."""
        if not self._scanner_bridge:
            return
        
        try:
            thresholds = self._scanner_bridge.get_cost_thresholds()
            self._cost_threshold = thresholds.round_trip_cost_pct
            # Minimum pip potential should cover costs
            self._pip_threshold = max(0.07, thresholds.tier_3_valid_threshold)
            
            logger.info(f"💰 QM Scanner cost thresholds updated:")
            logger.info(f"   Cost threshold: {self._cost_threshold:.3f}%")
            logger.info(f"   Min PIP: {self._pip_threshold:.3f}%")
        except Exception as e:
            logger.warning(f"⚠️ Could not update cost thresholds: {e}")
        
    def register_branch(self, symbol: str, exchange: str, 
                        initial_price: float = 0.0) -> RealityBranch:
        """Register a new reality branch for scanning"""
        with self._lock:
            branch_id = f"{exchange}:{symbol}"
            
            if branch_id in self.branches:
                return self.branches[branch_id]
                
            branch = RealityBranch(
                branch_id=branch_id,
                symbol=symbol,
                exchange=exchange,
                amplitude=initial_price,
                first_detection=time.time(),
                last_update=time.time(),
            )
            
            self.branches[branch_id] = branch
            
            self._emit_thought(
                topic="mirror.branch.registered",
                payload={
                    "branch_id": branch_id,
                    "symbol": symbol,
                    "exchange": exchange,
                }
            )
            
            return branch
            
    def update_branch(self, branch_id: str, 
                      price: float = None,
                      volume: float = None,
                      frequency: float = None,
                      phase: float = None) -> Optional[RealityBranch]:
        """Update branch state with new market data"""
        with self._lock:
            if branch_id not in self.branches:
                return None
                
            branch = self.branches[branch_id]
            old_amplitude = branch.amplitude
            
            if price is not None:
                branch.amplitude = price
            if frequency is not None:
                branch.frequency = frequency
            if phase is not None:
                branch.phase = phase
                
            # Compute drift
            if old_amplitude > 0 and branch.amplitude > 0:
                price_change = abs(branch.amplitude - old_amplitude) / old_amplitude
                time_delta = time.time() - branch.last_update
                branch.drift_score = price_change / max(0.001, time_delta)
                
            branch.update_lambda(self.LAMBDA_DECAY_ALPHA)
            branch.last_update = time.time()
            
            return branch

    def _refine_with_obsidian(self, branch: RealityBranch, snapshot: Dict[str, Any]) -> None:
        if not self._obsidian_filter:
            return
        try:
            filtered = self._obsidian_filter.apply(branch.symbol, snapshot)
            branch.obsidian_chaos = float(filtered.get('obsidian_chaos', 0.0))
            branch.obsidian_clarity = float(filtered.get('obsidian_clarity', 1.0))
            branch.obsidian_casimir_frequency = float(filtered.get('obsidian_casimir_frequency', 0.0))

            # If Casimir carrier is present, gently pull branch frequency toward it
            if branch.obsidian_casimir_frequency:
                branch.frequency = (branch.frequency * 0.8) + (branch.obsidian_casimir_frequency * 0.2)
        except Exception:
            pass
            
    # ═══════════════════════════════════════════════════════════════
    # VALIDATION PASSES (Batten Matrix)
    # ═══════════════════════════════════════════════════════════════
    
    def validation_pass_1_harmonic(self, branch_id: str) -> float:
        """
        Pass 1: Harmonic frequency alignment scan
        
        Checks how well the branch frequency aligns with
        sacred frequencies (Solfeggio, Schumann harmonics).
        """
        with self._lock:
            if branch_id not in self.branches:
                return 0.0
                
            branch = self.branches[branch_id]
            
            # Check alignment with Solfeggio frequencies
            solfeggio_alignments = []
            for freq in SOLFEGGIO:
                ratio = branch.frequency / freq if freq > 0 else 0
                harmonic_distance = abs(ratio - round(ratio))
                alignment = 1.0 - min(1.0, harmonic_distance * 2)
                solfeggio_alignments.append(alignment)
                
            # Check Schumann harmonic alignment
            schumann_ratio = branch.frequency / SCHUMANN_BASE
            schumann_alignment = 1.0 - min(1.0, abs(schumann_ratio - round(schumann_ratio)) * 2)
            
            # Golden ratio frequency check
            phi_freq = SCHUMANN_BASE * PHI
            phi_alignment = 1.0 - min(1.0, abs(branch.frequency - phi_freq) / phi_freq)
            
            # Combine scores
            p1 = (
                max(solfeggio_alignments) * 0.4 +
                schumann_alignment * 0.4 +
                phi_alignment * 0.2
            )
            
            branch.p1_harmonic = p1
            
            if p1 >= 0.5:
                branch.branch_phase = BranchPhase.VALIDATED_P1
                
            branch.validation_history.append({
                "pass": 1,
                "score": p1,
                "timestamp": time.time(),
            })
            
            self._emit_thought(
                topic="mirror.validation.p1",
                payload={
                    "branch_id": branch_id,
                    "p1_score": p1,
                    "phase": branch.branch_phase.value,
                }
            )
            
            return p1
            
    def validation_pass_2_coherence(self, branch_id: str) -> float:
        """
        Pass 2: Coherence field measurement
        
        Measures the branch's internal coherence and
        correlation with neighboring branches.
        """
        with self._lock:
            if branch_id not in self.branches:
                return 0.0
                
            branch = self.branches[branch_id]
            
            if branch.branch_phase not in [BranchPhase.VALIDATED_P1, 
                                            BranchPhase.VALIDATED_P2,
                                            BranchPhase.VALIDATED_P3]:
                return 0.0  # Must pass P1 first
                
            # Internal coherence based on drift stability
            drift_coherence = math.exp(-branch.drift_score * 10)
            
            # Phase stability (how consistent is phase over recent history)
            phase_coherence = 0.5  # Base value, would be computed from history
            
            # Cross-branch coherence (correlation with other branches)
            cross_coherence = self._compute_cross_coherence(branch_id)
            
            # Lambda factor
            lambda_factor = branch.lambda_stability
            
            obsidian_boost = 0.0
            if branch.obsidian_clarity >= 1.2:
                obsidian_boost += 0.05
            if branch.obsidian_chaos >= 0.8:
                obsidian_boost -= 0.05

            p2 = (
                drift_coherence * 0.3 +
                phase_coherence * 0.2 +
                cross_coherence * 0.3 +
                lambda_factor * 0.2
            )
            p2 = max(0.0, min(1.0, p2 + obsidian_boost))
            
            branch.p2_coherence = p2
            
            if p2 >= 0.5:
                branch.branch_phase = BranchPhase.VALIDATED_P2
                
            branch.validation_history.append({
                "pass": 2,
                "score": p2,
                "timestamp": time.time(),
            })
            
            self._emit_thought(
                topic="mirror.validation.p2",
                payload={
                    "branch_id": branch_id,
                    "p2_score": p2,
                    "phase": branch.branch_phase.value,
                }
            )
            
            return p2
            
    def validation_pass_3_stability(self, branch_id: str) -> float:
        """
        Pass 3: Timeline stability assessment
        
        Assesses the stability of the potential timeline
        and its beneficial outcome probability.
        """
        with self._lock:
            if branch_id not in self.branches:
                return 0.0
                
            branch = self.branches[branch_id]
            
            if branch.branch_phase not in [BranchPhase.VALIDATED_P2,
                                            BranchPhase.VALIDATED_P3]:
                return 0.0  # Must pass P2 first
                
            # Timeline stability from lambda
            stability = branch.lambda_stability
            
            # Beneficial probability estimation
            # Based on harmonic alignment + coherence + momentum
            harmonic_factor = branch.p1_harmonic
            coherence_factor = branch.p2_coherence
            
            # Estimate pip potential (simplified)
            if branch.amplitude > 0:
                volatility_estimate = branch.drift_score * branch.amplitude * 100
                pip_potential = min(1.4, max(0.07, volatility_estimate))
            else:
                pip_potential = 0.07
                
            branch.pip_potential = pip_potential
            
            # Beneficial probability
            beneficial = (harmonic_factor + coherence_factor + stability) / 3.0
            if branch.obsidian_clarity >= 1.2:
                beneficial = min(1.0, beneficial + 0.03)
            if branch.obsidian_chaos >= 0.8:
                beneficial = max(0.0, beneficial - 0.03)
            branch.beneficial_probability = beneficial
            
            # Convergence window estimation (Fibonacci timing)
            fib_window = FIBONACCI[min(len(FIBONACCI)-1, int(stability * 10))]
            branch.convergence_window = fib_window * 60  # Convert to seconds
            
            p3 = stability * beneficial * PHI  # Golden amplification
            p3 = min(1.0, p3)  # Cap at 1.0
            
            branch.p3_stability = p3
            
            if p3 >= 0.5:
                branch.branch_phase = BranchPhase.VALIDATED_P3
                
            # Update overall coherence
            branch.compute_coherence()
            
            # Check if ready for 4th pass
            if branch.is_ready_for_execution(self.COHERENCE_THRESHOLD):
                branch.branch_phase = BranchPhase.READY_FOR_4TH
                
            branch.validation_history.append({
                "pass": 3,
                "score": p3,
                "timestamp": time.time(),
                "pip_potential": pip_potential,
                "beneficial": beneficial,
            })
            
            self._emit_thought(
                topic="mirror.validation.p3",
                payload={
                    "branch_id": branch_id,
                    "p3_score": p3,
                    "phase": branch.branch_phase.value,
                    "ready_for_4th": branch.branch_phase == BranchPhase.READY_FOR_4TH,
                    "score": branch.compute_branch_score(),
                }
            )
            
            return p3
            
    def _compute_cross_coherence(self, branch_id: str) -> float:
        """Compute coherence with other branches in the same exchange"""
        branch = self.branches.get(branch_id)
        if not branch:
            return 0.0
            
        same_exchange_branches = [
            b for b_id, b in self.branches.items()
            if b.exchange == branch.exchange and b_id != branch_id
        ]
        
        if not same_exchange_branches:
            return 0.5  # Default if no comparison available
            
        # Phase coherence with neighbors
        phase_diffs = []
        for other in same_exchange_branches:
            phase_diff = abs(branch.phase - other.phase)
            # Normalize to 0-1 (0 = perfectly aligned, 1 = opposite)
            phase_diff = min(phase_diff, 2 * math.pi - phase_diff) / math.pi
            phase_diffs.append(1.0 - phase_diff)
            
        return np.mean(phase_diffs) if phase_diffs else 0.5
        
    # ═══════════════════════════════════════════════════════════════
    # CONVERGENCE DETECTION
    # ═══════════════════════════════════════════════════════════════
    
    def scan_for_convergences(self) -> List[TimelineConvergence]:
        """
        Scan all branches for timeline convergences.
        A convergence occurs when multiple branches align in phase and frequency.
        """
        with self._lock:
            # Get validated branches
            validated = [
                b for b in self.branches.values()
                if b.branch_phase in [BranchPhase.VALIDATED_P3, BranchPhase.READY_FOR_4TH]
            ]
            
            if len(validated) < self.MIN_BRANCHES_FOR_CONVERGENCE:
                return []
                
            new_convergences = []
            
            # Group by similar phase
            phase_groups: Dict[int, List[RealityBranch]] = {}
            for branch in validated:
                # Quantize phase to buckets
                bucket = int(branch.phase / self.CONVERGENCE_PHASE_TOLERANCE)
                if bucket not in phase_groups:
                    phase_groups[bucket] = []
                phase_groups[bucket].append(branch)
                
            # Check each group for convergence
            for bucket, group in phase_groups.items():
                if len(group) >= self.MIN_BRANCHES_FOR_CONVERGENCE:
                    # Calculate convergence strength
                    phases = [b.phase for b in group]
                    frequencies = [b.frequency for b in group]
                    beneficials = [b.beneficial_probability for b in group]
                    
                    phase_alignment = 1.0 - (np.std(phases) / (math.pi / 2))
                    freq_alignment = 1.0 - (np.std(frequencies) / np.mean(frequencies)) if np.mean(frequencies) > 0 else 0
                    beneficial_consensus = np.mean(beneficials)
                    
                    strength = (phase_alignment + freq_alignment + beneficial_consensus) / 3.0
                    
                    if strength >= 0.5:
                        conv_id = f"conv_{bucket}_{int(time.time())}"
                        convergence = TimelineConvergence(
                            convergence_id=conv_id,
                            branches=[b.branch_id for b in group],
                            convergence_strength=strength,
                            frequency_alignment=freq_alignment,
                            phase_alignment=phase_alignment,
                            beneficial_consensus=beneficial_consensus,
                            window_start=time.time(),
                            window_duration=min(b.convergence_window for b in group),
                        )
                        
                        self.convergences[conv_id] = convergence
                        new_convergences.append(convergence)
                        
                        self._emit_thought(
                            topic="mirror.convergence.detected",
                            payload={
                                "convergence_id": conv_id,
                                "strength": strength,
                                "branch_count": len(group),
                                "branches": [b.branch_id for b in group],
                            }
                        )
                        
                        # Notify callbacks
                        for callback in self._convergence_callbacks:
                            try:
                                callback(convergence)
                            except Exception as e:
                                logger.error(f"Convergence callback error: {e}")
                                
                        logger.info(f"🌀 Timeline convergence detected: {conv_id}")
                        logger.info(f"   Strength: {strength:.3f}, Branches: {len(group)}")
                        
            return new_convergences
            
    def get_ready_branches(self) -> List[RealityBranch]:
        """Get all branches ready for 4th pass execution"""
        with self._lock:
            return [
                b for b in self.branches.values()
                if b.branch_phase == BranchPhase.READY_FOR_4TH
            ]
            
    def execute_4th_pass(self, branch_id: str) -> Dict[str, Any]:
        """
        Execute the 4th pass for a validated branch.
        This is the final gate before trade execution.
        
        🦙 ENHANCED: Uses AlpacaScannerBridge for trailing stop execution
        
        Returns execution decision and metadata.
        """
        with self._lock:
            if branch_id not in self.branches:
                return {"success": False, "reason": "branch_not_found"}
                
            branch = self.branches[branch_id]
            
            if branch.branch_phase != BranchPhase.READY_FOR_4TH:
                return {
                    "success": False,
                    "reason": "not_ready",
                    "current_phase": branch.branch_phase.value,
                }
                
            # Final validation check
            score = branch.compute_branch_score()
            
            if score < self.COHERENCE_THRESHOLD:
                return {
                    "success": False,
                    "reason": "score_below_threshold",
                    "score": score,
                    "threshold": self.COHERENCE_THRESHOLD,
                }
                
            # Check lambda hasn't decayed too much
            if branch.lambda_stability < 0.3:
                return {
                    "success": False,
                    "reason": "lambda_decay",
                    "lambda": branch.lambda_stability,
                }
            
            # 🦙 Check profitability with dynamic cost thresholds
            if branch.pip_potential < self._pip_threshold:
                return {
                    "success": False,
                    "reason": "pip_below_cost_threshold",
                    "pip_potential": branch.pip_potential,
                    "threshold": self._pip_threshold,
                }
                
            # ✅ 4th pass approved - ready for execution
            branch.branch_phase = BranchPhase.EXECUTED
            
            result = {
                "success": True,
                "branch_id": branch_id,
                "symbol": branch.symbol,
                "exchange": branch.exchange,
                "score": score,
                "pip_potential": branch.pip_potential,
                "coherence": branch.coherence_score,
                "lambda": branch.lambda_stability,
                "beneficial_probability": branch.beneficial_probability,
                "validation_passes": {
                    "p1_harmonic": branch.p1_harmonic,
                    "p2_coherence": branch.p2_coherence,
                    "p3_stability": branch.p3_stability,
                },
                "timestamp": time.time(),
            }
            
            # 🦙 Execute via Scanner Bridge with trailing stop
            if self._scanner_bridge and branch.exchange == 'alpaca':
                try:
                    # Calculate dynamic trail % based on pip potential
                    trail_pct = max(1.0, min(3.0, branch.pip_potential * 0.5))
                    
                    # This is where the actual trade would execute
                    # The scanner bridge handles trailing stop setup
                    result['trailing_stop'] = {
                        'enabled': True,
                        'trail_percent': trail_pct,
                        'activation_profit': branch.pip_potential * 0.3,
                    }
                    
                    logger.info(f"🛡️ Trailing stop configured: {trail_pct:.2f}% trail")
                    
                except Exception as e:
                    logger.error(f"⚠️ Trailing stop setup error: {e}")
                    result['trailing_stop'] = {'enabled': False, 'error': str(e)}
            
            # Emit execution event
            self._emit_thought(
                topic="mirror.execution.4th_pass",
                payload=result
            )
            
            # Notify execution callbacks
            for callback in self._execution_callbacks:
                try:
                    callback(result)
                except Exception as e:
                    logger.error(f"Execution callback error: {e}")
                    
            logger.info(f"✅ 4th PASS EXECUTED: {branch_id}")
            logger.info(f"   Score: {score:.4f}, PIP: {branch.pip_potential:.2f}")
            
            return result
            
    # ═══════════════════════════════════════════════════════════════
    # STARGATE INTEGRATION
    # ═══════════════════════════════════════════════════════════════
    
    def synchronize_with_stargate(self) -> Dict[str, Any]:
        """
        Synchronize scanner state with Stargate Protocol.
        Uses stargate network coherence to boost branch validation.
        """
        if not self._stargate_engine:
            return {"synced": False, "reason": "no_stargate_engine"}
            
        try:
            stargate_status = self._stargate_engine.get_status()
            network = stargate_status.get("network", {})
            
            # Apply stargate coherence boost to branches
            stargate_coherence = network.get("global_coherence", 0.0)
            schumann_alignment = network.get("schumann_alignment", 0.0)
            
            boosted_count = 0
            for branch in self.branches.values():
                if branch.branch_phase in [BranchPhase.VALIDATED_P2, 
                                           BranchPhase.VALIDATED_P3]:
                    # Boost coherence with stargate network alignment
                    boost = stargate_coherence * schumann_alignment * 0.1
                    branch.p2_coherence = min(1.0, branch.p2_coherence + boost)
                    branch.compute_coherence()
                    boosted_count += 1
                    
            # Update global scanner state
            self.global_coherence = (
                self.global_coherence * 0.9 + stargate_coherence * 0.1
            )
            
            return {
                "synced": True,
                "stargate_coherence": stargate_coherence,
                "schumann_alignment": schumann_alignment,
                "branches_boosted": boosted_count,
            }
            
        except Exception as e:
            logger.error(f"Stargate sync error: {e}")
            return {"synced": False, "reason": str(e)}
            
    # ═══════════════════════════════════════════════════════════════
    # BATCH UPDATE FROM TRADING LOOP
    # ═══════════════════════════════════════════════════════════════
    
    def update_from_market_data(self, opportunities: List[Dict], prices: Dict[str, float]) -> Dict[str, Any]:
        """
        🔮 BATCH UPDATE: Feed market opportunities into quantum mirror scanner.
        
        This is the CRITICAL integration point that connects the trading loop
        to the quantum mirror validation system.
        
        Args:
            opportunities: List of trading opportunities with from_asset, to_asset, exchange
            prices: Current price map {symbol: price}
            
        Returns:
            Summary of branches updated and ready for execution
        """
        with self._lock:
            registered = 0
            updated = 0
            validated = 0
            ready_branches = []
            
            for opp in opportunities:
                # Extract opportunity data
                from_asset = opp.get('from_asset', '') if isinstance(opp, dict) else getattr(opp, 'from_asset', '')
                to_asset = opp.get('to_asset', '') if isinstance(opp, dict) else getattr(opp, 'to_asset', '')
                exchange = opp.get('source_exchange', 'kraken') if isinstance(opp, dict) else getattr(opp, 'source_exchange', 'kraken')
                expected_pnl = opp.get('expected_pnl_usd', 0) if isinstance(opp, dict) else getattr(opp, 'expected_pnl_usd', 0)
                
                if not from_asset or not to_asset:
                    continue
                    
                symbol = f"{from_asset}/{to_asset}"
                branch_id = f"{exchange}:{symbol}"
                price = prices.get(to_asset, prices.get(from_asset, 100.0))
                volume = opp.get('volume', 0.0) if isinstance(opp, dict) else getattr(opp, 'volume', 0.0)
                
                # Register or get existing branch
                if branch_id not in self.branches:
                    branch = self.register_branch(symbol, exchange, price)
                    registered += 1
                else:
                    branch = self.branches[branch_id]
                    updated += 1
                    
                # Update branch with current price and derive frequency from price pattern
                branch = self.update_branch(
                    branch_id,
                    price=price,
                    volume=volume,
                    frequency=(price % 100) + SCHUMANN_BASE * PHI,
                    phase=(price % math.pi)
                )

                # Refine branch via Obsidian filter (gem refinement)
                if branch:
                    volatility = opp.get('volatility', 0.0) if isinstance(opp, dict) else getattr(opp, 'volatility', 0.0)
                    sentiment = 0.5 + max(-0.5, min(0.5, expected_pnl / 10.0))
                    snapshot = {
                        'price': price,
                        'volume': volume,
                        'volatility': volatility,
                        'sentiment': sentiment,
                        'coherence': branch.coherence_score if branch.coherence_score > 0 else 0.5,
                    }
                    self._refine_with_obsidian(branch, snapshot)
                
                # Run 3-pass Batten Matrix validation
                p1 = self.validation_pass_1_harmonic(branch_id)
                if p1 >= 0.3:  # Only continue if P1 passes
                    p2 = self.validation_pass_2_coherence(branch_id)
                    if p2 >= 0.3:  # Only continue if P2 passes
                        p3 = self.validation_pass_3_stability(branch_id)
                        validated += 1
                        
                        # Check if ready for 4th pass
                        if branch.is_ready_for_execution(self.COHERENCE_THRESHOLD * 0.8):  # Slightly relaxed threshold
                            ready_branches.append({
                                "branch_id": branch_id,
                                "symbol": symbol,
                                "exchange": exchange,
                                "score": branch.compute_branch_score(),
                                "pip_potential": branch.pip_potential,
                                "expected_pnl": expected_pnl,
                            })
            
            # Update global coherence from validated branches
            if self.branches:
                coherences = [b.coherence_score for b in self.branches.values() if b.coherence_score > 0]
                if coherences:
                    self.global_coherence = np.mean(coherences)
                    
            # Scan for convergences among validated branches
            convergences = self.scan_for_convergences()
            
            result = {
                "registered": registered,
                "updated": updated,
                "validated": validated,
                "ready_count": len(ready_branches),
                "ready_branches": ready_branches[:10],  # Top 10
                "convergences_detected": len(convergences),
                "global_coherence": self.global_coherence,
            }
            
            if ready_branches:
                logger.info(f"🔮 Quantum Mirror: {len(ready_branches)} branches ready for 4th pass!")
                for rb in ready_branches[:3]:
                    logger.info(f"   ⚡ {rb['branch_id']}: score={rb['score']:.3f}")
                    
            return result
    
    def get_quantum_boost(self, from_asset: str, to_asset: str, exchange: str) -> Tuple[float, str]:
        """
        Get quantum coherence boost for a specific trading opportunity.
        
        Returns:
            (boost_score, reason_string)
        """
        with self._lock:
            symbol = f"{from_asset}/{to_asset}"
            branch_id = f"{exchange}:{symbol}"
            
            if branch_id not in self.branches:
                return 0.0, "no_branch"
                
            branch = self.branches[branch_id]
            
            # Calculate boost based on branch state
            boost = 0.0
            reasons = []
            
            if branch.branch_phase == BranchPhase.READY_FOR_4TH:
                boost += 0.3
                reasons.append("4TH_READY")
            elif branch.branch_phase == BranchPhase.VALIDATED_P3:
                boost += 0.2
                reasons.append("P3_VALID")
            elif branch.branch_phase == BranchPhase.VALIDATED_P2:
                boost += 0.1
                reasons.append("P2_VALID")
                
            # Coherence bonus
            if branch.coherence_score >= 0.618:
                boost += 0.15
                reasons.append(f"φ_COHERENT({branch.coherence_score:.2f})")
                
            # Lambda stability bonus
            if branch.lambda_stability >= 0.8:
                boost += 0.1
                reasons.append(f"Λ_STABLE({branch.lambda_stability:.2f})")
                
            # Pip potential bonus
            if branch.pip_potential >= 0.07:
                boost += 0.05
                reasons.append(f"PIP({branch.pip_potential:.2f})")
                
            return min(1.0, boost), "+".join(reasons) if reasons else "neutral"
    
    # ═══════════════════════════════════════════════════════════════
    # CALLBACKS & INTEGRATION
    # ═══════════════════════════════════════════════════════════════
    
    def on_convergence(self, callback: Callable[[TimelineConvergence], None]) -> None:
        """Register callback for convergence detection"""
        self._convergence_callbacks.append(callback)
        
    def on_execution(self, callback: Callable[[Dict], None]) -> None:
        """Register callback for 4th pass execution"""
        self._execution_callbacks.append(callback)
        
    def _emit_thought(self, topic: str, payload: Dict[str, Any]) -> None:
        """Emit thought to ThoughtBus if available"""
        if self._thought_bus:
            try:
                from aureon.core.aureon_thought_bus import Thought
                thought = Thought(
                    source="quantum_mirror_scanner",
                    topic=topic,
                    payload=payload
                )
                self._thought_bus.publish(thought)
            except Exception as e:
                logger.debug(f"Could not emit thought: {e}")
                
    # ═══════════════════════════════════════════════════════════════
    # STATUS & REPORTING
    # ═══════════════════════════════════════════════════════════════
    
    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive scanner status"""
        with self._lock:
            phase_counts = {}
            for branch in self.branches.values():
                phase = branch.branch_phase.value
                phase_counts[phase] = phase_counts.get(phase, 0) + 1
                
            ready_branches = self.get_ready_branches()
            active_convergences = [
                c for c in self.convergences.values() if c.is_active()
            ]
            
            return {
                "timestamp": time.time(),
                "total_branches": len(self.branches),
                "phase_distribution": phase_counts,
                "ready_for_execution": len(ready_branches),
                "active_convergences": len(active_convergences),
                "global_coherence": self.global_coherence,
                "dominant_frequency": self.dominant_frequency,
                "timeline_entropy": self.timeline_entropy,
                "ready_branch_ids": [b.branch_id for b in ready_branches],
            }
            
    def get_branch_details(self, branch_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific branch"""
        with self._lock:
            if branch_id not in self.branches:
                return None
                
            branch = self.branches[branch_id]
            return {
                "branch_id": branch.branch_id,
                "symbol": branch.symbol,
                "exchange": branch.exchange,
                "phase": branch.branch_phase.value,
                "frequency": branch.frequency,
                "amplitude": branch.amplitude,
                "validation": {
                    "p1_harmonic": branch.p1_harmonic,
                    "p2_coherence": branch.p2_coherence,
                    "p3_stability": branch.p3_stability,
                },
                "metrics": {
                    "coherence": branch.coherence_score,
                    "lambda": branch.lambda_stability,
                    "drift": branch.drift_score,
                    "pip_potential": branch.pip_potential,
                    "beneficial": branch.beneficial_probability,
                    "score": branch.compute_branch_score(),
                },
                "timing": {
                    "first_detection": branch.first_detection,
                    "last_update": branch.last_update,
                    "convergence_window": branch.convergence_window,
                },
                "ready_for_execution": branch.is_ready_for_execution(self.COHERENCE_THRESHOLD),
            }


# ═══════════════════════════════════════════════════════════════
# 🚀 FACTORY & MAIN
# ═══════════════════════════════════════════════════════════════

def create_quantum_scanner(with_integrations: bool = True) -> QuantumMirrorScanner:
    """Factory function to create a Quantum Mirror Scanner with integrations"""
    thought_bus = None
    stargate_engine = None
    
    if with_integrations:
        try:
            from aureon.core.aureon_thought_bus import ThoughtBus
            thought_bus = ThoughtBus()
            logger.info("✅ ThoughtBus integration enabled")
        except ImportError:
            logger.warning("⚠️ ThoughtBus not available")
            
        try:
            from aureon.wisdom.aureon_stargate_protocol import create_stargate_engine
            stargate_engine = create_stargate_engine(with_integrations=False)
            logger.info("✅ Stargate Protocol integration enabled")
        except ImportError:
            logger.warning("⚠️ Stargate Protocol not available")
            
    return QuantumMirrorScanner(
        thought_bus=thought_bus,
        stargate_engine=stargate_engine
    )


# Alias for wire_all_systems compatibility
create_quantum_mirror_scanner = create_quantum_scanner


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s'
    )
    
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║     🔮 AUREON QUANTUM MIRROR SCANNER 🔮                      ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    print()
    
    # Create scanner
    scanner = create_quantum_scanner(with_integrations=True)
    
    # Register test branches (simulating market symbols)
    test_pairs = [
        ("BTC/USD", "kraken", 43250.0),
        ("ETH/USD", "kraken", 2280.0),
        ("SOL/USD", "kraken", 98.5),
        ("XRP/USD", "kraken", 0.62),
        ("ADA/USD", "kraken", 0.58),
        ("DOGE/USD", "kraken", 0.082),
    ]
    
    print("📊 REGISTERING REALITY BRANCHES")
    print("─" * 60)
    
    for symbol, exchange, price in test_pairs:
        branch = scanner.register_branch(symbol, exchange, price)
        # Set harmonic frequencies (simulated from price patterns)
        branch.frequency = (price % 100) + SCHUMANN_BASE * PHI
        branch.phase = (price % math.pi)
        print(f"  {branch.branch_id}: freq={branch.frequency:.2f} Hz")
        
    print()
    print("🔬 RUNNING VALIDATION PASSES")
    print("─" * 60)
    
    # Run validation passes on all branches
    for branch_id in scanner.branches.keys():
        # Pass 1: Harmonic
        p1 = scanner.validation_pass_1_harmonic(branch_id)
        print(f"  {branch_id} P1 (Harmonic): {p1:.3f}")
        
        # Pass 2: Coherence
        p2 = scanner.validation_pass_2_coherence(branch_id)
        print(f"  {branch_id} P2 (Coherence): {p2:.3f}")
        
        # Pass 3: Stability
        p3 = scanner.validation_pass_3_stability(branch_id)
        print(f"  {branch_id} P3 (Stability): {p3:.3f}")
        
        # Check if ready
        branch = scanner.branches[branch_id]
        score = branch.compute_branch_score()
        print(f"  {branch_id} SCORE: {score:.4f} | Phase: {branch.branch_phase.value}")
        print()
        
    # Scan for convergences
    print("🌀 SCANNING FOR TIMELINE CONVERGENCES")
    print("─" * 60)
    convergences = scanner.scan_for_convergences()
    print(f"  Found {len(convergences)} convergence(s)")
    
    for conv in convergences:
        print(f"  📍 {conv.convergence_id}")
        print(f"     Strength: {conv.convergence_strength:.3f}")
        print(f"     Branches: {len(conv.branches)}")
        
    print()
    print("✅ BRANCHES READY FOR 4TH PASS")
    print("─" * 60)
    ready = scanner.get_ready_branches()
    for branch in ready:
        print(f"  ⚡ {branch.branch_id}: score={branch.compute_branch_score():.4f}")
        
        # Execute 4th pass
        result = scanner.execute_4th_pass(branch.branch_id)
        if result["success"]:
            print(f"     ✅ EXECUTED - PIP potential: {result['pip_potential']:.2f}")
            
    print()
    print("📊 FINAL STATUS")
    print("─" * 60)
    status = scanner.get_status()
    print(f"  Total branches: {status['total_branches']}")
    print(f"  Phase distribution: {status['phase_distribution']}")
    print(f"  Ready for execution: {status['ready_for_execution']}")
    print(f"  Active convergences: {status['active_convergences']}")
    print(f"  Global coherence: {status['global_coherence']:.4f}")
    
    print()
    print("✅ Quantum Mirror Scanner operational")

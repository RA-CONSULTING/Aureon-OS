"""
Aureon Vault — Self-Feedback Unified Model
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

The system treats itself and its contents as one big vault that feeds
back on itself. Ten modules:

  AureonVault              — ring-bounded self-model, subscribes to ThoughtBus
  VaultContent             — atomic "Fibonacci card"
  FibonacciCardShuffler    — golden-ratio replay ordering
  LoveGratitudeClock       — cycle rate = base / (love × gratitude)
  CasimirQuantifier        — drift force between present and past vault
  AurisMetacognition       — 9-node deterministic voter
  HNCDeployer              — Λ(t)-driven white-cell count
  WhiteCellAgent           — immune-system recovery agent
  HarmonicPinger           — ChirpBus + ThoughtBus harmonic heartbeat
  RallyCoordinator         — high-frequency burst mode
  AureonSelfFeedbackLoop   — top-level orchestrator (tick → all of above)

Gary Leckey / Aureon Institute — 2026
"""

from aureon.vault.aureon_vault import (
    AUREON_VAULT_RELEASE_HOLD,
    AureonVault,
    VaultContent,
)
from aureon.vault.fibonacci_shuffler import (
    FibonacciCardShuffler,
    FIBONACCI_INTERVALS,
    PHI,
)
from aureon.vault.love_gratitude_clock import LoveGratitudeClock, ClockReading
from aureon.vault.casimir_quantifier import CasimirQuantifier, CasimirReading
from aureon.vault.auris_metacognition import (
    AurisMetacognition,
    AurisVoteResult,
    NodeVote,
    NODES,
    LIGHTHOUSE_THRESHOLD,
)
from aureon.vault.hnc_deployer import HNCDeployer, DeploymentDecision
from aureon.vault.white_cell import (
    WhiteCellAgent,
    ThreatReport,
    WhiteCellOutcome,
    detect_threats,
)
from aureon.vault.harmonic_pinger import HarmonicPinger, PingResult
from aureon.vault.rally_coordinator import RallyCoordinator, RallyState
from aureon.vault.self_feedback_loop import (
    AureonSelfFeedbackLoop,
    TickResult,
    get_self_feedback_loop,
)
from aureon.vault.voice import (
    Utterance,
    VoiceStatement,
    ChoiceGate,
    ChoiceGateDecision,
    VaultVoice,
    QueenVoice,
    MinerVoice,
    ScoutVoice,
    CouncilVoice,
    ArchitectVoice,
    LoverVoice,
    build_all_voices,
    SelfDialogueEngine,
    ThoughtStreamLoop,
)

__all__ = [
    # Vault core
    "AureonVault",
    "AUREON_VAULT_RELEASE_HOLD",
    "VaultContent",
    # Shuffler
    "FibonacciCardShuffler",
    "FIBONACCI_INTERVALS",
    "PHI",
    # Clock
    "LoveGratitudeClock",
    "ClockReading",
    # Casimir
    "CasimirQuantifier",
    "CasimirReading",
    # Auris
    "AurisMetacognition",
    "AurisVoteResult",
    "NodeVote",
    "NODES",
    "LIGHTHOUSE_THRESHOLD",
    # HNC
    "HNCDeployer",
    "DeploymentDecision",
    # White cell
    "WhiteCellAgent",
    "ThreatReport",
    "WhiteCellOutcome",
    "detect_threats",
    # Pinger
    "HarmonicPinger",
    "PingResult",
    # Rally
    "RallyCoordinator",
    "RallyState",
    # Top-level
    "AureonSelfFeedbackLoop",
    "TickResult",
    "get_self_feedback_loop",
    # Voice layer
    "Utterance",
    "VoiceStatement",
    "ChoiceGate",
    "ChoiceGateDecision",
    "VaultVoice",
    "QueenVoice",
    "MinerVoice",
    "ScoutVoice",
    "CouncilVoice",
    "ArchitectVoice",
    "LoverVoice",
    "build_all_voices",
    "SelfDialogueEngine",
    "ThoughtStreamLoop",
]

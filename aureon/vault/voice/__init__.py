"""
Aureon Vault Voice — The System Speaks to Itself
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

The voice layer gives the self-feedback vault the ability to write its
own prompts and have conversations with itself through its own thought
processes — not scripted, as it chooses.

Five modules:

  utterance.py          — VoiceStatement + Utterance dataclasses
  choice_gate.py        — ChoiceGate decides WHEN the vault speaks
  vault_voice.py        — Seven personas: Vault, Queen, Miner, Scout,
                          Council, Architect, Lover. Each composes
                          self-authored prompts from vault state.
  self_dialogue.py      — SelfDialogueEngine orchestrates exchanges
                          between voices, feeding outputs back into
                          the vault so each voice shapes the next.
  thought_stream_loop.py — Background daemon that runs the dialogue
                          engine at the love+gratitude cadence.

Gary Leckey / Aureon Institute — 2026
"""

from aureon.vault.voice.utterance import Utterance, VoiceStatement
from aureon.vault.voice.choice_gate import ChoiceGate, ChoiceGateDecision
from aureon.vault.voice.vault_voice import (
    VaultVoice,
    QueenVoice,
    MinerVoice,
    ScoutVoice,
    CouncilVoice,
    ArchitectVoice,
    LoverVoice,
    VOICE_REGISTRY,
    build_all_voices,
)
from aureon.vault.voice.self_dialogue import (
    SelfDialogueEngine,
    DEFAULT_VOICE_WEIGHTS,
)
from aureon.vault.voice.thought_stream_loop import (
    ThoughtStreamLoop,
    ThoughtStreamStatus,
)
from aureon.vault.voice.aureon_personas import (
    ResonantPersona,
    PainterVoice,
    ArtistVoice,
    QuantumPhysicistVoice,
    PhilosopherVoice,
    ChildVoice,
    ElderVoice,
    MysticVoice,
    EngineerVoice,
    LeftVoice,
    RightVoice,
    AUREON_PERSONA_REGISTRY,
    build_aureon_personas,
)
from aureon.vault.voice.persona_vacuum import (
    PERSONA_VACUUM_RELEASE_HOLD,
    PersonaVacuum,
    get_persona_vacuum,
)
from aureon.vault.voice.persona_action import (
    PERSONA_ACTION_RELEASE_HOLD,
    PersonaAction,
    ActionExecution,
    PersonaActuator,
)
from aureon.vault.voice.affinity_chorus import (
    AFFINITY_CHORUS_RELEASE_HOLD,
    AffinityChorus,
    AffinityContribution,
    DEFAULT_TTL_S as CHORUS_DEFAULT_TTL_S,
    vault_fingerprint_seed,
    make_vault_seed_fn,
)
from aureon.vault.voice.life_context import (
    LIFE_CONTEXT_RELEASE_HOLD,
    LifeContext,
    LifeEvent,
)
from aureon.vault.voice.opportunity_scanner import (
    OPPORTUNITY_SCANNER_RELEASE_HOLD,
    OpportunityScanner,
    OpportunityHit,
)
from aureon.vault.voice.symbolic_life_bridge import (
    SYMBOLIC_LIFE_RELEASE_HOLD,
    SymbolicLifeBridge,
)
from aureon.vault.voice.temporal_causality import (
    TEMPORAL_CAUSALITY_RELEASE_HOLD,
    GoalEcho,
    GoalState,
    TemporalCausalityLaw,
    get_temporal_causality_law,
    reset_temporal_causality_law,
)
from aureon.vault.voice.goal_dispatch_bridge import (
    GOAL_DISPATCH_RELEASE_HOLD,
    GoalDispatchBridge,
    get_goal_dispatch_bridge,
    reset_goal_dispatch_bridge,
)
from aureon.vault.voice.bus_flight_check import (
    BUS_FLIGHT_CHECK_RELEASE_HOLD,
    BusFlightCheck,
    get_bus_flight_check,
    reset_bus_flight_check,
)
from aureon.vault.voice.vault_feed_audit import (
    VAULT_FEED_AUDIT_RELEASE_HOLD,
    VaultFeedAudit,
)
from aureon.vault.voice.hash_resonance_index import (
    HASH_RESONANCE_RELEASE_HOLD,
    HashResonanceIndex,
    BondRecord,
    bond_strength,
)
from aureon.vault.voice.meta_cognition_observer import (
    META_COGNITION_RELEASE_HOLD,
    MetaCognitionObserver,
    ReflectionCard,
    get_meta_cognition_observer,
    reset_meta_cognition_observer,
)
from aureon.vault.voice.persona_miner_bridge import (
    PERSONA_MINER_RELEASE_HOLD,
    PersonaMinerBridge,
    MinerPacket,
    PersonaStats,
    IntentStats,
    get_persona_miner_bridge,
    reset_persona_miner_bridge,
)
from aureon.vault.voice.goal_skill_aligner import (
    GOAL_SKILL_ALIGNER_RELEASE_HOLD,
    GoalSkillAligner,
    get_goal_skill_aligner,
    reset_goal_skill_aligner,
)
from aureon.vault.voice.skill_executor_bridge import (
    SKILL_EXECUTOR_RELEASE_HOLD,
    SkillExecutorBridge,
    code_architect_adapter,
    get_skill_executor_bridge,
    reset_skill_executor_bridge,
)
from aureon.vault.voice._goal_claims import GoalClaims
from aureon.vault.voice.whole_knowledge_voice import (
    WHOLE_KNOWLEDGE_VOICE_RELEASE_HOLD,
    FACETS as WHOLE_KNOWLEDGE_VOICE_FACETS,
    ExpressionProfile,
    RuntimeTranslation,
    VoiceArtifact,
    build_expression_profile,
    compose_voice_artifact,
    translate_runtime_state,
)

__all__ = [
    # Utterance
    "Utterance",
    "VoiceStatement",
    # Choice gate
    "ChoiceGate",
    "ChoiceGateDecision",
    # Voices
    "VaultVoice",
    "QueenVoice",
    "MinerVoice",
    "ScoutVoice",
    "CouncilVoice",
    "ArchitectVoice",
    "LoverVoice",
    "VOICE_REGISTRY",
    "build_all_voices",
    # Dialogue engine
    "SelfDialogueEngine",
    "DEFAULT_VOICE_WEIGHTS",
    # Thought stream loop
    "ThoughtStreamLoop",
    "ThoughtStreamStatus",
    # Resonant personas (quantum superposition layer)
    "ResonantPersona",
    "PainterVoice",
    "ArtistVoice",
    "QuantumPhysicistVoice",
    "PhilosopherVoice",
    "ChildVoice",
    "ElderVoice",
    "MysticVoice",
    "EngineerVoice",
    "LeftVoice",
    "RightVoice",
    "AUREON_PERSONA_REGISTRY",
    "build_aureon_personas",
    "PersonaVacuum",
    "PERSONA_VACUUM_RELEASE_HOLD",
    "get_persona_vacuum",
    # Action layer (speak → act)
    "PersonaAction",
    "PERSONA_ACTION_RELEASE_HOLD",
    "ActionExecution",
    "PersonaActuator",
    # Unified-collapse layer
    "AffinityChorus",
    "AFFINITY_CHORUS_RELEASE_HOLD",
    "AffinityContribution",
    "CHORUS_DEFAULT_TTL_S",
    "vault_fingerprint_seed",
    "make_vault_seed_fn",
    # Life context + opportunity scanning
    "LifeContext",
    "LIFE_CONTEXT_RELEASE_HOLD",
    "LifeEvent",
    "OpportunityScanner",
    "OPPORTUNITY_SCANNER_RELEASE_HOLD",
    "OpportunityHit",
    "SymbolicLifeBridge",
    "SYMBOLIC_LIFE_RELEASE_HOLD",
    "GoalEcho",
    "GoalState",
    "TemporalCausalityLaw",
    "TEMPORAL_CAUSALITY_RELEASE_HOLD",
    "get_temporal_causality_law",
    "reset_temporal_causality_law",
    "GoalDispatchBridge",
    "GOAL_DISPATCH_RELEASE_HOLD",
    "get_goal_dispatch_bridge",
    "reset_goal_dispatch_bridge",
    "BusFlightCheck",
    "BUS_FLIGHT_CHECK_RELEASE_HOLD",
    "get_bus_flight_check",
    "reset_bus_flight_check",
    "VaultFeedAudit",
    "VAULT_FEED_AUDIT_RELEASE_HOLD",
    "HashResonanceIndex",
    "HASH_RESONANCE_RELEASE_HOLD",
    "BondRecord",
    "bond_strength",
    "MetaCognitionObserver",
    "META_COGNITION_RELEASE_HOLD",
    "ReflectionCard",
    "get_meta_cognition_observer",
    "reset_meta_cognition_observer",
    "PersonaMinerBridge",
    "PERSONA_MINER_RELEASE_HOLD",
    "MinerPacket",
    "PersonaStats",
    "IntentStats",
    "get_persona_miner_bridge",
    "reset_persona_miner_bridge",
    "GoalSkillAligner",
    "GOAL_SKILL_ALIGNER_RELEASE_HOLD",
    "get_goal_skill_aligner",
    "reset_goal_skill_aligner",
    "SkillExecutorBridge",
    "SKILL_EXECUTOR_RELEASE_HOLD",
    "code_architect_adapter",
    "get_skill_executor_bridge",
    "reset_skill_executor_bridge",
    "GoalClaims",
    "WHOLE_KNOWLEDGE_VOICE_FACETS",
    "WHOLE_KNOWLEDGE_VOICE_RELEASE_HOLD",
    "ExpressionProfile",
    "RuntimeTranslation",
    "VoiceArtifact",
    "build_expression_profile",
    "compose_voice_artifact",
    "translate_runtime_state",
]

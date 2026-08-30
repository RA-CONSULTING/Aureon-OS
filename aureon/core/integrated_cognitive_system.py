#!/usr/bin/env python3
"""
IntegratedCognitiveSystem -- The unified orchestrator that wires everything together.

Boots all cognitive subsystems in parallel, runs a unified cognitive tick at ~1Hz,
accepts user input, and routes goals to the GoalExecutionEngine.
"""

from __future__ import annotations

import logging
import os
import sys
import threading
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger("aureon.core.ics")

# Source Law coherence thresholds for cognitive execution.
# Defaults are set for trading (0.938/0.934). The ICS lowers them to 0.5/0.45
# because we're running user-requested cognitive goals, not autonomous trades.
# Trading subsystems that import SourceLawEngine directly still use their own
# thresholds via the env var override pattern.
os.environ.setdefault("AUREON_SOURCE_LAW_ENTRY", "0.55")
os.environ.setdefault("AUREON_SOURCE_LAW_EXIT", "0.45")

# ---------------------------------------------------------------------------
# Graceful imports — every subsystem wrapped in try/except
# ---------------------------------------------------------------------------
try:
    from aureon.core.aureon_thought_bus import get_thought_bus, Thought
    _HAS_THOUGHT_BUS = True
except Exception:
    get_thought_bus = None  # type: ignore[assignment]
    Thought = None  # type: ignore[assignment,misc]
    _HAS_THOUGHT_BUS = False

try:
    from aureon.core.organism_contracts import OrganismContractStack
    _HAS_CONTRACT_STACK = True
except Exception:
    OrganismContractStack = None  # type: ignore[assignment,misc]
    _HAS_CONTRACT_STACK = False

try:
    from aureon.vault.aureon_vault import AureonVault
    _HAS_VAULT = True
except Exception:
    AureonVault = None  # type: ignore[assignment,misc]
    _HAS_VAULT = False

try:
    from aureon.core.aureon_lambda_engine import LambdaEngine, SubsystemReading
    _HAS_LAMBDA = True
except Exception:
    LambdaEngine = None  # type: ignore[assignment,misc]
    SubsystemReading = None  # type: ignore[assignment,misc]
    _HAS_LAMBDA = False

try:
    from aureon.queen.queen_cortex import get_cortex
    _HAS_CORTEX = True
except Exception:
    get_cortex = None  # type: ignore[assignment]
    _HAS_CORTEX = False

try:
    from aureon.vault.self_feedback_loop import get_self_feedback_loop
    _HAS_FEEDBACK_LOOP = True
except Exception:
    get_self_feedback_loop = None  # type: ignore[assignment]
    _HAS_FEEDBACK_LOOP = False

try:
    from aureon.queen.queen_sentient_loop import QueenSentientLoop
    _HAS_SENTIENT = True
except Exception:
    QueenSentientLoop = None  # type: ignore[assignment,misc]
    _HAS_SENTIENT = False

try:
    from aureon.autonomous.aureon_agent_core import AureonAgentCore
    _HAS_AGENT_CORE = True
except Exception:
    AureonAgentCore = None  # type: ignore[assignment,misc]
    _HAS_AGENT_CORE = False

try:
    from aureon.queen.queen_action_bridge import get_queen_action_bridge
    _HAS_ACTION_BRIDGE = True
except Exception:
    get_queen_action_bridge = None  # type: ignore[assignment]
    _HAS_ACTION_BRIDGE = False

try:
    from aureon.queen.being_model import get_being_model
    _HAS_BEING_MODEL = True
except Exception:
    get_being_model = None  # type: ignore[assignment]
    _HAS_BEING_MODEL = False

try:
    from aureon.autonomous.aureon_elephant_memory import ElephantMemory
    _HAS_ELEPHANT = True
except Exception:
    ElephantMemory = None  # type: ignore[assignment,misc]
    _HAS_ELEPHANT = False

try:
    from aureon.vault.voice.self_dialogue import SelfDialogueEngine
    _HAS_SELF_DIALOGUE = True
except Exception:
    SelfDialogueEngine = None  # type: ignore[assignment,misc]
    _HAS_SELF_DIALOGUE = False

try:
    from aureon.vault.auris_metacognition import AurisMetacognition
    _HAS_AURIS = True
except Exception:
    AurisMetacognition = None  # type: ignore[assignment,misc]
    _HAS_AURIS = False

try:
    from aureon.core.goal_execution_engine import GoalExecutionEngine
    _HAS_GOAL_ENGINE = True
except Exception:
    GoalExecutionEngine = None  # type: ignore[assignment,misc]
    _HAS_GOAL_ENGINE = False

try:
    from aureon.core.cognitive_dashboard import CognitiveDashboard
    _HAS_DASHBOARD = True
except Exception:
    CognitiveDashboard = None  # type: ignore[assignment,misc]
    _HAS_DASHBOARD = False

try:
    from aureon.harmonic.phi_bridge import get_phi_bridge
    _HAS_PHI_BRIDGE = True
except Exception:
    get_phi_bridge = None  # type: ignore[assignment]
    _HAS_PHI_BRIDGE = False

try:
    from aureon.vault.ui.server import create_app as create_vault_app, run_server as _run_vault_server
    _HAS_VAULT_UI = True
except Exception:
    create_vault_app = None  # type: ignore[assignment]
    _run_vault_server = None  # type: ignore[assignment]
    _HAS_VAULT_UI = False

try:
    from aureon.inhouse_ai.orchestrator import OpenMultiAgent
    from aureon.inhouse_ai.agent import AgentConfig
    _HAS_SWARM = True
except Exception:
    OpenMultiAgent = None  # type: ignore[assignment,misc]
    AgentConfig = None  # type: ignore[assignment,misc]
    _HAS_SWARM = False

try:
    from aureon.queen.temporal_ground import get_temporal_ground_station
    _HAS_TEMPORAL = True
except Exception:
    get_temporal_ground_station = None  # type: ignore[assignment]
    _HAS_TEMPORAL = False

try:
    from aureon.queen.queen_mycelium_mind import get_mycelium_mind
    _HAS_MYCELIUM = True
except Exception:
    get_mycelium_mind = None  # type: ignore[assignment]
    _HAS_MYCELIUM = False

try:
    from aureon.queen.queen_metacognition import QueenMetacognition as _QueenMetacognition
    _HAS_METACOGNITION = True
except Exception:
    _QueenMetacognition = None  # type: ignore[assignment,misc]
    _HAS_METACOGNITION = False

try:
    from aureon.swarm_motion.love_stream import StandingWaveLoveStream
    _HAS_LOVE_STREAM = True
except Exception:
    StandingWaveLoveStream = None  # type: ignore[assignment,misc]
    _HAS_LOVE_STREAM = False

try:
    from aureon.integrations import wire_integrations
    _HAS_INTEGRATIONS = True
except Exception:
    wire_integrations = None  # type: ignore[assignment]
    _HAS_INTEGRATIONS = False

try:
    from aureon.queen.queen_cognitive_action_planner import QueenCognitiveActionPlanner
    _HAS_COGNITIVE_PLANNER = True
except Exception:
    QueenCognitiveActionPlanner = None  # type: ignore[assignment,misc]
    _HAS_COGNITIVE_PLANNER = False

try:
    from aureon.queen.queen_conscience import QueenConscience as _QueenConscience
    _HAS_CONSCIENCE = True
except Exception:
    _QueenConscience = None  # type: ignore[assignment,misc]
    _HAS_CONSCIENCE = False

try:
    from aureon.queen.queen_source_law import SourceLawEngine
    _HAS_SOURCE_LAW = True
except Exception:
    SourceLawEngine = None  # type: ignore[assignment,misc]
    _HAS_SOURCE_LAW = False

try:
    from aureon.swarm_motion.as_above_so_below import AsAboveSoBelowMirror
    _HAS_MIRROR = True
except Exception:
    AsAboveSoBelowMirror = None  # type: ignore[assignment,misc]
    _HAS_MIRROR = False

try:
    from aureon.queen.queen_prose_composer import QueenProseComposer
    _HAS_PROSE = True
except Exception:
    QueenProseComposer = None  # type: ignore[assignment,misc]
    _HAS_PROSE = False

try:
    from aureon.queen.temporal_knowledge import get_temporal_knowledge
    _HAS_TKB = True
except Exception:
    get_temporal_knowledge = None  # type: ignore[assignment]
    _HAS_TKB = False

try:
    from aureon.intelligence.aureon_temporal_dialer import TemporalDialer, DialMode
    _HAS_DIALER = True
except Exception:
    TemporalDialer = None  # type: ignore[assignment,misc]
    DialMode = None  # type: ignore[assignment,misc]
    _HAS_DIALER = False

try:
    from aureon.wisdom.aureon_math_angel import NexusSystem
    _HAS_NEXUS = True
except Exception:
    NexusSystem = None  # type: ignore[assignment,misc]
    _HAS_NEXUS = False

try:
    from aureon.queen.knowledge_dataset import get_knowledge_dataset
    _HAS_KNOWLEDGE_DATASET = True
except Exception:
    get_knowledge_dataset = None  # type: ignore[assignment]
    _HAS_KNOWLEDGE_DATASET = False

try:
    from aureon.queen.queen_stash_pockets import get_stash_pockets
    _HAS_STASH_POCKETS = True
except Exception:
    get_stash_pockets = None  # type: ignore[assignment]
    _HAS_STASH_POCKETS = False

try:
    from aureon.queen.knowledge_interpreter import get_knowledge_interpreter
    _HAS_INTERPRETER = True
except Exception:
    get_knowledge_interpreter = None  # type: ignore[assignment]
    _HAS_INTERPRETER = False

try:
    from aureon.integrations.world_data import get_world_data_ingester
    _HAS_WORLD_DATA = True
except Exception:
    get_world_data_ingester = None  # type: ignore[assignment]
    _HAS_WORLD_DATA = False

try:
    from aureon.queen.self_research_loop import get_self_research_loop
    _HAS_SELF_RESEARCH = True
except Exception:
    get_self_research_loop = None  # type: ignore[assignment]
    _HAS_SELF_RESEARCH = False

try:
    from aureon.queen.vault_knowledge_bridge import get_vault_knowledge_bridge
    _HAS_VAULT_BRIDGE = True
except Exception:
    get_vault_knowledge_bridge = None  # type: ignore[assignment]
    _HAS_VAULT_BRIDGE = False

try:
    from aureon.data_feeds.market_data_refresher import start_refresher as _start_market_refresher, stop_refresher as _stop_market_refresher
    _HAS_MARKET_REFRESHER = True
except Exception:
    _start_market_refresher = None  # type: ignore[assignment]
    _stop_market_refresher = None  # type: ignore[assignment]
    _HAS_MARKET_REFRESHER = False

try:
    from aureon.queen.accounting_context_bridge import get_accounting_context_bridge
    _HAS_ACCOUNTING_CONTEXT = True
except Exception:
    get_accounting_context_bridge = None  # type: ignore[assignment]
    _HAS_ACCOUNTING_CONTEXT = False

try:
    from aureon.autonomous.hnc_saas_cognitive_bridge import SaaSCognitiveBridge
    _HAS_SAAS_COGNITIVE_BRIDGE = True
except Exception:
    SaaSCognitiveBridge = None  # type: ignore[assignment,misc]
    _HAS_SAAS_COGNITIVE_BRIDGE = False

try:
    from aureon.exchanges.capital_cfd_trader import set_module_lambda_engine as _set_capital_lambda
    _HAS_CAPITAL_TRADER = True
except Exception:
    _set_capital_lambda = None  # type: ignore[assignment]
    _HAS_CAPITAL_TRADER = False


# ═══════════════════════════════════════════════════════════════════════════════
# IntegratedCognitiveSystem
# ═══════════════════════════════════════════════════════════════════════════════

class IntegratedCognitiveSystem:
    """
    The unified wire that boots all cognitive subsystems, runs them as one
    organism, accepts user goals, and shows the feedback loop live.
    """

    def __init__(self) -> None:
        # Subsystem references (populated during boot)
        self.thought_bus: Any = None
        self.vault: Any = None
        self.lambda_engine: Any = None
        self.cortex: Any = None
        self.feedback_loop: Any = None
        self.sentient_loop: Any = None
        self.agent_core: Any = None
        self.action_bridge: Any = None
        self.being_model: Any = None
        self.elephant_memory: Any = None
        self.self_dialogue: Any = None
        self.auris: Any = None
        self.goal_engine: Any = None
        self.dashboard: Any = None
        self.phi_bridge: Any = None
        self.vault_app: Any = None
        self.swarm: Any = None           # OpenMultiAgent orchestrator
        self.temporal_ground: Any = None  # TemporalGroundStation
        self.mycelium_mind: Any = None   # Thought propagation + synaptic learning
        self.metacognition: Any = None   # 5W self-reflection loop
        self.love_stream: Any = None    # 528 Hz love stream + Λ(t) synthesis
        self.conscience: Any = None     # Ethical compass (Jiminy Cricket)
        self.source_law: Any = None    # The Emerald Tablet — 10-9-1 decision funnel
        self.mirror: Any = None        # As Above So Below — Hermetic reflection
        self.prose_composer: Any = None # Queen's self-description in natural language
        self.temporal_knowledge: Any = None # Time-indexed event knowledge for agents
        self.temporal_dialer: Any = None # HNC frequency tuner — closes the feedback loop
        self.nexus_system: Any = None    # Math angle protocol — coherence + phase
        self.knowledge_dataset: Any = None # Crystallized knowledge from stash pockets
        self.stash_pockets: Any = None   # Per-goal scratch pads — stop leaning on LLM
        self.knowledge_interpreter: Any = None # Swarm-driven understanding pass
        self.world_data_ingester: Any = None # Free-API world news / wiki / yahoo
        self.self_research_loop: Any = None # Active self-question research loop
        self.vault_knowledge_bridge: Any = None # Vault -> interpreter -> dataset sync
        self.cognitive_planner: Any = None     # Ollama-powered autonomous goal synthesiser
        self.accounting_context: Any = None    # Final-ready accounts/compliance context bridge
        self.saas_cognition: Any = None        # HNC SaaS unhackable pursuit cognitive bridge
        self.contract_stack: Any = None        # Goal/task/job/work-order contract spine

        # State
        self._running = False
        self._tick_thread: Optional[threading.Thread] = None
        self._vault_ui_thread: Optional[threading.Thread] = None
        self._market_refresher = None
        self._boot_status: Dict[str, str] = {}
        self._tick_count = 0
        self._vault_ui_port: int = 5566
        self._vault_ui_host: str = "127.0.0.1"

    # ------------------------------------------------------------------
    # Boot sequence
    # ------------------------------------------------------------------
    def boot(self) -> Dict[str, str]:
        """
        13-phase boot sequence. Each phase in try/except for graceful
        degradation. Returns {subsystem_name: "alive"|"failed"|"skipped"}.
        """
        status: Dict[str, str] = {}

        # Activate Queen autonomous control in background — importing
        # aureon_queen_hive_mind pulls a heavy dependency chain that can
        # take 30+ seconds; don't block the boot sequence.
        def _do_activate():
            try:
                from aureon.core.aureon_baton_link import activate_autonomous_control
                activate_autonomous_control()
            except Exception:
                pass
        threading.Thread(target=_do_activate, daemon=True, name="ICS.auto_ctrl").start()

        def _boot_phase(name: str, fn):
            try:
                fn()
                status[name] = "alive"
                self._publish_boot(name, "alive")
            except Exception as exc:
                status[name] = f"failed: {exc}"
                self._publish_boot(name, f"failed: {exc}")
                logger.warning("Boot %s failed: %s", name, exc)

        # Phase 1: ThoughtBus
        def boot_thought_bus():
            if not _HAS_THOUGHT_BUS:
                raise RuntimeError("import failed")
            self.thought_bus = get_thought_bus()
        _boot_phase("thought_bus", boot_thought_bus)

        # Phase 1.5: Organism contract stack (goals -> tasks -> jobs -> work orders)
        def boot_contract_stack():
            if not _HAS_CONTRACT_STACK:
                raise RuntimeError("import failed")
            self.contract_stack = OrganismContractStack(
                thought_bus=self.thought_bus,
                state_path="state/organism_contract_stack.json",
                source="integrated_cognitive_system",
            )
            self.contract_stack.publish_status()
        _boot_phase("contract_stack", boot_contract_stack)

        # Phase 2: Vault
        def boot_vault():
            if not _HAS_VAULT:
                raise RuntimeError("import failed")
            self.vault = AureonVault()
            self.vault.wire_thought_bus()
        _boot_phase("vault", boot_vault)

        # Phase 2.1: Accounting context bridge (final-ready accounts/compliance)
        def boot_accounting_context():
            if not _HAS_ACCOUNTING_CONTEXT:
                raise RuntimeError("import failed")
            self.accounting_context = get_accounting_context_bridge()
            self.accounting_context.load_context()
            self.accounting_context.ingest_to_vault(self.vault, force=False)
            if self.thought_bus is not None:
                self.accounting_context.publish_status(
                    self.thought_bus,
                    topic="accounting.context.ready",
                )
        _boot_phase("accounting_context", boot_accounting_context)

        # Phase 2.2: HNC SaaS cognitive bridge (unhackable pursuit loop)
        def boot_saas_cognition():
            if not _HAS_SAAS_COGNITIVE_BRIDGE:
                raise RuntimeError("import failed")
            self.saas_cognition = SaaSCognitiveBridge(
                thought_bus=self.thought_bus,
                contract_stack=self.contract_stack,
                vault=self.vault,
            )
            self.saas_cognition.load_context()
            self.saas_cognition.ingest_to_vault(self.vault, force=False)
            if self.thought_bus is not None:
                self.saas_cognition.publish_ready()
        _boot_phase("saas_cognition", boot_saas_cognition)

        # Phase 2.5: Temporal Knowledge Base (subscribes to ThoughtBus
        # immediately so it captures every event from boot onwards)
        def boot_tkb():
            if not _HAS_TKB:
                raise RuntimeError("import failed")
            self.temporal_knowledge = get_temporal_knowledge()
            if self.thought_bus is not None:
                self.temporal_knowledge.subscribe_to(self.thought_bus)
        _boot_phase("temporal_knowledge", boot_tkb)

        # Phase 2.6: Temporal Dialer (HNC frequency tuner — closes the
        # feedback loop between TKB and the Lambda field)
        def boot_dialer():
            if not _HAS_DIALER:
                raise RuntimeError("import failed")
            self.temporal_dialer = TemporalDialer(name="ICS_Dialer")
            self.temporal_dialer.calibrate()
        _boot_phase("temporal_dialer", boot_dialer)

        # Phase 3: Self-Dialogue Engine (needs vault)
        def boot_self_dialogue():
            if not _HAS_SELF_DIALOGUE:
                raise RuntimeError("import failed")
            self.self_dialogue = SelfDialogueEngine(vault=self.vault)
        _boot_phase("self_dialogue", boot_self_dialogue)

        # Phase 4: Lambda Engine
        def boot_lambda():
            if not _HAS_LAMBDA:
                raise RuntimeError("import failed")
            self.lambda_engine = LambdaEngine()
        _boot_phase("lambda_engine", boot_lambda)

        # Phase 5: Queen Cortex
        def boot_cortex():
            if not _HAS_CORTEX:
                raise RuntimeError("import failed")
            self.cortex = get_cortex()
            self.cortex.start()
        _boot_phase("cortex", boot_cortex)

        # Phase 6: Self-Feedback Loop
        def boot_feedback():
            if not _HAS_FEEDBACK_LOOP:
                raise RuntimeError("import failed")
            self.feedback_loop = get_self_feedback_loop(vault=self.vault)
            self.feedback_loop.start()
        _boot_phase("feedback_loop", boot_feedback)

        # Phase 7: Sentient Loop
        def boot_sentient():
            if not _HAS_SENTIENT:
                raise RuntimeError("import failed")
            self.sentient_loop = QueenSentientLoop(think_interval=1.0)
            self.sentient_loop.start()
        _boot_phase("sentient_loop", boot_sentient)

        # Phase 8: Mycelium Mind (thought propagation + synaptic learning)
        def boot_mycelium():
            if not _HAS_MYCELIUM:
                raise RuntimeError("import failed")
            self.mycelium_mind = get_mycelium_mind()
            self.mycelium_mind.start()
        _boot_phase("mycelium_mind", boot_mycelium)

        # Phase 9: Queen Metacognition (5W self-reflection loop)
        def boot_metacognition():
            if not _HAS_METACOGNITION:
                raise RuntimeError("import failed")
            self.metacognition = _QueenMetacognition()
            self.metacognition.start()
        _boot_phase("metacognition", boot_metacognition)

        # Phase 10: Love Stream (528 Hz love signal → vault love_amplitude)
        def boot_love_stream():
            if not _HAS_LOVE_STREAM:
                raise RuntimeError("import failed")
            self.love_stream = StandingWaveLoveStream(sample_rate_hz=1.0)
            self.love_stream.start()
        _boot_phase("love_stream", boot_love_stream)

        # Phase 11: Conscience (ethical compass — Jiminy Cricket)
        def boot_conscience():
            if not _HAS_CONSCIENCE:
                raise RuntimeError("import failed")
            self.conscience = _QueenConscience()
        _boot_phase("conscience", boot_conscience)

        # Phase 12: Source Law Engine (The Emerald Tablet — 10-9-1 decision funnel)
        def boot_source_law():
            if not _HAS_SOURCE_LAW:
                raise RuntimeError("import failed")
            self.source_law = SourceLawEngine()
            self.source_law.start()
        _boot_phase("source_law", boot_source_law)

        # Phase 13: As Above So Below Mirror (Hermetic reflection)
        def boot_mirror():
            if not _HAS_MIRROR or self.love_stream is None:
                raise RuntimeError("import failed or love_stream not available")
            self.mirror = AsAboveSoBelowMirror(love_stream=self.love_stream)
            self.mirror.start()
        _boot_phase("mirror", boot_mirror)

        # Phase 14: Agent Core
        def boot_agent():
            if not _HAS_AGENT_CORE:
                raise RuntimeError("import failed")
            self.agent_core = AureonAgentCore()
        _boot_phase("agent_core", boot_agent)

        # Phase 11: Action Bridge
        def boot_bridge():
            if not _HAS_ACTION_BRIDGE:
                raise RuntimeError("import failed")
            self.action_bridge = get_queen_action_bridge()
        _boot_phase("action_bridge", boot_bridge)

        # Phase 12: Being Model
        def boot_being():
            if not _HAS_BEING_MODEL:
                raise RuntimeError("import failed")
            self.being_model = get_being_model()
        _boot_phase("being_model", boot_being)

        # Phase 13: Elephant Memory
        def boot_elephant():
            if not _HAS_ELEPHANT:
                raise RuntimeError("import failed")
            self.elephant_memory = ElephantMemory()
        _boot_phase("elephant_memory", boot_elephant)

        # Phase 14: Swarm (OpenMultiAgent — parallel agent teams)
        def boot_swarm():
            if not _HAS_SWARM:
                raise RuntimeError("import failed")
            self.swarm = OpenMultiAgent()
        _boot_phase("swarm", boot_swarm)

        # Phase 15: Temporal Ground (timeline forking / multiverse hash)
        def boot_temporal():
            if not _HAS_TEMPORAL:
                raise RuntimeError("import failed")
            self.temporal_ground = get_temporal_ground_station(thought_bus=self.thought_bus)
        _boot_phase("temporal_ground", boot_temporal)

        # Phase 15.5: Math Angle Protocol (NexusSystem) — coherence math
        # used by knowledge dataset to score fragment alignment WITHOUT LLM
        def boot_nexus():
            if not _HAS_NEXUS:
                raise RuntimeError("import failed")
            self.nexus_system = NexusSystem(n_observers=7)
        _boot_phase("nexus_system", boot_nexus)

        # Phase 15.6: Knowledge Dataset — crystallizes stash pocket dumps
        # into a queryable, persistent, phase-coherent knowledge base
        def boot_knowledge_dataset():
            if not _HAS_KNOWLEDGE_DATASET:
                raise RuntimeError("import failed")
            self.knowledge_dataset = get_knowledge_dataset(
                nexus_system=self.nexus_system,
            )
        _boot_phase("knowledge_dataset", boot_knowledge_dataset)

        # Phase 15.65: Knowledge Interpreter — turns raw dumps into
        # structured logic (data_type, category, meaning, related)
        # via 4 deterministic passes. No LLM dependency.
        def boot_interpreter():
            if not _HAS_INTERPRETER:
                raise RuntimeError("import failed")
            self.knowledge_interpreter = get_knowledge_interpreter(
                swarm=self.swarm,
                knowledge_dataset=self.knowledge_dataset,
                nexus_system=self.nexus_system,
                use_llm=False,  # deterministic by default
            )
        _boot_phase("knowledge_interpreter", boot_interpreter)

        # Phase 15.7: Stash Pockets — per-goal scratch pads. Agents dump
        # intermediate findings here, on close they pass through the
        # interpreter, crystallize into the dataset, and flow into
        # elephant memory.
        def boot_stash_pockets():
            if not _HAS_STASH_POCKETS:
                raise RuntimeError("import failed")
            self.stash_pockets = get_stash_pockets(
                elephant_memory=self.elephant_memory,
                knowledge_dataset=self.knowledge_dataset,
                nexus_system=self.nexus_system,
                temporal_knowledge=self.temporal_knowledge,
                thought_bus=self.thought_bus,
                knowledge_interpreter=self.knowledge_interpreter,
            )
        _boot_phase("stash_pockets", boot_stash_pockets)

        # Phase 16: Goal Engine (wired to all above)
        def boot_goal_engine():
            if not _HAS_GOAL_ENGINE:
                raise RuntimeError("import failed")
            self.goal_engine = GoalExecutionEngine(
                agent_core=self.agent_core,
                thought_bus=self.thought_bus,
                lambda_engine=self.lambda_engine,
                elephant_memory=self.elephant_memory,
                self_dialogue=self.self_dialogue,
                auris=self.auris,
                vault=self.vault,
                swarm=self.swarm,
                temporal_ground=self.temporal_ground,
                source_law=self.source_law,
                temporal_knowledge=self.temporal_knowledge,
                stash_pockets=self.stash_pockets,
                knowledge_dataset=self.knowledge_dataset,
            )
        _boot_phase("goal_engine", boot_goal_engine)

        # Phase 16.5: Cognitive Action Planner (Ollama goal synthesiser)
        # Starts now without an Ollama adapter — wiring.py injects it
        # once Ollama health check passes (async in Phase 23).
        def boot_cognitive_planner():
            if not _HAS_COGNITIVE_PLANNER:
                raise RuntimeError("import failed")
            self.cognitive_planner = QueenCognitiveActionPlanner(
                goal_engine=self.goal_engine,
                thought_bus=self.thought_bus,
            )
            self.cognitive_planner.start()
        _boot_phase("cognitive_planner", boot_cognitive_planner)

        # Phase 16.7: Capital CFD Trader — wire Λ(t) into scoring engine.
        # Sets module-level lambda reference so any CapitalCFDTrader instance
        # (created now or later) picks up the live field automatically.
        def boot_capital_wiring():
            if not _HAS_CAPITAL_TRADER or _set_capital_lambda is None:
                raise RuntimeError("capital_cfd_trader import failed")
            if self.lambda_engine is None:
                raise RuntimeError("lambda_engine not booted")
            _set_capital_lambda(self.lambda_engine)
        _boot_phase("capital_lambda_wiring", boot_capital_wiring)

        # Phase 17: Dashboard (state collector via ThoughtBus)
        def boot_dashboard():
            if not _HAS_DASHBOARD:
                raise RuntimeError("import failed")
            self.dashboard = CognitiveDashboard(thought_bus=self.thought_bus)
        _boot_phase("dashboard", boot_dashboard)

        # Phase 18: Auris Metacognition (9-node voter)
        def boot_auris():
            if not _HAS_AURIS:
                raise RuntimeError("import failed")
            self.auris = AurisMetacognition()
        _boot_phase("auris", boot_auris)

        # Phase 19: Phi Bridge (phone <-> desktop vault sync)
        def boot_phi_bridge():
            if not _HAS_PHI_BRIDGE:
                raise RuntimeError("import failed")
            self.phi_bridge = get_phi_bridge(vault=self.vault)
        _boot_phase("phi_bridge", boot_phi_bridge)

        # Phase 20: Vault UI (Flask server for phone bridge + web chat)
        def boot_vault_ui():
            if not _HAS_VAULT_UI:
                raise RuntimeError("import failed")
            self.vault_app = create_vault_app(loop=self.feedback_loop)
        _boot_phase("vault_ui", boot_vault_ui)

        # Phase 22.5: World Data Ingester — pulls live data from FREE
        # APIs (Wikipedia, Yahoo Finance, CoinGecko, Hacker News, Reddit,
        # GDELT) into the vault. No keys required.
        def boot_world_data():
            if not _HAS_WORLD_DATA:
                raise RuntimeError("import failed")
            self.world_data_ingester = get_world_data_ingester(
                vault=self.vault,
                thought_bus=self.thought_bus,
            )
        _boot_phase("world_data_ingester", boot_world_data)

        # Phase 22.6: Self-Research Loop — actively researches the system's
        # own questions. Background thread that finds question-type
        # fragments, generates queries, pulls answers via the ingester,
        # and crystallizes results back into the knowledge dataset.
        def boot_self_research():
            if not _HAS_SELF_RESEARCH:
                raise RuntimeError("import failed")
            self.self_research_loop = get_self_research_loop(
                knowledge_dataset=self.knowledge_dataset,
                world_data_ingester=self.world_data_ingester,
                stash_pockets=self.stash_pockets,
                thought_bus=self.thought_bus,
                interval_s=120.0,  # research every 2 minutes
                max_questions_per_cycle=2,
            )
            self.self_research_loop.start()
        _boot_phase("self_research_loop", boot_self_research)

        # Phase 22.7: Vault Knowledge Bridge — continuous vault → dataset
        # sync so every new card flows through the interpreter and gets
        # self-organised against the existing structure in real time.
        def boot_vault_bridge():
            if not _HAS_VAULT_BRIDGE:
                raise RuntimeError("import failed")
            self.vault_knowledge_bridge = get_vault_knowledge_bridge(
                vault=self.vault,
                knowledge_dataset=self.knowledge_dataset,
                knowledge_interpreter=self.knowledge_interpreter,
                stash_pockets=self.stash_pockets,
                thought_bus=self.thought_bus,
                sync_interval_s=30.0,
                self_organize_every_n_absorbs=15,
            )
            self.vault_knowledge_bridge.start()
        _boot_phase("vault_knowledge_bridge", boot_vault_bridge)

        # Phase 23: Wire integrations (Ollama + Obsidian into vault/loop)
        # Run in background — OllamaBridge.health_check() uses a 120s default
        # timeout; if Ollama is not running this blocks the entire boot.
        # Aureon functions without Ollama (voices fall back to AureonBrainAdapter).
        def boot_integrations():
            if not _HAS_INTEGRATIONS:
                raise RuntimeError("import failed")
            def _do_wire():
                try:
                    result = wire_integrations(
                        vault=self.vault,
                        loop=self.feedback_loop,
                        goal_engine=self.goal_engine,
                    )
                    # Also inject Ollama into the cognitive planner once available
                    if (
                        result is not None
                        and result.ollama_adapter is not None
                        and self.cognitive_planner is not None
                        and hasattr(self.cognitive_planner, "set_ollama_adapter")
                    ):
                        self.cognitive_planner.set_ollama_adapter(result.ollama_adapter)
                except Exception:
                    pass
            threading.Thread(target=_do_wire, daemon=True, name="ICS.integrations").start()
        _boot_phase("integrations", boot_integrations)

        # Phase 26: Prose Composer (self-description from real state)
        def boot_prose():
            if not _HAS_PROSE:
                raise RuntimeError("import failed")
            self.prose_composer = QueenProseComposer(
                being_model=self.being_model,
                lambda_engine=self.lambda_engine,
                vault=self.vault,
                elephant_memory=self.elephant_memory,
                auris=self.auris,
                source_law=self.source_law,
                cortex=self.cortex,
                goal_engine=self.goal_engine,
                agent_core=self.agent_core,
                subsystem_status=status,
                temporal_knowledge=self.temporal_knowledge,
                knowledge_dataset=self.knowledge_dataset,
            )
        _boot_phase("prose_composer", boot_prose)

        self._boot_status = status
        return status

    def _publish_boot(self, subsystem: str, status: str) -> None:
        if self.thought_bus is not None:
            try:
                self.thought_bus.publish(
                    "ics.boot.progress",
                    {"subsystem": subsystem, "status": status},
                    source="ics",
                )
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Unified cognitive tick (~1Hz background thread)
    # ------------------------------------------------------------------
    def _start_tick_thread(self) -> None:
        self._running = True
        self._tick_thread = threading.Thread(
            target=self._tick_loop, name="ics-tick", daemon=True,
        )
        self._tick_thread.start()

    def _tick_loop(self) -> None:
        while self._running:
            try:
                self._unified_cognitive_tick()
            except Exception as exc:
                logger.debug("Tick error: %s", exc)
            time.sleep(1.0)

    def _unified_cognitive_tick(self) -> None:
        """
        Runs at ~1Hz. Five phases collecting state from each subsystem
        and publishing to ThoughtBus for the dashboard.
        """
        self._tick_count += 1
        bus = self.thought_bus
        if bus is None:
            return

        # BODY: Agent status
        body_state: Dict[str, Any] = {"tools": 0, "vm_sessions": 0, "actions": 0, "last_action": ""}
        if self.agent_core is not None:
            try:
                stats = self.agent_core.get_stats()
                caps = self.agent_core.get_capabilities()
                body_state["tools"] = len(caps) if isinstance(caps, list) else 0
                body_state["actions"] = stats.get("calls", 0)
                body_state["last_action"] = ""
            except Exception:
                pass
        try:
            bus.publish("ics.body.state", body_state, source="ics")
        except Exception:
            pass

        # CONTRACTS: internal goal/task/job/work-order stack.
        if self.contract_stack is not None and (self._tick_count == 1 or self._tick_count % 60 == 0):
            try:
                self.contract_stack.publish_status()
            except Exception:
                pass

        # MIND: Cortex band snapshot
        mind_state: Dict[str, Any] = {"delta": 0.0, "theta": 0.0, "alpha": 0.0, "beta": 0.0, "gamma": 0.0}
        if self.cortex is not None:
            try:
                cs = self.cortex.get_state()
                for band_name in ("delta", "theta", "alpha", "beta", "gamma"):
                    band = cs.band(band_name)
                    mind_state[band_name] = band.amplitude if hasattr(band, "amplitude") else 0.0
            except Exception:
                pass
        try:
            bus.publish("ics.mind.state", mind_state, source="ics")
        except Exception:
            pass

        # SOURCE: Lambda engine step
        source_state: Dict[str, Any] = {
            "lambda_t": 0.0, "coherence_gamma": 0.0, "consciousness_psi": 0.0,
            "consciousness_level": "DORMANT", "symbolic_life_score": 0.0,
        }
        if self.lambda_engine is not None:
            try:
                # Build readings from SUBSYSTEM HEALTH (not empty cortex bands).
                # Each alive subsystem = confident 1.0 reading.
                # Cortex bands add their amplitude/coherence too.
                # When all subsystems are healthy, coherence_gamma → ~1.0
                readings = []
                if _HAS_LAMBDA:
                    subsystem_health = [
                        ("thought_bus",     self.thought_bus is not None),
                        ("contract_stack",  self.contract_stack is not None),
                        ("vault",           self.vault is not None),
                        ("accounting",      self.accounting_context is not None),
                        ("saas_cognition",  self.saas_cognition is not None),
                        ("lambda",          True),  # self
                        ("cortex",          self.cortex is not None),
                        ("feedback_loop",   self.feedback_loop is not None),
                        ("sentient_loop",   self.sentient_loop is not None),
                        ("mycelium_mind",   self.mycelium_mind is not None),
                        ("metacognition",   self.metacognition is not None),
                        ("love_stream",     self.love_stream is not None),
                        ("conscience",      self.conscience is not None),
                        ("source_law",      self.source_law is not None),
                        ("agent_core",      self.agent_core is not None),
                        ("being_model",     self.being_model is not None),
                        ("elephant_memory", self.elephant_memory is not None),
                        ("swarm",           self.swarm is not None),
                        ("temporal_ground", self.temporal_ground is not None),
                        ("goal_engine",     self.goal_engine is not None),
                        ("auris",           self.auris is not None),
                        ("phi_bridge",      self.phi_bridge is not None),
                        ("vault_app",       self.vault_app is not None),
                    ]
                    for name, alive in subsystem_health:
                        readings.append(SubsystemReading(
                            name=name,
                            value=1.0 if alive else 0.0,
                            confidence=0.95 if alive else 0.1,
                            state="active" if alive else "down",
                        ))
                    # Add cortex bands as enrichment (do not dominate)
                    if self.cortex is not None:
                        try:
                            cs = self.cortex.get_state()
                            for band_name in ("delta", "theta", "alpha", "beta", "gamma"):
                                band = cs.band(band_name)
                                amp = getattr(band, "amplitude", 0.0)
                                coh = getattr(band, "coherence", 0.5)
                                # Normalise amplitude so a silent band still
                                # reads as "healthy baseline" not zero
                                readings.append(SubsystemReading(
                                    name=f"band_{band_name}",
                                    value=max(0.5, amp),
                                    confidence=max(0.5, coh),
                                    state="active",
                                ))
                        except Exception:
                            pass

                    # ── HNC FEEDBACK LADDER (UP) ─────────────────────
                    # Feed temporal patterns from TKB as harmonic readings
                    # into the Lambda field. Hot topics become subsystem
                    # readings whose value reflects their burst rate.
                    if self.temporal_knowledge is not None:
                        try:
                            hot = self.temporal_knowledge.hottest_topics(n=5, window_s=60.0)
                            if hot:
                                # Normalise rates against the hottest topic
                                max_count = max(c for _, c in hot)
                                for topic, count in hot:
                                    norm = count / max_count if max_count > 0 else 0.5
                                    readings.append(SubsystemReading(
                                        name=f"tkb_{topic[:20]}",
                                        value=max(0.4, norm),
                                        confidence=0.85,
                                        state="active",
                                    ))
                            bursts = self.temporal_knowledge.bursting_topics(window_s=60.0)
                            if bursts:
                                # Bursting topics inject high-confidence high-value readings
                                # (this raises Lambda coherence when something is happening)
                                for topic, recent_rate, base_rate in bursts[:3]:
                                    burst_strength = min(1.0, recent_rate / max(base_rate, 1.0))
                                    readings.append(SubsystemReading(
                                        name=f"burst_{topic[:20]}",
                                        value=min(1.0, 0.7 + burst_strength * 0.3),
                                        confidence=0.95,
                                        state="bursting",
                                    ))
                        except Exception:
                            pass

                ls = self.lambda_engine.step(readings=readings or None, vault=self.vault)
                source_state = {
                    "lambda_t": ls.lambda_t,
                    "coherence_gamma": ls.coherence_gamma,
                    "consciousness_psi": ls.consciousness_psi,
                    "consciousness_level": ls.consciousness_level,
                    "symbolic_life_score": ls.symbolic_life_score,
                }
            except Exception:
                pass
        try:
            bus.publish("ics.source.state", source_state, source="ics")
        except Exception:
            pass

        # SOUL: Being model snapshot
        soul_state: Dict[str, Any] = {
            "consciousness_level": "", "consciousness_psi": 0.0,
            "purpose": "", "objective": "", "symbolic_life_score": 0.0,
        }
        if self.being_model is not None:
            try:
                bs = self.being_model.snapshot(vault=self.vault)
                soul_state = {
                    "consciousness_level": bs.consciousness_level,
                    "consciousness_psi": bs.consciousness_psi or 0.0,
                    "purpose": bs.sacred_purpose,
                    "objective": bs.active_objective,
                    "symbolic_life_score": bs.symbolic_life_score or 0.0,
                }
            except Exception:
                pass
        try:
            bus.publish("ics.soul.state", soul_state, source="ics")
        except Exception:
            pass

        # HNC COMBUSTION: Composite coherence + auris
        hnc_state: Dict[str, Any] = {
            "auris_consensus": "NEUTRAL", "auris_confidence": 0.0,
            "auris_agreeing": 0, "auris_total": 9,
            "lighthouse_cleared": False,
            "cells_deployed": 0, "cells_success": 0,
            "composite_coherence": 0.0,
        }
        if self.auris is not None and self.vault is not None:
            try:
                vote = self.auris.vote(self.vault)
                hnc_state["auris_consensus"] = vote.consensus
                hnc_state["auris_confidence"] = vote.confidence
                hnc_state["auris_agreeing"] = vote.agreeing
                hnc_state["auris_total"] = vote.total
                hnc_state["lighthouse_cleared"] = vote.lighthouse_cleared
            except Exception:
                pass

        # Composite coherence: 0.4*lambda_gamma + 0.3*cortex_psi + 0.3*auris_confidence
        lambda_gamma = source_state.get("coherence_gamma", 0.0)
        cortex_psi = source_state.get("consciousness_psi", 0.0)
        auris_conf = hnc_state.get("auris_confidence", 0.0)
        hnc_state["composite_coherence"] = (
            0.4 * lambda_gamma + 0.3 * cortex_psi + 0.3 * auris_conf
        )

        if self.feedback_loop is not None:
            try:
                fl_status = self.feedback_loop.get_status()
                hnc_state["cells_deployed"] = fl_status.get("total_cells_deployed", 0)
                hnc_state["cells_success"] = fl_status.get("total_cells_success", 0)
            except Exception:
                pass

        try:
            bus.publish("ics.hnc.state", hnc_state, source="ics")
        except Exception:
            pass

        # ACCOUNTING: compact metadata only, never filing/submission/payment.
        if self.accounting_context is not None and (self._tick_count == 1 or self._tick_count % 60 == 0):
            try:
                self.accounting_context.publish_status(bus, topic="accounting.status")
            except Exception:
                pass

        # HNC SAAS COGNITION: keep the unhackable pursuit loop on ThoughtBus.
        if self.saas_cognition is not None and (self._tick_count == 1 or self._tick_count % 30 == 0):
            try:
                self.saas_cognition.publish_state()
            except Exception:
                pass

        # TEMPORAL GROUND: maintain multiverse hash chain continuously
        if self.temporal_ground is not None:
            try:
                self.temporal_ground.tick(
                    lambda_t=source_state.get("lambda_t", 0.0),
                    coherence_gamma=source_state.get("coherence_gamma", 0.0),
                    consciousness_psi=source_state.get("consciousness_psi", 0.0),
                    auris_consensus=hnc_state.get("auris_consensus", "NEUTRAL"),
                )
            except Exception:
                pass

        # VAULT FEED: ingest tick state so Auris/Casimir have cards to work with
        if self.vault is not None:
            try:
                self.vault.ingest("ics.tick", {
                    "lambda_t": source_state.get("lambda_t", 0.0),
                    "coherence": source_state.get("coherence_gamma", 0.0),
                    "consciousness": source_state.get("consciousness_level", ""),
                    "auris": hnc_state.get("auris_consensus", "NEUTRAL"),
                    "tick": self._tick_count,
                }, category="ics_tick")
            except Exception:
                pass

        # ── HNC FEEDBACK LADDER (DOWN) ──────────────────────────────
        # Tune the Temporal Dialer to a frequency derived from the new
        # Lambda gamma (coherence) × 528Hz love frequency. Pull a quantum
        # packet and publish it back to ThoughtBus. The packet will be
        # captured by the TKB on its next event, completing the loop.
        if self.temporal_dialer is not None and self._tick_count % 3 == 0:
            try:
                # Map gamma [0..1] to a frequency on the love-Schumann lattice:
                #   gamma=0 -> 7.83 Hz (Schumann)
                #   gamma=1 -> 528 Hz (Love)
                gamma = source_state.get("coherence_gamma", 0.5)
                target_hz = 7.83 + (528.0 - 7.83) * gamma
                resonance = self.temporal_dialer.tune_frequency(
                    frequency_hz=target_hz,
                    bandwidth=10.0,
                )
                packet = self.temporal_dialer.pull_quantum_data()
                if packet is not None:
                    try:
                        bus.publish("temporal.dialer.packet", {
                            "frequency_hz": packet.frequency,
                            "intensity": packet.intensity,
                            "coherence": packet.coherence,
                            "resonance": resonance,
                            "source_layer": packet.source_layer,
                            "lambda_gamma": gamma,
                            "tick": self._tick_count,
                        }, source="ics.dialer")
                    except Exception:
                        pass
            except Exception:
                pass

        # SOURCE LAW: The Emerald Tablet — cogitate every 5th tick
        # (not every tick — cognition needs accumulated signals)
        if self.source_law is not None and self._tick_count % 5 == 0:
            try:
                result = self.source_law.cogitate()
                if result is not None:
                    try:
                        bus.publish("ics.source_law.cognition", {
                            "action": result.action,
                            "confidence": result.confidence,
                            "coherence": result.coherence_gamma,
                            "consciousness": result.consciousness_level,
                            "symbol": result.dominant_symbol,
                            "vacuum_size": result.vacuum_size,
                            "cycle": result.cogitation_cycle,
                        }, source="ics")
                    except Exception:
                        pass
            except Exception:
                pass

        # φ¹ BRIDGE PUSH — full ICS organism state every tick.
        # Sent at tick-end so lambda/coherence/auris are fully computed.
        if self.phi_bridge is not None and self.sentient_loop is not None:
            try:
                bridge_state = dict(self.sentient_loop.get_status())
                bridge_state.update({
                    # Lambda field + consciousness level from source_state
                    "lambda_t":            source_state.get("lambda_t", 0.0),
                    "coherence_gamma":     source_state.get("coherence_gamma", 0.0),
                    "consciousness_psi":   source_state.get("consciousness_psi", 0.0),
                    "consciousness_level": source_state.get("consciousness_level", "DORMANT"),
                    "symbolic_life_score": source_state.get("symbolic_life_score", 0.0),
                    # Auris 9-node consensus + composite coherence from hnc_state
                    "auris_consensus":     hnc_state.get("auris_consensus", "NEUTRAL"),
                    "auris_confidence":    hnc_state.get("auris_confidence", 0.0),
                    "composite_coherence": hnc_state.get("composite_coherence", 0.0),
                    # Recent ThoughtBus events (last 8) for HNC-OS documentary
                    "tb_events":           self._recent_tb_events(),
                })
                self.phi_bridge.push_state(bridge_state)
            except Exception:
                pass

    def _recent_tb_events(self) -> list:
        """Last 8 ThoughtBus events serialised for the Phi Bridge snapshot."""
        if self.thought_bus is None:
            return []
        try:
            return [
                {
                    "id":      e.get("id", ""),
                    "topic":   e.get("topic", ""),
                    "payload": e.get("payload", {}),
                    "ts":      e.get("ts", 0.0),
                    "source":  e.get("source", ""),
                }
                for e in self.thought_bus.get_recent(8)
            ]
        except Exception:
            return []

    # ------------------------------------------------------------------
    # User input processing
    # ------------------------------------------------------------------
    def process_user_input(self, text: str) -> Optional[str]:
        """
        Process user input. Returns a response string or None.

        Commands: /status, /goal, /saas, /accounts, /contracts, /pause, /resume, /cancel, /coherence, /quit
        Anything else -> GoalExecutionEngine.submit_goal()
        """
        text = text.strip()
        if not text:
            return None

        # Publish to ThoughtBus
        if self.thought_bus is not None:
            try:
                self.thought_bus.publish("user.input", {"text": text}, source="user")
            except Exception:
                pass

        # Commands
        if text == "/status":
            return self._cmd_status()
        elif text == "/swarm":
            return self._cmd_swarm_status()
        elif text == "/goal":
            return self._cmd_goal_status()
        elif text == "/pause":
            if self.goal_engine:
                self.goal_engine.pause()
            return "Goal execution paused."
        elif text == "/resume":
            if self.goal_engine:
                self.goal_engine.resume()
            return "Goal execution resumed."
        elif text == "/cancel":
            if self.goal_engine:
                self.goal_engine.cancel()
            return "Goal cancelled."
        elif text == "/coherence":
            return self._cmd_coherence()
        elif text == "/decree":
            return self._cmd_decree()
        elif text.startswith("/essay"):
            return self._cmd_essay(text)
        elif text == "/ladder":
            return self._cmd_ladder()
        elif text == "/stash":
            return self._cmd_stash()
        elif text.startswith("/research"):
            return self._cmd_research(text)
        elif text == "/organize":
            return self._cmd_organize()
        elif text == "/contracts" or text.startswith("/contracts "):
            return self._cmd_contracts(text)
        elif text == "/saas" or text.startswith("/saas "):
            return self._cmd_saas(text)
        elif text == "/accounts" or text.startswith("/accounts "):
            return self._cmd_accounts(text)
        elif text == "/quit":
            return "__QUIT__"

        # Default: submit as goal
        contract_id = ""
        if self.contract_stack is not None:
            try:
                workflow = self.contract_stack.create_goal_workflow(
                    text,
                    source="ics.user_input",
                    route_surfaces=["memory", "reasoning", "contracts", "thought_bus"],
                )
                contract_id = ((workflow.get("goal") or {}).get("contract_id") or "")
            except Exception:
                contract_id = ""
        if self.goal_engine is not None:
            try:
                plan = self.goal_engine.submit_goal(text)
                completed = sum(1 for s in plan.steps if s.status == "completed")
                suffix = f" Contract: {contract_id}." if contract_id else ""
                return (f"Goal '{plan.objective[:50]}' {plan.status}. "
                        f"{completed}/{len(plan.steps)} steps completed.{suffix}")
            except Exception as exc:
                return f"Goal execution error: {exc}"

        if contract_id:
            return f"Goal engine not available, but contract workflow was queued: {contract_id}."
        return "Goal engine not available. No subsystems could process this input."

    def _cmd_status(self) -> str:
        lines = ["=== ICS STATUS ==="]
        for name, st in self._boot_status.items():
            marker = "OK" if st == "alive" else "FAIL"
            lines.append(f"  [{marker:>4}] {name}")
        if self.contract_stack is not None:
            try:
                cst = self.contract_stack.status()
                lines.append(
                    "  Contracts: "
                    f"{cst.get('contract_count', 0)} contracts, "
                    f"queued={cst.get('queue_count', 0)}"
                )
            except Exception:
                lines.append("  Contracts: status unavailable")
        if self.accounting_context is not None:
            try:
                ast = self.accounting_context.status()
                lines.append(
                    "  Accounting: "
                    f"{ast.get('accounts_build_status', 'unknown')} "
                    f"overdue={ast.get('overdue_count', 0)} "
                    f"manual_filing={ast.get('manual_filing_required', True)}"
                )
            except Exception:
                lines.append("  Accounting: status unavailable")
        if self.saas_cognition is not None:
            try:
                sst = self.saas_cognition.status()
                summary = sst.get("summary") or {}
                lines.append(
                    "  SaaS cognition: "
                    f"{sst.get('status', 'unknown')} "
                    f"benchmarks={summary.get('unhackable_benchmark_count', 0)} "
                    f"attack_cases={summary.get('attack_case_count', 0)} "
                    f"findings={summary.get('actionable_finding_count', 0)} "
                    f"queued={summary.get('queued_decision_count', 0)}"
                )
            except Exception:
                lines.append("  SaaS cognition: status unavailable")
        lines.append(f"  Tick count: {self._tick_count}")
        return "\n".join(lines)

    def _cmd_contracts(self, text: str) -> str:
        if self.contract_stack is None:
            return "Organism contract stack not available."

        parts = text.split(maxsplit=2)
        action = parts[1].lower() if len(parts) > 1 else "status"
        if action in {"", "status"}:
            st = self.contract_stack.publish_status()
            lines = ["=== ORGANISM CONTRACT STACK ==="]
            lines.append(f"  Schema: {st.get('contract_schema_version')}")
            lines.append(f"  Contracts: {st.get('contract_count', 0)}")
            lines.append(f"  Queued work orders: {st.get('queue_count', 0)}")
            lines.append(f"  Types: {st.get('type_counts', {})}")
            lines.append(f"  Statuses: {st.get('status_counts', {})}")
            lines.append("  Topics:")
            for key, topic in sorted((st.get("topics") or {}).items()):
                lines.append(f"    - {key}: {topic}")
            return "\n".join(lines)

        if action == "goal":
            objective = parts[2].strip() if len(parts) > 2 else ""
            if not objective:
                return "Usage: /contracts goal <objective>"
            workflow = self.contract_stack.create_goal_workflow(
                objective,
                source="ics.contract_command",
                route_surfaces=["memory", "reasoning", "contracts", "thought_bus"],
            )
            goal_id = (workflow.get("goal") or {}).get("contract_id")
            work_orders = workflow.get("work_orders") or []
            return (
                "Contract workflow queued. "
                f"Goal={goal_id}; work_orders={len(work_orders)}."
            )

        if action == "next":
            item = self.contract_stack.claim_next(worker="ics.contract_command")
            if item is None:
                return "No queued organism work orders."
            return f"Claimed {item.contract_id}: {item.title}"

        if action == "complete":
            rest = parts[2].strip() if len(parts) > 2 else ""
            if not rest:
                return "Usage: /contracts complete <work_order_id> [note]"
            bits = rest.split(maxsplit=1)
            contract_id = bits[0]
            note = bits[1] if len(bits) > 1 else "completed from ICS command"
            done = self.contract_stack.complete_work_order(
                contract_id,
                result={"note": note},
                ok=True,
                worker="ics.contract_command",
            )
            if done is None:
                return f"Work order not found: {contract_id}"
            return f"Completed {done.contract_id}: {done.title}"

        return "Usage: /contracts [status|goal <objective>|next|complete <work_order_id> [note]]"

    def _cmd_saas(self, text: str) -> str:
        if self.saas_cognition is None:
            return "HNC SaaS cognitive bridge not available."

        parts = text.split()
        action = parts[1].lower() if len(parts) > 1 else "status"
        if action in {"", "status"}:
            try:
                st = self.saas_cognition.status(force=True)
            except Exception as exc:
                return f"SaaS cognition status error: {exc}"
            summary = st.get("summary") or {}
            lines = ["=== HNC SAAS COGNITION ==="]
            lines.append(f"  Status: {st.get('status', 'unknown')}")
            lines.append(f"  Blueprint: {summary.get('blueprint_status', 'unknown')}")
            lines.append(f"  Attack lab: {summary.get('attack_lab_status', 'unknown')}")
            lines.append(f"  HNC surfaces: {summary.get('hnc_surface_count', 0)}")
            lines.append(f"  Unhackable benchmarks: {summary.get('unhackable_benchmark_count', 0)}")
            lines.append(f"  Attack cases: {summary.get('attack_case_count', 0)}")
            lines.append(f"  Actionable findings: {summary.get('actionable_finding_count', 0)}")
            lines.append(f"  Queued decisions: {summary.get('queued_decision_count', 0)}")
            lines.append("  Questions:")
            for question in (st.get("questions") or [])[:6]:
                lines.append(f"    - {question.get('risk')}: {question.get('question')}")
            lines.append("  Safety: authorized local/staging self-attack only; no external attacks, live trading, filing, payments, or secrets.")
            return "\n".join(lines)

        if action in {"think", "refresh"}:
            try:
                st = self.saas_cognition.load_context(force=True)
                self.saas_cognition.ingest_to_vault(self.vault, force=True)
                self.saas_cognition.publish_state()
                return (
                    "SaaS cognitive bridge refreshed. "
                    f"status={st.status}; questions={len(st.questions)}; decisions={len(st.decisions)}; "
                    f"queued={st.summary.get('queued_decision_count', 0)}"
                )
            except Exception as exc:
                return f"SaaS cognition refresh error: {exc}"

        if action in {"attack", "lab"}:
            try:
                from aureon.autonomous.hnc_authorized_attack_lab import build_authorized_attack_lab_report, write_report

                report = build_authorized_attack_lab_report(
                    targets=["http://localhost"],
                    execute_simulations=True,
                    queue_fixes=True,
                )
                write_report(report)
                self.saas_cognition.load_context(force=True)
                self.saas_cognition.publish_state()
                summary = report.summary
                return (
                    "Authorized SaaS self-attack lab completed. "
                    f"status={report.status}; cases={summary.get('attack_case_count', 0)}; "
                    f"findings={summary.get('actionable_finding_count', 0)}; "
                    f"fixes_queued={summary.get('fix_contracts_queued')}"
                )
            except Exception as exc:
                return f"SaaS attack lab error: {exc}"

        if action in {"blueprint", "architect"}:
            try:
                from aureon.autonomous.hnc_saas_security_architect import build_hnc_saas_security_blueprint, write_report

                blueprint = build_hnc_saas_security_blueprint(queue_contracts=True)
                write_report(blueprint)
                self.saas_cognition.load_context(force=True)
                self.saas_cognition.publish_state()
                summary = blueprint.summary
                return (
                    "SaaS security blueprint refreshed. "
                    f"status={blueprint.status}; controls={summary.get('control_count', 0)}; "
                    f"benchmarks={summary.get('unhackable_benchmark_count', 0)}; "
                    f"contracts={summary.get('contract_queued')}"
                )
            except Exception as exc:
                return f"SaaS blueprint error: {exc}"

        return "Usage: /saas [status|think|attack|blueprint]"

    def _cmd_accounts(self, text: str) -> str:
        if self.accounting_context is None:
            return "Accounting context bridge not available."

        parts = text.split()
        action = parts[1].lower() if len(parts) > 1 else "status"
        if action in {"", "status"}:
            try:
                st = self.accounting_context.status(force=True)
            except Exception as exc:
                return f"Accounting status error: {exc}"
            lines = ["=== ACCOUNTING STATUS ==="]
            lines.append(f"  Company: {st.get('company_number')} {st.get('company_name')}")
            lines.append(f"  Status:  {st.get('company_status') or 'unknown'}")
            lines.append(f"  Period:  {st.get('period_start')} to {st.get('period_end')}")
            lines.append(f"  Build:   {st.get('accounts_build_status')} at {st.get('generated_at') or 'unknown'}")
            lines.append(f"  Overdue: {st.get('overdue_count', 0)}")
            lines.append(f"  Bank evidence complete: {st.get('bank_evidence_complete')}")
            lines.append(f"  Manual filing required: {st.get('manual_filing_required')}")
            combined = st.get("combined_bank_data") or {}
            if combined:
                transaction_sources = combined.get("transaction_source_count", combined.get("csv_source_count", 0))
                lines.append(
                    "  Bank/account data: "
                    f"{transaction_sources} transaction sources "
                    f"({combined.get('csv_source_count', 0)} CSV, {combined.get('pdf_source_count', 0)} parsed PDF), "
                    f"{combined.get('unique_rows_in_period', 0)} unique period rows, "
                    f"{combined.get('duplicate_rows_removed', 0)} duplicate overlaps removed"
                )
                source_summary = combined.get("source_provider_summary") or {}
                if source_summary:
                    lines.append(
                        "  Source providers: "
                        + ", ".join(f"{name}={info.get('rows', 0)}" for name, info in sorted(source_summary.items()))
                    )
                flow_summary = combined.get("flow_provider_summary") or {}
                if flow_summary:
                    lines.append(
                        "  Flow providers: "
                        + ", ".join(f"{name}={info.get('rows', 0)}" for name, info in sorted(flow_summary.items()))
                    )
            registry = st.get("accounting_system_registry") or {}
            if registry and not registry.get("error"):
                lines.append(
                    "  Accounting tools: "
                    f"{registry.get('module_count', 0)} modules/tools, "
                    f"{registry.get('artifact_count', 0)} artifacts"
                )
            accounting_control = st.get("aureon_accounting_control") or {}
            if accounting_control:
                journal = accounting_control.get("journal") or {}
                projection = accounting_control.get("quickbooks_projection") or {}
                lines.append(
                    "  Aureon journal: "
                    f"integrity={journal.get('integrity_verified', False)} "
                    f"entries={journal.get('entry_count', 0)} "
                    f"approved={journal.get('approved_entry_count', 0)} "
                    f"QBO_queued={projection.get('queued_count', 0)} "
                    f"readback={projection.get('readback_verified_count', 0)}"
                )
            reconciliation = st.get("accounting_reconciliation") or {}
            if reconciliation:
                reconciliation_summary = reconciliation.get("summary") or {}
                lines.append(
                    "  Reconciliation: "
                    f"workstreams={reconciliation_summary.get('workstream_count', 0)} "
                    f"critical={reconciliation_summary.get('critical_workstream_count', 0)} "
                    f"postings_authorised={reconciliation_summary.get('posting_authorised_count', 0)} "
                    f"external_actions_authorised={reconciliation_summary.get('external_compliance_action_authorised_count', 0)}"
                )
            quickbooks = st.get("quickbooks") or {}
            if quickbooks:
                qbo_api = quickbooks.get("api") or {}
                qbo_bank = quickbooks.get("bank_feed") or {}
                lines.append(
                    "  QuickBooks: "
                    "authority=Aureon_OS "
                    f"{quickbooks.get('connection_state', 'unknown')} "
                    f"api_readback={qbo_api.get('company_info_readback', 'not_verified')} "
                    f"bank_feed={qbo_bank.get('connected', False)} "
                    f"pending={qbo_bank.get('pending_transaction_count', 0)} "
                    f"ownership={qbo_bank.get('ownership_status', 'unknown')} "
                    f"aureon_posted={qbo_bank.get('aureon_posted_transaction_count', 0)}"
                )
            readiness = st.get("accounting_readiness") or {}
            if readiness:
                lines.append(
                    "  Readiness: "
                    f"{'ready' if readiness.get('ready') else 'blocked'} for "
                    f"{readiness.get('ready_for', 'final-ready manual upload pack')}; "
                    f"required_failures={len(readiness.get('required_failures') or [])}"
                )
            statutory = st.get("statutory_filing_pack") or {}
            if statutory:
                lines.append(
                    "  Companies House/HMRC final-ready pack: "
                    f"{len(statutory.get('outputs') or {})} outputs; "
                    "official filing remains manual"
                )
            raw_manifest = st.get("raw_data_manifest") or {}
            raw_summary = raw_manifest.get("summary") or {}
            if raw_summary:
                lines.append(
                    "  Raw data intake: "
                    f"{raw_summary.get('file_count', 0)} files, "
                    f"{raw_summary.get('transaction_source_count', 0)} transaction sources, "
                    f"{raw_summary.get('evidence_only_count', 0)} evidence-only"
                )
            workflow = st.get("autonomous_workflow") or {}
            if workflow:
                cognitive = workflow.get("cognitive_review") or st.get("cognitive_review") or {}
                vault_memory = workflow.get("vault_memory") or st.get("vault_memory") or {}
                handoff_pack = st.get("human_filing_handoff_pack") or workflow.get("human_filing_handoff_pack") or {}
                handoff_readiness = handoff_pack.get("readiness") or {}
                uk_brain = (
                    st.get("uk_accounting_requirements_brain")
                    or handoff_pack.get("uk_accounting_requirements_brain")
                    or workflow.get("uk_accounting_requirements_brain")
                    or {}
                )
                uk_summary = uk_brain.get("summary") or {}
                uk_figures = uk_brain.get("figures") or {}
                evidence_authoring = (
                    st.get("accounting_evidence_authoring")
                    or handoff_pack.get("accounting_evidence_authoring")
                    or workflow.get("accounting_evidence_authoring")
                    or {}
                )
                evidence_summary = evidence_authoring.get("summary") or {}
                llm_authoring = evidence_authoring.get("llm_document_authoring") or evidence_summary.get("llm_document_authoring") or {}
                lines.append(
                    "  Autonomous accounts workflow: "
                    f"{workflow.get('status', 'unknown')} "
                    f"agent_tasks={len(workflow.get('agent_tasks') or [])}"
                )
                lines.append(
                    "  Evidence authoring: "
                    f"{evidence_authoring.get('status', 'unknown')} "
                    f"requests={evidence_summary.get('draft_count', 0)} "
                    f"documents={evidence_summary.get('generated_document_count', 0)} "
                    f"petty_cash={evidence_summary.get('petty_cash_withdrawal_count', 0)} "
                    f"llm_status={llm_authoring.get('status', 'unknown')} "
                    f"llm_docs={llm_authoring.get('completed_count', 0)} "
                    "internal_support_documents_only"
                )
                lines.append(
                    "  UK accounting requirements brain: "
                    f"{uk_brain.get('status', 'unknown')} "
                    f"requirements={uk_summary.get('requirement_count', 0)} "
                    f"questions={uk_summary.get('question_count', 0)} "
                    f"unresolved={uk_summary.get('unresolved_question_count', 0)} "
                    f"vat_over_threshold={uk_figures.get('turnover_over_vat_threshold', 'unknown')}"
                )
                lines.append(
                    "  Human filing handoff: "
                    f"{handoff_pack.get('status', 'unknown')} "
                    f"ready={handoff_readiness.get('ready_for_manual_upload', handoff_readiness.get('ready_for_manual_review', 'unknown'))}"
                )
                lines.append(
                    "  Accounting mind: "
                    f"vault_memory={vault_memory.get('status', 'unknown')} "
                    f"self_questioning={cognitive.get('status', 'unknown')} "
                    f"source={cognitive.get('answer_source', 'n/a')}"
                )
            end_user = st.get("end_user_accounting_automation") or {}
            if end_user:
                coverage = end_user.get("requirement_coverage") or []
                generated = sum(
                    1
                    for item in coverage
                    if str(item.get("status", "")).startswith("generated")
                    or str(item.get("status", "")).startswith("final_ready")
                )
                outputs = end_user.get("outputs") or {}
                lines.append(
                    "  End-user automation: "
                    f"{end_user.get('status', 'unknown')} "
                    f"coverage={generated}/{len(coverage)} "
                    f"start_here={outputs.get('end_user_start_here', 'not generated')}"
                )
            swarm_scan = st.get("swarm_raw_data_wave_scan") or {}
            if swarm_scan:
                benchmark = swarm_scan.get("benchmark") or {}
                consensus = ((swarm_scan.get("waves") or {}).get("phi_swarm_consensus") or {})
                lines.append(
                    "  Swarm raw-data wave scan: "
                    f"{swarm_scan.get('status', 'unknown')} "
                    f"files={benchmark.get('files_scanned', 0)} "
                    f"benchmark={benchmark.get('total_duration_seconds', 0)}s "
                    f"consensus={consensus.get('status', 'unknown')} score={consensus.get('score', 'n/a')}"
                )
            confirmation = st.get("end_user_confirmation") or {}
            if confirmation:
                payload = confirmation.get("confirmation") or confirmation
                lines.append(
                    "  End-user confirmation feed: "
                    f"{confirmation.get('status', payload.get('status', 'unknown'))} "
                    f"confirmed={len(payload.get('what_aureon_confirmed') or [])} "
                    f"attention={len(payload.get('attention_items') or [])}"
                )
            missing = st.get("missing_outputs") or []
            lines.append(f"  Missing outputs: {', '.join(missing) if missing else 'none'}")
            pack = ((st.get("outputs") or {}).get("accounts_pack_pdf") or {}).get("path")
            if pack:
                lines.append(f"  Accounts pack: {pack}")
            return "\n".join(lines)

        if action in {"reconciliation", "workstreams"}:
            try:
                st = self.accounting_context.status(force=True)
            except Exception as exc:
                return f"Accounting reconciliation status error: {exc}"
            reconciliation = st.get("accounting_reconciliation") or {}
            if not reconciliation:
                return "Aureon accounting reconciliation has no generated status yet."
            summary = reconciliation.get("summary") or {}
            lines = ["=== AUREON ACCOUNTING RECONCILIATION ==="]
            lines.append("  Authority: derived Aureon work queue; not a journal, filing instruction, or approval")
            lines.append(
                "  Controls: "
                f"workstreams={summary.get('workstream_count', 0)} "
                f"critical={summary.get('critical_workstream_count', 0)} "
                f"postings_authorised={summary.get('posting_authorised_count', 0)} "
                f"QBO_projections_authorised={summary.get('quickbooks_projection_authorised_count', 0)} "
                f"external_actions_authorised={summary.get('external_compliance_action_authorised_count', 0)}"
            )
            for item in reconciliation.get("workstreams") or []:
                if not isinstance(item, dict):
                    continue
                lines.append(
                    f"  [{str(item.get('priority', 'unknown')).upper()}] "
                    f"{item.get('id', 'unknown')}: {item.get('state', 'unknown')}"
                )
                if item.get("next_action"):
                    lines.append(f"    Next evidence/action: {item['next_action']}")
            return "\n".join(lines)

        if action in {"quickbooks", "qbo"}:
            try:
                st = self.accounting_context.status(force=True)
            except Exception as exc:
                return f"QuickBooks control-plane status error: {exc}"
            quickbooks = st.get("quickbooks") or {}
            if not quickbooks:
                return "QuickBooks control plane has no live status receipt yet."
            api = quickbooks.get("api") or {}
            bank = quickbooks.get("bank_feed") or {}
            chart = quickbooks.get("chart_of_accounts") or {}
            controls = quickbooks.get("controls") or {}
            reports = quickbooks.get("reports") or {}
            tax_features = quickbooks.get("tax_features") or {}
            accounting_control = st.get("aureon_accounting_control") or {}
            canonical_journal = accounting_control.get("journal") or {}
            projection_queue = accounting_control.get("quickbooks_projection") or {}
            lines = ["=== QUICKBOOKS CONTROL PLANE ==="]
            lines.append("  Authority: Aureon OS is canonical; QuickBooks is projection/read-back only")
            lines.append(
                "  Aureon journal: "
                f"integrity={canonical_journal.get('integrity_verified', False)} "
                f"entries={canonical_journal.get('entry_count', 0)} "
                f"approved={canonical_journal.get('approved_entry_count', 0)}"
            )
            lines.append(
                "  Projection queue: "
                f"queued={projection_queue.get('queued_count', 0)} "
                f"readback={projection_queue.get('readback_verified_count', 0)} "
                f"outstanding={projection_queue.get('outstanding_readback_count', 0)} "
                f"observations={projection_queue.get('observation_task_count', 0)}"
            )
            lines.append(f"  State: {quickbooks.get('connection_state', 'unknown')}")
            lines.append(f"  CompanyInfo API read-back: {api.get('company_info_readback', 'not_verified')}")
            lines.append(f"  OAuth: {api.get('oauth', 'not_verified')}")
            lines.append(
                "  Bank feed: "
                f"connected={bank.get('connected', False)} "
                f"provider={bank.get('provider', 'unknown')} "
                f"pending={bank.get('pending_transaction_count', 0)} "
                f"ownership={bank.get('ownership_status', 'unknown')}"
            )
            lines.append(
                "  Posting: "
                f"aureon_posted={bank.get('aureon_posted_transaction_count', 0)} "
                f"bulk_allowed={bank.get('bulk_posting_allowed', False)}"
            )
            lines.append(
                "  Chart: "
                f"accounts={chart.get('account_count', 0)} "
                f"staged_changes_applied={chart.get('staged_changes_applied', False)}"
            )
            lines.append(
                "  Reports: "
                f"pnl_has_data={reports.get('profit_and_loss_current_period_has_data', False)} "
                f"balance_sheet_nonzero_accounts={reports.get('balance_sheet_nonzero_account_count', 0)} "
                f"reconciled_to_aureon={reports.get('reconciled_to_aureon_canonical_ledger', False)}"
            )
            lines.append(
                "  Tax features: "
                f"CIS={tax_features.get('cis_enabled', False)} "
                f"VAT={tax_features.get('vat_enabled', False)} "
                f"payroll={tax_features.get('payroll_enabled', False)}"
            )
            lines.append(f"  QuickBooks mutations: {controls.get('quickbooks_mutations', 'disabled')}")
            lines.append("  Safety: no bulk posting, filing, payment, bank, VAT, PAYE, or CIS mutation is automatic.")
            return "\n".join(lines)

        if action in {"tools", "registry"}:
            try:
                st = self.accounting_context.status(force=True)
            except Exception as exc:
                return f"Accounting tools error: {exc}"
            registry = st.get("accounting_system_registry") or {}
            if not registry or registry.get("error"):
                return f"Accounting tools registry unavailable: {registry.get('error', 'unknown')}"
            lines = ["=== ACCOUNTING TOOL REGISTRY ==="]
            lines.append(f"  Modules/tools: {registry.get('module_count', 0)}")
            lines.append(f"  Artifacts:     {registry.get('artifact_count', 0)}")
            lines.append(f"  Runnable:      {registry.get('runnable_tool_count', 0)}")
            lines.append("  Domains:")
            for domain, count in sorted((registry.get("domain_counts") or {}).items()):
                lines.append(f"    - {domain}: {count}")
            lines.append("  Safety: Companies House/HMRC filing and tax/payment actions remain manual only.")
            return "\n".join(lines)

        if action == "ingest":
            try:
                ingested = self.accounting_context.ingest_to_vault(self.vault, force=True)
                status = self.accounting_context.publish_status(self.thought_bus, topic="accounting.status")
                return (
                    "Accounting context refreshed and ingested into vault. "
                    f"cards={ingested}, overdue={status.get('overdue_count', 0)}"
                )
            except Exception as exc:
                return f"Accounting ingest error: {exc}"

        if action in {"readiness", "audit"}:
            try:
                if hasattr(self.accounting_context, "validate_accounting_readiness"):
                    readiness = self.accounting_context.validate_accounting_readiness(force=True)
                else:
                    readiness = (self.accounting_context.status(force=True).get("accounting_readiness") or {})
                if self.thought_bus is not None:
                    try:
                        self.thought_bus.publish("accounting.readiness", readiness, source="ics.accounting")
                    except Exception:
                        pass
                lines = ["=== ACCOUNTING READINESS ==="]
                lines.append(f"  Ready: {readiness.get('ready')}")
                lines.append(f"  Ready for: {readiness.get('ready_for', 'final-ready manual upload pack')}")
                lines.append(f"  Bank sources: {readiness.get('bank_sources', 0)}")
                lines.append(f"  Unique bank rows: {readiness.get('unique_bank_rows', 0)}")
                lines.append(f"  Statutory outputs: {readiness.get('statutory_outputs', 0)}")
                failures = readiness.get("required_failures") or []
                lines.append(f"  Required failures: {len(failures)}")
                for item in failures[:8]:
                    lines.append(f"    - {item.get('name')}: {item.get('detail')}")
                if not failures:
                    lines.append("  Required checklist: complete")
                lines.append("  Safety: filing, HMRC submission, tax and payments remain manual.")
                return "\n".join(lines)
            except Exception as exc:
                return f"Accounting readiness error: {exc}"

        if action in {"requirements", "brain", "questions"}:
            try:
                st = self.accounting_context.status(force=True)
            except Exception as exc:
                return f"Accounting requirements brain error: {exc}"
            handoff_pack = st.get("human_filing_handoff_pack") or {}
            workflow = st.get("autonomous_workflow") or {}
            uk_brain = (
                st.get("uk_accounting_requirements_brain")
                or handoff_pack.get("uk_accounting_requirements_brain")
                or workflow.get("uk_accounting_requirements_brain")
                or {}
            )
            if not uk_brain:
                return "Accounting UK requirements brain has not been generated yet. Run /accounts autonomous or /accounts build first."
            summary = uk_brain.get("summary") or {}
            figures = uk_brain.get("figures") or {}
            lines = ["=== UK ACCOUNTING REQUIREMENTS BRAIN ==="]
            lines.append(f"  Status: {uk_brain.get('status', 'unknown')}")
            lines.append(f"  Requirements: {summary.get('requirement_count', 0)}")
            lines.append(f"  Accountant self-questions: {summary.get('question_count', 0)}")
            lines.append(f"  Unresolved questions: {summary.get('unresolved_question_count', 0)}")
            lines.append(f"  VAT turnover over threshold: {figures.get('turnover_over_vat_threshold')}")
            lines.append(f"  VAT threshold: {figures.get('vat_registration_threshold', 'unknown')}")
            lines.append("  Questions:")
            for question in (uk_brain.get("accountant_self_questions") or [])[:10]:
                lines.append(f"    - {question.get('status')}: {question.get('question')}")
            lines.append("  Safety: inspect/reconcile/generate final-ready local packs only; filing, VAT/HMRC submission and payments remain manual.")
            return "\n".join(lines)

        if action in {"evidence", "documents", "receipts", "invoices"}:
            try:
                st = self.accounting_context.status(force=True)
            except Exception as exc:
                return f"Accounting evidence authoring error: {exc}"
            handoff_pack = st.get("human_filing_handoff_pack") or {}
            workflow = st.get("autonomous_workflow") or {}
            evidence_authoring = (
                st.get("accounting_evidence_authoring")
                or handoff_pack.get("accounting_evidence_authoring")
                or workflow.get("accounting_evidence_authoring")
                or {}
            )
            if not evidence_authoring:
                return "Accounting evidence authoring pack has not been generated yet. Run /accounts autonomous first."
            summary = evidence_authoring.get("summary") or {}
            llm_authoring = evidence_authoring.get("llm_document_authoring") or summary.get("llm_document_authoring") or {}
            outputs = evidence_authoring.get("outputs") or {}
            lines = ["=== ACCOUNTING EVIDENCE AUTHORING ==="]
            lines.append(f"  Status: {evidence_authoring.get('status', 'unknown')}")
            lines.append(f"  Evidence requests: {summary.get('draft_count', 0)}")
            lines.append(f"  Generated internal document templates: {summary.get('generated_document_count', 0)}")
            lines.append(
                "  LLM document authoring: "
                f"{llm_authoring.get('status', 'unknown')} "
                f"generated={llm_authoring.get('completed_count', 0)} "
                f"model={llm_authoring.get('model') or 'not selected'}"
            )
            lines.append(f"  Petty-cash withdrawals: {summary.get('petty_cash_withdrawal_count', 0)}")
            lines.append(f"  Related-party/director queries: {summary.get('related_party_query_count', 0)}")
            lines.append(f"  Expense receipt requests: {summary.get('expense_receipt_request_count', 0)}")
            lines.append(f"  Income source queries: {summary.get('income_source_query_count', 0)}")
            lines.append(f"  Manifest: {outputs.get('accounting_evidence_authoring_manifest', 'not found')}")
            lines.append(f"  Requests CSV: {outputs.get('accounting_evidence_requests_csv', 'not found')}")
            lines.append("  Safety: generated documents are internal support records only, not real receipts/invoices or filing evidence.")
            return "\n".join(lines)

        if action in {"filing", "statutory"}:
            subaction = parts[2].lower() if len(parts) > 2 else "status"
            if subaction in {"build", "generate"}:
                if not hasattr(self.accounting_context, "run_statutory_filing_pack"):
                    return "Accounting statutory generator not available."
                try:
                    result = self.accounting_context.run_statutory_filing_pack()
                    if self.thought_bus is not None:
                        topic = (
                            "accounting.statutory.generated"
                            if result.get("status") == "completed"
                            else "accounting.statutory.blocked"
                        )
                        try:
                            self.thought_bus.publish(topic, result, source="ics.accounting")
                        except Exception:
                            pass
                    self.accounting_context.ingest_to_vault(self.vault, force=True)
                    readiness = result.get("readiness") or ((result.get("summary") or {}).get("accounting_readiness") or {})
                    return (
                        "Accounting statutory filing-support build "
                        f"{result.get('status')} (exit={result.get('exit_code', 'n/a')}); final-ready manual pack. "
                        f"ready={readiness.get('ready', 'unknown')}; "
                        "Companies House/HMRC filing remains manual."
                    )
                except Exception as exc:
                    if self.thought_bus is not None:
                        try:
                            self.thought_bus.publish(
                                "accounting.statutory.blocked",
                                {"error": str(exc)},
                                source="ics.accounting",
                            )
                        except Exception:
                            pass
                    return f"Accounting statutory build blocked: {exc}"

            try:
                st = self.accounting_context.status(force=True)
            except Exception as exc:
                return f"Accounting filing status error: {exc}"
            statutory = st.get("statutory_filing_pack") or {}
            outputs = statutory.get("outputs") or {}
            figures = statutory.get("figures") or {}
            requirement_summary = (statutory.get("government_requirements_matrix") or {}).get("summary") or {}
            uk_brain = (
                st.get("uk_accounting_requirements_brain")
                or (st.get("human_filing_handoff_pack") or {}).get("uk_accounting_requirements_brain")
                or {}
            )
            uk_summary = uk_brain.get("summary") or {}
            lines = ["=== ACCOUNTING STATUTORY/HMRC PACK ==="]
            lines.append(f"  Company: {st.get('company_number')} {st.get('company_name')}")
            lines.append(f"  Period:  {st.get('period_start')} to {st.get('period_end')}")
            lines.append(f"  Generated: {statutory.get('generated_at') or 'not generated'}")
            if figures:
                lines.append(
                    "  Figures: "
                    f"turnover={figures.get('turnover', 'n/a')}, "
                    f"expenses={figures.get('expenses', 'n/a')}, "
                    f"profit_before_tax={figures.get('profit_before_tax', 'n/a')}, "
                    f"corporation_tax={figures.get('corporation_tax', 'n/a')}"
                )
            lines.append(f"  Outputs: {len(outputs)}")
            if requirement_summary:
                lines.append(
                    "  Government requirements: "
                    f"{requirement_summary.get('requirement_count', 0)} tracked, "
                    f"{requirement_summary.get('generated_or_readiness_count', 0)} generated/readiness, "
                "official submission manual"
                )
            if uk_summary:
                lines.append(
                    "  UK requirements brain: "
                    f"{uk_summary.get('requirement_count', 0)} tracked, "
                    f"{uk_summary.get('question_count', 0)} self-questions, "
                    f"{uk_summary.get('unresolved_question_count', 0)} unresolved"
                )
            for key in (
                "companies_house_accounts_pdf",
                "directors_report_pdf",
                "ct600_manual_entry_json",
                "hmrc_ct600_draft_json",
                "ct600_box_map_markdown",
                "hmrc_tax_computation_pdf",
                "ixbrl_readiness_note",
                "government_requirements_matrix_markdown",
                "filing_checklist",
            ):
                item = outputs.get(key) or ((st.get("outputs") or {}).get(key) or {})
                lines.append(f"    - {key}: {item.get('path') or 'not found'}")
            lines.append("  Safety: final-ready manual filing pack only; no Companies House/HMRC filing or payment is automatic.")
            return "\n".join(lines)

        if action in {"raw", "intake"}:
            try:
                st = self.accounting_context.status(force=True)
            except Exception as exc:
                return f"Accounting raw-data status error: {exc}"
            raw_manifest = st.get("raw_data_manifest") or {}
            summary = raw_manifest.get("summary") or {}
            lines = ["=== ACCOUNTING RAW DATA INTAKE ==="]
            lines.append(f"  Company: {st.get('company_number')} {st.get('company_name')}")
            lines.append(f"  Period:  {st.get('period_start')} to {st.get('period_end')}")
            lines.append(f"  Files:   {summary.get('file_count', 0)}")
            lines.append(f"  Transaction sources: {summary.get('transaction_source_count', 0)}")
            lines.append(f"  Evidence-only files: {summary.get('evidence_only_count', 0)}")
            providers = summary.get("provider_counts") or {}
            if providers:
                lines.append("  Providers: " + ", ".join(f"{key}={value}" for key, value in sorted(providers.items())))
            paths = st.get("source_files") or {}
            if paths.get("raw_data_manifest"):
                lines.append(f"  Manifest: {paths.get('raw_data_manifest')}")
            swarm_scan = st.get("swarm_raw_data_wave_scan") or {}
            if swarm_scan:
                benchmark = swarm_scan.get("benchmark") or {}
                consensus = ((swarm_scan.get("waves") or {}).get("phi_swarm_consensus") or {})
                lines.append(
                    "  Swarm wave scan: "
                    f"files={benchmark.get('files_scanned', 0)} "
                    f"files_per_second={benchmark.get('files_per_second', 0)} "
                    f"consensus={consensus.get('status', 'unknown')}"
                )
            lines.append("  Safety: intake is local evidence inventory only; filing and payment remain manual.")
            return "\n".join(lines)

        if action in {"end-user", "end_user", "automation", "user"}:
            try:
                if not hasattr(self.accounting_context, "run_end_user_accounting_automation"):
                    return "End-user accounting automation not available."
                result = self.accounting_context.run_end_user_accounting_automation(no_fetch=True)
                if self.thought_bus is not None:
                    topic = (
                        "accounting.end_user_accounts.completed"
                        if result.get("status") == "completed"
                        else "accounting.end_user_accounts.blocked"
                    )
                    try:
                        self.thought_bus.publish(topic, result, source="ics.accounting")
                    except Exception:
                        pass
                self.accounting_context.ingest_to_vault(self.vault, force=True)
                summary = result.get("summary") or {}
                end_user = summary.get("end_user_accounting_automation") or result.get("end_user_accounting_automation") or {}
                coverage = end_user.get("requirement_coverage") or []
                generated = sum(
                    1
                    for item in coverage
                    if str(item.get("status", "")).startswith("generated")
                    or str(item.get("status", "")).startswith("final_ready")
                )
                outputs = end_user.get("outputs") or {}
                return (
                    "End-user accounting automation "
                    f"{result.get('status')} (exit={result.get('exit_code', 'n/a')}). "
                    f"coverage={generated}/{len(coverage)} generated; "
                    f"start_here={outputs.get('end_user_start_here', 'not generated')}; "
                    "official Companies House/HMRC filing and payment remain manual."
                )
            except Exception as exc:
                if self.thought_bus is not None:
                    try:
                        self.thought_bus.publish(
                            "accounting.end_user_accounts.blocked",
                            {"error": str(exc)},
                            source="ics.accounting",
                        )
                    except Exception:
                        pass
                return f"End-user accounting automation blocked: {exc}"

        if action in {"autonomous", "full"}:
            try:
                if not hasattr(self.accounting_context, "run_autonomous_full_accounts"):
                    return "Accounting autonomous workflow not available."
                result = self.accounting_context.run_autonomous_full_accounts(no_fetch=True)
                if self.thought_bus is not None:
                    topic = (
                        "accounting.autonomous.accounts.completed"
                        if result.get("status") == "completed"
                        else "accounting.autonomous.accounts.blocked"
                    )
                    try:
                        self.thought_bus.publish(topic, result, source="ics.accounting")
                    except Exception:
                        pass
                self.accounting_context.ingest_to_vault(self.vault, force=True)
                summary = result.get("summary") or {}
                readiness = result.get("readiness") or summary.get("accounting_readiness") or {}
                raw_summary = ((summary.get("raw_data_manifest") or {}).get("summary") or {})
                workflow = summary.get("autonomous_workflow") or {}
                cognitive = workflow.get("cognitive_review") or {}
                handoff_pack = summary.get("human_filing_handoff_pack") or workflow.get("human_filing_handoff_pack") or {}
                handoff_readiness = handoff_pack.get("readiness") or {}
                uk_brain = (
                    summary.get("uk_accounting_requirements_brain")
                    or handoff_pack.get("uk_accounting_requirements_brain")
                    or workflow.get("uk_accounting_requirements_brain")
                    or {}
                )
                uk_summary = uk_brain.get("summary") or {}
                evidence_authoring = (
                    summary.get("accounting_evidence_authoring")
                    or handoff_pack.get("accounting_evidence_authoring")
                    or workflow.get("accounting_evidence_authoring")
                    or {}
                )
                evidence_summary = evidence_authoring.get("summary") or {}
                return (
                    "Accounting autonomous full-accounts workflow "
                    f"{result.get('status')} (exit={result.get('exit_code', 'n/a')}). "
                    f"raw_files={raw_summary.get('file_count', 0)}; "
                    f"agent_tasks={len(workflow.get('agent_tasks') or [])}; "
                    f"evidence_requests={evidence_summary.get('draft_count', 0)}; "
                    f"uk_questions={uk_summary.get('question_count', 0)}; "
                    f"handoff_ready={handoff_readiness.get('ready_for_manual_upload', handoff_readiness.get('ready_for_manual_review', 'unknown'))}; "
                    f"self_questioning={cognitive.get('status', 'unknown')}; "
                    f"ready={readiness.get('ready', 'unknown')}; "
                    "official filing remains manual."
                )
            except Exception as exc:
                if self.thought_bus is not None:
                    try:
                        self.thought_bus.publish(
                            "accounting.autonomous.accounts.blocked",
                            {"error": str(exc)},
                            source="ics.accounting",
                        )
                    except Exception:
                        pass
                return f"Accounting autonomous workflow blocked: {exc}"

        if action == "build":
            try:
                used_end_user = False
                if hasattr(self.accounting_context, "run_end_user_accounting_automation"):
                    used_end_user = True
                    result = self.accounting_context.run_end_user_accounting_automation(no_fetch=True)
                else:
                    result = self.accounting_context.run_full_accounts(no_fetch=True)
                if self.thought_bus is not None:
                    topic = (
                        (
                            "accounting.end_user_accounts.completed"
                            if result.get("status") == "completed"
                            else "accounting.end_user_accounts.blocked"
                        )
                        if used_end_user
                        else (
                            "accounting.accounts.generated"
                            if result.get("status") == "completed"
                            else "accounting.accounts.blocked"
                        )
                    )
                    try:
                        self.thought_bus.publish(topic, result, source="ics.accounting")
                    except Exception:
                        pass
                self.accounting_context.ingest_to_vault(self.vault, force=True)
                summary = result.get("summary") or {}
                readiness = summary.get("accounting_readiness") or {}
                return (
                    "Accounting build "
                    f"{result.get('status')} (exit={result.get('exit_code', 'n/a')}); final-ready manual pack. "
                    f"manual_filing_required={((result.get('safety') or {}).get('manual_filing_required', True))}; "
                    f"overdue={summary.get('overdue_count', 'unknown')}; "
                    f"ready={readiness.get('ready', 'unknown')}"
                )
            except Exception as exc:
                if self.thought_bus is not None:
                    try:
                        self.thought_bus.publish(
                            "accounting.accounts.blocked",
                            {"error": str(exc)},
                            source="ics.accounting",
                        )
                    except Exception:
                        pass
                return f"Accounting build blocked: {exc}"

        return "Usage: /accounts [status|reconciliation|quickbooks|raw|tools|registry|ingest|readiness|evidence|requirements|filing|statutory build|end-user|autonomous|build]"

    def _cmd_goal_status(self) -> str:
        if self.goal_engine is None:
            return "Goal engine not available."
        status = self.goal_engine.get_status()
        plan = status.get("current_plan")
        if plan is None:
            return "No active goal."
        lines = [f"Goal: {plan['objective'][:60]}"]
        lines.append(f"Status: {plan['status']}")
        lines.append(f"Steps: {plan['completed_steps']}/{plan['total_steps']} completed")
        active = plan.get("active_step")
        if active:
            lines.append(f"Active: {active['title']}")
        return "\n".join(lines)

    def _cmd_swarm_status(self) -> str:
        if self.swarm is None:
            return "Swarm (OpenMultiAgent) not available."
        try:
            st = self.swarm.get_status()
            teams = st.get("teams", {})
            agents = st.get("standalone_agents", [])
            lines = ["=== SWARM STATUS ==="]
            lines.append(f"  Adapter: {st.get('adapter', 'unknown')}")
            lines.append(f"  Teams:   {len(teams)}")
            for tname, tinfo in teams.items():
                lines.append(f"    [{tname}] agents={tinfo.get('agents', 0)} tasks={tinfo.get('tasks', {})}")
            lines.append(f"  Standalone agents: {len(agents)}")
            if self.temporal_ground is not None:
                tg = self.temporal_ground
                hc = getattr(tg, '_hash_chain', None)
                cl = getattr(hc, '_chain_length', '?') if hc else '?'
                lines.append(f"  Timeline chain: length={cl}")
            return "\n".join(lines)
        except Exception as exc:
            return f"Swarm status error: {exc}"

    def _cmd_organize(self) -> str:
        """Manually trigger vault→dataset sync + self-organize."""
        lines = ["=== VAULT KNOWLEDGE BRIDGE ==="]
        if self.vault_knowledge_bridge is None:
            lines.append("  Bridge not available.")
            return "\n".join(lines)

        # Run one sync cycle immediately
        try:
            result = self.vault_knowledge_bridge.run_one_cycle()
            lines.append(f"  Cycle examined:    {result['examined']} cards")
            lines.append(f"  Cards absorbed:    {result['absorbed']}")
            lines.append(f"  Fragments added:   {result['fragments_added']}")
            lines.append(f"  Self-organised:    {result['self_organized']}")
            if result.get("self_organize_result"):
                so = result["self_organize_result"]
                lines.append(f"    tags reindexed:  {so['tags_reindexed']}")
                lines.append(f"    duplicates:      {so['duplicates_marked']}")
                lines.append(f"    links added:     {so['links_added']}")
        except Exception as exc:
            lines.append(f"  Cycle error: {exc}")

        # Show bridge status
        status = self.vault_knowledge_bridge.get_status()
        lines.append("  Bridge lifetime:")
        lines.append(f"    cycles:          {status['cycles']}")
        lines.append(f"    cards examined:  {status['cards_examined']}")
        lines.append(f"    cards absorbed:  {status['cards_absorbed']}")
        lines.append(f"    fragments added: {status['fragments_added']}")
        lines.append(f"    self-organises:  {status['self_organize_runs']}")
        return "\n".join(lines)

    def _cmd_research(self, text: str) -> str:
        """Manually trigger research. Usage: /research [query]
        With no query, runs one cycle of the self-research loop.
        With a query, fetches answers immediately from external APIs.
        """
        if self.world_data_ingester is None:
            return "World data ingester not available."

        parts = text.split(maxsplit=1)
        if len(parts) > 1:
            query = parts[1].strip()
            try:
                items = self.world_data_ingester.answer_question(query, n_per_source=2)
                if not items:
                    return f"No external results found for: {query}"
                self.world_data_ingester.ingest_to_vault(items)
                lines = [f"=== RESEARCH: {query} ==="]
                lines.append(f"  Found {len(items)} items, ingested into vault")
                for it in items[:5]:
                    lines.append(f"  [{it.source:18}] {it.title[:60]}")
                return "\n".join(lines)
            except Exception as exc:
                return f"Research error: {exc}"

        # No query — run one cycle of the loop
        if self.self_research_loop is None:
            return "Self-research loop not available."
        try:
            result = self.self_research_loop.run_one_cycle()
            return (f"Research cycle {result['cycle']}: "
                    f"{result['questions_processed']} questions, "
                    f"{result['items_pulled']} items pulled, "
                    f"{result['fragments_added']} fragments added")
        except Exception as exc:
            return f"Cycle error: {exc}"

    def _cmd_stash(self) -> str:
        """Show stash pocket + knowledge dataset status with taxonomy."""
        lines = ["=== STASH POCKETS + KNOWLEDGE DATASET ==="]
        if self.stash_pockets is not None:
            sp = self.stash_pockets.get_status()
            lines.append(f"  Pockets:    {sp['open_pockets']} open / {sp['closed_pockets']} closed")
            lines.append(f"  Lifetime:   {sp['total_opened']} opened / {sp['total_closed']} closed")
            lines.append(f"  Crystallized: {sp['fragments_crystallized']} fragments")
        else:
            lines.append("  Stash pockets not available.")
        if self.knowledge_dataset is not None:
            kd = self.knowledge_dataset.get_status()
            lines.append(f"  Dataset:    {kd['fragments']} fragments, {kd['unique_tags']} tags")
            lines.append(f"  Activity:   {kd['absorptions']} absorbs / {kd['retrievals']} retrieves")
            lines.append(f"  Persisted:  {kd['path']}")
            # Auto-taxonomy
            try:
                taxonomy = self.knowledge_dataset.get_taxonomy()
                if taxonomy:
                    lines.append("  Taxonomy (category → data_type → count):")
                    for cat, types in sorted(taxonomy.items()):
                        type_str = ", ".join(f"{dt}({n})" for dt, n in types.items())
                        lines.append(f"    {cat:12} {type_str}")
            except Exception:
                pass
        if self.knowledge_interpreter is not None:
            ki = self.knowledge_interpreter.get_status()
            lines.append(f"  Interpreter: {ki['interpretations']} runs, "
                         f"{ki['deterministic_passes']} deterministic / "
                         f"{ki['swarm_passes']} swarm")
        lines.append("  (Math angle protocol + structured interpretation — not LLM)")
        return "\n".join(lines)

    def _cmd_ladder(self) -> str:
        """Show the HNC feedback ladder — TKB events → Lambda → Dialer → bus."""
        lines = ["=== HNC FEEDBACK LADDER ==="]

        # UP: TKB feeding Lambda
        if self.temporal_knowledge:
            tkb_status = self.temporal_knowledge.get_status()
            hot = self.temporal_knowledge.hottest_topics(n=3, window_s=60.0)
            bursts = self.temporal_knowledge.bursting_topics(window_s=60.0)
            lines.append(f"  ↑ TKB:    {tkb_status['total_events']} events, "
                         f"{tkb_status['unique_topics']} topics, "
                         f"{tkb_status['uptime_s']:.0f}s uptime")
            if hot:
                lines.append(f"    hot:    {', '.join(f'{t}({c})' for t, c in hot)}")
            if bursts:
                lines.append(f"    burst:  {len(bursts)} topics bursting")

        # MIDDLE: Lambda
        if self.lambda_engine:
            try:
                ls = self.lambda_engine.step()
                lines.append(f"  Λ Lambda: gamma={ls.coherence_gamma:.3f} "
                             f"psi={ls.consciousness_psi:.3f} "
                             f"level={ls.consciousness_level}")
            except Exception:
                pass

        # DOWN: Dialer
        if self.temporal_dialer:
            ds = self.temporal_dialer.get_status()
            state = ds.get("state", {})
            if isinstance(state, dict):
                freq = state.get("frequency", 0)
                res = state.get("resonance", 0)
                mode = state.get("mode", "?")
                lines.append(f"  ↓ Dialer: freq={freq:.2f}Hz "
                             f"resonance={res:.3f} mode={mode}")
                lines.append(f"    packets: {ds.get('packets_received', 0)}")

        # Source Law (the Tablet at the apex)
        if self.source_law:
            try:
                result = getattr(self.source_law, '_last_result', None) or self.source_law.cogitate()
                if result:
                    lines.append(f"  ☉ Tablet: {result.action} "
                                 f"coh={result.coherence_gamma:.3f}")
            except Exception:
                pass

        lines.append("  (TKB → Lambda → Dialer → ThoughtBus → TKB) — closed loop")
        return "\n".join(lines)

    def _cmd_essay(self, text: str) -> str:
        """Compose a self-description essay at the requested word count.

        Usage: /essay [word_count]   (default 600)
        """
        if self.prose_composer is None:
            return "Prose composer not available."
        # Parse word count
        parts = text.split()
        target = 600
        if len(parts) >= 2:
            try:
                target = int(parts[1])
            except ValueError:
                pass
        try:
            essay = self.prose_composer.compose(
                topic="self-description",
                target_words=target,
            )
            return f"[{essay.word_count} words]\n\n{essay.text}"
        except Exception as exc:
            return f"Compose error: {exc}"

    def _cmd_decree(self) -> str:
        """The Emerald Tablet's last decree — Source Law cognition result."""
        if self.source_law is None:
            return "Source Law Engine not available."
        result = getattr(self.source_law, '_last_result', None)
        if result is None:
            # Force a cogitation
            try:
                result = self.source_law.cogitate()
            except Exception as exc:
                return f"Cogitation failed: {exc}"
        if result is None:
            return "No cognition yet. Vacuum is accumulating signals."
        lines = [
            "=== EMERALD TABLET DECREE ===",
            f"  Action:        {result.action}",
            f"  Confidence:    {result.confidence:.2f}",
            f"  Coherence:     {result.coherence_gamma:.3f}",
            f"  Consciousness: {result.consciousness_level} (psi={result.consciousness_psi:.3f})",
            f"  Vacuum size:   {result.vacuum_size} signals accumulated",
            f"  Cycle:         {result.cogitation_cycle}",
        ]
        if result.dominant_symbol:
            lines.append(f"  Symbol:        {result.dominant_symbol}")
        if result.reasoning:
            lines.append(f"  Reasoning:")
            for r in result.reasoning[:5]:
                lines.append(f"    - {r}")
        return "\n".join(lines)

    def _cmd_coherence(self) -> str:
        if self.lambda_engine is None:
            return "Lambda engine not available."
        try:
            state = self.lambda_engine.step()
            return (f"Lambda(t): {state.lambda_t:.4f}  "
                    f"Gamma: {state.coherence_gamma:.3f}  "
                    f"Psi: {state.consciousness_psi:.3f}  "
                    f"Level: {state.consciousness_level}")
        except Exception as exc:
            return f"Coherence read error: {exc}"

    # ------------------------------------------------------------------
    # Vault UI server (Flask + Phi Bridge for phone)
    # ------------------------------------------------------------------
    def _start_vault_ui(self, host: str = "127.0.0.1", port: int = 5566) -> None:
        """Start the Flask vault UI server in a background thread."""
        self._vault_ui_host = host
        self._vault_ui_port = port
        if self.vault_app is None:
            return

        def _serve():
            try:
                self.vault_app.run(
                    host=host, port=port, debug=False,
                    use_reloader=False, threaded=True,
                )
            except Exception as exc:
                logger.warning("Vault UI server error: %s", exc)

        self._vault_ui_thread = threading.Thread(
            target=_serve, name="ics-vault-ui", daemon=True,
        )
        self._vault_ui_thread.start()

    def _detect_lan_ip(self) -> str:
        """Best-effort LAN IPv4 lookup."""
        import socket
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"

    # ------------------------------------------------------------------
    # Remote tunnel (4G / internet access)
    # ------------------------------------------------------------------
    def _start_tunnel(self, port: int) -> Optional[str]:
        """
        Start a tunnel so the phone can reach the ICS over 4G / internet.
        Tries cloudflared → ngrok → pyngrok in order.
        Returns the public URL or None.
        """
        import subprocess as _sp
        import shutil

        # Try 1: cloudflared (Cloudflare Tunnel — free, no signup)
        if shutil.which("cloudflared"):
            try:
                proc = _sp.Popen(
                    ["cloudflared", "tunnel", "--url", f"http://127.0.0.1:{port}"],
                    stdout=_sp.PIPE, stderr=_sp.PIPE, text=True,
                )
                self._tunnel_proc = proc
                # cloudflared prints the URL to stderr
                import time as _time
                for _ in range(30):
                    line = proc.stderr.readline()
                    if "trycloudflare.com" in line or "cfargotunnel.com" in line:
                        import re
                        m = re.search(r'(https://[^\s]+)', line)
                        if m:
                            return m.group(1)
                    _time.sleep(0.5)
            except Exception as exc:
                logger.debug("cloudflared failed: %s", exc)

        # Try 2: ngrok CLI
        if shutil.which("ngrok"):
            try:
                proc = _sp.Popen(
                    ["ngrok", "http", str(port), "--log", "stdout"],
                    stdout=_sp.PIPE, stderr=_sp.PIPE, text=True,
                )
                self._tunnel_proc = proc
                import time as _time
                for _ in range(20):
                    line = proc.stdout.readline()
                    if "url=" in line and "ngrok" in line:
                        import re
                        m = re.search(r'url=(https://[^\s]+)', line)
                        if m:
                            return m.group(1)
                    _time.sleep(0.5)
            except Exception as exc:
                logger.debug("ngrok failed: %s", exc)

        # Try 3: pyngrok (Python package)
        try:
            from pyngrok import ngrok as _ngrok
            tunnel = _ngrok.connect(port, "http")
            return tunnel.public_url
        except Exception:
            pass

        return None

    # ------------------------------------------------------------------
    # Main run loop
    # ------------------------------------------------------------------
    def run(self, lan: bool = False, remote: bool = False, port: int = 5566) -> None:
        """
        Main entry point. Boots subsystems, starts dashboard and tick thread,
        starts the vault UI server (with Phi Bridge for phone access),
        then blocks on stdin input loop.

        Args:
            lan: If True, bind on 0.0.0.0 so phones on the same WiFi can connect.
            remote: If True, start a tunnel (cloudflared/ngrok) for 4G access.
            port: Port for the vault UI / Phi Bridge server (default 5566).
        """
        # Boot
        print("\n  Booting Integrated Cognitive System...\n")
        status = self.boot()

        alive = sum(1 for v in status.values() if v == "alive")
        total = len(status)
        print(f"\n  Boot complete: {alive}/{total} subsystems online.\n")
        for name, st in status.items():
            marker = "+" if st == "alive" else "-"
            print(f"    [{marker}] {name}: {st}")
        print()

        # Start background threads
        self._start_tick_thread()
        if _HAS_MARKET_REFRESHER and _start_market_refresher is not None:
            try:
                self._market_refresher = _start_market_refresher()
                print("  Market data refresher: started (catches up last 72h, then every 2h)")
            except Exception as _mre:
                print(f"  Market data refresher: failed to start ({_mre})")
        # Dashboard collects state via ThoughtBus subscriptions but does not
        # start its render thread — Rich Live would conflict with stdin input().
        # Live data is available via /status command, Vault UI web, and phone.

        # TRINITY + ANTIVIRUS + CALENDAR + SWARM — full self-authoring stack.
        from aureon.core.aureon_self_introspection import get_self_introspection
        from aureon.core.aureon_cognitive_authoring_loop import launch_authoring_loop
        from aureon.core.aureon_geometric_live_chain import launch_geometric_chain
        from aureon.core.aureon_self_check_scanner import launch_self_check_scanner
        from aureon.core.aureon_phi_calendar import launch_phi_calendar
        from aureon.core.aureon_repair_swarm import launch_repair_swarm
        get_self_introspection()
        launch_authoring_loop()
        launch_geometric_chain()
        launch_self_check_scanner()
        launch_phi_calendar()
        launch_repair_swarm()
        print("  Self-authoring stack: introspection + authoring + geometric + scanner + calendar + swarm: started")

        # Start Vault UI + Phi Bridge server
        ui_host = "0.0.0.0" if (lan or remote) else "127.0.0.1"
        if self.vault_app is not None:
            self._start_vault_ui(host=ui_host, port=port)
            lan_ip = self._detect_lan_ip() if (lan or remote) else "127.0.0.1"
            print(f"  Vault UI:    http://{lan_ip}:{port}/")
            if lan:
                print(f"  Phi Bridge:  http://{lan_ip}:{port}/bridge")
                print(f"  (Phone: same WiFi → open the bridge URL)")

            # Remote tunnel for 4G / internet access
            if remote:
                print(f"  Starting tunnel for 4G access...")
                tunnel_url = self._start_tunnel(port)
                if tunnel_url:
                    print(f"  Remote URL:  {tunnel_url}")
                    print(f"  Phone (4G):  {tunnel_url}/bridge")
                    print(f"  (Open this URL on your phone — works over 4G, anywhere)")
                else:
                    print(f"  Tunnel failed. Install one of:")
                    print(f"    cloudflared: https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/")
                    print(f"    ngrok:       https://ngrok.com/download")
                    print(f"    pyngrok:     pip install pyngrok")
            print()

        print("  Commands: /status  /goal  /saas  /accounts  /contracts  /pause  /resume  /cancel  /coherence  /quit")
        print("  Type any text to submit as a goal.\n")

        # Input loop (main thread)
        while self._running:
            try:
                raw = input("You > ").strip()
            except (EOFError, KeyboardInterrupt):
                break

            if not raw:
                continue

            response = self.process_user_input(raw)
            if response == "__QUIT__":
                break
            if response:
                print(f"\n{response}\n")

        self.shutdown()

    def shutdown(self) -> None:
        """Stop all loops and save state."""
        print("\n  Shutting down ICS...")
        self._running = False

        if self.dashboard is not None:
            try:
                self.dashboard.stop()
            except Exception:
                pass

        if self.sentient_loop is not None:
            try:
                self.sentient_loop.stop()
            except Exception:
                pass

        if self.feedback_loop is not None:
            try:
                self.feedback_loop.stop()
            except Exception:
                pass

        if self.cortex is not None:
            try:
                self.cortex.stop()
            except Exception:
                pass

        if self.mycelium_mind is not None:
            try:
                self.mycelium_mind.stop()
            except Exception:
                pass

        if self.metacognition is not None:
            try:
                self.metacognition.stop()
            except Exception:
                pass

        if self.love_stream is not None:
            try:
                self.love_stream.stop()
            except Exception:
                pass

        if self.source_law is not None:
            try:
                self.source_law.stop()
            except Exception:
                pass

        if self.mirror is not None:
            try:
                self.mirror.stop()
            except Exception:
                pass

        if self.lambda_engine is not None:
            try:
                self.lambda_engine.save_history()
            except Exception:
                pass

        if self.knowledge_dataset is not None:
            try:
                self.knowledge_dataset.save()
            except Exception:
                pass

        if self.self_research_loop is not None:
            try:
                self.self_research_loop.stop()
            except Exception:
                pass

        if self.vault_knowledge_bridge is not None:
            try:
                self.vault_knowledge_bridge.stop()
            except Exception:
                pass

        if self._market_refresher is not None:
            try:
                self._market_refresher.stop()
            except Exception:
                pass

        if self._tick_thread is not None:
            self._tick_thread.join(timeout=3)

        print("  ICS shutdown complete.")

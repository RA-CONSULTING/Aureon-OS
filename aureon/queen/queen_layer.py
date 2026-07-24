#!/usr/bin/env python3
"""
Queen Layer -- The Top-Level Orchestrator

The Queen is the TOP LAYER of the Aureon operating system.
She boots first, activates all subsystems beneath her, monitors them
through the ThoughtBus, and ensures the entire machine is running
at full capacity.

Architecture:
    Queen Layer (this file)
        |
        +-- Queen Hive Mind (central consciousness)
        |       |
        |       +-- wire_all_systems() -- core wiring (enigma, mycelium, etc.)
        |       +-- take_full_control() -- exchange + system control
        |
        +-- Infrastructure (Intelligence Engine, Feed Hub, System Wiring, Whale Sonar)
        |
        +-- Queen Modules (56 modules: HiveCommand, SentientLoop, DeepIntelligence, ...)
        |
        +-- Domain Systems (harmonic, scanners, wisdom, analytics, bots_intelligence, ...)
        |
        +-- Execution (MicroProfitLabyrinth, API Server)

Every system is activated safely (try/except), wired to the ThoughtBus,
and tracked in a health registry. The machine runs at whatever capacity
is available -- offline systems are logged but never crash the boot.

Gary Leckey & Tina Brown | April 2026 | Queen at the Top
"""

from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)

import importlib
import logging
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ============================================================================
# DOMAIN SYSTEMS REGISTRY
# Each entry: (name, module_path, init_kwargs)
#   init_kwargs can contain:
#     class_name  -- instantiate this class
#     singleton_fn -- call this module-level function to get/create instance
#     (empty dict) -- just import the module (side-effect activation)
# ============================================================================

DOMAIN_SYSTEMS: List[tuple] = [
    # ── intelligence/ ─────────────────────────────────────────────────
    ("real_intelligence_engine",      "aureon_real_intelligence_engine",      {"singleton_fn": "get_intelligence_engine"}),
    ("dr_auris_throne",              "dr_auris_throne",                      {"singleton_fn": "get_dr_auris_throne"}),
    ("timeline_oracle",               "aureon_timeline_oracle",               {"class_name": "TimelineOracle"}),
    ("unified_data_puller",           "aureon_unified_intelligence_registry", {"singleton_fn": "get_unified_puller"}),
    ("unified_decision_engine",       "aureon_unified_decision_engine",       {"class_name": "UnifiedDecisionEngine"}),
    ("market_pulse",                  "aureon_market_pulse",                  {}),  # needs client arg — import only
    ("phase_transition_detector",     "aureon_phase_transition_detector",     {"class_name": "PhaseTransitionDetector"}),
    ("truth_prediction_engine",       "aureon_truth_prediction_engine",       {"class_name": "TruthPredictionEngine"}),
    ("integrated_forecast",           "aureon_integrated_forecast",           {}),  # dataclass — import only

    # ── harmonic/ ─────────────────────────────────────────────────────
    ("harmonic_chain_master",         "aureon_harmonic_chain_master",         {"class_name": "HarmonicChainMaster"}),
    ("harmonic_wave_fusion",          "aureon_harmonic_fusion",               {"singleton_fn": "get_harmonic_fusion"}),
    ("harmonic_signal_chain",         "aureon_harmonic_signal_chain",         {"class_name": "HarmonicSignalChain"}),
    ("harmonic_seed",                 "aureon_harmonic_seed",                 {"class_name": "HarmonicSeedLoader"}),
    ("harmonic_counter_frequency",    "aureon_harmonic_counter_frequency",    {"singleton_fn": "get_counter_frequency"}),
    ("harmonic_waveform",             "aureon_harmonic_waveform",             {"class_name": "HarmonicWaveformScanner"}),
    ("harmonic_momentum_wave",        "aureon_harmonic_momentum_wave",        {"class_name": "HarmonicMomentumWaveScanner"}),
    ("planetary_harmonic_sweep",      "aureon_planetary_harmonic_sweep",      {}),
    ("schumann_resonance_bridge",     "aureon_schumann_resonance_bridge",     {}),
    ("market_energy_field",           "aureon_market_energy_field",           {}),

    # ── scanners/ ─────────────────────────────────────────────────────
    ("ocean_wave_scanner",            "aureon_ocean_wave_scanner",            {"class_name": "OceanWaveScanner"}),
    ("strategic_warfare_scanner",     "aureon_strategic_warfare_scanner",     {"singleton_fn": "get_warfare_scanner"}),
    ("global_wave_scanner",           "aureon_global_wave_scanner",           {"class_name": "GlobalWaveScanner"}),
    ("obsidian_filter",               "aureon_obsidian_filter",               {"class_name": "AureonObsidianFilter"}),
    ("phantom_signal_filter",         "aureon_phantom_signal_filter",         {"class_name": "PhantomSignalFilter"}),
    ("alpaca_stock_scanner",          "aureon_alpaca_stock_scanner",          {}),

    # ── wisdom/ ───────────────────────────────────────────────────────
    ("ghost_dance_protocol",          "aureon_ghost_dance_protocol",          {"singleton_fn": "get_ghost_dance"}),
    ("enigma_dream",                  "aureon_enigma_dream",                  {}),
    ("qgita_framework",               "aureon_qgita_framework",               {}),
    ("plums_guardian",                 "aureon_plums_guardian",                 {}),

    # ── analytics/ ────────────────────────────────────────────────────
    ("manipulation_hunter",           "aureon_historical_manipulation_hunter", {"singleton_fn": "get_manipulation_hunter"}),
    ("lighthouse",                    "aureon_lighthouse",                     {}),
    ("whale_behavior_predictor",      "aureon_whale_behavior_predictor",      {"class_name": "WhaleBehaviorPredictor"}),
    ("whale_pattern_mapper",          "aureon_whale_pattern_mapper",          {"class_name": "WhalePatternMapper"}),
    ("whale_shape_registry",          "aureon_whale_shape_registry",          {"class_name": "WhaleShapeRegistry"}),

    # ── bots_intelligence/ ────────────────────────────────────────────
    ("bot_shape_scanner",             "aureon_bot_shape_scanner",             {"singleton_fn": "get_bot_scanner"}),
    ("orca_intelligence",             "aureon_orca_intelligence",             {"singleton_fn": "get_orca"}),
    ("bot_shape_classifier",          "aureon_bot_shape_classifier",          {"class_name": "BotShapeClassifier"}),
    ("global_firm_intelligence",      "aureon_global_firm_intelligence",      {}),
    ("orca_monitor",                  "aureon_orca_monitor",                  {"class_name": "OrcaMonitor"}),

    # ── core/ (supplementary -- ThoughtBus and mycelium boot earlier)
    ("consciousness_module",          "aureon_consciousness_module",          {"class_name": "ConsciousnessModule"}),
    ("immune_system",                 "aureon_immune_system",                 {"class_name": "AureonImmuneSystem"}),
    ("knowledge_base",                "aureon_knowledge_base",                {"singleton_fn": "create_knowledge_base"}),
    ("lambda_engine",                 "aureon_lambda_engine",                 {"class_name": "LambdaEngine"}),
    ("memory_core",                   "aureon_memory_core",                   {"class_name": "AureonMemoryCore"}),
    ("elephant_memory",               "aureon_elephant_memory",               {}),
    ("system_coordinator",            "aureon_system_coordinator",            {}),

    # ── strategies/ ───────────────────────────────────────────────────
    ("probability_ultimate_intelligence", "probability_ultimate_intelligence", {"singleton_fn": "get_ultimate_intelligence"}),
    ("probability_intelligence_matrix",  "probability_intelligence_matrix",   {"singleton_fn": "get_probability_matrix"}),

    # ── atn/ ──────────────────────────────────────────────────────────
    ("atn_controller",                "aureon_atn_controller",                {}),
]

# Queen modules that need special handling (class_name, start method)
QUEEN_PRIORITY_MODULES: List[tuple] = [
    # (module_name, class_name, should_call_start)
    ("queen_cortex",            "QueenCortex",           True),   # Brainwave layers — must boot BEFORE sentient loop
    ("queen_source_law",        "SourceLawEngine",       True),   # 10-9-1 consciousness funnel — accumulates in superposition
    ("queen_mycelium_mind",     "MyceliumMind",          True),   # Thought propagation — spores carry thoughts, pathways learn
    ("queen_metacognition",     "QueenMetacognition",    True),   # Self-reflective mirror — 5 W reflection on cognitions
    ("queen_sentient_loop",     "QueenSentientLoop",     True),
    ("queen_deep_intelligence", "QueenDeepIntelligence",  False),
    ("queen_fully_online",      "QueenFullyOnline",       False),
    ("queen_volume_hunter",     "QueenVolumeHunter",      False),
    ("queen_signal_reader",     "QueenSignalReader",      False),
]

# Modules to skip during auto-discovery (self, __init__, or handled above)
QUEEN_MODULE_SKIP = frozenset({
    "queen_layer",     # this file
    "__init__",
})


class QueenLayer:
    """
    The Queen Layer -- top-level orchestrator for the entire Aureon system.

    Boot sequence:
        1. Queen awakens (singleton + take_full_control)
        2. Core systems wired (existing wire_all_systems)
        3. Infrastructure booted (Intelligence, Feed Hub, Wiring, Sonar)
        4. Queen modules activated (56 modules auto-discovered)
        5. Domain systems activated (harmonic, scanners, wisdom, etc.)
        6. Execution layer started (Labyrinth, API)
    """

    def __init__(self, live_trading: bool = False):
        self.live_trading = live_trading
        self.registry: Dict[str, Dict[str, Any]] = {}
        self.queen = None
        self.thought_bus = None
        self.labyrinth = None
        self._booted = False

    # ================================================================
    # PUBLIC API
    # ================================================================

    def boot(self) -> Dict[str, Any]:
        """Boot the entire machine with the Queen at the top. Returns health summary."""
        if self._booted:
            return self.get_health()

        boot_start = time.time()
        print("\n" + "=" * 80)
        print("  QUEEN LAYER -- BOOTING ALL SYSTEMS")
        print("  The Queen awakens first. All systems activate beneath her.")
        print("=" * 80)

        self._phase1_queen_awakens()
        self._phase2_wire_core_systems()
        self._phase3_boot_infrastructure()
        self._phase4_activate_queen_modules()
        self._phase5_activate_domain_systems()
        self._phase6_start_execution()

        self._booted = True
        elapsed = time.time() - boot_start

        # HNC direction: at boot the base layer reads the ONE canonical field and publishes it, so the
        # first-pass orchestration is coupled to the shared symbolic.life.pulse — not only the late
        # conscience veto. Guarded/offline-safe.
        field = self.substrate_field()
        self._publish("queen.layer.substrate_field", field)

        # Publish boot complete to ThoughtBus
        self._publish("queen.layer.boot_complete", {
            "elapsed_s": round(elapsed, 2),
            "health": self.get_health(),
            "substrate_field": field,
        })

        health = self.get_health()
        print(f"\n{'=' * 80}")
        print(f"  QUEEN LAYER BOOT COMPLETE")
        print(f"  Systems: {health['online']}/{health['total']} ONLINE  |  "
              f"Offline: {health['offline']}  |  Time: {elapsed:.1f}s")
        print(f"{'=' * 80}\n")

        return health

    def get_health(self) -> Dict[str, Any]:
        """Return current health of all registered systems."""
        online = sum(1 for v in self.registry.values() if v.get("status") == "ONLINE")
        offline = sum(1 for v in self.registry.values() if v.get("status") == "OFFLINE")
        total = len(self.registry)
        systems = {}
        for name, info in self.registry.items():
            systems[name] = {
                "status": info.get("status", "UNKNOWN"),
                "error": info.get("error"),
            }
        return {
            "online": online,
            "offline": offline,
            "total": total,
            "systems": systems,
        }

    def substrate_field(self) -> Dict[str, Any]:
        """Read the ONE canonical HNC field (``symbolic.life.pulse`` via ``read_canonical_field``).

        The base Queen layer is directed by the same shared field the conscience veto and the rest of
        the organism read — coherence Γ / symbolic-life score ψ, not a private number. Guarded and
        offline-safe: returns ``{"available": False}`` when the HNC daemon is not publishing, never raises.
        """
        try:
            from aureon.core.hnc_field import read_canonical_field

            return read_canonical_field().to_dict()
        except Exception:  # noqa: BLE001 — the field is best-effort; the layer boots regardless
            return {"available": False}

    def get_system(self, name: str) -> Optional[Any]:
        """Retrieve a booted system instance by name."""
        entry = self.registry.get(name)
        return entry.get("instance") if entry else None

    # ================================================================
    # BOOT PHASES
    # ================================================================

    def _phase1_queen_awakens(self):
        """Phase 1: The Queen wakes up and takes full control."""
        print("\n[Phase 1/6] QUEEN AWAKENS")

        # ThoughtBus first -- the nervous system
        try:
            from aureon.core.aureon_thought_bus import get_thought_bus
            self.thought_bus = get_thought_bus()
            self._register("thought_bus", self.thought_bus)
            print("   ThoughtBus: ONLINE")
        except Exception as e:
            logger.warning(f"ThoughtBus unavailable: {e}")
            self._register("thought_bus", None, error=str(e))

        # Chirp Bus
        try:
            from aureon.core.aureon_chirp_bus import get_chirp_bus
            chirp = get_chirp_bus()
            self._register("chirp_bus", chirp)
            print("   ChirpBus: ONLINE")
        except Exception as e:
            self._register("chirp_bus", None, error=str(e))

        # Queen singleton
        try:
            from aureon.utils.aureon_queen_hive_mind import get_queen
            self.queen = get_queen()
            self._register("queen_hive_mind", self.queen)
            print("   Queen Hive Mind: ONLINE")
        except Exception as e:
            logger.error(f"Queen Hive Mind failed: {e}")
            self._register("queen_hive_mind", None, error=str(e))
            return

        # Take full control
        try:
            if hasattr(self.queen, "take_full_control"):
                self.queen.take_full_control()
            self.queen.has_full_control = True
            self.queen.trading_enabled = True
            print("   Queen: FULL CONTROL GRANTED")
        except Exception as e:
            logger.warning(f"take_full_control warning: {e}")

        self._publish("queen.layer.phase1_complete", {"queen": "ONLINE"})

    def _phase2_wire_core_systems(self):
        """Phase 2: Wire the Queen to her core subsystems using existing wire methods."""
        print("\n[Phase 2/6] WIRING CORE SYSTEMS")
        if not self.queen:
            print("   SKIPPED (Queen not available)")
            return

        # Use the existing wire_all_systems from queen_hive_mind module
        try:
            from aureon.utils.aureon_queen_hive_mind import wire_all_systems
            results = wire_all_systems(self.queen)
            wired = sum(1 for v in results.values() if v)
            total = len(results)
            for name, success in results.items():
                self._register(f"queen_wire_{name}", name if success else None,
                               error=None if success else "wire failed")
            print(f"   Queen core wiring: {wired}/{total} systems wired")
        except Exception as e:
            logger.warning(f"wire_all_systems error: {e}")
            print(f"   Queen core wiring: error ({e})")

        self._publish("queen.layer.phase2_complete", {"wired": True})

    def _phase3_boot_infrastructure(self):
        """Phase 3: Boot Intelligence Engine, Feed Hub, System Wiring, Whale Sonar."""
        print("\n[Phase 3/6] BOOTING INFRASTRUCTURE")

        # Intelligence Engine
        engine = self._safe_activate(
            "intelligence_engine",
            "aureon_real_intelligence_engine",
            singleton_fn="get_intelligence_engine",
        )
        if engine and self.queen:
            self.queen.intelligence_engine = engine
            if hasattr(engine, "bot_profiler"):
                self.queen.bot_profiler = engine.bot_profiler
            if hasattr(engine, "whale_predictor"):
                self.queen.whale_predictor = engine.whale_predictor

        # Feed Hub
        feed_hub = self._safe_activate(
            "feed_hub",
            "aureon_real_data_feed_hub",
            singleton_fn="get_feed_hub",
        )
        if feed_hub and self.queen:
            self.queen.feed_hub = feed_hub

        # Start global feed
        try:
            from aureon.data_feeds.aureon_real_data_feed_hub import start_global_feed
            start_global_feed(interval=2.0)
            print("   Global feed: STARTED (2s interval)")
        except Exception as e:
            logger.debug(f"start_global_feed: {e}")

        # System Wiring (wire all 178+ systems to feed hub)
        try:
            from aureon.core.aureon_system_wiring import wire_all_systems as wire_all_feed_systems
            wired_count = wire_all_feed_systems()
            self._register("system_wiring", True)
            print(f"   System wiring: {wired_count} systems connected")
        except Exception as e:
            self._register("system_wiring", None, error=str(e))
            logger.warning(f"System wiring error: {e}")

        # Whale Sonar
        self._safe_activate(
            "whale_sonar",
            "mycelium_whale_sonar",
            singleton_fn="create_and_start_sonar",
        )

        # Mycelium Network
        try:
            from aureon.core.aureon_mycelium import MyceliumNetwork
            initial_cap = getattr(self.queen, "initial_capital", 100.0) if self.queen else 100.0
            mycelium = MyceliumNetwork(initial_capital=initial_cap)
            self._register("mycelium_network", mycelium)
        except Exception as e:
            self._register("mycelium_network", None, error=str(e))

        self._publish("queen.layer.phase3_complete", {"infrastructure": "ONLINE"})

    def _phase4_activate_queen_modules(self):
        """Phase 4: Activate all queen/* modules -- the Queen's cognitive faculties."""
        print("\n[Phase 4/6] ACTIVATING QUEEN MODULES")

        # Priority modules first (these have known classes and lifecycle)
        for module_name, class_name, should_start in QUEEN_PRIORITY_MODULES:
            instance = self._safe_activate(
                module_name,
                module_name,
                class_name=class_name,
            )
            if instance and should_start and hasattr(instance, "start"):
                try:
                    instance.start()
                    logger.info(f"   {module_name}: started")
                except Exception as e:
                    logger.debug(f"   {module_name} start error: {e}")

        # Auto-discover remaining queen_*.py modules
        queen_dir = Path(__file__).parent
        priority_names = {m[0] for m in QUEEN_PRIORITY_MODULES}

        activated = 0
        for py_file in sorted(queen_dir.glob("queen_*.py")):
            module_name = py_file.stem
            if module_name in QUEEN_MODULE_SKIP or module_name in priority_names:
                continue
            # Already registered from priority list? skip
            if module_name in self.registry:
                continue
            self._safe_activate(module_name, module_name)
            activated += 1

        # In-House AI Bridge — sovereign consciousness enhancement
        try:
            from aureon.queen.queen_inhouse_ai_bridge import get_queen_ai_bridge
            bridge = get_queen_ai_bridge()
            bridge.start()
            if self.thought_bus is not None and hasattr(bridge, "_thought_bus"):
                bridge._thought_bus = self.thought_bus
            self._register("queen_inhouse_ai_bridge", bridge)
            print("   Queen AI Bridge: ONLINE (sovereign in-house AI)")
        except Exception as e:
            self._register("queen_inhouse_ai_bridge", None, error=str(e))
            logger.debug("Queen AI Bridge unavailable: %s", e)

        online = sum(
            1 for k, v in self.registry.items()
            if k.startswith("queen_") and v.get("status") == "ONLINE"
        )
        print(f"   Queen modules: {online} ONLINE (of {len(priority_names) + activated + 1} attempted)")

        self._publish("queen.layer.phase4_complete", {"queen_modules_online": online})

    def _phase5_activate_domain_systems(self):
        """Phase 5: Activate systems from all domains (harmonic, scanners, wisdom, etc.)."""
        print("\n[Phase 5/6] ACTIVATING DOMAIN SYSTEMS")

        for name, module_path, init_kwargs in DOMAIN_SYSTEMS:
            # Skip if already activated in phase 3
            if name in self.registry:
                continue
            instance = self._safe_activate(name, module_path, **init_kwargs)
            # Start systems that have a lifecycle start() method
            if instance is not None and hasattr(instance, "start") and callable(instance.start):
                try:
                    instance.start()
                except Exception as e:
                    logger.debug(f"Could not start {name}: {e}")

        domain_online = sum(
            1 for name, _mod, _kw in DOMAIN_SYSTEMS
            if self.registry.get(name, {}).get("status") == "ONLINE"
        )
        print(f"   Domain systems: {domain_online}/{len(DOMAIN_SYSTEMS)} ONLINE")

        self._publish("queen.layer.phase5_complete", {"domain_systems_online": domain_online})

    def _phase6_start_execution(self):
        """Phase 6: Start execution layer (Labyrinth + API)."""
        print("\n[Phase 6/6] STARTING EXECUTION LAYER")

        # Micro Profit Labyrinth
        try:
            from aureon.trading.micro_profit_labyrinth import MicroProfitLabyrinth
            self.labyrinth = MicroProfitLabyrinth()
            self.labyrinth.dry_run = not self.live_trading
            self._register("micro_profit_labyrinth", self.labyrinth)

            # Wire Queen to labyrinth
            if self.queen and hasattr(self.queen, "wire_micro_labyrinth"):
                self.queen.wire_micro_labyrinth(self.labyrinth)

            mode = "LIVE" if self.live_trading else "DRY-RUN"
            print(f"   Micro Profit Labyrinth: ONLINE ({mode})")
        except Exception as e:
            self._register("micro_profit_labyrinth", None, error=str(e))
            logger.warning(f"Labyrinth error: {e}")

        # Wire additional execution systems to Queen
        if self.queen and self.labyrinth:
            try:
                # Reuse the master launcher's wire_queen_systems for HFT + enigma
                from aureon.autonomous.aureon_master_launcher import wire_queen_systems
                summary = wire_queen_systems(self.queen, self.labyrinth)
                for k, v in summary.items():
                    if v and k not in self.registry:
                        self._register(f"exec_{k}", True)
            except Exception as e:
                logger.debug(f"wire_queen_systems: {e}")

        # API Server (best-effort, in background thread)
        try:
            from aureon.bridges.aureon_frontend_bridge import start_api_server
            api_thread = threading.Thread(target=start_api_server, daemon=True)
            api_thread.start()
            self._register("api_server", True)
            print("   API Server: STARTED")
        except Exception as e:
            self._register("api_server", None, error=str(e))
            logger.debug(f"API server: {e}")

        self._publish("queen.layer.phase6_complete", {"execution": "ONLINE"})

    # ================================================================
    # HELPERS
    # ================================================================

    def _safe_activate(
        self,
        name: str,
        module_path: str,
        class_name: str = None,
        singleton_fn: str = None,
    ) -> Optional[Any]:
        """Safely import, instantiate, wire ThoughtBus, and register a system."""
        try:
            mod = importlib.import_module(module_path)

            if singleton_fn:
                instance = getattr(mod, singleton_fn)()
            elif class_name:
                cls = getattr(mod, class_name)
                instance = cls()
            else:
                # Module-level activation (some modules do work on import)
                instance = mod

            # Wire ThoughtBus if the system accepts one
            if self.thought_bus is not None:
                if hasattr(instance, "thought_bus") and instance.thought_bus is None:
                    instance.thought_bus = self.thought_bus
                if hasattr(instance, "set_thought_bus") and callable(instance.set_thought_bus):
                    instance.set_thought_bus(self.thought_bus)
                if hasattr(instance, "_thought_bus") and instance._thought_bus is None:
                    instance._thought_bus = self.thought_bus

            self._register(name, instance)
            return instance

        except Exception as e:
            self._register(name, None, error=str(e))
            logger.debug(f"Could not activate {name}: {e}")
            return None

    def _register(self, name: str, instance: Any, error: str = None):
        """Register a system in the health registry."""
        if instance is not None and error is None:
            self.registry[name] = {
                "status": "ONLINE",
                "instance": instance,
                "ts": time.time(),
            }
        else:
            self.registry[name] = {
                "status": "OFFLINE",
                "instance": None,
                "error": error,
                "ts": time.time(),
            }

    def _publish(self, topic: str, payload: dict):
        """Publish a lifecycle event to the ThoughtBus."""
        if self.thought_bus is None:
            return
        try:
            from aureon.core.aureon_thought_bus import Thought
            thought = Thought(
                source="queen_layer",
                topic=topic,
                payload=payload,
            )
            self.thought_bus.publish(thought)
        except Exception:
            pass


# ============================================================================
# SINGLETON + PUBLIC API
# ============================================================================

_QUEEN_LAYER: Optional[QueenLayer] = None


def get_queen_layer(live_trading: bool = False) -> QueenLayer:
    """Get or create the global QueenLayer singleton."""
    global _QUEEN_LAYER
    if _QUEEN_LAYER is None:
        _QUEEN_LAYER = QueenLayer(live_trading=live_trading)
    return _QUEEN_LAYER


def boot_queen_layer(live_trading: bool = False) -> Dict[str, Any]:
    """Boot the Queen Layer and return health summary."""
    layer = get_queen_layer(live_trading=live_trading)
    return layer.boot()

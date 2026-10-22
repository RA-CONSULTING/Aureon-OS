"""🫀 Organ Registry — supervised processes for the fused runtime.

Replaces the stale pids/*.pid mechanism with a JSON registry plus REAL
liveness checks (psutil when available, tasklist fallback otherwise).

Supervised organs (dependency order — data feeders first, radar last):
  real_time_data_feeder     — multi-source real-time data feed (60s cycle)
  schumann_real_daemon      — live Schumann resonance sensor (real data)
  planetary_monitor_daemon  — planetary/Kp/solar-wind monitor loop
  solar_system_collector    — heliospheric metrics collector
  sero_space_weather        — NOAA/SWPC space-weather bridge (daemon loop)
  sero_autonomous_expansion — continuous mode (health cycles)
  aureon_radar_bridge       — aureon_radar/aureon_bridge.py in
                              SIGNAL/DRY-RUN mode ONLY. The launch command
                              is fixed below and must never carry a
                              live-trading flag; there is intentionally no
                              code path here that adds one.
  aureon_radar_suite        — aureon_radar/master_launcher.py (Unified Hub
                              + Phi-Radar). This launcher runs LIVE trading
                              on Capital.com, so its start is pinned behind
                              the capital release pin: it refuses to spawn
                              until aureon_fusion/state/capital_release.flag
                              exists. The registry never creates that flag;
                              only the orchestrator pulls the pin after the
                              audit. Status/stop supervision works regardless.

Activation wave (2026-09-04, second entry) added four organs:
  mind_thought_action_hub   — upstream aureon/autonomous/
                              aureon_mind_thought_action_hub.py as a module
                              launch (aiohttp dashboard on port 13002).
                              Read-only verification hits GET endpoints only.
                              Its embedded self-questioning loop is disabled
                              (AUREON_SELF_QUESTIONING_AI=0) because
                              self_questioning_ai runs as its own organ.
  self_questioning_ai       — workspace aureon_self_questioning_runner.py
                              driving the upstream SelfQuestioningAI engine
                              (one cycle + real sleep per period; upstream
                              repo read-only). Requires a live Ollama on
                              localhost:11434; the registrar probes it before
                              allowing the start.
  hnc_core                  — aureon_fusion.hnc_core run (ws2 deliverable:
                              the continuous Master-Equation organ; upstream
                              LambdaEngine imported under suppression flags,
                              state pinned to aureon_fusion/state/).
  soul_protection_daemon    — workspace soul_protection_daemon.py (ws3
                              deliverable: 5s protection cycle).
  queen_mind                — the owner's OWN queen metacognition stack
                              (UNCAGING wave, REGISTRAR deliverable): 120 s
                              metacognitive cycle on the loopback-only model
                              plane. Spec resolves at import time — fused
                              module preferred, workspace script fallback,
                              dormant-with-reason if the MIND peer has not
                              delivered.
  heartbeat_daemon          — Track A scheduler organ: 300 s cycle running
                              heartbeat_exec.run() (heals sero_feel/, keeps
                              heartbeat_last_results.json fresh for
                              queen_mind) plus the two orphan one-shot
                              tools (solar_system_temporal_bridge merge,
                              real_data_feeds batch fetch on a worker
                              thread, skip-if-busy).

Every activation-wave organ is launched with
AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS=1 and AUREON_AUDIT_MODE=1 in its
environment, `python -u`, cwd=workspace, and (for the upstream module
launches) PYTHONPATH pinned to the upstream repo root.

Dormant organs: registered-but-not-started. A dormant organ refuses start
(like the capital pin's 'held') and carries a human-readable reason in
status. Use when a workstream deliverable is missing or an organ must be
kept offline.

Verbs: status | start <organ>|--all | stop <organ>|--all | restart <organ> |
       dormant <organ> <reason> | undormant <organ> |
       prune (kill duplicate/orphan instances of registered organ scripts,
       keeping the registry-recorded PID alive)
Stale recorded PIDs are auto-reconciled on every registry load.
Import-safe: nothing spawns at import time.
"""

import contextlib
import csv
import io
import json
import os
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

from .paths import (
    WORKSPACE, LOGS, FUSION_STATE, SERO_AUTONOMOUS_EXPANSION, AUREON_RADAR,
    SCHUMANN_DAEMON, PLANETARY_DAEMON, REALTIME_FEEDER, AUREON_UPSTREAM,
)
from . import events

REGISTRY_FILE = FUSION_STATE / "organ_registry.json"
OBSERVED_IDENTITY_FILE = FUSION_STATE / "observed_process_identity.json"

# Capital release pin. Owned by the orchestrator — this module only READS
# its presence. Never create, touch, or delete it here.
CAPITAL_RELEASE_FLAG = FUSION_STATE / "capital_release.flag"

# Script paths not yet mirrored in paths.py (paths.py is import-only; the
# canonical WORKSPACE root above keeps these correct under SERO_WORKSPACE).
SOLAR_SYSTEM_COLLECTOR = WORKSPACE / "solar_system_collector.py"
SERO_SPACE_WEATHER = WORKSPACE / "sero_space_weather.py"
RADAR_MASTER_LAUNCHER = AUREON_RADAR / "master_launcher.py"

# UNITY SUPERVISOR wave (2026-09-07 build): ten previously unsupervised
# radar/fusion loops plus the supervisor itself and the flight-recorder
# seat (delivered by the FLIGHT-RECORDER agent). These organs are launched
# from either aureon_radar/ or the workspace root, matching the command
# lines already observed in the live fleet.
GRAND_WHEEL = Path(__file__).resolve().parent / "grand_wheel.py"
KNOWLEDGE_PULSE_FEEDER = Path(__file__).resolve().parent / "knowledge_pulse_feeder.py"
TRADING_PROGRESS_MONITOR = AUREON_RADAR / "trading_progress_monitor.py"
PORTFOLIO_WRITER_LOOP = AUREON_RADAR / "_portfolio_writer_loop.py"
TEMPORAL_REFRESH_LOOP = AUREON_RADAR / "_temporal_refresh_loop.py"
WORLD_DIGEST_LOOP = AUREON_RADAR / "_world_digest_loop.py"
HARMONIC_SEED_LOOP = AUREON_RADAR / "_harmonic_seed_loop.py"
GLOBAL_ENERGY_AGGREGATOR = AUREON_RADAR / "global_energy_aggregator.py"
ORCA_UNIFIED_KILL_CHAIN = AUREON_RADAR / "bots" / "orca_unified_kill_chain.py"
ORCA_COMMAND_CENTER = AUREON_RADAR / "bots" / "orca_command_center.py"
UNITY_SUPERVISOR = Path(__file__).resolve().parent / "unity_supervisor.py"
FLIGHT_RECORDER = Path(__file__).resolve().parent / "flight_recorder.py"
BUS_BRIDGE = Path(__file__).resolve().parent / "bus_bridge.py"

# Owner-approval gate for queen_mind restart. Only the unity supervisor
# checks this; the file is NEVER created or modified by the registry.
QUEEN_MIND_RESTART_APPROVAL = FUSION_STATE / "queen_mind_restart_approved.json"

# Activation-wave organs (2026-09-04 second memory entry).
# HNC_CORE_DAEMON is the retired pre-fusion script; the ws2 deliverable is
# the fused module aureon_fusion.hnc_core, launched with `run`.
SOUL_PROTECTION_DAEMON = WORKSPACE / "soul_protection_daemon.py"
MIND_HUB_MODULE = "aureon.autonomous.aureon_mind_thought_action_hub"

# UNCAGING wave (REGISTRAR workstream): queen_mind — the owner's OWN queen
# metacognition/consciousness/sentience/self-enhancement stack (upstream
# aureon/queen), uncaged under fusion discipline. The model plane is
# hard-pinned to loopback Ollama in the organ's own code; the registry
# additionally refuses the spawn unless the local model answers its probe.
# The fused module aureon_fusion/queen_mind is the preferred deliverable; a
# workspace-root queen_mind.py is the accepted fallback. If NEITHER exists
# the organ is registered DORMANT with the reason recorded.
FUSED_QUEEN_MIND = Path(__file__).resolve().parent / "queen_mind.py"
WORKSPACE_QUEEN_MIND = WORKSPACE / "queen_mind.py"

# Upstream imports happen ONLY under these suppression env vars. Every
# activation-wave launch command carries both, per doctrine.
SUPPRESSION_ENV = {
    "AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS": "1",
    "AUREON_AUDIT_MODE": "1",
}

# Ollama probe for self_questioning_ai: the organ is meaningless without a
# local model answering on this port.
OLLAMA_PROBE_URL = "http://localhost:11434/api/tags"
OLLAMA_PROBE_TIMEOUT_S = 5.0


def _launch_env(extra: dict = None) -> dict:
    """Child environment for activation-wave organs: suppression env vars
    pinned, plus PYTHONPATH pinned to the upstream repo root so upstream
    module launches resolve the `aureon` package with cwd=workspace."""
    env = dict(os.environ)
    env.update(SUPPRESSION_ENV)
    existing = env.get("PYTHONPATH")
    upstream = str(AUREON_UPSTREAM)
    env["PYTHONPATH"] = upstream + (os.pathsep + existing if existing else "")
    if extra:
        env.update(extra)
    return env


def _radar_env(extra: dict = None) -> dict:
    """Child environment for aureon_radar scripts that import the upstream
    `aureon` package: PYTHONPATH pinned to the upstream repo root, but NO
    activation-wave suppression flags (radar loops run in their native
    mode)."""
    env = dict(os.environ)
    existing = env.get("PYTHONPATH")
    upstream = str(AUREON_UPSTREAM)
    env["PYTHONPATH"] = upstream + (os.pathsep + existing if existing else "")
    if extra:
        env.update(extra)
    return env


def _workspace_env(extra: dict = None) -> dict:
    """Child environment for aureon_fusion modules that need BOTH the workspace
    package (aureon_fusion.*) and the upstream package (aureon.*)."""
    env = dict(os.environ)
    existing = env.get("PYTHONPATH")
    parts = [str(WORKSPACE), str(AUREON_UPSTREAM)]
    if existing:
        parts.append(existing)
    env["PYTHONPATH"] = os.pathsep.join(parts)
    if extra:
        env.update(extra)
    return env


def ollama_available() -> bool:
    """True when a local Ollama answers the model-list probe. Read-only GET;
    stdlib only; short timeout — safe to call from start()."""
    try:
        import urllib.request
        req = urllib.request.Request(OLLAMA_PROBE_URL, method="GET")
        with urllib.request.urlopen(req, timeout=OLLAMA_PROBE_TIMEOUT_S) as resp:
            return resp.status == 200
    except Exception:
        return False


def mind_hub_port_available() -> bool:
    """True when the mind hub's port is free to bind."""
    try:
        import socket
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(("127.0.0.1", 13002)) != 0
    except Exception:
        return False


def _queen_mind_spec() -> dict:
    """Launch spec for the queen_mind organ, resolved at import time.

    Preferred: the fused module aureon_fusion/queen_mind (MIND workstream
    deliverable). Fallback: a workspace-root queen_mind.py script. When
    neither exists the organ is registered dormant with the reason on
    record — the registrar registers the seat even when the peer failed.
    Either way the launch carries the suppression env vars, `python -u`,
    cwd=workspace and a 120 s metacognitive cycle. NO Ollama preflight:
    per the owner's correction the Queen Mind reasons natively (HNC, AURIS,
    QGITA, internal knowledge systems, QueenProseComposer) — zero network,
    zero LLM — so the organ must start with Ollama absent.
    """
    spec = {
        "match": "queen_mind",
        "args": ["--interval", "120"],
        "cwd": str(WORKSPACE),
        "mode": "continuous (120s metacognitive cycle)",
        "log": str(LOGS / "organ_queen_mind.log"),
        "env": _launch_env(),
    }
    if FUSED_QUEEN_MIND.exists():
        spec["module"] = "aureon_fusion.queen_mind"
    elif WORKSPACE_QUEEN_MIND.exists():
        spec["script"] = str(WORKSPACE_QUEEN_MIND)
    else:
        spec["dormant"] = True
        spec["dormant_reason"] = (
            "queen_mind module not delivered by the MIND workstream "
            "(neither aureon_fusion/queen_mind.py nor workspace "
            "queen_mind.py exists) — registered dormant; undormant once "
            "the module lands, then start"
        )
    return spec


# Fixed launch commands. The radar bridge command is deliberately a plain
# `python aureon_bridge.py` — signal/dry-run only, never live execution.
# The table is in dependency order: data feeders first, radar organs last.
# `start --all` walks it forward, `stop --all` walks it in reverse.
ORGANS = {
    "unified_market_trader": {
        "module": "aureon.exchanges.unified_market_trader",
        "match": "aureon.exchanges.unified_market_trader",
        "args": ["--interval", "2"], "cwd": str(AUREON_UPSTREAM),
        "mode": "continuous (provider analysis; order and exchange mutation holds)",
        "log": str(LOGS / "organ_unified_market_trader.log"),
        "env": _radar_env({
            # The supervisor runs with suppressed imports; this analysis service
            # needs native provider clients, with mutations held separately below.
            "AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS": "0", "AUREON_AUDIT_MODE": "0",
            "AUREON_ENV_FILE": str(AUREON_RADAR / ".env"),
            "AUREON_DISABLE_REAL_ORDERS": "1", "AUREON_DISABLE_EXCHANGE_MUTATIONS": "1",
            "AUREON_ORDER_INTENT_PUBLISH": "0", "AUREON_LIVE_TRADING": "0",
            "AUREON_UNIFIED_ORDER_EXECUTOR": "0", "UNIFIED_LIGHTWEIGHT_KRAKEN_BOOT": "1",
            "UNIFIED_KRAKEN_SPOT_COST_BASIS_PROBE": "0", "CAPITAL_MIND_MAP_REFRESH_ENABLED": "0",
            "UNIFIED_CAPITAL_TICK_TIMEOUT_SEC": "5", "UNIFIED_KRAKEN_TICK_TIMEOUT_SEC": "5",
            "UNIFIED_EXCHANGE_DASHBOARD_PAYLOAD_TIMEOUT_SEC": "2",
            "UNIFIED_ORDERBOOK_PROBE_MAX_PER_TICK": "2", "UNIFIED_INTEL_ORDERBOOK_MAX_BONUS": "0",
            "PYTHONUTF8": "1",
        }),
    },
    "operator_gateway": {
        "requires_local_http_profile": True,
        "module": "aureon.operator.operator_server",
        "match": "aureon.operator.operator_server",
        "args": [], "cwd": str(AUREON_UPSTREAM),
        "mode": "continuous (existing local operator gateway on port 8080)",
        "log": str(LOGS / "organ_operator_gateway.log"),
        "env": _launch_env({
            "AUREON_ENV_FILE": str(AUREON_RADAR / ".env"),
            # Allow the operator's configured model to answer UI requests while
            # import audit guards and the four execution controls stay enabled.
            "AUREON_LLM_ALLOW_HTTP_IN_AUDIT": "1",
            "AUREON_LLM_REQUEST_TIMEOUT_S": "25",
            "AUREON_DISABLE_REAL_ORDERS": "1", "AUREON_DISABLE_EXCHANGE_MUTATIONS": "1",
            "AUREON_ORDER_INTENT_PUBLISH": "0", "AUREON_LIVE_TRADING": "0",
            "AUREON_UNIFIED_ORDER_EXECUTOR": "0", "PYTHONUTF8": "1",
        }),
    },
    "frontend_vite": {
        "requires_local_http_profile": True,
        "executable": r"C:\Program Files\nodejs\node.exe",
        "script": str(AUREON_UPSTREAM / "frontend" / "node_modules" / "vite" / "bin" / "vite.js"),
        "match": "node_modules\\vite\\bin\\vite.js",
        "args": ["--host", "127.0.0.1", "--port", "5173", "--strictPort"],
        "cwd": str(AUREON_UPSTREAM / "frontend"),
        "mode": "continuous (local frontend on port 5173)",
        "log": str(LOGS / "organ_frontend_vite.log"),
        "env": _launch_env({"AUREON_TERMINAL_STATE_URL": "http://127.0.0.1:8791",
                            "AUREON_OPERATOR_URL": "http://127.0.0.1:8080"}),
    },
    "unified_market_status": {
        "module": "aureon.exchanges.unified_market_status_server",
        "match": "aureon.exchanges.unified_market_status_server",
        "args": ["--port", "8791"], "cwd": str(AUREON_UPSTREAM),
        "mode": "continuous (read-only terminal status on port 8791)",
        "log": str(LOGS / "organ_unified_market_status.log"),
        "env": _launch_env(),
    },
    "market_stream_feeder": {
        "module": "aureon.data_feeds.ws_market_data_feeder",
        "match": "aureon.data_feeds.ws_market_data_feeder",
        "args": ["--out", str(AUREON_UPSTREAM / "ws_cache" / "ws_prices.json"),
                 "--kraken", "--write-interval-s", "1", "--kraken-interval-s", "30", "--quiet"],
        "cwd": str(AUREON_UPSTREAM),
        "mode": "continuous (public Binance websocket and Kraken market snapshots)",
        "log": str(LOGS / "organ_market_stream_feeder.log"),
        "env": _launch_env({
            "AUREON_STREAM_FEEDER_BATON": "0",
            "AUREON_STREAM_ENABLE_ALPACA": "0",
            "AUREON_STREAM_ENABLE_CAPITAL": "0",
            "AUREON_ALLOW_DUPLICATE_STREAM_FEEDER": "0",
            "AUREON_DISABLE_REAL_ORDERS": "1",
            "AUREON_DISABLE_EXCHANGE_MUTATIONS": "1",
            "AUREON_ORDER_INTENT_PUBLISH": "0",
            "AUREON_LIVE_TRADING": "0",
            "AUREON_UNIFIED_ORDER_EXECUTOR": "0",
            "PYTHONUTF8": "1",
        }),
    },
    "real_time_data_feeder": {
        "script": str(REALTIME_FEEDER),
        "args": [],
        "cwd": str(WORKSPACE),
        "mode": "continuous (60s cycle)",
        "log": str(LOGS / "organ_real_time_data_feeder.log"),
    },
    "schumann_real_daemon": {
        "script": str(SCHUMANN_DAEMON),
        "args": [],
        "cwd": str(WORKSPACE),
        "mode": "continuous (real-data sensor)",
        "log": str(LOGS / "organ_schumann_real_daemon.log"),
    },
    "planetary_monitor_daemon": {
        "script": str(PLANETARY_DAEMON),
        "args": [],
        "cwd": str(WORKSPACE),
        "mode": "continuous (poll loop)",
        "log": str(LOGS / "organ_planetary_monitor_daemon.log"),
    },
    "solar_system_collector": {
        "script": str(SOLAR_SYSTEM_COLLECTOR),
        "args": ["--interval", "300"],
        "cwd": str(WORKSPACE),
        "mode": "continuous (300s collection)",
        "log": str(LOGS / "organ_solar_system_collector.log"),
    },
    "sero_space_weather": {
        "script": str(SERO_SPACE_WEATHER),
        "args": ["--daemon"],
        "cwd": str(WORKSPACE),
        "mode": "continuous (NOAA/SWPC daemon loop)",
        "log": str(LOGS / "organ_sero_space_weather.log"),
    },
    "sero_autonomous_expansion": {
        "script": str(SERO_AUTONOMOUS_EXPANSION),
        "args": ["--continuous", "--interval", "300"],
        "cwd": str(WORKSPACE),
        "mode": "continuous",
        "log": str(LOGS / "organ_sero_autonomous_expansion.log"),
    },
    "aureon_radar_bridge": {
        "script": str(AUREON_RADAR / "aureon_bridge.py"),
        "args": [],
        "cwd": str(AUREON_RADAR),
        "mode": "signal/dry-run",
        "log": str(LOGS / "organ_aureon_radar_bridge.log"),
    },
    "aureon_radar_suite": {
        "script": str(RADAR_MASTER_LAUNCHER),
        "args": [],
        "cwd": str(WORKSPACE),
        "mode": "live trading (capital-gated)",
        "log": str(LOGS / "organ_aureon_radar_suite.log"),
        "requires_release": True,
    },
    # ── Activation wave (2026-09-04 second entry) ──────────────────────
    # mind_thought_action_hub depends on ThoughtBus being up (the original
    # fleet provides it); self_questioning_ai depends on Ollama and is the
    # single owner of the self-questioning loop. The two workspace daemons
    # are leaf organs — nothing downstream consumes them yet.
    "mind_thought_action_hub": {
        "module": MIND_HUB_MODULE,
        "match": "aureon_mind_thought_action_hub",
        "args": [],
        "cwd": str(WORKSPACE),
        "mode": "continuous (aiohttp dashboard :13002)",
        "log": str(LOGS / "organ_mind_thought_action_hub.log"),
        "env": _launch_env({
            "AUREON_MIND_HUB_PORT": "13002",  # env override hook; upstream
            # currently binds the default 13002, which the registrar probes
            "AUREON_SELF_QUESTIONING_AI": "0",  # embedded loop off — the
            # standalone self_questioning_ai organ owns that cycle
        }),
        "port": 13002,
    },
    "self_questioning_ai": {
        # Launched via the workspace-owned runner (aureon-os-upstream is
        # strictly read-only): the runner drives the upstream
        # SelfQuestioningAI engine with a REAL sleep between cycles and
        # per-cycle exception isolation. 600 s interval halves the benchmark-
        # flagged CPU cost of the per-cycle whole-repo scan.
        "script": str(WORKSPACE / "aureon_self_questioning_runner.py"),
        "args": ["--interval", "600"],
        "cwd": str(WORKSPACE),
        "mode": "continuous (600s questioning cycle)",
        "log": str(LOGS / "organ_self_questioning_ai.log"),
        "env": _launch_env(),
        "requires_ollama": True,
    },
    "hnc_core": {
        "module": "aureon_fusion.hnc_core",
        "match": "aureon_fusion.hnc_core",
        "args": ["run"],
        "cwd": str(WORKSPACE),
        "mode": "continuous (60s Master-Equation step)",
        "log": str(LOGS / "organ_hnc_core.log"),
        "env": _launch_env(),
    },
    "soul_protection_daemon": {
        "script": str(SOUL_PROTECTION_DAEMON),
        "args": [],
        "cwd": str(WORKSPACE),
        "mode": "continuous (5s protection cycle)",
        "log": str(LOGS / "organ_soul_protection_daemon.log"),
        "env": _launch_env(),
    },
    # ── NEURAL CANVAS (owner decree 2026-09-05: "we shall have a user
    # interface to watch her full neural pathways firing and moving") ─────
    # Read-only aiohttp visualization on :13012 — leaf organ, nothing
    # downstream consumes it. NO "port" key: the start-time port guard is
    # mind-hub-specific (hardcoded 13002 probe) and would false-block.
    "mind_neural_canvas": {
        "module": "aureon_fusion.neural_canvas",
        "match": "aureon_fusion.neural_canvas",
        "args": ["serve", "--port", "13012"],
        "cwd": str(WORKSPACE),
        "mode": "continuous (aiohttp neural canvas :13012)",
        "log": str(LOGS / "organ_mind_neural_canvas.log"),
        "env": _launch_env(),
    },
    # ── UNCAGING wave (REGISTRAR deliverable) ───────────────────────────
    # queen_mind is a leaf organ: nothing downstream consumes it yet. Its
    # spec resolves at import time (fused module preferred, workspace script
    # fallback, dormant-with-reason when the MIND peer has not delivered).
    "queen_mind": _queen_mind_spec(),
    # ── TRACK A (BUILDTIME wave): heartbeat scheduler organ — heals
    # sero_feel/ via the heartbeat's Schumann probe, refreshes
    # state/heartbeat_last_results.json every cycle (queen_mind reads it
    # live), and gives the two orphan one-shot tools (solar bridge merge,
    # real_data_feeds batch fetch) a scheduled home. Leaf organ.
    "heartbeat_daemon": {
        "module": "aureon_fusion.heartbeat_daemon",
        "match": "aureon_fusion.heartbeat_daemon",
        "args": [],
        "cwd": str(WORKSPACE),
        "mode": "continuous (300s HEARTBEAT cycle + solar merge + real-data feeds)",
        "log": str(LOGS / "organ_heartbeat_daemon.log"),
        "env": _launch_env(),
    },
    # ── UNITY SUPERVISOR wave (2026-09-07 build): SaaS-style persistent
    # supervisor plus the ten previously unsupervised loops and the
    # flight-recorder seat. Command lines mirror the live fleet so the
    # registry's matcher can adopt already-running instances.
    "grand_wheel": {
        "module": "aureon_fusion.grand_wheel",
        "match": "aureon_fusion.grand_wheel",
        "args": ["run_once", "--loop", "1000000"],
        "cwd": str(WORKSPACE),
        "mode": "continuous (60s happiness wheel)",
        "log": str(LOGS / "organ_grand_wheel.log"),
        "env": _launch_env(),
    },
    "knowledge_pulse_feeder": {
        "module": "aureon_fusion.knowledge_pulse_feeder",
        "match": "aureon_fusion.knowledge_pulse_feeder",
        "args": ["run", "--interval", "60"],
        "cwd": str(WORKSPACE),
        "mode": "continuous (60s knowledge pulse)",
        "log": str(LOGS / "organ_knowledge_pulse_feeder.log"),
        "env": _launch_env(),
    },
    "trading_progress_monitor": {
        "script": str(TRADING_PROGRESS_MONITOR),
        "args": [],
        "cwd": str(AUREON_RADAR),
        "mode": "continuous (30s trading progress)",
        "log": str(AUREON_RADAR / "logs" / "trading_progress_monitor.log"),
    },
    "_portfolio_writer_loop": {
        "script": str(PORTFOLIO_WRITER_LOOP),
        "args": [],
        "cwd": str(AUREON_RADAR),
        "mode": "continuous (60s portfolio truth writer)",
        "log": str(AUREON_RADAR / "logs" / "portfolio_writer_loop.log"),
        "env": _radar_env(),
    },
    "_temporal_refresh_loop": {
        "script": str(TEMPORAL_REFRESH_LOOP),
        "args": [],
        "cwd": str(AUREON_RADAR),
        "mode": "continuous (120s temporal refresh + prophecy resolution)",
        "log": str(AUREON_RADAR / "logs" / "temporal_refresh_loop.log"),
        "env": _radar_env(),
    },
    "_world_digest_loop": {
        "script": str(WORLD_DIGEST_LOOP),
        "args": [],
        "cwd": str(AUREON_RADAR),
        "mode": "continuous (600s world digest)",
        "log": str(AUREON_RADAR / "_world_digest_loop.log"),
        "env": _radar_env({"PYTHONUTF8": "1"}),
    },
    "_harmonic_seed_loop": {
        "script": str(HARMONIC_SEED_LOOP),
        "args": ["--daemon"],
        "cwd": str(AUREON_RADAR),
        "mode": "continuous (2400s harmonic seed)",
        "log": str(AUREON_RADAR / "harmonic_seed_loop.log"),
        "env": _radar_env({"PYTHONUTF8": "1"}),
    },
    "global_energy_aggregator": {
        "script": str(GLOBAL_ENERGY_AGGREGATOR),
        "args": ["--interval", "300"],
        "cwd": str(AUREON_RADAR),
        "mode": "continuous (300s global energy aggregator)",
        "log": str(AUREON_RADAR / "logs" / "global_energy_aggregator.log"),
        "env": _radar_env({"PYTHONUTF8": "1"}),
    },
    "orca_unified_kill_chain": {
        "script": str(ORCA_UNIFIED_KILL_CHAIN),
        "match": "orca_unified_kill_chain.py",
        "args": ["--auto"],
        "cwd": str(WORKSPACE),
        "mode": "continuous (30s orca kill chain)",
        "log": str(LOGS / "organ_orca_unified_kill_chain.log"),
        "env": _radar_env({"PYTHONUTF8": "1"}),
    },
    "orca_command_center": {
        "script": str(ORCA_COMMAND_CENTER),
        "match": "orca_command_center.py",
        "args": ["--port", "8888"],
        "cwd": str(AUREON_RADAR),
        "mode": "continuous (aiohttp orca dashboard :8888)",
        "log": str(AUREON_RADAR / "logs" / "orca_command_center.log"),
        "env": _radar_env({
            "PYTHONUTF8": "1",
            # Existing native provider reads continue; this dashboard has no
            # authority to publish order intents or mutate exchange accounts.
            "AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS": "0", "AUREON_AUDIT_MODE": "0",
            "AUREON_DISABLE_REAL_ORDERS": "1", "AUREON_DISABLE_EXCHANGE_MUTATIONS": "1",
            "AUREON_ORDER_INTENT_PUBLISH": "0", "AUREON_UNIFIED_ORDER_EXECUTOR": "0",
            "AUREON_LIVE_TRADING": "0",
        }),
    },
    "unity_supervisor": {
        "module": "aureon_fusion.unity_supervisor",
        "match": "aureon_fusion.unity_supervisor",
        "args": [],
        "cwd": str(WORKSPACE),
        "mode": "continuous (30-60s fleet supervision)",
        "log": str(LOGS / "organ_unity_supervisor.log"),
        "env": _launch_env(),
    },
    "flight_recorder": {
        "module": "aureon_fusion.flight_recorder",
        "match": "aureon_fusion.flight_recorder",
        "args": ["--daemon"],
        "cwd": str(WORKSPACE),
        "mode": "continuous (per-faculty flight recorder)",
        "log": str(LOGS / "organ_flight_recorder.log"),
        "env": _workspace_env(),
    },
    "bus_bridge": {
        "module": "aureon_fusion.bus_bridge",
        "match": "aureon_fusion.bus_bridge",
        "args": [],
        "cwd": str(WORKSPACE),
        "mode": "continuous (thought-bus unity bridge)",
        "log": str(LOGS / "organ_bus_bridge.log"),
        "env": _workspace_env(),
    },
    # ── Phase 6: read-only assessment / affect / HNC live producers ───────────
    # These upstream modules publish the runtime snapshots consumed by
    # aureon/saas/observed_runtime.py. They are launched with the four safety
    # holds in force; they read state and emit JSON, never exchange mutation.
    "assessment_snapshot_producer": {
        "module": "aureon.autonomous.aureon_assessment_snapshot_producer",
        "match": "aureon.autonomous.aureon_assessment_snapshot_producer",
        "args": ["--daemon", "--interval", "60", "--quiet"],
        "cwd": str(AUREON_UPSTREAM),
        "mode": "continuous (60s read-only assessment snapshots)",
        "log": str(LOGS / "organ_assessment_snapshot_producer.log"),
        "env": _launch_env({
            "AUREON_DISABLE_REAL_ORDERS": "1",
            "AUREON_DISABLE_EXCHANGE_MUTATIONS": "1",
            "AUREON_ORDER_INTENT_PUBLISH": "0",
            "AUREON_LIVE_TRADING": "0",
            "AUREON_UNIFIED_ORDER_EXECUTOR": "0",
            "PYTHONUTF8": "1",
        }),
    },
    "harmonic_affect_producer": {
        "module": "aureon.autonomous.aureon_harmonic_affect_state",
        "match": "aureon.autonomous.aureon_harmonic_affect_state",
        "args": ["--daemon", "--interval", "60", "--quiet"],
        "cwd": str(AUREON_UPSTREAM),
        "mode": "continuous (60s harmonic affect state)",
        "log": str(LOGS / "organ_harmonic_affect_producer.log"),
        "env": _launch_env({
            "AUREON_DISABLE_REAL_ORDERS": "1",
            "AUREON_DISABLE_EXCHANGE_MUTATIONS": "1",
            "AUREON_ORDER_INTENT_PUBLISH": "0",
            "AUREON_LIVE_TRADING": "0",
            "AUREON_UNIFIED_ORDER_EXECUTOR": "0",
            "PYTHONUTF8": "1",
        }),
    },
    "hnc_live_daemon": {
        "module": "aureon.core.hnc_live_daemon",
        "match": "aureon.core.hnc_live_daemon",
        "args": [],
        "cwd": str(AUREON_UPSTREAM),
        "mode": "continuous (HNC live Λ(t) field)",
        "log": str(LOGS / "organ_hnc_live_daemon.log"),
        "env": _launch_env({
            "AUREON_DISABLE_REAL_ORDERS": "1",
            "AUREON_DISABLE_EXCHANGE_MUTATIONS": "1",
            "AUREON_ORDER_INTENT_PUBLISH": "0",
            "AUREON_LIVE_TRADING": "0",
            "AUREON_UNIFIED_ORDER_EXECUTOR": "0",
            "PYTHONUTF8": "1",
        }),
    },
}

# On-demand tools that are NOT organs (note only — kept out of ORGANS on
# purpose): signal_lab (ws2) has no delivered module at registration time;
# it lands as a CLI tool entry in TOOLS.md when ws2 ships it.

# Explicit dependency order (same sequence as the table, kept as a list so
# the fleet verbs never depend on dict iteration happening to be right).
ORGAN_ORDER = list(ORGANS)


def _release_granted() -> bool:
    """True only when the orchestrator has pulled the capital pin."""
    if os.environ.get("AUREON_DEPLOYMENT_HOLD") == "1":
        return False
    return CAPITAL_RELEASE_FLAG.exists()


def _dormant_state(spec: dict, entry: dict):
    """Effective (dormant, reason) for an organ: the registry entry
    overrides the spec's initial default. Registered-but-not-started."""
    if "dormant" in entry:
        return bool(entry["dormant"]), (entry.get("dormant_reason") or "").strip()
    return bool(spec.get("dormant")), (spec.get("dormant_reason") or "").strip()


def _probe_hint(spec: dict) -> str:
    """Command-line fragment that identifies this organ's process: an
    explicit match hint (module launches), else the script path."""
    return spec.get("match") or spec["script"]


def _excluded_pids() -> set:
    """This process and its ancestors — a registry CLI must never match,
    adopt, or prune itself."""
    excluded = {os.getpid()}
    try:
        import psutil
        parent = psutil.Process(os.getpid()).ppid()
        while parent:
            excluded.add(parent)
            parent = psutil.Process(parent).ppid()
    except Exception:
        pass
    return excluded


def _process_creation_time(pid) -> float | None:
    """Native process creation time (epoch) for a PID, or None if unavailable.

    A recorded creation time lets downstream observers verify that a live PID
    still belongs to the process the registry launched, not a recycled PID.
    """
    if not pid:
        return None
    try:
        import psutil
        return float(psutil.Process(pid).create_time())
    except Exception:
        return None


def _match_pattern(spec: dict):
    """Regex for this organ's EXACT process identity on a command line.

    Module organs: the exact `-m <dotted.module>` token. The previous
    stem-based matcher was split by Path() — Path('aureon_fusion.hnc_core')
    .stem is 'aureon_fusion' — so hnc_core's matcher matched ANY
    `-m aureon_fusion.<x>` launch, including queen_mind's (benchmark
    finding: restarting hnc_core adopted queen's PID; prune then treated
    the real queen as a duplicate). Script organs: the exact script
    filename as a path/quote/space-delimited token.
    """
    import re
    module = spec.get("module")
    if module:
        return re.compile(rf"(?:^|[\s\"])-m[\s\"]+{re.escape(module)}(?:[\s\"]|$)")
    hint = _probe_hint(spec)
    if "." in hint and not hint.endswith(".py") \
            and "/" not in hint and "\\" not in hint:
        # bare dotted hint without a module key — same exact-token rule
        return re.compile(rf"(?:^|[\s\"])-m[\s\"]+{re.escape(hint)}(?:[\s\"]|$)")
    name = Path(hint).name
    return re.compile(rf"(?:^|[/\\\"\s]){re.escape(name)}(?:[/\\\"\s]|$)")


def _cmdline_matches(cmdline: str, spec: dict) -> bool:
    if not cmdline:
        return False
    return bool(_match_pattern(spec).search(cmdline))


def _iter_matching_pids(spec: dict):
    """All live PIDs whose command line matches an organ's EXACT process
    identity (excluding this process and its ancestors)."""
    try:
        import psutil
        excluded = _excluded_pids()
        found = []
        executables = {"python", "python.exe", "pythonw.exe", "python3", "node", "node.exe"}
        if spec.get("executable"):
            executables.add(Path(spec["executable"]).name.lower())
        for proc in psutil.process_iter(["name"]):
            if proc.pid in excluded:
                continue
            # Every registered organ uses Python or an explicit executable.
            # Reading command lines from unrelated Windows processes can block
            # recovery for minutes; their image name already excludes them.
            if str(proc.info.get("name") or "").lower() not in executables:
                continue
            try:
                cmdline = " ".join(proc.cmdline() or [])
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
            if _cmdline_matches(cmdline, spec):
                found.append(proc.pid)
        return found
    except Exception:
        return []


def _find_running_pid(spec: dict):
    """Find an already-running instance of an organ (started outside the
    registry) by matching its EXACT process identity. None if not found.

    Excludes the current process and its ancestors so a registry CLI invoked
    as `organ_registry start <organ>` never adopts itself.
    """
    pids = _iter_matching_pids(spec)
    return pids[0] if pids else None


def _kill_tree(pid, *, preserve_children: bool = False) -> bool:
    """Terminate a process AND its whole descendant tree (Windows children
    survive parent termination — e.g. master_launcher's unified_hub and
    phi_radar). Children first, newest-first; escalate to kill after a
    short grace. Returns True when nothing is left alive.
    """
    try:
        import psutil
        try:
            root = psutil.Process(pid)
        except psutil.NoSuchProcess:
            return True
        procs = [root]
        try:
            if not preserve_children:
                procs.extend(root.children(recursive=True))
        except Exception:
            pass
        # Newest first so children die before their parents can respawn them
        def _ctime(p):
            try:
                return p.create_time()
            except Exception:
                return 0.0
        procs.sort(key=_ctime, reverse=True)
        for p in procs:
            try:
                p.terminate()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        def _wait_remaining(candidates):
            try:
                return psutil.wait_procs(candidates, timeout=5)[1]
            except psutil.AccessDenied:
                # Windows can deny OpenProcess while a terminated process is
                # disappearing. Recheck liveness; permission failure itself is
                # never evidence that termination succeeded.
                remaining = []
                for candidate in candidates:
                    try:
                        if candidate.is_running():
                            remaining.append(candidate)
                    except psutil.NoSuchProcess:
                        pass
                    except psutil.AccessDenied:
                        remaining.append(candidate)
                return remaining
        alive = _wait_remaining(procs)
        for p in alive:
            try:
                p.kill()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        alive2 = _wait_remaining(alive)
        return not alive2
    except ImportError:
        return False


# ───────────────────────────── registry IO ─────────────────────────────────

# Inter-process advisory lock for registry read-modify-writes. Modelled on
# upstream aureon/core/aureon_lambda_engine.py (_acquire_advisory_lock):
# a sidecar .lock file with msvcrt.locking on Windows / flock elsewhere,
# non-blocking retries up to a deadline. Without this, two concurrent
# registry CLIs interleave load→modify→save and silently drop updates, and
# the fixed-name .tmp collides across processes (PermissionError-after-Popen
# orphaned the just-started organ's registry record).
_REGISTRY_LOCK_STATE = threading.local()


def _acquire_registry_lock(timeout_s: float = 10.0):
    """Acquire the advisory registry lock; returns the handle or None on
    conflict after timeout_s. Caller must release with _release."""
    lock_path = REGISTRY_FILE.with_name(REGISTRY_FILE.name + ".lock")
    deadline = time.monotonic() + timeout_s
    while True:
        handle = None
        try:
            handle = open(lock_path, "a+b")
            handle.seek(0, os.SEEK_END)
            if handle.tell() == 0:
                handle.write(b"\x00")
                handle.flush()
                os.fsync(handle.fileno())
            handle.seek(0)
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle.fileno(),
                            fcntl.LOCK_EX | fcntl.LOCK_NB)  # noqa: F821
            return handle
        except (ImportError, OSError):
            if handle is not None:
                try:
                    handle.close()
                except OSError:
                    pass
            if time.monotonic() >= deadline:
                return None
            time.sleep(0.05)


def _release_registry_lock(handle) -> None:
    try:
        handle.seek(0)
        if os.name == "nt":
            import msvcrt
            msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)  # noqa: F821
    except (ImportError, OSError):
        pass
    finally:
        try:
            handle.close()
        except OSError:
            pass


@contextlib.contextmanager
def _registry_lock(timeout_s: float = 10.0):
    """Hold the advisory lock across a registry read-modify-write. Yields
    True when the lock is held; on conflict yields False and the caller must
    NOT write. Re-entrant within one process (nested takes are no-ops)."""
    if getattr(_REGISTRY_LOCK_STATE, "handle", None) is not None:
        yield True
        return
    handle = _acquire_registry_lock(timeout_s)
    if handle is None:
        yield False
        return
    _REGISTRY_LOCK_STATE.handle = handle
    try:
        yield True
    finally:
        _REGISTRY_LOCK_STATE.handle = None
        _release_registry_lock(handle)


def _read_registry_file() -> dict:
    """Raw registry read (no lock — os.replace makes reads atomic)."""
    reg = {}
    try:
        if REGISTRY_FILE.exists():
            with open(REGISTRY_FILE, "r", encoding="utf-8") as f:
                reg = json.load(f)
    except Exception:
        reg = {}
    if not isinstance(reg, dict):
        reg = {}
    reg.setdefault("organs", {})
    return reg


def _load_registry() -> dict:
    """Load the registry, auto-reconciling stale PIDs and adopting
    externally-started instances of supervised organs. The reconcile+save
    runs under the advisory lock so two registry processes cannot interleave
    a read-modify-write."""
    with _registry_lock() as held:
        reg = _read_registry_file()
        if not held:
            # The atomic snapshot is readable while another writer owns the
            # lock. Do not turn a failed read lock into a fleet scan or a
            # second write attempt that blocks an unrelated recovery command.
            for name, spec in ORGANS.items():
                reg["organs"].setdefault(name, {}).setdefault("mode", spec["mode"])
            return reg
        changed = False
        for name, spec in ORGANS.items():
            entry = reg["organs"].get(name, {})
            pid = entry.get("pid")
            if pid and not _pid_alive(pid, spec):
                events.publish_event("organ_registry", "organ.dead",
                                     {"organ": name, "pid": pid,
                                      "reason": "recorded pid no longer alive"},
                                     priority=9)
                events.chirp("organ_registry", "organ_dead", 8,
                             {"organ": name, "pid": pid})
                entry["pid"] = None
                entry["stale_reconciled_at"] = int(time.time())
                changed = True
            dormant, _reason = _dormant_state(spec, entry)
            if not entry.get("pid") and not dormant:
                found = _find_running_pid(spec)
                if found:
                    entry["pid"] = found
                    entry["adopted_external_at"] = int(time.time())
                    entry["process_created_at"] = _process_creation_time(found)
                    changed = True
            entry.setdefault("mode", spec["mode"])
            reg["organs"][name] = entry
        if changed or not REGISTRY_FILE.exists():
            _save_registry(reg)
        return reg


def _replace_with_retry(src: Path, dest: Path,
                        attempts: int = 20, delay_s: float = 0.05) -> None:
    """os.replace with retry: on Windows a just-replaced destination can be
    held briefly by an antivirus/reader handle, surfacing as a transient
    PermissionError. Raises the last OSError when all attempts fail."""
    last = None
    for i in range(attempts):
        try:
            os.replace(src, dest)
            return
        except OSError as exc:
            last = exc
            if i < attempts - 1:
                time.sleep(delay_s)
    raise last


def _save_registry(reg: dict) -> bool:
    """Locked, atomic registry write: per-pid unique tmp file + os.replace,
    all under the advisory lock. Returns False — and writes NOTHING — when
    the lock cannot be acquired: a refused write is always preferable to a
    lost update or a mid-verb PermissionError orphaning a started organ."""
    FUSION_STATE.mkdir(parents=True, exist_ok=True)
    handle = None
    if getattr(_REGISTRY_LOCK_STATE, "handle", None) is None:
        handle = _acquire_registry_lock()
        if handle is None:
            return False
    tmp = REGISTRY_FILE.with_name(
        f"{REGISTRY_FILE.name}.tmp.{os.getpid()}.{time.time_ns()}")
    ok = False
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(reg, f, indent=2, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
        _replace_with_retry(tmp, REGISTRY_FILE)
        ok = True
    except OSError:
        ok = False
    finally:
        try:
            tmp.unlink()
        except OSError:
            pass
        if handle is not None:
            _release_registry_lock(handle)
    if ok:
        _sweep_stale_registry_tmp()
    return ok


def _sweep_stale_registry_tmp():
    """Best-effort removal of orphaned registry tmp files from crashed
    writers. Only files older than 1h are touched — a younger file may
    belong to a writer still working."""
    try:
        now = time.time()
        for stale in FUSION_STATE.glob(f"{REGISTRY_FILE.name}.tmp.*"):
            try:
                if now - stale.stat().st_mtime > 3600:
                    stale.unlink()
            except OSError:
                pass
    except Exception:
        pass


# ───────────────────────────── liveness ────────────────────────────────────

def _pid_alive(pid, spec: dict = None) -> bool:
    """True if pid is a live process (and, when possible, matches the
    organ's EXACT process identity — a recycled PID owned by a sibling
    module like queen_mind must NOT pass hnc_core's probe)."""
    if not pid:
        return False
    try:
        import psutil
        if not psutil.pid_exists(pid):
            return False
        if spec:
            try:
                proc = psutil.Process(pid)
                cmdline = " ".join(proc.cmdline())
                if not _cmdline_matches(cmdline, spec):
                    return False  # PID recycled by an unrelated process
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                return True  # alive but not inspectable — trust pid_exists
        return True
    except ImportError:
        pass
    # tasklist fallback — exact PID-column match only. A substring test
    # false-positives when the /FI filter is lost (locale drift, tasklist
    # quirks): probing PID 123 must not match PID 1234 in the output.
    try:
        out = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"],
            capture_output=True, text=True, timeout=15,
            encoding="utf-8", errors="replace",
        )
        for row in csv.reader(io.StringIO(out.stdout or "")):
            if len(row) >= 2 and row[1].strip() == str(pid):
                return True
        return False
    except Exception:
        return False


# ───────────────────────────── verbs ───────────────────────────────────────

# Organ logs are written via stdout redirection (subprocess stdout → file),
# not a logging FileHandler, so nothing rotates them while they grow. Cap
# them at start time using the fleet's timestamped-.bak convention
# (cf. aureon_radar/radar.log.20260903_224610.bak). Fail-closed: any
# failure (e.g. the file still held open by a dying child on Windows)
# leaves the log in place and never blocks the organ start.
_LOG_ROTATE_MAX_BYTES = 20 * 1024 * 1024
_LOG_ROTATE_KEEP = 5


def _rotate_log_if_oversized(log_path: Path) -> None:
    try:
        if not log_path.exists() \
                or log_path.stat().st_size < _LOG_ROTATE_MAX_BYTES:
            return
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        os.replace(log_path,
                   log_path.with_name(f"{log_path.name}.{stamp}.bak"))
        backups = sorted(log_path.parent.glob(f"{log_path.name}.*.bak"))
        for stale in backups[:-_LOG_ROTATE_KEEP]:
            try:
                stale.unlink()
            except OSError:
                pass  # a held-open backup is skipped, never fatal
    except OSError:
        pass  # locked or vanished log: append to it as-is


def start(organ: str) -> dict:
    """Serialize liveness check, spawn and PID publication as one operation.

    A supervisor and a manual start must not both pass the duplicate guard
    before either has published its PID. A lock conflict never starts a child.
    """
    if organ not in ORGANS:
        return {"ok": False, "error": f"unknown organ '{organ}': {sorted(ORGANS)}"}
    with _registry_lock() as held:
        if not held:
            return {"ok": False, "organ": organ, "state": "registry_busy",
                    "reason": "registry is busy; no process was started"}
        return _start_locked(organ)


def _start_locked(organ: str) -> dict:
    """Start implementation; caller holds the re-entrant registry lock."""
    spec = ORGANS.get(organ)
    if not spec:
        return {"ok": False, "error": f"unknown organ '{organ}': {sorted(ORGANS)}"}
    reg = _load_registry()
    entry = reg["organs"][organ]
    dormant, reason = _dormant_state(spec, entry)
    if dormant:
        return {"ok": True, "organ": organ, "state": "dormant",
                "reason": reason or "organ marked dormant — "
                          f"use 'undormant {organ}' to clear, then start"}
    if spec.get("requires_release") and not _release_granted():
        # Pinned HOLD: no spawn, no adoption, no flag creation — the
        # orchestrator pulls this pin after the audit.
        return {"ok": True, "organ": organ, "state": "held",
                "reason": f"{CAPITAL_RELEASE_FLAG.name} absent — "
                          f"live trading pinned HOLD by orchestrator"}
    if spec.get("requires_ollama") and not ollama_available():
        return {"ok": False, "organ": organ, "state": "blocked",
                "reason": f"no Ollama answering {OLLAMA_PROBE_URL} — "
                          f"{organ} needs the loopback model plane"}
    if spec.get("port") and not mind_hub_port_available():
        return {"ok": False, "organ": organ, "state": "blocked",
                "reason": f"port {spec['port']} already bound — refusing to "
                          f"start a duplicate mind hub"}
    if entry.get("pid") and _pid_alive(entry["pid"], spec):
        return {"ok": True, "organ": organ, "pid": entry["pid"], "state": "already_running"}

    # Duplicate guard: if this script is already running ANYWHERE outside
    # the registry, refuse instead of spawning a second instance (on a live
    # trading system a duplicate phi-radar could double-fire orders).
    external = _find_running_pid(spec)
    if external:
        return {"ok": False, "organ": organ, "pid": external,
                "state": "already_running",
                "reason": f"{Path(_probe_hint(spec)).name} already running as "
                          f"pid {external} outside the registry — refusing "
                          f"duplicate start (use 'prune' to clean extras)"}

    log_path = Path(spec["log"])
    log_path.parent.mkdir(parents=True, exist_ok=True)
    _rotate_log_if_oversized(log_path)
    flags = 0
    if sys.platform == "win32":
        flags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        flags |= getattr(subprocess, "CREATE_NO_WINDOW", 0)
    if spec.get("executable"):
        cmd = [spec["executable"], spec["script"], *spec["args"]]
    elif spec.get("module"):
        cmd = [sys.executable, "-u", "-m", spec["module"], *spec["args"]]
    else:
        cmd = [sys.executable, "-u", spec["script"], *spec["args"]]
    env = spec.get("env")
    if organ in {"operator_gateway", "frontend_vite"}:
        # Load only the installed account-protected HTTP profile, at spawn time.
        # Keep credentials out of the registry, command line and event receipts.
        import importlib.util

        profile_path = AUREON_UPSTREAM / "aureon" / "operator" / "local_http_profile.py"
        required_profile = spec.get("requires_local_http_profile") is True
        if required_profile and not profile_path.is_file():
            return {"ok": False, "organ": organ, "state": "blocked",
                    "reason": "commissioned HTTP credential loader missing"}
        if profile_path.is_file():
            module_spec = importlib.util.spec_from_file_location("aureon_local_http_profile", profile_path)
            profile_module = importlib.util.module_from_spec(module_spec)
            module_spec.loader.exec_module(profile_module)
            env = profile_module.service_environment(organ, dict(env or os.environ), required=required_profile)
    with open(log_path, "a", encoding="utf-8", errors="replace") as logf:
        proc = subprocess.Popen(
            cmd, cwd=spec["cwd"],
            stdout=logf, stderr=subprocess.STDOUT,
            creationflags=flags, env=env,
        )
    update = {
        "pid": proc.pid,
        "started_at": int(time.time()),
        "started_at_iso": datetime.now(timezone.utc).isoformat(),
        "process_created_at": _process_creation_time(proc.pid),
        "cmd": cmd,
        "mode": spec["mode"],
        "log": spec["log"],
    }
    # Locked RMW: reload the registry under the advisory lock so a
    # concurrent registry process cannot lose its update to our write.
    with _registry_lock() as held:
        if held:
            reg = _load_registry()
            entry = reg["organs"][organ]
        entry.update(update)
        saved = _save_registry(reg)
    if not saved:
        return {"ok": False, "organ": organ, "pid": proc.pid,
                "state": "registry_write_failed",
                "reason": "registry lock conflict — process started (see its "
                          "log) but the registry could not record it; rerun "
                          "'status' to adopt it"}
    events.publish_event("organ_registry", "organ.started",
                         {"organ": organ, "pid": proc.pid, "mode": spec["mode"]},
                         priority=6)
    return {"ok": True, "organ": organ, "pid": proc.pid, "state": "started",
            "mode": spec["mode"], "log": spec["log"]}


def stop(organ: str, timeout: int = 8) -> dict:
    spec = ORGANS.get(organ)
    if not spec:
        return {"ok": False, "error": f"unknown organ '{organ}': {sorted(ORGANS)}"}
    reg = _load_registry()
    entry = reg["organs"][organ]
    pid = entry.get("pid")
    if not pid or not _pid_alive(pid, spec):
        with _registry_lock():
            reg = _load_registry()
            reg["organs"][organ]["pid"] = None
            _save_registry(reg)
        return {"ok": True, "organ": organ, "state": "not_running"}

    # The supervisor's descendants are independent registered services. Reload
    # its policy without terminating the runtime it supervises.
    stopped = _kill_tree(pid, preserve_children=organ == "unity_supervisor")

    if not stopped:
        stopped = _taskkill(pid, preserve_children=organ == "unity_supervisor")

    if not stopped:
        # Preserve the recorded owner when Windows denied termination. Clearing
        # it and calling start would merely adopt the old process and falsely
        # report a completed restart with stale launch configuration.
        return {"ok": False, "organ": organ, "state": "stop_failed", "pid": pid,
                "reason": "registered process could not be stopped; existing owner preserved"}

    if stopped:
        # Audit trail: the kill lands in the intrusion ledger
        # (commitments only, never raw detail). Never raises.
        try:
            from . import receipts
            receipts.log_intrusion({
                "event": "organ_registry.stop",
                "reason": "registry-supervised stop",
                "detail": {"organ": organ, "pid": pid},
            })
        except Exception:
            pass

    with _registry_lock():
        reg = _load_registry()
        fresh = reg["organs"][organ]
        fresh["pid"] = None
        fresh["stopped_at"] = int(time.time())
        _save_registry(reg)
    events.publish_event("organ_registry", "organ.stopped",
                         {"organ": organ, "pid": pid,
                          "state": "stopped" if stopped else "stop_failed"},
                         priority=6)
    return {"ok": True, "organ": organ, "state": "stopped" if stopped else "stop_failed",
            "pid": pid}


def _taskkill(pid, *, preserve_children: bool = False) -> bool:
    try:
        subprocess.run(
            ["taskkill", "/PID", str(pid), *([] if preserve_children else ["/T"]), "/F"],
            capture_output=True, timeout=15,
        )
        return not _pid_alive(pid)
    except Exception:
        return False


def restart(organ: str) -> dict:
    stopped = stop(organ)
    if not stopped.get("ok"):
        return stopped
    return start(organ)


def dormant(organ: str, reason: str = "") -> dict:
    """Mark an organ registered-but-not-started. If it is running it is
    stopped first (registry-owned restart doctrine), then the dormant flag
    and reason are recorded; start() refuses while dormant, status shows
    the reason. The opposite verb is undormant().
    """
    spec = ORGANS.get(organ)
    if not spec:
        return {"ok": False, "error": f"unknown organ '{organ}': {sorted(ORGANS)}"}
    reg = _load_registry()
    entry = reg["organs"][organ]
    result = {"ok": True, "organ": organ, "state": "dormant"}
    pid = entry.get("pid")
    if pid and _pid_alive(pid, spec):
        stopped = stop(organ)
        result["stopped_pid"] = pid
        result["stop_state"] = stopped.get("state")
        reg = _load_registry()
        entry = reg["organs"][organ]
    entry["dormant"] = True
    entry["dormant_reason"] = reason.strip() or "no reason given"
    entry["dormant_at"] = int(time.time())
    with _registry_lock():
        reg = _load_registry()
        fresh = reg["organs"][organ]
        fresh["dormant"] = True
        fresh["dormant_reason"] = entry["dormant_reason"]
        fresh["dormant_at"] = entry["dormant_at"]
        _save_registry(reg)
    events.publish_event("organ_registry", "organ.dormant",
                         {"organ": organ, "reason": entry["dormant_reason"]},
                         priority=6)
    result["reason"] = entry["dormant_reason"]
    return result


def undormant(organ: str) -> dict:
    """Clear the dormant mark so start() is allowed again. Does not start
    the organ — that remains an explicit decision."""
    spec = ORGANS.get(organ)
    if not spec:
        return {"ok": False, "error": f"unknown organ '{organ}': {sorted(ORGANS)}"}
    reg = _load_registry()
    entry = reg["organs"][organ]
    was = bool(entry.get("dormant"))
    with _registry_lock():
        reg = _load_registry()
        fresh = reg["organs"][organ]
        fresh["dormant"] = False
        fresh["undormanted_at"] = int(time.time())
        if not fresh.get("dormant_reason"):
            fresh["dormant_reason"] = ""
        _save_registry(reg)
    if was:
        events.publish_event("organ_registry", "organ.undormant",
                             {"organ": organ}, priority=6)
    return {"ok": True, "organ": organ, "state": "undormant",
            "was_dormant": was,
            "note": f"organ not started — run 'start {organ}' when ready"}


def prune() -> dict:
    """Scan for duplicate/orphan instances of registered organ scripts and
    kill every match that is not the registry-recorded (live) PID. Returns a
    per-organ report; 'killed' lists removed PIDs, 'failures' lists PIDs
    that survived. Safe with the live fleet: the recorded instance of each
    organ is always left running.
    """
    reg = _load_registry()
    report = {}
    for name, spec in ORGANS.items():
        recorded = reg["organs"].get(name, {}).get("pid")
        recorded_alive = bool(recorded) and _pid_alive(recorded, spec)
        keep = recorded if recorded_alive else None
        killed, failures, skipped = [], [], []
        for pid in _iter_matching_pids(spec):
            if keep and pid == keep:
                continue
            if recorded and not recorded_alive:
                # The registry-recorded pid failed the alive/identity probe
                # but we cannot positively prove WHICH process is the real
                # organ. Killing here is the benchmark's kept=null hazard —
                # a genuine organ dies (the hnc_core matcher once adopted
                # queen_mind's pid, and prune would have killed the real
                # queen). Ambiguous → report and skip, never kill.
                skipped.append(pid)
                continue
            # Supervised services remain independent when a duplicate
            # supervisor is removed, just as when its policy is restarted.
            if _kill_tree(pid, preserve_children=name == "unity_supervisor"):
                killed.append(pid)
            else:
                failures.append(pid)
        report[name] = {"kept": keep, "killed": killed, "failures": failures,
                        "skipped": skipped}
        if skipped:
            events.publish_event(
                "organ_registry", "organ.prune_skipped",
                {"organ": name, "recorded": recorded, "skipped": skipped},
                priority=6)
        if killed or failures:
            events.publish_event(
                "organ_registry", "organ.pruned",
                {"organ": name, "kept": keep, "killed": killed,
                 "failures": failures}, priority=6)
            # Audit trail: prune kills land in the intrusion ledger
            # (commitments only, never raw detail). Never raises.
            try:
                from . import receipts
                receipts.log_intrusion({
                    "event": ("organ_registry.prune_failure" if failures
                              else "organ_registry.prune"),
                    "reason": "registry prune removed duplicate/orphan instances",
                    "detail": {"organ": name, "killed": killed,
                               "failures": failures, "kept": keep},
                })
            except Exception:
                pass
    return report


def start_all() -> dict:
    """Start every registered organ in dependency order (feeders first,
    radar last). Capital-gated organs report 'held' without spawning."""
    results = {}
    for name in ORGAN_ORDER:
        results[name] = start(name)
    return results


def stop_all() -> dict:
    """Stop every registered organ in reverse dependency order (radar
    first, feeders last) so consumers tear down before their sources."""
    results = {}
    for name in reversed(ORGAN_ORDER):
        results[name] = stop(name)
    return results


def _cwd_matches(spec: dict, process) -> bool:
    """True when the process cwd matches the organ's configured cwd."""
    expected = spec.get("cwd")
    if not expected:
        return True
    try:
        actual = process.cwd()
    except Exception:
        return False
    return Path(actual).resolve() == Path(expected).resolve()


def write_observed_process_identity() -> dict:
    """Verify every registered PID and write an identity receipt.

    The receipt follows the schema expected by
    aureon.saas.observed_runtime.py (_project kind="process_identity"):
    {schema: "aureon.process_identity.v1", generated_at, organs: {name: {
        pid, process_created_at, process_name, spec_match, cwd_match,
        verified_at}}}.

    This is cheap enough to run inside the unity_supervisor cycle; it only
    probes PIDs already recorded in the registry.
    """
    reg = _load_registry()
    now = time.time()
    rows = {}
    try:
        import psutil
        native = psutil.Process
    except Exception:
        native = None
    for name, spec in ORGANS.items():
        entry = reg["organs"].get(name, {})
        pid = entry.get("pid")
        if not pid:
            continue
        row = {"pid": pid}
        if native is None:
            row["reason"] = "native_process_reader_missing"
        else:
            try:
                proc = native(pid)
                if not proc.is_running():
                    continue
                cmdline = " ".join(proc.cmdline() or [])
                row.update({
                    "process_created_at": float(proc.create_time()),
                    "process_name": str(proc.name()).lower(),
                    "spec_match": _cmdline_matches(cmdline, spec),
                    "cwd_match": _cwd_matches(spec, proc),
                    "verified_at": now,
                })
            except Exception:
                continue
        rows[name] = row
    payload = {
        "schema": "aureon.process_identity.v1",
        "generated_at": now,
        "organs": rows,
    }
    FUSION_STATE.mkdir(parents=True, exist_ok=True)
    tmp = OBSERVED_IDENTITY_FILE.with_name(
        f"{OBSERVED_IDENTITY_FILE.name}.tmp.{os.getpid()}.{time.time_ns()}")
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
        _replace_with_retry(tmp, OBSERVED_IDENTITY_FILE)
    except OSError:
        try:
            tmp.unlink()
        except OSError:
            pass
        raise
    return payload


def status_data() -> dict:
    """Liveness snapshot for every supervised organ."""

    reg = _load_registry()
    out = {}
    stale = []
    for name, spec in ORGANS.items():
        entry = reg["organs"].get(name, {})
        pid = entry.get("pid")
        alive = bool(pid) and _pid_alive(pid, spec)
        if pid and not alive:
            stale.append(name)
        dormant, reason = _dormant_state(spec, entry)
        out[name] = {
            "state": "running" if alive else ("dormant" if dormant else "stopped"),
            "pid": pid if alive else None,
            "mode": spec["mode"],
            "started_at": entry.get("started_at_iso"),
            "log": spec["log"],
            "script": spec.get("script") or f"-m {spec.get('module', '(not delivered)')}",
        }
        if dormant:
            out[name]["dormant_reason"] = reason
            out[name]["dormant_since"] = entry.get("dormant_at")
        if spec.get("requires_release"):
            out[name]["gate"] = CAPITAL_RELEASE_FLAG.name
            out[name]["gate_state"] = "released" if _release_granted() else "pinned_HOLD"
        if spec.get("requires_ollama"):
            out[name]["ollama"] = "live" if ollama_available() else "unreachable"
        if spec.get("port"):
            out[name]["port"] = spec["port"]
            out[name]["port_state"] = "free" if mind_hub_port_available() else "bound"
    if stale:
        # One locked RMW for every stale entry found during the scan.
        with _registry_lock():
            reg = _load_registry()
            for name in stale:
                entry = reg["organs"].get(name, {})
                entry["pid"] = None
                entry["stale_reconciled_at"] = int(time.time())
            _save_registry(reg)
    return out


def status_text() -> str:
    data = status_data()
    lines = ["═" * 76, "🫀 ORGAN REGISTRY", "═" * 76]
    for name, info in data.items():
        gated = "gate" in info
        if info["state"] == "running":
            icon = "🟢"
        elif gated and info.get("gate_state") == "pinned_HOLD":
            icon = "🔒"
        else:
            icon = "⚪"
        lines.append(f"  {icon} {name:<26} {info['state']:<8} "
                     f"pid={info['pid'] or '-':<8} mode={info['mode']}")
        lines.append(f"      log: {info['log']}")
        if info["state"] == "dormant":
            lines.append(f"      dormant: {info.get('dormant_reason') or 'no reason recorded'} "
                         f"(start refused — 'undormant {name}' to clear)")
        if gated:
            lines.append(f"      gate: {info['gate']} = {info['gate_state']} "
                         f"(start refused until orchestrator releases capital)")
        if info.get("ollama"):
            lines.append(f"      ollama: {info['ollama']}")
        if info.get("port"):
            lines.append(f"      port {info['port']}: {info['port_state']}")
    lines.append("═" * 76)
    return "\n".join(lines)


def selftest() -> dict:
    """Regression checks for the process-identity matcher.

    Captures the benchmark failure: hnc_core's old stem-split hint
    ('aureon_fusion') matched ANY `-m aureon_fusion.<x>` cmdline, so
    restarting hnc_core while queen_mind ran adopted queen's PID, and
    prune treated the genuine queen as a duplicate.
    """
    hnc = ORGANS["hnc_core"]
    queen = ORGANS["queen_mind"]
    hnc_cmd = "python -u -m aureon_fusion.hnc_core run"
    queen_cmd = "python -u -m aureon_fusion.queen_mind --interval 120"
    checks = [
        ("hnc matcher accepts hnc_core cmdline",
         _cmdline_matches(hnc_cmd, hnc)),
        ("hnc matcher REJECTS queen_mind cmdline (benchmark regression)",
         not _cmdline_matches(queen_cmd, hnc)),
        ("queen matcher accepts queen_mind cmdline",
         _cmdline_matches(queen_cmd, queen)),
        ("queen matcher REJECTS hnc_core cmdline",
         not _cmdline_matches(hnc_cmd, queen)),
        ("hnc matcher rejects sibling prefix '-m aureon_fusion.hnc_core_v2'",
         not _cmdline_matches("python -m aureon_fusion.hnc_core_v2 run", hnc)),
    ]
    results = [{"check": name, "pass": ok} for name, ok in checks]
    return {"ok": all(ok for _, ok in checks), "checks": results,
            "prune_rule": "never kill when the recorded pid fails the "
                          "alive/identity probe without a positively-"
                          "identified duplicate — ambiguous → skip"}


def main(argv=None):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in ("-h", "--help", "help"):
        print("usage: python -m aureon_fusion.organ_registry "
              "[status | start <organ>|--all | stop <organ>|--all | "
              "restart <organ> | dormant <organ> <reason> | "
              "undormant <organ> | prune | selftest]")
        print(f"organs: {', '.join(ORGANS)}")
        print("identity rule: module organs match the exact `-m <module>` "
              "token (Path-stem hints once let hnc_core match queen_mind); "
              "prune never kills when the recorded pid fails the "
              "alive/identity probe without a positively-identified "
              "duplicate — ambiguous means skip, not kill.")
        return 0
    verb = argv[0]
    if verb == "selftest":
        result = selftest()
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0 if result.get("ok") else 1
    if verb == "status":
        print(status_text())
        return 0
    if verb == "prune":
        report = prune()
        print(json.dumps(report, indent=2, ensure_ascii=False))
        failures = {n: r["failures"] for n, r in report.items() if r["failures"]}
        return 1 if failures else 0
    if verb in ("dormant", "undormant"):
        if len(argv) < 2:
            print(f"usage: {verb} <organ>  (organs: {', '.join(ORGANS)})",
                  file=sys.stderr)
            return 2
        result = dormant(argv[1], " ".join(argv[2:])) if verb == "dormant" \
            else undormant(argv[1])
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0 if result.get("ok") else 2
    if verb in ("start", "stop", "restart"):
        if len(argv) < 2:
            print(f"usage: {verb} <organ>|--all  (organs: {', '.join(ORGANS)})",
                  file=sys.stderr)
            return 2
        if argv[1] == "--all":
            if verb == "restart":
                print("restart --all is not supported; use stop --all then start --all",
                      file=sys.stderr)
                return 2
            results = start_all() if verb == "start" else stop_all()
            print(json.dumps(results, indent=2, ensure_ascii=False))
            ok_states = ("started", "already_running", "stopped", "not_running",
                         "held", "dormant")
            bad = {n: r for n, r in results.items()
                   if not r.get("ok") or r.get("state") not in ok_states}
            if bad:
                print(f"fleet {verb} incomplete: {sorted(bad)}", file=sys.stderr)
                return 1
            return 0
        result = globals()[verb](argv[1])
        state = result.get("state")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        if state in ("started", "already_running", "stopped", "held", "dormant"):
            return 0
        return 1 if result.get("ok") else 2
    print(f"unknown verb: {verb}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())

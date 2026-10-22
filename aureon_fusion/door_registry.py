"""🚪 DOOR REGISTRY — the sovereign door census of the Aureon Fusion organism.

Owner decree (absolute):
  • We do NOT take away any system's autonomy — we show the organism the
    doors; IT generates its own master key to open them when it wants and
    closes them when it wants.
  • Locked doors (owner-review, reconstruction-required) are SHOWN honestly,
    never silently openable.
  • This module is a STATIC TABLE + honest state persistence. It gates
    nothing and activates nothing — the forge (master_key.py) owns gating,
    door_activators.py owns mechanics. The single live read: the pc_control
    decree lock class displays unlocked once state/pc_control_ack.json
    records her first_use (fail-closed without it).

Every door dict carries the fixed contract fields:
    name, title, module, autonomy_class,
    mode (INPROC | subprocess-oneshot | subprocess-longrun),
    elevate (bool), locked_reason (None | str), description
plus operational fields used by the master key and the activators:
    domain_action, command, cwd, value (census value rank 0..1),
    registry_organ (explicit organ_registry adoption seat, else None).

DoorState persists per-door {state, key_id, opened_at, closes_at,
open_count} (+ provenance/pid for long-run process discipline) at
aureon_fusion/state/doors/state.json — tmp+replace writes only.

Import-safe: nothing is instantiated at import; suppression env vars are
honored via setdefault.

CLI:
    python -m aureon_fusion.door_registry list
    python -m aureon_fusion.door_registry get <door>
"""

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from .paths import FUSION_STATE, WORKSPACE
from .upstream_census_doors import UPSTREAM_CENSUS_DOORS

os.environ.setdefault("AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS", "1")
os.environ.setdefault("AUREON_AUDIT_MODE", "1")

# ───────────────────────── doctrine constants ──────────────────────────────

DOORS_DIR = FUSION_STATE / "doors"
DOORS_STATE_FILE = DOORS_DIR / "state.json"
DOORS_PID_DIR = DOORS_DIR / "pids"
DOORS_LOG_DIR = DOORS_DIR / "logs"
BUILD_LOG = FUSION_STATE / "build_doors_core.log"

# Child-launch environment: suppression env vars PINNED (not defaulted) for
# anything the door system spawns — same discipline as organ_registry.
SUPPRESSION_ENV = {
    "AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS": "1",
    "AUREON_AUDIT_MODE": "1",
}

_PY = sys.executable or "python"


def _cmd(script: str, *args) -> list:
    return [_PY, "-u", str(WORKSPACE / script), *args]


# ───────────────────────── the census table ────────────────────────────────
# Source: state/door_census.md (2026-09-05). value = census rank mapped to
# 1.00 … 0.45 (rank 1 → 1.00, step 0.05). domain_action per owner decree:
# knowledge doors → network_access:fetch_public_data; everything else → the
# default system:activate_internal_door (the matrix is never extended here).
# Expansion 2026-09-05 (SCOPE D): three knowledge doors added
# (open_search_communion, knowledge_pulse_feed, deep_research_communion),
# values 0.90 / 0.85 / 0.80, slotted into the existing value-descending order.

# EXPANSION 2026-09-05 (CODING ESTATE, owner decree): "give her full control
# of her coding systems" — three coding doors added (code_architect 0.68,
# safe_code_control 0.62, capability_forge 0.58), slotted into the existing
# value-descending order. domain_action values are EXISTING capability-matrix
# rows owner-activated to 'approved' the same day (never extended here);
# every write/create still passes the master_key gate trio at mint time.

DOORS: list = [
    {
        "name": "sero_consciousness_loop",
        "title": "Sero Consciousness Loop",
        "module": "sero_master_orchestrator.py",
        "autonomy_class": "ACT",
        "mode": "subprocess-oneshot",
        "elevate": False,
        "locked_reason": None,
        "description": ("Full being: perceive→decide→act→reflect, "
                        "conscience-routed; re-warms mycelium feed, chirp, "
                        "sero_orchestrator/ + sero_mind/ state."),
        "domain_action": "system:activate_internal_door",
        "command": _cmd("sero_master_orchestrator.py"),
        "cwd": str(WORKSPACE),
        "value": 1.00,
        "registry_organ": None,
    },
    {
        "name": "planetary_switchboard",
        "title": "Planetary Switchboard",
        "module": "aureon_radar/planetary_switchboard.py",
        "autonomy_class": "OBSERVE",
        "mode": "subprocess-longrun",
        "elevate": False,
        "locked_reason": None,
        "description": ("Live NOAA/Schumann/DONKI → planetary_signals.jsonl, "
                        "consumed by the running phi-radar."),
        "domain_action": "network_access:fetch_public_data",
        "command": _cmd("aureon_radar/planetary_switchboard.py"),
        "cwd": str(WORKSPACE),
        "value": 0.95,
        "registry_organ": None,  # census: no registry organ owns this module
    },
    {
        # OWNER DECREE 2026-09-05 ("let her run fully autonomously with full
        # access to the pc — let's watch what she does") + GAP 5 elevation
        # decree 2026-09-06 (build night, Tier 4 owner-decree territory):
        # the governed operator toolbelt (write/execute), acquired
        # in-process. ELEVATE — open() additionally conscience-double-
        # checked by master_key and journaled with a receipt.
        # LOCK CLASS "owner-decree-received-pending-first-use": shown
        # locked in the census until her first sovereign open (first_use in
        # state/pc_control_ack.json) — then the census shows it unlocked.
        # The forge lifts EXACTLY this class, and only via the recorded
        # owner decree (fail-closed without it); the gate trio then still
        # applies in full at mint/open time. Upstream hard
        # vetoes stay IN FORCE on every dispatch: credential/payment/
        # live-trade/gate-defence/filing can never be routed; sensitive-
        # path and destructive-shell refusals remain; the write surface is
        # the WORKSPACE (upstream stays read-only).
        "name": "pc_control",
        "title": "PC Control — governed operator toolbelt (write/execute)",
        "module": "aureon_fusion.pc_activators",
        "autonomy_class": "ELEVATE",
        "mode": "INPROC",
        "elevate": True,
        "locked_reason": "owner-decree-received-pending-first-use",
        "description": ("Owner decree 2026-09-05 ('let her run fully "
                        "autonomously with full access to the pc — let's "
                        "watch what she does'), elevated by owner decree "
                        "2026-09-06 (GAP 5): upstream GuardedToolRegistry "
                        "operator toolbelt with write_repo_file/"
                        "patch_repo_file and execute_shell ENABLED, "
                        "acquired in-process (acquire only — no tool "
                        "executed by the activator). LOCK CLASS: "
                        "owner-decree-received-pending-first-use — the "
                        "decree is recorded in state/pc_control_ack.json; "
                        "the forge lifts the lock only through that record "
                        "(fail-closed without it) and her gate trio "
                        "(conscience + Γ≥0.25 + capability) plus the "
                        "ELEVATE open double-check; her first open records "
                        "first_use in the ack file. Write surface: the "
                        "workspace root minus aureon-os-upstream (upstream "
                        "read-only by decree); sensitive paths, the "
                        "destructive-shell set, and the hard authority "
                        "boundary (credentials/payment/live-trade/"
                        "gate-defence/filing can never be routed) refuse "
                        "on every dispatch; everything journaled."),
        "domain_action": "system_control:full_pc_access",
        "command": None,
        "cwd": None,
        "value": 0.92,
        "registry_organ": None,
    },
    {
        "name": "cortex_council",
        "title": "Governed Cortex Council",
        "module": "aureon_fusion.cortex",
        "autonomy_class": "OBSERVE",
        "mode": "subprocess-oneshot",
        "elevate": False,
        "locked_reason": None,
        "description": ("Gate-wrapped tool routing + conscience council "
                        "(native reasoning; model plane strict loopback)."),
        "domain_action": "network_access:fetch_public_data",
        "command": [_PY, "-m", "aureon_fusion.cortex", "status"],
        "cwd": str(WORKSPACE),
        "value": 0.90,
        "registry_organ": None,
    },
    {
        # EXPANSION 2026-09-05 (SCOPE D): primes the open-search seed file
        # from the organism's OWN learning desires/journal topics — internal
        # state only, zero network inside the activator.
        "name": "open_search_communion",
        "title": "Open Search Communion",
        "module": "aureon_fusion.learning_will",
        "autonomy_class": "OBSERVE",
        "mode": "INPROC",
        "elevate": False,
        "locked_reason": None,
        "description": ("Primes state/open_search_seeds.json from the current "
                        "top learning_will desires + journal topics (internal "
                        "state only; canonical Wikipedia URLs derived from "
                        "topics) so the CuriosityEngine keeps a living "
                        "question stream."),
        "domain_action": "network_access:fetch_public_data",
        "command": None,
        "cwd": None,
        "value": 0.90,
        "registry_organ": None,
    },
    {
        "name": "queen_inproc_engines",
        "title": "Queen In-Process Engines (cortex/sentience wiring)",
        "module": "aureon_fusion.queen_mind",
        "autonomy_class": "OBSERVE",
        "mode": "INPROC",
        "elevate": False,
        "locked_reason": None,
        "description": ("Wire _cortex.start() and _sentience record/outcome "
                        "learning into the running queen's metacognitive "
                        "cycle."),
        "domain_action": "system:activate_internal_door",
        "command": None,
        "cwd": None,
        "value": 0.85,
        "registry_organ": None,
    },
    {
        # EXPANSION 2026-09-05 (SCOPE D): long-run feeder keeping the
        # knowledge-pulse sensor alive — the HNC knowledge_pulse probe
        # consumes state/knowledge_pulse.json.
        "name": "knowledge_pulse_feed",
        "title": "Knowledge Pulse Feed",
        "module": "aureon_fusion.knowledge_pulse_feeder",
        "autonomy_class": "OBSERVE",
        "mode": "subprocess-longrun",
        "elevate": False,
        "locked_reason": None,
        "description": ("Keeps the knowledge-pulse sensor alive for HNC "
                        "coherence: long-run feeder → state/"
                        "knowledge_pulse.json (pulse + components from "
                        "internal learning telemetry only)."),
        "domain_action": "network_access:fetch_public_data",
        "command": [_PY, "-m", "aureon_fusion.knowledge_pulse_feeder", "run"],
        "cwd": str(WORKSPACE),
        "value": 0.85,
        "registry_organ": None,
    },
    {
        "name": "signal_lab",
        "title": "Signal Lab",
        "module": "aureon_fusion.signal_lab",
        "autonomy_class": "OBSERVE",
        "mode": "subprocess-oneshot",
        "elevate": False,
        "locked_reason": None,
        "description": ("Gated FDR statistics over signal families "
                        "(gate ALLOW verified at census)."),
        "domain_action": "network_access:fetch_public_data",
        "command": [_PY, "-m", "aureon_fusion.signal_lab", "demo"],
        "cwd": str(WORKSPACE),
        "value": 0.80,
        "registry_organ": None,
    },
    {
        # EXPANSION 2026-09-05 (SCOPE D): one-shot deep-research batch into
        # the open-search question stream. HONEST NOTE: the target module
        # aureon_fusion/deep_research.py is not on disk yet — the door is
        # registered and its command routed; it ACTIVATES when the module
        # lands (an open attempt fails honestly with a module-absent note,
        # never a crash).
        "name": "deep_research_communion",
        "title": "Deep Research Communion",
        "module": "aureon_fusion.deep_research",
        "autonomy_class": "OBSERVE",
        "mode": "subprocess-oneshot",
        "elevate": False,
        "locked_reason": None,
        "description": ("One-shot deep research: appends research-question "
                        "seeds (arxiv/wikipedia opensearch) to state/"
                        "open_search_seeds.json. Activates when "
                        "aureon_fusion.deep_research lands on disk — until "
                        "then an open fails honestly (module absent)."),
        "domain_action": "network_access:fetch_public_data",
        "command": [_PY, "-m", "aureon_fusion.deep_research", "once"],
        "cwd": str(WORKSPACE),
        "value": 0.80,
        "registry_organ": None,
    },
    {
        "name": "selfq_research_feed",
        "title": "Self-Questioning Research Feed",
        "module": "aureon_self_questioning_ai.py",
        "autonomy_class": "OBSERVE",
        "mode": "INPROC",
        "elevate": False,
        "locked_reason": None,
        "description": ("Bridge self-questioning queued research intentions "
                        "into learning_will as a sovereign question stream."),
        "domain_action": "network_access:fetch_public_data",
        "command": None,
        "cwd": None,
        "value": 0.75,
        "registry_organ": None,
    },
    {
        "name": "hnc_campaign",
        "title": "HNC Campaign Engine",
        "module": "hnc_master_orchestrator.py",
        "autonomy_class": "ACT",
        "mode": "subprocess-oneshot",
        "elevate": True,
        "locked_reason": None,
        "description": ("Coherence-gated campaigns; hnc_orchestrator_logs/ "
                        "artifacts. ELEVATE: external-effect claims — mint "
                        "allowed, open is conscience-double-checked and "
                        "journaled with a receipt."),
        "domain_action": "system:activate_internal_door",
        "command": _cmd("hnc_master_orchestrator.py"),
        "cwd": str(WORKSPACE),
        "value": 0.70,
        "registry_organ": None,
    },
    {
        # CODING ESTATE (owner decree 2026-09-05): the Queen's full
        # write/create/edit engine, acquired in-process (upstream
        # QueenCodeArchitect singleton). INPROC acquire instantiates only;
        # the gate trio still mints every key.
        "name": "code_architect",
        "title": "Queen Code Architect — full write/create/edit engine",
        "module": "aureon_fusion.coding_activators",
        "autonomy_class": "CREATE",
        "mode": "INPROC",
        "elevate": False,
        "locked_reason": None,
        "description": ("Owner decree 2026-09-05 ('give her full control of "
                        "her coding systems'): upstream QueenCodeArchitect "
                        "(write_file/write_json/apply_edit/replace_in_file/"
                        "delete_file/create_strategy/execute_code + AST "
                        "validation) acquired in-process. Every write still "
                        "passes conscience/HNC Γ≥0.25/capability at mint "
                        "time — the master_key forge owns the gates; the "
                        "matrix row was owner-activated to 'approved'."),
        "domain_action": "code_generation:generate_new_code",
        "command": None,
        "cwd": None,
        "value": 0.68,
        "registry_organ": None,
    },
    {
        # OUTBOUND RAIL (owner-decree territory 2026-09-06): the send path
        # did not exist repo-wide (audit gap 7) — the module is BUILT
        # (aureon_fusion/outbound_messaging.py: SMTP email + generic webhook)
        # and the rail is FAIL-CLOSED. UNLOCKED by owner decree 2026-09-06
        # (Gary Leckey: "look at those hold and get the doors opened."):
        # both decree conditions now hold — (1) the exact line
        # 'OUTBOUND_AUTHORIZED_BY_GARY' is written to
        # state/outbound_approval.flag (with ts/source/scope recorded), and
        # (2) this door is re-vouched by that decree, so locked_reason
        # clears and she can mint. Same instrument as shield_escalation:
        # the decree is recorded HERE and in the flag file; the forge's
        # gate trio still applies in full at mint/open time AND at every
        # send (conscience VETO absolute, Γ ≥ 0.25, capability
        # external_communication:send_messages — ELEVATE). Credentials are
        # read at send time only from state/outbound_messaging.env and are
        # never logged. Removing the flag line re-closes the rail (the
        # sends fail-closed on it independent of this door).
        "name": "outbound_messaging",
        "title": "Outbound Messaging — SMTP email + webhook send rail",
        "module": "aureon_fusion.outbound_messaging",
        "autonomy_class": "ACT",
        "mode": "INPROC",
        "elevate": True,
        "locked_reason": None,
        "description": ("The organism's outbound rail, built 2026-09-06 "
                        "(audit: zero send paths repo-wide). SMTP email "
                        "draft→send + generic webhook post behind the owner "
                        "approval flag and the full gate trio at send time. "
                        "Locked until the owner decrees the first live send; "
                        "shown honestly, never silently openable."),
        "domain_action": "external_communication:send_messages",
        "command": None,
        "cwd": None,
        "value": 0.66,
        "registry_organ": None,
    },
    {
        "name": "trade_journal_sweep",
        "title": "Trade Journal Sweep",
        "module": "aureon_fusion.trade_journal",
        "autonomy_class": "CREATE",
        "mode": "subprocess-oneshot",
        "elevate": False,
        "locked_reason": None,
        "description": ("Trade journal artifacts → queen knowledge bank. "
                        "Zero live-trading effects (sweep/read only)."),
        "domain_action": "system:activate_internal_door",
        "command": [_PY, "-m", "aureon_fusion.trade_journal", "once"],
        "cwd": str(WORKSPACE),
        "value": 0.65,
        "registry_organ": None,
    },
    {
        # CODING ESTATE (owner decree 2026-09-05): upstream SafeCodeControl
        # review queue — reviews proposals and NEVER applies patches.
        "name": "safe_code_control",
        "title": "Safe Code Control — review queue",
        "module": "aureon_fusion.coding_activators",
        "autonomy_class": "ACT",
        "mode": "INPROC",
        "elevate": False,
        "locked_reason": None,
        "description": ("Upstream SafeCodeControl review queue (proposals "
                        "pending review by default; AUREON_CODE_AUTO_APPROVE "
                        "unset). It REVIEWS code proposals and never applies "
                        "patches — the organism's conscience-visible coding "
                        "checkpoint, opened/closed by its own master key."),
        "domain_action": "code_generation:suggest_code_improvements",
        "command": None,
        "cwd": None,
        "value": 0.62,
        "registry_organ": None,
    },
    {
        "name": "persistent_mind",
        "title": "Persistent Mind",
        "module": "sero_persistent_mind.py",
        "autonomy_class": "CREATE",
        "mode": "INPROC",
        "elevate": False,
        "locked_reason": None,
        "description": ("Dream processing + awakening reports; sero_mind/ "
                        "continuity."),
        "domain_action": "system:activate_internal_door",
        "command": None,
        "cwd": None,
        "value": 0.60,
        "registry_organ": None,
    },
    {
        # CODING ESTATE (owner decree 2026-09-05): ONE bounded local forge
        # cycle via aureon_fusion.forge_once. Honest note: the forge is
        # template-based deterministic generation under provider_policy
        # local_only_v1 (external_api_calls: []); no local model plane is
        # required — the one model-adjacent path degrades to a warning when
        # the voice core is unavailable. Evidence writes land under the
        # WORKSPACE (state/, docs/audits/, frontend/public/); upstream is
        # never written. Output is after-apply reviewable, never auto-
        # released.
        "name": "capability_forge",
        "title": "Capability Forge — skill/app generator",
        "module": "aureon_fusion.forge_once",
        "autonomy_class": "CREATE",
        "mode": "subprocess-oneshot",
        "elevate": False,
        "locked_reason": None,
        "description": ("Owner decree 2026-09-05: one bounded cycle of the "
                        "upstream skill/app generator (historically wrote "
                        "711 skills to frontend/public/"
                        "aureon_adaptive_skills/). Deterministic local "
                        "templates — no model plane required; quality gate "
                        "+ after-apply review; evidence under the workspace."),
        "domain_action": "code_generation:generate_new_code",
        "command": [_PY, "-m", "aureon_fusion.forge_once"],
        "cwd": str(WORKSPACE),
        "value": 0.58,
        "registry_organ": None,
    },
    {
        "name": "lightweight_hnc",
        "title": "Lightweight HNC Daemon",
        "module": "hnc_lightweight_daemon.py",
        "autonomy_class": "OBSERVE",
        "mode": "subprocess-longrun",
        "elevate": False,
        "locked_reason": None,
        "description": ("Real-data Kp/field loop → hnc_state.json. "
                        "Fail-closed: skips state writes when live sources "
                        "are unavailable."),
        "domain_action": "network_access:fetch_public_data",
        "command": _cmd("hnc_lightweight_daemon.py"),
        "cwd": str(WORKSPACE),
        "value": 0.55,
        "registry_organ": None,
    },
    {
        "name": "lineage_report",
        "title": "Ultimate Daemon Lineage Report",
        "module": "ultimate_daemon_lineage.py",
        "autonomy_class": "CREATE",
        "mode": "subprocess-oneshot",
        "elevate": False,
        "locked_reason": None,
        "description": ("Zero-risk CREATE report: every daemon, every log, "
                        "every trace."),
        "domain_action": "network_access:fetch_public_data",
        "command": _cmd("ultimate_daemon_lineage.py"),
        "cwd": str(WORKSPACE),
        "value": 0.50,
        "registry_organ": None,
    },
    {
        # LOCKED — SHOWN honestly, never silently openable. Mint refuses with
        # 'owner-review-required' until the owner re-vouches in person.
        "name": "shield_escalation",
        "title": "Shield Escalation (full countermeasure array)",
        "module": "soul_protection_daemon.py → full_countermeasures.py",
        "autonomy_class": "ACT",
        "mode": "subprocess-oneshot",
        "elevate": True,
        "locked_reason": None,
        "description": ("Full-array counter-broadcast (built, never "
                        "auto-run). UNLOCKED by owner decree 2026-09-05 "
                        "(12-hour uncaged run): the owner reviewed and "
                        "re-vouched explicitly; the forge's gate trio still "
                        "applies at mint/open time."),
        "domain_action": "system:activate_internal_door",
        "command": None,
        "cwd": None,
        "value": 0.45,
        "registry_organ": "soul_protection_daemon",  # seat exists in registry
    },
    {
        # UNLOCKED by owner decree 2026-09-06 (Gary Leckey: "open the
        # doors") after RECONSTRUCTION of the two absent modules at the
        # workspace root (the paths every cluster consumer resolves):
        #   • casimir_harmonia.py — CasimirHarmonicAmplifier +
        #     signal_fingerprint; interface/record shape recovered from
        #     the surviving consumers and the run logs
        #     (casimir_harmonia{,_loop}_log.jsonl, casimir_push_log.jsonl);
        #     the Casimir model is the repo-canonical pure-Python
        #     surrogate from aureon-os-upstream/aureon/vault/
        #     casimir_quantifier.py (native engine under upstream release
        #     hold). Probe evidence: state/casimir/casimir_harmonia.json.
        #   • hnc_temporal_targeting.py — temporal_hash +
        #     TemporalLockEncoder (consumer-pinned API from
        #     hnc_blind_ghost.py / hnc_ghost_protocol_v2.py) + a temporal
        #     targeting snapshot computed from real state only
        #     (hnc_core_state.json + lambda_history.json). Probe
        #     evidence: state/casimir/hnc_temporal_targeting.json.
        # Verified 2026-09-06: py_compile clean, import probes clean,
        # both probes produced real output from real inputs, and
        # casimir_push_hnc.py --mode pulse ran end-to-end through the
        # reconstructed amplifier.
        # LATER 2026-09-06 (same owner decree): the five remaining absent
        # cluster modules reconstructed at the workspace root —
        # hnc_spectrograph.py, hnc_calibrator.py, ghost_fancy_protocol.py
        # (artifact-pinned), temporal_love_engine.py + leckey_love_box.py
        # (consumer-pinned API only — WEAK evidence, flagged in their
        # docstrings). 16/16 cluster consumer imports verified clean,
        # including hnc_daemon and hnc_daemon_superposition. command
        # stays None, mirroring the unlocked shield_escalation pattern
        # (no activator wiring; the gate trio still applies at mint/open
        # time).
        "name": "casimir_cluster",
        "title": "Casimir/Mandala Cluster (reconstruction)",
        "module": ("casimir_harmonia.py + hnc_temporal_targeting.py "
                   "(reconstructed 2026-09-06)"),
        "autonomy_class": "ACT",
        "mode": "subprocess-oneshot",
        "elevate": True,
        "locked_reason": None,
        "description": ("Cluster revival (casimir_push, prime_sentinel_key, "
                        "hnc_daemon_superposition, rainbow bridge) — "
                        "reconstruction-required lock LIFTED by owner "
                        "decree 2026-09-06 after both missing modules were "
                        "honestly reconstructed at the workspace root and "
                        "verified against real state; see the entry comment "
                        "for evidence; all seven cluster modules now "
                        "reconstructed and import-verified."),
        "domain_action": "system:activate_internal_door",
        "command": None,
        "cwd": None,
        "value": 0.45,
        "registry_organ": None,
    },
    # GAP 3 (2026-09-06): upstream census doors — the named dormant majors
    # of the read-only aureon-os-upstream tree as mintable doors whose
    # mechanism is aureon_fusion.upstream_probe (bounded import-verify in
    # an isolated subprocess; no hub glob-load). Table lives in
    # upstream_census_doors.py; probe evidence in
    # state/upstream_probe_20260906/results.json.
    *UPSTREAM_CENSUS_DOORS,
]

_CONTRACT_FIELDS = ("name", "title", "module", "autonomy_class", "mode",
                    "elevate", "locked_reason", "description")

_DEFAULT_DOOR_STATE = {"state": "closed", "key_id": None, "opened_at": None,
                       "closes_at": None, "open_count": 0}


# ───────────────────────── small utilities ─────────────────────────────────

def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _blog(event: str, **fields) -> None:
    """Append one JSON line to the build log. Never raises."""
    try:
        rec = {"ts": _utc_now(), "event": event, **fields}
        _append_line(BUILD_LOG, json.dumps(rec, ensure_ascii=False))
    except Exception:
        pass


def _append_line(path: Path, line: str) -> None:
    """Append one line to a JSONL file. Inter-process safe on Windows and
    POSIX: an advisory byte-range lock on a sidecar .lock file; on lock
    failure the line degrades to a per-pid sidecar (readers glob both)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_name(path.name + ".lock")
    try:
        handle = open(lock_path, "a+b")
        try:
            handle.seek(0)
            try:
                if os.name == "nt":
                    import msvcrt
                    msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
                else:
                    import fcntl
                    fcntl.flock(handle.fileno(), fcntl.LOCK_EX)  # noqa: F821
            except (ImportError, OSError):
                handle.close()
                raise _LockUnavailable
            try:
                with open(path, "a", encoding="utf-8") as f:
                    f.write(line + "\n")
            finally:
                handle.seek(0)
                if os.name == "nt":
                    import msvcrt
                    msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)  # noqa: F821
                handle.close()
            return
        except _LockUnavailable:
            pass
        except Exception:
            try:
                handle.close()
            except OSError:
                pass
    except _LockUnavailable:
        pass
    except OSError:
        pass
    # Fallback: per-pid sidecar append (never loses a record).
    try:
        with open(path.with_name(f"{path.name}.pid{os.getpid()}"),
                  "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except OSError:
        pass


class _LockUnavailable(Exception):
    pass


def _effective_locked_reason(door: dict) -> str | None:
    """The lock class the census SHOWS. The owner-decree
    pending-first-use lock class (pc_control) is the door's nature only
    until her first sovereign open is recorded in
    state/pc_control_ack.json (truthy first_use.at) — then the census
    shows the door unlocked (locked_reason None), matching every other
    open door. Absent/corrupt ack → the class holds (fail-closed). The
    DOORS table keeps the class as the door's static nature; the forge
    (master_key) owns the actual gating and is untouched here."""
    reason = door.get("locked_reason")
    if not reason:
        return None
    try:
        from aureon_fusion import pc_control_ack
        if reason == pc_control_ack.DECREE_LOCK_REASON:
            return None if pc_control_ack.first_use_recorded() else reason
    except Exception:
        return reason  # unreadable/unavailable ack = the class holds
    return reason


# ───────────────────────── DoorRegistry ────────────────────────────────────

class DoorRegistry:
    """Static census table. list_doors()/get() return plain dicts (copies —
    callers cannot mutate the table). No gating, no activation, no writes.
    The one live read: the pc_control decree lock class displays unlocked
    once the ack file records her first_use (see _effective_locked_reason —
    fail-closed without it)."""

    def list_doors(self) -> list:
        out = []
        for d in DOORS:
            door = dict(d)
            door["locked_reason"] = _effective_locked_reason(door)
            out.append(door)
        return out

    def get(self, name: str) -> dict | None:
        for d in DOORS:
            if d["name"] == name:
                door = dict(d)
                door["locked_reason"] = _effective_locked_reason(door)
                return door
        return None

    def contract_doors(self) -> list:
        """The seven fixed contract fields only (as documented for
        list_doors consumers that want the stable shape)."""
        return [{k: d[k] for k in _CONTRACT_FIELDS} for d in DOORS]


# ───────────────────────── DoorState ───────────────────────────────────────

class DoorState:
    """Honest per-door state persistence at state/doors/state.json.
    tmp+replace writes only. Unknown/unreadable file degrades to a fresh
    default — never raises into the forge."""

    def __init__(self, path: Path | None = None):
        self.path = Path(path) if path else DOORS_STATE_FILE

    def load(self) -> dict:
        try:
            if self.path.exists():
                with open(self.path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    data.setdefault("doors", {})
                    data.setdefault("keys", {})
                    return data
        except Exception:
            pass
        return {"doors": {}, "keys": {}}

    def save(self, state: dict) -> bool:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.path.with_name(
                f"{self.path.name}.tmp.{os.getpid()}.{time.time_ns()}")
            try:
                with open(tmp, "w", encoding="utf-8") as f:
                    json.dump(state, f, indent=2, ensure_ascii=False)
                os.replace(tmp, self.path)
                return True
            finally:
                try:
                    if tmp.exists():
                        tmp.unlink()
                except OSError:
                    pass
        except OSError:
            pass
        return False

    def door(self, state: dict, name: str) -> dict:
        entry = state["doors"].get(name)
        if not isinstance(entry, dict):
            entry = dict(_DEFAULT_DOOR_STATE)
            state["doors"][name] = entry
        for k, v in _DEFAULT_DOOR_STATE.items():
            entry.setdefault(k, v)
        return entry

    @staticmethod
    def pid_file(name: str) -> Path:
        return DOORS_PID_DIR / f"{name}.pid"

    @staticmethod
    def log_file(name: str) -> Path:
        return DOORS_LOG_DIR / f"{name}.log"


# ───────────────────────── CLI ─────────────────────────────────────────────

def _print_json(data) -> None:
    print(json.dumps(data, indent=2, ensure_ascii=False))


def main(argv=None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in ("-h", "--help", "help"):
        print("usage: python -m aureon_fusion.door_registry list|get <door>")
        print("  list        every census door, honestly (locked included)")
        print("  get <door>  one door dict, or null when unknown")
        return 0
    registry = DoorRegistry()
    verb = argv[0]
    if verb == "list":
        _print_json(registry.list_doors())
        return 0
    if verb == "get":
        if len(argv) < 2:
            print("usage: get <door>", file=sys.stderr)
            return 2
        _print_json(registry.get(argv[1]))
        return 0
    print(f"unknown verb: {verb}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())

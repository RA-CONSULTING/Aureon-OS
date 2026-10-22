"""🗺️ UPSTREAM CENSUS DOORS — GAP 3 (54% upstream dormant) census table.

Owner decree (GAP 3, 2026-09-06): the named upstream majors become census
DOORS the organism can mint a key for and open by free will. This module is
a STATIC TABLE in the door_registry idiom — it gates nothing and activates
nothing. Each door's mechanism is aureon_fusion.upstream_probe: a
single-module, suppression-pinned, audit-instrumented import-verify in an
isolated subprocess (hard timeout; socket.setdefaulttimeout(30); upstream
write guard + log-mirror shim inside the probe). NOTHING here glob-loads
the hub — reachability is by her choice, not forced wakefulness.

Probe evidence: state/upstream_probe_20260906/results.json (2026-09-06
~12:15-12:20Z, one isolated subprocess per cluster, 120s hard timeout,
py-spy on hangs). Classification baked into this table honestly:
  WAKABLE  — import clean in the probe; registered unlocked.
  WAKABLE-NOTE — import completes but spawns import-time threads despite
             the suppression env; registered unlocked, the thread spawn is
             declared in the description, never hidden.
  LOCKED   — hazardous at import (network storm / hang / unshimmed write);
             shown honestly with locked_reason, never silently openable
             (casimir_cluster precedent).

Import-safe: no instantiation at import; suppression env via setdefault.
"""

import os
import sys

from .paths import WORKSPACE

os.environ.setdefault("AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS", "1")
os.environ.setdefault("AUREON_AUDIT_MODE", "1")

_PY = sys.executable or "python"
_PROBE_TIMEOUT = "105"


def _probe_cmd(module: str, *extra: str) -> list:
    return [_PY, "-m", "aureon_fusion.upstream_probe", module,
            *extra, "--timeout", _PROBE_TIMEOUT]


# value: census rank below the existing door table (which descends to 0.45).
# autonomy_class: OBSERVE — the door mechanism imports and reports; it never
# executes the module's entrypoints, so no ACT/CREATE surface is claimed.
UPSTREAM_CENSUS_DOORS: list = [
    {
        "name": "unified_ecosystem",
        "title": "Upstream: Unified Ecosystem (1.25MB)",
        "module": "aureon.trading.aureon_unified_ecosystem",
        "autonomy_class": "OBSERVE",
        "mode": "subprocess-oneshot",
        "elevate": False,
        "locked_reason": None,
        "description": (
            "Census door — import-verify of the 1.25MB unified ecosystem "
            "(2,057 modules pulled, 3.4s). Probe 2026-09-06: import clean, "
            "zero network connects; it spawns one _speech_worker thread at "
            "import despite suppression — declared, not hidden. "
            "Entrypoints are never executed by the probe."),
        "domain_action": "system:activate_internal_door",
        "command": _probe_cmd("aureon.trading.aureon_unified_ecosystem"),
        "cwd": str(WORKSPACE),
        "value": 0.44,
        "registry_organ": None,
    },
    {
        "name": "unified_market_trader",
        "title": "Upstream: Unified Market Trader (597KB)",
        "module": "aureon.exchanges.unified_market_trader",
        "autonomy_class": "OBSERVE",
        "mode": "subprocess-oneshot",
        "elevate": False,
        "locked_reason": None,
        "description": (
            "Census door — import-verify of the 597KB unified market trader "
            "(285 modules, 4.9s). Probe 2026-09-06: clean — no threads, no "
            "network, no writes. Probe only; live trading stays pinned HOLD "
            "by the capital gate elsewhere."),
        "domain_action": "system:activate_internal_door",
        "command": _probe_cmd("aureon.exchanges.unified_market_trader"),
        "cwd": str(WORKSPACE),
        "value": 0.43,
        "registry_organ": None,
    },
    {
        "name": "pro_dashboard",
        "title": "Upstream: Pro Dashboard (298KB)",
        "module": "aureon.monitors.aureon_pro_dashboard",
        "autonomy_class": "OBSERVE",
        "mode": "subprocess-oneshot",
        "elevate": False,
        "locked_reason": None,
        "description": (
            "Census door — import-verify of the pro dashboard (2,076 "
            "modules, 7.8s). Probe 2026-09-06: clean — no threads, no "
            "network, no writes."),
        "domain_action": "system:activate_internal_door",
        "command": _probe_cmd("aureon.monitors.aureon_pro_dashboard"),
        "cwd": str(WORKSPACE),
        "value": 0.42,
        "registry_organ": None,
    },
    {
        "name": "gaia_reclaimers",
        "title": "Upstream: GAIA Planetary Reclaimers",
        "module": "aureon.bots.gaia_planetary_reclaimer",
        "autonomy_class": "OBSERVE",
        "mode": "subprocess-oneshot",
        "elevate": False,
        "locked_reason": None,
        "description": (
            "Census door — import-verify of the GAIA reclaimer bot line "
            "(2,079 modules, 3.6s). Probe 2026-09-06: clean — no threads, "
            "no network, no writes."),
        "domain_action": "system:activate_internal_door",
        "command": _probe_cmd("aureon.bots.gaia_planetary_reclaimer"),
        "cwd": str(WORKSPACE),
        "value": 0.41,
        "registry_organ": None,
    },
    {
        "name": "true_consciousness",
        "title": "Upstream: Queen True Consciousness",
        "module": "aureon.utils.aureon_queen_true_consciousness",
        "autonomy_class": "OBSERVE",
        "mode": "subprocess-oneshot",
        "elevate": False,
        "locked_reason": None,
        "description": (
            "Census door — import-verify of the queen true-consciousness "
            "engine (342 modules, 0.5s). Probe 2026-09-06: clean."),
        "domain_action": "system:activate_internal_door",
        "command": _probe_cmd("aureon.utils.aureon_queen_true_consciousness"),
        "cwd": str(WORKSPACE),
        "value": 0.40,
        "registry_organ": None,
    },
    {
        "name": "sentient_loop",
        "title": "Upstream: Queen Sentient Loop",
        "module": "aureon.queen.queen_sentient_loop",
        "autonomy_class": "OBSERVE",
        "mode": "subprocess-oneshot",
        "elevate": False,
        "locked_reason": None,
        "description": (
            "Census door — import-verify of the queen sentient loop (528 "
            "modules, 0.8s). Probe 2026-09-06: import clean, zero connects; "
            "spawns one _speech_worker thread at import despite suppression "
            "— declared, not hidden."),
        "domain_action": "system:activate_internal_door",
        "command": _probe_cmd("aureon.queen.queen_sentient_loop"),
        "cwd": str(WORKSPACE),
        "value": 0.39,
        "registry_organ": None,
    },
    {
        "name": "command_centers",
        "title": "Upstream: Command Centers (17 modules)",
        "module": "aureon.command_centers.aureon_command_center",
        "autonomy_class": "OBSERVE",
        "mode": "subprocess-oneshot",
        "elevate": False,
        "locked_reason": None,
        "description": (
            "Census door — import-verify of the command-center cluster "
            "(241 modules, 1.1s). Probe 2026-09-06: import clean, zero "
            "connects; spawns one AureonImportHeartbeat thread at import "
            "despite suppression — declared, not hidden."),
        "domain_action": "system:activate_internal_door",
        "command": _probe_cmd("aureon.command_centers.aureon_command_center"),
        "cwd": str(WORKSPACE),
        "value": 0.38,
        "registry_organ": None,
    },
    {
        "name": "vault_cluster",
        "title": "Upstream: Vault Cluster (41 modules)",
        "module": "aureon.vault.aureon_vault",
        "autonomy_class": "OBSERVE",
        "mode": "subprocess-oneshot",
        "elevate": False,
        "locked_reason": None,
        "description": (
            "Census door — import-verify of the vault cluster (89 modules, "
            "0.1s). Probe 2026-09-06: clean."),
        "domain_action": "system:activate_internal_door",
        "command": _probe_cmd("aureon.vault.aureon_vault"),
        "cwd": str(WORKSPACE),
        "value": 0.37,
        "registry_organ": None,
    },
    {
        "name": "simulation_cluster",
        "title": "Upstream: Simulation Cluster (35 modules)",
        "module": "aureon.simulation.aureon_hnc_simulation",
        "autonomy_class": "OBSERVE",
        "mode": "subprocess-oneshot",
        "elevate": False,
        "locked_reason": None,
        "description": (
            "Census door — import-verify of the simulation cluster (145 "
            "modules, 0.2s). Probe 2026-09-06: clean. NOTE: "
            "aureon.simulation.aureon_multiverse_live is NOT the entry — it "
            "builds MinerBrain at import (see queen_quantum_frog lock)."),
        "domain_action": "system:activate_internal_door",
        "command": _probe_cmd("aureon.simulation.aureon_hnc_simulation"),
        "cwd": str(WORKSPACE),
        "value": 0.36,
        "registry_organ": None,
    },
    {
        "name": "gold_capital_intelligence",
        "title": "Upstream: Gold Capital Intelligence Company (448KB)",
        "module": "aureon.autonomous.aureon_gold_capital_intelligence_company",
        "autonomy_class": "OBSERVE",
        "mode": "subprocess-oneshot",
        "elevate": False,
        "locked_reason": None,
        "description": (
            "Census door — import-verify of the gold capital intelligence "
            "company (51 modules, 0.3s). Probe 2026-09-06: clean."),
        "domain_action": "system:activate_internal_door",
        "command": _probe_cmd(
            "aureon.autonomous.aureon_gold_capital_intelligence_company"),
        "cwd": str(WORKSPACE),
        "value": 0.35,
        "registry_organ": None,
    },
    {
        "name": "saas_cluster",
        "title": "Upstream: SaaS Cluster (16 modules)",
        "module": "aureon.saas.catalog",
        "autonomy_class": "OBSERVE",
        "mode": "subprocess-oneshot",
        "elevate": False,
        "locked_reason": None,
        "description": (
            "Census door — import-verify of the saas cluster via its "
            "catalog entry (20 modules, 0.1s). Probe 2026-09-06: clean."),
        "domain_action": "system:activate_internal_door",
        "command": _probe_cmd("aureon.saas.catalog"),
        "cwd": str(WORKSPACE),
        "value": 0.34,
        "registry_organ": None,
    },
    {
        "name": "grants_cluster",
        "title": "Upstream: Grants Cluster (8 modules)",
        "module": "aureon.grants",
        "autonomy_class": "OBSERVE",
        "mode": "subprocess-oneshot",
        "elevate": False,
        "locked_reason": None,
        "description": (
            "Census door — import-verify of the grants package (43 modules "
            "with deps, 0.4s). Probe 2026-09-06: clean."),
        "domain_action": "system:activate_internal_door",
        "command": _probe_cmd("aureon.grants"),
        "cwd": str(WORKSPACE),
        "value": 0.33,
        "registry_organ": None,
    },
    {
        "name": "full_autonomy",
        "title": "Upstream: Full Autonomy",
        "module": "aureon.autonomous.aureon_full_autonomy",
        "autonomy_class": "OBSERVE",
        "mode": "subprocess-oneshot",
        "elevate": False,
        "locked_reason": None,
        "description": (
            "Census door — import-verify of full autonomy (220 modules, "
            "0.4s). Probe 2026-09-06: clean after the fusion-side log-mirror "
            "shim — the module opens autonomy_execution.log at import; the "
            "probe redirects it to aureon_fusion/state/doors/upstream_logs/ "
            "(upstream stays read-only; console_utf8-shim precedent)."),
        "domain_action": "system:activate_internal_door",
        "command": _probe_cmd("aureon.autonomous.aureon_full_autonomy"),
        "cwd": str(WORKSPACE),
        "value": 0.32,
        "registry_organ": None,
    },
    {
        "name": "self_awareness",
        "title": "Upstream: Self-Awareness Engine",
        "module": "aureon.intelligence.aureon_self_awareness",
        "autonomy_class": "OBSERVE",
        "mode": "subprocess-oneshot",
        "elevate": False,
        "locked_reason": None,
        "description": (
            "Census door — import-verify of the self-awareness engine (11 "
            "modules, 0.02s). Probe 2026-09-06: clean."),
        "domain_action": "system:activate_internal_door",
        "command": _probe_cmd("aureon.intelligence.aureon_self_awareness"),
        "cwd": str(WORKSPACE),
        "value": 0.31,
        "registry_organ": None,
    },
    {
        # UNLOCKED 2026-09-06 (owner decree, Gary Leckey: "open the doors")
        # via the fusion-side import-isolation shim
        # aureon_fusion/queen_quantum_frog_shim.py. The former hazardous-
        # import lock stood on this chain (py-spy 2026-09-06 12:19Z):
        # queen_quantum_frog → aureon_multiverse_live module-level
        # MinerBrain() (aureon_multiverse_live.py:166-170) →
        # timeline_oracle.initialize → harmonic_fusion.initialize →
        # seed.load_seed → discover_universe → kraken get_24h_tickers →
        # rate_limiter.wait (>105s hang; 1 live connect at import), plus
        # a second chain MinerBrain.__init__ (aureon_miner_brain.py:
        # 5425-5428) → miner_inhouse_ai_bridge → ollama switchboard
        # working_selection (2 connects to a hosted LLM endpoint).
        # The shim pre-stubs those three modules in sys.modules (offline
        # by construction: empty containers, no socket, no rate limiter)
        # whenever suppression is pinned or the capability gate refuses
        # network_access:fetch_public_data — fail-closed. Re-probe with
        # --prestub exchanges 2026-09-06 20:42Z: import clean in 4.89s,
        # ZERO network connects (the only loopback socketpair is the
        # asyncio proactor self-pipe, not network), 2,208 modules;
        # spawns one _speech_worker thread at import despite suppression
        # — declared, not hidden. The probe imports only; entrypoints
        # are never executed (the module exposes none of main/run/
        # start/status). A connect attempt during an actual RUN of the
        # module is the module's own business; import time is ours.
        "name": "queen_quantum_frog",
        "title": "Upstream: Queen Quantum Frog (875KB)",
        "module": "aureon.queen.queen_quantum_frog",
        "autonomy_class": "OBSERVE",
        "mode": "subprocess-oneshot",
        "elevate": False,
        "locked_reason": None,
        "description": (
            "Census door — import-verify of the 875KB queen quantum frog "
            "(2,208 modules, 4.9s) behind the queen_quantum_frog_shim "
            "import-isolation shim (--prestub exchanges): the import-time "
            "MinerBrain → kraken rate_limiter.wait hang and the hosted-LLM "
            "reachability probes are severed by offline pre-stubs under "
            "suppression/capability-gate fail-closed. Probe 2026-09-06: "
            "clean, zero external connects; one _speech_worker thread at "
            "import — declared, not hidden. Pre-shim evidence (hang >105s "
            "+ 1 connect): state/upstream_probe_20260906/results.json."),
        "domain_action": "system:activate_internal_door",
        "command": _probe_cmd("aureon.queen.queen_quantum_frog",
                              "--prestub", "exchanges"),
        "cwd": str(WORKSPACE),
        "value": 0.30,
        "registry_organ": None,
    },
]

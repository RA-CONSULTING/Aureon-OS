"""🐸 QUEEN QUANTUM FROG SHIM — import-isolation adapter for the
queen_quantum_frog census door (owner decree 2026-09-06, Gary Leckey:
"open the doors").

HAZARD (probe evidence 2026-09-06, state/upstream_probe_20260906/
results.json + py-spy dump): importing aureon.queen.queen_quantum_frog
at module level pulls aureon.simulation.aureon_multiverse_live, which
builds MinerBrain() AT IMPORT (aureon_multiverse_live.py:166-170)
→ timeline_oracle.initialize → harmonic_fusion.initialize →
seed.load_seed → discover_universe → kraken get_24h_tickers →
rate_limiter.wait — an import-time Kraken API hang (>105s) with one
live network connect (Cloudflare 443). A second import-time chain,
found while building this shim, goes MinerBrain.__init__
(aureon_miner_brain.py:5425-5428) → miner_inhouse_ai_bridge → ollama
model_switchboard working_selection, which probes a hosted LLM
endpoint (2 connects to 34.36.133.15:443). Both chains are severed by
the pre-stubs below.

This shim makes the door's import surface safe WITHOUT touching the
read-only upstream tree:
  • Importing THIS module is instant and inert — zero upstream imports,
    zero network, zero instantiation, zero threads.
  • The real upstream module is imported lazily on FIRST ATTRIBUTE
    ACCESS via module-level __getattr__ (PEP 562), never at import time.
  • Before the lazy import, the modules the import-time chains reach
    for are pre-stubbed in sys.modules whenever a fail-closed condition
    holds — AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS=1, or the capability
    gate refusing network_access:fetch_public_data: the exchange
    clients (kraken, binance — harmonic-seed discover_universe) and the
    miner in-house AI bridge (hosted-LLM reachability probes). The
    stubs are offline by construction: every data method returns an
    empty container or None, no socket is ever opened, no rate limiter
    is ever waited on. Network is thereby routed through the organism's
    own capability/policy layer (aureon_fusion.capability_gate) and
    fails CLOSED (no external network) when suppressed.
  • When neither fail-closed condition holds, the real upstream module
    loads as-is; any network it then performs is the module's own
    run-time business — documented, never hidden. Import time stays
    ours: THIS module never opens a socket at import, in any mode.

The census-door probe uses install_exchange_prestubs() via
`--prestub exchanges` so the door mechanism verifies the REAL upstream
module import (not this adapter) with the fail-closed stubs in place.

CLI:
    python -m aureon_fusion.queen_quantum_frog_shim status  # gate/suppression state
    python -m aureon_fusion.queen_quantum_frog_shim probe   # guarded lazy import + report
"""

import importlib
import json
import os
import sys
import time
import types

os.environ.setdefault("AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS", "1")
os.environ.setdefault("AUREON_AUDIT_MODE", "1")

UPSTREAM_MODULE = "aureon.queen.queen_quantum_frog"
NETWORK_GATE = "network_access:fetch_public_data"
SHIM_VERSION = "1.0.0"

# (module, client class, singleton getter) — the modules the import-time
# chains reach for and their live-network entry points:
#  • exchange clients — MinerBrain → harmonic-seed discover_universe
#    (aureon/harmonic/aureon_harmonic_seed.py:303-320) → kraken
#    get_24h_tickers → rate_limiter.wait (the >105s hang).
#  • miner in-house AI bridge — MinerBrain.__init__
#    (aureon/utils/aureon_miner_brain.py:5425-5428) → ollama
#    model_switchboard working_selection (hosted-LLM endpoint probes).
_EXCHANGE_PRESTUBS = (
    ("aureon.exchanges.kraken_client", "KrakenClient", "get_kraken_client"),
    ("aureon.exchanges.binance_client", "BinanceClient", "get_binance_client"),
    ("aureon.miner.miner_inhouse_ai_bridge", "MinerAIBridge",
     "get_miner_ai_bridge"),
)


def suppression_active() -> bool:
    """The organism-wide import-side-effect suppression pin."""
    return os.environ.get("AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS") == "1"


def network_allowed_by_gate() -> bool:
    """Capability-matrix verdict for the network domain. Any internal
    error is a fail-closed 'no' (mirrors capability_gate's own
    fail-closed doctrine)."""
    try:
        from aureon_fusion import capability_gate
        verdict = capability_gate.check(NETWORK_GATE)
    except Exception:
        return False
    return verdict.get("verdict") == "ALLOW" and bool(verdict.get("allowed"))


class _OfflineExchangeStub:
    """Offline-by-construction exchange client. Every data method returns
    an empty container; __getattr__ covers any other method surface
    upstream probes with hasattr(). No socket, no rate limiter, no
    credentials — MinerBrain's import-time chain completes against
    empties in microseconds."""

    def get_24h_tickers(self, *a, **k):
        return []

    def get_tradeable_pairs(self, *a, **k):
        return {}

    def get_ticker(self, *a, **k):
        return {}

    def get_tickers(self, *a, **k):
        return {}

    def get_balance(self, *a, **k):
        return {}

    def get_balances(self, *a, **k):
        return {}

    def get_ohlc(self, *a, **k):
        return []

    def get_ohlcv(self, *a, **k):
        return []

    def get_historical_data(self, *a, **k):
        return []

    def get_exchange_info(self, *a, **k):
        return {}

    def __getattr__(self, name):
        if name.startswith("__"):
            raise AttributeError(name)

        def _offline(*args, **kwargs):
            return None

        return _offline


def _build_exchange_stub_module(modname, class_name, getter_name):
    """A synthetic module standing in for an upstream exchange client:
    the class, its singleton getter, and any other imported name all
    resolve to the offline stub — never the real client."""
    mod = types.ModuleType(modname)
    client_cls = type(class_name, (_OfflineExchangeStub,),
                      {"__module__": modname})
    mod.__dict__[class_name] = client_cls

    def _get_client(_cls=client_cls):
        return _cls()

    mod.__dict__[getter_name] = _get_client

    def _module_getattr(name, _cls=client_cls):
        if name.startswith("__"):
            raise AttributeError(name)
        return _cls

    mod.__dict__["__getattr__"] = _module_getattr
    return mod


def install_exchange_prestubs() -> list:
    """Inject offline exchange-client stubs into sys.modules BEFORE any
    aureon import (pre-stub: the real modules never load). Returns the
    list of module names installed. Idempotent."""
    installed = []
    for modname, class_name, getter_name in _EXCHANGE_PRESTUBS:
        sys.modules[modname] = _build_exchange_stub_module(
            modname, class_name, getter_name)
        installed.append(modname)
    return installed


_real_module = None
_loading = False


def _ensure_upstream_path():
    from .paths import AUREON_UPSTREAM
    p = str(AUREON_UPSTREAM)
    if p not in sys.path:
        sys.path.insert(0, p)


def load_real_module():
    """Lazy import of aureon.queen.queen_quantum_frog, guarded.

    Fail-closed rule: if suppression is active OR the capability gate
    refuses the network domain, exchange clients are pre-stubbed so the
    import-time MinerBrain → harmonic-seed chain runs fully offline
    (zero connects, zero rate_limiter.wait). Otherwise the module loads
    as-is; its run-time network is its own documented business."""
    global _real_module, _loading
    if _real_module is not None:
        return _real_module
    if _loading:
        raise RuntimeError(
            "queen_quantum_frog_shim: recursive lazy load — refusing")
    _loading = True
    try:
        prestubbed = False
        if suppression_active() or not network_allowed_by_gate():
            install_exchange_prestubs()
            prestubbed = True
        _ensure_upstream_path()
        _real_module = importlib.import_module(UPSTREAM_MODULE)
        _real_module.__dict__.setdefault("_AUREON_PRESTUBBED", prestubbed)
        return _real_module
    finally:
        _loading = False


def __getattr__(name):
    """PEP 562 lazy surface: the heavy upstream import happens on first
    attribute access, never at import time of this shim."""
    if name.startswith("__"):
        raise AttributeError(name)
    return getattr(load_real_module(), name)


# ───────────────────────── CLI (verification) ──────────────────────────────

def _connect_counter():
    """Count socket connect attempts (same instrumentation idiom as
    upstream_probe._ImportAudit)."""
    import socket
    state = {"connects": [], "orig_cc": socket.create_connection,
             "orig_connect": socket.socket.connect}

    def counted_cc(addr, *args, **kwargs):
        state["connects"].append(str(addr))
        return state["orig_cc"](addr, *args, **kwargs)

    def counted_connect(sock, addr):
        state["connects"].append(str(addr))
        return state["orig_connect"](sock, addr)

    socket.create_connection = counted_cc
    socket.socket.connect = counted_connect
    return state


def main(argv=None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    argv = list(sys.argv[1:] if argv is None else argv)
    verb = argv[0] if argv else "status"
    if verb == "status":
        print(json.dumps({
            "shim": "queen_quantum_frog_shim",
            "version": SHIM_VERSION,
            "upstream_module": UPSTREAM_MODULE,
            "suppression_active": suppression_active(),
            "network_gate": NETWORK_GATE,
            "network_allowed_by_gate": network_allowed_by_gate(),
        }, indent=2, ensure_ascii=False))
        return 0
    if verb == "probe":
        # Guarded dry probe: lazy-load the real module and touch ONE
        # attribute, counting every socket connect attempt. Proves the
        # import-time surface is offline under the fail-closed rule. No
        # upstream entrypoint (main/run/start) is executed.
        counter = _connect_counter()
        try:
            t0 = time.monotonic()
            mod = load_real_module()
            attr = argv[1] if len(argv) > 1 else "MultiverseLiveEngine"
            getattr(mod, attr, None)
            elapsed = round(time.monotonic() - t0, 3)
        finally:
            import socket
            socket.create_connection = counter["orig_cc"]
            socket.socket.connect = counter["orig_connect"]
        print(json.dumps({
            "ok": True,
            "shim": "queen_quantum_frog_shim",
            "upstream_module": UPSTREAM_MODULE,
            "attribute_touched": attr,
            "prestubbed": bool(getattr(mod, "_AUREON_PRESTUBBED", None)),
            "suppression_active": suppression_active(),
            "elapsed_s": elapsed,
            "connects_attempted": counter["connects"][:20],
            "connects_count": len(counter["connects"]),
            "external_connects_count": sum(
                1 for c in counter["connects"] if "'127.0.0.1'" not in c),
            "entrypoints_executed": [],
        }, indent=2, ensure_ascii=False))
        return 0
    print("usage: python -m aureon_fusion.queen_quantum_frog_shim "
          "[status | probe [attribute]]", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())

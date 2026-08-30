"""Pytest conftest: add aureon/ and all its subdirectories to sys.path so bare
module-name imports (e.g. ``from aureon_nexus import ...``) resolve correctly
after the repository reorganisation.

Also runs ``async def`` tests via ``asyncio.run``: 16 test modules define native
coroutine tests, no async pytest plugin is declared in the repo's requirements, and
without one pytest fails every such test with "async def functions are not natively
supported" — so those 16 modules were red on every run without their assertions ever
executing. A stdlib hook keeps the repo's no-extra-dependency posture (the same reason
the JWT verifier is stdlib) while making the tests actually run.
"""

import asyncio
import inspect
import os
import sys
import threading
from pathlib import Path

import pytest

# These are standalone diagnostic SCRIPTS, not pytest modules: each defines
# ZERO test functions and runs its whole scenario at module level, so the only
# thing pytest collection gets from importing them is the side effects —
# test_orca_quick boots an OrcaKillCycle (exchange clients, TheKing, stream
# loops), test_bot_intelligence_wiring boots the Queen/bus stack
# (ETAOmnipresent), the queen/cost-basis/windows files start _stream_loop /
# _bg_refresh / _monitor_loop workers, test_scout_deployment starts
# SourceLawTimer + a wisdom scan. Measured on this tree (B5 sentinel run 4): 31
# live threads before the FIRST test executed, publishing into every later
# test's isolated trace dir for the whole ~28-minute run — the mechanism behind
# the last order-dependent failures. Ignoring them here loses zero tests and
# keeps the scripts byte-identical for their real use:
#   python tests/test_orca_quick.py
#
# The second block is the sys.exit family (measured, B5 run 6): test_crash.py
# permanently replaces sys.exit with a print-and-continue guard for the WHOLE
# pytest process, and eleven sibling scripts call sys.exit at module level —
# imports that only ever survived collection because test_crash ('c') imported
# alphabetically before them and had already disarmed sys.exit. Any subset run
# that starts after 'c' (bisections, split-half confirmations) crashed the
# session with INTERNALERROR SystemExit, and every full run silently executed
# those scripts' whole scenarios at collection time. Membership is the AST
# audit of zero-test files with an unguarded module-level sys.exit; a
# main-guarded sibling (test_profit_gate.py) stays collectable.
#
# The third block is the scenario-executing remainder (measured, B6 import
# probe over every zero-test candidate, scratchpad probe_batch1/2): each file
# defines ZERO collectable tests but runs its whole scenario at import, so
# every pytest collection silently executed all of them — ~2.5 minutes of
# script runtime per run, much of it live network (smoke_test boots the
# Kraken ecosystem, 49s; test_ocean_whale_map fetches market data for 197+
# coins, 29s; test_ecosystem_demo 24s; test_uk_binance boots
# MicroProfitLabyrinth AND os.chdir()s the whole process). Two are worse than
# waste: test_hnc_hub_publish pushed 60 SYNTHETIC BTC ticks into the real
# feed-hub bus at every collection (fake data into a real pipe), and
# smoke_test carries a module-level sys.exit(1) in its except branch — a
# latent INTERNALERROR whenever Kraken init fails. Membership is measured:
# elapsed >= ~2s or >= ~5KB of scenario output in the probe, AND zero
# collectable tests confirmed against the collect-only census (which caught
# that test_queen_trade_execution_validation's 6 tests live on a TestCase
# subclass without the Test* name prefix — it stays collectable). Import-only
# zero-test files (e.g. test_alpaca_capital_style, test_imports_debug) stay
# collectable because their cost is shared module-cache warming.
collect_ignore = [
    # thread-spawning scripts (B5 run 4)
    "tests/test_bot_intelligence_wiring.py",
    "tests/test_cost_basis_target.py",
    "tests/test_orca_quick.py",
    "tests/test_queen_deep_intelligence_live.py",
    "tests/test_queen_metrics.py",
    "tests/test_queens_heart.py",
    "tests/test_scout_deployment.py",
    "tests/test_windows_startup.py",
    # sys.exit family (B5 run 6)
    "tests/test_binance_margin_dryrun.py",
    "tests/test_crash.py",
    "tests/test_fallback.py",
    "tests/test_hive_mind_live.py",
    "tests/test_live_tv_wiring.py",
    "tests/test_operational_core.py",
    "tests/test_orca_super_gate.py",
    "tests/test_quantum_v11_amplification.py",
    "tests/test_trade_capability.py",
    "tests/test_unified_trading_logic.py",
    "tests/test_why_no_trades.py",
    "tests/vault/test_hnc_human_loop.py",
    "tests/vault/test_temporal_ground.py",
    # scenario-executing zero-test scripts (B6 import probe)
    "tests/smoke_test.py",
    "tests/test_ecosystem_demo.py",
    "tests/test_full_cycle.py",
    "tests/test_full_spectrum_flow.py",
    "tests/test_hnc_hub_publish.py",
    "tests/test_imports.py",
    "tests/test_mountain_pilgrimage.py",
    "tests/test_ocean_whale_map.py",
    "tests/test_orca_in_main_loop.py",
    "tests/test_orca_integration.py",
    "tests/test_platform_trades.py",
    "tests/test_queen_full_system_integration.py",
    "tests/test_queen_live_location.py",
    "tests/test_uk_binance.py",
]

ROOT = os.path.dirname(os.path.abspath(__file__))
AUREON = os.path.join(ROOT, "aureon")

for dirpath, dirnames, _filenames in os.walk(AUREON):
    # Skip __pycache__ and hidden directories
    dirnames[:] = [d for d in dirnames if not d.startswith(("__pycache__", "."))]
    if dirpath not in sys.path:
        sys.path.insert(0, dirpath)

if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# Bind the two singleton-bearing legacy names to their PACKAGE modules eagerly.
# The path entries above make bare names importable, but a bare import creates
# a SECOND module instance from the same file — two bus/mycelium modules, two
# singleton slots, and (via the repo-root star-import shims) sometimes a module
# with NO slot at all, depending on which test touched sys.path first
# (measured: tests/test_whale_sonar.py AttributeError whenever an earlier
# module pushed the repo root to sys.path[0]). One module object per organ.
import aureon.core.aureon_chirp_bus as _canonical_chirp  # noqa: E402
import aureon.core.aureon_mycelium as _canonical_mycelium  # noqa: E402
import aureon.core.aureon_thought_bus as _canonical_bus  # noqa: E402
import aureon.harmonic.aureon_hft_harmonic_mycelium as _canonical_hft  # noqa: E402

sys.modules.setdefault("aureon_thought_bus", _canonical_bus)
sys.modules.setdefault("aureon_mycelium", _canonical_mycelium)
sys.modules.setdefault("aureon_chirp_bus", _canonical_chirp)
sys.modules.setdefault("aureon_hft_harmonic_mycelium", _canonical_hft)


# (module_name, attribute) pairs of process-wide singletons that leak between
# test MODULES when one module builds them and never tears them down — the
# root cause of the order-dependent failures found in the B1 triage. The bus
# module is importable under two names (bare via the sys.path shim above, and
# as the package path), and each name holds its own singleton slot, so both
# are covered. Snapshot/restore is per-module: tests inside one module keep
# their shared state; the NEXT module starts from whatever existed before.
_LEAKY_SINGLETONS = (
    ("aureon_thought_bus", "_thought_bus_instance"),
    ("aureon.core.aureon_thought_bus", "_thought_bus_instance"),
    ("aureon.observer", "_observer_singleton"),
    # The mycelium mesh: one test calling get_mycelium() cold-boots the network
    # for the whole process, and every later status read (mycelium_surface →
    # affect monitor → soul) then perceives a live mesh — a "blind" soul
    # downstream suddenly has self-perception it never built. Proven poisoner:
    # tests/test_organism_unification.py → tests/test_soul.py.
    ("aureon_mycelium", "_mycelium_instance"),
    ("aureon.core.aureon_mycelium", "_mycelium_instance"),
    # Inner-work ascent history accumulates across modules the same way.
    ("aureon.core.inner_work", "_monitor"),
)

_ASYNC_LOOP_KEY = pytest.StashKey[asyncio.AbstractEventLoop]()
_ASYNC_SOURCE_CACHE: dict[Path, bool] = {}


def _test_requires_async_loop(item) -> bool:
    test_fn = getattr(item, "obj", None)
    if test_fn is not None and inspect.iscoroutinefunction(test_fn):
        return True
    path = Path(str(getattr(item, "path", "")))
    if not path.is_file():
        return False
    cached = _ASYNC_SOURCE_CACHE.get(path)
    if cached is None:
        try:
            cached = "asyncio.run(" in path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            cached = False
        _ASYNC_SOURCE_CACHE[path] = cached
    return cached


@pytest.hookimpl(tryfirst=True)
def pytest_runtest_setup(item):
    """Create only the event-loop control socket before pytest-socket locks down."""
    if _test_requires_async_loop(item):
        item.stash[_ASYNC_LOOP_KEY] = asyncio.new_event_loop()


@pytest.fixture(autouse=True)
def _socket_blocked_asyncio_run(request, monkeypatch):
    """Run async tests on the pre-created loop while sockets stay blocked."""
    loop = request.node.stash.get(_ASYNC_LOOP_KEY, None)
    if loop is None:
        yield
        return

    def run(coroutine, *, debug=None, loop_factory=None):
        if loop_factory is not None:
            raise RuntimeError("test loop_factory is incompatible with socket isolation")
        if loop.is_running():
            raise RuntimeError("asyncio.run() cannot be called from a running event loop")
        prior_debug = loop.get_debug()
        if debug is not None:
            loop.set_debug(debug)
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(coroutine)
        finally:
            asyncio.set_event_loop(None)
            loop.set_debug(prior_debug)

    monkeypatch.setattr(asyncio, "run", run)
    yield


@pytest.hookimpl(hookwrapper=True, trylast=True)
def pytest_runtest_teardown(item, nextitem):
    yield
    loop = item.stash.get(_ASYNC_LOOP_KEY, None)
    if loop is None or loop.is_closed():
        return
    pending = tuple(asyncio.all_tasks(loop))
    for task in pending:
        task.cancel()
    if pending:
        loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
    loop.run_until_complete(loop.shutdown_asyncgens())
    loop.close()


def pytest_collection_finish(session):
    """Collection imports EVERY test module up front, and a few legacy
    script-style tests run their whole scenario at import (test_orca_quick
    builds an OrcaKillCycle → mycelium mesh; test_bot_intelligence_wiring
    builds the thought bus). Those organisms exist BEFORE the first module
    fixture snapshot, so the per-module restore below would faithfully
    preserve them for the entire run — a "blind" soul three hundred modules
    later then perceives a live mesh it never built. Clear them here so the
    session starts as clean as any single module run does."""
    for mod_name, attr in _LEAKY_SINGLETONS:
        mod = sys.modules.get(mod_name)
        if mod is not None and getattr(mod, attr, None) is not None:
            setattr(mod, attr, None)
    # Threads can't be cleared the way singleton slots can — a background
    # publisher surviving collection poisons every later test's isolated trace
    # dir (bus_trace resolves its dir per call). Name any survivor loudly so a
    # future script-style module is caught here, not three hundred modules
    # downstream.
    stray = sorted({t.name for t in threading.enumerate()
                    if t is not threading.main_thread() and t.is_alive()})
    if stray:
        sys.stderr.write(
            "\n[conftest] WARNING: background threads survived collection "
            f"(likely an import side effect in a test module): {', '.join(stray)}\n")


@pytest.fixture(autouse=True, scope="module")
def _restore_process_singletons():
    saved = []
    for mod_name, attr in _LEAKY_SINGLETONS:
        mod = sys.modules.get(mod_name)
        if mod is not None and hasattr(mod, attr):
            saved.append((mod, attr, getattr(mod, attr)))
    yield
    for mod_name, attr in _LEAKY_SINGLETONS:
        mod = sys.modules.get(mod_name)
        if mod is None or not hasattr(mod, attr):
            continue
        for smod, sattr, value in saved:
            if smod is mod and sattr == attr:
                setattr(mod, attr, value)
                break
        else:
            # the module was imported DURING this test module; clear whatever
            # singleton it created so it cannot leak forward
            setattr(mod, attr, None)


def pytest_pyfunc_call(pyfuncitem):
    """Execute native-coroutine tests with asyncio.run (fresh loop per test).

    Returning True tells pytest the call was handled; returning None lets the normal
    sync path run. If a dedicated async plugin (pytest-asyncio/anyio) is ever installed,
    it hooks earlier in the chain and this fallback simply never fires.
    """
    test_fn = pyfuncitem.obj
    if inspect.iscoroutinefunction(test_fn):
        kwargs = {name: pyfuncitem.funcargs[name]
                  for name in pyfuncitem._fixtureinfo.argnames}
        asyncio.run(test_fn(**kwargs))
        return True
    return None

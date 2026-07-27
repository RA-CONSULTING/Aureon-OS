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

import pytest

# These eight are standalone diagnostic SCRIPTS, not pytest modules: each defines
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
collect_ignore = [
    "tests/test_bot_intelligence_wiring.py",
    "tests/test_cost_basis_target.py",
    "tests/test_orca_quick.py",
    "tests/test_queen_deep_intelligence_live.py",
    "tests/test_queen_metrics.py",
    "tests/test_queens_heart.py",
    "tests/test_scout_deployment.py",
    "tests/test_windows_startup.py",
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
import aureon.core.aureon_mycelium as _canonical_mycelium  # noqa: E402
import aureon.core.aureon_thought_bus as _canonical_bus  # noqa: E402

sys.modules.setdefault("aureon_thought_bus", _canonical_bus)
sys.modules.setdefault("aureon_mycelium", _canonical_mycelium)


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

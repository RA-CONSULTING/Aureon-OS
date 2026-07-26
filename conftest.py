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

import pytest

ROOT = os.path.dirname(os.path.abspath(__file__))
AUREON = os.path.join(ROOT, "aureon")

for dirpath, dirnames, _filenames in os.walk(AUREON):
    # Skip __pycache__ and hidden directories
    dirnames[:] = [d for d in dirnames if not d.startswith(("__pycache__", "."))]
    if dirpath not in sys.path:
        sys.path.insert(0, dirpath)

if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


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

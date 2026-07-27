"""Compatibility shim for legacy import path.

Use `aureon.core.aureon_thought_bus` directly in new code.

This must be a true ALIAS, not a star-copy: the core module holds the
process-wide singleton slot (``_thought_bus_instance``), and ``import *``
cannot carry a private module global. With two module objects, whichever name
a caller imports second gets a bus module with NO singleton slot — measured
breaking tests/test_whale_sonar.py whenever an earlier test module pushed the
repo root to ``sys.path[0]`` so the bare name resolved here first. Registering
the real module object under this legacy name makes both names ONE module:
one bus, one singleton, no split-brain.
"""

import sys

import aureon.core.aureon_thought_bus as _real

sys.modules[__name__] = _real

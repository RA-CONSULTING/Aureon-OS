"""Compatibility shim for legacy import path.

Use `aureon.core.aureon_mycelium` directly in new code.

This must be a true ALIAS, not a star-copy: the core module holds the
process-wide singleton slot (``_mycelium_instance``), and ``import *`` cannot
carry a private module global. With two module objects, the two names track
two different meshes (the split-brain measured in the B5 order-dependence
hunt). Registering the real module object under this legacy name makes both
names ONE module: one mesh, one singleton.
"""

import sys

import aureon.core.aureon_mycelium as _real

sys.modules[__name__] = _real

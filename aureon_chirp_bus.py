"""Compatibility shim for legacy import path.

Use `aureon.core.aureon_chirp_bus` directly in new code.

A true ALIAS, not a star-copy: the core module holds the process-wide
singleton slot (``_chirp_bus``), and ``import *`` cannot carry a private
module global — two module objects would mean two chirp buses (the same
split-brain class measured on the thought bus in the B5 hunt). Registering
the real module object under this legacy name keeps one bus, one slot.
"""

import sys

import aureon.core.aureon_chirp_bus as _real

sys.modules[__name__] = _real

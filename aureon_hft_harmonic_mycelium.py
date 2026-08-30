"""Compatibility shim for legacy import path.

Use `aureon.harmonic.aureon_hft_harmonic_mycelium` directly in new code.

A true ALIAS, not a star-copy: the target module holds process-wide singleton
slots (``_hft_instance``, ``_hft_engine_instance``), and ``import *`` cannot
carry private module globals — two module objects would mean two engines (the
same split-brain class measured on the thought bus in the B5 hunt).
"""

import sys

import aureon.harmonic.aureon_hft_harmonic_mycelium as _real

sys.modules[__name__] = _real

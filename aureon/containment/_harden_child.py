"""Opt-in hardening child. Run with ``python -I``.

This file does not import the ``aureon`` package. ``python -I`` would not
put the checkout on ``sys.path`` in a way that imports ``aureon/__init__.py``
for a sibling loaded by file path, and the cold-boot child must not pull
the trading stack in. The parent writes the policy into the sidecar.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _load():
    path = Path(__file__).with_name("hardening.py")
    spec = importlib.util.spec_from_file_location("_aureon_containment_hardening", path)
    if spec is None or spec.loader is None:
        sys.stderr.write("hardening module is missing\n")
        return None
    module = importlib.util.module_from_spec(spec)
    # dataclasses resolves the class module through sys.modules.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def main() -> int:
    module = _load()
    if module is None:
        return 2
    return module.child_main()


if __name__ == "__main__":
    raise SystemExit(main())

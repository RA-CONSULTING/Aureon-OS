#!/usr/bin/env python3
"""GAP 2 probe: import ONE hub module in isolation and report the outcome.

Usage: python _gap2_module_probe.py <module_file.py>

Replicates the hub's import environment (radar dir on sys.path, console_utf8
shim, hivemind-deadlock pre-emption, socket default timeout) so a failure
here is a failure the hub would hit too. Side effects suppressed via env.
"""

import os
import sys
import json
import traceback
import importlib.util
from pathlib import Path

os.environ["AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS"] = "1"
os.environ["AUREON_AUDIT_MODE"] = "1"

RADAR_DIR = Path("C:/Users/user/.kimi_openclaw/workspace/aureon_radar")
sys.path.insert(0, str(RADAR_DIR))

# Same guards as unified_hub.py
import socket as _socket
_socket.setdefaulttimeout(30)

def _ensure_console_utf8() -> None:
    try:
        import aureon.utils.console_utf8  # noqa: F401
        return
    except Exception:
        pass
    shim_path = RADAR_DIR / "_console_utf8_shim.py"
    try:
        spec = importlib.util.spec_from_file_location(
            "aureon.utils.console_utf8", shim_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        sys.modules["aureon.utils.console_utf8"] = mod
    except Exception:
        pass


_ensure_console_utf8()

try:
    import aureon.strategies.probability_ultimate_intelligence as _pui
    class _Degraded:
        patterns: list = []
        accuracy: float = 0.0
    _pui.get_ultimate_intelligence = lambda *a, **k: _Degraded()
except Exception:
    pass


def main() -> int:
    target = Path(sys.argv[1]).resolve()
    name = target.stem
    try:
        spec = importlib.util.spec_from_file_location(name, target)
        mod = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = mod
        spec.loader.exec_module(mod)
        print(json.dumps({"module": name, "ok": True}))
        return 0
    except BaseException as e:
        tb = traceback.format_exc(limit=3)
        print(json.dumps({
            "module": name,
            "ok": False,
            "error": f"{type(e).__name__}: {e}",
            "tb_tail": tb.strip().splitlines()[-1] if tb.strip() else "",
        }))
        return 1


if __name__ == "__main__":
    sys.exit(main())

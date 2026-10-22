#!/usr/bin/env python3
"""GAP 2 full-load simulation: import every hub module in ONE process,
exactly as AureonModuleLoader does, with the hub's guards active.
Reports per-category load counts and every failure reason."""

import os
import sys
import json
import importlib.util
from pathlib import Path

os.environ["AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS"] = "1"
os.environ["AUREON_AUDIT_MODE"] = "1"

RADAR_DIR = Path("C:/Users/user/.kimi_openclaw/workspace/aureon_radar")
sys.path.insert(0, str(RADAR_DIR))

import socket as _socket
_socket.setdefaulttimeout(30)

def _ensure_console_utf8() -> None:
    try:
        import aureon.utils.console_utf8  # noqa: F401
        return
    except Exception:
        pass
    shim_path = RADAR_DIR / "_console_utf8_shim.py"
    spec = importlib.util.spec_from_file_location(
        "aureon.utils.console_utf8", shim_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    sys.modules["aureon.utils.console_utf8"] = mod


_ensure_console_utf8()

try:
    import aureon.strategies.probability_ultimate_intelligence as _pui
    class _Degraded:
        patterns: list = []
        accuracy: float = 0.0
    _pui.get_ultimate_intelligence = lambda *a, **k: _Degraded()
except Exception:
    pass

DIRS = {
    "scanner": RADAR_DIR / "scanners",
    "bot": RADAR_DIR / "bots",
    "analyzer": RADAR_DIR / "analyzers",
    "harmonic": RADAR_DIR / "harmonic",
    "planetary": RADAR_DIR / "planetary",
}

loaded = {}
failed = {}
for kind, d in DIRS.items():
    for f in sorted(d.glob("*.py")):
        if f.name.startswith("__"):
            continue
        try:
            spec = importlib.util.spec_from_file_location(f.stem, f)
            mod = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = mod
            spec.loader.exec_module(mod)
            loaded[f"{kind}:{f.stem}"] = True
        except BaseException as e:
            failed[f"{kind}:{f.stem}"] = f"{type(e).__name__}: {e}"

by_kind = {}
for k in loaded:
    by_kind[k.split(":")[0]] = by_kind.get(k.split(":")[0], 0) + 1
print(json.dumps({
    "loaded_total": len(loaded),
    "by_kind": by_kind,
    "failed_total": len(failed),
    "failed": failed,
}, indent=1))

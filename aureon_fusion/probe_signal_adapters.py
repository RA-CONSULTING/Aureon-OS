"""Probe: before/after the signal-adapters coercion for every loaded
harmonic:/planetary: module.

What it does, end to end:
  1. Loads every module the hub's AureonModuleLoader would load from
     aureon_radar/harmonic/ and aureon_radar/planetary/ (same file-glob +
     path-based import, with a per-module deadline on a daemon thread).
  2. For each module, probes it EXACTLY like the hub does (module-level
     scan/analyze/signal/evaluate/score/predict -> module-defined classes ->
     attribute scan) and captures the first raw result the hub would see.
     BEFORE  = the real SignalFusionEngine's verdict on that raw result:
               None -> the source is omitted from fusion (silently 0).
     AFTER   = the same engine with signal_adapters' coercion patch:
               rich objects resolve to a numeric score via the documented
               precedence; unparseable shapes stay omitted (fail-closed).
  3. Independently validates the registration-time path: the same modules
     run through adapt_modules() (SignalAdapterModule wrappers) on a third
     engine — no hub edits needed beyond the one adapt_modules() call.
  4. Prints a per-module table (raw shape | before | after | wrapper) and
     totals: loaded, object-returning, converted-to-nonzero.

Run from anywhere:
  PYTHONUTF8=1 python -m aureon_fusion.probe_signal_adapters
or:
  PYTHONUTF8=1 python aureon_fusion/probe_signal_adapters.py

THE PRECISE ONE-LINE HOOK FOR unified_hub.py (parent applies; do not edit
any probing logic). Two variants — pick ONE:

  Variant A (recommended — patches the single score chokepoint; covers
  both the module-level and class-probe call sites):

    In UnifiedTradingHub.initialize(), immediately BEFORE
    `modules = self.loader.load_all()` (unified_hub.py:819), add:

        import sys as _sys
        _sys.path.insert(0, str(RADAR_DIR.parent))  # workspace root — aureon_fusion
        import aureon_fusion.signal_adapters as _signal_adapters
        _signal_adapters.install_coercion_patch(engine_class=SignalFusionEngine)

  Variant B (registration-time wrapping — the hub's loader/prober accept
  the wrapper objects as-is):

    In the same place, instead:

        import sys as _sys
        _sys.path.insert(0, str(RADAR_DIR.parent))  # workspace root — aureon_fusion
        import aureon_fusion.signal_adapters as _signal_adapters
        ...
        modules = self.loader.load_all()
        modules = _signal_adapters.adapt_modules(modules)  # <- wrap step

    (the `...` is Variant A's insertion point; Variant B replaces the
    install_coercion_patch line with the adapt_modules call after load_all)

  Why the sys.path insert: the hub runs as a standalone script with
  cwd=aureon_radar, and aureon_fusion is only importable with the
  workspace root on sys.path.
"""

from __future__ import annotations

import importlib.util
import sys
import threading
import time
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[1]
RADAR_DIR = WORKSPACE / "aureon_radar"
for p in (str(RADAR_DIR), str(WORKSPACE)):
    if p not in sys.path:
        sys.path.insert(0, p)

import logging
logging.basicConfig(level=logging.WARNING, format="%(levelname)s | %(name)s | %(message)s")

import dataclasses

import unified_hub  # noqa: E402  (pre-emptions + real engine for ground truth)
from unified_hub import AureonModuleLoader, SignalFusionEngine, HARMONIC_DIR, PLANETARY_DIR  # noqa: E402

# Importing unified_hub attaches its stdout+file handlers to the ROOT logger
# (basicConfig force=True) — strip them so this probe cannot write lines into
# the live unified_hub.log.
_root = logging.getLogger()
for _h in list(_root.handlers):
    if getattr(_h, "_unified_hub", False):
        _root.removeHandler(_h)

import aureon_fusion.signal_adapters as sa  # noqa: E402

SYMBOL = "BTCUSD"
PRICE = 65000.0
_MODULE_LOAD_TIMEOUT = 60.0
_PROBE_TIMEOUT = 5.0  # same deadline the hub uses per module


def _load_with_deadline(path: Path):
    """Path-based import identical to AureonModuleLoader._load_module, but
    on a daemon thread with a hard deadline (import-time side effects)."""
    box = {}
    def _work():
        try:
            spec = importlib.util.spec_from_file_location(path.stem, path)
            mod = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = mod
            spec.loader.exec_module(mod)
            box["mod"] = mod
        except Exception as e:
            box["err"] = e
    t = threading.Thread(target=_work, daemon=True, name=f"load-{path.stem}")
    t.start()
    t.join(_MODULE_LOAD_TIMEOUT)
    if t.is_alive():
        return None, TimeoutError(f"import exceeded {_MODULE_LOAD_TIMEOUT:.0f}s")
    if "err" in box:
        return None, box["err"]
    return box.get("mod"), None


def _probe_raw_full(mod, symbol, price):
    """Full raw capture in the ADAPTER's probe order: module-level probe
    functions with arity fallback, then class instances (mirroring
    _probe_module_classes but returning the raw object), then the attribute
    scan (functions only — class constructors are never called; object
    returns from unnamed attrs are recorded for the inventory but are
    numeric-only surfaces in both the hub and the wrapper)."""
    import inspect as _inspect
    for method_name in SignalFusionEngine._PROBE_METHODS:
        method = getattr(mod, method_name, None)
        if not callable(method) or _inspect.iscoroutinefunction(method):
            continue
        for args in ((symbol, price), (symbol,), (price,), ()):
            try:
                result = method(*args)
            except TypeError:
                continue
            except Exception:
                break
            if result is not None:
                return result, f"fn:{method_name}{_arity_tag(args, symbol, price)}"
            break

    mod_key = getattr(mod, '__name__', str(id(mod)))
    instances = []
    for _cls_name, cls in _inspect.getmembers(mod, _inspect.isclass):
        if cls.__module__ != mod_key:
            continue
        if not any(callable(getattr(cls, m, None)) for m in SignalFusionEngine._PROBE_METHODS):
            continue
        try:
            init_src = _inspect.getsource(cls.__init__)
        except (TypeError, OSError):
            init_src = ''
        if any(tok in init_src for tok in SignalFusionEngine._INIT_RISK_TOKENS):
            continue
        try:
            instances.append(cls())
        except Exception:
            continue
    for inst in instances:
        for m in SignalFusionEngine._PROBE_METHODS:
            meth = getattr(inst, m, None)
            if not callable(meth) or _inspect.iscoroutinefunction(meth):
                continue
            for args in ((symbol, price), (symbol,), (price,), ()):
                try:
                    result = meth(*args)
                except TypeError:
                    continue
                except Exception:
                    break
                if result is not None:
                    return result, f"class:{type(inst).__name__}.{m}{_arity_tag(args, symbol, price)}"
                break

    for attr_name in dir(mod):
        if attr_name.startswith('_') or attr_name in SignalFusionEngine._NEVER_CALL:
            continue
        if attr_name in ('scan_all', 'load_all'):
            continue
        try:
            attr = getattr(mod, attr_name)
        except Exception:
            continue
        if (not callable(attr) or _inspect.isclass(attr)
                or _inspect.iscoroutinefunction(attr)):
            continue
        try:
            result = attr(symbol, price)
        except Exception:
            continue
        if result is not None and not isinstance(result, (int, float)):
            return result, f"attr-fn:{attr_name}"
    return None, None


def _arity_tag(args, symbol, price):
    return {(): "[0]", (symbol,): "[1]", (price,): "[1]", (symbol, price): "[2]"}.get(args, "")


def _classify(result) -> str:
    if result is None:
        return "none"
    if isinstance(result, bool):
        return "bool"
    if isinstance(result, (int, float)):
        return "numeric"
    if isinstance(result, str):
        return "str"
    if dataclasses.is_dataclass(result) and not isinstance(result, type):
        return f"dataclass:{type(result).__name__}"
    if isinstance(result, dict):
        return "dict"
    if isinstance(result, (list, tuple)):
        return type(result).__name__
    return f"object:{type(result).__name__}"


def _extract_with_deadline(engine, name, mod, symbol, price):
    """engine._extract_with_timeout on a hard deadline; parked on timeout."""
    box = {}
    def _work():
        try:
            box["score"] = engine._extract_with_timeout(name, mod, symbol, price)
        except Exception as e:
            box["err"] = e
    t = threading.Thread(target=_work, daemon=True, name=f"probe-{name}")
    t.start()
    t.join(_PROBE_TIMEOUT)
    if t.is_alive():
        return None, "TIMEOUT"
    if "err" in box:
        return None, f"ERR:{type(box['err']).__name__}"
    return box.get("score"), None


def main():
    print("═" * 78)
    print("SIGNAL ADAPTER PROBE — harmonic/ + planetary/ modules")
    print(f"symbol={SYMBOL} price={PRICE} probe_deadline={_PROBE_TIMEOUT}s")
    print("═" * 78)

    loader = AureonModuleLoader()
    modules = {}
    load_failures = []
    for directory, prefix in ((HARMONIC_DIR, "harmonic"), (PLANETARY_DIR, "planetary")):
        for f in sorted(directory.glob("*.py")):
            if f.name.startswith("__"):
                continue
            name = f"{prefix}:{f.stem}"
            mod, err = _load_with_deadline(f)
            if mod is None:
                load_failures.append((name, str(err)[:80]))
                continue
            modules[name] = mod
    print(f"loaded {len(modules)} modules "
          f"({len(load_failures)} failed/timed out)")
    for name, err in load_failures:
        print(f"  LOAD-FAIL {name}: {err}")

    # Phase 1 (BEFORE): the hub exactly as production runs it.
    engine_before = SignalFusionEngine({})
    # Phase 2 (AFTER): same engine class, coercion patched at the chokepoint.
    assert sa.install_coercion_patch(engine_class=SignalFusionEngine)
    engine_after = SignalFusionEngine({})
    # Phase 3 (WRAPPER): registration-time adapt_modules path.
    wrapped = sa.adapt_modules(modules)
    engine_wrapped = SignalFusionEngine(wrapped)

    rows = []
    t0 = time.time()
    for name, mod in modules.items():
        raw, surface = _probe_raw_full(mod, SYMBOL, PRICE)
        raw_kind = _classify(raw)
        before, before_err = _extract_with_deadline(
            engine_before, name, mod, SYMBOL, PRICE)
        after, after_err = _extract_with_deadline(
            engine_after, name, mod, SYMBOL, PRICE)
        wrap, wrap_err = _extract_with_deadline(
            engine_wrapped, name, wrapped[name], SYMBOL, PRICE)
        rows.append({
            "name": name, "surface": surface or "-", "raw": raw_kind,
            "before": before, "before_err": before_err,
            "after": after, "after_err": after_err, "wrap": wrap, "wrap_err": wrap_err,
        })
    probe_secs = time.time() - t0

    print()
    hdr = f"{'module':44} {'surface':40} {'raw shape':24} {'before':>8} {'after':>8} {'wrapper':>8}"
    print(hdr)
    print("-" * len(hdr))
    for r in rows:
        before_s = (f"{r['before']:+.3f}" if isinstance(r["before"], float)
                    else (r["before_err"] or "omit"))
        after_s = (f"{r['after']:+.3f}" if isinstance(r["after"], float)
                   else (r["after_err"] or "omit"))
        wrap_s = (f"{r['wrap']:+.3f}" if isinstance(r["wrap"], float)
                  else (r["wrap_err"] or "omit"))
        print(f"{r['name']:44} {r['surface']:40} {r['raw']:24} "
              f"{before_s:>8} {after_s:>8} {wrap_s:>8}")

    def is_object_kind(kind: str) -> bool:
        return kind not in ("none", "bool", "numeric") and not kind == "str"

    def is_probe_surface(surface: str) -> bool:
        # fn:/class: surfaces are coercion points (hub _coerce_score or the
        # wrapper's coerce_optional). attr-fn: surfaces are numeric-only in
        # BOTH the hub and the wrapper — objects there are never coerced.
        return surface.startswith(("fn:", "class:"))

    loaded = len(rows)
    obj_rows = [r for r in rows if is_object_kind(r["raw"])]
    obj_probe = [r for r in obj_rows if is_probe_surface(r["surface"])]
    obj_attr = [r for r in obj_rows if not is_probe_surface(r["surface"])]
    numeric_rows = [r for r in rows if r["raw"] == "numeric"]
    none_rows = [r for r in rows if r["raw"] == "none"]
    converted = [r for r in rows
                 if not isinstance(r["before"], float)
                 and isinstance(r["after"], float)]
    converted_nz = [r for r in converted
                    if isinstance(r["after"], float) and r["after"] != 0.0]
    wrapper_match = [r for r in rows
                     if (isinstance(r["after"], float) and isinstance(r["wrap"], float)
                         and abs(r["after"] - r["wrap"]) < 1e-9)
                     or (not isinstance(r["after"], float) and not isinstance(r["wrap"], float))]

    print()
    print("═" * 78)
    print("TOTALS")
    print("═" * 78)
    print(f"modules loaded                                : {loaded}")
    print(f"object via PROBE surface (fn/class) — bug set : {len(obj_probe)}")
    for r in obj_probe:
        after_s = (f"{r['after']:+.4f}" if isinstance(r["after"], float)
                   else (r["after_err"] or "omit"))
        print(f"    {r['name']:44} {r['raw']:22} -> after {after_s}")
    print(f"object via attr-fn (numeric-only by design)   : {len(obj_attr)}")
    for r in obj_attr:
        print(f"    {r['name']:44} {r['raw']:22} (never coerced)")
    print(f"numeric (already contract-clean)              : {len(numeric_rows)}")
    print(f"no probe surface / raw None (honest abstain)  : {len(none_rows)}")
    print(f"BEFORE nonzero                                : "
          f"{sum(1 for r in rows if isinstance(r['before'], float))}")
    print(f"AFTER  explicit-numeric (was omitted -> now a): {len(converted)}")
    for r in converted:
        print(f"    {r['name']:44} omit -> {r['after']:+.4f}")
    print(f"AFTER  nonzero                                : {len(converted_nz)}")
    print(f"wrapper-path agreement with patch             : {len(wrapper_match)}/{loaded}")
    print(f"probe wall time                               : {probe_secs:.1f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())

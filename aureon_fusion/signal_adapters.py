"""Signal adapters — normalization layer between the hive's object-speaking
harmonic/planetary modules and the fusion hub's numeric probe contract.

Bug context (bug-hunt 2026-09-06, silent zero-contribution): of the ~50
modules the unified hub loads from aureon_radar/harmonic/ and
aureon_radar/planetary/, only a handful expose the hub's probe contract
(scan/analyze/signal/evaluate/score/predict); most speak in rich OBJECTS —
dicts with nonstandard fields, dataclasses, namedtuples — through functions
the generic prober either never calls (wrong name/arity) or calls but
accepts only numeric returns from (the attribute scan). Wherever an object
did reach the scorer, the hub's ``SignalFusionEngine._coerce_score`` —
which understands only plain numerics, {'score': n} and
{'direction','confidence'} — mapped it to None, so the source was silently
omitted from every fusion cycle while looking "loaded". This module
deterministically extracts a numeric score from each shape, with a
documented precedence, and offers two integration mechanisms that do not
require touching unified_hub.py's probing logic (see install_coercion_patch
/ adapt_modules and the hook note in the probe script,
aureon_fusion/probe_signal_adapters.py).

Extraction precedence (deterministic — same shape, same score):
  P1  Signed scalar fields, tried in order; the first finite numeric wins:
      score, signal, value, delta, correlation, zscore, z_score, momentum,
      resonance, coherence, bias, pressure, intensity, amplitude,
      alignment, strength, weight, drift, deviation, gradient, reading,
      index, harmonic, resonance_score, field_strength, modulation,
      clustering_score.
      (A field that is itself a dict/object is recursed into, not cast.)
  P1b Module-local conventions: any field ending in "_score" (tried in
      sorted key order — deterministic when several are present).
  P2  Direction + magnitude: a ``direction``/``side``/``bias_direction``
      token ({LONG,BUY,UP,BULLISH,POSITIVE,+1,1,TRUE} -> +,
      {SHORT,SELL,DOWN,BEARISH,NEGATIVE,-1,FALSE} -> -) multiplied by the
      first finite numeric among confidence, conviction, magnitude,
      strength (default 0.5). A magnitude WITHOUT a direction is NOT a
      signal: assigning a sign would fabricate direction, so it is 0.0.
  P3  Nested containers, one level at a time (depth-limited, cycle-safe):
      result, data, output, metrics, analysis, fields, payload, report,
      summary, reading, signal_data, nested, inner, details.
  P4  dataclasses (asdict), namedtuples (_asdict), and plain objects with
      a __dict__ (vars) flatten into the same field precedence above.
      Modules, functions and types are never introspected.
  P5  Numeric strings parse; a single-element list/tuple unwraps. Anything
      else — and any shape that reaches no signal — is unparseable.

Doctrine (same as the rest of the fusion runtime):
  * fail-closed: no public function raises, and no function ever
    fabricates a nonzero value. Unparseable -> 0.0 plus a one-line
    warning naming the shape that was rejected.
  * bounded: every returned score is clamped to [-1, 1]; NaN/inf map to
    0.0 (a non-finite number must never reach the fusion sum).
  * abstain passes through: None is the modules' own honest "no signal"
    and stays None through coerce_optional / the hub patch, so the hub's
    conviction-floor / source-omission semantics are untouched.

Integration without editing unified_hub.py's probe logic — two mechanisms:
  1. install_coercion_patch(engine_class=...) — replaces the single
     chokepoint SignalFusionEngine._coerce_score (the only place probe
     results become scores; both the module-level and class-probe call
     sites flow through it) with the precedence extraction above. The
     precise hook for unified_hub.py is described in the module docstring
     of the probe script (aureon_fusion/probe_signal_adapters.py).
  2. adapt_modules(modules) + SignalAdapterModule — wraps each loaded
     module object at registration time; the hub's loader/prober already
     accepts any object exposing scan(symbol, price), so the wrapper
     needs no hub changes beyond the one adapt_modules() call. The
     wrapper mirrors the hub's probe order (module-level probe functions,
     then local classes, then attribute scan) and its safety sets
     (_NEVER_CALL, _INIT_RISK_TOKENS are duplicated here verbatim and
     must stay in sync with unified_hub.py). Two deliberate differences,
     both fail-closed: module-level probe functions get the arity
     fallback the hub only applies to classes ((symbol,price) ->
     (symbol,) -> (price,) -> ()); and the attribute scan never calls
     class constructors and never coerces object returns from unnamed
     attributes — those are not probe-contract surfaces, and empirically
     their object returns are argument-mismatch artifacts, not signals.

Import-safe: no side effects at import time, no process spawning.
"""

from __future__ import annotations

import dataclasses
import inspect
import logging
import math
from typing import Any, Dict, Optional

logger = logging.getLogger("AUREON_SIGNAL_ADAPTERS")

# ── field precedence ─────────────────────────────────────────────────────────
# P1: signed/intensity scalar fields, first finite numeric wins.
_SIGNED_FIELDS = (
    "score", "signal", "value", "delta", "correlation", "zscore", "z_score",
    "momentum", "resonance", "coherence", "bias", "pressure", "intensity",
    "amplitude", "alignment", "strength", "weight", "drift", "deviation",
    "gradient", "reading", "index", "harmonic", "resonance_score",
    "field_strength", "modulation", "clustering_score",
)

# P1b: generic fallback — any field whose name ends in "_score" is a
# module-local score convention; tried in sorted key order so the choice is
# deterministic when several are present.
def _score_suffix_fields(fields: Dict[str, Any]):
    return sorted(k for k in fields if k.endswith("_score"))

# P2: magnitude fields — only usable when a direction token is present.
_MAGNITUDE_FIELDS = ("confidence", "conviction", "magnitude", "strength")

# P2: direction tokens -> sign. Anything else unrecognized -> no sign.
_DIRECTION_POSITIVE = frozenset({
    "long", "buy", "up", "bullish", "positive", "+", "+1", "1", "true",
    "longs", "bid", "call", "calls",
})
_DIRECTION_NEGATIVE = frozenset({
    "short", "sell", "down", "bearish", "negative", "-", "-1", "false",
    "shorts", "ask", "put", "puts",
})
_DIRECTION_FIELDS = ("direction", "side", "bias_direction", "signal_direction")

# P3: container fields recursed into, one level at a time.
_NESTED_FIELDS = (
    "result", "data", "output", "metrics", "analysis", "fields", "payload",
    "report", "summary", "reading", "signal_data", "nested", "inner",
    "details",
)

_MAX_DEPTH = 4

# Probe order/safety sets — duplicated VERBATIM from unified_hub.py
# (SignalFusionEngine). The hub runs as __main__, so these cannot be
# imported from it; keep in sync with the hub.
_PROBE_METHODS = ('scan', 'analyze', 'signal', 'evaluate', 'score', 'predict')

_NEVER_CALL = frozenset({
    'main', 'run', 'start', 'stop', 'run_forever', 'run_forever_ssl',
    'main_loop', 'cli', 'entrypoint', 'launch', 'serve', 'listen', 'loop',
    'execute', 'fire', 'go', 'begin', 'boot', 'start_all', 'monitor',
    'watch', 'poll', 'spin', 'work', 'process',
    'ensure_sonar',  # per-call WhaleSonar thread spawn (thread-spam leak)
    # ORCA live monitor: must never be probed as a signal extractor;
    # calling any of these with (symbol, price) starts a position loop
    # or submits orders inside the hub process.
    'monitor_and_trade', 'run_all_test_orders', 'run_test_order',
    'run_balance_price_check', 'submit_exit_order', 'get_all_positions',
})

_INIT_RISK_TOKENS = ('place_order', 'create_order', 'execute_order',
                     'submit_order', 'orders.create', 'create_market_order',
                     'place_market', 'fire_order', 'send_order')

_CLAMP_LO, _CLAMP_HI = -1.0, 1.0


def _finite(value: Any) -> Optional[float]:
    """float(value) if it is a real finite number, else None. Bools are not
    numbers here — a bool probe result is not a signal (hub rule)."""
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        out = float(value)
    elif isinstance(value, str):
        try:
            out = float(value.strip())
        except (TypeError, ValueError):
            return None
    else:
        return None
    return out if math.isfinite(out) else None


def _clamp(value: float) -> float:
    return max(_CLAMP_LO, min(_CLAMP_HI, value))


def _flatten(obj: Any) -> Optional[Dict[str, Any]]:
    """Map an object shape to a field dict for precedence extraction, or
    None if the shape carries no fields (dataclass / namedtuple / __dict__).
    Modules, functions and types are never introspected."""
    if isinstance(obj, dict):
        return obj
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        try:
            return dataclasses.asdict(obj)
        except Exception:
            return None
    if isinstance(obj, tuple) and hasattr(obj, "_asdict"):
        try:
            return dict(obj._asdict())
        except Exception:
            return None
    if inspect.ismodule(obj) or inspect.isroutine(obj) or isinstance(obj, type):
        return None
    try:
        d = vars(obj)
    except TypeError:
        return None
    return d if isinstance(d, dict) and d else None


def _sign_of(fields: Dict[str, Any]) -> Optional[float]:
    for f in _DIRECTION_FIELDS:
        raw = fields.get(f)
        if raw is None:
            continue
        token = str(raw).strip().lower()
        if token in _DIRECTION_POSITIVE:
            return 1.0
        if token in _DIRECTION_NEGATIVE:
            return -1.0
        num = _finite(raw)
        if num is not None:
            return 1.0 if num > 0 else (-1.0 if num < 0 else None)
    return None


def _extract(result: Any, depth: int = 0, seen: Optional[set] = None) -> Optional[float]:
    """Core precedence extraction. Returns a finite score (already clamped),
    or None when the shape carries no trustworthy signal."""
    if seen is None:
        seen = set()
    if result is None or isinstance(result, bool) or depth > _MAX_DEPTH:
        return None
    if id(result) in seen:
        return None
    seen.add(id(result))

    num = _finite(result)
    if num is not None:
        return _clamp(num)

    if isinstance(result, (list, tuple)) and not hasattr(result, "_asdict"):
        # a single-element sequence unwraps; an aggregate is not a signal —
        # reducing it (mean/max) would fabricate a number the module never
        # stated.
        if len(result) == 1:
            return _extract(result[0], depth + 1, seen)
        return None

    fields = _flatten(result)
    if fields is None:
        return None

    # P1: signed scalar fields, precedence order. A field holding a nested
    # object is recursed into rather than cast.
    for f in _SIGNED_FIELDS:
        if f not in fields:
            continue
        raw = fields[f]
        num = _finite(raw)
        if num is not None:
            return _clamp(num)
        if raw is not None and not isinstance(raw, (str, bytes)):
            nested = _extract(raw, depth + 1, seen)
            if nested is not None:
                return nested

    # P1b: module-local "*_score" conventions, sorted for determinism.
    for f in _score_suffix_fields(fields):
        if f in _SIGNED_FIELDS:
            continue  # already tried above
        num = _finite(fields[f])
        if num is not None:
            return _clamp(num)

    # P2: direction + magnitude. Magnitude without direction is NOT a
    # signal (no fabricated sign).
    sign = _sign_of(fields)
    if sign is not None:
        mag = None
        for f in _MAGNITUDE_FIELDS:
            if f in fields:
                mag = _finite(fields[f])
                if mag is not None:
                    break
        if mag is None:
            mag = 0.5  # hub default for a bare direction verdict
        return _clamp(sign * abs(mag))

    # P3: recurse into conventional container fields.
    for f in _NESTED_FIELDS:
        raw = fields.get(f)
        if raw is None or isinstance(raw, (str, bytes)):
            continue
        nested = _extract(raw, depth + 1, seen)
        if nested is not None:
            return nested

    return None


def _describe(result: Any) -> str:
    if result is None:
        return "None"
    if dataclasses.is_dataclass(result) and not isinstance(result, type):
        return f"dataclass {type(result).__name__}"
    if isinstance(result, dict):
        keys = ", ".join(list(result.keys())[:6])
        return f"dict{{{keys}}}"
    return type(result).__name__


def _warn_unparseable(result: Any, where: str) -> None:
    logger.warning(
        f"{where}: unparseable probe result ({_describe(result)}) — "
        f"contributing 0.0 (fail-closed)")


def coerce_score(result: Any) -> float:
    """Hub-contract coercion: ANY probe result -> float in [-1, 1].

    None and unparseable shapes -> 0.0 with a one-line warning; NaN/inf ->
    0.0. Never raises, never fabricates a nonzero value.
    """
    if result is None:
        return 0.0
    score = _extract(result)
    if score is None:
        _warn_unparseable(result, "coerce_score")
        return 0.0
    if not math.isfinite(score):
        _warn_unparseable(result, "coerce_score(non-finite)")
        return 0.0
    return _clamp(score)


def coerce_optional(result: Any) -> Optional[float]:
    """Adapter/wrapper variant: None (honest module abstain) passes through
    as None so the hub omits the source; unparseable non-None shapes are
    also None (omitted) but warned — the wrapper must not invent a score
    where the module stated none."""
    if result is None:
        return None
    score = _extract(result)
    if score is None:
        _warn_unparseable(result, "coerce_optional")
        return None
    if not math.isfinite(score):
        _warn_unparseable(result, "coerce_optional(non-finite)")
        return None
    return _clamp(score)


def coerce_probe_result(result: Any) -> Optional[float]:
    """Drop-in replacement for SignalFusionEngine._coerce_score.

    A strict superset of the hub's original mapping (plain numerics,
    {'score': n}, {'direction','confidence'} all resolve identically);
    rich objects resolve via the documented precedence. Anything that
    carries no signal returns None, exactly like the original — so the
    hub's omission / conviction-floor semantics are preserved.
    """
    import inspect as _inspect
    if _inspect.iscoroutine(result) or isinstance(result, bool):
        return None
    if result is None:
        return None
    if isinstance(result, (int, float)):
        try:
            v = float(result)
        except (TypeError, ValueError):
            return None
        return _clamp(v) if math.isfinite(v) else None
    score = _extract(result)
    if score is None:
        _warn_unparseable(result, "coerce_probe_result")
    return score


def install_coercion_patch(engine_class: Optional[type] = None) -> bool:
    """Route every hub probe result through coerce_probe_result by replacing
    the single chokepoint SignalFusionEngine._coerce_score (both the
    module-level and the class-probe call sites flow through it).

    engine_class: pass SignalFusionEngine explicitly when patching from
    inside unified_hub.py (the hub runs as __main__, so this module cannot
    import it). When omitted, tries sys.modules['unified_hub'] and
    __main__. Returns True when a class was patched.
    """
    if engine_class is None:
        import sys
        candidate = sys.modules.get('unified_hub')
        if candidate is None:
            candidate = sys.modules.get('__main__')
        engine_class = getattr(candidate, 'SignalFusionEngine', None)
    if engine_class is None:
        logger.warning(
            "install_coercion_patch: SignalFusionEngine not found — "
            "pass engine_class explicitly (hub runs as __main__)")
        return False
    engine_class._coerce_score = staticmethod(coerce_probe_result)
    logger.info(
        f"signal_adapters: coercion patch installed on "
        f"{engine_class.__module__}.{engine_class.__name__}._coerce_score")
    return True


class SignalAdapterModule:
    """Registration-time wrapper: presents a loaded harmonic/planetary
    module as a clean scan(symbol, price) -> Optional[float] surface the
    hub's prober already accepts. Probing mirrors SignalFusionEngine's
    order (module-level probe functions, then module-defined classes with
    cached instances, then the attribute scan) and its safety sets.
    Unparseable probe results are omitted (None), never fabricated.
    """

    def __init__(self, wrapped: Any, name: str = "module"):
        self._wrapped = wrapped
        self._name = name
        self._instances: Optional[list] = None

    def __repr__(self) -> str:  # keep hub logs readable
        return f"<SignalAdapterModule {self._name}>"

    def scan(self, symbol: str, price: float) -> Optional[float]:
        return self._probe(symbol, price)

    # alias so a `scan`-less module probed via `analyze` still resolves
    analyze = scan

    def _probe(self, symbol: str, price: float) -> Optional[float]:
        mod = self._wrapped
        # Module-level probe functions. The hub only tries (symbol, price);
        # the wrapper is arity-tolerant (same fallback the hub's class probe
        # already uses) so probe-named functions with narrower signatures are
        # reachable too.
        for method_name in _PROBE_METHODS:
            method = getattr(mod, method_name, None)
            if not callable(method) or inspect.iscoroutinefunction(method):
                continue
            for args in ((symbol, price), (symbol,), (price,), ()):
                try:
                    result = method(*args)
                except TypeError:
                    continue  # wrong arity — try a narrower call
                except Exception:
                    break     # method itself failed — next method
                score = coerce_optional(result)
                if score is not None:
                    return score
                break  # ran fine but produced no score — next method

        score = self._probe_classes(symbol, price)
        if score is not None:
            return score

        # Attribute scan — mirrors the hub's fallback (numeric results only,
        # same _NEVER_CALL set) with one deliberate difference: class
        # constructors are NOT called. The hub calls them with (symbol,
        # price) and discards the instance; doing so is a side effect with
        # zero scoring value. Object returns from unnamed attributes are
        # likewise never coerced: they are not probe-contract surfaces, and
        # empirically they are argument-mismatch artifacts (e.g. a packet
        # encoder that received the price as its message-type field) — a
        # number extracted from those shapes would be fabricated, not
        # measured. Coercion applies only at probe-named surfaces.
        for attr_name in dir(mod):
            if attr_name.startswith('_') or attr_name in _NEVER_CALL:
                continue
            if attr_name in ('scan_all', 'load_all'):
                continue
            try:
                attr = getattr(mod, attr_name)
            except Exception:
                continue
            if (not callable(attr) or inspect.isclass(attr)
                    or inspect.iscoroutinefunction(attr)):
                continue
            try:
                result = attr(symbol, price)
            except Exception:
                continue
            num = _finite(result)
            if num is not None:
                return _clamp(num)
        return None

    def _probe_classes(self, symbol: str, price: float) -> Optional[float]:
        mod = self._wrapped
        if self._instances is None:
            instances = []
            mod_key = getattr(mod, '__name__', str(id(mod)))
            for cls_name, cls in inspect.getmembers(mod, inspect.isclass):
                if cls.__module__ != mod_key:
                    continue  # imported class, not defined by this module
                if not any(callable(getattr(cls, m, None)) for m in _PROBE_METHODS):
                    continue
                try:
                    init_src = inspect.getsource(cls.__init__)
                except (TypeError, OSError):
                    init_src = ''
                if any(tok in init_src for tok in _INIT_RISK_TOKENS):
                    continue
                try:
                    instances.append(cls())
                except Exception:
                    continue
            self._instances = instances

        for inst in self._instances:
            for m in _PROBE_METHODS:
                meth = getattr(inst, m, None)
                if not callable(meth) or inspect.iscoroutinefunction(meth):
                    continue
                for args in ((symbol, price), (symbol,), (price,), ()):
                    try:
                        result = meth(*args)
                    except TypeError:
                        continue  # wrong arity — try a narrower call
                    except Exception:
                        break     # method itself failed — next method
                    score = coerce_optional(result)
                    if score is not None:
                        return score
                    break  # ran fine but produced no score — next method
        return None


def adapt_modules(modules: Dict[str, Any],
                  prefixes: tuple = ("harmonic:", "planetary:")) -> Dict[str, Any]:
    """Wrap every loaded module under the given hub-key prefixes in a
    SignalAdapterModule. Registration-time integration: the hub's loader
    and prober accept the wrapper as-is. Idempotent — already-wrapped
    modules and other categories pass through untouched.
    """
    out: Dict[str, Any] = {}
    for name, mod in modules.items():
        if name.startswith(prefixes) and not isinstance(mod, SignalAdapterModule):
            out[name] = SignalAdapterModule(mod, name)
        else:
            out[name] = mod
    return out

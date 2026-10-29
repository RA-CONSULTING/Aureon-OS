"""Run one inventoried call in this process. The parent kills the process group on timeout."""

from __future__ import annotations

import importlib
import inspect
import json
import sys
from datetime import date
from pathlib import Path
from typing import Any


def _plain(value: Any, depth: int = 0) -> Any:
    if depth > 4:
        return type(value).__name__
    if value is None or isinstance(value, (str, int, float, bool)):
        if isinstance(value, float) and value != value:
            return None
        if isinstance(value, str):
            return value[:500]
        return value
    if isinstance(value, dict):
        return {str(key): _plain(item, depth + 1) for key, item in list(value.items())[:30]}
    if isinstance(value, (list, tuple)):
        return [_plain(item, depth + 1) for item in list(value)[:30]]
    if hasattr(value, "to_dict") and callable(value.to_dict):
        try:
            return _plain(value.to_dict(), depth + 1)
        except Exception:
            pass
    if hasattr(value, "__dict__") and not isinstance(value, type):
        fields = {key: item for key, item in vars(value).items() if not str(key).startswith("_")}
        return {"type": type(value).__name__, "fields": _plain(fields, depth + 1)}
    return {"type": type(value).__name__}


def _coerce(fn: Any, kwargs: dict[str, Any]) -> dict[str, Any]:
    try:
        signature = inspect.signature(fn)
    except (TypeError, ValueError):
        return kwargs
    coerced = dict(kwargs)
    for name, value in list(coerced.items()):
        param = signature.parameters.get(name)
        if param is None:
            continue
        annotation = param.annotation
        origin = getattr(annotation, "__origin__", None)
        name_of = annotation if isinstance(annotation, str) else getattr(annotation, "__name__", "")
        if (annotation is date or name_of == "date" or str(name_of).endswith("date")) and isinstance(value, str):
            coerced[name] = date.fromisoformat(value)
        elif (annotation is frozenset or origin is frozenset) and isinstance(value, list):
            coerced[name] = frozenset(value)
    return coerced


def _load(dotted: str, module_rel: str) -> Any:
    from aureon_public.guard_loader import PINNED_COMMIT, apply_space_guard
    from aureon_public.paths import repo_root
    from aureon_public.pin_blob import load_checkout_module

    apply_space_guard()
    root = repo_root()
    path = root / module_rel if module_rel.startswith("unified_margin_trader/") else root / "aureon" / module_rel
    spec = importlib.util.find_spec(dotted)
    origin = getattr(spec, "origin", None) if spec is not None else None
    from_checkout = True
    if origin:
        origin_path = Path(origin)
        root_resolved = root.resolve()
        resolved = origin_path.resolve()
        if origin_path.is_file() and resolved != root_resolved and root_resolved not in resolved.parents:
            from_checkout = False
    if from_checkout:
        loaded, error = load_checkout_module(dotted, path, root, PINNED_COMMIT)
        if error or loaded is None:
            raise RuntimeError(error or f"{path.name} could not be loaded")
        return loaded
    return importlib.import_module(dotted)


def _call(dotted: str, symbol: str, arguments: dict[str, Any], module_rel: str) -> Any:
    imported = _load(dotted, module_rel)
    if "." not in symbol:
        fn = getattr(imported, symbol)
        return fn(**_coerce(fn, arguments))
    class_name, method_name = symbol.rsplit(".", 1)
    cls = getattr(imported, class_name)
    init_args = arguments.get("init") if isinstance(arguments.get("init"), dict) else {}
    method_args = {key: value for key, value in arguments.items() if key != "init"}
    signature = inspect.signature(cls.__init__)
    parameters = [name for name in signature.parameters if name != "self"]
    init_args = {key: value for key, value in init_args.items() if key in parameters}
    instance = cls(**_coerce(cls.__init__, init_args))
    method = getattr(instance, method_name)
    return method(**_coerce(method, method_args))


def main() -> None:
    real_stdout = sys.stdout
    sys.stdout = sys.stderr
    try:
        job = json.loads(sys.stdin.read() or "{}")
        result = _call(
            str(job["dotted"]),
            str(job["symbol"]),
            dict(job.get("arguments") or {}),
            str(job["module"]),
        )
        payload = {"ok": True, "result": _plain(result)}
    except SystemExit:
        payload = {"ok": False, "error": "SystemExit"}
    except Exception as exc:
        payload = {"ok": False, "error": f"{type(exc).__name__}: {exc}"[:240]}
    sys.stdout = real_stdout
    real_stdout.write(json.dumps(payload))


if __name__ == "__main__":
    main()

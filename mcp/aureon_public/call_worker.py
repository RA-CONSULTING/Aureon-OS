"""Run one inventoried call in this process. The parent kills the process group on timeout."""

from __future__ import annotations

import inspect
import json
import os
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


def _inventory_path(cls: type) -> str:
    """Inventory module path for a class. ``aureon.`` is the package prefix."""

    module = cls.__module__
    if module.startswith("aureon."):
        module = module[len("aureon.") :]
    return module.replace(".", "/") + ".py"


def _post_init_defined(cls: type) -> bool:
    """True when ``__post_init__`` is defined anywhere on the class MRO."""

    return any("__post_init__" in base.__dict__ for base in cls.__mro__)


def _dataclass_from_dict(fn: Any, annotation: Any, value: Any) -> Any | None:
    """Build an allowlisted dataclass from a JSON object.

    The class is resolved from the annotation, including a name in the
    function's globals, then checked by its own module. A class from another
    package is not built unless that class is on ``_CONSTRUCTOR_ALLOWLIST``.

    A generated dataclass ``__init__`` has code filename ``<string>`` and
    still calls ``__post_init__``. Any class that defines ``__post_init__``
    on its MRO is refused and is not constructed.
    """

    if not isinstance(value, dict):
        return None
    cls = annotation
    if isinstance(annotation, str):
        cls = fn.__globals__.get(annotation) or fn.__globals__.get(annotation.split(".")[-1])
    if not isinstance(cls, type) or not hasattr(cls, "__dataclass_fields__"):
        return None
    code = getattr(getattr(cls, "__init__", None), "__code__", None)
    if code is None or code.co_filename != "<string>":
        return None
    from aureon_public.body import _CONSTRUCTOR_ALLOWLIST

    if (_inventory_path(cls), cls.__name__) not in _CONSTRUCTOR_ALLOWLIST:
        return None
    if _post_init_defined(cls):
        return None
    if not set(value).issubset(cls.__dataclass_fields__):
        return None
    return cls(**value)


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
        else:
            built = _dataclass_from_dict(fn, annotation, value)
            if built is not None:
                coerced[name] = built
    return coerced


def _drop_checkout_root() -> None:
    """The Space guard puts the checkout on sys.path. The worker must not keep it."""

    from aureon_public.paths import repo_root

    root = repo_root().resolve()
    kept: list[str] = []
    for entry in sys.path:
        if not entry:
            continue
        try:
            if Path(entry).resolve() == root:
                continue
        except OSError:
            kept.append(entry)
            continue
        kept.append(entry)
    sys.path[:] = kept


def _load(dotted: str, module_rel: str) -> Any:
    del module_rel
    if dotted != "aureon" and not dotted.startswith("aureon."):
        raise RuntimeError("only an aureon module can be loaded")
    from aureon_public.guard_loader import apply_space_guard
    from aureon_public.pin_blob import (
        import_through_finder,
        install_pinned_aureon_finder,
        refuse_preseeded_aureon,
    )

    install_pinned_aureon_finder()
    apply_space_guard()
    _drop_checkout_root()
    refuse_preseeded_aureon()
    return import_through_finder(dotted)


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


_SWEEP_SOCKETS: list[str] = []


def _install_sweep_guard() -> None:
    """Block and log connections. Used only while the call sweep is measuring."""

    if os.environ.get("AUREON_PUBLIC_SWEEP") != "1":
        return
    import socket

    class _Guard(socket.socket):
        def connect(self, address: object, *args: object, **kwargs: object) -> None:
            _SWEEP_SOCKETS.append(str(address)[:160])
            raise OSError("socket blocked")

        def connect_ex(self, address: object, *args: object, **kwargs: object) -> int:
            _SWEEP_SOCKETS.append(str(address)[:160])
            raise OSError("socket blocked")

    def _create_connection(*args: object, **kwargs: object) -> object:
        _SWEEP_SOCKETS.append("create_connection")
        raise OSError("socket blocked")

    socket.socket = _Guard  # type: ignore[misc]
    socket.create_connection = _create_connection  # type: ignore[assignment]


def _sweep_modules() -> list[str]:
    from aureon_public.stage2_import_sweep import is_http_client

    banned = []
    for name in sys.modules:
        if any(marker in name for marker in ("inhouse_ai", "ollama_config")):
            banned.append(name)
            continue
        if name in {"aureon.queen", "aureon.miner", "aureon.swarm_motion"} or name.startswith(
            ("aureon.queen.", "aureon.miner.", "aureon.swarm_motion.")
        ):
            banned.append(name)
            continue
        if is_http_client(name):
            banned.append(name)
    return sorted(banned)


def main() -> None:
    _install_sweep_guard()
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
    if os.environ.get("AUREON_PUBLIC_REPORT_MODULES") == "1":
        payload["modules"] = sorted(
            name
            for name in sys.modules
            if "inhouse_ai" in name or "ollama_config" in name
        )
    if os.environ.get("AUREON_PUBLIC_SWEEP") == "1":
        payload["sweep"] = {"modules": _sweep_modules(), "sockets": list(_SWEEP_SOCKETS)}
    sys.stdout = real_stdout
    real_stdout.write(json.dumps(payload))


if __name__ == "__main__":
    main()

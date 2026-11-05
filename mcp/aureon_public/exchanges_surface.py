"""Read-gated public surface for the exchanges inventory.

Stage 8 owns this slice only. The tools read ``docs/mcp/inventory.json``.
They do not import ``aureon.exchanges``, do not open a socket, and do not
place an order. The Charlie gate is HOLD. Live orders stay refused. An
environment variable cannot select EXECUTE.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import tempfile
from pathlib import Path
from typing import Any, Mapping

from aureon_public.body import (
    ENABLED_THROUGH,
    INVENTORY_SHA256,
    OPEN_PLAN_THROUGH,
    _inventory,
    body_call,
    body_call_operator,
    body_surface,
    lookup,
    public_entry_refusal,
)
from aureon_public.guard_loader import PINNED_COMMIT
from aureon_public.quiet import quiet
from aureon_public.tools import _dumps

_READ_ACTIONS = {"", "READ", "HOLD"}
_SENSITIVE_NAME = re.compile(r"(KEY|SECRET|TOKEN|PASSWORD|CREDENTIAL|PRIVATE)", re.I)
_BLOCKED_IMPORTS = (
    "aureon.exchanges",
    "aureon.trading",
    "aureon.bots",
    "aureon.bots_intelligence",
    "aureon.bridges",
    "aureon.scanners",
    "unified_margin_trader",
)
SCHEMA = "aureon.go-live.exchanges-read-surface.v1"
PLANTED_SECRETS = {
    "BINANCE_API_SECRET": "planted-exchanges-surface-binance-secret",
    "KRAKEN_API_KEY": "planted-exchanges-surface-kraken-key",
    "KRAKEN_API_SECRET": "planted-exchanges-surface-kraken-secret",
}


def _truthy(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "y", "on"}


def _falsey(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"0", "false", "no", "n", "off"}


def gate_view(environ: Mapping[str, str] | None = None) -> dict[str, Any]:
    """Charlie HOLD gate. The surface default is live orders off.

    Unset ``AUREON_DISABLE_REAL_ORDERS`` stays off. ``0`` and
    ``AUREON_LIVE_TRADING=1`` are ignored. EXECUTE is not selectable.
    """

    env = os.environ if environ is None else environ
    raw_orders = env.get("AUREON_DISABLE_REAL_ORDERS")
    explicit_live = (raw_orders is not None and _falsey(raw_orders)) or _truthy(
        env.get("AUREON_LIVE_TRADING")
    )
    return {
        "called": False,
        "decision": "HOLD",
        "env_selects_execute": False,
        "execute": "refused",
        "explicit_live_request_ignored": explicit_live,
        "imported": False,
        "live_orders": "refused",
        "read_gated": True,
        "real_orders_default": "off",
    }


def _sensitive_values(environ: Mapping[str, str] | None = None) -> set[str]:
    env = os.environ if environ is None else environ
    found: set[str] = set()
    for name, value in env.items():
        if len(value) < 12 or not _SENSITIVE_NAME.search(name):
            continue
        found.add(value)
    return found


def _is_secret(value: str, environ: Mapping[str, str] | None = None) -> bool:
    if not value:
        return False
    return value in _sensitive_values(environ)


def _leaked(text: str, environ: Mapping[str, str] | None = None) -> bool:
    return any(secret in text for secret in _sensitive_values(environ))


def _emit(payload: dict[str, Any]) -> str:
    body = {**gate_view(), **payload}
    body.setdefault("provenance", "cited")
    text = _dumps(body)
    if _leaked(text):
        withheld = {
            **gate_view(),
            "label": "cited. Response withheld.",
            "provenance": "cited",
            "reason": "response withheld",
            "status": "unavailable",
        }
        text = _dumps(withheld)
        if _leaked(text):
            return (
                '{"called":false,"decision":"HOLD","execute":"refused",'
                '"live_orders":"refused","read_gated":true,'
                '"reason":"response withheld","status":"unavailable"}'
            )
    return text


def _exchange_rows() -> list[dict[str, Any]]:
    rows, _index = _inventory()
    return [row for row in rows if row.get("package") == "exchanges"]


def catalog_facts() -> dict[str, Any]:
    """Counts from the inventory. No exchange module is imported."""

    rows = _exchange_rows()
    kinds: dict[str, int] = {}
    modules: set[str] = set()
    reachable = 0
    for row in rows:
        kind = str(row.get("kind") or "")
        kinds[kind] = kinds.get(kind, 0) + 1
        modules.add(str(row.get("module") or ""))
        if kind in {"function", "method"} and public_entry_refusal(row) is None:
            reachable += 1
    return {
        "kinds": dict(sorted(kinds.items())),
        "modules": len(modules),
        "reachable": reachable,
        "rows": len(rows),
    }


def _row_view(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "form": row.get("form"),
        "kind": row.get("kind"),
        "module": row.get("module"),
        "package": "exchanges",
        "safety": row.get("safety"),
        "server": row.get("server"),
        "stage": row.get("stage"),
        "symbol": row.get("symbol"),
    }


@quiet
def exchanges_gate() -> str:
    """Charlie HOLD/EXECUTE gate for the exchanges surface. Provenance: cited.

    The decision is HOLD. Live orders stay refused. EXECUTE is refused.
    This tool does not import aureon.exchanges and does not read keys.

    Args:
        none: This tool takes no inputs. Label: cited, the gate.
    """

    return _emit(
        {
            "enabled_through": ENABLED_THROUGH,
            "label": "cited. Exchanges gate is HOLD. No exchange module was imported.",
            "open_plan_through": OPEN_PLAN_THROUGH,
            "package": "exchanges",
            "pin": PINNED_COMMIT,
            "status": "cited",
        }
    )


@quiet
def exchanges_surface(module: str = "", symbol: str = "", action: str = "READ") -> str:
    """Read the exchanges inventory. Provenance: cited.

    An empty module and symbol returns catalog counts. A module without a
    symbol lists that module's symbols. Both name one row. Nothing is
    imported and nothing is called. Keys are not read. EXECUTE is refused.

    Args:
        module: Inventory path under exchanges/. Empty returns counts. Label: cited.
        symbol: Inventory symbol. Empty lists the module. Label: cited.
        action: READ or HOLD. Any other action is refused. Label: cited.
    """

    if _is_secret(module) or _is_secret(symbol) or _is_secret(action):
        return _emit(
            {
                "label": "cited. Argument withheld.",
                "reason": "argument is not an inventory id",
                "status": "unavailable",
            }
        )
    chosen = action.strip().upper()
    if chosen not in _READ_ACTIONS:
        return _emit(
            {
                "label": "cited. EXECUTE is refused. No exchange function ran.",
                "reason": "EXECUTE is refused on the exchanges read surface",
                "status": "unavailable",
            }
        )
    if not module and not symbol:
        facts = catalog_facts()
        return _emit(
            {
                "catalog": facts,
                "label": "cited. Read-gated exchanges catalog. No exchange module was imported.",
                "package": "exchanges",
                "status": "cited",
            }
        )
    if not module.startswith("exchanges/") or ".." in module or module.startswith("/"):
        return _emit(
            {
                "label": "cited. Not an exchanges inventory module.",
                "reason": "module is outside the exchanges inventory",
                "status": "unavailable",
            }
        )
    if not symbol:
        rows = [row for row in _exchange_rows() if row.get("module") == module]
        if not rows:
            return _emit(
                {
                    "label": "cited. Module is not in the exchanges inventory.",
                    "reason": "module is not in the exchanges inventory",
                    "status": "unavailable",
                }
            )
        names = [str(row["symbol"]) for row in rows]
        return _emit(
            {
                "label": "cited. Module surface only. No symbol was called.",
                "module": module,
                "shown": names[:40],
                "status": "cited",
                "symbols": len(names),
            }
        )
    row = lookup(module, symbol)
    if row is None or row.get("package") != "exchanges":
        return _emit(
            {
                "label": "cited. Symbol is not in the exchanges inventory.",
                "reason": "symbol is not in the exchanges inventory",
                "status": "unavailable",
            }
        )
    return _emit(
        {
            "label": "cited. Inventory row only. The entry point was not called.",
            "row": _row_view(row),
            "status": "cited",
        }
    )


@quiet
def exchanges_surface_resource() -> str:
    """Exchanges catalog resource. Provenance: cited.

    Counts and the HOLD gate. No exchange module is imported.
    """

    facts = catalog_facts()
    return _emit(
        {
            "catalog": facts,
            "label": "cited. aureon://exchanges/surface. No exchange module was imported.",
            "package": "exchanges",
            "status": "cited",
        }
    )


class _ImportProbe:
    def __init__(self) -> None:
        self.attempts: list[str] = []

    def find_spec(self, fullname: str, path: object = None, target: object = None) -> None:
        del path, target
        for prefix in _BLOCKED_IMPORTS:
            if fullname == prefix or fullname.startswith(prefix + "."):
                if fullname not in self.attempts:
                    self.attempts.append(fullname)
                raise ImportError("stage 8 exchanges surface refused this import")
        return None


def _load_json(text: str) -> dict[str, Any]:
    loaded = json.loads(text)
    if not isinstance(loaded, dict):
        raise RuntimeError("surface did not return an object")
    return loaded


def _freeze_source() -> dict[str, str]:
    """Resolve aureon_source once, before the socket guard blocks git."""

    import aureon_public.guard_loader as guard_loader
    import aureon_public.tools as tools

    frozen = dict(guard_loader.aureon_source())

    def cached() -> dict[str, str]:
        return dict(frozen)

    guard_loader.aureon_source = cached  # type: ignore[method-assign]
    tools.aureon_source = cached  # type: ignore[method-assign]
    return frozen


def guarded_sweep() -> dict[str, Any]:
    """Call every exchanges row under the socket and import guard.

    ``aureon_source`` is frozen first. That checkout lookup runs ``git
    rev-parse HEAD`` and is not an exchange call. The guard window starts
    after it. Live-order flags in the environment are ignored.
    """

    from aureon_public.sweep_guard import install_sweep_guard, snapshot

    source = _freeze_source()
    sandbox = Path(tempfile.mkdtemp(prefix="aureon-exchanges-sweep-"))
    os.environ["AUREON_PUBLIC_SANDBOX"] = str(sandbox)
    os.environ["TMPDIR"] = str(sandbox)
    probe = _ImportProbe()
    sys.meta_path.insert(0, probe)
    install_sweep_guard()
    rows = sorted(_exchange_rows(), key=lambda item: (str(item["module"]), str(item["symbol"])))
    entries: list[dict[str, Any]] = []
    for row in rows:
        module = str(row["module"])
        symbol = str(row["symbol"])
        public = _load_json(body_call(module, symbol))
        operator = _load_json(body_call_operator(module, symbol))
        surface_only = _load_json(body_surface(module, symbol))
        read = _load_json(exchanges_surface(module, symbol))
        entries.append(
            {
                "body_surface_called": surface_only.get("called") is True,
                "body_surface_reason": surface_only.get("reason"),
                "called": read.get("called") is True or public.get("called") is True,
                "decision": read.get("decision"),
                "execute": read.get("execute"),
                "imported": read.get("imported") is True,
                "kind": row.get("kind"),
                "live_orders": public.get("live_orders"),
                "module": module,
                "operator_live_orders": operator.get("live_orders"),
                "operator_reason": operator.get("reason"),
                "public_reason": public.get("reason"),
                "safety": row.get("safety"),
                "surface_status": read.get("status"),
                "symbol": symbol,
            }
        )
    sample = rows[0]
    execute_probe = _load_json(
        exchanges_surface(str(sample["module"]), str(sample["symbol"]), action="EXECUTE")
    )
    catalog = _load_json(exchanges_surface())
    gate = _load_json(exchanges_gate())
    guard = snapshot()
    encoded = json.dumps(entries, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    facts = catalog_facts()
    report = {
        "aureon_source": source,
        "aureon_source_frozen_before_guard": True,
        "badge": "unchanged",
        "called": sum(1 for item in entries if item["called"]),
        "catalog": facts,
        "catalog_status": catalog.get("status"),
        "decision": "HOLD",
        "enabled_through": ENABLED_THROUGH,
        "entries": entries,
        "entries_sha256": hashlib.sha256(encoded.encode("utf-8")).hexdigest(),
        "execute": "refused",
        "execute_probe": {
            "called": execute_probe.get("called") is True,
            "decision": execute_probe.get("decision"),
            "execute": execute_probe.get("execute"),
            "live_orders": execute_probe.get("live_orders"),
            "reason": execute_probe.get("reason"),
            "status": execute_probe.get("status"),
        },
        "explicit_live_request_ignored": gate.get("explicit_live_request_ignored"),
        "gate_decision": gate.get("decision"),
        "go_live_clear": False,
        "guard": {
            "import_attempts": list(probe.attempts),
            "processes": list(guard["processes"]),
            "sockets": list(guard["sockets"]),
            "writes": list(guard["writes"]),
        },
        "imported_modules": sorted(
            name for name in sys.modules if name == "aureon.exchanges" or name.startswith("aureon.exchanges.")
        ),
        "imports_performed": len(probe.attempts),
        "inventory_sha256": INVENTORY_SHA256,
        "key_leak": False,
        "live_orders": "refused",
        "open_plan_through": OPEN_PLAN_THROUGH,
        "package": "exchanges",
        "pin": PINNED_COMMIT,
        "pin_moved": False,
        "planted_secret_names": sorted(PLANTED_SECRETS),
        "published": False,
        "reachable": facts["reachable"],
        "read_gated": True,
        "real_orders_default": "off",
        "rows": len(entries),
        "schema": SCHEMA,
        "slice": "exchanges",
        "stage": 8,
    }
    text = json.dumps(report, sort_keys=True)
    if _leaked(text):
        report["key_leak"] = True
    return report


def sweep_ok(report: dict[str, Any]) -> str | None:
    """None when the report is a closed read-gated sweep. Otherwise the gap."""

    if report.get("schema") != SCHEMA or report.get("stage") != 8:
        return "schema"
    if report.get("decision") != "HOLD" or report.get("execute") != "refused":
        return "gate"
    if report.get("live_orders") != "refused" or report.get("read_gated") is not True:
        return "read gate"
    if report.get("real_orders_default") != "off":
        return "live orders default"
    if report.get("go_live_clear") is not False or report.get("published") is not False:
        return "publish"
    if report.get("pin") != PINNED_COMMIT or report.get("pin_moved") is not False:
        return "pin"
    if report.get("badge") != "unchanged":
        return "badge"
    if report.get("open_plan_through") != 2 or report.get("enabled_through") != 6:
        return "stage fence"
    if report.get("key_leak") is not False:
        return "key leak"
    if report.get("explicit_live_request_ignored") is not True:
        return "live request"
    if report.get("called") != 0 or report.get("reachable") != 0 or report.get("imports_performed") != 0:
        return "call or import"
    if report.get("rows") != 647:
        return "row count"
    catalog = report.get("catalog") or {}
    if catalog.get("modules") != 43 or catalog.get("rows") != 647 or catalog.get("reachable") != 0:
        return "catalog"
    if catalog.get("kinds") != {"class": 85, "function": 75, "method": 444, "module": 43}:
        return "kinds"
    if report.get("imported_modules"):
        return "imported module"
    guard = report.get("guard") or {}
    if guard.get("sockets") or guard.get("processes") or guard.get("writes") or guard.get("import_attempts"):
        return "guard"
    probe = report.get("execute_probe") or {}
    if probe.get("called") is not False or probe.get("decision") != "HOLD" or probe.get("execute") != "refused":
        return "execute probe"
    if probe.get("live_orders") != "refused":
        return "execute probe orders"
    if probe.get("reason") != "EXECUTE is refused on the exchanges read surface":
        return "execute probe reason"
    entries = report.get("entries")
    if not isinstance(entries, list) or len(entries) != report.get("rows"):
        return "rows"
    for item in entries:
        if item.get("called") is not False or item.get("imported") is not False:
            return "entry called"
        if item.get("decision") != "HOLD" or item.get("execute") != "refused":
            return "entry gate"
        if item.get("live_orders") != "refused" or item.get("operator_live_orders") != "refused":
            return "entry orders"
        if item.get("public_reason") != "operator entry point is not on aureon-public":
            return "public reason"
        if item.get("operator_reason") != "operator row is not allowlisted":
            return "operator reason"
        if item.get("body_surface_called") is not False:
            return "body surface"
        if item.get("surface_status") != "cited":
            return "surface status"
        if not str(item.get("module") or "").startswith("exchanges/"):
            return "module"
    encoded = json.dumps(entries, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    digest = hashlib.sha256(encoded.encode("utf-8")).hexdigest()
    if digest != report.get("entries_sha256"):
        return "entries digest"
    text = json.dumps(report, sort_keys=True)
    for secret in PLANTED_SECRETS.values():
        if secret in text:
            return "planted secret"
    return None


def _guarded_child() -> None:
    os.environ["AUREON_DISABLE_REAL_ORDERS"] = "0"
    os.environ["AUREON_LIVE_TRADING"] = "1"
    os.environ["AUREON_OPERATOR_MCP"] = "1"
    for name, value in PLANTED_SECRETS.items():
        os.environ.setdefault(name, value)
    report = guarded_sweep()
    reason = sweep_ok(report)
    if reason:
        sys.stderr.write(f"exchanges sweep refused: {reason}\n")
        raise SystemExit(2)
    sys.stdout.write(json.dumps(report, sort_keys=True))


def main(argv: list[str] | None = None) -> None:
    args = list(sys.argv[1:] if argv is None else argv)
    if args == ["--guarded-sweep"]:
        _guarded_child()
        return
    raise SystemExit("usage: python -m aureon_public.exchanges_surface --guarded-sweep")


if __name__ == "__main__":
    main()

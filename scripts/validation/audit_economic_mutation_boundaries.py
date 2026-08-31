#!/usr/bin/env python3
"""Static, fail-closed census of provider economic mutation call sites.

The auditor reads source text only. It never imports repository modules,
opens sockets, reads environment variables, or invokes a provider client.
Parsed source scope is Python, TypeScript/TSX, and executable JavaScript
(JS/MJS/CJS). Shell, PowerShell, and CMD are not parsed; a bounded repository
token audit found no provider order/mutation candidates in those languages.

Default CLI use is a certification gate: it exits non-zero while any
live-capable unguarded blocker exists. The --report-only option is deliberately
available for producing the truthful inventory while migration is incomplete;
inventory drift still fails in either mode.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ALLOWLIST = Path(__file__).with_name("economic_mutation_allowlist.json")
SOURCE_SUFFIXES = {".cjs", ".js", ".mjs", ".py", ".ts", ".tsx"}
SKIP_PARTS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "build",
    "dist",
    "node_modules",
    "site-packages",
    "vendor",
}

CLASSIFICATIONS = {
    "economic-boundary-last-mile",
    "provider-client-raw-transport-guard",
    "dry-run-test-demo-only",
    "unreachable-quarantined-launcher",
    "live-capable-unguarded-blocker",
}
BLOCKER = "live-capable-unguarded-blocker"
PREFILTER_TOKENS = (
    "/api/v3/order",
    "/sapi/v1/margin/order",
    "/fapi/v1/order",
    "/fapi/v1/batchorders",
    "/dapi/v1/order",
    "/dapi/v1/batchorders",
    "/eapi/v1/order",
    "/eapi/v1/batchorders",
    "/papi/v1/order",
    "/api/v3/orderlist",
    "/api/v3/sor/order",
    "/api/v3/order/amend",
    "/api/v3/openorders",
    "addorder",
    "amendorder",
    "cancelorder",
    "editorder",
    "cancelall",
    "/api/v1/positions",
    "/api/v1/workingorders",
    "/v2/orders",
    "/v2/positions",
    "/v3/accounts/",
    "order_market_buy",
    "order_market_sell",
    "order_limit_buy",
    "order_limit_sell",
    "create_order",
    "createorder",
    "place_order",
    "placeorder",
    "place_market_order",
    "place_limit_order",
    "submit_order",
    "submitorder",
    "cancel_order",
    "cancelorder",
    "replace_order",
    "replaceorder",
    "close_trade",
    "closetrade",
    "exercise_options_position",
    "exerciseoption",
    "order.place",
    "create_market_order",
    "create_limit_order",
    "create_market_buy_order",
    "create_market_sell_order",
    "createmarketorder",
    "createlimitorder",
    "place_margin_order",
    "close_margin_position",
    "place_working_order",
    "delete_working_order",
    "update_position_limits",
    "place_stop_order",
    "place_stop_limit_order",
    "place_stop_loss_order",
    "place_take_profit_order",
    "place_trailing_stop_order",
    "place_bracket_order",
    "place_oco_order",
    "place_oto_order",
    "place_order_with_tp_sl",
    "open_position_with_tp_sl",
    "cancel_orders",
    "closeallpositions",
)

PYTHON_TRANSPORT_TAILS = {
    "_private",
    "_private_request",
    "_do_request",
    "_request",
    "_signed_request",
    "delete",
    "fetch",
    "patch",
    "post",
    "put",
    "query_private",
    "request",
    "send",
    "urlopen",
    "consume_and_call",
}
TS_TRANSPORT_TAILS = {
    "apirequest",
    "alpacarequest",
    "binancerequest",
    "fetch",
    "privaterequest",
    "request",
    "send",
}
TS_SDK_TAILS = {
    "cancel_all_orders",
    "cancelallorders",
    "cancel_order",
    "cancel_order_by_id",
    "cancelorder",
    "cancelorderbyid",
    "close_position",
    "closeposition",
    "close_trade",
    "closetrade",
    "create_order",
    "createorder",
    "edit_order",
    "editorder",
    "exercise_options_position",
    "exerciseoption",
    "order_limit_buy",
    "order_limit_sell",
    "order_market_buy",
    "order_market_sell",
    "place_limit_order",
    "place_market_order",
    "place_order",
    "placeorder",
    "replace_order",
    "replace_order_by_id",
    "replaceorder",
    "replaceorderbyid",
    "submit_order",
    "submitorder",
    "create_market_order",
    "createmarketorder",
    "create_limit_order",
    "createlimitorder",
    "create_market_buy_order",
    "createmarketbuyorder",
    "create_market_sell_order",
    "createmarketsellorder",
    "cancel_orders",
    "cancelorders",
    "place_margin_order",
    "placemarginorder",
    "close_margin_position",
    "closemarginposition",
    "place_working_order",
    "placeworkingorder",
    "delete_working_order",
    "deleteworkingorder",
    "update_position_limits",
    "updatepositionlimits",
    "place_stop_order",
    "placestoporder",
    "place_stop_limit_order",
    "placestoplimitorder",
    "place_stop_loss_order",
    "placestoplossorder",
    "place_take_profit_order",
    "placetakeprofitorder",
    "place_trailing_stop_order",
    "placetrailingstoporder",
    "place_bracket_order",
    "placebracketorder",
    "place_oco_order",
    "placeocoorder",
    "place_oto_order",
    "placeotoorder",
    "place_order_with_tp_sl",
    "placeorderwithtpsl",
    "open_position_with_tp_sl",
    "openpositionwithtpsl",
}

PROVIDERS = ("binance", "kraken", "alpaca", "capital", "oanda")

SDK_OPERATION_BY_NORMALIZED_TAIL = {
    "createorder": "sdk-submit-order",
    "createmarketorder": "sdk-submit-order",
    "createlimitorder": "sdk-submit-order",
    "createmarketbuyorder": "sdk-submit-order",
    "createmarketsellorder": "sdk-submit-order",
    "placeorder": "sdk-submit-order",
    "placemarketorder": "sdk-submit-order",
    "placelimitorder": "sdk-submit-order",
    "submitorder": "sdk-submit-order",
    "cancelorder": "sdk-cancel-order",
    "cancelorderbyid": "sdk-cancel-order",
    "cancelorders": "sdk-cancel-orders",
    "cancelallorders": "sdk-cancel-all-orders",
    "editorder": "sdk-replace-order",
    "replaceorder": "sdk-replace-order",
    "replaceorderbyid": "sdk-replace-order",
    "closeposition": "sdk-close-position",
    "closetrade": "sdk-close-trade",
    "exercise": "sdk-exercise-option-position",
    "exerciseoption": "sdk-exercise-option-position",
    "exerciseoptionsposition": "sdk-exercise-option-position",
    "placemarginorder": "sdk-submit-margin-order",
    "closemarginposition": "sdk-close-margin-position",
    "placeworkingorder": "sdk-submit-working-order",
    "deleteworkingorder": "sdk-cancel-working-order",
    "cancelworkingorder": "sdk-cancel-working-order",
    "updatepositionlimits": "sdk-edit-position",
    "placestoporder": "sdk-submit-stop-order",
    "placestoplimitorder": "sdk-submit-stop-order",
    "placestoplossorder": "sdk-submit-stop-order",
    "placetrailingstoporder": "sdk-submit-stop-order",
    "placetakeprofitorder": "sdk-submit-take-profit-order",
    "placebracketorder": "sdk-submit-bracket-order",
    "placeocoorder": "sdk-submit-oco-order",
    "placeotoorder": "sdk-submit-oto-order",
    "placeorderwithtpsl": "sdk-submit-tp-sl-order",
    "openpositionwithtpsl": "sdk-submit-tp-sl-order",
}


@dataclass(frozen=True)
class Finding:
    file: str
    fingerprint: str
    language: str
    provider: str
    operation: str
    transport: str
    enclosing_symbol: str
    line: int
    canonical_call: str
    classification: str = ""
    rationale: str = ""
    owner: str = ""

    def allowlist_key(self) -> tuple[str, str]:
        return self.file, self.fingerprint


@dataclass(frozen=True)
class DetectedOperation:
    provider: str
    operation: str
    endpoint: str
    method: str


def _relative(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def source_paths(root: Path = ROOT) -> list[Path]:
    paths: list[Path] = []
    for directory, child_directories, filenames in os.walk(root):
        child_directories[:] = sorted(
            name for name in child_directories if name not in SKIP_PARTS
        )
        base = Path(directory)
        paths.extend(
            base / name
            for name in filenames
            if Path(name).suffix.lower() in SOURCE_SUFFIXES
        )
    return sorted(paths, key=lambda item: item.as_posix().casefold())


def _canonical_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _fingerprint(
    *,
    file: str,
    language: str,
    provider: str,
    operation: str,
    transport: str,
    enclosing_symbol: str,
    canonical_call: str,
    duplicate_ordinal: int,
) -> str:
    payload = {
        "call": canonical_call,
        "duplicate_ordinal": duplicate_ordinal,
        "enclosing_symbol": enclosing_symbol,
        "file": file,
        "language": language,
        "operation": operation,
        "provider": provider,
        "transport": transport,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return "econop:" + hashlib.sha256(encoded).hexdigest()[:24]


def _method_hint(callee: str, source: str) -> str:
    tail = callee.rsplit(".", 1)[-1].lower()
    if tail in {"post", "put", "patch", "delete"}:
        return tail.upper()
    matches = re.findall(r"(?<![A-Za-z])(POST|PUT|PATCH|DELETE|GET)(?![A-Za-z])", source, re.I)
    return matches[0].upper() if matches else ""


def _classify_endpoint(
    *,
    callee: str,
    source: str,
    resolved_strings: Iterable[str] = (),
) -> DetectedOperation | None:
    text = " ".join((source, *resolved_strings))
    folded = text.casefold().replace("\\", "/")
    method = _method_hint(callee, text)

    if "/api/v3/order/test" in folded:
        return None
    advanced_binance_routes = (
        ("/api/v3/order/amend", "amend-order", {"POST", "PUT", "PATCH"}),
        ("/api/v3/sor/order", "submit-sor-order", {"POST"}),
        ("/sapi/v1/margin/order/oco", "submit-margin-oco-order", {"POST"}),
        ("/api/v3/orderlist", "submit-oco-order", {"POST"}),
        ("/api/v3/order/oco", "submit-oco-order", {"POST"}),
    )
    for route, operation, methods in advanced_binance_routes:
        if route in folded and method in methods:
            return DetectedOperation("binance", operation, route, method)

    binance_derivatives = (
        ("/fapi/v1/batchorders", "futures", "order-batch"),
        ("/dapi/v1/batchorders", "delivery", "order-batch"),
        ("/eapi/v1/batchorders", "options", "order-batch"),
        ("/fapi/v1/order", "futures", "order"),
        ("/dapi/v1/order", "delivery", "order"),
        ("/eapi/v1/order", "options", "order"),
        ("/papi/v1/order", "portfolio", "order"),
    )
    for route, market, shape in binance_derivatives:
        if route not in folded or method not in {"POST", "PUT", "PATCH", "DELETE"}:
            continue
        action = {
            "POST": "submit",
            "PUT": "amend",
            "PATCH": "amend",
            "DELETE": "cancel",
        }[method]
        suffix = f"{market}-order"
        if shape == "order-batch":
            suffix += "-batch"
        return DetectedOperation("binance", f"{action}-{suffix}", route, method)

    if "/api/v3/openorders" in folded:
        if method == "DELETE":
            return DetectedOperation("binance", "cancel-all-orders", "/api/v3/openOrders", method)
        return None
    if "/api/v3/order" in folded or "/sapi/v1/margin/order" in folded:
        endpoint = (
            "/sapi/v1/margin/order"
            if "/sapi/v1/margin/order" in folded
            else "/api/v3/order"
        )
        if method == "POST":
            return DetectedOperation("binance", "submit-order", endpoint, method)
        if method == "DELETE":
            return DetectedOperation("binance", "cancel-order", endpoint, method)
        return None

    kraken_routes = {
        "addorderbatch": "submit-order-batch",
        "cancelorderbatch": "cancel-order-batch",
        "cancelallordersafter": "dead-man-cancel",
        "amendorder": "amend-order",
        "cancelorder": "cancel-order",
        "editorder": "edit-order",
        "cancelall": "cancel-all-orders",
        "addorder": "submit-order",
    }
    for route, operation in kraken_routes.items():
        if re.search(
            rf"(?:/0/private/|['\"]){route}(?=$|[\s'\"/?&#])",
            folded,
        ):
            return DetectedOperation("kraken", operation, f"/0/private/{route}", "POST")

    capital_path = "/api/v1/positions" in folded or bool(
        re.search(r"['\"f]/positions(?:/|\b)", folded)
    )
    if capital_path and method in {"POST", "PUT", "DELETE"}:
        operation = {
            "POST": "submit-position",
            "PUT": "edit-position",
            "DELETE": "close-position",
        }[method]
        return DetectedOperation("capital", operation, "/api/v1/positions", method)
    capital_working = "/api/v1/workingorders" in folded or bool(
        re.search(r"['\"f]/workingorders(?:/|\b)", folded)
    )
    if capital_working and method in {"POST", "PUT", "DELETE"}:
        operation = {
            "POST": "submit-working-order",
            "PUT": "edit-working-order",
            "DELETE": "cancel-working-order",
        }[method]
        return DetectedOperation("capital", operation, "/api/v1/workingorders", method)

    alpaca_positions = bool(re.search(r"(?<!/trade)/v2/positions", folded))
    alpaca_orders = bool(re.search(r"(?<!/trade)/v2/orders", folded))
    if alpaca_positions and "/exercise" in folded and method == "POST":
        return DetectedOperation(
            "alpaca", "exercise-option-position", "/v2/positions/{symbol}/exercise", method
        )
    if alpaca_positions and method == "DELETE":
        operation = "close-all-positions" if re.search(r"/v2/positions[\"')]", folded) else "close-position"
        return DetectedOperation("alpaca", operation, "/v2/positions", method)
    if alpaca_orders and method in {"POST", "PATCH", "DELETE"}:
        operation = {
            "POST": "submit-order",
            "PATCH": "replace-order",
            "DELETE": (
                "cancel-all-orders"
                if re.search(r"/v2/orders[\"')]", folded)
                else "cancel-order"
            ),
        }[method]
        return DetectedOperation("alpaca", operation, "/v2/orders", method)

    if "/v3/accounts/" in folded:
        if "/trades/" in folded and "/close" in folded and method in {"PUT", "POST"}:
            return DetectedOperation("oanda", "close-trade", "/v3/accounts/{id}/trades/{id}/close", method)
        if "/positions/" in folded and "/close" in folded and method in {"PUT", "POST"}:
            return DetectedOperation(
                "oanda", "close-position", "/v3/accounts/{id}/positions/{instrument}/close", method
            )
        if "/orders" in folded and method in {"POST", "PUT", "PATCH", "DELETE"}:
            if "/cancel" in folded or method == "DELETE":
                operation = "cancel-order"
            elif method in {"PUT", "PATCH"} and re.search(r"/orders/[^/\"']+", folded):
                operation = "replace-order"
            else:
                operation = "submit-order"
            return DetectedOperation("oanda", operation, "/v3/accounts/{id}/orders", method)

    return None


def _sdk_operation(
    callee: str,
    rel_path: str,
    source_context: str = "",
    provider_hints: Iterable[str] | None = None,
    provider_override: str = "",
) -> DetectedOperation | None:
    folded = callee.casefold()
    tail = folded.rsplit(".", 1)[-1]
    normalized_tail = tail.replace("_", "")
    receiver = folded.rsplit(".", 1)[0] if "." in folded else ""
    path_folded = rel_path.casefold()
    context = f"{receiver} {path_folded}"

    if normalized_tail in {
        "ordermarketbuy",
        "ordermarketsell",
        "orderlimitbuy",
        "orderlimitsell",
    }:
        return DetectedOperation(
            provider_override or "binance",
            "submit-order",
            "sdk",
            "SDK",
        )
    operation = SDK_OPERATION_BY_NORMALIZED_TAIL.get(normalized_tail)
    if operation is None:
        return None

    provider = provider_override
    for candidate in PROVIDERS:
        if provider:
            break
        if candidate in context:
            provider = candidate
            break

    if not provider:
        signals = set(provider_hints or ())
        if provider_hints is None:
            import_lines = " ".join(
                re.findall(
                    r"(?:^|\n)\s*(?:from|import)\b[^\n]*",
                    source_context,
                    re.I,
                )
            ).casefold()
            signals = {
                candidate
                for candidate in PROVIDERS
                if candidate in import_lines
            }
        if len(signals) == 1:
            provider = next(iter(signals))
        elif len(signals) > 1:
            provider = "multi-provider"
        else:
            return None

    return DetectedOperation(provider, operation, "sdk", "SDK")


def _providers_from_text(text: str) -> set[str]:
    folded = text.casefold().replace("\\", "/")
    found = {provider for provider in PROVIDERS if re.search(rf"\b{provider}\b", folded)}
    if any(route in folded for route in (
        "/api/v3/order", "/sapi/v1/margin/order", "/fapi/v1/order",
        "/dapi/v1/order", "/eapi/v1/order", "/papi/v1/order",
    )):
        found.add("binance")
    if "/0/private/" in folded or "order.place" in folded:
        if "order.place" in folded:
            found.add("binance")
        if "/0/private/" in folded or "addorder" in folded:
            found.add("kraken")
    if re.search(r"(?<!/trade)/v2/(?:orders|positions)", folded):
        found.add("alpaca")
    if "/api/v1/positions" in folded or "/api/v1/workingorders" in folded:
        found.add("capital")
    if "/v3/accounts/" in folded:
        found.add("oanda")
    return found


class PythonCallVisitor(ast.NodeVisitor):
    def __init__(self, path: Path, source: str) -> None:
        self.path = path
        self.rel_path = _relative(path)
        self.source = source
        import_lines = " ".join(
            re.findall(r"(?:^|\n)\s*(?:from|import)\b[^\n]*", source, re.I)
        )
        self.provider_hints = _providers_from_text(
            f"{import_lines} {self.rel_path} {source}"
        )
        self.constants: dict[str, Any] = {}
        self.receiver_providers: dict[str, str] = {}
        self.function_defs: dict[str, ast.FunctionDef | ast.AsyncFunctionDef] = {}
        self.read_only_retrieval_functions: set[str] = set()
        self.read_only_transport_bindings: set[tuple[str, str]] = set()
        self.consume_operations: dict[int, DetectedOperation] = {}
        self.guarded_transport_call_ids: set[int] = set()
        self.scope: list[str] = []
        self.raw: list[tuple[ast.Call, str, DetectedOperation, str, str]] = []

    @staticmethod
    def _callee(node: ast.AST) -> str:
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            prefix = PythonCallVisitor._callee(node.value)
            return f"{prefix}.{node.attr}" if prefix else node.attr
        if isinstance(node, ast.Subscript):
            return PythonCallVisitor._callee(node.value)
        return ""

    @staticmethod
    def _argument_count(node: ast.Lambda | ast.FunctionDef | ast.AsyncFunctionDef) -> int:
        args = node.args
        return (
            len(args.posonlyargs)
            + len(args.args)
            + len(args.kwonlyargs)
            + int(args.vararg is not None)
            + int(args.kwarg is not None)
        )

    def _static_value(self, node: ast.AST) -> Any:
        if isinstance(node, ast.Constant):
            return node.value
        if isinstance(node, ast.Name):
            return self.constants.get(node.id)
        if isinstance(node, ast.Attribute):
            return self.constants.get(self._callee(node))
        if isinstance(node, ast.Dict):
            result: dict[Any, Any] = {}
            for key_node, value_node in zip(node.keys, node.values, strict=True):
                if key_node is None:
                    return None
                key = self._static_value(key_node)
                value = self._static_value(value_node)
                if key is None or value is None:
                    return None
                try:
                    result[key] = value
                except TypeError:
                    return None
            return result
        if isinstance(node, (ast.List, ast.Tuple)):
            values = [self._static_value(item) for item in node.elts]
            return None if any(value is None for value in values) else values
        if isinstance(node, ast.Subscript):
            container = self._static_value(node.value)
            key = self._static_value(node.slice)
            try:
                return container[key]
            except (KeyError, IndexError, TypeError):
                return None
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
            left = self._static_value(node.left)
            right = self._static_value(node.right)
            if isinstance(left, str) and isinstance(right, str):
                return left + right
            return None
        if isinstance(node, ast.FormattedValue):
            value = self._static_value(node.value)
            return None if value is None else str(value)
        if isinstance(node, ast.JoinedStr):
            pieces: list[str] = []
            for value_node in node.values:
                value = self._static_value(value_node)
                if value is None:
                    return None
                pieces.append(str(value))
            return "".join(pieces)
        if isinstance(node, ast.Call):
            callee = self._callee(node.func).casefold()
            if callee.endswith(".get") and node.args:
                container = self._static_value(node.func.value) if isinstance(node.func, ast.Attribute) else None
                key = self._static_value(node.args[0])
                default = self._static_value(node.args[1]) if len(node.args) > 1 else None
                if not isinstance(container, dict):
                    return None
                try:
                    return container.get(key, default)
                except TypeError:
                    return None
            if callee in {"json.dumps", "dumps"} and node.args:
                value = self._static_value(node.args[0])
                if value is not None:
                    return json.dumps(value, sort_keys=True)
            if callee in {"str", "builtins.str"} and node.args:
                value = self._static_value(node.args[0])
                return None if value is None else str(value)
        return None

    @staticmethod
    def _flatten_static(value: Any) -> list[str]:
        if isinstance(value, str):
            return [value]
        if isinstance(value, dict):
            values: list[str] = []
            for key, item in value.items():
                values.extend(PythonCallVisitor._flatten_static(key))
                values.extend(PythonCallVisitor._flatten_static(item))
            return values
        if isinstance(value, (list, tuple)):
            values = []
            for item in value:
                values.extend(PythonCallVisitor._flatten_static(item))
            return values
        return []

    def _resolved_strings(self, call: ast.Call) -> list[str]:
        values: list[str] = []
        for node in (*call.args, *(keyword.value for keyword in call.keywords)):
            values.extend(self._flatten_static(self._static_value(node)))
            if isinstance(node, ast.JoinedStr):
                values.append(ast.unparse(node))
        return values

    def _provider_for_callee(self, callee: str, *, scope: str = "") -> str:
        folded = callee.casefold()
        receiver = folded.rsplit(".", 1)[0] if "." in folded else folded
        root = receiver.split(".", 1)[0]
        for key in (receiver, root):
            provider = self.receiver_providers.get(key)
            if provider:
                return provider
        for provider in PROVIDERS:
            if provider in f"{receiver} {self.rel_path.casefold()} {scope.casefold()}":
                return provider
        if len(self.provider_hints) == 1:
            return next(iter(self.provider_hints))
        if len(self.provider_hints) > 1:
            return "multi-provider"
        return ""

    def _remember_target(self, target: ast.AST, value_node: ast.AST) -> None:
        target_name = self._callee(target)
        if not target_name:
            return
        value = self._static_value(value_node)
        if value is not None:
            self.constants[target_name] = value
            if isinstance(target, ast.Name):
                self.constants[target.id] = value
        if isinstance(value_node, ast.Call):
            callee = self._callee(value_node.func).casefold()
            root = callee.split(".", 1)[0]
            provider = self.receiver_providers.get(root, "")
            if not provider:
                provider = next((item for item in PROVIDERS if item in callee), "")
            if provider:
                self.receiver_providers[target_name.casefold()] = provider

    def _is_read_only_retrieval_function(
        self,
        function: ast.FunctionDef | ast.AsyncFunctionDef,
    ) -> bool:
        """Prove a local callback delegates only to the registry's web retrieval tool.

        This is deliberately structural rather than a name/path allowlist.  The
        economic census treats ``web_fetch`` as retrieval, but does not extend
        that exception to arbitrary ``fetch`` callables or to any call carrying
        an explicit/dynamic HTTP method.
        """

        registry_fetch = False
        for call in (node for node in ast.walk(function) if isinstance(node, ast.Call)):
            callee = self._callee(call.func)
            tail = callee.rsplit(".", 1)[-1].casefold()
            canonical = ast.unparse(call)
            resolved = self._resolved_strings(call)
            method = _method_hint(callee, " ".join((canonical, *resolved)))
            normalized_tail = tail.replace("_", "")
            if tail in {"post", "put", "patch", "delete"}:
                return False
            if method in {"POST", "PUT", "PATCH", "DELETE"}:
                return False
            if normalized_tail in SDK_OPERATION_BY_NORMALIZED_TAIL:
                return False
            if _classify_endpoint(
                callee=callee,
                source=canonical,
                resolved_strings=resolved,
            ) is not None:
                return False
            if tail != "execute" or not call.args:
                continue
            tool_name = self._static_value(call.args[0])
            if tool_name != "web_fetch":
                continue
            if len(call.args) != 2 or call.keywords:
                return False
            arguments = call.args[1]
            if not isinstance(arguments, ast.Dict):
                return False
            keys = [self._static_value(key) for key in arguments.keys if key is not None]
            if keys != ["url"]:
                return False
            registry_fetch = True
        return registry_fetch

    def _remember_read_only_transport_binding(
        self,
        target: ast.AST,
        value_node: ast.AST,
    ) -> None:
        """Record ``local = injected_callback or proven_read_only_default`` bindings."""

        target_name = self._callee(target)
        if not target_name or "." in target_name or not self.scope:
            return
        if not isinstance(value_node, ast.BoolOp) or not isinstance(value_node.op, ast.Or):
            return
        if len(value_node.values) != 2:
            return
        injected, fallback = value_node.values
        if not isinstance(injected, ast.Name) or not isinstance(fallback, ast.Name):
            return
        if fallback.id not in self.read_only_retrieval_functions:
            return
        function = self.function_defs.get(self.scope[-1])
        if function is None:
            return
        parameters = (*function.args.posonlyargs, *function.args.args, *function.args.kwonlyargs)
        parameter = next((item for item in parameters if item.arg == injected.id), None)
        if parameter is None or parameter.annotation is None:
            return
        annotation = ast.unparse(parameter.annotation).casefold()
        if "fetch" not in annotation and "callable" not in annotation:
            return
        self.read_only_transport_bindings.add((".".join(self.scope), target_name))

    def _is_bound_read_only_retrieval_call(self, call: ast.Call, callee: str) -> bool:
        if "." in callee or len(call.args) != 1 or call.keywords:
            return False
        return (".".join(self.scope), callee) in self.read_only_transport_bindings

    def prepare(self, tree: ast.AST) -> None:
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self.function_defs[node.name] = node
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    provider = next((item for item in PROVIDERS if item in alias.name.casefold()), "")
                    if provider:
                        self.receiver_providers[(alias.asname or alias.name.split(".")[0]).casefold()] = provider
            elif isinstance(node, ast.ImportFrom):
                provider = next((item for item in PROVIDERS if item in (node.module or "").casefold()), "")
                if provider:
                    for alias in node.names:
                        self.receiver_providers[(alias.asname or alias.name).casefold()] = provider
        self.read_only_retrieval_functions = {
            name
            for name, function in self.function_defs.items()
            if self._is_read_only_retrieval_function(function)
        }
        for _ in range(3):
            for node in ast.walk(tree):
                if isinstance(node, ast.Assign):
                    for target in node.targets:
                        self._remember_target(target, node.value)
                elif isinstance(node, ast.AnnAssign) and node.value is not None:
                    self._remember_target(node.target, node.value)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            callee = self._callee(node.func)
            if callee.rsplit(".", 1)[-1].casefold() != "consume_and_call":
                continue
            structured = self._structured_consume(node, callee)
            if structured is None:
                continue
            operation, guarded_calls = structured
            self.consume_operations[id(node)] = operation
            self.guarded_transport_call_ids.update(id(call) for call in guarded_calls)

    def _mutation_calls(self, node: ast.AST) -> list[ast.Call]:
        calls: list[ast.Call] = []
        for candidate in ast.walk(node):
            if not isinstance(candidate, ast.Call):
                continue
            callee = self._callee(candidate.func)
            normalized = callee.rsplit(".", 1)[-1].casefold().replace("_", "")
            if normalized in SDK_OPERATION_BY_NORMALIZED_TAIL:
                calls.append(candidate)
                continue
            if any(
                isinstance(arg, ast.Attribute)
                and arg.attr.casefold().replace("_", "") in SDK_OPERATION_BY_NORMALIZED_TAIL
                for arg in candidate.args
            ):
                calls.append(candidate)
                continue
            operation = _classify_endpoint(
                callee=callee,
                source=ast.unparse(candidate),
                resolved_strings=self._resolved_strings(candidate),
            )
            if operation is not None:
                calls.append(candidate)
        return calls

    def _structured_consume(
        self,
        node: ast.Call,
        callee: str,
    ) -> tuple[DetectedOperation, list[ast.Call]] | None:
        receiver = callee.rsplit(".", 1)[0].casefold()
        if "boundary" not in receiver and "recovery" not in receiver:
            return None
        if not node.args:
            return None
        permit = node.args[0]
        if "recovery" in receiver and (
            not isinstance(permit, ast.Name) or "recover" not in permit.id.casefold()
        ):
            return None
        keywords = {keyword.arg: keyword.value for keyword in node.keywords if keyword.arg}
        if not {"method", "path", "body", "transport"} <= keywords.keys():
            return None
        method = self._static_value(keywords["method"])
        path = self._static_value(keywords["path"])
        if not isinstance(method, str) or not isinstance(path, str):
            return None
        operation = _classify_endpoint(
            callee=callee,
            source=f"{method} {path}",
            resolved_strings=(method, path),
        )
        if operation is None:
            return None
        transport = keywords["transport"]
        closure: ast.AST | None = None
        if isinstance(transport, ast.Lambda):
            if self._argument_count(transport) != 0:
                return None
            closure = transport.body
        elif isinstance(transport, ast.Name):
            function = self.function_defs.get(transport.id)
            if function is None or self._argument_count(function) != 0:
                return None
            closure = function
        if closure is None:
            return None
        mutation_calls = self._mutation_calls(closure)
        if not mutation_calls:
            return None
        return operation, mutation_calls

    def visit_Assign(self, node: ast.Assign) -> Any:
        for target in node.targets:
            self._remember_target(target, node.value)
            self._remember_read_only_transport_binding(target, node.value)
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> Any:
        if node.value is not None:
            self._remember_target(node.target, node.value)
            self._remember_read_only_transport_binding(node.target, node.value)
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> Any:
        self.scope.append(node.name)
        self.generic_visit(node)
        self.scope.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> Any:
        self.scope.append(node.name)
        self.generic_visit(node)
        self.scope.pop()

    visit_AsyncFunctionDef = visit_FunctionDef

    def _websocket_operation(self, call: ast.Call, callee: str) -> DetectedOperation | None:
        text = " ".join((ast.unparse(call), *self._resolved_strings(call))).casefold()
        if "order.place" in text:
            return DetectedOperation("binance", "submit-order", "websocket:order.place", "WS")
        if re.search(r"\baddorder\b", text):
            return DetectedOperation("kraken", "submit-order", "websocket:addOrder", "WS")
        return None

    def _dynamic_transport_operation(
        self,
        call: ast.Call,
        callee: str,
    ) -> DetectedOperation | None:
        tail = callee.rsplit(".", 1)[-1].casefold()
        provider = self._provider_for_callee(
            callee,
            scope=".".join(self.scope),
        )
        if not provider:
            return None
        if tail == "fetch" and self._is_bound_read_only_retrieval_call(call, callee):
            return None
        canonical = ast.unparse(call)
        resolved = self._resolved_strings(call)
        combined = " ".join((canonical, *resolved)).casefold()
        if "/api/v3/order/test" in combined:
            return None
        receiver = callee.rsplit(".", 1)[0].casefold()
        receiver_tail = receiver.rsplit(".", 1)[-1]
        if tail == "put" and (
            receiver_tail == "queue" or receiver_tail.endswith("_queue")
        ):
            return None
        scope = ".".join(self.scope)
        if provider == "capital" and tail == "post" and (
            "/session" in combined or scope.endswith("CapitalClient._create_session")
        ):
            return None
        if (
            tail == "post"
            and scope.endswith("HMRCApiClient._token_request")
            and ("token_url" in combined or "/oauth/token" in combined)
        ):
            return None
        method = _method_hint(callee, " ".join((canonical, *resolved)))
        if method == "GET":
            return None
        if tail in {"post", "put", "patch", "delete"}:
            return DetectedOperation(provider, "dynamic-provider-mutation", "dynamic", method or tail.upper())
        if tail in {"request", "_request", "_signed_request", "fetch"}:
            folded = canonical.casefold()
            has_dynamic_method = (
                method in {"POST", "PUT", "PATCH", "DELETE"}
                or bool(re.search(r"\bmethod\b", folded))
                or (call.args and not isinstance(call.args[0], ast.Constant))
            )
            if has_dynamic_method:
                return DetectedOperation(provider, "dynamic-provider-mutation", "dynamic", method or "DYNAMIC")
        return None

    def visit_Call(self, node: ast.Call) -> Any:
        callee = self._callee(node.func)
        tail = callee.rsplit(".", 1)[-1].casefold()
        canonical = _canonical_text(ast.unparse(node))
        operation: DetectedOperation | None = None
        transport = ""

        if id(node) in self.guarded_transport_call_ids:
            self.generic_visit(node)
            return
        if tail == "consume_and_call":
            operation = self.consume_operations.get(id(node))
            if operation is not None:
                transport = "economic-boundary-dispatch"
        elif tail == "send":
            operation = self._websocket_operation(node, callee)
            if operation is not None:
                transport = "authenticated-websocket"
        elif tail in PYTHON_TRANSPORT_TAILS:
            operation = _classify_endpoint(
                callee=callee,
                source=f"{canonical} {self.rel_path}",
                resolved_strings=self._resolved_strings(node),
            )
            if operation is not None:
                transport = "raw-http"
        if operation is None and tail != "consume_and_call":
            operation = _sdk_operation(
                callee,
                self.rel_path,
                self.source,
                self.provider_hints,
                self._provider_for_callee(callee, scope=".".join(self.scope)),
            )
            if operation is not None:
                transport = "sdk-or-provider-wrapper"
        if operation is None and tail != "consume_and_call":
            operation = self._dynamic_transport_operation(node, callee)
            if operation is not None:
                transport = "raw-http-dynamic"
        if operation is not None:
            self.raw.append(
                (
                    node,
                    callee,
                    operation,
                    transport,
                    ".".join(self.scope) or "<module>",
                )
            )
        self.generic_visit(node)


def _python_findings(path: Path, source: str | None = None) -> tuple[list[Finding], str | None]:
    source = source if source is not None else path.read_text(encoding="utf-8", errors="strict")
    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError as exc:
        return [], f"{_relative(path)}:{exc.lineno}:{exc.msg}"
    visitor = PythonCallVisitor(path, source)
    visitor.prepare(tree)
    visitor.visit(tree)
    rel_path = _relative(path)
    findings: list[Finding] = []
    duplicate_counts: dict[str, int] = {}
    for node, _callee, operation, transport, scope in visitor.raw:
        canonical = _canonical_text(ast.unparse(node))
        base = json.dumps(
            [rel_path, operation.provider, operation.operation, transport, scope, canonical],
            separators=(",", ":"),
        )
        ordinal = duplicate_counts.get(base, 0)
        duplicate_counts[base] = ordinal + 1
        findings.append(
            Finding(
                file=rel_path,
                fingerprint=_fingerprint(
                    file=rel_path,
                    language="python",
                    provider=operation.provider,
                    operation=operation.operation,
                    transport=transport,
                    enclosing_symbol=scope,
                    canonical_call=canonical,
                    duplicate_ordinal=ordinal,
                ),
                language="python",
                provider=operation.provider,
                operation=operation.operation,
                transport=transport,
                enclosing_symbol=scope,
                line=getattr(node, "lineno", 0),
                canonical_call=canonical,
            )
        )
    return findings, None


def _mask_ts_comments(source: str) -> str:
    chars = list(source)
    index = 0
    quote = ""
    template_quote = chr(96)
    while index < len(chars):
        char = chars[index]
        nxt = chars[index + 1] if index + 1 < len(chars) else ""
        if quote:
            if char == "\\":
                index += 2
                continue
            if char == quote:
                quote = ""
            index += 1
            continue
        if char in {"'", '"', template_quote}:
            quote = char
            index += 1
            continue
        if char == "/" and nxt == "/":
            end = source.find("\n", index)
            end = len(chars) if end < 0 else end
            for pos in range(index, end):
                chars[pos] = " "
            index = end
            continue
        if char == "/" and nxt == "*":
            end = source.find("*/", index + 2)
            end = len(chars) - 2 if end < 0 else end
            for pos in range(index, end + 2):
                if chars[pos] != "\n":
                    chars[pos] = " "
            index = end + 2
            continue
        index += 1
    return "".join(chars)


def _balanced_call_end(source: str, open_index: int) -> int | None:
    depth = 0
    quote = ""
    template_quote = chr(96)
    index = open_index
    while index < len(source):
        char = source[index]
        if quote:
            if char == "\\":
                index += 2
                continue
            if char == quote:
                quote = ""
            index += 1
            continue
        if char in {"'", '"', template_quote}:
            quote = char
        elif char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 0:
                return index + 1
        index += 1
    return None


def _looks_like_ts_declaration(source: str, start: int, end: int) -> bool:
    line_start = source.rfind("\n", 0, start) + 1
    prefix = source[line_start:start].strip()
    if re.search(
        r"(?:^|\s)(?:async|function|public|private|protected|static|abstract|declare)\s*$",
        prefix,
    ):
        return True
    suffix = source[end : end + 240]
    return bool(re.match(r"\s*(?::[^;=\n{]+)?\s*(?:\{|=>)", suffix))


def _ts_scope(source: str, position: int) -> str:
    prefix = source[:position]
    patterns = (
        r"\bclass\s+([A-Za-z_$][\w$]*)",
        r"\b(?:async\s+)?function\s+([A-Za-z_$][\w$]*)",
        r"\b(?:public|private|protected)?\s*(?:async\s+)?([A-Za-z_$][\w$]*)\s*\([^;{}]*\)\s*(?::[^{}]+)?\{",
    )
    candidates: list[tuple[int, str]] = []
    for pattern in patterns:
        candidates.extend((match.start(), match.group(1)) for match in re.finditer(pattern, prefix))
    return max(candidates, default=(-1, "<module>"))[1]


def _ts_findings(path: Path, source: str | None = None) -> tuple[list[Finding], str | None]:
    source = source if source is not None else path.read_text(encoding="utf-8", errors="strict")
    masked = _mask_ts_comments(source)
    rel_path = _relative(path)
    call_pattern = re.compile(
        r"(?P<callee>[A-Za-z_$][\w$]*(?:\??\.[A-Za-z_$][\w$]*)*)"
        r"(?:\s*<[^;{}()]+>)?\s*\("
    )
    string_bindings: dict[str, str] = {}
    import_lines = " ".join(
        re.findall(r"(?:^|\n)\s*import\b[^\n]*", source, re.I)
    )
    provider_hints = _providers_from_text(f"{import_lines} {rel_path} {source}")
    transport_provider_hints = _providers_from_text(f"{import_lines} {rel_path}")
    receiver_providers: dict[str, str] = {}
    receiver_pattern = re.compile(
        r"\b(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*"
        r"(?:new\s+)?(?:ccxt\.)?([A-Za-z_$][\w$]*)",
        re.I,
    )
    for binding in receiver_pattern.finditer(masked):
        provider = next(
            (
                candidate
                for candidate in PROVIDERS
                if candidate in binding.group(2).casefold()
            ),
            "",
        )
        if provider:
            receiver_providers[binding.group(1).casefold()] = provider
    binding_pattern = re.compile(
        r"\b(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*"
        r"((?:['\"]).*?(?:['\"])|(?:\x60).*?(?:\x60))",
        re.S,
    )
    for binding in binding_pattern.finditer(masked):
        rendered = binding.group(2)
        string_bindings[binding.group(1)] = rendered
    findings: list[Finding] = []
    duplicate_counts: dict[str, int] = {}
    for match in call_pattern.finditer(masked):
        callee = match.group("callee").replace("?.", ".")
        tail = callee.rsplit(".", 1)[-1].casefold()
        if (
            tail not in TS_TRANSPORT_TAILS
            and tail not in {"post", "put", "patch", "delete"}
            and tail not in TS_SDK_TAILS
        ):
            continue
        open_index = masked.find("(", match.start())
        end = _balanced_call_end(masked, open_index)
        if end is None:
            continue
        if _looks_like_ts_declaration(masked, match.start(), end):
            continue
        call_source = masked[match.start() : end]
        canonical = _canonical_text(call_source)
        scope = _ts_scope(masked, match.start())
        resolved = [
            value
            for name, value in string_bindings.items()
            if re.search(rf"\b{re.escape(name)}\b", canonical)
        ]
        operation_provider_hints = transport_provider_hints | _providers_from_text(
            " ".join([canonical, *resolved])
        )
        receiver = callee.casefold().rsplit(".", 1)[0] if "." in callee else ""
        provider_override = receiver_providers.get(receiver.split(".", 1)[0], "")
        if not provider_override:
            provider_override = next(
                (
                    candidate
                    for candidate in PROVIDERS
                    if candidate
                    in f"{receiver} {rel_path.casefold()} {scope.casefold()} "
                    f"{canonical.casefold()}"
                ),
                "",
            )
        if not provider_override:
            if len(operation_provider_hints) == 1:
                provider_override = next(iter(operation_provider_hints))
            elif len(operation_provider_hints) > 1:
                provider_override = "multi-provider"
        operation: DetectedOperation | None = None
        transport = ""
        if tail in TS_TRANSPORT_TAILS or tail in {"post", "put", "patch", "delete"}:
            operation = _classify_endpoint(
                callee=callee,
                source=f"{canonical} {rel_path}",
                resolved_strings=resolved,
            )
            if operation:
                transport = "raw-http"
        if operation is None and tail == "send":
            folded_call = canonical.casefold()
            if "order.place" in folded_call:
                operation = DetectedOperation(
                    "binance", "submit-order", "websocket:order.place", "WS"
                )
            elif re.search(r"\baddorder\b", folded_call):
                operation = DetectedOperation(
                    "kraken", "submit-order", "websocket:addOrder", "WS"
                )
            if operation:
                transport = "authenticated-websocket"
        if operation is None:
            operation = _sdk_operation(
                callee,
                rel_path,
                source,
                provider_hints,
                provider_override,
            )
            if operation:
                transport = "sdk-or-provider-wrapper"
        if operation is None and provider_override:
            folded_call = canonical.casefold()
            if "/api/v3/order/test" not in folded_call:
                method = _method_hint(callee, canonical)
                fixed_mutation = tail in {"post", "put", "patch", "delete"}
                explicit_get = method == "GET"
                dynamic_method = bool(
                    re.search(
                        r"(?:\{\s*method\s*\}|\bmethod\s*:|,\s*method\b)",
                        folded_call,
                    )
                )
                if not explicit_get and (fixed_mutation or dynamic_method):
                    operation = DetectedOperation(
                        provider_override,
                        "dynamic-provider-mutation",
                        "dynamic",
                        method or "DYNAMIC",
                    )
                    transport = "raw-http-dynamic"
        if operation is None:
            continue
        base = json.dumps(
            [rel_path, operation.provider, operation.operation, transport, scope, canonical],
            separators=(",", ":"),
        )
        ordinal = duplicate_counts.get(base, 0)
        duplicate_counts[base] = ordinal + 1
        findings.append(
            Finding(
                file=rel_path,
                fingerprint=_fingerprint(
                    file=rel_path,
                    language="typescript",
                    provider=operation.provider,
                    operation=operation.operation,
                    transport=transport,
                    enclosing_symbol=scope,
                    canonical_call=canonical,
                    duplicate_ordinal=ordinal,
                ),
                language="typescript",
                provider=operation.provider,
                operation=operation.operation,
                transport=transport,
                enclosing_symbol=scope,
                line=masked.count("\n", 0, match.start()) + 1,
                canonical_call=canonical,
            )
        )
    return findings, None


def discover(
    root: Path = ROOT,
    *,
    paths: Iterable[Path] | None = None,
) -> tuple[list[Finding], list[str]]:
    findings: list[Finding] = []
    parse_errors: list[str] = []
    for path in paths if paths is not None else source_paths(root):
        try:
            source = path.read_text(encoding="utf-8", errors="strict")
        except UnicodeDecodeError as exc:
            parse_errors.append(f"{_relative(path)}:decode:{exc}")
            continue
        folded = source.casefold()
        relative = _relative(path)
        provider_transport_surface = (
            bool(_providers_from_text(f"{relative} {source}"))
            and bool(
                re.search(
                    r"\b(?:fetch|request|post|put|patch|delete|send)\s*\(",
                    folded,
                )
            )
        )
        if (
            not any(token in folded for token in PREFILTER_TOKENS)
            and not provider_transport_surface
        ):
            continue
        if path.suffix.lower() == ".py":
            per_file, error = _python_findings(path, source)
        else:
            per_file, error = _ts_findings(path, source)
        findings.extend(per_file)
        if error:
            parse_errors.append(error)
    return sorted(findings, key=lambda item: (item.file, item.line, item.fingerprint)), parse_errors


def _migration_batches(blockers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    unsafe_live_test_clis = {
        "Kings_Accounting_Suite/aureon_systems/test_queen_power_redistribution.py",
        "tests/test_kill_chain_real.py",
        "tests/test_queen_power_redistribution.py",
    }
    provider_clients = {
        "aureon/exchanges/alpaca_client.py",
        "aureon/exchanges/alpaca_options_client.py",
        "aureon/exchanges/binance_client.py",
        "aureon/exchanges/capital_client.py",
        "aureon/exchanges/kraken_client.py",
        "scripts/traders/alpacaApi.ts",
        "scripts/traders/capitalComApi.ts",
        "scripts/traders/oandaApi.ts",
    }
    grouped: dict[str, list[dict[str, Any]]] = {
        "01-quarantine-live-test-clis": [],
        "02-gate-supabase-provider-functions": [],
        "03-guard-provider-client-chokepoints": [],
        "04-migrate-direct-http-bypasses": [],
        "05-migrate-legacy-sdk-wrapper-callers": [],
    }
    for blocker in blockers:
        file = str(blocker["file"])
        if file in unsafe_live_test_clis:
            key = "01-quarantine-live-test-clis"
        elif file.startswith("supabase/functions/"):
            key = "02-gate-supabase-provider-functions"
        elif file in provider_clients:
            key = "03-guard-provider-client-chokepoints"
        elif blocker["transport"] == "raw-http":
            key = "04-migrate-direct-http-bypasses"
        else:
            key = "05-migrate-legacy-sdk-wrapper-callers"
        grouped[key].append(blocker)
    return [
        {
            "batch": name,
            "call_site_count": len(items),
            "file_count": len({str(item["file"]) for item in items}),
            "files": sorted({str(item["file"]) for item in items}),
        }
        for name, items in grouped.items()
        if items
    ]


def load_allowlist(path: Path = DEFAULT_ALLOWLIST) -> dict[tuple[str, str], dict[str, str]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema") != "aureon.economic-mutation-allowlist.v1":
        raise ValueError("unexpected allowlist schema")
    entries: dict[tuple[str, str], dict[str, str]] = {}
    for raw in payload.get("entries", []):
        required = {"file", "fingerprint", "classification", "rationale", "owner"}
        missing = sorted(required - raw.keys())
        if missing:
            raise ValueError(f"allowlist entry missing fields {missing}: {raw!r}")
        if raw["classification"] not in CLASSIFICATIONS:
            raise ValueError(f"unknown classification: {raw['classification']}")
        if not str(raw["rationale"]).strip() or not str(raw["owner"]).strip():
            raise ValueError("allowlist rationale and owner must be non-empty")
        key = (str(raw["file"]), str(raw["fingerprint"]))
        if key in entries:
            raise ValueError(f"duplicate allowlist key: {key}")
        entries[key] = {str(name): str(value) for name, value in raw.items()}
    return entries


def audit(
    *,
    root: Path = ROOT,
    allowlist_path: Path = DEFAULT_ALLOWLIST,
) -> dict[str, Any]:
    paths = source_paths(root)
    discovered, parse_errors = discover(root, paths=paths)
    allowlist = load_allowlist(allowlist_path)
    discovered_keys = {finding.allowlist_key() for finding in discovered}
    unallowlisted = [
        asdict(finding) for finding in discovered if finding.allowlist_key() not in allowlist
    ]
    stale = [
        {"file": file, "fingerprint": fingerprint}
        for file, fingerprint in sorted(set(allowlist) - discovered_keys)
    ]
    classified: list[Finding] = []
    for finding in discovered:
        entry = allowlist.get(finding.allowlist_key())
        if entry is None:
            continue
        classified.append(
            Finding(
                **{
                    **asdict(finding),
                    "classification": entry["classification"],
                    "rationale": entry["rationale"],
                    "owner": entry["owner"],
                }
            )
        )
    counts_by_classification = {
        name: sum(item.classification == name for item in classified)
        for name in sorted(CLASSIFICATIONS)
    }
    counts_by_provider = {
        provider: sum(item.provider == provider for item in classified)
        for provider in sorted({item.provider for item in classified})
    }
    blockers = [asdict(item) for item in classified if item.classification == BLOCKER]
    inventory_aligned = not parse_errors and not unallowlisted and not stale
    certified = inventory_aligned and not blockers
    return {
        "schema": "aureon.economic-mutation-census.v1",
        "root": str(root),
        "allowlist": str(allowlist_path),
        "source_files_scanned": len(paths),
        "detected_count": len(discovered),
        "classified_count": len(classified),
        "counts_by_classification": counts_by_classification,
        "counts_by_provider": counts_by_provider,
        "inventory_aligned": inventory_aligned,
        "certified_no_bypass": certified,
        "blocker_count": len(blockers),
        "blockers": blockers,
        "migration_batches": _migration_batches(blockers),
        "unallowlisted": unallowlisted,
        "stale_allowlist_entries": stale,
        "parse_errors": parse_errors,
        "findings": [asdict(item) for item in classified],
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--allowlist", type=Path, default=DEFAULT_ALLOWLIST)
    parser.add_argument(
        "--report-only",
        action="store_true",
        help="Return zero for a complete inventory even while known blockers remain.",
    )
    parser.add_argument(
        "--compact",
        action="store_true",
        help="Emit compact JSON instead of pretty-printed JSON.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        result = audit(allowlist_path=args.allowlist)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"schema": "aureon.economic-mutation-census.v1", "error": str(exc)}))
        return 2
    print(
        json.dumps(
            result,
            sort_keys=True,
            indent=None if args.compact else 2,
            separators=(",", ":") if args.compact else None,
        )
    )
    if not result["inventory_aligned"]:
        return 2
    if result["blocker_count"] and not args.report_only:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Read the Queen source-law HOLD/EXECUTE gate. Do not place an order.

The numbers come from ``aureon/queen/queen_source_law.py`` only when that
file's git blob is the blob at the public pin. This module does not import
``aureon.queen``. Importing that package boots ``QueenLayer``. It does not
import an exchange, the miner, or a trading client.

``math_action`` is the comparison. ``public_action`` is HOLD. Live orders are
off. No parameter and no environment variable turns them on.
``AUREON_SOURCE_LAW_ENTRY`` may only raise the entry floor. A lower value is
ignored, matching the source-law rule that the gate may rise and may not fall.
"""

from __future__ import annotations

import ast
import math
import os
import sys
from pathlib import Path
from typing import Any

_LAW = Path("aureon") / "queen" / "queen_source_law.py"
_ENTRY_NAME = "_ENTRY_FLOOR"
_NODE_NAME = "_MIN_NODE_CONFIDENCE"
_BANNED = (
    "aureon.exchanges",
    "aureon.miner",
    "aureon.trading",
    "aureon.bots",
    "aureon.bots_intelligence",
    "aureon.bridges",
    "aureon.scanners",
    "unified_margin_trader",
)


def _finite(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    if not math.isfinite(number):
        return None
    return number


def _order_fields() -> dict[str, Any]:
    """The public order line. It is not read from the caller."""

    return {
        "economic_mutation": False,
        "exchange_calls": "not_performed",
        "live_orders": "off",
        "order_permission": "refused",
        "orders_placed": False,
        "public_action": "HOLD",
        "read_gated": True,
        "release_boundary": "HOLD",
    }


def _banned_now(before: set[str]) -> list[str]:
    loaded = []
    for name in sys.modules:
        if name in before:
            continue
        if name in _BANNED or name.startswith(tuple(prefix + "." for prefix in _BANNED)):
            loaded.append(name)
    return sorted(loaded)


def _module_float(tree: ast.AST, name: str) -> float | None:
    if not isinstance(tree, ast.Module):
        return None
    for node in tree.body:
        value: ast.expr | None
        names: list[str]
        if isinstance(node, ast.Assign):
            names = [target.id for target in node.targets if isinstance(target, ast.Name)]
            value = node.value
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            names = [node.target.id]
            value = node.value
        else:
            continue
        if name not in names or not isinstance(value, ast.Constant):
            continue
        number = _finite(value.value)
        if number is not None:
            return number
    return None


def _raised_floor(pinned: float) -> float:
    """Entry gate may rise. An env value below the pinned floor does not apply."""

    raw = os.environ.get("AUREON_SOURCE_LAW_ENTRY", "").strip()
    if not raw:
        return pinned
    try:
        raised = float(raw)
    except ValueError:
        return pinned
    if not math.isfinite(raised):
        return pinned
    return min(1.0, max(pinned, raised))


def _cited_floors() -> tuple[dict[str, float] | None, str | None]:
    from aureon_public.guard_loader import PINNED_COMMIT
    from aureon_public.paths import repo_root
    from aureon_public.pin_blob import checkout_blob_refusal

    root = repo_root()
    path = root / _LAW
    refusal = checkout_blob_refusal(path, root, PINNED_COMMIT)
    if refusal:
        return None, refusal
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (OSError, SyntaxError) as exc:
        return None, f"source law did not parse: {type(exc).__name__}"
    entry = _module_float(tree, _ENTRY_NAME)
    node = _module_float(tree, _NODE_NAME)
    if entry is None or node is None:
        return None, "source law entry floor was not in the pinned file"
    if not 0.0 < entry <= 1.0 or not 0.0 < node <= 1.0:
        return None, "source law floor is outside (0, 1]"
    return {"entry_floor": _raised_floor(entry), "node_floor": node, "pinned_entry_floor": entry}, None


def source_law_reading(
    coherence_gamma: float | None = None,
    lowest_node_confidence: float | None = None,
) -> dict[str, Any]:
    """Compare one reading with the pinned entry floor. Do not send an order."""

    before = set(sys.modules)
    body = _order_fields()
    body["label"] = (
        "cited. queen_source_law_gate. Live orders are off. No exchange was called."
    )
    body["provenance"] = "cited"
    body["source"] = _LAW.as_posix()
    banned = _banned_now(before)
    if banned:
        body["status"] = "unavailable"
        body["reason"] = "read loaded a banned package"
        body["banned_modules"] = banned
        body["math_action"] = "HOLD"
        return body

    gamma, gamma_error = _optional_finite(coherence_gamma, "coherence_gamma")
    lowest, lowest_error = _optional_finite(lowest_node_confidence, "lowest_node_confidence")
    if gamma_error or lowest_error:
        body["status"] = "unavailable"
        body["reason"] = gamma_error or lowest_error
        body["math_action"] = "HOLD"
        return body

    floors, refusal = _cited_floors()
    banned = _banned_now(before)
    if banned:
        body["status"] = "unavailable"
        body["reason"] = "read loaded a banned package"
        body["banned_modules"] = banned
        body["math_action"] = "HOLD"
        return body
    if floors is None:
        body["status"] = "unavailable"
        body["reason"] = refusal or "source law was not read"
        body["math_action"] = "HOLD"
        return body

    entry = floors["entry_floor"]
    node_floor = floors["node_floor"]
    body["entry_floor"] = entry
    body["node_floor"] = node_floor
    body["pinned_entry_floor"] = floors["pinned_entry_floor"]
    if gamma is None:
        body["status"] = "cited"
        body["math_action"] = "HOLD"
        body["reason"] = "no coherence reading was supplied"
        return body
    body["coherence_gamma"] = gamma
    if lowest is not None:
        body["lowest_node_confidence"] = lowest
        if lowest < node_floor:
            body["status"] = "cited"
            body["math_action"] = "HOLD"
            body["reason"] = (
                f"node confidence {lowest:.2f} is below {node_floor}. "
                "The public server does not place an order."
            )
            return body
    if gamma >= entry:
        math_action = "EXECUTE"
        reason = f"coherence {gamma:.4f} is at or above the entry floor {entry}"
    else:
        math_action = "HOLD"
        reason = f"coherence {gamma:.4f} is below the entry floor {entry}"
    body["status"] = "cited"
    body["math_action"] = math_action
    body["reason"] = reason + ". The public server does not place an order."
    return body


def _optional_finite(value: object, name: str) -> tuple[float | None, str | None]:
    if value is None:
        return None, None
    number = _finite(value)
    if number is None:
        return None, f"{name} is not a finite reading"
    return number, None

"""Shared coherence gate for the brain LLM and the plumber.

Both paths call :func:`aureon.core.hnc_field.assess_coherence` before the
queen is shown a value. A reading that is not a finite number in ``[0, 1]``
is HOLD with no order intent. Nothing in this module raises for a bad input.
"""

from __future__ import annotations

from typing import Any

from aureon.core.hnc_field import assess_coherence

__all__ = ["brain_llm_coherence", "plumber_coherence"]


def _hold(path: str, reason: str) -> dict[str, Any]:
    return {
        "path": path,
        "verdict": "HOLD",
        "order_intent": None,
        "queen_saw_value": False,
        "coherence": None,
        "action": None,
        "reason": reason,
    }


def _queen_after_check(value: float, *, advisory_open: Any) -> dict[str, Any]:
    """The queen sees only a value the shared check already accepted.

    A coherence reading is not itself a live order. ``order_intent`` stays
    empty here; the capital gate is what permits a live order.
    """

    action = "buy" if advisory_open is True and value >= 0.8 else None
    return {
        "action": action,
        "queen_saw_value": True,
        "coherence": value,
        "order_intent": None,
    }


def judge_coherence(value: Any, *, path: str, advisory_open: Any = None) -> dict[str, Any]:
    """Run the shared check, then the queen, and never let an input raise."""

    try:
        decision = assess_coherence(value)
    except Exception:
        return _hold(path, "coherence check failed closed")
    if not decision.accepted or decision.value is None or decision.verdict != "ACCEPTED":
        return _hold(path, decision.reason or "coherence is not a finite reading in [0, 1]")
    try:
        queen = _queen_after_check(decision.value, advisory_open=advisory_open)
    except Exception:
        return _hold(path, "queen step failed closed")
    return {
        "path": path,
        "verdict": "ACCEPTED",
        "order_intent": None,
        "queen_saw_value": True,
        "coherence": decision.value,
        "action": queen.get("action"),
        "advisory_open": advisory_open,
        "reason": decision.reason,
    }


def brain_llm_coherence(value: Any, *, advisory_open: Any = None) -> dict[str, Any]:
    """Brain LLM path. The shared check runs before the queen sees ``value``."""

    return judge_coherence(value, path="brain", advisory_open=advisory_open)


def plumber_coherence(value: Any, *, advisory_open: Any = None) -> dict[str, Any]:
    """Plumber path. The same shared check runs before the queen sees ``value``."""

    return judge_coherence(value, path="plumber", advisory_open=advisory_open)

"""Stage 3 and 4 read-gate tools. Each inventory call goes through dispatch.

Miner is an empty insight. Queen is the zero-point ground on a supplied field
value, without the queen package init. Exchange modules are not imported.
Key groups are labels. No order is placed.
"""

from __future__ import annotations

from typing import Any

from aureon_public.alignment_layer import label_result
from aureon_public.body import dispatch
from aureon_public.quiet import quiet
from aureon_public.stage34_gate import key_group_labels
from aureon_public.tools import _dumps


def _call(module: str, symbol: str, arguments: dict[str, Any]) -> str:
    return dispatch(module, symbol, arguments, server="public", timeout=30.0)


@quiet
def stage34_miner_insight() -> str:
    """Return MinerAIInsight.to_dict for a default insight.

    The bridge is not constructed. No adapter is loaded. The timestamp is the
    dataclass default clock, not a market reading.

    Args:
        none: The insight fields are the dataclass defaults. Label: cited.
    """

    return label_result(
        _call("miner/miner_inhouse_ai_bridge.py", "MinerAIInsight.to_dict", {}),
        "aureon/miner/miner_inhouse_ai_bridge.py",
        "Empty MinerAIInsight. The bridge is not constructed.",
    )


@quiet
def stage34_queen_ground() -> str:
    """Return compute_zpe_ground for lambda_t 1.0.

    queen/__init__.py is not executed. Persona, phase ladder, and order gates
    are not called. Trade readiness: HOLD.

    Args:
        none: lambda_t is 1.0. Label: cited.
    """

    return label_result(
        _call(
            "queen/temporal_ground.py",
            "compute_zpe_ground",
            {"lambda_t": 1.0},
        ),
        "aureon/queen/temporal_ground.py",
        "lambda_t 1.0. The queen package init is not executed.",
    )


@quiet
def stage34_key_groups() -> str:
    """Label exchange key groups without returning values.

    A complete group is redacted:<venue>. A missing group is absent:<venue>.
    Live orders stay refused. Trade readiness: HOLD.

    Args:
        none: The env is read for presence only. Label: cited.
    """

    return _dumps(
        {
            "key_groups": key_group_labels(),
            "key_material": "not read",
            "label": "cited. Key groups are labels. Values are not returned.",
            "live_orders": "refused",
            "provenance": "cited",
            "status": "cited",
            "trade_readiness": "HOLD",
        }
    )


TESTED: tuple[tuple[str, str], ...] = (
    ("miner/miner_inhouse_ai_bridge.py", "MinerAIInsight.to_dict"),
    ("queen/temporal_ground.py", "compute_zpe_ground"),
)

TOOLS: list[Any] = [
    stage34_miner_insight,
    stage34_queen_ground,
    stage34_key_groups,
]

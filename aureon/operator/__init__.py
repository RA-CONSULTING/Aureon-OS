"""
Aureon Operator — the switchboard that runs many AIs through the Aureon repo.

See ``docs/architecture/AUREON_OPERATOR_SWITCHBOARD.md`` for the full picture.

    from aureon.operator import AureonOperator, run_operator
    print(run_operator("How does Aureon integrate data across systems?").text)
"""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from aureon.operator.aureon_operator import AureonOperator, run_operator
    from aureon.operator.cognition import AureonCognition, run_cognition
    from aureon.operator.schemas import (
        CognitionResult,
        ConsensusReading,
        GroundingContext,
        OperatorResponse,
        ProviderAnswer,
        ToolInvocation,
    )


_LAZY_EXPORTS = {
    "AureonOperator": ("aureon.operator.aureon_operator", "AureonOperator"),
    "run_operator": ("aureon.operator.aureon_operator", "run_operator"),
    "AureonCognition": ("aureon.operator.cognition", "AureonCognition"),
    "run_cognition": ("aureon.operator.cognition", "run_cognition"),
    "OperatorResponse": ("aureon.operator.schemas", "OperatorResponse"),
    "ProviderAnswer": ("aureon.operator.schemas", "ProviderAnswer"),
    "GroundingContext": ("aureon.operator.schemas", "GroundingContext"),
    "ConsensusReading": ("aureon.operator.schemas", "ConsensusReading"),
    "ToolInvocation": ("aureon.operator.schemas", "ToolInvocation"),
    "CognitionResult": ("aureon.operator.schemas", "CognitionResult"),
}


def __getattr__(name: str) -> Any:
    """Load an operator surface only when that exact surface is requested."""

    target = _LAZY_EXPORTS.get(name)
    if target is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_name, attribute = target
    value = getattr(importlib.import_module(module_name), attribute)
    globals()[name] = value
    return value


__all__ = [
    "AureonOperator",
    "run_operator",
    "AureonCognition",
    "run_cognition",
    "OperatorResponse",
    "ProviderAnswer",
    "GroundingContext",
    "ConsensusReading",
    "ToolInvocation",
    "CognitionResult",
]

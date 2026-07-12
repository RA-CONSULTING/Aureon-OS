"""
Aureon Operator — the switchboard that runs many AIs through the Aureon repo.

See ``docs/architecture/AUREON_OPERATOR_SWITCHBOARD.md`` for the full picture.

    from aureon.operator import AureonOperator, run_operator
    print(run_operator("How does Aureon integrate data across systems?").text)
"""

from aureon.operator.aureon_operator import AureonOperator, run_operator
from aureon.operator.schemas import (
    CognitionResult,
    ConsensusReading,
    GroundingContext,
    OperatorResponse,
    ProviderAnswer,
    ToolInvocation,
)


def __getattr__(name):
    # Lazy so importing the package stays light (cognition pulls the agent loop,
    # tool registry, repo index, etc. only when actually used).
    if name in ("AureonCognition", "run_cognition"):
        from aureon.operator import cognition as _c

        return getattr(_c, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


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

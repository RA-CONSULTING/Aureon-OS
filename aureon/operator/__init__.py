"""
Aureon Operator — the switchboard that runs many AIs through the Aureon repo.

See ``docs/architecture/AUREON_OPERATOR_SWITCHBOARD.md`` for the full picture.

    from aureon.operator import AureonOperator, run_operator
    print(run_operator("How does Aureon integrate data across systems?").text)
"""

from typing import Any

_OPERATOR_EXPORTS = {"AureonOperator", "run_operator"}
_COGNITION_EXPORTS = {"AureonCognition", "run_cognition"}
_SCHEMA_EXPORTS = {
    "CognitionResult",
    "ConsensusReading",
    "GroundingContext",
    "OperatorResponse",
    "ProviderAnswer",
    "ToolInvocation",
}


def __getattr__(name: str) -> Any:
    # Keep package discovery side-effect-free. The operator, cognition loop,
    # providers, and schema graph load only when their public name is used.
    if name in _OPERATOR_EXPORTS:
        from aureon.operator import aureon_operator as _operator

        return getattr(_operator, name)
    if name in _COGNITION_EXPORTS:
        from aureon.operator import cognition as _c

        return getattr(_c, name)
    if name in _SCHEMA_EXPORTS:
        from aureon.operator import schemas as _schemas

        return getattr(_schemas, name)
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

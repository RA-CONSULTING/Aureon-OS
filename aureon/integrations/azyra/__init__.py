"""Azyra WMS integration — gated desktop operator bridge, tools, and the
autonomous warehouse-fix pass. All live actions run through explicit gates and
report honest blockers; see ``docs/azyra_warehouse_admin_reality_check.md``.
"""

from aureon.integrations.azyra.operator_bridge import ActionResult, AzyraOperatorBridge
from aureon.integrations.azyra.tools import (
    AZYRA_OPERATOR_TOOL_NAMES,
    get_azyra_operator_bridge,
    register_azyra_operator_tools,
)

__all__ = [
    "ActionResult",
    "AzyraOperatorBridge",
    "AZYRA_OPERATOR_TOOL_NAMES",
    "get_azyra_operator_bridge",
    "register_azyra_operator_tools",
]

"""Office logistics/admin integration — capability matrix, solo operator cycle,
and ToolRegistry bindings. Read/plan/report by default; every live mutation
escalates to its own gates (Azyra operator gates or AUREON_ADMIN_LIVE_MODE).
"""

from aureon.integrations.office.capability_matrix import build_logistics_admin_capability_matrix
from aureon.integrations.office.solo_operator import run_logistics_office_solo_cycle
from aureon.integrations.office.tools import (
    OFFICE_LOGISTICS_TOOL_NAMES,
    register_office_logistics_tools,
)

__all__ = [
    "build_logistics_admin_capability_matrix",
    "run_logistics_office_solo_cycle",
    "OFFICE_LOGISTICS_TOOL_NAMES",
    "register_office_logistics_tools",
]

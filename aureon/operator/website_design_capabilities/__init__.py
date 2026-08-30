"""Read-only implementations for Aureon's website design capability set.

Every public capability in this package is deterministic for the supplied
files/data.  The package audits or prepares evidence; it never writes website
files, calls providers, handles credentials, or grants deployment authority.
"""

from aureon.operator.website_design_capabilities.common import (
    RESULT_SCHEMA,
    CapabilityFinding,
    CapabilityInputError,
    CapabilityResult,
    Severity,
)

__all__ = [
    "CapabilityFinding",
    "CapabilityInputError",
    "CapabilityResult",
    "RESULT_SCHEMA",
    "Severity",
]

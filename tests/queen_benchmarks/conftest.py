"""Seed benchmark tests. When QUEEN_MUTANT_SPEC is set (mutation check only),
swap the named mutant in before any test module imports its target. (Not an
AUREON_* name: the root conftest strips those from the environment.)"""

import json
import os

_SPEC = os.environ.get("QUEEN_MUTANT_SPEC")
if _SPEC:
    from aureon.autonomous.queen_benchmark_gate import apply_mutant

    apply_mutant(json.loads(_SPEC))

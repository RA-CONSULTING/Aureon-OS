"""Fresh-process containment probe for the archived full-pathway stress body."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def test_full_pathway_holds_before_subsystem_construction_in_fresh_process(
    tmp_path: Path,
) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    harness = repo_root / "tests" / "stress" / "stress_test_full_pathway.py"
    probe = f"""
import importlib.util
import sys
import threading

spec = importlib.util.spec_from_file_location("held_full_pathway", {str(harness)!r})
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
before_threads = {{thread.ident for thread in threading.enumerate()}}
spec.loader.exec_module(module)

def trap(*_args, **_kwargs):
    raise AssertionError("held stress harness constructed a subsystem")

for name in (
    "ThoughtBus", "AureonVault", "BusFlightCheck", "GoalDispatchBridge",
    "HashResonanceIndex", "PersonaActuator", "SymbolicLifeBridge",
    "TemporalCausalityLaw", "VaultFeedAudit",
):
    setattr(module, name, trap)

try:
    module.run(n_events=1)
except RuntimeError as exc:
    assert str(exc) == module.STRESS_FULL_PATHWAY_RELEASE_HOLD
else:
    raise AssertionError("stress harness did not return its release HOLD")

assert {{thread.ident for thread in threading.enumerate()}} == before_threads
print("fresh-process-no-effect")
"""
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    completed = subprocess.run(
        [sys.executable, "-c", probe],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert "fresh-process-no-effect" in completed.stdout
    assert list(tmp_path.iterdir()) == []

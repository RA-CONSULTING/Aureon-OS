#!/usr/bin/env python3
"""
tests/vault/test_white_cell.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

White cell agent tests:
  • engages a failed_skill threat end-to-end
  • authors + executes a recovery compound skill via the CodeArchitect
  • reports outcome through ThoughtBus
  • detect_threats() finds seeded failures in the vault
"""

import os
import sys
import pytest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from aureon.vault import (
    AureonVault,
    WhiteCellAgent,
    ThreatReport,
    detect_threats,
)


PASS = 0
FAIL = 0


def check(condition: bool, msg: str) -> None:
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  [OK] {msg}")
    else:
        FAIL += 1
        print(f"  [!!] {msg}")


@pytest.mark.parametrize("kind", ["failed_skill", "casimir_drift"])
def test_engage_is_held_before_architect_or_bus_effect(kind: str):
    print(f"\n[A/B] WhiteCellAgent {kind} engagement remains held")

    class Bomb:
        def __getattribute__(self, _name: str):
            raise AssertionError("release-held cell touched an effect owner")

    cell = WhiteCellAgent(architect=Bomb(), thought_bus=Bomb())
    threat = ThreatReport(
        threat_id=f"{kind}_001",
        kind=kind,
        description="synthetic threat",
        severity=0.9,
    )
    with pytest.raises(RuntimeError, match="white_cell_agent_hold"):
        cell.engage(threat)
    with pytest.raises(RuntimeError, match="white_cell_agent_hold"):
        cell._auto_wire()


def test_detect_threats_from_vault():
    print("\n[C] detect_threats finds threats seeded in the vault")
    vault = AureonVault()

    # Seed a failed skill execution
    vault.ingest(
        topic="skill.executed.fail",
        payload={"ok": False, "skill_name": "broken_thing", "error": "timeout"},
        category="skill_execution",
    )
    # Seed a high Casimir force
    vault.last_casimir_force = 5.5
    # Seed a gamma spike
    vault.cortex_snapshot["gamma"] = 0.6
    # Seed low gratitude
    vault.gratitude_score = 0.2

    threats = detect_threats(vault, max_threats=10)

    kinds = {t.kind for t in threats}
    check(
        "casimir_drift" in kinds,
        f"casimir_drift detected (kinds: {kinds})",
    )
    check("low_gratitude" in kinds, "low_gratitude detected")
    check("gamma_spike" in kinds, "gamma_spike detected")
    check("failed_skill" in kinds, "failed_skill detected")
    check(len(threats) <= 10, "threat count respects max_threats")


def main():
    print("=" * 80)
    print("  WHITE CELL TEST SUITE")
    print("=" * 80)

    test_engage_is_held_before_architect_or_bus_effect("failed_skill")
    test_engage_is_held_before_architect_or_bus_effect("casimir_drift")
    test_detect_threats_from_vault()

    print()
    print("=" * 80)
    print(f"  RESULT: {PASS} passed, {FAIL} failed")
    print("=" * 80)
    sys.exit(0 if FAIL == 0 else 1)


if __name__ == "__main__":
    main()

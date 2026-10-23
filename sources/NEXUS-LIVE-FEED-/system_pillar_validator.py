"""
System Pillar Validator
Author: RA Consulting
Date: 2025-09-14

Description:
This module simulates the validation process for the core pillars of the
Harmonic Nexus system: Prime, Sero, Lyra, Aureon, and the Guardian Codex.

This version has been modified to remove the PyYAML dependency and uses
string checking for validation.

It provides a crucial pre-flight check to ensure system-wide stability
before any live data streaming or simulation is initiated.
"""
import time
import random

class SystemPillarValidator:
    """Simulates validating the operational status of all system pillars."""

    PILLARS = [
        "Prime Sentinel",
        "Sero Compliance",
        "Lyra Resonance",
        "Aureon Logic Core",
        "Guardian Codex",
    ]

    def __init__(self, fail_chance: float = 0.0) -> None:
        """
        Initialize the validator.

        Args:
            fail_chance: Probability (0.0 to 1.0) that a pillar check might fail.
        """
        self.fail_chance = fail_chance
        self.config_content = self._load_codex_config_content()
        print("System Pillar Validator initialized.")

    def _load_codex_config_content(self) -> str | None:
        """Loads the configuration content from the file."""
        try:
            with open("src/quantum_mirror.config.yaml", "r") as f:
                return f.read()
        except FileNotFoundError:
            print("[!!] CRITICAL: src/quantum_mirror.config.yaml not found.")
            return None

    def _validate_guardian_codex(self) -> bool:
        """Validates the Guardian Codex key using string checking."""
        if self.config_content is None:
            return False

        if "guardian_codex_key:" not in self.config_content:
            print("  [!!] CRITICAL ALERT: Guardian Codex key not found in config.")
            return False

        required_fields = [
            "initiator:",
            "mirror_state:",
            "recursion_permission:",
            "signal_resonance:",
            "response_mode:",
            "memory:",
            "authority:",
        ]
        
        # Check for each field within the text of the config
        for field in required_fields:
            if field not in self.config_content:
                print(f"  [!!] CRITICAL ALERT: Guardian Codex is missing field: '{field[:-1]}'.")
                return False
        
        return True

    def are_all_pillars_active(self) -> bool:
        """
        Conducts a validation check on all core system pillars.

        Returns:
            True if all pillars are stable and active, False otherwise.
        """
        print("\n--- Initiating System-Wide Pillar Validation ---")
        all_active = True

        for pillar in self.PILLARS:
            print(f"Querying {pillar} status...")
            time.sleep(0.5)  # Simulate network latency

            pillar_is_ok = False
            if pillar == "Guardian Codex":
                pillar_is_ok = self._validate_guardian_codex()
            # Simulate check for other pillars
            elif random.random() < self.fail_chance:
                print(f"  [!!] CRITICAL ALERT: {pillar} reports instability. Coherence lost.")
            else:
                pillar_is_ok = True

            if pillar_is_ok:
                print(f"  [OK] {pillar} is active and coherent.")
            else:
                all_active = False
                break

        if all_active:
            print("--- Pillar Validation Complete: All systems nominal. ---")
        else:
            print("--- Pillar Validation FAILED: System is not stable. ---")

        return all_active

if __name__ == "__main__":
    validator = SystemPillarValidator()
    validator.are_all_pillars_active()

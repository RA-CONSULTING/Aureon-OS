#!/usr/bin/env python3
"""Zero-dependency fail-closed facade for the unreleased Aureon ICS.

The reconciled legacy implementation is retained in
``integrated_cognitive_system_unreleased.py``. That module raises before any
subsystem import so importing this public facade cannot load dotenv files,
probe providers, create sockets, start threads, or mutate operator state.
"""

from __future__ import annotations

from typing import Any, Dict

ICS_HOLD_REASON = "production_magic_star_release_unavailable"


def integrated_cognitive_system_security_preflight() -> Dict[str, Any]:
    """Return the non-secret production release state."""

    return {
        "schema": "aureon.integrated-cognitive-system.security-preflight.v1",
        "status": "HOLD",
        "reason_code": ICS_HOLD_REASON,
        "subsystem_imports_performed": False,
        "credentials_loaded": False,
        "network_started": False,
        "threads_started": False,
        "production_magic_star_release_available": False,
        "production_ready": False,
    }


def _background_side_effects_suppressed() -> bool:
    """Compatibility readback: this facade always suppresses effects."""

    return True


class IntegratedCognitiveSystem:
    """Inert compatibility shell; every execution entrypoint is held."""

    def __init__(self) -> None:
        self._running = False
        self._tick_thread: Any | None = None
        self._vault_ui_thread: Any | None = None
        self._boot_status: Dict[str, str] = {}
        self._tick_count = 0
        self._vault_ui_port = 5566
        self._vault_ui_host = "127.0.0.1"

        # Compatibility slots remain inert and can be inspected without
        # importing or constructing their former implementations.
        for name in (
            "thought_bus",
            "contract_stack",
            "vault",
            "lambda_engine",
            "cortex",
            "feedback_loop",
            "sentient_loop",
            "agent_core",
            "action_bridge",
            "being_model",
            "elephant_memory",
            "self_dialogue",
            "auris",
            "goal_engine",
            "dashboard",
            "phi_bridge",
            "vault_app",
            "swarm",
            "temporal_ground",
            "accounting_context",
            "saas_cognition",
        ):
            setattr(self, name, None)

    @staticmethod
    def security_preflight() -> Dict[str, Any]:
        return integrated_cognitive_system_security_preflight()

    def boot(self) -> Dict[str, str]:
        raise RuntimeError(
            f"integrated_cognitive_system_boot_hold:{ICS_HOLD_REASON}"
        )

    def run(self, lan: bool = False, remote: bool = False, port: int = 5566) -> None:
        _ = port
        if lan or remote:
            raise RuntimeError(
                f"vault_ui_external_exposure_hold:{ICS_HOLD_REASON}"
            )
        raise RuntimeError(
            f"integrated_cognitive_system_runtime_hold:{ICS_HOLD_REASON}"
        )

    def _start_tick_thread(self) -> None:
        raise RuntimeError(
            f"integrated_cognitive_tick_start_hold:{ICS_HOLD_REASON}"
        )

    def _unified_cognitive_tick(self) -> None:
        raise RuntimeError(
            f"integrated_cognitive_tick_hold:{ICS_HOLD_REASON}"
        )

    def _start_vault_ui(self, host: str = "127.0.0.1", port: int = 5566) -> None:
        _ = host, port
        raise RuntimeError(
            f"integrated_vault_ui_start_hold:{ICS_HOLD_REASON}"
        )

    def _start_tunnel(self, port: int) -> None:
        _ = port
        return None

    def process_user_input(self, text: str) -> None:
        _ = text
        raise RuntimeError(
            f"integrated_cognitive_input_hold:{ICS_HOLD_REASON}"
        )

    def shutdown(self) -> None:
        self._running = False
        self._tick_thread = None
        self._vault_ui_thread = None


__all__ = [
    "ICS_HOLD_REASON",
    "IntegratedCognitiveSystem",
    "integrated_cognitive_system_security_preflight",
]

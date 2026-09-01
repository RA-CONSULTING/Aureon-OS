"""
WhiteCellAgent — Immune-System Pattern Agent
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

"Agents act like white blood cells ... mycelium cortex active feedback loop."

A white cell takes one detected threat (a failed skill, a blocked operation,
a cycle detection, a missing capability) and:

  1. Analyses the threat — what's failing and why
  2. Proposes a recovery path through the CodeArchitect
  3. Validates the authored skill through the 3-gate validator
  4. Executes the recovery
  5. Reports the outcome back to the vault's gratitude loop
  6. Publishes a 'white_cell.outcome' event on the ThoughtBus so the
     mycelium pathways can strengthen/weaken accordingly

White cells are short-lived — one cell per threat per tick. They don't
persist across ticks; the HNCDeployer decides each tick how many new ones
to spawn.
"""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger("aureon.vault.white_cell")


@dataclass
class ThreatReport:
    """One detected threat to engage."""
    threat_id: str
    kind: str                          # failed_skill | low_gratitude | gamma_spike | casimir_drift
    description: str
    source_content_id: Optional[str] = None
    severity: float = 0.5              # [0, 1]
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WhiteCellOutcome:
    """Result of engaging one threat."""
    cell_id: str
    threat_id: str
    engaged_at: float
    success: bool
    recovery_skill_name: Optional[str] = None
    duration_s: float = 0.0
    reasoning: str = ""
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cell_id": self.cell_id,
            "threat_id": self.threat_id,
            "engaged_at": self.engaged_at,
            "success": self.success,
            "recovery_skill_name": self.recovery_skill_name,
            "duration_s": round(self.duration_s, 4),
            "reasoning": self.reasoning,
            "error": self.error,
        }


class WhiteCellAgent:
    """
    Immune-system pattern agent. Each instance engages exactly one threat.

    Usage:
        cell = WhiteCellAgent(architect=my_architect)
        outcome = cell.engage(threat)
    """

    def __init__(
        self,
        architect: Any = None,
        thought_bus: Any = None,
        auto_wire: bool = False,
    ):
        if auto_wire:
            raise RuntimeError(
                "white_cell_agent_hold:production_magic_star_release_unavailable"
            )
        self.cell_id = uuid.uuid4().hex[:8]
        self.architect = architect
        self.thought_bus = thought_bus
        if auto_wire:
            self._auto_wire()

    def _auto_wire(self) -> None:
        raise RuntimeError(
            "white_cell_agent_hold:production_magic_star_release_unavailable"
        )
        if self.architect is None:
            try:
                from aureon.code_architect import get_code_architect
                self.architect = get_code_architect()
            except Exception:
                self.architect = None
        if self.thought_bus is None:
            try:
                from aureon.core.aureon_thought_bus import ThoughtBus
                self.thought_bus = ThoughtBus()
            except Exception:
                self.thought_bus = None

    # ─────────────────────────────────────────────────────────────────────
    # Engage
    # ─────────────────────────────────────────────────────────────────────

    def engage(self, threat: ThreatReport) -> WhiteCellOutcome:
        """
        Engage one threat:
          - author a compound recovery skill via the CodeArchitect
          - execute it
          - publish the outcome
        """
        raise RuntimeError(
            "white_cell_agent_hold:production_magic_star_release_unavailable"
        )
        start = time.time()
        outcome = WhiteCellOutcome(
            cell_id=self.cell_id,
            threat_id=threat.threat_id,
            engaged_at=start,
            success=False,
        )

        if self.architect is None:
            outcome.error = "no_architect"
            outcome.reasoning = "cell has no code architect to author recovery"
            outcome.duration_s = time.time() - start
            self._publish(outcome, threat)
            return outcome

        try:
            # Ensure atomics exist (idempotent)
            try:
                self.architect.bootstrap_atomics()
            except Exception:
                pass

            # Pick the recovery strategy based on threat kind
            recovery_deps = self._recovery_deps_for(threat)
            recovery_name = f"recover_{threat.kind}_{threat.threat_id}"

            # Author the compound recovery skill
            skill = self.architect.teach_compound(
                name=recovery_name,
                dependency_skill_names=recovery_deps,
                description=f"White cell recovery for {threat.kind}: {threat.description}",
            )
            if skill is None:
                outcome.error = "skill_composition_failed"
                outcome.reasoning = f"could not compose {recovery_name}"
                outcome.duration_s = time.time() - start
                self._publish(outcome, threat)
                return outcome

            outcome.recovery_skill_name = skill.name

            # Execute the recovery
            result = self.architect.execute_skill(skill.name)
            inner = result.return_value if isinstance(result.return_value, dict) else {}
            inner_ok = bool(result.ok and (inner.get("ok", True)))

            outcome.success = inner_ok
            outcome.reasoning = (
                f"authored+ran {skill.name} "
                f"alignment={skill.pillar_alignment_score:.3f} "
                f"status={skill.status.value}"
            )
            if not inner_ok:
                outcome.error = str(result.error or inner.get("error", "unknown"))

        except Exception as e:
            outcome.error = f"{type(e).__name__}: {e}"
            outcome.reasoning = "exception during engagement"

        outcome.duration_s = time.time() - start
        self._publish(outcome, threat)
        return outcome

    def _recovery_deps_for(self, threat: ThreatReport) -> List[str]:
        """Return a short list of atomic/compound skills to compose as recovery."""
        if threat.kind == "failed_skill":
            return ["screenshot", "list_windows", "get_active_window"]
        if threat.kind == "low_gratitude":
            return ["screenshot", "get_cursor_position", "wait"]
        if threat.kind == "gamma_spike":
            return ["screenshot", "list_windows", "get_active_window", "wait"]
        if threat.kind == "casimir_drift":
            return ["screenshot", "get_screen_size", "list_windows"]
        return ["screenshot"]

    def _publish(self, outcome: WhiteCellOutcome, threat: ThreatReport) -> None:
        raise RuntimeError(
            "white_cell_agent_hold:production_magic_star_release_unavailable"
        )
        if not self.thought_bus:
            return
        try:
            from aureon.core.aureon_thought_bus import Thought
            self.thought_bus.publish(Thought(
                source="vault.white_cell",
                topic="white_cell.outcome",
                payload={
                    "threat_kind": threat.kind,
                    "threat_id": threat.threat_id,
                    "threat_severity": threat.severity,
                    "cell_id": outcome.cell_id,
                    "success": outcome.success,
                    "recovery_skill_name": outcome.recovery_skill_name,
                    "duration_s": outcome.duration_s,
                    "error": outcome.error,
                },
            ))
        except Exception:
            pass


# ─────────────────────────────────────────────────────────────────────────────
# Threat detection
# ─────────────────────────────────────────────────────────────────────────────


def detect_threats(vault: Any, max_threats: int = 4) -> List[ThreatReport]:
    """
    Scan the vault for signals that warrant white cell engagement.
    Returns a list (possibly empty) of ThreatReport objects.
    """
    threats: List[ThreatReport] = []

    # Casimir drift
    force = float(getattr(vault, "last_casimir_force", 0.0) or 0.0)
    if force > 4.0:
        threats.append(ThreatReport(
            threat_id=f"casimir_{int(force * 100)}",
            kind="casimir_drift",
            description=f"Casimir drift force {force:.2f}",
            severity=min(1.0, force / 10.0),
        ))

    # Gratitude low → recover
    gratitude = float(getattr(vault, "gratitude_score", 0.5) or 0.5)
    if gratitude < 0.35:
        threats.append(ThreatReport(
            threat_id=f"gratitude_{int(gratitude * 100)}",
            kind="low_gratitude",
            description=f"gratitude score {gratitude:.2f}",
            severity=1.0 - gratitude,
        ))

    # Gamma spike → attention
    cortex = getattr(vault, "cortex_snapshot", {}) or {}
    gamma = float(cortex.get("gamma", 0.0) or 0.0)
    if gamma > 0.3:
        threats.append(ThreatReport(
            threat_id=f"gamma_{int(gamma * 100)}",
            kind="gamma_spike",
            description=f"gamma amplitude {gamma:.2f}",
            severity=min(1.0, gamma),
        ))

    # Failed skill execution cards in vault
    try:
        recent_execs = vault.by_category("skill_execution", n=20)
    except Exception:
        recent_execs = []
    failed = [c for c in recent_execs if not c.payload.get("ok", True)]
    if failed:
        top = failed[-1]
        threats.append(ThreatReport(
            threat_id=f"failed_{top.content_id}",
            kind="failed_skill",
            description=str(top.payload.get("error", "unknown") or "unknown"),
            source_content_id=top.content_id,
            severity=0.7,
            metadata={"skill_name": top.payload.get("skill_name", "")},
        ))

    return threats[:max_threats]

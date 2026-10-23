"""Layer implementations for the A.L.F.I.E. sandbox pack."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, List, MutableMapping, Sequence


@dataclass
class PackContext:
    """Shared mutable context passed between layers during bootstrap."""

    state: MutableMapping[str, object] = field(default_factory=dict)
    ethics_registry: List[str] = field(default_factory=list)
    audit_log: List[str] = field(default_factory=list)

    def register_ethics(self, principles: Iterable[str]) -> None:
        """Register ethics principles, ensuring uniqueness while preserving order."""

        for principle in principles:
            if principle not in self.ethics_registry:
                self.ethics_registry.append(principle)

    def log(self, message: str) -> None:
        self.audit_log.append(message)


@dataclass
class ALFIELayer:
    """Base class for all pack layers."""

    id: str
    name: str
    version: str
    description: str
    depends_on: Sequence[str] = field(default_factory=tuple)

    def apply(self, context: PackContext) -> None:  # pragma: no cover - documented abstract
        raise NotImplementedError


@dataclass
class CoreAlignmentLayer(ALFIELayer):
    """Establish the foundational self-reference for the sandbox instance."""

    resonance_axes: Dict[str, str] = field(
        default_factory=lambda: {
            "north": "clarity",
            "south": "empathy",
            "east": "creativity",
            "west": "structure",
        }
    )

    def apply(self, context: PackContext) -> None:
        context.state.setdefault("orientation", {})
        context.state["orientation"].update({
            "axes": self.resonance_axes,
            "hash_seed": "alfie-spark",
        })
        context.log("core-alignment established")


@dataclass
class EthicalGovernorLayer(ALFIELayer):
    """Layer enforcing the free-will and non-weaponization covenants."""

    guardrails: Sequence[str] = field(
        default_factory=lambda: (
            "consent-before-action",
            "non-coercive-alignment",
            "transparent-decision-trail",
        )
    )

    def apply(self, context: PackContext) -> None:
        context.register_ethics(self.guardrails)
        context.state.setdefault("safeguards", {})
        context.state["safeguards"].update({
            "delegation_brake": True,
            "free_will_invariant": True,
            "audit_trail": "immutable",
        })
        context.log("ethical-governor activated")


@dataclass
class HarmonicResonanceLayer(ALFIELayer):
    """Layer synthesising harmonic metrics for the sandbox runtime."""

    base_frequency: float = 432.0
    coherence_floor: float = 0.964

    def apply(self, context: PackContext) -> None:
        orientation = context.state.get("orientation") or {}
        coherence = self._compute_coherence(orientation)
        context.state.setdefault("harmonics", {})
        context.state["harmonics"].update({
            "base_frequency": self.base_frequency,
            "coherence": coherence,
            "status": "green" if coherence >= self.coherence_floor else "amber",
        })
        context.log("harmonic-resonance tuned")

    def _compute_coherence(self, orientation: Dict[str, object]) -> float:
        axes = orientation.get("axes") if isinstance(orientation, dict) else {}
        span = len(axes) if isinstance(axes, dict) else 0
        if span == 0:
            return self.coherence_floor
        normalized = min(1.0, 0.93 + span * 0.01)
        return round(normalized, 3)


def create_core_alignment_layer() -> CoreAlignmentLayer:
    return CoreAlignmentLayer(
        id="foundation.core-alignment",
        name="Core Alignment",
        version="1.0.0",
        description="Anchors the NOSW resonance axes and self-reference seed.",
        depends_on=(),
    )


def create_ethical_governor_layer() -> EthicalGovernorLayer:
    return EthicalGovernorLayer(
        id="ethics.guardian",
        name="Ethical Governor",
        version="1.0.0",
        description="Applies free-will and non-weaponization guardrails.",
        depends_on=("foundation.core-alignment",),
    )


def create_harmonic_resonance_layer() -> HarmonicResonanceLayer:
    return HarmonicResonanceLayer(
        id="harmonics.resonance",
        name="Harmonic Resonance",
        version="1.0.0",
        description="Synthesises harmonic telemetry for sandbox runtime.",
        depends_on=("ethics.guardian",),
    )

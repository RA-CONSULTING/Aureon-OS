"""Utilities for working with the ALFIE Evolution Pack manifest."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Tuple


@dataclass(frozen=True)
class Layer:
    """Represents a single layer within the evolution pack."""

    id: str
    path: str
    required: bool
    phase: int

    def resolved_path(self, base: Path | None = None) -> Path:
        """Return the on-disk path for this layer relative to ``base``."""

        base_path = Path("." if base is None else base)
        return base_path / self.path


@dataclass(frozen=True)
class SafetyDirectives:
    """Immutable safety configuration for the evolution pack."""

    prime_directive: str
    coherence_floor: float
    explainability: bool
    no_weaponization: bool


@dataclass
class EvolutionPack:
    """In-memory representation of the ALFIE evolution pack."""

    name: str
    version: str
    generated: datetime
    entry: str  # Name of the default initialization sequence within the manifest
    layers: Dict[str, Layer]
    init_sequence: Tuple[str, ...]
    safety: SafetyDirectives

    # ------------------------------------------------------------------
    def get_layer(self, layer_id: str) -> Layer:
        """Return a layer by identifier."""

        try:
            return self.layers[layer_id]
        except KeyError as exc:  # pragma: no cover - defensive branch
            raise KeyError(f"Unknown layer '{layer_id}'") from exc

    # ------------------------------------------------------------------
    def iter_sequence_layers(self) -> Iterable[Layer]:
        """Iterate over layers according to the initialization sequence."""

        for layer_id in self.init_sequence:
            yield self.layers[layer_id]

    # ------------------------------------------------------------------
    def layers_by_phase(self) -> Dict[int, Tuple[Layer, ...]]:
        """Group layers by phase while preserving initialization order."""

        sequence_index = {layer_id: idx for idx, layer_id in enumerate(self.init_sequence)}
        phases: Dict[int, List[Layer]] = {}
        for layer in self.layers.values():
            phases.setdefault(layer.phase, []).append(layer)

        ordered: Dict[int, Tuple[Layer, ...]] = {}
        for phase, layer_list in phases.items():
            layer_list.sort(key=lambda layer: (sequence_index.get(layer.id, float("inf")), layer.id))
            ordered[phase] = tuple(layer_list)
        return ordered

    # ------------------------------------------------------------------
    def required_layers(self) -> Tuple[Layer, ...]:
        """Return required layers ordered by initialization sequence."""

        sequence_index = {layer_id: idx for idx, layer_id in enumerate(self.init_sequence)}
        required = [layer for layer in self.layers.values() if layer.required]
        required.sort(key=lambda layer: (sequence_index.get(layer.id, float("inf")), layer.id))
        return tuple(required)

    # ------------------------------------------------------------------
    def optional_layers(self) -> Tuple[Layer, ...]:
        """Return optional layers ordered by initialization sequence."""

        sequence_index = {layer_id: idx for idx, layer_id in enumerate(self.init_sequence)}
        optional = [layer for layer in self.layers.values() if not layer.required]
        optional.sort(key=lambda layer: (sequence_index.get(layer.id, float("inf")), layer.id))
        return tuple(optional)

    # ------------------------------------------------------------------
    def validate(self) -> List[str]:
        """Return a list of human-readable validation issues."""

        errors: List[str] = []
        if not self.entry:
            errors.append("Entry sequence name is empty")

        if not self.init_sequence:
            errors.append("Initialization sequence is empty")

        layer_ids = set(self.layers)
        for layer_id in self.init_sequence:
            if layer_id not in layer_ids:
                errors.append(f"Initialization sequence references unknown layer '{layer_id}'")

        for layer in self.layers.values():
            if layer.required and layer.id not in self.init_sequence:
                errors.append(f"Required layer '{layer.id}' missing from initialization sequence")

            if layer.phase < 0:
                errors.append(f"Layer '{layer.id}' has invalid phase {layer.phase}")

        return errors

    # ------------------------------------------------------------------
    def missing_files(self, base: Path) -> List[Layer]:
        """Return layers whose referenced files are absent relative to ``base``."""

        base_path = Path(base)
        sequence_index = {layer_id: idx for idx, layer_id in enumerate(self.init_sequence)}
        missing = [
            layer
            for layer in self.layers.values()
            if not layer.resolved_path(base_path).exists()
        ]
        missing.sort(key=lambda layer: (sequence_index.get(layer.id, float("inf")), layer.id))
        return missing


# ----------------------------------------------------------------------
def _parse_generated(timestamp: str) -> datetime:
    """Parse an ISO-8601 timestamp allowing a trailing ``Z``."""

    if timestamp.endswith("Z"):
        timestamp = f"{timestamp[:-1]}+00:00"
    dt = datetime.fromisoformat(timestamp)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


# ----------------------------------------------------------------------
def load_evolution_pack(json_path: Path) -> EvolutionPack:
    """Load the ALFIE evolution pack from ``json_path``."""

    with open(json_path, "r", encoding="utf-8") as fp:
        raw = json.load(fp)

    layers = {
        entry["id"]: Layer(
            id=entry["id"],
            path=entry["path"],
            required=bool(entry["required"]),
            phase=int(entry["phase"]),
        )
        for entry in raw["layers"]
    }

    sequence_name = raw["entry"]
    try:
        sequence_values = raw[sequence_name]
    except KeyError as exc:  # pragma: no cover - malformed manifest
        raise ValueError(
            f"Missing initialization sequence '{sequence_name}' in pack manifest"
        ) from exc

    if not isinstance(sequence_values, list):  # pragma: no cover - malformed manifest
        raise ValueError(
            f"Initialization sequence '{sequence_name}' must be an array"
        )

    init_sequence = tuple(str(layer_id) for layer_id in sequence_values)

    pack = EvolutionPack(
        name=raw["name"],
        version=raw["version"],
        generated=_parse_generated(raw["generated"]),
        entry=sequence_name,
        layers=layers,
        init_sequence=init_sequence,
        safety=SafetyDirectives(
            prime_directive=raw["safety"]["prime_directive"],
            coherence_floor=float(raw["safety"]["coherence_floor"]),
            explainability=bool(raw["safety"]["explainability"]),
            no_weaponization=bool(raw["safety"]["no_weaponization"]),
        ),
    )

    errors = pack.validate()
    if errors:
        raise ValueError(
            "Invalid ALFIE evolution pack: " + "; ".join(errors)
        )

    return pack


__all__ = [
    "Layer",
    "SafetyDirectives",
    "EvolutionPack",
    "load_evolution_pack",
]

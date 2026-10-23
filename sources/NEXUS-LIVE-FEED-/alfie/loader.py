"""Bootstrap helpers for the A.L.F.I.E. sandbox pack."""

from __future__ import annotations

import importlib
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Sequence

from .layers import ALFIELayer, PackContext
from .manifest import LayerSpec, Manifest, PackMetadata


@dataclass
class BootstrappedPack:
    """Result of loading the pack from a manifest."""

    metadata: PackMetadata
    layers: Sequence[ALFIELayer]
    context: PackContext


class LayerLoadError(RuntimeError):
    """Raised when a layer cannot be instantiated or validated."""


def bootstrap_from_manifest(path: Path | str) -> BootstrappedPack:
    """Load the pack described by ``path`` and execute its layers."""

    manifest = Manifest.load(path)
    context = PackContext()
    loaded_layers: List[ALFIELayer] = []
    executed_ids: List[str] = []

    for spec in manifest.layers:
        _assert_dependencies(spec.depends_on, executed_ids)
        layer = _instantiate_layer(spec)
        _assert_layer_contract(layer, spec)
        layer.apply(context)
        loaded_layers.append(layer)
        executed_ids.append(layer.id)

    context.log("pack_bootstrapped")

    return BootstrappedPack(metadata=manifest.pack, layers=tuple(loaded_layers), context=context)


def _assert_dependencies(required: Sequence[str], executed: Iterable[str]) -> None:
    executed_set = set(executed)
    missing = [dep for dep in required if dep not in executed_set]
    if missing:
        raise LayerLoadError(f"unsatisfied dependencies: {missing}")


def _instantiate_layer(spec: LayerSpec) -> ALFIELayer:
    try:
        module = importlib.import_module(spec.module)
    except ModuleNotFoundError as exc:
        raise LayerLoadError(f"layer module not found: {spec.module}") from exc

    try:
        factory = getattr(module, spec.entrypoint)
    except AttributeError as exc:
        raise LayerLoadError(
            f"layer entrypoint '{spec.entrypoint}' not found in module {spec.module}"
        ) from exc

    layer = factory()
    if not isinstance(layer, ALFIELayer):  # pragma: no cover - defensive guard
        raise LayerLoadError(f"entrypoint {spec.entrypoint} did not return an ALFIELayer instance")
    return layer


def _assert_layer_contract(layer: ALFIELayer, spec: LayerSpec) -> None:
    if layer.id != spec.id:
        raise LayerLoadError(f"layer id mismatch: {layer.id} != {spec.id}")
    if layer.version != spec.version:
        raise LayerLoadError(f"layer version mismatch for {layer.id}: {layer.version} != {spec.version}")
    if tuple(layer.depends_on) != tuple(spec.depends_on):
        raise LayerLoadError(f"layer dependencies mismatch for {layer.id}")


__all__ = [
    "BootstrappedPack",
    "LayerLoadError",
    "bootstrap_from_manifest",
]

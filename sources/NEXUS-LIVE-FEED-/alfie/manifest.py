"""Manifest schema and helpers for the A.L.F.I.E. sandbox pack."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence


class ManifestValidationError(ValueError):
    """Raised when a manifest fails schema or checksum validation."""


@dataclass(frozen=True)
class LayerSpec:
    """Definition for a single layer inside the pack."""

    id: str
    name: str
    module: str
    entrypoint: str
    version: str
    depends_on: Sequence[str]


@dataclass(frozen=True)
class PackMetadata:
    """High level metadata about the pack."""

    id: str
    name: str
    version: str
    description: str
    mission: str
    ethics: Sequence[str]


@dataclass(frozen=True)
class Manifest:
    """Concrete representation of the manifest file."""

    schema_version: str
    generated_at: datetime
    pack: PackMetadata
    layers: Sequence[LayerSpec]
    checksum: str

    @classmethod
    def load(cls, path: Path | str) -> "Manifest":
        """Load and validate a manifest from ``path``."""

        manifest_path = Path(path)
        raw = _load_json(manifest_path)
        _validate_schema(raw)

        generated_at = _parse_timestamp(raw["generated_at"])
        pack = _parse_pack(raw["pack"])
        layers = tuple(_parse_layers(raw["layers"]))

        expected_checksum = compute_checksum({
            "schema_version": raw["schema_version"],
            "generated_at": raw["generated_at"],
            "pack": raw["pack"],
            "layers": raw["layers"],
        })
        checksum = raw["checksum"]
        if checksum != expected_checksum:
            raise ManifestValidationError(
                "checksum mismatch: expected {expected}, found {found}".format(
                    expected=expected_checksum,
                    found=checksum,
                )
            )

        return cls(
            schema_version=raw["schema_version"],
            generated_at=generated_at,
            pack=pack,
            layers=layers,
            checksum=checksum,
        )


def _load_json(path: Path) -> Dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:  # pragma: no cover - surfaced in tests
        raise ManifestValidationError(f"manifest not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ManifestValidationError(f"invalid JSON: {exc}") from exc
    return data


def _validate_schema(raw: Dict[str, Any]) -> None:
    required_top = {"schema_version", "generated_at", "pack", "layers", "checksum"}
    missing = required_top.difference(raw)
    if missing:
        raise ManifestValidationError(f"missing manifest keys: {sorted(missing)}")

    if raw["schema_version"] != "1.0.0":
        raise ManifestValidationError("unsupported schema_version: {sv}".format(sv=raw["schema_version"]))

    if not isinstance(raw["layers"], list) or not raw["layers"]:
        raise ManifestValidationError("manifest must declare at least one layer")


def _parse_timestamp(value: str) -> datetime:
    if not isinstance(value, str):
        raise ManifestValidationError("generated_at must be an ISO-8601 string")

    iso_value = value.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(iso_value)
    except ValueError as exc:
        raise ManifestValidationError(f"invalid generated_at timestamp: {value}") from exc

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _parse_pack(raw_pack: Dict[str, Any]) -> PackMetadata:
    required_keys = {"id", "name", "version", "description", "mission", "ethics"}
    missing = required_keys.difference(raw_pack)
    if missing:
        raise ManifestValidationError(f"pack metadata missing keys: {sorted(missing)}")

    ethics = raw_pack["ethics"]
    if not isinstance(ethics, list) or not all(isinstance(item, str) for item in ethics):
        raise ManifestValidationError("pack.ethics must be a list of strings")

    return PackMetadata(
        id=str(raw_pack["id"]),
        name=str(raw_pack["name"]),
        version=str(raw_pack["version"]),
        description=str(raw_pack["description"]),
        mission=str(raw_pack["mission"]),
        ethics=tuple(ethics),
    )


def _parse_layers(raw_layers: Iterable[Dict[str, Any]]) -> List[LayerSpec]:
    parsed: List[LayerSpec] = []
    for entry in raw_layers:
        required_keys = {"id", "name", "module", "entrypoint", "version", "depends_on"}
        missing = required_keys.difference(entry)
        if missing:
            raise ManifestValidationError(
                "layer {layer_id} missing keys: {keys}".format(
                    layer_id=entry.get("id", "<unknown>"),
                    keys=sorted(missing),
                )
            )

        depends_on = entry["depends_on"]
        if not isinstance(depends_on, list) or not all(isinstance(dep, str) for dep in depends_on):
            raise ManifestValidationError(
                "layer {layer_id} depends_on must be a list of strings".format(layer_id=entry["id"])
            )

        parsed.append(
            LayerSpec(
                id=str(entry["id"]),
                name=str(entry["name"]),
                module=str(entry["module"]),
                entrypoint=str(entry["entrypoint"]),
                version=str(entry["version"]),
                depends_on=tuple(depends_on),
            )
        )
    return parsed


def canonicalize(value: Any) -> str:
    """Return a canonical JSON string for ``value``."""

    if isinstance(value, dict):
        items = (
            f"{json.dumps(key)}:{canonicalize(value[key])}"
            for key in sorted(value.keys())
        )
        return "{" + ",".join(items) + "}"

    if isinstance(value, list):
        return "[" + ",".join(canonicalize(item) for item in value) + "]"

    if isinstance(value, tuple):
        return "[" + ",".join(canonicalize(item) for item in value) + "]"

    return json.dumps(value)


def compute_checksum(manifest_slice: Dict[str, Any]) -> str:
    """Compute the checksum for the provided manifest slice."""

    canonical = canonicalize(manifest_slice)
    # The hash lives here to keep the manifest upgrade-safe.
    from hashlib import sha256

    digest = sha256(canonical.encode("utf-8")).hexdigest()
    return f"sha256:{digest}"

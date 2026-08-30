"""Canonical fail-closed roof for every Queen-labelled Python process."""

from __future__ import annotations

import ast
import hashlib
import json
import threading
from collections.abc import Callable
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from aureon.core.organism_composition import OrganismComposition

SCHEMA_VERSION = "aureon.queen-process-roof.v1"
MANIFEST_SCHEMA = "aureon.queen-process-manifest.v1"
REPO_ROOT = Path(__file__).resolve().parents[2]
_FACTORY_TOKEN = object()
_EXCLUDED_PARTS = frozenset({
    ".git", ".venv", "__pycache__", "archive", "archives", "build",
    "dist", "imports", "node_modules", "tests", "venv",
})
_LIFECYCLE_NAMES = frozenset({
    "boot", "main", "run", "run_dashboard", "start", "start_all",
    "start_autonomous",
})
_AUTHORITY_TOKENS = (
    "place_market_order", "place_order", "submit_order", "cancel_order",
    "close_position", "requests.post", "requests.put", "requests.delete",
    "session.post", "session.put", "session.delete", "subprocess.popen",
    "os.system",
)
_FALSE_FLAGS = {
    "action_eligible": False,
    "accounting_eligible": False,
    "learning_eligible": False,
    "actionable": False,
    "operational_eligible": False,
    "provider_eligible": False,
    "economic_mutation": False,
}


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _is_queen_source(relative: Path) -> bool:
    parts = {part.casefold() for part in relative.parts}
    return not bool(parts & _EXCLUDED_PARTS) and (
        "queen" in relative.stem.casefold() or "queen" in parts
    )


def _module_name(relative: Path) -> str:
    parts = list(relative.with_suffix("").parts)
    if parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)


def _role(relative: Path) -> str:
    parts = {part.casefold() for part in relative.parts}
    stem = relative.stem.casefold()
    if "governance" in parts or "conscience" in stem or "crown" in stem:
        return "governance"
    if "account" in str(relative).casefold() or "profit" in stem:
        return "accounting"
    if "monitor" in parts or "dashboard" in stem or "command_center" in stem:
        return "observation"
    if "autonomous" in parts or "runner" in stem or "machine" in stem:
        return "orchestration"
    if "queen" in parts:
        return "queen_faculty"
    return "queen_process"


def _entrypoints(tree: ast.Module) -> tuple[str, ...]:
    names = {
        node.name
        for node in tree.body
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
        and ("queen" in node.name.casefold() or node.name.casefold() in _LIFECYCLE_NAMES)
    }
    return tuple(sorted(names)) or ("module",)


def _effect_class(source: str, entrypoints: tuple[str, ...]) -> str:
    folded = source.casefold()
    if any(token in folded for token in _AUTHORITY_TOKENS):
        return "authority_capable"
    if any(name.casefold() in _LIFECYCLE_NAMES for name in entrypoints):
        return "active_process"
    return "advisory"


@dataclass(frozen=True, slots=True)
class QueenProcessDescriptor:
    process_id: str
    source_file: str
    module_name: str
    source_sha256: str
    role: str
    effect_class: str
    entrypoints: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.process_id.startswith("queen-process:"):
            raise ValueError("queen_process_id_required")
        if not self.source_file or not self.module_name or len(self.source_sha256) != 64:
            raise ValueError("complete_queen_process_identity_required")
        if self.role not in {
            "accounting", "governance", "observation", "orchestration",
            "queen_faculty", "queen_process",
        }:
            raise ValueError("recognized_queen_process_role_required")
        if self.effect_class not in {"active_process", "advisory", "authority_capable"}:
            raise ValueError("recognized_queen_process_effect_class_required")
        if not self.entrypoints or self.entrypoints != tuple(sorted(set(self.entrypoints))):
            raise ValueError("sorted_unique_queen_entrypoints_required")

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["entrypoints"] = list(self.entrypoints)
        return result


@dataclass(frozen=True, slots=True)
class QueenProcessManifest:
    processes: tuple[QueenProcessDescriptor, ...]
    manifest_id: str
    schema: str = MANIFEST_SCHEMA

    def __post_init__(self) -> None:
        ids = [item.process_id for item in self.processes]
        files = [item.source_file for item in self.processes]
        modules = [item.module_name for item in self.processes]
        if (
            self.schema != MANIFEST_SCHEMA
            or not self.processes
            or ids != sorted(set(ids))
            or len(files) != len(set(files))
            or len(modules) != len(set(modules))
        ):
            raise ValueError("sorted_unique_queen_process_manifest_required")
        if self.manifest_id != f"queen-process-manifest:{_sha256(self.payload())}":
            raise ValueError("queen_process_manifest_id_mismatch")

    def payload(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "processes": [item.to_dict() for item in self.processes],
        }

    def to_dict(self) -> dict[str, Any]:
        return {**self.payload(), "manifest_id": self.manifest_id}


def discover_queen_process_manifest(root: Path = REPO_ROOT) -> QueenProcessManifest:
    """Seat every active Queen-labelled source without importing it."""

    root = Path(root).resolve()
    descriptors: list[QueenProcessDescriptor] = []
    for path in sorted(root.rglob("*.py")):
        try:
            relative = path.resolve().relative_to(root)
        except ValueError:
            continue
        if not _is_queen_source(relative):
            continue
        source = path.read_text(encoding="utf-8")
        try:
            tree = ast.parse(source, filename=str(relative))
        except SyntaxError as exc:
            raise ValueError(f"queen_process_source_parse_failed:{relative.as_posix()}") from exc
        source_file = relative.as_posix()
        entrypoints = _entrypoints(tree)
        descriptors.append(
            QueenProcessDescriptor(
                process_id=(
                    "queen-process:"
                    + hashlib.sha256(source_file.encode("utf-8")).hexdigest()
                ),
                source_file=source_file,
                module_name=_module_name(relative),
                source_sha256=hashlib.sha256(source.encode("utf-8")).hexdigest(),
                role=_role(relative),
                effect_class=_effect_class(source, entrypoints),
                entrypoints=entrypoints,
            )
        )
    processes = tuple(sorted(descriptors, key=lambda item: item.process_id))
    payload = {
        "schema": MANIFEST_SCHEMA,
        "processes": [item.to_dict() for item in processes],
    }
    return QueenProcessManifest(
        processes=processes,
        manifest_id=f"queen-process-manifest:{_sha256(payload)}",
    )


@dataclass(frozen=True, slots=True)
class QueenProcessActivation:
    status: str
    reason: str | None
    process_id: str | None
    module_name: str
    instance: Any = None

    def receipt(self) -> dict[str, Any]:
        payload = {
            "schema": "aureon.queen-process-activation.v1",
            "status": self.status,
            "reason": self.reason,
            "process_id": self.process_id,
            "module_name": self.module_name,
            "truth_status": "real_observed" if self.status == "ACTIVE" else "no_data",
            "generated_values": False,
            **_FALSE_FLAGS,
        }
        payload["receipt_id"] = f"queen-activation:{_sha256(payload)}"
        return payload


class QueenProcessRoof:
    """Factory-only owner of Queen source identity and process activation."""

    def __init__(
        self,
        *,
        _factory_token: object,
        composition: OrganismComposition,
        manifest: QueenProcessManifest,
    ) -> None:
        if _factory_token is not _FACTORY_TOKEN:
            raise TypeError("use_bind_queen_process_roof")
        if not isinstance(composition, OrganismComposition):
            raise TypeError("canonical_organism_composition_required")
        if not isinstance(manifest, QueenProcessManifest):
            raise TypeError("queen_process_manifest_required")
        self._composition = composition
        self._manifest = manifest
        self._by_module = {item.module_name: item for item in manifest.processes}
        self._active: dict[str, Any] = {}
        self._lock = threading.RLock()

    @property
    def manifest(self) -> QueenProcessManifest:
        return self._manifest

    def status(self) -> dict[str, Any]:
        composition_status = self._composition.status()
        ready = composition_status.get("status") == "ready"
        payload = {
            "schema": SCHEMA_VERSION,
            "status": "ready" if ready else "hold",
            "reason": None if ready else "canonical_organism_composition_not_ready",
            "manifest_id": self._manifest.manifest_id,
            "seated_process_count": len(self._manifest.processes),
            "active_process_count": len(self._active),
            "composition_status": composition_status.get("status"),
            "economic_blocker_count": composition_status.get("economic_blocker_count"),
            "truth_status": "real_observed" if ready else "no_data",
            "generated_values": False,
            **_FALSE_FLAGS,
        }
        payload["receipt_id"] = f"queen-roof:{_sha256(payload)}"
        return payload

    def cognition_kwargs(self, module_name: str) -> dict[str, Any]:
        if module_name not in self._by_module:
            raise ValueError("seated_queen_process_required")
        if self.status()["status"] != "ready":
            raise RuntimeError("canonical_organism_composition_not_ready")
        return self._composition.cognition_kwargs()

    def activate(
        self,
        module_name: str,
        factory: Callable[[], Any],
    ) -> QueenProcessActivation:
        descriptor = self._by_module.get(str(module_name or ""))
        if descriptor is None:
            return QueenProcessActivation(
                "HOLD", "seated_queen_process_required", None, str(module_name or "")
            )
        if not callable(factory):
            return QueenProcessActivation(
                "HOLD", "queen_process_factory_required",
                descriptor.process_id, descriptor.module_name,
            )
        if self.status()["status"] != "ready":
            return QueenProcessActivation(
                "HOLD", "canonical_organism_composition_not_ready",
                descriptor.process_id, descriptor.module_name,
            )
        with self._lock:
            existing = self._active.get(descriptor.process_id)
            if existing is not None:
                return QueenProcessActivation(
                    "ACTIVE", "queen_process_already_active",
                    descriptor.process_id, descriptor.module_name, existing,
                )
            try:
                instance = factory()
            except Exception:
                return QueenProcessActivation(
                    "HOLD", "queen_process_factory_failed",
                    descriptor.process_id, descriptor.module_name,
                )
            if instance is None:
                return QueenProcessActivation(
                    "HOLD", "queen_process_instance_required",
                    descriptor.process_id, descriptor.module_name,
                )
            self._active[descriptor.process_id] = instance
            return QueenProcessActivation(
                "ACTIVE", None, descriptor.process_id, descriptor.module_name, instance,
            )


def bind_queen_process_roof(
    *, composition: OrganismComposition, root: Path = REPO_ROOT
) -> QueenProcessRoof:
    return QueenProcessRoof(
        _factory_token=_FACTORY_TOKEN,
        composition=composition,
        manifest=discover_queen_process_manifest(root),
    )


_ROOF_LOCK = threading.RLock()
_ROOF: QueenProcessRoof | None = None


def configure_canonical_queen_process_roof(roof: QueenProcessRoof) -> QueenProcessRoof:
    if not isinstance(roof, QueenProcessRoof):
        raise TypeError("queen_process_roof_required")
    global _ROOF
    with _ROOF_LOCK:
        _ROOF = roof
    return roof


def get_canonical_queen_process_roof() -> QueenProcessRoof | None:
    with _ROOF_LOCK:
        return _ROOF


def reset_canonical_queen_process_roof_for_tests() -> None:
    global _ROOF
    with _ROOF_LOCK:
        _ROOF = None


__all__ = [
    "MANIFEST_SCHEMA",
    "QueenProcessActivation",
    "QueenProcessDescriptor",
    "QueenProcessManifest",
    "QueenProcessRoof",
    "SCHEMA_VERSION",
    "bind_queen_process_roof",
    "configure_canonical_queen_process_roof",
    "discover_queen_process_manifest",
    "get_canonical_queen_process_roof",
]

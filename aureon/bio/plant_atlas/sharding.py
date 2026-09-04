"""Deterministic species sharding and run manifests for Eigenbot/Isambard-AI."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping

RUN_MANIFEST_VERSION = "agpha.run-manifest.v1"


@dataclass(frozen=True)
class WorkItem:
    taxon_key: str
    input_relpath: str
    input_sha256: str | None = None


@dataclass(frozen=True)
class ShardAssignment:
    index: int
    items: tuple[WorkItem, ...]
    expected_item_count: int
    assignment_sha256: str


@dataclass(frozen=True)
class AtlasRunManifest:
    run_id: str
    snapshot_id: str
    created_at: str
    source_snapshot_root: str
    output_root: str
    shard_count: int
    lanes: tuple[str, ...]
    shards: tuple[ShardAssignment, ...]
    algorithm_versions: Mapping[str, str]
    network_policy: str = "staged_snapshot_only"
    require_source_checksums: bool = True
    schema_version: str = RUN_MANIFEST_VERSION
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def validate(self) -> list[str]:
        errors: list[str] = []
        if self.schema_version != RUN_MANIFEST_VERSION:
            errors.append(f"unsupported manifest schema {self.schema_version!r}")
        if not all(value.strip() for value in (self.run_id, self.snapshot_id, self.source_snapshot_root, self.output_root)):
            errors.append("run_id, snapshot_id, source_snapshot_root, and output_root are required")
        if self.shard_count <= 0:
            errors.append("shard_count must be positive")
        if len(self.shards) != self.shard_count:
            errors.append("manifest must contain exactly shard_count assignments")
        indices = [assignment.index for assignment in self.shards]
        if indices != list(range(self.shard_count)):
            errors.append("shard indices must be contiguous from zero")
        all_keys: list[str] = []
        for assignment in self.shards:
            if assignment.expected_item_count != len(assignment.items):
                errors.append(f"shard {assignment.index}: expected_item_count mismatch")
            digest = assignment_digest(assignment.index, assignment.items)
            if digest != assignment.assignment_sha256:
                errors.append(f"shard {assignment.index}: assignment checksum mismatch")
            all_keys.extend(item.taxon_key for item in assignment.items)
            for item in assignment.items:
                if not item.taxon_key.strip() or not item.input_relpath.strip():
                    errors.append(f"shard {assignment.index}: work item fields must be non-empty")
                if item.input_sha256 is not None:
                    digest = item.input_sha256.lower()
                    if len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest):
                        errors.append(f"shard {assignment.index}: invalid input_sha256 for {item.taxon_key}")
                elif self.require_source_checksums:
                    errors.append(f"shard {assignment.index}: missing input_sha256 for {item.taxon_key}")
        if len(all_keys) != len(set(all_keys)):
            errors.append("a taxon may appear in only one shard")
        if self.network_policy != "staged_snapshot_only":
            errors.append("AGPHA v1 compute manifests require network_policy='staged_snapshot_only'")
        return errors

    def require_valid(self) -> "AtlasRunManifest":
        errors = self.validate()
        if errors:
            raise ValueError("invalid AGPHA run manifest:\n- " + "\n- ".join(errors))
        return self

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def canonical_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=False)

    def content_sha256(self) -> str:
        return hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()

    def shard(self, index: int) -> ShardAssignment:
        if index < 0 or index >= self.shard_count:
            raise IndexError(f"shard index {index} outside 0..{self.shard_count - 1}")
        return self.shards[index]


def taxon_input_relpath(taxon_key: str) -> str:
    digest = hashlib.sha256(taxon_key.encode("utf-8")).hexdigest()[:24]
    return f"taxa/{digest}.json"


def stable_shard_index(taxon_key: str, shard_count: int) -> int:
    if shard_count <= 0:
        raise ValueError("shard_count must be positive")
    digest = hashlib.sha256(taxon_key.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], byteorder="big", signed=False) % shard_count


def assignment_digest(index: int, items: Iterable[WorkItem]) -> str:
    payload = {
        "index": index,
        "items": [asdict(item) for item in items],
    }
    text = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def partition_taxa(
    taxon_keys: Iterable[str],
    shard_count: int,
    *,
    input_checksums: Mapping[str, str] | None = None,
) -> tuple[ShardAssignment, ...]:
    """Assign each unique taxon to exactly one deterministic shard."""

    if shard_count <= 0:
        raise ValueError("shard_count must be positive")
    unique = sorted({key.strip() for key in taxon_keys if key and key.strip()})
    checksums = dict(input_checksums or {})
    unknown = sorted(set(checksums) - set(unique))
    if unknown:
        raise ValueError(f"input_checksums contains unknown taxa: {unknown}")
    buckets: list[list[WorkItem]] = [[] for _ in range(shard_count)]
    for key in unique:
        index = stable_shard_index(key, shard_count)
        buckets[index].append(
            WorkItem(
                taxon_key=key,
                input_relpath=taxon_input_relpath(key),
                input_sha256=checksums.get(key),
            )
        )
    assignments: list[ShardAssignment] = []
    for index, items in enumerate(buckets):
        ordered = tuple(sorted(items, key=lambda item: item.taxon_key))
        assignments.append(
            ShardAssignment(
                index=index,
                items=ordered,
                expected_item_count=len(ordered),
                assignment_sha256=assignment_digest(index, ordered),
            )
        )
    return tuple(assignments)


def build_run_manifest(
    taxon_keys: Iterable[str],
    *,
    run_id: str,
    snapshot_id: str,
    created_at: str,
    source_snapshot_root: str,
    output_root: str,
    shard_count: int,
    lanes: Iterable[str] = ("spectral_measured", "spectral_computed", "sequence_signature"),
    algorithm_versions: Mapping[str, str] | None = None,
    metadata: Mapping[str, Any] | None = None,
    input_checksums: Mapping[str, str] | None = None,
    require_source_checksums: bool = True,
) -> AtlasRunManifest:
    manifest = AtlasRunManifest(
        run_id=run_id,
        snapshot_id=snapshot_id,
        created_at=created_at,
        source_snapshot_root=source_snapshot_root,
        output_root=output_root,
        shard_count=shard_count,
        lanes=tuple(dict.fromkeys(lanes)),
        shards=partition_taxa(taxon_keys, shard_count, input_checksums=input_checksums),
        algorithm_versions=dict(
            algorithm_versions
            or {
                "spectral": "agpha.spectral-octave.v1",
                "sequence": "agpha.sequence-dft.v1",
                "schema": "agpha.species-shard.v1",
            }
        ),
        require_source_checksums=require_source_checksums,
        metadata=dict(metadata or {}),
    )
    return manifest.require_valid()


def run_manifest_from_dict(data: Mapping[str, Any]) -> AtlasRunManifest:
    manifest = AtlasRunManifest(
        schema_version=str(data.get("schema_version", RUN_MANIFEST_VERSION)),
        run_id=str(data["run_id"]),
        snapshot_id=str(data["snapshot_id"]),
        created_at=str(data["created_at"]),
        source_snapshot_root=str(data["source_snapshot_root"]),
        output_root=str(data["output_root"]),
        shard_count=int(data["shard_count"]),
        lanes=tuple(data.get("lanes", [])),
        shards=tuple(
            ShardAssignment(
                index=int(item["index"]),
                items=tuple(
                    WorkItem(
                        taxon_key=str(work["taxon_key"]),
                        input_relpath=str(work["input_relpath"]),
                        input_sha256=(str(work["input_sha256"]) if work.get("input_sha256") is not None else None),
                    )
                    for work in item.get("items", [])
                ),
                expected_item_count=int(item["expected_item_count"]),
                assignment_sha256=str(item["assignment_sha256"]),
            )
            for item in data.get("shards", [])
        ),
        algorithm_versions=dict(data.get("algorithm_versions", {})),
        network_policy=str(data.get("network_policy", "staged_snapshot_only")),
        require_source_checksums=bool(data.get("require_source_checksums", True)),
        metadata=dict(data.get("metadata", {})),
    )
    return manifest.require_valid()


def load_run_manifest(path: str | Path) -> AtlasRunManifest:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("run manifest JSON must contain an object")
    return run_manifest_from_dict(payload)


def write_run_manifest(manifest: AtlasRunManifest, path: str | Path) -> Path:
    manifest.require_valid()
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(manifest.to_dict(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return target

"""Evidence-first data model for the Aureon Global Plant Harmonic Atlas (AGPHA).

The atlas keeps four questions separate:

1. What taxon or biological object is this?
2. What open evidence exists for it?
3. What mathematical or physical transform was applied?
4. What remains unknown, conflicting, or explicitly negative?

A harmonic mapping is not a biological-effect claim.  In particular, a signature
computed from an amino-acid sequence is a deterministic mathematical fingerprint;
it is never represented as a measured molecular vibration.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

SCHEMA_VERSION = "agpha.species-shard.v1"


class EvidenceState(str, Enum):
    """How directly a record is supported."""

    MEASURED_DIRECT = "measured_direct"
    CURATED_DIRECT = "curated_direct"
    COMPUTED = "computed"
    INFERRED_ORTHOLOG = "inferred_ortholog"
    NEGATIVE_RESULT = "negative_result"
    NO_DATA = "no_data"
    QUERY_NOT_RUN = "query_not_run"
    CONFLICTING = "conflicting"


class HarmonicLane(str, Enum):
    """Non-interchangeable routes into a harmonic representation."""

    SPECTRAL_MEASURED = "spectral_measured"
    SPECTRAL_COMPUTED = "spectral_computed"
    STRUCTURE_NORMAL_MODE = "structure_normal_mode"
    SEQUENCE_SIGNATURE = "sequence_signature"
    ORTHOLOG_INFERRED = "ortholog_inferred"
    LEGACY_HNC_PACKET = "legacy_hnc_packet"


class ClaimCeiling(str, Enum):
    """Maximum interpretation allowed by a shard; deliberately excludes therapy."""

    INVENTORY_ONLY = "inventory_only"
    MATERIAL_AUTHENTICATION = "material_authentication"
    PRECLINICAL_HYPOTHESIS = "preclinical_hypothesis"


@dataclass(frozen=True)
class EvidenceRef:
    provider: str
    record_id: str
    state: EvidenceState
    source_uri: str | None = None
    licence: str | None = None
    retrieved_at: str | None = None
    checksum_sha256: str | None = None
    notes: str | None = None

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not self.provider.strip():
            errors.append("evidence provider is required")
        if not self.record_id.strip():
            errors.append("evidence record_id is required")
        if self.checksum_sha256 is not None:
            digest = self.checksum_sha256.lower()
            if len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest):
                errors.append("evidence checksum_sha256 must be a 64-character hex digest")
        return errors


@dataclass(frozen=True)
class TaxonIdentity:
    accepted_name: str
    rank: str = "species"
    family: str | None = None
    genus: str | None = None
    identifiers: Mapping[str, str] = field(default_factory=dict)
    synonyms: tuple[str, ...] = ()

    def validate(self) -> list[str]:
        errors: list[str] = []
        parts = self.accepted_name.strip().split()
        if len(parts) < 2:
            errors.append("accepted_name must contain at least genus and species epithet")
        if self.rank.lower() != "species":
            errors.append("AGPHA v1 species shards require rank='species'")
        if self.genus and parts and self.genus != parts[0]:
            errors.append("taxon genus must match the first token of accepted_name")
        for namespace, value in self.identifiers.items():
            if not str(namespace).strip() or not str(value).strip():
                errors.append("taxon identifier namespaces and values must be non-empty")
        return errors


@dataclass(frozen=True)
class ProteinRecord:
    protein_id: str
    accession: str | None
    name: str | None
    sequence_sha256: str | None
    sequence_length: int | None
    evidence: tuple[EvidenceRef, ...]
    gene: str | None = None
    reviewed: bool | None = None
    structure_ids: tuple[str, ...] = ()
    notes: str | None = None

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not self.protein_id.strip():
            errors.append("protein_id is required")
        if self.sequence_length is not None and self.sequence_length <= 0:
            errors.append(f"protein {self.protein_id}: sequence_length must be positive")
        if self.sequence_sha256 is not None:
            digest = self.sequence_sha256.lower()
            if len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest):
                errors.append(f"protein {self.protein_id}: invalid sequence_sha256")
        if not self.evidence:
            errors.append(f"protein {self.protein_id}: at least one evidence reference is required")
        for ref in self.evidence:
            errors.extend(f"protein {self.protein_id}: {msg}" for msg in ref.validate())
        return errors


@dataclass(frozen=True)
class MoleculeRecord:
    molecule_id: str
    name: str
    identifiers: Mapping[str, str]
    evidence: tuple[EvidenceRef, ...]
    plant_parts: tuple[str, ...] = ()
    phases: tuple[str, ...] = ()
    notes: str | None = None

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not self.molecule_id.strip() or not self.name.strip():
            errors.append("molecule_id and molecule name are required")
        if not self.evidence:
            errors.append(f"molecule {self.molecule_id}: at least one evidence reference is required")
        for ref in self.evidence:
            errors.extend(f"molecule {self.molecule_id}: {msg}" for msg in ref.validate())
        return errors


@dataclass(frozen=True)
class SpectralPeak:
    peak_id: str
    subject_id: str
    value: float
    unit: str
    method: str
    evidence: EvidenceRef
    relative_intensity: float | str | None = None
    assignment: str | None = None
    phase: str | None = None

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not self.peak_id.strip() or not self.subject_id.strip():
            errors.append("spectral peak_id and subject_id are required")
        if not math.isfinite(self.value) or self.value <= 0:
            errors.append(f"spectral peak {self.peak_id}: value must be finite and positive")
        if self.unit not in {"cm^-1", "nm", "Hz", "THz"}:
            errors.append(f"spectral peak {self.peak_id}: unsupported unit {self.unit!r}")
        if not self.method.strip():
            errors.append(f"spectral peak {self.peak_id}: method is required")
        errors.extend(f"spectral peak {self.peak_id}: {msg}" for msg in self.evidence.validate())
        return errors


@dataclass(frozen=True)
class AdjacentBand:
    label: str
    lower_hz: float
    center_hz: float
    upper_hz: float
    delta_fraction: float

    def validate(self) -> list[str]:
        errors: list[str] = []
        values = (self.lower_hz, self.center_hz, self.upper_hz, self.delta_fraction)
        if not all(math.isfinite(v) for v in values):
            errors.append(f"adjacent band {self.label}: all values must be finite")
        if not 0 < self.lower_hz < self.center_hz < self.upper_hz:
            errors.append(f"adjacent band {self.label}: expected lower < center < upper")
        if not 0 < self.delta_fraction < 1:
            errors.append(f"adjacent band {self.label}: delta_fraction must lie in (0, 1)")
        return errors


@dataclass(frozen=True)
class HarmonicComponent:
    tone_hz: float
    source_coordinate: float | None = None
    source_unit: str | None = None
    amplitude: float | None = None
    phase_radians: float | None = None
    channel: str | None = None
    mode_index: int | None = None
    adjacent_bands: tuple[AdjacentBand, ...] = ()

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not math.isfinite(self.tone_hz) or self.tone_hz <= 0:
            errors.append("harmonic tone_hz must be finite and positive")
        if self.amplitude is not None and (not math.isfinite(self.amplitude) or self.amplitude < 0):
            errors.append("harmonic amplitude must be finite and non-negative")
        for band in self.adjacent_bands:
            errors.extend(band.validate())
        return errors


@dataclass(frozen=True)
class HarmonicMapping:
    mapping_id: str
    subject_id: str
    lane: HarmonicLane
    algorithm: str
    algorithm_version: str
    input_sha256: str
    evidence_state: EvidenceState
    physical_interpretation: bool
    components: tuple[HarmonicComponent, ...]
    source_evidence: tuple[EvidenceRef, ...] = ()
    selected_octaves: int | None = None
    notes: str | None = None

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not self.mapping_id.strip() or not self.subject_id.strip():
            errors.append("harmonic mapping_id and subject_id are required")
        if not self.algorithm.strip() or not self.algorithm_version.strip():
            errors.append(f"harmonic mapping {self.mapping_id}: algorithm and version are required")
        digest = self.input_sha256.lower()
        if len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest):
            errors.append(f"harmonic mapping {self.mapping_id}: invalid input_sha256")
        if not self.components:
            errors.append(f"harmonic mapping {self.mapping_id}: at least one component is required")
        nonphysical_lanes = {
            HarmonicLane.SEQUENCE_SIGNATURE,
            HarmonicLane.ORTHOLOG_INFERRED,
        }
        if self.lane in nonphysical_lanes and self.physical_interpretation:
            errors.append(
                f"harmonic mapping {self.mapping_id}: {self.lane.value} may not be marked physical"
            )
        physical_lanes = {
            HarmonicLane.SPECTRAL_MEASURED,
            HarmonicLane.SPECTRAL_COMPUTED,
            HarmonicLane.STRUCTURE_NORMAL_MODE,
        }
        if self.physical_interpretation and self.lane not in physical_lanes:
            errors.append(
                f"harmonic mapping {self.mapping_id}: physical_interpretation is invalid for lane {self.lane.value}"
            )
        if self.evidence_state in {
            EvidenceState.NO_DATA,
            EvidenceState.QUERY_NOT_RUN,
            EvidenceState.NEGATIVE_RESULT,
            EvidenceState.CONFLICTING,
        }:
            errors.append(
                f"harmonic mapping {self.mapping_id}: evidence state {self.evidence_state.value} cannot emit tones"
            )
        if self.lane == HarmonicLane.SPECTRAL_MEASURED and self.evidence_state != EvidenceState.MEASURED_DIRECT:
            errors.append(
                f"harmonic mapping {self.mapping_id}: measured spectral lane requires measured_direct evidence"
            )
        if self.lane == HarmonicLane.SPECTRAL_COMPUTED and self.evidence_state != EvidenceState.COMPUTED:
            errors.append(
                f"harmonic mapping {self.mapping_id}: computed spectral lane requires computed evidence"
            )
        for component in self.components:
            errors.extend(f"harmonic mapping {self.mapping_id}: {msg}" for msg in component.validate())
        for ref in self.source_evidence:
            errors.extend(f"harmonic mapping {self.mapping_id}: {msg}" for msg in ref.validate())
        return errors


@dataclass(frozen=True)
class KnowledgeGap:
    gap_id: str
    layer: str
    state: EvidenceState
    query_scope: str
    reason: str
    next_action: str | None = None

    def validate(self) -> list[str]:
        errors: list[str] = []
        if self.state not in {
            EvidenceState.NO_DATA,
            EvidenceState.QUERY_NOT_RUN,
            EvidenceState.CONFLICTING,
            EvidenceState.NEGATIVE_RESULT,
        }:
            errors.append(f"gap {self.gap_id}: state must represent missing, negative, or conflicting evidence")
        if not all(value.strip() for value in (self.gap_id, self.layer, self.query_scope, self.reason)):
            errors.append("knowledge gap id, layer, query_scope, and reason are required")
        return errors


@dataclass(frozen=True)
class Observation:
    observation_id: str
    statement: str
    evidence_state: EvidenceState
    evidence: tuple[EvidenceRef, ...]
    interpretation_boundary: str

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not self.observation_id.strip() or not self.statement.strip():
            errors.append("observation_id and statement are required")
        if not self.interpretation_boundary.strip():
            errors.append(f"observation {self.observation_id}: interpretation boundary is required")
        if not self.evidence:
            errors.append(f"observation {self.observation_id}: evidence is required")
        for ref in self.evidence:
            errors.extend(f"observation {self.observation_id}: {msg}" for msg in ref.validate())
        return errors


@dataclass(frozen=True)
class SpeciesShard:
    shard_id: str
    taxon: TaxonIdentity
    snapshot_id: str
    claim_ceiling: ClaimCeiling
    boundary_statement: str
    evidence: tuple[EvidenceRef, ...] = ()
    proteins: tuple[ProteinRecord, ...] = ()
    molecules: tuple[MoleculeRecord, ...] = ()
    spectral_peaks: tuple[SpectralPeak, ...] = ()
    harmonic_mappings: tuple[HarmonicMapping, ...] = ()
    observations: tuple[Observation, ...] = ()
    gaps: tuple[KnowledgeGap, ...] = ()
    schema_version: str = SCHEMA_VERSION
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def validate(self) -> list[str]:
        errors: list[str] = []
        if self.schema_version != SCHEMA_VERSION:
            errors.append(f"unsupported schema_version {self.schema_version!r}")
        if not self.shard_id.strip() or not self.snapshot_id.strip():
            errors.append("shard_id and snapshot_id are required")
        if not self.boundary_statement.strip():
            errors.append("boundary_statement is required")
        errors.extend(self.taxon.validate())
        for ref in self.evidence:
            errors.extend(ref.validate())
        for record in self.proteins:
            errors.extend(record.validate())
        for record in self.molecules:
            errors.extend(record.validate())
        for record in self.spectral_peaks:
            errors.extend(record.validate())
        for mapping in self.harmonic_mappings:
            errors.extend(mapping.validate())
        for observation in self.observations:
            errors.extend(observation.validate())
        for gap in self.gaps:
            errors.extend(gap.validate())

        subject_ids = {p.protein_id for p in self.proteins} | {m.molecule_id for m in self.molecules}
        subject_ids |= {peak.subject_id for peak in self.spectral_peaks}
        for mapping in self.harmonic_mappings:
            if mapping.subject_id not in subject_ids and mapping.lane != HarmonicLane.LEGACY_HNC_PACKET:
                errors.append(
                    f"harmonic mapping {mapping.mapping_id}: unknown subject_id {mapping.subject_id!r}"
                )

        duplicate_sets = {
            "protein_id": [p.protein_id for p in self.proteins],
            "molecule_id": [m.molecule_id for m in self.molecules],
            "peak_id": [p.peak_id for p in self.spectral_peaks],
            "mapping_id": [m.mapping_id for m in self.harmonic_mappings],
            "gap_id": [g.gap_id for g in self.gaps],
            "observation_id": [o.observation_id for o in self.observations],
        }
        for label, values in duplicate_sets.items():
            if len(values) != len(set(values)):
                errors.append(f"duplicate {label} values are not permitted")
        return errors

    def require_valid(self) -> "SpeciesShard":
        errors = self.validate()
        if errors:
            raise ValueError("invalid AGPHA species shard:\n- " + "\n- ".join(errors))
        return self

    def to_dict(self) -> dict[str, Any]:
        return _normalise(asdict(self))

    def canonical_json(self) -> str:
        return canonical_json(self.to_dict())

    def content_sha256(self) -> str:
        return hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()


def _normalise(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Mapping):
        return {str(k): _normalise(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [_normalise(v) for v in value]
    return value


def canonical_json(value: Mapping[str, Any] | Sequence[Any]) -> str:
    return json.dumps(_normalise(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def species_shard_from_dict(data: Mapping[str, Any]) -> SpeciesShard:
    """Parse and validate one serialised species shard."""
    from .model_io import species_shard_from_dict as _parse

    return _parse(data)


def load_species_shard(path: str | Path) -> SpeciesShard:
    from .model_io import load_species_shard as _load

    return _load(path)


def write_species_shard(shard: SpeciesShard, path: str | Path) -> Path:
    from .model_io import write_species_shard as _write

    return _write(shard, path)


def inventory_summary(shards: Iterable[SpeciesShard]) -> dict[str, Any]:
    from .model_io import inventory_summary as _summary

    return _summary(shards)

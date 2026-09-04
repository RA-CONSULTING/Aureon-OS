"""Serialisation and inventory helpers for AGPHA species shards."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable, Mapping

from .models import (
    AdjacentBand,
    ClaimCeiling,
    EvidenceRef,
    EvidenceState,
    HarmonicComponent,
    HarmonicLane,
    HarmonicMapping,
    KnowledgeGap,
    MoleculeRecord,
    Observation,
    ProteinRecord,
    SCHEMA_VERSION,
    SpeciesShard,
    SpectralPeak,
    TaxonIdentity,
)


def _evidence_ref(data: Mapping[str, Any]) -> EvidenceRef:
    return EvidenceRef(
        provider=str(data["provider"]),
        record_id=str(data["record_id"]),
        state=EvidenceState(data["state"]),
        source_uri=data.get("source_uri"),
        licence=data.get("licence"),
        retrieved_at=data.get("retrieved_at"),
        checksum_sha256=data.get("checksum_sha256"),
        notes=data.get("notes"),
    )


def _adjacent_band(data: Mapping[str, Any]) -> AdjacentBand:
    return AdjacentBand(
        label=str(data["label"]),
        lower_hz=float(data["lower_hz"]),
        center_hz=float(data["center_hz"]),
        upper_hz=float(data["upper_hz"]),
        delta_fraction=float(data["delta_fraction"]),
    )


def _component(data: Mapping[str, Any]) -> HarmonicComponent:
    return HarmonicComponent(
        tone_hz=float(data["tone_hz"]),
        source_coordinate=(float(data["source_coordinate"]) if data.get("source_coordinate") is not None else None),
        source_unit=data.get("source_unit"),
        amplitude=(float(data["amplitude"]) if data.get("amplitude") is not None else None),
        phase_radians=(float(data["phase_radians"]) if data.get("phase_radians") is not None else None),
        channel=data.get("channel"),
        mode_index=(int(data["mode_index"]) if data.get("mode_index") is not None else None),
        adjacent_bands=tuple(_adjacent_band(item) for item in data.get("adjacent_bands", [])),
    )


def species_shard_from_dict(data: Mapping[str, Any]) -> SpeciesShard:
    """Parse and validate one serialised species shard."""

    taxon_data = data["taxon"]
    shard = SpeciesShard(
        schema_version=str(data.get("schema_version", SCHEMA_VERSION)),
        shard_id=str(data["shard_id"]),
        snapshot_id=str(data["snapshot_id"]),
        claim_ceiling=ClaimCeiling(data["claim_ceiling"]),
        boundary_statement=str(data["boundary_statement"]),
        taxon=TaxonIdentity(
            accepted_name=str(taxon_data["accepted_name"]),
            rank=str(taxon_data.get("rank", "species")),
            family=taxon_data.get("family"),
            genus=taxon_data.get("genus"),
            identifiers=dict(taxon_data.get("identifiers", {})),
            synonyms=tuple(taxon_data.get("synonyms", [])),
        ),
        evidence=tuple(_evidence_ref(item) for item in data.get("evidence", [])),
        proteins=tuple(
            ProteinRecord(
                protein_id=str(item["protein_id"]),
                accession=item.get("accession"),
                name=item.get("name"),
                sequence_sha256=item.get("sequence_sha256"),
                sequence_length=(int(item["sequence_length"]) if item.get("sequence_length") is not None else None),
                evidence=tuple(_evidence_ref(ref) for ref in item.get("evidence", [])),
                gene=item.get("gene"),
                reviewed=item.get("reviewed"),
                structure_ids=tuple(item.get("structure_ids", [])),
                notes=item.get("notes"),
            )
            for item in data.get("proteins", [])
        ),
        molecules=tuple(
            MoleculeRecord(
                molecule_id=str(item["molecule_id"]),
                name=str(item["name"]),
                identifiers=dict(item.get("identifiers", {})),
                evidence=tuple(_evidence_ref(ref) for ref in item.get("evidence", [])),
                plant_parts=tuple(item.get("plant_parts", [])),
                phases=tuple(item.get("phases", [])),
                notes=item.get("notes"),
            )
            for item in data.get("molecules", [])
        ),
        spectral_peaks=tuple(
            SpectralPeak(
                peak_id=str(item["peak_id"]),
                subject_id=str(item["subject_id"]),
                value=float(item["value"]),
                unit=str(item["unit"]),
                method=str(item["method"]),
                evidence=_evidence_ref(item["evidence"]),
                relative_intensity=item.get("relative_intensity"),
                assignment=item.get("assignment"),
                phase=item.get("phase"),
            )
            for item in data.get("spectral_peaks", [])
        ),
        harmonic_mappings=tuple(
            HarmonicMapping(
                mapping_id=str(item["mapping_id"]),
                subject_id=str(item["subject_id"]),
                lane=HarmonicLane(item["lane"]),
                algorithm=str(item["algorithm"]),
                algorithm_version=str(item["algorithm_version"]),
                input_sha256=str(item["input_sha256"]),
                evidence_state=EvidenceState(item["evidence_state"]),
                physical_interpretation=bool(item["physical_interpretation"]),
                components=tuple(_component(component) for component in item.get("components", [])),
                source_evidence=tuple(_evidence_ref(ref) for ref in item.get("source_evidence", [])),
                selected_octaves=(int(item["selected_octaves"]) if item.get("selected_octaves") is not None else None),
                notes=item.get("notes"),
            )
            for item in data.get("harmonic_mappings", [])
        ),
        observations=tuple(
            Observation(
                observation_id=str(item["observation_id"]),
                statement=str(item["statement"]),
                evidence_state=EvidenceState(item["evidence_state"]),
                evidence=tuple(_evidence_ref(ref) for ref in item.get("evidence", [])),
                interpretation_boundary=str(item["interpretation_boundary"]),
            )
            for item in data.get("observations", [])
        ),
        gaps=tuple(
            KnowledgeGap(
                gap_id=str(item["gap_id"]),
                layer=str(item["layer"]),
                state=EvidenceState(item["state"]),
                query_scope=str(item["query_scope"]),
                reason=str(item["reason"]),
                next_action=item.get("next_action"),
            )
            for item in data.get("gaps", [])
        ),
        metadata=dict(data.get("metadata", {})),
    )
    return shard.require_valid()


def load_species_shard(path: str | Path) -> SpeciesShard:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("species shard JSON must contain an object")
    return species_shard_from_dict(payload)


def write_species_shard(shard: SpeciesShard, path: str | Path) -> Path:
    shard.require_valid()
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(shard.to_dict(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return target


def inventory_summary(shards: Iterable[SpeciesShard]) -> dict[str, Any]:
    records = list(shards)
    lanes: dict[str, int] = {}
    evidence_states: dict[str, int] = {}
    for shard in records:
        for mapping in shard.harmonic_mappings:
            lanes[mapping.lane.value] = lanes.get(mapping.lane.value, 0) + 1
            evidence_states[mapping.evidence_state.value] = evidence_states.get(mapping.evidence_state.value, 0) + 1
    return {
        "species": len(records),
        "proteins": sum(len(shard.proteins) for shard in records),
        "molecules": sum(len(shard.molecules) for shard in records),
        "spectral_peaks": sum(len(shard.spectral_peaks) for shard in records),
        "harmonic_mappings": sum(len(shard.harmonic_mappings) for shard in records),
        "observations": sum(len(shard.observations) for shard in records),
        "gaps": sum(len(shard.gaps) for shard in records),
        "lanes": dict(sorted(lanes.items())),
        "mapping_evidence_states": dict(sorted(evidence_states.items())),
    }

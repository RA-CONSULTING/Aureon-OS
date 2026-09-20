from __future__ import annotations

from pathlib import Path

import pytest

from aureon.bio.plant_atlas.models import (
    EvidenceState,
    HarmonicComponent,
    HarmonicLane,
    HarmonicMapping,
    load_species_shard,
)

ROOT = Path(__file__).resolve().parents[2]
PILOTS = ROOT / "data" / "plant_atlas" / "pilots"


def test_pilot_shards_validate_and_hash_stably() -> None:
    blackthorn = load_species_shard(PILOTS / "prunus_spinosa.v1.json")
    dandelion = load_species_shard(PILOTS / "taraxacum_officinale.v1.json")

    assert blackthorn.taxon.identifiers["ncbitaxon"] == "114937"
    assert dandelion.taxon.identifiers["ncbitaxon"] == "50225"
    assert blackthorn.content_sha256() == blackthorn.content_sha256()
    assert dandelion.content_sha256() == dandelion.content_sha256()


def test_blackthorn_pilot_preserves_negative_evidence_and_withholds_packet() -> None:
    shard = load_species_shard(PILOTS / "prunus_spinosa.v1.json")

    assert not shard.harmonic_mappings
    assert shard.metadata["harmonic_packet_status"] == "withheld"
    assert any(item.evidence_state == EvidenceState.NEGATIVE_RESULT for item in shard.observations)
    assert "no therapeutic" in shard.boundary_statement.lower()


def test_dandelion_pilot_keeps_legacy_and_measured_lanes_distinct() -> None:
    shard = load_species_shard(PILOTS / "taraxacum_officinale.v1.json")
    lanes = {mapping.lane for mapping in shard.harmonic_mappings}

    assert HarmonicLane.SPECTRAL_MEASURED in lanes
    assert HarmonicLane.LEGACY_HNC_PACKET in lanes
    assert all(
        not mapping.physical_interpretation
        for mapping in shard.harmonic_mappings
        if mapping.lane == HarmonicLane.LEGACY_HNC_PACKET
    )


def test_sequence_lane_cannot_be_marked_as_physical() -> None:
    mapping = HarmonicMapping(
        mapping_id="bad",
        subject_id="protein:x",
        lane=HarmonicLane.SEQUENCE_SIGNATURE,
        algorithm="test",
        algorithm_version="1",
        input_sha256="0" * 64,
        evidence_state=EvidenceState.COMPUTED,
        physical_interpretation=True,
        components=(HarmonicComponent(tone_hz=1000.0),),
    )

    errors = mapping.validate()
    assert any("may not be marked physical" in error for error in errors)

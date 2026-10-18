from __future__ import annotations

import hashlib
import json
from pathlib import Path

from aureon.bio.plant_atlas.models import HarmonicLane, load_species_shard
from aureon.bio.plant_atlas.sharding import build_run_manifest, taxon_input_relpath
from aureon.bio.plant_atlas.worker import run_manifest_shard


def test_worker_builds_species_shard_and_receipt_offline(tmp_path: Path) -> None:
    source_root = tmp_path / "snapshot"
    output_root = tmp_path / "output"
    key = "ncbitaxon:50225"
    input_path = source_root / taxon_input_relpath(key)
    input_path.parent.mkdir(parents=True)
    input_path.write_text(
        json.dumps(
            {
                "schema_version": "agpha.input-bundle.v1",
                "taxon_key": key,
                "taxon": {
                    "accepted_name": "Taraxacum officinale",
                    "rank": "species",
                    "family": "Asteraceae",
                    "genus": "Taraxacum",
                    "identifiers": {"ncbitaxon": "50225"},
                },
                "claim_ceiling": "inventory_only",
                "evidence": [
                    {
                        "provider": "NCBI Taxonomy",
                        "record_id": key,
                        "state": "curated_direct",
                    }
                ],
                "proteins": [
                    {
                        "protein_id": "protein:test",
                        "accession": "TEST1",
                        "name": "test protein",
                        "sequence": "ACDEFGHIKLMNPQRSTVWY",
                        "evidence": [
                            {
                                "provider": "UniProt",
                                "record_id": "TEST1",
                                "state": "curated_direct",
                            }
                        ],
                    }
                ],
                "molecules": [
                    {
                        "molecule_id": "molecule:test",
                        "name": "test molecule",
                        "identifiers": {},
                        "evidence": [
                            {
                                "provider": "test",
                                "record_id": "occurrence:test",
                                "state": "curated_direct",
                            }
                        ],
                    }
                ],
                "spectral_peaks": [
                    {
                        "peak_id": "peak:test",
                        "subject_id": "molecule:test",
                        "value": 1603.0,
                        "unit": "cm^-1",
                        "method": "Raman",
                        "evidence": {
                            "provider": "test",
                            "record_id": "spectrum:test",
                            "state": "measured_direct",
                        },
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    manifest = build_run_manifest(
        [key],
        run_id="worker-test",
        snapshot_id="snapshot-test",
        created_at="2026-09-04T13:00:00Z",
        source_snapshot_root=str(source_root),
        output_root=str(output_root),
        shard_count=1,
        input_checksums={key: hashlib.sha256(input_path.read_bytes()).hexdigest()},
    )

    receipt = run_manifest_shard(manifest, 0)

    assert receipt["failed"] == 0
    assert receipt["completed"] == 1
    output_path = output_root / receipt["items"][0]["output_relpath"]
    shard = load_species_shard(output_path)
    assert {mapping.lane for mapping in shard.harmonic_mappings} == {
        HarmonicLane.SEQUENCE_SIGNATURE,
        HarmonicLane.SPECTRAL_MEASURED,
    }


def test_worker_fails_closed_when_input_bundle_changes_after_manifest(tmp_path: Path) -> None:
    source_root = tmp_path / "snapshot"
    output_root = tmp_path / "output"
    key = "ncbitaxon:114937"
    input_path = source_root / taxon_input_relpath(key)
    input_path.parent.mkdir(parents=True)
    input_path.write_text(
        json.dumps(
            {
                "schema_version": "agpha.input-bundle.v1",
                "taxon_key": key,
                "taxon": {
                    "accepted_name": "Prunus spinosa",
                    "rank": "species",
                    "family": "Rosaceae",
                    "genus": "Prunus",
                    "identifiers": {"ncbitaxon": "114937"},
                },
            }
        ),
        encoding="utf-8",
    )
    expected = hashlib.sha256(input_path.read_bytes()).hexdigest()
    manifest = build_run_manifest(
        [key],
        run_id="tamper-test",
        snapshot_id="snapshot-test",
        created_at="2026-09-04T13:00:00Z",
        source_snapshot_root=str(source_root),
        output_root=str(output_root),
        shard_count=1,
        input_checksums={key: expected},
    )
    input_path.write_text("{}", encoding="utf-8")

    receipt = run_manifest_shard(manifest, 0)

    assert receipt["completed"] == 0
    assert receipt["failed"] == 1
    assert receipt["items"][0]["error_type"] == "ValueError"
    assert "checksum mismatch" in receipt["items"][0]["error"]

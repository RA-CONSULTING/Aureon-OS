from __future__ import annotations

import json
from pathlib import Path

import pytest

jsonschema = pytest.importorskip("jsonschema")

ROOT = Path(__file__).resolve().parents[2]
SCHEMAS = ROOT / "docs" / "schemas"


def _validator(name: str):
    schema = json.loads((SCHEMAS / name).read_text(encoding="utf-8"))
    return jsonschema.Draft202012Validator(schema)


def test_pilot_shards_conform_to_public_json_schema() -> None:
    validator = _validator("agpha.species-shard.v1.schema.json")
    for path in sorted((ROOT / "data" / "plant_atlas" / "pilots").glob("*.json")):
        errors = sorted(validator.iter_errors(json.loads(path.read_text(encoding="utf-8"))), key=str)
        assert not errors, f"{path}: {[error.message for error in errors]}"


def test_example_manifest_conforms_to_public_json_schema() -> None:
    validator = _validator("agpha.run-manifest.v1.schema.json")
    path = ROOT / "data" / "plant_atlas" / "manifests" / "pilot.example.v1.json"
    errors = sorted(validator.iter_errors(json.loads(path.read_text(encoding="utf-8"))), key=str)
    assert not errors, [error.message for error in errors]


def test_minimal_input_bundle_conforms_to_public_json_schema() -> None:
    validator = _validator("agpha.input-bundle.v1.schema.json")
    bundle = {
        "schema_version": "agpha.input-bundle.v1",
        "taxon_key": "ncbitaxon:50225",
        "taxon": {
            "accepted_name": "Taraxacum officinale",
            "rank": "species",
            "family": "Asteraceae",
            "genus": "Taraxacum",
            "identifiers": {"ncbitaxon": "50225"},
            "synonyms": [],
        },
    }
    errors = sorted(validator.iter_errors(bundle), key=str)
    assert not errors, [error.message for error in errors]


def test_source_snapshot_schema_accepts_zero_result_query_receipt() -> None:
    validator = _validator("agpha.source-snapshot.v1.schema.json")
    snapshot = {
        "snapshot_id": "snapshot:test",
        "created_at": "2026-09-04T13:00:00Z",
        "files": [],
        "queries": [
            {
                "query_id": "query:test",
                "source_id": "wfo_plant_list",
                "request_sha256": "0" * 64,
                "status": "zero_result",
                "result_count": 0,
                "retrieved_at": "2026-09-04T13:00:00Z",
                "response_relpath": None,
                "response_sha256": None,
                "notes": "zero-result receipt preserved",
            }
        ],
        "registry_version": "agpha.source-registry.v1",
        "schema_version": "agpha.source-snapshot.v1",
        "metadata": {},
    }
    errors = sorted(validator.iter_errors(snapshot), key=str)
    assert not errors, [error.message for error in errors]

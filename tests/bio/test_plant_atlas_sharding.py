from __future__ import annotations

import json

from aureon.bio.plant_atlas.sharding import (
    build_run_manifest,
    partition_taxa,
    run_manifest_from_dict,
)


def test_partition_is_deterministic_complete_and_nonoverlapping() -> None:
    keys = ["ncbitaxon:114937", "ncbitaxon:50225", "ncbitaxon:3702", "ncbitaxon:4577"]
    first = partition_taxa(keys, 8)
    second = partition_taxa(reversed(keys), 8)

    assert first == second
    assigned = [item.taxon_key for shard in first for item in shard.items]
    assert sorted(assigned) == sorted(keys)
    assert len(assigned) == len(set(assigned))


def test_manifest_round_trip_preserves_checksum() -> None:
    manifest = build_run_manifest(
        ["ncbitaxon:114937", "ncbitaxon:50225"],
        run_id="test-run",
        snapshot_id="snapshot-1",
        created_at="2026-09-04T13:00:00Z",
        source_snapshot_root="/snapshot",
        output_root="/output",
        shard_count=4,
        require_source_checksums=False,
    )
    payload = json.loads(json.dumps(manifest.to_dict()))
    restored = run_manifest_from_dict(payload)

    assert restored == manifest
    assert restored.content_sha256() == manifest.content_sha256()


def test_manifest_requires_input_checksums_by_default() -> None:
    import pytest

    with pytest.raises(ValueError, match="missing input_sha256"):
        build_run_manifest(
            ["ncbitaxon:50225"],
            run_id="strict-test",
            snapshot_id="snapshot-1",
            created_at="2026-09-04T13:00:00Z",
            source_snapshot_root="/snapshot",
            output_root="/output",
            shard_count=1,
        )

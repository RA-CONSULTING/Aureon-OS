from __future__ import annotations

import hashlib
from pathlib import Path

from aureon.bio.plant_atlas.source_snapshot import (
    QueryReceipt,
    QueryStatus,
    SourceSnapshotManifest,
    snapshot_files_from_paths,
    verify_source_snapshot,
)


def test_source_snapshot_verifies_and_detects_tampering(tmp_path: Path) -> None:
    root = tmp_path / "snapshot"
    data_path = root / "wfo" / "names.csv"
    data_path.parent.mkdir(parents=True)
    data_path.write_text("wfo_id,accepted_name\nwfo:1,Taraxacum officinale\n", encoding="utf-8")

    files = snapshot_files_from_paths(
        root,
        [
            {
                "relpath": "wfo/names.csv",
                "source_id": "wfo_plant_list",
                "source_record_id": "wfo-release:test",
                "retrieved_at": "2026-09-04T13:00:00Z",
                "licence_or_terms": "CC0-1.0",
                "media_type": "text/csv",
            }
        ],
    )
    snapshot = SourceSnapshotManifest(
        snapshot_id="snapshot:test",
        created_at="2026-09-04T13:00:00Z",
        files=files,
        queries=(
            QueryReceipt(
                query_id="query:wfo:test",
                source_id="wfo_plant_list",
                request_sha256=hashlib.sha256(b"wfo release test").hexdigest(),
                status=QueryStatus.COMPLETE,
                result_count=1,
                retrieved_at="2026-09-04T13:00:00Z",
                response_relpath="wfo/names.csv",
                response_sha256=files[0].sha256,
            ),
        ),
    ).require_valid()

    report = verify_source_snapshot(snapshot, root)
    assert report.passed
    assert report.verified_files == 1

    data_path.write_text("tampered\n", encoding="utf-8")
    tampered = verify_source_snapshot(snapshot, root)
    assert not tampered.passed
    assert tampered.size_mismatches or tampered.checksum_mismatches

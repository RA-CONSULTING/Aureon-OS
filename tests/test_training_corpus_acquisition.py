"""Offline acquisition contracts; no Hub or production corpus is mutated."""

import gzip
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from training.scratch import fetch_corpus as corpus


def _payload():
    return b'{"text":"a real training document"}\n'


def _record(path: Path):
    body = path.read_bytes()
    return {"file": path.name, "bytes": len(body), "sha256": hashlib.sha256(body).hexdigest()}


def test_pinned_metadata_distinguishes_commit_blob_and_content_hash():
    info = SimpleNamespace(
        sha="a" * 40,
        siblings=[SimpleNamespace(
            rfilename="sample/100BT/test.json.gz",
            size=128,
            blob_id="b" * 40,
            lfs=SimpleNamespace(sha256="c" * 64),
        )],
    )
    with patch("huggingface_hub.HfApi") as constructor:
        constructor.return_value.repo_info.return_value = info
        revision, records = corpus.shard_records(corpus.api(), "test/corpus", "sample/100BT", (".json.gz",))
    assert revision == "a" * 40
    assert records[0]["sha256"] == "c" * 64
    assert records[0]["blob_id"] == "b" * 40
    assert records[0]["sha256"] != records[0]["blob_id"]


def test_gzip_verification_catches_truncation_and_missing_text(tmp_path):
    path = tmp_path / "shard.json.gz"
    with gzip.open(path, "wb") as stream:
        stream.write(_payload())
    record = _record(path)
    assert corpus.verify_shard(path, record, checksum=True) == (True, "ok")
    path.write_bytes(path.read_bytes()[:-4])
    ok, reason = corpus.verify_shard(path, record, checksum=True)
    assert not ok
    assert "size_mismatch" in reason
    path.unlink()
    with gzip.open(path, "wb") as stream:
        stream.write(b'{"id":"metadata only"}\n')
    assert corpus.verify_shard(path, _record(path), checksum=True) == (
        False, "missing_text_at_line:1",
    )


def test_audit_is_read_only_and_bounded_verification_does_not_download(tmp_path):
    out = tmp_path / "code"
    path = out / "one.json.gz"
    path.parent.mkdir()
    with gzip.open(path, "wb") as stream:
        stream.write(_payload())
    manifest = out / "manifest-code.json"
    manifest.write_text('{"repo":"original","shards":[]}')
    before = manifest.read_bytes()
    records = [_record(path), {"file": "absent.json.gz", "bytes": 100}]
    with patch.object(corpus, "curl_shard", side_effect=AssertionError("downloaded")):
        result = corpus.fetch(
            "codeparrot/codeparrot-clean", records, out, 0, manifest,
            revision="a" * 40, audit=True,
        )
    assert manifest.read_bytes() == before
    assert result["failed"] == 1
    assert result["complete"] is False
    assert result["failed_files"] == ["absent.json.gz"]


def test_valid_existing_shard_never_redownloads_and_manifest_is_atomic(tmp_path):
    out = tmp_path / "code"
    path = out / "one.json.gz"
    path.parent.mkdir()
    with gzip.open(path, "wb") as stream:
        stream.write(_payload())
    record = _record(path)
    manifest = out / "manifest-code.json"
    manifest.write_text('{"repo":"original","shards":[]}')
    with patch.object(corpus.subprocess, "run", side_effect=AssertionError("downloaded")):
        result = corpus.fetch(
            record.get("repo", "codeparrot/codeparrot-clean"), [record], out, 0, manifest,
            revision="a" * 40,
        )
    saved = json.loads(manifest.read_text())
    assert result["complete"] is True
    assert saved["verified_shards"] == 1
    assert saved["shards"][0]["sha256"] == record["sha256"]
    assert (out / "manifest-code.legacy.json").is_file()
    assert not list(out.rglob("*.tmp"))


def test_incremental_download_accumulates_same_revision_and_detects_change(tmp_path):
    out = tmp_path / "code"
    out.mkdir()
    first = out / "one.json.gz"
    second = out / "two.json.gz"
    for path in (first, second):
        with gzip.open(path, "wb") as stream:
            stream.write(_payload())
    manifest = out / "manifest-code.json"
    records = [_record(first), _record(second)]
    for record in records:
        result = corpus.fetch(
            "codeparrot/codeparrot-clean", records, out, 0, manifest,
            revision="a" * 40, max_files=1 if record is records[0] else 2,
        )
        assert result["complete"] is (record is records[-1])
    saved = json.loads(manifest.read_text())
    assert saved["verified_shards"] == 2
    assert saved["complete"] is True
    corpus.fetch(
        "codeparrot/codeparrot-clean", [records[0]], out, 0, manifest,
        revision="b" * 40,
    )
    saved = json.loads(manifest.read_text())
    assert saved["verified_shards"] == 1
    assert saved["complete"] is True
    assert saved["shards"][0]["file"] == "one.json.gz"


def test_oversized_or_invalid_part_never_grows_or_becomes_complete(tmp_path):
    out = tmp_path / "code"
    path = out / "one.json.gz"
    path.parent.mkdir()
    part = path.with_name(path.name + ".part")
    part.write_bytes(b"x" * 100)
    with patch.object(corpus.subprocess, "run") as run:
        run.return_value = SimpleNamespace(returncode=22, stderr="unauthorized")
        ok, _rate, reason = corpus.curl_shard(
            "test/corpus", path.name, out, 20, revision="a" * 40,
        )
    assert not ok
    assert reason == "curl_exit:22"
    assert not part.exists()
    assert not path.exists()
    assert run.call_args.args[0][-1].startswith(
        "https://huggingface.co/datasets/test/corpus/resolve/" + "a" * 40 + "/"
    )


def test_invalid_existing_shard_is_quarantined_not_ingested(tmp_path):
    out = tmp_path / "code"
    path = out / "one.json.gz"
    path.parent.mkdir()
    path.write_bytes(b"corrupt")
    record = {"file": path.name, "bytes": 7, "sha256": "0" * 64}
    assert record["sha256"] != hashlib.sha256(path.read_bytes()).hexdigest()
    with patch.object(corpus.subprocess, "run") as run:
        run.return_value = SimpleNamespace(returncode=1, stderr="stopped")
        ok, _rate, reason = corpus.curl_shard("test/corpus", path.name, out, 7)
    assert not ok
    assert reason == "curl_exit:1"
    assert not path.exists()
    assert (out / "one.json.gz.invalid").read_bytes() == b"corrupt"

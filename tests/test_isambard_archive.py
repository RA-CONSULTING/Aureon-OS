from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from huggingface import isambard_archive as archive


@pytest.fixture
def sources(tmp_path: Path) -> tuple[archive.SourceSpec, archive.SourceSpec]:
    pretrain = tmp_path / "sources" / "pretrain"
    hnc = tmp_path / "sources" / "hnc-organism"
    pretrain.mkdir(parents=True)
    hnc.mkdir(parents=True)
    return archive.default_sources(pretrain, hnc)


@pytest.fixture
def state(tmp_path: Path, sources: tuple[archive.SourceSpec, archive.SourceSpec]):
    with archive.ArchiveState(tmp_path / "resume" / "state.sqlite3", sources) as value:
        yield value


def _scan(state: archive.ArchiveState, file_filter: archive.FileFilter | None = None):
    return archive.Inventory(state).scan(file_filter)


def _git_blob(data: bytes) -> str:
    digest = hashlib.sha1()
    digest.update(f"blob {len(data)}\0".encode("ascii"))
    digest.update(data)
    return digest.hexdigest()


def _entry(path: str, data: bytes, *, lfs: bool = False):
    if lfs:
        return SimpleNamespace(
            path=path,
            size=len(data),
            blob_id="git-pointer-oid",
            lfs={"oid": hashlib.sha256(data).hexdigest(), "size": len(data)},
        )
    return SimpleNamespace(path=path, size=len(data), blob_id=_git_blob(data), lfs=None)


class FakeOperation:
    def __init__(self, *, path_in_repo: str, path_or_fileobj: str):
        self.path_in_repo = path_in_repo
        self.path_or_fileobj = path_or_fileobj


class FakeHub:
    def __init__(self):
        self.remote: dict[str, dict[str, SimpleNamespace]] = {}
        self.revisions: dict[str, str] = {}
        self.created: list[tuple[str, bool]] = []
        self.commits: list[list[str]] = []
        self.commit_attempts = 0
        self.fail_on_commit: int | None = None
        self.mismatch: set[tuple[str, str]] = set()
        self.info_calls = 0

    def create_repo(self, repo_id: str, *, repo_type: str, private: bool, exist_ok: bool):
        assert repo_type == "dataset"
        assert exist_ok is True
        self.created.append((repo_id, private))
        self.remote.setdefault(repo_id, {})
        self.revisions.setdefault(repo_id, "initial-revision")

    def list_repo_tree(self, repo_id: str, *, repo_type: str, recursive: bool):
        assert repo_type == "dataset" and recursive is True
        return list(self.remote.get(repo_id, {}).values())

    def repo_info(self, repo_id: str, *, repo_type: str):
        self.info_calls += 1
        return SimpleNamespace(sha=self.revisions.get(repo_id, "initial-revision"))

    def create_commit(self, *, repo_id: str, repo_type: str, operations, commit_message: str):
        self.commit_attempts += 1
        if self.fail_on_commit == self.commit_attempts:
            raise OSError("simulated interrupted commit")
        self.commits.append([operation.path_in_repo for operation in operations])
        for operation in operations:
            data = Path(operation.path_or_fileobj).read_bytes()
            self.remote[repo_id][operation.path_in_repo] = _entry(operation.path_in_repo, data)
        self.revisions[repo_id] = f"revision-{self.commit_attempts}"
        return SimpleNamespace(oid=self.revisions[repo_id])

    def get_paths_info(
        self, repo_id: str, paths, *, repo_type: str, revision=None, expand=False
    ):
        assert repo_type == "dataset"
        assert expand is True
        results = []
        for path in paths:
            value = self.remote.get(repo_id, {}).get(path)
            if value is None:
                continue
            if (repo_id, path) in self.mismatch:
                value = SimpleNamespace(path=path, size=value.size, blob_id="0" * 40, lfs=None)
            results.append(value)
        return results


def _uploader(state: archive.ArchiveState, api: FakeHub) -> archive.ArchiveUploader:
    return archive.ArchiveUploader(state, api, commit_operation_add=FakeOperation)


def _upload(uploader: archive.ArchiveUploader, **kwargs):
    return uploader.upload_approved(
        acknowledge_public=archive.PUBLIC_ACK,
        acknowledge_partial_release=archive.PARTIAL_ACK,
        **kwargs,
    )


@pytest.mark.parametrize(
    ("source", "relative", "repo", "destination"),
    [
        ("pretrain", "fineweb-edu/part-0.jsonl", archive.DATA_REPO, "pretrain/fineweb-edu/part-0.jsonl"),
        ("hnc-organism", "runs/run-1/events.jsonl", archive.RUNS_REPO, "runs/run-1/events.jsonl"),
        ("hnc-organism", "training/sft/train.jsonl", archive.DATA_REPO, "training/sft/train.jsonl"),
        ("hnc-organism", "training/aureon_tokenizer.json", archive.DATA_REPO, "training/aureon_tokenizer.json"),
        ("hnc-organism", "training/aureon_tokenizer.report.json", archive.DATA_REPO, "training/aureon_tokenizer.report.json"),
        ("hnc-organism", "training/other.txt", archive.ARCHIVE_REPO, "hnc-organism/training/other.txt"),
        ("hnc-organism", "models/canonical/model.safetensors", archive.ARCHIVE_REPO, "hnc-organism/models/canonical/model.safetensors"),
    ],
)
def test_required_mapping(source, relative, repo, destination):
    mapped = archive.map_destination(source, relative)
    assert mapped == archive.Destination(repo, destination)


def test_resume_reuses_unchanged_hashes(state, sources, monkeypatch):
    path = sources[1].path / "note.txt"
    path.write_text("stable", encoding="utf-8")
    original = archive._hash_and_scan
    calls = 0

    def counted(value):
        nonlocal calls
        calls += 1
        return original(value)

    monkeypatch.setattr(archive, "_hash_and_scan", counted)
    assert _scan(state)["hashed"] == 1
    first = state.file_rows()[0]
    assert calls == 1
    assert _scan(state)["reused"] == 1
    second = state.file_rows()[0]
    assert calls == 1
    assert second["sha256"] == first["sha256"]

    path.write_text("changed", encoding="utf-8")
    os.utime(path, ns=(path.stat().st_atime_ns, path.stat().st_mtime_ns + 1_000_000))
    assert _scan(state)["hashed"] == 1
    assert calls == 2


def test_interrupted_scan_is_durable_and_blocks_upload_until_resumed(state, sources, monkeypatch):
    (sources[1].path / "a.txt").write_text("a", encoding="utf-8")
    (sources[1].path / "b.txt").write_text("b", encoding="utf-8")
    original = archive.Inventory._scan_file
    calls = 0

    def interrupt_after_first(self, *args):
        nonlocal calls
        result = original(self, *args)
        calls += 1
        if calls == 1:
            raise RuntimeError("simulated interrupted process")
        return result

    monkeypatch.setattr(archive.Inventory, "_scan_file", interrupt_after_first)
    with pytest.raises(RuntimeError, match="interrupted"):
        _scan(state)
    assert state.scan_in_progress is True
    assert len(state.file_rows()) == 1
    with pytest.raises(archive.ArchiveError, match="incomplete"):
        _upload(_uploader(state, FakeHub()))
    with pytest.raises(archive.FinalVerificationError, match="incomplete"):
        archive.verify_remote(state, FakeHub(), final=True)

    monkeypatch.setattr(archive.Inventory, "_scan_file", original)
    result = _scan(state)
    assert result["reused"] == 1
    assert result["hashed"] == 1
    assert state.scan_in_progress is False


def test_inventory_and_public_exports(state, sources, tmp_path):
    known = sources[0].path / "fineweb-edu" / "part.jsonl"
    known.parent.mkdir()
    known.write_bytes(b'{"text":"public"}\n')
    project = sources[1].path / "runs" / "run.json"
    project.parent.mkdir()
    project.write_text("{}", encoding="utf-8")
    _scan(state)

    output = tmp_path / "public-export"
    summary = state.export_manifests(output)
    manifest = [json.loads(line) for line in (output / "manifest.jsonl").read_text().splitlines()]
    assert summary["approved_files"] == 2
    assert {row["destination"] for row in manifest} == {
        "pretrain/fineweb-edu/part.jsonl",
        "runs/run.json",
    }
    assert all(row["source_root"] in {"pretrain", "hnc-organism"} for row in manifest)
    assert str(tmp_path) not in (output / "manifest.jsonl").read_text()
    assert "local_path" not in (output / "manifest.jsonl").read_text()


def test_secret_and_license_gates_without_secret_disclosure(state, sources, tmp_path):
    pretrain = sources[0].path
    hnc = sources[1].path
    (pretrain / "fineweb").mkdir()
    (pretrain / "fineweb" / "ok.jsonl").write_text("data", encoding="utf-8")
    (pretrain / "unknown").mkdir()
    (pretrain / "unknown" / "review.jsonl").write_text("data", encoding="utf-8")
    (pretrain / "data" / "code").mkdir(parents=True)
    (pretrain / "data" / "code" / "raw.jsonl").write_text("data", encoding="utf-8")
    (pretrain / "data" / "code-python-edu").mkdir(parents=True)
    (pretrain / "data" / "code-python-edu" / "raw.jsonl").write_text("data", encoding="utf-8")
    (pretrain / "smollm-corpus" / "python-edu").mkdir(parents=True)
    (pretrain / "smollm-corpus" / "python-edu" / "ok.jsonl").write_text("data", encoding="utf-8")
    (hnc / "codeparrot").mkdir()
    (hnc / "codeparrot" / "raw.py").write_text("print('review')", encoding="utf-8")
    (hnc / "the-stack").mkdir()
    (hnc / "the-stack" / "raw.py").write_text("print('blocked')", encoding="utf-8")
    (hnc / ".env").write_text("PASSWORD=not-for-export", encoding="utf-8")
    (hnc / ".env.example").write_text("PASSWORD=your-placeholder-value", encoding="utf-8")
    secret = "hf_" + "A" * 32
    (hnc / "config.txt").write_text(f"token={secret}", encoding="utf-8")
    (hnc / "id_rsa").write_text("not read as a public key", encoding="utf-8")
    (hnc / "models").mkdir()
    (hnc / "models" / "config.json").write_text("{}", encoding="utf-8")
    (hnc / "runtime").mkdir()
    (hnc / "runtime" / "state.json").write_text("{}", encoding="utf-8")
    (hnc / ".git").mkdir()
    (hnc / ".git" / "config").write_text("[core]\n", encoding="utf-8")
    _scan(state)

    output = tmp_path / "exports"
    state.export_manifests(output)
    blocked_text = (output / "blocked.jsonl").read_text(encoding="utf-8")
    blocked = [json.loads(line) for line in blocked_text.splitlines()]
    by_path = {row["relative_path"]: row for row in blocked}
    assert "dotenv_file" in by_path[".env"]["block_reasons"]
    assert "huggingface_token" in by_path["config.txt"]["block_reasons"]
    assert "ssh_or_private_key_material" in by_path["id_rsa"]["block_reasons"]
    assert "license_or_provenance_review_required" in by_path["unknown/review.jsonl"]["block_reasons"]
    assert "codeparrot/raw.py" in by_path
    assert "the-stack/raw.py" in by_path
    assert "data/code/raw.jsonl" in by_path
    assert "data/code-python-edu/raw.jsonl" in by_path
    assert "models/config.json" in by_path
    assert "runtime/state.json" in by_path
    assert "version_control_internals" in by_path[".git/config"]["block_reasons"]
    assert secret not in blocked_text
    assert str(tmp_path) not in blocked_text
    approved = {
        json.loads(line)["relative_path"]
        for line in (output / "manifest.jsonl").read_text(encoding="utf-8").splitlines()
    }
    assert ".env.example" in approved
    assert "fineweb/ok.jsonl" in approved
    assert "smollm-corpus/python-edu/ok.jsonl" in approved


def test_symlink_is_recorded_but_never_followed(state, sources, tmp_path):
    outside = tmp_path / "outside" / "secret.txt"
    outside.parent.mkdir()
    outside.write_text("must not be inventoried", encoding="utf-8")
    link = sources[1].path / "linked-secret"
    try:
        link.symlink_to(outside)
    except (OSError, NotImplementedError) as error:
        pytest.skip(f"symlink fixture unavailable: {error}")
    _scan(state)
    assert state.file_rows() == []
    row = state.db.execute("SELECT * FROM symlinks").fetchone()
    assert row["target"] == str(outside)
    output = tmp_path / "exports"
    summary = state.export_manifests(output)
    assert summary["symlinks"] == 1
    public = json.loads((output / "manifest.jsonl").read_text(encoding="utf-8").strip())
    assert public["entry_type"] == "symlink"
    assert public["target_is_absolute"] is True
    assert "target" not in public
    assert str(outside) not in (output / "manifest.jsonl").read_text(encoding="utf-8")


def test_mutation_during_scan_is_blocked(state, sources, monkeypatch):
    path = sources[1].path / "changing.txt"
    path.write_text("before", encoding="utf-8")
    original = archive.scan_content_security

    def mutate_after_read(chunks):
        decision = original(chunks)
        path.write_text("after-and-longer", encoding="utf-8")
        return decision

    monkeypatch.setattr(archive, "scan_content_security", mutate_after_read)
    result = _scan(state)
    assert result["changed_during_scan"] == 1
    row = state.file_rows()[0]
    assert row["security_status"] == "unstable"
    assert "changed_during_scan" in json.loads(row["security_reasons"])
    assert row["sha256"] is None


def test_batch_file_byte_and_large_file_boundaries(state, sources):
    for name, size in (("a", 4), ("b", 4), ("c", 4), ("large", 10)):
        (sources[1].path / name).write_bytes(b"x" * size)
    _scan(state)
    rows = state.file_rows()
    batches = archive.build_batches(rows, max_files=2, max_bytes=8, large_file_bytes=9)
    assert [[row["relative_path"] for row in batch.files] for batch in batches] == [["a", "b"], ["c"], ["large"]]
    assert [batch.byte_count for batch in batches] == [8, 4, 10]


def test_remote_hash_skip_and_lfs_verification(state, sources):
    data = b"already present"
    path = sources[1].path / "present.bin"
    path.write_bytes(data)
    _scan(state)
    row = state.file_rows()[0]
    api = FakeHub()
    api.remote[row["repo_id"]] = {row["destination"]: _entry(row["destination"], data, lfs=True)}
    result = _upload(_uploader(state, api))
    assert result["skipped_remote"] == 1
    assert api.commits == []
    verified = state.file_rows()[0]
    assert verified["verification_status"] == "verified"
    assert verified["remote_sha256"] == hashlib.sha256(data).hexdigest()
    assert verified["revision"] == "initial-revision"


def test_upload_retries_without_duplicating_verified_files(state, sources):
    (sources[1].path / "a.txt").write_text("a", encoding="utf-8")
    (sources[1].path / "b.txt").write_text("b", encoding="utf-8")
    _scan(state)
    api = FakeHub()
    api.fail_on_commit = 2
    uploader = _uploader(state, api)
    with pytest.raises(archive.BatchUploadError):
        _upload(uploader, max_files=1)
    statuses = {row["relative_path"]: row["verification_status"] for row in state.file_rows()}
    assert statuses == {"a.txt": "verified", "b.txt": None}

    result = _upload(uploader, max_files=1)
    assert result["uploaded_files"] == 1
    attempted_paths = [path for commit in api.commits for path in commit]
    assert len(attempted_paths) == len(set(attempted_paths))
    assert all(row["verification_status"] == "verified" for row in state.file_rows())
    assert all(row["revision"] for row in state.file_rows())


def test_remote_mismatch_is_not_marked_verified(state, sources):
    (sources[1].path / "bad.txt").write_text("content", encoding="utf-8")
    _scan(state)
    row = state.file_rows()[0]
    api = FakeHub()
    api.mismatch.add((row["repo_id"], row["destination"]))
    with pytest.raises(archive.BatchUploadError):
        _upload(_uploader(state, api))
    assert state.file_rows()[0]["verification_status"] == "mismatch"


def test_final_verification_fails_on_blockers_and_remote_errors(state, sources):
    (sources[1].path / ".env").write_text("SECRET=blocked", encoding="utf-8")
    _scan(state)
    api = FakeHub()
    with pytest.raises(archive.FinalVerificationError, match="blocked"):
        archive.verify_remote(state, api, final=True)
    assert api.info_calls == 0

    state.record_license_review("hnc-organism", ".env", approve=True, reason="test only", reviewer="tester")
    # A license review cannot override a security blocker.
    with pytest.raises(archive.FinalVerificationError):
        archive.verify_remote(state, api, final=True)


def test_final_verification_checks_every_approved_remote_file(state, sources):
    (sources[1].path / "one.txt").write_text("one", encoding="utf-8")
    (sources[1].path / "two.txt").write_text("two", encoding="utf-8")
    _scan(state)
    api = FakeHub()
    with pytest.raises(archive.FinalVerificationError, match="missing or mismatched") as caught:
        archive.verify_remote(state, api, file_filter=archive.FileFilter(globs=("one.txt",)), final=True)
    assert caught.value.summary["missing_files"] == 2
    assert all(row["verification_status"] == "missing" for row in state.file_rows())


def test_approved_upload_excludes_blocked_siblings(state, sources):
    (sources[1].path / "public.txt").write_text("public", encoding="utf-8")
    (sources[1].path / ".env").write_text("PRIVATE=blocked", encoding="utf-8")
    _scan(state)
    api = FakeHub()
    result = _upload(_uploader(state, api))
    assert result["uploaded_files"] == 1
    assert result["blocked_files_in_selection"] == 1
    assert result["unresolved_blockers_total"] == 1
    assert [path for commit in api.commits for path in commit] == ["hnc-organism/public.txt"]
    assert len(state.unresolved_blockers()) == 1


def test_cli_inventory_and_export(tmp_path, sources, capsys):
    (sources[1].path / "cli.txt").write_text("cli", encoding="utf-8")
    state_path = tmp_path / "cli-state" / "state.sqlite3"
    output = tmp_path / "cli-export"
    assert archive.main([
        "inventory", "--state", str(state_path), "--pretrain-root", str(sources[0].path),
        "--hnc-root", str(sources[1].path),
    ]) == 0
    assert json.loads(capsys.readouterr().out)["files"] == 1
    assert archive.main(["export", "--state", str(state_path), "--output-dir", str(output)]) == 0
    assert json.loads(capsys.readouterr().out)["approved_files"] == 1
    assert (output / "manifest.jsonl").is_file()


def test_acknowledgements_and_state_location_are_enforced(state, sources, tmp_path):
    (sources[1].path / "one.txt").write_text("one", encoding="utf-8")
    _scan(state)
    api = FakeHub()
    with pytest.raises(archive.ArchiveError, match="public release"):
        _uploader(state, api).upload_approved(acknowledge_public=None, acknowledge_partial_release=archive.PARTIAL_ACK)
    with pytest.raises(archive.ArchiveError, match="approved-only"):
        _uploader(state, api).upload_approved(acknowledge_public=archive.PUBLIC_ACK, acknowledge_partial_release=None)
    assert api.created == []
    with pytest.raises(archive.ArchiveError, match="outside"):
        archive.ArchiveState(sources[1].path / "state.sqlite3", sources)
    assert not (sources[1].path / "state.sqlite3").exists()

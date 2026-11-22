"""Offline tests for guarded, immutable Hugging Face Space publication."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace

import pytest

from deploy.huggingface import publish_space as publisher

SOURCE_COMMIT = "a" * 40
MODEL_COMMIT = "b" * 40
SPACE_COMMIT = "c" * 40
TOKEN = "hf_" + "t" * 32


class FakeCheckout:
    def __init__(self, root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        self.root = root
        self.root.mkdir()
        self.head = SOURCE_COMMIT
        self.dirty = False
        self.modes: dict[str, str] = {}
        self.files = {
            path: f"# {path}\n".encode()
            for path in sorted(
                publisher.REQUIRED_PATHS - {"Dockerfile", ".dockerignore", "README.md"}
            )
        }
        self.files.update({
            "deploy/huggingface/Dockerfile": b"FROM scratch\n",
            "deploy/huggingface/Dockerfile.dockerignore": b".git\n",
            "deploy/huggingface/README.md": b"---\nsdk: docker\n---\nSpace card\n",
            "frontend/package.json": b'{"scripts":{"build":"vite build"}}\n',
            "frontend/package-lock.json": b'{"lockfileVersion":3}\n',
            "frontend/src/App.tsx": b"export default function App() { return null; }\n",
            "aureon/app.py": b"VALUE = 1\n",
            "aureon/.env.example": b"EXAMPLE_ONLY=\n",
        })
        monkeypatch.setattr(publisher, "_git_output", self._git_output)
        monkeypatch.setattr(publisher, "_blob_reader", self._blob_reader)

    def _oid(self, path: str) -> str:
        return hashlib.sha1(path.encode()).hexdigest()

    def _git_output(self, repo: Path, arguments: list[str]) -> bytes:
        assert repo == self.root
        if arguments[0] == "rev-parse":
            return f"{self.head}\n".encode()
        if arguments[0] == "status":
            return b"dirty\0" if self.dirty else b""
        if arguments[0] == "ls-tree":
            assert arguments[-1] == self.head
            records = []
            for path in sorted(self.files):
                mode = self.modes.get(path, "100644")
                records.append(f"{mode} blob {self._oid(path)}\t{path}".encode())
            return b"\0".join(records) + b"\0"
        raise AssertionError(arguments)

    @contextmanager
    def _blob_reader(self, repo: Path) -> Iterator:
        assert repo == self.root

        def read(oid: str) -> bytes:
            for path, content in self.files.items():
                if self._oid(path) == oid:
                    return content
            raise AssertionError(f"unknown fake object {oid}")

        yield read

    def stage(self, destination: Path) -> dict:
        return publisher.stage_space(self.root, destination)


class FakeApi:
    def __init__(self, hub: FakeHub, token: str | bool) -> None:
        self.hub = hub
        self.token = token
        self.uploads: list[dict] = []
        self.variables: list[dict] = []
        self.hardware_calls: list[dict] = []
        self.model_calls: list[dict] = []

    def whoami(self) -> dict:
        assert self.token == TOKEN
        return {"name": self.hub.username}

    def repo_info(self, **kwargs) -> SimpleNamespace:
        self.hub.repo_info_calls.append(kwargs)
        return SimpleNamespace(id=self.hub.remote_id)

    def list_repo_files(self, **kwargs) -> list[str]:
        self.hub.list_calls.append(kwargs)
        return list(self.hub.remote_files)

    def upload_folder(self, **kwargs) -> SimpleNamespace:
        assert self.token == TOKEN
        self.uploads.append(kwargs)
        return SimpleNamespace(oid=SPACE_COMMIT)

    def add_space_variable(self, **kwargs) -> None:
        assert self.token == TOKEN
        self.variables.append(kwargs)

    def request_space_hardware(self, **kwargs) -> None:
        assert self.token == TOKEN
        self.hardware_calls.append(kwargs)

    def model_info(self, **kwargs) -> SimpleNamespace:
        assert self.token is False
        self.model_calls.append(kwargs)
        return SimpleNamespace(sha=self.hub.model_sha, private=self.hub.model_private)


class FakeHub:
    def __init__(self) -> None:
        self.username = "GaryLeckey"
        self.remote_id = publisher.SPACE_REPOSITORY
        self.remote_files = [".gitattributes"]
        self.model_sha = MODEL_COMMIT
        self.model_private = False
        self.apis: list[FakeApi] = []
        self.repo_info_calls: list[dict] = []
        self.list_calls: list[dict] = []

    def __call__(self, token: str | bool) -> FakeApi:
        api = FakeApi(self, token)
        self.apis.append(api)
        return api

    @property
    def authenticated(self) -> FakeApi:
        return self.apis[0]


@pytest.fixture
def checkout(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> FakeCheckout:
    return FakeCheckout(tmp_path / "repo", monkeypatch)


def _publish(checkout: FakeCheckout, hub: FakeHub, **overrides) -> dict:
    arguments = {
        "model_revision": MODEL_COMMIT,
        "publish": True,
        "env": {"HF_TOKEN": TOKEN},
        "api_factory": hub,
    }
    arguments.update(overrides)
    return publisher.publish_space(checkout.root, **arguments)


def test_staging_allowlist_overrides_and_per_file_hashes(
    checkout: FakeCheckout,
    tmp_path: Path,
) -> None:
    checkout.files.update({
        ".git/config.py": b"not staged",
        "tests/test_example.py": b"not staged",
        ".test-tmp/cache.py": b"not staged",
        "aureon/.env": b"SECRET=not-staged",
        "aureon/runtime/state.py": b"not staged",
        "aureon/logs/old.py": b"not staged",
        "frontend/node_modules/pkg/index.js": b"not staged",
        "frontend/dist/stale.js": b"not staged",
        "frontend/model.safetensors": b"not staged",
        "training/checkpoint.pt": b"not staged",
        "training/archive.zip": b"not staged",
        "docs/not_needed.md": b"not staged",
        "docs/not_needed.py": b"not staged",
        "aureon-trading/aureon/duplicate.py": b"not staged",
    })

    staged = checkout.stage(tmp_path / "space")
    root = tmp_path / "space"

    assert (root / "Dockerfile").read_bytes() == checkout.files["deploy/huggingface/Dockerfile"]
    assert (root / ".dockerignore").read_bytes() == checkout.files[
        "deploy/huggingface/Dockerfile.dockerignore"
    ]
    assert (root / "README.md").read_bytes() == checkout.files["deploy/huggingface/README.md"]
    assert (root / "frontend/package.json").is_file()
    assert (root / "frontend/package-lock.json").is_file()
    assert (root / "frontend/src/App.tsx").is_file()
    assert (root / "aureon/.env.example").is_file()
    paths = {row["path"] for row in staged["files"]}
    assert not any(
        path.startswith((".git/", "tests/", ".test-tmp/", "frontend/dist/", "frontend/node_modules/"))
        for path in paths
    )
    assert "aureon/.env" not in paths
    assert "frontend/model.safetensors" not in paths
    assert "training/checkpoint.pt" not in paths
    assert "training/archive.zip" not in paths
    assert "docs/not_needed.md" not in paths
    assert "docs/not_needed.py" not in paths
    assert "aureon-trading/aureon/duplicate.py" not in paths
    assert staged["file_count"] == len(paths)
    for row in staged["files"]:
        content = root.joinpath(*row["path"].split("/")).read_bytes()
        assert row["sha256"] == hashlib.sha256(content).hexdigest()
        assert row["size_bytes"] == len(content)


def test_staging_refuses_symlink(checkout: FakeCheckout, tmp_path: Path) -> None:
    checkout.files["aureon/link.py"] = b"../outside.py"
    checkout.modes["aureon/link.py"] = "120000"

    with pytest.raises(publisher.PublishError, match="symbolic link"):
        checkout.stage(tmp_path / "space")


def test_staging_refuses_secret_content_without_echoing_it(
    checkout: FakeCheckout,
    tmp_path: Path,
) -> None:
    checkout.files["aureon/config.py"] = f'HF_TOKEN = "{TOKEN}"\n'.encode()

    with pytest.raises(publisher.PublishError, match="possible Hugging Face token") as caught:
        checkout.stage(tmp_path / "space")
    assert TOKEN not in str(caught.value)


def test_staging_refuses_key_material(checkout: FakeCheckout, tmp_path: Path) -> None:
    checkout.files["aureon/private.pem"] = b"not read"

    with pytest.raises(publisher.PublishError, match="key-material"):
        checkout.stage(tmp_path / "space")


def test_dirty_source_and_source_mismatch_are_refused(checkout: FakeCheckout, tmp_path: Path) -> None:
    checkout.dirty = True
    with pytest.raises(publisher.PublishError, match="source repository is dirty"):
        checkout.stage(tmp_path / "dirty")
    checkout.dirty = False

    with pytest.raises(publisher.PublishError, match="does not equal"):
        publisher.stage_space(checkout.root, tmp_path / "mismatch", expected_source="d" * 40)


@pytest.mark.parametrize("revision", ["main", "B" * 40, "b" * 39, "g" * 40])
def test_publication_requires_full_lowercase_model_revision(
    checkout: FakeCheckout,
    revision: str,
) -> None:
    with pytest.raises(publisher.PublishError, match=publisher.MODEL_VARIABLE):
        _publish(checkout, FakeHub(), model_revision=revision)


def test_publication_requires_environment_token_and_never_imports_for_dry_run(
    checkout: FakeCheckout,
) -> None:
    hub = FakeHub()
    with pytest.raises(publisher.PublishError, match="requires HF_TOKEN"):
        _publish(checkout, hub, env={})
    assert hub.apis == []

    dry_run = publisher.publish_space(checkout.root, api_factory=hub)
    assert dry_run["dry_run"] is True
    assert dry_run["space_commit"] is None
    assert hub.apis == []


def test_conflicting_environment_tokens_are_refused(checkout: FakeCheckout) -> None:
    hub = FakeHub()
    with pytest.raises(publisher.PublishError, match="disagree"):
        _publish(
            checkout,
            hub,
            env={"HF_TOKEN": TOKEN, "HUGGING_FACE_HUB_TOKEN": "different"},
        )
    assert hub.apis == []


def test_paid_activation_requires_explicit_acknowledgement(checkout: FakeCheckout) -> None:
    hub = FakeHub()
    with pytest.raises(publisher.PublishError, match="paid hardware billing"):
        _publish(checkout, hub, activate_l40s=True)
    assert hub.apis == []


def test_wrong_identity_and_different_remote_repository_are_refused(
    checkout: FakeCheckout,
) -> None:
    wrong_user = FakeHub()
    wrong_user.username = "someone-else"
    with pytest.raises(publisher.PublishError, match="exactly GaryLeckey"):
        _publish(checkout, wrong_user)
    assert wrong_user.authenticated.uploads == []

    wrong_repo = FakeHub()
    wrong_repo.remote_id = "GaryLeckey/another-space"
    with pytest.raises(publisher.PublishError, match="different Space repository"):
        _publish(checkout, wrong_repo)
    assert wrong_repo.authenticated.uploads == []


def test_private_model_blocks_every_space_write_even_without_activation(
    checkout: FakeCheckout,
) -> None:
    hub = FakeHub()
    hub.model_private = True

    with pytest.raises(publisher.PublishError, match="publicly readable model"):
        _publish(checkout, hub)

    assert hub.authenticated.uploads == []
    assert hub.authenticated.variables == []
    assert hub.authenticated.hardware_calls == []
    assert hub.repo_info_calls == []
    assert hub.list_calls == []


def test_unknown_remote_files_are_listed_and_refused_without_writes(
    checkout: FakeCheckout,
) -> None:
    hub = FakeHub()
    hub.remote_files.extend(["README.md", "legacy/old.py"])

    with pytest.raises(publisher.PublishError, match="unknown remote Space files") as caught:
        _publish(checkout, hub)

    assert "legacy/old.py" in str(caught.value)
    assert hub.authenticated.uploads == []
    assert hub.authenticated.variables == []
    assert hub.authenticated.hardware_calls == []


def test_reviewed_legacy_deletion_is_exact_and_preserves_gitattributes(
    checkout: FakeCheckout,
) -> None:
    hub = FakeHub()
    hub.remote_files.extend(["legacy/old.py", "legacy/data?.txt"])

    receipt = _publish(checkout, hub, reviewed_legacy_deletion=True)

    upload = hub.authenticated.uploads[0]
    assert upload["repo_id"] == "GaryLeckey/aureon-os"
    assert upload["repo_type"] == "space"
    assert upload["delete_patterns"] == ["legacy/data[?].txt", "legacy/old.py"]
    assert ".gitattributes" not in upload["delete_patterns"]
    assert receipt["legacy_files_deleted"] == ["legacy/data?.txt", "legacy/old.py"]
    assert hub.authenticated.variables == [{
        "repo_id": publisher.SPACE_REPOSITORY,
        "key": "AUREON_MODEL_REVISION",
        "value": MODEL_COMMIT,
    }]
    assert receipt["space_commit"] == SPACE_COMMIT


def test_public_model_is_checked_without_paid_activation_by_default(checkout: FakeCheckout) -> None:
    hub = FakeHub()

    receipt = _publish(checkout, hub)

    assert len(hub.apis) == 2
    assert hub.apis[1].token is False
    assert len(hub.apis[1].model_calls) == 1
    assert hub.authenticated.hardware_calls == []
    assert receipt["hardware"] == {
        "requested": None,
        "request_accepted": False,
        "activated": False,
        "running_verified": False,
        "sleep_time": None,
    }


def test_activation_uses_anonymous_exact_public_model_then_l40s_no_sleep(
    checkout: FakeCheckout,
) -> None:
    hub = FakeHub()

    receipt = _publish(
        checkout,
        hub,
        activate_l40s=True,
        paid_l40s_acknowledged=True,
    )

    assert len(hub.apis) == 2
    assert hub.apis[1].token is False
    assert hub.apis[1].model_calls == [{
        "repo_id": "GaryLeckey/aureon-7b",
        "revision": MODEL_COMMIT,
    }]
    assert hub.authenticated.hardware_calls == [{
        "repo_id": "GaryLeckey/aureon-os",
        "hardware": "l40s",
        "sleep_time": -1,
    }]
    assert receipt["hardware"] == {
        "requested": "l40s",
        "request_accepted": True,
        "activated": False,
        "running_verified": False,
        "sleep_time": -1,
    }


def test_activation_stops_when_anonymous_model_revision_is_not_exact(
    checkout: FakeCheckout,
) -> None:
    hub = FakeHub()
    hub.model_sha = "d" * 40

    with pytest.raises(publisher.PublishError, match="exact requested revision"):
        _publish(
            checkout,
            hub,
            activate_l40s=True,
            paid_l40s_acknowledged=True,
        )
    assert hub.authenticated.hardware_calls == []


def test_receipt_is_sanitized_and_atomic_writer_preserves_it(
    checkout: FakeCheckout,
    tmp_path: Path,
) -> None:
    hub = FakeHub()
    receipt = _publish(
        checkout,
        hub,
        env={"HUGGING_FACE_HUB_TOKEN": TOKEN},
        expected_source=SOURCE_COMMIT,
    )
    receipt_path = tmp_path / "receipt.json"
    publisher.write_receipt(receipt_path, receipt)

    serialized = receipt_path.read_text(encoding="utf-8")
    assert TOKEN not in serialized
    assert str(tmp_path) not in serialized
    assert json.loads(serialized) == receipt
    assert receipt["source_commit"] == SOURCE_COMMIT
    assert receipt["model_revision"] == MODEL_COMMIT
    assert receipt["space_commit"] == SPACE_COMMIT
    assert set(receipt["hardware"]) == {
        "requested", "request_accepted", "activated", "running_verified", "sleep_time"
    }
    assert all(set(row) == {"path", "size_bytes", "sha256"} for row in receipt["files"])

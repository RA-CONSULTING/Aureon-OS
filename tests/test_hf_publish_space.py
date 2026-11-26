"""Offline tests for guarded, immutable Hugging Face Space publication."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

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
            # The real repository tracks these at the root. Staged verbatim they
            # make the Hub deploy the Space as a Gradio app.
            "app.py": b"import gradio as gr\n\ngr.Interface(fn=None).launch()\n",
            "app.yaml": b"name: aureon-protection-hold\nservices: []\n",
            "requirements.txt": b"gradio==5.49.1\n",
            "docker-compose.yml": b"services:\n  edge:\n    image: nginx\n",
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
        return SimpleNamespace(
            id=self.hub.remote_id,
            sha=self.hub.remote_sha,
            cardData={"sdk": self.hub.remote_sdk},
        )

    def list_repo_files(self, **kwargs) -> list[str]:
        self.hub.list_calls.append(kwargs)
        return list(self.hub.remote_files)

    def create_commit(self, **kwargs) -> SimpleNamespace:
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
        self.remote_sha = "d" * 40
        self.remote_sdk = "docker"
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


def test_content_mode_matches_a_real_staging(
    checkout: FakeCheckout,
    tmp_path: Path,
) -> None:
    """A client that cannot build the tree must still upload exactly these bytes."""

    root = tmp_path / "space"
    staged = checkout.stage(root)

    content_root = tmp_path / "content"
    manifest = publisher.stage_space(
        checkout.root,
        tmp_path / "unused-tree",
        content_dir=content_root,
    )

    # Identical path set and identical per-path digest.
    tree_rows = {row["path"]: row for row in staged["files"]}
    content_rows = {row["path"]: row for row in manifest["files"]}
    assert set(content_rows) == set(tree_rows)
    for path, row in tree_rows.items():
        assert content_rows[path]["sha256"] == row["sha256"]
        assert content_rows[path]["size_bytes"] == row["size_bytes"]

    # The captured bytes are usable directly, and neutralization still applied.
    assert (content_root / "requirements.txt").read_bytes() == (
        publisher.NEUTRAL_SDK_METADATA["requirements.txt"]
    )
    assert b"gradio" not in (content_root / "app.py").read_bytes().lower()
    assert (content_root / "README.md").read_bytes() == (
        checkout.files["deploy/huggingface/README.md"]
    )


def test_content_mode_refuses_an_existing_directory(
    checkout: FakeCheckout,
    tmp_path: Path,
) -> None:
    existing = tmp_path / "content"
    existing.mkdir()

    with pytest.raises(publisher.PublishError, match="must be a fresh"):
        publisher.stage_space(checkout.root, tmp_path / "tree", content_dir=existing)


def test_staged_root_metadata_cannot_resolve_a_non_docker_sdk(
    checkout: FakeCheckout,
    tmp_path: Path,
) -> None:
    """The 2026-11-25 failure: a Docker card deployed as Gradio via root metadata."""

    root = tmp_path / "space"
    staged = checkout.stage(root)

    # Every source path survives: nothing is dropped from the path set.
    staged_paths = {row["path"] for row in staged["files"]}
    for name in ("app.py", "app.yaml", "requirements.txt", "docker-compose.yml"):
        assert name in staged_paths
        assert name in checkout.files  # the repository source is untouched
    # But no SDK marker or compose project is resolvable from the staged root.
    requirements = (root / "requirements.txt").read_text(encoding="utf-8")
    assert "gradio" not in requirements
    assert "streamlit" not in requirements
    assert requirements.startswith("#")

    app_py = (root / "app.py").read_bytes()
    assert b"import gradio" not in app_py
    assert b"gradio" not in app_py.lower()

    assert "services:" not in (root / "app.yaml").read_text(encoding="utf-8")
    assert yaml.safe_load(
        (root / "docker-compose.yml").read_text(encoding="utf-8")
    ) == {"services": {}}

    # The Dockerfile and card the Hub needs are the deploy ones, verbatim.
    assert (root / "Dockerfile").read_bytes() == checkout.files["deploy/huggingface/Dockerfile"]
    assert yaml.safe_load(
        (root / "README.md").read_text(encoding="utf-8").split("---\n")[1]
    )["sdk"] == "docker"


def test_staging_keeps_every_tracked_path(checkout: FakeCheckout, tmp_path: Path) -> None:
    root = tmp_path / "space"
    staged = checkout.stage(root)

    # Every tracked path survives, plus only the three overlay targets that the
    # Hub requires at the root. Neutralizing metadata never removes a path.
    staged_paths = {row["path"] for row in staged["files"]}
    assert staged_paths == set(checkout.files) | set(publisher.OVERRIDES.values())


def test_card_that_declares_a_non_docker_sdk_is_refused(
    checkout: FakeCheckout,
    tmp_path: Path,
) -> None:
    checkout.files["deploy/huggingface/README.md"] = b"---\nsdk: gradio\n---\nSpace card\n"

    with pytest.raises(publisher.PublishError, match="must declare sdk: docker"):
        checkout.stage(tmp_path / "space")


def test_staging_complete_tree_overrides_and_per_file_hashes(
    checkout: FakeCheckout,
    tmp_path: Path,
) -> None:
    checkout.files.update({
        "README.md": b"# Original source card\n",
        "Dockerfile": b"FROM original-guarded-image\n",
        ".dockerignore": b"original-ignore\n",
        ".git/config.py": b"tracked fixture\n",
        "tests/test_example.py": (
            b'synthetic = "-----BEGIN PRIVATE KEY-----\nsynthetic-only\n-----END PRIVATE KEY-----"\n'
        ),
        "tests/test_tokens.py": b"token = \"ghp_abcdefghijklmnopqrstuvwxy\"\n",
        ".test-tmp/cache.py": b"tracked fixture\n",
        "aureon/runtime/state.py": b"tracked fixture\n",
        "aureon/logs/old.py": b"tracked fixture\n",
        "frontend/node_modules/pkg/index.js": b"tracked fixture\n",
        "frontend/dist/stale.js": b"tracked fixture\n",
        "frontend/model.safetensors": b"tracked fixture\n",
        "training/checkpoint.pt": b"tracked fixture\n",
        "training/archive.zip": b"tracked fixture\n",
        "training/corpus/files.jsonl": (
            b'{"text":"-----BEGIN PRIVATE KEY-----\\nsynthetic-only\\n-----END PRIVATE KEY-----"}\n'
        ),
        "training/other.py": b"tracked fixture\n",
        "docs/not_needed.md": b"tracked fixture\n",
        "docs/not_needed.py": b"tracked fixture\n",
        "aureon-trading/aureon/duplicate.py": b"tracked fixture\n",
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
    assert paths == set(checkout.files) | set(publisher.OVERRIDES.values())
    assert staged["file_count"] == len(paths)
    for path, expected in checkout.files.items():
        if path in publisher.OVERRIDES.values():
            continue
        if path in publisher.SPACE_SDK_METADATA:
            # Hub SDK metadata is replaced with neutral content at the same path.
            assert root.joinpath(*path.split("/")).read_bytes() == (
                publisher.NEUTRAL_SDK_METADATA[path]
            )
            continue
        assert root.joinpath(*path.split("/")).read_bytes() == expected
    for row in staged["files"]:
        content = root.joinpath(*row["path"].split("/")).read_bytes()
        assert row["sha256"] == hashlib.sha256(content).hexdigest()
        assert row["size_bytes"] == len(content)


def test_staging_refuses_environment_credential_paths(
    checkout: FakeCheckout,
    tmp_path: Path,
) -> None:
    checkout.files["aureon/.env"] = b"SECRET=must-not-be-published"

    with pytest.raises(publisher.PublishError, match="environment credential path"):
        checkout.stage(tmp_path / "space")


def test_staging_refuses_realistic_private_key_material(
    checkout: FakeCheckout,
    tmp_path: Path,
) -> None:
    checkout.files["aureon/config.py"] = (
        b"-----BEGIN PRIVATE KEY-----\n" + b"A" * 64 + b"\n-----END PRIVATE KEY-----\n"
    )

    with pytest.raises(publisher.PublishError, match="possible private key"):
        checkout.stage(tmp_path / "space")


def test_staging_refuses_invalid_space_card_metadata(
    checkout: FakeCheckout,
    tmp_path: Path,
) -> None:
    card = b"---\nsdk: docker\nshort_description: " + b"x" * 61 + b"\nsuggested_hardware: l40s\n---\n"
    checkout.files["deploy/huggingface/README.md"] = card
    with pytest.raises(publisher.PublishError, match="short_description"):
        checkout.stage(tmp_path / "long-description")

    checkout.files["deploy/huggingface/README.md"] = card.replace(b"x" * 61, b"Aureon OS")
    with pytest.raises(publisher.PublishError, match=r"suggested_hardware.*l40sx1"):
        checkout.stage(tmp_path / "wrong-hardware")


def test_shipped_space_card_metadata_is_valid() -> None:
    card = Path(publisher.__file__).with_name("README.md").read_bytes()
    publisher._validate_space_card(card)


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
    assert upload["parent_commit"] == "d" * 40
    deletions = [
        operation.path_in_repo
        for operation in upload["operations"]
        if operation.__class__.__name__ == "CommitOperationDelete"
    ]
    additions = [
        operation.path_in_repo
        for operation in upload["operations"]
        if operation.__class__.__name__ == "CommitOperationAdd"
    ]
    assert deletions == ["legacy/data?.txt", "legacy/old.py"]
    assert ".gitattributes" not in deletions
    assert len(additions) == receipt["file_count"]
    assert hub.list_calls[0]["revision"] == "d" * 40
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


def test_activation_refuses_a_drifted_card_that_would_not_serve_the_image(
    checkout: FakeCheckout,
) -> None:
    hub = FakeHub()
    # The committed drift: the live card declares sdk: gradio, so the Hub runtime
    # substitutes a notebook server and ignores the published Docker image. A GPU
    # request against it buys idle hardware, so the publisher must refuse first.
    hub.remote_sdk = "gradio"

    with pytest.raises(publisher.PublishError, match="requires a Space card with sdk: docker") as caught:
        _publish(
            checkout,
            hub,
            activate_l40s=True,
            paid_l40s_acknowledged=True,
        )

    assert "gradio" in str(caught.value)
    assert hub.authenticated.uploads == []
    assert hub.authenticated.variables == []
    assert hub.authenticated.hardware_calls == []


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
        "hardware": "l40sx1",
        "sleep_time": -1,
    }]
    assert receipt["hardware"] == {
        "requested": "l40sx1",
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

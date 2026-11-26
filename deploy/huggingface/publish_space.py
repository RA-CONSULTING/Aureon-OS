#!/usr/bin/env python3
"""Stage and optionally publish the guarded Aureon OS Hugging Face Space.

The default is a local dry run. Publication is restricted to the existing
``GaryLeckey/aureon-os`` Space and uses a token supplied only through the
process environment. No command in this module creates a repository, logs in,
stores a token, or activates paid hardware without its separate gates.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import tempfile
from collections.abc import Callable, Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

import yaml

SPACE_REPOSITORY = "GaryLeckey/aureon-os"
MODEL_REPOSITORY = "GaryLeckey/aureon-7b"
SPACE_OWNER = "GaryLeckey"
MODEL_VARIABLE = "AUREON_MODEL_REVISION"
L40S_HARDWARE = "l40sx1"
# Paid hardware is only meaningful when the published Space still runs the
# Docker image that serves it. A Gradio-only card leaves the Hub runtime free to
# substitute a notebook server, which ignores this image and its GPU work.
EXPECTED_SPACE_SDK = "docker"
COMMIT_RE = re.compile(r"[0-9a-f]{40}\Z")


KEY_SUFFIXES = frozenset({".jks", ".key", ".keystore", ".p12", ".pem", ".pfx"})
SECRET_NAMES = frozenset({
    "credentials.json",
    "id_dsa",
    "id_ecdsa",
    "id_ed25519",
    "id_rsa",
    "secrets.json",
    "secrets.yaml",
    "secrets.yml",
})
SECRET_PATTERNS = (
    ("private key", re.compile(
        br"-----BEGIN (?:RSA |EC |OPENSSH |ENCRYPTED )?PRIVATE KEY-----"
        br"[ \t]*\r?\n(?:(?:Proc-Type|DEK-Info):[^\r\n]+\r?\n)*"
        br"[ \t]*[A-Za-z0-9+/]{48,}={0,2}"
    )),
    ("Hugging Face token", re.compile(br"(?<![A-Za-z0-9])hf_[A-Za-z0-9]{24,}(?![A-Za-z0-9])")),
    ("GitHub token", re.compile(br"(?<![A-Za-z0-9])(?:ghp|github_pat)_[A-Za-z0-9_]{24,}")),
    ("AWS access key", re.compile(br"(?<![A-Z0-9])(?:AKIA|ASIA)[A-Z0-9]{16}(?![A-Z0-9])")),
)
# Exact public test sentinel, not a credential. Keep its test and corpus rows
# without weakening detection of realistic GitHub tokens.
SYNTHETIC_CREDENTIAL_SENTINELS = (b"ghp_abcdefghijklmnopqrstuvwxy",)
OVERRIDES = {
    "deploy/huggingface/Dockerfile": "Dockerfile",
    "deploy/huggingface/Dockerfile.dockerignore": ".dockerignore",
    "deploy/huggingface/README.md": "README.md",
}
# The Hub reads these root files to choose and configure an SDK. This repository
# tracks them for non-Space purposes (a DigitalOcean hold manifest and the full
# desktop runtime requirements), and root app.py is the local entrypoint. Staged
# verbatim they make the Hub treat a Docker Space as a Gradio app, which is what
# happened on 2026-11-25: the card said sdk: docker, the launch served app.py,
# the Dockerfile never built, and no GPU was ever attached.
#
# These are replaced only in the staged copy. Repository sources keep their
# content, and the Docker image still receives every one of them through
# COPY . /app/aureon-os, because the image is built from the Space root where
# the neutral replacements below also apply.
SPACE_SDK_METADATA = (
    "app.py",
    "app.yaml",
    "requirements.txt",
    "docker-compose.yml",
)
# Neutral content for each. No SDK marker and no compose services means the Hub
# cannot resolve any SDK other than the Dockerfile declared by the card.
NEUTRAL_SDK_METADATA: dict[str, bytes] = {
    "requirements.txt": (
        b"# Intentionally empty in the Space staging root.\n"
        b"# The image installs from requirements-linux.txt (see Dockerfile).\n"
        b"# A Gradio/Streamlit requirements or app.py here makes the Hub deploy the\n"
        b"# repository as that SDK instead of building the Dockerfile.\n"
    ),
    "docker-compose.yml": (
        b"# Intentionally empty in the Space staging root: a Docker Space builds the\n"
        b"# Dockerfile, not a compose project.\n"
        b"services: {}\n"
    ),
    "app.yaml": b"# Intentionally empty in the Space staging root (no SDK markers).\n",
    "app.py": (
        b'"""Intentionally inert in the Space staging root.\n'
        b"\n"
        b"The public Space is the Docker image (see Dockerfile, entrypoint.sh, and\n"
        b"supervisord.conf). The Hub serves this path only when no Dockerfile applies,\n"
        b"so any interactive UI app here would mask the real organism console.\n"
        b'"""\n\n'
        b"def main() -> None:\n"
        b"    raise SystemExit(\n"
        b"        'This Space runs the Docker image; see deploy/huggingface/README.md.'\n"
        b"    )\n\n\n"
        b'if __name__ == "__main__":\n'
        b"    main()\n"
    ),
}
REQUIRED_PATHS = frozenset({
    ".dockerignore",
    "Dockerfile",
    "LICENSE",
    "README.md",
    "deploy/huggingface/Dockerfile",
    "deploy/huggingface/Dockerfile.dockerignore",
    "deploy/huggingface/README.md",
    "deploy/huggingface/demo_api.py",
    "deploy/huggingface/early_console.py",
    "deploy/huggingface/entrypoint.sh",
    "deploy/huggingface/model_bootstrap.py",
    "deploy/huggingface/model_service.sh",
    "deploy/huggingface/smoke.py",
    "deploy/huggingface/nginx.conf",
    "deploy/huggingface/supervisord.conf",
    "deploy/selfhost/error_sink.py",
    "deploy/selfhost/postgres/01_roles.sql",
    "deploy/selfhost/postgres/02_tables.sql",
    "frontend/index.html",
    "frontend/package-lock.json",
    "frontend/package.json",
    "huggingface/hnc-field/replay/brain.json",
    "huggingface/organism-replay/replay/organism.json",
    "pyproject.toml",
    "requirements-linux.txt",
    "supabase/migrations/20260811210525_lock_down_legacy_public_tables.sql",
    "training/aureon_chat_server.py",
})


class PublishError(RuntimeError):
    """A safe, actionable publication refusal."""


@dataclass(frozen=True)
class _TreeEntry:
    mode: str
    kind: str
    oid: str
    path: str


def require_commit(value: str, label: str) -> str:
    """Return one immutable lowercase commit or refuse the operation."""

    commit = str(value or "").strip()
    if not COMMIT_RE.fullmatch(commit):
        raise PublishError(f"{label} must be one full lowercase 40-character commit SHA")
    return commit


def _git_output(repo: Path, arguments: list[str]) -> bytes:
    result = subprocess.run(
        ["git", *arguments],
        cwd=repo,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        check=False,
    )
    if result.returncode:
        diagnostic = result.stderr.decode("utf-8", errors="replace").strip()[:2000]
        raise PublishError(f"git {arguments[0]} failed: {diagnostic}")
    return result.stdout


def _clean_head(repo: Path, expected: str | None) -> str:
    if not repo.is_dir():
        raise PublishError("source repository directory does not exist")
    head = require_commit(
        _git_output(repo, ["rev-parse", "HEAD"]).decode("ascii", errors="strict").strip(),
        "source HEAD",
    )
    if expected is not None and head != require_commit(expected, "expected source revision"):
        raise PublishError("expected source revision does not equal the clean source HEAD")
    if _git_output(repo, ["status", "--porcelain=v1", "--untracked-files=all", "-z"]):
        raise PublishError("source repository is dirty; commit or remove every tracked and untracked change")
    return head


def _validate_path(path: str) -> str:
    if not path or "\\" in path or "\x00" in path or path.startswith("/"):
        raise PublishError(f"unsafe relative path: {json.dumps(path)}")
    pure = PurePosixPath(path)
    if any(part in {"", ".", ".."} for part in pure.parts) or pure.parts[0].endswith(":"):
        raise PublishError(f"unsafe relative path: {json.dumps(path)}")
    return pure.as_posix()



def _refuse_secret_path(path: str) -> None:
    pure = PurePosixPath(path)
    name = pure.name.casefold()
    if (name == ".env" or name.startswith(".env.")) and name != ".env.example":
        raise PublishError(f"refusing environment credential path: {path}")
    if name in SECRET_NAMES or pure.suffix.casefold() in KEY_SUFFIXES:
        raise PublishError(f"refusing secret or key-material path: {path}")


def _refuse_secret_content(path: str, content: bytes) -> None:
    scanned = content
    for sentinel in SYNTHETIC_CREDENTIAL_SENTINELS:
        scanned = scanned.replace(sentinel, b"synthetic-credential-fixture")
    for label, pattern in SECRET_PATTERNS:
        if pattern.search(scanned):
            # Never include the matched value in an exception or receipt.
            raise PublishError(f"refusing possible {label} in staged source path: {path}")


def _validate_space_card(content: bytes) -> None:
    """Reject known Hub metadata errors before any authenticated write."""

    try:
        text = content.decode("utf-8")
        match = re.match(r"\A---[ \t]*\r?\n(.*?)\r?\n---[ \t]*\r?\n", text, re.DOTALL)
        metadata = yaml.safe_load(match.group(1)) if match else None
    except (UnicodeError, yaml.YAMLError) as exc:
        raise PublishError("Space README has invalid YAML front matter") from exc
    if not isinstance(metadata, dict):
        raise PublishError("Space README must start with YAML front matter")
    _validate_space_metadata(metadata)


def _validate_space_metadata(metadata: dict[str, Any]) -> None:
    """Validate the Hub metadata the card is about to publish."""

    if metadata.get("sdk") != EXPECTED_SPACE_SDK:
        raise PublishError(
            f"Space README must declare sdk: {EXPECTED_SPACE_SDK}; this card declares "
            f"{metadata.get('sdk')!r}. Any other SDK makes the Hub deploy the repository "
            "as that SDK and never build the Dockerfile."
        )
    description = metadata.get("short_description")
    if description is not None and (
        not isinstance(description, str) or not 1 <= len(description.strip()) <= 60
    ):
        raise PublishError("Space README short_description must contain 1 to 60 characters")
    hardware = metadata.get("suggested_hardware")
    if hardware is not None and hardware != L40S_HARDWARE:
        raise PublishError(f"Space README suggested_hardware must be {L40S_HARDWARE} for one L40S")


def _tree_entries(repo: Path, commit: str) -> list[_TreeEntry]:
    raw = _git_output(repo, ["ls-tree", "-r", "-z", "--full-tree", commit])
    entries: list[_TreeEntry] = []
    for record in raw.split(b"\0"):
        if not record:
            continue
        try:
            metadata, raw_path = record.split(b"\t", 1)
            mode, kind, oid = metadata.decode("ascii").split(" ", 2)
            path = _validate_path(raw_path.decode("utf-8"))
        except (UnicodeError, ValueError) as exc:
            raise PublishError("git ls-tree returned an invalid or non-UTF-8 path") from exc
        entries.append(_TreeEntry(mode=mode, kind=kind, oid=oid, path=path))
    return entries


def _selected_entries(entries: list[_TreeEntry]) -> list[_TreeEntry]:
    """Return the complete tracked tree; never curate paths by perceived relevance."""

    selected: list[_TreeEntry] = []
    seen: set[str] = set()
    for entry in entries:
        path = entry.path
        _refuse_secret_path(path)
        if entry.mode == "120000":
            raise PublishError(f"refusing symbolic link in Space source: {path}")
        if entry.kind != "blob" or entry.mode not in {"100644", "100755"}:
            raise PublishError(f"refusing unsupported Git entry in Space source: {path}")
        if path in seen:
            raise PublishError(f"refusing duplicate Git path in Space source: {path}")
        seen.add(path)
        selected.append(entry)
    return sorted(selected, key=lambda item: item.path)


def _refuse_windows_case_collisions(entries: list[_TreeEntry]) -> None:
    """Keep case-distinct tracked files intact by requiring a case-sensitive stager."""

    if os.name != "nt":
        return
    seen: dict[str, str] = {}
    for entry in entries:
        folded = entry.path.casefold()
        previous = seen.get(folded)
        if previous is not None and previous != entry.path:
            raise PublishError(
                "case-distinct tracked paths require staging on a case-sensitive Linux filesystem: "
                + json.dumps([previous, entry.path])
            )
        seen[folded] = entry.path


@contextmanager
def _blob_reader(repo: Path) -> Iterator[Callable[[str], bytes]]:
    """Read selected objects through one request/response Git process."""

    process = subprocess.Popen(
        ["git", "cat-file", "--batch"],
        cwd=repo,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    failed = True

    def read_blob(oid: str) -> bytes:
        if process.stdin is None or process.stdout is None:
            raise PublishError("git cat-file pipes are unavailable")
        process.stdin.write(oid.encode("ascii") + b"\n")
        process.stdin.flush()
        header = process.stdout.readline(4096)
        try:
            returned_oid, kind, raw_size = header.decode("ascii").rstrip("\n").split(" ", 2)
            size = int(raw_size)
        except (UnicodeError, ValueError) as exc:
            raise PublishError("git cat-file returned an invalid object header") from exc
        if returned_oid != oid or kind != "blob" or size < 0:
            raise PublishError("git cat-file returned an unexpected object")
        chunks: list[bytes] = []
        remaining = size
        while remaining:
            chunk = process.stdout.read(min(remaining, 1024 * 1024))
            if not chunk:
                raise PublishError("git cat-file returned a truncated object")
            chunks.append(chunk)
            remaining -= len(chunk)
        if process.stdout.read(1) != b"\n":
            raise PublishError("git cat-file returned invalid object framing")
        return b"".join(chunks)

    try:
        yield read_blob
        failed = False
    finally:
        if process.stdin is not None and not process.stdin.closed:
            process.stdin.close()
        if failed and process.poll() is None:
            process.terminate()
        returncode = process.wait(timeout=15)
        if not failed and returncode:
            diagnostic = ""
            if process.stderr is not None:
                diagnostic = process.stderr.read().decode("utf-8", errors="replace").strip()[:2000]
            raise PublishError(f"git cat-file failed: {diagnostic}")


def _write_new_file(
    root: Path,
    relative: str,
    content: bytes,
    *,
    replace: bool = False,
) -> dict[str, Any]:
    relative = _validate_path(relative)
    destination = root.joinpath(*PurePosixPath(relative).parts)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if not destination.parent.resolve().is_relative_to(root.resolve()):
        raise PublishError("staged file escapes the fresh staging directory")
    with destination.open("wb" if replace else "xb") as handle:
        handle.write(content)
    return {
        "path": relative,
        "size_bytes": len(content),
        "sha256": hashlib.sha256(content).hexdigest(),
    }


def stage_space(
    repo: Path,
    destination: Path,
    *,
    expected_source: str | None = None,
    content_dir: Path | None = None,
) -> dict[str, Any]:
    """Stage every tracked file from one exact clean Git commit.

    ``content_dir`` writes the exact final bytes of every staged file as an
    additive manifest, so a client that cannot create the tree itself (a
    Windows filesystem with case-distinct paths) can still upload precisely what
    staging would have produced. The manifest is built from Git objects only, so
    it is identical to a byte-for-byte staging on a case-sensitive filesystem.
    """

    repo = Path(repo).resolve()
    destination = Path(destination)
    if content_dir is not None:
        destination = Path(content_dir).resolve()
        if destination.exists():
            raise PublishError("content directory must be a fresh, nonexistent path")
        destination.mkdir(parents=True)
    head = _clean_head(repo, expected_source)
    selected = _selected_entries(_tree_entries(repo, head))
    _refuse_windows_case_collisions(selected)
    if content_dir is None:
        if destination.exists() or destination.is_symlink():
            raise PublishError("staging destination must be a fresh, nonexistent path")
        destination.mkdir()
    manifest: list[dict[str, Any]] = []
    with _blob_reader(repo) as read_blob:
        for entry in selected:
            content = read_blob(entry.oid)
            _refuse_secret_content(entry.path, content)
            manifest.append(_write_new_file(destination, entry.path, content))

    # Keep every tracked path. Space-required root metadata replaces the content
    # at the same three paths rather than dropping or renaming any source path.
    for source, target in OVERRIDES.items():
        source_path = destination.joinpath(*PurePosixPath(source).parts)
        if not source_path.is_file() or source_path.is_symlink():
            raise PublishError(f"required Space override is absent: {source}")
        target_path = destination.joinpath(*PurePosixPath(target).parts)
        if target_path.exists():
            if not target_path.is_file() or target_path.is_symlink():
                raise PublishError(f"Space override target is not a regular file: {target}")
            target_path.unlink()
            manifest = [row for row in manifest if row["path"] != target]
        manifest.append(_write_new_file(destination, target, source_path.read_bytes()))

    # Neutralize every root file the Hub reads to pick an SDK. Each path is
    # rewritten in place in the staged tree, so the path set never shrinks and
    # the Docker build context still receives a file at every tracked location.
    for name in SPACE_SDK_METADATA:
        target_path = destination.joinpath(*PurePosixPath(name).parts)
        if target_path.is_symlink():
            raise PublishError(f"staged path must not be a symlink: {name}")
        if content_dir is not None:
            # Content mode never wrote the raw files; they exist only in the
            # manifest, so neutralize by replacing that entry.
            if not any(row["path"] == name for row in manifest):
                continue
        elif target_path.is_file():
            target_path.unlink()
        else:
            # Absent is fine: nothing can mislead the Hub.
            continue
        manifest = [row for row in manifest if row["path"] != name]
        manifest.append(
            _write_new_file(
                destination,
                name,
                NEUTRAL_SDK_METADATA[name],
                # Content mode already wrote the raw file; overwrite in place.
                replace=content_dir is not None,
            )
        )

    _validate_space_card((destination / "README.md").read_bytes())
    paths = {row["path"] for row in manifest}
    missing = sorted(REQUIRED_PATHS - paths)
    if not any(path.startswith("frontend/src/") for path in paths):
        missing.append("frontend/src/ (at least one source file)")
    if missing:
        raise PublishError(f"Space source is incomplete: {json.dumps(missing)}")

    # A checkout change during staging cannot alter the blobs already selected,
    # but refusing it here keeps the recorded clean-HEAD contract explicit.
    if _clean_head(repo, head) != head:
        raise PublishError("source HEAD changed during staging")
    manifest.sort(key=lambda row: row["path"])
    return {
        "schema_version": 1,
        "source_commit": head,
        "file_count": len(manifest),
        "files": manifest,
    }


def _token_from_environment(env: Mapping[str, str]) -> str:
    primary = env.get("HF_TOKEN", "").strip()
    fallback = env.get("HUGGING_FACE_HUB_TOKEN", "").strip()
    if primary and fallback and primary != fallback:
        raise PublishError("HF_TOKEN and HUGGING_FACE_HUB_TOKEN disagree; set only one")
    token = primary or fallback
    if not token:
        raise PublishError("publication requires HF_TOKEN or HUGGING_FACE_HUB_TOKEN in the environment")
    return token


def _lazy_hf_api(token: str | bool) -> Any:
    from huggingface_hub import HfApi

    # False is intentional: model verification must not use cached credentials.
    return HfApi(token=token)


def _safe_unknown_remote(remote_files: list[str], staged_paths: set[str]) -> list[str]:
    unknown: set[str] = set()
    for raw_path in remote_files:
        path = _validate_path(raw_path)
        if path not in staged_paths and path.casefold() != ".gitattributes":
            unknown.add(path)
    return sorted(unknown)


def _commit_exact_snapshot(
    api: Any,
    destination: Path,
    staged: Mapping[str, Any],
    *,
    legacy_files: list[str],
    parent_commit: str,
) -> Any:
    """Commit exact reviewed paths without an O(remote x legacy) glob scan."""

    from huggingface_hub import CommitOperationAdd, CommitOperationDelete

    operations: list[Any] = [
        CommitOperationDelete(path_in_repo=path, is_folder=False)
        for path in legacy_files
    ]
    for row in staged["files"]:
        relative = row["path"]
        source = destination.joinpath(*PurePosixPath(relative).parts)
        if not source.is_file() or source.is_symlink():
            raise PublishError(f"staged file is unavailable for commit: {relative}")
        if source.stat().st_size != row["size_bytes"]:
            raise PublishError(f"staged file size changed before commit: {relative}")
        operations.append(CommitOperationAdd(path_or_fileobj=str(source), path_in_repo=relative))
    return api.create_commit(
        repo_id=SPACE_REPOSITORY,
        repo_type="space",
        commit_message=f"Publish Aureon OS from source {staged['source_commit']}",
        operations=operations,
        parent_commit=parent_commit,
    )


def _base_receipt(
    staged: dict[str, Any],
    model_revision: str | None,
    *,
    dry_run: bool,
    activate_l40s: bool,
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "dry_run": dry_run,
        "source_commit": staged["source_commit"],
        "model_repository": MODEL_REPOSITORY,
        "model_revision": model_revision,
        "space_repository": SPACE_REPOSITORY,
        "space_commit": None,
        "file_count": staged["file_count"],
        "files": staged["files"],
        "legacy_files_deleted": [],
        "hardware": {
            "requested": L40S_HARDWARE if activate_l40s else None,
            "request_accepted": False,
            "activated": False,
            "running_verified": False,
            "sleep_time": None,
        },
    }


def publish_space(
    repo: Path,
    *,
    model_revision: str | None = None,
    expected_source: str | None = None,
    publish: bool = False,
    reviewed_legacy_deletion: bool = False,
    activate_l40s: bool = False,
    paid_l40s_acknowledged: bool = False,
    staging_dir: Path | None = None,
    content_dir: Path | None = None,
    env: Mapping[str, str] | None = None,
    api_factory: Callable[[str | bool], Any] | None = None,
) -> dict[str, Any]:
    """Return a sanitized receipt; perform Hub writes only with publish=True."""

    if activate_l40s and not paid_l40s_acknowledged:
        raise PublishError("L40S activation requires explicit acknowledgement of paid hardware billing")
    if paid_l40s_acknowledged and not activate_l40s:
        raise PublishError("paid-hardware acknowledgement is valid only with L40S activation")
    if model_revision is not None or publish or activate_l40s:
        model_revision = require_commit(model_revision or "", MODEL_VARIABLE)

    @contextmanager
    def staging() -> Iterator[Path]:
        if staging_dir is not None:
            yield Path(staging_dir)
            return
        with tempfile.TemporaryDirectory(prefix="aureon-space-stage-") as temporary:
            yield Path(temporary) / "space"

    with staging() as destination:
        staged = stage_space(
            repo,
            destination,
            expected_source=expected_source,
            content_dir=content_dir,
        )
        receipt = _base_receipt(
            staged,
            model_revision,
            dry_run=not publish,
            activate_l40s=activate_l40s,
        )
        if not publish:
            return receipt

        token = _token_from_environment(os.environ if env is None else env)
        factory = _lazy_hf_api if api_factory is None else api_factory
        api = factory(token)
        identity = api.whoami()
        if identity.get("name") != SPACE_OWNER:
            raise PublishError(f"Hub token identity must be exactly {SPACE_OWNER}")

        # Model publication precedes every Space write, not just paid activation.
        # An anonymous client proves that the immutable model is publicly usable.
        anonymous = factory(False)
        model_info = anonymous.model_info(repo_id=MODEL_REPOSITORY, revision=model_revision)
        if getattr(model_info, "private", False):
            raise PublishError("Space publication requires a publicly readable model")
        if getattr(model_info, "sha", None) != model_revision:
            raise PublishError("anonymous model_info did not resolve the exact requested revision")

        space_info = api.repo_info(repo_id=SPACE_REPOSITORY, repo_type="space")
        remote_id = getattr(space_info, "id", None)
        if remote_id is not None and remote_id != SPACE_REPOSITORY:
            raise PublishError("Hub returned a different Space repository; refusing publication")
        remote_revision = require_commit(str(getattr(space_info, "sha", "")), "remote Space revision")
        remote_files = api.list_repo_files(
            repo_id=SPACE_REPOSITORY,
            repo_type="space",
            revision=remote_revision,
        )
        if activate_l40s:
            # The image is only served when the live card still declares the
            # Docker SDK. Refuse paid activation against a drifted card instead
            # of requesting a GPU that the deployed process cannot use.
            card = getattr(space_info, "cardData", None)
            card = card if isinstance(card, Mapping) else {}
            if card.get("sdk") != EXPECTED_SPACE_SDK:
                raise PublishError(
                    "paid L40S activation requires a Space card with sdk: "
                    f"{EXPECTED_SPACE_SDK}; remote card declares sdk: {card.get('sdk')!r}"
                )
        unknown = _safe_unknown_remote(remote_files, {row["path"] for row in staged["files"]})
        if unknown and not reviewed_legacy_deletion:
            raise PublishError(
                "unknown remote Space files require explicit reviewed legacy deletion: "
                + json.dumps(unknown)
            )

        uploaded = _commit_exact_snapshot(
            api,
            destination,
            staged,
            legacy_files=unknown,
            parent_commit=remote_revision,
        )
        space_commit = getattr(uploaded, "oid", None) or getattr(uploaded, "sha", None)
        receipt["space_commit"] = require_commit(str(space_commit or ""), "published Space commit")
        receipt["legacy_files_deleted"] = unknown

        # This is a nonsecret variable, never a Space secret or a logged value.
        api.add_space_variable(
            repo_id=SPACE_REPOSITORY,
            key=MODEL_VARIABLE,
            value=model_revision,
        )

        if activate_l40s:
            api.request_space_hardware(
                repo_id=SPACE_REPOSITORY,
                hardware=L40S_HARDWARE,
                sleep_time=-1,
            )
            # The API accepted a paid hardware request. Only a subsequent real
            # runtime/readiness probe can establish that the L40S is running.
            receipt["hardware"] = {
                "requested": L40S_HARDWARE,
                "request_accepted": True,
                "activated": False,
                "running_verified": False,
                "sleep_time": -1,
            }
        return receipt


def write_receipt(path: Path, receipt: Mapping[str, Any]) -> None:
    """Atomically write the already-sanitized receipt without environment data."""

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    content = (json.dumps(receipt, indent=2, sort_keys=True, allow_nan=False) + "\n").encode("utf-8")
    descriptor, temporary_name = tempfile.mkstemp(prefix=".space-receipt-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, path)
    except Exception:
        Path(temporary_name).unlink(missing_ok=True)
        raise


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--source-revision", help="optional expected clean source HEAD")
    parser.add_argument(
        "--model-revision",
        default=os.environ.get(MODEL_VARIABLE),
        help="full lowercase GaryLeckey/aureon-7b commit (or AUREON_MODEL_REVISION)",
    )
    parser.add_argument("--staging-dir", type=Path, help="fresh path to retain; otherwise a temp path is used")
    parser.add_argument(
        "--content-dir",
        type=Path,
        help=(
            "write the exact staged bytes to this fresh path instead of creating the "
            "staged tree, for filesystems that cannot hold case-distinct paths"
        ),
    )
    parser.add_argument("--publish", action="store_true", help="perform Hub writes; omitted means dry-run")
    parser.add_argument("--reviewed-legacy-deletion", action="store_true")
    parser.add_argument("--activate-l40s", action="store_true")
    parser.add_argument("--acknowledge-paid-l40s", action="store_true")
    parser.add_argument("--receipt", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = _parser().parse_args(argv)
    try:
        receipt = publish_space(
            arguments.repo,
            model_revision=arguments.model_revision,
            expected_source=arguments.source_revision,
            publish=arguments.publish,
            reviewed_legacy_deletion=arguments.reviewed_legacy_deletion,
            activate_l40s=arguments.activate_l40s,
            paid_l40s_acknowledged=arguments.acknowledge_paid_l40s,
            staging_dir=arguments.staging_dir,
            content_dir=arguments.content_dir,
        )
        if arguments.receipt is not None:
            write_receipt(arguments.receipt, receipt)
    except PublishError as exc:
        print(f"Space publication refused: {exc}", flush=True)
        return 2
    except Exception as exc:  # Hub diagnostics can contain request metadata; do not echo them.
        print(f"Space publication failed safely ({type(exc).__name__})", flush=True)
        return 1
    print(json.dumps(receipt, indent=2, sort_keys=True, allow_nan=False), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

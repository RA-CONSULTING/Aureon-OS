"""Prove release source hashes ignore Windows checkout line conversion."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import shutil
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
DEPLOYMENT = ROOT / "deployment/google-cloud"
CONTROL = DEPLOYMENT / "trading-control"
sys.path.insert(0, str(DEPLOYMENT))
sys.path.insert(0, str(CONTROL))


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


bundle = load("clone_stable_bundle", DEPLOYMENT / "build_release_bundle.py")
generator = load("clone_stable_paths", DEPLOYMENT / "generate_reviewed_paths.py")
images = load("clone_stable_images", CONTROL / "immutable_image_build.py")


def git(directory: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(directory), *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


@pytest.mark.skipif(shutil.which("git") is None, reason="git unavailable")
def test_release_hashes_are_clone_stable_with_autocrlf(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    (source / ".gitattributes").write_bytes(b"# no release EOL override\n")
    relative = "aureon_fusion/example.py"
    path = source / relative
    path.parent.mkdir(parents=True)
    committed = b"VALUE = 1\nSECOND = 2\n"
    path.write_bytes(committed)
    git(source, "init")
    git(source, "config", "user.email", "fixture@example.invalid")
    git(source, "config", "user.name", "Fixture")
    git(source, "add", ".")
    git(source, "commit", "-m", "fixture")
    revision = git(source, "rev-parse", "HEAD")

    windows_clone = tmp_path / "windows-clone"
    linux_clone = tmp_path / "linux-clone"
    subprocess.run(
        [
            "git",
            "-c",
            "core.autocrlf=true",
            "clone",
            "--quiet",
            str(source),
            str(windows_clone),
        ],
        check=True,
    )
    subprocess.run(
        [
            "git",
            "-c",
            "core.autocrlf=false",
            "clone",
            "--quiet",
            str(source),
            str(linux_clone),
        ],
        check=True,
    )

    for reader in (bundle._git_blob, generator._git_blob, images._git_blob):
        assert reader(windows_clone, revision, relative) == committed
        assert reader(linux_clone, revision, relative) == committed

    selected = [{"path": relative, "sha256": bundle.digest(committed)}]
    manifests = []
    payloads = []
    for index, checkout in enumerate((windows_clone, linux_clone)):
        destination = tmp_path / f"bundle-{index}"
        manifest = bundle.build(
            checkout,
            selected,
            destination,
            revision,
            f"20260913T18000{index}Z-aaaaaaaa",
        )
        manifests.append(manifest["payload_sha256"])
        payloads.append((destination / "files" / relative).read_bytes())
    assert manifests[0] == manifests[1]
    assert payloads == [committed, committed]

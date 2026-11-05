"""Public source-archive channel. Production publish stays refused on this tip."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _channel():
    path = ROOT / "packaging" / "release_channel.py"
    spec = importlib.util.spec_from_file_location("aureon_release_channel", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def test_tip_channel_refuses_production_publish() -> None:
    channel = _channel()
    report = channel.evaluate(ROOT)
    assert report["problems"] == []
    assert report["production_publish_allowed"] is False
    assert report["go_live_clear"] is False
    assert report["system_alive"] is False
    assert report["live_trading"] is False
    assert report["orders_placed"] is False
    assert report["published"] is False
    assert report["pin_moved"] is False
    assert report["pin"] == channel.PUBLISHED_PIN
    assert report["pin"] == "34864ff0547d2cff03e707414743a3b0cc8770b5"
    assert report["lineage_tip"] == "bb04503119681adcf832f3c3e9b0cbf09fc7a938"
    assert report["lineage_tip_is_ancestor"] is True
    assert report["orange_badge"] == "HOLD"
    assert report["release_boundary"] == "HOLD"
    assert [row["verified_on_head"] for row in report["receipts"]] == [False, False, False, False, False]
    by_id = {row["id"]: row for row in report["receipts"]}
    assert by_id[1]["present"] is True
    assert by_id[1]["bound_commit"] == "c68a89d2a184d99582bb24310b91e024323a212c"
    assert by_id[1]["release_boundary"] == "HOLD"
    assert by_id[2]["go_live_clear"] is False
    assert by_id[2]["bound_commit"] == "c68a89d2a184d99582bb24310b91e024323a212c"
    assert by_id[3]["go_live_clear"] is False
    assert by_id[4]["decision"] == "HOLD"
    assert by_id[5]["present"] is False
    assert by_id[5]["verified_on_head"] is False
    notes = (ROOT / "docs" / "releases" / "RELEASE_NOTES_tip.md").read_text(encoding="utf-8")
    assert "The system is alive." not in notes
    assert "go_live_clear: true" not in notes
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "release%20boundary-HOLD-orange" in readme
    guard = (ROOT / "mcp" / "aureon_public" / "guard_loader.py").read_text(encoding="utf-8")
    assert f'PINNED_COMMIT = "{channel.PUBLISHED_PIN}"' in guard


def test_publish_command_exits_without_calling_github() -> None:
    source = (ROOT / "packaging" / "release_channel.py").read_text(encoding="utf-8")
    assert "gh release" not in source
    assert "urllib" not in source
    result = subprocess.run(
        [sys.executable, "packaging/release_channel.py", "publish"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 3
    body = json.loads(result.stdout)
    assert body["published"] is False
    assert body["production_publish_allowed"] is False
    assert "Receipts 1-5 are not verified" in body["reason"]


def test_tag_must_be_a_lowercase_prefix_of_head() -> None:
    channel = _channel()
    head = channel.git_head(ROOT)
    assert channel.accept_tag(f"tip-{head[:12]}", head) == f"tip-{head[:12]}"
    for refused in ("V2.2", "v2.2.0", "tip-deadbeef", "tip-GO-LIVE", "tip-bb045031G"):
        try:
            channel.accept_tag(refused, head)
        except ValueError:
            continue
        raise AssertionError(f"accepted {refused}")


def test_tree_archive_checksums_match_bytes(tmp_path: Path) -> None:
    work = tmp_path / "tree"
    work.mkdir()
    (work / "README").write_text("hold\n", encoding="utf-8")
    subprocess.run(["git", "init", "-b", "main"], cwd=work, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "channel@example.com"], cwd=work, check=True)
    subprocess.run(["git", "config", "user.name", "channel"], cwd=work, check=True)
    subprocess.run(["git", "add", "README"], cwd=work, check=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=work, check=True, capture_output=True)
    channel = _channel()
    dest = tmp_path / "out"
    rows = channel.build_tree_archives(work, dest, "Aureon-OS-tip-test")
    assert [row["name"] for row in rows] == [
        "Aureon-OS-tip-test.tar.gz",
        "Aureon-OS-tip-test.zip",
    ]
    for row in rows:
        path = dest / row["name"]
        assert _sha256(path) == row["sha256"]
        assert path.stat().st_size == row["bytes"]
    with tarfile.open(dest / rows[0]["name"], "r:gz") as archive:
        names = archive.getnames()
    assert "Aureon-OS-tip-test/README" in names
    with zipfile.ZipFile(dest / rows[1]["name"]) as archive:
        assert "Aureon-OS-tip-test/README" in archive.namelist()


def test_workflow_opens_a_draft_and_does_not_publish() -> None:
    text = (ROOT / ".github" / "workflows" / "source-archive-release.yml").read_text(encoding="utf-8")
    assert 'tags:\n      - "tip-*"' in text
    assert "gh release create" in text
    assert "--draft" in text
    assert "--prerelease" in text
    assert "--latest" not in text
    assert "gh release edit" not in text
    assert "--draft=false" not in text
    assert "contents: write" in text
    assert "python packaging/release_channel.py publish" in text
    assert 'test "$status" -eq 3' in text
    assert "The system is not claimed alive." in text or "not claimed alive" in text
    create = text.split("gh release create", 1)[1]
    assert "--draft" in create
    assert "--prerelease" in create

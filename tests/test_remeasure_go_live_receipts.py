"""Remeasure runner: a dirty worktree is refused, and the summary stays HOLD."""

from __future__ import annotations

import importlib.util
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "validation" / "remeasure_go_live_receipts.py"
PIN = "0646146c53e59dbcab41363a613d5651c9c9d50f"


def _load():
    spec = importlib.util.spec_from_file_location("remeasure_go_live_receipts", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _git(repo: Path, *args: str) -> None:
    subprocess.check_call(["git", "-C", str(repo), *args])


def _repo(tmp_path: Path) -> Path:
    _git(tmp_path, "init")
    _git(tmp_path, "config", "user.email", "remeasure@example.com")
    _git(tmp_path, "config", "user.name", "remeasure")
    (tmp_path / "a.txt").write_text("a\n", encoding="utf-8")
    _git(tmp_path, "add", "a.txt")
    _git(tmp_path, "commit", "-m", "init")
    return tmp_path


def test_dirty_worktree_is_refused(tmp_path: Path) -> None:
    module = _load()
    repo = _repo(tmp_path)
    (repo / "a.txt").write_text("changed\n", encoding="utf-8")

    dirty = module.refuse_dirty(repo)
    assert dirty is not None
    assert "a.txt" in dirty
    assert module.main(["--root", str(repo)]) == 2


def test_untracked_file_is_a_dirty_worktree(tmp_path: Path) -> None:
    module = _load()
    repo = _repo(tmp_path)
    assert module.refuse_dirty(repo) is None
    (repo / "extra.txt").write_text("x\n", encoding="utf-8")
    assert module.refuse_dirty(repo) is not None


def test_summary_lists_verdicts_and_keeps_go_live_clear_false() -> None:
    module = _load()
    context = {
        "head": "0726a325ac934ed2e8d2d18d5c69c31fbfafc666",
        "published_pin": PIN,
        "tools": {
            "python": "3.12.3",
            "git": "git version 2.43.0",
            "unshare": "unshare from util-linux 2.39.3",
            "openssl": "OpenSSL 3.0.13",
        },
    }
    rows = [
        {"receipt": 1, "name": "containment", "verdict": "pass", "detail": "worktree_dirty False"},
        {"receipt": 2, "name": "release provenance", "verdict": "fail", "detail": "on-disk tip b2b03103"},
        {"receipt": 3, "name": "hnc head anchor", "verdict": "absent", "detail": "note is not on HEAD"},
        {"receipt": 4, "name": "census and call sweep", "verdict": "fail", "detail": "census exit 1"},
    ]
    text = module.format_summary(context, rows)

    assert f"HEAD: {context['head']}" in text
    assert f"published_pin: {PIN}" in text
    assert "published_pin_matches_checkout: true" in text
    assert "go_live_clear: false" in text
    assert "go_live_clear: true" not in text
    assert "python: 3.12.3" in text
    assert "git version 2.43.0" in text
    assert "| 1 | containment | pass |" in text
    assert "| 2 | release provenance | fail |" in text
    assert "| 3 | hnc head anchor | absent |" in text
    assert "| 4 | census and call sweep | fail |" in text
    assert "does not push refs/notes/aureon-hnc-head" in text


def test_note_commands_add_without_force_push_or_timestamp() -> None:
    module = _load()
    lines = module.reattach_command_lines()
    assert lines == [
        " ".join(module.reattach_argv("aureon-hnc-head", "evidence/output/hnc_head_anchor.tsr.b64")),
        " ".join(
            module.reattach_argv("aureon-hnc-head-next", "evidence/output/hnc_head_next.tsr.b64")
        ),
    ]
    assert lines == [
        "git notes --ref=aureon-hnc-head add -F evidence/output/hnc_head_anchor.tsr.b64 HEAD",
        "git notes --ref=aureon-hnc-head-next add -F evidence/output/hnc_head_next.tsr.b64 HEAD",
    ]
    for command in lines:
        assert " -f" not in command
        assert "push" not in command
        assert "timestamp.digicert.com" not in command


def _rev(repo: Path) -> str:
    return subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()


def test_tip_not_on_main_is_refused_before_write(tmp_path: Path) -> None:
    module = _load()
    repo = _repo(tmp_path)
    frozen = _rev(repo)
    missing = "b2b0310362597dc520114de86d8700c0c50758d5"
    missing_reason = module.tip_blocks_write(repo, missing)
    assert missing_reason is not None
    assert "not on main" in missing_reason
    assert "does not exist" not in missing_reason

    (repo / "side.txt").write_text("pre-squash\n", encoding="utf-8")
    _git(repo, "add", "side.txt")
    _git(repo, "commit", "-m", "old branch")
    side = _rev(repo)
    _git(repo, "reset", "--hard", "HEAD~1")
    assert _rev(repo) == frozen
    kind = subprocess.check_output(["git", "-C", str(repo), "cat-file", "-t", side], text=True).strip()
    assert kind == "commit"
    side_reason = module.tip_blocks_write(repo, side)
    assert side_reason is not None
    assert "not on main" in side_reason
    assert "does not exist" not in side_reason
    assert module.commit_on_main(repo, frozen) is True
    assert module.tip_blocks_write(repo, frozen) is None

    script = repo / "scripts" / "validation" / "go_live_stage6.py"
    script.parent.mkdir(parents=True)
    script.write_text(f'TIP = "{side}"\n', encoding="utf-8")
    original = f'{{"go_live_clear": false, "tip": "{side}"}}\n'
    paths = (
        repo / "measured" / "go_live_stage6_provenance.json",
        repo / "measured" / "go_live_stage6_source_census.json",
    )
    for path in paths:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(original, encoding="utf-8")
    before = [path.read_bytes() for path in paths]
    block = module.stage6_write_block(repo)
    assert block is not None
    assert "not on main" in block
    assert "does not exist" not in block
    assert side in block
    assert [path.read_bytes() for path in paths] == before

    script.write_text(f'TIP = "{frozen}"\n', encoding="utf-8")
    assert module.stage6_write_block(repo) is None
    assert [path.read_bytes() for path in paths] == before


def test_recorded_stage6_tip_is_not_on_main() -> None:
    module = _load()
    old_tip = "b2b0310362597dc520114de86d8700c0c50758d5"
    paths = (
        ROOT / "measured" / "go_live_stage6_provenance.json",
        ROOT / "measured" / "go_live_stage6_source_census.json",
    )
    before = [path.read_bytes() for path in paths]
    assert module.read_stage6_tip(ROOT) == old_tip
    block = module.stage6_write_block(ROOT)
    assert block is not None
    assert "is not an ancestor of the frozen head (not on main)" in block
    assert "does not exist" not in block
    assert old_tip in block
    assert [path.read_bytes() for path in paths] == before


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_provenance_text_uses_the_tip_that_was_read(tmp_path: Path) -> None:
    module = _load()
    repo = _repo(tmp_path)
    other = "a" * 40
    script = repo / "scripts" / "validation" / "go_live_stage6.py"
    _write(script, f'TIP = "{other}"\n')
    missing = module.provenance_failure_detail(repo, "b" * 40, None, 1, "boom")
    assert other in missing
    assert "none read" not in missing
    assert "b2b03103" not in missing

    script.write_text("TIP = None\n", encoding="utf-8")
    unread = module.provenance_failure_detail(repo, "b" * 40, None, 1, "")
    assert "tip none read" in unread
    assert "b2b03103" not in unread

    disk = "c" * 40
    script.write_text(f'TIP = "{other}"\n', encoding="utf-8")
    stale = module.provenance_stale_detail(repo, "d" * 40, {"tip": disk})
    assert disk in stale
    assert other not in stale
    assert "b2b03103" not in stale
    empty = module.provenance_stale_detail(repo, "d" * 40, {})
    assert f"tip {other}" in empty
    script.unlink()
    none = module.provenance_stale_detail(repo, "d" * 40, {})
    assert "tip none read" in none


@pytest.mark.parametrize(
    ("verdict", "code"),
    [
        ("pass", 0),
        ("anchored", 0),
        ("attached", 0),
        ("stale", 3),
        ("hold", 3),
        ("absent", 3),
        ("skip", 3),
        ("fail", 1),
        ("refused", 1),
    ],
)
def test_exit_code_for_each_verdict(verdict: str, code: int) -> None:
    module = _load()
    assert module.runner_exit([{"verdict": verdict}]) == code


def test_fail_beats_a_hold_verdict() -> None:
    module = _load()
    assert module.runner_exit([{"verdict": "hold"}, {"verdict": "fail"}]) == 1


def test_failed_containment_leaves_committed_files(tmp_path: Path) -> None:
    module = _load()
    repo = _repo(tmp_path)
    dest_json = repo / "reports" / "measured" / "native_process_containment.json"
    dest_md = repo / "reports" / "measured" / "native_process_containment.md"
    original_json = b'{"git_head_at_measurement":"c68a89d2a184d99582bb24310b91e024323a212c"}\n'
    original_md = b"committed\n"
    dest_json.parent.mkdir(parents=True)
    dest_json.write_bytes(original_json)
    dest_md.write_bytes(original_md)
    fresh_json = tmp_path / "fresh.json"
    fresh_md = tmp_path / "fresh.md"
    fresh_json.write_text('{"verdict":"fail"}\n', encoding="utf-8")
    fresh_md.write_text("new\n", encoding="utf-8")
    assert (
        module.install_containment_receipt(
            repo,
            {"verdict": "fail", "worktree_dirty_at_measurement": False},
            fresh_json,
            fresh_md,
        )
        is False
    )
    assert dest_json.read_bytes() == original_json
    assert dest_md.read_bytes() == original_md
    assert (
        module.install_containment_receipt(
            repo,
            {"verdict": "pass", "worktree_dirty_at_measurement": True},
            fresh_json,
            fresh_md,
        )
        is False
    )
    assert dest_json.read_bytes() == original_json
    assert dest_md.read_bytes() == original_md


def test_refused_receipt_discards_staged_sweep(tmp_path: Path) -> None:
    module = _load()
    repo = _repo(tmp_path)
    target = repo / "measured" / "aureon_public_call_sweep.json"
    original = b'{"kept": true}\n'
    _write(target, original.decode("utf-8"))
    staged = tmp_path / "staged.json"
    staged.write_text('{"new": true}\n', encoding="utf-8")
    done = subprocess.CompletedProcess(args=["bash"], returncode=0, stdout="", stderr="")
    done.out_path = staged
    kept, detail = module._place_sweep(repo, done, keep=False)
    assert kept is False
    assert "was not written" in detail
    assert target.read_bytes() == original
    assert not staged.exists()


def _anchor_repo(tmp_path: Path) -> tuple[Path, str]:
    repo = _repo(tmp_path)
    for name in (
        "evidence/output/hnc_head_anchor.tsr.b64",
        "evidence/output/hnc_head_anchor.json",
        "evidence/output/hnc_head_anchor.id",
        "evidence/output/hnc_head_next.tsr.b64",
        "evidence/output/hnc_head_next.json",
        "evidence/output/hnc_head_next.id",
    ):
        text = "seq1-token\n" if "anchor.tsr" in name else "seq2-token\n" if "next.tsr" in name else "{}\n"
        _write(repo / name, text)
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "record anchors")
    return repo, _rev(repo)


def _note_bytes(repo: Path, name: str, commit: str = "HEAD") -> bytes:
    return subprocess.check_output(
        ["git", "-C", str(repo), "notes", "--ref", name, "show", commit]
    )


def test_matching_notes_on_the_recording_commit_are_anchored(tmp_path: Path) -> None:
    module = _load()
    repo, sha = _anchor_repo(tmp_path)
    for name, rel in module.NOTE_PAIRS:
        subprocess.check_call(
            ["git", "-C", str(repo), "notes", "--ref", name, "add", "-F", str(repo / rel), "HEAD"]
        )
    row = module.measure_anchor(repo, attach=True)
    assert row["verdict"] == "anchored"
    assert row["detail"] == f"anchored on {sha[:12]}"
    assert "git notes" not in str(row["detail"])


def test_reattach_is_offered_only_when_no_anchored_commit_exists(tmp_path: Path) -> None:
    module = _load()
    repo, _sha = _anchor_repo(tmp_path)
    row = module.measure_anchor(repo, attach=False)
    assert row["verdict"] == "absent"
    detail = str(row["detail"])
    assert "anchored on" not in detail
    assert "git notes --ref=aureon-hnc-head add -F" in detail
    assert " add -f " not in detail
    assert module.runner_exit([row]) == 3


def test_attach_note_adds_only_when_none_exists(tmp_path: Path) -> None:
    module = _load()
    repo, _sha = _anchor_repo(tmp_path)
    row = module.measure_anchor(repo, attach=True)
    assert row["verdict"] == "attached"
    for name, rel in module.NOTE_PAIRS:
        assert _note_bytes(repo, name) == (repo / rel).read_bytes()


def test_attach_note_leaves_a_different_note_alone(tmp_path: Path) -> None:
    module = _load()
    repo, _sha = _anchor_repo(tmp_path)
    other = tmp_path / "other.txt"
    other.write_text("different-note\n", encoding="utf-8")
    subprocess.check_call(
        [
            "git",
            "-C",
            str(repo),
            "notes",
            "--ref",
            "aureon-hnc-head",
            "add",
            "-F",
            str(other),
            "HEAD",
        ]
    )
    before = _note_bytes(repo, "aureon-hnc-head")
    row = module.measure_anchor(repo, attach=True)
    assert row["verdict"] == "fail"
    assert "different note already exists" in str(row["detail"])
    assert "left alone" in str(row["detail"])
    assert _note_bytes(repo, "aureon-hnc-head") == before
    with pytest.raises(subprocess.CalledProcessError):
        _note_bytes(repo, "aureon-hnc-head-next")


def test_child_go_live_clear_true_is_refused() -> None:
    module = _load()
    row = module._row(2, "release provenance", "hold", "wrote the file", go_live_clear=True)
    assert row["verdict"] == "refused"
    assert row["go_live_clear"] is False

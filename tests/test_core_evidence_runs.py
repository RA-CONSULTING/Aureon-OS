"""The evidence bundle matches a fresh in-memory rebuild, except commit_sha."""

from __future__ import annotations

import subprocess
from pathlib import Path

from aureon.evidence.hnc_anchor import (
    RECORDED_NOTE_COMMIT,
    TOKEN_REL,
    attach_note,
    load_token_text,
    recording_commit,
    resolve_note_commit,
)
from aureon.evidence.metrics import auroc, fraction_above, rates, upper_threshold, wilson_interval
from aureon.evidence.runner import main

ROOT = Path(__file__).resolve().parents[1]


def test_auroc_ties_and_order() -> None:
    assert auroc([1.0], [1.0]) == 0.5
    assert auroc([1.0, 2.0], [0.0, 0.0]) == 1.0
    assert auroc([0.0], [1.0, 2.0]) == 0.0
    assert auroc([], [1.0]) is None
    interval = wilson_interval(10, 200)
    assert interval is not None
    assert interval[0] < 0.05 < interval[1]


def test_threshold_tail_and_rates() -> None:
    scores = [float(index) for index in range(1, 21)]
    threshold = upper_threshold(scores, 0.05)
    assert fraction_above(scores, threshold) <= 0.05
    counted = rates([True, True, False, False], [True, False, True, False])
    assert counted["tp"] == 1
    assert counted["fn"] == 1
    assert counted["fp"] == 1
    assert counted["tn"] == 1
    assert counted["precision"] == 0.5
    assert counted["recall"] == 0.5
    assert counted["false_alarm_rate"] == 0.5


def test_evidence_bundle_matches_committed_bytes() -> None:
    assert main(["--check"]) == 0


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)


def test_recorded_hnc_note_commit_is_an_ancestor_not_head() -> None:
    sha = recording_commit(ROOT)
    assert sha is not None
    assert sha.startswith(RECORDED_NOTE_COMMIT)
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    assert sha != head
    ancestor = subprocess.run(
        ["git", "merge-base", "--is-ancestor", sha, "HEAD"],
        cwd=ROOT,
        check=False,
    )
    assert ancestor.returncode == 0


def test_hnc_note_is_read_when_head_is_a_descendant_of_the_noted_commit(tmp_path: Path) -> None:
    token_text = (ROOT / TOKEN_REL).read_text(encoding="utf-8")
    target = tmp_path / TOKEN_REL
    target.parent.mkdir(parents=True)
    target.write_text(token_text, encoding="utf-8")
    _git(tmp_path, "init")
    _git(tmp_path, "config", "user.email", "cursoragent@cursor.com")
    _git(tmp_path, "config", "user.name", "Cursor Agent")
    _git(tmp_path, "add", TOKEN_REL)
    _git(tmp_path, "commit", "-m", "record the HNC note")
    attach_note(tmp_path)
    noted = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=tmp_path, text=True).strip()
    (tmp_path / "later.txt").write_text("descendant\n", encoding="utf-8")
    _git(tmp_path, "add", "later.txt")
    _git(tmp_path, "commit", "-m", "descendant of the noted commit")
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=tmp_path, text=True).strip()
    missing = subprocess.run(
        ["git", "notes", "--ref", "aureon-hnc-head", "show", "HEAD"],
        cwd=tmp_path,
        capture_output=True,
        check=False,
    )
    assert missing.returncode != 0
    assert head != noted
    assert resolve_note_commit(tmp_path) == noted
    assert load_token_text(tmp_path, require_note=True) == token_text

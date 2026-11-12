"""Receipt 3: the measured HNC head is a git note, not a working-tree file."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

import pytest

from aureon.evidence.hnc_anchor import (
    EXPECTED_ANCHOR_ID,
    EXPECTED_NEXT_ANCHOR_ID,
    GENESIS,
    NEXT_NOTE_NAME,
    NEXT_NOTE_REF,
    NEXT_RECORD_REL,
    NEXT_TOKEN_REL,
    NOTE_NAME,
    NOTE_REF,
    PIN_FORMULA_SERIES_SHA256,
    PUBLIC_PIN,
    PUBLISHED_PIN,
    RECORD_REL,
    TOKEN_REL,
    AnchorError,
    attach_note,
    canonical_token_text,
    commitment_bytes,
    decode_token_text,
    genesis_id,
    git_blob_sha1,
    load_token_text,
    measurement_commitment,
    next_commitment,
    parse_timestamp_text,
    recording_commit,
    stamp_next,
    validate_chain,
    verify_timestamp,
)
from tests.support.receipt_provenance import last_commit_writing

ROOT = Path(__file__).resolve().parents[1]
RECORD = ROOT / "evidence" / "output" / "hnc_head_anchor.json"
NEXT_RECORD = ROOT / "evidence" / "output" / "hnc_head_next.json"
TOKEN = ROOT / TOKEN_REL
NEXT_TOKEN = ROOT / NEXT_TOKEN_REL
OPEN_SSL_TEXT = """
Status info:
Status: Granted.
Status description: unspecified
Failure info: unspecified

TST info:
Version: 1
Policy OID: 2.16.840.1.114412.7.1
Hash Algorithm: sha256
Message data:
    0000 - aa bb cc dd ee ff 00 11-22 33 44 55 66 77 88 99   ................
    0010 - ab cd ef 01 23 45 67 89-9a bc de f0 12 34 56 78   ....#Eg......4Vx
Serial number: 0xAB
Time stamp: Nov  5 19:32:26 2026 GMT
Accuracy: unspecified
Ordering: no
Nonce: 0x01
TSA: unspecified
Extensions:
"""


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)


def _rev(root: Path) -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()


def _init_repo(root: Path) -> None:
    _git(root, "init")
    _git(root, "config", "user.email", "cursoragent@cursor.com")
    _git(root, "config", "user.name", "Cursor Agent")


def _write_evidence_record(root: Path, record_rel: str, note_ref: str) -> None:
    path = root / record_rel
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"note_ref": note_ref, "schema": "aureon.evidence.hnc-head-anchor.v1"}
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")


def _note_show(root: Path, note_name: str, commit: str) -> bytes:
    return subprocess.check_output(
        ["git", "notes", "--ref", note_name, "show", commit],
        cwd=root,
        stderr=subprocess.DEVNULL,
    )


def test_genesis_id_is_the_named_string() -> None:
    assert genesis_id() == hashlib.sha256(GENESIS.encode("utf-8")).hexdigest()
    assert len(genesis_id()) == 64


def test_timestamp_text_parser_reads_the_external_clock() -> None:
    parsed = parse_timestamp_text(OPEN_SSL_TEXT)
    assert parsed["gen_time"] == "2026-11-05T19:32:26Z"
    assert parsed["serial_hex"] == "ab"
    assert parsed["policy_oid"] == "2.16.840.1.114412.7.1"
    assert parsed["tsa_ordering"] is False
    assert parsed["imprint_sha256"] == "aabbccddeeff00112233445566778899abcdef01234567899abcdef012345678"


def test_chain_rejects_a_rollback() -> None:
    record = json.loads(RECORD.read_text(encoding="utf-8"))
    validate_chain(record)
    rolled = json.loads(RECORD.read_text(encoding="utf-8"))
    rolled["sequence"] = 0
    with pytest.raises(AnchorError):
        validate_chain(rolled)
    rolled["sequence"] = 2
    with pytest.raises(AnchorError):
        validate_chain(rolled)
    later = json.loads(RECORD.read_text(encoding="utf-8"))
    later["sequence"] = 2
    later["prev_anchor_id"] = record["anchor_id"]
    later["anchor_id"] = "b" * 64
    later["external"] = dict(record["external"])
    later["external"]["gen_time"] = "2020-01-01T00:00:00Z"
    with pytest.raises(AnchorError):
        validate_chain(later, record)
    later["external"]["gen_time"] = "2099-01-01T00:00:00Z"
    validate_chain(later, record)


def test_public_pin_and_hold_are_unchanged() -> None:
    record = json.loads(RECORD.read_text(encoding="utf-8"))
    guard = (ROOT / "mcp/aureon_public/guard_loader.py").read_text(encoding="utf-8")
    space = (ROOT / "huggingface/hnc-field/guard.py").read_text(encoding="utf-8")
    assert PUBLIC_PIN == "34864ff0547d2cff03e707414743a3b0cc8770b5"
    assert PUBLISHED_PIN == "bb04503119681adcf832f3c3e9b0cbf09fc7a938"
    assert 'PINNED_COMMIT = "0646146c53e59dbcab41363a613d5651c9c9d50f"' in guard  # live published pin; PUBLISHED_PIN on this head is historical
    assert 'COMMIT = "0646146c53e59dbcab41363a613d5651c9c9d50f"' in space  # live published pin; PUBLISHED_PIN on this head is historical
    assert record["public_require_pin"] == PUBLIC_PIN
    assert record["measurement"]["public_require_pin"] == PUBLIC_PIN
    assert record["published_require_pin"] == PUBLISHED_PIN
    assert record["recorded_pin_status"] == "historical"
    assert record["hnc_identity_changed"] is False
    assert record["measurement"]["formula_series_sha256"] == PIN_FORMULA_SERIES_SHA256
    assert record["measurement"]["hnc_identity_changed"] is False
    assert record["system_alive"] is False
    assert record["live_trading"] is False
    assert record["orders_placed"] is False
    assert record["go_live"] == "HOLD"
    assert record["go_live_clear"] is False
    assert record["market_series"] is False
    assert record["tag"] == "measured"
    assert record["anchor_id"] == EXPECTED_ANCHOR_ID
    assert (ROOT / "evidence/output/hnc_head_anchor.id").read_text(encoding="utf-8") == record["anchor_id"] + "\n"
    assert record["note_ref"] == NOTE_REF


def test_committed_token_verifies_over_the_measured_commitment() -> None:
    record = json.loads(RECORD.read_text(encoding="utf-8"))
    token = decode_token_text(TOKEN.read_text(encoding="utf-8"))
    assert hashlib.sha256(token).hexdigest() == record["anchor_id"]
    parsed = verify_timestamp(token, commitment_bytes(record["measurement"]))
    assert parsed["gen_time"] == record["external"]["gen_time"]
    assert parsed["serial_hex"] == record["external"]["serial_hex"]
    assert parsed["imprint_sha256"] == record["measurement_sha256"]
    mutated = dict(record["measurement"])
    mutated["formula_series_sha256"] = "0" * 64
    with pytest.raises(AnchorError):
        verify_timestamp(token, commitment_bytes(mutated))


def test_working_tree_edit_does_not_move_the_note(tmp_path: Path) -> None:
    token_text = TOKEN.read_text(encoding="utf-8")
    target = tmp_path / TOKEN_REL
    target.parent.mkdir(parents=True)
    target.write_text(token_text, encoding="utf-8")
    _write_evidence_record(tmp_path, RECORD_REL, NOTE_REF)
    _init_repo(tmp_path)
    _git(tmp_path, "add", TOKEN_REL, RECORD_REL)
    _git(tmp_path, "commit", "-m", "anchor token")
    attach_note(tmp_path)
    target.write_text(canonical_token_text(b"\x30\x00"), encoding="utf-8")
    assert load_token_text(tmp_path, require_note=True) == token_text
    note = subprocess.check_output(
        ["git", "notes", "--ref", "aureon-hnc-head", "show", "HEAD"],
        cwd=tmp_path,
    )
    assert note.decode("ascii") == token_text
    assert git_blob_sha1(token_text.encode("ascii")) == subprocess.check_output(
        ["git", "hash-object", "--stdin"],
        input=token_text.encode("ascii"),
        cwd=tmp_path,
    ).decode("ascii").strip()


def test_commitment_from_the_recorded_summary_matches_the_token() -> None:
    summary = json.loads((ROOT / "evidence/output/hnc.json").read_text(encoding="utf-8"))
    commitment = measurement_commitment(summary)
    record = json.loads(RECORD.read_text(encoding="utf-8"))
    assert commitment == record["measurement"]
    assert commitment["market_series"] is False
    assert commitment["system_alive"] is False


def test_next_head_is_sequence_two_with_a_later_verified_clock() -> None:
    record = json.loads(RECORD.read_text(encoding="utf-8"))
    nxt = json.loads(NEXT_RECORD.read_text(encoding="utf-8"))
    summary = json.loads((ROOT / "evidence/output/hnc.json").read_text(encoding="utf-8"))
    validate_chain(nxt, record)
    assert next_commitment(summary, record) == nxt["measurement"]
    assert nxt["sequence"] == 2
    assert nxt["prev_anchor_id"] == record["anchor_id"] == EXPECTED_ANCHOR_ID
    assert nxt["previous_gen_time"] == record["external"]["gen_time"] == "2026-11-05T19:40:18Z"
    assert nxt["external"]["gen_time"] == "2026-11-05T20:44:49Z"
    assert nxt["external"]["tsa_ordering"] is False
    assert nxt["external"]["provider_contacted_by_check"] is False
    assert nxt["anchor_id"] == EXPECTED_NEXT_ANCHOR_ID
    assert nxt["external_head_anchor_attested"] is False
    assert nxt["measurement"]["external_head_anchor_attested"] is False
    assert nxt["system_alive"] is False
    assert nxt["live_trading"] is False
    assert nxt["orders_placed"] is False
    assert nxt["go_live"] == "HOLD"
    assert nxt["go_live_clear"] is False
    assert nxt["market_series"] is False
    assert nxt["public_require_pin"] == PUBLIC_PIN
    assert nxt["measurement"]["public_require_pin"] == PUBLIC_PIN
    assert nxt["published_require_pin"] == PUBLISHED_PIN
    assert nxt["recorded_pin_status"] == "historical"
    assert nxt["hnc_identity_changed"] is False
    assert nxt["measurement"]["formula_series_sha256"] == PIN_FORMULA_SERIES_SHA256
    assert (ROOT / "evidence/output/hnc_head_next.id").read_text(encoding="utf-8") == nxt["anchor_id"] + "\n"
    token = decode_token_text(NEXT_TOKEN.read_text(encoding="utf-8"))
    assert hashlib.sha256(token).hexdigest() == nxt["anchor_id"]
    parsed = verify_timestamp(token, commitment_bytes(nxt["measurement"]))
    assert parsed["gen_time"] == nxt["external"]["gen_time"]
    assert parsed["serial_hex"] == nxt["external"]["serial_hex"]
    assert parsed["imprint_sha256"] == nxt["measurement_sha256"]
    runbook = (ROOT / "docs/runbooks/GO_LIVE_HARDENING.md").read_text(encoding="utf-8")
    assert "Receipts 2, 3, 4, and 5 remain HOLD" in runbook
    assert "external_head_anchor_attested" in runbook
    assert "The system is not reported" in runbook
    assert "go_live_clear" in runbook
    assert PUBLIC_PIN in runbook
    assert PUBLISHED_PIN in runbook
    assert "receipt 5" in runbook
    follow = (ROOT / "docs/runbooks/GO_LIVE_HNC_HEAD_NEXT.md").read_text(encoding="utf-8")
    assert "historical" in follow
    assert "Sequence 2" in follow
    assert PUBLIC_PIN in follow
    assert PUBLISHED_PIN in follow
    assert "go_live_clear" in follow
    assert "not rewritten" in follow
    guard = (ROOT / "mcp/aureon_public/guard_loader.py").read_text(encoding="utf-8")
    assert 'PINNED_COMMIT = "0646146c53e59dbcab41363a613d5651c9c9d50f"' in guard  # live published pin; PUBLISHED_PIN on this head is historical


def test_recorded_next_head_is_not_stamped_again(tmp_path: Path) -> None:
    with pytest.raises(AnchorError, match="already recorded"):
        stamp_next(tmp_path, {})


def test_working_tree_edit_does_not_move_the_next_note(tmp_path: Path) -> None:
    token_text = NEXT_TOKEN.read_text(encoding="utf-8")
    target = tmp_path / NEXT_TOKEN_REL
    target.parent.mkdir(parents=True)
    target.write_text(token_text, encoding="utf-8")
    _write_evidence_record(tmp_path, NEXT_RECORD_REL, NEXT_NOTE_REF)
    _init_repo(tmp_path)
    _git(tmp_path, "add", NEXT_TOKEN_REL, NEXT_RECORD_REL)
    _git(tmp_path, "commit", "-m", "next anchor token")
    attach_note(tmp_path, note_name=NEXT_NOTE_NAME, token_rel=NEXT_TOKEN_REL)
    target.write_text(canonical_token_text(b"\x30\x00"), encoding="utf-8")
    loaded = load_token_text(
        tmp_path,
        require_note=True,
        note_name=NEXT_NOTE_NAME,
        note_ref=NEXT_NOTE_REF,
        token_rel=NEXT_TOKEN_REL,
        record_rel=NEXT_RECORD_REL,
    )
    assert loaded == token_text


def _commit_recorded_token(
    root: Path,
    *,
    token_rel: str,
    record_rel: str,
    note_ref: str,
    token_text: str,
    message: str,
) -> str:
    target = root / token_rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(token_text, encoding="utf-8")
    _write_evidence_record(root, record_rel, note_ref)
    _git(root, "add", token_rel, record_rel)
    _git(root, "commit", "-m", message)
    return _rev(root)


def _later_commit(root: Path) -> str:
    marker = root / "later.txt"
    previous = marker.read_text(encoding="utf-8") if marker.is_file() else ""
    marker.write_text(previous + "later\n", encoding="utf-8")
    _git(root, "add", "later.txt")
    _git(root, "commit", "-m", "later head")
    return _rev(root)


def test_check_reads_each_note_from_its_recording_commit_when_head_is_later(tmp_path: Path) -> None:
    sequence_one = TOKEN.read_text(encoding="utf-8")
    sequence_two = NEXT_TOKEN.read_text(encoding="utf-8")
    _init_repo(tmp_path)
    first = _commit_recorded_token(
        tmp_path,
        token_rel=TOKEN_REL,
        record_rel=RECORD_REL,
        note_ref=NOTE_REF,
        token_text=sequence_one,
        message="record sequence 1",
    )
    subprocess.check_call(
        ["git", "notes", "--ref", NOTE_NAME, "add", "-F", str(tmp_path / TOKEN_REL), first],
        cwd=tmp_path,
    )
    second = _commit_recorded_token(
        tmp_path,
        token_rel=NEXT_TOKEN_REL,
        record_rel=NEXT_RECORD_REL,
        note_ref=NEXT_NOTE_REF,
        token_text=sequence_two,
        message="record sequence 2",
    )
    subprocess.check_call(
        ["git", "notes", "--ref", NEXT_NOTE_NAME, "add", "-F", str(tmp_path / NEXT_TOKEN_REL), second],
        cwd=tmp_path,
    )
    head = _later_commit(tmp_path)
    assert recording_commit(tmp_path, RECORD_REL) == first
    assert recording_commit(tmp_path, NEXT_RECORD_REL) == second
    assert first != second != head
    with pytest.raises(subprocess.CalledProcessError):
        _note_show(tmp_path, NOTE_NAME, "HEAD")
    with pytest.raises(subprocess.CalledProcessError):
        _note_show(tmp_path, NEXT_NOTE_NAME, "HEAD")
    assert load_token_text(tmp_path, require_note=True) == sequence_one
    assert (
        load_token_text(
            tmp_path,
            require_note=True,
            note_name=NEXT_NOTE_NAME,
            note_ref=NEXT_NOTE_REF,
            token_rel=NEXT_TOKEN_REL,
            record_rel=NEXT_RECORD_REL,
        )
        == sequence_two
    )


def test_missing_note_on_the_recording_commit_does_not_fall_back_to_head(tmp_path: Path) -> None:
    token_text = TOKEN.read_text(encoding="utf-8")
    _init_repo(tmp_path)
    recording = _commit_recorded_token(
        tmp_path,
        token_rel=TOKEN_REL,
        record_rel=RECORD_REL,
        note_ref=NOTE_REF,
        token_text=token_text,
        message="record sequence 1",
    )
    head = _later_commit(tmp_path)
    subprocess.check_call(
        ["git", "notes", "--ref", NOTE_NAME, "add", "-F", str(tmp_path / TOKEN_REL), "HEAD"],
        cwd=tmp_path,
    )
    assert _note_show(tmp_path, NOTE_NAME, head) == token_text.encode("ascii")
    with pytest.raises(subprocess.CalledProcessError):
        _note_show(tmp_path, NOTE_NAME, recording)
    with pytest.raises(AnchorError, match="does not read the note from HEAD"):
        load_token_text(tmp_path, require_note=True)


def test_different_note_bytes_on_the_recording_commit_do_not_fall_back_to_head(tmp_path: Path) -> None:
    token_text = TOKEN.read_text(encoding="utf-8")
    other = canonical_token_text(b"\x30\x03")
    assert other != token_text
    _init_repo(tmp_path)
    recording = _commit_recorded_token(
        tmp_path,
        token_rel=TOKEN_REL,
        record_rel=RECORD_REL,
        note_ref=NOTE_REF,
        token_text=token_text,
        message="record sequence 1",
    )
    other_path = tmp_path / "other-note.txt"
    other_path.write_text(other, encoding="utf-8")
    subprocess.check_call(
        ["git", "notes", "--ref", NOTE_NAME, "add", "-F", str(other_path), recording],
        cwd=tmp_path,
    )
    _later_commit(tmp_path)
    subprocess.check_call(
        ["git", "notes", "--ref", NOTE_NAME, "add", "-F", str(tmp_path / TOKEN_REL), "HEAD"],
        cwd=tmp_path,
    )
    assert _note_show(tmp_path, NOTE_NAME, "HEAD") == token_text.encode("ascii")
    assert _note_show(tmp_path, NOTE_NAME, recording) == other.encode("ascii")
    with pytest.raises(AnchorError, match="does not read the note from HEAD"):
        load_token_text(tmp_path, require_note=True)


def test_this_history_names_both_recording_commits() -> None:
    head = _rev(ROOT)
    # last_commit_writing skips on a shallow clone, or when the commit is
    # only a graft or shallow boundary.
    sequence_one = last_commit_writing(RECORD_REL)
    sequence_two = last_commit_writing(NEXT_RECORD_REL)
    assert sequence_one == "9b666838f88f80a3eab5be11856d9b0a12c886e2"
    assert sequence_two == "9b666838f88f80a3eab5be11856d9b0a12c886e2"
    assert sequence_one != head
    assert sequence_two != head
    follow = (ROOT / "docs/runbooks/GO_LIVE_HNC_HEAD_NEXT.md").read_text(encoding="utf-8")
    assert "does not read either note from HEAD" in follow
    assert "9b666838" in follow
    remeasure = (ROOT / "docs/runbooks/GO_LIVE_RECEIPTS_REMEASURE.md").read_text(encoding="utf-8")
    assert "does not read the note from HEAD" in remeasure
    assert "on HEAD" not in remeasure.split("## Receipt 3", 1)[0].split("What each receipt runs", 1)[1]

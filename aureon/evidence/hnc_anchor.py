"""External monotonic head for the measured HNC evidence.

The formula path is the fixed-seed ``HarmonicRealityField`` run already in
``aureon.evidence.hnc``. This module does not fetch a market series and does
not place an order.

The head is an RFC 3161 timestamp over that measured commitment. ``make
evidence`` reads sequence 1 from the git note ``refs/notes/aureon-hnc-head``
and a later head from ``refs/notes/aureon-hnc-head-next``. It requires the
committed bytes to match. A working-tree edit does not move either note or
either committed blob. The timestamp records historical pin
``34864ff0547d2cff03e707414743a3b0cc8770b5``. The published require-pin is
``bb04503119681adcf832f3c3e9b0cbf09fc7a938``. This module does not move it.
A series-hash change is refused rather than recorded as a new HNC identity.

A later head is sequence 2 only: ``prev_anchor_id`` is the sequence 1 anchor
id, and the verified ``gen_time`` is strictly later. The ledger flag
``external_head_anchor_attested`` stays false. ``go_live_clear`` stays false.
The record does not say the system is alive.
"""

from __future__ import annotations

import base64
import hashlib
import json
import re
import subprocess
import tempfile
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from aureon.evidence.serialize import dump

# Pin inside the receipt 3 RFC 3161 commitment. Historical. Not the published pin.
PUBLIC_PIN = "34864ff0547d2cff03e707414743a3b0cc8770b5"
PUBLISHED_PIN = "bb04503119681adcf832f3c3e9b0cbf09fc7a938"
# Series sha256 of the formula path in evidence/output/hnc.json at PUBLIC_PIN.


def _identity_note(subject: str) -> str:
    return (
        "The measured formula series sha256 matches the series recorded for historical "
        f"public pin {PUBLIC_PIN}. The published require-pin is {PUBLISHED_PIN}. "
        f"{subject} does not publish a new HNC identity and does not move the published require-pin."
    )


def _refuse_new_identity() -> str:
    return (
        "Measured formula series sha256 differs from the series recorded for historical pin "
        f"{PUBLIC_PIN} ({PIN_FORMULA_SERIES_SHA256}). "
        f"The published require-pin stays {PUBLISHED_PIN}. "
        "Refusing to record a new HNC identity."
    )
PIN_FORMULA_SERIES_SHA256 = "0a69c024c3a7b849857314ef710f11439eb13a30cd7c45f05429becea574f5c2"
# SHA-256 of the RFC 3161 token bytes recorded for this head. Not a new HNC identity.
EXPECTED_ANCHOR_ID = "548596463d7b4dddeeba274562b212960f879baf475ee135c7d2fd3468f58e11"

NOTE_NAME = "aureon-hnc-head"
NOTE_REF = "refs/notes/aureon-hnc-head"
TSA_URL = "http://timestamp.digicert.com"
TOKEN_REL = "evidence/output/hnc_head_anchor.tsr.b64"
RECORD_REL = "evidence/output/hnc_head_anchor.json"
ID_REL = "evidence/output/hnc_head_anchor.id"
NEXT_NOTE_NAME = "aureon-hnc-head-next"
NEXT_NOTE_REF = "refs/notes/aureon-hnc-head-next"
NEXT_TOKEN_REL = "evidence/output/hnc_head_next.tsr.b64"
NEXT_RECORD_REL = "evidence/output/hnc_head_next.json"
NEXT_ID_REL = "evidence/output/hnc_head_next.id"
# SHA-256 of the sequence-2 RFC 3161 token recorded for this head.
EXPECTED_NEXT_ANCHOR_ID = "e02c59279b46e912a08b1add73f44b82970f535676d0011a3bcb769dfba68784"
GENESIS = "aureon.evidence.hnc-head-anchor.genesis.v1"
SCHEMA = "aureon.evidence.hnc-head-anchor.v1"
COMMITMENT_SCHEMA = "aureon.evidence.hnc-measurement-commitment.v1"

_STAMP_RE = re.compile(
    r"Time stamp: ([A-Z][a-z]{2})\s+(\d{1,2}) (\d{2}:\d{2}:\d{2}) (\d{4}) GMT"
)
_SERIAL_RE = re.compile(r"Serial number: 0x([0-9A-Fa-f]+)")
_POLICY_RE = re.compile(r"Policy OID: (\d+(?:\.\d+)+)")
_ORDER_RE = re.compile(r"Ordering: (yes|no)")
_HEX_LINE_RE = re.compile(
    r"^\s+[0-9a-fA-F]{4} - ([0-9a-fA-F]{2}(?:[ -][0-9a-fA-F]{2})*)"
)
_MONTHS = {
    "Jan": 1,
    "Feb": 2,
    "Mar": 3,
    "Apr": 4,
    "May": 5,
    "Jun": 6,
    "Jul": 7,
    "Aug": 8,
    "Sep": 9,
    "Oct": 10,
    "Nov": 11,
    "Dec": 12,
}


class AnchorError(RuntimeError):
    """The head anchor does not verify."""


def genesis_id() -> str:
    return hashlib.sha256(GENESIS.encode("utf-8")).hexdigest()


def git_blob_sha1(payload: bytes) -> str:
    prefix = f"blob {len(payload)}\0".encode("ascii")
    return hashlib.sha1(prefix + payload).hexdigest()


def canonical_token_text(token: bytes) -> str:
    return base64.b64encode(token).decode("ascii") + "\n"


def decode_token_text(text: str) -> bytes:
    if text != text.strip() + "\n":
        raise AnchorError("token text is not a single canonical base64 line")
    try:
        token = base64.b64decode(text.strip(), validate=True)
    except ValueError as exc:
        raise AnchorError("token text is not base64") from exc
    if canonical_token_text(token) != text:
        raise AnchorError("token text is not canonical base64")
    return token


def measurement_commitment(hnc_summary: dict[str, Any]) -> dict[str, Any]:
    """Bytes the timestamp covers. Measured fields only. No clock, no commit."""

    formula = hnc_summary["formula"]
    multiverse = hnc_summary["multiverse"]
    formula_sha = str(formula["sha256"])
    return {
        "schema": COMMITMENT_SCHEMA,
        "tag": "measured",
        "public_require_pin": PUBLIC_PIN,
        "hnc_identity_changed": formula_sha != PIN_FORMULA_SERIES_SHA256,
        "formula_series_sha256": formula_sha,
        "formula_seed": int(formula["series_reference_seed"]),
        "formula_steps": int(formula["steps"]),
        "formula_source": str(formula["source"]),
        "multiverse_series_sha256": str(multiverse["sha256"]),
        "sequence": 1,
        "prev_anchor_id": genesis_id(),
        "genesis": GENESIS,
        "live_trading": False,
        "orders_placed": False,
        "system_alive": False,
        "go_live": "HOLD",
        "go_live_clear": False,
        "market_series": False,
    }


def commitment_bytes(commitment: dict[str, Any]) -> bytes:
    return dump(commitment).encode("utf-8")


def _ca_file() -> str:
    for path in (
        "/etc/ssl/certs/ca-certificates.crt",
        "/etc/pki/tls/certs/ca-bundle.crt",
        "/etc/ssl/cert.pem",
    ):
        if Path(path).is_file():
            return path
    raise AnchorError("system CA bundle was not found; the timestamp token is not verified")


def _openssl_env() -> dict[str, str]:
    import os

    env = os.environ.copy()
    env["LC_ALL"] = "C"
    return env


def request_timestamp(data: bytes) -> bytes:
    """Ask the timestamp authority for a token over ``data``. Not used by check."""

    with tempfile.TemporaryDirectory() as tmp:
        raw = Path(tmp) / "data.bin"
        query = Path(tmp) / "query.tsq"
        raw.write_bytes(data)
        proc = subprocess.run(
            ["openssl", "ts", "-query", "-data", str(raw), "-sha256", "-cert", "-out", str(query)],
            capture_output=True,
            env=_openssl_env(),
        )
        if proc.returncode != 0:
            detail = proc.stderr.decode("utf-8", "replace").strip()
            raise AnchorError(f"openssl ts -query failed: {detail}")
        query_bytes = query.read_bytes()
    request = urllib.request.Request(
        TSA_URL,
        data=query_bytes,
        headers={"Content-Type": "application/timestamp-query"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            body = response.read()
    except OSError as exc:
        raise AnchorError(f"timestamp authority request failed: {exc}") from exc
    if not body.startswith(b"\x30"):
        raise AnchorError("timestamp authority did not return a DER TimeStampResp")
    return body


def parse_timestamp_text(text: str) -> dict[str, Any]:
    if "Status: Granted." not in text:
        raise AnchorError("timestamp token was not granted")
    stamp = _STAMP_RE.search(text)
    serial = _SERIAL_RE.search(text)
    policy = _POLICY_RE.search(text)
    ordering = _ORDER_RE.search(text)
    if stamp is None or serial is None or policy is None or ordering is None:
        raise AnchorError("timestamp token text is missing genTime, serial, policy, or ordering")
    month = _MONTHS.get(stamp.group(1))
    if month is None:
        raise AnchorError("timestamp month is not an English abbreviation")
    day = int(stamp.group(2))
    clock = stamp.group(3)
    year = int(stamp.group(4))
    gen = datetime.strptime(f"{year:04d}-{month:02d}-{day:02d}T{clock}", "%Y-%m-%dT%H:%M:%S")
    gen = gen.replace(tzinfo=UTC)
    imprint = _imprint_hex(text)
    return {
        "gen_time": gen.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "serial_hex": serial.group(1).lower(),
        "policy_oid": policy.group(1),
        "tsa_ordering": ordering.group(1) == "yes",
        "imprint_sha256": imprint,
    }


def _imprint_hex(text: str) -> str:
    chunks: list[str] = []
    capture = False
    for line in text.splitlines():
        if line.startswith("Message data:"):
            capture = True
            continue
        if not capture:
            continue
        match = _HEX_LINE_RE.match(line)
        if match is None:
            break
        chunks.append(match.group(1).replace("-", "").replace(" ", ""))
    imprint = "".join(chunks).lower()
    if len(imprint) != 64:
        raise AnchorError("timestamp imprint is not a sha256 hex string")
    return imprint


def verify_timestamp(token: bytes, data: bytes) -> dict[str, Any]:
    """Verify ``token`` against ``data`` with the system trust store. No network."""

    with tempfile.TemporaryDirectory() as tmp:
        folder = Path(tmp)
        token_path = folder / "token.tsr"
        data_path = folder / "data.bin"
        token_path.write_bytes(token)
        data_path.write_bytes(data)
        verified = subprocess.run(
            [
                "openssl",
                "ts",
                "-verify",
                "-in",
                str(token_path),
                "-data",
                str(data_path),
                "-CAfile",
                _ca_file(),
            ],
            capture_output=True,
            env=_openssl_env(),
        )
        if verified.returncode != 0:
            detail = verified.stderr.decode("utf-8", "replace").strip()
            raise AnchorError(f"timestamp verification failed: {detail}")
        printed = subprocess.run(
            ["openssl", "ts", "-reply", "-in", str(token_path), "-text"],
            capture_output=True,
            env=_openssl_env(),
        )
    if printed.returncode != 0:
        detail = printed.stderr.decode("utf-8", "replace").strip()
        raise AnchorError(f"openssl ts -reply failed: {detail}")
    parsed = parse_timestamp_text(printed.stdout.decode("utf-8"))
    digest = hashlib.sha256(data).hexdigest()
    if parsed["imprint_sha256"] != digest:
        raise AnchorError("timestamp imprint does not match the measured commitment")
    parsed["verification"] = "openssl ts -verify"
    parsed["ca"] = "system trust store"
    return parsed


def _git_bytes(root: Path, args: list[str]) -> bytes | None:
    try:
        return subprocess.check_output(args, cwd=root, stderr=subprocess.DEVNULL)
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def _git_ok(root: Path, args: list[str]) -> bool:
    try:
        done = subprocess.run(args, cwd=root, capture_output=True)
    except (OSError, subprocess.TimeoutExpired):
        return False
    return done.returncode == 0


def fetch_notes(root: Path) -> bool:
    """Fetch ``refs/notes/*`` from origin. A failed fetch is not itself an error.

    Notes that are already in the clone stay usable when origin cannot be
    reached. ``--check`` still refuses to pass when the notes ref is absent.
    """

    import os

    env = os.environ.copy()
    env["GIT_TERMINAL_PROMPT"] = "0"
    try:
        done = subprocess.run(
            ["git", "fetch", "origin", "refs/notes/*:refs/notes/*"],
            cwd=root,
            capture_output=True,
            env=env,
            timeout=120,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return done.returncode == 0


def read_note(root: Path, note_name: str = NOTE_NAME, commit: str = "HEAD") -> bytes | None:
    return _git_bytes(root, ["git", "notes", "--ref", note_name, "show", commit])


def read_head_blob(root: Path, token_rel: str = TOKEN_REL) -> bytes | None:
    return _git_bytes(root, ["git", "show", f"HEAD:{token_rel}"])


def _notes_ref_present(root: Path, note_ref: str) -> bool:
    return _git_ok(root, ["git", "show-ref", "--verify", "--quiet", note_ref])


def _list_note_attachments(root: Path, note_name: str) -> list[tuple[str, str]]:
    """Return ``(note blob sha, commit sha)`` rows from ``git notes list``."""

    raw = _git_bytes(root, ["git", "notes", "--ref", note_name, "list"])
    if not raw:
        return []
    pairs: list[tuple[str, str]] = []
    for line in raw.decode("utf-8", "replace").splitlines():
        parts = line.split()
        if len(parts) < 2:
            continue
        blob, commit = parts[0].lower(), parts[1].lower()
        if re.fullmatch(r"[0-9a-f]{40}", blob) and re.fullmatch(r"[0-9a-f]{40}", commit):
            pairs.append((blob, commit))
    return pairs


def _load_record(root: Path, record_rel: str) -> dict[str, Any] | None:
    path = root / record_rel
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    return payload


def _recorded_note_commit(root: Path, record_rel: str) -> str | None:
    payload = _load_record(root, record_rel)
    if payload is None:
        return None
    for key in ("note_commit", "note_commit_sha", "attached_commit"):
        value = payload.get(key)
        if isinstance(value, str) and re.fullmatch(r"[0-9a-fA-F]{40}", value):
            return value.lower()
    return None


def _recorded_note_blob(root: Path, record_rel: str, token_rel: str) -> str | None:
    payload = _load_record(root, record_rel)
    if payload is not None:
        blob = payload.get("note_git_blob")
        if isinstance(blob, str) and re.fullmatch(r"[0-9a-fA-F]{40}", blob):
            return blob.lower()
    head = read_head_blob(root, token_rel)
    if head is not None:
        return git_blob_sha1(head)
    return None


def _object_exists(root: Path, sha: str) -> bool:
    return _git_ok(root, ["git", "cat-file", "-e", f"{sha}^{{commit}}"])


def _is_ancestor(root: Path, sha: str) -> bool:
    return _git_ok(root, ["git", "merge-base", "--is-ancestor", sha, "HEAD"])


def _recording_commit(root: Path, token_rel: str) -> str | None:
    """Commit that added the committed token, when that commit is on this history."""

    raw = _git_bytes(root, ["git", "log", "--diff-filter=A", "--format=%H", "--", token_rel])
    if not raw:
        return None
    for line in raw.decode("utf-8", "replace").splitlines():
        sha = line.strip().lower()
        if re.fullmatch(r"[0-9a-f]{40}", sha) and _is_ancestor(root, sha):
            return sha
    return None


def _newest_commit(root: Path, commits: list[str]) -> str:
    wanted = set(commits)
    raw = _git_bytes(root, ["git", "rev-list", "HEAD"])
    if raw:
        for line in raw.decode("utf-8", "replace").splitlines():
            sha = line.strip().lower()
            if sha in wanted:
                return sha
    return commits[0]


def _not_fetched(note_ref: str) -> AnchorError:
    return AnchorError(
        f"{note_ref} was not fetched. "
        "The check does not treat the committed token as the git note. "
        "Fetch notes with: git fetch origin 'refs/notes/*:refs/notes/*'"
    )


def _resolve_note_commit(
    root: Path,
    note_name: str,
    note_ref: str,
    token_rel: str,
    record_rel: str,
) -> str:
    """Commit whose note is the recorded token. HEAD is not assumed.

    ``git notes list`` names every commit the note is attached to. A
    ``note_commit`` field on the evidence record wins when it is one of
    those commits. Otherwise the commit that added the token file is used
    when the note is attached there, else the newest ancestor of HEAD whose
    note blob matches the recorded content hash.
    """

    if not _notes_ref_present(root, note_ref):
        raise _not_fetched(note_ref)
    pairs = _list_note_attachments(root, note_name)
    if not pairs:
        raise AnchorError(
            f"git note {note_ref} is missing. "
            "`git notes list` has no commit for it."
        )
    expected = _recorded_note_blob(root, record_rel, token_rel)
    if expected is None:
        raise AnchorError(
            f"git note {note_ref} cannot be checked. "
            f"{record_rel} has no note_git_blob and {token_rel} is not committed."
        )
    matches = [commit for blob, commit in pairs if blob == expected]
    if not matches:
        detail = ", ".join(f"{commit[:12]}={blob}" for blob, commit in pairs)
        raise AnchorError(
            f"git note {note_ref} content hash does not match recorded note_git_blob {expected}. "
            f"git notes list has {detail}"
        )
    recorded = _recorded_note_commit(root, record_rel)
    if recorded is not None and recorded in matches:
        return recorded
    recording = _recording_commit(root, token_rel)
    if recording is not None and recording in matches:
        return recording
    ancestors = [commit for commit in matches if _object_exists(root, commit) and _is_ancestor(root, commit)]
    if ancestors:
        return _newest_commit(root, ancestors)
    existing = [commit for commit in matches if _object_exists(root, commit)]
    if existing:
        return _newest_commit(root, existing)
    return matches[0]


def load_token_text(
    root: Path,
    *,
    require_note: bool,
    note_name: str = NOTE_NAME,
    note_ref: str = NOTE_REF,
    token_rel: str = TOKEN_REL,
    record_rel: str = RECORD_REL,
) -> str:
    """Return the canonical token text from the note or the committed blob.

    ``--check`` reads the note from the commit it is attached to. The working
    tree is used only when neither git object exists and a note is not
    required, so a local edit cannot replace a note that is already attached.
    """

    head = read_head_blob(root, token_rel)
    if require_note:
        commit = _resolve_note_commit(root, note_name, note_ref, token_rel, record_rel)
        note = read_note(root, note_name, commit)
        if note is None:
            raise AnchorError(
                f"git note {note_ref} is missing on {commit}. "
                "`git notes list` named that commit but the note could not be read."
            )
        actual = git_blob_sha1(note)
        expected = _recorded_note_blob(root, record_rel, token_rel)
        if expected is not None and actual != expected:
            raise AnchorError(
                f"git note {note_ref} content hash {actual} does not match "
                f"recorded note_git_blob {expected}"
            )
        if head is not None and note != head:
            raise AnchorError(
                f"git note {note_ref} content hash {actual} does not match "
                f"recorded note_git_blob {git_blob_sha1(head)}"
            )
        raw = note
    else:
        note = read_note(root, note_name)
        if note is not None and head is not None and note != head:
            raise AnchorError("git note and committed HNC head token differ")
        if note is not None:
            raw = note
        elif head is not None:
            raw = head
        else:
            path = root / token_rel
            if not path.is_file():
                raise AnchorError(
                    "HNC head token is not in git. "
                    "Stamp it, commit the bytes, and attach the git note. "
                    "make evidence does not request a new timestamp."
                )
            raw = path.read_bytes()
    try:
        text = raw.decode("ascii")
    except UnicodeError as exc:
        raise AnchorError("HNC head token text is not ASCII") from exc
    decode_token_text(text)
    return text


def verify_required_notes(root: Path) -> None:
    """Fetch notes, then read each HNC note from the commit it is attached to."""

    fetch_notes(root)
    load_token_text(root, require_note=True)
    load_token_text(
        root,
        require_note=True,
        note_name=NEXT_NOTE_NAME,
        note_ref=NEXT_NOTE_REF,
        token_rel=NEXT_TOKEN_REL,
        record_rel=NEXT_RECORD_REL,
    )


def parse_gen_time(value: str) -> datetime:
    if not value.endswith("Z"):
        raise AnchorError("gen_time is not UTC")
    try:
        parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError as exc:
        raise AnchorError("gen_time is not YYYY-MM-DDTHH:MM:SSZ") from exc
    return parsed.replace(tzinfo=UTC)


def validate_chain(record: dict[str, Any], previous: dict[str, Any] | None = None) -> None:
    """Accept sequence 1 at genesis, or a later head with a strictly later clock."""

    sequence = record.get("sequence")
    if isinstance(sequence, bool) or not isinstance(sequence, int) or sequence < 1:
        raise AnchorError("head sequence is not a positive integer")
    prev = record.get("prev_anchor_id")
    anchor_id = record.get("anchor_id")
    if not isinstance(anchor_id, str) or len(anchor_id) != 64:
        raise AnchorError("anchor_id is not a sha256 hex string")
    gen_time = parse_gen_time(str(record["external"]["gen_time"]))
    if sequence == 1:
        if previous is not None:
            raise AnchorError("sequence 1 has no previous head")
        if prev != genesis_id():
            raise AnchorError("sequence 1 does not point at the genesis id")
        return
    if previous is None:
        raise AnchorError("a later head needs the previous measured record")
    if sequence != int(previous["sequence"]) + 1:
        raise AnchorError("head sequence is not the previous sequence plus one")
    if prev != previous["anchor_id"]:
        raise AnchorError("prev_anchor_id is not the previous anchor id")
    if anchor_id == previous["anchor_id"]:
        raise AnchorError("anchor id is reused")
    previous_time = parse_gen_time(str(previous["external"]["gen_time"]))
    if gen_time <= previous_time:
        raise AnchorError("gen_time is not strictly later than the previous head")


def anchor_record(
    hnc_summary: dict[str, Any],
    token: bytes,
    parsed: dict[str, Any],
    token_text: str,
) -> dict[str, Any]:
    commitment = measurement_commitment(hnc_summary)
    if commitment["hnc_identity_changed"]:
        raise AnchorError(_refuse_new_identity())
    anchor_id = hashlib.sha256(token).hexdigest()
    if EXPECTED_ANCHOR_ID and anchor_id != EXPECTED_ANCHOR_ID:
        raise AnchorError(
            "timestamp token does not match the recorded HNC head anchor id "
            f"{EXPECTED_ANCHOR_ID}"
        )
    measured = hashlib.sha256(commitment_bytes(commitment)).hexdigest()
    record = {
        "schema": SCHEMA,
        "receipt": 3,
        "receipt_name": "durable HNC evidence with an external monotonic head anchor",
        "tag": "measured",
        "go_live": "HOLD",
        "go_live_clear": False,
        "system_alive": False,
        "live_trading": False,
        "orders_placed": False,
        "external_llm": False,
        "market_series": False,
        "public_require_pin": PUBLIC_PIN,
        "published_require_pin": PUBLISHED_PIN,
        "recorded_pin_status": "historical",
        "hnc_identity_changed": False,
        "hnc_identity_note": _identity_note("This receipt"),
        "sequence": 1,
        "prev_anchor_id": genesis_id(),
        "genesis": GENESIS,
        "anchor_id": anchor_id,
        "note_ref": NOTE_REF,
        "note_git_blob": git_blob_sha1(token_text.encode("ascii")),
        "measurement_sha256": measured,
        "measurement": commitment,
        "external": {
            "kind": "rfc3161",
            "provider": TSA_URL,
            "provider_contacted_by_check": False,
            "policy_oid": parsed["policy_oid"],
            "hash_algorithm": "sha256",
            "gen_time": parsed["gen_time"],
            "serial_hex": parsed["serial_hex"],
            "tsa_ordering": parsed["tsa_ordering"],
            "imprint_sha256": parsed["imprint_sha256"],
            "token_sha256": anchor_id,
            "verification": parsed["verification"],
            "ca": parsed["ca"],
        },
        "binding": {
            "token_source": f"{NOTE_REF} on HEAD, equal to the committed blob {TOKEN_REL}",
            "working_tree_is_not_the_source": True,
            "monotonic_rule": (
                "Sequence 1 points at the genesis id. A later head is a new timestamp "
                "whose sequence is one greater, whose prev_anchor_id is this anchor_id, "
                "and whose verified gen_time is strictly later. The timestamp authority "
                "reports ordering no, so this chain is the monotonic rule. This receipt "
                "does not append a later head. A working-tree edit does not move the git note."
            ),
        },
    }
    validate_chain(record)
    return record


def id_text(record: dict[str, Any]) -> str:
    return str(record["anchor_id"]) + "\n"


def next_commitment(hnc_summary: dict[str, Any], previous: dict[str, Any]) -> dict[str, Any]:
    """Sequence-1 commitment plus the next sequence and the previous anchor id.

    ``external_head_anchor_attested`` is inside the timestamped bytes and is
    false. The commitment keeps historical pin ``PUBLIC_PIN``. This function
    does not move ``PUBLISHED_PIN``.
    """

    if int(previous.get("sequence", 0)) != 1:
        raise AnchorError("the next head can follow sequence 1 only")
    previous_id = previous.get("anchor_id")
    if previous_id != EXPECTED_ANCHOR_ID:
        raise AnchorError("the next head does not follow the recorded sequence 1 anchor")
    commitment = dict(measurement_commitment(hnc_summary))
    if commitment["hnc_identity_changed"]:
        raise AnchorError(_refuse_new_identity())
    commitment["sequence"] = 2
    commitment["prev_anchor_id"] = previous_id
    commitment["external_head_anchor_attested"] = False
    return commitment


def next_anchor_record(
    hnc_summary: dict[str, Any],
    previous: dict[str, Any],
    token: bytes,
    parsed: dict[str, Any],
    token_text: str,
) -> dict[str, Any]:
    commitment = next_commitment(hnc_summary, previous)
    anchor_id = hashlib.sha256(token).hexdigest()
    if EXPECTED_NEXT_ANCHOR_ID and anchor_id != EXPECTED_NEXT_ANCHOR_ID:
        raise AnchorError(
            "timestamp token does not match the recorded next HNC head anchor id "
            f"{EXPECTED_NEXT_ANCHOR_ID}"
        )
    measured = hashlib.sha256(commitment_bytes(commitment)).hexdigest()
    record = {
        "schema": SCHEMA,
        "receipt": 3,
        "receipt_name": "durable HNC evidence with an external monotonic head anchor",
        "follow_on": "next monotonic head",
        "tag": "measured",
        "go_live": "HOLD",
        "go_live_clear": False,
        "system_alive": False,
        "live_trading": False,
        "orders_placed": False,
        "external_llm": False,
        "external_head_anchor_attested": False,
        "market_series": False,
        "public_require_pin": PUBLIC_PIN,
        "published_require_pin": PUBLISHED_PIN,
        "recorded_pin_status": "historical",
        "hnc_identity_changed": False,
        "hnc_identity_note": _identity_note("This follow-on"),
        "sequence": 2,
        "prev_anchor_id": previous["anchor_id"],
        "previous_gen_time": previous["external"]["gen_time"],
        "genesis": GENESIS,
        "anchor_id": anchor_id,
        "note_ref": NEXT_NOTE_REF,
        "note_git_blob": git_blob_sha1(token_text.encode("ascii")),
        "measurement_sha256": measured,
        "measurement": commitment,
        "external": {
            "kind": "rfc3161",
            "provider": TSA_URL,
            "provider_contacted_by_check": False,
            "policy_oid": parsed["policy_oid"],
            "hash_algorithm": "sha256",
            "gen_time": parsed["gen_time"],
            "serial_hex": parsed["serial_hex"],
            "tsa_ordering": parsed["tsa_ordering"],
            "imprint_sha256": parsed["imprint_sha256"],
            "token_sha256": anchor_id,
            "verification": parsed["verification"],
            "ca": parsed["ca"],
        },
        "binding": {
            "token_source": (
                f"{NEXT_NOTE_REF} on HEAD, equal to the committed blob {NEXT_TOKEN_REL}"
            ),
            "working_tree_is_not_the_source": True,
            "monotonic_rule": (
                "Sequence 2 names the sequence 1 anchor id as prev_anchor_id. "
                "The verified gen_time is strictly later than sequence 1. "
                "The timestamp authority's ordering flag is recorded as measured. "
                "This chain is the monotonic rule. external_head_anchor_attested "
                "stays false. This record does not say the system is alive and does "
                "not clear go-live. A working-tree edit does not move the git note."
            ),
        },
    }
    validate_chain(record, previous)
    if record["external_head_anchor_attested"] is not False:
        raise AnchorError("external_head_anchor_attested is not false")
    if record["system_alive"] is not False or record["go_live"] != "HOLD":
        raise AnchorError("the next head must stay on HOLD and must not say the system is alive")
    return record


def assemble(root: Path, hnc_summary: dict[str, Any], *, require_note: bool) -> dict[str, str]:
    """Verify the external token and return the evidence files as text."""

    text = load_token_text(root, require_note=require_note)
    token = decode_token_text(text)
    commitment = commitment_bytes(measurement_commitment(hnc_summary))
    parsed = verify_timestamp(token, commitment)
    record = anchor_record(hnc_summary, token, parsed, text)
    blob = subprocess.run(
        ["git", "hash-object", "--stdin"],
        input=text.encode("ascii"),
        capture_output=True,
        cwd=root,
        check=False,
    )
    if blob.returncode != 0 or blob.stdout.decode("ascii").strip() != record["note_git_blob"]:
        raise AnchorError("git hash-object of the token text does not match note_git_blob")
    if EXPECTED_ANCHOR_ID == "":
        raise AnchorError("EXPECTED_ANCHOR_ID is empty; the measured head has not been recorded")
    return {
        TOKEN_REL: text,
        RECORD_REL: dump(record),
        ID_REL: id_text(record),
    }


def stamp_files(root: Path, hnc_summary: dict[str, Any]) -> dict[str, str]:
    """Request one timestamp and return the files. Check does not call this."""

    commitment = measurement_commitment(hnc_summary)
    if commitment["hnc_identity_changed"]:
        raise AnchorError(_refuse_new_identity())
    data = commitment_bytes(commitment)
    token = request_timestamp(data)
    text = canonical_token_text(token)
    parsed = verify_timestamp(token, data)
    record = anchor_record(hnc_summary, token, parsed, text)
    files = {
        TOKEN_REL: text,
        RECORD_REL: dump(record),
        ID_REL: id_text(record),
    }
    for relative, contents in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(contents, encoding="utf-8")
    return files


def attach_note(
    root: Path,
    *,
    note_name: str = NOTE_NAME,
    token_rel: str = TOKEN_REL,
) -> None:
    """Attach the committed token to HEAD. Refuses a dirty working-tree copy."""

    path = root / token_rel
    head = read_head_blob(root, token_rel)
    if head is None:
        raise AnchorError(f"{token_rel} is not committed on HEAD")
    work = path.read_bytes()
    if work != head:
        raise AnchorError("working tree token differs from HEAD; the note was not moved")
    proc = subprocess.run(
        ["git", "notes", "--ref", note_name, "add", "-f", "-F", str(path), "HEAD"],
        cwd=root,
        capture_output=True,
    )
    if proc.returncode != 0:
        detail = proc.stderr.decode("utf-8", "replace").strip()
        raise AnchorError(f"git notes add failed: {detail}")
    note = read_note(root, note_name)
    if note != head:
        raise AnchorError("git note does not match the committed token")


def assemble_next(
    root: Path,
    hnc_summary: dict[str, Any],
    previous: dict[str, Any],
    *,
    require_note: bool,
) -> dict[str, str]:
    """Verify the sequence-2 token and return its evidence files as text."""

    if EXPECTED_NEXT_ANCHOR_ID == "":
        raise AnchorError("EXPECTED_NEXT_ANCHOR_ID is empty; the next head has not been recorded")
    text = load_token_text(
        root,
        require_note=require_note,
        note_name=NEXT_NOTE_NAME,
        note_ref=NEXT_NOTE_REF,
        token_rel=NEXT_TOKEN_REL,
        record_rel=NEXT_RECORD_REL,
    )
    token = decode_token_text(text)
    commitment = commitment_bytes(next_commitment(hnc_summary, previous))
    parsed = verify_timestamp(token, commitment)
    record = next_anchor_record(hnc_summary, previous, token, parsed, text)
    blob = subprocess.run(
        ["git", "hash-object", "--stdin"],
        input=text.encode("ascii"),
        capture_output=True,
        cwd=root,
        check=False,
    )
    if blob.returncode != 0 or blob.stdout.decode("ascii").strip() != record["note_git_blob"]:
        raise AnchorError("git hash-object of the next token text does not match note_git_blob")
    return {
        NEXT_TOKEN_REL: text,
        NEXT_RECORD_REL: dump(record),
        NEXT_ID_REL: id_text(record),
    }


def stamp_next(root: Path, hnc_summary: dict[str, Any]) -> dict[str, str]:
    """Request one timestamp for sequence 2. Check does not call this.

    Refuses when the formula series would move the public pin, when sequence 1
    does not verify, or when the verified gen_time is not strictly later.
    """

    if EXPECTED_NEXT_ANCHOR_ID:
        raise AnchorError(
            "the next HNC head is already recorded; this command does not request another timestamp"
        )
    previous_files = assemble(root, hnc_summary, require_note=False)
    previous = json.loads(previous_files[RECORD_REL])
    data = commitment_bytes(next_commitment(hnc_summary, previous))
    token = request_timestamp(data)
    text = canonical_token_text(token)
    parsed = verify_timestamp(token, data)
    record = next_anchor_record(hnc_summary, previous, token, parsed, text)
    files = {
        NEXT_TOKEN_REL: text,
        NEXT_RECORD_REL: dump(record),
        NEXT_ID_REL: id_text(record),
    }
    for relative, contents in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(contents, encoding="utf-8")
    return files

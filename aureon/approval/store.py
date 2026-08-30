"""The ledger of approvals — the part that cannot be talked round.

One JSON file per token under ``state/approvals/``. Every state change is
appended to that file's history with the evidence that caused it, and written
atomically (temp file, ``fsync``, ``os.replace``) so a crash mid-write cannot
leave a half-parsed approval behind. A ledger of approvals that can be corrupted
by a power cut is not a ledger.

Three of the six non-negotiable properties are enforced here, in code paths a
caller cannot go around:

**Single use (3).** ``save`` claims the token file with ``O_EXCL``, so a second
``save`` of the same token raises rather than resetting a resolved request to
PENDING. ``resolve`` refuses any token whose state is already terminal. A
replayed email — the same reply delivered twice, or forwarded back — changes
nothing. UNCLEAR and IGNORED are deliberately *not* terminal: neither is an
answer, so neither may spend Gary's token before he answers.

**Expiry (4).** ``resolve`` compares against ``expires_at`` before it records
anything. An attempt to approve an expired request stamps it EXPIRED and returns
``False``. The old yes does not land, and the token is closed on its way out.

**Fail closed.** A record that cannot be read — missing, truncated, malformed,
or carrying a token that does not match its own filename — resolves to nothing.
Worst case an approval becomes unobtainable and Gary is asked again; the failure
mode is "nothing happens", never "something happened that nobody authorised".

``root`` is honoured verbatim when passed, with no environment fallback, for the
reason ``grants.dossier.grants_directory`` gives: a reader that quietly reaches
out of the caller's tree into the live repository hides faults and leaks live
data into tests.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from aureon.approval.schemas import (
    OPEN_STATES,
    TERMINAL_STATES,
    ApprovalRequest,
    ApprovalState,
    coerce_state,
    is_token,
)

LOG = logging.getLogger("aureon.approval.store")

# aureon/approval/store.py -> repo root
REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_APPROVALS_DIR = REPO_ROOT / "state" / "approvals"
DIR_VAR = "AUREON_APPROVALS_DIR"
RECORD_VERSION = 1
# Enough history to audit a thread, capped so a stranger replying in a loop
# cannot grow the file without bound. The total is kept alongside it.
MAX_HISTORY = 50


def approvals_dir(root: Path | str | None = None) -> Path:
    """Where the approval ledger lives.

    An explicit ``root`` wins and is used verbatim (``<root>/state/approvals``).
    Otherwise ``AUREON_APPROVALS_DIR``, otherwise ``state/approvals`` beside this
    repository.
    """
    if root is not None:
        return Path(root) / "state" / "approvals"
    override = str(os.environ.get(DIR_VAR, "") or "").strip()
    return Path(override) if override else DEFAULT_APPROVALS_DIR


def record_path(token: str, *, root: Path | str | None = None) -> Path:
    """The file one token's record lives in.

    Raises on a token that is not token-shaped. The token arrives from an inbound
    email, and ``"../../data/research/grants/pipeline"`` must not be able to steer
    a write out of this directory.
    """
    if not is_token(token):
        raise ValueError("refusing to touch a malformed approval token")
    return approvals_dir(root) / f"{token}.json"


def _now(now: datetime | None = None) -> datetime:
    value = now or datetime.now(UTC)
    return value if value.tzinfo else value.replace(tzinfo=UTC)


def _write_atomic(path: Path, payload: dict[str, Any]) -> None:
    """Write JSON so that the file is either the old one or the new one.

    ``os.replace`` is atomic on POSIX and on Windows (``MoveFileEx`` with
    ``REPLACE_EXISTING``), and the ``fsync`` before it means the bytes are on the
    platter before the rename makes them visible.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.{os.getpid()}.tmp")
    try:
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2, ensure_ascii=False)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    finally:
        try:
            if tmp.exists():
                tmp.unlink()
        except OSError:  # pragma: no cover — best-effort cleanup
            pass


def save(request: ApprovalRequest, *, root: Path | str | None = None) -> Path:
    """Persist a freshly composed request. Never overwrites an existing token.

    Raises :class:`FileExistsError` if this token already has a record. That is
    property 3 at the filesystem level: there is no code path in this package
    that can move a resolved token back to PENDING, so a replay cannot reopen a
    spent approval.
    """
    if not isinstance(request, ApprovalRequest):
        raise TypeError("save expects an ApprovalRequest")
    path = record_path(request.token, root=root)
    path.parent.mkdir(parents=True, exist_ok=True)
    # Claim the token atomically before writing a byte. If two processes compose
    # the same token (they cannot, but the ledger does not rely on that), exactly
    # one wins the claim.
    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        raise FileExistsError(
            f"approval {request.token[:8]} already has a record — refusing to overwrite it") from None
    os.close(fd)
    _write_atomic(path, {
        "version": RECORD_VERSION,
        "request": request.to_dict(),
        "saved_at": _now().isoformat(),
        "resolved_at": None,
        "history": [{"state": request.state.value, "evidence": "request composed",
                     "at": request.created_at.isoformat()}],
        "history_recorded": 1,
    })
    LOG.info("approval %s saved (%s, expires %s)",
             request.token[:8], request.action, request.expires_at.isoformat())
    return path


def load_record(token: str, *, root: Path | str | None = None) -> dict[str, Any] | None:
    """The whole record, history included, or ``None`` if it cannot be read."""
    try:
        path = record_path(token, root=root)
    except ValueError:
        LOG.debug("load_record refused a malformed token")
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        # A truncated claim from a crashed save lands here. Unreadable, therefore
        # unresolvable, therefore nothing gets approved on it.
        LOG.warning("approval record for %s is unreadable — treated as unresolvable", token[:8])
        return None
    if not isinstance(raw, dict) or not isinstance(raw.get("request"), dict):
        LOG.warning("approval record for %s is malformed — treated as unresolvable", token[:8])
        return None
    if str(raw["request"].get("token") or "") != token:
        # The filename and the record disagree: something wrote this by hand.
        LOG.warning("approval record for %s carries a different token — refused", token[:8])
        return None
    return raw


def load(token: str, *, root: Path | str | None = None) -> ApprovalRequest | None:
    """The request behind a token, or ``None`` if there is none to be had."""
    record = load_record(token, root=root)
    if record is None:
        return None
    try:
        return ApprovalRequest.from_dict(record["request"])
    except ValueError:
        LOG.warning("approval record for %s could not be rebuilt — treated as unresolvable",
                    token[:8])
        return None


def resolve(
    token: str,
    state: Any,
    evidence: str,
    *,
    root: Path | str | None = None,
    now: datetime | None = None,
) -> bool:
    """Record what happened to one request. The single-use, expiry-bound gate.

    Returns ``True`` only when this call changed the ledger. **``True`` means
    "recorded", not "approved"** — the state you passed says which. Returns
    ``False``, having changed nothing that authorises anything, when:

    - the token is unknown, malformed, or its record is unreadable;
    - the request is already resolved (property 3 — a replayed reply is inert);
    - the deadline has passed (property 4 — the request is stamped EXPIRED and
      the answer is discarded, whatever it said);
    - the caller tried to move a request back to PENDING.

    ``APPROVED`` and ``DECLINED`` close the token for good. ``UNCLEAR`` and
    ``IGNORED`` are recorded against an open request and leave it open, because
    "I could not read your answer" and "a stranger wrote to me" are not answers.
    """
    try:
        target = coerce_state(state)
    except ValueError:
        LOG.warning("approval %s: refused an unknown state %r", str(token)[:8], state)
        return False
    if target is ApprovalState.PENDING:
        LOG.warning("approval %s: refused to move a request back to PENDING", str(token)[:8])
        return False

    record = load_record(token, root=root)
    if record is None:
        LOG.warning("approval %s: no such request — nothing to resolve", str(token)[:8])
        return False
    try:
        request = ApprovalRequest.from_dict(record["request"])
    except ValueError:
        LOG.warning("approval %s: record could not be rebuilt — refusing to resolve", str(token)[:8])
        return False

    short = request.token[:8]
    if request.resolved:
        LOG.warning("approval %s: already %s — single use, refusing %s",
                    short, request.state, target)
        return False

    stamp = _now(now)
    if request.is_expired(stamp) and target is not ApprovalState.EXPIRED:
        # Property 4. Recorded as expired, with the answer that arrived too late
        # written into the evidence so the trail shows what was refused and why.
        _commit(record, request, ApprovalState.EXPIRED, stamp, root=root, evidence=(
            f"expired at {request.expires_at.isoformat()}; a late {target} arrived "
            f"at {stamp.isoformat()} and was refused — {evidence}"))
        LOG.warning("approval %s: expired at %s — a late %s cannot authorise it",
                    short, request.expires_at.isoformat(), target)
        return False

    _commit(record, request, target, stamp, root=root, evidence=evidence)
    LOG.info("approval %s: recorded %s", short, target)
    return True


def _commit(
    record: dict[str, Any],
    request: ApprovalRequest,
    state: ApprovalState,
    stamp: datetime,
    *,
    root: Path | str | None,
    evidence: str,
) -> None:
    """Append one state change and write the record atomically."""
    history = list(record.get("history") or ())
    history.append({"state": state.value, "evidence": str(evidence or "no evidence recorded"),
                    "at": stamp.isoformat()})
    total = int(record.get("history_recorded") or len(history) - 1) + 1
    if len(history) > MAX_HISTORY:
        history = history[:1] + history[-(MAX_HISTORY - 1):]
    record["request"] = request.with_state(state).to_dict()
    record["history"] = history
    record["history_recorded"] = total
    record["resolved_at"] = stamp.isoformat() if state in TERMINAL_STATES else None
    _write_atomic(record_path(request.token, root=root), record)


def tokens(*, root: Path | str | None = None) -> tuple[str, ...]:
    """Every token with a record, oldest filename first."""
    directory = approvals_dir(root)
    try:
        names = sorted(p.stem for p in directory.glob("*.json"))
    except OSError:
        return ()
    return tuple(name for name in names if is_token(name))


def open_requests(*, root: Path | str | None = None) -> tuple[ApprovalRequest, ...]:
    """Every request still waiting on Gary. Unreadable records are omitted."""
    out = []
    for token in tokens(root=root):
        request = load(token, root=root)
        if request is not None and request.state in OPEN_STATES:
            out.append(request)
    return tuple(out)


def expire_overdue(*, root: Path | str | None = None, now: datetime | None = None) -> tuple[str, ...]:
    """Stamp every open request past its deadline as EXPIRED. Returns their tokens.

    Property 4 does not depend on this sweep — ``resolve`` refuses a late answer
    on its own — but running it keeps the ledger honest about what is still live.
    """
    stamp = _now(now)
    expired: list[str] = []
    for request in open_requests(root=root):
        if request.is_expired(stamp) and resolve(
                request.token, ApprovalState.EXPIRED,
                f"deadline {request.expires_at.isoformat()} passed unanswered",
                root=root, now=stamp):
            expired.append(request.token)
    return tuple(expired)


__all__ = ["DEFAULT_APPROVALS_DIR", "DIR_VAR", "MAX_HISTORY",
           "approvals_dir", "expire_overdue", "load", "load_record", "open_requests",
           "record_path", "resolve", "save", "tokens"]

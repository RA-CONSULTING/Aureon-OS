"""Owner-gated application of one exact V5 investor-copy governance proposal.

This module is intentionally specific to the immutable 2026-07-30 proposal
named below.  It can verify an owner-supplied decision, reconstruct the exact
three-file governance delta, and prove the proposed state in a temporary shadow
repository.  It cannot generate an owner decision, edit website or policy
files, create a candidate or package, use credentials or network access, or
grant release/deployment authority.

Canonical writes are inaccessible unless ``apply=True`` is supplied together
with a fresh, exact, immutable decision issued by the named owner.  Every
preflight is repeated immediately before the three-file transaction.  A
durable, same-volume journal makes an interrupted cooperative transaction
recoverable without claiming filesystem-level multi-file atomicity.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import re
import shutil
import stat
import tempfile
import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from aureon.operator.design_evidence_brief import (
    DEFAULT_BRIEF_PATH,
    _claim_capsule,
    audit_design_evidence_brief,
    audit_design_evidence_brief_file,
)
from aureon.operator.design_investor_copy_repair import _claim_binding
from aureon.operator.design_stakeholder_feedback import (
    audit_design_stakeholder_feedback,
    audit_design_stakeholder_feedback_file,
)
from aureon.operator.public_claim_evidence import (
    DEFAULT_REGISTER_RELATIVE_PATH,
    audit_public_claim_evidence,
    audit_public_claim_evidence_file,
)

DECISION_SCHEMA = "aureon.investor-copy-governance-owner-decision.v1"
VERIFICATION_SCHEMA = "aureon.investor-copy-governance-decision-verification.v1"
PLAN_SCHEMA = "aureon.investor-copy-governance-application-plan.v1"
APPLICATION_SCHEMA = "aureon.investor-copy-governance-application.v1"

NAMED_OWNER = "Gary Leckey"
APPROVE_STATE = "approve-exact-governance-delta"
DECISION_STATES = frozenset({APPROVE_STATE, "reject", "request-revision"})
MAX_DECISION_AGE = timedelta(hours=24)
MAX_PROPOSAL_AGE = timedelta(hours=24)
FUTURE_TOLERANCE = timedelta(minutes=5)

DEFAULT_PROPOSAL_PATH = Path(
    "artifacts/website-operator/20260730T094627Z-investor-copy-governance-application-proposal-v5.json"
)
DEFAULT_VALIDATION_PATH = Path(
    "artifacts/website-operator/"
    "20260730T094627Z-investor-copy-governance-application-proposal-validation-v5.json"
)
SUPERSEDED_PROPOSAL_PATH = Path(
    "artifacts/website-operator/20260730T070009Z-investor-copy-governance-proposal.json"
)
SUPERSEDED_VALIDATION_PATH = Path(
    "artifacts/website-operator/20260730T070009Z-investor-copy-governance-proposal-validation.json"
)
SUPERSEDED_V2_PROPOSAL_PATH = Path(
    "artifacts/website-operator/20260730T072344Z-investor-copy-governance-superseding-proposal.json"
)
SUPERSEDED_V2_VALIDATION_PATH = Path(
    "artifacts/website-operator/"
    "20260730T072344Z-investor-copy-governance-superseding-proposal-validation.json"
)
SUPERSEDED_V3_PROPOSAL_PATH = Path(
    "artifacts/website-operator/20260730T074800Z-investor-copy-governance-superseding-proposal-v3.json"
)
SUPERSEDED_V3_VALIDATION_PATH = Path(
    "artifacts/website-operator/"
    "20260730T074800Z-investor-copy-governance-superseding-proposal-validation-v3.json"
)
SUPERSEDED_V4_PROPOSAL_PATH = Path(
    "artifacts/website-operator/20260730T075154Z-investor-copy-governance-superseding-proposal-v4.json"
)
SUPERSEDED_V4_VALIDATION_PATH = Path(
    "artifacts/website-operator/"
    "20260730T075154Z-investor-copy-governance-superseding-proposal-validation-v4.json"
)
DEFAULT_DECISION_ROOT = Path("artifacts/website-operator/owner-decisions")
DEFAULT_RECEIPT_ROOT = Path("artifacts/website-operator/copy-governance-applications")
DEFAULT_RECOVERY_RECEIPT_ROOT = Path("artifacts/website-operator/copy-governance-recoveries")
TRANSACTION_LOCK_PATH = Path("data/website_operator/.investor-copy-governance-transaction.lock")
TRANSACTION_ROOT = Path("data/website_operator/.investor-copy-governance-transaction")
TRANSACTION_JOURNAL_PATH = TRANSACTION_ROOT / "journal.json"

EXPECTED_PROPOSAL_SHA256 = "CDCC9AB0C38338EB57EDF416ECF9CE52ED3B448C32259EF7190AE0CEAF796897"
EXPECTED_VALIDATION_SHA256 = "A8BB51803E8A4F476A0C35C09C427D5AC6D0C7C42E147730213F6E9D4343340A"
SUPERSEDED_PROPOSAL_SHA256 = "F9061D2C2E21C4BF201D2108B931346D19945D2658C78C65ACDE5DB16B3CE072"
SUPERSEDED_VALIDATION_SHA256 = "D1FF5A70C0DBC8D59939705539C10395155D12F6AA310D94BCA334886326B6E7"
SUPERSEDED_V2_PROPOSAL_SHA256 = "5111F351D1EAEEAD2E57E4DA372300F5614674920AACD406EE2CA27873A70DCF"
SUPERSEDED_V2_VALIDATION_SHA256 = "BDFC1687BB2729ADD52FE9FA52B5531A0197B08A8D04A575EE654D7984EB6D79"
SUPERSEDED_V3_PROPOSAL_SHA256 = "73C53FD9E0087BA371876FFDAB02CF47E980A9472A6F4D656B4761C5E7F317BD"
SUPERSEDED_V3_VALIDATION_SHA256 = "538CD6ED13688039C69DDF2A675165E99268B258A86F6029DB48482A7B1E7613"
SUPERSEDED_V4_PROPOSAL_SHA256 = "EB1F8FDAEB6CF5F314502FAAC2ECC46A5AB7D21BE5CB21D1E111FB9873E81448"
SUPERSEDED_V4_VALIDATION_SHA256 = "D3F2E10DAC7D2E7182DD2D362B2035A6A4FF7E120194978BC4A64D866438FE5F"
EXPECTED_REGISTER_BEFORE_SHA256 = "78032392BD3ECED2C5C9B294415AD6D2C6380FF903F7E43844C191AFD99C99A7"
EXPECTED_REGISTER_AFTER_SHA256 = "3D24208BB40CCFFC42B9EC70FA46C9226B8FD1B8363A767FC6D5E757C78959BF"
EXPECTED_FEEDBACK_BEFORE_SHA256 = "A9DC7F847B926FF7E762A0F01EC58357D084624F05D5529E4A9596A96EF5C4DE"
EXPECTED_FEEDBACK_AFTER_SHA256 = "28D4F56F87A3133C2A2871303B00BFD0B5A0FAF8CBD71CC6C19034C2E4AAD2E9"
EXPECTED_BRIEF_BEFORE_SHA256 = "6BCD1A422A5697CDA7FD94DC1AA8CA428050ABF2F21203460A11D3BD3D794046"
EXPECTED_BRIEF_AFTER_SHA256 = "FDEB5C0070FDFDE4FDC0832852E278D81E63F11C700843878709E6B2565D953C"
EXPECTED_POLICY_SHA256 = "025340D876B041C1A2095F60C82549DC165BFFE93126B98A9C853CB4836CF492"
EXPECTED_TARGET_SHA256 = "A2F2C742A78AC4E72A85D38F15EE464A5B468BBFF3034D309B4E4C08F252F930"
EXPECTED_ROUTE_CAPSULE_SHA256 = "608B4AA3CF3B3A6909FD24DA370BF0C76346E81A41C55BE41531B62EEA56EEDA"
EXPECTED_REQUIRED_CONCEPT_GROUPS_SHA256 = "7788A568EB2F20DC21EE185D2040AE304ADBE6D9C1C2BB8A297F4FC8F2842766"
EXPECTED_SATISFIED_CONCEPT_IDS = ["commercial-wedge", "company-category", "human-control"]
EXPECTED_PROJECTS_SOURCE_INPUT = {
    "id": "projects-positioning",
    "path": "website/projects/index.html",
    "sha256": "5D75CF500C4259CC9DCF504A98456034CE03C22080FD4EDB7F4A6C356D7CD893",
    "role": ("Public company-category and Evidence OS positioning anchors for governed route claims."),
}
EXPECTED_DESIGN_RECEIPT_PATH = Path("artifacts/website-operator/20260730T045336Z-design-cycle-4204c795.json")
EXPECTED_DESIGN_RECEIPT_SHA256 = "264D722168DE283FC48ABD83422566DB335A7030BFCD744029F6E11B5555EFC6"
EXPECTED_PROJECTS_SOURCE_PATH = Path("website/projects/index.html")
EXPECTED_PROJECTS_SOURCE_SHA256 = "5D75CF500C4259CC9DCF504A98456034CE03C22080FD4EDB7F4A6C356D7CD893"
EXPECTED_COMPANY_PLATFORM_PATH = Path("website/data/company-platform.json")
EXPECTED_COMPANY_PLATFORM_SHA256 = "53B4296E7FD12A3289D04876D3F1B52DA22D1CDED101133DE91E41A3630D62BC"
EXPECTED_SURFACE_CLAIM_ID = "aureon-evidence-os-positioning"
EXPECTED_SURFACE_WORDING = "One evidence OS."
EXPECTED_SURFACE_RECORD_BEFORE_SHA256 = "E275C0C5751ED290A04EECF6DE5AD5B83F306C030FAD169026400CFC8C1AE5BE"
EXPECTED_SURFACE_RECORD_AFTER_SHA256 = "B8CD9260CA76F0649FA5AB0B94E7D3E3EC674C28804C8FD51178437D5DD673B3"
EXPECTED_SURFACE_SOURCE_LOCATOR = 'meta[property="og:title"] and meta[name="twitter:title"]'
EXPECTED_SURFACE_SOURCE_OCCURRENCES = 2

REGISTER_PATH = DEFAULT_REGISTER_RELATIVE_PATH
FEEDBACK_PATH = Path("data/website_operator/design_stakeholder_feedback.v1.json")
BRIEF_PATH = DEFAULT_BRIEF_PATH
POLICY_PATH = Path("data/website_operator/investor_copy_quality_policy.v1.json")
TARGET_PATH = Path("website/funding/investor-deck/index.html")
TARGET_ROUTE = "/funding/investor-deck/"
TARGET_ROUTE_ID = "investor-reading-room"
TARGET_TASK_ID = "DESIGN-COPY-001"
CANONICAL_GOVERNANCE_PATHS = [
    REGISTER_PATH.as_posix(),
    FEEDBACK_PATH.as_posix(),
    BRIEF_PATH.as_posix(),
]

NON_RELEASE_AUTHORITY = {
    "scope": "exact owner-gated three-file claim-governance application only",
    "website_mutation": "never",
    "policy_mutation": "never",
    "candidate_authority": "none",
    "package_authority": "none",
    "release_eligible": False,
    "deployment_authority": "none",
    "credential_access": "none",
    "network_access": "none",
}

_DECISION_FIELDS = frozenset(
    {
        "schema",
        "decision_id",
        "decided_at",
        "owner",
        "decision",
        "proposal",
        "validation",
        "acknowledgements",
    }
)
_BINDING_FIELDS = frozenset({"path", "sha256"})
_ACK_FIELDS = frozenset(
    {
        "governance_files",
        "no_policy_change",
        "no_website_change",
        "no_candidate_or_package_authority",
        "no_release_or_deployment_authority",
        "v1_through_v4_superseded_and_rejected",
        "sentence_level_evidence_os_wording",
    }
)
_EXPECTED_ACKNOWLEDGEMENTS = {
    "governance_files": CANONICAL_GOVERNANCE_PATHS,
    "no_policy_change": True,
    "no_website_change": True,
    "no_candidate_or_package_authority": True,
    "no_release_or_deployment_authority": True,
    "v1_through_v4_superseded_and_rejected": True,
    "sentence_level_evidence_os_wording": EXPECTED_SURFACE_WORDING,
}
_EXPECTED_DELTA_FIELDS = frozenset(
    {
        "policy",
        "website",
        "claim_register",
        "stakeholder_feedback",
        "design_brief",
        "expected_route_capsule",
    }
)
_SHA256 = re.compile(r"^[A-F0-9]{64}$")
_IDENTIFIER = re.compile(r"^[a-z0-9][a-z0-9._-]{2,127}$")
_DECISION_FILENAME = re.compile(r"^([a-z0-9][a-z0-9._-]{2,127})\.json$")
_WINDOWS_RESERVED_STEMS = frozenset(
    {"CON", "PRN", "AUX", "NUL"}
    | {f"COM{index}" for index in range(1, 10)}
    | {f"LPT{index}" for index in range(1, 10)}
)
_REPARSE_POINT = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)


class InvestorCopyGovernanceError(ValueError):
    """A decision, proposal, source, audit, or transaction is not safe."""

    def __init__(self, code: str, message: str, *, details: Sequence[str] = ()) -> None:
        super().__init__(message)
        self.code = code
        self.details = tuple(details)


@dataclass(frozen=True)
class _Decision:
    value: dict[str, Any]
    path: Path
    sha256: str
    decision_id: str
    state: str
    decided_at: datetime


@dataclass(frozen=True)
class _JsonSnapshot:
    value: dict[str, Any]
    raw: bytes
    sha256: str


@dataclass(frozen=True)
class _ApplicationPlan:
    decision: _Decision
    proposal: dict[str, Any]
    validation: dict[str, Any]
    register: dict[str, Any]
    feedback: dict[str, Any]
    brief: dict[str, Any]
    register_bytes: bytes
    feedback_bytes: bytes
    brief_bytes: bytes
    route_capsule: dict[str, Any]
    claim_audit: dict[str, Any]
    feedback_audit: dict[str, Any]
    design_audit: dict[str, Any]


def _find_repo_root(start: Path | None = None) -> Path:
    candidate = (start or Path.cwd()).resolve()
    for root in (candidate, *candidate.parents):
        if (root / "pyproject.toml").is_file() and (root / "aureon").is_dir():
            return root
    raise InvestorCopyGovernanceError("repo-root", "Repository root is unavailable.")


def _iso(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _now(value: datetime | None) -> datetime:
    return (value or datetime.now(UTC)).astimezone(UTC)


def _wall_now() -> datetime:
    """Return the real wall clock used by mutating operations."""

    return datetime.now(UTC)


def _timestamp(value: object, *, label: str) -> datetime:
    if not isinstance(value, str) or not value or len(value) > 64:
        raise InvestorCopyGovernanceError("timestamp", f"{label} timestamp is malformed.")
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise InvestorCopyGovernanceError("timestamp", f"{label} timestamp is malformed.") from exc
    if result.tzinfo is None:
        raise InvestorCopyGovernanceError("timestamp", f"{label} timestamp is malformed.")
    return result.astimezone(UTC)


def _fresh(
    value: object,
    *,
    label: str,
    current: datetime,
    maximum_age: timedelta,
) -> datetime:
    observed = _timestamp(value, label=label)
    age = current - observed
    if age < -FUTURE_TOLERANCE:
        raise InvestorCopyGovernanceError("future-input", f"{label} is materially future-dated.")
    if age > maximum_age:
        raise InvestorCopyGovernanceError("stale-input", f"{label} is outside its freshness window.")
    return observed


def _mapping(value: object, *, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise InvestorCopyGovernanceError("shape", f"{label} must be one object.")
    return dict(value)


def _exact_fields(
    value: Mapping[str, Any],
    fields: frozenset[str],
    *,
    label: str,
) -> None:
    if set(value) != fields:
        raise InvestorCopyGovernanceError("shape", f"{label} field contract changed.")


def _safe_identifier(value: object, *, label: str) -> str:
    if not isinstance(value, str) or _IDENTIFIER.fullmatch(value) is None:
        raise InvestorCopyGovernanceError("identifier", f"{label} is malformed.")
    return value


def _safe_sha256(value: object, *, label: str) -> str:
    if not isinstance(value, str) or _SHA256.fullmatch(value) is None:
        raise InvestorCopyGovernanceError("sha256", f"{label} is malformed.")
    return value


def _safe_relative(value: object, *, label: str) -> str:
    if not isinstance(value, str) or not value or value != value.replace("\\", "/"):
        raise InvestorCopyGovernanceError("path", f"{label} is malformed.")
    relative = Path(value)
    if relative.is_absolute() or any(part in {"", ".", ".."} for part in relative.parts):
        raise InvestorCopyGovernanceError("path", f"{label} is malformed.")
    return relative.as_posix()


def _is_link_or_reparse(path: Path) -> bool:
    try:
        details = path.lstat()
    except OSError as exc:
        raise InvestorCopyGovernanceError("filesystem", "A bound filesystem object is unavailable.") from exc
    attributes = int(getattr(details, "st_file_attributes", 0))
    return path.is_symlink() or bool(attributes & _REPARSE_POINT)


def _regular_file(path: Path, *, label: str) -> Path:
    lexical = path.absolute()
    if _is_link_or_reparse(lexical):
        raise InvestorCopyGovernanceError("unsafe-file", f"{label} must not be a link or reparse point.")
    try:
        details = lexical.lstat()
    except OSError as exc:
        raise InvestorCopyGovernanceError("missing-file", f"{label} is unavailable.") from exc
    if not stat.S_ISREG(details.st_mode) or details.st_nlink != 1:
        raise InvestorCopyGovernanceError("unsafe-file", f"{label} must be one single-link regular file.")
    return lexical.resolve(strict=True)


def _repo_file(root: Path, relative: str, *, label: str) -> Path:
    safe = _safe_relative(relative, label=label)
    current = root
    for part in Path(safe).parts:
        current = current / part
        if _is_link_or_reparse(current):
            raise InvestorCopyGovernanceError("unsafe-file", f"{label} crosses a link or reparse point.")
    target = _regular_file(current, label=label)
    try:
        target.relative_to(root)
    except ValueError as exc:
        raise InvestorCopyGovernanceError("path", f"{label} escaped the repository.") from exc
    return target


def _controlled_directory(root: Path, relative: Path, *, label: str) -> Path:
    safe = _safe_relative(relative.as_posix(), label=label)
    current = root
    for part in Path(safe).parts:
        current = current / part
        if _is_link_or_reparse(current):
            raise InvestorCopyGovernanceError(
                "unsafe-directory",
                f"{label} crosses a link or reparse point.",
            )
        try:
            details = current.lstat()
        except OSError as exc:
            raise InvestorCopyGovernanceError(
                "missing-directory",
                f"{label} is unavailable.",
            ) from exc
        if not stat.S_ISDIR(details.st_mode):
            raise InvestorCopyGovernanceError(
                "unsafe-directory",
                f"{label} contains a non-directory component.",
            )
        try:
            current.resolve(strict=True).relative_to(root)
        except ValueError as exc:
            raise InvestorCopyGovernanceError(
                "unsafe-directory",
                f"{label} escaped the repository.",
            ) from exc
    return current.resolve(strict=True)


def _controlled_directory_create_leaf(
    root: Path,
    relative: Path,
    *,
    label: str,
) -> Path:
    parent = _controlled_directory(root, relative.parent, label=f"{label} parent")
    leaf = parent / relative.name
    if leaf.exists():
        return _controlled_directory(root, relative, label=label)
    leaf.mkdir()
    _fsync_directory(parent)
    return _controlled_directory(root, relative, label=label)


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def _bytes_sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest().upper()


def _json_sha256(value: object) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest().upper()


def _serialise(value: Mapping[str, Any]) -> bytes:
    return (
        json.dumps(
            dict(value),
            indent=2,
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _reject_json_constant(value: str) -> None:
    raise ValueError(f"Unsupported JSON constant: {value}")


def _unique_json_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def _snapshot_json(
    path: Path,
    *,
    label: str,
    canonical: bool = False,
) -> _JsonSnapshot:
    """Parse and hash the same one-handle, single-link regular-file snapshot."""

    lexical = path.absolute()
    if _is_link_or_reparse(lexical):
        raise InvestorCopyGovernanceError(
            "unsafe-file",
            f"{label} must not be a link or reparse point.",
        )
    try:
        before = lexical.lstat()
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
            raise InvestorCopyGovernanceError(
                "unsafe-file",
                f"{label} must be one single-link regular file.",
            )
        flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
        handle = os.open(lexical, flags)
        with os.fdopen(handle, "rb", closefd=True) as stream:
            opened = os.fstat(stream.fileno())
            if (
                not stat.S_ISREG(opened.st_mode)
                or opened.st_nlink != 1
                or (before.st_dev, before.st_ino) != (opened.st_dev, opened.st_ino)
            ):
                raise InvestorCopyGovernanceError(
                    "snapshot-race",
                    f"{label} changed while its snapshot was opened.",
                )
            raw = stream.read()
            finished = os.fstat(stream.fileno())
            if (
                (opened.st_dev, opened.st_ino, opened.st_size)
                != (finished.st_dev, finished.st_ino, finished.st_size)
                or getattr(opened, "st_mtime_ns", None) != getattr(finished, "st_mtime_ns", None)
                or getattr(opened, "st_ctime_ns", None) != getattr(finished, "st_ctime_ns", None)
            ):
                raise InvestorCopyGovernanceError(
                    "snapshot-race",
                    f"{label} changed during its snapshot read.",
                )
        if raw.startswith(b"\xef\xbb\xbf"):
            raise InvestorCopyGovernanceError(
                "serialization",
                f"{label} must not carry a UTF-8 BOM.",
            )
        parsed = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_unique_json_object,
            parse_constant=_reject_json_constant,
        )
        value = _mapping(parsed, label=label)
        if canonical and (raw != _serialise(value) or b"\r" in raw):
            raise InvestorCopyGovernanceError(
                "serialization",
                f"{label} is not exact UTF-8, LF-only, two-space JSON with one final newline.",
            )
    except InvestorCopyGovernanceError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        raise InvestorCopyGovernanceError(
            "json",
            f"{label} is not valid unambiguous UTF-8 JSON.",
        ) from exc
    return _JsonSnapshot(
        value=value,
        raw=raw,
        sha256=_bytes_sha256(raw),
    )


def _read_json(path: Path, *, label: str) -> dict[str, Any]:
    return _snapshot_json(path, label=label).value


def _require_canonical_serialisation(path: Path, value: Mapping[str, Any], *, label: str) -> bytes:
    observed = path.read_bytes()
    expected = _serialise(value)
    if observed != expected or b"\r" in observed:
        raise InvestorCopyGovernanceError(
            "serialization",
            f"{label} is not exact UTF-8, LF-only, two-space JSON with one final newline.",
        )
    return observed


def _binding(value: object, *, label: str) -> dict[str, str]:
    binding = _mapping(value, label=label)
    _exact_fields(binding, _BINDING_FIELDS, label=label)
    path = _safe_relative(binding.get("path"), label=f"{label} path")
    sha256 = _safe_sha256(binding.get("sha256"), label=f"{label} SHA-256")
    return {"path": path, "sha256": sha256}


def _controlled_decision_file(root: Path, value: Path) -> Path:
    decision_root = root / DEFAULT_DECISION_ROOT
    current = root
    for part in DEFAULT_DECISION_ROOT.parts:
        current = current / part
        if (
            not current.is_dir()
            or _is_link_or_reparse(current)
            or current.resolve(strict=True).is_relative_to(root) is False
        ):
            raise InvestorCopyGovernanceError(
                "decision-root",
                "The owner-decision root crosses an unsafe controlled directory.",
            )
    lexical = (value if value.is_absolute() else root / value).absolute()
    match = _DECISION_FILENAME.fullmatch(lexical.name)
    if (
        lexical.parent != decision_root.absolute()
        or match is None
        or match.group(1).split(".", 1)[0].upper() in _WINDOWS_RESERVED_STEMS
    ):
        raise InvestorCopyGovernanceError(
            "decision-path",
            "Owner decision must be one strict ASCII JSON child of the controlled root.",
        )
    return _regular_file(lexical, label="Owner decision")


def _decision_or_raise(
    decision_path: Path,
    *,
    root: Path,
    current: datetime,
) -> _Decision:
    path = _controlled_decision_file(root, decision_path)
    snapshot = _snapshot_json(path, label="Owner decision", canonical=True)
    value = snapshot.value
    _exact_fields(value, _DECISION_FIELDS, label="Owner decision")
    if value.get("schema") != DECISION_SCHEMA:
        raise InvestorCopyGovernanceError("decision-schema", "Owner decision schema is unsupported.")
    decision_id = _safe_identifier(value.get("decision_id"), label="Decision id")
    if path.name != f"{decision_id}.json":
        raise InvestorCopyGovernanceError(
            "decision-path",
            "Owner decision filename must exactly match its decision id.",
        )
    decided_at = _fresh(
        value.get("decided_at"),
        label="Owner decision",
        current=current,
        maximum_age=MAX_DECISION_AGE,
    )
    if value.get("owner") != NAMED_OWNER:
        raise InvestorCopyGovernanceError(
            "decision-owner", "Owner decision is not issued by the named owner."
        )
    state = value.get("decision")
    if state not in DECISION_STATES:
        raise InvestorCopyGovernanceError("decision-state", "Owner decision state is unsupported.")
    proposal = _binding(value.get("proposal"), label="Proposal binding")
    validation = _binding(value.get("validation"), label="Validation binding")
    if proposal != {
        "path": DEFAULT_PROPOSAL_PATH.as_posix(),
        "sha256": EXPECTED_PROPOSAL_SHA256,
    }:
        raise InvestorCopyGovernanceError(
            "proposal-binding", "Owner decision does not bind the exact proposal."
        )
    if validation != {
        "path": DEFAULT_VALIDATION_PATH.as_posix(),
        "sha256": EXPECTED_VALIDATION_SHA256,
    }:
        raise InvestorCopyGovernanceError(
            "validation-binding", "Owner decision does not bind the exact validation."
        )
    acknowledgements = _mapping(value.get("acknowledgements"), label="Owner acknowledgements")
    _exact_fields(acknowledgements, _ACK_FIELDS, label="Owner acknowledgements")
    if acknowledgements != _EXPECTED_ACKNOWLEDGEMENTS:
        raise InvestorCopyGovernanceError(
            "decision-boundary", "Owner decision boundary was broadened or changed."
        )
    return _Decision(
        value=value,
        path=path,
        sha256=snapshot.sha256,
        decision_id=decision_id,
        state=str(state),
        decided_at=decided_at,
    )


def _assert_decision_causal(
    decision: _Decision,
    *,
    proposal: Mapping[str, Any],
    validation: Mapping[str, Any],
) -> None:
    if decision.decided_at < max(
        _timestamp(proposal.get("generated_at"), label="Governance proposal"),
        _timestamp(validation.get("validated_at"), label="Governance validation"),
    ):
        raise InvestorCopyGovernanceError(
            "decision-before-artifacts",
            "Owner decision predates the exact proposal or validation it approves.",
        )


def verify_investor_copy_governance_decision(
    decision_path: Path,
    *,
    repo_root: Path | None = None,
    as_of: datetime | None = None,
) -> dict[str, Any]:
    """Verify one owner-supplied immutable decision without changing any file."""

    root = _find_repo_root(repo_root)
    current = _now(as_of)
    decision_id = ""
    decision_sha256 = ""
    decision_state = ""
    blocked_codes: list[str] = []
    try:
        _assert_no_pending_transaction(root)
        decision = _decision_or_raise(decision_path, root=root, current=current)
        proposal, validation, _ = _proposal_and_validation(root=root, current=current)
        _assert_decision_causal(
            decision,
            proposal=proposal,
            validation=validation,
        )
        decision_id = decision.decision_id
        decision_sha256 = decision.sha256
        decision_state = decision.state
        valid = True
    except InvestorCopyGovernanceError as exc:
        valid = False
        blocked_codes = [exc.code]
    approved = valid and decision_state == APPROVE_STATE
    if approved:
        state = "approved"
    elif valid and decision_state == "reject":
        state = "rejected"
    elif valid and decision_state == "request-revision":
        state = "revision-requested"
    else:
        state = "blocked"
    return {
        "schema": VERIFICATION_SCHEMA,
        "verified_at": _iso(current),
        "state": state,
        "valid": valid,
        "approved": approved,
        "decision_id": decision_id,
        "decision_sha256": decision_sha256,
        "decision_state": decision_state,
        "proposal_sha256": EXPECTED_PROPOSAL_SHA256,
        "validation_sha256": EXPECTED_VALIDATION_SHA256,
        "blocked_codes": blocked_codes,
        "canonical_mutation": False,
        "authority": dict(NON_RELEASE_AUTHORITY),
    }


def _proposal_and_validation(
    *,
    root: Path,
    current: datetime,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    proposal_path = _repo_file(root, DEFAULT_PROPOSAL_PATH.as_posix(), label="Governance proposal")
    validation_path = _repo_file(root, DEFAULT_VALIDATION_PATH.as_posix(), label="Governance validation")
    proposal_snapshot = _snapshot_json(
        proposal_path,
        label="Governance proposal",
        canonical=True,
    )
    validation_snapshot = _snapshot_json(
        validation_path,
        label="Governance validation",
        canonical=True,
    )
    if proposal_snapshot.sha256 != EXPECTED_PROPOSAL_SHA256:
        raise InvestorCopyGovernanceError("proposal-drift", "Exact governance proposal SHA-256 changed.")
    if validation_snapshot.sha256 != EXPECTED_VALIDATION_SHA256:
        raise InvestorCopyGovernanceError("validation-drift", "Exact governance validation SHA-256 changed.")
    proposal = proposal_snapshot.value
    validation = validation_snapshot.value
    superseded_pairs = [
        (
            "v1",
            "incomplete-source-and-feedback-bindings",
            SUPERSEDED_PROPOSAL_PATH,
            SUPERSEDED_PROPOSAL_SHA256,
            SUPERSEDED_VALIDATION_PATH,
            SUPERSEDED_VALIDATION_SHA256,
        ),
        (
            "v2",
            "incomplete-three-file-authority-and-supersession-language",
            SUPERSEDED_V2_PROPOSAL_PATH,
            SUPERSEDED_V2_PROPOSAL_SHA256,
            SUPERSEDED_V2_VALIDATION_PATH,
            SUPERSEDED_V2_VALIDATION_SHA256,
        ),
        (
            "v3",
            "ambiguous-claim-route-scope",
            SUPERSEDED_V3_PROPOSAL_PATH,
            SUPERSEDED_V3_PROPOSAL_SHA256,
            SUPERSEDED_V3_VALIDATION_PATH,
            SUPERSEDED_V3_VALIDATION_SHA256,
        ),
        (
            "v4",
            "multi-sentence-permitted-wording-not-renderable-as-one-hash-bound-surface",
            SUPERSEDED_V4_PROPOSAL_PATH,
            SUPERSEDED_V4_PROPOSAL_SHA256,
            SUPERSEDED_V4_VALIDATION_PATH,
            SUPERSEDED_V4_VALIDATION_SHA256,
        ),
    ]
    base_proposal: dict[str, Any] | None = None
    for (
        generation,
        _reason_code,
        prior_proposal_path,
        prior_proposal_sha256,
        prior_validation_path,
        prior_validation_sha256,
    ) in superseded_pairs:
        prior_proposal = _repo_file(
            root,
            prior_proposal_path.as_posix(),
            label=f"Superseded {generation} governance proposal",
        )
        prior_validation = _repo_file(
            root,
            prior_validation_path.as_posix(),
            label=f"Superseded {generation} governance validation",
        )
        prior_proposal_snapshot = _snapshot_json(
            prior_proposal,
            label=f"Superseded {generation} governance proposal",
            canonical=True,
        )
        prior_validation_snapshot = _snapshot_json(
            prior_validation,
            label=f"Superseded {generation} governance validation",
            canonical=True,
        )
        if (
            prior_proposal_snapshot.sha256 != prior_proposal_sha256
            or prior_validation_snapshot.sha256 != prior_validation_sha256
        ):
            raise InvestorCopyGovernanceError(
                "superseded-artifact-drift",
                "An immutable superseded governance artifact changed.",
            )
        if generation == "v1":
            base_proposal = prior_proposal_snapshot.value
    if base_proposal is None:
        raise InvestorCopyGovernanceError(
            "base-delta-binding",
            "Superseded v1 base proposal is unavailable.",
        )
    _fresh(
        proposal.get("generated_at"),
        label="Governance proposal",
        current=current,
        maximum_age=MAX_PROPOSAL_AGE,
    )
    _fresh(
        validation.get("validated_at"),
        label="Governance validation",
        current=current,
        maximum_age=MAX_PROPOSAL_AGE,
    )
    if (
        proposal.get("schema") != "aureon.investor-copy-governance-proposal.v5"
        or proposal.get("state") != "proposal-only-owner-approval-required"
    ):
        raise InvestorCopyGovernanceError("proposal-shape", "Governance proposal schema or state changed.")
    if (
        validation.get("schema") != "aureon.investor-copy-governance-proposal-validation.v5"
        or validation.get("state") != "pass-proposal-only"
        or validation.get("passed") is not True
    ):
        raise InvestorCopyGovernanceError(
            "validation-state", "Governance proposal validation is not passing."
        )
    raw_validation_proposal = _mapping(validation.get("proposal"), label="Validated proposal")
    if (
        set(raw_validation_proposal) != {"path", "sha256", "json_valid"}
        or raw_validation_proposal.get("path") != DEFAULT_PROPOSAL_PATH.as_posix()
        or raw_validation_proposal.get("sha256") != EXPECTED_PROPOSAL_SHA256
        or raw_validation_proposal.get("json_valid") is not True
    ):
        raise InvestorCopyGovernanceError(
            "validation-binding", "Validation no longer binds the exact proposal."
        )
    supersession = _mapping(proposal.get("supersession"), label="Proposal supersession")
    validation_supersession = _mapping(
        validation.get("supersedes"),
        label="Validation supersession",
    )
    if (
        supersession.get("original_application_allowed") is not False
        or supersession.get("reason_code") != "surface-compatible-source-bound-wording-correction"
        or validation_supersession.get("original_application_allowed") is not False
        or validation_supersession.get("reason_code") != "surface-compatible-source-bound-wording-correction"
    ):
        raise InvestorCopyGovernanceError(
            "supersession-binding", "Corrected proposal supersession binding changed."
        )
    proposal_artifacts = supersession.get("artifacts")
    validation_artifacts = validation_supersession.get("artifacts")
    if (
        not isinstance(proposal_artifacts, list)
        or not isinstance(validation_artifacts, list)
        or len(proposal_artifacts) != len(superseded_pairs)
        or len(validation_artifacts) != len(superseded_pairs)
    ):
        raise InvestorCopyGovernanceError(
            "supersession-binding",
            "Corrected proposal supersession set changed.",
        )
    for index, (
        generation,
        reason_code,
        prior_proposal_path,
        prior_proposal_sha256,
        prior_validation_path,
        prior_validation_sha256,
    ) in enumerate(superseded_pairs):
        expected_prior_proposal = {
            "path": prior_proposal_path.as_posix(),
            "sha256": prior_proposal_sha256,
        }
        expected_prior_validation = {
            "path": prior_validation_path.as_posix(),
            "sha256": prior_validation_sha256,
        }
        proposal_item = _mapping(
            proposal_artifacts[index],
            label=f"Proposal superseded {generation} artifact",
        )
        validation_item = _mapping(
            validation_artifacts[index],
            label=f"Validation superseded {generation} artifact",
        )
        if (
            proposal_item.get("generation") != generation
            or proposal_item.get("reason_code") != reason_code
            or proposal_item.get("application_allowed") is not False
            or _binding(
                proposal_item.get("proposal"),
                label=f"Proposal superseded {generation} proposal binding",
            )
            != expected_prior_proposal
            or _binding(
                proposal_item.get("validation"),
                label=f"Proposal superseded {generation} validation binding",
            )
            != expected_prior_validation
            or validation_item.get("generation") != generation
            or validation_item.get("reason_code") != reason_code
            or validation_item.get("application_allowed") is not False
            or _binding(
                validation_item.get("proposal"),
                label=f"Validation superseded {generation} proposal binding",
            )
            != expected_prior_proposal
            or _binding(
                validation_item.get("validation"),
                label=f"Validation superseded {generation} validation binding",
            )
            != expected_prior_validation
        ):
            raise InvestorCopyGovernanceError(
                "supersession-binding",
                "Corrected proposal supersession binding changed.",
            )
    expected_superseded_proposal = {
        "path": SUPERSEDED_PROPOSAL_PATH.as_posix(),
        "sha256": SUPERSEDED_PROPOSAL_SHA256,
    }
    base_source = _binding(
        _mapping(proposal.get("base_delta"), label="Base delta").get("source"),
        label="Base-delta proposal binding",
    )
    if (
        base_source != expected_superseded_proposal
        or base_proposal.get("schema") != "aureon.investor-copy-governance-proposal.v1"
    ):
        raise InvestorCopyGovernanceError(
            "base-delta-binding", "Corrected proposal no longer binds the exact base delta."
        )
    expected_outputs = [
        {
            "path": REGISTER_PATH.as_posix(),
            "before_sha256": EXPECTED_REGISTER_BEFORE_SHA256,
            "after_sha256": EXPECTED_REGISTER_AFTER_SHA256,
        },
        {
            "path": FEEDBACK_PATH.as_posix(),
            "before_sha256": EXPECTED_FEEDBACK_BEFORE_SHA256,
            "after_sha256": EXPECTED_FEEDBACK_AFTER_SHA256,
        },
        {
            "path": BRIEF_PATH.as_posix(),
            "before_sha256": EXPECTED_BRIEF_BEFORE_SHA256,
            "after_sha256": EXPECTED_BRIEF_AFTER_SHA256,
        },
    ]
    if validation.get("proposed_outputs") != expected_outputs:
        raise InvestorCopyGovernanceError(
            "validation-outputs", "Validation proposed-output bindings changed."
        )
    checks = validation.get("checks")
    if (
        not isinstance(checks, list)
        or not checks
        or not all(
            isinstance(item, Mapping) and item.get("passed") is True and isinstance(item.get("id"), str)
            for item in checks
        )
    ):
        raise InvestorCopyGovernanceError("validation-checks", "Validation has a missing or failed check.")
    return proposal, validation, base_proposal


def _validate_proposal_boundary(proposal: Mapping[str, Any]) -> dict[str, Any]:
    target = _mapping(proposal.get("target"), label="Proposal target")
    if (
        target.get("task_id") != TARGET_TASK_ID
        or target.get("route_id") != TARGET_ROUTE_ID
        or target.get("route") != TARGET_ROUTE
        or target.get("path") != TARGET_PATH.relative_to("website").as_posix()
    ):
        raise InvestorCopyGovernanceError("target-binding", "Proposal target route, path, or task changed.")
    authority = _mapping(proposal.get("authority"), label="Proposal authority")
    required_authority = {
        "scope": "read-only corrected governance proposal for exact owner consideration",
        "canonical_claim_register_mutation": "none",
        "canonical_stakeholder_feedback_mutation": "none",
        "canonical_policy_mutation": "none",
        "canonical_design_brief_mutation": "none",
        "canonical_website_mutation": "none",
        "candidate_staging": "none",
        "release_eligible": False,
        "package_authority": "none",
        "deployment_authority": "none",
        "credential_access": "none",
        "network_access": "none",
        "approval_authority": "none",
        "owner_approval_required": True,
    }
    if authority != required_authority:
        raise InvestorCopyGovernanceError("proposal-authority", "Proposal authority boundary was broadened.")
    owner_gate = _mapping(proposal.get("owner_approval_gate"), label="Owner approval gate")
    if (
        owner_gate.get("required") is not True
        or owner_gate.get("named_owner") != NAMED_OWNER
        or owner_gate.get("broad_system_access_is_not_this_decision") is not True
        or owner_gate.get("decision_states")
        != [
            APPROVE_STATE,
            "reject",
            "request-revision",
        ]
    ):
        raise InvestorCopyGovernanceError("owner-gate", "Proposal owner gate changed.")
    delta = _mapping(proposal.get("corrected_canonical_delta"), label="Canonical delta")
    _exact_fields(delta, _EXPECTED_DELTA_FIELDS, label="Canonical delta")
    policy = _mapping(delta.get("policy"), label="Policy delta")
    website = _mapping(delta.get("website"), label="Website delta")
    if policy.get("action") != "none" or website.get("action") != "none":
        raise InvestorCopyGovernanceError(
            "scope-broadened", "Proposal now carries a policy or website change."
        )
    claim_register = _mapping(delta.get("claim_register"), label="Claim-register delta")
    stakeholder_feedback = _mapping(delta.get("stakeholder_feedback"), label="Stakeholder-feedback delta")
    design_brief = _mapping(delta.get("design_brief"), label="Design-brief delta")
    surface_correction = _mapping(
        claim_register.get("surface_correction"),
        label="Sentence-level claim-surface correction",
    )
    _exact_fields(
        surface_correction,
        frozenset(
            {
                "claim_id",
                "expected_record_sha256_before",
                "append_permitted_wording",
                "append_source_evidence_text",
                "source",
                "expected_record_sha256_after",
            }
        ),
        label="Sentence-level claim-surface correction",
    )
    surface_source = _mapping(
        surface_correction.get("source"),
        label="Sentence-level claim-surface source",
    )
    _exact_fields(
        surface_source,
        frozenset({"path", "sha256", "locator", "exact_anchor_occurrences"}),
        label="Sentence-level claim-surface source",
    )
    if (
        claim_register.get("path") != REGISTER_PATH.as_posix()
        or claim_register.get("action") != "exact-delta-from-superseded-v1-proposal-plus-sentence-wording"
        or claim_register.get("expected_sha256") != EXPECTED_REGISTER_AFTER_SHA256
        or surface_correction.get("claim_id") != EXPECTED_SURFACE_CLAIM_ID
        or surface_correction.get("expected_record_sha256_before") != EXPECTED_SURFACE_RECORD_BEFORE_SHA256
        or surface_correction.get("append_permitted_wording") != EXPECTED_SURFACE_WORDING
        or surface_correction.get("append_source_evidence_text") != EXPECTED_SURFACE_WORDING
        or surface_correction.get("expected_record_sha256_after") != EXPECTED_SURFACE_RECORD_AFTER_SHA256
        or surface_source.get("path") != EXPECTED_PROJECTS_SOURCE_PATH.as_posix()
        or surface_source.get("sha256") != EXPECTED_PROJECTS_SOURCE_SHA256
        or surface_source.get("locator") != EXPECTED_SURFACE_SOURCE_LOCATOR
        or surface_source.get("exact_anchor_occurrences") != EXPECTED_SURFACE_SOURCE_OCCURRENCES
        or stakeholder_feedback.get("path") != FEEDBACK_PATH.as_posix()
        or stakeholder_feedback.get("action") != "replace-exact-claim-register-sha256-only"
        or stakeholder_feedback.get("replace_claim_register_sha256") != EXPECTED_REGISTER_AFTER_SHA256
        or stakeholder_feedback.get("expected_sha256_after_exact_delta_with_existing_utf8_lf_serialisation")
        != EXPECTED_FEEDBACK_AFTER_SHA256
        or stakeholder_feedback.get("signals_changed") is not False
        or stakeholder_feedback.get("evidence_snapshot_changed") is not False
        or stakeholder_feedback.get("authority_changed") is not False
        or design_brief.get("path") != BRIEF_PATH.as_posix()
        or design_brief.get("expected_sha256_after_exact_delta_with_existing_utf8_lf_serialisation")
        != EXPECTED_BRIEF_AFTER_SHA256
        or design_brief.get("replace_claim_control_register_sha256") != EXPECTED_REGISTER_AFTER_SHA256
        or design_brief.get("replace_feedback_control_sha256") != EXPECTED_FEEDBACK_AFTER_SHA256
    ):
        raise InvestorCopyGovernanceError(
            "delta-binding", "Proposed canonical path or expected hash changed."
        )
    expected_capsule = _mapping(delta.get("expected_route_capsule"), label="Expected route capsule")
    if (
        expected_capsule.get("sha256") != EXPECTED_ROUTE_CAPSULE_SHA256
        or expected_capsule.get("expected_satisfied_concept_ids") != EXPECTED_SATISFIED_CONCEPT_IDS
    ):
        raise InvestorCopyGovernanceError("capsule-binding", "Expected route capsule binding changed.")
    return delta


def _observed_binding(
    proposal: Mapping[str, Any],
    name: str,
    *,
    path: str,
    sha256: str,
) -> dict[str, Any]:
    observed = _mapping(proposal.get("observed_bindings"), label="Observed bindings")
    binding = _mapping(observed.get(name), label=f"Observed {name}")
    if binding.get("path") != path or binding.get("sha256") != sha256:
        raise InvestorCopyGovernanceError(f"{name}-binding", f"Observed {name} binding changed.")
    return binding


def _revalidate_design_receipt(proposal: Mapping[str, Any], *, root: Path) -> None:
    target = _mapping(proposal.get("target"), label="Proposal target")
    binding = _mapping(target.get("design_cycle_receipt"), label="Design-cycle receipt binding")
    receipt_relative = _safe_relative(binding.get("path"), label="Design-cycle receipt path")
    receipt = _repo_file(root, receipt_relative, label="Design-cycle receipt")
    snapshot = _snapshot_json(
        receipt,
        label="Design-cycle receipt",
        canonical=True,
    )
    if snapshot.sha256 != _safe_sha256(
        binding.get("sha256"),
        label="Design-cycle receipt SHA-256",
    ):
        raise InvestorCopyGovernanceError("design-receipt-drift", "Design-cycle receipt changed.")
    content = snapshot.value
    if content.get("run_id") != binding.get("run_id"):
        raise InvestorCopyGovernanceError("design-receipt-drift", "Design-cycle run id changed.")
    work_orders = content.get("work_orders")
    if not isinstance(work_orders, list):
        raise InvestorCopyGovernanceError("design-task-drift", "Design-cycle work orders are malformed.")
    matches = [
        dict(item) for item in work_orders if isinstance(item, Mapping) and item.get("id") == TARGET_TASK_ID
    ]
    if len(matches) != 1 or _json_sha256(matches[0]) != _safe_sha256(
        binding.get("task_sha256"), label="Design task SHA-256"
    ):
        raise InvestorCopyGovernanceError("design-task-drift", "Exact design-copy task changed.")


def _canonical_inputs(
    proposal: Mapping[str, Any],
    *,
    root: Path,
) -> tuple[
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    bytes,
    bytes,
    bytes,
]:
    register_path = _repo_file(root, REGISTER_PATH.as_posix(), label="Claim register")
    feedback_path = _repo_file(root, FEEDBACK_PATH.as_posix(), label="Stakeholder feedback")
    brief_path = _repo_file(root, BRIEF_PATH.as_posix(), label="Design brief")
    register_snapshot = _snapshot_json(
        register_path,
        label="Claim register",
        canonical=True,
    )
    feedback_snapshot = _snapshot_json(
        feedback_path,
        label="Stakeholder feedback",
        canonical=True,
    )
    brief_snapshot = _snapshot_json(
        brief_path,
        label="Design brief",
        canonical=True,
    )
    register = register_snapshot.value
    feedback = feedback_snapshot.value
    brief = brief_snapshot.value
    register_bytes = register_snapshot.raw
    feedback_bytes = feedback_snapshot.raw
    brief_bytes = brief_snapshot.raw
    if (
        register_snapshot.sha256 != EXPECTED_REGISTER_BEFORE_SHA256
        or feedback_snapshot.sha256 != EXPECTED_FEEDBACK_BEFORE_SHA256
        or brief_snapshot.sha256 != EXPECTED_BRIEF_BEFORE_SHA256
    ):
        raise InvestorCopyGovernanceError(
            "canonical-drift",
            "Canonical claim register, stakeholder feedback, or design brief changed.",
        )
    _observed_binding(
        proposal,
        "claim_register",
        path=REGISTER_PATH.as_posix(),
        sha256=EXPECTED_REGISTER_BEFORE_SHA256,
    )
    _observed_binding(
        proposal,
        "stakeholder_feedback",
        path=FEEDBACK_PATH.as_posix(),
        sha256=EXPECTED_FEEDBACK_BEFORE_SHA256,
    )
    _observed_binding(
        proposal,
        "design_brief",
        path=BRIEF_PATH.as_posix(),
        sha256=EXPECTED_BRIEF_BEFORE_SHA256,
    )
    return (
        register,
        feedback,
        brief,
        register_bytes,
        feedback_bytes,
        brief_bytes,
    )


def _revalidate_bound_sources(
    proposal: Mapping[str, Any],
    base_proposal: Mapping[str, Any],
    *,
    root: Path,
) -> None:
    _observed_binding(
        proposal,
        "policy",
        path=POLICY_PATH.as_posix(),
        sha256=EXPECTED_POLICY_SHA256,
    )
    _observed_binding(
        proposal,
        "target_html",
        path=TARGET_PATH.as_posix(),
        sha256=EXPECTED_TARGET_SHA256,
    )
    if _file_sha256(_repo_file(root, POLICY_PATH.as_posix(), label="Copy policy")) != (
        EXPECTED_POLICY_SHA256
    ):
        raise InvestorCopyGovernanceError("policy-drift", "Copy policy changed.")
    if _file_sha256(_repo_file(root, TARGET_PATH.as_posix(), label="Target HTML")) != (
        EXPECTED_TARGET_SHA256
    ):
        raise InvestorCopyGovernanceError("target-drift", "Target HTML changed.")
    project_binding = _observed_binding(
        proposal,
        "projects_positioning_source",
        path=EXPECTED_PROJECTS_SOURCE_PATH.as_posix(),
        sha256=EXPECTED_PROJECTS_SOURCE_SHA256,
    )
    projects_source = _repo_file(
        root,
        str(project_binding["path"]),
        label="Projects positioning source",
    )
    if _file_sha256(projects_source) != project_binding["sha256"]:
        raise InvestorCopyGovernanceError("source-drift", "Projects-positioning source changed.")
    surface_correction = _mapping(
        _mapping(
            proposal.get("corrected_canonical_delta"),
            label="Canonical delta",
        ).get("claim_register"),
        label="Claim-register delta",
    )
    surface_correction = _mapping(
        surface_correction.get("surface_correction"),
        label="Sentence-level claim-surface correction",
    )
    surface_source = _mapping(
        surface_correction.get("source"),
        label="Sentence-level claim-surface source",
    )
    if (
        surface_source.get("path") != project_binding["path"]
        or surface_source.get("sha256") != project_binding["sha256"]
        or surface_source.get("locator") != EXPECTED_SURFACE_SOURCE_LOCATOR
        or surface_source.get("exact_anchor_occurrences") != EXPECTED_SURFACE_SOURCE_OCCURRENCES
    ):
        raise InvestorCopyGovernanceError(
            "source-binding",
            "Sentence-level Evidence OS source binding changed.",
        )
    try:
        projects_text = projects_source.read_text(encoding="utf-8", errors="strict")
    except (OSError, UnicodeError) as exc:
        raise InvestorCopyGovernanceError(
            "source-read",
            "Projects-positioning source is not strict UTF-8 text.",
        ) from exc
    if projects_text.count(EXPECTED_SURFACE_WORDING) != EXPECTED_SURFACE_SOURCE_OCCURRENCES:
        raise InvestorCopyGovernanceError(
            "source-anchor",
            "Sentence-level Evidence OS source anchor changed.",
        )
    assessment = base_proposal.get("concept_assessment")
    if not isinstance(assessment, list) or len(assessment) != 3:
        raise InvestorCopyGovernanceError("concept-assessment", "Proposal concept assessment changed.")
    for raw in assessment:
        item = _mapping(raw, label="Concept assessment")
        source = _mapping(item.get("source"), label="Concept source")
        relative = _safe_relative(source.get("path"), label="Concept source path")
        expected = _safe_sha256(source.get("sha256"), label="Concept source SHA-256")
        if _file_sha256(_repo_file(root, relative, label="Concept source")) != expected:
            raise InvestorCopyGovernanceError("source-drift", "A proposal evidence source changed.")
        if source.get("exact_anchor_present") is not True:
            raise InvestorCopyGovernanceError("source-anchor", "A proposal evidence anchor is not exact.")
    _revalidate_design_receipt(proposal, root=root)


def _build_register(
    register: Mapping[str, Any],
    *,
    delta: Mapping[str, Any],
    correction_delta: Mapping[str, Any],
) -> tuple[dict[str, Any], bytes]:
    proposed = copy.deepcopy(dict(register))
    claims = proposed.get("claims")
    if not isinstance(claims, list) or not all(isinstance(item, dict) for item in claims):
        raise InvestorCopyGovernanceError("register-shape", "Canonical claim register claims are malformed.")
    register_delta = _mapping(delta.get("claim_register"), label="Claim-register delta")
    update = _mapping(register_delta.get("update_existing_claim"), label="Existing claim delta")
    update_id = _safe_identifier(update.get("id"), label="Updated claim id")
    matches = [item for item in claims if item.get("id") == update_id]
    if len(matches) != 1:
        raise InvestorCopyGovernanceError("claim-update", "Updated claim is missing or duplicated.")
    claim = matches[0]
    wording = update.get("append_permitted_wording")
    evidence_text = update.get("append_source_evidence_text")
    locator = update.get("replace_source_locator")
    route = update.get("append_public_route")
    if (
        not isinstance(wording, str)
        or not wording
        or wording != evidence_text
        or not isinstance(locator, str)
        or not locator
        or route != TARGET_ROUTE
        or claim.get("boundary") != update.get("unchanged_boundary")
    ):
        raise InvestorCopyGovernanceError(
            "claim-update", "Existing claim delta changed or weakens its boundary."
        )
    permitted = claim.get("permitted_wording")
    source = claim.get("source")
    routes = claim.get("public_routes")
    if (
        not isinstance(permitted, list)
        or wording in permitted
        or not isinstance(source, dict)
        or not isinstance(source.get("evidence_texts"), list)
        or evidence_text in source["evidence_texts"]
        or not isinstance(routes, list)
        or route in routes
    ):
        raise InvestorCopyGovernanceError(
            "claim-prestate", "Existing claim is not at the exact expected pre-state."
        )
    permitted.append(wording)
    source["evidence_texts"].append(evidence_text)
    source["locator"] = locator
    routes.append(route)
    if _json_sha256(claim) != update.get("expected_record_sha256"):
        raise InvestorCopyGovernanceError(
            "claim-record-hash", "Updated claim record hash does not match the proposal."
        )

    raw_additions = register_delta.get("add_claims")
    if not isinstance(raw_additions, list) or len(raw_additions) != 2:
        raise InvestorCopyGovernanceError("claim-additions", "Proposal must add exactly two claims.")
    existing_ids = {str(item.get("id")) for item in claims}
    for raw in raw_additions:
        addition = _mapping(raw, label="Added claim")
        expected_record = _safe_sha256(
            addition.pop("expected_record_sha256", None),
            label="Added claim record SHA-256",
        )
        claim_id = _safe_identifier(addition.get("id"), label="Added claim id")
        if claim_id in existing_ids:
            raise InvestorCopyGovernanceError("claim-prestate", "An added claim id already exists.")
        if _json_sha256(addition) != expected_record:
            raise InvestorCopyGovernanceError(
                "claim-record-hash", "Added claim record hash does not match the proposal."
            )
        source_binding = _mapping(addition.get("source"), label="Added claim source")
        if TARGET_ROUTE not in addition.get("public_routes", []) or not str(
            source_binding.get("path", "")
        ).startswith("website/"):
            raise InvestorCopyGovernanceError(
                "claim-scope", "Added claim lacks the exact public-route/source boundary."
            )
        claims.append(addition)
        existing_ids.add(claim_id)

    corrected_register = _mapping(
        correction_delta.get("claim_register"),
        label="Corrected claim-register delta",
    )
    surface_correction = _mapping(
        corrected_register.get("surface_correction"),
        label="Sentence-level claim-surface correction",
    )
    surface_claim_id = _safe_identifier(
        surface_correction.get("claim_id"),
        label="Sentence-level claim id",
    )
    surface_matches = [item for item in claims if item.get("id") == surface_claim_id]
    if (
        surface_claim_id != EXPECTED_SURFACE_CLAIM_ID
        or len(surface_matches) != 1
        or _json_sha256(surface_matches[0]) != EXPECTED_SURFACE_RECORD_BEFORE_SHA256
        or surface_correction.get("expected_record_sha256_before") != EXPECTED_SURFACE_RECORD_BEFORE_SHA256
    ):
        raise InvestorCopyGovernanceError(
            "claim-surface-prestate",
            "Sentence-level Evidence OS claim is not at the exact V4 shadow pre-state.",
        )
    surface_claim = surface_matches[0]
    surface_wording = surface_correction.get("append_permitted_wording")
    surface_evidence_text = surface_correction.get("append_source_evidence_text")
    surface_source = _mapping(
        surface_correction.get("source"),
        label="Sentence-level claim-surface source",
    )
    permitted_wording = surface_claim.get("permitted_wording")
    claim_source = _mapping(
        surface_claim.get("source"),
        label="Sentence-level claim source record",
    )
    evidence_texts = claim_source.get("evidence_texts")
    if (
        surface_wording != EXPECTED_SURFACE_WORDING
        or surface_evidence_text != EXPECTED_SURFACE_WORDING
        or not isinstance(permitted_wording, list)
        or surface_wording in permitted_wording
        or not isinstance(evidence_texts, list)
        or surface_evidence_text in evidence_texts
        or surface_source.get("path") != claim_source.get("path")
        or surface_source.get("sha256") != claim_source.get("sha256")
        or surface_source.get("locator") != EXPECTED_SURFACE_SOURCE_LOCATOR
        or surface_source.get("exact_anchor_occurrences") != EXPECTED_SURFACE_SOURCE_OCCURRENCES
    ):
        raise InvestorCopyGovernanceError(
            "claim-surface-delta",
            "Sentence-level Evidence OS wording or source binding changed.",
        )
    permitted_wording.append(surface_wording)
    evidence_texts.append(surface_evidence_text)
    claim_source["evidence_texts"] = evidence_texts
    surface_claim["source"] = claim_source
    if (
        _json_sha256(surface_claim) != EXPECTED_SURFACE_RECORD_AFTER_SHA256
        or surface_correction.get("expected_record_sha256_after") != EXPECTED_SURFACE_RECORD_AFTER_SHA256
    ):
        raise InvestorCopyGovernanceError(
            "claim-surface-record-hash",
            "Sentence-level Evidence OS claim record hash changed.",
        )

    output = _serialise(proposed)
    if _bytes_sha256(output) != EXPECTED_REGISTER_AFTER_SHA256:
        raise InvestorCopyGovernanceError(
            "register-after-hash", "Proposed claim-register bytes do not match the exact hash."
        )
    return proposed, output


def _append_exact(target: object, additions: object, *, label: str) -> None:
    if (
        not isinstance(target, list)
        or not isinstance(additions, list)
        or not additions
        or not all(isinstance(item, str) and item for item in additions)
        or len(additions) != len(set(additions))
        or any(item in target for item in additions)
    ):
        raise InvestorCopyGovernanceError(
            "brief-prestate", f"{label} is not at the exact expected pre-state."
        )
    target.extend(additions)


def _build_feedback(
    feedback: Mapping[str, Any],
    *,
    delta: Mapping[str, Any],
) -> tuple[dict[str, Any], bytes]:
    proposed = copy.deepcopy(dict(feedback))
    feedback_delta = _mapping(delta.get("stakeholder_feedback"), label="Stakeholder-feedback delta")
    claim_register = _mapping(proposed.get("claim_register"), label="Feedback claim-register binding")
    if (
        claim_register.get("path") != REGISTER_PATH.as_posix()
        or claim_register.get("sha256") != EXPECTED_REGISTER_BEFORE_SHA256
        or feedback_delta.get("replace_claim_register_sha256") != EXPECTED_REGISTER_AFTER_SHA256
    ):
        raise InvestorCopyGovernanceError(
            "feedback-prestate",
            "Stakeholder feedback is not at the exact register-binding pre-state.",
        )
    original = copy.deepcopy(proposed)
    claim_register["sha256"] = EXPECTED_REGISTER_AFTER_SHA256
    proposed["claim_register"] = claim_register
    comparison = copy.deepcopy(proposed)
    comparison["claim_register"] = {
        **_mapping(comparison.get("claim_register"), label="Feedback comparison binding"),
        "sha256": EXPECTED_REGISTER_BEFORE_SHA256,
    }
    if comparison != original:
        raise InvestorCopyGovernanceError(
            "feedback-delta",
            "Stakeholder feedback delta changes more than the exact register SHA-256.",
        )
    output = _serialise(proposed)
    if _bytes_sha256(output) != EXPECTED_FEEDBACK_AFTER_SHA256:
        raise InvestorCopyGovernanceError(
            "feedback-after-hash",
            "Proposed stakeholder-feedback bytes do not match the exact hash.",
        )
    return proposed, output


def _build_brief(
    brief: Mapping[str, Any],
    *,
    delta: Mapping[str, Any],
) -> tuple[dict[str, Any], bytes]:
    proposed = copy.deepcopy(dict(brief))
    brief_delta = _mapping(delta.get("design_brief"), label="Design-brief delta")
    claim_control = _mapping(proposed.get("claim_control"), label="Brief claim control")
    if claim_control.get("register_sha256") != EXPECTED_REGISTER_BEFORE_SHA256:
        raise InvestorCopyGovernanceError("brief-prestate", "Design brief register binding changed.")
    global_ids = brief_delta.get("append_global_claim_ids")
    _append_exact(
        claim_control.get("claim_ids"),
        global_ids,
        label="Global brief claim ids",
    )
    claim_control["register_sha256"] = EXPECTED_REGISTER_AFTER_SHA256
    proposed["claim_control"] = claim_control
    route_plan = proposed.get("route_plan")
    if not isinstance(route_plan, list):
        raise InvestorCopyGovernanceError("brief-shape", "Design brief route plan is malformed.")
    matches = [item for item in route_plan if isinstance(item, dict) and item.get("id") == TARGET_ROUTE_ID]
    if len(matches) != 1 or matches[0].get("route") != TARGET_ROUTE:
        raise InvestorCopyGovernanceError(
            "brief-route", "Investor-reading-room route is missing or duplicated."
        )
    _append_exact(
        matches[0].get("claim_ids"),
        brief_delta.get("append_investor_reading_room_claim_ids"),
        label="Investor route claim ids",
    )
    source_inputs = proposed.get("source_inputs")
    raw_additions = brief_delta.get("append_source_inputs")
    if (
        not isinstance(source_inputs, list)
        or raw_additions != [EXPECTED_PROJECTS_SOURCE_INPUT]
        or any(
            isinstance(item, Mapping)
            and (
                item.get("id") == EXPECTED_PROJECTS_SOURCE_INPUT["id"]
                or item.get("path") == EXPECTED_PROJECTS_SOURCE_INPUT["path"]
            )
            for item in source_inputs
        )
    ):
        raise InvestorCopyGovernanceError(
            "brief-source-input-prestate",
            "Projects-positioning source input is not an exact single addition.",
        )
    source_inputs.append(copy.deepcopy(EXPECTED_PROJECTS_SOURCE_INPUT))
    feedback_control = _mapping(proposed.get("feedback_control"), label="Brief feedback control")
    if (
        feedback_control.get("feedback_sha256") != EXPECTED_FEEDBACK_BEFORE_SHA256
        or brief_delta.get("replace_feedback_control_sha256") != EXPECTED_FEEDBACK_AFTER_SHA256
    ):
        raise InvestorCopyGovernanceError(
            "brief-feedback-prestate",
            "Design brief feedback binding changed before the exact delta.",
        )
    feedback_control["feedback_sha256"] = EXPECTED_FEEDBACK_AFTER_SHA256
    proposed["feedback_control"] = feedback_control
    output = _serialise(proposed)
    if _bytes_sha256(output) != EXPECTED_BRIEF_AFTER_SHA256:
        raise InvestorCopyGovernanceError(
            "brief-after-hash", "Proposed design-brief bytes do not match the exact hash."
        )
    return proposed, output


def _route_capsule(
    register: Mapping[str, Any],
    brief: Mapping[str, Any],
    *,
    root: Path,
) -> dict[str, Any]:
    raw_claims = register.get("claims")
    raw_routes = brief.get("route_plan")
    if not isinstance(raw_claims, list) or not isinstance(raw_routes, list):
        raise InvestorCopyGovernanceError(
            "capsule-shape", "Proposed claim register or route plan is malformed."
        )
    claim_index = {
        str(item.get("id")): item
        for item in raw_claims
        if isinstance(item, Mapping) and isinstance(item.get("id"), str)
    }
    matches = [item for item in raw_routes if isinstance(item, Mapping) and item.get("id") == TARGET_ROUTE_ID]
    if len(matches) != 1:
        raise InvestorCopyGovernanceError("capsule-route", "Exact investor route is missing or duplicated.")
    route = dict(matches[0])
    claim_ids = route.get("claim_ids")
    if (
        not isinstance(claim_ids, list)
        or not claim_ids
        or not all(isinstance(item, str) and item in claim_index for item in claim_ids)
    ):
        raise InvestorCopyGovernanceError("capsule-claims", "Investor route claim ids are malformed.")
    capsule = {
        "route_id": TARGET_ROUTE_ID,
        "route": TARGET_ROUTE,
        "claims": [_claim_capsule(claim_index[claim_id], claim_id=claim_id) for claim_id in claim_ids],
    }
    if _json_sha256(capsule) != EXPECTED_ROUTE_CAPSULE_SHA256:
        raise InvestorCopyGovernanceError("capsule-after-hash", "Proposed route capsule hash changed.")
    policy = _read_json(
        _repo_file(root, POLICY_PATH.as_posix(), label="Copy policy"),
        label="Copy policy",
    )
    routes = policy.get("routes")
    if not isinstance(routes, list):
        raise InvestorCopyGovernanceError("policy-shape", "Copy policy routes are malformed.")
    policy_matches = [
        item for item in routes if isinstance(item, Mapping) and item.get("route") == TARGET_ROUTE
    ]
    if len(policy_matches) != 1:
        raise InvestorCopyGovernanceError(
            "policy-route", "Copy policy does not uniquely control the target route."
        )
    binding = _claim_binding(
        capsule=capsule,
        route=TARGET_ROUTE,
        required_claim_ids=[str(item) for item in claim_ids],
        required_concept_groups=policy_matches[0].get("required_concept_groups"),
    )
    if (
        binding.get("route_claim_capsule_sha256") != EXPECTED_ROUTE_CAPSULE_SHA256
        or binding.get("required_concept_groups_sha256") != EXPECTED_REQUIRED_CONCEPT_GROUPS_SHA256
        or binding.get("satisfied_concept_ids") != EXPECTED_SATISFIED_CONCEPT_IDS
    ):
        raise InvestorCopyGovernanceError(
            "concept-satisfiability", "Required concept satisfiability replay changed."
        )
    return capsule


def _copy_shadow_dependency(root: Path, shadow: Path, relative: str) -> None:
    source = _repo_file(root, relative, label="Shadow audit dependency")
    destination = shadow / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)


def _shadow_dependency_paths(
    register: Mapping[str, Any],
    feedback: Mapping[str, Any],
    brief: Mapping[str, Any],
    *,
    root: Path,
) -> set[str]:
    paths = {
        _safe_relative(
            _mapping(brief.get("source_document"), label="Brief source document").get("path"),
            label="Brief source document path",
        )
    }
    for item in brief.get("source_inputs", []):
        paths.add(
            _safe_relative(
                _mapping(item, label="Brief source input").get("path"),
                label="Brief source input path",
            )
        )
    for item in brief.get("route_plan", []):
        route = _mapping(item, label="Brief route")
        for allowed in route.get("allowed_paths", []):
            paths.add(f"website/{_safe_relative(allowed, label='Allowed website path')}")
    for item in register.get("claims", []):
        claim = _mapping(item, label="Public claim")
        source = _mapping(claim.get("source"), label="Public claim source")
        paths.add(_safe_relative(source.get("path"), label="Public claim source path"))
    research_path = _safe_relative(
        _mapping(brief.get("research_refresh"), label="Research refresh").get("declaration_path"),
        label="Research declaration path",
    )
    feedback_path = _safe_relative(
        _mapping(brief.get("feedback_control"), label="Feedback control").get("feedback_path"),
        label="Feedback declaration path",
    )
    paths.update({research_path, feedback_path})
    research = _read_json(
        _repo_file(root, research_path, label="Research declaration"),
        label="Research declaration",
    )
    for item in research.get("sources", []):
        source = _mapping(item, label="Research source")
        snapshot = _mapping(source.get("snapshot"), label="Research source snapshot")
        paths.add(_safe_relative(snapshot.get("path"), label="Research snapshot path"))
    artwork = _mapping(research.get("artwork_policy"), label="Artwork policy")
    artwork_snapshot = _mapping(artwork.get("evidence_snapshot"), label="Artwork evidence snapshot")
    paths.add(_safe_relative(artwork_snapshot.get("path"), label="Artwork evidence snapshot path"))
    feedback_snapshot = _mapping(feedback.get("evidence_snapshot"), label="Feedback evidence snapshot")
    paths.add(_safe_relative(feedback_snapshot.get("path"), label="Feedback evidence snapshot path"))
    paths.discard(REGISTER_PATH.as_posix())
    paths.discard(FEEDBACK_PATH.as_posix())
    paths.discard(BRIEF_PATH.as_posix())
    return paths


def _shadow_full_audits(
    register: Mapping[str, Any],
    feedback: Mapping[str, Any],
    brief: Mapping[str, Any],
    *,
    root: Path,
    current: datetime,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Run unmodified stakeholder and design audits against the proposed state."""

    with tempfile.TemporaryDirectory(prefix="aureon-copy-governance-audit-") as raw:
        shadow = Path(raw)
        (shadow / "aureon").mkdir()
        (shadow / "pyproject.toml").write_bytes(b"# temporary audit root\n")
        for relative in sorted(_shadow_dependency_paths(register, feedback, brief, root=root)):
            _copy_shadow_dependency(root, shadow, relative)
        register_path = shadow / REGISTER_PATH
        feedback_path = shadow / FEEDBACK_PATH
        brief_path = shadow / BRIEF_PATH
        register_path.parent.mkdir(parents=True, exist_ok=True)
        register_path.write_bytes(_serialise(register))
        feedback_path.write_bytes(_serialise(feedback))
        brief_path.write_bytes(_serialise(brief))
        feedback_audit = audit_design_stakeholder_feedback(
            feedback,
            feedback_path=feedback_path,
            repo_root=shadow,
            as_of=current,
        )
        design_audit = audit_design_evidence_brief(
            brief,
            brief_path=brief_path,
            repo_root=shadow,
            as_of=current,
        )
        return feedback_audit, design_audit


def _preflight_or_raise(
    decision: _Decision,
    *,
    root: Path,
    current: datetime,
) -> _ApplicationPlan:
    if decision.state != APPROVE_STATE:
        raise InvestorCopyGovernanceError(
            "decision-not-approved", "Owner decision is not the exact approve state."
        )
    proposal, validation, base_proposal = _proposal_and_validation(root=root, current=current)
    _assert_decision_causal(
        decision,
        proposal=proposal,
        validation=validation,
    )
    delta = _validate_proposal_boundary(proposal)
    (
        register,
        feedback,
        brief,
        register_before,
        feedback_before,
        brief_before,
    ) = _canonical_inputs(proposal, root=root)
    _revalidate_bound_sources(proposal, base_proposal, root=root)
    base_delta = _mapping(
        base_proposal.get("proposed_canonical_delta"),
        label="Superseded canonical delta",
    )
    proposed_register, register_bytes = _build_register(
        register,
        delta=base_delta,
        correction_delta=delta,
    )
    proposed_feedback, feedback_bytes = _build_feedback(feedback, delta=delta)
    proposed_brief, brief_bytes = _build_brief(brief, delta=delta)
    if (
        register_bytes == register_before
        or feedback_bytes == feedback_before
        or brief_bytes == brief_before
        or [
            REGISTER_PATH.as_posix(),
            FEEDBACK_PATH.as_posix(),
            BRIEF_PATH.as_posix(),
        ]
        != CANONICAL_GOVERNANCE_PATHS
    ):
        raise InvestorCopyGovernanceError(
            "changed-file-set", "Exact three-file governance delta was not proven."
        )
    claim_audit = audit_public_claim_evidence(
        proposed_register,
        repo_root=root,
        as_of=current.date(),
    )
    if claim_audit.get("passed") is not True:
        finding_codes = sorted(
            {
                str(item.get("code"))
                for item in claim_audit.get("findings", [])
                if isinstance(item, Mapping) and item.get("severity") == "error"
            }
        )
        raise InvestorCopyGovernanceError(
            "claim-audit",
            "Proposed claim register does not pass its full source audit.",
            details=finding_codes,
        )
    route_capsule = _route_capsule(proposed_register, proposed_brief, root=root)
    feedback_audit, design_audit = _shadow_full_audits(
        proposed_register,
        proposed_feedback,
        proposed_brief,
        root=root,
        current=current,
    )
    if feedback_audit.get("passed") is not True:
        failed_checks = sorted(
            str(item.get("id"))
            for item in feedback_audit.get("checks", [])
            if isinstance(item, Mapping) and item.get("passed") is not True
        )
        raise InvestorCopyGovernanceError(
            "stakeholder-feedback-audit",
            "Proposed stakeholder feedback does not pass the unmodified full audit.",
            details=failed_checks,
        )
    if design_audit.get("passed") is not True:
        failed_checks = sorted(
            str(item.get("id"))
            for item in design_audit.get("checks", [])
            if isinstance(item, Mapping) and item.get("passed") is not True
        )
        raise InvestorCopyGovernanceError(
            "design-brief-audit",
            "Proposed design brief does not pass the unmodified full audit.",
            details=failed_checks,
        )
    if (
        _file_sha256(_repo_file(root, REGISTER_PATH.as_posix(), label="Claim register"))
        != EXPECTED_REGISTER_BEFORE_SHA256
        or _file_sha256(_repo_file(root, FEEDBACK_PATH.as_posix(), label="Stakeholder feedback"))
        != EXPECTED_FEEDBACK_BEFORE_SHA256
        or _file_sha256(_repo_file(root, BRIEF_PATH.as_posix(), label="Design brief"))
        != EXPECTED_BRIEF_BEFORE_SHA256
        or _file_sha256(_repo_file(root, POLICY_PATH.as_posix(), label="Copy policy"))
        != EXPECTED_POLICY_SHA256
        or _file_sha256(_repo_file(root, TARGET_PATH.as_posix(), label="Target HTML"))
        != EXPECTED_TARGET_SHA256
        or _file_sha256(
            _repo_file(
                root,
                EXPECTED_DESIGN_RECEIPT_PATH.as_posix(),
                label="Design-cycle receipt",
            )
        )
        != EXPECTED_DESIGN_RECEIPT_SHA256
        or _file_sha256(
            _repo_file(
                root,
                EXPECTED_PROJECTS_SOURCE_PATH.as_posix(),
                label="Projects positioning source",
            )
        )
        != EXPECTED_PROJECTS_SOURCE_SHA256
        or _file_sha256(
            _repo_file(
                root,
                EXPECTED_COMPANY_PLATFORM_PATH.as_posix(),
                label="Company platform source",
            )
        )
        != EXPECTED_COMPANY_PLATFORM_SHA256
    ):
        raise InvestorCopyGovernanceError(
            "preflight-race", "A bound canonical or public input changed during preflight."
        )
    if (
        _file_sha256(decision.path) != decision.sha256
        or _file_sha256(root / DEFAULT_PROPOSAL_PATH) != EXPECTED_PROPOSAL_SHA256
        or _file_sha256(root / DEFAULT_VALIDATION_PATH) != EXPECTED_VALIDATION_SHA256
        or _file_sha256(root / SUPERSEDED_PROPOSAL_PATH) != SUPERSEDED_PROPOSAL_SHA256
        or _file_sha256(root / SUPERSEDED_VALIDATION_PATH) != SUPERSEDED_VALIDATION_SHA256
        or _file_sha256(root / SUPERSEDED_V2_PROPOSAL_PATH) != SUPERSEDED_V2_PROPOSAL_SHA256
        or _file_sha256(root / SUPERSEDED_V2_VALIDATION_PATH) != SUPERSEDED_V2_VALIDATION_SHA256
        or _file_sha256(root / SUPERSEDED_V3_PROPOSAL_PATH) != SUPERSEDED_V3_PROPOSAL_SHA256
        or _file_sha256(root / SUPERSEDED_V3_VALIDATION_PATH) != SUPERSEDED_V3_VALIDATION_SHA256
        or _file_sha256(root / SUPERSEDED_V4_PROPOSAL_PATH) != SUPERSEDED_V4_PROPOSAL_SHA256
        or _file_sha256(root / SUPERSEDED_V4_VALIDATION_PATH) != SUPERSEDED_V4_VALIDATION_SHA256
    ):
        raise InvestorCopyGovernanceError(
            "approval-race", "Decision, proposal, or validation changed during preflight."
        )
    return _ApplicationPlan(
        decision=decision,
        proposal=proposal,
        validation=validation,
        register=proposed_register,
        feedback=proposed_feedback,
        brief=proposed_brief,
        register_bytes=register_bytes,
        feedback_bytes=feedback_bytes,
        brief_bytes=brief_bytes,
        route_capsule=route_capsule,
        claim_audit=claim_audit,
        feedback_audit=feedback_audit,
        design_audit=design_audit,
    )


def plan_investor_copy_governance_application(
    decision_path: Path,
    *,
    repo_root: Path | None = None,
    as_of: datetime | None = None,
) -> dict[str, Any]:
    """Plan and fully simulate the exact governance delta without canonical writes."""

    root = _find_repo_root(repo_root)
    current = _now(as_of)
    decision_id = ""
    decision_sha256 = ""
    decision_state = ""
    blocked_codes: list[str] = []
    blocked_details: list[str] = []
    try:
        _assert_no_pending_transaction(root)
        decision = _decision_or_raise(decision_path, root=root, current=current)
        decision_id = decision.decision_id
        decision_sha256 = decision.sha256
        decision_state = decision.state
        if decision.state != APPROVE_STATE:
            blocked_codes = [f"decision-{decision.state}"]
            passed = False
        else:
            _preflight_or_raise(decision, root=root, current=current)
            passed = True
    except InvestorCopyGovernanceError as exc:
        passed = False
        blocked_codes = [exc.code]
        blocked_details = list(exc.details)
    return {
        "schema": PLAN_SCHEMA,
        "planned_at": _iso(current),
        "state": "pass" if passed else "blocked",
        "passed": passed,
        "decision_id": decision_id,
        "decision_sha256": decision_sha256,
        "decision_state": decision_state,
        "proposal": {
            "path": DEFAULT_PROPOSAL_PATH.as_posix(),
            "sha256": EXPECTED_PROPOSAL_SHA256,
        },
        "validation": {
            "path": DEFAULT_VALIDATION_PATH.as_posix(),
            "sha256": EXPECTED_VALIDATION_SHA256,
        },
        "canonical_changes": [
            {
                "path": REGISTER_PATH.as_posix(),
                "before_sha256": EXPECTED_REGISTER_BEFORE_SHA256,
                "after_sha256": EXPECTED_REGISTER_AFTER_SHA256,
            },
            {
                "path": FEEDBACK_PATH.as_posix(),
                "before_sha256": EXPECTED_FEEDBACK_BEFORE_SHA256,
                "after_sha256": EXPECTED_FEEDBACK_AFTER_SHA256,
            },
            {
                "path": BRIEF_PATH.as_posix(),
                "before_sha256": EXPECTED_BRIEF_BEFORE_SHA256,
                "after_sha256": EXPECTED_BRIEF_AFTER_SHA256,
            },
        ],
        "policy_change": False,
        "website_change": False,
        "route_capsule_sha256": EXPECTED_ROUTE_CAPSULE_SHA256,
        "satisfied_concept_ids": list(EXPECTED_SATISFIED_CONCEPT_IDS),
        "blocked_codes": blocked_codes,
        "blocked_details": blocked_details,
        "canonical_mutation": False,
        "authority": dict(NON_RELEASE_AUTHORITY),
    }


def _stage_bytes(destination: Path, value: bytes) -> Path:
    handle, raw_path = tempfile.mkstemp(
        prefix=f".{destination.name}.governance.",
        suffix=".tmp",
        dir=str(destination.parent),
    )
    staged = Path(raw_path)
    try:
        with open(handle, "wb", closefd=True) as stream:
            stream.write(value)
            stream.flush()
            os.fsync(stream.fileno())
    except BaseException:
        staged.unlink(missing_ok=True)
        raise
    return staged


def _replace_file(
    source: Path,
    destination: Path,
    *,
    expected_before_sha256: str | None = None,
    expected_after_sha256: str | None = None,
    guards: Sequence[tuple[Path, str]] = (),
) -> None:
    """CAS-check and replace one file; also serves as the fault-injection seam."""

    if expected_before_sha256 is not None:
        if _file_sha256(destination) != expected_before_sha256:
            raise InvestorCopyGovernanceError(
                "commit-cas-mismatch",
                "Destination changed before its exact replacement.",
            )
        for guarded_path, guarded_sha256 in guards:
            if _file_sha256(guarded_path) != guarded_sha256:
                raise InvestorCopyGovernanceError(
                    "commit-cas-mismatch",
                    "A bound transaction input changed before replacement.",
                )
    os.replace(source, destination)
    if expected_after_sha256 is not None and _file_sha256(destination) != expected_after_sha256:
        raise InvestorCopyGovernanceError(
            "commit-cas-mismatch",
            "Destination failed exact post-replacement read-back.",
        )


def _restore_bytes(destination: Path, value: bytes) -> None:
    staged = _stage_bytes(destination, value)
    try:
        _replace_file(staged, destination)
    finally:
        staged.unlink(missing_ok=True)


def _acquire_transaction_lock(
    root: Path,
    *,
    decision_sha256: str,
    current: datetime,
) -> tuple[Path, bytes]:
    """Create one fail-closed, cross-process lock for cooperating writers."""

    _controlled_directory(
        root,
        TRANSACTION_LOCK_PATH.parent,
        label="Governance data directory",
    )
    path = root / TRANSACTION_LOCK_PATH
    value = _serialise(
        {
            "schema": "aureon.investor-copy-governance-transaction-lock.v1",
            "created_at": _iso(current),
            "decision_sha256": decision_sha256,
            "pid": os.getpid(),
            "token": uuid.uuid4().hex,
        }
    )
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    try:
        handle = os.open(path, flags, 0o600)
    except FileExistsError as exc:
        raise InvestorCopyGovernanceError(
            "transaction-lock",
            "Another or a stale governance transaction lock exists.",
        ) from exc
    try:
        with os.fdopen(handle, "wb", closefd=True) as stream:
            stream.write(value)
            stream.flush()
            os.fsync(stream.fileno())
    except BaseException:
        path.unlink(missing_ok=True)
        raise
    return path, value


def _release_transaction_lock(path: Path, value: bytes) -> bool:
    """Remove only the exact lock created by this process."""

    try:
        if path.read_bytes() != value:
            return False
        path.unlink()
        return not path.exists()
    except OSError:
        return False


def _fsync_directory(path: Path) -> None:
    """Best-effort directory metadata flush (unsupported on some Windows builds)."""

    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
    try:
        handle = os.open(path, flags)
    except OSError:
        return
    try:
        os.fsync(handle)
    except OSError:
        pass
    finally:
        os.close(handle)


def _write_exclusive_bytes(path: Path, value: bytes) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    handle = os.open(path, flags, 0o600)
    try:
        with os.fdopen(handle, "wb", closefd=True) as stream:
            stream.write(value)
            stream.flush()
            os.fsync(stream.fileno())
    except BaseException:
        path.unlink(missing_ok=True)
        raise
    _fsync_directory(path.parent)


def _transaction_specs() -> list[dict[str, str]]:
    return [
        {
            "path": REGISTER_PATH.as_posix(),
            "before_sha256": EXPECTED_REGISTER_BEFORE_SHA256,
            "after_sha256": EXPECTED_REGISTER_AFTER_SHA256,
            "before_file": "register.before.json",
            "after_file": "register.after.json",
            "stage_file": "register.stage.json",
        },
        {
            "path": FEEDBACK_PATH.as_posix(),
            "before_sha256": EXPECTED_FEEDBACK_BEFORE_SHA256,
            "after_sha256": EXPECTED_FEEDBACK_AFTER_SHA256,
            "before_file": "feedback.before.json",
            "after_file": "feedback.after.json",
            "stage_file": "feedback.stage.json",
        },
        {
            "path": BRIEF_PATH.as_posix(),
            "before_sha256": EXPECTED_BRIEF_BEFORE_SHA256,
            "after_sha256": EXPECTED_BRIEF_AFTER_SHA256,
            "before_file": "brief.before.json",
            "after_file": "brief.after.json",
            "stage_file": "brief.stage.json",
        },
    ]


def _write_transaction_journal(
    root: Path,
    journal: Mapping[str, Any],
    *,
    expected_current: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    transaction_root = _controlled_directory(
        root,
        TRANSACTION_ROOT,
        label="Transaction journal directory",
    )
    value = dict(journal)
    encoded = _serialise(value)
    staged = transaction_root / f".journal-{uuid.uuid4().hex}.tmp"
    _write_exclusive_bytes(staged, encoded)
    destination = root / TRANSACTION_JOURNAL_PATH
    try:
        if expected_current is not None:
            if not destination.exists():
                raise InvestorCopyGovernanceError(
                    "transaction-journal-race",
                    "Transaction journal disappeared before its state transition.",
                )
            current_snapshot = _snapshot_json(
                destination,
                label="Current transaction journal",
                canonical=True,
            )
            if current_snapshot.raw != _serialise(expected_current):
                raise InvestorCopyGovernanceError(
                    "transaction-journal-race",
                    "Transaction journal changed before its state transition.",
                )
        elif destination.exists():
            raise InvestorCopyGovernanceError(
                "transaction-journal-race",
                "Initial transaction journal destination already exists.",
            )
        if (
            _controlled_directory(
                root,
                TRANSACTION_ROOT,
                label="Transaction journal directory",
            )
            != transaction_root
        ):
            raise InvestorCopyGovernanceError(
                "transaction-journal",
                "Transaction journal directory changed before publication.",
            )
        os.replace(staged, destination)
        _fsync_directory(transaction_root)
    finally:
        staged.unlink(missing_ok=True)
    if destination.read_bytes() != encoded:
        raise InvestorCopyGovernanceError(
            "transaction-journal",
            "Transaction journal failed exact read-back.",
        )
    return value


def _read_transaction_journal(root: Path) -> dict[str, Any]:
    _controlled_directory(
        root,
        TRANSACTION_ROOT,
        label="Transaction journal directory",
    )
    journal_path = _repo_file(
        root,
        TRANSACTION_JOURNAL_PATH.as_posix(),
        label="Transaction journal",
    )
    snapshot = _snapshot_json(
        journal_path,
        label="Transaction journal",
        canonical=True,
    )
    journal = snapshot.value
    if journal.get("schema") != "aureon.investor-copy-governance-transaction.v1":
        raise InvestorCopyGovernanceError(
            "transaction-journal",
            "Transaction journal schema is unsupported.",
        )
    return journal


def _validated_transaction_entries(journal: Mapping[str, Any]) -> list[dict[str, str]]:
    raw_entries = journal.get("files")
    expected = _transaction_specs()
    if not isinstance(raw_entries, list) or len(raw_entries) != len(expected):
        raise InvestorCopyGovernanceError(
            "transaction-journal",
            "Transaction journal file manifest changed.",
        )
    entries: list[dict[str, str]] = []
    for index, expected_entry in enumerate(expected):
        item = _mapping(raw_entries[index], label="Transaction file manifest entry")
        if item != expected_entry:
            raise InvestorCopyGovernanceError(
                "transaction-journal",
                "Transaction journal file manifest changed.",
            )
        entries.append({str(key): str(value) for key, value in item.items()})
    return entries


def _set_transaction_state(
    root: Path,
    journal: Mapping[str, Any],
    state: str,
    *,
    completed_replacements: int | None = None,
    extra: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    updated = dict(journal)
    updated["state"] = state
    if completed_replacements is not None:
        updated["completed_replacements"] = completed_replacements
    if extra:
        updated.update(dict(extra))
    return _write_transaction_journal(
        root,
        updated,
        expected_current=journal,
    )


def _prepare_transaction_journal(
    plan: _ApplicationPlan,
    *,
    root: Path,
    current: datetime,
    lock_value: bytes,
    expected_receipt: Mapping[str, Any],
) -> dict[str, Any]:
    """Durably record exact before/after images before the first canonical write."""

    transaction_root = root / TRANSACTION_ROOT
    try:
        _controlled_directory(
            root,
            TRANSACTION_ROOT.parent,
            label="Governance data directory",
        )
        transaction_root.mkdir()
    except FileExistsError as exc:
        raise InvestorCopyGovernanceError(
            "transaction-journal",
            "An incomplete or stale governance transaction journal exists.",
        ) from exc
    _fsync_directory(transaction_root.parent)
    receipt_path = DEFAULT_RECEIPT_ROOT / f"{plan.decision.decision_id}-application.json"
    receipt_bytes = _serialise(expected_receipt)
    journal = {
        "schema": "aureon.investor-copy-governance-transaction.v1",
        "transaction_id": f"copy-governance-{uuid.uuid4().hex}",
        "created_at": _iso(current),
        "state": "PREPARING",
        "completed_replacements": 0,
        "pid": os.getpid(),
        "decision": {
            "path": plan.decision.path.relative_to(root).as_posix(),
            "sha256": plan.decision.sha256,
            "decision_id": plan.decision.decision_id,
        },
        "proposal": {
            "path": DEFAULT_PROPOSAL_PATH.as_posix(),
            "sha256": EXPECTED_PROPOSAL_SHA256,
        },
        "validation": {
            "path": DEFAULT_VALIDATION_PATH.as_posix(),
            "sha256": EXPECTED_VALIDATION_SHA256,
        },
        "lock": {
            "path": TRANSACTION_LOCK_PATH.as_posix(),
            "sha256": _bytes_sha256(lock_value),
        },
        "files": _transaction_specs(),
        "receipt": {
            "path": receipt_path.as_posix(),
            "sha256": _bytes_sha256(receipt_bytes),
            "stage_file": "application-receipt.stage.json",
        },
    }
    journal = _write_transaction_journal(root, journal)
    before_values = [
        (root / REGISTER_PATH).read_bytes(),
        (root / FEEDBACK_PATH).read_bytes(),
        (root / BRIEF_PATH).read_bytes(),
    ]
    after_values = [
        plan.register_bytes,
        plan.feedback_bytes,
        plan.brief_bytes,
    ]
    try:
        for entry, before_value, after_value in zip(
            _transaction_specs(),
            before_values,
            after_values,
            strict=True,
        ):
            if (
                _bytes_sha256(before_value) != entry["before_sha256"]
                or _bytes_sha256(after_value) != entry["after_sha256"]
            ):
                raise InvestorCopyGovernanceError(
                    "transaction-journal",
                    "Transaction backup image does not match its exact manifest hash.",
                )
            _write_exclusive_bytes(
                transaction_root / entry["before_file"],
                before_value,
            )
            _write_exclusive_bytes(
                transaction_root / entry["after_file"],
                after_value,
            )
        for entry in _transaction_specs():
            if (
                _file_sha256(transaction_root / entry["before_file"]) != entry["before_sha256"]
                or _file_sha256(transaction_root / entry["after_file"]) != entry["after_sha256"]
            ):
                raise InvestorCopyGovernanceError(
                    "transaction-journal",
                    "Transaction image failed exact durable read-back.",
                )
        _write_exclusive_bytes(
            transaction_root / "application-receipt.stage.json",
            receipt_bytes,
        )
        if _file_sha256(transaction_root / "application-receipt.stage.json") != _bytes_sha256(receipt_bytes):
            raise InvestorCopyGovernanceError(
                "transaction-journal",
                "Application receipt publish image failed exact durable read-back.",
            )
        _fsync_directory(transaction_root)
        return _set_transaction_state(
            root,
            journal,
            "PREPARED",
            completed_replacements=0,
        )
    except BaseException:
        # The PREPARING journal is intentionally retained for recovery.
        raise


def _pid_is_alive(value: object) -> bool:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        return False
    if value == os.getpid():
        return True
    if os.name == "nt":
        # ``os.kill(pid, 0)`` can report an already-exited Windows PID as
        # alive.  Query the process exit code through a real process handle.
        import ctypes

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        open_process = kernel32.OpenProcess
        open_process.argtypes = [ctypes.c_ulong, ctypes.c_int, ctypes.c_ulong]
        open_process.restype = ctypes.c_void_p
        get_exit_code = kernel32.GetExitCodeProcess
        get_exit_code.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_ulong)]
        get_exit_code.restype = ctypes.c_int
        close_handle = kernel32.CloseHandle
        close_handle.argtypes = [ctypes.c_void_p]
        close_handle.restype = ctypes.c_int
        handle = open_process(0x1000, 0, value)
        if not handle:
            # Access denied means a process exists but is outside our query
            # rights; other failures are treated as absent.
            return ctypes.get_last_error() == 5
        try:
            exit_code = ctypes.c_ulong()
            if not get_exit_code(handle, ctypes.byref(exit_code)):
                return True
            return exit_code.value == 259
        finally:
            close_handle(handle)
    try:
        os.kill(value, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True


def _validate_transaction_journal_bindings(
    journal: Mapping[str, Any],
) -> tuple[list[dict[str, str]], str, dict[str, str], dict[str, str]]:
    states = {
        "PREPARING",
        "PREPARED",
        "COMMITTING",
        "VALIDATING",
        "VALIDATED",
        "RECOVERING",
        "COMMITTED",
        "ROLLED_BACK",
        "BLOCKED",
    }
    if journal.get("state") not in states:
        raise InvestorCopyGovernanceError(
            "transaction-journal",
            "Transaction journal state is unsupported.",
        )
    transaction_id = _safe_identifier(
        journal.get("transaction_id"),
        label="Transaction id",
    )
    if (
        not isinstance(journal.get("pid"), int)
        or isinstance(journal.get("pid"), bool)
        or not isinstance(journal.get("completed_replacements"), int)
        or not 0 <= int(journal.get("completed_replacements", -1)) <= 3
    ):
        raise InvestorCopyGovernanceError(
            "transaction-journal",
            "Transaction process or progress binding is malformed.",
        )
    proposal = _binding(journal.get("proposal"), label="Transaction proposal binding")
    validation = _binding(
        journal.get("validation"),
        label="Transaction validation binding",
    )
    if proposal != {
        "path": DEFAULT_PROPOSAL_PATH.as_posix(),
        "sha256": EXPECTED_PROPOSAL_SHA256,
    } or validation != {
        "path": DEFAULT_VALIDATION_PATH.as_posix(),
        "sha256": EXPECTED_VALIDATION_SHA256,
    }:
        raise InvestorCopyGovernanceError(
            "transaction-journal",
            "Transaction approval artifact binding changed.",
        )
    lock = _mapping(journal.get("lock"), label="Transaction lock binding")
    if (
        set(lock) != {"path", "sha256"}
        or _safe_relative(lock.get("path"), label="Transaction lock path") != TRANSACTION_LOCK_PATH.as_posix()
    ):
        raise InvestorCopyGovernanceError(
            "transaction-journal",
            "Transaction lock binding changed.",
        )
    _safe_sha256(lock.get("sha256"), label="Transaction lock SHA-256")
    receipt = _mapping(journal.get("receipt"), label="Transaction receipt binding")
    if (
        set(receipt) != {"path", "sha256", "stage_file"}
        or receipt.get("stage_file") != "application-receipt.stage.json"
    ):
        raise InvestorCopyGovernanceError(
            "transaction-journal",
            "Transaction receipt binding changed.",
        )
    receipt_path = _safe_relative(
        receipt.get("path"),
        label="Transaction receipt path",
    )
    if Path(receipt_path).parent != DEFAULT_RECEIPT_ROOT:
        raise InvestorCopyGovernanceError(
            "transaction-journal",
            "Transaction receipt escaped the immutable receipt root.",
        )
    receipt_binding = {
        "path": receipt_path,
        "sha256": _safe_sha256(
            receipt.get("sha256"),
            label="Transaction receipt SHA-256",
        ),
        "stage_file": "application-receipt.stage.json",
    }
    decision = _mapping(journal.get("decision"), label="Transaction decision binding")
    if set(decision) != {"path", "sha256", "decision_id"}:
        raise InvestorCopyGovernanceError(
            "transaction-journal",
            "Transaction decision binding changed.",
        )
    decision_path = _safe_relative(
        decision.get("path"),
        label="Transaction decision path",
    )
    if Path(decision_path).parent != DEFAULT_DECISION_ROOT:
        raise InvestorCopyGovernanceError(
            "transaction-journal",
            "Transaction decision escaped the controlled decision root.",
        )
    decision_binding = {
        "path": decision_path,
        "sha256": _safe_sha256(
            decision.get("sha256"),
            label="Transaction decision SHA-256",
        ),
        "decision_id": _safe_identifier(
            decision.get("decision_id"),
            label="Transaction decision id",
        ),
    }
    expected_receipt_path = (
        DEFAULT_RECEIPT_ROOT / f"{decision_binding['decision_id']}-application.json"
    ).as_posix()
    if receipt_binding["path"] != expected_receipt_path:
        raise InvestorCopyGovernanceError(
            "transaction-journal",
            "Transaction receipt does not match its exact decision id.",
        )
    return (
        _validated_transaction_entries(journal),
        transaction_id,
        receipt_binding,
        decision_binding,
    )


def _remove_bound_transaction_lock(
    root: Path,
    journal: Mapping[str, Any],
) -> bool:
    lock_path = root / TRANSACTION_LOCK_PATH
    if not lock_path.exists():
        return True
    try:
        controlled_lock = _repo_file(
            root,
            TRANSACTION_LOCK_PATH.as_posix(),
            label="Transaction lock",
        )
        value = controlled_lock.read_bytes()
        lock = _mapping(journal.get("lock"), label="Transaction lock binding")
        if _bytes_sha256(value) != lock.get("sha256"):
            return False
        controlled_lock.unlink()
        _fsync_directory(controlled_lock.parent)
        return not lock_path.exists()
    except (InvestorCopyGovernanceError, OSError):
        return False


def _cleanup_transaction_root(root: Path) -> bool:
    lexical = root / TRANSACTION_ROOT
    if not lexical.exists():
        return True
    try:
        transaction_root = _controlled_directory(
            root,
            TRANSACTION_ROOT,
            label="Transaction journal directory",
        )
    except InvestorCopyGovernanceError:
        return False
    allowed = {
        "journal.json",
        "application-receipt.stage.json",
        "recovery-receipt.stage.json",
        "recovery-receipt.stage.json.building",
    }
    for entry in _transaction_specs():
        allowed.update(
            {
                entry["before_file"],
                entry["after_file"],
                entry["stage_file"],
                f"{entry['stage_file']}.building",
            }
        )
    try:
        children = list(transaction_root.iterdir())
        for child in children:
            if child.name not in allowed and re.fullmatch(r"\.journal-[a-f0-9]{32}\.tmp", child.name) is None:
                return False
            if child.is_dir() or _is_link_or_reparse(child):
                return False
        for child in children:
            child.unlink(missing_ok=True)
        transaction_root.rmdir()
        _fsync_directory(transaction_root.parent)
        return not transaction_root.exists()
    except OSError:
        return False


def _prepare_fixed_bytes(stage: Path, value: bytes) -> None:
    expected_sha256 = _bytes_sha256(value)
    if stage.exists():
        if _is_link_or_reparse(stage) or not stage.is_file() or stage.stat().st_nlink != 1:
            raise InvestorCopyGovernanceError(
                "receipt-stage",
                "Receipt publish stage is unsafe.",
            )
        if _file_sha256(stage) == expected_sha256:
            return
    building = stage.with_name(f"{stage.name}.building")
    if building.exists():
        if _is_link_or_reparse(building) or not building.is_file() or building.stat().st_nlink != 1:
            raise InvestorCopyGovernanceError(
                "receipt-stage",
                "Receipt publish build stage is unsafe.",
            )
        building.unlink()
    _write_exclusive_bytes(building, value)
    if _file_sha256(building) != expected_sha256:
        raise InvestorCopyGovernanceError(
            "receipt-stage",
            "Receipt publish build stage failed exact read-back.",
        )
    os.replace(building, stage)
    _fsync_directory(stage.parent)
    if _file_sha256(stage) != expected_sha256:
        raise InvestorCopyGovernanceError(
            "receipt-stage",
            "Receipt publish stage failed exact read-back.",
        )


def _normalise_known_receipt_alias(
    destination: Path,
    stage: Path,
    *,
    expected_sha256: str,
    label: str,
) -> Path | None:
    """Remove only the journal-known same-inode alias, then require nlink one."""

    if not destination.exists():
        return None
    if _is_link_or_reparse(destination) or not destination.is_file():
        return None
    if stage.exists():
        if _is_link_or_reparse(stage) or not stage.is_file():
            return None
        try:
            same_file = os.path.samefile(stage, destination)
        except OSError:
            return None
        if not same_file or _file_sha256(stage) != expected_sha256:
            return None
        stage.unlink()
        _fsync_directory(stage.parent)
    try:
        details = destination.lstat()
    except OSError:
        return None
    if not stat.S_ISREG(details.st_mode) or details.st_nlink != 1:
        return None
    snapshot = _snapshot_json(destination, label=label, canonical=True)
    if snapshot.sha256 != expected_sha256:
        return None
    return destination.resolve(strict=True)


def _write_immutable_recovery_receipt(
    receipt: Mapping[str, Any],
    *,
    root: Path,
) -> Path:
    destination_parent = _controlled_directory_create_leaf(
        root,
        DEFAULT_RECOVERY_RECEIPT_ROOT,
        label="Recovery receipt root",
    )
    transaction_root = _controlled_directory(
        root,
        TRANSACTION_ROOT,
        label="Transaction journal directory",
    )
    transaction_id = _safe_identifier(
        receipt.get("transaction_id"),
        label="Recovery transaction id",
    )
    outcome = receipt.get("outcome")
    if outcome not in {"committed", "rolled-back"}:
        raise InvestorCopyGovernanceError(
            "recovery-receipt",
            "Recovery receipt outcome is unsupported.",
        )
    destination = destination_parent / f"{transaction_id}-{outcome}.json"
    value = _serialise(receipt)
    expected_sha256 = _bytes_sha256(value)
    staged = transaction_root / "recovery-receipt.stage.json"
    if destination.exists():
        existing = _normalise_known_receipt_alias(
            destination,
            staged,
            expected_sha256=expected_sha256,
            label="Recovery receipt",
        )
        if existing is None:
            raise InvestorCopyGovernanceError(
                "recovery-receipt-exists",
                "A different immutable recovery receipt already exists.",
            )
        return existing
    _prepare_fixed_bytes(staged, value)
    try:
        try:
            if (
                _controlled_directory(
                    root,
                    DEFAULT_RECOVERY_RECEIPT_ROOT,
                    label="Recovery receipt root",
                )
                != destination_parent
            ):
                raise InvestorCopyGovernanceError(
                    "recovery-receipt-root",
                    "Recovery receipt root changed before publication.",
                )
            os.link(staged, destination)
        except FileExistsError as exc:
            existing = _normalise_known_receipt_alias(
                destination,
                staged,
                expected_sha256=expected_sha256,
                label="Recovery receipt",
            )
            if existing is None:
                raise InvestorCopyGovernanceError(
                    "recovery-receipt-exists",
                    "A different immutable recovery receipt already exists.",
                ) from exc
            return existing
        staged.unlink()
        _fsync_directory(transaction_root)
        _fsync_directory(destination_parent)
        written = _normalise_known_receipt_alias(
            destination,
            staged,
            expected_sha256=expected_sha256,
            label="Recovery receipt",
        )
        if written is None:
            raise InvestorCopyGovernanceError(
                "recovery-receipt-readback",
                "Recovery receipt failed exact read-back.",
            )
        return written
    except BaseException:
        # Journal-bound stage/destination are retained for deterministic recovery.
        raise


def _recovery_receipt_value(
    journal: Mapping[str, Any],
    *,
    outcome: str,
    recovered_at: str,
    preserved_paths: Sequence[str] = (),
) -> dict[str, Any]:
    files = _validated_transaction_entries(journal)
    return {
        "schema": "aureon.investor-copy-governance-recovery.v1",
        "transaction_id": journal["transaction_id"],
        "recovered_at": recovered_at,
        "outcome": outcome,
        "decision": dict(_mapping(journal.get("decision"), label="Recovery decision binding")),
        "proposal": {
            "path": DEFAULT_PROPOSAL_PATH.as_posix(),
            "sha256": EXPECTED_PROPOSAL_SHA256,
        },
        "validation": {
            "path": DEFAULT_VALIDATION_PATH.as_posix(),
            "sha256": EXPECTED_VALIDATION_SHA256,
        },
        "canonical_files": [
            {
                "path": entry["path"],
                "before_sha256": entry["before_sha256"],
                "after_sha256": entry["after_sha256"],
            }
            for entry in files
        ],
        "preserved_foreign_paths": list(preserved_paths),
        "policy_change": False,
        "website_change": False,
        "release_eligible": False,
        "authority": dict(NON_RELEASE_AUTHORITY),
    }


def _pending_transaction_exists(root: Path) -> bool:
    return (root / TRANSACTION_ROOT).exists() or (root / TRANSACTION_LOCK_PATH).exists()


def _assert_no_pending_transaction(root: Path) -> None:
    if _pending_transaction_exists(root):
        raise InvestorCopyGovernanceError(
            "transaction-recovery-required",
            "A governance transaction journal or lock requires recovery before audit or planning.",
        )


def _orphan_lock_recovery(
    root: Path,
    *,
    allow_current_pid: bool,
) -> dict[str, Any]:
    lock_path = root / TRANSACTION_LOCK_PATH
    if not lock_path.exists():
        return {
            "state": "absent",
            "outcome": "absent",
            "blocked_codes": [],
            "applied": False,
        }
    try:
        lock_file = _repo_file(
            root,
            TRANSACTION_LOCK_PATH.as_posix(),
            label="Orphan transaction lock",
        )
        lock_snapshot = _snapshot_json(
            lock_file,
            label="Orphan transaction lock",
            canonical=True,
        )
        lock_bytes = lock_snapshot.raw
        lock = lock_snapshot.value
        if (
            lock.get("schema") != "aureon.investor-copy-governance-transaction-lock.v1"
            or not isinstance(lock.get("pid"), int)
            or isinstance(lock.get("pid"), bool)
            or not isinstance(lock.get("token"), str)
        ):
            raise InvestorCopyGovernanceError(
                "transaction-lock",
                "Orphan transaction lock is malformed.",
            )
        pid = int(lock["pid"])
        if _pid_is_alive(pid) and not (allow_current_pid and pid == os.getpid()):
            return {
                "state": "blocked",
                "outcome": "active",
                "blocked_codes": ["transaction-active"],
                "applied": False,
            }
        if lock_file.read_bytes() != lock_bytes:
            raise InvestorCopyGovernanceError(
                "transaction-lock",
                "Orphan transaction lock changed during recovery.",
            )
        lock_file.unlink()
        _fsync_directory(lock_file.parent)
        return {
            "state": "recovered",
            "outcome": "orphan-lock-cleared",
            "blocked_codes": [],
            "applied": False,
        }
    except (InvestorCopyGovernanceError, OSError) as exc:
        code = exc.code if isinstance(exc, InvestorCopyGovernanceError) else "transaction-lock"
        return {
            "state": "blocked",
            "outcome": "blocked",
            "blocked_codes": [code],
            "applied": False,
        }


def _prepare_fixed_stage(
    source: Path,
    stage: Path,
    *,
    expected_sha256: str,
) -> None:
    if _file_sha256(source) != expected_sha256:
        raise InvestorCopyGovernanceError(
            "transaction-backup-drift",
            "A durable transaction image changed.",
        )
    if stage.exists():
        if _is_link_or_reparse(stage) or not stage.is_file() or stage.stat().st_nlink != 1:
            raise InvestorCopyGovernanceError(
                "transaction-stage",
                "A transaction stage path is unsafe.",
            )
        if _file_sha256(stage) == expected_sha256:
            return
    building = stage.with_name(f"{stage.name}.building")
    if building.exists():
        if _is_link_or_reparse(building) or not building.is_file() or building.stat().st_nlink != 1:
            raise InvestorCopyGovernanceError(
                "transaction-stage",
                "A transaction stage build path is unsafe.",
            )
        building.unlink()
    _write_exclusive_bytes(building, source.read_bytes())
    if _file_sha256(building) != expected_sha256:
        raise InvestorCopyGovernanceError(
            "transaction-stage",
            "A rebuilt transaction stage failed exact read-back.",
        )
    os.replace(building, stage)
    _fsync_directory(stage.parent)
    if _file_sha256(stage) != expected_sha256:
        raise InvestorCopyGovernanceError(
            "transaction-stage",
            "A transaction stage image failed exact read-back.",
        )


def _recover_transaction(
    root: Path,
    *,
    current: datetime,
    allow_current_pid: bool = False,
) -> dict[str, Any]:
    lexical_transaction_root = root / TRANSACTION_ROOT
    if not lexical_transaction_root.exists():
        return _orphan_lock_recovery(
            root,
            allow_current_pid=allow_current_pid,
        )
    try:
        transaction_root = _controlled_directory(
            root,
            TRANSACTION_ROOT,
            label="Transaction journal directory",
        )
    except InvestorCopyGovernanceError:
        return {
            "state": "blocked",
            "outcome": "blocked",
            "blocked_codes": ["transaction-journal"],
            "applied": False,
        }
    journal_path = root / TRANSACTION_JOURNAL_PATH
    if not journal_path.exists():
        # Recover the first journal publication window. A complete canonical
        # temp can be promoted; an incomplete known temp can only be discarded
        # while every canonical file is still at its exact before image.
        try:
            children = list(transaction_root.iterdir())
            journal_temps = [
                child
                for child in children
                if re.fullmatch(r"\.journal-[a-f0-9]{32}\.tmp", child.name) is not None
            ]
            if len(children) == 1 and len(journal_temps) == 1:
                candidate = journal_temps[0]
                try:
                    candidate_snapshot = _snapshot_json(
                        candidate,
                        label="Preparing transaction journal",
                        canonical=True,
                    )
                    candidate_journal = candidate_snapshot.value
                    _validate_transaction_journal_bindings(candidate_journal)
                    if candidate_journal.get("state") != "PREPARING":
                        raise InvestorCopyGovernanceError(
                            "transaction-journal",
                            "Initial journal temp is not in PREPARING state.",
                        )
                    pid = int(candidate_journal["pid"])
                    if _pid_is_alive(pid) and not (allow_current_pid and pid == os.getpid()):
                        return {
                            "state": "blocked",
                            "outcome": "active",
                            "blocked_codes": ["transaction-active"],
                            "applied": False,
                        }
                    os.replace(candidate, journal_path)
                    _fsync_directory(transaction_root)
                    return _recover_transaction(
                        root,
                        current=current,
                        allow_current_pid=allow_current_pid,
                    )
                except InvestorCopyGovernanceError:
                    pass
                before_hashes = [
                    _file_sha256(
                        _repo_file(
                            root,
                            entry["path"],
                            label="Preparing canonical file",
                        )
                    )
                    for entry in _transaction_specs()
                ]
                if before_hashes != [entry["before_sha256"] for entry in _transaction_specs()]:
                    raise InvestorCopyGovernanceError(
                        "transaction-journal",
                        "Incomplete initial journal temp cannot be discarded after a canonical change.",
                    )
            elif children:
                raise InvestorCopyGovernanceError(
                    "transaction-journal",
                    "Transaction directory has content but no durable journal.",
                )
            lock_result = _orphan_lock_recovery(
                root,
                allow_current_pid=allow_current_pid,
            )
            if lock_result["state"] == "blocked":
                return lock_result
            if not _cleanup_transaction_root(root):
                raise InvestorCopyGovernanceError(
                    "transaction-cleanup",
                    "Empty transaction directory could not be removed.",
                )
            return {
                "state": "recovered",
                "outcome": "empty-preparation-cleared",
                "blocked_codes": [],
                "applied": False,
            }
        except (InvestorCopyGovernanceError, OSError) as exc:
            code = exc.code if isinstance(exc, InvestorCopyGovernanceError) else "transaction-journal"
            return {
                "state": "blocked",
                "outcome": "blocked",
                "blocked_codes": [code],
                "applied": False,
            }
    try:
        journal = _read_transaction_journal(root)
        entries, transaction_id, receipt_binding, decision_binding = _validate_transaction_journal_bindings(
            journal
        )
        pid = int(journal["pid"])
        if _pid_is_alive(pid) and not (allow_current_pid and pid == os.getpid()):
            return {
                "state": "blocked",
                "outcome": "active",
                "blocked_codes": ["transaction-active"],
                "applied": False,
            }
        receipt_path = root / receipt_binding["path"]
        receipt_exists = receipt_path.exists()
        receipt_exact = False
        if receipt_exists:
            _controlled_directory(
                root,
                DEFAULT_RECEIPT_ROOT,
                label="Governance receipt root",
            )
            receipt_exact = (
                _normalise_known_receipt_alias(
                    receipt_path,
                    transaction_root / receipt_binding["stage_file"],
                    expected_sha256=receipt_binding["sha256"],
                    label="Application receipt",
                )
                is not None
            )
        observed_hashes: dict[str, str] = {}
        missing_paths: list[str] = []
        for entry in entries:
            try:
                destination = _repo_file(
                    root,
                    entry["path"],
                    label="Recovering canonical file",
                )
                observed_hashes[entry["path"]] = _file_sha256(destination)
            except InvestorCopyGovernanceError:
                missing_paths.append(entry["path"])
        all_after = not missing_paths and all(
            observed_hashes[entry["path"]] == entry["after_sha256"] for entry in entries
        )
        recovered_at = journal.get("recovery_started_at")
        if not isinstance(recovered_at, str):
            recovered_at = _iso(current)
        _timestamp(recovered_at, label="Recovery start")

        if all_after and receipt_exact:
            if (
                _normalise_known_receipt_alias(
                    receipt_path,
                    transaction_root / receipt_binding["stage_file"],
                    expected_sha256=receipt_binding["sha256"],
                    label="Application receipt",
                )
                is None
            ):
                raise InvestorCopyGovernanceError(
                    "receipt-drift",
                    "Application receipt changed before recovery commit.",
                )
            journal = _set_transaction_state(
                root,
                journal,
                "RECOVERING",
                completed_replacements=3,
                extra={
                    "recovery_started_at": recovered_at,
                    "recovery_outcome": "committed",
                },
            )
            recovery_receipt = _write_immutable_recovery_receipt(
                _recovery_receipt_value(
                    journal,
                    outcome="committed",
                    recovered_at=recovered_at,
                ),
                root=root,
            )
            if recovery_receipt.stat().st_nlink != 1 or _file_sha256(recovery_receipt) != _bytes_sha256(
                _serialise(
                    _recovery_receipt_value(
                        journal,
                        outcome="committed",
                        recovered_at=recovered_at,
                    )
                )
            ):
                raise InvestorCopyGovernanceError(
                    "recovery-receipt-drift",
                    "Recovery receipt changed before committed state.",
                )
            journal = _set_transaction_state(
                root,
                journal,
                "COMMITTED",
                completed_replacements=3,
            )
            lock_released = _remove_bound_transaction_lock(root, journal)
            journal_cleaned = lock_released and _cleanup_transaction_root(root)
            maintenance = not lock_released or not journal_cleaned
            return {
                "state": (
                    "applied-governance-maintenance-required" if maintenance else "applied-governance-only"
                ),
                "outcome": "committed",
                "blocked_codes": (
                    ["transaction-lock-release-failed"]
                    if not lock_released
                    else ["transaction-journal-cleanup-failed"]
                    if not journal_cleaned
                    else []
                ),
                "applied": True,
                "decision_id": decision_binding["decision_id"],
                "canonical_changes": [
                    {
                        "path": entry["path"],
                        "before_sha256": entry["before_sha256"],
                        "after_sha256": entry["after_sha256"],
                    }
                    for entry in entries
                ],
                "transaction_lock_released": lock_released,
                "transaction_journal_cleaned": journal_cleaned,
                "receipt_path": receipt_binding["path"],
                "receipt_sha256": receipt_binding["sha256"],
                "recovery_receipt_path": recovery_receipt.relative_to(root).as_posix(),
                "recovery_receipt_sha256": _file_sha256(recovery_receipt),
            }

        journal = _set_transaction_state(
            root,
            journal,
            "RECOVERING",
            extra={
                "recovery_started_at": recovered_at,
                "recovery_outcome": "rolled-back",
            },
        )
        preserved: list[str] = list(missing_paths)
        if receipt_exists:
            if receipt_exact:
                receipt_path.unlink()
                _fsync_directory(receipt_path.parent)
            else:
                preserved.append(receipt_binding["path"])
        for entry in reversed(entries):
            if entry["path"] in missing_paths:
                continue
            destination = _repo_file(
                root,
                entry["path"],
                label="Rollback canonical file",
            )
            observed = observed_hashes.get(entry["path"])
            if observed == entry["before_sha256"]:
                continue
            if observed != entry["after_sha256"]:
                if entry["path"] not in preserved:
                    preserved.append(entry["path"])
                continue
            backup = transaction_root / entry["before_file"]
            stage = transaction_root / entry["stage_file"]
            _prepare_fixed_stage(
                backup,
                stage,
                expected_sha256=entry["before_sha256"],
            )
            destination = _repo_file(
                root,
                entry["path"],
                label="Rollback canonical file before replace",
            )
            _replace_file(
                stage,
                destination,
                expected_before_sha256=entry["after_sha256"],
                expected_after_sha256=entry["before_sha256"],
            )
        for entry in entries:
            if entry["path"] in missing_paths:
                continue
            destination = _repo_file(
                root,
                entry["path"],
                label="Rollback canonical read-back",
            )
            if entry["path"] in preserved:
                continue
            if _file_sha256(destination) != entry["before_sha256"]:
                preserved.append(entry["path"])
        preserved = sorted(set(preserved))
        if preserved:
            journal = _set_transaction_state(
                root,
                journal,
                "BLOCKED",
                extra={"preserved_foreign_paths": preserved},
            )
            lock_released = _remove_bound_transaction_lock(root, journal)
            return {
                "state": "blocked",
                "outcome": "blocked",
                "blocked_codes": [
                    "concurrent-drift-preserved",
                    *([] if lock_released else ["transaction-lock-release-failed"]),
                ],
                "applied": False,
                "transaction_lock_released": lock_released,
                "transaction_journal_cleaned": False,
                "concurrent_drift_preserved_paths": preserved,
            }
        rolled_back_receipt_value = _recovery_receipt_value(
            journal,
            outcome="rolled-back",
            recovered_at=recovered_at,
        )
        recovery_receipt = _write_immutable_recovery_receipt(
            rolled_back_receipt_value,
            root=root,
        )
        if recovery_receipt.stat().st_nlink != 1 or _file_sha256(recovery_receipt) != _bytes_sha256(
            _serialise(rolled_back_receipt_value)
        ):
            raise InvestorCopyGovernanceError(
                "recovery-receipt-drift",
                "Recovery receipt changed before rolled-back state.",
            )
        journal = _set_transaction_state(
            root,
            journal,
            "ROLLED_BACK",
            completed_replacements=0,
        )
        lock_released = _remove_bound_transaction_lock(root, journal)
        journal_cleaned = lock_released and _cleanup_transaction_root(root)
        if not lock_released or not journal_cleaned:
            return {
                "state": "blocked",
                "outcome": "rolled-back",
                "blocked_codes": (
                    ["transaction-lock-release-failed"]
                    if not lock_released
                    else ["transaction-journal-cleanup-failed"]
                ),
                "applied": False,
                "transaction_lock_released": lock_released,
                "transaction_journal_cleaned": journal_cleaned,
                "rollback_verified": True,
                "recovery_receipt_path": recovery_receipt.relative_to(root).as_posix(),
                "recovery_receipt_sha256": _file_sha256(recovery_receipt),
            }
        return {
            "state": "recovered",
            "outcome": "rolled-back",
            "blocked_codes": [],
            "applied": False,
            "transaction_lock_released": True,
            "transaction_journal_cleaned": True,
            "rollback_verified": True,
            "recovery_receipt_path": recovery_receipt.relative_to(root).as_posix(),
            "recovery_receipt_sha256": _file_sha256(recovery_receipt),
        }
    except (InvestorCopyGovernanceError, OSError, ValueError) as exc:
        code = exc.code if isinstance(exc, InvestorCopyGovernanceError) else "transaction-recovery"
        return {
            "state": "blocked",
            "outcome": "blocked",
            "blocked_codes": [code],
            "applied": False,
            "transaction_journal_cleaned": False,
        }


def recover_incomplete_investor_copy_governance_transaction(
    *,
    repo_root: Path | None = None,
) -> dict[str, Any]:
    """Recover a dead cooperative writer using its exact durable journal."""

    root = _find_repo_root(repo_root)
    current = _wall_now()
    result = _recover_transaction(root, current=current)
    return {
        "schema": "aureon.investor-copy-governance-recovery-result.v1",
        "recovered_at": _iso(current),
        **result,
        "policy_change": False,
        "website_change": False,
        "release_eligible": False,
        "authority": dict(NON_RELEASE_AUTHORITY),
    }


def _cleanup_failed_receipt(
    root: Path,
    *,
    decision_id: str,
    decision_sha256: str,
    existed_before: bool,
) -> bool:
    """Remove only a newly created receipt bound to this failed transaction."""

    path = root / DEFAULT_RECEIPT_ROOT / f"{decision_id}-application.json"
    if existed_before or not path.exists():
        return True
    try:
        value = _read_json(
            _regular_file(path, label="Failed application receipt"), label="Failed application receipt"
        )
        decision = _mapping(value.get("decision"), label="Failed receipt decision")
        if (
            value.get("schema") != APPLICATION_SCHEMA
            or value.get("application_id") != f"{decision_id}-application"
            or decision.get("decision_id") != decision_id
            or decision.get("decision_sha256") != decision_sha256
        ):
            return False
        path.unlink()
        return not path.exists()
    except (InvestorCopyGovernanceError, OSError, ValueError):
        return False


def _rollback_owned_outputs(
    entries: Sequence[tuple[Path, bytes | None, str]],
    *,
    root: Path,
) -> tuple[list[str], list[str]]:
    """Restore only exact transaction-owned after-images; preserve other drift."""

    errors: list[str] = []
    preserved: list[str] = []
    for path, original, expected_after_sha256 in reversed(entries):
        if original is None:
            continue
        try:
            observed = path.read_bytes()
            if observed == original:
                continue
            if _bytes_sha256(observed) != expected_after_sha256:
                try:
                    preserved.append(path.relative_to(root).as_posix())
                except ValueError:
                    preserved.append(str(path))
                continue
            _restore_bytes(path, original)
            if path.read_bytes() != original:
                errors.append("rollback-readback")
        except Exception:
            errors.append("rollback-failed")
    return sorted(set(errors)), sorted(set(preserved))


def _post_write_validate(
    plan: _ApplicationPlan,
    *,
    root: Path,
    current: datetime,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    register_path = _repo_file(root, REGISTER_PATH.as_posix(), label="Written claim register")
    feedback_path = _repo_file(root, FEEDBACK_PATH.as_posix(), label="Written stakeholder feedback")
    brief_path = _repo_file(root, BRIEF_PATH.as_posix(), label="Written design brief")
    if (
        register_path.read_bytes() != plan.register_bytes
        or feedback_path.read_bytes() != plan.feedback_bytes
        or brief_path.read_bytes() != plan.brief_bytes
        or _file_sha256(register_path) != EXPECTED_REGISTER_AFTER_SHA256
        or _file_sha256(feedback_path) != EXPECTED_FEEDBACK_AFTER_SHA256
        or _file_sha256(brief_path) != EXPECTED_BRIEF_AFTER_SHA256
    ):
        raise InvestorCopyGovernanceError(
            "post-write-readback", "Written governance bytes failed exact read-back."
        )
    claim_audit = audit_public_claim_evidence_file(repo_root=root, as_of=current.date())
    feedback_audit = audit_design_stakeholder_feedback_file(repo_root=root, as_of=current)
    design_audit = audit_design_evidence_brief_file(repo_root=root, as_of=current)
    if claim_audit.get("passed") is not True:
        raise InvestorCopyGovernanceError("post-write-claim-audit", "Post-write claim audit failed.")
    if feedback_audit.get("passed") is not True:
        failed = sorted(
            str(item.get("id"))
            for item in feedback_audit.get("checks", [])
            if isinstance(item, Mapping) and item.get("passed") is not True
        )
        raise InvestorCopyGovernanceError(
            "post-write-feedback-audit",
            "Post-write stakeholder-feedback audit failed.",
            details=failed,
        )
    if design_audit.get("passed") is not True:
        failed = sorted(
            str(item.get("id"))
            for item in design_audit.get("checks", [])
            if isinstance(item, Mapping) and item.get("passed") is not True
        )
        raise InvestorCopyGovernanceError(
            "post-write-design-audit",
            "Post-write design-brief audit failed.",
            details=failed,
        )
    capsules = design_audit.get("route_claim_capsules")
    if not isinstance(capsules, list):
        raise InvestorCopyGovernanceError("post-write-capsule", "Post-write route capsules are unavailable.")
    matches = [
        item for item in capsules if isinstance(item, Mapping) and item.get("route_id") == TARGET_ROUTE_ID
    ]
    if len(matches) != 1 or _json_sha256(matches[0]) != EXPECTED_ROUTE_CAPSULE_SHA256:
        raise InvestorCopyGovernanceError("post-write-capsule", "Post-write route capsule hash changed.")
    _route_capsule(plan.register, plan.brief, root=root)
    if (
        _file_sha256(_repo_file(root, POLICY_PATH.as_posix(), label="Copy policy")) != EXPECTED_POLICY_SHA256
        or _file_sha256(_repo_file(root, TARGET_PATH.as_posix(), label="Target HTML"))
        != EXPECTED_TARGET_SHA256
    ):
        raise InvestorCopyGovernanceError(
            "forbidden-write", "Policy or website target changed during the transaction."
        )
    proposal, _validation, base_proposal = _proposal_and_validation(
        root=root,
        current=current,
    )
    _revalidate_bound_sources(proposal, base_proposal, root=root)
    if _file_sha256(plan.decision.path) != plan.decision.sha256:
        raise InvestorCopyGovernanceError(
            "approval-race",
            "Owner decision changed during the transaction.",
        )
    return claim_audit, feedback_audit, design_audit


def _application_receipt(
    plan: _ApplicationPlan,
    *,
    current: datetime,
    claim_audit: Mapping[str, Any],
    feedback_audit: Mapping[str, Any],
    design_audit: Mapping[str, Any],
) -> dict[str, Any]:
    raw_claim_summary = claim_audit.get("summary")
    claim_summary = dict(raw_claim_summary) if isinstance(raw_claim_summary, Mapping) else {}
    raw_design_summary = design_audit.get("summary")
    design_summary = dict(raw_design_summary) if isinstance(raw_design_summary, Mapping) else {}
    raw_feedback_summary = feedback_audit.get("summary")
    feedback_summary = dict(raw_feedback_summary) if isinstance(raw_feedback_summary, Mapping) else {}
    return {
        "schema": APPLICATION_SCHEMA,
        "application_id": f"{plan.decision.decision_id}-application",
        "applied_at": _iso(current),
        "state": "applied-governance-only",
        "decision": {
            "decision_id": plan.decision.decision_id,
            "decision_sha256": plan.decision.sha256,
            "owner": NAMED_OWNER,
            "state": APPROVE_STATE,
        },
        "proposal": {
            "path": DEFAULT_PROPOSAL_PATH.as_posix(),
            "sha256": EXPECTED_PROPOSAL_SHA256,
        },
        "validation": {
            "path": DEFAULT_VALIDATION_PATH.as_posix(),
            "sha256": EXPECTED_VALIDATION_SHA256,
        },
        "canonical_changes": [
            {
                "path": REGISTER_PATH.as_posix(),
                "before_sha256": EXPECTED_REGISTER_BEFORE_SHA256,
                "after_sha256": EXPECTED_REGISTER_AFTER_SHA256,
            },
            {
                "path": FEEDBACK_PATH.as_posix(),
                "before_sha256": EXPECTED_FEEDBACK_BEFORE_SHA256,
                "after_sha256": EXPECTED_FEEDBACK_AFTER_SHA256,
            },
            {
                "path": BRIEF_PATH.as_posix(),
                "before_sha256": EXPECTED_BRIEF_BEFORE_SHA256,
                "after_sha256": EXPECTED_BRIEF_AFTER_SHA256,
            },
        ],
        "audits": {
            "claim_audit_passed": claim_audit.get("passed") is True,
            "claim_count": int(claim_summary.get("claim_count", 0)),
            "claim_error_count": int(claim_summary.get("error_count", 0)),
            "stakeholder_feedback_audit_passed": feedback_audit.get("passed") is True,
            "stakeholder_signal_count": int(feedback_summary.get("signal_count", 0)),
            "stakeholder_capsule_count": int(feedback_summary.get("emitted_capsule_count", 0)),
            "design_audit_passed": design_audit.get("passed") is True,
            "design_check_count": int(design_summary.get("check_count", 0)),
            "route_capsule_sha256": EXPECTED_ROUTE_CAPSULE_SHA256,
            "required_concept_groups_sha256": EXPECTED_REQUIRED_CONCEPT_GROUPS_SHA256,
            "satisfied_concept_ids": list(EXPECTED_SATISFIED_CONCEPT_IDS),
        },
        "policy_change": False,
        "website_change": False,
        "release_eligible": False,
        "authority": dict(NON_RELEASE_AUTHORITY),
        "next_gate": (
            "This receipt changes claim governance only. It grants no candidate, "
            "package, release, deployment, credential, or live-state authority."
        ),
    }


def _write_immutable_receipt(
    receipt: Mapping[str, Any],
    *,
    root: Path,
    staged_source: Path | None = None,
) -> Path:
    destination_parent = _controlled_directory_create_leaf(
        root,
        DEFAULT_RECEIPT_ROOT,
        label="Governance receipt root",
    )
    application_id = _safe_identifier(receipt.get("application_id"), label="Application id")
    destination = destination_parent / f"{application_id}.json"
    value = _serialise(receipt)
    expected_sha256 = _bytes_sha256(value)
    if destination.exists():
        raise InvestorCopyGovernanceError(
            "receipt-exists",
            "Refusing to overwrite immutable application evidence.",
        )
    if staged_source is None:
        raise InvestorCopyGovernanceError(
            "receipt-stage-required",
            "Application receipt publication requires its journal-bound stage.",
        )
    transaction_root = _controlled_directory(
        root,
        TRANSACTION_ROOT,
        label="Transaction journal directory",
    )
    staged = staged_source.absolute()
    if (
        staged.parent != transaction_root
        or staged.name != "application-receipt.stage.json"
        or _is_link_or_reparse(staged)
        or not staged.is_file()
        or staged.stat().st_nlink != 1
        or _file_sha256(staged) != expected_sha256
    ):
        raise InvestorCopyGovernanceError(
            "receipt-stage",
            "Application receipt publish stage is not the exact journal-bound image.",
        )
    try:
        try:
            if (
                _controlled_directory(
                    root,
                    DEFAULT_RECEIPT_ROOT,
                    label="Governance receipt root",
                )
                != destination_parent
            ):
                raise InvestorCopyGovernanceError(
                    "receipt-root",
                    "Governance receipt root changed before publication.",
                )
            os.link(staged, destination)
        except FileExistsError as exc:
            raise InvestorCopyGovernanceError(
                "receipt-exists", "Refusing to overwrite immutable application evidence."
            ) from exc
        staged.unlink()
        _fsync_directory(transaction_root)
        _fsync_directory(destination_parent)
        written = _normalise_known_receipt_alias(
            destination,
            staged,
            expected_sha256=expected_sha256,
            label="Application receipt",
        )
        if written is None:
            raise InvestorCopyGovernanceError(
                "receipt-readback", "Application receipt failed exact read-back."
            )
        return written
    except BaseException:
        # The deterministic stage and any published alias remain journal-owned
        # so recovery can roll forward or back without guessing a temp path.
        raise


def apply_investor_copy_governance_delta(
    decision_path: Path,
    *,
    apply: bool = False,
    repo_root: Path | None = None,
    as_of: datetime | None = None,
) -> dict[str, Any]:
    """Apply only the exact approved governance delta; default mode never writes."""

    root = _find_repo_root(repo_root)
    apply_time_override = apply is True and as_of is not None
    current = _wall_now() if apply is True else _now(as_of)
    base_result = {
        "schema": APPLICATION_SCHEMA,
        "attempted_at": _iso(current),
        "applied": False,
        "decision_id": "",
        "decision_state": "",
        "canonical_changes": [],
        "receipt_path": "",
        "receipt_sha256": "",
        "recovery_receipt_path": "",
        "recovery_receipt_sha256": "",
        "transaction_lock_released": True,
        "transaction_journal_cleaned": True,
        "policy_change": False,
        "website_change": False,
        "release_eligible": False,
        "authority": dict(NON_RELEASE_AUTHORITY),
    }
    if apply_time_override:
        return {
            **base_result,
            "state": "blocked",
            "blocked_codes": ["apply-time-override-forbidden"],
        }
    recovery: dict[str, Any] | None = None
    if apply is True:
        recovery = _recover_transaction(root, current=current)
        if recovery.get("applied") is True:
            return {
                **base_result,
                **recovery,
                "decision_state": APPROVE_STATE,
                "policy_change": False,
                "website_change": False,
                "release_eligible": False,
                "authority": dict(NON_RELEASE_AUTHORITY),
            }
        if recovery.get("state") == "blocked":
            return {
                **base_result,
                "state": "blocked",
                "blocked_codes": list(recovery.get("blocked_codes", [])),
                "transaction_lock_released": recovery.get(
                    "transaction_lock_released",
                    False,
                ),
                "transaction_journal_cleaned": recovery.get(
                    "transaction_journal_cleaned",
                    False,
                ),
                "concurrent_drift_preserved_paths": list(
                    recovery.get("concurrent_drift_preserved_paths", [])
                ),
            }
    verification = verify_investor_copy_governance_decision(
        decision_path,
        repo_root=root,
        as_of=current,
    )
    base_result["decision_id"] = verification.get("decision_id", "")
    base_result["decision_state"] = verification.get("decision_state", "")
    if verification.get("valid") is not True:
        return {
            **base_result,
            "state": "blocked",
            "blocked_codes": list(verification.get("blocked_codes", [])),
        }
    if verification.get("approved") is not True:
        return {
            **base_result,
            "state": str(verification.get("state", "blocked")),
            "blocked_codes": [f"decision-{verification.get('decision_state', 'blocked')}"],
        }
    if apply is not True:
        return {
            **base_result,
            "state": "blocked",
            "blocked_codes": ["explicit-apply-required"],
        }

    register_path = _repo_file(root, REGISTER_PATH.as_posix(), label="Claim register")
    feedback_path = _repo_file(root, FEEDBACK_PATH.as_posix(), label="Stakeholder feedback")
    brief_path = _repo_file(root, BRIEF_PATH.as_posix(), label="Design brief")
    transaction_lock: Path | None = None
    transaction_lock_value: bytes | None = None
    journal_prepared = False
    try:
        locking_decision = _decision_or_raise(decision_path, root=root, current=current)
        transaction_lock, transaction_lock_value = _acquire_transaction_lock(
            root,
            decision_sha256=locking_decision.sha256,
            current=current,
        )
    except (InvestorCopyGovernanceError, OSError, ValueError) as exc:
        code = exc.code if isinstance(exc, InvestorCopyGovernanceError) else "transaction-lock"
        return {
            **base_result,
            "state": "blocked",
            "blocked_codes": [code],
        }
    try:
        decision = _decision_or_raise(decision_path, root=root, current=current)
        plan = _preflight_or_raise(decision, root=root, current=current)
        expected_receipt = _application_receipt(
            plan,
            current=current,
            claim_audit=plan.claim_audit,
            feedback_audit=plan.feedback_audit,
            design_audit=plan.design_audit,
        )
        expected_receipt_path = (
            root / DEFAULT_RECEIPT_ROOT / f"{locking_decision.decision_id}-application.json"
        )
        if expected_receipt_path.exists():
            raise InvestorCopyGovernanceError(
                "receipt-exists",
                "Refusing to start when immutable application evidence already exists.",
            )
        journal = _prepare_transaction_journal(
            plan,
            root=root,
            current=current,
            lock_value=transaction_lock_value,
            expected_receipt=expected_receipt,
        )
        journal_prepared = True
        transaction_root = _controlled_directory(
            root,
            TRANSACTION_ROOT,
            label="Transaction journal directory",
        )

        # Final race check after durable preparation and immediately before the first write.
        if (
            _file_sha256(register_path) != EXPECTED_REGISTER_BEFORE_SHA256
            or _file_sha256(feedback_path) != EXPECTED_FEEDBACK_BEFORE_SHA256
            or _file_sha256(brief_path) != EXPECTED_BRIEF_BEFORE_SHA256
            or _file_sha256(decision.path) != decision.sha256
            or _file_sha256(root / DEFAULT_PROPOSAL_PATH) != EXPECTED_PROPOSAL_SHA256
            or _file_sha256(root / DEFAULT_VALIDATION_PATH) != EXPECTED_VALIDATION_SHA256
        ):
            raise InvestorCopyGovernanceError(
                "pre-commit-race", "A bound input changed immediately before commit."
            )
        approval_guards = [
            (decision.path, decision.sha256),
            (root / DEFAULT_PROPOSAL_PATH, EXPECTED_PROPOSAL_SHA256),
            (root / DEFAULT_VALIDATION_PATH, EXPECTED_VALIDATION_SHA256),
            (root / SUPERSEDED_PROPOSAL_PATH, SUPERSEDED_PROPOSAL_SHA256),
            (root / SUPERSEDED_VALIDATION_PATH, SUPERSEDED_VALIDATION_SHA256),
            (root / SUPERSEDED_V2_PROPOSAL_PATH, SUPERSEDED_V2_PROPOSAL_SHA256),
            (root / SUPERSEDED_V2_VALIDATION_PATH, SUPERSEDED_V2_VALIDATION_SHA256),
            (root / SUPERSEDED_V3_PROPOSAL_PATH, SUPERSEDED_V3_PROPOSAL_SHA256),
            (root / SUPERSEDED_V3_VALIDATION_PATH, SUPERSEDED_V3_VALIDATION_SHA256),
            (root / SUPERSEDED_V4_PROPOSAL_PATH, SUPERSEDED_V4_PROPOSAL_SHA256),
            (root / SUPERSEDED_V4_VALIDATION_PATH, SUPERSEDED_V4_VALIDATION_SHA256),
            (root / POLICY_PATH, EXPECTED_POLICY_SHA256),
            (root / TARGET_PATH, EXPECTED_TARGET_SHA256),
            (root / EXPECTED_DESIGN_RECEIPT_PATH, EXPECTED_DESIGN_RECEIPT_SHA256),
            (root / EXPECTED_PROJECTS_SOURCE_PATH, EXPECTED_PROJECTS_SOURCE_SHA256),
            (root / EXPECTED_COMPANY_PLATFORM_PATH, EXPECTED_COMPANY_PLATFORM_SHA256),
        ]
        canonical_paths = [register_path, feedback_path, brief_path]
        entries = _validated_transaction_entries(journal)
        for index, (entry, destination) in enumerate(zip(entries, canonical_paths, strict=True)):
            journal = _set_transaction_state(
                root,
                journal,
                "COMMITTING",
                completed_replacements=index,
            )
            stage = transaction_root / entry["stage_file"]
            _prepare_fixed_stage(
                transaction_root / entry["after_file"],
                stage,
                expected_sha256=entry["after_sha256"],
            )
            state_guards = [
                (
                    canonical_paths[other_index],
                    (
                        entries[other_index]["after_sha256"]
                        if other_index < index
                        else entries[other_index]["before_sha256"]
                    ),
                )
                for other_index in range(len(entries))
                if other_index != index
            ]
            destination = _repo_file(
                root,
                entry["path"],
                label="Canonical governance file before replace",
            )
            _replace_file(
                stage,
                destination,
                expected_before_sha256=entry["before_sha256"],
                expected_after_sha256=entry["after_sha256"],
                guards=[*approval_guards, *state_guards],
            )
            journal = _set_transaction_state(
                root,
                journal,
                "COMMITTING",
                completed_replacements=index + 1,
            )
        journal = _set_transaction_state(
            root,
            journal,
            "VALIDATING",
            completed_replacements=3,
        )
        claim_audit, feedback_audit, design_audit = _post_write_validate(plan, root=root, current=current)
        receipt = _application_receipt(
            plan,
            current=current,
            claim_audit=claim_audit,
            feedback_audit=feedback_audit,
            design_audit=design_audit,
        )
        expected_receipt_binding = _mapping(
            journal.get("receipt"),
            label="Transaction receipt binding",
        )
        if receipt != expected_receipt or _bytes_sha256(_serialise(receipt)) != expected_receipt_binding.get(
            "sha256"
        ):
            raise InvestorCopyGovernanceError(
                "receipt-binding",
                "Post-write audit receipt differs from the durable pre-write binding.",
            )
        journal = _set_transaction_state(
            root,
            journal,
            "VALIDATED",
            completed_replacements=3,
        )
        receipt_path = _write_immutable_receipt(
            receipt,
            root=root,
            staged_source=transaction_root / "application-receipt.stage.json",
        )
        if _file_sha256(receipt_path) != expected_receipt_binding.get("sha256"):
            raise InvestorCopyGovernanceError(
                "receipt-readback",
                "Application commit marker failed exact read-back.",
            )
        journal = _set_transaction_state(
            root,
            journal,
            "COMMITTED",
            completed_replacements=3,
        )
        lock_released = _release_transaction_lock(
            transaction_lock,
            transaction_lock_value,
        )
        journal_cleaned = lock_released and _cleanup_transaction_root(root)
        maintenance = not lock_released or not journal_cleaned
        return {
            **base_result,
            "state": (
                "applied-governance-maintenance-required" if maintenance else "applied-governance-only"
            ),
            "applied": True,
            "canonical_changes": receipt["canonical_changes"],
            "receipt_path": receipt_path.relative_to(root).as_posix(),
            "receipt_sha256": _file_sha256(receipt_path),
            "transaction_lock_released": lock_released,
            "transaction_journal_cleaned": journal_cleaned,
            "blocked_codes": (
                ["transaction-lock-release-failed"]
                if not lock_released
                else ["transaction-journal-cleanup-failed"]
                if not journal_cleaned
                else []
            ),
        }
    except BaseException as exc:
        if journal_prepared or (root / TRANSACTION_ROOT).exists():
            recovery_result = _recover_transaction(
                root,
                current=current,
                allow_current_pid=True,
            )
        else:
            released = (
                transaction_lock is not None
                and transaction_lock_value is not None
                and _release_transaction_lock(
                    transaction_lock,
                    transaction_lock_value,
                )
            )
            recovery_result = {
                "state": "recovered" if released else "blocked",
                "outcome": "orphan-lock-cleared" if released else "blocked",
                "blocked_codes": [] if released else ["transaction-lock-release-failed"],
                "applied": False,
                "transaction_lock_released": released,
                "transaction_journal_cleaned": True,
            }
        if not isinstance(exc, Exception):
            raise
        code = exc.code if isinstance(exc, InvestorCopyGovernanceError) else "transaction-error"
        details = list(exc.details) if isinstance(exc, InvestorCopyGovernanceError) else []
        if recovery_result.get("applied") is True:
            return {
                **base_result,
                **recovery_result,
                "decision_id": locking_decision.decision_id,
                "decision_state": APPROVE_STATE,
                "policy_change": False,
                "website_change": False,
                "release_eligible": False,
                "authority": dict(NON_RELEASE_AUTHORITY),
            }
        recovery_codes = list(recovery_result.get("blocked_codes", []))
        rollback_verified = (
            recovery_result.get("outcome") in {"rolled-back", "orphan-lock-cleared"} and not recovery_codes
        )
        return {
            **base_result,
            "state": "blocked",
            "blocked_codes": [code, *recovery_codes],
            "blocked_details": details,
            "rollback_verified": rollback_verified,
            "transaction_lock_released": recovery_result.get(
                "transaction_lock_released",
                False,
            ),
            "transaction_journal_cleaned": recovery_result.get(
                "transaction_journal_cleaned",
                False,
            ),
            "recovery_receipt_path": recovery_result.get(
                "recovery_receipt_path",
                "",
            ),
            "recovery_receipt_sha256": recovery_result.get(
                "recovery_receipt_sha256",
                "",
            ),
            "concurrent_drift_preserved_paths": list(
                recovery_result.get("concurrent_drift_preserved_paths", [])
            ),
        }


def _parse_as_of(value: str | None) -> datetime | None:
    if value is None:
        return None
    return _timestamp(value, label="--as-of")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="aureon-investor-copy-governance",
        description=(
            "Verify, simulate, or explicitly apply one exact owner-approved "
            "three-file investor-copy governance delta."
        ),
    )
    parser.add_argument("--decision", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path)
    parser.add_argument(
        "--as-of",
        help="Read-only planning timestamp; forbidden together with --apply.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Enable the exact three-file canonical transaction after every gate passes.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(list(argv) if argv is not None else None)
    try:
        current = _parse_as_of(args.as_of)
        if args.apply:
            result = apply_investor_copy_governance_delta(
                args.decision,
                apply=True,
                repo_root=args.repo_root,
                as_of=current,
            )
            passed = (
                result.get("applied") is True
                and result.get("transaction_lock_released") is True
                and result.get("transaction_journal_cleaned") is True
            )
        else:
            result = plan_investor_copy_governance_application(
                args.decision,
                repo_root=args.repo_root,
                as_of=current,
            )
            passed = result.get("passed") is True
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0 if passed else 2
    except InvestorCopyGovernanceError as exc:
        print(
            json.dumps(
                {
                    "state": "blocked",
                    "blocked_codes": [exc.code],
                    "authority": dict(NON_RELEASE_AUTHORITY),
                },
                indent=2,
            )
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

"""Compile one fixed motion/performance configuration for a staged candidate.

The candidate tree hash is dynamic.  The doctrine, thresholds, remote-origin
policy, and motion policy are fixed in reviewed operator code.  A worker or
caller cannot select or relax them.

Compilation and replay are local-only.  They do not run the audit, mutate a
candidate or canonical website, validate a candidate, package, release,
access credentials, or deploy. Exact pre-import source authentication is
available only through direct execution of this file. Imported calls still
reject current source drift, but package initializers have already executed.
"""

from __future__ import annotations

import hashlib
import importlib
import json
import os
import re
import stat
import sys
import threading
from collections.abc import Mapping, Sequence
from pathlib import Path
from types import ModuleType
from typing import Any, Final, cast

COMPILATION_SCHEMA = "aureon.design-candidate-motion-config-compilation.v2"
VERIFICATION_SCHEMA = "aureon.design-candidate-motion-config-verification.v2"
CONFIG_SCHEMA = "aureon.design-motion-performance-budget-config.v1"
COMPILER_PATH = "aureon/operator/design_candidate_motion_policy_compiler.py"
MOTION_IMPLEMENTATION_PATH = "aureon/operator/design_motion_performance_budget.py"
TEST_EVIDENCE_PATH = "aureon/operator/design_candidate_test_evidence.py"
SECURE_WRITER_PATH = "aureon/operator/secure_immutable_artifact.py"
CANDIDATE_CONTROL_PATH = "aureon/operator/design_candidate_control.py"
SOURCE_CLOSURE_HELPER_PATH = "aureon/operator/design_candidate_source_closure.py"
SOURCE_CLOSURE_SCHEMA = "aureon.design-candidate-executable-source-closure.v1"
SOURCE_CLOSURE_ALGORITHM = "python-ast-local-raw-sha256-closure-v2"
SOURCE_CLOSURE_ROOTS = (
    "aureon/operator/design_candidate_motion_policy_compiler.py",
    SOURCE_CLOSURE_HELPER_PATH,
    "aureon/operator/design_candidate_test_policy_compiler.py",
)
SOURCE_POLICY_PATH = "aureon/operator/website_operator.defaults.json"
OUTPUT_ROOT = "artifacts/website-operator/motion-performance-budget/candidate-configs"

EXPECTED_DOCTRINE_SHA256 = "BD51BE9B2A8F48BDFE12EDC7A75DF234C0BEDEABE047DD093938ACEA7E289D4D"
EXPECTED_SOURCE_POLICY_SHA256 = "3956D6AACC2B122086D8E2AC1FBB93AB9D01750CAE9B693D2C6DB6148F31741D"

FIXED_THRESHOLDS: Final[dict[str, int]] = {
    "max_total_bytes": 4_500_000,
    "max_html_bytes": 750_000,
    "max_css_bytes": 350_000,
    "max_javascript_bytes": 300_000,
    "max_image_bytes": 2_200_000,
    "max_font_bytes": 750_000,
    "max_media_bytes": 0,
    "max_other_bytes": 250_000,
    "max_single_asset_bytes": 500_000,
    "max_animation_duration_ms": 800,
    "min_transition_duration_ms": 80,
    "max_transition_duration_ms": 500,
    "max_reduced_motion_duration_ms": 1,
    "max_animation_declarations": 24,
    "max_transition_declarations": 80,
    "max_remote_resource_references": 0,
    "max_embedded_data_bytes": 0,
}
FIXED_REMOTE_ORIGINS: Final[dict[str, object]] = {
    "allowed": [],
    "allow_data_urls": False,
}
FIXED_POLICY: Final[dict[str, str]] = {
    "autoplay_media": "forbid",
    "infinite_animation": "forbid",
    "dynamic_motion": "forbid",
    "reduced_motion_override": "required",
    "undeclared_remote_origins": "forbid",
}

AUTHORITY: Final[dict[str, object]] = {
    "scope": "fixed local candidate motion-config compilation and replay only",
    "executable_source_ingress": (
        "sealed only by direct compiler-file execution; imported API is drift-check-only"
    ),
    "worker_threshold_selection": "none",
    "audit_execution_authority": "none",
    "canonical_website_mutation": "none",
    "candidate_mutation": "none",
    "candidate_validation_authority": "none",
    "promotion_authority": "none",
    "package_authority": "none",
    "release_authority": "none",
    "deployment_authority": "none",
    "credential_access": "none",
}

_RUN_ID = re.compile(r"[a-z0-9][a-z0-9._-]{2,80}\Z")
_SHA256 = re.compile(r"[A-F0-9]{64}\Z")
_CONFIG_ID = re.compile(r"candidate-motion-v2-[a-f0-9]{64}\Z")
_SEALED_CLI_FLAGS = ("-I", "-S", "-B")
_COMPILATION_FIELDS = frozenset(
    {
        "schema",
        "state",
        "passed",
        "candidate",
        "doctrine",
        "source_policy",
        "config",
        "source_closure",
        "authority",
        "compilation_payload_sha256",
    }
)
_LOADED_COMPILER_SHA256 = hashlib.sha256(Path(__file__).read_bytes()).hexdigest().upper()
candidate_control: Any = None
candidate_evidence: Any = None
motion_budget: Any = None
secure_immutable_artifact: Any = None
_verified_source_closure: Any = None
_verified_source_finder: Any = None
_verified_source_manifest_sha256: str | None = None
_CANDIDATE_RECEIPT_FIELDS = frozenset(
    {
        "schema",
        "validated_at",
        "state",
        "passed",
        "release_eligible",
        "deployment_authority",
        "authority",
        "validation_input",
        "work_order",
        "candidate",
        "changes",
        "claims",
        "claim_surface",
        "source_closure",
        "checks",
        "next_gate",
    }
)
_CANDIDATE_WORK_ORDER_FIELDS = frozenset({"run_id", "path", "file_sha256", "sha256", "baseline_tree_sha256"})
_CANDIDATE_BINDING_FIELDS = frozenset({"root", "website_path", "tree_sha256", "file_count", "total_bytes"})
_ISSUED_COMPILATIONS: set[str] = set()
_ISSUED_LOCK = threading.Lock()


class DesignCandidateMotionPolicyCompilerError(ValueError):
    """The candidate, doctrine, toolchain, or compiled configuration is unsafe."""


def _canonical_bytes(value: object) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        + b"\n"
    )


def _json_sha256(value: object) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest().upper()


def _strict_json_equal(left: object, right: object) -> bool:
    try:
        return _canonical_bytes(left) == _canonical_bytes(right)
    except (TypeError, ValueError):
        return False


def _bytes_sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest().upper()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def _bootstrap_canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _bootstrap_json_sha256(value: object) -> str:
    return hashlib.sha256(_bootstrap_canonical_bytes(value)).hexdigest().upper()


def _bootstrap_strict_equal(left: object, right: object) -> bool:
    try:
        return _bootstrap_canonical_bytes(left) == _bootstrap_canonical_bytes(right)
    except (TypeError, ValueError):
        return False


def _bootstrap_repo_root(repo_root: Path | None) -> Path:
    if repo_root is not None:
        root = Path(os.path.abspath(repo_root))
    else:
        found_root = next(
            (
                parent
                for parent in Path(os.path.abspath(__file__)).parents
                if (parent / "pyproject.toml").is_file() and (parent / "aureon" / "operator").is_dir()
            ),
            None,
        )
        if found_root is None:
            raise DesignCandidateMotionPolicyCompilerError(
                "Could not locate the repository for executable-source preflight."
            )
        root = found_root
    try:
        details = root.lstat()
    except OSError as exc:
        raise DesignCandidateMotionPolicyCompilerError(
            "Executable-source repository root is missing."
        ) from exc
    reparse = int(getattr(details, "st_file_attributes", 0)) & int(
        getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    )
    if not stat.S_ISDIR(details.st_mode) or stat.S_ISLNK(details.st_mode) or reparse:
        raise DesignCandidateMotionPolicyCompilerError(
            "Executable-source repository root must be an ordinary directory."
        )
    return root


def _bootstrap_read_file(root: Path, path: Path, *, label: str) -> tuple[Path, bytes]:
    lexical = Path(os.path.abspath(path if path.is_absolute() else root / path))
    try:
        relative = lexical.relative_to(root)
    except ValueError as exc:
        raise DesignCandidateMotionPolicyCompilerError(f"{label} escapes the repository.") from exc
    if any(part in {"", ".", ".."} or ":" in part for part in relative.parts):
        raise DesignCandidateMotionPolicyCompilerError(
            f"{label} has an aliased or alternate-data-stream path."
        )
    current = root
    try:
        for part in relative.parts:
            case_matches = sorted(
                entry.name for entry in os.scandir(current) if entry.name.casefold() == part.casefold()
            )
            if case_matches != [part]:
                raise DesignCandidateMotionPolicyCompilerError(
                    f"{label} has a missing or case-aliased path component."
                )
            current = current / part
            details = current.lstat()
            reparse = int(getattr(details, "st_file_attributes", 0)) & int(
                getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
            )
            if stat.S_ISLNK(details.st_mode) or reparse:
                raise DesignCandidateMotionPolicyCompilerError(
                    f"{label} may not traverse a link or reparse point."
                )
        before = lexical.lstat()
        if not stat.S_ISREG(before.st_mode) or int(before.st_nlink) != 1:
            raise DesignCandidateMotionPolicyCompilerError(
                f"{label} must be an ordinary file with exactly one hard link."
            )
        raw = lexical.read_bytes()
        after = lexical.lstat()
    except DesignCandidateMotionPolicyCompilerError:
        raise
    except OSError as exc:
        raise DesignCandidateMotionPolicyCompilerError(f"{label} is missing or unreadable.") from exc
    identity_before = (
        stat.S_IFMT(before.st_mode),
        int(getattr(before, "st_dev", 0)),
        int(getattr(before, "st_ino", 0)),
        int(before.st_nlink),
        int(before.st_size),
    )
    identity_after = (
        stat.S_IFMT(after.st_mode),
        int(getattr(after, "st_dev", 0)),
        int(getattr(after, "st_ino", 0)),
        int(after.st_nlink),
        int(after.st_size),
    )
    if identity_before != identity_after or len(raw) != int(after.st_size):
        raise DesignCandidateMotionPolicyCompilerError(f"{label} changed while it was read.")
    return lexical, raw


def _bootstrap_strict_json(raw: bytes, *, label: str) -> dict[str, Any]:
    def pairs(values: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in values:
            if key in result:
                raise DesignCandidateMotionPolicyCompilerError(f"{label} contains a duplicate JSON key.")
            result[key] = value
        return result

    def nonfinite(value: str) -> None:
        raise DesignCandidateMotionPolicyCompilerError(f"{label} contains non-finite JSON: {value}.")

    try:
        value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=pairs,
            parse_constant=nonfinite,
        )
    except DesignCandidateMotionPolicyCompilerError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise DesignCandidateMotionPolicyCompilerError(f"{label} is not strict UTF-8 JSON.") from exc
    if not isinstance(value, dict):
        raise DesignCandidateMotionPolicyCompilerError(f"{label} must be a JSON object.")
    return value


def _bootstrap_source_closure(
    candidate_receipt_path: Path,
    *,
    repo_root: Path | None,
) -> tuple[Path, dict[str, Any], Any]:
    root = _bootstrap_repo_root(repo_root)
    receipt_path, receipt_raw = _bootstrap_read_file(
        root,
        candidate_receipt_path,
        label="Candidate receipt preflight",
    )
    relative_receipt = receipt_path.relative_to(root)
    parts = relative_receipt.parts
    if (
        len(parts) != 4
        or parts[0:2] != ("artifacts", "website-candidates")
        or _RUN_ID.fullmatch(parts[2]) is None
        or parts[3] != "candidate.v1.json"
    ):
        raise DesignCandidateMotionPolicyCompilerError(
            "Candidate receipt preflight path is not the exact staged path."
        )
    receipt = _bootstrap_strict_json(receipt_raw, label="Candidate receipt preflight")
    binding = receipt.get("validation_input")
    if not isinstance(binding, dict) or frozenset(binding) != frozenset(
        {"path", "file_sha256", "json_sha256", "payload_sha256"}
    ):
        raise DesignCandidateMotionPolicyCompilerError(
            "Candidate receipt preflight validation-input binding is malformed."
        )
    validation_path = receipt_path.parent / "candidate-validation-input.v1.json"
    expected_validation_relative = validation_path.relative_to(root).as_posix()
    if binding.get("path") != expected_validation_relative:
        raise DesignCandidateMotionPolicyCompilerError(
            "Candidate receipt preflight validation-input path is not exact."
        )
    _, validation_raw = _bootstrap_read_file(
        root,
        validation_path,
        label="Candidate validation input preflight",
    )
    validation = _bootstrap_strict_json(
        validation_raw,
        label="Candidate validation input preflight",
    )
    if (
        binding.get("file_sha256") != _bytes_sha256(validation_raw)
        or binding.get("json_sha256") != _bootstrap_json_sha256(validation)
        or binding.get("payload_sha256") != validation.get("payload_sha256")
    ):
        raise DesignCandidateMotionPolicyCompilerError(
            "Candidate validation-input raw, canonical, or payload binding failed preflight."
        )
    unsigned_validation = dict(validation)
    validation_payload_sha256 = unsigned_validation.pop("payload_sha256", None)
    if (
        not isinstance(validation_payload_sha256, str)
        or _SHA256.fullmatch(validation_payload_sha256) is None
        or _bootstrap_json_sha256(unsigned_validation) != validation_payload_sha256
    ):
        raise DesignCandidateMotionPolicyCompilerError(
            "Candidate validation-input payload self-hash failed preflight."
        )
    source_closure = validation.get("source_closure")
    if not isinstance(source_closure, dict) or not _bootstrap_strict_equal(
        receipt.get("source_closure"),
        source_closure,
    ):
        raise DesignCandidateMotionPolicyCompilerError(
            "Candidate receipt and validation input do not bind one exact source closure."
        )
    if (
        frozenset(source_closure)
        != frozenset({"schema", "algorithm", "roots", "files", "exclusions", "manifest_sha256"})
        or source_closure.get("schema") != SOURCE_CLOSURE_SCHEMA
        or source_closure.get("algorithm") != SOURCE_CLOSURE_ALGORITHM
        or source_closure.get("roots") != list(SOURCE_CLOSURE_ROOTS)
    ):
        raise DesignCandidateMotionPolicyCompilerError(
            "Executable-source closure bootstrap contract is invalid."
        )
    files = source_closure.get("files")
    if not isinstance(files, list) or not files:
        raise DesignCandidateMotionPolicyCompilerError(
            "Executable-source closure bootstrap file list is empty."
        )
    if not isinstance(source_closure.get("exclusions"), list):
        raise DesignCandidateMotionPolicyCompilerError(
            "Executable-source closure bootstrap exclusions are malformed."
        )
    paths: list[str] = []
    helper_row: dict[str, Any] | None = None
    for row in files:
        if not isinstance(row, dict) or frozenset(row) != frozenset({"path", "bytes", "sha256"}):
            raise DesignCandidateMotionPolicyCompilerError(
                "Executable-source closure bootstrap file row is malformed."
            )
        path = row.get("path")
        byte_count = row.get("bytes")
        sha256 = row.get("sha256")
        if (
            not isinstance(path, str)
            or not path
            or path != path.strip()
            or "\\" in path
            or ":" in path
            or path.startswith("/")
            or Path(path).as_posix() != path
            or any(part in {"", ".", ".."} for part in path.split("/"))
            or not path.endswith(".py")
            or type(byte_count) is not int
            or byte_count < 1
            or not isinstance(sha256, str)
            or _SHA256.fullmatch(sha256) is None
        ):
            raise DesignCandidateMotionPolicyCompilerError(
                "Executable-source closure bootstrap file row is unsafe."
            )
        paths.append(path)
        if path == SOURCE_CLOSURE_HELPER_PATH:
            helper_row = row
    if paths != sorted(set(paths)) or not set(SOURCE_CLOSURE_ROOTS).issubset(paths):
        raise DesignCandidateMotionPolicyCompilerError(
            "Executable-source closure bootstrap paths are not exact, sorted, and unique."
        )
    unsigned_closure = dict(source_closure)
    manifest_sha256 = unsigned_closure.pop("manifest_sha256", None)
    if (
        not isinstance(manifest_sha256, str)
        or _SHA256.fullmatch(manifest_sha256) is None
        or _bootstrap_json_sha256(unsigned_closure) != manifest_sha256
        or helper_row is None
    ):
        raise DesignCandidateMotionPolicyCompilerError(
            "Executable-source closure bootstrap self-hash or helper binding is invalid."
        )
    helper_path, helper_raw = _bootstrap_read_file(
        root,
        Path(SOURCE_CLOSURE_HELPER_PATH),
        label="Executable-source closure helper",
    )
    if len(helper_raw) != helper_row["bytes"] or _bytes_sha256(helper_raw) != helper_row["sha256"]:
        raise DesignCandidateMotionPolicyCompilerError(
            "Executable-source closure helper raw bytes changed before authentication."
        )
    helper = ModuleType("_aureon_verified_design_candidate_source_closure")
    helper.__file__ = str(helper_path)
    helper.__package__ = ""
    try:
        exec(compile(helper_raw, str(helper_path), "exec"), helper.__dict__)  # noqa: S102
        helper.verify_source_closure(root, source_closure)
    except Exception as exc:
        raise DesignCandidateMotionPolicyCompilerError(
            f"Executable-source closure preflight failed: {exc}"
        ) from exc
    return root, source_closure, helper


def _prepare_runtime(
    candidate_receipt_path: Path,
    *,
    repo_root: Path | None,
) -> tuple[Path, dict[str, Any]]:
    global candidate_control, candidate_evidence, motion_budget
    global secure_immutable_artifact, _verified_source_closure
    global _verified_source_finder, _verified_source_manifest_sha256

    root, source_closure, helper = _bootstrap_source_closure(
        candidate_receipt_path,
        repo_root=repo_root,
    )
    sealed_ingress = __name__ == "__main__" and __package__ in {None, ""}
    if (
        _verified_source_finder is None
        or _verified_source_manifest_sha256 != source_closure["manifest_sha256"]
    ):
        try:
            _verified_source_finder = helper.install_verified_source_importer(
                root,
                source_closure,
                require_unloaded=sealed_ingress,
            )
        except Exception as exc:
            raise DesignCandidateMotionPolicyCompilerError(
                f"Verified raw-source importer could not be installed: {exc}"
            ) from exc
        _verified_source_manifest_sha256 = str(source_closure["manifest_sha256"])
    candidate_control = importlib.import_module("aureon.operator.design_candidate_control")
    candidate_evidence = importlib.import_module("aureon.operator.design_candidate_test_evidence")
    motion_budget = importlib.import_module("aureon.operator.design_motion_performance_budget")
    secure_immutable_artifact = importlib.import_module("aureon.operator.secure_immutable_artifact")
    _verified_source_closure = helper
    try:
        helper.verify_loaded_source_modules(
            source_closure,
            require_verified_loader=sealed_ingress,
        )
        helper.verify_source_closure(root, source_closure)
    except Exception as exc:
        raise DesignCandidateMotionPolicyCompilerError(
            f"Loaded executable-source closure failed authentication: {exc}"
        ) from exc
    return root, source_closure


def _repo_root(repo_root: Path | None) -> Path:
    try:
        return cast(Path, candidate_evidence._find_repo_root(repo_root))  # noqa: SLF001
    except candidate_evidence.DesignCandidateTestEvidenceError as exc:
        raise DesignCandidateMotionPolicyCompilerError(str(exc)) from exc


def _regular_file(root: Path, relative: str, *, label: str) -> Path:
    try:
        return cast(
            Path,
            candidate_evidence._resolve_under(  # noqa: SLF001
                root,
                relative,
                label=label,
            ),
        )
    except candidate_evidence.DesignCandidateTestEvidenceError as exc:
        raise DesignCandidateMotionPolicyCompilerError(str(exc)) from exc


def _relative(root: Path, path: Path, *, label: str) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError as exc:
        raise DesignCandidateMotionPolicyCompilerError(f"{label} escapes the repository.") from exc


def _assert_loaded_sources(root: Path, source_closure: Mapping[str, Any]) -> None:
    if _verified_source_closure is None:
        raise DesignCandidateMotionPolicyCompilerError(
            "Executable-source closure was not authenticated before local imports."
        )
    try:
        _verified_source_closure.verify_loaded_source_modules(
            source_closure,
            require_verified_loader=__name__ == "__main__" and __package__ in {None, ""},
        )
        _verified_source_closure.verify_source_closure(root, source_closure)
    except Exception as exc:
        raise DesignCandidateMotionPolicyCompilerError(
            f"Executable-source closure changed after local imports: {exc}"
        ) from exc


def _candidate(
    root: Path,
    candidate_receipt_path: Path,
) -> dict[str, Any]:
    try:
        receipt_path = candidate_evidence._regular_file(  # noqa: SLF001
            candidate_receipt_path,
            label="Candidate receipt",
            single_link=True,
        )
        receipt, raw = candidate_evidence._load_json_file(  # noqa: SLF001
            receipt_path,
            label="Candidate receipt",
        )
    except candidate_evidence.DesignCandidateTestEvidenceError as exc:
        raise DesignCandidateMotionPolicyCompilerError(str(exc)) from exc
    try:
        candidate_control.require_candidate_receipt_contract(receipt)
    except candidate_control.DesignCandidateControlError as exc:
        raise DesignCandidateMotionPolicyCompilerError(
            f"Candidate receipt runtime contract failed: {exc}"
        ) from exc
    relative = _relative(root, receipt_path, label="Candidate receipt")
    parts = Path(relative).parts
    if (
        len(parts) != 4
        or parts[:2] != ("artifacts", "website-candidates")
        or _RUN_ID.fullmatch(parts[2]) is None
        or parts[3] != "candidate.v1.json"
    ):
        raise DesignCandidateMotionPolicyCompilerError(
            "Candidate receipt must be exactly "
            "artifacts/website-candidates/<lowercase-run-id>/candidate.v1.json."
        )
    if frozenset(receipt) != _CANDIDATE_RECEIPT_FIELDS:
        raise DesignCandidateMotionPolicyCompilerError(
            "Candidate receipt top-level fields are not the exact current contract."
        )
    work_order = receipt.get("work_order")
    if not isinstance(work_order, Mapping) or frozenset(work_order) != _CANDIDATE_WORK_ORDER_FIELDS:
        raise DesignCandidateMotionPolicyCompilerError(
            "Candidate receipt work-order binding fields are not exact."
        )
    try:
        candidate_control.require_current_work_order_binding(work_order, repo_root=root)
    except candidate_control.DesignCandidateControlError as exc:
        raise DesignCandidateMotionPolicyCompilerError(
            f"Candidate work-order persisted-byte and JSON binding failed: {exc}"
        ) from exc
    candidate = receipt.get("candidate")
    candidate_root = f"artifacts/website-candidates/{parts[2]}"
    website_path = f"{candidate_root}/website"
    if (
        not isinstance(candidate, Mapping)
        or frozenset(candidate) != _CANDIDATE_BINDING_FIELDS
        or candidate.get("root") != candidate_root
        or candidate.get("website_path") != website_path
    ):
        raise DesignCandidateMotionPolicyCompilerError(
            "Candidate receipt does not bind the deterministic staged layout."
        )
    try:
        website = candidate_evidence._resolve_under(  # noqa: SLF001
            root,
            website_path,
            label="Staged candidate website",
            directory=True,
        )
        verification = candidate_control.verify_staged_candidate_receipt(
            receipt,
            repo_root=root,
            _require_current_baseline=False,
        )
    except (
        candidate_evidence.DesignCandidateTestEvidenceError,
        candidate_control.DesignCandidateControlError,
    ) as exc:
        raise DesignCandidateMotionPolicyCompilerError(str(exc)) from exc
    if (
        verification.get("schema") != candidate_control.VERIFICATION_SCHEMA
        or verification.get("passed") is not True
        or verification.get("release_eligible") is not False
        or verification.get("deployment_authority") != "none"
    ):
        failed_checks = [
            str(row.get("id"))
            for row in verification.get("checks", [])
            if isinstance(row, Mapping) and row.get("passed") is not True
        ]
        raise DesignCandidateMotionPolicyCompilerError(
            f"Full staged-candidate and work-order verification did not pass (failed_checks={failed_checks})."
        )
    motion_snapshot = motion_budget.snapshot_static_tree_dual_hash(
        website,
        repo_root=root,
    )
    if (
        motion_snapshot.get("kind") != "staged-static-tree"
        or motion_snapshot.get("root") != website_path
        or motion_snapshot.get("candidate_tree_sha256") != candidate.get("tree_sha256")
        or motion_snapshot.get("file_count") != candidate.get("file_count")
        or motion_snapshot.get("total_bytes") != candidate.get("total_bytes")
    ):
        raise DesignCandidateMotionPolicyCompilerError(
            "The single captured byte manifest disagrees with the exact candidate receipt."
        )
    return {
        "receipt_path": relative,
        "receipt_file_sha256": _bytes_sha256(raw),
        "receipt_json_sha256": candidate_evidence._json_sha256(receipt),  # noqa: SLF001
        "root": candidate_root,
        "website_path": website_path,
        "tree_sha256": motion_snapshot["candidate_tree_sha256"],
        "candidate_tree_algorithm": motion_snapshot["candidate_tree_algorithm"],
        "motion_tree_sha256": motion_snapshot["motion_tree_sha256"],
        "motion_tree_algorithm": motion_snapshot["motion_tree_algorithm"],
        "captured_manifest_sha256": motion_snapshot["captured_manifest_sha256"],
        "file_count": motion_snapshot["file_count"],
        "total_bytes": motion_snapshot["total_bytes"],
    }


def _doctrine(root: Path) -> dict[str, str]:
    path = _regular_file(root, motion_budget.DOCTRINE_PATH, label="Design doctrine")
    current = _sha256_file(path)
    if current != EXPECTED_DOCTRINE_SHA256:
        raise DesignCandidateMotionPolicyCompilerError(
            "Design doctrine changed and requires an explicit candidate-motion policy review."
        )
    return {
        "path": motion_budget.DOCTRINE_PATH,
        "sha256": current,
    }


def _source_policy(root: Path) -> dict[str, str]:
    path = _regular_file(root, SOURCE_POLICY_PATH, label="WebsiteOperator source policy")
    current = _sha256_file(path)
    if current != EXPECTED_SOURCE_POLICY_SHA256:
        raise DesignCandidateMotionPolicyCompilerError(
            "WebsiteOperator source policy bytes changed and require explicit code review; "
            "no budget, route, authority, or gate relaxation is accepted dynamically."
        )
    return {"path": SOURCE_POLICY_PATH, "sha256": current}


def _config(candidate: Mapping[str, Any], doctrine: Mapping[str, str]) -> dict[str, Any]:
    return {
        "schema": CONFIG_SCHEMA,
        "source": {
            "kind": "staged-static-tree",
            "root": candidate["website_path"],
            "tree_sha256": candidate["motion_tree_sha256"],
        },
        "doctrine": dict(doctrine),
        "thresholds": dict(FIXED_THRESHOLDS),
        "remote_origins": {
            "allowed": [],
            "allow_data_urls": False,
        },
        "policy": dict(FIXED_POLICY),
    }


def _compile(
    candidate_receipt_path: Path,
    *,
    repo_root: Path | None,
    register: bool,
) -> dict[str, Any]:
    root, source_closure = _prepare_runtime(
        candidate_receipt_path,
        repo_root=repo_root,
    )
    _assert_loaded_sources(root, source_closure)
    input_path = (
        candidate_receipt_path if candidate_receipt_path.is_absolute() else root / candidate_receipt_path
    )
    candidate = _candidate(root, input_path)
    doctrine = _doctrine(root)
    source_policy = _source_policy(root)
    config = _config(candidate, doctrine)
    candidate_after = _candidate(root, input_path)
    doctrine_after = _doctrine(root)
    source_policy_after = _source_policy(root)
    _assert_loaded_sources(root, source_closure)
    if (
        not _strict_json_equal(candidate_after, candidate)
        or not _strict_json_equal(doctrine_after, doctrine)
        or not _strict_json_equal(source_policy_after, source_policy)
    ):
        raise DesignCandidateMotionPolicyCompilerError(
            "Candidate, doctrine, or reviewed WebsiteOperator source policy changed "
            "during motion-policy compilation."
        )
    encoded = _canonical_bytes(config)
    config_id = f"candidate-motion-v2-{_bytes_sha256(encoded).lower()}"
    compilation: dict[str, Any] = {
        "schema": COMPILATION_SCHEMA,
        "state": "compiled-local",
        "passed": True,
        "candidate": candidate,
        "doctrine": doctrine,
        "source_policy": source_policy,
        "source_closure": source_closure,
        "config": {
            "config_id": config_id,
            "file_sha256": _bytes_sha256(encoded),
            "json_sha256": _json_sha256(config),
            "thresholds_sha256": _json_sha256(dict(FIXED_THRESHOLDS)),
            "payload": config,
        },
        "authority": dict(AUTHORITY),
    }
    compilation["compilation_payload_sha256"] = _json_sha256(compilation)
    if register:
        with _ISSUED_LOCK:
            _ISSUED_COMPILATIONS.add(str(compilation["compilation_payload_sha256"]))
    return compilation


def compile_candidate_motion_config(
    candidate_receipt_path: Path,
    *,
    repo_root: Path | None = None,
) -> dict[str, Any]:
    """Return one fixed config; imported use is a trusted drift-check boundary."""

    return _compile(candidate_receipt_path, repo_root=repo_root, register=True)


def validate_candidate_motion_config_compilation(
    compilation: Mapping[str, Any],
    *,
    repo_root: Path | None = None,
) -> dict[str, Any]:
    """Replay a compilation against all current fixed inputs."""

    if frozenset(compilation) != _COMPILATION_FIELDS:
        raise DesignCandidateMotionPolicyCompilerError("Candidate motion compilation fields are not exact.")
    if (
        compilation.get("schema") != COMPILATION_SCHEMA
        or compilation.get("state") != "compiled-local"
        or compilation.get("passed") is not True
        or not _strict_json_equal(compilation.get("authority"), AUTHORITY)
    ):
        raise DesignCandidateMotionPolicyCompilerError(
            "Candidate motion compilation state or authority is invalid."
        )
    unsigned = dict(compilation)
    supplied_hash = unsigned.pop("compilation_payload_sha256", None)
    if (
        not isinstance(supplied_hash, str)
        or _SHA256.fullmatch(supplied_hash) is None
        or supplied_hash != _json_sha256(unsigned)
    ):
        raise DesignCandidateMotionPolicyCompilerError(
            "Candidate motion compilation payload hash is invalid."
        )
    candidate = compilation.get("candidate")
    if not isinstance(candidate, Mapping) or not isinstance(candidate.get("receipt_path"), str):
        raise DesignCandidateMotionPolicyCompilerError(
            "Candidate motion compilation lacks its candidate receipt."
        )
    expected = _compile(
        Path(str(candidate["receipt_path"])),
        repo_root=repo_root,
        register=False,
    )
    if not _strict_json_equal(compilation, expected):
        raise DesignCandidateMotionPolicyCompilerError(
            "Candidate motion compilation does not equal fixed current compiler replay."
        )
    config = cast(Mapping[str, Any], compilation["config"])
    return {
        "schema": VERIFICATION_SCHEMA,
        "state": "pass",
        "passed": True,
        "verification_scope": ("fixed compiler replay against exact candidate, doctrine and control modules"),
        "compiler_replayed": True,
        "origin_attested": False,
        "candidate_receipt_path": candidate["receipt_path"],
        "candidate_tree_sha256": candidate["tree_sha256"],
        "candidate_tree_algorithm": candidate["candidate_tree_algorithm"],
        "motion_tree_sha256": candidate["motion_tree_sha256"],
        "motion_tree_algorithm": candidate["motion_tree_algorithm"],
        "captured_manifest_sha256": candidate["captured_manifest_sha256"],
        "doctrine_sha256": compilation["doctrine"]["sha256"],
        "source_policy_sha256": compilation["source_policy"]["sha256"],
        "config_id": config["config_id"],
        "config_file_sha256": config["file_sha256"],
        "config_json_sha256": config["json_sha256"],
        "thresholds_sha256": config["thresholds_sha256"],
        "authority": dict(AUTHORITY),
    }


def _output_path(root: Path, config_id: str, *, create_directory: bool) -> Path:
    if _CONFIG_ID.fullmatch(config_id) is None:
        raise DesignCandidateMotionPolicyCompilerError(
            "Candidate motion config id is not the exact v2 content address."
        )
    parent = root / OUTPUT_ROOT
    try:
        safe_grandparent = candidate_evidence._regular_directory(  # noqa: SLF001
            parent.parent,
            label="Candidate motion-config output parent",
        )
    except candidate_evidence.DesignCandidateTestEvidenceError as exc:
        raise DesignCandidateMotionPolicyCompilerError(str(exc)) from exc
    if parent.exists() or parent.is_symlink():
        try:
            safe_parent = candidate_evidence._regular_directory(  # noqa: SLF001
                parent,
                label="Candidate motion-config output directory",
            )
        except candidate_evidence.DesignCandidateTestEvidenceError as exc:
            raise DesignCandidateMotionPolicyCompilerError(str(exc)) from exc
    elif create_directory:
        try:
            os.mkdir(parent, 0o700)
        except OSError as exc:
            raise DesignCandidateMotionPolicyCompilerError(
                "Candidate motion-config output directory could not be created safely."
            ) from exc
        try:
            safe_parent = candidate_evidence._regular_directory(  # noqa: SLF001
                parent,
                label="Candidate motion-config output directory",
            )
        except candidate_evidence.DesignCandidateTestEvidenceError as exc:
            raise DesignCandidateMotionPolicyCompilerError(str(exc)) from exc
    else:
        raise DesignCandidateMotionPolicyCompilerError(
            "Candidate motion-config output directory does not exist."
        )
    if safe_parent.parent != safe_grandparent:
        raise DesignCandidateMotionPolicyCompilerError(
            "Candidate motion-config output directory changed during resolution."
        )
    output = safe_parent / f"{config_id}.json"
    try:
        secure_immutable_artifact.validate_no_alternate_stream_path(
            output,
            label="Candidate motion-config output path",
        )
    except secure_immutable_artifact.SecureImmutableArtifactError as exc:
        raise DesignCandidateMotionPolicyCompilerError(str(exc)) from exc
    return cast(Path, output)


def verify_compiled_candidate_motion_config_file(
    config_path: Path,
    *,
    expected_config_sha256: str,
    candidate_receipt_path: Path,
    repo_root: Path | None = None,
) -> dict[str, Any]:
    """Reject threshold shopping by requiring exact fixed compiler output."""

    if _SHA256.fullmatch(expected_config_sha256) is None:
        raise DesignCandidateMotionPolicyCompilerError(
            "Expected motion-config hash must be an uppercase SHA-256."
        )
    expected = _compile(
        candidate_receipt_path,
        repo_root=repo_root,
        register=False,
    )
    try:
        secure_immutable_artifact.validate_no_alternate_stream_path(
            config_path,
            label="Compiled candidate motion configuration path",
        )
        secure_immutable_artifact.validate_no_alternate_stream_path(
            candidate_receipt_path,
            label="Candidate receipt path",
        )
    except secure_immutable_artifact.SecureImmutableArtifactError as exc:
        raise DesignCandidateMotionPolicyCompilerError(str(exc)) from exc
    root = _repo_root(repo_root)
    binding = cast(Mapping[str, Any], expected["config"])
    expected_path = _output_path(
        root,
        str(binding["config_id"]),
        create_directory=False,
    )
    supplied_path = config_path if config_path.is_absolute() else root / config_path
    try:
        supplied = candidate_evidence._regular_file(  # noqa: SLF001
            supplied_path,
            label="Compiled candidate motion configuration",
            single_link=True,
        )
    except candidate_evidence.DesignCandidateTestEvidenceError as exc:
        raise DesignCandidateMotionPolicyCompilerError(str(exc)) from exc
    raw = supplied.read_bytes()
    if (
        supplied != expected_path
        or expected_config_sha256 != binding["file_sha256"]
        or _bytes_sha256(raw) != expected_config_sha256
        or raw != _canonical_bytes(binding["payload"])
    ):
        raise DesignCandidateMotionPolicyCompilerError(
            "Motion configuration does not equal the fixed compiler path and bytes."
        )
    try:
        (
            loaded_path,
            _,
            loaded_config,
            _,
            _,
            loaded_sha,
            loaded_root,
        ) = motion_budget._load_config(  # noqa: SLF001
            supplied,
            repo_root=root,
        )
    except motion_budget.DesignMotionPerformanceBudgetError as exc:
        raise DesignCandidateMotionPolicyCompilerError(str(exc)) from exc
    if (
        loaded_path != supplied
        or loaded_root != root
        or loaded_config != binding["payload"]
        or loaded_sha != expected_config_sha256
    ):
        raise DesignCandidateMotionPolicyCompilerError(
            "Motion control did not accept the exact fixed compiler configuration."
        )
    candidate = cast(Mapping[str, Any], expected["candidate"])
    return {
        "schema": VERIFICATION_SCHEMA,
        "state": "pass",
        "passed": True,
        "verification_scope": (
            "exact fixed path and bytes, deterministic compiler replay, "
            "and motion-control configuration acceptance"
        ),
        "compiler_replayed": True,
        "origin_attested": False,
        "candidate_receipt_path": candidate["receipt_path"],
        "candidate_tree_sha256": candidate["tree_sha256"],
        "candidate_tree_algorithm": candidate["candidate_tree_algorithm"],
        "motion_tree_sha256": candidate["motion_tree_sha256"],
        "motion_tree_algorithm": candidate["motion_tree_algorithm"],
        "captured_manifest_sha256": candidate["captured_manifest_sha256"],
        "doctrine_sha256": expected["doctrine"]["sha256"],
        "source_policy_sha256": expected["source_policy"]["sha256"],
        "config_path": _relative(root, supplied, label="Candidate motion configuration"),
        "config_id": binding["config_id"],
        "config_file_sha256": binding["file_sha256"],
        "config_json_sha256": binding["json_sha256"],
        "thresholds_sha256": binding["thresholds_sha256"],
        "authority": dict(AUTHORITY),
    }


def write_compiled_candidate_motion_config(
    compilation: Mapping[str, Any],
    *,
    repo_root: Path | None = None,
) -> dict[str, Any]:
    """Create one immutable fixed-path config from a fresh compiler result."""

    issued_hash = compilation.get("compilation_payload_sha256")
    with _ISSUED_LOCK:
        if not isinstance(issued_hash, str) or issued_hash not in _ISSUED_COMPILATIONS:
            raise DesignCandidateMotionPolicyCompilerError(
                "Motion-config writer accepts only a fresh same-process compiler result."
            )
        _ISSUED_COMPILATIONS.remove(issued_hash)
    validate_candidate_motion_config_compilation(compilation, repo_root=repo_root)
    root = _repo_root(repo_root)
    binding = cast(Mapping[str, Any], compilation["config"])
    output = _output_path(
        root,
        str(binding["config_id"]),
        create_directory=True,
    )
    encoded = _canonical_bytes(binding["payload"])
    if not output.exists() and not output.is_symlink():
        try:
            secure_immutable_artifact.write_new_file(output, encoded)
        except secure_immutable_artifact.SecureImmutableArtifactError as exc:
            if not output.is_file():
                raise DesignCandidateMotionPolicyCompilerError(
                    f"Compiled candidate motion configuration could not be created safely: {exc}"
                ) from exc
    return verify_compiled_candidate_motion_config_file(
        output,
        expected_config_sha256=str(binding["file_sha256"]),
        candidate_receipt_path=Path(str(compilation["candidate"]["receipt_path"])),
        repo_root=root,
    )


def _require_sealed_cli_runtime() -> None:
    """Require the exact isolated direct-file interpreter boundary."""

    if (
        __name__ != "__main__"
        or __package__ not in {None, ""}
        or sys.flags.isolated != 1
        or sys.flags.no_site != 1
        or sys.flags.dont_write_bytecode != 1
    ):
        raise DesignCandidateMotionPolicyCompilerError(
            "Compiler CLI requires direct isolated file execution with python "
            + " ".join(_SEALED_CLI_FLAGS)
            + "."
        )


def _write_compact_cli_json(value: object) -> None:
    """Write exactly one canonical compact JSON object with an LF terminator."""

    encoded = _canonical_bytes(value)
    stream = getattr(sys.stdout, "buffer", None)
    if stream is not None:
        stream.write(encoded)
        stream.flush()
        return
    sys.stdout.write(encoded.decode("utf-8"))
    sys.stdout.flush()


def main(argv: Sequence[str] | None = None) -> int:
    """Compile/write or verify read-only through the sealed direct-file CLI."""

    try:
        _require_sealed_cli_runtime()
        arguments = list(argv if argv is not None else sys.argv[1:])
        if len(arguments) == 2 and arguments[0] == "--candidate-receipt":
            compilation = compile_candidate_motion_config(Path(arguments[1]))
            verification = write_compiled_candidate_motion_config(compilation)
        elif (
            len(arguments) == 6
            and arguments[0] == "--verify-config"
            and arguments[2] == "--expected-config-sha256"
            and arguments[4] == "--candidate-receipt"
        ):
            verification = verify_compiled_candidate_motion_config_file(
                Path(arguments[1]),
                expected_config_sha256=arguments[3],
                candidate_receipt_path=Path(arguments[5]),
            )
        else:
            raise DesignCandidateMotionPolicyCompilerError(
                "Usage: design_candidate_motion_policy_compiler.py "
                "--candidate-receipt artifacts/website-candidates/<run-id>/candidate.v1.json "
                "or --verify-config <fixed-config-path> "
                "--expected-config-sha256 <UPPERCASE-SHA256> "
                "--candidate-receipt artifacts/website-candidates/<run-id>/candidate.v1.json"
            )
    except Exception as exc:
        _write_compact_cli_json(
            {
                "error": f"{type(exc).__name__}: {exc}",
                "passed": False,
                "state": "blocked",
            }
        )
        return 2
    _write_compact_cli_json(verification)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

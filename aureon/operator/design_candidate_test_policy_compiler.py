"""Compile one deterministic, non-worker-selectable candidate test policy.

The staged worker may produce a website candidate, but it may not choose test
identifiers, commands, arguments, interpreters, timeouts, trusted inputs, or a
source policy.  This module projects the fixed WebsiteOperator external-check
policy into four reviewed candidate-safe commands and explicitly defers the
composite visual release gate.

Compilation and verification are local-only controls.  They never execute a
test, mutate the canonical website, validate a candidate, package a release,
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
from typing import Any, cast

COMPILATION_SCHEMA = "aureon.design-candidate-test-policy-compilation.v2"
VERIFICATION_SCHEMA = "aureon.design-candidate-test-policy-verification.v2"
POLICY_SCHEMA = "aureon.design-candidate-test-policy.v1"

SOURCE_POLICY_PATH = "aureon/operator/website_operator.defaults.json"
STATIC_QA_TOOL_PATH = "aureon/operator/design_candidate_static_qa.py"
JAVASCRIPT_TOOL_PATH = "tools/aureon_candidate_javascript_syntax_v1.js"
TEST_EVIDENCE_TOOL_PATH = "aureon/operator/design_candidate_test_evidence.py"
COMPILER_TOOL_PATH = "aureon/operator/design_candidate_test_policy_compiler.py"
SECURE_WRITER_TOOL_PATH = "aureon/operator/secure_immutable_artifact.py"
CANDIDATE_CONTROL_TOOL_PATH = "aureon/operator/design_candidate_control.py"
SOURCE_CLOSURE_HELPER_PATH = "aureon/operator/design_candidate_source_closure.py"
SOURCE_CLOSURE_SCHEMA = "aureon.design-candidate-executable-source-closure.v1"
SOURCE_CLOSURE_ALGORITHM = "python-ast-local-raw-sha256-closure-v2"
SOURCE_CLOSURE_ROOTS = (
    "aureon/operator/design_candidate_motion_policy_compiler.py",
    SOURCE_CLOSURE_HELPER_PATH,
    "aureon/operator/design_candidate_test_policy_compiler.py",
)
CANONICAL_WEBSITE_PATH = "website"
POLICY_OUTPUT_ROOT = "artifacts/website-operator/candidate-test-policies"
EXPECTED_SOURCE_POLICY_SHA256 = "3956D6AACC2B122086D8E2AC1FBB93AB9D01750CAE9B693D2C6DB6148F31741D"

WEBSITE_OPERATOR_STATIC_COMMAND_ID = "candidate.website-operator-static.v1"
JAVASCRIPT_COMMAND_ID = "candidate.javascript-syntax.v1"
DESIGN_SYSTEM_COMMAND_ID = "candidate.v28-design-system-static.v1"
METADATA_ETHOS_COMMAND_ID = "candidate.v28-metadata-ethos-static.v1"
REQUIRED_COMMAND_IDS = (
    WEBSITE_OPERATOR_STATIC_COMMAND_ID,
    JAVASCRIPT_COMMAND_ID,
    DESIGN_SYSTEM_COMMAND_ID,
    METADATA_ETHOS_COMMAND_ID,
)

JAVASCRIPT_SOURCE_ID = "javascript-syntax"
DESIGN_SYSTEM_SOURCE_ID = "v28-design-system"
METADATA_ETHOS_SOURCE_ID = "v28-metadata-ethos"
COMPOSITE_SOURCE_ID = "v28-composite-visual-release-gate"
EXPECTED_SOURCE_IDS = (
    JAVASCRIPT_SOURCE_ID,
    DESIGN_SYSTEM_SOURCE_ID,
    METADATA_ETHOS_SOURCE_ID,
    COMPOSITE_SOURCE_ID,
)

EXPECTED_SOURCE_COMMANDS: dict[str, tuple[str, ...]] = {
    JAVASCRIPT_SOURCE_ID: (
        "node",
        "--check",
        "{site_root}/script.js",
    ),
    DESIGN_SYSTEM_SOURCE_ID: (
        "node",
        "{repo_root}/tools/aureon_website_design_audit_v28.js",
    ),
    METADATA_ETHOS_SOURCE_ID: (
        "node",
        "{repo_root}/tools/aureon_metadata_ethos_audit_v28.js",
    ),
    COMPOSITE_SOURCE_ID: (
        "node",
        "{repo_root}/tools/aureon_visual_release_gate_v28.js",
        "--repo-root",
        "{repo_root}",
        "--manifest",
        ("{repo_root}/docs/audits/AUREON_VISUAL_RELEASE_GATE_20260726T181742Z_V28.manifest.json"),
    ),
}

SOURCE_TO_CANDIDATE_COMMAND: dict[str, str | None] = {
    JAVASCRIPT_SOURCE_ID: JAVASCRIPT_COMMAND_ID,
    DESIGN_SYSTEM_SOURCE_ID: DESIGN_SYSTEM_COMMAND_ID,
    METADATA_ETHOS_SOURCE_ID: METADATA_ETHOS_COMMAND_ID,
    COMPOSITE_SOURCE_ID: None,
}

EXECUTION_POLICY = {
    "mode": "ordered-once-fail-fast",
    "shell": False,
    "inherit_environment": False,
    "network": "offline-intent-no-kernel-network-sandbox",
    "output_privacy": "sha256-only",
    "preserve_failures": True,
    "retry_count": 0,
}

AUTHORITY = {
    "scope": "deterministic compilation and replay of one exact local candidate test policy",
    "executable_source_ingress": (
        "sealed only by direct compiler-file execution; imported API is drift-check-only"
    ),
    "worker_command_selection": "none",
    "test_execution_authority": "none",
    "canonical_website_mutation": "none",
    "candidate_validation_authority": "none",
    "promotion_authority": "none",
    "package_authority": "none",
    "release_authority": "none",
    "deployment_authority": "none",
    "credential_access": "none",
    "composite_visual_gate": "deferred-not-passed",
}

_RUN_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}\Z")
_SHA256 = re.compile(r"[A-F0-9]{64}\Z")
_POLICY_ID = re.compile(r"candidate-suite-v2-[a-f0-9]{64}\Z")
_SEALED_CLI_FLAGS = ("-I", "-S", "-B")
_LOADED_COMPILER_SOURCE_SHA256 = hashlib.sha256(Path(__file__).read_bytes()).hexdigest().upper()
candidate_control: Any = None
test_evidence: Any = None
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
_COMPILATION_FIELDS = frozenset(
    {
        "schema",
        "state",
        "passed",
        "source_policy",
        "candidate",
        "mapping",
        "policy",
        "source_closure",
        "authority",
        "compilation_payload_sha256",
    }
)
_ISSUED_COMPILATIONS: set[str] = set()
_ISSUED_LOCK = threading.Lock()


class DesignCandidateTestPolicyCompilerError(ValueError):
    """The candidate, source policy, toolchain, or compiled policy is unsafe."""


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _json_sha256(value: object) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest().upper()


def _strict_json_equal(left: object, right: object) -> bool:
    try:
        return _canonical_bytes(left) == _canonical_bytes(right)
    except (TypeError, ValueError):
        return False


def _bytes_sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest().upper()


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
            raise DesignCandidateTestPolicyCompilerError(
                "Could not locate the repository for executable-source preflight."
            )
        root = found_root
    try:
        details = root.lstat()
    except OSError as exc:
        raise DesignCandidateTestPolicyCompilerError("Executable-source repository root is missing.") from exc
    reparse = int(getattr(details, "st_file_attributes", 0)) & int(
        getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    )
    if not stat.S_ISDIR(details.st_mode) or stat.S_ISLNK(details.st_mode) or reparse:
        raise DesignCandidateTestPolicyCompilerError(
            "Executable-source repository root must be an ordinary directory."
        )
    return root


def _bootstrap_read_file(root: Path, path: Path, *, label: str) -> tuple[Path, bytes]:
    lexical = Path(os.path.abspath(path if path.is_absolute() else root / path))
    try:
        relative = lexical.relative_to(root)
    except ValueError as exc:
        raise DesignCandidateTestPolicyCompilerError(f"{label} escapes the repository.") from exc
    if any(part in {"", ".", ".."} or ":" in part for part in relative.parts):
        raise DesignCandidateTestPolicyCompilerError(f"{label} has an aliased or alternate-data-stream path.")
    current = root
    try:
        for part in relative.parts:
            case_matches = sorted(
                entry.name for entry in os.scandir(current) if entry.name.casefold() == part.casefold()
            )
            if case_matches != [part]:
                raise DesignCandidateTestPolicyCompilerError(
                    f"{label} has a missing or case-aliased path component."
                )
            current = current / part
            details = current.lstat()
            reparse = int(getattr(details, "st_file_attributes", 0)) & int(
                getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
            )
            if stat.S_ISLNK(details.st_mode) or reparse:
                raise DesignCandidateTestPolicyCompilerError(
                    f"{label} may not traverse a link or reparse point."
                )
        before = lexical.lstat()
        if not stat.S_ISREG(before.st_mode) or int(before.st_nlink) != 1:
            raise DesignCandidateTestPolicyCompilerError(
                f"{label} must be an ordinary file with exactly one hard link."
            )
        raw = lexical.read_bytes()
        after = lexical.lstat()
    except DesignCandidateTestPolicyCompilerError:
        raise
    except OSError as exc:
        raise DesignCandidateTestPolicyCompilerError(f"{label} is missing or unreadable.") from exc
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
        raise DesignCandidateTestPolicyCompilerError(f"{label} changed while it was read.")
    return lexical, raw


def _bootstrap_strict_json(raw: bytes, *, label: str) -> dict[str, Any]:
    def pairs(values: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in values:
            if key in result:
                raise DesignCandidateTestPolicyCompilerError(f"{label} contains a duplicate JSON key.")
            result[key] = value
        return result

    def nonfinite(value: str) -> None:
        raise DesignCandidateTestPolicyCompilerError(f"{label} contains non-finite JSON: {value}.")

    try:
        value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=pairs,
            parse_constant=nonfinite,
        )
    except DesignCandidateTestPolicyCompilerError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise DesignCandidateTestPolicyCompilerError(f"{label} is not strict UTF-8 JSON.") from exc
    if not isinstance(value, dict):
        raise DesignCandidateTestPolicyCompilerError(f"{label} must be a JSON object.")
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
        raise DesignCandidateTestPolicyCompilerError(
            "Candidate receipt preflight path is not the exact staged path."
        )
    receipt = _bootstrap_strict_json(receipt_raw, label="Candidate receipt preflight")
    binding = receipt.get("validation_input")
    if not isinstance(binding, dict) or frozenset(binding) != frozenset(
        {"path", "file_sha256", "json_sha256", "payload_sha256"}
    ):
        raise DesignCandidateTestPolicyCompilerError(
            "Candidate receipt preflight validation-input binding is malformed."
        )
    validation_path = receipt_path.parent / "candidate-validation-input.v1.json"
    expected_validation_relative = validation_path.relative_to(root).as_posix()
    if binding.get("path") != expected_validation_relative:
        raise DesignCandidateTestPolicyCompilerError(
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
        or binding.get("json_sha256") != _json_sha256(validation)
        or binding.get("payload_sha256") != validation.get("payload_sha256")
    ):
        raise DesignCandidateTestPolicyCompilerError(
            "Candidate validation-input raw, canonical, or payload binding failed preflight."
        )
    unsigned_validation = dict(validation)
    validation_payload_sha256 = unsigned_validation.pop("payload_sha256", None)
    if (
        not isinstance(validation_payload_sha256, str)
        or _SHA256.fullmatch(validation_payload_sha256) is None
        or _json_sha256(unsigned_validation) != validation_payload_sha256
    ):
        raise DesignCandidateTestPolicyCompilerError(
            "Candidate validation-input payload self-hash failed preflight."
        )
    source_closure = validation.get("source_closure")
    if not isinstance(source_closure, dict) or not _strict_json_equal(
        receipt.get("source_closure"),
        source_closure,
    ):
        raise DesignCandidateTestPolicyCompilerError(
            "Candidate receipt and validation input do not bind one exact source closure."
        )
    if (
        frozenset(source_closure)
        != frozenset({"schema", "algorithm", "roots", "files", "exclusions", "manifest_sha256"})
        or source_closure.get("schema") != SOURCE_CLOSURE_SCHEMA
        or source_closure.get("algorithm") != SOURCE_CLOSURE_ALGORITHM
        or source_closure.get("roots") != list(SOURCE_CLOSURE_ROOTS)
    ):
        raise DesignCandidateTestPolicyCompilerError(
            "Executable-source closure bootstrap contract is invalid."
        )
    files = source_closure.get("files")
    if not isinstance(files, list) or not files:
        raise DesignCandidateTestPolicyCompilerError(
            "Executable-source closure bootstrap file list is empty."
        )
    if not isinstance(source_closure.get("exclusions"), list):
        raise DesignCandidateTestPolicyCompilerError(
            "Executable-source closure bootstrap exclusions are malformed."
        )
    paths: list[str] = []
    helper_row: dict[str, Any] | None = None
    for row in files:
        if not isinstance(row, dict) or frozenset(row) != frozenset({"path", "bytes", "sha256"}):
            raise DesignCandidateTestPolicyCompilerError(
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
            raise DesignCandidateTestPolicyCompilerError(
                "Executable-source closure bootstrap file row is unsafe."
            )
        paths.append(path)
        if path == SOURCE_CLOSURE_HELPER_PATH:
            helper_row = row
    if paths != sorted(set(paths)) or not set(SOURCE_CLOSURE_ROOTS).issubset(paths):
        raise DesignCandidateTestPolicyCompilerError(
            "Executable-source closure bootstrap paths are not exact, sorted, and unique."
        )
    unsigned_closure = dict(source_closure)
    manifest_sha256 = unsigned_closure.pop("manifest_sha256", None)
    if (
        not isinstance(manifest_sha256, str)
        or _SHA256.fullmatch(manifest_sha256) is None
        or _json_sha256(unsigned_closure) != manifest_sha256
        or helper_row is None
    ):
        raise DesignCandidateTestPolicyCompilerError(
            "Executable-source closure bootstrap self-hash or helper binding is invalid."
        )
    helper_path, helper_raw = _bootstrap_read_file(
        root,
        Path(SOURCE_CLOSURE_HELPER_PATH),
        label="Executable-source closure helper",
    )
    if len(helper_raw) != helper_row["bytes"] or _bytes_sha256(helper_raw) != helper_row["sha256"]:
        raise DesignCandidateTestPolicyCompilerError(
            "Executable-source closure helper raw bytes changed before authentication."
        )
    helper = ModuleType("_aureon_verified_design_candidate_source_closure")
    helper.__file__ = str(helper_path)
    helper.__package__ = ""
    try:
        exec(compile(helper_raw, str(helper_path), "exec"), helper.__dict__)  # noqa: S102
        helper.verify_source_closure(root, source_closure)
    except Exception as exc:
        raise DesignCandidateTestPolicyCompilerError(
            f"Executable-source closure preflight failed: {exc}"
        ) from exc
    return root, source_closure, helper


def _prepare_runtime(
    candidate_receipt_path: Path,
    *,
    repo_root: Path | None,
) -> tuple[Path, dict[str, Any]]:
    global candidate_control, secure_immutable_artifact, test_evidence
    global _verified_source_closure, _verified_source_finder
    global _verified_source_manifest_sha256

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
            raise DesignCandidateTestPolicyCompilerError(
                f"Verified raw-source importer could not be installed: {exc}"
            ) from exc
        _verified_source_manifest_sha256 = str(source_closure["manifest_sha256"])
    candidate_control = importlib.import_module("aureon.operator.design_candidate_control")
    test_evidence = importlib.import_module("aureon.operator.design_candidate_test_evidence")
    secure_immutable_artifact = importlib.import_module("aureon.operator.secure_immutable_artifact")
    _verified_source_closure = helper
    try:
        helper.verify_loaded_source_modules(
            source_closure,
            require_verified_loader=sealed_ingress,
        )
        helper.verify_source_closure(root, source_closure)
    except Exception as exc:
        raise DesignCandidateTestPolicyCompilerError(
            f"Loaded executable-source closure failed authentication: {exc}"
        ) from exc
    return root, source_closure


def _policy_bytes(value: Mapping[str, Any]) -> bytes:
    return (
        json.dumps(
            dict(value),
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
        + b"\n"
    )


def _require_exact_fields(
    value: Mapping[str, Any],
    expected: frozenset[str],
    *,
    label: str,
) -> None:
    actual = frozenset(value)
    if actual != expected:
        raise DesignCandidateTestPolicyCompilerError(
            f"{label} fields are not exact "
            f"(missing={sorted(expected - actual)}, extra={sorted(actual - expected)})."
        )


def _repo_relative(root: Path, path: Path, *, label: str) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError as exc:
        raise DesignCandidateTestPolicyCompilerError(f"{label} escapes the repository.") from exc


def _regular_file(root: Path, relative: str, *, label: str) -> Path:
    try:
        path = test_evidence._resolve_under(  # noqa: SLF001
            root,
            relative,
            label=label,
        )
    except test_evidence.DesignCandidateTestEvidenceError as exc:
        raise DesignCandidateTestPolicyCompilerError(str(exc)) from exc
    return cast(Path, path)


def _file_hash(root: Path, relative: str, *, label: str) -> str:
    path = _regular_file(root, relative, label=label)
    return cast(str, test_evidence._sha256_file(path))  # noqa: SLF001


def _assert_loaded_source_bindings(root: Path, source_closure: Mapping[str, Any]) -> None:
    if _verified_source_closure is None:
        raise DesignCandidateTestPolicyCompilerError(
            "Executable-source closure was not authenticated before local imports."
        )
    try:
        _verified_source_closure.verify_loaded_source_modules(
            source_closure,
            require_verified_loader=__name__ == "__main__" and __package__ in {None, ""},
        )
        _verified_source_closure.verify_source_closure(root, source_closure)
    except Exception as exc:
        raise DesignCandidateTestPolicyCompilerError(
            f"Executable-source closure changed after local imports: {exc}"
        ) from exc


def _strict_json(path: Path, *, label: str) -> tuple[dict[str, Any], bytes]:
    try:
        return cast(
            tuple[dict[str, Any], bytes],
            test_evidence._load_json_file(path, label=label),  # noqa: SLF001
        )
    except test_evidence.DesignCandidateTestEvidenceError as exc:
        raise DesignCandidateTestPolicyCompilerError(str(exc)) from exc


def _candidate_binding(
    root: Path,
    candidate_receipt_path: Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    try:
        receipt_path = test_evidence._regular_file(  # noqa: SLF001
            candidate_receipt_path,
            label="Candidate receipt",
            single_link=True,
        )
    except test_evidence.DesignCandidateTestEvidenceError as exc:
        raise DesignCandidateTestPolicyCompilerError(str(exc)) from exc
    relative = _repo_relative(root, receipt_path, label="Candidate receipt")
    parts = Path(relative).parts
    if (
        len(parts) != 4
        or parts[0:2] != ("artifacts", "website-candidates")
        or _RUN_ID.fullmatch(parts[2]) is None
        or parts[3] != "candidate.v1.json"
    ):
        raise DesignCandidateTestPolicyCompilerError(
            "Candidate receipt must be exactly artifacts/website-candidates/<run-id>/candidate.v1.json."
        )
    receipt, raw = _strict_json(receipt_path, label="Candidate receipt")
    try:
        candidate_control.require_candidate_receipt_contract(receipt)
    except candidate_control.DesignCandidateControlError as exc:
        raise DesignCandidateTestPolicyCompilerError(
            f"Candidate receipt runtime contract failed: {exc}"
        ) from exc
    _require_exact_fields(
        receipt,
        _CANDIDATE_RECEIPT_FIELDS,
        label="Candidate receipt",
    )
    work_order = receipt.get("work_order")
    if not isinstance(work_order, Mapping):
        raise DesignCandidateTestPolicyCompilerError("Candidate receipt lacks its work-order binding.")
    _require_exact_fields(
        work_order,
        _CANDIDATE_WORK_ORDER_FIELDS,
        label="Candidate receipt work-order binding",
    )
    try:
        candidate_control.require_current_work_order_binding(work_order, repo_root=root)
    except candidate_control.DesignCandidateControlError as exc:
        raise DesignCandidateTestPolicyCompilerError(
            f"Candidate work-order persisted-byte and JSON binding failed: {exc}"
        ) from exc
    candidate = receipt.get("candidate")
    if not isinstance(candidate, Mapping):
        raise DesignCandidateTestPolicyCompilerError("Candidate receipt lacks its candidate binding.")
    _require_exact_fields(
        candidate,
        _CANDIDATE_BINDING_FIELDS,
        label="Candidate receipt candidate binding",
    )
    website_path = f"artifacts/website-candidates/{parts[2]}/website"
    if (
        candidate.get("root") != f"artifacts/website-candidates/{parts[2]}"
        or candidate.get("website_path") != website_path
    ):
        raise DesignCandidateTestPolicyCompilerError(
            "Candidate receipt does not bind the deterministic staged layout."
        )
    try:
        website_root = test_evidence._resolve_under(  # noqa: SLF001
            root,
            website_path,
            label="Staged candidate website",
            directory=True,
        )
        summary = test_evidence._tree_summary(website_root)  # noqa: SLF001
        policy_binding = {
            "receipt_path": relative,
            "receipt_file_sha256": _bytes_sha256(raw),
            "receipt_json_sha256": _json_sha256(receipt),
            "tree_sha256": summary["tree_sha256"],
        }
        (
            loaded_receipt,
            loaded_path,
            candidate_root,
            loaded_website,
            loaded_summary,
            loaded_raw,
        ) = test_evidence._load_bound_candidate(  # noqa: SLF001
            root,
            policy_binding,
        )
    except test_evidence.DesignCandidateTestEvidenceError as exc:
        raise DesignCandidateTestPolicyCompilerError(str(exc)) from exc
    if (
        not _strict_json_equal(loaded_receipt, receipt)
        or loaded_path != receipt_path
        or loaded_website != website_root
        or loaded_raw != raw
        or not _strict_json_equal(loaded_summary, summary)
        or candidate_root != receipt_path.parent
    ):
        raise DesignCandidateTestPolicyCompilerError(
            "Candidate receipt replay did not preserve its exact staged binding."
        )
    try:
        full_verification = candidate_control.verify_staged_candidate_receipt(
            receipt,
            repo_root=root,
            _require_current_baseline=False,
        )
    except candidate_control.DesignCandidateControlError as exc:
        raise DesignCandidateTestPolicyCompilerError(
            f"Full staged-candidate and work-order verification failed: {exc}"
        ) from exc
    if (
        full_verification.get("schema") != candidate_control.VERIFICATION_SCHEMA
        or full_verification.get("passed") is not True
        or full_verification.get("release_eligible") is not False
        or full_verification.get("deployment_authority") != "none"
    ):
        failed_checks = [
            str(row.get("id"))
            for row in full_verification.get("checks", [])
            if isinstance(row, Mapping) and row.get("passed") is not True
        ]
        raise DesignCandidateTestPolicyCompilerError(
            f"Full staged-candidate and work-order verification did not pass (failed_checks={failed_checks})."
        )
    return (
        policy_binding,
        {
            **policy_binding,
            "root": _repo_relative(root, candidate_root, label="Candidate root"),
            "website_path": _repo_relative(root, website_root, label="Candidate website"),
            "file_count": summary["file_count"],
            "total_bytes": summary["total_bytes"],
        },
    )


def _source_policy(
    root: Path,
) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    source_path = _regular_file(root, SOURCE_POLICY_PATH, label="WebsiteOperator source policy")
    source, raw = _strict_json(source_path, label="WebsiteOperator source policy")
    if _bytes_sha256(raw) != EXPECTED_SOURCE_POLICY_SHA256:
        raise DesignCandidateTestPolicyCompilerError(
            "WebsiteOperator source policy bytes changed and require explicit code review; "
            "no budget, route, authority, or external-check change is accepted dynamically."
        )
    if source.get("schema") != "aureon.website-operator.config.v1":
        raise DesignCandidateTestPolicyCompilerError("WebsiteOperator source policy schema is unsupported.")
    checks = source.get("checks")
    external = checks.get("external") if isinstance(checks, Mapping) else None
    if not isinstance(external, list):
        raise DesignCandidateTestPolicyCompilerError(
            "WebsiteOperator source policy checks.external must be an array."
        )
    by_id: dict[str, Mapping[str, Any]] = {}
    optional_unknown_ids: list[str] = []
    required_source_ids: list[str] = []
    for index, row in enumerate(external):
        if not isinstance(row, Mapping):
            raise DesignCandidateTestPolicyCompilerError(f"External source check {index} must be an object.")
        identifier = row.get("id")
        if (
            not isinstance(identifier, str)
            or not identifier
            or identifier != identifier.strip()
            or identifier in by_id
        ):
            raise DesignCandidateTestPolicyCompilerError(
                "External source check ids must be non-empty, trimmed, and unique."
            )
        enabled = row.get("enabled", True)
        required = row.get("required", True)
        if not isinstance(enabled, bool) or not isinstance(required, bool):
            raise DesignCandidateTestPolicyCompilerError(
                f"External source check {identifier} must use boolean enabled/required controls."
            )
        command = row.get("command")
        if (
            not isinstance(command, list)
            or not command
            or not all(isinstance(token, str) and token for token in command)
        ):
            raise DesignCandidateTestPolicyCompilerError(
                f"External source check {identifier} command is malformed."
            )
        by_id[identifier] = row
        if enabled and required:
            required_source_ids.append(identifier)
            if identifier not in SOURCE_TO_CANDIDATE_COMMAND:
                raise DesignCandidateTestPolicyCompilerError(
                    f"Unknown required external source check blocks compilation: {identifier}"
                )
        elif identifier not in SOURCE_TO_CANDIDATE_COMMAND:
            optional_unknown_ids.append(identifier)

    missing = [identifier for identifier in EXPECTED_SOURCE_IDS if identifier not in by_id]
    if missing:
        raise DesignCandidateTestPolicyCompilerError(
            f"Required source-policy mappings are missing: {missing}"
        )
    mappings: list[dict[str, Any]] = []
    for identifier in EXPECTED_SOURCE_IDS:
        row = by_id[identifier]
        if row.get("enabled") is not True or row.get("required") is not True:
            raise DesignCandidateTestPolicyCompilerError(
                f"Expected source check must remain explicitly enabled and required: {identifier}"
            )
        command = row.get("command")
        expected_command = list(EXPECTED_SOURCE_COMMANDS[identifier])
        if command != expected_command:
            raise DesignCandidateTestPolicyCompilerError(
                f"Expected source command changed and requires operator review: {identifier}"
            )
        candidate_command = SOURCE_TO_CANDIDATE_COMMAND[identifier]
        mappings.append(
            {
                "source_id": identifier,
                "source_command_sha256": _json_sha256(command),
                "disposition": (
                    "deferred-to-source-bound-visual-review"
                    if candidate_command is None
                    else "adapted-to-read-only-candidate-command"
                ),
                "candidate_command_id": candidate_command,
            }
        )
    source_binding = {
        "path": SOURCE_POLICY_PATH,
        "file_sha256": _bytes_sha256(raw),
        "json_sha256": _json_sha256(source),
        "required_external_ids": required_source_ids,
        "required_external_ids_sha256": _json_sha256(required_source_ids),
        "optional_unknown_ids": optional_unknown_ids,
        "optional_unknown_ids_sha256": _json_sha256(optional_unknown_ids),
    }
    return source, source_binding, mappings


def _trusted_input(root: Path, relative: str) -> dict[str, str]:
    return {
        "path": relative,
        "sha256": _file_hash(root, relative, label=f"Trusted input {relative}"),
    }


def _command(
    root: Path,
    *,
    command_id: str,
    engine: str,
    argv: Sequence[str],
    trusted_input_paths: Sequence[str],
    timeout_seconds: int,
) -> dict[str, Any]:
    try:
        executable, _ = test_evidence._resolve_tool(engine)  # noqa: SLF001
    except test_evidence.DesignCandidateTestEvidenceError as exc:
        raise DesignCandidateTestPolicyCompilerError(str(exc)) from exc
    trusted_inputs = sorted(
        (_trusted_input(root, path) for path in trusted_input_paths),
        key=lambda item: item["path"],
    )
    template: dict[str, Any] = {
        "engine": engine,
        "argv": list(argv),
        "cwd": ".",
        "timeout_seconds": timeout_seconds,
        "viewport_widths": [],
        "trusted_inputs": trusted_inputs,
        "tool_executable_sha256": test_evidence._sha256_file(executable),  # noqa: SLF001
        "required_outputs": list(test_evidence.PROCESS_OUTPUTS),
    }
    return {
        "id": command_id,
        "template": template,
        "template_sha256": _json_sha256(template),
    }


def _commands(root: Path) -> list[dict[str, Any]]:
    python_inputs = (STATIC_QA_TOOL_PATH, SOURCE_POLICY_PATH)
    return [
        _command(
            root,
            command_id=WEBSITE_OPERATOR_STATIC_COMMAND_ID,
            engine="python",
            argv=(
                "{python}",
                "-I",
                f"{{repo_root}}/{STATIC_QA_TOOL_PATH}",
                "--mode",
                "website-operator-static",
                "--candidate-root",
                "{candidate_root}",
            ),
            trusted_input_paths=python_inputs,
            timeout_seconds=180,
        ),
        _command(
            root,
            command_id=JAVASCRIPT_COMMAND_ID,
            engine="node",
            argv=(
                "{node}",
                f"{{repo_root}}/{JAVASCRIPT_TOOL_PATH}",
                "{candidate_root}",
                "script.js",
                "funding/funding-status.js",
                "live/live.js",
            ),
            trusted_input_paths=(JAVASCRIPT_TOOL_PATH,),
            timeout_seconds=60,
        ),
        _command(
            root,
            command_id=DESIGN_SYSTEM_COMMAND_ID,
            engine="python",
            argv=(
                "{python}",
                "-I",
                f"{{repo_root}}/{STATIC_QA_TOOL_PATH}",
                "--mode",
                "v28-design-system-static",
                "--candidate-root",
                "{candidate_root}",
            ),
            trusted_input_paths=python_inputs,
            timeout_seconds=180,
        ),
        _command(
            root,
            command_id=METADATA_ETHOS_COMMAND_ID,
            engine="python",
            argv=(
                "{python}",
                "-I",
                f"{{repo_root}}/{STATIC_QA_TOOL_PATH}",
                "--mode",
                "v28-metadata-ethos-static",
                "--candidate-root",
                "{candidate_root}",
            ),
            trusted_input_paths=python_inputs,
            timeout_seconds=180,
        ),
    ]


def _repository_control(
    root: Path,
    commands: Sequence[Mapping[str, Any]],
    source_closure: Mapping[str, Any],
) -> dict[str, Any]:
    try:
        canonical_root = test_evidence._resolve_under(  # noqa: SLF001
            root,
            CANONICAL_WEBSITE_PATH,
            label="Canonical website",
            directory=True,
        )
        canonical_summary = test_evidence._tree_summary(canonical_root)  # noqa: SLF001
    except test_evidence.DesignCandidateTestEvidenceError as exc:
        raise DesignCandidateTestPolicyCompilerError(str(exc)) from exc
    paths = {
        "pyproject.toml",
    }
    source_files = source_closure.get("files")
    if not isinstance(source_files, list):
        raise DesignCandidateTestPolicyCompilerError(
            "Executable-source closure lost its repository-control rows."
        )
    for row in source_files:
        if not isinstance(row, Mapping) or not isinstance(row.get("path"), str):
            raise DesignCandidateTestPolicyCompilerError(
                "Executable-source closure repository-control row is malformed."
            )
        paths.add(str(row["path"]))
    for command in commands:
        template = command.get("template")
        trusted = template.get("trusted_inputs") if isinstance(template, Mapping) else None
        if not isinstance(trusted, list):
            raise DesignCandidateTestPolicyCompilerError("Internal command construction lost trusted inputs.")
        for row in trusted:
            if not isinstance(row, Mapping) or not isinstance(row.get("path"), str):
                raise DesignCandidateTestPolicyCompilerError(
                    "Internal trusted input construction is malformed."
                )
            paths.add(str(row["path"]))
    entries = [
        {
            "path": relative,
            "kind": "file",
            "sha256": _file_hash(root, relative, label=f"Repository control {relative}"),
        }
        for relative in sorted(paths)
    ]
    return {
        "canonical_website_path": CANONICAL_WEBSITE_PATH,
        "canonical_website_tree_sha256": canonical_summary["tree_sha256"],
        "entries": entries,
        "manifest_sha256": _json_sha256(entries),
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
    _assert_loaded_source_bindings(root, source_closure)
    input_path = (
        candidate_receipt_path if candidate_receipt_path.is_absolute() else root / candidate_receipt_path
    )
    policy_candidate, candidate_binding = _candidate_binding(root, input_path)
    _, source_binding, mappings = _source_policy(root)
    commands = _commands(root)
    if [command["id"] for command in commands] != list(REQUIRED_COMMAND_IDS):
        raise DesignCandidateTestPolicyCompilerError(
            "Internal command order drifted from the fixed required suite."
        )
    repository_control = _repository_control(root, commands, source_closure)
    policy_candidate_after, candidate_binding_after = _candidate_binding(root, input_path)
    _, source_binding_after, mappings_after = _source_policy(root)
    commands_after = _commands(root)
    repository_control_after = _repository_control(root, commands_after, source_closure)
    _assert_loaded_source_bindings(root, source_closure)
    if (
        policy_candidate_after != policy_candidate
        or candidate_binding_after != candidate_binding
        or source_binding_after != source_binding
        or mappings_after != mappings
        or commands_after != commands
        or repository_control_after != repository_control
    ):
        raise DesignCandidateTestPolicyCompilerError(
            "Candidate, source policy, trusted toolchain, interpreter, or canonical "
            "website changed during policy compilation."
        )
    mapping = {
        "baseline_command_id": WEBSITE_OPERATOR_STATIC_COMMAND_ID,
        "source_checks": mappings,
        "source_checks_sha256": _json_sha256(mappings),
        "deferred_source_ids": [COMPOSITE_SOURCE_ID],
        "deferred_source_ids_sha256": _json_sha256([COMPOSITE_SOURCE_ID]),
    }
    content_core = {
        "schema": "aureon.design-candidate-test-policy-content-core.v2",
        "candidate": policy_candidate,
        "source_policy": source_binding,
        "mapping": mapping,
        "repository_control": repository_control,
        "required_command_ids": list(REQUIRED_COMMAND_IDS),
        "commands": commands,
        "execution": dict(EXECUTION_POLICY),
        "policy_authority": dict(test_evidence.POLICY_AUTHORITY),
        "compiler": {
            "path": COMPILER_TOOL_PATH,
            "sha256": _LOADED_COMPILER_SOURCE_SHA256,
        },
    }
    content_core_sha256 = _json_sha256(content_core)
    policy_id = f"candidate-suite-v2-{content_core_sha256.lower()}"
    policy: dict[str, Any] = {
        "schema": POLICY_SCHEMA,
        "policy_id": policy_id,
        "candidate": policy_candidate,
        "repository_control": repository_control,
        "required_command_ids": list(REQUIRED_COMMAND_IDS),
        "commands": commands,
        "execution": dict(EXECUTION_POLICY),
        "authority": dict(test_evidence.POLICY_AUTHORITY),
    }
    encoded = _policy_bytes(policy)
    compilation: dict[str, Any] = {
        "schema": COMPILATION_SCHEMA,
        "state": "compiled-local",
        "passed": True,
        "source_policy": source_binding,
        "candidate": candidate_binding,
        "mapping": mapping,
        "source_closure": source_closure,
        "policy": {
            "policy_id": policy_id,
            "content_core_sha256": content_core_sha256,
            "required_command_ids": list(REQUIRED_COMMAND_IDS),
            "required_command_ids_sha256": _json_sha256(list(REQUIRED_COMMAND_IDS)),
            "json_sha256": _json_sha256(policy),
            "file_sha256": _bytes_sha256(encoded),
            "payload": policy,
        },
        "authority": dict(AUTHORITY),
    }
    compilation["compilation_payload_sha256"] = _json_sha256(compilation)
    if register:
        with _ISSUED_LOCK:
            _ISSUED_COMPILATIONS.add(str(compilation["compilation_payload_sha256"]))
    return compilation


def compile_candidate_test_policy(
    candidate_receipt_path: Path,
    *,
    repo_root: Path | None = None,
) -> dict[str, Any]:
    """Return one fixed policy; imported use is a trusted drift-check boundary."""

    return _compile(candidate_receipt_path, repo_root=repo_root, register=True)


def validate_candidate_test_policy_compilation(
    compilation: Mapping[str, Any],
    *,
    repo_root: Path | None = None,
) -> dict[str, Any]:
    """Replay a compilation against current candidate, source, tool and site bytes."""

    _require_exact_fields(compilation, _COMPILATION_FIELDS, label="Policy compilation")
    if (
        compilation.get("schema") != COMPILATION_SCHEMA
        or compilation.get("state") != "compiled-local"
        or compilation.get("passed") is not True
        or not _strict_json_equal(compilation.get("authority"), AUTHORITY)
    ):
        raise DesignCandidateTestPolicyCompilerError(
            "Policy compilation state or authority boundary is invalid."
        )
    payload = dict(compilation)
    recorded_hash = payload.pop("compilation_payload_sha256", None)
    if not isinstance(recorded_hash, str) or _SHA256.fullmatch(recorded_hash) is None:
        raise DesignCandidateTestPolicyCompilerError("Policy compilation payload hash is malformed.")
    if recorded_hash != _json_sha256(payload):
        raise DesignCandidateTestPolicyCompilerError("Policy compilation payload hash is invalid.")
    candidate = compilation.get("candidate")
    if not isinstance(candidate, Mapping) or not isinstance(candidate.get("receipt_path"), str):
        raise DesignCandidateTestPolicyCompilerError("Policy compilation candidate binding is missing.")
    expected = _compile(
        Path(str(candidate["receipt_path"])),
        repo_root=repo_root,
        register=False,
    )
    if not _strict_json_equal(compilation, expected):
        raise DesignCandidateTestPolicyCompilerError(
            "Policy compilation does not equal the fixed compiler replay."
        )
    policy = compilation.get("policy")
    if not isinstance(policy, Mapping):
        raise DesignCandidateTestPolicyCompilerError("Compiled policy binding is missing.")
    return {
        "schema": VERIFICATION_SCHEMA,
        "state": "pass",
        "passed": True,
        "verification_scope": (
            "deterministic compiler replay against current candidate, source policy, "
            "trusted tools, interpreters and canonical website"
        ),
        "compiler_replayed": True,
        "origin_attested": False,
        "candidate_receipt_path": candidate["receipt_path"],
        "candidate_tree_sha256": candidate["tree_sha256"],
        "source_policy_file_sha256": compilation["source_policy"]["file_sha256"],
        "policy_id": policy["policy_id"],
        "policy_content_core_sha256": policy["content_core_sha256"],
        "policy_file_sha256": policy["file_sha256"],
        "policy_json_sha256": policy["json_sha256"],
        "required_command_ids": policy["required_command_ids"],
        "deferred_source_ids": compilation["mapping"]["deferred_source_ids"],
        "authority": dict(AUTHORITY),
    }


def _policy_output_path(root: Path, policy_id: str, *, create_directory: bool) -> Path:
    if _POLICY_ID.fullmatch(policy_id) is None:
        raise DesignCandidateTestPolicyCompilerError(
            "Candidate policy id is not the exact v2 content address."
        )
    parent = root / POLICY_OUTPUT_ROOT
    try:
        parent_parent = test_evidence._regular_directory(  # noqa: SLF001
            parent.parent,
            label="Candidate policy output parent",
        )
    except test_evidence.DesignCandidateTestEvidenceError as exc:
        raise DesignCandidateTestPolicyCompilerError(str(exc)) from exc
    if parent.exists() or parent.is_symlink():
        try:
            safe_parent = test_evidence._regular_directory(  # noqa: SLF001
                parent,
                label="Candidate policy output directory",
            )
        except test_evidence.DesignCandidateTestEvidenceError as exc:
            raise DesignCandidateTestPolicyCompilerError(str(exc)) from exc
    elif create_directory:
        try:
            os.mkdir(parent, 0o700)
        except OSError as exc:
            raise DesignCandidateTestPolicyCompilerError(
                "Candidate policy output directory could not be created safely."
            ) from exc
        try:
            safe_parent = test_evidence._regular_directory(  # noqa: SLF001
                parent,
                label="Candidate policy output directory",
            )
        except test_evidence.DesignCandidateTestEvidenceError as exc:
            raise DesignCandidateTestPolicyCompilerError(str(exc)) from exc
    else:
        raise DesignCandidateTestPolicyCompilerError("Candidate policy output directory does not exist.")
    if safe_parent.parent != parent_parent:
        raise DesignCandidateTestPolicyCompilerError(
            "Candidate policy output directory changed during resolution."
        )
    output = safe_parent / f"{policy_id}.json"
    try:
        secure_immutable_artifact.validate_no_alternate_stream_path(
            output,
            label="Candidate policy output path",
        )
    except secure_immutable_artifact.SecureImmutableArtifactError as exc:
        raise DesignCandidateTestPolicyCompilerError(str(exc)) from exc
    if output.parent != safe_parent:
        raise DesignCandidateTestPolicyCompilerError("Candidate policy output path escaped.")
    return cast(Path, output)


def verify_compiled_candidate_test_policy_file(
    policy_path: Path,
    *,
    expected_policy_sha256: str,
    candidate_receipt_path: Path,
    repo_root: Path | None = None,
) -> dict[str, Any]:
    """Reject policy shopping by replaying the fixed compiler and exact file bytes."""

    if _SHA256.fullmatch(expected_policy_sha256) is None:
        raise DesignCandidateTestPolicyCompilerError(
            "Expected compiled policy hash must be an uppercase SHA-256."
        )
    expected = _compile(
        candidate_receipt_path,
        repo_root=repo_root,
        register=False,
    )
    try:
        secure_immutable_artifact.validate_no_alternate_stream_path(
            policy_path,
            label="Compiled candidate test policy path",
        )
        secure_immutable_artifact.validate_no_alternate_stream_path(
            candidate_receipt_path,
            label="Candidate receipt path",
        )
    except secure_immutable_artifact.SecureImmutableArtifactError as exc:
        raise DesignCandidateTestPolicyCompilerError(str(exc)) from exc
    try:
        root = test_evidence._find_repo_root(repo_root)  # noqa: SLF001
    except test_evidence.DesignCandidateTestEvidenceError as exc:
        raise DesignCandidateTestPolicyCompilerError(str(exc)) from exc
    policy_binding = expected["policy"]
    expected_output = _policy_output_path(
        root,
        str(policy_binding["policy_id"]),
        create_directory=False,
    )
    input_path = policy_path if policy_path.is_absolute() else root / policy_path
    try:
        input_file = test_evidence._regular_file(  # noqa: SLF001
            input_path,
            label="Compiled candidate test policy",
            single_link=True,
        )
    except test_evidence.DesignCandidateTestEvidenceError as exc:
        raise DesignCandidateTestPolicyCompilerError(str(exc)) from exc
    if input_file != expected_output:
        raise DesignCandidateTestPolicyCompilerError(
            "Compiled candidate test policy is not at the fixed compiler path."
        )
    raw = input_file.read_bytes()
    if (
        _bytes_sha256(raw) != expected_policy_sha256
        or expected_policy_sha256 != policy_binding["file_sha256"]
        or raw != _policy_bytes(policy_binding["payload"])
    ):
        raise DesignCandidateTestPolicyCompilerError(
            "Compiled candidate test policy bytes do not equal the fixed compiler output."
        )
    try:
        test_evidence._load_policy(  # noqa: SLF001
            input_file,
            expected_policy_sha256=expected_policy_sha256,
            root=root,
        )
    except test_evidence.DesignCandidateTestEvidenceError as exc:
        raise DesignCandidateTestPolicyCompilerError(str(exc)) from exc
    candidate = expected["candidate"]
    source = expected["source_policy"]
    mapping = expected["mapping"]
    return {
        "schema": VERIFICATION_SCHEMA,
        "state": "pass",
        "passed": True,
        "verification_scope": (
            "exact file bytes plus deterministic compiler replay and test-evidence parser acceptance"
        ),
        "compiler_replayed": True,
        "origin_attested": False,
        "candidate_receipt_path": candidate["receipt_path"],
        "candidate_tree_sha256": candidate["tree_sha256"],
        "source_policy_file_sha256": source["file_sha256"],
        "policy_path": _repo_relative(root, input_file, label="Compiled policy"),
        "policy_id": policy_binding["policy_id"],
        "policy_content_core_sha256": policy_binding["content_core_sha256"],
        "policy_file_sha256": policy_binding["file_sha256"],
        "policy_json_sha256": policy_binding["json_sha256"],
        "required_command_ids": policy_binding["required_command_ids"],
        "deferred_source_ids": mapping["deferred_source_ids"],
        "authority": dict(AUTHORITY),
    }


def write_compiled_candidate_test_policy(
    compilation: Mapping[str, Any],
    *,
    repo_root: Path | None = None,
) -> dict[str, Any]:
    """Create one immutable fixed-path policy from a fresh same-process compilation."""

    issued_hash = compilation.get("compilation_payload_sha256")
    with _ISSUED_LOCK:
        if not isinstance(issued_hash, str) or issued_hash not in _ISSUED_COMPILATIONS:
            raise DesignCandidateTestPolicyCompilerError(
                "Policy writer accepts only a fresh same-process fixed-compiler result."
            )
        _ISSUED_COMPILATIONS.remove(issued_hash)
    validate_candidate_test_policy_compilation(compilation, repo_root=repo_root)
    try:
        root = test_evidence._find_repo_root(repo_root)  # noqa: SLF001
    except test_evidence.DesignCandidateTestEvidenceError as exc:
        raise DesignCandidateTestPolicyCompilerError(str(exc)) from exc
    policy_binding = compilation["policy"]
    policy = policy_binding["payload"]
    output = _policy_output_path(
        root,
        str(policy_binding["policy_id"]),
        create_directory=True,
    )
    encoded = _policy_bytes(policy)
    if not output.exists() and not output.is_symlink():
        try:
            secure_immutable_artifact.write_new_file(output, encoded)
        except secure_immutable_artifact.SecureImmutableArtifactError as exc:
            if not output.is_file():
                raise DesignCandidateTestPolicyCompilerError(
                    f"Compiled candidate test policy could not be created safely: {exc}"
                ) from exc
    return verify_compiled_candidate_test_policy_file(
        output,
        expected_policy_sha256=str(policy_binding["file_sha256"]),
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
        raise DesignCandidateTestPolicyCompilerError(
            "Compiler CLI requires direct isolated file execution with python "
            + " ".join(_SEALED_CLI_FLAGS)
            + "."
        )


def _write_compact_cli_json(value: object) -> None:
    """Write exactly one canonical compact JSON object with an LF terminator."""

    encoded = _canonical_bytes(value) + b"\n"
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
            compilation = compile_candidate_test_policy(Path(arguments[1]))
            verification = write_compiled_candidate_test_policy(compilation)
        elif (
            len(arguments) == 6
            and arguments[0] == "--verify-policy"
            and arguments[2] == "--expected-policy-sha256"
            and arguments[4] == "--candidate-receipt"
        ):
            verification = verify_compiled_candidate_test_policy_file(
                Path(arguments[1]),
                expected_policy_sha256=arguments[3],
                candidate_receipt_path=Path(arguments[5]),
            )
        else:
            raise DesignCandidateTestPolicyCompilerError(
                "Usage: design_candidate_test_policy_compiler.py "
                "--candidate-receipt artifacts/website-candidates/<run-id>/candidate.v1.json "
                "or --verify-policy <fixed-policy-path> "
                "--expected-policy-sha256 <UPPERCASE-SHA256> "
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

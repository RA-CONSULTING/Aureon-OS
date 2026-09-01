"""Aureon-authored, proposal-only internal patch loop.

The internal coding workforce observes a bounded source file, deliberates,
authors one unified diff, validates its exact shape, and must seal it through
the local Plumber proposal forge before SafeCodeControl receives a metadata-
only review record.  This module deliberately has no repository mutation path:
the checked-in Plumber and Magic Star components are local-development controls
and cannot grant production release authority.

No Codex implementation receipt is created here.  A valid local result proves
only a transient HNC seal and remains HOLD; it is explicitly not recoverable or
pending review because no durable authenticated proposal vault exists.  A future
review/release service must consume ciphertext through an independently reviewed
production boundary; that service is not implemented by this module.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import time
from dataclasses import asdict, dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Sequence

from aureon.autonomous.aureon_agent_company_brain_fabric import (
    CANONICAL_AGENT_COMPANY_ROLE_COUNT,
)
from aureon.autonomous.aureon_internal_coding_workforce import (
    INTERNAL_AUTHOR_MAX_TOKENS,
    InternalCodingWorkforce,
)
from aureon.autonomous.aureon_safe_code_control import CodeProposal, SafeCodeControl
from aureon.plumber.proposal_forge import (
    LocalProposalForge,
    OpaqueProposalHandle,
    ProposalForgeError,
    QuarantinedProposal,
)

SCHEMA_VERSION = "aureon-internal-patch-cycle-v2"
MAX_SOURCE_BYTES = 512 * 1024
MAX_PATCH_BYTES = 128 * 1024
MAX_GOAL_BYTES = 8 * 1024
MAX_CHANGED_LINES = 500
MAX_WORKFORCE_PROMPT_CHARS = 65_536
MAX_COUNCIL_EXCERPT_CHARS = 1_500
MAX_PRE_APPLY_PROPOSAL_CHARS = 48_000
BLOCKED_PATH_TOKENS = (
    ".env",
    "credential",
    "credentials",
    "secret",
    "secrets",
    "private_key",
    "live_order",
    "order_router",
    "payment",
    "filing",
    "hmrc",
    "companies_house",
)
SECRET_SOURCE_PATTERNS = (
    re.compile(r"BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY", re.I),
    re.compile(r"\bsk_(?:live|proj)_[A-Za-z0-9_-]{12,}", re.I),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"(?i)(api[_-]?secret|password|private[_-]?key)\s*=\s*['\"][^'\"]{6,}"),
)
REPAIRABLE_AUTHORING_HOLDS = frozenset(
    {
        "authored_diff_git_apply_check_failed",
        "model_response_did_not_contain_unified_diff",
        "unified_diff_shape_required",
    }
)
PRE_APPLY_COUNCIL_ROLES = (
    "Code Architect",
    "Test Pilot",
    "CISO Secret Keeper",
    "Security Auditor",
    "Release Manager",
    "Risk Governor",
    "Evidence Clerk",
    "Archive Librarian",
)
PRE_APPLY_COUNCIL_REVIEWER = "aureon:pre_apply_council"
PROTECTED_PROPOSAL_SCHEMA = "aureon-internal-hnc-proposal-binding-v1"


class InternalPatchHold(RuntimeError):
    """Raised when an internally authored proposal cannot safely proceed."""


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _canonical_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)


def _evidence_digest(payload: dict[str, Any]) -> str:
    return _sha256_bytes(_canonical_json(payload).encode("utf-8"))


def _metadata_only_request(request: "InternalPatchRequest") -> dict[str, Any]:
    """Return review metadata without retaining the goal or command arguments."""

    return {
        "schema_version": "aureon-internal-patch-request-summary-v1",
        "request_sha256": _evidence_digest(request.to_dict()),
        "goal_sha256": _sha256_bytes(request.goal.encode("utf-8")),
        "target_path": request.target_path,
        "expected_source_sha256": request.expected_source_sha256,
        "test_commands_sha256": _evidence_digest(
            {"test_commands": [list(command) for command in request.test_commands]}
        ),
        "test_command_count": len(request.test_commands),
        "raw_goal_included": False,
        "raw_test_commands_included": False,
    }


def _metadata_only_deliberation(deliberation: dict[str, Any]) -> dict[str, Any]:
    """Commit to every decision while omitting untrusted model prose."""

    decisions: list[dict[str, Any]] = []
    for item in deliberation.get("decisions") or ():
        if not isinstance(item, dict):
            continue
        decisions.append(
            {
                "role": str(item.get("role") or ""),
                "process_id": str(item.get("process_id") or ""),
                "lane": str(item.get("lane") or ""),
                "agent_decision_sha256": _sha256_bytes(
                    str(item.get("agent_decision") or "").encode("utf-8")
                ),
                "process_decision_sha256": _sha256_bytes(
                    str(item.get("process_decision") or "").encode("utf-8")
                ),
                "agent_verdict": str(item.get("agent_verdict") or ""),
                "process_verdict": str(item.get("process_verdict") or ""),
                "agent_work_receipt_id": str(item.get("agent_work_receipt_id") or ""),
                "process_work_receipt_id": str(item.get("process_work_receipt_id") or ""),
                "raw_decisions_included": False,
            }
        )
    return {
        key: value
        for key, value in deliberation.items()
        if key != "decisions"
    } | {
        "deliberation_sha256": _evidence_digest(deliberation),
        "decisions": decisions,
        "raw_decisions_included": False,
    }


def _implementation_passport(report: dict[str, Any]) -> dict[str, Any]:
    matches = [
        item
        for item in report.get("passports") or ()
        if isinstance(item, dict)
        and item.get("subject_type") == "agent"
        and item.get("subject_id") == "Implementation Worker"
        and item.get("brain_ready") is True
    ]
    if len(matches) != 1:
        raise InternalPatchHold("implementation_worker_brain_passport_required")
    return matches[0]


def _forge_model_id(passport: dict[str, Any]) -> str:
    model = str(passport.get("model") or "").strip()
    if not model:
        raise InternalPatchHold("implementation_worker_model_id_required")
    if model.startswith(("ollama:", "aureon-local:")):
        return model
    return f"ollama:{model}"


def _council_receipt_ids(council: dict[str, Any]) -> list[str]:
    return [
        receipt_id
        for item in council.get("decisions") or ()
        if isinstance(item, dict)
        for receipt_id in (
            str(item.get("agent_work_receipt_id") or ""),
            str(item.get("process_work_receipt_id") or ""),
        )
        if receipt_id
    ]


def _protected_provenance(
    *,
    request: "InternalPatchRequest",
    base_commit: str,
    deliberation_digest: str,
    author_prompt_context: dict[str, Any],
    author_work_receipt_ids: list[str],
    patch_validation: dict[str, Any],
    git_apply_check: dict[str, Any],
    structural_canonicalization: dict[str, Any],
    pre_apply_council: dict[str, Any],
    pre_apply_council_digest: str,
    workforce_report: dict[str, Any],
) -> dict[str, Any]:
    passport = _implementation_passport(workforce_report)
    return {
        "schema_version": PROTECTED_PROPOSAL_SCHEMA,
        "artifact_origin": "Aureon",
        "generator_role": "Implementation Worker",
        "openai_role": "adviser_and_reviewer_only",
        "openai_implementation": False,
        "ownership_claim": "none",
        "base_commit": base_commit,
        "request_sha256": _evidence_digest(request.to_dict()),
        "target_path": request.target_path,
        "expected_source_sha256": request.expected_source_sha256,
        "deliberation_sha256": deliberation_digest,
        "author_prompt_context_sha256": _evidence_digest(author_prompt_context),
        "author_work_receipt_ids": list(author_work_receipt_ids),
        "patch_validation_sha256": _evidence_digest(patch_validation),
        "git_apply_check_sha256": _evidence_digest(git_apply_check),
        "structural_canonicalization_sha256": _evidence_digest(
            structural_canonicalization
        ),
        "pre_apply_council_sha256": pre_apply_council_digest,
        "pre_apply_council_work_receipt_ids": _council_receipt_ids(
            pre_apply_council
        ),
        "implementation_brain_passport_id": str(passport.get("receipt_id") or ""),
        "implementation_hnc_routing_receipt_id": str(
            passport.get("routing_receipt_id") or ""
        ),
        "implementation_hnc_receipt_id": str(passport.get("hnc_receipt_id") or ""),
        "workforce_report_sha256": _evidence_digest(workforce_report),
        "repository_mutation_authorized": False,
        "generated_code_execution_authorized": False,
        "action_eligible": False,
        "economic_eligible": False,
    }


def _exact_pre_apply_council_accepted(council: dict[str, Any]) -> bool:
    decisions = council.get("decisions")
    if not isinstance(decisions, list) or len(decisions) != len(PRE_APPLY_COUNCIL_ROLES):
        return False
    if tuple(item.get("role") for item in decisions if isinstance(item, dict)) != PRE_APPLY_COUNCIL_ROLES:
        return False
    receipt_ids: list[str] = []
    for item in decisions:
        if not isinstance(item, dict):
            return False
        if item.get("agent_verdict") != "ACCEPT" or item.get("process_verdict") != "ACCEPT":
            return False
        if not str(item.get("process_id") or "").strip():
            return False
        for key in ("agent_work_receipt_id", "process_work_receipt_id"):
            receipt_id = str(item.get(key) or "").strip()
            if not receipt_id:
                return False
            receipt_ids.append(receipt_id)
    return (
        council.get("schema_version") == "aureon-internal-coding-deliberation-v1"
        and council.get("status") == "complete"
        and council.get("scope_locked") is True
        and council.get("decision_mode") == "accept_hold"
        and council.get("accepted") is True
        and council.get("hold_count") == 0
        and council.get("active_agent_count") == len(PRE_APPLY_COUNCIL_ROLES)
        and council.get("decision_count") == len(PRE_APPLY_COUNCIL_ROLES) * 2
        and len(receipt_ids) == len(PRE_APPLY_COUNCIL_ROLES) * 2
        and len(set(receipt_ids)) == len(receipt_ids)
    )


def _record_exact_council_proposal_hold(
    controller: SafeCodeControl,
    proposal: dict[str, Any],
) -> dict[str, Any]:
    pending_matches = [item for item in controller.pending_proposals if item is proposal]
    if proposal.get("status") != "pending_review" or len(pending_matches) != 1:
        raise InternalPatchHold("pre_apply_proposal_queue_binding_invalid")

    original_proposal = dict(proposal)
    original_pending = list(controller.pending_proposals)
    original_recent = list(controller.recent_reviews)
    try:
        controller.pending_proposals = [
            item for item in controller.pending_proposals if item is not proposal
        ]
        proposal["status"] = "proposal_reviewed_hold"
        proposal["reviewed_at"] = time.time()
        proposal["reviewer"] = PRE_APPLY_COUNCIL_REVIEWER
        proposal["approval_scope"] = "proposal_review_only"
        proposal["proposal_only"] = True
        proposal["execution_authorized"] = False
        proposal["release_authorized"] = False
        proposal["production_ready"] = False
        controller.recent_reviews.append(proposal)
        controller.recent_reviews = controller.recent_reviews[-controller.max_recent :]
        controller._persist()
    except Exception as exc:
        proposal.clear()
        proposal.update(original_proposal)
        controller.pending_proposals = original_pending
        controller.recent_reviews = original_recent
        try:
            controller._persist()
        except Exception:
            pass
        raise InternalPatchHold("pre_apply_proposal_approval_persist_failed") from exc
    return proposal


def _bounded_council_context(
    deliberation: dict[str, Any],
    *,
    prompt_prefix: str,
    prompt_suffix: str,
) -> tuple[str, dict[str, Any]]:
    """Fit useful council excerpts without truncating source or causal hashes."""

    decisions = [item for item in deliberation.get("decisions", []) if isinstance(item, dict)]
    if not decisions:
        raise InternalPatchHold("council_decisions_required_for_author_prompt")

    def render(excerpt_chars: int) -> str:
        context = [
            {
                "role": str(item.get("role") or ""),
                "process_id": str(item.get("process_id") or ""),
                "process_decision_sha256": _sha256_bytes(
                    str(item.get("process_decision") or "").encode("utf-8")
                ),
                "process_decision_excerpt": str(item.get("process_decision") or "")[:excerpt_chars],
            }
            for item in decisions
        ]
        return _canonical_json(context)

    minimum = render(0)
    if len(prompt_prefix) + len(minimum) + len(prompt_suffix) > MAX_WORKFORCE_PROMPT_CHARS:
        raise InternalPatchHold("author_prompt_minimum_context_exceeds_limit")

    low, high = 0, MAX_COUNCIL_EXCERPT_CHARS
    while low < high:
        candidate = (low + high + 1) // 2
        if len(prompt_prefix) + len(render(candidate)) + len(prompt_suffix) <= MAX_WORKFORCE_PROMPT_CHARS:
            low = candidate
        else:
            high = candidate - 1
    context_json = render(low)
    prompt_chars = len(prompt_prefix) + len(context_json) + len(prompt_suffix)
    if prompt_chars > MAX_WORKFORCE_PROMPT_CHARS:
        raise InternalPatchHold("author_prompt_limit_proof_failed")
    return context_json, {
        "schema_version": "aureon-author-prompt-context-v1",
        "decision_count": len(decisions),
        "excerpt_char_limit": low,
        "context_digest": _sha256_bytes(context_json.encode("utf-8")),
        "prompt_char_count": prompt_chars,
        "prompt_char_limit": MAX_WORKFORCE_PROMPT_CHARS,
        "full_source_preserved": True,
        "all_decisions_digest_bound": True,
    }


def _normalize_target(value: str) -> str:
    raw = str(value or "").strip().replace("\\", "/")
    path = PurePosixPath(raw)
    if not raw or path.is_absolute() or ".." in path.parts or raw.startswith("/"):
        raise InternalPatchHold("target_path_must_be_repo_relative")
    normalized = path.as_posix()
    if any(token in normalized.lower() for token in BLOCKED_PATH_TOKENS):
        raise InternalPatchHold("target_path_is_authority_or_secret_bearing")
    return normalized


def _extract_diff(text: str) -> str:
    value = str(text or "").strip()
    fenced = re.search(r"```(?:diff|patch)?\s*\n(.*?)```", value, flags=re.I | re.S)
    if fenced:
        value = fenced.group(1).strip()
    start_candidates = [offset for token in ("diff --git ", "--- ") if (offset := value.find(token)) >= 0]
    if not start_candidates:
        raise InternalPatchHold("model_response_did_not_contain_unified_diff")
    value = value[min(start_candidates) :].strip() + "\n"
    if len(value.encode("utf-8")) > MAX_PATCH_BYTES:
        raise InternalPatchHold("patch_exceeds_size_limit")
    if "\x00" in value or "GIT binary patch" in value:
        raise InternalPatchHold("binary_patch_forbidden")
    return value


def _diff_targets(patch_text: str) -> list[str]:
    targets: list[str] = []
    for line in patch_text.splitlines():
        if not (line.startswith("--- ") or line.startswith("+++ ")):
            continue
        raw = line[4:].strip().split("\t", 1)[0]
        if raw == "/dev/null":
            continue
        raw = re.sub(r"^[ab]/", "", raw)
        target = _normalize_target(raw)
        if target not in targets:
            targets.append(target)
    return targets


def _validate_authored_diff(patch_text: str, *, target_path: str) -> dict[str, Any]:
    if "--- " not in patch_text or "+++ " not in patch_text or "@@" not in patch_text:
        raise InternalPatchHold("unified_diff_shape_required")
    targets = _diff_targets(patch_text)
    if targets != [target_path]:
        raise InternalPatchHold("patch_target_mismatch")
    changed_lines = sum(
        1
        for line in patch_text.splitlines()
        if (line.startswith("+") and not line.startswith("+++"))
        or (line.startswith("-") and not line.startswith("---"))
    )
    if changed_lines < 1 or changed_lines > MAX_CHANGED_LINES:
        raise InternalPatchHold("patch_changed_line_limit_failed")
    return {
        "target_paths": targets,
        "changed_line_count": changed_lines,
        "patch_sha256": _sha256_bytes(patch_text.encode("utf-8")),
        "patch_bytes": len(patch_text.encode("utf-8")),
    }


def _git_apply_check(root: Path, patch_text: str) -> dict[str, Any]:
    command = ["git", "apply", "--whitespace=nowarn", "--check"]
    try:
        proc = subprocess.run(
            command,
            cwd=root,
            input=patch_text,
            text=True,
            encoding="utf-8",
            errors="strict",
            capture_output=True,
            timeout=30,
        )
    except Exception as exc:
        return {
            "ok": False,
            "command": command,
            "check_only": True,
            "filesystem_mutation_attempted": False,
            "error_type": type(exc).__name__,
        }
    return {
        "ok": proc.returncode == 0,
        "command": command,
        "check_only": True,
        "filesystem_mutation_attempted": False,
        "returncode": proc.returncode,
        "stdout": proc.stdout[-2_000:],
        "stderr": proc.stderr[-2_000:],
    }


def _canonicalize_full_replacement_diff(
    *,
    source: str,
    patch_text: str,
    target_path: str,
) -> tuple[str, dict[str, Any]]:
    """Mechanically repair hunk counts for one exact full-file replacement.

    This is deliberately narrower than a general diff repairer. It accepts no
    metadata, second hunk, or partial source coverage. Context and removal lines
    must replay the immutable source in exact order, so model-authored content
    cannot gain scope or silently change while its structural counts are
    canonicalized.
    """

    newline = chr(10)
    lines = patch_text.rstrip(newline).split(newline)
    expected_old = source.splitlines()
    expected_from = f"--- a/{target_path}"
    expected_to = f"+++ b/{target_path}"
    if len(lines) < 4 or lines[0] != expected_from or lines[1] != expected_to:
        raise InternalPatchHold("full_replacement_canonicalization_headers_invalid")
    if not lines[2].startswith("@@ ") or "@@" not in lines[2][3:]:
        raise InternalPatchHold("full_replacement_canonicalization_hunk_invalid")
    body = lines[3:]
    if not body or any(line.startswith(("@@", "diff --git ", "--- ", "+++ ")) for line in body):
        raise InternalPatchHold("full_replacement_canonicalization_multiple_sections")
    if any(not line.startswith(("-", "+", " ")) for line in body):
        raise InternalPatchHold("full_replacement_canonicalization_body_invalid")
    source_index = 0
    result_lines: list[str] = []
    model_additions: list[str] = []
    removed_line_count = 0
    context_line_count = 0
    for line in body:
        prefix, content = line[0], line[1:]
        if prefix in {"-", " "}:
            if source_index >= len(expected_old) or content != expected_old[source_index]:
                raise InternalPatchHold("full_replacement_canonicalization_source_mismatch")
            source_index += 1
            if prefix == " ":
                context_line_count += 1
                result_lines.append(content)
            else:
                removed_line_count += 1
        else:
            model_additions.append(content)
            result_lines.append(content)
    if source_index != len(expected_old):
        raise InternalPatchHold("full_replacement_canonicalization_source_mismatch")
    if not model_additions or not result_lines:
        raise InternalPatchHold("full_replacement_canonicalization_empty_result")
    model_additions_text = newline.join(model_additions) + newline
    candidate_text = newline.join(result_lines) + newline
    if any(pattern.search(candidate_text) for pattern in SECRET_SOURCE_PATTERNS):
        raise InternalPatchHold("full_replacement_canonicalization_secret_scan_failed")
    canonical_lines = [
        expected_from,
        expected_to,
        f"@@ -1,{len(expected_old)} +1,{len(result_lines)} @@",
        *[f"-{line}" for line in expected_old],
        *[f"+{line}" for line in result_lines],
    ]
    canonical = newline.join(canonical_lines) + newline
    if len(canonical.encode("utf-8")) > MAX_PATCH_BYTES:
        raise InternalPatchHold("full_replacement_canonicalization_size_limit_failed")
    original_digest = _sha256_bytes(patch_text.encode("utf-8"))
    canonical_digest = _sha256_bytes(canonical.encode("utf-8"))
    return canonical, {
        "schema_version": "aureon-full-replacement-canonicalization-v1",
        "used": True,
        "target_path": target_path,
        "immutable_source_sha256": _sha256_bytes(source.encode("utf-8")),
        "source_line_count": len(expected_old),
        "source_lines_consumed": source_index,
        "removed_line_count": removed_line_count,
        "context_line_count": context_line_count,
        "added_line_count": len(result_lines),
        "model_addition_line_count": len(model_additions),
        "model_additions_sha256": _sha256_bytes(model_additions_text.encode("utf-8")),
        "candidate_source_sha256": _sha256_bytes(candidate_text.encode("utf-8")),
        "original_patch_sha256": original_digest,
        "canonical_patch_sha256": canonical_digest,
        "model_additions_preserved": True,
        "source_coverage_complete": True,
        "action_eligible": False,
        "economic_eligible": False,
    }


def _build_pre_apply_council_prompt(
    *,
    binding: dict[str, Any],
    patch_text: str,
) -> str:
    prompt = (
        "PRE-APPLY COUNCIL. Review this complete exact digest-bound coding proposal. "
        "Do not request tools and do not claim execution. The expected_source_sha256 "
        "identifies the unchanged input file; patch_sha256 identifies this unified diff, "
        "so those distinct hashes are not expected to be equal.\n"
        f"Binding: {_canonical_json(binding)}\n"
        "FULL VALIDATED UNIFIED DIFF (no bytes omitted):\n"
        f"{patch_text}"
    )
    if len(prompt) > MAX_PRE_APPLY_PROPOSAL_CHARS:
        raise InternalPatchHold("pre_apply_full_patch_prompt_exceeds_limit")
    return prompt


@dataclass(frozen=True)
class InternalPatchRequest:
    goal: str
    target_path: str
    expected_source_sha256: str
    test_commands: tuple[tuple[str, ...], ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            **asdict(self),
            "test_commands": [list(command) for command in self.test_commands],
        }


def build_patch_request(
    *,
    root: Path,
    goal: str,
    target_path: str,
    test_commands: Sequence[Sequence[str]],
) -> InternalPatchRequest:
    target = _normalize_target(target_path)
    source_path = Path(root).resolve() / target
    if not source_path.is_file():
        raise InternalPatchHold("target_file_missing")
    source = source_path.read_bytes()
    if not source or len(source) > MAX_SOURCE_BYTES:
        raise InternalPatchHold("source_size_limit_failed")
    goal_text = str(goal or "").strip()
    try:
        goal_bytes = goal_text.encode("utf-8", errors="strict")
    except UnicodeEncodeError as exc:
        raise InternalPatchHold("goal_size_limit_failed") from exc
    if not goal_bytes or len(goal_bytes) > MAX_GOAL_BYTES:
        raise InternalPatchHold("goal_size_limit_failed")
    commands = tuple(tuple(str(part) for part in command) for command in test_commands)
    if not commands or any(not command or not all(command) for command in commands):
        raise InternalPatchHold("test_commands_required")
    return InternalPatchRequest(
        goal=goal_text,
        target_path=target,
        expected_source_sha256=_sha256_bytes(source),
        test_commands=commands,
    )


def _source_for_authoring(root: Path, request: InternalPatchRequest) -> str:
    source_path = root / request.target_path
    source = source_path.read_bytes()
    if _sha256_bytes(source) != request.expected_source_sha256:
        raise InternalPatchHold("source_changed_since_request")
    try:
        text = source.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise InternalPatchHold("source_must_be_utf8_text") from exc
    if any(pattern.search(text) for pattern in SECRET_SOURCE_PATTERNS):
        raise InternalPatchHold("source_secret_scan_failed_before_model")
    return text


def _trusted_proposal_controller(
    repo_root: Path,
    controller: SafeCodeControl | None,
) -> SafeCodeControl:
    proposal_controller = controller or SafeCodeControl(
        state_path=repo_root / "state" / "aureon_internal_patch_proposals.json"
    )
    if type(proposal_controller) is not SafeCodeControl:
        raise InternalPatchHold("trusted_safe_code_controller_required")
    proposal_state_path = proposal_controller.state_path.resolve()
    proposal_state_root = (repo_root / "state").resolve()
    try:
        proposal_state_root.relative_to(repo_root)
        proposal_state_path.relative_to(proposal_state_root)
    except ValueError as exc:
        raise InternalPatchHold("proposal_state_path_must_remain_under_repo_state") from exc
    if proposal_state_path.suffix.casefold() != ".json":
        raise InternalPatchHold("proposal_state_path_must_be_json")
    return proposal_controller


def run_internal_patch_cycle(
    *,
    root: Path,
    request: InternalPatchRequest,
    workforce: InternalCodingWorkforce,
    controller: SafeCodeControl | None = None,
    proposal_forge: LocalProposalForge | None = None,
    base_commit: str = "",
    adviser_id: str = "",
    reviewer_id: str = "",
    adviser_evidence_sha256: str = "",
) -> dict[str, Any]:
    """Seal one Aureon-authored proposal without mutating the repository."""

    repo_root = Path(root).resolve()
    proposal_controller = _trusted_proposal_controller(repo_root, controller)
    if type(proposal_forge) is not LocalProposalForge:
        raise InternalPatchHold("trusted_local_proposal_forge_required")
    forge_preflight = proposal_forge.preflight()
    if (
        not isinstance(forge_preflight, dict)
        or forge_preflight.get("schema")
        != "aureon.plumber.proposal-forge-preflight.v0"
        or forge_preflight.get("ready") is not True
        or forge_preflight.get("key_material_returned") is not False
        or forge_preflight.get("proposal_admission_authorized") is not False
    ):
        raise InternalPatchHold("hnc_proposal_master_key_unavailable")
    initial_report = workforce.report()
    endpoint_digests = {
        str(item.get("endpoint_authority_digest") or "")
        for item in initial_report.get("passports") or ()
        if isinstance(item, dict)
    }
    if len(endpoint_digests) != 1:
        raise InternalPatchHold("self_coder_local_endpoint_binding_required")
    try:
        workforce.assert_sensitive_local_only(
            endpoint_authority_digest=next(iter(endpoint_digests))
        )
    except Exception as exc:
        raise InternalPatchHold("self_coder_local_confidential_runtime_required") from exc
    if re.fullmatch(r"(?:[0-9a-f]{40}|[0-9a-f]{64})", base_commit) is None:
        raise InternalPatchHold("proposal_base_commit_required")
    if not adviser_id.strip() or not reviewer_id.strip():
        raise InternalPatchHold("proposal_adviser_and_reviewer_ids_required")
    if re.fullmatch(r"[0-9a-f]{64}", adviser_evidence_sha256) is None:
        raise InternalPatchHold("proposal_adviser_evidence_digest_required")
    prior_items = [
        *proposal_controller.pending_proposals,
        *proposal_controller.recent_reviews,
    ]
    if prior_items:
        raise InternalPatchHold(
            "existing_proposal_state_requires_manual_protected_archive"
        )
    target = _normalize_target(request.target_path)
    if target != request.target_path:
        raise InternalPatchHold("request_target_not_canonical")
    source = _source_for_authoring(repo_root, request)
    expected = CANONICAL_AGENT_COMPANY_ROLE_COUNT
    if (
        not initial_report.get("brain_fabric_ready")
        or initial_report.get("agent_brain_count") != expected
        or initial_report.get("process_brain_count") != expected
        or len(initial_report.get("passports") or ()) != expected * 2
    ):
        raise InternalPatchHold("full_agent_company_brain_fabric_required")

    deliberation = workforce.deliberate_coding_goal(request.goal, scope_locked=True)
    deliberation_digest = _evidence_digest(deliberation)
    author_prompt_prefix = (
        "AUTHOR ONE UNIFIED DIFF ONLY. Do not use Markdown commentary outside the diff.\n"
        f"Goal: {request.goal}\n"
        f"Exact target: {target}\n"
        f"Expected source SHA-256: {request.expected_source_sha256}\n"
        f"Full Aureon deliberation SHA-256: {deliberation_digest}\n"
        "Aureon bounded council context: "
    )
    author_prompt_suffix = (
        "\n"
        "Rules: modify only the exact target; preserve unrelated behavior; do not add secrets, network calls, "
        "economic actions, deployment, or authority bypasses; keep the patch minimal and testable.\n"
        f"CURRENT FILE {target}:\n{source}"
    )
    council_context, author_prompt_context = _bounded_council_context(
        deliberation,
        prompt_prefix=author_prompt_prefix,
        prompt_suffix=author_prompt_suffix,
    )
    author_prompt = author_prompt_prefix + council_context + author_prompt_suffix
    model_output, author_receipt = workforce.decide(
        subject_type="agent",
        subject_id="Implementation Worker",
        process_id=workforce.process_id_for_role("Implementation Worker"),
        prompt=author_prompt,
        stage="patch_authoring",
        work_kind="unified_diff_authoring",
        max_tokens=INTERNAL_AUTHOR_MAX_TOKENS,
    )
    author_receipts = [author_receipt]
    correction_attempted = False
    authoring_failure_reason = ""
    git_apply_check: dict[str, Any] = {}
    structural_canonicalization: dict[str, Any] = {"used": False}
    try:
        patch_text = _extract_diff(model_output)
        patch_validation = _validate_authored_diff(patch_text, target_path=target)
        git_apply_check = _git_apply_check(repo_root, patch_text)
        if git_apply_check.get("ok") is not True:
            raise InternalPatchHold("authored_diff_git_apply_check_failed")
    except InternalPatchHold as exc:
        if str(exc) not in REPAIRABLE_AUTHORING_HOLDS:
            raise
        correction_attempted = True
        authoring_failure_reason = str(exc)
        failure_detail = str(
            git_apply_check.get("stderr")
            or git_apply_check.get("stdout")
            or git_apply_check.get("error_type")
            or authoring_failure_reason
        )[:1_000]
        repair_prompt = (
            "CORRECT THE PREVIOUS FORMAT FAILURE. Return exactly one unified diff and nothing else.\n"
            f"Goal: {request.goal}\n"
            f"Exact target: {target}\n"
            f"Expected source SHA-256: {request.expected_source_sha256}\n"
            f"Previous bounded failure: {authoring_failure_reason}. Detail: {failure_detail}\n"
            "The response must contain --- a/<target>, +++ b/<target>, and at least one @@ hunk. "
            "Modify only the exact target; preserve unrelated behavior; do not add secrets, network calls, "
            "economic actions, deployment, or authority bypasses.\n"
            f"CURRENT FILE {target}:\n{source}"
        )
        repair_prompt = repair_prompt.replace(
            "Goal: ",
            (
                f"Exact immutable source line count: {len(source.splitlines())}. "
                "The @@ old count must equal that count and the new count must exactly equal the emitted '+' lines."
                " For a complete replacement, emit only the --- and +++ headers, one @@ hunk, every original "
                "line prefixed with '-', then every replacement line prefixed with '+'; use no diff --git, "
                "index metadata, or context lines."
                + chr(10)
                + "Goal: "
            ),
            1,
        )
        model_output, repair_receipt = workforce.decide(
            subject_type="agent",
            subject_id="Implementation Worker",
            process_id=workforce.process_id_for_role("Implementation Worker"),
            prompt=repair_prompt,
            stage="patch_authoring_correction",
            work_kind="unified_diff_format_correction",
            max_tokens=INTERNAL_AUTHOR_MAX_TOKENS,
        )
        author_receipts.append(repair_receipt)
        patch_text = _extract_diff(model_output)
        patch_validation = _validate_authored_diff(patch_text, target_path=target)
        git_apply_check = _git_apply_check(repo_root, patch_text)
        if git_apply_check.get("ok") is not True:
            patch_text, structural_canonicalization = _canonicalize_full_replacement_diff(
                source=source,
                patch_text=patch_text,
                target_path=target,
            )
            patch_validation = _validate_authored_diff(patch_text, target_path=target)
            git_apply_check = _git_apply_check(repo_root, patch_text)
            if git_apply_check.get("ok") is not True:
                raise InternalPatchHold("canonicalized_diff_git_apply_check_failed") from exc

    council_binding = {
        "goal_digest": _sha256_bytes(request.goal.encode("utf-8")),
        "target_path": target,
        "expected_source_sha256": request.expected_source_sha256,
        "patch_sha256": patch_validation["patch_sha256"],
        "test_commands_digest": _evidence_digest(
            {"test_commands": [list(command) for command in request.test_commands]}
        ),
        "deliberation_digest": deliberation_digest,
        "author_prompt_context_digest": author_prompt_context["context_digest"],
        "git_apply_check_digest": _evidence_digest(git_apply_check),
        "git_apply_check_ok": True,
        "structural_canonicalization_digest": _evidence_digest(structural_canonicalization),
    }
    pre_apply_prompt = _build_pre_apply_council_prompt(
        binding=council_binding,
        patch_text=patch_text,
    )
    pre_apply_council = workforce.deliberate_coding_goal(
        pre_apply_prompt,
        selected_roles=PRE_APPLY_COUNCIL_ROLES,
        require_accept=True,
    )
    pre_apply_council = {
        **pre_apply_council,
        "acceptance_scope": "proposal_review_only",
        "execution_authorized": False,
        "release_authorized": False,
        "production_ready": False,
    }
    pre_apply_council_digest = _evidence_digest(pre_apply_council)
    if not _exact_pre_apply_council_accepted(pre_apply_council):
        raise InternalPatchHold("pre_apply_council_held")

    author_work_receipt_ids = [receipt.receipt_id for receipt in author_receipts]
    workforce_report = workforce.report()
    proposal_status = "internal_patch_transient_hnc_seal_held"
    pending_senior_review = False
    proposal_protection: dict[str, Any]
    public_request = request.to_dict()
    public_deliberation = deliberation
    public_pre_apply_council = pre_apply_council

    if proposal_forge is not None:
        provenance = _protected_provenance(
            request=request,
            base_commit=base_commit,
            deliberation_digest=deliberation_digest,
            author_prompt_context=author_prompt_context,
            author_work_receipt_ids=author_work_receipt_ids,
            patch_validation=patch_validation,
            git_apply_check=git_apply_check,
            structural_canonicalization=structural_canonicalization,
            pre_apply_council=pre_apply_council,
            pre_apply_council_digest=pre_apply_council_digest,
            workforce_report=workforce_report,
        )
        try:
            forge_outcome = proposal_forge.forge_proposal(
                source_request=request.goal,
                unified_diff=patch_text,
                model_id=_forge_model_id(_implementation_passport(workforce_report)),
                adviser_id=adviser_id,
                reviewer_id=reviewer_id,
                adviser_evidence_sha256=adviser_evidence_sha256,
                provenance=provenance,
                base_commit=base_commit,
            )
        except ProposalForgeError as exc:
            raise InternalPatchHold(f"hnc_proposal_forge_failed:{exc.code}") from None

        hnc_summary = forge_outcome.public_summary()
        public_request = _metadata_only_request(request)
        public_deliberation = _metadata_only_deliberation(deliberation)
        public_pre_apply_council = _metadata_only_deliberation(pre_apply_council)
        protected_metadata = {
            "request": public_request,
            "deliberation_digest": deliberation_digest,
            "author_prompt_context": author_prompt_context,
            "author_work_receipt_id": author_receipts[-1].receipt_id,
            "author_work_receipt_ids": author_work_receipt_ids,
            "authoring_correction_attempted": correction_attempted,
            "authoring_failure_reason": authoring_failure_reason,
            "patch_validation": patch_validation,
            "git_apply_check": git_apply_check,
            "structural_canonicalization": structural_canonicalization,
            "pre_apply_council_digest": pre_apply_council_digest,
            "pre_apply_council_receipt_ids": _council_receipt_ids(pre_apply_council),
            "provenance_sha256": _evidence_digest(provenance),
            "hnc_proposal": hnc_summary,
            "brain_fabric_ready": True,
            "codex_implementation": False,
            "aureon_receipt_raw_goal_retained": False,
            "aureon_receipt_raw_diff_retained": False,
            "local_model_nonretention_verified": False,
        }
        if isinstance(forge_outcome, OpaqueProposalHandle):
            try:
                discard_summary = proposal_forge.discard_proposal(
                    forge_outcome,
                    reason_code="durable_proposal_vault_unavailable",
                )
            except ProposalForgeError as exc:
                raise InternalPatchHold(
                    f"hnc_transient_proposal_burn_failed:{exc.code}"
                ) from None
            protected_metadata["hnc_discard"] = discard_summary
            proposal_spec = CodeProposal(
                kind="aureon_internal_hnc_unified_diff",
                title=f"HNC-protected Aureon proposal for {target}"[:120],
                summary=(
                    "Aureon's workforce authored this exact-source-bound diff; "
                    "Plumber verified one transient opaque HNC seal. No durable "
                    "review capability exists in this local implementation."
                ),
                target_files=[target],
                patch_text="",
                metadata=protected_metadata,
                source="aureon_internal_coding_workforce",
            )
            prior_auto_approve = proposal_controller.auto_approve
            proposal_controller.auto_approve = False
            try:
                proposal = proposal_controller.propose(proposal_spec)
            finally:
                proposal_controller.auto_approve = prior_auto_approve
            proposal = _record_exact_council_proposal_hold(
                proposal_controller,
                proposal,
            )
            proposal_protection = {
                "mode": "local_in_memory_opaque_hnc_handle_burned",
                "admitted_hnc": True,
                "quarantined_hnc": False,
                "transient_hnc_seal_verified": True,
                "transient_hnc_handle_burned": True,
                "proposal_recoverable": False,
                "durable_proposal_vault_available": False,
                "aureon_receipt_stores_raw_goal": False,
                "aureon_receipt_stores_raw_diff": False,
                "thought_bus_stores_answer_commitment_only": True,
                "client_external_model_egress_attempted": False,
                "local_model_server_downstream_egress_verified": False,
                "local_model_nonretention_verified": False,
                "opaque_handle_persistent": False,
                "local_development_only": True,
                "production_ready": False,
            }
        elif isinstance(forge_outcome, QuarantinedProposal):
            proposal_status = "internal_patch_proposal_quarantined_hnc"
            proposal = {
                "kind": "aureon_internal_hnc_unified_diff",
                "title": f"Quarantined Aureon proposal for {target}"[:120],
                "summary": "Plumber quarantined the candidate; no raw proposal was retained.",
                "target_files": [target],
                "patch_text": "",
                "metadata": protected_metadata,
                "source": "aureon_internal_coding_workforce",
                "status": "hnc_quarantined",
                "proposal_only": True,
                "execution_authorized": False,
                "release_authorized": False,
                "production_ready": False,
            }
            proposal_protection = {
                "mode": "metadata_only_hnc_quarantine",
                "admitted_hnc": False,
                "quarantined_hnc": True,
                "transient_hnc_seal_verified": False,
                "transient_hnc_handle_burned": False,
                "proposal_recoverable": False,
                "durable_proposal_vault_available": False,
                "aureon_receipt_stores_raw_goal": False,
                "aureon_receipt_stores_raw_diff": False,
                "thought_bus_stores_answer_commitment_only": True,
                "client_external_model_egress_attempted": False,
                "local_model_server_downstream_egress_verified": False,
                "local_model_nonretention_verified": False,
                "opaque_handle_persistent": False,
                "local_development_only": True,
                "production_ready": False,
            }
        else:  # pragma: no cover - proposal forge has a closed outcome union
            raise InternalPatchHold("hnc_proposal_forge_outcome_invalid")

        # Drop the two raw model artifacts before assembling any serializable receipt.
        model_output = ""
        patch_text = ""
    apply_evidence = {
        "status": (
            "held_transient_hnc_seal_only"
            if proposal_protection.get("transient_hnc_seal_verified") is True
            else "quarantined_proposal_only"
        ),
        "applied": False,
        "effect_attempted": False,
        "blocked_reason": (
            "durable_proposal_vault_unavailable"
            if proposal_protection.get("transient_hnc_seal_verified") is True
            else "hnc_proposal_quarantined"
        ),
        "test_commands_executed": False,
        "repository_mutation_authorized": False,
        "generated_code_execution_authorized": False,
        "repository_mutation_implemented": False,
        "generated_code_execution_implemented": False,
        "subprocess_test_execution_implemented": False,
        "release_authorized": False,
        "proposal_only": True,
        "local_development_only": True,
        "production_ready": False,
    }
    cycle = {
        "schema_version": SCHEMA_VERSION,
        "status": proposal_status,
        "applied": False,
        "pending_senior_review": pending_senior_review,
        "proposal_recoverable": False,
        "transient_hnc_seal_verified": proposal_protection.get(
            "transient_hnc_seal_verified"
        )
        is True,
        "request": public_request,
        "source_sha256": request.expected_source_sha256,
        "deliberation": public_deliberation,
        "deliberation_digest": deliberation_digest,
        "author_prompt_context": author_prompt_context,
        "proposal": proposal,
        "proposal_protection": proposal_protection,
        "patch_validation": patch_validation,
        "pre_apply_council": public_pre_apply_council,
        "pre_apply_council_digest": pre_apply_council_digest,
        "authoring_correction_attempted": correction_attempted,
        "authoring_failure_reason": authoring_failure_reason,
        "author_work_receipt_ids": author_work_receipt_ids,
        "git_apply_check": git_apply_check,
        "structural_canonicalization": structural_canonicalization,
        "apply_evidence": apply_evidence,
        "workforce_report": workforce_report,
        "codex_role": "senior_review_and_veto_only",
        "codex_implementation": False,
        "repository_mutation_authorized": False,
        "generated_code_execution_authorized": False,
        "repository_mutation_implemented": False,
        "generated_code_execution_implemented": False,
        "subprocess_test_execution_implemented": False,
        "release_authorized": False,
        "proposal_only": True,
        "effect_attempted": False,
        "test_commands_executed": False,
        "production_magic_star_release_available": False,
        "production_ready": False,
        "action_eligible": False,
        "economic_eligible": False,
    }
    cycle["evidence_digest"] = _evidence_digest(cycle)
    return cycle


__all__ = [
    "InternalPatchHold",
    "InternalPatchRequest",
    "SCHEMA_VERSION",
    "build_patch_request",
    "run_internal_patch_cycle",
]

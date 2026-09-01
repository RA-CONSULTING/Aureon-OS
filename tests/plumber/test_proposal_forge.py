from __future__ import annotations

import ast
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Mapping

import pytest

from aureon.harmonic.hnc_quantum_packet_crypto import decode_hnc_quantum_packet
from aureon.plumber.os_protection import LocalOSProtectionBoundary
from aureon.plumber.proposal_forge import (
    AUTHORSHIP_STATEMENT,
    PROPOSAL_PURPOSE,
    LocalProposalForge,
    OpaqueProposalHandle,
    PromotionDisposition,
    ProposalForgeError,
    ProposalReview,
    QuarantinedProposal,
)
from aureon.plumber.star_custody_v02 import LocalDevelopmentStarCustodyV02

NOW = datetime(2031, 4, 5, 6, 7, 8, tzinfo=UTC)
MASTER_KEY = b"proposal-forge-local-test-key-material"
BASE_COMMIT = "a" * 40
REQUEST = "Add a deterministic helper without changing external behavior."
DIFF = """--- a/aureon/example.py
+++ b/aureon/example.py
@@ -1 +1,2 @@
 value = 1
+helper = lambda: value
"""
MODEL_ID = "aureon-local:ollama-test-author"
ADVISER_ID = "openai:codex-adviser"
REVIEWER_ID = "openai:codex-reviewer"
ADVISER_EVIDENCE = hashlib.sha256(b"adviser-transcript").hexdigest()
PROVENANCE = {
    "source": "aureon.autonomous.aureon_internal_self_coder",
    "request_id": "self-code-request-17",
    "target_path": "aureon/example.py",
    "internal_workforce_receipt_sha256": hashlib.sha256(b"workforce").hexdigest(),
}


def _boundary(key: bytes | None = MASTER_KEY) -> LocalOSProtectionBoundary:
    return LocalOSProtectionBoundary(
        boundary_id="proposal-forge-os-boundary",
        master_key_provider=lambda: key,
        max_ingress_bytes=1024 * 1024,
        trusted_now=lambda: NOW,
    )


def _forge(
    boundary: LocalOSProtectionBoundary | None = None,
) -> tuple[LocalProposalForge, LocalOSProtectionBoundary]:
    selected = boundary or _boundary()
    return (
        LocalProposalForge(forge_id="self-coder-proposal-forge", os_boundary=selected),
        selected,
    )


def _forge_one(
    forge: LocalProposalForge,
    **overrides: Any,
) -> OpaqueProposalHandle | QuarantinedProposal:
    values: dict[str, Any] = {
        "source_request": REQUEST,
        "unified_diff": DIFF,
        "model_id": MODEL_ID,
        "adviser_id": ADVISER_ID,
        "reviewer_id": REVIEWER_ID,
        "adviser_evidence_sha256": ADVISER_EVIDENCE,
        "provenance": PROVENANCE,
        "base_commit": BASE_COMMIT,
    }
    values.update(overrides)
    return forge.forge_proposal(**values)


def _review(
    handle: OpaqueProposalHandle,
    *,
    decision: str = "APPROVE",
    **overrides: Any,
) -> ProposalReview:
    values: dict[str, Any] = {
        "proposal_commitment": handle.proposal_commitment,
        "base_commit": handle.descriptor["base_commit"],
        "diff_sha256": handle.descriptor["diff_sha256"],
        "decision": decision,
        "reviewer_organization": "OpenAI",
        "reviewer_id": REVIEWER_ID,
        "reviewer_role": "independent_adviser_reviewer",
        "review_receipt_sha256": hashlib.sha256(b"exact-review").hexdigest(),
        "reviewed_at": NOW,
    }
    values.update(overrides)
    return ProposalReview.build(**values)


def test_forge_returns_only_opaque_handle_and_hnc_binds_exact_provenance() -> None:
    forge, boundary = _forge()

    outcome = _forge_one(forge)

    assert isinstance(outcome, OpaqueProposalHandle)
    public = outcome.public_summary()
    rendered = json.dumps(public, sort_keys=True)
    assert REQUEST not in rendered
    assert DIFF not in rendered
    assert outcome.token not in rendered
    assert "ciphertext_b64" not in rendered
    assert public["promotion_disposition"] == "HOLD"
    descriptor = public["descriptor"]
    assert descriptor["source_request_sha256"] == hashlib.sha256(REQUEST.encode()).hexdigest()
    assert descriptor["diff_sha256"] == hashlib.sha256(DIFF.encode()).hexdigest()
    assert descriptor["base_commit"] == BASE_COMMIT
    assert descriptor["model_id"] == MODEL_ID
    assert descriptor["adviser_organization"] == "OpenAI"
    assert descriptor["adviser_id"] == ADVISER_ID
    assert descriptor["reviewer_id"] == REVIEWER_ID
    assert descriptor["proposal_generator"] == "Aureon"
    assert descriptor["openai_role"] == "adviser_and_reviewer"
    assert descriptor["ownership_claim"] == "none"
    assert descriptor["authorship_statement"] == AUTHORSHIP_STATEMENT

    forge_record = forge._records[outcome.proposal_id]
    os_record = boundary._records[forge_record.os_handle.handle_id]
    decoded = decode_hnc_quantum_packet(
        os_record.packet,
        MASTER_KEY,
        expected_purpose=PROPOSAL_PURPOSE,
    )
    payload = json.loads(decoded.plaintext)
    assert payload["source_request"] == REQUEST
    assert payload["unified_diff"] == DIFF
    assert payload["provenance"] == PROVENANCE
    assert payload["descriptor"] == descriptor
    caller_aad = os_record.packet["operator_aad"]["caller_aad"]
    assert caller_aad["descriptor"] == descriptor
    assert caller_aad["repository_mutation_authorized"] is False
    assert caller_aad["generated_code_execution_authorized"] is False


def test_exact_duplicate_proposal_is_quarantined_by_os_replay_guard() -> None:
    forge, _boundary_instance = _forge()

    first = _forge_one(forge)
    second = _forge_one(forge)

    assert isinstance(first, OpaqueProposalHandle)
    assert isinstance(second, QuarantinedProposal)
    assert "ingress_replay_detected" in second.quarantine.denial_codes
    assert second.descriptor["proposal_commitment"] == first.proposal_commitment
    assert forge.public_summary()["active_opaque_proposal_count"] == 1


def test_discard_burns_forge_and_os_handles_without_decoding() -> None:
    forge, boundary = _forge()
    handle = _forge_one(forge)
    assert isinstance(handle, OpaqueProposalHandle)

    summary = forge.discard_proposal(
        handle,
        reason_code="durable_proposal_vault_unavailable",
    )

    assert summary["disposition"] == "DISCARDED_HNC"
    assert summary["proposal_handle_consumed"] is True
    assert summary["carrier_released"] is False
    assert summary["plaintext_decoded"] is False
    assert summary["os_discard_handle_commitment"] == handle.os_handle_commitment
    assert forge.public_summary()["active_opaque_proposal_count"] == 0
    assert forge.public_summary()["consumed_opaque_proposal_count"] == 1
    assert boundary.public_summary()["active_opaque_handle_count"] == 0
    assert boundary.public_summary()["consumed_opaque_handle_count"] == 1
    with pytest.raises(
        ProposalForgeError,
        match="proposal_handle_unavailable_or_replayed",
    ):
        forge.discard_proposal(handle, reason_code="retry_forbidden")


@pytest.mark.parametrize(
    "bad_diff",
    [
        "print('not a diff')\n",
        "GIT binary patch\n--- a/x\n+++ b/x\n@@ -1 +1 @@\n-a\n+b\n",
        "--- a/x\n+++ b/x\n",
    ],
)
def test_malformed_diff_becomes_metadata_only_hnc_quarantine(bad_diff: str) -> None:
    forge, boundary = _forge()

    outcome = _forge_one(forge, unified_diff=bad_diff)

    assert isinstance(outcome, QuarantinedProposal)
    assert "ingress_content_invalid" in outcome.quarantine.denial_codes
    rendered = json.dumps(outcome.public_summary(), sort_keys=True)
    assert bad_diff not in rendered
    assert outcome.quarantine.hnc_evidence_binding is not None
    evidence_packet = boundary._quarantine_packets[outcome.quarantine.admission_id]
    decoded = decode_hnc_quantum_packet(
        evidence_packet,
        MASTER_KEY,
        expected_purpose="aureon.plumber.os.quarantine-evidence.v0",
    )
    assert bad_diff.encode() not in decoded.plaintext
    assert forge.public_summary()["active_opaque_proposal_count"] == 0


def test_missing_hnc_key_quarantines_and_creates_no_proposal_handle() -> None:
    forge, boundary = _forge(_boundary(None))

    outcome = _forge_one(forge)

    assert isinstance(outcome, QuarantinedProposal)
    assert "master_key_unavailable" in outcome.quarantine.denial_codes
    assert outcome.quarantine.hnc_evidence_binding is None
    assert forge._records == {}
    assert boundary._records == {}
    assert DIFF not in json.dumps(outcome.public_summary(), sort_keys=True)


def test_oversized_diff_is_quarantined_without_a_plaintext_copy() -> None:
    forge, _boundary_instance = _forge()
    oversized = DIFF + "+" + ("x" * (128 * 1024)) + "\n"

    outcome = _forge_one(forge, unified_diff=oversized)

    assert isinstance(outcome, QuarantinedProposal)
    assert "ingress_content_invalid" in outcome.quarantine.denial_codes
    assert outcome.descriptor["diff_size_bytes"] == len(oversized.encode())
    assert oversized not in json.dumps(outcome.public_summary(), sort_keys=True)
    assert forge._records == {}


def test_openai_model_cannot_be_misattributed_as_aureon_generator() -> None:
    forge, boundary = _forge()

    with pytest.raises(ProposalForgeError, match="aureon_generator_model_id_invalid"):
        _forge_one(forge, model_id="openai:gpt-codex")

    assert forge._records == {}
    assert boundary._records == {}


@pytest.mark.parametrize(
    "hostile_diff",
    [
        pytest.param(
            "--- /tmp/x.py\n+++ b/x.py\n@@ -1 +1 @@\n-a\n+b\n",
            id="absolute-path",
        ),
        pytest.param(
            "--- a/C:/x.py\n+++ b/C:/x.py\n@@ -1 +1 @@\n-a\n+b\n",
            id="drive-path",
        ),
        pytest.param(
            "--- a/../x.py\n+++ b/../x.py\n@@ -1 +1 @@\n-a\n+b\n",
            id="parent-traversal",
        ),
        pytest.param(
            "--- a/pkg\\x.py\n+++ b/pkg\\x.py\n@@ -1 +1 @@\n-a\n+b\n",
            id="backslash-path",
        ),
        pytest.param(
            "diff --git a/../x.py b/../x.py\n--- a/x.py\n+++ b/x.py\n@@ -1 +1 @@\n-a\n+b\n",
            id="hostile-diff-git-header",
        ),
        pytest.param(
            "".join(
                f"--- a/f{index}.py\n+++ b/f{index}.py\n@@ -1 +1 @@\n-a\n+b\n"
                for index in range(9)
            ),
            id="too-many-files",
        ),
        pytest.param(
            "--- a/x.py\n+++ b/x.py\n" + ("@@ -1 +1 @@\n-a\n+b\n" * 129),
            id="too-many-hunks",
        ),
        pytest.param(
            "--- a/x.py\n+++ b/x.py\n@@ -1 +1 @@\n-" + ("x" * (16 * 1024 + 1)) + "\n+y\n",
            id="overlong-line",
        ),
    ],
)
def test_hostile_unified_diff_paths_and_shapes_are_quarantined(
    hostile_diff: str,
) -> None:
    forge, _boundary_instance = _forge()

    outcome = _forge_one(forge, unified_diff=hostile_diff)

    assert isinstance(outcome, QuarantinedProposal)
    assert "ingress_content_invalid" in outcome.quarantine.denial_codes
    assert hostile_diff not in json.dumps(outcome.public_summary(), sort_keys=True)
    assert forge._records == {}


class _ExplosiveApplier:
    def __init__(self, events: list[str]) -> None:
        self.events = events

    @property
    def applier_id(self) -> str:
        raise AssertionError("local forge must not inspect applier identity")

    @property
    def measurement_sha256(self) -> str:
        raise AssertionError("local forge must not inspect applier measurement")

    def apply_reviewed_proposal(
        self,
        *,
        protected_proposal: object,
        proposal_summary: Mapping[str, Any],
        review: ProposalReview,
    ) -> Mapping[str, Any]:
        self.events.append("final_applier")
        raise AssertionError("local forge must never invoke a final applier")


def test_non_approved_review_holds_without_consuming_or_calling_applier(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    forge, boundary = _forge()
    handle = _forge_one(forge)
    assert isinstance(handle, OpaqueProposalHandle)
    review = _review(handle, decision="HOLD")
    events: list[str] = []
    applier: Any = _ExplosiveApplier(events)
    custody = object.__new__(LocalDevelopmentStarCustodyV02)
    monkeypatch.setattr(
        LocalDevelopmentStarCustodyV02,
        "protect_carrier",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("must not call custody")),
    )

    result = forge.promote_reviewed(
        handle,
        review=review,
        custody=custody,
        release_context_sha256=hashlib.sha256(b"release").hexdigest(),
        final_applier=applier,
    )

    assert result.disposition is PromotionDisposition.HOLD
    assert result.denial_codes == ("review_not_approved",)
    assert result.proposal_handle_consumed is False
    assert events == []
    assert forge.public_summary()["active_opaque_proposal_count"] == 1
    assert boundary.public_summary()["active_opaque_handle_count"] == 1


def test_mismatched_review_holds_before_the_nonproduction_release_hold() -> None:
    forge, _boundary_instance = _forge()
    handle = _forge_one(forge)
    assert isinstance(handle, OpaqueProposalHandle)
    wrong_review = _review(handle, reviewer_id="openai:different-reviewer")
    custody = object.__new__(LocalDevelopmentStarCustodyV02)

    result = forge.promote_reviewed(
        handle,
        review=wrong_review,
        custody=custody,
        release_context_sha256=hashlib.sha256(b"release").hexdigest(),
        final_applier=object(),  # type: ignore[arg-type]
    )

    assert result.denial_codes == ("review_binding_mismatch",)
    assert result.proposal_handle_consumed is False
    assert forge.public_summary()["active_opaque_proposal_count"] == 1


def test_approved_review_never_calls_nonproduction_custody_or_malicious_applier(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    forge, boundary = _forge()
    handle = _forge_one(forge)
    assert isinstance(handle, OpaqueProposalHandle)
    review = _review(handle)
    events: list[str] = []
    applier: Any = _ExplosiveApplier(events)
    custody = object.__new__(LocalDevelopmentStarCustodyV02)
    monkeypatch.setattr(
        LocalDevelopmentStarCustodyV02,
        "protect_carrier",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("local forge must not call nonproduction custody")
        ),
    )

    first = forge.promote_reviewed(
        handle,
        review=review,
        custody=custody,
        release_context_sha256=hashlib.sha256(b"release").hexdigest(),
        final_applier=applier,
    )
    second = forge.promote_reviewed(
        handle,
        review=review,
        custody=custody,
        release_context_sha256=hashlib.sha256(b"release").hexdigest(),
        final_applier=applier,
    )

    assert list(PromotionDisposition) == [PromotionDisposition.HOLD]
    assert events == []
    assert first.disposition is PromotionDisposition.HOLD
    assert second.disposition is PromotionDisposition.HOLD
    assert first.denial_codes == ("production_magic_star_release_unavailable",)
    assert second.denial_codes == ("production_magic_star_release_unavailable",)
    assert first.proposal_handle_consumed is False
    assert first.production_magic_star_release_available is False
    assert first.final_applier_invoked is False
    rendered = json.dumps(first.public_summary(), sort_keys=True)
    assert DIFF not in rendered
    assert REQUEST not in rendered
    assert forge.public_summary()["active_opaque_proposal_count"] == 1
    assert forge.public_summary()["consumed_opaque_proposal_count"] == 0
    assert boundary.public_summary()["active_opaque_handle_count"] == 1


def test_forge_module_has_no_repo_mutation_or_code_execution_primitive() -> None:
    module_path = Path(__file__).parents[2] / "aureon" / "plumber" / "proposal_forge.py"
    tree = ast.parse(module_path.read_text(encoding="utf-8"))
    imported_roots = {
        alias.name.split(".", 1)[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    called_names = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    called_attributes = {
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    }

    assert imported_roots.isdisjoint({"os", "pathlib", "subprocess", "importlib", "runpy"})
    assert called_names.isdisjoint({"compile", "eval", "exec", "open", "__import__"})
    assert called_attributes.isdisjoint(
        {
            "chmod",
            "mkdir",
            "open",
            "Popen",
            "remove",
            "rename",
            "replace",
            "run",
            "unlink",
            "write_bytes",
            "write_text",
        }
    )


@pytest.mark.parametrize(("key", "ready"), [(MASTER_KEY, True), (None, False)])
def test_forge_preflight_is_non_authorizing_and_key_free(
    key: bytes | None,
    ready: bool,
) -> None:
    forge, _boundary_instance = _forge(_boundary(key))

    preflight = forge.preflight()

    assert preflight["schema"] == "aureon.plumber.proposal-forge-preflight.v0"
    assert preflight["ready"] is ready
    assert preflight["key_material_returned"] is False
    assert preflight["proposal_admission_authorized"] is False
    assert preflight["action_eligible"] is False
    assert preflight["economic_eligible"] is False
    assert MASTER_KEY.hex() not in json.dumps(preflight, sort_keys=True)

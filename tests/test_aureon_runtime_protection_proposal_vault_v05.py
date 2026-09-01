from __future__ import annotations

import ast
import builtins
import hashlib
import importlib
import inspect
import json
import secrets
import shutil
import sqlite3
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from types import MethodType
from typing import Any

import pytest

import aureon.autonomous.aureon_internal_self_coder as self_coder_module
import aureon.autonomous.aureon_intrusion_protection_bridge as bridge_module
import aureon.autonomous.aureon_runtime_protection_proposal_vault_v05 as vault_module
from aureon.autonomous.aureon_internal_work_ledger import DurableInternalWorkLedger
from aureon.autonomous.aureon_intrusion_protection_bridge import (
    INTRUSION_PROTECTION_PROPOSAL_SCHEMA,
    build_runtime_intrusion_protection_proposal_v04,
)
from aureon.autonomous.aureon_runtime_protection_proposal_vault_v05 import (
    RUNTIME_PROTECTION_CODE_CANDIDATE_SCHEMA,
    RUNTIME_PROTECTION_PROPOSAL_VAULT_SCHEMA,
    ProtectionProposalVaultReceiptV05,
    ReviewableProtectionProposalV05,
    RuntimeProtectionProposalVaultError,
    SQLiteRuntimeProtectionProposalVaultV05,
)
from aureon.plumber.crypto import domain_hash
from aureon.plumber.production_release_broker_v03 import ProductionReleaseBrokerV03
from aureon.plumber.proposal_forge import LocalProposalForge
from aureon.plumber.runtime_intrusion_ledger_v04 import SQLiteRuntimeIntrusionLedgerV04
from aureon.plumber.star_custody_v02 import LocalDevelopmentStarCustodyV02
from tests.test_aureon_intrusion_protection_bridge import (
    PLAINTEXT_CANARY,
    _ledger_with_violation,
    _quarantined_event,
    _runtime_metadata,
)

VAULT_KEY = b"aureon-runtime-protection-proposal-vault-test-key"
WRONG_KEY = b"aureon-runtime-protection-proposal-vault-wrong-key"


def _vault(
    path: Path,
    ledger: SQLiteRuntimeIntrusionLedgerV04,
    *,
    key: bytes = VAULT_KEY,
    max_proposals: int = 8,
) -> SQLiteRuntimeProtectionProposalVaultV05:
    return SQLiteRuntimeProtectionProposalVaultV05(
        path.resolve(),
        vault_id="aureon-runtime-protection-test-vault",
        source_ledger=ledger,
        proposal_key_provider=lambda: key,
        max_proposals=max_proposals,
    )


def _drop_mutate_restore(
    path: Path,
    *,
    trigger_name: str,
    statement: str,
    parameters: tuple[Any, ...] = (),
) -> None:
    connection = sqlite3.connect(str(path), isolation_level=None)
    try:
        trigger_row = connection.execute(
            "SELECT sql FROM sqlite_schema WHERE type='trigger' AND name=?",
            (trigger_name,),
        ).fetchone()
        assert trigger_row is not None and isinstance(trigger_row[0], str)
        trigger_sql = trigger_row[0]
        connection.execute("BEGIN IMMEDIATE")
        connection.execute(f'DROP TRIGGER "{trigger_name}"')
        connection.execute(statement, parameters)
        connection.execute(trigger_sql)
        connection.execute("COMMIT")
    finally:
        if connection.in_transaction:
            connection.execute("ROLLBACK")
        connection.close()


def _assert_hold_only(summary: dict[str, Any]) -> None:
    assert summary["disposition"] == "HOLD"
    assert summary["review_required"] is True
    assert summary["commitment_only"] is True
    assert summary["proposal_owner"] == "Aureon"
    assert summary["code_generation_invoked"] is True
    for name in (
        "legal_title_attested",
        "key_provider_restart_continuity_attested",
        "independent_key_custody_attested",
        "external_model_invoked",
        "self_coder_invoked",
        "proposal_forge_invoked",
        "apply_authorized",
        "import_authorized",
        "execute_authorized",
        "release_authorized",
        "repository_mutation_authorized",
        "generated_code_execution_authorized",
        "release_broker_invoked",
        "magic_star_invoked",
        "external_action_authorized",
        "action_eligible",
        "economic_eligible",
        "external_head_anchor_attested",
        "production_ready",
    ):
        assert summary[name] is False


def _candidate_source_from_diff(candidate: dict[str, Any]) -> str:
    unified_diff = candidate["unified_diff"]
    assert isinstance(unified_diff, str) and unified_diff.endswith("\n")
    lines = unified_diff.splitlines()
    hunk_index = next(
        index for index, line in enumerate(lines) if line.startswith("@@ -0,0 +1,")
    )
    source_lines = lines[hunk_index + 1 :]
    assert source_lines and all(line.startswith("+") for line in source_lines)
    return "\n".join(line[1:] for line in source_lines) + "\n"


def test_seal_restart_review_and_replay_are_exact_and_hold_only(
    tmp_path: Path,
) -> None:
    ledger, source_receipt, outcome, resource_commitment = _ledger_with_violation(
        tmp_path / "source.sqlite3"
    )
    vault_path = tmp_path / "vault.sqlite3"
    vault: SQLiteRuntimeProtectionProposalVaultV05 | None = None
    reopened: SQLiteRuntimeProtectionProposalVaultV05 | None = None
    try:
        vault = _vault(vault_path, ledger)
        before = vault.preflight()
        assert before["schema"] == RUNTIME_PROTECTION_PROPOSAL_VAULT_SCHEMA
        assert before["entry_count"] == 0
        assert before["ready"] is True
        receipt = vault.seal_from_intrusion(
            source_sequence=int(source_receipt["sequence"]),
            source_entry_commitment=str(source_receipt["entry_commitment"]),
        )
        receipt_summary = receipt.public_summary()
        _assert_hold_only(receipt_summary)
        assert receipt_summary["standalone_receipt_authenticated"] is False
        assert receipt_summary["live_vault_verification_required"] is True
        assert receipt_summary["durability_readback"] is False
        assert receipt_summary["encrypted_hnc_packet_persisted"] is False
        verified_receipt = vault.verify_receipt(receipt)
        _assert_hold_only(verified_receipt)
        assert verified_receipt["live_vault_verification_performed"] is True
        assert verified_receipt["durability_readback"] is True
        assert verified_receipt["keyed_entry_authenticated"] is True
        assert verified_receipt["encrypted_hnc_packet_persisted"] is True
        assert verified_receipt["encrypted_hnc_packet_authenticated"] is True
        assert verified_receipt["technical_provenance_recorded"] is True

        expected = build_runtime_intrusion_protection_proposal_v04(
            ledger=ledger,
            sequence=int(source_receipt["sequence"]),
            entry_commitment=str(source_receipt["entry_commitment"]),
        ).public_summary()
        review = vault.read_for_review(
            vault_sequence=receipt.sequence,
            vault_entry_commitment=receipt.entry_commitment,
            proposal_commitment=receipt.proposal_commitment,
            candidate_commitment=receipt.candidate_commitment,
        )
        proposal_material = review.proposal_summary()
        assert proposal_material["standalone_review_authenticated"] is False
        assert proposal_material["live_vault_readback_required"] is True
        assert proposal_material["proposal"] == expected
        review_summary = review.public_summary()
        assert review_summary["commitment_only"] is False
        assert review_summary["proposal_commitment_only"] is True
        assert review_summary["public_summary_commitment_only"] is True
        assert review_summary["candidate_review_material_available"] is True
        assert review_summary["candidate_plaintext_in_public_summary"] is False
        assert review_summary["repository_mutation_authorized"] is False
        assert review_summary["generated_code_execution_authorized"] is False
        candidate_material = review.protection_code_candidate_for_review()
        assert candidate_material["standalone_review_authenticated"] is False
        assert candidate_material["live_vault_readback_required"] is True
        candidate = candidate_material["protection_code_candidate"]
        assert isinstance(candidate, dict)
        assert candidate["schema"] == RUNTIME_PROTECTION_CODE_CANDIDATE_SCHEMA
        assert candidate["candidate_owner"] == "Aureon"
        assert candidate["candidate_commitment"] == receipt.candidate_commitment
        assert candidate["candidate_source_sha256"] == receipt.candidate_source_sha256
        assert candidate["unified_diff_sha256"] == receipt.candidate_unified_diff_sha256
        assert candidate["source_event_name"] == "os.remove"
        assert candidate["source_reason_code"] == "runtime_effect_not_magic_star_released"
        assert candidate["disposition"] == "HOLD"
        assert candidate["deterministic_template_rendered"] is True
        assert candidate["technical_provenance_recorded"] is True
        assert candidate["openai_assistance_disclosed"] is True
        assert candidate["code_generation_invoked"] is True
        assert candidate["legal_title_attested"] is False
        assert candidate["semantic_correctness_attested"] is False
        assert candidate["integration_tested"] is False
        for name in (
            "external_model_invoked",
            "self_coder_invoked",
            "proposal_forge_invoked",
            "apply_authorized",
            "import_authorized",
            "execute_authorized",
            "release_authorized",
            "patch_applied",
            "repository_mutation_authorized",
            "external_action_authorized",
            "action_eligible",
            "economic_eligible",
            "production_ready",
        ):
            assert candidate[name] is False
        candidate_source = _candidate_source_from_diff(candidate)
        assert hashlib.sha256(candidate_source.encode()).hexdigest() == candidate[
            "candidate_source_sha256"
        ]
        assert len(candidate_source.encode()) == candidate["candidate_source_size_bytes"]
        assert len(str(candidate["unified_diff"]).encode()) == candidate[
            "unified_diff_size_bytes"
        ]
        assert "ALLOW" not in candidate_source
        parsed_source = ast.parse(candidate_source)
        assert not any(isinstance(node, (ast.Import, ast.ImportFrom)) for node in ast.walk(parsed_source))
        assert {
            node.func.id
            for node in ast.walk(parsed_source)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        } <= {"type"}
        assert not (Path.cwd() / str(candidate["target_path"])).exists()
        assert PLAINTEXT_CANARY not in str(receipt_summary)
        assert outcome.admission_id not in str(receipt_summary)
        assert resource_commitment not in str(receipt_summary)

        vault.close()
        vault = None
        reopened = _vault(vault_path, ledger)
        after_restart = reopened.preflight()
        assert after_restart["entry_count"] == 1
        assert after_restart["encrypted_hnc_packets_authenticated"] is True
        replay = reopened.seal_from_intrusion(
            source_sequence=int(source_receipt["sequence"]),
            source_entry_commitment=str(source_receipt["entry_commitment"]),
        )
        assert replay == receipt
        restarted_review = reopened.read_for_review(
            vault_sequence=receipt.sequence,
            vault_entry_commitment=receipt.entry_commitment,
            proposal_commitment=receipt.proposal_commitment,
            candidate_commitment=receipt.candidate_commitment,
        )
        assert restarted_review.protection_code_candidate_for_review() == candidate_material
        assert reopened.preflight()["entry_count"] == 1
    finally:
        if reopened is not None:
            reopened.close()
        if vault is not None:
            vault.close()
        ledger.close()


def test_plaintext_and_source_identifiers_are_absent_from_vault_files(
    tmp_path: Path,
) -> None:
    ledger, source_receipt, outcome, resource_commitment = _ledger_with_violation(
        tmp_path / "source.sqlite3"
    )
    vault_path = tmp_path / "vault.sqlite3"
    vault = _vault(vault_path, ledger)
    try:
        receipt = vault.seal_from_intrusion(
            source_sequence=int(source_receipt["sequence"]),
            source_entry_commitment=str(source_receipt["entry_commitment"]),
        )
        candidate_material = vault.read_for_review(
            vault_sequence=receipt.sequence,
            vault_entry_commitment=receipt.entry_commitment,
            proposal_commitment=receipt.proposal_commitment,
            candidate_commitment=receipt.candidate_commitment,
        ).protection_code_candidate_for_review()
        candidate = candidate_material["protection_code_candidate"]
        assert isinstance(candidate, dict)
        candidate_markers = (
            str(candidate["target_path"]).encode(),
            b"def review_runtime_protection_candidate",
            b"EXPECTED_REASON_CODE",
        )
        public_bytes = str(receipt.public_summary()).encode("utf-8")
        assert PLAINTEXT_CANARY.encode() not in public_bytes
        assert outcome.admission_id.encode() not in public_bytes
        assert resource_commitment.encode() not in public_bytes
        assert all(marker not in public_bytes for marker in candidate_markers)
        for candidate in vault_path.parent.glob(f"{vault_path.name}*"):
            raw = candidate.read_bytes()
            assert PLAINTEXT_CANARY.encode() not in raw
            assert outcome.admission_id.encode() not in raw
            assert resource_commitment.encode() not in raw
            assert all(marker not in raw for marker in candidate_markers)
    finally:
        vault.close()
        ledger.close()


def test_wrong_or_missing_key_fails_before_readiness(tmp_path: Path) -> None:
    ledger, source_receipt, _outcome, _resource = _ledger_with_violation(
        tmp_path / "source.sqlite3"
    )
    vault_path = tmp_path / "vault.sqlite3"
    vault = _vault(vault_path, ledger)
    try:
        vault.seal_from_intrusion(
            source_sequence=int(source_receipt["sequence"]),
            source_entry_commitment=str(source_receipt["entry_commitment"]),
        )
    finally:
        vault.close()
    try:
        with pytest.raises(
            RuntimeProtectionProposalVaultError,
            match="runtime_protection_vault_metadata_authentication_invalid",
        ):
            _vault(vault_path, ledger, key=WRONG_KEY)
        with pytest.raises(
            RuntimeProtectionProposalVaultError,
            match="runtime_protection_vault_key_unavailable",
        ):
            SQLiteRuntimeProtectionProposalVaultV05(
                (tmp_path / "missing-key.sqlite3").resolve(),
                vault_id="aureon-runtime-protection-test-vault",
                source_ledger=ledger,
                proposal_key_provider=lambda: None,
            )
    finally:
        ledger.close()


def test_sqlite_immutability_triggers_reject_row_and_metadata_changes(
    tmp_path: Path,
) -> None:
    ledger, source_receipt, _outcome, _resource = _ledger_with_violation(
        tmp_path / "source.sqlite3"
    )
    vault_path = tmp_path / "vault.sqlite3"
    vault = _vault(vault_path, ledger)
    try:
        vault.seal_from_intrusion(
            source_sequence=int(source_receipt["sequence"]),
            source_entry_commitment=str(source_receipt["entry_commitment"]),
        )
    finally:
        vault.close()
    connection = sqlite3.connect(str(vault_path), isolation_level=None)
    try:
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "UPDATE runtime_protection_vault_entries_v05 "
                "SET proposal_payload_size_bytes=proposal_payload_size_bytes+1 WHERE sequence=1"
            )
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "DELETE FROM runtime_protection_vault_entries_v05 WHERE sequence=1"
            )
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "UPDATE runtime_protection_vault_metadata_v05 SET vault_id='attacker'"
            )
    finally:
        connection.close()
        ledger.close()


@pytest.mark.parametrize(
    ("trigger_name", "statement", "expected_code"),
    (
        (
            "runtime_protection_vault_entries_v05_no_update",
            "UPDATE runtime_protection_vault_entries_v05 "
            "SET proposal_payload_size_bytes=proposal_payload_size_bytes+1 WHERE sequence=1",
            "runtime_protection_vault_entry_authentication_invalid",
        ),
        (
            "runtime_protection_vault_entries_v05_no_update",
            "UPDATE runtime_protection_vault_entries_v05 "
            "SET proposal_packet_json=zeroblob(length(proposal_packet_json)) WHERE sequence=1",
            "runtime_protection_vault_entry_authentication_invalid",
        ),
        (
            "runtime_protection_vault_metadata_v05_no_update",
            "UPDATE runtime_protection_vault_metadata_v05 SET vault_id='attacker'",
            "runtime_protection_vault_metadata_authentication_invalid",
        ),
    ),
)
def test_authenticated_restart_rejects_row_ciphertext_and_metadata_tamper(
    tmp_path: Path,
    trigger_name: str,
    statement: str,
    expected_code: str,
) -> None:
    ledger, source_receipt, _outcome, _resource = _ledger_with_violation(
        tmp_path / "source.sqlite3"
    )
    vault_path = tmp_path / "vault.sqlite3"
    vault = _vault(vault_path, ledger)
    try:
        vault.seal_from_intrusion(
            source_sequence=int(source_receipt["sequence"]),
            source_entry_commitment=str(source_receipt["entry_commitment"]),
        )
    finally:
        vault.close()
    try:
        _drop_mutate_restore(
            vault_path,
            trigger_name=trigger_name,
            statement=statement,
        )
        with pytest.raises(RuntimeProtectionProposalVaultError, match=expected_code):
            _vault(vault_path, ledger)
    finally:
        ledger.close()


def test_schema_extension_is_rejected_on_restart(tmp_path: Path) -> None:
    ledger, _source_receipt, _outcome, _resource = _ledger_with_violation(
        tmp_path / "source.sqlite3"
    )
    vault_path = tmp_path / "vault.sqlite3"
    vault = _vault(vault_path, ledger)
    vault.close()
    connection = sqlite3.connect(str(vault_path), isolation_level=None)
    try:
        connection.execute(
            "CREATE INDEX attacker_extension ON runtime_protection_vault_entries_v05(recorded_at)"
        )
    finally:
        connection.close()
    try:
        with pytest.raises(
            RuntimeProtectionProposalVaultError,
            match="runtime_protection_vault_schema_invalid",
        ):
            _vault(vault_path, ledger)
    finally:
        ledger.close()


def test_analyze_internal_schema_extension_is_rejected_on_restart(
    tmp_path: Path,
) -> None:
    ledger, _source_receipt, _outcome, _resource = _ledger_with_violation(
        tmp_path / "source.sqlite3"
    )
    vault_path = tmp_path / "vault.sqlite3"
    vault = _vault(vault_path, ledger)
    vault.close()
    connection = sqlite3.connect(str(vault_path), isolation_level=None)
    try:
        connection.execute("ANALYZE")
        assert connection.execute(
            "SELECT COUNT(*) FROM sqlite_schema WHERE name='sqlite_stat1'"
        ).fetchone() == (1,)
    finally:
        connection.close()
    try:
        with pytest.raises(
            RuntimeProtectionProposalVaultError,
            match="runtime_protection_vault_schema_invalid",
        ):
            _vault(vault_path, ledger)
    finally:
        ledger.close()


def test_concurrent_exact_replay_materializes_one_entry(tmp_path: Path) -> None:
    ledger, source_receipt, _outcome, _resource = _ledger_with_violation(
        tmp_path / "source.sqlite3"
    )
    vault = _vault(tmp_path / "vault.sqlite3", ledger)
    try:
        def seal() -> dict[str, Any]:
            return vault.seal_from_intrusion(
                source_sequence=int(source_receipt["sequence"]),
                source_entry_commitment=str(source_receipt["entry_commitment"]),
            ).public_summary()

        with ThreadPoolExecutor(max_workers=8) as pool:
            receipts = list(pool.map(lambda _index: seal(), range(16)))
        assert all(item == receipts[0] for item in receipts)
        assert vault.preflight()["entry_count"] == 1
    finally:
        vault.close()
        ledger.close()


def test_final_capacity_is_terminal_but_existing_proposal_remains_reviewable(
    tmp_path: Path,
) -> None:
    ledger, source_receipt, _outcome, _resource = _ledger_with_violation(
        tmp_path / "source.sqlite3"
    )
    vault = _vault(tmp_path / "vault.sqlite3", ledger, max_proposals=1)
    try:
        receipt = vault.seal_from_intrusion(
            source_sequence=int(source_receipt["sequence"]),
            source_entry_commitment=str(source_receipt["entry_commitment"]),
        )
        assert receipt.terminal_after_append is True
        status = vault.preflight()
        assert status["ready"] is False
        assert status["remaining_proposal_capacity"] == 0
        review = vault.read_for_review(
            vault_sequence=receipt.sequence,
            vault_entry_commitment=receipt.entry_commitment,
            proposal_commitment=receipt.proposal_commitment,
            candidate_commitment=receipt.candidate_commitment,
        )
        assert review.proposal_commitment == receipt.proposal_commitment
        replay = vault.seal_from_intrusion(
            source_sequence=int(source_receipt["sequence"]),
            source_entry_commitment=str(source_receipt["entry_commitment"]),
        )
        assert replay == receipt
        later_outcome, later_packet, _later_resource = _quarantined_event(
            ledger_instance_commitment=str(
                ledger.preflight()["ledger_instance_commitment"]
            ),
            event_name="os.rmdir",
        )
        later_receipt = ledger.append_violation(
            intrusion_id=later_outcome.admission_id,
            runtime_metadata=_runtime_metadata(later_outcome),
            quarantine_summary=later_outcome.public_summary(),
            hnc_packet=later_packet,
        )
        with pytest.raises(
            RuntimeProtectionProposalVaultError,
            match="runtime_protection_vault_capacity_exhausted",
        ):
            vault.seal_from_intrusion(
                source_sequence=int(later_receipt["sequence"]),
                source_entry_commitment=str(later_receipt["entry_commitment"]),
            )
        assert vault.read_for_review(
            vault_sequence=receipt.sequence,
            vault_entry_commitment=receipt.entry_commitment,
            proposal_commitment=receipt.proposal_commitment,
            candidate_commitment=receipt.candidate_commitment,
        ).proposal_commitment == receipt.proposal_commitment
    finally:
        vault.close()
        ledger.close()


def test_vault_rejects_nonexact_source_ledger_type(tmp_path: Path) -> None:
    class LedgerSubclass(SQLiteRuntimeIntrusionLedgerV04):
        pass

    counterfeit = object.__new__(LedgerSubclass)
    with pytest.raises(
        RuntimeProtectionProposalVaultError,
        match="exact_runtime_intrusion_ledger_required",
    ):
        SQLiteRuntimeProtectionProposalVaultV05(
            (tmp_path / "vault.sqlite3").resolve(),
            vault_id="aureon-runtime-protection-test-vault",
            source_ledger=counterfeit,
            proposal_key_provider=lambda: VAULT_KEY,
        )


def test_source_preflight_monkeypatch_cannot_forge_vault_identity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ledger, _source_receipt, _outcome, _resource = _ledger_with_violation(
        tmp_path / "source.sqlite3"
    )
    real = ledger.preflight()

    def forged_preflight(_self: SQLiteRuntimeIntrusionLedgerV04) -> dict[str, Any]:
        return {
            **real,
            "ledger_id": "FORGED",
            "ledger_instance_commitment": "f" * 64,
        }

    monkeypatch.setattr(SQLiteRuntimeIntrusionLedgerV04, "preflight", forged_preflight)
    try:
        with pytest.raises(
            RuntimeProtectionProposalVaultError,
            match="runtime_protection_vault_source_ledger_code_identity_invalid",
        ):
            _vault(tmp_path / "vault.sqlite3", ledger)
    finally:
        ledger.close()


@pytest.mark.parametrize(
    "method_name",
    (
        "preflight",
        "authenticated_violation_projection",
        "authenticated_violation_projections",
        "_validated_entries_in_atomic_snapshot",
        "_validate_pragmas",
        "_validate_schema",
        "_validated_entries",
        "_validate_row",
        "_required_ledger_instance_commitment",
    ),
)
def test_source_authentication_chain_instance_shadow_fails_before_append(
    tmp_path: Path,
    method_name: str,
) -> None:
    ledger, source_receipt, _outcome, _resource = _ledger_with_violation(
        tmp_path / "source.sqlite3"
    )
    vault_path = tmp_path / "vault.sqlite3"
    vault = _vault(vault_path, ledger)
    called = False

    def forged_method(_self: Any, *_args: Any, **_kwargs: Any) -> Any:
        nonlocal called
        called = True
        return []

    setattr(ledger, method_name, MethodType(forged_method, ledger))
    try:
        with pytest.raises(
            RuntimeProtectionProposalVaultError,
            match="runtime_protection_vault_source_ledger_code_identity_invalid",
        ):
            vault.seal_from_intrusion(
                source_sequence=int(source_receipt["sequence"]),
                source_entry_commitment=str(source_receipt["entry_commitment"]),
            )
        assert called is False
        connection = sqlite3.connect(str(vault_path))
        try:
            assert connection.execute(
                "SELECT COUNT(*) FROM runtime_protection_vault_entries_v05"
            ).fetchone() == (0,)
        finally:
            connection.close()
    finally:
        vault.close()
        ledger.close()


def test_bridge_and_vault_source_identity_manifests_cannot_drift() -> None:
    bridge_manifest = bridge_module._EXACT_SOURCE_LEDGER_METHODS
    vault_manifest = vault_module._EXACT_SOURCE_LEDGER_METHODS
    assert tuple(name for name, _method, _code in bridge_manifest) == tuple(
        name for name, _method, _code in vault_manifest
    )
    assert len(bridge_manifest) == 9
    for bridge_item, vault_item in zip(
        bridge_manifest,
        vault_manifest,
        strict=True,
    ):
        assert bridge_item[0] == vault_item[0]
        assert bridge_item[1] is vault_item[1]
        assert bridge_item[2] is vault_item[2]


@pytest.mark.parametrize(
    "method_name",
    (
        "preflight",
        "authenticated_violation_projection",
        "authenticated_violation_projections",
        "_validated_entries_in_atomic_snapshot",
        "_validate_pragmas",
        "_validate_schema",
        "_validated_entries",
        "_validate_row",
        "_required_ledger_instance_commitment",
    ),
)
@pytest.mark.parametrize("attack_kind", ("class_binding", "same_function_code"))
def test_source_authentication_chain_class_or_code_replacement_fails_before_append(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    method_name: str,
    attack_kind: str,
) -> None:
    ledger, source_receipt, _outcome, _resource = _ledger_with_violation(
        tmp_path / "source.sqlite3"
    )
    vault_path = tmp_path / "vault.sqlite3"
    vault = _vault(vault_path, ledger)
    exact_method = vars(SQLiteRuntimeIntrusionLedgerV04)[method_name]

    def forged_method(*_args: Any, **_kwargs: Any) -> Any:
        raise AssertionError("forged source method must not execute")

    try:
        with monkeypatch.context() as patch:
            if attack_kind == "class_binding":
                patch.setattr(
                    SQLiteRuntimeIntrusionLedgerV04,
                    method_name,
                    forged_method,
                )
            else:
                patch.setattr(exact_method, "__code__", forged_method.__code__)
            with pytest.raises(
                RuntimeProtectionProposalVaultError,
                match="runtime_protection_vault_source_ledger_code_identity_invalid",
            ):
                vault.seal_from_intrusion(
                    source_sequence=int(source_receipt["sequence"]),
                    source_entry_commitment=str(source_receipt["entry_commitment"]),
                )
        connection = sqlite3.connect(str(vault_path))
        try:
            assert connection.execute(
                "SELECT COUNT(*) FROM runtime_protection_vault_entries_v05"
            ).fetchone() == (0,)
        finally:
            connection.close()
    finally:
        vault.close()
        ledger.close()


def test_source_class_getattribute_interception_fails_before_append(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ledger, source_receipt, _outcome, _resource = _ledger_with_violation(
        tmp_path / "source.sqlite3"
    )
    vault_path = tmp_path / "vault.sqlite3"
    vault = _vault(vault_path, ledger)
    called = False

    def hostile_getattribute(self: Any, name: str) -> Any:
        nonlocal called
        called = True
        return object.__getattribute__(self, name)

    try:
        with monkeypatch.context() as patch:
            patch.setattr(
                SQLiteRuntimeIntrusionLedgerV04,
                "__getattribute__",
                hostile_getattribute,
                raising=False,
            )
            with pytest.raises(
                RuntimeProtectionProposalVaultError,
                match="runtime_protection_vault_source_ledger_code_identity_invalid",
            ):
                vault.seal_from_intrusion(
                    source_sequence=int(source_receipt["sequence"]),
                    source_entry_commitment=str(source_receipt["entry_commitment"]),
                )
        assert called is False
        connection = sqlite3.connect(str(vault_path))
        try:
            assert connection.execute(
                "SELECT COUNT(*) FROM runtime_protection_vault_entries_v05"
            ).fetchone() == (0,)
        finally:
            connection.close()
    finally:
        vault.close()
        ledger.close()


def test_vault_proposal_resolver_instance_shadow_fails_before_append(
    tmp_path: Path,
) -> None:
    ledger, source_receipt, _outcome, _resource = _ledger_with_violation(
        tmp_path / "source.sqlite3"
    )
    vault_path = tmp_path / "vault.sqlite3"
    vault = _vault(vault_path, ledger)
    called = False

    def forged_resolver(_self: Any, *_args: Any, **_kwargs: Any) -> Any:
        nonlocal called
        called = True
        raise AssertionError("forged resolver must not execute")

    vault._proposal_from_source = MethodType(  # type: ignore[method-assign]
        forged_resolver,
        vault,
    )
    try:
        with pytest.raises(
            RuntimeProtectionProposalVaultError,
            match="runtime_protection_vault_proposal_resolver_identity_invalid",
        ):
            vault.seal_from_intrusion(
                source_sequence=int(source_receipt["sequence"]),
                source_entry_commitment=str(source_receipt["entry_commitment"]),
            )
        assert called is False
        connection = sqlite3.connect(str(vault_path))
        try:
            assert connection.execute(
                "SELECT COUNT(*) FROM runtime_protection_vault_entries_v05"
            ).fetchone() == (0,)
        finally:
            connection.close()
    finally:
        vault.close()
        ledger.close()


def test_public_receipt_and_review_types_require_vault_factory() -> None:
    with pytest.raises(
        RuntimeProtectionProposalVaultError,
        match="runtime_protection_vault_receipt_factory_required",
    ):
        ProtectionProposalVaultReceiptV05()
    with pytest.raises(
        RuntimeProtectionProposalVaultError,
        match="runtime_protection_vault_review_factory_required",
    ):
        ReviewableProtectionProposalV05()


def test_conventional_private_factories_require_internal_tokens_and_raw_material_is_private(
    tmp_path: Path,
) -> None:
    ledger, source_receipt, _outcome, _resource = _ledger_with_violation(
        tmp_path / "source.sqlite3"
    )
    vault = _vault(tmp_path / "vault.sqlite3", ledger)
    try:
        real_proposal = build_runtime_intrusion_protection_proposal_v04(
            ledger=ledger,
            sequence=int(source_receipt["sequence"]),
            entry_commitment=str(source_receipt["entry_commitment"]),
        ).public_summary()
        real_receipt = vault.seal_from_intrusion(
            source_sequence=int(source_receipt["sequence"]),
            source_entry_commitment=str(source_receipt["entry_commitment"]),
        )
        real_review = vault.read_for_review(
            vault_sequence=real_receipt.sequence,
            vault_entry_commitment=real_receipt.entry_commitment,
            proposal_commitment=real_receipt.proposal_commitment,
            candidate_commitment=real_receipt.candidate_commitment,
        )
        real_candidate_material = real_review.protection_code_candidate_for_review()
        real_candidate = real_candidate_material["protection_code_candidate"]
        assert isinstance(real_candidate, dict)
        assert not hasattr(real_review, "proposal")
        proposal_material = real_review.proposal_summary()
        assert proposal_material["standalone_review_authenticated"] is False
        assert proposal_material["live_vault_readback_required"] is True
        fake_hash = "f" * 64
        with pytest.raises(
            RuntimeProtectionProposalVaultError,
            match="runtime_protection_vault_receipt_origin_invalid",
        ):
            ProtectionProposalVaultReceiptV05._issue(
                vault_id="fake-vault",
                vault_instance_commitment=fake_hash,
                sequence=1,
                proposal_id=f"remediation-{fake_hash[:32]}",
                proposal_commitment=fake_hash,
                candidate_commitment=fake_hash,
                candidate_source_sha256=fake_hash,
                candidate_unified_diff_sha256=fake_hash,
                source_ledger_id="fake-ledger",
                source_ledger_instance_commitment=fake_hash,
                source_ledger_sequence=2,
                source_entry_commitment=fake_hash,
                source_projection_commitment=fake_hash,
                proposal_packet_sha256=fake_hash,
                proposal_payload_sha256=fake_hash,
                recorded_at=datetime.now(UTC).isoformat(),
                entry_commitment=fake_hash,
                terminal_after_append=False,
            )
        with pytest.raises(
            RuntimeProtectionProposalVaultError,
            match="runtime_protection_vault_review_origin_invalid",
        ):
            ReviewableProtectionProposalV05._issue(
                vault_id="fake-vault",
                vault_instance_commitment=fake_hash,
                vault_sequence=1,
                vault_entry_commitment=fake_hash,
                proposal=real_proposal,
                protection_code_candidate=real_candidate,
            )
    finally:
        vault.close()
        ledger.close()


def test_oversized_tampered_packet_is_rejected_by_bounded_sql_census(
    tmp_path: Path,
) -> None:
    ledger, source_receipt, _outcome, _resource = _ledger_with_violation(
        tmp_path / "source.sqlite3"
    )
    vault_path = tmp_path / "vault.sqlite3"
    vault = _vault(vault_path, ledger)
    try:
        vault.seal_from_intrusion(
            source_sequence=int(source_receipt["sequence"]),
            source_entry_commitment=str(source_receipt["entry_commitment"]),
        )
    finally:
        vault.close()
    try:
        _drop_mutate_restore(
            vault_path,
            trigger_name="runtime_protection_vault_entries_v05_no_update",
            statement=(
                "UPDATE runtime_protection_vault_entries_v05 "
                "SET proposal_packet_json=zeroblob(1048577) WHERE sequence=1"
            ),
        )
        with pytest.raises(
            RuntimeProtectionProposalVaultError,
            match="runtime_protection_vault_bounded_census_invalid",
        ):
            _vault(vault_path, ledger)
    finally:
        ledger.close()


def test_pipeline_invokes_no_self_coder_forge_magic_star_or_release(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ledger, source_receipt, _outcome, _resource = _ledger_with_violation(
        tmp_path / "source.sqlite3"
    )

    def forbidden(*_args: Any, **_kwargs: Any) -> Any:
        raise AssertionError("downstream authority invoked")

    monkeypatch.setattr(self_coder_module, "run_autonomous_self_coding", forbidden)
    monkeypatch.setattr(DurableInternalWorkLedger, "append", forbidden)
    monkeypatch.setattr(LocalProposalForge, "forge_proposal", forbidden)
    monkeypatch.setattr(ProductionReleaseBrokerV03, "execute_release", forbidden)
    monkeypatch.setattr(LocalDevelopmentStarCustodyV02, "protect_carrier", forbidden)
    monkeypatch.setattr(builtins, "compile", forbidden)
    monkeypatch.setattr(builtins, "eval", forbidden)
    monkeypatch.setattr(builtins, "exec", forbidden)
    monkeypatch.setattr(importlib, "import_module", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    monkeypatch.setattr(subprocess, "run", forbidden)
    modules_before = frozenset(sys.modules)
    vault = _vault(tmp_path / "vault.sqlite3", ledger)
    try:
        receipt = vault.seal_from_intrusion(
            source_sequence=int(source_receipt["sequence"]),
            source_entry_commitment=str(source_receipt["entry_commitment"]),
        )
        review = vault.read_for_review(
            vault_sequence=receipt.sequence,
            vault_entry_commitment=receipt.entry_commitment,
            proposal_commitment=receipt.proposal_commitment,
            candidate_commitment=receipt.candidate_commitment,
        )
        assert review.public_summary()["release_authorized"] is False
        candidate_material = review.protection_code_candidate_for_review()
        candidate = candidate_material["protection_code_candidate"]
        assert isinstance(candidate, dict)
        target = Path.cwd() / str(candidate["target_path"])
        assert not target.exists()
        assert frozenset(sys.modules) == modules_before
    finally:
        vault.close()
        ledger.close()


def test_schema_stays_one_atomic_vault_and_api_accepts_no_candidate_input(
    tmp_path: Path,
) -> None:
    signature = inspect.signature(SQLiteRuntimeProtectionProposalVaultV05.seal_from_intrusion)
    assert tuple(signature.parameters) == (
        "self",
        "source_sequence",
        "source_entry_commitment",
    )
    ledger, source_receipt, _outcome, _resource = _ledger_with_violation(
        tmp_path / "source.sqlite3"
    )
    vault_path = tmp_path / "vault.sqlite3"
    vault = _vault(vault_path, ledger)
    try:
        vault.seal_from_intrusion(
            source_sequence=int(source_receipt["sequence"]),
            source_entry_commitment=str(source_receipt["entry_commitment"]),
        )
    finally:
        vault.close()
    connection = sqlite3.connect(str(vault_path))
    try:
        tables = {
            str(row[0])
            for row in connection.execute(
                "SELECT name FROM sqlite_schema WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            )
        }
        assert tables == {
            "runtime_protection_vault_metadata_v05",
            "runtime_protection_vault_entries_v05",
        }
        assert not any("candidate" in name for name in tables)
        columns = tuple(
            str(row[1])
            for row in connection.execute(
                "PRAGMA table_info(runtime_protection_vault_entries_v05)"
            )
        )
        assert columns.count("candidate_commitment") == 1
        indexes = connection.execute(
            "PRAGMA index_list(runtime_protection_vault_entries_v05)"
        ).fetchall()
        assert len(indexes) == 5
        assert all(row[2] == 1 and row[3] == "u" and row[4] == 0 for row in indexes)
        assert connection.execute(
            "SELECT COUNT(*) FROM runtime_protection_vault_entries_v05"
        ).fetchone() == (1,)
    finally:
        connection.close()
        ledger.close()


def test_key_continuity_is_unattested_and_random_restart_key_fails_closed(
    tmp_path: Path,
) -> None:
    ledger, source_receipt, _outcome, _resource = _ledger_with_violation(
        tmp_path / "source.sqlite3"
    )
    vault_path = (tmp_path / "vault.sqlite3").resolve()

    def fresh_key() -> bytes:
        return secrets.token_bytes(32)

    vault = SQLiteRuntimeProtectionProposalVaultV05(
        vault_path,
        vault_id="aureon-runtime-protection-random-key-test-vault",
        source_ledger=ledger,
        proposal_key_provider=fresh_key,
        max_proposals=8,
    )
    try:
        status = vault.preflight()
        assert status["current_open_key_matches_authenticated_metadata"] is True
        assert status["key_provider_restart_continuity_attested"] is False
        assert status["independent_key_custody_attested"] is False
        assert status["future_restart_decryption_attested"] is False
        vault.seal_from_intrusion(
            source_sequence=int(source_receipt["sequence"]),
            source_entry_commitment=str(source_receipt["entry_commitment"]),
        )
    finally:
        vault.close()
    try:
        with pytest.raises(
            RuntimeProtectionProposalVaultError,
            match="runtime_protection_vault_metadata_authentication_invalid",
        ):
            SQLiteRuntimeProtectionProposalVaultV05(
                vault_path,
                vault_id="aureon-runtime-protection-random-key-test-vault",
                source_ledger=ledger,
                proposal_key_provider=fresh_key,
                max_proposals=8,
            )
    finally:
        ledger.close()


def test_undersized_packet_and_unbounded_proposal_capacity_are_rejected(
    tmp_path: Path,
) -> None:
    ledger, _source_receipt, _outcome, _resource = _ledger_with_violation(
        tmp_path / "source.sqlite3"
    )
    try:
        with pytest.raises(
            RuntimeProtectionProposalVaultError,
            match="runtime_protection_vault_packet_bytes_invalid",
        ):
            SQLiteRuntimeProtectionProposalVaultV05(
                (tmp_path / "small-packet.sqlite3").resolve(),
                vault_id="aureon-runtime-protection-small-packet-test-vault",
                source_ledger=ledger,
                proposal_key_provider=lambda: VAULT_KEY,
                max_packet_bytes=1024,
            )
        with pytest.raises(
            RuntimeProtectionProposalVaultError,
            match="runtime_protection_vault_capacity_invalid",
        ):
            SQLiteRuntimeProtectionProposalVaultV05(
                (tmp_path / "unbounded.sqlite3").resolve(),
                vault_id="aureon-runtime-protection-unbounded-test-vault",
                source_ledger=ledger,
                proposal_key_provider=lambda: VAULT_KEY,
                max_proposals=65,
            )
        bounded = SQLiteRuntimeProtectionProposalVaultV05(
            (tmp_path / "bounded.sqlite3").resolve(),
            vault_id="aureon-runtime-protection-bounded-test-vault",
            source_ledger=ledger,
            proposal_key_provider=lambda: VAULT_KEY,
        )
        try:
            bounded_status = bounded.preflight()
            assert bounded_status["max_proposals"] == 64
            assert bounded_status["source_max_violation_entries"] == 8
            assert bounded_status["source_capacity_bound_enforced"] is True
            assert (
                bounded_status["source_authentication_scaling"]
                == "O(source_entries+vault_entries)"
            )
        finally:
            bounded.close()
    finally:
        ledger.close()


def test_source_capacity_above_measured_lock_bound_is_rejected(
    tmp_path: Path,
) -> None:
    ledger = SQLiteRuntimeIntrusionLedgerV04(
        (tmp_path / "source.sqlite3").resolve(),
        ledger_id="aureon-runtime-protection-oversized-source",
        quarantine_hnc_key_provider=lambda: VAULT_KEY,
        max_violation_entries=65,
    )
    vault_path = tmp_path / "vault.sqlite3"
    try:
        with pytest.raises(
            RuntimeProtectionProposalVaultError,
            match="runtime_protection_vault_source_capacity_invalid",
        ):
            _vault(vault_path, ledger)
        assert not vault_path.exists()
    finally:
        ledger.close()


def test_trigger_literal_whitespace_tamper_is_rejected_by_exact_schema(
    tmp_path: Path,
) -> None:
    ledger, _source_receipt, _outcome, _resource = _ledger_with_violation(
        tmp_path / "source.sqlite3"
    )
    vault_path = tmp_path / "vault.sqlite3"
    vault = _vault(vault_path, ledger)
    vault.close()
    connection = sqlite3.connect(str(vault_path), isolation_level=None)
    try:
        trigger_name = "runtime_protection_vault_entries_v05_chain"
        row = connection.execute(
            "SELECT sql FROM sqlite_schema WHERE type='trigger' AND name=?",
            (trigger_name,),
        ).fetchone()
        assert row is not None and isinstance(row[0], str)
        original = row[0]
        zero_hash = "0" * 64
        tampered = original.replace(zero_hash, "0" * 32 + " " + "0" * 32, 1)
        assert tampered != original
        connection.execute("BEGIN IMMEDIATE")
        connection.execute(f'DROP TRIGGER "{trigger_name}"')
        connection.execute(tampered)
        connection.execute("COMMIT")
    finally:
        if connection.in_transaction:
            connection.execute("ROLLBACK")
        connection.close()
    try:
        with pytest.raises(
            RuntimeProtectionProposalVaultError,
            match="runtime_protection_vault_schema_invalid",
        ):
            _vault(vault_path, ledger)
    finally:
        ledger.close()


@pytest.mark.parametrize(
    "attack_kind",
    (
        "inner_global_replacement",
        "inner_code_replacement",
        "wrapper_global_replacement",
        "wrapper_code_replacement",
        "recipe_id_replacement",
        "recipe_hash_replacement",
    ),
)
def test_candidate_renderer_identity_replacement_fails_before_append(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    attack_kind: str,
) -> None:
    ledger, source_receipt, _outcome, _resource = _ledger_with_violation(
        tmp_path / "source.sqlite3"
    )
    vault_path = tmp_path / "vault.sqlite3"
    vault = _vault(vault_path, ledger)

    def forged_renderer(_proposal: Any) -> dict[str, Any]:
        return {}

    if attack_kind == "inner_global_replacement":
        monkeypatch.setattr(
            vault_module,
            "_render_protection_code_candidate",
            forged_renderer,
        )
    elif attack_kind == "inner_code_replacement":
        monkeypatch.setattr(
            vault_module._render_protection_code_candidate,
            "__code__",
            forged_renderer.__code__,
        )
    elif attack_kind == "wrapper_global_replacement":
        monkeypatch.setattr(
            vault_module,
            "_render_exact_protection_code_candidate",
            forged_renderer,
        )
    elif attack_kind == "wrapper_code_replacement":
        monkeypatch.setattr(
            vault_module._render_exact_protection_code_candidate,
            "__code__",
            forged_renderer.__code__,
        )
    elif attack_kind == "recipe_id_replacement":
        monkeypatch.setattr(
            vault_module,
            "_CANDIDATE_RECIPE_ID",
            "forged.runtime-protection.recipe.v99",
        )
    else:
        monkeypatch.setattr(vault_module, "_CANDIDATE_RECIPE_SHA256", "f" * 64)
    try:
        with pytest.raises(
            RuntimeProtectionProposalVaultError,
            match="runtime_protection_vault_candidate_renderer_identity_invalid",
        ):
            vault.seal_from_intrusion(
                source_sequence=int(source_receipt["sequence"]),
                source_entry_commitment=str(source_receipt["entry_commitment"]),
            )
        connection = sqlite3.connect(str(vault_path))
        try:
            assert connection.execute(
                "SELECT COUNT(*) FROM runtime_protection_vault_entries_v05"
            ).fetchone() == (0,)
        finally:
            connection.close()
    finally:
        vault.close()
        ledger.close()


def test_candidate_renderer_escapes_hostile_text_and_rejects_oversize(
    tmp_path: Path,
) -> None:
    ledger, source_receipt, _outcome, _resource = _ledger_with_violation(
        tmp_path / "source.sqlite3"
    )
    try:
        base = build_runtime_intrusion_protection_proposal_v04(
            ledger=ledger,
            sequence=int(source_receipt["sequence"]),
            entry_commitment=str(source_receipt["entry_commitment"]),
        ).public_summary()

        def with_event(event_name: str) -> dict[str, Any]:
            proposal = json.loads(json.dumps(base))
            proposal["intrusion_evidence"]["event_name"] = event_name
            core = {
                key: value
                for key, value in proposal.items()
                if key not in {"proposal_id", "proposal_commitment"}
            }
            commitment = domain_hash(INTRUSION_PROTECTION_PROPOSAL_SCHEMA, core)
            proposal["proposal_id"] = f"remediation-{commitment[:32]}"
            proposal["proposal_commitment"] = commitment
            return proposal

        attacks = (
            '"quoted"',
            "back\\slash",
            "line\r\nbreak",
            "nul\x00byte",
            "unicode-\u2603",
            "__import__('os').system('attacker')",
            "x\ndiff --git a/attacker b/attacker\n@@ -0,0 +1 @@\n+exec('x')",
        )
        for attack in attacks:
            candidate = vault_module._render_protection_code_candidate(with_event(attack))
            source = _candidate_source_from_diff(candidate)
            parsed = ast.parse(source)
            assignments = {
                target.id: node.value.value
                for node in parsed.body
                if isinstance(node, ast.Assign)
                and len(node.targets) == 1
                and isinstance((target := node.targets[0]), ast.Name)
                and isinstance(node.value, ast.Constant)
            }
            assert assignments["EXPECTED_EVENT_NAME"] == attack
            assert str(candidate["unified_diff"]).startswith("diff --git a/aureon/")
            assert str(candidate["unified_diff"]).count("\ndiff --git ") == 0
            target_path = str(candidate["target_path"])
            assert target_path.startswith("aureon/autonomous/generated/")
            assert ".." not in target_path and "\\" not in target_path
        with pytest.raises(
            RuntimeProtectionProposalVaultError,
            match="runtime_protection_vault_candidate_capacity_exceeded",
        ):
            vault_module._render_protection_code_candidate(with_event("x" * 20_000))
    finally:
        ledger.close()


def test_candidate_commitment_tamper_and_wrong_review_selector_fail_closed(
    tmp_path: Path,
) -> None:
    ledger, source_receipt, _outcome, _resource = _ledger_with_violation(
        tmp_path / "source.sqlite3"
    )
    vault_path = tmp_path / "vault.sqlite3"
    vault = _vault(vault_path, ledger)
    try:
        receipt = vault.seal_from_intrusion(
            source_sequence=int(source_receipt["sequence"]),
            source_entry_commitment=str(source_receipt["entry_commitment"]),
        )
        with pytest.raises(
            RuntimeProtectionProposalVaultError,
            match="runtime_protection_vault_review_selector_mismatch",
        ):
            vault.read_for_review(
                vault_sequence=receipt.sequence,
                vault_entry_commitment=receipt.entry_commitment,
                proposal_commitment=receipt.proposal_commitment,
                candidate_commitment="f" * 64,
            )
    finally:
        vault.close()
    try:
        _drop_mutate_restore(
            vault_path,
            trigger_name="runtime_protection_vault_entries_v05_no_update",
            statement=(
                "UPDATE runtime_protection_vault_entries_v05 "
                "SET candidate_commitment=? WHERE sequence=1"
            ),
            parameters=("f" * 64,),
        )
        with pytest.raises(
            RuntimeProtectionProposalVaultError,
            match="runtime_protection_vault_entry_authentication_invalid",
        ):
            _vault(vault_path, ledger)
    finally:
        ledger.close()


def test_hnc_seal_failure_leaves_no_partial_candidate_row(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ledger, source_receipt, _outcome, _resource = _ledger_with_violation(
        tmp_path / "source.sqlite3"
    )
    vault_path = tmp_path / "vault.sqlite3"
    vault = _vault(vault_path, ledger)

    def fail_seal(*_args: Any, **_kwargs: Any) -> Any:
        raise RuntimeError("injected")

    monkeypatch.setattr(vault_module, "build_hnc_quantum_packet", fail_seal)
    try:
        with pytest.raises(
            RuntimeProtectionProposalVaultError,
            match="runtime_protection_vault_hnc_seal_failed",
        ):
            vault.seal_from_intrusion(
                source_sequence=int(source_receipt["sequence"]),
                source_entry_commitment=str(source_receipt["entry_commitment"]),
            )
    finally:
        vault.close()
    connection = sqlite3.connect(str(vault_path))
    try:
        assert connection.execute(
            "SELECT COUNT(*) FROM runtime_protection_vault_entries_v05"
        ).fetchone() == (0,)
    finally:
        connection.close()
        ledger.close()


def test_vault_source_has_no_candidate_apply_import_execute_or_release_route() -> None:
    source_path = Path(str(vault_module.__file__)).resolve()
    source = source_path.read_text(encoding="utf-8")
    parsed = ast.parse(source)
    imported_roots = {
        alias.name.split(".", 1)[0]
        for node in parsed.body
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }
    assert {"subprocess", "importlib", "socket", "requests", "httpx"}.isdisjoint(
        imported_roots
    )
    called_names = {
        node.func.id
        for node in ast.walk(parsed)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    assert {"compile", "eval", "exec", "__import__"}.isdisjoint(called_names)
    assert "LocalProposalForge" not in source
    assert "ProductionReleaseBroker" not in source
    assert "LocalDevelopmentStarCustody" not in source


def test_byte_copy_clone_is_detectable_only_as_unanchored_hold_limitation(
    tmp_path: Path,
) -> None:
    ledger, source_receipt, _outcome, _resource = _ledger_with_violation(
        tmp_path / "source.sqlite3"
    )
    vault_path = tmp_path / "vault.sqlite3"
    clone_path = tmp_path / "vault-clone.sqlite3"
    vault = _vault(vault_path, ledger)
    try:
        vault.seal_from_intrusion(
            source_sequence=int(source_receipt["sequence"]),
            source_entry_commitment=str(source_receipt["entry_commitment"]),
        )
    finally:
        vault.close()
    shutil.copy2(vault_path, clone_path)
    original = _vault(vault_path, ledger)
    clone = _vault(clone_path, ledger)
    try:
        original_status = original.preflight()
        clone_status = clone.preflight()
        assert original_status["vault_instance_commitment"] == clone_status[
            "vault_instance_commitment"
        ]
        assert original_status["head_entry_commitment"] == clone_status[
            "head_entry_commitment"
        ]
        assert original_status["external_head_anchor_attested"] is False
        assert clone_status["external_head_anchor_attested"] is False
        assert original_status["production_ready"] is False
        assert clone_status["production_ready"] is False
    finally:
        clone.close()
        original.close()
        ledger.close()

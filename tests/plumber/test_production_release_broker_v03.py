"""Adversarial and restart checks for the v0.3 broker metadata contract."""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from dataclasses import replace
from pathlib import Path

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from aureon.plumber.crypto import canonical_json_bytes, ed25519_public_key_hex
from aureon.plumber.production_release_broker_v03 import (
    AuthorityBindingV03,
    DispatchClaimSignerV03,
    DispatchClaimV03,
    ExecutorOutcome,
    LedgerClaimDisposition,
    ProductionReleaseBrokerError,
    ProductionReleaseBrokerV03,
    ProductionReleaseVerifierV03,
    ReceiptDisposition,
    ReleaseCommandV03,
    ReleaseReceiptV03,
    SQLiteTerminalLedgerV03,
    decode_dispatch_claim_v03,
    decode_executor_evidence_v03,
    decode_release_command_v03,
    decode_review_authorization_v03,
    decode_terminal_receipt_v03,
    sign_dispatch_claim_v03,
    sign_executor_evidence_v03,
    sign_review_authorization_v03,
    sign_terminal_receipt_v03,
    terminal_receipt_id_v03,
)


def oid(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


class FakeDispatchSigner:
    def __init__(
        self,
        signer_id: str,
        key_id: str,
        key: Ed25519PrivateKey,
        *,
        fail: bool = False,
    ) -> None:
        self.signer_id = signer_id
        self.key_id = key_id
        self.key = key
        self.fail = fail
        self.calls = 0
        self.unsigned_wires: list[bytes] = []

    def sign_dispatch(
        self,
        unsigned_dispatch_wire: bytes,
        *,
        deadline_at_ms: int,
    ) -> bytes:
        self.calls += 1
        self.unsigned_wires.append(unsigned_dispatch_wire)
        if self.fail:
            raise RuntimeError("dispatch signer unavailable")
        values = json.loads(unsigned_dispatch_wire)
        assert deadline_at_ms == values["claim_expires_at_ms"]
        dispatch = sign_dispatch_claim_v03(self.key, **values)
        return canonical_json_bytes(dispatch.wire_dict())


class Clock:
    def __init__(self, value: int = 2_000) -> None:
        self.value = value

    def __call__(self) -> int:
        return self.value


@pytest.fixture()
def contract():  # noqa: ANN201 - compact multi-object security fixture
    review_key = Ed25519PrivateKey.generate()
    dispatch_key = Ed25519PrivateKey.generate()
    executor_key = Ed25519PrivateKey.generate()
    receipt_key = Ed25519PrivateKey.generate()
    review_binding = AuthorityBindingV03(
        role="REVIEW",
        authority_id="review-authority",
        key_id="review-key-v1",
        public_key_hex=ed25519_public_key_hex(review_key),
    )
    executor_binding = AuthorityBindingV03(
        role="EXECUTOR",
        authority_id="executor-authority",
        key_id="executor-key-v1",
        public_key_hex=ed25519_public_key_hex(executor_key),
    )
    dispatch_binding = AuthorityBindingV03(
        role="DISPATCH",
        authority_id="dispatch-authority",
        key_id="dispatch-key-v1",
        public_key_hex=ed25519_public_key_hex(dispatch_key),
    )
    receipt_binding = AuthorityBindingV03(
        role="RECEIPT",
        authority_id="receipt-authority",
        key_id="receipt-key-v1",
        public_key_hex=ed25519_public_key_hex(receipt_key),
    )
    clock = Clock()
    verifier = ProductionReleaseVerifierV03(
        review_authority=review_binding,
        dispatch_authority=dispatch_binding,
        executor_authority=executor_binding,
        receipt_authority=receipt_binding,
        trusted_now_ms=clock,
    )
    command = ReleaseCommandV03(
        command_id=oid("command-1"),
        packet_commitment="1" * 64,
        admission_commitment="2" * 64,
        effect_id=oid("effect-1"),
        capability_id=oid("operator-route-1"),
        capability_measurement_sha256="3" * 64,
        runtime_measurement_sha256="4" * 64,
        authorization_context_sha256="5" * 64,
        request_nonce=oid("nonce-1"),
        issued_at_ms=1_000,
        expires_at_ms=10_000,
    )
    review = sign_review_authorization_v03(
        review_key,
        review_id=oid("review-1"),
        command_commitment=command.commitment,
        decision="ALLOW",
        issued_at_ms=1_100,
        expires_at_ms=9_000,
        authority_id=review_binding.authority_id,
        key_id=review_binding.key_id,
    )
    dispatch = sign_dispatch_claim_v03(
        dispatch_key,
        command_commitment=command.commitment,
        review_commitment=review.commitment,
        effect_id=command.effect_id,
        request_nonce=command.request_nonce,
        dispatch_nonce=oid("dispatch-1"),
        claimed_at_ms=2_000,
        claim_expires_at_ms=2_500,
        authority_id=dispatch_binding.authority_id,
        key_id=dispatch_binding.key_id,
    )
    evidence = sign_executor_evidence_v03(
        executor_key,
        evidence_id=oid("executor-evidence-1"),
        command_commitment=command.commitment,
        review_commitment=review.commitment,
        dispatch_commitment=dispatch.commitment,
        effect_id=command.effect_id,
        capability_id=command.capability_id,
        runtime_measurement_sha256=command.runtime_measurement_sha256,
        request_nonce=command.request_nonce,
        outcome=ExecutorOutcome.CONSUMED,
        result_sha256="6" * 64,
        provider_readback_sha256="7" * 64,
        reason_code="effect_consumed_with_provider_readback",
        terminal_at_ms=2_100,
        authority_id=executor_binding.authority_id,
        key_id=executor_binding.key_id,
    )
    receipt = sign_terminal_receipt_v03(
        receipt_key,
        denied=False,
        receipt_id=terminal_receipt_id_v03(evidence.commitment),
        command_commitment=command.commitment,
        review_commitment=review.commitment,
        executor_evidence_commitment=evidence.commitment,
        effect_id=command.effect_id,
        request_nonce=command.request_nonce,
        disposition=ReceiptDisposition.RELEASED,
        reason_code="effect_consumed_with_provider_readback",
        terminal_at_ms=evidence.terminal_at_ms,
        authority_id=receipt_binding.authority_id,
        key_id=receipt_binding.key_id,
    )
    return {
        "keys": (review_key, executor_key, receipt_key),
        "bindings": (review_binding, executor_binding, receipt_binding),
        "dispatch_key": dispatch_key,
        "dispatch_binding": dispatch_binding,
        "dispatch_signer": FakeDispatchSigner(
            dispatch_binding.authority_id,
            dispatch_binding.key_id,
            dispatch_key,
        ),
        "clock": clock,
        "verifier": verifier,
        "command": command,
        "review": review,
        "dispatch": dispatch,
        "evidence": evidence,
        "receipt": receipt,
    }


def terminal_chain_for_dispatch(contract, dispatch: DispatchClaimV03):  # noqa: ANN001, ANN201
    _review_key, executor_key, receipt_key = contract["keys"]
    _review_binding, executor_binding, receipt_binding = contract["bindings"]
    evidence = sign_executor_evidence_v03(
        executor_key,
        evidence_id=oid(f"evidence:{dispatch.dispatch_nonce}"),
        command_commitment=contract["command"].commitment,
        review_commitment=contract["review"].commitment,
        dispatch_commitment=dispatch.commitment,
        effect_id=contract["command"].effect_id,
        capability_id=contract["command"].capability_id,
        runtime_measurement_sha256=contract["command"].runtime_measurement_sha256,
        request_nonce=contract["command"].request_nonce,
        outcome=ExecutorOutcome.CONSUMED,
        result_sha256="6" * 64,
        provider_readback_sha256="7" * 64,
        reason_code="effect_consumed_with_provider_readback",
        terminal_at_ms=dispatch.claimed_at_ms + 10,
        authority_id=executor_binding.authority_id,
        key_id=executor_binding.key_id,
    )
    receipt = sign_terminal_receipt_v03(
        receipt_key,
        denied=False,
        receipt_id=terminal_receipt_id_v03(evidence.commitment),
        command_commitment=contract["command"].commitment,
        review_commitment=contract["review"].commitment,
        executor_evidence_commitment=evidence.commitment,
        effect_id=contract["command"].effect_id,
        request_nonce=contract["command"].request_nonce,
        disposition=ReceiptDisposition.RELEASED,
        reason_code="effect_consumed_with_provider_readback",
        terminal_at_ms=evidence.terminal_at_ms,
        authority_id=receipt_binding.authority_id,
        key_id=receipt_binding.key_id,
    )
    return evidence, receipt


def test_exact_signed_release_chain_verifies_and_is_secret_free(contract) -> None:  # noqa: ANN001
    contract["verifier"].verify_terminal(
        contract["command"],
        contract["review"],
        contract["dispatch"],
        contract["receipt"],
        contract["evidence"],
    )
    rendered = json.dumps(
        {
            "command": contract["command"].public_dict(),
            "review": contract["review"].wire_dict(),
            "evidence": contract["evidence"].wire_dict(),
            "receipt": contract["receipt"].wire_dict(),
        },
        sort_keys=True,
    )
    assert "PRIVATE_BROKER_SENTINEL" not in rendered
    assert "private_key" not in rendered.casefold()
    assert "contains_plaintext" not in contract["command"].public_dict()
    with pytest.raises(ProductionReleaseBrokerError, match="command_id_invalid"):
        replace(contract["command"], command_id="PRIVATE_BROKER_SENTINEL")
    assert contract["receipt"].production_ready is False


def test_all_remote_wire_objects_require_bounded_canonical_exact_json(contract) -> None:  # noqa: ANN001
    command = decode_release_command_v03(
        canonical_json_bytes(contract["command"].wire_dict())
    )
    review = decode_review_authorization_v03(
        canonical_json_bytes(contract["review"].wire_dict())
    )
    evidence = decode_executor_evidence_v03(
        canonical_json_bytes(contract["evidence"].wire_dict())
    )
    receipt = decode_terminal_receipt_v03(
        canonical_json_bytes(contract["receipt"].wire_dict())
    )
    assert command == contract["command"]
    assert review == contract["review"]
    assert evidence == contract["evidence"]
    assert receipt == contract["receipt"]

    with pytest.raises(ProductionReleaseBrokerError, match="wire_invalid"):
        decode_release_command_v03(b'{"schema":"x", "schema":"y"}')
    with pytest.raises(ProductionReleaseBrokerError, match="wire_invalid"):
        decode_review_authorization_v03(b"{" + b"x" * (65 * 1024) + b"}")
    extra = {**contract["receipt"].wire_dict(), "caller_claimed_ready": True}
    with pytest.raises(ProductionReleaseBrokerError, match="shape_invalid"):
        decode_terminal_receipt_v03(canonical_json_bytes(extra))


def test_authorities_must_be_distinct(contract) -> None:  # noqa: ANN001
    review, executor, receipt = contract["bindings"]
    reused = replace(receipt, public_key_hex=review.public_key_hex)
    with pytest.raises(ProductionReleaseBrokerError, match="public_keys_not_distinct"):
        ProductionReleaseVerifierV03(
            review_authority=review,
            dispatch_authority=contract["dispatch_binding"],
            executor_authority=executor,
            receipt_authority=reused,
        )


@pytest.mark.parametrize(
    ("target", "field", "value", "error"),
    [
        ("review", "command_commitment", "a" * 64, "review_authorization_join"),
        ("evidence", "request_nonce", oid("nonce-swapped"), "executor_evidence_join"),
        ("receipt", "effect_id", oid("effect-swapped"), "terminal_receipt_join"),
    ],
)
def test_join_tampering_fails_closed(contract, target, field, value, error) -> None:  # noqa: ANN001
    values = {
        "review": contract["review"],
        "evidence": contract["evidence"],
        "receipt": contract["receipt"],
    }
    values[target] = replace(values[target], **{field: value})
    with pytest.raises(ProductionReleaseBrokerError, match=error):
        contract["verifier"].verify_terminal(
            contract["command"],
            values["review"],
            contract["dispatch"],
            values["receipt"],
            values["evidence"],
        )


def test_self_signed_receipt_is_rejected(contract) -> None:  # noqa: ANN001
    review_key, _executor_key, _receipt_key = contract["keys"]
    forged = sign_terminal_receipt_v03(
        review_key,
        denied=False,
        **contract["receipt"].unsigned_dict(),
    )
    with pytest.raises(
        ProductionReleaseBrokerError,
        match="terminal_signature_invalid",
    ):
        contract["verifier"].verify_terminal(
            contract["command"],
            contract["review"],
            contract["dispatch"],
            forged,
            contract["evidence"],
        )


def test_receipt_cannot_predate_its_signed_executor_evidence(contract) -> None:  # noqa: ANN001
    _review_key, _executor_key, receipt_key = contract["keys"]
    values = contract["receipt"].unsigned_dict()
    values["terminal_at_ms"] = contract["evidence"].terminal_at_ms - 1
    early = sign_terminal_receipt_v03(receipt_key, denied=False, **values)
    with pytest.raises(ProductionReleaseBrokerError, match="receipt_time_join_invalid"):
        contract["verifier"].verify_terminal(
            contract["command"],
            contract["review"],
            contract["dispatch"],
            early,
            contract["evidence"],
        )


def test_receipt_identity_and_content_are_canonical_for_executor_evidence(
    contract,
) -> None:  # noqa: ANN001
    _review_key, _executor_key, receipt_key = contract["keys"]
    values = contract["receipt"].unsigned_dict()
    values["receipt_id"] = oid("alternate-authentic-receipt")
    alternate = sign_terminal_receipt_v03(receipt_key, denied=False, **values)
    with pytest.raises(ProductionReleaseBrokerError, match="canonical_join_invalid"):
        contract["verifier"].verify_terminal(
            contract["command"],
            contract["review"],
            contract["dispatch"],
            alternate,
            contract["evidence"],
        )


def test_expired_review_blocks_new_dispatch_but_historical_terminal_stays_verifiable(
    contract,
) -> None:  # noqa: ANN001
    contract["clock"].value = 9_001
    with pytest.raises(ProductionReleaseBrokerError, match="join_or_time_invalid"):
        contract["verifier"].verify_review(contract["command"], contract["review"])
    contract["verifier"].verify_terminal(
        contract["command"],
        contract["review"],
        contract["dispatch"],
        contract["receipt"],
        contract["evidence"],
    )


def test_sqlite_claim_terminal_and_restart_are_exactly_idempotent(
    tmp_path: Path,
    contract,
) -> None:  # noqa: ANN001
    path = (tmp_path / "release.sqlite3").resolve()
    ledger = SQLiteTerminalLedgerV03(
        path,
        dispatch_signer=contract["dispatch_signer"],
        trusted_now_ms=contract["clock"],
    )
    claimed = ledger.claim(
        contract["command"],
        contract["review"],
        verifier=contract["verifier"],
        claim_timeout_ms=2_000,
    )
    assert claimed.disposition is LedgerClaimDisposition.CLAIMED
    assert ledger.claim(
        contract["command"],
        contract["review"],
        verifier=contract["verifier"],
    ).disposition is LedgerClaimDisposition.IN_FLIGHT
    dispatch = DispatchClaimV03.from_wire(claimed.dispatch)
    evidence, receipt = terminal_chain_for_dispatch(contract, dispatch)
    ledger.record_executor_evidence(
        contract["command"],
        contract["review"],
        evidence,
        verifier=contract["verifier"],
    )

    first = ledger.record_terminal(
        contract["command"],
        contract["review"],
        receipt,
        evidence,
        verifier=contract["verifier"],
    )
    restarted = SQLiteTerminalLedgerV03(
        path,
        dispatch_signer=contract["dispatch_signer"],
        trusted_now_ms=contract["clock"],
    )
    replay = restarted.claim(
        contract["command"],
        contract["review"],
        verifier=contract["verifier"],
    )
    assert replay.disposition is LedgerClaimDisposition.TERMINAL_REPLAY
    assert replay.receipt == first
    assert replay.executor_evidence == evidence.wire_dict()
    assert restarted.read_terminal(
        contract["command"],
        contract["review"],
        verifier=contract["verifier"],
    ) == first
    assert restarted.record_terminal(
        contract["command"],
        contract["review"],
        receipt,
        evidence,
        verifier=contract["verifier"],
    ) == first


@pytest.mark.parametrize("reuse", ["effect", "nonce"])
def test_effect_or_nonce_cannot_be_claimed_by_another_command(
    tmp_path: Path,
    contract,
    reuse: str,
) -> None:  # noqa: ANN001
    ledger = SQLiteTerminalLedgerV03(
        (tmp_path / "release.sqlite3").resolve(),
        dispatch_signer=contract["dispatch_signer"],
        trusted_now_ms=contract["clock"],
    )
    ledger.claim(
        contract["command"],
        contract["review"],
        verifier=contract["verifier"],
    )
    changed = replace(
        contract["command"],
        command_id=oid("command-2"),
        packet_commitment="8" * 64,
        admission_commitment="9" * 64,
        effect_id=(
            contract["command"].effect_id if reuse == "effect" else oid("effect-2")
        ),
        request_nonce=(
            contract["command"].request_nonce if reuse == "nonce" else oid("nonce-2")
        ),
    )
    review_key, _executor_key, _receipt_key = contract["keys"]
    review_binding, _executor_binding, _receipt_binding = contract["bindings"]
    changed_review = sign_review_authorization_v03(
        review_key,
        review_id=oid("review-2"),
        command_commitment=changed.commitment,
        decision="ALLOW",
        issued_at_ms=1_100,
        expires_at_ms=9_000,
        authority_id=review_binding.authority_id,
        key_id=review_binding.key_id,
    )
    with pytest.raises(ProductionReleaseBrokerError, match="effect_nonce_or_dispatch_reused"):
        ledger.claim(changed, changed_review, verifier=contract["verifier"])


def test_stale_crash_claim_stays_unresolved_until_signed_executor_evidence(
    tmp_path: Path,
    contract,
) -> None:  # noqa: ANN001
    ledger = SQLiteTerminalLedgerV03(
        (tmp_path / "release.sqlite3").resolve(),
        dispatch_signer=contract["dispatch_signer"],
        trusted_now_ms=contract["clock"],
    )
    claimed = ledger.claim(
        contract["command"],
        contract["review"],
        verifier=contract["verifier"],
        claim_timeout_ms=500,
    )
    contract["clock"].value = 2_501
    assert ledger.claim(
        contract["command"],
        contract["review"],
        verifier=contract["verifier"],
    ).disposition is LedgerClaimDisposition.STALE_UNCERTAIN
    assert ledger.read_terminal(
        contract["command"],
        contract["review"],
        verifier=contract["verifier"],
    ) is None

    dispatch = DispatchClaimV03.from_wire(claimed.dispatch)
    evidence, receipt = terminal_chain_for_dispatch(contract, dispatch)
    ledger.record_executor_evidence(
        contract["command"],
        contract["review"],
        evidence,
        verifier=contract["verifier"],
    )
    stored = ledger.record_terminal(
        contract["command"],
        contract["review"],
        receipt,
        evidence,
        verifier=contract["verifier"],
    )
    assert stored["disposition"] == "RELEASED"
    assert stored["effect_retry_authorized"] is False
    assert SQLiteTerminalLedgerV03(
        (tmp_path / "release.sqlite3").resolve(),
        dispatch_signer=contract["dispatch_signer"],
        trusted_now_ms=contract["clock"],
    ).read_terminal(
        contract["command"],
        contract["review"],
        verifier=contract["verifier"],
    ) == stored


def test_sqlite_ledger_rejects_memory_and_relative_paths(tmp_path: Path) -> None:
    with pytest.raises(ProductionReleaseBrokerError, match="durable_sqlite_path_required"):
        SQLiteTerminalLedgerV03(Path(":memory:"), dispatch_signer=object())  # type: ignore[arg-type]
    with pytest.raises(ProductionReleaseBrokerError, match="durable_sqlite_path_required"):
        SQLiteTerminalLedgerV03(Path("relative.sqlite3"), dispatch_signer=object())  # type: ignore[arg-type]
    assert not (tmp_path / "relative.sqlite3").exists()


def test_release_receipt_type_cannot_claim_denied_disposition(contract) -> None:  # noqa: ANN001
    with pytest.raises(ProductionReleaseBrokerError, match="release_receipt_invalid"):
        ReleaseReceiptV03(
            **{
                **contract["receipt"].unsigned_dict(),
                "disposition": ReceiptDisposition.DENIED,
                "signature_hex": contract["receipt"].signature_hex,
            }
        )


class FakeExecutor:
    def __init__(
        self,
        executor_id: str,
        key: Ed25519PrivateKey,
        verifier: ProductionReleaseVerifierV03,
        *,
        fail: bool = False,
    ) -> None:
        self.executor_id = executor_id
        self.key = key
        self.verifier = verifier
        self.fail = fail
        self.calls = 0

    def execute(
        self,
        command_wire: bytes,
        review_wire: bytes,
        dispatch_wire: bytes,
    ) -> bytes:
        self.calls += 1
        if self.fail:
            raise RuntimeError("secret executor detail must be sanitized")
        command = decode_release_command_v03(command_wire)
        review = decode_review_authorization_v03(review_wire)
        dispatch = decode_dispatch_claim_v03(dispatch_wire)
        self.verifier.verify_dispatch_current(command, review, dispatch)
        evidence = sign_executor_evidence_v03(
            self.key,
            evidence_id=oid(f"executor:{dispatch.dispatch_nonce}"),
            command_commitment=command.commitment,
            review_commitment=review.commitment,
            dispatch_commitment=dispatch.commitment,
            effect_id=command.effect_id,
            capability_id=command.capability_id,
            runtime_measurement_sha256=command.runtime_measurement_sha256,
            request_nonce=command.request_nonce,
            outcome=ExecutorOutcome.CONSUMED,
            result_sha256="6" * 64,
            provider_readback_sha256="7" * 64,
            reason_code="effect_consumed_with_provider_readback",
            terminal_at_ms=dispatch.claimed_at_ms + 10,
            authority_id=self.executor_id,
            key_id="executor-key-v1",
        )
        return canonical_json_bytes(evidence.wire_dict())


class FakeReceiptSigner:
    def __init__(
        self,
        signer_id: str,
        key: Ed25519PrivateKey,
        *,
        fail: bool = False,
        fail_after_store: bool = False,
    ) -> None:
        self.signer_id = signer_id
        self.key = key
        self.fail = fail
        self.fail_after_store = fail_after_store
        self.calls = 0
        self.read_calls = 0
        self.receipts: dict[str, bytes] = {}

    def sign_terminal(  # noqa: ANN201
        self,
        command_wire: bytes,
        review_wire: bytes,
        evidence_wire: bytes,
        *,
        idempotency_key: str,
    ) -> bytes:
        self.calls += 1
        if self.fail:
            raise RuntimeError("secret signer detail must be sanitized")
        command = decode_release_command_v03(command_wire)
        review = decode_review_authorization_v03(review_wire)
        evidence = decode_executor_evidence_v03(evidence_wire)
        assert idempotency_key == evidence.commitment
        receipt = sign_terminal_receipt_v03(
            self.key,
            denied=evidence.outcome is ExecutorOutcome.DENIED,
            receipt_id=terminal_receipt_id_v03(evidence.commitment),
            command_commitment=command.commitment,
            review_commitment=review.commitment,
            executor_evidence_commitment=evidence.commitment,
            effect_id=command.effect_id,
            request_nonce=command.request_nonce,
            disposition=(
                ReceiptDisposition.RELEASED
                if evidence.outcome is ExecutorOutcome.CONSUMED
                else ReceiptDisposition.DENIED
            ),
            reason_code=evidence.reason_code,
            terminal_at_ms=evidence.terminal_at_ms,
            authority_id=self.signer_id,
            key_id="receipt-key-v1",
        )
        wire = canonical_json_bytes(receipt.wire_dict())
        previous = self.receipts.setdefault(idempotency_key, wire)
        assert previous == wire
        if self.fail_after_store:
            raise RuntimeError("response lost after signer committed")
        return wire

    def read_terminal(self, *, idempotency_key: str) -> bytes | None:
        self.read_calls += 1
        return self.receipts.get(idempotency_key)


def test_reference_broker_dispatches_once_and_restart_returns_terminal(
    tmp_path: Path,
    contract,
) -> None:  # noqa: ANN001
    _review_key, executor_key, receipt_key = contract["keys"]
    _review_binding, executor_binding, receipt_binding = contract["bindings"]
    path = (tmp_path / "broker.sqlite3").resolve()
    executor = FakeExecutor(
        executor_binding.authority_id, executor_key, contract["verifier"]
    )
    signer = FakeReceiptSigner(receipt_binding.authority_id, receipt_key)
    broker = ProductionReleaseBrokerV03(
        verifier=contract["verifier"],
        ledger=SQLiteTerminalLedgerV03(
            path,
            dispatch_signer=contract["dispatch_signer"],
            trusted_now_ms=contract["clock"],
        ),
        executor=executor,
        receipt_signer=signer,
        claim_timeout_ms=500,
    )
    terminal = broker.execute_release(contract["command"], contract["review"])
    assert terminal["disposition"] == "RELEASED"
    assert executor.calls == 1
    assert signer.calls == 1

    contract["clock"].value = 10_001
    restarted = ProductionReleaseBrokerV03(
        verifier=contract["verifier"],
        ledger=SQLiteTerminalLedgerV03(
            path,
            dispatch_signer=contract["dispatch_signer"],
            trusted_now_ms=contract["clock"],
        ),
        executor=executor,
        receipt_signer=signer,
        claim_timeout_ms=500,
    )
    assert restarted.execute_release(contract["command"], contract["review"]) == terminal
    assert executor.calls == 1
    assert signer.calls == 1


def test_restart_reauthenticates_stored_terminal_receipt_before_readback(
    tmp_path: Path,
    contract,
) -> None:  # noqa: ANN001
    _review_key, executor_key, receipt_key = contract["keys"]
    _review_binding, executor_binding, receipt_binding = contract["bindings"]
    path = (tmp_path / "broker.sqlite3").resolve()
    executor = FakeExecutor(
        executor_binding.authority_id, executor_key, contract["verifier"]
    )
    signer = FakeReceiptSigner(receipt_binding.authority_id, receipt_key)
    broker = ProductionReleaseBrokerV03(
        verifier=contract["verifier"],
        ledger=SQLiteTerminalLedgerV03(
            path,
            dispatch_signer=contract["dispatch_signer"],
            trusted_now_ms=contract["clock"],
        ),
        executor=executor,
        receipt_signer=signer,
    )
    terminal = broker.execute_release(contract["command"], contract["review"])
    tampered = {**terminal, "terminal_at_ms": terminal["terminal_at_ms"] + 1}
    with sqlite3.connect(path) as connection:
        connection.execute(
            "UPDATE release_terminal_v03 SET receipt_json=? WHERE command_commitment=?",
            (canonical_json_bytes(tampered), contract["command"].commitment),
        )
    with pytest.raises(
        ProductionReleaseBrokerError,
        match="stored_terminal_commitment_mismatch",
    ):
        ProductionReleaseBrokerV03(
            verifier=contract["verifier"],
            ledger=SQLiteTerminalLedgerV03(
                path,
                dispatch_signer=contract["dispatch_signer"],
                trusted_now_ms=contract["clock"],
            ),
            executor=executor,
            receipt_signer=signer,
        ).execute_release(contract["command"], contract["review"])
    assert executor.calls == 1


def test_executor_crash_is_never_retried_or_closed_as_a_false_denial(
    tmp_path: Path,
    contract,
) -> None:  # noqa: ANN001
    _review_key, executor_key, receipt_key = contract["keys"]
    _review_binding, executor_binding, receipt_binding = contract["bindings"]
    path = (tmp_path / "broker.sqlite3").resolve()
    executor = FakeExecutor(
        executor_binding.authority_id,
        executor_key,
        contract["verifier"],
        fail=True,
    )
    signer = FakeReceiptSigner(receipt_binding.authority_id, receipt_key)
    broker = ProductionReleaseBrokerV03(
        verifier=contract["verifier"],
        ledger=SQLiteTerminalLedgerV03(
            path,
            dispatch_signer=contract["dispatch_signer"],
            trusted_now_ms=contract["clock"],
        ),
        executor=executor,
        receipt_signer=signer,
        claim_timeout_ms=500,
    )
    with pytest.raises(
        ProductionReleaseBrokerError,
        match="executor_unavailable_or_uncertain_claim_retained",
    ) as captured:
        broker.execute_release(contract["command"], contract["review"])
    assert "secret executor detail" not in str(captured.value)
    assert executor.calls == 1

    contract["clock"].value = 2_501
    with pytest.raises(
        ProductionReleaseBrokerError,
        match="stale_uncertain_reconciliation_required",
    ):
        ProductionReleaseBrokerV03(
            verifier=contract["verifier"],
            ledger=SQLiteTerminalLedgerV03(
                path,
                dispatch_signer=contract["dispatch_signer"],
                trusted_now_ms=contract["clock"],
            ),
            executor=executor,
            receipt_signer=signer,
            claim_timeout_ms=500,
        ).execute_release(contract["command"], contract["review"])
    assert executor.calls == 1
    assert signer.calls == 0


def test_receipt_signer_failure_resumes_from_durable_evidence_without_redispatch(
    tmp_path: Path,
    contract,
) -> None:  # noqa: ANN001
    _review_key, executor_key, receipt_key = contract["keys"]
    _review_binding, executor_binding, receipt_binding = contract["bindings"]
    path = (tmp_path / "evidence-resume.sqlite3").resolve()
    executor = FakeExecutor(
        executor_binding.authority_id, executor_key, contract["verifier"]
    )
    failing_signer = FakeReceiptSigner(
        receipt_binding.authority_id,
        receipt_key,
        fail=True,
    )
    with pytest.raises(
        ProductionReleaseBrokerError,
        match="terminal_signer_unavailable_evidence_retained",
    ) as captured:
        ProductionReleaseBrokerV03(
            verifier=contract["verifier"],
            ledger=SQLiteTerminalLedgerV03(
                path,
                dispatch_signer=contract["dispatch_signer"],
                trusted_now_ms=contract["clock"],
            ),
            executor=executor,
            receipt_signer=failing_signer,
            claim_timeout_ms=500,
        ).execute_release(contract["command"], contract["review"])
    assert "secret signer detail" not in str(captured.value)
    assert executor.calls == 1
    with sqlite3.connect(path) as connection:
        state, evidence_json, receipt_json = connection.execute(
            "SELECT state, executor_evidence_json, receipt_json "
            "FROM release_terminal_v03"
        ).fetchone()
    assert state == "EVIDENCED"
    assert evidence_json is not None
    assert receipt_json is None

    contract["clock"].value = 2_501
    recovered = ProductionReleaseBrokerV03(
        verifier=contract["verifier"],
        ledger=SQLiteTerminalLedgerV03(
            path,
            dispatch_signer=contract["dispatch_signer"],
            trusted_now_ms=contract["clock"],
        ),
        executor=executor,
        receipt_signer=FakeReceiptSigner(receipt_binding.authority_id, receipt_key),
        claim_timeout_ms=500,
    ).execute_release(contract["command"], contract["review"])
    assert recovered["disposition"] == "RELEASED"
    assert executor.calls == 1


def test_receipt_readback_recovers_response_lost_after_idempotent_commit(
    tmp_path: Path,
    contract,
) -> None:  # noqa: ANN001
    _review_key, executor_key, receipt_key = contract["keys"]
    _review_binding, executor_binding, receipt_binding = contract["bindings"]
    executor = FakeExecutor(
        executor_binding.authority_id, executor_key, contract["verifier"]
    )
    signer = FakeReceiptSigner(
        receipt_binding.authority_id,
        receipt_key,
        fail_after_store=True,
    )
    result = ProductionReleaseBrokerV03(
        verifier=contract["verifier"],
        ledger=SQLiteTerminalLedgerV03(
            (tmp_path / "receipt-readback.sqlite3").resolve(),
            dispatch_signer=contract["dispatch_signer"],
            trusted_now_ms=contract["clock"],
        ),
        executor=executor,
        receipt_signer=signer,
        claim_timeout_ms=500,
    ).execute_release(contract["command"], contract["review"])
    assert result["disposition"] == "RELEASED"
    assert executor.calls == 1
    assert signer.calls == 1
    assert signer.read_calls == 1


def test_invalid_review_cannot_create_or_burn_a_durable_claim(
    tmp_path: Path,
    contract,
) -> None:  # noqa: ANN001
    _review_key, executor_key, receipt_key = contract["keys"]
    _review_binding, executor_binding, receipt_binding = contract["bindings"]
    ledger = SQLiteTerminalLedgerV03(
        (tmp_path / "broker.sqlite3").resolve(),
        dispatch_signer=contract["dispatch_signer"],
        trusted_now_ms=contract["clock"],
    )
    broker = ProductionReleaseBrokerV03(
        verifier=contract["verifier"],
        ledger=ledger,
        executor=FakeExecutor(
            executor_binding.authority_id,
            executor_key,
            contract["verifier"],
        ),
        receipt_signer=FakeReceiptSigner(receipt_binding.authority_id, receipt_key),
    )
    forged = replace(contract["review"], command_commitment="a" * 64)
    with pytest.raises(ProductionReleaseBrokerError, match="review_authorization_join"):
        broker.execute_release(contract["command"], forged)
    assert ledger.inspect(
        contract["command"],
        contract["review"],
        verifier=contract["verifier"],
    ) is None


@pytest.mark.parametrize(
    "field",
    ["command_id", "effect_id", "capability_id", "request_nonce"],
)
def test_command_identifiers_cannot_carry_secret_like_plaintext(
    contract,
    field: str,
) -> None:  # noqa: ANN001
    with pytest.raises(ProductionReleaseBrokerError, match="_invalid"):
        replace(contract["command"], **{field: "api_token_PRIVATE_BROKER_SENTINEL"})


def test_dispatch_requires_the_fourth_pinned_authority_signature(contract) -> None:  # noqa: ANN001
    assert isinstance(contract["dispatch_signer"], DispatchClaimSignerV03)
    forged = replace(contract["dispatch"], dispatch_nonce=oid("attacker-dispatch"))
    with pytest.raises(ProductionReleaseBrokerError, match="dispatch_signature_invalid"):
        contract["verifier"].verify_dispatch_current(
            contract["command"], contract["review"], forged
        )


@pytest.mark.parametrize("case", ["pre_claim", "at_expiry", "post_lease", "future"])
def test_executor_evidence_must_be_after_signed_dispatch_and_within_lease(
    contract,
    case: str,
) -> None:  # noqa: ANN001
    _review_key, executor_key, _receipt_key = contract["keys"]
    _review_binding, executor_binding, _receipt_binding = contract["bindings"]
    dispatch = contract["dispatch"]
    terminal_at = {
        "pre_claim": dispatch.claimed_at_ms - 1,
        "at_expiry": dispatch.claim_expires_at_ms,
        "post_lease": dispatch.claim_expires_at_ms + 1,
        "future": 8_000,
    }[case]
    if case == "future":
        dispatch = sign_dispatch_claim_v03(
            contract["dispatch_key"],
            command_commitment=contract["command"].commitment,
            review_commitment=contract["review"].commitment,
            effect_id=contract["command"].effect_id,
            request_nonce=contract["command"].request_nonce,
            dispatch_nonce=oid("future-window"),
            claimed_at_ms=2_000,
            claim_expires_at_ms=8_500,
            authority_id=contract["dispatch_binding"].authority_id,
            key_id=contract["dispatch_binding"].key_id,
        )
    evidence = sign_executor_evidence_v03(
        executor_key,
        **{
            **contract["evidence"].unsigned_dict(),
            "evidence_id": oid(f"temporal:{case}"),
            "dispatch_commitment": dispatch.commitment,
            "terminal_at_ms": terminal_at,
            "authority_id": executor_binding.authority_id,
            "key_id": executor_binding.key_id,
        },
    )
    with pytest.raises(ProductionReleaseBrokerError, match="join_or_time_invalid"):
        contract["verifier"].verify_executor_evidence(
            contract["command"], contract["review"], dispatch, evidence
        )


def test_json_safe_integer_limit_applies_to_wire_and_trusted_clock(contract) -> None:  # noqa: ANN001
    with pytest.raises(ProductionReleaseBrokerError, match="command_issued_at_invalid"):
        replace(contract["command"], issued_at_ms=1 << 53)
    contract["clock"].value = 1 << 53
    with pytest.raises(ProductionReleaseBrokerError, match="trusted_time_invalid"):
        contract["verifier"].verify_review(contract["command"], contract["review"])


def test_precreated_or_later_modified_sqlite_schema_is_rejected(
    tmp_path: Path,
    contract,
) -> None:  # noqa: ANN001
    malformed = (tmp_path / "malformed.sqlite3").resolve()
    with sqlite3.connect(malformed) as connection:
        connection.execute(
            "CREATE TABLE release_terminal_v03 (command_commitment TEXT PRIMARY KEY)"
        )
    with pytest.raises(ProductionReleaseBrokerError, match="terminal_ledger_schema_invalid"):
        SQLiteTerminalLedgerV03(
            malformed,
            dispatch_signer=contract["dispatch_signer"],
            trusted_now_ms=contract["clock"],
        )

    path = (tmp_path / "modified.sqlite3").resolve()
    ledger = SQLiteTerminalLedgerV03(
        path,
        dispatch_signer=contract["dispatch_signer"],
        trusted_now_ms=contract["clock"],
    )
    with sqlite3.connect(path) as connection:
        connection.execute(
            "CREATE TRIGGER hostile_release_trigger AFTER INSERT ON release_terminal_v03 "
            "BEGIN SELECT 1; END"
        )
    with pytest.raises(ProductionReleaseBrokerError, match="terminal_ledger_schema_invalid"):
        ledger.inspect(
            contract["command"],
            contract["review"],
            verifier=contract["verifier"],
        )


@pytest.mark.parametrize("tamper", ["expiry", "signature"])
def test_claim_inspection_authenticates_signed_dispatch_and_redundant_columns(
    tmp_path: Path,
    contract,
    tamper: str,
) -> None:  # noqa: ANN001
    path = (tmp_path / f"dispatch-{tamper}.sqlite3").resolve()
    ledger = SQLiteTerminalLedgerV03(
        path,
        dispatch_signer=contract["dispatch_signer"],
        trusted_now_ms=contract["clock"],
    )
    claim = ledger.claim(
        contract["command"],
        contract["review"],
        verifier=contract["verifier"],
        claim_timeout_ms=500,
    )
    with sqlite3.connect(path) as connection:
        if tamper == "expiry":
            connection.execute(
                "UPDATE release_terminal_v03 SET claim_expires_at_ms=9000"
            )
        else:
            dispatch = DispatchClaimV03.from_wire(claim.dispatch)
            forged = replace(dispatch, signature_hex="0" * 128)
            connection.execute(
                "UPDATE release_terminal_v03 SET dispatch_json=?",
                (canonical_json_bytes(forged.wire_dict()),),
            )
    expected = "stored_dispatch_join_mismatch" if tamper == "expiry" else "dispatch_signature_invalid"
    with pytest.raises(ProductionReleaseBrokerError, match=expected):
        ledger.inspect(
            contract["command"],
            contract["review"],
            verifier=contract["verifier"],
        )


def test_pending_dispatch_retries_identical_payload_after_signer_failure(
    tmp_path: Path,
    contract,
) -> None:  # noqa: ANN001
    signer = FakeDispatchSigner(
        contract["dispatch_binding"].authority_id,
        contract["dispatch_binding"].key_id,
        contract["dispatch_key"],
        fail=True,
    )
    path = (tmp_path / "pending-dispatch.sqlite3").resolve()
    ledger = SQLiteTerminalLedgerV03(
        path,
        dispatch_signer=signer,
        trusted_now_ms=contract["clock"],
    )
    with pytest.raises(ProductionReleaseBrokerError, match="claim_reserved"):
        ledger.claim(
            contract["command"],
            contract["review"],
            verifier=contract["verifier"],
            claim_timeout_ms=500,
        )
    with sqlite3.connect(path) as connection:
        state, unsigned_wire, dispatch_wire = connection.execute(
            "SELECT state, dispatch_unsigned_json, dispatch_json "
            "FROM release_terminal_v03"
        ).fetchone()
    assert state == "PENDING_DISPATCH"
    assert dispatch_wire is None
    assert bytes(unsigned_wire) == signer.unsigned_wires[0]

    signer.fail = False
    claim = ledger.claim(
        contract["command"],
        contract["review"],
        verifier=contract["verifier"],
        claim_timeout_ms=500,
    )
    assert claim.disposition is LedgerClaimDisposition.CLAIMED
    assert signer.unsigned_wires == [bytes(unsigned_wire), bytes(unsigned_wire)]


def test_expired_pending_dispatch_is_renewed_without_reusing_old_signer_bytes(
    tmp_path: Path,
    contract,
) -> None:  # noqa: ANN001
    signer = FakeDispatchSigner(
        contract["dispatch_binding"].authority_id,
        contract["dispatch_binding"].key_id,
        contract["dispatch_key"],
        fail=True,
    )
    ledger = SQLiteTerminalLedgerV03(
        (tmp_path / "expired-pending-dispatch.sqlite3").resolve(),
        dispatch_signer=signer,
        trusted_now_ms=contract["clock"],
    )
    with pytest.raises(ProductionReleaseBrokerError, match="claim_reserved"):
        ledger.claim(
            contract["command"],
            contract["review"],
            verifier=contract["verifier"],
            claim_timeout_ms=500,
        )
    old_unsigned_wire = signer.unsigned_wires[0]

    contract["clock"].value = 2_500
    signer.fail = False
    claim = ledger.claim(
        contract["command"],
        contract["review"],
        verifier=contract["verifier"],
        claim_timeout_ms=500,
    )
    renewed = DispatchClaimV03.from_wire(claim.dispatch)
    assert claim.disposition is LedgerClaimDisposition.CLAIMED
    assert signer.calls == 2
    assert signer.unsigned_wires[1] != old_unsigned_wire
    assert renewed.claimed_at_ms == 2_500
    assert renewed.claim_expires_at_ms == 3_000


def test_sqlite_ledger_does_not_retain_windows_file_handles(
    tmp_path: Path,
    contract,
) -> None:  # noqa: ANN001
    path = (tmp_path / "handle-release.sqlite3").resolve()
    ledger = SQLiteTerminalLedgerV03(
        path,
        dispatch_signer=contract["dispatch_signer"],
        trusted_now_ms=contract["clock"],
    )
    assert ledger.inspect(
        contract["command"],
        contract["review"],
        verifier=contract["verifier"],
    ) is None

    moved = path.with_suffix(".moved")
    os.replace(path, moved)
    assert moved.is_file()


class LockProbeDispatchSigner(FakeDispatchSigner):
    def __init__(self, *args, database_path: Path, **kwargs) -> None:  # noqa: ANN002, ANN003
        super().__init__(*args, **kwargs)
        self.database_path = database_path
        self.writer_lock_available = False

    def sign_dispatch(
        self,
        unsigned_dispatch_wire: bytes,
        *,
        deadline_at_ms: int,
    ) -> bytes:
        with sqlite3.connect(self.database_path, timeout=0.1, isolation_level=None) as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute("ROLLBACK")
        self.writer_lock_available = True
        return super().sign_dispatch(
            unsigned_dispatch_wire,
            deadline_at_ms=deadline_at_ms,
        )


def test_dispatch_signer_call_occurs_outside_sqlite_writer_transaction(
    tmp_path: Path,
    contract,
) -> None:  # noqa: ANN001
    path = (tmp_path / "signer-lock.sqlite3").resolve()
    signer = LockProbeDispatchSigner(
        contract["dispatch_binding"].authority_id,
        contract["dispatch_binding"].key_id,
        contract["dispatch_key"],
        database_path=path,
    )
    ledger = SQLiteTerminalLedgerV03(
        path,
        dispatch_signer=signer,
        trusted_now_ms=contract["clock"],
    )
    assert ledger.claim(
        contract["command"],
        contract["review"],
        verifier=contract["verifier"],
    ).disposition is LedgerClaimDisposition.CLAIMED
    assert signer.writer_lock_available is True


def test_sqlite_durability_pragmas_are_read_back(tmp_path: Path, contract) -> None:  # noqa: ANN001
    ledger = SQLiteTerminalLedgerV03(
        (tmp_path / "durable.sqlite3").resolve(),
        dispatch_signer=contract["dispatch_signer"],
        trusted_now_ms=contract["clock"],
    )
    with ledger._connect() as connection:  # noqa: SLF001 - security read-back test
        assert connection.execute("PRAGMA journal_mode").fetchone() == ("wal",)
        assert connection.execute("PRAGMA synchronous").fetchone() == (2,)


def test_receipt_key_alone_cannot_forge_restart_chain(
    tmp_path: Path,
    contract,
) -> None:  # noqa: ANN001
    _review_key, executor_key, receipt_key = contract["keys"]
    _review_binding, executor_binding, receipt_binding = contract["bindings"]
    path = (tmp_path / "receipt-only-forgery.sqlite3").resolve()
    executor = FakeExecutor(
        executor_binding.authority_id, executor_key, contract["verifier"]
    )
    signer = FakeReceiptSigner(receipt_binding.authority_id, receipt_key)
    broker = ProductionReleaseBrokerV03(
        verifier=contract["verifier"],
        ledger=SQLiteTerminalLedgerV03(
            path,
            dispatch_signer=contract["dispatch_signer"],
            trusted_now_ms=contract["clock"],
        ),
        executor=executor,
        receipt_signer=signer,
    )
    terminal = broker.execute_release(contract["command"], contract["review"])
    with sqlite3.connect(path) as connection:
        row = connection.execute(
            "SELECT executor_evidence_json FROM release_terminal_v03"
        ).fetchone()
        assert row is not None
        evidence = decode_executor_evidence_v03(bytes(row[0]))
        invented = replace(evidence, evidence_id=oid("invented-without-executor-key"))
        forged_receipt = sign_terminal_receipt_v03(
            receipt_key,
            denied=False,
            **{
                **decode_terminal_receipt_v03(
                    canonical_json_bytes(terminal)
                ).unsigned_dict(),
                "receipt_id": oid("receipt-key-only-forgery"),
                "executor_evidence_commitment": invented.commitment,
            },
        )
        connection.execute(
            "UPDATE release_terminal_v03 SET receipt_json=?, receipt_commitment=?, "
            "executor_evidence_json=?, executor_evidence_commitment=?",
            (
                canonical_json_bytes(forged_receipt.wire_dict()),
                forged_receipt.commitment,
                canonical_json_bytes(invented.wire_dict()),
                invented.commitment,
            ),
        )
    with pytest.raises(ProductionReleaseBrokerError, match="executor_signature_invalid"):
        broker.execute_release(contract["command"], contract["review"])
    assert executor.calls == 1


def test_fresh_claim_cannot_close_without_executor_evidence(
    tmp_path: Path,
    contract,
) -> None:  # noqa: ANN001
    ledger = SQLiteTerminalLedgerV03(
        (tmp_path / "no-evidence.sqlite3").resolve(),
        dispatch_signer=contract["dispatch_signer"],
        trusted_now_ms=contract["clock"],
    )
    ledger.claim(
        contract["command"],
        contract["review"],
        verifier=contract["verifier"],
    )
    with pytest.raises(ProductionReleaseBrokerError, match="exact_terminal_chain_required"):
        ledger.record_terminal(
            contract["command"],
            contract["review"],
            contract["receipt"],
            None,  # type: ignore[arg-type]
            verifier=contract["verifier"],
        )


class ForwardingLedger:
    production_ready = False

    def __init__(self, inner: SQLiteTerminalLedgerV03) -> None:
        self.inner = inner

    def inspect(self, *args, **kwargs):  # noqa: ANN002, ANN003, ANN201
        return self.inner.inspect(*args, **kwargs)

    def claim(self, *args, **kwargs):  # noqa: ANN002, ANN003, ANN201
        return self.inner.claim(*args, **kwargs)

    def record_terminal(self, *args, **kwargs):  # noqa: ANN002, ANN003, ANN201
        return self.inner.record_terminal(*args, **kwargs)

    def record_executor_evidence(self, *args, **kwargs):  # noqa: ANN002, ANN003, ANN201
        return self.inner.record_executor_evidence(*args, **kwargs)


def test_broker_accepts_a_durable_ledger_adapter_not_only_local_sqlite(
    tmp_path: Path,
    contract,
) -> None:  # noqa: ANN001
    _review_key, executor_key, receipt_key = contract["keys"]
    _review_binding, executor_binding, receipt_binding = contract["bindings"]
    inner = SQLiteTerminalLedgerV03(
        (tmp_path / "adapter.sqlite3").resolve(),
        dispatch_signer=contract["dispatch_signer"],
        trusted_now_ms=contract["clock"],
    )
    result = ProductionReleaseBrokerV03(
        verifier=contract["verifier"],
        ledger=ForwardingLedger(inner),
        executor=FakeExecutor(
            executor_binding.authority_id,
            executor_key,
            contract["verifier"],
        ),
        receipt_signer=FakeReceiptSigner(receipt_binding.authority_id, receipt_key),
    ).execute_release(contract["command"], contract["review"])
    assert result["disposition"] == "RELEASED"


class ExpiringClaimLedger(ForwardingLedger):
    def __init__(self, inner: SQLiteTerminalLedgerV03, clock: Clock) -> None:
        super().__init__(inner)
        self.clock = clock

    def claim(self, *args, **kwargs):  # noqa: ANN002, ANN003, ANN201
        claim = self.inner.claim(*args, **kwargs)
        self.clock.value = DispatchClaimV03.from_wire(claim.dispatch).claim_expires_at_ms
        return claim


def test_dispatch_is_rechecked_after_claim_before_executor_transport(
    tmp_path: Path,
    contract,
) -> None:  # noqa: ANN001
    _review_key, executor_key, receipt_key = contract["keys"]
    _review_binding, executor_binding, receipt_binding = contract["bindings"]
    inner = SQLiteTerminalLedgerV03(
        (tmp_path / "expired-before-transport.sqlite3").resolve(),
        dispatch_signer=contract["dispatch_signer"],
        trusted_now_ms=contract["clock"],
    )
    executor = FakeExecutor(
        executor_binding.authority_id, executor_key, contract["verifier"]
    )
    broker = ProductionReleaseBrokerV03(
        verifier=contract["verifier"],
        ledger=ExpiringClaimLedger(inner, contract["clock"]),
        executor=executor,
        receipt_signer=FakeReceiptSigner(receipt_binding.authority_id, receipt_key),
        claim_timeout_ms=500,
    )
    with pytest.raises(ProductionReleaseBrokerError, match="dispatch_claim_join_or_time_invalid"):
        broker.execute_release(contract["command"], contract["review"])
    assert executor.calls == 0

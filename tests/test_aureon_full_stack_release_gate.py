from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from aureon.autonomous.aureon_full_stack_release_gate import (
    CANONICAL_STACK_LAYERS,
    LOCAL_ACCEPTANCE,
    PRODUCTION_READBACK,
    FullStackHold,
    FullStackReleaseGate,
    FullStackReleaseRequest,
    LocalFullStackEvidenceResolver,
    build_full_stack_bundle,
    validate_full_stack_release_receipt,
)
from tests.aureon_full_stack_fixtures import (
    FULL_STACK_NOW,
    StaticFullStackResolver,
    build_test_full_stack_bundle,
    build_test_full_stack_gate,
)

SCOPE = hashlib.sha256(b"whole-repo-release").hexdigest()


def test_local_acceptance_requires_every_canonical_layer_once() -> None:
    gate, request, resolver = build_test_full_stack_gate(scope_digest=SCOPE)

    receipt = gate.require_accept(request)

    assert receipt["decision"] == "ACCEPT"
    assert receipt["reason"] == "all_layers_local_contracts_passed"
    assert receipt["required_layer_ids"] == list(CANONICAL_STACK_LAYERS)
    assert len(receipt["layer_receipt_ids"]) == 12
    assert len(set(receipt["layer_receipt_ids"])) == 12
    assert resolver.calls == 1
    assert receipt["action_eligible"] is False
    assert receipt["economic_eligible"] is False


def test_missing_layer_returns_evidence_only_hold() -> None:
    request = FullStackReleaseRequest("release:missing", "local", LOCAL_ACCEPTANCE, SCOPE)
    resolver = StaticFullStackResolver()
    complete = build_test_full_stack_bundle(request)
    resolver.bundle = build_full_stack_bundle(
        resolver_id=resolver.resolver_id,
        request=request,
        issued_at=FULL_STACK_NOW - 5.0,
        layers=complete["layers"][:-1],
    )
    gate = FullStackReleaseGate(resolver=resolver, now=lambda: FULL_STACK_NOW)

    result = gate.evaluate(request)

    assert result.decision == "HOLD"
    assert result.receipt["reason"] == "complete_fresh_full_stack_evidence_required"
    assert result.receipt["layer_receipt_ids"] == []
    assert result.receipt["actionable"] is False


def test_production_requires_provider_readback_for_every_layer() -> None:
    request = FullStackReleaseRequest("release:production", "production", PRODUCTION_READBACK, SCOPE)
    resolver = StaticFullStackResolver(build_test_full_stack_bundle(request, provider_readback=False))
    gate = FullStackReleaseGate(resolver=resolver, now=lambda: FULL_STACK_NOW)

    with pytest.raises(FullStackHold, match="complete_fresh"):
        gate.require_accept(request)


def test_production_accepts_only_complete_provider_readback() -> None:
    gate, request, _resolver = build_test_full_stack_gate(
        scope_digest=SCOPE,
        release_id="release:production-readback",
        environment="production",
        assurance_level=PRODUCTION_READBACK,
        provider_readback=True,
    )

    receipt = gate.require_accept(request)

    assert receipt["decision"] == "ACCEPT"
    assert receipt["reason"] == "all_layers_provider_read_back"
    assert receipt["assurance_level"] == PRODUCTION_READBACK


def test_stale_layer_holds_even_when_bundle_hash_is_rebuilt() -> None:
    request = FullStackReleaseRequest("release:stale", "local", LOCAL_ACCEPTANCE, SCOPE)
    resolver = StaticFullStackResolver()
    bundle = build_test_full_stack_bundle(request, now=FULL_STACK_NOW - 100_000.0)
    resolver.bundle = bundle
    gate = FullStackReleaseGate(resolver=resolver, now=lambda: FULL_STACK_NOW)

    assert gate.evaluate(request).decision == "HOLD"


def test_scope_drift_holds_before_release() -> None:
    gate, request, resolver = build_test_full_stack_gate(scope_digest=SCOPE)
    drifted = FullStackReleaseRequest(
        release_id=request.release_id,
        environment=request.environment,
        assurance_level=request.assurance_level,
        scope_digest="f" * 64,
    )

    assert gate.evaluate(drifted).decision == "HOLD"
    assert resolver.calls == 1


def test_missing_required_layer_control_holds_after_rehash() -> None:
    request = FullStackReleaseRequest("release:control", "local", LOCAL_ACCEPTANCE, SCOPE)
    resolver = StaticFullStackResolver()
    bundle = build_test_full_stack_bundle(request)
    layer = dict(bundle["layers"][0])
    layer["control_ids"] = layer["control_ids"][:-1]
    layer.pop("receipt_id")
    from aureon.autonomous.aureon_full_stack_release_gate import _sha256

    layer["receipt_id"] = f"stack:layer:{_sha256(layer)}"
    resolver.bundle = build_full_stack_bundle(
        resolver_id=resolver.resolver_id,
        request=request,
        issued_at=FULL_STACK_NOW - 5.0,
        layers=[layer, *bundle["layers"][1:]],
    )
    gate = FullStackReleaseGate(resolver=resolver, now=lambda: FULL_STACK_NOW)

    assert gate.evaluate(request).decision == "HOLD"


def test_rehashed_true_eligibility_flag_is_rejected() -> None:
    request = FullStackReleaseRequest("release:eligibility", "local", LOCAL_ACCEPTANCE, SCOPE)
    resolver = StaticFullStackResolver()
    bundle = build_test_full_stack_bundle(request)
    layer = dict(bundle["layers"][0])
    layer["actionable"] = True
    layer.pop("receipt_id")
    from aureon.autonomous.aureon_full_stack_release_gate import _sha256

    layer["receipt_id"] = f"stack:layer:{_sha256(layer)}"
    layers = [layer, *bundle["layers"][1:]]
    resolver.bundle = build_full_stack_bundle(
        resolver_id=resolver.resolver_id,
        request=request,
        issued_at=FULL_STACK_NOW - 5.0,
        layers=layers,
    )
    gate = FullStackReleaseGate(resolver=resolver, now=lambda: FULL_STACK_NOW)

    assert gate.evaluate(request).decision == "HOLD"


def test_missing_local_manifest_holds_without_creating_evidence(tmp_path: Path) -> None:
    request = FullStackReleaseRequest("release:absent", "local", LOCAL_ACCEPTANCE, SCOPE)
    resolver = LocalFullStackEvidenceResolver(root=tmp_path)
    gate = FullStackReleaseGate(resolver=resolver, now=lambda: FULL_STACK_NOW)

    result = gate.evaluate(request)

    assert result.decision == "HOLD"
    assert not (tmp_path / "docs").exists()


def test_resolver_exception_is_a_hold_not_an_accept() -> None:
    request = FullStackReleaseRequest("release:error", "local", LOCAL_ACCEPTANCE, SCOPE)
    resolver = StaticFullStackResolver(error=True)
    gate = FullStackReleaseGate(resolver=resolver, now=lambda: FULL_STACK_NOW)

    assert gate.evaluate(request).decision == "HOLD"
    assert resolver.calls == 1


def test_rehashed_release_lineage_must_still_name_all_twelve_layers() -> None:
    gate, request, _resolver = build_test_full_stack_gate(scope_digest=SCOPE)
    receipt = dict(gate.require_accept(request))
    receipt["layer_receipt_ids"] = receipt["layer_receipt_ids"][:-1]
    receipt.pop("receipt_id")
    from aureon.autonomous.aureon_full_stack_release_gate import _sha256

    receipt["receipt_id"] = f"stack:release:{_sha256(receipt)}"

    with pytest.raises(ValueError, match="complete_full_stack_accept_lineage_required"):
        validate_full_stack_release_receipt(receipt, request=request)

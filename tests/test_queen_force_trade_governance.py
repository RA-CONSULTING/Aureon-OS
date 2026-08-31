from __future__ import annotations

import inspect
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest

from aureon.queen import queen_force_trade_governance as governance

PLAN = governance.ForceTradePlan(
    provider="kraken",
    symbol="XXBTZUSD",
    side="BUY",
    quantity="0.0001",
)
OTHER_PLAN = governance.ForceTradePlan(
    provider="binance",
    symbol="BTCUSDT",
    side="BUY",
    quantity="0.0001",
)


def _mint_simulated_production_authorization(monkeypatch, *, plan=PLAN):
    def validated(*_args, **_kwargs):
        return {
            "valid": True,
            "production_ready": True,
            "star_commitment": "a" * 64,
            "expires_at_ms": 5_000,
        }

    monkeypatch.setattr(governance, "validate_magic_star_v02", validated)
    return governance._mint_magic_star_authorization(
        star=object(),
        trust={},
        plan=plan,
        trusted_now_ms=lambda: 1_000,
    )


def test_default_denies_without_exact_plan_or_magic_star_authorization(monkeypatch):
    monkeypatch.setattr(governance, "_module_available", lambda _name: True)

    decision = governance.evaluate_queen_force_trade_authority()

    assert decision.allowed is False
    assert "exact_force_trade_plan_required" in decision.missing_requirements


def test_environment_flags_cannot_authorize_force_trade(monkeypatch):
    monkeypatch.setattr(governance, "_module_available", lambda _name: True)
    monkeypatch.setenv("AUREON_QUEEN_FORCE_TRADE_ONLY", "false")
    monkeypatch.setenv("AUREON_QUEEN_FORCE_TRADE_APPROVED", "true")
    monkeypatch.setenv("LIVE", "1")

    decision = governance.evaluate_queen_force_trade_authority(plan=PLAN)

    assert decision.allowed is False
    assert decision.missing_requirements == [
        "external_production_magic_star_authority_service_unavailable",
        "production_magic_star_authorization_required"
    ]
    assert "bypass" not in decision.reason.lower()


def test_module_presence_is_readiness_not_authority(monkeypatch):
    monkeypatch.setattr(governance, "_module_available", lambda _name: True)

    decision = governance.evaluate_queen_force_trade_authority(plan=PLAN)

    assert all(decision.modules_ready.values())
    assert decision.allowed is False
    assert "production_magic_star_authorization_required" in decision.reason


def test_authorization_is_opaque_and_forged_object_is_rejected(monkeypatch):
    monkeypatch.setattr(governance, "_module_available", lambda _name: True)

    with pytest.raises(TypeError, match="not production authority"):
        governance.OpaqueForceTradeAuthorization()

    decision = governance.evaluate_queen_force_trade_authority(
        plan=PLAN,
        authorization=object(),  # type: ignore[arg-type]
    )
    assert decision.allowed is False
    assert decision.missing_requirements == [
        "external_production_magic_star_authority_service_unavailable",
        "opaque_magic_star_authorization_required",
    ]


def test_local_development_magic_star_cannot_mint_live_authority(monkeypatch):
    monkeypatch.setattr(
        governance,
        "validate_magic_star_v02",
        lambda *_args, **_kwargs: {
            "valid": True,
            "production_ready": False,
            "star_commitment": "a" * 64,
            "expires_at_ms": 5_000,
        },
    )

    with pytest.raises(
        governance.QueenForceTradeAuthorizationError,
        match="production_magic_star_authorization_unavailable",
    ):
        governance._mint_magic_star_authorization(
            star=object(),
            trust={},
            plan=PLAN,
            trusted_now_ms=lambda: 1_000,
        )


def test_introspected_in_process_construction_token_still_cannot_release_trade(monkeypatch):
    monkeypatch.setattr(governance, "_module_available", lambda _name: True)
    token = inspect.getclosurevars(
        governance.OpaqueForceTradeAuthorization.__init__
    ).nonlocals["construction_token"]
    forged = governance.OpaqueForceTradeAuthorization(
        token,
        plan_sha256=PLAN.commitment,
        star_commitment="f" * 64,
        expires_at_ms=9_999_999,
        production_ready=True,
    )

    decision = governance.claim_queen_force_trade_authority(
        plan=PLAN,
        authorization=forged,
        trusted_now_ms=lambda: 1_000,
    )

    assert decision.allowed is False
    assert decision.missing_requirements == [
        "external_production_magic_star_authority_service_unavailable"
    ]


def test_wrong_exact_plan_does_not_consume_authorization(monkeypatch):
    monkeypatch.setattr(governance, "_module_available", lambda _name: True)
    authorization = _mint_simulated_production_authorization(monkeypatch)

    wrong = governance.claim_queen_force_trade_authority(
        plan=OTHER_PLAN,
        authorization=authorization,
        trusted_now_ms=lambda: 1_000,
    )
    right = governance.claim_queen_force_trade_authority(
        plan=PLAN,
        authorization=authorization,
        trusted_now_ms=lambda: 1_000,
    )

    assert wrong.allowed is False
    assert wrong.missing_requirements == [
        "force_trade_authorization_plan_mismatch",
        "external_production_magic_star_authority_service_unavailable",
    ]
    assert right.allowed is False
    assert right.missing_requirements == [
        "external_production_magic_star_authority_service_unavailable"
    ]


def test_locally_minted_authorization_never_becomes_production_authority(monkeypatch):
    monkeypatch.setattr(governance, "_module_available", lambda _name: True)
    authorization = _mint_simulated_production_authorization(monkeypatch)

    first = governance.claim_queen_force_trade_authority(
        plan=PLAN,
        authorization=authorization,
        trusted_now_ms=lambda: 1_000,
    )
    replay = governance.claim_queen_force_trade_authority(
        plan=PLAN,
        authorization=authorization,
        trusted_now_ms=lambda: 1_000,
    )

    assert first.allowed is False
    assert replay.allowed is False
    assert first.missing_requirements == replay.missing_requirements == [
        "external_production_magic_star_authority_service_unavailable"
    ]


def test_concurrent_local_claims_all_remain_on_hold(monkeypatch):
    monkeypatch.setattr(governance, "_module_available", lambda _name: True)
    authorization = _mint_simulated_production_authorization(monkeypatch)
    workers = 12
    start = Barrier(workers)

    def claim() -> bool:
        start.wait()
        return governance.claim_queen_force_trade_authority(
            plan=PLAN,
            authorization=authorization,
            trusted_now_ms=lambda: 1_000,
        ).allowed

    with ThreadPoolExecutor(max_workers=workers) as pool:
        outcomes = list(pool.map(lambda _index: claim(), range(workers)))

    assert outcomes.count(True) == 0
    assert outcomes.count(False) == workers


def test_expired_authorization_is_not_claimable(monkeypatch):
    monkeypatch.setattr(governance, "_module_available", lambda _name: True)
    authorization = _mint_simulated_production_authorization(monkeypatch)

    decision = governance.claim_queen_force_trade_authority(
        plan=PLAN,
        authorization=authorization,
        trusted_now_ms=lambda: 5_001,
    )

    assert decision.allowed is False
    assert decision.missing_requirements == [
        "force_trade_authorization_expired",
        "external_production_magic_star_authority_service_unavailable",
    ]

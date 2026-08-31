#!/usr/bin/env python3
"""Fail-closed authorization contract for any force-trade dispatcher.

Environment variables and Queen module availability are status inputs, never
authority. The checked-in Plumber v0.2 Magic-Star profile is explicitly a
local-development profile (``production_ready=False``). Python objects are also
forgeable by code already executing in the same process, so no object minted or
constructed here is accepted as production authority. Every claim remains on
HOLD until a separate trusted authority service is implemented and verified.
"""

from __future__ import annotations

import importlib.util
import re
import time
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from threading import Lock
from typing import Callable, Dict, List, Mapping

from aureon.plumber.crypto import domain_hash
from aureon.plumber.magic_star_v02 import (
    AuthorityBindingV02,
    MagicStarError,
    MagicStarV02,
    validate_magic_star_v02,
)

FORCE_TRADE_CAPABILITY_ID = "aureon.force-trade.exact-order.v1"

_REQUIRED_QUEEN_MODULES: Dict[str, str] = {
    "aureon.queen.queen_consciousness_model": "Core cognition state machine",
    "aureon.queen.queen_sentience_integration": "Unified systems integration",
    "aureon.queen.queen_neuron": "Deep-learning decision engine",
}
_TOKEN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$")


class QueenForceTradeAuthorizationError(ValueError):
    """Stable denial raised while validating a Magic-Star authorization."""

    def __init__(self, code: str) -> None:
        self.code = str(code)
        super().__init__(self.code)


def _canonical_token(value: object, *, code: str, upper: bool = False) -> str:
    candidate = str(value or "").strip()
    if _TOKEN.fullmatch(candidate) is None:
        raise QueenForceTradeAuthorizationError(code)
    return candidate.upper() if upper else candidate.lower()


def _canonical_positive_decimal(value: object) -> str:
    candidate = str(value or "").strip()
    try:
        number = Decimal(candidate)
    except InvalidOperation as exc:
        raise QueenForceTradeAuthorizationError("force_trade_quantity_invalid") from exc
    if not number.is_finite() or number <= 0:
        raise QueenForceTradeAuthorizationError("force_trade_quantity_invalid")
    normalized = format(number, "f")
    if "." in normalized:
        normalized = normalized.rstrip("0").rstrip(".")
    return normalized


@dataclass(frozen=True, slots=True)
class ForceTradePlan:
    """Canonical, immutable description of one exact provider order."""

    provider: str
    symbol: str
    side: str
    quantity: str
    quantity_kind: str = "base_units"
    order_type: str = "market"
    time_in_force: str = "provider_default"

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "provider",
            _canonical_token(self.provider, code="force_trade_provider_invalid"),
        )
        object.__setattr__(
            self,
            "symbol",
            _canonical_token(
                self.symbol,
                code="force_trade_symbol_invalid",
                upper=True,
            ),
        )
        side = _canonical_token(
            self.side,
            code="force_trade_side_invalid",
            upper=True,
        )
        if side not in {"BUY", "SELL"}:
            raise QueenForceTradeAuthorizationError("force_trade_side_invalid")
        object.__setattr__(self, "side", side)
        object.__setattr__(self, "quantity", _canonical_positive_decimal(self.quantity))
        object.__setattr__(
            self,
            "quantity_kind",
            _canonical_token(
                self.quantity_kind,
                code="force_trade_quantity_kind_invalid",
            ),
        )
        object.__setattr__(
            self,
            "order_type",
            _canonical_token(self.order_type, code="force_trade_order_type_invalid"),
        )
        object.__setattr__(
            self,
            "time_in_force",
            _canonical_token(
                self.time_in_force,
                code="force_trade_time_in_force_invalid",
            ),
        )

    def public_dict(self) -> dict[str, str]:
        return {
            "provider": self.provider,
            "symbol": self.symbol,
            "side": self.side,
            "quantity": self.quantity,
            "quantity_kind": self.quantity_kind,
            "order_type": self.order_type,
            "time_in_force": self.time_in_force,
        }

    @property
    def commitment(self) -> str:
        return domain_hash("AUREON-FORCE-TRADE-EXACT-PLAN-V1", self.public_dict())


def force_trade_release_context_sha256(plan: ForceTradePlan) -> str:
    if not isinstance(plan, ForceTradePlan):
        raise QueenForceTradeAuthorizationError("exact_force_trade_plan_required")
    return domain_hash(
        "AUREON-FORCE-TRADE-AUTHORIZATION-CONTEXT-V1",
        {
            "capability_id": FORCE_TRADE_CAPABILITY_ID,
            "plan_sha256": plan.commitment,
        },
    )


def force_trade_candidate_center_sha256(plan: ForceTradePlan) -> str:
    if not isinstance(plan, ForceTradePlan):
        raise QueenForceTradeAuthorizationError("exact_force_trade_plan_required")
    return domain_hash(
        "AUREON-FORCE-TRADE-CANDIDATE-CENTER-V1",
        {
            "capability_id": FORCE_TRADE_CAPABILITY_ID,
            "plan_sha256": plan.commitment,
        },
    )


def _system_now_ms() -> int:
    return time.time_ns() // 1_000_000


def _build_opaque_authorization_boundary():
    construction_token = object()

    class OpaqueForceTradeAuthorization:
        """Local one-use state carrier; not an in-process security boundary.

        The constructor token reduces accidental misuse only.  Python code in
        this process can introspect or monkeypatch it, so production dispatch
        never treats an instance as sufficient authority.
        """

        __slots__ = (
            "__plan_sha256",
            "__star_commitment",
            "__expires_at_ms",
            "__production_ready",
            "__claimed",
            "__lock",
        )

        def __init__(
            self,
            token: object = None,
            *,
            plan_sha256: str = "",
            star_commitment: str = "",
            expires_at_ms: int = 0,
            production_ready: bool = False,
        ) -> None:
            if token is not construction_token:
                raise TypeError(
                    "OpaqueForceTradeAuthorization is not publicly constructible; "
                    "it is a local state carrier, not production authority"
                )
            self.__plan_sha256 = str(plan_sha256)
            self.__star_commitment = str(star_commitment)
            self.__expires_at_ms = int(expires_at_ms)
            self.__production_ready = production_ready is True
            self.__claimed = False
            self.__lock = Lock()

        def __repr__(self) -> str:
            return "OpaqueForceTradeAuthorization(<redacted>)"

        def _status_exact_plan(self, plan: ForceTradePlan, *, now_ms: int) -> str | None:
            if not isinstance(plan, ForceTradePlan):
                return "exact_force_trade_plan_required"
            with self.__lock:
                if self.__production_ready is not True:
                    return "production_magic_star_authorization_unavailable"
                if self.__claimed:
                    return "force_trade_authorization_already_consumed"
                if int(now_ms) > self.__expires_at_ms:
                    return "force_trade_authorization_expired"
                if plan.commitment != self.__plan_sha256:
                    return "force_trade_authorization_plan_mismatch"
                return None

        def _claim_exact_plan(self, plan: ForceTradePlan, *, now_ms: int) -> str | None:
            if not isinstance(plan, ForceTradePlan):
                return "exact_force_trade_plan_required"
            with self.__lock:
                if self.__production_ready is not True:
                    return "production_magic_star_authorization_unavailable"
                if self.__claimed:
                    return "force_trade_authorization_already_consumed"
                if int(now_ms) > self.__expires_at_ms:
                    return "force_trade_authorization_expired"
                if plan.commitment != self.__plan_sha256:
                    return "force_trade_authorization_plan_mismatch"
                # No rollback is exposed. Once the final dispatcher claims the
                # capability, provider-side effects may have started even if its
                # handler later raises.
                self.__claimed = True
                return None

    OpaqueForceTradeAuthorization.__name__ = "OpaqueForceTradeAuthorization"
    OpaqueForceTradeAuthorization.__qualname__ = "OpaqueForceTradeAuthorization"
    OpaqueForceTradeAuthorization.__module__ = __name__

    def mint(
        *,
        star: MagicStarV02,
        trust: Mapping[str, AuthorityBindingV02],
        plan: ForceTradePlan,
        trusted_now_ms: Callable[[], int] = _system_now_ms,
    ) -> OpaqueForceTradeAuthorization:
        if not isinstance(plan, ForceTradePlan):
            raise QueenForceTradeAuthorizationError("exact_force_trade_plan_required")
        try:
            summary = validate_magic_star_v02(
                star,
                trust=trust,
                expected_release_context_sha256=force_trade_release_context_sha256(plan),
                expected_candidate_center_sha256=force_trade_candidate_center_sha256(plan),
                trusted_now_ms=trusted_now_ms,
            )
        except MagicStarError as exc:
            raise QueenForceTradeAuthorizationError(
                "force_trade_magic_star_validation_failed"
            ) from exc
        if summary.get("valid") is not True:
            raise QueenForceTradeAuthorizationError(
                "force_trade_magic_star_validation_failed"
            )
        if summary.get("production_ready") is not True:
            raise QueenForceTradeAuthorizationError(
                "production_magic_star_authorization_unavailable"
            )
        return OpaqueForceTradeAuthorization(
            construction_token,
            plan_sha256=plan.commitment,
            star_commitment=str(summary.get("star_commitment", "")),
            expires_at_ms=int(summary.get("expires_at_ms", 0)),
            production_ready=True,
        )

    return OpaqueForceTradeAuthorization, mint


OpaqueForceTradeAuthorization, _mint_magic_star_authorization = (
    _build_opaque_authorization_boundary()
)


@dataclass
class QueenForceTradeDecision:
    """Result of force-trade preflight or final atomic claim."""

    allowed: bool
    reason: str
    modules_ready: Dict[str, bool] = field(default_factory=dict)
    missing_requirements: List[str] = field(default_factory=list)
    plan_sha256: str | None = None
    capability_id: str = FORCE_TRADE_CAPABILITY_ID


def _module_available(module_name: str) -> bool:
    return importlib.util.find_spec(module_name) is not None


def _base_preflight(
    *,
    plan: ForceTradePlan | None,
    authorization: OpaqueForceTradeAuthorization | None,
    trusted_now_ms: Callable[[], int],
) -> tuple[Dict[str, bool], List[str], str | None]:
    modules_ready = {
        module: _module_available(module) for module in _REQUIRED_QUEEN_MODULES
    }
    missing = [
        f"queen_module_unavailable:{module}"
        for module, ready in modules_ready.items()
        if not ready
    ]
    if not isinstance(plan, ForceTradePlan):
        missing.insert(0, "exact_force_trade_plan_required")
        return modules_ready, missing, None
    # No Python object can establish a trust boundary against hostile code in
    # the same interpreter.  Keep the checked-in production path closed until
    # an independently deployed authority service/HSM returns verifiable proof.
    missing.insert(0, "external_production_magic_star_authority_service_unavailable")
    if authorization is None:
        missing.insert(1, "production_magic_star_authorization_required")
        return modules_ready, missing, plan.commitment
    if not isinstance(authorization, OpaqueForceTradeAuthorization):
        missing.insert(1, "opaque_magic_star_authorization_required")
        return modules_ready, missing, plan.commitment
    status = authorization._status_exact_plan(plan, now_ms=int(trusted_now_ms()))
    if status is not None:
        missing.insert(0, status)
    return modules_ready, missing, plan.commitment


def evaluate_queen_force_trade_authority(
    *,
    plan: ForceTradePlan | None = None,
    authorization: OpaqueForceTradeAuthorization | None = None,
    trusted_now_ms: Callable[[], int] = _system_now_ms,
) -> QueenForceTradeDecision:
    """Perform a non-consuming preflight without constructing provider clients."""

    modules_ready, missing, plan_sha256 = _base_preflight(
        plan=plan,
        authorization=authorization,
        trusted_now_ms=trusted_now_ms,
    )
    if missing:
        return QueenForceTradeDecision(
            allowed=False,
            reason="Force trade HOLD: " + ", ".join(missing),
            modules_ready=modules_ready,
            missing_requirements=missing,
            plan_sha256=plan_sha256,
        )
    return QueenForceTradeDecision(
        allowed=True,
        reason="Force trade preflight ready for final atomic authorization claim",
        modules_ready=modules_ready,
        plan_sha256=plan_sha256,
    )


def claim_queen_force_trade_authority(
    *,
    plan: ForceTradePlan,
    authorization: OpaqueForceTradeAuthorization | None,
    trusted_now_ms: Callable[[], int] = _system_now_ms,
) -> QueenForceTradeDecision:
    """Atomically consume one exact-plan authorization at the final dispatcher."""

    preflight = evaluate_queen_force_trade_authority(
        plan=plan,
        authorization=authorization,
        trusted_now_ms=trusted_now_ms,
    )
    if not preflight.allowed:
        return preflight
    assert isinstance(authorization, OpaqueForceTradeAuthorization)
    denial = authorization._claim_exact_plan(plan, now_ms=int(trusted_now_ms()))
    if denial is not None:
        return QueenForceTradeDecision(
            allowed=False,
            reason=f"Force trade HOLD: {denial}",
            modules_ready=preflight.modules_ready,
            missing_requirements=[denial],
            plan_sha256=plan.commitment,
        )
    return QueenForceTradeDecision(
        allowed=True,
        reason="Force trade authorization atomically claimed for exact plan",
        modules_ready=preflight.modules_ready,
        plan_sha256=plan.commitment,
    )


__all__ = [
    "FORCE_TRADE_CAPABILITY_ID",
    "ForceTradePlan",
    "OpaqueForceTradeAuthorization",
    "QueenForceTradeAuthorizationError",
    "QueenForceTradeDecision",
    "claim_queen_force_trade_authority",
    "evaluate_queen_force_trade_authority",
    "force_trade_candidate_center_sha256",
    "force_trade_release_context_sha256",
]

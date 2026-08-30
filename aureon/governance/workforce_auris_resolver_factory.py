"""Restart-safe Auris-node reconstruction from a measured workforce window.

The calibration window is authority-free evidence.  This factory will only
reconstruct nodes for the exact final provider moment bound into that window.
A newer, older, or merely different HNC/Auris moment requires recalibration.
"""

from __future__ import annotations

import copy
import math
import time
from collections.abc import Callable, Collection, Mapping
from decimal import Decimal
from typing import Any

from aureon.governance.cognition_gate import CognitionGovernanceRequest
from aureon.governance.live_workforce_calibration import (
    validate_workforce_auris_calibration_report,
)
from aureon.governance.queen_crown_supplier import (
    ProviderEvidenceLoader,
    load_local_request_provider_evidence,
)
from aureon.governance.workforce_auris_node_resolver import (
    TruthGatedWorkforceAurisNodeResolver,
    bind_truth_gated_workforce_auris_resolver,
)
from aureon.swarm.auris_node_receipts import (
    DEFAULT_MAX_AGE_S,
    TrustedAurisNodeResolver,
    validate_provider_moment,
)

_FACTORY_TOKEN = object()


def _nonblank(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label}_required")
    return value.strip()


def _positive_finite(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"positive_finite_{label}_required")
    result = float(value)
    if not math.isfinite(result) or result <= 0.0:
        raise ValueError(f"positive_finite_{label}_required")
    return result


def _source_timestamp_text(value: Any) -> str:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("source_timestamp_must_be_finite")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("source_timestamp_must_be_finite")
    result = format(Decimal(str(number)), "f")
    if "." in result:
        result = result.rstrip("0").rstrip(".")
    return "0" if Decimal(result) == 0 else result


class CalibratedWorkforceAurisResolverFactory:
    """Build four nodes only for the calibration's exact final provider moment."""

    def __init__(
        self,
        *,
        _token: object,
        factory_id: str,
        trusted_resolver_ids: Collection[str],
        calibration_report: Mapping[str, Any],
        pair_loader: ProviderEvidenceLoader,
        max_age_s: float,
        clock: Callable[[], float],
    ) -> None:
        if _token is not _FACTORY_TOKEN:
            raise TypeError("use_bind_calibrated_workforce_auris_resolver_factory")
        self.factory_id = _nonblank(factory_id, "factory_id")
        self._trusted_resolver_ids = frozenset(
            _nonblank(value, "trusted_resolver_id") for value in trusted_resolver_ids
        )
        if self.factory_id.casefold() not in {
            value.casefold() for value in self._trusted_resolver_ids
        }:
            raise ValueError("allowlisted_auris_node_resolver_factory_required")
        if not callable(pair_loader) or not callable(clock):
            raise TypeError("resolver_factory_runtime_callable_required")
        self._pair_loader = pair_loader
        self._max_age_s = _positive_finite(max_age_s, "max_age_s")
        self._clock = clock
        validated = validate_workforce_auris_calibration_report(
            calibration_report,
            now=float(clock()),
            max_age_s=self._max_age_s,
        )
        if validated["resolver_id"] != self.factory_id:
            raise ValueError("calibration_resolver_factory_identity_mismatch")
        self._calibration_report = copy.deepcopy(validated)

    def build_auris_node_resolver(
        self,
        request: CognitionGovernanceRequest,
    ) -> TrustedAurisNodeResolver:
        if not isinstance(request, CognitionGovernanceRequest):
            raise TypeError("cognition_governance_request_required")
        now = float(self._clock())
        report = validate_workforce_auris_calibration_report(
            self._calibration_report,
            now=now,
            max_age_s=self._max_age_s,
        )
        hnc, auris = self._pair_loader(request)
        moment = validate_provider_moment(
            hnc,
            auris,
            now=now,
            max_age_s=self._max_age_s,
        )
        final_round = report["rounds"][-1]
        if (
            final_round["hnc_receipt_id"] != moment.hnc_receipt_id
            or final_round["auris_receipt_id"] != moment.auris_receipt_id
            or final_round["provider_moment_digest"] != moment.provider_moment_digest
            or final_round["source_timestamp"] != moment.source_timestamp
        ):
            raise ValueError("recalibration_required_for_current_provider_moment")
        if (
            request.provider_receipt_ids != moment.provider_receipt_ids
            or request.provider_moment_digest != moment.provider_moment_digest
            or request.provider_source_timestamp
            != _source_timestamp_text(moment.source_timestamp)
        ):
            raise ValueError("request_provider_moment_must_match_calibration")
        resolver = bind_truth_gated_workforce_auris_resolver(
            resolver_id=self.factory_id,
            trusted_resolver_ids=self._trusted_resolver_ids,
            hnc_evidence=hnc,
            auris_evidence=auris,
            seat_agents=report["seat_agents"],
            seat_samples=report["seat_samples"],
            now=now,
            max_age_s=self._max_age_s,
        )
        if not isinstance(resolver, TruthGatedWorkforceAurisNodeResolver):
            raise AssertionError("truth_gated_workforce_resolver_required")
        return resolver


def bind_calibrated_workforce_auris_resolver_factory(
    *,
    factory_id: str,
    trusted_resolver_ids: Collection[str],
    calibration_report: Mapping[str, Any],
    pair_loader: ProviderEvidenceLoader = load_local_request_provider_evidence,
    max_age_s: float = DEFAULT_MAX_AGE_S,
    clock: Callable[[], float] = time.time,
) -> CalibratedWorkforceAurisResolverFactory:
    """Bind a process-owned factory to one complete measured calibration."""

    return CalibratedWorkforceAurisResolverFactory(
        _token=_FACTORY_TOKEN,
        factory_id=factory_id,
        trusted_resolver_ids=trusted_resolver_ids,
        calibration_report=calibration_report,
        pair_loader=pair_loader,
        max_age_s=max_age_s,
        clock=clock,
    )


__all__ = [
    "CalibratedWorkforceAurisResolverFactory",
    "bind_calibrated_workforce_auris_resolver_factory",
]

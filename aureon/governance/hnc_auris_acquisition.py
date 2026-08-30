"""Process-owned acquisition of one exact live HNC/Auris provider moment."""

from __future__ import annotations

import math
import time
from collections.abc import Callable, Collection, Mapping
from decimal import Decimal
from typing import Any

from aureon.governance.live_workforce_calibration import (
    load_latest_active_provider_pair,
)
from aureon.swarm.auris_node_receipts import (
    DEFAULT_MAX_AGE_S,
    validate_provider_moment,
)

ProviderPairLoader = Callable[
    [], tuple[Mapping[str, Any], Mapping[str, Any]]
]
_SUPPLIER_TOKEN = object()


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


def _timestamp_text(value: float) -> str:
    result = format(Decimal(str(value)), "f")
    if "." in result:
        result = result.rstrip("0").rstrip(".")
    return "0" if Decimal(result) == 0 else result


class HncAurisGovernanceAcquisitionSupplier:
    """Return provider lineage only after validating the complete local pair."""

    def __init__(
        self,
        *,
        _token: object,
        supplier_id: str,
        pair_loader: ProviderPairLoader,
        max_age_s: float,
        clock: Callable[[], float],
    ) -> None:
        if _token is not _SUPPLIER_TOKEN:
            raise TypeError("use_bind_hnc_auris_governance_acquisition_supplier")
        self.supplier_id = _nonblank(supplier_id, "acquisition_supplier_id")
        if not callable(pair_loader) or not callable(clock):
            raise TypeError("acquisition_runtime_callable_required")
        self._pair_loader = pair_loader
        self._max_age_s = _positive_finite(max_age_s, "max_age_s")
        self._clock = clock

    def load_governance_acquisition(self) -> Mapping[str, Any]:
        current = self._clock()
        if isinstance(current, bool) or not isinstance(current, (int, float)):
            raise ValueError("finite_acquisition_clock_required")
        now = float(current)
        if not math.isfinite(now):
            raise ValueError("finite_acquisition_clock_required")
        hnc, auris = self._pair_loader()
        moment = validate_provider_moment(
            hnc,
            auris,
            now=now,
            max_age_s=self._max_age_s,
        )
        return {
            "provider_receipt_ids": list(moment.provider_receipt_ids),
            "provider_moment_digest": moment.provider_moment_digest,
            "provider_source_timestamp": _timestamp_text(moment.source_timestamp),
        }


def bind_hnc_auris_governance_acquisition_supplier(
    *,
    supplier_id: str,
    trusted_supplier_ids: Collection[str],
    pair_loader: ProviderPairLoader = load_latest_active_provider_pair,
    max_age_s: float = DEFAULT_MAX_AGE_S,
    clock: Callable[[], float] = time.time,
) -> HncAurisGovernanceAcquisitionSupplier:
    """Bind the request acquisition source without waking a producer."""

    identity = _nonblank(supplier_id, "acquisition_supplier_id")
    allowlist = {
        _nonblank(value, "trusted_acquisition_supplier_id").casefold()
        for value in trusted_supplier_ids
    }
    if identity.casefold() not in allowlist:
        raise ValueError("acquisition_supplier_not_allowlisted")
    return HncAurisGovernanceAcquisitionSupplier(
        _token=_SUPPLIER_TOKEN,
        supplier_id=identity,
        pair_loader=pair_loader,
        max_age_s=max_age_s,
        clock=clock,
    )


__all__ = [
    "HncAurisGovernanceAcquisitionSupplier",
    "ProviderPairLoader",
    "bind_hnc_auris_governance_acquisition_supplier",
]

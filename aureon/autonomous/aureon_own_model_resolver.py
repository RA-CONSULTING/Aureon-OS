"""Evidence-only routing to Aureon's pinned local language model."""

from __future__ import annotations

import hashlib
import json
import math
import time
from typing import Any, Callable

from aureon.inhouse_ai.llm_adapter import LLMAdapter, _aureon_own_adapter
from aureon.inhouse_ai.own_model_config import (
    AUREON_OWN_DEFAULT_MODEL,
    AUREON_OWN_PROVIDER,
    aureon_own_route,
    is_aureon_own_route,
)
from aureon.integrations.ollama.model_switchboard import (
    HNCModelRoutingReceipt,
    OllamaModelSwitchboard,
)

OWN_MODEL_ROUTE_PREFIX = "aureon-own:hnc-route:"


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    ).hexdigest()


class AureonOwnModelBrainResolver:
    """A pinned own-model route; failed probes and absent HNC evidence HOLD."""

    def __init__(
        self,
        *,
        adapter: LLMAdapter | None = None,
        field_reader: Callable[[], Any] | None = None,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self.adapter = adapter or _aureon_own_adapter()
        self.base_url, self.model = aureon_own_route()
        self._field_reader = field_reader
        self._clock = clock
        self._cache: dict[tuple[str, str], Any] = {}

    def self_coder_transport_preflight(self) -> dict[str, Any]:
        ready = is_aureon_own_route(self.base_url, self.model)
        return {
            "schema_version": "aureon-self-coder-transport-preflight-v1",
            "ready": ready,
            "provider_mode": AUREON_OWN_PROVIDER if ready else "hold",
            "endpoint_authority_digest": _digest(self.base_url),
            "endpoint_loopback": ready,
            "external_source_egress_authorized": False,
            "action_eligible": False,
            "economic_eligible": False,
        }

    def resolve(self, lane: str):
        return self.resolve_for(lane, nerve_id=f"lane:{lane}")

    def resolve_for(self, lane: str, *, nerve_id: str):
        from aureon.autonomous.aureon_internal_coding_workforce import ResolvedBrain

        lane = str(lane or "").strip().lower()
        nerve = str(nerve_id or "").strip()
        key = (lane, nerve)
        if key in self._cache:
            return self._cache[key]
        if self._field_reader is None:
            from aureon.core.hnc_field import read_canonical_field

            field = read_canonical_field()
        else:
            field = self._field_reader()
        metrics = tuple(
            getattr(field, name, None)
            for name in ("coherence_gamma", "consciousness_psi", "lambda_t", "source_timestamp")
        )
        valid_field = bool(
            getattr(field, "available", False) is True
            and str(getattr(field, "receipt_id", "") or "").startswith("hnc:live_field:")
            and all(type(value) in {int, float} and math.isfinite(float(value)) for value in metrics)
            and 0.0 <= float(metrics[0]) <= 1.0
        )
        working = bool(
            lane in {"coding", "architecture", "self_evolution", "fast", "general"}
            and nerve
            and is_aureon_own_route(self.base_url, self.model)
            and self.adapter.model == AUREON_OWN_DEFAULT_MODEL
            and self.adapter.health_check()
        )
        ready = bool(working and valid_field)
        now = self._clock()
        gamma = float(metrics[0]) if valid_field else 0.0
        source = "live_probe_passed:hnc_own_model" if ready else "no_data"
        receipt = HNCModelRoutingReceipt(
            schema_version="aureon-own-model-hnc-route-v1",
            decision="ROUTE" if ready else "HOLD",
            reason="own_model_probe_and_hnc_field_validated" if ready else "own_model_or_hnc_field_unavailable",
            nerve_id=nerve,
            lane=lane,
            model=self.model if ready else "",
            provider_mode=AUREON_OWN_PROVIDER if ready else "hold",
            hnc_receipt_id=str(getattr(field, "receipt_id", "")) if ready else "",
            hnc_source_timestamp=float(metrics[3]) if valid_field else None,
            coherence_gamma=gamma if valid_field else None,
            consciousness_psi=float(metrics[1]) if valid_field else None,
            lambda_t=float(metrics[2]) if valid_field else None,
            coherence_band=OllamaModelSwitchboard._coherence_band(gamma) if valid_field else "no_data",
            catalog_digest=_digest(self.base_url),
            catalog_size=1,
            candidate_count=1,
            selected_rank=1 if ready else None,
            selection_source=source,
            issued_at=now,
            action_eligible=False,
            economic_eligible=False,
            receipt_id="",
        )
        route_id = OWN_MODEL_ROUTE_PREFIX + _digest(receipt.to_dict())
        resolved = ResolvedBrain(
            adapter=self.adapter if ready else None,
            lane=lane,
            model=self.model,
            source=source,
            endpoint_reachable=working,
            working=working,
            catalog_size=1,
            catalog_refreshed_at=now,
            endpoint_authority_digest=_digest(self.base_url),
            routing_receipt_id=route_id,
            hnc_receipt_id=receipt.hnc_receipt_id,
            hnc_gamma=receipt.coherence_gamma,
            hnc_coherence_band=receipt.coherence_band,
            provider_mode=receipt.provider_mode,
        )
        self._cache[key] = resolved
        return resolved


__all__ = ["AureonOwnModelBrainResolver", "OWN_MODEL_ROUTE_PREFIX"]

"""A complete HNC live-field envelope the canonical validator accepts.

The receipt id is derived from the same inputs the daemon binds. A static
label such as ``hnc:live_field:test-affect`` is not a measured field.
"""

from __future__ import annotations

import time
from typing import Any

from aureon.core.hnc_field import build_hnc_live_field_receipt_id

# Fixture identity for the lambda-history receipt. Not a credential.
_MEMORY_HASH = "ab" * 32


def live_field_envelope(
    symbolic_life_score: float,
    coherence_gamma: float | None = None,
    consciousness_psi: float | None = None,
    *,
    provider_receipt: str = "test.provider:hnc",
    step: int = 1,
    **extra: Any,
) -> dict[str, Any]:
    received_at = time.time()
    gamma = symbolic_life_score if coherence_gamma is None else coherence_gamma
    psi = gamma if consciousness_psi is None else consciousness_psi
    memory_hash = str(extra.pop("memory_canonical_hash", _MEMORY_HASH))
    memory_receipt = f"hnc:lambda_history:{memory_hash}"
    input_receipt_ids = sorted({memory_receipt, provider_receipt})
    payload: dict[str, Any] = {
        "data_status": "live",
        "source": "hnc_live_daemon",
        "source_id": "aureon:hnc:live_daemon",
        "source_timestamp": received_at,
        "received_at": received_at,
        "ts": received_at,
        "receipt_type": "hnc_live_field",
        "provider_receipt_type": "hnc_live_field",
        "input_receipt_ids": input_receipt_ids,
        "step": step,
        "memory_receipt_id": memory_receipt,
        "memory_canonical_hash": memory_hash,
        "symbolic_life_score": symbolic_life_score,
        "coherence_gamma": gamma,
        "consciousness_psi": psi,
        "consciousness_level": "AWARE",
        "lambda_t": symbolic_life_score,
        "source_count": 1,
        "truth_status": "real_derived",
        "generated_values": False,
        "freshness_status": "fresh",
        "operational_eligible": False,
        "provider_eligible": False,
        "action_eligible": False,
        "actionable": False,
        "accounting_eligible": False,
        "learning_eligible": False,
        "eligible_for_action": False,
        "eligible_for_accounting": False,
        "eligible_for_learning": False,
        "equation_inputs_complete": True,
        "action_gate_passed": False,
        "action_gate_reason": "route_specific_market_link_required",
    }
    payload.update(extra)
    payload["receipt_id"] = build_hnc_live_field_receipt_id(
        input_receipt_ids=tuple(payload["input_receipt_ids"]),
        source_timestamp=payload["source_timestamp"],
        received_at=payload["received_at"],
        step=int(payload["step"]),
        lambda_t=float(payload["lambda_t"]),
        coherence_gamma=float(payload["coherence_gamma"]),
        consciousness_psi=float(payload["consciousness_psi"]),
        symbolic_life_score=float(payload["symbolic_life_score"]),
    )
    return payload

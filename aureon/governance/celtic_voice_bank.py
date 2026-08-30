"""Repository-bound Celtic voice profiles for the Druidic Council.

The wisdom bank supplies language and deliberative context only. It never
supplies Gamma, a seat decision, provider evidence, or permission to act.
Those remain the responsibility of Auris/HNC receipts, the trusted seat
resolver, and the independent Council+Crown dual-key join.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from aureon.governance.druid_voice import (
    DruidSeatIssuerBinding,
    ResolvedDruidSeatVoice,
    TrustedDruidSeatResolver,
)
from aureon.swarm.druidic_council import REQUIRED_SEATS

CELTIC_VOICE_BANK_SCHEMA = "aureon.celtic_voice_bank.v1"
CELTIC_VOICE_BANK_PATH = (
    Path(__file__).resolve().parents[2] / "wisdom_data" / "celtic_wisdom.json"
)
CELTIC_VOICE_BANK_SOURCE = "wisdom_data/celtic_wisdom.json"
SEASONAL_GATE_ORDER = ("samhain", "imbolc", "beltane", "lughnasadh")
SEAT_PRINCIPLES = {
    "seer": "druidic_cycles",
    "sentinel": "otherworld_thresholds",
    "weaver": "ogham_patterns",
    "keeper": "triad_wisdom",
}
TRIAD_CONFIRMING_VOICES = 3

_DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
_FALSE_FLAGS = (
    "action_eligible",
    "accounting_eligible",
    "learning_eligible",
    "action_gate_passed",
    "actionable",
    "operational_eligible",
    "provider_eligible",
    "eligible_for_action",
    "eligible_for_accounting",
    "eligible_for_learning",
    "economic_mutation",
)
_TOPIC_NAMES = (
    "Druidic Cycles",
    "Ogham Patterns",
    "Triad Wisdom",
    "Otherworld Thresholds",
    "Samhain Wisdom",
    "Imbolc Renewal",
    "Beltane Growth",
    "Lughnasadh Harvest",
)
_GATE_STARTS = {
    "imbolc": (2, 1),
    "beltane": (5, 1),
    "lughnasadh": (8, 1),
    "samhain": (10, 31),
}


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def _sha256(value: Any) -> str:
    raw = value if isinstance(value, bytes) else _canonical_json(value).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ValueError(f"canonical_{name}_required")
    return value


def _digest(value: Any, name: str) -> str:
    text = _text(value, name)
    if _DIGEST_RE.fullmatch(text) is None:
        raise ValueError(f"{name}_must_be_sha256")
    return text


def _confidence(value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("finite_principle_confidence_required")
    number = float(value)
    if not math.isfinite(number) or not 0.0 <= number <= 1.0:
        raise ValueError("bounded_principle_confidence_required")
    return number


def _false_flags() -> dict[str, bool]:
    return dict.fromkeys(_FALSE_FLAGS, False)


def _receipt_causal(receipt: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema": receipt["schema"],
        "receipt_type": receipt["receipt_type"],
        "civilization": receipt["civilization"],
        "dataset_source": receipt["dataset_source"],
        "dataset_sha256": receipt["dataset_sha256"],
        "dataset_version": receipt["dataset_version"],
        "dataset_last_updated": receipt["dataset_last_updated"],
        "source_labels": receipt["source_labels"],
        "topic_names": receipt["topic_names"],
        "seat_profiles": receipt["seat_profiles"],
        "triad_logic": receipt["triad_logic"],
        "seasonal_gates": receipt["seasonal_gates"],
        "learned_insight_count": receipt["learned_insight_count"],
        "learned_insights_digest": receipt["learned_insights_digest"],
        "reference_material_status": receipt["reference_material_status"],
        "data_status": receipt["data_status"],
        "truth_status": receipt["truth_status"],
        "generated_values": receipt["generated_values"],
        **_false_flags(),
    }


def _build_receipt(document: Mapping[str, Any], *, source_bytes: bytes) -> dict[str, Any]:
    if document.get("civilization") != "Celtic":
        raise ValueError("celtic_wisdom_document_required")
    version = _text(document.get("version"), "dataset_version")
    last_updated = _text(document.get("last_updated"), "dataset_last_updated")
    sources = document.get("sources")
    if (
        not isinstance(sources, list)
        or not sources
        or any(not isinstance(item, str) or not item.strip() for item in sources)
        or len(set(sources)) != len(sources)
    ):
        raise ValueError("distinct_celtic_source_labels_required")

    topics = document.get("topics")
    if not isinstance(topics, list) or tuple(item.get("name") for item in topics) != _TOPIC_NAMES:
        raise ValueError("exact_celtic_topic_bank_required")

    principles = document.get("core_principles")
    if not isinstance(principles, Mapping) or set(principles) != set(SEAT_PRINCIPLES.values()):
        raise ValueError("exact_celtic_core_principles_required")
    profiles = []
    for seat in REQUIRED_SEATS:
        key = SEAT_PRINCIPLES[seat]
        raw = principles[key]
        if not isinstance(raw, Mapping) or set(raw) != {
            "description",
            "trading_application",
            "confidence",
        }:
            raise ValueError("exact_celtic_principle_schema_required")
        profiles.append(
            {
                "seat": seat,
                "principle": key,
                "description": _text(raw["description"], "principle_description"),
                "application_context": _text(
                    raw["trading_application"],
                    "principle_application",
                ),
                "confidence": _confidence(raw["confidence"]),
            }
        )

    seasonal = document.get("seasonal_wisdom")
    if not isinstance(seasonal, Mapping) or set(seasonal) != set(SEASONAL_GATE_ORDER):
        raise ValueError("exact_four_celtic_seasonal_gates_required")
    gates = []
    for gate in SEASONAL_GATE_ORDER:
        raw = seasonal[gate]
        if not isinstance(raw, Mapping) or set(raw) != {
            "period",
            "meaning",
            "market_insight",
        }:
            raise ValueError("exact_celtic_seasonal_gate_schema_required")
        gates.append(
            {
                "gate": gate,
                "period": _text(raw["period"], "seasonal_period"),
                "meaning": _text(raw["meaning"], "seasonal_meaning"),
                "application_context": _text(
                    raw["market_insight"],
                    "seasonal_application",
                ),
            }
        )

    learned = document.get("learned_insights")
    if not isinstance(learned, list):
        raise ValueError("celtic_learned_insight_list_required")
    triad = principles["triad_wisdom"]
    causal = {
        "schema": CELTIC_VOICE_BANK_SCHEMA,
        "receipt_type": "celtic_council_voice_bank",
        "civilization": "Celtic",
        "dataset_source": CELTIC_VOICE_BANK_SOURCE,
        "dataset_sha256": _sha256(source_bytes),
        "dataset_version": version,
        "dataset_last_updated": last_updated,
        "source_labels": list(sources),
        "topic_names": list(_TOPIC_NAMES),
        "seat_profiles": profiles,
        "triad_logic": {
            "principle": "triad_wisdom",
            "description": triad["description"],
            "application_context": triad["trading_application"],
            "required_confirming_voices": TRIAD_CONFIRMING_VOICES,
        },
        "seasonal_gates": gates,
        "learned_insight_count": len(learned),
        "learned_insights_digest": _sha256(learned),
        "reference_material_status": "mixed_repository_reference_only",
        "data_status": "repository_snapshot",
        "truth_status": "source_bound_context",
        "generated_values": False,
        **_false_flags(),
    }
    receipt = dict(causal)
    receipt["receipt_id"] = f"celtic:voice_bank:{_sha256(causal)}"
    return receipt


def read_canonical_celtic_voice_bank() -> dict[str, Any]:
    """Read and bind the one canonical repository Celtic voice bank."""

    source = CELTIC_VOICE_BANK_PATH.read_bytes()
    document = json.loads(source.decode("utf-8"))
    if not isinstance(document, Mapping):
        raise ValueError("celtic_wisdom_mapping_required")
    return validate_celtic_voice_bank_receipt(
        _build_receipt(document, source_bytes=source)
    )


def validate_celtic_voice_bank_receipt(receipt: Mapping[str, Any]) -> dict[str, Any]:
    """Validate exact schema, canonical data binding, and non-authority flags."""

    if not isinstance(receipt, Mapping):
        raise ValueError("celtic_voice_bank_receipt_required")
    if receipt.get("schema") != CELTIC_VOICE_BANK_SCHEMA:
        raise ValueError("celtic_voice_bank_schema_mismatch")
    if receipt.get("receipt_type") != "celtic_council_voice_bank":
        raise ValueError("celtic_voice_bank_receipt_type_mismatch")
    _digest(receipt.get("dataset_sha256"), "dataset_sha256")
    if receipt.get("dataset_source") != CELTIC_VOICE_BANK_SOURCE:
        raise ValueError("canonical_celtic_dataset_source_required")
    if receipt.get("civilization") != "Celtic":
        raise ValueError("celtic_wisdom_document_required")
    if [item.get("seat") for item in receipt.get("seat_profiles", [])] != list(REQUIRED_SEATS):
        raise ValueError("stable_celtic_seat_profiles_required")
    if [item.get("principle") for item in receipt["seat_profiles"]] != [
        SEAT_PRINCIPLES[seat] for seat in REQUIRED_SEATS
    ]:
        raise ValueError("stable_celtic_seat_principles_required")
    if [item.get("gate") for item in receipt.get("seasonal_gates", [])] != list(
        SEASONAL_GATE_ORDER
    ):
        raise ValueError("stable_celtic_seasonal_gate_order_required")
    triad = receipt.get("triad_logic")
    if not isinstance(triad, Mapping) or triad.get("required_confirming_voices") != 3:
        raise ValueError("three_voice_triad_logic_required")
    if receipt.get("data_status") != "repository_snapshot":
        raise ValueError("repository_celtic_voice_bank_required")
    if receipt.get("truth_status") != "source_bound_context":
        raise ValueError("source_bound_celtic_context_required")
    if receipt.get("reference_material_status") != "mixed_repository_reference_only":
        raise ValueError("reference_only_celtic_material_required")
    if receipt.get("generated_values") is not False:
        raise ValueError("generated_celtic_voice_bank_forbidden")
    if any(receipt.get(name) is not False for name in _FALSE_FLAGS):
        raise ValueError("celtic_voice_bank_must_be_non_authoritative")
    _digest(receipt.get("learned_insights_digest"), "learned_insights_digest")
    count = receipt.get("learned_insight_count")
    if isinstance(count, bool) or not isinstance(count, int) or count < 0:
        raise ValueError("valid_learned_insight_count_required")
    causal = _receipt_causal(receipt)
    required = set(causal) | {"receipt_id"}
    if set(receipt) != required:
        raise ValueError("exact_celtic_voice_bank_schema_required")
    if receipt.get("receipt_id") != f"celtic:voice_bank:{_sha256(causal)}":
        raise ValueError("celtic_voice_bank_hash_mismatch")
    return copy.deepcopy(dict(receipt))


def seasonal_gate_for_date(value: date) -> str:
    """Return the most recent declared fire-festival gate for a civil date."""

    if not isinstance(value, date):
        raise ValueError("civil_date_required")
    month_day = (value.month, value.day)
    if month_day >= _GATE_STARTS["samhain"]:
        return "samhain"
    if month_day >= _GATE_STARTS["lughnasadh"]:
        return "lughnasadh"
    if month_day >= _GATE_STARTS["beltane"]:
        return "beltane"
    if month_day >= _GATE_STARTS["imbolc"]:
        return "imbolc"
    return "samhain"


def celtic_seat_context(
    receipt: Mapping[str, Any],
    *,
    seat: str,
    seasonal_gate: str,
) -> dict[str, Any]:
    """Return the hash-bound language context for one stable seat."""

    bank = validate_celtic_voice_bank_receipt(receipt)
    seat_name = _text(seat, "seat").lower()
    gate_name = _text(seasonal_gate, "seasonal_gate").lower()
    if seat_name not in REQUIRED_SEATS:
        raise ValueError("unknown_council_seat")
    if gate_name not in SEASONAL_GATE_ORDER:
        raise ValueError("unknown_celtic_seasonal_gate")
    profile = next(item for item in bank["seat_profiles"] if item["seat"] == seat_name)
    gate = next(item for item in bank["seasonal_gates"] if item["gate"] == gate_name)
    causal = {
        "voice_bank_receipt_id": bank["receipt_id"],
        "seat": seat_name,
        "principle": profile["principle"],
        "principle_description": profile["description"],
        "principle_application_context": profile["application_context"],
        "seasonal_gate": gate_name,
        "seasonal_meaning": gate["meaning"],
        "seasonal_application_context": gate["application_context"],
        "triad_required_confirming_voices": TRIAD_CONFIRMING_VOICES,
    }
    return {**causal, "context_digest": _sha256(causal)}


@dataclass(frozen=True)
class CelticSeatedDruidResolver:
    """Wrap a trusted resolver without changing its decision or evidence."""

    delegate: TrustedDruidSeatResolver
    voice_bank_receipt: Mapping[str, Any]
    seasonal_gate: str

    def _bank(self) -> dict[str, Any]:
        bank = validate_celtic_voice_bank_receipt(self.voice_bank_receipt)
        canonical = read_canonical_celtic_voice_bank()
        if (
            bank["receipt_id"] != canonical["receipt_id"]
            or bank["dataset_sha256"] != canonical["dataset_sha256"]
        ):
            raise ValueError("canonical_repository_celtic_voice_bank_required")
        return bank

    def _gate(self) -> str:
        gate = _text(self.seasonal_gate, "seasonal_gate").lower()
        if gate not in SEASONAL_GATE_ORDER:
            raise ValueError("unknown_celtic_seasonal_gate")
        return gate

    def _delegate_bindings(self) -> Mapping[str, DruidSeatIssuerBinding]:
        raw = self.delegate.trusted_druid_seat_bindings()
        if not isinstance(raw, Mapping) or set(raw) != set(REQUIRED_SEATS):
            raise ValueError("exact_delegate_druid_bindings_required")
        if any(not isinstance(raw[seat], DruidSeatIssuerBinding) for seat in REQUIRED_SEATS):
            raise ValueError("typed_delegate_druid_bindings_required")
        return raw

    def trusted_druid_seat_bindings(self) -> Mapping[str, DruidSeatIssuerBinding]:
        bank = self._bank()
        gate = self._gate()
        bindings = self._delegate_bindings()
        seated = {}
        for seat in REQUIRED_SEATS:
            original = bindings[seat]
            context = celtic_seat_context(bank, seat=seat, seasonal_gate=gate)
            seated_source = {
                "delegate_decision_source_id": original.decision_source_id,
                "celtic_context_digest": context["context_digest"],
            }
            seated[seat] = DruidSeatIssuerBinding(
                resolver_id=original.resolver_id,
                issuer_id=original.issuer_id,
                decision_source_id=f"celtic:seat_source:{_sha256(seated_source)}",
                seat=original.seat,
                agent_id=original.agent_id,
            )
        return seated

    def resolve_druid_seat_voice(
        self,
        seat: str,
        proposal_digest: str,
        prompt_digest: str,
    ) -> ResolvedDruidSeatVoice | None:
        seat_name = _text(seat, "seat").lower()
        if seat_name not in REQUIRED_SEATS:
            raise ValueError("unknown_council_seat")
        original_binding = self._delegate_bindings()[seat_name]
        resolved = self.delegate.resolve_druid_seat_voice(
            seat_name,
            proposal_digest,
            prompt_digest,
        )
        if resolved is None:
            return None
        if not isinstance(resolved, ResolvedDruidSeatVoice):
            raise ValueError("typed_delegate_druid_voice_required")
        if (
            resolved.resolver_id,
            resolved.issuer_id,
            resolved.decision_source_id,
            resolved.seat,
            resolved.agent_id,
        ) != (
            original_binding.resolver_id,
            original_binding.issuer_id,
            original_binding.decision_source_id,
            original_binding.seat,
            original_binding.agent_id,
        ):
            raise ValueError("delegate_druid_voice_binding_mismatch")
        bank = self._bank()
        gate = self._gate()
        context = celtic_seat_context(bank, seat=seat_name, seasonal_gate=gate)
        seated_binding = self.trusted_druid_seat_bindings()[seat_name]
        return ResolvedDruidSeatVoice(
            resolver_id=resolved.resolver_id,
            issuer_id=resolved.issuer_id,
            decision_source_id=seated_binding.decision_source_id,
            seat=resolved.seat,
            agent_id=resolved.agent_id,
            decision=resolved.decision,
            reason=(
                f"celtic_voice[{seat_name}:{context['principle']}:{gate}]: "
                f"{resolved.reason}"
            ),
            proposal_digest=resolved.proposal_digest,
            prompt_digest=resolved.prompt_digest,
            auris_node_receipt_id=resolved.auris_node_receipt_id,
            hnc_receipt_id=resolved.hnc_receipt_id,
            auris_receipt_id=resolved.auris_receipt_id,
            provider_receipt_ids=resolved.provider_receipt_ids,
            provider_moment_digest=resolved.provider_moment_digest,
            source_timestamp=resolved.source_timestamp,
        )


__all__ = [
    "CELTIC_VOICE_BANK_PATH",
    "CELTIC_VOICE_BANK_SCHEMA",
    "CelticSeatedDruidResolver",
    "SEASONAL_GATE_ORDER",
    "SEAT_PRINCIPLES",
    "TRIAD_CONFIRMING_VOICES",
    "celtic_seat_context",
    "read_canonical_celtic_voice_bank",
    "seasonal_gate_for_date",
    "validate_celtic_voice_bank_receipt",
]

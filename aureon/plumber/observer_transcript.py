"""Canonical HNC observer transcript commitments for Plumber v0.

Observer values are authenticated public context.  This module never treats
them as encryption keys, key shares, or sources of cryptographic entropy.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Self

from .crypto import domain_hash
from .schema import (
    DenialCode,
    SchemaError,
    freeze_mapping,
    require_exact_keys,
    require_fixed_decimal,
    require_nonblank,
    require_sha256,
)

OBSERVER_TRANSCRIPT_SCHEMA = "aureon.plumber.observer-transcript.v0"
_FIELDS = (
    "schema",
    "packet_identity",
    "session_identity",
    "purpose_commitment",
    "challenge_commitment",
    "canonical_hnc_values",
    "trajectory_commitments",
    "coherence",
    "consciousness_proxy",
    "symbolic_life",
    "hnc_parameters",
    "rock_commitments",
    "active_mode",
    "active_plateau",
    "transition_commitment",
    "regime",
    "divergence_score",
    "source_receipt_commitments",
    "transcript_commitment",
)


def _numbers(value: Mapping[str, Any], *, field: str) -> dict[str, str]:
    if not isinstance(value, Mapping) or not value:
        raise SchemaError(DenialCode.INVALID_TYPE, field=field)
    parsed: dict[str, str] = {}
    for key, item in value.items():
        require_nonblank(key, field=f"{field}.key")
        parsed[key] = require_fixed_decimal(item, field=f"{field}.{key}")
    return parsed


def _commitments(value: Sequence[Any], *, field: str, nonempty: bool = True) -> tuple[str, ...]:
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        raise SchemaError(DenialCode.INVALID_TYPE, field=field)
    result = tuple(value)
    if nonempty and not result:
        raise SchemaError(DenialCode.INVALID_VALUE, field=field)
    for item in result:
        require_sha256(item, field=field)
    return result


@dataclass(frozen=True, slots=True)
class ObserverTranscriptV0:
    schema: str
    packet_identity: str
    session_identity: str
    purpose_commitment: str
    challenge_commitment: str
    canonical_hnc_values: Mapping[str, str]
    trajectory_commitments: tuple[str, ...]
    coherence: str
    consciousness_proxy: str | None
    symbolic_life: bool
    hnc_parameters: Mapping[str, str]
    rock_commitments: tuple[str, ...]
    active_mode: str
    active_plateau: str
    transition_commitment: str
    regime: str
    divergence_score: str
    source_receipt_commitments: tuple[str, ...]
    transcript_commitment: str

    def __post_init__(self) -> None:
        if self.schema != OBSERVER_TRANSCRIPT_SCHEMA:
            raise SchemaError(DenialCode.INVALID_SCHEMA, field="schema")
        for field in ("packet_identity", "session_identity", "active_mode", "active_plateau", "regime"):
            require_nonblank(getattr(self, field), field=field)
        for field in ("purpose_commitment", "challenge_commitment", "transition_commitment", "transcript_commitment"):
            require_sha256(getattr(self, field), field=field)
        _numbers(self.canonical_hnc_values, field="canonical_hnc_values")
        _numbers(self.hnc_parameters, field="hnc_parameters")
        object.__setattr__(
            self,
            "canonical_hnc_values",
            freeze_mapping(self.canonical_hnc_values, field="canonical_hnc_values"),
        )
        object.__setattr__(
            self,
            "hnc_parameters",
            freeze_mapping(self.hnc_parameters, field="hnc_parameters"),
        )
        object.__setattr__(
            self,
            "trajectory_commitments",
            _commitments(self.trajectory_commitments, field="trajectory_commitments"),
        )
        object.__setattr__(
            self,
            "rock_commitments",
            _commitments(self.rock_commitments, field="rock_commitments", nonempty=False),
        )
        object.__setattr__(
            self,
            "source_receipt_commitments",
            _commitments(self.source_receipt_commitments, field="source_receipt_commitments"),
        )
        require_fixed_decimal(self.coherence, field="coherence")
        require_fixed_decimal(self.divergence_score, field="divergence_score")
        if self.consciousness_proxy is not None:
            require_fixed_decimal(self.consciousness_proxy, field="consciousness_proxy")
        if type(self.symbolic_life) is not bool:
            raise SchemaError(DenialCode.INVALID_TYPE, field="symbolic_life")
        if domain_hash("aureon.plumber.observer-transcript.v0", self.commitment_payload()) != self.transcript_commitment:
            raise SchemaError(DenialCode.OBSERVER_TRANSCRIPT_MISMATCH, field="transcript_commitment")

    @classmethod
    def build(
        cls,
        *,
        packet_identity: str,
        session_identity: str,
        purpose_commitment: str,
        challenge_commitment: str,
        canonical_hnc_values: Mapping[str, int | str],
        trajectory_commitments: Sequence[str],
        coherence: int | str,
        consciousness_proxy: int | str | None,
        symbolic_life: bool,
        hnc_parameters: Mapping[str, int | str],
        rock_commitments: Sequence[str],
        active_mode: str,
        active_plateau: str,
        transition_commitment: str,
        regime: str,
        divergence_score: int | str,
        source_receipt_commitments: Sequence[str],
    ) -> Self:
        values: dict[str, Any] = {
            "schema": OBSERVER_TRANSCRIPT_SCHEMA,
            "packet_identity": packet_identity,
            "session_identity": session_identity,
            "purpose_commitment": purpose_commitment,
            "challenge_commitment": challenge_commitment,
            "canonical_hnc_values": _numbers(canonical_hnc_values, field="canonical_hnc_values"),
            "trajectory_commitments": _commitments(trajectory_commitments, field="trajectory_commitments"),
            "coherence": require_fixed_decimal(coherence, field="coherence"),
            "consciousness_proxy": (
                None
                if consciousness_proxy is None
                else require_fixed_decimal(consciousness_proxy, field="consciousness_proxy")
            ),
            "symbolic_life": symbolic_life,
            "hnc_parameters": _numbers(hnc_parameters, field="hnc_parameters"),
            "rock_commitments": _commitments(rock_commitments, field="rock_commitments", nonempty=False),
            "active_mode": active_mode,
            "active_plateau": active_plateau,
            "transition_commitment": transition_commitment,
            "regime": regime,
            "divergence_score": require_fixed_decimal(divergence_score, field="divergence_score"),
            "source_receipt_commitments": _commitments(
                source_receipt_commitments,
                field="source_receipt_commitments",
            ),
        }
        return cls(
            **values,
            transcript_commitment=domain_hash("aureon.plumber.observer-transcript.v0", values),
        )

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> Self:
        parsed = require_exact_keys(value, _FIELDS, field="observer_transcript")
        parsed["canonical_hnc_values"] = _numbers(parsed["canonical_hnc_values"], field="canonical_hnc_values")
        parsed["hnc_parameters"] = _numbers(parsed["hnc_parameters"], field="hnc_parameters")
        for field, nonempty in (
            ("trajectory_commitments", True),
            ("rock_commitments", False),
            ("source_receipt_commitments", True),
        ):
            parsed[field] = _commitments(parsed[field], field=field, nonempty=nonempty)
        return cls(**parsed)

    def commitment_payload(self) -> dict[str, Any]:
        return {
            field: getattr(self, field)
            for field in _FIELDS
            if field != "transcript_commitment"
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            **self.commitment_payload(),
            "trajectory_commitments": list(self.trajectory_commitments),
            "rock_commitments": list(self.rock_commitments),
            "source_receipt_commitments": list(self.source_receipt_commitments),
            "transcript_commitment": self.transcript_commitment,
        }

    def public_summary(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "packet_identity": self.packet_identity,
            "session_identity": self.session_identity,
            "purpose_commitment": self.purpose_commitment,
            "challenge_commitment": self.challenge_commitment,
            "hnc_values_commitment": domain_hash("aureon.plumber.hnc-values.v0", self.canonical_hnc_values),
            "trajectory_count": len(self.trajectory_commitments),
            "rock_count": len(self.rock_commitments),
            "source_receipt_count": len(self.source_receipt_commitments),
            "transcript_commitment": self.transcript_commitment,
        }


def build_observer_transcript(**values: Any) -> ObserverTranscriptV0:
    return ObserverTranscriptV0.build(**values)


__all__ = ["OBSERVER_TRANSCRIPT_SCHEMA", "ObserverTranscriptV0", "build_observer_transcript"]

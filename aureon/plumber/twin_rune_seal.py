"""Twin-rune binding across source, observer, time, purpose, and challenge."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Self

from .crypto import domain_hash
from .schema import DenialCode, SchemaError, require_exact_keys, require_sha256

TWIN_RUNE_SCHEMA = "aureon.plumber.twin-rune-seal.v0"
_FIELDS = (
    "schema",
    "source_identity_commitment",
    "observer_transcript_commitment",
    "temporal_identity_commitment",
    "purpose_commitment",
    "challenge_commitment",
    "source_rune",
    "observer_rune",
    "seal_commitment",
)


def _computed_runes(values: Mapping[str, str]) -> tuple[str, str, str]:
    source_rune = domain_hash(
        "aureon.plumber.source-rune.v0",
        {key: values[key] for key in (
            "source_identity_commitment",
            "temporal_identity_commitment",
            "purpose_commitment",
            "challenge_commitment",
        )},
    )
    observer_rune = domain_hash(
        "aureon.plumber.observer-rune.v0",
        {key: values[key] for key in (
            "observer_transcript_commitment",
            "temporal_identity_commitment",
            "purpose_commitment",
            "challenge_commitment",
        )},
    )
    joined = {
        "schema": TWIN_RUNE_SCHEMA,
        "source_identity_commitment": values["source_identity_commitment"],
        "observer_transcript_commitment": values["observer_transcript_commitment"],
        "temporal_identity_commitment": values["temporal_identity_commitment"],
        "purpose_commitment": values["purpose_commitment"],
        "challenge_commitment": values["challenge_commitment"],
        "source_rune": source_rune,
        "observer_rune": observer_rune,
    }
    seal = domain_hash("aureon.plumber.twin-rune-seal.v0", joined)
    return source_rune, observer_rune, seal


@dataclass(frozen=True, slots=True)
class TwinRuneSealV0:
    schema: str
    source_identity_commitment: str
    observer_transcript_commitment: str
    temporal_identity_commitment: str
    purpose_commitment: str
    challenge_commitment: str
    source_rune: str
    observer_rune: str
    seal_commitment: str

    def __post_init__(self) -> None:
        if self.schema != TWIN_RUNE_SCHEMA:
            raise SchemaError(DenialCode.INVALID_SCHEMA, field="schema")
        for field in _FIELDS[1:]:
            require_sha256(getattr(self, field), field=field)
        source_rune, observer_rune, seal = self._computed()
        if (source_rune, observer_rune, seal) != (
            self.source_rune,
            self.observer_rune,
            self.seal_commitment,
        ):
            raise SchemaError(DenialCode.TWIN_RUNE_MISMATCH, field="seal_commitment")

    @classmethod
    def build(
        cls,
        *,
        source_identity_commitment: str,
        observer_transcript_commitment: str,
        temporal_identity_commitment: str,
        purpose_commitment: str,
        challenge_commitment: str,
    ) -> Self:
        base = {
            "schema": TWIN_RUNE_SCHEMA,
            "source_identity_commitment": source_identity_commitment,
            "observer_transcript_commitment": observer_transcript_commitment,
            "temporal_identity_commitment": temporal_identity_commitment,
            "purpose_commitment": purpose_commitment,
            "challenge_commitment": challenge_commitment,
        }
        source_rune, observer_rune, _seal = _computed_runes(base)
        joined = {**base, "source_rune": source_rune, "observer_rune": observer_rune}
        return cls(
            **joined,
            seal_commitment=domain_hash("aureon.plumber.twin-rune-seal.v0", joined),
        )

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> Self:
        return cls(**require_exact_keys(value, _FIELDS, field="twin_rune_seal"))

    def _computed(self) -> tuple[str, str, str]:
        return _computed_runes(self.to_dict())

    def to_dict(self) -> dict[str, str]:
        return {field: getattr(self, field) for field in _FIELDS}

    def public_summary(self) -> dict[str, str]:
        return self.to_dict()


def build_twin_rune_seal(**values: Any) -> TwinRuneSealV0:
    return TwinRuneSealV0.build(**values)


__all__ = ["TWIN_RUNE_SCHEMA", "TwinRuneSealV0", "build_twin_rune_seal"]

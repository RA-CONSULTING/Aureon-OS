"""Synthetic, offline-only tamper lab for the Plumber/HNC boundary.

The lab accepts no caller packet, key, path, endpoint, or production target.
It creates one disposable in-memory fixture and suppresses decoder details,
plaintext, ciphertext, and key material from its report.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from .crypto import domain_hash
from .schema import DenialCode, SchemaError, require_sha256

SYNTHETIC_BREAKER_SCOPE = "synthetic_offline_only"
_CASE_RE = re.compile(r"^[a-z][a-z0-9_]{0,63}$")


@dataclass(frozen=True, slots=True)
class SyntheticBreakerCase:
    name: str
    tamper_rejected: bool
    result_code: str

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or _CASE_RE.fullmatch(self.name) is None:
            raise SchemaError(DenialCode.INVALID_VALUE, field="case.name")
        if type(self.tamper_rejected) is not bool:
            raise SchemaError(DenialCode.INVALID_TYPE, field="case.tamper_rejected")
        if self.result_code not in {"rejected", "unexpected_accept", "lab_failure"}:
            raise SchemaError(DenialCode.INVALID_VALUE, field="case.result_code")
        if self.tamper_rejected != (self.result_code == "rejected"):
            raise SchemaError(DenialCode.INVALID_VALUE, field="case.result_code")

    def public_summary(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "tamper_rejected": self.tamper_rejected,
            "result_code": self.result_code,
        }


@dataclass(frozen=True, slots=True)
class SyntheticBreakerReport:
    lab_scope: str
    synthetic_packet_commitment: str
    cases: tuple[SyntheticBreakerCase, ...]
    all_tamper_rejected: bool
    plaintext_exposed: bool
    production_validation: bool
    report_commitment: str

    def __post_init__(self) -> None:
        if self.lab_scope != SYNTHETIC_BREAKER_SCOPE:
            raise SchemaError(DenialCode.INVALID_VALUE, field="lab_scope")
        require_sha256(self.synthetic_packet_commitment, field="synthetic_packet_commitment")
        if not self.cases or any(not isinstance(case, SyntheticBreakerCase) for case in self.cases):
            raise SchemaError(DenialCode.INVALID_TYPE, field="cases")
        names = tuple(case.name for case in self.cases)
        if tuple(sorted(set(names))) != names:
            raise SchemaError(DenialCode.INVALID_VALUE, field="cases")
        if self.all_tamper_rejected != all(case.tamper_rejected for case in self.cases):
            raise SchemaError(DenialCode.INVALID_VALUE, field="all_tamper_rejected")
        if self.plaintext_exposed is not False or self.production_validation is not False:
            raise SchemaError(DenialCode.INVALID_VALUE, field="lab_scope")
        require_sha256(self.report_commitment, field="report_commitment")
        if domain_hash("aureon.plumber.synthetic-breaker-report.v0", self.commitment_payload()) != (
            self.report_commitment
        ):
            raise SchemaError(DenialCode.INVALID_VALUE, field="report_commitment")

    def commitment_payload(self) -> dict[str, Any]:
        return {
            "lab_scope": self.lab_scope,
            "synthetic_packet_commitment": self.synthetic_packet_commitment,
            "cases": [case.public_summary() for case in self.cases],
            "all_tamper_rejected": self.all_tamper_rejected,
            "plaintext_exposed": self.plaintext_exposed,
            "production_validation": self.production_validation,
        }

    def public_summary(self) -> dict[str, Any]:
        return {**self.commitment_payload(), "report_commitment": self.report_commitment}


def run_synthetic_offline_breaker_lab() -> SyntheticBreakerReport:
    """Run the existing HNC tamper checks against a fixed synthetic fixture."""

    from aureon.harmonic.hnc_quantum_packet_crypto import (
        build_hnc_quantum_packet,
        run_hnc_packet_breaker_checks,
    )

    synthetic_key = b"aureon-plumber-synthetic-key-32b"
    synthetic_packet = build_hnc_quantum_packet(
        b"synthetic-offline-breaker-fixture",
        synthetic_key,
        purpose="aureon.plumber.synthetic-breaker",
        nonce=b"breaker-lab!",
    )
    raw_report = run_hnc_packet_breaker_checks(synthetic_packet, synthetic_key)
    raw_cases = raw_report.get("checks")
    if not isinstance(raw_cases, list):
        raw_cases = []
    cases: list[SyntheticBreakerCase] = []
    for item in raw_cases:
        if not isinstance(item, dict):
            continue
        name = item.get("name")
        if not isinstance(name, str) or _CASE_RE.fullmatch(name) is None:
            continue
        passed = item.get("passed") is True
        cases.append(
            SyntheticBreakerCase(
                name=name,
                tamper_rejected=passed,
                result_code="rejected" if passed else "unexpected_accept",
            )
        )
    if not cases:
        cases = [
            SyntheticBreakerCase(
                name="lab_setup",
                tamper_rejected=False,
                result_code="lab_failure",
            )
        ]
    ordered = tuple(sorted(cases, key=lambda item: item.name))
    packet_commitment = require_sha256(
        synthetic_packet.get("packet_sha256"),
        field="synthetic_packet_commitment",
    )
    all_tamper_rejected = all(case.tamper_rejected for case in ordered)
    values = {
        "lab_scope": SYNTHETIC_BREAKER_SCOPE,
        "synthetic_packet_commitment": packet_commitment,
        "cases": [case.public_summary() for case in ordered],
        "all_tamper_rejected": all_tamper_rejected,
        "plaintext_exposed": False,
        "production_validation": False,
    }
    return SyntheticBreakerReport(
        lab_scope=SYNTHETIC_BREAKER_SCOPE,
        synthetic_packet_commitment=packet_commitment,
        cases=ordered,
        all_tamper_rejected=all_tamper_rejected,
        plaintext_exposed=False,
        production_validation=False,
        report_commitment=domain_hash("aureon.plumber.synthetic-breaker-report.v0", values),
    )


__all__ = [
    "SYNTHETIC_BREAKER_SCOPE",
    "SyntheticBreakerCase",
    "SyntheticBreakerReport",
    "run_synthetic_offline_breaker_lab",
]

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto

import pytest

from aureon.governance.cognition_gate import (
    TrustedCrownReceiptSupplier,
    build_cognition_governance_request,
)
from aureon.governance.crown_voice import validate_crown_voice_receipt
from aureon.governance.queen_crown_supplier import QueenConscienceCrownSupplier
from tests.test_auris_node_receipts import NOW, _auris, _hnc


class _Verdict(Enum):
    APPROVED = auto()
    VETO = auto()


@dataclass
class _Whisper:
    verdict: _Verdict
    message: str


class _Conscience:
    def __init__(self, verdict=_Verdict.APPROVED):
        self.verdict = verdict
        self.calls = []

    def ask_why(self, action, context=None):
        self.calls.append((action, context))
        return _Whisper(self.verdict, "exact proposal evaluated")


def _fixture():
    hnc = _hnc()
    auris = _auris(hnc)
    from aureon.swarm.auris_node_receipts import validate_provider_moment

    moment = validate_provider_moment(hnc, auris, now=NOW)
    request = build_cognition_governance_request(
        prompt="Should this bounded trade execute?",
        answer="bounded intent",
        acquisition={
            "provider_receipt_ids": list(moment.provider_receipt_ids),
            "provider_moment_digest": moment.provider_moment_digest,
            "provider_source_timestamp": format(moment.source_timestamp, ".0f"),
        },
        queen_verdict="APPROVED",
    )
    return request, hnc, auris


def test_queen_evaluates_full_proposal_and_issues_strict_crown():
    request, hnc, auris = _fixture()
    queen = _Conscience()
    supplier = QueenConscienceCrownSupplier(
        conscience=queen,
        evidence_loader=lambda _request: (hnc, auris),
        clock=lambda: NOW,
    )
    assert isinstance(supplier, TrustedCrownReceiptSupplier)
    receipt = supplier.supply_crown_receipt(request)
    assert validate_crown_voice_receipt(receipt, now=NOW)["decision"] == "APPROVE"
    assert request.proposal_digest in queen.calls[0][0]
    assert queen.calls[0][1]["proposal"]["answer"] == "bounded intent"


def test_queen_veto_is_preserved_as_abort():
    request, hnc, auris = _fixture()
    supplier = QueenConscienceCrownSupplier(
        conscience=_Conscience(_Verdict.VETO),
        evidence_loader=lambda _request: (hnc, auris),
        clock=lambda: NOW,
    )
    assert supplier.supply_crown_receipt(request)["decision"] == "ABORT"


def test_wrong_shared_provider_moment_fails_closed():
    _, hnc, auris = _fixture()
    request = build_cognition_governance_request(
        prompt="Should this bounded trade execute?",
        answer="bounded intent",
        acquisition={
            "provider_receipt_ids": ["provider:wrong:receipt"],
            "provider_moment_digest": "f" * 64,
            "provider_source_timestamp": format(NOW - 1.0, ".0f"),
        },
        queen_verdict="APPROVED",
    )
    supplier = QueenConscienceCrownSupplier(
        conscience=_Conscience(),
        evidence_loader=lambda _request: (hnc, auris),
        clock=lambda: NOW,
    )
    with pytest.raises(ValueError, match="provider_moment_mismatch"):
        supplier.supply_crown_receipt(request)

"""
Dr. Auris Throne in the agent seat — validated code or honest silence.

Pins: the chart is the law (only chart codes pass parsing, 9999 and invented
codes are refused); a dark model returns None with a NAMED blocker (never a
guessed code); a live stubbed model drives the full categorization march and
the consultation record measures every ask; offline/audit mode keeps the
real Ollama adapter honestly dark in this container.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from aureon.accounting.categorize import recategorize_suspense
from aureon.accounting.client_ledger import ClientLedger
from aureon.accounting.file_drop import ingest_file
from aureon.accounting.throne_agent import ThroneCategorizer


@pytest.fixture(autouse=True)
def _dark_field(monkeypatch, tmp_path):
    monkeypatch.setenv("AUREON_HNC_TRACE_PATH", str(tmp_path / "hnc.jsonl"))


@dataclass
class _StubResponse:
    text: str
    stop_reason: str = "end_turn"


@dataclass
class _StubAdapter:
    """A model in a box: scripted answers, measured prompts."""

    answers: list = field(default_factory=list)
    prompts_seen: list = field(default_factory=list)
    live: bool = True

    def health_check(self) -> bool:
        return self.live

    def prompt(self, messages, system="", **kwargs) -> _StubResponse:
        self.prompts_seen.append({"messages": messages, "system": system})
        if not self.answers:
            return _StubResponse(text="UNDECIDED")
        return _StubResponse(text=str(self.answers.pop(0)))


def test_parse_accepts_only_the_chart():
    throne = ThroneCategorizer(adapter=_StubAdapter(live=True))
    assert throne._parse_code("7000") == "7000"
    assert throne._parse_code("The code is 7100.") == "7100"
    assert throne._parse_code("UNDECIDED") is None
    assert throne._parse_code("8888") is None          # not on the chart
    assert throne._parse_code("9999") is None          # suspense is not a destination
    assert throne._parse_code("") is None
    assert throne._parse_code("maybe rent?") is None


def test_dark_model_is_reported_dark_never_guessed():
    throne = ThroneCategorizer(adapter=_StubAdapter(live=False))
    assert throne.decide("Office rent January", -85_000) is None
    status = throne.status()
    assert status["model_live"] is False
    assert any("agent seat empty" in b for b in status["blockers"])
    assert status["consultations"] == []  # a dark model is never consulted


def test_live_stub_drives_the_full_categorization_march(tmp_path):
    f = tmp_path / "statement.csv"
    f.write_text("date,description,amount\n"
                 "2026-02-02,Client payment ACME,1500.00\n"
                 "2026-02-03,Mystery subscription,-25.00\n", encoding="utf-8")
    led = ClientLedger("ra-consulting")
    ingest_file("bank_csv", f, led)

    stub = _StubAdapter(answers=["4000", "7500"], live=True)
    throne = ThroneCategorizer(adapter=stub)
    out = recategorize_suspense(led, [], decide=throne.decide)

    assert out["moved"] == 2 and out["suspense_pennies_remaining"] == 0
    assert led.trial_balance()["balanced"] is True
    assert led.balance_pennies("4000") == 150_000
    assert led.balance_pennies("7500") == 2_500
    # every ask measured: prompt carried the chart and the Throne system seat
    assert len(throne.consultations) == 2
    assert all(c["usable"] for c in throne.consultations)
    assert all("Dr. Auris Throne" in p["system"] for p in stub.prompts_seen)
    assert all("Nominal chart" in p["messages"][0]["content"] for p in stub.prompts_seen)


def test_hallucinated_code_refused_twice(tmp_path):
    f = tmp_path / "s.csv"
    f.write_text("date,description,amount\n2026-02-04,Oddity,10.00\n", encoding="utf-8")
    led = ClientLedger("acme-ltd")
    ingest_file("bank_csv", f, led)

    throne = ThroneCategorizer(adapter=_StubAdapter(answers=["8888"], live=True))
    out = recategorize_suspense(led, [], decide=throne.decide)
    # the throne's own parser already refused it → undecided, stays in suspense
    assert out["moved"] == 0 and out["still_in_suspense"] == 1 and out["refused"] == 0
    assert led.suspense_pennies() != 0
    assert throne.consultations[0]["usable"] is False


def test_real_adapter_is_honestly_dark_in_offline_container(monkeypatch):
    # Cloud-backed developer checkouts may be live; this case opts out explicitly.
    monkeypatch.setenv("AUREON_LLM_OFFLINE", "1")
    throne = ThroneCategorizer()  # default AureonLocalAdapter
    assert throne.decide("Office rent January", -85_000) is None
    assert any("agent seat empty" in b for b in throne.status()["blockers"])

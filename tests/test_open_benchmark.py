"""
Open benchmark harness — Aureon vs the published competition. Pinned.

Pins: datasets are provenance-stamped open sources (URL + sha256 + license)
and an unreachable source yields an HONEST empty set with the blocker named;
every item runs through the one door and carries an envelope; the scorer
counts only measured matches (a scripted correct answer scores, a wrong one
does not — no fabrication in either direction); every competition row is a
citation (source URL + vendor_published label), never a claimed number; and
the architecture table claims only Tier-A-pinned features.
"""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from aureon.analytics.open_benchmark import (
    ARCHITECTURE_CONTRACT,
    COMPETITION,
    VENDOR_PUBLISHED,
    Dataset,
    fetch_dataset,
    run_gsm8k,
    write_report,
)


@pytest.fixture(autouse=True)
def _dark_field(monkeypatch, tmp_path):
    monkeypatch.setenv("AUREON_HNC_TRACE_PATH", str(tmp_path / "hnc.jsonl"))
    monkeypatch.setenv("AUREON_ASSIMILATION_PATH", str(tmp_path / "assim.jsonl"))
    monkeypatch.setenv("AUREON_AFFECT_LAMBDA_PATH", str(tmp_path / "affect.json"))


# ── provenance-stamped fetch, honest offline ───────────────────────────────


def test_offline_without_cache_is_honestly_empty(tmp_path):
    ds = fetch_dataset("gsm8k", offline=True, cache_dir=tmp_path / "empty")
    assert ds.items == []
    assert ds.provenance["status"] == "honest_unavailable"
    assert "source unreachable" in ds.provenance["blocker"]


def test_offline_cache_reads_with_stamp(tmp_path):
    cache = tmp_path / "cache"
    cache.mkdir()
    (cache / "gsm8k.jsonl").write_text(
        '{"question": "2+2?", "answer": "the sum\\n#### 4"}\n', encoding="utf-8")
    (cache / "gsm8k.provenance.json").write_text(json.dumps(
        {"source_url": "https://example/test.jsonl", "sha256": "ab" * 32,
         "license": "MIT (labeled fixture)"}), encoding="utf-8")
    ds = fetch_dataset("gsm8k", limit=5, offline=True, cache_dir=cache)
    assert len(ds.items) == 1
    assert ds.provenance["sha256"] == "ab" * 32
    assert "MIT" in ds.provenance["license"]
    assert ds.provenance["items_total"] == 1


def test_committed_cache_carries_full_stamp():
    ds = fetch_dataset("gsm8k", limit=3, offline=True)
    if not ds.items:                       # cache not present on this tree
        assert ds.provenance["status"] == "honest_unavailable"
        return
    for key in ("source_url", "sha256", "license", "retrieved_at"):
        assert ds.provenance.get(key), key
    assert "grade-school-math" in ds.provenance["source_url"]


# ── the scorer is honest in both directions ────────────────────────────────


class _Plan:
    """LABELED harness double: fixed scripted answers, one per call."""

    model = "plan-harness"

    def __init__(self, finals):
        self.finals = list(finals)
        self.calls = 0

    def prompt(self, messages, system="", tools=None, max_tokens=4096,
               temperature=0.7, **k):
        from aureon.inhouse_ai.llm_adapter import LLMResponse

        text = self.finals[min(self.calls, len(self.finals) - 1)]
        self.calls += 1
        return LLMResponse(text=text, stop_reason="end_turn", model=self.model)

    def stream(self, *a, **k):
        from aureon.inhouse_ai.llm_adapter import StreamChunk

        yield StreamChunk(done=True)


class _ApprovedConscience:
    def ask_why(self, _action, _context):
        return SimpleNamespace(
            verdict=SimpleNamespace(name="APPROVED"),
            message="approved by deterministic benchmark conscience",
        )


def _cog(adapter):
    from aureon.operator.cognition import AureonCognition

    return AureonCognition(
        adapter=adapter,
        join_mesh=False,
        conscience=_ApprovedConscience(),
        mesh_broadcast=False,
        allow_repo_grounding=False,
        allow_organism_context=False,
        governance_enabled=False,
    )


def _fixture_ds():
    return Dataset(name="gsm8k", items=[
        {"question": "What is 2+2?", "answer": "sum\n#### 4"},
        {"question": "What is 3*5?", "answer": "product\n#### 15"},
    ], provenance={"license": "labeled fixture", "items_total": 2})


def test_humaneval_scorer_unwraps_fenced_code_honest_both_ways():
    from aureon.analytics.open_benchmark import run_humaneval

    # like real HumanEval, the prompt alone is valid Python (docstring body)
    ds = Dataset(name="humaneval", items=[{
        "task_id": "T/0", "prompt": 'def add2(x):\n    """add 2"""\n',
        "entry_point": "add2",
        "test": "def check(f):\n    assert f(1) == 3\n"}],
        provenance={"license": "labeled fixture", "items_total": 1})
    good = run_humaneval(
        _cog(_Plan(["```python\ndef add2(x):\n    return x + 2\n```"])), ds)
    assert good["passed"] == 1 and good["pass_at_1"] == 1.0
    wrong = run_humaneval(
        _cog(_Plan(["```python\ndef add2(x):\n    return x + 5\n```"])), ds)
    assert wrong["passed"] == 0 and wrong["pass_at_1"] == 0.0


def test_scorer_counts_only_measured_matches():
    right = run_gsm8k(_cog(_Plan(["The answer is 4.", "The answer is 15."])),
                      _fixture_ds())
    assert right["correct"] == 2 and right["accuracy"] == 1.0
    wrong = run_gsm8k(_cog(_Plan(["The answer is 7.", "No number here at all,"])),
                      _fixture_ds())
    assert wrong["correct"] == 0 and wrong["accuracy"] == 0.0
    # every item went through the one door and carries an envelope trace
    assert all(r["envelope"] for r in right["results"])


# ── citations, never claims ────────────────────────────────────────────────


def test_competition_rows_are_citations_not_claims():
    assert len(COMPETITION) >= 3
    for row in COMPETITION:
        assert row["source"].startswith("https://")
        assert row["label"] == VENDOR_PUBLISHED
        # no naked numbers: any score field is None (cite the card directly)
        assert all(v is None for k, v in row["scores"].items() if k != "note")


def test_architecture_table_claims_only_pinned_features():
    for row in ARCHITECTURE_CONTRACT:
        assert row["aureon"].startswith("measured — b")
        assert row["raw_model_api"] == "not offered"


def test_report_writer_renders_honest_unavailable(tmp_path):
    payload = {
        "adapter": "NoneAdapter",
        "aureon_measured": {
            "gsm8k": {"n": 0, "ok_turns": 0, "correct": 0, "accuracy": None,
                      "provenance": {}, "results": []},
            "humaneval": {"n": 0, "ok_turns": 0, "passed": 0, "pass_at_1": None,
                          "provenance": {}, "results": []}},
        "competition_cited": COMPETITION,
        "architecture_contract": ARCHITECTURE_CONTRACT,
        "honesty": "test",
    }
    md, js = tmp_path / "r.md", tmp_path / "r.json"
    write_report(payload, md, js)
    text = md.read_text(encoding="utf-8")
    assert "honest_unavailable" in text
    assert "vendor-published" in text or "Competition" in text
    assert json.loads(js.read_text(encoding="utf-8"))["adapter"] == "NoneAdapter"

"""
The Containment Study — the SG-1 thesis pinned rule by rule.

Pins: the ungoverned swarm actualizes EVERYTHING (pure expansion) while the
governed one is selective; the beyond-cliff β=1.2 group is contained only
under governance; hard votes collapse the sea to exactly zero entropy (and
the monoculture then never clears the gate); heading churn is contained;
single-agent task ownership is structurally refused; the study is labeled;
and the whole experiment is deterministic.
"""

from __future__ import annotations

import pytest

from aureon.swarm.containment import POLICIES, run_containment_study


@pytest.fixture(autouse=True)
def _dark_field(monkeypatch, tmp_path):
    monkeypatch.setenv("AUREON_HNC_TRACE_PATH", str(tmp_path / "hnc.jsonl"))


@pytest.fixture(scope="module")
def study():
    return run_containment_study()


def test_ungoverned_expansion_is_real_and_governance_is_selective(study):
    v = study["variants"]
    assert v["ungoverned"]["actualization_rate"] == 1.0   # everything materializes
    assert v["no_gate"]["actualization_rate"] == 1.0      # the Queen was the gate
    assert v["governed"]["actualization_rate"] < 0.5      # selection is real


def test_cliff_and_warmup_contained_only_under_governance(study):
    v = study["variants"]
    assert v["governed"]["cliff_actualizations"] == 0
    assert v["governed"]["warmup_actualizations"] == 0
    assert v["no_gate"]["cliff_actualizations"] > 0       # β=1.2 ran free
    assert v["ungoverned"]["warmup_actualizations"] > 0   # unmeasured Γ ignored


def test_hard_votes_collapse_the_sea(study):
    v = study["variants"]
    assert v["hard_votes"]["mean_simplex_entropy"] == 0.0  # monoculture, exactly
    assert v["governed"]["mean_simplex_entropy"] > 0.5     # the sea stays a sea
    # and the monoculture never clears the coherence gate — measured, not asserted
    assert v["hard_votes"]["actualization_rate"] == 0.0


def test_heading_churn_is_contained(study):
    v = study["variants"]
    assert v["governed"]["heading_churn"] < v["no_gate"]["heading_churn"]


def test_single_agent_ownership_structurally_refused(study):
    assert study["single_agent_refusal"] is not None
    assert "never owned by a single agent" in study["single_agent_refusal"]


def test_study_is_labeled_and_deterministic(study):
    assert "LABELED governance-ablation" in study["boundary"]
    assert study == run_containment_study()               # same physics, same record
    assert set(study["variants"]) == set(POLICIES)


def test_unknown_policy_is_refused_by_name():
    from aureon.swarm.containment import _run_policy

    with pytest.raises(ValueError, match="by name"):
        _run_policy("anarchy", 4)

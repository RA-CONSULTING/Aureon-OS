"""Remaining stage-1 tools. Fixtures come from the repo tests named in input_source."""

from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

pytestmark = pytest.mark.timeout(180)


def _load(text: str) -> dict:
    return json.loads(text)


def test_generated_score_matches_the_repo_baseline() -> None:
    from aureon_public.stage1_rest import generated_breakdown, generated_normalized, generated_score

    full = _load(generated_score())
    assert full["called"] is True
    assert full["result"] == 100.0
    assert full["input_source"].endswith("test_harmonic_nexus_score_full_strength_is_100")
    assert "not a live reading" in full["input_note"].lower()

    bounds = _load(generated_normalized())
    assert bounds["called"] is True
    fields = bounds["result"]["fields"]
    assert fields["source_strength"] == 1.0
    assert fields["coherence_agreement"] == 0.0
    assert 0.0 <= fields["repeatability"] <= 1.0

    breakdown = _load(generated_breakdown())
    assert breakdown["called"] is True
    assert set(breakdown["result"]) == {
        "source_strength",
        "coherence_agreement",
        "repeatability",
        "friction_feasibility",
        "contradiction_handling",
        "score",
    }


def test_swarm_voice_and_steer_match_the_repo_baseline() -> None:
    from aureon_public.stage1_rest import swarm_steer_flow, swarm_voice_read

    voice = _load(swarm_voice_read(0.80))
    assert voice["called"] is True
    assert voice["result"] == ["ACTIVE", 0.80]
    assert "test_druidic_council.py" in voice["input_source"]
    assert "not a live lighthouse reading" in voice["input_note"].lower()

    steered = _load(swarm_steer_flow())
    assert steered["called"] is True
    original = [1.0, 2.0, 0.0, 0.5]
    out = steered["result"]["steered"]

    def norm(values: list[float]) -> float:
        return math.sqrt(sum(item * item for item in values))

    assert norm(out) == pytest.approx(norm(original), abs=1e-12)
    assert "test_swarm_fleadh.py" in steered["input_source"]


def test_stage1_defaults_are_labelled_and_not_live() -> None:
    from aureon_public.stage1_rest import (
        generated_default_inputs,
        organism_compose_layers,
        swarm_actualization_to_dict,
        swarm_agent_substrate,
        swarm_build_lane,
        swarm_build_seat,
        swarm_coherence_gamma,
        swarm_echo,
    )

    for fn in (
        generated_default_inputs,
        organism_compose_layers,
        swarm_actualization_to_dict,
        swarm_agent_substrate,
        swarm_build_lane,
        swarm_build_seat,
        swarm_coherence_gamma,
        swarm_echo,
    ):
        body = _load(fn())
        assert body.get("input_source"), fn.__name__
        assert body.get("input_note"), fn.__name__
        assert "not a" in body["input_note"].lower()
        assert "consciousness_" not in json.dumps(body)
    gamma = _load(swarm_coherence_gamma())
    assert gamma["result"] is None
    echo = _load(swarm_echo())
    assert echo["result"] is None
    substrate = _load(swarm_agent_substrate())
    assert substrate["called"] is True
    assert substrate["result"] == 0.0
    hold = _load(organism_compose_layers())
    assert hold["called"] is True
    assert hold["result"]["may_act"] is False
    lane = _load(swarm_build_lane())
    assert lane["called"] is True
    seat = _load(swarm_build_seat())
    assert seat["called"] is True
    assert seat["result"]["seat"] == "seer"


def test_stage1_measured_record_is_pinned_and_labelled() -> None:
    from aureon_public.guard_loader import PINNED_COMMIT
    from aureon_public.stage1_rest import TOOLS

    record = json.loads((ROOT / "measured" / "aureon_public_stage1.json").read_text(encoding="utf-8"))
    assert record["environment"]["aureon_direct_url"]["vcs_info"]["commit_id"] == PINNED_COMMIT
    assert set(record["calls"]) == {fn.__name__ for fn in TOOLS}
    for name, call in record["calls"].items():
        body = json.loads(call["text"])
        assert body["aureon_source"]["kind"] == "pinned", name
        assert body["aureon_source"]["commit"] == PINNED_COMMIT
        assert call["input_source"] == body["input_source"]
        assert "consciousness_" not in call["text"]
        assert call["isError"] is False

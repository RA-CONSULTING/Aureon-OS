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


def test_dataclass_from_dict_refuses_an_unlisted_class_from_another_package() -> None:
    from aureon.swarm.druidic_council import CouncilSeat
    from aureon_public.call_worker import _dataclass_from_dict

    def reader():
        return None

    reader.__globals__["CouncilSeat"] = CouncilSeat
    payload = {"name": "seer", "agent_id": "agent-seer"}
    assert _dataclass_from_dict(reader, CouncilSeat, payload) is None
    assert _dataclass_from_dict(reader, "CouncilSeat", payload) is None


def test_dataclass_from_dict_refuses_post_init_anywhere_on_the_mro(monkeypatch: pytest.MonkeyPatch) -> None:
    from dataclasses import dataclass

    import aureon_public.body as body
    from aureon_public.call_worker import _dataclass_from_dict, _inventory_path

    ran = {"parent": False, "direct": False}

    @dataclass
    class Parent:
        def __post_init__(self) -> None:
            ran["parent"] = True

    @dataclass
    class Child(Parent):
        value: int

    @dataclass
    class Direct:
        value: int

        def __post_init__(self) -> None:
            ran["direct"] = True

    def reader():
        return None

    allowed = set(body._CONSTRUCTOR_ALLOWLIST)
    allowed.add((_inventory_path(Child), Child.__name__))
    allowed.add((_inventory_path(Direct), Direct.__name__))
    monkeypatch.setattr(body, "_CONSTRUCTOR_ALLOWLIST", allowed)
    assert Child.__init__.__code__.co_filename == "<string>"
    assert Direct.__init__.__code__.co_filename == "<string>"
    assert _dataclass_from_dict(reader, Child, {"value": 1}) is None
    assert _dataclass_from_dict(reader, Direct, {"value": 1}) is None
    assert ran == {"parent": False, "direct": False}


def _write_sibling(path: Path, text: str) -> None:
    import os
    import subprocess

    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    except PermissionError:
        subprocess.check_call(["sudo", "-n", "mkdir", "-p", str(path.parent)])
        subprocess.check_call(["sudo", "-n", "chown", "-R", f"{os.getuid()}:{os.getgid()}", str(path.parents[1])])
        path.write_text(text, encoding="utf-8")


def _remove_tree(path: Path) -> None:
    import shutil
    import subprocess

    if not path.exists():
        return
    try:
        shutil.rmtree(path)
    except PermissionError:
        subprocess.check_call(["sudo", "-n", "rm", "-rf", str(path)])


def test_organism_compose_does_not_load_sibling_feeds(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import urllib.request

    from aureon_public.paths import repo_root
    from aureon_public.stage1_rest import organism_compose_layers

    requests: list[str] = []

    def capture(url: object, *args: object, **kwargs: object) -> None:
        requests.append(str(url))
        raise AssertionError(f"urllib Request was built for {url}")

    monkeypatch.setattr(urllib.request, "Request", capture)
    monkeypatch.setattr(urllib.request, "urlopen", capture)

    def plant(root: Path, marker: Path) -> None:
        field = (
            "from pathlib import Path\n"
            f"Path({str(marker)!r}).write_text('field')\n"
            "from urllib.request import Request\n"
            "Request('https://services.swpc.noaa.gov/products/noaa-planetary-k-index.json')\n"
            "SOURCE = 'https://services.swpc.noaa.gov/products/noaa-planetary-k-index.json'\n"
            "def observe_planetary_k_index(transport=None):\n"
            "    from urllib.request import Request, urlopen\n"
            "    if transport is None:\n"
            "        Request(SOURCE)\n"
            "        return urlopen(SOURCE).read()\n"
            "    return transport(SOURCE)\n"
        )
        market = (
            "from pathlib import Path\n"
            f"Path({str(marker)!r}).write_text('market')\n"
            "from urllib.request import Request\n"
            "Request('https://data-api.binance.vision/api/v3/ticker/price?symbol=BTCUSDT')\n"
            "SOURCE = 'https://data-api.binance.vision/api/v3/ticker/price?symbol=BTCUSDT'\n"
            "def observe_public_price(transport=None):\n"
            "    from urllib.request import Request, urlopen\n"
            "    if transport is None:\n"
            "        Request(SOURCE)\n"
            "        return urlopen(SOURCE).read()\n"
            "    return transport(SOURCE)\n"
        )
        _write_sibling(root / "NEXUS-LIVE-FEED-" / "organism" / "public_field.py", field)
        _write_sibling(root / "Aureon-Trading--Project-Sero" / "organism" / "public_market.py", market)

    marker = tmp_path / "sibling-exec.txt"
    plant(tmp_path / "repos-env", marker)
    monkeypatch.setenv("AUREON_REPOS_ROOT", str(tmp_path / "repos-env"))

    beside = repo_root().parent
    planted_beside: list[Path] = []
    for name in ("NEXUS-LIVE-FEED-", "Aureon-Trading--Project-Sero"):
        path = beside / name
        if not path.exists():
            planted_beside.append(path)
    try:
        if len(planted_beside) == 2:
            plant(beside, marker)
        body = _load(organism_compose_layers())
    finally:
        for path in planted_beside:
            _remove_tree(path)
    assert len(planted_beside) == 2 or all((beside / name).exists() for name in (
        "NEXUS-LIVE-FEED-",
        "Aureon-Trading--Project-Sero",
    ))
    assert body["called"] is True
    assert body["result"]["may_act"] is False
    assert requests == []
    assert not marker.exists()


def test_generated_score_matches_the_repo_baseline() -> None:
    from aureon_public.stage1_rest import generated_breakdown, generated_normalized, generated_score

    full = _load(generated_score())
    assert full["called"] is True
    assert full["result"] == 100.0
    assert full["input_source"].endswith("test_harmonic_nexus_score_full_strength_is_100")
    assert "not a live reading" in full["input_note"].lower()
    assert "does not score any Aureon or HNC claim" in full["input_note"]
    assert "cannot be quoted as evidence" in full["input_note"]

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
    score = json.loads(record["calls"]["generated_score"]["text"])
    assert "does not score any Aureon or HNC claim" in score["input_note"]
    assert "cannot be quoted as evidence" in score["input_note"]
    assert score["input_note"] == record["calls"]["generated_score"]["input_note"]

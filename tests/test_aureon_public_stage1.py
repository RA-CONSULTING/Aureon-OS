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


# Reachable public functions whose annotations name a dataclass that defines
# __post_init__. 27 parameters, 25 entry points. Strings only: this module
# does not import those packages.
_POST_INIT_CASES = [
    ("approval/notify.py", "subject_line", "request", "ApprovalRequest"),
    ("core/organism_composition.py", "bind_canonical_organism_composition", "governance", "GovernanceBindings"),
    ("core/organism_composition.py", "configure_canonical_organism_composition", "composition", "OrganismComposition"),
    ("governance/legacy_capability_manifest.py", "build_legacy_capability_manifest", "capabilities", "LegacyEconomicCapability"),
    ("governance/legacy_economic_unity.py", "bind_legacy_economic_unity_gateway", "capabilities", "LegacyEconomicCapability"),
    ("governance/qgita_kundalini_truth_gate.py", "validate_diagnostic_bundle", "request", "TruthGateRequest"),
    ("governance/qgita_kundalini_truth_gate.py", "validate_grounding_bundle", "request", "TruthGateRequest"),
    ("governance/trusted_truth_evidence.py", "validate_diagnostic_signal_set", "request", "TruthGateRequest"),
    ("grants/scout.py", "assess", "opportunity", "Opportunity"),
    ("plumber/authorization_chain_v02.py", "validate_authorization_trust_v02", "trust", "AuthorityBindingV02"),
    ("plumber/magic_star_v02.py", "build_heart_source_identity_commitment_v02", "source_authority", "AuthorityBindingV02"),
    ("plumber/magic_star_v02.py", "heart_receipt_commitment_v02", "receipt", "SignedReceipt"),
    ("plumber/magic_star_v02.py", "validate_distinct_authorities_v02", "trust", "AuthorityBindingV02"),
    ("plumber/magic_star_v02.py", "verify_component_v02", "expected_authority", "AuthorityBindingV02"),
    ("plumber/receipts.py", "validate_receipt", "receipt", "SignedReceipt"),
    ("plumber/recipient_proof_v02.py", "verify_recipient_proof_v02", "enrollment", "RecipientEnrollmentV02"),
    ("plumber/release_boundary_v02.py", "validate_capability_release_result_v02", "receipt_authority", "AuthorityBindingV02"),
    ("plumber/release_boundary_v02.py", "validate_capability_release_result_v02", "result", "CapabilityReleaseResultV02"),
    ("plumber/release_evidence_v02.py", "validate_release_evidence_trust_v02", "trust", "AuthorityBindingV02"),
    ("plumber/source_identity.py", "verify_source_identity", "value", "SourceIdentityV0"),
    ("plumber/spore_transport.py", "reassemble_ciphertext", "fragments", "SporeFragment"),
    ("plumber/spore_transport.py", "reassemble_ciphertext", "manifest", "SporeManifest"),
    ("plumber/temporal_identity.py", "validate_temporal_identity", "identity", "TemporalIdentityV0"),
    ("portals/actions.py", "apply_approved_action", "action", "PortalAction"),
    ("queen/queen_mind.py", "bind_queen_mind", "manifest", "QueenFacultyManifest"),
    ("queen/queen_process_roof.py", "bind_queen_process_roof", "composition", "OrganismComposition"),
    ("wisdom/platypus.py", "compute_lambda_field", "config", "PlatypusConfig"),
]


def test_post_init_cases_cover_the_reachable_parameters() -> None:
    assert len(_POST_INIT_CASES) == 27
    assert len({(module, symbol) for module, symbol, _param, _name in _POST_INIT_CASES}) == 25
    assert ("queen/queen_process_roof.py", "bind_queen_process_roof", "composition", "OrganismComposition") in _POST_INIT_CASES
    assert ("portals/actions.py", "apply_approved_action", "action", "PortalAction") in _POST_INIT_CASES
    assert ("core/organism_composition.py", "configure_canonical_organism_composition", "composition", "OrganismComposition") in _POST_INIT_CASES


@pytest.mark.parametrize(
    ("module", "symbol", "param", "class_name"),
    _POST_INIT_CASES,
    ids=[f"{module}:{symbol}:{param}" for module, symbol, param, _name in _POST_INIT_CASES],
)
def test_worker_refuses_post_init_dataclass(module: str, symbol: str, param: str, class_name: str) -> None:
    """A JSON object through the worker does not construct the dataclass."""

    import subprocess
    import sys

    code = r"""
import inspect
import sys
import typing

sys.path.insert(0, sys.argv[1])
module, symbol, param, class_name = sys.argv[2:6]
from aureon_public.body import dotted_for
from aureon_public.call_worker import _call, _dataclass_from_dict, _load

mod = _load(dotted_for(module), module)
fn = getattr(mod, symbol)
hint = typing.get_type_hints(fn)[param]

def walk(value):
    if isinstance(value, type):
        yield value
        return
    for arg in typing.get_args(value):
        yield from walk(arg)

found = [cls for cls in walk(hint) if cls.__name__ == class_name]
if len(found) != 1:
    raise SystemExit(f"class {class_name} not in {hint!r}")
cls = found[0]
ran = {"n": 0}

def boom(self):
    ran["n"] += 1

patched = False
for base in cls.__mro__:
    if "__post_init__" in base.__dict__:
        setattr(base, "__post_init__", boom)
        patched = True
if not patched:
    raise SystemExit("no __post_init__ on MRO")
raw = inspect.signature(fn).parameters[param].annotation
built = _dataclass_from_dict(fn, raw, {})
if built is not None:
    raise SystemExit("dataclass was built from the JSON object")
try:
    _call(dotted_for(module), symbol, {param: {}}, module)
except Exception:
    pass
if ran["n"]:
    raise SystemExit(f"__post_init__ ran {ran['n']}")
"""
    completed = subprocess.run(
        [sys.executable, "-c", code, str(ROOT / "mcp"), module, symbol, param, class_name],
        cwd="/tmp",
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr[-2000:] + completed.stdout[-500:]


def test_stage1_score_input_with_post_init_is_not_built() -> None:
    """The allowlisted stage-1 score dataclass is refused once it defines __post_init__."""

    import subprocess
    import sys

    code = r"""
import inspect
import sys

sys.path.insert(0, sys.argv[1])
from aureon_public.call_worker import _call, _dataclass_from_dict, _load

module = "generated/research_cinema/harmonic_nexus_score_model.py"
mod = _load("aureon.generated.research_cinema.harmonic_nexus_score_model", module)
cls = mod.HarmonicNexusScoreInputs
fn = mod.harmonic_nexus_score
ran = {"n": 0}

def boom(self):
    ran["n"] += 1

cls.__post_init__ = boom
payload = {
    "source_strength": 1.0,
    "coherence_agreement": 1.0,
    "repeatability": 1.0,
    "friction_feasibility": 1.0,
    "contradiction_handling": 1.0,
}
raw = inspect.signature(fn).parameters["inputs"].annotation
if _dataclass_from_dict(fn, raw, payload) is not None:
    raise SystemExit("stage-1 dataclass was built")
try:
    _call(
        "aureon.generated.research_cinema.harmonic_nexus_score_model",
        "harmonic_nexus_score",
        {"inputs": payload},
        module,
    )
except Exception:
    pass
if ran["n"]:
    raise SystemExit(f"__post_init__ ran {ran['n']}")
"""
    completed = subprocess.run(
        [sys.executable, "-c", code, str(ROOT / "mcp")],
        cwd="/tmp",
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr[-2000:] + completed.stdout[-500:]


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
        swarm_actualization_to_dict,
        swarm_agent_substrate,
        swarm_build_seat,
        swarm_coherence_gamma,
        swarm_echo,
    )

    for fn in (
        generated_default_inputs,
        swarm_actualization_to_dict,
        swarm_agent_substrate,
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
    seat = _load(swarm_build_seat())
    assert seat["called"] is True
    assert seat["result"]["seat"] == "seer"


def test_stage1_measured_record_is_pinned_and_labelled() -> None:
    from aureon_public.guard_loader import PINNED_COMMIT
    from aureon_public.stage1_rest import TOOLS

    record = json.loads((ROOT / "measured" / "aureon_public_stage1.json").read_text(encoding="utf-8"))
    from aureon_public.measurement_stamp import CODE_COMMIT_NOTE, PIN_AUREON_TREE

    assert record["environment"]["aureon_direct_url"]["vcs_info"]["commit_id"] == PINNED_COMMIT
    assert record["environment"]["aureon_tree"] == PIN_AUREON_TREE
    assert record["environment"]["pin_aureon_tree"] == PIN_AUREON_TREE
    assert record["environment"]["code_commit_note"] == CODE_COMMIT_NOTE
    assert len(record["environment"]["code_commit"]) == 40
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

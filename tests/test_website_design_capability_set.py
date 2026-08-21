"""Focused invariants for the website/design capability contract registry."""

from __future__ import annotations

import sys
from copy import deepcopy
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest

_MODULE_PATH = (
    Path(__file__).resolve().parents[1] / "aureon" / "operator" / "website_design_capability_set.py"
)
_SPEC = spec_from_file_location("aureon_website_design_capability_set", _MODULE_PATH)
assert _SPEC is not None and _SPEC.loader is not None
_MODULE = module_from_spec(_SPEC)
sys.modules[_SPEC.name] = _MODULE
_SPEC.loader.exec_module(_MODULE)

AUTHORITY_BOUNDARY = _MODULE.AUTHORITY_BOUNDARY
HNC_STAGES = _MODULE.HNC_STAGES
OWNER_AGENTS = _MODULE.OWNER_AGENTS
REGISTRY_OWNER_AGENT = _MODULE.REGISTRY_OWNER_AGENT
REQUIRED_SKILL_IDS = _MODULE.REQUIRED_SKILL_IDS
WebsiteDesignCapabilitySetError = _MODULE.WebsiteDesignCapabilitySetError
discover_website_design_capability_set = _MODULE.discover_website_design_capability_set
require_valid_website_design_capability_set = _MODULE.require_valid_website_design_capability_set
validate_website_design_capability_set = _MODULE.validate_website_design_capability_set


def _failed_checks(registry: dict[str, object]) -> set[str]:
    verification = validate_website_design_capability_set(registry)
    return {str(check["id"]) for check in verification["checks"] if not check["passed"]}


def test_canonical_registry_passes_and_is_non_authoritative() -> None:
    registry = discover_website_design_capability_set()
    verification = validate_website_design_capability_set(registry)

    assert verification["passed"] is True
    assert verification["state"] == "pass"
    assert verification["release_eligible"] is False
    assert verification["deployment_authority"] == "none"
    assert registry["authority"] == AUTHORITY_BOUNDARY
    assert registry["registry_owner_agent"] == REGISTRY_OWNER_AGENT == "skill_writer"


def test_every_required_skill_has_one_owner_contract_version_and_evidence_path() -> None:
    registry = discover_website_design_capability_set()
    skills = registry["skills"]

    assert isinstance(skills, list)
    assert [row["skill_id"] for row in skills] == list(REQUIRED_SKILL_IDS)
    assert all(isinstance(row["owner_agent"], str) for row in skills)
    assert all(row["owner_agent"] in OWNER_AGENTS for row in skills)
    assert all("owner_agents" not in row for row in skills)
    assert len({row["contract"]["id"] for row in skills}) == len(skills)
    assert len({row["evidence_path"] for row in skills}) == len(skills)
    assert all(row["version"] == "1.0.0" for row in skills)
    assert all(row["contract"]["obligation"].strip() for row in skills)
    assert all(row["contract"]["evidence_required"] is True for row in skills)


def test_hnc_loop_is_exact_closed_and_fully_covered() -> None:
    registry = discover_website_design_capability_set()
    loop = registry["hnc_loop"]
    skills = registry["skills"]

    assert isinstance(loop, list)
    assert [row["stage"] for row in loop] == list(HNC_STAGES)
    assert [row["ordinal"] for row in loop] == list(range(1, 13))
    assert all(row["next_stage"] == loop[(index + 1) % len(loop)]["stage"] for index, row in enumerate(loop))
    assert {stage for skill in skills for stage in skill["hnc_stages"]} == set(HNC_STAGES)


def test_deploy_is_one_capability_and_never_authority() -> None:
    registry = discover_website_design_capability_set()
    deploy_skills = [row for row in registry["skills"] if "Deploy" in row["hnc_stages"]]

    assert [row["skill_id"] for row in deploy_skills] == ["homepl_deploy_cache_ssl_readback"]
    assert deploy_skills[0]["owner_agent"] == "homepl_deploy"
    assert registry["authority"]["deployment_default"] == "blocked"
    assert registry["authority"]["registry_grants_deployment_authority"] is False
    assert registry["authority"]["human_veto"] == "final-and-non-overridable-at-every-stage"


@pytest.mark.parametrize(
    ("mutation", "expected_check"),
    [
        (
            lambda registry: registry["skills"][0].__setitem__(
                "owner_agent", ["design_director", "graphic_motion"]
            ),
            "single-accountable-owner",
        ),
        (
            lambda registry: registry["skills"][0].__setitem__("owner_agent", "graphic_motion"),
            "single-accountable-owner",
        ),
        (
            lambda registry: registry["skills"][0].__setitem__("version", "latest"),
            "versioned-contracts",
        ),
        (
            lambda registry: registry["skills"][0].__setitem__(
                "evidence_path", "../outside/visual_identity_tokens"
            ),
            "evidence-paths",
        ),
        (
            lambda registry: registry["skills"].pop(),
            "required-skills",
        ),
        (
            lambda registry: registry["hnc_loop"][7].__setitem__("contract", "automatic authority"),
            "hnc-loop-order",
        ),
        (
            lambda registry: registry["authority"].__setitem__("registry_grants_deployment_authority", True),
            "authority-boundary",
        ),
    ],
)
def test_registry_rejects_contract_drift(mutation, expected_check: str) -> None:
    registry = deepcopy(discover_website_design_capability_set())
    mutation(registry)

    assert expected_check in _failed_checks(registry)


def test_require_valid_rejects_invalid_registry() -> None:
    registry = discover_website_design_capability_set()
    registry["skills"][0]["contract"]["obligation"] = ""

    with pytest.raises(WebsiteDesignCapabilitySetError, match="versioned-contracts"):
        require_valid_website_design_capability_set(registry)

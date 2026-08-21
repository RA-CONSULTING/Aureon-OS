"""Machine-readable website and design capability contracts.

This module is the small, deterministic control-plane registry for Aureon's
investor-website work.  It names the required skills, gives each skill exactly
one accountable owner, and binds every skill to a versioned contract and a
repo-relative evidence location.

Discovery and validation are deliberately read-only.  A valid registry does
not select a candidate, approve a claim, grant credentials, authorise a
deployment, or prove a live outcome.  Production remains default-deny until
the exact current candidate/package and target pass the human AuthorityGate;
the CEO/owner/user veto is final at every stage.
"""

from __future__ import annotations

import argparse
import importlib
import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Any

REGISTRY_SCHEMA = "aureon.website-design-capability-set.v1"
VERIFICATION_SCHEMA = "aureon.website-design-capability-set-verification.v1"
REGISTRY_VERSION = "2.0.0"
REGISTRY_OWNER_AGENT = "skill_writer"
EVIDENCE_ROOT = PurePosixPath("artifacts/website-operator/capability-evidence")

OWNER_AGENTS = (
    "design_director",
    "graphic_motion",
    "frontend_implementation",
    "evidence_copy",
    "research_object",
    "homepl_deploy",
    "audit_benchmark",
    "skill_writer",
)

REQUIRED_SKILL_IDS = (
    "visual_identity_tokens",
    "layout_typography_grid",
    "motion_interaction",
    "information_architecture_routing",
    "evidence_bound_copywriting",
    "research_object_rendering",
    "diagram_connectome_graphics",
    "image_svg_generative_pipeline",
    "accessibility_reduced_motion",
    "performance_core_web_vitals",
    "homepl_deploy_cache_ssl_readback",
    "claim_state_linter",
    "competitor_position_audit",
    "design_qa_visual_regression",
    "content_inventory_connectors",
)

IMPLEMENTATION_ENTRYPOINTS = {
    "visual_identity_tokens": "audit_tokens",
    "layout_typography_grid": "audit_layout",
    "motion_interaction": "audit_motion",
    "information_architecture_routing": "audit_routing",
    "evidence_bound_copywriting": "audit_copy_provenance",
    "research_object_rendering": "audit_research_objects",
    "diagram_connectome_graphics": "audit_diagram_fallbacks",
    "image_svg_generative_pipeline": "audit_image_inventory",
    "accessibility_reduced_motion": "prepare_accessibility_audit",
    "performance_core_web_vitals": "audit_performance",
    "homepl_deploy_cache_ssl_readback": "verify_homepl_readback",
    "claim_state_linter": "lint_claim_states",
    "competitor_position_audit": "audit_competitor_sources",
    "design_qa_visual_regression": "evaluate_visual_regression",
    "content_inventory_connectors": "reconcile_content_inventory",
}
IMPLEMENTATION_PACKAGE = "aureon.operator.website_design_capabilities"


@dataclass(frozen=True)
class LoopStep:
    """One mandatory transition in the HNC website-improvement loop."""

    stage: str
    contract: str
    next_stage: str

    def to_dict(self, ordinal: int) -> dict[str, object]:
        return {
            "ordinal": ordinal,
            "stage": self.stage,
            "contract": self.contract,
            "next_stage": self.next_stage,
            "evidence_required": True,
        }


HNC_LOOP = (
    LoopStep(
        "Sense",
        "Inventory the controlled source, live surface, research, stakeholder signals, "
        "rights state, and current external evidence without mutation.",
        "Route",
    ),
    LoopStep(
        "Route",
        "Select only the registered skill and its single accountable owner for each bounded task.",
        "Constraint",
    ),
    LoopStep(
        "Constraint",
        "Bind claim state, provenance, rights, privacy, accessibility, performance, source, and authority limits.",
        "Generate",
    ),
    LoopStep(
        "Generate",
        "Create changes only in an isolated candidate whose source and intended delta are inspectable.",
        "Test",
    ),
    LoopStep(
        "Test",
        "Run deterministic static, functional, accessibility, performance, link, metadata, and visual checks.",
        "ResonanceCheck",
    ),
    LoopStep(
        "ResonanceCheck",
        "Compare the tested result with Aureon's ethos, investor journey, research evidence, and named review evidence.",
        "Veto",
    ),
    LoopStep(
        "Veto",
        "Stop on any unresolved claim, rights, privacy, accessibility, performance, source, visual, or security blocker.",
        "AuthorityGate",
    ),
    LoopStep(
        "AuthorityGate",
        "Require the current CEO/owner/user decision bound to the exact candidate/package hash and deployment target; "
        "the human veto cannot be overridden.",
        "Deploy",
    ),
    LoopStep(
        "Deploy",
        "After a verified backup, publish only the exact authorised package to the authenticated served root.",
        "ReadBack",
    ),
    LoopStep(
        "ReadBack",
        "Fetch the public routes and verify status, TLS, cache behaviour, content hashes, fragments, and critical assets.",
        "Ledger",
    ),
    LoopStep(
        "Ledger",
        "Append immutable candidate, test, approval, backup, deployment, and live-readback evidence; never infer success.",
        "Expand",
    ),
    LoopStep(
        "Expand",
        "Promote only evidence-backed learning into a versioned contract improvement, then sense the system again.",
        "Sense",
    ),
)

HNC_STAGES = tuple(step.stage for step in HNC_LOOP)

AUTHORITY_BOUNDARY = {
    "deployment_default": "blocked",
    "registry_grants_deployment_authority": False,
    "human_authority": "ceo_owner_user",
    "approval_binding": "exact-current-candidate-package-hash-and-deployment-target",
    "human_veto": "final-and-non-overridable-at-every-stage",
    "backup_required_before_deploy": True,
    "live_readback_required": True,
    "credentials_in_evidence": False,
}


@dataclass(frozen=True)
class WebsiteDesignSkill:
    """A required capability with one accountable owner and evidence contract."""

    skill_id: str
    owner_agent: str
    obligation: str
    hnc_stages: tuple[str, ...]
    version: str = "1.0.0"

    @property
    def implementation_module(self) -> str:
        return f"{IMPLEMENTATION_PACKAGE}.{self.skill_id}"

    @property
    def implementation_entrypoint(self) -> str:
        return IMPLEMENTATION_ENTRYPOINTS[self.skill_id]

    @property
    def contract_id(self) -> str:
        return f"aureon.website-capability.{self.skill_id}.v1"

    @property
    def evidence_path(self) -> str:
        return (EVIDENCE_ROOT / self.skill_id).as_posix()

    def to_dict(self) -> dict[str, object]:
        return {
            "skill_id": self.skill_id,
            "required": True,
            "version": self.version,
            "owner_agent": self.owner_agent,
            "contract": {
                "id": self.contract_id,
                "obligation": self.obligation,
                "evidence_required": True,
            },
            "evidence_path": self.evidence_path,
            "hnc_stages": list(self.hnc_stages),
            "implementation": {
                "module": self.implementation_module,
                "entrypoint": self.implementation_entrypoint,
                "mode": "deterministic-read-only-audit-or-prepare",
                "result_schema": "aureon.website-capability-result.v1",
                "side_effects_allowed": False,
                "deployment_authority": "none",
            },
        }


SKILLS = (
    WebsiteDesignSkill(
        "visual_identity_tokens",
        "design_director",
        "Define source-controlled colour, type, spacing, depth, and state tokens; verify contrast and brand "
        "consistency before candidate use.",
        ("Constraint", "Generate", "ResonanceCheck"),
    ),
    WebsiteDesignSkill(
        "layout_typography_grid",
        "frontend_implementation",
        "Implement a responsive grid and typographic hierarchy that preserve reading order, legibility, and route intent "
        "across the supported viewport matrix.",
        ("Generate", "Test"),
    ),
    WebsiteDesignSkill(
        "motion_interaction",
        "graphic_motion",
        "Use purposeful, finite interaction and motion with equivalent reduced-motion and keyboard behaviour; reject "
        "spectacle that obscures evidence.",
        ("Constraint", "Generate", "ResonanceCheck"),
    ),
    WebsiteDesignSkill(
        "information_architecture_routing",
        "design_director",
        "Map investor questions to a coherent route, navigation, CTA, and fragment hierarchy with no dead ends or "
        "ambiguous evidence paths.",
        ("Route", "Constraint", "Test"),
    ),
    WebsiteDesignSkill(
        "evidence_bound_copywriting",
        "evidence_copy",
        "Write concise investor-facing copy bound to claim state and provenance, clearly separating research, use cases, "
        "relationships, and verified adoption.",
        ("Constraint", "Generate", "ResonanceCheck"),
    ),
    WebsiteDesignSkill(
        "research_object_rendering",
        "research_object",
        "Render curated research from dated authoritative records while preserving title, authorship, identifier, date, "
        "source link, and qualification without invented traction.",
        ("Sense", "Generate", "Test"),
    ),
    WebsiteDesignSkill(
        "diagram_connectome_graphics",
        "graphic_motion",
        "Express the HNC research-to-use-case system as a legible evidence-labelled diagram with an accessible textual "
        "fallback and no unsupported causal claim.",
        ("Constraint", "Generate", "Test"),
    ),
    WebsiteDesignSkill(
        "image_svg_generative_pipeline",
        "graphic_motion",
        "Create and optimise public visual assets only with recorded provenance, route-scoped rights, alt text, and "
        "footprint evidence; reject uncleared assets.",
        ("Constraint", "Generate", "Test", "Veto"),
    ),
    WebsiteDesignSkill(
        "accessibility_reduced_motion",
        "audit_benchmark",
        "Verify semantics, focus, keyboard flow, contrast, no-JavaScript reading, and reduced-motion behaviour; any "
        "unresolved release-blocking finding is a veto.",
        ("Test", "Veto"),
    ),
    WebsiteDesignSkill(
        "performance_core_web_vitals",
        "audit_benchmark",
        "Measure fixed asset budgets and Core Web Vitals across the agreed mobile and desktop matrix; veto unexplained "
        "regressions or incomplete measurements.",
        ("Test", "Veto"),
    ),
    WebsiteDesignSkill(
        "homepl_deploy_cache_ssl_readback",
        "homepl_deploy",
        "Verify the served-root backup, publish only an exactly authorised package, then prove TLS, cache, route, and "
        "file-hash state by live readback without retaining credentials.",
        ("AuthorityGate", "Deploy", "ReadBack", "Ledger"),
    ),
    WebsiteDesignSkill(
        "claim_state_linter",
        "evidence_copy",
        "Classify every material public claim as evidenced, qualified, or omitted and veto stale figures, internal "
        "records, overclaiming, or unsupported relationship and adoption language.",
        ("Sense", "Constraint", "Test", "Veto"),
    ),
    WebsiteDesignSkill(
        "competitor_position_audit",
        "audit_benchmark",
        "Capture dated primary-source competitor patterns, distinguish reusable design conventions from unsupported "
        "imitation, and route findings into Aureon's own evidence-led position.",
        ("Sense", "Route", "ResonanceCheck"),
    ),
    WebsiteDesignSkill(
        "design_qa_visual_regression",
        "audit_benchmark",
        "Capture and compare the named browser and viewport matrix, fragments, no-JavaScript state, and critical visual "
        "flows; incomplete evidence or an unresolved regression is a veto.",
        ("Test", "ResonanceCheck", "Veto", "Ledger"),
    ),
    WebsiteDesignSkill(
        "content_inventory_connectors",
        "research_object",
        "Read only the minimally necessary dated Gmail, Drive, ORCID, Substack, GitHub, and analytics evidence; redact "
        "secrets, personal data, and internal figures, and never equate raw activity with adoption.",
        ("Sense", "Route", "Ledger", "Expand"),
    ),
)

SKILL_BY_ID = {skill.skill_id: skill for skill in SKILLS}


class WebsiteDesignCapabilitySetError(ValueError):
    """Raised when the checked-in capability contract is invalid."""


def discover_website_design_capability_set() -> dict[str, object]:
    """Return a fresh, JSON-serialisable view of the checked-in registry."""

    return {
        "schema": REGISTRY_SCHEMA,
        "registry_version": REGISTRY_VERSION,
        "registry_owner_agent": REGISTRY_OWNER_AGENT,
        "state": "implemented-default-deny",
        "authority": dict(AUTHORITY_BOUNDARY),
        "owner_agents": list(OWNER_AGENTS),
        "hnc_loop": [step.to_dict(ordinal) for ordinal, step in enumerate(HNC_LOOP, start=1)],
        "skills": [skill.to_dict() for skill in SKILLS],
    }


def _check(identifier: str, passed: bool, message: str) -> dict[str, object]:
    return {"id": identifier, "passed": passed, "message": message}


def _valid_evidence_path(value: object, skill_id: str) -> bool:
    if not isinstance(value, str) or not value:
        return False
    path = PurePosixPath(value)
    return not path.is_absolute() and ".." not in path.parts and path == EVIDENCE_ROOT / skill_id


def _implementation_is_importable(module_name: str, entrypoint: str) -> bool:
    """Resolve one canonical implementation and reject aliases or rebound callables."""

    try:
        module = importlib.import_module(module_name)
        implementation = getattr(module, entrypoint)
    except (AttributeError, ImportError, ModuleNotFoundError):
        return False
    return (
        callable(implementation)
        and getattr(implementation, "__module__", None) == module_name
        and getattr(implementation, "__name__", None) == entrypoint
        and getattr(module, "SKILL_ID", None) == module_name.rsplit(".", maxsplit=1)[-1]
    )


def validate_website_design_capability_set(
    registry: Mapping[str, Any] | None = None,
) -> dict[str, object]:
    """Validate schema, ownership, contracts, evidence paths, loop, and authority.

    Validation performs no filesystem or network I/O and carries no release or
    deployment authority.
    """

    candidate: Mapping[str, Any] = discover_website_design_capability_set() if registry is None else registry
    checks: list[dict[str, object]] = []

    checks.append(
        _check(
            "schema-version",
            candidate.get("schema") == REGISTRY_SCHEMA
            and candidate.get("registry_version") == REGISTRY_VERSION,
            "Registry schema and version must match the checked-in contract.",
        )
    )
    checks.append(
        _check(
            "registry-owner",
            candidate.get("registry_owner_agent") == REGISTRY_OWNER_AGENT,
            "The skill-writer agent must own registry maintenance.",
        )
    )
    checks.append(
        _check(
            "authority-boundary",
            candidate.get("authority") == AUTHORITY_BOUNDARY
            and candidate.get("state") == "implemented-default-deny",
            "The registry must remain default-deny with final CEO/owner/user control.",
        )
    )

    loop_rows = candidate.get("hnc_loop")
    loop_ok = isinstance(loop_rows, list) and len(loop_rows) == len(HNC_LOOP)
    if isinstance(loop_rows, list):
        for ordinal, expected in enumerate(HNC_LOOP, start=1):
            if ordinal > len(loop_rows) or not isinstance(loop_rows[ordinal - 1], Mapping):
                loop_ok = False
                continue
            row = loop_rows[ordinal - 1]
            loop_ok = loop_ok and (
                row.get("ordinal") == ordinal
                and row.get("stage") == expected.stage
                and row.get("contract") == expected.contract
                and row.get("next_stage") == expected.next_stage
                and row.get("evidence_required") is True
            )
    checks.append(
        _check(
            "hnc-loop-order",
            loop_ok,
            "The exact Sense-to-Expand loop and return to Sense must remain intact.",
        )
    )

    owner_rows = candidate.get("owner_agents")
    checks.append(
        _check(
            "owner-agent-catalogue",
            isinstance(owner_rows, list)
            and all(isinstance(owner, str) for owner in owner_rows)
            and len(owner_rows) == len(set(owner_rows))
            and tuple(owner_rows) == OWNER_AGENTS,
            "Only the canonical owner-agent identifiers may be used.",
        )
    )

    skill_rows = candidate.get("skills")
    rows_ok = isinstance(skill_rows, list) and len(skill_rows) == len(REQUIRED_SKILL_IDS)
    seen_ids: list[str] = []
    seen_contracts: list[str] = []
    seen_paths: list[str] = []
    covered_stages: set[str] = set()
    deploy_stage_skills: set[str] = set()
    single_owner_ok = rows_ok
    contracts_ok = rows_ok
    versions_ok = rows_ok
    evidence_ok = rows_ok
    stages_ok = rows_ok
    implementation_contracts_ok = rows_ok
    implementations_importable = rows_ok
    seen_implementations: list[str] = []

    if isinstance(skill_rows, list):
        for row in skill_rows:
            if not isinstance(row, Mapping):
                rows_ok = single_owner_ok = contracts_ok = versions_ok = evidence_ok = stages_ok = (
                    implementation_contracts_ok
                ) = implementations_importable = False
                continue
            skill_id = row.get("skill_id")
            if not isinstance(skill_id, str):
                rows_ok = single_owner_ok = contracts_ok = versions_ok = evidence_ok = stages_ok = (
                    implementation_contracts_ok
                ) = implementations_importable = False
                continue
            seen_ids.append(skill_id)
            expected_skill = SKILL_BY_ID.get(skill_id)

            owner = row.get("owner_agent")
            single_owner_ok = (
                single_owner_ok
                and expected_skill is not None
                and isinstance(owner, str)
                and owner in OWNER_AGENTS
                and owner == expected_skill.owner_agent
            )
            single_owner_ok = single_owner_ok and "owner_agents" not in row
            rows_ok = rows_ok and row.get("required") is True

            version = row.get("version")
            versions_ok = (
                versions_ok
                and isinstance(version, str)
                and bool(re.fullmatch(r"[1-9]\d*\.\d+\.\d+", version))
            )
            versions_ok = versions_ok and expected_skill is not None and version == expected_skill.version

            contract = row.get("contract")
            if isinstance(contract, Mapping):
                contract_id = contract.get("id")
                obligation = contract.get("obligation")
                expected_contract = f"aureon.website-capability.{skill_id}.v1"
                contracts_ok = contracts_ok and (
                    contract_id == expected_contract
                    and isinstance(obligation, str)
                    and bool(obligation.strip())
                    and expected_skill is not None
                    and obligation == expected_skill.obligation
                    and contract.get("evidence_required") is True
                )
                if isinstance(contract_id, str):
                    seen_contracts.append(contract_id)
            else:
                contracts_ok = False

            evidence_path = row.get("evidence_path")
            evidence_ok = evidence_ok and _valid_evidence_path(evidence_path, skill_id)
            if isinstance(evidence_path, str):
                seen_paths.append(evidence_path)

            stages = row.get("hnc_stages")
            if isinstance(stages, list) and stages:
                stage_values = {stage for stage in stages if isinstance(stage, str)}
                stages_ok = stages_ok and len(stage_values) == len(stages)
                stages_ok = stages_ok and stage_values.issubset(set(HNC_STAGES))
                stages_ok = (
                    stages_ok and expected_skill is not None and tuple(stages) == expected_skill.hnc_stages
                )
                covered_stages.update(stage_values)
                if "Deploy" in stage_values:
                    deploy_stage_skills.add(skill_id)
            else:
                stages_ok = False

            implementation = row.get("implementation")
            if isinstance(implementation, Mapping) and expected_skill is not None:
                module_name = implementation.get("module")
                entrypoint = implementation.get("entrypoint")
                expected_module = expected_skill.implementation_module
                expected_entrypoint = expected_skill.implementation_entrypoint
                contract_ok = (
                    module_name == expected_module
                    and entrypoint == expected_entrypoint
                    and implementation.get("mode") == "deterministic-read-only-audit-or-prepare"
                    and implementation.get("result_schema") == "aureon.website-capability-result.v1"
                    and implementation.get("side_effects_allowed") is False
                    and implementation.get("deployment_authority") == "none"
                )
                implementation_contracts_ok = implementation_contracts_ok and contract_ok
                if isinstance(module_name, str) and isinstance(entrypoint, str):
                    binding = f"{module_name}:{entrypoint}"
                    seen_implementations.append(binding)
                    implementations_importable = (
                        implementations_importable
                        and module_name == expected_module
                        and entrypoint == expected_entrypoint
                        and _implementation_is_importable(expected_module, expected_entrypoint)
                    )
                else:
                    implementations_importable = False
            else:
                implementation_contracts_ok = False
                implementations_importable = False

    expected_ids = set(REQUIRED_SKILL_IDS)
    checks.extend(
        [
            _check(
                "required-skills",
                rows_ok
                and len(seen_ids) == len(set(seen_ids))
                and set(seen_ids) == expected_ids
                and tuple(seen_ids) == REQUIRED_SKILL_IDS,
                "Every canonical required skill must appear exactly once.",
            ),
            _check(
                "single-accountable-owner",
                single_owner_ok,
                "Every skill must name exactly one canonical owner_agent scalar.",
            ),
            _check(
                "versioned-contracts",
                versions_ok
                and contracts_ok
                and len(seen_contracts) == len(set(seen_contracts)) == len(REQUIRED_SKILL_IDS),
                "Every skill must have a semantic version and one unique non-empty evidence contract.",
            ),
            _check(
                "evidence-paths",
                evidence_ok and len(seen_paths) == len(set(seen_paths)) == len(REQUIRED_SKILL_IDS),
                "Every skill must have one unique safe path below the capability-evidence root.",
            ),
            _check(
                "hnc-stage-coverage",
                stages_ok and covered_stages == set(HNC_STAGES),
                "The registered skills must cover every mandatory HNC loop stage.",
            ),
            _check(
                "deploy-capability-separation",
                deploy_stage_skills == {"homepl_deploy_cache_ssl_readback"},
                "Only the Home.pl deployment skill may implement Deploy; authority still comes only from AuthorityGate.",
            ),
            _check(
                "implementation-contracts",
                implementation_contracts_ok
                and len(seen_implementations) == len(set(seen_implementations)) == len(REQUIRED_SKILL_IDS),
                "Every skill must bind exactly once to its canonical read-only implementation contract.",
            ),
            _check(
                "implementations-importable",
                implementations_importable,
                "Every canonical implementation module and entrypoint must import and resolve without rebinding.",
            ),
        ]
    )

    passed = all(bool(check["passed"]) for check in checks)
    return {
        "schema": VERIFICATION_SCHEMA,
        "passed": passed,
        "state": "pass" if passed else "fail",
        "release_eligible": False,
        "deployment_authority": "none",
        "checks": checks,
    }


def require_valid_website_design_capability_set(
    registry: Mapping[str, Any] | None = None,
) -> dict[str, object]:
    """Return a valid registry or raise without creating any external effect."""

    candidate = dict(registry) if registry is not None else discover_website_design_capability_set()
    verification = validate_website_design_capability_set(candidate)
    if not verification["passed"]:
        raw_checks = verification.get("checks")
        failed = (
            [str(check["id"]) for check in raw_checks if not check["passed"]]
            if isinstance(raw_checks, list)
            else ["verification-shape"]
        )
        raise WebsiteDesignCapabilitySetError("Invalid website/design capability set: " + ", ".join(failed))
    return candidate


def main(argv: Sequence[str] | None = None) -> int:
    """Print the registry or its read-only verification as JSON."""

    parser = argparse.ArgumentParser(
        prog="aureon-website-design-capabilities",
        description="Inspect Aureon's read-only website/design capability contracts.",
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Print verification instead of the registry.",
    )
    args = parser.parse_args(argv)
    payload = (
        validate_website_design_capability_set()
        if args.validate
        else discover_website_design_capability_set()
    )
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if not args.validate or payload["passed"] else 1


if __name__ == "__main__":  # pragma: no cover - exercised through the public functions
    raise SystemExit(main())

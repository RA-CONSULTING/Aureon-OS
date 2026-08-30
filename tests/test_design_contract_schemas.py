"""Public JSON Schema contracts for governed website-design artifacts."""

from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

from aureon.autonomous.aureon_public_website_design_runner import (
    _JOB_STATES,
    DELIVERY_JOB_SCHEMA,
    DELIVERY_VERIFICATION_SCHEMA,
    INVESTOR_COPY_REPAIR_CONTRACT_SCHEMA,
    INVESTOR_COPY_WORKER_CONTEXT_SCHEMA,
)
from aureon.autonomous.aureon_public_website_design_runner import (
    AUTHORITY as RUNNER_AUTHORITY,
)
from aureon.operator.design_candidate_claim_surface import (
    AUTHORITY as CLAIM_SURFACE_AUTHORITY,
)
from aureon.operator.design_candidate_claim_surface import (
    CLAIM_SURFACE_SCHEMA,
    MANIFEST_KINDS,
    MANIFEST_RATIONALES,
)
from aureon.operator.design_evidence_brief import (
    AUDIT_SCHEMA,
    BRIEF_SCHEMA,
    NON_AUTHORITATIVE_AUTHORITY,
)
from aureon.operator.website_operator import DESIGN_CYCLE_SCHEMA, WebsiteOperator
from tests.test_website_operator import operator_fixture as operator_fixture

REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_ROOT = REPO_ROOT / "docs" / "research" / "schemas"


def _schema(name: str) -> dict:
    return json.loads((SCHEMA_ROOT / name).read_text(encoding="utf-8"))


def _local_refs(value: object) -> set[str]:
    refs: set[str] = set()
    if isinstance(value, dict):
        ref = value.get("$ref")
        if isinstance(ref, str) and ref.startswith("#/"):
            refs.add(ref)
        for item in value.values():
            refs.update(_local_refs(item))
    elif isinstance(value, list):
        for item in value:
            refs.update(_local_refs(item))
    return refs


def _design_cycle_validator() -> Draft202012Validator:
    schema = _schema("AUREON_WEBSITE_DESIGN_JOB_V1.schema.json")
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=FormatChecker())


def _assert_schema_valid(
    validator: Draft202012Validator,
    payload: object,
) -> None:
    errors = sorted(
        validator.iter_errors(payload),
        key=lambda error: (
            tuple(str(part) for part in error.absolute_path),
            tuple(str(part) for part in error.absolute_schema_path),
        ),
    )
    assert not errors, "\n".join(
        (
            f"instance=/{'/'.join(str(part) for part in error.absolute_path)} "
            f"schema=/{'/'.join(str(part) for part in error.absolute_schema_path)} "
            f"validator={error.validator}"
        )
        for error in errors
    )


def test_design_evidence_brief_schema_matches_manifest_and_no_authority_boundary() -> None:
    schema = _schema("AUREON_DESIGN_EVIDENCE_BRIEF_V1.schema.json")
    manifest = json.loads(
        (REPO_ROOT / "data" / "website_operator" / "investor_site_design_brief.v1.json").read_text(
            encoding="utf-8"
        )
    )

    assert {entry["$ref"] for entry in schema["oneOf"]} == {
        "#/$defs/brief",
        "#/$defs/audit",
    }
    assert schema["$defs"]["brief"]["properties"]["schema"]["const"] == BRIEF_SCHEMA
    assert schema["$defs"]["audit"]["properties"]["schema"]["const"] == AUDIT_SCHEMA
    assert set(manifest) == set(schema["$defs"]["brief"]["required"])
    assert manifest["authority"] == NON_AUTHORITATIVE_AUTHORITY

    authority = schema["$defs"]["briefAuthority"]["properties"]
    assert authority["canonical_website_mutation"]["const"] == ("never by this brief or a design agent")
    assert authority["release_eligible"]["const"] is False
    assert authority["package_authority"]["const"] == "none"
    assert authority["deployment_authority"]["const"] == "none"
    assert authority["credential_access"]["const"] == "none"
    refresh = schema["$defs"]["researchRefreshBrief"]["properties"]
    assert refresh["declaration_path"]["const"] == ("data/website_operator/design_research_sources.v1.json")
    assert refresh["required_state"]["const"] == "current"
    assert refresh["required_passed"]["const"] is True
    assert refresh["artwork_state"]["const"] == "not-cleared"
    assert refresh["artwork_cleared_for_use"]["const"] is False
    assert manifest["research_refresh"]["declaration_sha256"]
    assert "research_refresh" in schema["$defs"]["audit"]["required"]


def test_design_cycle_schema_binds_copy_gate_privacy_and_release_authority() -> None:
    schema = _schema("AUREON_WEBSITE_DESIGN_JOB_V1.schema.json")
    _design_cycle_validator()

    assert schema["properties"]["schema"]["const"] == DESIGN_CYCLE_SCHEMA
    assert schema["additionalProperties"] is False
    assert {
        "evidence_controls",
        "hard_gates",
        "hard_gates_pass",
        "release_eligible",
        "authority_boundaries",
        "deployment_state",
        "summary",
    }.issubset(schema["required"])
    assert schema["properties"]["deployment_state"]["const"] == ("not-authorised-not-attempted")

    authority = schema["$defs"]["authorityBoundaries"]
    assert authority["additionalProperties"] is False
    assert authority["properties"]["credential_access"]["const"] == "none"
    assert authority["properties"]["deployment"]["const"] == "none"
    assert authority["properties"]["investor_copy_governance"]["const"] == (
        "verification and full shadow simulation are read-only; broad system "
        "access is not approval, and exact three-file application remains "
        "blocked without a fresh immutable named-owner decision plus explicit "
        "apply; no website, policy, candidate, package, release or deployment "
        "authority"
    )
    assert authority["properties"]["human_visual_acceptance_required"]["const"] is True
    assert authority["properties"]["autonomous_threshold_changes"]["const"] is False

    controls = schema["$defs"]["evidenceControls"]
    assert controls["additionalProperties"] is False
    assert "investor_copy" in controls["required"]
    assert controls["properties"]["release_eligible"]["const"] is False
    assert controls["properties"]["deployment_authority"]["const"] == "none"
    assert controls["properties"]["investor_copy"]["$ref"] == ("#/$defs/investorCopyControl")

    copy_control = schema["$defs"]["investorCopyControl"]
    assert copy_control["additionalProperties"] is False
    assert {"receipt", "binding"}.issubset(copy_control["properties"])
    assert copy_control["properties"]["release_eligible"]["const"] is False
    assert copy_control["properties"]["deployment_authority"]["const"] == "none"

    compact_receipt = schema["$defs"]["investorCopyReceipt"]
    compact_binding = schema["$defs"]["investorCopyBinding"]
    route_binding = schema["$defs"]["investorCopyRouteBinding"]
    assert compact_receipt["additionalProperties"] is False
    assert compact_binding["additionalProperties"] is False
    assert route_binding["additionalProperties"] is False
    assert compact_receipt["properties"]["schema"]["const"] == ("aureon.investor-copy-quality-audit.v1")
    assert {
        "findings",
        "text",
        "title",
        "h1",
        "message",
        "evidence",
    }.isdisjoint(compact_receipt["properties"])
    assert {"text", "title", "h1", "message", "evidence"}.isdisjoint(route_binding["properties"])
    assert {
        "policy_sha256",
        "route_hashes_sha256",
        "findings_sha256",
        "binding_sha256",
        "blocker_count",
        "warning_count",
    }.issubset(compact_binding["required"])

    hard_gates = schema["$defs"]["hardGates"]
    assert hard_gates["minContains"] == 1
    assert hard_gates["maxContains"] == 1
    assert hard_gates["contains"]["properties"]["id"]["const"] == ("investor_copy_quality_current")
    hard_gate = schema["$defs"]["hardGate"]
    investor_gate_rule = hard_gate["allOf"][0]
    assert investor_gate_rule["if"]["properties"]["id"]["const"] == ("investor_copy_quality_current")
    assert investor_gate_rule["then"]["properties"]["evidence"]["$ref"] == (
        "#/$defs/investorCopyGateEvidence"
    )
    gate_evidence = schema["$defs"]["investorCopyGateEvidence"]
    assert gate_evidence["additionalProperties"] is False
    assert gate_evidence["properties"]["release_eligible"]["const"] is False
    assert gate_evidence["properties"]["deployment_authority"]["const"] == "none"
    assert set(gate_evidence["allOf"][0]["then"]["required"]) == {
        "summary",
        "binding",
    }

    passing_contract = schema["allOf"][0]["then"]["properties"]
    assert passing_contract["state"]["const"] == ("verified-local-human-review-required")
    assert passing_contract["release_eligible"]["const"] is True
    assert passing_contract["summary"]["properties"]["ready_for_deployment"]["const"] is False

    defs = schema["$defs"]
    local_refs = _local_refs(schema)
    assert local_refs
    assert all(ref.startswith("#/$defs/") for ref in local_refs)
    assert {ref.removeprefix("#/$defs/") for ref in local_refs}.issubset(defs)


def test_design_cycle_schema_accepts_real_privacy_safe_operator_payload(
    operator_fixture: tuple[WebsiteOperator, object, dict],
) -> None:
    operator, _, _ = operator_fixture
    payload = operator.design_cycle_payload(
        "Validate one synthetic, privacy-safe WebsiteOperator design-cycle contract.",
        routes=["/"],
        run_external=False,
    )

    assert payload["schema"] == DESIGN_CYCLE_SCHEMA
    _assert_schema_valid(_design_cycle_validator(), payload)


def test_staged_delivery_runner_schema_preserves_pre_owner_boundary() -> None:
    schema = _schema("AUREON_PUBLIC_WEBSITE_DESIGN_DELIVERY_RUNNER_V1.schema.json")

    assert {entry["$ref"] for entry in schema["oneOf"]} == {
        "#/$defs/deliveryJob",
        "#/$defs/verification",
        "#/$defs/workerContext",
    }
    job = schema["$defs"]["deliveryJob"]
    verification = schema["$defs"]["verification"]
    worker_context = schema["$defs"]["workerContext"]
    authority = schema["$defs"]["runnerAuthority"]["properties"]

    assert job["properties"]["schema"]["const"] == DELIVERY_JOB_SCHEMA
    assert set(job["properties"]["state"]["enum"]) == _JOB_STATES
    assert verification["properties"]["schema"]["const"] == DELIVERY_VERIFICATION_SCHEMA
    assert authority["canonical_website_mutation"]["const"] == ("never by this runner or a design agent")
    assert authority["release_eligible"]["const"] is RUNNER_AUTHORITY["release_eligible"]
    assert authority["package_authority"]["const"] == "none"
    assert authority["deployment_authority"]["const"] == "none"
    assert authority["credential_access"]["const"] == "none"
    assert job["properties"]["release_eligible"]["const"] is False
    assert job["properties"]["package_authority"]["const"] == "none"
    assert job["properties"]["deployment_authority"]["const"] == "none"
    assert "asset_requirement" in job["required"]
    assert "delivery_contract" in job["required"]
    assert job["properties"]["asset_requirement"]["$ref"] == "#/$defs/assetRequirement"
    assert job["properties"]["delivery_contract"]["$ref"] == "#/$defs/deliveryContract"
    assert job["properties"]["investor_copy_repair"]["$ref"] == ("#/$defs/investorCopyRepairReference")
    assert job["properties"]["investor_copy_evaluation"]["$ref"] == ("#/$defs/investorCopyEvaluation")
    assert job["properties"]["asset_import"]["$ref"] == "#/$defs/assetImport"
    assert "candidate-assets-ready" in {
        state
        for item in job["allOf"]
        for state in item.get("if", {}).get("properties", {}).get("state", {}).get("enum", [])
    }
    binary_post_import_rule = next(
        item
        for item in job["allOf"]
        if "candidate-assets-ready"
        in item.get("if", {}).get("properties", {}).get("state", {}).get("enum", [])
        and "asset_import" in item.get("then", {}).get("required", [])
    )
    assert "asset_import" in binary_post_import_rule["then"]["required"]

    asset_requirement = schema["$defs"]["assetRequirement"]
    assert asset_requirement["additionalProperties"] is False
    assert asset_requirement["properties"]["trusted_import_extensions"]["const"] == [".webp"]
    assert asset_requirement["properties"]["import_operation"]["enum"] == [
        "runner-only-trusted-editorial-importer",
        "not-required-text-only",
    ]
    asset_import = schema["$defs"]["assetImport"]
    assert asset_import["additionalProperties"] is False
    assert asset_import["properties"]["state"]["const"] == "candidate-assets-ready"
    assert asset_import["properties"]["assets_ready"]["const"] is True
    assert asset_import["properties"]["release_eligible"]["const"] is False
    assert asset_import["properties"]["package_authority"]["const"] == "none"
    assert asset_import["properties"]["deployment_authority"]["const"] == "none"
    assert "authoring_contract" in asset_import["required"]
    assert asset_import["properties"]["authoring_contract"]["$ref"] == ("#/$defs/editorialAuthoringContract")
    authoring_contract = schema["$defs"]["editorialAuthoringContract"]
    assert authoring_contract["additionalProperties"] is False
    assert authoring_contract["properties"]["schema"]["const"] == (
        "aureon.public-website-editorial-authoring-contract.v1"
    )
    assert authoring_contract["properties"]["state"]["const"] == ("trusted-route-bound")
    assert {
        "surfaces_sha256",
        "trusted_evidence_sha256",
        "contract_sha256",
    }.issubset(authoring_contract["required"])
    assert schema["$defs"]["textOnlyAssetImport"]["additionalProperties"] is False

    assert {
        "asset_requirement",
        "asset_import",
        "mutation_contract",
    }.issubset(worker_context["required"])
    assert worker_context["properties"]["deployment_authority"]["const"] == "none"
    mutation_contract = schema["$defs"]["mutationContract"]
    assert mutation_contract["additionalProperties"] is False
    assert mutation_contract["properties"]["binary_read_authority"]["const"] == "none"
    assert mutation_contract["properties"]["binary_write_authority"]["const"] == "none"
    assert mutation_contract["properties"]["binary_import_authority"]["const"] == "none"
    assert mutation_contract["properties"]["canonical_write_authority"]["const"] == "none"
    assert "candidate promotion" in worker_context["properties"]["prohibited_operations"]["const"]
    assert "deployment" in worker_context["properties"]["prohibited_operations"]["const"]
    assert "binary asset read" in worker_context["properties"]["prohibited_operations"]["const"]
    assert "binary asset write" in worker_context["properties"]["prohibited_operations"]["const"]
    assert "binary asset import" in worker_context["properties"]["prohibited_operations"]["const"]
    assert worker_context["properties"]["investor_copy_repair"]["$ref"] == (
        "#/$defs/investorCopyWorkerContext"
    )
    delivery_contract = schema["$defs"]["deliveryContract"]
    assert delivery_contract["additionalProperties"] is False
    assert set(delivery_contract["required"]) == {
        "kind",
        "copy_repair_required",
    }
    assert {
        (
            branch["properties"]["kind"]["const"],
            branch["properties"]["copy_repair_required"]["const"],
        )
        for branch in delivery_contract["oneOf"]
    } == {
        ("route-bounded-design", False),
        ("investor-copy-repair", True),
    }
    copy_reference = schema["$defs"]["investorCopyRepairReference"]
    assert copy_reference["additionalProperties"] is False
    assert set(copy_reference["required"]) == {
        "schema",
        "required",
        "contract_id",
        "path",
        "sha256",
        "task_id",
        "task_sha256",
        "design_cycle_receipt_sha256",
    }
    assert copy_reference["properties"]["schema"]["const"] == (INVESTOR_COPY_REPAIR_CONTRACT_SCHEMA)
    copy_context = schema["$defs"]["investorCopyWorkerContext"]
    assert copy_context["additionalProperties"] is False
    assert set(copy_context["required"]) == {
        "schema",
        "required",
        "contract_id",
        "contract_file_sha256",
        "contract_json_sha256",
        "task_id",
        "task_sha256",
        "route",
        "path",
        "source_audit",
        "claim_control",
        "acceptance",
        "authority",
    }
    assert copy_context["properties"]["schema"]["const"] == (INVESTOR_COPY_WORKER_CONTEXT_SCHEMA)
    assert "control_passed" in schema["$defs"]["candidateValidation"]["required"]
    refresh = schema["$defs"]["researchRefreshBinding"]["properties"]
    assert refresh["declaration_path"]["const"] == ("data/website_operator/design_research_sources.v1.json")
    assert refresh["state"]["const"] == "current"
    assert refresh["passed"]["const"] is True
    assert refresh["artwork"]["properties"]["state"]["const"] == "not-cleared"
    assert refresh["artwork"]["properties"]["cleared_for_use"]["const"] is False
    assert "research_refresh" in schema["$defs"]["briefBinding"]["required"]


def test_staged_delivery_runner_schema_rejects_delivery_contract_downgrades() -> None:
    schema = _schema("AUREON_PUBLIC_WEBSITE_DESIGN_DELIVERY_RUNNER_V1.schema.json")
    contract_schema = {
        "$schema": schema["$schema"],
        "$ref": "#/$defs/deliveryContract",
        "$defs": schema["$defs"],
    }
    validator = Draft202012Validator(contract_schema)
    generic = {
        "kind": "route-bounded-design",
        "copy_repair_required": False,
    }
    copy_repair = {
        "kind": "investor-copy-repair",
        "copy_repair_required": True,
    }

    _assert_schema_valid(validator, generic)
    _assert_schema_valid(validator, copy_repair)
    assert list(
        validator.iter_errors(
            {
                "kind": "investor-copy-repair",
                "copy_repair_required": False,
            }
        )
    )
    assert list(
        validator.iter_errors(
            {
                **generic,
                "investor_copy_repair": "cannot be smuggled into the mode selector",
            }
        )
    )


def test_candidate_control_v2_schema_binds_source_selection_and_claim_boundary() -> None:
    schema = _schema("AUREON_DESIGN_CANDIDATE_CONTROL_V2.schema.json")
    work_order = schema["$defs"]["workOrder"]
    receipt = schema["$defs"]["candidateReceipt"]
    live = schema["$defs"]["liveReconciliation"]
    retained_local = schema["$defs"]["retainedLocalOwnerSourceReconciliation"]
    verified_live = schema["$defs"]["verifiedLiveBackupOwnerSourceReconciliation"]
    source = schema["$defs"]["verifiedLiveBackupCandidateSource"]
    claims = schema["$defs"]["claimSummary"]
    test_policy = schema["$defs"]["testPolicy"]
    candidate_layout = schema["$defs"]["candidateLayout"]
    work_order_binding = schema["$defs"]["candidateWorkOrderBinding"]

    assert work_order["properties"]["live_reconciliation"]["$ref"] == ("#/$defs/liveReconciliation")
    assert work_order["properties"]["claim_control"]["$ref"] == "#/$defs/claimControl"
    assert work_order["properties"]["test_policy"]["$ref"] == "#/$defs/testPolicy"
    assert work_order["properties"]["candidate_layout"]["$ref"] == "#/$defs/candidateLayout"
    assert work_order["properties"]["created_at"]["pattern"].endswith("Z$")
    assert receipt["properties"]["claims"]["$ref"] == "#/$defs/claimSummary"
    assert live["additionalProperties"] is False
    assert retained_local["additionalProperties"] is False
    assert verified_live["additionalProperties"] is False
    assert source["additionalProperties"] is False
    assert set(source["required"]) == {
        "kind",
        "root",
        "manifest_path",
        "manifest_sha256",
        "tree_sha256",
        "baseline_tree_sha256",
        "file_count",
        "total_bytes",
        "remote_root",
    }
    assert source["properties"]["kind"]["const"] == "verified-live-backup"
    assert source["properties"]["remote_root"]["const"] == "/"
    assert test_policy["additionalProperties"] is False
    assert candidate_layout["additionalProperties"] is False
    assert "file_sha256" in work_order_binding["required"]
    assert verified_live["properties"]["decision_schema"]["const"] == (
        "aureon.owner-source-reconciliation-decision.v2"
    )
    assert verified_live["properties"]["source_selection"]["const"] == ("use-verified-live-backup")
    assert claims["additionalProperties"] is False
    assert {
        "material_claim_paths",
        "bound_material_claim_paths",
        "unbound_material_claim_paths",
        "staged_register_sha256",
        "staged_register_audit",
    }.issubset(claims["required"])


def test_claim_surface_schema_preserves_hash_only_route_capsule_boundary() -> None:
    schema = _schema("AUREON_DESIGN_CANDIDATE_CLAIM_SURFACE_V1.schema.json")

    assert schema["properties"]["schema"]["const"] == CLAIM_SURFACE_SCHEMA
    assert schema["properties"]["release_eligible"]["const"] is False
    assert schema["properties"]["package_authority"]["const"] == "none"
    assert schema["properties"]["deployment_authority"]["const"] == "none"
    assert set(schema["required"]) == {
        "schema",
        "state",
        "passed",
        "release_eligible",
        "package_authority",
        "deployment_authority",
        "authority",
        "context",
        "manifest",
        "new_surfaces",
        "surface_fingerprint_sha256",
        "summary",
        "checks",
    }

    authority = schema["$defs"]["authority"]["properties"]
    assert (
        authority["canonical_website_mutation"]["const"]
        == (CLAIM_SURFACE_AUTHORITY["canonical_website_mutation"])
    )
    assert authority["credential_access"]["const"] == "none"
    assert authority["release_authority"]["const"] == "WebsiteOperator owner gate only"

    manifest = schema["$defs"]["manifestEntry"]
    assert set(manifest["required"]) == {
        "path",
        "kind",
        "claim_id",
        "text_sha256",
        "surface_sha256",
        "rationale",
    }
    assert manifest["additionalProperties"] is False
    assert set(manifest["properties"]["kind"]["enum"]) == MANIFEST_KINDS
    assert set(manifest["properties"]["rationale"]["enum"]) == MANIFEST_RATIONALES
    assert "text" not in manifest["properties"]

    surface = schema["$defs"]["newSurface"]
    assert set(surface["required"]) == {
        "path",
        "source",
        "text_sha256",
        "surface_sha256",
    }
    assert "text" not in surface["properties"]
    assert "claim_capsule" not in schema["$defs"]["context"]["properties"]
    assert "claim_capsule" in schema["$defs"]["inputContext"]["properties"]

    control = _schema("AUREON_DESIGN_CANDIDATE_CONTROL_V2.schema.json")
    receipt = control["$defs"]["candidateReceipt"]
    assert "claim_surface" in receipt["required"]
    assert receipt["properties"]["claim_surface"]["$ref"] == "#/$defs/candidateClaimSurface"
    validation_surface = control["$defs"]["candidateValidationClaimSurface"]
    assert validation_surface["properties"]["binding"]["oneOf"][1]["$ref"] == (
        f"{schema['$id']}#/$defs/inputContext"
    )

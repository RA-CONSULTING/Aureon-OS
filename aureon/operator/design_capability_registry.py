"""Read-only discovery and freshness checks for Aureon's website-design capability.

This registry is deliberately *not* a release gate.  It makes the existing
Harmonic Design Suite, coder-agent design roles, and WebsiteOperator lifecycle
methods inspectable from one small, source-bound payload.  A passing registry
only says that those repository capability declarations and controlled
source-selection protocols are present and mutually consistent; it never
authorises a package, a visual baseline, a backup, a source choice, or a
deployment.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import inspect
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Mapping, Sequence

REGISTRY_SCHEMA = "aureon.design-capability-registry.v1"
VERIFICATION_SCHEMA = "aureon.design-capability-registry-verification.v1"
WEBSITE_SOURCE_RATIONALISATION_REVIEWED_SHA256 = (
    "D79397371038912C26056A4C8A154671B0269DF54DDBBB2BAD0BE472D070DD09"
)
WEBSITE_SOURCE_RATIONALISATION_LAUNCHER_PATH = "tools/run-website-source-rationalisation.py"
WEBSITE_SOURCE_RATIONALISATION_LAUNCHER_SHA256 = (
    "827D4112E6C6042B4931E987237E1E7B6035B5A147373CDE202D9DC95184B009"
)
WEBSITE_SOURCE_RATIONALISATION_REVIEWED_BINDINGS = {
    "REVIEWED_TRUSTED_LAUNCHER_SHA256": ("827D4112E6C6042B4931E987237E1E7B6035B5A147373CDE202D9DC95184B009"),
    "REVIEWED_RELEASE_BUILDER_SHA256": ("0C42EA5FEB59DCE1583A7731189BF91223AB0F6B5DD333936BCA7E9F65438204"),
    "REVIEWED_POWERSHELL_SHA256": ("3247BCFD60F6DD25F34CB74B5889AB10EF1B3EC72B4D4B3D95B5B25B534560B8"),
    "REVIEWED_MOTION_POLICY_SHA256": ("2685C98B8D0199A30B09B3983E7F1C48DE65EF64D76E4B9900BE8F503F251A73"),
    "REVIEWED_SECURE_WRITER_SHA256": ("D704D691A4D3221E096A470884E5D1293EA663164BB6740FE5BDD26D32B4DB81"),
}
WEBSITE_RUNTIME_OPTIMISATION_REVIEWED_SHA256 = (
    "97C34F73142FC38EB14851BA7B42ACD3294F7F43AB0AF1C10E44AC8507FACD5E"
)
WEBSITE_RUNTIME_OPTIMISATION_LAUNCHER_PATH = "tools/run-website-runtime-optimisation.py"
WEBSITE_RUNTIME_OPTIMISATION_LAUNCHER_SHA256 = (
    "593A1703E31328C6A42D150C4D7AAFE8C7102D483D3A6D80134F7C46DC2B748A"
)
WEBSITE_BROWSER_ACCEPTANCE_CONTRACT_PATH = "data/website_operator/browser_acceptance_contract.v1.json"
WEBSITE_BROWSER_ACCEPTANCE_CONTRACT_SHA256 = (
    "AB8480600C4A29435D188891132882E008A57CEC02EBEC9E4B8B26B73A8C63DD"
)
WEBSITE_BROWSER_ACCEPTANCE_CONTRACT_PAYLOAD_SHA256 = (
    "25C85236E40E954B9FB75B561D7EE645E3B019027D9872E71935F5CE4276E5EC"
)
WEBSITE_RUNTIME_OPTIMISATION_MEASUREMENT_SCHEMA_PATH = (
    "docs/research/schemas/AUREON_WEBSITE_RUNTIME_OPTIMISATION_MEASUREMENT_V1.schema.json"
)
WEBSITE_RUNTIME_OPTIMISATION_MEASUREMENT_SCHEMA_SHA256 = (
    "294B5B5C3E4FC889F6433B05A6B63AE1CCDF87B318559E8CA007B275EE06A246"
)
WEBSITE_RUNTIME_OPTIMISATION_PROPOSAL_SCHEMA_PATH = (
    "docs/research/schemas/AUREON_WEBSITE_RUNTIME_OPTIMISATION_PROPOSAL_V1.schema.json"
)
WEBSITE_RUNTIME_OPTIMISATION_PROPOSAL_SCHEMA_SHA256 = (
    "7A696E815F69E5A2883BC8506DB9CFB1FD451F58F9A8AB989070B4D49D1457BB"
)
WEBSITE_RUNTIME_OPTIMISATION_REVIEWED_BINDINGS = {
    "REVIEWED_TRUSTED_LAUNCHER_SHA256": WEBSITE_RUNTIME_OPTIMISATION_LAUNCHER_SHA256,
    "REVIEWED_SOURCE_PLANNER_SHA256": WEBSITE_SOURCE_RATIONALISATION_REVIEWED_SHA256,
    "REVIEWED_SOURCE_PLANNER_LAUNCHER_SHA256": (WEBSITE_SOURCE_RATIONALISATION_LAUNCHER_SHA256),
    "REVIEWED_RELEASE_BUILDER_SHA256": (
        WEBSITE_SOURCE_RATIONALISATION_REVIEWED_BINDINGS["REVIEWED_RELEASE_BUILDER_SHA256"]
    ),
    "REVIEWED_MOTION_POLICY_SHA256": (
        WEBSITE_SOURCE_RATIONALISATION_REVIEWED_BINDINGS["REVIEWED_MOTION_POLICY_SHA256"]
    ),
    "REVIEWED_SECURE_WRITER_SHA256": (
        WEBSITE_SOURCE_RATIONALISATION_REVIEWED_BINDINGS["REVIEWED_SECURE_WRITER_SHA256"]
    ),
    "REVIEWED_ACCEPTANCE_CONTRACT_PAYLOAD_SHA256": (WEBSITE_BROWSER_ACCEPTANCE_CONTRACT_PAYLOAD_SHA256),
}
WEBSITE_RUNTIME_MEASUREMENT_STATIC_INTEGRITY_PATH = (
    "aureon/operator/website_runtime_measurement_provenance.py"
)
WEBSITE_RUNTIME_MEASUREMENT_STATIC_INTEGRITY_SHA256 = (
    "36AAF145164B7C969A97EA4802E369F1811EB82F518C2C4FBC76F28CE2CD21E5"
)
WEBSITE_RUNTIME_MEASUREMENT_STATIC_INTEGRITY_LAUNCHER_PATH = (
    "tools/run-website-runtime-measurement-provenance.py"
)
WEBSITE_RUNTIME_MEASUREMENT_STATIC_INTEGRITY_LAUNCHER_SHA256 = (
    "85B099FD044CE0A409806E8936494E2CE25AE9CF47BF45E05057BF88D9CF25BE"
)
WEBSITE_RUNTIME_MEASUREMENT_STATIC_INTEGRITY_SCHEMA_PATH = (
    "docs/research/schemas/AUREON_WEBSITE_RUNTIME_MEASUREMENT_STATIC_INTEGRITY_V1.schema.json"
)
WEBSITE_RUNTIME_MEASUREMENT_STATIC_INTEGRITY_SCHEMA_SHA256 = (
    "5AA39AF8822DE7DADE86D696C2A996A3EF036FD2342FBF999E97E032DBFFE8D1"
)

DESIGN_COUNCIL_ROLES = (
    "Website Design Director",
    "Competitor Research Scout",
    "Brand and Design-System Lead",
    "Technical Editorial Writer",
    "Claims and Evidence Editor",
    "Stakeholder Insight & Privacy Editor",
    "Motion Designer",
    "Visual Asset Director",
    "Accessibility and Performance QA",
    "Design Release QA",
)

CODING_DESIGN_ROLES = (
    "PublicWebsiteDesignWorker",
    "PublicWebsiteDesignQA",
)

WEBSITE_OPERATOR_CAPABILITIES = (
    ("site-audit", "audit", "audit"),
    ("live-surface-reconciliation", "observe", "observe_live_surface"),
    ("research-route-layout-attribution", "diagnose", "research_hydration_attribution"),
    ("owner-source-reconciliation", "reconcile", "create_candidate_work_order"),
    ("design-nexus-cycle", "design", "design_cycle"),
    ("bounded-work-order", "design", "work_order"),
    ("staged-candidate-work-order", "design", "create_candidate_work_order"),
    ("staged-candidate-staging", "design", "stage_candidate"),
    ("staged-candidate-validation", "design", "validate_candidate"),
    ("staged-candidate-visual-review", "design", "verify_candidate_prepromotion_review"),
    ("design-learning-record", "design", "record_design_learning"),
    ("release-builder", "build", "build_release"),
    ("backup-preflight", "backup", "backup_preflight"),
    ("backup-verification", "backup", "verify_backup"),
    ("owner-gate", "release-control", "gate_deployment"),
    ("explicit-deploy", "deploy", "deploy"),
    ("live-hash-readback", "verify", "readback"),
)

SOURCE_SPECS = (
    (
        "harmonic-design-suite",
        "skills/aureon-harmonic-design-suite/SKILL.md",
        ("# Aureon Harmonic Design Suite", "Website Design Director", "human visual acceptance"),
    ),
    (
        "design-cycle-runner",
        "skills/aureon-harmonic-design-suite/scripts/run_design_cycle.py",
        ("WebsiteOperator", "design_cycle"),
    ),
    (
        "website-operator",
        "aureon/operator/website_operator.py",
        ("class WebsiteOperator", "def design_cycle", "def gate_deployment", "def deploy"),
    ),
    (
        "live-surface-reconciliation",
        "aureon/operator/live_surface_reconciliation.py",
        ("RECONCILIATION_SCHEMA", "reconcile_live_surface", "write_live_surface_reconciliation"),
    ),
    (
        "research-hydration-attribution",
        "tools/aureon_research_hydration_attribution.js",
        ("correlateHydration", "runAttribution", "analysis_only"),
    ),
    (
        "owner-source-reconciliation",
        "aureon/operator/owner_source_reconciliation.py",
        (
            "OWNER_SOURCE_RECONCILIATION_SCHEMA",
            "OWNER_VERIFIED_LIVE_BACKUP_RECONCILIATION_SCHEMA",
            "OWNER_SOURCE_RECONCILIATION_VALIDATION_SCHEMA",
            "OWNER_VERIFIED_LIVE_BACKUP_RECONCILIATION_VALIDATION_SCHEMA",
            "OWNER_SOURCE_RECONCILIATION_AUTHORITY",
            "OWNER_VERIFIED_LIVE_BACKUP_RECONCILIATION_AUTHORITY",
            "validate_owner_source_reconciliation",
        ),
    ),
    (
        "website-source-rationalisation",
        "aureon/operator/website_source_rationalisation.py",
        (
            "PLAN_SCHEMA",
            "OWNER_DECISION_SCHEMA",
            "create_source_rationalisation_plan",
            "validate_owner_source_rationalisation_decision",
            "There is no source-copy, file-removal",
        ),
    ),
    (
        "website-source-rationalisation-launcher",
        "tools/run-website-source-rationalisation.py",
        (
            "Isolated, package-free trust bootstrap",
            "--expected-launcher-sha256",
            "__aureon_trusted_launcher_attestation__",
        ),
    ),
    (
        "website-source-rationalisation-runbook",
        "docs/runbooks/WEBSITE_SOURCE_RATIONALISATION.md",
        (
            "# Website source rationalisation",
            "proposal-only",
            "owner-decision-validated-review-only",
        ),
    ),
    (
        "website-runtime-optimisation",
        "aureon/operator/website_runtime_optimisation.py",
        (
            "MEASUREMENT_SCHEMA",
            "PROPOSAL_SCHEMA",
            "PRODUCTION_MEASUREMENT_PROVENANCE_STATE",
            "compile_runtime_optimisation_proposal",
            "require_runtime_optimisation_proposal",
            "no encoder, CSS transformer",
        ),
    ),
    (
        "website-runtime-optimisation-launcher",
        "tools/run-website-runtime-optimisation.py",
        (
            "Isolated, package-free trust bootstrap",
            "--expected-launcher-sha256",
            "__aureon_runtime_optimisation_launcher_attestation__",
        ),
    ),
    (
        "website-browser-acceptance-contract",
        "data/website_operator/browser_acceptance_contract.v1.json",
        (
            "aureon.browser-acceptance-contract.v1",
            "AUREON-WEB-V29-OPTIMISATION-ACCEPTANCE",
            "release-blocking",
            "payloadSha256",
        ),
    ),
    (
        "website-runtime-optimisation-measurement-schema",
        "docs/research/schemas/AUREON_WEBSITE_RUNTIME_OPTIMISATION_MEASUREMENT_V1.schema.json",
        (
            "https://json-schema.org/draft/2020-12/schema",
            "aureon.website-runtime-optimisation-measurement-evidence.v1",
            "measurement-only",
            "source_selection_authority",
        ),
    ),
    (
        "website-runtime-optimisation-proposal-schema",
        "docs/research/schemas/AUREON_WEBSITE_RUNTIME_OPTIMISATION_PROPOSAL_V1.schema.json",
        (
            "https://json-schema.org/draft/2020-12/schema",
            "aureon.website-runtime-optimisation-proposal.v1",
            "proposal-only",
            "blocked-not-run",
        ),
    ),
    (
        "website-runtime-optimisation-runbook",
        "docs/runbooks/WEBSITE_RUNTIME_OPTIMISATION.md",
        (
            "# Website runtime optimisation control plane (production blocked)",
            "Production proposal compilation and writing",
            "blocked-not-run",
            "PublicWebsiteDesignWorker",
        ),
    ),
    (
        "website-runtime-measurement-static-integrity",
        "aureon/operator/website_runtime_measurement_provenance.py",
        (
            "aureon.website-runtime-measurement-static-integrity.v1",
            "static-integrity-verified-production-blocked",
            "def verify_measurement_provenance_file",
            "no encoder, subprocess, writer, emitter",
        ),
    ),
    (
        "website-runtime-measurement-static-integrity-launcher",
        "tools/run-website-runtime-measurement-provenance.py",
        (
            "Isolated byte-binding bootstrap",
            "--expected-launcher-sha256",
            "--expected-module-sha256",
            "__aureon_runtime_measurement_provenance_launcher_attestation__",
        ),
    ),
    (
        "website-runtime-measurement-static-integrity-schema",
        "docs/research/schemas/AUREON_WEBSITE_RUNTIME_MEASUREMENT_STATIC_INTEGRITY_V1.schema.json",
        (
            "https://json-schema.org/draft/2020-12/schema",
            "aureon.website-runtime-measurement-static-integrity.v1",
            "static-artifact-integrity-only",
            "eligible_for_proposal_compilation",
        ),
    ),
    (
        "design-candidate-control",
        "aureon/operator/design_candidate_control.py",
        ("WORK_ORDER_SCHEMA", "stage_design_candidate", "validate_design_candidate"),
    ),
    (
        "design-candidate-claim-surface",
        "aureon/operator/design_candidate_claim_surface.py",
        ("CLAIM_SURFACE_SCHEMA", "MANIFEST_KINDS", "evaluate_candidate_claim_surface"),
    ),
    (
        "design-research-refresh",
        "aureon/operator/design_research_refresh.py",
        ("REFRESH_RECEIPT_SCHEMA", "audit_design_research_sources_file", "not-cleared"),
    ),
    (
        "design-research-source-declaration",
        "data/website_operator/design_research_sources.v1.json",
        ("aureon.design-research-sources.v1", "not-cleared", "deployment_authority"),
    ),
    (
        "design-stakeholder-feedback",
        "aureon/operator/design_stakeholder_feedback.py",
        (
            "FEEDBACK_AUDIT_SCHEMA",
            "audit_design_stakeholder_feedback_file",
            "raw_correspondence_access",
        ),
    ),
    (
        "design-stakeholder-feedback-declaration",
        "data/website_operator/design_stakeholder_feedback.v1.json",
        (
            "aureon.design-stakeholder-feedback.v1",
            "raw_correspondence_access",
            "deployment_authority",
        ),
    ),
    (
        "design-editorial-asset-provenance",
        "aureon/operator/design_editorial_asset_provenance.py",
        (
            "AUDIT_SCHEMA",
            "audit_design_editorial_asset_provenance_file",
            "GLOBAL_NOT_CLEARED_POLICY",
            "asset_capsules_sha256",
        ),
    ),
    (
        "design-editorial-asset-provenance-declaration",
        "data/website_operator/editorial_asset_provenance.v1.json",
        (
            "aureon.design-editorial-asset-provenance.v1",
            "not-cleared",
            "named_human_decision",
            "deployment_authority",
        ),
    ),
    (
        "design-editorial-rights-decision-preparation",
        "aureon/operator/design_editorial_asset_provenance.py",
        (
            "RIGHTS_PREPARATION_REQUEST_SCHEMA",
            "RIGHTS_BINDING_PROPOSAL_SCHEMA",
            "RIGHTS_PREPARATION_AUTHORITY",
            "prepare_editorial_asset_rights_decisions",
            "rights_inference",
        ),
    ),
    (
        "design-editorial-asset-candidate-importer",
        "aureon/operator/design_editorial_asset_candidate_importer.py",
        (
            "IMPORT_RECEIPT_SCHEMA",
            "import_editorial_assets_to_candidate",
            "verify_candidate_editorial_asset_import",
            "write_candidate_editorial_asset_import",
            "canonical_website_mutation",
        ),
    ),
    (
        "investor-copy-quality-control",
        "aureon/operator/design_investor_copy_quality.py",
        (
            "AUDIT_SCHEMA",
            "audit_investor_copy_quality_file",
            "static-traction-count",
            "canonical_website_mutation",
        ),
    ),
    (
        "investor-copy-quality-policy",
        "data/website_operator/investor_copy_quality_policy.v1.json",
        (
            "aureon.investor-copy-quality-policy.v1",
            "category-language",
            "static-traction-count",
            "deployment_authority",
        ),
    ),
    (
        "investor-copy-repair-contract",
        "aureon/operator/design_investor_copy_repair.py",
        (
            "CONTRACT_SCHEMA",
            "PREFLIGHT_SCHEMA",
            "EVALUATION_SCHEMA",
            "preflight_investor_copy_repair_contract",
            "preflight_investor_copy_repair_work_order",
            "verify_investor_copy_repair_contract",
            "evaluate_investor_copy_repair_candidate",
            "source-bound",
        ),
    ),
    (
        "investor-copy-governance-application",
        "aureon/operator/design_investor_copy_governance.py",
        (
            "DECISION_SCHEMA",
            "NON_RELEASE_AUTHORITY",
            "broad_system_access_is_not_this_decision",
            "verify_investor_copy_governance_decision",
            "plan_investor_copy_governance_application",
            "apply_investor_copy_governance_delta",
        ),
    ),
    (
        "hnc-evidence-control-graph",
        "aureon/operator/design_hnc_evidence_graph.py",
        (
            "CONTRACT_SCHEMA",
            "audit_hnc_evidence_graph_contract_file",
            "write_hnc_evidence_graph_bundle",
            "candidate_mutation",
        ),
    ),
    (
        "hnc-evidence-control-graph-contract",
        "data/website_operator/hnc_evidence_graph.v1.json",
        (
            "aureon.hnc-evidence-graph-contract.v1",
            "after-homepage-proof-rail",
            "static-complete",
            "deployment_authority",
        ),
    ),
    (
        "design-evidence-brief",
        "aureon/operator/design_evidence_brief.py",
        ("BRIEF_SCHEMA", "audit_design_evidence_brief_file", "planning evidence only"),
    ),
    (
        "staged-design-delivery-runner",
        "aureon/autonomous/aureon_public_website_design_runner.py",
        (
            'DELIVERY_JOB_SCHEMA = "aureon.public-website-design-delivery-job.v2"',
            'CANDIDATE_QA_SCHEMA = "aureon.public-website-design-candidate-qa.v2"',
            "evaluate_delivery_candidate_qa",
            "SEALED_COMPILER_PYTHON_FLAGS",
            "_BoundedProcessResult",
            "_sealed_compiler_environment",
            "_stop_sealed_process",
            "_run_bounded_sealed_process",
            "_verify_compiled_candidate_motion_config_file_sealed",
            "_verify_compiled_candidate_test_policy_file_sealed",
            "candidate-qa-verified",
            "awaiting-owner-promotion",
        ),
    ),
    (
        "staged-design-delivery-v2-schema",
        "docs/research/schemas/AUREON_PUBLIC_WEBSITE_DESIGN_DELIVERY_RUNNER_V2.schema.json",
        (
            "Aureon staged public website design delivery runner V2",
            "aureon.public-website-design-delivery-job.v2",
            "candidate-qa-verified",
            "historical-v1-read-only",
        ),
    ),
    (
        "staged-design-delivery-v2-runbook",
        "docs/research/AUREON_PUBLIC_WEBSITE_DESIGN_DELIVERY_V2_RUNBOOK.md",
        (
            "# Aureon public website staged-delivery V2 runbook",
            "fixed compiler",
            "motion passes",
            "initial browser gate",
        ),
    ),
    (
        "staged-design-worker-broker",
        "aureon/autonomous/aureon_staged_design_worker_broker.py",
        (
            "LEASE_SCHEMA",
            "issue_staged_design_worker_lease",
            "submit_staged_design_worker_delivery",
            "credential_access",
        ),
    ),
    (
        "design-candidate-visual-review",
        "aureon/operator/design_candidate_visual_review.py",
        ("VISUAL_REVIEW_SCHEMA", "validate_candidate_visual_review"),
    ),
    (
        "design-candidate-initial-gate",
        "aureon/operator/design_candidate_initial_gate.py",
        ("INITIAL_GATE_SCHEMA", "evaluate_initial_candidate_gate", "write_initial_candidate_gate"),
    ),
    (
        "design-motion-performance-budget",
        "aureon/operator/design_motion_performance_budget.py",
        (
            "CONFIG_SCHEMA",
            "RECEIPT_SCHEMA",
            "audit_motion_performance_budget",
            "validate_motion_performance_receipt",
            "eligible_for_next_local_gate",
        ),
    ),
    (
        "design-motion-performance-budget-runbook",
        "docs/runbooks/DESIGN_MOTION_PERFORMANCE_BUDGET.md",
        (
            "# Design motion and performance budget",
            "A passing result is local",
            "human visual acceptance",
        ),
    ),
    (
        "secure-immutable-artifact",
        "aureon/operator/secure_immutable_artifact.py",
        (
            "Handle-bound exclusive creation",
            "def write_new_file",
            "same handle",
        ),
    ),
    (
        "secure-immutable-artifact-runbook",
        "docs/runbooks/SECURE_IMMUTABLE_ARTIFACT.md",
        (
            "# Secure immutable artifact creation",
            "kernel-resolved final path",
            "same-handle byte read-back",
        ),
    ),
    (
        "design-candidate-static-qa",
        "aureon/operator/design_candidate_static_qa.py",
        (
            'SCHEMA = "aureon.design-candidate-static-qa.v1"',
            "def audit_candidate_static",
            "candidate_mutation",
            "v28-composite-visual-release-gate-not-satisfied",
        ),
    ),
    (
        "design-candidate-static-qa-runbook",
        "docs/runbooks/DESIGN_CANDIDATE_STATIC_QA.md",
        (
            "# Read-only staged-candidate static QA",
            "candidate.website-operator-static.v1",
            "v28-composite-visual-release-gate",
        ),
    ),
    (
        "design-candidate-test-policy-compiler",
        "aureon/operator/design_candidate_test_policy_compiler.py",
        (
            "deterministic, non-worker-selectable candidate test policy",
            "REQUIRED_COMMAND_IDS",
            "SOURCE_CLOSURE_SCHEMA",
            "_SEALED_CLI_FLAGS",
            "--verify-policy",
            "imported API is drift-check-only",
            "worker_command_selection",
            "deferred-not-passed",
        ),
    ),
    (
        "design-candidate-test-policy-compiler-runbook",
        "docs/runbooks/DESIGN_CANDIDATE_TEST_POLICY_COMPILER.md",
        (
            "# Candidate test policy compiler",
            "A design",
            "worker cannot supply command ids",
            "complete ordered executable suite",
        ),
    ),
    (
        "design-candidate-motion-policy-compiler",
        "aureon/operator/design_candidate_motion_policy_compiler.py",
        (
            "one fixed motion/performance configuration",
            "FIXED_THRESHOLDS",
            "SOURCE_CLOSURE_SCHEMA",
            "_SEALED_CLI_FLAGS",
            "--verify-config",
            "imported API is drift-check-only",
            "worker_threshold_selection",
            "audit_execution_authority",
        ),
    ),
    (
        "design-candidate-source-closure",
        "aureon/operator/design_candidate_source_closure.py",
        (
            'SOURCE_CLOSURE_SCHEMA = "aureon.design-candidate-executable-source-closure.v1"',
            'SOURCE_CLOSURE_ALGORITHM = "python-ast-local-raw-sha256-closure-v2"',
            "def build_source_closure",
            "def verify_source_closure",
            "def install_verified_source_importer",
        ),
    ),
    (
        "design-candidate-motion-policy-compiler-runbook",
        "docs/runbooks/DESIGN_CANDIDATE_MOTION_POLICY_COMPILER.md",
        (
            "# Candidate motion-policy compiler",
            "prevents",
            "threshold shopping",
            "shared handle-bound immutable-artifact writer",
        ),
    ),
    (
        "design-candidate-test-evidence",
        "aureon/operator/design_candidate_test_evidence.py",
        (
            "POLICY_SCHEMA",
            "RECEIPT_SCHEMA",
            "VERIFICATION_SCHEMA",
            "NODE_TOOLCHAIN_BINDING",
            "NODE_TOOLCHAIN_BINDING_SHA256",
            "_resolve_reviewed_node_toolchain",
            "_run_process_once",
            "origin_attested",
            "trusted_orchestration_seal_required",
            "evidence_passed",
        ),
    ),
    (
        "design-candidate-test-evidence-runbook",
        "docs/runbooks/DESIGN_CANDIDATE_TEST_EVIDENCE.md",
        (
            "# Trusted staged-candidate test evidence",
            "A design worker's statement that tests passed is not test evidence.",
            "origin_attested: false",
            "evidence_passed: true",
        ),
    ),
    (
        "design-learning-ledger",
        "aureon/operator/design_learning_ledger.py",
        ("LEARNING_RECORD_SCHEMA", "validate_design_learning_record", "write_design_learning_record"),
    ),
    (
        "coding-agent-skill-base",
        "aureon/autonomous/aureon_coding_agent_skill_base.py",
        ("def public_website_design_skill_stack", "PublicWebsiteDesignWorker", "PublicWebsiteDesignQA"),
    ),
)

NON_AUTHORITATIVE_AUTHORITY = {
    "registry_scope": "read-only repository capability discovery and freshness verification",
    "release_eligibility": "always-false",
    "deployment_authority": "none",
    "human_visual_acceptance": "required for material brand changes",
    "release_authority": "WebsiteOperator owner gate only",
    "credential_access": "never available to design agents or this registry",
}

EXPECTED_CANDIDATE_QA_ORDER = (
    "compile-fixed-motion-config",
    "compile-fixed-test-policy",
    "run-motion-budget-first",
    "run-complete-trusted-test-policy",
    "enter-initial-browser-gate-only-after-qa-verification",
)

EXPECTED_COMPILER_EXECUTABLE_SOURCE_INGRESS = (
    "sealed only by direct compiler-file execution; imported API is drift-check-only"
)
EXPECTED_SEALED_COMPILER_PYTHON_FLAGS = ("-I", "-S", "-B")
EXPECTED_SOURCE_CLOSURE_SCHEMA = "aureon.design-candidate-executable-source-closure.v1"
EXPECTED_SOURCE_CLOSURE_ALGORITHM = "python-ast-local-raw-sha256-closure-v2"
EXPECTED_MOTION_VERIFY_FLAG = "--verify-config"
EXPECTED_TEST_VERIFY_FLAG = "--verify-policy"
EXPECTED_NODE_BINDING_SCHEMA = "aureon.node-toolchain-binding.v1"
EXPECTED_NODE_LOCATOR_AUTHORITY = "reviewed-source-pinned-absolute-path-no-path-fallback"
EXPECTED_TEST_EVIDENCE_MAX_STREAM_BYTES = 2 * 1024 * 1024
EXPECTED_SEALED_COMPILER_MAX_OUTPUT_BYTES = 64 * 1024
EXPECTED_SEALED_COMPILER_TIMEOUT_SECONDS = 300

EXPECTED_CANDIDATE_TEST_COMMAND_IDS = (
    "candidate.website-operator-static.v1",
    "candidate.javascript-syntax.v1",
    "candidate.v28-design-system-static.v1",
    "candidate.v28-metadata-ethos-static.v1",
)

EXPECTED_CANDIDATE_MOTION_THRESHOLDS = {
    "max_total_bytes": 4_500_000,
    "max_html_bytes": 750_000,
    "max_css_bytes": 350_000,
    "max_javascript_bytes": 300_000,
    "max_image_bytes": 2_200_000,
    "max_font_bytes": 750_000,
    "max_media_bytes": 0,
    "max_other_bytes": 250_000,
    "max_single_asset_bytes": 500_000,
    "max_animation_duration_ms": 800,
    "min_transition_duration_ms": 80,
    "max_transition_duration_ms": 500,
    "max_reduced_motion_duration_ms": 1,
    "max_animation_declarations": 24,
    "max_transition_declarations": 80,
    "max_remote_resource_references": 0,
    "max_embedded_data_bytes": 0,
}

EXPECTED_CANDIDATE_MOTION_POLICY = {
    "autoplay_media": "forbid",
    "infinite_animation": "forbid",
    "dynamic_motion": "forbid",
    "reduced_motion_override": "required",
    "undeclared_remote_origins": "forbid",
}


class DesignCapabilityRegistryError(ValueError):
    """A registry input is invalid or cannot be verified safely."""


def _utc_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while True:
            chunk = stream.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest().upper()


def _find_repo_root(start: Path | None = None) -> Path:
    candidate = (start or Path.cwd()).resolve()
    for root in (candidate, *candidate.parents):
        if (root / "pyproject.toml").is_file() and (root / "aureon").is_dir():
            return root
    raise DesignCapabilityRegistryError(
        "Could not locate an Aureon repository with pyproject.toml and aureon/."
    )


def _safe_source_path(repo_root: Path, value: object) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise DesignCapabilityRegistryError("A registry source path must be a non-empty relative path.")
    normalised = value.replace("\\", "/")
    relative = Path(normalised)
    if relative.is_absolute() or any(part in {"", ".", ".."} for part in relative.parts):
        raise DesignCapabilityRegistryError(f"Unsafe registry source path: {value}")
    candidate = (repo_root / relative).resolve()
    try:
        candidate.relative_to(repo_root.resolve())
    except ValueError as exc:
        raise DesignCapabilityRegistryError(f"Registry source path escapes the repository: {value}") from exc
    return candidate


def _source_snapshot(
    repo_root: Path,
    identifier: str,
    relative_path: str,
    required_markers: Sequence[str],
) -> dict[str, Any]:
    path = _safe_source_path(repo_root, relative_path)
    record: dict[str, Any] = {
        "id": identifier,
        "path": relative_path,
        "required_markers": list(required_markers),
        "available": path.is_file(),
        "sha256": "",
        "markers_present": {},
    }
    if not path.is_file():
        return record
    text = path.read_text(encoding="utf-8", errors="replace")
    record["sha256"] = _sha256(path)
    record["markers_present"] = {marker: marker in text for marker in required_markers}
    return record


def _source_text(repo_root: Path, relative_path: str) -> str:
    path = _safe_source_path(repo_root, relative_path)
    return path.read_text(encoding="utf-8", errors="replace") if path.is_file() else ""


def _module_tree(repo_root: Path, relative_path: str) -> ast.Module | None:
    text = _source_text(repo_root, relative_path)
    if not text:
        return None
    try:
        return ast.parse(text, filename=relative_path)
    except SyntaxError:
        return None


def _function_literal_return(tree: ast.Module | None, function_name: str) -> Mapping[str, Any] | None:
    if tree is None:
        return None
    for node in tree.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) or node.name != function_name:
            continue
        for child in ast.walk(node):
            if not isinstance(child, ast.Return) or child.value is None:
                continue
            try:
                value = ast.literal_eval(child.value)
            except (ValueError, TypeError):
                continue
            if isinstance(value, Mapping):
                return value
    return None


def _design_council_roles(repo_root: Path) -> list[dict[str, Any]]:
    tree = _module_tree(repo_root, "aureon/autonomous/aureon_coding_agent_skill_base.py")
    stack = _function_literal_return(tree, "public_website_design_skill_stack") or {}
    levels = stack.get("levels")
    roles = levels.get("L4_role") if isinstance(levels, Mapping) else None
    if not isinstance(roles, list):
        return []
    return [
        {
            "name": role,
            "declared_by": "public_website_design_skill_stack",
            "source": "skills/aureon-harmonic-design-suite/SKILL.md",
            "available": True,
        }
        for role in roles
        if isinstance(role, str) and role.strip()
    ]


def _literal_keyword(call: ast.Call, name: str) -> str:
    for keyword in call.keywords:
        if keyword.arg != name:
            continue
        try:
            value = ast.literal_eval(keyword.value)
        except (ValueError, TypeError):
            return ""
        return value if isinstance(value, str) else ""
    return ""


def _coding_roles(repo_root: Path) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    tree = _module_tree(repo_root, "aureon/autonomous/aureon_coding_agent_skill_base.py")
    if tree is None:
        return selected
    functions = [
        node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == "coder_agent_roles"
    ]
    for function in functions:
        for node in ast.walk(function):
            if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name):
                continue
            if node.func.id != "CoderAgentRole":
                continue
            name = _literal_keyword(node, "name")
            if name not in CODING_DESIGN_ROLES:
                continue
            purpose = _literal_keyword(node, "purpose")
            safety_boundary = _literal_keyword(node, "safety_boundary")
            if not name or not purpose or not safety_boundary:
                continue
            selected.append(
                {
                    "name": name,
                    "purpose": purpose,
                    "safety_boundary": safety_boundary,
                    "declared_by": "coder_agent_roles",
                    "source": "aureon/autonomous/aureon_coding_agent_skill_base.py",
                    "available": True,
                }
            )
    return selected


def _website_operator_method_names(repo_root: Path) -> set[str]:
    tree = _module_tree(repo_root, "aureon/operator/website_operator.py")
    if tree is None:
        return set()
    for node in tree.body:
        if not isinstance(node, ast.ClassDef) or node.name != "WebsiteOperator":
            continue
        return {
            child.name for child in node.body if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef))
        }
    return set()


def _operator_capabilities(repo_root: Path) -> list[dict[str, Any]]:
    methods = _website_operator_method_names(repo_root)
    return [
        {
            "id": identifier,
            "category": category,
            "method": method,
            "available": method in methods,
            "source": "aureon/operator/website_operator.py",
        }
        for identifier, category, method in WEBSITE_OPERATOR_CAPABILITIES
    ]


def owner_source_reconciliation_readiness(repo_root: Path) -> dict[str, Any]:
    """Expose installed v1/v2 validation without selecting a source.

    This is static, read-only protocol discovery. It does not create an owner
    decision, inspect a backup, stage a candidate, or choose between the local
    canonical tree and a verified live backup.
    """

    unavailable: dict[str, Any] = {
        "available": False,
        "installed": False,
        "state": "unavailable",
        "validation_protocol_available": False,
        "v1_retain_local_supported": False,
        "v2_verified_live_backup_supported": False,
        "owner_decision_required": True,
        "autonomous_source_selection": False,
        "candidate_delivery_ready": False,
        "canonical_website_mutation": "none",
        "release_eligible": False,
        "package_authority": "none",
        "deployment_authority": "none",
        "credential_access": "none",
        "release_authority": "WebsiteOperator owner gate only",
        "max_decision_age_seconds": 0,
        "source_modes": {},
        "error": "",
    }
    source_file = _safe_source_path(
        repo_root,
        "aureon/operator/owner_source_reconciliation.py",
    )
    try:
        from aureon.operator import owner_source_reconciliation as reconciliation
    except Exception as exc:
        unavailable["installed"] = source_file.is_file()
        unavailable["error"] = f"{type(exc).__name__}: {exc}"
        return unavailable

    v1_authority = reconciliation.OWNER_SOURCE_RECONCILIATION_AUTHORITY
    v2_authority = reconciliation.OWNER_VERIFIED_LIVE_BACKUP_RECONCILIATION_AUTHORITY

    def retains_boundary(authority: object) -> bool:
        return (
            isinstance(authority, Mapping)
            and authority.get("canonical_website_mutation") == "none by this decision or a design agent"
            and authority.get("release_eligible") is False
            and authority.get("package_authority") == "none"
            and authority.get("deployment_authority") == "none"
            and authority.get("credential_access") == "none"
            and authority.get("release_authority") == "WebsiteOperator owner gate only"
        )

    max_age_seconds = int(reconciliation.MAX_OWNER_SOURCE_DECISION_AGE.total_seconds())
    protocol_available = (
        source_file.is_file()
        and reconciliation.OWNER_SOURCE_RECONCILIATION_SCHEMA
        == "aureon.owner-source-reconciliation-decision.v1"
        and reconciliation.OWNER_VERIFIED_LIVE_BACKUP_RECONCILIATION_SCHEMA
        == "aureon.owner-source-reconciliation-decision.v2"
        and reconciliation.OWNER_SOURCE_RECONCILIATION_VALIDATION_SCHEMA
        == "aureon.owner-source-reconciliation-validation.v1"
        and reconciliation.OWNER_VERIFIED_LIVE_BACKUP_RECONCILIATION_VALIDATION_SCHEMA
        == "aureon.owner-source-reconciliation-validation.v2"
        and retains_boundary(v1_authority)
        and retains_boundary(v2_authority)
        and 0 < max_age_seconds <= 4 * 60 * 60
        and callable(reconciliation.validate_owner_source_reconciliation)
    )
    return {
        "available": protocol_available,
        "installed": True,
        "state": "installed-owner-decision-required" if protocol_available else "protocol-blocked",
        "validation_protocol_available": protocol_available,
        "v1_retain_local_supported": protocol_available,
        "v2_verified_live_backup_supported": protocol_available,
        "owner_decision_required": True,
        "autonomous_source_selection": False,
        "candidate_delivery_ready": False,
        "canonical_website_mutation": "none",
        "release_eligible": False,
        "package_authority": "none",
        "deployment_authority": "none",
        "credential_access": "none",
        "release_authority": "WebsiteOperator owner gate only",
        "max_decision_age_seconds": max_age_seconds,
        "source_modes": {
            "v1": {
                "schema": reconciliation.OWNER_SOURCE_RECONCILIATION_SCHEMA,
                "selection": "retain-local-canonical-source",
                "verified_live_backup_selected": False,
            },
            "v2": {
                "schema": reconciliation.OWNER_VERIFIED_LIVE_BACKUP_RECONCILIATION_SCHEMA,
                "selection": "use-verified-live-backup",
                "verified_live_backup_selected": True,
            },
        },
        "error": "",
    }


def website_source_rationalisation_readiness(repo_root: Path) -> dict[str, Any]:
    """Expose the installed protocol by AST inspection only.

    The target module is not imported. Discovery therefore cannot execute its
    import-time code, planner, decision validator, subprocess, or writer before
    the registry has authenticated the source snapshot.
    """

    unavailable: dict[str, Any] = {
        "available": False,
        "installed": False,
        "state": "unavailable",
        "planning_protocol_available": False,
        "decision_validation_protocol_available": False,
        "plan_executed": False,
        "decision_validation_executed": False,
        "discovery_mode": "metadata-only-ast-no-import-no-subprocess",
        "module_imported": False,
        "owner_decision_required": True,
        "autonomous_owner_decision": False,
        "staging_implemented": False,
        "canonical_website_mutation": "none",
        "physical_source_file_removal": "none",
        "candidate_authority": "none",
        "package_authority": "none",
        "release_eligible": False,
        "deployment_authority": "none",
        "credential_access": "none",
        "network_access": "none",
        "max_decision_age_seconds": 0,
        "fixed_footprint_limits": {},
        "source_sha256": "",
        "expected_source_sha256": WEBSITE_SOURCE_RATIONALISATION_REVIEWED_SHA256,
        "source_hash_matches": False,
        "reviewed_bindings": {},
        "public_signatures_locked": False,
        "repo_code_imported": False,
        "launcher_path": WEBSITE_SOURCE_RATIONALISATION_LAUNCHER_PATH,
        "launcher_sha256": "",
        "expected_launcher_sha256": WEBSITE_SOURCE_RATIONALISATION_LAUNCHER_SHA256,
        "launcher_hash_matches": False,
        "launcher_repo_code_imported": False,
        "error": "",
    }
    source_file = _safe_source_path(
        repo_root,
        "aureon/operator/website_source_rationalisation.py",
    )
    launcher_file = _safe_source_path(
        repo_root,
        WEBSITE_SOURCE_RATIONALISATION_LAUNCHER_PATH,
    )
    tree = _module_tree(repo_root, "aureon/operator/website_source_rationalisation.py")
    launcher_tree = _module_tree(repo_root, WEBSITE_SOURCE_RATIONALISATION_LAUNCHER_PATH)
    if tree is None or launcher_tree is None or not source_file.is_file() or not launcher_file.is_file():
        unavailable["installed"] = source_file.is_file()
        unavailable["error"] = (
            "Source-rationalisation module or isolated launcher is missing or is not valid Python."
        )
        return unavailable

    def literal_assignment(name: str) -> object:
        for node in tree.body:
            value_node: ast.expr | None = None
            if (
                isinstance(node, ast.Assign)
                and any(isinstance(target, ast.Name) and target.id == name for target in node.targets)
            ) or (
                isinstance(node, ast.AnnAssign)
                and isinstance(node.target, ast.Name)
                and node.target.id == name
            ):
                value_node = node.value
            if value_node is not None:
                if (
                    isinstance(value_node, ast.Call)
                    and isinstance(value_node.func, ast.Name)
                    and value_node.func.id == "MappingProxyType"
                    and len(value_node.args) == 1
                    and not value_node.keywords
                ):
                    value_node = value_node.args[0]
                try:
                    return ast.literal_eval(value_node)
                except (ValueError, TypeError):
                    return None
        return None

    functions = {
        node.name: node for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    function_names = set(functions)

    def parameter_names(name: str) -> set[str] | None:
        node = functions.get(name)
        if node is None or node.args.vararg is not None or node.args.kwarg is not None:
            return None
        return {
            argument.arg
            for argument in (
                *node.args.posonlyargs,
                *node.args.args,
                *node.args.kwonlyargs,
            )
        }

    expected_public_parameters = {
        "create_source_rationalisation_plan": {"run_id"},
        "require_source_rationalisation_plan": {"value"},
        "write_source_rationalisation_plan": {"plan", "output_path"},
        "validate_owner_source_rationalisation_decision": {"plan_path", "decision_path"},
        "require_owner_validation": {"value"},
        "write_owner_validation": {"plan_path", "decision_path", "output_path"},
    }
    public_signatures_locked = all(
        parameter_names(name) == expected for name, expected in expected_public_parameters.items()
    )
    max_age_seconds = 0
    for node in tree.body:
        if not isinstance(node, ast.Assign) or not any(
            isinstance(target, ast.Name) and target.id == "MAX_OWNER_DECISION_AGE" for target in node.targets
        ):
            continue
        call = node.value
        if (
            isinstance(call, ast.Call)
            and isinstance(call.func, ast.Name)
            and call.func.id == "timedelta"
            and not call.args
            and len(call.keywords) == 1
            and call.keywords[0].arg == "hours"
            and isinstance(call.keywords[0].value, ast.Constant)
            and call.keywords[0].value.value == 4
        ):
            max_age_seconds = 4 * 60 * 60
        break

    def no_authority(authority: object, *, validation: bool = False) -> bool:
        if not isinstance(authority, Mapping):
            return False
        return (
            authority.get("canonical_website_mutation") == "none"
            and authority.get("physical_source_file_removal") == "none"
            and authority.get("package_authority") == "none"
            and authority.get("release_eligible") is False
            and authority.get("deployment_authority") == "none"
            and authority.get("credential_access") == "none"
            and authority.get("network_access") == "none"
            and authority.get("staging_authority") == "none"
            and (authority.get("staging_executed") is False if validation else True)
        )

    source_sha256 = hashlib.sha256(source_file.read_bytes()).hexdigest().upper()
    source_hash_matches = source_sha256 == WEBSITE_SOURCE_RATIONALISATION_REVIEWED_SHA256
    launcher_sha256 = hashlib.sha256(launcher_file.read_bytes()).hexdigest().upper()
    launcher_hash_matches = launcher_sha256 == WEBSITE_SOURCE_RATIONALISATION_LAUNCHER_SHA256
    fixed_limits_value = literal_assignment("FIXED_FOOTPRINT_LIMITS")
    fixed_limits = dict(fixed_limits_value) if isinstance(fixed_limits_value, Mapping) else {}
    reviewed_bindings = {
        name: literal_assignment(name) for name in WEBSITE_SOURCE_RATIONALISATION_REVIEWED_BINDINGS
    }
    repo_code_imported = any(
        (
            isinstance(node, ast.ImportFrom)
            and isinstance(node.module, str)
            and node.module.startswith("aureon")
        )
        or (isinstance(node, ast.Import) and any(alias.name.startswith("aureon") for alias in node.names))
        for node in tree.body
    )
    launcher_repo_code_imported = any(
        (
            isinstance(node, ast.ImportFrom)
            and isinstance(node.module, str)
            and node.module.startswith("aureon")
        )
        or (isinstance(node, ast.Import) and any(alias.name.startswith("aureon") for alias in node.names))
        for node in launcher_tree.body
    )
    plan_authority = literal_assignment("PLAN_AUTHORITY")
    decision_authority = literal_assignment("OWNER_DECISION_AUTHORITY")
    validation_authority = literal_assignment("VALIDATION_AUTHORITY")
    protocol_available = (
        source_file.is_file()
        and source_hash_matches
        and launcher_hash_matches
        and reviewed_bindings == WEBSITE_SOURCE_RATIONALISATION_REVIEWED_BINDINGS
        and public_signatures_locked
        and not repo_code_imported
        and not launcher_repo_code_imported
        and literal_assignment("PLAN_SCHEMA") == "aureon.website-source-rationalisation-plan.v1"
        and literal_assignment("OWNER_DECISION_SCHEMA")
        == "aureon.website-source-rationalisation-owner-decision.v1"
        and literal_assignment("OWNER_VALIDATION_SCHEMA")
        == "aureon.website-source-rationalisation-owner-validation.v1"
        and no_authority(plan_authority)
        and no_authority(decision_authority)
        and no_authority(validation_authority, validation=True)
        and isinstance(plan_authority, Mapping)
        and plan_authority.get("staging_authority") == "none"
        and plan_authority.get("candidate_authority") == "none"
        and isinstance(decision_authority, Mapping)
        and decision_authority.get("candidate_mutation") == "none"
        and decision_authority.get("candidate_removal_authority") == "none"
        and isinstance(validation_authority, Mapping)
        and validation_authority.get("candidate_authority") == "none"
        and 0 < max_age_seconds <= 4 * 60 * 60
        and fixed_limits
        == {
            "max_total_bytes": 4_500_000,
            "max_image_bytes": 2_200_000,
            "max_css_bytes": 350_000,
            "max_single_asset_bytes": 500_000,
        }
        and {
            "create_source_rationalisation_plan",
            "require_source_rationalisation_plan",
            "write_source_rationalisation_plan",
            "validate_owner_source_rationalisation_decision",
            "require_owner_validation",
            "write_owner_validation",
        }.issubset(function_names)
    )
    return {
        **unavailable,
        "available": protocol_available,
        "installed": True,
        "state": "installed-owner-decision-required" if protocol_available else "protocol-blocked",
        "planning_protocol_available": protocol_available,
        "decision_validation_protocol_available": protocol_available,
        "max_decision_age_seconds": max_age_seconds,
        "fixed_footprint_limits": fixed_limits,
        "source_sha256": source_sha256,
        "source_hash_matches": source_hash_matches,
        "reviewed_bindings": reviewed_bindings,
        "public_signatures_locked": public_signatures_locked,
        "repo_code_imported": repo_code_imported,
        "launcher_sha256": launcher_sha256,
        "launcher_hash_matches": launcher_hash_matches,
        "launcher_repo_code_imported": launcher_repo_code_imported,
    }


def website_runtime_optimisation_readiness(repo_root: Path) -> dict[str, Any]:
    """Discover the proposal compiler by authenticated static inspection only."""

    unavailable: dict[str, Any] = {
        "available": False,
        "installed": False,
        "state": "unavailable",
        "proposal_compilation_protocol_available": False,
        "measurement_validation_protocol_available": False,
        "measurement_validation_scope": "unavailable",
        "measurement_provenance_verification_available": False,
        "production_compilation_blocked": True,
        "production_compilation_blocker": ("blocked-reviewed-measurement-provenance-tool-not-installed"),
        "browser_acceptance_contract_available": False,
        "measurement_schema_available": False,
        "proposal_schema_available": False,
        "proposal_compilation_executed": False,
        "measurement_validation_executed": False,
        "discovery_mode": "metadata-only-ast-and-json-no-import-no-subprocess",
        "module_imported": False,
        "measurement_evidence_required": True,
        "autonomous_measurement_evidence": False,
        "source_selection_required": True,
        "autonomous_source_selection": False,
        "transformations_executed": False,
        "canonical_website_mutation": "none",
        "physical_source_file_removal": "none",
        "encoding_execution": "none",
        "css_transformation_execution": "none",
        "reference_mutation": "none",
        "candidate_authority": "none",
        "staging_authority": "none",
        "package_authority": "none",
        "release_eligible": False,
        "deployment_authority": "none",
        "credential_access": "none",
        "network_access": "none",
        "max_input_age_seconds": 0,
        "fixed_footprint_limits": {},
        "source_sha256": "",
        "expected_source_sha256": WEBSITE_RUNTIME_OPTIMISATION_REVIEWED_SHA256,
        "source_hash_matches": False,
        "launcher_path": WEBSITE_RUNTIME_OPTIMISATION_LAUNCHER_PATH,
        "launcher_sha256": "",
        "expected_launcher_sha256": WEBSITE_RUNTIME_OPTIMISATION_LAUNCHER_SHA256,
        "launcher_hash_matches": False,
        "acceptance_contract_path": WEBSITE_BROWSER_ACCEPTANCE_CONTRACT_PATH,
        "acceptance_contract_sha256": "",
        "expected_acceptance_contract_sha256": WEBSITE_BROWSER_ACCEPTANCE_CONTRACT_SHA256,
        "acceptance_contract_hash_matches": False,
        "acceptance_contract_payload_valid": False,
        "measurement_schema_path": WEBSITE_RUNTIME_OPTIMISATION_MEASUREMENT_SCHEMA_PATH,
        "measurement_schema_sha256": "",
        "expected_measurement_schema_sha256": (WEBSITE_RUNTIME_OPTIMISATION_MEASUREMENT_SCHEMA_SHA256),
        "measurement_schema_hash_matches": False,
        "measurement_schema_json_valid": False,
        "proposal_schema_path": WEBSITE_RUNTIME_OPTIMISATION_PROPOSAL_SCHEMA_PATH,
        "proposal_schema_sha256": "",
        "expected_proposal_schema_sha256": WEBSITE_RUNTIME_OPTIMISATION_PROPOSAL_SCHEMA_SHA256,
        "proposal_schema_hash_matches": False,
        "proposal_schema_json_valid": False,
        "reviewed_bindings": {},
        "public_signatures_locked": False,
        "repo_code_imported": False,
        "launcher_repo_code_imported": False,
        "forbidden_operational_imports_present": False,
        "error": "",
    }
    module_relative = "aureon/operator/website_runtime_optimisation.py"
    source_file = _safe_source_path(repo_root, module_relative)
    launcher_file = _safe_source_path(repo_root, WEBSITE_RUNTIME_OPTIMISATION_LAUNCHER_PATH)
    acceptance_file = _safe_source_path(repo_root, WEBSITE_BROWSER_ACCEPTANCE_CONTRACT_PATH)
    measurement_schema_file = _safe_source_path(
        repo_root, WEBSITE_RUNTIME_OPTIMISATION_MEASUREMENT_SCHEMA_PATH
    )
    proposal_schema_file = _safe_source_path(repo_root, WEBSITE_RUNTIME_OPTIMISATION_PROPOSAL_SCHEMA_PATH)
    tree = _module_tree(repo_root, module_relative)
    launcher_tree = _module_tree(repo_root, WEBSITE_RUNTIME_OPTIMISATION_LAUNCHER_PATH)
    if (
        tree is None
        or launcher_tree is None
        or not source_file.is_file()
        or not launcher_file.is_file()
        or not acceptance_file.is_file()
        or not measurement_schema_file.is_file()
        or not proposal_schema_file.is_file()
    ):
        unavailable["installed"] = source_file.is_file()
        unavailable["error"] = (
            "Runtime optimisation source, launcher, browser contract, or JSON Schema is missing."
        )
        return unavailable

    def literal_assignment(name: str) -> object:
        for node in tree.body:
            value_node: ast.expr | None = None
            if (
                isinstance(node, ast.Assign)
                and any(isinstance(target, ast.Name) and target.id == name for target in node.targets)
            ) or (
                isinstance(node, ast.AnnAssign)
                and isinstance(node.target, ast.Name)
                and node.target.id == name
            ):
                value_node = node.value
            if value_node is None:
                continue
            if (
                isinstance(value_node, ast.Call)
                and isinstance(value_node.func, ast.Name)
                and value_node.func.id == "MappingProxyType"
                and len(value_node.args) == 1
                and not value_node.keywords
            ):
                value_node = value_node.args[0]
            try:
                return ast.literal_eval(value_node)
            except (ValueError, TypeError):
                return None
        return None

    functions = {
        node.name: node for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }

    def parameter_names(name: str) -> set[str] | None:
        node = functions.get(name)
        if node is None or node.args.vararg is not None or node.args.kwarg is not None:
            return None
        return {argument.arg for argument in (*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs)}

    expected_public_parameters = {
        "compile_runtime_optimisation_proposal": {
            "source_plan_path",
            "source_plan_sha256",
            "measurement_path",
            "measurement_sha256",
            "acceptance_contract_path",
            "acceptance_contract_sha256",
            "run_id",
        },
        "require_measurement_evidence": {"value"},
        "require_runtime_optimisation_proposal": {"value"},
        "write_runtime_optimisation_proposal": {
            "source_plan_path",
            "source_plan_sha256",
            "measurement_path",
            "measurement_sha256",
            "acceptance_contract_path",
            "acceptance_contract_sha256",
            "output_path",
            "run_id",
        },
    }
    public_signatures_locked = all(
        parameter_names(name) == parameters for name, parameters in expected_public_parameters.items()
    )
    max_age_seconds = 0
    for node in tree.body:
        if not isinstance(node, ast.Assign) or not any(
            isinstance(target, ast.Name) and target.id == "MAX_INPUT_AGE" for target in node.targets
        ):
            continue
        call = node.value
        if (
            isinstance(call, ast.Call)
            and isinstance(call.func, ast.Name)
            and call.func.id == "timedelta"
            and not call.args
            and len(call.keywords) == 1
            and call.keywords[0].arg == "hours"
            and isinstance(call.keywords[0].value, ast.Constant)
            and call.keywords[0].value.value == 4
        ):
            max_age_seconds = 4 * 60 * 60
        break
    source_sha256 = _sha256(source_file)
    launcher_sha256 = _sha256(launcher_file)
    acceptance_sha256 = _sha256(acceptance_file)
    measurement_schema_sha256 = _sha256(measurement_schema_file)
    proposal_schema_sha256 = _sha256(proposal_schema_file)
    source_hash_matches = source_sha256 == WEBSITE_RUNTIME_OPTIMISATION_REVIEWED_SHA256
    launcher_hash_matches = launcher_sha256 == WEBSITE_RUNTIME_OPTIMISATION_LAUNCHER_SHA256
    acceptance_hash_matches = acceptance_sha256 == WEBSITE_BROWSER_ACCEPTANCE_CONTRACT_SHA256
    measurement_schema_hash_matches = (
        measurement_schema_sha256 == WEBSITE_RUNTIME_OPTIMISATION_MEASUREMENT_SCHEMA_SHA256
    )
    proposal_schema_hash_matches = (
        proposal_schema_sha256 == WEBSITE_RUNTIME_OPTIMISATION_PROPOSAL_SCHEMA_SHA256
    )
    reviewed_bindings = {
        name: literal_assignment(name) for name in WEBSITE_RUNTIME_OPTIMISATION_REVIEWED_BINDINGS
    }
    repo_code_imported = any(
        (
            isinstance(node, ast.ImportFrom)
            and isinstance(node.module, str)
            and node.module.startswith("aureon")
        )
        or (isinstance(node, ast.Import) and any(alias.name.startswith("aureon") for alias in node.names))
        for node in tree.body
    )
    launcher_repo_code_imported = any(
        (
            isinstance(node, ast.ImportFrom)
            and isinstance(node.module, str)
            and node.module.startswith("aureon")
        )
        or (isinstance(node, ast.Import) and any(alias.name.startswith("aureon") for alias in node.names))
        for node in launcher_tree.body
    )
    forbidden_imports = {"subprocess", "socket", "urllib", "http", "ftplib", "shutil"}
    imported_roots = {
        alias.name.split(".", 1)[0]
        for node in tree.body
        if isinstance(node, ast.Import)
        for alias in node.names
    } | {
        str(node.module).split(".", 1)[0]
        for node in tree.body
        if isinstance(node, ast.ImportFrom) and node.module
    }
    forbidden_operational_imports_present = bool(imported_roots & forbidden_imports)
    acceptance_payload_valid = False
    try:
        acceptance = json.loads(acceptance_file.read_text(encoding="utf-8"))
        if isinstance(acceptance, dict):
            expected_payload = acceptance.pop("payloadSha256", None)
            acceptance_payload_valid = (
                isinstance(expected_payload, str)
                and hashlib.sha256(
                    json.dumps(
                        acceptance,
                        sort_keys=True,
                        separators=(",", ":"),
                        ensure_ascii=False,
                        allow_nan=False,
                    ).encode("utf-8")
                )
                .hexdigest()
                .upper()
                == expected_payload
                and expected_payload == WEBSITE_BROWSER_ACCEPTANCE_CONTRACT_PAYLOAD_SHA256
            )
    except (OSError, UnicodeError, json.JSONDecodeError, TypeError, ValueError):
        acceptance_payload_valid = False
    measurement_schema_json_valid = False
    proposal_schema_json_valid = False
    try:
        measurement_schema = json.loads(measurement_schema_file.read_text(encoding="utf-8"))
        proposal_schema = json.loads(proposal_schema_file.read_text(encoding="utf-8"))
        measurement_schema_json_valid = (
            isinstance(measurement_schema, dict)
            and measurement_schema.get("$schema") == "https://json-schema.org/draft/2020-12/schema"
            and measurement_schema.get("type") == "object"
            and measurement_schema.get("additionalProperties") is False
            and isinstance(measurement_schema.get("properties"), dict)
            and measurement_schema["properties"].get("schema", {}).get("const")
            == "aureon.website-runtime-optimisation-measurement-evidence.v1"
        )
        proposal_schema_json_valid = (
            isinstance(proposal_schema, dict)
            and proposal_schema.get("$schema") == "https://json-schema.org/draft/2020-12/schema"
            and proposal_schema.get("type") == "object"
            and proposal_schema.get("additionalProperties") is False
            and isinstance(proposal_schema.get("properties"), dict)
            and proposal_schema["properties"].get("schema", {}).get("const")
            == "aureon.website-runtime-optimisation-proposal.v1"
        )
    except (OSError, UnicodeError, json.JSONDecodeError, TypeError, ValueError, AttributeError):
        measurement_schema_json_valid = False
        proposal_schema_json_valid = False
    fixed_limits_value = literal_assignment("FIXED_FOOTPRINT_LIMITS")
    fixed_limits = dict(fixed_limits_value) if isinstance(fixed_limits_value, Mapping) else {}
    authority = literal_assignment("NO_AUTHORITY")
    no_authority = isinstance(authority, Mapping) and (
        authority.get("source_selection_authority") == "none"
        and authority.get("measurement_creation_authority") == "none"
        and authority.get("canonical_website_mutation") == "none"
        and authority.get("physical_source_file_removal") == "none"
        and authority.get("encoding_execution") == "none"
        and authority.get("css_transformation_execution") == "none"
        and authority.get("reference_mutation") == "none"
        and authority.get("candidate_authority") == "none"
        and authority.get("staging_authority") == "none"
        and authority.get("package_authority") == "none"
        and authority.get("release_eligible") is False
        and authority.get("deployment_authority") == "none"
        and authority.get("credential_access") == "none"
        and authority.get("network_access") == "none"
    )
    source_contract_available = (
        source_hash_matches
        and launcher_hash_matches
        and acceptance_hash_matches
        and acceptance_payload_valid
        and measurement_schema_hash_matches
        and measurement_schema_json_valid
        and proposal_schema_hash_matches
        and proposal_schema_json_valid
        and reviewed_bindings == WEBSITE_RUNTIME_OPTIMISATION_REVIEWED_BINDINGS
        and public_signatures_locked
        and not repo_code_imported
        and not launcher_repo_code_imported
        and not forbidden_operational_imports_present
        and literal_assignment("MEASUREMENT_SCHEMA")
        == "aureon.website-runtime-optimisation-measurement-evidence.v1"
        and literal_assignment("PROPOSAL_SCHEMA") == "aureon.website-runtime-optimisation-proposal.v1"
        and literal_assignment("ACCEPTANCE_CONTRACT_SCHEMA") == "aureon.browser-acceptance-contract.v1"
        and literal_assignment("PRODUCTION_MEASUREMENT_PROVENANCE_STATE")
        == "blocked-reviewed-measurement-provenance-tool-not-installed"
        and no_authority
        and max_age_seconds == 4 * 60 * 60
        and fixed_limits
        == {
            "max_total_bytes": 4_500_000,
            "max_image_bytes": 2_200_000,
            "max_css_bytes": 350_000,
            "max_single_asset_bytes": 500_000,
        }
    )
    return {
        **unavailable,
        "available": source_contract_available,
        "installed": True,
        "state": (
            "installed-reviewed-measurement-provenance-required"
            if source_contract_available
            else "protocol-blocked"
        ),
        "proposal_compilation_protocol_available": False,
        "measurement_validation_protocol_available": source_contract_available,
        "measurement_validation_scope": "structural-only-no-freshness-or-provenance",
        "measurement_provenance_verification_available": False,
        "production_compilation_blocked": True,
        "production_compilation_blocker": ("blocked-reviewed-measurement-provenance-tool-not-installed"),
        "browser_acceptance_contract_available": (acceptance_hash_matches and acceptance_payload_valid),
        "measurement_schema_available": (measurement_schema_hash_matches and measurement_schema_json_valid),
        "proposal_schema_available": proposal_schema_hash_matches and proposal_schema_json_valid,
        "max_input_age_seconds": max_age_seconds,
        "fixed_footprint_limits": fixed_limits,
        "source_sha256": source_sha256,
        "source_hash_matches": source_hash_matches,
        "launcher_sha256": launcher_sha256,
        "launcher_hash_matches": launcher_hash_matches,
        "acceptance_contract_sha256": acceptance_sha256,
        "acceptance_contract_hash_matches": acceptance_hash_matches,
        "acceptance_contract_payload_valid": acceptance_payload_valid,
        "measurement_schema_sha256": measurement_schema_sha256,
        "measurement_schema_hash_matches": measurement_schema_hash_matches,
        "measurement_schema_json_valid": measurement_schema_json_valid,
        "proposal_schema_sha256": proposal_schema_sha256,
        "proposal_schema_hash_matches": proposal_schema_hash_matches,
        "proposal_schema_json_valid": proposal_schema_json_valid,
        "reviewed_bindings": reviewed_bindings,
        "public_signatures_locked": public_signatures_locked,
        "repo_code_imported": repo_code_imported,
        "launcher_repo_code_imported": launcher_repo_code_imported,
        "forbidden_operational_imports_present": forbidden_operational_imports_present,
    }


def website_runtime_measurement_static_integrity_readiness(repo_root: Path) -> dict[str, Any]:
    """Discover the pinned read/validate-only static-integrity surface without importing it."""

    unavailable: dict[str, Any] = {
        "available": False,
        "installed": False,
        "state": "unavailable",
        "capability_scope": "read-validate-only",
        "static_integrity_validation_available": False,
        "static_integrity_validation_executed": False,
        "trusted_static_integrity_execution_path": "fresh-isolated-launcher-only",
        "imported_api_authoritative": False,
        "measurement_provenance_verification_available": False,
        "production_eligible": False,
        "eligible_for_proposal_compilation": False,
        "production_compilation_blocked": True,
        "worker_available": False,
        "worker_executed": False,
        "artifact_emission_available": False,
        "artifact_emission_executed": False,
        "canonical_website_mutation": "none",
        "physical_source_file_removal": "none",
        "encoding_execution": "none",
        "css_transformation_execution": "none",
        "reference_mutation": "none",
        "candidate_authority": "none",
        "staging_authority": "none",
        "package_authority": "none",
        "release_eligible": False,
        "deployment_authority": "none",
        "credential_access": "none",
        "network_access": "none",
        "discovery_mode": "metadata-only-ast-and-json-no-import-no-subprocess",
        "module_imported": False,
        "launcher_module_imported": False,
        "subprocess_launched": False,
        "standard_library_only": False,
        "forbidden_operational_imports_present": False,
        "writer_or_emitter_surface_present": False,
        "public_verify_signature_locked": False,
        "launcher_isolation_markers_locked": False,
        "source_path": WEBSITE_RUNTIME_MEASUREMENT_STATIC_INTEGRITY_PATH,
        "source_sha256": "",
        "expected_source_sha256": WEBSITE_RUNTIME_MEASUREMENT_STATIC_INTEGRITY_SHA256,
        "source_hash_matches": False,
        "launcher_path": WEBSITE_RUNTIME_MEASUREMENT_STATIC_INTEGRITY_LAUNCHER_PATH,
        "launcher_sha256": "",
        "expected_launcher_sha256": (WEBSITE_RUNTIME_MEASUREMENT_STATIC_INTEGRITY_LAUNCHER_SHA256),
        "launcher_hash_matches": False,
        "schema_path": WEBSITE_RUNTIME_MEASUREMENT_STATIC_INTEGRITY_SCHEMA_PATH,
        "schema_sha256": "",
        "expected_schema_sha256": WEBSITE_RUNTIME_MEASUREMENT_STATIC_INTEGRITY_SCHEMA_SHA256,
        "schema_hash_matches": False,
        "schema_json_valid": False,
        "error": "",
    }
    module_file = _safe_source_path(repo_root, WEBSITE_RUNTIME_MEASUREMENT_STATIC_INTEGRITY_PATH)
    launcher_file = _safe_source_path(repo_root, WEBSITE_RUNTIME_MEASUREMENT_STATIC_INTEGRITY_LAUNCHER_PATH)
    schema_file = _safe_source_path(repo_root, WEBSITE_RUNTIME_MEASUREMENT_STATIC_INTEGRITY_SCHEMA_PATH)
    module_tree = _module_tree(repo_root, WEBSITE_RUNTIME_MEASUREMENT_STATIC_INTEGRITY_PATH)
    launcher_tree = _module_tree(repo_root, WEBSITE_RUNTIME_MEASUREMENT_STATIC_INTEGRITY_LAUNCHER_PATH)
    if (
        module_tree is None
        or launcher_tree is None
        or not module_file.is_file()
        or not launcher_file.is_file()
        or not schema_file.is_file()
    ):
        unavailable["installed"] = module_file.is_file()
        unavailable["error"] = "Static-integrity module, isolated launcher, or schema is missing."
        return unavailable

    def imported_roots(tree: ast.Module) -> set[str]:
        return {
            alias.name.split(".", 1)[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        } | {
            str(node.module).split(".", 1)[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.module
        }

    def literal_assignment(tree: ast.Module, name: str) -> object:
        for node in tree.body:
            value_node: ast.expr | None = None
            if (
                isinstance(node, ast.Assign)
                and any(isinstance(target, ast.Name) and target.id == name for target in node.targets)
            ) or (
                isinstance(node, ast.AnnAssign)
                and isinstance(node.target, ast.Name)
                and node.target.id == name
            ):
                value_node = node.value
            if value_node is None:
                continue
            if (
                isinstance(value_node, ast.Call)
                and isinstance(value_node.func, ast.Name)
                and value_node.func.id == "MappingProxyType"
                and len(value_node.args) == 1
                and not value_node.keywords
            ):
                value_node = value_node.args[0]
            try:
                return ast.literal_eval(value_node)
            except (ValueError, TypeError):
                return None
        return None

    source_sha256 = _sha256(module_file)
    launcher_sha256 = _sha256(launcher_file)
    schema_sha256 = _sha256(schema_file)
    source_hash_matches = source_sha256 == WEBSITE_RUNTIME_MEASUREMENT_STATIC_INTEGRITY_SHA256
    launcher_hash_matches = launcher_sha256 == WEBSITE_RUNTIME_MEASUREMENT_STATIC_INTEGRITY_LAUNCHER_SHA256
    schema_hash_matches = schema_sha256 == WEBSITE_RUNTIME_MEASUREMENT_STATIC_INTEGRITY_SCHEMA_SHA256
    module_imports = imported_roots(module_tree)
    launcher_imports = imported_roots(launcher_tree)
    standard_library_roots = {
        "__future__",
        "argparse",
        "collections",
        "copy",
        "datetime",
        "hashlib",
        "json",
        "os",
        "pathlib",
        "re",
        "stat",
        "sys",
        "types",
        "typing",
        "unicodedata",
    }
    forbidden_operational_roots = {
        "boto3",
        "ftplib",
        "http",
        "paramiko",
        "requests",
        "shutil",
        "socket",
        "subprocess",
        "tempfile",
        "urllib",
    }
    forbidden_operational_imports_present = bool(
        (module_imports | launcher_imports) & forbidden_operational_roots
    )
    standard_library_only = (
        module_imports <= standard_library_roots
        and launcher_imports <= standard_library_roots
        and not forbidden_operational_imports_present
    )
    writer_calls = {
        "chmod",
        "hardlink_to",
        "mkdir",
        "rename",
        "rmdir",
        "symlink_to",
        "touch",
        "unlink",
        "write_bytes",
        "write_text",
    }
    called_attributes = {
        node.func.attr
        for node in ast.walk(module_tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    }
    called_names = {
        node.func.id
        for node in ast.walk(module_tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    function_names = {
        node.name for node in module_tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    writer_or_emitter_surface_present = bool(called_attributes & writer_calls) or any(
        name.startswith(("write_", "emit_", "create_", "encode_")) for name in function_names
    )
    verify_function = next(
        (
            node
            for node in module_tree.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name == "verify_measurement_provenance_file"
        ),
        None,
    )
    public_verify_signature_locked = (
        verify_function is not None
        and not verify_function.args.posonlyargs
        and not verify_function.args.args
        and verify_function.args.vararg is None
        and tuple(argument.arg for argument in verify_function.args.kwonlyargs)
        == ("repo_root", "measurement_path", "expected_measurement_sha256")
        and all(default is None for default in verify_function.args.kw_defaults)
        and verify_function.args.kwarg is None
    )
    module_text = module_file.read_text(encoding="utf-8", errors="strict")
    launcher_text = launcher_file.read_text(encoding="utf-8", errors="strict")
    launcher_attributes = {node.attr for node in ast.walk(launcher_tree) if isinstance(node, ast.Attribute)}
    launcher_isolation_markers_locked = (
        {"isolated", "no_site", "dont_write_bytecode"} <= launcher_attributes
        and "Launcher requires python -I -S -B." in launcher_text
        and "--expected-launcher-sha256" in launcher_text
        and "--expected-module-sha256" in launcher_text
        and "__aureon_runtime_measurement_provenance_launcher_attestation__" in launcher_text
        and "CLI requires python -I -S -B." in module_text
    )
    expected_authority = {
        "scope": "read-only static artifact integrity verification only",
        "source_selection_authority": "none",
        "measurement_creation_authority": "none",
        "canonical_website_mutation": "none",
        "physical_source_file_removal": "none",
        "encoding_execution": "none",
        "css_transformation_execution": "none",
        "reference_mutation": "none",
        "candidate_authority": "none",
        "staging_authority": "none",
        "package_authority": "none",
        "release_eligible": False,
        "deployment_authority": "none",
        "network_access": "none",
        "credential_access": "none",
    }
    module_contract_locked = (
        literal_assignment(module_tree, "MEASUREMENT_SCHEMA")
        == "aureon.website-runtime-measurement-static-integrity.v1"
        and literal_assignment(module_tree, "VERIFIED_STATE")
        == "static-integrity-verified-production-blocked"
        and literal_assignment(module_tree, "VERIFICATION_MODE") == "static-artifact-integrity-only"
        and literal_assignment(module_tree, "NO_AUTHORITY") == expected_authority
        and "subprocess" not in called_names
    )
    schema_json_valid = False
    try:
        schema = json.loads(schema_file.read_text(encoding="utf-8", errors="strict"))
        properties = schema.get("properties") if isinstance(schema, Mapping) else None
        definitions = schema.get("$defs") if isinstance(schema, Mapping) else None
        schema_authority = definitions.get("authority") if isinstance(definitions, Mapping) else None
        schema_authority_properties = (
            schema_authority.get("properties") if isinstance(schema_authority, Mapping) else None
        )
        schema_json_valid = (
            isinstance(schema, Mapping)
            and schema.get("$schema") == "https://json-schema.org/draft/2020-12/schema"
            and schema.get("type") == "object"
            and schema.get("additionalProperties") is False
            and isinstance(properties, Mapping)
            and properties.get("schema", {}).get("const")
            == "aureon.website-runtime-measurement-static-integrity.v1"
            and properties.get("state", {}).get("const") == "static-integrity-verified-production-blocked"
            and properties.get("mode", {}).get("const") == "static-artifact-integrity-only"
            and properties.get("eligible_for_proposal_compilation", {}).get("const") is False
            and isinstance(schema_authority, Mapping)
            and schema_authority.get("additionalProperties") is False
            and isinstance(schema_authority_properties, Mapping)
            and set(schema_authority_properties) == set(expected_authority)
            and all(
                isinstance(schema_authority_properties.get(name), Mapping)
                and schema_authority_properties[name].get("const") == expected
                for name, expected in expected_authority.items()
            )
        )
    except (OSError, UnicodeError, json.JSONDecodeError, TypeError, ValueError, AttributeError):
        schema_json_valid = False
    protocol_available = (
        source_hash_matches
        and launcher_hash_matches
        and schema_hash_matches
        and standard_library_only
        and not writer_or_emitter_surface_present
        and public_verify_signature_locked
        and launcher_isolation_markers_locked
        and module_contract_locked
        and schema_json_valid
    )
    return {
        **unavailable,
        "available": protocol_available,
        "installed": True,
        "state": (
            "installed-read-validate-only-production-ineligible" if protocol_available else "protocol-blocked"
        ),
        "static_integrity_validation_available": protocol_available,
        "standard_library_only": standard_library_only,
        "forbidden_operational_imports_present": forbidden_operational_imports_present,
        "writer_or_emitter_surface_present": writer_or_emitter_surface_present,
        "public_verify_signature_locked": public_verify_signature_locked,
        "launcher_isolation_markers_locked": launcher_isolation_markers_locked,
        "source_sha256": source_sha256,
        "source_hash_matches": source_hash_matches,
        "launcher_sha256": launcher_sha256,
        "launcher_hash_matches": launcher_hash_matches,
        "schema_sha256": schema_sha256,
        "schema_hash_matches": schema_hash_matches,
        "schema_json_valid": schema_json_valid,
    }


def design_research_refresh_readiness(repo_root: Path) -> dict[str, Any]:
    """Expose only the current redacted research-refresh planning signal.

    This is intentionally separate from the static registry verification. A
    source declaration can expire without making the installed capability
    disappear. Neither a current result nor this discovery payload creates a
    candidate, grants delivery readiness, clears artwork, or authorises a
    release.
    """

    unavailable = {
        "available": False,
        "state": "unavailable",
        "current": False,
        "planning_signal_available": False,
        "candidate_delivery_ready": False,
        "delivery_authority": "none",
        "release_eligible": False,
        "deployment_authority": "none",
        "declaration": {},
        "artwork": {"state": "", "cleared_for_use": False},
        "error": "",
    }
    try:
        from aureon.operator.design_research_refresh import audit_design_research_sources_file

        receipt = audit_design_research_sources_file(repo_root=repo_root)
    except Exception as exc:
        unavailable["error"] = f"{type(exc).__name__}: {exc}"
        return unavailable

    raw_declaration = receipt.get("declaration")
    raw_artwork = receipt.get("artwork")
    declaration = raw_declaration if isinstance(raw_declaration, Mapping) else {}
    artwork = raw_artwork if isinstance(raw_artwork, Mapping) else {}
    current = (
        receipt.get("passed") is True
        and receipt.get("state") == "current"
        and receipt.get("release_eligible") is False
        and receipt.get("package_authority") == "none"
        and receipt.get("deployment_authority") == "none"
        and artwork.get("state") == "not-cleared"
        and artwork.get("cleared_for_use") is False
    )
    return {
        "available": True,
        "state": "current" if current else str(receipt.get("state") or "blocked"),
        "current": current,
        "planning_signal_available": current,
        "candidate_delivery_ready": False,
        "delivery_authority": "none",
        "release_eligible": False,
        "deployment_authority": "none",
        "declaration": {
            "path": str(declaration.get("path") or ""),
            "sha256": str(declaration.get("sha256") or ""),
        },
        "artwork": {
            "state": str(artwork.get("state") or ""),
            "cleared_for_use": artwork.get("cleared_for_use") is True,
        },
        "error": "",
    }


def stakeholder_feedback_readiness(repo_root: Path) -> dict[str, Any]:
    """Expose a privacy-safe planning signal without correspondence content.

    The readiness view deliberately omits signal capsules, signal identifiers,
    quotations, identities, provider metadata, URLs, and free-form content. It
    carries only the canonical declaration binding, freshness, aggregate
    counts, and deterministic capsule-set hash needed to prove that later
    route-bound work used the current controlled-code review.
    """

    unavailable: dict[str, Any] = {
        "available": False,
        "installed": False,
        "state": "unavailable",
        "current": False,
        "planning_only": True,
        "planning_signal_available": False,
        "candidate_delivery_ready": False,
        "release_eligible": False,
        "release_authority": "none",
        "package_authority": "none",
        "deployment_authority": "none",
        "raw_correspondence_access": "none",
        "declaration": {},
        "freshness": {"state": "", "issued_at": "", "refresh_by": ""},
        "signal_capsules_sha256": "",
        "summary": {
            "signal_count": 0,
            "action_requested_count": 0,
            "no_action_count": 0,
        },
        "response_manifest_required": True,
        "error": "",
    }
    try:
        from aureon.operator.design_stakeholder_feedback import (
            audit_design_stakeholder_feedback_file,
        )
    except Exception as exc:
        unavailable["error"] = f"{type(exc).__name__}: {exc}"
        return unavailable

    unavailable["available"] = True
    unavailable["installed"] = True
    unavailable["state"] = "blocked"
    try:
        receipt = audit_design_stakeholder_feedback_file(repo_root=repo_root)
    except Exception as exc:
        unavailable["error"] = f"{type(exc).__name__}: {exc}"
        return unavailable

    raw_binding = receipt.get("feedback")
    binding = raw_binding if isinstance(raw_binding, Mapping) else {}
    raw_freshness = receipt.get("freshness")
    freshness = raw_freshness if isinstance(raw_freshness, Mapping) else {}
    raw_summary = receipt.get("summary")
    summary = raw_summary if isinstance(raw_summary, Mapping) else {}
    current = (
        receipt.get("passed") is True
        and receipt.get("state") in {"current", "refresh-due"}
        and receipt.get("receipt_authority") is False
        and receipt.get("release_eligible") is False
        and receipt.get("package_authority") == "none"
        and receipt.get("deployment_authority") == "none"
    )

    def safe_count(field: str) -> int:
        value = summary.get(field)
        return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else 0

    return {
        "available": True,
        "installed": True,
        "state": str(receipt.get("state") or "blocked"),
        "current": current,
        "planning_only": True,
        "planning_signal_available": current,
        "candidate_delivery_ready": False,
        "release_eligible": False,
        "release_authority": "none",
        "package_authority": "none",
        "deployment_authority": "none",
        "raw_correspondence_access": "none",
        "declaration": {
            "feedback_id": str(binding.get("feedback_id") or ""),
            "path": str(binding.get("path") or ""),
            "sha256": str(binding.get("sha256") or ""),
        },
        "freshness": {
            "state": str(freshness.get("state") or ""),
            "issued_at": str(freshness.get("issued_at") or ""),
            "refresh_by": str(freshness.get("refresh_by") or ""),
        },
        "signal_capsules_sha256": str(receipt.get("signal_capsules_sha256") or ""),
        "summary": {
            "signal_count": safe_count("signal_count"),
            "action_requested_count": safe_count("action_requested_count"),
            "no_action_count": safe_count("no_action_count"),
        },
        "response_manifest_required": True,
        "error": "",
    }


def editorial_rights_decision_preparation_readiness(repo_root: Path) -> dict[str, Any]:
    """Expose the explicit-human preparation protocol without running it.

    Readiness means only that the verifier can persist an already supplied,
    exact human decision as immutable evidence and a proposal. The registry
    never infers approval, acts as the reviewer, or changes the canonical
    manifest, global artwork policy, candidate, package, or live site.
    """

    unavailable: dict[str, Any] = {
        "available": False,
        "installed": False,
        "state": "unavailable",
        "preparation_protocol_available": False,
        "human_decision_input_required": True,
        "autonomous_human_decision": False,
        "rights_inference": "never",
        "canonical_manifest_mutation": "never",
        "global_artwork_policy_mutation": "never",
        "candidate_use_rights_ready": False,
        "candidate_asset_ready": False,
        "candidate_delivery_ready": False,
        "release_eligible": False,
        "package_authority": "none",
        "deployment_authority": "none",
        "credential_access": "none",
        "network_access": "none",
        "connector_access": "none",
        "preparation_scope": "",
        "schemas": {},
        "error": "",
    }
    source_file = _safe_source_path(
        repo_root,
        "aureon/operator/design_editorial_asset_provenance.py",
    )
    try:
        from aureon.operator import design_editorial_asset_provenance as provenance
    except Exception as exc:
        unavailable["installed"] = source_file.is_file()
        unavailable["error"] = f"{type(exc).__name__}: {exc}"
        return unavailable

    authority = provenance.RIGHTS_PREPARATION_AUTHORITY
    protocol_available = (
        source_file.is_file()
        and provenance.RIGHTS_PREPARATION_REQUEST_SCHEMA
        == "aureon.editorial-asset-rights-decision-preparation-request.v1"
        and provenance.RIGHTS_BINDING_PROPOSAL_SCHEMA
        == "aureon.editorial-asset-rights-manifest-binding-proposal.v1"
        and isinstance(authority, Mapping)
        and authority.get("rights_inference") == "never"
        and authority.get("canonical_manifest_mutation") == "never"
        and authority.get("global_artwork_policy_mutation") == "never"
        and authority.get("canonical_website_mutation") == "never"
        and authority.get("source_asset_mutation") == "never"
        and authority.get("candidate_mutation") == "never"
        and authority.get("release_eligible") is False
        and authority.get("package_authority") == "none"
        and authority.get("deployment_authority") == "none"
        and authority.get("credential_access") == "none"
        and authority.get("network_access") == "none"
        and authority.get("connector_access") == "none"
        and callable(provenance.prepare_editorial_asset_rights_decisions)
    )
    return {
        "available": protocol_available,
        "installed": True,
        "state": "installed-explicit-human-decision-required" if protocol_available else "protocol-blocked",
        "preparation_protocol_available": protocol_available,
        "human_decision_input_required": True,
        "autonomous_human_decision": False,
        "rights_inference": "never",
        "canonical_manifest_mutation": "never",
        "global_artwork_policy_mutation": "never",
        "candidate_use_rights_ready": False,
        "candidate_asset_ready": False,
        "candidate_delivery_ready": False,
        "release_eligible": False,
        "package_authority": "none",
        "deployment_authority": "none",
        "credential_access": "none",
        "network_access": "none",
        "connector_access": "none",
        "preparation_scope": str(authority.get("scope") or ""),
        "schemas": {
            "request": provenance.RIGHTS_PREPARATION_REQUEST_SCHEMA,
            "proposal": provenance.RIGHTS_BINDING_PROPOSAL_SCHEMA,
            "decision": provenance.RIGHTS_DECISION_SCHEMA,
        },
        "error": "",
    }


def editorial_asset_provenance_readiness(repo_root: Path) -> dict[str, Any]:
    """Expose aggregate rights closure without claiming candidate import state."""

    unavailable: dict[str, Any] = {
        "available": False,
        "installed": False,
        "state": "unavailable",
        "integrity_verified": False,
        "public_use_ready": False,
        "candidate_use_rights_ready": False,
        "candidate_asset_ready": False,
        "candidate_delivery_ready": False,
        "release_eligible": False,
        "package_authority": "none",
        "deployment_authority": "none",
        "global_artwork_policy": {
            "state": "not-cleared",
            "cleared_for_use": False,
        },
        "manifest": {},
        "asset_capsules_sha256": "",
        "route_asset_capsules_sha256": "",
        "public_coverage_sha256": "",
        "summary": {
            "mapped_asset_count": 0,
            "unmapped_asset_count": 0,
            "currently_referenced_asset_count": 0,
            "unapproved_current_asset_count": 0,
            "current_copy_drift_asset_count": 0,
            "candidate_use_ready_count": 0,
        },
        "error": "",
    }
    try:
        from aureon.operator.design_editorial_asset_provenance import (
            audit_design_editorial_asset_provenance_file,
        )
    except Exception as exc:
        unavailable["error"] = f"{type(exc).__name__}: {exc}"
        return unavailable

    unavailable["available"] = True
    unavailable["installed"] = True
    unavailable["state"] = "blocked"
    try:
        receipt = audit_design_editorial_asset_provenance_file(repo_root=repo_root)
    except Exception as exc:
        unavailable["error"] = f"{type(exc).__name__}: {exc}"
        return unavailable

    raw_checks = receipt.get("checks")
    checks = raw_checks if isinstance(raw_checks, list) else []
    integrity_check_ids = {
        "canonical-manifest-binding",
        "global-artwork-policy-not-cleared",
        "redacted-evidence-integrity",
        "delivery-rights-separation",
        "asset-byte-and-inventory-integrity",
        "candidate-rights-closure",
    }
    checks_by_id = {str(item.get("id") or ""): item for item in checks if isinstance(item, Mapping)}
    integrity_verified = all(
        isinstance(checks_by_id.get(identifier), Mapping) and checks_by_id[identifier].get("passed") is True
        for identifier in integrity_check_ids
    )
    raw_manifest = receipt.get("manifest")
    manifest = raw_manifest if isinstance(raw_manifest, Mapping) else {}
    raw_policy = receipt.get("global_artwork_policy")
    policy = raw_policy if isinstance(raw_policy, Mapping) else {}
    raw_coverage = receipt.get("public_coverage")
    coverage = raw_coverage if isinstance(raw_coverage, Mapping) else {}
    raw_summary = receipt.get("summary")
    summary = raw_summary if isinstance(raw_summary, Mapping) else {}

    def safe_count(field: str) -> int:
        value = summary.get(field)
        return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else 0

    candidate_ready_count = safe_count("candidate_use_ready_count")
    public_use_ready = (
        receipt.get("passed") is True
        and coverage.get("all_current_references_authorised") is True
        and coverage.get("all_current_copy_bindings_closed") is True
    )
    return {
        "available": True,
        "installed": True,
        "state": str(receipt.get("state") or "blocked"),
        "integrity_verified": integrity_verified,
        "public_use_ready": public_use_ready,
        "candidate_use_rights_ready": candidate_ready_count > 0,
        "candidate_asset_ready": False,
        "candidate_delivery_ready": False,
        "release_eligible": False,
        "package_authority": "none",
        "deployment_authority": "none",
        "global_artwork_policy": {
            "state": str(policy.get("state") or ""),
            "cleared_for_use": policy.get("cleared_for_use") is True,
        },
        "manifest": {
            "manifest_id": str(manifest.get("manifest_id") or ""),
            "path": str(manifest.get("path") or ""),
            "sha256": str(manifest.get("sha256") or ""),
        },
        "asset_capsules_sha256": str(receipt.get("asset_capsules_sha256") or ""),
        "route_asset_capsules_sha256": str(receipt.get("route_asset_capsules_sha256") or ""),
        "public_coverage_sha256": str(coverage.get("coverage_sha256") or ""),
        "summary": {
            "mapped_asset_count": safe_count("mapped_asset_count"),
            "unmapped_asset_count": safe_count("unmapped_asset_count"),
            "currently_referenced_asset_count": safe_count("currently_referenced_asset_count"),
            "unapproved_current_asset_count": safe_count("unapproved_current_asset_count"),
            "current_copy_drift_asset_count": safe_count("current_copy_drift_asset_count"),
            "candidate_use_ready_count": candidate_ready_count,
        },
        "error": "",
    }


def editorial_asset_importer_readiness(repo_root: Path) -> dict[str, Any]:
    """Expose the trusted binary protocol without candidate-specific readiness."""

    unavailable: dict[str, Any] = {
        "available": False,
        "installed": False,
        "state": "unavailable",
        "import_protocol_available": False,
        "receipt_verification_available": False,
        "candidate_use_rights_ready": False,
        "candidate_asset_ready": False,
        "candidate_import_ready": False,
        "candidate_delivery_ready": False,
        "canonical_website_mutation": "never",
        "binary_read_scope": "",
        "candidate_write_scope": "",
        "transformations": "none",
        "release_eligible": False,
        "package_authority": "none",
        "deployment_authority": "none",
        "credential_access": "none",
        "network_access": "none",
        "error": "",
    }
    try:
        from aureon.operator import design_editorial_asset_candidate_importer as importer

        authority = importer.NON_AUTHORITATIVE_AUTHORITY
        protocol_available = (
            isinstance(authority, Mapping)
            and authority.get("canonical_website_mutation") == "never"
            and authority.get("candidate_write_scope") == "exact work-order-declared image targets only"
            and authority.get("binary_read_scope") == "content-addressed verified editorial intake only"
            and authority.get("transformations") == "none"
            and authority.get("release_eligible") is False
            and authority.get("package_authority") == "none"
            and authority.get("deployment_authority") == "none"
            and authority.get("credential_access") == "none"
            and authority.get("network_access") == "none"
            and callable(importer.import_editorial_assets_to_candidate)
            and callable(importer.verify_candidate_editorial_asset_import)
            and callable(importer.write_candidate_editorial_asset_import)
        )
    except Exception as exc:
        unavailable["error"] = f"{type(exc).__name__}: {exc}"
        return unavailable

    provenance = editorial_asset_provenance_readiness(repo_root)
    candidate_use_rights_ready = provenance.get("candidate_use_rights_ready") is True
    return {
        "available": protocol_available,
        "installed": True,
        "state": (
            "installed-awaiting-approved-asset"
            if protocol_available and not candidate_use_rights_ready
            else "installed-rights-ready-awaiting-candidate-import"
            if protocol_available
            else "importer-blocked"
        ),
        "import_protocol_available": protocol_available,
        "receipt_verification_available": protocol_available,
        "candidate_use_rights_ready": candidate_use_rights_ready,
        "candidate_asset_ready": False,
        "candidate_import_ready": False,
        "candidate_delivery_ready": False,
        "canonical_website_mutation": "never",
        "binary_read_scope": str(authority.get("binary_read_scope") or ""),
        "candidate_write_scope": str(authority.get("candidate_write_scope") or ""),
        "transformations": str(authority.get("transformations") or ""),
        "release_eligible": False,
        "package_authority": "none",
        "deployment_authority": "none",
        "credential_access": "none",
        "network_access": "none",
        "error": "",
    }


def investor_copy_quality_readiness(repo_root: Path) -> dict[str, Any]:
    """Expose copy-gate counts without public text snippets or findings."""

    unavailable: dict[str, Any] = {
        "available": False,
        "installed": False,
        "state": "unavailable",
        "policy_current": False,
        "copy_ready": False,
        "candidate_delivery_ready": False,
        "release_eligible": False,
        "package_authority": "none",
        "deployment_authority": "none",
        "policy": {},
        "summary": {
            "route_count": 0,
            "finding_count": 0,
            "blocker_count": 0,
            "warning_count": 0,
        },
        "error": "",
    }
    try:
        from aureon.operator.design_investor_copy_quality import (
            audit_investor_copy_quality_file,
        )

        receipt = audit_investor_copy_quality_file(repo_root=repo_root)
    except Exception as exc:
        unavailable["error"] = f"{type(exc).__name__}: {exc}"
        return unavailable

    raw_policy = receipt.get("policy")
    policy = raw_policy if isinstance(raw_policy, Mapping) else {}
    raw_summary = receipt.get("summary")
    summary = raw_summary if isinstance(raw_summary, Mapping) else {}

    def safe_count(field: str) -> int:
        value = summary.get(field)
        return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else 0

    return {
        "available": True,
        "installed": True,
        "state": str(receipt.get("state") or "blocked"),
        "policy_current": policy.get("current") is True,
        "copy_ready": receipt.get("passed") is True,
        "candidate_delivery_ready": False,
        "release_eligible": False,
        "package_authority": "none",
        "deployment_authority": "none",
        "policy": {
            "policy_id": str(policy.get("policy_id") or ""),
            "path": str(policy.get("path") or ""),
            "sha256": str(policy.get("sha256") or ""),
            "refresh_by": str(policy.get("refresh_by") or ""),
        },
        "summary": {
            "route_count": safe_count("route_count"),
            "finding_count": safe_count("finding_count"),
            "blocker_count": safe_count("blocker_count"),
            "warning_count": safe_count("warning_count"),
        },
        "error": "",
    }


def investor_copy_repair_readiness(repo_root: Path) -> dict[str, Any]:
    """Expose the exact source-bound repair protocol without issuing a contract.

    This static view does not select a source, create a work order or contract,
    stage copy, evaluate a candidate, or advance any browser/release gate.
    Operational readiness remains bound to one current DESIGN-COPY task, exact
    v4 work order, selected-source tree, policy, route, and claim capsule.
    """

    unavailable: dict[str, Any] = {
        "available": False,
        "installed": False,
        "state": "unavailable",
        "source_bound_protocol_available": False,
        "task_preflight_available": False,
        "selected_source_preflight_available": False,
        "contract_creation_available": False,
        "contract_verification_available": False,
        "candidate_reaudit_available": False,
        "current_contract_ready": False,
        "candidate_copy_ready": False,
        "candidate_delivery_ready": False,
        "canonical_website_mutation": "never",
        "candidate_staging": "never",
        "claim_register_mutation": "never",
        "human_copy_review": "required",
        "human_visual_acceptance": "required",
        "release_eligible": False,
        "package_authority": "none",
        "deployment_authority": "none",
        "credential_access": "none",
        "network_access": "none",
        "max_contract_lifetime_seconds": 0,
        "schemas": {},
        "error": "",
    }
    source_file = _safe_source_path(
        repo_root,
        "aureon/operator/design_investor_copy_repair.py",
    )
    try:
        from aureon.operator import design_investor_copy_repair as repair
    except Exception as exc:
        unavailable["installed"] = source_file.is_file()
        unavailable["error"] = f"{type(exc).__name__}: {exc}"
        return unavailable

    authority = repair.NON_AUTHORITATIVE_AUTHORITY
    max_lifetime_seconds = int(repair.MAX_CONTRACT_LIFETIME.total_seconds())
    protocol_available = (
        source_file.is_file()
        and repair.CONTRACT_SCHEMA == "aureon.design-investor-copy-repair.v1"
        and repair.PREFLIGHT_SCHEMA == "aureon.design-investor-copy-repair-preflight.v1"
        and repair.VERIFICATION_SCHEMA == "aureon.design-investor-copy-repair-verification.v1"
        and repair.EVALUATION_SCHEMA == "aureon.design-investor-copy-repair-evaluation.v1"
        and isinstance(authority, Mapping)
        and authority.get("canonical_website_mutation") == "never"
        and authority.get("candidate_staging") == "never"
        and authority.get("claim_register_mutation") == "never"
        and authority.get("human_copy_review") == "required"
        and authority.get("human_visual_acceptance") == "required"
        and authority.get("release_eligible") is False
        and authority.get("package_authority") == "none"
        and authority.get("deployment_authority") == "none"
        and authority.get("credential_access") == "none"
        and authority.get("network_access") == "none"
        and authority.get("release_authority") == "WebsiteOperator owner gate only"
        and 0 < max_lifetime_seconds <= 24 * 60 * 60
        and callable(repair.preflight_investor_copy_repair_contract)
        and callable(repair.preflight_investor_copy_repair_work_order)
        and callable(repair.create_investor_copy_repair_contract)
        and callable(repair.write_investor_copy_repair_contract)
        and callable(repair.verify_investor_copy_repair_contract)
        and callable(repair.evaluate_investor_copy_repair_candidate)
    )
    return {
        "available": protocol_available,
        "installed": True,
        "state": "installed-awaiting-exact-design-copy-task" if protocol_available else "protocol-blocked",
        "source_bound_protocol_available": protocol_available,
        "task_preflight_available": protocol_available,
        "selected_source_preflight_available": protocol_available,
        "contract_creation_available": protocol_available,
        "contract_verification_available": protocol_available,
        "candidate_reaudit_available": protocol_available,
        "current_contract_ready": False,
        "candidate_copy_ready": False,
        "candidate_delivery_ready": False,
        "canonical_website_mutation": "never",
        "candidate_staging": "never",
        "claim_register_mutation": "never",
        "human_copy_review": "required",
        "human_visual_acceptance": "required",
        "release_eligible": False,
        "package_authority": "none",
        "deployment_authority": "none",
        "credential_access": "none",
        "network_access": "none",
        "max_contract_lifetime_seconds": max_lifetime_seconds,
        "schemas": {
            "preflight": repair.PREFLIGHT_SCHEMA,
            "contract": repair.CONTRACT_SCHEMA,
            "verification": repair.VERIFICATION_SCHEMA,
            "evaluation": repair.EVALUATION_SCHEMA,
        },
        "error": "",
    }


def investor_copy_governance_readiness(repo_root: Path) -> dict[str, Any]:
    """Expose the exact owner-gated governance protocol without running it.

    Verification and full shadow simulation are read-only.  The installed
    apply function is discoverable only as an explicitly gated protocol:
    readiness never supplies an owner decision, treats broad system access as
    approval, invokes the function, or grants website/package/release authority.
    The registry deliberately does not inspect owner-decision files, so current
    decision presence and current apply authorisation always remain false here.
    """

    unavailable: dict[str, Any] = {
        "available": False,
        "installed": False,
        "state": "unavailable",
        "decision_verification_available": False,
        "simulation_available": False,
        "apply_protocol_available": False,
        "implementation_tooling_verified": False,
        "exact_owner_decision_required": True,
        "autonomous_owner_decision": False,
        "broad_access_approval_valid": False,
        "current_owner_decision_present": False,
        "current_apply_authorised": False,
        "current_apply_ready": False,
        "canonical_governance_mutation": "never without exact fresh owner decision and explicit apply",
        "canonical_governance_paths": [],
        "website_mutation": "never",
        "policy_mutation": "never",
        "candidate_authority": "none",
        "package_authority": "none",
        "release_eligible": False,
        "deployment_authority": "none",
        "credential_access": "none",
        "network_access": "none",
        "max_decision_age_seconds": 0,
        "schemas": {},
        "error": "",
    }
    source_file = _safe_source_path(
        repo_root,
        "aureon/operator/design_investor_copy_governance.py",
    )
    try:
        from aureon.operator import design_investor_copy_governance as governance
    except Exception as exc:
        unavailable["installed"] = source_file.is_file()
        unavailable["error"] = f"{type(exc).__name__}: {exc}"
        return unavailable

    authority = governance.NON_RELEASE_AUTHORITY
    governance_paths = list(governance.CANONICAL_GOVERNANCE_PATHS)
    apply_parameter = inspect.signature(governance.apply_investor_copy_governance_delta).parameters.get(
        "apply"
    )
    max_decision_age_seconds = int(governance.MAX_DECISION_AGE.total_seconds())
    try:
        source_text = source_file.read_text(encoding="utf-8")
    except OSError as exc:
        unavailable["installed"] = source_file.is_file()
        unavailable["error"] = f"{type(exc).__name__}: {exc}"
        return unavailable
    broad_access_guard_present = "broad_system_access_is_not_this_decision" in source_text
    protocol_available = (
        source_file.is_file()
        and governance.DECISION_SCHEMA == "aureon.investor-copy-governance-owner-decision.v1"
        and governance.VERIFICATION_SCHEMA == "aureon.investor-copy-governance-decision-verification.v1"
        and governance.PLAN_SCHEMA == "aureon.investor-copy-governance-application-plan.v1"
        and governance.APPLICATION_SCHEMA == "aureon.investor-copy-governance-application.v1"
        and governance.NAMED_OWNER == "Gary Leckey"
        and governance.APPROVE_STATE == "approve-exact-governance-delta"
        and set(governance.DECISION_STATES)
        == {"approve-exact-governance-delta", "reject", "request-revision"}
        and 0 < max_decision_age_seconds <= 24 * 60 * 60
        and governance_paths
        == [
            "data/website_operator/public_claim_evidence_register.v1.json",
            "data/website_operator/design_stakeholder_feedback.v1.json",
            "data/website_operator/investor_site_design_brief.v1.json",
        ]
        and isinstance(authority, Mapping)
        and authority.get("scope") == "exact owner-gated three-file claim-governance application only"
        and authority.get("website_mutation") == "never"
        and authority.get("policy_mutation") == "never"
        and authority.get("candidate_authority") == "none"
        and authority.get("package_authority") == "none"
        and authority.get("release_eligible") is False
        and authority.get("deployment_authority") == "none"
        and authority.get("credential_access") == "none"
        and authority.get("network_access") == "none"
        and broad_access_guard_present
        and callable(governance.verify_investor_copy_governance_decision)
        and callable(governance.plan_investor_copy_governance_application)
        and callable(governance.apply_investor_copy_governance_delta)
        and apply_parameter is not None
        and apply_parameter.default is False
    )
    return {
        "available": protocol_available,
        "installed": True,
        "state": ("installed-exact-owner-decision-required" if protocol_available else "protocol-blocked"),
        "decision_verification_available": protocol_available,
        "simulation_available": protocol_available,
        "apply_protocol_available": protocol_available,
        "implementation_tooling_verified": protocol_available,
        "exact_owner_decision_required": True,
        "autonomous_owner_decision": False,
        "broad_access_approval_valid": False,
        "current_owner_decision_present": False,
        "current_apply_authorised": False,
        "current_apply_ready": False,
        "canonical_governance_mutation": (
            "exact three-file transaction only after exact fresh owner decision and explicit apply"
        ),
        "canonical_governance_paths": governance_paths,
        "website_mutation": "never",
        "policy_mutation": "never",
        "candidate_authority": "none",
        "package_authority": "none",
        "release_eligible": False,
        "deployment_authority": "none",
        "credential_access": "none",
        "network_access": "none",
        "max_decision_age_seconds": max_decision_age_seconds,
        "schemas": {
            "decision": governance.DECISION_SCHEMA,
            "verification": governance.VERIFICATION_SCHEMA,
            "simulation": governance.PLAN_SCHEMA,
            "application": governance.APPLICATION_SCHEMA,
        },
        "error": "",
    }


def hnc_evidence_graph_readiness(repo_root: Path) -> dict[str, Any]:
    """Expose a tested source-neutral component without candidate authority."""

    unavailable: dict[str, Any] = {
        "available": False,
        "installed": False,
        "state": "unavailable",
        "component_bundle_ready": False,
        "candidate_transplant_ready": False,
        "candidate_delivery_ready": False,
        "release_eligible": False,
        "package_authority": "none",
        "deployment_authority": "none",
        "contract": {},
        "claim_ids": [],
        "bundle_sha256": "",
        "outputs": {},
        "error": "",
    }
    try:
        from aureon.operator.design_hnc_evidence_graph import (
            audit_hnc_evidence_graph_contract_file,
        )

        receipt = audit_hnc_evidence_graph_contract_file(repo_root=repo_root)
    except Exception as exc:
        unavailable["error"] = f"{type(exc).__name__}: {exc}"
        return unavailable

    raw_contract = receipt.get("contract")
    contract = raw_contract if isinstance(raw_contract, Mapping) else {}
    raw_register = receipt.get("claim_register")
    claim_register = raw_register if isinstance(raw_register, Mapping) else {}
    raw_outputs = receipt.get("outputs")
    outputs = raw_outputs if isinstance(raw_outputs, Mapping) else {}
    ready = receipt.get("passed") is True
    return {
        "available": True,
        "installed": True,
        "state": str(receipt.get("state") or "blocked"),
        "component_bundle_ready": ready,
        "candidate_transplant_ready": False,
        "candidate_delivery_ready": False,
        "release_eligible": False,
        "package_authority": "none",
        "deployment_authority": "none",
        "contract": {
            "component_id": str(contract.get("component_id") or ""),
            "path": str(contract.get("path") or ""),
            "sha256": str(contract.get("sha256") or ""),
        },
        "claim_ids": [str(item) for item in claim_register.get("claim_ids", []) if isinstance(item, str)],
        "bundle_sha256": str(receipt.get("bundle_sha256") or ""),
        "outputs": {
            str(name): {
                "bytes": (
                    value.get("bytes")
                    if isinstance(value, Mapping) and isinstance(value.get("bytes"), int)
                    else 0
                ),
                "sha256": (str(value.get("sha256") or "") if isinstance(value, Mapping) else ""),
            }
            for name, value in outputs.items()
        },
        "error": "",
    }


def design_evidence_brief_readiness(repo_root: Path) -> dict[str, Any]:
    """Return the current planning-only brief state without release authority.

    The static registry answers whether this capability is installed.  The
    brief itself is mutable evidence with its own freshness boundary, so this
    separate snapshot must never turn a passing planning audit into a claim
    that a candidate has been staged, validated, visually accepted, packaged,
    or released.
    """

    unavailable = {
        "available": False,
        "state": "unavailable",
        "brief_ready": False,
        "planning_pipeline_available": False,
        "candidate_delivery_ready": False,
        "release_eligible": False,
        "deployment_authority": "none",
        "brief": {},
        "research_refresh": {
            "declaration_path": "",
            "declaration_sha256": "",
            "state": "",
            "passed": False,
            "artwork": {"state": "", "cleared_for_use": False},
        },
        "stakeholder_feedback": {
            "feedback_id": "",
            "path": "",
            "sha256": "",
            "state": "",
            "passed": False,
            "signal_capsules_sha256": "",
            "signal_count": 0,
        },
        "next_required_stage": "restore the source-bound design-evidence brief",
        "error": "",
    }
    try:
        from aureon.operator.design_evidence_brief import audit_design_evidence_brief_file

        receipt = audit_design_evidence_brief_file(repo_root=repo_root)
    except Exception as exc:
        unavailable["error"] = f"{type(exc).__name__}: {exc}"
        return unavailable

    raw_brief = receipt.get("brief")
    brief = raw_brief if isinstance(raw_brief, Mapping) else {}
    raw_research_refresh = receipt.get("research_refresh")
    research_refresh = raw_research_refresh if isinstance(raw_research_refresh, Mapping) else {}
    raw_artwork = research_refresh.get("artwork")
    artwork = raw_artwork if isinstance(raw_artwork, Mapping) else {}
    raw_stakeholder_feedback = receipt.get("stakeholder_feedback")
    stakeholder_feedback = raw_stakeholder_feedback if isinstance(raw_stakeholder_feedback, Mapping) else {}
    raw_summary = receipt.get("summary")
    summary = raw_summary if isinstance(raw_summary, Mapping) else {}
    raw_signal_count = summary.get("feedback_signal_count")
    signal_count = (
        raw_signal_count
        if isinstance(raw_signal_count, int)
        and not isinstance(raw_signal_count, bool)
        and raw_signal_count >= 0
        else 0
    )
    brief_ready = receipt.get("passed") is True
    return {
        "available": True,
        "state": "brief-ready" if brief_ready else "brief-blocked",
        "brief_ready": brief_ready,
        "planning_pipeline_available": brief_ready,
        "candidate_delivery_ready": False,
        "release_eligible": False,
        "deployment_authority": "none",
        "brief": {
            "id": str(brief.get("brief_id") or ""),
            "path": str(brief.get("path") or ""),
            "sha256": str(brief.get("sha256") or ""),
            "refresh_by": str(brief.get("refresh_by") or ""),
        },
        "research_refresh": {
            "declaration_path": str(research_refresh.get("declaration_path") or ""),
            "declaration_sha256": str(research_refresh.get("declaration_sha256") or ""),
            "state": str(research_refresh.get("state") or ""),
            "passed": research_refresh.get("passed") is True,
            "artwork": {
                "state": str(artwork.get("state") or ""),
                "cleared_for_use": artwork.get("cleared_for_use") is True,
            },
        },
        "stakeholder_feedback": {
            "feedback_id": str(stakeholder_feedback.get("feedback_id") or ""),
            "path": str(stakeholder_feedback.get("path") or ""),
            "sha256": str(stakeholder_feedback.get("sha256") or ""),
            "state": str(stakeholder_feedback.get("state") or ""),
            "passed": stakeholder_feedback.get("passed") is True,
            "signal_capsules_sha256": str(stakeholder_feedback.get("signal_capsules_sha256") or ""),
            "signal_count": signal_count,
        },
        "next_required_stage": (
            "fresh reconciliation and an exact-path candidate work order"
            if brief_ready
            else "repair or refresh the source-bound brief before planning a candidate"
        ),
        "error": "",
    }


def staged_design_worker_broker_readiness(repo_root: Path) -> dict[str, Any]:
    """Expose an installed broker protocol without creating a worker lease.

    This is deliberately static discovery rather than operational readiness.
    A broker can be installed while no candidate exists, no lease has been
    issued, and delivery remains blocked by reconciliation and owner controls.
    """

    unavailable = {
        "available": False,
        "state": "unavailable",
        "lease_protocol_available": False,
        "candidate_delivery_ready": False,
        "canonical_website_mutation": "never",
        "release_eligible": False,
        "package_authority": "none",
        "deployment_authority": "none",
        "credential_access": "none",
        "receipt_integrity_scope": "",
        "adapter_id": "",
        "max_lease_seconds": 0,
        "error": "",
    }
    try:
        from aureon.autonomous import aureon_staged_design_worker_broker as broker

        authority = broker.AUTHORITY
        protocol_available = (
            isinstance(authority, Mapping)
            and authority.get("canonical_website_mutation")
            == "never by this broker or a staged design worker"
            and authority.get("release_eligible") is False
            and authority.get("package_authority") == "none"
            and authority.get("deployment_authority") == "none"
            and authority.get("credential_access") == "none"
            and authority.get("receipt_integrity_scope")
            == (
                "local accidental-drift detection only; it is not tamper-resistant against "
                "an account with direct filesystem write access"
            )
            and callable(broker.issue_staged_design_worker_lease)
            and callable(broker.submit_staged_design_worker_delivery)
            and isinstance(broker.DEFAULT_TRUSTED_ADAPTER_ID, str)
            and bool(broker.DEFAULT_TRUSTED_ADAPTER_ID)
            and isinstance(broker.MAX_LEASE_TTL_SECONDS, int)
            and 1 <= broker.MAX_LEASE_TTL_SECONDS <= 900
        )
    except Exception as exc:
        unavailable["error"] = f"{type(exc).__name__}: {exc}"
        return unavailable

    return {
        "available": protocol_available,
        "state": "installed-not-authorised" if protocol_available else "broker-blocked",
        "lease_protocol_available": protocol_available,
        "candidate_delivery_ready": False,
        "canonical_website_mutation": "never",
        "release_eligible": False,
        "package_authority": "none",
        "deployment_authority": "none",
        "credential_access": "none",
        "receipt_integrity_scope": str(authority.get("receipt_integrity_scope") or ""),
        "adapter_id": broker.DEFAULT_TRUSTED_ADAPTER_ID,
        "max_lease_seconds": broker.MAX_LEASE_TTL_SECONDS,
        "error": "",
    }


def motion_performance_budget_readiness(repo_root: Path) -> dict[str, Any]:
    """Expose the installed static-audit protocol without running an audit.

    Module presence cannot establish a motion-budget decision. A usable pass
    requires a separately issued receipt whose decision is exactly ``pass``
    and whose ``eligible_for_next_local_gate`` value is true.
    """

    unavailable: dict[str, Any] = {
        "available": False,
        "installed": False,
        "state": "unavailable",
        "audit_protocol_available": False,
        "receipt_replay_available": False,
        "audit_executed": False,
        "decision_status": "not-evaluated",
        "decision_passed": False,
        "eligible_for_next_local_gate": False,
        "pass_inferred_from_installation": False,
        "pass_requirement": (
            "an exact receipt with decision.status pass and decision.eligible_for_next_local_gate true"
        ),
        "candidate_authority": "none",
        "candidate_validation_authority": "none",
        "promotion_authority": "none",
        "canonical_website_mutation": "none",
        "package_authority": "none",
        "release_authority": "none",
        "release_eligible": False,
        "deployment_authority": "none",
        "credential_access": "none",
        "network_access": "none",
        "error": "",
    }
    source_file = _safe_source_path(
        repo_root,
        "aureon/operator/design_motion_performance_budget.py",
    )
    try:
        from aureon.operator import design_motion_performance_budget as motion_budget

        authority = motion_budget.AUTHORITY
        protocol_available = (
            source_file.is_file()
            and motion_budget.CONFIG_SCHEMA == "aureon.design-motion-performance-budget-config.v1"
            and motion_budget.RECEIPT_SCHEMA == "aureon.design-motion-performance-budget.v1"
            and isinstance(authority, Mapping)
            and authority.get("audit_evidence_only") is True
            and authority.get("candidate_authority") == "none"
            and authority.get("canonical_mutation_authority") == "none"
            and authority.get("package_authority") == "none"
            and authority.get("release_authority") == "none"
            and authority.get("deployment_authority") == "none"
            and authority.get("credential_access") == "none"
            and authority.get("network_access") == "none"
            and callable(motion_budget.snapshot_static_tree)
            and callable(motion_budget.audit_motion_performance_budget)
            and callable(motion_budget.validate_motion_performance_receipt)
        )
    except Exception as exc:
        unavailable["installed"] = source_file.is_file()
        unavailable["error"] = f"{type(exc).__name__}: {exc}"
        return unavailable

    return {
        **unavailable,
        "available": protocol_available,
        "installed": True,
        "state": "installed-not-authorised" if protocol_available else "protocol-blocked",
        "audit_protocol_available": protocol_available,
        "receipt_replay_available": protocol_available,
    }


def candidate_test_evidence_readiness(repo_root: Path) -> dict[str, Any]:
    """Expose the installed trusted-test protocol without executing any test.

    Worker-supplied pass strings are never evidence. Structural receipt
    verification also never attests origin: trusted orchestration must seal
    the immutable receipt independently and the verifier must report
    ``evidence_passed`` true before the observation can be consumed.
    """

    unavailable: dict[str, Any] = {
        "available": False,
        "installed": False,
        "state": "unavailable",
        "execution_protocol_available": False,
        "structural_verification_available": False,
        "immutable_writer_available": False,
        "reviewed_node_toolchain": {
            "protocol_available": False,
            "schema": EXPECTED_NODE_BINDING_SCHEMA,
            "locator_authority": EXPECTED_NODE_LOCATOR_AUTHORITY,
            "absolute_path_size_sha256_bound": False,
            "ambient_path_fallback_allowed": False,
            "resolved": False,
            "executed": False,
        },
        "bounded_process": {
            "protocol_available": False,
            "launcher": "subprocess.Popen",
            "shell": False,
            "max_stream_bytes": EXPECTED_TEST_EVIDENCE_MAX_STREAM_BYTES,
            "retry_authority": "none",
            "executed": False,
        },
        "execution_authorised": False,
        "test_suite_executed": False,
        "worker_pass_strings_are_evidence": False,
        "structural_verification_passed": False,
        "origin_attested": False,
        "trusted_orchestration_seal_required": True,
        "evidence_passed": False,
        "pass_inferred_from_installation": False,
        "pass_requirement": (
            "an independently preserved trusted-orchestration seal plus strict verification "
            "with origin_attested false and evidence_passed true"
        ),
        "candidate_validation_authority": "none",
        "promotion_authority": "none",
        "canonical_website_mutation": "none",
        "package_authority": "none",
        "release_authority": "none",
        "release_eligible": False,
        "deployment_authority": "none",
        "credential_access": "none",
        "error": "",
    }
    source_file = _safe_source_path(
        repo_root,
        "aureon/operator/design_candidate_test_evidence.py",
    )
    try:
        from aureon.operator import design_candidate_test_evidence as test_evidence

        policy_authority = test_evidence.POLICY_AUTHORITY
        evidence_authority = test_evidence.EVIDENCE_AUTHORITY
        node_binding = test_evidence.NODE_TOOLCHAIN_BINDING
        node_path = node_binding.get("absolute_path") if isinstance(node_binding, Mapping) else None
        node_size = node_binding.get("size_bytes") if isinstance(node_binding, Mapping) else None
        node_sha256 = node_binding.get("sha256") if isinstance(node_binding, Mapping) else None
        node_binding_protocol_available = (
            isinstance(node_binding, Mapping)
            and node_binding.get("schema") == EXPECTED_NODE_BINDING_SCHEMA
            and node_binding.get("locator_authority") == EXPECTED_NODE_LOCATOR_AUTHORITY
            and isinstance(node_path, str)
            and Path(node_path).is_absolute()
            and isinstance(node_size, int)
            and not isinstance(node_size, bool)
            and node_size > 0
            and isinstance(node_sha256, str)
            and len(node_sha256) == 64
            and all(character in "0123456789ABCDEF" for character in node_sha256)
            and callable(test_evidence._json_sha256)  # noqa: SLF001
            and test_evidence._json_sha256(dict(node_binding))  # noqa: SLF001
            == test_evidence.NODE_TOOLCHAIN_BINDING_SHA256
            and callable(test_evidence._resolve_reviewed_node_toolchain)  # noqa: SLF001
            and callable(test_evidence._resolve_tool)  # noqa: SLF001
        )
        bounded_process_source = inspect.getsource(test_evidence._run_process_once)  # noqa: SLF001
        bounded_process_protocol_available = (
            test_evidence.MAX_STREAM_BYTES == EXPECTED_TEST_EVIDENCE_MAX_STREAM_BYTES
            and callable(test_evidence._run_process_once)  # noqa: SLF001
            and "tempfile.TemporaryFile" in bounded_process_source
            and "subprocess.Popen(" in bounded_process_source
            and "shell=False" in bounded_process_source
            and "MAX_STREAM_BYTES" in bounded_process_source
            and "process.kill()" in bounded_process_source
        )

        def retains_boundary(authority: object) -> bool:
            return (
                isinstance(authority, Mapping)
                and authority.get("canonical_website_mutation") == "none"
                and authority.get("candidate_validation_authority") == "none"
                and authority.get("promotion_authority") == "none"
                and authority.get("package_authority") == "none"
                and authority.get("release_authority") == "none"
                and authority.get("deployment_authority") == "none"
                and authority.get("credential_access") == "none"
            )

        protocol_available = (
            source_file.is_file()
            and test_evidence.POLICY_SCHEMA == "aureon.design-candidate-test-policy.v1"
            and test_evidence.RECEIPT_SCHEMA == "aureon.design-candidate-test-evidence.v2"
            and test_evidence.VERIFICATION_SCHEMA == "aureon.design-candidate-test-evidence-verification.v2"
            and retains_boundary(policy_authority)
            and retains_boundary(evidence_authority)
            and test_evidence.LOCAL_EXECUTION_BOUNDARY.get("os_network_sandbox") is False
            and test_evidence.LOCAL_EXECUTION_BOUNDARY.get("filesystem_sandbox") is False
            and node_binding_protocol_available
            and bounded_process_protocol_available
            and callable(test_evidence.execute_candidate_test_evidence)
            and callable(test_evidence.validate_candidate_test_evidence_receipt)
            and callable(test_evidence.verify_candidate_test_evidence_receipt)
            and callable(test_evidence.write_candidate_test_evidence_receipt)
        )
    except Exception as exc:
        unavailable["installed"] = source_file.is_file()
        unavailable["error"] = f"{type(exc).__name__}: {exc}"
        return unavailable

    return {
        **unavailable,
        "available": protocol_available,
        "installed": True,
        "state": "installed-not-authorised" if protocol_available else "protocol-blocked",
        "execution_protocol_available": protocol_available,
        "structural_verification_available": protocol_available,
        "immutable_writer_available": protocol_available,
        "reviewed_node_toolchain": {
            "protocol_available": node_binding_protocol_available,
            "schema": EXPECTED_NODE_BINDING_SCHEMA,
            "locator_authority": EXPECTED_NODE_LOCATOR_AUTHORITY,
            "absolute_path_size_sha256_bound": node_binding_protocol_available,
            "ambient_path_fallback_allowed": False,
            "resolved": False,
            "executed": False,
        },
        "bounded_process": {
            "protocol_available": bounded_process_protocol_available,
            "launcher": "subprocess.Popen",
            "shell": False,
            "max_stream_bytes": EXPECTED_TEST_EVIDENCE_MAX_STREAM_BYTES,
            "retry_authority": "none",
            "executed": False,
        },
    }


def candidate_qa_control_plane_readiness(repo_root: Path) -> dict[str, Any]:
    """Discover the fixed V2 candidate-QA chain without executing any control.

    Installation establishes only that the reviewed static adapter, immutable
    writer, fixed compilers, V2 schema, and runner entrypoints are present with
    their non-authoritative boundaries intact. It never compiles a policy,
    writes a claim, runs motion or tests, enters a browser gate, or infers a
    pass.
    """

    unavailable: dict[str, Any] = {
        "available": False,
        "installed": False,
        "state": "unavailable",
        "static_qa_available": False,
        "fixed_test_policy_compiler_available": False,
        "fixed_motion_policy_compiler_available": False,
        "handle_bound_immutable_writer_available": False,
        "v2_runner_available": False,
        "candidate_test_evidence_runtime_available": False,
        "v2_schema_available": False,
        "v2_runbook_available": False,
        "compiler_verification_ingress": {
            "discovery_mode": "metadata-only-no-subprocess",
            "discovery_subprocess_launched": False,
            "imported_api": {
                "scope": "drift-check-only",
                "motion_read_only_verifier_available": False,
                "test_read_only_verifier_available": False,
                "pre_import_source_authentication": False,
            },
            "sealed_direct_file_read_only": {
                "protocol_available": False,
                "motion_protocol_available": False,
                "test_protocol_available": False,
                "executed": False,
                "python_flags": list(EXPECTED_SEALED_COMPILER_PYTHON_FLAGS),
                "motion_verify_flag": EXPECTED_MOTION_VERIFY_FLAG,
                "test_verify_flag": EXPECTED_TEST_VERIFY_FLAG,
                "source_closure_helper_available": False,
            },
            "runner_delegation": {
                "protocol_available": False,
                "required_for_candidate_qa": True,
                "bounded_popen_protocol_available": False,
                "launcher": "subprocess.Popen",
                "shell": False,
                "timeout_seconds": EXPECTED_SEALED_COMPILER_TIMEOUT_SECONDS,
                "max_aggregate_output_bytes": EXPECTED_SEALED_COMPILER_MAX_OUTPUT_BYTES,
                "retry_authority": "none",
                "invoked": False,
            },
        },
        "execution_order": list(EXPECTED_CANDIDATE_QA_ORDER),
        "execution_order_enforced": False,
        "policy_selection_authority": "none",
        "threshold_selection_authority": "none",
        "retry_authority": "none",
        "qa_execution_authorised": False,
        "qa_executed": False,
        "motion_audit_executed": False,
        "test_suite_executed": False,
        "browser_gate_executed": False,
        "qa_passed": False,
        "pass_inferred_from_installation": False,
        "candidate_creation_authority": "none",
        "candidate_mutation_authority": "none",
        "candidate_validation_authority": "none",
        "canonical_website_mutation": "none",
        "promotion_authority": "none",
        "package_authority": "none",
        "release_authority": "none",
        "release_eligible": False,
        "deployment_authority": "none",
        "credential_access": "none",
        "error": "",
    }
    source_paths = {
        "secure_writer": _safe_source_path(
            repo_root,
            "aureon/operator/secure_immutable_artifact.py",
        ),
        "static_qa": _safe_source_path(
            repo_root,
            "aureon/operator/design_candidate_static_qa.py",
        ),
        "test_policy_compiler": _safe_source_path(
            repo_root,
            "aureon/operator/design_candidate_test_policy_compiler.py",
        ),
        "motion_policy_compiler": _safe_source_path(
            repo_root,
            "aureon/operator/design_candidate_motion_policy_compiler.py",
        ),
        "source_closure": _safe_source_path(
            repo_root,
            "aureon/operator/design_candidate_source_closure.py",
        ),
        "runner": _safe_source_path(
            repo_root,
            "aureon/autonomous/aureon_public_website_design_runner.py",
        ),
        "test_evidence": _safe_source_path(
            repo_root,
            "aureon/operator/design_candidate_test_evidence.py",
        ),
        "runner_schema": _safe_source_path(
            repo_root,
            "docs/research/schemas/AUREON_PUBLIC_WEBSITE_DESIGN_DELIVERY_RUNNER_V2.schema.json",
        ),
        "runner_runbook": _safe_source_path(
            repo_root,
            "docs/research/AUREON_PUBLIC_WEBSITE_DESIGN_DELIVERY_V2_RUNBOOK.md",
        ),
    }
    installed = all(path.is_file() for path in source_paths.values())
    unavailable["installed"] = installed
    candidate_test_runtime = candidate_test_evidence_readiness(repo_root)
    candidate_test_node = candidate_test_runtime.get("reviewed_node_toolchain")
    candidate_test_process = candidate_test_runtime.get("bounded_process")
    candidate_test_runtime_available = (
        candidate_test_runtime.get("available") is True
        and isinstance(candidate_test_node, Mapping)
        and candidate_test_node.get("protocol_available") is True
        and candidate_test_node.get("ambient_path_fallback_allowed") is False
        and candidate_test_node.get("resolved") is False
        and candidate_test_node.get("executed") is False
        and isinstance(candidate_test_process, Mapping)
        and candidate_test_process.get("protocol_available") is True
        and candidate_test_process.get("launcher") == "subprocess.Popen"
        and candidate_test_process.get("shell") is False
        and candidate_test_process.get("max_stream_bytes") == EXPECTED_TEST_EVIDENCE_MAX_STREAM_BYTES
        and candidate_test_process.get("retry_authority") == "none"
        and candidate_test_process.get("executed") is False
    )

    try:
        from aureon.autonomous import aureon_public_website_design_runner as delivery_runner
        from aureon.operator import design_candidate_motion_policy_compiler as motion_compiler
        from aureon.operator import design_candidate_source_closure as source_closure
        from aureon.operator import design_candidate_static_qa as static_qa
        from aureon.operator import design_candidate_test_policy_compiler as test_policy_compiler
        from aureon.operator import secure_immutable_artifact

        static_authority = static_qa.AUTHORITY
        static_available = (
            source_paths["static_qa"].is_file()
            and static_qa.SCHEMA == "aureon.design-candidate-static-qa.v1"
            and tuple(static_qa.MODES)
            == (
                "website-operator-static",
                "v28-design-system-static",
                "v28-metadata-ethos-static",
            )
            and isinstance(static_authority, Mapping)
            and static_authority.get("canonical_website_mutation") == "none"
            and static_authority.get("candidate_mutation") == "none"
            and static_authority.get("package_authority") == "none"
            and static_authority.get("deployment_authority") == "none"
            and static_authority.get("release_eligible") is False
            and callable(static_qa.audit_candidate_static)
        )

        source_closure_available = (
            source_paths["source_closure"].is_file()
            and source_closure.SOURCE_CLOSURE_SCHEMA == EXPECTED_SOURCE_CLOSURE_SCHEMA
            and source_closure.SOURCE_CLOSURE_ALGORITHM == EXPECTED_SOURCE_CLOSURE_ALGORITHM
            and source_closure.SOURCE_CLOSURE_HELPER_PATH
            == "aureon/operator/design_candidate_source_closure.py"
            and callable(source_closure.build_source_closure)
            and callable(source_closure.verify_source_closure)
            and callable(source_closure.install_verified_source_importer)
        )

        test_authority = test_policy_compiler.AUTHORITY
        test_imported_verifier_available = (
            source_paths["test_policy_compiler"].is_file()
            and isinstance(test_authority, Mapping)
            and test_authority.get("executable_source_ingress") == EXPECTED_COMPILER_EXECUTABLE_SOURCE_INGRESS
            and callable(test_policy_compiler.verify_compiled_candidate_test_policy_file)
        )
        test_compiler_available = (
            source_paths["test_policy_compiler"].is_file()
            and test_policy_compiler.COMPILATION_SCHEMA
            == "aureon.design-candidate-test-policy-compilation.v2"
            and test_policy_compiler.VERIFICATION_SCHEMA
            == "aureon.design-candidate-test-policy-verification.v2"
            and tuple(test_policy_compiler.REQUIRED_COMMAND_IDS) == EXPECTED_CANDIDATE_TEST_COMMAND_IDS
            and test_policy_compiler.SOURCE_TO_CANDIDATE_COMMAND.get(test_policy_compiler.COMPOSITE_SOURCE_ID)
            is None
            and isinstance(test_authority, Mapping)
            and test_authority.get("executable_source_ingress") == EXPECTED_COMPILER_EXECUTABLE_SOURCE_INGRESS
            and test_authority.get("worker_command_selection") == "none"
            and test_authority.get("test_execution_authority") == "none"
            and test_authority.get("candidate_validation_authority") == "none"
            and test_authority.get("promotion_authority") == "none"
            and test_authority.get("package_authority") == "none"
            and test_authority.get("release_authority") == "none"
            and test_authority.get("deployment_authority") == "none"
            and test_authority.get("composite_visual_gate") == "deferred-not-passed"
            and callable(test_policy_compiler.compile_candidate_test_policy)
            and callable(test_policy_compiler.verify_compiled_candidate_test_policy_file)
        )
        test_sealed_read_only_available = (
            test_compiler_available
            and source_closure_available
            and tuple(test_policy_compiler._SEALED_CLI_FLAGS)  # noqa: SLF001
            == EXPECTED_SEALED_COMPILER_PYTHON_FLAGS
            and test_policy_compiler.SOURCE_CLOSURE_SCHEMA == EXPECTED_SOURCE_CLOSURE_SCHEMA
            and test_policy_compiler.SOURCE_CLOSURE_ALGORITHM == EXPECTED_SOURCE_CLOSURE_ALGORITHM
            and test_policy_compiler.SOURCE_CLOSURE_HELPER_PATH == source_closure.SOURCE_CLOSURE_HELPER_PATH
            and source_closure.SOURCE_CLOSURE_HELPER_PATH in tuple(test_policy_compiler.SOURCE_CLOSURE_ROOTS)
            and callable(test_policy_compiler._require_sealed_cli_runtime)  # noqa: SLF001
            and callable(test_policy_compiler.main)
        )

        motion_authority = motion_compiler.AUTHORITY
        motion_imported_verifier_available = (
            source_paths["motion_policy_compiler"].is_file()
            and isinstance(motion_authority, Mapping)
            and motion_authority.get("executable_source_ingress")
            == EXPECTED_COMPILER_EXECUTABLE_SOURCE_INGRESS
            and callable(motion_compiler.verify_compiled_candidate_motion_config_file)
        )
        motion_compiler_available = (
            source_paths["motion_policy_compiler"].is_file()
            and motion_compiler.COMPILATION_SCHEMA == "aureon.design-candidate-motion-config-compilation.v2"
            and motion_compiler.VERIFICATION_SCHEMA == "aureon.design-candidate-motion-config-verification.v2"
            and dict(motion_compiler.FIXED_THRESHOLDS) == EXPECTED_CANDIDATE_MOTION_THRESHOLDS
            and dict(motion_compiler.FIXED_REMOTE_ORIGINS) == {"allowed": [], "allow_data_urls": False}
            and dict(motion_compiler.FIXED_POLICY) == EXPECTED_CANDIDATE_MOTION_POLICY
            and motion_compiler.EXPECTED_DOCTRINE_SHA256
            == "BD51BE9B2A8F48BDFE12EDC7A75DF234C0BEDEABE047DD093938ACEA7E289D4D"
            and isinstance(motion_authority, Mapping)
            and motion_authority.get("executable_source_ingress")
            == EXPECTED_COMPILER_EXECUTABLE_SOURCE_INGRESS
            and motion_authority.get("worker_threshold_selection") == "none"
            and motion_authority.get("audit_execution_authority") == "none"
            and motion_authority.get("candidate_validation_authority") == "none"
            and motion_authority.get("promotion_authority") == "none"
            and motion_authority.get("package_authority") == "none"
            and motion_authority.get("release_authority") == "none"
            and motion_authority.get("deployment_authority") == "none"
            and callable(motion_compiler.compile_candidate_motion_config)
            and callable(motion_compiler.verify_compiled_candidate_motion_config_file)
        )
        motion_sealed_read_only_available = (
            motion_compiler_available
            and source_closure_available
            and tuple(motion_compiler._SEALED_CLI_FLAGS)  # noqa: SLF001
            == EXPECTED_SEALED_COMPILER_PYTHON_FLAGS
            and motion_compiler.SOURCE_CLOSURE_SCHEMA == EXPECTED_SOURCE_CLOSURE_SCHEMA
            and motion_compiler.SOURCE_CLOSURE_ALGORITHM == EXPECTED_SOURCE_CLOSURE_ALGORITHM
            and motion_compiler.SOURCE_CLOSURE_HELPER_PATH == source_closure.SOURCE_CLOSURE_HELPER_PATH
            and source_closure.SOURCE_CLOSURE_HELPER_PATH in tuple(motion_compiler.SOURCE_CLOSURE_ROOTS)
            and callable(motion_compiler._require_sealed_cli_runtime)  # noqa: SLF001
            and callable(motion_compiler.main)
        )

        writer_available = (
            source_paths["secure_writer"].is_file()
            and callable(secure_immutable_artifact.write_new_file)
            and isinstance(secure_immutable_artifact.SecureImmutableArtifactError, type)
            and "Handle-bound exclusive creation" in str(secure_immutable_artifact.__doc__ or "")
        )

        runner_authority = delivery_runner.AUTHORITY
        qa_authority = delivery_runner._CANDIDATE_QA_AUTHORITY
        transitions = delivery_runner._ALLOWED_STATE_TRANSITIONS
        runner_available = (
            source_paths["runner"].is_file()
            and delivery_runner.DELIVERY_JOB_SCHEMA == "aureon.public-website-design-delivery-job.v2"
            and delivery_runner.LEGACY_DELIVERY_JOB_SCHEMA == "aureon.public-website-design-delivery-job.v1"
            and delivery_runner.CANDIDATE_QA_SCHEMA == "aureon.public-website-design-candidate-qa.v2"
            and isinstance(runner_authority, Mapping)
            and runner_authority.get("canonical_website_mutation") == "never by this runner or a design agent"
            and runner_authority.get("release_eligible") is False
            and runner_authority.get("package_authority") == "none"
            and runner_authority.get("deployment_authority") == "none"
            and isinstance(qa_authority, Mapping)
            and qa_authority.get("candidate_mutation") == "none"
            and qa_authority.get("worker_qa_authority") == "none"
            and qa_authority.get("threshold_override_authority") == "none"
            and qa_authority.get("test_selection_authority") == "none"
            and qa_authority.get("retry_authority") == "none"
            and qa_authority.get("promotion_authority") == "none"
            and qa_authority.get("package_authority") == "none"
            and qa_authority.get("release_authority") == "none"
            and qa_authority.get("deployment_authority") == "none"
            and transitions.get("candidate-validated")
            == frozenset({"candidate-qa-verified", "candidate-qa-repair-required"})
            and transitions.get("candidate-qa-verified")
            == frozenset({"awaiting-browser-evidence", "initial-gate-rejected"})
            and callable(delivery_runner.evaluate_delivery_candidate_qa)
            and callable(delivery_runner.evaluate_delivery_initial_gate)
        )
        bounded_runner_source = inspect.getsource(
            delivery_runner._run_bounded_sealed_process  # noqa: SLF001
        )
        bounded_runner_protocol_available = (
            delivery_runner.SEALED_COMPILER_TIMEOUT_SECONDS == EXPECTED_SEALED_COMPILER_TIMEOUT_SECONDS
            and delivery_runner.SEALED_COMPILER_MAX_OUTPUT_BYTES == EXPECTED_SEALED_COMPILER_MAX_OUTPUT_BYTES
            and callable(delivery_runner._stop_sealed_process)  # noqa: SLF001
            and callable(delivery_runner._run_bounded_sealed_process)  # noqa: SLF001
            and "subprocess.Popen(" in bounded_runner_source
            and "stdout=subprocess.PIPE" in bounded_runner_source
            and "stderr=subprocess.PIPE" in bounded_runner_source
            and "shell=False" in bounded_runner_source
            and "SEALED_COMPILER_MAX_OUTPUT_BYTES" in bounded_runner_source
            and "_stop_sealed_process" in bounded_runner_source
            and "no retry is allowed" in bounded_runner_source
        )
        runner_sealed_delegation_available = (
            runner_available
            and tuple(delivery_runner.SEALED_COMPILER_PYTHON_FLAGS) == EXPECTED_SEALED_COMPILER_PYTHON_FLAGS
            and bounded_runner_protocol_available
            and motion_authority == delivery_runner.MOTION_POLICY_COMPILER_AUTHORITY
            and test_authority == delivery_runner.TEST_POLICY_COMPILER_AUTHORITY
            and callable(delivery_runner._run_sealed_compiler_verification)  # noqa: SLF001
            and callable(
                delivery_runner._verify_compiled_candidate_motion_config_file_sealed  # noqa: SLF001
            )
            and callable(
                delivery_runner._verify_compiled_candidate_test_policy_file_sealed  # noqa: SLF001
            )
        )
    except Exception as exc:
        unavailable["error"] = f"{type(exc).__name__}: {exc}"
        return unavailable

    protocol_available = (
        installed
        and static_available
        and test_compiler_available
        and motion_compiler_available
        and source_closure_available
        and test_sealed_read_only_available
        and motion_sealed_read_only_available
        and writer_available
        and runner_available
        and runner_sealed_delegation_available
        and candidate_test_runtime_available
    )
    return {
        **unavailable,
        "available": protocol_available,
        "installed": installed,
        "state": "installed-not-authorised" if protocol_available else "protocol-blocked",
        "static_qa_available": static_available,
        "fixed_test_policy_compiler_available": test_compiler_available,
        "fixed_motion_policy_compiler_available": motion_compiler_available,
        "handle_bound_immutable_writer_available": writer_available,
        "v2_runner_available": runner_available,
        "candidate_test_evidence_runtime_available": candidate_test_runtime_available,
        "v2_schema_available": source_paths["runner_schema"].is_file(),
        "v2_runbook_available": source_paths["runner_runbook"].is_file(),
        "compiler_verification_ingress": {
            "discovery_mode": "metadata-only-no-subprocess",
            "discovery_subprocess_launched": False,
            "imported_api": {
                "scope": "drift-check-only",
                "motion_read_only_verifier_available": motion_imported_verifier_available,
                "test_read_only_verifier_available": test_imported_verifier_available,
                "pre_import_source_authentication": False,
            },
            "sealed_direct_file_read_only": {
                "protocol_available": (motion_sealed_read_only_available and test_sealed_read_only_available),
                "motion_protocol_available": motion_sealed_read_only_available,
                "test_protocol_available": test_sealed_read_only_available,
                "executed": False,
                "python_flags": list(EXPECTED_SEALED_COMPILER_PYTHON_FLAGS),
                "motion_verify_flag": EXPECTED_MOTION_VERIFY_FLAG,
                "test_verify_flag": EXPECTED_TEST_VERIFY_FLAG,
                "source_closure_helper_available": source_closure_available,
            },
            "runner_delegation": {
                "protocol_available": runner_sealed_delegation_available,
                "required_for_candidate_qa": True,
                "bounded_popen_protocol_available": bounded_runner_protocol_available,
                "launcher": "subprocess.Popen",
                "shell": False,
                "timeout_seconds": EXPECTED_SEALED_COMPILER_TIMEOUT_SECONDS,
                "max_aggregate_output_bytes": EXPECTED_SEALED_COMPILER_MAX_OUTPUT_BYTES,
                "retry_authority": "none",
                "invoked": False,
            },
        },
        "execution_order_enforced": protocol_available,
    }


def discover_design_capability_registry(repo_root: Path | None = None) -> dict[str, Any]:
    """Return one source-bound, non-authoritative capability registry.

    Discovery has no network, hosting, release-package, or deployment side
    effects.  The returned payload contains a verification result so callers
    can reject stale copies when any declared source changes afterwards.
    """

    root = _find_repo_root(repo_root)
    registry: dict[str, Any] = {
        "schema": REGISTRY_SCHEMA,
        "generated_at": _utc_iso(),
        "repo_root": str(root),
        "authority": dict(NON_AUTHORITATIVE_AUTHORITY),
        "sources": [
            _source_snapshot(root, identifier, relative_path, markers)
            for identifier, relative_path, markers in SOURCE_SPECS
        ],
        "design_council_roles": _design_council_roles(root),
        "coding_roles": _coding_roles(root),
        "website_operator_capabilities": _operator_capabilities(root),
        "owner_source_reconciliation_readiness": owner_source_reconciliation_readiness(root),
        "website_source_rationalisation_readiness": website_source_rationalisation_readiness(root),
        "website_runtime_optimisation_readiness": website_runtime_optimisation_readiness(root),
        "website_runtime_measurement_static_integrity_readiness": (
            website_runtime_measurement_static_integrity_readiness(root)
        ),
        "design_research_refresh_readiness": design_research_refresh_readiness(root),
        "stakeholder_feedback_readiness": stakeholder_feedback_readiness(root),
        "editorial_rights_decision_preparation_readiness": (
            editorial_rights_decision_preparation_readiness(root)
        ),
        "editorial_asset_provenance_readiness": editorial_asset_provenance_readiness(root),
        "editorial_asset_importer_readiness": editorial_asset_importer_readiness(root),
        "investor_copy_quality_readiness": investor_copy_quality_readiness(root),
        "investor_copy_repair_readiness": investor_copy_repair_readiness(root),
        "investor_copy_governance_readiness": investor_copy_governance_readiness(root),
        "hnc_evidence_graph_readiness": hnc_evidence_graph_readiness(root),
        "design_evidence_brief_readiness": design_evidence_brief_readiness(root),
        "staged_design_worker_broker_readiness": staged_design_worker_broker_readiness(root),
        "motion_performance_budget_readiness": motion_performance_budget_readiness(root),
        "candidate_test_evidence_readiness": candidate_test_evidence_readiness(root),
        "candidate_qa_control_plane_readiness": candidate_qa_control_plane_readiness(root),
    }
    registry["verification"] = verify_design_capability_registry(registry, repo_root=root)
    return registry


def _check(identifier: str, passed: bool, message: str) -> dict[str, Any]:
    return {"id": identifier, "passed": passed, "message": message}


def _registry_names(rows: object, field: str) -> set[str]:
    if not isinstance(rows, list):
        return set()
    names: set[str] = set()
    for item in rows:
        if not isinstance(item, Mapping):
            continue
        value = item.get(field)
        if isinstance(value, str) and value.strip():
            names.add(value.strip())
    return names


def verify_design_capability_registry(
    registry: Mapping[str, Any], *, repo_root: Path | None = None
) -> dict[str, Any]:
    """Check a registry against the current local declarations without release authority."""

    root = _find_repo_root(repo_root)
    checks: list[dict[str, Any]] = []

    checks.append(
        _check(
            "schema",
            registry.get("schema") == REGISTRY_SCHEMA,
            "Registry schema must match the current design-capability contract.",
        )
    )
    checks.append(
        _check(
            "non-authoritative-boundary",
            registry.get("authority") == NON_AUTHORITATIVE_AUTHORITY,
            "Registry must retain no deployment authority and required human/release gates.",
        )
    )

    source_rows = registry.get("sources")
    source_ok = isinstance(source_rows, list) and len(source_rows) == len(SOURCE_SPECS)
    if isinstance(source_rows, list):
        expected_source_ids = {item[0] for item in SOURCE_SPECS}
        actual_source_ids = _registry_names(source_rows, "id")
        source_ok = source_ok and actual_source_ids == expected_source_ids
        for row in source_rows:
            if not isinstance(row, Mapping):
                source_ok = False
                continue
            try:
                source_path = _safe_source_path(root, row.get("path"))
            except DesignCapabilityRegistryError:
                source_ok = False
                continue
            expected_hash = row.get("sha256")
            available = source_path.is_file()
            current_hash = _sha256(source_path) if available else ""
            markers = row.get("required_markers")
            text = source_path.read_text(encoding="utf-8", errors="replace") if available else ""
            marker_ok = isinstance(markers, list) and all(
                isinstance(marker, str) and marker in text for marker in markers
            )
            if (
                not available
                or not isinstance(expected_hash, str)
                or expected_hash != current_hash
                or not marker_ok
            ):
                source_ok = False
    checks.append(
        _check(
            "source-freshness",
            source_ok,
            "Every declared source must exist, retain its required markers, and match its recorded SHA-256.",
        )
    )

    registered_rationalisation = registry.get("website_source_rationalisation_readiness")
    live_rationalisation = website_source_rationalisation_readiness(root)
    rationalisation_ok = (
        isinstance(registered_rationalisation, Mapping)
        and dict(registered_rationalisation) == live_rationalisation
        and live_rationalisation.get("available") is True
        and live_rationalisation.get("state") == "installed-owner-decision-required"
        and live_rationalisation.get("planning_protocol_available") is True
        and live_rationalisation.get("decision_validation_protocol_available") is True
        and live_rationalisation.get("plan_executed") is False
        and live_rationalisation.get("decision_validation_executed") is False
        and live_rationalisation.get("discovery_mode") == "metadata-only-ast-no-import-no-subprocess"
        and live_rationalisation.get("module_imported") is False
        and live_rationalisation.get("owner_decision_required") is True
        and live_rationalisation.get("autonomous_owner_decision") is False
        and live_rationalisation.get("staging_implemented") is False
        and live_rationalisation.get("canonical_website_mutation") == "none"
        and live_rationalisation.get("physical_source_file_removal") == "none"
        and live_rationalisation.get("candidate_authority") == "none"
        and live_rationalisation.get("package_authority") == "none"
        and live_rationalisation.get("release_eligible") is False
        and live_rationalisation.get("deployment_authority") == "none"
        and live_rationalisation.get("credential_access") == "none"
        and live_rationalisation.get("network_access") == "none"
        and live_rationalisation.get("max_decision_age_seconds") == 4 * 60 * 60
        and live_rationalisation.get("fixed_footprint_limits")
        == {
            "max_total_bytes": 4_500_000,
            "max_image_bytes": 2_200_000,
            "max_css_bytes": 350_000,
            "max_single_asset_bytes": 500_000,
        }
    )
    checks.append(
        _check(
            "website-source-rationalisation-boundary",
            rationalisation_ok,
            "Source-rationalisation discovery must remain unexecuted, owner-bound, and non-authoritative.",
        )
    )

    registered_runtime_optimisation = registry.get("website_runtime_optimisation_readiness")
    live_runtime_optimisation = website_runtime_optimisation_readiness(root)
    runtime_optimisation_ok = (
        isinstance(registered_runtime_optimisation, Mapping)
        and dict(registered_runtime_optimisation) == live_runtime_optimisation
        and live_runtime_optimisation.get("available") is True
        and live_runtime_optimisation.get("state") == "installed-reviewed-measurement-provenance-required"
        and live_runtime_optimisation.get("proposal_compilation_protocol_available") is False
        and live_runtime_optimisation.get("measurement_validation_protocol_available") is True
        and live_runtime_optimisation.get("measurement_validation_scope")
        == "structural-only-no-freshness-or-provenance"
        and live_runtime_optimisation.get("measurement_provenance_verification_available") is False
        and live_runtime_optimisation.get("production_compilation_blocked") is True
        and live_runtime_optimisation.get("production_compilation_blocker")
        == "blocked-reviewed-measurement-provenance-tool-not-installed"
        and live_runtime_optimisation.get("browser_acceptance_contract_available") is True
        and live_runtime_optimisation.get("measurement_schema_available") is True
        and live_runtime_optimisation.get("proposal_schema_available") is True
        and live_runtime_optimisation.get("proposal_compilation_executed") is False
        and live_runtime_optimisation.get("measurement_validation_executed") is False
        and live_runtime_optimisation.get("discovery_mode")
        == "metadata-only-ast-and-json-no-import-no-subprocess"
        and live_runtime_optimisation.get("module_imported") is False
        and live_runtime_optimisation.get("measurement_evidence_required") is True
        and live_runtime_optimisation.get("autonomous_measurement_evidence") is False
        and live_runtime_optimisation.get("source_selection_required") is True
        and live_runtime_optimisation.get("autonomous_source_selection") is False
        and live_runtime_optimisation.get("transformations_executed") is False
        and live_runtime_optimisation.get("canonical_website_mutation") == "none"
        and live_runtime_optimisation.get("physical_source_file_removal") == "none"
        and live_runtime_optimisation.get("encoding_execution") == "none"
        and live_runtime_optimisation.get("css_transformation_execution") == "none"
        and live_runtime_optimisation.get("reference_mutation") == "none"
        and live_runtime_optimisation.get("candidate_authority") == "none"
        and live_runtime_optimisation.get("staging_authority") == "none"
        and live_runtime_optimisation.get("package_authority") == "none"
        and live_runtime_optimisation.get("release_eligible") is False
        and live_runtime_optimisation.get("deployment_authority") == "none"
        and live_runtime_optimisation.get("credential_access") == "none"
        and live_runtime_optimisation.get("network_access") == "none"
        and live_runtime_optimisation.get("max_input_age_seconds") == 4 * 60 * 60
        and live_runtime_optimisation.get("fixed_footprint_limits")
        == {
            "max_total_bytes": 4_500_000,
            "max_image_bytes": 2_200_000,
            "max_css_bytes": 350_000,
            "max_single_asset_bytes": 500_000,
        }
    )
    checks.append(
        _check(
            "website-runtime-optimisation-boundary",
            runtime_optimisation_ok,
            "Runtime optimisation discovery must remain unexecuted, evidence-bound, and non-authoritative.",
        )
    )

    registered_static_integrity = registry.get("website_runtime_measurement_static_integrity_readiness")
    live_static_integrity = website_runtime_measurement_static_integrity_readiness(root)
    static_integrity_ok = (
        isinstance(registered_static_integrity, Mapping)
        and dict(registered_static_integrity) == live_static_integrity
        and live_static_integrity.get("available") is True
        and live_static_integrity.get("state") == "installed-read-validate-only-production-ineligible"
        and live_static_integrity.get("capability_scope") == "read-validate-only"
        and live_static_integrity.get("static_integrity_validation_available") is True
        and live_static_integrity.get("static_integrity_validation_executed") is False
        and live_static_integrity.get("trusted_static_integrity_execution_path")
        == "fresh-isolated-launcher-only"
        and live_static_integrity.get("imported_api_authoritative") is False
        and live_static_integrity.get("measurement_provenance_verification_available") is False
        and live_static_integrity.get("production_eligible") is False
        and live_static_integrity.get("eligible_for_proposal_compilation") is False
        and live_static_integrity.get("production_compilation_blocked") is True
        and live_static_integrity.get("worker_available") is False
        and live_static_integrity.get("worker_executed") is False
        and live_static_integrity.get("artifact_emission_available") is False
        and live_static_integrity.get("artifact_emission_executed") is False
        and live_static_integrity.get("canonical_website_mutation") == "none"
        and live_static_integrity.get("physical_source_file_removal") == "none"
        and live_static_integrity.get("encoding_execution") == "none"
        and live_static_integrity.get("css_transformation_execution") == "none"
        and live_static_integrity.get("reference_mutation") == "none"
        and live_static_integrity.get("candidate_authority") == "none"
        and live_static_integrity.get("staging_authority") == "none"
        and live_static_integrity.get("package_authority") == "none"
        and live_static_integrity.get("release_eligible") is False
        and live_static_integrity.get("deployment_authority") == "none"
        and live_static_integrity.get("credential_access") == "none"
        and live_static_integrity.get("network_access") == "none"
        and live_static_integrity.get("discovery_mode")
        == "metadata-only-ast-and-json-no-import-no-subprocess"
        and live_static_integrity.get("module_imported") is False
        and live_static_integrity.get("launcher_module_imported") is False
        and live_static_integrity.get("subprocess_launched") is False
        and live_static_integrity.get("standard_library_only") is True
        and live_static_integrity.get("forbidden_operational_imports_present") is False
        and live_static_integrity.get("writer_or_emitter_surface_present") is False
        and live_static_integrity.get("public_verify_signature_locked") is True
        and live_static_integrity.get("launcher_isolation_markers_locked") is True
        and live_static_integrity.get("source_hash_matches") is True
        and live_static_integrity.get("launcher_hash_matches") is True
        and live_static_integrity.get("schema_hash_matches") is True
        and live_static_integrity.get("schema_json_valid") is True
    )
    checks.append(
        _check(
            "website-runtime-measurement-static-integrity-boundary",
            static_integrity_ok,
            "Static-integrity discovery must remain pinned, read/validate-only, unexecuted, and production-ineligible.",
        )
    )

    registered_candidate_qa = registry.get("candidate_qa_control_plane_readiness")
    live_candidate_qa = candidate_qa_control_plane_readiness(root)
    live_ingress = live_candidate_qa.get("compiler_verification_ingress")
    imported_ingress = live_ingress.get("imported_api") if isinstance(live_ingress, Mapping) else None
    sealed_ingress = (
        live_ingress.get("sealed_direct_file_read_only") if isinstance(live_ingress, Mapping) else None
    )
    runner_delegation = live_ingress.get("runner_delegation") if isinstance(live_ingress, Mapping) else None
    candidate_qa_ok = (
        isinstance(registered_candidate_qa, Mapping)
        and dict(registered_candidate_qa) == live_candidate_qa
        and live_candidate_qa.get("available") is True
        and live_candidate_qa.get("state") == "installed-not-authorised"
        and live_candidate_qa.get("execution_order_enforced") is True
        and isinstance(live_ingress, Mapping)
        and live_ingress.get("discovery_mode") == "metadata-only-no-subprocess"
        and live_ingress.get("discovery_subprocess_launched") is False
        and isinstance(imported_ingress, Mapping)
        and imported_ingress.get("scope") == "drift-check-only"
        and imported_ingress.get("motion_read_only_verifier_available") is True
        and imported_ingress.get("test_read_only_verifier_available") is True
        and imported_ingress.get("pre_import_source_authentication") is False
        and isinstance(sealed_ingress, Mapping)
        and sealed_ingress.get("protocol_available") is True
        and sealed_ingress.get("motion_protocol_available") is True
        and sealed_ingress.get("test_protocol_available") is True
        and sealed_ingress.get("executed") is False
        and sealed_ingress.get("python_flags") == list(EXPECTED_SEALED_COMPILER_PYTHON_FLAGS)
        and sealed_ingress.get("motion_verify_flag") == EXPECTED_MOTION_VERIFY_FLAG
        and sealed_ingress.get("test_verify_flag") == EXPECTED_TEST_VERIFY_FLAG
        and sealed_ingress.get("source_closure_helper_available") is True
        and isinstance(runner_delegation, Mapping)
        and runner_delegation.get("protocol_available") is True
        and runner_delegation.get("required_for_candidate_qa") is True
        and runner_delegation.get("bounded_popen_protocol_available") is True
        and runner_delegation.get("launcher") == "subprocess.Popen"
        and runner_delegation.get("shell") is False
        and runner_delegation.get("timeout_seconds") == EXPECTED_SEALED_COMPILER_TIMEOUT_SECONDS
        and runner_delegation.get("max_aggregate_output_bytes") == EXPECTED_SEALED_COMPILER_MAX_OUTPUT_BYTES
        and runner_delegation.get("retry_authority") == "none"
        and runner_delegation.get("invoked") is False
        and live_candidate_qa.get("qa_execution_authorised") is False
        and live_candidate_qa.get("qa_executed") is False
        and live_candidate_qa.get("qa_passed") is False
    )
    checks.append(
        _check(
            "candidate-qa-compiler-verification-ingress",
            candidate_qa_ok,
            "Candidate-QA discovery must bind imported drift checks separately from unexecuted sealed direct-file verification and runner delegation.",
        )
    )

    live_design_roles = {item["name"] for item in _design_council_roles(root)}
    registered_design_roles = _registry_names(registry.get("design_council_roles"), "name")
    design_roles_ok = (
        registered_design_roles == set(DESIGN_COUNCIL_ROLES)
        and live_design_roles == set(DESIGN_COUNCIL_ROLES)
        and all(
            isinstance(item, Mapping) and item.get("available") is True
            for item in registry.get("design_council_roles", [])
        )
    )
    checks.append(
        _check(
            "design-council-roles",
            design_roles_ok,
            "The complete current Harmonic Design Suite council must be discoverable.",
        )
    )

    live_coding_roles = {item["name"] for item in _coding_roles(root)}
    registered_coding_roles = _registry_names(registry.get("coding_roles"), "name")
    coding_roles_ok = (
        registered_coding_roles == set(CODING_DESIGN_ROLES)
        and live_coding_roles == set(CODING_DESIGN_ROLES)
        and all(
            isinstance(item, Mapping) and item.get("available") is True
            for item in registry.get("coding_roles", [])
        )
    )
    checks.append(
        _check(
            "coding-design-roles",
            coding_roles_ok,
            "The bounded website worker and QA roles must be discoverable from the coding skill base.",
        )
    )

    expected_operator = {
        identifier: method for identifier, _category, method in WEBSITE_OPERATOR_CAPABILITIES
    }
    registered_operator = registry.get("website_operator_capabilities")
    operator_ok = isinstance(registered_operator, list)
    actual_operator: dict[str, str] = {}
    live_operator_methods = _website_operator_method_names(root)
    if isinstance(registered_operator, list):
        for row in registered_operator:
            if not isinstance(row, Mapping):
                operator_ok = False
                continue
            identifier = row.get("id")
            method = row.get("method")
            available_value = row.get("available")
            if not isinstance(identifier, str) or not isinstance(method, str):
                operator_ok = False
                continue
            actual_operator[identifier] = method
            if available_value is not True or method not in live_operator_methods:
                operator_ok = False
    operator_ok = operator_ok and actual_operator == expected_operator
    checks.append(
        _check(
            "website-operator-capabilities",
            operator_ok,
            "The current WebsiteOperator lifecycle methods must match the registered capability map.",
        )
    )

    passed = all(check["passed"] for check in checks)
    return {
        "schema": VERIFICATION_SCHEMA,
        "verified_at": _utc_iso(),
        "state": "pass" if passed else "fail",
        "passed": passed,
        "release_eligible": False,
        "deployment_authority": "none",
        "checks": checks,
    }


def _load_registry(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise DesignCapabilityRegistryError(f"Registry file does not exist: {path}") from exc
    except json.JSONDecodeError as exc:
        raise DesignCapabilityRegistryError(f"Registry file is not valid JSON: {path}") from exc
    if not isinstance(value, dict):
        raise DesignCapabilityRegistryError("Registry file must contain one JSON object.")
    return value


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="aureon-design-capabilities",
        description="Read-only capability discovery for Aureon's public website design stack.",
    )
    parser.add_argument("--repo-root", type=Path, help="Aureon repository root.")
    parser.add_argument(
        "--verify",
        type=Path,
        help="Verify a previously captured registry JSON instead of discovering a new one.",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)
    try:
        if args.verify:
            root = _find_repo_root(args.repo_root)
            registry = _load_registry(args.verify.resolve())
            verification = verify_design_capability_registry(registry, repo_root=root)
            payload: dict[str, Any] = {
                "registry": registry,
                "verification": verification,
                "owner_source_reconciliation_readiness": owner_source_reconciliation_readiness(root),
                "website_source_rationalisation_readiness": (website_source_rationalisation_readiness(root)),
                "website_runtime_optimisation_readiness": (website_runtime_optimisation_readiness(root)),
                "website_runtime_measurement_static_integrity_readiness": (
                    website_runtime_measurement_static_integrity_readiness(root)
                ),
                "design_research_refresh_readiness": design_research_refresh_readiness(root),
                "stakeholder_feedback_readiness": stakeholder_feedback_readiness(root),
                "editorial_rights_decision_preparation_readiness": (
                    editorial_rights_decision_preparation_readiness(root)
                ),
                "investor_copy_repair_readiness": investor_copy_repair_readiness(root),
                "investor_copy_governance_readiness": investor_copy_governance_readiness(root),
                "design_evidence_brief_readiness": design_evidence_brief_readiness(root),
                "motion_performance_budget_readiness": motion_performance_budget_readiness(root),
                "candidate_test_evidence_readiness": candidate_test_evidence_readiness(root),
                "candidate_qa_control_plane_readiness": candidate_qa_control_plane_readiness(root),
            }
        else:
            payload = discover_design_capability_registry(args.repo_root)
            verification = payload["verification"]
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0 if verification["passed"] else 2
    except DesignCapabilityRegistryError as exc:
        print(json.dumps({"state": "blocked", "error": str(exc)}, indent=2))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

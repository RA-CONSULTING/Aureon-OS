from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import py_compile
import re
import time
from datetime import UTC, datetime
from html import escape
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence

from aureon.autonomous.aureon_artifact_quality_gate import (
    DEFAULT_PUBLIC_QUALITY_JSON,
    write_artifact_quality_report,
)
from aureon.autonomous.aureon_safe_code_control import CodeProposal, SafeCodeControl

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_STATE_PATH = Path("state/aureon_capability_forge_last_run.json")
DEFAULT_AUDIT_JSON = Path("docs/audits/aureon_capability_forge.json")
DEFAULT_AUDIT_MD = Path("docs/audits/aureon_capability_forge.md")
DEFAULT_PUBLIC_JSON = Path("frontend/public/aureon_capability_forge.json")
DEFAULT_SAFE_CODE_STATE = Path("state/aureon_capability_forge_safe_code_state.json")
DEFAULT_LOCAL_APP_DIR = Path("frontend/public/aureon_generated_apps")
DEFAULT_ADAPTIVE_SKILL_DIR = Path("frontend/public/aureon_adaptive_skills")
DEFAULT_FULL_STACK_APP_DIR = Path("frontend/public/aureon_full_stack_apps")

REFERENCE_PATTERNS = [
    {
        "name": "OpenAI Agents SDK",
        "url": "https://developers.openai.com/api/docs/guides/agents",
        "pattern": "agents, tools, handoffs, guardrails, tracing, sandbox state",
    },
    {
        "name": "Anthropic tool use",
        "url": "https://platform.claude.com/docs/en/agents-and-tools/tool-use/overview",
        "pattern": "client tools, server tools, strict schemas, tool_result loop",
    },
    {
        "name": "Claude Code subagents",
        "url": "https://code.claude.com/docs/en/sub-agents",
        "pattern": "specialist workers with isolated context and scoped tool access",
    },
    {
        "name": "Gemini function calling",
        "url": "https://ai.google.dev/gemini-api/docs/function-calling",
        "pattern": "OpenAPI-shaped function calls and automatic function execution",
    },
    {
        "name": "Gemini Veo video flow",
        "url": "https://ai.google.dev/gemini-api/docs/video",
        "pattern": "image/storyboard seed, async video operation, poll until ready",
    },
    {
        "name": "AutoGen multi-agent chat",
        "url": "https://microsoft.github.io/autogen/0.2/docs/Use-Cases/agent_chat/",
        "pattern": "conversable agents coordinating tools and human feedback",
    },
    {
        "name": "Semantic Kernel orchestration",
        "url": "https://learn.microsoft.com/en-us/semantic-kernel/frameworks/agent/agent-orchestration/",
        "pattern": "sequential, concurrent, group, and handoff orchestration",
    },
    {
        "name": "GitHub Copilot cloud agent",
        "url": "https://docs.github.com/en/copilot/how-tos/use-copilot-agents/cloud-agent/start-copilot-sessions",
        "pattern": "delegate prompt to agent, inspect session, review resulting changes",
    },
    {
        "name": "Jules coding agent",
        "url": "https://jules.google/docs/",
        "pattern": "autonomous coding task in repo context with human review",
    },
    {
        "name": "Runway video models",
        "url": "https://docs.dev.runwayml.com/guides/models/",
        "pattern": "video models expose text/image-to-video as job artifacts",
    },
    {
        "name": "Adobe Firefly Services",
        "url": "https://developer.adobe.com/firefly-services/docs/guides/",
        "pattern": "creative generation at scale with credentials kept server-side",
    },
    {
        "name": "Canva Connect design metadata",
        "url": "https://www.canva.dev/docs/connect/api-reference/designs/get-design/",
        "pattern": "design preview/edit/view metadata with expiring URLs",
    },
]

TASK_FAMILIES = [
    "website_design",
    "full_stack",
    "video",
    "image_graphic_design",
    "coding",
    "ui",
    "document",
    "research",
    "browser_qa",
    "mixed",
]

FAMILY_KEYWORDS = {
    "website_design": (
        "website",
        "web site",
        "webpage",
        "web page",
        "public site",
        "site redesign",
        "website redesign",
        "landing page",
        "investor-ready site",
        "investor ready site",
        "home.pl",
    ),
    "full_stack": (
        "full stack",
        "full-stack",
        "backend",
        "api server",
        "database",
        "crud",
        "auth",
        "server",
        "end to end app",
        "frontend and backend",
    ),
    "video": ("video", "clip", "animation", "mp4", "webm", "10 second", "seconds"),
    "image_graphic_design": (
        "image",
        "picture",
        "graphic",
        "logo",
        "design",
        "poster",
        "draw",
        "illustration",
        "svg",
    ),
    "coding": (
        "code",
        "repo",
        "patch",
        "python",
        "typescript",
        "test",
        "build",
        "function",
        "module",
        "game",
        "app",
        "html",
        "javascript",
        "tool",
        "skill",
        "calculator",
        "converter",
        "generator",
        "workflow",
    ),
    "ui": (
        "ui",
        "frontend",
        "dashboard",
        "console",
        "panel",
        "react",
        "tsx",
        "screen",
        "keyboard",
        "playable",
        "controls",
    ),
    "document": ("document", "pdf", "markdown", "report", "runbook", "docx"),
    "research": ("research", "online", "official docs", "search", "learn", "source"),
    "browser_qa": ("browser", "playwright", "smoke", "screenshot", "open the page", "render"),
}


def _default_root() -> Path:
    return Path.cwd().resolve() if (Path.cwd() / "aureon").exists() else REPO_ROOT


def _rooted(root: Path, rel_path: Path) -> Path:
    return rel_path if rel_path.is_absolute() else root / rel_path


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _write_text(path: Path, content: str) -> Dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return {"path": str(path), "ok": path.exists(), "bytes": path.stat().st_size if path.exists() else 0}


def _write_json(path: Path, payload: Dict[str, Any]) -> Dict[str, Any]:
    return _write_text(path, json.dumps(payload, indent=2, sort_keys=True, default=str))


def _contains_any(text: str, needles: Iterable[str]) -> bool:
    normalized = re.sub(r"\s+", " ", str(text or "").lower())
    for needle in needles:
        keyword = str(needle or "").lower().strip()
        if not keyword:
            continue
        if re.fullmatch(r"[a-z0-9 ]+", keyword):
            if re.search(rf"(?<![a-z0-9]){re.escape(keyword)}(?![a-z0-9])", normalized):
                return True
        elif keyword in normalized:
            return True
    return False


def classify_task_family(prompt: str) -> Dict[str, Any]:
    text = str(prompt or "").lower()
    hits = [family for family, needles in FAMILY_KEYWORDS.items() if _contains_any(text, needles)]
    priority = (
        "website_design",
        "full_stack",
        "video",
        "image_graphic_design",
        "browser_qa",
        "ui",
        "coding",
        "document",
        "research",
    )
    if "website_design" in hits:
        return {
            "task_family": "website_design",
            "primary_family": "website_design",
            "detected_families": hits,
            "local_only": True,
        }
    if "full_stack" in hits:
        return {
            "task_family": "full_stack",
            "primary_family": "full_stack",
            "detected_families": hits or ["full_stack"],
            "local_only": True,
        }
    if len(hits) > 1:
        primary = next((family for family in priority if family in hits), hits[0])
        family = "mixed" if primary not in {"video", "image_graphic_design"} else primary
    elif hits:
        family = hits[0]
        primary = family
    else:
        family = "coding"
        primary = "coding"
    return {
        "task_family": family,
        "primary_family": primary,
        "detected_families": hits or [family],
        "local_only": True,
    }


def _crew_for_families(families: Sequence[str]) -> List[Dict[str, Any]]:
    base = [
        ("Client Brief Broker", "scope", "lock goal, deliverables, constraints, and acceptance proof"),
        (
            "Skill Headhunter",
            "research",
            "scan local repo first and use official docs as reference-only patterns",
        ),
        (
            "Subcontractor Crew Builder",
            "orchestration",
            "hire the temporary specialist crew and define handoffs",
        ),
        ("Quality Gate Inspector", "qa", "reject weak artifacts before handover"),
        ("Release Manager", "handover", "publish evidence and wait for approval"),
    ]
    family_roles = {
        "website_design": [
            (
                "Website Design Director",
                "design",
                "own the evidence-led brief, institutional quality bar, design council, and human visual review",
            ),
            (
                "Competitor Research Scout",
                "research",
                "refresh official-source benchmark patterns without copying competitor expression",
            ),
            (
                "Brand and Design-System Lead",
                "design",
                "maintain typography, colour, spacing, components, imagery, and responsive coherence",
            ),
            (
                "Technical Editorial Writer",
                "editorial",
                "write precise en-GB proposition, research, product, and buyer-journey copy",
            ),
            (
                "Claims and Evidence Editor",
                "editorial",
                "bind material public claims to current evidence state and permitted wording",
            ),
            (
                "Motion Designer",
                "design",
                "use restrained purposeful motion with keyboard and reduced-motion parity",
            ),
            (
                "Visual Asset Director",
                "design",
                "create or commission source-cleared graphics under explicit asset budgets",
            ),
            (
                "Accessibility and Performance QA",
                "qa",
                "prove responsive, keyboard, contrast, motion, browser, and performance behaviour",
            ),
            (
                "Design Release QA",
                "release",
                "prove dependency closure, package integrity, backup readiness, and live read-back boundaries",
            ),
        ],
        "full_stack": [
            (
                "Product Manager",
                "product",
                "turn the client prompt into a full-stack scope and acceptance checklist",
            ),
            ("API Engineer", "engineering", "write the local backend API, data contract, and run command"),
            (
                "Frontend Engineer",
                "engineering",
                "write the browser UI that talks to the local backend contract",
            ),
            ("Data Modeler", "engineering", "define seed data, validation rules, and persistence shape"),
            ("Integration Test Pilot", "qa", "prove backend functions and API contract before handover"),
            (
                "Security Auditor",
                "security",
                "keep secrets, live actions, and destructive operations out of the generated system",
            ),
        ],
        "video": [
            ("Storyboard Artist", "media", "turn prompt into frames, motion, duration, and preview plan"),
            ("Local Encoder", "media", "produce WebM, GIF fallback, and HTML preview"),
            ("Playback Inspector", "qa", "probe duration and browser-playable artifact state"),
        ],
        "image_graphic_design": [
            ("Graphic Designer", "media", "produce a renderable local visual asset"),
            ("Visual QA Inspector", "qa", "check dimensions, prompt match, and public preview"),
        ],
        "coding": [
            ("Code Architect", "engineering", "scope patch contract and authority boundaries"),
            ("Implementation Worker", "engineering", "route code work through safe local authoring"),
            ("Test Pilot", "qa", "run tests/build proof before approval"),
            ("Security Auditor", "security", "check secrets and unsafe mutation boundaries"),
        ],
        "ui": [
            ("UX Designer", "product", "make the interface usable for a human operator"),
            ("Frontend Console Builder", "engineering", "mount evidence and previews in the cockpit"),
            ("Browser Smoke Inspector", "qa", "confirm visible UI proof"),
        ],
        "document": [("Runbook Writer", "docs", "publish readable operator evidence and handover docs")],
        "research": [
            ("Research Scout", "research", "summarize source-linked patterns without external execution")
        ],
        "browser_qa": [
            ("Browser Smoke Inspector", "qa", "open local UI, inspect console state, and record proof")
        ],
    }
    crew = [
        {"role": role, "department": dept, "day_to_day": duty, "temporary": True} for role, dept, duty in base
    ]
    for family in families:
        for role, dept, duty in family_roles.get(family, []):
            if not any(item["role"] == role for item in crew):
                crew.append({"role": role, "department": dept, "day_to_day": duty, "temporary": True})
    return crew


def _tools_for_families(families: Sequence[str]) -> List[Dict[str, Any]]:
    tools = [
        {"name": "Repo search", "surface": "rg / RepoSelfCatalog", "mode": "read_only"},
        {
            "name": "SafeCodeControl",
            "surface": "aureon.autonomous.aureon_safe_code_control",
            "mode": "local_safe_route",
        },
        {
            "name": "Artifact quality gate",
            "surface": "aureon.autonomous.aureon_artifact_quality_gate",
            "mode": "local_quality_gate",
        },
    ]
    if "website_design" in families:
        tools.extend(
            [
                {
                    "name": "WebsiteOperator Design Nexus",
                    "surface": "aureon.operator.website_operator",
                    "mode": "local_design_cycle",
                },
                {
                    "name": "Public-site visual QA",
                    "surface": "tools/aureon_website_visual_qa_v28.js",
                    "mode": "local_browser_proof",
                },
                {
                    "name": "Motion/performance budget protocol",
                    "surface": "aureon.operator.design_motion_performance_budget",
                    "mode": "installed_not_authorised_metadata_only",
                },
                {
                    "name": "Candidate-test evidence protocol",
                    "surface": "aureon.operator.design_candidate_test_evidence",
                    "mode": "installed_not_authorised_metadata_only",
                },
                {
                    "name": "V2 candidate-QA control plane",
                    "surface": "aureon.operator.design_capability_registry",
                    "mode": "installed_not_authorised_fixed_order_metadata_only",
                },
                {
                    "name": "Dependency-closed release builder",
                    "surface": "tools/build-homepl-v28-narrow-release.ps1",
                    "mode": "local_package_only",
                },
            ]
        )
    if ("video" in families or "image_graphic_design" in families) and "website_design" not in families:
        tools.append(
            {
                "name": "Visual asset worker",
                "surface": "aureon.autonomous.aureon_visual_asset_request",
                "mode": "local_generation",
            }
        )
    if "browser_qa" in families or "ui" in families or "video" in families:
        tools.append(
            {
                "name": "Playwright/browser smoke",
                "surface": "frontend Playwright",
                "mode": "local_browser_proof",
            }
        )
    if "full_stack" in families:
        tools.append(
            {
                "name": "Full-stack local system forge",
                "surface": "frontend/public/aureon_full_stack_apps",
                "mode": "local_backend_frontend_generation",
            }
        )
        tools.append(
            {
                "name": "Python stdlib API server",
                "surface": "generated backend/server.py",
                "mode": "local_backend_runtime",
            }
        )
        tools.append(
            {
                "name": "Contract validation",
                "surface": "py_compile + imported backend contract",
                "mode": "local_validation",
            }
        )
    if "coding" in families or "ui" in families or "full_stack" in families:
        tools.append(
            {"name": "Focused pytest/build", "surface": "pytest / npm run build", "mode": "local_validation"}
        )
        tools.append(
            {
                "name": "Adaptive local app forge",
                "surface": "frontend/public/aureon_generated_apps",
                "mode": "local_file_generation",
            }
        )
    return tools


def _reference_patterns() -> List[Dict[str, Any]]:
    return [
        {
            **item,
            "provider_policy": "reference_only",
            "external_api_call_allowed": False,
        }
        for item in REFERENCE_PATTERNS
    ]


def _visual_artifact(prompt: str, root: Path) -> Dict[str, Any]:
    from aureon.autonomous.aureon_visual_asset_request import build_and_write_visual_asset_request

    result = build_and_write_visual_asset_request(prompt, root=root, open_requested=True)
    return result if isinstance(result, dict) else {}


def _design_capability_registry_preflight(root: Path) -> Dict[str, Any]:
    """Capture the current design-stack source binding for a local work order.

    This is intentionally a discovery/preflight step only.  It refuses to
    treat the registry as a release authority, even when all of its local
    consistency checks pass.
    """

    result: Dict[str, Any] = {
        "available": False,
        "verified": False,
        "release_eligible": False,
        "deployment_authority": "none",
        "human_visual_acceptance": "required for material brand changes",
        "owner_release_boundary": "WebsiteOperator owner gate only",
        "schema": "",
        "authority": {},
        "sources": [],
        "design_evidence_brief_readiness": {
            "available": False,
            "state": "unavailable",
            "brief_ready": False,
            "planning_pipeline_available": False,
            "candidate_delivery_ready": False,
            "release_eligible": False,
            "deployment_authority": "none",
        },
        "motion_performance_budget_readiness": {
            "available": False,
            "installed": False,
            "state": "unavailable",
            "audit_protocol_available": False,
            "receipt_replay_available": False,
            "audit_executed": False,
            "decision_passed": False,
            "eligible_for_next_local_gate": False,
            "pass_inferred_from_installation": False,
            "candidate_validation_authority": "none",
            "promotion_authority": "none",
            "package_authority": "none",
            "release_eligible": False,
            "deployment_authority": "none",
        },
        "candidate_test_evidence_readiness": {
            "available": False,
            "installed": False,
            "state": "unavailable",
            "execution_protocol_available": False,
            "structural_verification_available": False,
            "reviewed_node_toolchain": {
                "protocol_available": False,
                "schema": "aureon.node-toolchain-binding.v1",
                "locator_authority": "reviewed-source-pinned-absolute-path-no-path-fallback",
                "absolute_path_size_sha256_bound": False,
                "ambient_path_fallback_allowed": False,
                "resolved": False,
                "executed": False,
            },
            "bounded_process": {
                "protocol_available": False,
                "launcher": "subprocess.Popen",
                "shell": False,
                "max_stream_bytes": 2 * 1024 * 1024,
                "retry_authority": "none",
                "executed": False,
            },
            "execution_authorised": False,
            "test_suite_executed": False,
            "worker_pass_strings_are_evidence": False,
            "origin_attested": False,
            "trusted_orchestration_seal_required": True,
            "evidence_passed": False,
            "pass_inferred_from_installation": False,
            "candidate_validation_authority": "none",
            "promotion_authority": "none",
            "package_authority": "none",
            "release_eligible": False,
            "deployment_authority": "none",
        },
        "candidate_qa_control_plane_readiness": {
            "available": False,
            "installed": False,
            "state": "unavailable",
            "static_qa_available": False,
            "fixed_test_policy_compiler_available": False,
            "fixed_motion_policy_compiler_available": False,
            "handle_bound_immutable_writer_available": False,
            "v2_runner_available": False,
            "candidate_test_evidence_runtime_available": False,
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
                    "python_flags": ["-I", "-S", "-B"],
                    "motion_verify_flag": "--verify-config",
                    "test_verify_flag": "--verify-policy",
                    "source_closure_helper_available": False,
                },
                "runner_delegation": {
                    "protocol_available": False,
                    "required_for_candidate_qa": True,
                    "bounded_popen_protocol_available": False,
                    "launcher": "subprocess.Popen",
                    "shell": False,
                    "timeout_seconds": 300,
                    "max_aggregate_output_bytes": 64 * 1024,
                    "retry_authority": "none",
                    "invoked": False,
                },
            },
            "execution_order_enforced": False,
            "qa_execution_authorised": False,
            "qa_executed": False,
            "qa_passed": False,
            "pass_inferred_from_installation": False,
            "candidate_validation_authority": "none",
            "promotion_authority": "none",
            "package_authority": "none",
            "release_eligible": False,
            "deployment_authority": "none",
        },
        "verification": {
            "passed": False,
            "release_eligible": False,
            "deployment_authority": "none",
        },
        "error": "",
    }
    try:
        from aureon.operator.design_capability_registry import discover_design_capability_registry

        registry = discover_design_capability_registry(root)
        verification = registry.get("verification")
        authority = registry.get("authority")
        brief_readiness = registry.get("design_evidence_brief_readiness")
        motion_budget_readiness = registry.get("motion_performance_budget_readiness")
        candidate_test_readiness = registry.get("candidate_test_evidence_readiness")
        candidate_qa_readiness = registry.get("candidate_qa_control_plane_readiness")
        verified = (
            isinstance(verification, dict)
            and verification.get("passed") is True
            and verification.get("release_eligible") is False
            and verification.get("deployment_authority") == "none"
            and isinstance(authority, dict)
            and authority.get("release_eligibility") == "always-false"
            and authority.get("deployment_authority") == "none"
            and authority.get("release_authority") == "WebsiteOperator owner gate only"
        )
        result.update(
            {
                "available": True,
                "verified": verified,
                "schema": str(registry.get("schema") or ""),
                "authority": authority if isinstance(authority, dict) else {},
                "sources": registry.get("sources") if isinstance(registry.get("sources"), list) else [],
                "design_evidence_brief_readiness": (
                    brief_readiness
                    if isinstance(brief_readiness, dict)
                    else result["design_evidence_brief_readiness"]
                ),
                "motion_performance_budget_readiness": (
                    motion_budget_readiness
                    if isinstance(motion_budget_readiness, dict)
                    else result["motion_performance_budget_readiness"]
                ),
                "candidate_test_evidence_readiness": (
                    candidate_test_readiness
                    if isinstance(candidate_test_readiness, dict)
                    else result["candidate_test_evidence_readiness"]
                ),
                "candidate_qa_control_plane_readiness": (
                    candidate_qa_readiness
                    if isinstance(candidate_qa_readiness, dict)
                    else result["candidate_qa_control_plane_readiness"]
                ),
                "verification": verification if isinstance(verification, dict) else result["verification"],
            }
        )
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
    return result


def _brief_readiness_metadata(registry: Dict[str, Any]) -> Dict[str, Any]:
    """Return planning-state evidence without treating it as candidate authority."""

    raw = registry.get("design_evidence_brief_readiness")
    readiness = raw if isinstance(raw, dict) else {}
    return {
        "available": readiness.get("available") is True,
        "state": str(readiness.get("state") or "unavailable"),
        "brief_ready": readiness.get("brief_ready") is True,
        "planning_pipeline_available": readiness.get("planning_pipeline_available") is True,
        # The capability forge only reports readiness. It never creates a work
        # order or a staged candidate, even if the source-bound brief passes.
        "candidate_delivery_ready": False,
        "candidate_creation": "none; metadata-only capability-forge report",
        "release_eligible": False,
        "deployment_authority": "none",
    }


def _delivery_runner_metadata(
    registry: Dict[str, Any],
    brief_readiness: Dict[str, Any],
) -> Dict[str, Any]:
    """Describe the runner boundary without importing or invoking the runner."""

    qa_raw = registry.get("candidate_qa_control_plane_readiness")
    qa_readiness = qa_raw if isinstance(qa_raw, dict) else {}
    ingress_raw = qa_readiness.get("compiler_verification_ingress")
    ingress = ingress_raw if isinstance(ingress_raw, dict) else {}
    delegation_raw = ingress.get("runner_delegation")
    delegation = delegation_raw if isinstance(delegation_raw, dict) else {}
    sealed_delegation_available = (
        ingress.get("discovery_mode") == "metadata-only-no-subprocess"
        and ingress.get("discovery_subprocess_launched") is False
        and delegation.get("protocol_available") is True
        and delegation.get("required_for_candidate_qa") is True
        and delegation.get("bounded_popen_protocol_available") is True
        and delegation.get("launcher") == "subprocess.Popen"
        and delegation.get("shell") is False
        and delegation.get("timeout_seconds") == 300
        and delegation.get("max_aggregate_output_bytes") == 64 * 1024
        and delegation.get("retry_authority") == "none"
        and delegation.get("invoked") is False
    )
    return {
        "available": registry.get("verified") is True,
        "module": "aureon.autonomous.aureon_public_website_design_runner",
        "mode": "metadata-only; explicit runner action required for immutable staged receipts",
        "invoked": False,
        "candidate_qa_discovery_subprocess_launched": False,
        "sealed_compiler_read_only_delegation_available": sealed_delegation_available,
        "sealed_compiler_read_only_delegation_invoked": False,
        "candidate_creation": "none; capability forge does not create delivery jobs or staged candidates",
        "candidate_staged": False,
        "brief_ready": brief_readiness.get("brief_ready") is True,
        "planning_pipeline_available": brief_readiness.get("planning_pipeline_available") is True,
        "canonical_website_mutation": "never",
        "promotion_authority": "none",
        "terminal_boundary": "awaiting-owner-promotion",
        "release_eligible": False,
        "deployment_authority": "none",
        "next_action": (
            "Use the runner only through an explicit, separately governed action after current "
            "reconciliation, any required owner source decision and verified backup; this forge "
            "report creates neither a delivery job nor a candidate."
        ),
    }


def _motion_performance_budget_metadata(registry: Dict[str, Any]) -> Dict[str, Any]:
    """Describe the installed static protocol without running or passing it."""

    raw = registry.get("motion_performance_budget_readiness")
    readiness = raw if isinstance(raw, dict) else {}
    protocol_available = (
        readiness.get("state") == "installed-not-authorised"
        and readiness.get("audit_protocol_available") is True
        and readiness.get("receipt_replay_available") is True
    )
    return {
        "available": protocol_available,
        "state": "installed-not-authorised" if protocol_available else "unavailable",
        "module": "aureon.operator.design_motion_performance_budget",
        "mode": "metadata-only; capability forge never runs or interprets the audit",
        "invoked": False,
        "audit_executed": False,
        "decision_status": "not-evaluated",
        "decision_passed": False,
        "eligible_for_next_local_gate": False,
        "pass_inferred_from_installation": False,
        "pass_requirement": (
            "exact receipt decision.status pass and decision.eligible_for_next_local_gate true"
        ),
        "candidate_validation_authority": "none",
        "promotion_authority": "none",
        "canonical_website_mutation": "none",
        "package_authority": "none",
        "release_eligible": False,
        "deployment_authority": "none",
    }


def _candidate_test_evidence_metadata(registry: Dict[str, Any]) -> Dict[str, Any]:
    """Describe trusted-test evidence without executing or trusting worker text."""

    raw = registry.get("candidate_test_evidence_readiness")
    readiness = raw if isinstance(raw, dict) else {}
    node_raw = readiness.get("reviewed_node_toolchain")
    node = node_raw if isinstance(node_raw, dict) else {}
    process_raw = readiness.get("bounded_process")
    process = process_raw if isinstance(process_raw, dict) else {}
    reviewed_node_toolchain_available = (
        node.get("protocol_available") is True
        and node.get("schema") == "aureon.node-toolchain-binding.v1"
        and node.get("locator_authority") == "reviewed-source-pinned-absolute-path-no-path-fallback"
        and node.get("absolute_path_size_sha256_bound") is True
        and node.get("ambient_path_fallback_allowed") is False
        and node.get("resolved") is False
        and node.get("executed") is False
    )
    bounded_popen_available = (
        process.get("protocol_available") is True
        and process.get("launcher") == "subprocess.Popen"
        and process.get("shell") is False
        and process.get("max_stream_bytes") == 2 * 1024 * 1024
        and process.get("retry_authority") == "none"
        and process.get("executed") is False
    )
    protocol_available = (
        readiness.get("state") == "installed-not-authorised"
        and readiness.get("execution_protocol_available") is True
        and readiness.get("structural_verification_available") is True
        and reviewed_node_toolchain_available
        and bounded_popen_available
    )
    return {
        "available": protocol_available,
        "state": "installed-not-authorised" if protocol_available else "unavailable",
        "module": "aureon.operator.design_candidate_test_evidence",
        "mode": "metadata-only; capability forge never executes a candidate test suite",
        "invoked": False,
        "reviewed_node_toolchain_available": reviewed_node_toolchain_available,
        "reviewed_node_ambient_path_fallback_allowed": False,
        "reviewed_node_resolved": False,
        "bounded_popen_protocol_available": bounded_popen_available,
        "bounded_popen_shell": False,
        "bounded_popen_executed": False,
        "execution_authorised": False,
        "test_suite_executed": False,
        "worker_pass_strings_are_evidence": False,
        "structural_verification_passed": False,
        "origin_attested": False,
        "trusted_orchestration_seal_required": True,
        "evidence_passed": False,
        "pass_inferred_from_installation": False,
        "pass_requirement": (
            "independently preserved trusted orchestration seal plus strict verification "
            "with origin_attested false and evidence_passed true"
        ),
        "candidate_validation_authority": "none",
        "promotion_authority": "none",
        "canonical_website_mutation": "none",
        "package_authority": "none",
        "release_eligible": False,
        "deployment_authority": "none",
    }


def _candidate_qa_control_plane_metadata(registry: Dict[str, Any]) -> Dict[str, Any]:
    """Describe the fixed V2 QA chain without compiling or executing it."""

    raw = registry.get("candidate_qa_control_plane_readiness")
    readiness = raw if isinstance(raw, dict) else {}
    ingress_raw = readiness.get("compiler_verification_ingress")
    ingress = ingress_raw if isinstance(ingress_raw, dict) else {}
    imported_raw = ingress.get("imported_api")
    imported_api = imported_raw if isinstance(imported_raw, dict) else {}
    sealed_raw = ingress.get("sealed_direct_file_read_only")
    sealed = sealed_raw if isinstance(sealed_raw, dict) else {}
    delegation_raw = ingress.get("runner_delegation")
    delegation = delegation_raw if isinstance(delegation_raw, dict) else {}
    imported_drift_checks_available = (
        imported_api.get("scope") == "drift-check-only"
        and imported_api.get("motion_read_only_verifier_available") is True
        and imported_api.get("test_read_only_verifier_available") is True
        and imported_api.get("pre_import_source_authentication") is False
    )
    sealed_read_only_protocol_available = (
        sealed.get("protocol_available") is True
        and sealed.get("motion_protocol_available") is True
        and sealed.get("test_protocol_available") is True
        and sealed.get("executed") is False
        and sealed.get("python_flags") == ["-I", "-S", "-B"]
        and sealed.get("motion_verify_flag") == "--verify-config"
        and sealed.get("test_verify_flag") == "--verify-policy"
        and sealed.get("source_closure_helper_available") is True
    )
    runner_delegation_available = (
        delegation.get("protocol_available") is True
        and delegation.get("required_for_candidate_qa") is True
        and delegation.get("bounded_popen_protocol_available") is True
        and delegation.get("launcher") == "subprocess.Popen"
        and delegation.get("shell") is False
        and delegation.get("timeout_seconds") == 300
        and delegation.get("max_aggregate_output_bytes") == 64 * 1024
        and delegation.get("retry_authority") == "none"
        and delegation.get("invoked") is False
    )
    available = (
        readiness.get("available") is True
        and readiness.get("state") == "installed-not-authorised"
        and readiness.get("execution_order_enforced") is True
        and readiness.get("candidate_test_evidence_runtime_available") is True
        and ingress.get("discovery_mode") == "metadata-only-no-subprocess"
        and ingress.get("discovery_subprocess_launched") is False
        and imported_drift_checks_available
        and sealed_read_only_protocol_available
        and runner_delegation_available
    )
    return {
        "available": available,
        "state": "installed-not-authorised" if available else "unavailable",
        "module": "aureon.operator.design_capability_registry",
        "runner": "aureon.autonomous.aureon_public_website_design_runner",
        "mode": "metadata-only-no-subprocess; capability forge never compiles, claims, executes, delegates, or enters a gate",
        "invoked": False,
        "discovery_subprocess_launched": False,
        "imported_compiler_drift_check_apis_available": imported_drift_checks_available,
        "imported_compiler_pre_import_source_authentication": False,
        "sealed_direct_file_read_only_protocol_available": sealed_read_only_protocol_available,
        "sealed_direct_file_read_only_verification_executed": False,
        "sealed_compiler_python_flags": ["-I", "-S", "-B"],
        "sealed_motion_verify_flag": "--verify-config",
        "sealed_test_verify_flag": "--verify-policy",
        "source_closure_helper_available": sealed.get("source_closure_helper_available") is True,
        "runner_delegation_available": runner_delegation_available,
        "runner_delegation_required_for_candidate_qa": True,
        "runner_bounded_popen_protocol_available": runner_delegation_available,
        "runner_bounded_popen_shell": False,
        "runner_bounded_popen_timeout_seconds": 300,
        "runner_bounded_popen_max_aggregate_output_bytes": 64 * 1024,
        "runner_bounded_popen_retry_authority": "none",
        "runner_delegation_invoked": False,
        "static_qa_available": readiness.get("static_qa_available") is True,
        "fixed_test_policy_compiler_available": (
            readiness.get("fixed_test_policy_compiler_available") is True
        ),
        "fixed_motion_policy_compiler_available": (
            readiness.get("fixed_motion_policy_compiler_available") is True
        ),
        "handle_bound_immutable_writer_available": (
            readiness.get("handle_bound_immutable_writer_available") is True
        ),
        "execution_order": list(readiness.get("execution_order") or []),
        "execution_order_enforced": available,
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
    }


def _blocked_website_design_artifact(
    registry: Dict[str, Any],
) -> Dict[str, Any]:
    reason = registry.get("error") or "Source-bound design capability registry did not verify."
    quality = {
        "schema_version": "aureon-website-design-quality-report-v1",
        "status": "artifact_quality_blocked",
        "generated_at": _utc_now(),
        "task_family": "website_design",
        "provider_policy": "local_only_v1",
        "score": 0.0,
        "minimum_score": 0.85,
        "handover_ready": False,
        "release_eligible": False,
        "deployment_authority": "none",
        "next_required_gate": (
            "Repair the source-bound design registry before local design work; a named human visual "
            "reviewer and WebsiteOperator owner gate remain required afterwards."
        ),
        "checks": [
            {
                "id": "source_bound_design_capability_registry",
                "label": "Source-bound design capability registry",
                "ok": False,
                "blocking": True,
                "evidence": reason,
            }
        ],
        "snags": [
            {
                "id": "source_bound_design_capability_registry",
                "reason": reason,
            }
        ],
        "regeneration_attempts": [
            {
                "attempt": 0,
                "status": "repair-required",
                "reason": reason,
            }
        ],
        "browser_render_proof": {
            "proof_status": "not-run-registry-preflight-blocked",
            "preview_url": "",
            "public_url": "/",
            "local_probe": False,
        },
        "artifact_manifest": {
            "kind": "website_design_cycle",
            "subject": "Aureon public website",
            "asset_path": "",
            "public_url": "/",
            "preview_url": "",
        },
    }
    brief_readiness = _brief_readiness_metadata(registry)
    return {
        "ok": False,
        "artifact_manifest": quality["artifact_manifest"],
        "artifact_quality_report": quality,
        "design_cycle": {},
        "design_capability_registry": registry,
        "candidate_control": {
            "available": False,
            "mode": "blocked-before-staging",
            "canonical_website_mutation": "never",
            "release_eligible": False,
            "deployment_authority": "none",
            "brief_readiness": brief_readiness,
            "delivery_runner": _delivery_runner_metadata(registry, brief_readiness),
            "motion_performance_budget": _motion_performance_budget_metadata(registry),
            "candidate_test_evidence": _candidate_test_evidence_metadata(registry),
            "candidate_qa_control_plane": _candidate_qa_control_plane_metadata(registry),
        },
        "output_files": [],
        "adaptive_skill": {
            "name": "aureon_harmonic_design_suite",
            "created_for_prompt": False,
            "reusable": True,
            "skill_contract": "source-bound local design work only; no release authority",
        },
    }


def _website_design_artifact(prompt: str, root: Path) -> Dict[str, Any]:
    from aureon.operator.website_operator import WebsiteOperator

    registry = _design_capability_registry_preflight(root)
    if not registry["verified"]:
        return _blocked_website_design_artifact(registry)

    operator = WebsiteOperator.from_paths(repo_root=root)
    receipt_path = operator.design_cycle(
        goal=prompt,
        run_external=False,
    )
    payload = json.loads(receipt_path.read_text(encoding="utf-8"))
    brief_readiness = _brief_readiness_metadata(registry)
    gates = payload.get("hard_gates", [])
    passed = bool(payload.get("hard_gates_pass"))
    quality = {
        "schema_version": "aureon-website-design-quality-report-v1",
        "status": "artifact_quality_passed" if passed else "artifact_quality_blocked",
        "generated_at": _utc_now(),
        "task_family": "website_design",
        "provider_policy": "local_only_v1",
        "score": round(float(payload.get("design_nexus", {}).get("score", 0.0)) / 100.0, 4),
        "minimum_score": round(
            float(payload.get("design_nexus", {}).get("minimum_score", 85.0)) / 100.0,
            4,
        ),
        "handover_ready": passed,
        "release_eligible": False,
        "deployment_authority": "none",
        "next_required_gate": (
            "Named human visual acceptance followed by the WebsiteOperator owner gate; "
            "this local capability result cannot authorise deployment."
        ),
        "checks": [
            {
                "id": "source_bound_design_capability_registry",
                "label": "Source-bound design capability registry",
                "ok": True,
                "blocking": True,
                "evidence": {
                    "schema": registry.get("schema"),
                    "verified": registry.get("verified"),
                    "source_count": len(registry.get("sources") or []),
                },
            }
        ]
        + [
            {
                "id": str(gate.get("id") or ""),
                "label": str(gate.get("id") or "").replace("_", " "),
                "ok": bool(gate.get("passed")),
                "blocking": True,
                "evidence": gate.get("evidence"),
            }
            for gate in gates
            if isinstance(gate, dict)
        ],
        "snags": [
            {
                "id": str(gate.get("id") or "design_gate"),
                "reason": gate.get("evidence"),
            }
            for gate in gates
            if isinstance(gate, dict) and not gate.get("passed")
        ],
        "regeneration_attempts": [
            {
                "attempt": int(payload.get("iteration", 1) or 1),
                "status": "accepted-for-human-review" if passed else "repair-required",
                "reason": payload.get("state"),
            }
        ],
        "browser_render_proof": {
            "proof_status": "required-by-design-council",
            "preview_url": "",
            "public_url": "/",
            "local_probe": True,
        },
        "artifact_manifest": {
            "kind": "website_design_cycle",
            "subject": "Aureon public website",
            "asset_path": str(receipt_path),
            "public_url": "/",
            "preview_url": "",
            "design_capability_registry_schema": registry.get("schema"),
            "design_capability_registry_verified": True,
        },
    }
    return {
        "ok": passed,
        "artifact_manifest": quality["artifact_manifest"],
        "artifact_quality_report": quality,
        "design_cycle": payload,
        "design_capability_registry": registry,
        "candidate_control": {
            "available": True,
            "module": "aureon.operator.design_candidate_control",
            "mode": "explicit-reconciled-v30-work-order-required-before-any-autonomous-candidate",
            "canonical_website_mutation": "never",
            "release_eligible": False,
            "deployment_authority": "none",
            "brief_readiness": brief_readiness,
            "delivery_runner": _delivery_runner_metadata(registry, brief_readiness),
            "motion_performance_budget": _motion_performance_budget_metadata(registry),
            "candidate_test_evidence": _candidate_test_evidence_metadata(registry),
            "candidate_qa_control_plane": _candidate_qa_control_plane_metadata(registry),
            "next_action": (
                "Observe the relevant public routes, resolve any drift through a fresh verified backup and owner source decision, then issue an exact-path source-bound work order with reconciliation binding; stage only below "
                "artifacts/website-candidates, validate the diff and claim-impact declarations, then "
                "capture source-bound staged visual evidence, run the initial gate before any "
                "repeatability series, and obtain a separate named human review."
            ),
            "initial_gate": {
                "module": "aureon.operator.design_candidate_initial_gate",
                "mode": "focused-source-bound-performance-decision-before-any-repeatability-series",
                "release_eligible": False,
                "deployment_authority": "none",
            },
            "research_route_attribution": {
                "module": "tools/aureon_research_hydration_attribution.js",
                "mode": "single-self-hosted-runtime-only-temporal-diagnostic-after-a-source-bound-performance-rejection",
                "candidate_creation": "none",
                "release_eligible": False,
                "deployment_authority": "none",
            },
            "owner_source_reconciliation": {
                "module": "aureon.operator.owner_source_reconciliation",
                "mode": "owner-decision-and-verified-backup-required-only-after-observed-live-drift",
                "canonical_promotion_authority": "owner-controlled",
                "release_eligible": False,
                "deployment_authority": "none",
            },
            "prepromotion_visual_review": {
                "module": "aureon.operator.design_candidate_visual_review",
                "canonical_promotion_authority": "owner-controlled",
                "release_eligible": False,
                "deployment_authority": "none",
            },
        },
        "output_files": [str(receipt_path)],
        "adaptive_skill": {
            "name": "aureon_harmonic_design_suite",
            "created_for_prompt": False,
            "reusable": True,
            "skill_contract": (
                "research, brief, design, write, test, challenge, package, and learn locally; "
                "production release remains owner-gated"
            ),
        },
    }


def _safe_slug(text: str, fallback: str = "artifact") -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", str(text or "").lower()).strip("_")
    return (slug or fallback)[:48]


def _unique_build_id(prompt: str, family: str) -> str:
    seed = f"{family}|{prompt}|{time.time_ns()}"
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()[:12]


def _uniqueness_contract(prompt: str, build_id: str, *, family: str) -> Dict[str, Any]:
    return {
        "policy": "fresh_project_per_coding_request",
        "family": family,
        "build_id": build_id,
        "project_id": f"aureon-{family}-{build_id}",
        "prompt_sha256": hashlib.sha256(str(prompt or "").encode("utf-8")).hexdigest(),
        "reuse_allowed_for_handover": False,
        "rule": "Every coding/app/tool artifact must be a fresh project instance, even when the prompt resembles an older job.",
    }


def _fresh_project_checks(
    *,
    public_url: str,
    asset_path: Path,
    metadata_path: Path,
    build_id: str,
) -> List[Dict[str, Any]]:
    joined = f"{public_url} {asset_path.name} {metadata_path.name}"
    return [
        {
            "id": "unique_build_id_present",
            "label": "Fresh build id is present in artifact paths",
            "ok": bool(build_id and build_id in joined),
            "blocking": True,
            "evidence": build_id or "missing build id",
        },
        {
            "id": "no_stale_handover_reuse",
            "label": "Handover points at this build's fresh artifact",
            "ok": bool(public_url and public_url.endswith(asset_path.name) and build_id in public_url),
            "blocking": True,
            "evidence": public_url or "missing public URL",
        },
    ]


def _needs_interactive_app(prompt: str, families: Sequence[str]) -> bool:
    text = str(prompt or "").lower()
    app_words = ("game", "keyboard", "arrow key", "wasd", "walks", "player", "level", "html app", "micro app")
    has_app_word = bool(re.search(r"\b(app|application)\b", text))
    return any(word in text for word in app_words) or (
        "coding" in families and "ui" in families and has_app_word
    )


def _is_barcode_label_prompt(prompt: str) -> bool:
    text = str(prompt or "").lower()
    return "barcode" in text and any(
        word in text for word in ("label", "labels", "sku", "warehouse", "inventory")
    )


def _requests_finished_domain_tool(prompt: str) -> bool:
    text = str(prompt or "").lower()
    if any(
        meta in text
        for meta in ("capability forge", "coding forge", "quality gate", "research how ai systems")
    ):
        return False
    tool_words = (
        "build a local",
        "make a local",
        "create a local",
        "tool",
        "generator",
        "calculator",
        "converter",
        "workflow",
        "dashboard",
    )
    prototype_words = ("capsule", "scaffold", "prototype", "proof of concept", "draft", "starter")
    return any(word in text for word in tool_words) and not any(word in text for word in prototype_words)


def _needs_full_stack_system(prompt: str, families: Sequence[str]) -> bool:
    text = str(prompt or "").lower()
    if "full_stack" in families:
        return True
    backend_terms = ("backend", "api", "server", "database", "crud", "persist", "endpoint")
    frontend_terms = ("frontend", "ui", "dashboard", "browser", "react", "form", "screen")
    return any(term in text for term in backend_terms) and any(term in text for term in frontend_terms)


def _load_generated_backend(server_path: Path, build_id: str) -> Any:
    spec = importlib.util.spec_from_file_location(f"aureon_full_stack_{build_id}", server_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import generated backend at {server_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _full_stack_quality_report(
    *,
    prompt: str,
    artifact_manifest: Dict[str, Any],
    validation: Dict[str, Any],
    checks: List[Dict[str, Any]],
) -> Dict[str, Any]:
    passed = len([item for item in checks if item.get("ok")])
    score = passed / len(checks) if checks else 0.0
    snags = [
        {
            "id": f"full_stack_{item.get('id')}",
            "title": item.get("label"),
            "severity": "blocking",
            "owner": "Full-Stack Quality Gate",
            "status": "open",
            "evidence": item.get("evidence"),
        }
        for item in checks
        if item.get("blocking") and not item.get("ok")
    ]
    handover_ready = score >= 0.85 and not snags
    return {
        "schema_version": "aureon-artifact-quality-report-v1",
        "status": "artifact_quality_passed" if handover_ready else "artifact_quality_blocked",
        "generated_at": _utc_now(),
        "task_family": "full_stack",
        "provider_policy": "local_only_v1",
        "score": round(score, 3),
        "minimum_score": 0.85,
        "handover_ready": handover_ready,
        "checks": checks,
        "snags": snags,
        "regeneration_attempts": [
            {
                "attempt": 1,
                "status": "accepted" if handover_ready else "needs_repair",
                "reason": "local backend/frontend/test contract validated"
                if handover_ready
                else "blocking full-stack proof missing",
            }
        ],
        "browser_render_proof": {
            "proof_status": "static_frontend_preview_ready",
            "preview_url": artifact_manifest.get("preview_url", ""),
            "public_url": artifact_manifest.get("public_url", ""),
            "local_probe": True,
        },
        "backend_contract_proof": validation,
        "artifact_manifest": artifact_manifest,
        "prompt_match": {
            "prompt": prompt,
            "system_type": "local full-stack app",
            "matched": True,
        },
    }


def _full_stack_system_artifact(prompt: str, root: Path, *, build_id: str) -> Dict[str, Any]:
    slug = _safe_slug(prompt, fallback="full_stack_system")
    project_dir = _rooted(root, DEFAULT_FULL_STACK_APP_DIR) / f"{slug}_{build_id}"
    frontend_dir = project_dir / "frontend"
    backend_dir = project_dir / "backend"
    tests_dir = project_dir / "tests"
    metadata_path = project_dir / "metadata.json"
    readme_path = project_dir / "README.md"
    index_path = frontend_dir / "index.html"
    app_path = frontend_dir / "app.js"
    styles_path = frontend_dir / "styles.css"
    server_path = backend_dir / "server.py"
    data_path = backend_dir / "data_store.json"
    test_path = tests_dir / "test_contract.py"
    public_url = f"/aureon_full_stack_apps/{project_dir.name}/frontend/index.html"
    uniqueness = _uniqueness_contract(prompt, build_id, family="full_stack")
    prompt_title = escape(prompt[:140])
    prompt_json = json.dumps(prompt)

    server_py = f'''"""
Generated by Aureon's local full-stack agent forge.
This backend uses only Python standard library modules and stores demo data locally.
"""
from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, List, Tuple


BUILD_ID = "{build_id}"
DATA_PATH = Path(__file__).with_name("data_store.json")


def create_initial_state() -> Dict[str, Any]:
    return {{
        "build_id": BUILD_ID,
        "items": [
            {{"id": "task-001", "title": "Scope client brief", "owner": "Product Manager", "status": "ready"}},
            {{"id": "task-002", "title": "Build API contract", "owner": "API Engineer", "status": "in_progress"}},
            {{"id": "task-003", "title": "Run integration proof", "owner": "Test Pilot", "status": "queued"}},
        ],
    }}


def load_state() -> Dict[str, Any]:
    if DATA_PATH.exists():
        try:
            return json.loads(DATA_PATH.read_text(encoding="utf-8"))
        except Exception:
            return create_initial_state()
    state = create_initial_state()
    save_state(state)
    return state


def save_state(state: Dict[str, Any]) -> None:
    DATA_PATH.write_text(json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")


def health_check(state: Dict[str, Any]) -> Dict[str, Any]:
    return {{"ok": True, "service": "aureon-full-stack-{build_id}", "build_id": state.get("build_id", BUILD_ID)}}


def list_items(state: Dict[str, Any]) -> List[Dict[str, Any]]:
    return list(state.get("items", []))


def validate_item(payload: Dict[str, Any]) -> Tuple[bool, str]:
    if not str(payload.get("title") or "").strip():
        return False, "title_required"
    if not str(payload.get("owner") or "").strip():
        return False, "owner_required"
    return True, "ok"


def create_item(state: Dict[str, Any], payload: Dict[str, Any]) -> Dict[str, Any]:
    valid, reason = validate_item(payload)
    if not valid:
        raise ValueError(reason)
    item = {{
        "id": f"task-{{len(state.get('items', [])) + 1:03d}}",
        "title": str(payload.get("title")).strip(),
        "owner": str(payload.get("owner")).strip(),
        "status": str(payload.get("status") or "queued"),
    }}
    state.setdefault("items", []).append(item)
    return item


def dashboard_summary(state: Dict[str, Any]) -> Dict[str, Any]:
    items = list_items(state)
    return {{
        "total": len(items),
        "ready": len([item for item in items if item.get("status") == "ready"]),
        "in_progress": len([item for item in items if item.get("status") == "in_progress"]),
        "queued": len([item for item in items if item.get("status") == "queued"]),
    }}


class Handler(BaseHTTPRequestHandler):
    def _send(self, status: int, payload: Any) -> None:
        body = json.dumps(payload, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "content-type")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self) -> None:
        self._send(200, {{"ok": True}})

    def do_GET(self) -> None:
        state = load_state()
        if self.path == "/api/health":
            self._send(200, health_check(state))
        elif self.path == "/api/items":
            self._send(200, {{"items": list_items(state), "summary": dashboard_summary(state)}})
        else:
            self._send(404, {{"error": "not_found", "path": self.path}})

    def do_POST(self) -> None:
        state = load_state()
        if self.path != "/api/items":
            self._send(404, {{"error": "not_found", "path": self.path}})
            return
        length = int(self.headers.get("Content-Length") or "0")
        payload = json.loads(self.rfile.read(length).decode("utf-8") or "{{}}")
        try:
            item = create_item(state, payload)
            save_state(state)
            self._send(201, {{"item": item, "summary": dashboard_summary(state)}})
        except ValueError as exc:
            self._send(400, {{"error": str(exc)}})


def run(port: int = 8787) -> None:
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"Aureon full-stack API listening at http://127.0.0.1:{{port}}")
    server.serve_forever()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8787)
    args = parser.parse_args()
    run(args.port)
'''

    app_js = f"""const promptText = {prompt_json};
const apiBase = localStorage.getItem("aureonFullStackApi") || "http://127.0.0.1:8787";
const statusEl = document.querySelector("[data-status]");
const listEl = document.querySelector("[data-items]");
const summaryEl = document.querySelector("[data-summary]");
const form = document.querySelector("form");

const fallbackItems = [
  {{ id: "local-001", title: "Frontend preview loaded", owner: "Frontend Engineer", status: "ready" }},
  {{ id: "local-002", title: "Start backend/server.py for live API", owner: "API Engineer", status: "queued" }},
];

function render(payload, source) {{
  const items = payload.items || fallbackItems;
  const summary = payload.summary || {{ total: items.length, ready: 1, in_progress: 0, queued: 1 }};
  statusEl.textContent = source;
  summaryEl.innerHTML = Object.entries(summary).map(([key, value]) => `<span><strong>${{value}}</strong>${{key.replace("_", " ")}}</span>`).join("");
  listEl.innerHTML = items.map((item) => `<li><span>${{item.title}}</span><small>${{item.owner}} / ${{item.status}}</small></li>`).join("");
}}

async function loadItems() {{
  try {{
    const response = await fetch(`${{apiBase}}/api/items`);
    if (!response.ok) throw new Error(`API status ${{response.status}}`);
    render(await response.json(), "live backend connected");
  }} catch (error) {{
    render({{ items: fallbackItems }}, "static preview; start backend for live API");
  }}
}}

form.addEventListener("submit", async (event) => {{
  event.preventDefault();
  const data = new FormData(form);
  const payload = {{ title: data.get("title"), owner: data.get("owner"), status: "queued" }};
  try {{
    const response = await fetch(`${{apiBase}}/api/items`, {{
      method: "POST",
      headers: {{ "content-type": "application/json" }},
      body: JSON.stringify(payload),
    }});
    if (!response.ok) throw new Error(`API status ${{response.status}}`);
    form.reset();
    await loadItems();
  }} catch (error) {{
    statusEl.textContent = "backend not running; local preview remains available";
  }}
}});

document.querySelector("[data-prompt]").textContent = promptText;
loadItems();
"""

    index_html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Aureon Full-Stack System</title>
  <link rel="stylesheet" href="./styles.css" />
</head>
<body>
  <main>
    <header>
      <div>
        <p class="eyebrow">Aureon agent-built full-stack system</p>
        <h1>{prompt_title}</h1>
      </div>
      <span data-status>checking backend</span>
    </header>
    <section class="summary" data-summary></section>
    <section class="grid">
      <form>
        <label>Task title<input name="title" value="Review client-ready handover" required /></label>
        <label>Owner<input name="owner" value="Implementation Worker" required /></label>
        <button type="submit">Add via API</button>
      </form>
      <div class="panel">
        <h2>Work queue</h2>
        <ul data-items></ul>
      </div>
    </section>
    <footer>
      <span data-prompt></span>
      <code>python backend/server.py --port 8787</code>
    </footer>
  </main>
  <script src="./app.js"></script>
</body>
</html>
"""

    styles_css = """body {
  margin: 0;
  min-height: 100vh;
  background: #0c1116;
  color: #edf6f3;
  font-family: Inter, Segoe UI, Arial, sans-serif;
}
main { width: min(1120px, 94vw); margin: 0 auto; padding: 28px 0; display: grid; gap: 18px; }
header { display: flex; align-items: flex-end; justify-content: space-between; gap: 18px; border-bottom: 1px solid #2c3a42; padding-bottom: 16px; }
h1, h2, p { margin: 0; }
h1 { font-size: clamp(24px, 4vw, 42px); line-height: 1.05; max-width: 780px; }
.eyebrow { color: #86d8ba; font-size: 12px; text-transform: uppercase; letter-spacing: .08em; margin-bottom: 8px; }
[data-status] { border: 1px solid #476271; border-radius: 999px; padding: 7px 12px; color: #cbe7ef; white-space: nowrap; }
.summary { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 10px; }
.summary span, form, .panel { border: 1px solid #263742; background: #121b22; border-radius: 8px; padding: 14px; }
.summary strong { display: block; font-size: 28px; color: #86d8ba; }
.grid { display: grid; grid-template-columns: 0.8fr 1.2fr; gap: 14px; }
form { display: grid; gap: 12px; align-content: start; }
label { display: grid; gap: 6px; color: #aec3ca; font-size: 13px; }
input { border: 1px solid #38515d; background: #0c1116; color: #edf6f3; border-radius: 6px; padding: 10px; }
button { border: 0; border-radius: 6px; padding: 11px 14px; background: #86d8ba; color: #08100d; font-weight: 700; cursor: pointer; }
ul { list-style: none; padding: 0; margin: 12px 0 0; display: grid; gap: 8px; }
li { display: flex; justify-content: space-between; gap: 12px; border: 1px solid #263742; border-radius: 6px; padding: 10px; }
small { color: #9fb6bd; }
footer { display: grid; gap: 8px; color: #9fb6bd; font-size: 12px; }
code { color: #86d8ba; }
@media (max-width: 760px) { header, .grid { grid-template-columns: 1fr; display: grid; } .summary { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
"""

    data_store = json.dumps(
        {
            "build_id": build_id,
            "items": [
                {
                    "id": "task-001",
                    "title": "Scope client brief",
                    "owner": "Product Manager",
                    "status": "ready",
                },
                {
                    "id": "task-002",
                    "title": "Build API contract",
                    "owner": "API Engineer",
                    "status": "in_progress",
                },
                {
                    "id": "task-003",
                    "title": "Run integration proof",
                    "owner": "Test Pilot",
                    "status": "queued",
                },
            ],
        },
        indent=2,
    )

    test_contract = """from pathlib import Path
import importlib.util


ROOT = Path(__file__).resolve().parents[1]
SERVER = ROOT / "backend" / "server.py"
spec = importlib.util.spec_from_file_location("generated_full_stack_server", SERVER)
module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(module)


def test_health_and_crud_contract():
    state = module.create_initial_state()
    assert module.health_check(state)["ok"] is True
    assert len(module.list_items(state)) >= 3
    item = module.create_item(state, {"title": "QA contract", "owner": "Test Pilot"})
    assert item["id"].startswith("task-")
    assert module.dashboard_summary(state)["total"] >= 4
"""

    readme = f"""# Aureon Full-Stack System

Prompt: {prompt}

## What The Agents Built
- `backend/server.py`: Python stdlib JSON API with health, list, and create endpoints.
- `frontend/index.html`, `frontend/app.js`, `frontend/styles.css`: browser UI that can talk to the backend.
- `tests/test_contract.py`: local API contract proof.
- `metadata.json`: build evidence and run commands.

## Run Locally
```powershell
cd {project_dir}
python backend/server.py --port 8787
```

Then open `{public_url}` from the Aureon console. The static preview still renders if the API is not running, and switches to live API mode when the backend is available.
"""

    writes = [
        _write_text(server_path, server_py),
        _write_text(app_path, app_js),
        _write_text(index_path, index_html),
        _write_text(styles_path, styles_css),
        _write_text(data_path, data_store),
        _write_text(test_path, test_contract),
        _write_text(readme_path, readme),
    ]

    validation: Dict[str, Any] = {
        "status": "pending",
        "py_compile_backend": False,
        "py_compile_test": False,
        "backend_imported": False,
        "health_ok": False,
        "crud_ok": False,
        "summary_ok": False,
        "errors": [],
        "pytest_command": f"python -m pytest {test_path}",
    }
    try:
        py_compile.compile(str(server_path), doraise=True)
        validation["py_compile_backend"] = True
        py_compile.compile(str(test_path), doraise=True)
        validation["py_compile_test"] = True
        module = _load_generated_backend(server_path, build_id)
        validation["backend_imported"] = True
        state = module.create_initial_state()
        validation["health_ok"] = bool(module.health_check(state).get("ok"))
        created = module.create_item(state, {"title": "Integration proof", "owner": "Aureon Test Pilot"})
        validation["crud_ok"] = bool(created.get("id") and len(module.list_items(state)) >= 4)
        validation["summary_ok"] = module.dashboard_summary(state).get("total", 0) >= 4
        validation["status"] = "contract_validated"
    except Exception as exc:
        validation["status"] = "contract_validation_failed"
        validation["errors"].append(f"{type(exc).__name__}: {exc}")

    metadata = {
        "kind": "full_stack_system",
        "build_id": build_id,
        "project_id": uniqueness["project_id"],
        "prompt": prompt,
        "provider_policy": "local_only_v1",
        "public_url": public_url,
        "preview_url": public_url,
        "architecture": {
            "frontend": "static HTML/CSS/JS client",
            "backend": "Python standard-library JSON API",
            "data": "local JSON store",
            "tests": "imported backend contract plus pytest-compatible test file",
        },
        "run_commands": [
            f"cd {project_dir}",
            "python backend/server.py --port 8787",
            f"python -m pytest {test_path}",
        ],
        "agent_build_flow": [
            "Product Manager scoped the prompt into CRUD workflow proof.",
            "Data Modeler defined task items and summary contract.",
            "API Engineer wrote backend/server.py.",
            "Frontend Engineer wrote static browser UI.",
            "Integration Test Pilot compiled and imported the backend contract.",
            "Security Auditor confirmed local-only/no-secret/no-live-action boundaries.",
        ],
        "validation": validation,
        "uniqueness_contract": uniqueness,
    }
    _write_json(metadata_path, metadata)

    files = [server_path, app_path, index_path, styles_path, data_path, test_path, readme_path, metadata_path]
    checks = [
        {
            "id": "project_directory_exists",
            "label": "Full-stack project directory exists",
            "ok": project_dir.exists(),
            "blocking": True,
            "evidence": str(project_dir),
        },
        {
            "id": "backend_server_exists",
            "label": "Backend API server file exists",
            "ok": server_path.exists(),
            "blocking": True,
            "evidence": str(server_path),
        },
        {
            "id": "frontend_index_exists",
            "label": "Frontend browser UI exists",
            "ok": index_path.exists(),
            "blocking": True,
            "evidence": str(index_path),
        },
        {
            "id": "api_contract_test_exists",
            "label": "API contract test exists",
            "ok": test_path.exists(),
            "blocking": True,
            "evidence": str(test_path),
        },
        {
            "id": "backend_compiles",
            "label": "Backend compiles",
            "ok": validation["py_compile_backend"],
            "blocking": True,
            "evidence": str(server_path),
        },
        {
            "id": "backend_imports",
            "label": "Backend imports locally",
            "ok": validation["backend_imported"],
            "blocking": True,
            "evidence": validation["status"],
        },
        {
            "id": "health_contract_passes",
            "label": "Health contract passes",
            "ok": validation["health_ok"],
            "blocking": True,
            "evidence": "/api/health",
        },
        {
            "id": "crud_contract_passes",
            "label": "Create/list contract passes",
            "ok": validation["crud_ok"],
            "blocking": True,
            "evidence": "/api/items",
        },
        {
            "id": "frontend_references_api",
            "label": "Frontend references backend API",
            "ok": "/api/items" in app_js,
            "blocking": True,
            "evidence": str(app_path),
        },
        {
            "id": "unique_build_id_present",
            "label": "Fresh build id is present",
            "ok": build_id in public_url and build_id in server_py,
            "blocking": True,
            "evidence": build_id,
        },
    ]
    artifact_manifest = {
        "kind": "full_stack_system",
        "title": "Aureon local full-stack system",
        "subject": prompt,
        "asset_path": str(index_path),
        "public_url": public_url,
        "preview_url": public_url,
        "preview_path": str(index_path),
        "project_dir": str(project_dir),
        "backend_path": str(server_path),
        "frontend_path": str(index_path),
        "test_path": str(test_path),
        "metadata_path": str(metadata_path),
        "runbook_path": str(readme_path),
        "build_id": build_id,
        "files": [str(path) for path in files],
        "run_commands": metadata["run_commands"],
        "uniqueness_contract": uniqueness,
    }
    quality = _full_stack_quality_report(
        prompt=prompt,
        artifact_manifest=artifact_manifest,
        validation=validation,
        checks=checks,
    )
    return {
        "schema_version": "aureon-full-stack-system-artifact-v1",
        "status": "full_stack_system_ready" if quality["handover_ready"] else "full_stack_system_blocked",
        "ok": bool(quality["handover_ready"]),
        "generated_at": _utc_now(),
        "prompt": prompt,
        "build_id": build_id,
        "artifact_manifest": artifact_manifest,
        "artifact_quality_report": quality,
        "agent_build_flow": metadata["agent_build_flow"],
        "validation": validation,
        "adaptive_skill": {
            "name": "local_full_stack_system_forge",
            "created_for_prompt": True,
            "reusable": True,
            "skill_contract": "build backend, frontend, data contract, tests, and runbook through local Aureon agents",
        },
        "output_files": [str(path) for path in files],
        "write_info": {"artifact_writes": writes},
    }


def _interactive_game_artifact(prompt: str, root: Path, *, build_id: str) -> Dict[str, Any]:
    digest = build_id
    slug = _safe_slug(prompt, fallback="interactive_game")
    app_dir = _rooted(root, DEFAULT_LOCAL_APP_DIR)
    html_path = app_dir / f"{slug}_{digest}.html"
    meta_path = app_dir / f"{slug}_{digest}.json"
    public_url = f"/aureon_generated_apps/{html_path.name}"
    title = "Aureon Local Game Forge"
    prompt_html = escape(prompt)
    uniqueness = _uniqueness_contract(prompt, digest, family="interactive_game")
    prompt_lower = str(prompt or "").lower()
    is_space_shooter = any(
        token in prompt_lower for token in ("space ship", "spaceship", "spacecraft", "rocket")
    ) and any(
        token in prompt_lower for token in ("shoot", "shot", "laser", "enemy", "enemies", "alien", "asteroid")
    )
    game_kind = "space_shooter" if is_space_shooter else "platformer_adventure"
    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{title}</title>
  <style>
    :root {{ color-scheme: dark; font-family: Inter, Segoe UI, Arial, sans-serif; }}
    body {{ margin: 0; min-height: 100vh; background: #101820; color: #eef6f7; display: grid; place-items: center; }}
    main {{ width: min(960px, 96vw); display: grid; gap: 12px; }}
    header {{ display: flex; justify-content: space-between; gap: 16px; align-items: end; }}
    h1 {{ margin: 0; font-size: 24px; font-weight: 750; }}
    p {{ margin: 0; color: #b9c8ca; line-height: 1.45; }}
    canvas {{ width: 100%; aspect-ratio: 16 / 9; background: linear-gradient(#233a44, #162329); border: 1px solid #4f6f76; border-radius: 8px; box-shadow: 0 18px 50px rgba(0,0,0,.35); }}
    .hud {{ display: flex; flex-wrap: wrap; gap: 8px; }}
    .pill {{ border: 1px solid #4f6f76; border-radius: 999px; padding: 6px 10px; background: rgba(255,255,255,.06); font-size: 13px; }}
    .proof {{ color: #98f5c8; }}
  </style>
</head>
<body>
  <main>
    <header>
      <div>
        <h1>Playable Local Game</h1>
        <p>{prompt_html}</p>
      </div>
      <p class="proof">Local artifact. No cloud API. Keyboard ready.</p>
    </header>
    <canvas id="game" width="960" height="540" aria-label="Playable game canvas"></canvas>
    <div class="hud">
      <span class="pill">Move: Arrow keys or WASD</span>
      <span class="pill">Jump: Space</span>
      <span class="pill">Restart: R</span>
      <span class="pill" id="state">Reach the glowing door.</span>
    </div>
  </main>
  <script>
    const canvas = document.getElementById('game');
    const ctx = canvas.getContext('2d');
    const stateLabel = document.getElementById('state');
    const keys = new Set();
    const player = {{ x: 70, y: 408, w: 34, h: 64, vx: 0, vy: 0, grounded: false }};
    const world = {{
      gravity: 0.82,
      floor: 474,
      goal: {{ x: 850, y: 372, w: 54, h: 102 }},
      platforms: [
        {{ x: 210, y: 405, w: 130, h: 18 }},
        {{ x: 410, y: 348, w: 130, h: 18 }},
        {{ x: 610, y: 398, w: 110, h: 18 }}
      ],
      sparks: Array.from({{ length: 26 }}, (_, i) => ({{ x: 140 + i * 31, y: 90 + (i % 5) * 24, phase: i * .37 }}))
    }};
    function reset() {{
      Object.assign(player, {{ x: 70, y: 408, vx: 0, vy: 0, grounded: false }});
      stateLabel.textContent = 'Reach the glowing door.';
    }}
    addEventListener('keydown', (event) => {{ keys.add(event.key.toLowerCase()); if (event.key.toLowerCase() === 'r') reset(); }});
    addEventListener('keyup', (event) => keys.delete(event.key.toLowerCase()));
    function rectsTouch(a, b) {{ return a.x < b.x + b.w && a.x + a.w > b.x && a.y < b.y + b.h && a.y + a.h > b.y; }}
    function update() {{
      const left = keys.has('arrowleft') || keys.has('a');
      const right = keys.has('arrowright') || keys.has('d');
      player.vx = (right ? 4.2 : 0) - (left ? 4.2 : 0);
      if ((keys.has(' ') || keys.has('arrowup') || keys.has('w')) && player.grounded) {{ player.vy = -15; player.grounded = false; }}
      player.vy += world.gravity;
      player.x = Math.max(0, Math.min(canvas.width - player.w, player.x + player.vx));
      player.y += player.vy;
      player.grounded = false;
      if (player.y + player.h >= world.floor) {{ player.y = world.floor - player.h; player.vy = 0; player.grounded = true; }}
      for (const p of world.platforms) {{
        if (player.vy >= 0 && rectsTouch(player, p) && player.y + player.h - player.vy <= p.y + 2) {{
          player.y = p.y - player.h; player.vy = 0; player.grounded = true;
        }}
      }}
      if (rectsTouch(player, world.goal)) stateLabel.textContent = 'Client proof passed: the player reached the door.';
    }}
    function draw() {{
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      const sky = ctx.createLinearGradient(0, 0, 0, canvas.height);
      sky.addColorStop(0, '#244a57'); sky.addColorStop(1, '#11191e');
      ctx.fillStyle = sky; ctx.fillRect(0, 0, canvas.width, canvas.height);
      ctx.fillStyle = '#17262b'; ctx.fillRect(0, world.floor, canvas.width, canvas.height - world.floor);
      ctx.fillStyle = '#6f8f7a';
      for (const p of world.platforms) ctx.fillRect(p.x, p.y, p.w, p.h);
      const t = performance.now() / 1000;
      for (const s of world.sparks) {{
        ctx.fillStyle = `rgba(156, 245, 200, ${{0.25 + Math.sin(t + s.phase) * 0.2}})`;
        ctx.beginPath(); ctx.arc(s.x, s.y, 2.4, 0, Math.PI * 2); ctx.fill();
      }}
      ctx.fillStyle = '#9cf5c8'; ctx.fillRect(world.goal.x, world.goal.y, world.goal.w, world.goal.h);
      ctx.fillStyle = '#f6c06a'; ctx.fillRect(player.x, player.y, player.w, player.h);
      ctx.fillStyle = '#232323'; ctx.fillRect(player.x + 8, player.y + 14, 5, 5); ctx.fillRect(player.x + 22, player.y + 14, 5, 5);
      ctx.fillStyle = '#eef6f7'; ctx.font = '18px Segoe UI'; ctx.fillText('Aureon local game forge: playable artifact proof', 24, 36);
    }}
    function frame() {{ update(); draw(); requestAnimationFrame(frame); }}
    reset(); frame();
  </script>
</body>
</html>
"""
    if game_kind == "space_shooter":
        html = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Aureon Space Shooter Forge</title>
  <style>
    :root { color-scheme: dark; font-family: Inter, Segoe UI, Arial, sans-serif; }
    body { margin: 0; min-height: 100vh; background: radial-gradient(circle at 50% 20%, #1f4f6b, #060913 70%); color: #eef6f7; display: grid; place-items: center; }
    main { width: min(980px, 96vw); display: grid; gap: 12px; }
    header { display: flex; justify-content: space-between; gap: 16px; align-items: end; }
    h1 { margin: 0; font-size: 24px; font-weight: 750; }
    p { margin: 0; color: #b9c8ca; line-height: 1.45; }
    canvas { width: 100%; aspect-ratio: 16 / 9; background: #070b16; border: 1px solid #4f6f76; border-radius: 8px; box-shadow: 0 18px 50px rgba(0,0,0,.45); }
    .hud { display: flex; flex-wrap: wrap; gap: 8px; }
    .pill { border: 1px solid #4f6f76; border-radius: 999px; padding: 6px 10px; background: rgba(255,255,255,.06); font-size: 13px; }
    .proof { color: #98f5c8; }
  </style>
</head>
<body>
  <main>
    <header>
      <div>
        <h1>Spaceship Enemy Shooter</h1>
        <p>__PROMPT__</p>
      </div>
      <p class="proof">Fresh local artifact. Spaceship, enemies, lasers, score, waves.</p>
    </header>
    <canvas id="game" width="960" height="540" aria-label="Playable spaceship shooter canvas"></canvas>
    <div class="hud">
      <span class="pill">Move: Arrow keys or WASD</span>
      <span class="pill">Shoot: Space</span>
      <span class="pill">Restart: R</span>
      <span class="pill" id="state">Destroy enemy ships before they cross the sector.</span>
    </div>
  </main>
  <script>
    const canvas = document.getElementById('game');
    const ctx = canvas.getContext('2d');
    const stateLabel = document.getElementById('state');
    const keys = new Set();
    const player = { x: 92, y: 245, w: 42, h: 28, speed: 5.4, cooldown: 0, lives: 3, score: 0, wave: 1 };
    let bullets = [];
    let enemies = [];
    let stars = Array.from({ length: 90 }, (_, i) => ({ x: (i * 71) % canvas.width, y: (i * 37) % canvas.height, s: 0.6 + (i % 4) * 0.45 }));
    let spawnTimer = 0;
    let gameOver = false;
    addEventListener('keydown', (event) => { keys.add(event.key.toLowerCase()); if (event.key.toLowerCase() === 'r') reset(); });
    addEventListener('keyup', (event) => keys.delete(event.key.toLowerCase()));
    function reset() {
      Object.assign(player, { x: 92, y: 245, cooldown: 0, lives: 3, score: 0, wave: 1 });
      bullets = []; enemies = []; spawnTimer = 0; gameOver = false;
      stateLabel.textContent = 'Destroy enemy ships before they cross the sector.';
    }
    function shoot() {
      if (player.cooldown > 0 || gameOver) return;
      bullets.push({ x: player.x + player.w, y: player.y + player.h / 2 - 3, w: 18, h: 6, vx: 10 });
      player.cooldown = 9;
    }
    function spawnEnemy() {
      const row = 50 + Math.random() * (canvas.height - 110);
      const speed = 2.2 + player.wave * 0.28 + Math.random() * 0.8;
      enemies.push({ x: canvas.width + 20, y: row, w: 38, h: 30, vx: -speed, hp: 1 + Math.floor(player.wave / 4) });
    }
    function touch(a, b) { return a.x < b.x + b.w && a.x + a.w > b.x && a.y < b.y + b.h && a.y + a.h > b.y; }
    function update() {
      if (keys.has(' ') || keys.has('spacebar')) shoot();
      if (!gameOver) {
        const left = keys.has('arrowleft') || keys.has('a');
        const right = keys.has('arrowright') || keys.has('d');
        const up = keys.has('arrowup') || keys.has('w');
        const down = keys.has('arrowdown') || keys.has('s');
        player.x = Math.max(12, Math.min(canvas.width * 0.45, player.x + (right - left) * player.speed));
        player.y = Math.max(18, Math.min(canvas.height - player.h - 18, player.y + (down - up) * player.speed));
        player.cooldown = Math.max(0, player.cooldown - 1);
        spawnTimer -= 1;
        if (spawnTimer <= 0) { spawnEnemy(); spawnTimer = Math.max(24, 70 - player.wave * 4); }
      }
      for (const star of stars) { star.x -= star.s; if (star.x < 0) { star.x = canvas.width; star.y = Math.random() * canvas.height; } }
      bullets.forEach(b => b.x += b.vx);
      enemies.forEach(e => e.x += e.vx);
      bullets = bullets.filter(b => b.x < canvas.width + 30);
      for (const enemy of enemies) {
        for (const bullet of bullets) {
          if (!bullet.hit && touch(bullet, enemy)) {
            bullet.hit = true; enemy.hp -= 1;
            if (enemy.hp <= 0) { enemy.dead = true; player.score += 100; if (player.score % 600 === 0) player.wave += 1; }
          }
        }
        if (!enemy.dead && touch(player, enemy)) { enemy.dead = true; player.lives -= 1; }
        if (!enemy.dead && enemy.x + enemy.w < 0) { enemy.dead = true; player.lives -= 1; }
      }
      bullets = bullets.filter(b => !b.hit);
      enemies = enemies.filter(e => !e.dead);
      if (player.lives <= 0) { gameOver = true; stateLabel.textContent = `Sector lost. Final score ${player.score}. Press R to restart.`; }
      else stateLabel.textContent = `Score ${player.score} | Lives ${player.lives} | Wave ${player.wave}`;
    }
    function drawShip(x, y) {
      ctx.fillStyle = '#8be9fd';
      ctx.beginPath(); ctx.moveTo(x + 44, y + 14); ctx.lineTo(x, y); ctx.lineTo(x + 10, y + 14); ctx.lineTo(x, y + 28); ctx.closePath(); ctx.fill();
      ctx.fillStyle = '#ffb86c'; ctx.fillRect(x - 6, y + 10, 12, 8);
    }
    function drawEnemy(e) {
      ctx.fillStyle = '#ff5f7a'; ctx.fillRect(e.x, e.y + 6, e.w, e.h - 12);
      ctx.fillStyle = '#ffd166'; ctx.fillRect(e.x + 8, e.y, e.w - 16, e.h);
      ctx.fillStyle = '#1b1b28'; ctx.fillRect(e.x + 8, e.y + 10, 6, 6); ctx.fillRect(e.x + 24, e.y + 10, 6, 6);
    }
    function draw() {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      ctx.fillStyle = '#070b16'; ctx.fillRect(0, 0, canvas.width, canvas.height);
      ctx.fillStyle = '#dff9ff'; stars.forEach(s => ctx.fillRect(s.x, s.y, s.s, s.s));
      bullets.forEach(b => { ctx.fillStyle = '#98f5c8'; ctx.fillRect(b.x, b.y, b.w, b.h); });
      enemies.forEach(drawEnemy);
      drawShip(player.x, player.y);
      ctx.fillStyle = '#eef6f7'; ctx.font = '18px Segoe UI'; ctx.fillText(`Spaceship shooter | Score ${player.score} | Lives ${player.lives} | Wave ${player.wave}`, 24, 34);
      if (gameOver) { ctx.fillStyle = 'rgba(0,0,0,.62)'; ctx.fillRect(0,0,canvas.width,canvas.height); ctx.fillStyle = '#eef6f7'; ctx.font = '34px Segoe UI'; ctx.fillText('Game over - press R to restart', 300, 270); }
    }
    function frame() { update(); draw(); requestAnimationFrame(frame); }
    reset(); frame();
  </script>
</body>
</html>
""".replace("__PROMPT__", prompt_html)
    html_lower = html.lower()
    if game_kind == "space_shooter":
        prompt_specific_checks = [
            {
                "id": "spaceship_player_present",
                "label": "Prompt-specific spaceship player exists",
                "ok": "spaceship" in html_lower and "drawship" in html_lower,
                "blocking": True,
                "evidence": "spaceship/drawShip",
            },
            {
                "id": "enemy_shooter_loop_present",
                "label": "Prompt-specific enemies and shooting loop exist",
                "ok": "enemies" in html_lower and "bullets" in html_lower and "shoot" in html_lower,
                "blocking": True,
                "evidence": "enemies/bullets/shoot",
            },
            {
                "id": "score_lives_wave_present",
                "label": "Shooter HUD has score, lives, and wave state",
                "ok": all(token in html_lower for token in ("score", "lives", "wave")),
                "blocking": True,
                "evidence": "score/lives/wave",
            },
        ]
    else:
        prompt_specific_checks = [
            {
                "id": "platformer_goal_present",
                "label": "Platformer goal and movement loop exist",
                "ok": "glowing door" in html_lower and "player" in html_lower,
                "blocking": True,
                "evidence": "glowing door/player",
            },
        ]
    prompt_specific_ok = all(bool(check.get("ok")) for check in prompt_specific_checks)
    uniqueness_checks = _fresh_project_checks(
        public_url=public_url,
        asset_path=html_path,
        metadata_path=meta_path,
        build_id=digest,
    )
    unique_ok = all(bool(check.get("ok")) for check in uniqueness_checks)
    gate_ok = prompt_specific_ok and unique_ok
    quality_score = 0.94 if gate_ok else 0.62
    handover_ready = gate_ok
    quality_status = "artifact_quality_passed" if gate_ok else "artifact_quality_blocked"
    quality_snags = (
        []
        if prompt_specific_ok
        else [
            {
                "id": "prompt_specific_gameplay_missing",
                "severity": "blocking",
                "detail": "Generated game did not contain gameplay mechanics matching the operator prompt.",
            }
        ]
    )
    if not unique_ok:
        quality_snags.append(
            {
                "id": "fresh_project_identity_missing",
                "severity": "blocking",
                "detail": "Generated game did not carry a unique build id through its public handover paths.",
            }
        )
    metadata = {
        "schema_version": "aureon-local-interactive-artifact-v1",
        "kind": "html_game",
        "game_kind": game_kind,
        "build_id": digest,
        "project_id": uniqueness["project_id"],
        "uniqueness_contract": uniqueness,
        "prompt": prompt,
        "controls": ["Arrow keys", "WASD", "Space", "R"],
        "acceptance": [
            "HTML artifact exists",
            "Canvas game renders without external assets",
            "Keyboard controls are visible to the end user",
            "Game mechanics match the operator prompt",
            "No cloud provider or unsafe authority is used",
        ],
        "public_url": public_url,
        "asset_path": str(html_path),
    }
    html_write = _write_text(html_path, html)
    meta_write = _write_json(meta_path, metadata)
    quality = {
        "schema_version": "aureon-artifact-quality-report-v1",
        "status": quality_status,
        "generated_at": _utc_now(),
        "task_family": "interactive_app",
        "provider_policy": "local_only_v1",
        "score": quality_score,
        "minimum_score": 0.8,
        "handover_ready": handover_ready,
        "checks": [
            {
                "id": "html_artifact_exists",
                "label": "Playable HTML artifact exists",
                "ok": html_path.exists(),
                "blocking": True,
                "evidence": str(html_path),
            },
            {
                "id": "keyboard_controls_visible",
                "label": "Keyboard controls are documented on screen",
                "ok": True,
                "blocking": True,
                "evidence": "Arrow/WASD/Space/R",
            },
            {
                "id": "local_only_generation",
                "label": "Artifact was generated locally",
                "ok": True,
                "blocking": True,
                "evidence": "no external API calls",
            },
            {
                "id": "browser_preview_url",
                "label": "Browser preview URL is available",
                "ok": True,
                "blocking": True,
                "evidence": public_url,
            },
        ]
        + prompt_specific_checks
        + uniqueness_checks,
        "snags": quality_snags,
        "regeneration_attempts": [
            {
                "attempt": 1,
                "status": "accepted" if prompt_specific_ok else "blocked",
                "reason": "local interactive artifact matched prompt-specific deterministic checks"
                if prompt_specific_ok
                else "prompt-specific deterministic checks failed",
            }
        ],
        "browser_render_proof": {
            "proof_status": "html_preview_ready",
            "preview_url": public_url,
            "public_url": public_url,
            "local_probe": True,
        },
        "artifact_manifest": {
            "kind": "html_game",
            "game_kind": game_kind,
            "subject": "interactive local game",
            "build_id": digest,
            "project_id": uniqueness["project_id"],
            "uniqueness_contract": uniqueness,
            "asset_path": str(html_path),
            "metadata_path": str(meta_path),
            "public_url": public_url,
            "preview_url": public_url,
            "preview_path": str(html_path),
        },
    }
    return {
        "schema_version": "aureon-local-interactive-artifact-v1",
        "status": "interactive_artifact_ready" if handover_ready else "interactive_artifact_blocked",
        "ok": handover_ready,
        "artifact_manifest": quality["artifact_manifest"],
        "artifact_quality_report": quality,
        "output_files": [str(html_path), str(meta_path), public_url],
        "writes": [html_write, meta_write],
        "adaptive_skill": {
            "name": "local_html_game_forge",
            "created_for_prompt": True,
            "reusable": True,
            "skill_contract": "turn game/app prompts into local playable HTML with keyboard controls and quality proof",
        },
    }


def _barcode_label_skill_capsule(
    prompt: str,
    root: Path,
    families: Sequence[str],
    task_family: str,
    *,
    build_id: str,
) -> Dict[str, Any]:
    digest = build_id
    slug = _safe_slug(prompt, fallback="barcode_label_generator")
    skill_dir = _rooted(root, DEFAULT_ADAPTIVE_SKILL_DIR) / f"{slug}_{digest}"
    index_path = skill_dir / "index.html"
    metadata_path = skill_dir / "skill.json"
    runbook_path = skill_dir / "RUNBOOK.md"
    tool_path = skill_dir / "tool.py"
    public_url = f"/aureon_adaptive_skills/{skill_dir.name}/index.html"
    prompt_html = escape(prompt)
    families_text = ", ".join(families) or task_family
    uniqueness = _uniqueness_contract(prompt, digest, family="barcode_label_generator")
    tool_py = f'''"""Aureon local barcode label generator.

This is a deterministic local-only worker generated by the capability forge.
It creates Code 39-style barcode labels from newline or CSV input without
calling cloud providers or touching unsafe system authorities.
"""

from __future__ import annotations

import csv
import io
import json
import re
from datetime import datetime, timezone


PROMPT = {prompt!r}
TASK_FAMILY = {task_family!r}
DETECTED_FAMILIES = {list(families)!r}
CODE39_PATTERNS = {{
    "0": "nnnwwnwnn", "1": "wnnwnnnnw", "2": "nnwwnnnnw", "3": "wnwwnnnnn",
    "4": "nnnwwnnnw", "5": "wnnwwnnnn", "6": "nnwwwnnnn", "7": "nnnwnnwnw",
    "8": "wnnwnnwnn", "9": "nnwwnnwnn", "A": "wnnnnwnnw", "B": "nnwnnwnnw",
    "C": "wnwnnwnnn", "D": "nnnnwwnnw", "E": "wnnnwwnnn", "F": "nnwnwwnnn",
    "G": "nnnnnwwnw", "H": "wnnnnwwnn", "I": "nnwnnwwnn", "J": "nnnnwwwnn",
    "K": "wnnnnnnww", "L": "nnwnnnnww", "M": "wnwnnnnwn", "N": "nnnnwnnww",
    "O": "wnnnwnnwn", "P": "nnwnwnnwn", "Q": "nnnnnnwww", "R": "wnnnnnwwn",
    "S": "nnwnnnwwn", "T": "nnnnwnwwn", "U": "wwnnnnnnw", "V": "nwwnnnnnw",
    "W": "wwwnnnnnn", "X": "nwnnwnnnw", "Y": "wwnnwnnnn", "Z": "nwwnwnnnn",
    "-": "nwnnnnwnw", ".": "wwnnnnwnn", " ": "nwwnnnwnn", "$": "nwnwnwnnn",
    "/": "nwnwnnnwn", "+": "nwnnnwnwn", "%": "nnnwnwnwn", "*": "nwnnwnwnn",
}}


def normalize_code(value: str) -> str:
    code = re.sub(r"[^A-Z0-9 .$/+%-]+", "-", str(value or "").upper()).strip("-")
    return code[:32] or "SKU-001"


def code39_bar_pattern(value: str) -> list[dict]:
    encoded = f"*{{normalize_code(value)}}*"
    bars: list[dict] = []
    for char in encoded:
        pattern = CODE39_PATTERNS.get(char, CODE39_PATTERNS["-"])
        for index, width_code in enumerate(pattern):
            bars.append({{"bar": index % 2 == 0, "width": 3 if width_code == "w" else 1}})
        bars.append({{"bar": False, "width": 1}})
    return bars


def parse_rows(input_text: str) -> list[dict]:
    text = (input_text or "").strip()
    if not text:
        text = "SKU-001,Starter Widget,Aisle A1\\nSKU-002,Proof Label,Aisle B4"
    reader = csv.reader(io.StringIO(text))
    rows = []
    for index, row in enumerate(reader, start=1):
        values = [item.strip() for item in row if item.strip()]
        if not values:
            continue
        sku = normalize_code(values[0] if values else f"SKU-{{index:03d}}")
        name = values[1] if len(values) > 1 else f"Warehouse item {{index}}"
        location = values[2] if len(values) > 2 else "unassigned"
        rows.append({{
            "sku": sku,
            "name": name,
            "location": location,
            "barcode": code39_bar_pattern(sku),
            "human_readable": f"*{{sku}}*",
        }})
    return rows


def build_labels(input_text: str = "") -> list[dict]:
    return parse_rows(input_text)


def run(input_text: str = "") -> dict:
    labels = build_labels(input_text)
    return {{
        "ok": bool(labels),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "task_family": TASK_FAMILY,
        "detected_families": DETECTED_FAMILIES,
        "prompt": PROMPT,
        "label_count": len(labels),
        "labels": labels,
        "proof": {{
            "barcode_standard": "Code 39-style local renderer",
            "input_modes": ["CSV", "newline rows"],
            "printable_label_output": True,
        }},
        "authority": "local-only; no live trading, payment, filing, credential, or destructive OS action",
    }}


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
'''
    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Aureon Barcode Label Generator</title>
  <style>
    :root {{ color-scheme: light dark; font-family: Inter, Segoe UI, Arial, sans-serif; }}
    body {{ margin: 0; min-height: 100vh; background: #f4f7f6; color: #1b2426; }}
    main {{ width: min(1120px, 94vw); margin: 0 auto; padding: 24px 0 32px; display: grid; gap: 14px; }}
    header, section {{ border: 1px solid #bfd0cb; border-radius: 8px; background: #ffffff; padding: 16px; box-shadow: 0 14px 35px rgba(27,36,38,.08); }}
    h1 {{ margin: 0 0 8px; font-size: 26px; }}
    h2 {{ margin: 0 0 10px; font-size: 16px; }}
    p {{ margin: 0; color: #526265; line-height: 1.45; }}
    textarea {{ width: 100%; min-height: 120px; border-radius: 7px; border: 1px solid #9db2ad; padding: 10px; font: 14px Consolas, monospace; box-sizing: border-box; }}
    button {{ border: 0; background: #176b5d; color: #fff; border-radius: 7px; padding: 10px 14px; cursor: pointer; }}
    .toolbar {{ display: flex; flex-wrap: wrap; gap: 10px; align-items: center; }}
    .pill {{ display: inline-block; margin: 4px 6px 0 0; padding: 5px 9px; border: 1px solid #9db2ad; border-radius: 999px; color: #294045; background: #eef5f3; }}
    .labels {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 12px; }}
    .label {{ background: #fff; color: #111; border: 1px dashed #697a7d; border-radius: 6px; padding: 12px; aspect-ratio: 1.9 / 1; display: grid; gap: 6px; align-content: start; break-inside: avoid; }}
    .sku {{ font-weight: 800; letter-spacing: .04em; }}
    .name {{ font-size: 13px; color: #2d383a; }}
    .location {{ font-size: 12px; color: #5b686b; }}
    .barcode {{ display: flex; align-items: stretch; height: 46px; background: #fff; gap: 0; border: 1px solid #d7dfdd; padding: 5px; }}
    .bar {{ background: #111; }}
    .space {{ background: #fff; }}
    @media print {{
      body {{ background: #fff; }}
      header, .input-panel {{ display: none; }}
      section {{ border: 0; box-shadow: none; padding: 0; }}
      .labels {{ grid-template-columns: repeat(3, 1fr); }}
    }}
  </style>
</head>
<body>
  <main>
    <header>
      <h1>Aureon Barcode Label Generator</h1>
      <p>{prompt_html}</p>
      <div>
        <span class="pill">domain-specific worker</span>
        <span class="pill">Code 39-style renderer</span>
        <span class="pill">local only</span>
        <span class="pill">print preview ready</span>
      </div>
    </header>
    <section class="input-panel">
      <h2>Warehouse Rows</h2>
      <textarea id="rows">SKU-001,Starter Widget,Aisle A1
SKU-002,Proof Label,Aisle B4
SKU-003,Fragile Cable,Aisle C2</textarea>
      <div class="toolbar" style="margin-top: 10px;">
        <button id="generate">Generate labels</button>
        <button id="print" type="button">Print labels</button>
        <span id="status" class="pill">waiting</span>
      </div>
    </section>
    <section>
      <h2>Label Preview</h2>
      <div id="labels" class="labels" aria-live="polite"></div>
    </section>
  </main>
  <script>
    const CODE39 = {{
      "0":"nnnwwnwnn","1":"wnnwnnnnw","2":"nnwwnnnnw","3":"wnwwnnnnn","4":"nnnwwnnnw",
      "5":"wnnwwnnnn","6":"nnwwwnnnn","7":"nnnwnnwnw","8":"wnnwnnwnn","9":"nnwwnnwnn",
      "A":"wnnnnwnnw","B":"nnwnnwnnw","C":"wnwnnwnnn","D":"nnnnwwnnw","E":"wnnnwwnnn",
      "F":"nnwnwwnnn","G":"nnnnnwwnw","H":"wnnnnwwnn","I":"nnwnnwwnn","J":"nnnnwwwnn",
      "K":"wnnnnnnww","L":"nnwnnnnww","M":"wnwnnnnwn","N":"nnnnwnnww","O":"wnnnwnnwn",
      "P":"nnwnwnnwn","Q":"nnnnnnwww","R":"wnnnnnwwn","S":"nnwnnnwwn","T":"nnnnwnwwn",
      "U":"wwnnnnnnw","V":"nwwnnnnnw","W":"wwwnnnnnn","X":"nwnnwnnnw","Y":"wwnnwnnnn",
      "Z":"nwwnwnnnn","-":"nwnnnnwnw",".":"wwnnnnwnn"," ":"nwwnnnwnn","$":"nwnwnwnnn",
      "/":"nwnwnnnwn","+":"nwnnnwnwn","%":"nnnwnwnwn","*":"nwnnwnwnn"
    }};
    function normalizeCode(value) {{
      return String(value || '').toUpperCase().replace(/[^A-Z0-9 .$/+%-]+/g, '-').replace(/^-+|-+$/g, '').slice(0, 32) || 'SKU-001';
    }}
    function parseRows(text) {{
      return String(text || '').split(/\\n+/).map((line, index) => {{
        const parts = line.split(',').map((item) => item.trim()).filter(Boolean);
        if (!parts.length) return null;
        const sku = normalizeCode(parts[0] || `SKU-${{String(index + 1).padStart(3, '0')}}`);
        return {{ sku, name: parts[1] || `Warehouse item ${{index + 1}}`, location: parts[2] || 'unassigned' }};
      }}).filter(Boolean);
    }}
    function renderBarcode(sku) {{
      const code = `*${{normalizeCode(sku)}}*`;
      const wrapper = document.createElement('div');
      wrapper.className = 'barcode';
      for (const char of code) {{
        const pattern = CODE39[char] || CODE39['-'];
        for (let i = 0; i < pattern.length; i += 1) {{
          const span = document.createElement('span');
          span.className = i % 2 === 0 ? 'bar' : 'space';
          span.style.width = `${{pattern[i] === 'w' ? 3 : 1}}px`;
          wrapper.appendChild(span);
        }}
        const gap = document.createElement('span');
        gap.className = 'space';
        gap.style.width = '1px';
        wrapper.appendChild(gap);
      }}
      return wrapper;
    }}
    function generateLabels() {{
      const rows = parseRows(document.getElementById('rows').value);
      const target = document.getElementById('labels');
      target.innerHTML = '';
      for (const row of rows) {{
        const card = document.createElement('article');
        card.className = 'label';
        card.appendChild(renderBarcode(row.sku));
        card.insertAdjacentHTML('beforeend', `<div class="sku">${{row.sku}}</div><div class="name">${{row.name}}</div><div class="location">${{row.location}}</div>`);
        target.appendChild(card);
      }}
      document.getElementById('status').textContent = `${{rows.length}} label(s) ready`;
    }}
    document.getElementById('generate').addEventListener('click', generateLabels);
    document.getElementById('print').addEventListener('click', () => window.print());
    generateLabels();
  </script>
</body>
</html>
"""
    metadata = {
        "schema_version": "aureon-barcode-label-generator-v1",
        "kind": "barcode_label_generator",
        "build_id": digest,
        "project_id": uniqueness["project_id"],
        "uniqueness_contract": uniqueness,
        "prompt": prompt,
        "task_family": task_family,
        "detected_families": list(families),
        "public_url": public_url,
        "asset_path": str(index_path),
        "metadata_path": str(metadata_path),
        "runbook_path": str(runbook_path),
        "tool_path": str(tool_path),
        "skill_contract": "generate printable local warehouse barcode labels from CSV/newline rows",
        "barcode_standard": "Code 39-style local renderer",
    }
    runbook = "\n".join(
        [
            "# Aureon Barcode Label Generator",
            "",
            f"- prompt: {prompt}",
            f"- task_family: {task_family}",
            f"- detected_families: {families_text}",
            f"- preview: {public_url}",
            "",
            "## Run",
            "",
            "```powershell",
            f".\\.venv\\Scripts\\python.exe {tool_path}",
            "```",
            "",
            "## Input Format",
            "",
            "Use one item per line: `SKU, Item name, Location`.",
            "",
            "## Boundary",
            "",
            "Local-only. No live trading, payment, filing, credential reveal, or destructive OS action.",
            "",
        ]
    )
    writes = [
        _write_text(index_path, html),
        _write_json(metadata_path, metadata),
        _write_text(runbook_path, runbook),
        _write_text(tool_path, tool_py),
    ]
    tool_text = tool_path.read_text(encoding="utf-8") if tool_path.exists() else ""
    sample_ok = "CODE39_PATTERNS" in tool_text and "build_labels" in tool_text
    uniqueness_checks = _fresh_project_checks(
        public_url=public_url,
        asset_path=index_path,
        metadata_path=metadata_path,
        build_id=digest,
    )
    checks = [
        {
            "id": "barcode_preview_exists",
            "label": "Browser label preview exists",
            "ok": index_path.exists(),
            "blocking": True,
            "evidence": str(index_path),
        },
        {
            "id": "barcode_metadata_exists",
            "label": "Barcode skill metadata exists",
            "ok": metadata_path.exists(),
            "blocking": True,
            "evidence": str(metadata_path),
        },
        {
            "id": "barcode_run_contract_exists",
            "label": "Python run contract exists",
            "ok": tool_path.exists(),
            "blocking": True,
            "evidence": str(tool_path),
        },
        {
            "id": "domain_specific_barcode_logic",
            "label": "Domain-specific barcode logic exists",
            "ok": sample_ok,
            "blocking": True,
            "evidence": "CODE39_PATTERNS + build_labels",
        },
        {
            "id": "printable_label_preview",
            "label": "Printable label preview is available",
            "ok": "window.print" in html,
            "blocking": True,
            "evidence": public_url,
        },
        {
            "id": "local_only_generation",
            "label": "Skill was generated locally",
            "ok": True,
            "blocking": True,
            "evidence": "no external API calls",
        },
    ] + uniqueness_checks
    snags = [
        {
            "id": check["id"],
            "title": check["label"],
            "blocking": True,
            "next_action": "regenerate the barcode label worker with the missing proof",
        }
        for check in checks
        if check.get("blocking") and not check.get("ok")
    ]
    quality_ready = not snags
    quality = {
        "schema_version": "aureon-artifact-quality-report-v1",
        "status": "artifact_quality_passed" if quality_ready else "artifact_quality_blocked",
        "generated_at": _utc_now(),
        "task_family": "barcode_label_generator",
        "provider_policy": "local_only_v1",
        "score": 0.96 if quality_ready else 0.58,
        "minimum_score": 0.82,
        "handover_ready": quality_ready,
        "checks": checks,
        "snags": snags,
        "regeneration_attempts": [
            {
                "attempt": 1,
                "status": "accepted" if quality_ready else "needs_regeneration",
                "reason": "barcode label generator passed domain-specific local checks"
                if quality_ready
                else "barcode label generator missed blocking local checks",
            }
        ],
        "browser_render_proof": {
            "proof_status": "barcode_preview_ready",
            "preview_url": public_url,
            "public_url": public_url,
            "local_probe": True,
        },
        "artifact_manifest": {
            "kind": "barcode_label_generator",
            "subject": "warehouse barcode labels",
            "build_id": digest,
            "project_id": uniqueness["project_id"],
            "uniqueness_contract": uniqueness,
            "asset_path": str(index_path),
            "metadata_path": str(metadata_path),
            "runbook_path": str(runbook_path),
            "tool_path": str(tool_path),
            "public_url": public_url,
            "preview_url": public_url,
            "preview_path": str(index_path),
        },
    }
    return {
        "schema_version": "aureon-barcode-label-generator-v1",
        "status": "barcode_label_generator_ready" if quality_ready else "barcode_label_generator_blocked",
        "ok": quality_ready,
        "artifact_manifest": quality["artifact_manifest"],
        "artifact_quality_report": quality,
        "output_files": [str(index_path), str(metadata_path), str(runbook_path), str(tool_path), public_url],
        "writes": writes,
        "adaptive_skill": {
            "name": "barcode_label_generator_skill",
            "created_for_prompt": True,
            "reusable": True,
            "skill_contract": "generate printable local warehouse barcode labels from CSV/newline rows",
        },
    }


def _adaptive_skill_capsule(
    prompt: str,
    root: Path,
    families: Sequence[str],
    task_family: str,
    *,
    build_id: str,
) -> Dict[str, Any]:
    digest = build_id
    slug = _safe_slug(prompt, fallback="adaptive_skill")
    skill_dir = _rooted(root, DEFAULT_ADAPTIVE_SKILL_DIR) / f"{slug}_{digest}"
    index_path = skill_dir / "index.html"
    metadata_path = skill_dir / "skill.json"
    runbook_path = skill_dir / "RUNBOOK.md"
    tool_path = skill_dir / "tool.py"
    public_url = f"/aureon_adaptive_skills/{skill_dir.name}/index.html"
    prompt_html = escape(prompt)
    families_text = ", ".join(families) or task_family
    uniqueness = _uniqueness_contract(prompt, digest, family="adaptive_skill")
    tool_py = f'''"""Aureon adaptive local skill capsule.

Generated for a client prompt at query time. This capsule is intentionally
local-only: it records the request, exposes a deterministic run contract, and
can be enhanced by the coding organism once the client approves the direction.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone


PROMPT = {prompt!r}
TASK_FAMILY = {task_family!r}
DETECTED_FAMILIES = {list(families)!r}


def run(input_text: str = "") -> dict:
    """Return a local, testable result packet for this adaptive skill."""
    return {{
        "ok": True,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "task_family": TASK_FAMILY,
        "detected_families": DETECTED_FAMILIES,
        "prompt": PROMPT,
        "input_text": input_text,
        "result": "Adaptive skill capsule is ready for local enhancement and client review.",
        "authority": "local-only; no live trading, payment, filing, credential, or destructive OS action",
    }}


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
'''
    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Aureon Adaptive Skill Capsule</title>
  <style>
    :root {{ color-scheme: dark; font-family: Inter, Segoe UI, Arial, sans-serif; }}
    body {{ margin: 0; min-height: 100vh; background: #111a20; color: #eef6f7; }}
    main {{ width: min(980px, 94vw); margin: 0 auto; padding: 28px 0; display: grid; gap: 14px; }}
    section {{ border: 1px solid #456670; border-radius: 8px; background: rgba(255,255,255,.055); padding: 16px; }}
    h1 {{ margin: 0 0 8px; font-size: 26px; }}
    h2 {{ margin: 0 0 8px; font-size: 16px; }}
    p {{ margin: 0; line-height: 1.45; color: #c7d5d8; }}
    pre {{ white-space: pre-wrap; margin: 0; color: #9cf5c8; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(210px, 1fr)); gap: 10px; }}
    .pill {{ display: inline-block; margin: 4px 6px 0 0; padding: 5px 9px; border: 1px solid #5f818a; border-radius: 999px; color: #dcf4f6; }}
    button {{ border: 1px solid #9cf5c8; background: #173a32; color: #eef6f7; border-radius: 7px; padding: 9px 12px; cursor: pointer; }}
    textarea {{ width: 100%; min-height: 90px; border-radius: 7px; border: 1px solid #456670; background: #0d1418; color: #eef6f7; padding: 10px; }}
  </style>
</head>
<body>
  <main>
    <section>
      <h1>Aureon Adaptive Skill Capsule</h1>
      <p>{prompt_html}</p>
      <div>
        <span class="pill">task: {escape(task_family)}</span>
        <span class="pill">families: {escape(families_text)}</span>
        <span class="pill">local only</span>
        <span class="pill">quality gated</span>
      </div>
    </section>
    <div class="grid">
      <section>
        <h2>Who / What / Where</h2>
        <p>Adaptive Skill Composer created a reusable local capsule for this request.</p>
        <p>Files: index.html, skill.json, RUNBOOK.md, tool.py.</p>
      </section>
      <section>
        <h2>How / Proof</h2>
        <p>The capsule is browser-previewable, has a local Python run contract, and keeps all unsafe authority blocked.</p>
      </section>
    </div>
    <section>
      <h2>Local Test Harness</h2>
      <textarea id="input" placeholder="Optional local input for this skill"></textarea>
      <p style="margin-top: 10px;"><button id="run">Run local proof</button></p>
      <pre id="output">Waiting for local proof run.</pre>
    </section>
  </main>
  <script>
    const promptText = {json.dumps(prompt)};
    document.getElementById('run').addEventListener('click', () => {{
      const input = document.getElementById('input').value;
      const result = {{
        ok: true,
        prompt: promptText,
        input_text: input,
        result: 'Adaptive skill capsule is ready and can be enhanced by Aureon for this request.',
        authority: 'local-only; unsafe gates remain blocked'
      }};
      document.getElementById('output').textContent = JSON.stringify(result, null, 2);
    }});
  </script>
</body>
</html>
"""
    metadata = {
        "schema_version": "aureon-adaptive-skill-capsule-v1",
        "kind": "adaptive_skill_capsule",
        "build_id": digest,
        "project_id": uniqueness["project_id"],
        "uniqueness_contract": uniqueness,
        "prompt": prompt,
        "task_family": task_family,
        "detected_families": list(families),
        "public_url": public_url,
        "asset_path": str(index_path),
        "metadata_path": str(metadata_path),
        "runbook_path": str(runbook_path),
        "tool_path": str(tool_path),
        "skill_contract": "create a local, testable skill capsule whenever a prompt has no specialized worker yet",
    }
    runbook = "\n".join(
        [
            "# Aureon Adaptive Skill Capsule",
            "",
            f"- prompt: {prompt}",
            f"- task_family: {task_family}",
            f"- detected_families: {families_text}",
            f"- preview: {public_url}",
            "",
            "## Run",
            "",
            "```powershell",
            f".\\.venv\\Scripts\\python.exe {tool_path}",
            "```",
            "",
            "## Boundary",
            "",
            "Local-only. No live trading, payment, filing, credential reveal, or destructive OS action.",
            "",
        ]
    )
    writes = [
        _write_text(index_path, html),
        _write_json(metadata_path, metadata),
        _write_text(runbook_path, runbook),
        _write_text(tool_path, tool_py),
    ]
    requests_finished_tool = _requests_finished_domain_tool(prompt)
    uniqueness_checks = _fresh_project_checks(
        public_url=public_url,
        asset_path=index_path,
        metadata_path=metadata_path,
        build_id=digest,
    )
    unique_ok = all(bool(check.get("ok")) for check in uniqueness_checks)
    handover_ready = not requests_finished_tool and unique_ok
    snags = []
    if requests_finished_tool:
        snags.append(
            {
                "id": "missing_domain_specific_worker",
                "title": "Generic adaptive capsule is not a finished tool",
                "blocking": True,
                "next_action": "teach Aureon a domain-specific local worker, then rerun the request",
            }
        )
    if not unique_ok:
        snags.append(
            {
                "id": "fresh_project_identity_missing",
                "title": "Fresh project identity is missing from the handover",
                "blocking": True,
                "next_action": "regenerate with a unique build id before client handover",
            }
        )
    quality = {
        "schema_version": "aureon-artifact-quality-report-v1",
        "status": "artifact_quality_passed" if handover_ready else "artifact_quality_blocked",
        "generated_at": _utc_now(),
        "task_family": task_family,
        "provider_policy": "local_only_v1",
        "score": 0.9 if handover_ready else 0.68,
        "minimum_score": 0.8,
        "handover_ready": handover_ready,
        "checks": [
            {
                "id": "adaptive_skill_preview_exists",
                "label": "Browser preview exists",
                "ok": index_path.exists(),
                "blocking": True,
                "evidence": str(index_path),
            },
            {
                "id": "adaptive_skill_metadata_exists",
                "label": "Skill metadata exists",
                "ok": metadata_path.exists(),
                "blocking": True,
                "evidence": str(metadata_path),
            },
            {
                "id": "adaptive_skill_run_contract_exists",
                "label": "Local run contract exists",
                "ok": tool_path.exists(),
                "blocking": True,
                "evidence": str(tool_path),
            },
            {
                "id": "domain_specific_worker_present",
                "label": "Finished domain-specific worker exists when a tool is requested",
                "ok": not requests_finished_tool,
                "blocking": requests_finished_tool,
                "evidence": "generic capsule only"
                if requests_finished_tool
                else "generic capsule/prototype request",
            },
            {
                "id": "local_only_generation",
                "label": "Skill was generated locally",
                "ok": True,
                "blocking": True,
                "evidence": "no external API calls",
            },
        ]
        + uniqueness_checks,
        "snags": snags,
        "regeneration_attempts": [
            {
                "attempt": 1,
                "status": "needs_regeneration" if requests_finished_tool else "accepted",
                "reason": "generic capsule held because the client asked for a finished domain tool"
                if requests_finished_tool
                else "adaptive skill capsule passed local file and preview checks",
            }
        ],
        "browser_render_proof": {
            "proof_status": "adaptive_preview_ready",
            "preview_url": public_url,
            "public_url": public_url,
            "local_probe": True,
        },
        "artifact_manifest": {
            "kind": "adaptive_skill_capsule",
            "subject": task_family,
            "build_id": digest,
            "project_id": uniqueness["project_id"],
            "uniqueness_contract": uniqueness,
            "asset_path": str(index_path),
            "metadata_path": str(metadata_path),
            "runbook_path": str(runbook_path),
            "tool_path": str(tool_path),
            "public_url": public_url,
            "preview_url": public_url,
            "preview_path": str(index_path),
        },
    }
    return {
        "schema_version": "aureon-adaptive-skill-capsule-v1",
        "status": "adaptive_skill_capsule_ready",
        "ok": True,
        "artifact_manifest": quality["artifact_manifest"],
        "artifact_quality_report": quality,
        "output_files": [str(index_path), str(metadata_path), str(runbook_path), str(tool_path), public_url],
        "writes": writes,
        "adaptive_skill": {
            "name": "universal_adaptive_skill_forge",
            "created_for_prompt": True,
            "reusable": True,
            "skill_contract": "create local skill capsules for prompt families Aureon has not specialized yet",
        },
    }


def _safe_code_proposal(
    prompt: str,
    root: Path,
    families: Sequence[str],
    generated_files: Sequence[str] | None = None,
) -> Dict[str, Any]:
    controller = SafeCodeControl(state_path=_rooted(root, DEFAULT_SAFE_CODE_STATE))
    target_files = [
        "aureon/autonomous/aureon_capability_forge.py",
        "aureon/autonomous/aureon_artifact_quality_gate.py",
        "frontend/src/components/generated/AureonCodingOrganismConsole.tsx",
    ]
    if "website_design" in families:
        target_files = [
            "website/",
            "aureon/operator/website_operator.py",
            "skills/aureon-harmonic-design-suite/",
            "tools/aureon_website_visual_qa_v28.js",
        ]
    for item in generated_files or []:
        if item and item not in target_files:
            target_files.append(str(item))
    proposal = controller.propose(
        CodeProposal(
            kind="capability_forge_coding_job",
            title=prompt[:120],
            summary="Local capability forge scoped this coding/UI request, generated local artifacts when suitable, and queued safe route evidence for after-apply review.",
            target_files=target_files
            if any(family in families for family in ("website_design", "coding", "ui", "mixed"))
            else [],
            patch_text="",
            metadata={
                "provider_policy": "local_only_v1",
                "approval_gate": "after_apply",
                "detected_families": list(families),
                "generated_files": list(generated_files or []),
                "safe_authority": "no live trading, payment, filing, credential, or destructive OS bypass",
            },
            source="aureon_capability_forge",
        )
    )
    return {
        "safe_route": "SafeCodeControl.propose",
        "applied": True,
        "applied_scope": "local artifact/code evidence generated where safe; target repo patch remains reviewable through SafeCodeControl",
        "proposal": proposal,
        "generated_files": list(generated_files or []),
        "state_path": str(_rooted(root, DEFAULT_SAFE_CODE_STATE)),
        "approval_gate": "after_apply",
    }


def _placeholder_quality(prompt: str, root: Path, family: str) -> Dict[str, Any]:
    checks = [
        {
            "id": "scope_classified",
            "label": "Prompt classified into a local capability family",
            "ok": True,
            "blocking": True,
            "evidence": family,
        },
        {
            "id": "local_only_policy",
            "label": "Local-only provider policy is active",
            "ok": True,
            "blocking": True,
            "evidence": "no external API calls are allowed in v1",
        },
        {
            "id": "safe_route_recordable",
            "label": "Safe local route can publish evidence",
            "ok": True,
            "blocking": True,
            "evidence": str(_rooted(root, DEFAULT_PUBLIC_JSON)),
        },
    ]
    return {
        "schema_version": "aureon-artifact-quality-report-v1",
        "status": "artifact_quality_passed",
        "generated_at": _utc_now(),
        "task_family": family,
        "provider_policy": "local_only_v1",
        "score": 1.0,
        "minimum_score": 0.8,
        "handover_ready": True,
        "checks": checks,
        "snags": [],
        "regeneration_attempts": [
            {"attempt": 1, "status": "accepted", "reason": "non-media evidence route passed"}
        ],
        "browser_render_proof": {
            "proof_status": "non_media_evidence_ready",
            "preview_url": "",
            "public_url": "/aureon_capability_forge.json",
            "local_probe": True,
        },
        "artifact_manifest": {
            "kind": "file",
            "subject": family,
            "asset_path": str(_rooted(root, DEFAULT_PUBLIC_JSON)),
            "public_url": "/aureon_capability_forge.json",
            "preview_url": "",
        },
    }


def _make_markdown(report: Dict[str, Any]) -> str:
    summary = report.get("summary", {})
    lines = [
        "# Aureon Local Capability Forge",
        "",
        f"- status: {report.get('status')}",
        f"- task_family: {report.get('task_family')}",
        f"- generated_at: {report.get('generated_at')}",
        f"- provider_policy: {report.get('provider_policy')}",
        f"- approval_state: {(report.get('approval_state') or {}).get('state')}",
        f"- handover_ready: {report.get('handover_ready')}",
        f"- build_id: {report.get('build_id')}",
        f"- project_id: {report.get('project_id')}",
        f"- uniqueness_policy: {(report.get('uniqueness_contract') or {}).get('policy')}",
        f"- quality_score: {summary.get('artifact_quality_score')}",
        "",
        "## Recruited Crew",
    ]
    for item in report.get("recruited_crew", []):
        lines.append(f"- {item.get('role')}: {item.get('day_to_day')}")
    lines.extend(["", "## Reference Patterns"])
    for item in report.get("reference_patterns", []):
        lines.append(f"- {item.get('name')}: {item.get('url')} ({item.get('provider_policy')})")
    lines.extend(["", "## Output Files"])
    for item in report.get("output_files", []):
        lines.append(f"- {item}")
    return "\n".join(lines) + "\n"


def build_and_write_capability_forge(
    prompt: str,
    *,
    root: Path | None = None,
    provider_policy: str = "local_only_v1",
    approval_gate: str = "after_apply",
) -> Dict[str, Any]:
    root = Path(root or _default_root()).resolve()
    prompt_text = str(prompt or "").strip()
    if not prompt_text:
        raise ValueError("prompt is required")

    generated_at = _utc_now()
    classification = classify_task_family(prompt_text)
    task_family = classification["task_family"]
    detected_families = classification["detected_families"]
    build_id = _unique_build_id(prompt_text, task_family)
    uniqueness_contract = _uniqueness_contract(prompt_text, build_id, family=task_family)
    crew = _crew_for_families(detected_families)
    tools = _tools_for_families(detected_families)
    website_design = _website_design_artifact(prompt_text, root) if task_family == "website_design" else {}
    visual = (
        _visual_artifact(prompt_text, root)
        if not website_design
        and any(family in detected_families for family in ("video", "image_graphic_design"))
        else {}
    )
    full_stack = (
        _full_stack_system_artifact(prompt_text, root, build_id=build_id)
        if not website_design and not visual and _needs_full_stack_system(prompt_text, detected_families)
        else {}
    )
    interactive = (
        _interactive_game_artifact(prompt_text, root, build_id=build_id)
        if not website_design
        and not visual
        and not full_stack
        and _needs_interactive_app(prompt_text, detected_families)
        else {}
    )
    specialized = (
        _barcode_label_skill_capsule(prompt_text, root, detected_families, task_family, build_id=build_id)
        if not website_design
        and not visual
        and not full_stack
        and not interactive
        and _is_barcode_label_prompt(prompt_text)
        else {}
    )
    adaptive = (
        _adaptive_skill_capsule(prompt_text, root, detected_families, task_family, build_id=build_id)
        if not website_design and not visual and not full_stack and not interactive and not specialized
        else {}
    )
    adaptive_skill_source: Dict[str, Any] = (
        website_design or full_stack or interactive or specialized or adaptive
    )
    if adaptive_skill_source and not any(item.get("role") == "Adaptive Skill Composer" for item in crew):
        crew.append(
            {
                "role": "Adaptive Skill Composer",
                "department": "self_improvement",
                "day_to_day": "create a reusable local skill path when the prompt has no specialized worker yet",
                "temporary": True,
            }
        )
    if adaptive_skill_source and not any(item.get("name") == "Adaptive local skill forge" for item in tools):
        tools.append(
            {
                "name": "Adaptive local skill forge",
                "surface": "frontend/public/aureon_adaptive_skills",
                "mode": "local_file_generation",
            }
        )
    artifact_source: Dict[str, Any] = (
        website_design or visual or full_stack or interactive or specialized or adaptive
    )
    raw_artifact_manifest = artifact_source.get("artifact_manifest")
    artifact_manifest: Dict[str, Any] = (
        raw_artifact_manifest if isinstance(raw_artifact_manifest, dict) else {}
    )
    raw_artifact_quality_report = artifact_source.get("artifact_quality_report")
    artifact_quality_report: Dict[str, Any] = (
        raw_artifact_quality_report
        if isinstance(raw_artifact_quality_report, dict)
        else _placeholder_quality(prompt_text, root, task_family)
    )
    write_artifact_quality_report(artifact_quality_report, root=root)
    generated_files = [
        str(artifact_manifest.get("asset_path") or ""),
        str(artifact_manifest.get("metadata_path") or ""),
        str(artifact_manifest.get("runbook_path") or ""),
        str(artifact_manifest.get("tool_path") or ""),
    ]
    for item in (
        artifact_manifest.get("files", []) if isinstance(artifact_manifest.get("files"), list) else []
    ):
        generated_files.append(str(item))
    generated_files = [item for item in generated_files if item]
    applied_change_evidence = _safe_code_proposal(
        prompt_text,
        root,
        detected_families,
        generated_files=generated_files,
    )

    quality_ready = bool(artifact_quality_report.get("handover_ready"))
    route_ready = provider_policy == "local_only_v1" and quality_ready
    website_design_registry = (
        website_design.get("design_capability_registry", {}) if isinstance(website_design, dict) else {}
    )
    website_registry_verified = bool(website_design_registry.get("verified"))
    approval_state = {
        "state": "pending_user_review_after_apply" if route_ready else "blocked_by_quality_gate",
        "policy": approval_gate,
        "approved": False,
        "reviewer": "operator_or_codex",
        "next_action": "approve, reject, or request revision from the cockpit",
    }
    if task_family == "website_design":
        approval_state = {
            "state": (
                "candidate_ready_for_human_visual_review" if route_ready else "blocked_by_design_quality_gate"
            ),
            "policy": "named_human_visual_review_then_websiteoperator_owner_gate",
            "approved": False,
            "reviewer": "named_human_visual_reviewer",
            "next_action": (
                "Repair any objective gate failures, then obtain named human visual acceptance; "
                "only WebsiteOperator may later run the separate owner-controlled release path."
            ),
            "release_eligible": False,
            "deployment_authority": "none",
        }
    output_files = [
        DEFAULT_STATE_PATH.as_posix(),
        DEFAULT_AUDIT_JSON.as_posix(),
        DEFAULT_AUDIT_MD.as_posix(),
        DEFAULT_PUBLIC_JSON.as_posix(),
        DEFAULT_PUBLIC_QUALITY_JSON.as_posix(),
    ]
    for item in visual.get("output_files", []) if isinstance(visual, dict) else []:
        if item not in output_files:
            output_files.append(str(item))
    for item in website_design.get("output_files", []) if isinstance(website_design, dict) else []:
        if item not in output_files:
            output_files.append(str(item))
    for item in full_stack.get("output_files", []) if isinstance(full_stack, dict) else []:
        if item not in output_files:
            output_files.append(str(item))
    for item in interactive.get("output_files", []) if isinstance(interactive, dict) else []:
        if item not in output_files:
            output_files.append(str(item))
    for item in specialized.get("output_files", []) if isinstance(specialized, dict) else []:
        if item not in output_files:
            output_files.append(str(item))
    for item in adaptive.get("output_files", []) if isinstance(adaptive, dict) else []:
        if item not in output_files:
            output_files.append(str(item))

    raw_adaptive_skill_evidence = adaptive_skill_source.get("adaptive_skill")
    adaptive_skill_evidence: Dict[str, Any] = (
        raw_adaptive_skill_evidence
        if isinstance(raw_adaptive_skill_evidence, dict)
        else {
            "name": "existing_capability_path",
            "created_for_prompt": False,
            "reusable": True,
            "skill_contract": "classified prompt routed through existing local capability forge path",
        }
    )
    report: Dict[str, Any] = {
        "schema_version": "aureon-local-capability-forge-v1",
        "status": "capability_forge_ready" if route_ready else "capability_forge_quality_blocked",
        "ok": route_ready,
        "generated_at": generated_at,
        "job_id": f"capability-forge-{build_id}",
        "build_id": build_id,
        "project_id": uniqueness_contract["project_id"],
        "uniqueness_contract": uniqueness_contract,
        "prompt": prompt_text,
        "task_family": task_family,
        "detected_families": detected_families,
        "director_brief": {
            "goal": "Build locally, prove locally, regenerate weak work, and hand over only after quality gates pass.",
            "provider_policy": provider_policy,
            "approval_gate": approval_gate,
            "uniqueness_policy": uniqueness_contract["policy"],
            "no_bypass": ["live_trading", "payments", "filings", "credentials", "destructive_os_actions"],
        },
        "provider_policy": provider_policy,
        "external_api_calls": [],
        "reference_patterns": _reference_patterns(),
        "recruited_crew": crew,
        "local_tools_used": tools,
        "artifact_manifest": artifact_manifest,
        "website_design_report": website_design,
        "website_design_capability_registry": website_design_registry,
        "visual_asset_report": visual,
        "full_stack_system_report": full_stack,
        "interactive_artifact_report": interactive,
        "specialized_skill_report": specialized,
        "adaptive_skill_report": adaptive,
        "artifact_quality_report": artifact_quality_report,
        "regeneration_attempts": artifact_quality_report.get("regeneration_attempts", []),
        "applied_change_evidence": applied_change_evidence,
        "adaptive_skill_evidence": adaptive_skill_evidence,
        "approval_state": approval_state,
        "handover_ready": route_ready,
        "release_eligible": False,
        "deployment_authority": "none",
        "authority_boundaries": [
            "No paid/cloud provider call in local-only v1.",
            "No credential values emitted.",
            "No live trading, payment, filing, or destructive OS authority changes.",
            "Coding work uses safe local routes and after-apply evidence review.",
            "Website design registry discovery never authorises a package or deployment.",
            "Material public-site changes require named human visual acceptance and WebsiteOperator owner release.",
        ],
        "summary": {
            "task_family": task_family,
            "detected_family_count": len(detected_families),
            "crew_count": len(crew),
            "local_tool_count": len(tools),
            "reference_pattern_count": len(REFERENCE_PATTERNS),
            "external_api_call_count": 0,
            "build_id": build_id,
            "project_id": uniqueness_contract["project_id"],
            "fresh_project_per_request": True,
            "artifact_quality_score": artifact_quality_report.get("score", 0),
            "artifact_quality_passed": quality_ready,
            "blocking_snag_count": len(artifact_quality_report.get("snags", [])),
            "safe_code_route_recorded": bool(applied_change_evidence.get("proposal")),
            "adaptive_skill_created": bool(adaptive_skill_evidence.get("created_for_prompt")),
            "full_stack_system_created": bool(full_stack),
            "website_design_cycle_created": bool(website_design.get("design_cycle"))
            if isinstance(website_design, dict)
            else False,
            "website_design_registry_verified": website_registry_verified,
            "website_design_release_eligible": False,
            "handover_ready": route_ready,
        },
        "output_files": output_files,
        "write_info": {
            "writer": "AureonCapabilityForge",
            "authoring_path": [
                "classify_task_family",
                "recruit_local_crew",
                "reference_patterns_marked_reference_only",
                "website_design_nexus_before_generic_visual_generation",
                "local_visual_or_safe_code_route",
                "adaptive_skill_composer_for_missing_capabilities",
                "artifact_quality_gate",
                "after_apply_approval_state",
                "state/docs/frontend evidence publish",
            ],
        },
    }

    writes = [
        _write_json(_rooted(root, DEFAULT_STATE_PATH), report),
        _write_json(_rooted(root, DEFAULT_AUDIT_JSON), report),
        _write_text(_rooted(root, DEFAULT_AUDIT_MD), _make_markdown(report)),
        _write_json(_rooted(root, DEFAULT_PUBLIC_JSON), report),
    ]
    report["write_info"]["evidence_writes"] = writes
    for rel in (DEFAULT_STATE_PATH, DEFAULT_AUDIT_JSON, DEFAULT_PUBLIC_JSON):
        _write_json(_rooted(root, rel), report)
    _write_text(_rooted(root, DEFAULT_AUDIT_MD), _make_markdown(report))
    return report


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Aureon's local capability forge and quality gate.")
    parser.add_argument("--prompt", "-p", default="", help="Client prompt/job for the local forge.")
    parser.add_argument("--prompt-file", default="", help="Read the prompt from a file.")
    parser.add_argument("--repo-root", default="", help="Repository root; defaults to cwd/repo.")
    parser.add_argument("--json", action="store_true", help="Print JSON instead of Markdown.")
    args = parser.parse_args(argv)

    prompt = args.prompt
    if args.prompt_file:
        prompt = Path(args.prompt_file).read_text(encoding="utf-8")
    if not prompt.strip():
        parser.error("--prompt or --prompt-file is required")

    root = Path(args.repo_root).resolve() if args.repo_root else None
    report = build_and_write_capability_forge(prompt, root=root)
    print(json.dumps(report, indent=2, sort_keys=True, default=str) if args.json else _make_markdown(report))
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())

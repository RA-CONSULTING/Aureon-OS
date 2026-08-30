from __future__ import annotations

import ast
import hashlib
import inspect
import json
import subprocess
import sys
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from aureon.operator import website_runtime_optimisation as runtime_opt

REPO_ROOT = Path(__file__).resolve().parents[1]
MEASUREMENT_SCHEMA_PATH = (
    REPO_ROOT / "docs/research/schemas/AUREON_WEBSITE_RUNTIME_OPTIMISATION_MEASUREMENT_V1.schema.json"
)
PROPOSAL_SCHEMA_PATH = (
    REPO_ROOT / "docs/research/schemas/AUREON_WEBSITE_RUNTIME_OPTIMISATION_PROPOSAL_V1.schema.json"
)


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest().upper()


def _json_sha256(value: object) -> str:
    return _sha256_bytes(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    )


def _write_json(path: Path, value: object) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(value, indent=2, sort_keys=True).encode("utf-8") + b"\n"
    path.write_bytes(payload)
    return _sha256_bytes(payload)


def _summary(rows: list[dict[str, object]]) -> dict[str, object]:
    ordered = sorted(rows, key=lambda row: str(row["path"]))
    digest = _json_sha256(ordered)
    return {
        "tree_sha256": digest,
        "manifest_sha256": digest,
        "file_count": len(ordered),
        "total_bytes": sum(int(row["bytes"]) for row in ordered),
        "files": ordered,
    }


def _manifest(site: Path) -> list[dict[str, object]]:
    return [
        {
            "path": path.relative_to(site).as_posix(),
            "bytes": len(path.read_bytes()),
            "sha256": _sha256_bytes(path.read_bytes()),
        }
        for path in sorted(site.rglob("*"))
        if path.is_file()
    ]


def _with_payload(value: dict[str, Any], *, field: str = "payload_sha256") -> dict[str, Any]:
    result = deepcopy(value)
    result[field] = _json_sha256(result)
    return result


def _fixture(
    tmp_path: Path,
    *,
    now: datetime | None = None,
) -> tuple[Path, Path, str, Path, str, Path, str, datetime]:
    root = tmp_path / "repo"
    site = root / "website"
    site.mkdir(parents=True)
    (site / "index.html").write_bytes(b"<main><h1>Aureon</h1></main>\n")
    (site / "styles.css").write_bytes(b".hero { color: white; }\n" * 12)
    (site / "hero.png").write_bytes(b"P" * 1_000)
    measurement_tool = root / "tools/fixture-measurement.py"
    measurement_tool.parent.mkdir(parents=True)
    measurement_tool.write_text("# fixture measurement declaration\n", encoding="utf-8")
    rows = _manifest(site)
    retained = _summary(rows)
    source = {"root": "website", **retained}
    resolved_now = (now or datetime(2026, 8, 2, 19, 0, tzinfo=UTC)).astimezone(UTC)
    source_authority = {
        "scope": "read-only exact public-runtime source projection proposal",
        "canonical_website_mutation": "none",
        "physical_source_file_removal": "none",
        "staging_authority": "none",
        "candidate_authority": "none",
        "package_authority": "none",
        "release_eligible": False,
        "deployment_authority": "none",
        "credential_access": "none",
        "network_access": "none",
    }
    plan = _with_payload(
        {
            "schema": runtime_opt.SOURCE_PLAN_SCHEMA,
            "generated_at": (resolved_now - timedelta(minutes=5)).isoformat().replace("+00:00", "Z"),
            "run_id": "fixture-source-plan",
            "state": "proposal-only",
            "source_binding": source,
            "closure_binding": {
                "verify_only": True,
                "state": "verified-complete",
                "tool_sha256": runtime_opt.REVIEWED_RELEASE_BUILDER_SHA256,
            },
            "retained_projection": retained,
            "omitted_projection": {
                "manifest_sha256": _json_sha256([]),
                "file_count": 0,
                "total_bytes": 0,
                "files": [],
            },
            "motion_budget_projection": {
                "policy_sha256": runtime_opt.REVIEWED_MOTION_POLICY_SHA256,
            },
            "execution_binding": {
                "implementation_sha256": runtime_opt.REVIEWED_SOURCE_PLANNER_SHA256,
                "reviewed_trusted_launcher_sha256": (runtime_opt.REVIEWED_SOURCE_PLANNER_LAUNCHER_SHA256),
                "reviewed_secure_writer_sha256": runtime_opt.REVIEWED_SECURE_WRITER_SHA256,
                "launcher_attested": True,
            },
            "authority": source_authority,
        }
    )
    plan_path = root / runtime_opt.SOURCE_PLAN_ROOT / "fixture.plan.v1.json"
    plan_sha = _write_json(plan_path, plan)

    contract = json.loads((REPO_ROOT / runtime_opt.ACCEPTANCE_CONTRACT_PATH).read_text(encoding="utf-8"))
    contract["sourceBinding"] = {
        "retainedManifestSha256": retained["manifest_sha256"],
        "retainedFileCount": retained["file_count"],
        "retainedTotalBytes": retained["total_bytes"],
        "htmlDocumentCount": 20,
        "indexableDocumentCount": 17,
        "noindexDocumentCount": 3,
    }
    contract.pop("payloadSha256")
    contract = _with_payload(contract, field="payloadSha256")
    contract_path = root / runtime_opt.ACCEPTANCE_CONTRACT_PATH
    contract_sha = _write_json(contract_path, contract)

    hero = next(row for row in rows if row["path"] == "hero.png")
    evidence = _with_payload(
        {
            "schema": runtime_opt.MEASUREMENT_SCHEMA,
            "measured_at": (resolved_now - timedelta(minutes=2)).isoformat().replace("+00:00", "Z"),
            "run_id": "fixture-measurement",
            "state": "measurement-only",
            "source_plan_binding": {
                "path": plan_path.relative_to(root).as_posix(),
                "file_sha256": plan_sha,
                "payload_sha256": plan["payload_sha256"],
                "plan_run_id": plan["run_id"],
                "source_tree_sha256": source["tree_sha256"],
                "retained_tree_sha256": retained["tree_sha256"],
                "retained_manifest_sha256": retained["manifest_sha256"],
            },
            "acceptance_contract_binding": {
                "path": runtime_opt.ACCEPTANCE_CONTRACT_PATH.as_posix(),
                "file_sha256": contract_sha,
                "payload_sha256": contract["payloadSha256"],
                "contract_id": contract["contractId"],
            },
            "methodology": {
                "id": "fixture-read-only-measurement",
                "tool_path": "tools/fixture-measurement.py",
                "tool_sha256": _sha256_bytes(measurement_tool.read_bytes()),
                "measurement_mode": "read-only-source-ephemeral-derivatives",
                "ephemeral_workspace_only": True,
                "source_masters_preserved": True,
                "network_access": "none",
                "commands_recorded": False,
            },
            "transformations": [
                {
                    "id": "replace-hero-runtime-bytes",
                    "action": "replace-runtime-bytes",
                    "source_path": "hero.png",
                    "source_sha256": hero["sha256"],
                    "source_bytes": hero["bytes"],
                    "projected_runtime_path": "hero.webp",
                    "projected_sha256": "B" * 64,
                    "projected_bytes": 100,
                    "expected_saving_bytes": 900,
                    "measurement_basis": "measured-derivative",
                    "source_master_preserved": True,
                    "reference_mutation_required": True,
                    "execution_state": "not-executed",
                }
            ],
            "authority": dict(runtime_opt.MEASUREMENT_AUTHORITY),
        }
    )
    evidence_path = root / runtime_opt.MEASUREMENT_ROOT / "fixture.measurement.v1.json"
    evidence_sha = _write_json(evidence_path, evidence)
    (root / runtime_opt.PROPOSAL_ROOT).mkdir(parents=True)
    return (
        root,
        plan_path,
        plan_sha,
        evidence_path,
        evidence_sha,
        contract_path,
        contract_sha,
        resolved_now,
    )


def _compile_fixture(tmp_path: Path) -> tuple[dict[str, Any], tuple[Any, ...]]:
    fixture = _fixture(tmp_path)
    root, plan_path, plan_sha, evidence_path, evidence_sha, contract_path, contract_sha, now = fixture
    proposal = runtime_opt._compile_runtime_optimisation_proposal(
        repo_root=root,
        source_plan_path=plan_path,
        source_plan_sha256=plan_sha,
        measurement_path=evidence_path,
        measurement_sha256=evidence_sha,
        acceptance_contract_path=contract_path,
        acceptance_contract_sha256=contract_sha,
        run_id="fixture-runtime-proposal",
        now=now,
        production=False,
    )
    return proposal, fixture


def test_compiler_projects_exact_runtime_but_grants_no_execution_or_release(tmp_path: Path) -> None:
    proposal, _ = _compile_fixture(tmp_path)

    assert proposal["state"] == "proposal-only"
    assert proposal["projected_runtime"]["saving_bytes"] == 900
    assert proposal["projected_runtime"]["total_bytes"] == (proposal["current_runtime"]["total_bytes"] - 900)
    assert proposal["eligible_for_next_local_gate"] is False
    assert proposal["authority"] == runtime_opt.NO_AUTHORITY
    assert proposal["execution_binding"]["commands_executed"] is False
    assert proposal["execution_binding"]["transformations_executed"] is False
    assert all(row["status"] == "blocked-not-run" for row in proposal["acceptance_requirements"])
    runtime_opt.require_runtime_optimisation_proposal(proposal)


def test_source_drift_stale_input_and_exact_binding_tamper_fail_closed(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)
    root, plan_path, plan_sha, evidence_path, evidence_sha, contract_path, contract_sha, now = fixture
    (root / "website" / "index.html").write_text("changed", encoding="utf-8")
    with pytest.raises(runtime_opt.WebsiteRuntimeOptimisationError, match="source changed"):
        runtime_opt._compile_runtime_optimisation_proposal(
            repo_root=root,
            source_plan_path=plan_path,
            source_plan_sha256=plan_sha,
            measurement_path=evidence_path,
            measurement_sha256=evidence_sha,
            acceptance_contract_path=contract_path,
            acceptance_contract_sha256=contract_sha,
            now=now,
            production=False,
        )

    stale_fixture = _fixture(tmp_path / "stale", now=now - timedelta(hours=5))
    (
        stale_root,
        stale_plan,
        stale_plan_sha,
        stale_evidence,
        stale_evidence_sha,
        stale_contract,
        stale_contract_sha,
        _,
    ) = stale_fixture
    with pytest.raises(runtime_opt.WebsiteRuntimeOptimisationError, match="older than four hours"):
        runtime_opt._compile_runtime_optimisation_proposal(
            repo_root=stale_root,
            source_plan_path=stale_plan,
            source_plan_sha256=stale_plan_sha,
            measurement_path=stale_evidence,
            measurement_sha256=stale_evidence_sha,
            acceptance_contract_path=stale_contract,
            acceptance_contract_sha256=stale_contract_sha,
            now=now,
            production=False,
        )

    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    evidence["source_plan_binding"]["file_sha256"] = "F" * 64
    evidence.pop("payload_sha256")
    evidence = _with_payload(evidence)
    tampered_sha = _write_json(evidence_path, evidence)
    with pytest.raises(runtime_opt.WebsiteRuntimeOptimisationError, match="exact source plan"):
        runtime_opt._compile_runtime_optimisation_proposal(
            repo_root=root,
            source_plan_path=plan_path,
            source_plan_sha256=plan_sha,
            measurement_path=evidence_path,
            measurement_sha256=tampered_sha,
            acceptance_contract_path=contract_path,
            acceptance_contract_sha256=contract_sha,
            now=now,
            production=False,
        )


def test_measurement_and_proposal_cannot_claim_execution_or_acceptance(tmp_path: Path) -> None:
    proposal, fixture = _compile_fixture(tmp_path)
    evidence_path = fixture[3]
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    evidence["transformations"][0]["execution_state"] = "executed"
    evidence.pop("payload_sha256")
    evidence = _with_payload(evidence)
    with pytest.raises(runtime_opt.WebsiteRuntimeOptimisationError, match="authority or evidence basis"):
        runtime_opt.require_measurement_evidence(evidence)

    non_string_sha = json.loads(fixture[3].read_text(encoding="utf-8"))
    non_string_sha["transformations"][0]["projected_sha256"] = int("1" * 64)
    non_string_sha.pop("payload_sha256")
    non_string_sha = _with_payload(non_string_sha)
    with pytest.raises(runtime_opt.WebsiteRuntimeOptimisationError, match="projected_sha256"):
        runtime_opt.require_measurement_evidence(non_string_sha)

    boolean_saving = json.loads(fixture[3].read_text(encoding="utf-8"))
    boolean_saving["transformations"][0]["projected_bytes"] = 999
    boolean_saving["transformations"][0]["expected_saving_bytes"] = True
    boolean_saving.pop("payload_sha256")
    boolean_saving = _with_payload(boolean_saving)
    with pytest.raises(runtime_opt.WebsiteRuntimeOptimisationError, match="byte arithmetic"):
        runtime_opt.require_measurement_evidence(boolean_saving)

    oversized = json.loads(fixture[3].read_text(encoding="utf-8"))
    oversized["transformations"][0]["source_bytes"] = runtime_opt.MAX_TREE_BYTES + 1
    oversized["transformations"][0]["projected_bytes"] = 1
    oversized["transformations"][0]["expected_saving_bytes"] = runtime_opt.MAX_TREE_BYTES
    oversized.pop("payload_sha256")
    oversized = _with_payload(oversized)
    with pytest.raises(runtime_opt.WebsiteRuntimeOptimisationError, match="byte arithmetic"):
        runtime_opt.require_measurement_evidence(oversized)

    proposal["acceptance_requirements"][0]["status"] = "passed"
    proposal["acceptance_requirements"][0]["passed"] = True
    proposal.pop("payload_sha256")
    proposal = _with_payload(proposal)
    with pytest.raises(runtime_opt.WebsiteRuntimeOptimisationError, match="fabricates acceptance"):
        runtime_opt.require_runtime_optimisation_proposal(proposal)


def test_reviewed_source_is_standalone_and_launcher_blocks_wrong_pin() -> None:
    module_path = REPO_ROOT / runtime_opt.IMPLEMENTATION_PATH
    launcher_path = REPO_ROOT / runtime_opt.TRUSTED_LAUNCHER_PATH
    module_tree = ast.parse(module_path.read_text(encoding="utf-8"))
    launcher_tree = ast.parse(launcher_path.read_text(encoding="utf-8"))
    for tree in (module_tree, launcher_tree):
        assert not any(
            (isinstance(node, ast.ImportFrom) and str(node.module).startswith("aureon"))
            or (isinstance(node, ast.Import) and any(alias.name.startswith("aureon") for alias in node.names))
            for node in tree.body
        )
    assert _sha256_bytes(launcher_path.read_bytes()) == runtime_opt.REVIEWED_TRUSTED_LAUNCHER_SHA256
    result = subprocess.run(
        [
            sys.executable,
            "-I",
            "-S",
            "-B",
            str(launcher_path),
            "--expected-launcher-sha256",
            "0" * 64,
            "--expected-planner-sha256",
            _sha256_bytes(module_path.read_bytes()),
            "--",
            "--help",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 2
    assert "blocked:" in result.stderr


def test_strict_inputs_and_source_surface_exclude_operational_shortcuts(tmp_path: Path) -> None:
    proposal, fixture = _compile_fixture(tmp_path)
    root = fixture[0]
    assert not list((root / runtime_opt.PROPOSAL_ROOT).glob("*.json"))
    assert proposal["projected_runtime"]["within_fixed_footprint_limits"] is True
    assert proposal["eligible_for_next_local_gate"] is False

    with pytest.raises(runtime_opt.WebsiteRuntimeOptimisationError, match="duplicate JSON keys"):
        runtime_opt._strict_json(b'{"schema":"one","schema":"two"}', label="hostile evidence")

    evidence = json.loads(fixture[3].read_text(encoding="utf-8"))
    evidence["transformations"][0]["action"] = "execute-css-prune"
    evidence.pop("payload_sha256")
    evidence = _with_payload(evidence)
    with pytest.raises(runtime_opt.WebsiteRuntimeOptimisationError, match="authority or evidence basis"):
        runtime_opt.require_measurement_evidence(evidence)

    module_path = REPO_ROOT / runtime_opt.IMPLEMENTATION_PATH
    tree = ast.parse(module_path.read_text(encoding="utf-8"))
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
    assert not imported_roots.intersection({"subprocess", "socket", "urllib", "http", "ftplib", "shutil"})
    function_names = {
        node.name for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    assert not any(
        token in name
        for name in function_names
        for token in ("encode", "minify", "prune", "copy_candidate", "stage", "package", "deploy")
    )


def test_empty_projection_and_inconsistent_footprint_fail_closed(tmp_path: Path) -> None:
    with pytest.raises(runtime_opt.WebsiteRuntimeOptimisationError, match="may not be empty"):
        runtime_opt._project_runtime(
            [{"path": "only.png", "bytes": 10, "sha256": "A" * 64}],
            [
                {
                    "action": "omit-from-runtime-closure",
                    "source_path": "only.png",
                    "source_sha256": "A" * 64,
                    "source_bytes": 10,
                }
            ],
        )

    proposal, _ = _compile_fixture(tmp_path)
    proposal["projected_runtime"]["file_count"] = 0
    proposal.pop("payload_sha256")
    proposal = _with_payload(proposal)
    with pytest.raises(runtime_opt.WebsiteRuntimeOptimisationError, match="bounded non-empty runtime"):
        runtime_opt.require_runtime_optimisation_proposal(proposal)

    empty_transformations, _ = _compile_fixture(tmp_path / "empty-transformations")
    empty_transformations["transformations"] = []
    empty_transformations.pop("payload_sha256")
    empty_transformations = _with_payload(empty_transformations)
    with pytest.raises(runtime_opt.WebsiteRuntimeOptimisationError, match="bounded non-empty list"):
        runtime_opt.require_runtime_optimisation_proposal(empty_transformations)


def test_production_compilation_is_blocked_without_reviewed_measurement_provenance(
    tmp_path: Path,
) -> None:
    fixture = _fixture(tmp_path)
    root, plan_path, plan_sha, evidence_path, evidence_sha, contract_path, contract_sha, now = fixture
    with pytest.raises(
        runtime_opt.WebsiteRuntimeOptimisationError,
        match=runtime_opt.PRODUCTION_MEASUREMENT_PROVENANCE_STATE,
    ):
        runtime_opt._compile_runtime_optimisation_proposal(
            repo_root=root,
            source_plan_path=plan_path,
            source_plan_sha256=plan_sha,
            measurement_path=evidence_path,
            measurement_sha256=evidence_sha,
            acceptance_contract_path=contract_path,
            acceptance_contract_sha256=contract_sha,
            now=now,
            production=True,
        )
    assert not list((root / runtime_opt.PROPOSAL_ROOT).glob("*.json"))


def test_real_contract_and_current_source_plan_are_compatible() -> None:
    plan_path = (
        REPO_ROOT
        / "artifacts/website-operator/source-rationalisations/plans/source-rationalisation-20260802t183347z.plan.v1.json"
    )
    contract_path = REPO_ROOT / runtime_opt.ACCEPTANCE_CONTRACT_PATH
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    generated = datetime.fromisoformat(plan["generated_at"].replace("Z", "+00:00"))
    validated = runtime_opt._require_source_plan(plan, now=generated + timedelta(minutes=30))
    runtime_opt._require_acceptance_contract(contract, retained=validated["retained_projection"])

    weakened = deepcopy(contract)
    weakened["evidenceRequirements"]["browserReportMustBindContractPayloadSha256"] = False
    weakened.pop("payloadSha256")
    weakened = _with_payload(weakened, field="payloadSha256")
    with pytest.raises(runtime_opt.WebsiteRuntimeOptimisationError, match="reviewed immutable policy"):
        runtime_opt._require_acceptance_contract(weakened, retained=validated["retained_projection"])


def test_real_contract_rejects_every_rehashed_leaf_mutation() -> None:
    plan_path = (
        REPO_ROOT
        / "artifacts/website-operator/source-rationalisations/plans/source-rationalisation-20260802t183347z.plan.v1.json"
    )
    contract_path = REPO_ROOT / runtime_opt.ACCEPTANCE_CONTRACT_PATH
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    generated = datetime.fromisoformat(plan["generated_at"].replace("Z", "+00:00"))
    validated = runtime_opt._require_source_plan(plan, now=generated + timedelta(minutes=30))

    def leaf_paths(value: object, prefix: tuple[str | int, ...] = ()) -> list[tuple[str | int, ...]]:
        if isinstance(value, dict):
            rows: list[tuple[str | int, ...]] = []
            for key, nested in value.items():
                if key != "payloadSha256":
                    rows.extend(leaf_paths(nested, (*prefix, key)))
            return rows
        if isinstance(value, list):
            rows = []
            for index, nested in enumerate(value):
                rows.extend(leaf_paths(nested, (*prefix, index)))
            return rows
        return [prefix]

    def altered(value: object) -> object:
        if isinstance(value, bool):
            return not value
        if isinstance(value, int):
            return value + 1
        if isinstance(value, float):
            return value + 0.001
        if isinstance(value, str):
            return value + "-altered"
        raise AssertionError(f"Unsupported contract leaf type: {type(value).__name__}")

    paths = leaf_paths(contract)
    assert len(paths) >= 150
    for path in paths:
        weakened = deepcopy(contract)
        cursor: Any = weakened
        for component in path[:-1]:
            cursor = cursor[component]
        cursor[path[-1]] = altered(cursor[path[-1]])
        weakened.pop("payloadSha256")
        weakened = _with_payload(weakened, field="payloadSha256")
        with pytest.raises(runtime_opt.WebsiteRuntimeOptimisationError):
            runtime_opt._require_acceptance_contract(
                weakened,
                retained=validated["retained_projection"],
            )


def test_reviewed_contract_pin_rejects_rehashed_structural_and_type_mutations() -> None:
    plan_path = (
        REPO_ROOT
        / "artifacts/website-operator/source-rationalisations/plans/source-rationalisation-20260802t183347z.plan.v1.json"
    )
    contract_path = REPO_ROOT / runtime_opt.ACCEPTANCE_CONTRACT_PATH
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    generated = datetime.fromisoformat(plan["generated_at"].replace("Z", "+00:00"))
    retained = runtime_opt._require_source_plan(
        plan,
        now=generated + timedelta(minutes=30),
    )["retained_projection"]

    nested_extra = deepcopy(contract)
    nested_extra["evidenceRequirements"]["unexpectedNestedPolicy"] = True
    nested_missing = deepcopy(contract)
    nested_missing["evidenceRequirements"].pop("manualVisualReviewRequired")
    duplicate_list_member = deepcopy(contract)
    duplicate_list_member["routes"][1] = deepcopy(duplicate_list_member["routes"][0])
    non_object_list_member = deepcopy(contract)
    non_object_list_member["routes"][0] = "not-a-route-object"
    bool_to_int = deepcopy(contract)
    bool_to_int["evidenceRequirements"]["manualVisualReviewRequired"] = 1
    int_to_bool = deepcopy(contract)
    int_to_bool["releaseResultMaxima"]["failures"] = False
    reordered_routes = deepcopy(contract)
    reordered_routes["routes"] = list(reversed(reordered_routes["routes"]))
    altered_blocker_text = deepcopy(contract)
    altered_blocker_text["knownReleaseBlockers"][0]["required"] += " altered"

    cases = {
        "nested extra key": nested_extra,
        "nested missing key": nested_missing,
        "duplicate list member": duplicate_list_member,
        "non-object list member": non_object_list_member,
        "bool replaced by int": bool_to_int,
        "int replaced by bool": int_to_bool,
        "reordered routes": reordered_routes,
        "altered blocker text": altered_blocker_text,
    }
    for label, weakened in cases.items():
        weakened.pop("payloadSha256")
        weakened = _with_payload(weakened, field="payloadSha256")
        with pytest.raises(
            runtime_opt.WebsiteRuntimeOptimisationError,
            match="reviewed immutable policy",
        ) as caught:
            runtime_opt._require_acceptance_contract(weakened, retained=retained)
        assert "reviewed immutable policy" in str(caught.value), label


def test_reviewed_contract_rejects_corrupt_payload_hash_before_pin_check() -> None:
    plan_path = (
        REPO_ROOT
        / "artifacts/website-operator/source-rationalisations/plans/source-rationalisation-20260802t183347z.plan.v1.json"
    )
    contract_path = REPO_ROOT / runtime_opt.ACCEPTANCE_CONTRACT_PATH
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    generated = datetime.fromisoformat(plan["generated_at"].replace("Z", "+00:00"))
    retained = runtime_opt._require_source_plan(
        plan,
        now=generated + timedelta(minutes=30),
    )["retained_projection"]
    contract["payloadSha256"] = "0" * 64

    with pytest.raises(
        runtime_opt.WebsiteRuntimeOptimisationError,
        match="payload hash is invalid",
    ):
        runtime_opt._require_acceptance_contract(contract, retained=retained)


def test_public_and_prewrite_paths_cannot_disable_reviewed_contract_pin(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert "reviewed_payload_required" not in inspect.signature(
        runtime_opt.compile_runtime_optimisation_proposal
    ).parameters
    assert "reviewed_payload_required" not in inspect.signature(
        runtime_opt.write_runtime_optimisation_proposal
    ).parameters
    assert "reviewed_payload_required" not in inspect.signature(
        runtime_opt._revalidate_proposal_inputs
    ).parameters

    fixture = _fixture(tmp_path, now=datetime.now(UTC))
    root, plan_path, plan_sha, evidence_path, evidence_sha, contract_path, contract_sha, now = fixture
    proposal = runtime_opt._compile_runtime_optimisation_proposal(
        repo_root=root,
        source_plan_path=plan_path,
        source_plan_sha256=plan_sha,
        measurement_path=evidence_path,
        measurement_sha256=evidence_sha,
        acceptance_contract_path=contract_path,
        acceptance_contract_sha256=contract_sha,
        now=now,
        production=False,
    )
    fixture_contract = json.loads(contract_path.read_text(encoding="utf-8"))
    assert fixture_contract["payloadSha256"] != runtime_opt.REVIEWED_ACCEPTANCE_CONTRACT_PAYLOAD_SHA256
    with pytest.raises(
        runtime_opt.WebsiteRuntimeOptimisationError,
        match="reviewed immutable policy",
    ):
        runtime_opt._revalidate_proposal_inputs(root, proposal)

    captured: dict[str, Any] = {}

    def capture_public_call(**kwargs: Any) -> dict[str, Any]:
        captured.update(kwargs)
        return {}

    monkeypatch.setattr(runtime_opt, "_compile_runtime_optimisation_proposal", capture_public_call)
    runtime_opt.compile_runtime_optimisation_proposal(
        source_plan_path=Path("plan.json"),
        source_plan_sha256="A" * 64,
        measurement_path=Path("measurement.json"),
        measurement_sha256="B" * 64,
        acceptance_contract_path=Path("contract.json"),
        acceptance_contract_sha256="C" * 64,
    )
    assert captured["production"] is True
    assert "reviewed_payload_required" not in captured


def test_strict_json_schemas_accept_exact_fixtures_and_reject_authority_escalation(
    tmp_path: Path,
) -> None:
    jsonschema = pytest.importorskip("jsonschema")
    proposal, fixture = _compile_fixture(tmp_path)
    measurement = json.loads(fixture[3].read_text(encoding="utf-8"))
    measurement_schema = json.loads(MEASUREMENT_SCHEMA_PATH.read_text(encoding="utf-8"))
    proposal_schema = json.loads(PROPOSAL_SCHEMA_PATH.read_text(encoding="utf-8"))

    jsonschema.Draft202012Validator.check_schema(measurement_schema)
    jsonschema.Draft202012Validator.check_schema(proposal_schema)
    measurement_validator = jsonschema.Draft202012Validator(
        measurement_schema, format_checker=jsonschema.FormatChecker()
    )
    proposal_validator = jsonschema.Draft202012Validator(
        proposal_schema, format_checker=jsonschema.FormatChecker()
    )
    measurement_validator.validate(measurement)
    proposal_validator.validate(proposal)

    escalated_measurement = deepcopy(measurement)
    escalated_measurement["authority"]["network_access"] = "allowed"
    with pytest.raises(jsonschema.ValidationError):
        measurement_validator.validate(escalated_measurement)

    escalated_proposal = deepcopy(proposal)
    escalated_proposal["eligible_for_next_local_gate"] = True
    with pytest.raises(jsonschema.ValidationError):
        proposal_validator.validate(escalated_proposal)

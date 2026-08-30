"""Fail-closed guarantees for external editorial artwork."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
from copy import deepcopy
from datetime import UTC, datetime
from html import escape
from pathlib import Path
from typing import Any

import pytest

import aureon.operator.design_editorial_asset_provenance as provenance_module
from aureon.operator.design_editorial_asset_provenance import (
    AUDIT_SCHEMA,
    DEFAULT_MANIFEST_PATH,
    GLOBAL_NOT_CLEARED_POLICY,
    MANIFEST_SCHEMA,
    NON_AUTHORITATIVE_AUTHORITY,
    RIGHTS_BINDING_PROPOSAL_SCHEMA,
    RIGHTS_BOUNDARY_ACKNOWLEDGEMENT,
    RIGHTS_DECISION_SCHEMA,
    RIGHTS_PREPARATION_AUTHORITY,
    RIGHTS_PREPARATION_REQUEST_SCHEMA,
    RIGHTS_USAGE_SCOPE,
    RUNTIME_VISIBILITY_REQUIRED_STATE,
    SAFE_ROOTS,
    SURFACE_BINDING_SCHEMA,
    WORKER_CAPSULE_SCHEMA,
    DesignEditorialAssetProvenanceError,
    _file_safety,
    _jpeg_probe,
    _webp_probe,
    asset_scope_sha256,
    audit_design_editorial_asset_provenance,
    audit_design_editorial_asset_provenance_file,
    build_editorial_asset_worker_capsule,
    prepare_editorial_asset_rights_decisions,
    verify_editorial_asset_surface_bindings,
    write_editorial_asset_provenance_audit,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = REPO_ROOT / DEFAULT_MANIFEST_PATH
SCHEMA_PATH = REPO_ROOT / "docs/research/schemas/AUREON_DESIGN_EDITORIAL_ASSET_PROVENANCE_V1.schema.json"
DELIVERY_PATH = (
    REPO_ROOT / "docs/research/editorial-assets/SUBSTACK_SHAREABLE_ASSET_DELIVERY_REDACTION_20260730.json"
)
INVENTORY_PATH = REPO_ROOT / "docs/research/editorial-assets/LOCAL_EDITORIAL_ASSET_INVENTORY_20260730.json"
AS_OF = datetime(2026, 7, 30, 0, 35, tzinfo=UTC)
TARGET_ASSET_ID = "substack-feedback-loop"


def _manifest() -> dict[str, Any]:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _approved_temp_repo(tmp_path: Path) -> tuple[Path, dict[str, Any]]:
    root = tmp_path / "repo"
    (root / "aureon").mkdir(parents=True)
    (root / "pyproject.toml").write_text(
        "[project]\nname='editorial-asset-test'\nversion='0.0.0'\n",
        encoding="utf-8",
    )

    manifest = _manifest()
    target = deepcopy(next(item for item in manifest["assets"] if item["asset_id"] == TARGET_ASSET_ID))
    manifest["assets"] = [target]
    manifest["unmapped_assets"] = []

    delivery = json.loads(DELIVERY_PATH.read_text(encoding="utf-8"))
    delivery["items"] = [item for item in delivery["items"] if item["asset_id"] == TARGET_ASSET_ID]
    delivery_target = (
        root / "docs/research/editorial-assets/SUBSTACK_SHAREABLE_ASSET_DELIVERY_REDACTION_20260730.json"
    )
    _write_json(delivery_target, delivery)

    inventory = json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))
    inventory["files"] = [item for item in inventory["files"] if item["asset_id"] == TARGET_ASSET_ID]
    inventory_target = root / "docs/research/editorial-assets/LOCAL_EDITORIAL_ASSET_INVENTORY_20260730.json"
    _write_json(inventory_target, inventory)

    evidence_by_kind = {item["kind"]: item for item in manifest["evidence_snapshots"]}
    evidence_by_kind["redacted-delivery-evidence"]["sha256"] = _sha256(delivery_target)
    evidence_by_kind["redacted-local-asset-inventory"]["sha256"] = _sha256(inventory_target)

    source_and_variants = [target["source_asset"], *target["variants"]]
    for record in source_and_variants:
        source = REPO_ROOT / record["path"]
        destination = root / record["path"]
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)

    decision = {
        "schema": RIGHTS_DECISION_SCHEMA,
        "decision_id": "owner-rights-decision-feedback-loop-test",
        "asset_id": TARGET_ASSET_ID,
        "decision": "approved",
        "decided_by": "Gary Leckey",
        "decided_at": "2026-07-30T00:30:00Z",
        "rights_basis": "copyright-owner-authorisation",
        "usage_scope": RIGHTS_USAGE_SCOPE,
        "asset_scope_sha256": asset_scope_sha256(target),
        "boundary_acknowledgement": RIGHTS_BOUNDARY_ACKNOWLEDGEMENT,
    }
    decision_path = root / "docs/research/editorial-assets/rights-decisions/feedback-loop-approved.json"
    _write_json(decision_path, decision)
    target["rights_decision"] = {
        "state": "approved",
        "named_human_decision": True,
        "decision_evidence": {
            "path": decision_path.relative_to(root).as_posix(),
            "sha256": _sha256(decision_path),
        },
    }
    manifest_path = root / DEFAULT_MANIFEST_PATH
    _write_json(manifest_path, manifest)
    return root, manifest


def _pending_temp_repo_all_assets(
    tmp_path: Path,
) -> tuple[Path, dict[str, Any]]:
    root = tmp_path / "synthetic-six-asset-repo"
    (root / "aureon").mkdir(parents=True)
    (root / "pyproject.toml").write_text(
        "[project]\nname='editorial-rights-preparation-test'\nversion='0.0.0'\n",
        encoding="utf-8",
    )
    manifest = _manifest()
    for evidence_path in (DELIVERY_PATH, INVENTORY_PATH):
        destination = root / evidence_path.relative_to(REPO_ROOT)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(evidence_path, destination)
    for asset in manifest["assets"]:
        for record in [asset["source_asset"], *asset["variants"]]:
            source = REPO_ROOT / record["path"]
            destination = root / record["path"]
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
    _write_json(root / DEFAULT_MANIFEST_PATH, manifest)
    return root, manifest


def _rights_request(
    root: Path,
    asset_ids: list[str],
    **overrides: Any,
) -> dict[str, Any]:
    manifest_path = root / DEFAULT_MANIFEST_PATH
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assets = {str(asset["asset_id"]): asset for asset in manifest["assets"]}
    request: dict[str, Any] = {
        "schema": RIGHTS_PREPARATION_REQUEST_SCHEMA,
        "asset_ids": asset_ids,
        "asset_scopes": {asset_id: asset_scope_sha256(assets[asset_id]) for asset_id in asset_ids},
        "boundary_acknowledgement": RIGHTS_BOUNDARY_ACKNOWLEDGEMENT,
        "decision": "approved",
        "decided_by": "Gary Leckey",
        "decided_at": "2026-07-30T00:30:00Z",
        "manifest_sha256": _sha256(manifest_path),
        "rights_basis": "copyright-owner-authorisation",
        "usage_scope": RIGHTS_USAGE_SCOPE,
    }
    request.update(overrides)
    return request


def _tree_file_hashes(root: Path) -> dict[str, str]:
    return {path.relative_to(root).as_posix(): _sha256(path) for path in root.rglob("*") if path.is_file()}


def _install_bound_target_surfaces(
    root: Path,
    manifest: dict[str, Any],
) -> None:
    asset = manifest["assets"][0]
    variants = {item["role"]: item for item in asset["variants"]}
    placements = {item["destination_path"]: item for item in asset["placements"]}
    html_placement = placements["website/index.html"]
    small_path = str(variants["small"]["path"]).removeprefix("website/")
    large_path = str(variants["large"]["path"]).removeprefix("website/")
    html = f"""<!doctype html>
<html lang="en">
  <body>
    <article data-editorial-surface-id="{escape(html_placement["surface_id"])}">
      <a href="{escape(asset["public_post_url"], quote=True)}">
        <picture>
          <source type="image/webp" srcset="{escape(small_path, quote=True)}">
          <img src="{escape(large_path, quote=True)}"
               alt="{escape(html_placement["alt"], quote=True)}"
               width="{variants["large"]["width"]}"
               height="{variants["large"]["height"]}">
        </picture>
      </a>
      <figcaption>{escape(html_placement["caption"])}</figcaption>
      <p class="editorial-credit">{escape(html_placement["credit"])}</p>
    </article>
  </body>
</html>
"""
    html_path = root / "website/index.html"
    html_path.parent.mkdir(parents=True, exist_ok=True)
    html_path.write_text(html, encoding="utf-8")

    json_placement = placements["website/data/substack-research-index.json"]
    _write_json(
        root / "website/data/substack-research-index.json",
        {
            "items": [
                {
                    "surface_id": json_placement["surface_id"],
                    "url": asset["public_post_url"],
                    "artwork": large_path,
                    "artwork_small": small_path,
                    "artwork_alt": json_placement["alt"],
                    "artwork_caption": json_placement["caption"],
                    "artwork_credit": json_placement["credit"],
                }
            ]
        },
    )


def test_canonical_manifest_fails_closed_on_current_unapproved_use() -> None:
    result = audit_design_editorial_asset_provenance_file(
        MANIFEST_PATH,
        repo_root=REPO_ROOT,
        as_of=AS_OF,
    )

    assert result["schema"] == AUDIT_SCHEMA
    assert result["state"] == "blocked-unapproved-current-use"
    assert result["passed"] is False
    assert result["receipt_authority"] is False
    assert result["release_eligible"] is False
    assert result["package_authority"] == "none"
    assert result["deployment_authority"] == "none"
    assert result["authority"] == NON_AUTHORITATIVE_AUTHORITY
    assert result["global_artwork_policy"] == GLOBAL_NOT_CLEARED_POLICY
    assert result["summary"] == {
        "mapped_asset_count": 6,
        "unmapped_asset_count": 1,
        "currently_referenced_asset_count": 6,
        "unapproved_current_asset_count": 6,
        "current_copy_drift_asset_count": 6,
        "named_human_decision_count": 0,
        "candidate_use_ready_count": 0,
        "asset_capsule_count": 0,
        "route_asset_capsule_count": 0,
    }
    assert result["asset_capsules"] == []
    assert result["route_asset_capsules"] == []
    assert len(result["asset_capsules_sha256"]) == 64
    assert len(result["route_asset_capsules_sha256"]) == 64
    assert result["public_coverage"]["all_current_references_authorised"] is False
    assert result["public_coverage"]["all_current_copy_bindings_closed"] is False
    assert len(result["public_coverage"]["coverage_sha256"]) == 64
    assert all("path" not in item for item in result["evidence_snapshots"])
    assert all("path" not in item["source_asset"] for item in result["assets"])
    assert all("path" not in item["source_asset"] for item in result["unmapped_assets"])
    assert all(item["candidate_use_ready"] is False for item in result["assets"])
    assert all("currently-referenced-without-rights" in item["blocking_codes"] for item in result["assets"])
    assert all(
        item["source_asset"]["integrity_matches"] is True
        and len(item["variants"]) == 2
        and all(variant["integrity_matches"] for variant in item["variants"])
        for item in result["assets"]
    )
    assert result["unmapped_assets"] == [
        {
            **result["unmapped_assets"][0],
            "asset_id": "unmapped-bounded-systems",
            "mapping_state": "unmapped",
            "rights_state": "not-authorised",
            "reason_code": "no-direct-public-post-or-variant-binding",
            "candidate_use_ready": False,
        }
    ]


def test_all_current_webp_variants_and_routes_are_explicitly_reported() -> None:
    result = audit_design_editorial_asset_provenance_file(
        repo_root=REPO_ROOT,
        as_of=AS_OF,
    )

    variant_paths = {variant["path"] for asset in result["assets"] for variant in asset["variants"]}
    disk_paths = {
        path.relative_to(REPO_ROOT).as_posix()
        for path in (REPO_ROOT / "website/assets/images/research/substack").glob("*.webp")
    }
    assert variant_paths == disk_paths
    assert len(variant_paths) == 12
    routes = {asset["asset_id"]: asset["current_reference_routes"] for asset in result["assets"]}
    assert routes["substack-falsifiability"] == [
        "/",
        "/research/",
        "/research/journal/",
    ]
    assert routes["substack-research-index"] == ["/research/journal/"]
    assert all(routes[asset_id] for asset_id in routes)


def test_shareable_assets_delivery_has_no_rights_effect() -> None:
    manifest = _manifest()
    result = audit_design_editorial_asset_provenance_file(
        repo_root=REPO_ROOT,
        as_of=AS_OF,
    )

    assert all(
        item["delivery_evidence"]["rights_effect"] == "none"
        and item["delivery_evidence"]["binding_matches"] is True
        for item in result["assets"]
    )
    assert all(
        item["rights_decision"]
        == {
            "state": "pending",
            "named_human_decision": False,
            "decision_evidence": None,
        }
        for item in manifest["assets"]
    )
    assert result["summary"]["named_human_decision_count"] == 0
    assert result["summary"]["candidate_use_ready_count"] == 0


def test_private_source_register_is_never_read(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original = Path.read_text

    def guarded_read_text(
        path: Path,
        *args: Any,
        **kwargs: Any,
    ) -> str:
        if path.name.casefold() == "source-register.md":
            raise AssertionError("private source register must not be read")
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", guarded_read_text)
    result = audit_design_editorial_asset_provenance_file(
        repo_root=REPO_ROOT,
        as_of=AS_OF,
    )
    assert result["state"] == "blocked-unapproved-current-use"
    serialised = json.dumps(result).casefold()
    assert "source-register.md" not in serialised
    assert "message_id" not in serialised
    assert "thread_id" not in serialised
    assert ".env" not in serialised
    assert "docs/research/editorial-assets" not in serialised


def test_pending_unmapped_and_unknown_assets_emit_no_worker_capsule() -> None:
    for asset_id in (
        TARGET_ASSET_ID,
        "unmapped-bounded-systems",
        "unknown-editorial-asset",
    ):
        with pytest.raises(
            DesignEditorialAssetProvenanceError,
            match="not candidate-use-ready|Unknown mapped",
        ):
            build_editorial_asset_worker_capsule(
                asset_id,
                repo_root=REPO_ROOT,
                as_of=AS_OF,
            )


def test_named_human_rights_decision_emits_one_privacy_safe_capsule(
    tmp_path: Path,
) -> None:
    root, _ = _approved_temp_repo(tmp_path)
    audit = audit_design_editorial_asset_provenance_file(
        repo_root=root,
        as_of=AS_OF,
    )
    target = audit["assets"][0]

    assert audit["state"] == "candidate-use-ready"
    assert audit["passed"] is True
    assert target["candidate_use_ready"] is True
    assert target["rights"]["named_human_decision"] is True
    assert target["rights"]["decision_valid"] is True

    capsule = build_editorial_asset_worker_capsule(
        TARGET_ASSET_ID,
        repo_root=root,
        as_of=AS_OF,
    )
    assert capsule["schema"] == WORKER_CAPSULE_SCHEMA
    assert capsule["asset_id"] == TARGET_ASSET_ID
    assert capsule["rights"]["state"] == "approved"
    assert len(capsule["website_variants"]) == 2
    assert capsule["representation"]["classification"] == "concept-lab-not-facility"
    assert capsule["authority"]["source_content_available"] is False
    assert capsule["authority"]["source_paths_available"] is False
    assert capsule["authority"]["rights_evidence_available"] is False
    assert capsule["authority"]["release_eligible"] is False
    assert capsule["authority"]["package_authority"] == "none"
    assert capsule["authority"]["deployment_authority"] == "none"
    assert len(capsule["asset_capsule_sha256"]) == 64
    assert "decision_id" not in capsule["rights"]
    assert audit["asset_capsules"] == [capsule]
    assert len(audit["route_asset_capsules"]) == len(capsule["placements"])
    assert all(
        item["asset_capsule_sha256"] == capsule["asset_capsule_sha256"]
        for item in audit["route_asset_capsules"]
    )
    serialised = json.dumps(capsule).casefold()
    assert "gary leckey" not in serialised
    assert "decided_by" not in serialised
    assert "decision_evidence" not in serialised
    assert "source_asset" not in serialised
    assert "source-register" not in serialised


def test_prepare_six_assets_writes_separate_decisions_and_proposal_only(
    tmp_path: Path,
) -> None:
    root, manifest = _pending_temp_repo_all_assets(tmp_path)
    manifest_path = root / DEFAULT_MANIFEST_PATH
    manifest_before = manifest_path.read_bytes()
    repo_files_before = _tree_file_hashes(root)
    website_before = _tree_file_hashes(root / "website")
    asset_ids = [str(asset["asset_id"]) for asset in manifest["assets"]]
    request = _rights_request(root, asset_ids)

    proposal = prepare_editorial_asset_rights_decisions(
        request,
        repo_root=root,
        as_of=AS_OF,
    )

    assert proposal["schema"] == RIGHTS_BINDING_PROPOSAL_SCHEMA
    assert proposal["state"] == "manifest-binding-proposal-only"
    assert proposal["summary"] == {
        "requested_asset_count": 6,
        "separate_decision_file_count": 6,
        "proposed_manifest_binding_count": 6,
        "canonical_manifest_mutation_count": 0,
    }
    assert proposal["authority"] == RIGHTS_PREPARATION_AUTHORITY
    assert proposal["candidate_use_rights_ready"] is False
    assert proposal["release_eligible"] is False
    assert proposal["package_authority"] == "none"
    assert proposal["deployment_authority"] == "none"
    assert proposal["manifest"]["global_artwork_policy"] == "not-cleared"
    assert proposal["manifest"]["mutated"] is False
    assert proposal["manifest"]["sha256"] == request["manifest_sha256"]
    assert proposal["request"]["manifest_sha256"] == request["manifest_sha256"]
    assert proposal["request"]["usage_scope"] == request["usage_scope"]
    assert proposal["request"]["boundary_acknowledgement"] == request["boundary_acknowledgement"]
    assert proposal["privacy"]["reviewer_identity_in_proposal"] == "excluded"
    assert "decided_by" not in json.dumps(proposal)
    assert len(proposal["proposed_bindings"]) == 6
    assert (
        len(
            {
                binding["rights_decision"]["decision_evidence"]["path"]
                for binding in proposal["proposed_bindings"]
            }
        )
        == 6
    )

    decision_root = root / SAFE_ROOTS["rights_decisions"]
    decision_paths = sorted(decision_root.glob("*.json"))
    assert len(decision_paths) == 6
    decisions = [json.loads(path.read_text(encoding="utf-8")) for path in decision_paths]
    assert {decision["asset_id"] for decision in decisions} == set(asset_ids)
    assert all(
        decision["schema"] == RIGHTS_DECISION_SCHEMA
        and decision["decision"] == "approved"
        and decision["decided_by"] == "Gary Leckey"
        and decision["rights_basis"] == "copyright-owner-authorisation"
        and decision["usage_scope"] == request["usage_scope"]
        and decision["boundary_acknowledgement"] == request["boundary_acknowledgement"]
        for decision in decisions
    )
    expected_scopes = {str(asset["asset_id"]): asset_scope_sha256(asset) for asset in manifest["assets"]}
    assert request["asset_scopes"] == expected_scopes
    assert {
        str(decision["asset_id"]): str(decision["asset_scope_sha256"]) for decision in decisions
    } == expected_scopes
    assert all(path.stat().st_nlink == 1 and not path.is_symlink() for path in decision_paths)

    proposal_path = root / proposal["proposal_path"]
    assert json.loads(proposal_path.read_text(encoding="utf-8")) == proposal
    assert proposal_path.stat().st_nlink == 1
    assert manifest_path.read_bytes() == manifest_before
    assert _tree_file_hashes(root / "website") == website_before
    repo_files_after = _tree_file_hashes(root)
    expected_new_files = {path.relative_to(root).as_posix() for path in decision_paths} | {
        proposal_path.relative_to(root).as_posix()
    }
    assert set(repo_files_after) - set(repo_files_before) == expected_new_files
    assert {path: repo_files_after[path] for path in repo_files_before} == repo_files_before

    current_audit = audit_design_editorial_asset_provenance_file(
        repo_root=root,
        as_of=AS_OF,
    )
    assert current_audit["global_artwork_policy"] == GLOBAL_NOT_CLEARED_POLICY
    assert current_audit["summary"]["named_human_decision_count"] == 0
    assert current_audit["summary"]["candidate_use_ready_count"] == 0

    # Test-only replay proves that every proposed binding is independently
    # usable; the preparation function itself did not perform this mutation.
    replay_manifest = json.loads(manifest_before)
    replay_assets = {str(asset["asset_id"]): asset for asset in replay_manifest["assets"]}
    for binding in proposal["proposed_bindings"]:
        replay_assets[str(binding["asset_id"])]["rights_decision"] = binding["rights_decision"]
    _write_json(manifest_path, replay_manifest)
    replay_audit = audit_design_editorial_asset_provenance_file(
        repo_root=root,
        as_of=AS_OF,
    )
    assert replay_audit["summary"]["named_human_decision_count"] == 6
    assert replay_audit["summary"]["candidate_use_ready_count"] == 6


def test_rights_preparation_batch_rolls_back_every_output_on_commit_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, manifest = _pending_temp_repo_all_assets(tmp_path)
    manifest_path = root / DEFAULT_MANIFEST_PATH
    manifest_before = manifest_path.read_bytes()
    asset_ids = [str(asset["asset_id"]) for asset in manifest["assets"]]
    original_link = provenance_module._exclusive_link
    calls = 0

    def fail_third_link(staged: Path, target: Path) -> None:
        nonlocal calls
        calls += 1
        if calls == 3:
            raise OSError("synthetic atomic-link failure")
        original_link(staged, target)

    monkeypatch.setattr(provenance_module, "_exclusive_link", fail_third_link)

    with pytest.raises(
        DesignEditorialAssetProvenanceError,
        match="atomically retain",
    ):
        prepare_editorial_asset_rights_decisions(
            _rights_request(root, asset_ids),
            repo_root=root,
            as_of=AS_OF,
        )

    decision_root = root / SAFE_ROOTS["rights_decisions"]
    proposal_root = root / provenance_module.DEFAULT_RIGHTS_PROPOSAL_ROOT
    assert not list(decision_root.glob("*.json"))
    assert not list(proposal_root.glob("*.json"))
    assert not list(root.rglob("*.tmp"))
    assert manifest_path.read_bytes() == manifest_before


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ("duplicate", "must be unique"),
        ("partial-id", "Unknown exact mapped"),
        ("unknown", "Unknown exact mapped"),
        ("reviewer", "controlled owner-reviewer allowlist"),
        ("basis", "controlled rights basis"),
        ("future", "future-dated"),
        ("extra", "exact contract"),
        ("implicit-decision", "explicitly say approved or rejected"),
        ("stale-manifest", "manifest SHA-256 does not match"),
        ("missing-scope", "same exact key set"),
        ("extra-scope", "same exact key set"),
        ("mismatched-scope", "asset_scopes do not match"),
        ("lowercase-scope", "uppercase SHA-256"),
        ("wrong-usage", "exact usage scope"),
        ("wrong-boundary", "exact controlled representation boundary"),
    ],
)
def test_rights_preparation_rejects_adversarial_requests(
    tmp_path: Path,
    mutation: str,
    message: str,
) -> None:
    root, manifest = _pending_temp_repo_all_assets(tmp_path)
    asset_ids = [str(asset["asset_id"]) for asset in manifest["assets"]]
    request = _rights_request(root, asset_ids)
    if mutation == "duplicate":
        request["asset_ids"] = [asset_ids[0], asset_ids[0]]
    elif mutation == "partial-id":
        partial = asset_ids[0].removesuffix("evidence")
        request["asset_ids"] = [partial]
        request["asset_scopes"] = {partial: "A" * 64}
    elif mutation == "unknown":
        unknown = "unknown-editorial-asset"
        request["asset_ids"] = [unknown]
        request["asset_scopes"] = {unknown: "A" * 64}
    elif mutation == "reviewer":
        request["decided_by"] = "Mickey Mouse"
    elif mutation == "basis":
        request["rights_basis"] = "delivered-by-email"
    elif mutation == "future":
        request["decided_at"] = "2026-07-30T00:36:00Z"
    elif mutation == "extra":
        request["free_form_reason"] = "looks fine to me"
    elif mutation == "implicit-decision":
        request["decision"] = "pending"
    elif mutation == "stale-manifest":
        request["manifest_sha256"] = "0" * 64
    elif mutation == "missing-scope":
        del request["asset_scopes"][asset_ids[0]]
    elif mutation == "extra-scope":
        request["asset_scopes"]["unknown-editorial-asset"] = "A" * 64
    elif mutation == "mismatched-scope":
        request["asset_scopes"][asset_ids[0]] = "0" * 64
    elif mutation == "lowercase-scope":
        request["asset_scopes"][asset_ids[0]] = request["asset_scopes"][asset_ids[0]].lower()
    elif mutation == "wrong-usage":
        request["usage_scope"] = "all-public-routes"
    else:
        request["boundary_acknowledgement"] = "artwork received"

    with pytest.raises(DesignEditorialAssetProvenanceError, match=message):
        prepare_editorial_asset_rights_decisions(
            request,
            repo_root=root,
            as_of=AS_OF,
        )

    decision_root = root / SAFE_ROOTS["rights_decisions"]
    proposal_root = root / provenance_module.DEFAULT_RIGHTS_PROPOSAL_ROOT
    assert not decision_root.exists()
    assert not proposal_root.exists()


def test_rights_preparation_rejects_scope_drift_before_commit_and_rolls_back(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, manifest = _pending_temp_repo_all_assets(tmp_path)
    asset_ids = [str(asset["asset_id"]) for asset in manifest["assets"]]
    original_recheck = provenance_module._assert_rights_preparation_snapshot_current
    drifted = False

    def drift_then_recheck(
        *,
        root: Path,
        manifest_path: Path,
        snapshot: dict[str, Any],
    ) -> None:
        nonlocal drifted
        if not drifted:
            drifted = True
            changed = json.loads(manifest_path.read_text(encoding="utf-8"))
            changed["assets"][0]["placements"][0]["caption"] += " Scope changed after owner decision."
            _write_json(manifest_path, changed)
        original_recheck(
            root=root,
            manifest_path=manifest_path,
            snapshot=snapshot,
        )

    monkeypatch.setattr(
        provenance_module,
        "_assert_rights_preparation_snapshot_current",
        drift_then_recheck,
    )

    with pytest.raises(
        DesignEditorialAssetProvenanceError,
        match="manifest drifted|scope drifted",
    ):
        prepare_editorial_asset_rights_decisions(
            _rights_request(root, asset_ids),
            repo_root=root,
            as_of=AS_OF,
        )

    assert not list((root / SAFE_ROOTS["rights_decisions"]).glob("*.json"))
    assert not list((root / provenance_module.DEFAULT_RIGHTS_PROPOSAL_ROOT).glob("*.json"))


def test_rights_preparation_is_exclusive_and_rejects_existing_outputs(
    tmp_path: Path,
) -> None:
    root, manifest = _pending_temp_repo_all_assets(tmp_path)
    asset_ids = [str(asset["asset_id"]) for asset in manifest["assets"]]
    request = _rights_request(root, asset_ids)
    first = prepare_editorial_asset_rights_decisions(
        request,
        repo_root=root,
        as_of=AS_OF,
    )
    before = _tree_file_hashes(root)

    with pytest.raises(
        DesignEditorialAssetProvenanceError,
        match="already exists",
    ):
        prepare_editorial_asset_rights_decisions(
            request,
            repo_root=root,
            as_of=AS_OF,
        )

    assert _tree_file_hashes(root) == before
    assert len(first["proposed_bindings"]) == 6


def test_rights_preparation_cli_reads_only_a_controlled_request_file(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root, manifest = _pending_temp_repo_all_assets(tmp_path)
    asset_ids = [str(asset["asset_id"]) for asset in manifest["assets"]]
    request_path = root / provenance_module.DEFAULT_RIGHTS_REQUEST_ROOT / "synthetic-six-asset-request.json"
    _write_json(request_path, _rights_request(root, asset_ids))

    result = provenance_module.main(
        [
            "--repo-root",
            str(root),
            "--prepare-rights-request",
            str(request_path),
        ]
    )

    assert result == 0
    proposal = json.loads(capsys.readouterr().out)
    assert proposal["schema"] == RIGHTS_BINDING_PROPOSAL_SCHEMA
    assert proposal["summary"]["separate_decision_file_count"] == 6
    assert (root / proposal["proposal_path"]).is_file()

    duplicate_key_path = request_path.with_name("duplicate-key-request.json")
    duplicate_key_path.write_text(
        '{"schema":"first","schema":"second"}\n',
        encoding="utf-8",
    )
    with pytest.raises(
        DesignEditorialAssetProvenanceError,
        match="without duplicate object keys",
    ):
        provenance_module._read_rights_preparation_request_file(
            duplicate_key_path,
            root=root,
        )


def test_rights_preparation_rejects_hardlinked_manifest_and_reparse_output(
    tmp_path: Path,
) -> None:
    hardlink_root, hardlink_manifest = _pending_temp_repo_all_assets(tmp_path / "hardlink")
    hardlink_path = hardlink_root / DEFAULT_MANIFEST_PATH
    alias = hardlink_path.with_name("manifest-hardlink-alias.json")
    try:
        os.link(hardlink_path, alias)
    except (OSError, NotImplementedError) as exc:
        pytest.skip(f"Hardlink creation is unavailable: {exc}")
    with pytest.raises(
        DesignEditorialAssetProvenanceError,
        match="single-link",
    ):
        prepare_editorial_asset_rights_decisions(
            _rights_request(
                hardlink_root,
                [str(asset["asset_id"]) for asset in hardlink_manifest["assets"]],
            ),
            repo_root=hardlink_root,
            as_of=AS_OF,
        )

    reparse_root, reparse_manifest = _pending_temp_repo_all_assets(tmp_path / "reparse")
    rights_parent = reparse_root / "docs/research/editorial-assets"
    rights_parent.mkdir(parents=True, exist_ok=True)
    outside = tmp_path / "outside-rights"
    outside.mkdir()
    rights_root = rights_parent / "rights-decisions"
    try:
        os.symlink(outside, rights_root, target_is_directory=True)
    except (OSError, NotImplementedError):
        return
    with pytest.raises(
        DesignEditorialAssetProvenanceError,
        match="link|reparse",
    ):
        prepare_editorial_asset_rights_decisions(
            _rights_request(
                reparse_root,
                [str(asset["asset_id"]) for asset in reparse_manifest["assets"]],
            ),
            repo_root=reparse_root,
            as_of=AS_OF,
        )


def test_structural_surface_bindings_are_exact_deterministic_and_public_safe(
    tmp_path: Path,
) -> None:
    root, manifest = _approved_temp_repo(tmp_path)
    _install_bound_target_surfaces(root, manifest)

    first = verify_editorial_asset_surface_bindings(
        manifest["assets"][0],
        repo_root=root,
    )
    second = verify_editorial_asset_surface_bindings(
        manifest["assets"][0],
        repo_root=root,
    )
    audit = audit_design_editorial_asset_provenance_file(
        repo_root=root,
        as_of=AS_OF,
    )

    assert first == second
    assert first["schema"] == SURFACE_BINDING_SCHEMA
    assert first["website_projection"] == "canonical"
    assert first["computed_visibility_state"] == RUNTIME_VISIBILITY_REQUIRED_STATE
    assert first["runtime_visibility_required"] is True
    assert len(first["surface_bindings_sha256"]) == 64
    assert first["summary"] == {
        "declared_placement_count": 2,
        "referenced_placement_count": 2,
        "bound_placement_count": 2,
        "drift_placement_count": 0,
        "runtime_visibility_required_count": 2,
    }
    assert all(
        item["state"] == "bound"
        and item["binding_complete"] is True
        and item["finding_codes"] == []
        and item["computed_visibility_state"] == RUNTIME_VISIBILITY_REQUIRED_STATE
        and item["runtime_visibility_required"] is True
        and len(item["expected_binding_sha256"]) == 64
        and len(item["observation_sha256"]) == 64
        and len(item["surface_binding_sha256"]) == 64
        for item in first["placements"]
    )
    assert audit["state"] == "candidate-use-ready"
    assert audit["passed"] is True
    assert audit["summary"]["currently_referenced_asset_count"] == 1
    assert audit["summary"]["current_copy_drift_asset_count"] == 0
    assert audit["surface_bindings"] == [first]
    assert len(audit["surface_bindings_sha256"]) == 64
    assert audit["assets"][0]["surface_binding"] == first

    serialised = json.dumps(first)
    target = manifest["assets"][0]
    assert target["public_post_url"] not in serialised
    assert target["placements"][0]["alt"] not in serialised
    assert target["placements"][0]["caption"] not in serialised
    assert target["placements"][0]["credit"] not in serialised
    assert "rights-decisions" not in serialised
    assert "source_asset" not in serialised


def _assert_surface_binding_rejects_browser_native_hidden_ancestor(
    tmp_path: Path,
    opening: str,
    closing: str,
) -> None:
    root, manifest = _approved_temp_repo(tmp_path)
    _install_bound_target_surfaces(root, manifest)
    path = root / "website/index.html"
    text = path.read_text(encoding="utf-8")
    path.write_text(
        text.replace("<article ", f"{opening}<article ", 1).replace(
            "</article>",
            f"</article>{closing}",
            1,
        ),
        encoding="utf-8",
    )

    binding = verify_editorial_asset_surface_bindings(
        manifest["assets"][0],
        repo_root=root,
    )
    html_row = next(
        item for item in binding["placements"] if item["destination_path"] == "website/index.html"
    )
    audit = audit_design_editorial_asset_provenance_file(
        repo_root=root,
        as_of=AS_OF,
    )

    assert html_row["state"] == "drift"
    assert html_row["binding_complete"] is False
    assert "hidden-surface-binding" in html_row["finding_codes"]
    assert html_row["computed_visibility_state"] == RUNTIME_VISIBILITY_REQUIRED_STATE
    assert html_row["runtime_visibility_required"] is True
    assert audit["passed"] is False
    assert audit["summary"]["current_copy_drift_asset_count"] == 1


def test_surface_binding_rejects_closed_dialog_ancestor(tmp_path: Path) -> None:
    _assert_surface_binding_rejects_browser_native_hidden_ancestor(
        tmp_path,
        "<dialog>",
        "</dialog>",
    )


def test_surface_binding_rejects_inert_ancestor(tmp_path: Path) -> None:
    _assert_surface_binding_rejects_browser_native_hidden_ancestor(
        tmp_path,
        "<section inert>",
        "</section>",
    )


def test_surface_binding_rejects_closed_details_content(tmp_path: Path) -> None:
    _assert_surface_binding_rejects_browser_native_hidden_ancestor(
        tmp_path,
        "<details><summary>Artwork details</summary>",
        "</details>",
    )


def test_surface_binding_never_treats_static_structure_as_computed_css_visibility(
    tmp_path: Path,
) -> None:
    root, manifest = _approved_temp_repo(tmp_path)
    _install_bound_target_surfaces(root, manifest)
    path = root / "website/index.html"
    text = path.read_text(encoding="utf-8")
    path.write_text(
        text.replace(
            "<body>",
            "<head><style>.css-hidden { display: none; }</style></head><body>",
            1,
        ).replace(
            "<article ",
            '<article class="css-hidden" ',
            1,
        ),
        encoding="utf-8",
    )

    binding = verify_editorial_asset_surface_bindings(
        manifest["assets"][0],
        repo_root=root,
    )
    html_row = next(
        item for item in binding["placements"] if item["destination_path"] == "website/index.html"
    )

    # The source structure remains exact, but the receipt must never claim
    # that computed CSS visibility was proven without a browser.
    assert html_row["state"] == "bound"
    assert html_row["binding_complete"] is True
    assert html_row["finding_codes"] == []
    assert html_row["computed_visibility_state"] == RUNTIME_VISIBILITY_REQUIRED_STATE
    assert html_row["runtime_visibility_required"] is True


def test_surface_binding_can_replay_one_controlled_candidate_website(
    tmp_path: Path,
) -> None:
    root, manifest = _approved_temp_repo(tmp_path)
    _install_bound_target_surfaces(root, manifest)
    candidate_site = root / "artifacts/website-candidates/surface-replay-001/website"
    candidate_site.parent.mkdir(parents=True)
    shutil.copytree(root / "website", candidate_site)
    (root / "website/index.html").write_text(
        "<!doctype html><html><body></body></html>",
        encoding="utf-8",
    )

    canonical = verify_editorial_asset_surface_bindings(
        manifest["assets"][0],
        repo_root=root,
    )
    candidate = verify_editorial_asset_surface_bindings(
        manifest["assets"][0],
        repo_root=root,
        website_root=candidate_site,
    )

    assert canonical["website_projection"] == "canonical"
    assert canonical["summary"]["bound_placement_count"] == 1
    assert candidate["website_projection"] == "candidate"
    assert candidate["summary"]["bound_placement_count"] == 2
    assert candidate["summary"]["drift_placement_count"] == 0
    assert "surface-replay-001" not in json.dumps(candidate)

    with pytest.raises(
        DesignEditorialAssetProvenanceError,
        match="canonical website|deterministic",
    ):
        verify_editorial_asset_surface_bindings(
            manifest["assets"][0],
            repo_root=root,
            website_root=root / "artifacts/website-candidates/surface-replay-001",
        )
    with pytest.raises(
        DesignEditorialAssetProvenanceError,
        match="inside the Aureon repository",
    ):
        verify_editorial_asset_surface_bindings(
            manifest["assets"][0],
            repo_root=root,
            website_root=tmp_path / "outside/website",
        )


def test_surface_binding_rejects_expected_content_outside_the_surface(
    tmp_path: Path,
) -> None:
    root, manifest = _approved_temp_repo(tmp_path)
    _install_bound_target_surfaces(root, manifest)
    path = root / "website/index.html"
    text = path.read_text(encoding="utf-8")
    opening = text.index("<picture>")
    closing = text.index("</picture>") + len("</picture>")
    picture = text[opening:closing]
    path.write_text(
        text[:opening] + text[closing:].replace("</body>", f"{picture}</body>"),
        encoding="utf-8",
    )

    binding = verify_editorial_asset_surface_bindings(
        manifest["assets"][0],
        repo_root=root,
    )
    html_row = next(
        item for item in binding["placements"] if item["destination_path"] == "website/index.html"
    )
    audit = audit_design_editorial_asset_provenance_file(
        repo_root=root,
        as_of=AS_OF,
    )

    assert html_row["state"] == "drift"
    assert html_row["binding_complete"] is False
    assert "variant-reference-outside-surface" in html_row["finding_codes"]
    assert audit["passed"] is False
    assert audit["summary"]["current_copy_drift_asset_count"] == 1


@pytest.mark.parametrize(
    "bad_source,expected_code",
    [
        ("https://example.invalid/feedback-loop-720.webp", "remote-media-source"),
        ("data:image/webp;base64,AAAA", "nonlocal-media-source"),
        (
            "blob:https://garyleckey.substack.com/00000000-0000-0000-0000-000000000000",
            "nonlocal-media-source",
        ),
    ],
)
def test_surface_binding_rejects_remote_data_and_blob_sources(
    tmp_path: Path,
    bad_source: str,
    expected_code: str,
) -> None:
    root, manifest = _approved_temp_repo(tmp_path)
    _install_bound_target_surfaces(root, manifest)
    small = str(
        next(item for item in manifest["assets"][0]["variants"] if item["role"] == "small")["path"]
    ).removeprefix("website/")
    path = root / "website/index.html"
    path.write_text(
        path.read_text(encoding="utf-8").replace(
            f'srcset="{small}"',
            f'srcset="{bad_source}"',
        ),
        encoding="utf-8",
    )

    binding = verify_editorial_asset_surface_bindings(
        manifest["assets"][0],
        repo_root=root,
    )
    html_row = next(
        item for item in binding["placements"] if item["destination_path"] == "website/index.html"
    )

    assert html_row["state"] == "drift"
    assert expected_code in html_row["finding_codes"]
    assert "extra-media-source" in html_row["finding_codes"]
    assert "small-variant-not-bound" in html_row["finding_codes"]


@pytest.mark.parametrize(
    "mutation,expected_code",
    [
        ("hidden-credit", "credit-binding-drift"),
        ("variant-path-alias", "noncanonical-variant-reference"),
    ],
)
def test_surface_binding_rejects_hidden_copy_and_variant_path_aliases(
    tmp_path: Path,
    mutation: str,
    expected_code: str,
) -> None:
    root, manifest = _approved_temp_repo(tmp_path)
    _install_bound_target_surfaces(root, manifest)
    path = root / "website/index.html"
    text = path.read_text(encoding="utf-8")
    if mutation == "hidden-credit":
        text = text.replace(
            '<p class="editorial-credit">',
            '<p class="editorial-credit" hidden>',
        )
    else:
        small = str(
            next(item for item in manifest["assets"][0]["variants"] if item["role"] == "small")["path"]
        ).removeprefix("website/")
        aliased = small.replace(
            "substack/",
            "substack/../substack/",
            1,
        )
        text = text.replace(
            f'srcset="{small}"',
            f'srcset="{aliased}"',
        )
    path.write_text(text, encoding="utf-8")

    binding = verify_editorial_asset_surface_bindings(
        manifest["assets"][0],
        repo_root=root,
    )
    html_row = next(
        item for item in binding["placements"] if item["destination_path"] == "website/index.html"
    )

    assert html_row["state"] == "drift"
    assert expected_code in html_row["finding_codes"]


def test_surface_binding_rejects_duplicate_surfaces_and_extra_media(
    tmp_path: Path,
) -> None:
    root, manifest = _approved_temp_repo(tmp_path)
    _install_bound_target_surfaces(root, manifest)
    placement = manifest["assets"][0]["placements"][0]
    path = root / "website/index.html"
    text = path.read_text(encoding="utf-8")
    text = text.replace(
        "</article>",
        '<img src="assets/images/research/substack/extra.webp" alt="extra"></article>',
        1,
    ).replace(
        "</body>",
        (f'<aside data-editorial-surface-id="{placement["surface_id"]}"></aside></body>'),
    )
    path.write_text(text, encoding="utf-8")

    binding = verify_editorial_asset_surface_bindings(
        manifest["assets"][0],
        repo_root=root,
    )
    html_row = next(
        item for item in binding["placements"] if item["destination_path"] == "website/index.html"
    )

    assert html_row["state"] == "drift"
    assert "duplicate-editorial-surface-id" in html_row["finding_codes"]
    assert "surface-id-not-unique" in html_row["finding_codes"]
    assert "extra-media-source" in html_row["finding_codes"]


@pytest.mark.parametrize(
    "mutation,expected_code",
    [
        ("duplicate-surface", "duplicate-editorial-surface-id"),
        ("wrong-url", "public-post-anchor-binding-drift"),
        ("remote-artwork", "remote-media-source"),
        ("aliased-artwork", "noncanonical-variant-reference"),
        ("missing-credit", "credit-binding-drift"),
    ],
)
def test_json_surface_binding_is_exact_and_fail_closed(
    tmp_path: Path,
    mutation: str,
    expected_code: str,
) -> None:
    root, manifest = _approved_temp_repo(tmp_path)
    _install_bound_target_surfaces(root, manifest)
    path = root / "website/data/substack-research-index.json"
    content = json.loads(path.read_text(encoding="utf-8"))
    record = content["items"][0]
    if mutation == "duplicate-surface":
        content["items"].append(deepcopy(record))
    elif mutation == "wrong-url":
        record["url"] = "https://garyleckey.substack.com/p/different-note"
    elif mutation == "remote-artwork":
        record["artwork"] = "https://example.invalid/feedback-loop.webp"
    elif mutation == "aliased-artwork":
        record["artwork"] = record["artwork"].replace(
            "substack/",
            "substack/../substack/",
            1,
        )
    else:
        del record["artwork_credit"]
    _write_json(path, content)

    binding = verify_editorial_asset_surface_bindings(
        manifest["assets"][0],
        repo_root=root,
    )
    json_row = next(
        item
        for item in binding["placements"]
        if item["destination_path"] == "website/data/substack-research-index.json"
    )

    assert json_row["state"] == "drift"
    assert json_row["binding_complete"] is False
    assert expected_code in json_row["finding_codes"]


def test_rights_decision_cannot_survive_asset_scope_drift(tmp_path: Path) -> None:
    root, manifest = _approved_temp_repo(tmp_path)
    manifest["assets"][0]["placements"][0]["caption"] += " Editorial concept only."
    _write_json(root / DEFAULT_MANIFEST_PATH, manifest)

    with pytest.raises(
        DesignEditorialAssetProvenanceError,
        match="drifted from the exact asset scope",
    ):
        build_editorial_asset_worker_capsule(
            TARGET_ASSET_ID,
            repo_root=root,
            as_of=AS_OF,
        )


def test_human_rights_decision_requires_a_name_and_non_future_time(
    tmp_path: Path,
) -> None:
    root, manifest = _approved_temp_repo(tmp_path)
    binding = manifest["assets"][0]["rights_decision"]["decision_evidence"]
    decision_path = root / binding["path"]
    decision = json.loads(decision_path.read_text(encoding="utf-8"))
    decision["decided_by"] = "https://example.test Reviewer"
    _write_json(decision_path, decision)
    binding["sha256"] = _sha256(decision_path)
    _write_json(root / DEFAULT_MANIFEST_PATH, manifest)
    with pytest.raises(
        DesignEditorialAssetProvenanceError,
        match="identifiable human reviewer",
    ):
        audit_design_editorial_asset_provenance_file(
            repo_root=root,
            as_of=AS_OF,
        )

    decision["decided_by"] = "Gary Leckey"
    decision["decided_at"] = "2026-07-31T00:30:00Z"
    _write_json(decision_path, decision)
    binding["sha256"] = _sha256(decision_path)
    _write_json(root / DEFAULT_MANIFEST_PATH, manifest)
    with pytest.raises(
        DesignEditorialAssetProvenanceError,
        match="future-dated",
    ):
        audit_design_editorial_asset_provenance_file(
            repo_root=root,
            as_of=AS_OF,
        )


def test_syntactically_valid_but_untrusted_reviewer_cannot_grant_rights(
    tmp_path: Path,
) -> None:
    root, manifest = _approved_temp_repo(tmp_path)
    binding = manifest["assets"][0]["rights_decision"]["decision_evidence"]
    decision_path = root / binding["path"]
    decision = json.loads(decision_path.read_text(encoding="utf-8"))
    decision["decided_by"] = "Mickey Mouse"
    _write_json(decision_path, decision)
    binding["sha256"] = _sha256(decision_path)
    _write_json(root / DEFAULT_MANIFEST_PATH, manifest)

    with pytest.raises(
        DesignEditorialAssetProvenanceError,
        match="controlled owner-reviewer allowlist",
    ):
        audit_design_editorial_asset_provenance_file(
            repo_root=root,
            as_of=AS_OF,
        )


def test_representation_safety_blocks_facility_like_art_without_boundary() -> None:
    manifest = _manifest()
    feedback_loop = next(item for item in manifest["assets"] if item["asset_id"] == TARGET_ASSET_ID)
    feedback_loop["placements"][0]["alt"] = "Editorial photograph of the Aureon optical laboratory."

    with pytest.raises(
        DesignEditorialAssetProvenanceError,
        match="representational-safety class",
    ):
        audit_design_editorial_asset_provenance(
            manifest,
            manifest_path=MANIFEST_PATH,
            repo_root=REPO_ROOT,
            as_of=AS_OF,
        )


@pytest.mark.parametrize(
    "public_url",
    [
        "https://garyleckey.substack.com/p/example?token=secret",
        "https://garyleckey.substack.com/p/example#fragment",
        "https://garyleckey.substack.com/redirect/example",
        "https://user:password@garyleckey.substack.com/p/example",
        "http://garyleckey.substack.com/p/example",
        "https://example.test/p/example",
    ],
)
def test_public_post_must_be_direct_and_credential_free(public_url: str) -> None:
    manifest = _manifest()
    manifest["assets"][0]["public_post_url"] = public_url

    with pytest.raises(
        DesignEditorialAssetProvenanceError,
        match="direct credential-free public Substack post URL",
    ):
        audit_design_editorial_asset_provenance(
            manifest,
            manifest_path=MANIFEST_PATH,
            repo_root=REPO_ROOT,
            as_of=AS_OF,
        )


def test_global_artwork_policy_cannot_be_cleared() -> None:
    manifest = _manifest()
    manifest["global_artwork_policy"]["state"] = "cleared"
    manifest["global_artwork_policy"]["cleared_for_use"] = True

    with pytest.raises(
        DesignEditorialAssetProvenanceError,
        match="Global artwork policy must remain not-cleared",
    ):
        audit_design_editorial_asset_provenance(
            manifest,
            manifest_path=MANIFEST_PATH,
            repo_root=REPO_ROOT,
            as_of=AS_OF,
        )


def test_hash_drift_and_path_traversal_fail_closed() -> None:
    drift = _manifest()
    drift["assets"][0]["variants"][0]["sha256"] = "0" * 64
    result = audit_design_editorial_asset_provenance(
        drift,
        manifest_path=MANIFEST_PATH,
        repo_root=REPO_ROOT,
        as_of=AS_OF,
    )
    target = next(item for item in result["assets"] if item["asset_id"] == drift["assets"][0]["asset_id"])
    assert result["passed"] is False
    assert target["candidate_use_ready"] is False
    assert any(variant["hash_matches"] is False for variant in target["variants"])

    traversal = _manifest()
    traversal["assets"][0]["source_asset"]["path"] = "docs/design-assets/substack-public-art/../../../.env"
    with pytest.raises(DesignEditorialAssetProvenanceError, match="unsafe"):
        audit_design_editorial_asset_provenance(
            traversal,
            manifest_path=MANIFEST_PATH,
            repo_root=REPO_ROOT,
            as_of=AS_OF,
        )


def test_magic_mime_static_webp_and_metadata_are_inspected() -> None:
    with pytest.raises(
        DesignEditorialAssetProvenanceError,
        match="JPEG magic",
    ):
        _jpeg_probe(b"not-a-jpeg")

    vp8x_payload = b"\x02\x00\x00\x00" + (719).to_bytes(3, "little") + (404).to_bytes(3, "little")
    anim_payload = b"\x00\x00\x00\x00\x00\x00"
    chunks = (
        b"VP8X"
        + len(vp8x_payload).to_bytes(4, "little")
        + vp8x_payload
        + b"ANIM"
        + len(anim_payload).to_bytes(4, "little")
        + anim_payload
    )
    animated = b"RIFF" + (len(chunks) + 4).to_bytes(4, "little") + b"WEBP" + chunks
    probe = _webp_probe(animated)
    assert probe["media_type"] == "image/webp"
    assert probe["width"] == 720
    assert probe["height"] == 405
    assert probe["animation"] == "animated"


def test_hardlinks_and_reparse_paths_are_not_regular_safe_files(
    tmp_path: Path,
) -> None:
    original = tmp_path / "original.bin"
    original.write_bytes(b"bounded")
    hardlink = tmp_path / "hardlink.bin"
    try:
        os.link(original, hardlink)
    except (OSError, NotImplementedError) as exc:
        pytest.skip(f"Hardlink creation is unavailable: {exc}")
    _, hardlink_safety = _file_safety(
        tmp_path,
        "hardlink.bin",
        max_bytes=1024,
    )
    assert hardlink_safety["single_link"] is False
    assert hardlink_safety["regular_file"] is False

    symlink = tmp_path / "symlink.bin"
    try:
        os.symlink(original, symlink)
    except (OSError, NotImplementedError):
        return
    _, symlink_safety = _file_safety(
        tmp_path,
        "symlink.bin",
        max_bytes=1024,
    )
    assert symlink_safety["reparse_free"] is False
    assert symlink_safety["regular_file"] is False


def test_schema_is_exact_pending_and_non_authoritative() -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    manifest = _manifest()

    assert manifest["schema"] == MANIFEST_SCHEMA
    assert schema["$defs"]["manifest"]["additionalProperties"] is False
    assert schema["$defs"]["asset"]["additionalProperties"] is False
    assert schema["$defs"]["placement"]["additionalProperties"] is False
    assert schema["$defs"]["pendingRights"]["additionalProperties"] is False
    assert schema["$defs"]["pendingRights"]["properties"]["named_human_decision"]["const"] is False
    assert schema["$defs"]["deliveryEvidence"]["properties"]["rights_effect"]["const"] == "none"
    authority = schema["$defs"]["authority"]["properties"]
    assert authority["release_eligible"]["const"] is False
    assert authority["package_authority"]["const"] == "none"
    assert authority["deployment_authority"]["const"] == "none"
    assert authority["credential_access"]["const"] == "none"
    assert authority["network_access"]["const"] == "none"
    assert authority["connector_access"]["const"] == "none"

    jsonschema = pytest.importorskip("jsonschema")
    jsonschema.Draft202012Validator.check_schema(schema)
    jsonschema.Draft202012Validator(schema).validate(manifest)


def test_audit_writer_is_immutable_and_confined_to_docs_audits(
    tmp_path: Path,
) -> None:
    root = tmp_path / "repo"
    (root / "aureon").mkdir(parents=True)
    (root / "pyproject.toml").write_text(
        "[project]\nname='editorial-audit-writer-test'\nversion='0.0.0'\n",
        encoding="utf-8",
    )
    receipt = audit_design_editorial_asset_provenance_file(
        repo_root=REPO_ROOT,
        as_of=AS_OF,
    )
    output = Path("docs/audits/EDITORIAL_ASSET_AUDIT_TEST.json")

    written = write_editorial_asset_provenance_audit(
        receipt,
        output,
        repo_root=root,
    )
    assert json.loads(written.read_text(encoding="utf-8")) == receipt

    with pytest.raises(
        DesignEditorialAssetProvenanceError,
        match="already exists",
    ):
        write_editorial_asset_provenance_audit(
            receipt,
            output,
            repo_root=root,
        )

    with pytest.raises(
        DesignEditorialAssetProvenanceError,
        match="below docs/audits",
    ):
        write_editorial_asset_provenance_audit(
            receipt,
            Path("artifacts/unsafe-audit.json"),
            repo_root=root,
        )

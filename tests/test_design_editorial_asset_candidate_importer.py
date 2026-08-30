from __future__ import annotations

import hashlib
import json
import os
import shutil
from copy import deepcopy
from dataclasses import dataclass
from datetime import UTC, datetime
from html import escape
from pathlib import Path
from typing import Any

import pytest

import aureon.operator.design_candidate_control as candidate_control
import aureon.operator.design_editorial_asset_candidate_importer as importer
from aureon.operator.design_editorial_asset_candidate_importer import (
    DEFAULT_RECEIPT_NAME,
    IMPORT_RECEIPT_SCHEMA,
    IMPORT_VERIFICATION_SCHEMA,
    NON_AUTHORITATIVE_AUTHORITY,
    DesignEditorialAssetCandidateImporterError,
    import_editorial_assets_to_candidate,
    verify_candidate_editorial_asset_import,
    write_candidate_editorial_asset_import,
)
from aureon.operator.design_editorial_asset_provenance import (
    DEFAULT_MANIFEST_PATH,
    RIGHTS_BOUNDARY_ACKNOWLEDGEMENT,
    RIGHTS_DECISION_SCHEMA,
    RIGHTS_USAGE_SCOPE,
    asset_scope_sha256,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_MANIFEST_PATH = REPO_ROOT / DEFAULT_MANIFEST_PATH
SOURCE_DELIVERY_PATH = (
    REPO_ROOT / "docs/research/editorial-assets/SUBSTACK_SHAREABLE_ASSET_DELIVERY_REDACTION_20260730.json"
)
SOURCE_INVENTORY_PATH = (
    REPO_ROOT / "docs/research/editorial-assets/LOCAL_EDITORIAL_ASSET_INVENTORY_20260730.json"
)
SCHEMA_PATH = (
    REPO_ROOT / "docs/research/schemas/AUREON_DESIGN_EDITORIAL_ASSET_CANDIDATE_IMPORT_V1.schema.json"
)
VERIFICATION_SCHEMA_PATH = (
    REPO_ROOT
    / "docs/research/schemas/AUREON_DESIGN_EDITORIAL_ASSET_CANDIDATE_IMPORT_VERIFICATION_V1.schema.json"
)
TARGET_ASSET_ID = "substack-feedback-loop"
RUN_ID = "editorial-import-test"
AS_OF = datetime(2026, 7, 30, 0, 35, tzinfo=UTC)
NOW = datetime(2026, 7, 30, 0, 40, tzinfo=UTC)


@dataclass(frozen=True)
class PreparedImport:
    root: Path
    work_order_path: Path
    candidate_root: Path
    manifest_path: Path
    work_order: dict[str, Any]
    asset: dict[str, Any]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _prepare_import_repo(
    tmp_path: Path,
    *,
    approved: bool = True,
) -> PreparedImport:
    root = tmp_path / "repo"
    (root / "aureon").mkdir(parents=True)
    (root / "pyproject.toml").write_text(
        "[project]\nname='editorial-import-test'\nversion='0.0.0'\n",
        encoding="utf-8",
    )

    manifest = json.loads(SOURCE_MANIFEST_PATH.read_text(encoding="utf-8"))
    target = deepcopy(next(item for item in manifest["assets"] if item["asset_id"] == TARGET_ASSET_ID))
    manifest["assets"] = [target]
    manifest["unmapped_assets"] = []

    delivery = json.loads(SOURCE_DELIVERY_PATH.read_text(encoding="utf-8"))
    delivery["items"] = [item for item in delivery["items"] if item["asset_id"] == TARGET_ASSET_ID]
    delivery_target = (
        root / "docs/research/editorial-assets/SUBSTACK_SHAREABLE_ASSET_DELIVERY_REDACTION_20260730.json"
    )
    _write_json(delivery_target, delivery)

    inventory = json.loads(SOURCE_INVENTORY_PATH.read_text(encoding="utf-8"))
    inventory["files"] = [item for item in inventory["files"] if item["asset_id"] == TARGET_ASSET_ID]
    inventory_target = root / "docs/research/editorial-assets/LOCAL_EDITORIAL_ASSET_INVENTORY_20260730.json"
    _write_json(inventory_target, inventory)

    evidence_by_kind = {item["kind"]: item for item in manifest["evidence_snapshots"]}
    evidence_by_kind["redacted-delivery-evidence"]["sha256"] = _sha256(delivery_target)
    evidence_by_kind["redacted-local-asset-inventory"]["sha256"] = _sha256(inventory_target)

    for record in [target["source_asset"], *target["variants"]]:
        source = REPO_ROOT / record["path"]
        destination = root / record["path"]
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)

    if approved:
        decision = {
            "schema": RIGHTS_DECISION_SCHEMA,
            "decision_id": "owner-rights-decision-feedback-loop-import-test",
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

    website = root / "website"
    website.mkdir(exist_ok=True)
    (website / "index.html").write_text(
        "<!doctype html><html><body>Bound editorial route.</body></html>\n",
        encoding="utf-8",
    )
    baseline = importer._tree_summary(website)

    allowed_paths = sorted(
        [
            "index.html",
            *[Path(*Path(item["path"]).parts[1:]).as_posix() for item in target["variants"]],
        ]
    )
    work_order: dict[str, Any] = {
        "schema": "aureon.design-work-order.v4",
        "created_at": "2026-07-30T00:32:00Z",
        "run_id": RUN_ID,
        "goal": "Import one exact approved editorial asset batch.",
        "routes": ["/"],
        "allowed_paths": allowed_paths,
        "allowed_new_origins": [],
        "live_reconciliation": {},
        "baseline": baseline,
        "claim_control": {},
        "test_policy": {},
        "editorial_asset_control": importer.editorial_asset_control_binding(
            RUN_ID,
            allowed_paths=allowed_paths,
            repo_root=root,
        ),
        "candidate_layout": {
            "root": f"artifacts/website-candidates/{RUN_ID}",
            "website_path": f"artifacts/website-candidates/{RUN_ID}/website",
            "staged_claim_register_path": (
                f"artifacts/website-candidates/{RUN_ID}/claim-evidence/public_claim_evidence_register.v1.json"
            ),
        },
        "authority": {},
    }
    work_order_path = root / "artifacts/website-candidates/work-orders/editorial-import-test.v4.json"
    _write_json(work_order_path, work_order)

    candidate_root = root / f"artifacts/website-candidates/{RUN_ID}"
    candidate_root.mkdir(parents=True)
    shutil.copytree(website, candidate_root / "website")
    _write_json(candidate_root / "work-order.v4.json", work_order)

    intake_root = root / "artifacts/website-operator/editorial-assets/verified"
    intake_root.mkdir(parents=True)
    for variant in target["variants"]:
        shutil.copy2(
            root / variant["path"],
            intake_root / f"{variant['sha256']}.webp",
        )

    return PreparedImport(
        root=root,
        work_order_path=work_order_path,
        candidate_root=candidate_root,
        manifest_path=manifest_path,
        work_order=work_order,
        asset=target,
    )


def _allow_source_bound_verification(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def passed_verification(
        work_order: dict[str, Any],
        *,
        repo_root: Path | None = None,
        require_current_baseline: bool = True,
    ) -> dict[str, Any]:
        assert work_order["schema"] == "aureon.design-work-order.v4"
        assert repo_root is not None
        assert isinstance(require_current_baseline, bool)
        return {"passed": True, "checks": []}

    monkeypatch.setattr(importer, "verify_design_work_order", passed_verification)


def _rewrite_order(prepared: PreparedImport, work_order: dict[str, Any]) -> None:
    _write_json(prepared.work_order_path, work_order)
    _write_json(prepared.candidate_root / "work-order.v4.json", work_order)


def _candidate_summary(prepared: PreparedImport) -> dict[str, Any]:
    return importer._tree_summary(prepared.candidate_root / "website")


def _intake_path(prepared: PreparedImport, role: str) -> Path:
    variant = next(item for item in prepared.asset["variants"] if item["role"] == role)
    return (
        prepared.root / "artifacts/website-operator/editorial-assets/verified" / f"{variant['sha256']}.webp"
    )


def _install_candidate_editorial_surface(prepared: PreparedImport) -> None:
    asset = prepared.asset
    placement = next(item for item in asset["placements"] if item["route_scope"] == "/")
    variants = {item["role"]: item for item in asset["variants"]}
    small = str(variants["small"]["path"]).removeprefix("website/")
    large = str(variants["large"]["path"]).removeprefix("website/")
    html = f"""<!doctype html>
<html><body>
  <article data-editorial-surface-id="{escape(placement["surface_id"])}">
    <a href="{escape(asset["public_post_url"])}">
      <picture>
        <source type="image/webp" srcset="{escape(small)}">
        <img src="{escape(large)}"
             alt="{escape(placement["alt"])}"
             width="{variants["large"]["width"]}"
             height="{variants["large"]["height"]}">
      </picture>
    </a>
    <figcaption>{escape(placement["caption"])}</figcaption>
    <p>{escape(placement["credit"])}</p>
  </article>
</body></html>
"""
    (prepared.candidate_root / "website/index.html").write_text(
        html,
        encoding="utf-8",
    )


def _candidate_editorial_checks(
    prepared: PreparedImport,
) -> tuple[dict[str, Any], dict[str, Any]]:
    candidate_site = prepared.candidate_root / "website"
    changes = candidate_control._change_records(
        prepared.work_order["baseline"]["files"],
        candidate_control._file_manifest(candidate_site),
    )
    binary = candidate_control._trusted_binary_import_replay_check(
        root=prepared.root,
        order=prepared.work_order,
        candidate_root=prepared.candidate_root,
        candidate_site=candidate_site,
        changes=changes,
        as_of=AS_OF,
        require_current_baseline=True,
    )
    surface = candidate_control._trusted_editorial_surface_replay_check(
        root=prepared.root,
        order=prepared.work_order,
        candidate_root=prepared.candidate_root,
        candidate_site=candidate_site,
        binary_replay_check=binary,
        as_of=AS_OF,
    )
    return binary, surface


def test_imports_complete_batch_and_emits_redacted_immutable_receipt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prepared = _prepare_import_repo(tmp_path)
    _allow_source_bound_verification(monkeypatch)
    canonical_before = importer._tree_summary(prepared.root / "website")

    receipt = import_editorial_assets_to_candidate(
        prepared.work_order_path,
        repo_root=prepared.root,
        as_of=AS_OF,
        now=NOW,
    )

    assert receipt["schema"] == IMPORT_RECEIPT_SCHEMA
    assert receipt["state"] == "imported-local-candidate"
    assert receipt["passed"] is True
    assert receipt["batch_complete"] is True
    assert receipt["receipt_authority"] is False
    assert receipt["release_eligible"] is False
    assert receipt["package_authority"] == "none"
    assert receipt["deployment_authority"] == "none"
    assert receipt["authority"] == NON_AUTHORITATIVE_AUTHORITY
    assert receipt["provenance"]["global_artwork_policy_state"] == "not-cleared"
    assert receipt["provenance"]["global_artwork_cleared_for_use"] is False
    assert receipt["provenance"]["candidate_ready_asset_ids"] == [TARGET_ASSET_ID]
    assert receipt["routes"] == ["/"]
    assert receipt["summary"]["asset_count"] == 1
    assert receipt["summary"]["file_count"] == 2
    assert receipt["summary"]["batch_complete"] is True
    control = prepared.work_order["editorial_asset_control"]
    assert control["provenance_manifest_path"] == DEFAULT_MANIFEST_PATH.as_posix()
    assert control["provenance_manifest_sha256"] == _sha256(prepared.manifest_path)
    assert control["surface_binding_verification_required"] is True
    assert {item["role"] for item in receipt["imports"]} == {"small", "large"}
    assert all(
        item["target"].startswith(f"artifacts/website-candidates/{RUN_ID}/website/")
        for item in receipt["imports"]
    )
    assert importer._tree_summary(prepared.root / "website") == canonical_before

    receipt_path = prepared.candidate_root / DEFAULT_RECEIPT_NAME
    assert json.loads(receipt_path.read_text(encoding="utf-8")) == receipt
    verification = verify_candidate_editorial_asset_import(
        receipt,
        repo_root=prepared.root,
        as_of=AS_OF,
        verified_at=NOW,
    )
    assert verification["schema"] == IMPORT_VERIFICATION_SCHEMA
    assert verification["state"] == "verified-local-candidate"
    assert verification["passed"] is True
    assert verification["release_eligible"] is False
    assert verification["package_authority"] == "none"
    assert verification["deployment_authority"] == "none"
    assert verification["receipt"]["persisted"] is True
    assert verification["receipt"]["file_sha256"] == _sha256(receipt_path)
    payload = dict(receipt)
    payload_hash = payload.pop("receipt_payload_sha256")
    assert payload_hash == importer._json_sha256(payload)
    assert not list(prepared.candidate_root.glob(".editorial-import-*"))

    serialised = json.dumps(receipt).casefold()
    for prohibited in (
        "/verified/",
        "rights-decisions",
        "decided_by",
        "decision_evidence",
        "source_asset",
        "source-register",
        ".env",
        "aureon owner reviewer",
    ):
        assert prohibited not in serialised

    with pytest.raises(
        DesignEditorialAssetCandidateImporterError,
        match="immutable and already exists",
    ):
        import_editorial_assets_to_candidate(
            prepared.work_order_path,
            repo_root=prepared.root,
            as_of=AS_OF,
            now=NOW,
        )
    with pytest.raises(
        DesignEditorialAssetCandidateImporterError,
        match="immutable and already exists",
    ):
        write_candidate_editorial_asset_import(
            receipt,
            repo_root=prepared.root,
            as_of=AS_OF,
        )


def test_candidate_replays_imported_bytes_into_one_exact_structural_surface(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prepared = _prepare_import_repo(tmp_path)
    _allow_source_bound_verification(monkeypatch)
    import_editorial_assets_to_candidate(
        prepared.work_order_path,
        repo_root=prepared.root,
        as_of=AS_OF,
        now=NOW,
    )
    _install_candidate_editorial_surface(prepared)

    binary, surface = _candidate_editorial_checks(prepared)

    assert binary["passed"] is True
    assert surface["passed"] is True
    evidence = surface["evidence"]
    assert evidence["verification_state"] == "verified-local-candidate"
    assert evidence["candidate_ready_asset_ids"] == [TARGET_ASSET_ID]
    assert len(evidence["expected_surfaces"]) == 1
    assert evidence["expected_surfaces"][0]["surface_id"] == ("home-feedback-loop-question")
    assert evidence["failed_surfaces"] == []
    assert len(evidence["selected_route_asset_capsules_sha256"]) == 64
    assert len(evidence["candidate_surface_bindings_sha256"]) == 64
    assert len(evidence["expected_surfaces_sha256"]) == 64
    serialised = json.dumps(surface).casefold()
    assert "aureon owner reviewer" not in serialised
    assert "rights-decisions" not in serialised
    assert "decision_evidence" not in serialised


def test_candidate_surface_replay_rejects_wrong_post_and_comment_only_credit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prepared = _prepare_import_repo(tmp_path)
    _allow_source_bound_verification(monkeypatch)
    import_editorial_assets_to_candidate(
        prepared.work_order_path,
        repo_root=prepared.root,
        as_of=AS_OF,
        now=NOW,
    )
    _install_candidate_editorial_surface(prepared)
    target = prepared.candidate_root / "website/index.html"
    placement = prepared.asset["placements"][0]
    target.write_text(
        target.read_text(encoding="utf-8")
        .replace(
            prepared.asset["public_post_url"],
            "https://garyleckey.substack.com/p/different-note",
        )
        .replace(
            f"<p>{escape(placement['credit'])}</p>",
            f"<!-- {escape(placement['credit'])} -->",
        ),
        encoding="utf-8",
    )

    binary, surface = _candidate_editorial_checks(prepared)

    assert binary["passed"] is True
    assert surface["passed"] is False
    failed = surface["evidence"]["failed_surfaces"]
    assert len(failed) == 1
    assert {
        "public-post-anchor-binding-drift",
        "credit-binding-drift",
    }.issubset(set(failed[0]["finding_codes"]))


def test_public_verifier_rejects_receipt_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prepared = _prepare_import_repo(tmp_path)
    _allow_source_bound_verification(monkeypatch)
    receipt = import_editorial_assets_to_candidate(
        prepared.work_order_path,
        repo_root=prepared.root,
        as_of=AS_OF,
        now=NOW,
    )

    tampered_receipt = deepcopy(receipt)
    tampered_receipt["summary"]["total_bytes"] += 1
    with pytest.raises(
        DesignEditorialAssetCandidateImporterError,
        match="payload hash does not match",
    ):
        verify_candidate_editorial_asset_import(
            tampered_receipt,
            repo_root=prepared.root,
            as_of=AS_OF,
        )


@pytest.mark.parametrize("drift_kind", ["tamper", "addition", "removal"])
def test_public_verifier_rejects_unreceipted_binary_projection_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    drift_kind: str,
) -> None:
    prepared = _prepare_import_repo(tmp_path)
    _allow_source_bound_verification(monkeypatch)
    receipt = import_editorial_assets_to_candidate(
        prepared.work_order_path,
        repo_root=prepared.root,
        as_of=AS_OF,
        now=NOW,
    )
    target = prepared.root / receipt["imports"][0]["target"]
    if drift_kind == "tamper":
        data = bytearray(target.read_bytes())
        data[-1] ^= 0x01
        target.write_bytes(data)
    elif drift_kind == "addition":
        (prepared.candidate_root / "website/assets/rogue.woff2").parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        (prepared.candidate_root / "website/assets/rogue.woff2").write_bytes(b"unreceipted-binary")
    else:
        target.unlink()

    with pytest.raises(
        DesignEditorialAssetCandidateImporterError,
        match="Candidate binary projection no longer equals",
    ):
        verify_candidate_editorial_asset_import(
            receipt,
            repo_root=prepared.root,
            as_of=AS_OF,
        )


def test_public_verifier_permits_later_controlled_text_edits(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prepared = _prepare_import_repo(tmp_path)
    _allow_source_bound_verification(monkeypatch)
    receipt = import_editorial_assets_to_candidate(
        prepared.work_order_path,
        repo_root=prepared.root,
        as_of=AS_OF,
        now=NOW,
    )
    (prepared.candidate_root / "website/index.html").write_text(
        "<!doctype html><html><body>Later controlled text edit.</body></html>\n",
        encoding="utf-8",
    )

    verification = verify_candidate_editorial_asset_import(
        receipt,
        repo_root=prepared.root,
        as_of=AS_OF,
        verified_at=NOW,
    )

    assert verification["passed"] is True


@pytest.mark.parametrize(
    ("field", "tampered_value"),
    [
        ("policy", "caller-asserted-binary-control"),
        ("provenance_manifest_sha256", "0" * 64),
        ("surface_binding_verification_required", False),
    ],
)
def test_v4_editorial_asset_control_is_exact_and_source_bound(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    field: str,
    tampered_value: object,
) -> None:
    prepared = _prepare_import_repo(tmp_path)
    _allow_source_bound_verification(monkeypatch)
    order = deepcopy(prepared.work_order)
    order["editorial_asset_control"][field] = tampered_value
    _rewrite_order(prepared, order)

    with pytest.raises(
        DesignEditorialAssetCandidateImporterError,
        match="exact v4 receipt, replay, and provenance-surface binding",
    ):
        import_editorial_assets_to_candidate(
            prepared.work_order_path,
            repo_root=prepared.root,
            as_of=AS_OF,
        )


def test_v4_text_only_control_has_no_provenance_surface_binding(
    tmp_path: Path,
) -> None:
    prepared = _prepare_import_repo(tmp_path)

    control = importer.editorial_asset_control_binding(
        RUN_ID,
        allowed_paths=["index.html"],
        repo_root=prepared.root,
    )

    assert control["provenance_manifest_path"] == ""
    assert control["provenance_manifest_sha256"] == ""
    assert control["surface_binding_verification_required"] is False


def test_public_verifier_rejects_manifest_drift_after_work_order_issuance(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prepared = _prepare_import_repo(tmp_path)
    _allow_source_bound_verification(monkeypatch)
    receipt = import_editorial_assets_to_candidate(
        prepared.work_order_path,
        repo_root=prepared.root,
        as_of=AS_OF,
        now=NOW,
    )
    manifest = json.loads(prepared.manifest_path.read_text(encoding="utf-8"))
    manifest["manifest_id"] = "editorial-import-test-manifest-drift"
    _write_json(prepared.manifest_path, manifest)

    with pytest.raises(
        DesignEditorialAssetCandidateImporterError,
        match="exact v4 receipt, replay, and provenance-surface binding",
    ):
        verify_candidate_editorial_asset_import(
            receipt,
            repo_root=prepared.root,
            as_of=AS_OF,
        )


def test_public_verifier_propagates_current_baseline_policy(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prepared = _prepare_import_repo(tmp_path)
    calls: list[bool] = []

    def passed_verification(
        work_order: dict[str, Any],
        *,
        repo_root: Path | None = None,
        require_current_baseline: bool = True,
    ) -> dict[str, Any]:
        assert work_order["schema"] == "aureon.design-work-order.v4"
        assert repo_root is not None
        calls.append(require_current_baseline)
        return {"passed": True, "checks": []}

    monkeypatch.setattr(importer, "verify_design_work_order", passed_verification)
    receipt = import_editorial_assets_to_candidate(
        prepared.work_order_path,
        repo_root=prepared.root,
        as_of=AS_OF,
        now=NOW,
    )
    calls.clear()

    verification = verify_candidate_editorial_asset_import(
        receipt,
        repo_root=prepared.root,
        as_of=AS_OF,
        _require_current_baseline=False,
    )

    assert verification["passed"] is True
    assert calls == [False]


def test_requires_persisted_work_order_below_controlled_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prepared = _prepare_import_repo(tmp_path)
    _allow_source_bound_verification(monkeypatch)
    outside = prepared.root / "outside-order.json"
    _write_json(outside, prepared.work_order)

    with pytest.raises(
        DesignEditorialAssetCandidateImporterError,
        match="escapes its controlled root",
    ):
        import_editorial_assets_to_candidate(
            outside,
            repo_root=prepared.root,
            as_of=AS_OF,
        )

    with pytest.raises(
        DesignEditorialAssetCandidateImporterError,
        match="persisted design work-order JSON path",
    ):
        import_editorial_assets_to_candidate(  # type: ignore[arg-type]
            prepared.work_order,
            repo_root=prepared.root,
            as_of=AS_OF,
        )


def test_stale_source_bound_verification_blocks_before_any_write(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prepared = _prepare_import_repo(tmp_path)
    before = _candidate_summary(prepared)

    def failed_verification(
        work_order: dict[str, Any],
        *,
        repo_root: Path | None = None,
        require_current_baseline: bool = True,
    ) -> dict[str, Any]:
        assert work_order
        assert repo_root is not None
        assert require_current_baseline is True
        return {
            "passed": False,
            "checks": [{"id": "baseline-current", "passed": False}],
        }

    monkeypatch.setattr(importer, "verify_design_work_order", failed_verification)
    with pytest.raises(
        DesignEditorialAssetCandidateImporterError,
        match="invalid or stale: baseline-current",
    ):
        import_editorial_assets_to_candidate(
            prepared.work_order_path,
            repo_root=prepared.root,
            as_of=AS_OF,
        )

    assert _candidate_summary(prepared) == before
    assert not (prepared.candidate_root / DEFAULT_RECEIPT_NAME).exists()


def test_candidate_work_order_copy_mismatch_is_importer_bypass(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prepared = _prepare_import_repo(tmp_path)
    _allow_source_bound_verification(monkeypatch)
    candidate_order = deepcopy(prepared.work_order)
    candidate_order["goal"] = "Unbound candidate-local rewrite."
    _write_json(prepared.candidate_root / "work-order.v4.json", candidate_order)

    with pytest.raises(
        DesignEditorialAssetCandidateImporterError,
        match="does not match the persisted source-bound order",
    ):
        import_editorial_assets_to_candidate(
            prepared.work_order_path,
            repo_root=prepared.root,
            as_of=AS_OF,
        )


def test_candidate_binary_baseline_drift_is_importer_bypass(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prepared = _prepare_import_repo(tmp_path)
    _allow_source_bound_verification(monkeypatch)
    target_relative = Path(*Path(prepared.asset["variants"][0]["path"]).parts[1:])
    candidate_target = prepared.candidate_root / "website" / target_relative
    data = bytearray(candidate_target.read_bytes())
    data[-1] ^= 0x01
    candidate_target.write_bytes(data)

    with pytest.raises(
        DesignEditorialAssetCandidateImporterError,
        match="baseline mismatch.*importer bypass",
    ):
        import_editorial_assets_to_candidate(
            prepared.work_order_path,
            repo_root=prepared.root,
            as_of=AS_OF,
        )


def test_unapproved_asset_is_never_imported(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prepared = _prepare_import_repo(tmp_path, approved=False)
    _allow_source_bound_verification(monkeypatch)
    before = _candidate_summary(prepared)

    with pytest.raises(
        DesignEditorialAssetCandidateImporterError,
        match="not candidate-use-ready",
    ):
        import_editorial_assets_to_candidate(
            prepared.work_order_path,
            repo_root=prepared.root,
            as_of=AS_OF,
        )

    assert _candidate_summary(prepared) == before
    assert not (prepared.candidate_root / DEFAULT_RECEIPT_NAME).exists()


def test_partial_variant_batch_is_rejected_before_staging(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prepared = _prepare_import_repo(tmp_path)
    _allow_source_bound_verification(monkeypatch)
    order = deepcopy(prepared.work_order)
    order["allowed_paths"] = [path for path in order["allowed_paths"] if not path.endswith("-720.webp")]
    _rewrite_order(prepared, order)

    with pytest.raises(
        DesignEditorialAssetCandidateImporterError,
        match="Partial editorial asset batch",
    ):
        import_editorial_assets_to_candidate(
            prepared.work_order_path,
            repo_root=prepared.root,
            as_of=AS_OF,
        )
    assert not list(prepared.candidate_root.glob(".editorial-import-*"))


def test_route_and_destination_mismatch_fail_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prepared = _prepare_import_repo(tmp_path)
    _allow_source_bound_verification(monkeypatch)

    route_mismatch = deepcopy(prepared.work_order)
    route_mismatch["routes"] = ["/research/"]
    _rewrite_order(prepared, route_mismatch)
    with pytest.raises(
        DesignEditorialAssetCandidateImporterError,
        match="no placement on a work-order route",
    ):
        import_editorial_assets_to_candidate(
            prepared.work_order_path,
            repo_root=prepared.root,
            as_of=AS_OF,
        )

    destination_mismatch = deepcopy(prepared.work_order)
    destination_mismatch["allowed_paths"] = [
        path for path in destination_mismatch["allowed_paths"] if path != "index.html"
    ]
    _rewrite_order(prepared, destination_mismatch)
    with pytest.raises(
        DesignEditorialAssetCandidateImporterError,
        match="destination is not declared",
    ):
        import_editorial_assets_to_candidate(
            prepared.work_order_path,
            repo_root=prepared.root,
            as_of=AS_OF,
        )


def test_path_escape_and_unbound_image_target_fail_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prepared = _prepare_import_repo(tmp_path)
    _allow_source_bound_verification(monkeypatch)

    traversal = deepcopy(prepared.work_order)
    traversal["allowed_paths"].append("../escape.webp")
    _rewrite_order(prepared, traversal)
    with pytest.raises(
        DesignEditorialAssetCandidateImporterError,
        match="allowed path is unsafe",
    ):
        import_editorial_assets_to_candidate(
            prepared.work_order_path,
            repo_root=prepared.root,
            as_of=AS_OF,
        )

    unbound = deepcopy(prepared.work_order)
    unbound["allowed_paths"].append("assets/images/research/substack/unbound.webp")
    _rewrite_order(prepared, unbound)
    with pytest.raises(
        DesignEditorialAssetCandidateImporterError,
        match="not uniquely bound",
    ):
        import_editorial_assets_to_candidate(
            prepared.work_order_path,
            repo_root=prepared.root,
            as_of=AS_OF,
        )


@pytest.mark.parametrize("drift_kind", ["hash", "mime", "dimension", "animation"])
def test_intake_hash_mime_dimension_and_animation_drift_leave_no_partial_batch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    drift_kind: str,
) -> None:
    prepared = _prepare_import_repo(tmp_path)
    _allow_source_bound_verification(monkeypatch)
    before = _candidate_summary(prepared)
    small = _intake_path(prepared, "small")
    if drift_kind == "hash":
        data = bytearray(small.read_bytes())
        data[-1] ^= 0x01
        small.write_bytes(data)
    elif drift_kind == "mime":
        small.write_bytes((prepared.root / prepared.asset["source_asset"]["path"]).read_bytes())
    elif drift_kind == "dimension":
        small.write_bytes(_intake_path(prepared, "large").read_bytes())
    else:
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
        small.write_bytes(b"RIFF" + (len(chunks) + 4).to_bytes(4, "little") + b"WEBP" + chunks)

    with pytest.raises(
        DesignEditorialAssetCandidateImporterError,
        match="drifted from the exact approved image record",
    ):
        import_editorial_assets_to_candidate(
            prepared.work_order_path,
            repo_root=prepared.root,
            as_of=AS_OF,
        )

    assert _candidate_summary(prepared) == before
    assert not (prepared.candidate_root / DEFAULT_RECEIPT_NAME).exists()
    assert not list(prepared.candidate_root.glob(".editorial-import-*"))


def test_hardlink_and_symlink_intake_are_rejected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prepared = _prepare_import_repo(tmp_path)
    _allow_source_bound_verification(monkeypatch)
    intake = _intake_path(prepared, "small")
    duplicate = prepared.root / "hardlink-source.webp"
    shutil.copy2(intake, duplicate)
    intake.unlink()
    try:
        os.link(duplicate, intake)
    except (OSError, NotImplementedError) as exc:
        pytest.skip(f"Hardlink creation is unavailable: {exc}")

    with pytest.raises(
        DesignEditorialAssetCandidateImporterError,
        match="single-link",
    ):
        import_editorial_assets_to_candidate(
            prepared.work_order_path,
            repo_root=prepared.root,
            as_of=AS_OF,
        )

    intake.unlink()
    duplicate.unlink()
    source = prepared.root / prepared.asset["variants"][0]["path"]
    try:
        os.symlink(source, intake)
    except (OSError, NotImplementedError):
        return
    with pytest.raises(
        DesignEditorialAssetCandidateImporterError,
        match="symlink or reparse",
    ):
        import_editorial_assets_to_candidate(
            prepared.work_order_path,
            repo_root=prepared.root,
            as_of=AS_OF,
        )


def test_atomic_replace_failure_rolls_back_complete_candidate_batch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prepared = _prepare_import_repo(tmp_path)
    _allow_source_bound_verification(monkeypatch)
    before = _candidate_summary(prepared)
    original_replace = Path.replace
    triggered = False

    def fail_second_staged_replace(path: Path, target: Path) -> Path:
        nonlocal triggered
        if not triggered and path.name.startswith("01-") and Path(target).suffix.casefold() == ".webp":
            triggered = True
            raise OSError("simulated second atomic replace failure")
        return original_replace(path, target)

    monkeypatch.setattr(Path, "replace", fail_second_staged_replace)
    with pytest.raises(
        DesignEditorialAssetCandidateImporterError,
        match="baseline was restored",
    ):
        import_editorial_assets_to_candidate(
            prepared.work_order_path,
            repo_root=prepared.root,
            as_of=AS_OF,
        )

    assert triggered is True
    assert _candidate_summary(prepared) == before
    assert not (prepared.candidate_root / DEFAULT_RECEIPT_NAME).exists()
    assert not list(prepared.candidate_root.glob(".editorial-import-*"))


def test_schema_is_exact_non_authoritative_and_privacy_safe() -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    verification_schema = json.loads(VERIFICATION_SCHEMA_PATH.read_text(encoding="utf-8"))
    assert schema["additionalProperties"] is False
    assert schema["$defs"]["authority"]["additionalProperties"] is False
    assert schema["$defs"]["importRecord"]["additionalProperties"] is False
    authority = schema["$defs"]["authority"]["properties"]
    assert authority["canonical_website_mutation"]["const"] == "never"
    assert authority["transformations"]["const"] == "none"
    assert authority["release_eligible"]["const"] is False
    assert authority["package_authority"]["const"] == "none"
    assert authority["deployment_authority"]["const"] == "none"
    assert authority["credential_access"]["const"] == "none"
    assert authority["network_access"]["const"] == "none"
    assert authority["connector_access"]["const"] == "none"
    assert schema["properties"]["receipt_authority"]["const"] is False
    assert schema["properties"]["release_eligible"]["const"] is False
    assert (
        schema["$defs"]["provenanceBinding"]["properties"]["global_artwork_policy_state"]["const"]
        == "not-cleared"
    )
    assert verification_schema["additionalProperties"] is False
    assert verification_schema["properties"]["release_eligible"]["const"] is False
    assert verification_schema["properties"]["package_authority"]["const"] == "none"
    assert verification_schema["properties"]["deployment_authority"]["const"] == "none"
    assert verification_schema["$defs"]["receiptBinding"]["properties"]["persisted"]["const"] is True


def test_json_schema_accepts_a_complete_import_receipt_when_validator_available(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    jsonschema = pytest.importorskip("jsonschema")
    prepared = _prepare_import_repo(tmp_path)
    _allow_source_bound_verification(monkeypatch)
    receipt = import_editorial_assets_to_candidate(
        prepared.work_order_path,
        repo_root=prepared.root,
        as_of=AS_OF,
        now=NOW,
    )
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator.check_schema(schema)
    jsonschema.Draft202012Validator(
        schema,
        format_checker=jsonschema.FormatChecker(),
    ).validate(receipt)
    verification = verify_candidate_editorial_asset_import(
        receipt,
        repo_root=prepared.root,
        as_of=AS_OF,
        verified_at=NOW,
    )
    verification_schema = json.loads(VERIFICATION_SCHEMA_PATH.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator.check_schema(verification_schema)
    jsonschema.Draft202012Validator(
        verification_schema,
        format_checker=jsonschema.FormatChecker(),
    ).validate(verification)

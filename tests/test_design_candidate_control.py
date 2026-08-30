"""Focused safety guarantees for staged autonomous website design candidates."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource

from aureon.operator import design_candidate_control as candidate_control
from aureon.operator import design_candidate_motion_policy_compiler as motion_policy_compiler
from aureon.operator import design_candidate_test_evidence as candidate_evidence
from aureon.operator import design_candidate_test_policy_compiler as test_policy_compiler
from aureon.operator import design_motion_performance_budget as motion_budget
from aureon.operator import secure_immutable_artifact
from aureon.operator.design_candidate_claim_surface import evaluate_candidate_claim_surface
from aureon.operator.design_candidate_control import (
    NON_AUTHORITATIVE_AUTHORITY,
    DesignCandidateControlError,
    create_design_work_order,
    stage_design_candidate,
    validate_design_candidate,
    verify_candidate_receipt_for_current_site,
    verify_design_work_order,
    verify_staged_candidate_receipt,
    write_design_candidate_receipt,
    write_design_work_order,
)
from aureon.operator.design_candidate_source_closure import build_source_closure
from aureon.operator.live_surface_reconciliation import (
    reconcile_live_surface,
    write_live_surface_reconciliation,
)
from aureon.operator.owner_source_reconciliation import (
    OWNER_SOURCE_RECONCILIATION_AUTHORITY,
    OWNER_VERIFIED_LIVE_BACKUP_RECONCILIATION_AUTHORITY,
    OWNER_VERIFIED_LIVE_BACKUP_RECONCILIATION_SCHEMA,
)

NOW = datetime(2026, 7, 28, 10, 0, tzinfo=UTC)
REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_CLOSURE_PATHS = tuple(str(row["path"]) for row in build_source_closure(REPO_ROOT)["files"])
SEALED_COMPILER_PATHS = (
    "aureon/operator/design_candidate_test_policy_compiler.py",
    "aureon/operator/design_candidate_motion_policy_compiler.py",
)


def _candidate_control_schema_errors(
    definition: str,
    payload: object,
) -> list[Any]:
    schema = json.loads(
        (
            REPO_ROOT / "docs" / "research" / "schemas" / "AUREON_DESIGN_CANDIDATE_CONTROL_V2.schema.json"
        ).read_text(encoding="utf-8")
    )
    definition_schema = {
        "$schema": schema["$schema"],
        "$ref": f"#/$defs/{definition}",
        "$defs": schema["$defs"],
    }
    claim_surface_schema = json.loads(
        (
            REPO_ROOT
            / "docs"
            / "research"
            / "schemas"
            / "AUREON_DESIGN_CANDIDATE_CLAIM_SURFACE_V1.schema.json"
        ).read_text(encoding="utf-8")
    )
    registry = Registry().with_resource(
        claim_surface_schema["$id"],
        Resource.from_contents(claim_surface_schema),
    )
    Draft202012Validator.check_schema(definition_schema)
    validator = Draft202012Validator(
        definition_schema,
        registry=registry,
        format_checker=FormatChecker(),
    )
    return sorted(
        validator.iter_errors(payload),
        key=lambda error: (
            tuple(str(part) for part in error.absolute_path),
            tuple(str(part) for part in error.absolute_schema_path),
        ),
    )


def _assert_candidate_control_schema_valid(
    definition: str,
    payload: object,
) -> None:
    errors = _candidate_control_schema_errors(definition, payload)
    assert not errors, "\n".join(
        f"{'/'.join(str(part) for part in error.absolute_path)}: {error.message}" for error in errors
    )


def test_candidate_control_immutable_write_never_replaces_a_concurrent_writer(
    tmp_path: Path,
) -> None:
    target = tmp_path / "candidate" / "work-order.v4.json"
    payloads = [{"writer": "one"}, {"writer": "two"}]

    def write(payload: dict[str, str]) -> str:
        try:
            candidate_control._atomic_write_json(  # noqa: SLF001 - immutability boundary
                target,
                payload,
            )
        except DesignCandidateControlError:
            return "blocked"
        return "written"

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(write, payloads))

    assert sorted(results) == ["blocked", "written"]
    assert json.loads(target.read_text(encoding="utf-8")) in payloads


def test_candidate_manifest_rejects_an_outside_directory_link_before_hashing(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    outside = tmp_path / "outside"
    _fake_repo(repo)
    _write(outside / "must-not-enter-baseline.txt", "outside\n")
    linked = repo / "website" / "linked-outside"
    try:
        os.symlink(outside, linked, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"Directory symlink or junction-style reparse points are unavailable: {exc}")

    with pytest.raises(
        DesignCandidateControlError,
        match="symbolic links or reparse points",
    ):
        candidate_control._file_manifest(  # noqa: SLF001 - tree boundary under test
            repo / "website"
        )


def test_candidate_manifest_must_remain_stable_through_receipt_construction(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _fake_repo(tmp_path)
    order = _order(tmp_path, "manifest-stability", ["styles.css"])
    candidate_root = _stage(tmp_path, order)
    candidate_site = candidate_root / "website"
    candidate_stylesheet = candidate_site / "styles.css"
    candidate_stylesheet.write_text(
        "body { color: #234567; }\n",
        encoding="utf-8",
    )
    original_manifest = candidate_control._file_manifest
    candidate_reads = 0

    def manifest_with_concurrent_mutation(root: Path) -> list[dict]:
        nonlocal candidate_reads
        rows = original_manifest(root)
        if root.resolve() == candidate_site.resolve():
            candidate_reads += 1
            if candidate_reads == 1:
                candidate_stylesheet.write_text(
                    "body { color: #345678; }\n",
                    encoding="utf-8",
                )
        return rows

    monkeypatch.setattr(
        candidate_control,
        "_file_manifest",
        manifest_with_concurrent_mutation,
    )
    receipt = validate_design_candidate(
        order,
        claim_impacts=[_declaration("styles.css")],
        repo_root=tmp_path,
        now=NOW,
    )

    assert receipt["passed"] is False
    assert _check(receipt, "candidate-manifest-stable")["passed"] is False
    assert candidate_reads >= 2


def test_staged_candidate_manifest_cannot_admit_an_outside_directory_link(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    outside = tmp_path / "outside"
    _fake_repo(repo)
    order = _order(repo, "candidate-linked-tree", ["styles.css"])
    candidate_root = _stage(repo, order)
    _write(outside / "must-not-enter-candidate.txt", "outside\n")
    linked = candidate_root / "website" / "linked-outside"
    try:
        os.symlink(outside, linked, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"Directory symlink or junction-style reparse points are unavailable: {exc}")

    receipt = validate_design_candidate(
        order,
        claim_impacts=[],
        repo_root=repo,
        now=NOW,
    )

    assert receipt["passed"] is False
    assert _check(receipt, "candidate-manifest")["passed"] is False
    assert _check(receipt, "candidate-manifest-stable")["passed"] is False
    assert all(row.get("path") != "linked-outside/must-not-enter-candidate.txt" for row in receipt["changes"])


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _fake_repo(root: Path) -> None:
    _write(root / "pyproject.toml", "[tool.pytest.ini_options]\n")
    (root / "aureon" / "operator").mkdir(parents=True)
    for relative in SOURCE_CLOSURE_PATHS:
        destination = root / Path(relative)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(REPO_ROOT / Path(relative), destination)
    _write(root / "aureon" / "operator" / "website_operator.defaults.json", '{"policy":"test"}\n')
    _write(root / "website" / ".htaccess", "Options -Indexes\n")
    _write(
        root / "website" / "index.html",
        "<!doctype html><title>Aureon</title><p>Evidence, boundary and human review. "
        "This fixture is not evidence of customer adoption or independent validation.</p>\n",
    )
    _write(root / "website" / "styles.css", "body { color: #123456; }\n")
    _write(root / "website" / "data" / "other.json", '{"status":"source"}\n')
    register = {
        "schema": "aureon.public-claim-evidence-register.v1",
        "generated_at": "2026-07-28T10:00:00Z",
        "scope": "material public website positioning claims",
        "authority": {
            "scope": "read-only public-claim evidence control",
            "release_eligible": False,
            "deployment_authority": "none",
            "package_authority": "none",
            "human_review": "required for material public wording changes",
        },
        "claims": [
            {
                "id": "homepage-claim",
                "title": "Test homepage positioning",
                "claim": "Aureon is an evidence-led test company.",
                "state": "company-authored",
                "boundary": "This fixture is not evidence of customer adoption or independent validation.",
                "permitted_wording": ["Aureon is an evidence-led test company."],
                "prohibited_inferences": ["customer adoption", "independent validation"],
                "expires_on": "2027-07-28",
                "source": {
                    "path": "website/index.html",
                    "sha256": _sha256(root / "website" / "index.html"),
                    "locator": "fixture:index",
                    "evidence_texts": ["Aureon", "boundary"],
                    "boundary_text": "This fixture is not evidence of customer adoption or independent validation.",
                },
                "public_routes": ["/"],
            }
        ],
    }
    _write(
        root / "data" / "website_operator" / "public_claim_evidence_register.v1.json",
        json.dumps(register, indent=2) + "\n",
    )


class _Response:
    status = 200
    headers = {"Content-Type": "text/html"}

    def __init__(self, body: bytes, url: str) -> None:
        self.body = body
        self.url = url

    def geturl(self) -> str:
        return self.url

    def read(self, amount: int = -1) -> bytes:
        return self.body if amount < 0 else self.body[:amount]

    def close(self) -> None:
        return None


def _aligned_reconciliation(root: Path, run_id: str) -> Path:
    source = (root / "website" / "index.html").read_bytes()
    receipt = reconcile_live_surface(
        repo_root=root,
        site_root=root / "website",
        base_url="https://example.test/",
        routes=["index.html"],
        now=NOW,
        opener=lambda request, timeout: _Response(source, request.full_url),
    )
    return write_live_surface_reconciliation(
        receipt,
        root / "artifacts" / "website-operator" / f"{run_id}-alignment.json",
        repo_root=root,
    )


def _drift_reconciliation(root: Path, run_id: str) -> Path:
    source = (root / "website" / "index.html").read_bytes()
    live = source.replace(b"Evidence", b"Different production")
    receipt = reconcile_live_surface(
        repo_root=root,
        site_root=root / "website",
        base_url="https://example.test/",
        routes=["index.html"],
        now=NOW,
        opener=lambda request, timeout: _Response(live, request.full_url),
    )
    assert receipt["state"] == "live-drift-detected"
    return write_live_surface_reconciliation(
        receipt,
        root / "artifacts" / "website-operator" / f"{run_id}-drift.json",
        repo_root=root,
    )


def _owner_source_decision(root: Path, reconciliation_path: Path, run_id: str) -> tuple[Path, Path]:
    reconciliation = json.loads(reconciliation_path.read_text(encoding="utf-8"))
    now = datetime.now(UTC)
    backup = {
        "schema": "aureon.website-operator.backup.v1",
        "state": "verified-backup",
        "observed_at": (now - timedelta(minutes=1)).isoformat().replace("+00:00", "Z"),
        "remote_root": "/",
        "tree_sha256": "B" * 64,
    }
    backup_path = root / "artifacts" / "website-operator" / f"{run_id}-backup.json"
    _write(backup_path, json.dumps(backup, indent=2) + "\n")
    decision = {
        "schema": "aureon.owner-source-reconciliation-decision.v1",
        "decision": "approved",
        "scope": "successor-staged-design-candidate",
        "source_selection": "retain-local-canonical-source",
        "reconciliation_receipt_sha256": _sha256(reconciliation_path),
        "reconciliation_selected_tree_sha256": reconciliation["canonical"]["selected_tree_sha256"],
        "backup_receipt_sha256": _sha256(backup_path),
        "backup_tree_sha256": backup["tree_sha256"],
        "approved_at": now.isoformat().replace("+00:00", "Z"),
        "expires_at": (now + timedelta(hours=1)).isoformat().replace("+00:00", "Z"),
        "approved_by": "Aureon owner",
        "note": "Local source may be used only for this staged candidate; the production record is preserved by backup.",
        "authority": dict(OWNER_SOURCE_RECONCILIATION_AUTHORITY),
    }
    decision_path = (
        root / "artifacts" / "website-operator" / "owner-source-reconciliations" / f"{run_id}.json"
    )
    _write(decision_path, json.dumps(decision, indent=2) + "\n")
    return decision_path, backup_path


def _verified_live_backup_decision(
    root: Path,
    reconciliation_path: Path,
    run_id: str,
) -> tuple[Path, Path, Path, Path]:
    reconciliation = json.loads(reconciliation_path.read_text(encoding="utf-8"))
    backup_root = (root / "artifacts" / "homepl-backups" / run_id / "document-root").resolve()
    backup_root.mkdir(parents=True)
    shutil.copytree(root / "website", backup_root, dirs_exist_ok=True)
    _write(
        backup_root / "index.html",
        "<!doctype html><title>Live Aureon</title><p>Verified production record.</p>\n",
    )
    _write(backup_root / "styles.css", "body { color: #765432; }\n")
    rows = candidate_control._file_manifest(backup_root)  # noqa: SLF001 - source contract fixture
    manifest_path = (root / "artifacts" / "website-operator" / f"{run_id}-backup-manifest.csv").resolve()
    manifest_lines = ["Path,Bytes,Sha256"]
    manifest_lines.extend(f"{row['path']},{row['bytes']},{row['sha256']}" for row in rows)
    _write(manifest_path, "\n".join(manifest_lines) + "\n")
    now = datetime.now(UTC)
    backup = {
        "schema": "aureon.website-operator.backup.v1",
        "state": "verified-backup",
        "observed_at": (now - timedelta(minutes=1)).isoformat().replace("+00:00", "Z"),
        "method": "homepl-ftps",
        "source_assertion": "Authenticated Home.pl document-root download",
        "remote_root": "/",
        "backup_directory": str(backup_root),
        "manifest": str(manifest_path),
        "manifest_sha256": _sha256(manifest_path),
        "tree_sha256": candidate_control._website_operator_tree_hash(  # noqa: SLF001
            backup_root, rows
        ),
        "file_count": len(rows),
        "total_bytes": sum(row["bytes"] for row in rows),
    }
    backup_path = root / "artifacts" / "website-operator" / f"{run_id}-backup.json"
    _write(backup_path, json.dumps(backup, indent=2) + "\n")
    decision = {
        "schema": OWNER_VERIFIED_LIVE_BACKUP_RECONCILIATION_SCHEMA,
        "decision": "approved",
        "scope": "successor-staged-design-candidate",
        "source_selection": "use-verified-live-backup",
        "reconciliation_receipt_sha256": _sha256(reconciliation_path),
        "reconciliation_selected_tree_sha256": reconciliation["canonical"]["selected_tree_sha256"],
        "backup_receipt_sha256": _sha256(backup_path),
        "backup_tree_sha256": backup["tree_sha256"],
        "backup_directory": backup["backup_directory"],
        "backup_manifest": backup["manifest"],
        "backup_manifest_sha256": backup["manifest_sha256"],
        "approved_at": now.isoformat().replace("+00:00", "Z"),
        "expires_at": (now + timedelta(hours=1)).isoformat().replace("+00:00", "Z"),
        "approved_by": "Aureon owner",
        "note": "The exact fresh verified live backup is selected only for this staged candidate.",
        "authority": dict(OWNER_VERIFIED_LIVE_BACKUP_RECONCILIATION_AUTHORITY),
    }
    decision_path = (
        root / "artifacts" / "website-operator" / "owner-source-reconciliations" / f"{run_id}.json"
    )
    _write(decision_path, json.dumps(decision, indent=2) + "\n")
    return decision_path, backup_path, backup_root, manifest_path


def _rebind_verified_live_backup(
    decision_path: Path,
    backup_path: Path,
    backup_root: Path,
    manifest_path: Path,
) -> None:
    rows = candidate_control._file_manifest(backup_root)  # noqa: SLF001
    manifest_lines = ["Path,Bytes,Sha256"]
    manifest_lines.extend(f"{row['path']},{row['bytes']},{row['sha256']}" for row in rows)
    _write(manifest_path, "\n".join(manifest_lines) + "\n")
    backup = json.loads(backup_path.read_text(encoding="utf-8"))
    backup.update(
        {
            "manifest_sha256": _sha256(manifest_path),
            "tree_sha256": candidate_control._website_operator_tree_hash(  # noqa: SLF001
                backup_root, rows
            ),
            "file_count": len(rows),
            "total_bytes": sum(row["bytes"] for row in rows),
        }
    )
    backup_path.write_text(json.dumps(backup, indent=2) + "\n", encoding="utf-8")
    decision = json.loads(decision_path.read_text(encoding="utf-8"))
    decision.update(
        {
            "backup_receipt_sha256": _sha256(backup_path),
            "backup_tree_sha256": backup["tree_sha256"],
            "backup_manifest_sha256": backup["manifest_sha256"],
        }
    )
    decision_path.write_text(json.dumps(decision, indent=2) + "\n", encoding="utf-8")


def _live_backup_order(
    root: Path,
    run_id: str,
) -> tuple[Path, Path, Path, Path, Path]:
    reconciliation = _drift_reconciliation(root, run_id)
    decision, backup, backup_root, manifest = _verified_live_backup_decision(root, reconciliation, run_id)
    order = create_design_work_order(
        goal="Refine the owner-selected verified production record.",
        allowed_paths=["styles.css"],
        routes=["/"],
        reconciliation_receipt=reconciliation,
        owner_source_decision=decision,
        backup_receipt=backup,
        run_id=run_id,
        repo_root=root,
        now=NOW,
    )
    order_path = write_design_work_order(
        order,
        root / "artifacts" / "website-candidates" / "work-orders" / f"{run_id}.v4.json",
        repo_root=root,
    )
    return order_path, decision, backup, backup_root, manifest


def _order(root: Path, run_id: str, allowed_paths: list[str]) -> Path:
    order = create_design_work_order(
        goal="Refine one bounded investor-facing route.",
        allowed_paths=allowed_paths,
        routes=["/"],
        reconciliation_receipt=_aligned_reconciliation(root, run_id),
        run_id=run_id,
        repo_root=root,
        now=NOW,
    )
    return write_design_work_order(
        order,
        root / "artifacts" / "website-candidates" / "work-orders" / f"{run_id}.v4.json",
        repo_root=root,
    )


def _stage(root: Path, order: Path) -> Path:
    stage_design_candidate(order, repo_root=root)
    payload = json.loads(order.read_text(encoding="utf-8"))
    return root / payload["candidate_layout"]["root"]


def _declaration(path: str, *, material: bool = False) -> dict[str, str]:
    return {
        "path": path,
        "classification": "material-claim-change" if material else "no-material-claim-change",
        "rationale": "The bounded staged change was reviewed for its public claim impact.",
    }


def _valid_candidate_receipt(
    root: Path,
    *,
    run_id: str,
) -> tuple[dict[str, Any], Path]:
    _fake_repo(root)
    shutil.copy2(
        REPO_ROOT / candidate_control.DEFAULT_OPERATOR_CONFIG,
        root / candidate_control.DEFAULT_OPERATOR_CONFIG,
    )
    order = _order(root, run_id, ["styles.css"])
    candidate_root = _stage(root, order)
    (candidate_root / "website" / "styles.css").write_text(
        "body { color: #234567; }\n",
        encoding="utf-8",
    )
    receipt = validate_design_candidate(
        order,
        claim_impacts=[_declaration("styles.css")],
        repo_root=root,
        now=NOW,
    )
    assert receipt["passed"] is True
    return receipt, candidate_root / "candidate.v1.json"


def _prepare_sealed_compiler_inputs(root: Path) -> None:
    for relative in (
        "aureon/operator/design_candidate_static_qa.py",
        "tools/aureon_candidate_javascript_syntax_v1.js",
        "tools/aureon_website_design_audit_v28.js",
        "tools/aureon_metadata_ethos_audit_v28.js",
        "skills/aureon-harmonic-design-suite/references/design-doctrine.md",
    ):
        destination = root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(REPO_ROOT / relative, destination)
    (root / "artifacts" / "website-operator" / "motion-performance-budget").mkdir(
        parents=True,
        exist_ok=True,
    )


def _run_sealed_compiler(
    root: Path,
    compiler_path: str,
    *,
    run_id: str,
) -> subprocess.CompletedProcess[str]:
    environment = {
        key: value for key, value in os.environ.items() if key.upper() not in {"PYTHONHOME", "PYTHONSTARTUP"}
    }
    environment["PYTHONPATH"] = str(root / "ambient-import-poison")
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run(
        [
            sys.executable,
            "-I",
            "-S",
            "-B",
            str(root / compiler_path),
            "--candidate-receipt",
            f"artifacts/website-candidates/{run_id}/candidate.v1.json",
        ],
        cwd=root,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
        timeout=90,
    )


def test_sealed_compiler_ingresses_reject_all_transitive_source_mutations_before_execution(
    tmp_path: Path,
) -> None:
    run_id = "sealed-source-closure"
    receipt, receipt_path = _valid_candidate_receipt(tmp_path, run_id=run_id)
    write_design_candidate_receipt(receipt, receipt_path, repo_root=tmp_path)
    _prepare_sealed_compiler_inputs(tmp_path)
    manifest = receipt["source_closure"]
    source_paths = [str(row["path"]) for row in manifest["files"]]
    original_hashes = {
        relative: hashlib.sha256((tmp_path / relative).read_bytes()).hexdigest().upper()
        for relative in source_paths
    }

    for compiler_path in SEALED_COMPILER_PATHS:
        baseline = _run_sealed_compiler(tmp_path, compiler_path, run_id=run_id)
        assert baseline.returncode == 0, baseline.stderr
        assert json.loads(baseline.stdout)["passed"] is True

        for relative in source_paths:
            if relative == compiler_path:
                continue
            target = tmp_path / relative
            original = target.read_bytes()
            marker = tmp_path / ("marker-" + Path(compiler_path).stem + "-" + relative.replace("/", "_"))
            injection = (
                "\nfrom pathlib import Path as _AureonMarkerPath\n"
                f"_AureonMarkerPath({str(marker)!r}).write_text("
                "'executed', encoding='utf-8')\n"
            ).encode()
            target.write_bytes(original + injection)
            try:
                blocked = _run_sealed_compiler(
                    tmp_path,
                    compiler_path,
                    run_id=run_id,
                )
                assert blocked.returncode != 0
                assert not marker.exists()
            finally:
                target.write_bytes(original)
                if marker.exists():
                    marker.unlink()

    added = tmp_path / "aureon" / "operator" / "design_candidate_added_probe.py"
    added_marker = tmp_path / "new-import-marker"
    control = tmp_path / "aureon" / "operator" / "design_candidate_control.py"
    original_control = control.read_bytes()
    added.write_text(
        f"from pathlib import Path\nPath({str(added_marker)!r}).write_text('executed', encoding='utf-8')\n",
        encoding="utf-8",
    )
    control.write_bytes(original_control + b"\nfrom aureon.operator import design_candidate_added_probe\n")
    try:
        for compiler_path in SEALED_COMPILER_PATHS:
            blocked = _run_sealed_compiler(
                tmp_path,
                compiler_path,
                run_id=run_id,
            )
            assert blocked.returncode != 0
            assert not added_marker.exists()
    finally:
        control.write_bytes(original_control)
        added.unlink()
        if added_marker.exists():
            added_marker.unlink()

    assert {
        relative: hashlib.sha256((tmp_path / relative).read_bytes()).hexdigest().upper()
        for relative in source_paths
    } == original_hashes


def test_sealed_verify_only_compiler_processes_are_exactly_read_only(
    tmp_path: Path,
) -> None:
    run_id = "sealed-read-only-verifiers"
    receipt, receipt_path = _valid_candidate_receipt(tmp_path, run_id=run_id)
    write_design_candidate_receipt(receipt, receipt_path, repo_root=tmp_path)
    _prepare_sealed_compiler_inputs(tmp_path)

    motion_compilation = motion_policy_compiler.compile_candidate_motion_config(
        receipt_path,
        repo_root=tmp_path,
    )
    motion_verification = motion_policy_compiler.write_compiled_candidate_motion_config(
        motion_compilation,
        repo_root=tmp_path,
    )
    test_compilation = test_policy_compiler.compile_candidate_test_policy(
        receipt_path,
        repo_root=tmp_path,
    )
    test_verification = test_policy_compiler.write_compiled_candidate_test_policy(
        test_compilation,
        repo_root=tmp_path,
    )

    def tree_snapshot() -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for path in sorted(
            tmp_path.rglob("*"),
            key=lambda candidate: candidate.relative_to(tmp_path).as_posix(),
        ):
            details = path.lstat()
            row: dict[str, Any] = {
                "path": path.relative_to(tmp_path).as_posix(),
                "kind": "directory" if path.is_dir() else "file",
                "mtime_ns": details.st_mtime_ns,
            }
            if path.is_file():
                raw = path.read_bytes()
                row.update(
                    {
                        "bytes": len(raw),
                        "sha256": hashlib.sha256(raw).hexdigest().upper(),
                    }
                )
            rows.append(row)
        return rows

    before = tree_snapshot()
    commands = (
        (
            "aureon/operator/design_candidate_motion_policy_compiler.py",
            "--verify-config",
            tmp_path / motion_verification["config_path"],
            "--expected-config-sha256",
            motion_verification["config_file_sha256"],
            motion_policy_compiler.VERIFICATION_SCHEMA,
        ),
        (
            "aureon/operator/design_candidate_test_policy_compiler.py",
            "--verify-policy",
            tmp_path / test_verification["policy_path"],
            "--expected-policy-sha256",
            test_verification["policy_file_sha256"],
            test_policy_compiler.VERIFICATION_SCHEMA,
        ),
    )
    for compiler_path, verify_flag, input_path, hash_flag, expected_hash, schema in commands:
        command = [
            sys.executable,
            "-I",
            "-S",
            "-B",
            str((tmp_path / compiler_path).resolve()),
            verify_flag,
            str(input_path.resolve()),
            hash_flag,
            expected_hash,
            "--candidate-receipt",
            str(receipt_path.resolve()),
        ]
        completed = subprocess.run(
            command,
            cwd=tmp_path,
            shell=False,
            check=False,
            capture_output=True,
            text=False,
            timeout=300,
        )
        assert completed.returncode == 0
        assert completed.stderr == b""
        payload = json.loads(completed.stdout)
        canonical = (
            json.dumps(
                payload,
                ensure_ascii=False,
                allow_nan=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
            + b"\n"
        )
        assert completed.stdout == canonical
        assert completed.stdout.endswith(b"\n") and not completed.stdout.endswith(b"\n\n")
        assert payload["schema"] == schema
        assert payload["passed"] is True

    assert tree_snapshot() == before


def _claim_surface_context(
    *,
    route_id: str = "homepage",
    route: str = "/",
) -> dict[str, Any]:
    capsule = {
        "route_id": route_id,
        "route": route,
        "claims": [
            {
                "id": "homepage-claim",
                "claim": "Aureon is an evidence-led test company.",
                "boundary": "This fixture is not evidence of customer adoption or independent validation.",
                "permitted_wording": ["Aureon is an evidence-led test company."],
                "prohibited_inferences": ["customer adoption", "independent validation"],
            }
        ],
    }
    return {
        "id": route_id,
        "route": route,
        "allowed_paths": ["styles.css"],
        "claim_capsule": capsule,
        "claim_capsule_sha256": candidate_control._json_hash(capsule),  # noqa: SLF001
    }


def _valid_required_claim_surface_receipt(
    root: Path,
    *,
    run_id: str,
) -> tuple[dict[str, Any], Path]:
    _fake_repo(root)
    shutil.copy2(
        REPO_ROOT / candidate_control.DEFAULT_OPERATOR_CONFIG,
        root / candidate_control.DEFAULT_OPERATOR_CONFIG,
    )
    order = _order(root, run_id, ["styles.css"])
    candidate_root = _stage(root, order)
    (candidate_root / "website" / "styles.css").write_text(
        "body { color: #234567; }\n",
        encoding="utf-8",
    )
    receipt = validate_design_candidate(
        order,
        claim_impacts=[_declaration("styles.css")],
        claim_surface_context=_claim_surface_context(),
        claim_surface_manifest=[],
        repo_root=root,
        now=NOW,
    )
    assert receipt["passed"] is True
    assert receipt["claim_surface"]["required"] is True
    return receipt, candidate_root / "candidate.v1.json"


def _copy_real_candidate_compiler_sources(root: Path) -> None:
    sources = (
        (Path(str(test_policy_compiler.__file__)), test_policy_compiler.COMPILER_TOOL_PATH),
        (Path(str(motion_policy_compiler.__file__)), motion_policy_compiler.COMPILER_PATH),
        (Path(str(candidate_evidence.__file__)), test_policy_compiler.TEST_EVIDENCE_TOOL_PATH),
        (Path(str(motion_budget.__file__)), motion_policy_compiler.MOTION_IMPLEMENTATION_PATH),
        (Path(str(secure_immutable_artifact.__file__)), test_policy_compiler.SECURE_WRITER_TOOL_PATH),
        (Path(str(candidate_control.__file__)), test_policy_compiler.CANDIDATE_CONTROL_TOOL_PATH),
    )
    for source, relative in sources:
        destination = root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)


def _assert_both_real_compilers_reject(
    *,
    root: Path,
    receipt_path: Path,
    receipt: dict[str, Any],
    message: str,
) -> None:
    _copy_real_candidate_compiler_sources(root)
    _write(receipt_path, json.dumps(receipt, indent=2, allow_nan=True) + "\n")
    with pytest.raises(
        test_policy_compiler.DesignCandidateTestPolicyCompilerError,
        match=message,
    ):
        test_policy_compiler.compile_candidate_test_policy(receipt_path, repo_root=root)
    with pytest.raises(
        motion_policy_compiler.DesignCandidateMotionPolicyCompilerError,
        match=message,
    ):
        motion_policy_compiler.compile_candidate_motion_config(receipt_path, repo_root=root)


def _tamper_candidate_receipt(receipt: dict[str, Any], variant: str) -> None:
    if variant == "claims":
        receipt["claims"]["release_authority"] = "granted"
    elif variant == "claim-surface":
        receipt["claim_surface"]["release_authority"] = "granted"
    elif variant == "appended-check":
        receipt["checks"].append(
            {
                "id": "worker-release-authority",
                "passed": True,
                "message": "Worker-injected authority must never survive receipt replay.",
                "evidence": {"release_authority": "granted"},
            }
        )
    elif variant == "work-order":
        receipt["work_order"]["release_authority"] = "granted"
    elif variant == "candidate":
        receipt["candidate"]["release_authority"] = "granted"
    elif variant == "validated-at":
        receipt["validated_at"] = {"release_authority": "granted"}
    elif variant == "next-gate":
        receipt["next_gate"] = {"release_authority": "granted"}
    elif variant == "top-level":
        receipt["worker_release_authority"] = "granted"
    elif variant == "change":
        receipt["changes"][0]["release_authority"] = "granted"
    elif variant == "authority":
        receipt["authority"]["release_authority"] = "granted"
    else:
        raise AssertionError(f"Unknown candidate receipt tamper variant: {variant}")


def _tamper_work_order_contract(order: dict[str, Any], variant: str) -> None:
    if variant == "created-at-object":
        order["created_at"] = {"release_authority": "granted"}
    elif variant == "baseline-extra":
        order["baseline"]["release_authority"] = "granted"
    elif variant == "claim-control-extra":
        order["claim_control"]["release_authority"] = "granted"
    elif variant == "test-policy-extra":
        order["test_policy"]["release_authority"] = "granted"
    elif variant == "manifest-bytes-bool":
        order["baseline"]["files"][0]["bytes"] = True
    elif variant == "general-nested-extra":
        order["candidate_layout"]["release_authority"] = "granted"
    else:
        raise AssertionError(f"Unknown work-order tamper variant: {variant}")


def _refresh_staged_register(candidate_root: Path) -> None:
    register_path = candidate_root / "claim-evidence" / "public_claim_evidence_register.v1.json"
    register = json.loads(register_path.read_text(encoding="utf-8"))
    register["generated_at"] = "2026-07-28T10:05:00Z"
    register["claims"][0]["source"]["sha256"] = _sha256(candidate_root / "website" / "index.html")
    register_path.write_text(json.dumps(register, indent=2) + "\n", encoding="utf-8")


def _check(receipt: dict, identifier: str) -> dict:
    return next(item for item in receipt["checks"] if item["id"] == identifier)


@pytest.mark.parametrize(
    "variant",
    [
        "created-at-object",
        "baseline-extra",
        "claim-control-extra",
        "test-policy-extra",
        "manifest-bytes-bool",
        "general-nested-extra",
    ],
)
def test_work_order_recursive_contract_rejects_before_persistence_and_at_load(
    tmp_path: Path,
    variant: str,
) -> None:
    root = tmp_path / "repo"
    _fake_repo(root)
    run_id = f"work-order-{variant}"
    order = create_design_work_order(
        goal="Refine one bounded investor-facing route.",
        allowed_paths=["styles.css"],
        routes=["/"],
        reconciliation_receipt=_aligned_reconciliation(root, run_id),
        run_id=run_id,
        repo_root=root,
        now=NOW,
    )
    _tamper_work_order_contract(order, variant)

    assert _candidate_control_schema_errors("workOrder", order)
    with pytest.raises(DesignCandidateControlError):
        candidate_control.require_design_work_order_contract(order)
    verification = verify_design_work_order(order, repo_root=root)
    assert verification["passed"] is False
    assert _check(verification, "exact-v4-contract")["passed"] is False
    exact_path = root / "artifacts" / "website-candidates" / "work-orders" / f"{run_id}.v4.json"
    with pytest.raises(DesignCandidateControlError):
        write_design_work_order(order, exact_path, repo_root=root)

    _write(exact_path, json.dumps(order, indent=2, sort_keys=True) + "\n")
    with pytest.raises(DesignCandidateControlError):
        stage_design_candidate(exact_path, repo_root=root)


@pytest.mark.parametrize(
    "variant",
    [
        "created-at-object",
        "baseline-extra",
        "claim-control-extra",
        "test-policy-extra",
        "manifest-bytes-bool",
        "general-nested-extra",
    ],
)
def test_coherently_rebound_invalid_work_order_fails_validation_replay_and_both_real_compilers(
    tmp_path: Path,
    variant: str,
) -> None:
    root = tmp_path / "repo"
    receipt, receipt_path = _valid_candidate_receipt(root, run_id=f"rebound-{variant}")
    work_order_path = root / receipt["work_order"]["path"]
    order = json.loads(work_order_path.read_text(encoding="utf-8"))
    _tamper_work_order_contract(order, variant)
    work_order_raw = (json.dumps(order, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")
    work_order_path.write_bytes(work_order_raw)
    receipt["work_order"]["file_sha256"] = hashlib.sha256(work_order_raw).hexdigest().upper()
    receipt["work_order"]["sha256"] = candidate_control._json_hash(order)  # noqa: SLF001

    validation_path = root / receipt["validation_input"]["path"]
    validation_input = json.loads(validation_path.read_text(encoding="utf-8"))
    validation_input["work_order"] = dict(receipt["work_order"])
    validation_unsigned = dict(validation_input)
    validation_unsigned.pop("payload_sha256")
    validation_input["payload_sha256"] = candidate_control._json_hash(  # noqa: SLF001
        validation_unsigned
    )
    validation_raw = candidate_control._validation_input_bytes(validation_input)  # noqa: SLF001
    validation_path.write_bytes(validation_raw)
    receipt["validation_input"] = {
        "path": receipt["validation_input"]["path"],
        "file_sha256": hashlib.sha256(validation_raw).hexdigest().upper(),
        "json_sha256": candidate_control._json_hash(validation_input),  # noqa: SLF001
        "payload_sha256": validation_input["payload_sha256"],
    }

    _assert_candidate_control_schema_valid("candidateReceipt", receipt)
    candidate_control.require_candidate_receipt_contract(receipt)
    with pytest.raises(DesignCandidateControlError):
        validate_design_candidate(
            work_order_path,
            claim_impacts=[_declaration("styles.css")],
            repo_root=root,
            now=NOW,
        )
    verification = verify_staged_candidate_receipt(receipt, repo_root=root)
    assert verification["passed"] is False
    assert _check(verification, "work-order-binding")["passed"] is False
    _assert_both_real_compilers_reject(
        root=root,
        receipt_path=receipt_path,
        receipt=receipt,
        message="persisted-byte and JSON binding failed",
    )


def test_work_order_raw_byte_reformat_is_rejected_even_when_canonical_json_is_unchanged(
    tmp_path: Path,
) -> None:
    root = tmp_path / "repo"
    receipt, receipt_path = _valid_candidate_receipt(root, run_id="raw-work-order-reformat")
    work_order_path = root / receipt["work_order"]["path"]
    order = json.loads(work_order_path.read_text(encoding="utf-8"))
    original_canonical_sha256 = candidate_control._json_hash(order)  # noqa: SLF001
    work_order_path.write_text(
        json.dumps(order, separators=(",", ":"), ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )

    assert (
        candidate_control._json_hash(  # noqa: SLF001
            json.loads(work_order_path.read_text(encoding="utf-8"))
        )
        == original_canonical_sha256
    )
    with pytest.raises(DesignCandidateControlError, match="exact persisted bytes"):
        candidate_control.require_current_work_order_binding(
            receipt["work_order"],
            repo_root=root,
        )
    verification = verify_staged_candidate_receipt(receipt, repo_root=root)
    assert verification["passed"] is False
    assert _check(verification, "work-order-binding")["passed"] is False
    _assert_both_real_compilers_reject(
        root=root,
        receipt_path=receipt_path,
        receipt=receipt,
        message="persisted-byte and JSON binding failed",
    )


def test_candidate_receipt_full_replay_is_timestamp_bound_and_schema_exact(
    tmp_path: Path,
) -> None:
    receipt, _ = _valid_candidate_receipt(tmp_path, run_id="full-receipt-replay")

    _assert_candidate_control_schema_valid("candidateReceipt", receipt)
    validation_input = json.loads(
        (tmp_path / receipt["validation_input"]["path"]).read_text(encoding="utf-8")
    )
    _assert_candidate_control_schema_valid("candidateValidationInput", validation_input)
    verification = verify_staged_candidate_receipt(receipt, repo_root=tmp_path)

    assert verification["passed"] is True
    assert _check(verification, "validated-at")["passed"] is True
    replay = _check(verification, "candidate-control-revalidation")
    assert replay["passed"] is True
    assert replay["evidence"]["complete_receipt_match"] is True


@pytest.mark.parametrize(
    "variant",
    [
        "claims",
        "claim-surface",
        "appended-check",
        "work-order",
        "candidate",
        "validated-at",
        "next-gate",
        "top-level",
        "change",
        "authority",
    ],
)
def test_candidate_receipt_smuggling_fails_schema_full_replay_and_both_real_compilers(
    tmp_path: Path,
    variant: str,
) -> None:
    root = tmp_path / "repo"
    receipt, receipt_path = _valid_candidate_receipt(root, run_id=f"receipt-{variant}")
    _tamper_candidate_receipt(receipt, variant)

    assert _candidate_control_schema_errors("candidateReceipt", receipt)
    verification = verify_staged_candidate_receipt(receipt, repo_root=root)
    assert verification["passed"] is False
    assert _check(verification, "candidate-control-revalidation")["passed"] is False

    _copy_real_candidate_compiler_sources(root)
    _write(receipt_path, json.dumps(receipt, indent=2) + "\n")

    with pytest.raises(test_policy_compiler.DesignCandidateTestPolicyCompilerError) as test_exc:
        test_policy_compiler.compile_candidate_test_policy(receipt_path, repo_root=root)
    with pytest.raises(motion_policy_compiler.DesignCandidateMotionPolicyCompilerError) as motion_exc:
        motion_policy_compiler.compile_candidate_motion_config(receipt_path, repo_root=root)

    test_message = str(test_exc.value)
    motion_message = str(motion_exc.value)
    assert "Candidate receipt runtime contract failed" in test_message
    assert "Candidate receipt runtime contract failed" in motion_message


@pytest.mark.parametrize("minutes", [-1, 1, 60, 5_760])
def test_candidate_receipt_time_cannot_move_away_from_immutable_validation_input(
    tmp_path: Path,
    minutes: int,
) -> None:
    root = tmp_path / "repo"
    receipt, receipt_path = _valid_candidate_receipt(root, run_id=f"time-shift-{abs(minutes)}")
    original = datetime.fromisoformat(receipt["validated_at"].replace("Z", "+00:00"))
    receipt["validated_at"] = (original + timedelta(minutes=minutes)).isoformat().replace("+00:00", "Z")

    _assert_candidate_control_schema_valid("candidateReceipt", receipt)
    candidate_control.require_candidate_receipt_contract(receipt)
    verification = verify_staged_candidate_receipt(receipt, repo_root=root)

    assert verification["passed"] is False
    assert _check(verification, "validation-input-binding")["passed"] is True
    assert _check(verification, "validated-at")["passed"] is False
    _assert_both_real_compilers_reject(
        root=root,
        receipt_path=receipt_path,
        receipt=receipt,
        message="Full staged-candidate and work-order verification did not pass",
    )


@pytest.mark.parametrize(
    "variant",
    [
        "check-passed",
        "claim-surface-required",
        "authority-release-eligible",
    ],
)
def test_candidate_receipt_bool_integer_substitutions_fail_type_strict_contract_and_compilers(
    tmp_path: Path,
    variant: str,
) -> None:
    root = tmp_path / "repo"
    receipt, receipt_path = _valid_candidate_receipt(root, run_id=f"bool-int-{variant}")
    if variant == "check-passed":
        receipt["checks"][0]["passed"] = 1
    elif variant == "claim-surface-required":
        receipt["claim_surface"]["required"] = 0
    else:
        receipt["authority"]["release_eligible"] = 0

    assert _candidate_control_schema_errors("candidateReceipt", receipt)
    with pytest.raises(DesignCandidateControlError):
        candidate_control.require_candidate_receipt_contract(receipt)
    verification = verify_staged_candidate_receipt(receipt, repo_root=root)
    assert verification["passed"] is False
    assert _check(verification, "schema")["passed"] is False
    _assert_both_real_compilers_reject(
        root=root,
        receipt_path=receipt_path,
        receipt=receipt,
        message="Candidate receipt runtime contract failed",
    )


def test_required_claim_surface_cannot_be_rebased_to_receipt_supplied_context(
    tmp_path: Path,
) -> None:
    root = tmp_path / "repo"
    receipt, receipt_path = _valid_required_claim_surface_receipt(
        root,
        run_id="claim-context-source",
    )
    alternate = _claim_surface_context(route_id="alternate", route="/alternate")
    alternate_result = evaluate_candidate_claim_surface(
        baseline_site=root / "website",
        candidate_site=root / receipt["candidate"]["website_path"],
        changed_paths=["styles.css"],
        context=alternate,
        manifest=[],
    )
    assert alternate_result["passed"] is True
    receipt["claim_surface"] = {
        "required": True,
        "state": "pass",
        "binding": alternate,
        "manifest": alternate_result["manifest"],
        "result": alternate_result,
    }

    _assert_candidate_control_schema_valid("candidateReceipt", receipt)
    candidate_control.require_candidate_receipt_contract(receipt)
    verification = verify_staged_candidate_receipt(receipt, repo_root=root)

    assert verification["passed"] is False
    assert _check(verification, "validation-input-binding")["passed"] is True
    assert _check(verification, "candidate-control-revalidation")["passed"] is False
    _assert_both_real_compilers_reject(
        root=root,
        receipt_path=receipt_path,
        receipt=receipt,
        message="Full staged-candidate and work-order verification did not pass",
    )


@pytest.mark.parametrize(
    "variant",
    ["path", "file-sha256", "json-sha256", "payload-sha256"],
)
def test_candidate_validation_input_binding_mutation_fails_direct_and_compiler_replay(
    tmp_path: Path,
    variant: str,
) -> None:
    root = tmp_path / "repo"
    receipt, receipt_path = _valid_candidate_receipt(root, run_id=f"input-binding-{variant}")
    if variant == "path":
        receipt["validation_input"]["path"] = (
            "artifacts/website-candidates/other-run/candidate-validation-input.v1.json"
        )
    else:
        receipt["validation_input"][variant.replace("-", "_")] = "F" * 64

    _assert_candidate_control_schema_valid("candidateReceipt", receipt)
    verification = verify_staged_candidate_receipt(receipt, repo_root=root)
    assert verification["passed"] is False
    assert _check(verification, "validation-input-binding")["passed"] is False
    _assert_both_real_compilers_reject(
        root=root,
        receipt_path=receipt_path,
        receipt=receipt,
        message=(
            "validation-input path is not exact"
            if variant == "path"
            else "raw, canonical, or payload binding failed preflight"
        ),
    )


@pytest.mark.parametrize("variant", ["time", "payload", "claim-context"])
def test_candidate_validation_input_payload_mutation_fails_without_receipt_trust(
    tmp_path: Path,
    variant: str,
) -> None:
    root = tmp_path / "repo"
    if variant == "claim-context":
        receipt, receipt_path = _valid_required_claim_surface_receipt(
            root,
            run_id="input-payload-claim-context",
        )
    else:
        receipt, receipt_path = _valid_candidate_receipt(root, run_id=f"input-payload-{variant}")
    source_path = root / receipt["validation_input"]["path"]
    source = json.loads(source_path.read_text(encoding="utf-8"))
    if variant == "time":
        source["issued_at"] = "2026-08-01T00:00:00Z"
    elif variant == "payload":
        source["payload_sha256"] = "F" * 64
    else:
        source["claim_surface"]["binding"] = _claim_surface_context(
            route_id="alternate",
            route="/alternate",
        )
    _write(source_path, json.dumps(source, indent=2, sort_keys=True) + "\n")

    verification = verify_staged_candidate_receipt(receipt, repo_root=root)
    assert verification["passed"] is False
    assert _check(verification, "validation-input-binding")["passed"] is False
    _assert_both_real_compilers_reject(
        root=root,
        receipt_path=receipt_path,
        receipt=receipt,
        message="raw, canonical, or payload binding failed preflight",
    )


@pytest.mark.parametrize("link_kind", ["symlink", "hardlink"])
def test_candidate_validation_input_rejects_link_aliases(
    tmp_path: Path,
    link_kind: str,
) -> None:
    root = tmp_path / "repo"
    receipt, receipt_path = _valid_candidate_receipt(
        root,
        run_id=f"input-{link_kind}",
    )
    source_path = root / receipt["validation_input"]["path"]
    alias_source = root / f"{link_kind}-validation-input.json"
    alias_source.write_bytes(source_path.read_bytes())
    source_path.unlink()
    try:
        if link_kind == "symlink":
            os.symlink(alias_source, source_path)
        else:
            os.link(alias_source, source_path)
    except OSError as exc:
        pytest.skip(f"{link_kind} creation is unavailable on this host: {exc}")

    verification = verify_staged_candidate_receipt(receipt, repo_root=root)
    assert verification["passed"] is False
    assert _check(verification, "validation-input-binding")["passed"] is False
    _assert_both_real_compilers_reject(
        root=root,
        receipt_path=receipt_path,
        receipt=receipt,
        message=(
            "may not traverse a link or reparse point" if link_kind == "symlink" else "exactly one hard link"
        ),
    )


@pytest.mark.parametrize("raw_kind", ["duplicate-key", "non-finite"])
def test_candidate_validation_input_strict_raw_json_fails_closed(
    tmp_path: Path,
    raw_kind: str,
) -> None:
    root = tmp_path / "repo"
    receipt, receipt_path = _valid_candidate_receipt(
        root,
        run_id=f"input-{raw_kind}",
    )
    source_path = root / receipt["validation_input"]["path"]
    if raw_kind == "duplicate-key":
        raw = source_path.read_text(encoding="utf-8").replace(
            '"schema": "aureon.design-candidate-validation-input.v1",',
            (
                '"schema": "aureon.design-candidate-validation-input.v1",\n'
                '  "schema": "aureon.design-candidate-validation-input.v1",'
            ),
            1,
        )
    else:
        source = json.loads(source_path.read_text(encoding="utf-8"))
        source["issued_at"] = float("nan")
        raw = json.dumps(source, indent=2, sort_keys=True, allow_nan=True) + "\n"
    _write(source_path, raw)

    verification = verify_staged_candidate_receipt(receipt, repo_root=root)
    assert verification["passed"] is False
    assert _check(verification, "validation-input-binding")["passed"] is False
    _assert_both_real_compilers_reject(
        root=root,
        receipt_path=receipt_path,
        receipt=receipt,
        message=(
            "contains a duplicate JSON key" if raw_kind == "duplicate-key" else "contains non-finite JSON"
        ),
    )


def test_candidate_validation_input_is_single_path_create_once_evidence(
    tmp_path: Path,
) -> None:
    root = tmp_path / "repo"
    receipt, _ = _valid_candidate_receipt(root, run_id="input-create-once")
    source_path = root / receipt["validation_input"]["path"]
    original = source_path.read_bytes()
    order = root / receipt["work_order"]["path"]

    with pytest.raises(
        DesignCandidateControlError,
        match="already exists with different immutable inputs",
    ):
        validate_design_candidate(
            order,
            claim_impacts=[_declaration("styles.css")],
            repo_root=root,
            now=NOW + timedelta(minutes=1),
        )

    assert source_path.read_bytes() == original


def test_candidate_receipt_non_finite_value_and_duplicate_raw_key_fail_closed(
    tmp_path: Path,
) -> None:
    nan_root = tmp_path / "nan"
    nan_receipt, nan_path = _valid_candidate_receipt(nan_root, run_id="non-finite")
    nan_receipt["checks"][0]["evidence"]["probe"] = float("nan")
    verification = verify_staged_candidate_receipt(nan_receipt, repo_root=nan_root)
    assert verification["passed"] is False
    assert _check(verification, "schema")["passed"] is False
    _assert_both_real_compilers_reject(
        root=nan_root,
        receipt_path=nan_path,
        receipt=nan_receipt,
        message="Candidate receipt preflight contains non-finite JSON",
    )

    duplicate_root = tmp_path / "duplicate"
    duplicate_receipt, duplicate_path = _valid_candidate_receipt(
        duplicate_root,
        run_id="duplicate-key",
    )
    _copy_real_candidate_compiler_sources(duplicate_root)
    raw = json.dumps(duplicate_receipt, indent=2)
    raw = raw.replace(
        '"schema": "aureon.design-candidate.v1",',
        '"schema": "aureon.design-candidate.v1",\n  "schema": "aureon.design-candidate.v1",',
        1,
    )
    _write(duplicate_path, raw + "\n")
    with pytest.raises(
        test_policy_compiler.DesignCandidateTestPolicyCompilerError,
        match="Candidate receipt preflight contains a duplicate JSON key",
    ):
        test_policy_compiler.compile_candidate_test_policy(
            duplicate_path,
            repo_root=duplicate_root,
        )
    with pytest.raises(
        motion_policy_compiler.DesignCandidateMotionPolicyCompilerError,
        match="Candidate receipt preflight contains a duplicate JSON key",
    ):
        motion_policy_compiler.compile_candidate_motion_config(
            duplicate_path,
            repo_root=duplicate_root,
        )


def test_style_candidate_is_staged_not_applied_and_has_no_release_authority(tmp_path: Path) -> None:
    _fake_repo(tmp_path)
    canonical_before = (tmp_path / "website" / "styles.css").read_text(encoding="utf-8")
    order = _order(tmp_path, "style-only", ["styles.css"])
    _assert_candidate_control_schema_valid(
        "workOrder",
        json.loads(order.read_text(encoding="utf-8")),
    )

    assert (
        verify_design_work_order(json.loads(order.read_text(encoding="utf-8")), repo_root=tmp_path)["passed"]
        is True
    )
    candidate_root = _stage(tmp_path, order)
    candidate_style = candidate_root / "website" / "styles.css"
    candidate_style.write_text("body { color: #234567; }\n", encoding="utf-8")

    receipt = validate_design_candidate(
        order,
        claim_impacts=[_declaration("styles.css")],
        repo_root=tmp_path,
        now=NOW,
    )
    _assert_candidate_control_schema_valid("claimSummary", receipt["claims"])

    assert receipt["passed"] is True
    assert receipt["state"] == "validated-local"
    assert receipt["authority"] == NON_AUTHORITATIVE_AUTHORITY
    assert receipt["release_eligible"] is False
    assert receipt["deployment_authority"] == "none"
    assert len(receipt["changes"]) == 1
    change = receipt["changes"][0]
    assert change["path"] == "styles.css"
    assert change["change"] == "modified"
    assert change["before_sha256"] != change["after_sha256"]
    assert change["before_bytes"] == (tmp_path / "website" / "styles.css").stat().st_size
    assert change["after_bytes"] == candidate_style.stat().st_size
    assert (tmp_path / "website" / "styles.css").read_text(encoding="utf-8") == canonical_before
    assert _check(receipt, "exact-scope")["passed"] is True
    assert _check(receipt, "staged-claim-register")["passed"] is True


def test_v4_order_binds_trusted_binary_policy_and_v3_fails_closed(
    tmp_path: Path,
) -> None:
    _fake_repo(tmp_path)
    order_path = _order(tmp_path, "v4-contract", ["styles.css"])
    order = json.loads(order_path.read_text(encoding="utf-8"))

    assert order["schema"] == "aureon.design-work-order.v4"
    assert order["editorial_asset_control"] == {
        "policy": "every-binary-diff-requires-trusted-editorial-import-receipt",
        "receipt_path": ("artifacts/website-candidates/v4-contract/editorial-asset-import-receipt.v1.json"),
        "receipt_schema": "aureon.design-editorial-asset-candidate-import.v1",
        "verification_schema": ("aureon.design-editorial-asset-candidate-import-verification.v1"),
        "binary_extensions": [
            ".gif",
            ".ico",
            ".jpeg",
            ".jpg",
            ".png",
            ".webp",
            ".woff",
            ".woff2",
        ],
        "trusted_import_extensions": [".webp"],
        "unreceipted_binary_diff": "prohibited",
        "replay_verification_required": True,
        "provenance_manifest_path": "",
        "provenance_manifest_sha256": "",
        "surface_binding_verification_required": False,
    }
    assert verify_design_work_order(order, repo_root=tmp_path)["passed"] is True

    legacy = json.loads(json.dumps(order))
    legacy["schema"] = "aureon.design-work-order.v3"
    verification = verify_design_work_order(legacy, repo_root=tmp_path)
    assert verification["passed"] is False
    assert _check(verification, "schema")["passed"] is False


def test_unreceipted_webp_and_non_webp_binary_paths_fail_closed(
    tmp_path: Path,
) -> None:
    _fake_repo(tmp_path)
    _write(
        tmp_path / "data" / "website_operator" / "editorial_asset_provenance.v1.json",
        "{}\n",
    )
    with pytest.raises(
        DesignCandidateControlError,
        match="trusted provenance-bound WebP importer",
    ):
        _order(tmp_path, "png-prohibited", ["assets/diagram.png"])

    order = _order(tmp_path, "webp-receipt-required", ["assets/diagram.webp"])
    candidate_root = _stage(tmp_path, order)
    target = candidate_root / "website" / "assets" / "diagram.webp"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(b"RIFF-untrusted-manual-copy")
    receipt = validate_design_candidate(
        order,
        claim_impacts=[],
        repo_root=tmp_path,
        now=NOW,
    )

    assert receipt["passed"] is False
    binary_check = _check(receipt, "trusted-binary-import-replay")
    assert binary_check["passed"] is False
    assert binary_check["evidence"]["error"] == "required-fixed-receipt-missing"
    assert binary_check["evidence"]["changed_binary_paths"] == ["assets/diagram.webp"]


def test_text_suffix_cannot_hide_binary_or_embedded_media_payload(
    tmp_path: Path,
) -> None:
    _fake_repo(tmp_path)
    order = _order(tmp_path, "strict-text", ["styles.css"])
    candidate_root = _stage(tmp_path, order)
    (candidate_root / "website" / "styles.css").write_bytes(
        b"body{background:url(data:image/png;base64,AAAA)}\x00"
    )

    receipt = validate_design_candidate(
        order,
        claim_impacts=[_declaration("styles.css")],
        repo_root=tmp_path,
        now=NOW,
    )

    assert receipt["passed"] is False
    text_check = _check(receipt, "strict-text-integrity")
    assert text_check["passed"] is False
    assert text_check["evidence"]["findings"] == [{"path": "styles.css", "reason": "control-byte"}]


def test_out_of_scope_candidate_change_is_blocked_even_with_a_claim_declaration(tmp_path: Path) -> None:
    _fake_repo(tmp_path)
    order = _order(tmp_path, "scope-bound", ["styles.css"])
    candidate_root = _stage(tmp_path, order)
    _write(candidate_root / "website" / "styles.css", "body { color: #234567; }\n")
    _write(candidate_root / "website" / "data" / "other.json", '{"status":"changed"}\n')

    receipt = validate_design_candidate(
        order,
        claim_impacts=[
            _declaration("styles.css"),
            _declaration("data/other.json", material=True),
        ],
        repo_root=tmp_path,
        now=NOW,
    )

    assert receipt["passed"] is False
    assert _check(receipt, "exact-scope")["passed"] is False
    assert _check(receipt, "exact-scope")["evidence"]["out_of_scope_paths"] == ["data/other.json"]


def test_changed_unbound_html_is_material_with_unchanged_claim_register(
    tmp_path: Path,
) -> None:
    _fake_repo(tmp_path)
    _write(
        tmp_path / "website" / "about" / "index.html",
        "<!doctype html><title>About</title><p>Existing non-claim route.</p>\n",
    )
    order = _order(tmp_path, "claim-unbound-html", ["about/index.html"])
    candidate_root = _stage(tmp_path, order)
    staged_register = candidate_root / "claim-evidence" / "public_claim_evidence_register.v1.json"
    register_before = _sha256(staged_register)
    _write(
        candidate_root / "website" / "about" / "index.html",
        "<!doctype html><title>About Aureon</title><p>Refined non-claim route.</p>\n",
    )

    receipt = validate_design_candidate(
        order,
        claim_impacts=[_declaration("about/index.html", material=True)],
        repo_root=tmp_path,
        now=NOW,
    )
    _assert_candidate_control_schema_valid("claimSummary", receipt["claims"])
    incomplete_claim_boundary = json.loads(json.dumps(receipt["claims"]))
    incomplete_claim_boundary.pop("unbound_material_claim_paths")
    assert _candidate_control_schema_errors("claimSummary", incomplete_claim_boundary)
    register_check = _check(receipt, "staged-claim-register")

    assert receipt["passed"] is True
    assert _check(receipt, "material-claim-source-classification")["passed"] is True
    assert register_check["passed"] is True
    assert register_check["evidence"]["bound_material_claim_paths"] == []
    assert register_check["evidence"]["unbound_material_claim_paths"] == ["about/index.html"]
    assert register_check["evidence"]["missing_material_source_bindings"] == []
    assert register_check["evidence"]["added_source_bindings"] == []
    assert register_check["evidence"]["added_public_route_bindings"] == []
    assert register_check["evidence"]["staged_register_audit_state"] == "not-run"
    assert _sha256(staged_register) == register_before


def test_changed_bound_claim_source_requires_material_declaration_and_staged_register_refresh(
    tmp_path: Path,
) -> None:
    def staged_case(case: str) -> tuple[Path, Path, Path]:
        repo_root = tmp_path / case
        _fake_repo(repo_root)
        order = _order(repo_root, f"claim-bound-{case}", ["index.html"])
        candidate_root = _stage(repo_root, order)
        _write(
            candidate_root / "website" / "index.html",
            "<!doctype html><title>Aureon</title><p>Refined evidence and boundary record. "
            "This fixture is not evidence of customer adoption or independent validation.</p>\n",
        )
        return repo_root, order, candidate_root

    missing_root, missing_order, _ = staged_case("missing")
    missing_refresh = validate_design_candidate(
        missing_order,
        claim_impacts=[
            _declaration("index.html"),
        ],
        repo_root=missing_root,
        now=NOW,
    )

    assert missing_refresh["passed"] is False
    assert _check(missing_refresh, "material-claim-source-classification")["passed"] is False
    assert _check(missing_refresh, "staged-claim-register")["passed"] is True

    material_root, material_order, _ = staged_case("material")
    material_without_refresh = validate_design_candidate(
        material_order,
        claim_impacts=[
            _declaration("index.html", material=True),
        ],
        repo_root=material_root,
        now=NOW,
    )
    assert material_without_refresh["passed"] is False
    assert _check(material_without_refresh, "material-claim-source-classification")["passed"] is True
    assert _check(material_without_refresh, "staged-claim-register")["passed"] is False

    stale_root, stale_order, stale_candidate_root = staged_case("stale")
    staged_register = stale_candidate_root / "claim-evidence" / "public_claim_evidence_register.v1.json"
    stale_register = json.loads(staged_register.read_text(encoding="utf-8"))
    stale_register["generated_at"] = "2026-07-28T10:04:00Z"
    staged_register.write_text(
        json.dumps(stale_register, indent=2) + "\n",
        encoding="utf-8",
    )
    stale_binding = validate_design_candidate(
        stale_order,
        claim_impacts=[
            _declaration("index.html", material=True),
        ],
        repo_root=stale_root,
        now=NOW,
    )
    stale_check = _check(stale_binding, "staged-claim-register")
    assert stale_binding["passed"] is False
    assert stale_check["passed"] is False
    assert stale_check["evidence"]["bound_material_claim_paths"] == ["index.html"]
    assert stale_check["evidence"]["stale_material_source_bindings"] == ["index.html"]

    refreshed_root, refreshed_order, refreshed_candidate_root = staged_case("refreshed")
    _refresh_staged_register(refreshed_candidate_root)
    refreshed = validate_design_candidate(
        refreshed_order,
        claim_impacts=[
            _declaration("index.html", material=True),
        ],
        repo_root=refreshed_root,
        now=NOW,
    )
    _assert_candidate_control_schema_valid("claimSummary", refreshed["claims"])

    assert refreshed["passed"] is True
    assert _check(refreshed, "material-claim-source-classification")["passed"] is True
    assert _check(refreshed, "staged-claim-register")["passed"] is True


@pytest.mark.parametrize("broadening", ["route", "source"])
def test_staged_claim_register_refresh_cannot_broaden_route_or_source_scope(
    tmp_path: Path,
    broadening: str,
) -> None:
    _fake_repo(tmp_path)
    _write(
        tmp_path / "website" / "about" / "index.html",
        "<!doctype html><title>About Aureon</title><p>Aureon boundary. "
        "This fixture is not evidence of customer adoption or independent validation.</p>\n",
    )
    order = _order(tmp_path, f"claim-{broadening}-broadening", ["index.html"])
    candidate_root = _stage(tmp_path, order)
    _write(
        candidate_root / "website" / "index.html",
        "<!doctype html><title>Aureon</title><p>Refined evidence and boundary record. "
        "This fixture is not evidence of customer adoption or independent validation.</p>\n",
    )
    _refresh_staged_register(candidate_root)
    staged_register = candidate_root / "claim-evidence" / "public_claim_evidence_register.v1.json"
    register = json.loads(staged_register.read_text(encoding="utf-8"))
    if broadening == "route":
        register["claims"][0]["public_routes"].append("/about/")
    else:
        about_page = candidate_root / "website" / "about" / "index.html"
        register["claims"][0]["source"]["path"] = "website/about/index.html"
        register["claims"][0]["source"]["sha256"] = _sha256(about_page)
        register["claims"][0]["source"]["locator"] = "fixture:about"
    staged_register.write_text(
        json.dumps(register, indent=2) + "\n",
        encoding="utf-8",
    )

    receipt = validate_design_candidate(
        order,
        claim_impacts=[_declaration("index.html", material=True)],
        repo_root=tmp_path,
        now=NOW,
    )
    register_check = _check(receipt, "staged-claim-register")

    assert receipt["passed"] is False
    assert register_check["passed"] is False
    if broadening == "route":
        assert register_check["evidence"]["added_public_route_bindings"] == [
            {"claim_id": "homepage-claim", "route": "/about/"}
        ]
    else:
        assert register_check["evidence"]["added_source_bindings"] == ["about/index.html"]
        assert register_check["evidence"]["removed_source_bindings"] == ["index.html"]


def test_candidate_blocks_new_remote_origin_and_secret_pattern(tmp_path: Path) -> None:
    _fake_repo(tmp_path)
    order = _order(tmp_path, "origin-secret", ["styles.css"])
    candidate_root = _stage(tmp_path, order)
    _write(
        candidate_root / "website" / "styles.css",
        'body { background-image: url("https://unexpected.example/asset.png"); } /* sk-abcdefghijklmnopqrstuv */\n',
    )

    receipt = validate_design_candidate(
        order,
        claim_impacts=[_declaration("styles.css")],
        repo_root=tmp_path,
        now=NOW,
    )

    assert receipt["passed"] is False
    assert _check(receipt, "remote-origin-diff")["passed"] is False
    assert _check(receipt, "remote-origin-diff")["evidence"]["new_origins"] == ["https://unexpected.example"]
    assert _check(receipt, "secret-scan")["passed"] is False


def test_candidate_blocks_scheme_relative_origins_and_extended_secret_patterns(tmp_path: Path) -> None:
    _fake_repo(tmp_path)
    order = _order(tmp_path, "scheme-secret", ["styles.css"])
    candidate_root = _stage(tmp_path, order)
    _write(
        candidate_root / "website" / "styles.css",
        'body { background-image: url("//unexpected.example/asset.png"); } /* ghp_abcdefghijklmnopqrstuvwxy */\n',
    )

    receipt = validate_design_candidate(
        order,
        claim_impacts=[_declaration("styles.css")],
        repo_root=tmp_path,
        now=NOW,
    )

    assert receipt["passed"] is False
    assert _check(receipt, "remote-origin-diff")["evidence"]["new_origins"] == ["https://unexpected.example"]
    assert "github-token" in _check(receipt, "secret-scan")["evidence"]["findings"][0]["matches"]


def test_candidate_rejects_server_configuration_and_public_file_removal(tmp_path: Path) -> None:
    _fake_repo(tmp_path)
    with pytest.raises(DesignCandidateControlError, match="blocked or unsupported"):
        _order(tmp_path, "server-config", [".htaccess"])

    order = _order(tmp_path, "no-removal", ["index.html"])
    candidate_root = _stage(tmp_path, order)
    (candidate_root / "website" / "index.html").unlink()
    receipt = validate_design_candidate(
        order,
        claim_impacts=[_declaration("index.html", material=True)],
        repo_root=tmp_path,
        now=NOW,
    )

    assert receipt["passed"] is False
    assert _check(receipt, "no-public-file-removal")["passed"] is False


def test_stale_baseline_refuses_to_stage_a_candidate(tmp_path: Path) -> None:
    _fake_repo(tmp_path)
    order = _order(tmp_path, "stale-baseline", ["styles.css"])
    _write(tmp_path / "website" / "styles.css", "body { color: #654321; }\n")

    verification = verify_design_work_order(json.loads(order.read_text(encoding="utf-8")), repo_root=tmp_path)

    assert verification["passed"] is False
    assert _check(verification, "baseline-current")["passed"] is False
    with pytest.raises(DesignCandidateControlError, match="baseline-current"):
        stage_design_candidate(order, repo_root=tmp_path)


def test_candidate_requires_current_live_reconciliation_before_staging(tmp_path: Path) -> None:
    _fake_repo(tmp_path)

    with pytest.raises(DesignCandidateControlError, match="live-surface reconciliation receipt"):
        create_design_work_order(
            goal="Refine a bounded route.",
            allowed_paths=["styles.css"],
            routes=["/"],
            run_id="missing-reconciliation",
            repo_root=tmp_path,
            now=NOW,
        )


def test_drifted_candidate_requires_owner_decision_and_verified_backup(tmp_path: Path) -> None:
    _fake_repo(tmp_path)
    reconciliation = _drift_reconciliation(tmp_path, "drift-gate")

    with pytest.raises(DesignCandidateControlError, match="owner source-reconciliation decision"):
        create_design_work_order(
            goal="Refine a bounded route.",
            allowed_paths=["styles.css"],
            routes=["/"],
            reconciliation_receipt=reconciliation,
            run_id="drift-gate",
            repo_root=tmp_path,
            now=NOW,
        )

    decision, backup = _owner_source_decision(tmp_path, reconciliation, "drift-gate")
    order = create_design_work_order(
        goal="Refine a bounded route.",
        allowed_paths=["styles.css"],
        routes=["/"],
        reconciliation_receipt=reconciliation,
        owner_source_decision=decision,
        backup_receipt=backup,
        run_id="drift-owner-approved",
        repo_root=tmp_path,
        now=NOW,
    )
    _assert_candidate_control_schema_valid("workOrder", order)
    unpaired_v1 = json.loads(json.dumps(order))
    unpaired_v1["live_reconciliation"]["owner_source_reconciliation"]["candidate_source"] = {
        "kind": "verified-live-backup"
    }
    assert _candidate_control_schema_errors("workOrder", unpaired_v1)
    verification = verify_design_work_order(order, repo_root=tmp_path)

    assert order["live_reconciliation"]["state"] == "live-drift-detected"
    assert order["live_reconciliation"]["owner_source_reconciliation"]["required"] is True
    assert verification["passed"] is True
    assert _check(verification, "live-reconciliation")["passed"] is True


def test_verified_live_backup_is_staged_while_local_canonical_remains_unchanged(
    tmp_path: Path,
) -> None:
    _fake_repo(tmp_path)
    local_before = {
        path.relative_to(tmp_path / "website").as_posix(): path.read_bytes()
        for path in (tmp_path / "website").rglob("*")
        if path.is_file()
    }
    order_path, _, _, backup_root, _ = _live_backup_order(tmp_path, "live-backup-source")
    order = json.loads(order_path.read_text(encoding="utf-8"))
    _assert_candidate_control_schema_valid("workOrder", order)
    broadened_source = json.loads(json.dumps(order))
    broadened_source["live_reconciliation"]["owner_source_reconciliation"]["candidate_source"][
        "credential_access"
    ] = "none"
    assert _candidate_control_schema_errors("workOrder", broadened_source)

    verification = verify_design_work_order(order, repo_root=tmp_path)
    stage = stage_design_candidate(order_path, repo_root=tmp_path)
    candidate_site = tmp_path / stage["candidate_website"]

    assert verification["passed"] is True
    assert (
        order["live_reconciliation"]["owner_source_reconciliation"]["source_selection"]
        == "use-verified-live-backup"
    )
    source = order["live_reconciliation"]["owner_source_reconciliation"]["candidate_source"]
    assert source["kind"] == "verified-live-backup"
    assert source["root"] == str(backup_root)
    assert source["tree_sha256"]
    assert source["manifest_sha256"]
    assert source["baseline_tree_sha256"] == order["baseline"]["tree_sha256"]
    assert (candidate_site / "index.html").read_bytes() == (backup_root / "index.html").read_bytes()
    assert (candidate_site / "index.html").read_bytes() != (tmp_path / "website" / "index.html").read_bytes()
    _write(candidate_site / "styles.css", "body { color: #abcdef; }\n")
    receipt = validate_design_candidate(
        order_path,
        claim_impacts=[_declaration("styles.css")],
        repo_root=tmp_path,
        now=NOW,
    )
    current = verify_staged_candidate_receipt(receipt, repo_root=tmp_path)
    assert receipt["passed"] is True
    assert current["passed"] is True
    assert {
        path.relative_to(tmp_path / "website").as_posix(): path.read_bytes()
        for path in (tmp_path / "website").rglob("*")
        if path.is_file()
    } == local_before


@pytest.mark.parametrize("tamper", ["receipt", "manifest", "file", "decision"])
def test_live_backup_candidate_revalidation_rejects_bound_evidence_tamper(
    tmp_path: Path,
    tamper: str,
) -> None:
    _fake_repo(tmp_path)
    order_path, decision_path, backup_path, backup_root, manifest_path = _live_backup_order(
        tmp_path, f"live-tamper-{tamper}"
    )
    if tamper == "receipt":
        backup = json.loads(backup_path.read_text(encoding="utf-8"))
        backup["total_bytes"] += 1
        backup_path.write_text(json.dumps(backup, indent=2) + "\n", encoding="utf-8")
    elif tamper == "manifest":
        manifest_path.write_text(
            manifest_path.read_text(encoding="utf-8") + "\n",
            encoding="utf-8",
        )
    elif tamper == "file":
        _write(backup_root / "index.html", "<!doctype html><title>Tampered</title>\n")
    else:
        decision = json.loads(decision_path.read_text(encoding="utf-8"))
        decision["note"] = "Changed after the work order was bound."
        decision_path.write_text(json.dumps(decision, indent=2) + "\n", encoding="utf-8")

    order = json.loads(order_path.read_text(encoding="utf-8"))
    verification = verify_design_work_order(order, repo_root=tmp_path)

    assert verification["passed"] is False
    assert _check(verification, "live-reconciliation")["passed"] is False
    with pytest.raises(DesignCandidateControlError):
        stage_design_candidate(order_path, repo_root=tmp_path)


def test_live_backup_candidate_rejects_false_tree_even_when_owner_hashes_match(
    tmp_path: Path,
) -> None:
    _fake_repo(tmp_path)
    reconciliation = _drift_reconciliation(tmp_path, "live-false-tree")
    decision_path, backup_path, _, _ = _verified_live_backup_decision(
        tmp_path, reconciliation, "live-false-tree"
    )
    backup = json.loads(backup_path.read_text(encoding="utf-8"))
    backup["tree_sha256"] = "F" * 64
    backup_path.write_text(json.dumps(backup, indent=2) + "\n", encoding="utf-8")
    decision = json.loads(decision_path.read_text(encoding="utf-8"))
    decision["backup_tree_sha256"] = backup["tree_sha256"]
    decision["backup_receipt_sha256"] = _sha256(backup_path)
    decision_path.write_text(json.dumps(decision, indent=2) + "\n", encoding="utf-8")

    with pytest.raises(DesignCandidateControlError, match="tree hash"):
        create_design_work_order(
            goal="Use the exact verified live source.",
            allowed_paths=["styles.css"],
            routes=["/"],
            reconciliation_receipt=reconciliation,
            owner_source_decision=decision_path,
            backup_receipt=backup_path,
            run_id="live-false-tree-order",
            repo_root=tmp_path,
            now=NOW,
        )


@pytest.mark.parametrize(
    "blocked_path",
    [
        ".env",
        ".env.production",
        ".env1",
        "private.key",
        "certificate.pem",
        "bundle.pfx",
        "bundle.p12",
        "id_rsa",
        "id_ed25519",
        "server.php",
    ],
)
def test_live_backup_candidate_rejects_bound_secret_or_server_only_path(
    tmp_path: Path,
    blocked_path: str,
) -> None:
    _fake_repo(tmp_path)
    run_id = "live-blocked-" + blocked_path.replace(".", "-").strip("-")
    reconciliation = _drift_reconciliation(tmp_path, run_id)
    decision_path, backup_path, backup_root, manifest_path = _verified_live_backup_decision(
        tmp_path, reconciliation, run_id
    )
    _write(backup_root / blocked_path, "synthetic server-only fixture\n")
    _rebind_verified_live_backup(
        decision_path,
        backup_path,
        backup_root,
        manifest_path,
    )

    with pytest.raises(DesignCandidateControlError, match="blocked credential-bearing"):
        create_design_work_order(
            goal="Use the exact verified live source.",
            allowed_paths=["styles.css"],
            routes=["/"],
            reconciliation_receipt=reconciliation,
            owner_source_decision=decision_path,
            backup_receipt=backup_path,
            run_id=f"{run_id}-order",
            repo_root=tmp_path,
            now=NOW,
        )


@pytest.mark.parametrize(
    ("relative", "content", "expected_pattern"),
    [
        (
            "data/runtime.json",
            '{"token":"sk-syntheticcredential000000000000"}\n',
            "openai-api-key",
        ),
        (
            "notes/private-key.txt",
            "-----BEGIN PRIVATE KEY-----\nsynthetic-only\n-----END PRIVATE KEY-----\n",
            "private-key",
        ),
    ],
)
def test_live_backup_candidate_rejects_bound_credential_patterns_in_public_files(
    tmp_path: Path,
    relative: str,
    content: str,
    expected_pattern: str,
) -> None:
    _fake_repo(tmp_path)
    run_id = "live-secret-pattern-" + expected_pattern
    reconciliation = _drift_reconciliation(tmp_path, run_id)
    decision_path, backup_path, backup_root, manifest_path = _verified_live_backup_decision(
        tmp_path, reconciliation, run_id
    )
    _write(backup_root / relative, content)
    _rebind_verified_live_backup(
        decision_path,
        backup_path,
        backup_root,
        manifest_path,
    )

    with pytest.raises(
        DesignCandidateControlError,
        match=rf"credential patterns: .*{expected_pattern}",
    ):
        create_design_work_order(
            goal="Use the exact verified live source.",
            allowed_paths=["styles.css"],
            routes=["/"],
            reconciliation_receipt=reconciliation,
            owner_source_decision=decision_path,
            backup_receipt=backup_path,
            run_id=f"{run_id}-order",
            repo_root=tmp_path,
            now=NOW,
        )


def test_live_backup_candidate_rejects_manifest_escape_even_when_rebound(
    tmp_path: Path,
) -> None:
    _fake_repo(tmp_path)
    reconciliation = _drift_reconciliation(tmp_path, "live-manifest-escape")
    decision_path, backup_path, backup_root, manifest_path = _verified_live_backup_decision(
        tmp_path, reconciliation, "live-manifest-escape"
    )
    outside = backup_root.parent / "outside.html"
    _write(outside, "outside\n")
    _write(
        manifest_path,
        f"Path,Bytes,Sha256\n../outside.html,{outside.stat().st_size},{_sha256(outside)}\n",
    )
    backup = json.loads(backup_path.read_text(encoding="utf-8"))
    backup["manifest_sha256"] = _sha256(manifest_path)
    backup["file_count"] = 1
    backup["total_bytes"] = outside.stat().st_size
    backup_path.write_text(json.dumps(backup, indent=2) + "\n", encoding="utf-8")
    decision = json.loads(decision_path.read_text(encoding="utf-8"))
    decision["backup_manifest_sha256"] = backup["manifest_sha256"]
    decision["backup_receipt_sha256"] = _sha256(backup_path)
    decision_path.write_text(json.dumps(decision, indent=2) + "\n", encoding="utf-8")

    with pytest.raises(DesignCandidateControlError, match="Unsafe candidate path"):
        create_design_work_order(
            goal="Use the exact verified live source.",
            allowed_paths=["styles.css"],
            routes=["/"],
            reconciliation_receipt=reconciliation,
            owner_source_decision=decision_path,
            backup_receipt=backup_path,
            run_id="live-manifest-escape-order",
            repo_root=tmp_path,
            now=NOW,
        )


@pytest.mark.parametrize("kind", ["link", "hardlink"])
def test_live_backup_candidate_rejects_source_link_or_hardlink(
    tmp_path: Path,
    kind: str,
) -> None:
    repo = tmp_path / kind
    _fake_repo(repo)
    order_path, _, _, backup_root, _ = _live_backup_order(repo, f"live-source-{kind}")
    source = backup_root / "styles.css"
    outside = backup_root.parent / f"{kind}-source.css"
    shutil.copy2(source, outside)
    source.unlink()
    try:
        if kind == "link":
            os.symlink(outside, source)
        else:
            os.link(outside, source)
    except OSError as exc:
        pytest.skip(f"{kind} creation is unavailable on this host: {exc}")

    order = json.loads(order_path.read_text(encoding="utf-8"))
    verification = verify_design_work_order(order, repo_root=repo)

    assert verification["passed"] is False
    assert _check(verification, "live-reconciliation")["passed"] is False
    with pytest.raises(DesignCandidateControlError):
        stage_design_candidate(order_path, repo_root=repo)


def test_live_backup_work_order_rejects_source_binding_substitution(
    tmp_path: Path,
) -> None:
    _fake_repo(tmp_path)
    order_path, _, _, backup_root, _ = _live_backup_order(tmp_path, "live-source-substitution")
    order = json.loads(order_path.read_text(encoding="utf-8"))
    substitute = (backup_root.parent / "substitute").resolve()
    shutil.copytree(backup_root, substitute)
    order["live_reconciliation"]["owner_source_reconciliation"]["candidate_source"]["root"] = str(substitute)

    verification = verify_design_work_order(order, repo_root=tmp_path)

    assert verification["passed"] is False
    assert _check(verification, "live-reconciliation")["passed"] is False


def test_live_backup_candidate_rejects_backup_directory_outside_artifacts(
    tmp_path: Path,
) -> None:
    _fake_repo(tmp_path)
    reconciliation = _drift_reconciliation(tmp_path, "live-outside-artifacts")
    decision_path, backup_path, backup_root, _ = _verified_live_backup_decision(
        tmp_path,
        reconciliation,
        "live-outside-artifacts",
    )
    outside = (tmp_path / "private-data" / "homepl-document-root").resolve()
    shutil.copytree(backup_root, outside)
    rows = candidate_control._file_manifest(outside)  # noqa: SLF001
    backup = json.loads(backup_path.read_text(encoding="utf-8"))
    backup["backup_directory"] = str(outside)
    backup["tree_sha256"] = candidate_control._website_operator_tree_hash(  # noqa: SLF001
        outside, rows
    )
    backup_path.write_text(json.dumps(backup, indent=2) + "\n", encoding="utf-8")
    decision = json.loads(decision_path.read_text(encoding="utf-8"))
    decision["backup_directory"] = str(outside)
    decision["backup_tree_sha256"] = backup["tree_sha256"]
    decision["backup_receipt_sha256"] = _sha256(backup_path)
    decision_path.write_text(json.dumps(decision, indent=2) + "\n", encoding="utf-8")

    with pytest.raises(
        DesignCandidateControlError,
        match="below artifacts/homepl-backups",
    ):
        create_design_work_order(
            goal="Use the exact verified live source.",
            allowed_paths=["styles.css"],
            routes=["/"],
            reconciliation_receipt=reconciliation,
            owner_source_decision=decision_path,
            backup_receipt=backup_path,
            run_id="live-outside-artifacts-order",
            repo_root=tmp_path,
            now=NOW,
        )


def test_live_backup_candidate_rejects_manifest_outside_artifacts(
    tmp_path: Path,
) -> None:
    _fake_repo(tmp_path)
    reconciliation = _drift_reconciliation(tmp_path, "live-manifest-outside")
    decision_path, backup_path, _, manifest_path = _verified_live_backup_decision(
        tmp_path,
        reconciliation,
        "live-manifest-outside",
    )
    outside_manifest = (tmp_path / "private-data" / "manifest.csv").resolve()
    _write(outside_manifest, manifest_path.read_text(encoding="utf-8"))
    backup = json.loads(backup_path.read_text(encoding="utf-8"))
    backup["manifest"] = str(outside_manifest)
    backup["manifest_sha256"] = _sha256(outside_manifest)
    backup_path.write_text(json.dumps(backup, indent=2) + "\n", encoding="utf-8")
    decision = json.loads(decision_path.read_text(encoding="utf-8"))
    decision["backup_manifest"] = str(outside_manifest)
    decision["backup_manifest_sha256"] = backup["manifest_sha256"]
    decision["backup_receipt_sha256"] = _sha256(backup_path)
    decision_path.write_text(json.dumps(decision, indent=2) + "\n", encoding="utf-8")

    with pytest.raises(
        DesignCandidateControlError,
        match="manifest must stay below artifacts",
    ):
        create_design_work_order(
            goal="Use the exact verified live source.",
            allowed_paths=["styles.css"],
            routes=["/"],
            reconciliation_receipt=reconciliation,
            owner_source_decision=decision_path,
            backup_receipt=backup_path,
            run_id="live-manifest-outside-order",
            repo_root=tmp_path,
            now=NOW,
        )


def test_live_backup_source_must_remain_stable_during_copy(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _fake_repo(tmp_path)
    order_path, _, _, backup_root, _ = _live_backup_order(tmp_path, "live-source-stability")
    local_before = (tmp_path / "website" / "index.html").read_bytes()
    original_copy = shutil.copy2
    changed = False

    def copy_with_source_change(
        source: str | os.PathLike[str],
        target: str | os.PathLike[str],
        *,
        follow_symlinks: bool = True,
    ) -> str:
        nonlocal changed
        result = original_copy(
            source,
            target,
            follow_symlinks=follow_symlinks,
        )
        source_path = Path(source)
        if not changed and source_path.parent == backup_root:
            changed = True
            _write(backup_root / "index.html", "<!doctype html><title>Race</title>\n")
        return str(result)

    monkeypatch.setattr(candidate_control.shutil, "copy2", copy_with_source_change)

    with pytest.raises(DesignCandidateControlError, match="changed (?:before copy|while)"):
        stage_design_candidate(order_path, repo_root=tmp_path)

    assert changed is True
    assert (tmp_path / "website" / "index.html").read_bytes() == local_before


def test_post_validation_candidate_mutation_breaks_provenance_check(tmp_path: Path) -> None:
    _fake_repo(tmp_path)
    order = _order(tmp_path, "post-validation", ["styles.css"])
    candidate_root = _stage(tmp_path, order)
    _write(candidate_root / "website" / "styles.css", "body { color: #234567; }\n")
    receipt = validate_design_candidate(
        order,
        claim_impacts=[_declaration("styles.css")],
        repo_root=tmp_path,
        now=NOW,
    )
    output = candidate_root / "candidate.v1.json"
    write_design_candidate_receipt(receipt, output, repo_root=tmp_path)

    _write(candidate_root / "website" / "styles.css", "body { color: #345678; }\n")
    verification = verify_candidate_receipt_for_current_site(receipt, repo_root=tmp_path)

    assert verification["passed"] is False
    assert _check(verification, "staged-candidate-unchanged")["passed"] is False


def test_post_validation_work_order_tamper_breaks_provenance_check(tmp_path: Path) -> None:
    _fake_repo(tmp_path)
    order = _order(tmp_path, "order-tamper", ["styles.css"])
    candidate_root = _stage(tmp_path, order)
    _write(candidate_root / "website" / "styles.css", "body { color: #234567; }\n")
    receipt = validate_design_candidate(
        order,
        claim_impacts=[_declaration("styles.css")],
        repo_root=tmp_path,
        now=NOW,
    )

    tampered = json.loads(order.read_text(encoding="utf-8"))
    tampered["goal"] = "Changed after validation."
    order.write_text(json.dumps(tampered, indent=2) + "\n", encoding="utf-8")

    verification = verify_candidate_receipt_for_current_site(receipt, repo_root=tmp_path)

    assert verification["passed"] is False
    assert _check(verification, "work-order-binding")["passed"] is False


def test_candidate_receipt_cannot_be_redirected_to_canonical_website(tmp_path: Path) -> None:
    _fake_repo(tmp_path)
    order = _order(tmp_path, "receipt-layout", ["styles.css"])
    candidate_root = _stage(tmp_path, order)
    _write(candidate_root / "website" / "styles.css", "body { color: #234567; }\n")
    receipt = validate_design_candidate(
        order,
        claim_impacts=[_declaration("styles.css")],
        repo_root=tmp_path,
        now=NOW,
    )
    _write(tmp_path / "website" / "styles.css", "body { color: #234567; }\n")
    redirected = json.loads(json.dumps(receipt))
    redirected["candidate"]["website_path"] = "website"

    verification = verify_candidate_receipt_for_current_site(redirected, repo_root=tmp_path)

    assert verification["passed"] is False
    assert _check(verification, "receipt-layout-binding")["passed"] is False


def test_candidate_stage_refuses_work_order_placed_outside_approved_artifact_directory(
    tmp_path: Path,
) -> None:
    _fake_repo(tmp_path)
    approved = _order(tmp_path, "approved-order", ["styles.css"])
    copied = tmp_path / "docs" / "unapproved-work-order.json"
    copied.parent.mkdir(parents=True, exist_ok=True)
    copied.write_text(approved.read_text(encoding="utf-8"), encoding="utf-8")

    with pytest.raises(DesignCandidateControlError, match="artifacts/website-candidates"):
        stage_design_candidate(copied, repo_root=tmp_path)


def test_work_order_evidence_cannot_be_written_outside_candidate_artifacts(tmp_path: Path) -> None:
    _fake_repo(tmp_path)
    order = create_design_work_order(
        goal="Refine one bounded investor-facing route.",
        allowed_paths=["styles.css"],
        routes=["/"],
        reconciliation_receipt=_aligned_reconciliation(tmp_path, "outside-output"),
        run_id="outside-output",
        repo_root=tmp_path,
        now=NOW,
    )

    with pytest.raises(DesignCandidateControlError, match="artifacts/website-candidates"):
        write_design_work_order(order, tmp_path / "docs" / "work-order.json", repo_root=tmp_path)
    with pytest.raises(DesignCandidateControlError, match="beside, not inside"):
        write_design_work_order(
            order,
            tmp_path / order["candidate_layout"]["root"] / "work-order.v4.json",
            repo_root=tmp_path,
        )


def test_work_order_write_is_create_once_under_concurrent_callers(tmp_path: Path) -> None:
    _fake_repo(tmp_path)
    run_id = "concurrent-work-order"
    order = create_design_work_order(
        goal="Refine one bounded investor-facing route.",
        allowed_paths=["styles.css"],
        routes=["/"],
        reconciliation_receipt=_aligned_reconciliation(tmp_path, run_id),
        run_id=run_id,
        repo_root=tmp_path,
        now=NOW,
    )
    output = tmp_path / "artifacts" / "website-candidates" / "work-orders" / f"{run_id}.v4.json"

    def write() -> str:
        try:
            write_design_work_order(order, output, repo_root=tmp_path)
        except DesignCandidateControlError:
            return "blocked"
        return "written"

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _index: write(), range(2)))

    assert sorted(results) == ["blocked", "written"]
    loaded, relative, raw = candidate_control._load_work_order(  # noqa: SLF001
        output,
        tmp_path,
    )
    assert loaded == order
    assert relative == f"artifacts/website-candidates/work-orders/{run_id}.v4.json"
    assert raw == candidate_control._work_order_bytes(order)  # noqa: SLF001


def test_work_order_loader_rejects_alternate_stream_alias_syntax(tmp_path: Path) -> None:
    _fake_repo(tmp_path)
    approved = _order(tmp_path, "ads-work-order", ["styles.css"])

    with pytest.raises(DesignCandidateControlError, match="alternate data stream"):
        stage_design_candidate(Path(f"{approved}:alias"), repo_root=tmp_path)


def test_work_order_is_bound_to_current_operator_policy_and_claim_register(tmp_path: Path) -> None:
    _fake_repo(tmp_path)
    order = _order(tmp_path, "policy-register", ["styles.css"])
    assert (
        verify_design_work_order(json.loads(order.read_text(encoding="utf-8")), repo_root=tmp_path)["passed"]
        is True
    )

    _write(tmp_path / "aureon" / "operator" / "website_operator.defaults.json", '{"policy":"changed"}\n')
    after_policy = verify_design_work_order(json.loads(order.read_text(encoding="utf-8")), repo_root=tmp_path)

    assert after_policy["passed"] is False
    assert _check(after_policy, "test-policy")["passed"] is False


def test_public_schema_preserves_staged_only_no_deployment_boundary() -> None:
    schema = json.loads(
        (
            REPO_ROOT / "docs" / "research" / "schemas" / "AUREON_DESIGN_CANDIDATE_CONTROL_V2.schema.json"
        ).read_text(encoding="utf-8")
    )

    authority = schema["$defs"]["authority"]["properties"]
    assert authority["canonical_website_mutation"]["const"] == "never by this control or a design agent"
    assert authority["release_eligible"]["const"] is False
    assert authority["deployment_authority"]["const"] == "none"
    work_order = schema["$defs"]["workOrder"]
    assert work_order["properties"]["schema"]["const"] == "aureon.design-work-order.v4"
    assert "editorial_asset_control" in work_order["required"]
    editorial = schema["$defs"]["editorialAssetControl"]["properties"]
    assert editorial["trusted_import_extensions"]["const"] == [".webp"]
    assert editorial["unreceipted_binary_diff"]["const"] == "prohibited"
    assert editorial["replay_verification_required"]["const"] is True
    assert {entry["$ref"] for entry in schema["oneOf"]} == {
        "#/$defs/workOrder",
        "#/$defs/candidateReceipt",
        "#/$defs/candidateValidationInput",
    }
    validation_input = schema["$defs"]["candidateValidationInput"]
    assert validation_input["properties"]["schema"]["const"] == (
        "aureon.design-candidate-validation-input.v1"
    )
    validation_authority = schema["$defs"]["candidateValidationInputAuthority"]["properties"]
    assert validation_authority["release_eligible"]["const"] is False
    assert validation_authority["wall_clock_attestation"]["const"] == "none"
    assert validation_authority["input_origin_attested"]["const"] is False
    receipt = schema["$defs"]["candidateReceipt"]
    assert "validation_input" in receipt["required"]

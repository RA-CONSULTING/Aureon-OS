from __future__ import annotations

import ast
import hashlib
import json
import os
import shutil
import subprocess
import sys
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import MappingProxyType
from typing import Any, Callable

import pytest
from jsonschema import Draft202012Validator

from aureon.operator import website_runtime_measurement_provenance as provenance

REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = (
    REPO_ROOT / "docs/research/schemas/AUREON_WEBSITE_RUNTIME_MEASUREMENT_STATIC_INTEGRITY_V1.schema.json"
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


def _with_payload(value: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(value)
    result["payload_sha256"] = _json_sha256(result)
    return result


def _write_json(path: Path, value: object) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(value, indent=2, sort_keys=True).encode("utf-8") + b"\n"
    path.write_bytes(payload)
    return _sha256_bytes(payload)


def _png(width: int, height: int, size: int) -> bytes:
    header = (
        b"\x89PNG\r\n\x1a\n"
        + (13).to_bytes(4, "big")
        + b"IHDR"
        + width.to_bytes(4, "big")
        + height.to_bytes(4, "big")
        + b"\x08\x06\x00\x00\x00"
    )
    assert size >= len(header)
    return header + (b"P" * (size - len(header)))


def _jpeg(width: int, height: int, size: int) -> bytes:
    header = b"\xff\xd8\xff\xc0\x00\x07\x08" + height.to_bytes(2, "big") + width.to_bytes(2, "big")
    assert size >= len(header)
    return header + (b"J" * (size - len(header)))


def _webp(width: int, height: int, size: int) -> bytes:
    assert size >= 30
    chunk_size = size - 20
    chunk = (
        b"\x00\x00\x00\x00"
        + (width - 1).to_bytes(3, "little")
        + (height - 1).to_bytes(3, "little")
        + (b"W" * (chunk_size - 10))
    )
    payload = b"RIFF" + (size - 8).to_bytes(4, "little") + b"WEBPVP8X"
    payload += chunk_size.to_bytes(4, "little") + chunk
    assert len(payload) == size
    return payload


def _manifest(site: Path) -> dict[str, object]:
    rows = []
    for path in sorted(site.rglob("*")):
        if path.is_file():
            payload = path.read_bytes()
            rows.append(
                {
                    "path": path.relative_to(site).as_posix(),
                    "bytes": len(payload),
                    "sha256": _sha256_bytes(payload),
                }
            )
    rows.sort(key=lambda row: str(row["path"]))
    digest = _json_sha256(rows)
    return {
        "root": "website",
        "file_count": len(rows),
        "total_bytes": sum(int(row["bytes"]) for row in rows),
        "manifest_sha256": digest,
        "tree_sha256": digest,
        "files": rows,
    }


def _fixture(tmp_path: Path) -> tuple[Path, Path, dict[str, Any], str]:
    root = tmp_path / "repo"
    site = root / "website"
    site.mkdir(parents=True)
    (site / "index.html").write_bytes(b"<!doctype html><title>Aureon</title>\n")
    source = _png(320, 180, 240)
    (site / "assets").mkdir()
    (site / "assets/hero.png").write_bytes(source)

    run_id = "static-integrity-fixture"
    transformation_id = "hero-png-to-webp"
    derivative = _webp(320, 180, 80)
    replica_rows = []
    for role in ("replica-a", "replica-b"):
        relative = provenance.REPLICA_ROOT / run_id / transformation_id / role / "hero.webp"
        target = root.joinpath(*relative.parts)
        target.parent.mkdir(parents=True)
        target.write_bytes(derivative)
        replica_rows.append(
            {
                "role": role,
                "path": relative.as_posix(),
                "file_sha256": _sha256_bytes(derivative),
                "bytes": len(derivative),
                "media_type": "image/webp",
                "width": 320,
                "height": 180,
            }
        )
    document = _with_payload(
        {
            "schema": provenance.MEASUREMENT_SCHEMA,
            "observed_at": "2020-08-02T22:30:00Z",
            "run_id": run_id,
            "state": provenance.VERIFIED_STATE,
            "mode": provenance.VERIFICATION_MODE,
            "source_manifest": _manifest(site),
            "transformations": [
                {
                    "id": transformation_id,
                    "source_path": "assets/hero.png",
                    "source_sha256": _sha256_bytes(source),
                    "source_bytes": len(source),
                    "source_media_type": "image/png",
                    "source_width": 320,
                    "source_height": 180,
                    "projected_runtime_path": "assets/hero.webp",
                    "projected_sha256": _sha256_bytes(derivative),
                    "projected_bytes": len(derivative),
                    "projected_media_type": "image/webp",
                    "projected_width": 320,
                    "projected_height": 180,
                    "expected_saving_bytes": len(source) - len(derivative),
                    "replicas": replica_rows,
                    "source_master_preserved": True,
                    "execution_state": "pre-existing-static-artifacts-only",
                }
            ],
            "summary": {
                "transformation_count": 1,
                "source_bytes": len(source),
                "projected_bytes": len(derivative),
                "expected_saving_bytes": len(source) - len(derivative),
                "replica_bytes": len(derivative) * 2,
            },
            "eligible_for_proposal_compilation": False,
            "authority": dict(provenance.NO_AUTHORITY),
        }
    )
    relative_evidence = provenance.MEASUREMENT_ROOT / (f"{run_id}.measurement-static-integrity.v1.json")
    evidence_path = root.joinpath(*relative_evidence.parts)
    evidence_sha = _write_json(evidence_path, document)
    return root, evidence_path, document, evidence_sha


def _rewrite(
    path: Path,
    document: dict[str, Any],
    mutation: Callable[[dict[str, Any]], None],
) -> tuple[dict[str, Any], str]:
    changed = deepcopy(document)
    changed.pop("payload_sha256")
    mutation(changed)
    changed = _with_payload(changed)
    return changed, _write_json(path, changed)


def _verify(root: Path, evidence_path: Path, evidence_sha: str) -> dict[str, Any]:
    return provenance.verify_measurement_provenance_file(
        repo_root=root,
        measurement_path=evidence_path.relative_to(root).as_posix(),
        expected_measurement_sha256=evidence_sha,
    )


def test_valid_static_integrity_fixture_is_verified_but_production_blocked(tmp_path: Path) -> None:
    root, evidence_path, document, evidence_sha = _fixture(tmp_path)
    before = {
        path.relative_to(root).as_posix(): _sha256_bytes(path.read_bytes())
        for path in root.rglob("*")
        if path.is_file()
    }

    result = _verify(root, evidence_path, evidence_sha)

    after = {
        path.relative_to(root).as_posix(): _sha256_bytes(path.read_bytes())
        for path in root.rglob("*")
        if path.is_file()
    }
    assert result == document
    assert before == after
    assert result["state"] == "static-integrity-verified-production-blocked"
    assert result["mode"] == "static-artifact-integrity-only"
    assert result["eligible_for_proposal_compilation"] is False
    assert result["authority"] == provenance.NO_AUTHORITY
    assert all(
        value == "none"
        for key, value in provenance.NO_AUTHORITY.items()
        if key.endswith("authority") or key in {"network_access", "credential_access"}
    )


def test_authority_contract_is_immutable_and_validated_result_is_defensive(tmp_path: Path) -> None:
    root, evidence_path, document, evidence_sha = _fixture(tmp_path)
    assert isinstance(provenance.NO_AUTHORITY, MappingProxyType)
    with pytest.raises(TypeError):
        provenance.NO_AUTHORITY["deployment_authority"] = "granted"  # type: ignore[index]

    result = _verify(root, evidence_path, evidence_sha)
    result["authority"]["deployment_authority"] = "caller-mutated-copy"
    result["transformations"][0]["projected_bytes"] = 1

    assert document["authority"]["deployment_authority"] == "none"
    assert document["transformations"][0]["projected_bytes"] == 80
    assert provenance.NO_AUTHORITY["deployment_authority"] == "none"
    assert provenance.require_static_measurement_integrity is provenance.require_measurement_provenance
    assert (
        provenance.verify_static_measurement_integrity_file is provenance.verify_measurement_provenance_file
    )


def test_rebinding_exported_authority_cannot_change_validation_contract(tmp_path: Path) -> None:
    root, evidence_path, document, _ = _fixture(tmp_path)
    original = provenance.NO_AUTHORITY
    escalated = dict(original)
    escalated["deployment_authority"] = "granted"
    _, changed_sha = _rewrite(
        evidence_path,
        document,
        lambda value: value.__setitem__("authority", dict(escalated)),
    )

    provenance.__dict__["NO_AUTHORITY"] = escalated
    try:
        with pytest.raises(
            provenance.WebsiteRuntimeMeasurementProvenanceError,
            match="authority must remain production-blocked",
        ):
            _verify(root, evidence_path, changed_sha)
    finally:
        provenance.__dict__["NO_AUTHORITY"] = original

    assert provenance.NO_AUTHORITY is original
    assert provenance.NO_AUTHORITY["deployment_authority"] == "none"


@pytest.mark.parametrize(
    ("payload", "expected"),
    [
        (_png(17, 19, 40), ("image/png", 17, 19)),
        (_jpeg(23, 29, 40), ("image/jpeg", 23, 29)),
        (_webp(31, 37, 40), ("image/webp", 31, 37)),
    ],
)
def test_png_jpeg_webp_dimensions_come_from_headers(
    payload: bytes,
    expected: tuple[str, int, int],
) -> None:
    assert provenance._image_probe(payload, label="fixture") == expected


def test_jpeg_probe_does_not_treat_entropy_bytes_after_sos_as_header_segments() -> None:
    fake_sof_in_entropy = b"\xff\xd8\xff\xda\x00\x02\xff\xc0\x00\x07\x08\x00\x13\x00\x11"
    with pytest.raises(
        provenance.WebsiteRuntimeMeasurementProvenanceError,
        match="dimensions are absent",
    ):
        provenance._jpeg_probe(fake_sof_in_entropy)


def test_exact_file_hash_and_payload_hash_tampering_fail_closed(tmp_path: Path) -> None:
    root, evidence_path, document, evidence_sha = _fixture(tmp_path)
    evidence_path.write_bytes(evidence_path.read_bytes() + b" ")
    with pytest.raises(provenance.WebsiteRuntimeMeasurementProvenanceError, match="SHA-256"):
        _verify(root, evidence_path, evidence_sha)

    document["summary"]["projected_bytes"] = 79
    new_sha = _write_json(evidence_path, document)
    with pytest.raises(provenance.WebsiteRuntimeMeasurementProvenanceError, match="payload SHA-256"):
        _verify(root, evidence_path, new_sha)


@pytest.mark.parametrize(
    "invalid_timestamp",
    [
        "2026-08-02Z",
        "2026-08-02 22:30:00Z",
        "2026-08-02T22:30:00.1234567Z",
        "2026-13-02T22:30:00Z",
    ],
)
def test_observed_at_requires_exact_utc_date_time(
    tmp_path: Path,
    invalid_timestamp: str,
) -> None:
    root, evidence_path, document, _ = _fixture(tmp_path)
    _, changed_sha = _rewrite(
        evidence_path,
        document,
        lambda value: value.__setitem__("observed_at", invalid_timestamp),
    )
    with pytest.raises(provenance.WebsiteRuntimeMeasurementProvenanceError, match="observed_at"):
        _verify(root, evidence_path, changed_sha)


def test_observed_at_rejects_more_than_five_minutes_of_future_skew(tmp_path: Path) -> None:
    root, evidence_path, document, _ = _fixture(tmp_path)
    future = (datetime.now(UTC) + timedelta(minutes=6)).isoformat(timespec="seconds").replace("+00:00", "Z")
    _, changed_sha = _rewrite(
        evidence_path,
        document,
        lambda value: value.__setitem__("observed_at", future),
    )
    with pytest.raises(provenance.WebsiteRuntimeMeasurementProvenanceError, match="clock skew"):
        _verify(root, evidence_path, changed_sha)


@pytest.mark.parametrize(
    "mutation",
    [
        lambda value: value.__setitem__("state", "verified"),
        lambda value: value.__setitem__("mode", "encoder-replay"),
        lambda value: value.__setitem__("eligible_for_proposal_compilation", True),
        lambda value: value["authority"].__setitem__("deployment_authority", "granted"),
        lambda value: value["authority"].__setitem__("network_access", "read-only"),
        lambda value: value.__setitem__(
            "schema", "aureon.website-runtime-optimisation-measurement-evidence.v2"
        ),
    ],
)
def test_coherently_rehashed_semantic_fabrication_cannot_grant_authority(
    tmp_path: Path,
    mutation: Callable[[dict[str, Any]], None],
) -> None:
    root, evidence_path, document, _ = _fixture(tmp_path)
    _, changed_sha = _rewrite(evidence_path, document, mutation)
    with pytest.raises(provenance.WebsiteRuntimeMeasurementProvenanceError):
        _verify(root, evidence_path, changed_sha)


def test_replica_tamper_and_non_identical_replica_fail_closed(tmp_path: Path) -> None:
    root, evidence_path, document, evidence_sha = _fixture(tmp_path)
    replica_b = root / document["transformations"][0]["replicas"][1]["path"]
    replica_b.write_bytes(_webp(320, 180, 82))
    with pytest.raises(provenance.WebsiteRuntimeMeasurementProvenanceError, match="byte count"):
        _verify(root, evidence_path, evidence_sha)

    changed_bytes = replica_b.read_bytes()

    def bind_changed_replica(value: dict[str, Any]) -> None:
        replica = value["transformations"][0]["replicas"][1]
        replica["bytes"] = len(changed_bytes)
        replica["file_sha256"] = _sha256_bytes(changed_bytes)

    _, changed_sha = _rewrite(evidence_path, document, bind_changed_replica)
    with pytest.raises(provenance.WebsiteRuntimeMeasurementProvenanceError, match="identical"):
        _verify(root, evidence_path, changed_sha)


@pytest.mark.parametrize(
    "mutation",
    [
        lambda value: value["transformations"][0].__setitem__("projected_width", 319),
        lambda value: value["transformations"][0].__setitem__("expected_saving_bytes", 159),
        lambda value: value["summary"].__setitem__("replica_bytes", 159),
        lambda value: value["transformations"][0].__setitem__("source_master_preserved", False),
        lambda value: value["transformations"][0].__setitem__("execution_state", "executed"),
    ],
)
def test_dimension_arithmetic_summary_and_execution_attacks_fail_closed(
    tmp_path: Path,
    mutation: Callable[[dict[str, Any]], None],
) -> None:
    root, evidence_path, document, _ = _fixture(tmp_path)
    _, changed_sha = _rewrite(evidence_path, document, mutation)
    with pytest.raises(provenance.WebsiteRuntimeMeasurementProvenanceError):
        _verify(root, evidence_path, changed_sha)


def test_path_escape_cross_run_reuse_and_uncontrolled_evidence_path_fail_closed(
    tmp_path: Path,
) -> None:
    root, evidence_path, document, _ = _fixture(tmp_path)

    def escape(value: dict[str, Any]) -> None:
        value["transformations"][0]["replicas"][0]["path"] = "../replica.webp"

    _, escape_sha = _rewrite(evidence_path, document, escape)
    with pytest.raises(provenance.WebsiteRuntimeMeasurementProvenanceError, match="safe relative"):
        _verify(root, evidence_path, escape_sha)

    root, evidence_path, document, _ = _fixture(tmp_path / "second")
    original = root / document["transformations"][0]["replicas"][0]["path"]
    cross_relative = Path(
        str(document["transformations"][0]["replicas"][0]["path"]).replace(
            "static-integrity-fixture", "different-run"
        )
    )
    cross_target = root / cross_relative
    cross_target.parent.mkdir(parents=True)
    shutil.copy2(original, cross_target)

    def cross_run(value: dict[str, Any]) -> None:
        value["transformations"][0]["replicas"][0]["path"] = cross_relative.as_posix()

    _, cross_sha = _rewrite(evidence_path, document, cross_run)
    with pytest.raises(provenance.WebsiteRuntimeMeasurementProvenanceError, match="fixed replica root"):
        _verify(root, evidence_path, cross_sha)

    uncontrolled = root / "evidence.json"
    uncontrolled_sha = _write_json(uncontrolled, document)
    with pytest.raises(provenance.WebsiteRuntimeMeasurementProvenanceError, match="controlled-root"):
        provenance.verify_measurement_provenance_file(
            repo_root=root,
            measurement_path="evidence.json",
            expected_measurement_sha256=uncontrolled_sha,
        )

    wrong_name = root / provenance.MEASUREMENT_ROOT / "wrong.measurement-static-integrity.v1.json"
    wrong_name_sha = _write_json(wrong_name, document)
    with pytest.raises(provenance.WebsiteRuntimeMeasurementProvenanceError, match="exact run_id"):
        provenance.verify_measurement_provenance_file(
            repo_root=root,
            measurement_path=wrong_name.relative_to(root).as_posix(),
            expected_measurement_sha256=wrong_name_sha,
        )


def test_copied_bytes_under_a_new_run_remain_static_only_not_provenance(tmp_path: Path) -> None:
    root, _, document, _ = _fixture(tmp_path)
    changed = deepcopy(document)
    changed.pop("payload_sha256")
    original_run = str(changed["run_id"])
    copied_run = "copied-static-integrity-run"
    source = root.joinpath(*provenance.REPLICA_ROOT.parts, original_run)
    destination = root.joinpath(*provenance.REPLICA_ROOT.parts, copied_run)
    shutil.copytree(source, destination)
    changed["run_id"] = copied_run
    for replica in changed["transformations"][0]["replicas"]:
        replica["path"] = str(replica["path"]).replace(original_run, copied_run)
    changed = _with_payload(changed)

    result = provenance.require_static_measurement_integrity(changed, repo_root=root)

    assert result["mode"] == "static-artifact-integrity-only"
    assert result["eligible_for_proposal_compilation"] is False
    assert result["authority"] == dict(provenance.NO_AUTHORITY)


def test_links_hardlinks_and_source_manifest_drift_fail_closed(tmp_path: Path) -> None:
    root, evidence_path, document, evidence_sha = _fixture(tmp_path)
    replica_a = root / document["transformations"][0]["replicas"][0]["path"]
    replica_b = root / document["transformations"][0]["replicas"][1]["path"]
    replica_b.unlink()
    os.link(replica_a, replica_b)
    with pytest.raises(provenance.WebsiteRuntimeMeasurementProvenanceError, match="single-link"):
        _verify(root, evidence_path, evidence_sha)

    root, evidence_path, _, evidence_sha = _fixture(tmp_path / "drift")
    (root / "website/unrecorded.txt").write_bytes(b"drift")
    with pytest.raises(provenance.WebsiteRuntimeMeasurementProvenanceError, match="complete website tree"):
        _verify(root, evidence_path, evidence_sha)

    root, evidence_path, document, evidence_sha = _fixture(tmp_path / "link")
    replica_b = root / document["transformations"][0]["replicas"][1]["path"]
    target = root / document["transformations"][0]["replicas"][0]["path"]
    replica_b.unlink()
    try:
        replica_b.symlink_to(target)
    except OSError:
        pytest.skip("Symbolic links are unavailable in this environment.")
    with pytest.raises(provenance.WebsiteRuntimeMeasurementProvenanceError, match="link|ordinary"):
        _verify(root, evidence_path, evidence_sha)


def test_repo_root_rejects_a_symlink_or_reparse_ancestor(tmp_path: Path) -> None:
    real_parent = tmp_path / "real-parent"
    (real_parent / "repo").mkdir(parents=True)
    alias = tmp_path / "alias"
    try:
        alias.symlink_to(real_parent, target_is_directory=True)
    except OSError:
        pytest.skip("Directory symbolic links are unavailable in this environment.")

    with pytest.raises(
        provenance.WebsiteRuntimeMeasurementProvenanceError,
        match="link or reparse",
    ):
        provenance._repo_root(alias / "repo")


@pytest.mark.parametrize(
    "unsafe",
    [
        "folder/name. ",
        "folder/name.",
        "folder/na:me.png",
        "folder/na<me.png",
        "folder/e\u0301.png",
        "folder/control\x01.png",
    ],
)
def test_non_portable_alias_prone_paths_are_rejected(unsafe: str) -> None:
    with pytest.raises(provenance.WebsiteRuntimeMeasurementProvenanceError, match="portable|safe relative"):
        provenance._safe_relative(unsafe, label="fixture")


def test_schema_matches_exact_static_integrity_contract() -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["additionalProperties"] is False
    assert schema["properties"]["schema"]["const"] == provenance.MEASUREMENT_SCHEMA
    assert schema["properties"]["state"]["const"] == provenance.VERIFIED_STATE
    assert schema["properties"]["mode"]["const"] == provenance.VERIFICATION_MODE
    assert schema["properties"]["eligible_for_proposal_compilation"]["const"] is False
    assert "provenance-unverified" in schema["description"]
    assert schema["$defs"]["dimension"]["maximum"] == provenance.MAX_DIMENSION
    assert schema["$defs"]["transformation"]["additionalProperties"] is False
    assert schema["$defs"]["sourceManifest"]["additionalProperties"] is False
    assert schema["$defs"]["authority"]["additionalProperties"] is False
    authority_properties = schema["$defs"]["authority"]["properties"]
    assert set(authority_properties) == set(provenance.NO_AUTHORITY)
    for key, value in provenance.NO_AUTHORITY.items():
        assert authority_properties[key]["const"] == value

    path_validator = Draft202012Validator(schema["$defs"]["safeRelativePath"])
    for unsafe in ("folder/name.", "folder/name ", "folder/control\x01.png", "folder/na:me.png"):
        assert not path_validator.is_valid(unsafe)
    timestamp_validator = Draft202012Validator(schema["properties"]["observed_at"])
    assert timestamp_validator.is_valid("2026-08-02T22:30:00Z")
    assert not timestamp_validator.is_valid("2026-08-02Z")
    assert not timestamp_validator.is_valid("2026-08-02 22:30:00Z")


def test_module_has_no_encoder_subprocess_writer_or_network_surface() -> None:
    source = (REPO_ROOT / provenance.IMPLEMENTATION_PATH).read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports = {
        alias.name.split(".", 1)[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    imports.update(
        node.module.split(".", 1)[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    )
    assert imports.isdisjoint({"subprocess", "socket", "urllib", "requests", "shutil", "tempfile"})
    called_attributes = {
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    }
    assert called_attributes.isdisjoint(
        {"write_bytes", "write_text", "mkdir", "unlink", "rename", "replace", "rmdir"}
    )


def test_attestation_rebinds_canonical_paths_and_exact_current_bytes(monkeypatch) -> None:
    launcher = REPO_ROOT / provenance.TRUSTED_LAUNCHER_PATH
    module = REPO_ROOT / provenance.IMPLEMENTATION_PATH
    attestation = {
        "launcher_path": str(launcher),
        "launcher_sha256": _sha256_bytes(launcher.read_bytes()),
        "module_path": str(module),
        "module_sha256": _sha256_bytes(module.read_bytes()),
        "repo_root": str(REPO_ROOT),
        "isolated": True,
        "no_site": True,
        "dont_write_bytecode": True,
    }
    key = "__aureon_runtime_measurement_provenance_launcher_attestation__"

    forged_path = dict(attestation)
    forged_path["launcher_path"] = str(REPO_ROOT / "tools/forged-launcher.py")
    monkeypatch.setitem(provenance.__dict__, key, forged_path)
    with pytest.raises(
        provenance.WebsiteRuntimeMeasurementProvenanceError,
        match="exact canonical source paths",
    ):
        provenance._launcher_attestation()

    forged_hash = dict(attestation)
    forged_hash["module_sha256"] = "A" * 64
    monkeypatch.setitem(provenance.__dict__, key, forged_hash)
    with pytest.raises(provenance.WebsiteRuntimeMeasurementProvenanceError, match="SHA-256"):
        provenance._launcher_attestation()

    monkeypatch.setitem(provenance.__dict__, key, attestation)
    assert provenance._launcher_attestation() == attestation
    assert "reviewed pins" in provenance.__doc__.lower()


def test_isolated_launcher_authenticates_exact_launcher_and_module_hashes(tmp_path: Path) -> None:
    root, evidence_path, _, evidence_sha = _fixture(tmp_path)
    module_source = REPO_ROOT / provenance.IMPLEMENTATION_PATH
    launcher_source = REPO_ROOT / provenance.TRUSTED_LAUNCHER_PATH
    module_target = root / provenance.IMPLEMENTATION_PATH
    launcher_target = root / provenance.TRUSTED_LAUNCHER_PATH
    module_target.parent.mkdir(parents=True, exist_ok=True)
    launcher_target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(module_source, module_target)
    shutil.copy2(launcher_source, launcher_target)
    module_hash = _sha256_bytes(module_target.read_bytes())
    launcher_hash = _sha256_bytes(launcher_target.read_bytes())
    base_args = [
        str(launcher_target),
        "--expected-launcher-sha256",
        launcher_hash,
        "--expected-module-sha256",
        module_hash,
        "--",
        "--repo-root",
        str(root),
        "--measurement",
        evidence_path.relative_to(root).as_posix(),
        "--expected-measurement-sha256",
        evidence_sha,
    ]

    completed = subprocess.run(
        [sys.executable, "-I", "-S", "-B", *base_args],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert completed.returncode == 0, completed.stderr
    assert "static-integrity-valid: provenance-unverified; production-blocked" in completed.stdout

    not_isolated = subprocess.run(
        [sys.executable, *base_args],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert not_isolated.returncode == 2
    assert "requires python -I -S -B" in not_isolated.stderr

    wrong_pin = deepcopy(base_args)
    wrong_pin[2] = "0" * 64
    rejected = subprocess.run(
        [sys.executable, "-I", "-S", "-B", *wrong_pin],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert rejected.returncode == 2
    assert "supplied source pin" in rejected.stderr

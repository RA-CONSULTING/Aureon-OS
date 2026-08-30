from __future__ import annotations

import copy
import hashlib
import json
import os
import shutil
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pytest

from aureon.operator import design_candidate_control as candidate_control
from aureon.operator import design_candidate_motion_policy_compiler as compiler
from aureon.operator import design_candidate_test_evidence as evidence
from aureon.operator import design_motion_performance_budget as motion
from aureon.operator import secure_immutable_artifact

_UNIT_SOURCE_CLOSURE = {
    "files": [
        {"path": path}
        for path in (
            compiler.CANDIDATE_CONTROL_PATH,
            compiler.COMPILER_PATH,
            compiler.MOTION_IMPLEMENTATION_PATH,
            compiler.SECURE_WRITER_PATH,
            compiler.TEST_EVIDENCE_PATH,
        )
    ],
    "manifest_sha256": "0" * 64,
}


@pytest.fixture(autouse=True)
def _stub_full_candidate_control_for_unit_fixture(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(compiler, "candidate_control", candidate_control)
    monkeypatch.setattr(compiler, "candidate_evidence", evidence)
    monkeypatch.setattr(compiler, "motion_budget", motion)
    monkeypatch.setattr(compiler, "secure_immutable_artifact", secure_immutable_artifact)
    monkeypatch.setattr(
        compiler,
        "_prepare_runtime",
        lambda _path, *, repo_root: (Path(repo_root), _UNIT_SOURCE_CLOSURE),
    )

    def assert_unit_loaded_sources(root: Path, _source_closure: object) -> None:
        expected = {
            compiler.COMPILER_PATH: Path(compiler.__file__),
            compiler.CANDIDATE_CONTROL_PATH: Path(candidate_control.__file__),
            compiler.MOTION_IMPLEMENTATION_PATH: Path(motion.__file__),
            compiler.SECURE_WRITER_PATH: Path(secure_immutable_artifact.__file__),
            compiler.TEST_EVIDENCE_PATH: Path(evidence.__file__),
        }
        for relative, source in expected.items():
            if (
                hashlib.sha256((root / relative).read_bytes()).digest()
                != hashlib.sha256(source.read_bytes()).digest()
            ):
                raise compiler.DesignCandidateMotionPolicyCompilerError(
                    "Loaded candidate-motion compiler, motion control, candidate-control, "
                    "or candidate-evidence module bytes do not match current "
                    "repository-controlled source files."
                )

    monkeypatch.setattr(compiler, "_assert_loaded_sources", assert_unit_loaded_sources)
    monkeypatch.setattr(
        compiler.candidate_control,
        "require_candidate_receipt_contract",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        compiler.candidate_control,
        "require_current_work_order_binding",
        lambda *_args, **_kwargs: {},
    )
    monkeypatch.setattr(
        compiler.candidate_control,
        "verify_staged_candidate_receipt",
        lambda *_args, **_kwargs: {
            "schema": compiler.candidate_control.VERIFICATION_SCHEMA,
            "state": "pass",
            "passed": True,
            "release_eligible": False,
            "deployment_authority": "none",
            "checks": [],
        },
    )


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _repo(tmp_path: Path) -> tuple[Path, Path]:
    root = tmp_path / "repo"
    (root / "aureon" / "operator").mkdir(parents=True)
    (root / "artifacts" / "website-operator" / "motion-performance-budget").mkdir(parents=True)
    (root / "website").mkdir()
    (root / "website" / "index.html").write_text("<h1>Canonical</h1>\n", encoding="utf-8")
    (root / "pyproject.toml").write_text("[project]\nname='fixture'\n", encoding="utf-8")
    shutil.copy2(Path(compiler.__file__), root / compiler.COMPILER_PATH)
    shutil.copy2(Path(evidence.__file__), root / compiler.TEST_EVIDENCE_PATH)
    shutil.copy2(Path(motion.__file__), root / compiler.MOTION_IMPLEMENTATION_PATH)
    shutil.copy2(Path(secure_immutable_artifact.__file__), root / compiler.SECURE_WRITER_PATH)
    shutil.copy2(
        Path(compiler.candidate_control.__file__),
        root / compiler.CANDIDATE_CONTROL_PATH,
    )
    shutil.copy2(
        Path(compiler.__file__).parents[2] / compiler.SOURCE_POLICY_PATH,
        root / compiler.SOURCE_POLICY_PATH,
    )
    source_doctrine = (
        Path(compiler.__file__).parents[2]
        / "skills"
        / "aureon-harmonic-design-suite"
        / "references"
        / "design-doctrine.md"
    )
    doctrine = root / motion.DOCTRINE_PATH
    doctrine.parent.mkdir(parents=True)
    shutil.copy2(source_doctrine, doctrine)

    candidate_root = root / "artifacts" / "website-candidates" / "run-001"
    website = candidate_root / "website"
    website.mkdir(parents=True)
    (website / "index.html").write_text("<h1>Candidate</h1>\n", encoding="utf-8")
    (website / "styles.css").write_text(
        "@media (prefers-reduced-motion: reduce) { * { animation: none; } }\n",
        encoding="utf-8",
    )
    summary = evidence._tree_summary(website)  # noqa: SLF001
    receipt = {
        "schema": evidence.CANDIDATE_SCHEMA,
        "validated_at": "2026-07-30T00:00:00Z",
        "state": "validated-local",
        "passed": True,
        "release_eligible": False,
        "deployment_authority": "none",
        "authority": dict(evidence.CANDIDATE_NON_AUTHORITATIVE_AUTHORITY),
        "validation_input": {
            "path": ("artifacts/website-candidates/run-001/candidate-validation-input.v1.json"),
            "file_sha256": "C" * 64,
            "json_sha256": "D" * 64,
            "payload_sha256": "E" * 64,
        },
        "source_closure": _UNIT_SOURCE_CLOSURE,
        "work_order": {
            "run_id": "run-001",
            "path": "artifacts/website-candidates/work-orders/run-001.v4.json",
            "file_sha256": "F" * 64,
            "sha256": "A" * 64,
            "baseline_tree_sha256": "B" * 64,
        },
        "candidate": {
            "root": "artifacts/website-candidates/run-001",
            "website_path": "artifacts/website-candidates/run-001/website",
            "tree_sha256": summary["tree_sha256"],
            "file_count": summary["file_count"],
            "total_bytes": summary["total_bytes"],
        },
        "changes": [],
        "claims": {"declarations": []},
        "claim_surface": {"required": False},
        "checks": [],
        "next_gate": "manual",
    }
    receipt_path = candidate_root / "candidate.v1.json"
    _write_json(receipt_path, receipt)
    return root, receipt_path


def _compile(root: Path, receipt: Path) -> dict[str, Any]:
    return compiler.compile_candidate_motion_config(receipt, repo_root=root)


def _tree_snapshot(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest().upper()
        for path in sorted(
            (candidate for candidate in root.rglob("*") if candidate.is_file()),
            key=lambda candidate: candidate.relative_to(root).as_posix(),
        )
    }


def test_verify_only_cli_path_is_read_only_and_emits_exactly_one_compact_json_line(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsysbinary: pytest.CaptureFixture[bytes],
) -> None:
    root, receipt = _repo(tmp_path)
    compilation = _compile(root, receipt)
    verified = compiler.write_compiled_candidate_motion_config(compilation, repo_root=root)
    before = _tree_snapshot(root)
    original_verify = compiler.verify_compiled_candidate_motion_config_file

    def verify_from_fixture(
        config_path: Path,
        *,
        expected_config_sha256: str,
        candidate_receipt_path: Path,
    ) -> dict[str, Any]:
        return original_verify(
            config_path,
            expected_config_sha256=expected_config_sha256,
            candidate_receipt_path=candidate_receipt_path,
            repo_root=root,
        )

    monkeypatch.chdir(root)
    monkeypatch.setattr(compiler, "_require_sealed_cli_runtime", lambda: None)
    monkeypatch.setattr(
        compiler,
        "verify_compiled_candidate_motion_config_file",
        verify_from_fixture,
    )

    exit_code = compiler.main(
        [
            "--verify-config",
            verified["config_path"],
            "--expected-config-sha256",
            verified["config_file_sha256"],
            "--candidate-receipt",
            receipt.relative_to(root).as_posix(),
        ]
    )

    captured = capsysbinary.readouterr()
    assert exit_code == 0
    assert captured.err == b""
    assert captured.out == compiler._canonical_bytes(verified)  # noqa: SLF001
    assert captured.out.endswith(b"\n") and not captured.out.endswith(b"\n\n")
    assert _tree_snapshot(root) == before


def test_blocked_cli_path_emits_exactly_one_compact_json_line(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsysbinary: pytest.CaptureFixture[bytes],
) -> None:
    root, _ = _repo(tmp_path)
    before = _tree_snapshot(root)
    monkeypatch.chdir(root)
    monkeypatch.setattr(compiler, "_require_sealed_cli_runtime", lambda: None)

    exit_code = compiler.main(["--unsupported"])

    captured = capsysbinary.readouterr()
    payload = json.loads(captured.out)
    assert exit_code == 2
    assert captured.err == b""
    assert payload["state"] == "blocked"
    assert payload["passed"] is False
    assert captured.out == compiler._canonical_bytes(payload)  # noqa: SLF001
    assert captured.out.endswith(b"\n") and not captured.out.endswith(b"\n\n")
    assert _tree_snapshot(root) == before


def test_existing_write_mode_cli_remains_supported(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsysbinary: pytest.CaptureFixture[bytes],
) -> None:
    root, receipt = _repo(tmp_path)
    original_compile = compiler.compile_candidate_motion_config
    original_write = compiler.write_compiled_candidate_motion_config

    def compile_from_fixture(candidate_receipt_path: Path) -> dict[str, Any]:
        return original_compile(candidate_receipt_path, repo_root=root)

    def write_from_fixture(compilation: Mapping[str, Any]) -> dict[str, Any]:
        return original_write(compilation, repo_root=root)

    monkeypatch.chdir(root)
    monkeypatch.setattr(compiler, "_require_sealed_cli_runtime", lambda: None)
    monkeypatch.setattr(compiler, "compile_candidate_motion_config", compile_from_fixture)
    monkeypatch.setattr(compiler, "write_compiled_candidate_motion_config", write_from_fixture)

    exit_code = compiler.main(["--candidate-receipt", receipt.relative_to(root).as_posix()])

    captured = capsysbinary.readouterr()
    payload = json.loads(captured.out)
    assert exit_code == 0
    assert captured.err == b""
    assert payload["schema"] == compiler.VERIFICATION_SCHEMA
    assert payload["passed"] is True
    assert (root / payload["config_path"]).is_file()


def test_compiles_exact_reviewed_thresholds_and_zero_remote_origins(tmp_path: Path) -> None:
    root, receipt = _repo(tmp_path)

    result = _compile(root, receipt)
    config = result["config"]["payload"]

    assert config["thresholds"] == compiler.FIXED_THRESHOLDS
    assert config["remote_origins"] == {"allowed": [], "allow_data_urls": False}
    assert config["policy"] == compiler.FIXED_POLICY
    assert config["source"]["kind"] == "staged-static-tree"
    assert config["source"]["root"] == "artifacts/website-candidates/run-001/website"
    assert config["source"]["tree_sha256"] == result["candidate"]["motion_tree_sha256"]
    assert result["authority"]["worker_threshold_selection"] == "none"


def test_compilation_is_deterministic_and_has_no_time_or_absolute_path(tmp_path: Path) -> None:
    root, receipt = _repo(tmp_path)

    first = _compile(root, receipt)
    second = _compile(root, receipt)

    assert first == second
    encoded = json.dumps(first, sort_keys=True)
    assert str(root) not in encoded
    assert "created_at" not in encoded
    assert "compiled_at" not in encoded


def test_writes_fixed_immutable_path_and_motion_control_accepts_config(tmp_path: Path) -> None:
    root, receipt = _repo(tmp_path)
    compilation = _compile(root, receipt)

    verified = compiler.write_compiled_candidate_motion_config(
        compilation,
        repo_root=root,
    )

    output = root / verified["config_path"]
    assert output == (root / compiler.OUTPUT_ROOT / f"{compilation['config']['config_id']}.json")
    assert verified["passed"] is True
    assert verified["compiler_replayed"] is True
    assert verified["origin_attested"] is False
    assert verified["config_file_sha256"] == evidence._sha256_file(output)  # noqa: SLF001


def test_relaxed_threshold_substitution_fails_even_with_matching_substitute_hash(
    tmp_path: Path,
) -> None:
    root, receipt = _repo(tmp_path)
    compilation = _compile(root, receipt)
    verified = compiler.write_compiled_candidate_motion_config(compilation, repo_root=root)
    output = root / verified["config_path"]
    payload = json.loads(output.read_text(encoding="utf-8"))
    payload["thresholds"]["max_total_bytes"] = 999_999_999
    output.write_text(
        json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    substitute_hash = evidence._sha256_file(output)  # noqa: SLF001

    with pytest.raises(
        compiler.DesignCandidateMotionPolicyCompilerError,
        match="fixed compiler path and bytes",
    ):
        compiler.verify_compiled_candidate_motion_config_file(
            output,
            expected_config_sha256=substitute_hash,
            candidate_receipt_path=receipt,
            repo_root=root,
        )


def test_remote_origin_substitution_fails(tmp_path: Path) -> None:
    root, receipt = _repo(tmp_path)
    compilation = _compile(root, receipt)
    verified = compiler.write_compiled_candidate_motion_config(compilation, repo_root=root)
    output = root / verified["config_path"]
    payload = json.loads(output.read_text(encoding="utf-8"))
    payload["remote_origins"]["allowed"] = ["https://worker.invalid"]
    output.write_text(
        json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
        newline="\n",
    )

    with pytest.raises(compiler.DesignCandidateMotionPolicyCompilerError):
        compiler.verify_compiled_candidate_motion_config_file(
            output,
            expected_config_sha256=evidence._sha256_file(output),  # noqa: SLF001
            candidate_receipt_path=receipt,
            repo_root=root,
        )


def test_copied_config_at_alternate_path_is_policy_shopping(tmp_path: Path) -> None:
    root, receipt = _repo(tmp_path)
    compilation = _compile(root, receipt)
    verified = compiler.write_compiled_candidate_motion_config(compilation, repo_root=root)
    output = root / verified["config_path"]
    alternate = output.with_name("worker-selected.json")
    alternate.write_bytes(output.read_bytes())

    with pytest.raises(
        compiler.DesignCandidateMotionPolicyCompilerError,
        match="fixed compiler path and bytes",
    ):
        compiler.verify_compiled_candidate_motion_config_file(
            alternate,
            expected_config_sha256=verified["config_file_sha256"],
            candidate_receipt_path=receipt,
            repo_root=root,
        )


def test_writer_requires_fresh_same_process_result_and_is_single_use(tmp_path: Path) -> None:
    root, receipt = _repo(tmp_path)
    compilation = _compile(root, receipt)
    forged = copy.deepcopy(compilation)
    forged["compilation_payload_sha256"] = "A" * 64

    with pytest.raises(
        compiler.DesignCandidateMotionPolicyCompilerError,
        match="fresh same-process",
    ):
        compiler.write_compiled_candidate_motion_config(forged, repo_root=root)

    compiler.write_compiled_candidate_motion_config(compilation, repo_root=root)
    with pytest.raises(
        compiler.DesignCandidateMotionPolicyCompilerError,
        match="fresh same-process",
    ):
        compiler.write_compiled_candidate_motion_config(compilation, repo_root=root)


def test_candidate_tree_drift_blocks_compilation(tmp_path: Path) -> None:
    root, receipt = _repo(tmp_path)
    (receipt.parent / "website" / "index.html").write_text(
        "<h1>Changed</h1>\n",
        encoding="utf-8",
    )

    with pytest.raises(
        compiler.DesignCandidateMotionPolicyCompilerError,
        match="single captured byte manifest disagrees",
    ):
        _compile(root, receipt)


def test_candidate_receipt_path_is_exact(tmp_path: Path) -> None:
    root, receipt = _repo(tmp_path)
    alternate = receipt.with_name("worker.json")
    alternate.write_bytes(receipt.read_bytes())

    with pytest.raises(
        compiler.DesignCandidateMotionPolicyCompilerError,
        match="exactly artifacts/website-candidates",
    ):
        _compile(root, alternate)


def test_doctrine_drift_blocks_explicitly(tmp_path: Path) -> None:
    root, receipt = _repo(tmp_path)
    (root / motion.DOCTRINE_PATH).write_text("changed\n", encoding="utf-8")

    with pytest.raises(
        compiler.DesignCandidateMotionPolicyCompilerError,
        match="explicit candidate-motion policy review",
    ):
        _compile(root, receipt)


@pytest.mark.parametrize(
    "relative",
    [
        compiler.COMPILER_PATH,
        compiler.MOTION_IMPLEMENTATION_PATH,
        compiler.TEST_EVIDENCE_PATH,
        compiler.SECURE_WRITER_PATH,
        compiler.CANDIDATE_CONTROL_PATH,
    ],
)
def test_loaded_module_bytes_must_equal_repository_controlled_files(
    tmp_path: Path,
    relative: str,
) -> None:
    root, receipt = _repo(tmp_path)
    path = root / relative
    path.write_bytes(path.read_bytes() + b"\n# drift\n")

    with pytest.raises(
        compiler.DesignCandidateMotionPolicyCompilerError,
        match="Loaded candidate-motion compiler",
    ):
        _compile(root, receipt)


def test_compilation_payload_tampering_is_rejected(tmp_path: Path) -> None:
    root, receipt = _repo(tmp_path)
    compilation = _compile(root, receipt)
    compilation["config"]["payload"]["thresholds"]["max_total_bytes"] = 1

    with pytest.raises(
        compiler.DesignCandidateMotionPolicyCompilerError,
        match="payload hash",
    ):
        compiler.validate_candidate_motion_config_compilation(
            compilation,
            repo_root=root,
        )


def test_validate_only_rejects_bool_for_fixed_integer_even_with_recomputed_outer_hash(
    tmp_path: Path,
) -> None:
    root, receipt = _repo(tmp_path)
    compilation = _compile(root, receipt)
    compilation["config"]["payload"]["thresholds"]["max_media_bytes"] = False
    unsigned = dict(compilation)
    unsigned.pop("compilation_payload_sha256")
    compilation["compilation_payload_sha256"] = compiler._json_sha256(unsigned)  # noqa: SLF001

    with pytest.raises(
        compiler.DesignCandidateMotionPolicyCompilerError,
        match="fixed current compiler replay",
    ):
        compiler.validate_candidate_motion_config_compilation(
            compilation,
            repo_root=root,
        )


def test_verifier_does_not_create_missing_output_directory(tmp_path: Path) -> None:
    root, receipt = _repo(tmp_path)
    compilation = _compile(root, receipt)
    expected = root / compiler.OUTPUT_ROOT / f"{compilation['config']['config_id']}.json"

    with pytest.raises(
        compiler.DesignCandidateMotionPolicyCompilerError,
        match="output directory does not exist",
    ):
        compiler.verify_compiled_candidate_motion_config_file(
            expected,
            expected_config_sha256=compilation["config"]["file_sha256"],
            candidate_receipt_path=receipt,
            repo_root=root,
        )

    assert not expected.parent.exists()


def test_lowercase_expected_hash_is_rejected(tmp_path: Path) -> None:
    root, receipt = _repo(tmp_path)
    compilation = _compile(root, receipt)
    verified = compiler.write_compiled_candidate_motion_config(compilation, repo_root=root)

    with pytest.raises(
        compiler.DesignCandidateMotionPolicyCompilerError,
        match="uppercase SHA-256",
    ):
        compiler.verify_compiled_candidate_motion_config_file(
            root / verified["config_path"],
            expected_config_sha256=verified["config_file_sha256"].lower(),
            candidate_receipt_path=receipt,
            repo_root=root,
        )


def test_v2_config_id_is_full_config_byte_hash_and_exact_write_is_idempotent(
    tmp_path: Path,
) -> None:
    root, receipt = _repo(tmp_path)
    first = _compile(root, receipt)
    first_verified = compiler.write_compiled_candidate_motion_config(first, repo_root=root)
    second = _compile(root, receipt)
    second_verified = compiler.write_compiled_candidate_motion_config(second, repo_root=root)

    assert first["config"]["config_id"] == (f"candidate-motion-v2-{first['config']['file_sha256'].lower()}")
    assert first_verified == second_verified
    assert len(list((root / compiler.OUTPUT_ROOT).glob("*.json"))) == 1


def test_motion_verification_reports_both_single_observation_hashes(tmp_path: Path) -> None:
    root, receipt = _repo(tmp_path)
    compilation = _compile(root, receipt)
    verified = compiler.write_compiled_candidate_motion_config(compilation, repo_root=root)

    assert verified["candidate_tree_sha256"] == compilation["candidate"]["tree_sha256"]
    assert verified["motion_tree_sha256"] == compilation["candidate"]["motion_tree_sha256"]
    assert verified["candidate_tree_algorithm"] == motion.CANDIDATE_TREE_ALGORITHM
    assert verified["motion_tree_algorithm"] == motion.TREE_ALGORITHM
    assert verified["captured_manifest_sha256"] == compilation["candidate"]["captured_manifest_sha256"]


def test_fresh_candidate_revision_coexists_at_new_motion_content_address(
    tmp_path: Path,
) -> None:
    root, receipt_path = _repo(tmp_path)
    first = _compile(root, receipt_path)
    first_verified = compiler.write_compiled_candidate_motion_config(first, repo_root=root)

    website = receipt_path.parent / "website"
    (website / "index.html").write_text("<h1>Revision!</h1>\n", encoding="utf-8")
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    summary = evidence._tree_summary(website)  # noqa: SLF001
    receipt["candidate"].update(summary)
    _write_json(receipt_path, receipt)
    second = _compile(root, receipt_path)
    second_verified = compiler.write_compiled_candidate_motion_config(second, repo_root=root)

    assert first_verified["config_id"] != second_verified["config_id"]
    assert (root / first_verified["config_path"]).is_file()
    assert (root / second_verified["config_path"]).is_file()


def test_same_size_a_b_tree_race_fails_at_single_manifest_binding(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, receipt = _repo(tmp_path)
    target = receipt.parent / "website" / "index.html"
    before = target.read_bytes()
    replacement = b"<h1>Altered!!</h1>\r\n"
    assert len(replacement) == len(before)

    original_verify = compiler.candidate_control.verify_staged_candidate_receipt

    def swap_after_full_verify(*args: Any, **kwargs: Any) -> dict[str, Any]:
        result = original_verify(*args, **kwargs)
        target.write_bytes(replacement)
        return result

    monkeypatch.setattr(
        compiler.candidate_control,
        "verify_staged_candidate_receipt",
        swap_after_full_verify,
    )

    with pytest.raises(
        compiler.DesignCandidateMotionPolicyCompilerError,
        match="single captured byte manifest disagrees",
    ):
        _compile(root, receipt)


def test_candidate_extra_top_level_authority_is_rejected(tmp_path: Path) -> None:
    root, receipt_path = _repo(tmp_path)
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["worker_release_authority"] = True
    _write_json(receipt_path, receipt)

    with pytest.raises(
        compiler.DesignCandidateMotionPolicyCompilerError,
        match="top-level fields are not the exact",
    ):
        _compile(root, receipt_path)


def test_full_candidate_control_failure_blocks_compilation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, receipt = _repo(tmp_path)
    monkeypatch.setattr(
        compiler.candidate_control,
        "verify_staged_candidate_receipt",
        lambda *_args, **_kwargs: {
            "schema": compiler.candidate_control.VERIFICATION_SCHEMA,
            "state": "fail",
            "passed": False,
            "release_eligible": False,
            "deployment_authority": "none",
            "checks": [{"id": "work-order-binding", "passed": False}],
        },
    )

    with pytest.raises(
        compiler.DesignCandidateMotionPolicyCompilerError,
        match="Full staged-candidate and work-order verification did not pass",
    ):
        _compile(root, receipt)


@pytest.mark.skipif(os.name != "nt", reason="NTFS alternate data streams are Windows-specific")
def test_motion_verifier_rejects_ntfs_alternate_stream_path(tmp_path: Path) -> None:
    root, receipt = _repo(tmp_path)
    compilation = _compile(root, receipt)
    verified = compiler.write_compiled_candidate_motion_config(compilation, repo_root=root)
    output = root / verified["config_path"]

    with pytest.raises(
        compiler.DesignCandidateMotionPolicyCompilerError,
        match="alternate data stream",
    ):
        compiler.verify_compiled_candidate_motion_config_file(
            Path(f"{output}:worker"),
            expected_config_sha256=verified["config_file_sha256"],
            candidate_receipt_path=receipt,
            repo_root=root,
        )

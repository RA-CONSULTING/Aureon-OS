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
from aureon.operator import design_candidate_test_evidence as evidence
from aureon.operator import design_candidate_test_policy_compiler as compiler
from aureon.operator import secure_immutable_artifact

_UNIT_SOURCE_CLOSURE = {
    "files": [
        {"path": path}
        for path in (
            compiler.CANDIDATE_CONTROL_TOOL_PATH,
            compiler.COMPILER_TOOL_PATH,
            compiler.SECURE_WRITER_TOOL_PATH,
            compiler.TEST_EVIDENCE_TOOL_PATH,
        )
    ],
    "manifest_sha256": "0" * 64,
}


@pytest.fixture(autouse=True)
def _stub_full_candidate_control_for_unit_fixture(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(compiler, "candidate_control", candidate_control)
    monkeypatch.setattr(compiler, "test_evidence", evidence)
    monkeypatch.setattr(compiler, "secure_immutable_artifact", secure_immutable_artifact)
    monkeypatch.setattr(
        compiler,
        "_prepare_runtime",
        lambda _path, *, repo_root: (Path(repo_root), _UNIT_SOURCE_CLOSURE),
    )

    def assert_unit_loaded_sources(root: Path, _source_closure: object) -> None:
        expected = {
            compiler.COMPILER_TOOL_PATH: Path(compiler.__file__),
            compiler.CANDIDATE_CONTROL_TOOL_PATH: Path(candidate_control.__file__),
            compiler.SECURE_WRITER_TOOL_PATH: Path(secure_immutable_artifact.__file__),
            compiler.TEST_EVIDENCE_TOOL_PATH: Path(evidence.__file__),
        }
        for relative, source in expected.items():
            if (
                hashlib.sha256((root / relative).read_bytes()).digest()
                != hashlib.sha256(source.read_bytes()).digest()
            ):
                raise compiler.DesignCandidateTestPolicyCompilerError(
                    "Loaded compiler, candidate-control, test-evidence, or immutable-artifact "
                    "module bytes do not match the current repository-controlled source files."
                )

    monkeypatch.setattr(
        compiler,
        "_assert_loaded_source_bindings",
        assert_unit_loaded_sources,
    )
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


def _source_config(extra: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    source = Path(compiler.__file__).parents[2] / compiler.SOURCE_POLICY_PATH
    config = json.loads(source.read_text(encoding="utf-8"))
    external = config["checks"]["external"]
    external.extend(extra or [])
    return config


def _repo(tmp_path: Path) -> tuple[Path, Path]:
    root = tmp_path / "repo"
    (root / "aureon" / "operator").mkdir(parents=True)
    (root / "tools").mkdir()
    (root / "artifacts" / "website-operator").mkdir(parents=True)
    (root / "website").mkdir()
    (root / "website" / "index.html").write_text(
        "<h1>Canonical</h1>\n",
        encoding="utf-8",
    )
    (root / "pyproject.toml").write_text(
        "[project]\nname='fixture'\n",
        encoding="utf-8",
    )
    shutil.copy2(
        Path(compiler.__file__),
        root / compiler.COMPILER_TOOL_PATH,
    )
    shutil.copy2(
        Path(evidence.__file__),
        root / compiler.TEST_EVIDENCE_TOOL_PATH,
    )
    shutil.copy2(
        Path(secure_immutable_artifact.__file__),
        root / compiler.SECURE_WRITER_TOOL_PATH,
    )
    shutil.copy2(
        Path(compiler.candidate_control.__file__),
        root / compiler.CANDIDATE_CONTROL_TOOL_PATH,
    )
    (root / compiler.STATIC_QA_TOOL_PATH).write_text(
        "raise SystemExit(0)\n",
        encoding="utf-8",
    )
    (root / compiler.JAVASCRIPT_TOOL_PATH).write_text(
        '"use strict";\nprocess.exitCode = 0;\n',
        encoding="utf-8",
    )
    shutil.copy2(
        Path(compiler.__file__).parents[2] / compiler.SOURCE_POLICY_PATH,
        root / compiler.SOURCE_POLICY_PATH,
    )

    candidate_root = root / "artifacts" / "website-candidates" / "run-001"
    website_root = candidate_root / "website"
    website_root.mkdir(parents=True)
    (website_root / "index.html").write_text(
        "<h1>Candidate</h1>\n",
        encoding="utf-8",
    )
    (website_root / "script.js").write_text(
        "const ready = true;\n",
        encoding="utf-8",
    )
    (website_root / "funding").mkdir()
    (website_root / "funding" / "funding-status.js").write_text(
        "const funding = true;\n",
        encoding="utf-8",
    )
    (website_root / "live").mkdir()
    (website_root / "live" / "live.js").write_text(
        "const live = true;\n",
        encoding="utf-8",
    )
    summary = evidence._tree_summary(website_root)  # noqa: SLF001
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


def _compile(root: Path, receipt_path: Path) -> dict[str, Any]:
    return compiler.compile_candidate_test_policy(
        receipt_path,
        repo_root=root,
    )


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
    verified = compiler.write_compiled_candidate_test_policy(compilation, repo_root=root)
    before = _tree_snapshot(root)
    original_verify = compiler.verify_compiled_candidate_test_policy_file

    def verify_from_fixture(
        policy_path: Path,
        *,
        expected_policy_sha256: str,
        candidate_receipt_path: Path,
    ) -> dict[str, Any]:
        return original_verify(
            policy_path,
            expected_policy_sha256=expected_policy_sha256,
            candidate_receipt_path=candidate_receipt_path,
            repo_root=root,
        )

    monkeypatch.chdir(root)
    monkeypatch.setattr(compiler, "_require_sealed_cli_runtime", lambda: None)
    monkeypatch.setattr(
        compiler,
        "verify_compiled_candidate_test_policy_file",
        verify_from_fixture,
    )

    exit_code = compiler.main(
        [
            "--verify-policy",
            verified["policy_path"],
            "--expected-policy-sha256",
            verified["policy_file_sha256"],
            "--candidate-receipt",
            receipt.relative_to(root).as_posix(),
        ]
    )

    captured = capsysbinary.readouterr()
    assert exit_code == 0
    assert captured.err == b""
    assert captured.out == compiler._canonical_bytes(verified) + b"\n"  # noqa: SLF001
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
    assert captured.out == compiler._canonical_bytes(payload) + b"\n"  # noqa: SLF001
    assert captured.out.endswith(b"\n") and not captured.out.endswith(b"\n\n")
    assert _tree_snapshot(root) == before


def test_existing_write_mode_cli_remains_supported(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsysbinary: pytest.CaptureFixture[bytes],
) -> None:
    root, receipt = _repo(tmp_path)
    original_compile = compiler.compile_candidate_test_policy
    original_write = compiler.write_compiled_candidate_test_policy

    def compile_from_fixture(candidate_receipt_path: Path) -> dict[str, Any]:
        return original_compile(candidate_receipt_path, repo_root=root)

    def write_from_fixture(compilation: Mapping[str, Any]) -> dict[str, Any]:
        return original_write(compilation, repo_root=root)

    monkeypatch.chdir(root)
    monkeypatch.setattr(compiler, "_require_sealed_cli_runtime", lambda: None)
    monkeypatch.setattr(compiler, "compile_candidate_test_policy", compile_from_fixture)
    monkeypatch.setattr(compiler, "write_compiled_candidate_test_policy", write_from_fixture)

    exit_code = compiler.main(["--candidate-receipt", receipt.relative_to(root).as_posix()])

    captured = capsysbinary.readouterr()
    payload = json.loads(captured.out)
    assert exit_code == 0
    assert captured.err == b""
    assert payload["schema"] == compiler.VERIFICATION_SCHEMA
    assert payload["passed"] is True
    assert (root / payload["policy_path"]).is_file()


def test_compiles_exact_order_and_defers_composite_without_passing_it(tmp_path: Path) -> None:
    root, receipt_path = _repo(tmp_path)

    result = _compile(root, receipt_path)

    policy = result["policy"]["payload"]
    assert policy["required_command_ids"] == list(compiler.REQUIRED_COMMAND_IDS)
    assert [row["id"] for row in policy["commands"]] == list(compiler.REQUIRED_COMMAND_IDS)
    assert compiler.COMPOSITE_SOURCE_ID not in policy["required_command_ids"]
    assert result["mapping"]["deferred_source_ids"] == [compiler.COMPOSITE_SOURCE_ID]
    composite = result["mapping"]["source_checks"][-1]
    assert composite == {
        "source_id": compiler.COMPOSITE_SOURCE_ID,
        "source_command_sha256": compiler._json_sha256(  # noqa: SLF001
            list(compiler.EXPECTED_SOURCE_COMMANDS[compiler.COMPOSITE_SOURCE_ID])
        ),
        "disposition": "deferred-to-source-bound-visual-review",
        "candidate_command_id": None,
    }
    assert result["authority"]["composite_visual_gate"] == "deferred-not-passed"


def test_templates_are_fixed_and_worker_has_no_selection_surface(tmp_path: Path) -> None:
    root, receipt_path = _repo(tmp_path)

    result = _compile(root, receipt_path)
    commands = result["policy"]["payload"]["commands"]

    assert commands[0]["template"]["argv"] == [
        "{python}",
        "-I",
        f"{{repo_root}}/{compiler.STATIC_QA_TOOL_PATH}",
        "--mode",
        "website-operator-static",
        "--candidate-root",
        "{candidate_root}",
    ]
    assert commands[1]["template"]["argv"] == [
        "{node}",
        f"{{repo_root}}/{compiler.JAVASCRIPT_TOOL_PATH}",
        "{candidate_root}",
        "script.js",
        "funding/funding-status.js",
        "live/live.js",
    ]
    assert all(command["template"]["cwd"] == "." for command in commands)
    assert all(command["template"]["viewport_widths"] == [] for command in commands)
    assert all(
        command["template"]["required_outputs"] == list(evidence.PROCESS_OUTPUTS) for command in commands
    )


def test_compiler_ignores_poisoned_path_and_binds_only_reviewed_node(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, receipt_path = _repo(tmp_path)
    poisoned = tmp_path / "poisoned-path"
    poisoned.mkdir()
    alternate = poisoned / ("node.exe" if os.name == "nt" else "node")
    alternate.write_bytes(b"attacker-selected-node")
    marker = tmp_path / "ambient-node-compiler.marker"

    def poisoned_which(_name: str) -> str:
        marker.write_text("compiler consulted ambient discovery", encoding="utf-8")
        return str(alternate)

    monkeypatch.setenv("PATH", str(poisoned))
    monkeypatch.setattr(shutil, "which", poisoned_which)

    commands = _compile(root, receipt_path)["policy"]["payload"]["commands"]
    node_template = next(row["template"] for row in commands if row["template"]["engine"] == "node")

    assert node_template["tool_executable_sha256"] == evidence.NODE_TOOLCHAIN_BINDING["sha256"]
    assert not marker.exists()


def test_policy_binds_source_tools_compiler_evidence_and_canonical_site(tmp_path: Path) -> None:
    root, receipt_path = _repo(tmp_path)

    policy = _compile(root, receipt_path)["policy"]["payload"]

    entries = policy["repository_control"]["entries"]
    assert [row["path"] for row in entries] == sorted(
        {
            "pyproject.toml",
            compiler.CANDIDATE_CONTROL_TOOL_PATH,
            compiler.COMPILER_TOOL_PATH,
            compiler.TEST_EVIDENCE_TOOL_PATH,
            compiler.SECURE_WRITER_TOOL_PATH,
            compiler.STATIC_QA_TOOL_PATH,
            compiler.JAVASCRIPT_TOOL_PATH,
            compiler.SOURCE_POLICY_PATH,
        }
    )
    assert policy["repository_control"]["canonical_website_path"] == "website"
    assert (
        policy["repository_control"]["canonical_website_tree_sha256"]
        == evidence._tree_summary(root / "website")["tree_sha256"]  # noqa: SLF001
    )
    assert policy["authority"] == evidence.POLICY_AUTHORITY


def test_compilation_is_deterministic_and_contains_no_absolute_paths_or_timestamp(
    tmp_path: Path,
) -> None:
    root, receipt_path = _repo(tmp_path)

    first = _compile(root, receipt_path)
    second = _compile(root, receipt_path)

    assert first == second
    encoded = json.dumps(first, sort_keys=True)
    assert str(root) not in encoded
    assert "created_at" not in encoded
    assert "compiled_at" not in encoded


def test_writes_immutable_fixed_path_and_replays_through_evidence_parser(tmp_path: Path) -> None:
    root, receipt_path = _repo(tmp_path)
    compilation = _compile(root, receipt_path)

    verified = compiler.write_compiled_candidate_test_policy(
        compilation,
        repo_root=root,
    )

    output = root / verified["policy_path"]
    assert output == (root / compiler.POLICY_OUTPUT_ROOT / f"{compilation['policy']['policy_id']}.json")
    assert verified["passed"] is True
    assert verified["compiler_replayed"] is True
    assert verified["required_command_ids"] == list(compiler.REQUIRED_COMMAND_IDS)
    assert verified["deferred_source_ids"] == [compiler.COMPOSITE_SOURCE_ID]
    assert evidence._sha256_file(output) == compilation["policy"]["file_sha256"]  # noqa: SLF001


def test_policy_file_verifier_rejects_policy_shopping(tmp_path: Path) -> None:
    root, receipt_path = _repo(tmp_path)
    compilation = _compile(root, receipt_path)
    verified = compiler.write_compiled_candidate_test_policy(compilation, repo_root=root)
    output = root / verified["policy_path"]
    replacement = root / compiler.POLICY_OUTPUT_ROOT / "replacement.json"
    replacement.write_bytes(output.read_bytes())

    with pytest.raises(compiler.DesignCandidateTestPolicyCompilerError, match="fixed compiler path"):
        compiler.verify_compiled_candidate_test_policy_file(
            replacement,
            expected_policy_sha256=verified["policy_file_sha256"],
            candidate_receipt_path=receipt_path,
            repo_root=root,
        )


def test_policy_file_verifier_rejects_substitution_even_with_substitute_hash(
    tmp_path: Path,
) -> None:
    root, receipt_path = _repo(tmp_path)
    compilation = _compile(root, receipt_path)
    verified = compiler.write_compiled_candidate_test_policy(compilation, repo_root=root)
    output = root / verified["policy_path"]
    payload = json.loads(output.read_text(encoding="utf-8"))
    payload["required_command_ids"] = list(reversed(payload["required_command_ids"]))
    output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    substitute_hash = evidence._sha256_file(output)  # noqa: SLF001

    with pytest.raises(
        compiler.DesignCandidateTestPolicyCompilerError,
        match="fixed compiler output",
    ):
        compiler.verify_compiled_candidate_test_policy_file(
            output,
            expected_policy_sha256=substitute_hash,
            candidate_receipt_path=receipt_path,
            repo_root=root,
        )


def test_writer_rejects_forged_or_reused_compilation(tmp_path: Path) -> None:
    root, receipt_path = _repo(tmp_path)
    compilation = _compile(root, receipt_path)
    forged = copy.deepcopy(compilation)
    forged["compilation_payload_sha256"] = "A" * 64

    with pytest.raises(compiler.DesignCandidateTestPolicyCompilerError, match="fresh same-process"):
        compiler.write_compiled_candidate_test_policy(forged, repo_root=root)

    compiler.write_compiled_candidate_test_policy(compilation, repo_root=root)
    with pytest.raises(compiler.DesignCandidateTestPolicyCompilerError, match="fresh same-process"):
        compiler.write_compiled_candidate_test_policy(compilation, repo_root=root)


def test_writer_rejects_current_source_drift_after_compile(tmp_path: Path) -> None:
    root, receipt_path = _repo(tmp_path)
    compilation = _compile(root, receipt_path)
    config = _source_config(
        [
            {
                "id": "optional-future",
                "enabled": False,
                "required": False,
                "command": ["node", "future.js"],
            }
        ]
    )
    _write_json(root / compiler.SOURCE_POLICY_PATH, config)

    with pytest.raises(
        compiler.DesignCandidateTestPolicyCompilerError,
        match="source policy bytes changed",
    ):
        compiler.write_compiled_candidate_test_policy(compilation, repo_root=root)


def test_unknown_required_source_check_blocks(tmp_path: Path) -> None:
    root, receipt_path = _repo(tmp_path)
    config = _source_config(
        [
            {
                "id": "worker-selected-check",
                "enabled": True,
                "required": True,
                "command": ["node", "worker.js"],
            }
        ]
    )
    _write_json(root / compiler.SOURCE_POLICY_PATH, config)

    with pytest.raises(
        compiler.DesignCandidateTestPolicyCompilerError,
        match="source policy bytes changed",
    ):
        _compile(root, receipt_path)


def test_unknown_optional_source_check_requires_explicit_review(tmp_path: Path) -> None:
    root, receipt_path = _repo(tmp_path)
    config = _source_config(
        [
            {
                "id": "optional-future",
                "enabled": False,
                "required": False,
                "command": ["node", "future.js"],
            }
        ]
    )
    _write_json(root / compiler.SOURCE_POLICY_PATH, config)

    with pytest.raises(
        compiler.DesignCandidateTestPolicyCompilerError,
        match="source policy bytes changed",
    ):
        _compile(root, receipt_path)


@pytest.mark.parametrize(
    "source_id",
    list(compiler.EXPECTED_SOURCE_IDS),
)
def test_expected_source_check_must_remain_enabled_and_required(
    tmp_path: Path,
    source_id: str,
) -> None:
    root, receipt_path = _repo(tmp_path)
    config = _source_config()
    row = next(item for item in config["checks"]["external"] if item["id"] == source_id)
    row["required"] = False
    _write_json(root / compiler.SOURCE_POLICY_PATH, config)

    with pytest.raises(compiler.DesignCandidateTestPolicyCompilerError, match="source policy bytes changed"):
        _compile(root, receipt_path)


def test_changed_known_source_command_blocks_review(tmp_path: Path) -> None:
    root, receipt_path = _repo(tmp_path)
    config = _source_config()
    config["checks"]["external"][0]["command"].append("--worker-argument")
    _write_json(root / compiler.SOURCE_POLICY_PATH, config)

    with pytest.raises(compiler.DesignCandidateTestPolicyCompilerError, match="source policy bytes changed"):
        _compile(root, receipt_path)


def test_duplicate_source_ids_block(tmp_path: Path) -> None:
    root, receipt_path = _repo(tmp_path)
    config = _source_config()
    config["checks"]["external"].append(copy.deepcopy(config["checks"]["external"][0]))
    _write_json(root / compiler.SOURCE_POLICY_PATH, config)

    with pytest.raises(compiler.DesignCandidateTestPolicyCompilerError, match="source policy bytes changed"):
        _compile(root, receipt_path)


def test_stale_candidate_tree_blocks(tmp_path: Path) -> None:
    root, receipt_path = _repo(tmp_path)
    (receipt_path.parent / "website" / "index.html").write_text(
        "<h1>Changed</h1>\n",
        encoding="utf-8",
    )

    with pytest.raises(
        compiler.DesignCandidateTestPolicyCompilerError,
        match="stale|does not match",
    ):
        _compile(root, receipt_path)


def test_candidate_receipt_must_use_exact_deterministic_path(tmp_path: Path) -> None:
    root, receipt_path = _repo(tmp_path)
    redirected = receipt_path.with_name("worker-receipt.json")
    redirected.write_bytes(receipt_path.read_bytes())

    with pytest.raises(
        compiler.DesignCandidateTestPolicyCompilerError,
        match="exactly artifacts/website-candidates",
    ):
        _compile(root, redirected)


def test_tool_drift_after_compile_blocks_write(tmp_path: Path) -> None:
    root, receipt_path = _repo(tmp_path)
    compilation = _compile(root, receipt_path)
    (root / compiler.JAVASCRIPT_TOOL_PATH).write_text(
        '"use strict";\nprocess.exitCode = 1;\n',
        encoding="utf-8",
    )

    with pytest.raises(
        compiler.DesignCandidateTestPolicyCompilerError,
        match="fixed compiler replay",
    ):
        compiler.write_compiled_candidate_test_policy(compilation, repo_root=root)


def test_loaded_compiler_source_must_equal_controlled_repository_bytes(tmp_path: Path) -> None:
    root, receipt_path = _repo(tmp_path)
    (root / compiler.COMPILER_TOOL_PATH).write_text(
        (root / compiler.COMPILER_TOOL_PATH).read_text(encoding="utf-8") + "\n# drift\n",
        encoding="utf-8",
    )

    with pytest.raises(
        compiler.DesignCandidateTestPolicyCompilerError,
        match="Loaded compiler, candidate-control, test-evidence, or immutable-artifact module bytes",
    ):
        _compile(root, receipt_path)


def test_loaded_evidence_source_must_equal_controlled_repository_bytes(tmp_path: Path) -> None:
    root, receipt_path = _repo(tmp_path)
    (root / compiler.TEST_EVIDENCE_TOOL_PATH).write_text(
        (root / compiler.TEST_EVIDENCE_TOOL_PATH).read_text(encoding="utf-8") + "\n# drift\n",
        encoding="utf-8",
    )

    with pytest.raises(
        compiler.DesignCandidateTestPolicyCompilerError,
        match="Loaded compiler, candidate-control, test-evidence, or immutable-artifact module bytes",
    ):
        _compile(root, receipt_path)


def test_loaded_secure_writer_source_must_equal_controlled_repository_bytes(
    tmp_path: Path,
) -> None:
    root, receipt_path = _repo(tmp_path)
    (root / compiler.SECURE_WRITER_TOOL_PATH).write_text(
        (root / compiler.SECURE_WRITER_TOOL_PATH).read_text(encoding="utf-8") + "\n# drift\n",
        encoding="utf-8",
    )

    with pytest.raises(
        compiler.DesignCandidateTestPolicyCompilerError,
        match="immutable-artifact module bytes",
    ):
        _compile(root, receipt_path)


def test_canonical_site_drift_after_compile_blocks_write(tmp_path: Path) -> None:
    root, receipt_path = _repo(tmp_path)
    compilation = _compile(root, receipt_path)
    (root / "website" / "index.html").write_text(
        "<h1>Canonical changed</h1>\n",
        encoding="utf-8",
    )

    with pytest.raises(
        compiler.DesignCandidateTestPolicyCompilerError,
        match="fixed compiler replay",
    ):
        compiler.write_compiled_candidate_test_policy(compilation, repo_root=root)


def test_compilation_payload_tampering_is_rejected(tmp_path: Path) -> None:
    root, receipt_path = _repo(tmp_path)
    compilation = _compile(root, receipt_path)
    compilation["policy"]["payload"]["commands"][0]["template"]["timeout_seconds"] = 1

    with pytest.raises(compiler.DesignCandidateTestPolicyCompilerError, match="payload hash"):
        compiler.validate_candidate_test_policy_compilation(compilation, repo_root=root)


def test_validate_only_rejects_bool_for_fixed_integer_even_with_recomputed_outer_hash(
    tmp_path: Path,
) -> None:
    root, receipt_path = _repo(tmp_path)
    compilation = _compile(root, receipt_path)
    compilation["policy"]["payload"]["execution"]["retry_count"] = False
    unsigned = dict(compilation)
    unsigned.pop("compilation_payload_sha256")
    compilation["compilation_payload_sha256"] = compiler._json_sha256(unsigned)  # noqa: SLF001

    with pytest.raises(
        compiler.DesignCandidateTestPolicyCompilerError,
        match="fixed compiler replay",
    ):
        compiler.validate_candidate_test_policy_compilation(compilation, repo_root=root)


def test_lowercase_policy_hash_is_rejected(tmp_path: Path) -> None:
    root, receipt_path = _repo(tmp_path)
    compilation = _compile(root, receipt_path)
    verified = compiler.write_compiled_candidate_test_policy(compilation, repo_root=root)

    with pytest.raises(compiler.DesignCandidateTestPolicyCompilerError, match="uppercase SHA-256"):
        compiler.verify_compiled_candidate_test_policy_file(
            root / verified["policy_path"],
            expected_policy_sha256=verified["policy_file_sha256"].lower(),
            candidate_receipt_path=receipt_path,
            repo_root=root,
        )


def test_v2_policy_id_is_full_content_address_and_exact_write_is_idempotent(
    tmp_path: Path,
) -> None:
    root, receipt_path = _repo(tmp_path)
    first = _compile(root, receipt_path)
    first_verified = compiler.write_compiled_candidate_test_policy(first, repo_root=root)
    second = _compile(root, receipt_path)
    second_verified = compiler.write_compiled_candidate_test_policy(second, repo_root=root)

    assert first["policy"]["policy_id"] == (
        f"candidate-suite-v2-{first['policy']['content_core_sha256'].lower()}"
    )
    assert first_verified == second_verified
    assert len(list((root / compiler.POLICY_OUTPUT_ROOT).glob("*.json"))) == 1


def test_fresh_candidate_revision_coexists_at_new_content_address(tmp_path: Path) -> None:
    root, receipt_path = _repo(tmp_path)
    first = _compile(root, receipt_path)
    first_verified = compiler.write_compiled_candidate_test_policy(first, repo_root=root)

    website = receipt_path.parent / "website"
    (website / "index.html").write_text("<h1>Revision!</h1>\n", encoding="utf-8")
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    summary = evidence._tree_summary(website)  # noqa: SLF001
    receipt["candidate"].update(summary)
    _write_json(receipt_path, receipt)
    second = _compile(root, receipt_path)
    second_verified = compiler.write_compiled_candidate_test_policy(second, repo_root=root)

    assert first_verified["policy_id"] != second_verified["policy_id"]
    assert (root / first_verified["policy_path"]).is_file()
    assert (root / second_verified["policy_path"]).is_file()


def test_candidate_extra_top_level_authority_is_rejected(tmp_path: Path) -> None:
    root, receipt_path = _repo(tmp_path)
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["worker_release_authority"] = True
    _write_json(receipt_path, receipt)

    with pytest.raises(
        compiler.DesignCandidateTestPolicyCompilerError,
        match="Candidate receipt fields are not exact",
    ):
        _compile(root, receipt_path)


def test_full_candidate_control_failure_is_not_structural_origin(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, receipt_path = _repo(tmp_path)
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
        compiler.DesignCandidateTestPolicyCompilerError,
        match="Full staged-candidate and work-order verification did not pass",
    ):
        _compile(root, receipt_path)


@pytest.mark.skipif(
    os.name != "nt",
    reason="NTFS alternate data streams are Windows-specific",
)
def test_policy_verifier_rejects_ntfs_alternate_stream_path(tmp_path: Path) -> None:
    root, receipt_path = _repo(tmp_path)
    compilation = _compile(root, receipt_path)
    verified = compiler.write_compiled_candidate_test_policy(compilation, repo_root=root)
    output = root / verified["policy_path"]

    with pytest.raises(
        compiler.DesignCandidateTestPolicyCompilerError,
        match="alternate data stream",
    ):
        compiler.verify_compiled_candidate_test_policy_file(
            Path(f"{output}:worker"),
            expected_policy_sha256=verified["policy_file_sha256"],
            candidate_receipt_path=receipt_path,
            repo_root=root,
        )

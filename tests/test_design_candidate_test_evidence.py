from __future__ import annotations

import copy
import json
import os
import shutil
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import pytest

from aureon.operator import design_candidate_test_evidence as evidence


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    (root / "aureon").mkdir(parents=True)
    (root / "pyproject.toml").write_text("[project]\nname='fixture'\n", encoding="utf-8")
    (root / "website").mkdir()
    (root / "website" / "index.html").write_text(
        "<h1>Canonical</h1>\n",
        encoding="utf-8",
    )
    return root


def _candidate_receipt(root: Path) -> tuple[Path, Path, dict[str, Any]]:
    candidate_root = root / "artifacts" / "website-candidates" / "run-001"
    website_root = candidate_root / "website"
    website_root.mkdir(parents=True)
    (website_root / "index.html").write_text("<h1>Candidate</h1>\n", encoding="utf-8")
    (website_root / "script.js").write_text("const ready = true;\n", encoding="utf-8")
    summary = evidence._tree_summary(website_root)  # noqa: SLF001
    receipt: dict[str, Any] = {
        "schema": evidence.CANDIDATE_SCHEMA,
        "state": "validated-local",
        "passed": True,
        "release_eligible": False,
        "deployment_authority": "none",
        "authority": dict(evidence.CANDIDATE_NON_AUTHORITATIVE_AUTHORITY),
        "candidate": {
            "root": candidate_root.relative_to(root).as_posix(),
            "website_path": website_root.relative_to(root).as_posix(),
            "tree_sha256": summary["tree_sha256"],
            "file_count": summary["file_count"],
            "total_bytes": summary["total_bytes"],
        },
    }
    receipt_path = candidate_root / "candidate-receipt.json"
    _write_json(receipt_path, receipt)
    return receipt_path, website_root, receipt


def _tool(root: Path, name: str, source: str) -> Path:
    path = root / "tools" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8", newline="\n")
    return path


def _command(root: Path, command_id: str, tool: Path, *, timeout: int = 10) -> dict[str, Any]:
    tool_relative = tool.relative_to(root).as_posix()
    template: dict[str, Any] = {
        "engine": "python",
        "argv": [
            "{python}",
            "-I",
            f"{{repo_root}}/{tool_relative}",
            "{candidate_root}",
        ],
        "cwd": ".",
        "timeout_seconds": timeout,
        "viewport_widths": [],
        "trusted_inputs": [
            {
                "path": tool_relative,
                "sha256": evidence._sha256_file(tool),  # noqa: SLF001
            }
        ],
        "tool_executable_sha256": evidence._sha256_file(Path(sys.executable)),  # noqa: SLF001
        "required_outputs": list(evidence.PROCESS_OUTPUTS),
    }
    return {
        "id": command_id,
        "template": template,
        "template_sha256": evidence._json_sha256(template),  # noqa: SLF001
    }


def _policy(
    root: Path,
    commands: list[dict[str, Any]] | None = None,
) -> tuple[Path, str, Path, Path, dict[str, Any]]:
    receipt_path, website_root, _ = _candidate_receipt(root)
    if commands is None:
        tool = _tool(
            root,
            "pass_check.py",
            (
                "from pathlib import Path\n"
                "import sys\n"
                "site = Path(sys.argv[1])\n"
                "raise SystemExit(0 if (site / 'index.html').is_file() else 8)\n"
            ),
        )
        commands = [_command(root, "trusted-pass", tool)]
    candidate_receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    summary = evidence._tree_summary(website_root)  # noqa: SLF001
    repository_entries = [
        {
            "path": "pyproject.toml",
            "kind": "file",
            "sha256": evidence._sha256_file(root / "pyproject.toml"),  # noqa: SLF001
        }
    ]
    for command in commands:
        for trusted in command["template"]["trusted_inputs"]:
            if not any(row["path"] == trusted["path"] for row in repository_entries):
                repository_entries.append(
                    {
                        "path": trusted["path"],
                        "kind": "file",
                        "sha256": trusted["sha256"],
                    }
                )
    repository_entries.sort(key=lambda row: row["path"])
    canonical_summary = evidence._tree_summary(root / "website")  # noqa: SLF001
    policy: dict[str, Any] = {
        "schema": evidence.POLICY_SCHEMA,
        "policy_id": "candidate-suite-v1",
        "candidate": {
            "receipt_path": receipt_path.relative_to(root).as_posix(),
            "receipt_file_sha256": evidence._sha256_file(receipt_path),  # noqa: SLF001
            "receipt_json_sha256": evidence._json_sha256(candidate_receipt),  # noqa: SLF001
            "tree_sha256": summary["tree_sha256"],
        },
        "repository_control": {
            "canonical_website_path": "website",
            "canonical_website_tree_sha256": canonical_summary["tree_sha256"],
            "entries": repository_entries,
            "manifest_sha256": evidence._json_sha256(repository_entries),  # noqa: SLF001
        },
        "required_command_ids": [command["id"] for command in commands],
        "commands": commands,
        "execution": {
            "mode": "ordered-once-fail-fast",
            "shell": False,
            "inherit_environment": False,
            "network": "offline-intent-no-kernel-network-sandbox",
            "output_privacy": "sha256-only",
            "preserve_failures": True,
            "retry_count": 0,
        },
        "authority": dict(evidence.POLICY_AUTHORITY),
    }
    policy_path = root / "artifacts" / "website-operator" / "candidate-test-policy.json"
    _write_json(policy_path, policy)
    return (
        policy_path,
        evidence._sha256_file(policy_path),  # noqa: SLF001
        receipt_path,
        website_root,
        policy,
    )


def _execute(
    root: Path,
    policy_path: Path,
    policy_hash: str,
    policy: dict[str, Any],
) -> dict[str, Any]:
    return evidence.execute_candidate_test_evidence(
        policy_path,
        expected_policy_sha256=policy_hash,
        command_ids=policy["required_command_ids"],
        repo_root=root,
        receipt_id="candidate-tests-fixture",
    )


def test_executes_exact_pinned_suite_and_writes_hash_only_immutable_receipt(
    tmp_path: Path,
) -> None:
    root = _repo(tmp_path)
    policy_path, policy_hash, _, website_root, policy = _policy(root)

    receipt = _execute(root, policy_path, policy_hash, policy)

    assert receipt["passed"] is True
    assert receipt["state"] == "passed"
    assert receipt["authority"] == evidence.EVIDENCE_AUTHORITY
    assert receipt["local_execution"] == evidence.LOCAL_EXECUTION_BOUNDARY
    assert receipt["implementation"] == {
        "candidate_test_evidence_path": evidence.MODULE_PATH,
        "candidate_test_evidence_sha256": evidence._LOADED_SOURCE_SHA256,  # noqa: SLF001
        "secure_immutable_artifact_path": evidence.SECURE_WRITER_PATH,
        "secure_immutable_artifact_sha256": evidence._LOADED_SECURE_WRITER_SHA256,  # noqa: SLF001
    }
    execution = receipt["executions"][0]
    assert execution["attempt"] == 1
    assert execution["retry_count"] == 0
    assert execution["exit_code"] == 0
    assert execution["integrity"]["endpoint_consistent"] is True
    assert (
        execution["integrity"]["evidence_implementation_before"] == evidence._LOADED_SOURCE_SHA256  # noqa: SLF001
    )
    assert (
        execution["integrity"]["secure_writer_implementation_after"] == evidence._LOADED_SECURE_WRITER_SHA256  # noqa: SLF001
    )
    assert isinstance(execution["environment"]["inherited"], list)
    assert set(execution["environment"]["inherited"]) <= {
        "COMSPEC",
        "LOCALAPPDATA",
        "PATHEXT",
        "PROGRAMFILES",
        "PROGRAMFILES(X86)",
        "SYSTEMROOT",
        "TEMP",
        "TMP",
        "WINDIR",
    }
    assert "no-kernel-network-sandbox" in execution["environment"]["network"]
    assert "stdout" not in execution
    assert execution["outputs"]["stdout-sha256"]["retained"] is False
    assert (
        evidence._tree_summary(website_root)["tree_sha256"]
        == receipt["candidate"][  # noqa: SLF001
            "tree_sha256"
        ]
    )
    verification = evidence.validate_candidate_test_evidence_receipt(
        receipt,
        policy_path=policy_path,
        expected_policy_sha256=policy_hash,
        repo_root=root,
    )
    assert verification["passed"] is True
    assert verification["evidence_passed"] is True

    output = root / receipt["candidate"]["root"] / "candidate-test-evidence.json"
    evidence.write_candidate_test_evidence_receipt(
        receipt,
        output,
        policy_path=policy_path,
        expected_policy_sha256=policy_hash,
        repo_root=root,
    )
    output_hash = evidence._sha256_file(output)  # noqa: SLF001
    verified = evidence.verify_candidate_test_evidence_receipt(
        output,
        expected_receipt_file_sha256=output_hash,
        policy_path=policy_path,
        expected_policy_sha256=policy_hash,
        repo_root=root,
    )
    assert verified["receipt_file_sha256"] == output_hash
    with pytest.raises(evidence.DesignCandidateTestEvidenceError, match="fresh same-process"):
        evidence.write_candidate_test_evidence_receipt(
            receipt,
            output,
            policy_path=policy_path,
            expected_policy_sha256=policy_hash,
            repo_root=root,
        )


def test_structural_validator_is_not_origin_attestation_and_writer_requires_fresh_issue(
    tmp_path: Path,
) -> None:
    root = _repo(tmp_path)
    policy_path, policy_hash, _, _, policy = _policy(root)
    issued = _execute(root, policy_path, policy_hash, policy)
    forged = copy.deepcopy(issued)
    forged["receipt_id"] = "candidate-tests-rewritten"
    payload = dict(forged)
    payload.pop("receipt_payload_sha256", None)
    forged["receipt_payload_sha256"] = evidence._json_sha256(payload)  # noqa: SLF001

    structural = evidence.validate_candidate_test_evidence_receipt(
        forged,
        policy_path=policy_path,
        expected_policy_sha256=policy_hash,
        repo_root=root,
    )
    assert structural["passed"] is True
    assert structural["origin_attested"] is False
    assert structural["trusted_orchestration_seal_required"] is True
    output = root / issued["candidate"]["root"] / "forged.json"
    with pytest.raises(evidence.DesignCandidateTestEvidenceError, match="not origin attestation"):
        evidence.write_candidate_test_evidence_receipt(
            forged,
            output,
            policy_path=policy_path,
            expected_policy_sha256=policy_hash,
            repo_root=root,
        )


def test_one_issued_receipt_can_be_claimed_by_only_one_concurrent_writer(
    tmp_path: Path,
) -> None:
    root = _repo(tmp_path)
    policy_path, policy_hash, _, _, policy = _policy(root)
    receipt = _execute(root, policy_path, policy_hash, policy)
    candidate_root = root / receipt["candidate"]["root"]
    outputs = [
        candidate_root / "concurrent-a.json",
        candidate_root / "concurrent-b.json",
    ]
    barrier = threading.Barrier(2)

    def write_once(output: Path) -> str:
        barrier.wait(timeout=10)
        try:
            evidence.write_candidate_test_evidence_receipt(
                receipt,
                output,
                policy_path=policy_path,
                expected_policy_sha256=policy_hash,
                repo_root=root,
            )
        except evidence.DesignCandidateTestEvidenceError:
            return "rejected"
        return "written"

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(write_once, outputs))

    assert sorted(results) == ["rejected", "written"]
    assert sum(output.exists() for output in outputs) == 1


def test_rejects_unpinned_policy_and_duplicate_json_keys(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    policy_path, policy_hash, _, _, policy = _policy(root)
    with pytest.raises(evidence.DesignCandidateTestEvidenceError, match="pinned immutable hash"):
        evidence.execute_candidate_test_evidence(
            policy_path,
            expected_policy_sha256="A" * 64,
            command_ids=policy["required_command_ids"],
            repo_root=root,
        )

    original = policy_path.read_text(encoding="utf-8")
    policy_path.write_text(
        original.replace('"schema":', '"schema": "duplicate", "schema":', 1),
        encoding="utf-8",
    )
    with pytest.raises(evidence.DesignCandidateTestEvidenceError, match="Duplicate JSON key"):
        evidence.execute_candidate_test_evidence(
            policy_path,
            expected_policy_sha256=evidence._sha256_file(policy_path),  # noqa: SLF001
            command_ids=policy["required_command_ids"],
            repo_root=root,
        )


def test_external_policy_pin_rejects_whitespace_only_file_mutation(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    policy_path, policy_hash, _, _, policy = _policy(root)
    policy_path.write_text(
        policy_path.read_text(encoding="utf-8") + " ",
        encoding="utf-8",
    )
    with pytest.raises(
        evidence.DesignCandidateTestEvidenceError,
        match="file bytes.*externally pinned",
    ):
        evidence.execute_candidate_test_evidence(
            policy_path,
            expected_policy_sha256=policy_hash,
            command_ids=policy["required_command_ids"],
            repo_root=root,
        )


def test_rejects_subset_reorder_and_duplicate_command_selection(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    first = _tool(root, "first.py", "raise SystemExit(0)\n")
    second = _tool(root, "second.py", "raise SystemExit(0)\n")
    commands = [_command(root, "first-check", first), _command(root, "second-check", second)]
    policy_path, policy_hash, _, _, _ = _policy(root, commands)
    for selected in (["first-check"], ["second-check", "first-check"], ["first-check", "first-check"]):
        with pytest.raises(evidence.DesignCandidateTestEvidenceError, match="complete ordered"):
            evidence.execute_candidate_test_evidence(
                policy_path,
                expected_policy_sha256=policy_hash,
                command_ids=selected,
                repo_root=root,
            )


@pytest.mark.parametrize("route", ["-c", "-m", "-"])
def test_unused_trusted_tool_argument_cannot_bless_python_alternate_execution(
    tmp_path: Path,
    route: str,
) -> None:
    root = _repo(tmp_path)
    tool = _tool(root, "unused.py", "raise SystemExit(0)\n")
    command = _command(root, "alternate-route", tool)
    command["template"]["argv"] = [
        "{python}",
        "-I",
        route,
        "pytest",
        "{repo_root}/tools/unused.py",
    ]
    command["template_sha256"] = evidence._json_sha256(command["template"])  # noqa: SLF001
    policy_path, policy_hash, _, _, policy = _policy(root, [command])
    with pytest.raises(evidence.DesignCandidateTestEvidenceError, match="script position"):
        _execute(root, policy_path, policy_hash, policy)


def test_unused_trusted_tool_argument_cannot_bless_node_alternate_execution(
    tmp_path: Path,
) -> None:
    node, _ = evidence._resolve_tool("node")  # noqa: SLF001
    root = _repo(tmp_path)
    tool = _tool(root, "unused.js", "process.exit(0);\n")
    relative = tool.relative_to(root).as_posix()
    template: dict[str, Any] = {
        "engine": "node",
        "argv": [
            "{node}",
            "-p",
            "1",
            f"{{repo_root}}/{relative}",
        ],
        "cwd": ".",
        "timeout_seconds": 10,
        "viewport_widths": [],
        "trusted_inputs": [
            {
                "path": relative,
                "sha256": evidence._sha256_file(tool),  # noqa: SLF001
            }
        ],
        "tool_executable_sha256": evidence._sha256_file(node),  # noqa: SLF001
        "required_outputs": list(evidence.PROCESS_OUTPUTS),
    }
    command = {
        "id": "node-alternate-route",
        "template": template,
        "template_sha256": evidence._json_sha256(template),  # noqa: SLF001
    }
    policy_path, policy_hash, _, _, policy = _policy(root, [command])
    with pytest.raises(evidence.DesignCandidateTestEvidenceError, match="script position"):
        _execute(root, policy_path, policy_hash, policy)


def test_reviewed_node_resolution_ignores_poisoned_path_and_discovery(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    poisoned = tmp_path / "poisoned"
    poisoned.mkdir()
    alternate = poisoned / ("node.exe" if os.name == "nt" else "node")
    alternate.write_bytes(b"attacker-selected-node")
    marker = tmp_path / "ambient-node-discovery.marker"

    def poisoned_which(_name: str) -> str:
        marker.write_text("ambient discovery was consulted", encoding="utf-8")
        return str(alternate)

    monkeypatch.setenv("PATH", str(poisoned))
    monkeypatch.setattr(shutil, "which", poisoned_which)

    executable, token = evidence._resolve_tool("node")  # noqa: SLF001

    assert executable == Path(str(evidence.NODE_TOOLCHAIN_BINDING["absolute_path"]))
    assert token == "{node}"
    assert evidence._sha256_file(executable) == evidence.NODE_TOOLCHAIN_BINDING["sha256"]  # noqa: SLF001
    assert not marker.exists()


def test_reviewed_node_resolution_fails_closed_without_ambient_fallback_on_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    poisoned = tmp_path / "poisoned"
    poisoned.mkdir()
    alternate = poisoned / ("node.exe" if os.name == "nt" else "node")
    alternate.write_bytes(b"attacker-selected-node")
    marker = tmp_path / "ambient-node-fallback.marker"
    reviewed = Path(str(evidence.NODE_TOOLCHAIN_BINDING["absolute_path"]))
    original_hash = evidence._sha256_file  # noqa: SLF001

    def poisoned_which(_name: str) -> str:
        marker.write_text("ambient fallback was consulted", encoding="utf-8")
        return str(alternate)

    def drifted_hash(path: Path) -> str:
        if Path(os.path.abspath(path)) == Path(os.path.abspath(reviewed)):
            return "0" * 64
        return original_hash(path)

    monkeypatch.setenv("PATH", str(poisoned))
    monkeypatch.setattr(shutil, "which", poisoned_which)
    monkeypatch.setattr(evidence, "_sha256_file", drifted_hash)

    with pytest.raises(evidence.DesignCandidateTestEvidenceError, match="source-pinned size and SHA-256"):
        evidence._resolve_tool("node")  # noqa: SLF001

    assert not marker.exists()


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (
            lambda command: command["template"]["argv"].__setitem__(2, "-c"),
            "script position",
        ),
        (
            lambda command: command["template"]["argv"].append("TOKEN=value"),
            "environment assignments",
        ),
        (
            lambda command: command["template"]["argv"].append("../../outside"),
            "path escapes",
        ),
        (
            lambda command: command["template"].__setitem__("engine", "shell"),
            "engine is unsupported",
        ),
        (
            lambda command: command["template"].__setitem__("viewport_widths", [375]),
            "unsupported viewport",
        ),
        (
            lambda command: command["template"].__setitem__("viewport_widths", [390]),
            "Only a pinned Playwright",
        ),
    ],
)
def test_rejects_arbitrary_args_env_paths_engines_and_width_claims(
    tmp_path: Path,
    mutation: Any,
    message: str,
) -> None:
    root = _repo(tmp_path)
    tool = _tool(root, "safe.py", "raise SystemExit(0)\n")
    command = _command(root, "safe-check", tool)
    mutation(command)
    command["template_sha256"] = evidence._json_sha256(command["template"])  # noqa: SLF001
    policy_path, policy_hash, _, _, policy = _policy(root, [command])
    with pytest.raises(evidence.DesignCandidateTestEvidenceError, match=message):
        _execute(root, policy_path, policy_hash, policy)


def test_rejects_policy_environment_field_even_when_rehashed(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    policy_path, _, _, _, policy = _policy(root)
    policy["commands"][0]["template"]["env"] = {"TOKEN": "smuggled"}
    policy["commands"][0]["template_sha256"] = evidence._json_sha256(  # noqa: SLF001
        policy["commands"][0]["template"]
    )
    _write_json(policy_path, policy)
    policy_hash = evidence._sha256_file(policy_path)  # noqa: SLF001
    with pytest.raises(evidence.DesignCandidateTestEvidenceError, match="fields are not exact"):
        _execute(root, policy_path, policy_hash, policy)


def test_rejects_stale_candidate_tree_and_candidate_receipt(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    policy_path, policy_hash, receipt_path, website_root, policy = _policy(root)
    (website_root / "index.html").write_text("<h1>Drift</h1>\n", encoding="utf-8")
    with pytest.raises(evidence.DesignCandidateTestEvidenceError, match="stale"):
        _execute(root, policy_path, policy_hash, policy)

    root_two = _repo(tmp_path / "second")
    policy_path, policy_hash, receipt_path, _, policy = _policy(root_two)
    receipt_path.write_text(receipt_path.read_text(encoding="utf-8") + " ", encoding="utf-8")
    with pytest.raises(evidence.DesignCandidateTestEvidenceError, match="stale"):
        _execute(root_two, policy_path, policy_hash, policy)


def test_rejects_candidate_symlink_and_hard_link(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    policy_path, policy_hash, _, website_root, policy = _policy(root)
    target = website_root / "index.html"
    hardlink = website_root / "index-copy.html"
    os.link(target, hardlink)
    with pytest.raises(evidence.DesignCandidateTestEvidenceError, match="hard link"):
        _execute(root, policy_path, policy_hash, policy)

    root_two = _repo(tmp_path / "second")
    policy_path, policy_hash, _, website_root, policy = _policy(root_two)
    link = website_root / "linked.html"
    try:
        link.symlink_to(website_root / "index.html")
    except OSError:
        pytest.skip("Symlink creation is unavailable on this host.")
    with pytest.raises(evidence.DesignCandidateTestEvidenceError, match="link or reparse"):
        _execute(root_two, policy_path, policy_hash, policy)


def test_rejects_hard_linked_trusted_tool(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    tool = _tool(root, "trusted.py", "raise SystemExit(0)\n")
    alias = root / "tools" / "trusted-alias.py"
    os.link(tool, alias)
    command = _command(root, "trusted-check", tool)
    policy_path, policy_hash, _, _, policy = _policy(root, [command])
    with pytest.raises(evidence.DesignCandidateTestEvidenceError, match="exactly one hard link"):
        _execute(root, policy_path, policy_hash, policy)


def test_preserves_nonzero_failure_and_does_not_retry_or_run_later_command(
    tmp_path: Path,
) -> None:
    root = _repo(tmp_path)
    failure = _tool(root, "fail.py", "raise SystemExit(7)\n")
    later = _tool(root, "later.py", "raise SystemExit(0)\n")
    commands = [_command(root, "failing-check", failure), _command(root, "later-check", later)]
    policy_path, policy_hash, _, _, policy = _policy(root, commands)

    receipt = _execute(root, policy_path, policy_hash, policy)

    assert receipt["passed"] is False
    assert receipt["state"] == "failed"
    assert receipt["executions"][0]["state"] == "failed"
    assert receipt["executions"][0]["exit_code"] == 7
    assert receipt["executions"][0]["attempt"] == 1
    assert receipt["executions"][0]["retry_count"] == 0
    assert receipt["executions"][1]["state"] == "not-run-prior-failure"
    assert receipt["executions"][1]["attempt"] == 0
    verification = evidence.validate_candidate_test_evidence_receipt(
        receipt,
        policy_path=policy_path,
        expected_policy_sha256=policy_hash,
        repo_root=root,
    )
    assert verification["passed"] is True
    assert verification["evidence_passed"] is False


def test_preserves_timeout_as_failure_without_retry(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    slow = _tool(root, "slow.py", "import time\ntime.sleep(5)\n")
    command = _command(root, "timeout-check", slow, timeout=1)
    policy_path, policy_hash, _, _, policy = _policy(root, [command])

    receipt = _execute(root, policy_path, policy_hash, policy)

    execution = receipt["executions"][0]
    assert receipt["passed"] is False
    assert execution["state"] == "timed-out"
    assert execution["timed_out"] is True
    assert execution["exit_code"] is None
    assert execution["attempt"] == 1
    assert execution["retry_count"] == 0


def test_fast_oversized_output_is_detected_after_process_exit(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    noisy = _tool(
        root,
        "noisy.py",
        (f"import sys\nsys.stdout.buffer.write(b'x' * ({evidence.MAX_STREAM_BYTES} + 65536))\n"),
    )
    command = _command(root, "output-limit-check", noisy)
    policy_path, policy_hash, _, _, policy = _policy(root, [command])

    receipt = _execute(root, policy_path, policy_hash, policy)

    execution = receipt["executions"][0]
    assert receipt["passed"] is False
    assert execution["state"] == "output-limit-exceeded"
    assert execution["output_limit_exceeded"] is True
    assert execution["outputs"]["stdout-sha256"]["bytes"] > evidence.MAX_STREAM_BYTES
    verification = evidence.validate_candidate_test_evidence_receipt(
        receipt,
        policy_path=policy_path,
        expected_policy_sha256=policy_hash,
        repo_root=root,
    )
    assert verification["evidence_passed"] is False


def test_preserves_tool_version_failure_without_attempt_or_retry(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _repo(tmp_path)
    policy_path, policy_hash, _, _, policy = _policy(root)
    original = evidence._run_process_once  # noqa: SLF001

    def fail_version(*args: Any, **kwargs: Any) -> Any:
        argv = list(args[0])
        if argv[-1] == "--version":
            return 9, False, b"", b"version probe failed", "", False
        return original(*args, **kwargs)

    monkeypatch.setattr(evidence, "_run_process_once", fail_version)
    receipt = _execute(root, policy_path, policy_hash, policy)

    execution = receipt["executions"][0]
    assert receipt["passed"] is False
    assert execution["state"] == "tool-version-failure"
    assert execution["attempt"] == 0
    assert execution["retry_count"] == 0
    assert execution["tool"]["version_exit_code"] == 9
    verification = evidence.validate_candidate_test_evidence_receipt(
        receipt,
        policy_path=policy_path,
        expected_policy_sha256=policy_hash,
        repo_root=root,
    )
    assert verification["passed"] is True
    assert verification["evidence_passed"] is False


def test_detects_canonical_website_mutation_outside_candidate(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    mutator = _tool(
        root,
        "mutate_canonical.py",
        (
            "from pathlib import Path\n"
            "root = Path(__file__).resolve().parents[1]\n"
            "(root / 'website' / 'index.html').write_text('mutated', encoding='utf-8')\n"
        ),
    )
    command = _command(root, "canonical-mutation-probe", mutator)
    policy_path, policy_hash, _, _, policy = _policy(root, [command])

    receipt = _execute(root, policy_path, policy_hash, policy)

    execution = receipt["executions"][0]
    assert receipt["passed"] is False
    assert execution["state"] == "integrity-failure"
    assert (
        execution["integrity"]["canonical_website_before"]
        == policy["repository_control"]["canonical_website_tree_sha256"]
    )
    assert (
        execution["integrity"]["canonical_website_after"]
        != execution["integrity"]["canonical_website_before"]
    )
    assert execution["integrity"]["endpoint_consistent"] is False


def test_detects_pinned_repository_control_mutation_outside_candidate(
    tmp_path: Path,
) -> None:
    root = _repo(tmp_path)
    control = root / "controls" / "sentinel.txt"
    control.parent.mkdir()
    control.write_text("before\n", encoding="utf-8")
    mutator = _tool(
        root,
        "mutate_control.py",
        (
            "from pathlib import Path\n"
            "root = Path(__file__).resolve().parents[1]\n"
            "(root / 'controls' / 'sentinel.txt').write_text('after', encoding='utf-8')\n"
        ),
    )
    command = _command(root, "repository-mutation-probe", mutator)
    policy_path, _, _, _, policy = _policy(root, [command])
    policy["repository_control"]["entries"].append(
        {
            "path": "controls/sentinel.txt",
            "kind": "file",
            "sha256": evidence._sha256_file(control),  # noqa: SLF001
        }
    )
    policy["repository_control"]["entries"].sort(key=lambda row: row["path"])
    policy["repository_control"]["manifest_sha256"] = evidence._json_sha256(  # noqa: SLF001
        policy["repository_control"]["entries"]
    )
    _write_json(policy_path, policy)
    policy_hash = evidence._sha256_file(policy_path)  # noqa: SLF001

    receipt = _execute(root, policy_path, policy_hash, policy)

    execution = receipt["executions"][0]
    assert receipt["passed"] is False
    assert execution["state"] == "integrity-failure"
    assert (
        execution["integrity"]["repository_control_before"] == policy["repository_control"]["manifest_sha256"]
    )
    assert (
        execution["integrity"]["repository_control_after"]
        != execution["integrity"]["repository_control_before"]
    )
    assert execution["integrity"]["endpoint_consistent"] is False


@pytest.mark.parametrize(
    "mutate",
    [
        lambda receipt: receipt.__setitem__("passed", "passed"),
        lambda receipt: receipt["executions"][0].__setitem__("passed", "passed"),
        lambda receipt: receipt["executions"][0].__setitem__("engine", "chromium"),
        lambda receipt: receipt["executions"][0].__setitem__("viewport_widths", [375]),
        lambda receipt: receipt["executions"][0]["outputs"].pop("stderr-sha256"),
        lambda receipt: receipt["executions"][0]["tool"].pop("version_stdout"),
        lambda receipt: receipt["executions"][0].__setitem__("retry_count", 1),
        lambda receipt: receipt["authority"].__setitem__("deployment_authority", "granted"),
    ],
)
def test_strict_replay_rejects_worker_pass_output_engine_retry_and_authority_smuggling(
    tmp_path: Path,
    mutate: Any,
) -> None:
    root = _repo(tmp_path)
    policy_path, policy_hash, _, _, policy = _policy(root)
    receipt = _execute(root, policy_path, policy_hash, policy)
    mutate(receipt)
    payload = dict(receipt)
    payload.pop("receipt_payload_sha256", None)
    receipt["receipt_payload_sha256"] = evidence._json_sha256(payload)  # noqa: SLF001

    with pytest.raises(evidence.DesignCandidateTestEvidenceError):
        evidence.validate_candidate_test_evidence_receipt(
            receipt,
            policy_path=policy_path,
            expected_policy_sha256=policy_hash,
            repo_root=root,
        )


def test_strict_replay_rejects_output_hash_and_payload_tampering(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    policy_path, policy_hash, _, _, policy = _policy(root)
    receipt = _execute(root, policy_path, policy_hash, policy)
    receipt["executions"][0]["outputs"]["stdout-sha256"]["sha256"] = "A" * 64
    with pytest.raises(evidence.DesignCandidateTestEvidenceError, match="payload hash"):
        evidence.validate_candidate_test_evidence_receipt(
            receipt,
            policy_path=policy_path,
            expected_policy_sha256=policy_hash,
            repo_root=root,
        )


def test_writer_rejects_site_tree_and_repository_escape(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    policy_path, policy_hash, _, website_root, policy = _policy(root)
    receipt = _execute(root, policy_path, policy_hash, policy)
    with pytest.raises(evidence.DesignCandidateTestEvidenceError, match="website tree"):
        evidence.write_candidate_test_evidence_receipt(
            receipt,
            website_root / "evidence.json",
            policy_path=policy_path,
            expected_policy_sha256=policy_hash,
            repo_root=root,
        )
    receipt = evidence.execute_candidate_test_evidence(
        policy_path,
        expected_policy_sha256=policy_hash,
        command_ids=policy["required_command_ids"],
        repo_root=root,
        receipt_id="candidate-tests-second-writer-check",
    )
    with pytest.raises(evidence.DesignCandidateTestEvidenceError, match="staged candidate root"):
        evidence.write_candidate_test_evidence_receipt(
            receipt,
            root / "outside.json",
            policy_path=policy_path,
            expected_policy_sha256=policy_hash,
            repo_root=root,
        )


def test_file_verifier_rejects_unpinned_or_hard_linked_receipt(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    policy_path, policy_hash, _, _, policy = _policy(root)
    receipt = _execute(root, policy_path, policy_hash, policy)
    output = root / receipt["candidate"]["root"] / "test-evidence.json"
    evidence.write_candidate_test_evidence_receipt(
        receipt,
        output,
        policy_path=policy_path,
        expected_policy_sha256=policy_hash,
        repo_root=root,
    )
    with pytest.raises(evidence.DesignCandidateTestEvidenceError, match="external immutable hash"):
        evidence.verify_candidate_test_evidence_receipt(
            output,
            expected_receipt_file_sha256="F" * 64,
            policy_path=policy_path,
            expected_policy_sha256=policy_hash,
            repo_root=root,
        )
    alias = output.with_name("test-evidence-alias.json")
    os.link(output, alias)
    with pytest.raises(evidence.DesignCandidateTestEvidenceError, match="exactly one hard link"):
        evidence.verify_candidate_test_evidence_receipt(
            output,
            expected_receipt_file_sha256=evidence._sha256_file(output),  # noqa: SLF001
            policy_path=policy_path,
            expected_policy_sha256=policy_hash,
            repo_root=root,
        )


def test_file_verifier_rejects_duplicate_receipt_keys(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    policy_path, policy_hash, _, _, policy = _policy(root)
    receipt = _execute(root, policy_path, policy_hash, policy)
    output = policy_path.parents[1] / "duplicate-evidence.json"
    raw = json.dumps(receipt, sort_keys=True)
    output.write_text(
        raw.replace('"schema":', '"schema": "duplicate", "schema":', 1),
        encoding="utf-8",
    )
    with pytest.raises(evidence.DesignCandidateTestEvidenceError, match="Duplicate JSON key"):
        evidence.verify_candidate_test_evidence_receipt(
            output,
            expected_receipt_file_sha256=evidence._sha256_file(output),  # noqa: SLF001
            policy_path=policy_path,
            expected_policy_sha256=policy_hash,
            repo_root=root,
        )


def test_candidate_receipt_authority_smuggling_is_rejected(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    policy_path, _, receipt_path, _, policy = _policy(root)
    candidate = json.loads(receipt_path.read_text(encoding="utf-8"))
    candidate["authority"]["deployment_authority"] = "worker"
    _write_json(receipt_path, candidate)
    policy["candidate"]["receipt_file_sha256"] = evidence._sha256_file(receipt_path)  # noqa: SLF001
    policy["candidate"]["receipt_json_sha256"] = evidence._json_sha256(candidate)  # noqa: SLF001
    _write_json(policy_path, policy)
    policy_hash = evidence._sha256_file(policy_path)  # noqa: SLF001
    with pytest.raises(evidence.DesignCandidateTestEvidenceError, match="smuggles authority"):
        _execute(root, policy_path, policy_hash, policy)


def test_public_execution_rejects_loaded_module_source_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _repo(tmp_path)
    policy_path, policy_hash, _, _, policy = _policy(root)
    drifted_source = tmp_path / "drifted_design_candidate_test_evidence.py"
    drifted_source.write_bytes(Path(evidence.__file__).read_bytes() + b"\n# drift\n")
    monkeypatch.setattr(evidence, "__file__", str(drifted_source))

    with pytest.raises(
        evidence.DesignCandidateTestEvidenceError,
        match="Loaded candidate test-evidence module bytes",
    ):
        _execute(root, policy_path, policy_hash, policy)


def test_receipt_rejects_implementation_authority_smuggling(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    policy_path, policy_hash, _, _, policy = _policy(root)
    receipt = _execute(root, policy_path, policy_hash, policy)
    receipt["implementation"]["secure_immutable_artifact_sha256"] = "A" * 64
    unsigned = dict(receipt)
    unsigned.pop("receipt_payload_sha256")
    receipt["receipt_payload_sha256"] = evidence._json_sha256(unsigned)  # noqa: SLF001

    with pytest.raises(
        evidence.DesignCandidateTestEvidenceError,
        match="implementation binding is stale",
    ):
        evidence.validate_candidate_test_evidence_receipt(
            receipt,
            policy_path=policy_path,
            expected_policy_sha256=policy_hash,
            repo_root=root,
        )


@pytest.mark.skipif(os.name != "nt", reason="NTFS alternate data streams are Windows-specific")
def test_receipt_writer_rejects_ntfs_alternate_stream_path(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    policy_path, policy_hash, _, _, policy = _policy(root)
    receipt = _execute(root, policy_path, policy_hash, policy)
    base = root / receipt["candidate"]["root"] / "candidate-test-evidence.json"
    base.write_text("owner\n", encoding="utf-8")

    with pytest.raises(
        evidence.DesignCandidateTestEvidenceError,
        match="alternate data stream",
    ):
        evidence.write_candidate_test_evidence_receipt(
            receipt,
            Path(f"{base}:worker"),
            policy_path=policy_path,
            expected_policy_sha256=policy_hash,
            repo_root=root,
        )

    assert base.read_text(encoding="utf-8") == "owner\n"

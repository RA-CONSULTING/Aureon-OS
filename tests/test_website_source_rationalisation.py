from __future__ import annotations

import ast
import base64
import hashlib
import inspect
import io
import json
import os
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from aureon.operator import website_source_rationalisation as source_control

RUN_ID = "hostile-fixture-plan-001"
PLAN_TIME = datetime(2026, 8, 2, 10, 0, tzinfo=UTC)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _official_launcher_command(root: Path, *planner_args: str) -> list[str]:
    launcher = root / source_control.TRUSTED_LAUNCHER_PATH
    planner = root / source_control.IMPLEMENTATION_PATH
    return [
        sys.executable,
        "-I",
        "-S",
        "-B",
        str(launcher),
        "--expected-launcher-sha256",
        _sha256(launcher),
        "--expected-planner-sha256",
        _sha256(planner),
        "--",
        *planner_args,
    ]


def _fixture_repo(tmp_path: Path) -> tuple[Path, source_control.CommandRunner, list[list[str]]]:
    canonical = source_control._canonical_repo_root()  # noqa: SLF001
    root = tmp_path / "alternate-repo"
    site = root / "website"
    site.mkdir(parents=True)
    (root / "artifacts").mkdir()
    (root / "pyproject.toml").write_text("[project]\nname='fixture'\n", encoding="utf-8")
    (site / "index.html").write_bytes(b"<h1>Aureon</h1>\n")
    (site / "styles.css").write_bytes(b"x" * 360_000)
    (site / "hero.png").write_bytes(b"p" * 2_300_000)
    (site / "proof.webp").write_bytes(b"w" * 2_000_000)
    (site / "unused.txt").write_bytes(b"not in public closure")
    for relative in (
        source_control.IMPLEMENTATION_PATH,
        source_control.TRUSTED_LAUNCHER_PATH,
        source_control.RELEASE_BUILDER_PATH,
        source_control.MOTION_POLICY_PATH,
        source_control.SECURE_WRITER_PATH,
    ):
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(canonical / relative, target)

    retained = ["index.html", "styles.css", "hero.png", "proof.webp"]
    calls: list[list[str]] = []

    def runner(command: Any, cwd: Path, reviewed_source: bytes) -> source_control.CommandResult:
        calls.append(list(command))
        assert cwd == root
        assert hashlib.sha256(reviewed_source).hexdigest().upper() == (
            source_control.REVIEWED_RELEASE_BUILDER_SHA256
        )
        rows = [
            {
                "Path": relative,
                "Bytes": (site / relative).stat().st_size,
                "Sha256": _sha256(site / relative),
            }
            for relative in reversed(retained)
        ]
        payload = {
            "State": "release-plan-verified",
            "Release": source_control.RELEASE,
            "SourceRoot": str(site),
            "FileCount": len(rows),
            "TotalBytes": sum(int(row["Bytes"]) for row in rows),
            "PackageRoot": "/",
            "RemoteRoot": "action-time-confirmation-required",
            "EntryFiles": ["index.html"],
            "Closure": {
                "state": "verified-complete",
                "entry_file_count": 1,
                "discovered_file_count": 3,
                "local_reference_count": 3,
                "included_local_reference_count": 3,
                "missing_local_reference_count": 0,
                "fragment_reference_count": 0,
                "verified_fragment_reference_count": 0,
                "missing_fragment_reference_count": 0,
                "remote_reference_count": 0,
                "non_file_reference_count": 0,
                "remote_origins": [],
                "files_by_extension": {".css": 1, ".html": 1, ".png": 1, ".webp": 1},
            },
            "Files": rows,
        }
        return source_control.CommandResult(0, json.dumps(payload).encode(), b"")

    return root, runner, calls


def _test_plan(root: Path, runner: source_control.CommandRunner) -> dict[str, Any]:
    return source_control._create_test_only_source_rationalisation_plan(  # noqa: SLF001
        repo_root=root,
        runner=runner,
        run_id=RUN_ID,
        now=PLAN_TIME,
    )


def _validation_receipt(*, decision_sha256: str, check_ids: list[str]) -> dict[str, Any]:
    validation: dict[str, Any] = {
        "schema": source_control.OWNER_VALIDATION_SCHEMA,
        "validated_at": "2026-08-02T10:10:00Z",
        "state": "owner-decision-validated-review-only",
        "passed": True,
        "release_eligible": False,
        "authority": dict(source_control.VALIDATION_AUTHORITY),
        "plan": {
            "path": f"{source_control.PLAN_ROOT.as_posix()}/{RUN_ID}.plan.v1.json",
            "file_sha256": "A" * 64,
            "run_id": RUN_ID,
            "payload_sha256": "B" * 64,
        },
        "decision": {
            "path": f"{source_control.OWNER_DECISION_ROOT.as_posix()}/{RUN_ID}.decision.v1.json",
            "file_sha256": decision_sha256,
            "acknowledged_by": "Gary Leckey",
        },
        "checks": [
            {"id": check_id, "passed": True, "message": "exact check", "evidence": {}}
            for check_id in check_ids
        ],
        "next_gate": "Review only; no staging authority.",
    }
    validation["payload_sha256"] = source_control._json_sha256(validation)  # noqa: SLF001
    return validation


def test_fixture_plan_proves_partition_budget_but_has_no_production_authority(
    tmp_path: Path,
) -> None:
    root, runner, calls = _fixture_repo(tmp_path)
    before = {path.name: path.read_bytes() for path in (root / "website").iterdir()}

    plan = _test_plan(root, runner)

    assert {path.name: path.read_bytes() for path in (root / "website").iterdir()} == before
    assert len(calls) == 1
    assert calls[0][-2] == "-EncodedCommand"
    wrapper = base64.b64decode(calls[0][-1]).decode("utf-16-le")
    assert "-VerifyOnly" in wrapper
    assert "-File" not in calls[0]
    execution = plan["execution_binding"]
    assert execution["mode"] == "injected-test-fixture"
    assert execution["runner_id"] == source_control.TEST_FIXTURE_RUNNER_ID
    assert execution["production_writable"] is False
    assert execution["launcher_attested"] is False
    assert execution["reviewed_release_builder_sha256"] == _sha256(root / source_control.RELEASE_BUILDER_PATH)

    source_paths = {row["path"] for row in plan["source_binding"]["files"]}
    retained_paths = {row["path"] for row in plan["retained_projection"]["files"]}
    omitted_paths = {row["path"] for row in plan["omitted_projection"]["files"]}
    assert retained_paths.isdisjoint(omitted_paths)
    assert retained_paths | omitted_paths == source_paths
    assert omitted_paths == {"unused.txt"}
    assert plan["motion_budget_projection"]["violation_ids"] == [
        "resource-byte-budget-exceeded:total",
        "resource-byte-budget-exceeded:image",
        "resource-byte-budget-exceeded:css",
        "single-asset-budget-exceeded",
    ]

    with pytest.raises(source_control.WebsiteSourceRationalisationError):
        source_control.require_source_rationalisation_plan(plan)
    canonical_output = (
        source_control._canonical_repo_root()  # noqa: SLF001
        / source_control.PLAN_ROOT
        / f"{RUN_ID}.plan.v1.json"
    )
    assert not canonical_output.exists()
    with pytest.raises(source_control.WebsiteSourceRationalisationError):
        source_control.write_source_rationalisation_plan(plan, canonical_output)
    assert not canonical_output.exists()
    fixture_plan_path = root / source_control.PLAN_ROOT / f"{RUN_ID}.plan.v1.json"
    fixture_plan_path.parent.mkdir(parents=True)
    fixture_plan_path.write_bytes(source_control._json_artifact_bytes(plan))  # noqa: SLF001
    with pytest.raises(source_control.WebsiteSourceRationalisationError):
        source_control.validate_owner_source_rationalisation_decision(
            fixture_plan_path,
            fixture_plan_path,
        )


def test_public_api_and_cli_reject_alternate_root_and_fabricated_runner(tmp_path: Path) -> None:
    root, runner, _calls = _fixture_repo(tmp_path)
    create_parameters = inspect.signature(source_control.create_source_rationalisation_plan).parameters
    validate_parameters = inspect.signature(
        source_control.validate_owner_source_rationalisation_decision
    ).parameters
    writer_parameters = inspect.signature(source_control.write_owner_validation).parameters
    assert set(create_parameters) == {"run_id"}
    assert set(validate_parameters) == {"plan_path", "decision_path"}
    assert set(writer_parameters) == {"plan_path", "decision_path", "output_path"}
    assert "repo_root" not in create_parameters
    assert "runner" not in create_parameters
    with pytest.raises(TypeError):
        source_control.create_source_rationalisation_plan(repo_root=root)  # type: ignore[call-arg]
    with pytest.raises(TypeError):
        source_control.create_source_rationalisation_plan(runner=runner)  # type: ignore[call-arg]
    with pytest.raises(SystemExit):
        source_control.build_parser().parse_args(
            ["plan", "--repo-root", str(root), "--output", "ignored.json"]
        )


def test_fabricated_validation_checks_and_nonexistent_writer_inputs_fail_closed(
    tmp_path: Path,
) -> None:
    fabricated_ids = ["fabricated-pass", *source_control.OWNER_VALIDATION_CHECK_IDS[1:]]
    fabricated = _validation_receipt(decision_sha256="C" * 64, check_ids=fabricated_ids)
    with pytest.raises(source_control.WebsiteSourceRationalisationError, match="checks are malformed"):
        source_control.require_owner_validation(fabricated)

    root = source_control._canonical_repo_root()  # noqa: SLF001
    output = tmp_path / "must-not-exist.validation.json"
    completed = subprocess.run(
        _official_launcher_command(
            root,
            "validate-decision",
            "--plan",
            str(tmp_path / "missing.plan.json"),
            "--decision",
            str(tmp_path / "missing.decision.json"),
            "--output",
            str(output),
        ),
        cwd=root,
        capture_output=True,
        check=False,
        timeout=30,
    )
    assert completed.returncode == 2
    assert not output.exists()


def test_validation_writer_replay_catches_mutation_before_write(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "writer-replay"
    (root / "artifacts").mkdir(parents=True)
    plan_path = root / "plan.json"
    decision_path = root / "decision.json"
    plan_path.write_text("plan\n", encoding="utf-8")
    decision_path.write_text("decision-before\n", encoding="utf-8")
    output = root / source_control.VALIDATION_ROOT / f"{RUN_ID}.validation.v1.json"
    writes: list[Path] = []

    class FakeWriter:
        @staticmethod
        def write_new_file(path: Path, _payload: bytes) -> None:
            writes.append(path)

    def fake_validate(_plan: Path, decision: Path, *, now: datetime) -> dict[str, Any]:
        del now
        return _validation_receipt(
            decision_sha256=_sha256(decision),
            check_ids=list(source_control.OWNER_VALIDATION_CHECK_IDS),
        )

    def mutate_then_load(_root: Path) -> FakeWriter:
        decision_path.write_text("decision-after\n", encoding="utf-8")
        return FakeWriter()

    monkeypatch.setattr(source_control, "_canonical_repo_root", lambda: root)
    monkeypatch.setattr(source_control, "_require_trusted_launcher_attestation", lambda _root: None)
    monkeypatch.setattr(source_control, "_validate_owner_source_rationalisation_decision", fake_validate)
    monkeypatch.setattr(source_control, "_load_reviewed_secure_writer", mutate_then_load)

    with pytest.raises(source_control.WebsiteSourceRationalisationError, match="changed between"):
        source_control.write_owner_validation(plan_path, decision_path, output)
    assert writes == []
    assert not output.exists()


@pytest.mark.parametrize(
    "relative",
    [
        source_control.TRUSTED_LAUNCHER_PATH,
        source_control.RELEASE_BUILDER_PATH,
        source_control.MOTION_POLICY_PATH,
        source_control.SECURE_WRITER_PATH,
    ],
)
def test_reviewed_source_drift_blocks_before_fixture_runner(
    tmp_path: Path,
    relative: Path,
) -> None:
    root, runner, calls = _fixture_repo(tmp_path)
    with (root / relative).open("ab") as stream:
        stream.write(b"\n# hostile drift\n")
    with pytest.raises(source_control.WebsiteSourceRationalisationError, match="reviewed source pin"):
        _test_plan(root, runner)
    assert calls == []


def test_fixed_runner_uses_only_minimal_environment_and_never_retries(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("PATH", str(tmp_path / "attacker-bin"))
    monkeypatch.setenv("PSModulePath", str(tmp_path / "attacker-modules"))
    monkeypatch.setenv("AUREON_UNSAFE_INHERITED", "must-not-cross")
    calls: list[dict[str, Any]] = []
    waits: list[int] = []

    class FakeProcess:
        def __init__(self) -> None:
            self.stdin = io.BytesIO()
            self.stdout = io.BytesIO(b"x" * (source_control.MAX_PROCESS_OUTPUT_BYTES + 1))
            self.stderr = io.BytesIO()
            self.returncode = 0

        def wait(self, timeout: int) -> int:
            waits.append(timeout)
            return self.returncode

        def kill(self) -> None:
            self.returncode = -9

    def fake_popen(*_args: object, **kwargs: Any) -> FakeProcess:
        calls.append(kwargs)
        return FakeProcess()

    monkeypatch.setattr(source_control.subprocess, "Popen", fake_popen)
    builder = (
        source_control._canonical_repo_root() / source_control.RELEASE_BUILDER_PATH  # noqa: SLF001
    ).read_bytes()
    with pytest.raises(source_control.WebsiteSourceRationalisationError, match="exceeded its bound"):
        source_control._default_runner(["fixed"], tmp_path, builder)  # noqa: SLF001
    assert len(calls) == 1
    invocation = calls[0]
    assert invocation["env"] == source_control._sanitized_environment()  # noqa: SLF001
    assert "PATH" not in invocation["env"]
    assert "PSModulePath" not in invocation["env"]
    assert "AUREON_UNSAFE_INHERITED" not in invocation["env"]
    assert invocation["shell"] is False
    assert invocation["stdin"] is subprocess.PIPE
    assert invocation["stdout"] is subprocess.PIPE
    assert invocation["stderr"] is subprocess.PIPE
    assert waits == [source_control.PROCESS_TIMEOUT_SECONDS]


def test_source_pins_review_only_authority_and_no_pre_auth_repo_imports() -> None:
    root = source_control._canonical_repo_root()  # noqa: SLF001
    assert _sha256(root / source_control.TRUSTED_LAUNCHER_PATH) == (
        source_control.REVIEWED_TRUSTED_LAUNCHER_SHA256
    )
    assert _sha256(root / source_control.RELEASE_BUILDER_PATH) == (
        source_control.REVIEWED_RELEASE_BUILDER_SHA256
    )
    assert _sha256(root / source_control.MOTION_POLICY_PATH) == (source_control.REVIEWED_MOTION_POLICY_SHA256)
    assert _sha256(root / source_control.SECURE_WRITER_PATH) == (source_control.REVIEWED_SECURE_WRITER_SHA256)
    assert _sha256(source_control.POWERSHELL_EXECUTABLE) == source_control.REVIEWED_POWERSHELL_SHA256
    assert source_control.OWNER_DECISION_AUTHORITY["staging_authority"] == "none"
    assert "review-only" in str(source_control.OWNER_DECISION_AUTHORITY["scope"])
    decision = {
        "schema": source_control.OWNER_DECISION_SCHEMA,
        "decision": "acknowledged-review-only",
        "scope": "acknowledge-exact-source-rationalisation-proposal",
        "plan_run_id": RUN_ID,
        "plan_file_sha256": "A" * 64,
        "plan_payload_sha256": "B" * 64,
        "source_tree_sha256": "C" * 64,
        "retained_tree_sha256": "D" * 64,
        "omitted_manifest_sha256": "E" * 64,
        "acknowledged_at": "2026-08-02T10:05:00Z",
        "expires_at": "2026-08-02T14:00:00Z",
        "acknowledged_by": "Gary Leckey",
        "note": "Review-only acknowledgement; this grants no staging authority.",
        "authority": dict(source_control.OWNER_DECISION_AUTHORITY),
    }
    assert source_control._require_owner_decision_shape(decision) == decision  # noqa: SLF001
    old_stage_approval = dict(decision)
    old_stage_approval["decision"] = "approved"
    with pytest.raises(source_control.WebsiteSourceRationalisationError):
        source_control._require_owner_decision_shape(old_stage_approval)  # noqa: SLF001

    tree = ast.parse(Path(source_control.__file__).read_text(encoding="utf-8"))
    imports = [node for node in tree.body if isinstance(node, (ast.Import, ast.ImportFrom))]
    assert all(
        not (
            isinstance(node, ast.ImportFrom)
            and isinstance(node.module, str)
            and node.module.startswith("aureon")
        )
        and not (
            isinstance(node, ast.Import) and any(alias.name.startswith("aureon") for alias in node.names)
        )
        for node in imports
    )


def test_isolated_launcher_skips_hostile_package_initializers_and_blocks_planner_drift(
    tmp_path: Path,
) -> None:
    root = tmp_path / "launcher-repo"
    launcher = root / source_control.TRUSTED_LAUNCHER_PATH
    planner = root / source_control.IMPLEMENTATION_PATH
    launcher.parent.mkdir(parents=True)
    planner.parent.mkdir(parents=True)
    shutil.copy2(source_control._canonical_repo_root() / source_control.TRUSTED_LAUNCHER_PATH, launcher)  # noqa: SLF001
    marker = root / "planner-executed.txt"
    sentinel = root / "package-init-executed.txt"
    hostile = f"from pathlib import Path\nPath({str(sentinel)!r}).write_text('unsafe', encoding='utf-8')\n"
    (root / "aureon" / "__init__.py").write_text(hostile, encoding="utf-8")
    (root / "aureon" / "operator" / "__init__.py").write_text(hostile, encoding="utf-8")
    planner.write_text(
        "from pathlib import Path\nimport sys\nPath(sys.argv[1]).write_text('exact-bytes', encoding='utf-8')\n",
        encoding="utf-8",
    )
    command = [
        sys.executable,
        "-I",
        "-S",
        "-B",
        str(launcher),
        "--expected-launcher-sha256",
        _sha256(launcher),
        "--expected-planner-sha256",
        _sha256(planner),
        "--",
        str(marker),
    ]
    completed = subprocess.run(command, cwd=root, capture_output=True, check=False, timeout=30)
    assert completed.returncode == 0
    assert marker.read_text(encoding="utf-8") == "exact-bytes"
    assert not sentinel.exists()

    marker.unlink()
    planner.write_text("raise RuntimeError('drift must not execute')\n", encoding="utf-8")
    drifted = subprocess.run(command, cwd=root, capture_output=True, check=False, timeout=30)
    assert drifted.returncode == 2
    assert b"do not match the supplied source pin" in drifted.stderr
    assert not marker.exists()
    assert not sentinel.exists()


def test_direct_script_and_module_entrypoints_block_without_launcher_attestation(
    tmp_path: Path,
) -> None:
    root = source_control._canonical_repo_root()  # noqa: SLF001
    planner = root / source_control.IMPLEMENTATION_PATH
    output = tmp_path / "must-not-be-created.json"
    direct = subprocess.run(
        [sys.executable, "-I", "-S", "-B", str(planner), "plan", "--output", str(output)],
        cwd=root,
        capture_output=True,
        check=False,
        timeout=30,
    )
    assert direct.returncode == 2
    assert b"isolated-launcher attestation" in direct.stdout
    assert not output.exists()

    module = subprocess.run(
        [
            sys.executable,
            "-B",
            "-m",
            "aureon.operator.website_source_rationalisation",
            "plan",
            "--output",
            str(output),
        ],
        cwd=root,
        capture_output=True,
        check=False,
        timeout=30,
    )
    assert module.returncode == 2
    assert b"isolated-launcher attestation" in module.stdout
    assert not output.exists()


@pytest.mark.skipif(
    not source_control.POWERSHELL_EXECUTABLE.is_file(),
    reason="Pinned Windows PowerShell VerifyOnly builder is unavailable.",
)
def test_real_pinned_verify_only_replay_smoke_without_plan_creation() -> None:
    root = source_control._canonical_repo_root()  # noqa: SLF001
    site = root / source_control.SOURCE_ROOT
    tool = root / source_control.RELEASE_BUILDER_PATH
    sentinel = root / source_control.ARTIFACT_ROOT / "verify-only-no-output"
    existed_before = sentinel.exists()
    source_rows = source_control._manifest(site)  # noqa: SLF001
    closure, retained = source_control._closure_projection(  # noqa: SLF001
        root=root,
        source_rows=source_rows,
        tool_bytes=tool.read_bytes(),
        runner=source_control._default_runner,  # noqa: SLF001
    )
    assert sentinel.exists() is existed_before
    assert closure["verify_only"] is True
    assert closure["tool_sha256"] == source_control.REVIEWED_RELEASE_BUILDER_SHA256
    assert retained
    assert {row["path"] for row in retained}.issubset({row["path"] for row in source_rows})

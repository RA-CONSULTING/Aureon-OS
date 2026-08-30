"""Safety guarantees for the staged-only public website design delivery runner."""

from __future__ import annotations

import ast
import hashlib
import json
import os
import shutil
import sys
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from aureon.autonomous import aureon_public_website_design_runner as runner
from aureon.operator import design_candidate_source_closure as source_closure
from aureon.operator.design_candidate_claim_surface import evaluate_candidate_claim_surface
from aureon.operator.design_investor_copy_quality import (
    NON_AUTHORITATIVE_AUTHORITY as COPY_AUDIT_AUTHORITY,
)
from aureon.operator.live_surface_reconciliation import (
    reconcile_live_surface,
    write_live_surface_reconciliation,
)

NOW = datetime(2026, 7, 28, 20, 0, tzinfo=UTC)


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _delivery_schema_errors(payload: object) -> list[Any]:
    jsonschema = pytest.importorskip("jsonschema")
    schema_path = (
        Path(__file__).resolve().parents[1]
        / "docs"
        / "research"
        / "schemas"
        / "AUREON_PUBLIC_WEBSITE_DESIGN_DELIVERY_RUNNER_V2.schema.json"
    )
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator.check_schema(schema)
    validator = jsonschema.Draft202012Validator(
        schema,
        format_checker=jsonschema.FormatChecker(),
    )
    return sorted(
        validator.iter_errors(payload),
        key=lambda error: (
            tuple(str(part) for part in error.absolute_path),
            tuple(str(part) for part in error.absolute_schema_path),
        ),
    )


def _assert_delivery_schema_valid(payload: object) -> None:
    errors = _delivery_schema_errors(payload)
    leaves = [
        leaf
        for error in errors
        for leaf in (
            [error]
            if not error.context
            else [nested for child in error.context for nested in (child.context or [child])]
        )
    ]
    assert not errors, "\n".join(
        f"{'/'.join(str(part) for part in error.absolute_path)}: {error.message}" for error in leaves
    )


def test_runner_immutable_receipt_write_never_replaces_a_concurrent_writer(tmp_path: Path) -> None:
    target = tmp_path / "artifacts" / "website-delivery" / "run" / "01-work-order-ready.json"
    payloads = [{"writer": "one"}, {"writer": "two"}]

    def write(payload: dict[str, str]) -> str:
        try:
            runner._atomic_write_json(target, payload)  # noqa: SLF001 - direct immutability boundary
        except runner.PublicWebsiteDesignRunnerError:
            return "blocked"
        return "written"

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(write, payloads))

    assert sorted(results) == ["blocked", "written"]
    assert json.loads(target.read_text(encoding="utf-8")) in payloads


def test_runner_secure_writer_failure_never_unlinks_a_lexical_substitute(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "receipts" / "attempt.v2.json"
    substitute = b'{"attacker":"lexical-substitute"}\n'

    def fail_after_substitution(output: Path, _payload: bytes) -> None:
        output.write_bytes(substitute)
        raise runner.SecureImmutableArtifactError("fixture handle-bound failure")

    monkeypatch.setattr(runner, "write_new_file", fail_after_substitution)

    with pytest.raises(runner.PublicWebsiteDesignRunnerError):
        runner._atomic_write_json(target, {"trusted": True})

    assert target.read_bytes() == substitute


def test_runner_rejects_an_artifact_root_symlink_before_path_resolution(tmp_path: Path) -> None:
    _write(tmp_path / "pyproject.toml", "[tool.pytest.ini_options]\n")
    (tmp_path / "aureon").mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    artifact_link = tmp_path / "artifacts"
    try:
        os.symlink(outside, artifact_link, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"Directory symlinks are unavailable on this filesystem: {exc}")

    with pytest.raises(runner.PublicWebsiteDesignRunnerError, match="symbolic link or reparse point"):
        runner._artifact_root(  # noqa: SLF001 - direct path-boundary test
            tmp_path,
            runner.DEFAULT_DELIVERY_ROOT,
            label="Delivery-run artifact root",
        )


def test_runner_rejects_hard_linked_files_and_receipt_chain_records(
    tmp_path: Path,
) -> None:
    _fake_repo(tmp_path)
    delivery_directory = runner._delivery_directory(  # noqa: SLF001 - receipt boundary under test
        tmp_path,
        "hard-linked-receipt",
    )
    receipt = delivery_directory / "01-work-order-ready.json"
    _write(receipt, "{}\n")
    alias = tmp_path / "receipt-alias.json"
    try:
        os.link(receipt, alias)
    except OSError as exc:
        pytest.skip(f"Hard links are unavailable on this filesystem: {exc}")

    with pytest.raises(
        runner.PublicWebsiteDesignRunnerError,
        match="single-link",
    ):
        runner._regular_file_under(  # noqa: SLF001 - file boundary under test
            tmp_path,
            "artifacts/website-candidates/design-delivery-runs/hard-linked-receipt/01-work-order-ready.json",
            label="Delivery receipt",
            allowed_root=delivery_directory,
        )
    with pytest.raises(
        runner.PublicWebsiteDesignRunnerError,
        match="single-link",
    ):
        runner._receipt_records(  # noqa: SLF001 - chain boundary under test
            tmp_path,
            "hard-linked-receipt",
        )


def _fake_repo(root: Path) -> None:
    _write(root / "pyproject.toml", "[tool.pytest.ini_options]\n")
    (root / "aureon" / "operator").mkdir(parents=True)
    source_root = Path(runner.__file__).resolve().parents[2]
    executable_closure = source_closure.build_source_closure(source_root)
    for row in executable_closure["files"]:
        relative = Path(str(row["path"]))
        destination = root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_root / relative, destination)
    _write(root / "aureon" / "operator" / "website_operator.defaults.json", '{"policy":"test"}\n')
    _write(root / "website" / ".htaccess", "Options -Indexes\n")
    _write(
        root / "website" / "index.html",
        "<!doctype html><title>Aureon</title><p>Aureon is an evidence-led test company. "
        "This fixture is not evidence of customer adoption or independent validation.</p>\n",
    )
    _write(root / "website" / "styles.css", "body { color: #123456; }\n")
    register = {
        "schema": "aureon.public-claim-evidence-register.v1",
        "generated_at": "2026-07-28T20:00:00Z",
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


def test_runner_has_no_in_process_compiler_imports() -> None:
    source = Path(runner.__file__).read_text(encoding="utf-8")
    imported: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            imported.add(module)
            imported.update(f"{module}.{alias.name}" for alias in node.names)

    assert not any(
        name.endswith("design_candidate_motion_policy_compiler")
        or name.endswith("design_candidate_test_policy_compiler")
        for name in imported
    )


def test_runner_invokes_one_absolute_sealed_compiler_without_shell_or_retry(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _fake_repo(tmp_path)
    input_path = tmp_path / "artifacts" / "website-operator" / "qa-inputs" / "motion.json"
    receipt_path = tmp_path / "artifacts" / "website-candidates" / "run-001" / "candidate.v1.json"
    _write(input_path, "{}\n")
    _write(receipt_path, "{}\n")
    payload = {"passed": True, "state": "pass"}
    stdout = (
        json.dumps(
            payload,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        + b"\n"
    )
    calls: list[tuple[list[str], dict[str, Any]]] = []

    def fake_run(command: list[str], **kwargs: Any) -> runner._BoundedProcessResult:  # noqa: SLF001
        calls.append((command, kwargs))
        return runner._BoundedProcessResult(  # noqa: SLF001
            returncode=0,
            stdout=stdout,
            stderr=b"",
            stdout_sha256=hashlib.sha256(stdout).hexdigest().upper(),
            stderr_sha256=hashlib.sha256(b"").hexdigest().upper(),
            stdout_bytes=len(stdout),
            stderr_bytes=0,
        )

    monkeypatch.setenv("PATH", str(tmp_path / "poisoned-path"))
    monkeypatch.setenv("PYTHONPATH", str(tmp_path / "poisoned-pythonpath"))
    monkeypatch.setattr(runner, "_run_bounded_sealed_process", fake_run)

    observed = runner._run_sealed_compiler_verification(  # noqa: SLF001
        tmp_path,
        toolchain_name="motion_policy_compiler",
        verify_flag="--verify-config",
        input_path=input_path,
        expected_hash_flag="--expected-config-sha256",
        expected_sha256="A" * 64,
        candidate_receipt_path=receipt_path,
        label="Fixture sealed compiler",
    )

    assert observed == payload
    assert len(calls) == 1
    command, options = calls[0]
    assert command[0] == sys.executable
    assert command[1:4] == ["-I", "-S", "-B"]
    assert Path(command[4]).is_absolute()
    assert Path(command[4]) == tmp_path / runner._QA_TOOLCHAIN_PATHS["motion_policy_compiler"]  # noqa: SLF001
    assert command[5:] == [
        "--verify-config",
        str(input_path),
        "--expected-config-sha256",
        "A" * 64,
        "--candidate-receipt",
        str(receipt_path),
    ]
    assert options == {
        "cwd": tmp_path,
        "environment": runner._sealed_compiler_environment(),  # noqa: SLF001
        "timeout_seconds": runner.SEALED_COMPILER_TIMEOUT_SECONDS,
        "label": "Fixture sealed compiler",
    }
    assert options["environment"]["PATH"] != str(tmp_path / "poisoned-path")
    assert all(not key.startswith("PYTHON") for key in options["environment"])


def _run_bounded_python(
    tmp_path: Path,
    source: str,
    *,
    timeout_seconds: int = 5,
) -> runner._BoundedProcessResult:  # noqa: SLF001
    return runner._run_bounded_sealed_process(  # noqa: SLF001
        [sys.executable, "-I", "-c", source],
        cwd=tmp_path,
        environment=runner._sealed_compiler_environment(),  # noqa: SLF001
        timeout_seconds=timeout_seconds,
        label="Fixture bounded child",
    )


def test_bounded_compiler_capture_accepts_exact_aggregate_limit(tmp_path: Path) -> None:
    result = _run_bounded_python(
        tmp_path,
        f"import sys; sys.stdout.buffer.write(b'x' * {runner.SEALED_COMPILER_MAX_OUTPUT_BYTES})",
    )

    assert result.returncode == 0
    assert result.stdout_bytes == runner.SEALED_COMPILER_MAX_OUTPUT_BYTES
    assert len(result.stdout) == runner.SEALED_COMPILER_MAX_OUTPUT_BYTES
    assert result.stderr == b""


@pytest.mark.parametrize(
    ("stream", "exit_code"),
    [("stdout", 0), ("stderr", 0), ("stderr", 7)],
    ids=("stdout-success", "stderr-success", "stderr-nonzero"),
)
def test_bounded_compiler_capture_kills_cap_plus_one_without_raw_output(
    tmp_path: Path,
    stream: str,
    exit_code: int,
) -> None:
    payload_bytes = runner.SEALED_COMPILER_MAX_OUTPUT_BYTES + 1
    source = (
        "import sys\n"
        f"stream = sys.{stream}.buffer\n"
        f"stream.write(b'raw-secret-' + b'x' * ({payload_bytes} - 11))\n"
        "stream.flush()\n"
        f"raise SystemExit({exit_code})\n"
    )

    with pytest.raises(runner.PublicWebsiteDesignRunnerError, match="aggregate/per-stream") as caught:
        _run_bounded_python(tmp_path, source)

    assert "raw-secret" not in str(caught.value)
    assert "no retry" in str(caught.value)


def test_bounded_compiler_capture_drains_both_pipes_without_deadlock(tmp_path: Path) -> None:
    source = (
        "import sys\n"
        "sys.stdout.buffer.write(b'o' * 40000)\n"
        "sys.stdout.buffer.flush()\n"
        "sys.stderr.buffer.write(b'e' * 40000)\n"
        "sys.stderr.buffer.flush()\n"
    )

    with pytest.raises(runner.PublicWebsiteDesignRunnerError, match="aggregate/per-stream"):
        _run_bounded_python(tmp_path, source)


def test_bounded_compiler_capture_timeout_cleans_child_and_redacts_partial_output(
    tmp_path: Path,
) -> None:
    source = (
        "import sys, time\n"
        "sys.stdout.buffer.write(b'raw-timeout-secret')\n"
        "sys.stdout.buffer.flush()\n"
        "time.sleep(30)\n"
    )

    with pytest.raises(runner.PublicWebsiteDesignRunnerError, match="timed out") as caught:
        _run_bounded_python(tmp_path, source, timeout_seconds=1)

    assert "raw-timeout-secret" not in str(caught.value)
    assert "no retry" in str(caught.value)


def test_bounded_compiler_capture_spawn_error_is_not_retried(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = 0

    def fail_spawn(*_args: Any, **_kwargs: Any) -> Any:
        nonlocal calls
        calls += 1
        raise OSError("raw-spawn-secret")

    monkeypatch.setattr(runner.subprocess, "Popen", fail_spawn)

    with pytest.raises(runner.PublicWebsiteDesignRunnerError, match="could not start") as caught:
        _run_bounded_python(tmp_path, "raise SystemExit(0)")

    assert calls == 1
    assert "raw-spawn-secret" not in str(caught.value)
    assert "no retry" in str(caught.value)


@pytest.mark.parametrize(
    ("raw", "message"),
    [
        (b'{"value":1,"value":2}\n', "strict JSON object"),
        (b'{"value":NaN}\n', "strict JSON object"),
        (b'{"value":1}\n{"other":2}\n', "strict JSON object"),
        (b'{"value": 1}\n', "canonical compact JSON"),
        (b'{"value":1}', "canonical compact JSON"),
        (b"x" * (runner.SEALED_COMPILER_MAX_OUTPUT_BYTES + 1), "exceeded"),
    ],
    ids=("duplicate", "nonfinite", "multiple", "noncanonical", "missing-lf", "oversized"),
)
def test_runner_rejects_ambiguous_or_oversized_compiler_output(
    raw: bytes,
    message: str,
) -> None:
    with pytest.raises(runner.PublicWebsiteDesignRunnerError, match=message):
        runner._strict_compiler_json_object(raw, label="Fixture compiler")  # noqa: SLF001


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


def _aligned_copy_reconciliation(root: Path, run_id: str) -> Path:
    source = (root / "website" / COPY_HTML_PATH).read_bytes()
    receipt = reconcile_live_surface(
        repo_root=root,
        site_root=root / "website",
        base_url="https://example.test/",
        routes=[COPY_HTML_PATH],
        now=NOW,
        opener=lambda request, timeout: _Response(source, request.full_url),
    )
    return write_live_surface_reconciliation(
        receipt,
        root / "artifacts" / "website-operator" / f"{run_id}-alignment.json",
        repo_root=root,
    )


def _brief_audit() -> dict:
    capsule = {
        "route_id": "home",
        "route": "/",
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
    signal = {
        "signal_id": "fixture-first-visit-clarity",
        "signal_kind": "clarity-gap",
        "disposition": "action-requested",
        "priority": "high",
        "requested_response_dimension": "first-visit-clarity",
        "route_scope": "/",
        "claim_ids": ["homepage-claim"],
    }
    feedback_capsule = {
        "route_id": "home",
        "route": "/",
        "signals": [
            {
                "signal": signal,
                "signal_capsule_sha256": runner._json_sha256(signal),
            }
        ],
    }
    return {
        "schema": "aureon.design-evidence-brief-audit.v1",
        "passed": True,
        "brief": {
            "brief_id": "fixture-brief",
            "path": "data/website_operator/investor_site_design_brief.v1.json",
            "sha256": "A" * 64,
            "refresh_by": "2026-08-09T23:59:59Z",
        },
        "research_refresh": {
            "declaration_path": "data/website_operator/design_research_sources.v1.json",
            "declaration_sha256": "D" * 64,
            "state": "current",
            "passed": True,
            "artwork": {"state": "not-cleared", "cleared_for_use": False},
        },
        "stakeholder_feedback": {
            "feedback_id": "fixture-feedback",
            "path": "data/website_operator/design_stakeholder_feedback.v1.json",
            "sha256": "E" * 64,
            "state": "current",
            "passed": True,
            "signal_ids": ["fixture-first-visit-clarity"],
            "signal_capsules_sha256": "F" * 64,
        },
        "claim_control": {
            "register_path": "data/website_operator/public_claim_evidence_register.v1.json",
            "register_sha256": "B" * 64,
            "claim_ids": ["homepage-claim"],
        },
        "source_inputs": [{"id": "fixture", "path": "website/index.html", "sha256": "C" * 64}],
        "route_plan": [
            {
                "id": "home",
                "route": "/",
                "local_path": "index.html",
                "allowed_paths": ["index.html", "styles.css"],
                "claim_ids": ["homepage-claim"],
                "content_order": ["Problem", "Method", "Proof"],
            }
        ],
        "route_claim_capsules": [capsule],
        "route_claim_capsules_sha256": runner._json_sha256([capsule]),
        "route_feedback_capsules": [feedback_capsule],
        "route_feedback_capsules_sha256": runner._json_sha256([feedback_capsule]),
    }


COPY_ROUTE = "/funding/investor-deck/"
COPY_HTML_PATH = "funding/investor-deck/index.html"
COPY_TASK_ID = "DESIGN-COPY-001"


def _investor_copy_html(*, include_static_count: bool) -> str:
    static_count = "<p>Evidence OS currently exposes 11 selected routes.</p>" if include_static_count else ""
    return (
        "<!doctype html><html><head>"
        "<title>Aureon Investor Evidence Platform</title>"
        '<meta name="description" content="A research-led systems company '
        "connecting controlled evidence, accountable delivery and investor-ready "
        'public research.">'
        "</head><body><h1>Research-led systems company</h1>"
        "<p>Evidence OS is the first wedge.</p>"
        "<p>This does not establish independent external validation.</p>"
        "<p>Accountable human control remains required.</p>"
        f"{static_count}</body></html>"
    )


def _copy_brief_audit(root: Path) -> dict:
    claim = {
        "id": "evidence-os",
        "claim": "Controlled test wording that is never copied into the contract.",
        "state": "bounded",
        "boundary": "This does not establish independent external validation.",
        "permitted_wording": ["Evidence OS is the first wedge."],
        "prohibited_inferences": ["external validation"],
        "public_routes": [COPY_ROUTE],
        "expires_on": "2027-07-28",
        "source": {
            "path": f"website/{COPY_HTML_PATH}",
            "sha256": _sha256(root / "website" / COPY_HTML_PATH),
        },
    }
    capsule = {
        "route_id": "investor-reading-room",
        "route": COPY_ROUTE,
        "claims": [claim],
    }
    signal = {
        "signal_id": "fixture-investor-clarity",
        "signal_kind": "clarity-gap",
        "disposition": "action-requested",
        "priority": "high",
        "requested_response_dimension": "business-model-clarity",
        "route_scope": COPY_ROUTE,
        "claim_ids": ["evidence-os"],
    }
    feedback_capsule = {
        "route_id": "investor-reading-room",
        "route": COPY_ROUTE,
        "signals": [
            {
                "signal": signal,
                "signal_capsule_sha256": runner._json_sha256(signal),
            }
        ],
    }
    return {
        "schema": "aureon.design-evidence-brief-audit.v1",
        "passed": True,
        "brief": {
            "brief_id": "fixture-copy-brief",
            "path": "data/website_operator/investor_site_design_brief.v1.json",
            "sha256": "A" * 64,
            "refresh_by": "2026-08-09T23:59:59Z",
        },
        "research_refresh": {
            "declaration_path": "data/website_operator/design_research_sources.v1.json",
            "declaration_sha256": "D" * 64,
            "state": "current",
            "passed": True,
            "artwork": {"state": "not-cleared", "cleared_for_use": False},
        },
        "stakeholder_feedback": {
            "feedback_id": "fixture-copy-feedback",
            "path": "data/website_operator/design_stakeholder_feedback.v1.json",
            "sha256": "E" * 64,
            "state": "current",
            "passed": True,
            "signal_ids": ["fixture-investor-clarity"],
            "signal_capsules_sha256": "F" * 64,
        },
        "claim_control": {
            "register_path": "data/website_operator/public_claim_evidence_register.v1.json",
            "register_sha256": "B" * 64,
            "claim_ids": ["evidence-os"],
        },
        "source_inputs": [
            {
                "id": "fixture-copy",
                "path": f"website/{COPY_HTML_PATH}",
                "sha256": _sha256(root / "website" / COPY_HTML_PATH),
            }
        ],
        "route_plan": [
            {
                "id": "investor-reading-room",
                "route": COPY_ROUTE,
                "local_path": COPY_HTML_PATH,
                "allowed_paths": [COPY_HTML_PATH, "styles.css"],
                "claim_ids": ["evidence-os"],
                "content_order": [
                    "Investment reading frame",
                    "Commercial wedge",
                    "Controlled next step",
                ],
            }
        ],
        "route_claim_capsules": [capsule],
        "route_claim_capsules_sha256": runner._json_sha256([capsule]),
        "route_feedback_capsules": [feedback_capsule],
        "route_feedback_capsules_sha256": runner._json_sha256([feedback_capsule]),
    }


def _write_copy_policy(root: Path) -> None:
    policy = {
        "schema": "aureon.investor-copy-quality-policy.v1",
        "policy_id": "aureon-investor-copy-quality-runner-test",
        "issued_at": (NOW - timedelta(hours=1)).isoformat().replace("+00:00", "Z"),
        "refresh_by": (NOW + timedelta(days=1)).isoformat().replace("+00:00", "Z"),
        "authority": dict(COPY_AUDIT_AUTHORITY),
        "snapshot_max_age_days": 14,
        "routes": [
            {
                "route": COPY_ROUTE,
                "path": COPY_HTML_PATH,
                "rule_ids": [
                    "hype-language",
                    "meta-description",
                    "page-title",
                    "single-h1",
                    "static-operating-count",
                ],
                "required_concept_groups": [
                    {
                        "concept_id": "commercial-wedge",
                        "severity": "blocker",
                        "alternatives": ["evidence os"],
                    }
                ],
            }
        ],
    }
    _write(
        root / "data" / "website_operator" / "investor_copy_quality_policy.v1.json",
        json.dumps(policy, indent=2) + "\n",
    )


def _write_copy_design_cycle(root: Path) -> Path:
    receipt = {
        "schema": "aureon-website-design-job-v1",
        "run_id": "designcopyrunner",
        "generated_at": NOW.isoformat().replace("+00:00", "Z"),
        "work_orders": [
            {
                "id": COPY_TASK_ID,
                "owner": "technical-editor",
                "title": "Remove investor-copy policy blockers from one route",
                "finding": {
                    "code": "copy.investor-quality",
                    "severity": "error",
                    "path": COPY_HTML_PATH,
                    "route": COPY_ROUTE,
                    "blocker_count": 1,
                    "warning_count": 0,
                },
                "allowed_scope": [
                    "artifacts/website-candidates/<run-id>/website/<exact paths declared by v4 work order>"
                ],
                "candidate_work_order_required": True,
                "acceptance": ["Rerun the investor-copy audit against the exact staged candidate."],
            }
        ],
    }
    path = root / "artifacts" / "website-operator" / "design-copy-cycle.json"
    _write(path, json.dumps(receipt, indent=2) + "\n")
    return path


def _patch_brief(monkeypatch, payload: dict) -> None:
    monkeypatch.setattr(
        runner,
        "audit_design_evidence_brief_file",
        lambda **_kwargs: deepcopy(payload),
    )


def _create_and_stage(root: Path, monkeypatch, run_id: str = "runner-style") -> tuple[dict, Path]:
    payload = _brief_audit()
    _patch_brief(monkeypatch, payload)
    job, _ = runner.create_design_delivery_job(
        goal="Refine one bounded investor-facing route.",
        route_id="home",
        reconciliation_receipt=_aligned_reconciliation(root, run_id),
        run_id=run_id,
        repo_root=root,
        now=NOW,
    )
    assert job["state"] == "work-order-ready"
    return runner.stage_design_delivery_job(run_id, repo_root=root, now=NOW)


def _claim_impact(path: str) -> dict[str, str]:
    return {
        "path": path,
        "classification": "no-material-claim-change",
        "rationale": "The bounded staged change was reviewed for its public claim impact.",
    }


def _patch_fake_editorial_import(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    audits: dict[Path, dict] = {}

    def fake_import(
        work_order_path: Path,
        *,
        repo_root: Path | None = None,
        **_kwargs: object,
    ) -> dict:
        assert repo_root is not None
        order = json.loads((repo_root / work_order_path).read_text(encoding="utf-8"))
        control = order["editorial_asset_control"]
        asset_capsule = {
            "asset_id": "fixture-hero",
            "scope": "privacy-safe-test-capsule",
        }
        placement = {
            "route_scope": "/",
            "destination_path": "website/index.html",
            "surface_id": "fixture-home-hero",
            "alt": "Aureon research evidence illustration",
            "caption": "Research evidence translated into a bounded public explanation.",
            "credit": "Artwork supplied for the linked Aureon research article.",
        }
        route_capsule = {
            "route_scope": "/",
            "asset_id": "fixture-hero",
            "public_post_url": "https://example.substack.com/p/fixture-hero",
            "website_variants": [
                {
                    "role": "large",
                    "path": "website/assets/hero.webp",
                    "sha256": "D" * 64,
                    "media_type": "image/webp",
                    "width": 1600,
                    "height": 900,
                }
            ],
            "placement": placement,
        }
        route_capsule["route_asset_capsule_sha256"] = runner._json_sha256(route_capsule)
        selected_capsules_sha256 = runner._json_sha256([asset_capsule])
        audits[repo_root.resolve()] = {
            "passed": True,
            "manifest": {
                "sha256": control["provenance_manifest_sha256"],
            },
            "asset_capsules": [asset_capsule],
            "route_asset_capsules": [route_capsule],
        }
        receipt = {
            "receipt_payload_sha256": "A" * 64,
            "provenance": {
                "manifest_file_sha256": control["provenance_manifest_sha256"],
                "selected_asset_capsules_sha256": selected_capsules_sha256,
                "candidate_ready_asset_ids": ["fixture-hero"],
            },
            "summary": {"imports_sha256": "C" * 64},
            "work_order": {
                "json_sha256": runner._json_sha256(order),
                "baseline_tree_sha256": order["baseline"]["tree_sha256"],
            },
            "imports": [
                {
                    "asset_id": "fixture-hero",
                    "target": (f"artifacts/website-candidates/{order['run_id']}/website/assets/hero.webp"),
                    "route_scopes": ["/"],
                    "destination_paths": ["index.html"],
                    "surface_ids": ["fixture-home-hero"],
                }
            ],
        }
        _write(
            repo_root / control["receipt_path"],
            json.dumps(receipt, indent=2) + "\n",
        )
        return receipt

    def fake_verify(
        _receipt: dict,
        **_kwargs: object,
    ) -> dict:
        return {
            "schema": ("aureon.design-editorial-asset-candidate-import-verification.v1"),
            "state": "verified-local-candidate",
            "passed": True,
        }

    def fake_audit(
        _manifest_path: Path,
        *,
        repo_root: Path | None = None,
        **_kwargs: object,
    ) -> dict:
        assert repo_root is not None
        return deepcopy(audits[repo_root.resolve()])

    monkeypatch.setattr(runner, "import_editorial_assets_to_candidate", fake_import)
    monkeypatch.setattr(
        runner,
        "verify_candidate_editorial_asset_import",
        fake_verify,
    )
    monkeypatch.setattr(
        runner,
        "audit_design_editorial_asset_provenance_file",
        fake_audit,
    )


def _create_and_stage_binary_run(
    root: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    run_id: str,
) -> tuple[dict, Path]:
    _write(root / "website" / "assets" / "hero.webp", "fixture-webp-bytes")
    _write(
        root / "data" / "website_operator" / "editorial_asset_provenance.v1.json",
        '{"schema":"fixture-source-binding"}\n',
    )
    payload = _brief_audit()
    payload["route_plan"][0]["allowed_paths"].append("assets/hero.webp")
    _patch_brief(monkeypatch, payload)
    runner.create_design_delivery_job(
        goal="Refine text around one trusted editorial asset.",
        route_id="home",
        reconciliation_receipt=_aligned_reconciliation(root, run_id),
        run_id=run_id,
        repo_root=root,
        now=NOW,
    )
    return runner.stage_design_delivery_job(run_id, repo_root=root, now=NOW)


def test_runner_derives_staged_worker_context_and_never_mutates_canonical_site(
    tmp_path: Path, monkeypatch
) -> None:
    _fake_repo(tmp_path)
    canonical_before = (tmp_path / "website" / "styles.css").read_text(encoding="utf-8")

    staged_job, staged_path = _create_and_stage(tmp_path, monkeypatch)
    context = runner.worker_context_for_delivery_job("runner-style", repo_root=tmp_path, now=NOW)
    _assert_delivery_schema_valid(staged_job)
    _assert_delivery_schema_valid(context)

    assert staged_job["state"] == "candidate-staged"
    assert staged_path.exists()
    assert context["workspace"]["candidate_website"].startswith("artifacts/website-candidates/")
    assert context["route"]["allowed_paths"] == ["index.html", "styles.css"]
    assert context["asset_requirement"]["required"] is False
    assert context["asset_import"]["state"] == "not-required-text-only"
    assert context["asset_import"]["assets_ready"] is False
    assert "authoring_contract" not in context["asset_import"]
    assert context["mutation_contract"] == {
        "text_write_paths": ["index.html", "styles.css"],
        "binary_read_authority": "none",
        "binary_write_authority": "none",
        "binary_import_authority": "none",
        "canonical_write_authority": "none",
    }
    assert context["route"]["claim_capsule_sha256"] == runner._json_sha256(context["route"]["claim_capsule"])
    assert context["route"]["feedback_capsule_sha256"] == runner._json_sha256(
        context["route"]["feedback_capsule"]
    )
    assert staged_job["brief_binding"]["stakeholder_feedback"]["signal_ids"] == [
        "fixture-first-visit-clarity"
    ]
    assert context["release_eligible"] is False
    assert context["deployment_authority"] == "none"
    assert "canonical website mutation" in context["prohibited_operations"]
    assert "deployment" in context["prohibited_operations"]
    assert "binary asset read" in context["prohibited_operations"]
    assert "binary asset write" in context["prohibited_operations"]
    assert "binary asset import" in context["prohibited_operations"]

    candidate_style = tmp_path / context["workspace"]["candidate_website"] / "styles.css"
    candidate_style.write_text("body { color: #234567; }\n", encoding="utf-8")
    validated_job, validated_path = runner.validate_design_delivery_job(
        "runner-style",
        claim_impacts=[_claim_impact("styles.css")],
        repo_root=tmp_path,
        now=NOW,
    )

    assert validated_job["state"] == "candidate-validated"
    assert validated_job["candidate_validation"]["passed"] is True
    assert validated_path.exists()
    assert (tmp_path / "website" / "styles.css").read_text(encoding="utf-8") == canonical_before
    assert (tmp_path / validated_job["candidate_validation"]["path"]).name == "candidate.v1.json"
    verification = runner.verify_design_delivery_job(validated_job, repo_root=tmp_path, now=NOW)
    assert verification["passed"] is True
    _assert_delivery_schema_valid(validated_job)
    assert all(job["release_eligible"] is False for job in (staged_job, validated_job))
    assert all(job["deployment_authority"] == "none" for job in (staged_job, validated_job))


def test_design_copy_job_is_exact_html_only_and_requires_current_candidate_reaudit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _fake_repo(tmp_path)
    baseline_html = _investor_copy_html(include_static_count=True)
    _write(tmp_path / "website" / COPY_HTML_PATH, baseline_html)
    _write_copy_policy(tmp_path)
    design_cycle = _write_copy_design_cycle(tmp_path)
    audit = _copy_brief_audit(tmp_path)
    _patch_brief(monkeypatch, audit)

    created, _ = runner.create_design_delivery_job(
        goal="Repair one exact investor-copy route.",
        route_id="investor-reading-room",
        reconciliation_receipt=_aligned_copy_reconciliation(
            tmp_path,
            "runner-copy-exact",
        ),
        design_cycle_receipt=design_cycle,
        design_copy_task_id=COPY_TASK_ID,
        run_id="runner-copy-exact",
        repo_root=tmp_path,
        now=NOW,
    )
    work_order = json.loads((tmp_path / created["work_order"]["path"]).read_text(encoding="utf-8"))
    _assert_delivery_schema_valid(created)
    missing_copy_binding = deepcopy(created)
    missing_copy_binding.pop("investor_copy_repair")
    assert _delivery_schema_errors(missing_copy_binding)
    downgraded_copy_job = deepcopy(created)
    downgraded_copy_job["delivery_contract"] = {
        "kind": "route-bounded-design",
        "copy_repair_required": False,
    }
    assert _delivery_schema_errors(downgraded_copy_job)

    assert work_order["routes"] == [COPY_ROUTE]
    assert work_order["allowed_paths"] == [COPY_HTML_PATH]
    assert created["investor_copy_repair"]["task_id"] == COPY_TASK_ID
    assert created["investor_copy_repair"]["required"] is True

    staged, _ = runner.stage_design_delivery_job(
        "runner-copy-exact",
        repo_root=tmp_path,
        now=NOW,
    )
    context = runner.worker_context_for_delivery_job(
        "runner-copy-exact",
        repo_root=tmp_path,
        now=NOW,
    )
    copy_context = context["investor_copy_repair"]
    serialised_context = json.dumps(copy_context)
    _assert_delivery_schema_valid(context)
    context_with_extra_copy_field = deepcopy(context)
    context_with_extra_copy_field["investor_copy_repair"]["selected_source"] = {
        "kind": "forbidden-worker-projection"
    }
    assert _delivery_schema_errors(context_with_extra_copy_field)

    assert context["route"]["allowed_paths"] == [COPY_HTML_PATH]
    assert context["mutation_contract"]["text_write_paths"] == [COPY_HTML_PATH]
    assert copy_context["contract_file_sha256"] == created["investor_copy_repair"]["sha256"]
    assert runner._SHA256.fullmatch(copy_context["contract_json_sha256"])
    assert "selected_source" not in serialised_context
    assert "manifest_path" not in serialised_context
    assert "before_sha256" not in serialised_context

    candidate_html = tmp_path / staged["candidate"]["candidate_website"] / COPY_HTML_PATH
    candidate_html.write_text(
        _investor_copy_html(include_static_count=False),
        encoding="utf-8",
    )
    validated, _ = runner.validate_design_delivery_job(
        "runner-copy-exact",
        claim_impacts=[
            {
                "path": COPY_HTML_PATH,
                "classification": "material-claim-change",
                "rationale": (
                    "Removed a stale operating count while preserving the exact "
                    "permitted claim and representation boundary."
                ),
            }
        ],
        claim_surface_manifest=[],
        repo_root=tmp_path,
        now=NOW,
    )
    _assert_delivery_schema_valid(validated)

    assert validated["state"] == "candidate-validated"
    assert validated["candidate_validation"] == {
        "path": validated["candidate_validation"]["path"],
        "sha256": validated["candidate_validation"]["sha256"],
        "control_passed": True,
        "passed": True,
    }
    assert validated["investor_copy_evaluation"]["passed"] is True
    assert validated["investor_copy_evaluation"]["candidate_audit"]["blocker_count"] == 0
    assert validated["investor_copy_evaluation"]["candidate_audit"]["warning_count"] == 0
    assert (
        runner.verify_design_delivery_job(
            validated,
            repo_root=tmp_path,
            now=NOW,
        )["passed"]
        is True
    )
    assert (tmp_path / "website" / COPY_HTML_PATH).read_text(encoding="utf-8") == baseline_html


def test_design_copy_preflight_rejects_unsatisfied_capsule_without_writing_work_order(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _fake_repo(tmp_path)
    _write(
        tmp_path / "website" / COPY_HTML_PATH,
        _investor_copy_html(include_static_count=True),
    )
    _write_copy_policy(tmp_path)
    design_cycle = _write_copy_design_cycle(tmp_path)
    audit = _copy_brief_audit(tmp_path)
    audit["route_claim_capsules"][0]["claims"][0]["permitted_wording"] = ["A different bounded statement."]
    audit["route_claim_capsules_sha256"] = runner._json_sha256(audit["route_claim_capsules"])
    _patch_brief(monkeypatch, audit)

    with pytest.raises(
        runner.PublicWebsiteDesignRunnerError,
        match="preflight failed closed",
    ):
        runner.create_design_delivery_job(
            goal="Repair one exact investor-copy route.",
            route_id="investor-reading-room",
            reconciliation_receipt=_aligned_copy_reconciliation(
                tmp_path,
                "runner-copy-preflight",
            ),
            design_cycle_receipt=design_cycle,
            design_copy_task_id=COPY_TASK_ID,
            run_id="runner-copy-preflight",
            repo_root=tmp_path,
            now=NOW,
        )

    assert not (tmp_path / runner.DEFAULT_WORK_ORDER_ROOT / "runner-copy-preflight.v4.json").exists()
    assert not (tmp_path / runner.DEFAULT_DELIVERY_ROOT / "runner-copy-preflight").exists()


def test_design_copy_failure_preserves_distinct_control_and_copy_outcomes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _fake_repo(tmp_path)
    _write(
        tmp_path / "website" / COPY_HTML_PATH,
        _investor_copy_html(include_static_count=True),
    )
    _write_copy_policy(tmp_path)
    design_cycle = _write_copy_design_cycle(tmp_path)
    _patch_brief(monkeypatch, _copy_brief_audit(tmp_path))
    runner.create_design_delivery_job(
        goal="Repair one exact investor-copy route.",
        route_id="investor-reading-room",
        reconciliation_receipt=_aligned_copy_reconciliation(
            tmp_path,
            "runner-copy-failed-audit",
        ),
        design_cycle_receipt=design_cycle,
        design_copy_task_id=COPY_TASK_ID,
        run_id="runner-copy-failed-audit",
        repo_root=tmp_path,
        now=NOW,
    )
    staged, _ = runner.stage_design_delivery_job(
        "runner-copy-failed-audit",
        repo_root=tmp_path,
        now=NOW,
    )
    candidate_html = tmp_path / staged["candidate"]["candidate_website"] / COPY_HTML_PATH
    candidate_html.write_text(
        candidate_html.read_text(encoding="utf-8") + "\n<!-- attempted copy repair -->\n",
        encoding="utf-8",
    )

    failed, _ = runner.validate_design_delivery_job(
        "runner-copy-failed-audit",
        claim_impacts=[
            {
                "path": COPY_HTML_PATH,
                "classification": "material-claim-change",
                "rationale": (
                    "The HTML changed but the controlled public wording and "
                    "representation boundary were preserved."
                ),
            }
        ],
        claim_surface_manifest=[],
        repo_root=tmp_path,
        now=NOW,
    )

    assert failed["state"] == "candidate-repair-required"
    assert failed["candidate_validation"]["control_passed"] is True
    assert failed["candidate_validation"]["passed"] is False
    assert failed["investor_copy_evaluation"]["passed"] is False
    assert (
        runner.verify_design_delivery_job(
            failed,
            repo_root=tmp_path,
            now=NOW,
        )["passed"]
        is True
    )
    with pytest.raises(
        runner.PublicWebsiteDesignRunnerError,
        match="validated staged candidate",
    ):
        runner.evaluate_delivery_initial_gate(
            "runner-copy-failed-audit",
            visual_receipt=tmp_path / "unused-visual.json",
            route_name=COPY_ROUTE,
            repo_root=tmp_path,
            now=NOW,
        )


def test_copy_delivery_contract_cannot_be_downgraded_by_dropping_binding(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _fake_repo(tmp_path)
    _write(
        tmp_path / "website" / COPY_HTML_PATH,
        _investor_copy_html(include_static_count=True),
    )
    _write_copy_policy(tmp_path)
    _patch_brief(monkeypatch, _copy_brief_audit(tmp_path))
    created, _ = runner.create_design_delivery_job(
        goal="Repair one exact investor-copy route.",
        route_id="investor-reading-room",
        reconciliation_receipt=_aligned_copy_reconciliation(
            tmp_path,
            "runner-copy-downgrade",
        ),
        design_cycle_receipt=_write_copy_design_cycle(tmp_path),
        design_copy_task_id=COPY_TASK_ID,
        run_id="runner-copy-downgrade",
        repo_root=tmp_path,
        now=NOW,
    )
    downgraded = deepcopy(created)
    downgraded.pop("investor_copy_repair")

    verification = runner.verify_design_delivery_job(
        downgraded,
        repo_root=tmp_path,
        now=NOW,
    )
    checks = {item["id"]: item["passed"] for item in verification["checks"]}

    assert verification["passed"] is False
    assert checks["delivery-contract-kind"] is False
    assert checks["investor-copy-contract-binding"] is False


def test_binary_job_withholds_worker_until_candidate_assets_ready_and_exposes_text_only_paths(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _fake_repo(tmp_path)
    _patch_fake_editorial_import(monkeypatch)
    staged_job, _ = _create_and_stage_binary_run(
        tmp_path,
        monkeypatch,
        run_id="runner-binary-assets",
    )

    assert staged_job["state"] == "candidate-staged"
    assert staged_job["asset_requirement"]["required"] is True
    assert staged_job["asset_requirement"]["declared_binary_paths"] == ["assets/hero.webp"]
    assert "asset_import" not in staged_job
    with pytest.raises(
        runner.PublicWebsiteDesignRunnerError,
        match="candidate-assets-ready",
    ):
        runner.worker_context_for_delivery_job(
            "runner-binary-assets",
            repo_root=tmp_path,
            now=NOW,
        )
    with pytest.raises(
        runner.PublicWebsiteDesignRunnerError,
        match="candidate-assets-ready",
    ):
        runner.validate_design_delivery_job(
            "runner-binary-assets",
            claim_impacts=[],
            repo_root=tmp_path,
            now=NOW,
        )

    ready_job, ready_path = runner.prepare_design_delivery_assets(
        "runner-binary-assets",
        repo_root=tmp_path,
        now=NOW,
    )
    context = runner.worker_context_for_delivery_job(
        "runner-binary-assets",
        repo_root=tmp_path,
        now=NOW,
    )

    assert ready_job["state"] == "candidate-assets-ready"
    assert ready_job["asset_import"]["state"] == "candidate-assets-ready"
    assert ready_job["asset_import"]["assets_ready"] is True
    assert ready_job["asset_import"]["release_eligible"] is False
    assert ready_job["asset_import"]["package_authority"] == "none"
    assert ready_job["asset_import"]["deployment_authority"] == "none"
    assert ready_path.name.endswith("-candidate-assets-ready.json")
    assert context["route"]["allowed_paths"] == ["index.html", "styles.css"]
    assert "assets/hero.webp" not in context["route"]["allowed_paths"]
    assert context["mutation_contract"]["text_write_paths"] == [
        "index.html",
        "styles.css",
    ]
    assert context["mutation_contract"]["binary_read_authority"] == "none"
    assert context["mutation_contract"]["binary_write_authority"] == "none"
    assert context["mutation_contract"]["binary_import_authority"] == "none"
    assert context["asset_import"]["assets_ready"] is True
    authoring = context["asset_import"]["authoring_contract"]
    assert authoring["schema"] == runner.EDITORIAL_AUTHORING_CONTRACT_SCHEMA
    assert authoring["state"] == "trusted-route-bound"
    assert authoring["contract_sha256"] == runner._json_sha256(
        {key: value for key, value in authoring.items() if key != "contract_sha256"}
    )
    assert authoring["surfaces"] == [
        {
            "route": "/",
            "destination": "index.html",
            "surface_id": "fixture-home-hero",
            "public_post_url": "https://example.substack.com/p/fixture-hero",
            "variants": [
                {
                    "role": "large",
                    "public_path": "assets/hero.webp",
                    "media_type": "image/webp",
                    "width": 1600,
                    "height": 900,
                }
            ],
            "alt": "Aureon research evidence illustration",
            "caption": "Research evidence translated into a bounded public explanation.",
            "credit": "Artwork supplied for the linked Aureon research article.",
        }
    ]
    assert authoring["surfaces_sha256"] == runner._json_sha256(authoring["surfaces"])
    assert authoring["trusted_evidence"]["import_receipt_payload_sha256"] == "A" * 64
    assert authoring["trusted_evidence"]["imports_sha256"] == "C" * 64
    assert (
        runner.verify_design_delivery_job(
            ready_job,
            repo_root=tmp_path,
            now=NOW,
        )["passed"]
        is True
    )

    receipt_path = tmp_path / ready_job["asset_import"]["receipt"]["path"]
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["receipt_payload_sha256"] = "D" * 64
    _write(receipt_path, json.dumps(receipt, indent=2) + "\n")
    with pytest.raises(
        runner.PublicWebsiteDesignRunnerError,
        match="worker context is withheld",
    ):
        runner.worker_context_for_delivery_job(
            "runner-binary-assets",
            repo_root=tmp_path,
            now=NOW,
        )


def test_runner_blocks_brief_drift_before_staging_and_keeps_canonical_untouched(
    tmp_path: Path, monkeypatch
) -> None:
    _fake_repo(tmp_path)
    payload = _brief_audit()
    _patch_brief(monkeypatch, payload)
    canonical_before = (tmp_path / "website" / "index.html").read_text(encoding="utf-8")
    runner.create_design_delivery_job(
        goal="Refine one bounded investor-facing route.",
        route_id="home",
        reconciliation_receipt=_aligned_reconciliation(tmp_path, "brief-drift"),
        run_id="brief-drift",
        repo_root=tmp_path,
        now=NOW,
    )
    payload["brief"]["sha256"] = "D" * 64

    with pytest.raises(runner.PublicWebsiteDesignRunnerError, match="no longer verifies"):
        runner.stage_design_delivery_job("brief-drift", repo_root=tmp_path, now=NOW)

    assert (tmp_path / "website" / "index.html").read_text(encoding="utf-8") == canonical_before
    assert not (tmp_path / "artifacts" / "website-candidates" / "brief-drift").exists()


def test_runner_blocks_research_refresh_drift_before_staging(tmp_path: Path, monkeypatch) -> None:
    _fake_repo(tmp_path)
    payload = _brief_audit()
    _patch_brief(monkeypatch, payload)
    runner.create_design_delivery_job(
        goal="Refine one bounded investor-facing route.",
        route_id="home",
        reconciliation_receipt=_aligned_reconciliation(tmp_path, "refresh-drift"),
        run_id="refresh-drift",
        repo_root=tmp_path,
        now=NOW,
    )
    payload["research_refresh"]["declaration_sha256"] = "E" * 64

    with pytest.raises(runner.PublicWebsiteDesignRunnerError, match="no longer verifies"):
        runner.stage_design_delivery_job("refresh-drift", repo_root=tmp_path, now=NOW)

    assert not (tmp_path / "artifacts" / "website-candidates" / "refresh-drift").exists()


def test_runner_blocks_noncurrent_research_refresh_before_staging(tmp_path: Path, monkeypatch) -> None:
    _fake_repo(tmp_path)
    payload = _brief_audit()
    _patch_brief(monkeypatch, payload)
    runner.create_design_delivery_job(
        goal="Refine one bounded investor-facing route.",
        route_id="home",
        reconciliation_receipt=_aligned_reconciliation(tmp_path, "refresh-stale"),
        run_id="refresh-stale",
        repo_root=tmp_path,
        now=NOW,
    )
    payload["research_refresh"]["state"] = "refresh-due"

    with pytest.raises(runner.PublicWebsiteDesignRunnerError, match="no longer verifies"):
        runner.stage_design_delivery_job("refresh-stale", repo_root=tmp_path, now=NOW)

    assert not (tmp_path / "artifacts" / "website-candidates" / "refresh-stale").exists()


def test_runner_blocks_stakeholder_feedback_drift_before_staging(tmp_path: Path, monkeypatch) -> None:
    _fake_repo(tmp_path)
    payload = _brief_audit()
    _patch_brief(monkeypatch, payload)
    runner.create_design_delivery_job(
        goal="Refine one bounded investor-facing route.",
        route_id="home",
        reconciliation_receipt=_aligned_reconciliation(tmp_path, "stakeholder-feedback-drift"),
        run_id="stakeholder-feedback-drift",
        repo_root=tmp_path,
        now=NOW,
    )
    payload["stakeholder_feedback"]["sha256"] = "1" * 64

    with pytest.raises(runner.PublicWebsiteDesignRunnerError, match="no longer verifies"):
        runner.stage_design_delivery_job("stakeholder-feedback-drift", repo_root=tmp_path, now=NOW)

    assert not (tmp_path / "artifacts" / "website-candidates" / "stakeholder-feedback-drift").exists()


def test_failed_candidate_validation_is_preserved_and_requires_a_successor_run(
    tmp_path: Path, monkeypatch
) -> None:
    _fake_repo(tmp_path)
    staged_job, _ = _create_and_stage(tmp_path, monkeypatch, run_id="scope-failure")
    candidate_root = tmp_path / staged_job["candidate"]["candidate_root"]
    _write(candidate_root / "website" / "unexpected.js", "console.log('out of scope');\n")

    failed_job, _ = runner.validate_design_delivery_job(
        "scope-failure",
        claim_impacts=[_claim_impact("unexpected.js")],
        repo_root=tmp_path,
        now=NOW,
    )

    assert failed_job["state"] == "candidate-repair-required"
    assert failed_job["candidate_validation"]["passed"] is False
    assert failed_job["release_eligible"] is False
    assert failed_job["deployment_authority"] == "none"
    with pytest.raises(runner.PublicWebsiteDesignRunnerError, match="untouched staged candidate"):
        runner.validate_design_delivery_job(
            "scope-failure",
            claim_impacts=[_claim_impact("unexpected.js")],
            repo_root=tmp_path,
            now=NOW,
        )


def test_runner_blocks_an_unsupported_customer_adoption_claim_even_when_staged_claim_hash_is_refreshed(
    tmp_path: Path, monkeypatch
) -> None:
    """Regression: source-hash refresh must not certify unsupported public copy."""

    _fake_repo(tmp_path)
    staged_job, _ = _create_and_stage(tmp_path, monkeypatch, run_id="claim-surface-bypass")
    candidate_root = tmp_path / staged_job["candidate"]["candidate_root"]
    candidate_page = candidate_root / "website" / "index.html"
    unsafe = "Aureon has customer adoption in regulated sectors."
    candidate_page.write_text(
        "<!doctype html><title>Aureon</title><p>Aureon is an evidence-led test company. "
        "This fixture is not evidence of customer adoption or independent validation. "
        f"{unsafe}</p>\n",
        encoding="utf-8",
    )
    staged_register = candidate_root / "claim-evidence" / "public_claim_evidence_register.v1.json"
    register = json.loads(staged_register.read_text(encoding="utf-8"))
    register["generated_at"] = "2026-07-28T20:05:00Z"
    register["claims"][0]["source"]["sha256"] = _sha256(candidate_page)
    staged_register.write_text(json.dumps(register, indent=2) + "\n", encoding="utf-8")

    context = runner._claim_surface_context(staged_job)  # noqa: SLF001 - sealed runner binding under test
    preview = evaluate_candidate_claim_surface(
        baseline_site=tmp_path / "website",
        candidate_site=candidate_root / "website",
        changed_paths=["index.html"],
        context=context,
        manifest=[],
    )
    manifest = [
        {
            "path": row["path"],
            "kind": "non-claim",
            "claim_id": "",
            "text_sha256": row["text_sha256"],
            "surface_sha256": row["surface_sha256"],
            "rationale": "interface-label",
        }
        for row in preview["new_surfaces"]
    ]

    failed_job, _ = runner.validate_design_delivery_job(
        "claim-surface-bypass",
        claim_impacts=[
            {
                "path": "index.html",
                "classification": "material-claim-change",
                "rationale": "The public page and its staged claim source hash were refreshed for review.",
            }
        ],
        claim_surface_manifest=manifest,
        repo_root=tmp_path,
        now=NOW,
    )

    assert failed_job["state"] == "candidate-repair-required"
    receipt = json.loads((tmp_path / failed_job["candidate_validation"]["path"]).read_text(encoding="utf-8"))
    check = next(item for item in receipt["checks"] if item["id"] == "claim-surface-capsule")
    assert check["passed"] is False
    assert (tmp_path / "website" / "index.html").read_text(encoding="utf-8") != candidate_page.read_text(
        encoding="utf-8"
    )


def test_runner_has_no_owner_promotion_or_deployment_entrypoint() -> None:
    forbidden = {"deploy", "build_release", "gate_deployment", "promote_candidate", "apply_candidate"}

    assert not (forbidden & set(dir(runner)))
    assert runner.AUTHORITY["canonical_website_mutation"].startswith("never")
    assert runner.AUTHORITY["package_authority"] == "none"
    assert runner.AUTHORITY["deployment_authority"] == "none"


def test_runner_rejects_tampered_candidate_validation_and_receipt_sequence(
    tmp_path: Path, monkeypatch
) -> None:
    _fake_repo(tmp_path)
    _create_and_stage(tmp_path, monkeypatch, run_id="receipt-integrity")
    validated_job, validated_path = runner.validate_design_delivery_job(
        "receipt-integrity",
        claim_impacts=[_claim_impact("styles.css")],
        repo_root=tmp_path,
        now=NOW,
    )
    candidate_receipt = tmp_path / validated_job["candidate_validation"]["path"]
    payload = json.loads(candidate_receipt.read_text(encoding="utf-8"))
    payload["candidate"]["tree_sha256"] = "0" * 64
    candidate_receipt.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    verification = runner.verify_design_delivery_job(validated_job, repo_root=tmp_path, now=NOW)
    checks = {item["id"]: item["passed"] for item in verification["checks"]}
    assert checks["candidate-workspace-and-validation-binding"] is False

    validated_path.rename(validated_path.with_name("09-candidate-validated.json"))
    with pytest.raises(runner.PublicWebsiteDesignRunnerError, match="contiguous"):
        runner.load_latest_delivery_job("receipt-integrity", repo_root=tmp_path)


def test_runner_rejects_artifact_root_that_resolves_outside_the_repository(
    tmp_path: Path, monkeypatch
) -> None:
    _fake_repo(tmp_path)
    _patch_brief(monkeypatch, _brief_audit())
    reconciliation = _aligned_reconciliation(tmp_path, "outside-root")
    monkeypatch.setattr(runner, "DEFAULT_DELIVERY_ROOT", Path("..") / "outside-delivery")

    with pytest.raises(runner.PublicWebsiteDesignRunnerError, match="inside the Aureon repository"):
        runner.create_design_delivery_job(
            goal="Refine one bounded investor-facing route.",
            route_id="home",
            reconciliation_receipt=reconciliation,
            run_id="outside-root",
            repo_root=tmp_path,
            now=NOW,
        )


def test_runner_requires_gate_and_visual_review_receipts_for_post_gate_states(
    tmp_path: Path, monkeypatch
) -> None:
    _fake_repo(tmp_path)
    _create_and_stage(tmp_path, monkeypatch, run_id="post-gate-binding")
    validated_job, _ = runner.validate_design_delivery_job(
        "post-gate-binding",
        claim_impacts=[_claim_impact("styles.css")],
        repo_root=tmp_path,
        now=NOW,
    )
    post_gate_job = deepcopy(validated_job)
    post_gate_job["state"] = "awaiting-browser-evidence"

    verification = runner.verify_design_delivery_job(post_gate_job, repo_root=tmp_path, now=NOW)
    checks = {item["id"]: item["passed"] for item in verification["checks"]}
    assert checks["initial-gate-binding"] is False


def _validated_qa_run(
    root: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    run_id: str,
) -> dict:
    staged, _ = _create_and_stage(root, monkeypatch, run_id=run_id)
    candidate_style = root / staged["candidate"]["candidate_website"] / "styles.css"
    candidate_style.write_text("body { color: #234567; }\n", encoding="utf-8")
    validated, _ = runner.validate_design_delivery_job(
        run_id,
        claim_impacts=[_claim_impact("styles.css")],
        repo_root=root,
        now=NOW,
    )
    assert validated["state"] == "candidate-validated"
    return validated


def _write_qa_inputs(root: Path, run_id: str) -> tuple[Path, str, Path, str]:
    motion = root / "artifacts" / "website-operator" / "qa-inputs" / f"{run_id}-motion.json"
    policy = motion.with_name(f"{run_id}-tests.json")
    _write(motion, '{"fixture":"externally-pinned-motion-config"}\n')
    _write(
        policy,
        json.dumps(
            {
                "schema": "aureon.design-candidate-test-policy.v1",
                "content_core_sha256": "C" * 64,
                "required_command_ids": ["fixture-static-qa"],
            }
        )
        + "\n",
    )
    return motion, _sha256(motion), policy, _sha256(policy)


def _patch_qa_engines(
    root: Path,
    monkeypatch: pytest.MonkeyPatch,
    job: dict,
    *,
    motion_passed: bool,
    evidence_passed: bool,
    cross_run_test_evidence: bool = False,
) -> list[str]:
    calls: list[str] = []
    candidate = job["candidate"]
    candidate_website = root / candidate["candidate_website"]
    candidate_snapshot = runner._candidate_qa_tree_binding(
        root,
        candidate_website,
        label="Fixture candidate",
    )
    validation_receipt = json.loads((root / job["candidate_validation"]["path"]).read_text(encoding="utf-8"))
    validation_tree_sha256 = validation_receipt["candidate"]["tree_sha256"]
    canonical_rows = [
        {
            "path": path.relative_to(root / "website").as_posix(),
            "sha256": _sha256(path),
            "bytes": path.stat().st_size,
        }
        for path in sorted(
            (path for path in (root / "website").rglob("*") if path.is_file()),
            key=lambda path: path.relative_to(root / "website").as_posix(),
        )
    ]
    canonical_test_tree_sha256 = runner._json_sha256(canonical_rows)
    trusted_toolchain = {
        name: {
            "path": f"aureon/fixture/{name}.py",
            "sha256": chr(65 + index) * 64,
        }
        for index, name in enumerate(
            (
                "runner",
                "test_evidence",
                "motion_policy_compiler",
                "test_policy_compiler",
                "motion_budget",
                "secure_immutable_artifact",
            )
        )
    }

    def fake_trusted_toolchain(repo_root: Path) -> dict:
        assert repo_root == root
        return deepcopy(trusted_toolchain)

    def fake_compiler_verify(
        policy_path: Path,
        *,
        expected_policy_sha256: str,
        candidate_receipt_path: Path,
        repo_root: Path | None = None,
    ) -> dict:
        assert repo_root == root
        expected_policy = (
            root / "artifacts" / "website-operator" / "qa-inputs" / f"{job['run_id']}-tests.json"
        )
        if policy_path != expected_policy:
            raise runner.PublicWebsiteDesignRunnerError(
                "Fixture rejected policy shopping outside the fixed compiler path."
            )
        assert expected_policy_sha256 == _sha256(policy_path)
        calls.append("policy-compiler-replay")
        return {
            "schema": runner.TEST_POLICY_COMPILER_VERIFICATION_SCHEMA,
            "state": "pass",
            "passed": True,
            "verification_scope": runner.TEST_POLICY_COMPILER_VERIFICATION_SCOPE,
            "compiler_replayed": True,
            "origin_attested": False,
            "candidate_receipt_path": candidate_receipt_path.relative_to(root).as_posix(),
            "candidate_tree_sha256": validation_tree_sha256,
            "source_policy_file_sha256": runner.COMPILER_SOURCE_POLICY_FILE_SHA256,
            "policy_path": policy_path.relative_to(root).as_posix(),
            "policy_id": f"candidate-suite-v2-{'c' * 64}",
            "policy_content_core_sha256": "C" * 64,
            "policy_file_sha256": expected_policy_sha256,
            "policy_json_sha256": "F" * 64,
            "required_command_ids": ["fixture-static-qa"],
            "deferred_source_ids": list(runner.TEST_POLICY_COMPILER_DEFERRED_SOURCE_IDS),
            "authority": dict(runner.TEST_POLICY_COMPILER_AUTHORITY),
        }

    def fake_motion_compiler_verify(
        config_path: Path,
        *,
        expected_config_sha256: str,
        candidate_receipt_path: Path,
        repo_root: Path | None = None,
    ) -> dict:
        assert repo_root == root
        expected_config = (
            root / "artifacts" / "website-operator" / "qa-inputs" / f"{job['run_id']}-motion.json"
        )
        if config_path != expected_config:
            raise runner.PublicWebsiteDesignRunnerError(
                "Fixture rejected threshold shopping outside the fixed compiler path."
            )
        assert expected_config_sha256 == _sha256(config_path)
        calls.append("motion-compiler-replay")
        return {
            "schema": runner.MOTION_POLICY_COMPILER_VERIFICATION_SCHEMA,
            "state": "pass",
            "passed": True,
            "verification_scope": runner.MOTION_POLICY_COMPILER_VERIFICATION_SCOPE,
            "compiler_replayed": True,
            "origin_attested": False,
            "candidate_receipt_path": candidate_receipt_path.relative_to(root).as_posix(),
            "candidate_tree_sha256": validation_tree_sha256,
            "candidate_tree_algorithm": candidate_snapshot["candidate_tree_algorithm"],
            "motion_tree_sha256": candidate_snapshot["motion_tree_sha256"],
            "motion_tree_algorithm": candidate_snapshot["motion_tree_algorithm"],
            "captured_manifest_sha256": candidate_snapshot["captured_manifest_sha256"],
            "doctrine_sha256": runner.MOTION_POLICY_COMPILER_DOCTRINE_SHA256,
            "source_policy_sha256": runner.COMPILER_SOURCE_POLICY_FILE_SHA256,
            "config_path": config_path.relative_to(root).as_posix(),
            "config_id": f"candidate-motion-v2-{expected_config_sha256.lower()}",
            "config_file_sha256": expected_config_sha256,
            "config_json_sha256": "8" * 64,
            "thresholds_sha256": "9" * 64,
            "authority": dict(runner.MOTION_POLICY_COMPILER_AUTHORITY),
        }

    def fake_motion_audit(
        config_path: Path,
        *,
        repo_root: Path | None = None,
        output_path: Path | None = None,
    ) -> dict:
        assert repo_root == root
        assert output_path is not None
        calls.append("motion-audit")
        receipt = {
            "schema": "aureon.design-motion-performance-budget.v1",
            "config": {
                "path": config_path.relative_to(root).as_posix(),
                "sha256": _sha256(config_path),
                "schema": "aureon.design-motion-performance-budget-config.v1",
            },
            "source": {
                "kind": "staged-static-tree",
                "root": candidate["candidate_website"],
                "observed_tree_sha256": candidate_snapshot["motion_tree_sha256"],
            },
            "decision": {
                "status": "pass" if motion_passed else "blocked",
                "eligible_for_next_local_gate": motion_passed,
            },
            "receipt_sha256": "A" * 64,
        }
        _write(output_path, json.dumps(receipt, indent=2) + "\n")
        return receipt

    def fake_motion_replay(
        receipt_path: Path,
        *,
        repo_root: Path | None = None,
    ) -> dict:
        assert repo_root == root
        calls.append("motion-replay")
        return json.loads(receipt_path.read_text(encoding="utf-8"))

    def fake_test_execute(
        policy_path: Path,
        *,
        expected_policy_sha256: str,
        command_ids: list[str],
        repo_root: Path | None = None,
        receipt_id: str | None = None,
        now: datetime | None = None,
    ) -> dict:
        assert repo_root == root
        assert expected_policy_sha256 == _sha256(policy_path)
        assert command_ids == ["fixture-static-qa"]
        assert receipt_id
        assert now == NOW
        calls.append("test-execute")
        return {
            "schema": "aureon.design-candidate-test-evidence.v2",
            "passed": evidence_passed,
            "receipt_payload_sha256": "B" * 64,
        }

    def fake_test_write(
        receipt: dict,
        output_path: Path,
        *,
        policy_path: Path,
        expected_policy_sha256: str,
        repo_root: Path | None = None,
    ) -> Path:
        assert repo_root == root
        assert expected_policy_sha256 == _sha256(policy_path)
        calls.append("test-write-same-process")
        _write(output_path, json.dumps(receipt, indent=2) + "\n")
        return output_path

    def fake_test_verify(
        receipt_path: Path,
        *,
        expected_receipt_file_sha256: str,
        policy_path: Path,
        expected_policy_sha256: str,
        repo_root: Path | None = None,
    ) -> dict:
        assert repo_root == root
        if expected_receipt_file_sha256 != _sha256(receipt_path):
            raise runner.DesignCandidateTestEvidenceError("Fixture receipt hash no longer matches.")
        assert expected_policy_sha256 == _sha256(policy_path)
        calls.append("test-replay")
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        return {
            "schema": "aureon.design-candidate-test-evidence-verification.v2",
            "origin_attested": False,
            "evidence_passed": receipt["passed"],
            "policy_file_sha256": expected_policy_sha256,
            "candidate_tree_sha256": ("F" * 64 if cross_run_test_evidence else validation_tree_sha256),
            "canonical_website_tree_sha256": canonical_test_tree_sha256,
            "receipt_payload_sha256": receipt["receipt_payload_sha256"],
        }

    monkeypatch.setattr(
        runner,
        "_trusted_qa_toolchain_binding",
        fake_trusted_toolchain,
    )
    monkeypatch.setattr(
        runner,
        "_verify_compiled_candidate_test_policy_file_sealed",
        fake_compiler_verify,
    )
    monkeypatch.setattr(
        runner,
        "_verify_compiled_candidate_motion_config_file_sealed",
        fake_motion_compiler_verify,
    )
    monkeypatch.setattr(runner, "audit_motion_performance_budget", fake_motion_audit)
    monkeypatch.setattr(
        runner,
        "validate_motion_performance_receipt",
        fake_motion_replay,
    )
    monkeypatch.setattr(
        runner,
        "execute_candidate_test_evidence",
        fake_test_execute,
    )
    monkeypatch.setattr(
        runner,
        "write_candidate_test_evidence_receipt",
        fake_test_write,
    )
    monkeypatch.setattr(
        runner,
        "verify_candidate_test_evidence_receipt",
        fake_test_verify,
    )
    return calls


def test_compiler_verification_schema_authority_paths_and_hashes_fail_before_qa(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _fake_repo(tmp_path)
    run_id = "qa-sealed-verifier-rejection"
    validated = _validated_qa_run(tmp_path, monkeypatch, run_id=run_id)
    motion, motion_hash, policy, policy_hash = _write_qa_inputs(tmp_path, run_id)
    calls = _patch_qa_engines(
        tmp_path,
        monkeypatch,
        validated,
        motion_passed=True,
        evidence_passed=True,
    )
    good_motion = runner._verify_compiled_candidate_motion_config_file_sealed  # noqa: SLF001
    good_policy = runner._verify_compiled_candidate_test_policy_file_sealed  # noqa: SLF001
    motion_authority = dict(runner.MOTION_POLICY_COMPILER_AUTHORITY)
    motion_authority["release_authority"] = "worker"
    policy_authority = dict(runner.TEST_POLICY_COMPILER_AUTHORITY)
    policy_authority["release_authority"] = "worker"
    cases: list[tuple[str, dict[str, Any]]] = [
        ("motion", {"schema": "wrong.schema"}),
        ("motion", {"authority": motion_authority}),
        ("motion", {"config_path": "artifacts/website-operator/qa-inputs/substitute.json"}),
        ("motion", {"config_file_sha256": "F" * 64}),
        ("motion", {"config_json_sha256": "lowercase-is-not-a-sha256"}),
        ("test", {"schema": "wrong.schema"}),
        ("test", {"authority": policy_authority}),
        ("test", {"policy_path": "artifacts/website-operator/qa-inputs/substitute.json"}),
        ("test", {"policy_file_sha256": "F" * 64}),
        ("test", {"policy_json_sha256": "lowercase-is-not-a-sha256"}),
    ]

    def verifier_with_update(
        verifier: Any,
        *,
        apply_update: bool,
        changes: dict[str, Any],
    ) -> Any:
        def invoke(*args: Any, **kwargs: Any) -> dict[str, Any]:
            result = deepcopy(verifier(*args, **kwargs))
            if apply_update:
                result.update(changes)
            return result

        return invoke

    for compiler_kind, update in cases:
        calls.clear()
        monkeypatch.setattr(
            runner,
            "_verify_compiled_candidate_motion_config_file_sealed",
            verifier_with_update(
                good_motion,
                apply_update=compiler_kind == "motion",
                changes=update,
            ),
        )
        monkeypatch.setattr(
            runner,
            "_verify_compiled_candidate_test_policy_file_sealed",
            verifier_with_update(
                good_policy,
                apply_update=compiler_kind == "test",
                changes=update,
            ),
        )

        with pytest.raises(
            runner.PublicWebsiteDesignRunnerError,
            match="does not equal the complete fixed compiler result",
        ):
            runner.evaluate_delivery_candidate_qa(
                run_id,
                motion_config=motion,
                expected_motion_config_sha256=motion_hash,
                test_policy=policy,
                expected_test_policy_sha256=policy_hash,
                repo_root=tmp_path,
                now=NOW,
            )

        assert "motion-audit" not in calls
        assert "test-execute" not in calls
        assert not (
            tmp_path / validated["candidate"]["candidate_root"] / "candidate-qa" / "attempt.v2.json"
        ).exists()


def test_v2_candidate_qa_runs_motion_then_complete_tests_and_seals_both_receipts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _fake_repo(tmp_path)
    validated = _validated_qa_run(
        tmp_path,
        monkeypatch,
        run_id="qa-pass",
    )
    canonical_before = runner._static_tree_binding(
        tmp_path,
        tmp_path / "website",
        expected_kind="canonical-static-tree",
        label="Canonical before QA",
    )
    motion, motion_hash, policy, policy_hash = _write_qa_inputs(
        tmp_path,
        "qa-pass",
    )
    calls = _patch_qa_engines(
        tmp_path,
        monkeypatch,
        validated,
        motion_passed=True,
        evidence_passed=True,
    )

    qa_job, qa_path = runner.evaluate_delivery_candidate_qa(
        "qa-pass",
        motion_config=motion,
        expected_motion_config_sha256=motion_hash,
        test_policy=policy,
        expected_test_policy_sha256=policy_hash,
        repo_root=tmp_path,
        now=NOW,
    )

    assert qa_job["state"] == "candidate-qa-verified"
    assert calls[:6] == [
        "motion-compiler-replay",
        "policy-compiler-replay",
        "motion-audit",
        "motion-replay",
        "test-execute",
        "test-write-same-process",
    ]
    assert "test-replay" in calls
    assert qa_job["candidate_qa"]["tests"]["evidence_passed"] is True
    assert qa_job["candidate_qa"]["tests"]["trusted_same_process_execution_write"] is True
    assert qa_job["candidate_qa"]["tests"]["structural_verification_origin_attested"] is False
    assert qa_job["candidate_qa"]["motion"]["eligible_for_next_local_gate"] is True
    assert (
        qa_job["candidate_qa"]["candidate"]["captured_manifest_sha256"]
        == (qa_job["candidate_qa"]["motion_config_compiler"]["captured_manifest_sha256"])
    )
    assert (
        qa_job["candidate_qa"]["candidate"]["validation_tree_sha256"]
        == (qa_job["candidate_qa"]["motion_config_compiler"]["candidate_tree_sha256"])
    )
    assert (
        qa_job["candidate_qa"]["candidate"]["motion_tree_sha256"]
        == (qa_job["candidate_qa"]["motion_config_compiler"]["motion_tree_sha256"])
    )
    assert qa_job["candidate_qa"]["tests"]["receipt"]["path"].endswith("candidate-test-evidence.v2.json")
    assert qa_path.is_file()
    claim_path = tmp_path / qa_job["candidate_qa"]["attempt"]["path"]
    claim_payload = json.loads(claim_path.read_text(encoding="utf-8"))
    _assert_delivery_schema_valid(claim_payload)
    for compiler_binding in ("motion_config_compiler", "test_policy_compiler"):
        legacy_imported_ingress = deepcopy(claim_payload)
        legacy_imported_ingress[compiler_binding]["authority"]["executable_source_ingress"] = (
            "trusted imported in-process compiler API"
        )
        assert _delivery_schema_errors(legacy_imported_ingress)
    assert (
        runner.verify_design_delivery_job(
            qa_job,
            repo_root=tmp_path,
            now=NOW,
        )["passed"]
        is True
    )
    _assert_delivery_schema_valid(qa_job)
    assert (
        runner._static_tree_binding(
            tmp_path,
            tmp_path / "website",
            expected_kind="canonical-static-tree",
            label="Canonical after QA",
        )
        == canonical_before
    )


def test_initial_browser_gate_rejects_direct_candidate_validated_bypass(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _fake_repo(tmp_path)
    _validated_qa_run(
        tmp_path,
        monkeypatch,
        run_id="qa-direct-gate-bypass",
    )

    with pytest.raises(
        runner.PublicWebsiteDesignRunnerError,
        match="candidate-qa-verified",
    ):
        runner.evaluate_delivery_initial_gate(
            "qa-direct-gate-bypass",
            visual_receipt=tmp_path / "worker-says-passed.json",
            route_name="/",
            repo_root=tmp_path,
            now=NOW,
        )


def test_candidate_qa_rejects_policy_shopping_before_claim_or_execution(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _fake_repo(tmp_path)
    validated = _validated_qa_run(
        tmp_path,
        monkeypatch,
        run_id="qa-policy-shopping",
    )
    motion, motion_hash, policy, _ = _write_qa_inputs(
        tmp_path,
        "qa-policy-shopping",
    )
    calls = _patch_qa_engines(
        tmp_path,
        monkeypatch,
        validated,
        motion_passed=True,
        evidence_passed=True,
    )
    alternate = policy.with_name("worker-selected-tests.json")
    _write(alternate, policy.read_text(encoding="utf-8"))

    with pytest.raises(
        runner.PublicWebsiteDesignRunnerError,
        match="non-fixed|policy shopping",
    ):
        runner.evaluate_delivery_candidate_qa(
            "qa-policy-shopping",
            motion_config=motion,
            expected_motion_config_sha256=motion_hash,
            test_policy=alternate,
            expected_test_policy_sha256=_sha256(alternate),
            repo_root=tmp_path,
            now=NOW,
        )

    candidate_root = tmp_path / validated["candidate"]["candidate_root"]
    assert not (candidate_root / "candidate-qa" / "attempt.v2.json").exists()
    assert "motion-audit" not in calls
    assert "test-execute" not in calls


def test_candidate_qa_rejects_threshold_shopping_before_claim_or_execution(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _fake_repo(tmp_path)
    validated = _validated_qa_run(
        tmp_path,
        monkeypatch,
        run_id="qa-threshold-shopping",
    )
    motion, _, policy, policy_hash = _write_qa_inputs(
        tmp_path,
        "qa-threshold-shopping",
    )
    calls = _patch_qa_engines(
        tmp_path,
        monkeypatch,
        validated,
        motion_passed=True,
        evidence_passed=True,
    )
    alternate = motion.with_name("caller-relaxed-motion-config.json")
    _write(alternate, motion.read_text(encoding="utf-8"))

    with pytest.raises(
        runner.PublicWebsiteDesignRunnerError,
        match="non-fixed|threshold shopping",
    ):
        runner.evaluate_delivery_candidate_qa(
            "qa-threshold-shopping",
            motion_config=alternate,
            expected_motion_config_sha256=_sha256(alternate),
            test_policy=policy,
            expected_test_policy_sha256=policy_hash,
            repo_root=tmp_path,
            now=NOW,
        )

    candidate_root = tmp_path / validated["candidate"]["candidate_root"]
    assert not (candidate_root / "candidate-qa" / "attempt.v2.json").exists()
    assert "motion-audit" not in calls
    assert "test-execute" not in calls


def test_blocked_motion_consumes_qa_without_running_tests_or_allowing_policy_shopping(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _fake_repo(tmp_path)
    validated = _validated_qa_run(
        tmp_path,
        monkeypatch,
        run_id="qa-motion-blocked",
    )
    motion, motion_hash, policy, policy_hash = _write_qa_inputs(
        tmp_path,
        "qa-motion-blocked",
    )
    calls = _patch_qa_engines(
        tmp_path,
        monkeypatch,
        validated,
        motion_passed=False,
        evidence_passed=True,
    )

    qa_job, _ = runner.evaluate_delivery_candidate_qa(
        "qa-motion-blocked",
        motion_config=motion,
        expected_motion_config_sha256=motion_hash,
        test_policy=policy,
        expected_test_policy_sha256=policy_hash,
        repo_root=tmp_path,
        now=NOW,
    )

    assert qa_job["state"] == "candidate-qa-repair-required"
    assert "test-execute" not in calls
    assert qa_job["candidate_qa"]["tests"]["state"] == "not-run-motion-blocked"
    alternate = motion.with_name("alternate-motion.json")
    _write(alternate, '{"fixture":"relaxed-threshold-shopping"}\n')
    with pytest.raises(
        runner.PublicWebsiteDesignRunnerError,
        match="one-attempt transition",
    ):
        runner.evaluate_delivery_candidate_qa(
            "qa-motion-blocked",
            motion_config=alternate,
            expected_motion_config_sha256=_sha256(alternate),
            test_policy=policy,
            expected_test_policy_sha256=policy_hash,
            repo_root=tmp_path,
            now=NOW,
        )


def test_failed_trusted_test_evidence_consumes_qa_and_cannot_be_retried(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _fake_repo(tmp_path)
    validated = _validated_qa_run(
        tmp_path,
        monkeypatch,
        run_id="qa-test-failed",
    )
    motion, motion_hash, policy, policy_hash = _write_qa_inputs(
        tmp_path,
        "qa-test-failed",
    )
    _patch_qa_engines(
        tmp_path,
        monkeypatch,
        validated,
        motion_passed=True,
        evidence_passed=False,
    )

    qa_job, _ = runner.evaluate_delivery_candidate_qa(
        "qa-test-failed",
        motion_config=motion,
        expected_motion_config_sha256=motion_hash,
        test_policy=policy,
        expected_test_policy_sha256=policy_hash,
        repo_root=tmp_path,
        now=NOW,
    )

    assert qa_job["state"] == "candidate-qa-repair-required"
    assert qa_job["candidate_qa"]["tests"]["state"] == "failed"
    assert qa_job["candidate_qa"]["tests"]["evidence_passed"] is False
    with pytest.raises(
        runner.PublicWebsiteDesignRunnerError,
        match="one-attempt transition",
    ):
        runner.evaluate_delivery_candidate_qa(
            "qa-test-failed",
            motion_config=motion,
            expected_motion_config_sha256=motion_hash,
            test_policy=policy,
            expected_test_policy_sha256=policy_hash,
            repo_root=tmp_path,
            now=NOW,
        )


@pytest.mark.parametrize(
    "target",
    [
        "candidate",
        "canonical",
        "trusted-toolchain",
        "motion-config",
        "test-policy",
        "motion-receipt",
        "test-receipt",
    ],
)
def test_candidate_qa_replay_rejects_mutation_and_substitution(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    target: str,
) -> None:
    _fake_repo(tmp_path)
    run_id = f"qa-drift-{target}"
    validated = _validated_qa_run(
        tmp_path,
        monkeypatch,
        run_id=run_id,
    )
    motion, motion_hash, policy, policy_hash = _write_qa_inputs(
        tmp_path,
        run_id,
    )
    _patch_qa_engines(
        tmp_path,
        monkeypatch,
        validated,
        motion_passed=True,
        evidence_passed=True,
    )
    qa_job, _ = runner.evaluate_delivery_candidate_qa(
        run_id,
        motion_config=motion,
        expected_motion_config_sha256=motion_hash,
        test_policy=policy,
        expected_test_policy_sha256=policy_hash,
        repo_root=tmp_path,
        now=NOW,
    )
    qa = qa_job["candidate_qa"]
    if target == "trusted-toolchain":
        changed_toolchain = deepcopy(qa["trusted_toolchain"])
        changed_toolchain["test_evidence"]["sha256"] = "9" * 64
        monkeypatch.setattr(
            runner,
            "_trusted_qa_toolchain_binding",
            lambda _root: changed_toolchain,
        )
    elif target == "candidate":
        changed = tmp_path / qa["candidate"]["website_path"] / "styles.css"
    elif target == "canonical":
        changed = tmp_path / "website" / "styles.css"
    elif target == "motion-config":
        changed = tmp_path / qa["motion"]["config"]["path"]
    elif target == "test-policy":
        changed = tmp_path / qa["tests"]["policy"]["path"]
    elif target == "motion-receipt":
        changed = tmp_path / qa["motion"]["receipt"]["path"]
    else:
        changed = tmp_path / qa["tests"]["receipt"]["path"]
    if target != "trusted-toolchain":
        changed.write_bytes(changed.read_bytes() + b" ")

    verification = runner.verify_design_delivery_job(
        qa_job,
        repo_root=tmp_path,
        now=NOW,
    )
    checks = {item["id"]: item["passed"] for item in verification["checks"]}
    assert checks["candidate-qa-binding"] is False


def test_cross_run_test_evidence_consumes_attempt_but_never_advances(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _fake_repo(tmp_path)
    validated = _validated_qa_run(
        tmp_path,
        monkeypatch,
        run_id="qa-cross-run",
    )
    motion, motion_hash, policy, policy_hash = _write_qa_inputs(
        tmp_path,
        "qa-cross-run",
    )
    _patch_qa_engines(
        tmp_path,
        monkeypatch,
        validated,
        motion_passed=True,
        evidence_passed=True,
        cross_run_test_evidence=True,
    )

    with pytest.raises(
        runner.PublicWebsiteDesignRunnerError,
        match="cross-run",
    ):
        runner.evaluate_delivery_candidate_qa(
            "qa-cross-run",
            motion_config=motion,
            expected_motion_config_sha256=motion_hash,
            test_policy=policy,
            expected_test_policy_sha256=policy_hash,
            repo_root=tmp_path,
            now=NOW,
        )
    job, _ = runner.load_latest_delivery_job(
        "qa-cross-run",
        repo_root=tmp_path,
    )
    verification = runner.verify_design_delivery_job(
        job,
        repo_root=tmp_path,
        now=NOW,
    )
    checks = {item["id"]: item["passed"] for item in verification["checks"]}
    assert checks["candidate-qa-binding"] is False
    with pytest.raises(
        runner.PublicWebsiteDesignRunnerError,
        match="no longer verifies|already exists",
    ):
        runner.evaluate_delivery_candidate_qa(
            "qa-cross-run",
            motion_config=motion,
            expected_motion_config_sha256=motion_hash,
            test_policy=policy,
            expected_test_policy_sha256=policy_hash,
            repo_root=tmp_path,
            now=NOW,
        )


def test_historical_v1_job_is_verifiable_but_cannot_advance(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _fake_repo(tmp_path)
    _patch_brief(monkeypatch, _brief_audit())
    job, path = runner.create_design_delivery_job(
        goal="Retain one historical local receipt.",
        route_id="home",
        reconciliation_receipt=_aligned_reconciliation(
            tmp_path,
            "legacy-read-only",
        ),
        run_id="legacy-read-only",
        repo_root=tmp_path,
        now=NOW,
    )
    job["schema"] = runner.LEGACY_DELIVERY_JOB_SCHEMA
    path.write_text(json.dumps(job, indent=2) + "\n", encoding="utf-8")
    loaded, _ = runner.load_latest_delivery_job(
        "legacy-read-only",
        repo_root=tmp_path,
    )
    verification = runner.verify_design_delivery_job(
        loaded,
        repo_root=tmp_path,
        now=NOW,
    )

    assert verification["passed"] is True
    assert verification["compatibility"] == "historical-v1-read-only"
    with pytest.raises(
        runner.PublicWebsiteDesignRunnerError,
        match="historical read-only",
    ):
        runner.stage_design_delivery_job(
            "legacy-read-only",
            repo_root=tmp_path,
            now=NOW,
        )

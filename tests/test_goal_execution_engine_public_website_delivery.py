"""Focused safety coverage for explicit staged website delivery dispatch."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from aureon.autonomous import aureon_public_website_design_runner as runner
from aureon.autonomous import aureon_staged_design_worker_broker as broker
from aureon.core.goal_execution_engine import (
    PUBLIC_WEBSITE_DESIGN_DELIVERY_INTENT,
    PUBLIC_WEBSITE_DESIGN_DELIVERY_REQUEST_SCHEMA,
    GoalExecutionEngine,
    GoalStep,
)


def _request(action: str, **extra: object) -> dict[str, object]:
    return {
        "request_schema": PUBLIC_WEBSITE_DESIGN_DELIVERY_REQUEST_SCHEMA,
        "action": action,
        "delivery_mode": "staged-only",
        "release_eligible": False,
        "package_authority": "none",
        "deployment_authority": "none",
        **extra,
    }


def _runner_job(state: str = "work-order-ready") -> dict[str, object]:
    return {
        "schema": runner.DELIVERY_JOB_SCHEMA,
        "state": state,
        "authority": dict(runner.AUTHORITY),
        "release_eligible": False,
        "package_authority": "none",
        "deployment_authority": "none",
    }


def _broker_result(
    state: str = "lease-issued",
    *,
    run_id: str,
    lease_id: str = "lease-0123456789abcdef0123456789abcdef",
    adapter_id: str = broker.DEFAULT_TRUSTED_ADAPTER_ID,
    candidate_validated: bool = False,
) -> dict[str, object]:
    result: dict[str, object] = {
        "schema": broker.LEASE_SCHEMA if state == "lease-issued" else broker.OUTCOME_SCHEMA,
        "state": state,
        "authority": dict(broker.AUTHORITY),
        "release_eligible": False,
        "package_authority": "none",
        "deployment_authority": "none",
        "credential_access": "none",
        "run_id": run_id,
        "lease_id": lease_id,
        "adapter_id": adapter_id,
    }
    if candidate_validated:
        result["candidate_outcome"] = {
            "state": "candidate-validated",
            "candidate_validation": {"passed": True},
        }
    return result


def _write_receipt(tmp_path: Path, name: str, payload: dict[str, object]) -> Path:
    path = tmp_path / name
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _feedback_signal() -> dict[str, object]:
    return {
        "signal_id": "fixture-first-visit-clarity",
        "signal_kind": "clarity-gap",
        "disposition": "action-requested",
        "priority": "high",
        "requested_response_dimension": "first-visit-clarity",
        "route_scope": "/",
        "claim_ids": ["homepage-claim"],
    }


def _feedback_capsule(*, include_signal: bool = True) -> dict[str, object]:
    signal = _feedback_signal()
    signals = (
        [
            {
                "signal": signal,
                "signal_capsule_sha256": runner._json_sha256(signal),
            }
        ]
        if include_signal
        else []
    )
    return {"route_id": "home", "route": "/", "signals": signals}


def _feedback_response_manifest() -> dict[str, dict[str, object]]:
    signal = _feedback_signal()
    signal_id = str(signal["signal_id"])
    return {
        signal_id: {
            "disposition": signal["disposition"],
            "response_code": "addressed",
            "route_scope": signal["route_scope"],
            "changed_paths": ["styles.css"],
            "claim_ids": ["homepage-claim"],
            "signal_capsule_sha256": runner._json_sha256(signal),
        }
    }


def _worker_submission() -> dict[str, object]:
    return {
        "patch_manifest": [{"path": "styles.css", "content": "body { color: #123456; }\n"}],
        "claim_impact_manifest": [
            {
                "path": "styles.css",
                "classification": "no-material-claim-change",
                "rationale": "A bounded presentation refinement leaves public claim wording unchanged.",
            }
        ],
        "claim_surface_manifest": [],
        "feedback_response_manifest": _feedback_response_manifest(),
    }


def test_plain_language_website_redesign_stays_on_analysis_cycle() -> None:
    plan = GoalExecutionEngine()._decompose_goal(
        "Research competitors and redesign the public website with serious high-spec motion."
    )

    assert [step.intent for step in plan.steps] == ["public_website_design_cycle"]
    assert all(step.intent != PUBLIC_WEBSITE_DESIGN_DELIVERY_INTENT for step in plan.steps)


def test_structured_create_dispatches_only_after_exact_staged_only_contract(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[dict[str, object]] = []

    def fake_create(**kwargs: object) -> tuple[dict[str, object], Path]:
        calls.append(dict(kwargs))
        return _runner_job(), tmp_path / "01-work-order-ready.json"

    monkeypatch.setattr(runner, "create_design_delivery_job", fake_create)
    monkeypatch.setattr(
        runner,
        "stage_design_delivery_job",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("stage must not be inferred")),
    )

    plan = GoalExecutionEngine().submit_structured_goal(
        intent=PUBLIC_WEBSITE_DESIGN_DELIVERY_INTENT,
        params=_request(
            "create",
            goal="Refine the bounded investor-facing home route.",
            route_id="home",
            reconciliation_receipt="artifacts/website-operator/alignment.json",
            run_id="engine-create",
        ),
    )

    assert plan.status == "completed"
    assert plan.steps[0].intent == PUBLIC_WEBSITE_DESIGN_DELIVERY_INTENT
    assert plan.steps[0].validation_result["valid"] is True
    assert calls == [
        {
            "goal": "Refine the bounded investor-facing home route.",
            "route_id": "home",
            "reconciliation_receipt": Path("artifacts/website-operator/alignment.json"),
            "owner_source_decision": None,
            "backup_receipt": None,
            "design_cycle_receipt": None,
            "design_copy_task_id": None,
            "run_id": "engine-create",
        }
    ]
    result = plan.steps[0].result["result"]
    assert result["release_eligible"] is False
    assert result["package_authority"] == "none"
    assert result["deployment_authority"] == "none"


def test_structured_copy_create_forwards_paired_design_task_binding(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[dict[str, object]] = []

    def fake_create(**kwargs: object) -> tuple[dict[str, object], Path]:
        calls.append(dict(kwargs))
        return _runner_job(), tmp_path / "01-work-order-ready.json"

    monkeypatch.setattr(runner, "create_design_delivery_job", fake_create)
    plan = GoalExecutionEngine().submit_structured_goal(
        intent=PUBLIC_WEBSITE_DESIGN_DELIVERY_INTENT,
        params=_request(
            "create",
            goal="Repair one exact investor-copy route.",
            route_id="investor-reading-room",
            reconciliation_receipt="artifacts/website-operator/alignment.json",
            design_cycle_receipt=("artifacts/website-operator/design-cycle.json"),
            design_copy_task_id="DESIGN-COPY-001",
            run_id="engine-copy-create",
        ),
    )

    assert plan.status == "completed"
    assert calls[0]["design_cycle_receipt"] == Path("artifacts/website-operator/design-cycle.json")
    assert calls[0]["design_copy_task_id"] == "DESIGN-COPY-001"


@pytest.mark.parametrize(
    "extra",
    [
        {"design_cycle_receipt": ("artifacts/website-operator/design-cycle.json")},
        {"design_copy_task_id": "DESIGN-COPY-001"},
        {
            "design_cycle_receipt": ("artifacts/website-operator/design-cycle.json"),
            "design_copy_task_id": "copy-1",
        },
    ],
)
def test_structured_copy_create_rejects_partial_or_malformed_task_binding(
    extra: dict[str, object],
) -> None:
    with pytest.raises(ValueError, match="design"):
        GoalExecutionEngine._normalise_public_website_design_delivery_request(
            _request(
                "create",
                goal="Repair one exact investor-copy route.",
                route_id="investor-reading-room",
                reconciliation_receipt=("artifacts/website-operator/alignment.json"),
                run_id="engine-copy-invalid",
                **extra,
            )
        )


def test_structured_stage_does_not_infer_create_or_any_other_action(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[str] = []

    monkeypatch.setattr(
        runner,
        "create_design_delivery_job",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("create must not be inferred")),
    )

    def fake_stage(run_id: str) -> tuple[dict[str, object], Path]:
        calls.append(run_id)
        return _runner_job("candidate-staged"), tmp_path / "02-candidate-staged.json"

    monkeypatch.setattr(runner, "stage_design_delivery_job", fake_stage)

    plan = GoalExecutionEngine().submit_structured_goal(
        intent=PUBLIC_WEBSITE_DESIGN_DELIVERY_INTENT,
        params=_request("stage", run_id="engine-stage"),
    )

    assert plan.status == "completed"
    assert calls == ["engine-stage"]
    assert plan.steps[0].result["result"]["runner_result"]["state"] == "candidate-staged"


def test_validate_requires_and_forwards_the_claim_surface_manifest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[tuple[str, list[object], list[object]]] = []

    def fake_validate(
        run_id: str,
        *,
        claim_impacts: list[object],
        claim_surface_manifest: list[object],
    ) -> tuple[dict[str, object], Path]:
        calls.append((run_id, claim_impacts, claim_surface_manifest))
        result = _runner_job("candidate-validated")
        result["candidate_validation"] = {"passed": True}
        return result, _write_receipt(tmp_path, "candidate-validated.json", result)

    monkeypatch.setattr(runner, "validate_design_delivery_job", fake_validate)

    plan = GoalExecutionEngine().submit_structured_goal(
        intent=PUBLIC_WEBSITE_DESIGN_DELIVERY_INTENT,
        params=_request(
            "validate",
            run_id="engine-validate",
            claim_impacts=[],
            claim_surface_manifest=[],
        ),
    )

    assert plan.status == "completed"
    assert calls == [("engine-validate", [], [])]

    with pytest.raises(ValueError, match="claim_surface_manifest"):
        GoalExecutionEngine().submit_structured_goal(
            intent=PUBLIC_WEBSITE_DESIGN_DELIVERY_INTENT,
            params=_request("validate", run_id="missing-surface", claim_impacts=[]),
        )


def test_delivery_runner_cannot_be_called_from_text_or_deployment_like_params(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = GoalExecutionEngine()
    runner_called = False

    def forbidden_runner(*_args: object, **_kwargs: object) -> object:
        nonlocal runner_called
        runner_called = True
        raise AssertionError("runner must not be called for a rejected request")

    monkeypatch.setattr(runner, "create_design_delivery_job", forbidden_runner)

    with pytest.raises(ValueError, match="Promotion, release, and deployment"):
        engine.submit_structured_goal(
            intent=PUBLIC_WEBSITE_DESIGN_DELIVERY_INTENT,
            params=_request(
                "deploy",
                goal="Deploy the candidate.",
                route_id="home",
                reconciliation_receipt="artifacts/website-operator/alignment.json",
                run_id="engine-deploy",
            ),
        )

    with pytest.raises(ValueError, match="repository-relative path"):
        engine.submit_structured_goal(
            intent=PUBLIC_WEBSITE_DESIGN_DELIVERY_INTENT,
            params=_request(
                "create",
                goal="Refine a route.",
                route_id="home",
                reconciliation_receipt="C:/outside/alignment.json",
                run_id="engine-absolute",
            ),
        )

    bare_step = GoalStep(
        intent=PUBLIC_WEBSITE_DESIGN_DELIVERY_INTENT,
        params={"action": "stage", "run_id": "bare-step"},
    )
    result = engine._execute_step(bare_step)

    assert runner_called is False
    assert result["success"] is False
    assert "request_schema" in str(result["error"])


def test_worker_lease_dispatches_only_the_explicit_broker_lease_action(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[tuple[str, dict[str, object]]] = []

    def fake_issue(run_id: str, **kwargs: object) -> tuple[dict[str, object], Path]:
        calls.append((run_id, dict(kwargs)))
        result = _broker_result(
            run_id=run_id, adapter_id=str(kwargs.get("adapter_id") or broker.DEFAULT_TRUSTED_ADAPTER_ID)
        )
        return result, _write_receipt(tmp_path, "worker-lease.json", result)

    monkeypatch.setattr(broker, "issue_staged_design_worker_lease", fake_issue)
    monkeypatch.setattr(
        broker,
        "submit_staged_design_worker_delivery",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("worker submit must not be inferred from a lease request")
        ),
    )
    monkeypatch.setattr(
        runner,
        "stage_design_delivery_job",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("runner stage must not be called by a worker lease")
        ),
    )

    plan = GoalExecutionEngine().submit_structured_goal(
        intent=PUBLIC_WEBSITE_DESIGN_DELIVERY_INTENT,
        params=_request(
            "worker-lease",
            run_id="engine-worker-lease",
            adapter_id=broker.DEFAULT_TRUSTED_ADAPTER_ID,
            ttl_seconds=60,
        ),
    )

    assert plan.status == "completed"
    assert calls == [
        (
            "engine-worker-lease",
            {"adapter_id": broker.DEFAULT_TRUSTED_ADAPTER_ID, "ttl_seconds": 60},
        )
    ]
    result = plan.steps[0].result["result"]
    assert result["broker_result"]["state"] == "lease-issued"
    assert result["authority"] == broker.AUTHORITY
    assert result["credential_access"] == "none"
    assert result["authority_boundary_verified"] is True


def test_worker_submit_passes_only_the_sealed_manifest_to_the_broker(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[tuple[str, str, str, dict[str, object]]] = []
    submission = _worker_submission()
    feedback_capsule = _feedback_capsule()

    monkeypatch.setattr(
        broker,
        "issue_staged_design_worker_lease",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("worker lease must not be inferred from a submit request")
        ),
    )

    def fake_submit(
        run_id: str,
        lease_id: str,
        *,
        adapter_id: str,
        submission: dict[str, object],
    ) -> tuple[dict[str, object], Path]:
        assert (
            broker._normalise_submission(
                submission,
                allowed_paths=("styles.css",),
                feedback_capsule=feedback_capsule,
                feedback_capsule_sha256=runner._json_sha256(feedback_capsule),
            )
            == submission
        )
        calls.append((run_id, lease_id, adapter_id, submission))
        result = _broker_result(
            "candidate-validated",
            run_id=run_id,
            lease_id=lease_id,
            adapter_id=adapter_id,
            candidate_validated=True,
        )
        return result, _write_receipt(tmp_path, "worker-outcome.json", result)

    monkeypatch.setattr(broker, "submit_staged_design_worker_delivery", fake_submit)
    monkeypatch.setattr(
        runner,
        "validate_design_delivery_job",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("the engine must not call runner validation for a broker submit")
        ),
    )

    plan = GoalExecutionEngine().submit_structured_goal(
        intent=PUBLIC_WEBSITE_DESIGN_DELIVERY_INTENT,
        params=_request(
            "worker-submit",
            run_id="engine-worker-submit",
            lease_id="lease-0123456789abcdef0123456789abcdef",
            adapter_id=broker.DEFAULT_TRUSTED_ADAPTER_ID,
            **submission,
        ),
    )

    assert plan.status == "completed"
    assert calls == [
        (
            "engine-worker-submit",
            "lease-0123456789abcdef0123456789abcdef",
            broker.DEFAULT_TRUSTED_ADAPTER_ID,
            submission,
        )
    ]
    assert plan.steps[0].result["tool_used"] == "staged_design_worker_broker"
    assert plan.steps[0].validation_result["valid"] is True


def test_worker_submit_allows_empty_feedback_manifest_for_empty_sealed_capsule(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[dict[str, object]] = []
    submission = _worker_submission()
    submission["feedback_response_manifest"] = {}
    empty_feedback_capsule = _feedback_capsule(include_signal=False)

    def fake_submit(
        run_id: str,
        lease_id: str,
        *,
        adapter_id: str,
        submission: dict[str, object],
    ) -> tuple[dict[str, object], Path]:
        assert (
            broker._normalise_submission(
                submission,
                allowed_paths=("styles.css",),
                feedback_capsule=empty_feedback_capsule,
                feedback_capsule_sha256=runner._json_sha256(empty_feedback_capsule),
            )
            == submission
        )
        calls.append(submission)
        result = _broker_result(
            "candidate-validated",
            run_id=run_id,
            lease_id=lease_id,
            adapter_id=adapter_id,
            candidate_validated=True,
        )
        return result, _write_receipt(tmp_path, "empty-feedback-worker-outcome.json", result)

    monkeypatch.setattr(broker, "submit_staged_design_worker_delivery", fake_submit)

    plan = GoalExecutionEngine().submit_structured_goal(
        intent=PUBLIC_WEBSITE_DESIGN_DELIVERY_INTENT,
        params=_request(
            "worker-submit",
            run_id="engine-empty-feedback-worker-submit",
            lease_id="lease-0123456789abcdef0123456789abcdef",
            adapter_id=broker.DEFAULT_TRUSTED_ADAPTER_ID,
            **submission,
        ),
    )

    assert plan.status == "completed"
    assert calls == [submission]
    assert calls[0]["feedback_response_manifest"] == {}


def test_worker_submit_rejects_worker_authored_qa_evidence_before_broker_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    broker_called = False

    def forbidden_submit(*_args: object, **_kwargs: object) -> object:
        nonlocal broker_called
        broker_called = True
        raise AssertionError("the broker must not receive worker-authored QA evidence")

    monkeypatch.setattr(broker, "submit_staged_design_worker_delivery", forbidden_submit)
    submission = _worker_submission()
    submission["test_manifest"] = [
        {
            "id": "stylesheet-review",
            "status": "passed",
            "evidence": "A worker assertion cannot replace independent QA.",
        }
    ]

    with pytest.raises(ValueError, match="unsupported fields: test_manifest"):
        GoalExecutionEngine().submit_structured_goal(
            intent=PUBLIC_WEBSITE_DESIGN_DELIVERY_INTENT,
            params=_request(
                "worker-submit",
                run_id="engine-worker-authored-qa",
                lease_id="lease-0123456789abcdef0123456789abcdef",
                adapter_id=broker.DEFAULT_TRUSTED_ADAPTER_ID,
                **submission,
            ),
        )

    assert broker_called is False


@pytest.mark.parametrize(
    "nested_qa",
    [
        {"test_manifest": []},
        {"nested": [{"TEST_MANIFEST": [{"status": "passed"}]}]},
        {"metadata": ({"test_manifest": []},)},
    ],
)
def test_worker_submit_rejects_nested_worker_authored_qa_before_broker_call(
    monkeypatch: pytest.MonkeyPatch,
    nested_qa: dict[str, object],
) -> None:
    broker_called = False

    def forbidden_submit(*_args: object, **_kwargs: object) -> object:
        nonlocal broker_called
        broker_called = True
        raise AssertionError("the broker must not receive nested worker-authored QA evidence")

    monkeypatch.setattr(broker, "submit_staged_design_worker_delivery", forbidden_submit)
    submission = _worker_submission()
    signal_id = str(_feedback_signal()["signal_id"])
    feedback_manifest = submission["feedback_response_manifest"]
    assert isinstance(feedback_manifest, dict)
    feedback_response = feedback_manifest[signal_id]
    assert isinstance(feedback_response, dict)
    feedback_response.update(nested_qa)

    with pytest.raises(ValueError, match="worker-authored test_manifest"):
        GoalExecutionEngine().submit_structured_goal(
            intent=PUBLIC_WEBSITE_DESIGN_DELIVERY_INTENT,
            params=_request(
                "worker-submit",
                run_id="engine-nested-worker-authored-qa",
                lease_id="lease-0123456789abcdef0123456789abcdef",
                adapter_id=broker.DEFAULT_TRUSTED_ADAPTER_ID,
                **submission,
            ),
        )

    assert broker_called is False


def test_worker_submit_rejects_cyclic_input_before_broker_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    broker_called = False

    def forbidden_submit(*_args: object, **_kwargs: object) -> object:
        nonlocal broker_called
        broker_called = True
        raise AssertionError("the broker must not receive cyclic input")

    monkeypatch.setattr(broker, "submit_staged_design_worker_delivery", forbidden_submit)
    submission = _worker_submission()
    cycle: list[object] = []
    cycle.append(cycle)
    patch_manifest = submission["patch_manifest"]
    assert isinstance(patch_manifest, list)
    patch = patch_manifest[0]
    assert isinstance(patch, dict)
    patch["metadata"] = cycle

    with pytest.raises(ValueError, match="acyclic JSON-compatible"):
        GoalExecutionEngine().submit_structured_goal(
            intent=PUBLIC_WEBSITE_DESIGN_DELIVERY_INTENT,
            params=_request(
                "worker-submit",
                run_id="engine-cyclic-worker-input",
                lease_id="lease-0123456789abcdef0123456789abcdef",
                adapter_id=broker.DEFAULT_TRUSTED_ADAPTER_ID,
                **submission,
            ),
        )

    assert broker_called is False


@pytest.mark.parametrize(
    "manifest_name",
    [
        "patch_manifest",
        "claim_impact_manifest",
        "claim_surface_manifest",
    ],
)
def test_worker_submit_rejects_worker_authored_qa_in_every_manifest_before_broker_call(
    monkeypatch: pytest.MonkeyPatch,
    manifest_name: str,
) -> None:
    broker_called = False

    def forbidden_submit(*_args: object, **_kwargs: object) -> object:
        nonlocal broker_called
        broker_called = True
        raise AssertionError("the broker must not receive nested worker-authored QA evidence")

    monkeypatch.setattr(broker, "submit_staged_design_worker_delivery", forbidden_submit)
    submission = _worker_submission()
    manifest = submission[manifest_name]
    assert isinstance(manifest, list)
    if manifest:
        entry = manifest[0]
        assert isinstance(entry, dict)
        entry["test_manifest"] = []
    else:
        manifest.append({"test_manifest": []})

    with pytest.raises(ValueError, match="worker-authored test_manifest"):
        GoalExecutionEngine().submit_structured_goal(
            intent=PUBLIC_WEBSITE_DESIGN_DELIVERY_INTENT,
            params=_request(
                "worker-submit",
                run_id=f"engine-{manifest_name}-worker-authored-qa",
                lease_id="lease-0123456789abcdef0123456789abcdef",
                adapter_id=broker.DEFAULT_TRUSTED_ADAPTER_ID,
                **submission,
            ),
        )

    assert broker_called is False


def test_worker_submit_rejects_malformed_feedback_manifest_before_broker_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    broker_called = False

    def forbidden_submit(*_args: object, **_kwargs: object) -> object:
        nonlocal broker_called
        broker_called = True
        raise AssertionError("the broker must not receive a malformed feedback manifest")

    monkeypatch.setattr(broker, "submit_staged_design_worker_delivery", forbidden_submit)

    signal_id = str(_feedback_signal()["signal_id"])
    for mutation in ("missing", "list", "non-object-value"):
        submission = _worker_submission()
        if mutation == "missing":
            submission.pop("feedback_response_manifest")
        elif mutation == "list":
            submission["feedback_response_manifest"] = []
        else:
            submission["feedback_response_manifest"] = {signal_id: "not-an-object"}

        with pytest.raises(ValueError, match="feedback_response_manifest"):
            GoalExecutionEngine().submit_structured_goal(
                intent=PUBLIC_WEBSITE_DESIGN_DELIVERY_INTENT,
                params=_request(
                    "worker-submit",
                    run_id=f"engine-invalid-feedback-{mutation}",
                    lease_id="lease-0123456789abcdef0123456789abcdef",
                    adapter_id=broker.DEFAULT_TRUSTED_ADAPTER_ID,
                    **submission,
                ),
            )

    assert broker_called is False


def test_worker_broker_result_with_any_credential_or_release_authority_is_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    unsafe = _broker_result(run_id="engine-unsafe-worker-lease")
    unsafe["credential_access"] = "read-only"

    monkeypatch.setattr(
        broker,
        "issue_staged_design_worker_lease",
        lambda *_args, **_kwargs: (
            unsafe,
            _write_receipt(tmp_path, "unsafe-worker-lease.json", unsafe),
        ),
    )

    plan = GoalExecutionEngine().submit_structured_goal(
        intent=PUBLIC_WEBSITE_DESIGN_DELIVERY_INTENT,
        params=_request("worker-lease", run_id="engine-unsafe-worker-lease"),
    )

    assert plan.status == "failed"
    assert plan.steps[0].result["success"] is False
    assert plan.steps[0].result["error"] == "worker-broker-authority-boundary-invalid"
    assert plan.steps[0].validation_result["valid"] is False


@pytest.mark.parametrize("fault", ["schema", "run-id", "receipt"])
def test_worker_broker_requires_matching_schema_identity_and_receipt_readback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fault: str
) -> None:
    def fake_issue(run_id: str, **_kwargs: object) -> tuple[dict[str, object], Path]:
        result = _broker_result(run_id=run_id)
        stored = dict(result)
        if fault == "schema":
            result["schema"] = broker.OUTCOME_SCHEMA
            stored = dict(result)
        elif fault == "run-id":
            result["run_id"] = "another-run"
            stored = dict(result)
        elif fault == "receipt":
            stored["lease_id"] = "lease-fedcba9876543210fedcba9876543210"
        return result, _write_receipt(tmp_path, f"broker-{fault}.json", stored)

    monkeypatch.setattr(broker, "issue_staged_design_worker_lease", fake_issue)

    plan = GoalExecutionEngine().submit_structured_goal(
        intent=PUBLIC_WEBSITE_DESIGN_DELIVERY_INTENT,
        params=_request("worker-lease", run_id="engine-contract-check"),
    )

    assert plan.status == "failed"
    assert plan.steps[0].result["error"] == "worker-broker-result-contract-invalid"
    assert plan.steps[0].result["result"]["broker_receipt_verified"] is False

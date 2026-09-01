from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path
from typing import Any

from aureon.autonomous.aureon_full_live_release import (
    compute_source_scope_digest,
    evaluate_full_live_release,
    probe_full_stack,
    validate_os_protection_summary,
)
from aureon.autonomous.aureon_full_stack_release_gate import (
    CANONICAL_STACK_LAYERS,
    PRODUCTION_READBACK,
    REQUIRED_LAYER_CONTROLS,
    FullStackReleaseRequest,
    LocalFullStackEvidenceResolver,
    build_full_stack_bundle,
    build_layer_evidence,
)

NOW = 1_787_100_000.0
SCOPE = "a" * 64


def _run_git_test_mutation(root: Path, *arguments: str) -> None:
    """Retry only transient Windows object-store locks in disposable test repos."""

    completed: subprocess.CompletedProcess[str] | None = None
    for attempt in range(5):
        completed = subprocess.run(
            ["git", "-C", str(root), *arguments],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        if completed.returncode == 0:
            return
        transient_windows_lock = (
            os.name == "nt" and "permission denied" in completed.stderr.casefold()
        )
        if not transient_windows_lock or attempt == 4:
            completed.check_returncode()
        time.sleep(1.0)
    assert completed is not None
    completed.check_returncode()


def _live_environment() -> dict[str, str]:
    values = {
        "ALPACA_API_KEY": "secret-alpaca-key",
        "ALPACA_SECRET_KEY": "secret-alpaca-secret",
        "AUREON_ALLOWED_ORIGINS": "https://example.test",
        "AUREON_WORKER_ACCESS_SECRET": "secret-worker-access-value-that-is-long-enough",
        "BINANCE_API_KEY": "secret-binance-key",
        "BINANCE_API_SECRET": "secret-binance-secret",
        "CAPITAL_API_KEY": "secret-capital-key",
        "CAPITAL_IDENTIFIER": "secret-capital-identifier",
        "CAPITAL_PASSWORD": "secret-capital-password",
        "CLOUDFLARE_ACCOUNT_ID": "secret-cloudflare-account",
        "CLOUDFLARE_API_TOKEN": "secret-cloudflare-token",
        "KRAKEN_API_KEY": "secret-kraken-key",
        "KRAKEN_API_SECRET": "secret-kraken-secret",
        "SUPABASE_ANON_KEY": "secret-supabase-anon",
        "SUPABASE_SERVICE_ROLE_KEY": "secret-supabase-service",
        "SUPABASE_URL": "https://example.supabase.co",
        "ALPACA_PAPER": "false",
        "AUREON_AUDIT_MODE": "0",
        "AUREON_DISABLE_EXCHANGE_MUTATIONS": "0",
        "AUREON_DISABLE_REAL_ORDERS": "0",
        "AUREON_DRY_RUN": "0",
        "AUREON_LIVE_TRADING": "1",
        "AUREON_ORDER_AUTHORITY_MODE": "intent_only_runtime_gated",
        "AUREON_ORDER_INTENT_PUBLISH": "1",
        "AUREON_ORDER_TICKET_REQUIRES_EXECUTOR": "1",
        "AUREON_UNIFIED_ORDER_EXECUTOR": "1",
        "BINANCE_TESTNET": "false",
        "BINANCE_USE_TESTNET": "false",
        "CAPITAL_DEMO": "false",
        "CAPITAL_DEMO_MODE": "false",
        "CONFIRM_LIVE": "yes",
        "DRY_RUN": "0",
        "LIVE": "1",
    }
    return values


def _stack_ok(root: Path, scope_digest: str, now: float) -> dict[str, Any]:
    del root, now
    return {
        "ok": scope_digest == SCOPE,
        "decision": "ACCEPT",
        "reason": "all_layers_provider_read_back",
        "receipt_id": "stack:release:" + "1" * 64,
    }


def _economic_ok(root: Path) -> dict[str, Any]:
    del root
    return {
        "ok": True,
        "inventory_aligned": True,
        "certified_no_bypass": True,
        "detected_count": 70,
        "classified_count": 70,
        "blocker_count": 0,
        "counts_by_classification": {
            "provider-client-raw-transport-guard": 66,
            "economic-boundary-last-mile": 4,
        },
    }


def _os_protection_ok(root: Path) -> dict[str, Any]:
    del root
    return {
        "ok": True,
        "reason": "full_os_protection_certified",
        "schema": "aureon.os-protection-boundary-census.v1",
        "source_files_scanned": 5113,
        "detected_count": 6850,
        "classified_count": 6850,
        "blocker_count": 0,
        "protected_count": 6850,
        "explicit_hold_count": 0,
        "parse_error_count": 0,
        "inventory_sha256": "5" * 64,
        "certified_full_os_protection": True,
    }


def _fields_ok(root: Path, now: float) -> dict[str, Any]:
    del root, now
    return {
        "ok": True,
        "hnc_receipt_id": "hnc:live_field:" + "2" * 64,
        "auris_receipt_id": "auris:cosmic_state:" + "3" * 24,
        "provider_moment_digest": "4" * 64,
        "provider_receipt_ids": ["provider:one", "provider:two"],
        "provider_source_timestamp": NOW - 1.0,
        "auris_gamma": 0.95,
        "auris_gate_open": True,
        "active_threshold": 0.8,
    }


def _ollama_ok(environ: dict[str, str]) -> dict[str, Any]:
    del environ
    return {"ok": True, "reason": "ollama_model_ready", "model": "llama3:latest", "available_model_count": 2}


def _evaluate(
    tmp_path: Path,
    *,
    environment: dict[str, str] | None = None,
    economic=_economic_ok,
    os_protection=_os_protection_ok,
):
    return evaluate_full_live_release(
        root=tmp_path,
        environ=environment or _live_environment(),
        now=NOW,
        scope_digest_fn=lambda root: SCOPE,
        stack_probe_fn=_stack_ok,
        os_protection_audit_fn=os_protection,
        economic_audit_fn=economic,
        field_probe_fn=_fields_ok,
        ollama_probe_fn=_ollama_ok,
    )


def test_exact_full_live_release_accepts_as_evidence_only(tmp_path: Path) -> None:
    result = _evaluate(tmp_path)

    assert result.decision == "ACCEPT"
    assert result.receipt["failed_checks"] == []
    assert result.receipt["reason"] == "full_live_release_accepted"
    assert result.receipt["full_os_protection"]["protected_count"] == 6850
    assert result.receipt["full_os_protection"]["certified_full_os_protection"] is True
    assert result.receipt["economic_zero_bypass"]["blocker_count"] == 0
    assert result.receipt["ten_nine_one_fields"]["auris_gamma"] == 0.95
    assert result.receipt["receipt_id"].startswith("live:release:")
    for name in (
        "action_eligible",
        "accounting_eligible",
        "learning_eligible",
        "economic_mutation",
        "provider_eligible",
        "operational_eligible",
        "actionable",
        "action_gate_passed",
    ):
        assert result.receipt[name] is False


def test_operator_approval_cannot_override_economic_blockers(tmp_path: Path) -> None:
    def blocked(root: Path) -> dict[str, Any]:
        del root
        return {
            "ok": False,
            "inventory_aligned": True,
            "certified_no_bypass": False,
            "detected_count": 1570,
            "classified_count": 1570,
            "blocker_count": 1445,
            "counts_by_classification": {"live-capable-unguarded-blocker": 1445},
        }

    result = _evaluate(tmp_path, economic=blocked)

    assert result.decision == "HOLD"
    assert "economic_zero_bypass" in result.receipt["failed_checks"]
    assert result.receipt["economic_zero_bypass"]["blocker_count"] == 1445
    assert result.receipt["economic_mutation"] is False


def test_operator_approval_cannot_override_full_os_protection_blockers(tmp_path: Path) -> None:
    def blocked(root: Path) -> dict[str, Any]:
        del root
        return {
            "ok": False,
            "reason": "unprotected_os_routes_remain",
            "schema": "aureon.os-protection-boundary-census.v1",
            "source_files_scanned": 5113,
            "detected_count": 6850,
            "classified_count": 6850,
            "blocker_count": 6850,
            "protected_count": 0,
            "explicit_hold_count": 0,
            "parse_error_count": 0,
            "inventory_sha256": "9" * 64,
            "certified_full_os_protection": False,
        }

    result = _evaluate(tmp_path, os_protection=blocked)

    assert result.decision == "HOLD"
    assert "full_os_protection" in result.receipt["failed_checks"]
    assert result.receipt["full_os_protection"]["blocker_count"] == 6850
    assert result.receipt["full_os_protection"]["ok"] is False
    assert result.receipt["actionable"] is False


def test_rehashed_os_protection_decision_cannot_hide_blockers(tmp_path: Path) -> None:
    def forged(root: Path) -> dict[str, Any]:
        payload = _os_protection_ok(root)
        payload["blocker_count"] = 1
        payload["protected_count"] = 6849
        return payload

    result = _evaluate(tmp_path, os_protection=forged)

    assert result.decision == "HOLD"
    assert result.receipt["full_os_protection"]["reason"] == "os_protection_audit_failed"
    assert result.receipt["full_os_protection"]["ok"] is False


def test_os_protection_summary_requires_complete_exact_partition() -> None:
    payload = _os_protection_ok(Path("."))
    payload["classified_count"] = 6849

    try:
        validate_os_protection_summary(payload)
    except ValueError as exc:
        assert str(exc) == "complete_os_protection_classification_partition_required"
    else:  # pragma: no cover - defensive assertion
        raise AssertionError("incomplete OS-protection partition was accepted")


def test_missing_cloud_credentials_hold_without_leaking_values(tmp_path: Path) -> None:
    environment = _live_environment()
    leaked = environment.pop("CLOUDFLARE_API_TOKEN")
    result = _evaluate(tmp_path, environment=environment)
    serialized = json.dumps(result.receipt, sort_keys=True)

    assert result.decision == "HOLD"
    assert "credentials" in result.receipt["failed_checks"]
    assert result.receipt["credentials"]["missing_names"] == ["CLOUDFLARE_API_TOKEN"]
    assert leaked not in serialized
    assert "secret-binance-secret" not in serialized


def test_live_flags_must_be_exact_even_with_all_credentials(tmp_path: Path) -> None:
    environment = _live_environment()
    environment["DRY_RUN"] = "1"
    environment["AUREON_ORDER_AUTHORITY_MODE"] = "unbounded"

    result = _evaluate(tmp_path, environment=environment)

    assert result.decision == "HOLD"
    assert "live_flags" in result.receipt["failed_checks"]
    assert result.receipt["live_flags"]["failed_names"] == ["AUREON_ORDER_AUTHORITY_MODE", "DRY_RUN"]


def _write_production_bundle(root: Path, scope_digest: str, *, now: float = NOW) -> FullStackReleaseRequest:
    request = FullStackReleaseRequest(
        release_id="release:provider-readback-test",
        environment="production",
        assurance_level=PRODUCTION_READBACK,
        scope_digest=scope_digest,
    )
    layers = []
    for layer_id in CANONICAL_STACK_LAYERS:
        provider_id = f"provider:{layer_id}:readback"
        layers.append(
            build_layer_evidence(
                layer_id=layer_id,
                environment=request.environment,
                scope_digest=request.scope_digest,
                checked_at=now - 10.0,
                expires_at=now + 300.0,
                evidence_kinds=["offline_contract", "provider_readback"],
                control_ids=list(REQUIRED_LAYER_CONTROLS[layer_id]),
                source_receipt_ids=[f"acceptance:{layer_id}:contract", provider_id],
                provider_readback_receipt_ids=[provider_id],
                summary_digest=(layer_id.encode().hex() + "0" * 64)[:64],
            )
        )
    bundle = build_full_stack_bundle(
        resolver_id=LocalFullStackEvidenceResolver.resolver_id,
        request=request,
        issued_at=now - 5.0,
        layers=layers,
    )
    path = root / "docs" / "evidence" / "aureon_full_stack_release.v1.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(bundle), encoding="utf-8")
    return request


def test_local_manifest_requires_exact_current_source_scope(tmp_path: Path) -> None:
    _write_production_bundle(tmp_path, SCOPE)

    accepted = probe_full_stack(tmp_path, SCOPE, NOW)
    drifted = probe_full_stack(tmp_path, "b" * 64, NOW)

    assert accepted["ok"] is True
    assert accepted["decision"] == "ACCEPT"
    assert drifted["ok"] is False
    assert drifted["decision"] == "HOLD"


def test_source_scope_digest_changes_for_dirty_and_untracked_code(tmp_path: Path) -> None:
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.email", "test@example.invalid"], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.name", "Aureon Test"], check=True)
    source = tmp_path / "brain.py"
    source.write_text("ANSWER = 1\n", encoding="utf-8")
    _run_git_test_mutation(tmp_path, "add", "brain.py")
    _run_git_test_mutation(tmp_path, "commit", "-qm", "baseline")

    clean = compute_source_scope_digest(tmp_path)
    source.write_text("ANSWER = 2\n", encoding="utf-8")
    dirty = compute_source_scope_digest(tmp_path)
    (tmp_path / "new_agent.py").write_text("SEAT = 'keeper'\n", encoding="utf-8")
    untracked = compute_source_scope_digest(tmp_path)

    assert len({clean, dirty, untracked}) == 3
    assert all(len(item) == 64 for item in (clean, dirty, untracked))

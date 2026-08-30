from __future__ import annotations

import io
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from scripts.validation.audit_aureon_hnc_ollama_coreviewer import main


NOW = datetime(2026, 8, 11, 12, 0, tzinfo=timezone.utc)


def _field_reader(_root: Path, now: datetime) -> dict[str, Any]:
    stamp = now.isoformat()
    return {
        "gamma": 0.82,
        "advisory_open": True,
        "lighthouse_severity": None,
        "auris_confidence": 0.79,
        "beta": 1.0,
        "evidence_ready": True,
        "sources": {
            "canonical_hnc_field": {
                "source": "canonical_hnc_field",
                "status": "live",
                "truth_status": "live",
                "fresh": True,
                "generated_values": False,
                "source_timestamp": stamp,
            },
            "auris_cosmic_state": {
                "source": "auris_cosmic_state",
                "status": "live",
                "truth_status": "live",
                "fresh": True,
                "generated_values": False,
                "source_timestamp": stamp,
            },
        },
    }


def _flow_computer(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
    return {
        "flow": "steady",
        "field_status": "live",
        "gamma": 0.82,
        "auris_confidence": 0.79,
        "beta": 1.0,
        "patch_batch_limit": 2,
        "minimum_review_cycles": 1,
        "required_test_layers": ["focused", "integration", "regression"],
    }


def _inventory_reader() -> dict[str, Any]:
    return {
        "source_file_count": 3990,
        "consumer_file_count": 54,
        "unexpected_direct_llm_surfaces": [],
        "all_discovered_calls_centralized": True,
    }


def _snapshot(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def _assert_numeric_free(value: Any) -> None:
    if isinstance(value, dict):
        for item in value.values():
            _assert_numeric_free(item)
    elif isinstance(value, list):
        for item in value:
            _assert_numeric_free(item)
    elif isinstance(value, (int, float)) and not isinstance(value, bool):
        raise AssertionError(f"no_data envelope contains numeric value: {value!r}")


def test_default_mode_is_no_network_no_bootstrap_and_no_filesystem_mutation(tmp_path: Path) -> None:
    sentinel = tmp_path / "sentinel.txt"
    sentinel.write_text("unchanged", encoding="utf-8")
    before = _snapshot(tmp_path)
    calls = {"bootstrap": 0, "router": 0}

    def forbidden_bootstrap(_root: Path) -> dict[str, Any]:
        calls["bootstrap"] += 1
        raise AssertionError("default mode must not bootstrap credentials")

    def forbidden_router(_prompt: str, _context: dict[str, Any], _clock: Any) -> dict[str, Any]:
        calls["router"] += 1
        raise AssertionError("default mode must not construct or call an Ollama route")

    stdout = io.StringIO()
    exit_code = main(
        [],
        root=tmp_path,
        field_reader=_field_reader,
        flow_computer=_flow_computer,
        inventory_reader=_inventory_reader,
        bootstrapper=forbidden_bootstrap,
        live_router=forbidden_router,
        clock=lambda: NOW,
        stdout=stdout,
    )
    report = json.loads(stdout.getvalue())

    assert exit_code == 0
    assert calls == {"bootstrap": 0, "router": 0}
    assert _snapshot(tmp_path) == before
    assert report["mode"] == "audit_only"
    assert report["status"] == "coreviewer_ready"
    assert report["actionable"] is False
    assert report["side_effect_contract"] == {
        "credential_bootstrap": "none",
        "filesystem_writes": "none",
        "network_requests": "none",
        "patch_application": "none",
        "stdout": "json_only",
    }


def test_live_mode_bootstraps_once_routes_one_review_and_requires_complete_receipt(
    tmp_path: Path,
) -> None:
    calls = {"bootstrap": 0, "router": 0}

    def bootstrap(_root: Path) -> dict[str, Any]:
        calls["bootstrap"] += 1
        return {
            "loaded": True,
            "keystore_applied": True,
            "present": {"AUREON_OLLAMA_API_KEY": True},
        }

    def router(prompt: str, context: dict[str, Any], clock: Any) -> dict[str, Any]:
        calls["router"] += 1
        assert prompt == "review provenance repair"
        assert context["authority"] == "advisory_review_only_non_actionable"
        stamp = clock().isoformat()
        return {
            "status": "received",
            "truth_status": "live",
            "actionable": False,
            "generated_values": False,
            "source": "ollama_cloud_native_api",
            "model": "current-code-model",
            "model_selection_source": "ranked_live_catalog",
            "request_id": "coreview-real-request",
            "requested_at": stamp,
            "received_at": stamp,
            "provider_timestamp": stamp,
            "provider_done": True,
            "provider_done_reason": "stop",
            "response_text": "Observed finding with a bounded recommendation.",
            "error": "",
            "credential_values_exposed": False,
        }

    stdout = io.StringIO()
    exit_code = main(
        ["--live-ollama", "--prompt", "review provenance repair"],
        root=tmp_path,
        field_reader=_field_reader,
        flow_computer=_flow_computer,
        inventory_reader=_inventory_reader,
        bootstrapper=bootstrap,
        live_router=router,
        clock=lambda: NOW,
        stdout=stdout,
    )
    report = json.loads(stdout.getvalue())

    assert exit_code == 0
    assert calls == {"bootstrap": 1, "router": 1}
    assert report["status"] == "live_review_received"
    assert report["provider_request_count"] == 1
    assert report["provider_receipt"]["model"] == "current-code-model"
    assert report["provider_receipt"]["source"] == "ollama_cloud_native_api"
    assert report["provider_receipt"]["provider_timestamp"] == NOW.isoformat()
    assert report["actionable"] is False
    assert report["review_contract"]["filesystem_writes"] == "none"


def test_stale_live_receipt_is_numeric_free_no_data_and_non_actionable(tmp_path: Path) -> None:
    def bootstrap(_root: Path) -> dict[str, Any]:
        return {"present": {"OLLAMA_API_KEY": True}}

    def stale_router(_prompt: str, _context: dict[str, Any], _clock: Any) -> dict[str, Any]:
        stale = (NOW - timedelta(hours=1)).isoformat()
        return {
            "source": "ollama_cloud_native_api",
            "model": "current-code-model",
            "model_selection_source": "ranked_live_catalog",
            "request_id": "coreview-stale-request",
            "requested_at": stale,
            "received_at": stale,
            "provider_timestamp": stale,
            "provider_done": True,
            "response_text": "This stale response must not be accepted.",
            "error": "",
        }

    stdout = io.StringIO()
    exit_code = main(
        ["--live-ollama"],
        root=tmp_path,
        field_reader=_field_reader,
        flow_computer=_flow_computer,
        inventory_reader=_inventory_reader,
        bootstrapper=bootstrap,
        live_router=stale_router,
        clock=lambda: NOW,
        stdout=stdout,
    )
    report = json.loads(stdout.getvalue())

    assert exit_code == 1
    assert report["status"] == "no_data"
    assert report["truth_status"] == "no_data"
    assert report["actionable"] is False
    assert report["provider_receipt"]["model"] is None
    assert report["provider_receipt"]["response_text"] is None
    assert report["no_data_reason"] == "provider_timestamp_missing_stale_or_future"
    _assert_numeric_free(report)

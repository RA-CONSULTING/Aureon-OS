#!/usr/bin/env python3
"""Read-only HNC/Auris and Ollama coreviewer audit.

The default command is deliberately inert: it reads current local evidence,
computes Aureon's native evolution flow, inventories source-level LLM routes,
and emits one JSON document to stdout.  It does not bootstrap credentials,
construct an Ollama client, touch the network, or persist a report.

``--live-ollama`` is the sole network mode.  It loads credentials only inside
the current process, selects the centralized ``self_evolution`` nerve without
completion probes, and sends exactly one advisory code-review request.  The
response is never executed, published, or treated as permission to mutate.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping, Optional, Sequence, TextIO


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

SCHEMA_VERSION = "aureon-hnc-ollama-coreviewer-audit-v1"
FIELD_MAX_AGE_SECONDS = 900.0
PROVIDER_MAX_AGE_SECONDS = 300.0
FUTURE_TOLERANCE_SECONDS = 30.0
REAL_TRUTH_STATUSES = frozenset({"live", "real_derived"})
DEFAULT_REVIEW_PROMPT = (
    "Review the current bounded Aureon backend repair for provenance, test "
    "coverage, rollback safety, and preservation of HNC/Auris equations."
)

Clock = Callable[[], datetime]
FieldReader = Callable[[Path, datetime], Mapping[str, Any]]
FlowComputer = Callable[..., Mapping[str, Any]]
InventoryReader = Callable[[], Mapping[str, Any]]
Bootstrapper = Callable[[Path], Mapping[str, Any]]
LiveRouter = Callable[[str, Mapping[str, Any], Clock], Mapping[str, Any]]


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _parse_timestamp(value: Any) -> Optional[datetime]:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        number = float(value)
        if not math.isfinite(number):
            return None
        try:
            return datetime.fromtimestamp(number, tz=timezone.utc)
        except (OverflowError, OSError, ValueError):
            return None
    text = str(value).strip()
    if not text:
        return None
    try:
        return _aware_utc(datetime.fromisoformat(text.replace("Z", "+00:00")))
    except ValueError:
        return None


def _timestamp_is_fresh(value: Any, now: datetime, max_age_seconds: float) -> bool:
    parsed = _parse_timestamp(value)
    if parsed is None:
        return False
    age = (_aware_utc(now) - parsed).total_seconds()
    return -FUTURE_TOLERANCE_SECONDS <= age <= max_age_seconds


def _timestamp_text(value: Any) -> Optional[str]:
    parsed = _parse_timestamp(value)
    return parsed.isoformat() if parsed is not None else None


def _trace_receipt(
    name: str,
    row: Mapping[str, Any],
    *,
    now: datetime,
    max_age_seconds: float,
) -> dict[str, Any]:
    timestamp = row.get("source_timestamp", row.get("_ts", row.get("ts", row.get("timestamp"))))
    truth_status = str(row.get("truth_status") or "").strip().lower()
    generated_values = row.get("generated_values")
    fresh = _timestamp_is_fresh(timestamp, now, max_age_seconds)
    valid = bool(row) and fresh and truth_status in REAL_TRUTH_STATUSES and generated_values is False
    receipt: dict[str, Any] = {
        "source": name,
        "status": "live" if valid else "no_data",
        "truth_status": truth_status if valid else "no_data",
        "fresh": valid,
        "generated_values": False,
        "source_timestamp": _timestamp_text(timestamp) if valid else None,
    }
    if not valid:
        reasons: list[str] = []
        if not row:
            reasons.append("source_receipt_missing")
        if row and not fresh:
            reasons.append("source_timestamp_missing_or_stale")
        if row and truth_status not in REAL_TRUTH_STATUSES:
            reasons.append("truth_status_not_live_or_real_derived")
        if row and generated_values is not False:
            reasons.append("generated_values_not_explicitly_false")
        receipt["no_data_reason"] = ";".join(reasons) or "source_receipt_invalid"
    return receipt


def read_fresh_field_inputs(root: Path, now: datetime) -> Mapping[str, Any]:
    """Read real local HNC/Auris evidence without starting any producer."""

    field_payload: dict[str, Any] = {}
    try:
        from aureon.core.hnc_field import read_canonical_field

        field = read_canonical_field()
        field_payload = field.to_dict() if hasattr(field, "to_dict") else dict(vars(field))
    except Exception as exc:  # the audit must report darkness, never invent a field
        field_payload = {"available": False, "error": type(exc).__name__}

    field_row = dict(field_payload)
    field_row.setdefault("truth_status", field_payload.get("truth_status"))
    field_row.setdefault("generated_values", field_payload.get("generated_values"))
    field_receipt = _trace_receipt(
        "canonical_hnc_field",
        field_row if field_payload.get("available") else {},
        now=now,
        max_age_seconds=FIELD_MAX_AGE_SECONDS,
    )

    def latest(name: str) -> dict[str, Any]:
        try:
            from aureon.core.bus_trace import read_trace_latest

            value = read_trace_latest(name) or {}
            return dict(value) if isinstance(value, Mapping) else {}
        except Exception:
            return {}

    auris_row = latest("auris_cosmic_state")
    lighthouse_row = latest("lighthouse_event")
    auris_receipt = _trace_receipt(
        "auris_cosmic_state",
        auris_row,
        now=now,
        max_age_seconds=FIELD_MAX_AGE_SECONDS,
    )
    lighthouse_receipt = _trace_receipt(
        "lighthouse_event",
        lighthouse_row,
        now=now,
        max_age_seconds=FIELD_MAX_AGE_SECONDS,
    )

    beta: Optional[float] = None
    try:
        from aureon.core.hnc_params import load_params

        beta = float(load_params().beta)
        if not math.isfinite(beta):
            beta = None
    except Exception:
        beta = None

    field_live = field_receipt["status"] == "live"
    auris_live = auris_receipt["status"] == "live"
    return {
        "gamma": field_payload.get("coherence_gamma") if field_live else None,
        "advisory_open": auris_row.get("gate_open") if auris_live else None,
        "lighthouse_severity": lighthouse_row.get("severity")
        if lighthouse_receipt["status"] == "live"
        else None,
        "auris_confidence": auris_row.get("coherence_gamma") if auris_live else None,
        "beta": beta,
        "evidence_ready": bool(field_live and auris_live),
        "sources": {
            "canonical_hnc_field": field_receipt,
            "auris_cosmic_state": auris_receipt,
            "lighthouse_event": lighthouse_receipt,
        },
    }


def compute_native_flow(
    gamma: Any,
    advisory_open: Any,
    lighthouse_severity: Any,
    *,
    auris_confidence: Any,
    beta: Any,
) -> Mapping[str, Any]:
    from aureon.operator.coherence_gate import compute_evolution_flow

    return compute_evolution_flow(
        gamma,
        advisory_open,
        lighthouse_severity,
        auris_confidence=auris_confidence,
        beta=beta,
    )


def read_static_llm_inventory() -> Mapping[str, Any]:
    """Use the source scanner only; never call ``runtime_inventory`` here."""

    from scripts.validation.audit_external_llm_fallback import static_inventory

    return static_inventory()


def bootstrap_live_credentials(root: Path) -> Mapping[str, Any]:
    from aureon.core.aureon_env import bootstrap_credentials

    return bootstrap_credentials(root)


def _field_view(inputs: Mapping[str, Any], flow: Mapping[str, Any]) -> dict[str, Any]:
    sources = dict(inputs.get("sources") or {})
    ready = bool(inputs.get("evidence_ready"))
    view: dict[str, Any] = {
        "status": "live" if ready else "no_data",
        "truth_status": "real_derived" if ready else "no_data",
        "actionable": False,
        "generated_values": False,
        "flow": str(flow.get("flow") or "observe"),
        "field_status": str(flow.get("field_status") or "canonical_dark"),
        "required_test_layers": list(flow.get("required_test_layers") or []),
        "sources": sources,
    }
    if ready:
        view.update(
            {
                "gamma": flow.get("gamma"),
                "auris_confidence": flow.get("auris_confidence"),
                "beta": flow.get("beta"),
                "patch_batch_limit": flow.get("patch_batch_limit"),
                "minimum_review_cycles": flow.get("minimum_review_cycles"),
            }
        )
    else:
        blocked = [
            name
            for name in ("canonical_hnc_field", "auris_cosmic_state")
            if (sources.get(name) or {}).get("status") != "live"
        ]
        view["no_data_reason"] = "missing_or_stale_field_receipts:" + ",".join(blocked)
    return view


def _inventory_view(inventory: Mapping[str, Any]) -> dict[str, Any]:
    unexpected = list(inventory.get("unexpected_direct_llm_surfaces") or [])
    centralized = bool(inventory.get("all_discovered_calls_centralized")) and not unexpected
    return {
        "status": "real_derived" if centralized else "no_data",
        "truth_status": "real_derived" if centralized else "no_data",
        "actionable": False,
        "generated_values": False,
        "source": "repo_static_source_inventory",
        "source_file_count": inventory.get("source_file_count"),
        "consumer_file_count": inventory.get("consumer_file_count"),
        "all_discovered_calls_centralized": centralized,
        "unexpected_direct_llm_surfaces": unexpected,
    }


def build_default_report(
    *,
    root: Path = REPO_ROOT,
    field_reader: FieldReader = read_fresh_field_inputs,
    flow_computer: FlowComputer = compute_native_flow,
    inventory_reader: InventoryReader = read_static_llm_inventory,
    clock: Clock = _utc_now,
) -> dict[str, Any]:
    """Build an audit report using local reads and pure computation only."""

    now = _aware_utc(clock())
    inputs = dict(field_reader(Path(root).resolve(), now))
    flow = dict(
        flow_computer(
            inputs.get("gamma"),
            inputs.get("advisory_open"),
            inputs.get("lighthouse_severity"),
            auris_confidence=inputs.get("auris_confidence"),
            beta=inputs.get("beta"),
        )
    )
    inventory = _inventory_view(dict(inventory_reader()))
    hnc = _field_view(inputs, flow)
    ready = hnc["status"] == "live" and inventory["status"] == "real_derived"
    return {
        "schema_version": SCHEMA_VERSION,
        "mode": "audit_only",
        "status": "coreviewer_ready" if ready else "coreviewer_observed",
        "truth_status": "real_derived",
        "actionable": False,
        "generated_values": False,
        "generated_at": now.isoformat(),
        "side_effect_contract": {
            "network_requests": "none",
            "filesystem_writes": "none",
            "credential_bootstrap": "none",
            "patch_application": "none",
            "stdout": "json_only",
        },
        "hnc_auris": hnc,
        "llm_static_inventory": inventory,
    }


def _safe_bootstrap_view(report: Mapping[str, Any]) -> dict[str, Any]:
    present = dict(report.get("present") or {})
    return {
        "loaded": bool(report.get("loaded")),
        "keystore_applied": bool(report.get("keystore_applied")),
        "ollama_key_present": any(
            bool(present.get(name))
            for name in ("AUREON_LLM_API_KEY", "OLLAMA_API_KEY", "AUREON_OLLAMA_API_KEY")
        ),
        "credential_values_exposed": False,
    }


def route_one_live_review(prompt: str, context: Mapping[str, Any], clock: Clock) -> Mapping[str, Any]:
    """Perform one Ollama Cloud review completion and return its receipt."""

    from aureon.integrations.ollama import OllamaModelSwitchboard
    from aureon.ollama_config import is_ollama_cloud_url, ollama_config_snapshot

    config = ollama_config_snapshot()
    if not config.get("cloud") or not config.get("api_key_configured"):
        return {
            "status": "no_data",
            "truth_status": "no_data",
            "actionable": False,
            "generated_values": False,
            "no_data_reason": "ollama_cloud_configuration_unavailable",
        }

    switchboard = OllamaModelSwitchboard()
    bridge, selection = switchboard.bridge_for("self_evolution", require_working=False)
    if (
        not selection.model
        or not selection.endpoint_reachable
        or selection.catalog_size < 1
        or "live_catalog" not in selection.source
        or not is_ollama_cloud_url(str(getattr(bridge, "base_url", "")))
    ):
        return {
            "status": "no_data",
            "truth_status": "no_data",
            "actionable": False,
            "generated_values": False,
            "no_data_reason": "live_self_evolution_model_receipt_unavailable",
        }

    request_id = f"coreview_{uuid.uuid4().hex}"
    requested_at = _aware_utc(clock())
    review_prompt = (
        "You are Aureon's advisory code co-reviewer. Do not call tools, edit files, "
        "authorize live actions, or claim tests ran. Separate observed evidence from "
        "recommendations and preserve HNC/Auris equations.\n\n"
        f"Review objective: {prompt}\n"
        f"Current verified local context: {json.dumps(context, sort_keys=True, default=str)}"
    )
    response = bridge.chat(
        [{"role": "user", "content": review_prompt}],
        model=selection.model,
        options={"temperature": 0.1, "num_predict": 900},
    )
    received_at = _aware_utc(clock())
    message = response.get("message") if isinstance(response.get("message"), Mapping) else {}
    return {
        "status": "received" if not response.get("error") else "no_data",
        "truth_status": "live" if not response.get("error") else "no_data",
        "actionable": False,
        "generated_values": False,
        "source": "ollama_cloud_native_api",
        "model": str(response.get("model") or selection.model),
        "model_selection_source": selection.source,
        "request_id": request_id,
        "requested_at": requested_at.isoformat(),
        "received_at": received_at.isoformat(),
        "provider_timestamp": response.get("created_at"),
        "provider_done": response.get("done"),
        "provider_done_reason": response.get("done_reason"),
        "response_text": str(message.get("content") or ""),
        "error": str(response.get("error") or ""),
        "prompt_eval_count": response.get("prompt_eval_count"),
        "eval_count": response.get("eval_count"),
        "credential_values_exposed": False,
    }


def _receipt_problem(receipt: Mapping[str, Any], now: datetime) -> str:
    required_text = {
        "source": receipt.get("source"),
        "model": receipt.get("model"),
        "model_selection_source": receipt.get("model_selection_source"),
        "request_id": receipt.get("request_id"),
        "requested_at": receipt.get("requested_at"),
        "received_at": receipt.get("received_at"),
        "provider_timestamp": receipt.get("provider_timestamp"),
        "response_text": receipt.get("response_text"),
    }
    missing = [name for name, value in required_text.items() if not str(value or "").strip()]
    if missing:
        return "provider_receipt_missing:" + ",".join(missing)
    if receipt.get("source") != "ollama_cloud_native_api":
        return "provider_source_not_ollama_cloud"
    if "live_catalog" not in str(receipt.get("model_selection_source") or ""):
        return "model_not_selected_from_live_catalog"
    if receipt.get("provider_done") is not True or str(receipt.get("error") or "").strip():
        return "provider_response_incomplete_or_error"
    if not _timestamp_is_fresh(receipt.get("provider_timestamp"), now, PROVIDER_MAX_AGE_SECONDS):
        return "provider_timestamp_missing_stale_or_future"
    requested = _parse_timestamp(receipt.get("requested_at"))
    received = _parse_timestamp(receipt.get("received_at"))
    if requested is None or received is None or received < requested:
        return "request_receipt_timestamps_invalid"
    return ""


def _numeric_free_no_data(
    base: Mapping[str, Any],
    reason: str,
    *,
    bootstrap: Optional[Mapping[str, Any]] = None,
    receipt: Optional[Mapping[str, Any]] = None,
) -> dict[str, Any]:
    hnc = dict(base.get("hnc_auris") or {})
    inventory = dict(base.get("llm_static_inventory") or {})
    failed_receipt = dict(receipt or {})
    return {
        "schema_version": SCHEMA_VERSION,
        "mode": "live_ollama",
        "status": "no_data",
        "truth_status": "no_data",
        "actionable": False,
        "generated_values": False,
        "generated_at": base.get("generated_at"),
        "no_data_reason": reason,
        "hnc_auris": {
            "status": hnc.get("status", "no_data"),
            "truth_status": hnc.get("truth_status", "no_data"),
            "actionable": False,
            "generated_values": False,
            "flow": hnc.get("flow"),
            "field_status": hnc.get("field_status"),
            "no_data_reason": hnc.get("no_data_reason"),
        },
        "llm_static_inventory": {
            "status": inventory.get("status", "no_data"),
            "truth_status": inventory.get("truth_status", "no_data"),
            "actionable": False,
            "generated_values": False,
            "source": inventory.get("source"),
            "all_discovered_calls_centralized": bool(
                inventory.get("all_discovered_calls_centralized")
            ),
            "unexpected_direct_llm_surfaces": list(
                inventory.get("unexpected_direct_llm_surfaces") or []
            ),
        },
        "credential_bootstrap": dict(bootstrap or {}),
        "provider_receipt": {
            "status": "no_data",
            "truth_status": "no_data",
            "actionable": False,
            "generated_values": False,
            "source": failed_receipt.get("source"),
            "model": None,
            "source_timestamp": None,
            "request_id": failed_receipt.get("request_id"),
            "requested_at": failed_receipt.get("requested_at"),
            "received_at": failed_receipt.get("received_at"),
            "response_text": None,
            "no_data_reason": reason,
            "credential_values_exposed": False,
        },
    }


def run_live_coreview(
    base: Mapping[str, Any],
    *,
    root: Path,
    prompt: str,
    bootstrapper: Bootstrapper = bootstrap_live_credentials,
    live_router: LiveRouter = route_one_live_review,
    clock: Clock = _utc_now,
) -> dict[str, Any]:
    hnc = dict(base.get("hnc_auris") or {})
    inventory = dict(base.get("llm_static_inventory") or {})
    if hnc.get("status") != "live":
        return _numeric_free_no_data(base, str(hnc.get("no_data_reason") or "hnc_auris_no_data"))
    if not inventory.get("all_discovered_calls_centralized"):
        return _numeric_free_no_data(base, "unexpected_direct_llm_surfaces_present")

    bootstrap = _safe_bootstrap_view(dict(bootstrapper(Path(root).resolve())))
    if not bootstrap["ollama_key_present"]:
        return _numeric_free_no_data(base, "ollama_cloud_credential_unavailable", bootstrap=bootstrap)

    context = {
        "hnc_auris": hnc,
        "llm_static_inventory": inventory,
        "authority": "advisory_review_only_non_actionable",
    }
    receipt = dict(live_router(str(prompt or DEFAULT_REVIEW_PROMPT), context, clock))
    now = _aware_utc(clock())
    problem = _receipt_problem(receipt, now)
    if problem:
        return _numeric_free_no_data(base, problem, bootstrap=bootstrap, receipt=receipt)

    return {
        "schema_version": SCHEMA_VERSION,
        "mode": "live_ollama",
        "status": "live_review_received",
        "truth_status": "live",
        "actionable": False,
        "generated_values": False,
        "generated_at": now.isoformat(),
        "hnc_auris": hnc,
        "llm_static_inventory": inventory,
        "credential_bootstrap": bootstrap,
        "provider_request_count": 1,
        "provider_receipt": receipt,
        "review_contract": {
            "role": "advisory_code_coreviewer",
            "patch_application": "none",
            "filesystem_writes": "none",
            "obsidian_writes": "none",
            "thought_bus_publications": "none",
            "state_writes": "none",
            "live_orders": "none",
        },
    }


def main(
    argv: Optional[Sequence[str]] = None,
    *,
    root: Path = REPO_ROOT,
    field_reader: FieldReader = read_fresh_field_inputs,
    flow_computer: FlowComputer = compute_native_flow,
    inventory_reader: InventoryReader = read_static_llm_inventory,
    bootstrapper: Bootstrapper = bootstrap_live_credentials,
    live_router: LiveRouter = route_one_live_review,
    clock: Clock = _utc_now,
    stdout: TextIO = sys.stdout,
) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--live-ollama",
        action="store_true",
        help="make exactly one authenticated Ollama Cloud advisory review request",
    )
    parser.add_argument(
        "--prompt",
        default=DEFAULT_REVIEW_PROMPT,
        help="bounded code-review objective used only with --live-ollama",
    )
    args = parser.parse_args(argv)

    report = build_default_report(
        root=root,
        field_reader=field_reader,
        flow_computer=flow_computer,
        inventory_reader=inventory_reader,
        clock=clock,
    )
    if args.live_ollama:
        report = run_live_coreview(
            report,
            root=root,
            prompt=args.prompt,
            bootstrapper=bootstrapper,
            live_router=live_router,
            clock=clock,
        )
    json.dump(report, stdout, indent=2, sort_keys=True, default=str)
    stdout.write("\n")
    return 0 if report.get("status") != "no_data" else 1


if __name__ == "__main__":
    raise SystemExit(main())

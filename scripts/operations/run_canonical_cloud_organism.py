#!/usr/bin/env python3
"""Audit, compose, and optionally activate Aureon's one canonical organism.

The default command is a read-only preflight.  ``--activate`` remains
fail-closed until the live Druidic calibration is fresh and complete, the
repository mutation census is aligned with zero blockers, and an exact
capability manifest is bound to that census.  Only after those gates does the
command configure Ollama Cloud, construct the Queen, provision the 41+41 brain
fabric, or instantiate exchange clients.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
import time
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from aureon.core.organism_composition import (  # noqa: E402
    CALIBRATION_PATH,
    REQUIRED_SUBSYSTEMS,
    load_latest_calibration_status,
)
from aureon.core.unified_organism_builder import (  # noqa: E402
    build_canonical_cloud_organism,
)
from aureon.governance.economic_mutation_readiness import (  # noqa: E402
    build_economic_mutation_readiness_receipt,
)
from aureon.governance.legacy_capability_manifest import (  # noqa: E402
    validate_legacy_capability_manifest,
)
from aureon.queen.queen_process_roof import (  # noqa: E402
    discover_queen_process_manifest,
    get_canonical_queen_process_roof,
)

ALLOWLIST_PATH = ROOT / "scripts" / "validation" / "economic_mutation_allowlist.json"
DEFAULT_CAPABILITY_MANIFEST = ROOT / "state" / "legacy_economic_capability_manifest.json"
BOOTSTRAP_SCHEMA = "aureon.canonical-cloud-organism-bootstrap.v1"
_FALSE_FLAGS = {
    "action_eligible": False,
    "accounting_eligible": False,
    "learning_eligible": False,
    "actionable": False,
    "operational_eligible": False,
    "provider_eligible": False,
    "economic_mutation": False,
}
_SUBSYSTEM_ROLES = {
    "thought_bus": "canonical nervous system and receipt bus",
    "mycelium": "post-answer hive propagation",
    "connectome": "system topology and links",
    "soul": "purpose and triadic deliberation",
    "hnc": "10-to-9 coherence field",
    "auris": "9-to-1 answer coherence measurement",
    "celtic_voice_bank": "seasonal gates, triads, and seated voice context",
    "council": "four-seat peer deliberation",
    "crown": "independent Queen conscience key",
    "brain_switchboard": "Ollama Cloud model routing for 41 agents and processes",
    "queen_mind": "receipt-bound four-faculty cognitive identity",
}

if set(_SUBSYSTEM_ROLES) != set(REQUIRED_SUBSYSTEMS):
    raise RuntimeError("canonical_bootstrap_subsystem_map_mismatch")


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def _sha256_payload(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _run_census() -> Mapping[str, Any]:
    from scripts.validation.audit_economic_mutation_boundaries import audit

    return audit(root=ROOT, allowlist_path=ALLOWLIST_PATH)


def _load_json(path: Path) -> Mapping[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise ValueError("json_object_required")
    return payload


def inspect_bootstrap_readiness(
    *,
    capability_manifest_path: Path = DEFAULT_CAPABILITY_MANIFEST,
    calibration_path: Path = CALIBRATION_PATH,
    max_age_s: float = 300.0,
    clock: Callable[[], float] = time.time,
    census_loader: Callable[[], Mapping[str, Any]] | None = None,
) -> tuple[dict[str, Any], dict[str, Any], tuple[Any, ...]]:
    """Return a non-secret readiness report, census receipt, and capabilities."""

    current = float(clock())
    if not math.isfinite(current):
        raise ValueError("finite_bootstrap_clock_required")
    census = (census_loader or _run_census)()
    allowlist_sha256 = hashlib.sha256(ALLOWLIST_PATH.read_bytes()).hexdigest()
    economic = build_economic_mutation_readiness_receipt(
        census,
        allowlist_sha256=allowlist_sha256,
        now=current,
    )
    calibration = load_latest_calibration_status(
        complete_path=Path(calibration_path),
        hold_path=Path(calibration_path).with_name(
            "druidic_live_calibration_hold_latest.json"
        ),
        now=current,
        max_age_s=max_age_s,
    )
    queen_manifest = discover_queen_process_manifest(ROOT)
    queen_effect_counts = {
        effect: sum(item.effect_class == effect for item in queen_manifest.processes)
        for effect in ("active_process", "advisory", "authority_capable")
    }
    capabilities: tuple[Any, ...] = ()
    manifest_status = "blocked_by_economic_census"
    manifest_id = None
    manifest_error = None
    manifest_path = Path(capability_manifest_path)
    if economic["status"] == "ready":
        if not manifest_path.exists():
            manifest_status = "missing"
            manifest_error = "current_legacy_capability_manifest_required"
        else:
            try:
                manifest, capabilities = validate_legacy_capability_manifest(
                    _load_json(manifest_path),
                    economic_readiness_receipt=economic,
                )
                manifest_status = "ready"
                manifest_id = manifest["manifest_id"]
            except (OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
                manifest_status = "hold"
                manifest_error = str(exc)
    reason = None
    if economic["status"] != "ready":
        reason = economic["reason"]
    elif calibration.get("status") != "complete":
        reason = calibration.get("reason") or "complete_druidic_calibration_required"
    elif manifest_status != "ready":
        reason = manifest_error or "current_legacy_capability_manifest_required"
    causal: dict[str, Any] = {
        "schema": BOOTSTRAP_SCHEMA,
        "status": "ready_to_activate" if reason is None else "hold",
        "reason": reason,
        "economic_readiness_receipt_id": economic["receipt_id"],
        "economic_inventory_aligned": economic["inventory_aligned"],
        "economic_no_bypass_certified": economic["certified_no_bypass"],
        "economic_blocker_count": economic["blocker_count"],
        "calibration_status": calibration.get("status", "missing"),
        "calibration_reason": calibration.get("reason"),
        "calibration_receipt_id": calibration.get("receipt_id"),
        "capability_manifest_status": manifest_status,
        "capability_manifest_id": manifest_id,
        "capability_manifest_error": manifest_error,
        "capability_count": len(capabilities),
        "registered_subsystem_count": len(_SUBSYSTEM_ROLES),
        "queen_process_manifest_id": queen_manifest.manifest_id,
        "queen_process_seated_count": len(queen_manifest.processes),
        "queen_process_effect_counts": queen_effect_counts,
        "queen_process_roof_status": "hold" if reason is not None else "pending_activation",
        "cloud_configuration_checked": False,
        "cloud_model_call_count": 0,
        "exchange_client_construction_count": 0,
        "exchange_call_count": 0,
        "order_call_count": 0,
        "derived_at": current,
        **_FALSE_FLAGS,
    }
    causal["receipt_id"] = f"organism-bootstrap:{_sha256_payload(causal)}"
    return causal, economic, capabilities


def activate(
    *,
    capability_manifest_path: Path = DEFAULT_CAPABILITY_MANIFEST,
    calibration_path: Path = CALIBRATION_PATH,
    max_age_s: float = 300.0,
) -> dict[str, Any]:
    """Construct the organism only after every preflight gate is READY."""

    report, economic, capabilities = inspect_bootstrap_readiness(
        capability_manifest_path=capability_manifest_path,
        calibration_path=calibration_path,
        max_age_s=max_age_s,
    )
    if report["status"] != "ready_to_activate":
        return report

    from aureon.autonomous.aureon_cloud_brain_composition import (
        build_material_truth_gated_cloud_thought_path,
    )
    from aureon.autonomous.aureon_internal_coding_workforce import (
        OllamaSwitchboardBrainResolver,
    )
    from aureon.ollama_config import ensure_ollama_runtime_config
    from aureon.queen.queen_conscience import QueenConscience

    config = ensure_ollama_runtime_config(force=True, repo_root=ROOT)
    if not (
        config.get("cloud") is True
        and config.get("api_key_configured") is True
        and config.get("authorization_header_enabled") is True
    ):
        failed = dict(report)
        failed["reason"] = "authenticated_ollama_cloud_runtime_required"
        failed["cloud_configuration_checked"] = True
        failed["receipt_id"] = f"organism-bootstrap:{_sha256_payload({key: value for key, value in failed.items() if key != 'receipt_id'})}"
        return failed

    composition, workforce, exchange = build_canonical_cloud_organism(
        brain_resolver=OllamaSwitchboardBrainResolver(),
        thought_path=build_material_truth_gated_cloud_thought_path(
            max_age_s=max_age_s
        ),
        conscience=QueenConscience(),
        capabilities=capabilities,
        present_subsystems=_SUBSYSTEM_ROLES,
        economic_readiness_receipt=economic,
        calibration_path=calibration_path,
        max_age_s=max_age_s,
    )
    status = composition.status()
    roof = get_canonical_queen_process_roof()
    roof_status = roof.status() if roof is not None else {
        "status": "hold",
        "reason": "canonical_queen_process_roof_required",
    }
    active = {
        **report,
        "status": "active" if status["status"] == "ready" else "hold",
        "reason": status["reason"],
        "cloud_configuration_checked": True,
        "cloud_model_call_count": len(workforce.work_receipts),
        "exchange_client_construction_count": len(exchange.client.clients),
        "organism_status": status,
        "queen_process_roof_status": roof_status["status"],
        "queen_process_roof": roof_status,
    }
    active["receipt_id"] = f"organism-bootstrap:{_sha256_payload({key: value for key, value in active.items() if key != 'receipt_id'})}"
    return active


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--activate", action="store_true")
    parser.add_argument("--report-only", action="store_true")
    parser.add_argument(
        "--capability-manifest",
        type=Path,
        default=DEFAULT_CAPABILITY_MANIFEST,
    )
    parser.add_argument("--calibration", type=Path, default=CALIBRATION_PATH)
    parser.add_argument("--max-age-s", type=float, default=300.0)
    args = parser.parse_args(argv)
    result = (
        activate(
            capability_manifest_path=args.capability_manifest,
            calibration_path=args.calibration,
            max_age_s=args.max_age_s,
        )
        if args.activate
        else inspect_bootstrap_readiness(
            capability_manifest_path=args.capability_manifest,
            calibration_path=args.calibration,
            max_age_s=args.max_age_s,
        )[0]
    )
    print(_canonical_json(result))
    if result["status"] in {"ready_to_activate", "active"} or args.report_only:
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

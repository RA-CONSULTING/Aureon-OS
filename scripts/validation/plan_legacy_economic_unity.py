#!/usr/bin/env python3
"""Build a deterministic no-discard migration plan for legacy mutations."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Mapping

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ALLOWLIST = Path(__file__).with_name("economic_mutation_allowlist.json")
PLAN_SCHEMA = "aureon.legacy_economic_unity_plan.v1"
BLOCKER = "live-capable-unguarded-blocker"
UNITY_TARGET = "aureon.governance.legacy_economic_unity"
ALREADY_UNIFIED = frozenset(
    {
        "economic-boundary-last-mile",
        "provider-client-raw-transport-guard",
    }
)


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


def _nonblank(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError(f"{name}_must_be_nonblank_canonical_text")
    return value


def _repo_path(value: Any) -> str:
    raw = _nonblank(value, "file")
    if "\\" in raw:
        raise ValueError("file_must_be_repo_relative_posix_path")
    parsed = PurePosixPath(raw)
    if parsed.is_absolute() or ".." in parsed.parts or raw != parsed.as_posix():
        raise ValueError("file_must_be_repo_relative_posix_path")
    return raw


def _wave(entry: Mapping[str, Any]) -> str:
    file = entry["file"]
    provider = entry["provider"]
    if file.startswith("imports/"):
        return "parallel_snapshot_merge"
    if file.startswith("tests/"):
        return "test_contract_alignment"
    if file.endswith("unified_exchange_client.py"):
        return "unified_exchange_dispatch"
    if "/exchanges/" in file and file.endswith("_client.py"):
        return "provider_transport_chokepoint"
    if file.endswith((".ts", ".tsx", ".js", ".mjs", ".cjs")):
        return "cross_runtime_signed_envelope"
    if provider == "multi-provider":
        return "multi_provider_orchestrator"
    if any(part in file for part in ("/queen/", "/bots/", "/trading/")):
        return "strategy_brain_adapter"
    if file.startswith("Kings_Accounting_Suite/"):
        return "accounting_brain_adapter"
    return "direct_call_adapter"


def _target_adapter(entry: Mapping[str, Any], wave: str) -> str:
    provider = entry["provider"]
    if wave == "cross_runtime_signed_envelope":
        return f"{UNITY_TARGET}.signed_cross_runtime.{provider}"
    if wave == "provider_transport_chokepoint":
        return f"{UNITY_TARGET}.provider_transport.{provider}"
    if wave == "unified_exchange_dispatch":
        return f"{UNITY_TARGET}.unified_exchange"
    if wave == "parallel_snapshot_merge":
        return f"{UNITY_TARGET}.snapshot_parity"
    return f"{UNITY_TARGET}.{provider}"


def _normalize_entry(raw: Mapping[str, Any]) -> dict[str, str]:
    if not isinstance(raw, Mapping):
        raise ValueError("allowlist_entry_must_be_mapping")
    required = {
        "file",
        "fingerprint",
        "provider",
        "operation",
        "transport",
        "classification",
        "rationale",
        "owner",
    }
    if set(raw) != required:
        raise ValueError("allowlist_entry_schema_mismatch")
    entry = {key: _nonblank(raw[key], key) for key in required}
    entry["file"] = _repo_path(entry["file"])
    if not entry["fingerprint"].startswith("econop:"):
        raise ValueError("economic_operation_fingerprint_required")
    return entry


def build_legacy_unity_plan(allowlist: Mapping[str, Any]) -> dict[str, Any]:
    """Map every census entry without deleting or discounting legacy paths."""

    if not isinstance(allowlist, Mapping) or allowlist.get("schema") != "aureon.economic-mutation-allowlist.v1":
        raise ValueError("economic_mutation_allowlist_v1_required")
    raw_entries = allowlist.get("entries")
    if not isinstance(raw_entries, list) or not raw_entries:
        raise ValueError("nonempty_economic_mutation_entries_required")
    entries = [_normalize_entry(entry) for entry in raw_entries]
    keys = [(entry["file"], entry["fingerprint"]) for entry in entries]
    if len(set(keys)) != len(keys):
        raise ValueError("economic_mutation_entries_must_be_unique")

    routes: list[dict[str, Any]] = []
    for entry in entries:
        classification = entry["classification"]
        if classification == BLOCKER:
            wave = _wave(entry)
            disposition = "MIGRATE_AND_PRESERVE"
            target = _target_adapter(entry, wave)
        elif classification in ALREADY_UNIFIED:
            wave = "verified_boundary"
            disposition = "PRESERVE_UNIFIED"
            target = UNITY_TARGET
        elif classification == "dry-run-test-demo-only":
            wave = "test_contract_alignment"
            disposition = "PRESERVE_TEST_CAPABILITY"
            target = UNITY_TARGET
        else:
            raise ValueError("unsupported_or_discounting_classification")
        route = {
            "file": entry["file"],
            "fingerprint": entry["fingerprint"],
            "provider": entry["provider"],
            "operation": entry["operation"],
            "transport": entry["transport"],
            "current_classification": classification,
            "disposition": disposition,
            "migration_wave": wave,
            "target_adapter": target,
            "legacy_capability_preserved": True,
            "requires_hnc_receipt": classification == BLOCKER,
            "requires_auris_receipt": classification == BLOCKER,
            "requires_dual_key": classification == BLOCKER,
            "live_activation": "HOLD_UNTIL_PROVIDER_READBACK" if classification == BLOCKER else "UNCHANGED",
        }
        route["route_plan_digest"] = _sha256_payload(route)
        routes.append(route)

    blocker_routes = [route for route in routes if route["current_classification"] == BLOCKER]
    wave_counts = Counter(route["migration_wave"] for route in blocker_routes)
    provider_counts = Counter(route["provider"] for route in blocker_routes)
    summary = {
        "total_census_entries": len(routes),
        "remaining_legacy_routes": len(blocker_routes),
        "migration_target_count": sum(route["disposition"] == "MIGRATE_AND_PRESERVE" for route in routes),
        "legacy_capability_preserved_count": sum(route["legacy_capability_preserved"] is True for route in routes),
        "discarded_route_count": 0,
        "discounted_route_count": 0,
        "capability_loss_count": 0,
        "wave_counts": dict(sorted(wave_counts.items())),
        "provider_counts": dict(sorted(provider_counts.items())),
        "migration_complete": not blocker_routes,
        "live_activation_ready": False,
    }
    plan: dict[str, Any] = {
        "schema": PLAN_SCHEMA,
        "source_allowlist_digest": _sha256_payload(allowlist),
        "policy": {
            "legacy_systems_are_migration_targets": True,
            "quarantine_is_not_completion": True,
            "hnc_auris_dual_key_required": True,
            "provider_readback_required_for_live_activation": True,
        },
        "summary": summary,
        "routes": routes,
    }
    plan["plan_digest"] = _sha256_payload(plan)
    validate_legacy_unity_plan(plan)
    return plan


def validate_legacy_unity_plan(plan: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(plan, Mapping) or plan.get("schema") != PLAN_SCHEMA:
        raise ValueError("legacy_economic_unity_plan_v1_required")
    normalized = dict(plan)
    plan_digest = normalized.pop("plan_digest", None)
    if plan_digest != _sha256_payload(normalized):
        raise ValueError("legacy_unity_plan_digest_mismatch")
    routes = normalized.get("routes")
    summary = normalized.get("summary")
    if not isinstance(routes, list) or not isinstance(summary, Mapping):
        raise ValueError("complete_legacy_unity_plan_required")
    if any(route.get("legacy_capability_preserved") is not True for route in routes):
        raise ValueError("all_legacy_capabilities_must_be_preserved")
    if any(route.get("disposition") in {"DISCARD", "IGNORE", "QUARANTINE_AS_COMPLETE"} for route in routes):
        raise ValueError("legacy_routes_must_not_be_discounted")
    blockers = [route for route in routes if route.get("current_classification") == BLOCKER]
    if any(route.get("disposition") != "MIGRATE_AND_PRESERVE" for route in blockers):
        raise ValueError("every_blocker_must_be_a_migration_target")
    if (
        summary.get("total_census_entries") != len(routes)
        or summary.get("remaining_legacy_routes") != len(blockers)
        or summary.get("migration_target_count") != len(blockers)
        or summary.get("legacy_capability_preserved_count") != len(routes)
        or summary.get("discarded_route_count") != 0
        or summary.get("discounted_route_count") != 0
        or summary.get("capability_loss_count") != 0
        or summary.get("migration_complete") is not (not blockers)
        or summary.get("live_activation_ready") is not False
    ):
        raise ValueError("legacy_unity_plan_summary_mismatch")
    for route in routes:
        item = dict(route)
        digest = item.pop("route_plan_digest", None)
        if digest != _sha256_payload(item):
            raise ValueError("legacy_unity_route_digest_mismatch")
    return dict(plan)


def _load_json(path: Path) -> Mapping[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, Mapping):
        raise ValueError("json_object_required")
    return value


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--allowlist", type=Path, default=DEFAULT_ALLOWLIST)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--summary-only", action="store_true")
    parser.add_argument("--require-complete", action="store_true")
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    allowlist_path = args.allowlist.resolve()
    if ROOT not in allowlist_path.parents:
        raise SystemExit("allowlist_must_be_inside_repo")
    plan = build_legacy_unity_plan(_load_json(allowlist_path))
    payload: Mapping[str, Any] = plan["summary"] if args.summary_only else plan
    encoded = _canonical_json(payload) + "\n"
    if args.output is not None:
        output = args.output.resolve()
        if ROOT not in output.parents:
            raise SystemExit("output_must_be_inside_repo")
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(encoded, encoding="utf-8", newline="\n")
    else:
        print(encoded, end="")
    if args.require_complete and not plan["summary"]["migration_complete"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

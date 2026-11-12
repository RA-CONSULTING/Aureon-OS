"""Create one canonical held, no-mutation authority-chain probe."""
from __future__ import annotations

import argparse
import hashlib
import json
import time
import uuid

from contract import (
    INTENT_SCHEMA,
    canonical_bytes,
    probe_runtime_measurement_sha256,
    validate_intent,
    validate_readiness_release_binding,
)


SCOPE = [
    "AUREON_DEPLOYMENT_HOLD",
    "AUREON_DISABLE_REAL_ORDERS",
    "AUREON_DISABLE_EXCHANGE_MUTATIONS",
    "AUREON_LIVE_TRADING",
    "AUREON_ORDER_INTENT_PUBLISH",
    "AUREON_UNIFIED_ORDER_EXECUTOR",
]
SAFE_CONTROLS = {
    "AUREON_DEPLOYMENT_HOLD": True,
    "AUREON_DISABLE_REAL_ORDERS": True,
    "AUREON_DISABLE_EXCHANGE_MUTATIONS": True,
    "AUREON_LIVE_TRADING": False,
    "AUREON_ORDER_INTENT_PUBLISH": False,
    "AUREON_UNIFIED_ORDER_EXECUTOR": False,
}


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def build_probe(*, event_sha256: str, lease_expires_at_ms: int,
                revision: str, now_ms: int | None = None,
                readiness_release: dict | None = None) -> dict:
    current = int(time.time() * 1000) if now_ms is None else int(now_ms)
    authorization = {
        "active": True,
        "expires_at_ms": int(lease_expires_at_ms),
        "event_sha256": event_sha256,
        "scope_sha256": _sha(json.dumps(SCOPE, separators=(",", ":")).encode()),
        "release_authority": False,
        "mutation_authority": False,
    }
    if readiness_release is not None:
        authorization["readiness_release"] = validate_readiness_release_binding(
            readiness_release,
        )
    intent = {
        "schema": INTENT_SCHEMA,
        "intent_id": _sha((str(uuid.uuid4()) + str(current)).encode()),
        "kind": "control_plane_probe",
        "tenant_commitment": _sha(b"owner_cloud_account"),
        "account_scope": "owner",
        "created_at_ms": current,
        "expires_at_ms": current + 60_000,
        "authorization": authorization,
        "requested_controls": dict(SAFE_CONTROLS),
        "market_evidence_sha256": _sha(b"all-four-production-auth-read-probe:no-mutation"),
        "runtime_measurement_sha256": probe_runtime_measurement_sha256(revision),
        "source_revision": revision,
        "order": None,
        "dry_run": True,
    }
    return validate_intent(intent, now_ms=current, max_order_usd=5, live_release=False)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--event-sha256", required=True)
    parser.add_argument("--lease-expires-at-ms", required=True, type=int)
    parser.add_argument("--revision", required=True)
    args = parser.parse_args()
    probe = build_probe(
        event_sha256=args.event_sha256,
        lease_expires_at_ms=args.lease_expires_at_ms,
        revision=args.revision,
    )
    print(canonical_bytes(probe).decode("ascii"))


if __name__ == "__main__":
    main()

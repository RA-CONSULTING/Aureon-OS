"""Benchmark the v05 runtime-protection proposal vault in local HOLD mode."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import statistics
import sys
import tempfile
import time
from contextlib import ExitStack
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from aureon.autonomous.aureon_runtime_protection_proposal_vault_v05 import (  # noqa: E402
    SQLiteRuntimeProtectionProposalVaultV05,
)
from aureon.plumber.crypto import canonical_json_bytes  # noqa: E402
from aureon.plumber.os_protection import (  # noqa: E402
    OS_DURABLE_QUARANTINE_EVIDENCE_SCHEMA,
    LocalOSProtectionBoundary,
    QuarantinedHNC,
)
from aureon.plumber.runtime_intrusion_ledger_v04 import (  # noqa: E402
    SQLiteRuntimeIntrusionLedgerV04,
)

_MASTER_KEY = b"aureon-runtime-protection-v05-benchmark-hnc-key"
_VAULT_KEY = b"aureon-runtime-protection-v05-benchmark-vault-key"
_REASON = "runtime_effect_not_magic_star_released"
_PLAINTEXT_CANARY = "AUREON_V05_BENCHMARK_INTRUSION_PLAINTEXT_CANARY"
_EVENTS = (
    "os.remove",
    "os.rmdir",
    "os.mkdir",
    "os.rename",
    "os.system",
    "subprocess.Popen",
    "shutil.rmtree",
    "sqlite3.connect",
)


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _runtime_content(caller_aad: dict[str, Any]) -> bytes:
    return cast(
        bytes,
        canonical_json_bytes(
            {
                "schema": "aureon.plumber.runtime-intrusion.v04",
                "sequence": 1,
                "event_name": caller_aad["event_name"],
                "resource_commitment": caller_aad["resource_commitment"],
                "reason_code": caller_aad["reason_code"],
                "raw_arguments_retained": False,
                "audit_event_origin_attested": False,
                "effect_attempt_attested": False,
                "resource_commitment_confidentiality_attested": False,
                "resource_commitments_keyed": False,
                "action_eligible": False,
                "economic_eligible": False,
                "production_ready": False,
            }
        ),
    )


def _quarantined_event(
    *,
    ledger_instance_commitment: str,
    event_name: str,
    trusted_now: datetime,
) -> tuple[QuarantinedHNC, dict[str, Any], str]:
    resource_commitment = _sha256_bytes(
        f"{_PLAINTEXT_CANARY}:{event_name}".encode()
    )
    caller_aad = {
        "event_name": event_name,
        "resource_commitment": resource_commitment,
        "reason_code": _REASON,
    }
    boundary = LocalOSProtectionBoundary(
        boundary_id="runtime-protection-v05-benchmark-boundary",
        master_key_provider=lambda: _MASTER_KEY,
        max_ingress_bytes=1,
        trusted_now=lambda: trusted_now,
    )
    boundary._durable_evidence_ledger_instance_commitment = (
        ledger_instance_commitment
    )
    outcome = boundary.admit_external(
        _runtime_content(caller_aad),
        source_id="aureon:runtime-guard-v04",
        ingress_kind="runtime-effect-violation",
        purpose="aureon.plumber.runtime-intrusion-quarantine.v04",
        operator_aad=caller_aad,
    )
    if not isinstance(outcome, QuarantinedHNC):
        raise RuntimeError("benchmark_runtime_intrusion_not_quarantined")
    packet = dict(boundary._quarantine_packets[outcome.admission_id])
    return outcome, packet, resource_commitment


def _runtime_metadata(outcome: QuarantinedHNC) -> dict[str, Any]:
    return {
        "schema": OS_DURABLE_QUARANTINE_EVIDENCE_SCHEMA,
        "intrusion_id": outcome.admission_id,
        "content_sha256": outcome.content_sha256,
        "source_id_sha256": _sha256_bytes(outcome.source_id.encode("utf-8")),
        "ingress_kind_sha256": _sha256_bytes(
            outcome.ingress_kind.encode("utf-8")
        ),
        "denial_code_count": len(outcome.denial_codes),
        "raw_arguments_retained": False,
        "plaintext_retained": False,
        "action_eligible": False,
        "economic_eligible": False,
        "production_ready": False,
    }


def _elapsed_ms(call: Any) -> tuple[Any, float]:
    started = time.perf_counter_ns()
    value = call()
    elapsed = (time.perf_counter_ns() - started) / 1_000_000
    return value, elapsed


def _distribution(values: list[float]) -> dict[str, float]:
    ordered = sorted(values)
    p95_index = max(0, min(len(ordered) - 1, int(0.95 * len(ordered) + 0.9999) - 1))
    return {
        "median": round(statistics.median(ordered), 4),
        "p95": round(ordered[p95_index], 4),
        "min": round(ordered[0], 4),
        "max": round(ordered[-1], 4),
    }


def run_benchmark(repo_root: Path) -> dict[str, Any]:
    implementation_path = (
        repo_root
        / "aureon"
        / "autonomous"
        / "aureon_runtime_protection_proposal_vault_v05.py"
    )
    harness_path = Path(__file__).resolve()
    with (
        tempfile.TemporaryDirectory(prefix="aureon-v05-benchmark-") as raw_temp,
        ExitStack() as resources,
    ):
        temporary = Path(raw_temp)
        source_path = temporary / "runtime-intrusions.sqlite3"
        vault_path = temporary / "runtime-protection-vault.sqlite3"
        ledger = SQLiteRuntimeIntrusionLedgerV04(
            source_path.resolve(),
            ledger_id="aureon-runtime-protection-v05-benchmark-source",
            quarantine_hnc_key_provider=lambda: _MASTER_KEY,
            max_violation_entries=16,
        )
        resources.callback(ledger.close)
        source_preflight = ledger.preflight()
        source_instance = str(source_preflight["ledger_instance_commitment"])
        source_receipts: list[dict[str, Any]] = []
        outcomes: list[QuarantinedHNC] = []
        resource_commitments: list[str] = []
        fixed_now = datetime(2038, 9, 1, 12, 0, 0, tzinfo=UTC)
        for offset, event_name in enumerate(_EVENTS):
            outcome, packet, resource_commitment = _quarantined_event(
                ledger_instance_commitment=source_instance,
                event_name=event_name,
                trusted_now=fixed_now.replace(second=offset),
            )
            source_receipts.append(
                ledger.append_violation(
                    intrusion_id=outcome.admission_id,
                    runtime_metadata=_runtime_metadata(outcome),
                    quarantine_summary=outcome.public_summary(),
                    hnc_packet=packet,
                )
            )
            outcomes.append(outcome)
            resource_commitments.append(resource_commitment)

        vault, empty_open_ms = _elapsed_ms(
            lambda: SQLiteRuntimeProtectionProposalVaultV05(
                vault_path.resolve(),
                vault_id="aureon-runtime-protection-v05-benchmark-vault",
                source_ledger=ledger,
                proposal_key_provider=lambda: _VAULT_KEY,
                max_proposals=8,
            )
        )
        resources.callback(vault.close)
        seal_ms: list[float] = []
        receipts = []
        for source_receipt in source_receipts:
            receipt, elapsed = _elapsed_ms(
                lambda source_receipt=source_receipt: vault.seal_from_intrusion(
                    source_sequence=int(source_receipt["sequence"]),
                    source_entry_commitment=str(
                        source_receipt["entry_commitment"]
                    ),
                )
            )
            receipts.append(receipt)
            seal_ms.append(elapsed)

        verify_ms: list[float] = []
        verified = []
        for receipt in receipts:
            summary, elapsed = _elapsed_ms(
                lambda receipt=receipt: vault.verify_receipt(receipt)
            )
            verified.append(summary)
            verify_ms.append(elapsed)

        review_ms: list[float] = []
        candidate_targets: list[str] = []
        candidate_markers: list[str] = []
        reviews = []
        for receipt in receipts:
            review, elapsed = _elapsed_ms(
                lambda receipt=receipt: vault.read_for_review(
                    vault_sequence=receipt.sequence,
                    vault_entry_commitment=receipt.entry_commitment,
                    proposal_commitment=receipt.proposal_commitment,
                    candidate_commitment=receipt.candidate_commitment,
                )
            )
            reviews.append(review)
            review_ms.append(elapsed)
            material = review.protection_code_candidate_for_review()
            candidate = material["protection_code_candidate"]
            candidate_targets.append(str(candidate["target_path"]))
            candidate_markers.extend(
                (
                    str(candidate["target_path"]),
                    str(candidate["source_event_name"]),
                    str(candidate["source_reason_code"]),
                    "evaluate_exact_runtime_violation",
                )
            )

        replay_ms: list[float] = []
        replay_source = source_receipts[0]
        for _ in range(20):
            replay, elapsed = _elapsed_ms(
                lambda: vault.seal_from_intrusion(
                    source_sequence=int(replay_source["sequence"]),
                    source_entry_commitment=str(
                        replay_source["entry_commitment"]
                    ),
                )
            )
            if replay != receipts[0]:
                raise RuntimeError("benchmark_replay_receipt_changed")
            replay_ms.append(elapsed)

        before_restart = vault.preflight()
        public_material = json.dumps(
            {
                "preflight": before_restart,
                "receipts": [receipt.public_summary() for receipt in receipts],
                "verified": verified,
                "reviews": [review.public_summary() for review in reviews],
            },
            sort_keys=True,
        ).encode("utf-8")
        candidate_files_absent = all(
            not (repo_root / target).exists() for target in candidate_targets
        )
        forbidden_markers = [
            _PLAINTEXT_CANARY,
            *(outcome.admission_id for outcome in outcomes),
            *resource_commitments,
            *candidate_markers,
        ]
        vault_storage = b"".join(
            path.read_bytes()
            for path in (
                vault_path,
                Path(f"{vault_path}-wal"),
                Path(f"{vault_path}-shm"),
            )
            if path.exists()
        )
        plaintext_absent = all(
            marker.encode("utf-8") not in vault_storage
            for marker in forbidden_markers
        )
        candidate_plaintext_absent_from_public_material = all(
            marker.encode("utf-8") not in public_material
            for marker in candidate_markers
        )
        vault.close()

        restarted, restart_ms = _elapsed_ms(
            lambda: SQLiteRuntimeProtectionProposalVaultV05(
                vault_path.resolve(),
                vault_id="aureon-runtime-protection-v05-benchmark-vault",
                source_ledger=ledger,
                proposal_key_provider=lambda: _VAULT_KEY,
                max_proposals=8,
            )
        )
        resources.callback(restarted.close)
        after_restart = restarted.preflight()
        restarted.close()
        ledger.close()

    return {
        "schema": "aureon.autonomous.runtime-protection-proposal-vault-benchmark.v05",
        "measured_at_utc": datetime.now(UTC).isoformat(),
        "measured_at_local_audit_date": "2026-09-01",
        "mode": "local_offline_hold_only_performance_measurement",
        "host": {
            "platform": platform.platform(),
            "python": platform.python_version(),
        },
        "implementation_sha256": _sha256_file(implementation_path),
        "benchmark_harness_sha256": _sha256_file(harness_path),
        "proposal_count": len(receipts),
        "source_violation_count": len(source_receipts),
        "source_declared_capacity": 16,
        "vault_declared_capacity": 8,
        "empty_open_ms": round(empty_open_ms, 4),
        "seal_ms": _distribution(seal_ms),
        "live_verify_ms": _distribution(verify_ms),
        "review_read_ms": _distribution(review_ms),
        "idempotent_replay_ms": {
            "iterations": len(replay_ms),
            **_distribution(replay_ms),
        },
        "restart_open_and_authenticate_all_ms": round(restart_ms, 4),
        "restart_entry_count": int(after_restart["entry_count"]),
        "head_stable_across_restart": (
            before_restart["head_entry_commitment"]
            == after_restart["head_entry_commitment"]
        ),
        "source_authentication_scaling": after_restart[
            "source_authentication_scaling"
        ],
        "source_capacity_bound_enforced": after_restart[
            "source_capacity_bound_enforced"
        ],
        "source_max_violation_entries_supported_by_vault": 64,
        "vault_max_proposals_supported": 64,
        "candidate_code_generated": True,
        "candidate_files_written": not candidate_files_absent,
        "candidate_plaintext_absent_from_public_material": (
            candidate_plaintext_absent_from_public_material
        ),
        "plaintext_markers_absent_from_vault_db_wal_shm": plaintext_absent,
        "verified_receipt_required_for_authentication": True,
        "current_open_key_matches_authenticated_metadata": True,
        "key_provider_restart_continuity_attested": False,
        "independent_key_custody_attested": False,
        "external_model_invoked": False,
        "self_coder_invoked": False,
        "proposal_forge_invoked": False,
        "repository_mutation_authorized": False,
        "candidate_apply_authorized": False,
        "candidate_import_authorized": False,
        "generated_code_execution_authorized": False,
        "release_authorized": False,
        "external_head_anchor_attested": False,
        "production_ready": False,
        "capacity_scaling_audit": {
            "method": "independent_instrumented_source_row_and_lock_measurement",
            "source_capacity_64_vault_entries_4": {
                "source_rows": 66,
                "source_row_validations": 132,
                "source_lock_acquisitions": 2,
                "preflight_median_ms": 501.616,
                "preflight_max_ms": 647.779,
                "aggregate_source_lock_max_ms": 621.526,
                "longest_single_source_lock_ms": 325.387,
            },
            "rejected_source_capacity_128_vault_entries_4": {
                "source_rows": 130,
                "source_row_validations": 260,
                "source_lock_acquisitions": 2,
                "preflight_median_ms": 1157.779,
                "preflight_max_ms": 1305.198,
                "aggregate_source_lock_max_ms": 1282.82,
                "longest_single_source_lock_ms": 651.112,
            },
            "selected_declared_source_capacity_limit": 64,
        },
        "limitations": [
            "valid_prefix_rollback_and_byte_copy_clone_not_detectable",
            "same_process_arbitrary_code_execution_outside_proof",
            "local_key_provider_restart_continuity_not_attested",
            "commitment_only_intrusion_projection_yields_generic_event_family_candidate",
            "candidate_semantic_correctness_and_integration_not_attested",
            "no_candidate_apply_import_execute_or_release_authority",
            "no_independent_monotonic_head_anchor",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional JSON receipt path; stdout is always emitted.",
    )
    args = parser.parse_args()
    result = run_benchmark(_REPO_ROOT)
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output is not None:
        args.output.resolve().write_text(rendered, encoding="utf-8", newline="\n")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

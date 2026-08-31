#!/usr/bin/env python3
"""Offline HNC crypto and OS-admission microbenchmark.

This benchmark measures local performance and verifies one ciphertext-tamper
negative control.  It performs no network, provider, repository, or generated
code action, and its timings are not a security proof or production claim.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from aureon.harmonic.hnc_quantum_packet_crypto import (
    HNCPacketError,
    build_hnc_quantum_packet,
    decode_hnc_quantum_packet,
    validate_hnc_packet_contract,
)
from aureon.plumber.os_protection import AdmittedHNC, LocalOSProtectionBoundary

PURPOSE = "aureon.benchmark.hnc-crypto-boundary.v1"
MASTER_KEY = hashlib.sha256(b"aureon-offline-hnc-benchmark-key-v1").digest()
NOW = datetime(2032, 1, 2, 3, 4, 5, tzinfo=UTC)


def _percentile(samples: list[float], fraction: float) -> float:
    ordered = sorted(samples)
    index = min(len(ordered) - 1, int(len(ordered) * fraction))
    return ordered[index]


def _metric(samples: list[float], *, payload_bytes: int) -> dict[str, Any]:
    total = sum(samples)
    return {
        "iterations": len(samples),
        "payload_bytes": payload_bytes,
        "mean_ms": statistics.mean(samples) * 1000,
        "p50_ms": _percentile(samples, 0.50) * 1000,
        "p95_ms": _percentile(samples, 0.95) * 1000,
        "p99_ms": _percentile(samples, 0.99) * 1000,
        "operations_per_second": len(samples) / total,
        "payload_mib_per_second": (len(samples) * payload_bytes / (1024 * 1024)) / total,
    }


def _tamper_ciphertext(packet: dict[str, Any]) -> dict[str, Any]:
    tampered = {**packet}
    ciphertext = str(tampered["ciphertext_b64"])
    replacement = "A" if ciphertext[0] != "A" else "B"
    tampered["ciphertext_b64"] = replacement + ciphertext[1:]
    return tampered


def benchmark_crypto(payload_bytes: int, iterations: int) -> dict[str, Any]:
    payload = hashlib.shake_256(f"payload:{payload_bytes}".encode()).digest(payload_bytes)
    build_samples: list[float] = []
    decode_samples: list[float] = []
    latest: dict[str, Any] | None = None
    for index in range(iterations):
        started = time.perf_counter()
        packet = build_hnc_quantum_packet(
            payload,
            MASTER_KEY,
            purpose=PURPOSE,
            operator_aad={"benchmark_iteration": index, "payload_bytes": payload_bytes},
        )
        build_samples.append(time.perf_counter() - started)
        if validate_hnc_packet_contract(packet).get("valid") is not True:
            raise RuntimeError("hnc_packet_contract_failed")
        started = time.perf_counter()
        decoded = decode_hnc_quantum_packet(
            packet,
            MASTER_KEY,
            expected_purpose=PURPOSE,
        )
        decode_samples.append(time.perf_counter() - started)
        if decoded.plaintext != payload:
            raise RuntimeError("hnc_round_trip_mismatch")
        latest = packet
    assert latest is not None
    tamper_rejected = False
    try:
        decode_hnc_quantum_packet(
            _tamper_ciphertext(latest),
            MASTER_KEY,
            expected_purpose=PURPOSE,
        )
    except HNCPacketError:
        tamper_rejected = True
    return {
        "build": _metric(build_samples, payload_bytes=payload_bytes),
        "decode": _metric(decode_samples, payload_bytes=payload_bytes),
        "round_trip_exact": True,
        "ciphertext_tamper_rejected": tamper_rejected,
    }


def benchmark_os_admission(payload_bytes: int, iterations: int) -> dict[str, Any]:
    payload = hashlib.shake_256(b"os-admission-payload").digest(payload_bytes)
    boundary = LocalOSProtectionBoundary(
        boundary_id="offline-hnc-benchmark",
        master_key_provider=lambda: MASTER_KEY,
        max_ingress_bytes=max(payload_bytes, 1),
        max_active_handles=1,
        max_active_ingress_bytes=max(payload_bytes, 1),
        max_replay_tokens=max(iterations, 1),
        max_quarantine_evidence=1,
        trusted_now=lambda: NOW,
    )
    samples: list[float] = []
    for index in range(iterations):
        started = time.perf_counter()
        outcome = boundary.admit_external(
            payload,
            source_id=f"benchmark-iteration-{index}",
            ingress_kind="application/octet-stream",
            purpose=PURPOSE,
            operator_aad={"benchmark_iteration": index},
        )
        if not isinstance(outcome, AdmittedHNC):
            raise RuntimeError("os_admission_unexpected_quarantine")
        boundary.discard_admitted(
            outcome.handle,
            reason_code="benchmark_no_release",
        )
        samples.append(time.perf_counter() - started)
    summary = boundary.public_summary()
    if summary["active_opaque_handle_count"] != 0 or summary["active_ingress_bytes"] != 0:
        raise RuntimeError("os_admission_retention_leak")
    return {
        "admit_and_burn": _metric(samples, payload_bytes=payload_bytes),
        "active_handles_after_run": summary["active_opaque_handle_count"],
        "active_ingress_bytes_after_run": summary["active_ingress_bytes"],
        "production_ready": summary["production_ready"],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--quick", action="store_true", help="Use short CI-friendly iteration counts.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    cases = ((1024, 20), (64 * 1024, 10), (1024 * 1024, 3)) if args.quick else (
        (1024, 200),
        (64 * 1024, 100),
        (1024 * 1024, 20),
    )
    crypto = {
        str(payload_bytes): benchmark_crypto(payload_bytes, iterations)
        for payload_bytes, iterations in cases
    }
    admission_iterations = 20 if args.quick else 200
    admission = benchmark_os_admission(4096, admission_iterations)
    passed = all(item["ciphertext_tamper_rejected"] for item in crypto.values())
    report = {
        "schema": "aureon.hnc-crypto-boundary-benchmark.v1",
        "offline": True,
        "performance_only_not_security_proof": True,
        "production_claim": False,
        "crypto": crypto,
        "os_admission": admission,
        "negative_controls_passed": passed,
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())

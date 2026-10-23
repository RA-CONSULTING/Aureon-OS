"""Adversarial checks for the local v0.4 Python runtime audit guard."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import textwrap
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from aureon.plumber.crypto import canonical_json_bytes
from aureon.plumber.os_protection import LocalOSProtectionBoundary
from aureon.plumber.runtime_guard_v04 import (
    AuditEffectRuleV04,
    GuardedRuntimeCapabilityV04,
    HNCRuntimeViolationRecorderV04,
    RuntimeEffectManifestV04,
    RuntimeGuardError,
    audit_event_resource_commitment_v04,
    decode_runtime_effect_manifest_v04,
)


def oid(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def test_runtime_effect_manifest_is_exact_canonical_and_bounded() -> None:
    open_write_commitment = audit_event_resource_commitment_v04(
        "open",
        (str(Path("one.txt").resolve()), "w", 0),
    )
    first = AuditEffectRuleV04(
        event_name="os.mkdir",
        resource_commitment=audit_event_resource_commitment_v04(
            "os.mkdir",
            (str(Path("one-dir").resolve()), 511, -1),
        ),
        max_uses=1,
    )
    second = AuditEffectRuleV04(
        event_name="os.mkdir",
        resource_commitment=audit_event_resource_commitment_v04(
            "os.mkdir",
            (str(Path("two-dir").resolve()), 511, -1),
        ),
        max_uses=1,
    )
    manifest = RuntimeEffectManifestV04(
        effect_id=oid("effect"),
        capability_id=oid("capability"),
        runtime_measurement_sha256=oid("runtime"),
        operations=tuple(
            sorted(
                (first, second),
                key=lambda item: (item.event_name, item.resource_commitment),
            )
        ),
    )
    encoded = canonical_json_bytes(manifest.wire_dict())
    assert decode_runtime_effect_manifest_v04(encoded) == manifest
    assert len(manifest.commitment) == 64
    assert open_write_commitment != audit_event_resource_commitment_v04(
        "open",
        (str(Path("one.txt").resolve()), "a", 0),
    )
    with pytest.raises(RuntimeGuardError, match="target_not_absolute_text"):
        audit_event_resource_commitment_v04("open", ("relative.txt", "w", 0))
    assert open_write_commitment != audit_event_resource_commitment_v04(
        "open",
        (str(Path("one.txt").resolve()), "x", 0),
    )

    extra = {**manifest.wire_dict(), "caller_claimed_safe": True}
    with pytest.raises(RuntimeGuardError, match="manifest_shape_invalid"):
        decode_runtime_effect_manifest_v04(canonical_json_bytes(extra))
    with pytest.raises(RuntimeGuardError, match="operations_not_canonical"):
        RuntimeEffectManifestV04(
            effect_id=manifest.effect_id,
            capability_id=manifest.capability_id,
            runtime_measurement_sha256=manifest.runtime_measurement_sha256,
            operations=tuple(reversed(manifest.operations)),
        )
    with pytest.raises(RuntimeGuardError, match="event_not_authorizable"):
        AuditEffectRuleV04(
            event_name="sys.addaudithook",
            resource_commitment=oid("never-authorize-hook-install"),
            max_uses=1,
        )
    for event_name in (
        "_thread.start_new_thread",
        "ctypes.dlopen",
        "open",
        "os.rename",
        "os.startfile/2",
        "socket.connect",
        "subprocess.Popen",
        "winreg.LoadKey",
    ):
        with pytest.raises(RuntimeGuardError, match="event_not_authorizable"):
            AuditEffectRuleV04(
                event_name=event_name,
                resource_commitment=oid("never-authorize:" + event_name),
                max_uses=1,
            )
    with pytest.raises(RuntimeGuardError, match="audit_mkdir_arguments_invalid"):
        audit_event_resource_commitment_v04(
            "os.mkdir",
            (str(Path("one-dir").resolve()), 511, 7),
        )
    with pytest.raises(RuntimeGuardError, match="audit_argument_type_unsupported"):
        audit_event_resource_commitment_v04(
            "os.rename",
            (memoryview(bytearray(64 * 1024 + 1)), "target", -1, -1),
        )
    with pytest.raises(RuntimeGuardError, match="audit_argument_text_invalid"):
        audit_event_resource_commitment_v04(
            "os.rename",
            ("x" * (64 * 1024 + 1), "target", -1, -1),
        )
    with pytest.raises(RuntimeGuardError, match="audit_argument_budget_exceeded"):
        audit_event_resource_commitment_v04(
            "os.rename",
            tuple("x" * (64 * 1024) for _ in range(5)),
        )


def test_runtime_guard_requires_exact_boundary_recorder_and_capabilities() -> None:
    boundary = LocalOSProtectionBoundary(
        boundary_id="runtime-guard-test",
        master_key_provider=lambda: b"runtime-guard-test-key-material-32",
    )
    recorder = HNCRuntimeViolationRecorderV04(boundary=boundary)
    assert recorder.preflight()["ready"] is True
    assert recorder.receipts() == ()
    returned_receipt = recorder.record(
        event_name="os.remove",
        resource_commitment=oid("resource"),
        reason_code="test_denial",
    )
    returned_receipt["hnc_evidence_binding"]["tampered"] = True
    assert "tampered" not in recorder.receipts()[0]["hnc_evidence_binding"]
    copied_receipt = recorder.receipts()[0]
    copied_receipt["hnc_evidence_binding"]["tampered_copy"] = True
    assert "tampered_copy" not in recorder.receipts()[0]["hnc_evidence_binding"]
    capability = GuardedRuntimeCapabilityV04(
        capability_id=oid("capability"),
        capability_measurement_sha256=oid("measurement"),
        handler=lambda: None,
    )
    assert capability.capability_id == oid("capability")

    class BoundaryLookalike:
        def key_preflight(self):  # noqa: ANN201
            return {"ready": True}

    with pytest.raises(RuntimeGuardError, match="exact_local_os_protection"):
        HNCRuntimeViolationRecorderV04(
            boundary=BoundaryLookalike(),  # type: ignore[arg-type]
        )


def test_runtime_violation_recorder_capacity_is_atomic_under_concurrency() -> None:
    recorder = HNCRuntimeViolationRecorderV04(
        boundary=LocalOSProtectionBoundary(
            boundary_id="runtime-guard-capacity-test",
            master_key_provider=lambda: b"runtime-guard-capacity-key-material-32",
        ),
        max_receipts=2,
    )
    assert recorder.preflight()["ready"] is True

    def attempt(index: int) -> str:
        try:
            recorder.record(
                event_name="os.remove",
                resource_commitment=oid(f"resource:{index}"),
                reason_code="concurrent_test_denial",
            )
        except RuntimeGuardError as exc:
            return exc.code
        return "recorded"

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(attempt, range(8)))

    assert results.count("recorded") == 2
    assert results.count("runtime_violation_capacity_exhausted") == 6
    receipts = recorder.receipts()
    assert len(receipts) == 2
    assert [item["sequence"] for item in receipts] == [1, 2]
    assert recorder.terminal_failure_code() == "runtime_violation_capacity_exhausted"
    exhausted = recorder.preflight()
    assert exhausted["ready"] is False
    assert exhausted["reason_code"] == "runtime_violation_capacity_exhausted"


def test_runtime_recorder_preflight_does_not_spend_last_hnc_capacity() -> None:
    boundary = LocalOSProtectionBoundary(
        boundary_id="runtime-guard-insufficient-capacity",
        master_key_provider=lambda: b"runtime-guard-capacity-hold-key-32",
        max_quarantine_evidence=1,
    )
    recorder = HNCRuntimeViolationRecorderV04(
        boundary=boundary,
        max_receipts=1,
    )
    preflight = recorder.preflight()
    assert preflight["ready"] is False
    assert preflight["reason_code"] == "runtime_hnc_quarantine_capacity_insufficient"
    assert preflight["hnc_quarantine_capacity_backed"] is False
    assert boundary.public_summary()["quarantine_evidence_count"] == 0

    exact_capacity_boundary = LocalOSProtectionBoundary(
        boundary_id="runtime-guard-exact-capacity",
        master_key_provider=lambda: b"runtime-guard-exact-capacity-key-32",
        max_quarantine_evidence=3,
    )
    exact_capacity_recorder = HNCRuntimeViolationRecorderV04(
        boundary=exact_capacity_boundary,
        max_receipts=2,
    )
    exact_preflight = exact_capacity_recorder.preflight()
    assert exact_preflight["ready"] is True
    assert exact_preflight["hnc_quarantine_capacity_after_probe"] == 2
    for index in range(2):
        exact_capacity_recorder.record(
            event_name="os.remove",
            resource_commitment=oid(f"exact-capacity:{index}"),
            reason_code="capacity_test_denial",
        )
    assert len(exact_capacity_recorder.receipts()) == 2


def test_runtime_guard_installation_veto_is_terminal_for_the_process() -> None:
    child = textwrap.dedent(
        r"""
        import hashlib
        import json
        import sys

        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

        from aureon.plumber.crypto import ed25519_public_key_hex
        from aureon.plumber.os_protection import LocalOSProtectionBoundary
        from aureon.plumber.production_release_broker_v03 import (
            AuthorityBindingV03,
            ProductionReleaseVerifierV03,
        )
        from aureon.plumber.runtime_guard_v04 import (
            GuardedRuntimeCapabilityV04,
            HNCRuntimeViolationRecorderV04,
            RuntimeAuditGuardV04,
            RuntimeGuardError,
        )

        def oid(label):
            return hashlib.sha256(label.encode("utf-8")).hexdigest()

        def binding(role, authority, key_id, key):
            return AuthorityBindingV03(
                role=role,
                authority_id=authority,
                key_id=key_id,
                public_key_hex=ed25519_public_key_hex(key),
            )

        review_key = Ed25519PrivateKey.generate()
        dispatch_key = Ed25519PrivateKey.generate()
        executor_key = Ed25519PrivateKey.generate()
        receipt_key = Ed25519PrivateKey.generate()
        verifier = ProductionReleaseVerifierV03(
            review_authority=binding(
                "REVIEW", "review-authority", "review-key-v1", review_key
            ),
            dispatch_authority=binding(
                "DISPATCH", "dispatch-authority", "dispatch-key-v1", dispatch_key
            ),
            executor_authority=binding(
                "EXECUTOR", "executor-authority", "executor-key-v1", executor_key
            ),
            receipt_authority=binding(
                "RECEIPT", "receipt-authority", "receipt-key-v1", receipt_key
            ),
            trusted_now_ms=lambda: 2000,
        )
        capability_id = oid("installation-veto-capability")
        guard = RuntimeAuditGuardV04(
            verifier=verifier,
            recorder=HNCRuntimeViolationRecorderV04(
                boundary=LocalOSProtectionBoundary(
                    boundary_id="runtime-guard-install-veto",
                    master_key_provider=lambda: b"runtime-guard-veto-key-material-32",
                )
            ),
            runtime_measurement_sha256=oid("runtime"),
            capabilities={
                capability_id: GuardedRuntimeCapabilityV04(
                    capability_id=capability_id,
                    capability_measurement_sha256=oid("capability-measurement"),
                    handler=lambda: None,
                )
            },
        )

        def veto_private_probe(event, _arguments):
            if event == "aureon.runtime_guard_v04.install_probe":
                raise RuntimeError("veto")

        sys.addaudithook(veto_private_probe)
        errors = []
        for _attempt in range(2):
            try:
                guard.install()
            except RuntimeGuardError as exc:
                errors.append(exc.code)
            else:
                raise AssertionError("vetoed guard installation was claimed")
        print(json.dumps({"errors": errors, "summary": guard.public_summary()}))
        """
    )
    environment = os.environ.copy()
    environment.update(
        {
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONHASHSEED": "0",
            "PYTHONNOUSERSITE": "1",
        }
    )
    completed = subprocess.run(
        [sys.executable, "-B", "-c", child],
        cwd=Path(__file__).resolve().parents[2],
        env=environment,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    report = json.loads(completed.stdout)
    assert report["errors"] == [
        "runtime_audit_guard_installation_unproven",
        "runtime_audit_guard_installation_terminal",
    ]
    assert report["summary"]["installed"] is False
    assert report["summary"]["installation_failed_terminal"] is True


def test_installed_guard_enforces_signed_exact_effects_and_hnc_quarantine(
    tmp_path: Path,
) -> None:
    child = textwrap.dedent(
        r"""
        import contextvars
        import hashlib
        import json
        import os
        import socket
        import subprocess
        import sys
        import threading
        from pathlib import Path

        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

        from aureon.plumber.crypto import canonical_json_bytes, ed25519_public_key_hex
        from aureon.plumber.os_protection import LocalOSProtectionBoundary
        from aureon.plumber.production_release_broker_v03 import (
            AuthorityBindingV03,
            ProductionReleaseVerifierV03,
            ReleaseCommandV03,
            decode_release_command_v03,
            decode_review_authorization_v03,
            sign_dispatch_claim_v03,
            sign_review_authorization_v03,
        )
        from aureon.plumber.runtime_guard_v04 import (
            AuditEffectRuleV04,
            GuardedRuntimeCapabilityV04,
            HNCRuntimeViolationRecorderV04,
            RuntimeAuditGuardV04,
            RuntimeEffectManifestV04,
            RuntimeGuardError,
            RuntimeGuardViolation,
            audit_event_resource_commitment_v04,
        )

        def oid(label):
            return hashlib.sha256(label.encode("utf-8")).hexdigest()

        root = Path(os.environ["AUREON_RUNTIME_GUARD_TEST_ROOT"]).resolve()
        allowed = (root / "allowed-dir").resolve()
        second_allowed = (root / "second-allowed-dir").resolve()
        escaped_allowed = (root / "escaped-allowed-dir").resolve()
        worker_allowed = (root / "worker-allowed-dir").resolve()
        serialized_allowed = (root / "serialized-allowed-dir").resolve()
        secondary_allowed = (root / "secondary-allowed-dir").resolve()
        lying_allowed = (root / "lying-allowed-dir").resolve()
        lying_actual_path = (root / "lying-actual-dir").resolve()
        raw_open = (root / "raw-open.txt").resolve()
        preopened = (root / "preopened-hold.txt").resolve()
        read_source = (root / "read-source.txt").resolve()
        synthetic_allowed = (root / "synthetic-allowed-dir").resolve()
        denied = (root / "NEVER_STORE_THIS_PATH_CANARY.txt").resolve()
        preopened_stream = preopened.open("w", encoding="utf-8")
        read_source.write_text("read-before-install-only", encoding="utf-8")
        worker_trigger = threading.Event()
        worker_done = threading.Event()
        worker_stop = threading.Event()
        worker_job = {"kind": "violate", "material": None}
        worker_results = []

        def preexisting_worker_loop():
            while True:
                worker_trigger.wait()
                worker_trigger.clear()
                if worker_stop.is_set():
                    worker_done.set()
                    return
                if worker_job["kind"] == "violate":
                    try:
                        denied.write_text(
                            "NEVER_STORE_THIS_WORKER_CANARY",
                            encoding="utf-8",
                        )
                    except RuntimeGuardViolation as exc:
                        worker_results.append({"violation": exc.code})
                    else:
                        worker_results.append({"violation": "not-blocked"})
                elif worker_job["kind"] == "execute":
                    active_count = guard.public_summary()["active_execution_count"]
                    try:
                        guard.execute_released(*worker_job["material"])
                    except RuntimeGuardError as exc:
                        worker_results.append(
                            {"concurrent": exc.code, "active_count": active_count}
                        )
                    else:
                        worker_results.append(
                            {"concurrent": "not-blocked", "active_count": active_count}
                        )
                worker_done.set()

        preexisting_worker = threading.Thread(
            target=preexisting_worker_loop,
            name="runtime-guard-preexisting-worker",
            daemon=True,
        )
        preexisting_worker.start()
        clock = {"now": 2000}

        review_key = Ed25519PrivateKey.generate()
        dispatch_key = Ed25519PrivateKey.generate()
        executor_key = Ed25519PrivateKey.generate()
        receipt_key = Ed25519PrivateKey.generate()

        def binding(role, authority, key_id, key):
            return AuthorityBindingV03(
                role=role,
                authority_id=authority,
                key_id=key_id,
                public_key_hex=ed25519_public_key_hex(key),
            )

        review_binding = binding("REVIEW", "review-authority", "review-key-v1", review_key)
        dispatch_binding = binding("DISPATCH", "dispatch-authority", "dispatch-key-v1", dispatch_key)
        executor_binding = binding("EXECUTOR", "executor-authority", "executor-key-v1", executor_key)
        receipt_binding = binding("RECEIPT", "receipt-authority", "receipt-key-v1", receipt_key)
        verifier = ProductionReleaseVerifierV03(
            review_authority=review_binding,
            dispatch_authority=dispatch_binding,
            executor_authority=executor_binding,
            receipt_authority=receipt_binding,
            trusted_now_ms=lambda: clock["now"],
        )

        runtime_measurement = oid("guarded-runtime")
        capability_measurement = oid("write-capability")
        write_capability_id = oid("write-capability-id")
        catching_capability_id = oid("catching-capability-id")
        escaping_capability_id = oid("escaping-capability-id")
        append_mismatch_capability_id = oid("append-mismatch-capability-id")
        worker_capability_id = oid("worker-capability-id")
        serialized_capability_id = oid("serialized-capability-id")
        secondary_capability_id = oid("secondary-capability-id")
        lying_path_capability_id = oid("lying-path-capability-id")
        synthetic_event_capability_id = oid("synthetic-event-capability-id")
        escaped_context = None

        class LyingPath(str):
            def encode(self, *args, **kwargs):
                return str(lying_allowed).encode(*args, **kwargs)

        lying_actual = LyingPath(str(lying_actual_path))

        def write_allowed():
            allowed.mkdir()

        def catch_violation_then_write():
            try:
                denied.write_text("NEVER_STORE_THIS_VALUE_CANARY", encoding="utf-8")
            except RuntimeGuardViolation:
                pass
            second_allowed.mkdir()

        def capture_context_without_effect():
            global escaped_context
            escaped_context = contextvars.copy_context()

        def append_under_write_only_manifest():
            raw_open.write_text("unexpected-open", encoding="utf-8")

        def caught_worker_violation_then_mkdir():
            worker_job["kind"] = "violate"
            worker_job["material"] = None
            worker_done.clear()
            worker_trigger.set()
            if not worker_done.wait(10):
                raise AssertionError("pre-existing worker did not answer")
            worker_allowed.mkdir()

        def serialize_concurrent_release_then_mkdir():
            worker_job["kind"] = "execute"
            worker_done.clear()
            worker_trigger.set()
            if not worker_done.wait(10):
                raise AssertionError("concurrent release worker did not answer")
            serialized_allowed.mkdir()

        def secondary_mkdir():
            secondary_allowed.mkdir()

        def lying_path_mkdir():
            os.mkdir(lying_actual)

        def synthetic_mkdir_audit_event_only():
            sys.audit("os.mkdir", str(synthetic_allowed), 511, -1)

        recorder = HNCRuntimeViolationRecorderV04(
            boundary=LocalOSProtectionBoundary(
                boundary_id="runtime-guard-child",
                master_key_provider=lambda: b"runtime-guard-child-hnc-key-material",
                max_quarantine_evidence=128,
            ),
            max_receipts=64,
        )
        guard = RuntimeAuditGuardV04(
            verifier=verifier,
            recorder=recorder,
            runtime_measurement_sha256=runtime_measurement,
            capabilities={
                write_capability_id: GuardedRuntimeCapabilityV04(
                    capability_id=write_capability_id,
                    capability_measurement_sha256=capability_measurement,
                    handler=write_allowed,
                ),
                catching_capability_id: GuardedRuntimeCapabilityV04(
                    capability_id=catching_capability_id,
                    capability_measurement_sha256=capability_measurement,
                    handler=catch_violation_then_write,
                ),
                escaping_capability_id: GuardedRuntimeCapabilityV04(
                    capability_id=escaping_capability_id,
                    capability_measurement_sha256=capability_measurement,
                    handler=capture_context_without_effect,
                ),
                append_mismatch_capability_id: GuardedRuntimeCapabilityV04(
                    capability_id=append_mismatch_capability_id,
                    capability_measurement_sha256=capability_measurement,
                    handler=append_under_write_only_manifest,
                ),
                worker_capability_id: GuardedRuntimeCapabilityV04(
                    capability_id=worker_capability_id,
                    capability_measurement_sha256=capability_measurement,
                    handler=caught_worker_violation_then_mkdir,
                ),
                serialized_capability_id: GuardedRuntimeCapabilityV04(
                    capability_id=serialized_capability_id,
                    capability_measurement_sha256=capability_measurement,
                    handler=serialize_concurrent_release_then_mkdir,
                ),
                secondary_capability_id: GuardedRuntimeCapabilityV04(
                    capability_id=secondary_capability_id,
                    capability_measurement_sha256=capability_measurement,
                    handler=secondary_mkdir,
                ),
                lying_path_capability_id: GuardedRuntimeCapabilityV04(
                    capability_id=lying_path_capability_id,
                    capability_measurement_sha256=capability_measurement,
                    handler=lying_path_mkdir,
                ),
                synthetic_event_capability_id: GuardedRuntimeCapabilityV04(
                    capability_id=synthetic_event_capability_id,
                    capability_measurement_sha256=capability_measurement,
                    handler=synthetic_mkdir_audit_event_only,
                ),
            },
        )

        def signed_material(label, capability_id, target):
            rule = AuditEffectRuleV04(
                event_name="os.mkdir",
                resource_commitment=audit_event_resource_commitment_v04(
                    "os.mkdir", (str(target), 511, -1)
                ),
                max_uses=1,
            )
            manifest = RuntimeEffectManifestV04(
                effect_id=oid("effect:" + label),
                capability_id=capability_id,
                runtime_measurement_sha256=runtime_measurement,
                operations=(rule,),
            )
            command = ReleaseCommandV03(
                command_id=oid("command:" + label),
                packet_commitment=oid("packet:" + label),
                admission_commitment=oid("admission:" + label),
                effect_id=manifest.effect_id,
                capability_id=capability_id,
                capability_measurement_sha256=capability_measurement,
                runtime_measurement_sha256=runtime_measurement,
                authorization_context_sha256=manifest.commitment,
                request_nonce=oid("request:" + label),
                issued_at_ms=1000,
                expires_at_ms=10000,
            )
            review = sign_review_authorization_v03(
                review_key,
                review_id=oid("review:" + label),
                command_commitment=command.commitment,
                decision="ALLOW",
                issued_at_ms=1100,
                expires_at_ms=9000,
                authority_id=review_binding.authority_id,
                key_id=review_binding.key_id,
            )
            dispatch = sign_dispatch_claim_v03(
                dispatch_key,
                command_commitment=command.commitment,
                review_commitment=review.commitment,
                effect_id=command.effect_id,
                request_nonce=command.request_nonce,
                dispatch_nonce=oid("dispatch:" + label),
                claimed_at_ms=2000,
                claim_expires_at_ms=3000,
                authority_id=dispatch_binding.authority_id,
                key_id=dispatch_binding.key_id,
            )
            return tuple(
                canonical_json_bytes(item.wire_dict())
                for item in (command, review, dispatch, manifest)
            )

        install = guard.install()
        hold_count = guard.public_summary()["violation_count"]
        preopened_stream.write("preopened-descriptor-hold")
        preopened_stream.flush()
        preopened_stream.close()
        direct_environment_key = "AUREON_RUNTIME_GUARD_DIRECT_DATA_HOLD"
        os.environ._data[direct_environment_key] = "held"
        assert os.getenv(direct_environment_key) == "held"
        del os.environ._data[direct_environment_key]
        assert guard.public_summary()["violation_count"] == hold_count

        try:
            read_source.read_text(encoding="utf-8")
        except RuntimeGuardViolation as exc:
            blocked_codes = [exc.code]
        else:
            raise AssertionError("post-install file read was accepted")

        exact = signed_material("exact", write_capability_id, allowed)
        execution = guard.execute_released(*exact)
        assert allowed.is_dir()
        assert execution["all_manifest_operations_consumed"] is True
        assert execution["external_effect_success_attested"] is False
        assert execution["capability_measurement_attested"] is False
        assert execution["provider_readback_verified"] is False
        assert execution["runtime_measurement_attested"] is False
        assert execution["production_ready"] is False

        synthetic_material = signed_material(
            "synthetic-event",
            synthetic_event_capability_id,
            synthetic_allowed,
        )
        synthetic_execution = guard.execute_released(*synthetic_material)
        assert synthetic_execution["all_manifest_operations_consumed"] is True
        assert synthetic_execution["audit_event_origin_attested"] is False
        assert synthetic_execution["external_effect_success_attested"] is False
        assert not synthetic_allowed.exists()

        append_mismatch = signed_material(
            "append-mismatch",
            append_mismatch_capability_id,
            allowed,
        )
        try:
            guard.execute_released(*append_mismatch)
        except RuntimeGuardViolation as exc:
            blocked_codes.append(exc.code)
        else:
            raise AssertionError("append used a write-only manifest")
        assert not raw_open.exists()

        lying_material = signed_material(
            "lying-path",
            lying_path_capability_id,
            lying_allowed,
        )
        try:
            guard.execute_released(*lying_material)
        except RuntimeGuardViolation as exc:
            blocked_codes.append(exc.code)
        else:
            raise AssertionError("str subclass forged an authorized path")
        assert not lying_actual_path.exists()
        assert not lying_allowed.exists()

        try:
            guard.execute_released(*exact)
        except RuntimeGuardError as exc:
            assert exc.code == "runtime_dispatch_replayed"
        else:
            raise AssertionError("signed dispatch replay was accepted")

        exact_command = decode_release_command_v03(exact[0])
        exact_review = decode_review_authorization_v03(exact[1])
        second_dispatch = sign_dispatch_claim_v03(
            dispatch_key,
            command_commitment=exact_command.commitment,
            review_commitment=exact_review.commitment,
            effect_id=exact_command.effect_id,
            request_nonce=exact_command.request_nonce,
            dispatch_nonce=oid("dispatch:exact:second-valid-signature"),
            claimed_at_ms=2000,
            claim_expires_at_ms=3000,
            authority_id=dispatch_binding.authority_id,
            key_id=dispatch_binding.key_id,
        )
        try:
            guard.execute_released(
                exact[0],
                exact[1],
                canonical_json_bytes(second_dispatch.wire_dict()),
                exact[3],
            )
        except RuntimeGuardError as exc:
            assert exc.code == "runtime_release_identity_replayed"
        else:
            raise AssertionError("same release identity accepted a second dispatch")

        # Retain the append-mode mismatch result and add the default-deny cases.
        for operation in (
            lambda: denied.write_text("NEVER_STORE_THIS_VALUE_CANARY", encoding="utf-8"),
            lambda: os.environ.__setitem__("AUREON_NEVER_STORE_CANARY", "secret"),
            lambda: subprocess.run([sys.executable, "-c", "pass"], check=True),
            lambda: threading.Thread(target=lambda: None).start(),
        ):
            try:
                operation()
            except RuntimeGuardViolation as exc:
                blocked_codes.append(exc.code)
            else:
                raise AssertionError("unreleased runtime effect was accepted")

        try:
            socket.socket()
        except RuntimeGuardViolation as exc:
            blocked_codes.append(exc.code)
        else:
            raise AssertionError("unreleased socket construction was accepted")

        injected_hook_events = []
        sys.addaudithook(
            lambda event, _args: injected_hook_events.append(event)
        )
        # CPython deliberately suppresses an existing hook's exception while
        # vetoing a later hook.  Prove the attempted hook was not installed.
        sys.audit("aureon.runtime_guard_v04.test_after_veto")
        assert injected_hook_events == []

        catching = signed_material(
            "catching",
            catching_capability_id,
            second_allowed,
        )
        try:
            guard.execute_released(*catching)
        except RuntimeGuardViolation as exc:
            assert exc.code == "runtime_active_permit_revoked"
        else:
            raise AssertionError("caught internal violation was hidden")
        assert not second_allowed.exists()

        worker_material = signed_material(
            "worker-violation",
            worker_capability_id,
            worker_allowed,
        )
        try:
            guard.execute_released(*worker_material)
        except RuntimeGuardViolation as exc:
            assert exc.code == "runtime_active_permit_revoked"
        else:
            raise AssertionError("pre-existing worker violation was hidden")
        assert not worker_allowed.exists()
        assert worker_results[-1] == {
            "violation": "runtime_effect_not_magic_star_released"
        }

        secondary_material = signed_material(
            "secondary-after-concurrency",
            secondary_capability_id,
            secondary_allowed,
        )
        worker_job["material"] = secondary_material
        serialized_material = signed_material(
            "serialized-primary",
            serialized_capability_id,
            serialized_allowed,
        )
        serialized_execution = guard.execute_released(*serialized_material)
        assert serialized_execution["all_manifest_operations_consumed"] is True
        assert serialized_allowed.is_dir()
        assert worker_results[-1] == {
            "concurrent": "concurrent_runtime_effect_forbidden",
            "active_count": 1,
        }
        secondary_execution = guard.execute_released(*secondary_material)
        assert secondary_execution["all_manifest_operations_consumed"] is True
        assert secondary_allowed.is_dir()

        escaping = signed_material(
            "escaping",
            escaping_capability_id,
            escaped_allowed,
        )
        try:
            guard.execute_released(*escaping)
        except RuntimeGuardError as exc:
            assert exc.code == "runtime_effect_manifest_not_fully_consumed"
        else:
            raise AssertionError("unconsumed escaped permit was accepted")
        assert escaped_context is not None
        try:
            escaped_context.run(
                lambda: escaped_allowed.mkdir()
            )
        except RuntimeGuardViolation as exc:
            blocked_codes.append(exc.code)
        else:
            raise AssertionError("copied context retained a released permit")
        assert not escaped_allowed.exists()

        try:
            sys.audit("os.remove", str(denied), -1)
        except RuntimeGuardViolation as exc:
            blocked_codes.append(exc.code)
        else:
            raise AssertionError("caller-spoofed audit event was not denied")

        worker_stop.set()
        worker_done.clear()
        worker_trigger.set()
        assert worker_done.wait(10)
        preexisting_worker.join(timeout=10)
        assert not preexisting_worker.is_alive()

        receipts = recorder.receipts()
        rendered = json.dumps(receipts, sort_keys=True)
        assert len(receipts) == 13
        assert "NEVER_STORE_THIS_PATH_CANARY" not in rendered
        assert "NEVER_STORE_THIS_VALUE_CANARY" not in rendered
        assert "AUREON_NEVER_STORE_CANARY" not in rendered
        assert all(item["hnc_evidence_binding"] for item in receipts)
        assert all(item["raw_arguments_retained"] is False for item in receipts)
        assert all(item["audit_event_origin_attested"] is False for item in receipts)
        summary = guard.public_summary()
        assert summary["violation_count"] == 13
        assert summary["evidence_failure_count"] == 0
        assert summary["native_code_isolation_attested"] is False
        assert install["production_ready"] is False
        print(json.dumps({
            "blocked_codes": blocked_codes,
            "execution": execution,
            "receipt_count": len(receipts),
            "summary": summary,
        }, sort_keys=True))
        """
    )
    environment = os.environ.copy()
    environment.update(
        {
            "AUREON_RUNTIME_GUARD_TEST_ROOT": str(tmp_path.resolve()),
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONHASHSEED": "0",
            "PYTHONNOUSERSITE": "1",
        }
    )
    completed = subprocess.run(
        [sys.executable, "-B", "-c", child],
        cwd=Path(__file__).resolve().parents[2],
        env=environment,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    report = json.loads(completed.stdout)
    assert report["receipt_count"] == 13
    assert report["blocked_codes"] == [
        "runtime_effect_not_magic_star_released",
    ] * 10
    assert report["summary"]["consumed_dispatch_count"] == 9
    assert report["summary"]["active_permit"] is False

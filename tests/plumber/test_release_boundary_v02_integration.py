from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from aureon.plumber.release_boundary_v02 import (
    CapabilityReleaseResultV02,
    ReleaseBoundaryError,
    validate_capability_release_result_v02,
)
from aureon.plumber.release_state_v02 import InMemoryEPASChainStoreV02, ReleasePhase

from .test_release_boundary_v02 import MASTER_KEY, PLAINTEXT, _build_fixture, _digest


def test_release_boundary_end_to_end_success_has_verified_secret_free_readback() -> None:
    fixture = _build_fixture()

    result = fixture.release()
    verified = validate_capability_release_result_v02(
        result,
        receipt_authority=fixture.receipt_authority,
        expected_join={
            "packet_commitment": fixture.packet.packet_commitment,
            "session_id": fixture.session_id,
            "capability_id": "verify-signature",
        },
    )
    rendered = json.dumps(result.public_dict(), sort_keys=True)

    assert result.result == {"signature_valid": True}
    assert verified["valid"] is True
    assert verified["production_ready"] is False
    assert result.release_state.phase is ReleasePhase.CONSUMED
    assert result.epas_state.epoch == fixture.initial_epas.epoch + 1
    assert fixture.epas_store.snapshot() == result.epas_state
    assert fixture.invocations == [PLAINTEXT]
    assert PLAINTEXT.decode() not in rendered
    assert MASTER_KEY.decode() not in rendered


def test_shared_epas_cas_allows_only_one_cross_boundary_concurrent_release() -> None:
    shared_epas = InMemoryEPASChainStoreV02(
        epoch=19,
        head_sha256=_digest("shared-concurrency-epas-head"),
    )
    first = _build_fixture(
        packet_id="packet-concurrent-first",
        session_id="session-concurrent-first",
        epas_store=shared_epas,
    )
    second = _build_fixture(
        packet_id="packet-concurrent-second",
        session_id="session-concurrent-second",
        epas_store=shared_epas,
    )
    start = Barrier(3)

    def release(fixture: object) -> CapabilityReleaseResultV02 | ReleaseBoundaryError:
        start.wait()
        try:
            return fixture.release()  # type: ignore[attr-defined,no-any-return]
        except ReleaseBoundaryError as exc:
            return exc

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(release, fixture) for fixture in (first, second)]
        start.wait()
        outcomes = [future.result(timeout=10) for future in futures]

    successes = [item for item in outcomes if isinstance(item, CapabilityReleaseResultV02)]
    denials = [item for item in outcomes if isinstance(item, ReleaseBoundaryError)]
    assert len(successes) == 1
    assert len(denials) == 1
    assert len(first.invocations) + len(second.invocations) == 1
    assert shared_epas.snapshot().epoch == 20
    assert successes[0].epas_state == shared_epas.snapshot()

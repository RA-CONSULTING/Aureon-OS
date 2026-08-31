from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

import pytest

from aureon.plumber.release_state_v02 import (
    InMemoryEPASChainStoreV02,
    InMemoryReleaseStateStoreV02,
    OpaqueCustodyLease,
    ReleasePhase,
    ReleaseStateError,
)

NOW_MS = 1_900_000_000_000


def _digest(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


@dataclass
class _Clock:
    now_ms: int = NOW_MS

    def __call__(self) -> int:
        return self.now_ms


def _created_store(
    *,
    clock: _Clock | None = None,
) -> tuple[InMemoryReleaseStateStoreV02, _Clock]:
    trusted_clock = clock or _Clock()
    store = InMemoryReleaseStateStoreV02(trusted_now_ms=trusted_clock)
    store.create(
        session_id="session-v02",
        packet_id="packet-v02",
        purpose="verify_document_signature",
        live_binding_sha256=_digest("live-binding"),
        expires_at_ms=NOW_MS + 60_000,
    )
    return store, trusted_clock


def test_release_state_happy_path_is_atomic_one_use_and_lab_only() -> None:
    store, _clock = _created_store()
    assert store.production_ready is False
    assert store.snapshot("session-v02").phase is ReleasePhase.CREATED

    reserved = store.reserve(
        session_id="session-v02",
        expected_live_binding_sha256=_digest("live-binding"),
    )
    lease = store.claim_custody(session_id="session-v02")
    consumed = store.consume(lease)

    assert reserved.version == 1
    assert consumed.phase is ReleasePhase.CONSUMED
    assert consumed.version == 3
    assert consumed.terminal_reason is None

    with pytest.raises(ReleaseStateError, match="release_session_not_consumable"):
        store.consume(lease)


def test_release_state_rejects_session_reuse_and_live_binding_change() -> None:
    store, _clock = _created_store()

    with pytest.raises(ReleaseStateError, match="release_session_reused"):
        store.create(
            session_id="session-v02",
            packet_id="another-packet",
            purpose="verify_document_signature",
            live_binding_sha256=_digest("live-binding"),
            expires_at_ms=NOW_MS + 60_000,
        )

    with pytest.raises(ReleaseStateError, match="live_binding_changed"):
        store.reserve(
            session_id="session-v02",
            expected_live_binding_sha256=_digest("different-live-binding"),
        )
    denied = store.snapshot("session-v02")
    assert denied.phase is ReleasePhase.DENIED
    assert denied.terminal_reason == "live_binding_changed"


def test_release_state_expiry_is_terminal_and_clears_custody() -> None:
    store, clock = _created_store()
    store.reserve(
        session_id="session-v02",
        expected_live_binding_sha256=_digest("live-binding"),
    )
    store.claim_custody(session_id="session-v02")
    clock.now_ms = NOW_MS + 60_000

    with pytest.raises(ReleaseStateError, match="release_session_expired"):
        store.claim_custody(session_id="session-v02")
    expired = store.snapshot("session-v02")
    assert expired.phase is ReleasePhase.DENIED
    assert expired.terminal_reason == "release_session_expired"


def test_release_state_rejects_forged_lease_and_makes_denial_terminal() -> None:
    store, _clock = _created_store()
    store.reserve(
        session_id="session-v02",
        expected_live_binding_sha256=_digest("live-binding"),
    )
    real_lease = store.claim_custody(session_id="session-v02")
    forged = OpaqueCustodyLease(
        session_id=real_lease.session_id,
        packet_id=real_lease.packet_id,
        lease_token="forged-lease-token",
    )

    with pytest.raises(ReleaseStateError, match="custody_lease_mismatch"):
        store.consume(forged)
    assert store.snapshot("session-v02").phase is ReleasePhase.DENIED
    with pytest.raises(ReleaseStateError, match="release_session_not_consumable"):
        store.consume(real_lease)


def test_release_state_public_views_and_repr_omit_lease_secret() -> None:
    store, _clock = _created_store()
    store.reserve(
        session_id="session-v02",
        expected_live_binding_sha256=_digest("live-binding"),
    )
    lease = store.claim_custody(session_id="session-v02")

    rendered_snapshot = json.dumps(store.snapshot("session-v02").public_dict(), sort_keys=True)
    rendered_lease = repr(lease)
    assert lease.lease_token not in rendered_snapshot
    assert lease.lease_token not in rendered_lease
    assert "lease_token" not in rendered_snapshot
    assert "lease_token" not in rendered_lease
    assert "plaintext" not in rendered_snapshot


def test_epas_compare_and_set_advances_once_and_rejects_stale_predecessor() -> None:
    initial_head = _digest("epas-head")
    store = InMemoryEPASChainStoreV02(epoch=9, head_sha256=initial_head)
    assert store.production_ready is False

    advanced = store.compare_and_set(
        expected_epoch=9,
        expected_head_sha256=initial_head,
        terminal_star_sha256=_digest("terminal-star"),
        session_id="session-v02",
        authorization_sha256=_digest("authorization"),
        outcome="CONSUMED",
    )

    assert advanced.epoch == 10
    assert advanced.head_sha256 != initial_head
    with pytest.raises(ReleaseStateError, match="epas_predecessor_mismatch"):
        store.compare_and_set(
            expected_epoch=9,
            expected_head_sha256=initial_head,
            terminal_star_sha256=_digest("terminal-star"),
            session_id="session-v02",
            authorization_sha256=_digest("authorization"),
            outcome="CONSUMED",
        )


def test_epas_compare_and_set_rejects_invalid_terminal_outcome() -> None:
    store = InMemoryEPASChainStoreV02(epoch=0, head_sha256=_digest("epas-head"))

    with pytest.raises(ReleaseStateError, match="epas_outcome_invalid"):
        store.compare_and_set(
            expected_epoch=0,
            expected_head_sha256=_digest("epas-head"),
            terminal_star_sha256=_digest("terminal-star"),
            session_id="session-v02",
            authorization_sha256=_digest("authorization"),
            outcome="RELEASED",
        )


def test_v02_integer_schema_rejects_boolean_epoch() -> None:
    with pytest.raises(ReleaseStateError, match="epas_epoch_invalid"):
        InMemoryEPASChainStoreV02(
            epoch=True,  # type: ignore[arg-type]
            head_sha256=_digest("epas-head"),
        )


@pytest.mark.parametrize(
    ("expected_epoch", "expected_head"),
    [
        (10, _digest("epas-head")),
        (9, _digest("mixed-lineage-head")),
    ],
    ids=("future-epoch", "mixed-head"),
)
def test_epas_rejects_future_or_mixed_predecessor_without_advancing(
    expected_epoch: int,
    expected_head: str,
) -> None:
    initial_head = _digest("epas-head")
    store = InMemoryEPASChainStoreV02(epoch=9, head_sha256=initial_head)
    initial = store.snapshot()

    with pytest.raises(ReleaseStateError, match="epas_predecessor_mismatch"):
        store.compare_and_set(
            expected_epoch=expected_epoch,
            expected_head_sha256=expected_head,
            terminal_star_sha256=_digest("terminal-star"),
            session_id="session-v02",
            authorization_sha256=_digest("authorization"),
            outcome="CONSUMED",
        )

    assert store.snapshot() == initial

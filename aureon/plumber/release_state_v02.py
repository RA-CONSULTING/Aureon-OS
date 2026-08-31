"""Atomic in-memory state model for the Plumber Magic Star v0.2 lab path.

The stores in this module model one-use and EPAS compare-and-set semantics.  They
are deliberately process-local and rollbackable, so they are never production
evidence.  Production requires a durable, monotonic, independently administered
state service.
"""

from __future__ import annotations

import re
import secrets
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field, replace
from enum import StrEnum
from typing import Any

from .crypto import b64url_encode, domain_hash

STATE_SCHEMA = "aureon.plumber.magic-star.release-state.v02"
EPAS_STATE_SCHEMA = "aureon.plumber.magic-star.epas-state.v02"
_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_MAX_SESSION_LIFETIME_MS = 15 * 60 * 1000


class ReleaseStateError(ValueError):
    """A stable fail-closed release-state error."""

    def __init__(self, code: str) -> None:
        self.code = str(code)
        super().__init__(self.code)


class ReleasePhase(StrEnum):
    CREATED = "CREATED"
    RESERVED = "RESERVED"
    CUSTODY = "CUSTODY"
    CONSUMED = "CONSUMED"
    DENIED = "DENIED"


@dataclass(frozen=True, slots=True)
class ReleaseStateSnapshot:
    schema: str
    session_id: str
    packet_id: str
    purpose: str
    live_binding_sha256: str
    expires_at_ms: int
    phase: ReleasePhase
    version: int
    terminal_reason: str | None = None

    def public_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "session_id": self.session_id,
            "packet_id": self.packet_id,
            "purpose": self.purpose,
            "live_binding_sha256": self.live_binding_sha256,
            "expires_at_ms": self.expires_at_ms,
            "phase": self.phase.value,
            "version": self.version,
            "terminal_reason": self.terminal_reason,
        }


@dataclass(frozen=True, slots=True)
class OpaqueCustodyLease:
    """One-use lease.  The secret token is omitted from repr and public views."""

    session_id: str
    packet_id: str
    lease_token: str = field(repr=False)


@dataclass(slots=True)
class _MutableState:
    snapshot: ReleaseStateSnapshot
    lease_digest: str | None = None


def _identifier(value: object, *, code: str) -> str:
    if not isinstance(value, str) or _IDENTIFIER.fullmatch(value) is None:
        raise ReleaseStateError(code)
    return value


def _sha256(value: object, *, code: str) -> str:
    if not isinstance(value, str) or _SHA256.fullmatch(value) is None:
        raise ReleaseStateError(code)
    return value


def _uint(value: object, *, code: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ReleaseStateError(code)
    return value


def _system_now_ms() -> int:
    return time.time_ns() // 1_000_000


class InMemoryReleaseStateStoreV02:
    """Thread-safe one-use state store for tests and local development only."""

    production_ready = False

    def __init__(self, *, trusted_now_ms: Callable[[], int] = _system_now_ms) -> None:
        self._trusted_now_ms = trusted_now_ms
        self._states: dict[str, _MutableState] = {}
        self._lock = threading.RLock()

    def _now(self) -> int:
        return _uint(self._trusted_now_ms(), code="trusted_time_invalid")

    def _active(self, session_id: str) -> _MutableState:
        key = _identifier(session_id, code="session_id_invalid")
        state = self._states.get(key)
        if state is None:
            raise ReleaseStateError("release_session_unknown")
        return state

    def _require_not_expired(self, state: _MutableState) -> None:
        if self._now() >= state.snapshot.expires_at_ms:
            state.snapshot = replace(
                state.snapshot,
                phase=ReleasePhase.DENIED,
                version=state.snapshot.version + 1,
                terminal_reason="release_session_expired",
            )
            state.lease_digest = None
            raise ReleaseStateError("release_session_expired")

    def create(
        self,
        *,
        session_id: str,
        packet_id: str,
        purpose: str,
        live_binding_sha256: str,
        expires_at_ms: int,
    ) -> ReleaseStateSnapshot:
        session = _identifier(session_id, code="session_id_invalid")
        packet = _identifier(packet_id, code="packet_id_invalid")
        bounded_purpose = _identifier(purpose, code="purpose_invalid")
        live_binding = _sha256(live_binding_sha256, code="live_binding_invalid")
        expiry = _uint(expires_at_ms, code="expiry_invalid")
        with self._lock:
            now = self._now()
            if expiry <= now or expiry - now > _MAX_SESSION_LIFETIME_MS:
                raise ReleaseStateError("expiry_outside_local_policy")
            if session in self._states:
                raise ReleaseStateError("release_session_reused")
            snapshot = ReleaseStateSnapshot(
                schema=STATE_SCHEMA,
                session_id=session,
                packet_id=packet,
                purpose=bounded_purpose,
                live_binding_sha256=live_binding,
                expires_at_ms=expiry,
                phase=ReleasePhase.CREATED,
                version=0,
            )
            self._states[session] = _MutableState(snapshot=snapshot)
            return snapshot

    def reserve(self, *, session_id: str, expected_live_binding_sha256: str) -> ReleaseStateSnapshot:
        expected = _sha256(expected_live_binding_sha256, code="live_binding_invalid")
        with self._lock:
            state = self._active(session_id)
            self._require_not_expired(state)
            if state.snapshot.phase is not ReleasePhase.CREATED:
                raise ReleaseStateError("release_session_not_reservable")
            if state.snapshot.live_binding_sha256 != expected:
                self._deny_locked(state, "live_binding_changed")
                raise ReleaseStateError("live_binding_changed")
            state.snapshot = replace(
                state.snapshot,
                phase=ReleasePhase.RESERVED,
                version=state.snapshot.version + 1,
            )
            return state.snapshot

    def claim_custody(self, *, session_id: str) -> OpaqueCustodyLease:
        with self._lock:
            state = self._active(session_id)
            self._require_not_expired(state)
            if state.snapshot.phase is not ReleasePhase.RESERVED:
                raise ReleaseStateError("release_session_not_claimable")
            token = b64url_encode(secrets.token_bytes(32))
            state.lease_digest = domain_hash(
                "AUREON-PLUMBER-V02-CUSTODY-LEASE",
                {"session_id": state.snapshot.session_id, "lease_token": token},
            )
            state.snapshot = replace(
                state.snapshot,
                phase=ReleasePhase.CUSTODY,
                version=state.snapshot.version + 1,
            )
            return OpaqueCustodyLease(
                session_id=state.snapshot.session_id,
                packet_id=state.snapshot.packet_id,
                lease_token=token,
            )

    def consume(self, lease: OpaqueCustodyLease) -> ReleaseStateSnapshot:
        if not isinstance(lease, OpaqueCustodyLease):
            raise ReleaseStateError("custody_lease_invalid")
        with self._lock:
            state = self._active(lease.session_id)
            self._require_not_expired(state)
            if state.snapshot.phase is not ReleasePhase.CUSTODY:
                raise ReleaseStateError("release_session_not_consumable")
            if state.snapshot.packet_id != lease.packet_id:
                self._deny_locked(state, "custody_lease_packet_mismatch")
                raise ReleaseStateError("custody_lease_packet_mismatch")
            expected = domain_hash(
                "AUREON-PLUMBER-V02-CUSTODY-LEASE",
                {"session_id": state.snapshot.session_id, "lease_token": lease.lease_token},
            )
            if not secrets.compare_digest(state.lease_digest or "", expected):
                self._deny_locked(state, "custody_lease_mismatch")
                raise ReleaseStateError("custody_lease_mismatch")
            state.lease_digest = None
            state.snapshot = replace(
                state.snapshot,
                phase=ReleasePhase.CONSUMED,
                version=state.snapshot.version + 1,
            )
            return state.snapshot

    def validate_lease(self, lease: OpaqueCustodyLease) -> bool:
        """Re-sample time and authenticate an opaque lease without consuming it."""

        if not isinstance(lease, OpaqueCustodyLease):
            raise ReleaseStateError("custody_lease_invalid")
        with self._lock:
            state = self._active(lease.session_id)
            self._require_not_expired(state)
            if state.snapshot.phase is not ReleasePhase.CUSTODY:
                raise ReleaseStateError("release_session_not_in_custody")
            if state.snapshot.packet_id != lease.packet_id:
                self._deny_locked(state, "custody_lease_packet_mismatch")
                raise ReleaseStateError("custody_lease_packet_mismatch")
            expected = domain_hash(
                "AUREON-PLUMBER-V02-CUSTODY-LEASE",
                {"session_id": state.snapshot.session_id, "lease_token": lease.lease_token},
            )
            if not secrets.compare_digest(state.lease_digest or "", expected):
                self._deny_locked(state, "custody_lease_mismatch")
                raise ReleaseStateError("custody_lease_mismatch")
            return True

    def _deny_locked(self, state: _MutableState, reason: str) -> ReleaseStateSnapshot:
        if state.snapshot.phase in {ReleasePhase.CONSUMED, ReleasePhase.DENIED}:
            return state.snapshot
        state.lease_digest = None
        state.snapshot = replace(
            state.snapshot,
            phase=ReleasePhase.DENIED,
            version=state.snapshot.version + 1,
            terminal_reason=_identifier(reason, code="terminal_reason_invalid"),
        )
        return state.snapshot

    def deny(self, *, session_id: str, reason: str) -> ReleaseStateSnapshot:
        with self._lock:
            return self._deny_locked(self._active(session_id), reason)

    def snapshot(self, session_id: str) -> ReleaseStateSnapshot:
        with self._lock:
            return self._active(session_id).snapshot


@dataclass(frozen=True, slots=True)
class EPASChainSnapshot:
    schema: str
    epoch: int
    head_sha256: str

    def public_dict(self) -> dict[str, Any]:
        return {"schema": self.schema, "epoch": self.epoch, "head_sha256": self.head_sha256}


@dataclass(frozen=True, slots=True)
class OpaqueEPASReservation:
    epoch: int
    head_sha256: str
    reservation_token: str = field(repr=False)


class InMemoryEPASChainStoreV02:
    """Exact-predecessor EPAS chain model.  It is not durable ancestry proof."""

    production_ready = False

    def __init__(self, *, epoch: int, head_sha256: str) -> None:
        self._snapshot = EPASChainSnapshot(
            schema=EPAS_STATE_SCHEMA,
            epoch=_uint(epoch, code="epas_epoch_invalid"),
            head_sha256=_sha256(head_sha256, code="epas_head_invalid"),
        )
        self._reservation_digest: str | None = None
        self._lock = threading.RLock()

    def snapshot(self) -> EPASChainSnapshot:
        with self._lock:
            return self._snapshot

    def compare_and_set(
        self,
        *,
        expected_epoch: int,
        expected_head_sha256: str,
        terminal_star_sha256: str,
        session_id: str,
        authorization_sha256: str,
        outcome: str,
    ) -> EPASChainSnapshot:
        epoch = _uint(expected_epoch, code="epas_epoch_invalid")
        head = _sha256(expected_head_sha256, code="epas_head_invalid")
        star = _sha256(terminal_star_sha256, code="terminal_star_invalid")
        session = _identifier(session_id, code="session_id_invalid")
        authorization = _sha256(authorization_sha256, code="authorization_invalid")
        terminal_outcome = str(outcome or "")
        if terminal_outcome not in {"CONSUMED", "DENIED"}:
            raise ReleaseStateError("epas_outcome_invalid")
        with self._lock:
            if self._reservation_digest is not None:
                raise ReleaseStateError("epas_chain_reserved")
            current = self._snapshot
            if current.epoch != epoch or current.head_sha256 != head:
                raise ReleaseStateError("epas_predecessor_mismatch")
            next_epoch = current.epoch + 1
            next_head = domain_hash(
                "AUREON-PLUMBER-V02-EPAS-MEMORY",
                {
                    "previous_epoch": current.epoch,
                    "previous_head_sha256": current.head_sha256,
                    "terminal_star_sha256": star,
                    "session_id": session,
                    "authorization_sha256": authorization,
                    "outcome": terminal_outcome,
                    "next_epoch": next_epoch,
                },
            )
            self._snapshot = EPASChainSnapshot(
                schema=EPAS_STATE_SCHEMA,
                epoch=next_epoch,
                head_sha256=next_head,
            )
            return self._snapshot

    def reserve(
        self,
        *,
        expected_epoch: int,
        expected_head_sha256: str,
    ) -> OpaqueEPASReservation:
        epoch = _uint(expected_epoch, code="epas_epoch_invalid")
        head = _sha256(expected_head_sha256, code="epas_head_invalid")
        with self._lock:
            if self._reservation_digest is not None:
                raise ReleaseStateError("epas_chain_reserved")
            if self._snapshot.epoch != epoch or self._snapshot.head_sha256 != head:
                raise ReleaseStateError("epas_predecessor_mismatch")
            token = b64url_encode(secrets.token_bytes(32))
            self._reservation_digest = domain_hash(
                "AUREON-PLUMBER-V02-EPAS-RESERVATION",
                {"epoch": epoch, "head_sha256": head, "reservation_token": token},
            )
            return OpaqueEPASReservation(
                epoch=epoch,
                head_sha256=head,
                reservation_token=token,
            )

    def finalize(
        self,
        reservation: OpaqueEPASReservation,
        *,
        terminal_star_sha256: str,
        session_id: str,
        authorization_sha256: str,
        outcome: str,
    ) -> EPASChainSnapshot:
        if not isinstance(reservation, OpaqueEPASReservation):
            raise ReleaseStateError("epas_reservation_invalid")
        star = _sha256(terminal_star_sha256, code="terminal_star_invalid")
        session = _identifier(session_id, code="session_id_invalid")
        authorization = _sha256(authorization_sha256, code="authorization_invalid")
        terminal_outcome = str(outcome or "")
        if terminal_outcome not in {"CONSUMED", "DENIED"}:
            raise ReleaseStateError("epas_outcome_invalid")
        with self._lock:
            expected_digest = domain_hash(
                "AUREON-PLUMBER-V02-EPAS-RESERVATION",
                {
                    "epoch": reservation.epoch,
                    "head_sha256": reservation.head_sha256,
                    "reservation_token": reservation.reservation_token,
                },
            )
            if not secrets.compare_digest(
                self._reservation_digest or "", expected_digest
            ):
                raise ReleaseStateError("epas_reservation_mismatch")
            current = self._snapshot
            if (
                current.epoch != reservation.epoch
                or current.head_sha256 != reservation.head_sha256
            ):
                self._reservation_digest = None
                raise ReleaseStateError("epas_predecessor_mismatch")
            next_epoch = current.epoch + 1
            next_head = domain_hash(
                "AUREON-PLUMBER-V02-EPAS-MEMORY",
                {
                    "previous_epoch": current.epoch,
                    "previous_head_sha256": current.head_sha256,
                    "terminal_star_sha256": star,
                    "session_id": session,
                    "authorization_sha256": authorization,
                    "outcome": terminal_outcome,
                    "next_epoch": next_epoch,
                },
            )
            self._snapshot = EPASChainSnapshot(
                schema=EPAS_STATE_SCHEMA,
                epoch=next_epoch,
                head_sha256=next_head,
            )
            self._reservation_digest = None
            return self._snapshot


__all__ = [
    "EPASChainSnapshot",
    "EPAS_STATE_SCHEMA",
    "InMemoryEPASChainStoreV02",
    "InMemoryReleaseStateStoreV02",
    "OpaqueCustodyLease",
    "OpaqueEPASReservation",
    "ReleasePhase",
    "ReleaseStateError",
    "ReleaseStateSnapshot",
    "STATE_SCHEMA",
]

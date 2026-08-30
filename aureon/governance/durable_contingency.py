"""Crash-safe recovery of a pre-approved economic contingency.

The SHA-256 envelope detects corruption and accidental tampering; it is not an
identity credential. Trust comes from the private route directory ACL and from
injecting an adapter whose identity is allowlisted at the composition root.
Request data cannot select the adapter or provide an approval receipt/boolean.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import secrets
import tempfile
import time
from collections.abc import Callable, Mapping
from contextlib import contextmanager
from dataclasses import asdict, dataclass, fields
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, TypeVar

from aureon.governance.economic_boundary import (
    CONTINGENCY_SCOPE_SCHEMA,
    ContingencyWarrant,
    ContingencyWarrantScope,
    EconomicGovernanceBlocked,
    EconomicGovernanceBoundary,
    EconomicIntent,
    EconomicMutationPermit,
    _issue_trusted_contingency_recovery_claim,
)

RECOVERY_STORE_SCHEMA = "aureon.durable_contingency_store.v1"
RECOVERY_RECORD_SCHEMA = "aureon.durable_contingency_record.v1"
_FACTORY_TOKEN = object()
_DIGEST_LENGTH = 64
_T = TypeVar("_T")


class DurableContingencyStateError(EconomicGovernanceBlocked):
    """The durable recovery record is absent, corrupt, or not claimable."""


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def _digest_payload(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _valid_digest(value: Any, name: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != _DIGEST_LENGTH
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise DurableContingencyStateError(f"{name}_invalid")
    return value


def _canonical_decimal(value: Any, name: str) -> str:
    if isinstance(value, bool):
        raise DurableContingencyStateError(f"{name}_invalid")
    try:
        number = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise DurableContingencyStateError(f"{name}_invalid") from exc
    if not number.is_finite():
        raise DurableContingencyStateError(f"{name}_invalid")
    text = format(number, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return "0" if number == 0 else text


def _nonblank(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise DurableContingencyStateError(f"{name}_invalid")
    return value


def _private_store_path(path: Path) -> Path:
    lowered = {part.casefold() for part in path.parts}
    if lowered.intersection({"frontend", "public"}):
        raise ValueError("private_recovery_store_path_required")
    if path.suffix.casefold() != ".json":
        raise ValueError("json_recovery_store_path_required")
    return path


@dataclass(frozen=True, slots=True)
class DurableContingencyRecordRef:
    record_digest: str
    entry_state_anchor: str
    bound_route_state_anchor: str | None = None

    def __post_init__(self) -> None:
        _valid_digest(self.record_digest, "record_digest")
        _valid_digest(self.entry_state_anchor, "entry_state_anchor")
        if self.bound_route_state_anchor is not None:
            _valid_digest(
                self.bound_route_state_anchor,
                "bound_route_state_anchor",
            )


@dataclass(frozen=True, slots=True)
class DurableContingencyMaterial:
    warrant: ContingencyWarrant
    scope: ContingencyWarrantScope


@dataclass(frozen=True, slots=True)
class RecoveredContingencyPermit:
    reference: DurableContingencyRecordRef
    claim_id: str
    intent: EconomicIntent
    permit: EconomicMutationPermit


class DurableContingencyRecovery:
    """Allowlisted, OS-locked recovery adapter bound to one private store."""

    def __init__(
        self,
        *,
        _factory_token: object,
        adapter_id: str,
        boundary: EconomicGovernanceBoundary,
        store_path: Path,
        clock: Callable[[], float],
        claim_ttl: Decimal,
    ) -> None:
        if _factory_token is not _FACTORY_TOKEN:
            raise TypeError("use_bind_durable_contingency_recovery")
        self.adapter_id = _nonblank(adapter_id, "adapter_id")
        self.boundary = boundary
        self.store_path = _private_store_path(store_path)
        self.clock = clock
        self.claim_ttl = claim_ttl

    def _now(self) -> Decimal:
        value = self.clock()
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(float(value))
        ):
            raise DurableContingencyStateError("finite_clock_required")
        return Decimal(str(float(value)))

    @property
    def _lock_path(self) -> Path:
        return self.store_path.with_name(self.store_path.stem + ".lock")

    @contextmanager
    def _lock(self):
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        with self._lock_path.open("a+b") as handle:
            handle.seek(0, os.SEEK_END)
            if handle.tell() == 0:
                handle.write(b"0")
                handle.flush()
                os.fsync(handle.fileno())
            handle.seek(0)
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(
                    handle.fileno(),
                    fcntl.LOCK_EX | fcntl.LOCK_NB,
                )
            try:
                yield
            finally:
                handle.seek(0)
                if os.name == "nt":
                    import msvcrt

                    msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl

                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

    def _core_record(
        self,
        warrant: ContingencyWarrant,
        scope: ContingencyWarrantScope,
        entry_state_anchor: str,
    ) -> dict[str, Any]:
        return {
            "schema": RECOVERY_RECORD_SCHEMA,
            "adapter_id": self.adapter_id,
            "warrant": asdict(warrant),
            "scope": scope.payload(),
            "entry_state_anchor": entry_state_anchor,
        }

    @staticmethod
    def _empty_store() -> dict[str, Any]:
        return {
            "schema": RECOVERY_STORE_SCHEMA,
            "records": {},
        }

    def _read_locked(self) -> dict[str, Any]:
        if not self.store_path.exists():
            return self._empty_store()
        try:
            raw = json.loads(self.store_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise DurableContingencyStateError(
                "recovery_store_unreadable"
            ) from exc
        if (
            not isinstance(raw, dict)
            or raw.get("schema") != RECOVERY_STORE_SCHEMA
            or not isinstance(raw.get("records"), dict)
        ):
            raise DurableContingencyStateError("recovery_store_schema_invalid")
        observed = raw.get("state_hash")
        core = {key: value for key, value in raw.items() if key != "state_hash"}
        if observed != _digest_payload(core):
            raise DurableContingencyStateError("recovery_store_hash_mismatch")
        for key, record in raw["records"].items():
            if not isinstance(record, dict) or key != record.get("record_digest"):
                raise DurableContingencyStateError(
                    "recovery_record_index_invalid"
                )
            immutable = {
                name: record.get(name)
                for name in (
                    "schema",
                    "adapter_id",
                    "warrant",
                    "scope",
                    "entry_state_anchor",
                )
            }
            if key != _digest_payload(immutable):
                raise DurableContingencyStateError(
                    "recovery_record_digest_mismatch"
                )
        return raw

    def _write_locked(self, state: Mapping[str, Any]) -> None:
        core = {key: value for key, value in state.items() if key != "state_hash"}
        payload = {**core, "state_hash": _digest_payload(core)}
        serialized = json.dumps(
            payload,
            sort_keys=True,
            indent=2,
            ensure_ascii=False,
            allow_nan=False,
        ) + "\n"
        temporary_name: str | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=self.store_path.parent,
                prefix=self.store_path.name + ".",
                suffix=".tmp",
                delete=False,
            ) as temporary:
                temporary_name = temporary.name
                temporary.write(serialized)
                temporary.flush()
                os.fsync(temporary.fileno())
            os.chmod(temporary_name, 0o600)
            os.replace(temporary_name, self.store_path)
            temporary_name = None
        finally:
            if temporary_name is not None:
                try:
                    Path(temporary_name).unlink()
                except OSError:
                    pass

    @staticmethod
    def _exact_dataclass(
        type_: type[_T],
        raw: Any,
        name: str,
    ) -> _T:
        if not isinstance(raw, Mapping):
            raise DurableContingencyStateError(f"{name}_invalid")
        values = dict(raw)
        if (
            type_ is ContingencyWarrantScope
            and values.pop("schema", None) != CONTINGENCY_SCOPE_SCHEMA
        ):
            raise DurableContingencyStateError(f"{name}_invalid")
        if type_ is ContingencyWarrantScope:
            # Scope payloads intentionally omit absent optional causal fields.
            # Restore their dataclass defaults before exact-key validation.
            for optional_name in (
                "field_provider_receipt_ids",
                "field_provider_moment_digest",
                "field_provider_source_timestamp",
                "decision_evidence_json",
            ):
                values.setdefault(optional_name, None)
        expected = {item.name for item in fields(type_)}
        if set(values) != expected:
            raise DurableContingencyStateError(f"{name}_invalid")
        if type_ is ContingencyWarrantScope:
            provider_ids = values.get("provider_receipt_ids")
            if not isinstance(provider_ids, list):
                raise DurableContingencyStateError(f"{name}_invalid")
            values["provider_receipt_ids"] = tuple(provider_ids)
            field_provider_ids = values.get("field_provider_receipt_ids")
            if field_provider_ids is not None:
                if not isinstance(field_provider_ids, list):
                    raise DurableContingencyStateError(f"{name}_invalid")
                values["field_provider_receipt_ids"] = tuple(field_provider_ids)
        try:
            return type_(**values)
        except (TypeError, ValueError) as exc:
            raise DurableContingencyStateError(f"{name}_invalid") from exc

    def _record_locked(
        self,
        state: Mapping[str, Any],
        reference: DurableContingencyRecordRef,
    ) -> tuple[dict[str, Any], ContingencyWarrant, ContingencyWarrantScope]:
        records = state.get("records")
        record = (
            records.get(reference.record_digest)
            if isinstance(records, Mapping)
            else None
        )
        if not isinstance(record, dict):
            raise DurableContingencyStateError(
                "durable_contingency_record_missing"
            )
        if (
            record.get("adapter_id") != self.adapter_id
            or record.get("record_digest") != reference.record_digest
            or record.get("entry_state_anchor")
            != reference.entry_state_anchor
            or (
                reference.bound_route_state_anchor is not None
                and record.get("bound_route_state_anchor")
                != reference.bound_route_state_anchor
            )
        ):
            raise DurableContingencyStateError(
                "durable_contingency_route_binding_mismatch"
            )
        warrant = self._exact_dataclass(
            ContingencyWarrant,
            record.get("warrant"),
            "persisted_warrant",
        )
        scope = self._exact_dataclass(
            ContingencyWarrantScope,
            record.get("scope"),
            "persisted_scope",
        )
        self.boundary._validate_recovered_warrant(
            warrant,
            scope,
            now=self._now(),
        )
        return record, warrant, scope

    @staticmethod
    def _stable_route_binding_anchor(
        record_digest: str,
        entry_state_anchor: str,
        scope: ContingencyWarrantScope,
    ) -> str:
        return _digest_payload(
            {
                "record_digest": record_digest,
                "entry_state_anchor": entry_state_anchor,
                "venue": scope.venue,
                "environment": scope.environment,
                "account_id_hash": scope.account_id_hash,
                "authorization_receipt_id": (
                    scope.authorization_receipt_id
                ),
                "cycle_id": scope.cycle_id,
                "entry_intent_digest": scope.entry_intent_digest,
            }
        )

    def register(
        self,
        warrant: ContingencyWarrant,
        scope: ContingencyWarrantScope,
        *,
        entry_state_anchor: str,
    ) -> DurableContingencyRecordRef:
        """Persist full causal material before the entry transport is callable."""

        anchor = _valid_digest(entry_state_anchor, "entry_state_anchor")
        if (
            not isinstance(warrant, ContingencyWarrant)
            or not isinstance(scope, ContingencyWarrantScope)
            or warrant.boundary_id != self.boundary._boundary_id
        ):
            raise DurableContingencyStateError(
                "current_boundary_warrant_required"
            )
        self.boundary._validate_recovered_warrant(
            warrant,
            scope,
            now=self._now(),
        )
        immutable = self._core_record(warrant, scope, anchor)
        digest = _digest_payload(immutable)
        with self._lock():
            state = self._read_locked()
            existing = state["records"].get(digest)
            if existing is None:
                state["records"][digest] = {
                    **immutable,
                    "record_digest": digest,
                    "bound_route_state_anchor": None,
                    "status": "AVAILABLE",
                    "claim_id": None,
                    "claimed_at": None,
                    "claim_expires_at": None,
                    "permit_id": None,
                    "permit_expires_at": None,
                    "intent_digest": None,
                    "body_digest": None,
                    "provider_moment_digest": None,
                    "provider_source_timestamp": None,
                    "outcome_recorded_at": None,
                }
                self._write_locked(state)
            else:
                expected_binding = self._stable_route_binding_anchor(
                    digest,
                    anchor,
                    scope,
                )
                stored_binding = existing.get(
                    "bound_route_state_anchor"
                )
                if stored_binding not in {None, expected_binding}:
                    raise DurableContingencyStateError(
                        "durable_contingency_route_binding_mismatch"
                    )
                reference = DurableContingencyRecordRef(
                    record_digest=digest,
                    entry_state_anchor=anchor,
                    bound_route_state_anchor=expected_binding,
                )
                self._record_locked(
                    state,
                    DurableContingencyRecordRef(
                        record_digest=digest,
                        entry_state_anchor=anchor,
                    ),
                )
                return reference
        return DurableContingencyRecordRef(
            record_digest=digest,
            entry_state_anchor=anchor,
            bound_route_state_anchor=self._stable_route_binding_anchor(
                digest,
                anchor,
                scope,
            ),
        )

    def bind_route_state(
        self,
        reference: DurableContingencyRecordRef,
    ) -> DurableContingencyRecordRef:
        """Complete the reciprocal binding before entry transport."""

        if reference.bound_route_state_anchor is None:
            raise DurableContingencyStateError(
                "stable_route_binding_anchor_required"
            )
        with self._lock():
            state = self._read_locked()
            unbound_reference = DurableContingencyRecordRef(
                record_digest=reference.record_digest,
                entry_state_anchor=reference.entry_state_anchor,
            )
            record, _, scope = self._record_locked(
                state,
                unbound_reference,
            )
            anchor = self._stable_route_binding_anchor(
                reference.record_digest,
                reference.entry_state_anchor,
                scope,
            )
            if reference.bound_route_state_anchor != anchor:
                raise DurableContingencyStateError(
                    "durable_contingency_route_binding_mismatch"
                )
            if record.get("status") != "AVAILABLE":
                raise DurableContingencyStateError(
                    "unclaimed_recovery_record_required_for_binding"
                )
            observed = record.get("bound_route_state_anchor")
            if observed not in {None, anchor}:
                raise DurableContingencyStateError(
                    "durable_contingency_route_binding_mismatch"
                )
            record["bound_route_state_anchor"] = anchor
            self._write_locked(state)
        return reference

    def verify_route_binding(
        self,
        reference: DurableContingencyRecordRef,
    ) -> None:
        if reference.bound_route_state_anchor is None:
            raise DurableContingencyStateError(
                "reciprocal_route_state_binding_required"
            )
        with self._lock():
            state = self._read_locked()
            self._record_locked(state, reference)

    def scope_for_recovery(
        self,
        reference: DurableContingencyRecordRef,
    ) -> ContingencyWarrantScope:
        """Return only adapter-verified scope material, never caller evidence."""

        return self.material_for_recovery(reference).scope

    def material_for_recovery(
        self,
        reference: DurableContingencyRecordRef,
    ) -> DurableContingencyMaterial:
        """Return full causal material only after adapter verification."""

        if reference.bound_route_state_anchor is None:
            raise DurableContingencyStateError(
                "reciprocal_route_state_binding_required"
            )
        with self._lock():
            state = self._read_locked()
            record, warrant, scope = self._record_locked(state, reference)
            if record.get("status") != "AVAILABLE":
                raise DurableContingencyStateError(
                    "contingency_recovery_requires_reconciliation"
                )
            return DurableContingencyMaterial(
                warrant=warrant,
                scope=scope,
            )

    def _claim(
        self,
        reference: DurableContingencyRecordRef,
        intent: EconomicIntent,
    ) -> tuple[str, ContingencyWarrant, ContingencyWarrantScope, str, str]:
        if not isinstance(intent, EconomicIntent):
            raise TypeError("economic_intent_required")
        if reference.bound_route_state_anchor is None:
            raise DurableContingencyStateError(
                "reciprocal_route_state_binding_required"
            )
        now = self._now()
        with self._lock():
            state = self._read_locked()
            record, warrant, scope = self._record_locked(state, reference)
            status = record.get("status")
            if status == "CLAIMED":
                claim_expiry = Decimal(
                    _canonical_decimal(
                        record.get("claim_expires_at"),
                        "claim_expires_at",
                    )
                )
                if now <= claim_expiry:
                    raise DurableContingencyStateError(
                        "contingency_recovery_already_claimed"
                    )
                if record.get("permit_id") is not None:
                    raise DurableContingencyStateError(
                        "contingency_recovery_requires_reconciliation"
                    )
                status = "AVAILABLE"
            if status != "AVAILABLE":
                raise DurableContingencyStateError(
                    "contingency_recovery_requires_reconciliation"
                )
            self.boundary._validate_contingency_reduction(scope, intent)
            claim_id = f"contingency-claim:{secrets.token_hex(24)}"
            claimed_at = _canonical_decimal(now, "claimed_at")
            expires_at = _canonical_decimal(
                now + self.claim_ttl,
                "claim_expires_at",
            )
            record.update(
                {
                    "status": "CLAIMED",
                    "claim_id": claim_id,
                    "claimed_at": claimed_at,
                    "claim_expires_at": expires_at,
                    "permit_id": None,
                    "permit_expires_at": None,
                    "intent_digest": intent.intent_digest,
                    "body_digest": intent.body_digest,
                    "provider_moment_digest": (
                        intent.provider_moment_digest
                    ),
                    "provider_source_timestamp": (
                        intent.provider_source_timestamp
                    ),
                    "outcome_recorded_at": None,
                }
            )
            self._write_locked(state)
        return claim_id, warrant, scope, claimed_at, expires_at

    def _release_unprepared_claim(
        self,
        reference: DurableContingencyRecordRef,
        claim_id: str,
    ) -> None:
        try:
            with self._lock():
                state = self._read_locked()
                record, _, _ = self._record_locked(state, reference)
                if (
                    record.get("status") == "CLAIMED"
                    and record.get("claim_id") == claim_id
                    and record.get("permit_id") is None
                ):
                    record.update(
                        {
                            "status": "AVAILABLE",
                            "claim_id": None,
                            "claimed_at": None,
                            "claim_expires_at": None,
                            "intent_digest": None,
                            "body_digest": None,
                            "provider_moment_digest": None,
                            "provider_source_timestamp": None,
                        }
                    )
                    self._write_locked(state)
        except (OSError, BlockingIOError, DurableContingencyStateError):
            # A stale CLAIMED record is safe: its lease outlives the permit.
            return

    def prepare_reduction(
        self,
        reference: DurableContingencyRecordRef,
        intent: EconomicIntent,
    ) -> RecoveredContingencyPermit:
        """Atomically claim, validate fresh position evidence, and mint once."""

        claim_id, warrant, scope, claimed_at, expires_at = self._claim(
            reference,
            intent,
        )
        claim = _issue_trusted_contingency_recovery_claim(
            adapter_id=self.adapter_id,
            record_digest=reference.record_digest,
            claim_id=claim_id,
            claimed_at=claimed_at,
            expires_at=expires_at,
            warrant=warrant,
            scope=scope,
            boundary_capability=self.boundary._recovery_capability,
        )
        try:
            permit = self.boundary.prepare_recovered_contingency_reduction(
                claim,
                intent,
            )
        except Exception:
            self._release_unprepared_claim(reference, claim_id)
            raise
        try:
            with self._lock():
                state = self._read_locked()
                record, _, _ = self._record_locked(state, reference)
                if (
                    record.get("status") != "CLAIMED"
                    or record.get("claim_id") != claim_id
                    or record.get("intent_digest") != intent.intent_digest
                ):
                    raise DurableContingencyStateError(
                        "contingency_claim_changed_before_permit_persist"
                    )
                record.update(
                    {
                        "status": "PERMIT_PREPARED",
                        "permit_id": permit.permit_id,
                        "permit_expires_at": permit.expires_at,
                    }
                )
                self._write_locked(state)
        except Exception:
            # No transport is callable until PERMIT_PREPARED is durably read.
            raise
        return RecoveredContingencyPermit(
            reference=reference,
            claim_id=claim_id,
            intent=intent,
            permit=permit,
        )

    def _set_outcome(
        self,
        recovered: RecoveredContingencyPermit,
        *,
        expected_status: str,
        next_status: str,
    ) -> None:
        with self._lock():
            state = self._read_locked()
            record, _, _ = self._record_locked(
                state,
                recovered.reference,
            )
            if (
                record.get("status") != expected_status
                or record.get("claim_id") != recovered.claim_id
                or record.get("permit_id")
                != recovered.permit.permit_id
                or record.get("intent_digest")
                != recovered.intent.intent_digest
                or record.get("body_digest")
                != recovered.intent.body_digest
                or record.get("provider_moment_digest")
                != recovered.intent.provider_moment_digest
                or record.get("provider_source_timestamp")
                != recovered.intent.provider_source_timestamp
            ):
                raise DurableContingencyStateError(
                    "exact_recovery_claim_lineage_required"
                )
            record["status"] = next_status
            record["outcome_recorded_at"] = _canonical_decimal(
                self._now(),
                "outcome_recorded_at",
            )
            self._write_locked(state)

    def consume_and_call(
        self,
        recovered: RecoveredContingencyPermit,
        *,
        method: str,
        path: str,
        body: Mapping[str, Any],
        transport: Callable[[], _T],
    ) -> _T:
        """Persist SUBMITTING before transport; any uncertainty reconciles."""

        if not isinstance(recovered, RecoveredContingencyPermit):
            raise TypeError("recovered_contingency_permit_required")
        self._set_outcome(
            recovered,
            expected_status="PERMIT_PREPARED",
            next_status="SUBMITTING",
        )
        try:
            result = self.boundary.consume_and_call(
                recovered.permit,
                method=method,
                path=path,
                body=body,
                transport=transport,
            )
        except EconomicGovernanceBlocked:
            self._set_outcome(
                recovered,
                expected_status="SUBMITTING",
                next_status="BURNED",
            )
            raise
        except Exception:
            self._set_outcome(
                recovered,
                expected_status="SUBMITTING",
                next_status="AMBIGUOUS",
            )
            raise
        self._set_outcome(
            recovered,
            expected_status="SUBMITTING",
            next_status="RETURNED",
        )
        return result

    def status(
        self,
        reference: DurableContingencyRecordRef,
    ) -> str:
        with self._lock():
            state = self._read_locked()
            record, _, _ = self._record_locked(state, reference)
            return _nonblank(record.get("status"), "recovery_status")


def bind_durable_contingency_recovery(
    *,
    adapter_id: str,
    trusted_adapter_ids: frozenset[str],
    boundary: EconomicGovernanceBoundary,
    store_path: Path | str,
    clock: Callable[[], float] = time.time,
    claim_ttl_s: float = 5.0,
) -> DurableContingencyRecovery:
    """Bind one explicitly allowlisted adapter at the composition root."""

    if not isinstance(trusted_adapter_ids, frozenset) or not trusted_adapter_ids:
        raise ValueError("trusted_adapter_ids_must_be_nonempty_frozenset")
    canonical_id = _nonblank(adapter_id, "adapter_id")
    allowlist = {
        _nonblank(value, "trusted_adapter_id").casefold()
        for value in trusted_adapter_ids
    }
    if canonical_id.casefold() not in allowlist:
        raise ValueError("durable_contingency_adapter_not_allowlisted")
    if not isinstance(boundary, EconomicGovernanceBoundary):
        raise TypeError("economic_governance_boundary_required")
    if not callable(clock):
        raise TypeError("clock_callable_required")
    try:
        claim_ttl = Decimal(str(claim_ttl_s))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError("finite_claim_ttl_required") from exc
    permit_ttl = getattr(boundary, "_permit_ttl", None)
    if (
        not claim_ttl.is_finite()
        or claim_ttl <= 0
        or not isinstance(permit_ttl, Decimal)
        or claim_ttl <= permit_ttl
    ):
        raise ValueError("claim_ttl_must_outlive_permit_ttl")
    return DurableContingencyRecovery(
        _factory_token=_FACTORY_TOKEN,
        adapter_id=canonical_id,
        boundary=boundary,
        store_path=Path(store_path),
        clock=clock,
        claim_ttl=claim_ttl,
    )


__all__ = [
    "DurableContingencyMaterial",
    "DurableContingencyRecordRef",
    "DurableContingencyRecovery",
    "DurableContingencyStateError",
    "RecoveredContingencyPermit",
    "bind_durable_contingency_recovery",
]

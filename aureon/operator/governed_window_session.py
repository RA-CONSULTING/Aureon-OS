"""Fail-closed browser-window handoff governance.

The desktop gateway deliberately binds one exact native window.  Browser tabs,
navigation and popups can legitimately change that identity, so this module
provides an explicit, policy-bound handoff rather than weakening the gateway's
exact-match rule.

The module is control-plane only.  It performs no GUI action, URL inspection,
network request or filesystem access.  Window discovery, process-lineage
inspection and atomic gateway rebinding are injected read-only/control-plane
interfaces, which also keeps the implementation hermetic in tests.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import re
import threading
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Callable, Mapping, Protocol, Sequence

from aureon.autonomous.aureon_governed_desktop_gateway import WindowInfo

POLICY_SCHEMA = "aureon-governed-window-session-policy-v1"
MAX_POLICY_TTL_SECONDS = 24 * 60 * 60
MAX_POLICY_HANDOFFS = 1_000
MAX_ENUMERATED_WINDOWS = 4_096
MIN_SIGNING_SECRET_BYTES = 32


class WindowSessionError(RuntimeError):
    """A stable, non-sensitive failure from the handoff control plane."""

    def __init__(self, code: str) -> None:
        self.code = str(code)
        super().__init__(self.code)


@dataclass(frozen=True)
class WindowCandidate:
    """One trusted enumerator result.

    ``origin_label`` is an opaque label asserted by the injected enumerator. It
    is intentionally not a URL and this module never tries to discover one.
    """

    window: WindowInfo
    origin_label: str

    def __post_init__(self) -> None:
        _validate_window(self.window)
        _nonempty_label("origin_label", self.origin_label)


@dataclass(frozen=True)
class GatewayWindowBinding:
    """Exact result required from an atomic gateway replacement."""

    binding_id: str
    window: WindowInfo

    def __post_init__(self) -> None:
        _nonempty_label("binding_id", self.binding_id)
        _validate_window(self.window)


class WindowEnumerator(Protocol):
    """Read-only native-window inventory."""

    def enumerate_windows(self) -> Sequence[WindowCandidate]:
        ...


class ProcessInspector(Protocol):
    """Read-only process-lineage decision supplied by the host."""

    def is_same_process_or_descendant(
        self,
        process_id: int,
        *,
        ancestor_process_id: int,
    ) -> bool:
        ...


class ExactWindowGateway(Protocol):
    """Atomic exact-window binding surface expected from a gateway adapter.

    A successful replacement must leave exactly the returned binding active.
    A failed replacement must preserve the previous binding unchanged.
    """

    def replace_target_window_binding(
        self,
        *,
        previous_binding_id: str | None,
        window: WindowInfo,
    ) -> GatewayWindowBinding:
        ...

    def release_target_window_binding(self, binding_id: str) -> None:
        ...


@dataclass(frozen=True)
class WindowSessionPolicy:
    """Signed authority for a single browser process family and origin label."""

    session_id: str
    nonce: str
    initial_window: WindowInfo
    root_process_id: int
    allowed_title_regex: str
    origin_label: str
    issued_at: datetime
    expires_at: datetime
    max_handoffs: int
    schema_version: str = POLICY_SCHEMA

    def canonical_payload(self) -> Mapping[str, object]:
        return {
            "allowed_title_regex": self.allowed_title_regex,
            "expires_at": _utc_iso(self.expires_at),
            "initial_window": _window_payload(self.initial_window),
            "issued_at": _utc_iso(self.issued_at),
            "max_handoffs": self.max_handoffs,
            "nonce": self.nonce,
            "origin_label": self.origin_label,
            "root_process_id": self.root_process_id,
            "schema_version": self.schema_version,
            "session_id": self.session_id,
        }


@dataclass(frozen=True)
class SignedWindowSessionPolicy:
    """Canonical policy plus its content hash and HMAC-SHA256 signature."""

    policy: WindowSessionPolicy
    policy_sha256: str
    signature_sha256: str


@dataclass(frozen=True)
class SessionWindowBinding:
    """The sole binding currently authorized by a governed session."""

    session_id: str
    binding_id: str
    policy_sha256: str
    generation: int
    handoff_count: int
    bound_at: datetime
    origin_label: str
    window: WindowInfo
    window_sha256: str

    def audit_dict(self) -> Mapping[str, object]:
        """Return an audit-safe snapshot without raw title or origin strings."""

        return {
            "binding_id": self.binding_id,
            "bound_at": _utc_iso(self.bound_at),
            "generation": self.generation,
            "handoff_count": self.handoff_count,
            "origin_label_sha256": _sha256_text(self.origin_label),
            "policy_sha256": self.policy_sha256,
            "session_id": self.session_id,
            "window": {
                "handle": self.window.handle,
                "process_id": self.window.process_id,
                "rect": {
                    "height": self.window.height,
                    "left": self.window.left,
                    "top": self.window.top,
                    "width": self.window.width,
                },
                "title_length": len(self.window.title),
                "title_sha256": _sha256_text(self.window.title),
            },
            "window_sha256": self.window_sha256,
        }


def sign_window_session_policy(
    policy: WindowSessionPolicy,
    signing_secret: bytes,
) -> SignedWindowSessionPolicy:
    """Sign a policy in memory with a runtime-only HMAC secret."""

    secret = _validate_secret(signing_secret)
    _validate_policy(policy)
    canonical = _canonical_policy_bytes(policy)
    return SignedWindowSessionPolicy(
        policy=policy,
        policy_sha256=hashlib.sha256(canonical).hexdigest(),
        signature_sha256=hmac.new(secret, canonical, hashlib.sha256).hexdigest(),
    )


def verify_window_session_policy(
    envelope: SignedWindowSessionPolicy,
    signing_secret: bytes,
    *,
    now: datetime,
) -> str:
    """Verify structure, hash, signature and validity time; return policy hash."""

    if not isinstance(envelope, SignedWindowSessionPolicy):
        raise WindowSessionError("signed_policy_required")
    secret = _validate_secret(signing_secret)
    _validate_policy(envelope.policy)
    canonical = _canonical_policy_bytes(envelope.policy)
    calculated_hash = hashlib.sha256(canonical).hexdigest()
    supplied_hash = _sha256_value("policy_sha256", envelope.policy_sha256)
    if not hmac.compare_digest(calculated_hash, supplied_hash):
        raise WindowSessionError("policy_hash_mismatch")
    calculated_signature = hmac.new(secret, canonical, hashlib.sha256).hexdigest()
    supplied_signature = _sha256_value("signature_sha256", envelope.signature_sha256)
    if not hmac.compare_digest(calculated_signature, supplied_signature):
        raise WindowSessionError("policy_signature_invalid")

    current = _aware_utc("now", now)
    issued_at = _aware_utc("issued_at", envelope.policy.issued_at)
    expires_at = _aware_utc("expires_at", envelope.policy.expires_at)
    if current < issued_at:
        raise WindowSessionError("policy_not_yet_valid")
    if current >= expires_at:
        raise WindowSessionError("policy_expired")
    return calculated_hash


def window_sha256(window: WindowInfo) -> str:
    """Hash the full native identity: handle, PID, title and rectangle."""

    _validate_window(window)
    payload = json.dumps(
        _window_payload(window),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


class GovernedWindowSession:
    """Authorize exact window replacements under one signed session policy."""

    def __init__(
        self,
        *,
        gateway: ExactWindowGateway,
        window_enumerator: WindowEnumerator,
        process_inspector: ProcessInspector,
        signed_policy: SignedWindowSessionPolicy,
        signing_secret: bytes,
        utc_now: Callable[[], datetime] | None = None,
    ) -> None:
        self._gateway = gateway
        self._window_enumerator = window_enumerator
        self._process_inspector = process_inspector
        self._signed_policy = signed_policy
        self._signing_secret = bytes(_validate_secret(signing_secret))
        self._utc_now = utc_now or (lambda: datetime.now(UTC))
        self._lock = threading.RLock()
        self._active: SessionWindowBinding | None = None
        self._handoff_count = 0
        self._closed = False

    @property
    def active_binding(self) -> SessionWindowBinding | None:
        """Return the last authorized snapshot without re-authorizing it."""

        with self._lock:
            return self._active

    @property
    def closed(self) -> bool:
        with self._lock:
            return self._closed

    def start(self) -> SessionWindowBinding:
        """Bind the exactly signed initial window from a fresh enumeration."""

        with self._lock:
            if self._closed:
                raise WindowSessionError("window_session_closed")
            if self._active is not None:
                raise WindowSessionError("window_session_already_started")
            policy_hash = self._verify_policy_locked(close_active_on_error=False)
            policy = self._signed_policy.policy
            candidates = self._enumerate_locked()
            initial_hash = window_sha256(policy.initial_window)
            exact = [item for item in candidates if window_sha256(item.window) == initial_hash]
            if len(exact) > 1:
                raise WindowSessionError("initial_window_ambiguous")
            if not exact:
                raise WindowSessionError("initial_window_not_found")
            candidate = exact[0]
            self._assert_allowed_locked(candidate)
            receipt = self._replace_locked(previous_binding_id=None, candidate=candidate)
            binding = self._session_binding(
                receipt=receipt,
                candidate=candidate,
                policy_hash=policy_hash,
                generation=0,
            )
            self._active = binding
            return binding

    def authorize_active_binding(self) -> SessionWindowBinding:
        """Re-read and authorize the exact current binding before an action."""

        with self._lock:
            self._require_open_active_locked()
            self._verify_policy_locked(close_active_on_error=True)
            active = self._active
            assert active is not None
            matches = [
                item
                for item in self._enumerate_locked()
                if item.window.handle == active.window.handle
            ]
            if len(matches) > 1:
                raise WindowSessionError("active_window_ambiguous")
            if not matches:
                raise WindowSessionError("active_window_not_found")
            candidate = matches[0]
            if window_sha256(candidate.window) != active.window_sha256:
                raise WindowSessionError("active_window_identity_changed_handoff_required")
            self._assert_allowed_locked(candidate)
            return active

    def handoff(
        self,
        *,
        expected_active_binding_id: str,
        expected_active_window_sha256: str,
        target_handle: int | None = None,
    ) -> SessionWindowBinding:
        """Atomically replace the active exact window after a fresh enumeration.

        The two expected values form a compare-and-swap guard.  Supplying a
        target handle is the normal popup/tab handoff path.  When omitted, the
        enumerated state must contain exactly one changed eligible candidate.
        """

        with self._lock:
            self._require_open_active_locked()
            policy_hash = self._verify_policy_locked(close_active_on_error=True)
            active = self._active
            assert active is not None
            if expected_active_binding_id != active.binding_id:
                raise WindowSessionError("active_binding_compare_and_swap_failed")
            expected_window_hash = _sha256_value(
                "expected_active_window_sha256",
                expected_active_window_sha256,
            )
            if not hmac.compare_digest(expected_window_hash, active.window_sha256):
                raise WindowSessionError("active_window_compare_and_swap_failed")
            policy = self._signed_policy.policy
            if self._handoff_count >= policy.max_handoffs:
                raise WindowSessionError("maximum_window_handoffs_reached")

            candidates = self._enumerate_locked()
            if target_handle is not None:
                _positive_int("target_handle", target_handle)
                selected = [item for item in candidates if item.window.handle == target_handle]
                if len(selected) > 1:
                    raise WindowSessionError("target_window_ambiguous")
                if not selected:
                    raise WindowSessionError("target_window_handle_not_found")
                candidate = selected[0]
                self._assert_allowed_locked(candidate)
                if window_sha256(candidate.window) == active.window_sha256:
                    raise WindowSessionError("window_handoff_no_identity_change")
            else:
                eligible: list[WindowCandidate] = []
                for item in candidates:
                    if window_sha256(item.window) == active.window_sha256:
                        continue
                    if self._is_allowed_locked(item):
                        eligible.append(item)
                if len(eligible) > 1:
                    raise WindowSessionError("target_window_ambiguous")
                if not eligible:
                    raise WindowSessionError("eligible_target_window_not_found")
                candidate = eligible[0]

            receipt = self._replace_locked(
                previous_binding_id=active.binding_id,
                candidate=candidate,
            )
            self._handoff_count += 1
            binding = self._session_binding(
                receipt=receipt,
                candidate=candidate,
                policy_hash=policy_hash,
                generation=active.generation + 1,
            )
            self._active = binding
            return binding

    def close(self) -> None:
        """Release the sole active gateway binding; idempotent."""

        with self._lock:
            if self._closed:
                return
            self._closed = True
            try:
                self._release_active_locked()
            finally:
                self._signing_secret = b""

    def _verify_policy_locked(self, *, close_active_on_error: bool) -> str:
        try:
            return verify_window_session_policy(
                self._signed_policy,
                self._signing_secret,
                now=self._utc_now(),
            )
        except WindowSessionError:
            if close_active_on_error and self._active is not None:
                self._closed = True
                try:
                    self._release_active_locked()
                finally:
                    self._signing_secret = b""
            raise

    def _require_open_active_locked(self) -> None:
        if self._closed:
            raise WindowSessionError("window_session_closed")
        if self._active is None:
            raise WindowSessionError("window_session_not_started")

    def _enumerate_locked(self) -> tuple[WindowCandidate, ...]:
        try:
            raw = tuple(self._window_enumerator.enumerate_windows())
        except Exception as exc:
            raise WindowSessionError("window_enumeration_failed") from exc
        if len(raw) > MAX_ENUMERATED_WINDOWS:
            raise WindowSessionError("window_enumeration_limit_exceeded")
        for candidate in raw:
            if not isinstance(candidate, WindowCandidate):
                raise WindowSessionError("invalid_window_candidate")
        return raw

    def _assert_allowed_locked(self, candidate: WindowCandidate) -> None:
        policy = self._signed_policy.policy
        if candidate.origin_label != policy.origin_label:
            raise WindowSessionError("window_origin_label_not_allowed")
        if re.fullmatch(policy.allowed_title_regex, candidate.window.title) is None:
            raise WindowSessionError("window_title_not_allowed")
        try:
            in_lineage = self._process_inspector.is_same_process_or_descendant(
                candidate.window.process_id,
                ancestor_process_id=policy.root_process_id,
            )
        except Exception as exc:
            raise WindowSessionError("process_lineage_inspection_failed") from exc
        if in_lineage is not True:
            raise WindowSessionError("window_process_lineage_not_allowed")

    def _is_allowed_locked(self, candidate: WindowCandidate) -> bool:
        try:
            self._assert_allowed_locked(candidate)
        except WindowSessionError as exc:
            if exc.code == "process_lineage_inspection_failed":
                raise
            return False
        return True

    def _replace_locked(
        self,
        *,
        previous_binding_id: str | None,
        candidate: WindowCandidate,
    ) -> GatewayWindowBinding:
        try:
            receipt = self._gateway.replace_target_window_binding(
                previous_binding_id=previous_binding_id,
                window=candidate.window,
            )
        except Exception as exc:
            raise WindowSessionError("gateway_window_replacement_failed") from exc
        if not isinstance(receipt, GatewayWindowBinding):
            self._poison_gateway_receipt_locked(None)
            raise WindowSessionError("gateway_window_binding_receipt_invalid")
        if previous_binding_id is not None and receipt.binding_id == previous_binding_id:
            self._poison_gateway_receipt_locked(receipt)
            raise WindowSessionError("gateway_window_binding_not_replaced")
        if receipt.window != candidate.window:
            self._poison_gateway_receipt_locked(receipt)
            raise WindowSessionError("gateway_window_binding_identity_mismatch")
        return receipt

    def _poison_gateway_receipt_locked(
        self,
        receipt: GatewayWindowBinding | None,
    ) -> None:
        if receipt is not None:
            try:
                self._gateway.release_target_window_binding(receipt.binding_id)
            except Exception:
                pass
        self._active = None
        self._closed = True

    def _session_binding(
        self,
        *,
        receipt: GatewayWindowBinding,
        candidate: WindowCandidate,
        policy_hash: str,
        generation: int,
    ) -> SessionWindowBinding:
        return SessionWindowBinding(
            session_id=self._signed_policy.policy.session_id,
            binding_id=receipt.binding_id,
            policy_sha256=policy_hash,
            generation=generation,
            handoff_count=self._handoff_count,
            bound_at=_aware_utc("now", self._utc_now()),
            origin_label=candidate.origin_label,
            window=candidate.window,
            window_sha256=window_sha256(candidate.window),
        )

    def _release_active_locked(self) -> None:
        active = self._active
        self._active = None
        if active is None:
            return
        try:
            self._gateway.release_target_window_binding(active.binding_id)
        except Exception as exc:
            raise WindowSessionError("gateway_window_release_failed") from exc


def _validate_policy(policy: WindowSessionPolicy) -> None:
    if not isinstance(policy, WindowSessionPolicy):
        raise WindowSessionError("window_session_policy_required")
    if policy.schema_version != POLICY_SCHEMA:
        raise WindowSessionError("window_session_policy_schema_invalid")
    _nonempty_label("session_id", policy.session_id)
    _nonempty_label("nonce", policy.nonce)
    _nonempty_label("origin_label", policy.origin_label)
    _validate_window(policy.initial_window)
    _positive_int("root_process_id", policy.root_process_id)
    if policy.root_process_id != policy.initial_window.process_id:
        raise WindowSessionError("root_process_must_match_initial_window")
    pattern = _nonempty_label("allowed_title_regex", policy.allowed_title_regex)
    if len(pattern) > 512:
        raise WindowSessionError("allowed_title_regex_too_long")
    try:
        re.compile(pattern)
    except re.error as exc:
        raise WindowSessionError("allowed_title_regex_invalid") from exc
    issued_at = _aware_utc("issued_at", policy.issued_at)
    expires_at = _aware_utc("expires_at", policy.expires_at)
    ttl = expires_at - issued_at
    if ttl <= timedelta(0):
        raise WindowSessionError("policy_ttl_must_be_positive")
    if ttl > timedelta(seconds=MAX_POLICY_TTL_SECONDS):
        raise WindowSessionError("policy_ttl_exceeds_limit")
    if isinstance(policy.max_handoffs, bool) or not isinstance(policy.max_handoffs, int):
        raise WindowSessionError("max_handoffs_must_be_integer")
    if policy.max_handoffs < 0 or policy.max_handoffs > MAX_POLICY_HANDOFFS:
        raise WindowSessionError("max_handoffs_out_of_range")


def _validate_secret(signing_secret: bytes) -> bytes:
    if not isinstance(signing_secret, bytes):
        raise WindowSessionError("signing_secret_bytes_required")
    if len(signing_secret) < MIN_SIGNING_SECRET_BYTES:
        raise WindowSessionError("signing_secret_too_short")
    return signing_secret


def _validate_window(window: WindowInfo) -> None:
    if not isinstance(window, WindowInfo):
        raise WindowSessionError("window_info_required")
    _positive_int("window_handle", window.handle)
    _positive_int("window_process_id", window.process_id)
    _nonempty_label("window_title", window.title)
    for name, value in (("window_left", window.left), ("window_top", window.top)):
        if isinstance(value, bool) or not isinstance(value, int):
            raise WindowSessionError(f"{name}_must_be_integer")
    _positive_int("window_width", window.width)
    _positive_int("window_height", window.height)


def _window_payload(window: WindowInfo) -> Mapping[str, object]:
    _validate_window(window)
    return {
        "handle": window.handle,
        "process_id": window.process_id,
        "rect": {
            "height": window.height,
            "left": window.left,
            "top": window.top,
            "width": window.width,
        },
        "title": window.title,
    }


def _canonical_policy_bytes(policy: WindowSessionPolicy) -> bytes:
    return json.dumps(
        policy.canonical_payload(),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _positive_int(name: str, value: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise WindowSessionError(f"{name}_must_be_positive_integer")
    return value


def _nonempty_label(name: str, value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise WindowSessionError(f"{name}_required")
    if len(value) > 1_024:
        raise WindowSessionError(f"{name}_too_long")
    return value


def _aware_utc(name: str, value: datetime) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise WindowSessionError(f"{name}_must_be_timezone_aware")
    return value.astimezone(UTC)


def _utc_iso(value: datetime) -> str:
    return _aware_utc("datetime", value).isoformat().replace("+00:00", "Z")


def _sha256_value(name: str, value: str) -> str:
    if not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise WindowSessionError(f"{name}_must_be_lowercase_sha256")
    return value


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()

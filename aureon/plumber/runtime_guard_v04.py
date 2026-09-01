"""Fail-closed Python runtime effect guard for the Aureon Plumber.

This module is a local reference boundary, not a process sandbox.  Once
explicitly installed it uses CPython audit events to deny covered mutations
and post-install file opens unless the current synchronous handler was selected
by an exact, current v0.3
dispatch and its signed command commits to an exact v0.4 effect manifest.

Denied attempts are represented only by bounded metadata commitments.  An
exact :class:`LocalOSProtectionBoundary` turns that metadata into HNC
quarantine evidence; raw audit arguments are never retained or returned.

Python objects remain introspectable and privileged/native code can bypass
Python audit hooks.  JavaScript, child runtimes, remote authority isolation,
durable replay state, OS policy, pre-opened descriptors/sockets, memory maps,
and inbound socket payloads are outside this module.  Earlier audit hooks see
an event before this hook and therefore remain part of the trusted bootstrap.
Consequently all types here remain ``production_ready = False``.
"""

from __future__ import annotations

import hashlib
import os
import re
import secrets
import sys
import threading
from collections.abc import Callable, Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Final

from .audit import assert_public_summary_safe
from .crypto import canonical_json_bytes, decode_canonical_json, domain_hash
from .os_protection import LocalOSProtectionBoundary, QuarantinedHNC
from .production_release_broker_v03 import (
    DispatchClaimV03,
    ProductionReleaseVerifierV03,
    ReleaseCommandV03,
    ReviewAuthorizationV03,
    decode_dispatch_claim_v03,
    decode_release_command_v03,
    decode_review_authorization_v03,
)
from .schema import SchemaError, require_sha256

RUNTIME_EFFECT_MANIFEST_SCHEMA: Final = "aureon.plumber.runtime-effect-manifest.v04"
RUNTIME_EFFECT_RULE_SCHEMA: Final = "aureon.plumber.runtime-effect-rule.v04"
RUNTIME_GUARD_EXECUTION_SCHEMA: Final = "aureon.plumber.runtime-guard-execution.v04"
RUNTIME_GUARD_PREFLIGHT_SCHEMA: Final = "aureon.plumber.runtime-guard-preflight.v04"
RUNTIME_GUARD_LIFECYCLE_SCHEMA: Final = "aureon.plumber.runtime-guard-lifecycle.v04"
RUNTIME_INTRUSION_SCHEMA: Final = "aureon.plumber.runtime-intrusion.v04"
RUNTIME_INTRUSION_PURPOSE: Final = "aureon.plumber.runtime-intrusion-quarantine.v04"

_MAX_RULES: Final = 128
_MAX_RULE_USES: Final = 1024
_MAX_TOTAL_RULE_USES: Final = 4096
_MAX_AUDIT_VALUE_DEPTH: Final = 12
_MAX_AUDIT_VALUE_NODES: Final = 4096
_MAX_AUDIT_TEXT_BYTES: Final = 64 * 1024
_MAX_AUDIT_AGGREGATE_BYTES: Final = 256 * 1024
_MAX_VIOLATION_RECEIPTS: Final = 4096
_MAX_CONSUMED_RELEASES: Final = 4096
_SAFE_INTEGER_MAX: Final = (1 << 53) - 1
_IDENTIFIER_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_AUDIT_EVENT_RE = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9._:/-]{0,127}$")
_INSTALL_PROBE_EVENT: Final = "aureon.runtime_guard_v04.install_probe"

_ALWAYS_PROTECTED_EVENTS: Final = frozenset(
    {
        "_thread.start_new_thread",
        "code.__new__",
        "compile",
        "cpython.PyInterpreterState_New",
        "ctypes.PyObj_FromPtr",
        "ctypes.addressof",
        "ctypes.call_function",
        "ctypes.cdata",
        "ctypes.cdata/buffer",
        "ctypes.create_string_buffer",
        "ctypes.create_unicode_buffer",
        "ctypes.dlopen",
        "ctypes.dlsym",
        "ctypes.dlsym/handle",
        "ctypes.set_errno",
        "ctypes.set_exception",
        "ctypes.set_last_error",
        "ctypes.string_at",
        "ctypes.wstring_at",
        "exec",
        "ftplib.connect",
        "ftplib.sendcmd",
        "function.__new__",
        "http.client.connect",
        "http.client.send",
        "import",
        "imaplib.open",
        "imaplib.send",
        "marshal.load",
        "marshal.loads",
        "mmap.__new__",
        "nntplib.connect",
        "nntplib.putline",
        "os.add_dll_directory",
        "os.chdir",
        "os.chflags",
        "os.chmod",
        "os.chown",
        "os.exec",
        "os.fork",
        "os.forkpty",
        "os.kill",
        "os.killpg",
        "os.link",
        "os.lockf",
        "os.mkdir",
        "os.posix_spawn",
        "os.putenv",
        "os.remove",
        "os.removexattr",
        "os.rename",
        "os.rmdir",
        "os.startfile",
        "os.startfile/2",
        "os.spawn",
        "os.setxattr",
        "os.symlink",
        "os.system",
        "os.truncate",
        "os.unsetenv",
        "os.utime",
        "pickle.find_class",
        "poplib.connect",
        "poplib.putline",
        "shutil.copyfile",
        "shutil.chown",
        "shutil.copymode",
        "shutil.copystat",
        "shutil.copytree",
        "shutil.make_archive",
        "shutil.move",
        "shutil.rmtree",
        "shutil.unpack_archive",
        "smtplib.connect",
        "smtplib.send",
        "socket.__new__",
        "socket.bind",
        "socket.connect",
        "socket.getaddrinfo",
        "socket.gethostbyaddr",
        "socket.gethostbyname",
        "socket.gethostname",
        "socket.getnameinfo",
        "socket.getservbyname",
        "socket.getservbyport",
        "socket.sendmsg",
        "socket.sendto",
        "socket.sethostname",
        "sqlite3.connect",
        "sqlite3.connect/handle",
        "sqlite3.enable_load_extension",
        "sqlite3.load_extension",
        "subprocess.Popen",
        "sys.addaudithook",
        "sys.setprofile",
        "sys.settrace",
        "telnetlib.Telnet.open",
        "telnetlib.Telnet.write",
        "urllib.Request",
        "webbrowser.open",
        "winreg.ConnectRegistry",
        "winreg.CreateKey",
        "winreg.DeleteKey",
        "winreg.DeleteValue",
        "winreg.DisableReflectionKey",
        "winreg.EnableReflectionKey",
        "winreg.LoadKey",
        "winreg.SaveKey",
        "winreg.SetValue",
    }
)
_DENY_ONLY_EVENT_MINIMUM: Final = frozenset(
    {
        "_thread.start_new_thread",
        "open",
        "code.__new__",
        "compile",
        "cpython.PyInterpreterState_New",
        "ctypes.PyObj_FromPtr",
        "ctypes.addressof",
        "ctypes.call_function",
        "ctypes.cdata",
        "ctypes.cdata/buffer",
        "ctypes.create_string_buffer",
        "ctypes.create_unicode_buffer",
        "ctypes.dlopen",
        "ctypes.dlsym",
        "ctypes.dlsym/handle",
        "ctypes.set_errno",
        "ctypes.set_exception",
        "ctypes.set_last_error",
        "ctypes.string_at",
        "ctypes.wstring_at",
        "exec",
        "function.__new__",
        "http.client.connect",
        "http.client.send",
        "import",
        "marshal.load",
        "marshal.loads",
        "mmap.__new__",
        "os.add_dll_directory",
        "os.chdir",
        "os.exec",
        "os.fork",
        "os.forkpty",
        "os.kill",
        "os.killpg",
        "os.lockf",
        "os.posix_spawn",
        "os.startfile",
        "os.startfile/2",
        "os.spawn",
        "os.system",
        "pickle.find_class",
        "socket.__new__",
        "socket.bind",
        "socket.connect",
        "socket.getaddrinfo",
        "socket.gethostbyaddr",
        "socket.gethostbyname",
        "socket.gethostname",
        "socket.getnameinfo",
        "socket.getservbyname",
        "socket.getservbyport",
        "socket.sendmsg",
        "socket.sendto",
        "socket.sethostname",
        "sqlite3.connect",
        "sqlite3.connect/handle",
        "sqlite3.enable_load_extension",
        "sqlite3.load_extension",
        "subprocess.Popen",
        "sys.addaudithook",
        "sys.setprofile",
        "sys.settrace",
        "urllib.Request",
        "winreg.ConnectRegistry",
        "winreg.DisableReflectionKey",
        "winreg.EnableReflectionKey",
        "winreg.LoadKey",
        "winreg.SaveKey",
    }
)
_SUPPORTED_RULE_EVENTS: Final = frozenset({"open", *_ALWAYS_PROTECTED_EVENTS})
_AUTHORIZABLE_EVENTS: Final = frozenset({"os.mkdir"})
_NON_AUTHORIZABLE_EVENTS: Final = (
    _SUPPORTED_RULE_EVENTS - _AUTHORIZABLE_EVENTS
)
if not _DENY_ONLY_EVENT_MINIMUM <= _NON_AUTHORIZABLE_EVENTS:
    raise RuntimeError("runtime_guard_deny_only_event_invariant_failed")
_SOCKET_INSTANCE_EVENTS: Final = frozenset(
    {"socket.bind", "socket.connect", "socket.sendto"}
)


class RuntimeGuardError(ValueError):
    """Stable, non-secret runtime guard contract failure."""

    def __init__(self, code: str) -> None:
        self.code = str(code)
        super().__init__(self.code)


class RuntimeGuardViolation(PermissionError):
    """A covered runtime effect was denied before the operation."""

    def __init__(self, code: str) -> None:
        self.code = str(code)
        super().__init__(self.code)


def _identifier(value: object, *, code: str) -> str:
    if type(value) is not str or _IDENTIFIER_RE.fullmatch(value) is None:
        raise RuntimeGuardError(code)
    return value


def _audit_event_identifier(value: object, *, code: str) -> str:
    if type(value) is not str or _AUDIT_EVENT_RE.fullmatch(value) is None:
        raise RuntimeGuardError(code)
    return value


def _sha256(value: object, *, code: str) -> str:
    if type(value) is not str:
        raise RuntimeGuardError(code)
    try:
        return require_sha256(value, field=code)
    except SchemaError as exc:
        raise RuntimeGuardError(code) from exc


def _uint(value: object, *, code: str) -> int:
    if type(value) is not int or value < 0 or value > _SAFE_INTEGER_MAX:
        raise RuntimeGuardError(code)
    return value


def _safe_integer(value: object, *, code: str) -> int:
    if (
        type(value) is not int
        or value < -_SAFE_INTEGER_MAX
        or value > _SAFE_INTEGER_MAX
    ):
        raise RuntimeGuardError(code)
    return value


def _exact_mapping(
    value: object,
    keys: set[str],
    *,
    code: str,
) -> dict[str, Any]:
    if not isinstance(value, Mapping) or set(value) != keys:
        raise RuntimeGuardError(code)
    return dict(value)


def _decode_mapping(data: bytes | str, *, code: str) -> dict[str, Any]:
    try:
        value = decode_canonical_json(
            data,
            require_mapping=True,
            max_bytes=_MAX_AUDIT_TEXT_BYTES,
        )
    except BaseException as exc:
        raise RuntimeGuardError(code) from exc
    if not isinstance(value, dict):  # pragma: no cover - decoder contract
        raise RuntimeGuardError(code)
    return value


def _hash_bytes(value: bytes) -> dict[str, Any]:
    if type(value) is not bytes:
        raise RuntimeGuardError("audit_argument_bytes_invalid")
    if len(value) > _MAX_AUDIT_TEXT_BYTES:
        raise RuntimeGuardError("audit_argument_bytes_invalid")
    return {
        "kind": "bytes",
        "size_bytes": len(value),
        "sha256": hashlib.sha256(value).hexdigest(),
    }


def _hash_text(value: str) -> dict[str, Any]:
    if type(value) is not str:
        raise RuntimeGuardError("audit_argument_text_invalid")
    if len(value) > _MAX_AUDIT_TEXT_BYTES or "\x00" in value:
        raise RuntimeGuardError("audit_argument_text_invalid")
    try:
        encoded = str.encode(value, "utf-8", errors="strict")
    except UnicodeEncodeError as exc:
        raise RuntimeGuardError("audit_argument_text_invalid") from exc
    if len(encoded) > _MAX_AUDIT_TEXT_BYTES:
        raise RuntimeGuardError("audit_argument_text_invalid")
    return {
        "kind": "text",
        "size_bytes": len(encoded),
        "sha256": hashlib.sha256(encoded).hexdigest(),
    }


def _snapshot_audit_value(
    value: object,
    *,
    depth: int = 0,
    remaining_nodes: list[int] | None = None,
    remaining_bytes: list[int] | None = None,
) -> Any:
    budget = remaining_nodes if remaining_nodes is not None else [_MAX_AUDIT_VALUE_NODES]
    byte_budget = (
        remaining_bytes
        if remaining_bytes is not None
        else [_MAX_AUDIT_AGGREGATE_BYTES]
    )
    budget[0] -= 1
    if budget[0] < 0 or depth > _MAX_AUDIT_VALUE_DEPTH:
        raise RuntimeGuardError("audit_argument_budget_exceeded")
    if value is None or type(value) is bool:
        return value
    if type(value) is int:
        return {
            "kind": "integer",
            "value": _safe_integer(value, code="audit_integer_invalid"),
        }
    if type(value) is str:
        snapshot = _hash_text(value)
        byte_budget[0] -= int(snapshot["size_bytes"])
        if byte_budget[0] < 0:
            raise RuntimeGuardError("audit_argument_budget_exceeded")
        return snapshot
    if type(value) is bytes:
        if len(value) > _MAX_AUDIT_TEXT_BYTES:
            raise RuntimeGuardError("audit_argument_bytes_invalid")
        byte_budget[0] -= len(value)
        if byte_budget[0] < 0:
            raise RuntimeGuardError("audit_argument_budget_exceeded")
        return _hash_bytes(value)
    if type(value) is dict:
        entries: list[dict[str, Any]] = []
        for key, item in value.items():
            if type(key) is not str:
                raise RuntimeGuardError("audit_mapping_key_invalid")
            key_snapshot = _hash_text(key)
            byte_budget[0] -= int(key_snapshot["size_bytes"])
            if byte_budget[0] < 0:
                raise RuntimeGuardError("audit_argument_budget_exceeded")
            entries.append(
                {
                    "key": key_snapshot,
                    "value": _snapshot_audit_value(
                        item,
                        depth=depth + 1,
                        remaining_nodes=budget,
                        remaining_bytes=byte_budget,
                    ),
                }
            )
        entries.sort(key=lambda entry: canonical_json_bytes(entry["key"]))
        return {"kind": "mapping", "entries": entries}
    if isinstance(value, (list, tuple)):
        if type(value) not in (list, tuple):
            raise RuntimeGuardError("audit_argument_type_unsupported")
        return {
            "kind": "sequence",
            "items": [
                _snapshot_audit_value(
                    item,
                    depth=depth + 1,
                    remaining_nodes=budget,
                    remaining_bytes=byte_budget,
                )
                for item in value
            ],
        }
    raise RuntimeGuardError("audit_argument_type_unsupported")


def _open_is_mutating(arguments: tuple[Any, ...]) -> bool:
    if len(arguments) < 3:
        return True
    mode = arguments[1]
    flags = arguments[2]
    if type(mode) is str and any(
        str.__contains__(mode, marker) for marker in "wax+"
    ):
        return True
    if type(flags) is int:
        write_flags = (
            os.O_WRONLY
            | os.O_RDWR
            | os.O_CREAT
            | os.O_TRUNC
            | os.O_APPEND
        )
        return bool(flags & write_flags)
    return mode is None or type(mode) is not str


def _open_access(arguments: tuple[Any, ...]) -> dict[str, bool]:
    mode = arguments[1] if len(arguments) > 1 else None
    flags = arguments[2] if len(arguments) > 2 else None
    if type(mode) is str:
        return {
            "append": str.__contains__(mode, "a"),
            "create": any(
                str.__contains__(mode, marker) for marker in "wax"
            ),
            "exclusive": str.__contains__(mode, "x"),
            "truncate": str.__contains__(mode, "w"),
            "update": str.__contains__(mode, "+"),
        }
    if type(flags) is int:
        return {
            "append": bool(flags & os.O_APPEND),
            "create": bool(flags & os.O_CREAT),
            "exclusive": bool(flags & os.O_EXCL),
            "truncate": bool(flags & os.O_TRUNC),
            "update": bool(flags & os.O_RDWR),
        }
    raise RuntimeGuardError("audit_open_access_invalid")


def _requires_protection(event_name: str, arguments: tuple[Any, ...]) -> bool:
    if event_name == "open":
        return True
    return event_name in _ALWAYS_PROTECTED_EVENTS


def _event_resource(event_name: str, arguments: tuple[Any, ...]) -> dict[str, Any]:
    _audit_event_identifier(event_name, code="audit_event_name_invalid")
    if event_name not in _SUPPORTED_RULE_EVENTS:
        raise RuntimeGuardError("audit_event_not_guarded")
    if event_name == "open":
        if not arguments:
            raise RuntimeGuardError("audit_open_arguments_invalid")
        target = arguments[0]
        if type(target) is str:
            target_text = target
        else:
            raise RuntimeGuardError("audit_open_target_not_absolute_text")
        if not os.path.isabs(target_text):
            raise RuntimeGuardError("audit_open_target_not_absolute_text")
        return {
            "event_name": event_name,
            "target": _snapshot_audit_value(target_text),
            "access": _open_access(arguments),
        }
    if event_name == "os.mkdir" and (
        len(arguments) != 3
        or type(arguments[0]) is not str
        or not os.path.isabs(arguments[0])
        or type(arguments[1]) is not int
        or arguments[1] < 0
        or arguments[1] > 0o7777
        or type(arguments[2]) is not int
        or arguments[2] != -1
    ):
        raise RuntimeGuardError("audit_mkdir_arguments_invalid")
    selected = arguments[1:] if event_name in _SOCKET_INSTANCE_EVENTS else arguments
    return {
        "event_name": event_name,
        "arguments": _snapshot_audit_value(selected),
    }


def audit_event_resource_commitment_v04(
    event_name: str,
    arguments: tuple[Any, ...],
) -> str:
    """Return an opaque resource commitment for one CPython audit event.

    For ``open`` the commitment binds the exact target and normalized mutation
    semantics.  Raw ``open`` remains non-authorizable because later handle
    writes are not audited.  Socket-instance commitments ignore the
    process-local socket object and bind the remaining audited arguments.
    Network, native-loader, thread, and child-process events are observable but
    never manifest-authorizable in this Python reference layer.
    """

    if type(arguments) is not tuple:
        raise RuntimeGuardError("audit_arguments_tuple_required")
    return domain_hash(
        "AUREON-PLUMBER-V04-AUDIT-RESOURCE",
        _event_resource(event_name, arguments),
    )


@dataclass(frozen=True, slots=True)
class AuditEffectRuleV04:
    event_name: str
    resource_commitment: str
    max_uses: int
    schema: str = RUNTIME_EFFECT_RULE_SCHEMA

    def __post_init__(self) -> None:
        if self.schema != RUNTIME_EFFECT_RULE_SCHEMA:
            raise RuntimeGuardError("runtime_effect_rule_schema_invalid")
        _audit_event_identifier(
            self.event_name,
            code="runtime_effect_event_invalid",
        )
        if (
            self.event_name not in _SUPPORTED_RULE_EVENTS
            or self.event_name not in _AUTHORIZABLE_EVENTS
        ):
            raise RuntimeGuardError("runtime_effect_event_not_authorizable")
        _sha256(self.resource_commitment, code="runtime_effect_resource_invalid")
        uses = _uint(self.max_uses, code="runtime_effect_max_uses_invalid")
        if uses < 1 or uses > _MAX_RULE_USES:
            raise RuntimeGuardError("runtime_effect_max_uses_invalid")

    def wire_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "event_name": self.event_name,
            "resource_commitment": self.resource_commitment,
            "max_uses": self.max_uses,
        }


@dataclass(frozen=True, slots=True)
class RuntimeEffectManifestV04:
    effect_id: str
    capability_id: str
    runtime_measurement_sha256: str
    operations: tuple[AuditEffectRuleV04, ...]
    schema: str = RUNTIME_EFFECT_MANIFEST_SCHEMA

    def __post_init__(self) -> None:
        if self.schema != RUNTIME_EFFECT_MANIFEST_SCHEMA:
            raise RuntimeGuardError("runtime_effect_manifest_schema_invalid")
        _sha256(self.effect_id, code="runtime_effect_id_invalid")
        _sha256(self.capability_id, code="runtime_capability_id_invalid")
        _sha256(
            self.runtime_measurement_sha256,
            code="runtime_measurement_invalid",
        )
        if (
            type(self.operations) is not tuple
            or not self.operations
            or len(self.operations) > _MAX_RULES
            or any(type(item) is not AuditEffectRuleV04 for item in self.operations)
        ):
            raise RuntimeGuardError("runtime_effect_operations_invalid")
        keys = [
            (item.event_name, item.resource_commitment)
            for item in self.operations
        ]
        if keys != sorted(keys) or len(keys) != len(set(keys)):
            raise RuntimeGuardError("runtime_effect_operations_not_canonical")
        if sum(item.max_uses for item in self.operations) > _MAX_TOTAL_RULE_USES:
            raise RuntimeGuardError("runtime_effect_total_uses_invalid")

    def wire_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "effect_id": self.effect_id,
            "capability_id": self.capability_id,
            "runtime_measurement_sha256": self.runtime_measurement_sha256,
            "operations": [item.wire_dict() for item in self.operations],
        }

    @property
    def commitment(self) -> str:
        return domain_hash(
            "AUREON-PLUMBER-V04-RUNTIME-EFFECT-MANIFEST",
            self.wire_dict(),
        )


def decode_runtime_effect_manifest_v04(data: bytes | str) -> RuntimeEffectManifestV04:
    payload = _exact_mapping(
        _decode_mapping(data, code="runtime_effect_manifest_wire_invalid"),
        {
            "schema",
            "effect_id",
            "capability_id",
            "runtime_measurement_sha256",
            "operations",
        },
        code="runtime_effect_manifest_shape_invalid",
    )
    raw_operations = payload["operations"]
    if not isinstance(raw_operations, list) or len(raw_operations) > _MAX_RULES:
        raise RuntimeGuardError("runtime_effect_operations_invalid")
    operations: list[AuditEffectRuleV04] = []
    for value in raw_operations:
        rule = _exact_mapping(
            value,
            {"schema", "event_name", "resource_commitment", "max_uses"},
            code="runtime_effect_rule_shape_invalid",
        )
        try:
            operations.append(AuditEffectRuleV04(**rule))
        except (TypeError, ValueError) as exc:
            if isinstance(exc, RuntimeGuardError):
                raise
            raise RuntimeGuardError("runtime_effect_rule_shape_invalid") from exc
    payload["operations"] = tuple(operations)
    try:
        return RuntimeEffectManifestV04(**payload)
    except (TypeError, ValueError) as exc:
        if isinstance(exc, RuntimeGuardError):
            raise
        raise RuntimeGuardError("runtime_effect_manifest_shape_invalid") from exc


@dataclass(frozen=True, slots=True)
class GuardedRuntimeCapabilityV04:
    capability_id: str
    capability_measurement_sha256: str
    handler: Callable[[], object]

    def __post_init__(self) -> None:
        _sha256(self.capability_id, code="runtime_capability_id_invalid")
        _sha256(
            self.capability_measurement_sha256,
            code="runtime_capability_measurement_invalid",
        )
        if not callable(self.handler):
            raise RuntimeGuardError("runtime_capability_handler_invalid")


def _reject_content(_view: memoryview) -> bool:
    return False


class HNCRuntimeViolationRecorderV04:
    """Bounded, in-memory HNC quarantine evidence for denied audit events."""

    production_ready = False

    def __init__(
        self,
        *,
        boundary: LocalOSProtectionBoundary,
        max_receipts: int = 1024,
        require_durable_evidence: bool = False,
    ) -> None:
        if type(boundary) is not LocalOSProtectionBoundary:
            raise RuntimeGuardError("exact_local_os_protection_boundary_required")
        limit = _uint(max_receipts, code="runtime_violation_capacity_invalid")
        if limit < 1 or limit > _MAX_VIOLATION_RECEIPTS:
            raise RuntimeGuardError("runtime_violation_capacity_invalid")
        if type(require_durable_evidence) is not bool:
            raise RuntimeGuardError("runtime_durable_evidence_policy_invalid")
        self._boundary = boundary
        self._max_receipts = limit
        self._require_durable_evidence = require_durable_evidence
        self._receipts: list[dict[str, Any]] = []
        self._reserved_receipts = 0
        self._sequence = 0
        self._preflight: dict[str, Any] | None = None
        self._terminal_failure_code: str | None = None
        self._runtime_guard_sealed = False
        self._runtime_guard_owner_token: str | None = None
        self._runtime_guard_boundary_generation: int | None = None
        self._runtime_guard_lifecycle_generation = 0
        self._runtime_lifecycle_lock = threading.RLock()
        self._lock = threading.RLock()

    def _mark_terminal_locked(self, code: str) -> None:
        selected = _identifier(code, code="runtime_intrusion_terminal_code_invalid")
        if self._terminal_failure_code is None:
            self._runtime_guard_lifecycle_generation += 1
            self._terminal_failure_code = selected

    def preflight(self) -> dict[str, Any]:
        """Warm and prove the commitment-only HNC quarantine path."""

        with self._runtime_lifecycle_lock, self._lock:
            if self._preflight is not None:
                cached = dict(self._preflight)
                if self._terminal_failure_code is not None:
                    cached["ready"] = False
                    cached["reason_code"] = self._terminal_failure_code
                    return cached
                remaining_required = max(
                    0,
                    self._max_receipts
                    - len(self._receipts)
                    - self._reserved_receipts,
                )
                key = self._boundary.key_preflight()
                boundary_summary = self._boundary.public_summary()
                maximum = boundary_summary.get("max_quarantine_evidence")
                used = boundary_summary.get("quarantine_evidence_count")
                local_available = (
                    max(0, maximum - used)
                    if type(maximum) is int and type(used) is int
                    else 0
                )
                cached["hnc_key_ready"] = key.get("ready") is True
                cached["hnc_quarantine_capacity_after_probe"] = local_available
                cached["hnc_quarantine_capacity_backed"] = (
                    local_available >= remaining_required
                )
                if key.get("ready") is not True:
                    self._mark_terminal_locked("runtime_hnc_key_unavailable")
                elif local_available < remaining_required:
                    self._mark_terminal_locked(
                        "runtime_hnc_quarantine_capacity_insufficient"
                    )
                durable_configured = (
                    boundary_summary.get(
                        "durable_quarantine_evidence_configured"
                    )
                    is True
                )
                if (
                    self._terminal_failure_code is None
                    and (self._require_durable_evidence or durable_configured)
                ):
                    try:
                        durable = (
                            self._boundary.durable_quarantine_evidence_preflight()
                        )
                        available = durable.get("remaining_violation_capacity")
                        durable_ready = durable.get("ready") is True
                        capacity_backed = (
                            type(available) is int
                            and available >= remaining_required
                        )
                        cached["durable_hnc_evidence_ready"] = durable_ready
                        cached["durable_hnc_capacity_backed"] = capacity_backed
                        cached["durable_hnc_capacity_after_probe"] = (
                            available if type(available) is int else 0
                        )
                        if not durable_ready or not capacity_backed:
                            failure_code = (
                                str(
                                    durable.get("reason_code")
                                    or "runtime_durable_hnc_evidence_not_ready"
                                )
                                if not durable_ready
                                else "runtime_durable_hnc_capacity_insufficient"
                            )
                            self._mark_terminal_locked(failure_code)
                    except BaseException:
                        boundary_summary = self._boundary.public_summary()
                        self._mark_terminal_locked(
                            str(
                                boundary_summary.get(
                                    "durable_quarantine_evidence_failure_code"
                                )
                                or "runtime_durable_hnc_evidence_preflight_failed"
                            )
                        )
                if self._terminal_failure_code is not None:
                    cached["ready"] = False
                    cached["reason_code"] = self._terminal_failure_code
                return cached
            key = self._boundary.key_preflight()
            ready = key.get("ready") is True
            hnc_evidence_ready = False
            capacity_backed = False
            durable_evidence_ready = False
            durable_capacity_backed = False
            durable_available_before = 0
            durable_available_after = 0
            available_before = 0
            available_after = 0
            reason_code = str(key.get("reason_code") or "runtime_hnc_key_unavailable")
            if self._require_durable_evidence:
                try:
                    durable_before = self._boundary.durable_quarantine_evidence_preflight()
                    durable_evidence_ready = durable_before.get("ready") is True
                    available = durable_before.get("remaining_violation_capacity")
                    if type(available) is int:
                        durable_available_before = max(0, available)
                    durable_capacity_backed = (
                        durable_evidence_ready
                        and durable_available_before >= self._max_receipts + 1
                    )
                    if not durable_evidence_ready:
                        reason_code = "runtime_durable_hnc_evidence_not_ready"
                    elif not durable_capacity_backed:
                        reason_code = "runtime_durable_hnc_capacity_insufficient"
                except BaseException:
                    durable_evidence_ready = False
                    durable_capacity_backed = False
                    reason_code = "runtime_durable_hnc_evidence_preflight_failed"
            else:
                durable_evidence_ready = False
                durable_capacity_backed = True
            if ready:
                boundary_before = self._boundary.public_summary()
                maximum = boundary_before.get("max_quarantine_evidence")
                used = boundary_before.get("quarantine_evidence_count")
                if type(maximum) is int and type(used) is int:
                    available_before = max(0, maximum - used)
                capacity_backed = (
                    available_before >= self._max_receipts + 1
                    and durable_capacity_backed
                )
                if not capacity_backed:
                    reason_code = (
                        "runtime_durable_hnc_capacity_insufficient"
                        if self._require_durable_evidence
                        and not durable_capacity_backed
                        else "runtime_hnc_quarantine_capacity_insufficient"
                    )
            if ready and capacity_backed:
                probe = canonical_json_bytes(
                    {
                        "schema": RUNTIME_GUARD_PREFLIGHT_SCHEMA,
                        "probe": "commitment-only-hnc-quarantine",
                        "production_ready": False,
                    }
                )
                try:
                    outcome = self._boundary.admit_external(
                        probe,
                        source_id="aureon:runtime-guard-v04",
                        ingress_kind="runtime-guard-preflight",
                        purpose=RUNTIME_INTRUSION_PURPOSE,
                        operator_aad={"preflight": True},
                        content_validator=_reject_content,
                    )
                    hnc_evidence_ready = (
                        type(outcome) is QuarantinedHNC
                        and outcome.hnc_evidence_binding is not None
                    )
                    boundary_after = self._boundary.public_summary()
                    maximum_after = boundary_after.get("max_quarantine_evidence")
                    used_after = boundary_after.get("quarantine_evidence_count")
                    if type(maximum_after) is int and type(used_after) is int:
                        available_after = max(0, maximum_after - used_after)
                    capacity_backed = available_after >= self._max_receipts
                    if self._require_durable_evidence:
                        try:
                            durable_after = (
                                self._boundary.durable_quarantine_evidence_preflight()
                            )
                            durable_evidence_ready = durable_after.get("ready") is True
                            durable_available = durable_after.get(
                                "remaining_violation_capacity"
                            )
                            if type(durable_available) is int:
                                durable_available_after = max(0, durable_available)
                            durable_capacity_backed = (
                                durable_evidence_ready
                                and durable_available_after >= self._max_receipts
                            )
                        except BaseException:
                            durable_evidence_ready = False
                            durable_capacity_backed = False
                    capacity_backed = capacity_backed and durable_capacity_backed
                    hnc_evidence_ready = hnc_evidence_ready and capacity_backed
                except BaseException:
                    hnc_evidence_ready = False
                    capacity_backed = False
                reason_code = (
                    "ready"
                    if hnc_evidence_ready
                    else (
                        "runtime_durable_hnc_evidence_preflight_failed"
                        if self._require_durable_evidence
                        and not durable_evidence_ready
                        else (
                            "runtime_durable_hnc_capacity_insufficient"
                            if self._require_durable_evidence
                            and not durable_capacity_backed
                            else (
                                "runtime_hnc_quarantine_capacity_insufficient"
                                if not capacity_backed
                                else "runtime_hnc_quarantine_preflight_failed"
                            )
                        )
                    )
                )
            result = {
                "schema": RUNTIME_GUARD_PREFLIGHT_SCHEMA,
                "ready": ready and hnc_evidence_ready,
                "reason_code": reason_code,
                "hnc_key_ready": ready,
                "hnc_quarantine_evidence_ready": hnc_evidence_ready,
                "hnc_quarantine_capacity_backed": capacity_backed,
                "hnc_quarantine_capacity_before_probe": available_before,
                "hnc_quarantine_capacity_after_probe": available_after,
                "required_violation_receipt_capacity": self._max_receipts,
                "durable_evidence_required": self._require_durable_evidence,
                "durable_hnc_evidence_ready": durable_evidence_ready,
                "durable_hnc_capacity_backed": durable_capacity_backed,
                "durable_hnc_capacity_before_probe": durable_available_before,
                "durable_hnc_capacity_after_probe": durable_available_after,
                "exclusive_boundary_custody_attested": False,
                "external_head_anchor_attested": False,
                "magic_star_durable_custody_attested": False,
                "raw_arguments_retained": False,
                "action_eligible": False,
                "economic_eligible": False,
                "production_ready": False,
            }
            assert_public_summary_safe(result)
            self._preflight = dict(result)
            return result

    def record(
        self,
        *,
        event_name: str,
        resource_commitment: str,
        reason_code: str,
    ) -> dict[str, Any]:
        """Record one violation while excluding guard lifecycle transitions."""

        with self._runtime_lifecycle_lock:
            return self._record_under_lifecycle(
                event_name=event_name,
                resource_commitment=resource_commitment,
                reason_code=reason_code,
            )

    def _record_under_lifecycle(
        self,
        *,
        event_name: str,
        resource_commitment: str,
        reason_code: str,
    ) -> dict[str, Any]:
        event = _audit_event_identifier(
            event_name,
            code="runtime_intrusion_event_invalid",
        )
        resource = _sha256(
            resource_commitment,
            code="runtime_intrusion_resource_invalid",
        )
        reason = _identifier(reason_code, code="runtime_intrusion_reason_invalid")
        with self._lock:
            if self._terminal_failure_code is not None:
                raise RuntimeGuardError(self._terminal_failure_code)
            if (
                len(self._receipts) + self._reserved_receipts
                >= self._max_receipts
            ):
                self._mark_terminal_locked("runtime_violation_capacity_exhausted")
                raise RuntimeGuardError(
                    self._terminal_failure_code
                    or "runtime_violation_capacity_exhausted"
                )
            self._reserved_receipts += 1
            self._sequence += 1
            sequence = self._sequence
        reservation_active = True
        try:
            metadata = {
                "schema": RUNTIME_INTRUSION_SCHEMA,
                "sequence": sequence,
                "event_name": event,
                "resource_commitment": resource,
                "reason_code": reason,
                "raw_arguments_retained": False,
                "audit_event_origin_attested": False,
                "effect_attempt_attested": False,
                "resource_commitment_confidentiality_attested": False,
                "resource_commitments_keyed": False,
                "action_eligible": False,
                "economic_eligible": False,
                "production_ready": False,
            }
            outcome = self._boundary.admit_external(
                canonical_json_bytes(metadata),
                source_id="aureon:runtime-guard-v04",
                ingress_kind="runtime-effect-violation",
                purpose=RUNTIME_INTRUSION_PURPOSE,
                operator_aad={
                    "event_name": event,
                    "resource_commitment": resource,
                    "reason_code": reason,
                },
                content_validator=_reject_content,
            )
            if (
                type(outcome) is not QuarantinedHNC
                or outcome.hnc_evidence_binding is None
            ):
                raise RuntimeGuardError("runtime_intrusion_hnc_evidence_unavailable")
            receipt = {
                **metadata,
                "hnc_quarantine_commitment": outcome.quarantine_commitment,
                "hnc_evidence_binding": outcome.hnc_evidence_binding.public_summary(),
            }
            assert_public_summary_safe(receipt)
            stored_receipt = _decode_mapping(
                canonical_json_bytes(receipt),
                code="runtime_intrusion_receipt_clone_failed",
            )
            with self._lock:
                self._reserved_receipts -= 1
                reservation_active = False
                self._receipts.append(stored_receipt)
                self._receipts.sort(key=lambda item: int(item["sequence"]))
                boundary_summary = self._boundary.public_summary()
                if boundary_summary.get("durable_quarantine_evidence_terminal") is True:
                    self._mark_terminal_locked(
                        str(
                            boundary_summary.get(
                                "durable_quarantine_evidence_failure_code"
                            )
                            or "runtime_intrusion_evidence_terminal"
                        )
                    )
                elif (
                    len(self._receipts) + self._reserved_receipts
                    >= self._max_receipts
                ):
                    self._mark_terminal_locked(
                        "runtime_violation_capacity_exhausted"
                    )
            return _decode_mapping(
                canonical_json_bytes(receipt),
                code="runtime_intrusion_receipt_clone_failed",
            )
        except BaseException as exc:
            with self._lock:
                if self._terminal_failure_code is None:
                    self._mark_terminal_locked(
                        exc.code
                        if isinstance(exc, RuntimeGuardError)
                        else "runtime_intrusion_evidence_recording_failed"
                    )
            raise
        finally:
            if reservation_active:
                with self._lock:
                    self._reserved_receipts -= 1

    def seal_for_runtime_guard_install(self) -> dict[str, Any]:
        """Pin the boundary/sink before an irreversible CPython hook install."""

        with self._runtime_lifecycle_lock:
            with self._lock:
                if self._terminal_failure_code is not None:
                    raise RuntimeGuardError(self._terminal_failure_code)
                if self._runtime_guard_sealed:
                    return self.validate_runtime_guard_seal(
                        self._runtime_guard_owner_token or "",
                        self._runtime_guard_lifecycle_generation,
                    )
            preflight = self.preflight()
            if preflight.get("ready") is not True:
                raise RuntimeGuardError("runtime_hnc_violation_recorder_not_ready")
            owner_token = secrets.token_hex(32)
            try:
                boundary_seal = self._boundary.seal_for_runtime_guard(owner_token)
                owner_sha256 = hashlib.sha256(
                    owner_token.encode("utf-8", errors="strict")
                ).hexdigest()
                boundary_generation = boundary_seal.get("lifecycle_generation")
                if (
                    boundary_seal.get("sealed") is not True
                    or boundary_seal.get("owner_token_sha256") != owner_sha256
                    or type(boundary_generation) is not int
                    or boundary_generation < 1
                    or boundary_seal.get("terminal") is not False
                    or boundary_seal.get("production_ready") is not False
                ):
                    raise RuntimeGuardError("runtime_guard_boundary_seal_invalid")
                confirmed = self.preflight()
                if confirmed.get("ready") is not True:
                    raise RuntimeGuardError(
                        "runtime_hnc_violation_recorder_not_ready"
                    )
            except BaseException as exc:
                with self._lock:
                    self._mark_terminal_locked(
                        exc.code
                        if isinstance(exc, RuntimeGuardError)
                        else "runtime_guard_lifecycle_seal_failed"
                    )
                raise RuntimeGuardError("runtime_guard_lifecycle_seal_failed") from exc
            with self._lock:
                self._runtime_guard_sealed = True
                self._runtime_guard_owner_token = owner_token
                self._runtime_guard_boundary_generation = boundary_generation
                self._runtime_guard_lifecycle_generation += 1
                result = {
                    "schema": RUNTIME_GUARD_LIFECYCLE_SCHEMA,
                    "sealed": True,
                    "owner_token_sha256": owner_sha256,
                    "lifecycle_generation": (
                        self._runtime_guard_lifecycle_generation
                    ),
                    "boundary_lifecycle_generation": boundary_generation,
                    "durable_evidence_required": self._require_durable_evidence,
                    "terminal": False,
                    "production_ready": False,
                }
            assert_public_summary_safe(result)
            return result

    def validate_runtime_guard_seal(
        self,
        owner_token: str,
        lifecycle_generation: int,
    ) -> dict[str, Any]:
        """Validate the recorder and boundary lifecycle generations exactly."""

        with self._runtime_lifecycle_lock:
            with self._lock:
                if (
                    not self._runtime_guard_sealed
                    or owner_token != self._runtime_guard_owner_token
                    or lifecycle_generation
                    != self._runtime_guard_lifecycle_generation
                    or self._terminal_failure_code is not None
                    or self._runtime_guard_boundary_generation is None
                ):
                    raise RuntimeGuardError("runtime_guard_lifecycle_invalid")
                boundary_generation = self._runtime_guard_boundary_generation
            try:
                boundary = self._boundary.validate_runtime_guard_seal(
                    owner_token,
                    boundary_generation,
                )
            except BaseException as exc:
                with self._lock:
                    self._mark_terminal_locked(
                        "runtime_guard_boundary_seal_validation_failed"
                    )
                raise RuntimeGuardError(
                    "runtime_guard_boundary_seal_validation_failed"
                ) from exc
            result = {
                "schema": RUNTIME_GUARD_LIFECYCLE_SCHEMA,
                "sealed": True,
                "owner_token_sha256": hashlib.sha256(
                    owner_token.encode("utf-8", errors="strict")
                ).hexdigest(),
                "lifecycle_generation": lifecycle_generation,
                "boundary_lifecycle_generation": boundary_generation,
                "boundary_seal_valid": boundary.get("sealed") is True,
                "terminal": False,
                "production_ready": False,
            }
            assert_public_summary_safe(result)
            return result

    def _runtime_guard_lease_identity(self) -> tuple[str, int]:
        """Return private lease material only to the exact in-process guard."""

        with self._runtime_lifecycle_lock, self._lock:
            if (
                not self._runtime_guard_sealed
                or self._runtime_guard_owner_token is None
                or self._runtime_guard_lifecycle_generation < 1
                or self._terminal_failure_code is not None
            ):
                raise RuntimeGuardError("runtime_guard_lifecycle_invalid")
            return (
                self._runtime_guard_owner_token,
                self._runtime_guard_lifecycle_generation,
            )

    @contextmanager
    def runtime_guard_decision_lease(
        self,
        owner_token: str,
        lifecycle_generation: int,
    ) -> Iterator[dict[str, Any]]:
        """Hold one exact non-appending lifecycle decision across all layers."""

        with self._runtime_lifecycle_lock:
            before = self.validate_runtime_guard_seal(
                owner_token,
                lifecycle_generation,
            )
            boundary_generation = self._runtime_guard_boundary_generation
            if boundary_generation is None:  # pragma: no cover - validated above
                raise RuntimeGuardError("runtime_guard_lifecycle_invalid")
            with self._boundary.runtime_guard_lifecycle_lease(
                owner_token,
                boundary_generation,
            ):
                yield before
            self.validate_runtime_guard_seal(
                owner_token,
                lifecycle_generation,
            )

    def terminal_failure_code(self) -> str | None:
        with self._runtime_lifecycle_lock, self._lock:
            return self._terminal_failure_code

    def receipts(self) -> tuple[dict[str, Any], ...]:
        with self._runtime_lifecycle_lock, self._lock:
            return tuple(
                _decode_mapping(
                    canonical_json_bytes(item),
                    code="runtime_intrusion_receipt_clone_failed",
                )
                for item in self._receipts
            )


@dataclass(slots=True)
class _ActivePermit:
    dispatch_commitment: str
    owner_thread_id: int
    remaining: dict[tuple[str, str], int]
    violation_generation_at_start: int
    violations: int = 0
    revoked: bool = False


_GLOBAL_GUARD_LOCK = threading.RLock()
_GLOBAL_GUARD: RuntimeAuditGuardV04 | None = None


class RuntimeAuditGuardV04:
    """Permanent, default-deny CPython audit hook for covered effects."""

    production_ready = False

    def __init__(
        self,
        *,
        verifier: ProductionReleaseVerifierV03,
        recorder: HNCRuntimeViolationRecorderV04,
        runtime_measurement_sha256: str,
        capabilities: Mapping[str, GuardedRuntimeCapabilityV04],
    ) -> None:
        if type(verifier) is not ProductionReleaseVerifierV03:
            raise RuntimeGuardError("production_release_verifier_required")
        if type(recorder) is not HNCRuntimeViolationRecorderV04:
            raise RuntimeGuardError("exact_runtime_violation_recorder_required")
        runtime_measurement = _sha256(
            runtime_measurement_sha256,
            code="runtime_measurement_invalid",
        )
        if not isinstance(capabilities, Mapping) or not capabilities:
            raise RuntimeGuardError("runtime_capability_registry_required")
        normalized: dict[str, GuardedRuntimeCapabilityV04] = {}
        for capability_id, capability in capabilities.items():
            if (
                type(capability) is not GuardedRuntimeCapabilityV04
                or capability_id != capability.capability_id
                or capability_id in normalized
            ):
                raise RuntimeGuardError("runtime_capability_registry_invalid")
            normalized[capability_id] = capability
        self._verifier = verifier
        self._recorder = recorder
        self._runtime_measurement_sha256 = runtime_measurement
        self._capabilities = normalized
        # Thread-local state deliberately does not propagate through copied
        # contextvars/async tasks.  A permit exists only for the synchronous
        # registered handler stack on the installing process thread.
        self._thread_state = threading.local()
        self._consumed_dispatches: set[str] = set()
        self._consumed_release_identities: set[tuple[str, str]] = set()
        self._violation_count = 0
        self._evidence_failure_count = 0
        self._evidence_terminal = False
        self._evidence_terminal_reason_code: str | None = None
        self._installed = False
        self._installation_failed_terminal = False
        self._install_probe: object | None = None
        self._install_probe_seen = False
        self._recorder_owner_token: str | None = None
        self._recorder_lifecycle_generation: int | None = None
        self._runtime_lifecycle_lock = threading.RLock()
        self._lock = threading.RLock()
        self._execution_lock = threading.Lock()
        self._active_execution_count = 0

    def install(self) -> dict[str, Any]:
        """Install one irreversible hook after proving HNC evidence readiness."""

        preflight = self._recorder.preflight()
        if preflight.get("ready") is not True:
            raise RuntimeGuardError("runtime_hnc_violation_recorder_not_ready")
        global _GLOBAL_GUARD
        with _GLOBAL_GUARD_LOCK:
            if _GLOBAL_GUARD is not None:
                if _GLOBAL_GUARD is self and self._installed:
                    return self.public_summary()
                if _GLOBAL_GUARD is self and self._installation_failed_terminal:
                    raise RuntimeGuardError(
                        "runtime_audit_guard_installation_terminal"
                    )
                raise RuntimeGuardError("runtime_audit_guard_already_installed")
            with self._runtime_lifecycle_lock:
                # Sealing is the installation credential.  The recorder pins
                # the durable sink under its own lock; from this point close is
                # rejected and the seal is revalidated for every capability.
                seal = self._recorder.seal_for_runtime_guard_install()
                if seal.get("sealed") is not True:
                    raise RuntimeGuardError("runtime_guard_lifecycle_seal_failed")
                owner_token, lifecycle_generation = (
                    self._recorder._runtime_guard_lease_identity()
                )
                self._recorder.validate_runtime_guard_seal(
                    owner_token,
                    lifecycle_generation,
                )
                self._recorder_owner_token = owner_token
                self._recorder_lifecycle_generation = lifecycle_generation
                # Hold the exact recorder/boundary/sink decision lease until
                # the irreversible hook is installed and proven.  A failed or
                # vetoed attempt remains process-terminal and leaves the sink
                # sealed; no close/DDL/terminal transition can occupy the old
                # preflight-to-install gap.
                with self._recorder.runtime_guard_decision_lease(
                    owner_token,
                    lifecycle_generation,
                ):
                    _GLOBAL_GUARD = self
                    self._install_probe = object()
                    self._install_probe_seen = False
                    try:
                        sys.addaudithook(self._audit_hook)
                        sys.audit(_INSTALL_PROBE_EVENT, self._install_probe)
                    except BaseException as exc:
                        self._install_probe = None
                        self._installation_failed_terminal = True
                        raise RuntimeGuardError(
                            "runtime_audit_guard_installation_unproven"
                        ) from exc
                    if not self._install_probe_seen:
                        # CPython permits an earlier audit hook to veto hook
                        # installation without returning an error.
                        self._install_probe = None
                        self._installation_failed_terminal = True
                        raise RuntimeGuardError(
                            "runtime_audit_guard_installation_unproven"
                        )
                    self._install_probe = None
                    self._installed = True
        return self.public_summary()

    @contextmanager
    def _runtime_guard_decision_lease(self) -> Iterator[dict[str, Any]]:
        """Hold the exact lifecycle only for one non-mutating decision."""

        with self._runtime_lifecycle_lock:
            owner_token = self._recorder_owner_token
            lifecycle_generation = self._recorder_lifecycle_generation
            if owner_token is None or lifecycle_generation is None:
                raise RuntimeGuardError("runtime_guard_lifecycle_invalid")
            body_failed = False
            try:
                with self._recorder.runtime_guard_decision_lease(
                    owner_token,
                    lifecycle_generation,
                ) as snapshot:
                    try:
                        yield snapshot
                    except BaseException:
                        body_failed = True
                        raise
            except BaseException as exc:
                if body_failed:
                    raise
                with self._lock:
                    self._evidence_terminal = True
                    self._evidence_terminal_reason_code = (
                        self._recorder.terminal_failure_code()
                        or "runtime_guard_lifecycle_invalid"
                    )
                raise RuntimeGuardError(
                    "runtime_intrusion_evidence_terminal"
                ) from exc

    def _record_violation(
        self,
        *,
        event_name: str,
        resource_commitment: str,
        permit: _ActivePermit | None,
    ) -> None:
        with self._runtime_lifecycle_lock:
            self._record_violation_under_lifecycle(
                event_name=event_name,
                resource_commitment=resource_commitment,
                permit=permit,
            )

    def _record_violation_under_lifecycle(
        self,
        *,
        event_name: str,
        resource_commitment: str,
        permit: _ActivePermit | None,
    ) -> None:
        with self._lock:
            self._violation_count += 1
            if permit is not None:
                permit.violations += 1
        previous_recording = getattr(self._thread_state, "recording", False)
        self._thread_state.recording = True
        try:
            self._recorder.record(
                event_name=event_name,
                resource_commitment=resource_commitment,
                reason_code="runtime_effect_not_magic_star_released",
            )
            terminal_code = self._recorder.terminal_failure_code()
            if terminal_code is not None:
                with self._lock:
                    self._evidence_terminal = True
                    self._evidence_terminal_reason_code = terminal_code
        except BaseException:
            with self._lock:
                self._evidence_failure_count += 1
                self._evidence_terminal = True
                self._evidence_terminal_reason_code = (
                    self._recorder.terminal_failure_code()
                    or "runtime_intrusion_evidence_recording_failed"
                )
        finally:
            self._thread_state.recording = previous_recording

    def _audit_hook(self, event_name: str, arguments: tuple[Any, ...]) -> None:
        # Each audit decision, not the arbitrary caller handler, is serialized
        # with recorder/boundary/sink lifecycle state.  The authorization
        # decision is therefore linearizable without deadlocking handlers that
        # join worker threads.
        with self._runtime_lifecycle_lock:
            self._audit_hook_under_lifecycle(event_name, arguments)

    def _audit_authorization_decision(
        self,
        *,
        event_name: str,
        resource_commitment: str,
        fingerprinted: bool,
        permit: _ActivePermit | None,
    ) -> tuple[bool, str | None]:
        """Atomically consume or reject one permit use under a lifecycle lease."""

        key = (event_name, resource_commitment)
        terminal_code = self._recorder.terminal_failure_code()
        with self._lock:
            if terminal_code is not None:
                self._evidence_terminal = True
                self._evidence_terminal_reason_code = terminal_code
            evidence_terminal = self._evidence_terminal
            generation_changed = (
                permit is not None
                and self._violation_count
                != permit.violation_generation_at_start
            )
            if permit is not None and (
                evidence_terminal or generation_changed or permit.revoked
            ):
                permit.revoked = True
                return (
                    False,
                    "runtime_intrusion_evidence_terminal"
                    if evidence_terminal
                    else "runtime_active_permit_revoked",
                )
            if (
                fingerprinted
                and event_name in _AUTHORIZABLE_EVENTS
                and permit is not None
                and permit.owner_thread_id == threading.get_ident()
                and permit.remaining.get(key, 0) > 0
            ):
                permit.remaining[key] -= 1
                return True, None
        return False, None

    def _audit_hook_under_lifecycle(
        self,
        event_name: str,
        arguments: tuple[Any, ...],
    ) -> None:
        if (
            event_name == _INSTALL_PROBE_EVENT
            and len(arguments) == 1
            and arguments[0] is self._install_probe
        ):
            self._install_probe_seen = True
            return
        if not _requires_protection(event_name, arguments):
            return
        if getattr(self._thread_state, "recording", False):
            raise RuntimeGuardViolation("runtime_intrusion_recorder_effect_forbidden")
        fingerprinted = True
        try:
            resource_commitment = audit_event_resource_commitment_v04(
                event_name,
                arguments,
            )
        except BaseException:
            fingerprinted = False
            resource_commitment = domain_hash(
                "AUREON-PLUMBER-V04-UNFINGERPRINTABLE-AUDIT-RESOURCE",
                {"event_name": event_name},
            )
        permit = getattr(self._thread_state, "active_permit", None)
        owner_token = self._recorder_owner_token
        lifecycle_generation = self._recorder_lifecycle_generation
        if owner_token is not None and lifecycle_generation is not None:
            try:
                # Decision-only: recording/appending happens after this exact
                # durable transaction has exited.
                with self._runtime_guard_decision_lease():
                    authorized, rejection_code = (
                        self._audit_authorization_decision(
                            event_name=event_name,
                            resource_commitment=resource_commitment,
                            fingerprinted=fingerprinted,
                            permit=permit,
                        )
                    )
            except BaseException:
                with self._lock:
                    self._evidence_terminal = True
                    self._evidence_terminal_reason_code = (
                        self._recorder.terminal_failure_code()
                        or "runtime_guard_lifecycle_invalid"
                    )
                    if permit is not None:
                        permit.revoked = True
                raise RuntimeGuardViolation(
                    "runtime_intrusion_evidence_terminal"
                ) from None
        else:
            # Pre-install direct tests still exercise the local decision state;
            # a process hook never reaches this branch after installation.
            authorized, rejection_code = self._audit_authorization_decision(
                event_name=event_name,
                resource_commitment=resource_commitment,
                fingerprinted=fingerprinted,
                permit=permit,
            )
        if rejection_code is not None:
            raise RuntimeGuardViolation(rejection_code)
        if authorized:
            return
        # Never append while the ledger decision transaction is open.
        self._record_violation_under_lifecycle(
            event_name=event_name,
            resource_commitment=resource_commitment,
            permit=permit,
        )
        raise RuntimeGuardViolation("runtime_effect_not_magic_star_released")

    def execute_released(
        self,
        command_wire: bytes,
        review_wire: bytes,
        dispatch_wire: bytes,
        manifest_wire: bytes,
    ) -> dict[str, Any]:
        """Serialize and execute one exact registered runtime capability."""

        terminal_code = self._recorder.terminal_failure_code()
        with self._lock:
            if terminal_code is not None:
                self._evidence_terminal = True
                self._evidence_terminal_reason_code = terminal_code
            if self._evidence_terminal:
                raise RuntimeGuardError("runtime_intrusion_evidence_terminal")
        if getattr(self._thread_state, "active_permit", None) is not None:
            raise RuntimeGuardError("nested_runtime_effect_forbidden")
        if not self._execution_lock.acquire(blocking=False):
            raise RuntimeGuardError("concurrent_runtime_effect_forbidden")
        with self._lock:
            self._active_execution_count += 1
        try:
            return self._execute_released_serial(
                command_wire,
                review_wire,
                dispatch_wire,
                manifest_wire,
            )
        finally:
            with self._lock:
                self._active_execution_count -= 1
            self._execution_lock.release()

    def _execute_released_serial(
        self,
        command_wire: bytes,
        review_wire: bytes,
        dispatch_wire: bytes,
        manifest_wire: bytes,
    ) -> dict[str, Any]:
        with self._runtime_lifecycle_lock, self._lock:
            if not self._installed:
                raise RuntimeGuardError("runtime_audit_guard_not_installed")
            owner_token = self._recorder_owner_token
            lifecycle_generation = self._recorder_lifecycle_generation
            if owner_token is None or lifecycle_generation is None:
                raise RuntimeGuardError("runtime_guard_lifecycle_invalid")
        return self._execute_released_serial_under_lifecycle(
            command_wire,
            review_wire,
            dispatch_wire,
            manifest_wire,
        )

    def _execute_released_serial_under_lifecycle(
        self,
        command_wire: bytes,
        review_wire: bytes,
        dispatch_wire: bytes,
        manifest_wire: bytes,
    ) -> dict[str, Any]:
        """Run one exact handler while the process execution lock is held."""

        if any(type(item) is not bytes for item in (
            command_wire,
            review_wire,
            dispatch_wire,
            manifest_wire,
        )):
            raise RuntimeGuardError("runtime_guard_canonical_wire_required")
        command: ReleaseCommandV03 = decode_release_command_v03(command_wire)
        review: ReviewAuthorizationV03 = decode_review_authorization_v03(review_wire)
        dispatch: DispatchClaimV03 = decode_dispatch_claim_v03(dispatch_wire)
        manifest = decode_runtime_effect_manifest_v04(manifest_wire)
        self._verifier.verify_dispatch_current(command, review, dispatch)
        capability = self._capabilities.get(command.capability_id)
        if capability is None:
            raise RuntimeGuardError("runtime_capability_not_registered")
        if (
            manifest.effect_id != command.effect_id
            or manifest.capability_id != command.capability_id
            or manifest.runtime_measurement_sha256
            != command.runtime_measurement_sha256
            or command.runtime_measurement_sha256
            != self._runtime_measurement_sha256
            or command.capability_measurement_sha256
            != capability.capability_measurement_sha256
            or command.authorization_context_sha256 != manifest.commitment
        ):
            raise RuntimeGuardError("runtime_manifest_command_join_invalid")
        if getattr(self._thread_state, "active_permit", None) is not None:
            raise RuntimeGuardError("nested_runtime_effect_forbidden")
        dispatch_commitment = dispatch.commitment
        release_identities = {
            ("command", command.commitment),
            ("command_id", command.command_id),
            ("effect_id", command.effect_id),
            ("request_nonce", command.request_nonce),
        }
        remaining = {
            (item.event_name, item.resource_commitment): item.max_uses
            for item in manifest.operations
        }
        # Consume the release and establish its permit in one exact lifecycle
        # decision.  This context performs no evidence append.
        with self._runtime_guard_decision_lease():
            terminal_code = self._recorder.terminal_failure_code()
            with self._lock:
                if terminal_code is not None:
                    self._evidence_terminal = True
                    self._evidence_terminal_reason_code = terminal_code
                if self._evidence_terminal:
                    raise RuntimeGuardError(
                        "runtime_intrusion_evidence_terminal"
                    )
                if dispatch_commitment in self._consumed_dispatches:
                    raise RuntimeGuardError("runtime_dispatch_replayed")
                if not release_identities.isdisjoint(
                    self._consumed_release_identities
                ):
                    raise RuntimeGuardError("runtime_release_identity_replayed")
                if len(self._consumed_dispatches) >= _MAX_CONSUMED_RELEASES:
                    raise RuntimeGuardError(
                        "runtime_release_replay_capacity_exhausted"
                    )
                # Consume before caller-controlled work.  Failure is unresolved
                # and never grants a retry through this local reference guard.
                self._consumed_dispatches.add(dispatch_commitment)
                self._consumed_release_identities.update(release_identities)
                permit = _ActivePermit(
                    dispatch_commitment=dispatch_commitment,
                    owner_thread_id=threading.get_ident(),
                    remaining=remaining,
                    violation_generation_at_start=self._violation_count,
                )
        self._thread_state.active_permit = permit
        try:
            try:
                result = capability.handler()
                if result is not None:
                    raise RuntimeGuardError(
                        "runtime_capability_result_channel_forbidden"
                    )
            except RuntimeGuardViolation:
                raise
            except BaseException:
                raise RuntimeGuardError(
                    "runtime_capability_failed_claim_consumed"
                ) from None
            # Final-return linearization point.  A completed terminal
            # transition or guard violation during the handler prevents any
            # successful execution receipt from escaping.
            with self._runtime_guard_decision_lease():
                terminal_code = self._recorder.terminal_failure_code()
                with self._lock:
                    if terminal_code is not None:
                        self._evidence_terminal = True
                        self._evidence_terminal_reason_code = terminal_code
                    if self._evidence_terminal:
                        permit.revoked = True
                        raise RuntimeGuardError(
                            "runtime_intrusion_evidence_terminal"
                        )
                    violation_generation_changed = (
                        self._violation_count
                        != permit.violation_generation_at_start
                    )
                    if (
                        permit.violations
                        or permit.revoked
                        or violation_generation_changed
                    ):
                        raise RuntimeGuardError(
                            "runtime_capability_violation_claim_consumed"
                        )
                    if any(count != 0 for count in permit.remaining.values()):
                        raise RuntimeGuardError(
                            "runtime_effect_manifest_not_fully_consumed"
                        )
        finally:
            self._thread_state.active_permit = None
        receipt = {
            "schema": RUNTIME_GUARD_EXECUTION_SCHEMA,
            "effect_id": command.effect_id,
            "capability_id": command.capability_id,
            "command_commitment": command.commitment,
            "review_commitment": review.commitment,
            "dispatch_commitment": dispatch_commitment,
            "manifest_commitment": manifest.commitment,
            "operation_count": len(manifest.operations),
            "operation_use_count": sum(
                item.max_uses for item in manifest.operations
            ),
            "all_manifest_operations_consumed": True,
            "audit_event_authorizations_consumed": True,
            "audit_event_origin_attested": False,
            "capability_measurement_attested": False,
            "effect_retry_authorized": False,
            "external_effect_success_attested": False,
            "handler_identity_attested": False,
            "provider_readback_verified": False,
            "result_channel_returned": False,
            "runtime_measurement_attested": False,
            "production_ready": False,
        }
        assert_public_summary_safe(receipt)
        return receipt

    def public_summary(self) -> dict[str, Any]:
        with self._runtime_lifecycle_lock, self._lock:
            result = {
                "schema": RUNTIME_GUARD_PREFLIGHT_SCHEMA,
                "installed": self._installed,
                "runtime_measurement_sha256": self._runtime_measurement_sha256,
                "registered_capability_count": len(self._capabilities),
                "declared_guard_event_count": len(_SUPPORTED_RULE_EVENTS),
                "authorizable_event_count": len(_AUTHORIZABLE_EVENTS),
                "deny_only_event_count": len(_NON_AUTHORIZABLE_EVENTS),
                "consumed_dispatch_count": len(self._consumed_dispatches),
                "max_consumed_release_count": _MAX_CONSUMED_RELEASES,
                "consumed_release_identity_count": len(
                    self._consumed_release_identities
                ),
                "violation_count": self._violation_count,
                "evidence_failure_count": self._evidence_failure_count,
                "evidence_terminal": self._evidence_terminal,
                "evidence_terminal_reason_code": (
                    self._evidence_terminal_reason_code
                ),
                "active_execution_count": self._active_execution_count,
                "active_permit": self._active_execution_count > 0,
                "runtime_guard_lifecycle_sealed": (
                    self._recorder_owner_token is not None
                    and self._recorder_lifecycle_generation is not None
                ),
                "runtime_guard_lifecycle_generation": (
                    self._recorder_lifecycle_generation
                ),
                "capability_measurement_attested": False,
                "installation_failed_terminal": (
                    self._installation_failed_terminal
                ),
                "native_code_isolation_attested": False,
                "javascript_isolation_attested": False,
                "durable_replay_state": False,
                "audit_event_origin_attested": False,
                "file_handle_lifetime_isolation_attested": False,
                "handler_identity_attested": False,
                "inbound_payload_admission_attested": False,
                "native_environment_integrity_attested": False,
                "preopened_descriptor_isolation_attested": False,
                "provider_readback_verified": False,
                "python_object_integrity_attested": False,
                "resource_commitment_confidentiality_attested": False,
                "resource_commitments_keyed": False,
                "runtime_event_coverage_attested": False,
                "runtime_measurement_attested": False,
                "symlink_race_isolation_attested": False,
                "action_eligible": False,
                "economic_eligible": False,
                "production_ready": False,
            }
        assert_public_summary_safe(result)
        return result


__all__ = [
    "RUNTIME_EFFECT_MANIFEST_SCHEMA",
    "RUNTIME_EFFECT_RULE_SCHEMA",
    "RUNTIME_GUARD_EXECUTION_SCHEMA",
    "RUNTIME_GUARD_LIFECYCLE_SCHEMA",
    "RUNTIME_GUARD_PREFLIGHT_SCHEMA",
    "RUNTIME_INTRUSION_PURPOSE",
    "RUNTIME_INTRUSION_SCHEMA",
    "AuditEffectRuleV04",
    "GuardedRuntimeCapabilityV04",
    "HNCRuntimeViolationRecorderV04",
    "RuntimeAuditGuardV04",
    "RuntimeEffectManifestV04",
    "RuntimeGuardError",
    "RuntimeGuardViolation",
    "audit_event_resource_commitment_v04",
    "decode_runtime_effect_manifest_v04",
]

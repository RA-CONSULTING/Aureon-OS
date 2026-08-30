"""Trusted native/session evidence for owner-authorized SCORM frames.

The browser URL is read from the native Edge address-bar accessibility tree.
No cookies, browser storage, DOM, DevTools endpoint, clipboard, keystrokes, or
model assertions are used. The neutral session manifest contributes only
launch/window/action policy. Synthetic-benchmark provenance comes from a
separate owner-signed launch authority bound to the native URL evidence.
"""

from __future__ import annotations

import ctypes
import ctypes.wintypes
import hashlib
import json
import re
import sys
import threading
import unicodedata
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Callable, Mapping, Protocol
from urllib.parse import urlsplit

from aureon.operator.governed_window_session import (
    ProcessInspector,
    SessionWindowBinding,
)
from aureon.operator.hnc_scorm_coherence import (
    ASSESSMENT_CONTROL,
    ASSESSMENT_RESPONSE,
    BOUND_WINDOW_SURFACE,
    COORDINATE_CONTROL,
    CREDENTIAL_COMMIT_CONTROL,
    FOCUSED_CONTROL,
    FRAME_WAIT,
    NATIVE_ACCESSIBILITY_CONTROL,
    NATIVE_BROWSER_UI,
    NATIVE_FOCUSED_CONTROL,
    NAVIGATION,
    NAVIGATION_CONTROL,
    NO_CREDENTIAL_EFFECT,
    OWNER_BENCHMARK_ASSERTED,
    PREVIEW_ONLY,
    SYNTHETIC_BENCHMARK,
    WINDOW_NAVIGATION,
    SCORMActionIntent,
    SCORMActionTargetEvidence,
    SCORMBenchmarkGrant,
    SCORMFrameEvidence,
    SCORMOwnerBenchmarkLaunchAuthority,
    SCORMProviderContextEvidence,
    SCORMRunAuthority,
    SCORMTargetBounds,
    canonical_visible_evidence_sha256,
)
from aureon.operator.local_gui_observer import ScreenObservation
from aureon.operator.scorm_cloud_session import (
    SCORM_CLOUD_HOST,
    ActiveSCORMCloudSession,
    SCORMEvidenceLedger,
)

SCORM_NATIVE_URL_EVIDENCE_SCHEMA = "aureon-scorm-native-url-evidence-v1"
SCORM_NATIVE_TARGET_EVIDENCE_SCHEMA = "aureon-scorm-native-target-evidence-v1"
MAX_NATIVE_UI_ELEMENTS = 512
MAX_NATIVE_UI_ANCESTORS = 128
MAX_ADDRESS_BAR_TEXT_BYTES = 16_384
MAX_FRAME_AGE_SECONDS = 120.0
MAX_FRAME_FUTURE_SKEW_SECONDS = 5.0
MAX_CONTEXT_TTL_SECONDS = 60.0
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_ADDRESS_AUTOMATION_IDS = frozenset(
    {
        "addressEditBox",
        "view_1001",
        "view_1012",
    }
)
_ASSESSMENT_MARKERS = (
    "assessment",
    "certification exam",
    "certification quiz",
    "exam question",
    "final exam",
    "graded assessment",
    "knowledge check",
    "no answer submitted",
    "quiz question",
    "submit answer",
    "submit response",
)
_CREDENTIAL_MARKERS = (
    "confirm identity",
    "create account",
    "log in",
    "login",
    "save credentials",
    "sign in",
    "submit identity",
    "verify identity",
)
_NAVIGATION_MARKERS = (
    "back",
    "begin",
    "close",
    "continue",
    "exit",
    "finish",
    "menu",
    "next",
    "pause",
    "play",
    "previous",
    "resume",
    "start",
)
_ASSESSMENT_TRANSITION_MARKERS = (
    "continue",
    "finish",
    "next",
    "submit",
)
_ASSESSMENT_ROLES = frozenset(
    {"checkbox", "listitem", "radiobutton"}
)
_ASSESSMENT_TEXT_ENTRY_ROLES = frozenset({"combobox", "edit"})
_ASSESSMENT_TEXT_ENTRY_MARKERS = (
    "answer",
    "choice",
    "option",
    "response",
)
_BROWSER_CHROME_NAME_MARKERS = (
    "address and search bar",
    "address bar",
    "browser toolbar",
    "favorites bar",
    "tab actions menu",
)
_NAVIGATION_ROLES = frozenset(
    {"button", "hyperlink", "menuitem", "tabitem", "treeitem"}
)
_SCORM_PLAYER_NAVIGATION_THUMBS = frozenset({"nextBtn", "prevBtn"})
_UIA_CONTROL_ROLES = {
    50000: "button",
    50002: "checkbox",
    50003: "combobox",
    50004: "edit",
    50005: "hyperlink",
    50006: "image",
    50007: "listitem",
    50008: "list",
    50010: "menuitem",
    50011: "menubar",
    50012: "menu",
    50013: "progressbar",
    50014: "radiobutton",
    50015: "scrollbar",
    50017: "statusbar",
    50018: "tab",
    50019: "tabitem",
    50020: "text",
    50023: "treeitem",
    50024: "custom",
    50025: "group",
    50026: "thumb",
    50030: "document",
    50031: "splitbutton",
    50032: "window",
    50033: "pane",
}
class SCORMEvidenceAuthorityError(RuntimeError):
    """A stable, non-sensitive trusted-evidence failure."""

    def __init__(self, code: str) -> None:
        self.code = str(code)
        super().__init__(self.code)


@dataclass(frozen=True)
class NativeAddressBarRead:
    """Raw read-only result from one exact native Edge address-bar control."""

    exact_url: str = field(repr=False)
    window_handle: int
    process_id: int
    automation_id: str
    control_name: str


class NativeAddressBarReader(Protocol):
    def __call__(
        self,
        window_handle: int,
        process_id: int,
        max_elements: int,
    ) -> NativeAddressBarRead:
        ...


@dataclass(frozen=True)
class NativeBrowserURLEvidence:
    """Hash-safe binding between native URL UI and a session generation."""

    exact_url: str = field(repr=False)
    live_origin: str
    live_url_sha256: str
    window_binding_id: str
    window_generation: int
    window_identity_sha256: str
    window_handle: int
    process_id: int
    automation_id_sha256: str
    control_name_sha256: str
    captured_at_unix: int
    evidence_sha256: str
    schema_version: str = SCORM_NATIVE_URL_EVIDENCE_SCHEMA
    evidence_kind: str = NATIVE_BROWSER_UI

    def __post_init__(self) -> None:
        if self.schema_version != SCORM_NATIVE_URL_EVIDENCE_SCHEMA:
            raise SCORMEvidenceAuthorityError("native_url_evidence_schema_invalid")
        if self.evidence_kind != NATIVE_BROWSER_UI:
            raise SCORMEvidenceAuthorityError("native_url_evidence_kind_invalid")
        _validate_live_url(self.exact_url)
        if self.live_origin != f"https://{SCORM_CLOUD_HOST}":
            raise SCORMEvidenceAuthorityError("native_url_origin_invalid")
        if self.live_url_sha256 != _sha256_text(self.exact_url):
            raise SCORMEvidenceAuthorityError("native_url_hash_mismatch")
        for name in (
            "live_url_sha256",
            "window_identity_sha256",
            "automation_id_sha256",
            "control_name_sha256",
            "evidence_sha256",
        ):
            _require_sha256(name, getattr(self, name))
        _required_label("window_binding_id", self.window_binding_id, 256)
        for name, value, minimum in (
            ("window_generation", self.window_generation, 0),
            ("window_handle", self.window_handle, 1),
            ("process_id", self.process_id, 1),
            ("captured_at_unix", self.captured_at_unix, 0),
        ):
            if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
                raise SCORMEvidenceAuthorityError(f"{name}_invalid")
        if self.evidence_sha256 != _sha256_json(self.evidence_payload()):
            raise SCORMEvidenceAuthorityError("native_url_evidence_digest_invalid")

    def evidence_payload(self) -> dict[str, object]:
        return {
            "automation_id_sha256": self.automation_id_sha256,
            "captured_at_unix": self.captured_at_unix,
            "control_name_sha256": self.control_name_sha256,
            "evidence_kind": self.evidence_kind,
            "live_origin": self.live_origin,
            "live_url_sha256": self.live_url_sha256,
            "process_id": self.process_id,
            "schema_version": self.schema_version,
            "window_binding_id": self.window_binding_id,
            "window_generation": self.window_generation,
            "window_handle": self.window_handle,
            "window_identity_sha256": self.window_identity_sha256,
        }

    def audit_dict(self) -> dict[str, object]:
        return {**self.evidence_payload(), "evidence_sha256": self.evidence_sha256}


class Win32EdgeNativeURLProbe:
    """Read the exact Edge URL from native UI Automation without mutation."""

    locality = "local"

    def __init__(
        self,
        *,
        reader: NativeAddressBarReader | None = None,
        utc_now: Callable[[], datetime] | None = None,
        max_elements: int = MAX_NATIVE_UI_ELEMENTS,
    ) -> None:
        if reader is not None and not callable(reader):
            raise TypeError("reader must be callable")
        if (
            isinstance(max_elements, bool)
            or not isinstance(max_elements, int)
            or not 1 <= max_elements <= MAX_NATIVE_UI_ELEMENTS
        ):
            raise ValueError("max_elements must be within [1, 512]")
        self._reader = reader or _read_edge_address_bar_with_comtypes
        self._utc_now = utc_now or (lambda: datetime.now(UTC))
        self._max_elements = max_elements

    def capture(self, binding: SessionWindowBinding) -> NativeBrowserURLEvidence:
        if not isinstance(binding, SessionWindowBinding):
            raise TypeError("binding must be SessionWindowBinding")
        try:
            raw = self._reader(
                binding.window.handle,
                binding.window.process_id,
                self._max_elements,
            )
        except SCORMEvidenceAuthorityError:
            raise
        except Exception as exc:  # noqa: BLE001 - native accessibility boundary
            raise SCORMEvidenceAuthorityError("native_address_bar_read_failed") from exc
        if not isinstance(raw, NativeAddressBarRead):
            raise SCORMEvidenceAuthorityError("native_address_bar_result_invalid")
        if (
            raw.window_handle != binding.window.handle
            or raw.process_id != binding.window.process_id
        ):
            raise SCORMEvidenceAuthorityError("native_address_bar_window_mismatch")
        if raw.automation_id not in _ADDRESS_AUTOMATION_IDS:
            raise SCORMEvidenceAuthorityError("native_address_bar_identity_invalid")
        normalized_name = " ".join(raw.control_name.casefold().split())
        if "address" not in normalized_name or not (
            "bar" in normalized_name or "search" in normalized_name
        ):
            raise SCORMEvidenceAuthorityError("native_address_bar_name_invalid")
        exact_url, live_origin = _validate_live_url(raw.exact_url)
        now_unix = int(_aware_utc(self._utc_now()).timestamp())
        payload = {
            "automation_id_sha256": _sha256_text(raw.automation_id),
            "captured_at_unix": now_unix,
            "control_name_sha256": _sha256_text(raw.control_name),
            "evidence_kind": NATIVE_BROWSER_UI,
            "live_origin": live_origin,
            "live_url_sha256": _sha256_text(exact_url),
            "process_id": raw.process_id,
            "schema_version": SCORM_NATIVE_URL_EVIDENCE_SCHEMA,
            "window_binding_id": binding.binding_id,
            "window_generation": binding.generation,
            "window_handle": raw.window_handle,
            "window_identity_sha256": binding.window_sha256,
        }
        return NativeBrowserURLEvidence(
            exact_url=exact_url,
            live_origin=live_origin,
            live_url_sha256=str(payload["live_url_sha256"]),
            window_binding_id=binding.binding_id,
            window_generation=binding.generation,
            window_identity_sha256=binding.window_sha256,
            window_handle=raw.window_handle,
            process_id=raw.process_id,
            automation_id_sha256=str(payload["automation_id_sha256"]),
            control_name_sha256=str(payload["control_name_sha256"]),
            captured_at_unix=now_unix,
            evidence_sha256=_sha256_json(payload),
        )


@dataclass(frozen=True)
class NativeControlRead:
    """Raw, local-only UI Automation identity for one exact target."""

    window_handle: int
    root_process_id: int
    element_process_id: int
    x: int
    y: int
    width: int
    height: int
    role: str
    name: str = field(repr=False)
    automation_id: str = field(repr=False)
    ancestor_depth: int = 0
    focused: bool = False

    def __post_init__(self) -> None:
        for label, value, minimum in (
            ("window_handle", self.window_handle, 1),
            ("root_process_id", self.root_process_id, 1),
            ("element_process_id", self.element_process_id, 1),
            ("x", self.x, 0),
            ("y", self.y, 0),
            ("width", self.width, 1),
            ("height", self.height, 1),
            ("ancestor_depth", self.ancestor_depth, 0),
        ):
            if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
                raise SCORMEvidenceAuthorityError(f"native_target_{label}_invalid")
        _required_label("native_target_role", self.role, 128)
        if not isinstance(self.name, str) or len(self.name.encode("utf-8")) > 16_384:
            raise SCORMEvidenceAuthorityError("native_target_name_invalid")
        if not isinstance(self.automation_id, str) or len(self.automation_id) > 1_024:
            raise SCORMEvidenceAuthorityError("native_target_automation_id_invalid")
        if not isinstance(self.focused, bool):
            raise SCORMEvidenceAuthorityError("native_target_focused_invalid")


class NativeControlTargetReader(Protocol):
    def read_at(
        self,
        window_handle: int,
        root_process_id: int,
        x: int,
        y: int,
        max_ancestors: int,
    ) -> NativeControlRead:
        ...

    def read_focused(
        self,
        window_handle: int,
        root_process_id: int,
        max_ancestors: int,
    ) -> NativeControlRead:
        ...


@dataclass(frozen=True)
class NativeActionTargetSnapshot:
    """Redacted native target evidence bound to an exact action intent."""

    target_surface: str
    target_bounds: SCORMTargetBounds | None
    target_evidence_kind: str
    target_evidence_sha256: str
    accessibility_role_sha256: str | None
    accessibility_name_sha256: str | None
    accessibility_automation_id_sha256: str | None
    role: str = field(default="", repr=False)
    name: str = field(default="", repr=False)
    automation_id: str = field(default="", repr=False)

    def audit_dict(self) -> dict[str, object]:
        return {
            "accessibility_automation_id_sha256": (
                self.accessibility_automation_id_sha256
            ),
            "accessibility_name_sha256": self.accessibility_name_sha256,
            "accessibility_role_sha256": self.accessibility_role_sha256,
            "target_bounds": (
                self.target_bounds.to_dict() if self.target_bounds is not None else None
            ),
            "target_evidence_kind": self.target_evidence_kind,
            "target_evidence_sha256": self.target_evidence_sha256,
            "target_surface": self.target_surface,
        }


class Win32EdgeNativeTargetProbe:
    """Read one post-intent target from native UI Automation without input."""

    locality = "local"

    def __init__(
        self,
        *,
        reader: NativeControlTargetReader | None = None,
        process_inspector: ProcessInspector,
        max_ancestors: int = MAX_NATIVE_UI_ANCESTORS,
    ) -> None:
        if reader is not None and not (
            callable(getattr(reader, "read_at", None))
            and callable(getattr(reader, "read_focused", None))
        ):
            raise TypeError("reader must expose read_at and read_focused")
        if not callable(getattr(process_inspector, "is_same_process_or_descendant", None)):
            raise TypeError("process_inspector is invalid")
        if (
            isinstance(max_ancestors, bool)
            or not isinstance(max_ancestors, int)
            or not 1 <= max_ancestors <= MAX_NATIVE_UI_ANCESTORS
        ):
            raise ValueError("max_ancestors must be within [1, 128]")
        self._reader = reader or _ComtypesNativeControlTargetReader()
        self._process_inspector = process_inspector
        self._max_ancestors = max_ancestors

    def capture(
        self,
        binding: SessionWindowBinding,
        intent: SCORMActionIntent,
    ) -> NativeActionTargetSnapshot:
        if not isinstance(binding, SessionWindowBinding):
            raise TypeError("binding must be SessionWindowBinding")
        if not isinstance(intent, SCORMActionIntent):
            raise TypeError("intent must be SCORMActionIntent")
        if intent.name == "wait":
            payload = {
                "action_sequence": intent.action_sequence,
                "action_sha256": intent.action_sha256,
                "schema_version": SCORM_NATIVE_TARGET_EVIDENCE_SCHEMA,
                "target_evidence_kind": BOUND_WINDOW_SURFACE,
                "target_surface": FRAME_WAIT,
                "window_binding_id": binding.binding_id,
                "window_generation": binding.generation,
                "window_identity_sha256": binding.window_sha256,
            }
            return NativeActionTargetSnapshot(
                target_surface=FRAME_WAIT,
                target_bounds=None,
                target_evidence_kind=BOUND_WINDOW_SURFACE,
                target_evidence_sha256=_sha256_json(payload),
                accessibility_role_sha256=None,
                accessibility_name_sha256=None,
                accessibility_automation_id_sha256=None,
            )
        try:
            if intent.coordinates is not None:
                raw = self._reader.read_at(
                    binding.window.handle,
                    binding.window.process_id,
                    intent.coordinates.x,
                    intent.coordinates.y,
                    self._max_ancestors,
                )
                surface = COORDINATE_CONTROL
                evidence_kind = NATIVE_ACCESSIBILITY_CONTROL
            else:
                raw = self._reader.read_focused(
                    binding.window.handle,
                    binding.window.process_id,
                    self._max_ancestors,
                )
                surface = FOCUSED_CONTROL
                evidence_kind = NATIVE_FOCUSED_CONTROL
        except SCORMEvidenceAuthorityError:
            raise
        except Exception as exc:  # noqa: BLE001 - native accessibility boundary
            raise SCORMEvidenceAuthorityError("native_action_target_read_failed") from exc
        self._validate_control_read(raw, binding, intent)
        bounds = SCORMTargetBounds(
            x=raw.x,
            y=raw.y,
            width=raw.width,
            height=raw.height,
        )
        automation_id_hash = _sha256_text(raw.automation_id) if raw.automation_id else None
        payload = {
            "accessibility_automation_id_sha256": automation_id_hash,
            "accessibility_name_sha256": _sha256_text(raw.name),
            "accessibility_role_sha256": _sha256_text(raw.role),
            "action_sequence": intent.action_sequence,
            "action_sha256": intent.action_sha256,
            "ancestor_depth": raw.ancestor_depth,
            "element_process_id": raw.element_process_id,
            "focused": raw.focused,
            "schema_version": SCORM_NATIVE_TARGET_EVIDENCE_SCHEMA,
            "target_bounds": bounds.to_dict(),
            "target_evidence_kind": evidence_kind,
            "target_surface": surface,
            "window_binding_id": binding.binding_id,
            "window_generation": binding.generation,
            "window_identity_sha256": binding.window_sha256,
        }
        return NativeActionTargetSnapshot(
            target_surface=surface,
            target_bounds=bounds,
            target_evidence_kind=evidence_kind,
            target_evidence_sha256=_sha256_json(payload),
            accessibility_role_sha256=_sha256_text(raw.role),
            accessibility_name_sha256=_sha256_text(raw.name),
            accessibility_automation_id_sha256=automation_id_hash,
            role=raw.role,
            name=raw.name,
            automation_id=raw.automation_id,
        )

    def _validate_control_read(
        self,
        raw: NativeControlRead,
        binding: SessionWindowBinding,
        intent: SCORMActionIntent,
    ) -> None:
        if not isinstance(raw, NativeControlRead):
            raise SCORMEvidenceAuthorityError("native_action_target_result_invalid")
        if (
            raw.window_handle != binding.window.handle
            or raw.root_process_id != binding.window.process_id
            or raw.ancestor_depth > self._max_ancestors
        ):
            raise SCORMEvidenceAuthorityError("native_action_target_window_mismatch")
        try:
            in_lineage = self._process_inspector.is_same_process_or_descendant(
                raw.element_process_id,
                ancestor_process_id=binding.window.process_id,
            )
        except Exception as exc:
            raise SCORMEvidenceAuthorityError(
                "native_action_target_lineage_unavailable"
            ) from exc
        if in_lineage is not True:
            raise SCORMEvidenceAuthorityError("native_action_target_process_mismatch")
        if (
            raw.x < 0
            or raw.y < 0
            or raw.x + raw.width > binding.window.left + binding.window.width
            or raw.y + raw.height > binding.window.top + binding.window.height
            or raw.x < binding.window.left
            or raw.y < binding.window.top
        ):
            raise SCORMEvidenceAuthorityError("native_action_target_bounds_invalid")
        if intent.coordinates is not None and not (
            raw.x <= intent.coordinates.x < raw.x + raw.width
            and raw.y <= intent.coordinates.y < raw.y + raw.height
        ):
            raise SCORMEvidenceAuthorityError("native_action_coordinates_outside_target")
        if intent.coordinates is None and raw.focused is not True:
            raise SCORMEvidenceAuthorityError("native_action_target_not_focused")


@dataclass(frozen=True)
class _CachedFrameContext:
    observation: ScreenObservation
    binding: SessionWindowBinding
    native_url: NativeBrowserURLEvidence


def owner_benchmark_run_manifest_sha256(
    active_session: ActiveSCORMCloudSession,
) -> str:
    """Return the canonical owner-benchmark run-manifest digest."""

    if not isinstance(active_session, ActiveSCORMCloudSession):
        raise TypeError("active_session must be ActiveSCORMCloudSession")
    return _sha256_json(
        {
            "allowed_origin": f"https://{SCORM_CLOUD_HOST}",
            "control_manifest_sha256": (
                active_session.control_manifest.control_grant_sha256
            ),
            "launch_plan_sha256": active_session.plan.plan_sha256,
            "launch_url_sha256": active_session.plan.url_sha256,
            "mode": "external_scorm_owner_benchmark",
            "schema_version": "aureon-scorm-owner-benchmark-run-manifest-v2",
            "session_id": active_session.plan.session_id,
        }
    )


def public_preview_run_manifest_sha256(
    active_session: ActiveSCORMCloudSession,
) -> str:
    """Compatibility alias for the owner-benchmark run-manifest digest."""

    return owner_benchmark_run_manifest_sha256(active_session)


class SCORMOwnerBenchmarkEvidenceAuthorizer:
    """Issue owner-keyed frame/target/grant evidence, fail closed."""

    locality = "local"

    def __init__(
        self,
        *,
        active_session: ActiveSCORMCloudSession,
        run_authority: SCORMRunAuthority,
        hnc_signing_secret: bytes,
        session_signing_secret: bytes,
        owner_benchmark_signing_secret: bytes,
        owner_benchmark_issuer: str,
        owner_benchmark_key_id: str,
        synthetic_persona_id: str,
        native_url_probe: Win32EdgeNativeURLProbe,
        native_target_probe: Win32EdgeNativeTargetProbe,
        ledger: SCORMEvidenceLedger,
        utc_now: Callable[[], datetime] | None = None,
        context_ttl_seconds: float = 30.0,
        max_cached_contexts: int = 16,
    ) -> None:
        if not isinstance(active_session, ActiveSCORMCloudSession):
            raise TypeError("active_session must be ActiveSCORMCloudSession")
        if not isinstance(run_authority, SCORMRunAuthority):
            raise TypeError("run_authority must be SCORMRunAuthority")
        if not isinstance(native_url_probe, Win32EdgeNativeURLProbe):
            raise TypeError("native_url_probe must be Win32EdgeNativeURLProbe")
        if not isinstance(native_target_probe, Win32EdgeNativeTargetProbe):
            raise TypeError("native_target_probe must be Win32EdgeNativeTargetProbe")
        if not isinstance(ledger, SCORMEvidenceLedger):
            raise TypeError("ledger must be SCORMEvidenceLedger")
        hnc_secret = _required_secret("hnc_signing_secret", hnc_signing_secret)
        session_secret = _required_secret(
            "session_signing_secret",
            session_signing_secret,
        )
        owner_secret = _required_secret(
            "owner_benchmark_signing_secret",
            owner_benchmark_signing_secret,
        )
        if len({hnc_secret, session_secret, owner_secret}) != 3:
            raise SCORMEvidenceAuthorityError("scorm_signing_secrets_must_be_distinct")
        issuer = _required_label(
            "owner_benchmark_issuer",
            owner_benchmark_issuer,
            256,
        )
        key_id = _required_label(
            "owner_benchmark_key_id",
            owner_benchmark_key_id,
            256,
        )
        persona_id = _required_label(
            "synthetic_persona_id",
            synthetic_persona_id,
            256,
        )
        if (
            isinstance(context_ttl_seconds, bool)
            or not isinstance(context_ttl_seconds, (int, float))
            or not 1.0 <= float(context_ttl_seconds) <= MAX_CONTEXT_TTL_SECONDS
        ):
            raise ValueError("context_ttl_seconds must be within [1, 60]")
        if (
            isinstance(max_cached_contexts, bool)
            or not isinstance(max_cached_contexts, int)
            or not 1 <= max_cached_contexts <= 64
        ):
            raise ValueError("max_cached_contexts must be within [1, 64]")
        plan = active_session.plan
        stable_actual = (
            plan.session_id,
            owner_benchmark_run_manifest_sha256(active_session),
            f"https://{SCORM_CLOUD_HOST}",
            plan.url_sha256,
            plan.plan_sha256,
            active_session.control_grant_sha256,
        )
        stable_expected = (
            run_authority.run_id,
            run_authority.run_manifest_sha256,
            run_authority.allowed_origin,
            run_authority.launch_url_sha256,
            run_authority.launch_plan_sha256,
            run_authority.control_grant_sha256,
        )
        if stable_actual != stable_expected:
            raise SCORMEvidenceAuthorityError("run_authority_session_mismatch")
        if run_authority.run_authority_sha256 == active_session.control_grant_sha256:
            raise SCORMEvidenceAuthorityError("run_and_control_grant_hashes_must_differ")
        clock = utc_now or (lambda: datetime.now(UTC))
        now = _aware_utc(clock())
        run_authority.verify_signature(hnc_secret).validate_time(now=now)
        active_session.control_manifest.verify(
            session_secret,
            plan=plan,
            policy_sha256=active_session.initial_binding.policy_sha256,
            now=now,
        )
        self.active_session = active_session
        self.run_authority = run_authority
        self.native_url_probe = native_url_probe
        self.native_target_probe = native_target_probe
        self.ledger = ledger
        self.owner_benchmark_issuer = issuer
        self.owner_benchmark_key_id = key_id
        self.synthetic_persona_id = persona_id
        self._hnc_secret = bytearray(hnc_secret)
        self._session_secret = bytearray(session_secret)
        self._owner_secret = bytearray(owner_secret)
        self._utc_now = clock
        self._context_ttl_seconds = float(context_ttl_seconds)
        self._max_cached_contexts = max_cached_contexts
        self._contexts: OrderedDict[str, _CachedFrameContext] = OrderedDict()
        self._lock = threading.RLock()
        self._closed = False

    def issue_provider_context(
        self,
        observation: ScreenObservation,
        binding: SessionWindowBinding,
    ) -> SCORMProviderContextEvidence:
        if not isinstance(observation, ScreenObservation):
            raise TypeError("observation must be ScreenObservation")
        if not isinstance(binding, SessionWindowBinding):
            raise TypeError("binding must be SessionWindowBinding")
        hnc_secret, session_secret, owner_secret = self._secrets()
        now = _aware_utc(self._utc_now())
        self._validate_fresh_observation(observation, binding, now=now)
        self.run_authority.verify_signature(hnc_secret).validate_time(now=now)
        self.active_session.control_manifest.verify(
            session_secret,
            plan=self.active_session.plan,
            policy_sha256=binding.policy_sha256,
            now=now,
        )
        native_url = self.native_url_probe.capture(binding)
        if self.active_session.authorize_binding() != binding:
            raise SCORMEvidenceAuthorityError("binding_changed_during_native_url_read")
        if (
            native_url.window_binding_id != binding.binding_id
            or native_url.window_generation != binding.generation
            or native_url.window_identity_sha256 != binding.window_sha256
            or native_url.exact_url != self.active_session.plan.exact_url
            or native_url.live_url_sha256 != self.active_session.plan.url_sha256
            or native_url.live_origin != self.run_authority.allowed_origin
        ):
            raise SCORMEvidenceAuthorityError("native_url_launch_context_mismatch")
        visible_sha256 = canonical_visible_evidence_sha256(observation)
        visible_text = _observation_visible_text(observation)
        expires_at = self._bounded_expiry(now)
        owner_launch_authority = SCORMOwnerBenchmarkLaunchAuthority.issue(
            owner_secret=owner_secret,
            issuer=self.owner_benchmark_issuer,
            key_id=self.owner_benchmark_key_id,
            synthetic_persona_id=self.synthetic_persona_id,
            run_authority=self.run_authority,
            native_live_url_sha256=native_url.live_url_sha256,
            native_address_bar_receipt_sha256=native_url.evidence_sha256,
            active_session_id=binding.session_id,
            window_binding_id=binding.binding_id,
            window_generation=binding.generation,
            window_identity_sha256=binding.window_sha256,
            issued_at=now,
            expires_at=expires_at,
        )
        context = SCORMProviderContextEvidence.issue(
            secret=hnc_secret,
            run_authority=self.run_authority,
            launch_authority=owner_launch_authority,
            source_observation_sha256=observation.observation_id,
            source_screenshot_sha256=observation.screenshot_sha256,
            visible_evidence_sha256=visible_sha256,
            visible_text=visible_text,
            active_session_id=binding.session_id,
            live_origin=native_url.live_origin,
            window_binding_id=binding.binding_id,
            window_generation=binding.generation,
            window_identity_sha256=binding.window_sha256,
            issued_at=now,
            expires_at=expires_at,
        )
        self.ledger.append(
            "owner_benchmark_context_issued",
            {
                "native_address_bar_receipt_sha256": native_url.evidence_sha256,
                "owner_launch_authority_sha256": (
                    owner_launch_authority.owner_launch_authority_sha256
                ),
                "provenance": OWNER_BENCHMARK_ASSERTED,
                "provider_context_sha256": context.provider_context_sha256,
                "registration_state": context.registration_state,
                "source_observation_sha256": observation.observation_id,
                "synthetic_persona_sha256": (
                    owner_launch_authority.synthetic_persona_sha256
                ),
                "visible_text_sha256": context.visible_text_sha256,
                "window_binding_id": binding.binding_id,
                "window_generation": binding.generation,
            },
        )
        with self._lock:
            self._contexts[context.provider_context_sha256] = _CachedFrameContext(
                observation=observation,
                binding=binding,
                native_url=native_url,
            )
            self._contexts.move_to_end(context.provider_context_sha256)
            while len(self._contexts) > self._max_cached_contexts:
                self._contexts.popitem(last=False)
        return context

    def issue_action_target(
        self,
        frame: SCORMFrameEvidence,
        provider_context: SCORMProviderContextEvidence,
        intent: SCORMActionIntent,
    ) -> SCORMActionTargetEvidence:
        if not isinstance(frame, SCORMFrameEvidence):
            raise TypeError("frame must be SCORMFrameEvidence")
        if not isinstance(provider_context, SCORMProviderContextEvidence):
            raise TypeError("provider_context must be SCORMProviderContextEvidence")
        if not isinstance(intent, SCORMActionIntent):
            raise TypeError("intent must be SCORMActionIntent")
        hnc_secret, _, owner_secret = self._secrets()
        now = _aware_utc(self._utc_now())
        self.run_authority.verify_signature(hnc_secret).validate_time(now=now)
        cached = self._cached_context(provider_context)
        self._validate_fresh_observation(cached.observation, cached.binding, now=now)
        if frame.provider_context_sha256 != provider_context.provider_context_sha256:
            raise SCORMEvidenceAuthorityError("action_frame_context_mismatch")
        if (
            frame.source_observation_sha256 != cached.observation.observation_id
            or frame.visible_text != _observation_visible_text(cached.observation)
            or intent.source_observation_sha256 != frame.source_observation_sha256
        ):
            raise SCORMEvidenceAuthorityError("action_frame_observation_mismatch")
        current_url = self.native_url_probe.capture(cached.binding)
        if (
            current_url.exact_url != cached.native_url.exact_url
            or current_url.live_url_sha256 != frame.live_url_sha256
            or self.active_session.authorize_binding() != cached.binding
        ):
            raise SCORMEvidenceAuthorityError("action_native_context_changed")
        native_target = self.native_target_probe.capture(cached.binding, intent)
        semantic = _target_semantic(intent, native_target, cached.observation)
        interaction_kind = (
            ASSESSMENT_RESPONSE
            if semantic == ASSESSMENT_CONTROL
            else NAVIGATION
            if semantic in {NAVIGATION_CONTROL, WINDOW_NAVIGATION}
            else "credential_mutation"
        )
        credential_effect = {
            NAVIGATION_CONTROL: NO_CREDENTIAL_EFFECT,
            WINDOW_NAVIGATION: NO_CREDENTIAL_EFFECT,
            ASSESSMENT_CONTROL: PREVIEW_ONLY,
            CREDENTIAL_COMMIT_CONTROL: "real_identity_bound",
        }[semantic]
        interaction_evidence_kind = f"native_{semantic}_target"
        interaction_evidence_sha256 = _sha256_json(
            {
                "action_sha256": intent.action_sha256,
                "interaction_kind": interaction_kind,
                "native_target_sha256": native_target.target_evidence_sha256,
                "provider_context_sha256": provider_context.provider_context_sha256,
                "target_semantic": semantic,
            }
        )
        effect_evidence_kind = (
            f"owner_benchmark_asserted_{credential_effect}_effect"
        )
        effect_evidence_sha256 = _sha256_json(
            {
                "credential_effect": credential_effect,
                "interaction_evidence_sha256": interaction_evidence_sha256,
                "launch_authority_sha256": (
                    provider_context.launch_authority_sha256
                ),
                "target_evidence_sha256": native_target.target_evidence_sha256,
            }
        )
        expires_at = self._bounded_expiry(
            now,
            provider_expires_at_unix=provider_context.expires_at_unix,
        )
        target = SCORMActionTargetEvidence.issue(
            owner_secret=owner_secret,
            provider_context=provider_context,
            frame=frame,
            intent=intent,
            target_surface=native_target.target_surface,
            target_bounds=native_target.target_bounds,
            target_evidence_kind=native_target.target_evidence_kind,
            target_evidence_sha256=native_target.target_evidence_sha256,
            accessibility_role_sha256=native_target.accessibility_role_sha256,
            accessibility_name_sha256=native_target.accessibility_name_sha256,
            accessibility_automation_id_sha256=(
                native_target.accessibility_automation_id_sha256
            ),
            target_semantic=semantic,
            interaction_evidence_kind=interaction_evidence_kind,
            interaction_evidence_sha256=interaction_evidence_sha256,
            credential_effect=credential_effect,
            effect_evidence_kind=effect_evidence_kind,
            effect_evidence_sha256=effect_evidence_sha256,
            issued_at=now,
            expires_at=expires_at,
        )
        self.ledger.append(
            "action_target_issued",
            {
                "action_name": intent.name,
                "action_sequence": intent.action_sequence,
                "action_sha256": intent.action_sha256,
                "action_target_sha256": target.action_target_sha256,
                "credential_effect": target.credential_effect,
                "interaction_kind": target.interaction_kind,
                "target_evidence_sha256": target.target_evidence_sha256,
                "target_semantic": target.target_semantic,
            },
        )
        return target

    def issue_benchmark_grant(
        self,
        frame: SCORMFrameEvidence,
        provider_context: SCORMProviderContextEvidence,
        intent: SCORMActionIntent,
        action_target: SCORMActionTargetEvidence,
    ) -> SCORMBenchmarkGrant | None:
        if action_target.interaction_kind != ASSESSMENT_RESPONSE:
            return None
        if (
            action_target.registration_state != SYNTHETIC_BENCHMARK
            or action_target.credential_effect != PREVIEW_ONLY
            or action_target.launch_authority_sha256
            != provider_context.launch_authority_sha256
            or action_target.provenance != OWNER_BENCHMARK_ASSERTED
        ):
            raise SCORMEvidenceAuthorityError("owner_benchmark_assessment_target_invalid")
        _, _, owner_secret = self._secrets()
        now = _aware_utc(self._utc_now())
        expires_at = self._bounded_expiry(
            now,
            provider_expires_at_unix=action_target.expires_at_unix,
        )
        grant = SCORMBenchmarkGrant.issue(
            owner_secret=owner_secret,
            benchmark_id=f"{self.run_authority.run_id}-owner-benchmark-action",
            replay_nonce=_sha256_json(
                {
                    "action_sequence": intent.action_sequence,
                    "action_target_sha256": action_target.action_target_sha256,
                    "run_replay_nonce": self.run_authority.replay_nonce,
                }
            ),
            run_authority=self.run_authority,
            provider_context=provider_context,
            frame=frame,
            intent=intent,
            action_target=action_target,
            issued_at=now,
            expires_at=expires_at,
        )
        if grant.benchmark_grant_sha256 in {
            self.active_session.control_grant_sha256,
            self.run_authority.run_authority_sha256,
        }:
            raise SCORMEvidenceAuthorityError("benchmark_grant_hash_not_distinct")
        self.ledger.append(
            "benchmark_grant_issued",
            {
                "action_sequence": intent.action_sequence,
                "action_sha256": intent.action_sha256,
                "action_target_sha256": action_target.action_target_sha256,
                "benchmark_grant_sha256": grant.benchmark_grant_sha256,
                "provider_context_sha256": provider_context.provider_context_sha256,
            },
        )
        return grant

    def close(self) -> None:
        with self._lock:
            if self._closed:
                return
            for secret in (
                self._hnc_secret,
                self._session_secret,
                self._owner_secret,
            ):
                for index in range(len(secret)):
                    secret[index] = 0
            self._contexts.clear()
            self._closed = True

    def _secrets(self) -> tuple[bytes, bytes, bytes]:
        with self._lock:
            if self._closed:
                raise SCORMEvidenceAuthorityError("scorm_evidence_authorizer_closed")
            return (
                bytes(self._hnc_secret),
                bytes(self._session_secret),
                bytes(self._owner_secret),
            )

    def _cached_context(
        self,
        provider_context: SCORMProviderContextEvidence,
    ) -> _CachedFrameContext:
        with self._lock:
            cached = self._contexts.get(provider_context.provider_context_sha256)
            if cached is None:
                raise SCORMEvidenceAuthorityError("provider_context_not_locally_bound")
            self._contexts.move_to_end(provider_context.provider_context_sha256)
            return cached

    def _validate_fresh_observation(
        self,
        observation: ScreenObservation,
        binding: SessionWindowBinding,
        *,
        now: datetime,
    ) -> None:
        if self.active_session.authorize_binding() != binding:
            raise SCORMEvidenceAuthorityError("provider_binding_not_current")
        rect = observation.window_rect
        if (
            observation.window_handle != binding.window.handle
            or observation.window_process_id != binding.window.process_id
            or observation.window_title_sha256 != _sha256_text(binding.window.title)
            or rect is None
            or (rect.left, rect.top, rect.width, rect.height)
            != (
                binding.window.left,
                binding.window.top,
                binding.window.width,
                binding.window.height,
            )
        ):
            raise SCORMEvidenceAuthorityError("provider_observation_window_mismatch")
        age = now.timestamp() - float(observation.captured_at_unix)
        if age > MAX_FRAME_AGE_SECONDS or age < -MAX_FRAME_FUTURE_SKEW_SECONDS:
            raise SCORMEvidenceAuthorityError("provider_observation_not_fresh")

    def _bounded_expiry(
        self,
        now: datetime,
        *,
        provider_expires_at_unix: int | None = None,
    ) -> datetime:
        candidates = [
            now + timedelta(seconds=self._context_ttl_seconds),
            datetime.fromtimestamp(self.run_authority.expires_at_unix, tz=UTC),
            datetime.fromtimestamp(
                self.active_session.control_manifest.expires_at_unix,
                tz=UTC,
            ),
        ]
        if provider_expires_at_unix is not None:
            candidates.append(datetime.fromtimestamp(provider_expires_at_unix, tz=UTC))
        expires_at = min(candidates)
        if expires_at <= now:
            raise SCORMEvidenceAuthorityError("scorm_evidence_validity_exhausted")
        return expires_at


SCORMPublicPreviewEvidenceAuthorizer = SCORMOwnerBenchmarkEvidenceAuthorizer


def _observation_visible_text(observation: ScreenObservation) -> str:
    return unicodedata.normalize(
        "NFC",
        f"{observation.ocr_text}\n{observation.vision_text}".strip(),
    )


def _target_semantic(
    intent: SCORMActionIntent,
    target: NativeActionTargetSnapshot,
    observation: ScreenObservation,
) -> str:
    if intent.name == "wait":
        return WINDOW_NAVIGATION
    role = "".join(character for character in target.role.casefold() if character.isalnum())
    name = " ".join(target.name.casefold().split())
    visible = " ".join(
        f"{observation.ocr_text} {observation.vision_text}".casefold().split()
    )
    params: Mapping[str, object] = intent.params
    text_class = params.get("text_class")
    if text_class in {"credential", "personal_data"} or any(
        marker in name for marker in _CREDENTIAL_MARKERS
    ):
        return CREDENTIAL_COMMIT_CONTROL
    if (
        target.automation_id in _ADDRESS_AUTOMATION_IDS
        or any(marker in name for marker in _BROWSER_CHROME_NAME_MARKERS)
    ):
        raise SCORMEvidenceAuthorityError(
            "native_action_target_semantic_unresolved"
        )
    bounds_compatible = _target_bounds_match_observation(
        target,
        observation,
        intent,
    )
    assessment_frame = any(marker in visible for marker in _ASSESSMENT_MARKERS)
    name_grounded = _target_name_grounded_in_frame(name, visible)
    definition_tab_control = (
        bounds_compatible
        and intent.name == "left_click"
        and role == "text"
        and name_grounded
        and "click on each of the tabs" in visible
    )
    if definition_tab_control:
        return NAVIGATION_CONTROL
    named_assessment_control = (
        role in _ASSESSMENT_ROLES | _NAVIGATION_ROLES
        and any(marker in name for marker in _ASSESSMENT_MARKERS)
    )
    assessment_choice_control = (
        assessment_frame
        and role in _ASSESSMENT_ROLES
        and (
            name_grounded
            or any(marker in name for marker in _ASSESSMENT_TEXT_ENTRY_MARKERS)
        )
    )
    assessment_hyperlink_control = (
        assessment_frame and role == "hyperlink" and name_grounded
    )
    assessment_transition_control = (
        assessment_frame
        and role in _NAVIGATION_ROLES
        and any(
            marker == name or marker in name
            for marker in _ASSESSMENT_TRANSITION_MARKERS
        )
    )
    assessment_text_entry = (
        assessment_frame
        and intent.name == "type_text"
        and text_class == "assessment_answer"
        and target.target_surface == FOCUSED_CONTROL
        and role in _ASSESSMENT_TEXT_ENTRY_ROLES
        and any(marker in name for marker in _ASSESSMENT_TEXT_ENTRY_MARKERS)
    )
    exact_player_navigation_thumb = (
        bounds_compatible
        and role == "thumb"
        and target.automation_id in _SCORM_PLAYER_NAVIGATION_THUMBS
        and intent.name in {"left_click", "move_mouse"}
    )
    if exact_player_navigation_thumb:
        return ASSESSMENT_CONTROL if assessment_frame else NAVIGATION_CONTROL
    if bounds_compatible and any(
        (
            named_assessment_control,
            assessment_choice_control,
            assessment_hyperlink_control,
            assessment_transition_control,
            assessment_text_entry,
        )
    ):
        return ASSESSMENT_CONTROL
    if bounds_compatible and (
        role == "hyperlink"
        or (
            role in _NAVIGATION_ROLES
            and any(
                marker == name or marker in name
                for marker in _NAVIGATION_MARKERS
            )
        )
    ):
        return NAVIGATION_CONTROL
    if bounds_compatible and intent.name in {"move_mouse", "scroll"} and role in {
        "custom",
        "document",
        "group",
        "pane",
        "text",
    }:
        return WINDOW_NAVIGATION
    raise SCORMEvidenceAuthorityError("native_action_target_semantic_unresolved")


def _target_bounds_match_observation(
    target: NativeActionTargetSnapshot,
    observation: ScreenObservation,
    intent: SCORMActionIntent,
) -> bool:
    bounds = target.target_bounds
    if bounds is None:
        return False
    rect = observation.window_rect
    if rect is None:
        return False
    inside_window = (
        bounds.x >= rect.left
        and bounds.y >= rect.top
        and bounds.x + bounds.width <= rect.left + rect.width
        and bounds.y + bounds.height <= rect.top + rect.height
    )
    if not inside_window:
        return False
    return intent.coordinates is None or bounds.contains(intent.coordinates)


def _target_name_grounded_in_frame(name: str, visible: str) -> bool:
    normalized_name = " ".join(re.findall(r"[^\W_]+", name, flags=re.UNICODE))
    normalized_visible = " ".join(
        re.findall(r"[^\W_]+", visible, flags=re.UNICODE)
    )
    return bool(normalized_name) and (
        f" {normalized_name} " in f" {normalized_visible} "
    )


class _ComtypesNativeControlTargetReader:
    """Production UIA target reader; it never invokes an input pattern."""

    def read_at(
        self,
        window_handle: int,
        root_process_id: int,
        x: int,
        y: int,
        max_ancestors: int,
    ) -> NativeControlRead:
        return self._read(
            window_handle,
            root_process_id,
            max_ancestors,
            coordinates=(x, y),
        )

    def read_focused(
        self,
        window_handle: int,
        root_process_id: int,
        max_ancestors: int,
    ) -> NativeControlRead:
        return self._read(
            window_handle,
            root_process_id,
            max_ancestors,
            coordinates=None,
        )

    @staticmethod
    def _read(
        window_handle: int,
        root_process_id: int,
        max_ancestors: int,
        *,
        coordinates: tuple[int, int] | None,
    ) -> NativeControlRead:
        if sys.platform != "win32":
            raise SCORMEvidenceAuthorityError("native_action_target_requires_windows")
        if any(
            isinstance(value, bool) or not isinstance(value, int) or value <= 0
            for value in (window_handle, root_process_id, max_ancestors)
        ):
            raise SCORMEvidenceAuthorityError("native_action_target_argument_invalid")
        if coordinates is not None and any(
            isinstance(value, bool) or not isinstance(value, int) or value < 0
            for value in coordinates
        ):
            raise SCORMEvidenceAuthorityError("native_action_coordinates_invalid")
        try:
            import comtypes.client

            uia = comtypes.client.GetModule("UIAutomationCore.dll")
            automation = comtypes.client.CreateObject(
                uia.CUIAutomation,
                interface=uia.IUIAutomation,
            )
            root = automation.ElementFromHandle(window_handle)
            if (
                int(root.CurrentNativeWindowHandle) != window_handle
                or int(root.CurrentProcessId) != root_process_id
            ):
                raise SCORMEvidenceAuthorityError(
                    "native_action_target_root_mismatch"
                )
            if coordinates is None:
                element = automation.GetFocusedElement()
            else:
                point_type = getattr(uia, "tagPOINT", ctypes.wintypes.POINT)
                point = point_type()
                point.x, point.y = coordinates
                element = automation.ElementFromPoint(point)
            if element is None:
                raise SCORMEvidenceAuthorityError("native_action_target_unavailable")
            walker = automation.ControlViewWalker
            current = element
            ancestor_depth = -1
            for depth in range(max_ancestors + 1):
                if bool(automation.CompareElements(current, root)):
                    ancestor_depth = depth
                    break
                current = walker.GetParentElement(current)
                if current is None:
                    break
            if ancestor_depth < 0:
                raise SCORMEvidenceAuthorityError(
                    "native_action_target_not_in_bound_window"
                )
            rectangle = element.CurrentBoundingRectangle
            left = int(getattr(rectangle, "left", getattr(rectangle, "Left", 0)))
            top = int(getattr(rectangle, "top", getattr(rectangle, "Top", 0)))
            right = int(getattr(rectangle, "right", getattr(rectangle, "Right", 0)))
            bottom = int(
                getattr(rectangle, "bottom", getattr(rectangle, "Bottom", 0))
            )
            width = right - left
            height = bottom - top
            role = _UIA_CONTROL_ROLES.get(
                int(element.CurrentControlType),
                f"uia-{int(element.CurrentControlType)}",
            )
            raw = NativeControlRead(
                window_handle=window_handle,
                root_process_id=root_process_id,
                element_process_id=int(element.CurrentProcessId),
                x=left,
                y=top,
                width=width,
                height=height,
                role=role,
                name=str(element.CurrentName or ""),
                automation_id=str(element.CurrentAutomationId or ""),
                ancestor_depth=ancestor_depth,
                focused=bool(element.CurrentHasKeyboardFocus),
            )
        except SCORMEvidenceAuthorityError:
            raise
        except Exception as exc:
            raise SCORMEvidenceAuthorityError("native_action_target_uia_failed") from exc
        return raw


def _read_edge_address_bar_with_comtypes(
    window_handle: int,
    process_id: int,
    max_elements: int,
) -> NativeAddressBarRead:
    """Production UI Automation reader; it performs no input or focus change."""

    if sys.platform != "win32":
        raise SCORMEvidenceAuthorityError("native_address_bar_requires_windows")
    if any(
        isinstance(value, bool) or not isinstance(value, int) or value <= 0
        for value in (window_handle, process_id, max_elements)
    ):
        raise SCORMEvidenceAuthorityError("native_address_bar_argument_invalid")
    try:
        import comtypes.client

        uia = comtypes.client.GetModule("UIAutomationCore.dll")
        automation = comtypes.client.CreateObject(
            uia.CUIAutomation,
            interface=uia.IUIAutomation,
        )
        root = automation.ElementFromHandle(window_handle)
        if (
            int(root.CurrentNativeWindowHandle) != window_handle
            or int(root.CurrentProcessId) != process_id
        ):
            raise SCORMEvidenceAuthorityError("native_address_bar_root_mismatch")
        condition = automation.CreatePropertyCondition(30003, 50004)
        collection = root.FindAll(4, condition)
        length = int(collection.Length)
        if length < 0 or length > max_elements:
            raise SCORMEvidenceAuthorityError("native_address_bar_inventory_bounded")
        candidates: list[NativeAddressBarRead] = []
        for index in range(length):
            element = collection.GetElement(index)
            automation_id = str(element.CurrentAutomationId or "")
            if automation_id not in _ADDRESS_AUTOMATION_IDS:
                continue
            name = str(element.CurrentName or "")
            normalized_name = " ".join(name.casefold().split())
            if "address" not in normalized_name or not (
                "bar" in normalized_name or "search" in normalized_name
            ):
                continue
            if (
                int(element.CurrentProcessId) != process_id
                or bool(element.CurrentIsOffscreen)
                or not bool(element.CurrentIsEnabled)
            ):
                continue
            pattern = element.GetCurrentPattern(10002)
            value_pattern = pattern.QueryInterface(uia.IUIAutomationValuePattern)
            exact_url = str(value_pattern.CurrentValue or "")
            if len(exact_url.encode("utf-8")) > MAX_ADDRESS_BAR_TEXT_BYTES:
                raise SCORMEvidenceAuthorityError("native_address_bar_value_too_large")
            candidates.append(
                NativeAddressBarRead(
                    exact_url=exact_url,
                    window_handle=window_handle,
                    process_id=process_id,
                    automation_id=automation_id,
                    control_name=name,
                )
            )
    except SCORMEvidenceAuthorityError:
        raise
    except Exception as exc:
        raise SCORMEvidenceAuthorityError("native_address_bar_uia_failed") from exc
    if len(candidates) != 1:
        raise SCORMEvidenceAuthorityError("native_address_bar_not_unique")
    return candidates[0]


def _validate_live_url(value: object) -> tuple[str, str]:
    if (
        not isinstance(value, str)
        or not value
        or value != value.strip()
        or "\\" in value
        or len(value.encode("utf-8")) > MAX_ADDRESS_BAR_TEXT_BYTES
        or any(ord(char) < 0x20 or ord(char) == 0x7F for char in value)
    ):
        raise SCORMEvidenceAuthorityError("native_live_url_invalid")
    # Chromium may display the current HTTPS URL without its scheme in the
    # native address-bar ValuePattern.  Accept only the exact allowlisted host
    # prefix in that display form, then restore the canonical URL before any
    # parsing, hashing, or comparison with the signed launch plan.
    canonical_value = value
    scheme_omitted_prefix = f"{SCORM_CLOUD_HOST}/"
    if value.startswith(scheme_omitted_prefix):
        canonical_value = f"https://{value}"
    try:
        parsed = urlsplit(canonical_value)
        port = parsed.port
    except ValueError as exc:
        raise SCORMEvidenceAuthorityError("native_live_url_invalid") from exc
    if (
        parsed.scheme != "https"
        or parsed.netloc != SCORM_CLOUD_HOST
        or parsed.hostname != SCORM_CLOUD_HOST
        or parsed.username is not None
        or parsed.password is not None
        or port is not None
    ):
        raise SCORMEvidenceAuthorityError("native_live_url_origin_not_allowed")
    return canonical_value, f"https://{SCORM_CLOUD_HOST}"


def _required_secret(name: str, value: object) -> bytes:
    if not isinstance(value, bytes) or len(value) < 32:
        raise SCORMEvidenceAuthorityError(f"{name}_invalid")
    return value


def _aware_utc(value: datetime) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise SCORMEvidenceAuthorityError("scorm_evidence_clock_invalid")
    return value.astimezone(UTC)


def _require_sha256(name: str, value: object) -> str:
    if not isinstance(value, str) or _SHA256_RE.fullmatch(value) is None:
        raise SCORMEvidenceAuthorityError(f"{name}_invalid")
    return value


def _required_label(name: str, value: object, maximum: int) -> str:
    if (
        not isinstance(value, str)
        or not value
        or value != value.strip()
        or len(value) > maximum
        or any(ord(char) < 0x20 or ord(char) == 0x7F for char in value)
    ):
        raise SCORMEvidenceAuthorityError(f"{name}_invalid")
    return value


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _sha256_json(value: object) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


__all__ = [
    "NativeAddressBarRead",
    "NativeAddressBarReader",
    "NativeActionTargetSnapshot",
    "NativeBrowserURLEvidence",
    "NativeControlRead",
    "NativeControlTargetReader",
    "SCORMEvidenceAuthorityError",
    "SCORMOwnerBenchmarkEvidenceAuthorizer",
    "SCORMPublicPreviewEvidenceAuthorizer",
    "Win32EdgeNativeTargetProbe",
    "Win32EdgeNativeURLProbe",
    "owner_benchmark_run_manifest_sha256",
    "public_preview_run_manifest_sha256",
]

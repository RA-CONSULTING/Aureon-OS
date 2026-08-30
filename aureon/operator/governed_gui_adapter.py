"""Adapters between Aureon's local GUI runtime and governed desktop gateway.

The adapters in this module do not create a desktop backend and do not perform
network I/O.  A caller supplies an already-configured
``GovernedDesktopGateway``.  Screenshot bytes stay in memory, every mutating
action carries the executor's exact target-window binding, and dry-run results
are never represented as successful execution.
"""

from __future__ import annotations

import hashlib
import math
import re
import threading
import time
import uuid
from collections.abc import Callable, Mapping
from typing import Any, cast

from aureon.autonomous.aureon_governed_desktop_gateway import (
    DesktopActionResult,
    GovernedDesktopGateway,
)
from aureon.autonomous.aureon_governed_desktop_gateway import (
    ScreenObservation as GatewayScreenObservation,
)
from aureon.operator.local_gui_observer import (
    CapturedScreen,
    GatewayObservationRejectedError,
    ObservationError,
    WindowRect,
)
from aureon.operator.local_gui_observer import (
    ScreenObservation as RuntimeScreenObservation,
)
from aureon.operator.local_gui_runtime import ActionResult, GuiAction, detect_human_gate
from aureon.operator.local_gui_scorm_authority import (
    SCORMActionAuthorization,
    SCORMVisionRuntimeAuthority,
)

_ACTION_MAP = {
    "move_mouse": "move",
    "left_click": "click",
    "right_click": "right_click",
    "double_click": "double_click",
    "type_text": "type",
    "press_key": "press",
    "hotkey": "hotkey",
    "scroll": "scroll",
}

# Only gateway-owned, non-payload status labels may cross into runtime results.
# An unexpected reason remains a failure but is reduced to ``gateway_rejected``
# so an injected backend cannot echo typed or personal data into result logs.
_PUBLIC_GATEWAY_FAILURE_CODES = frozenset(
    {
        "action_not_allowed",
        "action_outside_lease_scope",
        "action_rate_min_interval",
        "action_rate_window_exceeded",
        "active_authorization_lease_required",
        "authorization_lease_changed_before_dispatch",
        "backend_action_failed",
        "coordinates_outside_screen",
        "coordinates_outside_target_window",
        "desktop_observation_failed",
        "duration_must_be_finite",
        "duration_out_of_range",
        "emergency_epoch_changed_before_dispatch",
        "emergency_epoch_changed_during_action",
        "emergency_stop_active",
        "evidence_completion_write_failed",
        "evidence_start_write_failed",
        "expected_before_sha256_invalid",
        "expected_before_sha256_required",
        "foreground_window_dpi_changed_during_capture",
        "foreground_window_changed_during_capture",
        "foreground_window_geometry_unavailable",
        "foreground_window_query_failed",
        "foreground_window_unavailable",
        "hotkey_key_count_out_of_range",
        "hotkey_keys_must_be_sequence",
        "interval_must_be_finite",
        "interval_out_of_range",
        "invalid_foreground_window_geometry",
        "invalid_foreground_window_identity",
        "invalid_foreground_window_record",
        "invalid_pointer_position",
        "invalid_postcondition_result",
        "invalid_screen_size",
        "invalid_window_dpi",
        "invalid_window_dpi_provider",
        "key_not_allowed",
        "key_required",
        "post_action_capture_failed",
        "postcondition_evaluator_failed",
        "postcondition_failed",
        "pointer_position_failed",
        "required_action_parameter_missing",
        "scroll_amount_out_of_range",
        "stale_source_frame",
        "target_window_binding_epoch_stale",
        "target_window_changed_after_action_handoff_required",
        "target_window_mismatch",
        "text_length_out_of_range",
        "text_must_be_string",
        "unknown_action_parameter",
        "valid_target_window_binding_required",
        "window_dpi_query_failed",
    }
)
_PROVEN_PRE_DISPATCH_GATEWAY_FAILURE_CODES = frozenset({"stale_source_frame"})
_PROVEN_POST_DISPATCH_GATEWAY_FAILURE_CODES = frozenset(
    {
        "invalid_postcondition_result",
        "post_action_capture_failed",
        "postcondition_evaluator_failed",
        "postcondition_failed",
        "target_window_changed_after_action_handoff_required",
    }
)


class GatewayScreenshotBackend:
    """Expose binding-masked gateway observations through ``CapturedScreen``.

    ``GovernedDesktopGateway.observe`` records durable start/completion
    evidence.  This adapter accepts the observation only when that operation
    succeeded and both the returned evidence hashes and the in-memory bytes
    agree.  A binding may be supplied up front or is latched once from the
    gateway's sole current binding; capture never falls back to unbound observe.
    """

    def __init__(
        self,
        gateway: GovernedDesktopGateway,
        *,
        binding_id: str | None = None,
        binding_supplier: Callable[[], str] | None = None,
    ) -> None:
        if binding_id is not None and binding_supplier is not None:
            raise ValueError("binding_id and binding_supplier are mutually exclusive")
        if binding_supplier is not None and not callable(binding_supplier):
            raise TypeError("binding_supplier must be callable")
        self._gateway = gateway
        self._binding_lock = threading.Lock()
        self._binding_id: str | None = None
        self._binding_supplier = binding_supplier
        if binding_id is not None:
            self.bind_target(binding_id)

    @property
    def binding_id(self) -> str | None:
        """Return the exact binding latched for observation, if available."""

        with self._binding_lock:
            return self._binding_id

    def bind_target(self, binding_id: str) -> None:
        """Latch one exact binding; rebinding requires a new observer."""

        _require_exact_binding_id(binding_id)
        with self._binding_lock:
            if self._binding_supplier is not None:
                raise ValueError("dynamic screenshot binding cannot be latched")
            if self._binding_id is not None and self._binding_id != binding_id:
                raise ValueError("screenshot binding is immutable")
            self._binding_id = binding_id

    def capture(self) -> CapturedScreen:
        binding_id = self._required_binding_id()
        try:
            result = self._gateway.observe(target_binding_id=binding_id)
        except Exception as exc:  # noqa: BLE001 - injected gateway boundary
            raise ObservationError("gateway_observation_failed") from exc

        if not isinstance(result, DesktopActionResult):
            raise ObservationError("gateway_observation_invalid_result")
        if not result.ok:
            reason = (
                result.reason
                if isinstance(result.reason, str)
                and result.reason in _PUBLIC_GATEWAY_FAILURE_CODES
                else "gateway_rejected"
            )
            raise GatewayObservationRejectedError(reason)
        if result.action != "observe" or result.reason != "observed":
            raise ObservationError("gateway_observation_invalid_result")
        if not _valid_action_id(result.action_id):
            raise ObservationError("gateway_observation_invalid_result")
        if result.before is None or result.after is None:
            raise ObservationError("gateway_observation_missing_frame")
        if not _observation_matches_hash(result.before, result.before_sha256):
            raise ObservationError("gateway_observation_evidence_mismatch")
        if not _observation_matches_hash(result.after, result.after_sha256):
            raise ObservationError("gateway_observation_evidence_mismatch")

        try:
            return CapturedScreen(
                image_bytes=result.after.image_bytes,
                width=result.after.width,
                height=result.after.height,
                mime_type="image/png",
                cursor_x=result.after.cursor_x,
                cursor_y=result.after.cursor_y,
                window_handle=result.after.window.handle,
                window_process_id=result.after.window.process_id,
                window_title_sha256=hashlib.sha256(
                    result.after.window.title.encode("utf-8")
                ).hexdigest(),
                window_rect=WindowRect(
                    left=result.after.window.left,
                    top=result.after.window.top,
                    width=result.after.window.width,
                    height=result.after.window.height,
                ),
                dpi_x=result.after.dpi_x,
                dpi_y=result.after.dpi_y,
            )
        except (TypeError, ValueError) as exc:
            raise ObservationError("gateway_observation_invalid_frame") from exc

    def _required_binding_id(self) -> str:
        supplier = self._binding_supplier
        if supplier is not None:
            try:
                candidate = supplier()
                _require_exact_binding_id(candidate)
            except Exception as exc:  # noqa: BLE001 - authority failures fail closed
                raise GatewayObservationRejectedError(
                    "target_window_mismatch"
                ) from exc
            with self._binding_lock:
                self._binding_id = candidate
            return candidate
        with self._binding_lock:
            if self._binding_id is None:
                try:
                    candidate = self._gateway.require_single_target_binding_id()
                    _require_exact_binding_id(candidate)
                except Exception as exc:  # noqa: BLE001 - injected gateway boundary
                    raise ObservationError("exact_target_window_binding_required") from exc
                self._binding_id = candidate
            return self._binding_id


class GovernedGatewayExecutor:
    """Map validated runtime actions onto one bound governed gateway."""

    def __init__(
        self,
        gateway: GovernedDesktopGateway,
        *,
        binding_id: str | None = None,
        binding_supplier: Callable[[], str] | None = None,
        sleeper: Callable[[float], object] = time.sleep,
        max_wait_seconds: float = 10.0,
        control_action_authorizer: Callable[
            [RuntimeScreenObservation, GuiAction], bool
        ]
        | None = None,
        assessment_action_authorizer: Callable[
            [RuntimeScreenObservation, GuiAction], object | None
        ]
        | None = None,
        scorm_authority: SCORMVisionRuntimeAuthority | None = None,
    ) -> None:
        if binding_id is None and binding_supplier is None:
            raise ValueError("binding_id or binding_supplier is required")
        if binding_id is not None and binding_supplier is not None:
            raise ValueError("binding_id and binding_supplier are mutually exclusive")
        if binding_id is not None:
            _require_exact_binding_id(binding_id)
        if binding_supplier is not None and not callable(binding_supplier):
            raise TypeError("binding_supplier must be callable")
        if not callable(sleeper):
            raise TypeError("sleeper must be callable")
        if (
            isinstance(max_wait_seconds, bool)
            or not isinstance(max_wait_seconds, (int, float))
            or not math.isfinite(float(max_wait_seconds))
            or float(max_wait_seconds) <= 0.0
            or float(max_wait_seconds) > 10.0
        ):
            raise ValueError("max_wait_seconds must be within (0, 10]")

        self._gateway = gateway
        self._binding_id = binding_id
        self._binding_supplier = binding_supplier
        self._sleeper = sleeper
        self._max_wait_seconds = float(max_wait_seconds)
        if control_action_authorizer is not None:
            raise TypeError(
                "control_action_authorizer callbacks are forbidden; use scorm_authority"
            )
        if scorm_authority is not None and not isinstance(
            scorm_authority,
            SCORMVisionRuntimeAuthority,
        ):
            raise TypeError("scorm_authority must be SCORMVisionRuntimeAuthority")
        if scorm_authority is not None and assessment_action_authorizer is not None:
            raise ValueError(
                "SCORM authority and synthetic assessment authority are mutually exclusive"
            )
        self._assessment_action_authorizer = assessment_action_authorizer
        self._scorm_authority = scorm_authority

    @property
    def binding_id(self) -> str:
        """Return the freshly authorized binding used for the next mutation."""

        return self._required_binding_id()

    def _required_binding_id(self) -> str:
        supplier = self._binding_supplier
        if supplier is None:
            assert self._binding_id is not None
            return self._binding_id
        candidate = supplier()
        _require_exact_binding_id(candidate)
        return candidate

    def execute(
        self,
        action: GuiAction,
        *,
        source_observation: RuntimeScreenObservation | None = None,
        action_authorization: object | None = None,
    ) -> ActionResult:
        if not isinstance(action, GuiAction):
            return ActionResult(
                False,
                "invalid_gui_action",
                dispatch_state="not_dispatched",
            )

        if (
            self._scorm_authority is None
            and action.name == "type_text"
            and action.params["text_class"] == "assessment_answer"
            and self._assessment_action_authorizer is None
        ):
            return ActionResult(
                False,
                "human_required_certification_assessment",
                dispatch_state="not_dispatched",
            )

        if action.name == "wait" and self._scorm_authority is None:
            return self._wait(action)

        if source_observation is None:
            return ActionResult(
                False,
                "source_observation_required",
                dispatch_state="not_dispatched",
            )
        if (
            not isinstance(source_observation, RuntimeScreenObservation)
            or re.fullmatch(r"[0-9a-f]{64}", source_observation.screenshot_sha256)
            is None
        ):
            return ActionResult(
                False,
                "source_observation_invalid",
                dispatch_state="not_dispatched",
            )

        scorm_audit: Mapping[str, object] | None = None
        if self._scorm_authority is not None:
            if not isinstance(action_authorization, SCORMActionAuthorization):
                return ActionResult(
                    False,
                    "scorm_control_authorization_required",
                    dispatch_state="not_dispatched",
                )
            if (
                action.name == "type_text"
                and action.params["text_class"] == "assessment_answer"
                and action_authorization.receipt.benchmark_grant_sha256 is None
            ):
                return ActionResult(
                    False,
                    "scorm_control_authorization_required",
                    dispatch_state="not_dispatched",
                )
            try:
                self._scorm_authority.verify_and_consume_action(
                    action_authorization,
                    source_observation,
                    action,
                )
            except Exception:  # noqa: BLE001 - signed authority failures fail closed
                return ActionResult(
                    False,
                    "scorm_control_authorization_required",
                    dispatch_state="not_dispatched",
                )
            scorm_audit = action_authorization.audit_dict()
            if action.name == "wait":
                return self._with_scorm_audit(self._wait(action), scorm_audit)
        elif action_authorization is not None:
            return ActionResult(
                False,
                "scorm_control_authorization_required",
                dispatch_state="not_dispatched",
            )

        assessment_context = (
            detect_human_gate(source_observation) == "certification_assessment"
            or (
                action.name == "type_text"
                and action.params["text_class"] == "assessment_answer"
            )
        )
        assessment_receipt: object | None = None
        if assessment_context and self._scorm_authority is None:
            if self._assessment_action_authorizer is None:
                return ActionResult(
                    False,
                    "human_required_certification_assessment",
                    dispatch_state="not_dispatched",
                )
            try:
                assessment_receipt = self._assessment_action_authorizer(
                    source_observation,
                    action,
                )
            except Exception:  # noqa: BLE001 - authority failures must fail closed
                assessment_receipt = None
            if assessment_receipt is None or assessment_receipt is False:
                return ActionResult(
                    False,
                    "human_required_certification_assessment",
                    dispatch_state="not_dispatched",
                )

        gateway_action = _ACTION_MAP.get(action.name)
        if gateway_action is None:
            return ActionResult(
                False,
                "action_not_supported_by_gateway",
                dispatch_state="not_dispatched",
            )
        gateway_params = _gateway_params(action)

        try:
            binding_id = self._required_binding_id()
        except Exception:  # noqa: BLE001 - dynamic binding failures fail closed
            return ActionResult(
                False,
                "scorm_control_authorization_required",
                dispatch_state="not_dispatched",
            )

        try:
            result = self._gateway.execute(
                gateway_action,
                gateway_params,
                target_binding_id=binding_id,
                expected_before_sha256=source_observation.screenshot_sha256,
            )
        except Exception:  # noqa: BLE001 - injected gateway boundary
            return ActionResult(False, "gateway_exception")

        converted = _to_action_result(result, expected_action=gateway_action)
        if scorm_audit is not None:
            return self._with_scorm_audit(converted, scorm_audit)
        if assessment_receipt is None:
            return converted
        receipt_to_dict = getattr(assessment_receipt, "to_dict", None)
        receipt_payload = receipt_to_dict() if callable(receipt_to_dict) else {}
        safe_receipt = {
            key: receipt_payload[key]
            for key in (
                "schema_version",
                "action_sequence",
                "grant_sha256",
                "context_sha256",
                "receipt_sha256",
            )
            if key in receipt_payload
        }
        return ActionResult(
            converted.ok,
            converted.code,
            {**converted.details, "synthetic_assessment_authority": safe_receipt},
            dispatch_state=converted.dispatch_state,
        )

    @staticmethod
    def _with_scorm_audit(
        result: ActionResult,
        audit: Mapping[str, object],
    ) -> ActionResult:
        return ActionResult(
            result.ok,
            result.code,
            {**result.details, "scorm_action_authority": dict(audit)},
            dispatch_state=result.dispatch_state,
        )

    def _wait(self, action: GuiAction) -> ActionResult:
        seconds = float(cast(float, action.params["seconds"]))
        if seconds > self._max_wait_seconds:
            return ActionResult(
                False,
                "wait_exceeds_adapter_limit",
                dispatch_state="not_dispatched",
            )
        try:
            self._sleeper(seconds)
        except Exception:  # noqa: BLE001 - injected sleeper boundary
            return ActionResult(False, "wait_failed", dispatch_state="ambiguous")
        return ActionResult(True, "wait_completed", dispatch_state="not_dispatched")


def _gateway_params(action: GuiAction) -> dict[str, Any]:
    params = action.params
    if action.name == "move_mouse":
        mapped = {"x": params["x"], "y": params["y"]}
        if "duration" in params:
            mapped["duration"] = params["duration"]
        return mapped
    if action.name in {"left_click", "right_click", "double_click"}:
        return {"x": params["x"], "y": params["y"]}
    if action.name == "scroll":
        return {"x": params["x"], "y": params["y"], "amount": params["clicks"]}
    if action.name == "type_text":
        mapped = {"text": params["text"]}
        if "interval" in params:
            mapped["interval"] = params["interval"]
        return mapped
    if action.name == "press_key":
        return {"key": params["key"]}
    if action.name == "hotkey":
        return {"keys": params["keys"]}
    return {}


def _to_action_result(result: object, *, expected_action: str) -> ActionResult:
    if not isinstance(result, DesktopActionResult):
        return ActionResult(
            False,
            "invalid_gateway_result",
            dispatch_state="ambiguous",
        )
    if (
        not isinstance(result.ok, bool)
        or not isinstance(result.dry_run, bool)
        or not isinstance(result.reason, str)
        or result.action != expected_action
        or not _valid_action_id(result.action_id)
    ):
        return ActionResult(
            False,
            "invalid_gateway_result",
            dispatch_state="ambiguous",
        )

    details: Mapping[str, object] = {
        "gateway_action": expected_action,
        "gateway_action_id": result.action_id,
        "dry_run": result.dry_run,
    }
    if not result.ok:
        if (
            result.reason == "target_window_changed_after_action_handoff_required"
            and result.dry_run is False
        ):
            return ActionResult(
                True,
                "gateway_executed_handoff_required",
                details,
                dispatch_state="dispatched",
            )
        reason = result.reason if result.reason in _PUBLIC_GATEWAY_FAILURE_CODES else "rejected"
        if (
            result.dry_run
            or reason in _PROVEN_PRE_DISPATCH_GATEWAY_FAILURE_CODES
        ):
            dispatch_state = "not_dispatched"
        elif reason in _PROVEN_POST_DISPATCH_GATEWAY_FAILURE_CODES:
            dispatch_state = "dispatched"
        else:
            dispatch_state = "ambiguous"
        return ActionResult(
            False,
            f"gateway_{reason}",
            details,
            dispatch_state=dispatch_state,
        )
    if result.dry_run:
        return ActionResult(
            False,
            "gateway_dry_run",
            details,
            dispatch_state="not_dispatched",
        )
    if result.reason != "executed":
        return ActionResult(
            False,
            "invalid_gateway_result",
            details,
            dispatch_state="ambiguous",
        )
    return ActionResult(
        True,
        "gateway_executed",
        details,
        dispatch_state="dispatched",
    )


def _observation_matches_hash(observation: GatewayScreenObservation, evidence_hash: str) -> bool:
    if not isinstance(observation.image_bytes, bytes) or not observation.image_bytes:
        return False
    calculated = hashlib.sha256(observation.image_bytes).hexdigest()
    return bool(evidence_hash) and calculated == observation.sha256 == evidence_hash


def _valid_action_id(value: object) -> bool:
    if not isinstance(value, str):
        return False
    try:
        return str(uuid.UUID(value)) == value
    except (ValueError, AttributeError):
        return False


def _require_exact_binding_id(binding_id: object) -> None:
    if not isinstance(binding_id, str) or not binding_id or binding_id.strip() != binding_id:
        raise ValueError("binding_id must be an exact non-empty string")


__all__ = ["GatewayScreenshotBackend", "GovernedGatewayExecutor"]

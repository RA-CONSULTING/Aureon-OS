"""Typed bridge from an active SCORM session to HNC v3 action receipts.

Preflight is deliberately non-authorizing. After the local model proposes an
exact action, a separately keyed provider attests its target and effect. The
HNC gate can then require a per-action preview grant and issue a one-use
receipt consumed immediately before gateway dispatch.
"""

from __future__ import annotations

import hashlib
import unicodedata
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Callable
from urllib.parse import urlsplit

from aureon.operator.governed_window_session import SessionWindowBinding
from aureon.operator.hnc_scorm_coherence import (
    CONTINUE,
    HNCScormCoherenceGate,
    SCORMActionDecision,
    SCORMActionIntent,
    SCORMActionReceipt,
    SCORMActionTargetEvidence,
    SCORMBenchmarkGrant,
    SCORMFrameEvidence,
    SCORMPreflightDecision,
    SCORMProviderContextEvidence,
    SCORMRunAuthority,
    canonical_action_sha256,
    canonical_visible_evidence_sha256,
    canonical_visible_text_sha256,
)
from aureon.operator.local_gui_observer import ScreenObservation
from aureon.operator.local_gui_runtime import GuiAction
from aureon.operator.scorm_cloud_session import ActiveSCORMCloudSession

SCORM_ACTION_AUTHORIZATION_SCHEMA = "aureon-local-gui-scorm-action-authorization-v2"

ProviderContextSupplier = Callable[
    [ScreenObservation, SessionWindowBinding],
    SCORMProviderContextEvidence,
]
ActionTargetSupplier = Callable[
    [SCORMFrameEvidence, SCORMProviderContextEvidence, SCORMActionIntent],
    SCORMActionTargetEvidence,
]
BenchmarkGrantSupplier = Callable[
    [
        SCORMFrameEvidence,
        SCORMProviderContextEvidence,
        SCORMActionIntent,
        SCORMActionTargetEvidence,
    ],
    SCORMBenchmarkGrant | None,
]


class SCORMRuntimeAuthorityError(RuntimeError):
    """An exact signed SCORM authority could not be established."""


@dataclass(frozen=True)
class SCORMObservationAuthorization:
    """Exact frame and prerequisite-only preflight evidence."""

    preflight: SCORMPreflightDecision
    frame: SCORMFrameEvidence
    provider_context: SCORMProviderContextEvidence

    def __post_init__(self) -> None:
        if not isinstance(self.preflight, SCORMPreflightDecision):
            raise TypeError("preflight must be SCORMPreflightDecision")
        if not isinstance(self.frame, SCORMFrameEvidence):
            raise TypeError("frame must be SCORMFrameEvidence")
        if not isinstance(self.provider_context, SCORMProviderContextEvidence):
            raise TypeError("provider_context must be SCORMProviderContextEvidence")
        if (
            self.preflight.source_observation_sha256
            != self.frame.source_observation_sha256
            or self.preflight.provider_context_sha256
            != self.provider_context.provider_context_sha256
            or self.frame.provider_context_sha256
            != self.provider_context.provider_context_sha256
        ):
            raise SCORMRuntimeAuthorityError("preflight_frame_context_mismatch")

    @property
    def decision(self) -> SCORMPreflightDecision:
        """Compatibility alias for current-decision display code."""

        return self.preflight

    def audit_dict(self) -> dict[str, object]:
        return self.preflight.to_dict()


@dataclass(frozen=True)
class SCORMActionAuthorization:
    """One exact provider target plus a short-lived HNC dispatch receipt."""

    receipt: SCORMActionReceipt
    observation_authorization: SCORMObservationAuthorization
    intent: SCORMActionIntent
    action_target: SCORMActionTargetEvidence
    decision: SCORMActionDecision
    benchmark_grant: SCORMBenchmarkGrant | None
    schema_version: str = SCORM_ACTION_AUTHORIZATION_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != SCORM_ACTION_AUTHORIZATION_SCHEMA:
            raise SCORMRuntimeAuthorityError("scorm_action_authorization_schema_invalid")
        if not isinstance(self.receipt, SCORMActionReceipt):
            raise TypeError("receipt must be SCORMActionReceipt")
        if not isinstance(self.observation_authorization, SCORMObservationAuthorization):
            raise TypeError(
                "observation_authorization must be SCORMObservationAuthorization"
            )
        if not isinstance(self.intent, SCORMActionIntent):
            raise TypeError("intent must be SCORMActionIntent")
        if not isinstance(self.action_target, SCORMActionTargetEvidence):
            raise TypeError("action_target must be SCORMActionTargetEvidence")
        if not isinstance(self.decision, SCORMActionDecision):
            raise TypeError("decision must be SCORMActionDecision")
        if self.benchmark_grant is not None and not isinstance(
            self.benchmark_grant,
            SCORMBenchmarkGrant,
        ):
            raise TypeError("benchmark_grant must be SCORMBenchmarkGrant or None")
        exact = (
            self.receipt.preflight_sha256,
            self.receipt.action_decision_sha256,
            self.receipt.action_target_sha256,
            self.receipt.action_sequence,
            self.receipt.action_sha256,
            self.receipt.benchmark_grant_sha256,
        )
        expected = (
            self.observation_authorization.preflight.preflight_sha256,
            self.decision.decision_sha256,
            self.action_target.action_target_sha256,
            self.intent.action_sequence,
            self.intent.action_sha256,
            (
                self.benchmark_grant.benchmark_grant_sha256
                if self.benchmark_grant is not None
                else None
            ),
        )
        if exact != expected:
            raise SCORMRuntimeAuthorityError("action_authorization_binding_mismatch")
        intent_source = self.intent.source_observation_sha256
        if (
            intent_source
            != self.observation_authorization.frame.source_observation_sha256
            or self.action_target.intent_source_observation_sha256 != intent_source
            or self.decision.intent_source_observation_sha256 != intent_source
            or self.receipt.intent_source_observation_sha256 != intent_source
        ):
            raise SCORMRuntimeAuthorityError(
                "action_authorization_intent_source_mismatch"
            )

    def audit_dict(self) -> dict[str, object]:
        receipt = self.receipt
        target = self.action_target
        frame = self.observation_authorization.frame
        return {
            "schema_version": self.schema_version,
            "active_session_id": frame.active_session_id,
            "action_name": receipt.action_name,
            "action_sequence": receipt.action_sequence,
            "action_sha256": receipt.action_sha256,
            "action_decision_sha256": receipt.action_decision_sha256,
            "action_target_sha256": receipt.action_target_sha256,
            "allowed_origin": receipt.allowed_origin,
            "benchmark_grant_sha256": receipt.benchmark_grant_sha256,
            "control_grant_sha256": receipt.control_grant_sha256,
            "coordinates": (
                receipt.coordinates.to_dict() if receipt.coordinates is not None else None
            ),
            "credential_effect": receipt.credential_effect,
            "interaction_kind": receipt.interaction_kind,
            "intent_source_observation_sha256": (
                receipt.intent_source_observation_sha256
            ),
            "launch_plan_sha256": receipt.launch_plan_sha256,
            "launch_url_sha256": receipt.launch_url_sha256,
            "preflight_sha256": receipt.preflight_sha256,
            "launch_authority_sha256": receipt.launch_authority_sha256,
            "provenance": receipt.provenance,
            "provider_context_sha256": receipt.provider_context_sha256,
            "receipt_sha256": receipt.receipt_sha256,
            "replay_nonce_sha256": hashlib.sha256(
                receipt.replay_nonce.encode("utf-8")
            ).hexdigest(),
            "run_authority_sha256": receipt.run_authority_sha256,
            "run_manifest_sha256": receipt.run_manifest_sha256,
            "source_observation_sha256": receipt.source_observation_sha256,
            "source_screenshot_sha256": receipt.source_screenshot_sha256,
            "synthetic_persona_sha256": receipt.synthetic_persona_sha256,
            "target_bounds": (
                target.target_bounds.to_dict()
                if target.target_bounds is not None
                else None
            ),
            "target_evidence_sha256": receipt.target_evidence_sha256,
            "target_semantic": target.target_semantic,
            "target_surface": target.target_surface,
            "visible_evidence_sha256": receipt.visible_evidence_sha256,
            "visible_text_sha256": receipt.visible_text_sha256,
            "window_binding_id": receipt.window_binding_id,
            "window_generation": receipt.window_generation,
            "window_identity_sha256": receipt.window_identity_sha256,
        }

    def to_dict(self) -> dict[str, object]:
        return self.audit_dict()


@dataclass(frozen=True)
class SCORMActionEvaluation:
    """Post-intent policy decision and optional dispatch authority."""

    decision: SCORMActionDecision
    authorization: SCORMActionAuthorization | None

    def __post_init__(self) -> None:
        if not isinstance(self.decision, SCORMActionDecision):
            raise TypeError("decision must be SCORMActionDecision")
        if self.authorization is not None and not isinstance(
            self.authorization,
            SCORMActionAuthorization,
        ):
            raise TypeError("authorization must be SCORMActionAuthorization or None")
        if (self.decision.kind == CONTINUE) != (self.authorization is not None):
            raise SCORMRuntimeAuthorityError("action_evaluation_authority_mismatch")


class SCORMVisionRuntimeAuthority:
    """Concrete local authority shared by planner, executor, and organism."""

    locality = "local"

    def __init__(
        self,
        *,
        active_session: ActiveSCORMCloudSession,
        coherence_gate: HNCScormCoherenceGate,
        run_authority: SCORMRunAuthority,
        provider_context_supplier: ProviderContextSupplier,
        action_target_supplier: ActionTargetSupplier,
        benchmark_grant_supplier: BenchmarkGrantSupplier | None = None,
        utc_now: Callable[[], datetime] | None = None,
    ) -> None:
        if not isinstance(active_session, ActiveSCORMCloudSession):
            raise TypeError("active_session must be ActiveSCORMCloudSession")
        if not isinstance(coherence_gate, HNCScormCoherenceGate):
            raise TypeError("coherence_gate must be HNCScormCoherenceGate")
        if not isinstance(run_authority, SCORMRunAuthority):
            raise TypeError("run_authority must be SCORMRunAuthority")
        if not callable(provider_context_supplier):
            raise TypeError("provider_context_supplier must be callable")
        if not callable(action_target_supplier):
            raise TypeError("action_target_supplier must be callable")
        if benchmark_grant_supplier is not None and not callable(
            benchmark_grant_supplier
        ):
            raise TypeError("benchmark_grant_supplier must be callable")
        plan = active_session.plan
        stable_actual = (
            plan.session_id,
            plan.plan_sha256,
            plan.url_sha256,
            active_session.control_grant_sha256,
        )
        stable_expected = (
            run_authority.run_id,
            run_authority.launch_plan_sha256,
            run_authority.launch_url_sha256,
            run_authority.control_grant_sha256,
        )
        if stable_actual != stable_expected:
            raise SCORMRuntimeAuthorityError("scorm_run_authority_session_mismatch")
        try:
            parsed = urlsplit(plan.exact_url)
            launch_origin = f"{parsed.scheme}://{parsed.netloc}"
        except Exception as exc:
            raise SCORMRuntimeAuthorityError("scorm_launch_origin_invalid") from exc
        if launch_origin != run_authority.allowed_origin:
            raise SCORMRuntimeAuthorityError("scorm_run_origin_session_mismatch")
        if not set(run_authority.allowed_actions).issubset(
            set(plan.allowed_gui_actions)
        ):
            raise SCORMRuntimeAuthorityError("scorm_run_action_scope_exceeds_session")
        self.active_session = active_session
        self.coherence_gate = coherence_gate
        self.run_authority = run_authority
        self.provider_context_supplier = provider_context_supplier
        self.action_target_supplier = action_target_supplier
        self.benchmark_grant_supplier = benchmark_grant_supplier
        self._utc_now = utc_now or (lambda: datetime.now(UTC))

    @property
    def run_authority_sha256(self) -> str:
        return self.run_authority.run_authority_sha256

    @property
    def control_grant_sha256(self) -> str:
        return self.run_authority.control_grant_sha256

    def authorize_binding(self) -> SessionWindowBinding:
        return self.active_session.authorize_binding()

    def authorize_binding_id(self) -> str:
        return self.authorize_binding().binding_id

    def recover_target_window_mismatch(self) -> bool:
        try:
            return bool(self.active_session.handoff_unique_changed_window())
        except Exception:
            return False

    def classify_observation(
        self,
        observation: ScreenObservation,
    ) -> SCORMObservationAuthorization:
        if not isinstance(observation, ScreenObservation):
            raise TypeError("observation must be ScreenObservation")
        binding = self.authorize_binding()
        if self.active_session.authorize_control(observation) is not True:
            raise SCORMRuntimeAuthorityError("scorm_observation_control_not_authorized")
        try:
            provider_context = self.provider_context_supplier(observation, binding)
        except Exception as exc:  # noqa: BLE001 - signed evidence boundary
            raise SCORMRuntimeAuthorityError(
                "scorm_provider_context_unavailable"
            ) from exc
        if not isinstance(provider_context, SCORMProviderContextEvidence):
            raise SCORMRuntimeAuthorityError("scorm_provider_context_type_invalid")
        visible_text = unicodedata.normalize(
            "NFC",
            f"{observation.ocr_text}\n{observation.vision_text}".strip(),
        )
        expected = (
            observation.observation_id,
            observation.screenshot_sha256,
            canonical_visible_evidence_sha256(observation),
            canonical_visible_text_sha256(visible_text),
            binding.session_id,
            binding.binding_id,
            binding.generation,
            binding.window_sha256,
            self.run_authority.run_id,
            self.run_authority.run_manifest_sha256,
            self.run_authority.run_authority_sha256,
            self.run_authority.allowed_origin,
            self.run_authority.launch_url_sha256,
            self.run_authority.launch_plan_sha256,
            self.run_authority.control_grant_sha256,
        )
        actual = (
            provider_context.source_observation_sha256,
            provider_context.source_screenshot_sha256,
            provider_context.visible_evidence_sha256,
            provider_context.visible_text_sha256,
            provider_context.active_session_id,
            provider_context.window_binding_id,
            provider_context.window_generation,
            provider_context.window_identity_sha256,
            provider_context.run_id,
            provider_context.run_manifest_sha256,
            provider_context.run_authority_sha256,
            provider_context.allowed_origin,
            provider_context.launch_url_sha256,
            provider_context.launch_plan_sha256,
            provider_context.control_grant_sha256,
        )
        if actual != expected:
            raise SCORMRuntimeAuthorityError("scorm_provider_context_frame_mismatch")
        frame = SCORMFrameEvidence.from_context(
            provider_context,
            visible_text=visible_text,
        )
        preflight = self.coherence_gate.classify_preflight(
            frame,
            run_authority=self.run_authority,
            provider_context=provider_context,
            now=self._now(),
        )
        return SCORMObservationAuthorization(
            preflight=preflight,
            frame=frame,
            provider_context=provider_context,
        )

    def evaluate_action(
        self,
        observation_authorization: SCORMObservationAuthorization,
        observation: ScreenObservation,
        action: GuiAction,
    ) -> SCORMActionEvaluation:
        self._validate_observation_bundle(observation_authorization, observation)
        if not isinstance(action, GuiAction):
            raise TypeError("action must be GuiAction")
        action_sequence = self.coherence_gate.next_action_sequence(self.run_authority)
        intent = SCORMActionIntent.from_action(
            action.name,
            action.params,
            action_sequence=action_sequence,
            source_observation_sha256=observation.observation_id,
        )
        try:
            action_target = self.action_target_supplier(
                observation_authorization.frame,
                observation_authorization.provider_context,
                intent,
            )
        except Exception as exc:  # noqa: BLE001 - provider target boundary
            raise SCORMRuntimeAuthorityError("scorm_action_target_unavailable") from exc
        if not isinstance(action_target, SCORMActionTargetEvidence):
            raise SCORMRuntimeAuthorityError("scorm_action_target_type_invalid")
        if (
            action_target.intent_source_observation_sha256
            != intent.source_observation_sha256
            or intent.source_observation_sha256
            != observation_authorization.frame.source_observation_sha256
        ):
            raise SCORMRuntimeAuthorityError("scorm_action_target_source_mismatch")
        grant = None
        if self.benchmark_grant_supplier is not None:
            try:
                grant = self.benchmark_grant_supplier(
                    observation_authorization.frame,
                    observation_authorization.provider_context,
                    intent,
                    action_target,
                )
            except Exception as exc:  # noqa: BLE001 - per-action grant boundary
                raise SCORMRuntimeAuthorityError(
                    "scorm_benchmark_grant_unavailable"
                ) from exc
            if grant is not None and not isinstance(grant, SCORMBenchmarkGrant):
                raise SCORMRuntimeAuthorityError("scorm_benchmark_grant_type_invalid")
        decision = self.coherence_gate.classify_action(
            observation_authorization.frame,
            observation_authorization.preflight,
            intent,
            action_target,
            run_authority=self.run_authority,
            provider_context=observation_authorization.provider_context,
            grant=grant,
            now=self._now(),
        )
        if decision.kind != CONTINUE:
            return SCORMActionEvaluation(decision=decision, authorization=None)
        receipt = self.coherence_gate.authorize_action(
            observation_authorization.frame,
            observation_authorization.preflight,
            decision,
            intent,
            action_target,
            run_authority=self.run_authority,
            provider_context=observation_authorization.provider_context,
            grant=grant,
            now=self._now(),
        )
        authorization = SCORMActionAuthorization(
            receipt=receipt,
            observation_authorization=observation_authorization,
            intent=intent,
            action_target=action_target,
            decision=decision,
            benchmark_grant=grant,
        )
        return SCORMActionEvaluation(
            decision=decision,
            authorization=authorization,
        )

    def authorize_action(
        self,
        observation_authorization: SCORMObservationAuthorization,
        observation: ScreenObservation,
        action: GuiAction,
    ) -> SCORMActionAuthorization:
        """Compatibility helper requiring an immediately actionable evaluation."""

        evaluated = self.evaluate_action(
            observation_authorization,
            observation,
            action,
        )
        if evaluated.authorization is None:
            raise SCORMRuntimeAuthorityError("scorm_action_not_authorized")
        return evaluated.authorization

    def verify_and_consume_action(
        self,
        authorization: SCORMActionAuthorization,
        observation: ScreenObservation,
        action: GuiAction,
    ) -> SCORMActionReceipt:
        if not isinstance(authorization, SCORMActionAuthorization):
            raise TypeError("authorization must be SCORMActionAuthorization")
        bundle = authorization.observation_authorization
        self._validate_observation_bundle(bundle, observation)
        if not isinstance(action, GuiAction):
            raise TypeError("action must be GuiAction")
        receipt = authorization.receipt
        if (
            authorization.intent.name != action.name
            or authorization.intent.params != dict(action.params)
            or authorization.intent.source_observation_sha256
            != observation.observation_id
            or receipt.action_sha256
            != canonical_action_sha256(action.name, action.params)
            or receipt.source_observation_sha256 != observation.observation_id
            or receipt.intent_source_observation_sha256
            != observation.observation_id
        ):
            raise SCORMRuntimeAuthorityError("scorm_action_receipt_intent_mismatch")
        binding = self.authorize_binding()
        if (
            binding.binding_id != receipt.window_binding_id
            or binding.generation != receipt.window_generation
            or binding.window_sha256 != receipt.window_identity_sha256
            or self.active_session.authorize_control(observation, action) is not True
        ):
            raise SCORMRuntimeAuthorityError("scorm_action_window_not_authorized")
        return self.coherence_gate.verify_and_consume_action(
            receipt,
            bundle.frame,
            bundle.preflight,
            authorization.intent,
            authorization.action_target,
            run_authority=self.run_authority,
            provider_context=bundle.provider_context,
            grant=authorization.benchmark_grant,
            now=self._now(),
        )

    def _validate_observation_bundle(
        self,
        bundle: SCORMObservationAuthorization,
        observation: ScreenObservation,
    ) -> None:
        if not isinstance(bundle, SCORMObservationAuthorization):
            raise TypeError("bundle must be SCORMObservationAuthorization")
        if not isinstance(observation, ScreenObservation):
            raise TypeError("observation must be ScreenObservation")
        visible_text = unicodedata.normalize(
            "NFC",
            f"{observation.ocr_text}\n{observation.vision_text}".strip(),
        )
        if (
            bundle.frame.source_observation_sha256 != observation.observation_id
            or bundle.frame.source_screenshot_sha256 != observation.screenshot_sha256
            or bundle.frame.visible_evidence_sha256
            != canonical_visible_evidence_sha256(observation)
            or bundle.frame.visible_text_sha256
            != canonical_visible_text_sha256(visible_text)
            or bundle.preflight.run_authority_sha256 != self.run_authority_sha256
        ):
            raise SCORMRuntimeAuthorityError("scorm_observation_bundle_mismatch")

    def _now(self) -> datetime:
        value = self._utc_now()
        if not isinstance(value, datetime) or value.tzinfo is None:
            raise SCORMRuntimeAuthorityError("scorm_authority_clock_invalid")
        return value.astimezone(UTC)


__all__ = [
    "ActionTargetSupplier",
    "BenchmarkGrantSupplier",
    "ProviderContextSupplier",
    "SCORM_ACTION_AUTHORIZATION_SCHEMA",
    "SCORMActionAuthorization",
    "SCORMActionEvaluation",
    "SCORMObservationAuthorization",
    "SCORMRuntimeAuthorityError",
    "SCORMVisionRuntimeAuthority",
]

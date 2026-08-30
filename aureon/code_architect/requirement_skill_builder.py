"""Bounded requirement-to-skill authoring for Aureon's CodeArchitect.

The model-facing surface accepts one strict JSON plan.  Model output never
becomes source code: this module validates an allowlisted declarative plan,
renders deterministic Python, performs compile/static checks, rehearses the
skill against Aureon's in-memory VM backend, and only then commits a
``VALIDATED`` skill that still requires explicit approval.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any, Dict, Mapping, Tuple

from aureon.code_architect.executor import SkillExecutor
from aureon.code_architect.skill import Skill, SkillLevel, SkillProposal, SkillStatus
from aureon.code_architect.skill_library import SkillLibrary, get_skill_library
from aureon.code_architect.validator import SkillValidator

MAX_REQUIREMENT_CHARS = 4_000
MAX_PLAN_CHARS = 32_000
MAX_STEPS = 64

_NAME_RE = re.compile(r"^[a-z][a-z0-9_]{2,63}$")
_INPUT_RE = re.compile(r"^[a-z][a-z0-9_]{0,47}$")
_SECRET_RE = re.compile(
    r"(?:BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY|\bsk_(?:live|proj)_[A-Za-z0-9_-]{8,}|"
    r"\b(?:password|api[_-]?secret|private[_-]?key|credential|access[_-]?token)\b)",
    re.IGNORECASE,
)

# Shell/PowerShell are intentionally absent.  Requirement-authored skills may
# only compose bounded human-interface and read-only observation primitives.
PRIMITIVE_PARAM_KINDS: Dict[str, Dict[str, str]] = {
    "screenshot": {},
    "mouse_move": {"x": "coordinate", "y": "coordinate"},
    "left_click": {"x": "optional_coordinate", "y": "optional_coordinate"},
    "right_click": {"x": "optional_coordinate", "y": "optional_coordinate"},
    "middle_click": {"x": "optional_coordinate", "y": "optional_coordinate"},
    "double_click": {"x": "optional_coordinate", "y": "optional_coordinate"},
    "triple_click": {"x": "optional_coordinate", "y": "optional_coordinate"},
    "left_click_drag": {
        "start_x": "coordinate",
        "start_y": "coordinate",
        "end_x": "coordinate",
        "end_y": "coordinate",
    },
    "scroll": {
        "x": "coordinate",
        "y": "coordinate",
        "direction": "direction",
        "amount": "scroll_amount",
    },
    "type_text": {"text": "text"},
    "press_key": {"key": "key"},
    "hotkey": {"keys": "keys"},
    "get_cursor_position": {},
    "get_screen_size": {},
    "list_windows": {},
    "get_active_window": {},
    "focus_window": {"title": "title"},
    "wait": {"seconds": "wait_seconds"},
}

REQUIRED_PARAMS: Dict[str, frozenset[str]] = {
    "mouse_move": frozenset({"x", "y"}),
    "left_click_drag": frozenset({"start_x", "start_y", "end_x", "end_y"}),
    "scroll": frozenset({"x", "y"}),
    "type_text": frozenset({"text"}),
    "press_key": frozenset({"key"}),
    "hotkey": frozenset({"keys"}),
    "focus_window": frozenset({"title"}),
}


class RequirementSkillError(ValueError):
    """Raised internally when a requirement plan violates its bounded schema."""


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _is_input_ref(value: Any) -> bool:
    return isinstance(value, dict) and set(value) == {"input", "default"}


def _validate_literal(kind: str, value: Any, *, context: str) -> None:
    if kind in {"coordinate", "optional_coordinate"}:
        if value is None and kind == "optional_coordinate":
            return
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise RequirementSkillError(f"{context}_must_be_numeric")
        if not 0 <= float(value) <= 16_384:
            raise RequirementSkillError(f"{context}_out_of_range")
        return
    if kind == "direction":
        if value not in {"up", "down", "left", "right"}:
            raise RequirementSkillError(f"{context}_direction_invalid")
        return
    if kind == "scroll_amount":
        if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 20:
            raise RequirementSkillError(f"{context}_scroll_amount_invalid")
        return
    if kind == "wait_seconds":
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= float(value) <= 1:
            raise RequirementSkillError(f"{context}_wait_invalid")
        return
    if kind == "text":
        if not isinstance(value, str) or len(value) > 2_000:
            raise RequirementSkillError(f"{context}_text_invalid")
        if _SECRET_RE.search(value):
            raise RequirementSkillError(f"{context}_secret_like_text_blocked")
        return
    if kind in {"key", "title"}:
        limit = 64 if kind == "key" else 240
        if not isinstance(value, str) or not value.strip() or len(value) > limit:
            raise RequirementSkillError(f"{context}_{kind}_invalid")
        if _SECRET_RE.search(value):
            raise RequirementSkillError(f"{context}_secret_like_text_blocked")
        return
    if kind == "keys":
        if (
            not isinstance(value, list)
            or not 1 <= len(value) <= 5
            or any(not isinstance(item, str) or not item.strip() or len(item) > 32 for item in value)
        ):
            raise RequirementSkillError(f"{context}_keys_invalid")
        return
    raise RequirementSkillError(f"{context}_unknown_param_kind")


def _python_value(value: Any) -> str:
    if _is_input_ref(value):
        input_name = str(value["input"])
        return f"kwargs.get({input_name!r}, {value['default']!r})"
    return repr(value)


class RequirementSkillBuilder:
    """Create staged, approval-required skills from strict declarative plans."""

    def __init__(
        self,
        *,
        library: SkillLibrary | None = None,
        validator: SkillValidator | None = None,
        adapter: Any = None,
    ) -> None:
        self.library = library if library is not None else get_skill_library()
        self.validator = validator or SkillValidator(strict_static=True)
        self.adapter = adapter

    @staticmethod
    def planning_system_prompt() -> str:
        primitives = sorted(PRIMITIVE_PARAM_KINDS)
        return (
            "Return exactly one JSON object and no Markdown. The only keys are name, description, steps, "
            "and optional sample_inputs. Each step has exactly primitive and params. Primitive must be one "
            f"of {json.dumps(primitives)}. Never emit Python, shell, PowerShell, credentials, secrets, "
            "network calls, or file operations. A reusable parameter may be encoded only as "
            '{"input":"field_name","default":<safe JSON literal>}. '
            "Keep the plan bounded and deterministic."
        )

    def _plan_with_adapter(self, requirement: str, adapter: Any) -> str:
        response = adapter.prompt(
            messages=[{"role": "user", "content": f"Requirement:\n{requirement}"}],
            system=self.planning_system_prompt(),
            max_tokens=2_048,
            temperature=0.0,
        )
        return str(getattr(response, "text", response) or "")

    def _parse_and_validate_plan(
        self,
        raw_plan: str | Mapping[str, Any],
    ) -> Tuple[Dict[str, Any], Dict[str, Tuple[str, Any]]]:
        if isinstance(raw_plan, Mapping):
            text = _canonical_json(dict(raw_plan))
        else:
            text = str(raw_plan or "").strip()
        if not text or len(text) > MAX_PLAN_CHARS:
            raise RequirementSkillError("plan_size_invalid")
        if _SECRET_RE.search(text):
            raise RequirementSkillError("plan_secret_scan_failed")
        try:
            plan = json.loads(text)
        except (TypeError, ValueError) as exc:
            raise RequirementSkillError("strict_json_plan_required") from exc
        if not isinstance(plan, dict):
            raise RequirementSkillError("plan_object_required")
        allowed_top = {"name", "description", "steps", "sample_inputs"}
        if set(plan) - allowed_top or not {"name", "description", "steps"}.issubset(plan):
            raise RequirementSkillError("plan_keys_invalid")

        name = plan.get("name")
        description = plan.get("description")
        steps = plan.get("steps")
        if not isinstance(name, str) or not _NAME_RE.fullmatch(name):
            raise RequirementSkillError("skill_name_invalid")
        if not isinstance(description, str) or not description.strip() or len(description) > 240:
            raise RequirementSkillError("skill_description_invalid")
        if not isinstance(steps, list) or not 1 <= len(steps) <= MAX_STEPS:
            raise RequirementSkillError("skill_steps_invalid")

        input_specs: Dict[str, Tuple[str, Any]] = {}
        normalized_steps = []
        for index, raw_step in enumerate(steps):
            if not isinstance(raw_step, dict) or set(raw_step) != {"primitive", "params"}:
                raise RequirementSkillError(f"step_{index}_shape_invalid")
            primitive = raw_step.get("primitive")
            params = raw_step.get("params")
            if primitive not in PRIMITIVE_PARAM_KINDS:
                raise RequirementSkillError(f"step_{index}_primitive_not_allowlisted")
            if not isinstance(params, dict):
                raise RequirementSkillError(f"step_{index}_params_invalid")
            kinds = PRIMITIVE_PARAM_KINDS[str(primitive)]
            if set(params) - set(kinds):
                raise RequirementSkillError(f"step_{index}_param_not_allowlisted")
            if not REQUIRED_PARAMS.get(str(primitive), frozenset()).issubset(params):
                raise RequirementSkillError(f"step_{index}_required_param_missing")
            if primitive in {
                "left_click",
                "right_click",
                "middle_click",
                "double_click",
                "triple_click",
            } and (("x" in params) != ("y" in params)):
                raise RequirementSkillError(f"step_{index}_click_coordinates_incomplete")

            normalized_params: Dict[str, Any] = {}
            for param_name, value in params.items():
                kind = kinds[param_name]
                if _is_input_ref(value):
                    input_name = value.get("input")
                    default = value.get("default")
                    if not isinstance(input_name, str) or not _INPUT_RE.fullmatch(input_name):
                        raise RequirementSkillError(f"step_{index}_{param_name}_input_name_invalid")
                    if _SECRET_RE.search(input_name):
                        raise RequirementSkillError(f"step_{index}_{param_name}_secret_input_blocked")
                    _validate_literal(kind, default, context=f"step_{index}_{param_name}_default")
                    prior = input_specs.get(input_name)
                    if prior is not None and prior != (kind, default):
                        raise RequirementSkillError(f"input_{input_name}_definition_conflict")
                    input_specs[input_name] = (kind, default)
                    normalized_params[param_name] = {"input": input_name, "default": default}
                else:
                    if isinstance(value, dict):
                        raise RequirementSkillError(f"step_{index}_{param_name}_object_invalid")
                    _validate_literal(kind, value, context=f"step_{index}_{param_name}")
                    normalized_params[param_name] = value
            normalized_steps.append({"primitive": primitive, "params": normalized_params})

        samples = plan.get("sample_inputs") or {}
        if not isinstance(samples, dict) or set(samples) - set(input_specs):
            raise RequirementSkillError("sample_inputs_invalid")
        normalized_samples: Dict[str, Any] = {}
        for input_name, value in samples.items():
            kind, _default = input_specs[input_name]
            _validate_literal(kind, value, context=f"sample_{input_name}")
            normalized_samples[input_name] = value

        normalized = {
            "name": name,
            "description": description.strip(),
            "steps": normalized_steps,
            "sample_inputs": normalized_samples,
        }
        return normalized, input_specs

    @staticmethod
    def _render_source(plan: Mapping[str, Any]) -> str:
        lines = [f"def {plan['name']}(**kwargs):", f"    {plan['description']!r}", "    results = []"]
        for step in plan["steps"]:
            args = ["session_id=kwargs.get('session_id')"]
            for key, value in step["params"].items():
                args.append(f"{key}={_python_value(value)}")
            lines.append(f"    results.append(vm_{step['primitive']}({', '.join(args)}))")
        lines.extend(
            [
                "    ok = True",
                "    for result in results:",
                "        if not bool(result.get('ok', False)):",
                "            ok = False",
                "    return {'ok': ok, 'steps': len(results), 'results': results}",
            ]
        )
        return "\n".join(lines) + "\n"

    @staticmethod
    def _params_schema(input_specs: Mapping[str, Tuple[str, Any]]) -> Dict[str, Any]:
        properties: Dict[str, Any] = {"session_id": {"type": "string"}}
        for name, (kind, default) in input_specs.items():
            if kind in {"coordinate", "optional_coordinate", "scroll_amount", "wait_seconds"}:
                json_type = "number"
            elif kind == "keys":
                json_type = "array"
            else:
                json_type = "string"
            properties[name] = {"type": json_type, "default": default}
        return {"type": "object", "properties": properties, "additionalProperties": False}

    def _validate_in_staging(
        self,
        proposal: SkillProposal,
        simulation_inputs: Mapping[str, Any],
    ) -> Dict[str, Any]:
        validation: Dict[str, Any] = {
            "compile_ok": False,
            "static_safe": False,
            "simulation_ok": False,
            "simulation_backend": "simulated",
        }
        try:
            compile(proposal.code, f"<requirement-skill:{proposal.name}>", "exec")
            validation["compile_ok"] = True
        except Exception as exc:
            validation["compile_error"] = f"{type(exc).__name__}: {exc}"
            return validation

        static_ok, static_errors = self.validator.static_check(proposal.code)
        validation["static_safe"] = bool(static_ok)
        validation["static_errors"] = list(static_errors[:10])
        if not static_ok:
            return validation

        from aureon.autonomous.vm_control import VMControlDispatcher

        dispatcher = VMControlDispatcher()
        session_id = ""
        try:
            session_id = dispatcher.create_session(
                backend="simulated",
                name=f"requirement-skill-{proposal.name}",
                make_default=True,
            )
            controller = dispatcher.get_session(session_id)
            if controller is None:
                validation["simulation_error"] = "simulated_session_missing"
                return validation
            controller.arm(dry_run=False)
            with tempfile.TemporaryDirectory(prefix="aureon_requirement_skill_stage_") as temp_dir:
                stage_library = SkillLibrary(storage_dir=Path(temp_dir) / "skills")
                staged_skill = Skill.from_proposal(proposal)
                staged_skill.status = SkillStatus.APPROVED
                staged_skill.tags = ["requirement_generated", "live_execution_disabled"]
                stage_library.add(staged_skill)
                executor = SkillExecutor(
                    library=stage_library,
                    dispatcher=dispatcher,
                    validator=self.validator,
                )
                params = dict(simulation_inputs)
                params["session_id"] = session_id
                result = executor.execute(staged_skill, params=params)
                returned = result.return_value
                validation["simulation_ok"] = bool(
                    result.ok and isinstance(returned, dict) and returned.get("ok") is True
                )
                validation["simulation_error"] = str(result.error or "")
                if result.ok and not validation["simulation_ok"]:
                    validation["simulation_error"] = "simulated_skill_reported_failure"
                validation["simulation_duration_s"] = round(float(result.duration_s), 6)
        except Exception as exc:
            validation["simulation_error"] = f"{type(exc).__name__}: {exc}"
        finally:
            dispatcher.destroy_all()
        return validation

    def _restore_library_file(self, existed: bool, content: bytes) -> None:
        path = self.library.library_path
        if not existed:
            path.unlink(missing_ok=True)
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".rollback", dir=str(path.parent))
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_name, path)
        finally:
            Path(temp_name).unlink(missing_ok=True)

    def _persist_skill_transaction(self, skill: Skill) -> Tuple[bool, bool, str]:
        lock = getattr(self.library, "_lock", None)
        if lock is None:
            raise RequirementSkillError("skill_library_lock_unavailable")
        with lock:
            prior = copy.deepcopy(self.library.get(skill.name))
            existed = self.library.library_path.exists()
            before = self.library.library_path.read_bytes() if existed else b""
            try:
                self.library.add(skill, persist=False)
                self.library.save()
                payload = json.loads(self.library.library_path.read_text(encoding="utf-8"))
                records = payload.get("skills", []) if isinstance(payload, dict) else []
                committed = next(
                    (item for item in records if isinstance(item, dict) and item.get("name") == skill.name),
                    None,
                )
                if committed is None or _canonical_json(committed) != _canonical_json(skill.to_dict()):
                    raise OSError("skill_library_commit_verification_failed")
                return True, False, ""
            except Exception as exc:
                rollback_error = ""
                try:
                    self.library.remove(skill.name, persist=False)
                    if prior is not None:
                        self.library.add(prior, persist=False)
                    self._restore_library_file(existed, before)
                except Exception as rollback_exc:
                    rollback_error = f"; rollback={type(rollback_exc).__name__}: {rollback_exc}"
                return False, not rollback_error, f"{type(exc).__name__}: {exc}{rollback_error}"

    def _remove_skill_transaction(self, name: str) -> Tuple[bool, bool, str]:
        lock = getattr(self.library, "_lock", None)
        if lock is None:
            raise RequirementSkillError("skill_library_lock_unavailable")
        with lock:
            prior = copy.deepcopy(self.library.get(name))
            if prior is None:
                return False, False, "skill_not_found"
            existed = self.library.library_path.exists()
            before = self.library.library_path.read_bytes() if existed else b""
            try:
                self.library.remove(name, persist=False)
                self.library.save()
                payload = json.loads(self.library.library_path.read_text(encoding="utf-8"))
                records = payload.get("skills", []) if isinstance(payload, dict) else []
                if any(isinstance(item, dict) and item.get("name") == name for item in records):
                    raise OSError("skill_library_removal_verification_failed")
                return True, False, ""
            except Exception as exc:
                rollback_error = ""
                try:
                    self.library.add(prior, persist=False)
                    self._restore_library_file(existed, before)
                except Exception as rollback_exc:
                    rollback_error = f"; rollback={type(rollback_exc).__name__}: {rollback_exc}"
                return False, not rollback_error, f"{type(exc).__name__}: {exc}{rollback_error}"

    def build(
        self,
        requirement: str,
        *,
        plan: str | Mapping[str, Any] | None = None,
        adapter: Any = None,
        simulation_inputs: Mapping[str, Any] | None = None,
    ) -> Dict[str, Any]:
        requirement_text = str(requirement or "").strip()
        if not requirement_text or len(requirement_text) > MAX_REQUIREMENT_CHARS:
            return {"ok": False, "status": "rejected", "reason": "requirement_size_invalid"}
        if _SECRET_RE.search(requirement_text):
            return {"ok": False, "status": "rejected", "reason": "requirement_secret_scan_failed"}
        try:
            raw_plan = plan
            if raw_plan is None:
                planner = adapter or self.adapter
                if planner is None:
                    raise RequirementSkillError("declarative_plan_or_adapter_required")
                raw_plan = self._plan_with_adapter(requirement_text, planner)
            normalized, input_specs = self._parse_and_validate_plan(raw_plan)
            if self.library.contains(normalized["name"]):
                raise RequirementSkillError("skill_name_already_exists")

            samples = dict(normalized.get("sample_inputs") or {})
            for input_name, value in dict(simulation_inputs or {}).items():
                if input_name not in input_specs:
                    raise RequirementSkillError("simulation_input_not_declared")
                kind, _default = input_specs[input_name]
                _validate_literal(kind, value, context=f"simulation_{input_name}")
                samples[input_name] = value

            source = self._render_source(normalized)
            plan_digest = _sha256_text(_canonical_json(normalized))
            proposal = SkillProposal(
                name=normalized["name"],
                description=normalized["description"],
                level=SkillLevel.TASK,
                category="requirement_generated",
                code=source,
                entry_function=normalized["name"],
                params_schema=self._params_schema(input_specs),
                dependencies=[],
                observation_sources=[f"requirement_sha256:{_sha256_text(requirement_text)}"],
                created_by="requirement_skill_builder",
                reasoning="Deterministically rendered from an allowlisted declarative primitive plan.",
                target="vm",
            )
            validation = self._validate_in_staging(proposal, samples)
            if not all(validation.get(key) is True for key in ("compile_ok", "static_safe", "simulation_ok")):
                return {
                    "ok": False,
                    "status": "validation_failed",
                    "reason": "compile_static_or_simulation_failed",
                    "skill_name": proposal.name,
                    "plan_digest": plan_digest,
                    "source_digest": _sha256_text(source),
                    "validation": validation,
                    "persisted": False,
                    "rolled_back": True,
                }

            skill = Skill.from_proposal(proposal)
            skill.status = SkillStatus.VALIDATED
            skill.tags = [
                "requirement_generated",
                "requires_explicit_approval",
                "live_execution_disabled",
                f"plan_sha256:{plan_digest}",
            ]
            committed, rolled_back, error = self._persist_skill_transaction(skill)
            if not committed:
                return {
                    "ok": False,
                    "status": "library_commit_failed",
                    "reason": error,
                    "skill_name": skill.name,
                    "plan_digest": plan_digest,
                    "source_digest": _sha256_text(source),
                    "validation": validation,
                    "persisted": False,
                    "rolled_back": rolled_back,
                }
            return {
                "ok": True,
                "status": "validated_pending_approval",
                "skill_name": skill.name,
                "skill_status": skill.status.value,
                "plan_digest": plan_digest,
                "source_digest": _sha256_text(source),
                "step_count": len(normalized["steps"]),
                "validation": validation,
                "persisted": True,
                "live_execution_enabled": False,
                "library_path": str(self.library.library_path),
            }
        except RequirementSkillError as exc:
            return {"ok": False, "status": "rejected", "reason": str(exc), "persisted": False}
        except Exception as exc:
            return {
                "ok": False,
                "status": "error",
                "reason": f"{type(exc).__name__}: {exc}",
                "persisted": False,
            }

    def approve_skill(
        self,
        name: str,
        *,
        reviewer: str,
        enable_live: bool = False,
    ) -> Dict[str, Any]:
        skill = self.library.get(str(name or ""))
        if skill is None:
            return {"ok": False, "status": "not_found", "reason": "skill_not_found"}
        if "requirement_generated" not in skill.tags:
            return {"ok": False, "status": "rejected", "reason": "not_requirement_generated"}
        reviewer_text = str(reviewer or "").strip()
        if not reviewer_text or len(reviewer_text) > 120:
            return {"ok": False, "status": "rejected", "reason": "reviewer_required"}

        approved = copy.deepcopy(skill)
        approved.status = SkillStatus.APPROVED
        approved.tags = [tag for tag in approved.tags if not tag.startswith("approved_by:")]
        approved.tags.append(f"approved_by:{reviewer_text}")
        if enable_live:
            approved.tags = [tag for tag in approved.tags if tag != "live_execution_disabled"]
        elif "live_execution_disabled" not in approved.tags:
            approved.tags.append("live_execution_disabled")
        committed, rolled_back, error = self._persist_skill_transaction(approved)
        return {
            "ok": committed,
            "status": "approved" if committed else "approval_commit_failed",
            "skill_name": approved.name,
            "skill_status": approved.status.value if committed else skill.status.value,
            "live_execution_enabled": committed and "live_execution_disabled" not in approved.tags,
            "rolled_back": rolled_back,
            "reason": error,
        }

    def reject_skill(self, name: str, *, reviewer: str, reason: str = "rejected") -> Dict[str, Any]:
        skill = self.library.get(str(name or ""))
        if skill is None:
            return {"ok": False, "status": "not_found", "reason": "skill_not_found"}
        if "requirement_generated" not in skill.tags:
            return {"ok": False, "status": "rejected", "reason": "not_requirement_generated"}
        if not str(reviewer or "").strip():
            return {"ok": False, "status": "rejected", "reason": "reviewer_required"}
        removed, rolled_back, error = self._remove_skill_transaction(skill.name)
        return {
            "ok": removed,
            "status": "removed_rejected_skill" if removed else "rejection_commit_failed",
            "skill_name": skill.name,
            "reviewer": str(reviewer).strip()[:120],
            "reject_reason": str(reason or "rejected")[:240],
            "rolled_back": rolled_back,
            "reason": error,
        }


__all__ = [
    "MAX_STEPS",
    "PRIMITIVE_PARAM_KINDS",
    "RequirementSkillBuilder",
    "RequirementSkillError",
]

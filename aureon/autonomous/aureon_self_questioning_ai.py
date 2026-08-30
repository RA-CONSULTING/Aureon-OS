"""Safe self-questioning autonomy for the Aureon organism.

This module gives Aureon a local inner loop:

1. inspect its own wiring, service, and integration state;
2. ask a local Ollama model what needs attention;
3. write the reasoning into the Obsidian vault;
4. publish the result onto ThoughtBus for the rest of the organism.

The loop is intentionally safe. It can create memory, emit thoughts, and queue
research/repair intentions. It never places exchange orders and never edits code
directly. Code mutation belongs to the existing authoring/refinement pipeline.
"""

from __future__ import annotations

from aureon.core.aureon_baton_link import link_system as _baton_link

_baton_link(__name__)

import argparse
import datetime as dt
import json
import os
import re
import threading
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence

from aureon.core.aureon_runtime_safety import (
    live_trading_enabled,
    apply_safe_runtime_environment,
    real_orders_allowed,
)
from aureon.core.aureon_thought_bus import Thought, ThoughtBus
from aureon.autonomous.aureon_goal_capability_map import build_goal_capability_map
from aureon.integrations.obsidian import ObsidianBridge
from aureon.obsidian_paths import resolve_obsidian_vault_path
from aureon.integrations.ollama import OllamaBridge

REPO_ROOT = Path(__file__).resolve().parents[2]
STATE_LOG = REPO_ROOT / "state" / "self_questioning_ai_cycles.jsonl"

DEFAULT_QUESTIONS = (
    "What is unhealthy, unwired, or drifting in my current organism state?",
    "Which skills, tools, logic modules, and code systems should I route through for the current goal?",
    "How should my cognitive systems think on their feet about the unhackable SaaS pursuit loop?",
    "What SaaS frontend, API, dashboard, and operator surfaces exist, and what must be unified next?",
    "Does my accounting/compliance state need safe review, final-ready pack generation, vault ingestion, or human filing action?",
    "Which safe action can I take next without live trading or exchange mutation?",
    "What evidence should I remember in Obsidian so the next cycle is smarter?",
    "What requires human approval before I proceed?",
)

ALLOWED_ACTION_TYPES = {
    "write_obsidian_note",
    "publish_thought",
    "queue_research",
    "run_audit_probe",
    "ask_human",
    "no_op",
}

BLOCKED_ACTION_WORDS = (
    "place order",
    "real order",
    "live order",
    "live trade",
    "margin trade",
    "exchange mutation",
    "withdraw",
    "deposit",
    "transfer funds",
    "api key",
    "secret key",
)

FAST_SELF_QUESTIONING_MODELS = (
    "qwen2.5:0.5b",
    "llama3.2:1b",
    "phi3:mini",
    "llama3:latest",
    "llama3",
)
DEFAULT_SELF_QUESTIONING_TIMEOUT_S = 120.0
DEFAULT_SELF_QUESTIONING_NUM_PREDICT = 192


def _utc_now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def _json_default(value: Any) -> str:
    return str(value)


def _append_jsonl(path: Path, record: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, default=_json_default, sort_keys=True) + "\n")


def _tail_jsonl(path: Path, limit: int = 20) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    out: List[Dict[str, Any]] = []
    try:
        for raw in path.read_text(encoding="utf-8", errors="replace").splitlines()[-limit:]:
            raw = raw.strip()
            if not raw:
                continue
            try:
                out.append(json.loads(raw))
            except Exception:
                continue
    except Exception:
        return []
    return out


def resolve_default_obsidian_vault(repo_root: Path = REPO_ROOT) -> Path:
    """Resolve the canonical external vault; keep the argument for compatibility."""

    _ = repo_root
    return resolve_obsidian_vault_path()


def _extract_json_object(text: str) -> Optional[Dict[str, Any]]:
    if not text:
        return None
    text = text.strip()
    try:
        data = json.loads(text)
        return data if isinstance(data, dict) else None
    except Exception:
        pass

    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.S)
    if fenced:
        try:
            data = json.loads(fenced.group(1))
            return data if isinstance(data, dict) else None
        except Exception:
            pass

    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        try:
            data = json.loads(text[start : end + 1])
            return data if isinstance(data, dict) else None
        except Exception:
            return None
    return None


@dataclass
class SelfQuestionAction:
    title: str
    action_type: str = "no_op"
    priority: int = 3
    risk: str = "low"
    requires_human: bool = False
    details: str = ""
    blocked: bool = False
    blocked_reason: str = ""

    @classmethod
    def from_any(cls, raw: Any) -> "SelfQuestionAction":
        if isinstance(raw, cls):
            return raw
        if not isinstance(raw, dict):
            return cls(title=str(raw or "No action"), details=str(raw or ""))
        return cls(
            title=str(raw.get("title") or raw.get("name") or "Untitled action"),
            action_type=str(raw.get("action_type") or raw.get("type") or "no_op"),
            priority=int(raw.get("priority") or 3),
            risk=str(raw.get("risk") or "low"),
            requires_human=bool(raw.get("requires_human", False)),
            details=str(raw.get("details") or raw.get("description") or ""),
        )

    def sanitised(self) -> "SelfQuestionAction":
        text = f"{self.title} {self.action_type} {self.details}".lower()
        action_type = self.action_type if self.action_type in ALLOWED_ACTION_TYPES else "queue_research"
        blocked_words = [word for word in BLOCKED_ACTION_WORDS if word in text]
        blocked = bool(blocked_words)
        reason = ""
        if blocked:
            reason = "blocked unsafe live-trading/exchange action: " + ", ".join(blocked_words)
            action_type = "ask_human"
        return SelfQuestionAction(
            title=self.title,
            action_type=action_type,
            priority=max(1, min(5, int(self.priority))),
            risk=self.risk,
            requires_human=bool(self.requires_human or blocked),
            details=self.details,
            blocked=blocked,
            blocked_reason=reason,
        )


@dataclass
class SelfQuestioningCycle:
    cycle_id: str
    timestamp: float
    iso_time: str
    questions: List[str]
    context: Dict[str, Any]
    summary: str
    answers: List[Dict[str, Any]]
    next_actions: List[SelfQuestionAction] = field(default_factory=list)
    answer_source: str = "fallback"
    note_path: str = ""
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["next_actions"] = [asdict(action) for action in self.next_actions]
        return data


class SelfQuestioningAI:
    """A safe local AI loop backed by Ollama, Obsidian, and ThoughtBus."""

    def __init__(
        self,
        repo_root: Optional[Path] = None,
        obsidian: Optional[ObsidianBridge] = None,
        ollama: Optional[OllamaBridge] = None,
        thought_bus: Optional[ThoughtBus] = None,
        state_path: Optional[Path] = None,
        safe_mode: bool = True,
    ) -> None:
        self.repo_root = Path(repo_root or REPO_ROOT).resolve()
        self.state_path = Path(state_path or (self.repo_root / "state" / "self_questioning_ai_cycles.jsonl"))
        self.safe_mode = bool(safe_mode)
        if self.safe_mode and not live_trading_enabled():
            apply_safe_runtime_environment()
        self.ollama_timeout_s = float(
            os.environ.get(
                "AUREON_SELF_QUESTIONING_OLLAMA_TIMEOUT_S",
                str(DEFAULT_SELF_QUESTIONING_TIMEOUT_S),
            )
        )
        self.ollama_num_predict = int(
            os.environ.get(
                "AUREON_SELF_QUESTIONING_NUM_PREDICT",
                str(DEFAULT_SELF_QUESTIONING_NUM_PREDICT),
            )
        )

        vault_path = resolve_default_obsidian_vault(self.repo_root)
        prefer_fs = not bool(os.environ.get("AUREON_OBSIDIAN_API_KEY", "").strip())
        self.obsidian = obsidian or ObsidianBridge(
            vault_path=str(vault_path),
            prefer_filesystem=prefer_fs,
        )
        self.ollama = ollama or OllamaBridge(
            chat_model=os.environ.get("AUREON_SELF_QUESTIONING_OLLAMA_MODEL") or None,
            timeout_s=self.ollama_timeout_s,
        )
        self.thought_bus = thought_bus or ThoughtBus(
            persist_path=str(self.repo_root / "state" / "self_questioning_thoughts.jsonl")
        )
        self.last_cycle: Optional[SelfQuestioningCycle] = None
        self._cycle_lock = threading.Lock()

    # ------------------------------------------------------------------
    # Public surface
    # ------------------------------------------------------------------
    def get_status(self) -> Dict[str, Any]:
        ollama_snapshot = self._safe_snapshot(self.ollama)
        goal_map = build_goal_capability_map(repo_root=self.repo_root).compact()
        return {
            "safe_mode": self.safe_mode,
            "real_orders_allowed": real_orders_allowed(),
            "goal_capability_map": goal_map,
            "repo_self_catalog": self._read_repo_self_catalog(
                self.repo_root / "docs" / "audits" / "aureon_repo_self_catalog.json"
            ),
            "capability_growth_loop": self._read_capability_growth_loop(
                self.repo_root / "docs" / "audits" / "aureon_capability_growth_loop.json"
            ),
            "ollama": ollama_snapshot,
            "selected_ollama_model": self._select_chat_model(ollama_snapshot),
            "ollama_timeout_s": self.ollama_timeout_s,
            "ollama_num_predict": self.ollama_num_predict,
            "obsidian": self._safe_snapshot(self.obsidian),
            "state_path": str(self.state_path),
            "last_cycle": self._compact_cycle_for_status(self.last_cycle) if self.last_cycle else None,
        }

    def run_cycle(
        self,
        questions: Optional[Sequence[str]] = None,
        include_audit: bool = True,
        include_self_scan: bool = True,
        augment_questions: bool = True,
    ) -> SelfQuestioningCycle:
        if not self._cycle_lock.acquire(blocking=False):
            return self._busy_cycle(questions)
        try:
            return self._run_cycle_locked(
                questions=questions,
                include_audit=include_audit,
                include_self_scan=include_self_scan,
                augment_questions=augment_questions,
            )
        finally:
            self._cycle_lock.release()

    def _run_cycle_locked(
        self,
        questions: Optional[Sequence[str]] = None,
        include_audit: bool = True,
        include_self_scan: bool = True,
        augment_questions: bool = True,
    ) -> SelfQuestioningCycle:
        if self.safe_mode and not live_trading_enabled():
            apply_safe_runtime_environment()
        errors: List[str] = []

        now = _utc_now()
        cycle_id = f"selfq_{now.strftime('%Y%m%dT%H%M%S')}_{uuid.uuid4().hex[:8]}"
        context = self._build_context(
            include_audit=include_audit,
            include_self_scan=include_self_scan,
            errors=errors,
        )
        question_list = self._build_questions(context, questions, augment=augment_questions)
        context["goal_capability_map"] = build_goal_capability_map(
            repo_root=self.repo_root,
            current_goal=" ".join(question_list),
        ).to_dict()

        self._publish(
            "autonomy.self_question.ask",
            {"cycle_id": cycle_id, "questions": question_list},
        )
        self._publish_goal_directive(cycle_id, context)

        answer_payload = self._ask_ollama(question_list, context, errors)
        actions = [
            SelfQuestionAction.from_any(item).sanitised()
            for item in answer_payload.get("next_actions", [])
        ]
        if not actions:
            actions = self._fallback_actions(context)

        cycle = SelfQuestioningCycle(
            cycle_id=cycle_id,
            timestamp=now.timestamp(),
            iso_time=now.isoformat(),
            questions=question_list,
            context=context,
            summary=str(answer_payload.get("summary") or "Self-questioning cycle completed."),
            answers=list(answer_payload.get("answers") or []),
            next_actions=actions,
            answer_source=str(answer_payload.get("answer_source") or "fallback"),
            errors=errors,
        )

        cycle.note_path = self._write_obsidian_cycle(cycle)
        _append_jsonl(self.state_path, cycle.to_dict())
        self.last_cycle = cycle

        self._publish(
            "autonomy.self_question.answer",
            {
                "cycle_id": cycle.cycle_id,
                "summary": cycle.summary,
                "answer_source": cycle.answer_source,
                "note_path": cycle.note_path,
                "actions": [asdict(action) for action in cycle.next_actions],
            },
        )
        self._publish_safe_research_actions(cycle)
        return cycle

    def _busy_cycle(self, questions: Optional[Sequence[str]]) -> SelfQuestioningCycle:
        now = _utc_now()
        question_list = [str(q).strip() for q in (questions or DEFAULT_QUESTIONS) if str(q).strip()]
        action = SelfQuestionAction(
            title="Wait for the active self-questioning cycle",
            action_type="publish_thought",
            priority=2,
            risk="low",
            details="A self-questioning cycle is already running; skip overlap and let the active cycle finish.",
        ).sanitised()
        cycle = SelfQuestioningCycle(
            cycle_id=f"selfq_busy_{now.strftime('%Y%m%dT%H%M%S')}_{uuid.uuid4().hex[:8]}",
            timestamp=now.timestamp(),
            iso_time=now.isoformat(),
            questions=question_list,
            context={"safe_mode": self.safe_mode, "real_orders_allowed": real_orders_allowed()},
            summary="Self-questioning cycle skipped because another cycle is already running.",
            answers=[
                {
                    "question": question_list[0] if question_list else "cycle busy",
                    "answer": "The safe action is to avoid overlapping Ollama reasoning and wait for the active cycle.",
                    "evidence": ["cycle lock already held"],
                }
            ],
            next_actions=[action],
            answer_source="busy",
        )
        self.last_cycle = cycle
        self._publish(
            "autonomy.self_question.busy",
            {"cycle_id": cycle.cycle_id, "summary": cycle.summary},
        )
        return cycle

    # ------------------------------------------------------------------
    # Observation
    # ------------------------------------------------------------------
    def _build_context(
        self,
        include_audit: bool,
        include_self_scan: bool,
        errors: List[str],
    ) -> Dict[str, Any]:
        context: Dict[str, Any] = {
            "repo_root": str(self.repo_root),
            "safe_mode": self.safe_mode,
            "real_orders_allowed": real_orders_allowed(),
            "runtime_flags": {
                "AUREON_AUDIT_MODE": os.environ.get("AUREON_AUDIT_MODE"),
                "AUREON_LIVE_TRADING": os.environ.get("AUREON_LIVE_TRADING"),
                "AUREON_DISABLE_REAL_ORDERS": os.environ.get("AUREON_DISABLE_REAL_ORDERS"),
            },
            "ollama": self._safe_snapshot(self.ollama),
            "obsidian": self._safe_snapshot(self.obsidian),
            "accounting": self._accounting_context_snapshot(errors),
            "saas_security": self._saas_security_snapshot(errors),
            "saas_product_inventory": self._saas_product_inventory_snapshot(errors),
            "repo_self_catalog": self._read_repo_self_catalog(
                self.repo_root / "docs" / "audits" / "aureon_repo_self_catalog.json"
            ),
            "capability_growth_loop": self._read_capability_growth_loop(
                self.repo_root / "docs" / "audits" / "aureon_capability_growth_loop.json"
            ),
            "goal_capability_map": build_goal_capability_map(repo_root=self.repo_root).to_dict(),
            "contract_stack": self._contract_stack_snapshot(errors),
            "previous_cycles": self._compact_previous_cycles(_tail_jsonl(self.state_path, limit=3)),
        }

        manifest_path = self.repo_root / "docs" / "audits" / "mind_wiring_audit.json"
        context["mind_wiring"] = self._read_mind_wiring_counts(manifest_path)

        try:
            context["recent_thoughts"] = self.thought_bus.recall(limit=10)
        except Exception as exc:
            errors.append(f"thought recall failed: {exc}")
            context["recent_thoughts"] = []

        if include_audit:
            context["integration_audit"] = self._run_integration_audit(errors)

        if include_self_scan:
            context["self_scan"] = self._run_self_scan(errors)

        context["obsidian_memory_hits"] = self._search_obsidian_memory(errors)
        return context

    def _read_repo_self_catalog(self, manifest_path: Path) -> Dict[str, Any]:
        if not manifest_path.exists():
            return {"available": False, "path": str(manifest_path)}
        try:
            data = json.loads(manifest_path.read_text(encoding="utf-8", errors="replace"))
            summary = data.get("summary") or {}
            return {
                "available": True,
                "path": str(manifest_path),
                "status": data.get("status"),
                "summary": {
                    "cataloged_file_count": summary.get("cataloged_file_count"),
                    "domain_count": summary.get("domain_count"),
                    "subsystem_count": summary.get("subsystem_count"),
                    "file_kind_count": summary.get("file_kind_count"),
                    "secret_metadata_only_count": summary.get("secret_metadata_only_count"),
                    "coverage_policy": summary.get("coverage_policy"),
                },
                "domain_counts": data.get("domain_counts") or {},
                "subsystem_counts": data.get("subsystem_counts") or {},
                "vault_memory": data.get("vault_memory") or {},
                "sample_labels": [
                    {
                        "path": label.get("path"),
                        "subsystem": label.get("subsystem"),
                        "file_kind": label.get("file_kind"),
                        "organism_domain": label.get("organism_domain"),
                        "llm_context": label.get("llm_context"),
                    }
                    for label in (data.get("labels") or [])[:12]
                ],
            }
        except Exception as exc:
            return {"available": False, "path": str(manifest_path), "error": str(exc)}

    def _read_capability_growth_loop(self, manifest_path: Path) -> Dict[str, Any]:
        if not manifest_path.exists():
            return {"available": False, "path": str(manifest_path)}
        try:
            data = json.loads(manifest_path.read_text(encoding="utf-8", errors="replace"))
            latest = (data.get("iterations") or [{}])[-1] or {}
            return {
                "available": True,
                "path": str(manifest_path),
                "status": data.get("status"),
                "summary": data.get("summary") or {},
                "latest_iteration_summary": latest.get("summary") or {},
                "latest_gap_ids": [gap.get("id") for gap in (latest.get("gaps") or [])[:12]],
                "vault_memory": data.get("vault_memory") or {},
            }
        except Exception as exc:
            return {"available": False, "path": str(manifest_path), "error": str(exc)}

    def _saas_security_snapshot(self, errors: List[str]) -> Dict[str, Any]:
        try:
            bridge_path = self.repo_root / "docs" / "audits" / "hnc_saas_cognitive_bridge.json"
            blueprint_path = self.repo_root / "docs" / "audits" / "hnc_saas_security_blueprint.json"
            attack_lab_path = self.repo_root / "docs" / "audits" / "hnc_authorized_attack_lab.json"

            def read(path: Path) -> Dict[str, Any]:
                if not path.exists():
                    return {"available": False, "path": str(path)}
                data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
                return {"available": True, "path": str(path), **data}

            bridge = read(bridge_path)
            blueprint = read(blueprint_path)
            attack_lab = read(attack_lab_path)
            b_summary = blueprint.get("summary") or {}
            a_summary = attack_lab.get("summary") or {}
            c_summary = bridge.get("summary") or {}
            return {
                "available": bool(bridge.get("available") or blueprint.get("available") or attack_lab.get("available")),
                "status": bridge.get("status") or blueprint.get("status") or attack_lab.get("status"),
                "summary": {
                    "unhackable_benchmark_count": b_summary.get("unhackable_benchmark_count", c_summary.get("unhackable_benchmark_count", 0)),
                    "release_gate_count": b_summary.get("release_gate_count", 0),
                    "attack_case_count": a_summary.get("attack_case_count", c_summary.get("attack_case_count", 0)),
                    "executed_simulation_count": a_summary.get("executed_simulation_count", 0),
                    "actionable_finding_count": a_summary.get("actionable_finding_count", c_summary.get("actionable_finding_count", 0)),
                    "production_deploy_blocked_until_gates_pass": b_summary.get("production_deploy_blocked_until_gates_pass", True),
                },
                "cognitive_bridge": {
                    "available": bool(bridge.get("available")),
                    "status": bridge.get("status"),
                    "summary": c_summary,
                    "question_count": len(bridge.get("questions") or []),
                    "decision_count": len(bridge.get("decisions") or []),
                    "thought_topics": bridge.get("thought_topics") or {},
                },
                "attack_lab": {
                    "available": bool(attack_lab.get("available")),
                    "status": attack_lab.get("status"),
                    "summary": a_summary,
                    "findings": (attack_lab.get("findings") or [])[:8],
                },
                "blueprint": {
                    "available": bool(blueprint.get("available")),
                    "status": blueprint.get("status"),
                    "summary": b_summary,
                    "release_gates": (blueprint.get("release_gates") or [])[:8],
                },
            }
        except Exception as exc:
            errors.append(f"saas security snapshot failed: {exc}")
            return {"available": False, "error": str(exc)}

    def _saas_product_inventory_snapshot(self, errors: List[str]) -> Dict[str, Any]:
        try:
            inventory_path = self.repo_root / "docs" / "audits" / "aureon_saas_system_inventory.json"
            plan_path = self.repo_root / "docs" / "audits" / "aureon_frontend_unification_plan.json"

            def read(path: Path) -> Dict[str, Any]:
                if not path.exists():
                    return {"available": False, "path": str(path)}
                data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
                return {"available": True, "path": str(path), **data}

            inventory = read(inventory_path)
            plan = read(plan_path)
            inv_summary = inventory.get("summary") or {}
            plan_summary = plan.get("summary") or {}
            return {
                "available": bool(inventory.get("available") or plan.get("available")),
                "status": plan.get("status") or inventory.get("status"),
                "inventory": {
                    "available": bool(inventory.get("available")),
                    "path": inventory.get("path"),
                    "summary": inv_summary,
                    "counts": inventory.get("counts") or {},
                    "gap_counts": {
                        "security_blockers": len((inventory.get("gaps") or {}).get("security_blockers") or []),
                        "orphaned_frontend": inv_summary.get("orphaned_frontend_count", 0),
                        "uncalled_supabase_functions": len((inventory.get("gaps") or {}).get("uncalled_supabase_functions") or []),
                    },
                },
                "unification_plan": {
                    "available": bool(plan.get("available")),
                    "path": plan.get("path"),
                    "summary": plan_summary,
                    "screen_ids": [screen.get("id") for screen in (plan.get("canonical_screens") or [])],
                    "migration_action_ids": [item.get("id") for item in (plan.get("migration_actions") or [])],
                    "safety_contract": plan.get("safety_contract") or {},
                },
            }
        except Exception as exc:
            errors.append(f"saas product inventory snapshot failed: {exc}")
            return {"available": False, "error": str(exc)}

    def _read_mind_wiring_counts(self, manifest_path: Path) -> Dict[str, Any]:
        if not manifest_path.exists():
            return {"available": False, "path": str(manifest_path)}
        try:
            data = json.loads(manifest_path.read_text(encoding="utf-8", errors="replace"))
            return {
                "available": True,
                "path": str(manifest_path),
                "counts": data.get("counts", {}),
                "service_probes": data.get("service_probes", [])[:10],
            }
        except Exception as exc:
            return {"available": False, "path": str(manifest_path), "error": str(exc)}

    def _run_integration_audit(self, errors: List[str]) -> Dict[str, Any]:
        try:
            from aureon.integrations.audit_trail import IntegrationAuditTrail

            status = IntegrationAuditTrail(
                log_path=self.repo_root / "state" / "self_questioning_integration_audit.jsonl"
            ).run(include=["ollama", "obsidian"])
            return {
                "total": status.total,
                "passed": status.passed,
                "failed": status.failed,
                "health_ratio": status.health_ratio,
                "results": [result.to_dict() for result in status.results],
            }
        except Exception as exc:
            errors.append(f"integration audit failed: {exc}")
            return {"error": str(exc)}

    def _run_self_scan(self, errors: List[str]) -> Dict[str, Any]:
        try:
            from aureon.core.aureon_self_check_scanner import SelfCheckScanner

            scanner = SelfCheckScanner(max_jobs_per_scan=0)
            scanner._wire()
            problems = scanner.detect()[:8]
            return {
                "problems": [
                    {
                        "kind": p.kind,
                        "target": p.target,
                        "severity": p.severity,
                        "detail": p.detail,
                        "evidence": p.evidence,
                    }
                    for p in problems
                ],
                "problem_count_sample": len(problems),
            }
        except Exception as exc:
            errors.append(f"self scan failed: {exc}")
            return {"error": str(exc), "problems": []}

    def _search_obsidian_memory(self, errors: List[str]) -> List[Dict[str, Any]]:
        try:
            if not self.obsidian.health_check():
                return []
            hits: List[Dict[str, Any]] = []
            for query in ("self_questioning_ai", "aureon autonomy", "mind wiring", "accounting full accounts"):
                for hit in self.obsidian.search(query)[:3]:
                    hits.append(hit)
            return hits[:8]
        except Exception as exc:
            errors.append(f"obsidian search failed: {exc}")
            return []

    # ------------------------------------------------------------------
    # Questioning and local LLM
    # ------------------------------------------------------------------
    def _build_questions(
        self,
        context: Dict[str, Any],
        custom: Optional[Sequence[str]],
        *,
        augment: bool = True,
    ) -> List[str]:
        questions = [str(q).strip() for q in (custom or DEFAULT_QUESTIONS) if str(q).strip()]
        if custom and not augment:
            return questions
        counts = ((context.get("mind_wiring") or {}).get("counts") or {})
        if counts.get("broken", 0):
            questions.append("Which broken mind-wiring entries should be repaired first?")
        if not (context.get("ollama") or {}).get("reachable"):
            questions.append("How should I continue when local Ollama is offline?")
        elif not ((context.get("ollama") or {}).get("models") or []):
            questions.append("Which local Ollama model must be installed or configured for deeper autonomy?")
        if not (context.get("obsidian") or {}).get("reachable"):
            questions.append("How should I preserve memory when Obsidian is unavailable?")
        accounting = context.get("accounting") or {}
        if accounting.get("overdue_count", 0):
            questions.append("Which accounting compliance item should be reviewed first without automatic filing?")
        saas_security = context.get("saas_security") or {}
        if saas_security.get("available"):
            questions.append("Which SaaS self-attack finding, benchmark, or release gate should I route through cognition next?")
        saas_product = context.get("saas_product_inventory") or {}
        if saas_product.get("available"):
            questions.append("Which SaaS frontend/API/dashboard surface should be migrated into the unified observation shell next?")
        if real_orders_allowed():
            questions.append("Why must I stop before any exchange mutation?")
        return questions

    def _ask_ollama(
        self,
        questions: Sequence[str],
        context: Dict[str, Any],
        errors: List[str],
    ) -> Dict[str, Any]:
        ollama_snapshot = context.get("ollama") or self._safe_snapshot(self.ollama)
        if not self._ollama_ready(ollama_snapshot):
            return self._fallback_answer(questions, context, "ollama_unavailable")
        chat_model = self._select_chat_model(ollama_snapshot)
        if not chat_model:
            errors.append("ollama has no installed chat model for self-questioning")
            return self._fallback_answer(questions, context, "ollama_model_unavailable")

        system = (
            "You are Aureon's self-questioning autonomy loop. "
            "Reason about the repo as one organism. For every goal, use the "
            "goal_capability_map to consider all relevant skills, tools, logic "
            "modules, code systems, memory, and ThoughtBus routes before choosing "
            "the safest next step. Use only safe actions: "
                "write Obsidian memory, publish ThoughtBus events, queue research, "
                "run audit probes, generate final-ready accounting packs on explicit request, "
                "or ask for human approval. Never suggest placing "
                "live orders, mutating exchange state, exposing secrets, or editing "
                "code directly from this loop. Never suggest automatic Companies House "
                "or HMRC filing/payment. Return short strict JSON only with no markdown fences."
        )
        prompt = {
            "questions": list(questions),
            "context": self._inner_loop_facts(context, ollama_snapshot),
            "response_rules": [
                "Return only one JSON object.",
                "Keep summary under 20 words.",
                "Keep each answer under 45 words.",
                "Use at most 3 short evidence strings per answer.",
                "Name the route surfaces or systems that should be used.",
                "Do not include next_actions; Aureon will derive safe actions locally.",
            ],
            "required_json_shape": {
                "summary": "short summary",
                "answers": [{"question": "...", "answer": "...", "evidence": ["..."]}],
            },
        }

        try:
            question_chars = sum(len(str(item)) for item in questions)
            if len(questions) <= 1 and question_chars < 300:
                response_tokens = max(self.ollama_num_predict, 256)
            else:
                response_tokens = max(
                    self.ollama_num_predict,
                    min(2048, 1024 + (256 * max(1, len(questions))) + (question_chars // 8)),
                )
            data = self.ollama.chat(
                messages=[{"role": "user", "content": json.dumps(prompt, default=_json_default)}],
                model=chat_model,
                system=system,
                format="json",
                options={
                    "temperature": 0.1,
                    "num_ctx": max(4096, response_tokens * 4),
                    "num_predict": response_tokens,
                },
            )
            if data.get("error"):
                errors.append(f"ollama returned error: {data.get('error')}")
                return self._fallback_answer(questions, context, "ollama_error")
            text = ((data.get("message") or {}).get("content") or "").strip()
            parsed = _extract_json_object(text)
            if parsed is None:
                if text:
                    errors.append(f"ollama returned text instead of json: {self._clip(text, 160)}")
                    return self._ollama_text_answer(questions, context, text)
                errors.append("ollama returned empty/non-json response")
                return self._fallback_answer(questions, context, "ollama_non_json")
            parsed["answer_source"] = "ollama"
            return parsed
        except Exception as exc:
            errors.append(f"ollama question failed: {exc}")
            return self._fallback_answer(questions, context, "ollama_error")

    def _ollama_text_answer(
        self,
        questions: Sequence[str],
        context: Dict[str, Any],
        text: str,
    ) -> Dict[str, Any]:
        answer = self._clip(text.strip(), 1200)
        first_line = next((line.strip() for line in answer.splitlines() if line.strip()), "")
        if first_line in {"{", "[", "```json"} or len(first_line) < 4:
            first_line = "Ollama self-questioning completed with schema-like text."
        evidence = self._context_evidence(context)
        evidence.append("ollama returned natural-language self-questioning output")
        return {
            "summary": self._clip(first_line or "Ollama self-questioning completed.", 240),
            "answers": [
                {
                    "question": question,
                    "answer": answer,
                    "evidence": evidence,
                }
                for question in questions
            ],
            "next_actions": [asdict(action) for action in self._fallback_actions(context)],
            "answer_source": "ollama_text",
        }

    def _ollama_ready(self, snapshot: Optional[Dict[str, Any]] = None) -> bool:
        if snapshot is not None:
            return bool(snapshot.get("reachable"))
        try:
            return bool(self.ollama.health_check())
        except Exception:
            return False

    def _fallback_answer(
        self,
        questions: Sequence[str],
        context: Dict[str, Any],
        reason: str,
    ) -> Dict[str, Any]:
        counts = ((context.get("mind_wiring") or {}).get("counts") or {})
        problems = ((context.get("self_scan") or {}).get("problems") or [])
        integration = context.get("integration_audit") or {}
        summary = (
            f"Fallback self-questioning completed ({reason}). "
            f"mind_wiring={counts or 'unknown'}, "
            f"integration={integration.get('passed', 'n/a')}/{integration.get('total', 'n/a')}, "
            f"sampled_problems={len(problems)}."
        )
        answers = []
        for question in questions:
            answers.append(
                {
                    "question": question,
                    "answer": self._deterministic_answer(question, context, reason),
                    "evidence": self._context_evidence(context),
                }
            )
        return {
            "summary": summary,
            "answers": answers,
            "next_actions": [asdict(a) for a in self._fallback_actions(context)],
            "answer_source": "fallback",
        }

    def _deterministic_answer(self, question: str, context: Dict[str, Any], reason: str) -> str:
        q = question.lower()
        counts = ((context.get("mind_wiring") or {}).get("counts") or {})
        if "unhealthy" in q or "unwired" in q or "drifting" in q:
            if counts:
                return (
                    f"The latest manifest reports {counts.get('wired', 0)} wired, "
                    f"{counts.get('partial', 0)} partial, and {counts.get('broken', 0)} broken."
                )
            return "No current mind-wiring manifest was available, so the first safe action is an audit probe."
        if "model" in q:
            models = (context.get("ollama") or {}).get("models") or []
            if models:
                return (
                    "Ollama can see local models, but this cycle used fallback mode. "
                    "Prefer a small self-questioning model for fast inner-loop reasoning."
                )
            return "The configured Ollama endpoint is reachable but reports no chat model, so deeper autonomy needs a refreshed catalog or corrected lane configuration."
        if "ollama" in q:
            return "If Ollama is offline, continue with deterministic checks and write the limitation into Obsidian."
        if "obsidian" in q or "remember" in q:
            return "Persist the cycle summary, evidence, and next action list into the vault or the JSONL state log."
        if "skill" in q or "tool" in q or "logic" in q or "code system" in q or "goal" in q:
            goal_map = context.get("goal_capability_map") or {}
            surfaces = sorted((goal_map.get("route_surfaces") or {}).keys())
            tools = ((goal_map.get("tool_registry") or {}).get("count")) or 0
            return (
                "Use the goal loop to recall memory, inspect state, inventory capabilities, "
                f"and route through relevant surfaces {surfaces}; {tools} registered tool/skill routes are visible."
            )
        if "saas" in q or "unhackable" in q or "self-attack" in q or "release gate" in q:
            product = context.get("saas_product_inventory") or {}
            if "frontend" in q or "dashboard" in q or "operator" in q or "observation shell" in q or "api" in q:
                inventory = product.get("inventory") or {}
                plan = product.get("unification_plan") or {}
                inv_summary = inventory.get("summary") or {}
                plan_summary = plan.get("summary") or {}
                return (
                    "Route product UI work through AureonSaaSSystemInventory and AureonFrontendUnificationPlan. "
                    f"status={product.get('status')}, "
                    f"surfaces={inv_summary.get('surface_count', 0)}, "
                    f"frontend={inv_summary.get('frontend_surface_count', 0)}, "
                    f"supabase_functions={inv_summary.get('supabase_function_count', 0)}, "
                    f"screens={plan_summary.get('screen_count', 0)}, "
                    f"security_blockers={inv_summary.get('security_blocker_count', 0)}. "
                    "Migrate into the canonical observation shell while keeping manual-only and safety gates visible."
                )
            saas = context.get("saas_security") or {}
            if saas.get("available"):
                summary = saas.get("summary") or {}
                bridge = saas.get("cognitive_bridge") or {}
                bridge_summary = bridge.get("summary") or {}
                return (
                    "Route SaaS reasoning through HNCSaaSSecurityArchitect, HNCAuthorizedAttackLab, "
                    "GoalCapabilityMap, ThoughtBus, contract stack, and capability growth. "
                    f"status={saas.get('status')}, "
                    f"benchmarks={summary.get('unhackable_benchmark_count', bridge_summary.get('unhackable_benchmark_count', 0))}, "
                    f"attack_cases={summary.get('attack_case_count', bridge_summary.get('attack_case_count', 0))}, "
                    f"actionable_findings={summary.get('actionable_finding_count', bridge_summary.get('actionable_finding_count', 0))}. "
                    "Think on your feet by publishing SaaS cognition state, fixing findings, and retesting authorized local/staging benchmarks."
                )
            return "SaaS cognition is not available yet, so generate the SaaS cognitive bridge state and publish it to ThoughtBus."
        if "human approval" in q:
            return "Any live trading, exchange mutation, secret handling, or direct code mutation requires human approval."
        if "account" in q or "tax" in q or "hmrc" in q or "filing" in q:
            accounting = context.get("accounting") or {}
            if accounting.get("available"):
                raw_files = accounting.get("raw_data_manifest_summary", {}).get("file_count", 0)
                workflow = accounting.get("autonomous_workflow_status") or "unknown"
                cognitive = (accounting.get("cognitive_review") or {}).get("status", "unknown")
                handoff = (accounting.get("human_filing_handoff_pack") or {})
                handoff_readiness = handoff.get("readiness") or {}
                handoff_ready = handoff_readiness.get("ready_for_manual_upload", handoff_readiness.get("ready_for_manual_review", "unknown"))
                uk_brain = accounting.get("uk_accounting_requirements_brain") or {}
                uk_summary = uk_brain.get("summary") or {}
                uk_figures = uk_brain.get("figures") or {}
                evidence_authoring = accounting.get("accounting_evidence_authoring") or {}
                evidence_summary = evidence_authoring.get("summary") or {}
                llm_authoring = evidence_authoring.get("llm_document_authoring") or evidence_summary.get("llm_document_authoring") or {}
                return (
                    f"Accounting context is available for {accounting.get('company_number')}; "
                    f"final-ready pack status is {accounting.get('accounts_build_status')}, "
                    f"overdue_count={accounting.get('overdue_count')}, raw_files={raw_files}, "
                    f"autonomous_workflow={workflow}, handoff_ready={handoff_ready}, "
                    f"uk_requirements={uk_summary.get('requirement_count', 0)}, "
                    f"uk_questions={uk_summary.get('question_count', 0)}, "
                    f"evidence_requests={evidence_summary.get('draft_count', 0)}, "
                    f"evidence_docs={evidence_summary.get('generated_document_count', 0)}, "
                    f"llm_document_workpapers={llm_authoring.get('completed_count', 0)} "
                    f"via {llm_authoring.get('status', 'unknown')}, "
                    f"vat_over_threshold={uk_figures.get('turnover_over_vat_threshold', 'unknown')}, "
                    f"self_questioning={cognitive}. "
                    "Safe actions are status review, vault ingest, final-ready pack generation on demand, and human filing approval."
                )
            return "Accounting context is unavailable, so the safe action is to run the accounting wiring audit and report missing artifacts."
        return f"Use safe local evidence first; this answer used fallback mode because {reason}."

    def _fallback_actions(self, context: Dict[str, Any]) -> List[SelfQuestionAction]:
        actions: List[SelfQuestionAction] = [
            SelfQuestionAction(
                title="Write this self-questioning cycle into Obsidian",
                action_type="write_obsidian_note",
                priority=1,
                risk="low",
                details="Persist questions, answers, evidence, and next actions.",
            )
        ]
        actions.append(
            SelfQuestionAction(
                title="Broadcast the goal-capability directive to the organism",
                action_type="publish_thought",
                priority=2,
                risk="low",
                details="Tell ThoughtBus which skills, tools, logic modules, and code systems should be considered for the goal.",
            )
        )
        counts = ((context.get("mind_wiring") or {}).get("counts") or {})
        if counts.get("broken", 0) or counts.get("partial", 0):
            actions.append(
                SelfQuestionAction(
                    title="Run mind wiring audit and queue research for broken entries",
                    action_type="queue_research",
                    priority=1,
                    risk="low",
                    details="Use audit evidence to create repair research items, not direct code edits.",
                )
            )
        accounting = context.get("accounting") or {}
        if accounting.get("available"):
            if accounting.get("overdue_count", 0):
                actions.append(
                    SelfQuestionAction(
                        title="Review accounting compliance status and keep filing manual",
                        action_type="ask_human",
                        priority=1,
                        risk="medium",
                        requires_human=True,
                        details=(
                            "Accounting context reports overdue compliance items. "
                            "Use /accounts status or /accounts build for final-ready pack generation; official filing/payment stays manual."
                        ),
                    )
                )
            uk_brain = accounting.get("uk_accounting_requirements_brain") or {}
            uk_summary = uk_brain.get("summary") or {}
            evidence_authoring = accounting.get("accounting_evidence_authoring") or {}
            evidence_summary = evidence_authoring.get("summary") or {}
            llm_authoring = evidence_authoring.get("llm_document_authoring") or evidence_summary.get("llm_document_authoring") or {}
            if evidence_summary.get("draft_count", 0):
                actions.append(
                    SelfQuestionAction(
                        title="Review generated accounting evidence requests and LLM workpapers",
                        action_type="ask_human",
                        priority=1,
                        risk="medium",
                        requires_human=True,
                        details=(
                            "Aureon generated internal receipt, invoice, petty-cash, and allocation requests. "
                            f"LLM generated {llm_authoring.get('completed_count', 0)} internal workpaper sections. "
                            "Attach real evidence or keep unsupported items in suspense/director loan/private drawings."
                        ),
                    )
                )
            if uk_summary.get("unresolved_question_count", 0):
                actions.append(
                    SelfQuestionAction(
                        title="Resolve accounting self-question gaps",
                        action_type="ask_human",
                        priority=1,
                        risk="medium",
                        requires_human=True,
                        details=(
                            "The UK accounting requirements brain has unresolved UTR, VAT, Companies House, PAYE/CIS, "
                            "or source-completeness questions. Inspect/reconcile locally, then ask the human for missing facts."
                        ),
                    )
                )
            else:
                actions.append(
                    SelfQuestionAction(
                        title="Refresh accounting context into the vault",
                        action_type="publish_thought",
                        priority=3,
                        risk="low",
                        details="Publish accounting.status and ingest final-ready accounts context for future cycles.",
                    )
                )
        saas = context.get("saas_security") or {}
        if saas.get("available"):
            bridge = saas.get("cognitive_bridge") or {}
            bridge_summary = bridge.get("summary") or {}
            if bridge_summary.get("actionable_finding_count", 0):
                actions.append(
                    SelfQuestionAction(
                        title="Route SaaS self-attack findings through the cognitive bridge",
                        action_type="queue_research",
                        priority=1,
                        risk="high",
                        details=(
                            "Use HNCAuthorizedAttackLab, HNCSaaSSecurityArchitect, contract stack, "
                            "CodeArchitect, tests, and retest evidence to close the finding."
                        ),
                    )
                )
            elif bridge_summary.get("unhackable_benchmark_count", 0):
                actions.append(
                    SelfQuestionAction(
                        title="Publish SaaS cognition state and continue authorized benchmark loop",
                        action_type="publish_thought",
                        priority=2,
                        risk="medium",
                        details=(
                            "Keep saas.cognition.* topics active so the organism can think on its feet "
                            "about unhackable gates, local/staging self-attacks, repairs, and retests."
                        ),
                    )
                )
        saas_product = context.get("saas_product_inventory") or {}
        if saas_product.get("available"):
            inventory = saas_product.get("inventory") or {}
            plan = saas_product.get("unification_plan") or {}
            gap_counts = inventory.get("gap_counts") or {}
            if gap_counts.get("security_blockers", 0):
                actions.append(
                    SelfQuestionAction(
                        title="Keep SaaS frontend security blockers visible",
                        action_type="publish_thought",
                        priority=2,
                        risk="high",
                        details="Publish the SaaS inventory blocker count into the unified frontend so production readiness cannot hide it.",
                    )
                )
            elif (plan.get("summary") or {}).get("screen_count", 0):
                actions.append(
                    SelfQuestionAction(
                        title="Refresh unified frontend observation manifests",
                        action_type="publish_thought",
                        priority=3,
                        risk="low",
                        details="Keep aureon_saas_system_inventory and aureon_frontend_unification_plan available to the React observation shell.",
                    )
                )
        if not (context.get("ollama") or {}).get("reachable"):
            actions.append(
                SelfQuestionAction(
                    title="Restore local Ollama model availability",
                    action_type="ask_human",
                    priority=2,
                    risk="medium",
                    requires_human=True,
                    details="Start Ollama or install/pull the configured model before expecting LLM-grade autonomy.",
                )
            )
        elif not ((context.get("ollama") or {}).get("models") or []):
            actions.append(
                SelfQuestionAction(
                    title="Install or configure the local Ollama chat model",
                    action_type="ask_human",
                    priority=2,
                    risk="medium",
                    requires_human=True,
                    details=(
                        "Ollama is reachable but reports no local models. "
                        "Refresh the configured Ollama catalog or select a model that the endpoint currently reports."
                    ),
                )
            )
        actions.append(
            SelfQuestionAction(
                title="Continue safe autonomous questioning on the next interval",
                action_type="publish_thought",
                priority=3,
                risk="low",
                details="Emit the result onto ThoughtBus for dashboards and future cycles.",
            )
        )
        return [a.sanitised() for a in actions]

    # ------------------------------------------------------------------
    # Memory and ThoughtBus
    # ------------------------------------------------------------------
    def _write_obsidian_cycle(self, cycle: SelfQuestioningCycle) -> str:
        if not self.obsidian.health_check():
            return ""
        note_path = f"autonomy/cycles/{cycle.cycle_id}.md"
        body = self._render_cycle_markdown(cycle)
        self.obsidian.write_note(note_path, body, overwrite=True)

        index_path = "autonomy/self_questioning_ai.md"
        self.obsidian.patch_section(
            index_path,
            "Cycle Log",
            (
                f"- `{cycle.iso_time}` `{cycle.cycle_id}` "
                f"{cycle.answer_source}: {cycle.summary} "
                f"([[{note_path}]])"
            ),
            operation="append",
        )
        self.obsidian.patch_section(
            index_path,
            "Current Status",
            self._render_status_block(cycle),
            operation="replace",
        )
        return note_path

    def _render_cycle_markdown(self, cycle: SelfQuestioningCycle) -> str:
        lines = [
            "---",
            "aureon_self_questioning: true",
            f"cycle_id: {cycle.cycle_id}",
            f"timestamp: {cycle.iso_time}",
            f"answer_source: {cycle.answer_source}",
            "---",
            "",
            f"# Self Questioning Cycle {cycle.cycle_id}",
            "",
            "## Summary",
            "",
            cycle.summary,
            "",
            "## Questions And Answers",
            "",
        ]
        for answer in cycle.answers:
            lines.append(f"### {answer.get('question', 'Question')}")
            lines.append("")
            lines.append(str(answer.get("answer", "")))
            evidence = answer.get("evidence") or []
            if evidence:
                lines.append("")
                lines.append("Evidence:")
                for item in evidence[:8]:
                    lines.append(f"- {item}")
            lines.append("")

        lines.extend(["## Next Actions", ""])
        for action in cycle.next_actions:
            blocked = " blocked" if action.blocked else ""
            human = " human-approval" if action.requires_human else ""
            lines.append(
                f"- priority {action.priority}: {action.title} "
                f"({action.action_type}, risk={action.risk}{blocked}{human})"
            )
            if action.details:
                lines.append(f"  - {action.details}")
            if action.blocked_reason:
                lines.append(f"  - blocked_reason: {action.blocked_reason}")

        if cycle.errors:
            lines.extend(["", "## Errors", ""])
            for err in cycle.errors:
                lines.append(f"- {err}")
        lines.append("")
        return "\n".join(lines)

    def _render_status_block(self, cycle: SelfQuestioningCycle) -> str:
        context = cycle.context
        counts = ((context.get("mind_wiring") or {}).get("counts") or {})
        goal_map = context.get("goal_capability_map") or {}
        tool_count = ((goal_map.get("tool_registry") or {}).get("count")) or 0
        return "\n".join(
            [
                f"- last_cycle: `{cycle.cycle_id}`",
                f"- timestamp: `{cycle.iso_time}`",
                f"- answer_source: `{cycle.answer_source}`",
                f"- mind_wiring: `{counts}`",
                f"- goal_directive: `{goal_map.get('directive_version', 'unknown')}`",
                f"- visible_tool_skill_routes: `{tool_count}`",
                f"- contract_stack: `{context.get('contract_stack')}`",
                f"- ollama_reachable: `{(context.get('ollama') or {}).get('reachable')}`",
                f"- obsidian_reachable: `{(context.get('obsidian') or {}).get('reachable')}`",
                f"- accounting: `{self._compact_accounting(context.get('accounting') or {})}`",
                f"- saas_security: `{self._compact_saas_security(context.get('saas_security') or {})}`",
                f"- saas_product_inventory: `{self._compact_saas_product_inventory(context.get('saas_product_inventory') or {})}`",
                f"- real_orders_allowed: `{context.get('real_orders_allowed')}`",
            ]
        )

    def _publish_safe_research_actions(self, cycle: SelfQuestioningCycle) -> None:
        for action in cycle.next_actions:
            if action.action_type != "queue_research" or action.blocked:
                continue
            self._publish(
                "authoring.research",
                {
                    "origin": "self_questioning_ai",
                    "cycle_id": cycle.cycle_id,
                    "title": action.title,
                    "details": action.details,
                    "requires_human": action.requires_human,
                },
            )

    def _publish_goal_directive(self, cycle_id: str, context: Dict[str, Any]) -> None:
        goal_map = context.get("goal_capability_map") or {}
        self._publish(
            "autonomy.goal.directive",
            {
                "cycle_id": cycle_id,
                "directive_version": goal_map.get("directive_version"),
                "directive": goal_map.get("directive"),
                "goal_loop": goal_map.get("goal_loop"),
                "recommended_routes": goal_map.get("recommended_routes", [])[:5],
                "route_surfaces": sorted((goal_map.get("route_surfaces") or {}).keys()),
                "contract_stack": context.get("contract_stack") or {},
                "real_orders_allowed": goal_map.get("real_orders_allowed"),
            },
        )
        self._publish(
            "organism.contract.directive",
            {
                "cycle_id": cycle_id,
                "directive": "Use GoalContract, TaskContract, JobContract, and WorkOrderContract for internal coordination.",
                "contract_stack": context.get("contract_stack") or {},
                "goal_loop": goal_map.get("goal_loop"),
            },
        )

    def _publish(self, topic: str, payload: Dict[str, Any]) -> None:
        try:
            self.thought_bus.publish(
                Thought(
                    source="self_questioning_ai",
                    topic=topic,
                    payload=payload,
                )
            )
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Compaction helpers
    # ------------------------------------------------------------------
    def _safe_snapshot(self, bridge: Any) -> Dict[str, Any]:
        try:
            return dict(bridge.snapshot())
        except Exception as exc:
            return {"reachable": False, "error": str(exc)}

    def _accounting_context_snapshot(self, errors: List[str]) -> Dict[str, Any]:
        try:
            from aureon.queen.accounting_context_bridge import get_accounting_context_bridge

            bridge = get_accounting_context_bridge()
            status = bridge.status()
            context = bridge.load_context()
            raw_summary = ((status.get("raw_data_manifest") or {}).get("summary") or {})
            workflow = status.get("autonomous_workflow") or {}
            statutory = status.get("statutory_filing_pack") or {}
            government_matrix = (statutory.get("government_requirements_matrix") or {}).get("summary") or {}
            readiness = status.get("accounting_readiness") or {}
            end_user_automation = status.get("end_user_accounting_automation") or {}
            handoff_pack = status.get("human_filing_handoff_pack") or workflow.get("human_filing_handoff_pack") or {}
            uk_accounting_brain = (
                status.get("uk_accounting_requirements_brain")
                or handoff_pack.get("uk_accounting_requirements_brain")
                or workflow.get("uk_accounting_requirements_brain")
                or {}
            )
            accounting_evidence_authoring = (
                status.get("accounting_evidence_authoring")
                or handoff_pack.get("accounting_evidence_authoring")
                or workflow.get("accounting_evidence_authoring")
                or {}
            )
            return {
                "available": bool(status.get("available", True)),
                "company_number": status.get("company_number"),
                "company_name": status.get("company_name"),
                "company_status": status.get("company_status"),
                "period_start": status.get("period_start"),
                "period_end": status.get("period_end"),
                "generated_at": status.get("generated_at"),
                "accounts_build_status": status.get("accounts_build_status"),
                "overdue_count": status.get("overdue_count", 0),
                "bank_evidence_complete": status.get("bank_evidence_complete"),
                "manual_filing_required": status.get("manual_filing_required", True),
                "missing_outputs": status.get("missing_outputs") or [],
                "combined_bank_data": status.get("combined_bank_data") or {},
                "accounting_system_registry": status.get("accounting_system_registry") or {},
                "accounting_readiness": readiness,
                "raw_data_manifest_summary": raw_summary,
                "statutory_output_count": len(statutory.get("outputs") or {}),
                "government_requirements_summary": government_matrix,
                "autonomous_workflow_status": workflow.get("status"),
                "autonomous_agent_task_count": len(workflow.get("agent_tasks") or []),
                "end_user_accounting_automation": end_user_automation,
                "vault_memory": status.get("vault_memory") or workflow.get("vault_memory") or {},
                "cognitive_review": status.get("cognitive_review") or workflow.get("cognitive_review") or {},
                "human_filing_handoff_pack": handoff_pack,
                "accounting_evidence_authoring": accounting_evidence_authoring,
                "uk_accounting_requirements_brain": uk_accounting_brain,
                "prompt_lines": (context.get("prompt_lines") or [])[:6],
                "topics": status.get("topics") or [],
            }
        except Exception as exc:
            errors.append(f"accounting context failed: {exc}")
            return {"available": False, "error": str(exc)}

    def _contract_stack_snapshot(self, errors: List[str]) -> Dict[str, Any]:
        try:
            from aureon.core.organism_contracts import build_contract_stack_snapshot

            return build_contract_stack_snapshot(self.repo_root)
        except Exception as exc:
            errors.append(f"contract stack snapshot failed: {exc}")
            return {"available": False, "error": str(exc)}

    def _compact_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        ollama_snapshot = context.get("ollama") or {}
        return {
            "runtime_flags": context.get("runtime_flags"),
            "real_orders_allowed": context.get("real_orders_allowed"),
            "ollama": self._compact_ollama(ollama_snapshot),
            "selected_ollama_model": self._select_chat_model(ollama_snapshot),
            "obsidian": self._compact_obsidian(context.get("obsidian") or {}),
            "accounting": self._compact_accounting(context.get("accounting") or {}),
            "saas_security": self._compact_saas_security(context.get("saas_security") or {}),
            "saas_product_inventory": self._compact_saas_product_inventory(context.get("saas_product_inventory") or {}),
            "repo_self_catalog": self._compact_repo_self_catalog(context.get("repo_self_catalog") or {}),
            "capability_growth_loop": self._compact_capability_growth_loop(context.get("capability_growth_loop") or {}),
            "goal_capability_map": self._compact_goal_map(context.get("goal_capability_map") or {}),
            "contract_stack": context.get("contract_stack") or {},
            "mind_wiring": context.get("mind_wiring"),
            "integration_audit": self._compact_integration(context.get("integration_audit") or {}),
            "self_scan": self._compact_self_scan(context.get("self_scan") or {}),
            "recent_thoughts": self._compact_thoughts(context.get("recent_thoughts") or []),
            "memory_hits": self._compact_memory_hits(context.get("obsidian_memory_hits") or []),
        }

    def _inner_loop_facts(
        self,
        context: Dict[str, Any],
        ollama_snapshot: Dict[str, Any],
    ) -> Dict[str, Any]:
        counts = ((context.get("mind_wiring") or {}).get("counts") or {})
        audit = context.get("integration_audit") or {}
        scan = self._compact_self_scan(context.get("self_scan") or {})
        memory_hits = context.get("obsidian_memory_hits") or []
        return {
            "safe_mode": context.get("safe_mode"),
            "real_orders_allowed": context.get("real_orders_allowed"),
            "runtime_flags": context.get("runtime_flags"),
            "selected_ollama_model": self._select_chat_model(ollama_snapshot),
            "ollama_models": (ollama_snapshot.get("models") or [])[:5],
            "obsidian": self._compact_obsidian(context.get("obsidian") or {}),
            "accounting": self._compact_accounting(context.get("accounting") or {}),
            "saas_security": self._compact_saas_security(context.get("saas_security") or {}),
            "saas_product_inventory": self._compact_saas_product_inventory(context.get("saas_product_inventory") or {}),
            "repo_self_catalog": self._compact_repo_self_catalog(context.get("repo_self_catalog") or {}),
            "capability_growth_loop": self._compact_capability_growth_loop(context.get("capability_growth_loop") or {}),
            "goal_capability_map": self._compact_goal_map(context.get("goal_capability_map") or {}),
            "contract_stack": context.get("contract_stack") or {},
            "mind_wiring_counts": counts,
            "integration_audit": {
                "total": audit.get("total"),
                "passed": audit.get("passed"),
                "failed": audit.get("failed"),
            },
            "sampled_self_scan_problems": (scan.get("problems") or [])[:3],
            "memory_hit_paths": [
                self._clip(hit.get("filename") or hit.get("path") or hit.get("note"), 160)
                for hit in memory_hits[:3]
                if isinstance(hit, dict)
            ],
        }

    def _compact_repo_self_catalog(self, snapshot: Dict[str, Any]) -> Dict[str, Any]:
        if not snapshot:
            return {}
        summary = snapshot.get("summary") or {}
        return {
            "available": snapshot.get("available"),
            "status": snapshot.get("status"),
            "path": snapshot.get("path"),
            "summary": {
                "cataloged_file_count": summary.get("cataloged_file_count"),
                "domain_count": summary.get("domain_count"),
                "subsystem_count": summary.get("subsystem_count"),
                "file_kind_count": summary.get("file_kind_count"),
                "secret_metadata_only_count": summary.get("secret_metadata_only_count"),
                "coverage_policy": summary.get("coverage_policy"),
            },
            "domain_counts": snapshot.get("domain_counts") or {},
            "subsystem_counts": snapshot.get("subsystem_counts") or {},
            "vault_memory": snapshot.get("vault_memory") or {},
            "sample_labels": (snapshot.get("sample_labels") or [])[:8],
        }

    def _compact_capability_growth_loop(self, snapshot: Dict[str, Any]) -> Dict[str, Any]:
        if not snapshot:
            return {}
        summary = snapshot.get("summary") or {}
        latest = snapshot.get("latest_iteration_summary") or {}
        return {
            "available": snapshot.get("available"),
            "status": snapshot.get("status"),
            "path": snapshot.get("path"),
            "summary": {
                "iteration_count": summary.get("iteration_count"),
                "latest_gap_count": summary.get("latest_gap_count"),
                "latest_mean_score": summary.get("latest_mean_score"),
                "latest_registered_improvement_count": summary.get("latest_registered_improvement_count"),
                "contract_queue_persisted": summary.get("contract_queue_persisted"),
            },
            "latest_iteration_summary": {
                "domain_count": latest.get("domain_count"),
                "gap_count": latest.get("gap_count"),
                "mean_score": latest.get("mean_score"),
                "registered_improvement_count": latest.get("registered_improvement_count"),
            },
            "latest_gap_ids": (snapshot.get("latest_gap_ids") or [])[:12],
            "vault_memory": snapshot.get("vault_memory") or {},
        }

    def _compact_goal_map(self, goal_map: Dict[str, Any]) -> Dict[str, Any]:
        if not goal_map:
            return {}
        tool_registry = goal_map.get("tool_registry") or {}
        organism = goal_map.get("organism") or {}
        return {
            "directive_version": goal_map.get("directive_version"),
            "directive": goal_map.get("directive"),
            "goal_loop": goal_map.get("goal_loop"),
            "route_surfaces": {
                key: value[:5] if isinstance(value, list) else value
                for key, value in (goal_map.get("route_surfaces") or {}).items()
            },
            "tool_registry": {
                "count": tool_registry.get("count"),
                "builtin_tools": (tool_registry.get("builtin_tools") or [])[:8],
                "vm_tools": (tool_registry.get("vm_tools") or [])[:8],
                "external_skill_routes": tool_registry.get("external_skill_routes") or [],
            },
            "organism": {
                "node_count": organism.get("node_count"),
                "domains": organism.get("domains"),
            },
            "contract_capabilities": goal_map.get("contract_capabilities") or {},
            "accounting_capabilities": goal_map.get("accounting_capabilities") or {},
            "recommended_routes": (goal_map.get("recommended_routes") or [])[:5],
            "safety_rules": (goal_map.get("safety_rules") or [])[:5],
        }

    def _compact_saas_security(self, snapshot: Dict[str, Any]) -> Dict[str, Any]:
        if not snapshot:
            return {}
        summary = snapshot.get("summary") or {}
        bridge = snapshot.get("cognitive_bridge") or {}
        attack_lab = snapshot.get("attack_lab") or {}
        blueprint = snapshot.get("blueprint") or {}
        return {
            "available": snapshot.get("available"),
            "status": snapshot.get("status"),
            "summary": summary,
            "cognitive_bridge": {
                "available": bridge.get("available"),
                "status": bridge.get("status"),
                "summary": bridge.get("summary") or {},
                "question_count": bridge.get("question_count", 0),
                "decision_count": bridge.get("decision_count", 0),
                "thought_topics": bridge.get("thought_topics") or {},
            },
            "attack_lab": {
                "available": attack_lab.get("available"),
                "status": attack_lab.get("status"),
                "summary": attack_lab.get("summary") or {},
                "findings": [
                    {
                        "id": item.get("id"),
                        "severity": item.get("severity"),
                        "status": item.get("status"),
                        "queued": item.get("queued"),
                    }
                    for item in (attack_lab.get("findings") or [])[:5]
                ],
            },
            "blueprint": {
                "available": blueprint.get("available"),
                "status": blueprint.get("status"),
                "summary": blueprint.get("summary") or {},
                "release_gate_count": len(blueprint.get("release_gates") or []),
            },
        }

    def _compact_saas_product_inventory(self, snapshot: Dict[str, Any]) -> Dict[str, Any]:
        if not snapshot:
            return {}
        inventory = snapshot.get("inventory") or {}
        plan = snapshot.get("unification_plan") or {}
        return {
            "available": snapshot.get("available"),
            "status": snapshot.get("status"),
            "inventory": {
                "available": inventory.get("available"),
                "summary": inventory.get("summary") or {},
                "gap_counts": inventory.get("gap_counts") or {},
            },
            "unification_plan": {
                "available": plan.get("available"),
                "summary": plan.get("summary") or {},
                "screen_ids": (plan.get("screen_ids") or [])[:10],
                "migration_action_ids": (plan.get("migration_action_ids") or [])[:10],
                "safety_contract": plan.get("safety_contract") or {},
            },
        }

    def _compact_ollama(self, snapshot: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "reachable": snapshot.get("reachable"),
            "chat_model": snapshot.get("chat_model"),
            "version": snapshot.get("version"),
            "models": (snapshot.get("models") or [])[:10],
            "running": (snapshot.get("running") or [])[:10],
        }

    def _compact_obsidian(self, snapshot: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "reachable": snapshot.get("reachable"),
            "mode": snapshot.get("mode"),
            "vault_path": snapshot.get("vault_path"),
            "note_count": snapshot.get("note_count"),
        }

    def _compact_accounting(self, snapshot: Dict[str, Any]) -> Dict[str, Any]:
        combined = snapshot.get("combined_bank_data") or {}
        registry = snapshot.get("accounting_system_registry") or {}
        raw_summary = snapshot.get("raw_data_manifest_summary") or {}
        readiness = snapshot.get("accounting_readiness") or {}
        government = snapshot.get("government_requirements_summary") or {}
        cognitive_review = snapshot.get("cognitive_review") or {}
        vault_memory = snapshot.get("vault_memory") or {}
        end_user = snapshot.get("end_user_accounting_automation") or {}
        end_user_coverage = end_user.get("requirement_coverage") or []
        end_user_generated = sum(1 for item in end_user_coverage if str(item.get("status", "")).startswith("generated"))
        handoff_pack = snapshot.get("human_filing_handoff_pack") or {}
        handoff_readiness = handoff_pack.get("readiness") or {}
        evidence_authoring = snapshot.get("accounting_evidence_authoring") or handoff_pack.get("accounting_evidence_authoring") or {}
        evidence_summary = evidence_authoring.get("summary") or {}
        llm_authoring = evidence_authoring.get("llm_document_authoring") or evidence_summary.get("llm_document_authoring") or {}
        uk_brain = snapshot.get("uk_accounting_requirements_brain") or handoff_pack.get("uk_accounting_requirements_brain") or {}
        uk_summary = uk_brain.get("summary") or {}
        uk_figures = uk_brain.get("figures") or {}
        return {
            "available": snapshot.get("available"),
            "company_number": snapshot.get("company_number"),
            "company_status": self._clip(snapshot.get("company_status"), 120),
            "period": (
                f"{snapshot.get('period_start')} to {snapshot.get('period_end')}"
                if snapshot.get("period_start") or snapshot.get("period_end")
                else ""
            ),
            "accounts_build_status": snapshot.get("accounts_build_status"),
            "overdue_count": snapshot.get("overdue_count", 0),
            "bank_evidence_complete": snapshot.get("bank_evidence_complete"),
            "manual_filing_required": snapshot.get("manual_filing_required", True),
            "missing_outputs": (snapshot.get("missing_outputs") or [])[:5],
            "combined_bank_sources": combined.get("transaction_source_count", combined.get("csv_source_count", 0)),
            "combined_csv_sources": combined.get("csv_source_count", 0),
            "combined_pdf_sources": combined.get("pdf_source_count", 0),
            "combined_unique_period_rows": combined.get("unique_rows_in_period", 0),
            "combined_duplicate_rows_removed": combined.get("duplicate_rows_removed", 0),
            "source_provider_summary": combined.get("source_provider_summary") or {},
            "flow_provider_summary": combined.get("flow_provider_summary") or {},
            "raw_file_count": raw_summary.get("file_count", 0),
            "raw_transaction_source_count": raw_summary.get("transaction_source_count", 0),
            "raw_evidence_only_count": raw_summary.get("evidence_only_count", 0),
            "statutory_output_count": snapshot.get("statutory_output_count", 0),
            "government_requirement_count": government.get("requirement_count", 0),
            "government_generated_or_readiness_count": government.get("generated_or_readiness_count", 0),
            "accounting_ready": readiness.get("ready"),
            "autonomous_workflow_status": snapshot.get("autonomous_workflow_status"),
            "autonomous_agent_task_count": snapshot.get("autonomous_agent_task_count", 0),
            "end_user_automation_status": end_user.get("status"),
            "end_user_coverage_generated": end_user_generated,
            "end_user_coverage_total": len(end_user_coverage),
            "vault_memory_status": vault_memory.get("status"),
            "vault_memory_note": vault_memory.get("note_path"),
            "cognitive_review_status": cognitive_review.get("status"),
            "cognitive_review_source": cognitive_review.get("answer_source"),
            "cognitive_review_note": cognitive_review.get("note_path"),
            "human_filing_handoff_status": handoff_pack.get("status"),
            "human_filing_handoff_ready": handoff_readiness.get("ready_for_manual_upload", handoff_readiness.get("ready_for_manual_review")),
            "human_filing_handoff_folder": handoff_pack.get("output_dir"),
            "evidence_authoring_status": evidence_authoring.get("status"),
            "evidence_request_count": evidence_summary.get("draft_count", 0),
            "evidence_document_count": evidence_summary.get("generated_document_count", 0),
            "llm_document_authoring_status": llm_authoring.get("status"),
            "llm_document_workpaper_count": llm_authoring.get("completed_count", 0),
            "llm_document_draft_count": llm_authoring.get("completed_count", 0),
            "llm_document_model": llm_authoring.get("model"),
            "petty_cash_request_count": evidence_summary.get("petty_cash_withdrawal_count", 0),
            "related_party_query_count": evidence_summary.get("related_party_query_count", 0),
            "uk_requirement_count": uk_summary.get("requirement_count", 0),
            "uk_accountant_question_count": uk_summary.get("question_count", 0),
            "uk_unresolved_question_count": uk_summary.get("unresolved_question_count", 0),
            "vat_turnover_over_threshold": uk_figures.get("turnover_over_vat_threshold"),
            "vat_registration_threshold": uk_figures.get("vat_registration_threshold"),
            "accounting_tool_count": registry.get("module_count", 0),
            "accounting_artifact_count": registry.get("artifact_count", 0),
            "accounting_tool_domains": registry.get("domain_counts") or {},
        }

    def _compact_self_scan(self, scan: Dict[str, Any]) -> Dict[str, Any]:
        problems = []
        for problem in (scan.get("problems") or [])[:5]:
            if not isinstance(problem, dict):
                continue
            problems.append(
                {
                    "kind": problem.get("kind"),
                    "target": self._clip(problem.get("target"), 160),
                    "severity": problem.get("severity"),
                    "detail": self._clip(problem.get("detail"), 240),
                }
            )
        return {
            "error": scan.get("error"),
            "problem_count_sample": scan.get("problem_count_sample", len(problems)),
            "problems": problems,
        }

    def _compact_thoughts(self, thoughts: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
        compacted: List[Dict[str, Any]] = []
        for thought in list(thoughts)[-5:]:
            if not isinstance(thought, dict):
                continue
            payload = thought.get("payload") or {}
            compacted.append(
                {
                    "source": thought.get("source"),
                    "topic": thought.get("topic"),
                    "payload": self._clip(json.dumps(payload, default=_json_default), 240),
                }
            )
        return compacted

    def _compact_memory_hits(self, hits: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
        compacted: List[Dict[str, Any]] = []
        for hit in list(hits)[:5]:
            if not isinstance(hit, dict):
                continue
            compacted.append(
                {
                    "path": self._clip(hit.get("path") or hit.get("file") or hit.get("note"), 180),
                    "title": self._clip(hit.get("title"), 120),
                    "snippet": self._clip(hit.get("snippet") or hit.get("content"), 240),
                }
            )
        return compacted

    def _select_chat_model(self, snapshot: Dict[str, Any]) -> str:
        models = [str(name) for name in (snapshot.get("models") or []) if str(name).strip()]
        specific = os.environ.get("AUREON_SELF_QUESTIONING_OLLAMA_MODEL", "").strip()
        if specific:
            return self._installed_model_name(specific, models)

        for candidate in FAST_SELF_QUESTIONING_MODELS:
            installed = self._installed_model_name(candidate, models)
            if installed:
                return installed

        bridge_model = str(getattr(self.ollama, "chat_model", "") or "").strip()
        installed = self._installed_model_name(bridge_model, models)
        if installed:
            return installed
        return models[0] if models else ""

    @staticmethod
    def _installed_model_name(preferred: str, models: Sequence[str]) -> str:
        preferred = str(preferred or "").strip()
        if not preferred:
            return ""
        model_set = {str(model).strip() for model in models if str(model).strip()}
        if not model_set:
            return ""
        if preferred in model_set:
            return preferred
        latest = f"{preferred}:latest"
        if latest in model_set:
            return latest
        if preferred.endswith(":latest"):
            base = preferred[: -len(":latest")]
            if base in model_set:
                return base
        return ""

    @staticmethod
    def _clip(value: Any, limit: int) -> str:
        text = "" if value is None else str(value)
        if len(text) <= limit:
            return text
        return text[: max(0, limit - 3)] + "..."

    def _compact_integration(self, audit: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "total": audit.get("total"),
            "passed": audit.get("passed"),
            "failed": audit.get("failed"),
            "health_ratio": audit.get("health_ratio"),
            "failed_results": [
                r for r in audit.get("results", []) if not r.get("passed")
            ][:5],
        }

    def _compact_previous_cycles(self, cycles: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        for cycle in cycles:
            actions = cycle.get("next_actions") or []
            out.append(
                {
                    "cycle_id": cycle.get("cycle_id"),
                    "iso_time": cycle.get("iso_time"),
                    "answer_source": cycle.get("answer_source"),
                    "summary": cycle.get("summary"),
                    "note_path": cycle.get("note_path"),
                    "actions": [
                        {
                            "title": a.get("title"),
                            "action_type": a.get("action_type"),
                            "priority": a.get("priority"),
                            "requires_human": a.get("requires_human"),
                            "blocked": a.get("blocked"),
                        }
                        for a in actions[:5]
                        if isinstance(a, dict)
                    ],
                }
            )
        return out

    def _compact_cycle_for_status(self, cycle: SelfQuestioningCycle) -> Dict[str, Any]:
        return {
            "cycle_id": cycle.cycle_id,
            "iso_time": cycle.iso_time,
            "summary": cycle.summary,
            "answer_source": cycle.answer_source,
            "note_path": cycle.note_path,
            "errors": list(cycle.errors),
            "next_actions": [asdict(action) for action in cycle.next_actions],
            "mind_wiring": (cycle.context.get("mind_wiring") or {}).get("counts"),
            "ollama": cycle.context.get("ollama"),
            "obsidian": cycle.context.get("obsidian"),
            "accounting": self._compact_accounting(cycle.context.get("accounting") or {}),
            "saas_security": self._compact_saas_security(cycle.context.get("saas_security") or {}),
            "saas_product_inventory": self._compact_saas_product_inventory(cycle.context.get("saas_product_inventory") or {}),
            "repo_self_catalog": self._compact_repo_self_catalog(cycle.context.get("repo_self_catalog") or {}),
            "capability_growth_loop": self._compact_capability_growth_loop(cycle.context.get("capability_growth_loop") or {}),
        }

    def _context_evidence(self, context: Dict[str, Any]) -> List[str]:
        evidence: List[str] = []
        counts = ((context.get("mind_wiring") or {}).get("counts") or {})
        if counts:
            evidence.append(f"mind_wiring counts: {counts}")
        ollama = context.get("ollama") or {}
        evidence.append(f"ollama reachable: {ollama.get('reachable')}")
        obsidian = context.get("obsidian") or {}
        evidence.append(f"obsidian mode: {obsidian.get('mode')} reachable={obsidian.get('reachable')}")
        integration = context.get("integration_audit") or {}
        if integration:
            evidence.append(
                f"integration audit: {integration.get('passed')}/{integration.get('total')}"
            )
        goal_map = context.get("goal_capability_map") or {}
        if goal_map:
            tools = ((goal_map.get("tool_registry") or {}).get("count")) or 0
            organism_nodes = ((goal_map.get("organism") or {}).get("node_count")) or 0
            evidence.append(
                f"goal capability map: {tools} tool/skill routes, {organism_nodes} organism nodes"
            )
        catalog = context.get("repo_self_catalog") or {}
        if catalog:
            summary = catalog.get("summary") or {}
            evidence.append(
                "repo self-catalog: "
                f"available={catalog.get('available')} files={summary.get('cataloged_file_count')}"
            )
        growth = context.get("capability_growth_loop") or {}
        if growth:
            summary = growth.get("summary") or {}
            evidence.append(
                "capability growth: "
                f"available={growth.get('available')} gaps={summary.get('latest_gap_count')}"
            )
        accounting = context.get("accounting") or {}
        if accounting:
            evidence.append(
                "accounting: "
                f"available={accounting.get('available')} "
                f"overdue={accounting.get('overdue_count', 0)} "
                f"manual_filing={accounting.get('manual_filing_required', True)}"
            )
        saas = context.get("saas_security") or {}
        if saas:
            summary = saas.get("summary") or {}
            evidence.append(
                "saas_security: "
                f"available={saas.get('available')} "
                f"benchmarks={summary.get('unhackable_benchmark_count', 0)} "
                f"attack_cases={summary.get('attack_case_count', 0)} "
                f"findings={summary.get('actionable_finding_count', 0)}"
            )
        saas_product = context.get("saas_product_inventory") or {}
        if saas_product:
            inventory = saas_product.get("inventory") or {}
            inv_summary = inventory.get("summary") or {}
            evidence.append(
                "saas_product_inventory: "
                f"available={saas_product.get('available')} "
                f"surfaces={inv_summary.get('surface_count', 0)} "
                f"frontend={inv_summary.get('frontend_surface_count', 0)} "
                f"security_blockers={inv_summary.get('security_blocker_count', 0)}"
            )
        return evidence


def run_once(args: argparse.Namespace) -> int:
    ai = SelfQuestioningAI()
    questions = args.question if args.question else None
    cycle = ai.run_cycle(
        questions=questions,
        include_audit=not args.no_audit,
        include_self_scan=not args.no_self_scan,
    )
    print(json.dumps(cycle.to_dict(), indent=2, default=_json_default))
    return 0


def run_loop(args: argparse.Namespace) -> int:
    ai = SelfQuestioningAI()
    interval = max(30.0, float(args.interval))
    while True:
        cycle = ai.run_cycle(
            questions=args.question if args.question else None,
            include_audit=not args.no_audit,
            include_self_scan=not args.no_self_scan,
        )
        print(
            json.dumps(
                {
                    "cycle_id": cycle.cycle_id,
                    "answer_source": cycle.answer_source,
                    "summary": cycle.summary,
                    "note_path": cycle.note_path,
                },
                default=_json_default,
            )
        )
        time.sleep(interval)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run Aureon's safe self-questioning AI loop.")
    parser.add_argument("--once", action="store_true", help="Run one cycle and exit.")
    parser.add_argument("--loop", action="store_true", help="Run forever.")
    parser.add_argument("--interval", type=float, default=300.0, help="Loop interval in seconds.")
    parser.add_argument("--question", action="append", help="Custom question to ask this cycle.")
    parser.add_argument("--no-audit", action="store_true", help="Skip Ollama/Obsidian integration audit.")
    parser.add_argument("--no-self-scan", action="store_true", help="Skip self-check scanner.")
    parser.add_argument("--status", action="store_true", help="Print status and exit.")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    from aureon.core.aureon_env import bootstrap_credentials

    bootstrap_credentials(REPO_ROOT)
    if args.status:
        print(json.dumps(SelfQuestioningAI().get_status(), indent=2, default=_json_default))
        return 0
    if args.loop:
        return run_loop(args)
    return run_once(args)


if __name__ == "__main__":
    raise SystemExit(main())

"""Unified internal contract stack for the Aureon organism.

This module gives Aureon one local language for asking work of itself:
goals, skills, tasks, jobs, and work orders all travel in the same
contract envelope and publish onto ThoughtBus topics. The stack is local,
auditable, and deliberately conservative. It can queue internal work, but it
does not grant filing, payment, exchange, or live-order authority.
"""

from __future__ import annotations

import json
import os
import re
import time
import uuid
from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from aureon.core.aureon_runtime_safety import real_orders_allowed


CONTRACT_SCHEMA_VERSION = "aureon-organism-contract-v1"

CONTRACT_TYPES = (
    "goal",
    "skill",
    "task",
    "job",
    "work_order",
    "directive",
    "result",
)

CONTRACT_STATUSES = (
    "created",
    "queued",
    "active",
    "completed",
    "failed",
    "blocked",
    "cancelled",
)

CONTRACT_TOPICS = {
    "goal": "organism.contract.goal.created",
    "skill": "organism.contract.skill.registered",
    "task": "organism.contract.task.created",
    "job": "organism.contract.job.created",
    "work_order": "organism.contract.work_order.queued",
    "directive": "organism.contract.directive",
    "result": "organism.contract.result",
    "blocked": "organism.contract.blocked",
    "status": "organism.contract.status",
    "claimed": "organism.contract.work_order.claimed",
    "completed": "organism.contract.work_order.completed",
    "failed": "organism.contract.work_order.failed",
    "superseded": "organism.contract.work_order.superseded",
}

DEFAULT_STATE_PATH = Path("state/organism_contract_stack.json")

UNSAFE_ACTION_TYPES = {
    "place_live_order",
    "execute_trade",
    "submit_hmrc",
    "submit_companies_house",
    "pay_tax",
    "pay_penalty",
    "make_payment",
    "withdraw_funds",
    "mutate_exchange_state",
}

UNSAFE_TEXT_PATTERNS = (
    r"\b(place|execute|submit|file|pay|withdraw)\b.*\b(live|real|order|trade|hmrc|companies house|tax|penalt|payment)\b",
    r"\b(api key|secret|password|credential)\b.*\b(overwrite|expose|print|publish)\b",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_") or "item"


def _safe_dict(value: Any) -> Dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


@dataclass
class ContractEnvelope:
    contract_id: str
    contract_type: str
    title: str
    source: str
    payload: Dict[str, Any] = field(default_factory=dict)
    status: str = "created"
    priority: int = 5
    risk: str = "low"
    requires_human: bool = False
    blocked: bool = False
    blocked_reason: str = ""
    queue: str = "default"
    parent_id: str = ""
    trace_id: str = field(default_factory=lambda: new_id("trace"))
    tags: List[str] = field(default_factory=list)
    safety: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=utc_now)
    updated_at: str = field(default_factory=utc_now)
    schema_version: str = CONTRACT_SCHEMA_VERSION

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ContractEnvelope":
        clean = dict(data)
        clean.setdefault("schema_version", CONTRACT_SCHEMA_VERSION)
        clean.setdefault("payload", {})
        clean.setdefault("safety", {})
        clean.setdefault("tags", [])
        return cls(**{key: clean[key] for key in cls.__dataclass_fields__ if key in clean})

    def topic(self) -> str:
        if self.blocked or self.status == "blocked":
            return CONTRACT_TOPICS["blocked"]
        return CONTRACT_TOPICS.get(self.contract_type, "organism.contract.event")

    def mark(self, status: str, **payload_updates: Any) -> "ContractEnvelope":
        if status not in CONTRACT_STATUSES:
            raise ValueError(f"unsupported contract status: {status}")
        self.status = status
        self.updated_at = utc_now()
        if payload_updates:
            self.payload.update(payload_updates)
        return self


def apply_contract_safety(contract: ContractEnvelope) -> ContractEnvelope:
    payload = contract.payload
    action_type = str(payload.get("action_type") or contract.contract_type).lower()
    text = " ".join(
        str(item or "")
        for item in (
            contract.title,
            payload.get("objective"),
            payload.get("instructions"),
            payload.get("details"),
            payload.get("description"),
        )
    ).lower()

    unsafe_action = action_type in UNSAFE_ACTION_TYPES
    unsafe_text = any(re.search(pattern, text) for pattern in UNSAFE_TEXT_PATTERNS)
    official_boundary = action_type in {
        "submit_hmrc",
        "submit_companies_house",
        "pay_tax",
        "pay_penalty",
        "make_payment",
    }
    live_order_boundary = action_type in {
        "place_live_order",
        "execute_trade",
        "mutate_exchange_state",
        "withdraw_funds",
    } or ("live order" in text or "real order" in text)

    safety = {
        "schema_version": "aureon-contract-safety-v1",
        "audit_mode": os.environ.get("AUREON_AUDIT_MODE", "0"),
        "real_orders_allowed": real_orders_allowed(),
        "official_filing_manual_only": True,
        "hmrc_submission_manual_only": True,
        "companies_house_submission_manual_only": True,
        "tax_or_penalty_payment_manual_only": True,
        "exchange_or_trading_mutation_requires_live_gate": True,
    }

    if official_boundary:
        contract.requires_human = True
        contract.blocked = True
        contract.blocked_reason = "official filing/submission/payment is manual only"
    elif live_order_boundary and not real_orders_allowed():
        contract.requires_human = True
        contract.blocked = True
        contract.blocked_reason = "live exchange/order mutation is not allowed by runtime gates"
    elif unsafe_action or unsafe_text:
        contract.requires_human = True
        contract.blocked = True
        contract.blocked_reason = "unsafe or externally mutating action requires an explicit human-owned path"

    if contract.blocked:
        contract.status = "blocked"
        contract.risk = "high"

    contract.safety = {**safety, **contract.safety}
    contract.updated_at = utc_now()
    return contract


def validate_contract(contract: ContractEnvelope) -> ContractEnvelope:
    if contract.schema_version != CONTRACT_SCHEMA_VERSION:
        raise ValueError(f"unsupported contract schema: {contract.schema_version}")
    if contract.contract_type not in CONTRACT_TYPES:
        raise ValueError(f"unsupported contract type: {contract.contract_type}")
    if contract.status not in CONTRACT_STATUSES:
        raise ValueError(f"unsupported contract status: {contract.status}")
    required = {
        "goal": ("objective",),
        "skill": ("name", "capability"),
        "task": ("instructions",),
        "job": ("task_ids",),
        "work_order": ("action_type",),
        "directive": ("directive",),
        "result": ("result",),
    }.get(contract.contract_type, ())
    missing = [key for key in required if key not in contract.payload]
    if missing:
        raise ValueError(f"missing required payload keys for {contract.contract_type}: {missing}")
    return apply_contract_safety(contract)


def goal_contract(
    objective: str,
    *,
    source: str = "organism",
    success_criteria: Optional[Iterable[str]] = None,
    route_surfaces: Optional[Iterable[str]] = None,
    priority: int = 5,
    tags: Optional[Iterable[str]] = None,
) -> ContractEnvelope:
    return validate_contract(
        ContractEnvelope(
            contract_id=new_id("goal"),
            contract_type="goal",
            title=str(objective)[:120] or "Goal",
            source=source,
            priority=priority,
            tags=list(tags or []),
            payload={
                "objective": str(objective),
                "success_criteria": list(success_criteria or []),
                "route_surfaces": list(route_surfaces or []),
                "loop": [
                    "understand",
                    "recall_memory",
                    "choose_route",
                    "create_tasks",
                    "queue_work_orders",
                    "observe_result",
                    "write_memory",
                ],
            },
        )
    )


def skill_contract(
    name: str,
    capability: str,
    *,
    source: str = "organism",
    input_schema: Optional[Dict[str, Any]] = None,
    output_schema: Optional[Dict[str, Any]] = None,
    safe_modes: Optional[Iterable[str]] = None,
    risk: str = "low",
) -> ContractEnvelope:
    return validate_contract(
        ContractEnvelope(
            contract_id=new_id("skill"),
            contract_type="skill",
            title=name,
            source=source,
            risk=risk,
            payload={
                "name": name,
                "capability": capability,
                "input_schema": _safe_dict(input_schema),
                "output_schema": _safe_dict(output_schema),
                "safe_modes": list(safe_modes or ["read_only", "local_draft", "publish_thought"]),
            },
        )
    )


def task_contract(
    title: str,
    instructions: str,
    *,
    goal_id: str = "",
    source: str = "organism",
    required_skills: Optional[Iterable[str]] = None,
    acceptance_checks: Optional[Iterable[str]] = None,
    parent_id: str = "",
    priority: int = 5,
) -> ContractEnvelope:
    return validate_contract(
        ContractEnvelope(
            contract_id=new_id("task"),
            contract_type="task",
            title=title,
            source=source,
            parent_id=parent_id or goal_id,
            priority=priority,
            payload={
                "goal_id": goal_id,
                "instructions": instructions,
                "required_skills": list(required_skills or []),
                "acceptance_checks": list(acceptance_checks or []),
            },
        )
    )


def job_contract(
    title: str,
    task_ids: Iterable[str],
    *,
    goal_id: str = "",
    source: str = "organism",
    queue: str = "default",
    parent_id: str = "",
    priority: int = 5,
) -> ContractEnvelope:
    task_id_list = list(task_ids)
    return validate_contract(
        ContractEnvelope(
            contract_id=new_id("job"),
            contract_type="job",
            title=title,
            source=source,
            queue=queue,
            parent_id=parent_id or goal_id,
            priority=priority,
            payload={
                "goal_id": goal_id,
                "task_ids": task_id_list,
                "queue": queue,
                "retry_policy": {"max_attempts": 1, "mode": "manual_retry"},
            },
        )
    )


def work_order_contract(
    title: str,
    action_type: str,
    *,
    job_id: str = "",
    goal_id: str = "",
    source: str = "organism",
    payload: Optional[Dict[str, Any]] = None,
    queue: str = "default",
    parent_id: str = "",
    priority: int = 5,
    requires_human: bool = False,
) -> ContractEnvelope:
    merged_payload = dict(payload or {})
    merged_payload.update(
        {
            "action_type": action_type,
            "job_id": job_id,
            "goal_id": goal_id,
            "queue": queue,
        }
    )
    return validate_contract(
        ContractEnvelope(
            contract_id=new_id("wo"),
            contract_type="work_order",
            title=title,
            source=source,
            status="queued",
            queue=queue,
            parent_id=parent_id or job_id or goal_id,
            priority=priority,
            requires_human=requires_human,
            payload=merged_payload,
        )
    )


def result_contract(
    title: str,
    result: Dict[str, Any],
    *,
    source: str = "organism",
    parent_id: str = "",
    ok: bool = True,
) -> ContractEnvelope:
    return validate_contract(
        ContractEnvelope(
            contract_id=new_id("result"),
            contract_type="result",
            title=title,
            source=source,
            status="completed" if ok else "failed",
            parent_id=parent_id,
            risk="low" if ok else "medium",
            payload={"result": dict(result), "ok": bool(ok)},
        )
    )


class OrganismContractStack:
    """Persistent local goal/task/job/work-order contract queue."""

    def __init__(
        self,
        *,
        thought_bus: Any = None,
        state_path: Optional[str | Path] = None,
        source: str = "organism_contract_stack",
    ) -> None:
        self.thought_bus = thought_bus
        self.state_path = Path(state_path or DEFAULT_STATE_PATH)
        self.source = source
        self.contracts: Dict[str, Dict[str, Any]] = {}
        self.queue: List[str] = []
        self.history: List[Dict[str, Any]] = []
        self._load()
        self._persist()

    def submit_goal(self, objective: str, **kwargs: Any) -> ContractEnvelope:
        contract = goal_contract(objective, source=kwargs.pop("source", self.source), **kwargs)
        return self.store(contract)

    def register_skill(self, name: str, capability: str, **kwargs: Any) -> ContractEnvelope:
        contract = skill_contract(name, capability, source=kwargs.pop("source", self.source), **kwargs)
        return self.store(contract)

    def create_task(self, title: str, instructions: str, **kwargs: Any) -> ContractEnvelope:
        contract = task_contract(title, instructions, source=kwargs.pop("source", self.source), **kwargs)
        return self.store(contract)

    def create_job(self, title: str, task_ids: Iterable[str], **kwargs: Any) -> ContractEnvelope:
        contract = job_contract(title, task_ids, source=kwargs.pop("source", self.source), **kwargs)
        return self.store(contract)

    def enqueue_work_order(self, title: str, action_type: str, **kwargs: Any) -> ContractEnvelope:
        contract = work_order_contract(title, action_type, source=kwargs.pop("source", self.source), **kwargs)
        return self.store(contract)

    def create_goal_workflow(
        self,
        objective: str,
        *,
        skills: Optional[Iterable[str]] = None,
        route_surfaces: Optional[Iterable[str]] = None,
        source: Optional[str] = None,
    ) -> Dict[str, Any]:
        skill_names = list(skills or [])
        goal = self.submit_goal(
            objective,
            source=source or self.source,
            route_surfaces=list(route_surfaces or ["memory", "reasoning", "contracts", "thought_bus"]),
            success_criteria=["work orders queued", "result observed", "memory written"],
        )
        task = self.create_task(
            "Plan and route goal",
            "Use the goal-capability map, relevant skills, ThoughtBus, vault memory, and safe local tools to plan the next step.",
            goal_id=goal.contract_id,
            parent_id=goal.contract_id,
            required_skills=skill_names,
            acceptance_checks=["route selected", "safe boundary checked", "next work order queued"],
            source=source or self.source,
        )
        job = self.create_job(
            "Execute routed goal plan",
            [task.contract_id],
            goal_id=goal.contract_id,
            parent_id=goal.contract_id,
            queue="organism.default",
            source=source or self.source,
        )
        work_order = self.enqueue_work_order(
            "Run internal goal step",
            "execute_internal_task",
            job_id=job.contract_id,
            goal_id=goal.contract_id,
            parent_id=job.contract_id,
            queue="organism.default",
            payload={
                "task_id": task.contract_id,
                "objective": objective,
                "recommended_skills": skill_names,
                "route_surfaces": list(route_surfaces or []),
            },
            source=source or self.source,
        )
        return {
            "goal": goal.to_dict(),
            "tasks": [task.to_dict()],
            "jobs": [job.to_dict()],
            "work_orders": [work_order.to_dict()],
        }

    def store(self, contract: ContractEnvelope) -> ContractEnvelope:
        contract = validate_contract(contract)
        data = contract.to_dict()
        self.contracts[contract.contract_id] = data
        if contract.contract_type == "work_order" and not contract.blocked:
            if contract.contract_id not in self.queue:
                self.queue.append(contract.contract_id)
        self.history.append(
            {
                "ts": utc_now(),
                "event": contract.topic(),
                "contract_id": contract.contract_id,
                "contract_type": contract.contract_type,
                "status": contract.status,
            }
        )
        self.history = self.history[-500:]
        self._persist()
        self._publish(contract.topic(), contract)
        return contract

    def claim_next(self, queue: str = "organism.default", worker: str = "organism") -> Optional[ContractEnvelope]:
        for contract_id in list(self.queue):
            contract = ContractEnvelope.from_dict(self.contracts.get(contract_id, {}))
            if contract.queue != queue or contract.status != "queued" or contract.blocked:
                continue
            contract.mark("active", worker=worker, claimed_at=utc_now())
            self.contracts[contract.contract_id] = contract.to_dict()
            self.queue.remove(contract.contract_id)
            self.history.append(
                {
                    "ts": utc_now(),
                    "event": CONTRACT_TOPICS["claimed"],
                    "contract_id": contract.contract_id,
                    "worker": worker,
                }
            )
            self._persist()
            self._publish(CONTRACT_TOPICS["claimed"], contract)
            return contract
        return None

    def claim_next_available(
        self,
        queues: Iterable[str],
        *,
        worker: str = "organism",
    ) -> Optional[ContractEnvelope]:
        """Claim fairly from multiple organism nerve queues.

        The deepest backlog is serviced first; the caller's queue order breaks
        ties. This prevents specialist queues from becoming disconnected while
        retaining deterministic behavior and the existing per-queue claim path.
        """

        queue_order = [str(item) for item in queues if str(item)]
        counts = {
            queue: sum(
                1
                for contract_id in self.queue
                for item in [self.contracts.get(contract_id, {})]
                if item.get("contract_type") == "work_order"
                and item.get("status") == "queued"
                and not item.get("blocked")
                and item.get("queue") == queue
            )
            for queue in queue_order
        }
        available = [queue for queue in queue_order if counts.get(queue, 0) > 0]
        if not available:
            return None
        selected = max(available, key=lambda queue: counts[queue])
        return self.claim_next(queue=selected, worker=worker)

    def deduplicate_queued_work_orders(
        self,
        queue: str,
        *,
        payload_path: Iterable[str],
        worker: str = "organism",
    ) -> Dict[str, Any]:
        """Cancel duplicate queued orders while preserving every envelope."""

        path = [str(item) for item in payload_path if str(item)]

        def identity(item: Dict[str, Any]) -> str:
            value: Any = item.get("payload") or {}
            for key in path:
                if not isinstance(value, dict):
                    return ""
                value = value.get(key)
            return str(value or "").strip().lower()

        candidates = sorted(
            (
                (contract_id, item)
                for contract_id, item in self.contracts.items()
                if item.get("contract_type") == "work_order"
                and item.get("status") == "queued"
                and not item.get("blocked")
                and item.get("queue") == queue
            ),
            key=lambda pair: (str(pair[1].get("created_at") or ""), pair[0]),
        )
        keepers: Dict[str, str] = {}
        superseded: list[Dict[str, str]] = []
        for contract_id, raw in candidates:
            key = identity(raw)
            if not key:
                continue
            keeper_id = keepers.get(key)
            if keeper_id is None:
                keepers[key] = contract_id
                continue
            contract = ContractEnvelope.from_dict(raw)
            contract.mark(
                "cancelled",
                superseded_by=keeper_id,
                superseded_reason="duplicate_open_work_order_identity",
                superseded_by_worker=worker,
            )
            self.contracts[contract_id] = contract.to_dict()
            if contract_id in self.queue:
                self.queue.remove(contract_id)
            event = {
                "ts": utc_now(),
                "event": CONTRACT_TOPICS["superseded"],
                "contract_id": contract_id,
                "superseded_by": keeper_id,
                "identity": key,
                "worker": worker,
            }
            self.history.append(event)
            superseded.append(
                {"contract_id": contract_id, "superseded_by": keeper_id, "identity": key}
            )
        if superseded:
            self.history = self.history[-500:]
            self._persist()
        return {
            "queue": queue,
            "identity_path": path,
            "keeper_count": len(keepers),
            "superseded_count": len(superseded),
            "superseded": superseded,
            "contracts_preserved": True,
        }

    def complete_work_order(
        self,
        contract_id: str,
        *,
        result: Optional[Dict[str, Any]] = None,
        ok: bool = True,
        worker: str = "organism",
    ) -> Optional[ContractEnvelope]:
        if contract_id not in self.contracts:
            return None
        contract = ContractEnvelope.from_dict(self.contracts[contract_id])
        contract.mark("completed" if ok else "failed", result=dict(result or {}), completed_by=worker)
        self.contracts[contract.contract_id] = contract.to_dict()
        self.history.append(
            {
                "ts": utc_now(),
                "event": CONTRACT_TOPICS["completed"] if ok else CONTRACT_TOPICS["failed"],
                "contract_id": contract.contract_id,
                "worker": worker,
            }
        )
        self._persist()
        self._publish(CONTRACT_TOPICS["completed"] if ok else CONTRACT_TOPICS["failed"], contract)
        self.store(
            result_contract(
                f"Result for {contract.title}",
                result or {},
                parent_id=contract.contract_id,
                ok=ok,
                source=worker,
            )
        )
        return contract

    def status(self) -> Dict[str, Any]:
        type_counts = Counter(item.get("contract_type") for item in self.contracts.values())
        status_counts = Counter(item.get("status") for item in self.contracts.values())
        queued = [
            item for item in self.contracts.values()
            if item.get("contract_type") == "work_order" and item.get("status") == "queued"
        ]
        return {
            "schema_version": "aureon-contract-stack-status-v1",
            "contract_schema_version": CONTRACT_SCHEMA_VERSION,
            "state_path": str(self.state_path),
            "contract_count": len(self.contracts),
            "type_counts": dict(sorted(type_counts.items())),
            "status_counts": dict(sorted(status_counts.items())),
            "queue_count": len(queued),
            "queues": dict(sorted(Counter(item.get("queue") for item in queued).items())),
            "topics": dict(CONTRACT_TOPICS),
            "recent": list(self.history[-12:]),
        }

    def publish_status(self) -> Dict[str, Any]:
        status = self.status()
        if self.thought_bus is not None:
            try:
                self.thought_bus.publish(CONTRACT_TOPICS["status"], status, source=self.source)
            except Exception:
                pass
        return status

    def import_state(self, state_path: str | Path) -> Dict[str, Any]:
        """Merge a compatible legacy contract state into this canonical stack.

        Existing contracts always win.  Imported queue membership is preserved
        only for work orders that are still queued and not blocked, so a
        completed or failed legacy order can never be accidentally reactivated.
        The source file is left untouched as an audit/recovery surface.
        """

        source_path = Path(state_path)
        result = {
            "source_path": str(source_path),
            "target_path": str(self.state_path),
            "source_available": source_path.exists(),
            "imported_contract_count": 0,
            "imported_queue_count": 0,
            "skipped_contract_count": 0,
            "source_preserved": True,
        }
        if not source_path.exists() or source_path.resolve() == self.state_path.resolve():
            return result
        try:
            data = json.loads(source_path.read_text(encoding="utf-8", errors="replace"))
        except Exception as exc:
            result["error"] = f"{type(exc).__name__}: {exc}"
            return result

        source_contracts = data.get("contracts") or {}
        source_queue = {str(item) for item in (data.get("queue") or [])}
        for contract_id, raw in source_contracts.items():
            contract_id = str(contract_id)
            if contract_id in self.contracts or not isinstance(raw, dict):
                result["skipped_contract_count"] += 1
                continue
            try:
                contract = validate_contract(ContractEnvelope.from_dict(raw))
            except Exception:
                result["skipped_contract_count"] += 1
                continue
            self.contracts[contract_id] = contract.to_dict()
            result["imported_contract_count"] += 1
            if (
                contract_id in source_queue
                and contract.contract_type == "work_order"
                and contract.status == "queued"
                and not contract.blocked
                and contract_id not in self.queue
            ):
                self.queue.append(contract_id)
                result["imported_queue_count"] += 1

        if result["imported_contract_count"]:
            self.history.append(
                {
                    "ts": utc_now(),
                    "event": "organism.contract.state_imported",
                    "source_path": str(source_path),
                    "imported_contract_count": result["imported_contract_count"],
                    "imported_queue_count": result["imported_queue_count"],
                }
            )
            self.history = self.history[-500:]
            self._persist()
        return result

    def _publish(self, topic: str, contract: ContractEnvelope) -> None:
        if self.thought_bus is None:
            return
        try:
            self.thought_bus.publish(
                topic,
                {"contract": contract.to_dict()},
                source=self.source,
                trace_id=contract.trace_id,
                parent_id=contract.parent_id or None,
            )
        except Exception:
            pass

    def _load(self) -> None:
        if not self.state_path.exists():
            return
        try:
            data = json.loads(self.state_path.read_text(encoding="utf-8", errors="replace"))
        except Exception:
            return
        self.contracts = {
            str(key): value
            for key, value in (data.get("contracts") or {}).items()
            if isinstance(value, dict)
        }
        self.queue = [
            str(item) for item in (data.get("queue") or [])
            if str(item) in self.contracts
        ]
        self.history = list(data.get("history") or [])[-500:]

    def _persist(self) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema_version": "aureon-contract-stack-state-v1",
            "updated_at": utc_now(),
            "contracts": self.contracts,
            "queue": self.queue,
            "history": self.history[-500:],
        }
        self.state_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def build_contract_stack_snapshot(repo_root: Optional[str | Path] = None) -> Dict[str, Any]:
    root = Path(repo_root or Path.cwd()).resolve()
    state_path = root / DEFAULT_STATE_PATH
    state_available = state_path.exists()
    contract_count = 0
    queue_count = 0
    if state_available:
        try:
            data = json.loads(state_path.read_text(encoding="utf-8", errors="replace"))
            contracts = data.get("contracts") or {}
            contract_count = len(contracts)
            queue_count = sum(
                1
                for item in contracts.values()
                if isinstance(item, dict)
                and item.get("contract_type") == "work_order"
                and item.get("status") == "queued"
            )
        except Exception:
            state_available = False
    return {
        "schema_version": "aureon-contract-stack-snapshot-v1",
        "contract_schema_version": CONTRACT_SCHEMA_VERSION,
        "state_path": str(state_path),
        "state_available": state_available,
        "contract_count": contract_count,
        "queue_count": queue_count,
        "contract_types": list(CONTRACT_TYPES),
        "contract_statuses": list(CONTRACT_STATUSES),
        "topics": dict(CONTRACT_TOPICS),
        "safe_boundaries": {
            "official_companies_house_filing": "manual_only",
            "official_hmrc_submission": "manual_only",
            "tax_or_penalty_payment": "manual_only",
            "exchange_or_trading_mutation": "requires_explicit_live_gate",
        },
    }


__all__ = [
    "CONTRACT_SCHEMA_VERSION",
    "CONTRACT_TYPES",
    "CONTRACT_STATUSES",
    "CONTRACT_TOPICS",
    "ContractEnvelope",
    "OrganismContractStack",
    "apply_contract_safety",
    "build_contract_stack_snapshot",
    "goal_contract",
    "job_contract",
    "result_contract",
    "skill_contract",
    "task_contract",
    "validate_contract",
    "work_order_contract",
]

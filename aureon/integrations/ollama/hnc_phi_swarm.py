"""HNC phi-routed Ollama Cloud reasoning swarm.

Research packets seed a bounded set of specialist model calls selected from
the authenticated live Ollama catalog.  The calls run in parallel and a final
coordinator reconciles their evidence.  HNC/Auris changes Fibonacci-sized
fan-out and proof depth; it never creates an internal no-thought state.
"""

from __future__ import annotations

import json
import math
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Sequence

from aureon.integrations.ollama.model_switchboard import OllamaModelSwitchboard


PHI = (1.0 + math.sqrt(5.0)) / 2.0
PHI_INV = 1.0 / PHI
SCHEMA_VERSION = "aureon-hnc-phi-ollama-swarm-v1"

ROLE_SPECS: tuple[tuple[str, str, str], ...] = (
    ("researcher", "general", "Extract the strongest repo-grounded evidence and identify uncertainty."),
    ("architect", "architecture", "Map subsystem dependencies, interfaces, and the smallest coherent design."),
    ("implementer", "coding", "Propose a bounded implementation and exact validation path."),
    ("challenger", "self_evolution", "Find failure modes, disconnected pathways, and rollback conditions."),
    ("rapid_scout", "fast", "Look for a simpler route, missing assumption, or fast falsification test."),
)

FLOW_WORKERS = {
    "expand": 5,
    "steady": 3,
    "observe": 2,
    "repair": 3,
}

SYNTHESIS_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "consensus": {"type": "string"},
        "disagreements": {"type": "array", "items": {"type": "string"}},
        "next_bounded_action": {"type": "string"},
        "validation": {"type": "array", "items": {"type": "string"}},
        "rollback": {"type": "string"},
        "evidence_ids": {"type": "array", "items": {"type": "string"}},
        "uncertainties": {"type": "array", "items": {"type": "string"}},
    },
    "required": [
        "consensus",
        "disagreements",
        "next_bounded_action",
        "validation",
        "rollback",
        "evidence_ids",
        "uncertainties",
    ],
}


def _env_int(name: str, default: int, *, minimum: int, maximum: int) -> int:
    try:
        value = int(os.environ.get(name, str(default)))
    except (TypeError, ValueError):
        value = default
    return max(minimum, min(maximum, value))


def _parse_json_object(content: str) -> Optional[Dict[str, Any]]:
    """Accept strict JSON plus common fenced/prefaced model variants."""

    text = str(content or "").strip()
    if not text:
        return None
    candidates = [text]
    fenced = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, flags=re.IGNORECASE | re.DOTALL)
    if fenced:
        candidates.insert(0, fenced.group(1))
    brace = text.find("{")
    if brace >= 0:
        candidates.append(text[brace:])
    for candidate in candidates:
        try:
            value = json.loads(candidate)
            if isinstance(value, dict):
                return value
        except json.JSONDecodeError:
            try:
                value, _end = json.JSONDecoder().raw_decode(candidate)
                if isinstance(value, dict):
                    return value
            except json.JSONDecodeError:
                pass
    return None


def build_phi_swarm_plan(
    flow: Dict[str, Any],
    *,
    catalog_size: int,
    max_total_calls: Optional[int] = None,
) -> Dict[str, Any]:
    """Turn the non-blocking evolution flow into a bounded Fibonacci fan-out."""

    flow_name = str(flow.get("flow") or "observe")
    call_ceiling = max_total_calls or _env_int(
        "AUREON_OLLAMA_SWARM_MAX_CALLS", 6, minimum=2, maximum=9
    )
    desired_workers = FLOW_WORKERS.get(flow_name, FLOW_WORKERS["observe"])
    available_workers = max(1, int(catalog_size or 1))
    worker_count = min(desired_workers, available_workers, call_ceiling - 1, len(ROLE_SPECS))
    weights = [PHI_INV ** index for index in range(worker_count)]
    weight_total = sum(weights) or 1.0
    return {
        "flow": flow_name,
        "worker_count": worker_count,
        "synthesis_call_count": 1,
        "max_reasoning_calls": call_ceiling,
        "planned_total_calls": worker_count + 1,
        "availability_probe_ceiling_per_selection": 5,
        "phi": PHI,
        "phi_inverse": PHI_INV,
        "worker_weights": [round(value / weight_total, 6) for value in weights],
        "minimum_review_cycles": int(flow.get("minimum_review_cycles") or 1),
        "internal_blocking": False,
    }


class HNCPhiOllamaSwarm:
    """Recruit live Ollama models as parallel, research-grounded nerve cells."""

    def __init__(
        self,
        *,
        repo_root: str | Path,
        switchboard: Optional[OllamaModelSwitchboard] = None,
        research_provider: Optional[Callable[[str, int], Sequence[Dict[str, Any]]]] = None,
    ) -> None:
        self.repo_root = Path(repo_root).resolve()
        self.switchboard = switchboard or OllamaModelSwitchboard()
        self.research_provider = research_provider

    def _research(self, objective: str, top_k: int) -> list[Dict[str, Any]]:
        if self.research_provider is not None:
            return [dict(item) for item in self.research_provider(objective, top_k)][:top_k]
        try:
            from aureon.queen.research_corpus_index import ResearchCorpusIndex

            index = ResearchCorpusIndex(
                root=str(self.repo_root / "docs"),
                cache_path=str(self.repo_root / "state" / "research_index.json"),
                exclude=("archive",),
            )
            research_query = (
                f"{objective} HNC Auris coherence Ollama model switchboard "
                "organism contract stack implementation validation"
            )
            return [item.to_dict() for item in index.search(research_query, top_k=top_k)]
        except Exception as exc:
            return [{"doc_id": "research_index", "text": "Research lookup unavailable.", "error": type(exc).__name__}]

    def _operational_evidence(
        self,
        flow: Dict[str, Any],
        switchboard_snapshot: Dict[str, Any],
    ) -> list[Dict[str, Any]]:
        """Add current runtime facts so research cannot masquerade as implementation proof."""

        packets: list[Dict[str, Any]] = [
            {
                "doc_id": "runtime/hnc_evolution_flow",
                "paragraph_idx": 0,
                "title": "Current HNC/Auris evolution flow",
                "text": json.dumps(
                    {
                        key: flow.get(key)
                        for key in (
                            "flow",
                            "field_status",
                            "gamma",
                            "auris_confidence",
                            "beta",
                            "patch_batch_limit",
                            "minimum_review_cycles",
                            "required_test_layers",
                        )
                    },
                    sort_keys=True,
                    default=str,
                ),
                "evidence_tier": "runtime_observation",
            },
            {
                "doc_id": "runtime/ollama_model_switchboard",
                "paragraph_idx": 0,
                "title": "Authenticated live Ollama catalog",
                "text": json.dumps(
                    {
                        "reachable": switchboard_snapshot.get("reachable"),
                        "catalog_size": switchboard_snapshot.get("catalog_size"),
                        "lanes": {
                            lane: (selection or {}).get("model")
                            for lane, selection in (switchboard_snapshot.get("lanes") or {}).items()
                        },
                        "credential_values_exposed": False,
                    },
                    sort_keys=True,
                ),
                "evidence_tier": "runtime_observation",
            },
        ]
        readiness_path = self.repo_root / "docs" / "audits" / "aureon_system_readiness_audit.json"
        contracts_path = self.repo_root / "state" / "organism_contract_stack.json"
        try:
            readiness = json.loads(readiness_path.read_text(encoding="utf-8"))
            packets.append(
                {
                    "doc_id": "runtime/system_readiness",
                    "paragraph_idx": 0,
                    "title": "Current system readiness",
                    "text": json.dumps(
                        {
                            "status": readiness.get("status"),
                            "summary": readiness.get("summary"),
                        },
                        sort_keys=True,
                    ),
                    "evidence_tier": "generated_audit",
                }
            )
        except Exception:
            pass
        try:
            contract_state = json.loads(contracts_path.read_text(encoding="utf-8"))
            contracts = contract_state.get("contracts") or {}
            queued = [
                item
                for item in contracts.values()
                if isinstance(item, dict)
                and item.get("contract_type") == "work_order"
                and item.get("status") == "queued"
            ]
            queue_counts: Dict[str, int] = {}
            for item in queued:
                queue = str(item.get("queue") or "organism.default")
                queue_counts[queue] = queue_counts.get(queue, 0) + 1
            packets.append(
                {
                    "doc_id": "runtime/organism_contract_stack",
                    "paragraph_idx": 0,
                    "title": "Canonical organism contract bus",
                    "text": json.dumps(
                        {
                            "contract_count": len(contracts),
                            "queued_work_order_count": len(queued),
                            "queues": queue_counts,
                        },
                        sort_keys=True,
                    ),
                    "evidence_tier": "runtime_state",
                }
            )
        except Exception:
            pass
        return packets

    def _recruit(self, count: int) -> list[Dict[str, Any]]:
        recruited: list[Dict[str, Any]] = []
        used: set[str] = set()
        for role, lane, instruction in ROLE_SPECS[:count]:
            ranked = self.switchboard.rank(lane, limit=1, exclude=used)
            if not ranked:
                ranked = self.switchboard.rank("general", limit=1, exclude=used)
            if not ranked:
                ranked = self.switchboard.rank(lane, limit=1)
            if not ranked or not ranked[0].model:
                continue
            selection = ranked[0]
            used.add(selection.model.lower())
            recruited.append(
                {
                    "role": role,
                    "lane": lane,
                    "instruction": instruction,
                    "model": selection.model,
                    "selection_source": selection.source,
                }
            )
        return recruited

    def _call_worker(
        self,
        worker: Dict[str, Any],
        objective: str,
        research: Sequence[Dict[str, Any]],
        flow: Dict[str, Any],
        weight: float,
    ) -> Dict[str, Any]:
        started = time.monotonic()
        bridge, selection = self.switchboard.bridge_for(worker["lane"], preferred=worker["model"])
        evidence = "\n".join(
            f"[{item.get('doc_id', 'research')}#{item.get('paragraph_idx', 0)}] {str(item.get('text', ''))[:900]}"
            for item in research
        )
        prompt = (
            f"Objective: {objective}\n"
            f"HNC evolution flow: {flow.get('flow')}; gamma={flow.get('gamma')}; "
            f"proof cycles={flow.get('minimum_review_cycles')}.\n"
            f"Your swarm role: {worker['role']}. {worker['instruction']}\n"
            "Use only the supplied Aureon research evidence for factual repo claims. "
            "Name evidence IDs, distinguish observation from proposal, and do not execute external actions. "
            "Research or symbolic claims are context, never proof that code exists; implementation claims require "
            "runtime, generated-audit, runtime-state, or exact file evidence.\n\n"
            f"Research evidence:\n{evidence or '[no matching research packet]'}"
        )
        reply = bridge.chat(
            [{"role": "user", "content": prompt}],
            model=selection.model,
            options={
                "temperature": 0.2,
                "num_predict": _env_int("AUREON_OLLAMA_SWARM_WORKER_TOKENS", 384, minimum=128, maximum=1024),
            },
        )
        content = str((reply.get("message") or {}).get("content") or "").strip()
        error = str(reply.get("error") or "")[:300]
        return {
            "role": worker["role"],
            "lane": worker["lane"],
            "model": selection.model,
            "selection_source": selection.source,
            "phi_weight": round(weight, 6),
            "ok": bool(content) and not error,
            "content": content[:8000],
            "error": error,
            "duration_s": round(time.monotonic() - started, 3),
            "prompt_eval_count": int(reply.get("prompt_eval_count") or 0),
            "eval_count": int(reply.get("eval_count") or 0),
        }

    def _synthesize(
        self,
        objective: str,
        flow: Dict[str, Any],
        workers: Sequence[Dict[str, Any]],
    ) -> Dict[str, Any]:
        started = time.monotonic()
        bridge, selection = self.switchboard.bridge_for("architecture")
        packets = "\n\n".join(
            f"[{item.get('role')} via {item.get('model')}, phi_weight={item.get('phi_weight')}]\n{item.get('content')}"
            for item in workers
            if item.get("ok")
        )
        if not packets:
            return {
                "ok": False,
                "model": selection.model,
                "answer": "No cloud worker returned usable content; retain the native repair loop and retry.",
                "error": "no_usable_worker_responses",
                "duration_s": round(time.monotonic() - started, 3),
            }
        prompt = (
            f"Reconcile this HNC phi swarm for objective: {objective}\n"
            f"Flow={flow.get('flow')}; required proof layers={flow.get('required_test_layers')}.\n"
            "Return only the requested compact JSON object, with no markdown or preamble. "
            "Prefer repo-grounded evidence, preserve uncertainty, and never authorize credentials, live money, "
            "official filings, or destructive actions.\n\n"
            f"Worker packets:\n{packets[:24000]}"
        )
        reply = bridge.chat(
            [{"role": "user", "content": prompt}],
            model=selection.model,
            format=SYNTHESIS_SCHEMA,
            options={
                "temperature": 0.1,
                "num_predict": _env_int("AUREON_OLLAMA_SWARM_SYNTHESIS_TOKENS", 1200, minimum=256, maximum=2048),
            },
        )
        content = str((reply.get("message") or {}).get("content") or "").strip()
        parsed = _parse_json_object(content)
        error = str(reply.get("error") or "")[:300]
        return {
            "ok": bool(content) and not error,
            "model": selection.model,
            "selection_source": selection.source,
            "answer": parsed if isinstance(parsed, dict) else content[:12000],
            "error": error,
            "duration_s": round(time.monotonic() - started, 3),
            "prompt_eval_count": int(reply.get("prompt_eval_count") or 0),
            "eval_count": int(reply.get("eval_count") or 0),
        }

    def run(self, objective: str, flow: Dict[str, Any]) -> Dict[str, Any]:
        started_at = time.time()
        started = time.monotonic()
        snapshot = self.switchboard.snapshot()
        plan = build_phi_swarm_plan(flow, catalog_size=int(snapshot.get("catalog_size") or 0))
        research = self._operational_evidence(flow, snapshot) + self._research(
            objective,
            top_k=max(3, plan["worker_count"]),
        )
        recruited = self._recruit(plan["worker_count"])
        results: list[Dict[str, Any]] = []
        if snapshot.get("reachable") and recruited:
            with ThreadPoolExecutor(max_workers=len(recruited), thread_name_prefix="aureon-phi-swarm") as pool:
                futures = {
                    pool.submit(
                        self._call_worker,
                        worker,
                        objective,
                        research,
                        flow,
                        plan["worker_weights"][index],
                    ): index
                    for index, worker in enumerate(recruited)
                }
                ordered: Dict[int, Dict[str, Any]] = {}
                for future in as_completed(futures):
                    index = futures[future]
                    try:
                        ordered[index] = future.result()
                    except Exception as exc:
                        ordered[index] = {
                            "role": recruited[index]["role"],
                            "model": recruited[index]["model"],
                            "ok": False,
                            "error": f"{type(exc).__name__}: {exc}"[:300],
                        }
                results = [ordered[index] for index in sorted(ordered)]
        synthesis = self._synthesize(objective, flow, results) if results else {
            "ok": False,
            "answer": "The live cloud catalog was unavailable; native Aureon reasoning remains active and the swarm will retry.",
            "error": "cloud_catalog_unavailable",
        }
        successful = sum(1 for item in results if item.get("ok"))
        final_switchboard = self.switchboard.snapshot()
        availability_probe_count = sum(
            1
            for item in (final_switchboard.get("availability") or {}).values()
            if float(item.get("last_probe_at") or 0) >= started_at
        )
        reasoning_call_count = len(results) + (1 if results else 0)
        return {
            "schema_version": SCHEMA_VERSION,
            "status": "hnc_phi_swarm_synthesized" if synthesis.get("ok") else "hnc_phi_swarm_native_retry",
            "ok": bool(synthesis.get("ok")),
            "objective": objective,
            "plan": plan,
            "research_packets": research,
            "workers": results,
            "synthesis": synthesis,
            "model_switchboard": final_switchboard,
            "summary": {
                "catalog_size": final_switchboard.get("catalog_size", 0),
                "recruited_worker_count": len(recruited),
                "successful_worker_count": successful,
                "api_call_count": reasoning_call_count,
                "reasoning_api_call_count": reasoning_call_count,
                "availability_probe_call_count": availability_probe_count,
                "total_cloud_request_count": reasoning_call_count + availability_probe_count,
                "distinct_worker_models": len({item.get("model") for item in results if item.get("model")}),
                "research_packet_count": len(research),
                "internal_blocking": False,
                "credential_values_exposed": False,
                "duration_s": round(time.monotonic() - started, 3),
            },
            "outer_authority_boundary_preserved": True,
        }


__all__ = [
    "PHI",
    "PHI_INV",
    "SCHEMA_VERSION",
    "HNCPhiOllamaSwarm",
    "build_phi_swarm_plan",
    "_parse_json_object",
]

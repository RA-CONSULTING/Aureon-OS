"""
IntegrationAuditTrail — Machine-Readable Checklist + Health Audit
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

One place where the Queen can ask "what's connected, what's broken, and
what still needs doing?" across every external integration. Each check
runs a tiny probe (import-test, HTTP ping, filesystem access, adapter
health) and writes the result into a durable audit log on disk at:

    integrations_audit.jsonl   (one JSONL event per audit run, repo root)

The checklist is a literal Python list of `CheckResult` spec rows — the
same list that generates the "✓/✗" report you see in docs and that the
self-feedback loop can emit at boot. Add a row here whenever you wire a
new integration.
"""

from __future__ import annotations

import datetime as _dt
import importlib
import json
import logging
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("aureon.integrations.audit")

AUDIT_LOG_PATH = Path("integrations_audit.jsonl")


# ─────────────────────────────────────────────────────────────────────────────
# Types
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class CheckResult:
    """One line of the audit checklist."""

    name: str
    category: str  # ollama | obsidian | wiring | pathway | inhouse_ai
    description: str
    passed: bool = False
    detail: str = ""
    duration_ms: float = 0.0
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "category": self.category,
            "description": self.description,
            "passed": self.passed,
            "detail": self.detail,
            "duration_ms": round(self.duration_ms, 3),
            "timestamp": self.timestamp,
            "iso_time": _dt.datetime.utcfromtimestamp(self.timestamp).isoformat()
            + "Z",
        }


@dataclass
class IntegrationStatus:
    """Aggregate snapshot of every integration check."""

    audit_id: str
    when: float
    results: List[CheckResult] = field(default_factory=list)

    @property
    def passed(self) -> int:
        return sum(1 for r in self.results if r.passed)

    @property
    def failed(self) -> int:
        return sum(1 for r in self.results if not r.passed)

    @property
    def total(self) -> int:
        return len(self.results)

    @property
    def health_ratio(self) -> float:
        return self.passed / max(self.total, 1)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "audit_id": self.audit_id,
            "when": self.when,
            "iso_time": _dt.datetime.utcfromtimestamp(self.when).isoformat() + "Z",
            "total": self.total,
            "passed": self.passed,
            "failed": self.failed,
            "health_ratio": round(self.health_ratio, 4),
            "results": [r.to_dict() for r in self.results],
        }

    def summary_lines(self) -> List[str]:
        out: List[str] = []
        out.append(
            f"Integration Audit {self.audit_id} "
            f"— {self.passed}/{self.total} checks passed "
            f"({self.health_ratio * 100:.0f}%)"
        )
        for r in self.results:
            mark = "✓" if r.passed else "✗"
            out.append(f"  {mark} [{r.category}] {r.name}: {r.detail}")
        return out


# ─────────────────────────────────────────────────────────────────────────────
# Checklist spec (the machine-readable table of what we audit)
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class CheckSpec:
    """A checklist entry: name, category, probe function."""

    name: str
    category: str
    description: str
    probe: Callable[[], Any]


def _check_import(module_path: str) -> Any:
    """Probe: importable python module."""
    def probe() -> Any:
        importlib.import_module(module_path)
        return {"module": module_path}
    return probe


def _check_class(module_path: str, class_name: str) -> Any:
    """Probe: importable + class exists."""
    def probe() -> Any:
        mod = importlib.import_module(module_path)
        cls = getattr(mod, class_name, None)
        if cls is None:
            raise AttributeError(f"{class_name} not found in {module_path}")
        return {"class": f"{module_path}.{class_name}"}
    return probe


def _check_ollama_bridge() -> Any:
    """Probe: instantiate + health-check the OllamaBridge."""
    from aureon.integrations.ollama import OllamaBridge
    bridge = OllamaBridge()
    reachable = bridge.health_check()
    snap = bridge.snapshot()
    return {
        "reachable": reachable,
        "base_url": snap.get("base_url"),
        "model_count": len(snap.get("models", [])),
        "running_count": len(snap.get("running", [])),
        "version": snap.get("version"),
    }


def _check_ollama_adapter_interface() -> Any:
    """Probe: OllamaLLMAdapter implements the LLMAdapter protocol."""
    from aureon.integrations.ollama import OllamaModelSwitchboard
    from aureon.inhouse_ai.llm_adapter import LLMAdapter
    adapter, selection = OllamaModelSwitchboard().adapter_for("general")
    if not isinstance(adapter, LLMAdapter):
        raise TypeError("OllamaLLMAdapter is not an LLMAdapter")
    return {
        "adapter": "OllamaLLMAdapter",
        "interface": "LLMAdapter",
        "lane": selection.lane,
        "model": selection.model,
        "catalog_size": selection.catalog_size,
    }


def _check_obsidian_bridge() -> Any:
    """Probe: instantiate + health-check the ObsidianBridge."""
    from aureon.integrations.obsidian import ObsidianBridge
    bridge = ObsidianBridge()
    reachable = bridge.health_check()
    snap = bridge.snapshot()
    return {
        "reachable": reachable,
        "mode": snap.get("mode"),
        "vault_path": snap.get("vault_path"),
        "note_count": snap.get("note_count"),
    }


def _check_obsidian_sink() -> Any:
    """Probe: ObsidianSink accepts an ObsidianBridge and reports status."""
    from aureon.integrations.obsidian import ObsidianBridge, ObsidianSink
    sink = ObsidianSink(ObsidianBridge())
    return sink.get_status()


def _check_vault_voice_loop() -> Any:
    """Probe: vault + voice layer imports and the cognitive loop exists."""
    from aureon.vault import (
        AureonVault,
        AureonSelfFeedbackLoop,
        SelfDialogueEngine,
        ThoughtStreamLoop,
    )
    vault = AureonVault()
    loop = AureonSelfFeedbackLoop(vault=vault, enable_voice=False)
    return {
        "vault_size": len(vault),
        "loop_id": loop.loop_id,
        "voice_engine_ready": bool(SelfDialogueEngine(vault=vault)),
        "thought_stream_ready": bool(ThoughtStreamLoop(vault=vault)),
    }


def _check_neural_pathway() -> Any:
    """Probe: the NeuralPathwayMapper can build a non-empty graph."""
    from aureon.integrations.neural_pathway_mapper import NeuralPathwayMapper
    mapper = NeuralPathwayMapper()
    graph = mapper.build_graph(max_modules=50)
    return {
        "nodes": len(graph.nodes),
        "edges": sum(len(v) for v in graph.edges.values()),
        "clusters": len(graph.clusters),
    }


# The literal checklist — add a row when you wire a new integration.
INTEGRATION_CHECKLIST: List[CheckSpec] = [
    CheckSpec(
        name="ollama.bridge.import",
        category="ollama",
        description="aureon.integrations.ollama.OllamaBridge imports",
        probe=_check_class(
            "aureon.integrations.ollama", "OllamaBridge"
        ),
    ),
    CheckSpec(
        name="ollama.adapter.import",
        category="ollama",
        description="aureon.integrations.ollama.OllamaLLMAdapter imports",
        probe=_check_class(
            "aureon.integrations.ollama", "OllamaLLMAdapter"
        ),
    ),
    CheckSpec(
        name="ollama.bridge.health",
        category="ollama",
        description="OllamaBridge reaches /api/version (graceful on unreachable)",
        probe=_check_ollama_bridge,
    ),
    CheckSpec(
        name="ollama.adapter.interface",
        category="ollama",
        description="OllamaLLMAdapter implements aureon.inhouse_ai.LLMAdapter",
        probe=_check_ollama_adapter_interface,
    ),
    CheckSpec(
        name="obsidian.bridge.import",
        category="obsidian",
        description="aureon.integrations.obsidian.ObsidianBridge imports",
        probe=_check_class(
            "aureon.integrations.obsidian", "ObsidianBridge"
        ),
    ),
    CheckSpec(
        name="obsidian.sink.import",
        category="obsidian",
        description="aureon.integrations.obsidian.ObsidianSink imports",
        probe=_check_class(
            "aureon.integrations.obsidian", "ObsidianSink"
        ),
    ),
    CheckSpec(
        name="obsidian.bridge.health",
        category="obsidian",
        description="ObsidianBridge picks a mode (local_rest OR filesystem)",
        probe=_check_obsidian_bridge,
    ),
    CheckSpec(
        name="obsidian.sink.health",
        category="obsidian",
        description="ObsidianSink status reports reachable + mode",
        probe=_check_obsidian_sink,
    ),
    CheckSpec(
        name="wiring.vault_voice_loop",
        category="wiring",
        description="AureonVault + SelfFeedbackLoop + VoiceEngine all import together",
        probe=_check_vault_voice_loop,
    ),
    CheckSpec(
        name="pathway.neural_mapper",
        category="pathway",
        description="NeuralPathwayMapper builds a non-empty graph",
        probe=_check_neural_pathway,
    ),
    CheckSpec(
        name="inhouse_ai.llm_adapter",
        category="inhouse_ai",
        description="aureon.inhouse_ai.llm_adapter still importable",
        probe=_check_import("aureon.inhouse_ai.llm_adapter"),
    ),
    CheckSpec(
        name="inhouse_ai.orchestrator",
        category="inhouse_ai",
        description="aureon.inhouse_ai.orchestrator.OpenMultiAgent still exists",
        probe=_check_class(
            "aureon.inhouse_ai.orchestrator", "OpenMultiAgent"
        ),
    ),
]


# ─────────────────────────────────────────────────────────────────────────────
# IntegrationAuditTrail
# ─────────────────────────────────────────────────────────────────────────────


class IntegrationAuditTrail:
    """
    Runs the checklist, captures results, and appends a JSONL audit
    event to `integrations_audit.jsonl` at the repo root.

    Usage:
        trail = IntegrationAuditTrail()
        status = trail.run()
        print("\n".join(status.summary_lines()))
    """

    def __init__(self, log_path: Optional[Path] = None):
        self.log_path = Path(log_path or AUDIT_LOG_PATH)
        self._last_status: Optional[IntegrationStatus] = None

    def run(
        self,
        include: Optional[List[str]] = None,
        emit_to_sink: Optional[Callable[[Dict[str, Any]], None]] = None,
    ) -> IntegrationStatus:
        """Run every check (or just those whose name/category is in `include`)."""
        audit_id = _dt.datetime.utcnow().strftime("audit_%Y%m%dT%H%M%S")
        when = time.time()
        results: List[CheckResult] = []
        for spec in INTEGRATION_CHECKLIST:
            if include and not (
                spec.name in include or spec.category in include
            ):
                continue
            result = self._run_one(spec)
            results.append(result)

        status = IntegrationStatus(audit_id=audit_id, when=when, results=results)
        self._last_status = status
        self._persist(status)
        if emit_to_sink is not None:
            try:
                emit_to_sink(status.to_dict())
            except Exception as e:
                logger.debug("audit sink emit failed: %s", e)
        return status

    def _run_one(self, spec: CheckSpec) -> CheckResult:
        t0 = time.time()
        result = CheckResult(
            name=spec.name,
            category=spec.category,
            description=spec.description,
        )
        try:
            payload = spec.probe()
            result.passed = True
            if isinstance(payload, dict):
                result.detail = json.dumps(payload, default=str)[:500]
            else:
                result.detail = str(payload)[:500]
        except Exception as e:
            result.passed = False
            result.detail = f"{type(e).__name__}: {e}"
        finally:
            result.duration_ms = (time.time() - t0) * 1000.0
        return result

    def _persist(self, status: IntegrationStatus) -> None:
        try:
            self.log_path.parent.mkdir(parents=True, exist_ok=True)
            with self.log_path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(status.to_dict(), default=str) + "\n")
        except Exception as e:
            logger.debug("audit persist failed: %s", e)

    @property
    def last_status(self) -> Optional[IntegrationStatus]:
        return self._last_status


# ─────────────────────────────────────────────────────────────────────────────
# One-shot convenience
# ─────────────────────────────────────────────────────────────────────────────


def run_full_audit(
    log_path: Optional[Path] = None,
    emit_to_sink: Optional[Callable[[Dict[str, Any]], None]] = None,
) -> IntegrationStatus:
    """Run the full checklist once and return the resulting status."""
    trail = IntegrationAuditTrail(log_path=log_path)
    return trail.run(emit_to_sink=emit_to_sink)


if __name__ == "__main__":  # pragma: no cover
    logging.basicConfig(level=logging.INFO)
    s = run_full_audit()
    print("\n".join(s.summary_lines()))

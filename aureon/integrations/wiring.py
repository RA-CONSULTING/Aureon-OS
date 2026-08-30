"""
wiring — Plug Ollama + Obsidian into the Recently-Worked Cognitive Loops
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

One entry point — `wire_integrations(vault, loop)` — that takes the
AureonVault + AureonSelfFeedbackLoop and:

  1. Builds an `OllamaBridge` and `OllamaLLMAdapter`, and (if Ollama is
     reachable) swaps the vault voice adapters over so every
     self-dialogue turn runs on a local Ollama model via the native
     /api/chat surface instead of the default AureonBrain fallback.
  2. Builds an `ObsidianBridge` + `ObsidianSink` and registers the sink
     as `on_utterance` + `on_tick` observer so every utterance becomes
     a markdown note and every tick appends a log line.
  3. Runs the `NeuralPathwayMapper` once and writes the graph into
     `vault.pathway_graph`, then ingests a `pathway.graph.built` card.
  4. Runs the `IntegrationAuditTrail` once at wire-time and emits the
     snapshot into the ObsidianSink audit note.

The function is idempotent — calling it twice is safe; the second call
re-checks health and refreshes the audit trail but does not duplicate
observers.

All components degrade gracefully. Missing Ollama? The vault voices keep
using AureonBrainAdapter. Missing Obsidian? The sink stays dormant and
the loop still ticks. Missing `requests`? Both bridges log a degraded
health result and every write becomes a no-op.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from aureon.integrations.audit_trail import (
    IntegrationAuditTrail,
    IntegrationStatus,
)
from aureon.integrations.neural_pathway_mapper import NeuralPathwayMapper
from aureon.integrations.obsidian import ObsidianBridge, ObsidianSink, ObsidianSinkConfig
from aureon.integrations.ollama import OllamaBridge, OllamaLLMAdapter, OllamaModelSwitchboard

logger = logging.getLogger("aureon.integrations.wiring")


# ─────────────────────────────────────────────────────────────────────────────
# WiringResult
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class WiringResult:
    """Everything that got built + wired in one call."""

    ollama_bridge: Any = None
    ollama_adapter: Any = None
    obsidian_bridge: Any = None
    obsidian_sink: Any = None
    pathway_mapper: Any = None
    audit: Optional[IntegrationStatus] = None
    pathway_stats: Dict[str, Any] = field(default_factory=dict)
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        def snap(obj: Any) -> Any:
            if obj is None:
                return None
            if hasattr(obj, "snapshot"):
                try:
                    return obj.snapshot()
                except Exception:
                    return None
            if hasattr(obj, "get_status"):
                try:
                    return obj.get_status()
                except Exception:
                    return None
            return str(obj)

        return {
            "ollama": snap(self.ollama_bridge),
            "ollama_adapter": (
                "OllamaLLMAdapter" if self.ollama_adapter is not None else None
            ),
            "obsidian": snap(self.obsidian_bridge),
            "obsidian_sink": snap(self.obsidian_sink),
            "pathway_stats": self.pathway_stats,
            "audit": self.audit.to_dict() if self.audit else None,
            "notes": list(self.notes),
        }


# ─────────────────────────────────────────────────────────────────────────────
# Main entry point
# ─────────────────────────────────────────────────────────────────────────────


# A tiny registry so we don't attach the same sink twice
_WIRED_LOOPS: "set[str]" = set()


def wire_integrations(
    vault: Any,
    loop: Any = None,
    goal_engine: Any = None,
    enable_ollama: bool = True,
    enable_obsidian: bool = True,
    enable_pathway_mapping: bool = True,
    run_audit: bool = True,
    obsidian_config: Optional[ObsidianSinkConfig] = None,
    ollama_model: Optional[str] = None,
) -> WiringResult:
    """
    Wire Ollama + Obsidian into the given vault + self-feedback loop.

    Args:
        vault: an AureonVault (required)
        loop:  an AureonSelfFeedbackLoop (optional — if given, the sink
               will receive tick events via a wrapped `tick()`)
        enable_ollama: if True and Ollama is reachable, swap the voice
                       adapters over to OllamaLLMAdapter
        enable_obsidian: if True, build the Obsidian bridge + sink and
                         attach to the voice engine's on_utterance hook
        enable_pathway_mapping: if True, populate vault.pathway_graph
        run_audit: if True, execute the integration audit trail immediately
        obsidian_config: optional ObsidianSinkConfig override
        ollama_model: optional model name for OllamaLLMAdapter

    Returns:
        WiringResult carrying every wired component.
    """
    result = WiringResult()

    # ── 1. Ollama ───────────────────────────────────────────────────────
    if enable_ollama:
        try:
            result.ollama_bridge = OllamaBridge()
            reachable = result.ollama_bridge.health_check()
            result.notes.append(
                f"ollama_bridge reachable={reachable} "
                f"base={result.ollama_bridge.base_url}"
            )
            if reachable:
                result.ollama_adapter, selection = OllamaModelSwitchboard(
                    bridge=result.ollama_bridge
                ).adapter_for(
                    "general",
                    preferred=ollama_model or "",
                )
                result.ollama_bridge = result.ollama_adapter.bridge
                result.notes.append(
                    f"ollama nerve lane=general model={selection.model} source={selection.source}"
                )
                _swap_voice_adapters(loop, result.ollama_adapter, result.notes)
                if goal_engine is not None and hasattr(goal_engine, "set_ollama_adapter"):
                    goal_engine.set_ollama_adapter(result.ollama_adapter)
                    result.notes.append("goal_engine wired to OllamaLLMAdapter")
            else:
                result.notes.append(
                    "ollama unreachable — voices keep using AureonBrainAdapter"
                )
        except Exception as e:
            result.notes.append(f"ollama wiring failed: {e}")

    # ── 2. Obsidian ─────────────────────────────────────────────────────
    if enable_obsidian:
        try:
            result.obsidian_bridge = ObsidianBridge()
            result.obsidian_sink = ObsidianSink(
                bridge=result.obsidian_bridge,
                config=obsidian_config,
            )
            result.notes.append(
                f"obsidian_bridge mode={result.obsidian_bridge.mode.value} "
                f"reachable={result.obsidian_bridge.health_check()}"
            )
            _attach_sink_to_loop(loop, result.obsidian_sink, result.notes)
        except Exception as e:
            result.notes.append(f"obsidian wiring failed: {e}")

    # ── 3. Neural pathway graph ─────────────────────────────────────────
    if enable_pathway_mapping:
        try:
            result.pathway_mapper = NeuralPathwayMapper()
            result.pathway_stats = result.pathway_mapper.write_to_vault(vault)
            result.notes.append(
                f"pathway_graph nodes={result.pathway_stats.get('node_count')} "
                f"edges={result.pathway_stats.get('edge_count')} "
                f"clusters={result.pathway_stats.get('cluster_count')}"
            )
        except Exception as e:
            result.notes.append(f"pathway mapping failed: {e}")

    # ── 4. Audit ────────────────────────────────────────────────────────
    if run_audit:
        try:
            trail = IntegrationAuditTrail()
            audit = trail.run(
                emit_to_sink=(
                    result.obsidian_sink.on_audit if result.obsidian_sink else None
                )
            )
            result.audit = audit
            result.notes.append(
                f"audit {audit.audit_id}: {audit.passed}/{audit.total} passed"
            )
            try:
                vault.ingest(
                    topic="integration.audit.snapshot",
                    payload=audit.to_dict(),
                    category="integration_audit",
                )
            except Exception:
                pass
        except Exception as e:
            result.notes.append(f"audit run failed: {e}")

    return result


# ─────────────────────────────────────────────────────────────────────────────
# Loop wiring helpers
# ─────────────────────────────────────────────────────────────────────────────


def _swap_voice_adapters(loop: Any, adapter: Any, notes: List[str]) -> None:
    """
    Point every VaultVoice on the loop's voice engine at the given adapter,
    and rewire the SelfDialogueEngine (and any attached ThoughtStreamLoop)
    too. No-op if the loop has no voice engine.
    """
    if loop is None:
        notes.append("voice_adapter_swap skipped: no loop provided")
        return
    voice_engine = getattr(loop, "voice_engine", None)
    if voice_engine is None:
        notes.append("voice_adapter_swap skipped: loop has no voice_engine")
        return
    try:
        voices = getattr(voice_engine, "voices", {}) or {}
        for name, voice in voices.items():
            try:
                voice.adapter = adapter
            except Exception:
                pass
        notes.append(
            f"voice_adapter_swap: {len(voices)} voices now on OllamaLLMAdapter"
        )
    except Exception as e:
        notes.append(f"voice_adapter_swap failed: {e}")


def _attach_sink_to_loop(loop: Any, sink: Any, notes: List[str]) -> None:
    """
    Subscribe the sink to the loop's utterance + tick events.

    Strategy:
      • ThoughtStreamLoop / SelfDialogueEngine both accept an
        `on_utterance` hook — we set it here.
      • AureonSelfFeedbackLoop doesn't have an on_tick callback by
        design; we wrap its `tick()` method to fire the sink after
        each cycle (once per loop, guarded by _WIRED_LOOPS).
    """
    if loop is None:
        notes.append("sink_attach skipped: no loop provided")
        return

    # Utterance hook
    voice_engine = getattr(loop, "voice_engine", None)
    if voice_engine is not None and hasattr(voice_engine, "converse"):
        original_converse = voice_engine.converse

        def wrapped_converse(*args, **kwargs):
            u = original_converse(*args, **kwargs)
            try:
                sink.on_utterance(u)
            except Exception:
                pass
            return u

        if not getattr(voice_engine, "_aureon_sink_wrapped", False):
            voice_engine.converse = wrapped_converse  # type: ignore[method-assign]
            voice_engine._aureon_sink_wrapped = True
            notes.append("sink_attach: voice_engine.converse wrapped")
        else:
            notes.append("sink_attach: voice_engine already wrapped")

    # Tick hook
    loop_id = getattr(loop, "loop_id", None)
    if loop_id and loop_id in _WIRED_LOOPS:
        notes.append(f"sink_attach: loop {loop_id} already wired")
        return

    if hasattr(loop, "tick"):
        original_tick = loop.tick

        def wrapped_tick(*args, **kwargs):
            result = original_tick(*args, **kwargs)
            try:
                sink.on_tick(result)
            except Exception:
                pass
            return result

        loop.tick = wrapped_tick  # type: ignore[method-assign]
        if loop_id:
            _WIRED_LOOPS.add(loop_id)
        notes.append(f"sink_attach: loop.tick wrapped for {loop_id or 'unknown'}")

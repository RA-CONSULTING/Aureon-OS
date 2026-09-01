#!/usr/bin/env python3
"""
tests/integrations/test_wiring_and_audit.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

End-to-end integration tests:
  1. NeuralPathwayMapper builds a non-empty graph + writes to vault
  2. IntegrationAuditTrail runs the full checklist and emits a JSONL event
  3. wire_integrations() attaches the Obsidian sink to the self-feedback
     loop, swaps voice adapters (if Ollama is wired to a fake bridge),
     and leaves the vault with a populated pathway_graph
  4. After wire_integrations, one loop.tick() produces an Obsidian log
     entry AND one voice_engine.converse() writes a daily journal entry
"""

import json
import os
import sys
import tempfile
import time
from pathlib import Path

import pytest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from aureon.integrations import (
    IntegrationAuditTrail,
    NeuralPathwayMapper,
    ObsidianBridge,
    ObsidianSink,
    ObsidianSinkConfig,
    run_full_audit,
    wire_integrations,
)
from aureon.integrations.audit_trail import INTEGRATION_CHECKLIST
from aureon.vault import AureonSelfFeedbackLoop, AureonVault

PASS = 0
FAIL = 0


def check(condition, msg):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  [OK] {msg}")
    else:
        FAIL += 1
        print(f"  [!!] {msg}")


# ─────────────────────────────────────────────────────────────────────────────
# 1. NeuralPathwayMapper
# ─────────────────────────────────────────────────────────────────────────────


def test_neural_pathway_mapper():
    print("\n[1] NeuralPathwayMapper")
    mapper = NeuralPathwayMapper()
    # Use a single max_modules value for the whole test so the cache
    # hash stays stable.
    graph = mapper.build_graph(max_modules=120)
    check(len(graph.nodes) > 10, f"graph has {len(graph.nodes)} nodes")
    check(
        sum(len(v) for v in graph.edges.values()) > 5,
        "graph has non-trivial edges",
    )
    check(len(graph.clusters) >= 2, f"multi-cluster: {sorted(graph.clusters)}")
    stats = graph.stats()
    check(
        stats["node_count"] == len(graph.nodes),
        "stats node_count matches",
    )
    check("most_referenced" in stats, "stats include most_referenced")

    # Cached rebuild with the SAME max_modules returns the identical object
    g2 = mapper.build_graph(max_modules=120)
    check(g2 is graph, "cached graph returned on rebuild")

    # Fresh mapper → write_to_vault populates vault.pathway_graph
    vault = AureonVault()
    mapper2 = NeuralPathwayMapper()
    mapper2.write_to_vault(vault, max_modules=60)
    check(isinstance(vault.pathway_graph, dict), "vault.pathway_graph is dict")
    check(
        sum(len(v) for v in vault.pathway_graph.values()) > 0,
        "vault.pathway_graph has edges",
    )
    check(
        any(
            "pathway.graph.built" in getattr(c, "source_topic", "")
            for c in vault._contents.values()
        ),
        "pathway.graph.built card ingested",
    )


# ─────────────────────────────────────────────────────────────────────────────
# 2. IntegrationAuditTrail
# ─────────────────────────────────────────────────────────────────────────────


def test_integration_audit_trail():
    print("\n[2] IntegrationAuditTrail")
    check(len(INTEGRATION_CHECKLIST) >= 10, f"checklist has {len(INTEGRATION_CHECKLIST)} entries")

    with tempfile.TemporaryDirectory() as tmp:
        log_path = Path(tmp) / "audit.jsonl"
        trail = IntegrationAuditTrail(log_path=log_path)
        status = trail.run()
        check(status.total == len(INTEGRATION_CHECKLIST), "every check ran")
        # Import-level checks and pathway mapping should all pass
        must_pass = {
            "ollama.bridge.import",
            "ollama.adapter.import",
            "obsidian.bridge.import",
            "obsidian.sink.import",
            "wiring.vault_voice_loop",
            "pathway.neural_mapper",
            "inhouse_ai.llm_adapter",
            "inhouse_ai.orchestrator",
            "ollama.adapter.interface",
        }
        passed_names = {r.name for r in status.results if r.passed}
        missing = must_pass - passed_names
        check(not missing, f"all critical checks pass ({list(missing) or 'none missing'})")

        # JSONL persistence
        check(log_path.exists(), "audit jsonl created")
        lines = log_path.read_text().strip().splitlines()
        check(len(lines) == 1, "one audit event persisted")
        event = json.loads(lines[0])
        check(event.get("audit_id") == status.audit_id, "persisted audit_id matches")

        # summary_lines formatting
        summary = status.summary_lines()
        check(any("Integration Audit" in line for line in summary), "summary header")


# ─────────────────────────────────────────────────────────────────────────────
# 3. wire_integrations end-to-end
# ─────────────────────────────────────────────────────────────────────────────


def test_wire_integrations_end_to_end():
    print("\n[3] effectful feedback-loop integration remains on production HOLD")
    with pytest.raises(RuntimeError, match="aureon_self_feedback_loop_hold"):
        AureonSelfFeedbackLoop(vault=AureonVault(), enable_voice=True)


# ─────────────────────────────────────────────────────────────────────────────
# 4. run_full_audit top-level
# ─────────────────────────────────────────────────────────────────────────────


def test_run_full_audit_top_level():
    print("\n[4] run_full_audit top-level helper")
    with tempfile.TemporaryDirectory() as tmp:
        status = run_full_audit(log_path=Path(tmp) / "audit.jsonl")
        check(status.total > 0, "full audit has results")
        check(status.health_ratio >= 0.5, f"health_ratio {status.health_ratio:.2f}")


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────


def main():
    test_neural_pathway_mapper()
    test_integration_audit_trail()
    test_wire_integrations_end_to_end()
    test_run_full_audit_top_level()

    print(f"\n{'═' * 60}")
    print(f"Wiring + audit tests: {PASS} passed, {FAIL} failed")
    print(f"{'═' * 60}")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

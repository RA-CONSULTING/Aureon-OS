from aureon.autonomous.aureon_antarctic_research_unity_bridge import build_report
from aureon.wisdom.antarctic_research_bridge import (
    apply_to_lyra_summary,
    apply_to_seer_summary,
    build_research_context,
)


def test_research_context_maps_seer_and_lyra_without_execution_command():
    ctx = build_research_context()

    assert ctx["status"] == "research_bridge_ready"
    assert ctx["shared_map"]["execution_command"] == "none"
    assert ctx["shared_map"]["influence"] == "context_modifier_only"
    assert ctx["seer"]["role"] == "seer_reads_stars"
    assert ctx["lyra"]["role"] == "lyra_reads_emotions"
    assert 0.90 <= ctx["seer"]["confidence_modifier"] <= 1.10
    assert 0.90 <= ctx["lyra"]["confidence_modifier"] <= 1.10


def test_wrappers_attach_context_to_existing_summaries():
    seer_summary = apply_to_seer_summary({"grade": "FOG", "unified_score": 0.5})
    lyra_summary = apply_to_lyra_summary(
        {"action": "HOLD", "emotional_frequency": 432, "emotional_zone": "BALANCE"}
    )

    assert seer_summary["antarctic_research"]["seer"]["role"] == "seer_reads_stars"
    assert lyra_summary["antarctic_research"]["lyra"]["role"] == "lyra_reads_emotions"
    assert lyra_summary["antarctic_research"]["lyra"]["current_emotional_frequency"] == 432


def test_unity_report_is_context_only_not_blocker_gate():
    report = build_report()

    assert report["status"] == "antarctic_research_context_wired"
    assert report["mode"] == "context_signal_only"
    assert report["summary"]["no_new_blocker_gates"] is True
    assert report["summary"]["execution_command_added"] is False
    assert all(row["authority"] == "context_signal_only" for row in report["wiring_rows"])

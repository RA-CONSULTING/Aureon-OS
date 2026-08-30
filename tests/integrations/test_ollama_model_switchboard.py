from __future__ import annotations

from dataclasses import replace
from types import SimpleNamespace

from aureon.integrations.ollama.model_switchboard import (
    HNCModelRoutingReceipt,
    OllamaModelSwitchboard,
    validate_hnc_model_routing_receipt,
)


class _Bridge:
    base_url = "https://ollama.com"
    chat_model = "general-model"
    embed_model = "embed-model"
    keep_alive = "5m"
    timeout_s = 2.0
    api_key = "not-reported"

    def __init__(self, models):
        self.models = models
        self.calls = 0

    def snapshot(self):
        self.calls += 1
        return {"reachable": True, "models": self.models}


def test_switchboard_routes_live_catalog_to_distinct_nerve_lanes(monkeypatch):
    bridge = _Bridge(
        [
            "deepseek-v4-flash:preview",
            "nemotron-3-ultra",
            "kimi-k2.7-code",
            "general-model",
        ]
    )
    switchboard = OllamaModelSwitchboard(bridge=bridge, catalog_ttl_s=60)

    assert switchboard.select("coding").model == "kimi-k2.7-code"
    assert switchboard.select("architecture").model == "nemotron-3-ultra"
    assert switchboard.select("fast").model == "deepseek-v4-flash:preview"
    assert switchboard.select("general").model != "kimi-k2.7-code"
    assert bridge.calls == 1

    ranked = switchboard.rank("general", limit=3, exclude={"general-model"})
    assert len(ranked) == 3
    assert all(item.model != "general-model" for item in ranked)

    monkeypatch.setenv("AUREON_OLLAMA_CODING_MODEL", "general-model")
    override = switchboard.select("coding")
    assert override.model == "general-model"
    assert override.source == "lane_override_in_live_catalog"


def test_switchboard_ignores_stale_override_not_present_in_catalog(monkeypatch):
    monkeypatch.setenv("AUREON_OLLAMA_ARCHITECTURE_MODEL", "removed-model")
    switchboard = OllamaModelSwitchboard(bridge=_Bridge(["nemotron-3-ultra", "general-model"]))

    selection = switchboard.select("architecture")

    assert selection.model == "nemotron-3-ultra"
    assert selection.source == "ranked_live_catalog"
    assert selection.catalog_size == 2


def test_switchboard_fails_over_from_listed_but_unusable_model(monkeypatch):
    switchboard = OllamaModelSwitchboard(
        bridge=_Bridge(["kimi-k3", "mistral-large-3:675b", "general-model"])
    )
    monkeypatch.setattr(
        switchboard,
        "_probe_selection",
        lambda selection, force=False: (
            selection.model == "mistral-large-3:675b",
            "live_probe_passed" if selection.model == "mistral-large-3:675b" else "payment_required",
        ),
    )

    selection = switchboard.working_selection("general")

    assert selection.model == "mistral-large-3:675b"
    assert selection.source.startswith("live_probe_passed:")


def _field(gamma: float = 0.9):
    return SimpleNamespace(
        available=True,
        receipt_id="hnc:live_field:test-route",
        source_timestamp=1_787_000_000.0,
        coherence_gamma=gamma,
        consciousness_psi=0.91,
        lambda_t=2.618,
    )


def test_hnc_routes_each_nerve_with_a_distinct_hash_bound_receipt(monkeypatch):
    switchboard = OllamaModelSwitchboard(
        bridge=_Bridge(["kimi-k2.7-code", "gpt-oss:20b", "deepseek-v4-flash:preview"]),
        field_reader=lambda: _field(0.91),
        clock=lambda: 1_787_000_001.0,
    )
    monkeypatch.setattr(
        switchboard,
        "_probe_selection",
        lambda selection, force=False: (True, "live_probe_passed"),
    )

    agent, agent_receipt = switchboard.route_nerve("coding", nerve_id="agent:Test Pilot")
    process, process_receipt = switchboard.route_nerve(
        "coding",
        nerve_id="process:internal_review",
    )

    assert agent.model in switchboard.refresh()
    assert process.model in switchboard.refresh()
    assert agent.source.startswith("live_probe_passed:hnc_active:")
    assert validate_hnc_model_routing_receipt(agent_receipt)
    assert validate_hnc_model_routing_receipt(process_receipt)
    assert agent_receipt.hnc_receipt_id == process_receipt.hnc_receipt_id
    assert agent_receipt.receipt_id != process_receipt.receipt_id
    assert agent_receipt.provider_mode == "ollama_cloud_primary"
    assert agent_receipt.action_eligible is False
    assert agent_receipt.economic_eligible is False


def test_hnc_organizing_band_avoids_oversized_model_when_fast_candidate_exists(monkeypatch):
    switchboard = OllamaModelSwitchboard(
        bridge=_Bridge(["mistral-large-3:675b", "gpt-oss:20b"]),
        field_reader=lambda: _field(0.7),
        clock=lambda: 1_787_000_001.0,
    )
    monkeypatch.setattr(
        switchboard,
        "_probe_selection",
        lambda selection, force=False: (True, "live_probe_passed"),
    )

    selection, receipt = switchboard.route_nerve(
        "architecture",
        nerve_id="agent:Risk Governor",
    )

    assert selection.model == "gpt-oss:20b"
    assert receipt.coherence_band == "organizing"
    assert validate_hnc_model_routing_receipt(receipt)


def test_hnc_route_holds_numeric_free_when_canonical_field_is_missing():
    switchboard = OllamaModelSwitchboard(
        bridge=_Bridge(["kimi-k2.7-code"]),
        field_reader=lambda: SimpleNamespace(available=False),
        clock=lambda: 1_787_000_001.0,
    )

    _selection, receipt = switchboard.route_nerve("coding", nerve_id="agent:Builder")

    assert receipt.decision == "HOLD"
    assert receipt.reason == "fresh_canonical_hnc_field_required"
    assert receipt.model == ""
    assert receipt.coherence_gamma is None
    assert receipt.hnc_source_timestamp is None
    assert validate_hnc_model_routing_receipt(receipt)


def test_hnc_route_receipt_rejects_causal_tampering(monkeypatch):
    switchboard = OllamaModelSwitchboard(
        bridge=_Bridge(["kimi-k2.7-code"]),
        field_reader=_field,
        clock=lambda: 1_787_000_001.0,
    )
    monkeypatch.setattr(
        switchboard,
        "_probe_selection",
        lambda selection, force=False: (True, "live_probe_passed"),
    )
    _selection, receipt = switchboard.route_nerve("coding", nerve_id="agent:Builder")

    assert isinstance(receipt, HNCModelRoutingReceipt)
    assert validate_hnc_model_routing_receipt(receipt)
    assert not validate_hnc_model_routing_receipt(replace(receipt, model="other"))
    assert not validate_hnc_model_routing_receipt(replace(receipt, action_eligible=True))


def test_one_captured_hnc_moment_is_shared_across_a_nerve_generation(monkeypatch):
    calls = 0

    def changing_field():
        nonlocal calls
        calls += 1
        return _field(0.9 if calls == 1 else 0.7)

    switchboard = OllamaModelSwitchboard(
        bridge=_Bridge(["kimi-k2.7-code", "gpt-oss:20b"]),
        field_reader=changing_field,
        clock=lambda: 1_787_000_001.0,
    )
    monkeypatch.setattr(
        switchboard,
        "_probe_selection",
        lambda selection, force=False: (True, "live_probe_passed"),
    )
    generation_field = switchboard.capture_hnc_field()

    _first, first_receipt = switchboard.route_nerve(
        "coding",
        nerve_id="agent:Builder",
        hnc_field=generation_field,
    )
    _second, second_receipt = switchboard.route_nerve(
        "architecture",
        nerve_id="process:review",
        hnc_field=generation_field,
    )

    assert calls == 1
    assert first_receipt.hnc_receipt_id == second_receipt.hnc_receipt_id
    assert first_receipt.coherence_gamma == second_receipt.coherence_gamma == 0.9
    assert first_receipt.coherence_band == second_receipt.coherence_band == "active"

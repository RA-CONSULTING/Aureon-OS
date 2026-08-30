from aureon.simulation.aureon_multiverse import PingPongEngine, PingPongPosition


def test_simulation_ping_pong_cannot_submit_or_mutate(monkeypatch):
    import aureon.simulation.aureon_multiverse as multiverse

    def no_network(*args, **kwargs):
        raise AssertionError("network access is forbidden in simulation")

    monkeypatch.setattr(multiverse.requests, "get", no_network)
    monkeypatch.setattr(multiverse.requests, "post", no_network)
    engine = PingPongEngine()

    receipt = engine.place_order("ETHBTC", "BUY", 1.0)
    assert receipt["status"] == "simulation_no_action"
    assert receipt["truth_status"] == "simulation_control"
    assert receipt["provider_id"] is None
    assert receipt["order_id"] is None
    assert receipt["fill_id"] is None
    assert receipt["generated_values"] is True
    assert receipt["action_enabled"] is False
    assert receipt["accounting_enabled"] is False
    assert receipt["learning_enabled"] is False
    assert receipt["eligible_for_external_action"] is False
    assert receipt["eligible_for_accounting"] is False
    assert receipt["eligible_for_learning"] is False

    assert engine.ping("ETHBTC", 2.0, 1.0) is False
    assert engine.positions == {}
    engine.positions["ETHBTC"] = PingPongPosition("ETHBTC", "PING", 1.0, 2.0, 0.0)
    assert engine.pong("ETHBTC", 2.0) is None
    assert "ETHBTC" in engine.positions
    assert engine.total_bounces == 0

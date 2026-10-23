import pytest

from harmonic_nexus import parse_ritual_spec, run_simulation


def summarise_nodes(nodes):
    return [
        (round(node.psi, 6), round(node.Gamma_local, 6), round(node.kappa, 6), round(node.C, 6))
        for node in nodes
    ]


def test_run_simulation_is_deterministic_with_seed():
    events = [(0, [1], 0.05), (5, [2, 3], 0.04)]
    metrics_a, nodes_a = run_simulation(steps=12, seed=1234, ritual_events=events, verbose=False)
    metrics_b, nodes_b = run_simulation(steps=12, seed=1234, ritual_events=events, verbose=False)

    assert len(metrics_a) == len(metrics_b) == 12

    for ma, mb in zip(metrics_a, metrics_b):
        assert ma.keys() == mb.keys()
        for key in ("Gamma_global", "toroidal_flux", "nodes_mean_psi", "nodes_mean_kappa"):
            assert ma[key] == pytest.approx(mb[key])
        assert ma["containment"] == mb["containment"]

    assert summarise_nodes(nodes_a) == summarise_nodes(nodes_b)


def test_parse_ritual_spec_parses_defaults():
    step, nodes, strength = parse_ritual_spec("10:1,2,3")
    assert step == 10
    assert nodes == [1, 2, 3]
    assert strength == pytest.approx(0.03)


def test_parse_ritual_spec_with_strength():
    step, nodes, strength = parse_ritual_spec("1:4:0.08")
    assert step == 1
    assert nodes == [4]
    assert strength == pytest.approx(0.08)


def test_parse_ritual_spec_invalid():
    with pytest.raises(ValueError):
        parse_ritual_spec("nope")

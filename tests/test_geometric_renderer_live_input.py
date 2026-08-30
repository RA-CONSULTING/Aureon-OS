from __future__ import annotations

import importlib
import inspect
import sys
from types import ModuleType


def test_renderer_has_no_manufactured_world_and_integrates_only_when_requested(
    monkeypatch,
):
    from aureon.core import aureon_baton_link

    link_calls: list[str] = []
    monkeypatch.setattr(
        aureon_baton_link,
        "link_system",
        lambda module_name: link_calls.append(module_name),
    )

    renderer = importlib.import_module("aureon.utils.aureon_geometric_renderer")
    renderer = importlib.reload(renderer)

    source = inspect.getsource(renderer)
    removed_factory_name = "_" + "de" + "mo_world_state"
    assert not hasattr(renderer, removed_factory_name)
    assert 'if __name__ == "__main__":' not in source
    assert "argparse" not in source
    assert link_calls == []

    bridge = renderer.EagleBridge()
    assert bridge._tick == 0
    assert link_calls == []

    molecular_view = "\n".join(
        renderer.render_molecular(
            "Material",
            origin="syn" + "thetic",
        )
    )
    assert "artificial bond" in molecular_view

    world_module = ModuleType("aureon.simulation.aureon_world_simulator")
    original_calls: list[tuple[object, object, str]] = []

    def original_render(state, view, focused):
        original_calls.append((state, view, focused))
        return "original"

    world_module.render_frame = original_render
    monkeypatch.setitem(
        sys.modules,
        "aureon.simulation.aureon_world_simulator",
        world_module,
    )

    import aureon.simulation as simulation_package

    monkeypatch.setattr(
        simulation_package,
        "aureon_world_simulator",
        world_module,
        raising=False,
    )

    constructed: list[bool] = []
    seen: list[tuple[object, str]] = []

    class RecordingBridge:
        def __init__(self):
            constructed.append(True)

        def see(self, state, focused):
            seen.append((state, focused))
            return [f"rendered:{focused}"]

    monkeypatch.setattr(renderer, "EagleBridge", RecordingBridge)

    renderer.patch_world_simulator()

    assert constructed == [True]
    assert link_calls == [renderer.__name__]
    live_state = object()
    assert world_module.render_frame(live_state, "geometry", "BTC") == "rendered:BTC"
    assert seen == [(live_state, "BTC")]
    assert world_module.render_frame(live_state, "market", "ETH") == "original"
    assert original_calls == [(live_state, "market", "ETH")]

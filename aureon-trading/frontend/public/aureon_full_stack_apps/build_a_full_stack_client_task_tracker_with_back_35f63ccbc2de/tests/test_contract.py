from pathlib import Path
import importlib.util


ROOT = Path(__file__).resolve().parents[1]
SERVER = ROOT / "backend" / "server.py"
spec = importlib.util.spec_from_file_location("generated_full_stack_server", SERVER)
module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(module)


def test_health_and_crud_contract():
    state = module.create_initial_state()
    assert module.health_check(state)["ok"] is True
    assert len(module.list_items(state)) >= 3
    item = module.create_item(state, {"title": "QA contract", "owner": "Test Pilot"})
    assert item["id"].startswith("task-")
    assert module.dashboard_summary(state)["total"] >= 4

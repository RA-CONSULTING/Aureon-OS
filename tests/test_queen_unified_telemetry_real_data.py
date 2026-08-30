import ast
import logging
import threading
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace


def _load_start_method_without_module_side_effects():
    source_path = (
        Path(__file__).resolve().parents[1]
        / 'aureon'
        / 'autonomous'
        / 'aureon_queen_unified_startup.py'
    )
    tree = ast.parse(source_path.read_text(encoding='utf-8'))
    class_node = next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == 'QueenUnifiedStartup'
    )
    method_node = next(
        node
        for node in class_node.body
        if isinstance(node, ast.FunctionDef) and node.name == 'start_telemetry_stream'
    )
    isolated = ast.Module(body=[method_node], type_ignores=[])
    ast.fix_missing_locations(isolated)
    namespace = {
        'datetime': datetime,
        'logger': logging.getLogger('queen-telemetry-test'),
        'threading': threading,
        'timezone': timezone,
    }
    exec(compile(isolated, str(source_path), 'exec'), namespace)
    return namespace['start_telemetry_stream']


def test_telemetry_emits_only_observed_runtime_heartbeat():
    start_telemetry_stream = _load_start_method_without_module_side_effects()
    stop_event = threading.Event()
    emitted = []
    startup = SimpleNamespace(
        running_threads={},
        stop_event=stop_event,
        dry_run=True,
        state=SimpleNamespace(
            queen_active=False,
            systems_running={
                'thought_bus': SimpleNamespace(status='running'),
                'provider_feed': SimpleNamespace(status='error'),
            },
        ),
    )

    def emit(topic, payload):
        emitted.append((topic, payload))
        stop_event.set()

    startup._emit_telemetry = emit
    start_telemetry_stream(startup)
    startup.running_threads['telemetry'].join(timeout=2)

    assert [topic for topic, _ in emitted] == ['queen.heartbeat']
    payload = emitted[0][1]
    assert payload['systems_active'] == 1
    assert payload['systems'] == {
        'thought_bus': 'running',
        'provider_feed': 'error',
    }
    assert payload['truth_status'] == 'real_derived'
    assert payload['source_id'] == 'queen_unified_startup:runtime_state'
    assert payload['generated_values'] is False
    assert 'queen_signal' not in payload

import ast
import asyncio
import threading

import pytest

from aureon.harmonic.aureon_harmonic_liquid_aluminium import (
    HarmonicLiquidAluminiumField,
    harmonic_streaming_runtime,
)


OWNER_FILES = (
    "aureon/data_feeds/unified_ws_feed.py",
    "aureon/queen/queen_sentience_integration.py",
    "aureon/queen/queen_quantum_frog.py",
    "aureon/utils/aureon_queen_hive_mind.py",
    "aureon/exchanges/binance_ws_client.py",
    "aureon/trading/unified_kill_chain.py",
    "aureon/bots/orca_complete_kill_cycle.py",
)

DECORATED_RUNTIME_METHODS = {
    "aureon/queen/queen_sentience_integration.py": {
        "QueenSentienceEngine": {"start_sentience_loop"},
    },
    "aureon/queen/queen_quantum_frog.py": {
        "OrcaKillCycle": {"hunt_and_kill", "run_autonomous", "run_autonomous_warroom"},
    },
    "aureon/trading/unified_kill_chain.py": {
        "UnifiedKillChain": {"run_loop"},
    },
    "aureon/bots/orca_complete_kill_cycle.py": {
        "OrcaKillCycle": {"hunt_and_kill", "run_autonomous", "run_autonomous_warroom"},
    },
}


def _constructor_start_calls(path):
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    calls = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) or node.name != "__init__":
            continue
        for child in ast.walk(node):
            if (
                isinstance(child, ast.Call)
                and isinstance(child.func, ast.Attribute)
                and child.func.attr == "start_streaming"
            ):
                calls.append(child.lineno)
    return calls


def test_no_production_owner_starts_harmonic_streaming_in_constructor():
    repo = __file__
    from pathlib import Path

    root = Path(repo).resolve().parents[1]
    offenders = {
        relative: _constructor_start_calls(root / relative)
        for relative in OWNER_FILES
        if _constructor_start_calls(root / relative)
    }
    assert offenders == {}


def test_blocking_runtime_owners_declare_symmetric_harmonic_lifecycle():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    missing = []
    for relative, classes in DECORATED_RUNTIME_METHODS.items():
        tree = ast.parse((root / relative).read_text(encoding="utf-8"), filename=relative)
        class_nodes = {
            node.name: node
            for node in tree.body
            if isinstance(node, ast.ClassDef)
        }
        for class_name, methods in classes.items():
            class_node = class_nodes[class_name]
            method_nodes = {
                node.name: node
                for node in class_node.body
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            }
            for method_name in methods:
                decorators = {
                    decorator.id
                    for decorator in method_nodes[method_name].decorator_list
                    if isinstance(decorator, ast.Name)
                }
                if "harmonic_streaming_runtime" not in decorators:
                    missing.append(f"{relative}:{class_name}.{method_name}")
    assert missing == []


def test_field_constructor_is_inert_and_explicit_stop_joins(monkeypatch):
    monkeypatch.delenv("AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS", raising=False)
    before = {thread.ident for thread in threading.enumerate()}

    field = HarmonicLiquidAluminiumField(stream_interval_ms=5)

    assert field.running is False
    assert field._stream_thread is None
    assert {thread.ident for thread in threading.enumerate()} == before

    published = threading.Event()
    monkeypatch.setattr(field, "capture_snapshot", lambda: object())
    monkeypatch.setattr(field, "publish_snapshot", lambda snapshot: published.set())

    assert field.start_streaming() is True
    worker = field._stream_thread
    assert worker is not None
    assert worker.name == "HarmonicLiquidAluminiumField"
    assert published.wait(0.5)
    assert field.start_streaming() is False

    assert field.stop_streaming(timeout=0.5) is True
    assert worker.is_alive() is False
    assert field._stream_thread is None
    assert field.running is False


class _RecordingField:
    def __init__(self, *args, **kwargs):
        self.start_calls = 0
        self.stop_calls = 0
        self.running = False

    def start_streaming(self):
        self.start_calls += 1
        if self.running:
            return False
        self.running = True
        return True

    def stop_streaming(self, timeout=2.0):
        self.stop_calls += 1
        self.running = False
        return True


def test_runtime_wrapper_stops_on_success_and_error():
    class Owner:
        def __init__(self):
            self.harmonic_field = _RecordingField()

        @harmonic_streaming_runtime
        def run(self, fail=False):
            if fail:
                raise RuntimeError("runtime failed")
            return "ok"

    owner = Owner()
    assert owner.run() == "ok"
    assert (owner.harmonic_field.start_calls, owner.harmonic_field.stop_calls) == (1, 1)

    with pytest.raises(RuntimeError, match="runtime failed"):
        owner.run(fail=True)
    assert (owner.harmonic_field.start_calls, owner.harmonic_field.stop_calls) == (2, 2)


def test_async_runtime_wrapper_stops_on_cancellation():
    entered = asyncio.Event()

    class Owner:
        def __init__(self):
            self.harmonic_field = _RecordingField()

        @harmonic_streaming_runtime
        async def run(self):
            entered.set()
            await asyncio.Event().wait()

    async def scenario():
        owner = Owner()
        task = asyncio.create_task(owner.run())
        await entered.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        return owner

    owner = asyncio.run(scenario())
    assert (owner.harmonic_field.start_calls, owner.harmonic_field.stop_calls) == (1, 1)


def test_unified_feed_constructor_is_inert_and_start_stop_own_field(monkeypatch):
    import aureon.data_feeds.unified_ws_feed as module

    monkeypatch.setattr(module, "HARMONIC_LIQUID_ALUMINIUM_AVAILABLE", True)
    monkeypatch.setattr(module, "HarmonicLiquidAluminiumField", _RecordingField)
    monkeypatch.setattr(module, "HFT_ENGINE_AVAILABLE", False)

    feed = module.UnifiedWSFeed(
        enable_binance=False,
        enable_kraken=False,
        enable_capital=False,
        enable_coinbase=False,
        enable_coingecko=False,
    )
    assert feed.harmonic_field.start_calls == 0

    asyncio.run(feed.start(symbols=[], coingecko_ids=[]))
    assert feed.harmonic_field.start_calls == 1
    assert feed.harmonic_field.running is True

    asyncio.run(feed.stop())
    assert feed.harmonic_field.stop_calls == 1
    assert feed.harmonic_field.running is False


def test_binance_ws_constructor_is_inert_and_start_stop_own_field(monkeypatch):
    import aureon.exchanges.binance_ws_client as module

    monkeypatch.setattr(module, "websocket", object())
    monkeypatch.setattr(module, "HARMONIC_LIQUID_ALUMINIUM_AVAILABLE", True)
    monkeypatch.setattr(module, "HarmonicLiquidAluminiumField", _RecordingField)

    client = module.BinanceWebSocketClient()
    assert client.harmonic_field.start_calls == 0

    monkeypatch.setattr(client, "_connect", lambda: None)
    client.start(streams=[])
    assert client.harmonic_field.start_calls == 1
    assert client.harmonic_field.running is True

    client.stop()
    assert client.harmonic_field.stop_calls == 1
    assert client.harmonic_field.running is False

from __future__ import annotations

import importlib
import inspect
import threading

import pytest


@pytest.fixture(autouse=True)
def _audit_imports(monkeypatch):
    monkeypatch.setenv("AUREON_AUDIT_MODE", "1")
    monkeypatch.setenv("AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS", "1")
    monkeypatch.setenv("PYTHON_DOTENV_DISABLED", "1")


def _thread_named(name: str) -> bool:
    return any(thread.name == name and thread.is_alive() for thread in threading.enumerate())


def test_quantum_frog_import_does_not_start_health_server():
    module = importlib.import_module("aureon.queen.queen_quantum_frog")

    assert module._health_thread is None
    assert module._health_server is None
    assert not _thread_named("orca-health-server")


def test_quantum_frog_health_server_has_explicit_start_and_stop(monkeypatch):
    module = importlib.import_module("aureon.queen.queen_quantum_frog")
    module.stop_health_server()
    started = threading.Event()
    released = threading.Event()

    class InMemoryHealthServer:
        server_address = ("127.0.0.1", 43210)

        def __init__(self, address, handler):
            self.address = address
            self.handler = handler
            self.closed = False

        def serve_forever(self, poll_interval):
            started.set()
            released.wait(timeout=2.0)

        def shutdown(self):
            released.set()

        def server_close(self):
            self.closed = True
            released.set()

    monkeypatch.setattr(module, "_HealthServer", InMemoryHealthServer)
    try:
        assert module.start_health_server(port=0) is True
        assert started.wait(timeout=1.0)
        thread = module._health_thread
        assert thread is not None
        assert thread.name == "orca-health-server"
        assert thread.is_alive()
        server = module._health_server
        assert server.server_address[1] > 0
    finally:
        module.stop_health_server()

    assert server.closed is True
    assert module._health_thread is None
    assert module._health_server is None
    assert not _thread_named("orca-health-server")


def test_queen_constructor_contains_no_biometric_factory_or_start():
    module = importlib.import_module("aureon.utils.aureon_queen_hive_mind")
    constructor = inspect.getsource(module.QueenHiveMind.__init__)

    assert "get_temporal_biometric_link()" not in constructor
    assert "self.temporal_biometric_link.start()" not in constructor


def test_queen_explicit_biometric_lifecycle_owns_worker(monkeypatch):
    module = importlib.import_module("aureon.utils.aureon_queen_hive_mind")
    stop_event = threading.Event()

    class Link:
        def __init__(self):
            self.running = False
            self.ws_thread = None

        def start(self):
            self.running = True
            self.ws_thread = threading.Thread(
                target=stop_event.wait,
                name="test-biometric-worker",
            )
            self.ws_thread.start()

        def stop(self):
            self.running = False
            stop_event.set()

    link = Link()
    monkeypatch.setattr(module, "TEMPORAL_BIOMETRIC_AVAILABLE", True)
    monkeypatch.setattr(module, "get_temporal_biometric_link", lambda: link)
    monkeypatch.delenv("AUREON_AUDIT_MODE", raising=False)
    monkeypatch.delenv("AUREON_DISABLE_REAL_ORDERS", raising=False)
    monkeypatch.delenv("AUREON_DISABLE_LIVE_BACKGROUND_STARTUP", raising=False)

    queen = module.QueenHiveMind.__new__(module.QueenHiveMind)
    queen.temporal_biometric_link = None

    assert queen.start_temporal_biometric_link() is True
    worker = link.ws_thread
    assert worker is not None and worker.is_alive()
    assert queen.close_runtime_services(timeout=1.0) == {
        "temporal_biometric_link": True,
    }
    assert not worker.is_alive()
    assert queen.temporal_biometric_link is None


def test_queen_biometric_start_remains_inert_in_audit_mode(monkeypatch):
    module = importlib.import_module("aureon.utils.aureon_queen_hive_mind")
    factory_called = False

    def factory():
        nonlocal factory_called
        factory_called = True
        raise AssertionError("audit mode must not construct the provider")

    monkeypatch.setattr(module, "TEMPORAL_BIOMETRIC_AVAILABLE", True)
    monkeypatch.setattr(module, "get_temporal_biometric_link", factory)
    monkeypatch.setenv("AUREON_AUDIT_MODE", "1")

    queen = module.QueenHiveMind.__new__(module.QueenHiveMind)
    queen.temporal_biometric_link = None

    assert queen.start_temporal_biometric_link() is False
    assert factory_called is False


class _Response:
    status_code = 200


class _Session:
    def __init__(self, *, block: bool = False):
        self.headers = {}
        self.get_calls = 0
        self.closed = False
        self.block = block
        self.started = threading.Event()
        self.release = threading.Event()

    def get(self, url, timeout):
        self.get_calls += 1
        self.started.set()
        if self.block:
            self.release.wait(timeout=2.0)
        return _Response()

    def close(self):
        self.closed = True
        self.release.set()


def _configure_alpaca(monkeypatch, module, session, *, dry_run: bool, credentials: bool):
    monkeypatch.setattr(module.requests, "Session", lambda: session)
    monkeypatch.setenv("ALPACA_DRY_RUN", "true" if dry_run else "false")
    monkeypatch.setenv("ALPACA_API_KEY", "test-key" if credentials else "")
    monkeypatch.setenv("ALPACA_SECRET_KEY", "test-secret" if credentials else "")
    monkeypatch.setenv("ALPACA_API_SECRET", "")
    monkeypatch.setenv("ALPACA_SECRET", "")
    monkeypatch.delenv("PROMETHEUS_METRICS_PORT", raising=False)


def test_alpaca_constructor_with_credentials_performs_no_probe(monkeypatch):
    module = importlib.import_module("aureon.exchanges.alpaca_client")
    session = _Session()
    _configure_alpaca(monkeypatch, module, session, dry_run=False, credentials=True)

    client = module.AlpacaClient()
    try:
        assert session.get_calls == 0
        assert client._auth_probe_thread is None
        assert not _thread_named("alpaca-auth-probe")
        assert client.auth_verified is False
    finally:
        client.close()


def test_alpaca_dry_run_and_credential_free_start_are_inert(monkeypatch):
    module = importlib.import_module("aureon.exchanges.alpaca_client")

    dry_session = _Session()
    _configure_alpaca(monkeypatch, module, dry_session, dry_run=True, credentials=True)
    dry_client = module.AlpacaClient()
    assert dry_client.start() is False
    assert dry_session.get_calls == 0
    assert dry_client.close()

    empty_session = _Session()
    _configure_alpaca(monkeypatch, module, empty_session, dry_run=False, credentials=False)
    empty_client = module.AlpacaClient()
    assert empty_client.start() is False
    assert empty_session.get_calls == 0
    assert empty_client.close()


def test_alpaca_explicit_start_and_close_own_auth_probe(monkeypatch):
    module = importlib.import_module("aureon.exchanges.alpaca_client")
    session = _Session(block=True)
    _configure_alpaca(monkeypatch, module, session, dry_run=False, credentials=True)
    client = module.AlpacaClient()

    assert client.start() is True
    assert session.started.wait(timeout=1.0)
    worker = client._auth_probe_thread
    assert worker is not None
    assert worker.name == "alpaca-auth-probe"
    assert worker.is_alive()

    assert client.close(timeout=1.0) is True
    assert session.closed is True
    assert not worker.is_alive()
    assert not _thread_named("alpaca-auth-probe")

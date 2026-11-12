import asyncio
import os

os.environ.setdefault("AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS", "1")

import aureon.autonomous.aureon_mind_thought_action_hub as hub_mod
from aureon.autonomous.aureon_mind_thought_action_hub import MindThoughtActionHub


def test_default_bind_is_loopback(monkeypatch):
    monkeypatch.delenv("AUREON_MIND_HUB_HOST", raising=False)
    assert hub_mod._bind_host() == "127.0.0.1"


def test_blank_override_falls_back_to_loopback(monkeypatch):
    monkeypatch.setenv("AUREON_MIND_HUB_HOST", "   ")
    assert hub_mod._bind_host() == "127.0.0.1"


def test_explicit_override_is_used(monkeypatch):
    monkeypatch.setenv("AUREON_MIND_HUB_HOST", "0.0.0.0")
    assert hub_mod._bind_host() == "0.0.0.0"


def test_start_binds_the_chosen_host(monkeypatch):
    monkeypatch.delenv("AUREON_MIND_HUB_HOST", raising=False)
    seen = {}

    class FakeRunner:
        def __init__(self, app):
            pass

        async def setup(self):
            pass

    class FakeSite:
        def __init__(self, runner, host, port):
            seen["host"], seen["port"] = host, port

        async def start(self):
            pass

    async def idle(self):
        return None

    monkeypatch.setattr(hub_mod.web, "AppRunner", FakeRunner)
    monkeypatch.setattr(hub_mod.web, "TCPSite", FakeSite)
    for name in ("goal_pursuit_loop", "_init_systems_async", "live_stats_updater"):
        monkeypatch.setattr(MindThoughtActionHub, name, idle)
    monkeypatch.setattr(MindThoughtActionHub, "_init_systems", lambda self: None)

    async def run():
        hub = MindThoughtActionHub(port=13002)
        await hub.start()
        await asyncio.sleep(0)

    asyncio.run(run())
    assert seen == {"host": "127.0.0.1", "port": 13002}


def test_no_wildcard_bind_left_in_source():
    src = open(hub_mod.__file__, encoding="utf-8").read()
    assert "TCPSite(runner, '0.0.0.0'" not in src
    assert 'TCPSite(runner, "0.0.0.0"' not in src

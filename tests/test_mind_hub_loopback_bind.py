"""The mind hub binds loopback unless told otherwise. No network, no real bind."""
from __future__ import annotations

import asyncio
import os

import pytest

os.environ.setdefault("AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS", "1")

import aureon.autonomous.aureon_mind_thought_action_hub as hub_mod


class _Site:
    seen: list[tuple[str, int]] = []

    def __init__(self, runner, host, port):
        _Site.seen.append((host, port))

    async def start(self):
        return None


def _bound(monkeypatch, **kwargs):
    _Site.seen = []
    monkeypatch.setattr(hub_mod.web, "TCPSite", _Site)

    async def idle(self):
        return None

    for name in ("goal_pursuit_loop", "_init_systems_async", "live_stats_updater"):
        if hasattr(hub_mod.MindThoughtActionHub, name):
            monkeypatch.setattr(hub_mod.MindThoughtActionHub, name, idle)

    async def run():
        hub = hub_mod.MindThoughtActionHub(**kwargs)
        await hub.start()
        await asyncio.sleep(0)

    asyncio.run(run())
    return _Site.seen[-1]


def test_default_bind_is_loopback(monkeypatch):
    assert _bound(monkeypatch) == ("127.0.0.1", 13002)


def test_explicit_host_is_used(monkeypatch):
    assert _bound(monkeypatch, port=23002, host="0.0.0.0") == ("0.0.0.0", 23002)


def test_env_defaults(monkeypatch):
    monkeypatch.delenv("AUREON_MIND_HUB_HOST", raising=False)
    monkeypatch.delenv("AUREON_MIND_HUB_PORT", raising=False)
    assert hub_mod.mind_hub_bind() == ("127.0.0.1", 13002)


def test_env_overrides(monkeypatch):
    monkeypatch.setenv("AUREON_MIND_HUB_HOST", "0.0.0.0")
    monkeypatch.setenv("AUREON_MIND_HUB_PORT", "23002")
    assert hub_mod.mind_hub_bind() == ("0.0.0.0", 23002)


@pytest.mark.parametrize("bad", ["abc", "0", "70000"])
def test_bad_port_stops(monkeypatch, bad):
    monkeypatch.setenv("AUREON_MIND_HUB_PORT", bad)
    with pytest.raises(SystemExit):
        hub_mod.mind_hub_bind()

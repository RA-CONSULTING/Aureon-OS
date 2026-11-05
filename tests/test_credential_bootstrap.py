"""
Aureon — credential bootstrap tests (Phase 16).

``bootstrap_credentials`` is the one call every long-running HNC process makes
so all keys reach the environment. These tests pin the two properties that make
it safe to log at boot: it reports **presence booleans only** (never a secret
value or a length that could leak a short key), and it never raises — a missing
dotenv or an empty/absent keystore degrades to "just the current environment".
Offline, no network.

Isolation: ``resolve_repo_root`` walks up looking for a dir containing both
``aureon/`` and ``scripts/`` — so each test builds a *fake* repo root under
``tmp_path`` (with those two dirs) to keep ``candidate_env_paths`` off the real
repo ``.env``. ``AUREON_ENV_FILE``/``DOTENV_PATH`` are cleared, ``os.environ``
is snapshot/restored, and the keystore is pointed at a throwaway dir so a
developer's real keys can't leak into the presence report.
"""

from __future__ import annotations

import json
import os

import pytest

from aureon.core import aureon_env


@pytest.fixture()
def fake_repo(tmp_path, monkeypatch):
    """A tmp dir that resolve_repo_root will accept as the repo root."""
    (tmp_path / "aureon").mkdir()
    (tmp_path / "scripts").mkdir()
    # keep candidate_env_paths from prepending an external file
    monkeypatch.delenv("AUREON_ENV_FILE", raising=False)
    monkeypatch.delenv("DOTENV_PATH", raising=False)
    # isolate the keystore so real UI-stored keys never leak into the report
    try:
        from aureon.operator import keystore

        monkeypatch.setattr(keystore, "CONFIG_DIR", tmp_path / "ks", raising=False)
        monkeypatch.setattr(keystore, "KEY_PATH", tmp_path / "ks" / "aureon.key", raising=False)
        monkeypatch.setattr(keystore, "STORE_PATH", tmp_path / "ks" / "keys.json.enc", raising=False)
    except Exception:
        pass
    # snapshot/restore os.environ around the mutation the bootstrap performs
    saved = dict(os.environ)
    for var in aureon_env.HNC_RUNTIME_KEYS:
        os.environ.pop(var, None)
    yield tmp_path
    os.environ.clear()
    os.environ.update(saved)


def test_bootstrap_loads_env_and_reports_presence(fake_repo):
    (fake_repo / ".env").write_text(
        "NASA_API_KEY=nasa-secret-1234\n"
        "NOAA_API_KEY=noaa-secret-5678\n"
        "# a comment\n"
        "USGS_API_KEY=usgs-secret-9012\n",
        encoding="utf-8",
    )
    report = aureon_env.bootstrap_credentials(repo_root=fake_repo)

    assert report["loaded"] is True
    present = report["present"]
    # every runtime key is reported, as a bool
    assert set(present) == set(aureon_env.HNC_RUNTIME_KEYS)
    assert all(isinstance(v, bool) for v in present.values())
    # the three keys we wrote resolved; an unwritten one did not
    assert present["NASA_API_KEY"] is True
    assert present["NOAA_API_KEY"] is True
    assert present["USGS_API_KEY"] is True
    assert present["OPENAI_API_KEY"] is False
    # and the values actually reached the environment for the daemons
    assert os.environ["NOAA_API_KEY"] == "noaa-secret-5678"


def test_bootstrap_never_leaks_secret_values(fake_repo):
    secret = "SUPER-SECRET-VALUE-abcdefghijklmnop"
    (fake_repo / ".env").write_text(f"NASA_API_KEY={secret}\n", encoding="utf-8")

    report = aureon_env.bootstrap_credentials(repo_root=fake_repo)

    # the report is presence-only: no secret, and no length that leaks it
    blob = json.dumps(report)
    assert secret not in blob
    assert str(len(secret)) not in json.dumps(report["present"])
    assert report["present"]["NASA_API_KEY"] is True


def test_plug_and_play_skips_dotenv(fake_repo, monkeypatch):
    monkeypatch.setenv("AUREON_PLUG_AND_PLAY", "1")
    secret = "plug-must-not-load-this-key"
    (fake_repo / ".env").write_text(f"OPENAI_API_KEY={secret}\n", encoding="utf-8")

    report = aureon_env.bootstrap_credentials(repo_root=fake_repo)

    assert report["loaded"] is False
    assert report["keystore_applied"] is False
    assert report["plug_and_play"] is True
    assert report["present"]["OPENAI_API_KEY"] is False
    assert "OPENAI_API_KEY" not in os.environ
    assert secret not in json.dumps(report)


def test_bootstrap_idempotent_and_never_raises(fake_repo):
    # no .env at all under this root → still succeeds, just nothing loaded
    r1 = aureon_env.bootstrap_credentials(repo_root=fake_repo)
    r2 = aureon_env.bootstrap_credentials(repo_root=fake_repo)
    assert set(r1["present"]) == set(aureon_env.HNC_RUNTIME_KEYS)
    assert r1["present"] == r2["present"]
    assert all(v is False for v in r1["present"].values())
    assert isinstance(r1["keystore_applied"], bool)

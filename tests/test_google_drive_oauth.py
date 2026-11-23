"""Offline tests for the read-only Drive OAuth and selective env import paths."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

from aureon.connectors.base import CredentialSource, OAUTH_TOKEN_ENV_VAR, build_google_service
from aureon.connectors.google_drive import DriveConnector

ROOT = Path(__file__).resolve().parents[1]


def _script(name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_oauth_token_is_used_without_service_account(tmp_path, monkeypatch):
    token = tmp_path / "token.dpapi"
    token.write_bytes(b"protected")
    monkeypatch.setattr("aureon.connectors.base._load_oauth_credentials", lambda *_args: object())
    import googleapiclient.discovery

    monkeypatch.setattr(googleapiclient.discovery, "build", lambda *_args, **_kwargs: object())
    service, status = build_google_service("drive", "v3", ["scope"], env={OAUTH_TOKEN_ENV_VAR: str(token)})
    assert service is not None
    assert status.available is True
    assert status.source == f"env:{OAUTH_TOKEN_ENV_VAR}"


def test_existing_service_account_still_has_precedence(tmp_path, monkeypatch):
    credential = tmp_path / "service.json"
    credential.write_text("not-read-by-this-mock")
    monkeypatch.setattr(
        "aureon.connectors.base._load_oauth_credentials",
        lambda *_args: (_ for _ in ()).throw(AssertionError()),
    )
    from google.oauth2 import service_account
    import googleapiclient.discovery

    monkeypatch.setattr(
        service_account.Credentials, "from_service_account_file", lambda *_args, **_kwargs: object()
    )
    monkeypatch.setattr(googleapiclient.discovery, "build", lambda *_args, **_kwargs: object())
    _service, status = build_google_service(
        "drive", "v3", ["scope"], env={"GOOGLE_APPLICATION_CREDENTIALS": str(credential)}
    )
    assert status.available is True
    assert status.source == "env:GOOGLE_APPLICATION_CREDENTIALS"


def test_oauth_client_file_validation_does_not_echo_secrets(tmp_path):
    tool = _script("setup_google_drive")
    path = tmp_path / "client.json"
    path.write_text(
        json.dumps(
            {
                "installed": {
                    "client_id": "test-client",
                    "client_secret": "not-real",
                    "redirect_uris": ["http://localhost"],
                }
            }
        )
    )
    assert tool._validate_client_file(path) == path.resolve()


def test_drive_env_import_selects_names_and_never_overwrites(tmp_path):
    tool = _script("import_drive_env")
    values = tool.selected(
        "AUREON_OWN_LLM_MODEL=aureon-7b-v65k\n"
        "KRAKEN_API_KEY=not-a-real-key\n"
        "not valid\n"
        "random prose\n"
        "PATH=must-not-be-overwritten\n"
    )
    assert "PATH" not in values
    target = tmp_path / ".env.local"
    target.write_text("KRAKEN_API_KEY=existing-local-value\n")
    added = tool.merge(target, values)
    assert added == ["AUREON_OWN_LLM_MODEL"]
    assert "existing-local-value" in target.read_text()
    assert "must-not-be-overwritten" not in target.read_text()

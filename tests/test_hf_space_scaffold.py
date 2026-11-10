"""Guarded Hugging Face scaffold. No sign-in, no public listener, pin unchanged."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PIN = "0646146c53e59dbcab41363a613d5651c9c9d50f"
TIP = "0646146c53e59dbcab41363a613d5651c9c9d50f"
SPACES = ("hnc-field", "auris-coherence", "qgita-snr", "organism-replay")
TOKEN = "hf_test_token_value_not_real"
BANNED = ("production ready", "production-ready", "validated", "Space is live")


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


bind = _load(ROOT / "huggingface" / "space_bind.py", "aureon_hf_space_bind")
distribution = _load(ROOT / "huggingface" / "distribution.py", "aureon_hf_distribution")


def _trading_env() -> dict[str, str]:
    return dict(bind.REQUIRED_ENV)


class _Demo:
    def __init__(self) -> None:
        self.kwargs: dict | None = None

    def launch(self, **kwargs) -> None:
        self.kwargs = kwargs


def _git_blob_sha1(data: bytes) -> str:
    header = f"blob {len(data)}\0".encode("ascii")
    return hashlib.sha1(header + data).hexdigest()


def test_public_pin_orange_badge_and_guard_blob_stay() -> None:
    loader = (ROOT / "mcp" / "aureon_public" / "guard_loader.py").read_text(encoding="utf-8")
    guard = (ROOT / "huggingface" / "hnc-field" / "guard.py").read_bytes()
    blob = re.search(r'GUARD_BLOB = "([0-9a-f]{40})"', loader)
    assert blob is not None
    assert _git_blob_sha1(guard) == blob.group(1)
    assert f'COMMIT = "{PIN}"' in guard.decode("utf-8")
    assert f'PINNED_COMMIT = "{PIN}"' in loader
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "release%20boundary-HOLD-orange" in readme
    for name in SPACES:
        text = (ROOT / "huggingface" / name / "requirements.txt").read_text(encoding="utf-8")
        assert PIN in text


def test_space_bind_copies_match_and_apps_use_them() -> None:
    canonical = (ROOT / "huggingface" / "space_bind.py").read_bytes()
    for name in SPACES:
        assert (ROOT / "huggingface" / name / "space_bind.py").read_bytes() == canonical
        app = (ROOT / "huggingface" / name / "app.py").read_text(encoding="utf-8")
        assert "space_bind.launch(demo)" in app
        assert "share=True" not in app
        assert "server_name=\"0.0.0.0\"" not in app


def test_bind_stays_on_localhost_until_gary_yes() -> None:
    env = _trading_env()
    assert bind.resolve_bind(env) == "127.0.0.1"
    env["AUREON_HF_BIND"] = "0.0.0.0"
    with pytest.raises(SystemExit, match="127.0.0.1"):
        bind.resolve_bind(env)
    env["AUREON_HF_GARY_YES"] = "1"
    with pytest.raises(SystemExit, match="127.0.0.1"):
        bind.resolve_bind(env)
    env["AUREON_HF_LISTENER"] = "1"
    assert bind.resolve_bind(env) == "0.0.0.0"
    env["AUREON_HF_SHARE"] = "1"
    with pytest.raises(SystemExit, match="share"):
        bind.resolve_bind(env)


def test_launch_scrubs_secrets_and_refuses_share(tmp_path: Path) -> None:
    env = _trading_env()
    env["HF_TOKEN"] = TOKEN
    env["KRAKEN_API_SECRET"] = "super-secret-kraken"
    env["PORT"] = "7861"
    demo = _Demo()
    meta: list = []
    bind.launch(demo, env=env, space_dir=tmp_path, meta_path=meta)
    assert demo.kwargs is not None
    assert demo.kwargs["server_name"] == "127.0.0.1"
    assert demo.kwargs["server_port"] == 7861
    assert demo.kwargs["share"] is False
    assert "HF_TOKEN" not in env
    assert "KRAKEN_API_SECRET" not in env
    assert TOKEN not in env.values()
    assert meta and type(meta[0]).__name__ == "_BlockDotenv"
    with pytest.raises(ImportError, match="dotenv"):
        meta[0].find_spec("dotenv", None)


def test_dotenv_file_is_not_opened(tmp_path: Path) -> None:
    secret = tmp_path / ".env"
    secret.write_text(f"HF_TOKEN={TOKEN}\n", encoding="utf-8")
    with pytest.raises(SystemExit, match="not read") as exc:
        bind.assert_no_dotenv_file(tmp_path)
    assert TOKEN not in str(exc.value)


def test_measure_names_missing_token_and_does_not_record_it() -> None:
    env = {"HF_TOKEN": "", "AUREON_HF_FLAVOR": "cpu-basic"}
    receipt = distribution.measure(env, root=ROOT, now="2026-11-05T20:40:00Z")
    encoded = json.dumps(receipt)
    assert receipt["decision"] == "HOLD"
    assert receipt["tag"] == "hold-skip"
    assert receipt["space_live"] is False
    assert receipt["deploy_attempted"] is False
    assert receipt["sign_in_attempted"] is False
    assert receipt["go_live"] == "HOLD"
    assert receipt["go_live_clear"] is False
    assert receipt["pin_moved"] is False
    assert receipt["orange_badge"] == "unchanged"
    assert receipt["orders_placed"] is False
    assert receipt["public_require_pin"] == PIN
    assert "HF_TOKEN" in receipt["missing"]
    assert "GARY_YES" in receipt["missing"]
    assert "PRO" in receipt["reason"]
    assert receipt["pro_status"] == "not_queried"
    assert receipt["pro_required"] is False
    assert TOKEN not in encoded

    env["HF_TOKEN"] = TOKEN
    env["AUREON_HF_FLAVOR"] = "zero-a10g"
    held = distribution.measure(env, root=ROOT, now="2026-11-05T20:40:00Z")
    encoded = json.dumps(held)
    assert held["token_present"] is True
    assert "HF_TOKEN" not in held["missing"]
    assert "PRO" in held["missing"]
    assert TOKEN not in encoded


def test_deploy_does_not_sign_in_without_gates() -> None:
    def boom(token: str):
        raise AssertionError(token)

    missing = distribution.deploy({"HF_ORG": "example-org"}, client_factory=boom, root=ROOT)
    assert missing["deploy_attempted"] is False
    assert missing["sign_in_attempted"] is False
    assert missing["space_live"] is False
    assert "HF_TOKEN" in missing["missing"]

    present = distribution.deploy(
        {"HF_TOKEN": TOKEN, "HF_ORG": "example-org", "AUREON_HF_FLAVOR": "cpu-basic"},
        client_factory=boom,
        root=ROOT,
    )
    assert present["token_present"] is True
    assert present["deploy_attempted"] is False
    assert present["sign_in_attempted"] is False
    assert TOKEN not in json.dumps(present)
    assert "GARY_YES" in present["missing"]

    pro = distribution.deploy(
        {
            "HF_TOKEN": TOKEN,
            "HF_ORG": "example-org",
            "AUREON_HF_GARY_YES": "1",
            "AUREON_HF_FLAVOR": "zero-a10g",
        },
        client_factory=boom,
        root=ROOT,
    )
    assert pro["deploy_attempted"] is False
    assert "PRO" in pro["missing"]
    assert pro["space_live"] is False


def test_public_visibility_is_refused_and_private_upload_is_not_live() -> None:
    def boom(token: str):
        raise AssertionError(token)

    refused = distribution.deploy(
        {
            "HF_TOKEN": TOKEN,
            "HF_ORG": "example-org",
            "AUREON_HF_GARY_YES": "1",
            "AUREON_HF_VISIBILITY": "public",
        },
        client_factory=boom,
        root=ROOT,
    )
    assert refused["deploy_attempted"] is False
    assert refused["space_live"] is False

    class _Info:
        private = True

    class _Api:
        def __init__(self, token: str) -> None:
            self.token = token
            self.creates: list[dict] = []

        def create_repo(self, **kwargs) -> str:
            self.creates.append(kwargs)
            return kwargs["repo_id"]

        def upload_folder(self, **kwargs) -> None:
            assert ".env" in kwargs["ignore_patterns"]
            assert self.token == TOKEN

        def repo_info(self, repo_id: str, repo_type: str) -> _Info:
            assert repo_type in {"dataset", "space"}
            return _Info()

    api = _Api(TOKEN)

    def factory(token: str) -> _Api:
        assert token == TOKEN
        return api

    uploaded = distribution.deploy(
        {
            "HF_TOKEN": TOKEN,
            "HF_ORG": "example-org",
            "AUREON_HF_GARY_YES": "1",
        },
        client_factory=factory,
        root=ROOT,
    )
    assert uploaded["deploy_attempted"] is True
    assert uploaded["sign_in_attempted"] is True
    assert uploaded["space_live"] is False
    assert uploaded["go_live"] == "HOLD"
    assert uploaded["tag"] == "uploaded-not-live"
    assert uploaded["visibility_selected"] == "private"
    assert uploaded["public_listener_opened"] is False
    assert all(row["private"] is True for row in api.creates)
    assert TOKEN not in json.dumps(uploaded)

    class _Runtime:
        stage = "RUNNING"

    class _Running:
        private = True
        runtime = _Runtime()

    class _RunningApi(_Api):
        def repo_info(self, repo_id: str, repo_type: str) -> _Running:
            return _Running()

    running = distribution.deploy(
        {
            "HF_TOKEN": TOKEN,
            "HF_ORG": "example-org",
            "AUREON_HF_GARY_YES": "1",
        },
        client_factory=lambda token: _RunningApi(token),
        root=ROOT,
    )
    assert running["space_live"] is True
    assert running["go_live"] == "HOLD"
    assert running["go_live_clear"] is False
    assert running["orange_badge"] == "unchanged"
    assert running["public_listener_opened"] is False
    assert running["tag"] == "runtime-running"
    assert "Space is live" not in json.dumps(running)


def test_hub_pro_error_is_named_and_redacted() -> None:
    class _Api:
        def __init__(self, token: str) -> None:
            self.token = token

        def create_repo(self, **kwargs) -> None:
            raise RuntimeError(f"PRO subscription required for this hardware {self.token}")

    receipt = distribution.deploy(
        {
            "HF_TOKEN": TOKEN,
            "HF_ORG": "example-org",
            "AUREON_HF_GARY_YES": "1",
        },
        client_factory=lambda token: _Api(token),
        root=ROOT,
    )
    encoded = json.dumps(receipt)
    assert receipt["space_live"] is False
    assert receipt["deploy_attempted"] is True
    assert "PRO" in receipt["missing"]
    assert receipt["pro_status"] == "hub_required"
    assert TOKEN not in encoded


def test_committed_receipt_is_hold_skip() -> None:
    path = ROOT / "measured" / "hf_space_distribution.json"
    md = (ROOT / "measured" / "hf_space_distribution.md").read_text(encoding="utf-8")
    receipt = json.loads(path.read_text(encoding="utf-8"))
    assert receipt["schema"] == "aureon.hf_space.distribution.v1"
    assert receipt["decision"] == "HOLD"
    assert receipt["tag"] == "hold-skip"
    assert receipt["space_live"] is False
    assert receipt["deploy_attempted"] is False
    assert receipt["sign_in_attempted"] is False
    assert receipt["token_present"] is False
    assert receipt["token_value_recorded"] is False
    assert "HF_TOKEN" in receipt["missing"]
    assert receipt["pro_status"] == "not_queried"
    assert receipt["pro_required"] is False
    assert "PRO" in receipt["reason"]
    assert receipt["public_require_pin"] == PIN
    assert receipt["pin_moved"] is False
    assert receipt["orange_badge"] == "unchanged"
    assert receipt["go_live"] == "HOLD"
    assert receipt["go_live_clear"] is False
    assert receipt["orders_placed"] is False
    assert receipt["git_head_at_measurement"] == TIP
    assert "The Space is not live." in md
    assert "Go-live: **HOLD**" in md
    docs = [
        ROOT / "huggingface" / "README.md",
        ROOT / "huggingface" / "PUBLISH.md",
        ROOT / "huggingface" / "ORG_CARD.md",
        ROOT / "measured" / "hf_space_distribution.md",
    ]
    docs.extend(ROOT / "huggingface" / name / "README.md" for name in SPACES)
    blob = "\n".join(path.read_text(encoding="utf-8") for path in docs)
    for phrase in BANNED:
        assert phrase not in blob
    publish = (ROOT / "huggingface" / "PUBLISH.md").read_text(encoding="utf-8")
    assert "--private" in publish
    assert "--public" not in publish
    assert "private=True" in publish
    assert "zero-a10g" in publish

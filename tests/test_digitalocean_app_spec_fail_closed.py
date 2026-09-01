from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
APP_SPECS = (REPO_ROOT / "app.yaml", REPO_ROOT / ".do" / "app.yaml")
COMPONENT_KEYS = (
    "services",
    "workers",
    "jobs",
    "static_sites",
    "functions",
    "databases",
)
FORBIDDEN_KEYS = {
    "github",
    "gitlab",
    "repo_clone_url",
    "deploy_on_push",
    "dockerfile_path",
    "source_dir",
    "envs",
    "http_port",
    "health_check",
}


def _spec(path: Path) -> dict[str, Any]:
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict)
    return loaded


def _walk_keys(value: object) -> set[str]:
    if isinstance(value, dict):
        keys = {str(key) for key in value}
        for child in value.values():
            keys.update(_walk_keys(child))
        return keys
    if isinstance(value, list):
        keys: set[str] = set()
        for child in value:
            keys.update(_walk_keys(child))
        return keys
    return set()


def test_every_digitalocean_manifest_is_an_empty_terminal_hold() -> None:
    for path in APP_SPECS:
        spec = _spec(path)
        assert spec["name"] == "aureon-protection-hold"
        assert spec["region"] == "lon"
        for component in COMPONENT_KEYS:
            assert spec.get(component) == [], f"{path}: {component} is deployable"


def test_holds_have_no_source_binding_runtime_or_secret_surface() -> None:
    for path in APP_SPECS:
        keys = _walk_keys(_spec(path))
        assert keys.isdisjoint(FORBIDDEN_KEYS), f"{path}: {keys & FORBIDDEN_KEYS}"

        source = path.read_text(encoding="utf-8")
        assert "deploy_on_push" not in source
        assert "type: SECRET" not in source
        assert "REDIS_URL" not in source
        assert "AUREON_LIVE_TRADING" not in source

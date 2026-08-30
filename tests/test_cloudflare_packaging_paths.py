from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
FLAMEBORN_ROOT = REPO_ROOT / "flameborn"
DEPLOY_ROOT = REPO_ROOT / "deploy" / "cloudflare" / "aureon_murge_worker"
UI_ROOT = FLAMEBORN_ROOT / "cloudflare-ui"
EXPECTED_UI_FILES = {".assetsignore", "_headers", "app.js", "index.html", "style.css"}


def _config(root: Path) -> dict[str, object]:
    loaded = json.loads((root / "wrangler.jsonc").read_text(encoding="utf-8"))
    assert isinstance(loaded, dict)
    return loaded


def test_every_cloudflare_entrypoint_resolves_from_its_config() -> None:
    for root in (FLAMEBORN_ROOT, DEPLOY_ROOT):
        config = _config(root)
        entrypoint = root / str(config["main"])
        assert entrypoint.is_file()
        assert config["assets"]["directory"] == "./dist-workers"
        assert config["assets"]["run_worker_first"] == ["/api", "/api/*"]


def test_worker_asset_build_references_only_existing_sources() -> None:
    script = (
        FLAMEBORN_ROOT / "scripts" / "build_workers_assets.sh"
    ).read_text(encoding="utf-8")
    assert 'SOURCE_DIR="$PROJECT_DIR/cloudflare-ui"' in script
    assert "for file in index.html app.js style.css _headers .assetsignore" in script
    assert 'mktemp -d "$PROJECT_DIR/.dist-workers.XXXXXX"' in script
    assert 'if [[ "$DIST_DIR" != "$PROJECT_DIR/dist-workers" ]]' in script
    assert {path.name for path in UI_ROOT.iterdir() if path.is_file()} == EXPECTED_UI_FILES


def test_html_asset_references_are_packaged() -> None:
    html = (UI_ROOT / "index.html").read_text(encoding="utf-8")
    referenced_assets = {"app.js", "style.css"}

    assert all(f'{attribute}="{asset}"' in html for attribute, asset in (
        ("src", "app.js"),
        ("href", "style.css"),
    ))
    assert all((UI_ROOT / asset).is_file() for asset in referenced_assets)
    assert "node_modules" not in html
    assert 'id="apiKey"' not in html

"""The public front door is a reading copy. It must not claim a deploy."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"
HOLD_SENTENCE = (
    "Go-live is HOLD. This checkout is never production ready and never a validated deployment."
)
HOMEPAGE = "https://aureonzorzatechnologies.pl"


def _html_pages() -> list[Path]:
    return sorted(SITE.rglob("*.html"))


def _active_workflow(text: str) -> str:
    kept: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        kept.append(line)
    return "\n".join(kept)


def test_front_door_pages_state_the_hold_and_the_homepage() -> None:
    pages = _html_pages()
    assert [path.relative_to(SITE).as_posix() for path in pages] == [
        "index.html",
        "install/index.html",
        "status/index.html",
    ]
    for path in pages:
        text = path.read_text(encoding="utf-8")
        assert HOLD_SENTENCE in text
        assert HOMEPAGE in text
        assert "GitHub Pages is off. This scaffold does not enable it." in text
        assert 'name="robots" content="noindex, nofollow"' in text
        assert "<main" in text
        scrubbed = text.replace("never production ready", "").replace(
            "never a validated deployment",
            "",
        )
        lowered = scrubbed.casefold()
        assert "production ready" not in lowered
        assert "production-ready" not in lowered
        assert "validated" not in lowered
        assert "0.0.0.0" not in text
        assert "href=\"cname\"" not in lowered


HONESTY = (
    "The live routes are active. With exchange keys in <code>.env</code>, "
    "the launcher boots into live trading. There is no verified live track record."
)


def test_front_page_matches_readme_honesty() -> None:
    text = (SITE / "index.html").read_text(encoding="utf-8")
    assert HONESTY in text
    assert "./install.sh --smoke" in text
    assert "keeps live trading off for that run" in text
    assert "NI696693" in text
    assert "trading as Aureon Zorza Technologies" in text
    assert "R&amp;A Consulting and Brokerage Services Ltd" in text
    assert "GARY-YES-DEPLOY-PAGES" in text
    for path in [*_html_pages(), SITE / "README.md", SITE / "status.json"]:
        assert "SRC Engineering" not in path.read_text(encoding="utf-8")
    door = (ROOT / "README.md").read_text(encoding="utf-8")
    section = door.split("## Public front door", 1)[1].split("## Where to go next", 1)[0]
    assert "The live routes are active." in section
    assert "There is no verified live track record." in section
    assert "SRC Engineering" not in section


def test_install_page_points_at_the_guarded_clone_path() -> None:
    text = (SITE / "install" / "index.html").read_text(encoding="utf-8")
    assert HONESTY in text
    assert "git clone https://github.com/RA-CONSULTING/Aureon-OS.git" in text
    assert "./install.sh --smoke" in text
    assert "AUREON_AUTONOMY_MODE=guarded" in text
    assert "does not read" in text.casefold()
    assert ".env" in text
    assert "http://127.0.0.1:8790/" in text
    assert "production/install.sh" in text
    assert "aureon-master.sh" in text


def test_status_json_keeps_go_live_on_hold() -> None:
    payload = json.loads((SITE / "status.json").read_text(encoding="utf-8"))
    assert payload["schema"] == "aureon.public-front-door.v1"
    assert payload["pages_feature_enabled_by_this_scaffold"] is False
    assert payload["pages_deploy"] == "HOLD"
    assert payload["go_live"] == "HOLD"
    assert payload["production_ready"] is False
    assert payload["validated"] is False
    assert payload["homepage"] == HOMEPAGE
    assert payload["license"] == "MIT"
    assert payload["clone_url"] == "https://github.com/RA-CONSULTING/Aureon-OS.git"
    assert payload["applicant"] == "R&A Consulting and Brokerage Services Ltd"
    assert payload["company_number"] == "NI696693"
    assert payload["trading_as"] == "Aureon Zorza Technologies"
    assert payload["guarded_install"] == "./install.sh --smoke"
    assert payload["guarded_install_reads_dotenv"] is False
    assert payload["guarded_smoke_live_trading"] is False
    assert payload["live_routes_active"] is True
    assert payload["env_keys_boot_live"] is True
    assert payload["verified_live_track_record"] is False


def test_robots_and_license_pointer_stay_closed() -> None:
    robots = (SITE / "robots.txt").read_text(encoding="utf-8")
    assert "Disallow: /" in robots
    assert not (SITE / "CNAME").exists()
    assert not (ROOT / "CNAME").exists()
    home = (SITE / "index.html").read_text(encoding="utf-8")
    assert "MIT" in home
    assert "LICENSE" in home
    assert "has_pages: false" in home


def test_pages_workflow_cannot_deploy_without_gary_yes() -> None:
    path = ROOT / ".github" / "workflows" / "pages-gated.yml"
    raw = path.read_text(encoding="utf-8")
    active = _active_workflow(raw)
    assert "workflow_dispatch:" in active
    assert "push:" not in active
    assert "pull_request:" not in active
    assert "schedule:" not in active
    assert "default: HOLD" in active
    assert "GARY-YES-DEPLOY-PAGES" in active
    assert "vars.AUREON_PAGES_DEPLOY == 'gary-yes'" in active
    assert "path: site" in active
    assert "exit 1" in active
    assert "gh api" not in active
    assert "enable-pages" not in active.casefold()
    assert active.index("permissions:\n  contents: read") < active.index("jobs:")
    assert active.index("pages: write") > active.index("deploy:")
    assert "actions/deploy-pages@v4" in active
    assert "actions/upload-pages-artifact@v3" in active


def test_status_page_keeps_go_live_clear_false() -> None:
    text = (SITE / "status" / "index.html").read_text(encoding="utf-8")
    assert "<code>go_live_clear</code> is false" in text
    assert "go-live is clear" not in text.casefold()
    assert "go_live_clear</code> is true" not in text


def test_readme_sends_strangers_to_the_reading_copy() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "site/index.html" in readme
    assert "GitHub Pages is off" in readme
    assert HOMEPAGE in readme
    assert "./install.sh" in readme

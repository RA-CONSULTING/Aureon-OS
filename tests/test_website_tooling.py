"""Tests for the static-website tooling: auditor, packager, and FTP deployer.

Offline and hermetic — the auditor/packager run against tiny fixtures built in ``tmp_path`` (and
the real ``website/`` for the clean-site assertion); the FTP deployer is exercised only via its
env-gating and dry-run plan (never a real network connection).
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import pytest

from scripts.website import audit_site, build_package, ftp_deploy

_REPO = Path(__file__).resolve().parents[1]

_GOOD_INDEX = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Test Site</title>
  <meta name="description" content="A test site.">
  <link rel="canonical" href="https://aureonzorzatechnologies.pl/">
  <meta property="og:url" content="https://aureonzorzatechnologies.pl/">
  <link rel="stylesheet" href="styles.css">
</head>
<body>
  <a class="skip-link" href="#main-content">Skip to content</a>
  <main id="main-content">
    <h1>Hello</h1>
    <img src="assets/pic.webp" alt="A picture" loading="lazy" decoding="async">
    <a href="https://github.com/x" target="_blank" rel="noopener noreferrer">External</a>
  </main>
  <script src="script.js"></script>
</body>
</html>
"""

_SITEMAP = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://aureonzorzatechnologies.pl/</loc></url>
</urlset>
"""

_ROBOTS = "User-agent: *\nAllow: /\n\nSitemap: https://aureonzorzatechnologies.pl/sitemap.xml\n"


def _make_good_site(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / "index.html").write_text(_GOOD_INDEX, encoding="utf-8")
    (root / "styles.css").write_text("body{color:#000}\n", encoding="utf-8")
    (root / "script.js").write_text("// noop\n", encoding="utf-8")
    (root / "robots.txt").write_text(_ROBOTS, encoding="utf-8")
    (root / "sitemap.xml").write_text(_SITEMAP, encoding="utf-8")
    (root / "assets").mkdir()
    (root / "assets" / "pic.webp").write_bytes(b"RIFF0000WEBP")
    return root


def _errors(root: Path) -> list[audit_site.Finding]:
    return [f for f in audit_site.audit(root) if f.level == "ERROR"]


# ---------------------------------------------------------------------------
# auditor
# ---------------------------------------------------------------------------


def test_good_site_has_no_errors(tmp_path):
    root = _make_good_site(tmp_path / "site")
    assert _errors(root) == []


def test_real_website_is_clean():
    root = _REPO / "website"
    if not root.is_dir():
        pytest.skip("website/ not present")
    errs = _errors(root)
    assert errs == [], f"real site has audit errors: {[(e.page, e.check) for e in errs]}"


def test_public_footprint_snapshot_matches_marked_surfaces():
    root = _REPO / "website"
    snapshot = json.loads((root / "data" / "public-attention-snapshot.json").read_text(encoding="utf-8"))
    signals = {signal["metric"]: signal for signal in snapshot["signals"]}
    pages = {
        "home": (root / "index.html").read_text(encoding="utf-8"),
        "research": (root / "research" / "index.html").read_text(encoding="utf-8"),
        "investor": (root / "funding" / "investor-deck" / "index.html").read_text(encoding="utf-8"),
    }

    required_pages = {
        "public_work_groups": ("home", "research", "investor"),
        "main_branch_commits": ("home",),
        "research_reads": ("home", "investor"),
    }
    for metric, page_names in required_pages.items():
        formatted = f"{signals[metric]['value']:,}"
        marker = re.compile(rf'data-footprint-value="{re.escape(metric)}">{re.escape(formatted)}<')
        for page_name in page_names:
            assert marker.search(pages[page_name]), f"{page_name} fallback drifted from {metric}={formatted}"

    github = signals["main_branch_commits"]
    github_summary = (
        f"{github['value']:,} commits &middot; "
        f"{github['secondary_metrics']['stars']} stars &middot; "
        f"{github['secondary_metrics']['forks']} forks"
    )
    assert github_summary in pages["investor"]
    script = (root / "script.js").read_text(encoding="utf-8")
    assert 'loadJson("data/public-attention-snapshot.json")' in script


def test_missing_alt_is_error(tmp_path):
    root = _make_good_site(tmp_path / "site")
    html = (
        (root / "index.html")
        .read_text()
        .replace(
            '<img src="assets/pic.webp" alt="A picture" loading="lazy" decoding="async">',
            '<img src="assets/pic.webp" loading="lazy">',
        )
    )
    (root / "index.html").write_text(html)
    assert any(e.check == "a11y-img-alt" for e in _errors(root))


def test_dead_asset_is_error(tmp_path):
    root = _make_good_site(tmp_path / "site")
    html = (root / "index.html").read_text().replace("assets/pic.webp", "assets/missing.webp")
    (root / "index.html").write_text(html)
    assert any(e.check == "dead-asset" for e in _errors(root))


def test_og_url_mismatch_is_error(tmp_path):
    root = _make_good_site(tmp_path / "site")
    html = (
        (root / "index.html")
        .read_text()
        .replace(
            '<meta property="og:url" content="https://aureonzorzatechnologies.pl/">',
            '<meta property="og:url" content="https://aureonzorzatechnologies.pl/other/">',
        )
    )
    (root / "index.html").write_text(html)
    assert any(e.check == "seo-og-url" for e in _errors(root))


def test_sitemap_drift_is_error(tmp_path):
    root = _make_good_site(tmp_path / "site")
    (root / "about").mkdir()
    (root / "about" / "index.html").write_text(
        _GOOD_INDEX.replace(
            "https://aureonzorzatechnologies.pl/", "https://aureonzorzatechnologies.pl/about/"
        ),
        encoding="utf-8",
    )
    # about/ is indexable but not in the sitemap → drift
    assert any(e.check == "sitemap-missing" for e in _errors(root))


def test_blank_link_without_noopener_is_error(tmp_path):
    root = _make_good_site(tmp_path / "site")
    html = (
        (root / "index.html")
        .read_text()
        .replace(
            '<a href="https://github.com/x" target="_blank" rel="noopener noreferrer">External</a>',
            '<a href="https://github.com/x" target="_blank">External</a>',
        )
    )
    (root / "index.html").write_text(html)
    assert any(e.check == "a11y-noopener" for e in _errors(root))


def test_broken_skip_target_is_error(tmp_path):
    root = _make_good_site(tmp_path / "site")
    html = (root / "index.html").read_text().replace('<main id="main-content">', "<main>")
    (root / "index.html").write_text(html)
    assert any(e.check == "a11y-skip-target" for e in _errors(root))


# ---------------------------------------------------------------------------
# packager
# ---------------------------------------------------------------------------


def test_build_is_deterministic_and_checksum_matches(tmp_path):
    root = _make_good_site(tmp_path / "site")
    a = build_package.build(root, tmp_path / "out_a", created_at="2026-01-01T00:00:00Z")
    b = build_package.build(root, tmp_path / "out_b", created_at="2026-01-01T00:00:00Z")

    zip_a = Path(a["zip_path"]).read_bytes()
    zip_b = Path(b["zip_path"]).read_bytes()
    assert zip_a == zip_b, "two builds at the same created-at must be byte-identical"
    assert a["zip_sha256"] == hashlib.sha256(zip_a).hexdigest() == b["zip_sha256"]

    pkg = Path(a["package_dir"])
    assert (pkg / "index.html").is_file()  # index.html at package root
    manifest = (pkg / build_package.MANIFEST_NAME).read_text()
    payload = [p for p in pkg.rglob("*") if p.is_file() and p.name != build_package.MANIFEST_NAME]
    assert f"TOTAL_FILE_COUNT: {len(payload):06d}" in manifest
    assert "HTACCESS_SECURITY_CONFIGURATION_INCLUDED: NO" in manifest
    assert "HTACCESS_REQUIRED" not in manifest
    companion = Path(a["companion"]).read_text()
    assert a["zip_sha256"] in companion and str(a["zip_size"]) in companion


def test_build_aborts_on_audit_error(tmp_path):
    root = _make_good_site(tmp_path / "site")
    (root / "index.html").write_text(
        (root / "index.html").read_text().replace("assets/pic.webp", "assets/missing.webp")
    )
    with pytest.raises(RuntimeError):
        build_package.build(root, tmp_path / "out", created_at="2026-01-01T00:00:00Z")


def test_build_excludes_working_surfaces_and_unreferenced_assets(tmp_path):
    root = _make_good_site(tmp_path / "site")
    (root / "archive").mkdir()
    (root / "archive" / "private.txt").write_text("working archive")
    (root / "styleguide.html").write_text("working style guide")
    (root / "data").mkdir()
    (root / "data" / "projects.json").write_text("[]")
    (root / "data" / "company-platform.json").write_text("[]")
    (root / "data" / "project-graph.json").write_text("{}")
    (root / "assets" / "css").mkdir()
    (root / "assets" / "css" / "aureon-zorza-backgrounds.css").write_text(".legacy{}")
    (root / "operator-notes.md").write_text("not a public runtime file")
    (root / "deploy-helper.ps1").write_text("Write-Output private")
    (root / ".env").write_text("SECRET=must-not-ship")
    (root / ".env.production").write_text("SECRET=must-not-ship")
    (root / "server.key").write_text("must-not-ship")
    (root / "certificate.pem").write_text("must-not-ship")
    (root / "identity.pfx").write_text("must-not-ship")
    (root / "identity.p12").write_text("must-not-ship")
    (root / "assets" / "unreferenced.png").write_bytes(b"not shipped")

    pkg = tmp_path / "website_package"
    build_package._copy_tree(root, pkg)

    assert (pkg / "assets" / "pic.webp").is_file()
    assert not (pkg / "assets" / "unreferenced.png").exists()
    assert not (pkg / "archive").exists()
    assert not (pkg / "styleguide.html").exists()
    assert not (pkg / "data" / "projects.json").exists()
    assert not (pkg / "data" / "company-platform.json").exists()
    assert not (pkg / "data" / "project-graph.json").exists()
    assert not (pkg / "assets" / "css" / "aureon-zorza-backgrounds.css").exists()
    assert not (pkg / "operator-notes.md").exists()
    assert not (pkg / "deploy-helper.ps1").exists()
    assert not (pkg / ".env").exists()
    assert not (pkg / ".env.production").exists()
    assert not (pkg / "server.key").exists()
    assert not (pkg / "certificate.pem").exists()
    assert not (pkg / "identity.pfx").exists()
    assert not (pkg / "identity.p12").exists()


def test_build_excludes_common_secret_bearing_names_directories_and_suffixes(tmp_path):
    root = _make_good_site(tmp_path / "site")
    secret_paths = (
        ".env.local",
        ".envrc",
        ".git-credentials",
        ".htpasswd",
        ".netrc",
        ".npmrc",
        ".pgpass",
        ".pypirc",
        ".aws/credentials",
        ".ssh/id_rsa",
        "Credentials.JSON",
        "auth.json",
        "client_secret_google.json",
        "firebase-adminsdk-prod.json",
        "google-services.json",
        "prod-service-account.json",
        "prod_credentials.json",
        "prod-secrets.json",
        "secrets.toml",
        "signing.jks",
        "signing.keystore",
        "passwords.kdbx",
        "ssh-private.ppk",
        "identity.pkcs8",
        "private-network.ovpn",
        "distribution.mobileprovision",
    )
    for relative in secret_paths:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("must-not-ship", encoding="utf-8")

    (root / ".htaccess").write_text("Options -Indexes", encoding="utf-8")
    (root / "tokens.css").write_text(":root { --safe-token: #fff; }", encoding="utf-8")
    pkg = tmp_path / "website_package"
    build_package._copy_tree(root, pkg)

    assert (pkg / ".htaccess").is_file()
    assert (pkg / "tokens.css").is_file()
    assert all(not (pkg / relative).exists() for relative in secret_paths)
    build_package._write_manifest(pkg, "2026-08-21T00:00:00Z")
    manifest = (pkg / build_package.MANIFEST_NAME).read_text(encoding="utf-8")
    assert "HTACCESS_SECURITY_CONFIGURATION_INCLUDED: YES" in manifest
    assert "HTACCESS_REQUIRED" not in manifest


# ---------------------------------------------------------------------------
# FTP deployer (env-gate + dry-run plan; no network)
# ---------------------------------------------------------------------------


def test_load_config_requires_all_env():
    with pytest.raises(KeyError):
        ftp_deploy.load_config(env={"AUREON_FTP_HOST": "h"})  # missing user/pass/dir


def test_load_config_defaults_to_ftps():
    cfg = ftp_deploy.load_config(
        env={
            "AUREON_FTP_HOST": "ftp.example.pl",
            "AUREON_FTP_USER": "u",
            "AUREON_FTP_PASS": "SECRETpw123",
            "AUREON_FTP_DIR": "/public_html/",
        }
    )
    assert cfg.tls is True and cfg.port == 21 and cfg.remote_dir == "/public_html"
    assert "SECRETpw123" not in cfg.safe_summary  # password never in the printable summary


def test_plan_uploads_maps_remote_paths(tmp_path):
    pkg = tmp_path / "website_package"
    (pkg / "assets").mkdir(parents=True)
    (pkg / "index.html").write_text("x")
    (pkg / "assets" / "a.webp").write_bytes(b"x")
    plan = ftp_deploy.plan_uploads(pkg, "/public_html")
    remotes = [r for _l, r in plan]
    assert remotes == ["/public_html/assets/a.webp", "/public_html/index.html"]


def test_dry_run_exits_zero_and_hides_password(tmp_path, capsys, monkeypatch):
    pkg = tmp_path / "website_package"
    pkg.mkdir()
    (pkg / "index.html").write_text("x")
    for k, v in {
        "AUREON_FTP_HOST": "ftp.example.pl",
        "AUREON_FTP_USER": "u",
        "AUREON_FTP_PASS": "SECRETXYZ",
        "AUREON_FTP_DIR": "/public_html",
    }.items():
        monkeypatch.setenv(k, v)
    rc = ftp_deploy.main(["--package", str(pkg), "--dry-run"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "/public_html/index.html" in out
    assert "SECRETXYZ" not in out


def test_deploy_refuses_without_env(tmp_path, monkeypatch, capsys):
    pkg = tmp_path / "website_package"
    pkg.mkdir()
    (pkg / "index.html").write_text("x")
    for k in ftp_deploy._REQUIRED_ENV:
        monkeypatch.delenv(k, raising=False)
    rc = ftp_deploy.main(["--package", str(pkg)])
    assert rc == 1
    assert "refused" in capsys.readouterr().err.lower()

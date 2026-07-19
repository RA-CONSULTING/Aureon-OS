"""
Aureon SaaS — catalog, domains, status tests (no HTTP; offline).
"""

from __future__ import annotations

import json
from pathlib import Path

from aureon.saas.catalog import build_catalog, write_frontend_manifests
from aureon.saas.domains import (
    PRODUCT_DOMAINS,
    domain_report,
    fs_domain_from_path,
    probe_domain,
    product_domain_for,
)
from aureon.saas.status import get_platform_status


def test_build_catalog_is_categorized():
    c = build_catalog()
    assert c["category_count"] == 12
    assert c["total_systems"] > 0
    assert set(c["product_domains"]) == set(PRODUCT_DOMAINS)
    assert c["filesystem_domains"]                       # non-empty domain rollup
    # every system carries both taxonomies
    a_cat = next(iter(c["categories"].values()))
    if a_cat["systems"]:
        s = a_cat["systems"][0]
        assert s["fs_domain"] and s["product_domain"] in PRODUCT_DOMAINS


def test_write_frontend_manifests_matches_ui_contract(tmp_path):
    written = write_frontend_manifests(out_dir=str(tmp_path))
    names = {Path(p).name for p in written}
    assert names == {"aureon_saas_system_inventory.json", "aureon_organism_runtime_status.json"}

    inv = json.loads((tmp_path / "aureon_saas_system_inventory.json").read_text())
    assert "surfaces" in inv and isinstance(inv["surfaces"], list) and inv["surfaces"]
    s0 = inv["surfaces"][0]
    for key in ("id", "path", "name", "kind", "domain", "wiring_status", "safety_class", "auth_requirement"):
        assert key in s0                                  # frontend SaaSInventorySurface contract
    assert s0["domain"] in PRODUCT_DOMAINS

    runtime = json.loads((tmp_path / "aureon_organism_runtime_status.json").read_text())
    assert "domains" in runtime and len(runtime["domains"]) == len(PRODUCT_DOMAINS)
    assert all("status" in d for d in runtime["domains"])  # OrganismDomainPulse


def test_taxonomy_mapping():
    assert product_domain_for("exchanges") == "trading"
    assert product_domain_for("queen") == "cognition"
    assert product_domain_for("totally_unknown_domain") == "self-improvement"
    assert fs_domain_from_path("aureon/queen/queen_conscience.py") == "queen"
    assert fs_domain_from_path("aureon/operator/cognition.py") == "operator"


def test_domain_report_reachability():
    report = domain_report()
    assert len(report) >= 24
    for d in report:
        assert set(d) >= {"domain", "product_domain", "entry_point", "available"}
    # the known-singleton domains must be reachable
    by = {d["domain"]: d for d in report}
    assert by["operator"]["available"] is True
    assert by["core"]["available"] is True


def test_probe_domain_shape():
    p = probe_domain("cognition")
    assert p["domain"] == "cognition"
    assert p["product_domain"] == "cognition"
    assert ":" in str(p["entry_point"])                  # module:attr


def test_platform_status_is_honest():
    s = get_platform_status()
    assert s["status"] in {"healthy", "degraded", "critical"}
    assert s["domains_total"] >= 24
    assert set(s["product_domains"]) == set(PRODUCT_DOMAINS)
    assert "operational_core" in s and "note" in s        # honesty note present


def test_bio_domain_is_connected():
    # the bio sensor suite / φ Celestial Observatory must be surfaced by the SaaS
    # product layer — categorized under research and reachable via its observatory.
    p = probe_domain("bio")
    assert p["product_domain"] == "research"
    assert p["available"] is True
    assert p["entry_point"] == "aureon.bio.celestial_observatory:observe"
    # and it appears in the aggregate report
    assert any(d["domain"] == "bio" for d in domain_report())


def test_every_real_aureon_package_is_categorized():
    # "all systems connected": no real package under aureon/ (one with .py modules)
    # may be left out of the product-domain taxonomy — otherwise it silently defaults
    # to self-improvement and never gets an intentional home.
    import aureon
    from aureon.saas.domains import _FS_TO_PRODUCT

    root = Path(aureon.__file__).resolve().parent
    real_pkgs = {
        child.name
        for child in root.iterdir()
        if child.is_dir()
        and not child.name.startswith("__")
        and any(f.suffix == ".py" for f in child.iterdir())
    }
    unmapped = sorted(real_pkgs - set(_FS_TO_PRODUCT))
    assert not unmapped, f"uncategorized aureon/ packages (add to _FS_TO_PRODUCT): {unmapped}"
    # every mapping target is one of the 6 product domains
    assert set(_FS_TO_PRODUCT.values()) <= set(PRODUCT_DOMAINS)

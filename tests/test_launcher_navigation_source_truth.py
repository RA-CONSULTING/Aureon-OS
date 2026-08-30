'''Protect the canonical launcher navigation source of truth.'''

from __future__ import annotations

import json

from scripts.validation import generate_saas_integration_manifest
from scripts.validation import validate_repo_navigation_contract as contract


def test_launcher_navigation_source_truth() -> None:
    expected_launchers = (
        'scripts/launchers/AUREON_PRODUCTION_LIVE.cmd',
        'scripts/launchers/AUREON_WAKE_UP_FULL_AUTONOMOUS.ps1',
        'scripts/launchers/AUREON_DATA_OCEAN.cmd',
        'scripts/launchers/AUREON_DATA_OCEAN.ps1',
    )
    assert expected_launchers == contract.CANONICAL_LAUNCHER_PATHS
    assert contract.collect_launcher_navigation_failures() == []
    assert all((contract.REPO_ROOT / path).is_file() for path in expected_launchers)

    required_by_source = {
        'CAPABILITIES.md': expected_launchers[:3],
        'QUICK_START.md': expected_launchers[:3],
        'RUNNING.md': expected_launchers,
        'docs/REPO_SITEMAP.md': expected_launchers[:3],
        'docs/SAAS_INTEGRATION_READINESS.md': expected_launchers[:2],
        'scripts/validation/generate_saas_integration_manifest.py':
            expected_launchers[:2],
        'docs/end_user_access_map.json':
            (expected_launchers[0], expected_launchers[2]),
        'frontend/public/aureon_end_user_access_map.json':
            (expected_launchers[0], expected_launchers[2]),
        'docs/repo_sitemap.json': (expected_launchers[0],),
        'frontend/public/aureon_repo_sitemap.json':
            (expected_launchers[0], expected_launchers[2]),
    }
    assert required_by_source.keys() == set(contract.LAUNCHER_NAVIGATION_SOURCES)
    for source_path, required_paths in required_by_source.items():
        source = (contract.REPO_ROOT / source_path).read_text(
            encoding='utf-8'
        ).replace('\\', '/')
        assert all(path in source for path in required_paths)

    docs_access = json.loads(contract.DOCS_ACCESS_MAP.read_text(encoding='utf-8'))
    public_access = json.loads(
        contract.PUBLIC_ACCESS_MAP.read_text(encoding='utf-8')
    )
    assert docs_access == public_access

    local_operator = next(
        surface
        for surface in generate_saas_integration_manifest.DEPLOYMENT_SURFACES
        if surface['id'] == 'local_operator'
    )
    assert local_operator['paths'] == [
        expected_launchers[0],
        expected_launchers[1],
        'RUNNING.md',
    ]

    sitemap = contract.REPO_ROOT / 'docs' / 'REPO_SITEMAP.md'
    launcher_links = {
        target
        for target in contract.markdown_link_targets(
            sitemap.read_text(encoding='utf-8')
        )
        if 'AUREON_' in target
    }
    assert launcher_links == {
        '../scripts/launchers/AUREON_PRODUCTION_LIVE.cmd',
        '../scripts/launchers/AUREON_DATA_OCEAN.cmd',
        '../scripts/launchers/AUREON_WAKE_UP_FULL_AUTONOMOUS.ps1',
    }
    assert all((sitemap.parent / target).resolve().is_file()
               for target in launcher_links)

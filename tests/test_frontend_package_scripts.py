'''Regression tests for the frontend package-script safety boundary.'''

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / 'frontend'
PACKAGE_JSON = FRONTEND / 'package.json'
BOUNDED_CLI = ROOT / 'aureon' / 'trading' / 'bounded_binance_roundtrip.py'

UNAVAILABLE_SCRIPTS = {
    'command-server',
    'gamma:sync',
    'gamma:runbook',
    'gamma:report',
    'test:earth',
    'test:nexus',
    'test:paper',
    'test:mc',
    'paper:live',
    'dance',
    'capital',
    'capital:dance',
    'alpaca',
    'alpaca:dance',
    'oanda',
    'oanda:dance',
}

STATIC_SAFE_SCRIPTS = {
    'symphony': ROOT / 'scripts' / 'traders' / 'unifiedSymphony.ts',
    'symphony:500': ROOT / 'scripts' / 'traders' / 'grandSymphony500.ts',
    'validate:secrets': ROOT / 'scripts' / 'traders' / 'validateSecrets.ts',
}


def _scripts() -> dict[str, str]:
    package = json.loads(PACKAGE_JSON.read_text(encoding='utf-8'))
    scripts = package.get('scripts')
    assert isinstance(scripts, dict)
    assert all(
        isinstance(name, str) and isinstance(command, str)
        for name, command in scripts.items()
    )
    return scripts


def test_public_script_names_are_preserved() -> None:
    scripts = _scripts()
    expected_public_names = {
        'dev', 'build', 'build:dev', 'lint', 'lint:shell', 'typecheck',
        'test:e2e', 'preview', 'command-server', 'gamma:sync',
        'gamma:runbook', 'gamma:report', 'test:earth', 'test:nexus',
        'test:paper', 'test:mc', 'paper:live', 'dance', 'trade:real',
        'capital', 'capital:dance', 'alpaca', 'alpaca:dance', 'oanda',
        'oanda:dance', 'symphony', 'symphony:500', 'validate:secrets',
    }
    assert expected_public_names <= scripts.keys()


def test_unavailable_helper_is_deterministic_exit_two() -> None:
    scripts = _scripts()
    assert scripts['unavailable'] == 'node -e process.exitCode=2'

    node = shutil.which('node')
    assert node is not None, 'Node is required by the frontend package'
    completed = subprocess.run(
        [node, '-e', 'process.exitCode=2', 'package-safety-probe'],
        cwd=FRONTEND,
        text=True,
        capture_output=True,
        timeout=10,
        check=False,
    )
    assert completed.returncode == 2
    assert completed.stdout == ''
    assert completed.stderr == ''


def test_unavailable_public_scripts_have_no_legacy_targets() -> None:
    scripts = _scripts()
    for name in UNAVAILABLE_SCRIPTS:
        assert scripts[name] == f'npm run unavailable -- {name}'

    routed = '\n'.join(scripts[name] for name in UNAVAILABLE_SCRIPTS)
    assert 'tsx' not in routed
    assert 'scripts/' not in routed
    assert 'server/' not in routed


def test_static_utilities_have_no_import_network_or_cwd_access() -> None:
    scripts = _scripts()
    tsx_scripts = {
        name: command
        for name, command in scripts.items()
        if command.startswith('tsx ')
    }
    assert tsx_scripts.keys() == STATIC_SAFE_SCRIPTS.keys()
    forbidden = {
        'module import': re.compile(
            r'^\s*(?:import\b|export\b[^\n]*\bfrom\b|.*\brequire\s*\()',
            re.MULTILINE,
        ),
        'network call': re.compile(
            r'\b(?:fetch|axios|WebSocket)\s*\(|'
            r'\bhttps?\s*\.\s*request\s*\('
        ),
        'working-directory access': re.compile(
            r'\b(?:process|Deno)\s*\.\s*(?:cwd|chdir)\s*\('
        ),
    }

    for name, path in STATIC_SAFE_SCRIPTS.items():
        relative = path.relative_to(ROOT).as_posix()
        assert scripts[name] == f'tsx ../{relative}'
        resolved_target = (FRONTEND / scripts[name].split()[1]).resolve()
        assert resolved_target == path.resolve()
        assert resolved_target.is_file()
        source = path.read_text(encoding='utf-8')
        for capability, pattern in forbidden.items():
            assert pattern.search(source) is None, f'{name} gained {capability}'


def test_real_trade_routes_only_to_inert_bounded_cli() -> None:
    scripts = _scripts()
    expected = 'python ../aureon/trading/bounded_binance_roundtrip.py --execute'
    assert scripts['trade:real'] == expected
    assert sum(
        'bounded_binance_roundtrip.py' in command
        for command in scripts.values()
    ) == 1
    assert all('realMoneyTrade' not in command for command in scripts.values())

    completed = subprocess.run(
        [sys.executable, str(BOUNDED_CLI), '--execute'],
        cwd=FRONTEND,
        text=True,
        capture_output=True,
        timeout=15,
        check=False,
    )
    assert completed.returncode == 2
    payload = json.loads(completed.stdout)
    assert payload['reason'] == 'injected_client_and_evidence_suppliers_required'
    assert payload['economic_mutation'] is False
    assert payload['eligible_for_action'] is False

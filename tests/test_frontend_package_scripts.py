'''Regression tests for the frontend package-script terminal HOLD boundary.'''

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / 'frontend'
PACKAGE_JSON = FRONTEND / 'package.json'

UNAVAILABLE_SCRIPTS = {
    'dev',
    'test:e2e',
    'preview',
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
    'trade:real',
    'capital',
    'capital:dance',
    'alpaca',
    'alpaca:dance',
    'oanda',
    'oanda:dance',
    'symphony',
    'symphony:500',
    'validate:secrets',
}

STATIC_SAFE_SCRIPTS = {
    'build': 'vite build',
    'build:dev': 'vite build --mode development',
    'lint': 'eslint .',
    'lint:shell': 'eslint src/shell --max-warnings 0',
    'typecheck': 'tsc -p tsconfig.app.json --noEmit',
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


def test_public_script_names_are_preserved_and_exhaustive() -> None:
    scripts = _scripts()
    assert set(scripts) == (
        UNAVAILABLE_SCRIPTS | set(STATIC_SAFE_SCRIPTS) | {'unavailable'}
    )


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


def test_every_operational_script_routes_to_terminal_hold() -> None:
    scripts = _scripts()
    for name in UNAVAILABLE_SCRIPTS:
        assert scripts[name] == f'npm run unavailable -- {name}'

    routed = '\n'.join(scripts[name] for name in UNAVAILABLE_SCRIPTS)
    for forbidden in (
        'vite preview',
        'playwright',
        'python',
        'tsx',
        'server/',
        'scripts/',
    ):
        assert forbidden not in routed


def test_only_offline_static_build_lint_and_typecheck_remain_active() -> None:
    scripts = _scripts()
    active = {
        name: command
        for name, command in scripts.items()
        if name != 'unavailable' and name not in UNAVAILABLE_SCRIPTS
    }
    assert active == STATIC_SAFE_SCRIPTS

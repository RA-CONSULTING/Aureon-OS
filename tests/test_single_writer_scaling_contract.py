from __future__ import annotations

import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SKIP_DIRS = {
    '.git',
    '.mypy_cache',
    '.pytest_cache',
    '.ruff_cache',
    '.venv',
    '__pycache__',
    'archive',
    'build',
    'data',
    'dist',
    'imports',
    'node_modules',
    'venv',
}

COMPOSE_CLASSES = {
    'docker-compose.yml': {
        'writer': {'command-center', 'trading-engine'},
        'read_only': {'grafana', 'prometheus'},
    },
    'docker-compose.autonomous.yml': {
        'writer': {'aureon-autonomous'},
        'read_only': set(),
    },
    'deploy/docker-compose.operator.yml': {
        'writer': {'aureon-operator'},
        'read_only': set(),
    },
    'deploy/docker-compose.saas.yml': {
        'writer': {'aureon-operator'},
        'read_only': {'frontend'},
    },
    'production/docker-compose.yml': {
        'writer': {'aureon', 'command-center'},
        'read_only': {'grafana', 'prometheus'},
    },
}

APP_CLASSES = {
    '.do/app.yaml': {'aureon-command-center'},
    'app.yaml': {'aureon-power-station'},
}

SUPERVISOR_FILES = {
    'deploy/supervisord.conf',
    'deploy/supervisord.linux.conf',
    'deploy/supervisord.master_launcher.conf',
    'production/supervisord.conf',
    'supervisord.conf',
}

SYSTEMD_FILES = {
    'deploy/micro_profit_labyrinth.service',
    'deploy/orca-kill-cycle.service',
    'deploy/systemd/aureon-hnc.service',
    'deploy/systemd/aureon-operator.service',
    'deploy/systemd/aureon-organism.service',
    'deploy/systemd/aureon-trading.service',
    'deploy/systemd/aureon.service',
}

OPERATOR_PROCESS_KEYS = (
    'AUREON_OPERATOR_HTTP_PROCESSES',
    'AUREON_OPERATOR_REPLICAS',
)

WORKER_FLAG_PATTERNS = (
    re.compile(r'(?i)(?:--workers?|--worker-count)(?:=|\s+)([2-9]\d*)'),
    re.compile(r'(?i)(?:^|\s)-w\s+([2-9]\d*)'),
)

UNSAFE_DOC_PATTERNS = (
    re.compile(r'(?i)\binstance_count\s*:\s*([2-9]\d*)'),
    re.compile(r'(?i)\bmax_instance_count\s*:\s*([2-9]\d*)'),
    re.compile(r'(?i)\breplicas\s*:\s*([2-9]\d*)'),
    re.compile(r'(?i)\bnumprocs\s*=\s*([2-9]\d*)'),
    re.compile(r'(?i)--scale\s+[^\s=]+\s*=\s*([2-9]\d*)'),
    re.compile(r'(?im)^#{1,6}\s+multiple instances\s*$'),
)


def _relative(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def _active_files() -> list[Path]:
    files: list[Path] = []
    for base, directories, names in os.walk(ROOT):
        directories[:] = sorted(
            directory
            for directory in directories
            if directory.lower() not in SKIP_DIRS
        )
        base_path = Path(base)
        files.extend(base_path / name for name in sorted(names))
    return files


def _discover_compose_files() -> set[str]:
    return {
        _relative(path)
        for path in _active_files()
        if path.suffix.lower() in {'.yaml', '.yml'}
        and (
            path.name.lower().startswith('docker-compose')
            or path.name.lower().startswith('compose')
        )
    }


def _discover_app_specs() -> set[str]:
    return {
        _relative(path)
        for path in _active_files()
        if path.name.lower() == 'app.yaml'
    }


def _discover_supervisor_files() -> set[str]:
    return {
        _relative(path)
        for path in _active_files()
        if path.suffix.lower() == '.conf'
        and path.name.lower().startswith('supervisord')
    }


def _discover_systemd_files() -> set[str]:
    return {
        _relative(path)
        for path in _active_files()
        if path.suffix.lower() == '.service' and 'deploy' in path.parts
    }


def _yaml_mapping_children(source: str, parent: str) -> dict[str, str]:
    lines = source.splitlines()
    parent_index = next(
        index
        for index, line in enumerate(lines)
        if line == f'{parent}:'
    )
    starts: list[tuple[str, int]] = []
    child_pattern = re.compile(r'^  ([A-Za-z0-9_.-]+):(?:\s+#.*)?$')
    for index in range(parent_index + 1, len(lines)):
        line = lines[index]
        if line and not line.startswith(' ') and not line.lstrip().startswith('#'):
            break
        match = child_pattern.match(line)
        if match:
            starts.append((match.group(1), index))

    blocks: dict[str, str] = {}
    for position, (name, start) in enumerate(starts):
        end = starts[position + 1][1] if position + 1 < len(starts) else len(lines)
        for index in range(start + 1, end):
            line = lines[index]
            if line and not line.startswith(' ') and not line.lstrip().startswith('#'):
                end = index
                break
        blocks[name] = '\n'.join(lines[start:end])
    return blocks


def _yaml_list_services(source: str) -> dict[str, str]:
    lines = source.splitlines()
    services_index = next(
        index
        for index, line in enumerate(lines)
        if line == 'services:'
    )
    pattern = re.compile(r'^  - name:\s*([A-Za-z0-9_.-]+)\s*$')
    starts: list[tuple[str, int]] = []
    for index in range(services_index + 1, len(lines)):
        line = lines[index]
        if line and not line.startswith(' ') and not line.lstrip().startswith('#'):
            break
        match = pattern.match(line)
        if match:
            starts.append((match.group(1), index))

    blocks: dict[str, str] = {}
    for position, (name, start) in enumerate(starts):
        end = starts[position + 1][1] if position + 1 < len(starts) else len(lines)
        for index in range(start + 1, end):
            line = lines[index]
            if line and not line.startswith(' ') and not line.lstrip().startswith('#'):
                end = index
                break
        blocks[name] = '\n'.join(lines[start:end])
    return blocks


def _nested_yaml_block(source: str, key: str, indent: int) -> str:
    lines = source.splitlines()
    marker = f'{key}:'
    start = next(
        (
            index
            for index, line in enumerate(lines)
            if line == f'{chr(32) * indent}{marker}'
        ),
        None,
    )
    if start is None:
        return ''
    end = len(lines)
    for index in range(start + 1, len(lines)):
        line = lines[index]
        if not line.strip() or line.lstrip().startswith('#'):
            continue
        line_indent = len(line) - len(line.lstrip())
        if line_indent <= indent:
            end = index
            break
    return '\n'.join(lines[start:end])


def _supervisor_programs(source: str) -> dict[str, str]:
    matches = list(re.finditer(r'(?m)^\[program:([^\]]+)\]\s*$', source))
    return {
        match.group(1): source[
            match.start() : matches[index + 1].start()
            if index + 1 < len(matches)
            else len(source)
        ]
        for index, match in enumerate(matches)
    }


def _assert_no_worker_multiplier(source: str, location: str) -> None:
    for pattern in WORKER_FLAG_PATTERNS:
        match = pattern.search(source)
        assert match is None, f'{location} multiplies workers: {match.group(0) if match else None}'


def _unsafe_doc_directives(source: str) -> list[str]:
    findings: list[str] = []
    for pattern in UNSAFE_DOC_PATTERNS:
        findings.extend(match.group(0) for match in pattern.finditer(source))
    return findings


def test_active_deployment_manifest_inventory_is_classified() -> None:
    assert _discover_compose_files() == set(COMPOSE_CLASSES)
    assert _discover_app_specs() == set(APP_CLASSES)
    assert _discover_supervisor_files() == SUPERVISOR_FILES
    assert _discover_systemd_files() == SYSTEMD_FILES


def test_compose_writer_services_are_explicit_singletons() -> None:
    for relative, classes in COMPOSE_CLASSES.items():
        source = (ROOT / relative).read_text(encoding='utf-8')
        services = _yaml_mapping_children(source, 'services')
        expected = classes['writer'] | classes['read_only']
        assert set(services) == expected, f'{relative} has an unclassified service'

        for service_name in classes['writer']:
            block = services[service_name]
            deploy = _nested_yaml_block(block, 'deploy', 4)
            assert deploy, f'{relative}:{service_name} has no deploy singleton'
            assert re.search(
                r'(?m)^      replicas:\s*1\s*(?:#.*)?$',
                deploy,
            ), f'{relative}:{service_name} is not pinned to one replica'
            assert not re.search(
                r'(?m)^\s+(?:autoscaling|scale):\s*',
                block,
            ), f'{relative}:{service_name} enables scaling'


def test_operator_compose_topology_is_one_process_and_one_replica() -> None:
    operator_manifests = (
        'deploy/docker-compose.operator.yml',
        'deploy/docker-compose.saas.yml',
    )
    for relative in operator_manifests:
        source = (ROOT / relative).read_text(encoding='utf-8')
        block = _yaml_mapping_children(source, 'services')['aureon-operator']
        for key in OPERATOR_PROCESS_KEYS:
            assert re.search(
                rf'(?m)^      {key}:\s*[^0-9\n]*1[^0-9\n]*$',
                block,
            ), f'{relative} must set {key}=1'


def test_digitalocean_writer_services_have_no_autoscaler() -> None:
    for relative, writer_services in APP_CLASSES.items():
        source = (ROOT / relative).read_text(encoding='utf-8')
        services = _yaml_list_services(source)
        assert set(services) == writer_services
        for service_name, block in services.items():
            assert re.search(
                r'(?m)^    instance_count:\s*1\s*(?:#.*)?$',
                block,
            ), f'{relative}:{service_name} must have instance_count 1'
            assert not re.search(
                r'(?m)^    autoscaling:\s*$',
                block,
            ), f'{relative}:{service_name} must not autoscale'


def test_supervisord_programs_never_multiply_processes() -> None:
    operator_programs = 0
    for relative in sorted(SUPERVISOR_FILES):
        source = (ROOT / relative).read_text(encoding='utf-8')
        programs = _supervisor_programs(source)
        assert programs, f'{relative} has no program sections'
        for program_name, block in programs.items():
            declared = re.findall(r'(?m)^numprocs\s*=\s*([^\s;#]+)', block)
            assert len(declared) <= 1
            if declared:
                assert declared == ['1'], f'{relative}:{program_name} has numprocs {declared[0]}'
            _assert_no_worker_multiplier(block, f'{relative}:{program_name}')
            if 'aureon.operator.operator_server' in block:
                operator_programs += 1
                assert declared == ['1'], f'{relative}:{program_name} must be explicit'
    assert operator_programs == 3


def test_systemd_worker_units_are_single_process_manifests() -> None:
    for relative in sorted(SYSTEMD_FILES):
        source = (ROOT / relative).read_text(encoding='utf-8')
        assert '@' not in Path(relative).name, f'{relative} is a scalable template unit'
        _assert_no_worker_multiplier(source, relative)

    operator_source = (
        ROOT / 'deploy/systemd/aureon-operator.service'
    ).read_text(encoding='utf-8')
    environment_file_offset = operator_source.index('EnvironmentFile=')
    for key in OPERATOR_PROCESS_KEYS:
        match = re.search(
            rf'(?m)^Environment={key}=1\s*$',
            operator_source,
        )
        assert match
        assert match.start() > environment_file_offset


def test_procfile_has_one_unmultiplied_process_type() -> None:
    source = (ROOT / 'Procfile').read_text(encoding='utf-8')
    entries = [
        line
        for line in source.splitlines()
        if line.strip() and not line.lstrip().startswith('#')
    ]
    assert len(entries) == 1
    assert entries[0].startswith('web:')
    _assert_no_worker_multiplier(source, 'Procfile')


def test_deployment_docs_do_not_recommend_multiple_writers() -> None:
    paths = sorted((ROOT / 'docs' / 'deployment').glob('*.md'))
    paths.extend(sorted((ROOT / 'docs' / 'runbooks').glob('*.md')))
    findings: dict[str, list[str]] = {}
    for path in paths:
        unsafe = _unsafe_doc_directives(path.read_text(encoding='utf-8'))
        if unsafe:
            findings[_relative(path)] = unsafe
    assert findings == {}

    runbook = (
        ROOT / 'docs/runbooks/SINGLE_WRITER_SCALING.md'
    ).read_text(encoding='utf-8')
    runbook_lower = runbook.lower()
    for required in (
        'leader election with fencing',
        'globally unique idempotency',
        'shared provider-aware rate limits',
        'local static validation is not provider read-back',
    ):
        assert required in runbook_lower


def test_unsafe_document_detector_is_not_vacuous() -> None:
    samples = (
        'instance_count: 2',
        'max_instance_count: 4',
        'replicas: 3',
        'numprocs=8',
        'docker compose up --scale trader=2',
        '### Multiple Instances',
    )
    for sample in samples:
        assert _unsafe_doc_directives(sample), sample

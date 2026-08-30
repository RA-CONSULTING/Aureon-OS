"""Synthetic-only tests for the state-safe pytest shard harness."""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from scripts.validation import pytest_no_skip_shards as harness

PLUGIN_INVENTORY = [
    {
        "distribution": "pytest-asyncio",
        "entry_point": "asyncio",
        "module": "pytest_asyncio.plugin",
        "version": "1.0",
    },
    {
        "distribution": "pytest-socket",
        "entry_point": "socket",
        "module": "pytest_socket",
        "version": "1.0",
    },
]


def _repo(tmp_path: Path) -> Path:
    (tmp_path / "tests").mkdir()
    (tmp_path / "state").mkdir()
    (tmp_path / "pyproject.toml").write_text(
        '[tool.pytest.ini_options]\ntestpaths = ["tests"]\n', encoding="utf-8"
    )
    return tmp_path


def _items(*file_counts: tuple[str, int]) -> list[dict[str, str]]:
    return [
        {"node_id": f"{source_file}::test_{index}", "source_file": source_file}
        for source_file, count in file_counts
        for index in range(count)
    ]


def _plugin_report(
    items: Sequence[Mapping[str, str]],
    *,
    collection_errors: Sequence[Mapping[str, str]] = (),
    collection_skips: Sequence[Mapping[str, str]] = (),
    runtime_skip_count: int = 0,
) -> dict[str, Any]:
    return {
        "collection_errors": list(collection_errors),
        "collection_skips": list(collection_skips),
        "items": [dict(item) for item in items],
        "loaded_plugins": [
            {
                "distribution": "pytest-socket",
                "module": "pytest_socket",
                "registered_as": "socket",
                "version": "1.0",
            }
        ],
        "pytest_exitstatus": 0,
        "runtime_phases": [],
        "runtime_skip_count": runtime_skip_count,
        "schema": harness.SCHEMA,
        "socket_blocker_loaded": True,
        "socket_blocking_requested": True,
    }


def _report_path(argv: Sequence[str]) -> Path:
    argument = next(part for part in argv if part.startswith(f"{harness.REPORT_OPTION}="))
    return Path(argument.split("=", 1)[1])


def _stub_runner(
    report_factory: Callable[[Sequence[str]], Mapping[str, Any]],
    *,
    mutate: Callable[[Path], None] | None = None,
    calls: list[tuple[tuple[str, ...], Mapping[str, str]]] | None = None,
    returncode: int = 0,
) -> harness.Runner:
    def run(
        argv: Sequence[str],
        cwd: Path,
        env: Mapping[str, str],
        timeout_seconds: float | None,
    ) -> harness.ProcessCapture:
        del timeout_seconds
        if calls is not None:
            calls.append((tuple(argv), dict(env)))
        report_path = _report_path(argv)
        report_path.write_text(json.dumps(report_factory(argv)), encoding="utf-8")
        if mutate is not None:
            mutate(cwd)
        return harness.ProcessCapture(
            argv=tuple(argv),
            returncode=returncode,
            stdout="synthetic stdout",
            stderr="synthetic stderr",
            duration_seconds=0.25,
        )

    return run


def _manifest(
    root: Path,
    items: Sequence[Mapping[str, str]],
    *,
    shard_count: int,
    collection_skips: Sequence[Mapping[str, str]] = (),
) -> dict[str, Any]:
    return harness.build_manifest(
        root=root,
        config_path=root / "pyproject.toml",
        collection_targets=("tests",),
        shard_count=shard_count,
        plugin_inventory=PLUGIN_INVENTORY,
        plugin_report=_plugin_report(items, collection_skips=collection_skips),
        baseline=harness.fingerprint_operational_paths(root),
    )


def test_safe_environment_scrubs_credentials_and_keeps_plugin_autoload() -> None:
    safe, scrubbed = harness.safe_subprocess_environment(
        {
            "PATH": "synthetic-path",
            "BINANCE_API_KEY": "binance-secret",
            "CAPITAL_DEMO": "false",
            "CUSTOM_PASSWORD": "password-secret",
            "GOOGLE_APPLICATION_CREDENTIALS": "credential-file.json",
            "OPENAI_API_KEY": "openai-secret",
            "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
            "PYTEST_PLUGINS": "uncontrolled.plugin",
            "TELEGRAM_BOT_TOKEN": "telegram-secret",
            "SAFE_VALUE": "kept",
        }
    )

    assert safe["PATH"] == "synthetic-path"
    assert safe["SAFE_VALUE"] == "kept"
    assert safe["AUREON_AUDIT_MODE"] == "1"
    assert safe["AUREON_LIVE_TRADING"] == "0"
    assert safe["AUREON_OBSERVER_MODE"] == "dry_run"
    assert safe["DRY_RUN"] == "1"
    assert safe["CAPITAL_DEMO"] == "true"
    assert safe["HTTP_PROXY"] == "http://127.0.0.1:9"
    assert safe["PYTHON_DOTENV_DISABLED"] == "1"
    assert "PYTEST_DISABLE_PLUGIN_AUTOLOAD" not in safe
    assert "PYTEST_PLUGINS" not in safe
    assert not any("secret" in value for value in safe.values())
    assert set(scrubbed) == {
        "BINANCE_API_KEY",
        "CAPITAL_DEMO",
        "CUSTOM_PASSWORD",
        "GOOGLE_APPLICATION_CREDENTIALS",
        "OPENAI_API_KEY",
        "PYTEST_DISABLE_PLUGIN_AUTOLOAD",
        "PYTEST_PLUGINS",
        "TELEGRAM_BOT_TOKEN",
    }


def test_pytest_socket_is_a_hard_preflight() -> None:
    with pytest.raises(harness.HarnessError, match="pytest-socket is required"):
        harness.require_pytest_socket([PLUGIN_INVENTORY[0]])
    harness.require_pytest_socket(PLUGIN_INVENTORY)


def test_manifest_is_canonical_and_lpt_assignment_is_disjoint_exhaustive(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    items = _items(
        ("tests/test_heavy.py", 3),
        ("tests/test_medium.py", 2),
        ("tests/test_light.py", 1),
    )
    skips = [{"node_id": "tests/test_optional.py", "reason": "optional dependency absent"}]

    first = _manifest(root, items, shard_count=2, collection_skips=skips)
    second = _manifest(root, list(reversed(items)), shard_count=2, collection_skips=skips)

    assert first == second
    assert first["shards"][0]["files"] == ["tests/test_heavy.py"]
    assert first["shards"][1]["files"] == ["tests/test_light.py", "tests/test_medium.py"]
    assert [shard["item_count"] for shard in first["shards"]] == [3, 3]
    assert first["proofs"]["disjoint"] is True
    assert first["proofs"]["exhaustive"] is True
    assert first["proofs"]["assigned_item_count"] == 6
    assert first["collection"]["collection_skip_count"] == 1
    assert harness.verify_manifest(first)["manifest_sha256"] == first["manifest_sha256"]


def test_collection_errors_are_distinct_from_reported_collection_skips(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    items = _items(("tests/test_a.py", 1))
    skipped = _manifest(
        root,
        items,
        shard_count=1,
        collection_skips=[{"node_id": "tests/test_optional.py", "reason": "declared skip"}],
    )
    assert skipped["collection"]["collection_skip_count"] == 1

    with pytest.raises(harness.HarnessError, match="collection reported 1 error"):
        harness.build_manifest(
            root=root,
            config_path=root / "pyproject.toml",
            collection_targets=("tests",),
            shard_count=1,
            plugin_inventory=PLUGIN_INVENTORY,
            plugin_report=_plugin_report(
                items,
                collection_errors=[{"node_id": "tests/test_bad.py", "reason": "SyntaxError"}],
            ),
            baseline=harness.fingerprint_operational_paths(root),
        )


def test_manifest_only_uses_controlled_pytest_command_and_stubbed_report(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    (root / "tests" / "test_a.py").write_text("def test_a(): pass\n", encoding="utf-8")
    manifest_path = root / "artifacts" / "shards.json"
    calls: list[tuple[tuple[str, ...], Mapping[str, str]]] = []
    items = _items(("tests/test_a.py", 1))
    runner = _stub_runner(lambda _argv: _plugin_report(items), calls=calls)

    manifest = harness.collect_and_write_manifest(
        root=root,
        config_path=root / "pyproject.toml",
        manifest_path=manifest_path,
        shard_count=1,
        runner=runner,
        plugin_inventory=PLUGIN_INVENTORY,
    )

    assert manifest_path.is_file()
    receipt_path = manifest_path.with_name("shards.json.collection-receipt.json")
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert manifest["proofs"]["collected_item_count"] == 1
    assert receipt["process"]["stdout"] == "synthetic stdout"
    assert receipt["process"]["stderr"] == "synthetic stderr"
    assert receipt["process"]["duration_seconds"] == 0.25
    assert receipt["state_mutation_detected"] is False

    argv, env = calls[0]
    assert argv[:3] == (harness.sys.executable, "-m", "pytest")
    assert argv[argv.index("--rootdir") + 1] == str(root)
    assert argv[argv.index("-c") + 1] == str(root / "pyproject.toml")
    assert argv[argv.index("-p") + 1] == harness.PLUGIN_MODULE
    assert "--disable-socket" in argv
    assert "--collect-only" in argv
    assert "tests" in argv
    assert "PYTEST_DISABLE_PLUGIN_AUTOLOAD" not in env
    assert env["AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS"] == "1"
    assert env["ALL_PROXY"] == "http://127.0.0.1:9"


def test_shard_mutation_is_preserved_and_blocks_every_later_shard(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    (root / "tests" / "test_a.py").write_text("", encoding="utf-8")
    (root / "tests" / "test_b.py").write_text("", encoding="utf-8")
    thoughts = root / "thoughts.jsonl"
    thoughts.write_text("before\n", encoding="utf-8")
    items = _items(("tests/test_a.py", 1), ("tests/test_b.py", 1))
    manifest = _manifest(root, items, shard_count=2)
    manifest_path = root / "artifacts" / "shards.json"
    harness._write_new_json(manifest_path, manifest)
    calls: list[tuple[tuple[str, ...], Mapping[str, str]]] = []

    def mutate(repo: Path) -> None:
        with (repo / "thoughts.jsonl").open("a", encoding="utf-8") as handle:
            handle.write("mutated\n")

    expected = manifest["shards"][0]["node_ids"]
    runner = _stub_runner(
        lambda _argv: _plugin_report(
            [{"node_id": node_id, "source_file": "tests/test_a.py"} for node_id in expected]
        ),
        mutate=mutate,
        calls=calls,
    )
    receipt = harness.execute_one_shard(
        root=root,
        manifest_path=manifest_path,
        shard_index=1,
        runner=runner,
        plugin_inventory=PLUGIN_INVENTORY,
    )

    assert receipt["status"] == "state_mutation_detected"
    assert receipt["state_mutation_detected"] is True
    assert receipt["operational_state_changes"][0]["path"] == "thoughts.jsonl"
    assert thoughts.read_text(encoding="utf-8") == "before\nmutated\n"
    assert len(calls) == 1

    with pytest.raises(harness.HarnessError, match="further shards are blocked"):
        harness.execute_one_shard(
            root=root,
            manifest_path=manifest_path,
            shard_index=2,
            runner=runner,
            plugin_inventory=PLUGIN_INVENTORY,
        )
    assert len(calls) == 1
    assert thoughts.read_text(encoding="utf-8") == "before\nmutated\n"


def test_collection_mutation_writes_terminal_receipt_but_no_manifest(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    (root / "tests" / "test_a.py").write_text("", encoding="utf-8")
    thoughts = root / "thoughts.jsonl"
    thoughts.write_text("before\n", encoding="utf-8")
    manifest_path = root / "artifacts" / "shards.json"
    items = _items(("tests/test_a.py", 1))

    def mutate(repo: Path) -> None:
        with (repo / "thoughts.jsonl").open("a", encoding="utf-8") as handle:
            handle.write("collection mutation\n")

    runner = _stub_runner(lambda _argv: _plugin_report(items), mutate=mutate)
    with pytest.raises(harness.HarnessError, match="state changed during pytest collection"):
        harness.collect_and_write_manifest(
            root=root,
            config_path=root / "pyproject.toml",
            manifest_path=manifest_path,
            shard_count=1,
            runner=runner,
            plugin_inventory=PLUGIN_INVENTORY,
        )

    receipt_path = manifest_path.with_name("shards.json.collection-receipt.json")
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert not manifest_path.exists()
    assert receipt["state_mutation_detected"] is True
    assert receipt["operational_state_changes"][0]["path"] == "thoughts.jsonl"
    assert thoughts.read_text(encoding="utf-8") == "before\ncollection mutation\n"


def test_collection_skip_is_terminal_and_writes_no_manifest(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    (root / "tests" / "test_optional.py").write_text("", encoding="utf-8")
    manifest_path = root / "artifacts" / "shards.json"
    items = _items(("tests/test_optional.py", 1))
    runner = _stub_runner(
        lambda _argv: _plugin_report(
            items,
            collection_skips=[{"node_id": "tests/test_optional.py", "reason": "optional"}],
        )
    )

    with pytest.raises(harness.HarnessError, match="collection reported 1 skip"):
        harness.collect_and_write_manifest(
            root=root,
            config_path=root / "pyproject.toml",
            manifest_path=manifest_path,
            shard_count=1,
            runner=runner,
            plugin_inventory=PLUGIN_INVENTORY,
        )

    assert not manifest_path.exists()


def test_runtime_writers_are_isolated_under_the_ephemeral_root(tmp_path: Path) -> None:
    environment = harness.isolate_runtime_writers({"UNCHANGED": "yes"}, tmp_path)

    assert environment["UNCHANGED"] == "yes"
    assert Path(environment["AUREON_THOUGHT_BUS_PATH"]).parent == tmp_path
    assert Path(environment["AUREON_BUS_TRACE_DIR"]).parent == tmp_path
    assert Path(environment["AUREON_HNC_TRACE_PATH"]).parent == tmp_path


def test_one_shard_makes_runtime_skip_terminal_without_hiding_it(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    (root / "tests" / "test_optional.py").write_text("", encoding="utf-8")
    items = _items(("tests/test_optional.py", 1))
    manifest = _manifest(root, items, shard_count=1)
    manifest_path = root / "artifacts" / "shards.json"
    harness._write_new_json(manifest_path, manifest)
    runner = _stub_runner(lambda _argv: _plugin_report(items, runtime_skip_count=1))

    receipt = harness.execute_one_shard(
        root=root,
        manifest_path=manifest_path,
        shard_index=1,
        runner=runner,
        plugin_inventory=PLUGIN_INVENTORY,
    )

    assert receipt["status"] == "runtime_skips_detected"
    assert receipt["runtime_skip_count"] == 1
    assert receipt["process"]["returncode"] == 0
    assert receipt["process"]["stdout"] == "synthetic stdout"
    assert receipt["selection_changes"] == {"missing": [], "unexpected": []}
    assert (
        harness.verify_existing_manifest(
            root=root,
            manifest_path=manifest_path,
            plugin_inventory=PLUGIN_INVENTORY,
        )["operational_state_matches"]
        is True
    )


def test_manifest_digest_and_recomputed_lpt_both_reject_tampering(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    manifest = _manifest(
        root,
        _items(("tests/test_a.py", 2), ("tests/test_b.py", 1)),
        shard_count=2,
    )
    digest_tampered = json.loads(json.dumps(manifest))
    digest_tampered["shard_count"] = 1
    with pytest.raises(harness.HarnessError, match="digest mismatch"):
        harness.verify_manifest(digest_tampered)

    assignment_tampered = json.loads(json.dumps(manifest))
    assignment_tampered["shards"].reverse()
    unsigned = dict(assignment_tampered)
    unsigned.pop("manifest_sha256")
    assignment_tampered["manifest_sha256"] = harness._sha256_bytes(harness._canonical_bytes(unsigned))
    with pytest.raises(harness.HarnessError, match="canonical LPT"):
        harness.verify_manifest(assignment_tampered)


def test_plugin_hooks_capture_reports_without_nonexistent_report_config_attribute() -> None:
    config = SimpleNamespace()
    harness.pytest_configure(config)
    collection_report = SimpleNamespace(
        failed=True,
        skipped=False,
        nodeid="tests/test_bad.py",
        longrepr="synthetic collection error",
    )
    runtime_report = SimpleNamespace(
        duration=0.1,
        nodeid="tests/test_a.py::test_a",
        outcome="skipped",
        wasxfail="declared",
        when="setup",
    )

    harness.pytest_collectreport(collection_report)
    harness.pytest_runtest_logreport(runtime_report)

    state = config._aureon_shard_report_state
    assert state["collection_errors"][0]["node_id"] == "tests/test_bad.py"
    assert state["runtime_phases"][0]["outcome"] == "skipped"
    harness.pytest_unconfigure(config)

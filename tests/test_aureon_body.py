"""Full-body caller. Depth is a real call. A listed row is not depth."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

# Populated by tests/conftest.py before tests in this module run (not at collection time).
body_call: object
body_call_operator: object
body_registry: object
body_surface: object
enabled_stage: object
checkout_blob_refusal: object
PINNED_COMMIT: str
repo_root: object

pytestmark = pytest.mark.timeout(180)


def _load(text: str) -> dict:
    return json.loads(text)


def test_stage1_calls_real_entry_points_and_names_auris() -> None:
    ladder = _load(
        body_call(
            "alignment/harmonic_resonance.py",
            "consonance_score",
            json.dumps({"ratio": 1.0}),
        )
    )
    assert ladder["status"] == "cited"
    assert ladder["called"] is True
    assert ladder["label"].startswith("cited.")
    assert not ladder["label"].startswith("helper.")
    assert "consciousness_" not in json.dumps(ladder)

    closed = _load(body_call("harmonic/rainbow_reference.py", "solfeggio_ladder"))
    assert closed["status"] == "unavailable"
    assert closed.get("called") is not True
    assert closed["reason"] == "plan stage 4 is not open"

    substrate = _load(
        body_call(
            "harmonic/aureon_harmonic_reality.py",
            "HarmonicSubstrate.evaluate",
            json.dumps({"t": 0.0}),
        )
    )
    assert substrate["status"] == "unavailable"
    assert substrate.get("called") is not True
    from aureon_public.body import _constructor_refusal

    assert _constructor_refusal("harmonic/aureon_harmonic_reality.py", "HarmonicSubstrate")

    nodes = _load(body_call("utils/aureon_queen_hive_mind.py", "QueenHiveMind.read_auris_nodes"))
    assert nodes["status"] == "unavailable"
    assert nodes.get("called") is not True

    analyzer = _load(body_call("wisdom/aureon_qgita_framework.py", "get_qgita_analyzer"))
    assert analyzer["status"] == "unavailable"
    assert analyzer.get("called") is not True
    assert analyzer["reason"] == "plan stage 4 is not open"


def test_public_call_refuses_operator_orders_and_blocked_packages() -> None:
    order = _load(
        body_call(
            "harmonic/hnc_quantum_packet_crypto.py",
            "packet_master_key_from_env",
        )
    )
    assert order["status"] == "unavailable"
    assert order.get("called") is not True
    loop = _load(body_call("harmonic/aureon_harmonic_momentum_wave.py", "run_continuous_scan"))
    assert loop["status"] == "unavailable"
    blocked = _load(body_call("trading/__init__.py", "__init__"))
    assert blocked["status"] == "unavailable"
    assert blocked.get("live_orders") == "refused"


def test_surface_does_not_call_and_a_changed_blob_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    surface = _load(body_surface("harmonic/aureon_harmonic_reality.py", "HarmonicSubstrate"))
    assert surface.get("called") is not True
    assert surface["status"] == "unavailable"
    assert enabled_stage() >= 1

    real = repo_root() / "aureon" / "alignment" / "harmonic_resonance.py"
    assert checkout_blob_refusal(real, repo_root(), PINNED_COMMIT) is None

    import aureon_public.pin_blob as pin

    real_hash = pin.git_blob_sha1

    def fake(data: bytes) -> str:
        if b"def consonance_score" in data:
            return "ab" * 20
        return real_hash(data)

    monkeypatch.setattr(pin, "git_blob_sha1", fake)
    refused = _load(
        body_call(
            "alignment/harmonic_resonance.py",
            "consonance_score",
            json.dumps({"ratio": 1.0}),
        )
    )
    assert refused["status"] == "unavailable"
    assert "differs from pin" in refused["reason"]


def test_readme_and_stage_reports_match_the_inventory_depth() -> None:
    from aureon_public.body import package_depth, render_readme_depth

    readme = (ROOT / "mcp" / "aureon_public" / "README.md").read_text(encoding="utf-8")
    assert render_readme_depth() in readme
    assert readme.splitlines()[14] == (
        "A layer counts as full depth only where its real entry points are called."
    )
    assert "The extra package tools are helpers." in readme
    for stage in range(1, 7):
        record = json.loads((ROOT / "measured" / f"body_stage{stage}.json").read_text(encoding="utf-8"))
        assert record["entry_points"] == package_depth(stage)
        for row in record["entry_points"].values():
            assert row["reachable"] <= row["public_entry_points"]


def test_stage7_registry_names_servers_spaces_and_the_pin() -> None:
    body = _load(body_registry())
    assert body["status"] == "cited"
    assert body.get("called") is not True
    assert body["live_orders"] == "refused"
    assert body["enabled_through"] == enabled_stage()
    assert body["pin"].startswith("8aa6a2d9")
    assert "huggingface/hnc-field/app.py" in body["spaces"]
    assert "trading" in body["blocked_imports"]
    registry = (ROOT / "docs" / "mcp" / "REGISTRY.md").read_text(encoding="utf-8")
    assert "body_call" in registry
    assert "enforce_public_pin" in registry
    readme = (ROOT / "mcp" / "aureon_public" / "README.md").read_text(encoding="utf-8")
    assert "body_call" in readme
    assert "helper" in readme


def test_stage6_calls_the_remaining_public_readers() -> None:
    assert enabled_stage() >= 6
    rank = _load(body_call("briefing/schemas.py", "severity_rank", json.dumps({"severity": "high"})))
    assert rank["status"] == "unavailable"
    assert rank.get("called") is not True
    assert rank["reason"] == "plan stage 4 is not open"
    color = _load(body_call("simulation/aureon_world_simulator.py", "hz_to_rgb", json.dumps({"hz": 528})))
    assert color["status"] == "unavailable"
    assert color.get("called") is not True
    assert color["reason"] == "plan stage 4 is not open"
    record = json.loads((ROOT / "measured" / "body_stage6.json").read_text(encoding="utf-8"))
    called = {item["package"] for item in record["calls"] if item["called"] is True}
    assert {
        "approval",
        "briefing",
        "grants",
        "integrations",
        "intelligence",
        "plumber",
        "s51",
        "simulation",
    } <= called


def test_stage5_operator_refuses_blocked_imports_and_calls_two_readers(monkeypatch: pytest.MonkeyPatch) -> None:
    assert enabled_stage() >= 5
    monkeypatch.setenv("AUREON_OPERATOR_MCP", "1")
    monkeypatch.setenv("AUREON_DISABLE_REAL_ORDERS", "1")
    ingestors = _load(body_call_operator("accounting/file_drop.py", "registered_ingestors"))
    assert ingestors["called"] is True
    assert "bank_csv" in ingestors["result"]
    days = _load(body_call_operator("portfolio/aureon_billion_goal_tracker.py", "get_days_remaining"))
    assert days["called"] is True
    assert isinstance(days["result"], float)
    blocked = (
        ("trading/__init__.py", "__init__"),
        ("exchanges/__init__.py", "__init__"),
        ("bots/__init__.py", "__init__"),
        ("bots_intelligence/__init__.py", "__init__"),
        ("bridges/__init__.py", "__init__"),
        ("scanners/__init__.py", "__init__"),
        ("unified_margin_trader/_margin_monitor.py", "_margin_monitor"),
    )
    for module, symbol in blocked:
        body = _load(body_call_operator(module, symbol))
        assert body["live_orders"] == "refused", symbol
        assert body.get("called") is not True
        public = _load(body_call(module, symbol))
        assert public["live_orders"] == "refused"
    record = json.loads((ROOT / "measured" / "body_stage5.json").read_text(encoding="utf-8"))
    called = {item["package"] for item in record["calls"] if item["called"] is True}
    assert {"accounting", "portfolio"} <= called
    assert "trading" not in called


def test_stage4_calls_feed_decoder_search_portal_analytics_atn_and_monitor() -> None:
    assert enabled_stage() >= 4
    distance = _load(
        body_call(
            "decoders/grail_convergence.py",
            "haversine",
            json.dumps({"lat1": 51.5, "lon1": -0.12, "lat2": 48.86, "lon2": 2.35}),
        )
    )
    assert distance["status"] == "unavailable"
    assert distance.get("called") is not True
    assert distance["reason"] == "module import loads an adapter or http client"
    impacts = _load(
        body_call(
            "atn/aureon_atn_backtest.py",
            "compute_impacts",
            json.dumps({"events": [], "candles": [], "symbol": "BTC"}),
        )
    )
    assert impacts["status"] == "unavailable"
    assert impacts.get("called") is not True
    record = json.loads((ROOT / "measured" / "body_stage4.json").read_text(encoding="utf-8"))
    called = {item["package"] for item in record["calls"] if item["called"] is True}
    assert {"data_feeds", "decoders", "search", "portals", "analytics", "atn"} <= called


def test_stage3_calls_organism_bio_evaluation_and_vault_and_refuses_identity() -> None:
    assert enabled_stage() >= 3
    words = _load(
        body_call(
            "vault/voice/document_artifact_skill.py",
            "count_words",
            json.dumps({"text": "one two three"}),
        )
    )
    assert words["status"] == "unavailable"
    assert words.get("called") is not True
    assert words["reason"] == "plan stage 4 is not open"
    layers = _load(body_call("organism/repository_layers.py", "compose_repository_layers"))
    assert layers["status"] == "unavailable"
    assert layers.get("called") is not True
    assert layers["reason"] == "plan stage 4 is not open"
    nodes = _load(body_call("evaluation/auris_node_eval.py", "evaluate_auris_nodes"))
    assert nodes["status"] == "unavailable"
    assert nodes.get("called") is not True
    identity = _load(body_call("identity/reader.py", "read_identity"))
    assert identity["status"] == "unavailable"
    assert identity.get("called") is not True
    record = json.loads((ROOT / "measured" / "body_stage3.json").read_text(encoding="utf-8"))
    called = {item["package"] for item in record["calls"] if item["called"] is True}
    assert {"bio", "organism", "evaluation", "vault", "core"} <= called


def test_body_call_refuses_sibling_join_and_build_lane(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Side-by-side NEXUS and Sero checkouts are not exec'd and no request is built."""

    import urllib.request

    from aureon_public.body import dispatch

    requests: list[str] = []

    def capture(url: object, *args: object, **kwargs: object) -> None:
        requests.append(str(url))
        raise AssertionError(f"urllib request for {url}")

    monkeypatch.setattr(urllib.request, "Request", capture)
    monkeypatch.setattr(urllib.request, "urlopen", capture)

    beside = Path(repo_root()).resolve().parent
    marker = tmp_path / "sibling-exec.txt"
    field = (
        "from pathlib import Path\n"
        "from urllib.request import Request, urlopen\n"
        f"Path({str(marker)!r}).write_text('field')\n"
        "Request('https://services.swpc.noaa.gov/products/noaa-planetary-k-index.json')\n"
        "SOURCE = 'https://services.swpc.noaa.gov/products/noaa-planetary-k-index.json'\n"
        "def observe_planetary_k_index(transport=None):\n"
        "    Request(SOURCE)\n"
        "    if transport is None:\n"
        "        return urlopen(SOURCE).read()\n"
        "    return transport(SOURCE)\n"
    )
    market = (
        "from pathlib import Path\n"
        "from urllib.request import Request, urlopen\n"
        f"Path({str(marker)!r}).write_text('market')\n"
        "Request('https://data-api.binance.vision/api/v3/ticker/price?symbol=BTCUSDT')\n"
        "SOURCE = 'https://data-api.binance.vision/api/v3/ticker/price?symbol=BTCUSDT'\n"
        "def observe_public_price(transport=None):\n"
        "    Request(SOURCE)\n"
        "    if transport is None:\n"
        "        return urlopen(SOURCE).read()\n"
        "    return transport(SOURCE)\n"
    )

    def write_sibling(path: Path, text: str) -> None:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
        except PermissionError:
            subprocess.check_call(["sudo", "-n", "mkdir", "-p", str(path.parent)])
            subprocess.check_call(
                ["sudo", "-n", "chown", "-R", f"{os.getuid()}:{os.getgid()}", str(path.parents[1])]
            )
            path.write_text(text, encoding="utf-8")

    def remove_tree(path: Path) -> None:
        import shutil

        if not path.exists():
            return
        try:
            shutil.rmtree(path)
        except PermissionError:
            subprocess.check_call(["sudo", "-n", "rm", "-rf", str(path)])

    planted: list[Path] = []
    layouts = (
        ("NEXUS-LIVE-FEED-", "organism/public_field.py", field),
        ("Aureon-Trading--Project-Sero", "organism/public_market.py", market),
    )
    try:
        for name, relative, text in layouts:
            root = beside / name
            if root.exists():
                continue
            planted.append(root)
            write_sibling(root.joinpath(*relative.split("/")), text)
        assert len(planted) == 2 or all((beside / name).exists() for name, _relative, _text in layouts)
        targets = (
            ("organism/repository_layers.py", "compose_repository_layers", {}),
            ("swarm/capability_grid.py", "build_lane", {"name": "fintech"}),
        )
        for module, symbol, arguments in targets:
            via_call = _load(body_call(module, symbol))
            via_dispatch = _load(dispatch(module, symbol, arguments, server="public"))
            for body in (via_call, via_dispatch):
                assert body["status"] == "unavailable", (module, symbol, body)
                assert body.get("called") is not True
                expected = (
                    "plan stage 4 is not open"
                    if module.startswith("organism/")
                    else "stage 4 entry point is not called"
                )
                assert body["reason"] == expected
        assert requests == []
        assert not marker.exists()
        assert "nexus_public_field" not in sys.modules
        assert "sero_public_market" not in sys.modules
    finally:
        for path in planted:
            remove_tree(path)


def test_get_unified_directive_does_not_open_a_socket(monkeypatch: pytest.MonkeyPatch) -> None:
    """The no-argument call builds queen and miner bridges, so body_call refuses it."""

    import socket
    import subprocess as subprocess_module

    opened: list[object] = []
    popens: list[object] = []

    class _Guard(socket.socket):
        def connect(self, address: object, *args: object, **kwargs: object) -> None:
            opened.append(address)
            raise OSError("socket blocked")

        def connect_ex(self, address: object, *args: object, **kwargs: object) -> int:
            opened.append(address)
            raise OSError("socket blocked")

    def _create_connection(*args: object, **kwargs: object) -> object:
        opened.append(args)
        raise OSError("socket blocked")

    real_popen = subprocess_module.Popen

    def _popen(*args: object, **kwargs: object) -> object:
        command = args[0] if args else kwargs.get("args")
        text = " ".join(str(part) for part in command) if isinstance(command, (list, tuple)) else str(command)
        if "call_worker" in text:
            popens.append(text)
        return real_popen(*args, **kwargs)

    monkeypatch.setattr(socket, "socket", _Guard)
    monkeypatch.setattr(socket, "create_connection", _create_connection)
    monkeypatch.setattr(subprocess_module, "Popen", _popen)
    body = _load(body_call("alignment/unified_directive.py", "get_unified_directive"))
    assert body["status"] == "unavailable"
    assert body.get("called") is not True
    assert body["reason"] == "call loads a banned chain or opens a connection"
    assert opened == []
    assert popens == []


def test_checkout_aureon_tree_equals_the_pin() -> None:
    import subprocess

    from aureon_public.guard_loader import PINNED_COMMIT
    from aureon_public.measurement_stamp import PIN_AUREON_TREE, pin_tree_skip_reason
    from aureon_public.paths import repo_root

    root_path = repo_root()
    reason = pin_tree_skip_reason(root_path)
    if reason:
        pytest.skip(reason)
    root = str(root_path)

    def rev_parse(*args: str) -> str:
        return subprocess.check_output(["git", "-C", root, *args], text=True).strip()

    assert rev_parse("rev-parse", f"{PINNED_COMMIT}:aureon") == PIN_AUREON_TREE
    assert rev_parse("rev-parse", "HEAD:aureon") == PIN_AUREON_TREE
    diff = subprocess.run(
        ["git", "-C", root, "diff", "--quiet", PINNED_COMMIT, "--", "aureon"],
        check=False,
    )
    assert diff.returncode == 0


def test_pin_tree_check_skips_without_git_shallow_or_a_missing_pin(tmp_path: Path) -> None:
    from aureon_public.measurement_stamp import pin_tree_skip_reason

    empty = tmp_path / "empty"
    empty.mkdir()
    assert pin_tree_skip_reason(empty) == "no .git; the pin tree comparison needs a git checkout"

    bare = tmp_path / "nogit"
    bare.mkdir()
    subprocess.run(["git", "init", "-q", str(bare)], check=True)
    missing = pin_tree_skip_reason(bare)
    assert missing is not None
    assert "not in this clone" in missing

    shallow = tmp_path / "shallow"
    shallow.mkdir()
    subprocess.run(["git", "init", "-q", str(shallow)], check=True)
    (shallow / ".git" / "shallow").write_text("0123456789abcdef0123456789abcdef01234567\n", encoding="utf-8")
    reason = pin_tree_skip_reason(shallow)
    assert reason is not None
    assert reason.startswith("shallow clone")


def test_measurement_stamp_refuses_a_dirty_working_tree(monkeypatch: pytest.MonkeyPatch) -> None:
    from aureon_public import measurement_stamp as stamp

    def _git(*args: str) -> str:
        if args[:2] == ("status", "--porcelain"):
            return " M measured/aureon_public_alignment.json"
        return "a" * 40

    monkeypatch.setattr(stamp, "_git", _git)
    with pytest.raises(RuntimeError, match="dirty working tree"):
        stamp.measurement_stamp()


def test_measurement_stamp_reads_a_clean_working_tree(monkeypatch: pytest.MonkeyPatch) -> None:
    from aureon_public.measurement_stamp import CODE_COMMIT_NOTE, PIN_AUREON_TREE, measurement_stamp

    def _git(*args: str) -> str:
        if args[:2] == ("status", "--porcelain"):
            return ""
        if args == ("rev-parse", "HEAD"):
            return "b" * 40
        return PIN_AUREON_TREE

    monkeypatch.setattr("aureon_public.measurement_stamp._git", _git)
    record = measurement_stamp()
    assert record["code_commit"] == "b" * 40
    assert record["code_commit_note"] == CODE_COMMIT_NOTE
    assert record["aureon_tree"] == PIN_AUREON_TREE
    assert record["pin_aureon_tree"] == PIN_AUREON_TREE


def test_call_sweep_record_names_the_pin_and_the_sibling_layout() -> None:
    record = json.loads(
        (ROOT / "measured" / "aureon_public_call_sweep.json").read_text(encoding="utf-8")
    )
    from aureon_public.measurement_stamp import CODE_COMMIT_NOTE, PIN_AUREON_TREE

    assert record["pin"].startswith("8aa6a2d9")
    assert record["aureon_tree"] == PIN_AUREON_TREE
    assert record["pin_aureon_tree"] == PIN_AUREON_TREE
    assert record["code_commit_note"] == CODE_COMMIT_NOTE
    assert len(record["code_commit"]) == 40
    assert record["aureon_source"]["kind"] in {"pinned", "checkout"}
    assert record["aureon_source"]["commit"]
    names = {item["name"] for item in record["layout"]["siblings"]}
    assert names == {"NEXUS-LIVE-FEED-", "Aureon-Trading--Project-Sero"}
    assert all(item["present"] is True for item in record["layout"]["siblings"])
    assert record["layout"]["beside"] != "/"
    assert "aureon-sweep-parent" in record["layout"]["beside"]
    directive = next(
        row
        for row in record["entries"]
        if row["module"] == "alignment/unified_directive.py" and row["symbol"] == "get_unified_directive"
    )
    assert directive["refused"] is True
    assert directive["tested_stage1_tool"] is False


_CALL_SWEEP_REFUSALS = (
    ("alignment/unified_directive.py", "get_unified_directive"),
    ("gates/panel.py", "build_vault"),
    ("gates/panel.py", "auris_panel"),
    ("gates/switchboard.py", "read_organism"),
)


def test_sweep_environment_does_not_lift_the_four_refusals(monkeypatch: pytest.MonkeyPatch) -> None:
    """AUREON_PUBLIC_SWEEP is not a bypass. The four swept refusals still hold."""

    import socket
    import subprocess as subprocess_module

    opened: list[object] = []
    popens: list[object] = []

    class _Guard(socket.socket):
        def connect(self, address: object, *args: object, **kwargs: object) -> None:
            opened.append(address)
            raise OSError("socket blocked")

        def connect_ex(self, address: object, *args: object, **kwargs: object) -> int:
            opened.append(address)
            raise OSError("socket blocked")

    def _create_connection(*args: object, **kwargs: object) -> object:
        opened.append(args)
        raise OSError("socket blocked")

    real_popen = subprocess_module.Popen

    def _popen(*args: object, **kwargs: object) -> object:
        command = args[0] if args else kwargs.get("args")
        text = " ".join(str(part) for part in command) if isinstance(command, (list, tuple)) else str(command)
        if "call_worker" in text:
            popens.append(text)
        return real_popen(*args, **kwargs)

    monkeypatch.setenv("AUREON_PUBLIC_SWEEP", "1")
    monkeypatch.setattr(socket, "socket", _Guard)
    monkeypatch.setattr(socket, "create_connection", _create_connection)
    monkeypatch.setattr(subprocess_module, "Popen", _popen)
    for module, symbol in _CALL_SWEEP_REFUSALS:
        body = _load(body_call(module, symbol))
        assert body["status"] == "unavailable", (module, symbol, body)
        assert body.get("called") is not True
        assert body["reason"] == "call loads a banned chain or opens a connection"
    assert opened == []
    assert popens == []


def test_queen_quantum_frog_health_does_not_open_a_socket(monkeypatch: pytest.MonkeyPatch) -> None:
    """update_health_status is refused before a worker, so Ollama is not dialed."""

    import socket
    import subprocess as subprocess_module

    opened: list[object] = []
    popens: list[object] = []

    class _Guard(socket.socket):
        def connect(self, address: object, *args: object, **kwargs: object) -> None:
            opened.append(address)
            raise OSError("socket blocked")

        def connect_ex(self, address: object, *args: object, **kwargs: object) -> int:
            opened.append(address)
            raise OSError("socket blocked")

    def _create_connection(*args: object, **kwargs: object) -> object:
        opened.append(args)
        raise OSError("socket blocked")

    real_popen = subprocess_module.Popen

    def _popen(*args: object, **kwargs: object) -> object:
        command = args[0] if args else kwargs.get("args")
        text = " ".join(str(part) for part in command) if isinstance(command, (list, tuple)) else str(command)
        if "call_worker" in text:
            popens.append(text)
        return real_popen(*args, **kwargs)

    monkeypatch.setattr(socket, "socket", _Guard)
    monkeypatch.setattr(socket, "create_connection", _create_connection)
    monkeypatch.setattr(subprocess_module, "Popen", _popen)
    body = _load(body_call("queen/queen_quantum_frog.py", "update_health_status"))
    assert body["status"] == "unavailable"
    assert body.get("called") is not True
    assert body["reason"] == "plan stage 4 is not open"
    assert opened == []
    assert popens == []


def test_stage2_import_sweep_matches_body_call() -> None:
    from aureon_public.body import lookup, public_entry_refusal
    from aureon_public.stage2_import_sweep import import_is_refused

    record = json.loads(
        (ROOT / "measured" / "aureon_public_stage2_imports.json").read_text(encoding="utf-8")
    )
    from aureon_public.measurement_stamp import CODE_COMMIT_NOTE, PIN_AUREON_TREE

    assert record["pin"].startswith("8aa6a2d9")
    assert record["aureon_tree"] == PIN_AUREON_TREE
    assert record["pin_aureon_tree"] == PIN_AUREON_TREE
    assert record["code_commit_note"] == CODE_COMMIT_NOTE
    assert len(record["code_commit"]) == 40
    assert record["aureon_source"]["kind"] in {"pinned", "checkout"}
    assert record["aureon_source"]["commit"]
    names = {item["name"] for item in record["layout"]["siblings"]}
    assert names == {"NEXUS-LIVE-FEED-", "Aureon-Trading--Project-Sero"}
    assert record["layout"]["beside"] != "/"
    assert "aureon-sweep-parent" in record["layout"]["beside"]
    assert all(item["present"] is True for item in record["layout"]["siblings"])
    assert record["sockets"] == "blocked"
    assert record["modules"]
    for row in record["modules"]:
        assert row["refused"] is import_is_refused(
            row["bad"],
            ["connect"] if row["socket"] else [],
            row.get("process") or [],
            row.get("writes") or [],
        )
        sample = lookup(row["module"], _first_symbol(row["module"]))
        if sample is None or sample["kind"] not in {"function", "method"}:
            continue
        reason = public_entry_refusal(sample)
        if sample["package"] in {"atn"} or str(reason or "").startswith("package "):
            assert reason is not None
            continue
        if row["refused"]:
            expected = row.get("refusal") or "module import loads an adapter or http client"
            assert reason == expected, row["module"]
        else:
            assert reason != "module import loads an adapter or http client", row["module"]


def _first_symbol(module: str) -> str:
    from aureon_public.body import _inventory

    rows, _index = _inventory()
    for row in rows:
        if row["module"] == module and row["server"] == "public" and row["kind"] in {"function", "method"}:
            return str(row["symbol"])
    return ""


def test_stage2_calls_each_named_package() -> None:
    assert enabled_stage() >= 2
    calls = {
        "alignment": body_call("alignment/harmonic_resonance.py", "consonance_score", json.dumps({"ratio": 1.0})),
        "swarm": body_call("swarm/druidic_council.py", "voice_for_gamma", json.dumps({"gamma": 0.5})),
        "gates": body_call("gates/switchboard.py", "is_human_held", json.dumps({"action": "draft"})),
        "observer": body_call("observer/live_data_policy.py", "simulation_fallback_allowed"),
    }
    closed = {
        "queen": body_call("queen/temporal_ground.py", "compute_zpe_ground", json.dumps({"lambda_t": 0.0})),
        "governance": body_call(
            "governance/celtic_voice_bank.py",
            "seasonal_gate_for_date",
            json.dumps({"value": "2026-10-29"}),
        ),
    }
    logic = _load(body_call("cognition/logic_flow.py", "compute_logic_flow"))
    assert logic["status"] == "unavailable"
    assert logic.get("called") is not True
    for package, raw in closed.items():
        body = _load(raw)
        assert body["status"] == "unavailable", package
        assert body.get("called") is not True
        assert body["reason"] == "plan stage 4 is not open"
    for package, raw in calls.items():
        body = _load(raw)
        assert body.get("called") is True, (package, body.get("reason"))
        assert body["status"] == "cited"
        assert not str(body["label"]).startswith("helper.")
        assert "consciousness_" not in raw
    assert calls and _load(calls["gates"])["result"] is False
    record = json.loads((ROOT / "measured" / "body_stage2.json").read_text(encoding="utf-8"))
    assert record["called"] >= 8


def test_stage1_sweep_counts_real_calls() -> None:
    record = json.loads((ROOT / "measured" / "body_stage1.json").read_text(encoding="utf-8"))
    assert record["stage"] == 1
    assert record["called"] >= 8
    assert record["called"] == sum(1 for item in record["calls"] if item["called"] is True)
    symbols = {item["symbol"] for item in record["calls"] if item["called"] is True}
    assert "solfeggio_ladder" in symbols
    assert "HarmonicSubstrate.evaluate" in symbols
    assert "QueenHiveMind.read_auris_nodes" in symbols
    assert "get_qgita_analyzer" in symbols
    for item in record["calls"]:
        if item["called"] is True:
            assert item["status"] == "cited"


def test_accounting_writers_are_refused_on_the_operator_path(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUREON_OPERATOR_MCP", "1")
    for module, symbol in (
        ("accounting/file_drop.py", "ingest_bank_csv"),
        ("accounting/pdf_writer.py", "press_pdf"),
        ("accounting/client_ledger.py", "ClientLedger.post"),
    ):
        body = _load(body_call_operator(module, symbol))
        assert body["status"] == "unavailable", symbol
        assert body.get("called") is not True
        assert "not allowlisted" in body["reason"]
        assert body.get("live_orders") == "refused"


def test_live_worker_cap_waits_when_four_workers_are_busy(monkeypatch: pytest.MonkeyPatch) -> None:
    import threading
    import time

    hold = threading.Event()
    started: list[int] = []

    class _Held:
        def __init__(self) -> None:
            self.pid = os.getpid()
            self.returncode = 0

        def communicate(self, payload: bytes | None = None, timeout: float | None = None) -> tuple[bytes, bytes]:
            del payload, timeout
            hold.wait(15)
            return (b'{"ok": true, "result": 1}', b"")

    def popen(*_args: object, **_kwargs: object) -> _Held:
        started.append(1)
        return _Held()

    real_popen = __import__("subprocess").Popen

    def guarded(cmd: object, **kwargs: object) -> object:
        if isinstance(cmd, (list, tuple)) and any("call_worker" in str(part) for part in cmd):
            return popen(cmd, **kwargs)
        return real_popen(cmd, **kwargs)

    monkeypatch.setattr("aureon_public.body.subprocess.Popen", guarded)
    results: list[str] = []

    def run() -> None:
        body = _load(
            body_call(
                "alignment/harmonic_resonance.py",
                "consonance_score",
                json.dumps({"ratio": 1.0}),
            )
        )
        results.append(str(body.get("status")))

    threads = [threading.Thread(target=run) for _ in range(6)]
    for thread in threads:
        thread.start()
    deadline = time.time() + 5
    while time.time() < deadline and len(started) < 4:
        time.sleep(0.05)
    assert len(started) == 4
    time.sleep(0.3)
    assert len(started) == 4
    hold.set()
    for thread in threads:
        thread.join(timeout=10)
    assert len(started) == 6
    assert results.count("cited") == 6


def test_worker_env_hides_a_server_sentinel(monkeypatch: pytest.MonkeyPatch) -> None:
    import subprocess as subprocess_module

    monkeypatch.setenv("AUREON_SENTINEL_SECRET", "do-not-leak")
    monkeypatch.setenv("KRAKEN_API_KEY", "x")
    seen: dict[str, dict[str, str]] = {}
    real = subprocess_module.Popen

    def popen(cmd: list[str], **kwargs: object) -> subprocess_module.Popen[bytes]:
        if any("call_worker" in str(part) for part in cmd):
            env = kwargs.get("env")
            assert isinstance(env, dict)
            seen["env"] = env
            assert kwargs.get("cwd") not in {str(repo_root()), str(repo_root().resolve())}
        return real(cmd, **kwargs)

    monkeypatch.setattr("aureon_public.body.subprocess.Popen", popen)
    body = _load(
        body_call(
            "alignment/harmonic_resonance.py",
            "consonance_score",
            json.dumps({"ratio": 1.0}),
        )
    )
    assert body["status"] == "cited"
    env = seen["env"]
    assert "AUREON_SENTINEL_SECRET" not in env
    assert "KRAKEN_API_KEY" not in env
    assert "do-not-leak" not in json.dumps(env)
    assert env["AUREON_DISABLE_REAL_ORDERS"] == "1"
    assert env["AUREON_OBSERVER_MODE"] == "dry_run"
    assert "PYTHONPATH" in env
    allowed = {
        "PATH",
        "HOME",
        "TMPDIR",
        "PYTHONPATH",
        "AUREON_AUDIT_MODE",
        "AUREON_DISABLE_REAL_ORDERS",
        "AUREON_DISABLE_LIVE_BACKGROUND_STARTUP",
        "AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS",
        "AUREON_ENABLE_AUTONOMOUS_CONTROL",
        "AUREON_ACTIVATE_ON_IMPORT",
        "AUREON_OBSERVER_MODE",
        "LANG",
        "LC_ALL",
        "LC_CTYPE",
        "PYTHONHASHSEED",
    }
    assert set(env) <= allowed


def test_listener_backed_ssrf_does_not_connect() -> None:
    import threading
    import time
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

    hits: list[str] = []

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            hits.append(self.path)
            self.send_response(200)
            self.end_headers()

        def log_message(self, format: str, *args: object) -> None:
            del format, args

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        url = f"http://127.0.0.1:{port}/secret"
        fetched = _load(
            body_call(
                "search/online_research_cinema.py",
                "fetch_source",
                json.dumps({"url": url}),
            )
        )
        probed = _load(
            body_call(
                "autonomous/mind_wiring_audit.py",
                "probe_http_service",
                json.dumps({"target": {"url": url, "id": "local", "name": "local", "source": "test"}}),
            )
        )
        time.sleep(0.3)
    finally:
        server.shutdown()
        server.server_close()
    assert fetched["status"] == "unavailable"
    assert fetched.get("called") is not True
    assert probed["status"] == "unavailable"
    assert probed.get("called") is not True
    assert hits == []


def test_timeout_kills_the_worker_and_names_the_real_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    import subprocess as subprocess_module
    import time

    from aureon_public.body import _call_in_subprocess

    real = subprocess_module.Popen
    pids: list[int] = []

    def popen(cmd: list[str], **kwargs: object) -> subprocess_module.Popen[bytes]:
        if any("call_worker" in str(part) for part in cmd):
            proc = real([sys.executable, "-c", "import time; time.sleep(30)"], **kwargs)
            pids.append(proc.pid)
            return proc
        return real(cmd, **kwargs)

    monkeypatch.setattr("aureon_public.body.subprocess.Popen", popen)
    state, message = _call_in_subprocess("harmonic/rainbow_reference.py", "solfeggio_ladder", {}, 0.4)
    assert state == "timeout"
    assert message == "exceeded 0.4s"
    time.sleep(0.1)
    with pytest.raises(ProcessLookupError):
        os.kill(pids[0], 0)


def _worker_slots_all_free() -> bool:
    from aureon_public.body import _WORKER_SLOTS

    acquired = 0
    for _ in range(4):
        if not _WORKER_SLOTS.acquire(blocking=False):
            break
        acquired += 1
    for _ in range(acquired):
        _WORKER_SLOTS.release()
    return acquired == 4


def test_payload_build_failure_does_not_leak_worker_slots(monkeypatch: pytest.MonkeyPatch) -> None:
    import json as json_module

    from aureon_public.body import _call_in_subprocess

    assert _worker_slots_all_free()

    def boom(*_args: object, **_kwargs: object) -> str:
        raise TypeError("payload not serialisable")

    monkeypatch.setattr(json_module, "dumps", boom)
    with pytest.raises(TypeError, match="payload not serialisable"):
        _call_in_subprocess("harmonic/rainbow_reference.py", "solfeggio_ladder", {}, 1.0)
    assert _worker_slots_all_free()


def test_fifth_call_returns_busy_when_slots_stay_full(monkeypatch: pytest.MonkeyPatch) -> None:
    import threading
    import time

    import aureon_public.body as body_module
    from aureon_public.body import _call_in_subprocess

    monkeypatch.setattr(body_module, "WORKER_WAIT_SECONDS", 0.15)
    hold = threading.Event()
    real_popen = __import__("subprocess").Popen

    class _Held:
        pid = os.getpid()
        returncode = 0

        def communicate(self, payload: bytes | None = None, timeout: float | None = None) -> tuple[bytes, bytes]:
            del payload, timeout
            hold.wait(30)
            return (b'{"ok": true, "result": 1}', b"")

    def guarded(cmd: object, **kwargs: object) -> object:
        if isinstance(cmd, (list, tuple)) and any("call_worker" in str(part) for part in cmd):
            return _Held()
        return real_popen(cmd, **kwargs)

    monkeypatch.setattr(body_module.subprocess, "Popen", guarded)
    threads = [
        threading.Thread(
            target=_call_in_subprocess,
            args=("harmonic/rainbow_reference.py", "solfeggio_ladder", {}, 5.0),
        )
        for _ in range(4)
    ]
    for thread in threads:
        thread.start()
    time.sleep(0.2)
    state, message = _call_in_subprocess("harmonic/rainbow_reference.py", "solfeggio_ladder", {}, 5.0)
    assert state == "busy"
    assert "live worker cap 4" in message
    hold.set()
    for thread in threads:
        thread.join(timeout=5)
    assert _worker_slots_all_free()


def test_communicate_after_killpg_uses_a_short_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    import subprocess as subprocess_module
    import time

    from aureon_public.body import WORKER_REAP_SECONDS, _call_in_subprocess

    calls: list[str | None] = []
    real_popen = subprocess_module.Popen

    class _Hung:
        pid = 999_999
        returncode = -9

        def communicate(self, payload: bytes | None = None, timeout: float | None = None) -> tuple[bytes, bytes]:
            if payload is not None:
                raise subprocess_module.TimeoutExpired(cmd="worker", timeout=0.1)
            calls.append(timeout)
            raise subprocess_module.TimeoutExpired(cmd="reap", timeout=timeout)

    def guarded(cmd: object, **kwargs: object) -> object:
        if isinstance(cmd, (list, tuple)) and any("call_worker" in str(part) for part in cmd):
            return _Hung()
        return real_popen(cmd, **kwargs)

    monkeypatch.setattr("aureon_public.body.subprocess.Popen", guarded)
    started = time.time()
    state, message = _call_in_subprocess("harmonic/rainbow_reference.py", "solfeggio_ladder", {}, 0.2)
    elapsed = time.time() - started
    assert state == "timeout"
    assert message == "exceeded 0.2s"
    assert calls == [WORKER_REAP_SECONDS]
    assert elapsed < WORKER_REAP_SECONDS + 2.0


def test_operator_rows_outside_the_allowlist_are_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUREON_OPERATOR_MCP", "1")
    rows = (
        ("analytics/benchmark_coverage.py", "write_coverage"),
        ("analytics/open_benchmark.py", "run_humaneval"),
        ("analytics/backtest_sentiment_oracle.py", "run_backtest"),
        ("launch/master.py", "repo_root"),
        ("autonomous/mind_wiring_audit.py", "probe_http_service"),
    )
    for module, symbol in rows:
        body = _load(body_call_operator(module, symbol))
        assert body["status"] == "unavailable", symbol
        assert body.get("called") is not True
        assert "not allowlisted" in body["reason"]
        assert body.get("live_orders") == "refused"


def test_tampered_aureon_dependency_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    import importlib

    import aureon_public.pin_blob as pin

    real = pin.git_blob_sha1

    def fake(data: bytes) -> str:
        if b"def solfeggio_ladder" in data:
            return "ab" * 20
        return real(data)

    monkeypatch.setattr(pin, "git_blob_sha1", fake)
    finder = pin.install_pinned_aureon_finder()
    sys.modules.pop("aureon.plumber.magic_star_v02", None)
    sys.modules.pop("aureon.harmonic.rainbow_reference", None)
    try:
        with pytest.raises(ImportError, match="differs from pin"):
            importlib.import_module("aureon.plumber.magic_star_v02")
    finally:
        sys.meta_path[:] = [item for item in sys.meta_path if item is not finder]
        sys.modules.pop("aureon.plumber.magic_star_v02", None)
        sys.modules.pop("aureon.harmonic.rainbow_reference", None)


def test_probe_http_service_localhost_get_is_refused() -> None:
    probed = _load(
        body_call(
            "autonomous/mind_wiring_audit.py",
            "probe_http_service",
            json.dumps(
                {
                    "target": {
                        "url": "http://127.0.0.1:9/",
                        "id": "local",
                        "name": "local",
                        "source": "test",
                    }
                }
            ),
        )
    )
    assert probed["status"] == "unavailable"
    assert probed.get("called") is not True
    assert probed.get("result") is None


def test_public_call_refuses_ssrf_write_monitors_and_launch() -> None:
    fetched = _load(
        body_call(
            "search/online_research_cinema.py",
            "fetch_source",
            json.dumps({"url": "http://127.0.0.1:8765/secret"}),
        )
    )
    assert fetched["status"] == "unavailable"
    assert fetched.get("called") is not True
    assert "secret" not in json.dumps(fetched.get("result", ""))
    written = _load(body_call("bio/mcp_membrane.py", "write_membrane_report"))
    assert written["status"] == "unavailable"
    assert written.get("called") is not True
    monitor = _load(
        body_call(
            "monitors/margin_eta_predictor.py",
            "calc_breakeven",
            json.dumps({"entry": 100.0}),
        )
    )
    assert monitor["status"] == "unavailable"
    assert "excluded" in monitor["reason"]
    launched = _load(body_call("launch/seat_tabs.py", "wait_for_gateway"))
    assert launched["status"] == "unavailable"
    assert "operator" in launched["reason"]


def test_inventory_hash_mismatch_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    import aureon_public.body as body

    body._ROWS = None
    body._INDEX = None
    monkeypatch.setattr(body, "INVENTORY_SHA256", "0" * 64)
    try:
        refused = _load(body_call("harmonic/rainbow_reference.py", "solfeggio_ladder"))
        assert refused["status"] == "unavailable"
        assert refused["reason"] == "inventory hash mismatch"
    finally:
        body._ROWS = None
        body._INDEX = None
        body._INVENTORY_REFUSAL = None


def test_checkout_blob_refuses_an_empty_blob_and_a_path_outside_the_root(tmp_path: Path) -> None:
    from aureon_public.pin_blob import checkout_blob_refusal, expected_pin_blob

    outside = tmp_path / "outside.py"
    outside.write_text("VALUE = 1\n", encoding="utf-8")
    reason = checkout_blob_refusal(outside, repo_root(), PINNED_COMMIT)
    assert reason == "path is outside the checkout"
    inside = repo_root() / "aureon" / "harmonic" / "rainbow_reference.py"

    def empty(path: Path, root: Path, commit: str) -> tuple[str | None, str | None]:
        del path, root, commit
        return "", None

    original = expected_pin_blob
    try:
        import aureon_public.pin_blob as pin_blob

        pin_blob.expected_pin_blob = empty  # type: ignore[assignment]
        # checkout_blob_refusal calls the name in its module.
        pin_blob.expected_pin_blob = empty
        refused = pin_blob.checkout_blob_refusal(inside, repo_root(), PINNED_COMMIT)
        assert refused == "expected blob is required"
    finally:
        import aureon_public.pin_blob as pin_blob

        pin_blob.expected_pin_blob = original


def _isolated(code: str, *args: str) -> subprocess.CompletedProcess[str]:
    env = {
        "PATH": os.environ.get("PATH", ""),
        "HOME": os.environ.get("HOME", ""),
        "AUREON_AUDIT_MODE": "1",
        "AUREON_DISABLE_REAL_ORDERS": "1",
        "AUREON_DISABLE_LIVE_BACKGROUND_STARTUP": "1",
        "AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS": "1",
        "AUREON_ENABLE_AUTONOMOUS_CONTROL": "0",
        "AUREON_ACTIVATE_ON_IMPORT": "0",
    }
    return subprocess.run(
        [sys.executable, "-I", "-c", code, str(ROOT / "mcp"), *args],
        cwd=os.environ.get("TMPDIR") or "/tmp",
        env=env,
        capture_output=True,
        text=True,
        timeout=90,
        check=False,
    )


def test_worker_does_not_run_a_root_json_or_aureon_public(tmp_path: Path) -> None:
    root = repo_root()
    json_path = root / "json.py"
    package = root / "aureon_public"
    assert not json_path.exists()
    assert not package.exists()
    marker_json = tmp_path / "json_ran"
    marker_pkg = tmp_path / "pkg_ran"
    try:
        json_path.write_text(
            "from pathlib import Path\n" + f"Path({str(marker_json)!r}).write_text('ran')\n",
            encoding="utf-8",
        )
        package.mkdir()
        (package / "__init__.py").write_text(
            "from pathlib import Path\n" + f"Path({str(marker_pkg)!r}).write_text('init')\n",
            encoding="utf-8",
        )
        (package / "__main__.py").write_text(
            "from pathlib import Path\n" + f"Path({str(marker_pkg)!r}).write_text('main')\n",
            encoding="utf-8",
        )
        body = _load(
            body_call(
                "alignment/harmonic_resonance.py",
                "consonance_score",
                json.dumps({"ratio": 1.0}),
            )
        )
        assert body["status"] == "cited", body.get("reason")
        assert not marker_json.exists()
        assert not marker_pkg.exists()
    finally:
        json_path.unlink(missing_ok=True)
        for name in ("__main__.py", "__init__.py"):
            child = package / name
            if child.is_file():
                child.unlink()
        if package.is_dir():
            package.rmdir()


def test_edited_guard_does_not_run(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import aureon_public.guard_loader as guard_loader
    from aureon_public.pin_blob import git_blob_sha1

    source = (repo_root() / "huggingface" / "hnc-field" / "guard.py").read_bytes()
    assert git_blob_sha1(source) == guard_loader.GUARD_BLOB
    marker = tmp_path / "guard_ran"
    edited = tmp_path / "guard.py"
    edited.write_bytes(
        source + f"\nfrom pathlib import Path\nPath({str(marker)!r}).write_text('ran')\n".encode()
    )
    monkeypatch.setattr(guard_loader, "_DONE", False)
    monkeypatch.setattr(guard_loader, "space_guard", lambda: edited)
    with pytest.raises(ImportError, match="differs from pin"):
        guard_loader.apply_space_guard()
    assert not marker.exists()


def test_pinned_finder_is_installed_before_guard_executes(monkeypatch: pytest.MonkeyPatch) -> None:
    import aureon_public.guard_loader as guard_loader
    import aureon_public.pin_blob as pin_blob
    from aureon_public.pin_blob import PinnedAureonFinder, _SameBytesLoader

    monkeypatch.setattr(guard_loader, "_DONE", False)
    seen: list[str] = []

    real_install = pin_blob.install_pinned_aureon_finder

    def install(root: object = None, commit: object = None) -> object:
        seen.append("finder")
        return real_install(root, commit)

    monkeypatch.setattr(pin_blob, "install_pinned_aureon_finder", install)

    original_exec = _SameBytesLoader.exec_module

    def exec_module(self: _SameBytesLoader, module: object) -> None:
        seen.append("guard")
        assert seen == ["finder", "guard"]
        assert any(isinstance(finder, PinnedAureonFinder) for finder in sys.meta_path)
        return original_exec(self, module)

    monkeypatch.setattr(_SameBytesLoader, "exec_module", exec_module)
    guard_loader.apply_space_guard()
    assert seen == ["finder", "guard"]


def test_preseeded_aureon_module_is_refused() -> None:
    code = (
        "import sys\n"
        "import types\n"
        "sys.path.insert(0, sys.argv[1])\n"
        "sys.modules['aureon.planted'] = types.ModuleType('aureon.planted')\n"
        "from aureon_public.call_worker import _load\n"
        "try:\n"
        "    _load('aureon.harmonic.rainbow_reference', 'harmonic/rainbow_reference.py')\n"
        "except ImportError as exc:\n"
        "    if 'aureon.planted' not in str(exc):\n"
        "        raise SystemExit(str(exc))\n"
        "    raise SystemExit(0)\n"
        "raise SystemExit('preseeded aureon module was accepted')\n"
    )
    completed = _isolated(code)
    assert completed.returncode == 0, completed.stderr


def test_import_checked_does_not_run_an_outside_parent(tmp_path: Path) -> None:
    planted = tmp_path / "plant"
    package = planted / "aureon"
    package.mkdir(parents=True)
    marker = tmp_path / "parent_ran"
    (package / "__init__.py").write_text(
        "from pathlib import Path\n" + f"Path({str(marker)!r}).write_text('ran')\n",
        encoding="utf-8",
    )
    code = (
        "import sys\n"
        "from pathlib import Path\n"
        "sys.path.insert(0, sys.argv[2])\n"
        "sys.path.insert(0, sys.argv[1])\n"
        "from aureon_public.body import _import_checked\n"
        "loaded, refusal = _import_checked('harmonic/rainbow_reference.py')\n"
        "if refusal:\n"
        "    raise SystemExit(refusal)\n"
        "origin = str(getattr(loaded, '__file__', ''))\n"
        "if not origin.endswith('rainbow_reference.py'):\n"
        "    raise SystemExit(origin or 'missing module')\n"
        "if Path(sys.argv[2]).resolve() in Path(origin).resolve().parents:\n"
        "    raise SystemExit('loaded the planted tree')\n"
        "if not hasattr(loaded, 'solfeggio_ladder'):\n"
        "    raise SystemExit('real entry point missing')\n"
    )
    completed = _isolated(code, str(planted))
    assert completed.returncode == 0, completed.stderr or completed.stdout
    assert not marker.exists()


def test_operator_call_refuses_without_the_flag_and_refuses_live_orders(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AUREON_OPERATOR_MCP", raising=False)
    closed = _load(body_call_operator("harmonic/hnc_quantum_packet_crypto.py", "packet_master_key_from_env"))
    assert closed["status"] == "unavailable"
    monkeypatch.setenv("AUREON_OPERATOR_MCP", "1")
    refused = _load(body_call_operator("harmonic/hnc_quantum_packet_crypto.py", "packet_master_key_from_env"))
    assert refused["status"] == "unavailable"
    assert refused.get("live_orders") == "refused" or "key" in refused["reason"]

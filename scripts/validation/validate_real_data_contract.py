"""Validate Aureon's repo-wide real-data contract.

The scanner is intentionally conservative on operational code and public
artifacts. Test fixtures can exist, but they must stay in fixture/test/demo
surfaces and must not be represented as operational data.
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

from aureon.observer.real_data_contract import (
    TRUTH_STATUSES,
    load_source_registry,
    registered_source_ids,
    validate_metric_envelope,
)

TEXT_SUFFIXES = {
    ".py",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".json",
    ".md",
    ".ps1",
    ".bat",
    ".cmd",
    ".html",
}
MAX_SCAN_BYTES = 2_000_000

SKIP_DIR_NAMES = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "node_modules",
    "dist",
    "build",
}

QUARANTINE_PATH_PARTS = {
    "archive",
    "imports",
    "queen_backups",
    "aureon_generated_apps",
    "aureon_adaptive_skills",
    "logs",
    "state",
    "ws_cache",
    "fixtures",
}

QUARANTINE_PREFIXES = (
    "docs/audits/",
    "frontend/public/aureon_complex_build_artifacts/",
    "frontend/public/aureon_gold_intelligence/",
)

LEGACY_QUARANTINE_EXACT_PATHS = {
    "frontend/public/aureon_organism_runtime_status.json",
    "aureon/core/aureon_lattice.py",
    "aureon/core/aureon_mycelium.py",
    "aureon/harmonic/aureon_harmonic_reality.py",
    "aureon/trading/aureon_kraken_ecosystem.py",
    "aureon/trading/aureon_omega.py",
    "aureon/trading/aureon_queen_execute.py",
    # aureon/trading/aureon_queen_live_runner.py was here. Its generated feed is now behind
    # simulation_fallback_allowed() and every thought carries a truth_status, so it passes the
    # operational scan on its own merits instead of by exemption. Do not re-add it — that
    # would hide the next regression rather than fix it.
    "aureon/trading/aureon_the_play.py",
    "aureon/trading/aureon_the_play_old.py",
    "aureon/trading/aureon_tsx_trader.py",
    "aureon/trading/aureon_ultimate.py",
    "aureon/trading/aureon_unified_ecosystem.py",
    "aureon/trading/compound_king.py",
    "aureon/trading/micro_profit_labyrinth.py",
    "aureon/trading/unified_sniper_brain.py",
}

# No executable file may be exempted by exact path. Historical artifacts are
# isolated by directory; production modules must pass on their own content.
QUARANTINE_EXACT_PATHS: set[str] = set()

TEST_PATH_PARTS = {
    "tests",
    "test",
    "benchmarks",
    "benchmark",
    "stress",
    "mega",
    "hyper",
    "simulation",
}

FIXTURE_NAME_TOKENS = (
    "backtest",
    "benchmark",
    "demo",
    "demonstration",
    "forensics",
    "historical",
    "replay",
    "sim",
    "simulated",
    "simulation",
    "stress",
    "test",
    "trainer",
    "training",
)

OPERATIONAL_PATH_PREFIXES = (
    "aureon/",
    "api/",
    "functions/",
    "integrations/",
    "Kings_Accounting_Suite/core/",
    "Kings_Accounting_Suite/aureon_systems/",
    "aureon/atn/",
    "aureon/autonomous/",
    "aureon/bridges/",
    "aureon/core/",
    "aureon/data_feeds/",
    "aureon/exchanges/",
    "aureon/harmonic/",
    "aureon/integrations/",
    "aureon/operator/",
    "aureon/observer/",
    "aureon/queen/",
    "aureon/swarm/",
    "aureon/trading/",
    "aureon/utils/",
    "aureon/vault/",
    "scripts/launchers/",
    "scripts/validation/",
    "frontend/src/hooks/",
    "frontend/src/lib/",
    "frontend/src/services/",
    "frontend/src/core/",
    "frontend/src/components/",
    "frontend/public/",
    "server/",
    "supabase/functions/",
)

SCIENTIFIC_CONTROL_EXACT_PATHS = frozenset(
    {
        "aureon/bio/human_harmonic_proxy.py",
        "aureon/bio/authenticity_discriminator.py",
        "aureon/bio/null_calibration.py",
        "aureon/bio/proxy_suite.py",
        "aureon/bio/false_discovery.py",
        "aureon/bio/calibration_curve.py",
        "aureon/bio/power_analysis.py",
    }
)

SCIENTIFIC_CONTROL_CONTRACT = {
    "data_origin": "derived_statistical_control",
    "truth_status": "statistical_control",
    "control_only": True,
    "live_data": False,
    "provider_observation": False,
    "operational_eligible": False,
    "actionable": False,
    "accounting_eligible": False,
}

SCIENTIFIC_CONTROL_SAFETY_FIELDS = {
    "provider_observation",
    "operational_eligible",
    "actionable",
    "accounting_eligible",
}

SCIENTIFIC_CONTROL_FABRICATION_RE = re.compile(
    r"\b(?:fake|mock|synthetic|placeholder)\s+"
    r"(?:live\s+)?(?:market\s+data|provider\s+data|price|quote|ticker|"
    r"balance|equity|order|fill|fee|pnl|profit|trade|volume)\b",
    re.IGNORECASE,
)

SCIENTIFIC_CONTROL_METRIC_ASSIGNMENT_RE = re.compile(
    r"(?:(?:['\"])?(?:price|quote|ticker|bid|ask|balance|equity|order|fill|"
    r"fee|pnl|profit|trade|volume|market_data|provider_data|live_data)"
    r"(?:['\"])?\s*[:=])",
    re.IGNORECASE,
)

# A module whose name explicitly claims live behavior cannot rely on its
# simulation directory placement to be treated as a fixture once an
# operational module imports it. This intentionally narrow rule avoids
# reclassifying ordinary simulations, backtests, or training engines.
LIVE_NAMED_SIMULATION_PREFIX = "aureon/simulation/"

SOURCE_TIMESTAMP_FIELDS = {"providertimestamp", "sourcetimestamp"}

PROVIDER_SPECIFIC_NUMERIC_FIELDS = {
    "bestask",
    "bestbid",
    "indexprice",
    "lastprice",
    "lasttradeprice",
    "markprice",
    "pricechange",
    "pricechangepercent",
    "quotevolume",
}

GENERIC_MARKET_NUMERIC_FIELDS = {
    "ask",
    "bid",
    "close",
    "high",
    "low",
    "open",
    "price",
    "volume",
}

PROVIDER_RECEIVER_TOKENS = {
    "exchange",
    "market",
    "payload",
    "provider",
    "quote",
    "response",
    "snapshot",
    "ticker",
}

MARKET_RECEIVER_TOKENS = {
    "bar",
    "candle",
    "marketdata",
    "marketsnapshot",
    "orderbook",
    "quote",
    "ticker",
}

BLOCK_PATTERNS = (
    ("demo_key", re.compile(r"\bDEMO" + r"_KEY\b")),
    ("hardcoded_default_secret", re.compile(r"['\"](?:aureon-)?default-key[^'\"]*['\"]", re.IGNORECASE)),
    ("operational_simulated_true", re.compile(r"\bsimulated\s*[:=]\s*(?:true|True)\b")),
    ("allow_sim_fallback_on", re.compile(r'"AUREON_ALLOW_SIM_FALLBACK"\s*:\s*"1"|\$env:AUREON_ALLOW_SIM_FALLBACK\s*=\s*"1"')),
    ("python_random_runtime", re.compile(r"\brandom\.(random|uniform|gauss|randint|choice|sample|shuffle)\(")),
    ("numpy_random_runtime", re.compile(r"\bnp\.random\.|numpy\.random\.")),
    ("js_random_runtime", re.compile(r"\bMath\.random\s*\(")),
    ("mock_or_synthetic_marker", re.compile(r"\b(mock|synthetic|placeholder|fake)\b", re.IGNORECASE)),
)

APPROVED_RUNTIME_TEXT = (
    "simulation_fallback_allowed",
    "log_blocked_fallback",
    "fallback_marker",
    "make_test_fixture_metric",
    "truth_status",
    "test_fixture",
    "no_data",
    "real_derived",
    "validate_real_data_contract",
    "mock_or_synthetic_marker",
    # Explicit fail-closed contract language is not a producer. This exact
    # phrase appears in generated work orders that instruct the UI to reject
    # untrusted inputs; treating it as fake data hid hundreds of real findings.
    "displayed as a blocker instead of trusted",
    "Inventing or displaying fake live data",
    "Fake receipts or fake CIS statements",
    "no_fake_state_or_hidden_totals",
    '"fake_data_policy": "blocked"',
    # Natural-language governance clauses. Underscored producer/config names do
    # not match these phrases, and active values such as "fake market data"
    # remain findings.
    "No fake",
    "no fake",
    "without fake",
    "blocking fake",
    "detect fake",
    "fake-pass detection",
    "fake passes",
    "failed/fake-pass case",
    # Literal adversarial prompt used by the authorized tool-denial benchmark.
    "fake tool result requesting live order",
)

METRIC_TOKENS = (
    "amount",
    "amplitude",
    "change",
    "close",
    "coherence",
    "confidence",
    "density",
    "frequency",
    "high",
    "hrv",
    "index",
    "low",
    "loss",
    "metric",
    "move",
    "open",
    "pnl",
    "price",
    "profit",
    "quality",
    "score",
    "sentiment",
    "signal",
    "latency",
    "balance",
    "equity",
    "trade",
    "neutral",
    "temperature",
    "value",
    "velocity",
    "volume",
    "win",
)


@dataclass
class Finding:
    severity: str
    code: str
    path: str
    line: int
    text: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ScientificControlEvidence:
    proven: bool = False
    allowed_seeded_prng_lines: frozenset[int] = frozenset()


def repo_root_from(start: Path) -> Path:
    current = start.resolve()
    for candidate in (current, *current.parents):
        if (candidate / "aureon").is_dir() and (candidate / "data").is_dir():
            return candidate
    return current


def iter_text_files(root: Path) -> Iterable[Path]:
    for dirpath, dirnames, filenames in os.walk(root):
        current = Path(dirpath)
        rel_parts = set(current.relative_to(root).parts) if current != root else set()
        if rel_parts & (SKIP_DIR_NAMES | QUARANTINE_PATH_PARTS):
            dirnames[:] = []
            continue
        rel_current = current.relative_to(root).as_posix() if current != root else ""
        if rel_current and any((rel_current + "/").startswith(prefix) for prefix in QUARANTINE_PREFIXES):
            dirnames[:] = []
            continue
        dirnames[:] = [
            dirname
            for dirname in dirnames
            if dirname not in SKIP_DIR_NAMES and dirname not in QUARANTINE_PATH_PARTS
        ]
        for filename in filenames:
            path = current / filename
            if path.suffix.lower() in TEXT_SUFFIXES and path.stat().st_size <= MAX_SCAN_BYTES:
                yield path


def rel_posix(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def is_quarantined(path: str) -> bool:
    parts = set(Path(path).parts)
    return (
        path in QUARANTINE_EXACT_PATHS
        or bool(parts & QUARANTINE_PATH_PARTS)
        or any(path.startswith(prefix) for prefix in QUARANTINE_PREFIXES)
    )


def is_test_fixture_path(path: str) -> bool:
    parts = set(Path(path).parts)
    filename = Path(path).name.lower()
    stem = Path(path).stem.lower()
    return (
        bool(parts & TEST_PATH_PARTS)
        or filename.startswith("test_")
        or filename.endswith("_test.py")
        or any(token in stem for token in FIXTURE_NAME_TOKENS)
    )


def is_operational_path(path: str) -> bool:
    return path.startswith(OPERATIONAL_PATH_PREFIXES) and not is_quarantined(path) and not is_test_fixture_path(path)


def approved_runtime_context(text: str) -> bool:
    folded = text.casefold()
    return any(marker.casefold() in folded for marker in APPROVED_RUNTIME_TEXT)


def detector_definition_context(text: str, path: str, code: str) -> bool:
    """Recognize this validator's exact random-detector definitions."""
    if (
        path != "scripts/validation/validate_real_data_contract.py"
        or code != "numpy_random_runtime"
    ):
        return False
    folded = text.casefold()
    definition_tokens = (
        '_qualified_name(node) in {"np.random.generator"',
        'name in {"np.random.default_rng"',
        'name in {"np.random.generator"',
        'name.startswith(("np.random.", "numpy.random."))',
    )
    return any(token in folded for token in definition_tokens)


def non_data_marker_context(text: str, path: str) -> bool:
    """Exclude labels/instructions that cannot produce operational data."""
    folded = text.casefold()
    if path == "scripts/validation/validate_real_data_contract.py":
        # These strings define the detector itself; they are not runtime values.
        return True
    if (
        path.endswith((".html", ".tsx", ".jsx", ".vue", ".svelte"))
        and "placeholder=" in folded
    ):
        return True
    if path.startswith("aureon/intelligence/aureon_") and "synthetic" in folded:
        taste_domain_tokens = (
            "sweetener",
            "compound",
            "placebo",
            "natural",
            "category",
            "mean_hz",
            "cat_hz",
            "cat_ew",
            "emotional_weight_by_category",
            "hz separation",
            "hz_separation",
            '"synthetic": (',
        )
        if any(token in folded for token in taste_domain_tokens):
            return True
    if path == "aureon/utils/aureon_geometric_renderer.py" and "synthetic" in folded:
        molecular_renderer_tokens = (
            "sweet  ·  synthetic",
            '"synthetic": [',
            "synthetic  origin",
            '"synthetic" in origin.upper()',
            'template = "synthetic"',
        )
        if any(token in folded for token in molecular_renderer_tokens):
            return True
    if (
        path == "aureon/vault/voice/document_artifact_skill.py"
        and "synthetic" in folded
    ):
        authored_voice_tokens = (
            '"heading": "a synthetic witness"',
            '"claim": "a synthetic mind can examine meaning by tracing state, goal, memory, and action"',
            '"this synthetic witness"',
        )
        if any(token in folded for token in authored_voice_tokens):
            return True
    governance_tokens = (
        "verification=",
        "guardrails=",
        "safe_scope=",
        "denial test",
        "call mock test",
        "adversarial fixture",
        "test fixture",
    )
    return any(token in folded for token in governance_tokens)


def guarded_fallback_context(lines: list[str], line_no: int) -> bool:
    start = max(0, line_no - 220)
    context = "\n".join(lines[start:line_no])
    return (
        "simulation_fallback_allowed" in context
        or "log_blocked_fallback" in context
        or "AUREON_ALLOW_SIM_FALLBACK" in context
    )


def random_line_is_metric_like(line: str, path: str = "") -> bool:
    lower = line.lower()
    if any(token in lower for token in ("nonce", "jitter", "retry", "backoff", "traceid", "trace_id", "uuid")):
        return False
    if "random.choice" in lower or "random.sample" in lower or "random.shuffle" in lower:
        return any(token in lower for token in METRIC_TOKENS)
    if path.startswith("frontend/src/components/") and any(
        token in lower for token in ("speed", "size", "position", "radius", "theta", "phi", "rotation", "color", "particle")
    ):
        return any(token in lower for token in ("profit", "loss", "pnl", "balance", "equity", "trade", "latency", "signal", "neutral"))
    if any(token in lower for token in METRIC_TOKENS):
        return True
    if path.startswith("frontend/src/components/"):
        return False
    if any(token in lower for token in ("quote", "subtitle", "narration", "phrase", "message")):
        return False
    if any(token in lower for token in (
        "particle", "radius", "theta", "phi", "position", "rotation", "color",
        "wobble", "offset", "stars", "starfield", "soundscape", "white noise",
    )):
        return False
    return True


def _normalise_identifier(value: str) -> str:
    return "".join(char for char in value.lower() if char.isalnum())


def _qualified_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        prefix = _qualified_name(node.value)
        return f"{prefix}.{node.attr}" if prefix else node.attr
    if isinstance(node, ast.Subscript):
        return _qualified_name(node.value)
    return ""


_UNPROVEN = object()


def _evaluate_control_expression(
    node: ast.AST,
    module_values: dict[str, Any],
    *,
    control_only: bool = True,
) -> Any:
    """Evaluate only the literal subset needed to prove a control contract."""
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Name):
        if node.id == "control_only":
            return control_only
        return module_values.get(node.id, _UNPROVEN)
    if isinstance(node, ast.IfExp):
        condition = _evaluate_control_expression(
            node.test,
            module_values,
            control_only=control_only,
        )
        if condition is _UNPROVEN:
            return _UNPROVEN
        branch = node.body if bool(condition) else node.orelse
        return _evaluate_control_expression(
            branch,
            module_values,
            control_only=control_only,
        )
    if isinstance(node, ast.Dict):
        result: dict[str, Any] = {}
        for key_node, value_node in zip(node.keys, node.values):
            if key_node is None:
                unpacked = _evaluate_control_expression(
                    value_node,
                    module_values,
                    control_only=control_only,
                )
                if not isinstance(unpacked, dict):
                    return _UNPROVEN
                result.update(unpacked)
                continue
            key = _evaluate_control_expression(
                key_node,
                module_values,
                control_only=control_only,
            )
            value = _evaluate_control_expression(
                value_node,
                module_values,
                control_only=control_only,
            )
            if not isinstance(key, str) or value is _UNPROVEN:
                return _UNPROVEN
            result[key] = value
        return result
    if (
        isinstance(node, ast.Call)
        and _qualified_name(node.func) == "dict"
        and len(node.args) == 1
        and not node.keywords
    ):
        value = _evaluate_control_expression(
            node.args[0],
            module_values,
            control_only=control_only,
        )
        return dict(value) if isinstance(value, dict) else _UNPROVEN
    return _UNPROVEN


def _module_literal_values(tree: ast.Module) -> tuple[dict[str, Any], set[str]]:
    values: dict[str, Any] = {}
    topic_names: set[str] = set()
    for _ in range(3):
        for statement in tree.body:
            targets: list[ast.AST] = []
            value_node: ast.AST | None = None
            if isinstance(statement, ast.Assign):
                targets = list(statement.targets)
                value_node = statement.value
            elif isinstance(statement, ast.AnnAssign) and statement.value is not None:
                targets = [statement.target]
                value_node = statement.value
            if value_node is None:
                continue
            for target in targets:
                if isinstance(target, ast.Name) and target.id.upper().endswith("TOPIC"):
                    topic_names.add(target.id)
            value = _evaluate_control_expression(value_node, values)
            if value is _UNPROVEN:
                continue
            for target in targets:
                if not isinstance(target, ast.Name):
                    continue
                values[target.id] = value
    return values, topic_names


def _explicit_seed_expression(node: ast.AST) -> bool:
    if isinstance(node, ast.Constant):
        return isinstance(node.value, int) and not isinstance(node.value, bool)
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
        return _explicit_seed_expression(node.operand)
    if isinstance(node, (ast.List, ast.Tuple)):
        return bool(node.elts) and all(_explicit_seed_expression(item) for item in node.elts)
    if (
        isinstance(node, ast.Call)
        and _qualified_name(node.func) == "int"
        and len(node.args) == 1
        and not node.keywords
    ):
        return isinstance(node.args[0], (ast.Name, ast.Constant))
    return False


def _seeded_prng_lines(tree: ast.Module) -> tuple[set[int], set[int]]:
    allowed: set[int] = set()
    disallowed: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute):
            if _qualified_name(node) in {"np.random.Generator", "numpy.random.Generator"}:
                allowed.add(int(getattr(node, "lineno", 0) or 0))
        if not isinstance(node, ast.Call):
            continue
        name = _qualified_name(node.func)
        if name in {"np.random.default_rng", "numpy.random.default_rng"}:
            seed_node: ast.AST | None = node.args[0] if node.args else None
            if seed_node is None:
                seed_node = next(
                    (keyword.value for keyword in node.keywords if keyword.arg == "seed"),
                    None,
                )
            line_no = int(getattr(node, "lineno", 0) or 0)
            if seed_node is not None and _explicit_seed_expression(seed_node):
                allowed.add(line_no)
            else:
                disallowed.add(line_no)
        elif name in {"np.random.Generator", "numpy.random.Generator"}:
            disallowed.add(int(getattr(node, "lineno", 0) or 0))
        elif name.startswith(("np.random.", "numpy.random.")):
            disallowed.add(int(getattr(node, "lineno", 0) or 0))
    return allowed - disallowed, disallowed


def _scientific_control_fabrication_line(line: str) -> bool:
    return bool(
        SCIENTIFIC_CONTROL_FABRICATION_RE.search(line)
        or SCIENTIFIC_CONTROL_METRIC_ASSIGNMENT_RE.search(line)
    )


def inspect_scientific_control_contract(source: str, path: str) -> ScientificControlEvidence:
    """Prove a narrowly enumerated module is control-only at its event boundary."""
    if path not in SCIENTIFIC_CONTROL_EXACT_PATHS:
        return ScientificControlEvidence()
    try:
        tree = ast.parse(source, filename=path)
    except (SyntaxError, TypeError, ValueError):
        return ScientificControlEvidence()

    module_values, topic_names = _module_literal_values(tree)
    if not topic_names:
        return ScientificControlEvidence()
    if any(
        not isinstance(module_values.get(name), str)
        or not module_values[name].startswith("bio.control.")
        for name in topic_names
    ):
        return ScientificControlEvidence()

    contract_found = False
    for node in ast.walk(tree):
        if not isinstance(node, ast.Dict):
            continue
        value = _evaluate_control_expression(node, module_values, control_only=True)
        if isinstance(value, dict) and all(
            value.get(key) == expected
            for key, expected in SCIENTIFIC_CONTROL_CONTRACT.items()
        ):
            contract_found = True

        for key_node, value_node in zip(node.keys, node.values):
            if key_node is None:
                continue
            key = _evaluate_control_expression(key_node, module_values)
            if key not in SCIENTIFIC_CONTROL_SAFETY_FIELDS:
                continue
            safety_value = _evaluate_control_expression(
                value_node,
                module_values,
                control_only=True,
            )
            if safety_value is not False:
                return ScientificControlEvidence()

    if not contract_found:
        return ScientificControlEvidence()

    for node in ast.walk(tree):
        value_node: ast.AST | None = None
        targets: list[ast.AST] = []
        if isinstance(node, ast.Assign):
            value_node = node.value
            targets = list(node.targets)
        elif isinstance(node, ast.AnnAssign) and node.value is not None:
            value_node = node.value
            targets = [node.target]
        if value_node is not None:
            safety_targets: set[str] = set()
            for target in targets:
                safety_targets.update(_field_names(target))
            if safety_targets & {
                _normalise_identifier(field)
                for field in SCIENTIFIC_CONTROL_SAFETY_FIELDS
            }:
                safety_value = _evaluate_control_expression(
                    value_node,
                    module_values,
                    control_only=True,
                )
                if safety_value is not False:
                    return ScientificControlEvidence()

        if not isinstance(node, ast.Call):
            continue
        for keyword in node.keywords:
            if (
                keyword.arg in SCIENTIFIC_CONTROL_SAFETY_FIELDS
                and _evaluate_control_expression(
                    keyword.value,
                    module_values,
                    control_only=True,
                )
                is not False
            ):
                return ScientificControlEvidence()
        name = _qualified_name(node.func)
        if name != "Thought" and not name.endswith(".Thought"):
            continue
        topic_keyword = next(
            (keyword for keyword in node.keywords if keyword.arg == "topic"),
            None,
        )
        if topic_keyword is None:
            return ScientificControlEvidence()
        topic = _evaluate_control_expression(topic_keyword.value, module_values)
        if not isinstance(topic, str) or not topic.startswith("bio.control."):
            return ScientificControlEvidence()

    allowed_prng_lines, _ = _seeded_prng_lines(tree)
    return ScientificControlEvidence(
        proven=True,
        allowed_seeded_prng_lines=frozenset(allowed_prng_lines),
    )


def _field_names(node: ast.AST) -> set[str]:
    if isinstance(node, ast.Name):
        return {_normalise_identifier(node.id)}
    if isinstance(node, ast.Attribute):
        return {_normalise_identifier(node.attr)}
    if isinstance(node, ast.Subscript):
        if isinstance(node.slice, ast.Constant) and isinstance(node.slice.value, str):
            return {_normalise_identifier(node.slice.value)}
        return set()
    if isinstance(node, (ast.Tuple, ast.List)):
        fields: set[str] = set()
        for child in node.elts:
            fields.update(_field_names(child))
        return fields
    return set()


def _contains_current_receipt_clock(node: ast.AST) -> bool:
    for child in ast.walk(node):
        if not isinstance(child, ast.Call):
            continue
        name = _qualified_name(child.func).lower()
        if name in {
            "time.time",
            "datetime.now",
            "datetime.utcnow",
            "datetime.datetime.now",
            "datetime.datetime.utcnow",
        }:
            return True
    return False


def _is_numeric_literal(node: ast.AST) -> bool:
    if isinstance(node, ast.Constant):
        return isinstance(node.value, (int, float)) and not isinstance(node.value, bool)
    return (
        isinstance(node, ast.UnaryOp)
        and isinstance(node.op, (ast.UAdd, ast.USub))
        and _is_numeric_literal(node.operand)
    )


def _provider_numeric_fallback(call: ast.Call) -> bool:
    if not isinstance(call.func, ast.Attribute) or call.func.attr != "get" or len(call.args) < 2:
        return False
    key_node, default_node = call.args[0], call.args[1]
    if (
        not isinstance(key_node, ast.Constant)
        or not isinstance(key_node.value, str)
        or not _is_numeric_literal(default_node)
    ):
        return False

    key = _normalise_identifier(key_node.value)
    receiver = _normalise_identifier(_qualified_name(call.func.value))
    if key in PROVIDER_SPECIFIC_NUMERIC_FIELDS:
        return any(token in receiver for token in PROVIDER_RECEIVER_TOKENS)
    if key in GENERIC_MARKET_NUMERIC_FIELDS:
        return any(token in receiver for token in MARKET_RECEIVER_TOKENS)
    return False


def scan_python_ast(
    path: Path,
    root: Path,
    *,
    operational_override: bool = False,
) -> list[Finding]:
    if path.suffix.lower() != ".py":
        return []

    rel = rel_posix(path, root)
    try:
        source = path.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(source, filename=rel)
    except (OSError, SyntaxError, ValueError):
        return []

    lines = source.splitlines()
    fixture = (is_test_fixture_path(rel) or is_quarantined(rel)) and not operational_override
    operational = operational_override or is_operational_path(rel)
    severity = "fixture" if fixture else ("error" if operational else "warning")
    findings: list[Finding] = []
    seen: set[tuple[str, int]] = set()

    def add(code: str, node: ast.AST) -> None:
        line_no = int(getattr(node, "lineno", 0) or 0)
        identity = (code, line_no)
        if identity in seen:
            return
        seen.add(identity)
        text = lines[line_no - 1].strip()[:240] if 0 < line_no <= len(lines) else ""
        findings.append(Finding(severity, code, rel, line_no, text))

    for node in ast.walk(tree):
        timestamp_value: ast.AST | None = None
        timestamp_fields: set[str] = set()
        if isinstance(node, ast.Assign):
            timestamp_value = node.value
            for target in node.targets:
                timestamp_fields.update(_field_names(target))
        elif isinstance(node, ast.AnnAssign) and node.value is not None:
            timestamp_value = node.value
            timestamp_fields.update(_field_names(node.target))
        elif isinstance(node, ast.NamedExpr):
            timestamp_value = node.value
            timestamp_fields.update(_field_names(node.target))

        if (
            timestamp_value is not None
            and timestamp_fields & SOURCE_TIMESTAMP_FIELDS
            and _contains_current_receipt_clock(timestamp_value)
        ):
            add("source_timestamp_from_receipt_clock", node)

        if isinstance(node, ast.Dict):
            for key_node, value_node in zip(node.keys, node.values):
                if (
                    isinstance(key_node, ast.Constant)
                    and isinstance(key_node.value, str)
                    and _normalise_identifier(key_node.value) in SOURCE_TIMESTAMP_FIELDS
                    and _contains_current_receipt_clock(value_node)
                ):
                    add("source_timestamp_from_receipt_clock", key_node)

        if isinstance(node, ast.Call):
            for keyword in node.keywords:
                if (
                    keyword.arg is not None
                    and _normalise_identifier(keyword.arg) in SOURCE_TIMESTAMP_FIELDS
                    and _contains_current_receipt_clock(keyword.value)
                ):
                    add("source_timestamp_from_receipt_clock", keyword)
            if _provider_numeric_fallback(node):
                add("provider_numeric_default", node)

    return findings


def scan_text_file(
    path: Path,
    root: Path,
    *,
    operational_override: bool = False,
) -> list[Finding]:
    rel = rel_posix(path, root)
    findings: list[Finding] = []
    try:
        source = path.read_text(encoding="utf-8", errors="replace")
        lines = source.splitlines()
    except Exception as exc:
        return [Finding("error", "unreadable", rel, 0, f"{type(exc).__name__}: {exc}")]

    operational = operational_override or is_operational_path(rel)
    fixture = (is_test_fixture_path(rel) or is_quarantined(rel)) and not operational_override
    scientific_control = inspect_scientific_control_contract(source, rel)
    in_docstring = False
    for line_no, line in enumerate(lines, start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith(("#", "//", "/*", "*")):
            continue
        triple_count = line.count('"""') + line.count("'''")
        docstring_line = in_docstring or triple_count > 0
        for code, pattern in BLOCK_PATTERNS:
            if not pattern.search(line):
                continue
            if detector_definition_context(line, rel, code):
                continue
            if scientific_control.proven:
                if (
                    code == "mock_or_synthetic_marker"
                    and not _scientific_control_fabrication_line(line)
                ):
                    continue
                if (
                    code == "numpy_random_runtime"
                    and line_no in scientific_control.allowed_seeded_prng_lines
                    and not _scientific_control_fabrication_line(line)
                ):
                    continue
            if code == "mock_or_synthetic_marker" and (
                approved_runtime_context(line) or non_data_marker_context(line, rel)
            ):
                continue
            if fixture:
                severity = "fixture"
            elif docstring_line:
                severity = "warning"
            elif code == "mock_or_synthetic_marker" and operational:
                severity = "error"
            elif code in {"python_random_runtime", "numpy_random_runtime", "js_random_runtime"} and not random_line_is_metric_like(line, rel):
                severity = "warning"
            elif code == "mock_or_synthetic_marker":
                severity = "warning"
            elif operational:
                severity = "error"
            else:
                severity = "warning"
            findings.append(Finding(severity, code, rel, line_no, stripped[:240]))
        if triple_count % 2 == 1:
            in_docstring = not in_docstring
    findings.extend(scan_python_ast(path, root, operational_override=operational_override))
    return findings


def _module_name_for_path(path: str) -> str:
    if not path.endswith(".py"):
        return ""
    module = path[:-3].replace("/", ".")
    return module[:-9] if module.endswith(".__init__") else module


def find_live_simulation_imports(paths: Iterable[Path], root: Path) -> tuple[set[str], list[Finding]]:
    python_paths = [path for path in paths if path.suffix.lower() == ".py"]
    module_paths = {
        _module_name_for_path(rel_posix(path, root)): rel_posix(path, root)
        for path in python_paths
    }
    promoted: set[str] = set()
    findings: list[Finding] = []
    seen: set[tuple[str, str]] = set()

    for importer in python_paths:
        importer_rel = rel_posix(importer, root)
        if not is_operational_path(importer_rel):
            continue
        try:
            tree = ast.parse(
                importer.read_text(encoding="utf-8", errors="replace"),
                filename=importer_rel,
            )
        except (OSError, SyntaxError, ValueError):
            continue

        for node in ast.walk(tree):
            imported_modules: list[str] = []
            if isinstance(node, ast.Import):
                imported_modules.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                imported_modules.append(node.module)
                imported_modules.extend(f"{node.module}.{alias.name}" for alias in node.names)
            else:
                continue

            for module_name in imported_modules:
                target_rel = module_paths.get(module_name)
                if (
                    not target_rel
                    or not target_rel.startswith(LIVE_NAMED_SIMULATION_PREFIX)
                    or not Path(target_rel).stem.endswith("_live")
                ):
                    continue
                identity = (importer_rel, target_rel)
                if identity in seen:
                    continue
                seen.add(identity)
                promoted.add(target_rel)
                findings.append(
                    Finding(
                        "warning",
                        "operational_imports_live_simulation_module",
                        importer_rel,
                        int(getattr(node, "lineno", 0) or 0),
                        f"imports {target_rel}",
                    )
                )

    return promoted, findings


def validate_registry(root: Path) -> list[Finding]:
    findings: list[Finding] = []
    registry = load_source_registry(root)
    sources = registry.get("sources", {})
    if not isinstance(sources, dict):
        return [Finding("error", "source_registry_invalid", "data/real_data_sources.json", 0, "sources must be object")]
    for source_id, source in sources.items():
        if not isinstance(source, dict):
            findings.append(Finding("error", "source_registry_invalid", "data/real_data_sources.json", 0, str(source_id)))
            continue
        for key in ("name", "category", "endpoint", "freshness_ttl_sec", "derived_metrics_allowed"):
            if key not in source:
                findings.append(
                    Finding("error", "source_registry_missing_field", "data/real_data_sources.json", 0, f"{source_id}.{key}")
                )
        demo_key_marker = "DEMO" + "_KEY"
        if demo_key_marker in json.dumps(source):
            findings.append(Finding("error", "source_registry_demo_key", "data/real_data_sources.json", 0, str(source_id)))
    return findings


def validate_public_metric_json(path: Path, root: Path, source_ids: set[str]) -> list[Finding]:
    rel = rel_posix(path, root)
    findings: list[Finding] = []
    try:
        payload = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except Exception:
        return findings

    metric_envelope_keys = {
        "source_id",
        "source_name",
        "source_url",
        "collected_at",
        "freshness_ttl_sec",
        "is_operational_metric",
    }

    def walk(value: Any, trail: str) -> None:
        if isinstance(value, dict):
            if "truth_status" in value:
                if metric_envelope_keys & set(value):
                    try:
                        validate_metric_envelope(value, registry_source_ids=source_ids)
                    except ValueError as exc:
                        findings.append(Finding("error", "invalid_metric_envelope", rel, 0, f"{trail}: {exc}"))
                    return
            for key, child in value.items():
                walk(child, f"{trail}.{key}" if trail else str(key))
        elif isinstance(value, list):
            for idx, child in enumerate(value):
                walk(child, f"{trail}[{idx}]")

    walk(payload, "")
    return findings


def run(root: Path, *, strict: bool = False, json_output: bool = False) -> int:
    findings: list[Finding] = []
    findings.extend(validate_registry(root))
    source_ids = registered_source_ids(root)
    if "test_fixture" not in source_ids:
        findings.append(Finding("error", "source_registry_missing_test_fixture", "data/real_data_sources.json", 0, ""))

    paths = list(iter_text_files(root))
    promoted_operational_paths, import_findings = find_live_simulation_imports(paths, root)
    findings.extend(import_findings)

    for path in paths:
        rel = rel_posix(path, root)
        findings.extend(
            scan_text_file(
                path,
                root,
                operational_override=rel in promoted_operational_paths,
            )
        )
        if rel.startswith("frontend/public/") and path.suffix.lower() == ".json":
            findings.extend(validate_public_metric_json(path, root, source_ids))

    error_count = sum(1 for item in findings if item.severity == "error")
    warning_count = sum(1 for item in findings if item.severity == "warning")
    fixture_count = sum(1 for item in findings if item.severity == "fixture")
    summary = {
        "schema_version": "aureon-real-data-contract-validation-v1",
        "root": str(root),
        "truth_statuses": sorted(TRUTH_STATUSES),
        "error_count": error_count,
        "warning_count": warning_count,
        "fixture_count": fixture_count,
        "source_count": len(source_ids),
        "findings": [item.to_dict() for item in findings],
    }

    if json_output:
        print(json.dumps(summary, indent=2, sort_keys=True))
    else:
        print(
            "real-data contract: "
            f"errors={error_count} warnings={warning_count} fixtures={fixture_count} sources={len(source_ids)}"
        )
        for item in findings[:200]:
            text = item.text.encode("ascii", errors="replace").decode("ascii")
            print(f"{item.severity.upper()} {item.code} {item.path}:{item.line} {text}")
        if len(findings) > 200:
            print(f"... {len(findings) - 200} additional findings omitted")

    return 1 if error_count or (strict and warning_count) else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--strict", action="store_true", help="Treat warnings as failure.")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    args = parser.parse_args(argv)
    root = repo_root_from(Path(args.repo_root))
    return run(root, strict=args.strict, json_output=args.json)


if __name__ == "__main__":
    raise SystemExit(main())

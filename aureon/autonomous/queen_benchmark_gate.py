"""Verification gate for the Queen's self-repair.

A repair counts only when it is proved, not when the suite happens to pass:

(a) the benchmark-derived seed tests in tests/queen_benchmarks pass after the fix;
(b) the fix is paired with a test that FAILED before the edit and PASSES after
    (the original red test, plus a Queen-authored regression test under
    tests/queen_authored that is itself checked red-then-green);
(c) no test file was weakened: no test file removed, no test or assert lost,
    no skip/xfail added.

It also runs a "silent wrong" check: mutants of the pricing functions must be
caught by the seed tests (a set that catches none is blind), and the
recorded benchmark outputs are compared with what the code produces now.

Offline, no keys, no network, no orders. Nothing is pushed.

    python -m aureon.autonomous.queen_benchmark_gate --root /path/to/repo
"""

from __future__ import annotations

import argparse
import ast
import copy
import hashlib
import importlib
import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

SEED_DIR = "tests/queen_benchmarks"
AUTHORED_DIR = "tests/queen_authored"
PRICING_TESTS = f"{SEED_DIR}/test_queen_bench_pricing.py"
MUTANT_ENV = "QUEEN_MUTANT_SPEC"

# The real pricing / sizing / fee maths the seed pricing tests pin.
PRICING_TARGETS: tuple[tuple[str, str], ...] = (
    ("aureon.exchanges.single_currency_equity", "nonnegative_amount"),
    ("aureon.exchanges.single_currency_equity", "gbp_equity_from_balances"),
    ("aureon.exchanges.single_currency_equity", "currency_amount_map"),
    ("aureon.exchanges.single_currency_equity", "assemble_sterling_snapshot"),
    ("aureon.exchanges.capital_cfd_trader", "CapitalCFDTrader._required_tp_pct_for_profit"),
    ("aureon.exchanges.capital_cfd_trader", "CapitalCFDTrader._estimate_capital_margin_required"),
    ("aureon.exchanges.capital_cfd_trader", "CapitalCFDTrader._capital_cost_profile"),
    ("aureon.exchanges.capital_cfd_trader", "CapitalCFDTrader._scaled_preflight"),
    ("aureon.exchanges.kraken_client", "_finite_decimal"),
    ("aureon.exchanges.kraken_client", "KrakenClient.compute_order_fees_in_quote"),
)

_BIN_SWAP = {ast.Add: ast.Sub, ast.Sub: ast.Add, ast.Mult: ast.Div, ast.Div: ast.Mult}
_CMP_SWAP = {ast.Lt: ast.GtE, ast.GtE: ast.Lt, ast.Gt: ast.LtE, ast.LtE: ast.Gt,
             ast.Eq: ast.NotEq, ast.NotEq: ast.Eq}
_SKIP_NAMES = {"skip", "skipif", "xfail", "importorskip"}


# ── pytest helpers ──────────────────────────────────────────────────────────


def _pytest_paths(root: Path, paths: list[str], env_extra: dict[str, str] | None = None,
                  timeout: int = 300) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1",
               AUREON_LLM_OFFLINE="1", AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS="1")
    env.update(env_extra or {})
    return subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "--tb=line", "-p", "no:cacheprovider", *paths],
        cwd=root, text=True, capture_output=True, timeout=timeout, env=env,
    )


def failed_nodeids(output: str) -> set[str]:
    import re

    return set(re.findall(r"^(?:FAILED|ERROR)\s+(\S+::\S+)", output or "", re.MULTILINE))


def run_seed_benchmarks(root: Path) -> dict[str, Any]:
    """(a) the benchmark seed set must pass. Absent seed dir is reported, not faked."""

    if not (root / SEED_DIR).is_dir():
        return {"present": False, "ok": True, "reason": "no tests/queen_benchmarks in this root"}
    try:
        done = _pytest_paths(root, [SEED_DIR])
    except subprocess.TimeoutExpired:
        return {"present": True, "ok": False, "reason": "seed benchmarks timed out"}
    tail = [line for line in (done.stdout or "").splitlines() if line.strip()][-1:]
    return {"present": True, "ok": done.returncode == 0, "returncode": done.returncode,
            "summary": tail[0] if tail else "", "failed": sorted(failed_nodeids(done.stdout))}


# ── (c) weakening census ────────────────────────────────────────────────────


def _is_test_file(relative: str) -> bool:
    name = relative.rsplit("/", 1)[-1]
    return relative.endswith(".py") and (name.startswith("test_") or relative.startswith("tests/"))


def census_tests(root: Path) -> dict[str, dict[str, int]]:
    """Per test file: test functions, assert statements, skip/xfail markers."""

    census: dict[str, dict[str, int]] = {}
    for path in sorted(root.rglob("*.py")):
        if any(part in {".git", "__pycache__", "state", "queen_backups", ".venv", "node_modules"}
               for part in path.parts):
            continue
        relative = path.relative_to(root).as_posix()
        if not _is_test_file(relative):
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (OSError, SyntaxError, UnicodeDecodeError):
            census[relative] = {"tests": 0, "asserts": 0, "skips": 0, "unparsed": 1}
            continue
        tests = asserts = skips = 0
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test_"):
                tests += 1
            elif isinstance(node, ast.Assert):
                asserts += 1
            elif isinstance(node, ast.Attribute) and node.attr in _SKIP_NAMES:
                skips += 1
        census[relative] = {"tests": tests, "asserts": asserts, "skips": skips}
    return census


def weakened(before: dict[str, dict[str, int]], after: dict[str, dict[str, int]]) -> list[str]:
    reasons: list[str] = []
    for relative, counts in before.items():
        now = after.get(relative)
        if now is None:
            reasons.append(f"{relative}: test file removed")
            continue
        if now["tests"] < counts["tests"]:
            reasons.append(f"{relative}: tests {counts['tests']} -> {now['tests']}")
        if now["asserts"] < counts["asserts"]:
            reasons.append(f"{relative}: asserts {counts['asserts']} -> {now['asserts']}")
        if now["skips"] > counts["skips"]:
            reasons.append(f"{relative}: skips {counts['skips']} -> {now['skips']}")
    for relative, now in after.items():
        if relative not in before and now["skips"] > 0:
            reasons.append(f"{relative}: new test file adds {now['skips']} skip(s)")
    return reasons


# ── (b) Queen-authored regression test, red then green ─────────────────────


def author_regression_test(root: Path, repairs: list[dict[str, Any]], architect: Any) -> str | None:
    """Write one regression test per proved implementation repair.

    The Queen's architect has no test-authoring method; this composes the test
    from the proof the repair was derived from (function, args, expected) and
    writes it with her own writer. A name_error repair has no value proof, so
    it gets no authored test (its original red test still pairs it).
    """

    cases: list[tuple[str, str, list[Any], Any, str]] = []
    seen: set[str] = set()
    for repair in repairs:
        module = repair.get("path", "")
        if repair.get("kind") != "implementation" or not module.endswith(".py"):
            continue
        dotted = module[:-3].replace("/", ".")
        for proof in repair.get("proof") or []:
            key = json.dumps([dotted, proof["function"], proof["args"], proof["expected"]], default=str)
            if key in seen:
                continue
            seen.add(key)
            cases.append((dotted, proof["function"], list(proof["args"]), proof["expected"],
                          f"{proof.get('test')}::{proof.get('test_name')}"))
    if not cases:
        return None
    digest = hashlib.sha1(json.dumps([c[:4] for c in cases], default=str).encode()).hexdigest()[:10]
    lines = [
        '"""Queen-authored regression tests (self-repair). Each pins a value that was',
        'red before her repair and must stay green. Do not weaken."""',
        "",
        "import importlib",
        "import sys",
        "from pathlib import Path",
        "",
        "sys.path.insert(0, str(Path(__file__).resolve().parents[2]))",
        "",
    ]
    for index, (dotted, function, args, expected, source) in enumerate(cases):
        lines += [
            "",
            f"def test_qa_{function}_{digest}_{index}():",
            f"    # source: {source}",
            f"    fn = getattr(importlib.import_module({dotted!r}), {function!r})",
            f"    assert fn(*{args!r}) == {expected!r}",
            "",
        ]
    relative = f"{AUTHORED_DIR}/test_qa_{digest}.py"
    if not architect.write_file(relative, "\n".join(lines), backup=False):
        return None
    return relative


def _head_source(root: Path, relative: str) -> bytes | None:
    done = subprocess.run(["git", "show", f"HEAD:{relative}"], cwd=root, capture_output=True, timeout=30)
    return done.stdout if done.returncode == 0 else None


def red_then_green(root: Path, test_path: str, repaired_paths: list[str]) -> dict[str, Any]:
    """Run test_path against the pre-repair sources (HEAD), then the repaired ones."""

    fixed: dict[str, bytes] = {}  # bytes, so CRLF files keep their line endings
    try:
        for relative in repaired_paths:
            original = _head_source(root, relative)
            if original is None:
                return {"red_before": False, "green_after": False, "reason": f"no HEAD source for {relative}"}
            fixed[relative] = (root / relative).read_bytes()
            (root / relative).write_bytes(original)
        red = _pytest_paths(root, [test_path], timeout=120).returncode != 0
    finally:
        for relative, content in fixed.items():
            (root / relative).write_bytes(content)
    green = _pytest_paths(root, [test_path], timeout=120).returncode == 0
    return {"red_before": red, "green_after": green}


def verify_repair(root: Path, *, census_before: dict[str, dict[str, int]], red_before: set[str],
                  repairs: list[dict[str, Any]], architect: Any) -> dict[str, Any]:
    """Return the gate verdict. ``verified`` is True only when (a), (b) and (c) all hold."""

    paths = sorted({item["path"] for item in repairs if item.get("path")})
    gate: dict[str, Any] = {"paired_red_tests": sorted(red_before)}
    gate["seed_benchmarks"] = run_seed_benchmarks(root)
    authored = author_regression_test(root, repairs, architect)
    gate["authored_test"] = authored
    if authored:
        gate["authored_red_green"] = red_then_green(root, authored, paths)
    else:
        gate["authored_reason"] = "no value proof to author from (name_error repair)" if repairs else "no repairs"
    gate["weakened"] = weakened(census_before, census_tests(root))
    reasons: list[str] = []
    if not gate["seed_benchmarks"]["ok"]:
        reasons.append("seed_benchmarks_failed")
    if not red_before:
        reasons.append("no_red_test_before_fix")
    rg = gate.get("authored_red_green")
    if rg is not None and not (rg.get("red_before") and rg.get("green_after")):
        reasons.append("authored_test_not_red_then_green")
    if gate["weakened"]:
        reasons.append("test_weakened")
    gate["verified"] = not reasons
    gate["reasons"] = reasons
    return gate


# ── silent-wrong: mutation check ───────────────────────────────────────────


def _resolve(module_name: str, qualname: str) -> tuple[Any, Any, str]:
    module = importlib.import_module(module_name)
    owner: Any = module
    parts = qualname.split(".")
    for part in parts[:-1]:
        owner = getattr(owner, part)
    return module, owner, parts[-1]


def _function_node(module: Any, qualname: str) -> ast.FunctionDef:
    tree = ast.parse(Path(module.__file__).read_text(encoding="utf-8"))
    body: list[ast.stmt] = tree.body
    node: Any = None
    for part in qualname.split("."):
        node = next((n for n in body if isinstance(n, (ast.FunctionDef, ast.ClassDef)) and n.name == part), None)
        if node is None:
            raise LookupError(qualname)
        body = node.body
    return node


def _sites(fn: ast.FunctionDef) -> list[tuple[int, str, int]]:
    sites: list[tuple[int, str, int]] = []
    for index, node in enumerate(ast.walk(fn)):
        line = getattr(node, "lineno", 0)
        if isinstance(node, ast.BinOp) and type(node.op) in _BIN_SWAP:
            sites.append((index, f"{type(node.op).__name__}->{_BIN_SWAP[type(node.op)].__name__}", line))
        elif isinstance(node, ast.Compare) and len(node.ops) == 1 and type(node.ops[0]) in _CMP_SWAP:
            sites.append((index, f"{type(node.ops[0]).__name__}->{_CMP_SWAP[type(node.ops[0])].__name__}", line))
        elif (isinstance(node, ast.Constant) and isinstance(node.value, (int, float))
              and not isinstance(node.value, bool)):
            sites.append((index, f"const {node.value!r}->{_perturb(node.value)!r}", line))
    return sites


def _perturb(value: int | float) -> int | float:
    if isinstance(value, int):
        return value + 1
    return value * 1.5 if value else 1.0


def mutants(module_name: str, qualname: str) -> list[dict[str, Any]]:
    module, _owner, _name = _resolve(module_name, qualname)
    fn = _function_node(module, qualname)
    return [{"module": module_name, "qualname": qualname, "site": site, "line": line, "change": change}
            for site, change, line in _sites(fn)]


def apply_mutant(spec: dict[str, Any]) -> None:
    """Swap one mutated function into its module/class (used by the seed conftest)."""

    module, owner, name = _resolve(spec["module"], spec["qualname"])
    fn = copy.deepcopy(_function_node(module, spec["qualname"]))
    for index, node in enumerate(ast.walk(fn)):
        if index != spec["site"]:
            continue
        if isinstance(node, ast.BinOp):
            node.op = _BIN_SWAP[type(node.op)]()
        elif isinstance(node, ast.Compare):
            node.ops = [_CMP_SWAP[type(node.ops[0])]()]
        elif isinstance(node, ast.Constant):
            node.value = _perturb(node.value)
        break
    tree = ast.fix_missing_locations(ast.Module(body=[fn], type_ignores=[]))
    namespace: dict[str, Any] = {}
    exec(compile(tree, module.__file__, "exec"), module.__dict__, namespace)  # noqa: S102 - local mutant
    setattr(owner, name, namespace[name])


def mutation_check(root: Path, targets: tuple[tuple[str, str], ...] = PRICING_TARGETS,
                   workers: int = 4) -> dict[str, Any]:
    if not (root / PRICING_TESTS).is_file():
        return {"ran": False, "reason": f"{PRICING_TESTS} missing"}
    baseline = _pytest_paths(root, [PRICING_TESTS])
    if baseline.returncode != 0:
        return {"ran": False, "reason": "pricing seed tests fail unmutated; mutation score meaningless",
                "failed": sorted(failed_nodeids(baseline.stdout))}
    specs: list[dict[str, Any]] = []
    unreadable: list[str] = []
    for module_name, qualname in targets:
        try:
            specs.extend(mutants(module_name, qualname))
        except Exception as exc:  # a target that cannot be read is reported, not dropped silently
            unreadable.append(f"{module_name}:{qualname}: {type(exc).__name__}")

    def _run(spec: dict[str, Any]) -> dict[str, Any]:
        try:
            done = _pytest_paths(root, [PRICING_TESTS, "-x"], {MUTANT_ENV: json.dumps(spec)}, timeout=180)
            return {**spec, "killed": done.returncode != 0, "returncode": done.returncode}
        except subprocess.TimeoutExpired:
            return {**spec, "killed": True, "returncode": "timeout"}

    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        results = list(pool.map(_run, specs))
    per_target: dict[str, dict[str, int]] = {}
    for item in results:
        row = per_target.setdefault(item["qualname"], {"mutants": 0, "killed": 0})
        row["mutants"] += 1
        row["killed"] += int(bool(item.get("killed")))
    killed = sum(1 for item in results if item.get("killed"))
    blind = sorted(name for name, row in per_target.items() if row["mutants"] and row["killed"] == 0)
    return {
        "ran": True,
        "mutants": len(results),
        "killed": killed,
        "survived": [{"qualname": r["qualname"], "line": r.get("line"), "change": r["change"]}
                     for r in results if not r.get("killed")],
        "score": round(killed / len(results), 4) if results else 0.0,
        "per_target": per_target,
        "blind_targets": blind,
        "blind": killed == 0,
        "unreadable_targets": unreadable,
    }


# ── silent-wrong: drift against recorded benchmark values ──────────────────


def drift_check(root: Path) -> dict[str, Any]:
    out: dict[str, Any] = {"drift": [], "held": []}
    cog_rec = root / "data/research/cognition_benchmark_results.json"
    if cog_rec.is_file():
        from aureon.operator.cognition_benchmark import run as run_cognition

        recorded = json.loads(cog_rec.read_text(encoding="utf-8"))
        current = run_cognition(root / "data/research/cognition_benchmark_prompts.json",
                                root / "data/research/cognition_benchmark_recordings.json")
        for condition in ("baseline", "cognition"):
            for key, value in recorded[condition]["metrics"].items():
                now = current[condition]["metrics"].get(key)
                if now != value:
                    out["drift"].append({"benchmark": "cognition_benchmark", "field": f"{condition}.{key}",
                                         "recorded": value, "current": now})
    else:
        out["held"].append("cognition_benchmark: no recorded results file")
    soul_rec = root / "docs/research/benchmarks/soul_deliberation_benchmark.json"
    if soul_rec.is_file():
        from aureon.core.soul_benchmark import run_soul_benchmark

        recorded = json.loads(soul_rec.read_text(encoding="utf-8"))
        current = run_soul_benchmark()
        for rung, values in recorded["rungs"].items():
            for key, value in values.items():
                now = (current["rungs"].get(rung) or {}).get(key)
                if now != value:
                    out["drift"].append({"benchmark": "soul_deliberation", "field": f"{rung}.{key}",
                                         "recorded": value, "current": now})
        now_ok = {c["check"]: c["ok"] for c in current["checks"]}
        for check in recorded["checks"]:
            if check["ok"] and now_ok.get(check["check"]) is False:
                out["drift"].append({"benchmark": "soul_deliberation", "field": f"check:{check['check']}",
                                     "recorded": True, "current": False})
    else:
        out["held"].append("soul_deliberation: no recorded benchmark json")
    out["held"].append("gate_switchboard: no recorded artifact on disk; seed logic tests assert its critical tier")
    out["drift_count"] = len(out["drift"])
    return out


def silent_wrong_check(root: Path, *, mutation: bool = True, relay: bool = True) -> dict[str, Any]:
    from aureon.autonomous.self_repair_guard import append_review

    root = root.resolve()
    report: dict[str, Any] = {"schema": "aureon.queen-benchmark-gate.v1", "root": str(root)}
    report["mutation"] = mutation_check(root) if mutation else {"ran": False, "reason": "disabled"}
    try:
        report["drift"] = drift_check(root)
    except Exception as exc:
        report["drift"] = {"error": f"{type(exc).__name__}: {exc}"[:300]}
    m, d = report["mutation"], report["drift"]
    summary = {
        "mutants": m.get("mutants"), "killed": m.get("killed"), "score": m.get("score"),
        "blind": m.get("blind"), "blind_targets": m.get("blind_targets"),
        "drift_count": d.get("drift_count"),
        "drift_fields": [f"{x['benchmark']}:{x['field']}" for x in d.get("drift", [])][:20],
    }
    report["summary"] = summary
    try:
        append_review(root, "silent_wrong_check", reason="mutation_and_drift", **summary)
    except Exception:
        pass
    if relay:
        try:
            from aureon.core.aureon_baton_link import relay_state

            relay_state("queen.self_repair", "seeing", {"silent_wrong": summary})
        except Exception:
            pass
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Queen benchmark gate: mutation + drift check.")
    parser.add_argument("--root", required=True)
    parser.add_argument("--no-mutation", action="store_true")
    parser.add_argument("--no-relay", action="store_true", help="caller relays the summary itself")
    args = parser.parse_args(argv)
    report = silent_wrong_check(Path(args.root), mutation=not args.no_mutation, relay=not args.no_relay)
    print(json.dumps(report, indent=2, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

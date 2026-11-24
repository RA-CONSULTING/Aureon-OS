"""Pin every ORCA call site that reads Capital.com positions to the CN50 guard.

Each read of ``<capital>.get_positions()`` in the ORCA bots must be the first
argument of ``split_owned_positions(...)`` from ``orca_capital_ownership`` and
must keep only the owned half (``[0]`` or the first name of a tuple unpack).
The tests are parametrised per call site, so removing or bypassing the guard at
any one site fails that site's test, whatever wrapper replaces it. The count
test fails if a site disappears or a new unguarded one appears.

Static (AST) check: these bots are 1k-20k line modules whose Capital paths need
live clients, clocks and state files; the radar monitor and kill chain also have
behavioural CN50 tests in test_orca_skips_unplanned_capital_position.py.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]

# path -> number of Capital position reads, every one of which must be guarded.
PINNED = {
    "aureon/bots/orca_unified_kill_chain.py": 1,
    "aureon/bots/orca_complete_kill_cycle.py": 4,
    "aureon_radar/bots/orca_complete_kill_cycle.py": 4,
    "aureon_radar/bots/orca_unified_kill_chain.py": 1,
    "aureon_radar/bots/orca_live_monitor.py": 1,
}
GUARD = "split_owned_positions"
GUARD_MODULE = "aureon.exchanges.orca_capital_ownership"


def _tree(rel: str) -> ast.Module:
    return ast.parse((REPO / rel).read_bytes().decode("utf-8", errors="replace"), filename=rel)


def _parents(tree: ast.AST) -> dict:
    parents = {}
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            parents[child] = node
    return parents


def _is_capital_read(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "get_positions"
        and "capital" in ast.unparse(node.func.value).lower()
    )


def _sites(rel: str):
    """[(site_id, call_node, parents)] in source order; id = enclosing function + ordinal."""
    tree = _tree(rel)
    parents = _parents(tree)
    sites, seen = [], {}
    for node in sorted((n for n in ast.walk(tree) if _is_capital_read(n)), key=lambda n: (n.lineno, n.col_offset)):
        owner, cur = "<module>", node
        while cur in parents:
            cur = parents[cur]
            if isinstance(cur, (ast.FunctionDef, ast.AsyncFunctionDef)):
                owner = cur.name
                break
        seen[owner] = seen.get(owner, 0) + 1
        sites.append((f"{owner}#{seen[owner]}", node, parents))
    return sites


def _guard_problem(call: ast.Call, parents: dict) -> str | None:
    wrap = parents.get(call)
    if not (isinstance(wrap, ast.Call) and isinstance(wrap.func, ast.Name) and wrap.func.id == GUARD
            and wrap.args and wrap.args[0] is call):
        return "Capital positions read without split_owned_positions(...)"
    use = parents.get(wrap)
    if isinstance(use, ast.Subscript) and use.value is wrap:
        if isinstance(use.slice, ast.Constant) and use.slice.value == 0:
            return None
        return "split_owned_positions(...) result indexed with something other than [0] (owned)"
    if isinstance(use, ast.Assign) and use.value is wrap and isinstance(use.targets[0], ast.Tuple):
        return None
    return "split_owned_positions(...) result not reduced to the owned list"


SITE_PARAMS = [
    pytest.param(rel, site_id, id=f"{rel}::{site_id}")
    for rel in PINNED
    for site_id, _node, _parents_map in _sites(rel)
]


@pytest.mark.parametrize("rel,site_id", SITE_PARAMS)
def test_capital_call_site_is_guarded(rel, site_id):
    node, parents = next((n, p) for s, n, p in _sites(rel) if s == site_id)
    problem = _guard_problem(node, parents)
    assert problem is None, f"{rel}:{node.lineno} ({site_id}): {problem}"


@pytest.mark.parametrize("rel", list(PINNED))
def test_capital_call_site_count_is_pinned(rel):
    sites = _sites(rel)
    guarded = [s for s, n, p in sites if _guard_problem(n, p) is None]
    assert len(sites) == PINNED[rel], f"{rel}: {len(sites)} Capital reads, expected {PINNED[rel]}"
    assert len(guarded) == PINNED[rel], f"{rel}: only {len(guarded)} of {PINNED[rel]} reads guarded"


@pytest.mark.parametrize("rel", list(PINNED))
def test_guard_name_is_the_real_ownership_filter(rel):
    tree = _tree(rel)
    imported = any(
        isinstance(n, ast.ImportFrom) and n.module == GUARD_MODULE and any(a.name == GUARD and a.asname in (None, GUARD) for a in n.names)
        for n in ast.walk(tree)
    )
    assert imported, f"{rel}: {GUARD} is not imported from {GUARD_MODULE}"
    shadowing = [
        n.lineno for n in ast.walk(tree)
        if (isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and n.name == GUARD)
        or (isinstance(n, ast.Name) and n.id == GUARD and isinstance(n.ctx, ast.Store))
        or (isinstance(n, ast.alias) and n.asname == GUARD and n.name != GUARD)
    ]
    assert not shadowing, f"{rel}: {GUARD} is redefined at lines {shadowing}"

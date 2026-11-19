"""The /api/organism status read must never import the Queen module tree.

A plain ``import aureon.utils.aureon_queen_hive_mind`` loads the unified
ecosystem and, through it, every exchange client (Buzz, 13 Nov 2026). The
status read only reports Queen children when that module is already loaded.
"""

from __future__ import annotations

import subprocess
import sys
import textwrap


def _run(code: str) -> str:
    out = subprocess.run(
        [sys.executable, "-c", textwrap.dedent(code)],
        capture_output=True,
        text=True,
        timeout=300,
        check=True,
    )
    return out.stdout.strip().splitlines()[-1]


def test_organism_payload_does_not_import_the_queen_or_exchanges() -> None:
    last = _run(
        """
        import sys
        from aureon.saas.gateway import build_organism_payload
        payload = build_organism_payload()
        queen = "aureon.utils.aureon_queen_hive_mind" in sys.modules
        exchanges = sorted(m for m in sys.modules if m == "aureon.exchanges" or m.startswith("aureon.exchanges."))
        print(repr((queen, exchanges, payload.get("queen_children", "absent"))))
        """
    )
    queen, exchanges, children = eval(last)  # noqa: S307 - our own repr
    assert queen is False
    assert exchanges == []
    assert children is None


def test_organism_payload_reads_an_already_loaded_queen() -> None:
    last = _run(
        """
        import sys, types
        fake = types.ModuleType("aureon.utils.aureon_queen_hive_mind")
        fake._QUEEN = types.SimpleNamespace(children={"a": 1, "b": 2})
        sys.modules["aureon.utils.aureon_queen_hive_mind"] = fake
        from aureon.saas.gateway import build_organism_payload
        print(repr(build_organism_payload().get("queen_children", "absent")))
        """
    )
    assert eval(last) == 2  # noqa: S307 - our own repr

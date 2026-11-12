"""Offline fixture loader for the public gallery.

The module reads JSON under ``examples/offline/fixtures``. It does not open a
socket. Importing it forces the offline flags before any ``aureon`` import
in the three gallery commands.
"""

from __future__ import annotations

import errno
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

# Source files the join citation reads. They are copied into the sandbox and
# are not imported as a trader and are not executed.
_CITED_SOURCES = (
    "aureon/trading/aureon_auris_trader.py",
    "aureon/core/hnc_field.py",
    "frontend/src/core/aurisNodes.ts",
)

os.environ["AUREON_LLM_OFFLINE"] = "1"
os.environ["AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS"] = "1"
os.environ["AUREON_DISABLE_REAL_ORDERS"] = "1"
os.environ["AUREON_LIVE_TRADING"] = "0"

GALLERY = Path(__file__).resolve().parent
ROOT = GALLERY.parents[1]
FIXTURES = GALLERY / "fixtures"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

BANNER = (
    "Release boundary: HOLD. This gallery is not a production-ready release. "
    "Live trading is off. No order is placed. The public pin and the orange badge stay."
)
PUBLIC_PIN = "0646146c53e59dbcab41363a613d5651c9c9d50f"
CONTAINMENT_PIN = "34864ff0547d2cff03e707414743a3b0cc8770b5"
FETCHED_AT = "2026-11-05T00:00:00Z"


def _refuse_live_fetch(url: str, timeout: float = 20.0) -> tuple[int, bytes]:
    raise RuntimeError(f"offline gallery refuses a live fetch: {url}")


def seal_market_series() -> None:
    """Point the module HTTP helper at a function that always raises."""

    from aureon.evaluation import market_series

    market_series.http_get = _refuse_live_fetch


def fixture_transport(url: str) -> tuple[int, bytes]:
    """Return a committed body. Binance is refused so the Kraken fixture is the pack."""

    if "binance.com" in url:
        return 451, b"fixture refuses binance"
    if "api.kraken.com/0/public/OHLC" in url:
        return 200, (FIXTURES / "kraken_ohlc.json").read_bytes()
    if "api.kraken.com/0/public/Spread" in url:
        return 200, (FIXTURES / "kraken_spread.json").read_bytes()
    raise RuntimeError(f"offline gallery has no fixture for {url}")


def load_fixture_pack(root: Path) -> dict[str, Any]:
    """Build a sandbox pack from fixtures and load it back. No network."""

    from aureon.evaluation.market_series import (
        fetch_public_pack,
        load_market_series,
        verify_pack,
        write_pack,
    )

    seal_market_series()
    pack = fetch_public_pack(fixture_transport, fetched_at=FETCHED_AT)
    problems = verify_pack(pack)
    if problems:
        raise RuntimeError("; ".join(problems))
    write_pack(root / "reports" / "measured", pack)
    loaded = load_market_series(root)
    if loaded.get("verdict") != "loaded":
        raise RuntimeError(f"fixture pack did not load: {loaded.get('reason')}")
    if loaded.get("orders_placed") is not False or loaded.get("live_trading") is not False:
        raise RuntimeError("fixture pack claims trading")
    if loaded.get("key_group") != "public:kraken" or loaded.get("authenticated") is not False:
        raise RuntimeError("fixture pack is not the public Kraken fixture")
    return loaded


def cold_child() -> tuple[dict[str, Any], str]:
    """Return the fixture child and the parent net namespace string."""

    payload = json.loads((FIXTURES / "cold_boot_child.json").read_text(encoding="utf-8"))
    if payload.get("evidence_tag") != "fixture" or payload.get("measured_on_this_machine") is not False:
        raise RuntimeError("cold-boot fixture is not labelled as an offline fixture")
    return _resolve(payload["child"]), str(payload["parent_net_ns"])


def _resolve(node: Any) -> Any:
    if isinstance(node, dict):
        resolved: dict[str, Any] = {}
        for key, value in node.items():
            if key == "errno_name":
                resolved["errno"] = getattr(errno, str(value))
            else:
                resolved[key] = _resolve(value)
        return resolved
    if isinstance(node, list):
        return [_resolve(item) for item in node]
    return node


def pin_and_badge_still_hold() -> None:
    """Read the pin and the orange badge. This does not write either file."""

    guard = (ROOT / "mcp" / "aureon_public" / "guard_loader.py").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    if f'PINNED_COMMIT = "{PUBLIC_PIN}"' not in guard:
        raise RuntimeError("public pin text is not the recorded pin")
    if "release%20boundary-HOLD-orange" not in readme:
        raise RuntimeError("orange release-boundary badge is missing")


def run_market() -> int:
    """Load the fixture pack and run ``market_series --check`` on that sandbox."""

    from aureon.evaluation.market_series import main as market_main

    print(BANNER)
    with tempfile.TemporaryDirectory(prefix="aureon-offline-market-") as directory:
        root = Path(directory)
        loaded = load_fixture_pack(root)
        code = market_main(["--check", "--out", str(root / "reports" / "measured")])
    pin_and_badge_still_hold()
    print(
        f"market series {loaded['verdict']} {loaded['key_group']} {loaded['symbol']} "
        f"bars={loaded['bar_count']} orders_placed={loaded['orders_placed']} "
        f"live_trading={loaded['live_trading']} authenticated={loaded['authenticated']}"
    )
    print("sandbox check exit", code)
    print(
        "fixture note: kraken_ohlc.json and kraken_spread.json are synthetic public-shaped bodies. "
        "No venue was contacted."
    )
    print("reports/measured in the checkout was not written")
    return 0 if code == 0 else int(code)


def _stage_cited_sources(root: Path) -> None:
    """Copy the files the join citation reads. The copies are not executed."""

    for relative in _CITED_SOURCES:
        source = ROOT / relative
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(source.read_bytes())


def run_brain() -> int:
    """Run ``evaluate_brain`` on the fixture sandbox. The derived column stays absent."""

    from aureon.evaluation.brain_proof import evaluate_brain, render_brain_markdown

    print(BANNER)
    seal_market_series()
    with tempfile.TemporaryDirectory(prefix="aureon-offline-brain-") as directory:
        root = Path(directory)
        load_fixture_pack(root)
        _stage_cited_sources(root)
        report = evaluate_brain(root)
        print(render_brain_markdown(report))
    pin_and_badge_still_hold()
    series = report["market_series"]
    trade = report["auris"]["trade_readiness"]
    print(
        f"brain schema={report['schema']} live_trading={report['live_trading']} "
        f"orders_placed={report['orders_placed']} market={series.get('verdict')} "
        f"trade={trade.get('verdict')} release_boundary={trade.get('release_boundary')}"
    )
    if report.get("live_trading") is not False or report.get("orders_placed") is not False:
        return 1
    if series.get("key_group") != "public:kraken":
        return 1
    if trade.get("release_boundary") != "HOLD" or trade.get("orders_placed") is not False:
        return 1
    print("derived series in this sandbox: absent, so that column stays HOLD")
    print(
        "fixture note: kraken_ohlc.json and kraken_spread.json are synthetic public-shaped bodies. "
        "No venue was contacted. "
        "The report tag measured means the pack verified, not that a venue was fetched."
    )
    print("reports/measured in the checkout was not written")
    return 0


def run_cold_boot() -> int:
    """Judge the fixture child. Does not call ``measure`` and does not write a receipt."""

    from aureon.containment.cold_boot import judge_default
    from aureon.containment.native import PIN as native_pin

    print(BANNER)
    # The committed stage-7 receipt records CONTAINMENT_PIN. native.PIN is the
    # later module require-pin. Both are historical; neither is PUBLIC_PIN.
    if native_pin == PUBLIC_PIN or CONTAINMENT_PIN == PUBLIC_PIN:
        print("a historical containment pin constant claims the live published pin")
        return 1
    child, parent_net_ns = cold_child()
    judged = judge_default(child, parent_net_ns)
    pin_and_badge_still_hold()
    print(f"fixture judge verdict: {judged['verdict']}")
    print(f"allowed at default: {judged['allowed_at_default']}")
    print("evidence tag: fixture. This is not a stage-7 measurement of this machine.")
    print(
        "python -m aureon.containment.cold_boot was not run. "
        "That command's measurer opens one control TCP handshake outside the namespace."
    )
    print(f"public require-pin left at {PUBLIC_PIN}. This gallery did not write it.")
    print(
        f"containment receipt pin left at {CONTAINMENT_PIN}. "
        f"module pin left at {native_pin}. pin_changed was not written."
    )
    print("Release boundary stays HOLD. Receipts 2, 3, 4, and 5 stay HOLD.")
    if judged["verdict"] != "pass" or judged["allowed_at_default"] != "none" or judged["failures"]:
        print(judged["failures"])
        return 1
    return 0

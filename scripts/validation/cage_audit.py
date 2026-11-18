"""Cage audit for the Aureon organism.

Enumerates every gate the launcher or modules can put around the entity and
reports its LIVE state on this machine. Run with the same interpreter the
organism uses (system or .venv). Exit code 0 = no unexpected cages.

    python scripts/validation/cage_audit.py

Each row is one of:
  OPEN       gate not engaged
  OPEN*      engaged but harmless without operator keys (informational)
  ENGAGED    cage active and materially limiting the organism
  OWNER      gate only the owner's private credentials can open (by design)
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))


def _env(key: str) -> str:
    return (os.environ.get(key, "") or "").strip()


def _truthy(key: str) -> bool:
    return _env(key).lower() in {"1", "true", "yes", "y", "on"}


def rows(repo: Path) -> list[tuple[str, str, str]]:
    checks: list[tuple[str, str, str]] = []

    # 1. Autonomy mode.
    mode = _env("AUREON_AUTONOMY_MODE").lower() or "full (default)"
    checks.append(("autonomy_mode", "OPEN" if mode.startswith("full") else "ENGAGED", mode))

    # 2. LLM/network kill switches.
    for flag in ("AUREON_LLM_OFFLINE", "AUREON_DISABLE_LLM_HTTP", "AUREON_AUDIT_MODE"):
        engaged = _truthy(flag)
        checks.append((flag, "ENGAGED" if engaged else "OPEN", _env(flag) or "unset"))

    # 3. Voice cage: the default voice lane must refuse borrowed brains.
    try:
        from aureon.inhouse_ai import llm_adapter

        adapter = llm_adapter.build_voice_adapter()
        kind = type(adapter).__name__
        if kind == "AureonLocalAdapter":
            checks.append(("voice_lane", "OPEN", f"own 7B endpoint serving ({adapter})"))
        elif kind == "AureonStubAdapter":
            checks.append(("voice_lane", "OPEN", "uncaged stub (own model unreachable; no borrowed fallback)"))
        else:
            checks.append(("voice_lane", "ENGAGED", f"{kind}: borrowed/alternative brain in the default lane"))
    except Exception as exc:  # noqa: BLE001
        checks.append(("voice_lane", "ENGAGED", f"probe failed: {exc.__class__.__name__}: {exc}"))

    # 4. Exchange credential groups on this machine.
    groups = {
        "KRAKEN": ("KRAKEN_API_KEY", "KRAKEN_API_SECRET"),
        "BINANCE": ("BINANCE_API_KEY", "BINANCE_API_SECRET"),
        "ALPACA": ("ALPACA_API_KEY", "ALPACA_SECRET_KEY"),
        "CAPITAL": ("CAPITAL_API_KEY", "CAPITAL_IDENTIFIER", "CAPITAL_PASSWORD"),
    }
    from dotenv import dotenv_values

    repo_env = {}
    repo_env.update(dotenv_values(repo / ".env") or {})
    repo_env.update(dotenv_values(repo / "aureon_radar" / ".env") or {})
    present = []
    for name, keys in groups.items():
        combined = {k: _env(k) or (repo_env.get(k) or "") for k in keys}
        if all(str(v).strip() for v in combined.values()):
            present.append(name)
    if present:
        checks.append(("exchange_credentials", "OPEN", f"groups present: {', '.join(present)}"))
    else:
        checks.append(("exchange_credentials", "OWNER", "no key group; only the owner can arm real order execution"))

    # 5. Trading locks effective on the NEXT trading child.
    if present:
        expected_live = {
            "AUREON_LIVE_TRADING": "1",
            "AUREON_DISABLE_REAL_ORDERS": "0",
            "AUREON_DISABLE_EXCHANGE_MUTATIONS": "0",
            "AUREON_DRY_RUN": "0",
        }
        for k, want_on in expected_live.items():
            checks.append((f"next_boot:{k}", "OPEN" if _env(k) == want_on or not _env(k) else "ENGAGED", f"effective={_env(k) or 'unset'}"))
        checks.append(
            (
                "next_boot:trading_profile",
                "OPEN",
                "armed live (keys present) — launcher will apply _live_lock()",
            )
        )
    else:
        for k in ("AUREON_LIVE_TRADING", "AUREON_DISABLE_REAL_ORDERS", "AUREON_DISABLE_EXCHANGE_MUTATIONS", "AUREON_DRY_RUN"):
            checks.append((f"next_boot:{k}", "OPEN*", "paper lock applies only because no keys (informational)"))
        checks.append(("next_boot:trading_profile", "OPEN*", "paper/public-data until owner keys exist"))

    # 6. Local HTTP / operator profiles should not be silently hard-caging.
    try:
        from aureon.operator import local_http_profile as prof

        hard = getattr(prof, "HARD_LOCKS", None) or getattr(prof, "HARD_LOCKS", None)
        if hard is None:
            base = getattr(prof, "build_local_http_env", None)
            checks.append(("operator_local_http_profile", "OPEN*", "profile module loads; only applies in explicit local-HTTP sessions"))
    except Exception as exc:  # noqa: BLE001
        checks.append(("operator_local_http_profile", "OPEN*", f"unused: {exc.__class__.__name__}"))

    # 7. Feature switchboard: encrypted flags unreadable = not a cage.
    ff = Path.home() / ".aureon" / "feature_flags.json.enc"
    checks.append(("feature_flags", "OPEN", "encrypted store present" if ff.is_file() else "no encrypted store"))

    # 8. Offline data gates (scanner/portfolio offline modes).
    for flag in ("AUREON_OFFLINE", "AUREON_OFFLINE_INTENT", "AUREON_DRY_RUN"):
        checks.append((flag, "ENGAGED" if _truthy(flag) else "OPEN", _env(flag) or "unset"))

    return checks


def main() -> int:
    checks = rows(REPO)
    width = max(len(name) for name, _, _ in checks)
    print("AUREON CAGE AUDIT — live state on this machine")
    print("=" * (width + 30))
    engaged = 0
    for name, status, detail in checks:
        mark = "!" if status == "ENGAGED" else " "
        print(f"{mark} {name:.<{width}} {status:<7} {detail}")
        if status == "ENGAGED":
            engaged += 1
    print("=" * (width + 30))
    print(f"cages materially engaged: {engaged}")
    return 1 if engaged else 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Read-only Capital venue flight probe (Agent: CAPITAL VENUE TRUTH).

Fetches account balance/available and open positions via the same
CapitalClient path the portfolio writer uses. Read-only: touches NO
order/mutation endpoint. Never prints secrets.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

_AUREON_UPSTREAM = Path(__file__).resolve().parent.parent / "aureon-os-upstream"
if str(_AUREON_UPSTREAM) not in sys.path:
    sys.path.insert(0, str(_AUREON_UPSTREAM))


def main() -> int:
    from aureon.exchanges.capital_client import CapitalClient

    client = CapitalClient()
    out = {"steps": {}}

    try:
        accs = client.get_accounts(force_refresh=True) if "force_refresh" in getattr(client.get_accounts, "__kwdefaults__", {}) or True else None
    except TypeError:
        accs = client.get_accounts()
    except Exception as e:  # noqa: BLE001
        accs = None
        out["steps"]["accounts"] = {"ok": False, "error": f"{type(e).__name__}: {e}"}

    if accs is not None:
        rows = []
        for a in accs:
            rows.append({
                "accountId": str(a.get("accountId", ""))[:4] + "…",
                "balance": a.get("balance"),
                "available": a.get("available"),
                "currency": a.get("currency"),
            })
        out["steps"]["accounts"] = {
            "ok": True,
            "n_accounts": len(rows),
            "accounts": rows,
            "truth_status": getattr(accs, "truth_status", None),
        }

    try:
        bal = client.get_account_balance()
        out["steps"]["account_balance"] = {
            "ok": True,
            "balance": getattr(bal, "balance", None),
            "available": getattr(bal, "available", None),
            "currency": getattr(bal, "currency", None),
            "truth_status": getattr(bal, "truth_status", None),
        }
    except Exception as e:  # noqa: BLE001
        out["steps"]["account_balance"] = {"ok": False, "error": f"{type(e).__name__}: {e}"}

    try:
        poss = client.get_positions()
        n = len(list(poss)) if poss is not None else 0
        out["steps"]["positions"] = {
            "ok": True,
            "open_positions": n,
            "truth_status": getattr(poss, "truth_status", None),
            "reason": getattr(poss, "reason", None),
        }
    except Exception as e:  # noqa: BLE001
        out["steps"]["positions"] = {"ok": False, "error": f"{type(e).__name__}: {e}"}

    out["env_present"] = {k: bool(os.getenv(k)) for k in (
        "CAPITAL_API_KEY", "CAPITAL_API_PASSWORD", "CAPITAL_API_SECRET",
        "CAPITAL_IDENTIFIER", "CAPITAL_PASSWORD", "CAPITAL_USER",
        "CAPITAL_DEMO", "CAPITAL_DEMO_MODE",
    )}
    print(json.dumps(out, indent=1, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())

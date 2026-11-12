"""Keep ORCA's hands off Capital.com positions it did not open.

The ORCA bots (``orca_unified_kill_chain`` and ``orca_live_monitor``) never
open Capital.com positions themselves, yet they used to read every open
position and treat it as theirs. On 9 Nov 2026 that turned Gary's own
manual trades into exit candidates and fake booked exits.

This guard fails closed. A Capital position is handed to ORCA only when its
dealId (or dealReference) is listed in ``AUREON_ORCA_CAPITAL_ADOPT_DEALS``,
a comma-separated list the operator sets on purpose. With the variable unset
or empty, ORCA adopts no Capital position at all. Nothing here closes,
changes or contacts anything; it only filters a list.
"""

from __future__ import annotations

import os
from typing import Any, Dict, Iterable, List, Set, Tuple

ADOPT_ENV = "AUREON_ORCA_CAPITAL_ADOPT_DEALS"


def adopted_deal_ids(env: Dict[str, str] | None = None) -> Set[str]:
    raw = (env if env is not None else os.environ).get(ADOPT_ENV, "") or ""
    return {part.strip() for part in raw.split(",") if part.strip()}


def _deal_keys(position: Dict[str, Any]) -> Set[str]:
    meta = position.get("position", position) if isinstance(position, dict) else {}
    if not isinstance(meta, dict):
        return set()
    keys = set()
    for field in ("dealId", "dealReference", "deal_id", "deal_reference"):
        value = meta.get(field)
        if value:
            keys.add(str(value))
    return keys


def split_owned_positions(
    positions: Iterable[Dict[str, Any]], env: Dict[str, str] | None = None
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Return (owned, skipped). Only explicitly adopted deals are owned."""
    allow = adopted_deal_ids(env)
    owned: List[Dict[str, Any]] = []
    skipped: List[Dict[str, Any]] = []
    for position in positions or []:
        keys = _deal_keys(position)
        if keys and keys & allow:
            owned.append(position)
        else:
            skipped.append(position)
    return owned, skipped

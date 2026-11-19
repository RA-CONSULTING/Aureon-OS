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


def _clean_id(value: Any) -> str:
    text = str(value or "").strip()
    if text.lower() in {"", "unknown", "none"}:
        return ""
    return text


def opened_deal_id(payload: Any) -> str | None:
    """The one OPENED dealId in a GET /confirms body or a recorded receipt.

    REJECTED, missing, blank, unknown, and any count other than one OPENED
    deal return None. A top-level dealId counts only when dealStatus is
    ACCEPTED and no OPENED row was listed.
    """
    if not isinstance(payload, dict) or payload.get("error"):
        return None
    status = str(
        payload.get("dealStatus") or payload.get("status") or ""
    ).strip().upper()
    if status == "REJECTED":
        return None
    raw = payload.get("provider_response")
    if isinstance(raw, dict):
        return opened_deal_id(raw)
    rows = payload.get("affectedDeals")
    if not isinstance(rows, list):
        alt = payload.get("affected_deals")
        rows = alt if isinstance(alt, list) else []
    opened: List[str] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        if str(row.get("status") or "").strip().upper() != "OPENED":
            continue
        deal = _clean_id(row.get("dealId"))
        if deal:
            opened.append(deal)
    if len(opened) == 1:
        return opened[0]
    if opened:
        return None
    if status == "ACCEPTED":
        return _clean_id(payload.get("dealId") or payload.get("provider_deal_id")) or None
    return None


def _position_body(target: Dict[str, Any]) -> Dict[str, Any]:
    raw = target.get("raw") if isinstance(target.get("raw"), dict) else {}
    pos = raw.get("position") if isinstance(raw.get("position"), dict) else {}
    return pos


def capital_close_deal_id(
    target: Dict[str, Any], allow: Set[str], confirm: Any = None
) -> str | None:
    """DealId to close, or None when the close must be refused.

    An allowlisted dealId that is not only the dealReference closes as
    itself. An allowlisted dealReference is resolved through ``confirm``
    (GET /confirms/{ref}, or a recorded receipt). Blank, unknown, missing,
    and REJECTED confirms stay refused. The close id is never the reference.
    """
    pos = _position_body(target)
    position_deal = _clean_id(pos.get("dealId") or pos.get("deal_id"))
    ref = _clean_id(
        pos.get("dealReference")
        or pos.get("deal_reference")
        or target.get("deal_reference")
        or target.get("dealReference")
    )
    ident = _clean_id(target.get("id")) or position_deal
    if ident and ident in allow and ident != ref:
        return ident
    if position_deal and position_deal in allow and position_deal != ref:
        return position_deal
    if not ref or ref not in allow:
        return None
    opened = opened_deal_id(confirm)
    if not opened:
        return None
    if position_deal and position_deal != opened:
        return None
    return opened


def resolve_capital_close_id(target: Dict[str, Any], allow: Set[str], read_confirm) -> str | None:
    """Close id for one scanned Capital target.

    ``read_confirm(ref)`` is GET /confirms/{ref} (CapitalClient.confirm_order).
    A recorded ``confirmation`` or ``receipt`` on the target is used instead.
    """
    recorded = target.get("confirmation")
    if not isinstance(recorded, dict):
        recorded = target.get("receipt")
    if isinstance(recorded, dict):
        return capital_close_deal_id(target, allow, recorded)
    direct = capital_close_deal_id(target, allow, None)
    if direct:
        return direct
    pos = _position_body(target)
    ref = _clean_id(
        pos.get("dealReference")
        or pos.get("deal_reference")
        or target.get("deal_reference")
        or target.get("dealReference")
    )
    if not ref or ref not in allow:
        return None
    payload = None
    if callable(read_confirm):
        try:
            payload = read_confirm(ref)
        except Exception:
            payload = None
    return capital_close_deal_id(target, allow, payload)

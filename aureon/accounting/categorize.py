"""
The Categorization Court — where suspense money receives its honest name.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

The file drop parks every unexplained pound in suspense (9999). This module
is the decision seam that moves it out — by name, never by guess:

* **Rules first**: an explicit per-client registry of keyword → nominal code
  mappings (registry-as-data, the same doctrine as everywhere else).
* **Agent second**: an optional ``decide`` callable — the seat where
  Dr. Auris Throne / the Ollama adapter plugs in. Whatever it returns must
  be a code on the client's chart; anything else is refused by the ledger
  itself, and the refusal is a recorded coordination step.
* **Suspense last**: what neither rules nor agent can name STAYS in suspense,
  counted and reported — an unexplained pound is never forced into a P&L line.

Every move is a balanced journal entry referencing the original entry id, so
the audit trail reads: bank row → suspense → named account, with provenance
at each hop and the HNC coordination record measuring the whole march.

Gary Leckey · Aureon Institute
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, List

from aureon.accounting.client_ledger import ClientLedger, Posting

__all__ = ["CategoryRule", "recategorize_suspense"]


@dataclass(frozen=True)
class CategoryRule:
    """One explicit mapping: a keyword seen in the description → a nominal code."""

    keyword: str
    code: str

    def matches(self, description: str) -> bool:
        return self.keyword.lower() in description.lower()


def _already_categorized_refs(ledger: ClientLedger) -> set:
    return {e["reference"] for e in ledger.entries
            if e["description"].startswith("categorize:")}


def recategorize_suspense(
        ledger: ClientLedger,
        rules: List[CategoryRule],
        decide: Callable[[str, int], str | None] | None = None,
) -> Dict[str, Any]:
    """Walk every entry still holding money in suspense and name it.

    ``decide(description, signed_pennies)`` is the agent seat — consulted only
    when no rule matches; may return a nominal code or ``None`` (undecided).
    Returns the measured outcome: moved, still-suspended, refused.
    """
    done = _already_categorized_refs(ledger)
    moved = still = refused = 0
    for entry in list(ledger.entries):
        if entry["id"] in done or entry["description"].startswith("categorize:"):
            continue
        sus = [ln for ln in entry["lines"] if ln["code"] == "9999"]
        if not sus:
            continue
        line = sus[0]
        credit_sus = line["credit_pennies"] > 0  # money in (income-shaped)
        amount = line["credit_pennies"] if credit_sus else line["debit_pennies"]
        desc = entry["description"]

        code = next((r.code for r in rules if r.matches(desc)), None)
        if code is None and decide is not None:
            try:
                code = decide(desc, amount if credit_sus else -amount)
            except Exception:  # noqa: BLE001 — an erring agent is an undecided agent
                code = None
        if code is None:
            still += 1
            continue

        if credit_sus:  # clear the suspense credit, credit the named account
            postings = [Posting("9999", debit_pennies=amount, memo=f"clears {entry['id']}"),
                        Posting(code, credit_pennies=amount, memo=desc)]
        else:
            postings = [Posting(code, debit_pennies=amount, memo=desc),
                        Posting("9999", credit_pennies=amount, memo=f"clears {entry['id']}")]
        posted = ledger.post(f"categorize: {desc}", postings,
                             reference=entry["id"], when=entry["ts"])
        if posted is None:  # unknown code → the ledger already recorded the refusal
            refused += 1
        else:
            moved += 1

    return {
        "client_id": ledger.client_id,
        "moved": moved,
        "still_in_suspense": still,
        "refused": refused,
        "suspense_pennies_remaining": ledger.suspense_pennies(),
        "note": ("what no rule or agent could name STAYS in suspense — an "
                 "unexplained pound is never forced into a P&L line"),
    }

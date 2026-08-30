"""Portals — what an authenticated operator session can be *read* through.

A funding portal is the funder's own record of what has actually been applied
for. Until now the organism had no way to see one: the only reads ever performed
were done by a human (or an assistant) driving a browser in a chat window, which
is not repeatable, not testable, not gated, and leaves no artifact in the repo.
This package is that capability, owned by the repository.

Two rules govern everything under this package and are not negotiable:

**Credentials are never handled here.** There is no login flow, no username or
password field, no credential store, and no code path that could acquire a
session. The portal session belongs to the operator's own browser. A reader in
this package attaches to an existing authenticated session or reports that it
cannot — see :class:`~aureon.portals.schemas.PortalSnapshot`, whose
``available`` / ``blocker`` invariant makes "quietly unavailable" impossible to
represent.

**Nothing here writes the ledger.** ``data/research/grants/pipeline.json`` is the
grant operator's file and is written live by him; this package reads it and never
touches it. :mod:`aureon.portals.reconcile` produces a dated recommendation
document and stops there.

**The one thing that can write to the funder cannot submit.**
:mod:`aureon.portals.actions` is the write path, and every write is two calls with
Gary between them: ``propose_field_update`` runs the gate chain and asks him;
``apply_approved_action`` re-reads the approval ledger at the instant of writing
and refuses unless it says APPROVED for that exact action, then hands the value to
a ``writer`` **the caller injects** — there is no default one, so with nothing
injected the module cannot reach a portal at all. There is no submit function in
it. Not a disabled one — absent; and
:func:`aureon.gates.switchboard.is_human_held` holds ``submit`` / ``file`` /
``lodge`` one layer down, so a submit intent cannot pass the chain either.
Completing a draft field is legitimate automation. Lodging an official filing is
Gary's, by his own standing rule.
"""

from __future__ import annotations

from aureon.portals.actions import (
    ActionState,
    FieldWriter,
    PortalAction,
    action_log_path,
    apply_approved_action,
    portals_dir,
    propose_field_update,
)
from aureon.portals.ifs import (
    DASHBOARD_URL,
    PortalBlocked,
    cdp_fetcher,
    parse_dashboard,
    read_dashboard,
)
from aureon.portals.schemas import (
    PORTAL_STATES,
    STATE_IN_PROGRESS,
    STATE_INELIGIBLE,
    STATE_NOT_STARTED,
    STATE_SUBMITTED,
    STATE_UNKNOWN,
    PortalApplication,
    PortalSnapshot,
    PortalState,
    coerce_snapshot,
    normalise_state,
)

__all__ = [
    "DASHBOARD_URL",
    "PORTAL_STATES",
    "STATE_IN_PROGRESS",
    "STATE_INELIGIBLE",
    "STATE_NOT_STARTED",
    "STATE_SUBMITTED",
    "STATE_UNKNOWN",
    "ActionState",
    "FieldWriter",
    "PortalAction",
    "PortalApplication",
    "PortalBlocked",
    "PortalSnapshot",
    "PortalState",
    "action_log_path",
    "apply_approved_action",
    "cdp_fetcher",
    "coerce_snapshot",
    "normalise_state",
    "parse_dashboard",
    "portals_dir",
    "propose_field_update",
    "read_dashboard",
]

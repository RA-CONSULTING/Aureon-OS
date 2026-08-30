"""The one address in this package, and the only way to get it.

Property 1, structurally: **the sender must be incapable of emailing anyone but
the owner.** Not "must check the recipient" — incapable. The mechanism is that
no callable in :mod:`aureon.approval` accepts a destination argument, and the
only address in the package comes out of :func:`owner_address`, which takes no
arguments at all. There is nothing to pass, so there is nothing to get wrong: a
sender that cannot address a funder cannot accidentally submit to one.

``is_owner`` does take an address, and the distinction matters: it reads an
address that arrived *inbound* on a reply, in order to verify it. It never hands
one to anything. Its parameter is named ``candidate`` rather than ``address`` or
``email`` on purpose — a parameter that reads like a destination invites a future
caller to treat it as one, and the test in ``tests/approval/test_core.py`` walks
every public signature in the package looking for exactly that.

**A collision worth knowing about.** ``AUREON_APPROVAL_EMAIL`` is already used
elsewhere in this repository as a boolean feature flag
(``aureon/operator/approval_email.py`` reads it through ``_truthy``, and
``operator/feature_switchboard.py`` lists it as a toggle). Gary's spec names it
as the address variable, so both readings have to coexist: a value that is not a
single well-formed address — ``"1"``, ``"true"``, ``"on"`` — is not an address,
is ignored with a debug line, and resolution falls through to
``AUREON_OWNER_EMAIL``. That is why this module validates instead of trusting.

A value holding more than one address is refused outright rather than split. A
list of "owners" is the one shape that could put a stranger on an approval
request, so the plural case resolves to nobody and the request goes nowhere.
"""

from __future__ import annotations

import logging
import os
import re
from email.utils import getaddresses

LOG = logging.getLogger("aureon.approval.config")

# Gary's spec: the approval address, falling back to the owner address.
APPROVAL_EMAIL_VAR = "AUREON_APPROVAL_EMAIL"
OWNER_EMAIL_VAR = "AUREON_OWNER_EMAIL"
ADDRESS_VARS: tuple[str, ...] = (APPROVAL_EMAIL_VAR, OWNER_EMAIL_VAR)

# Deliberately strict: one local part, one dotted domain, no commas, no angle
# brackets, no whitespace. This is the gate that turns a feature-flag "1" into
# "not an address" and a "gary@x.com, funder@y.com" into nobody.
_ADDRESS_RE = re.compile(r"^[^@\s,;<>\"]+@[^@\s,;<>\"]+\.[A-Za-z]{2,}$")


def _single(raw: str) -> str | None:
    """The one address in ``raw``, or ``None`` if it is not exactly one.

    Parsed with :func:`email.utils.getaddresses` so a display name cannot smuggle
    a second address past the comma check.
    """
    parsed = [addr for _name, addr in getaddresses([raw]) if addr]
    if len(parsed) != 1:
        return None
    addr = parsed[0].strip()
    return addr if _ADDRESS_RE.match(addr) else None


def owner_address() -> str | None:
    """The owner's address, resolved from configuration. Takes no arguments.

    ``AUREON_APPROVAL_EMAIL`` wins when it holds one well-formed address;
    otherwise ``AUREON_OWNER_EMAIL``. Returns ``None`` when neither does, which
    means no approval can be requested and — because :func:`is_owner` then
    matches nobody — no reply can approve anything either. Fails closed.
    """
    for var in ADDRESS_VARS:
        raw = str(os.environ.get(var, "") or "").strip()
        if not raw:
            continue
        addr = _single(raw)
        if addr:
            return addr
        # Do not log the value: it may be a real address, and this package never
        # prints one it was not asked to use.
        LOG.debug("%s does not hold exactly one well-formed address — ignored", var)
    LOG.debug("no approval address configured (%s)", ", ".join(ADDRESS_VARS))
    return None


def owner_configured() -> bool:
    """True when there is somebody to ask."""
    return owner_address() is not None


def is_owner(candidate: str | None) -> bool:
    """True when ``candidate`` is the configured owner, compared case-insensitively.

    ``candidate`` is an address read off an inbound reply — never a destination.
    Expects a bare address; use :func:`aureon.approval.reply.sender_of` to get
    one out of a ``From`` header, which is where the display-name trick lives.

    Returns ``False`` when no owner is configured: with nobody configured, nobody
    is the owner, and every reply is ignored.
    """
    owner = owner_address()
    if not owner or not candidate:
        return False
    return str(candidate).strip().lower() == owner.strip().lower()


__all__ = ["ADDRESS_VARS", "APPROVAL_EMAIL_VAR", "OWNER_EMAIL_VAR",
           "is_owner", "owner_address", "owner_configured"]

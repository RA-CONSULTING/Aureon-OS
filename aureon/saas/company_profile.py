"""
Company profile — the organization behind Aureon OS, as UI-consumable metadata.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

The company's legal and recognition facts live in ``COMPANY.md`` (and the README) as
prose, but nothing surfaced them to the console — so a professional operator cloning
the system saw the platform without the organization behind it. The one existing
``/api/company`` route is a misnomer: it returns the *agent workforce roster*, not the
registered company.

This is the missing surface. It is **registry-as-data**: the verifiable company facts
(registered name, company number, trading name, the Innovate NI recognition, community
support, contact) are transcribed here from ``COMPANY.md`` as structured, honest data —
nothing computed, nothing fabricated. Every fact is checkable on the public record
(Companies House NI, company number NI696693). ``truth_status`` is ``real_derived``: the
values are derived from the repository's own committed company document.

Gary Leckey · Aureon Institute
"""

from __future__ import annotations

from typing import Any, Dict

# ── the company of record (transcribed from COMPANY.md — verifiable public facts) ─────
_IDENTITY: Dict[str, str] = {
    "registered_name": "R&A Consulting and Brokerage Services Ltd",
    "company_number": "NI696693",
    "registrar": "Companies House, Northern Ireland",
    "status": "Active",
    "registered_office": "Belfast, Northern Ireland, United Kingdom",
    "director": "Gary Anthony Leckey",
    "trading_name": "Aureon Zorza Technologies",
    "research_identity": "Aureon Institute",
    "website": "https://aureonzorzatechnologies.com",
}

_IDENTITY_NOTE: str = (
    "Aureon Zorza Technologies is the technology brand and trading name of R&A Consulting "
    "and Brokerage Services Ltd — not a separately registered entity. Aureon Institute is "
    "the research identity under which the Harmonic Nexus Core (HNC) work is published. "
    "Company details are verifiable on the Companies House public register (company "
    "number NI696693)."
)

_RECOGNITION: Dict[str, str] = {
    "award": "Silver Level Innovator — Innovate NI Innovation Framework",
    "issuer": "Department for the Economy (with Tourism NI and Innovation NI)",
    "signatory": "Dr Caoimhe Archibald MLA, Minister for the Economy",
    "date": "2025-07-21",
    "detail": "An independent, government-backed Certificate of Recognition for reaching "
              "Silver level on the Innovate NI Innovation Framework — the credential behind "
              "Aureon's positioning as innovation specialists.",
}

_COMMUNITY: Dict[str, Any] = {
    "summary": "Supporter of Street Soccer NI and the Homeless World Cup (Norway 2025).",
    "partners": ["Street Soccer NI", "Homeless World Cup (Norway 2025)", "Choice",
                 "Simon Community", "Northern Ireland Housing Executive", "Belfast Charitable Society"],
}

_PRODUCT: Dict[str, str] = {
    "name": "Aureon OS",
    "powered_by": "Harmonic Nexus Core (HNC)",
    "summary": "R&A Consulting's flagship platform — a grounded AI operating layer for "
               "evidence-heavy, high-control workflows spanning trading research, an "
               "autonomous operator with a conscience in the loop, a planetary/HNC research "
               "fabric, and a self-building coding organism.",
}

_CONTACT: Dict[str, str] = {
    "website": "https://aureonzorzatechnologies.com",
    "repository": "https://github.com/RA-CONSULTING/Aureon-OS",
    "license": "MIT",
    "copyright": "© 2025 R&A Consulting and Brokerage Services Ltd",
}

_DISCLAIMER: str = (
    "Nothing here is an offer of securities or a promise of investment returns. Company "
    "and recognition details are stated as verifiable facts."
)


def build_company_profile() -> Dict[str, Any]:
    """The organization behind Aureon OS as honest, UI-consumable metadata.

    Pure data transcribed from ``COMPANY.md`` — no computation, no runtime probing, no
    fabrication. ``truth_status`` is ``real_derived`` (derived from the committed company
    document); the gateway stamps the provenance block on top.
    """
    return {
        "identity": dict(_IDENTITY),
        "identity_note": _IDENTITY_NOTE,
        "recognition": dict(_RECOGNITION),
        "community": {"summary": _COMMUNITY["summary"], "partners": list(_COMMUNITY["partners"])},
        "product": dict(_PRODUCT),
        "contact": dict(_CONTACT),
        "disclaimer": _DISCLAIMER,
        "source": "COMPANY.md",
        "truth_status": "real_derived",
    }


__all__ = ["build_company_profile"]

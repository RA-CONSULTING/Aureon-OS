# ORCID Public Record Reconciliation — 28 July 2026

## Scope and decision

This is a read-only reconciliation of the public ORCID record with the
canonical website research routes. It does not amend the public website,
create a candidate, authorise a Home.pl package, or make a claim about peer
review, validation, product readiness, adoption, funding, or endorsement.

**Decision:** no bulk website catalogue expansion is warranted. The current
site correctly uses a small, curated orientation set and links readers to the
persistent ORCID record for the complete public body of work.

## Sources checked

- Official ORCID works endpoint for researcher `0009-0004-2792-4649`:
  `https://pub.orcid.org/v3.0/0009-0004-2792-4649/works`
- Public ORCID profile:
  `https://orcid.org/0009-0004-2792-4649`
- Public Zenodo record pages linked by the site.
- Canonical site data: `website/data/research-catalogue.json` and the
  renderer in `website/research/index.html`.

At review time, the official endpoint returned 74 public work groups: 61
created on 24 July 2026 and 13 from 2025. This is an internal reconciliation
fact, **not** a website metric or a proposed public traction claim.

## Exact source mapping

| ORCID work / DOI | Canonical site representation | Reconciliation |
| --- | --- | --- |
| `221734228` / `10.5281/zenodo.21530783` — *HNC BioMolecule Adjacent Frequency Packet: White Paper (v1)* | `research-catalogue.json` orientation record `zenodo-21530783` | Title, date (24 July 2026) and type (Preprint) match. |
| `221734210` / `10.5281/zenodo.21530780` — *The Position of Echo-Feedback Cognitive φ-Substrate (PEFCφS): A Four-Layer Architecture for the Harmonic Nexus Core Framework* | `research-catalogue.json` orientation record `zenodo-21530780` | Title, date (24 July 2026) and type (Preprint) match. |
| `221732591` / `10.5281/zenodo.21530644` — *LSSP Pre-Registration: Detecting φ-Spaced Phase-Coherence Peaks in Open Neural Recordings — The Leckey Substrate Scaling Protocol (v1.0)* | `research-catalogue.json` orientation record `zenodo-21530644` | Title, date (23 April 2026) and type (Preprint) match. |

The other 58 work groups added to ORCID on 24 July 2026, together with the
13 older public groups, are reachable through the persistent ORCID link. They
should not be expanded into a long list of marketing cards: that would blur
research types, duplicate source navigation and weaken the curated investor
reading path.

The three other current orientation records are correctly Zenodo-first rather
than ORCID-backed at the time of review:

- `10.5281/zenodo.21540072` — *Experimental Protocol v2: Illumination Chip
  Concept — Bench Test Procedure and Null Criteria*.
- `10.5281/zenodo.21540051` — *EPAS Unified Architecture v2: A Theoretical
  Four-Wave Mixing Architecture with Computational Checks*.
- `10.5281/zenodo.21539997` — *The HNC Matrix Framework v2: Formal
  Consistency Review and Theoretical Interpretation*.

Their title, date and record type match the linked Zenodo metadata. Their
absence from the current ORCID group list is not a website defect.

## Public-language boundary

Safe public wording is:

> Public source-linked preprint or technical note; the record establishes
> attribution and availability. Independent review and validation remain
> separate.

Do not convert a work count, publication date, DOI, Zenodo download, ORCID
profile or Substack note into evidence of scientific validation, operational
performance, customer use, investment, partnership, grant success or market
adoption.

## Future refresh rule

If a future site revision spotlights a newly updated research work, it must
use the exact source title, record type, publication date, DOI and source URL;
provide a short evidence boundary; label its provenance precisely as either
`ORCID-indexed` or `Zenodo source record`; and pass the normal candidate,
visual, performance and owner-release gates. A direct ORCID link remains
sufficient until a specific source-bound reading card is approved.

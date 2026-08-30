/**
 * Company facts — the single, backend-independent source for the public surfaces.
 *
 * The operator Company page reads these from GET /api/org (see
 * aureon/saas/company_profile.py). The public front door (landing, legal, footer,
 * evidence) must render with no backend, so the same verifiable facts are mirrored
 * here as constants. Keep the two in sync; every value is a checkable public fact
 * (Companies House NI, company number NI696693) — nothing is fabricated.
 *
 * To correct a fact (e.g. domain, contact), edit it here and in
 * aureon/saas/company_profile.py — layout never hardcodes these.
 */

export const COMPANY = {
  registeredName: "R&A Consulting and Brokerage Services Ltd",
  tradingName: "Aureon Zorza Technologies",
  researchIdentity: "Aureon Institute",
  companyNumber: "NI696693",
  registrar: "Companies House, Northern Ireland",
  status: "Active",
  registeredOffice: "Belfast, Northern Ireland, United Kingdom",
  director: "Gary Anthony Leckey",
  website: "https://aureonzorzatechnologies.com",
  websiteLabel: "aureonzorzatechnologies.com",
  email: "gary@aureonzorzatechnologies.com",
  repository: "https://github.com/RA-CONSULTING/Aureon-OS",
  license: "MIT",
  copyright: "© 2025 R&A Consulting and Brokerage Services Ltd",
} as const;

export const PRODUCT = {
  name: "Aureon OS",
  poweredBy: "Harmonic Nexus Core (HNC)",
  tagline: "A grounded AI operating layer for evidence-heavy, high-control work.",
  summary:
    "One auditable system: trading research, an autonomous operator with a conscience in " +
    "the loop, a planetary/HNC research fabric, and a self-building coding organism — with " +
    "honest data provenance on every surface.",
} as const;

export const RECOGNITION = {
  award: "Silver Level Innovator — Innovate NI Innovation Framework",
  issuer: "Department for the Economy",
  signatory: "Dr Caoimhe Archibald MLA, Minister for the Economy",
  date: "2025-07-21",
  detail:
    "An independent, government-backed Certificate of Recognition for reaching Silver level on " +
    "the Innovate NI Innovation Framework.",
} as const;

const COMMUNITY = {
  summary: "Supporter of Street Soccer NI and the Homeless World Cup (Norway 2025).",
  partners: [
    "Street Soccer NI",
    "Homeless World Cup (Norway 2025)",
    "Choice",
    "Simon Community",
    "Northern Ireland Housing Executive",
    "Belfast Charitable Society",
  ],
} as const;

const IDENTITY_NOTE =
  "Aureon Zorza Technologies is the technology brand and trading name of R&A Consulting and " +
  "Brokerage Services Ltd — not a separately registered entity. Aureon Institute is the research " +
  "identity under which the Harmonic Nexus Core (HNC) work is published. Company details are " +
  "verifiable on the Companies House public register (company number NI696693).";

const DISCLAIMER =
  "Nothing here is an offer of securities or a promise of investment returns. Company and " +
  "recognition details are stated as verifiable facts.";

/** Fixed effective date for the legal policies — a real stamp, not new Date(). */
export const LEGAL_EFFECTIVE_DATE = "22 July 2026";

/**
 * The company profile in the exact shape GET /api/org returns, built from the constants
 * above so the Company surface renders honestly with no backend. truth_status is
 * real_derived — derived from the committed company facts, nothing fabricated.
 */
export function buildStaticCompanyProfile() {
  return {
    identity: {
      registered_name: COMPANY.registeredName,
      company_number: COMPANY.companyNumber,
      registrar: COMPANY.registrar,
      status: COMPANY.status,
      registered_office: COMPANY.registeredOffice,
      director: COMPANY.director,
      trading_name: COMPANY.tradingName,
      research_identity: COMPANY.researchIdentity,
      website: COMPANY.website,
    } as Record<string, string>,
    identity_note: IDENTITY_NOTE,
    recognition: {
      award: RECOGNITION.award,
      issuer: RECOGNITION.issuer,
      signatory: RECOGNITION.signatory,
      date: RECOGNITION.date,
      detail: RECOGNITION.detail,
    } as Record<string, string>,
    community: { summary: COMMUNITY.summary, partners: [...COMMUNITY.partners] },
    product: {
      name: PRODUCT.name,
      powered_by: PRODUCT.poweredBy,
      summary: PRODUCT.summary,
    } as Record<string, string>,
    contact: {
      website: COMPANY.website,
      repository: COMPANY.repository,
      license: COMPANY.license,
      copyright: COMPANY.copyright,
    } as Record<string, string>,
    disclaimer: DISCLAIMER,
    source: "companyFacts.ts",
    truth_status: "real_derived" as const,
  };
}

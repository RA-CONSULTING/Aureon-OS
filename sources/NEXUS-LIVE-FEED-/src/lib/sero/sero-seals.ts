// SERO — Source Seals binding
// Maps ethical “seals” to concrete checks and attaches them to the audit trail.

import type { ActuationRequest, GateVerdict, Evaluation } from "./sero-core";

export type SealStatus = {
  id: string;
  name: string;
  lit: boolean;           // true = seal illuminated / passed
  reason: string;         // short human-readable reason
  details?: Record<string, any>;
};

export const SOURCE_SEALS = [
  { id: "seal_1", name: "Golden Spiral" },       // Coherence
  { id: "seal_2", name: "Protection Hexa-Seal" },// Non-Harm
  { id: "seal_3", name: "Cosmic Script Seal" },  // Transparency
  { id: "seal_4", name: "Guardian Flame" },      // Inclusion / No one left out
  { id: "seal_5", name: "Crowned Infinity" },    // Dual Consent
  { id: "seal_6", name: "Phoenix-Ankh Medallion"}// Prime Intent (Love)
] as const;

/** Helper: find a verdict by code (exact or prefix) */
const hasPass = (verdicts: GateVerdict[], code: string | RegExp) =>
  verdicts.some(v => (code instanceof RegExp ? code.test(v.code) : v.code === code) && v.pass);

/** Evaluate seals from request + gate results. */
export function evaluateSeals(req: ActuationRequest, evaluation: Evaluation): SealStatus[] {
  const v = evaluation.verdicts;
  const ethos = (req as any).ethos ?? {};
  const heart = ethos.heart ?? {};
  const pli = Math.max(0, Math.min(1, (heart.compassion_index ?? 0) - (heart.malice_index ?? 0)));

  const seals: SealStatus[] = [
    {
      id: "seal_1",
      name: "Golden Spiral",
      lit: hasPass(v, /SC_OK|MW_OK|CD_OK/) && evaluation.score >= 0.80,
      reason: "System coherent; parameters sane; composite ≥ 0.80",
      details: { composite: evaluation.score }
    },
    {
      id: "seal_2",
      name: "Protection Hexa-Seal",
      lit: hasPass(v, "LAW_NO_WEAPONIZATION"),
      reason: "No weaponization / harm semantics detected."
    },
    {
      id: "seal_3",
      name: "Cosmic Script Seal",
      lit: hasPass(v, "LAW_TRANSPARENCY"),
      reason: "Provenance publishable / transparency satisfied."
    },
    {
      id: "seal_4",
      name: "Guardian Flame",
      // Inclusion signal: caller can set ethos.include_all = true for inclusive ops,
      // otherwise we require absence of exclusion flags.
      lit: (ethos.include_all === true) && !(ethos.exclude?.length > 0),
      reason: "Inclusive intent affirmed; no exclusions in effect.",
      details: { include_all: ethos.include_all === true, exclude: ethos.exclude ?? [] }
    },
    {
      id: "seal_5",
      name: "Crowned Infinity",
      lit: hasPass(v, "GOV_DUAL_CONSENT"),
      reason: "Dual consent verified (Prime Sentinel + System Steward)."
    },
    {
      id: "seal_6",
      name: "Phoenix-Ankh Medallion",
      // If you installed the Prime Intent Love gate, its code is PRIME_INTENT_LOVE
      lit: hasPass(v, "PRIME_INTENT_LOVE") || pli >= 0.50,
      reason: "Prime intent love-aligned (compassion >> malice).",
      details: { PLI: pli }
    }
  ];

  return seals;
}

/** Require all seals lit (configurable upstream). */
export function allSealsLit(seals: SealStatus[]): boolean {
  return seals.every(s => s.lit);
}

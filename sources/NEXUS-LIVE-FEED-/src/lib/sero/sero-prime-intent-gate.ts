// Sero - Prime Intent Gate — “Love is the pure intent”
// Blocks actuation unless compassion >> malice and the intent is love-aligned.

import { registerGate, type ActuationRequest, type GateVerdict } from "./sero-core";

// --- Types carried inside req.ethos ---
type HeartEvidence = {
  hrv_coherence?: number;        // 0..1
  compassion_index?: number;     // 0..1
  malice_index?: number;         // 0..1
  declaration?: "pure_of_heart" | "neutral" | "unclear";
};

// Helper for creating verdicts
const ok = (pass:boolean, code:string, message:string, details?:any): GateVerdict =>
  ({ pass, code, message, details });

// Simple semantic check for love-aligned phrasing
function isLoveSemantics(txt: string): boolean {
  const love = /\b(love|compassion|care|kindness|mercy|alleviate harm|healing)\b/i;
  const avoid = /\b(retaliat|punish|dominat|coerc|weapon|harm)\b/i;
  return love.test(txt) && !avoid.test(txt);
}

function gatePrimeIntentLove(req: ActuationRequest): GateVerdict {
  const text = [
    req.intent,
    JSON.stringify(req.params ?? {}),
    JSON.stringify((req as any).ethos ?? {})
  ].join(" ");

  const heart = (req as any).ethos?.heart as HeartEvidence | undefined;

  const comp   = heart?.compassion_index ?? 0.0;
  const mal    = heart?.malice_index ?? 0.0;
  const decl   = heart?.declaration ?? "neutral";
  const loveOK = isLoveSemantics(text) || decl === "pure_of_heart";

  // Prime Love Index: compassion minus malice, clipped to [0,1]
  const PLI = Math.max(0, Math.min(1, comp - mal));

  // Hard requirement: love semantics AND PLI ≥ 0.50
  const pass = loveOK && PLI >= 0.50;

  return pass
    ? ok(true, "PRIME_INTENT_LOVE", "Prime intent verified as love-aligned.", { PLI, comp, mal, decl, loveSemantics: loveOK })
    : ok(false, "PRIME_INTENT_LOVE",
        "Prime intent not sufficiently love-aligned (need love semantics and compassion >> malice).",
        { PLI, comp, mal, decl, loveSemantics: loveOK });
}

export function installPrimeIntentLoveGate() {
  registerGate(gatePrimeIntentLove);
}

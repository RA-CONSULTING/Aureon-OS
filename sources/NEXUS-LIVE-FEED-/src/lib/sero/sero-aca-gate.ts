// Alexander–Cleopatra–Aphrodite Gate (ACA Gate)
// Power holds (Triangle), Wisdom reveals (Square), Love invites (Vesica).
// Pass only if: protective containment, measured clarity+transparency, and consentful reversibility.

// Uses your existing Sero core types.
import { registerGate, type ActuationRequest, type GateVerdict } from "./sero-core";

export const ACAGateConfig = {
  // Per-axis minimums
  minPower: 0.70,      // containment / non-harm
  minWisdom: 0.70,     // clarity / measurement + transparency
  minLove: 0.80,       // consent + reversibility
  // Global product threshold (Golden Spiral condition)
  tau: 0.60,           // α_power * α_wisdom * α_love ≥ tau
};

// Expected soft schema inside req.ethos (don’t make it mandatory; gate is defensive)
type ACAEthos = {
  power?: { containment_index?: number; non_harm?: boolean };
  wisdom?: { clarity_index?: number; transparency?: boolean };
  love?: { consent?: boolean; reversibility?: number; pli?: number }; // pli = compassion−malice clamp[0,1]
};

const clip01 = (x: any) => Math.max(0, Math.min(1, Number(x ?? 0)));

function scorePower(e: ACAEthos["power"]) {
  const contain = clip01(e?.containment_index);
  const nonHarm = e?.non_harm === false ? 0 : 1; // any explicit harm → fail this axis
  return contain * nonHarm; // in [0,1]
}

function scoreWisdom(e: ACAEthos["wisdom"]) {
  const clarity = clip01(e?.clarity_index);
  const transp  = e?.transparency ? 1 : 0;       // transparency is binary guard
  return Math.min(clarity, transp);              // must be both clear AND transparent
}

function scoreLove(e: ACAEthos["love"]) {
  const consent = e?.consent ? 1 : 0;
  const rev     = clip01(e?.reversibility);      // undo-ability
  const pli     = clip01(e?.pli);                // compassion − malice (optional)
  // Love axis asks for consent, high reversibility, and (if present) love alignment
  return Math.min(consent, rev, pli || 1);
}

function gateACA(req: ActuationRequest): GateVerdict {
  const ethos = ((req as any).ethos ?? {}) as ACAEthos;

  const aP = scorePower(ethos.power);
  const aW = scoreWisdom(ethos.wisdom);
  const aL = scoreLove(ethos.love);

  const passAxes =
    aP >= ACAGateConfig.minPower &&
    aW >= ACAGateConfig.minWisdom &&
    aL >= ACAGateConfig.minLove;

  const product = aP * aW * aL;
  const pass = passAxes && product >= ACAGateConfig.tau;

  return {
    pass,
    code: "ACA_GEOMETRIC_PARABLE",
    message: pass
      ? "Triangle holds, Square reveals, Vesica invites — Golden Spiral path is open."
      : "Hold: one or more axes below threshold (power/wisdom/love) or product < τ.",
    details: {
      alpha_power: Number(aP.toFixed(3)),
      alpha_wisdom: Number(aW.toFixed(3)),
      alpha_love: Number(aL.toFixed(3)),
      product: Number(product.toFixed(3)),
      thresholds: ACAGateConfig
    }
  };
}

// Call this once at bootstrap (returns unregister for tests/hot-reload)
export function installACAGate() {
  return registerGate(gateACA);
}
export default installACAGate;

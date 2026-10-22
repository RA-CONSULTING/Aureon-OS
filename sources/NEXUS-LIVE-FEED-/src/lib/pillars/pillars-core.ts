export type PillarName = "ANCHOR" | "BRIDGE" | "GUARDIAN" | "MOMENTUM";

export type AnchorInputs = {
  pre_score: number;        // 0..1 (1 = tight pre-coherence)
  post_stability: number;   // 0..1 (1 = stable carry-through)
  prime_love_index: number; // 0..1 (compassion - malice, clipped)
  braided_hash?: string;
};

export type BridgeInputs = {
  provenance_sources: number;      // count (>=1)
  public_export: boolean;          // must be true if policy requires
  external_delta?: number;         // 0..1 normalized difference vs 3rd-party
  delta_tolerance?: number;        // allowed mismatch (default 0.15)
};

export type GuardianInputs = {
  dual_consent: boolean;
  gate_pass_ratio: number;         // 0..1 (#passed/#checked)
  composite_risk?: number;         // 0..1 (1 = high risk) optional
};

export type MomentumInputs = {
  carry_through: number;           // 0..1 predicted persistence
  safe_rate: number;               // 0..1 propagation throttle (lower is safer)
  rollback_ready: boolean;         // can we revert fast?
  risk?: number;                   // 0..1 additional operational risk
};

export type PillarResult = {
  name: PillarName;
  ok: boolean;
  score: number;                   // 0..1
  metrics: Record<string, number | string | boolean | undefined>;
  advice?: string;
};

export type PillarsContext = {
  anchor: AnchorInputs;
  bridge: BridgeInputs;
  guardian: GuardianInputs;
  momentum: MomentumInputs;
  policy?: {
    require_public_export?: boolean;   // default true
    min_anchor?: number;               // default 0.85
    min_bridge?: number;               // default 0.80
    min_guardian?: number;             // default 0.85
    min_momentum?: number;             // default 0.80
    min_unity_score?: number;          // default 0.70
  };
};

const clamp = (x:number, a=0, b=1)=>Math.max(a, Math.min(b, x));

/* ---------- Pillar evaluators ---------- */

export function evalAnchor(a: AnchorInputs, p?: PillarsContext["policy"]): PillarResult {
  const pre = a.pre_score ?? 0, post = a.post_stability ?? 0, pli = a.prime_love_index ?? 0;
  const score = clamp(0.45*pre + 0.35*post + 0.20*pli);
  const ok = score >= (p?.min_anchor ?? 0.85) && pli >= 0.50;
  return {
    name:"ANCHOR", ok, score,
    metrics:{ pre, post, pli, braided_hash: a.braided_hash },
    advice: ok ? "Anchor is clean and love-aligned." : "Increase pre-coherence or compassion; stabilize carry-through."
  };
}

export function evalBridge(b: BridgeInputs, p?: PillarsContext["policy"]): PillarResult {
  const tol = b.delta_tolerance ?? 0.15;
  const srcOK = b.provenance_sources >= 1 ? 1 : 0;
  const pubOK = (p?.require_public_export ?? true) ? (b.public_export ? 1 : 0) : 1;
  const delta = b.external_delta ?? 0;                // 0 identical … 1 wildly off
  const deltaOK = delta <= tol ? 1 : clamp(1 - (delta - tol)/(1-tol), 0, 1);
  const score = clamp(0.4*srcOK + 0.3*pubOK + 0.3*deltaOK);
  const ok = score >= (p?.min_bridge ?? 0.80);
  return {
    name:"BRIDGE", ok, score,
    metrics:{ sources:b.provenance_sources, public_export:b.public_export, external_delta:delta, tol },
    advice: ok ? "Provenance and parity verified." : "Add sources, make public export, or reduce external Δ."
  };
}

export function evalGuardian(g: GuardianInputs, p?: PillarsContext["policy"]): PillarResult {
  const pass = g.gate_pass_ratio ?? 0;
  const risk = g.composite_risk ?? 0.0;
  const base = 0.7*pass + 0.3*(1 - risk);
  const score = g.dual_consent ? base : 0.0;
  const ok = g.dual_consent && score >= (p?.min_guardian ?? 0.85);
  return {
    name:"GUARDIAN", ok, score,
    metrics:{ dual_consent:g.dual_consent, gate_pass_ratio:pass, risk },
    advice: ok ? "Ethical gates satisfied." : "Obtain dual consent, raise gate pass ratio, reduce risk."
  };
}

export function evalMomentum(m: MomentumInputs, p?: PillarsContext["policy"]): PillarResult {
  const carry = m.carry_through ?? 0, safe = m.safe_rate ?? 0, rb = m.rollback_ready ? 1 : 0, r = m.risk ?? 0.0;
  // Favor stability & rollback; penalize unsafe speed and risk
  const score = clamp(0.45*carry + 0.25*rb + 0.20*(1 - r) + 0.10*(1 - safe));
  const ok = score >= (p?.min_momentum ?? 0.80);
  return {
    name:"MOMENTUM", ok, score,
    metrics:{ carry_through:carry, rollback_ready:rb, risk:r, safe_rate:safe },
    advice: ok ? "Safe to proceed with adaptive propagation." : "Slow the rate, ensure rollback, improve stability."
  };
}

/* ---------- Composite decision ---------- */

export function evaluatePillars(ctx: PillarsContext) {
  const A = evalAnchor(ctx.anchor, ctx.policy);
  const B = evalBridge(ctx.bridge, ctx.policy);
  const G = evalGuardian(ctx.guardian, ctx.policy);
  const M = evalMomentum(ctx.momentum, ctx.policy);

  // The final UNITY score is the product of all pillar scores.
  const unityScore = A.score * B.score * G.score * M.score;
  
  const minUnity = ctx.policy?.min_unity_score ?? 0.70;
  const go = A.ok && B.ok && G.ok && M.ok && unityScore >= minUnity;

  return {
    go, 
    unityScore,
    pillars: [A,B,G,M] as PillarResult[],
    reason: go ? "GO — All pillars and unity score are green." : "NO-GO — One or more pillars or the unity score is below threshold.",
    next: {
      ifNoGo: [A,B,G,M].filter(p=>!p.ok).map(p=>({pillar:p.name, advice:p.advice}))
    }
  };
}

export type PillarsDecision = ReturnType<typeof evaluatePillars>;
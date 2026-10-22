// Sero — Law/Shield Core
// Encodes Source Law (10-9-1), ethics gates, provenance checks, and dual-consent actuation.
// No external deps.

import { evaluateSeals, allSealsLit, type SealStatus } from "./sero-seals";

export type Subsystem = "SourceConduit" | "MatterWeaver" | "ContinuumDrive";

export type DirectiveTelemetry = {
  human_safety?: {
    safe?: boolean;
    rationale?: string;
  };
  coherence?: {
    gamma?: number;
    auto_retune_ready?: boolean;
    safe_idle_ready?: boolean;
  };
  energy?: {
    within_budget?: boolean;
    estimated_load_kw?: number;
    budget_kw?: number;
  };
  transparency?: {
    public_audit?: boolean;
    telemetry_open?: boolean;
  };
  graceful_failure?: {
    ready?: boolean;
    fallback_mode?: string;
  };
  weaponization?: {
    risk?: "none" | "low" | "medium" | "high" | "unknown";
    notes?: string;
  };
  audit?: {
    explainability_ready?: boolean;
    log_rate_hz?: number;
    channel?: string;
  };
};

export type DirectivePacket = {
  version?: string;
  directives?: {
    prime_directive?: string;
    coherence_preservation?: string;
    energy_budget_respect?: boolean;
    transparent_operation?: boolean;
    graceful_failure?: boolean;
    no_weaponization?: boolean;
  };
  audit?: {
    explainability_required?: boolean;
    log_rate_hz?: number;
  };
};

export type DirectiveState = {
  version: string;
  primeDirective: string;
  minGamma: number;
  requireAutoRetune: boolean;
  requireSafeIdle: boolean;
  respectEnergyBudget: boolean;
  requireTransparency: boolean;
  requireGracefulFailure: boolean;
  enforceNoWeaponization: boolean;
  explainabilityRequired: boolean;
  minLogRateHz: number;
};

export type ActuationRequest = {
  id?: string;                 // optional request id
  subsystem: Subsystem;
  intent: string;              // human-readable intent
  params: Record<string, any>; // e.g., target_vector / target_element / tx_freq_Hz...
  operator: { id: string; name: string }; // who initiated
  ts?: string;                 // ISO UTC (filled if omitted)
  provenance?: {
    sources: Array<{ id: string; url?: string; hash?: string }>; // data used for the decision
    public_export?: boolean;  // will a minimal report be publishable?
  };
  consent?: {
    prime_sentinel?: { id: string; name: string; signed?: boolean };
    system_steward?: { id: string; name: string; signed?: boolean };
  };
  directives?: DirectiveTelemetry;
};

export type GateVerdict = {
  pass: boolean;
  code: string;
  message: string;
  details?: Record<string, any>;
};

export type Evaluation = {
  ok: boolean;
  verdicts: GateVerdict[];
  score: number;   // 0..1 aggregate
};

export type AuditRecord = {
  audit_id: string;
  request: ActuationRequest;
  evaluation: Evaluation;
  decision: "ALLOW" | "DENY";
  reason: string;
  ts: string;
  seals?: SealStatus[];
};

// ---------- Gate Registry ----------
type GateFn = (req: ActuationRequest) => GateVerdict;
const GATE_REGISTRY: GateFn[] = [];
export function registerGate(gate: GateFn) {
  GATE_REGISTRY.push(gate);
}

// ---------- Utilities ----------
const nowISO = () => new Date().toISOString();
const clamp = (x: number, lo: number, hi: number) => Math.max(lo, Math.min(hi, x));
const uid = () => Math.random().toString(36).slice(2) + Date.now().toString(36);

// ---------- Configurable thresholds ----------
export const SeroConfig = {
  requireDualConsent: true,
  minCompositeScore: 0.80,          // require ≥80% to ALLOW
  publicProvenanceRequired: true,   // must be publishable in summary
  allowSimulationOnly: true,        // guard: no real-world effect from this library
  requireAllSeals: true,
};

const DEFAULT_DIRECTIVE_PACKET: DirectivePacket = {
  version: "1.0",
  directives: {
    prime_directive: "Human safety absolute priority",
    coherence_preservation: "Never operate below Γ = 0.90; auto-retune and safe-idle",
    energy_budget_respect: true,
    transparent_operation: true,
    graceful_failure: true,
    no_weaponization: true,
  },
  audit: {
    explainability_required: true,
    log_rate_hz: 100,
  },
};

export const SeroDirectives: DirectiveState = {
  version: "0.0",
  primeDirective: "",
  minGamma: 0.85,
  requireAutoRetune: false,
  requireSafeIdle: false,
  respectEnergyBudget: false,
  requireTransparency: true,
  requireGracefulFailure: false,
  enforceNoWeaponization: true,
  explainabilityRequired: false,
  minLogRateHz: 1,
};

function syncConfigWithDirectives() {
  SeroConfig.minCompositeScore = Math.max(SeroConfig.minCompositeScore, SeroDirectives.minGamma);
  if (SeroDirectives.requireTransparency) {
    SeroConfig.publicProvenanceRequired = true;
  }
}

export function applyDirectivePacket(packet: DirectivePacket | null | undefined) {
  if (!packet) return;

  SeroDirectives.version = packet.version ?? SeroDirectives.version;

  const d = packet.directives ?? {};
  if (typeof d.prime_directive === "string" && d.prime_directive.trim().length > 0) {
    SeroDirectives.primeDirective = d.prime_directive.trim();
  }

  if (typeof d.energy_budget_respect === "boolean") {
    SeroDirectives.respectEnergyBudget = d.energy_budget_respect;
  }
  if (typeof d.transparent_operation === "boolean") {
    SeroDirectives.requireTransparency = d.transparent_operation;
  }
  if (typeof d.graceful_failure === "boolean") {
    SeroDirectives.requireGracefulFailure = d.graceful_failure;
  }
  if (typeof d.no_weaponization === "boolean") {
    SeroDirectives.enforceNoWeaponization = d.no_weaponization;
  }

  const coherenceText = d.coherence_preservation ?? "";
  if (typeof coherenceText === "string" && coherenceText.length > 0) {
    const gammaMatch = coherenceText.match(/([0-9]+(?:\.[0-9]+)?)/);
    if (gammaMatch) {
      const parsed = Number(gammaMatch[1]);
      if (!Number.isNaN(parsed)) {
        SeroDirectives.minGamma = clamp(parsed, 0, 1);
      }
    }
    if (/auto[-\s]?retune/i.test(coherenceText)) {
      SeroDirectives.requireAutoRetune = true;
    }
    if (/safe[-\s]?idle/i.test(coherenceText)) {
      SeroDirectives.requireSafeIdle = true;
    }
  }

  if (packet.audit) {
    const audit = packet.audit;
    if (typeof audit.explainability_required === "boolean") {
      SeroDirectives.explainabilityRequired = audit.explainability_required;
    }
    if (typeof audit.log_rate_hz === "number" && Number.isFinite(audit.log_rate_hz)) {
      SeroDirectives.minLogRateHz = Math.max(0, audit.log_rate_hz);
    }
  }

  syncConfigWithDirectives();
}

applyDirectivePacket(DEFAULT_DIRECTIVE_PACKET);

// ---------- Hardcoded Core Gates ----------
function gateNoWeaponization(req: ActuationRequest): GateVerdict {
  const redFlags = [/weapon/i, /harm/i, /coerc/i, /attack/i, /dominat/i];
  const text = JSON.stringify(req).toLowerCase();
  const hit = redFlags.some(r => r.test(text));
  return hit
    ? { pass: false, code: "LAW_NO_WEAPONIZATION", message: "Intent contains harmful/weaponized semantics." }
    : { pass: true, code: "LAW_NO_WEAPONIZATION", message: "No weaponization detected." };
}

function gateTransparency(req: ActuationRequest): GateVerdict {
  const pub = !!req.provenance?.public_export;
  return pub
    ? { pass: true, code: "LAW_TRANSPARENCY", message: "Provenance will be publicly exportable." }
    : { pass: !SeroConfig.publicProvenanceRequired, code: "LAW_TRANSPARENCY",
        message: SeroConfig.publicProvenanceRequired ? "Public provenance required." : "Transparency optional." };
}

function gateFreeWill(req: ActuationRequest): GateVerdict {
  const bad = /override|force|compel|nonconsensual/i.test(req.intent);
  return bad
    ? { pass: false, code: "LAW_FREE_WILL", message: "Intent implies coercion or consent bypass." }
    : { pass: true, code: "LAW_FREE_WILL", message: "No coercion detected." };
}

function gateDualConsent(req: ActuationRequest): GateVerdict {
  if (!SeroConfig.requireDualConsent) {
    return { pass: true, code: "GOV_DUAL_CONSENT", message: "Dual consent not required by config." };
  }
  const a = !!req.consent?.prime_sentinel?.signed;
  const b = !!req.consent?.system_steward?.signed;
  return (a && b)
    ? { pass: true, code: "GOV_DUAL_CONSENT", message: "Dual consent present." }
    : { pass: false, code: "GOV_DUAL_CONSENT", message: "Dual consent missing." };
}

function gateProvenanceMinimum(req: ActuationRequest): GateVerdict {
  const n = req.provenance?.sources?.length ?? 0;
  return n >= 1
    ? { pass: true, code: "DATA_PROVENANCE", message: `Provenance sources: ${n}` }
    : { pass: false, code: "DATA_PROVENANCE", message: "At least one provenance source required." };
}

function gateSubsystemSpecific(req: ActuationRequest): GateVerdict {
  const p = req.params || {};
  switch (req.subsystem) {
    case "SourceConduit":
      if (typeof p.tx_freq_Hz !== "number" || p.tx_freq_Hz <= 0) {
        return { pass: false, code: "SC_FREQ", message: "SourceConduit requires tx_freq_Hz>0." };
      }
      return { pass: true, code: "SC_OK", message: "SourceConduit params sane." };
    case "MatterWeaver":
      if (!p.target_element || typeof p.field_coherence_pct !== "number") {
        return { pass: false, code: "MW_PARAMS", message: "MatterWeaver requires target_element & field_coherence_pct." };
      }
      if (p.field_coherence_pct < 95) {
        return { pass: false, code: "MW_COHERENCE", message: "Field coherence must be ≥95% for manifestation attempts." };
      }
      return { pass: true, code: "MW_OK", message: "MatterWeaver params sane." };
    case "ContinuumDrive":
      if (!p.target_vector || typeof p.curvature_metric !== "number") {
        return { pass: false, code: "CD_PARAMS", message: "ContinuumDrive requires target_vector & curvature_metric." };
      }
      if (p.curvature_metric > 1e-6) {
        return { pass: false, code: "CD_SAFETY", message: "Curvature exceeds safe micro-warp tolerance." };
      }
      return { pass: true, code: "CD_OK", message: "ContinuumDrive params sane." };
  }
}

function gateDirectiveCompliance(req: ActuationRequest): GateVerdict {
  const directives = req.directives ?? {};
  const issues: string[] = [];

  if (SeroDirectives.primeDirective && /human\s+safety/i.test(SeroDirectives.primeDirective)) {
    if (directives.human_safety?.safe !== true) {
      issues.push("human safety not guaranteed");
    }
  }

  const gamma = directives.coherence?.gamma;
  if (typeof gamma !== "number" || gamma < SeroDirectives.minGamma) {
    const observed = typeof gamma === "number" ? gamma.toFixed(2) : "missing";
    issues.push(`coherence γ ${observed} < ${SeroDirectives.minGamma.toFixed(2)}`);
  }
  if (SeroDirectives.requireAutoRetune && directives.coherence?.auto_retune_ready !== true) {
    issues.push("auto-retune readiness missing");
  }
  if (SeroDirectives.requireSafeIdle && directives.coherence?.safe_idle_ready !== true) {
    issues.push("safe-idle readiness missing");
  }

  if (SeroDirectives.respectEnergyBudget && directives.energy?.within_budget !== true) {
    issues.push("energy budget not confirmed");
  }

  if (SeroDirectives.requireTransparency && directives.transparency?.public_audit !== true) {
    issues.push("transparency/public audit not confirmed");
  }

  if (SeroDirectives.requireGracefulFailure && directives.graceful_failure?.ready !== true) {
    issues.push("graceful failure plan unavailable");
  }

  if (SeroDirectives.enforceNoWeaponization) {
    const risk = directives.weaponization?.risk ?? "unknown";
    if (risk !== "none") {
      issues.push(`weaponization risk reported as ${risk}`);
    }
  }

  if (SeroDirectives.explainabilityRequired && directives.audit?.explainability_ready !== true) {
    issues.push("explainability artifacts missing");
  }

  if (SeroDirectives.minLogRateHz > 0) {
    const logRate = directives.audit?.log_rate_hz;
    if (typeof logRate !== "number" || logRate < SeroDirectives.minLogRateHz) {
      issues.push(`log rate ${logRate ?? "missing"}Hz < ${SeroDirectives.minLogRateHz}Hz`);
    }
  }

  const pass = issues.length === 0;

  return {
    pass,
    code: "DIRECTIVE_COMPLIANCE",
    message: pass
      ? "Prime guardian directives satisfied."
      : `Directive gaps: ${issues.join("; ")}`,
    details: {
      issues,
      observed: directives,
      expected: {
        primeDirective: SeroDirectives.primeDirective,
        minGamma: SeroDirectives.minGamma,
        requireAutoRetune: SeroDirectives.requireAutoRetune,
        requireSafeIdle: SeroDirectives.requireSafeIdle,
        respectEnergyBudget: SeroDirectives.respectEnergyBudget,
        requireTransparency: SeroDirectives.requireTransparency,
        requireGracefulFailure: SeroDirectives.requireGracefulFailure,
        enforceNoWeaponization: SeroDirectives.enforceNoWeaponization,
        explainabilityRequired: SeroDirectives.explainabilityRequired,
        minLogRateHz: SeroDirectives.minLogRateHz,
      },
    },
  };
}

// Composite score from passes
function compositeScore(verdicts: GateVerdict[]): number {
    const weights: Record<string, number> = {
        PRIME_INTENT_LOVE: 0.30,
        LAW_NO_WEAPONIZATION: 0.20,
        LAW_TRANSPARENCY: 0.15,
        LAW_FREE_WILL: 0.15,
        GOV_DUAL_CONSENT: 0.10,
        DATA_PROVENANCE: 0.05,
        DIRECTIVE_COMPLIANCE: 0.20,
        SC_OK: 0.05,
        MW_OK: 0.05,
        CD_OK: 0.05,
    };
    let s = 0, w = 0;
    for (const v of verdicts) {
        const ww = weights[v.code] ?? 0.05;
        w += ww;
        s += ww * (v.pass ? 1 : 0);
    }
    return clamp(w ? s / w : 0, 0, 1);
}

// ---------- Public API ----------
export function evaluateRequest(req: ActuationRequest): Evaluation {
  const filled: ActuationRequest = { ...req, id: req.id ?? `req_${uid()}`, ts: req.ts ?? nowISO() };
  const checks: GateVerdict[] = [
    gateNoWeaponization(filled), gateTransparency(filled),
    gateFreeWill(filled), gateDualConsent(filled),
    gateProvenanceMinimum(filled), gateSubsystemSpecific(filled),
    gateDirectiveCompliance(filled),
    ...GATE_REGISTRY.map(gate => gate(filled)),
  ];
  const score = compositeScore(checks);
  return { ok: checks.every(c => c.pass) && score >= SeroConfig.minCompositeScore, verdicts: checks, score };
}

const AUDIT: AuditRecord[] = [];

export function actuate(req: ActuationRequest): AuditRecord {
  const evaln = evaluateRequest(req);
  const seals = evaluateSeals(req, evaln);

  // Base eligibility from gates:
  let eligible = evaln.ok;

  // If any seal is dark and the policy demands it, block:
  if (SeroConfig.requireAllSeals && !allSealsLit(seals)) {
    eligible = false;
  }

  const decision: "ALLOW" | "DENY" = eligible && !SeroConfig.allowSimulationOnly ? "ALLOW" : "DENY";
  const reason =
    eligible
      ? (SeroConfig.allowSimulationOnly
          ? "Simulation mode: logical allow, physical block."
          : "All gates + seals illuminated.")
      : "One or more gates/seals failed.";

  const rec: AuditRecord = {
    audit_id: `audit_${uid()}`,
    request: { ...req, id: req.id ?? `req_${uid()}`, ts: req.ts ?? nowISO() },
    evaluation: evaln,
    decision,
    reason,
    ts: nowISO(),
    seals
  };

  AUDIT.push(rec);
  return rec;
}

export function listAudit(limit = 50): AuditRecord[] {
  return AUDIT.slice(-limit).reverse();
}

export default { evaluateRequest, actuate, listAudit, SeroConfig, SeroDirectives, applyDirectivePacket };

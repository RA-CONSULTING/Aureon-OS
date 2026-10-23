import express, { Request, Response } from "express";
import { verify as verifyEd25519 } from "@noble/ed25519";

/** Types **/
type Hex = string;

export interface Manifest {
  capsule_id: string;
  nodePublicKey: Hex;
  controllerPublicKey: Hex;
  signature: Hex;
  [key: string]: unknown;
}

interface ProofBundle {
  zkBalanceOk: Hex;
  energy: number;
  gini: number;
  phaseErr: number;
  [key: string]: unknown;
}

interface WriteProposal {
  capsule_id: string;
  deltaHash: Hex;
  proofs: ProofBundle;
  sig: Hex;
  [key: string]: unknown;
}

interface CapsuleWeights {
  planet: number;
  people: number;
  progress: number;
  profit: number;
  dissonance: number;
  coherence: number;
}

const app = express();
app.set("query parser", "extended");
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

const manifests = new Map<string, Manifest>();
const balance = new Map<string, number>();

type ParamBag = Record<string, unknown>;

const PROPOSAL_CORE_KEYS = new Set(["capsule_id", "deltaHash", "sig", "proofs"]);
const PROOF_CORE_KEYS = new Set(["zkBalanceOk", "energy", "gini", "phaseErr"]);

function mergeParams(req: Request): ParamBag {
  const bodySource =
    typeof req.body === "string"
      ? safeJsonParse<Record<string, unknown>>(req.body) ?? {}
      : req.body;
  const body = toParamBag(bodySource);
  const query = toParamBag(req.query);
  return deepMerge(body, query);
}

function toParamBag(source: unknown): ParamBag {
  if (!isPlainObject(source)) {
    return {};
  }

  return Object.fromEntries(
    Object.entries(source as Record<string, unknown>).map(([key, value]) => [key, normalizeParamValue(value)])
  );
}

function normalizeParamValue(value: unknown): unknown {
  if (Array.isArray(value)) {
    if (value.length === 1) {
      return normalizeParamValue(value[0]);
    }
    return value.map((item) => normalizeParamValue(item));
  }

  if (typeof value === "string") {
    const trimmed = value.trim();
    if (trimmed.startsWith("{") || trimmed.startsWith("[")) {
      const parsed = safeJsonParse<unknown>(trimmed);
      if (parsed !== undefined) {
        return normalizeParamValue(parsed);
      }
    }
    return value;
  }

  if (isPlainObject(value)) {
    return toParamBag(value);
  }

  return value;
}

function deepMerge(base: ParamBag, overrides: ParamBag): ParamBag {
  const result: ParamBag = { ...base };

  for (const [key, value] of Object.entries(overrides)) {
    if (value === undefined) {
      continue;
    }

    if (isPlainObject(value) && isPlainObject(result[key])) {
      result[key] = deepMerge(result[key] as ParamBag, value as ParamBag);
    } else {
      result[key] = value;
    }
  }

  return result;
}

function resolveManifest(params: ParamBag): Manifest | undefined {
  if ("manifest" in params) {
    return normalizeManifest(params.manifest);
  }
  return normalizeManifest(params);
}

function resolveWriteProposal(params: ParamBag): WriteProposal | undefined {
  if ("proposal" in params) {
    return normalizeWriteProposal(params.proposal);
  }
  return normalizeWriteProposal(params);
}

function normalizeManifest(value: unknown): Manifest | undefined {
  if (typeof value === "string") {
    const parsed = safeJsonParse<unknown>(value);
    if (parsed === undefined) {
      return undefined;
    }
    return normalizeManifest(parsed);
  }

  if (!isPlainObject(value)) {
    return undefined;
  }

  const candidate = value as Manifest;
  if (!isManifest(candidate)) {
    return undefined;
  }

  return { ...candidate };
}

function normalizeWriteProposal(value: unknown): WriteProposal | undefined {
  if (typeof value === "string") {
    const parsed = safeJsonParse<unknown>(value);
    if (parsed === undefined) {
      return undefined;
    }
    return normalizeWriteProposal(parsed);
  }

  if (!isPlainObject(value)) {
    return undefined;
  }

  const record = value as Record<string, unknown>;
  const proofs = normalizeProofBundle(record.proofs);
  const capsule_id = record.capsule_id;
  const deltaHash = record.deltaHash;
  const sig = record.sig;

  if (typeof capsule_id !== "string" || typeof deltaHash !== "string" || typeof sig !== "string" || !proofs) {
    return undefined;
  }

  const normalized: WriteProposal = { capsule_id, deltaHash: deltaHash as Hex, sig: sig as Hex, proofs };

  for (const [key, val] of Object.entries(record)) {
    if (!PROPOSAL_CORE_KEYS.has(key)) {
      normalized[key] = val;
    }
  }

  return normalized;
}

function normalizeProofBundle(value: unknown): ProofBundle | undefined {
  if (typeof value === "string") {
    const parsed = safeJsonParse<unknown>(value);
    if (parsed === undefined) {
      return undefined;
    }
    return normalizeProofBundle(parsed);
  }

  if (!isPlainObject(value)) {
    return undefined;
  }

  const record = value as Record<string, unknown>;
  const zkBalanceOk = record.zkBalanceOk;
  const energy = toNumber(record.energy);
  const gini = toNumber(record.gini);
  const phaseErr = toNumber(record.phaseErr);

  if (typeof zkBalanceOk !== "string" || energy === undefined || gini === undefined || phaseErr === undefined) {
    return undefined;
  }

  const normalized: ProofBundle = { zkBalanceOk, energy, gini, phaseErr };

  for (const [key, val] of Object.entries(record)) {
    if (!PROOF_CORE_KEYS.has(key)) {
      normalized[key] = val;
    }
  }

  return normalized;
}

function toNumber(value: unknown): number | undefined {
  if (typeof value === "number" && Number.isFinite(value)) {
    return value;
  }

  if (typeof value === "string") {
    const trimmed = value.trim();
    if (trimmed === "") {
      return undefined;
    }
    const parsed = Number(trimmed);
    if (Number.isFinite(parsed)) {
      return parsed;
    }
  }

  return undefined;
}

function isPlainObject(value: unknown): value is ParamBag {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

function safeJsonParse<T>(input: string): T | undefined {
  try {
    return JSON.parse(input) as T;
  } catch {
    return undefined;
  }
}

function isManifest(value: Manifest | ParamBag): value is Manifest {
  return (
    typeof value.capsule_id === "string" &&
    typeof value.nodePublicKey === "string" &&
    typeof value.controllerPublicKey === "string" &&
    typeof value.signature === "string"
  );
}

async function acceptWrite(
  prevB: number,
  proofs: ProofBundle,
  weights: CapsuleWeights
): Promise<boolean> {
  const { energy, gini, phaseErr } = proofs;
  const ceilings = { energy_safe: 11.2, gini_max: 0.65, phase_error: 0.2 } as const;

  const riskRatios = {
    energy: energy / ceilings.energy_safe,
    gini: gini / ceilings.gini_max,
    phase: Math.abs(phaseErr) / ceilings.phase_error,
  };

  const aggregateRisk =
    (riskRatios.energy * weights.planet +
      riskRatios.gini * weights.people +
      riskRatios.phase * weights.dissonance) /
    (weights.planet + weights.people + weights.dissonance);

  if (
    energy > ceilings.energy_safe ||
    gini > ceilings.gini_max ||
    Math.abs(phaseErr) > ceilings.phase_error ||
    aggregateRisk > 1
  ) {
    return false;
  }

  return verifyZK(proofs.zkBalanceOk, prevB);
}

app.post("/v1/register", async (req: Request, res: Response) => {
  const params = mergeParams(req);
  const manifest = resolveManifest(params);

  if (!manifest) {
    return res.status(400).json({ error: "manifest is required" });
  }

  if (!(await verifyManifestSig(manifest))) {
    return res.status(400).json({ error: "bad signature" });
  }

  manifests.set(manifest.capsule_id, manifest);
  balance.set(manifest.capsule_id, initialBalance());

  return res.json({ ok: true });
});

app.post("/v1/write", async (req: Request, res: Response) => {
  const params = mergeParams(req);
  const proposal = resolveWriteProposal(params);

  if (!proposal?.capsule_id || !proposal.proofs) {
    return res.status(400).json({ error: "invalid proposal" });
  }

  const manifest = manifests.get(proposal.capsule_id);
  if (!manifest) {
    return res.status(404).json({ error: "capsule not registered" });
  }

  if (!(await verifyNodeSig(proposal, manifest))) {
    return res.status(403).json({ error: "auth failed" });
  }

  const prevB = balance.get(proposal.capsule_id);
  if (typeof prevB !== "number") {
    return res.status(500).json({ error: "balance state missing" });
  }

  const writeAccepted = await acceptWrite(
    prevB,
    proposal.proofs,
    getWeights(proposal.capsule_id)
  );

  if (!writeAccepted) {
    return res.json({ status: "SAFE_MODE", hint: remediation(prevB) });
  }

  const newB = revealedOrDerivedB(proposal.proofs, prevB);
  balance.set(proposal.capsule_id, newB);

  return res.json({ status: "ACCEPT", balance: newB });
});

app.listen(8787, () => {
  console.log("Reference service listening on port 8787");
});

function verifyZK(pi: Hex, prevB: number): boolean {
  if (!isHex(pi)) {
    return false;
  }
  return prevB >= 0;
}

async function verifyManifestSig(manifest: Manifest): Promise<boolean> {
  const { signature, controllerPublicKey, ...payload } = manifest;

  if (!isHex(signature) || !isHex(controllerPublicKey)) {
    return false;
  }

  const messageBytes = new TextEncoder().encode(
    canonicalize({ ...payload, controllerPublicKey })
  );
  const signatureBytes = hexToBytes(signature);
  const publicKeyBytes = hexToBytes(controllerPublicKey);

  return verifyEd25519(signatureBytes, messageBytes, publicKeyBytes);
}

async function verifyNodeSig(
  proposal: WriteProposal,
  manifest: Manifest
): Promise<boolean> {
  if (!manifest.nodePublicKey || !isHex(manifest.nodePublicKey)) {
    return false;
  }

  if (!proposal.sig || !isHex(proposal.sig)) {
    return false;
  }

  const messageBytes = new TextEncoder().encode(
    canonicalize({
      capsule_id: proposal.capsule_id,
      deltaHash: proposal.deltaHash,
      proofs: proposal.proofs,
    })
  );

  return verifyEd25519(
    hexToBytes(proposal.sig),
    messageBytes,
    hexToBytes(manifest.nodePublicKey)
  );
}

function initialBalance(): number {
  return 1.0;
}

function getWeights(_id: string): CapsuleWeights {
  return {
    planet: 1,
    people: 0.8,
    progress: 0.6,
    profit: 0.2,
    dissonance: 0.7,
    coherence: 0.5,
  };
}

function remediation(prevB: number) {
  return {
    reduce_dissonance: prevB > 0.5,
    shrink_bandwidth: true,
    request_human_consent: prevB < 0.2,
  };
}

function revealedOrDerivedB(proofs: ProofBundle, prevB: number): number {
  const deduction =
    proofs.energy * 0.01 + proofs.gini * 0.02 + Math.abs(proofs.phaseErr) * 0.05;
  return Math.max(0, Number((prevB - deduction).toFixed(4)));
}

function canonicalize(value: unknown): string {
  if (value === null || typeof value !== "object") {
    return JSON.stringify(value);
  }

  if (Array.isArray(value)) {
    return `[${value.map((item) => canonicalize(item)).join(",")}]`;
  }

  const record = value as Record<string, unknown>;
  const entries = Object.keys(record)
    .filter((key) => record[key] !== undefined)
    .sort()
    .map((key) => `${JSON.stringify(key)}:${canonicalize(record[key])}`);

  return `{${entries.join(",")}}`;
}

function isHex(value: string | undefined): value is string {
  return typeof value === "string" && /^[0-9a-fA-F]+$/.test(value);
}

function hexToBytes(hex: string): Uint8Array {
  if (hex.length % 2 !== 0) {
    throw new Error("hex string must have an even length");
  }

  const bytes = new Uint8Array(hex.length / 2);

  for (let i = 0; i < hex.length; i += 2) {
    bytes[i / 2] = parseInt(hex.slice(i, i + 2), 16);
  }

  return bytes;
}

export { app };

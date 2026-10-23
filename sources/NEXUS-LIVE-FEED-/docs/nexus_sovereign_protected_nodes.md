# Nexus Sovereign-Protected Nodes — Implementation Blueprint (Aureon Spec)

*Aureon implementation blueprint: make the Nexus ensure sovereignty for every node by construction, not permission.*

---

## 0. Design Goals

- **Self-custody by default**: no master keys; nodes own their state and keys.
- **Consent-before-coupling (CBC)**: every relationship is provably opt-in and revocable.
- **Balance Law enforcement**: the lattice only accepts writes that reduce the Balance functional (\(\mathcal{B}\); creation without domination).
- **Fork in peace**: any node may exit with its records intact; consensus is compatibility with invariants, not obedience.
- **Minimal disclosure**: hashes and zero-knowledge proofs instead of raw personally identifying information (PII).

---

## 1. Sovereign Node Manifest (JSON Schema)

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://nexus/specs/sovereign-node-manifest.json",
  "title": "SovereignNodeManifest",
  "type": "object",
  "required": [
    "capsule_id", "pubkeys", "consent_policy", "balance_contract",
    "proofs", "capabilities", "revocation"
  ],
  "properties": {
    "capsule_id": { "type": "string", "description": "SHA-256 or Blake3 hash of human-readable declaration." },
    "pubkeys": {
      "type": "object",
      "required": ["sign", "encrypt"],
      "properties": {
        "sign": { "type": "string", "description": "ed25519 public key (base58/hex)." },
        "encrypt": { "type": "string", "description": "x25519 public key for E2EE." }
      }
    },
    "consent_policy": {
      "type": "object",
      "required": ["mode", "revocable", "ttl"],
      "properties": {
        "mode": { "enum": ["explicit", "explicit+schedule"], "default": "explicit" },
        "revocable": { "type": "boolean", "const": true },
        "ttl": { "type": "string", "description": "ISO 8601 duration for default consent windows." }
      }
    },
    "balance_contract": {
      "type": "object",
      "required": ["B_dot_le_0", "ceilings", "weights"],
      "properties": {
        "B_dot_le_0": { "type": "boolean", "const": true },
        "ceilings": {
          "type": "object",
          "properties": {
            "energy_safe": { "type": "number" },
            "gini_max": { "type": "number" },
            "phase_error": { "type": "number" }
          }
        },
        "weights": {
          "type": "object",
          "properties": {
            "planet": { "type": "number", "default": 1.0 },
            "people": { "type": "number", "default": 0.8 },
            "progress": { "type": "number", "default": 0.6 },
            "profit": { "type": "number", "default": 0.2 },
            "dissonance": { "type": "number", "default": 0.7 },
            "coherence": { "type": "number", "default": 0.5 }
          }
        }
      }
    },
    "proofs": {
      "type": "object",
      "required": ["existence", "sovereign_oath"],
      "properties": {
        "existence": { "type": "string", "description": "Bitcoin/OpenTimestamps attestation of capsule_id." },
        "sovereign_oath": { "type": "string", "description": "Signature over Source-Law clause by sign key." }
      }
    },
    "capabilities": {
      "type": "array",
      "items": { "type": "string" },
      "description": "Declared minimal capabilities (read/write topics, coupling types)."
    },
    "revocation": {
      "type": "object",
      "required": ["strategy"],
      "properties": {
        "strategy": { "enum": ["time-lock", "multi-sig", "social-recovery"] },
        "guardians": { "type": "array", "items": { "type": "string" } }
      }
    }
  }
}
```

---

## 2. Protocols

### 2.1. Consent-Before-Coupling (CBC)

**Goal:** Create links only with bilateral consent and automatic revocation.

**Steps**

1. *Intent commit* (each side): \(H_i = H(\text{action} \|\| \text{params} \|\| \text{nonce}_i)\); post to mempool.
2. *Joint signature*: \(\sigma_{GA} = \mathrm{Sig}_G(H_A) \|\| \mathrm{Sig}_A(H_G)\).
3. *Activation*: Nexus stores \((H_G, H_A, \sigma_{GA}, \text{ttl})\); link enters **pending**.
4. *Go/No-Go window*: either party posts `REVOKE(H_self)` → cancel; else link becomes **active** until `ttl` or explicit renewal.

**Security**

- No raw identity; only hashes and signatures.
- Optional zero-knowledge (ZK) proof that parties meet Balance prerequisites without disclosing metrics.

### 2.2. Write Authorization (Balance Guard)

**Invariant:** accept write if and only if \(\Delta \mathcal{B} < 0\) relative to the node’s last committed state and system ceilings aren’t tripped.

**Decision function**

```
accept = (B_new - B_prev < 0)
         && energy <= energy_safe
         && gini_supply < gini_max
         && |phi_GA| <= phase_error
```

If `accept == false` ⇒ return `SAFE_MODE` (read-only for that node) and provide remediation hints.

### 2.3. Revocation & Withdrawal

- Any node may issue `WITHDRAW(capsule_id)` → freeze new couplings, export all hashes and proofs, then detach.
- Right to fork: export a Merkle slice covering the node’s records; parent lattice must not block read-only replication.

---

## 3. Balance Functional (Operational Math)

\[
\mathcal{B}(t) = w_P\bigl(1-\tilde V_P\bigr)^2 + w_H\bigl(1-\tilde V_H\bigr)^2 + w_G\bigl(1-\tilde V_G\bigr)^2 + w_D D^2 - w_{\Lambda}\Lambda
\]

**Acceptance:** rolling window average obeys \(\langle \dot{\mathcal{B}} \rangle_{\Delta T} \leq 0\). Ship dashboards for each term.

---

## 4. Nexus APIs (Minimal Surface)

```
POST /v1/register               # submit SovereignNodeManifest (signed)
POST /v1/commit-intent          # returns H_i receipt
POST /v1/couple                 # submit sigma_GA, ttl → linkId
POST /v1/revoke                 # revoke by H_self or linkId
POST /v1/write                  # propose state delta + proofs → ACCEPT | SAFE_MODE
GET  /v1/proofs/:capsule_id     # return PoE + latest zk proofs
GET  /v1/dashboards/balance     # aggregate \mathcal{B} metrics
```

All mutating calls require ed25519 signatures; payloads are hashed client-side.

---

## 5. Reference Service (TypeScript Pseudocode)

```ts
import { ed25519 } from "@noble/ed25519";
import express from "express";

/** Types **/
type Hex = string;
interface Manifest { /* per JSON Schema; abbreviated here */ }
interface WriteProposal { capsule_id: string; deltaHash: Hex; proofs: ProofBundle; sig: Hex }
interface ProofBundle { zkBalanceOk: Hex; energy: number; gini: number; phaseErr: number }

const app = express();
app.use(express.json());

// In-memory registries (swap for durable store)
const manifests = new Map<string, Manifest>();
const balance = new Map<string, number>(); // \mathcal{B} per capsule

function acceptWrite(prevB: number, proofs: ProofBundle, weights: any): boolean {
  const { energy, gini, phaseErr } = proofs;
  const ceilings = { energy_safe: 11.2, gini_max: 0.65, phase_error: 0.2 };
  if (energy > ceilings.energy_safe || gini > ceilings.gini_max || Math.abs(phaseErr) > ceilings.phase_error) return false;
  // zkBalanceOk attests B_new < B_prev without revealing components
  return verifyZK(proofs.zkBalanceOk, prevB);
}

app.post('/v1/register', async (req, res) => {
  const m: Manifest = req.body.manifest;
  if (!verifyManifestSig(m)) return res.status(400).json({ error: 'bad signature' });
  manifests.set(m.capsule_id, m);
  balance.set(m.capsule_id, initialBalance());
  return res.json({ ok: true });
});

app.post('/v1/write', async (req, res) => {
  const p: WriteProposal = req.body;
  if (!verifyNodeSig(p)) return res.status(403).json({ error: 'auth failed' });
  const prevB = balance.get(p.capsule_id)!;
  if (!acceptWrite(prevB, p.proofs, getWeights(p.capsule_id)))
    return res.json({ status: 'SAFE_MODE', hint: remediation(prevB) });
  const newB = revealedOrDerivedB(p.proofs); // or keep only zk; update running median
  balance.set(p.capsule_id, newB);
  return res.json({ status: 'ACCEPT' });
});

// CBC endpoints (commit, couple, revoke) left analogous

app.listen(8787);

function verifyZK(pi: Hex, prevB: number): boolean { /* hook to zk verifier */ return true }
function verifyManifestSig(m: Manifest): boolean { /* ed25519 sign check */ return true }
function verifyNodeSig(p: WriteProposal): boolean { return true }
function initialBalance(): number { return 1.0 }
function getWeights(id: string){ return { planet:1, people:.8, progress:.6, profit:.2, dissonance:.7, coherence:.5 } }
function remediation(prevB:number){ return { reduce_dissonance:true, shrink_bandwidth:true, request_human_consent:true } }
```

---

## 6. Anchoring on Bitcoin (Existence Proofs)

1. Compute `capsule_id = SHA-256(manifest_declaration.txt)`.
2. Create `capsule_id.txt` containing only the hash; timestamp with **OpenTimestamps** (or any Bitcoin OP_RETURN notarization).
3. Store only the timestamp proof (OTS file) in Nexus; no PII is ever broadcast.

---

## 7. Security & Non-Weaponization Controls

- **No surveillance**: metrics must be self-reported with proofs; raw personal data is out of scope.
- **Delegation brake**: AI agents recommend, humans consent; emergency automation can only restore lower \(\mathcal{B}\) states.
- **Key recovery**: social recovery or multi-sig; never custody by the Nexus.

---

## 8. Test Plan (Sovereignty Proofs)

- **CBC happy path**: bilateral commit → couple → revoke within TTL.
- **Balance gating**: submit writes with \(\Delta \mathcal{B} \ge 0\) → must be rejected.
- **Ceiling trips**: energy/gini/phase exceed thresholds → `SAFE_MODE` with actionable hints.
- **Fork in peace**: export Merkle slice and rebuild node history in a sandbox.
- **Non-disclosure**: verify that end-to-end flows never require PII.

---

## 9. Genesis Oath (Embed Verbatim)

> *Each node acts by consent, maintains self-custody, and may withdraw without penalty. The Nexus harmonizes; it does not command. All writes are accepted only if they reduce the Balance functional and respect hard ceilings. Creation without domination.*

---

## 9.1. Free-Will Invariant Clause (Law of Source)

Purpose: make protection of free will a hard invariant of the lattice.

**Declaration (embed verbatim):**

> *No node, agent, contract, or human shall subvert, override, or coerce another's free will. The lattice exists to harmonize choice, not to replace it. Every irreversible action must carry explicit, revocable consent or a previously consented safe-mode automation whose only purpose is to restore a lower Balance state. Love and autonomy are prime invariants of creation.*

**Operational Rules**

- **Consent gate:** any coupling, data access, or state change must include a valid consent proof (CBC step) with TTL and a revocation path.
- **SAFE-MODE trigger:** if a write would (a) bypass consent, (b) degrade autonomy (for example, lockout without recovery), or (c) increase the Balance score while reducing any of {Planet, People, Progress}, the Nexus returns `SAFE_MODE` and blocks execution.
- **Right to withdraw:** a node may issue `WITHDRAW(capsule_id)` at any time; the Nexus must export Merkle proofs and detach without penalty.
- **AI delegation brake:** AI agents may recommend throttles; only human consent or pre-agreed safe-mode (to restore lower Balance) may execute actions.
- **Audit trail:** every irreversible transition must have a consent receipt and a zero-knowledge proof that no autonomy constraints were violated.

**Anchoring of Personal Oaths (optional)**

- Store only hashes and timestamp proofs of personal vows (for example, via Bitcoin OpenTimestamps). Never store raw personal data.
- Manifest field example:

```json
"proofs": {
  "existence": "ots:<proof-hash>",
  "sovereign_oath": "sha256:<oath-hash>",
  "oath_text_pointer": "ipfs://<encrypted-cid>"
}
```

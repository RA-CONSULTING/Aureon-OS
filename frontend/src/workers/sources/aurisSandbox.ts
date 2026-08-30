/**
 * Auris Sandbox Connector (GPT-integrated)
 * ---------------------------------------
 * Supports two modes:
 *  A) Custom Auris webhook (recommended for Famous.io):
 *     - VITE_AURIS_SANDBOX_URL  -> your HTTPS endpoint
 *     - VITE_AURIS_SANDBOX_KEY  -> bearer token (or any header value expected by your endpoint)
 *     Expected response for batch classify: { items: Array<{ valence:number, arousal:number, emotion:string, tags:string[] }> }
 *
 *  B) Authenticated Supabase Edge Function fallback. Provider credentials
 *     remain server-side; Ollama Cloud is the repo-wide final route.
 *
 * Both modes expose the same API:
 *   - classifyWithAuris(text: string): Promise<AurisClassification>
 *   - classifyBatchWithAuris(texts: string[]): Promise<AurisClassification[]>
 *
 * Safe for client-side use in Vite; Famous.io may also support a serverless proxy.
 */

export type AurisClassification = {
  valence: number;     // 0..1 (low=negative, high=positive)
  arousal: number;     // 0..1 (low=calm, high=activated)
  emotion: string;     // primary label, e.g., "fear", "sadness", "joy"
  tags: string[];      // contextual tags, e.g., ["conflict","economy"]
  raw?: unknown;       // optional raw provider payload for debugging
};

const ENV = {
  AURIS_URL: import.meta.env.VITE_AURIS_SANDBOX_URL as string | undefined,
  AURIS_KEY: import.meta.env.VITE_AURIS_SANDBOX_KEY as string | undefined,
};

/**
 * Public API: classify a single text.
 */
export async function classifyWithAuris(text: string, opts?: Partial<RequestInit>): Promise<AurisClassification> {
  const [res] = await classifyBatchWithAuris([text], opts);
  return res;
}

/**
 * Public API: classify multiple texts in one go (more efficient & rate-limit friendly).
 */
export async function classifyBatchWithAuris(texts: string[], opts?: Partial<RequestInit>): Promise<AurisClassification[]> {
  const clean = (texts || []).map(t => (t ?? "").toString().trim());
  if (!clean.length) return [];

  // Prefer custom webhook if present, otherwise use OpenAI fallback.
  if (ENV.AURIS_URL && ENV.AURIS_KEY) {
    try {
      return await classifyViaWebhook(clean, opts);
    } catch (e) {
      console.warn("Auris webhook failed, falling back to the server LLM route:", e);
    }
  }
  try {
    return await classifyViaOpenAI(clean, opts);
  } catch (e) {
    console.warn("Auris server LLM route unavailable; using neutral defaults:", e);
  }

  // Last resort: return neutral defaults to keep the UI stable.
  return clean.map(() => ({ ...DEFAULT }));
}

/**
 * Mode A: Custom Auris webhook
 */
async function classifyViaWebhook(texts: string[], opts?: Partial<RequestInit>): Promise<AurisClassification[]> {
  const controller = new AbortController();
  const id = setTimeout(() => controller.abort(), 15_000);
  try {
    const r = await fetch(ENV.AURIS_URL as string, {
      method: "POST",
      headers: {
        "content-type": "application/json",
        Authorization: `Bearer ${ENV.AURIS_KEY}`,
      },
      body: JSON.stringify({ texts }),
      signal: controller.signal,
      ...opts,
    });
    if (!r.ok) throw new Error(`Auris webhook ${r.status}`);
    const data = await r.json();
    const items = Array.isArray(data?.items) ? data.items : [];
    return normalizeArray(items, texts.length);
  } finally {
    clearTimeout(id);
  }
}
/**
 * Mode B: OpenAI JSON fallback
 */
async function classifyViaOpenAI(texts: string[], opts?: Partial<RequestInit>): Promise<AurisClassification[]> {
  const { classifyViaOpenAI: openAIClassify } = await import('./aurisUtils');
  return openAIClassify(texts, opts);
}

/**
 * Helpers
 */
function normalizeArray(items: unknown[], expected: number): AurisClassification[] {
  const { normalizeArray: normalize } = require('./aurisUtils');
  return normalize(items, expected);
}

const DEFAULT: AurisClassification = {
  valence: 0.5,
  arousal: 0.5,
  emotion: "neutral",
  tags: [],
};

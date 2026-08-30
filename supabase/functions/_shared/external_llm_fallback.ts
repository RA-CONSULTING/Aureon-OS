/** Server-side external-LLM routing shared by Aureon Supabase Edge Functions. */

export type ExternalLlmBody = Record<string, unknown>;

export interface ExternalLlmRequest {
  primaryApiKey?: string | null;
  primaryBody: ExternalLlmBody;
  primaryUrl?: string;
}

/** Parse an OpenAI-compatible message that may wrap JSON in prose or fences. */
export function parseExternalLlmJson<T>(content: unknown, fallback: T): T {
  const text = String(content || "").trim();
  if (!text) return fallback;

  const candidates = [text];
  const fenced = text.match(/```(?:json)?\s*([\s\S]*?)```/i);
  if (fenced?.[1]) candidates.push(fenced[1].trim());

  const objectStart = text.indexOf("{");
  const objectEnd = text.lastIndexOf("}");
  if (objectStart >= 0 && objectEnd > objectStart) {
    candidates.push(text.slice(objectStart, objectEnd + 1));
  }

  for (const candidate of candidates) {
    try {
      return JSON.parse(candidate) as T;
    } catch {
      // Try the next compatible representation.
    }
  }
  return fallback;
}

const DEFAULT_PRIMARY_URL = "https://ai.gateway.lovable.dev/v1/chat/completions";
const DEFAULT_OLLAMA_URL = "https://ollama.com/v1/chat/completions";

function env(name: string): string {
  return String(Deno.env.get(name) || "").trim();
}

function truthy(value: string): boolean {
  return ["1", "true", "yes", "on", "enabled"].includes(value.toLowerCase());
}

function ollamaFallbackEnabled(): boolean {
  const route = env("AUREON_EXTERNAL_LLM_FALLBACK").toLowerCase();
  if (["none", "off", "disabled", "false", "0"].includes(route)) return false;
  return route === "" || route === "ollama" || route === "ollama_cloud" || truthy(route);
}

function ollamaApiKey(): string {
  return env("OLLAMA_API_KEY") || env("AUREON_OLLAMA_API_KEY") || env("AUREON_LLM_API_KEY");
}

function ollamaEndpoint(): string {
  const configured = env("AUREON_LLM_BASE_URL") || env("AUREON_OLLAMA_BASE_URL");
  if (!configured) return DEFAULT_OLLAMA_URL;
  const base = configured.replace(/\/+$/, "");
  if (/\/chat\/completions$/i.test(base)) return base;
  if (/\/v1$/i.test(base)) return `${base}/chat/completions`;
  return `${base}/v1/chat/completions`;
}

function ollamaBody(primaryBody: ExternalLlmBody): ExternalLlmBody {
  const effort = env("AUREON_OLLAMA_REASONING_EFFORT").toLowerCase();
  const reasoningEffort = ["none", "low", "medium", "high"].includes(effort) ? effort : "none";
  return {
    ...primaryBody,
    model: env("AUREON_LLM_MODEL") || env("AUREON_OLLAMA_MODEL") || env("OLLAMA_MODEL") || "kimi-k2.7-code",
    reasoning_effort: reasoningEffort,
  };
}

function unavailableResponse(): Response {
  return new Response(
    JSON.stringify({ error: { message: "No external LLM provider is configured." } }),
    { status: 503, headers: { "Content-Type": "application/json" } },
  );
}

/**
 * Try the function's explicit gateway first, then Ollama Cloud. Response bodies
 * remain OpenAI-compatible, including streaming responses, so existing callers
 * can return or parse them unchanged. Credentials never leave server-side env.
 */
export async function fetchExternalLlm(request: ExternalLlmRequest): Promise<Response> {
  let primaryResponse: Response | null = null;
  const primaryKey = String(request.primaryApiKey || "").trim();

  if (primaryKey) {
    try {
      primaryResponse = await fetch(request.primaryUrl || DEFAULT_PRIMARY_URL, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${primaryKey}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify(request.primaryBody),
      });
      if (primaryResponse.ok) return primaryResponse;
    } catch {
      primaryResponse = null;
    }
  }

  const fallbackKey = ollamaApiKey();
  if (ollamaFallbackEnabled() && fallbackKey) {
    try {
      return await fetch(ollamaEndpoint(), {
        method: "POST",
        headers: {
          Authorization: `Bearer ${fallbackKey}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify(ollamaBody(request.primaryBody)),
      });
    } catch {
      // Preserve an explicit provider's response when available; otherwise
      // return a secret-free service-unavailable response below.
    }
  }

  return primaryResponse || unavailableResponse();
}

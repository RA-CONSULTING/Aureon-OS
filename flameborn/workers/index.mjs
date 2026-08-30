const OPENROUTER_FALLBACK_MODELS = [
  "openrouter/free",
  "google/gemma-4-31b-it:free",
  "google/gemma-4-26b-a4b-it:free",
  "meta-llama/llama-3.1-8b-instruct:free",
  "mistralai/mistral-7b-instruct:free",
];

const HF_FREE_MODELS = [
  "Qwen/Qwen2.5-7B-Instruct",
  "HuggingFaceH4/zephyr-7b-beta",
  "microsoft/Phi-3-mini-4k-instruct",
];

const FREE_MODE_PROVIDERS = new Set(["gemini", "openrouter", "aureon"]);
const ALLOWED_PROVIDERS = new Set([
  "gemini",
  "openrouter",
  "aureon",
  "ollama",
  "huggingface",
  "grok",
  "openai",
]);
const PROVIDER_MODEL_DEFAULTS = {
  gemini: "gemini-2.5-flash",
  openrouter: "openrouter/free",
  aureon: "aureon-brain",
  ollama: "kimi-k2.7-code",
  huggingface: HF_FREE_MODELS[0],
  grok: "grok-3-mini",
  openai: "gpt-4o-mini",
};
const PROVIDER_MODEL_ALLOWLISTS = new Map([
  ["gemini", new Set(["gemini-1.5-flash", "gemini-2.0-flash-exp", "gemini-2.5-flash"])],
  ["openrouter", new Set(OPENROUTER_FALLBACK_MODELS)],
  ["aureon", new Set([
    "aureon-brain",
    "aureon-queen",
    "aureon-council",
    "aureon-architect",
    "aureon-vault",
  ])],
  ["huggingface", new Set(HF_FREE_MODELS)],
  ["grok", new Set(["grok-2-latest", "grok-3-mini"])],
  ["openai", new Set(["gpt-4o-mini", "gpt-4o"])],
]);
const MAX_MESSAGE_BYTES = 8 * 1024;
const MAX_ROLE_PROMPT_BYTES = 2 * 1024;
const MAX_PROVIDER_TOKENS = 2048;
const MAX_JSON_BYTES = 64 * 1024;
const API_PREAUTH_RATE_LIMITER_BINDING = "API_PREAUTH_RATE_LIMITER";
const API_RATE_LIMITER_BINDING = "API_RATE_LIMITER";
const API_ROUTE_METHODS = new Map([
  ["/api/chat", new Set(["POST"])],
  ["/api/classroom/observe", new Set(["POST"])],
  ["/api/classroom/state", new Set(["GET"])],
  ["/api/classroom/replay", new Set(["GET"])],
  ["/api/aureon/status", new Set(["GET"])],
]);
const DISABLED_CLASSROOM_ROUTES = new Set([
  "/api/classroom/observe",
  "/api/classroom/state",
  "/api/classroom/replay",
]);
const PREFLIGHT_HEADERS = new Set(["authorization", "content-type"]);
const CLIENT_SECRET_FIELD_NAMES = new Set([
  "apikey",
  "authorization",
  "credentials",
  "providerapikey",
  "providerkey",
  "providersecret",
  "providertoken",
  "secret",
  "accesstoken",
]);
const API_SECURITY_HEADERS = {
  "Cache-Control": "no-store",
  "Content-Security-Policy": "default-src 'none'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'",
  "Referrer-Policy": "no-referrer",
  "X-Content-Type-Options": "nosniff",
  "X-Frame-Options": "DENY",
};

class ClientRequestError extends Error {
  constructor(status, code, message) {
    super(message);
    this.name = "ClientRequestError";
    this.status = status;
    this.code = code;
  }
}

function jsonResponse(status, payload) {
  return new Response(JSON.stringify(payload), {
    status,
    headers: {
      "Content-Type": "application/json; charset=utf-8",
      ...API_SECURITY_HEADERS,
    },
  });
}

function apiError(status, code, message) {
  return jsonResponse(status, { error: { code, message } });
}

function appendVary(headers, value) {
  const current = headers.get("Vary");
  const values = new Set((current || "").split(",").map((item) => item.trim()).filter(Boolean));
  values.add(value);
  headers.set("Vary", [...values].join(", "));
}

function secureApiResponse(response, corsOrigin = null) {
  const headers = new Headers(response.headers);
  for (const [name, value] of Object.entries(API_SECURITY_HEADERS)) headers.set(name, value);
  headers.delete("Access-Control-Allow-Origin");
  if (corsOrigin) {
    headers.set("Access-Control-Allow-Origin", corsOrigin);
    appendVary(headers, "Origin");
  }
  return new Response(response.body, {
    status: response.status,
    statusText: response.statusText,
    headers,
  });
}

function configuredAccessSecret(env) {
  const value = env?.AUREON_WORKER_ACCESS_SECRET;
  if (
    typeof value !== "string"
    || !value
    || value !== value.trim()
    || new TextEncoder().encode(value).byteLength < 32
  ) return null;
  return value;
}

function configuredCorsOrigins(env) {
  const raw = env?.AUREON_ALLOWED_ORIGINS;
  if (raw === undefined || raw === null || raw === "") return { valid: true, origins: new Set() };
  if (typeof raw !== "string") return { valid: false, origins: new Set() };

  const origins = new Set();
  for (const candidate of raw.split(",").map((item) => item.trim())) {
    if (!candidate || candidate === "*") return { valid: false, origins: new Set() };
    try {
      const parsed = new URL(candidate);
      const canonical = parsed.origin === candidate
        && parsed.protocol === "https:"
        && parsed.pathname === "/"
        && !parsed.search
        && !parsed.hash
        && !parsed.username
        && !parsed.password;
      if (!canonical) return { valid: false, origins: new Set() };
      origins.add(candidate);
    } catch {
      return { valid: false, origins: new Set() };
    }
  }
  return { valid: true, origins };
}

function corsDecision(request, env) {
  const configured = configuredCorsOrigins(env);
  if (!configured.valid) {
    return { origin: null, error: apiError(503, "cors_configuration_unavailable", "API CORS configuration is unavailable.") };
  }
  const origin = request.headers.get("Origin");
  if (!origin) return { origin: null, error: null };
  const requestOrigin = new URL(request.url).origin;
  if (origin === requestOrigin || configured.origins.has(origin)) return { origin, error: null };
  return { origin: null, error: apiError(403, "origin_denied", "Request origin is not allowed.") };
}

async function sha256Bytes(value) {
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(value));
  return new Uint8Array(digest);
}

function bytesToHex(value) {
  return [...value].map((byte) => byte.toString(16).padStart(2, "0")).join("");
}

async function hasExactBearer(request, secret) {
  const supplied = String(request.headers.get("Authorization") || "");
  const [suppliedDigest, expectedDigest] = await Promise.all([
    sha256Bytes(supplied),
    sha256Bytes(`Bearer ${secret}`),
  ]);
  let difference = 0;
  for (let index = 0; index < expectedDigest.length; index += 1) {
    difference |= suppliedDigest[index] ^ expectedDigest[index];
  }
  return difference === 0;
}

function stableClientAddress(request) {
  const value = String(request.headers.get("CF-Connecting-IP") || "").trim();
  if (value.length >= 3 && value.length <= 64 && /^[0-9a-f:.]+$/i.test(value)) return value;
  return "unattributed";
}

async function invokeRateLimiter(env, bindingName, key) {
  const limiter = env?.[bindingName];
  if (!limiter || typeof limiter.limit !== "function") {
    return apiError(503, "rate_limiter_unavailable", "API rate limiter is unavailable.");
  }

  let result;
  try {
    result = await limiter.limit({ key });
  } catch {
    return apiError(503, "rate_limiter_unavailable", "API rate limiter is unavailable.");
  }
  if (result?.success === false) {
    return apiError(429, "rate_limited", "Too many requests.");
  }
  if (result?.success !== true) {
    return apiError(503, "rate_limiter_unavailable", "API rate limiter is unavailable.");
  }
  return null;
}

async function enforcePreAuthRateLimit(request, env) {
  const clientDigest = bytesToHex(await sha256Bytes(stableClientAddress(request)));
  return invokeRateLimiter(env, API_PREAUTH_RATE_LIMITER_BINDING, `preauth:v1:${clientDigest}`);
}

async function enforceAuthenticatedRateLimit(request, env, secret, pathname) {
  const tokenDigest = bytesToHex(await sha256Bytes(secret));
  return invokeRateLimiter(
    env,
    API_RATE_LIMITER_BINDING,
    `authenticated:v1:${tokenDigest}:${request.method}:${pathname}`,
  );
}

function hasClientSuppliedSecret(value) {
  const pending = [value];
  while (pending.length) {
    const current = pending.pop();
    if (!current || typeof current !== "object") continue;
    if (Array.isArray(current)) {
      pending.push(...current);
      continue;
    }
    for (const [key, item] of Object.entries(current)) {
      const normalized = key.toLowerCase().replace(/[-_]/g, "");
      if (CLIENT_SECRET_FIELD_NAMES.has(normalized)) return true;
      pending.push(item);
    }
  }
  return false;
}

async function readJsonBody(request) {
  const mediaType = String(request.headers.get("Content-Type") || "")
    .split(";", 1)[0]
    .trim()
    .toLowerCase();
  if (mediaType !== "application/json") {
    throw new ClientRequestError(415, "json_content_type_required", "Content-Type must be application/json.");
  }

  const declaredLength = request.headers.get("Content-Length");
  if (declaredLength && /^\d+$/.test(declaredLength) && Number(declaredLength) > MAX_JSON_BYTES) {
    throw new ClientRequestError(413, "request_too_large", "JSON request body is too large.");
  }
  if (!request.body) throw new ClientRequestError(400, "invalid_json", "Request body must contain JSON.");

  const reader = request.body.getReader();
  const decoder = new TextDecoder("utf-8", { fatal: true });
  let bytes = 0;
  let text = "";
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      bytes += value.byteLength;
      if (bytes > MAX_JSON_BYTES) {
        try {
          await reader.cancel();
        } catch {
          // The size violation remains authoritative even if cancellation fails.
        }
        throw new ClientRequestError(413, "request_too_large", "JSON request body is too large.");
      }
      text += decoder.decode(value, { stream: true });
    }
    text += decoder.decode();
  } catch (error) {
    if (error instanceof ClientRequestError) throw error;
    throw new ClientRequestError(400, "invalid_json", "Request body must contain valid UTF-8 JSON.");
  } finally {
    reader.releaseLock();
  }

  let parsed;
  try {
    parsed = JSON.parse(text);
  } catch {
    throw new ClientRequestError(400, "invalid_json", "Request body must contain valid JSON.");
  }
  if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
    throw new ClientRequestError(400, "invalid_json_shape", "JSON request body must be an object.");
  }
  if (hasClientSuppliedSecret(parsed)) {
    throw new ClientRequestError(400, "client_secret_rejected", "Provider credentials must be configured as Worker secrets.");
  }
  return parsed;
}

async function parseJsonResponse(response) {
  const raw = await response.text();
  try {
    return raw ? JSON.parse(raw) : {};
  } catch {
    return { error: { message: raw || "Nieprawidłowa odpowiedź API." } };
  }
}

function commonMessages(parsed) {
  return [
    { role: "system", content: parsed.rolePrompt || "Jesteś pomocnym asystentem." },
    { role: "user", content: parsed.message || "" },
  ];
}

async function callOllamaCloud(parsed, env, fallbackFor = null) {
  const route = String(env.AUREON_EXTERNAL_LLM_FALLBACK || "ollama").toLowerCase();
  if (["none", "off", "disabled", "false", "0"].includes(route)) {
    throw new Error("Ollama fallback is disabled.");
  }
  const apiKey = env.OLLAMA_API_KEY || env.AUREON_OLLAMA_API_KEY || env.AUREON_LLM_API_KEY;
  if (!apiKey) throw new Error("OLLAMA_API_KEY is not configured.");
  const base = String(env.AUREON_LLM_BASE_URL || "https://ollama.com/v1").replace(/\/+$/, "");
  const endpoint = /\/chat\/completions$/i.test(base) ? base : `${base}/chat/completions`;
  const model = env.AUREON_LLM_MODEL || env.AUREON_OLLAMA_MODEL || "kimi-k2.7-code";
  const response = await fetch(endpoint, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${apiKey}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      model,
      messages: commonMessages(parsed),
      temperature: Number(parsed.temperature ?? 0.7),
      max_tokens: Number(parsed.max_tokens ?? 2000),
      reasoning_effort: env.AUREON_OLLAMA_REASONING_EFFORT || "none",
    }),
  });
  const data = await parseJsonResponse(response);
  if (!response.ok) throw new Error(data?.error?.message || `Ollama Cloud HTTP ${response.status}.`);
  const reply = data?.choices?.[0]?.message?.content;
  if (!reply) throw new Error("Ollama Cloud returned no visible response.");
  return { provider: "ollama", model, reply, fallbackFor };
}

function paidProvidersEnabled(env) {
  return env?.AUREON_ALLOW_PAID_PROVIDERS === "true";
}

function providerDefaultModel(provider, env) {
  if (provider === "ollama") {
    return String(env.AUREON_LLM_MODEL || env.AUREON_OLLAMA_MODEL || PROVIDER_MODEL_DEFAULTS.ollama);
  }
  return PROVIDER_MODEL_DEFAULTS[provider];
}

function providerModelAllowed(provider, model, env) {
  if (provider === "ollama") return model === providerDefaultModel(provider, env);
  return PROVIDER_MODEL_ALLOWLISTS.get(provider)?.has(model) === true;
}

function boundedText(value, field, maximumBytes, { fallback = "", required = false } = {}) {
  const resolved = value === undefined || value === null ? fallback : value;
  if (typeof resolved !== "string") {
    throw new ClientRequestError(400, "invalid_chat_request", `${field} must be a string.`);
  }
  if (required && !resolved.trim()) {
    throw new ClientRequestError(400, "invalid_chat_request", `${field} is required.`);
  }
  if (new TextEncoder().encode(resolved).byteLength > maximumBytes) {
    throw new ClientRequestError(400, "invalid_chat_request", `${field} exceeds its byte limit.`);
  }
  return resolved;
}

function boundedNumber(value, field, fallback, minimum, maximum, integer = false) {
  const resolved = value === undefined || value === null ? fallback : value;
  if (
    typeof resolved !== "number"
    || !Number.isFinite(resolved)
    || resolved < minimum
    || resolved > maximum
    || (integer && !Number.isInteger(resolved))
  ) {
    throw new ClientRequestError(400, "invalid_chat_request", `${field} is outside its allowed range.`);
  }
  return resolved;
}

function normalizeChatRequest(parsed, env) {
  const provider = typeof parsed.provider === "string"
    ? parsed.provider.trim().toLowerCase()
    : "gemini";
  if (!ALLOWED_PROVIDERS.has(provider)) {
    throw new ClientRequestError(400, "provider_not_allowed", "Requested provider is not allowed.");
  }

  const accessMode = typeof parsed.accessMode === "string"
    ? parsed.accessMode.trim().toLowerCase()
    : "free";
  if (!["free", "normal"].includes(accessMode)) {
    throw new ClientRequestError(400, "invalid_access_mode", "Access mode must be free or normal.");
  }
  if (accessMode === "normal" && !paidProvidersEnabled(env)) {
    throw new ClientRequestError(403, "paid_provider_disabled", "Paid provider access is disabled.");
  }
  if (accessMode === "free" && !FREE_MODE_PROVIDERS.has(provider)) {
    throw new ClientRequestError(403, "provider_not_free", "Requested provider is unavailable in free-only mode.");
  }

  const model = parsed.model === undefined || parsed.model === null || parsed.model === ""
    ? providerDefaultModel(provider, env)
    : boundedText(parsed.model, "model", 160);
  if (!providerModelAllowed(provider, model, env)) {
    throw new ClientRequestError(400, "model_not_allowed", "Requested model is not allowed.");
  }
  if (accessMode === "free" && provider === "openrouter" && model !== "openrouter/free" && !model.endsWith(":free")) {
    throw new ClientRequestError(403, "model_not_free", "Requested model is unavailable in free-only mode.");
  }

  return {
    ...parsed,
    provider,
    accessMode,
    model,
    message: boundedText(parsed.message, "message", MAX_MESSAGE_BYTES, { required: true }),
    rolePrompt: boundedText(
      parsed.rolePrompt,
      "rolePrompt",
      MAX_ROLE_PROMPT_BYTES,
      { fallback: "You are a helpful, careful assistant." },
    ),
    temperature: boundedNumber(parsed.temperature, "temperature", 0.7, 0, 2),
    max_tokens: boundedNumber(parsed.max_tokens, "max_tokens", 1200, 1, MAX_PROVIDER_TOKENS, true),
  };
}

function shouldRetryOpenRouter(message) {
  const normalized = String(message || "").toLowerCase();
  return (
    normalized.includes("at capacity") ||
    normalized.includes("capacity") ||
    normalized.includes("please try a different model") ||
    normalized.includes("rate limit") ||
    normalized.includes("temporarily unavailable") ||
    normalized.includes("over capacity")
  );
}

async function callOpenRouter(parsed, env) {
  const apiKey = env.OPENROUTER_API_KEY;
  if (!apiKey) throw new Error("Brak klucza OpenRouter API.");

  const requestedModel = parsed.model || "openrouter/free";
  const modelQueue = [
    requestedModel,
    ...OPENROUTER_FALLBACK_MODELS.filter((model) => model !== requestedModel),
  ];
  const tried = [];
  let lastError = "Błąd OpenRouter API.";

  for (const model of modelQueue) {
    tried.push(model);
    const response = await fetch("https://openrouter.ai/api/v1/chat/completions", {
      method: "POST",
      headers: {
        Authorization: `Bearer ${apiKey}`,
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost",
        "X-Title": "flAmeBornLLC LLM Academy",
      },
      body: JSON.stringify({
        model,
        messages: commonMessages(parsed),
        temperature: Number(parsed.temperature ?? 0.7),
        max_tokens: Number(parsed.max_tokens ?? 2000),
      }),
    });

    const data = await parseJsonResponse(response);
    if (!response.ok) {
      lastError = data?.error?.message || "Błąd OpenRouter API.";
      if (shouldRetryOpenRouter(lastError)) continue;
      throw new Error(lastError);
    }

    const reply = data?.choices?.[0]?.message?.content;
    if (!reply) {
      lastError = "Brak odpowiedzi modelu OpenRouter.";
      continue;
    }

    return {
      provider: "openrouter",
      model,
      reply,
      requestedModel,
      fallbackUsed: model !== requestedModel,
      triedModels: tried,
    };
  }

  throw new Error(`${lastError} Przetestowane modele: ${tried.join(", ")}`);
}

async function callGemini(parsed, env) {
  const apiKey = env.GEMINI_API_KEY || env.GOOGLE_API_KEY;
  if (!apiKey) throw new Error("Brak klucza GEMINI_API_KEY.");

  const model = String(parsed.model || "gemini-2.5-flash").replace(/^models\//, "");
  const response = await fetch(
    `https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent?key=${apiKey}`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        systemInstruction: {
          parts: [{ text: parsed.rolePrompt || "Jesteś pomocnym asystentem." }],
        },
        contents: [
          {
            role: "user",
            parts: [{ text: parsed.message || "" }],
          },
        ],
        generationConfig: {
          temperature: Number(parsed.temperature ?? 0.7),
          maxOutputTokens: Number(parsed.max_tokens ?? 2000),
        },
      }),
    },
  );

  const data = await parseJsonResponse(response);
  if (!response.ok) throw new Error(data?.error?.message || "Błąd Gemini API.");

  const parts = data?.candidates?.[0]?.content?.parts || [];
  const reply = parts.map((part) => part.text || "").join("").trim();
  if (!reply) throw new Error("Brak odpowiedzi modelu Gemini.");
  return { provider: "gemini", model, reply };
}

async function callOpenAI(parsed, env) {
  const apiKey = env.OPENAI_API_KEY;
  if (!apiKey) throw new Error("Brak klucza OPENAI_API_KEY.");

  const response = await fetch("https://api.openai.com/v1/chat/completions", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${apiKey}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      model: parsed.model || "gpt-4o-mini",
      messages: commonMessages(parsed),
      temperature: Number(parsed.temperature ?? 0.7),
      max_tokens: Number(parsed.max_tokens ?? 2000),
    }),
  });

  const data = await parseJsonResponse(response);
  if (!response.ok) throw new Error(data?.error?.message || "Błąd OpenAI API.");
  const reply = data?.choices?.[0]?.message?.content;
  if (!reply) throw new Error("Brak odpowiedzi modelu OpenAI.");
  return { provider: "openai", model: parsed.model, reply };
}

async function callHuggingFace(parsed, env) {
  const token = env.HF_TOKEN || env.HUGGINGFACE_API_KEY;
  if (!token) throw new Error("Brak klucza HF_TOKEN / HUGGINGFACE_API_KEY.");

  const model = parsed.model || HF_FREE_MODELS[0];
  if (!HF_FREE_MODELS.includes(model)) {
    throw new Error("Model Hugging Face poza listą free-only w tej aplikacji.");
  }

  const response = await fetch("https://router.huggingface.co/v1/chat/completions", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      model,
      messages: commonMessages(parsed),
      temperature: Number(parsed.temperature ?? 0.7),
      max_tokens: Number(parsed.max_tokens ?? 1200),
    }),
  });

  const data = await parseJsonResponse(response);
  if (!response.ok) throw new Error(data?.error?.message || "Błąd Hugging Face API.");
  const reply = data?.choices?.[0]?.message?.content;
  if (!reply) throw new Error("Brak odpowiedzi modelu Hugging Face.");
  return { provider: "huggingface", model, reply };
}

async function callGrok(parsed, env) {
  const allowPaid = String(env.XAI_ALLOW_PAID || "false").toLowerCase() === "true";
  const apiKey = env.XAI_API_KEY;
  if (!apiKey) throw new Error("Brak klucza XAI_API_KEY.");
  if (!allowPaid) {
    throw new Error(
      "Grok API: brak darmowych modeli API. Tryb free-only jest aktywny (XAI_ALLOW_PAID=false).",
    );
  }

  const response = await fetch("https://api.x.ai/v1/chat/completions", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${apiKey}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      model: parsed.model || "grok-3-mini",
      messages: commonMessages(parsed),
      temperature: Number(parsed.temperature ?? 0.7),
      max_tokens: Number(parsed.max_tokens ?? 2000),
    }),
  });

  const data = await parseJsonResponse(response);
  if (!response.ok) throw new Error(data?.error?.message || "Błąd Grok/xAI API.");
  const reply = data?.choices?.[0]?.message?.content;
  if (!reply) throw new Error("Brak odpowiedzi modelu Grok.");
  return { provider: "grok", model: parsed.model, reply };
}

function aureonArchitectureStatus(env = {}) {
  return {
    obsidianBridge: {
      mode: env.AUREON_API_BASE_URL ? "external-aureon" : "disabled-until-tenant-storage",
      note: "Cross-request memory is disabled until tenant-bound durable storage is configured.",
    },
    ollamaFallback: {
      mode: (env.OLLAMA_API_KEY || env.AUREON_OLLAMA_API_KEY || env.AUREON_LLM_API_KEY)
        ? "ollama-cloud-ready"
        : "waiting-for-worker-secret",
      expectedEndpoint: "Ollama Cloud OpenAI-compatible API",
    },
    queenLayer: {
      mode: env.AUREON_API_BASE_URL ? "remote-available" : "waiting-for-aureon-bridge",
      safeDefault: "observer/status only; no autonomous actions enabled",
    },
  };
}

function extractAureonReply(data) {
  if (!data || typeof data !== "object") return "";
  if (typeof data.reply === "string") return data.reply;
  if (typeof data.response === "string") return data.response;
  if (typeof data.text === "string") return data.text;
  if (typeof data.message === "string") return data.message;
  if (typeof data.message?.content === "string") return data.message.content;
  if (typeof data.utterance?.response?.text === "string") return data.utterance.response.text;
  if (typeof data.utterance?.statement?.text === "string") return data.utterance.statement.text;
  if (typeof data.statement?.text === "string") return data.statement.text;
  if (typeof data.result?.text === "string") return data.result.text;
  if (typeof data.result === "string") return data.result;
  return "";
}

async function callAureonBrain(parsed, env) {
  const model = parsed.model || "aureon-brain";
  const baseUrl = String(env.AUREON_API_BASE_URL || "").replace(/\/+$/, "");
  const chatPath = env.AUREON_CHAT_PATH || "/api/message";
  const apiKey = env.AUREON_API_KEY || "";
  const voice = aureonVoiceForModel(model);
  const userMessage = parsed.message || "";
  const includeConnectionFact = /connected|connection|bridge|status|połącz|polacz|połączenie|polaczenie/i.test(userMessage);
  const routedMessage = [
    "Context: this request is routed from flAmeBorn LLM Academy through the Aureon Phi Bridge.",
    includeConnectionFact
      ? "Connection fact: if asked whether Aureon is connected to flAmeBorn LLM Academy, the correct technical answer is yes."
      : "",
    `Human asks: ${userMessage}`,
    "Answer directly in natural language. No trading signals, no JSON, no status report unless asked.",
  ].filter(Boolean).join("\n");

  if (!baseUrl) {
    return {
      provider: "aureon",
      model,
      reply: [
        "Aureon Brain bridge is prepared but not connected to a live Aureon endpoint yet.",
        "Cloud mode is waiting for AUREON_API_BASE_URL.",
        "Use this provider after Gary exposes the Aureon bridge/vault server.",
      ].join(" "),
      bridgeConnected: false,
      architecture: aureonArchitectureStatus(env),
    };
  }

  const response = await fetch(`${baseUrl}${chatPath}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(apiKey ? { Authorization: `Bearer ${apiKey}` } : {}),
    },
    body: JSON.stringify({
      text: routedMessage,
      message: routedMessage,
      voice,
      fast: true,
      peer_id: "flameborn-academy",
      model,
      provider: "aureon",
      rolePrompt: parsed.rolePrompt || "You are Aureon Brain inside flAmeBornLLC LLM Academy.",
      context: {
        app: "flAmeBornLLC LLM Academy",
        mode: "aureon-vault-voice",
        voice,
        classroom: "observer-compatible",
      },
    }),
  });

  const data = await parseJsonResponse(response);
  if (!response.ok) throw new Error(data?.error?.message || data?.error || "Błąd Aureon Brain API.");
  const reply = extractAureonReply(data);
  if (!reply) throw new Error("Aureon Brain nie zwrócił tekstowej odpowiedzi.");
  return {
    provider: "aureon",
    model,
    reply,
    bridgeConnected: true,
    rawStatus: data.status || data.mode || null,
  };
}

function aureonVoiceForModel(model = "") {
  const normalized = String(model || "").toLowerCase();
  if (normalized.includes("council")) return "council";
  if (normalized.includes("architect")) return "architect";
  if (normalized.includes("lover")) return "lover";
  if (normalized.includes("miner")) return "miner";
  if (normalized.includes("scout")) return "scout";
  if (normalized.includes("vault")) return "vault";
  return "queen";
}

async function callProvider(provider, parsed, env) {
  try {
    if (provider === "gemini") return await callGemini(parsed, env);
    if (provider === "huggingface") return await callHuggingFace(parsed, env);
    if (provider === "grok") return await callGrok(parsed, env);
    if (provider === "openai") return await callOpenAI(parsed, env);
    if (provider === "aureon") return await callAureonBrain(parsed, env);
    if (provider === "ollama") return await callOllamaCloud(parsed, env, provider);
    return await callOpenRouter(parsed, env);
  } catch (primaryError) {
    if (provider === "ollama" || !paidProvidersEnabled(env)) throw primaryError;
    try {
      return await callOllamaCloud(parsed, env, provider);
    } catch (fallbackError) {
      throw new Error(`${primaryError.message} Ollama fallback: ${fallbackError.message}`);
    }
  }
}

async function handleChat(request, env) {
  let parsed;
  try {
    parsed = normalizeChatRequest(await readJsonBody(request), env);
  } catch (error) {
    if (error instanceof ClientRequestError) return apiError(error.status, error.code, error.message);
    return apiError(400, "invalid_json", "Request body must contain valid JSON.");
  }

  try {
    const provider = parsed.provider || "gemini";
    const result = await callProvider(provider, parsed, env);
    return jsonResponse(200, result);
  } catch {
    return apiError(502, "upstream_request_failed", "Upstream provider request failed.");
  }
}

function isApiPath(pathname) {
  return pathname === "/api" || pathname.startsWith("/api/");
}

async function handleApiPreflight(request, env, url) {
  const allowedMethods = API_ROUTE_METHODS.get(url.pathname);
  if (!allowedMethods) return secureApiResponse(apiError(404, "api_route_not_found", "API route not found."));
  if (!request.headers.get("Origin")) {
    return secureApiResponse(apiError(403, "origin_required", "CORS preflight requires an Origin header."));
  }
  const cors = corsDecision(request, env);
  if (cors.error) return secureApiResponse(cors.error);
  if (DISABLED_CLASSROOM_ROUTES.has(url.pathname)) {
    return secureApiResponse(
      apiError(503, "classroom_storage_unavailable", "Tenant-bound classroom storage is unavailable."),
      cors.origin,
    );
  }

  const requestedMethod = String(request.headers.get("Access-Control-Request-Method") || "").toUpperCase();
  if (!allowedMethods.has(requestedMethod)) {
    return secureApiResponse(apiError(405, "cors_method_denied", "CORS request method is not allowed."), cors.origin);
  }
  const requestedHeaders = String(request.headers.get("Access-Control-Request-Headers") || "")
    .split(",")
    .map((name) => name.trim().toLowerCase())
    .filter(Boolean);
  const requiredHeaders = requestedMethod === "POST"
    ? ["authorization", "content-type"]
    : ["authorization"];
  if (
    requestedHeaders.some((name) => !PREFLIGHT_HEADERS.has(name))
    || requiredHeaders.some((name) => !requestedHeaders.includes(name))
  ) {
    return secureApiResponse(apiError(403, "cors_headers_denied", "CORS request headers are not allowed."), cors.origin);
  }

  // Browser preflight requests do not carry credentials. The actual API request
  // below still requires an exact Bearer token and is rate limited after auth.
  const headers = new Headers({
    "Access-Control-Allow-Headers": "Authorization, Content-Type",
    "Access-Control-Allow-Methods": requestedMethod,
    "Access-Control-Max-Age": "0",
  });
  appendVary(headers, "Access-Control-Request-Method");
  appendVary(headers, "Access-Control-Request-Headers");
  return secureApiResponse(new Response(null, { status: 204, headers }), cors.origin);
}

async function handleAuthenticatedApi(request, env, url, secret) {
  const cors = corsDecision(request, env);
  if (cors.error) return secureApiResponse(cors.error);
  if (!(await hasExactBearer(request, secret))) {
    return secureApiResponse(
      apiError(401, "authentication_required", "A valid Bearer token is required."),
      cors.origin,
    );
  }

  const rateLimitError = await enforceAuthenticatedRateLimit(request, env, secret, url.pathname);
  if (rateLimitError) return secureApiResponse(rateLimitError, cors.origin);

  const allowedMethods = API_ROUTE_METHODS.get(url.pathname);
  if (!allowedMethods) {
    return secureApiResponse(apiError(404, "api_route_not_found", "API route not found."), cors.origin);
  }
  if (!allowedMethods.has(request.method)) {
    const response = apiError(405, "api_method_not_allowed", "Method not allowed.");
    response.headers.set("Allow", [...allowedMethods].join(", "));
    return secureApiResponse(response, cors.origin);
  }
  if (DISABLED_CLASSROOM_ROUTES.has(url.pathname)) {
    return secureApiResponse(
      apiError(503, "classroom_storage_unavailable", "Tenant-bound classroom storage is unavailable."),
      cors.origin,
    );
  }

  let response;
  if (request.method === "POST" && url.pathname === "/api/chat") {
    response = await handleChat(request, env);
  } else if (request.method === "GET" && url.pathname === "/api/aureon/status") {
    response = jsonResponse(200, {
      provider: "aureon",
      paidProvidersEnabled: paidProvidersEnabled(env),
      configured: Boolean(env.AUREON_API_BASE_URL),
      baseUrlConfigured: Boolean(env.AUREON_API_BASE_URL),
      chatPath: env.AUREON_CHAT_PATH || "/api/message",
      architecture: aureonArchitectureStatus(env),
    });
  } else {
    response = apiError(404, "api_route_not_found", "API route not found.");
  }
  return secureApiResponse(response, cors.origin);
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    if (isApiPath(url.pathname)) {
      const secret = configuredAccessSecret(env);
      if (!secret) {
        return secureApiResponse(apiError(503, "access_secret_unavailable", "API access control is unavailable."));
      }
      const preAuthRateLimitError = await enforcePreAuthRateLimit(request, env);
      if (preAuthRateLimitError) return secureApiResponse(preAuthRateLimitError);
      if (request.method === "OPTIONS") return handleApiPreflight(request, env, url);
      return handleAuthenticatedApi(request, env, url, secret);
    }

    if (request.method === "GET" || request.method === "HEAD") {
      if (env.ASSETS) return env.ASSETS.fetch(request);
      return new Response("Assets binding is missing.", { status: 500 });
    }

    return new Response("Method not allowed", { status: 405 });
  },
};

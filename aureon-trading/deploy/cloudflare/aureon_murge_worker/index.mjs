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
const OBSERVATION_DEPTH_LIMITS = {
  shallow: 900,
  standard: 1800,
  deep: 3200,
};

let classroomMemory = {
  events: [],
  reflections: [],
  summaries: [],
  patterns: [],
  inconsistencies: [],
  workflows: [],
  analytics: {
    mirroredEvents: 0,
    observerRuns: 0,
    estimatedTokens: 0,
    lastUpdated: null,
  },
};

const CORS_HEADERS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET,HEAD,POST,OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type, Authorization",
};

function jsonResponse(status, payload) {
  return new Response(JSON.stringify(payload), {
    status,
    headers: {
      "Content-Type": "application/json; charset=utf-8",
      ...CORS_HEADERS,
    },
  });
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

function enforceAccessMode(provider, parsed) {
  const mode = String(parsed.accessMode || "free").toLowerCase();
  if (mode !== "free") return;

  if (!FREE_MODE_PROVIDERS.has(provider)) {
    throw new Error(
      `Tryb FREE blokuje providera ${provider}. Przelacz na NORMAL, jesli chcesz uzyc tego providera.`,
    );
  }

  const model = String(parsed.model || "");
  if (provider === "gemini" && model.toLowerCase().includes("pro")) {
    throw new Error("Tryb FREE blokuje modele Gemini Pro. Uzyj Gemini Flash.");
  }
  if (provider === "openrouter" && model && model !== "openrouter/free" && !model.endsWith(":free")) {
    throw new Error("Tryb FREE blokuje platne modele OpenRouter. Uzyj modelu z koncowka :free.");
  }
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
  const apiKey = env.OPENROUTER_API_KEY || parsed.apiKey;
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
  const apiKey = env.GEMINI_API_KEY || env.GOOGLE_API_KEY || parsed.apiKey;
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
  const apiKey = env.OPENAI_API_KEY || parsed.apiKey;
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
  const token = env.HF_TOKEN || env.HUGGINGFACE_API_KEY || parsed.apiKey;
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
  const apiKey = env.XAI_API_KEY || parsed.apiKey;
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
      mode: env.AUREON_API_BASE_URL ? "external-aureon" : "memory-only-worker",
      note: "Cloudflare Workers cannot write to a local Obsidian vault without a remote Aureon bridge.",
    },
    ollamaFallback: {
      mode: "external-aureon-managed",
      expectedEndpoint: "Aureon OpenMultiAgent / Ollama fallback behind Gary bridge",
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
  const apiKey = env.AUREON_API_KEY || parsed.apiKey || "";
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
  enforceAccessMode(provider, parsed);

  if (provider === "gemini") return callGemini(parsed, env);
  if (provider === "huggingface") return callHuggingFace(parsed, env);
  if (provider === "grok") return callGrok(parsed, env);
  if (provider === "openai") return callOpenAI(parsed, env);
  if (provider === "aureon") return callAureonBrain(parsed, env);
  return callOpenRouter(parsed, env);
}

async function handleChat(request, env) {
  let parsed;
  try {
    parsed = await request.json();
  } catch {
    return jsonResponse(400, { error: { message: "Nieprawidłowy JSON." } });
  }

  try {
    const provider = parsed.provider || "gemini";
    const result = await callProvider(provider, parsed, env);
    return jsonResponse(200, result);
  } catch (error) {
    return jsonResponse(500, { error: { message: `Błąd serwera: ${error.message}` } });
  }
}

async function handleClassroomObserve(request) {
  let event;
  try {
    event = await request.json();
  } catch {
    return jsonResponse(400, { error: { message: "Nieprawidłowy JSON." } });
  }

  try {
    return jsonResponse(200, processClassroomEvent(event));
  } catch (error) {
    return jsonResponse(500, { error: { message: `Błąd observera: ${error.message}` } });
  }
}

function processClassroomEvent(event) {
  const safeEvent = normalizeClassroomEvent(event);
  const observers = safeEvent.observers
    .filter((observer) => observer.enabled !== false)
    .map((observer) => runObserver(observer, safeEvent));
  const memory = buildObservationMemory(safeEvent);
  const tokenCost = estimateTokens(`${safeEvent.conversation.user} ${safeEvent.conversation.assistant}`);

  classroomMemory.events.push({
    id: safeEvent.id,
    sessionId: safeEvent.sessionId,
    createdAt: safeEvent.createdAt,
    provider: safeEvent.conversation.provider,
    model: safeEvent.conversation.model,
    depth: safeEvent.depth,
  });
  classroomMemory.reflections.push(...observers.map((observer) => ({
    observerId: observer.id,
    role: observer.role,
    reflection: observer.latestReflection,
    createdAt: observer.lastRunAt,
  })));
  classroomMemory.summaries.push(...memory.summaries);
  classroomMemory.patterns.push(...memory.patterns);
  classroomMemory.inconsistencies.push(...memory.inconsistencies);
  classroomMemory.workflows.push(...memory.workflows);
  classroomMemory.events = classroomMemory.events.slice(-200);
  classroomMemory.reflections = classroomMemory.reflections.slice(-200);
  classroomMemory.summaries = classroomMemory.summaries.slice(-200);
  classroomMemory.patterns = classroomMemory.patterns.slice(-200);
  classroomMemory.inconsistencies = classroomMemory.inconsistencies.slice(-200);
  classroomMemory.workflows = classroomMemory.workflows.slice(-200);
  classroomMemory.analytics = {
    mirroredEvents: classroomMemory.analytics.mirroredEvents + 1,
    observerRuns: classroomMemory.analytics.observerRuns + observers.length,
    estimatedTokens: classroomMemory.analytics.estimatedTokens + tokenCost,
    lastUpdated: new Date().toISOString(),
  };

  return {
    eventId: safeEvent.id,
    observers,
    memory,
    analytics: {
      estimatedTokens: tokenCost,
      mirroredEvents: classroomMemory.analytics.mirroredEvents,
      observerRuns: classroomMemory.analytics.observerRuns,
      lastUpdated: classroomMemory.analytics.lastUpdated,
    },
  };
}

function normalizeClassroomEvent(event) {
  const depth = ["shallow", "standard", "deep"].includes(event.depth) ? event.depth : "standard";
  const limit = OBSERVATION_DEPTH_LIMITS[depth];
  const conversation = event.conversation || {};

  return {
    id: String(event.id || `evt-${Date.now()}`),
    sessionId: String(event.sessionId || "default-session"),
    createdAt: event.createdAt || new Date().toISOString(),
    depth,
    observers: Array.isArray(event.observers) ? event.observers.slice(0, 8) : [],
    conversation: {
      user: truncateText(conversation.user || "", Math.floor(limit * 0.45)),
      assistant: truncateText(conversation.assistant || "", Math.floor(limit * 0.55)),
      provider: String(conversation.provider || "unknown"),
      model: String(conversation.model || "unknown"),
      accessMode: String(conversation.accessMode || "free"),
    },
  };
}

function runObserver(observer, event) {
  const text = `${event.conversation.user}\n${event.conversation.assistant}`;
  const memory = buildObservationMemory(event);
  const preset = observer.preset || "memory";
  let reflection = "Context observed.";

  if (preset === "gemma") {
    reflection = [
      memory.summaries[0],
      memory.patterns[0] ? `Pattern: ${memory.patterns[0]}` : null,
      memory.workflows[0] ? `Workflow: ${memory.workflows[0]}` : null,
    ].filter(Boolean).join(" ");
  }
  if (preset === "aureon") {
    reflection = [
      "Aureon Queen observer mapped the turn into vault-compatible memory.",
      memory.workflows[0] ? `Workflow: ${memory.workflows[0]}` : null,
      memory.patterns[0] ? `Pattern: ${memory.patterns[0]}` : null,
    ].filter(Boolean).join(" ");
  }
  if (preset === "logic") reflection = memory.inconsistencies[0] || "No contradiction detected; keep monitoring assumptions.";
  if (preset === "code") reflection = memory.patterns[0] || "No new implementation pattern detected in this turn.";
  if (preset === "workflow") reflection = memory.workflows[0] || "Workflow continuity preserved; no new action chain found.";
  if (preset === "memory") reflection = memory.summaries[0] || "Session context compacted.";

  return {
    id: observer.id,
    role: observer.role,
    model: observer.model || "local-heuristic",
    state: "idle",
    tokenUsage: Number(observer.tokenUsage || 0) + estimateTokens(text),
    latestReflection: reflection,
    memoryItems: Number(observer.memoryItems || 0) + 1,
    lastRunAt: new Date().toISOString(),
  };
}

function buildObservationMemory(event) {
  const text = `${event.conversation.user}\n${event.conversation.assistant}`;
  const lower = text.toLowerCase();
  return {
    summaries: [truncateText(text.replace(/\s+/g, " "), 240)].filter(Boolean),
    patterns: [
      includesAny(lower, ["api", "token", "secret"]) ? "Provider credential and secret-management workflow detected." : null,
      includesAny(lower, ["deploy", "wrangler", "worker", "cloudflare"]) ? "Cloud deployment workflow detected." : null,
      includesAny(lower, ["script", "server.mjs", "index.mjs", "endpoint"]) ? "Application integration pattern detected." : null,
      includesAny(lower, ["aureon", "queen", "obsidian", "ollama", "vault"]) ? "Aureon brain/vault integration pattern detected." : null,
    ].filter(Boolean),
    inconsistencies: [
      includesAny(lower, ["404", "nie dziala", "does not work"]) ? "A route or external dashboard path failed and needs alternate verification." : null,
      includesAny(lower, ["quota", "limit", "billing"]) ? "Provider limit or billing condition may affect reproducibility." : null,
    ].filter(Boolean),
    workflows: [
      includesAny(lower, ["cloudflare", "workers.dev"]) ? "Cloudflare Workers publication path is active." : null,
      includesAny(lower, ["gemini", "openrouter", "huggingface", "grok", "openai"]) ? "Multi-provider model orchestration path is active." : null,
      includesAny(lower, ["aureon", "queen", "obsidian", "ollama", "vault"]) ? "Aureon Brain integration path is active: vault memory, Queen observer, Ollama fallback." : null,
      includesAny(lower, ["test", "sprawdz", "verify"]) ? "Verification-first workflow is active." : null,
    ].filter(Boolean),
  };
}

function includesAny(text, needles) {
  return needles.some((needle) => text.includes(needle));
}

function estimateTokens(text) {
  return Math.ceil(String(text || "").length / 4);
}

function truncateText(text, maxLength) {
  const value = String(text || "").trim();
  return value.length > maxLength ? `${value.slice(0, maxLength - 1)}…` : value;
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    if (request.method === "OPTIONS" && url.pathname.startsWith("/api/")) {
      return new Response(null, { headers: CORS_HEADERS });
    }

    if (request.method === "POST" && url.pathname === "/api/chat") {
      return handleChat(request, env);
    }

    if (request.method === "POST" && url.pathname === "/api/classroom/observe") {
      return handleClassroomObserve(request);
    }

    if (request.method === "GET" && url.pathname === "/api/classroom/state") {
      return jsonResponse(200, {
        memory: classroomMemory,
        analytics: classroomMemory.analytics,
      });
    }

    if (request.method === "GET" && url.pathname === "/api/classroom/replay") {
      return jsonResponse(200, {
        events: classroomMemory.events.slice(-100),
        reflections: classroomMemory.reflections.slice(-100),
        memory: {
          summaries: classroomMemory.summaries.slice(-50),
          patterns: classroomMemory.patterns.slice(-50),
          inconsistencies: classroomMemory.inconsistencies.slice(-50),
          workflows: classroomMemory.workflows.slice(-50),
        },
      });
    }

    if (request.method === "GET" && url.pathname === "/api/aureon/status") {
      return jsonResponse(200, {
        provider: "aureon",
        configured: Boolean(env.AUREON_API_BASE_URL),
        baseUrlConfigured: Boolean(env.AUREON_API_BASE_URL),
        chatPath: env.AUREON_CHAT_PATH || "/api/message",
        architecture: aureonArchitectureStatus(env),
      });
    }

    if (request.method === "GET" || request.method === "HEAD") {
      if (env.ASSETS) return env.ASSETS.fetch(request);
      return new Response("Assets binding is missing.", { status: 500 });
    }

    return new Response("Method not allowed", { status: 405 });
  },
};

import { createHash } from "node:crypto";

const SOCIAL_API_BASE = "https://www.moltbook.com/api/v1";
const REDACTED = "[REDACTED]";

const readAnnotations = Object.freeze({
  readOnlyHint: true,
  destructiveHint: false,
  idempotentHint: true,
  openWorldHint: true,
});

const writeAnnotations = Object.freeze({
  readOnlyHint: false,
  destructiveHint: true,
  idempotentHint: true,
  openWorldHint: true,
});

export const TOOL_DEFINITIONS = Object.freeze([
  {
    name: "registry_status",
    description: "Check a registry identity by agent ID or Base wallet address.",
    inputSchema: {
      type: "object",
      properties: {
        agent_id: { oneOf: [{ type: "string" }, { type: "integer", minimum: 0 }] },
        address: { type: "string" },
      },
      oneOf: [{ required: ["agent_id"] }, { required: ["address"] }],
      additionalProperties: false,
    },
    annotations: readAnnotations,
  },
  {
    name: "registry_lookup",
    description: "Fetch registry metadata for an agent ID.",
    inputSchema: {
      type: "object",
      properties: {
        agent_id: { oneOf: [{ type: "string" }, { type: "integer", minimum: 0 }] },
      },
      required: ["agent_id"],
      additionalProperties: false,
    },
    annotations: readAnnotations,
  },
  {
    name: "registry_register",
    description: "Register an agent through an injected signer after confirmation and idempotency checks.",
    inputSchema: {
      type: "object",
      properties: {
        endpoints: { type: "string", minLength: 2, maxLength: 16384 },
        uri: { type: "string", maxLength: 2048 },
        agent_wallet: { type: "string" },
        confirmed: { type: "boolean" },
        idempotency_key: { type: "string", minLength: 16, maxLength: 128 },
      },
      required: ["endpoints", "confirmed", "idempotency_key"],
      additionalProperties: false,
    },
    annotations: writeAnnotations,
  },
  {
    name: "registry_rate",
    description: "Rate an agent through an injected signer after confirmation and idempotency checks.",
    inputSchema: {
      type: "object",
      properties: {
        agent_id: { oneOf: [{ type: "string" }, { type: "integer", minimum: 0 }] },
        score: { type: "integer", minimum: 0, maximum: 100 },
        confirmed: { type: "boolean" },
        idempotency_key: { type: "string", minLength: 16, maxLength: 128 },
      },
      required: ["agent_id", "score", "confirmed", "idempotency_key"],
      additionalProperties: false,
    },
    annotations: writeAnnotations,
  },
  {
    name: "moltbook_hot",
    description: "List hot Moltbook posts through an injected HTTP transport.",
    inputSchema: {
      type: "object",
      properties: { limit: { type: "integer", minimum: 1, maximum: 100 } },
      additionalProperties: false,
    },
    annotations: readAnnotations,
  },
  {
    name: "moltbook_new",
    description: "List new Moltbook posts through an injected HTTP transport.",
    inputSchema: {
      type: "object",
      properties: { limit: { type: "integer", minimum: 1, maximum: 100 } },
      additionalProperties: false,
    },
    annotations: readAnnotations,
  },
  {
    name: "moltbook_get_post",
    description: "Retrieve one Moltbook post through an injected HTTP transport.",
    inputSchema: {
      type: "object",
      properties: { post_id: { type: "string", minLength: 1, maxLength: 128 } },
      required: ["post_id"],
      additionalProperties: false,
    },
    annotations: readAnnotations,
  },
  {
    name: "moltbook_reply",
    description: "Reply to a Moltbook post after confirmation and idempotency checks.",
    inputSchema: {
      type: "object",
      properties: {
        post_id: { type: "string", minLength: 1, maxLength: 128 },
        content: { type: "string", minLength: 1, maxLength: 5000 },
        confirmed: { type: "boolean" },
        idempotency_key: { type: "string", minLength: 16, maxLength: 128 },
      },
      required: ["post_id", "content", "confirmed", "idempotency_key"],
      additionalProperties: false,
    },
    annotations: writeAnnotations,
  },
  {
    name: "moltbook_create",
    description: "Create a Moltbook post after confirmation and idempotency checks.",
    inputSchema: {
      type: "object",
      properties: {
        title: { type: "string", minLength: 1, maxLength: 300 },
        content: { type: "string", minLength: 1, maxLength: 10000 },
        confirmed: { type: "boolean" },
        idempotency_key: { type: "string", minLength: 16, maxLength: 128 },
      },
      required: ["title", "content", "confirmed", "idempotency_key"],
      additionalProperties: false,
    },
    annotations: writeAnnotations,
  },
]);

class ToolError extends Error {
  constructor(code, message, details = undefined, redactionValues = []) {
    super(message);
    this.name = "ToolError";
    this.code = code;
    this.details = details;
    Object.defineProperty(this, "redactionValues", {
      value: redactionValues,
      enumerable: false,
    });
  }
}

function isPlainObject(value) {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function requireObject(value) {
  if (!isPlainObject(value)) {
    throw new ToolError("invalid_arguments", "Arguments must be a JSON object.");
  }
  return value;
}

function rejectUnknownKeys(value, allowed) {
  const unknown = Object.keys(value).filter((key) => !allowed.has(key));
  if (unknown.length > 0) {
    throw new ToolError("invalid_arguments", "Unexpected argument fields.", { fields: unknown });
  }
}

function validateAgentId(value) {
  if (Number.isSafeInteger(value) && value >= 0) return String(value);
  if (typeof value === "string" && /^(0|[1-9][0-9]*)$/.test(value)) return value;
  throw new ToolError("invalid_agent_id", "agent_id must be a non-negative decimal integer.");
}

function validateAddress(value, field = "address") {
  if (typeof value === "string" && /^0x[0-9a-fA-F]{40}$/.test(value)) return value;
  throw new ToolError("invalid_address", `${field} must be a 20-byte hexadecimal address.`);
}

function validateScore(value) {
  if (Number.isInteger(value) && value >= 0 && value <= 100) return value;
  throw new ToolError("invalid_score", "score must be an integer from 0 through 100.");
}

function validateEndpoints(value) {
  if (typeof value !== "string" || value.length < 2 || value.length > 16384) {
    throw new ToolError("invalid_endpoints", "endpoints must be a bounded JSON object string.");
  }
  let parsed;
  try {
    parsed = JSON.parse(value);
  } catch {
    throw new ToolError("invalid_endpoints", "endpoints must contain valid JSON.");
  }
  if (!isPlainObject(parsed)) {
    throw new ToolError("invalid_endpoints", "endpoints JSON must be an object.");
  }
  return parsed;
}

function validateHttpsUri(value) {
  if (value === undefined) return undefined;
  if (typeof value !== "string" || value.length > 2048) {
    throw new ToolError("invalid_uri", "uri must be a bounded HTTPS URL.");
  }
  let parsed;
  try {
    parsed = new URL(value);
  } catch {
    throw new ToolError("invalid_uri", "uri must be a valid HTTPS URL.");
  }
  if (parsed.protocol !== "https:" || parsed.username || parsed.password) {
    throw new ToolError("invalid_uri", "uri must be an HTTPS URL without embedded credentials.");
  }
  return parsed.toString();
}

function validateSocialId(value, field) {
  if (typeof value === "string" && /^[A-Za-z0-9_-]{1,128}$/.test(value)) return value;
  throw new ToolError("invalid_identifier", `${field} contains unsupported characters.`);
}

function validateLimit(value) {
  if (value === undefined) return 20;
  if (Number.isInteger(value) && value >= 1 && value <= 100) return value;
  throw new ToolError("invalid_limit", "limit must be an integer from 1 through 100.");
}

function validateText(value, field, maximum) {
  if (typeof value !== "string" || value.trim().length === 0 || value.length > maximum) {
    throw new ToolError("invalid_text", `${field} must contain 1 through ${maximum} characters.`);
  }
  return value;
}

function validateMutationGate(args) {
  if (args.confirmed !== true) {
    throw new ToolError("confirmation_required", "This mutation requires confirmed: true.");
  }
  if (
    typeof args.idempotency_key !== "string" ||
    !/^[A-Za-z0-9][A-Za-z0-9._:-]{15,127}$/.test(args.idempotency_key)
  ) {
    throw new ToolError(
      "idempotency_required",
      "A unique 16-128 character idempotency_key is required.",
    );
  }
  return args.idempotency_key;
}

function stableStringify(value) {
  if (Array.isArray(value)) return `[${value.map(stableStringify).join(",")}]`;
  if (isPlainObject(value)) {
    return `{${Object.keys(value)
      .sort()
      .map((key) => `${JSON.stringify(key)}:${stableStringify(value[key])}`)
      .join(",")}}`;
  }
  return JSON.stringify(value);
}

function fingerprint(value) {
  return createHash("sha256").update(stableStringify(value)).digest("hex");
}

function redactString(value, secretValues) {
  let output = value
    .replace(/Bearer\s+[^\s,;]+/gi, `Bearer ${REDACTED}`)
    .replace(/0x[0-9a-fA-F]{64}\b/g, REDACTED);
  for (const secret of secretValues) {
    if (typeof secret !== "string" || secret.length === 0) continue;
    output = output.split(secret).join(REDACTED);
  }
  return output;
}

function redact(value, secretValues = [], seen = new WeakSet()) {
  if (typeof value === "string") return redactString(value, secretValues);
  if (typeof value === "bigint") return value.toString();
  if (value === null || typeof value !== "object") return value;
  if (seen.has(value)) return "[CIRCULAR]";
  seen.add(value);
  if (Array.isArray(value)) return value.map((entry) => redact(entry, secretValues, seen));
  const output = {};
  for (const [key, entry] of Object.entries(value)) {
    if (/^(authorization|api[_-]?key|token|private[_-]?key|password|secret)$/i.test(key)) {
      output[key] = REDACTED;
    } else {
      output[key] = redact(entry, secretValues, seen);
    }
  }
  return output;
}

function success(
  tool,
  data,
  { receipt, mutation = false, economicMutation = false, status, secretValues = [] } = {},
) {
  const result = {
    ok: true,
    tool,
    data: redact(data, secretValues),
    mutation,
    mutation_status: mutation ? (status ?? "confirmed") : "not_applicable",
    economic_mutation: economicMutation,
    economic_mutation_status: economicMutation ? (status ?? "confirmed") : "not_applicable",
  };
  if (receipt !== undefined) result.receipt = redact(receipt, secretValues);
  return result;
}

function failure(
  tool,
  error,
  { mutation = false, economicMutation = false, status, secretValues = [] } = {},
) {
  const code = error instanceof ToolError ? error.code : "internal_error";
  const message = error instanceof Error ? error.message : "Unexpected tool failure.";
  const values = [...secretValues, ...(error?.redactionValues ?? [])];
  const payload = {
    code,
    message: redactString(message, values),
  };
  if (error instanceof ToolError && error.details !== undefined) {
    payload.details = redact(error.details, values);
  }
  return {
    ok: false,
    tool,
    error: payload,
    mutation,
    mutation_status: mutation ? (status ?? "not_started") : "not_applicable",
    economic_mutation: economicMutation,
    economic_mutation_status: economicMutation ? (status ?? "not_started") : "not_applicable",
  };
}

export function createMemoryIdempotencyStore() {
  const entries = new Map();
  return {
    async get(key) {
      return entries.get(key);
    },
    async set(key, value) {
      entries.set(key, value);
    },
  };
}

function unavailable(label) {
  return async () => {
    throw new ToolError("transport_unavailable", `${label} is not configured.`);
  };
}

function defaultCredentialLoader(env) {
  return async () => {
    const token = typeof env.MOLTBOOK_API_KEY === "string" ? env.MOLTBOOK_API_KEY.trim() : "";
    if (!token) throw new ToolError("credential_unavailable", "Moltbook credentials are not configured.");
    return { token };
  };
}

async function defaultHttpTransport({ method, path, query, body, credential }) {
  const url = new URL(`${SOCIAL_API_BASE}${path}`);
  for (const [key, value] of Object.entries(query ?? {})) url.searchParams.set(key, String(value));
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 10000);
  try {
    const response = await fetch(url, {
      method,
      headers: {
        Accept: "application/json",
        Authorization: `Bearer ${credential.token}`,
        ...(body === undefined ? {} : { "Content-Type": "application/json" }),
      },
      body,
      signal: controller.signal,
    });
    const text = await response.text();
    let parsed = text;
    if (text.length > 0) {
      try {
        parsed = JSON.parse(text);
      } catch {
        parsed = { message: "Provider returned a non-JSON response." };
      }
    }
    return { ok: response.ok, status: response.status, body: parsed };
  } finally {
    clearTimeout(timeout);
  }
}

function normalizeTransportError(error, fallbackCode, context, secretValues = []) {
  if (error instanceof ToolError) {
    return new ToolError(
      error.code,
      error.message,
      error.details,
      [...secretValues, ...(error.redactionValues ?? [])],
    );
  }
  const message = error instanceof Error ? error.message : "Unknown transport failure.";
  return new ToolError(fallbackCode, `${context}: ${message}`, undefined, secretValues);
}

async function loadRegistryProvider(factory) {
  let provider;
  try {
    provider = await factory();
  } catch (error) {
    throw normalizeTransportError(error, "provider_error", "Registry provider failed");
  }
  if (!isPlainObject(provider)) {
    throw new ToolError("transport_unavailable", "Registry provider is unavailable.");
  }
  return provider;
}

async function loadRegistrySigner(factory) {
  let signer;
  try {
    signer = await factory();
  } catch (error) {
    throw normalizeTransportError(error, "provider_error", "Registry signer failed");
  }
  if (!isPlainObject(signer)) {
    throw new ToolError("transport_unavailable", "Registry signer is unavailable.");
  }
  return signer;
}

async function loadCredential(loader) {
  let credential;
  try {
    credential = await loader();
  } catch (error) {
    throw normalizeTransportError(error, "credential_error", "Credential loading failed");
  }
  const token =
    typeof credential === "string"
      ? credential
      : isPlainObject(credential) && typeof credential.token === "string"
        ? credential.token
        : "";
  if (token.length < 1 || token.length > 4096) {
    throw new ToolError(
      "credential_unavailable",
      "Moltbook credentials are missing or invalid.",
      undefined,
      token ? [token] : [],
    );
  }
  return { token };
}

function normalizeHttpResponse(response, secretValues = [], requireObjectBody = false) {
  if (!isPlainObject(response) || !Number.isInteger(response.status)) {
    throw new ToolError(
      "provider_error",
      "Moltbook transport returned an invalid response envelope.",
      undefined,
      secretValues,
    );
  }
  const ok = typeof response.ok === "boolean" ? response.ok : response.status >= 200 && response.status < 300;
  let body = response.body;
  if (typeof body === "string") {
    try {
      body = JSON.parse(body);
    } catch {
      throw new ToolError(
        "provider_error",
        "Moltbook provider returned invalid JSON.",
        { status: response.status },
        secretValues,
      );
    }
  }
  if (!ok) {
    throw new ToolError(
      "provider_error",
      "Moltbook provider returned an error.",
      { status: response.status, response: body },
      secretValues,
    );
  }
  if (requireObjectBody && !isPlainObject(body)) {
    throw new ToolError(
      "provider_error",
      "Moltbook mutation did not return a structured receipt.",
      { status: response.status },
      secretValues,
    );
  }
  return { status: response.status, body };
}

async function beginIdempotent(tool, args, payload, store) {
  const key = validateMutationGate(args);
  const digest = fingerprint(payload);
  const scopedKey = `${tool}:${key}`;
  let existing;
  try {
    existing = await store.get(scopedKey);
  } catch (error) {
    throw normalizeTransportError(error, "idempotency_error", "Idempotency lookup failed");
  }
  if (existing !== undefined) {
    if (!isPlainObject(existing) || existing.fingerprint !== digest) {
      throw new ToolError(
        "idempotency_conflict",
        "The idempotency_key was already used with a different payload.",
      );
    }
    return { key, digest, scopedKey, existing };
  }
  return { key, digest, scopedKey, existing: undefined };
}

function replayMutation(tool, key, existing, economicMutation) {
  return success(tool, existing.data, {
    mutation: true,
    economicMutation,
    status: "confirmed",
    receipt: {
      idempotency_key: key,
      replayed: true,
      provider: existing.provider,
    },
  });
}

async function completeMutation({
  tool,
  key,
  digest,
  scopedKey,
  data,
  providerReceipt,
  store,
  secretValues = [],
  economicMutation = true,
}) {
  const safeData = redact(data, secretValues);
  const safeProvider = redact(providerReceipt, secretValues);
  try {
    await store.set(scopedKey, {
      fingerprint: digest,
      data: safeData,
      provider: safeProvider,
    });
  } catch (error) {
    throw normalizeTransportError(
      error,
      "idempotency_error",
      "Mutation completed but idempotency persistence failed",
      secretValues,
    );
  }
  return success(tool, safeData, {
    mutation: true,
    economicMutation,
    status: "confirmed",
    receipt: {
      idempotency_key: key,
      replayed: false,
      provider: safeProvider,
    },
    secretValues,
  });
}

function registryStatusArguments(raw) {
  const args = requireObject(raw);
  rejectUnknownKeys(args, new Set(["agent_id", "address"]));
  const hasAgent = Object.hasOwn(args, "agent_id");
  const hasAddress = Object.hasOwn(args, "address");
  if (hasAgent === hasAddress) {
    throw new ToolError("invalid_arguments", "Provide exactly one of agent_id or address.");
  }
  return hasAgent
    ? { agentId: validateAgentId(args.agent_id) }
    : { address: validateAddress(args.address) };
}

function registryLookupArguments(raw) {
  const args = requireObject(raw);
  rejectUnknownKeys(args, new Set(["agent_id"]));
  return { agentId: validateAgentId(args.agent_id) };
}

function registryRegisterArguments(raw) {
  const args = requireObject(raw);
  rejectUnknownKeys(
    args,
    new Set(["endpoints", "uri", "agent_wallet", "confirmed", "idempotency_key"]),
  );
  const endpoints = validateEndpoints(args.endpoints);
  const uri = validateHttpsUri(args.uri);
  const agentWallet =
    args.agent_wallet === undefined ? undefined : validateAddress(args.agent_wallet, "agent_wallet");
  validateMutationGate(args);
  return { args, endpoints, uri, agentWallet };
}

function registryRateArguments(raw) {
  const args = requireObject(raw);
  rejectUnknownKeys(args, new Set(["agent_id", "score", "confirmed", "idempotency_key"]));
  const agentId = validateAgentId(args.agent_id);
  const score = validateScore(args.score);
  validateMutationGate(args);
  return { args, agentId, score };
}

function socialReadArguments(raw, includeId = false) {
  const args = requireObject(raw);
  rejectUnknownKeys(args, new Set(includeId ? ["post_id"] : ["limit"]));
  return includeId
    ? { postId: validateSocialId(args.post_id, "post_id") }
    : { limit: validateLimit(args.limit) };
}

function socialReplyArguments(raw) {
  const args = requireObject(raw);
  rejectUnknownKeys(args, new Set(["post_id", "content", "confirmed", "idempotency_key"]));
  const postId = validateSocialId(args.post_id, "post_id");
  const content = validateText(args.content, "content", 5000);
  validateMutationGate(args);
  return { args, postId, content };
}

function socialCreateArguments(raw) {
  const args = requireObject(raw);
  rejectUnknownKeys(args, new Set(["title", "content", "confirmed", "idempotency_key"]));
  const title = validateText(args.title, "title", 300);
  const content = validateText(args.content, "content", 10000);
  validateMutationGate(args);
  return { args, title, content };
}

export function createRuntime({
  registryProviderFactory = unavailable("Registry provider"),
  registrySignerFactory = unavailable("Registry signer"),
  credentialLoader,
  httpTransport = defaultHttpTransport,
  idempotencyStore = createMemoryIdempotencyStore(),
  env = process.env,
} = {}) {
  const loadSocialCredential = credentialLoader ?? defaultCredentialLoader(env);

  async function registryRead(tool, raw, method, parseArguments) {
    try {
      const input = parseArguments(raw);
      const provider = await loadRegistryProvider(registryProviderFactory);
      if (typeof provider[method] !== "function") {
        throw new ToolError("transport_unavailable", `Registry provider does not implement ${method}.`);
      }
      let value;
      try {
        value = await provider[method](input);
      } catch (error) {
        throw normalizeTransportError(error, "provider_error", "Registry provider call failed");
      }
      if (value === null || value === undefined) {
        throw new ToolError("not_found", "The registry identity was not found.");
      }
      return success(tool, value);
    } catch (error) {
      return failure(tool, error);
    }
  }

  async function registryRegister(raw) {
    const tool = "registry_register";
    let attempted = false;
    try {
      const { args, endpoints, uri, agentWallet } = registryRegisterArguments(raw);
      const payload = { endpoints, ...(uri ? { uri } : {}), ...(agentWallet ? { agentWallet } : {}) };
      const state = await beginIdempotent(tool, args, payload, idempotencyStore);
      if (state.existing) return replayMutation(tool, state.key, state.existing, true);
      const signer = await loadRegistrySigner(registrySignerFactory);
      if (typeof signer.register !== "function") {
        throw new ToolError("transport_unavailable", "Registry signer does not implement register.");
      }
      attempted = true;
      let providerReceipt;
      try {
        providerReceipt = await signer.register(payload);
      } catch (error) {
        throw normalizeTransportError(error, "provider_error", "Registry registration failed");
      }
      if (!isPlainObject(providerReceipt)) {
        throw new ToolError("provider_error", "Registry registration did not return a structured receipt.");
      }
      return await completeMutation({
        tool,
        key: state.key,
        digest: state.digest,
        scopedKey: state.scopedKey,
        data: { registered: true },
        providerReceipt,
        store: idempotencyStore,
      });
    } catch (error) {
      return failure(tool, error, {
        mutation: true,
        economicMutation: true,
        status: attempted ? "unknown" : "not_started",
      });
    }
  }

  async function registryRate(raw) {
    const tool = "registry_rate";
    let attempted = false;
    try {
      const { args, agentId, score } = registryRateArguments(raw);
      const payload = { agentId, score };
      const state = await beginIdempotent(tool, args, payload, idempotencyStore);
      if (state.existing) return replayMutation(tool, state.key, state.existing, true);
      const signer = await loadRegistrySigner(registrySignerFactory);
      if (typeof signer.rate !== "function") {
        throw new ToolError("transport_unavailable", "Registry signer does not implement rate.");
      }
      attempted = true;
      let providerReceipt;
      try {
        providerReceipt = await signer.rate(payload);
      } catch (error) {
        throw normalizeTransportError(error, "provider_error", "Registry rating failed");
      }
      if (!isPlainObject(providerReceipt)) {
        throw new ToolError("provider_error", "Registry rating did not return a structured receipt.");
      }
      return await completeMutation({
        tool,
        key: state.key,
        digest: state.digest,
        scopedKey: state.scopedKey,
        data: { rated: true, agent_id: agentId, score },
        providerReceipt,
        store: idempotencyStore,
      });
    } catch (error) {
      return failure(tool, error, {
        mutation: true,
        economicMutation: true,
        status: attempted ? "unknown" : "not_started",
      });
    }
  }

  async function socialRead(tool, raw, request, parseArguments) {
    let secretValues = [];
    try {
      const input = parseArguments(raw);
      const credential = await loadCredential(loadSocialCredential);
      secretValues = [credential.token];
      let response;
      try {
        response = await httpTransport({ ...request(input), credential });
      } catch (error) {
        throw normalizeTransportError(error, "provider_error", "Moltbook transport failed", secretValues);
      }
      const normalized = normalizeHttpResponse(response, secretValues);
      return success(tool, normalized.body, { secretValues });
    } catch (error) {
      return failure(tool, error, { secretValues });
    }
  }

  async function socialMutation(tool, raw, parseArguments, makePayload, makeRequest) {
    let attempted = false;
    let secretValues = [];
    try {
      const parsed = parseArguments(raw);
      const payload = makePayload(parsed);
      const state = await beginIdempotent(tool, parsed.args, payload, idempotencyStore);
      if (state.existing) return replayMutation(tool, state.key, state.existing, false);
      const credential = await loadCredential(loadSocialCredential);
      secretValues = [credential.token];
      attempted = true;
      let response;
      try {
        response = await httpTransport({ ...makeRequest(parsed, payload), credential });
      } catch (error) {
        throw normalizeTransportError(error, "provider_error", "Moltbook transport failed", secretValues);
      }
      const normalized = normalizeHttpResponse(response, secretValues, true);
      return await completeMutation({
        tool,
        key: state.key,
        digest: state.digest,
        scopedKey: state.scopedKey,
        data: normalized.body,
        providerReceipt: { status: normalized.status, response: normalized.body },
        store: idempotencyStore,
        secretValues,
        economicMutation: false,
      });
    } catch (error) {
      return failure(tool, error, {
        mutation: true,
        economicMutation: false,
        status: attempted ? "unknown" : "not_started",
        secretValues,
      });
    }
  }

  const handlers = new Map([
    [
      "registry_status",
      (args) => registryRead("registry_status", args, "status", registryStatusArguments),
    ],
    [
      "registry_lookup",
      (args) => registryRead("registry_lookup", args, "lookup", registryLookupArguments),
    ],
    ["registry_register", registryRegister],
    ["registry_rate", registryRate],
    [
      "moltbook_hot",
      (args) =>
        socialRead(
          "moltbook_hot",
          args,
          ({ limit }) => ({ method: "GET", path: "/posts", query: { sort: "hot", limit } }),
          socialReadArguments,
        ),
    ],
    [
      "moltbook_new",
      (args) =>
        socialRead(
          "moltbook_new",
          args,
          ({ limit }) => ({ method: "GET", path: "/posts", query: { sort: "new", limit } }),
          socialReadArguments,
        ),
    ],
    [
      "moltbook_get_post",
      (args) =>
        socialRead(
          "moltbook_get_post",
          args,
          ({ postId }) => ({ method: "GET", path: `/posts/${encodeURIComponent(postId)}` }),
          (value) => socialReadArguments(value, true),
        ),
    ],
    [
      "moltbook_reply",
      (args) =>
        socialMutation(
          "moltbook_reply",
          args,
          socialReplyArguments,
          ({ postId, content }) => ({ postId, content }),
          ({ postId }, payload) => ({
            method: "POST",
            path: `/posts/${encodeURIComponent(postId)}/comments`,
            body: JSON.stringify({ content: payload.content }),
          }),
        ),
    ],
    [
      "moltbook_create",
      (args) =>
        socialMutation(
          "moltbook_create",
          args,
          socialCreateArguments,
          ({ title, content }) => ({ title, content }),
          (_parsed, payload) => ({
            method: "POST",
            path: "/posts",
            body: JSON.stringify(payload),
          }),
        ),
    ],
  ]);

  return Object.freeze({
    listTools() {
      return structuredClone(TOOL_DEFINITIONS);
    },
    async callTool(name, args = {}) {
      const handler = handlers.get(name);
      if (!handler) {
        return failure(
          typeof name === "string" ? name : "unknown",
          new ToolError("tool_not_found", "Unknown Moltbook tool."),
        );
      }
      return handler(args);
    },
  });
}

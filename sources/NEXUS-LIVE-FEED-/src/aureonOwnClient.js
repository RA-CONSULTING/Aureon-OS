export const AUREON_OWN_DEFAULT_BASE_URL = 'http://127.0.0.1:11435/v1';
export const AUREON_OWN_DEFAULT_MODEL = 'aureon-7b-v65k';

export function resolveAureonOwnRoute(env = process.env) {
  const baseUrl = String(
    env.AUREON_OWN_LLM_BASE_URL || AUREON_OWN_DEFAULT_BASE_URL,
  ).trim().replace(/\/+$/, '');
  const model = String(
    env.AUREON_OWN_LLM_MODEL || AUREON_OWN_DEFAULT_MODEL,
  ).trim();

  let parsed;
  try {
    parsed = new URL(baseUrl);
  } catch {
    throw new Error('aureon_own_model_route_invalid');
  }
  const hostname = parsed.hostname.replace(/^\[|\]$/g, '');
  const loopback = hostname === '::1' || /^127(?:\.\d{1,3}){3}$/.test(hostname);
  if (
    parsed.protocol !== 'http:'
    || !loopback
    || !parsed.port
    || parsed.pathname !== '/v1'
    || parsed.username
    || parsed.password
    || parsed.search
    || parsed.hash
    || model !== AUREON_OWN_DEFAULT_MODEL
  ) {
    throw new Error('aureon_own_model_route_invalid');
  }

  return {
    baseUrl,
    model,
    endpoint: `${baseUrl}/chat/completions`,
  };
}

export async function promptAureonOwn(messages, options = {}) {
  const {
    maxTokens = 512,
    temperature = 0,
    env = process.env,
    fetchImpl = globalThis.fetch,
  } = options;
  if (!Array.isArray(messages) || messages.length === 0) {
    throw new Error('aureon_own_model_messages_required');
  }
  if (typeof fetchImpl !== 'function') {
    throw new Error('aureon_own_model_fetch_unavailable');
  }
  if (!Number.isInteger(maxTokens) || maxTokens < 1 || maxTokens > 2048) {
    throw new Error('aureon_own_model_max_tokens_invalid');
  }
  if (!Number.isFinite(temperature) || temperature < 0 || temperature > 2) {
    throw new Error('aureon_own_model_temperature_invalid');
  }

  const route = resolveAureonOwnRoute(env);
  const response = await fetchImpl(route.endpoint, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    redirect: 'error',
    body: JSON.stringify({
      model: route.model,
      messages,
      max_tokens: maxTokens,
      temperature,
      stream: false,
    }),
  });
  if (!response.ok) {
    throw new Error(`aureon_own_model_http_${response.status}`);
  }

  const data = await response.json();
  const text = data?.choices?.[0]?.message?.content;
  if (data?.model !== route.model || typeof text !== 'string' || !text.trim()) {
    throw new Error('aureon_own_model_response_invalid');
  }
  return { text, model: data.model, raw: data };
}

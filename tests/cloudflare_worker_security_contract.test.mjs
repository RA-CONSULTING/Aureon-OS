import assert from "node:assert/strict";
import { readFile, readdir } from "node:fs/promises";
import test from "node:test";

import canonicalWorker from "../flameborn/workers/index.mjs";
import deployWorker from "../deploy/cloudflare/aureon_murge_worker/index.mjs";

const SECRET = "test-worker-access-secret-with-32-bytes";
const WORKER_ORIGIN = "https://worker.example";
const ALLOWED_ORIGIN = "https://console.example";
const CLIENT_IP = "203.0.113.19";
const WORKERS = [
  ["canonical", canonicalWorker],
  ["deploy", deployWorker],
];

function fakeLimiter(calls, result) {
  return {
    async limit(input) {
      calls.push(input);
      if (result instanceof Error) throw result;
      return result;
    },
  };
}

function makeEnv({
  includePreAuthLimiter = true,
  includeAuthenticatedLimiter = true,
  preAuthResult = { success: true },
  authenticatedResult = { success: true },
  allowedOrigins = "",
  extra = {},
} = {}) {
  const preAuthCalls = [];
  const authenticatedCalls = [];
  const env = {
    AUREON_WORKER_ACCESS_SECRET: SECRET,
    AUREON_ALLOWED_ORIGINS: allowedOrigins,
    ...extra,
  };
  if (includePreAuthLimiter) {
    env.API_PREAUTH_RATE_LIMITER = fakeLimiter(preAuthCalls, preAuthResult);
  }
  if (includeAuthenticatedLimiter) {
    env.API_RATE_LIMITER = fakeLimiter(authenticatedCalls, authenticatedResult);
  }
  return { env, preAuthCalls, authenticatedCalls };
}

function authorizedHeaders(extra = {}) {
  return {
    Authorization: `Bearer ${SECRET}`,
    ...extra,
  };
}

function makeRequest(pathname, init = {}) {
  const headers = new Headers(init.headers || {});
  if (!headers.has("CF-Connecting-IP")) headers.set("CF-Connecting-IP", CLIENT_IP);
  return new Request(`${WORKER_ORIGIN}${pathname}`, { ...init, headers });
}

async function readJson(response) {
  const text = await response.text();
  return text ? JSON.parse(text) : {};
}

function assertApiSecurityHeaders(response) {
  assert.equal(response.headers.get("Cache-Control"), "no-store");
  assert.equal(response.headers.get("X-Content-Type-Options"), "nosniff");
  assert.equal(response.headers.get("Referrer-Policy"), "no-referrer");
  assert.equal(response.headers.get("X-Frame-Options"), "DENY");
  assert.match(response.headers.get("Content-Security-Policy") || "", /frame-ancestors 'none'/);
}

for (const [name, worker] of WORKERS) {
  test(`${name}: missing access-secret configuration fails before rate limiting`, async () => {
    const missing = makeEnv();
    delete missing.env.AUREON_WORKER_ACCESS_SECRET;
    let response = await worker.fetch(makeRequest("/api/aureon/status"), missing.env);
    assert.equal(response.status, 503);
    assert.equal((await readJson(response)).error.code, "access_secret_unavailable");
    assert.equal(missing.preAuthCalls.length, 0);
    assert.equal(missing.authenticatedCalls.length, 0);
    assertApiSecurityHeaders(response);

    const blank = makeEnv();
    blank.env.AUREON_WORKER_ACCESS_SECRET = "   ";
    response = await worker.fetch(makeRequest("/api/aureon/status"), blank.env);
    assert.equal(response.status, 503);
    assert.equal(blank.preAuthCalls.length, 0);
    assert.equal(blank.authenticatedCalls.length, 0);

    const weak = makeEnv();
    weak.env.AUREON_WORKER_ACCESS_SECRET = "short";
    response = await worker.fetch(makeRequest("/api/aureon/status"), weak.env);
    assert.equal(response.status, 503);
    assert.equal((await readJson(response)).error.code, "access_secret_unavailable");
    assert.equal(weak.preAuthCalls.length, 0);
    assert.equal(weak.authenticatedCalls.length, 0);
  });

  test(`${name}: pre-auth limiter is mandatory and fails closed`, async () => {
    const missing = makeEnv({ includePreAuthLimiter: false });
    let response = await worker.fetch(makeRequest("/api/aureon/status", {
      headers: { Authorization: "Bearer rotating-candidate-one" },
    }), missing.env);
    assert.equal(response.status, 503);
    assert.equal((await readJson(response)).error.code, "rate_limiter_unavailable");
    assert.equal(missing.authenticatedCalls.length, 0);

    const throwing = makeEnv({ preAuthResult: new Error("binding failed") });
    response = await worker.fetch(makeRequest("/api/aureon/status"), throwing.env);
    assert.equal(response.status, 503);
    assert.equal(throwing.preAuthCalls.length, 1);
    assert.equal(throwing.authenticatedCalls.length, 0);

    const malformed = makeEnv({ preAuthResult: {} });
    response = await worker.fetch(makeRequest("/api/aureon/status"), malformed.env);
    assert.equal(response.status, 503);
    assert.equal(malformed.preAuthCalls.length, 1);
    assert.equal(malformed.authenticatedCalls.length, 0);

    const limited = makeEnv({ preAuthResult: { success: false } });
    response = await worker.fetch(makeRequest("/api/aureon/status"), limited.env);
    assert.equal(response.status, 429);
    assert.equal((await readJson(response)).error.code, "rate_limited");
    assert.equal(limited.preAuthCalls.length, 1);
    assert.equal(limited.authenticatedCalls.length, 0);
    assertApiSecurityHeaders(response);
  });

  test(`${name}: rotating invalid tokens, paths, and methods share one pre-auth key`, async () => {
    const requestEnv = makeEnv();
    let response = await worker.fetch(makeRequest("/api/aureon/status", {
      headers: { Authorization: "Bearer rotating-candidate-one" },
    }), requestEnv.env);
    assert.equal(response.status, 401);

    response = await worker.fetch(makeRequest("/api/chat", {
      method: "POST",
      headers: { Authorization: "Bearer rotating-candidate-two" },
    }), requestEnv.env);
    assert.equal(response.status, 401);

    response = await worker.fetch(makeRequest("/api/not-real", {
      method: "DELETE",
      headers: { Authorization: "Bearer rotating-candidate-three" },
    }), requestEnv.env);
    assert.equal(response.status, 401);

    assert.equal(requestEnv.preAuthCalls.length, 3);
    assert.equal(requestEnv.authenticatedCalls.length, 0);
    const keys = requestEnv.preAuthCalls.map((call) => call.key);
    assert.equal(new Set(keys).size, 1);
    assert.match(keys[0], /^preauth:v1:[a-f0-9]{64}$/);
    for (const forbidden of [SECRET, "candidate", "/api", "GET", "POST", "DELETE"]) {
      assert.equal(keys[0].includes(forbidden), false);
    }
  });

  test(`${name}: invalid or absent client IP uses one fixed pre-auth fallback`, async () => {
    const requestEnv = makeEnv();
    const invalidHeaders = {
      Authorization: "Bearer wrong-one",
      "CF-Connecting-IP": "attacker-controlled-value",
    };
    let response = await worker.fetch(makeRequest("/api/aureon/status", {
      headers: invalidHeaders,
    }), requestEnv.env);
    assert.equal(response.status, 401);

    const absentHeaders = new Headers({ Authorization: "Bearer wrong-two" });
    const absentRequest = new Request(`${WORKER_ORIGIN}/api/chat`, {
      method: "POST",
      headers: absentHeaders,
    });
    response = await worker.fetch(absentRequest, requestEnv.env);
    assert.equal(response.status, 401);

    assert.equal(requestEnv.preAuthCalls.length, 2);
    assert.equal(requestEnv.preAuthCalls[0].key, requestEnv.preAuthCalls[1].key);
    assert.equal(requestEnv.authenticatedCalls.length, 0);
  });

  test(`${name}: exact bearer auth precedes the authenticated limiter`, async () => {
    const requestEnv = makeEnv();
    let response = await worker.fetch(makeRequest("/api/aureon/status", {
      headers: { Authorization: `Bearer  ${SECRET}` },
    }), requestEnv.env);
    assert.equal(response.status, 401);
    assert.equal(requestEnv.preAuthCalls.length, 1);
    assert.equal(requestEnv.authenticatedCalls.length, 0);

    response = await worker.fetch(makeRequest("/api/aureon/status", {
      headers: authorizedHeaders(),
    }), requestEnv.env);
    assert.equal(response.status, 200);
    assert.equal(requestEnv.preAuthCalls.length, 2);
    assert.equal(requestEnv.authenticatedCalls.length, 1);
  });

  test(`${name}: authenticated limiter is mandatory, sanitized, and honors 429`, async () => {
    const missing = makeEnv({ includeAuthenticatedLimiter: false });
    let response = await worker.fetch(makeRequest("/api/aureon/status", {
      headers: authorizedHeaders(),
    }), missing.env);
    assert.equal(response.status, 503);
    assert.equal(missing.preAuthCalls.length, 1);
    assert.equal(missing.authenticatedCalls.length, 0);

    const limited = makeEnv({ authenticatedResult: { success: false } });
    response = await worker.fetch(makeRequest("/api/aureon/status", {
      headers: authorizedHeaders(),
    }), limited.env);
    assert.equal(response.status, 429);
    assert.equal((await readJson(response)).error.code, "rate_limited");
    assert.equal(limited.preAuthCalls.length, 1);
    assert.equal(limited.authenticatedCalls.length, 1);
    const key = limited.authenticatedCalls[0].key;
    assert.match(key, /^authenticated:v1:[a-f0-9]{64}:GET:\/api\/aureon\/status$/);
    assert.equal(key.includes(SECRET), false);
    assertApiSecurityHeaders(response);
  });

  test(`${name}: CORS is exact and runs after pre-auth limiting`, async () => {
    const allowed = makeEnv({ allowedOrigins: `${ALLOWED_ORIGIN},https://second.example` });
    let response = await worker.fetch(makeRequest("/api/aureon/status", {
      headers: authorizedHeaders({ Origin: ALLOWED_ORIGIN }),
    }), allowed.env);
    assert.equal(response.status, 200);
    assert.equal(response.headers.get("Access-Control-Allow-Origin"), ALLOWED_ORIGIN);
    assert.match(response.headers.get("Vary") || "", /Origin/);
    assert.equal(allowed.preAuthCalls.length, 1);
    assert.equal(allowed.authenticatedCalls.length, 1);

    const denied = makeEnv({ allowedOrigins: ALLOWED_ORIGIN });
    response = await worker.fetch(makeRequest("/api/aureon/status", {
      headers: authorizedHeaders({ Origin: "https://evil.example" }),
    }), denied.env);
    assert.equal(response.status, 403);
    assert.equal(response.headers.get("Access-Control-Allow-Origin"), null);
    assert.equal(denied.preAuthCalls.length, 1);
    assert.equal(denied.authenticatedCalls.length, 0);

    const wildcard = makeEnv({ allowedOrigins: "*" });
    response = await worker.fetch(makeRequest("/api/aureon/status", {
      headers: authorizedHeaders({ Origin: WORKER_ORIGIN }),
    }), wildcard.env);
    assert.equal(response.status, 503);
    assert.equal(wildcard.preAuthCalls.length, 1);
    assert.equal(wildcard.authenticatedCalls.length, 0);
  });

  test(`${name}: preflight is pre-auth limited and validates route, origin, method, and headers`, async () => {
    const valid = makeEnv({ allowedOrigins: ALLOWED_ORIGIN });
    let response = await worker.fetch(makeRequest("/api/aureon/status", {
      method: "OPTIONS",
      headers: {
        Origin: ALLOWED_ORIGIN,
        "Access-Control-Request-Method": "GET",
        "Access-Control-Request-Headers": "Authorization",
      },
    }), valid.env);
    assert.equal(response.status, 204);
    assert.equal(response.headers.get("Access-Control-Allow-Origin"), ALLOWED_ORIGIN);
    assert.equal(response.headers.get("Access-Control-Allow-Methods"), "GET");
    assert.equal(valid.preAuthCalls.length, 1);
    assert.equal(valid.authenticatedCalls.length, 0);
    assertApiSecurityHeaders(response);

    response = await worker.fetch(makeRequest("/api/aureon/status", {
      method: "OPTIONS",
      headers: {
        Origin: ALLOWED_ORIGIN,
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "Authorization, Content-Type",
      },
    }), valid.env);
    assert.equal(response.status, 405);

    response = await worker.fetch(makeRequest("/api/aureon/status", {
      method: "OPTIONS",
      headers: {
        Origin: ALLOWED_ORIGIN,
        "Access-Control-Request-Method": "GET",
        "Access-Control-Request-Headers": "Authorization, X-Secret",
      },
    }), valid.env);
    assert.equal(response.status, 403);

    response = await worker.fetch(makeRequest("/api/classroom/state", {
      method: "OPTIONS",
      headers: {
        Origin: ALLOWED_ORIGIN,
        "Access-Control-Request-Method": "GET",
        "Access-Control-Request-Headers": "Authorization",
      },
    }), valid.env);
    assert.equal(response.status, 503);
    assert.equal((await readJson(response)).error.code, "classroom_storage_unavailable");
    assert.equal(valid.preAuthCalls.length, 4);
    assert.equal(valid.authenticatedCalls.length, 0);
  });

  test(`${name}: JSON content type and streamed byte ceiling are enforced`, async () => {
    const wrongType = makeEnv();
    let response = await worker.fetch(makeRequest("/api/chat", {
      method: "POST",
      headers: authorizedHeaders({ "Content-Type": "text/plain" }),
      body: "{}",
    }), wrongType.env);
    assert.equal(response.status, 415);
    assert.equal((await readJson(response)).error.code, "json_content_type_required");

    const body = new ReadableStream({
      start(controller) {
        controller.enqueue(new Uint8Array(40 * 1024).fill(65));
        controller.enqueue(new Uint8Array(30 * 1024).fill(66));
        controller.close();
      },
    });
    const oversized = makeEnv();
    const request = makeRequest("/api/chat", {
      method: "POST",
      headers: authorizedHeaders({ "Content-Type": "application/json" }),
      body,
      duplex: "half",
    });
    assert.equal(request.headers.get("Content-Length"), null);
    response = await worker.fetch(request, oversized.env);
    assert.equal(response.status, 413);
    assert.equal((await readJson(response)).error.code, "request_too_large");
  });

  test(`${name}: client-supplied provider credentials are rejected before fetch`, async () => {
    const originalFetch = globalThis.fetch;
    let fetchCalls = 0;
    globalThis.fetch = async () => {
      fetchCalls += 1;
      throw new Error("provider fetch must not run");
    };
    try {
      const requestEnv = makeEnv();
      const response = await worker.fetch(makeRequest("/api/chat", {
        method: "POST",
        headers: authorizedHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify({
          provider: "openai",
          accessMode: "normal",
          message: "hello",
          nested: { apiKey: "must-not-cross-the-boundary" },
        }),
      }), requestEnv.env);
      assert.equal(response.status, 400);
      assert.equal((await readJson(response)).error.code, "client_secret_rejected");
      assert.equal(fetchCalls, 0);
    } finally {
      globalThis.fetch = originalFetch;
    }
  });

  test(`${name}: provider cost controls reject unauthorized or unbounded requests before fetch`, async () => {
    const originalFetch = globalThis.fetch;
    const fetchCalls = [];
    let providerSucceeds = false;
    globalThis.fetch = async (url, options) => {
      fetchCalls.push({ url: String(url), options });
      if (providerSucceeds) {
        return new Response(JSON.stringify({
          choices: [{ message: { content: "bounded paid response" } }],
        }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        });
      }
      return new Response(JSON.stringify({ error: { message: "primary failed" } }), {
        status: 500,
        headers: { "Content-Type": "application/json" },
      });
    };
    const send = async (body, extra = {}) => {
      const requestEnv = makeEnv({ extra });
      return worker.fetch(makeRequest("/api/chat", {
        method: "POST",
        headers: authorizedHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify(body),
      }), requestEnv.env);
    };

    try {
      let response = await send({
        provider: "openai",
        accessMode: "normal",
        model: "gpt-4o-mini",
        message: "hello",
      });
      assert.equal(response.status, 403);
      assert.equal((await readJson(response)).error.code, "paid_provider_disabled");

      response = await send({
        provider: "openai",
        accessMode: "normal",
        model: "gpt-4o-mini",
        message: "hello",
      }, {
        AUREON_ALLOW_PAID_PROVIDERS: "TRUE",
        OPENAI_API_KEY: "server-side-key",
      });
      assert.equal(response.status, 403);

      for (const body of [
        { provider: "unknown-provider", accessMode: "free", message: "hello" },
        { provider: "gemini", accessMode: "free", model: "arbitrary/model", message: "hello" },
        { provider: "gemini", accessMode: "free", message: "hello", max_tokens: 999999999 },
        { provider: "gemini", accessMode: "free", message: "hello", max_tokens: "NaN" },
        { provider: "gemini", accessMode: "free", message: "hello", temperature: "Infinity" },
        { provider: "gemini", accessMode: "free", message: "hello", rolePrompt: "r".repeat(2049) },
        { provider: "gemini", accessMode: "free", message: "m".repeat(8193) },
      ]) {
        response = await send(body);
        assert.equal(response.status, 400);
      }
      assert.equal(fetchCalls.length, 0);

      response = await send({
        provider: "gemini",
        accessMode: "free",
        model: "gemini-2.5-flash",
        message: "hello",
      }, {
        GEMINI_API_KEY: "server-side-gemini-key",
        OLLAMA_API_KEY: "server-side-ollama-key",
      });
      assert.equal(response.status, 502);
      assert.equal(fetchCalls.length, 1, "free primary failure must not trigger paid Ollama fallback");

      fetchCalls.length = 0;
      providerSucceeds = true;
      response = await send({
        provider: "openai",
        accessMode: "normal",
        model: "gpt-4o-mini",
        message: "hello",
        rolePrompt: "bounded role",
        temperature: 2,
        max_tokens: 2048,
      }, {
        AUREON_ALLOW_PAID_PROVIDERS: "true",
        OPENAI_API_KEY: "server-side-key",
      });
      assert.equal(response.status, 200);
      assert.equal(fetchCalls.length, 1);
      const outbound = JSON.parse(fetchCalls[0].options.body);
      assert.equal(outbound.max_tokens, 2048);
      assert.equal(outbound.temperature, 2);
    } finally {
      globalThis.fetch = originalFetch;
    }
  });

  test(`${name}: upstream failures are sanitized`, async () => {
    const upstreamLeak = "provider-secret-stack-and-account-id";
    const originalFetch = globalThis.fetch;
    globalThis.fetch = async () => new Response(JSON.stringify({
      error: { message: upstreamLeak },
    }), {
      status: 500,
      headers: { "Content-Type": "application/json" },
    });
    try {
      const requestEnv = makeEnv({
        extra: {
          OPENAI_API_KEY: "server-side-test-provider-key",
          AUREON_ALLOW_PAID_PROVIDERS: "true",
          AUREON_EXTERNAL_LLM_FALLBACK: "disabled",
        },
      });
      const response = await worker.fetch(makeRequest("/api/chat", {
        method: "POST",
        headers: authorizedHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify({
          provider: "openai",
          accessMode: "normal",
          message: "hello",
        }),
      }), requestEnv.env);
      const raw = await response.text();
      assert.equal(response.status, 502);
      assert.equal(raw.includes(upstreamLeak), false);
      assert.equal(raw.includes("server-side-test-provider-key"), false);
      assert.match(raw, /upstream_request_failed/);
      assertApiSecurityHeaders(response);
    } finally {
      globalThis.fetch = originalFetch;
    }
  });

  test(`${name}: classroom routes remain fail-closed without shared memory`, async () => {
    const requestEnv = makeEnv();
    const requests = [
      makeRequest("/api/classroom/state", { headers: authorizedHeaders() }),
      makeRequest("/api/classroom/replay", { headers: authorizedHeaders() }),
      makeRequest("/api/classroom/observe", {
        method: "POST",
        headers: authorizedHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify({ sessionId: "tenant-a", conversation: { user: "secret" } }),
      }),
    ];
    for (const request of requests) {
      const response = await worker.fetch(request, requestEnv.env);
      const payload = await readJson(response);
      assert.equal(response.status, 503);
      assert.equal(payload.error.code, "classroom_storage_unavailable");
      assert.equal("memory" in payload, false);
    }
    assert.equal(requestEnv.preAuthCalls.length, 3);
    assert.equal(requestEnv.authenticatedCalls.length, 3);
  });

  test(`${name}: authenticated status is narrow and provider-free`, async () => {
    const requestEnv = makeEnv();
    const response = await worker.fetch(makeRequest("/api/aureon/status", {
      headers: authorizedHeaders(),
    }), requestEnv.env);
    const payload = await readJson(response);
    assert.equal(response.status, 200);
    assert.equal(payload.provider, "aureon");
    assert.equal(payload.paidProvidersEnabled, false);
    assert.equal(payload.architecture.obsidianBridge.mode, "disabled-until-tenant-storage");
    assert.equal("memory" in payload, false);
    assert.equal(requestEnv.preAuthCalls.length, 1);
    assert.equal(requestEnv.authenticatedCalls.length, 1);
    assertApiSecurityHeaders(response);
  });
}

test("canonical and deploy Worker logic are source-identical and forbid latent secret/state bypasses", async () => {
  const [canonical, deploy] = await Promise.all([
    readFile(new URL("../flameborn/workers/index.mjs", import.meta.url), "utf8"),
    readFile(new URL("../deploy/cloudflare/aureon_murge_worker/index.mjs", import.meta.url), "utf8"),
  ]);
  const normalizedCanonical = canonical.replace(/\r\n/g, "\n");
  const normalizedDeploy = deploy.replace(/\r\n/g, "\n");
  assert.equal(normalizedDeploy, normalizedCanonical);
  for (const source of [normalizedCanonical, normalizedDeploy]) {
    assert.equal(source.includes("parsed.apiKey"), false);
    assert.equal(source.includes("classroomMemory"), false);
    assert.match(source, /AUREON_ALLOW_PAID_PROVIDERS === "true"/);
    assert.match(source, /byteLength < 32/);
    assert.match(source, /difference \|= suppliedDigest\[index\] \^ expectedDigest\[index\]/);
    assert.match(source, /preauth:v1:\$\{clientDigest\}/);
  }
});

test("Wrangler manifests bind both limiter stages and route exact /api through the Worker", async () => {
  const sources = await Promise.all([
    readFile(new URL("../flameborn/wrangler.jsonc", import.meta.url), "utf8"),
    readFile(new URL("../deploy/cloudflare/aureon_murge_worker/wrangler.jsonc", import.meta.url), "utf8"),
  ]);
  for (const source of sources) {
    const manifest = JSON.parse(source);
    assert.deepEqual(manifest.ratelimits, [
      {
        name: "API_PREAUTH_RATE_LIMITER",
        namespace_id: "2026081102",
        simple: { limit: 20, period: 60 },
      },
      {
        name: "API_RATE_LIMITER",
        namespace_id: "2026081101",
        simple: { limit: 60, period: 60 },
      },
    ]);
    assert.deepEqual(manifest.assets.run_worker_first, ["/api", "/api/*"]);
  }
});

test("dedicated Cloudflare UI has a closed asset graph and only supported API routes", async () => {
  const sourceRoot = new URL("../flameborn/cloudflare-ui/", import.meta.url);
  const builtRoot = new URL("../flameborn/dist-workers/", import.meta.url);
  const expectedFiles = [".assetsignore", "_headers", "app.js", "index.html", "style.css"];
  const [sourceFiles, builtFiles] = await Promise.all([
    readdir(sourceRoot),
    readdir(builtRoot),
  ]);
  assert.deepEqual(sourceFiles.sort(), expectedFiles);
  assert.deepEqual(builtFiles.sort(), expectedFiles);

  const [html, app, headers] = await Promise.all([
    readFile(new URL("index.html", sourceRoot), "utf8"),
    readFile(new URL("app.js", sourceRoot), "utf8"),
    readFile(new URL("_headers", sourceRoot), "utf8"),
  ]);
  const localReferences = [...html.matchAll(/(?:href|src)="([^"]+)"/g)]
    .map((match) => match[1])
    .filter((value) => !/^(?:https?:|data:|#)/i.test(value));
  assert.deepEqual(localReferences.sort(), ["app.js", "style.css"]);
  for (const reference of localReferences) {
    assert.equal(sourceFiles.includes(reference), true, `missing source asset ${reference}`);
    assert.equal(builtFiles.includes(reference), true, `missing built asset ${reference}`);
  }

  for (const file of expectedFiles) {
    const [source, built] = await Promise.all([
      readFile(new URL(file, sourceRoot), "utf8"),
      readFile(new URL(file, builtRoot), "utf8"),
    ]);
    assert.equal(built.replace(/\r\n/g, "\n"), source.replace(/\r\n/g, "\n"));
  }

  const routeLiterals = [...app.matchAll(/["'](\/api\/[^"']+)["']/g)].map((match) => match[1]);
  assert.deepEqual([...new Set(routeLiterals)].sort(), ["/api/aureon/status", "/api/chat"]);
  assert.match(app, /sessionStorage\.setItem/);
  assert.match(app, /headers\.set\("Authorization", `Bearer \$\{token\}`\)/);
  assert.equal(app.includes("localStorage"), false);
  assert.equal(app.includes("innerHTML"), false);
  assert.equal(app.includes("apiKey"), false);
  assert.equal(html.includes("node_modules"), false);
  assert.equal(html.includes('id="apiKey"'), false);
  assert.equal(html.includes('value="normal"'), false);
  assert.equal(html.includes('id="model"'), false);
  assert.match(app, /accessMode: "free"/);
  assert.match(headers, /Cache-Control: public, max-age=0, must-revalidate/);
  assert.match(headers, /Content-Security-Policy:/);
  assert.equal(headers.includes("immutable"), false);
});

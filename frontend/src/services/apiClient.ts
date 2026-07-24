/**
 * apiClient — the single typed entry point to the Aureon operator REST surface.
 *
 * Every dashboard reaches the backend over relative `/api/...` paths, which Vite
 * proxies to the operator server in dev (see vite.config.ts) and are same-origin
 * in production. This wrapper gives the whole UI ONE honest contract:
 *
 *   - a uniform result: it returns data on success and throws a typed `ApiError`
 *     on any non-2xx or transport failure, so callers can distinguish "backend
 *     offline" from "backend said no" and degrade honestly (never fabricate).
 *   - a short timeout so a dead gateway surfaces as "offline" instead of hanging.
 *   - no embedded credentials: a secured operator gets its bearer injected by the
 *     dev proxy or the same-origin session, never hard-coded here.
 *
 * Prefer this over bare `fetch("/api/...")` in new code.
 */

/** Thrown for any failed backend call. `offline` marks transport failures
 *  (gateway down / timeout / network) as opposed to a real HTTP error status. */
export class ApiError extends Error {
  readonly status: number;
  readonly offline: boolean;
  readonly path: string;
  constructor(message: string, opts: { status?: number; offline?: boolean; path: string }) {
    super(message);
    this.name = "ApiError";
    this.status = opts.status ?? 0;
    this.offline = opts.offline ?? false;
    this.path = opts.path;
  }
}

const DEFAULT_TIMEOUT_MS = 8000;

interface RequestOptions {
  /** Abort the request after this many ms (default 8000). */
  timeoutMs?: number;
  /** Extra headers merged over the defaults. */
  headers?: Record<string, string>;
  signal?: AbortSignal;
}

async function request<T>(
  method: "GET" | "POST" | "DELETE",
  path: string,
  body?: unknown,
  opts: RequestOptions = {},
): Promise<T> {
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), opts.timeoutMs ?? DEFAULT_TIMEOUT_MS);

  // If the caller passed their own signal, abort ours when theirs fires.
  if (opts.signal) {
    if (opts.signal.aborted) controller.abort();
    else opts.signal.addEventListener("abort", () => controller.abort(), { once: true });
  }

  let res: Response;
  try {
    res = await fetch(path, {
      method,
      cache: "no-store",
      signal: controller.signal,
      headers: {
        Accept: "application/json",
        ...(body !== undefined ? { "Content-Type": "application/json" } : {}),
        ...opts.headers,
      },
      ...(body !== undefined ? { body: JSON.stringify(body) } : {}),
    });
  } catch (err) {
    // fetch rejects only on transport failure (network down, CORS, abort) — the
    // gateway is unreachable. This is the honest "offline" signal.
    const aborted = err instanceof DOMException && err.name === "AbortError";
    throw new ApiError(aborted ? `Request to ${path} timed out` : `Cannot reach ${path}`, {
      offline: true,
      path,
    });
  } finally {
    window.clearTimeout(timeout);
  }

  if (!res.ok) {
    let detail = "";
    try {
      const j = await res.json();
      detail = typeof j?.error === "string" ? j.error : "";
    } catch {
      /* body was not JSON — keep the status-only message */
    }
    throw new ApiError(detail || `${method} ${path} -> ${res.status}`, {
      status: res.status,
      path,
    });
  }

  // 204 / empty body -> return undefined as T
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export const api = {
  get: <T>(path: string, opts?: RequestOptions) => request<T>("GET", path, undefined, opts),
  post: <T>(path: string, body?: unknown, opts?: RequestOptions) =>
    request<T>("POST", path, body, opts),
  del: <T>(path: string, opts?: RequestOptions) => request<T>("DELETE", path, undefined, opts),
};

/**
 * `/api/pulse` — the operator's one-call vitals (providers + platform status +
 * organism + switchboard). The richest single read for a top-of-app health band.
 * Shape is intentionally permissive: fields the backend omits stay optional.
 */
export interface OperatorPulse {
  ok?: boolean;
  status?: "healthy" | "degraded" | "critical" | string;
  /** Configured LLM providers — a list; its length is the provider count. */
  providers?: unknown[];
  switchboard?: { total?: number; enabled?: number; armed?: number } & Record<string, unknown>;
  organism?: {
    connectome?: { coverage_pct?: number; nodes?: number; woven?: number } & Record<string, unknown>;
  } & Record<string, unknown>;
  service?: unknown;
  [key: string]: unknown;
}

/** Fetch the operator pulse. Throws `ApiError` (with `.offline`) when the
 *  backend is unreachable, so callers show an honest offline state. */
export function fetchPulse(opts?: RequestOptions): Promise<OperatorPulse> {
  return api.get<OperatorPulse>("/api/pulse", opts);
}

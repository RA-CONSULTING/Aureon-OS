#!/usr/bin/env node

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const EXPECTED_RATE_LIMITS = new Map([
  ["API_PREAUTH_RATE_LIMITER", { limit: 20, period: 60 }],
  ["API_RATE_LIMITER", { limit: 60, period: 60 }],
]);

export class DeploymentPreflightError extends Error {
  constructor(message) {
    super(message);
    this.name = "DeploymentPreflightError";
  }
}

export function validateDeploymentEnvironment(env = {}) {
  const accessSecret = env.AUREON_WORKER_ACCESS_SECRET;
  if (
    typeof accessSecret !== "string"
    || !accessSecret
    || accessSecret !== accessSecret.trim()
    || Buffer.byteLength(accessSecret, "utf8") < 32
  ) {
    throw new DeploymentPreflightError(
      "AUREON_WORKER_ACCESS_SECRET must be trimmed and at least 32 UTF-8 bytes.",
    );
  }

  const rawOrigins = env.AUREON_ALLOWED_ORIGINS;
  if (typeof rawOrigins !== "string" || !rawOrigins) {
    throw new DeploymentPreflightError(
      "AUREON_ALLOWED_ORIGINS must contain at least one exact HTTPS origin.",
    );
  }

  const origins = rawOrigins.split(",");
  const uniqueOrigins = new Set();
  for (let index = 0; index < origins.length; index += 1) {
    const candidate = origins[index];
    if (!candidate || candidate !== candidate.trim() || candidate === "*") {
      throw new DeploymentPreflightError(
        `AUREON_ALLOWED_ORIGINS entry ${index + 1} is not an exact HTTPS origin.`,
      );
    }
    try {
      const parsed = new URL(candidate);
      if (parsed.protocol !== "https:" || parsed.origin !== candidate) {
        throw new Error("not canonical");
      }
    } catch {
      throw new DeploymentPreflightError(
        `AUREON_ALLOWED_ORIGINS entry ${index + 1} is not an exact HTTPS origin.`,
      );
    }
    if (uniqueOrigins.has(candidate)) {
      throw new DeploymentPreflightError(
        `AUREON_ALLOWED_ORIGINS entry ${index + 1} is duplicated.`,
      );
    }
    uniqueOrigins.add(candidate);
  }

  const paidProviders = env.AUREON_ALLOW_PAID_PROVIDERS;
  if (paidProviders !== undefined && paidProviders !== "true") {
    throw new DeploymentPreflightError(
      "AUREON_ALLOW_PAID_PROVIDERS must be omitted or exactly true.",
    );
  }

  return {
    originCount: uniqueOrigins.size,
    paidProvidersEnabled: paidProviders === "true",
  };
}

export function validateWranglerRateLimits(config) {
  if (!config || typeof config !== "object" || Array.isArray(config)) {
    throw new DeploymentPreflightError("Wrangler configuration must be an object.");
  }
  if (
    config.vars
    && Object.prototype.hasOwnProperty.call(config.vars, "AUREON_WORKER_ACCESS_SECRET")
  ) {
    throw new DeploymentPreflightError(
      "AUREON_WORKER_ACCESS_SECRET must be a provider secret, not a Wrangler vars value.",
    );
  }

  if (!Array.isArray(config.ratelimits)) {
    throw new DeploymentPreflightError("Wrangler rate-limit bindings are missing.");
  }

  for (const [name, expected] of EXPECTED_RATE_LIMITS) {
    const matches = config.ratelimits.filter((entry) => entry?.name === name);
    if (matches.length !== 1) {
      throw new DeploymentPreflightError(
        `Wrangler must define exactly one ${name} rate-limit binding.`,
      );
    }
    const binding = matches[0];
    if (typeof binding.namespace_id !== "string" || !binding.namespace_id.trim()) {
      throw new DeploymentPreflightError(`${name} must have a namespace_id.`);
    }
    if (
      binding.simple?.limit !== expected.limit
      || binding.simple?.period !== expected.period
    ) {
      throw new DeploymentPreflightError(
        `${name} must use limit ${expected.limit} and period ${expected.period}.`,
      );
    }
  }

  return { bindingCount: EXPECTED_RATE_LIMITS.size };
}

export function loadWranglerConfig(configPath) {
  let source;
  try {
    source = fs.readFileSync(configPath, "utf8").replace(/^\uFEFF/, "");
  } catch {
    throw new DeploymentPreflightError("Wrangler configuration could not be read.");
  }
  try {
    return JSON.parse(source);
  } catch {
    throw new DeploymentPreflightError(
      "Wrangler configuration must remain JSON-compatible JSONC for offline validation.",
    );
  }
}

export function runPreflight({ env = process.env, configPath } = {}) {
  const environment = validateDeploymentEnvironment(env);
  const rateLimits = validateWranglerRateLimits(loadWranglerConfig(configPath));
  return { ...environment, ...rateLimits };
}

const modulePath = fileURLToPath(import.meta.url);
const invokedPath = process.argv[1] ? path.resolve(process.argv[1]) : null;
if (invokedPath && pathToFileURL(invokedPath).href === import.meta.url) {
  const defaultConfigPath = path.resolve(path.dirname(modulePath), "..", "wrangler.jsonc");
  try {
    const result = runPreflight({
      env: process.env,
      configPath: process.argv[2] ? path.resolve(process.argv[2]) : defaultConfigPath,
    });
    console.log(
      `Cloudflare deployment security preflight passed: ${result.originCount} origin(s), `
      + `${result.bindingCount} rate-limit binding(s), paid providers `
      + `${result.paidProvidersEnabled ? "enabled" : "disabled"}.`,
    );
  } catch (error) {
    const message = error instanceof DeploymentPreflightError
      ? error.message
      : "unexpected validation error";
    console.error(`Cloudflare deployment security preflight failed: ${message}`);
    process.exitCode = 1;
  }
}

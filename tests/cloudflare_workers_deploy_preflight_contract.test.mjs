import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

import {
  DeploymentPreflightError,
  loadWranglerConfig,
  validateDeploymentEnvironment,
  validateWranglerRateLimits,
} from "../flameborn/scripts/validate_workers_deploy_config.mjs";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const FLAMEBORN = path.join(ROOT, "flameborn");
const VALID_ENV = Object.freeze({
  AUREON_WORKER_ACCESS_SECRET: "0123456789abcdef0123456789abcdef",
  AUREON_ALLOWED_ORIGINS: "https://academy.example,https://admin.example",
});

test("deployment environment accepts only bounded secret and canonical HTTPS origins", () => {
  assert.deepEqual(validateDeploymentEnvironment(VALID_ENV), {
    originCount: 2,
    paidProvidersEnabled: false,
  });
  assert.deepEqual(
    validateDeploymentEnvironment({
      ...VALID_ENV,
      AUREON_ALLOW_PAID_PROVIDERS: "true",
    }),
    { originCount: 2, paidProvidersEnabled: true },
  );

  for (const invalidSecret of [
    undefined,
    "",
    "short",
    ` ${VALID_ENV.AUREON_WORKER_ACCESS_SECRET}`,
  ]) {
    assert.throws(
      () => validateDeploymentEnvironment({
        ...VALID_ENV,
        AUREON_WORKER_ACCESS_SECRET: invalidSecret,
      }),
      DeploymentPreflightError,
    );
  }

  for (const invalidOrigins of [
    undefined,
    "",
    "*",
    "http://academy.example",
    "https://academy.example/",
    "https://academy.example/path",
    "https://academy.example, https://admin.example",
    "https://academy.example,https://academy.example",
  ]) {
    assert.throws(
      () => validateDeploymentEnvironment({
        ...VALID_ENV,
        AUREON_ALLOWED_ORIGINS: invalidOrigins,
      }),
      DeploymentPreflightError,
    );
  }

  for (const invalidPaidFlag of ["", "false", "TRUE", "1"]) {
    assert.throws(
      () => validateDeploymentEnvironment({
        ...VALID_ENV,
        AUREON_ALLOW_PAID_PROVIDERS: invalidPaidFlag,
      }),
      DeploymentPreflightError,
    );
  }
});

test("both packaged Wrangler configs retain the exact two rate-limit bindings", () => {
  const configPaths = [
    path.join(FLAMEBORN, "wrangler.jsonc"),
    path.join(ROOT, "deploy", "cloudflare", "aureon_murge_worker", "wrangler.jsonc"),
  ];
  for (const configPath of configPaths) {
    assert.deepEqual(validateWranglerRateLimits(loadWranglerConfig(configPath)), {
      bindingCount: 2,
    });
  }

  const missingBinding = loadWranglerConfig(configPaths[0]);
  missingBinding.ratelimits = missingBinding.ratelimits.slice(0, 1);
  assert.throws(() => validateWranglerRateLimits(missingBinding), DeploymentPreflightError);

  const plaintextSecret = loadWranglerConfig(configPaths[0]);
  plaintextSecret.vars = { AUREON_WORKER_ACCESS_SECRET: "forbidden" };
  assert.throws(() => validateWranglerRateLimits(plaintextSecret), DeploymentPreflightError);
});

test("deploy entrypoints run the offline preflight before Wrangler", () => {
  const bootstrap = fs.readFileSync(
    path.join(FLAMEBORN, "scripts", "workers_dev_bootstrap.sh"),
    "utf8",
  );
  const preflightCall = "node \"$PROJECT_DIR/scripts/validate_workers_deploy_config.mjs\"";
  assert.ok(bootstrap.includes(preflightCall));
  assert.ok(bootstrap.indexOf(preflightCall) < bootstrap.indexOf("npx wrangler"));
  assert.match(
    bootstrap,
    /if \[\[ "\$DO_DEPLOY" == "--deploy" \]\]; then[\s\S]*?validate_workers_deploy_config\.mjs/,
  );
  assert.doesNotMatch(bootstrap, /AUREON_WORKER_ACCESS_SECRET\s*=/);
  assert.doesNotMatch(bootstrap, /openssl|randomBytes|uuidgen/);

  const packageJson = JSON.parse(
    fs.readFileSync(path.join(FLAMEBORN, "package.json"), "utf8"),
  );
  assert.equal(
    packageJson.scripts["cf:preflight"],
    "node scripts/validate_workers_deploy_config.mjs wrangler.jsonc",
  );
  const directDeploy = packageJson.scripts["cf:deploy"];
  assert.ok(directDeploy.indexOf("cf:preflight") < directDeploy.indexOf("wrangler deploy"));
});

test("operator guide has no .env secret examples and keeps provider readback pending", () => {
  const guide = fs.readFileSync(
    path.join(FLAMEBORN, "CLOUDFLARE_WORKERS_DEV_SETUP.md"),
    "utf8",
  );
  assert.doesNotMatch(
    guide,
    /(?:CLOUDFLARE_API_TOKEN|AUREON_WORKER_ACCESS_SECRET)\s*=/,
  );
  assert.doesNotMatch(guide, /Authorization:\s*Bearer\s*<TOKEN>/);
  assert.match(guide, /AUREON_WORKER_ACCESS_SECRET/);
  assert.match(guide, /AUREON_ALLOWED_ORIGINS/);
  assert.match(guide, /AUREON_ALLOW_PAID_PROVIDERS/);
  assert.match(guide, /API_PREAUTH_RATE_LIMITER/);
  assert.match(guide, /API_RATE_LIMITER/);
  assert.match(guide, /Provider-side binding\/secret[\s\S]*PENDING/);
});

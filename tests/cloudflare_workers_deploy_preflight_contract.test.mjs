import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { createHash } from "node:crypto";
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
const MURGE = path.join(ROOT, "integrations", "aureon_murge");
const MURGE_SCRIPTS = path.join(ROOT, "scripts", "aureon_murge");
const IMPORTED_MURGE = path.join(
  ROOT,
  "imports",
  "aureon_murge_required_20260519_150125",
);
const VALID_ENV = Object.freeze({
  AUREON_WORKER_ACCESS_SECRET: "0123456789abcdef0123456789abcdef",
  AUREON_ALLOWED_ORIGINS: "https://academy.example,https://admin.example",
});
const UNAVAILABLE = "node -e process.exitCode=2";
const SHELL_HOLD = [
  "#!/usr/bin/env bash",
  "set -euo pipefail",
  "",
  "# Terminal HOLD: operational route is unavailable.",
  "exit 2",
  "",
].join("\n");
const NODE_HOLD = [
  "#!/usr/bin/env node",
  "",
  "// Terminal HOLD: operational route is unavailable.",
  "process.exitCode = 2;",
  "",
].join("\n");
const IMMEDIATE_NODE_HOLD = [
  "#!/usr/bin/env node",
  "",
  "// Terminal HOLD: operational route is unavailable.",
  "process.exit(2);",
  "",
].join("\n");
const PYTHON_HOLD = [
  "#!/usr/bin/env python3",
  "\"\"\"Terminal HOLD: operational route is unavailable.\"\"\"",
  "",
  "raise SystemExit(2)",
  "",
].join("\n");
const POWERSHELL_HOLD = [
  "# Terminal HOLD: operational route is unavailable.",
  "exit 2",
  "",
].join("\n");
const HELD_SHELL_SCRIPTS = Object.freeze([
  "check_aureon_health.sh",
  "cloudflare_bootstrap.sh",
  "cloudflare_check.sh",
  "fix_docker_sandbox_access.sh",
  "openrouter_bootstrap.sh",
  "save_gemini_key.sh",
  "setup_git_zenodo_secrets.sh",
  "setup_sandbox_runtime.sh",
  "start_aureon_brain_local.sh",
  "start_desktop_experiment.sh",
  "start_flameborn_runtime.sh",
  "workers_dev_bootstrap.sh",
]);

function readText(filePath) {
  return fs.readFileSync(filePath, "utf8").replaceAll("\r\n", "\n");
}

function readPackage(relativePath) {
  return JSON.parse(readText(path.join(ROOT, relativePath)));
}

function assertPackageBoundary({
  relativePath,
  held,
  safe,
}) {
  const scripts = readPackage(relativePath).scripts;
  assert.equal(scripts.unavailable, UNAVAILABLE, relativePath);
  assert.deepEqual(
    Object.keys(scripts).sort(),
    ["unavailable", ...held, ...Object.keys(safe)].sort(),
    relativePath,
  );
  for (const name of held) {
    assert.equal(
      scripts[name],
      `npm run unavailable -- ${name}`,
      `${relativePath}: ${name}`,
    );
  }
  for (const [name, command] of Object.entries(safe)) {
    assert.equal(scripts[name], command, `${relativePath}: ${name}`);
  }
}

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

test("Node package entrypoints expose only static checks, builds, and preflight", () => {
  const operational = [
    "start",
    "runtime:start",
    "desktop:install",
    "desktop:start",
    "desktop:smoke",
    "aureon:cli",
    "sandbox:build",
    "cf:dev",
    "cf:deploy",
    "cf:check",
  ];
  assertPackageBoundary({
    relativePath: "flameborn/package.json",
    held: operational,
    safe: {
      check: "node --check server.mjs && node --check runtime/server.mjs && bash -n scripts/setup_sandbox_runtime.sh && bash -n scripts/fix_docker_sandbox_access.sh && bash -n scripts/start_aureon_brain_local.sh && bash -n scripts/start_flameborn_runtime.sh",
      "cf:build": "bash scripts/build_workers_assets.sh",
      "cf:preflight": "node scripts/validate_workers_deploy_config.mjs wrangler.jsonc",
    },
  });
  assertPackageBoundary({
    relativePath: "integrations/aureon_murge/web_app/package.json",
    held: [...operational, "cf:build"],
    safe: {
      check: "npm run check:node",
      "check:node": "node --check server.mjs && node --check ../runtime/server.mjs && node --check ../desktop/main.cjs && node --check ../desktop/preload.cjs && node --check ../desktop/runtime-manager.cjs",
      "check:scripts:linux": "bash -n ../../../scripts/aureon_murge/setup_sandbox_runtime.sh && bash -n ../../../scripts/aureon_murge/fix_docker_sandbox_access.sh && bash -n ../../../scripts/aureon_murge/start_aureon_brain_local.sh && bash -n ../../../scripts/aureon_murge/start_flameborn_runtime.sh",
    },
  });
  assertPackageBoundary({
    relativePath: "integrations/aureon_murge/runtime/package.json",
    held: ["start"],
    safe: {
      check: "node --check server.mjs",
    },
  });
  assertPackageBoundary({
    relativePath: "imports/aureon_murge_required_20260519_150125/package.json",
    held: operational,
    safe: {
      check: "node --check server.mjs && node --check runtime/server.mjs && bash -n scripts/setup_sandbox_runtime.sh && bash -n scripts/fix_docker_sandbox_access.sh && bash -n scripts/start_aureon_brain_local.sh && bash -n scripts/start_flameborn_runtime.sh",
      "cf:build": "bash scripts/build_workers_assets.sh",
    },
  });
  for (const relativePath of [
    "flameborn/desktop/package.json",
    "integrations/aureon_murge/desktop/package.json",
    "imports/aureon_murge_required_20260519_150125/desktop/package.json",
  ]) {
    assertPackageBoundary({
      relativePath,
      held: ["start", "smoke", "pack:dir", "dist:linux"],
      safe: {},
    });
  }

  const probe = spawnSync(
    process.execPath,
    ["-e", "process.exitCode=2", "package-terminal-hold-probe"],
    { encoding: "utf8" },
  );
  assert.equal(probe.status, 2);
  assert.equal(probe.stdout, "");
  assert.equal(probe.stderr, "");
});

test("direct operational scripts are minimal terminal holds in every mirror", () => {
  for (const scriptsRoot of [
    path.join(FLAMEBORN, "scripts"),
    MURGE_SCRIPTS,
    path.join(IMPORTED_MURGE, "scripts"),
  ]) {
    for (const filename of HELD_SHELL_SCRIPTS) {
      assert.equal(readText(path.join(scriptsRoot, filename)), SHELL_HOLD);
    }
    assert.equal(readText(path.join(scriptsRoot, "aureon_cli.mjs")), NODE_HOLD);
    assert.equal(readText(path.join(scriptsRoot, "world_data_bridge.py")), PYTHON_HOLD);

    const shellNames = fs.readdirSync(scriptsRoot)
      .filter((name) => name.endsWith(".sh"))
      .sort();
    assert.deepEqual(
      shellNames,
      [...HELD_SHELL_SCRIPTS, "build_workers_assets.sh", "storage_audit.sh"].sort(),
    );
    assert.deepEqual(
      fs.readdirSync(scriptsRoot).filter((name) => name.endsWith(".py")).sort(),
      ["sum_csv_value.py", "world_data_bridge.py"],
    );
  }
  assert.equal(
    readText(path.join(MURGE_SCRIPTS, "start_murge_local_runtime.ps1")),
    POWERSHELL_HOLD,
  );
  assert.equal(
    readText(path.join(MURGE, "web_app", "scripts", "aureon_cli.mjs")),
    NODE_HOLD,
  );

  for (const cliPath of [
    path.join(FLAMEBORN, "scripts", "aureon_cli.mjs"),
    path.join(MURGE_SCRIPTS, "aureon_cli.mjs"),
    path.join(MURGE, "web_app", "scripts", "aureon_cli.mjs"),
    path.join(IMPORTED_MURGE, "scripts", "aureon_cli.mjs"),
  ]) {
    const completed = spawnSync(process.execPath, [cliPath], { encoding: "utf8" });
    assert.equal(completed.status, 2, cliPath);
    assert.equal(completed.stdout, "", cliPath);
    assert.equal(completed.stderr, "", cliPath);
  }
});

test("desktop main and runtime managers cannot spawn services directly", () => {
  const desktopRoots = [
    path.join(FLAMEBORN, "desktop"),
    path.join(MURGE, "desktop"),
    path.join(IMPORTED_MURGE, "desktop"),
  ];
  const managerSources = [];

  for (const desktopRoot of desktopRoots) {
    for (const [filename, expected] of [
      ["main.cjs", IMMEDIATE_NODE_HOLD],
      ["smoke-check.cjs", NODE_HOLD],
    ]) {
      const entrypoint = path.join(desktopRoot, filename);
      assert.equal(readText(entrypoint), expected, entrypoint);
      const completed = spawnSync(process.execPath, [entrypoint], { encoding: "utf8" });
      assert.equal(completed.status, 2, entrypoint);
      assert.equal(completed.stdout, "", entrypoint);
      assert.equal(completed.stderr, "", entrypoint);
    }

    const managerPath = path.join(desktopRoot, "runtime-manager.cjs");
    const managerSource = readText(managerPath);
    managerSources.push(managerSource);
    assert.doesNotMatch(
      managerSource,
      /child_process|\bspawn\s*\(|\bfork\s*\(|\bexecFile?\s*\(|node:http|node:https|node:fs|require\(["']electron["']\)/,
      managerPath,
    );

    const direct = spawnSync(process.execPath, [managerPath], { encoding: "utf8" });
    assert.equal(direct.status, 2, managerPath);
    assert.equal(direct.stdout, "", managerPath);
    assert.equal(direct.stderr, "", managerPath);

    const imported = spawnSync(
      process.execPath,
      [
        "-e",
        `const { RuntimeManager } = require(${JSON.stringify(managerPath)});` +
          "new RuntimeManager().ensureServices().then((status) => {" +
          "if (status.exitCode !== 2 || status.eligibleForAction !== false) process.exitCode = 1;" +
          "});",
      ],
      { encoding: "utf8" },
    );
    assert.equal(imported.status, 0, managerPath);
    assert.equal(imported.stdout, "", managerPath);
    assert.equal(imported.stderr, "", managerPath);
  }

  assert.equal(new Set(managerSources).size, 1);
});

test("direct server modules are terminal holds with non-executable source archives", () => {
  const archiveRoot = path.join(ROOT, "docs", "archive", "flameborn_operational_sources");
  const records = [
    {
      active: path.join(FLAMEBORN, "server.mjs"),
      archive: "flameborn_server.mjs.txt",
      size: 131827,
      sha256: "98211ee83fb6ac6cbbfead50aa0596a0e2a5577c08a4feb3699d105c1d49492b",
    },
    {
      active: path.join(FLAMEBORN, "runtime", "server.mjs"),
      archive: "flameborn_runtime_server.mjs.txt",
      size: 19487,
      sha256: "00d2370f390b01214d2e4a8c65f3e32ab8dd9d18c49e68dcc314351719b8ac5f",
    },
    {
      active: path.join(MURGE, "web_app", "server.mjs"),
      archive: "aureon_murge_web_server.mjs.txt",
      size: 77083,
      sha256: "e61ab8104ed21842444ebbeb4513bf7af745d0b23f4beec6881cceced06173fc",
    },
    {
      active: path.join(MURGE, "runtime", "server.mjs"),
      archive: "aureon_murge_runtime_server.mjs.txt",
      size: 22387,
      sha256: "e0edf3f2014bddc4a6a401bb7bd88f9331cc8a5838d7cc8f89112831b121f8fc",
    },
    {
      active: path.join(IMPORTED_MURGE, "server.mjs"),
      archive: "imported_aureon_murge_web_server.mjs.txt",
      size: 59886,
      sha256: "595c05517385babed64c34fc6c4b8bf4c7906d4981e2900d48f3855c9e408695",
    },
    {
      active: path.join(IMPORTED_MURGE, "runtime", "server.mjs"),
      archive: "imported_aureon_murge_runtime_server.mjs.txt",
      size: 19487,
      sha256: "00d2370f390b01214d2e4a8c65f3e32ab8dd9d18c49e68dcc314351719b8ac5f",
    },
  ];
  const archivePrefix = [
    "// Archived non-executable source snapshot. Do not rename to an executable extension.",
    "process.exit(2);",
    "/*",
    "",
  ].join("\n");
  const archiveSuffix = "*/\n";

  assert.deepEqual(
    fs.readdirSync(archiveRoot).sort(),
    records.map(({ archive }) => archive).sort(),
  );
  for (const record of records) {
    assert.equal(readText(record.active), IMMEDIATE_NODE_HOLD, record.active);
    const completed = spawnSync(process.execPath, [record.active], { encoding: "utf8" });
    assert.equal(completed.status, 2, record.active);
    assert.equal(completed.stdout, "", record.active);
    assert.equal(completed.stderr, "", record.active);

    assert.match(record.archive, /\.mjs\.txt$/);
    const archivePath = path.join(archiveRoot, record.archive);
    const archived = readText(archivePath);
    assert.ok(archived.startsWith(archivePrefix), record.archive);
    assert.ok(archived.endsWith(archiveSuffix), record.archive);
    const archivedProbe = spawnSync(process.execPath, [archivePath], { encoding: "utf8" });
    assert.equal(archivedProbe.status, 2, archivePath);
    assert.equal(archivedProbe.stdout, "", archivePath);
    assert.equal(archivedProbe.stderr, "", archivePath);
    const sourceBody = archived.slice(
      archivePrefix.length,
      archived.length - archiveSuffix.length,
    );
    assert.equal(Buffer.byteLength(sourceBody, "utf8"), record.size, record.archive);
    assert.equal(
      createHash("sha256").update(sourceBody).digest("hex"),
      record.sha256,
      record.archive,
    );
  }
});

test("runtime Dockerfiles build identical nonroot shell-free terminal HOLD images", () => {
  const dockerfiles = [
    path.join(FLAMEBORN, "runtime", "Dockerfile"),
    path.join(MURGE, "runtime", "Dockerfile"),
    path.join(IMPORTED_MURGE, "runtime", "Dockerfile"),
  ];
  const sources = dockerfiles.map(readText);
  assert.equal(new Set(sources).size, 1);

  for (const [index, source] of sources.entries()) {
    const owner = dockerfiles[index];
    assert.deepEqual(source.match(/^FROM .+$/gm), [
      "FROM gcc:14-bookworm AS hold-builder",
      "FROM scratch",
    ], owner);
    assert.match(source, /int main\(void\) \{ return 2; \}/, owner);
    assert.match(
      source,
      /COPY --from=hold-builder --chown=65532:65532 \/terminal-hold \/terminal-hold/,
      owner,
    );
    assert.match(source, /^USER 65532:65532$/m, owner);
    assert.match(source, /^ENTRYPOINT \["\/terminal-hold"\]$/m, owner);
    assert.doesNotMatch(
      source,
      /\b(?:apt-get|apk|curl|wget|sudo|bash|node|npm|python|git|nano|vim)\b/i,
      owner,
    );

    const runtimeStage = source.slice(source.lastIndexOf("FROM scratch"));
    assert.doesNotMatch(
      runtimeStage,
      /^(?:RUN|CMD|SHELL|ENV|EXPOSE|ADD|WORKDIR)\b/m,
      owner,
    );
  }
});

test("operator guide has no .env secret examples and keeps provider readback pending", () => {
  const guide = readText(
    path.join(FLAMEBORN, "CLOUDFLARE_WORKERS_DEV_SETUP.md"),
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

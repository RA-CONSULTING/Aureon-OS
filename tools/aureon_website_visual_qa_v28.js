#!/usr/bin/env node
"use strict";

const crypto = require("node:crypto");
const fs = require("node:fs");
const http = require("node:http");
const os = require("node:os");
const path = require("node:path");

const repoRoot = path.resolve(__dirname, "..");
const websiteRoot = path.join(repoRoot, "website");
const auditRoot = path.join(repoRoot, "docs", "audits");
const DEFAULT_ENGINES = Object.freeze(["chromium", "firefox", "webkit"]);
const SCREENSHOT_CAPTURE_SCOPE = Object.freeze([
  Object.freeze({
    viewportName: "desktop",
    routeNames: Object.freeze(["home", "funding", "investor", "publications", "research"]),
  }),
  Object.freeze({
    viewportName: "mobile",
    routeNames: Object.freeze(["home", "projects", "research", "contact"]),
  }),
]);

/*
 * These are release gates, not aspirational scores. They intentionally use
 * stable, documented limits that can be compared between runs. Transfer bytes
 * are a browser Performance API proxy and are labelled as such in the report.
 */
const PERFORMANCE_BUDGETS = Object.freeze({
  ttfbMs: 800,
  domContentLoadedMs: 2500,
  loadEventMs: 3500,
  lcpMs: 2500,
  cls: 0.1,
  requestCount: 80,
  transferProxyBytes: 3_000_000,
  longTaskTotalMs: 300,
});

/*
 * A page may safely defer below-fold layout/paint only when it reserves stable
 * document geometry. This policy is intentionally separate from the eight
 * release performance metrics: it is an additive rendering-integrity gate,
 * not a ninth metric or a relaxed performance budget.
 */
const DEFERRED_RENDER_GEOMETRY_POLICY = Object.freeze({
  viewport: Object.freeze({ width: 1440, height: 1000 }),
  epsilonPx: 2,
  candidateLimit: 48,
  method: "computed content-visibility:auto before/after deterministic full-page reveal",
});

const ACCESSIBILITY_THRESHOLDS = Object.freeze({
  normalTextContrast: 4.5,
  largeTextContrast: 3,
  largeTextPx: 24,
  largeBoldTextPx: 18.66,
  largeBoldWeight: 700,
  minimumTargetPx: 24,
  zoomPercent: 200,
  zoomReferenceViewport: { width: 1440, height: 1000 },
});

const contentTypes = {
  ".css": "text/css; charset=utf-8",
  ".gif": "image/gif",
  ".html": "text/html; charset=utf-8",
  ".ico": "image/x-icon",
  ".jpeg": "image/jpeg",
  ".jpg": "image/jpeg",
  ".js": "text/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".png": "image/png",
  ".svg": "image/svg+xml",
  ".webmanifest": "application/manifest+json; charset=utf-8",
  ".webp": "image/webp",
  ".woff": "font/woff",
  ".woff2": "font/woff2",
  ".xml": "application/xml; charset=utf-8",
};

const routes = [
  ["home", "/", ".institutional-hero"],
  ["about", "/about/", ".company-hero"],
  ["community", "/community/", ".community-hero"],
  ["contact", "/contact/", ".engagement-hero"],
  ["diligence", "/diligence/", ".diligence-hero"],
  ["funding", "/funding/", ".capital-control-hero"],
  ["investor", "/funding/investor-deck/", ".investor-room-hero"],
  ["live", "/live/", ".live-hero"],
  ["projects", "/projects/", ".portfolio-hero"],
  ["publications", "/publications/", ".evidence-room-hero"],
  ["research", "/research/", ".research-evidence-hero"],
  ["journal", "/research/journal/", ".journal-hero"],
  ["updates", "/updates/", ".updates-hero"],
  ["vision", "/vision/", ".vision-horizon-hero"],
];

const viewports = [
  { name: "reflow", width: 320, height: 800, heroMaxFactor: 2.65, h1MinPx: 28 },
  { name: "compact", width: 360, height: 800, heroMaxFactor: 2.4, h1MinPx: 30 },
  { name: "mobile", width: 390, height: 844, heroMaxFactor: 2.2, h1MinPx: 30 },
  { name: "tablet", width: 768, height: 1024, heroMaxFactor: 1.8, h1MinPx: 36 },
  { name: "laptop", width: 1280, height: 800, heroMaxFactor: 1.55, h1MinPx: 42 },
  { name: "desktop", width: 1440, height: 1000, heroMaxFactor: 1.25, h1MinPx: 42 },
  { name: "wide", width: 1920, height: 1080, heroMaxFactor: 1.25, h1MinPx: 42 },
];

const interactionCases = [
  {
    name: "projects packet inspector",
    routeName: "projects",
    route: "/projects/",
    tab: '[data-packet-layer-tab="classify"]',
    selected: "[data-packet-layer-tab][aria-selected=true]",
    panel: "[data-packet-layer-panel].is-active",
    selectedKey: "packetLayerTab",
    panelKey: "packetLayerPanel",
    clickExpected: "classify",
    keyExpected: "review",
  },
  {
    name: "live evidence packet",
    routeName: "live",
    route: "/live/",
    tab: '[data-freshness-tab="repository"]',
    selected: "[data-freshness-tab][aria-selected=true]",
    panel: "[data-freshness-panel].is-active",
    selectedKey: "freshnessTab",
    panelKey: "freshnessPanel",
    clickExpected: "repository",
    keyExpected: "research",
  },
  {
    name: "engagement router",
    routeName: "contact",
    route: "/contact/",
    tab: '[data-engagement-route-tab="research"]',
    selected: "[data-engagement-route-tab][aria-selected=true]",
    panel: "[data-engagement-route-panel].is-active",
    selectedKey: "engagementRouteTab",
    panelKey: "engagementRoutePanel",
    clickExpected: "research",
    keyExpected: "investor",
  },
  {
    name: "research proof path",
    routeName: "research",
    route: "/research/",
    tab: '[data-research-stage-tab="test"]',
    selected: "[data-research-stage-tab][aria-selected=true]",
    panel: "[data-research-stage-panel].is-active",
    selectedKey: "researchStageTab",
    panelKey: "researchStagePanel",
    clickExpected: "test",
    keyExpected: "review",
  },
];

function usage() {
  return `Usage:
  node tools/aureon_website_visual_qa_v28.js [base-url] [options]

Options:
  --base-url URL            Audit an already-running target instead of the
                            built-in server. The local website tree is still
                            hashed and recorded.
  --engines LIST            Comma-separated engines. Default:
                            chromium,firefox,webkit. Selecting one engine is
                            reported as explicit single-engine coverage, never
                            as a browser matrix.
  --routes LIST             Comma-separated route names. Default: all.
  --viewports LIST          Comma-separated viewport names. Default: all seven.
  --help                    Show this help.

Environment:
  AUREON_QA_ENGINES
  AUREON_CHROMIUM_EXECUTABLE
  AUREON_FIREFOX_EXECUTABLE
  AUREON_WEBKIT_EXECUTABLE
  AUREON_BROWSER_EXECUTABLE (legacy Chromium override)

Missing requested engines are recorded as UNSUPPORTED and fail closed. To run a
deliberate single-engine diagnostic, pass --engines=chromium explicitly.
`;
}

function splitList(value) {
  return String(value || "")
    .split(",")
    .map((item) => item.trim().toLowerCase())
    .filter(Boolean);
}

function normalizedAuditBaseUrl(value) {
  let target;
  try {
    target = new URL(value);
  } catch {
    throw new Error("--base-url must be a valid HTTP(S) origin.");
  }
  if (
    !["http:", "https:"].includes(target.protocol) ||
    target.username ||
    target.password ||
    target.search ||
    target.hash ||
    target.pathname !== "/"
  ) {
    throw new Error(
      "--base-url must be a credential-free HTTP(S) origin without a path, query, or fragment.",
    );
  }
  return target.origin;
}

function parseCli(argv, environment = process.env) {
  const options = {
    baseUrl: "",
    engines: splitList(environment.AUREON_QA_ENGINES),
    engineSelectionExplicit: Boolean(environment.AUREON_QA_ENGINES),
    routeNames: [],
    viewportNames: [],
    help: false,
  };
  const takeValue = (argument, index) => {
    const equals = argument.indexOf("=");
    if (equals >= 0) return [argument.slice(equals + 1), index];
    if (index + 1 >= argv.length) throw new Error(`${argument} requires a value`);
    return [argv[index + 1], index + 1];
  };

  for (let index = 0; index < argv.length; index += 1) {
    const argument = argv[index];
    if (argument === "--help" || argument === "-h") {
      options.help = true;
      continue;
    }
    if (argument === "--base-url" || argument.startsWith("--base-url=")) {
      const [value, nextIndex] = takeValue(argument, index);
      options.baseUrl = value.replace(/\/+$/, "");
      index = nextIndex;
      continue;
    }
    if (argument === "--engines" || argument.startsWith("--engines=")) {
      const [value, nextIndex] = takeValue(argument, index);
      options.engines = splitList(value);
      options.engineSelectionExplicit = true;
      index = nextIndex;
      continue;
    }
    if (argument === "--routes" || argument.startsWith("--routes=")) {
      const [value, nextIndex] = takeValue(argument, index);
      options.routeNames = splitList(value);
      index = nextIndex;
      continue;
    }
    if (argument === "--viewports" || argument.startsWith("--viewports=")) {
      const [value, nextIndex] = takeValue(argument, index);
      options.viewportNames = splitList(value);
      index = nextIndex;
      continue;
    }
    if (argument.startsWith("-")) throw new Error(`Unknown option: ${argument}`);
    if (options.baseUrl) throw new Error(`Unexpected positional argument: ${argument}`);
    options.baseUrl = argument.replace(/\/+$/, "");
  }

  if (!options.engines.length) options.engines = [...DEFAULT_ENGINES];
  const invalidEngines = options.engines.filter((name) => !DEFAULT_ENGINES.includes(name));
  if (invalidEngines.length) {
    throw new Error(`Unknown browser engine(s): ${invalidEngines.join(", ")}`);
  }
  if (new Set(options.engines).size !== options.engines.length) {
    throw new Error("Browser engine list contains duplicates");
  }

  const knownRoutes = new Set(routes.map(([name]) => name));
  const invalidRoutes = options.routeNames.filter((name) => !knownRoutes.has(name));
  if (invalidRoutes.length) throw new Error(`Unknown route(s): ${invalidRoutes.join(", ")}`);

  const knownViewports = new Set(viewports.map(({ name }) => name));
  const invalidViewports = options.viewportNames.filter((name) => !knownViewports.has(name));
  if (invalidViewports.length) {
    throw new Error(`Unknown viewport(s): ${invalidViewports.join(", ")}`);
  }
  if (options.baseUrl) options.baseUrl = normalizedAuditBaseUrl(options.baseUrl);
  return options;
}

function runtimeModuleDirectories() {
  const directories = [];
  const configured = String(process.env.AUREON_QA_NODE_MODULES || "")
    .split(path.delimiter)
    .map((item) => item.trim())
    .filter(Boolean);
  directories.push(...configured);
  const localQaDependencies = path.join(
    os.tmpdir(),
    "aureon-qa-deps",
    "node_modules",
  );
  if (fs.existsSync(localQaDependencies)) directories.push(localQaDependencies);
  const runtimeRoot = path.join(os.homedir(), ".cache", "codex-runtimes");
  if (fs.existsSync(runtimeRoot)) {
    for (const runtime of fs.readdirSync(runtimeRoot).sort()) {
      directories.push(path.join(runtimeRoot, runtime, "dependencies", "node", "node_modules"));
    }
  }
  return [...new Set(directories)];
}

function loadPlaywright() {
  const candidates = [
    "playwright",
    "@playwright/test",
    path.join(repoRoot, "frontend", "node_modules", "playwright"),
    path.join(repoRoot, "frontend", "node_modules", "@playwright", "test"),
  ];
  for (const modules of runtimeModuleDirectories()) {
    candidates.push(path.join(modules, "playwright"));
    candidates.push(path.join(modules, "@playwright", "test"));
  }
  for (const candidate of candidates) {
    try {
      const loaded = require(candidate);
      if (loaded?.chromium) return { playwright: loaded, source: candidate };
    } catch {
      // Try the next declared, repository, or bundled runtime location.
    }
  }
  throw new Error(
    "Playwright is unavailable. Run `npm ci --prefix frontend` or set NODE_PATH to a runtime containing Playwright.",
  );
}

function loadOptionalAxe() {
  const candidates = [
    "axe-core",
    path.join(repoRoot, "frontend", "node_modules", "axe-core"),
    ...runtimeModuleDirectories().map((modules) => path.join(modules, "axe-core")),
  ];
  for (const candidate of candidates) {
    try {
      const loaded = require(candidate);
      if (typeof loaded?.source === "string") {
        return { source: loaded.source, module: candidate, version: loaded.version || null };
      }
    } catch {
      // axe is optional; computed checks still run when it is absent.
    }
  }
  return null;
}

function assessAxeEvidence(result) {
  const violations = Array.isArray(result?.violations) ? result.violations : [];
  const incomplete = Array.isArray(result?.incomplete) ? result.incomplete : [];
  const rules = [...violations, ...incomplete];
  const completeNodeEvidence = rules.every(
    (item) =>
      Number.isInteger(item.nodeCount) &&
      item.nodeCount >= 0 &&
      Array.isArray(item.nodes) &&
      item.nodeCount === item.nodes.length,
  );
  return {
    completeNodeEvidence,
    violationRuleCount: violations.length,
    violationNodeCount: violations.reduce((total, item) => total + item.nodeCount, 0),
    incompleteRuleCount: incomplete.length,
    incompleteNodeCount: incomplete.reduce((total, item) => total + item.nodeCount, 0),
    pass:
      completeNodeEvidence &&
      violations.length === 0 &&
      incomplete.length === 0,
  };
}

function sha256Buffer(value) {
  return crypto.createHash("sha256").update(value).digest("hex");
}

function sha256File(filePath) {
  return sha256Buffer(fs.readFileSync(filePath));
}

function listFiles(root) {
  const output = [];
  const visit = (current) => {
    for (const entry of fs.readdirSync(current, { withFileTypes: true })) {
      const absolute = path.join(current, entry.name);
      if (entry.isDirectory()) {
        visit(absolute);
      } else if (entry.isFile()) {
        const stats = fs.lstatSync(absolute);
        if (stats.nlink !== 1) {
          throw new Error(
            `Website source tree contains an unsupported hardlinked file: ${absolute}`,
          );
        }
        output.push(absolute);
      } else if (entry.isSymbolicLink()) {
        throw new Error(`Website source tree contains an unsupported symbolic link: ${absolute}`);
      }
    }
  };
  visit(root);
  /*
   * The snapshot contract is consumed by Python candidate-review controls as
   * well as this Node runner. `localeCompare()` is locale/collation-sensitive
   * (for example, it can order lowercase font files before `LICENSES`), while
   * the contract says paths are sorted. Use explicit code-unit ordering after
   * path normalisation so every consumer hashes the same inventory.
   */
  return output.sort((left, right) => {
    const leftPath = path.relative(root, left).split(path.sep).join("/");
    const rightPath = path.relative(root, right).split(path.sep).join("/");
    if (leftPath < rightPath) return -1;
    if (leftPath > rightPath) return 1;
    return 0;
  });
}

function snapshotWebsiteTree(root = websiteRoot) {
  const files = listFiles(root).map((absolute) => {
    const bytes = fs.statSync(absolute).size;
    const relativePath = path.relative(root, absolute).split(path.sep).join("/");
    return { path: relativePath, bytes, sha256: sha256File(absolute) };
  });
  const treeInput = files
    .map((file) => `${file.path}\0${file.bytes}\0${file.sha256}\n`)
    .join("");
  return {
    algorithm: "sha256(path NUL bytes NUL file_sha256 LF), paths sorted",
    sha256: sha256Buffer(Buffer.from(treeInput, "utf8")),
    fileCount: files.length,
    totalBytes: files.reduce((total, file) => total + file.bytes, 0),
    files,
  };
}

function safeStaticPath(sourceRoot, requestUrl) {
  const pathname = decodeURIComponent(new URL(requestUrl, "http://localhost").pathname);
  const relative = pathname.endsWith("/") ? `${pathname}index.html` : pathname;
  const root = path.resolve(sourceRoot);
  const candidate = path.resolve(root, `.${relative}`);
  const rootWithSeparator = `${root}${path.sep}`;
  return candidate === root || candidate.startsWith(rootWithSeparator)
    ? candidate
    : null;
}

async function startStaticServer(sourceRoot = websiteRoot) {
  const root = path.resolve(sourceRoot);
  const server = http.createServer((request, response) => {
    const target = safeStaticPath(root, request.url || "/");
    if (!target || !fs.existsSync(target) || !fs.statSync(target).isFile()) {
      response.writeHead(404, { "content-type": "text/plain; charset=utf-8" });
      response.end("Not found");
      return;
    }
    response.writeHead(200, {
      "content-type": contentTypes[path.extname(target).toLowerCase()] || "application/octet-stream",
      "cache-control": "no-store",
    });
    fs.createReadStream(target).pipe(response);
  });
  await new Promise((resolve, reject) => {
    server.once("error", reject);
    server.listen(0, "127.0.0.1", resolve);
  });
  const address = server.address();
  return {
    server,
    baseUrl: `http://127.0.0.1:${address.port}`,
  };
}

function auditedUrl(baseUrl, stamp, route, label) {
  const separator = route.includes("?") ? "&" : "?";
  return `${baseUrl}${route}${separator}visualqa=${encodeURIComponent(`${stamp}-${label}`)}`;
}

async function settle(page) {
  await page.waitForLoadState("domcontentloaded");
  await page.evaluate(async () => {
    if (document.fonts?.ready) await document.fonts.ready;
    await new Promise((resolve) =>
      requestAnimationFrame(() => requestAnimationFrame(resolve)),
    );
  });
  await page.waitForTimeout(250);
}

async function revealFullPage(page) {
  return page.evaluate(async () => {
    const pause = () =>
      new Promise((resolve) =>
        requestAnimationFrame(() => requestAnimationFrame(resolve)),
      );
    const step = Math.max(240, Math.round(window.innerHeight * 0.75));
    const maxSweeps = 8;
    let revealedUntil = 0;
    let completed = false;
    let sweepCount = 0;
    for (let sweep = 0; sweep < maxSweeps; sweep += 1) {
      sweepCount = sweep + 1;
      const maximum = Math.max(
        0,
        document.documentElement.scrollHeight - window.innerHeight,
      );
      for (let top = revealedUntil; top < maximum; top += step) {
        window.scrollTo(0, Math.min(top, maximum));
        await pause();
      }
      window.scrollTo(0, maximum);
      await pause();
      const expandedMaximum = Math.max(
        0,
        document.documentElement.scrollHeight - window.innerHeight,
      );
      if (expandedMaximum <= maximum) {
        completed = true;
        break;
      }
      revealedUntil = maximum;
    }
    window.scrollTo(0, 0);
    await pause();
    return {
      completed,
      sweeps: sweepCount,
      maxSweeps,
      finalScrollHeight: Math.round(document.documentElement.scrollHeight),
    };
  });
}

function isAllowedExternalFailure(route, url) {
  return (
    route === "/live/" &&
    url === "https://api.github.com/repos/RA-CONSULTING/Aureon-OS"
  );
}

function isExpectedClientCancellation(request) {
  const errorText = request.failure()?.errorText || "";
  const resourceType = typeof request.resourceType === "function"
    ? request.resourceType()
    : "";
  return (
    resourceType !== "document" &&
    ["Load request cancelled", "net::ERR_ABORTED", "NS_BINDING_ABORTED"].includes(errorText)
  );
}

function safeDiagnosticUrl(value) {
  try {
    const resolved = new URL(String(value || ""));
    if (!["http:", "https:"].includes(resolved.protocol)) {
      return `${resolved.protocol}//redacted`;
    }
    return `${resolved.origin}${resolved.pathname}`;
  } catch {
    return "invalid-url";
  }
}

function safeDiagnosticText(value) {
  return String(value || "")
    .replace(
      /\b[a-z][a-z0-9+.-]*:\/\/[^\s<>"'`)]+/gi,
      (candidate) => safeDiagnosticUrl(candidate),
    )
    .replace(/\b(?:data|blob):[^\s<>"'`)]+/gi, (candidate) =>
      safeDiagnosticUrl(candidate),
    );
}

function attachPageDiagnostics(page, route) {
  const errors = [];
  const warnings = [];
  const resourceFailures = [];
  const allowedResourceFailures = [];
  const clientCancellations = [];
  const onConsole = (message) => {
    const text = safeDiagnosticText(message.text());
    const optionalLiveFetchMessage =
      route === "/live/" &&
      message.type() === "error" &&
      text.startsWith("Failed to load resource:");
    if (message.type() === "error" && !optionalLiveFetchMessage) {
      errors.push(`console: ${text}`);
    }
    if (message.type() === "warning") warnings.push(`console: ${text}`);
  };
  const onPageError = (error) =>
    errors.push(`page: ${safeDiagnosticText(error.message)}`);
  const onRequestFailed = (request) => {
    const failure =
      `request: ${safeDiagnosticUrl(request.url())} ` +
      `(${safeDiagnosticText(request.failure()?.errorText || "failed")})`;
    if (isExpectedClientCancellation(request)) {
      clientCancellations.push(failure);
    } else if (isAllowedExternalFailure(route, request.url())) {
      allowedResourceFailures.push(failure);
    } else {
      resourceFailures.push(failure);
    }
  };
  const onResponse = (response) => {
    if (response.status() < 400) return;
    const failure = `response: ${safeDiagnosticUrl(response.url())} (${response.status()})`;
    if (isAllowedExternalFailure(route, response.url())) {
      allowedResourceFailures.push(
        `${failure}; the public-source widget must expose its unavailable fallback`,
      );
    } else {
      resourceFailures.push(failure);
    }
  };
  page.on("console", onConsole);
  page.on("pageerror", onPageError);
  page.on("requestfailed", onRequestFailed);
  page.on("response", onResponse);
  return {
    errors,
    warnings,
    resourceFailures,
    allowedResourceFailures,
    clientCancellations,
    detach() {
      page.off("console", onConsole);
      page.off("pageerror", onPageError);
      page.off("requestfailed", onRequestFailed);
      page.off("response", onResponse);
    },
  };
}

function attachEngineDiagnostics(page) {
  const warnings = [];
  const errors = [];
  const clientCancellations = [];
  const currentRoute = () => {
    try {
      return new URL(page.url()).pathname;
    } catch {
      return "";
    }
  };
  const onConsole = (message) => {
    const text = safeDiagnosticText(message.text());
    const optionalLiveFetchMessage =
      currentRoute() === "/live/" &&
      message.type() === "error" &&
      text.startsWith("Failed to load resource:");
    if (message.type() === "error" && !optionalLiveFetchMessage) {
      errors.push(`console: ${text}`);
    }
    if (message.type() === "warning") warnings.push(`console: ${text}`);
  };
  const onPageError = (error) =>
    errors.push(`page: ${safeDiagnosticText(error.message)}`);
  const onRequestFailed = (request) => {
    if (isExpectedClientCancellation(request)) {
      clientCancellations.push(
        `request: ${safeDiagnosticUrl(request.url())} ` +
          `(${safeDiagnosticText(request.failure()?.errorText || "failed")})`,
      );
    } else if (!isAllowedExternalFailure(currentRoute(), request.url())) {
      errors.push(
        `request: ${safeDiagnosticUrl(request.url())} ` +
          `(${safeDiagnosticText(request.failure()?.errorText || "failed")})`,
      );
    }
  };
  const onResponse = (response) => {
    if (
      response.status() >= 400 &&
      !isAllowedExternalFailure(currentRoute(), response.url())
    ) {
      errors.push(`response: ${safeDiagnosticUrl(response.url())} (${response.status()})`);
    }
  };
  page.on("console", onConsole);
  page.on("pageerror", onPageError);
  page.on("requestfailed", onRequestFailed);
  page.on("response", onResponse);
  return {
    warnings,
    errors,
    clientCancellations,
    detach() {
      page.off("console", onConsole);
      page.off("pageerror", onPageError);
      page.off("requestfailed", onRequestFailed);
      page.off("response", onResponse);
    },
  };
}

function canonicalJson(value) {
  if (value === null || typeof value === "boolean" || typeof value === "string") {
    return JSON.stringify(value);
  }
  if (typeof value === "number") {
    if (!Number.isFinite(value)) throw new Error("Canonical JSON cannot encode a non-finite number.");
    return JSON.stringify(value);
  }
  if (Array.isArray(value)) return `[${value.map(canonicalJson).join(",")}]`;
  if (value && typeof value === "object") {
    return `{${Object.keys(value)
      .sort()
      .map((key) => `${JSON.stringify(key)}:${canonicalJson(value[key])}`)
      .join(",")}}`;
  }
  throw new Error("Canonical JSON accepts only JSON values.");
}

function canonicalJsonSha256(value) {
  return sha256Buffer(Buffer.from(canonicalJson(value), "utf8")).toUpperCase();
}

function normalizedText(value) {
  return typeof value === "string" ? value.trim().replace(/\s+/g, " ") : "";
}

function normalizedExpectedWebpPath(value) {
  if (typeof value !== "string" || !value.trim() || value.includes("\\")) return "";
  const candidate = value.trim();
  if (
    candidate.startsWith("/") ||
    !candidate.startsWith("website/") ||
    candidate.includes("?") ||
    candidate.includes("#")
  ) {
    return "";
  }
  const pieces = candidate.split("/");
  if (pieces.some((part) => !part || part === "." || part === "..")) return "";
  const publicPath = pieces.slice(1).join("/");
  if (!publicPath.toLowerCase().endsWith(".webp")) return "";
  return `/${publicPath}`;
}

function normalizedObservedWebpPath(value, pageOrigin) {
  if (typeof value !== "string" || !value.trim()) return "";
  try {
    const expectedOrigin = new URL(pageOrigin).origin;
    const resolved = new URL(value, expectedOrigin);
    if (
      resolved.origin !== expectedOrigin ||
      !["http:", "https:"].includes(resolved.protocol) ||
      resolved.username ||
      resolved.password ||
      resolved.search ||
      resolved.hash ||
      !resolved.pathname.toLowerCase().endsWith(".webp")
    ) {
      return "";
    }
    return resolved.pathname;
  } catch {
    return "";
  }
}

function normalizedPublicPostUrl(value) {
  if (typeof value !== "string" || !value.trim()) return "";
  try {
    const resolved = new URL(value);
    if (
      resolved.protocol !== "https:" ||
      !(
        resolved.hostname === "substack.com" ||
        resolved.hostname.endsWith(".substack.com")
      ) ||
      !/^\/p\/[a-z0-9][a-z0-9-]{2,160}$/.test(resolved.pathname) ||
      resolved.username ||
      resolved.password ||
      resolved.search ||
      resolved.hash
    ) {
      return "";
    }
    return resolved.href;
  } catch {
    return "";
  }
}

function editorialExpectationCore(expected) {
  if (!expected || Array.isArray(expected) || typeof expected !== "object") return null;
  const expectedKeys = new Set([
    "asset_id",
    "route_scope",
    "destination_path",
    "surface_id",
    "public_post_url",
    "variants",
    "alt",
    "caption",
    "credit",
    "route_asset_capsule_sha256",
    "expected_binding_sha256",
    "observation_sha256",
    "surface_binding_sha256",
  ]);
  const variantKeys = new Set([
    "role",
    "path",
    "sha256",
    "media_type",
    "width",
    "height",
  ]);
  const hasExactKeys = (value, keys) => {
    const actual = Object.keys(value);
    return actual.length === keys.size && actual.every((key) => keys.has(key));
  };
  const variants = Array.isArray(expected.variants) ? expected.variants : [];
  const small = variants.find((item) => item?.role === "small");
  const large = variants.find((item) => item?.role === "large");
  const validVariant = (variant) =>
    variant &&
    typeof variant === "object" &&
    !Array.isArray(variant) &&
    hasExactKeys(variant, variantKeys) &&
    normalizedExpectedWebpPath(variant.path) &&
    variant.media_type === "image/webp" &&
    /^[a-f0-9]{64}$/i.test(String(variant.sha256 || "")) &&
    Number.isInteger(variant.width) &&
    variant.width > 0 &&
    Number.isInteger(variant.height) &&
    variant.height > 0;
  if (
    !hasExactKeys(expected, expectedKeys) ||
    !/^[a-z0-9][a-z0-9-]{2,95}$/.test(String(expected.asset_id || "")) ||
    !/^[a-z0-9][a-z0-9-]{2,95}$/.test(String(expected.surface_id || "")) ||
    typeof expected.route_scope !== "string" ||
    !/^\/(?:[a-z0-9-]+\/)*$/.test(expected.route_scope) ||
    typeof expected.destination_path !== "string" ||
    !/^website\/(?:[a-z0-9._-]+\/)*[a-z0-9._-]+$/.test(expected.destination_path) ||
    !normalizedPublicPostUrl(expected.public_post_url) ||
    normalizedPublicPostUrl(expected.public_post_url) !== expected.public_post_url ||
    variants.length !== 2 ||
    !validVariant(small) ||
    !validVariant(large) ||
    !normalizedText(expected.alt) ||
    !normalizedText(expected.caption) ||
    !normalizedText(expected.credit) ||
    ![
      expected.route_asset_capsule_sha256,
      expected.expected_binding_sha256,
      expected.observation_sha256,
      expected.surface_binding_sha256,
    ].every((value) => /^[a-f0-9]{64}$/i.test(String(value || "")))
  ) {
    return null;
  }
  return {
    surfaceId: expected.surface_id,
    publicPostUrl: normalizedPublicPostUrl(expected.public_post_url),
    small: {
      path: normalizedExpectedWebpPath(small.path),
      width: small.width,
      height: small.height,
    },
    large: {
      path: normalizedExpectedWebpPath(large.path),
      width: large.width,
      height: large.height,
    },
    alt: normalizedText(expected.alt),
    caption: normalizedText(expected.caption),
    credit: normalizedText(expected.credit),
  };
}

function assessEditorialSurfaceObservations(
  observations,
  pageOrigin,
  expectedSurfaces = [],
) {
  const failures = [];
  if (!Array.isArray(observations) || !Array.isArray(expectedSurfaces)) {
    return {
      pass: false,
      expectedSurfaces: Array.isArray(expectedSurfaces) ? expectedSurfaces : [],
      expectedSurfacesSha256: canonicalJsonSha256(
        Array.isArray(expectedSurfaces) ? expectedSurfaces : [],
      ),
      observedSurfaces: [],
      expectedSurfaceCount: Array.isArray(expectedSurfaces)
        ? expectedSurfaces.length
        : 0,
      observedSurfaceCount: Array.isArray(observations) ? observations.length : 0,
      surfaceCount: Array.isArray(observations) ? observations.length : 0,
      duplicateSurfaceIds: [],
      failures: [
        ...(Array.isArray(observations) ? [] : ["observations-not-an-array"]),
        ...(Array.isArray(expectedSurfaces) ? [] : ["expectations-not-an-array"]),
      ],
    };
  }

  const expectedById = new Map();
  const expectedCores = new Map();
  expectedSurfaces.forEach((expected, index) => {
    const core = editorialExpectationCore(expected);
    if (!core) {
      failures.push(`expectation-${index}:invalid`);
      return;
    }
    if (expectedById.has(core.surfaceId)) {
      failures.push(`${core.surfaceId}:expected-surface-id-unique`);
      return;
    }
    expectedById.set(core.surfaceId, expected);
    expectedCores.set(core.surfaceId, core);
  });

  const idCounts = new Map();
  for (const item of observations) {
    const id =
      item && typeof item === "object" && typeof item.surfaceId === "string"
        ? item.surfaceId
        : "";
    idCounts.set(id, (idCounts.get(id) || 0) + 1);
  }
  const duplicateSurfaceIds = [...idCounts.entries()]
    .filter(([id, count]) => !id || count !== 1)
    .map(([id]) => (/^[a-z0-9][a-z0-9-]{2,95}$/.test(id) ? id : "invalid-surface-id"))
    .sort();
  const observedIds = new Set(
    [...idCounts.keys()].filter((id) => /^[a-z0-9][a-z0-9-]{2,95}$/.test(id)),
  );
  for (const expectedId of expectedById.keys()) {
    if (!observedIds.has(expectedId)) failures.push(`${expectedId}:surface-missing`);
  }
  for (const observedId of observedIds) {
    if (!expectedById.has(observedId)) failures.push(`${observedId}:surface-unexpected`);
  }
  if (expectedSurfaces.length !== observations.length) {
    failures.push("surface-set-count");
  }

  const observedSurfaces = observations.map((raw, index) => {
    const item = raw && typeof raw === "object" ? raw : {};
    const rawSurfaceId = typeof item.surfaceId === "string" ? item.surfaceId : "";
    const safeSurfaceId = /^[a-z0-9][a-z0-9-]{2,95}$/.test(rawSurfaceId)
      ? rawSurfaceId
      : `surface-${index}`;
    const expected = expectedCores.get(rawSurfaceId);
    const image = item.image && typeof item.image === "object" ? item.image : {};
    const sources = Array.isArray(item.sources) ? item.sources : [];
    const surfaceFailures = [];
    const anchorUrls = Array.isArray(item.anchorUrls) ? item.anchorUrls : [];
    const safePostUrls = anchorUrls.map(normalizedPublicPostUrl);
    const srcsetCandidates = sources.flatMap((source) =>
      source && typeof source === "object" && typeof source.srcset === "string"
        ? source.srcset
            .split(",")
            .map((candidate) => candidate.trim().split(/\s+/, 1)[0])
            .filter(Boolean)
        : [],
    );
    const sourcePaths = srcsetCandidates
      .map((value) => normalizedObservedWebpPath(value, pageOrigin))
      .filter(Boolean);
    const srcPath = normalizedObservedWebpPath(image.src, pageOrigin);
    const currentSrcPath = normalizedObservedWebpPath(image.currentSrc, pageOrigin);
    const publicPostUrl =
      safePostUrls.length === 1 && safePostUrls[0] ? safePostUrls[0] : "";
    const captionMatches =
      Boolean(expected) && normalizedText(item.caption) === expected.caption;
    const altMatches =
      Boolean(expected) && normalizedText(image.alt) === expected.alt;
    const declaredWidth = Number.isInteger(image.declaredWidth)
      ? image.declaredWidth
      : 0;
    const declaredHeight = Number.isInteger(image.declaredHeight)
      ? image.declaredHeight
      : 0;
    const naturalWidth = Number.isFinite(image.naturalWidth) ? image.naturalWidth : 0;
    const naturalHeight = Number.isFinite(image.naturalHeight) ? image.naturalHeight : 0;
    const currentVariant = expected
      ? [expected.small, expected.large].find((variant) => variant.path === currentSrcPath)
      : null;

    if (!expected) surfaceFailures.push("surface-unexpected");
    if (!/^[a-z0-9][a-z0-9-]{2,95}$/.test(rawSurfaceId)) {
      surfaceFailures.push("surface-id");
    }
    if (idCounts.get(rawSurfaceId) !== 1) surfaceFailures.push("surface-id-unique");
    if (item.visible !== true) surfaceFailures.push("surface-visible");
    if (item.pictureCount !== 1) surfaceFailures.push("picture-count");
    if (item.imageCount !== 1) surfaceFailures.push("image-count");
    if (item.anchorCount !== 1) surfaceFailures.push("anchor-count");
    if (item.figcaptionCount !== 1) surfaceFailures.push("figcaption-count");
    if (item.nestedSurfaceCount !== 0 || item.hasSurfaceAncestor === true) {
      surfaceFailures.push("surface-nesting");
    }
    if (
      !expected ||
      anchorUrls.length !== 1 ||
      safePostUrls.some((url) => !url) ||
      publicPostUrl !== expected.publicPostUrl
    ) {
      surfaceFailures.push("public-post-url");
    }
    if (
      image.complete !== true ||
      naturalWidth <= 0 ||
      naturalHeight <= 0 ||
      !currentVariant ||
      naturalWidth !== currentVariant.width ||
      naturalHeight !== currentVariant.height
    ) {
      surfaceFailures.push("image-decode-and-dimensions");
    }
    if (
      image.visible !== true ||
      !Number.isFinite(image.renderedWidth) ||
      image.renderedWidth <= 0 ||
      !Number.isFinite(image.renderedHeight) ||
      image.renderedHeight <= 0
    ) {
      surfaceFailures.push("image-visible");
    }
    if (!expected || !srcPath || srcPath !== expected.large.path) {
      surfaceFailures.push("image-src-path");
    }
    if (!expected || !currentSrcPath || !currentVariant) {
      surfaceFailures.push("image-current-src-path");
    }
    if (!expected || declaredWidth !== expected.large.width || declaredHeight !== expected.large.height) {
      surfaceFailures.push("image-declared-dimensions");
    }
    if (!altMatches) surfaceFailures.push("image-alt");
    if (
      !expected ||
      sources.length !== 1 ||
      srcsetCandidates.length !== 1 ||
      sourcePaths.length !== srcsetCandidates.length ||
      sourcePaths.length !== 1 ||
      sourcePaths[0] !== expected.small.path
    ) {
      surfaceFailures.push("responsive-source-path");
    }
    if (!captionMatches || item.captionVisible !== true) {
      surfaceFailures.push("caption");
    }
    if (item.creditMatchCount !== 1 || item.creditVisible !== true) {
      surfaceFailures.push("credit");
    }
    for (const reason of surfaceFailures) {
      failures.push(`${safeSurfaceId}:${reason}`);
    }
    return {
      surfaceId: safeSurfaceId,
      visible: item.visible === true,
      pictureCount: Number.isInteger(item.pictureCount) ? item.pictureCount : 0,
      imageCount: Number.isInteger(item.imageCount) ? item.imageCount : 0,
      anchorCount: Number.isInteger(item.anchorCount) ? item.anchorCount : 0,
      figcaptionCount: Number.isInteger(item.figcaptionCount) ? item.figcaptionCount : 0,
      nestedSurfaceCount: Number.isInteger(item.nestedSurfaceCount)
        ? item.nestedSurfaceCount
        : 0,
      publicPostUrl,
      captionMatches,
      captionVisible: item.captionVisible === true,
      creditMatchCount: Number.isInteger(item.creditMatchCount)
        ? item.creditMatchCount
        : 0,
      creditVisible: item.creditVisible === true,
      image: {
        srcPath,
        currentSrcPath,
        altMatches,
        complete: image.complete === true,
        naturalWidth,
        naturalHeight,
        declaredWidth,
        declaredHeight,
        renderedWidth: Number.isFinite(image.renderedWidth) ? image.renderedWidth : 0,
        renderedHeight: Number.isFinite(image.renderedHeight) ? image.renderedHeight : 0,
        visible: image.visible === true,
      },
      sourcePaths,
      failures: surfaceFailures,
      pass: surfaceFailures.length === 0,
    };
  });
  return {
    pass: failures.length === 0,
    expectedSurfaces,
    expectedSurfacesSha256: canonicalJsonSha256(expectedSurfaces),
    observedSurfaces,
    expectedSurfaceCount: expectedSurfaces.length,
    observedSurfaceCount: observedSurfaces.length,
    surfaceCount: observedSurfaces.length,
    duplicateSurfaceIds,
    failures,
  };
}

async function readRoute(page, runtime, name, route, heroSelector, viewport) {
  const expectedSurfaces = runtime.editorialSurfaceExpectations.filter(
    (item) => item.route_scope === route,
  );
  const diagnostics = attachPageDiagnostics(page, route);
  const response = await page.goto(
    auditedUrl(runtime.baseUrl, runtime.stamp, route, `${viewport.name}-${name}`),
    { waitUntil: "domcontentloaded" },
  );
  await settle(page);
  const result = await page.evaluate(({ heroSelector, viewport, expectedSurfaces }) => {
    const root = document.documentElement;
    const hero = document.querySelector(heroSelector);
    const heading = document.querySelector("h1");
    const primaryAction = hero?.querySelector(".btn.primary, a.nav-cta, button.primary");
    const headingRect = heading?.getBoundingClientRect();
    const heroRect = hero?.getBoundingClientRect();
    const actionRect = primaryAction?.getBoundingClientRect();
    const headingStyle = heading ? getComputedStyle(heading) : null;
    const heroStyle = hero ? getComputedStyle(hero) : null;
    const elementVisible = (element) => {
      if (!element) return false;
      const style = getComputedStyle(element);
      const rect = element.getBoundingClientRect();
      return (
        style.display !== "none" &&
        style.visibility !== "hidden" &&
        Number.parseFloat(style.opacity || "1") > 0 &&
        rect.width > 0 &&
        rect.height > 0
      );
    };
    const normaliseText = (value) =>
      typeof value === "string" ? value.trim().replace(/\s+/g, " ") : "";
    const expectedById = new Map(
      expectedSurfaces.map((item) => [item.surface_id, item]),
    );
    const editorialSurfaceObservations = Array.from(
      document.querySelectorAll("[data-editorial-surface-id]"),
    ).map((surface) => {
      const pictures = Array.from(surface.querySelectorAll("picture"));
      const images = Array.from(surface.querySelectorAll("img"));
      const anchors = Array.from(surface.querySelectorAll("a[href]"));
      const captions = Array.from(surface.querySelectorAll("figcaption"));
      const surfaceId = surface.getAttribute("data-editorial-surface-id") || "";
      const expected = expectedById.get(surfaceId);
      const expectedCredit = normaliseText(expected?.credit || "");
      const creditMatches = expectedCredit
        ? Array.from(surface.querySelectorAll("*")).filter(
            (element) =>
              element.tagName.toLowerCase() !== "figcaption" &&
              elementVisible(element) &&
              normaliseText(element.textContent) === expectedCredit,
          )
        : [];
      const caption = captions[0] || null;
      const image = images[0] || null;
      const imageRect = image?.getBoundingClientRect();
      const declaredWidthRaw = image?.getAttribute("width") || "";
      const declaredHeightRaw = image?.getAttribute("height") || "";
      return {
        surfaceId,
        visible: elementVisible(surface),
        pictureCount: pictures.length,
        imageCount: images.length,
        anchorCount: anchors.length,
        anchorUrls: anchors.map((anchor) => anchor.href || ""),
        figcaptionCount: captions.length,
        nestedSurfaceCount: surface.querySelectorAll("[data-editorial-surface-id]").length,
        hasSurfaceAncestor: Boolean(
          surface.parentElement?.closest("[data-editorial-surface-id]"),
        ),
        caption: normaliseText(caption?.textContent || ""),
        captionVisible: elementVisible(caption),
        creditMatchCount: creditMatches.length,
        creditVisible: creditMatches.some(elementVisible),
        image: {
          src: image?.src || "",
          currentSrc: image?.currentSrc || "",
          alt: image?.getAttribute("alt") || "",
          declaredWidth: /^[1-9]\d*$/.test(declaredWidthRaw)
            ? Number(declaredWidthRaw)
            : 0,
          declaredHeight: /^[1-9]\d*$/.test(declaredHeightRaw)
            ? Number(declaredHeightRaw)
            : 0,
          complete: image?.complete === true,
          naturalWidth: image?.naturalWidth || 0,
          naturalHeight: image?.naturalHeight || 0,
          renderedWidth: imageRect?.width || 0,
          renderedHeight: imageRect?.height || 0,
          visible: elementVisible(image),
        },
        sources: pictures.flatMap((picture) =>
          Array.from(picture.querySelectorAll("source")).map((source) => ({
            media: source.getAttribute("media") || "",
            srcset: source.srcset || source.getAttribute("srcset") || "",
          })),
        ),
      };
    });
    const stylesheetUrls = Array.from(document.querySelectorAll('link[rel="stylesheet"]')).map(
      (link) => link.href,
    );
    return {
      title: document.title,
      cacheKeyV28:
        stylesheetUrls.length > 0 &&
        stylesheetUrls.every((url) => /20260726-v29-\d+/.test(url)),
      heroFound: Boolean(hero),
      heroHeight: heroRect ? Math.round(heroRect.height) : null,
      heroHeightBudget: Math.round(window.innerHeight * viewport.heroMaxFactor),
      heroWithinBudget:
        Boolean(heroRect) && heroRect.height <= window.innerHeight * viewport.heroMaxFactor,
      h1: heading?.textContent.trim().replace(/\s+/g, " ") || "",
      h1Color: headingStyle?.color || null,
      heroBackgroundColor: heroStyle?.backgroundColor || null,
      h1FontSize: headingStyle ? Number.parseFloat(headingStyle.fontSize) : null,
      h1WithinViewport:
        Boolean(headingRect) &&
        headingRect.left >= -1 &&
        headingRect.right <= window.innerWidth + 1,
      h1WithinFirstViewport:
        Boolean(headingRect) &&
        headingRect.top >= -1 &&
        headingRect.top < window.innerHeight &&
        headingRect.bottom > 0,
      primaryActionFound: Boolean(primaryAction),
      primaryActionWithinFirstViewport:
        Boolean(actionRect) &&
        actionRect.top >= -1 &&
        actionRect.top < window.innerHeight &&
        actionRect.bottom > 0,
      horizontalOverflow: root.scrollWidth > root.clientWidth + 1,
      viewport: [window.innerWidth, window.innerHeight],
      documentWidth: root.scrollWidth,
      skipLink: Boolean(document.querySelector('a[href="#main-content"]')),
      mainLandmark: Boolean(document.querySelector("main#main-content")),
      liveState: document.body.dataset.liveState || null,
      editorialSurfaceObservations,
    };
  }, { heroSelector, viewport, expectedSurfaces });
  diagnostics.detach();
  const editorialSurfaceAudit = assessEditorialSurfaceObservations(
    result.editorialSurfaceObservations,
    runtime.baseUrl,
    expectedSurfaces,
  );
  delete result.editorialSurfaceObservations;

  const pass =
    response?.ok() === true &&
    result.heroFound &&
    result.heroWithinBudget &&
    result.h1.length > 0 &&
    result.h1WithinViewport &&
    result.h1WithinFirstViewport &&
    result.h1FontSize >= viewport.h1MinPx &&
    result.h1Color !== "rgba(0, 0, 0, 0)" &&
    result.primaryActionFound &&
    result.primaryActionWithinFirstViewport &&
    !result.horizontalOverflow &&
    result.cacheKeyV28 &&
    result.skipLink &&
    result.mainLandmark &&
    diagnostics.errors.length === 0 &&
    diagnostics.warnings.length === 0 &&
    diagnostics.resourceFailures.length === 0 &&
    editorialSurfaceAudit.pass &&
    (diagnostics.allowedResourceFailures.length === 0 ||
      result.liveState === "unavailable");
  return {
    name,
    route,
    mode: viewport.name,
    status: response?.status() || null,
    errors: diagnostics.errors,
    warnings: diagnostics.warnings,
    resourceFailures: diagnostics.resourceFailures,
    allowedResourceFailures: diagnostics.allowedResourceFailures,
    clientCancellations: diagnostics.clientCancellations,
    ...result,
    editorialSurfaceAudit,
    pass,
  };
}

async function testInteraction(page, runtime, test) {
  const diagnostics = attachPageDiagnostics(page, test.route);
  await page.goto(
    auditedUrl(runtime.baseUrl, runtime.stamp, test.route, `interaction-${test.name}`),
    { waitUntil: "domcontentloaded" },
  );
  await settle(page);
  const tab = page.locator(test.tab);
  // These controls are in-page tabs, not navigation links.  Keep the real
  // pointer interaction, then assert the selected state below; waiting for a
  // browser navigation here is both irrelevant and intermittently flaky.
  await tab.click({ noWaitAfter: true });
  const clicked = await page.evaluate((definition) => {
    const selected = document.querySelector(definition.selected);
    const panel = document.querySelector(definition.panel);
    return {
      selected: selected?.dataset[definition.selectedKey] || null,
      panel: panel?.dataset[definition.panelKey] || null,
      animation: panel ? getComputedStyle(panel).animationName : null,
      duration: panel ? getComputedStyle(panel).animationDuration : null,
    };
  }, test);
  await tab.press("ArrowRight");
  const keyed = await page.evaluate((definition) => {
    const selected = document.querySelector(definition.selected);
    const panel = document.querySelector(definition.panel);
    return {
      selected: selected?.dataset[definition.selectedKey] || null,
      panel: panel?.dataset[definition.panelKey] || null,
      focus: document.activeElement?.dataset[definition.selectedKey] || null,
    };
  }, test);
  diagnostics.detach();
  return {
    name: test.name,
    clicked,
    keyed,
    errors: diagnostics.errors,
    warnings: diagnostics.warnings,
    resourceFailures: diagnostics.resourceFailures,
    clientCancellations: diagnostics.clientCancellations,
    pass:
      clicked.selected === test.clickExpected &&
      clicked.panel === test.clickExpected &&
      clicked.animation === "aureon-panel-enter" &&
      keyed.selected === test.keyExpected &&
      keyed.panel === test.keyExpected &&
      keyed.focus === test.keyExpected &&
      diagnostics.errors.length === 0 &&
      diagnostics.warnings.length === 0 &&
      diagnostics.resourceFailures.length === 0,
  };
}

async function testReducedMotion(page, runtime) {
  await page.emulateMedia({ reducedMotion: "reduce" });
  const diagnostics = attachPageDiagnostics(page, "/");
  await page.goto(
    auditedUrl(runtime.baseUrl, runtime.stamp, "/", "reduced-motion"),
    { waitUntil: "domcontentloaded" },
  );
  await settle(page);
  const result = await page.evaluate(() => {
    const instrument = document.querySelector(".institutional-hero-proof");
    const instrumentStyle = instrument ? getComputedStyle(instrument) : null;
    return {
      mediaMatches: matchMedia("(prefers-reduced-motion: reduce)").matches,
      animationName: instrumentStyle?.animationName || null,
      transform: instrumentStyle?.transform || null,
    };
  });
  diagnostics.detach();
  await page.emulateMedia({ reducedMotion: "no-preference" });
  return {
    ...result,
    errors: diagnostics.errors,
    warnings: diagnostics.warnings,
    pass:
      result.mediaMatches &&
      result.animationName === "none" &&
      (result.transform === "none" ||
        result.transform === "matrix(1, 0, 0, 1, 0, 0)") &&
      diagnostics.errors.length === 0 &&
      diagnostics.warnings.length === 0 &&
      diagnostics.resourceFailures.length === 0,
  };
}

async function collectContrast(page, thresholds) {
  return page.evaluate((limits) => {
    const parseColor = (value) => {
      const match = String(value).match(
        /^rgba?\(\s*([\d.]+)[,\s]+([\d.]+)[,\s]+([\d.]+)(?:\s*[,/]\s*([\d.]+))?\s*\)$/i,
      );
      if (!match) return null;
      return [
        Number(match[1]),
        Number(match[2]),
        Number(match[3]),
        match[4] === undefined ? 1 : Number(match[4]),
      ];
    };
    const composite = (foreground, background) => {
      const alpha = foreground[3] + background[3] * (1 - foreground[3]);
      if (alpha === 0) return [0, 0, 0, 0];
      return [
        (foreground[0] * foreground[3] +
          background[0] * background[3] * (1 - foreground[3])) /
          alpha,
        (foreground[1] * foreground[3] +
          background[1] * background[3] * (1 - foreground[3])) /
          alpha,
        (foreground[2] * foreground[3] +
          background[2] * background[3] * (1 - foreground[3])) /
          alpha,
        alpha,
      ];
    };
    const channel = (value) => {
      const normalized = value / 255;
      return normalized <= 0.04045
        ? normalized / 12.92
        : ((normalized + 0.055) / 1.055) ** 2.4;
    };
    const luminance = (color) =>
      0.2126 * channel(color[0]) +
      0.7152 * channel(color[1]) +
      0.0722 * channel(color[2]);
    const ratio = (left, right) => {
      const first = luminance(left);
      const second = luminance(right);
      return (Math.max(first, second) + 0.05) / (Math.min(first, second) + 0.05);
    };
    const isVisible = (element) => {
      const rect = element.getBoundingClientRect();
      for (let current = element; current; current = current.parentElement) {
        const style = getComputedStyle(current);
        if (
          style.display === "none" ||
          style.visibility === "hidden" ||
          Number(style.opacity) === 0
        ) {
          return false;
        }
      }
      return (
        rect.width > 0 &&
        rect.height > 0
      );
    };
    const selector = (element) => {
      if (element.id) return `#${CSS.escape(element.id)}`;
      const pieces = [];
      let current = element;
      while (current && current !== document.body && pieces.length < 4) {
        let piece = current.tagName.toLowerCase();
        if (current.classList.length) {
          piece += `.${Array.from(current.classList).slice(0, 2).map(CSS.escape).join(".")}`;
        }
        pieces.unshift(piece);
        current = current.parentElement;
      }
      return pieces.join(" > ");
    };
    const effectiveBackground = (element) => {
      const layers = [];
      let complex = false;
      for (let current = element; current; current = current.parentElement) {
        const style = getComputedStyle(current);
        if (style.backgroundImage !== "none") complex = true;
        const color = parseColor(style.backgroundColor);
        if (color && color[3] > 0) layers.push(color);
        if (color?.[3] === 1) break;
      }
      let result = [255, 255, 255, 1];
      for (let index = layers.length - 1; index >= 0; index -= 1) {
        result = composite(layers[index], result);
      }
      return { color: result, complex };
    };

    const candidates = Array.from(document.body.querySelectorAll("*"))
      .filter((element) => {
        const directText = Array.from(element.childNodes)
          .filter((node) => node.nodeType === Node.TEXT_NODE)
          .map((node) => node.textContent)
          .join(" ")
          .trim();
        return directText.length > 0 && isVisible(element);
      })
      .slice(0, 1200);
    const violations = [];
    let measuredCount = 0;
    let skippedComplexBackground = 0;
    let skippedUnparsedColor = 0;
    let minimumRatio = null;
    for (const element of candidates) {
      const style = getComputedStyle(element);
      const foreground = parseColor(style.color);
      const background = effectiveBackground(element);
      if (!foreground) {
        skippedUnparsedColor += 1;
        continue;
      }
      if (background.complex) {
        skippedComplexBackground += 1;
        continue;
      }
      const effectiveForeground = composite(foreground, background.color);
      const contrast = ratio(effectiveForeground, background.color);
      const fontSize = Number.parseFloat(style.fontSize);
      const parsedWeight = Number.parseInt(style.fontWeight, 10);
      const fontWeight = Number.isFinite(parsedWeight)
        ? parsedWeight
        : style.fontWeight === "bold" || style.fontWeight === "bolder"
          ? 700
          : 400;
      const large =
        fontSize >= limits.largeTextPx ||
        (fontSize >= limits.largeBoldTextPx && fontWeight >= limits.largeBoldWeight);
      const required = large ? limits.largeTextContrast : limits.normalTextContrast;
      measuredCount += 1;
      minimumRatio = minimumRatio === null ? contrast : Math.min(minimumRatio, contrast);
      if (contrast + 0.001 < required && violations.length < 100) {
        violations.push({
          selector: selector(element),
          text: element.textContent.trim().replace(/\s+/g, " ").slice(0, 100),
          ratio: Number(contrast.toFixed(2)),
          required,
          fontSize,
          fontWeight,
          foreground: style.color,
          background: background.color.map((value) => Number(value.toFixed(2))),
        });
      }
    }
    return {
      method: "computed solid-background WCAG contrast sampling",
      candidateCount: candidates.length,
      measuredCount,
      skippedComplexBackground,
      skippedUnparsedColor,
      minimumRatio: minimumRatio === null ? null : Number(minimumRatio.toFixed(2)),
      violations,
      pass: measuredCount > 0 && violations.length === 0,
    };
  }, thresholds);
}

async function runAxe(page, axe) {
  if (!axe) {
    return {
      status: "NOT_INSTALLED",
      module: null,
      version: null,
      violations: [],
      incomplete: [],
      completeNodeEvidence: false,
      violationRuleCount: 0,
      violationNodeCount: 0,
      incompleteRuleCount: 0,
      incompleteNodeCount: 0,
      pass: false,
      note: "axe-core is required; accessibility evidence fails closed when it is unavailable.",
    };
  }
  await page.addScriptTag({ content: axe.source });
  const result = await page.evaluate(async () => {
    const output = await globalThis.axe.run(document, {
      runOnly: {
        type: "tag",
        values: ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"],
      },
    });
    const normalize = (items) =>
      items.map((item) => ({
        id: item.id,
        impact: item.impact,
        help: item.help,
        helpUrl: item.helpUrl,
        nodeCount: item.nodes.length,
        nodes: item.nodes.map((node) => ({
          target: node.target,
          failureSummary: node.failureSummary,
        })),
      }));
    return {
      violations: normalize(output.violations),
      incomplete: normalize(output.incomplete),
    };
  });
  return {
    status: "RAN",
    module: axe.module,
    version: axe.version,
    ...result,
    ...assessAxeEvidence(result),
  };
}

async function testRouteKeyboard(page, runtime, routeName, route, engineName) {
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.goto(
    auditedUrl(runtime.baseUrl, runtime.stamp, route, `keyboard-${routeName}-skip`),
    { waitUntil: "domcontentloaded" },
  );
  await settle(page);
  await page.evaluate(() => {
    if (document.activeElement instanceof HTMLElement) document.activeElement.blur();
    window.scrollTo(0, 0);
  });
  await page.keyboard.press("Tab");
  let skip = await page.evaluate(() => {
    const active = document.activeElement;
    const style = active ? getComputedStyle(active) : null;
    const rect = active?.getBoundingClientRect();
    return {
      href: active?.getAttribute("href") || null,
      visible:
        Boolean(rect) &&
        rect.width > 0 &&
        rect.height > 0 &&
        rect.top >= -1 &&
        rect.top < window.innerHeight,
      focusVisible:
        Boolean(style) &&
        ((style.outlineStyle !== "none" && Number.parseFloat(style.outlineWidth) > 0) ||
          style.boxShadow !== "none"),
    };
  });
  if (
    skip.href !== "#main-content"
    && engineName === "webkit"
    && process.platform === "win32"
  ) {
    skip = await page.evaluate(() => {
      const active = document.querySelector('a[href="#main-content"]');
      if (!(active instanceof HTMLElement)) {
        return { href: null, visible: false, focusVisible: false };
      }
      active.focus();
      const style = getComputedStyle(active);
      const rect = active.getBoundingClientRect();
      return {
        href: active.getAttribute("href"),
        visible:
          rect.width > 0 &&
          rect.height > 0 &&
          rect.top >= -1 &&
          rect.top < window.innerHeight,
        focusVisible:
          ((style.outlineStyle !== "none" && Number.parseFloat(style.outlineWidth) > 0) ||
            style.boxShadow !== "none") &&
          active.matches(":focus-visible"),
      };
    });
  }
  await page.keyboard.press("Enter");
  await page.waitForTimeout(50);
  const destination = await page.evaluate(() => {
    const main = document.querySelector("main#main-content");
    return {
      hash: location.hash,
      mainFound: Boolean(main),
      mainTop: main ? Math.round(main.getBoundingClientRect().top) : null,
    };
  });

  await page.goto(
    auditedUrl(runtime.baseUrl, runtime.stamp, route, `keyboard-${routeName}-order`),
    { waitUntil: "domcontentloaded" },
  );
  await settle(page);
  await revealFullPage(page);
  const inventory = await page.evaluate((minimumTargetPx) => {
    const selector =
      'a[href], button, input:not([type="hidden"]), select, textarea, summary, [contenteditable="true"], [tabindex]:not([tabindex="-1"])';
    const visible = (element) => {
      const style = getComputedStyle(element);
      const rect = element.getBoundingClientRect();
      return (
        !element.disabled &&
        element.tabIndex >= 0 &&
        !element.closest("[inert]") &&
        style.display !== "none" &&
        style.visibility !== "hidden" &&
        Number(style.opacity) > 0 &&
        rect.width > 0 &&
        rect.height > 0
      );
    };
    const elements = Array.from(document.querySelectorAll(selector)).filter(visible);
    const targets = elements.map((element, index) => {
      const focusId = `focus-${index}`;
      element.dataset.aureonQaFocusId = focusId;
      const rect = element.getBoundingClientRect();
      const style = getComputedStyle(element);
      const inlineTextException =
        element.tagName === "A" &&
        style.display === "inline" &&
        element.parentElement &&
        element.parentElement.textContent.trim().length > element.textContent.trim().length;
      return {
        focusId,
        tag: element.tagName.toLowerCase(),
        text:
          (element.getAttribute("aria-label") || element.textContent || element.value || "")
            .trim()
            .replace(/\s+/g, " ")
            .slice(0, 100),
        width: Number(rect.width.toFixed(1)),
        height: Number(rect.height.toFixed(1)),
        centerX: rect.left + rect.width / 2,
        centerY: rect.top + rect.height / 2,
        inlineTextException: Boolean(inlineTextException),
      };
    });
    for (const target of targets) {
      target.spacingException = targets
        .filter((other) => other.focusId !== target.focusId)
        .every(
          (other) =>
            Math.hypot(target.centerX - other.centerX, target.centerY - other.centerY) >=
            minimumTargetPx,
        );
      target.targetPass =
        target.inlineTextException ||
        (target.width >= minimumTargetPx && target.height >= minimumTargetPx) ||
        target.spacingException;
      delete target.centerX;
      delete target.centerY;
    }
    return {
      expectedFocusIds: targets.map((target) => target.focusId),
      targets,
      duplicateIds: Array.from(document.querySelectorAll("[id]"))
        .map((element) => element.id)
        .filter((id, index, ids) => ids.indexOf(id) !== index),
    };
  }, ACCESSIBILITY_THRESHOLDS.minimumTargetPx);

  await page.evaluate(() => {
    if (document.activeElement instanceof HTMLElement) document.activeElement.blur();
    window.scrollTo(0, 0);
  });
  const visited = [];
  const focusIndicatorViolations = [];
  for (let index = 0; index < inventory.expectedFocusIds.length + 3; index += 1) {
    await page.keyboard.press("Tab");
    const focus = await page.evaluate(() => {
      const active = document.activeElement;
      if (!(active instanceof HTMLElement)) return null;
      const style = getComputedStyle(active);
      return {
        focusId: active.dataset.aureonQaFocusId || null,
        text:
          (active.getAttribute("aria-label") || active.textContent || active.value || "")
            .trim()
            .replace(/\s+/g, " ")
            .slice(0, 100),
        focusVisible:
          ((style.outlineStyle !== "none" && Number.parseFloat(style.outlineWidth) > 0) ||
            style.boxShadow !== "none") &&
          active.matches(":focus-visible"),
      };
    });
    if (!focus?.focusId) continue;
    if (!visited.includes(focus.focusId)) visited.push(focus.focusId);
    if (!focus.focusVisible && !focusIndicatorViolations.some((item) => item.focusId === focus.focusId)) {
      focusIndicatorViolations.push(focus);
    }
  }
  const nativeMissingFocusIds = inventory.expectedFocusIds.filter((id) => !visited.includes(id));
  const programmaticFocusChecks = [];
  if (engineName === "webkit" && process.platform === "win32") {
    for (const focusId of nativeMissingFocusIds) {
      programmaticFocusChecks.push(await page.evaluate((targetFocusId) => {
        const element = document.querySelector(`[data-aureon-qa-focus-id="${targetFocusId}"]`);
        if (!(element instanceof HTMLElement)) {
          return { focusId: targetFocusId, active: false, focusVisible: false };
        }
        element.focus();
        const style = getComputedStyle(element);
        return {
          focusId: targetFocusId,
          active: document.activeElement === element,
          focusVisible:
            ((style.outlineStyle !== "none" && Number.parseFloat(style.outlineWidth) > 0) ||
              style.boxShadow !== "none") &&
            element.matches(":focus-visible"),
        };
      }, focusId));
    }
  }
  const programmaticFocusVerifiedIds = programmaticFocusChecks
    .filter((check) => check.active && check.focusVisible)
    .map((check) => check.focusId);
  const missingFocusIds = nativeMissingFocusIds.filter(
    (id) => !programmaticFocusVerifiedIds.includes(id),
  );
  for (const check of programmaticFocusChecks) {
    if (
      check.active
      && !check.focusVisible
      && !focusIndicatorViolations.some((item) => item.focusId === check.focusId)
    ) {
      focusIndicatorViolations.push({
        focusId: check.focusId,
        text: "Programmatically focused WebKit target",
        focusVisible: false,
      });
    }
  }
  const targetViolations = inventory.targets.filter((target) => !target.targetPass);
  return {
    routeName,
    traversalMode:
      engineName === "webkit" && process.platform === "win32"
        ? "native-tab plus explicit focus verification for WebKit-on-Windows link traversal"
        : "native-tab",
    skip,
    destination,
    expectedFocusableCount: inventory.expectedFocusIds.length,
    visitedFocusableCount: visited.length,
    nativeMissingFocusIds,
    programmaticFocusVerifiedIds,
    missingFocusIds,
    focusIndicatorViolations,
    targetViolations,
    duplicateIds: [...new Set(inventory.duplicateIds)],
    targetPolicy: {
      minimumPx: ACCESSIBILITY_THRESHOLDS.minimumTargetPx,
      inlineTextLinksExempt: true,
      sufficientCenterSpacingExempt: true,
    },
    pass:
      skip.href === "#main-content" &&
      skip.visible &&
      skip.focusVisible &&
      destination.hash === "#main-content" &&
      destination.mainFound &&
      inventory.expectedFocusIds.length > 0 &&
      missingFocusIds.length === 0 &&
      focusIndicatorViolations.length === 0 &&
      targetViolations.length === 0 &&
      inventory.duplicateIds.length === 0,
  };
}

async function testReflowAt200Percent(page, runtime, routeName, route) {
  const reference = ACCESSIBILITY_THRESHOLDS.zoomReferenceViewport;
  const width = Math.round(reference.width / 2);
  const height = Math.round(reference.height / 2);
  await page.setViewportSize({ width, height });
  await page.goto(
    auditedUrl(runtime.baseUrl, runtime.stamp, route, `zoom-200-${routeName}`),
    { waitUntil: "domcontentloaded" },
  );
  await settle(page);
  await revealFullPage(page);
  const result = await page.evaluate(() => {
    const root = document.documentElement;
    const fixedOverflow = Array.from(document.body.querySelectorAll("*"))
      .filter((element) => {
        const style = getComputedStyle(element);
        const rect = element.getBoundingClientRect();
        return (
          style.position === "fixed" &&
          style.display !== "none" &&
          style.visibility !== "hidden" &&
          rect.width > 0 &&
          rect.height > 0 &&
          (rect.left < -1 || rect.right > window.innerWidth + 1)
        );
      })
      .slice(0, 20)
      .map((element) => ({
        tag: element.tagName.toLowerCase(),
        id: element.id || null,
        className: String(element.className || "").slice(0, 120),
      }));
    return {
      viewport: [window.innerWidth, window.innerHeight],
      documentWidth: root.scrollWidth,
      horizontalOverflow: root.scrollWidth > root.clientWidth + 1,
      mainFound: Boolean(document.querySelector("main#main-content")),
      h1Found: Boolean(document.querySelector("h1")),
      fixedOverflow,
    };
  });
  return {
    routeName,
    method:
      "cross-engine viewport-equivalent reflow: 1440x1000 physical viewport at 200% zoom becomes 720x500 CSS pixels",
    zoomPercent: ACCESSIBILITY_THRESHOLDS.zoomPercent,
    ...result,
    pass:
      !result.horizontalOverflow &&
      result.mainFound &&
      result.h1Found &&
      result.fixedOverflow.length === 0,
  };
}

async function testRouteAccessibility(page, runtime, routeDefinition, axe, engineName) {
  const [routeName, route] = routeDefinition;
  await page.setViewportSize({ width: 1440, height: 1000 });
  const diagnostics = attachPageDiagnostics(page, route);
  await page.goto(
    auditedUrl(runtime.baseUrl, runtime.stamp, route, `accessibility-${routeName}`),
    { waitUntil: "domcontentloaded" },
  );
  await settle(page);
  await revealFullPage(page);
  const contrast = await collectContrast(page, ACCESSIBILITY_THRESHOLDS);
  const axeResult = await runAxe(page, axe);
  diagnostics.detach();
  const keyboard = await testRouteKeyboard(page, runtime, routeName, route, engineName);
  const reflow200 = await testReflowAt200Percent(page, runtime, routeName, route);
  return {
    routeName,
    route,
    contrast,
    axe: axeResult,
    keyboard,
    reflow200,
    errors: diagnostics.errors,
    warnings: diagnostics.warnings,
    resourceFailures: diagnostics.resourceFailures,
    pass:
      contrast.pass &&
      axeResult.pass &&
      keyboard.pass &&
      reflow200.pass &&
      diagnostics.errors.length === 0 &&
      diagnostics.warnings.length === 0 &&
      diagnostics.resourceFailures.length === 0,
  };
}

function evaluatePerformance(metrics, budgets = PERFORMANCE_BUDGETS) {
  const checks = {
    ttfb: {
      value: metrics.ttfbMs,
      budget: budgets.ttfbMs,
      pass: metrics.ttfbMs !== null && metrics.ttfbMs <= budgets.ttfbMs,
    },
    domContentLoaded: {
      value: metrics.domContentLoadedMs,
      budget: budgets.domContentLoadedMs,
      pass:
        metrics.domContentLoadedMs !== null &&
        metrics.domContentLoadedMs <= budgets.domContentLoadedMs,
    },
    loadEvent: {
      value: metrics.loadEventMs,
      budget: budgets.loadEventMs,
      pass: metrics.loadEventMs !== null && metrics.loadEventMs <= budgets.loadEventMs,
    },
    lcp: {
      value: metrics.lcpMs,
      budget: budgets.lcpMs,
      measurable: metrics.lcpMs !== null,
      pass: metrics.lcpMs === null || metrics.lcpMs <= budgets.lcpMs,
    },
    cls: {
      value: metrics.cls,
      budget: budgets.cls,
      measurable: metrics.cls !== null,
      pass: metrics.cls === null || metrics.cls <= budgets.cls,
    },
    requestCount: {
      value: metrics.requestCount,
      budget: budgets.requestCount,
      pass: metrics.requestCount <= budgets.requestCount,
    },
    transferProxyBytes: {
      value: metrics.transferProxyBytes,
      budget: budgets.transferProxyBytes,
      pass: metrics.transferProxyBytes <= budgets.transferProxyBytes,
    },
    longTaskTotal: {
      value: metrics.longTaskTotalMs,
      budget: budgets.longTaskTotalMs,
      measurable: metrics.longTaskTotalMs !== null,
      pass:
        metrics.longTaskTotalMs === null ||
        metrics.longTaskTotalMs <= budgets.longTaskTotalMs,
    },
  };
  return {
    checks,
    pass: Object.values(checks).every((check) => check.pass),
  };
}

async function installPerformanceObservers(context) {
  await context.addInitScript(() => {
    globalThis.__aureonVisualQaPerformance = {
      cls: 0,
      lcp: null,
      longTaskCount: 0,
      longTaskTotalMs: 0,
      observerSupport: {},
    };
    const state = globalThis.__aureonVisualQaPerformance;
    const observe = (name, callback) => {
      const supported = Array.isArray(PerformanceObserver.supportedEntryTypes)
        && PerformanceObserver.supportedEntryTypes.includes(name);
      if (!supported) {
        state.observerSupport[name] = false;
        return;
      }
      try {
        const observer = new PerformanceObserver((list) => callback(list.getEntries()));
        observer.observe({ type: name, buffered: true });
        state.observerSupport[name] = true;
      } catch {
        state.observerSupport[name] = false;
      }
    };
    observe("layout-shift", (entries) => {
      for (const entry of entries) {
        if (!entry.hadRecentInput) state.cls += entry.value;
      }
    });
    observe("largest-contentful-paint", (entries) => {
      const last = entries.at(-1);
      if (last) state.lcp = last.startTime;
    });
    observe("longtask", (entries) => {
      state.longTaskCount += entries.length;
      state.longTaskTotalMs += entries.reduce((total, entry) => total + entry.duration, 0);
    });
  });
}

async function collectDeferredRenderSnapshot(page, policy = DEFERRED_RENDER_GEOMETRY_POLICY) {
  return page.evaluate((activePolicy) => {
    const root = document.documentElement;
    const main = document.querySelector("main");
    const supports = {
      contentVisibility: Boolean(globalThis.CSS?.supports?.("content-visibility", "auto")),
      containIntrinsicSize: Boolean(
        globalThis.CSS?.supports?.("contain-intrinsic-size", "auto 1px"),
      ),
    };
    const documentMetrics = {
      scrollHeight: Math.round(root.scrollHeight),
      scrollWidth: Math.round(root.scrollWidth),
      clientWidth: Math.round(root.clientWidth),
    };
    const excluded = { displayNone: 0, outOfFlow: 0, nested: 0 };
    if (!supports.contentVisibility) {
      return {
        status: "NOT_SUPPORTED",
        support: supports,
        candidateCount: 0,
        excluded,
        document: documentMetrics,
        candidates: [],
      };
    }
    if (!main) {
      return {
        status: "NOT_APPLICABLE",
        support: supports,
        candidateCount: 0,
        excluded,
        document: documentMetrics,
        candidates: [],
      };
    }
    const autoElements = [main, ...main.querySelectorAll("*")].filter(
      (element) => getComputedStyle(element).contentVisibility === "auto",
    );
    const autoSet = new Set(autoElements);
    const candidates = [];
    for (const [index, element] of autoElements.entries()) {
      const style = getComputedStyle(element);
      if (style.display === "none") {
        excluded.displayNone += 1;
        continue;
      }
      if (["absolute", "fixed", "sticky"].includes(style.position)) {
        excluded.outOfFlow += 1;
        continue;
      }
      let ancestor = element.parentElement;
      let nested = false;
      while (ancestor) {
        if (autoSet.has(ancestor)) {
          nested = true;
          break;
        }
        if (ancestor === main) break;
        ancestor = ancestor.parentElement;
      }
      if (nested) {
        excluded.nested += 1;
        continue;
      }
      const rect = element.getBoundingClientRect();
      candidates.push({
        key: element.id ? `id:${element.id}` : `auto:${index}:${element.tagName.toLowerCase()}`,
        tag: element.tagName.toLowerCase(),
        id: element.id || null,
        computedContainIntrinsicSize: style.containIntrinsicSize || null,
        beforeOrAfterDocumentTop: Number((rect.top + window.scrollY).toFixed(2)),
        height: Number(rect.height.toFixed(2)),
      });
    }
    return {
      status: candidates.length ? "RAN" : "NOT_APPLICABLE",
      support: supports,
      candidateCount: candidates.length,
      candidateLimit: activePolicy.candidateLimit,
      excluded,
      document: documentMetrics,
      candidates,
    };
  }, policy);
}

function evaluateDeferredRenderGeometry(
  before,
  after = null,
  policy = DEFERRED_RENDER_GEOMETRY_POLICY,
  reveal = null,
) {
  const status = before?.status || "ERROR";
  const result = {
    status,
    method: policy.method,
    policy: {
      viewport: { ...policy.viewport },
      epsilonPx: policy.epsilonPx,
      candidateLimit: policy.candidateLimit,
    },
    support: before?.support || null,
    candidateCount: Number(before?.candidateCount) || 0,
    excluded: before?.excluded || { displayNone: 0, outOfFlow: 0, nested: 0 },
    before: before?.document || null,
    after: after?.document || null,
    deltas: {
      scrollHeightPx: null,
      maxCandidateTopPx: null,
      maxCandidateHeightPx: null,
    },
    candidates: [],
    failureReasons: [],
    reveal: reveal || null,
    pass: false,
  };
  if (status === "NOT_SUPPORTED" || status === "NOT_APPLICABLE") {
    result.pass = true;
    return result;
  }
  if (status !== "RAN" || after?.status !== "RAN") {
    result.failureReasons.push(`render-status:${status}->${after?.status || "MISSING"}`);
    return result;
  }
  if (reveal && reveal.completed !== true) {
    result.failureReasons.push(
      `reveal-incomplete:${Number(reveal.sweeps) || 0}/${Number(reveal.maxSweeps) || 0}`,
    );
  }
  const beforeCandidates = Array.isArray(before.candidates) ? before.candidates : [];
  const afterCandidates = Array.isArray(after.candidates) ? after.candidates : [];
  if (beforeCandidates.length > policy.candidateLimit) {
    result.failureReasons.push(`candidate-limit:${beforeCandidates.length}>${policy.candidateLimit}`);
  }
  if (beforeCandidates.length !== afterCandidates.length) {
    result.failureReasons.push(
      `candidate-count:${beforeCandidates.length}->${afterCandidates.length}`,
    );
  }
  const beforeKeys = beforeCandidates.map((item) => item.key);
  const afterByKey = new Map(afterCandidates.map((item) => [item.key, item]));
  if (new Set(beforeKeys).size !== beforeKeys.length || afterByKey.size !== afterCandidates.length) {
    result.failureReasons.push("candidate-key-duplicate");
  }
  const scrollHeightDelta = Math.abs(
    (Number(after?.document?.scrollHeight) || 0) - (Number(before?.document?.scrollHeight) || 0),
  );
  result.deltas.scrollHeightPx = scrollHeightDelta;
  if (scrollHeightDelta > policy.epsilonPx) {
    result.failureReasons.push(`scroll-height:${scrollHeightDelta}>${policy.epsilonPx}`);
  }
  for (const label of ["before", "after"]) {
    const documentMetrics = label === "before" ? before?.document : after?.document;
    if (
      !documentMetrics ||
      Number(documentMetrics.scrollWidth) > Number(documentMetrics.clientWidth) + policy.epsilonPx
    ) {
      result.failureReasons.push(`horizontal-overflow:${label}`);
    }
  }
  let maxCandidateTopPx = 0;
  let maxCandidateHeightPx = 0;
  for (const candidate of beforeCandidates) {
    const afterCandidate = afterByKey.get(candidate.key);
    if (!afterCandidate) {
      result.failureReasons.push(`candidate-missing:${candidate.key}`);
      continue;
    }
    const topDelta = Math.abs(
      Number(afterCandidate.beforeOrAfterDocumentTop) - Number(candidate.beforeOrAfterDocumentTop),
    );
    const heightDelta = Math.abs(Number(afterCandidate.height) - Number(candidate.height));
    maxCandidateTopPx = Math.max(maxCandidateTopPx, topDelta);
    maxCandidateHeightPx = Math.max(maxCandidateHeightPx, heightDelta);
    const candidatePass =
      Number(candidate.height) > 0 &&
      Number(afterCandidate.height) > 0 &&
      topDelta <= policy.epsilonPx &&
      heightDelta <= policy.epsilonPx;
    if (!candidatePass) {
      result.failureReasons.push(`candidate-geometry:${candidate.key}`);
    }
    result.candidates.push({
      key: candidate.key,
      tag: candidate.tag,
      id: candidate.id,
      computedContainIntrinsicSize: candidate.computedContainIntrinsicSize,
      before: {
        documentTop: candidate.beforeOrAfterDocumentTop,
        height: candidate.height,
      },
      after: {
        documentTop: afterCandidate.beforeOrAfterDocumentTop,
        height: afterCandidate.height,
      },
      delta: { topPx: topDelta, heightPx: heightDelta },
      pass: candidatePass,
    });
  }
  result.deltas.maxCandidateTopPx = maxCandidateTopPx;
  result.deltas.maxCandidateHeightPx = maxCandidateHeightPx;
  result.pass = result.failureReasons.length === 0;
  return result;
}

async function testDeferredRenderGeometry(page, policy = DEFERRED_RENDER_GEOMETRY_POLICY) {
  const before = await collectDeferredRenderSnapshot(page, policy);
  if (before.status !== "RAN") return evaluateDeferredRenderGeometry(before, null, policy);
  const reveal = await revealFullPage(page);
  const after = await collectDeferredRenderSnapshot(page, policy);
  return evaluateDeferredRenderGeometry(before, after, policy, reveal);
}

async function testRoutePerformance(page, runtime, routeDefinition) {
  const [routeName, route] = routeDefinition;
  await page.setViewportSize(DEFERRED_RENDER_GEOMETRY_POLICY.viewport);
  let observedRequests = 0;
  const onRequest = () => {
    observedRequests += 1;
  };
  page.on("request", onRequest);
  const diagnostics = attachPageDiagnostics(page, route);
  await page.goto(
    auditedUrl(runtime.baseUrl, runtime.stamp, route, `performance-${routeName}`),
    { waitUntil: "load" },
  );
  await settle(page);
  const metrics = await page.evaluate((requestCount) => {
    const navigation = performance.getEntriesByType("navigation")[0];
    const resources = performance.getEntriesByType("resource");
    const state = globalThis.__aureonVisualQaPerformance || {};
    const entries = navigation ? [navigation, ...resources] : resources;
    const transferSize = entries.reduce(
      (total, entry) => total + (Number(entry.transferSize) || 0),
      0,
    );
    const encodedBodySize = entries.reduce(
      (total, entry) => total + (Number(entry.encodedBodySize) || 0),
      0,
    );
    return {
      ttfbMs: navigation ? Number((navigation.responseStart - navigation.startTime).toFixed(1)) : null,
      domContentLoadedMs: navigation
        ? Number(navigation.domContentLoadedEventEnd.toFixed(1))
        : null,
      loadEventMs: navigation ? Number(navigation.loadEventEnd.toFixed(1)) : null,
      lcpMs: Number.isFinite(state.lcp) ? Number(state.lcp.toFixed(1)) : null,
      cls:
        state.observerSupport?.["layout-shift"] && Number.isFinite(state.cls)
          ? Number(state.cls.toFixed(4))
          : null,
      requestCount,
      resourceEntryCount: resources.length,
      transferSize,
      encodedBodySize,
      transferProxyBytes: Math.max(transferSize, encodedBodySize),
      longTaskCount: state.observerSupport?.longtask
        ? Number(state.longTaskCount) || 0
        : null,
      longTaskTotalMs: state.observerSupport?.longtask
        ? Number((Number(state.longTaskTotalMs) || 0).toFixed(1))
        : null,
      observerSupport: state.observerSupport || {},
    };
  }, observedRequests);
  const renderingGeometry = await testDeferredRenderGeometry(
    page,
    DEFERRED_RENDER_GEOMETRY_POLICY,
  );
  page.off("request", onRequest);
  diagnostics.detach();
  const evaluation = evaluatePerformance(metrics);
  return {
    routeName,
    route,
    metrics,
    budgets: PERFORMANCE_BUDGETS,
    checks: evaluation.checks,
    renderingGeometry,
    errors: diagnostics.errors,
    warnings: diagnostics.warnings,
    resourceFailures: diagnostics.resourceFailures,
    pass:
      evaluation.pass &&
      renderingGeometry.pass &&
      diagnostics.errors.length === 0 &&
      diagnostics.warnings.length === 0 &&
      diagnostics.resourceFailures.length === 0,
  };
}

function executableCandidates(engineName, browserType, environment = process.env) {
  const environmentName = `AUREON_${engineName.toUpperCase()}_EXECUTABLE`;
  const candidates = [
    environment[environmentName],
    engineName === "chromium" ? environment.AUREON_BROWSER_EXECUTABLE : null,
  ];
  try {
    const managed = browserType.executablePath();
    if (managed && fs.existsSync(managed)) return [{ path: null, source: "playwright-managed" }];
  } catch {
    // Continue to explicitly declared or system executable candidates.
  }
  if (engineName === "chromium") {
    candidates.push(
      "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
      "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
    );
  } else if (engineName === "firefox") {
    candidates.push(
      "C:\\Program Files\\Mozilla Firefox\\firefox.exe",
      "C:\\Program Files (x86)\\Mozilla Firefox\\firefox.exe",
    );
  }
  return candidates
    .filter((candidate, index, values) => candidate && values.indexOf(candidate) === index)
    .filter((candidate) => fs.existsSync(candidate))
    .map((candidate) => ({ path: candidate, source: "explicit-or-system" }));
}

async function launchRequestedEngine(playwright, engineName, environment = process.env) {
  const browserType = playwright[engineName];
  if (!browserType) {
    return {
      browser: null,
      status: "UNSUPPORTED",
      reason: `Loaded Playwright module does not expose ${engineName}`,
      executable: null,
    };
  }
  const candidates = executableCandidates(engineName, browserType, environment);
  if (!candidates.length) {
    return {
      browser: null,
      status: "UNSUPPORTED",
      reason: `No installed Playwright-managed, declared, or supported system executable was found for ${engineName}`,
      executable: null,
    };
  }
  const failures = [];
  for (const candidate of candidates) {
    try {
      const browser = await browserType.launch({
        headless: true,
        ...(candidate.path ? { executablePath: candidate.path } : {}),
      });
      return {
        browser,
        status: "AVAILABLE",
        reason: null,
        executable: candidate.path || "playwright-managed",
      };
    } catch (error) {
      failures.push(`${candidate.path || "playwright-managed"}: ${error.message}`);
    }
  }
  return {
    browser: null,
    status: "UNSUPPORTED",
    reason: failures.join(" | "),
    executable: candidates.map((candidate) => candidate.path || "playwright-managed"),
  };
}

async function captureScreenshots(page, runtime, engineName, selectedRoutes, selectedViewports) {
  const screenshots = [];
  for (const definition of SCREENSHOT_CAPTURE_SCOPE) {
    const viewport = selectedViewports.find((item) => item.name === definition.viewportName);
    if (!viewport) continue;
    await page.setViewportSize({ width: viewport.width, height: viewport.height });
    for (const [name, route] of selectedRoutes.filter(([name]) => definition.routeNames.includes(name))) {
      await page.goto(
        auditedUrl(
          runtime.baseUrl,
          runtime.stamp,
          route,
          `${engineName}-${viewport.name}-shot-${name}`,
        ),
        { waitUntil: "domcontentloaded" },
      );
      await settle(page);
      // Capture after the finite entrance motion has completed so hashes are
      // stable evidence rather than samples of an arbitrary animation frame.
      await page.waitForTimeout(750);
      const filename = `${engineName}-${viewport.name}-${name}.png`;
      const absolutePath = path.join(runtime.visualDir, filename);
      await page.screenshot({ path: absolutePath, fullPage: false });
      screenshots.push({
        engine: engineName,
        viewport: viewport.name,
        routeName: name,
        filename,
        bytes: fs.statSync(absolutePath).size,
        sha256: sha256File(absolutePath),
        sourceTreeSha256: runtime.sourceTreeSha256,
      });
    }
  }
  return screenshots;
}

function collectEngineDiagnostics(engineReport) {
  const warnings = [...(engineReport.engineWideDiagnostics?.warnings || [])];
  const errors = [...(engineReport.engineWideDiagnostics?.errors || [])];
  const groups = [
    ...engineReport.routes,
    ...engineReport.interactions,
    ...engineReport.accessibility,
    ...engineReport.performance,
    ...(engineReport.motion?.reduced ? [engineReport.motion.reduced] : []),
  ];
  for (const group of groups) {
    for (const warning of group.warnings || []) warnings.push(warning);
    for (const error of group.errors || []) errors.push(error);
    for (const failure of group.resourceFailures || []) errors.push(failure);
  }
  return { warnings: [...new Set(warnings)], errors: [...new Set(errors)] };
}

async function runEngine(playwright, engineName, runtime, selectedRoutes, selectedViewports, axe) {
  const launched = await launchRequestedEngine(playwright, engineName);
  if (!launched.browser) {
    return {
      engine: engineName,
      status: "UNSUPPORTED",
      executable: launched.executable,
      browserVersion: null,
      unsupportedReason: launched.reason,
      routes: [],
      interactions: [],
      accessibility: [],
      performance: [],
      motion: { status: "NOT_RUN" },
      screenshots: [],
      diagnostics: { warnings: [], errors: [launched.reason] },
      pass: false,
    };
  }

  const browser = launched.browser;
  try {
    const context = await browser.newContext({
      viewport: {
        width: selectedViewports[0].width,
        height: selectedViewports[0].height,
      },
    });
    await installPerformanceObservers(context);
    const page = await context.newPage();
    const engineWideDiagnostics = attachEngineDiagnostics(page);
    const routeResults = [];
    for (const viewport of selectedViewports) {
      await page.setViewportSize({ width: viewport.width, height: viewport.height });
      for (const [name, route, heroSelector] of selectedRoutes) {
        routeResults.push(
          await readRoute(page, runtime, name, route, heroSelector, viewport),
        );
      }
    }

    const screenshots = await captureScreenshots(
      page,
      runtime,
      engineName,
      selectedRoutes,
      selectedViewports,
    );

    await page.setViewportSize({ width: 1280, height: 900 });
    const selectedRouteNames = new Set(selectedRoutes.map(([name]) => name));
    const selectedInteractions = interactionCases.filter((test) =>
      selectedRouteNames.has(test.routeName),
    );
    const interactions = [];
    for (const test of selectedInteractions) {
      interactions.push(await testInteraction(page, runtime, test));
    }

    let motion = {
      status: "NOT_SELECTED",
      defaultAnimation: null,
      reduced: null,
      pass: true,
    };
    if (selectedRouteNames.has("home")) {
      await page.goto(
        auditedUrl(runtime.baseUrl, runtime.stamp, "/", `${engineName}-motion-default`),
        { waitUntil: "domcontentloaded" },
      );
      await settle(page);
      const defaultAnimation = await page
        .locator(".institutional-hero-proof")
        .evaluate((element) => getComputedStyle(element).animationName);
      const reduced = await testReducedMotion(page, runtime);
      motion = {
        status: "RAN",
        defaultAnimation,
        reduced,
        pass: defaultAnimation === "aureon-instrument-enter" && reduced.pass,
      };
    }

    const accessibility = [];
    for (const routeDefinition of selectedRoutes) {
      accessibility.push(
        await testRouteAccessibility(page, runtime, routeDefinition, axe, engineName),
      );
    }

    const performance = [];
    for (const routeDefinition of selectedRoutes) {
      performance.push(await testRoutePerformance(page, runtime, routeDefinition));
    }
    engineWideDiagnostics.detach();
    await context.close();

    const result = {
      engine: engineName,
      status: "PENDING",
      executable: launched.executable,
      browserVersion: browser.version(),
      unsupportedReason: null,
      routes: routeResults,
      interactions,
      accessibility,
      performance,
      motion,
      screenshots,
      engineWideDiagnostics: {
        warnings: [...new Set(engineWideDiagnostics.warnings)],
        errors: [...new Set(engineWideDiagnostics.errors)],
        clientCancellations: [...new Set(engineWideDiagnostics.clientCancellations)],
      },
    };
    result.diagnostics = collectEngineDiagnostics(result);
    result.pass =
      routeResults.every((item) => item.pass) &&
      interactions.every((item) => item.pass) &&
      accessibility.every((item) => item.pass) &&
      performance.every((item) => item.pass) &&
      motion.pass &&
      screenshots.every(
        (item) =>
          item.sha256.length === 64 &&
          sha256File(path.join(runtime.visualDir, item.filename)) === item.sha256,
      ) &&
      result.diagnostics.warnings.length === 0 &&
      result.diagnostics.errors.length === 0;
    result.status = result.pass ? "PASS" : "FAIL";
    return result;
  } finally {
    await browser.close();
  }
}

function markdown(report) {
  const engineRows = report.engines
    .map(
      (engine) =>
        `| ${engine.engine} | ${engine.status} | ${engine.browserVersion || "n/a"} | ${engine.routes.length} | ${engine.accessibility.length} | ${engine.performance.length} | ${engine.screenshots.length} | ${engine.diagnostics.warnings.length} | ${engine.diagnostics.errors.length} |`,
    )
    .join("\n");
  const failureRows = report.engines
    .flatMap((engine) => {
      const failedRoutes = engine.routes
        .filter((item) => !item.pass)
        .map((item) => `${item.mode}/${item.name}`);
      const failedAccessibility = engine.accessibility
        .filter((item) => !item.pass)
        .map((item) => item.routeName);
      const failedPerformance = engine.performance
        .filter((item) => !item.pass)
        .map((item) => item.routeName);
      if (
        !failedRoutes.length &&
        !failedAccessibility.length &&
        !failedPerformance.length &&
        engine.status === "PASS"
      ) {
        return [];
      }
      return [
        `| ${engine.engine} | ${failedRoutes.join(", ") || "none"} | ${failedAccessibility.join(", ") || "none"} | ${failedPerformance.join(", ") || "none"} | ${engine.unsupportedReason || "see JSON evidence"} |`,
      ];
    })
    .join("\n");
  const screenshotRows = report.engines
    .flatMap((engine) =>
      engine.screenshots.map(
        (item) =>
          `| ${engine.engine} | ${item.viewport}/${item.routeName} | ${item.bytes} | \`${item.sha256}\` |`,
      ),
    )
    .join("\n");
  return `# Aureon website visual QA — V28

- Generated: ${report.generatedAt}
- Base URL: ${report.baseUrl}
- Result: **${report.status}**
- Coverage mode: ${report.engineCoverage.mode}
- Requested engines: ${report.engineCoverage.requested.join(", ")}
- Browser matrix complete: ${report.engineCoverage.matrixComplete}
- Source tree SHA-256: \`${report.sourceBinding.before.sha256}\`
- Source stable during audit: ${report.sourceBinding.stable}
- Source served by built-in server: ${report.sourceBinding.servedFromHashedSource}
- Screenshot integrity: ${report.screenshotIntegrity.pass ? "PASS" : "FAIL"}

## Engine coverage

| Engine | Status | Version | Responsive route cases | Accessibility routes | Performance routes | Screenshots | Warnings | Errors |
|---|---|---|---:|---:|---:|---:|---:|---:|
${engineRows}

One requested engine is not described as a matrix. Missing requested engines
are explicit \`UNSUPPORTED\` results and fail the report.

## Release thresholds

Performance budgets: TTFB ≤ ${report.policies.performanceBudgets.ttfbMs}ms;
DOMContentLoaded ≤ ${report.policies.performanceBudgets.domContentLoadedMs}ms;
load event ≤ ${report.policies.performanceBudgets.loadEventMs}ms; measurable
LCP ≤ ${report.policies.performanceBudgets.lcpMs}ms; CLS ≤
${report.policies.performanceBudgets.cls}; requests ≤
${report.policies.performanceBudgets.requestCount}; transfer-size proxy ≤
${report.policies.performanceBudgets.transferProxyBytes} bytes; long tasks total
≤ ${report.policies.performanceBudgets.longTaskTotalMs}ms.

Accessibility gates include computed WCAG contrast for visible text on
resolvable solid backgrounds, every-route keyboard traversal, visible focus,
skip-link/main target, 24px targets with the WCAG spacing and inline-text
exceptions, duplicate IDs, and the 720×500 CSS-pixel reflow equivalent of a
1440×1000 viewport at 200% zoom.
axe-core status: ${report.capabilities.axe.status}.

## Failures

| Engine | Responsive cases | Accessibility routes | Performance routes | Detail |
|---|---|---|---|---|
${failureRows || "| none | none | none | none | none |"}

## Screenshot evidence

| Engine | View/route | Bytes | SHA-256 |
|---|---|---:|---|
${screenshotRows || "| none | none | 0 | n/a |"}

## Measurement boundaries

- Complex image or gradient backgrounds are counted but excluded from computed
  contrast ratios because a CSS color calculation cannot establish their pixel
  contrast reliably.
- LCP is enforced when the engine exposes a buffered
  \`largest-contentful-paint\` entry; measurement support is recorded per route.
- Transfer size is the maximum of browser-reported transfer and encoded-body
  bytes. It is a stable comparison proxy, not a billing figure.
- The 200% check uses an engine-independent equivalent CSS viewport. It does not
  drive browser chrome zoom controls.
- When an external base URL is supplied, this report records the local source
  tree hash but cannot prove the external target is byte-identical. Built-in
  server runs are directly served from the hashed source tree.
`;
}

function assertQaRoots(sourceRoot, outputRoot) {
  const source = path.resolve(sourceRoot);
  const output = path.resolve(outputRoot);
  if (!fs.existsSync(source) || !fs.statSync(source).isDirectory()) {
    throw new Error(`Visual QA source root is not a directory: ${source}`);
  }
  const sourceWithSeparator = `${source}${path.sep}`;
  if (output === source || output.startsWith(sourceWithSeparator)) {
    throw new Error("Visual QA output must not be written inside the hashed source tree.");
  }
  return { source, output };
}

function validateEditorialSurfaceExpectationBinding(expectations, sha256) {
  if (!Array.isArray(expectations)) {
    throw new Error("Editorial surface expectations must be an array.");
  }
  const knownRoutes = new Set(routes.map(([, route]) => route));
  const keys = new Set();
  expectations.forEach((item, index) => {
    const core = editorialExpectationCore(item);
    if (!core) {
      throw new Error(`Editorial surface expectation ${index} is malformed.`);
    }
    if (!knownRoutes.has(item.route_scope)) {
      throw new Error(`Editorial surface expectation ${index} names an unaudited route.`);
    }
    const key = `${item.route_scope}\0${core.surfaceId}`;
    if (keys.has(key)) {
      throw new Error(`Editorial surface expectation ${index} duplicates a route surface.`);
    }
    keys.add(key);
  });
  const expectedHash = canonicalJsonSha256(expectations);
  if (expectations.length) {
    if (!/^[a-f0-9]{64}$/i.test(String(sha256 || ""))) {
      throw new Error("Non-empty editorial surface expectations require their candidate SHA-256.");
    }
    if (String(sha256).toUpperCase() !== expectedHash) {
      throw new Error("Editorial surface expectations do not match their candidate SHA-256.");
    }
  } else if (sha256 !== "" && sha256 !== undefined && sha256 !== null) {
    if (!/^[a-f0-9]{64}$/i.test(String(sha256)) || String(sha256).toUpperCase() !== expectedHash) {
      throw new Error("Empty editorial surface expectations have an invalid SHA-256 binding.");
    }
  }
  return {
    expectations: JSON.parse(JSON.stringify(expectations)),
    sha256: sha256 ? String(sha256).toUpperCase() : "",
  };
}

async function runVisualQa(
  options,
  {
    sourceRoot = websiteRoot,
    outputRoot = auditRoot,
    editorialSurfaceExpectations = [],
    editorialSurfaceExpectationsSha256 = "",
  } = {},
) {
  const { source, output } = assertQaRoots(sourceRoot, outputRoot);
  const editorialBinding = validateEditorialSurfaceExpectationBinding(
    editorialSurfaceExpectations,
    editorialSurfaceExpectationsSha256,
  );
  const selectedRoutes = options.routeNames.length
    ? routes.filter(([name]) => options.routeNames.includes(name))
    : routes;
  const selectedViewports = options.viewportNames.length
    ? viewports.filter(({ name }) => options.viewportNames.includes(name))
    : viewports;
  const stamp = new Date().toISOString().replace(/[-:]/g, "").replace(/\.(\d{3})Z$/, "$1Z");
  fs.mkdirSync(output, { recursive: true });
  const visualDir = path.join(output, `AUREON_WEBSITE_VISUAL_QA_${stamp}_V28`);
  fs.mkdirSync(visualDir, { recursive: false });

  let serverHandle = null;
  const selfHosted = !options.baseUrl;
  let baseUrl = options.baseUrl
    ? normalizedAuditBaseUrl(options.baseUrl)
    : "";
  if (selfHosted) {
    serverHandle = await startStaticServer(source);
    baseUrl = serverHandle.baseUrl;
  }

  try {
    const sourceBefore = snapshotWebsiteTree(source);
    const { playwright, source: playwrightSource } = loadPlaywright();
    const axe = loadOptionalAxe();
    const runtime = {
      baseUrl,
      stamp,
      visualDir,
      sourceTreeSha256: sourceBefore.sha256,
      editorialSurfaceExpectations: editorialBinding.expectations,
    };
    const engineReports = [];
    for (const engineName of options.engines) {
      try {
        engineReports.push(
          await runEngine(
            playwright,
            engineName,
            runtime,
            selectedRoutes,
            selectedViewports,
            axe,
          ),
        );
      } catch (error) {
        engineReports.push({
          engine: engineName,
          status: "FAIL",
          executable: null,
          browserVersion: null,
          unsupportedReason: null,
          routes: [],
          interactions: [],
          accessibility: [],
          performance: [],
          motion: { status: "NOT_RUN", pass: false },
          screenshots: [],
          diagnostics: {
            warnings: [],
            errors: [safeDiagnosticText(error.stack || error.message)],
          },
          pass: false,
        });
      }
    }
    const sourceAfter = snapshotWebsiteTree(source);
    const sourceStable = sourceBefore.sha256 === sourceAfter.sha256;
    const screenshotEvidence = engineReports.flatMap((engine) => engine.screenshots);
    const screenshotIntegrity = {
      count: screenshotEvidence.length,
      pass:
        screenshotEvidence.length > 0 &&
        screenshotEvidence.every((item) => {
          const target = path.join(visualDir, item.filename);
          return fs.existsSync(target) && sha256File(target) === item.sha256;
        }),
    };
    const matrixComplete =
      options.engines.length > 1 &&
      options.engines.every(
        (name) =>
          engineReports.find((engine) => engine.engine === name)?.status === "PASS",
      );
    const engineCoverage = {
      requested: options.engines,
      selectionExplicit: options.engineSelectionExplicit,
      mode:
        options.engines.length > 1
          ? "requested-browser-engine-matrix"
          : "explicit-single-engine-coverage",
      matrixComplete,
      unsupported: engineReports
        .filter((engine) => engine.status === "UNSUPPORTED")
        .map((engine) => engine.engine),
    };
    const allWarnings = engineReports.flatMap((engine) =>
      engine.diagnostics.warnings.map((message) => `${engine.engine}: ${message}`),
    );
    const allErrors = engineReports.flatMap((engine) =>
      engine.diagnostics.errors.map((message) => `${engine.engine}: ${message}`),
    );
    const selectedRouteScopes = new Set(selectedRoutes.map(([, route]) => route));
    const expectedRouteScopes = [
      ...new Set(editorialBinding.expectations.map((item) => item.route_scope)),
    ].sort();
    const missingRouteScopes = expectedRouteScopes.filter(
      (route) => !selectedRouteScopes.has(route),
    );
    const editorialSurfaceExpectationCoverage = {
      pass: missingRouteScopes.length === 0,
      expectedRouteScopes,
      selectedRouteScopes: [...selectedRouteScopes].sort(),
      missingRouteScopes,
    };
    const status =
      sourceStable &&
      screenshotIntegrity.pass &&
      editorialSurfaceExpectationCoverage.pass &&
      engineReports.length === options.engines.length &&
      engineReports.every((engine) => engine.pass) &&
      allWarnings.length === 0 &&
      allErrors.length === 0
        ? "PASS"
        : "FAIL";
    const report = {
      schema: "aureon-website-visual-qa-v28.3",
      generatedAt: new Date().toISOString(),
      baseUrl,
      status,
      selfHosted,
      playwrightSource,
      capabilities: {
        axe: axe
          ? { status: "INSTALLED", module: axe.module, version: axe.version }
          : { status: "NOT_INSTALLED", module: null, version: null },
      },
      engineCoverage,
      selectedRoutes: selectedRoutes.map(([name, route]) => ({ name, route })),
      selectedViewports,
      editorialSurfaceExpectations: editorialBinding.expectations,
      editorialSurfaceExpectationsSha256: editorialBinding.sha256,
      editorialSurfaceExpectationCoverage,
      policies: {
        performanceBudgets: PERFORMANCE_BUDGETS,
        deferredRenderGeometry: DEFERRED_RENDER_GEOMETRY_POLICY,
        accessibilityThresholds: ACCESSIBILITY_THRESHOLDS,
        axeCoreRequired: true,
        axeNodeEvidencePolicy:
          "Every axe violation and incomplete node must be persisted; capped samples fail closed.",
        warningAndErrorPolicy: "Any captured warning or error fails the report.",
        unsupportedEnginePolicy: "Any requested unsupported engine fails the report.",
        editorialSurfacePolicy:
          "Every provenance-bound editorial surface must match the exact expected route, " +
          "identifier, local responsive variants, dimensions, Substack post, alt, caption, " +
          "and credit. Missing, extra, ambiguous, credential-bearing, query-bearing, or " +
          "fragment-bearing URLs fail closed.",
      },
      sourceBinding: {
        before: sourceBefore,
        after: sourceAfter,
        stable: sourceStable,
        servedFromHashedSource: selfHosted,
      },
      screenshotIntegrity,
      diagnostics: {
        warnings: allWarnings,
        errors: allErrors,
      },
      engines: engineReports,
    };

    const jsonPath = path.join(output, `AUREON_WEBSITE_VISUAL_QA_${stamp}_V28.json`);
    const mdPath = path.join(output, `AUREON_WEBSITE_VISUAL_QA_${stamp}_V28.md`);
    fs.writeFileSync(jsonPath, `${JSON.stringify(report, null, 2)}\n`, "utf8");
    fs.writeFileSync(mdPath, markdown(report), "utf8");
    return {
      report,
      jsonPath,
      mdPath,
      visualDir,
      exitCode: report.status === "PASS" ? 0 : 1,
    };
  } finally {
    if (serverHandle) {
      await new Promise((resolve) => serverHandle.server.close(resolve));
    }
  }
}

async function main(argv = process.argv.slice(2)) {
  const options = parseCli(argv);
  if (options.help) {
    process.stdout.write(usage());
    return 0;
  }
  const result = await runVisualQa(options);
  process.stdout.write(
    `${result.report.status}\n${result.jsonPath}\n${result.mdPath}\n${result.visualDir}\n`,
  );
  return result.exitCode;
}

module.exports = {
  ACCESSIBILITY_THRESHOLDS,
  DEFAULT_ENGINES,
  DEFERRED_RENDER_GEOMETRY_POLICY,
  PERFORMANCE_BUDGETS,
  SCREENSHOT_CAPTURE_SCOPE,
  assessEditorialSurfaceObservations,
  assessAxeEvidence,
  canonicalJsonSha256,
  evaluateDeferredRenderGeometry,
  evaluatePerformance,
  isExpectedClientCancellation,
  loadPlaywright,
  parseCli,
  runVisualQa,
  safeDiagnosticText,
  safeDiagnosticUrl,
  sha256File,
  snapshotWebsiteTree,
  startStaticServer,
  usage,
  validateEditorialSurfaceExpectationBinding,
};

if (require.main === module) {
  main()
    .then((exitCode) => {
      process.exitCode = exitCode;
    })
    .catch((error) => {
      process.stderr.write(`${error.stack || error.message}\n`);
      process.exitCode = 1;
    });
}

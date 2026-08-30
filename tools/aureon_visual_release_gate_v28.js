#!/usr/bin/env node
"use strict";

const crypto = require("node:crypto");
const fs = require("node:fs");
const path = require("node:path");

const {
  DEFERRED_RENDER_GEOMETRY_POLICY,
  PERFORMANCE_BUDGETS,
  snapshotWebsiteTree,
} = require("./aureon_website_visual_qa_v28.js");

const MANIFEST_SCHEMA = "aureon-visual-release-gate-manifest-v28.1";
const MANUAL_REVIEW_SCHEMA = "aureon-manual-pixel-review-receipt-v28.1";
const GATE_RECEIPT_SCHEMA = "aureon-composite-visual-release-gate-receipt-v28.1";
const VISUAL_RECEIPT_SCHEMA = "aureon-website-visual-qa-v28.3";
const GATE_ID = "aureon-v28-composite-visual-release";
const MAX_EVIDENCE_AGE_SECONDS = 24 * 60 * 60;
const MAX_FUTURE_SKEW_SECONDS = 5 * 60;
const FINAL_RELEASE_ENGINES = Object.freeze(["chromium", "firefox", "webkit"]);
const REMEDIATION_ENGINES = Object.freeze(["chromium"]);

const CANONICAL_ROUTES = Object.freeze([
  { name: "home", route: "/" },
  { name: "about", route: "/about/" },
  { name: "community", route: "/community/" },
  { name: "contact", route: "/contact/" },
  { name: "diligence", route: "/diligence/" },
  { name: "funding", route: "/funding/" },
  { name: "investor", route: "/funding/investor-deck/" },
  { name: "live", route: "/live/" },
  { name: "projects", route: "/projects/" },
  { name: "publications", route: "/publications/" },
  { name: "research", route: "/research/" },
  { name: "journal", route: "/research/journal/" },
  { name: "updates", route: "/updates/" },
  { name: "vision", route: "/vision/" },
]);

const CANONICAL_VIEWPORTS = Object.freeze([
  { name: "reflow", width: 320, height: 800, heroMaxFactor: 2.65, h1MinPx: 28 },
  { name: "compact", width: 360, height: 800, heroMaxFactor: 2.4, h1MinPx: 30 },
  { name: "mobile", width: 390, height: 844, heroMaxFactor: 2.2, h1MinPx: 30 },
  { name: "tablet", width: 768, height: 1024, heroMaxFactor: 1.8, h1MinPx: 36 },
  { name: "laptop", width: 1280, height: 800, heroMaxFactor: 1.55, h1MinPx: 42 },
  { name: "desktop", width: 1440, height: 1000, heroMaxFactor: 1.25, h1MinPx: 42 },
  { name: "wide", width: 1920, height: 1080, heroMaxFactor: 1.25, h1MinPx: 42 },
]);

const CANONICAL_INTERACTIONS = Object.freeze([
  "projects packet inspector",
  "live evidence packet",
  "engagement router",
  "research proof path",
]);

const CANONICAL_SCREENSHOTS = Object.freeze([
  { viewport: "desktop", routeName: "home" },
  { viewport: "desktop", routeName: "funding" },
  { viewport: "desktop", routeName: "investor" },
  { viewport: "desktop", routeName: "publications" },
  { viewport: "desktop", routeName: "research" },
  { viewport: "mobile", routeName: "home" },
  { viewport: "mobile", routeName: "projects" },
  { viewport: "mobile", routeName: "research" },
  { viewport: "mobile", routeName: "contact" },
]);

const CANONICAL_POLICY = Object.freeze({
  visualReceiptSchema: VISUAL_RECEIPT_SCHEMA,
  maxEvidenceAgeSeconds: MAX_EVIDENCE_AGE_SECONDS,
  requiredFinalReleaseEngines: FINAL_RELEASE_ENGINES,
  permittedRemediationEngines: REMEDIATION_ENGINES,
  manualReviewableAxeIncompleteRuleIds: ["color-contrast"],
  requireCurrentWebsiteTree: true,
  requireSelfHostedSource: true,
  requireAxeInstalled: true,
  requireUncappedAxeNodeEvidence: true,
  requireZeroAxeViolations: true,
  requireManualReviewOfEveryAxeIncompleteNode: true,
  requireZeroManualFailuresOrUnreviewed: true,
  preserveAutomatedIncompleteStatus: true,
});

const PERFORMANCE_CHECKS = Object.freeze([
  "ttfb",
  "domContentLoaded",
  "loadEvent",
  "lcp",
  "cls",
  "requestCount",
  "transferProxyBytes",
  "longTaskTotal",
]);

function stableStringify(value) {
  if (Array.isArray(value)) {
    return `[${value.map((item) => stableStringify(item)).join(",")}]`;
  }
  if (value && typeof value === "object") {
    const keys = Object.keys(value).sort();
    return `{${keys
      .map((key) => `${JSON.stringify(key)}:${stableStringify(value[key])}`)
      .join(",")}}`;
  }
  return JSON.stringify(value);
}

function canonicalScope(intent) {
  return {
    engines:
      intent === "remediation-evidence"
        ? [...REMEDIATION_ENGINES]
        : [...FINAL_RELEASE_ENGINES],
    routes: CANONICAL_ROUTES.map((item) => item.name),
    viewports: CANONICAL_VIEWPORTS.map((item) => item.name),
  };
}

function sha256Buffer(value) {
  return crypto.createHash("sha256").update(value).digest("hex");
}

function sha256File(filePath) {
  return sha256Buffer(fs.readFileSync(filePath));
}

function isObject(value) {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

function exactKeys(value, expected) {
  if (!isObject(value)) return false;
  const observed = Object.keys(value).sort();
  const canonical = [...expected].sort();
  return stableStringify(observed) === stableStringify(canonical);
}

function same(value, expected) {
  return stableStringify(value) === stableStringify(expected);
}

function isSha256(value) {
  return typeof value === "string" && /^[a-f0-9]{64}$/.test(value);
}

function addFinding(findings, code, message, evidence = undefined) {
  const finding = { code, severity: "error", message };
  if (evidence !== undefined) finding.evidence = evidence;
  findings.push(finding);
}

function emptyArray(value) {
  return Array.isArray(value) && value.length === 0;
}

function parseCanonicalTimestamp(value, label, findings) {
  if (
    typeof value !== "string" ||
    !/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$/.test(value)
  ) {
    addFinding(
      findings,
      "freshness.timestamp_format",
      `${label} must be a canonical UTC timestamp with millisecond precision.`,
      { label, observed: value ?? null },
    );
    return null;
  }
  const milliseconds = Date.parse(value);
  if (!Number.isFinite(milliseconds) || new Date(milliseconds).toISOString() !== value) {
    addFinding(
      findings,
      "freshness.timestamp_invalid",
      `${label} is not a valid canonical UTC timestamp.`,
      { label, observed: value },
    );
    return null;
  }
  return milliseconds;
}

function validateFreshTimestamp(milliseconds, label, nowMs, findings) {
  if (milliseconds === null) return;
  const ageMs = nowMs - milliseconds;
  if (ageMs < -MAX_FUTURE_SKEW_SECONDS * 1000) {
    addFinding(
      findings,
      "freshness.future_evidence",
      `${label} is too far in the future.`,
      { label, futureBySeconds: Math.round(-ageMs / 1000) },
    );
  }
  if (ageMs > MAX_EVIDENCE_AGE_SECONDS * 1000) {
    addFinding(
      findings,
      "freshness.stale_evidence",
      `${label} exceeds the fixed V28 evidence age limit.`,
      {
        label,
        ageSeconds: Math.round(ageMs / 1000),
        limitSeconds: MAX_EVIDENCE_AGE_SECONDS,
      },
    );
  }
}

function canonicalRelativePath(value) {
  if (
    typeof value !== "string" ||
    !value ||
    value.includes("\\") ||
    value.startsWith("/") ||
    /^[a-zA-Z]:/.test(value)
  ) {
    return null;
  }
  const normalized = path.posix.normalize(value);
  if (
    normalized !== value ||
    normalized === "." ||
    normalized === ".." ||
    normalized.startsWith("../") ||
    normalized.split("/").includes("..")
  ) {
    return null;
  }
  return normalized;
}

function resolveRepoFile(repoRoot, relative, label, findings) {
  const normalized = canonicalRelativePath(relative);
  if (!normalized) {
    addFinding(
      findings,
      "manifest.path_invalid",
      `${label} must be a canonical repository-relative POSIX path.`,
      { label, observed: relative ?? null },
    );
    return null;
  }
  if (!normalized.startsWith("docs/audits/")) {
    addFinding(
      findings,
      "manifest.path_scope",
      `${label} must stay inside docs/audits/.`,
      { label, observed: normalized },
    );
    return null;
  }
  const candidate = path.resolve(repoRoot, ...normalized.split("/"));
  const root = path.resolve(repoRoot);
  const relativeToRoot = path.relative(root, candidate);
  if (relativeToRoot.startsWith("..") || path.isAbsolute(relativeToRoot)) {
    addFinding(
      findings,
      "manifest.path_escape",
      `${label} escapes the repository root.`,
      { label, observed: normalized },
    );
    return null;
  }
  if (!fs.existsSync(candidate) || !fs.statSync(candidate).isFile()) {
    addFinding(
      findings,
      "evidence.file_missing",
      `${label} does not resolve to an evidence file.`,
      { label, path: normalized },
    );
    return null;
  }
  const real = fs.realpathSync(candidate);
  const realRelative = path.relative(root, real);
  if (realRelative.startsWith("..") || path.isAbsolute(realRelative)) {
    addFinding(
      findings,
      "manifest.symlink_escape",
      `${label} resolves outside the repository root.`,
      { label, path: normalized },
    );
    return null;
  }
  return { absolute: candidate, relative: normalized };
}

function readJsonFile(filePath, label, findings) {
  try {
    const raw = fs.readFileSync(filePath, "utf8").replace(/^\uFEFF/, "");
    const payload = JSON.parse(raw);
    if (!isObject(payload)) {
      addFinding(
        findings,
        "evidence.json_shape",
        `${label} must contain one JSON object.`,
      );
      return null;
    }
    return payload;
  } catch (error) {
    addFinding(
      findings,
      "evidence.json_invalid",
      `${label} is not valid JSON.`,
      { error: error.message },
    );
    return null;
  }
}

function readEvidenceReference(repoRoot, reference, label, findings) {
  if (!exactKeys(reference, ["path", "sha256"])) {
    addFinding(
      findings,
      "manifest.evidence_reference_shape",
      `${label} must contain exactly path and sha256.`,
    );
  }
  const resolved = resolveRepoFile(repoRoot, reference?.path, label, findings);
  const declaredHash = reference?.sha256;
  if (!isSha256(declaredHash)) {
    addFinding(
      findings,
      "manifest.evidence_hash_format",
      `${label} sha256 must be a lowercase SHA-256 digest.`,
      { observed: declaredHash ?? null },
    );
  }
  if (!resolved) return null;
  const observedHash = sha256File(resolved.absolute);
  if (declaredHash !== observedHash) {
    addFinding(
      findings,
      "evidence.hash_mismatch",
      `${label} bytes do not match the manifest hash.`,
      { path: resolved.relative, declared: declaredHash ?? null, observed: observedHash },
    );
  }
  return {
    ...resolved,
    declaredHash,
    observedHash,
    payload: readJsonFile(resolved.absolute, label, findings),
  };
}

function identityPayload(node) {
  const deepNfc = (value) => {
    if (Array.isArray(value)) return value.map((item) => deepNfc(item));
    if (typeof value === "string") return value.normalize("NFC");
    return value;
  };
  return [
    "aureon-axe-incomplete-node-v1",
    deepNfc(node.engine),
    deepNfc(node.route),
    deepNfc(node.ruleId),
    deepNfc(node.target),
  ];
}

function incompleteNodeIdentity(node) {
  return `axei1-${sha256Buffer(
    Buffer.from(JSON.stringify(identityPayload(node)), "utf8"),
  )}`;
}

function collectIncompleteNodes(visualReceipt) {
  const sourceTreeSha256 = visualReceipt?.sourceBinding?.before?.sha256 ?? null;
  const nodes = [];
  for (const engine of Array.isArray(visualReceipt?.engines) ? visualReceipt.engines : []) {
    for (const accessibility of Array.isArray(engine?.accessibility)
      ? engine.accessibility
      : []) {
      for (const rule of Array.isArray(accessibility?.axe?.incomplete)
        ? accessibility.axe.incomplete
        : []) {
        for (const node of Array.isArray(rule?.nodes) ? rule.nodes : []) {
          const value = {
            sourceTreeSha256,
            engine: engine.engine ?? null,
            routeName: accessibility.routeName ?? null,
            route: accessibility.route ?? null,
            ruleId: rule.id ?? null,
            impact: rule.impact ?? null,
            target: node.target ?? null,
            failureSummary: node.failureSummary ?? null,
          };
          nodes.push({ nodeId: incompleteNodeIdentity(value), ...value });
        }
      }
    }
  }
  return nodes;
}

function validateManifest(manifest, findings) {
  const expectedKeys = [
    "schema",
    "gateId",
    "intent",
    "releaseId",
    "generatedAt",
    "websiteTreeSha256",
    "scope",
    "policy",
    "evidence",
  ];
  if (!exactKeys(manifest, expectedKeys)) {
    addFinding(
      findings,
      "manifest.shape",
      "Gate manifest keys do not match the canonical V28 contract.",
      { expectedKeys, observedKeys: isObject(manifest) ? Object.keys(manifest).sort() : [] },
    );
  }
  if (manifest?.schema !== MANIFEST_SCHEMA) {
    addFinding(
      findings,
      "manifest.schema",
      "Gate manifest schema is not the canonical V28 schema.",
      { expected: MANIFEST_SCHEMA, observed: manifest?.schema ?? null },
    );
  }
  if (manifest?.gateId !== GATE_ID) {
    addFinding(
      findings,
      "manifest.gate_id",
      "Gate manifest gateId is not canonical.",
      { expected: GATE_ID, observed: manifest?.gateId ?? null },
    );
  }
  if (!["final-release", "remediation-evidence"].includes(manifest?.intent)) {
    addFinding(
      findings,
      "manifest.intent",
      "Gate manifest intent must be final-release or remediation-evidence.",
      { observed: manifest?.intent ?? null },
    );
  }
  if (
    typeof manifest?.releaseId !== "string" ||
    !/^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$/.test(manifest.releaseId)
  ) {
    addFinding(
      findings,
      "manifest.release_id",
      "releaseId must be a bounded stable identifier.",
      { observed: manifest?.releaseId ?? null },
    );
  }
  if (!isSha256(manifest?.websiteTreeSha256)) {
    addFinding(
      findings,
      "manifest.source_hash",
      "websiteTreeSha256 must be a lowercase SHA-256 digest.",
      { observed: manifest?.websiteTreeSha256 ?? null },
    );
  }
  const expectedScope = canonicalScope(manifest?.intent);
  if (!same(manifest?.scope, expectedScope)) {
    addFinding(
      findings,
      "manifest.scope",
      "Gate manifest scope differs from the canonical scope for its intent.",
      { expected: expectedScope, observed: manifest?.scope ?? null },
    );
  }
  if (!same(manifest?.policy, CANONICAL_POLICY)) {
    addFinding(
      findings,
      "manifest.policy",
      "Gate manifest policy differs from the fixed fail-closed V28 policy.",
      { expected: CANONICAL_POLICY, observed: manifest?.policy ?? null },
    );
  }
  if (
    !exactKeys(manifest?.evidence, [
      "visualReceipt",
      "manualPixelReviewReceipt",
    ])
  ) {
    addFinding(
      findings,
      "manifest.evidence_shape",
      "Manifest evidence must identify exactly the visual and manual pixel-review receipts.",
    );
  }
  if (manifest?.intent === "remediation-evidence") {
    addFinding(
      findings,
      "manifest.remediation_only",
      "Chromium-only remediation evidence cannot satisfy the final visual release gate.",
      {
        remediationEngines: REMEDIATION_ENGINES,
        requiredFinalReleaseEngines: FINAL_RELEASE_ENGINES,
      },
    );
  }
}

function validateRuleNodes(rules, kind, context, findings) {
  if (!Array.isArray(rules)) {
    addFinding(
      findings,
      "visual.axe_rule_array",
      `${context} ${kind} must be an array.`,
    );
    return { ruleCount: 0, nodeCount: 0, complete: false };
  }
  let complete = true;
  let nodeCount = 0;
  const ruleIds = new Set();
  for (const [ruleIndex, rule] of rules.entries()) {
    const label = `${context} ${kind}[${ruleIndex}]`;
    if (!isObject(rule) || typeof rule.id !== "string" || !rule.id) {
      complete = false;
      addFinding(
        findings,
        "visual.axe_rule_shape",
        `${label} has no stable rule id.`,
      );
      continue;
    }
    if (ruleIds.has(rule.id)) {
      complete = false;
      addFinding(
        findings,
        "visual.axe_rule_duplicate",
        `${context} repeats axe rule ${rule.id}.`,
      );
    }
    ruleIds.add(rule.id);
    if (
      !Number.isInteger(rule.nodeCount) ||
      rule.nodeCount <= 0 ||
      !Array.isArray(rule.nodes) ||
      rule.nodes.length === 0 ||
      rule.nodeCount !== rule.nodes.length
    ) {
      complete = false;
      addFinding(
        findings,
        "visual.axe_node_evidence",
        `${label} does not persist every declared node.`,
        {
          declaredNodeCount: rule.nodeCount ?? null,
          persistedNodeCount: Array.isArray(rule.nodes) ? rule.nodes.length : null,
        },
      );
    }
    const nodes = Array.isArray(rule.nodes) ? rule.nodes : [];
    nodeCount += nodes.length;
    for (const [nodeIndex, node] of nodes.entries()) {
      if (
        !isObject(node) ||
        !Array.isArray(node.target) ||
        node.target.length === 0 ||
        node.target.some((part) => typeof part !== "string" || !part) ||
        typeof node.failureSummary !== "string" ||
        !node.failureSummary
      ) {
        complete = false;
        addFinding(
          findings,
          "visual.axe_node_shape",
          `${label}.nodes[${nodeIndex}] lacks complete target or failure evidence.`,
        );
      }
    }
  }
  return { ruleCount: rules.length, nodeCount, complete };
}

function validateVisualReceipt(visual, visualFile, manifest, currentSnapshot, findings) {
  const result = {
    generatedAtMs: null,
    violationRuleCount: 0,
    violationNodeCount: 0,
    incompleteRuleCount: 0,
    incompleteNodeCount: 0,
    incompleteNodes: [],
    nonAxeFailureIds: [],
    screenshotFailures: [],
  };
  if (!isObject(visual)) return result;

  if (visual.schema !== VISUAL_RECEIPT_SCHEMA) {
    addFinding(
      findings,
      "visual.schema",
      "Visual receipt is not the strict uncapped V28.3 schema.",
      { expected: VISUAL_RECEIPT_SCHEMA, observed: visual.schema ?? null },
    );
  }
  result.generatedAtMs = parseCanonicalTimestamp(
    visual.generatedAt,
    "visual receipt generatedAt",
    findings,
  );
  if (
    visual.selfHosted !== true ||
    visual?.sourceBinding?.servedFromHashedSource !== true
  ) {
    addFinding(
      findings,
      "visual.source_hosting",
      "Visual receipt must be served directly from the hashed local source.",
    );
  }
  if (
    visual?.capabilities?.axe?.status !== "INSTALLED" ||
    typeof visual?.capabilities?.axe?.module !== "string" ||
    !visual.capabilities.axe.module ||
    typeof visual?.capabilities?.axe?.version !== "string" ||
    !visual.capabilities.axe.version
  ) {
    addFinding(
      findings,
      "visual.axe_not_installed",
      "Strict V28.3 evidence requires an installed, versioned axe-core capability.",
      { capability: visual?.capabilities?.axe ?? null },
    );
  }
  if (
    visual?.policies?.axeCoreRequired !== true ||
    visual?.policies?.axeNodeEvidencePolicy !==
      "Every axe violation and incomplete node must be persisted; capped samples fail closed."
  ) {
    addFinding(
      findings,
      "visual.axe_policy",
      "Visual receipt does not carry the strict uncapped axe evidence policy.",
    );
  }
  if (!same(visual?.policies?.performanceBudgets, PERFORMANCE_BUDGETS)) {
    addFinding(
      findings,
      "visual.performance_policy",
      "Visual receipt performance budgets differ from the V28 gate budgets.",
    );
  }
  if (
    !same(
      visual?.policies?.deferredRenderGeometry,
      DEFERRED_RENDER_GEOMETRY_POLICY,
    )
  ) {
    addFinding(
      findings,
      "visual.deferred_render_geometry_policy",
      "Visual receipt deferred-render geometry policy differs from the V28 gate policy.",
    );
  }
  if (
    !same(visual.selectedRoutes, CANONICAL_ROUTES) ||
    !same(visual.selectedViewports, CANONICAL_VIEWPORTS)
  ) {
    addFinding(
      findings,
      "visual.scope",
      "Visual receipt does not cover the canonical 14-route, seven-viewport scope.",
    );
  }
  const requiredEngines = Array.isArray(manifest?.scope?.engines)
    ? manifest.scope.engines
    : [];
  const expectedSelectionExplicit = requiredEngines.length === 1;
  const expectedCoverageMode =
    requiredEngines.length > 1
      ? "requested-browser-engine-matrix"
      : "explicit-single-engine-coverage";
  if (
    !isObject(visual.engineCoverage) ||
    !same(visual.engineCoverage.requested, requiredEngines) ||
    visual.engineCoverage.selectionExplicit !== expectedSelectionExplicit ||
    visual.engineCoverage.mode !== expectedCoverageMode ||
    !emptyArray(visual.engineCoverage.unsupported)
  ) {
    addFinding(
      findings,
      "visual.engine_scope",
      "Visual receipt engine coverage does not match the manifest intent and scope.",
      {
        expected: {
          requested: requiredEngines,
          selectionExplicit: expectedSelectionExplicit,
          mode: expectedCoverageMode,
          unsupported: [],
        },
        observed: visual.engineCoverage ?? null,
      },
    );
  }

  const before = visual?.sourceBinding?.before;
  const after = visual?.sourceBinding?.after;
  const sourceHash = manifest.websiteTreeSha256;
  if (
    visual?.sourceBinding?.stable !== true ||
    !isObject(before) ||
    !isObject(after) ||
    before.sha256 !== after.sha256
  ) {
    addFinding(
      findings,
      "visual.source_unstable",
      "Visual receipt source changed during the run.",
      { before: before?.sha256 ?? null, after: after?.sha256 ?? null },
    );
  }
  if (
    before?.sha256 !== sourceHash ||
    after?.sha256 !== sourceHash ||
    currentSnapshot.sha256 !== sourceHash
  ) {
    addFinding(
      findings,
      "visual.source_mismatch",
      "Manifest, visual receipt and current website tree hashes do not match.",
      {
        manifest: sourceHash,
        visualBefore: before?.sha256 ?? null,
        visualAfter: after?.sha256 ?? null,
        current: currentSnapshot.sha256,
      },
    );
  }
  for (const [label, snapshot] of [
    ["before", before],
    ["after", after],
  ]) {
    if (
      snapshot?.algorithm !== currentSnapshot.algorithm ||
      snapshot?.fileCount !== currentSnapshot.fileCount ||
      snapshot?.totalBytes !== currentSnapshot.totalBytes ||
      !Array.isArray(snapshot?.files) ||
      snapshot.files.length !== snapshot.fileCount ||
      !same(snapshot.files, currentSnapshot.files)
    ) {
      addFinding(
        findings,
        "visual.source_inventory",
        `Visual ${label} source inventory does not match the current website tree.`,
        {
          observedFileCount: snapshot?.fileCount ?? null,
          observedTotalBytes: snapshot?.totalBytes ?? null,
          observedAlgorithm: snapshot?.algorithm ?? null,
          currentFileCount: currentSnapshot.fileCount,
          currentTotalBytes: currentSnapshot.totalBytes,
          currentAlgorithm: currentSnapshot.algorithm,
        },
      );
    }
  }

  if (!emptyArray(visual?.diagnostics?.warnings) || !emptyArray(visual?.diagnostics?.errors)) {
    addFinding(
      findings,
      "visual.diagnostics",
      "Visual receipt contains top-level warnings or errors.",
      { diagnostics: visual?.diagnostics ?? null },
    );
  }

  const engines = Array.isArray(visual.engines) ? visual.engines : [];
  if (
    engines.length !== requiredEngines.length ||
    engines.map((engine) => engine.engine).join(",") !==
      requiredEngines.join(",")
  ) {
    addFinding(
      findings,
      "visual.engine_records",
      "Visual receipt engine records do not match the canonical scope.",
    );
  }

  const engineComputedStatus = new Map();
  for (const engine of engines) {
    const engineName = engine.engine;
    const nonAxeStart = result.nonAxeFailureIds.length;
    let engineViolationNodes = 0;
    let engineIncompleteNodes = 0;
    if (
      !emptyArray(engine?.diagnostics?.warnings) ||
      !emptyArray(engine?.diagnostics?.errors) ||
      !emptyArray(engine?.engineWideDiagnostics?.warnings) ||
      !emptyArray(engine?.engineWideDiagnostics?.errors)
    ) {
      result.nonAxeFailureIds.push(`${engineName}:diagnostics`);
    }

    const routeResults = Array.isArray(engine.routes) ? engine.routes : [];
    const expectedRouteKeys = new Set(
      CANONICAL_VIEWPORTS.flatMap((viewport) =>
        CANONICAL_ROUTES.map((route) => `${route.name}|${route.route}|${viewport.name}`),
      ),
    );
    const observedRouteKeys = new Set();
    for (const route of routeResults) {
      const key = `${route.name}|${route.route}|${route.mode}`;
      if (observedRouteKeys.has(key)) {
        result.nonAxeFailureIds.push(`${engineName}:route-duplicate:${key}`);
      }
      observedRouteKeys.add(key);
      if (
        route.pass !== true ||
        !emptyArray(route.errors) ||
        !emptyArray(route.warnings) ||
        !emptyArray(route.resourceFailures)
      ) {
        result.nonAxeFailureIds.push(`${engineName}:route:${key}`);
      }
    }
    for (const key of expectedRouteKeys) {
      if (!observedRouteKeys.has(key)) {
        result.nonAxeFailureIds.push(`${engineName}:route-missing:${key}`);
      }
    }
    for (const key of observedRouteKeys) {
      if (!expectedRouteKeys.has(key)) {
        result.nonAxeFailureIds.push(`${engineName}:route-extra:${key}`);
      }
    }

    const interactions = Array.isArray(engine.interactions) ? engine.interactions : [];
    const observedInteractions = interactions.map((item) => item.name);
    if (!same(observedInteractions, CANONICAL_INTERACTIONS)) {
      result.nonAxeFailureIds.push(`${engineName}:interaction-scope`);
    }
    for (const interaction of interactions) {
      if (
        interaction.pass !== true ||
        !emptyArray(interaction.errors) ||
        !emptyArray(interaction.warnings) ||
        !emptyArray(interaction.resourceFailures)
      ) {
        result.nonAxeFailureIds.push(
          `${engineName}:interaction:${interaction.name ?? "unknown"}`,
        );
      }
    }

    const accessibilityItems = Array.isArray(engine.accessibility)
      ? engine.accessibility
      : [];
    const observedAccessibility = new Set();
    for (const accessibility of accessibilityItems) {
      const key = `${accessibility.routeName}|${accessibility.route}`;
      if (observedAccessibility.has(key)) {
        result.nonAxeFailureIds.push(`${engineName}:accessibility-duplicate:${key}`);
      }
      observedAccessibility.add(key);
      const nonAxePass =
        accessibility?.contrast?.pass === true &&
        accessibility?.keyboard?.pass === true &&
        accessibility?.reflow200?.pass === true &&
        emptyArray(accessibility.errors) &&
        emptyArray(accessibility.warnings) &&
        emptyArray(accessibility.resourceFailures);
      if (!nonAxePass) {
        result.nonAxeFailureIds.push(`${engineName}:accessibility-non-axe:${key}`);
      }

      const axe = accessibility?.axe;
      if (
        axe?.status !== "RAN" ||
        typeof axe?.module !== "string" ||
        !axe.module ||
        typeof axe?.version !== "string" ||
        !axe.version
      ) {
        addFinding(
          findings,
          "visual.axe_not_run",
          `${engineName} ${key} has no installed axe execution evidence.`,
        );
      }
      const context = `${engineName} ${key}`;
      const violations = validateRuleNodes(
        axe?.violations,
        "violations",
        context,
        findings,
      );
      const incomplete = validateRuleNodes(
        axe?.incomplete,
        "incomplete",
        context,
        findings,
      );
      const completeNodeEvidence = violations.complete && incomplete.complete;
      if (
        axe?.completeNodeEvidence !== completeNodeEvidence ||
        axe?.violationRuleCount !== violations.ruleCount ||
        axe?.violationNodeCount !== violations.nodeCount ||
        axe?.incompleteRuleCount !== incomplete.ruleCount ||
        axe?.incompleteNodeCount !== incomplete.nodeCount
      ) {
        addFinding(
          findings,
          "visual.axe_summary_mismatch",
          `${context} axe summary does not equal the persisted rule and node evidence.`,
          {
            observed: {
              completeNodeEvidence: axe?.completeNodeEvidence ?? null,
              violationRuleCount: axe?.violationRuleCount ?? null,
              violationNodeCount: axe?.violationNodeCount ?? null,
              incompleteRuleCount: axe?.incompleteRuleCount ?? null,
              incompleteNodeCount: axe?.incompleteNodeCount ?? null,
            },
            computed: {
              completeNodeEvidence,
              violationRuleCount: violations.ruleCount,
              violationNodeCount: violations.nodeCount,
              incompleteRuleCount: incomplete.ruleCount,
              incompleteNodeCount: incomplete.nodeCount,
            },
          },
        );
      }
      if (!completeNodeEvidence || axe?.completeNodeEvidence !== true) {
        addFinding(
          findings,
          "visual.axe_node_evidence",
          `${context} axe evidence is capped, missing or incomplete.`,
        );
      }
      result.violationRuleCount += violations.ruleCount;
      result.violationNodeCount += violations.nodeCount;
      result.incompleteRuleCount += incomplete.ruleCount;
      result.incompleteNodeCount += incomplete.nodeCount;
      engineViolationNodes += violations.nodeCount;
      engineIncompleteNodes += incomplete.nodeCount;
      for (const rule of Array.isArray(axe?.incomplete) ? axe.incomplete : []) {
        if (!CANONICAL_POLICY.manualReviewableAxeIncompleteRuleIds.includes(rule.id)) {
          addFinding(
            findings,
            "visual.axe_incomplete_rule_not_reviewable",
            `${context} contains an incomplete axe rule outside the manual pixel-review boundary.`,
            {
              ruleId: rule.id ?? null,
              permitted: CANONICAL_POLICY.manualReviewableAxeIncompleteRuleIds,
            },
          );
        }
      }

      const expectedAxePass =
        completeNodeEvidence &&
        violations.ruleCount === 0 &&
        violations.nodeCount === 0 &&
        incomplete.ruleCount === 0 &&
        incomplete.nodeCount === 0;
      if (axe?.pass !== expectedAxePass) {
        addFinding(
          findings,
          "visual.axe_pass_inconsistent",
          `${context} axe pass flag hides or misstates persisted evidence.`,
          { expected: expectedAxePass, observed: axe?.pass ?? null },
        );
      }
      const expectedAccessibilityPass = nonAxePass && expectedAxePass;
      if (accessibility.pass !== expectedAccessibilityPass) {
        addFinding(
          findings,
          "visual.accessibility_pass_inconsistent",
          `${context} accessibility pass flag does not preserve axe incomplete status.`,
          { expected: expectedAccessibilityPass, observed: accessibility.pass ?? null },
        );
      }
    }
    const expectedAccessibility = new Set(
      CANONICAL_ROUTES.map((route) => `${route.name}|${route.route}`),
    );
    if (!same([...observedAccessibility].sort(), [...expectedAccessibility].sort())) {
      result.nonAxeFailureIds.push(`${engineName}:accessibility-scope`);
    }

    const performance = Array.isArray(engine.performance) ? engine.performance : [];
    const observedPerformance = new Set();
    for (const item of performance) {
      const key = `${item.routeName}|${item.route}`;
      if (observedPerformance.has(key)) {
        result.nonAxeFailureIds.push(`${engineName}:performance-duplicate:${key}`);
      }
      observedPerformance.add(key);
      const checks = item?.checks;
      const renderingGeometry = item?.renderingGeometry;
      const checksPass =
        isObject(checks) &&
        same(Object.keys(checks).sort(), [...PERFORMANCE_CHECKS].sort()) &&
        PERFORMANCE_CHECKS.every((name) => checks?.[name]?.pass === true);
      const geometryPass =
        isObject(renderingGeometry) &&
        ["RAN", "NOT_APPLICABLE", "NOT_SUPPORTED"].includes(renderingGeometry.status) &&
        renderingGeometry.method === DEFERRED_RENDER_GEOMETRY_POLICY.method &&
        same(renderingGeometry.policy, DEFERRED_RENDER_GEOMETRY_POLICY) &&
        renderingGeometry.pass === true &&
        emptyArray(renderingGeometry.failureReasons);
      if (
        item.pass !== true ||
        !same(item.budgets, PERFORMANCE_BUDGETS) ||
        !checksPass ||
        !geometryPass ||
        !emptyArray(item.errors) ||
        !emptyArray(item.warnings) ||
        !emptyArray(item.resourceFailures)
      ) {
        result.nonAxeFailureIds.push(`${engineName}:performance:${key}`);
      }
    }
    const expectedPerformance = new Set(
      CANONICAL_ROUTES.map((route) => `${route.name}|${route.route}`),
    );
    if (!same([...observedPerformance].sort(), [...expectedPerformance].sort())) {
      result.nonAxeFailureIds.push(`${engineName}:performance-scope`);
    }
    if (engine?.motion?.status !== "RAN" || engine?.motion?.pass !== true) {
      result.nonAxeFailureIds.push(`${engineName}:motion`);
    }
    const engineNonAxeFailures =
      result.nonAxeFailureIds.length - nonAxeStart;
    const expectedEnginePass =
      engineViolationNodes === 0 &&
      engineIncompleteNodes === 0 &&
      engineNonAxeFailures === 0;
    engineComputedStatus.set(engineName, {
      expectedPass: expectedEnginePass,
      violationNodes: engineViolationNodes,
      incompleteNodes: engineIncompleteNodes,
      nonAxeFailures: engineNonAxeFailures,
    });
    if (
      engine.pass !== expectedEnginePass ||
      engine.status !== (expectedEnginePass ? "PASS" : "FAIL")
    ) {
      addFinding(
        findings,
        "visual.engine_status_inconsistent",
        `${engineName} status does not preserve the automated axe result.`,
        {
          expectedPass: expectedEnginePass,
          observedPass: engine.pass ?? null,
          observedStatus: engine.status ?? null,
          violationNodes: engineViolationNodes,
          incompleteNodes: engineIncompleteNodes,
          nonAxeFailures: engineNonAxeFailures,
        },
      );
    }
  }

  if (result.violationRuleCount !== 0 || result.violationNodeCount !== 0) {
    addFinding(
      findings,
      "visual.axe_violations",
      "Automated axe violations are release blockers and cannot be manually waived.",
      {
        violationRuleCount: result.violationRuleCount,
        violationNodeCount: result.violationNodeCount,
      },
    );
  }
  if (result.nonAxeFailureIds.length) {
    addFinding(
      findings,
      "visual.non_axe_failures",
      "One or more non-axe browser, interaction, keyboard, reflow or performance gates failed.",
      { failureIds: result.nonAxeFailureIds },
    );
  }

  result.incompleteNodes = collectIncompleteNodes(visual);
  if (result.incompleteNodes.length !== result.incompleteNodeCount) {
    addFinding(
      findings,
      "visual.incomplete_identity_count",
      "Deterministic incomplete-node identities do not cover every persisted node.",
      {
        declared: result.incompleteNodeCount,
        identities: result.incompleteNodes.length,
      },
    );
  }
  const identityCounts = new Map();
  for (const node of result.incompleteNodes) {
    identityCounts.set(node.nodeId, (identityCounts.get(node.nodeId) || 0) + 1);
  }
  const collisions = [...identityCounts.entries()]
    .filter(([, count]) => count !== 1)
    .map(([nodeId, count]) => ({ nodeId, count }));
  if (collisions.length) {
    addFinding(
      findings,
      "visual.incomplete_identity_collision",
      "Axe incomplete nodes do not have unique deterministic identities.",
      { collisions },
    );
  }

  const expectedVisualPass =
    visual?.sourceBinding?.stable === true &&
    visual?.screenshotIntegrity?.pass === true &&
    emptyArray(visual?.diagnostics?.warnings) &&
    emptyArray(visual?.diagnostics?.errors) &&
    engines.length === requiredEngines.length &&
    engines.every((engine) => engineComputedStatus.get(engine.engine)?.expectedPass);
  if (
    visual.status !== (expectedVisualPass ? "PASS" : "FAIL") ||
    (result.incompleteNodeCount > 0 && visual.status !== "FAIL")
  ) {
    addFinding(
      findings,
      "visual.status_inconsistent",
      "Visual receipt status hides or misstates automated incomplete evidence.",
      {
        expected: expectedVisualPass ? "PASS" : "FAIL",
        observed: visual.status ?? null,
        incompleteNodeCount: result.incompleteNodeCount,
      },
    );
  }
  const expectedMatrixComplete =
    requiredEngines.length > 1 &&
    engines.every((engine) => engineComputedStatus.get(engine.engine)?.expectedPass);
  if (visual?.engineCoverage?.matrixComplete !== expectedMatrixComplete) {
    addFinding(
      findings,
      "visual.matrix_status_inconsistent",
      "Visual receipt matrixComplete does not match the engine evidence.",
      {
        expected: expectedMatrixComplete,
        observed: visual?.engineCoverage?.matrixComplete ?? null,
      },
    );
  }

  const screenshotDir = path.join(
    path.dirname(visualFile.absolute),
    path.basename(visualFile.absolute, ".json"),
  );
  const expectedScreenshotKeys = new Set(
    requiredEngines.flatMap((engine) =>
      CANONICAL_SCREENSHOTS.map(
        (item) => `${engine}|${item.viewport}|${item.routeName}`,
      ),
    ),
  );
  const observedScreenshotKeys = new Set();
  let observedScreenshotCount = 0;
  for (const engine of engines) {
    for (const screenshot of Array.isArray(engine.screenshots)
      ? engine.screenshots
      : []) {
      observedScreenshotCount += 1;
      const key = `${screenshot.engine}|${screenshot.viewport}|${screenshot.routeName}`;
      if (observedScreenshotKeys.has(key)) {
        result.screenshotFailures.push(`duplicate:${key}`);
      }
      observedScreenshotKeys.add(key);
      const expectedFilename = `${screenshot.engine}-${screenshot.viewport}-${screenshot.routeName}.png`;
      if (
        screenshot.filename !== expectedFilename ||
        path.basename(screenshot.filename || "") !== screenshot.filename
      ) {
        result.screenshotFailures.push(`filename:${key}`);
        continue;
      }
      const target = path.join(screenshotDir, screenshot.filename);
      if (!fs.existsSync(target) || !fs.statSync(target).isFile()) {
        result.screenshotFailures.push(`missing:${key}`);
        continue;
      }
      const observedHash = sha256File(target);
      const observedBytes = fs.statSync(target).size;
      if (
        screenshot.sha256 !== observedHash ||
        screenshot.bytes !== observedBytes ||
        screenshot.sourceTreeSha256 !== manifest.websiteTreeSha256
      ) {
        result.screenshotFailures.push(`hash-or-source:${key}`);
      }
    }
  }
  for (const key of expectedScreenshotKeys) {
    if (!observedScreenshotKeys.has(key)) {
      result.screenshotFailures.push(`missing-key:${key}`);
    }
  }
  for (const key of observedScreenshotKeys) {
    if (!expectedScreenshotKeys.has(key)) {
      result.screenshotFailures.push(`extra-key:${key}`);
    }
  }
  if (
    visual?.screenshotIntegrity?.pass !== true ||
    visual?.screenshotIntegrity?.count !== observedScreenshotCount ||
    result.screenshotFailures.length
  ) {
    addFinding(
      findings,
      "visual.screenshot_integrity",
      "Screenshot evidence is missing, altered, out of scope or bound to another source tree.",
      {
        declaredCount: visual?.screenshotIntegrity?.count ?? null,
        observedCount: observedScreenshotCount,
        failures: result.screenshotFailures,
      },
    );
  }
  return result;
}

function validateManualReview(
  manual,
  manualFile,
  visual,
  visualFile,
  manifest,
  expectedNodes,
  visualGeneratedAtMs,
  findings,
) {
  const result = {
    generatedAtMs: null,
    expectedNodeIds: expectedNodes.map((node) => node.nodeId),
    reviewedNodeIds: [],
    missingNodeIds: [],
    extraNodeIds: [],
    duplicateNodeIds: [],
    failedNodeIds: [],
    unreviewedNodeIds: [],
    contextMismatchNodeIds: [],
  };
  if (!isObject(manual)) return result;

  const expectedKeys = [
    "schema",
    "releaseId",
    "generatedAt",
    "reviewer",
    "visualReceipt",
    "websiteTreeSha256",
    "summary",
    "reviews",
  ];
  if (!exactKeys(manual, expectedKeys)) {
    addFinding(
      findings,
      "manual.shape",
      "Manual pixel-review receipt keys do not match the canonical contract.",
    );
  }
  if (manual.schema !== MANUAL_REVIEW_SCHEMA) {
    addFinding(
      findings,
      "manual.schema",
      "Manual pixel-review receipt schema is not canonical.",
      { expected: MANUAL_REVIEW_SCHEMA, observed: manual.schema ?? null },
    );
  }
  if (manual.releaseId !== manifest.releaseId) {
    addFinding(
      findings,
      "manual.release_binding",
      "Manual pixel review is bound to a different releaseId.",
      { expected: manifest.releaseId, observed: manual.releaseId ?? null },
    );
  }
  result.generatedAtMs = parseCanonicalTimestamp(
    manual.generatedAt,
    "manual pixel-review receipt generatedAt",
    findings,
  );
  if (
    !exactKeys(manual.reviewer, ["name", "method"]) ||
    typeof manual?.reviewer?.name !== "string" ||
    !manual.reviewer.name.trim() ||
    manual?.reviewer?.method !== "manual-pixel-inspection"
  ) {
    addFinding(
      findings,
      "manual.reviewer",
      "Manual pixel review needs a named reviewer and the canonical inspection method.",
    );
  }
  const expectedVisualBinding = {
    path: visualFile.relative,
    sha256: visualFile.observedHash,
    generatedAt: visual.generatedAt,
  };
  if (!same(manual.visualReceipt, expectedVisualBinding)) {
    addFinding(
      findings,
      "manual.visual_binding",
      "Manual pixel review does not bind the exact visual receipt bytes and timestamp.",
      { expected: expectedVisualBinding, observed: manual.visualReceipt ?? null },
    );
  }
  if (
    manual.websiteTreeSha256 !== manifest.websiteTreeSha256 ||
    manual.websiteTreeSha256 !== visual?.sourceBinding?.before?.sha256
  ) {
    addFinding(
      findings,
      "manual.source_binding",
      "Manual pixel review is bound to a different website source tree.",
      {
        manual: manual.websiteTreeSha256 ?? null,
        manifest: manifest.websiteTreeSha256,
        visual: visual?.sourceBinding?.before?.sha256 ?? null,
      },
    );
  }

  const expectedById = new Map(expectedNodes.map((node) => [node.nodeId, node]));
  const reviews = Array.isArray(manual.reviews) ? manual.reviews : [];
  if (!Array.isArray(manual.reviews)) {
    addFinding(
      findings,
      "manual.reviews_array",
      "Manual pixel-review receipt reviews must be an array.",
    );
  }
  const observedCounts = new Map();
  let passed = 0;
  let notApplicable = 0;
  let failed = 0;
  let explicitUnreviewed = 0;
  const reviewTimestamps = [];
  for (const [index, review] of reviews.entries()) {
    const reviewKeys = [
      "nodeId",
      "engine",
      "routeName",
      "route",
      "ruleId",
      "impact",
      "target",
      "failureSummary",
      "status",
      "reviewedAt",
      "notes",
    ];
    if (!exactKeys(review, reviewKeys)) {
      addFinding(
        findings,
        "manual.review_shape",
        `Manual review entry ${index} does not match the canonical node disposition shape.`,
      );
    }
    const nodeId = review?.nodeId;
    observedCounts.set(nodeId, (observedCounts.get(nodeId) || 0) + 1);
    result.reviewedNodeIds.push(nodeId);
    const expected = expectedById.get(nodeId);
    if (!expected) {
      result.extraNodeIds.push(nodeId ?? `index:${index}`);
    } else {
      const expectedContext = {
        engine: expected.engine,
        routeName: expected.routeName,
        route: expected.route,
        ruleId: expected.ruleId,
        impact: expected.impact,
        target: expected.target,
        failureSummary: expected.failureSummary,
      };
      const observedContext = {
        engine: review.engine,
        routeName: review.routeName,
        route: review.route,
        ruleId: review.ruleId,
        impact: review.impact,
        target: review.target,
        failureSummary: review.failureSummary,
      };
      if (
        !same(observedContext, expectedContext) ||
        incompleteNodeIdentity({
          sourceTreeSha256: manifest.websiteTreeSha256,
          ...observedContext,
        }) !== nodeId
      ) {
        result.contextMismatchNodeIds.push(nodeId);
      }
    }
    if (review.status === "verified-pass") {
      passed += 1;
    } else if (review.status === "not-applicable") {
      notApplicable += 1;
    } else if (review.status === "fail") {
      failed += 1;
      result.failedNodeIds.push(nodeId ?? `index:${index}`);
    } else if (review.status === "unreviewed") {
      explicitUnreviewed += 1;
      result.unreviewedNodeIds.push(nodeId ?? `index:${index}`);
    } else {
      result.unreviewedNodeIds.push(nodeId ?? `index:${index}`);
      addFinding(
        findings,
        "manual.review_status",
        `Manual review entry ${index} has an invalid status.`,
        { observed: review.status ?? null },
      );
    }
    if (
      review.status === "verified-pass" ||
      review.status === "not-applicable" ||
      review.status === "fail"
    ) {
      const reviewedAt = parseCanonicalTimestamp(
        review.reviewedAt,
        `manual review ${nodeId ?? index} reviewedAt`,
        findings,
      );
      if (reviewedAt !== null) reviewTimestamps.push({ nodeId, milliseconds: reviewedAt });
      if (typeof review.notes !== "string" || !review.notes.trim()) {
        addFinding(
          findings,
          "manual.review_notes",
          `Manual review ${nodeId ?? index} needs a non-empty pixel-inspection note.`,
        );
      }
    }
  }
  result.duplicateNodeIds = [...observedCounts.entries()]
    .filter(([, count]) => count > 1)
    .map(([nodeId]) => nodeId);
  result.missingNodeIds = expectedNodes
    .filter((node) => !observedCounts.has(node.nodeId))
    .map((node) => node.nodeId);
  const unreviewedTotal = explicitUnreviewed + result.missingNodeIds.length;
  const expectedSummary = {
    expectedIncompleteNodes: expectedNodes.length,
    reviewedNodes: passed + notApplicable + failed,
    verifiedPassNodes: passed,
    notApplicableNodes: notApplicable,
    failedNodes: failed,
    unreviewedNodes: unreviewedTotal,
  };
  if (!same(manual.summary, expectedSummary)) {
    addFinding(
      findings,
      "manual.summary",
      "Manual pixel-review summary does not equal the recomputed node dispositions.",
      { expected: expectedSummary, observed: manual.summary ?? null },
    );
  }
  if (
    result.missingNodeIds.length ||
    result.extraNodeIds.length ||
    result.duplicateNodeIds.length ||
    result.contextMismatchNodeIds.length
  ) {
    addFinding(
      findings,
      "manual.coverage",
      "Manual pixel review does not account exactly once for every deterministic axe incomplete node.",
      {
        missingNodeIds: result.missingNodeIds,
        extraNodeIds: result.extraNodeIds,
        duplicateNodeIds: result.duplicateNodeIds,
        contextMismatchNodeIds: result.contextMismatchNodeIds,
      },
    );
  }
  if (result.failedNodeIds.length || result.unreviewedNodeIds.length || unreviewedTotal) {
    addFinding(
      findings,
      "manual.disposition",
      "Manual pixel review contains failed or unreviewed nodes.",
      {
        failedNodeIds: result.failedNodeIds,
        unreviewedNodeIds: [
          ...new Set([...result.unreviewedNodeIds, ...result.missingNodeIds]),
        ],
      },
    );
  }
  if (
    result.generatedAtMs !== null &&
    visualGeneratedAtMs !== null &&
    result.generatedAtMs < visualGeneratedAtMs
  ) {
    addFinding(
      findings,
      "freshness.manual_predates_visual",
      "Manual pixel-review receipt predates its visual evidence.",
    );
  }
  for (const reviewTime of reviewTimestamps) {
    if (
      visualGeneratedAtMs !== null &&
      reviewTime.milliseconds < visualGeneratedAtMs
    ) {
      addFinding(
        findings,
        "freshness.review_predates_visual",
        "A manual node review predates the visual receipt.",
        { nodeId: reviewTime.nodeId },
      );
    }
    if (
      result.generatedAtMs !== null &&
      reviewTime.milliseconds > result.generatedAtMs
    ) {
      addFinding(
        findings,
        "freshness.review_after_receipt",
        "A manual node review is timestamped after its receipt.",
        { nodeId: reviewTime.nodeId },
      );
    }
  }
  return result;
}

function evaluateCompositeGate({ repoRoot, manifestPath, now = new Date() }) {
  const root = path.resolve(repoRoot);
  const manifestAbsolute = path.resolve(manifestPath);
  const findings = [];
  const nowDate = now instanceof Date ? now : new Date(now);
  if (!Number.isFinite(nowDate.getTime())) {
    throw new Error("now must be a valid Date");
  }
  const relativeManifest = path
    .relative(root, manifestAbsolute)
    .split(path.sep)
    .join("/");
  const manifestResolved = resolveRepoFile(
    root,
    relativeManifest,
    "gate manifest",
    findings,
  );
  const manifest = manifestResolved
    ? readJsonFile(manifestResolved.absolute, "gate manifest", findings)
    : null;
  const manifestSha256 = manifestResolved
    ? sha256File(manifestResolved.absolute)
    : null;

  if (manifest) validateManifest(manifest, findings);
  const currentSnapshot = snapshotWebsiteTree(path.join(root, "website"));
  if (manifest && manifest.websiteTreeSha256 !== currentSnapshot.sha256) {
    addFinding(
      findings,
      "source.current_mismatch",
      "Gate manifest is not bound to the current website tree.",
      {
        manifest: manifest.websiteTreeSha256 ?? null,
        current: currentSnapshot.sha256,
      },
    );
  }

  const manifestGeneratedAtMs = manifest
    ? parseCanonicalTimestamp(
        manifest.generatedAt,
        "gate manifest generatedAt",
        findings,
      )
    : null;
  let visualFile = null;
  let manualFile = null;
  if (manifest) {
    visualFile = readEvidenceReference(
      root,
      manifest?.evidence?.visualReceipt,
      "visual receipt",
      findings,
    );
    manualFile = readEvidenceReference(
      root,
      manifest?.evidence?.manualPixelReviewReceipt,
      "manual pixel-review receipt",
      findings,
    );
  }
  const visualResult =
    manifest && visualFile?.payload
      ? validateVisualReceipt(
          visualFile.payload,
          visualFile,
          manifest,
          currentSnapshot,
          findings,
        )
      : {
          generatedAtMs: null,
          violationRuleCount: 0,
          violationNodeCount: 0,
          incompleteRuleCount: 0,
          incompleteNodeCount: 0,
          incompleteNodes: [],
          nonAxeFailureIds: [],
          screenshotFailures: [],
        };
  const manualResult =
    manifest && visualFile?.payload && manualFile?.payload
      ? validateManualReview(
          manualFile.payload,
          manualFile,
          visualFile.payload,
          visualFile,
          manifest,
          visualResult.incompleteNodes,
          visualResult.generatedAtMs,
          findings,
        )
      : {
          generatedAtMs: null,
          expectedNodeIds: visualResult.incompleteNodes.map((node) => node.nodeId),
          reviewedNodeIds: [],
          missingNodeIds: visualResult.incompleteNodes.map((node) => node.nodeId),
          extraNodeIds: [],
          duplicateNodeIds: [],
          failedNodeIds: [],
          unreviewedNodeIds: visualResult.incompleteNodes.map((node) => node.nodeId),
          contextMismatchNodeIds: [],
        };

  const nowMs = nowDate.getTime();
  validateFreshTimestamp(manifestGeneratedAtMs, "gate manifest", nowMs, findings);
  validateFreshTimestamp(
    visualResult.generatedAtMs,
    "visual receipt",
    nowMs,
    findings,
  );
  validateFreshTimestamp(
    manualResult.generatedAtMs,
    "manual pixel-review receipt",
    nowMs,
    findings,
  );
  if (
    manifestGeneratedAtMs !== null &&
    manualResult.generatedAtMs !== null &&
    manifestGeneratedAtMs < manualResult.generatedAtMs
  ) {
    addFinding(
      findings,
      "freshness.manifest_predates_manual",
      "Gate manifest predates the manual pixel-review receipt.",
    );
  }

  const uniqueFindings = [];
  const seenFindings = new Set();
  for (const finding of findings) {
    const key = stableStringify(finding);
    if (!seenFindings.has(key)) {
      seenFindings.add(key);
      uniqueFindings.push(finding);
    }
  }
  const state = uniqueFindings.length === 0 ? "pass" : "blocked";
  return {
    schema: GATE_RECEIPT_SCHEMA,
    generatedAt: nowDate.toISOString(),
    state,
    releaseId: manifest?.releaseId ?? null,
    intent: manifest?.intent ?? null,
    manifest: {
      path: manifestResolved?.relative ?? relativeManifest,
      sha256: manifestSha256,
      schema: manifest?.schema ?? null,
      generatedAt: manifest?.generatedAt ?? null,
    },
    policy: CANONICAL_POLICY,
    scope: manifest?.scope ?? null,
    sourceBinding: {
      manifestSha256: manifest?.websiteTreeSha256 ?? null,
      visualBeforeSha256:
        visualFile?.payload?.sourceBinding?.before?.sha256 ?? null,
      visualAfterSha256:
        visualFile?.payload?.sourceBinding?.after?.sha256 ?? null,
      currentWebsiteTreeSha256: currentSnapshot.sha256,
      currentFileCount: currentSnapshot.fileCount,
      currentTotalBytes: currentSnapshot.totalBytes,
      pass:
        Boolean(manifest) &&
        manifest.websiteTreeSha256 === currentSnapshot.sha256 &&
        visualFile?.payload?.sourceBinding?.stable === true &&
        visualFile?.payload?.sourceBinding?.before?.sha256 ===
          currentSnapshot.sha256 &&
        visualFile?.payload?.sourceBinding?.after?.sha256 ===
          currentSnapshot.sha256,
    },
    visualEvidence: {
      path: visualFile?.relative ?? manifest?.evidence?.visualReceipt?.path ?? null,
      sha256: visualFile?.observedHash ?? null,
      schema: visualFile?.payload?.schema ?? null,
      generatedAt: visualFile?.payload?.generatedAt ?? null,
      automatedStatus: visualFile?.payload?.status ?? null,
      axeInstalled: visualFile?.payload?.capabilities?.axe?.status === "INSTALLED",
      completeNodeEvidence:
        visualResult.incompleteNodes.length === visualResult.incompleteNodeCount &&
        !uniqueFindings.some((item) =>
          [
            "visual.axe_node_evidence",
            "visual.axe_node_shape",
            "visual.axe_summary_mismatch",
            "visual.incomplete_identity_count",
            "visual.incomplete_identity_collision",
          ].includes(item.code),
        ),
      violationRuleCount: visualResult.violationRuleCount,
      violationNodeCount: visualResult.violationNodeCount,
      incompleteRuleCount: visualResult.incompleteRuleCount,
      incompleteNodeCount: visualResult.incompleteNodeCount,
      incompleteNodeIds: visualResult.incompleteNodes.map((node) => node.nodeId),
      nonAxeFailureIds: visualResult.nonAxeFailureIds,
      screenshotFailures: visualResult.screenshotFailures,
    },
    manualPixelReview: {
      path:
        manualFile?.relative ??
        manifest?.evidence?.manualPixelReviewReceipt?.path ??
        null,
      sha256: manualFile?.observedHash ?? null,
      schema: manualFile?.payload?.schema ?? null,
      generatedAt: manualFile?.payload?.generatedAt ?? null,
      expectedNodeCount: visualResult.incompleteNodes.length,
      reviewRecordCount: Array.isArray(manualFile?.payload?.reviews)
        ? manualFile.payload.reviews.length
        : 0,
      missingNodeIds: manualResult.missingNodeIds,
      extraNodeIds: manualResult.extraNodeIds,
      duplicateNodeIds: manualResult.duplicateNodeIds,
      contextMismatchNodeIds: manualResult.contextMismatchNodeIds,
      failedNodeIds: manualResult.failedNodeIds,
      unreviewedNodeIds: [
        ...new Set([
          ...manualResult.unreviewedNodeIds,
          ...manualResult.missingNodeIds,
        ]),
      ],
    },
    summary: {
      blockers: uniqueFindings.length,
      axeViolations: visualResult.violationNodeCount,
      axeIncompleteNodes: visualResult.incompleteNodeCount,
      manualFailures: manualResult.failedNodeIds.length,
      manualUnreviewed: new Set([
        ...manualResult.unreviewedNodeIds,
        ...manualResult.missingNodeIds,
      ]).size,
      nonAxeFailures: visualResult.nonAxeFailureIds.length,
      screenshotFailures: visualResult.screenshotFailures.length,
    },
    findings: uniqueFindings,
    boundary: {
      automatedAxeIncompletePreserved: true,
      automatedVisualStatus:
        visualFile?.payload?.status ?? "unavailable",
      compositePassRequiresSeparateManualReceipt: true,
      missingManualEvidenceCanPass: false,
      publicationAuthority: "none",
    },
  };
}

function usage() {
  return `Usage:
  node tools/aureon_visual_release_gate_v28.js --manifest PATH [--output PATH] [--repo-root PATH]

Validates the canonical V28 gate manifest, strict V28.3 axe receipt and separate
manual pixel-review receipt. The command exits 0 only for a fully bound PASS.
It never changes website source or converts axe incomplete evidence into an
automated PASS.
`;
}

function parseCli(argv) {
  const options = {
    manifest: null,
    output: null,
    repoRoot: path.resolve(__dirname, ".."),
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
    if (argument === "--manifest" || argument.startsWith("--manifest=")) {
      const [value, nextIndex] = takeValue(argument, index);
      options.manifest = value;
      index = nextIndex;
      continue;
    }
    if (argument === "--output" || argument.startsWith("--output=")) {
      const [value, nextIndex] = takeValue(argument, index);
      options.output = value;
      index = nextIndex;
      continue;
    }
    if (argument === "--repo-root" || argument.startsWith("--repo-root=")) {
      const [value, nextIndex] = takeValue(argument, index);
      options.repoRoot = path.resolve(value);
      index = nextIndex;
      continue;
    }
    throw new Error(`Unknown argument: ${argument}`);
  }
  if (!options.help && !options.manifest) {
    throw new Error("--manifest is required");
  }
  return options;
}

function writeReceipt(repoRoot, output, receipt) {
  const root = path.resolve(repoRoot);
  const target = path.resolve(root, output);
  const relative = path.relative(root, target);
  if (relative.startsWith("..") || path.isAbsolute(relative)) {
    throw new Error("--output must stay inside the repository");
  }
  if (fs.existsSync(target)) {
    throw new Error(`Refusing to overwrite gate receipt: ${target}`);
  }
  fs.mkdirSync(path.dirname(target), { recursive: true });
  fs.writeFileSync(target, `${JSON.stringify(receipt, null, 2)}\n`, {
    encoding: "utf8",
    flag: "wx",
  });
  return target;
}

function main(argv = process.argv.slice(2)) {
  const options = parseCli(argv);
  if (options.help) {
    process.stdout.write(usage());
    return 0;
  }
  const manifestPath = path.resolve(options.repoRoot, options.manifest);
  const receipt = evaluateCompositeGate({
    repoRoot: options.repoRoot,
    manifestPath,
  });
  let output = null;
  if (options.output) {
    output = writeReceipt(options.repoRoot, options.output, receipt);
  }
  process.stdout.write(
    `${JSON.stringify(
      {
        state: receipt.state,
        blockers: receipt.summary.blockers,
        axeViolations: receipt.summary.axeViolations,
        axeIncompleteNodes: receipt.summary.axeIncompleteNodes,
        manualFailures: receipt.summary.manualFailures,
        manualUnreviewed: receipt.summary.manualUnreviewed,
        sourceTreeSha256: receipt.sourceBinding.currentWebsiteTreeSha256,
        output,
      },
      null,
      2,
    )}\n`,
  );
  return receipt.state === "pass" ? 0 : 1;
}

module.exports = {
  CANONICAL_POLICY,
  CANONICAL_INTERACTIONS,
  CANONICAL_ROUTES,
  CANONICAL_SCREENSHOTS,
  CANONICAL_VIEWPORTS,
  FINAL_RELEASE_ENGINES,
  GATE_ID,
  GATE_RECEIPT_SCHEMA,
  MANIFEST_SCHEMA,
  MANUAL_REVIEW_SCHEMA,
  MAX_EVIDENCE_AGE_SECONDS,
  VISUAL_RECEIPT_SCHEMA,
  canonicalScope,
  collectIncompleteNodes,
  evaluateCompositeGate,
  incompleteNodeIdentity,
  parseCli,
  stableStringify,
};

if (require.main === module) {
  try {
    process.exitCode = main();
  } catch (error) {
    process.stderr.write(`${error.stack || error.message}\n`);
    process.exitCode = 1;
  }
}

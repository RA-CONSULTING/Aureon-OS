"use strict";

const assert = require("node:assert/strict");
const { spawnSync } = require("node:child_process");
const crypto = require("node:crypto");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const test = require("node:test");

const {
  DEFERRED_RENDER_GEOMETRY_POLICY,
  PERFORMANCE_BUDGETS,
  SCREENSHOT_CAPTURE_SCOPE,
  snapshotWebsiteTree,
} = require("../tools/aureon_website_visual_qa_v28.js");
const {
  CANONICAL_INTERACTIONS,
  CANONICAL_POLICY,
  CANONICAL_ROUTES,
  CANONICAL_SCREENSHOTS,
  CANONICAL_VIEWPORTS,
  GATE_ID,
  MANIFEST_SCHEMA,
  MANUAL_REVIEW_SCHEMA,
  VISUAL_RECEIPT_SCHEMA,
  canonicalScope,
  collectIncompleteNodes,
  evaluateCompositeGate,
  incompleteNodeIdentity,
  parseCli,
} = require("../tools/aureon_visual_release_gate_v28.js");

const NOW = new Date("2026-07-26T18:00:00.000Z");
const VISUAL_AT = "2026-07-26T17:00:00.000Z";
const REVIEWED_AT = "2026-07-26T17:15:00.000Z";
const MANUAL_AT = "2026-07-26T17:30:00.000Z";
const MANIFEST_AT = "2026-07-26T17:40:00.000Z";
const PERFORMANCE_CHECK_NAMES = [
  "ttfb",
  "domContentLoaded",
  "loadEvent",
  "lcp",
  "cls",
  "requestCount",
  "transferProxyBytes",
  "longTaskTotal",
];

function sha256File(filePath) {
  return crypto.createHash("sha256").update(fs.readFileSync(filePath)).digest("hex");
}

function writeJson(filePath, payload) {
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
  fs.writeFileSync(filePath, `${JSON.stringify(payload, null, 2)}\n`, "utf8");
}

function readJson(filePath) {
  return JSON.parse(fs.readFileSync(filePath, "utf8"));
}

function relative(root, filePath) {
  return path.relative(root, filePath).split(path.sep).join("/");
}

function makeRouteResults() {
  return CANONICAL_VIEWPORTS.flatMap((viewport) =>
    CANONICAL_ROUTES.map((route) => ({
      name: route.name,
      route: route.route,
      mode: viewport.name,
      status: 200,
      errors: [],
      warnings: [],
      resourceFailures: [],
      allowedResourceFailures: [],
      pass: true,
    })),
  );
}

function makeAccessibility(engineName) {
  return CANONICAL_ROUTES.map((route, index) => {
    const incomplete =
      index === 0
        ? [
            {
              id: "color-contrast",
              impact: "serious",
              help: "Elements must meet minimum color contrast ratio thresholds",
              helpUrl: "https://example.test/axe/color-contrast",
              nodeCount: 1,
              nodes: [
                {
                  target: [`.${engineName}-hero-title`],
                  failureSummary:
                    "Element background requires deterministic rendered-pixel review.",
                },
              ],
            },
          ]
        : [];
    const incompleteNodeCount = incomplete.reduce(
      (total, rule) => total + rule.nodes.length,
      0,
    );
    const axePass = incomplete.length === 0;
    return {
      routeName: route.name,
      route: route.route,
      contrast: { pass: true },
      axe: {
        status: "RAN",
        module: "axe-core",
        version: "4.10.3",
        violations: [],
        incomplete,
        completeNodeEvidence: true,
        violationRuleCount: 0,
        violationNodeCount: 0,
        incompleteRuleCount: incomplete.length,
        incompleteNodeCount,
        pass: axePass,
      },
      keyboard: { pass: true },
      reflow200: { pass: true },
      errors: [],
      warnings: [],
      resourceFailures: [],
      pass: axePass,
    };
  });
}

function makePerformance() {
  return CANONICAL_ROUTES.map((route) => ({
    routeName: route.name,
    route: route.route,
    metrics: {},
    budgets: PERFORMANCE_BUDGETS,
    checks: Object.fromEntries(
      PERFORMANCE_CHECK_NAMES.map((name) => [name, { pass: true }]),
    ),
    renderingGeometry: {
      status: "NOT_APPLICABLE",
      method: DEFERRED_RENDER_GEOMETRY_POLICY.method,
      policy: DEFERRED_RENDER_GEOMETRY_POLICY,
      pass: true,
      failureReasons: [],
    },
    errors: [],
    warnings: [],
    resourceFailures: [],
    pass: true,
  }));
}

function createFixture(t, { intent = "final-release" } = {}) {
  const repoRoot = fs.mkdtempSync(path.join(os.tmpdir(), "aureon-v28-gate-"));
  t.after(() => fs.rmSync(repoRoot, { recursive: true, force: true }));
  const websiteRoot = path.join(repoRoot, "website");
  fs.mkdirSync(websiteRoot, { recursive: true });
  fs.writeFileSync(
    path.join(websiteRoot, "index.html"),
    "<!doctype html><title>Gate fixture</title>\n",
    "utf8",
  );
  fs.writeFileSync(path.join(websiteRoot, "styles.css"), "body { color: #111; }\n", "utf8");
  const sourceSnapshot = snapshotWebsiteTree(websiteRoot);
  const scope = canonicalScope(intent);
  const auditRoot = path.join(repoRoot, "docs", "audits");
  fs.mkdirSync(auditRoot, { recursive: true });
  const visualName = "AUREON_WEBSITE_VISUAL_QA_20260726T170000Z_V28";
  const visualPath = path.join(auditRoot, `${visualName}.json`);
  const visualDir = path.join(auditRoot, visualName);
  fs.mkdirSync(visualDir, { recursive: true });

  const engines = scope.engines.map((engineName) => {
    const screenshots = CANONICAL_SCREENSHOTS.map((definition) => {
      const filename = `${engineName}-${definition.viewport}-${definition.routeName}.png`;
      const absolute = path.join(visualDir, filename);
      fs.writeFileSync(
        absolute,
        Buffer.from(`${engineName}:${definition.viewport}:${definition.routeName}`, "utf8"),
      );
      return {
        engine: engineName,
        viewport: definition.viewport,
        routeName: definition.routeName,
        filename,
        bytes: fs.statSync(absolute).size,
        sha256: sha256File(absolute),
        sourceTreeSha256: sourceSnapshot.sha256,
      };
    });
    return {
      engine: engineName,
      status: "FAIL",
      executable: "playwright-managed",
      browserVersion: `${engineName}-fixture`,
      unsupportedReason: null,
      routes: makeRouteResults(),
      interactions: CANONICAL_INTERACTIONS.map((name) => ({
        name,
        errors: [],
        warnings: [],
        resourceFailures: [],
        pass: true,
      })),
      accessibility: makeAccessibility(engineName),
      performance: makePerformance(),
      motion: { status: "RAN", pass: true },
      screenshots,
      engineWideDiagnostics: { warnings: [], errors: [] },
      diagnostics: { warnings: [], errors: [] },
      pass: false,
    };
  });

  const visual = {
    schema: VISUAL_RECEIPT_SCHEMA,
    generatedAt: VISUAL_AT,
    baseUrl: "http://127.0.0.1:43111",
    status: "FAIL",
    selfHosted: true,
    playwrightSource: "fixture",
    capabilities: {
      axe: { status: "INSTALLED", module: "axe-core", version: "4.10.3" },
    },
    engineCoverage: {
      requested: scope.engines,
      selectionExplicit: scope.engines.length === 1,
      mode:
        scope.engines.length === 1
          ? "explicit-single-engine-coverage"
          : "requested-browser-engine-matrix",
      matrixComplete: false,
      unsupported: [],
    },
    selectedRoutes: CANONICAL_ROUTES,
    selectedViewports: CANONICAL_VIEWPORTS,
    policies: {
      performanceBudgets: PERFORMANCE_BUDGETS,
      deferredRenderGeometry: DEFERRED_RENDER_GEOMETRY_POLICY,
      accessibilityThresholds: {},
      axeCoreRequired: true,
      axeNodeEvidencePolicy:
        "Every axe violation and incomplete node must be persisted; capped samples fail closed.",
      warningAndErrorPolicy: "Any captured warning or error fails the report.",
      unsupportedEnginePolicy: "Any requested unsupported engine fails the report.",
    },
    sourceBinding: {
      before: sourceSnapshot,
      after: JSON.parse(JSON.stringify(sourceSnapshot)),
      stable: true,
      servedFromHashedSource: true,
    },
    screenshotIntegrity: {
      count: engines.reduce((total, engine) => total + engine.screenshots.length, 0),
      pass: true,
    },
    diagnostics: { warnings: [], errors: [] },
    engines,
  };
  writeJson(visualPath, visual);
  const visualHash = sha256File(visualPath);
  const expectedNodes = collectIncompleteNodes(visual);
  const releaseId = `fixture-${intent}`;
  const reviews = expectedNodes.map((node) => ({
    nodeId: node.nodeId,
    engine: node.engine,
    routeName: node.routeName,
    route: node.route,
    ruleId: node.ruleId,
    impact: node.impact,
    target: node.target,
    failureSummary: node.failureSummary,
    status: "verified-pass",
    reviewedAt: REVIEWED_AT,
    notes: "Rendered pixels were inspected and the applicable contrast threshold passed.",
  }));
  const manual = {
    schema: MANUAL_REVIEW_SCHEMA,
    releaseId,
    generatedAt: MANUAL_AT,
    reviewer: {
      name: "Fixture Reviewer",
      method: "manual-pixel-inspection",
    },
    visualReceipt: {
      path: relative(repoRoot, visualPath),
      sha256: visualHash,
      generatedAt: visual.generatedAt,
    },
    websiteTreeSha256: sourceSnapshot.sha256,
    summary: {
      expectedIncompleteNodes: expectedNodes.length,
      reviewedNodes: reviews.length,
      verifiedPassNodes: reviews.length,
      notApplicableNodes: 0,
      failedNodes: 0,
      unreviewedNodes: 0,
    },
    reviews,
  };
  const manualPath = path.join(
    auditRoot,
    "AUREON_WEBSITE_MANUAL_PIXEL_REVIEW_20260726T173000Z_V28.json",
  );
  writeJson(manualPath, manual);
  const manifest = {
    schema: MANIFEST_SCHEMA,
    gateId: GATE_ID,
    intent,
    releaseId,
    generatedAt: MANIFEST_AT,
    websiteTreeSha256: sourceSnapshot.sha256,
    scope,
    policy: CANONICAL_POLICY,
    evidence: {
      visualReceipt: {
        path: relative(repoRoot, visualPath),
        sha256: visualHash,
      },
      manualPixelReviewReceipt: {
        path: relative(repoRoot, manualPath),
        sha256: sha256File(manualPath),
      },
    },
  };
  const manifestPath = path.join(
    auditRoot,
    "AUREON_VISUAL_RELEASE_GATE_20260726T174000Z_V28.manifest.json",
  );
  writeJson(manifestPath, manifest);
  return {
    repoRoot,
    websiteRoot,
    visualPath,
    manualPath,
    manifestPath,
  };
}

function rebindManual(fixture, mutate) {
  const manual = readJson(fixture.manualPath);
  mutate(manual);
  writeJson(fixture.manualPath, manual);
  const manifest = readJson(fixture.manifestPath);
  manifest.evidence.manualPixelReviewReceipt.sha256 = sha256File(fixture.manualPath);
  writeJson(fixture.manifestPath, manifest);
}

function rebindVisual(fixture, mutate) {
  const visual = readJson(fixture.visualPath);
  mutate(visual);
  writeJson(fixture.visualPath, visual);
  const visualHash = sha256File(fixture.visualPath);
  const manual = readJson(fixture.manualPath);
  manual.visualReceipt.sha256 = visualHash;
  manual.visualReceipt.generatedAt = visual.generatedAt;
  writeJson(fixture.manualPath, manual);
  const manifest = readJson(fixture.manifestPath);
  manifest.evidence.visualReceipt.sha256 = visualHash;
  manifest.evidence.manualPixelReviewReceipt.sha256 = sha256File(fixture.manualPath);
  writeJson(fixture.manifestPath, manifest);
}

function findingCodes(receipt) {
  return new Set(receipt.findings.map((finding) => finding.code));
}

test("deterministic incomplete identity matches the authoritative V28 formula", () => {
  const nodeId = incompleteNodeIdentity({
    engine: "chromium",
    route: "/",
    ruleId: "color-contrast",
    target: ['.text-link[href$="projects/#core"] > span[aria-hidden="true"]'],
  });
  assert.equal(
    nodeId,
    "axei1-b5e1229be3053a8e0567fbe2610a77c128c1863861fe4b4e937095e1995f1ed1",
  );
});

test("canonical release screenshots match the QA capture scope and include investor desktop", () => {
  const qaScope = SCREENSHOT_CAPTURE_SCOPE.flatMap((definition) =>
    definition.routeNames.map((routeName) => ({ viewport: definition.viewportName, routeName })),
  );
  assert.deepEqual(CANONICAL_SCREENSHOTS, qaScope);
  assert(CANONICAL_SCREENSHOTS.some((item) => item.viewport === "desktop" && item.routeName === "investor"));
});

test("CLI requires one explicit manifest and keeps output optional", () => {
  assert.deepEqual(
    {
      manifest: parseCli(["--manifest=docs/audits/gate.json"]).manifest,
      output: parseCli(["--manifest=docs/audits/gate.json"]).output,
    },
    { manifest: "docs/audits/gate.json", output: null },
  );
  assert.throws(() => parseCli([]), /--manifest is required/);
  assert.throws(
    () => parseCli(["--manifest=gate.json", "--allow-incomplete"]),
    /Unknown argument/,
  );
});

test("final release passes only with the complete three-engine composite evidence", (t) => {
  const fixture = createFixture(t);
  const receipt = evaluateCompositeGate({
    repoRoot: fixture.repoRoot,
    manifestPath: fixture.manifestPath,
    now: NOW,
  });
  assert.equal(receipt.state, "pass");
  assert.equal(receipt.intent, "final-release");
  assert.deepEqual(receipt.scope.engines, ["chromium", "firefox", "webkit"]);
  assert.equal(receipt.visualEvidence.automatedStatus, "FAIL");
  assert.equal(receipt.visualEvidence.violationNodeCount, 0);
  assert.equal(receipt.visualEvidence.incompleteNodeCount, 3);
  assert.equal(receipt.manualPixelReview.reviewRecordCount, 3);
  assert.equal(receipt.summary.blockers, 0);
});

test("release schemas match the exact final and remediation engine contracts", (t) => {
  const fixture = createFixture(t);
  const schemaRoot = path.join(
    __dirname,
    "..",
    "docs",
    "research",
    "schemas",
  );
  const manualSchema = readJson(
    path.join(schemaRoot, "AUREON_MANUAL_PIXEL_REVIEW_V28.schema.json"),
  );
  const manifestSchema = readJson(
    path.join(schemaRoot, "AUREON_VISUAL_RELEASE_GATE_MANIFEST_V28.schema.json"),
  );
  const finalEngines = canonicalScope("final-release").engines;
  const remediationEngines = canonicalScope("remediation-evidence").engines;
  const manualSchemaEngines =
    manualSchema.$defs.nodeReview.properties.engine.enum;
  const manifestPolicy = manifestSchema.properties.policy.const;
  const manifestIntentBranch = manifestSchema.allOf[0];
  const manual = readJson(fixture.manualPath);
  const receiptEngines = [
    ...new Set(manual.reviews.map((review) => review.engine)),
  ];

  assert.deepEqual(manualSchemaEngines, finalEngines);
  assert.deepEqual(manifestPolicy.requiredFinalReleaseEngines, finalEngines);
  assert.deepEqual(manifestPolicy.permittedRemediationEngines, remediationEngines);
  assert.deepEqual(
    manifestIntentBranch.then.properties.scope.properties.engines.const,
    finalEngines,
  );
  assert.deepEqual(
    manifestIntentBranch.else.properties.scope.properties.engines.const,
    remediationEngines,
  );
  assert.deepEqual(receiptEngines, finalEngines);
  for (const review of manual.reviews) {
    assert(manualSchemaEngines.includes(review.engine));
  }

  const receipt = evaluateCompositeGate({
    repoRoot: fixture.repoRoot,
    manifestPath: fixture.manifestPath,
    now: NOW,
  });
  assert.equal(receipt.state, "pass");
});

test("CLI emits a reusable receipt and exits zero only for final PASS", (t) => {
  const fixture = createFixture(t);
  const clock = Date.now();
  const visual = readJson(fixture.visualPath);
  visual.generatedAt = new Date(clock - 30 * 60 * 1000).toISOString();
  writeJson(fixture.visualPath, visual);
  const manual = readJson(fixture.manualPath);
  manual.generatedAt = new Date(clock - 10 * 60 * 1000).toISOString();
  manual.visualReceipt.generatedAt = visual.generatedAt;
  manual.visualReceipt.sha256 = sha256File(fixture.visualPath);
  for (const review of manual.reviews) {
    review.reviewedAt = new Date(clock - 20 * 60 * 1000).toISOString();
  }
  writeJson(fixture.manualPath, manual);
  const manifest = readJson(fixture.manifestPath);
  manifest.generatedAt = new Date(clock - 5 * 60 * 1000).toISOString();
  manifest.evidence.visualReceipt.sha256 = sha256File(fixture.visualPath);
  manifest.evidence.manualPixelReviewReceipt.sha256 = sha256File(fixture.manualPath);
  writeJson(fixture.manifestPath, manifest);
  const tool = path.resolve(__dirname, "..", "tools", "aureon_visual_release_gate_v28.js");
  const output = "artifacts/website-operator/final-visual-gate.json";
  const completed = spawnSync(
    process.execPath,
    [
      tool,
      "--repo-root",
      fixture.repoRoot,
      "--manifest",
      relative(fixture.repoRoot, fixture.manifestPath),
      "--output",
      output,
    ],
    { cwd: fixture.repoRoot, encoding: "utf8" },
  );
  assert.equal(completed.status, 0, completed.stderr);
  const summary = JSON.parse(completed.stdout);
  assert.equal(summary.state, "pass");
  assert.equal(summary.blockers, 0);
  const receipt = readJson(path.join(fixture.repoRoot, output));
  assert.equal(receipt.state, "pass");
  assert.equal(receipt.summary.blockers, 0);
});

test("reviewed not-applicable nodes remain explicit and can satisfy manual coverage", (t) => {
  const fixture = createFixture(t);
  rebindManual(fixture, (manual) => {
    manual.reviews[0].status = "not-applicable";
    manual.reviews[0].notes =
      "The target is an aria-hidden decorative glyph and has no text contrast requirement.";
    manual.summary.verifiedPassNodes -= 1;
    manual.summary.notApplicableNodes = 1;
  });
  const receipt = evaluateCompositeGate({
    repoRoot: fixture.repoRoot,
    manifestPath: fixture.manifestPath,
    now: NOW,
  });
  assert.equal(receipt.state, "pass");
  assert.equal(receipt.summary.manualFailures, 0);
  assert.equal(receipt.summary.manualUnreviewed, 0);
});

test("Chromium-only evidence remains explicitly remediation-only", (t) => {
  const fixture = createFixture(t, { intent: "remediation-evidence" });
  const receipt = evaluateCompositeGate({
    repoRoot: fixture.repoRoot,
    manifestPath: fixture.manifestPath,
    now: NOW,
  });
  assert.equal(receipt.state, "blocked");
  assert(findingCodes(receipt).has("manifest.remediation_only"));
  assert(!findingCodes(receipt).has("visual.engine_scope"));
  assert.equal(receipt.summary.axeIncompleteNodes, 1);
});

test("missing, failed or unreviewed manual node evidence cannot pass", async (t) => {
  await t.test("missing node", (child) => {
    const fixture = createFixture(child);
    rebindManual(fixture, (manual) => {
      manual.reviews.pop();
      manual.summary.reviewedNodes -= 1;
      manual.summary.verifiedPassNodes -= 1;
      manual.summary.unreviewedNodes = 1;
    });
    const receipt = evaluateCompositeGate({
      repoRoot: fixture.repoRoot,
      manifestPath: fixture.manifestPath,
      now: NOW,
    });
    assert.equal(receipt.state, "blocked");
    assert(findingCodes(receipt).has("manual.coverage"));
    assert(findingCodes(receipt).has("manual.disposition"));
    assert.equal(receipt.summary.manualUnreviewed, 1);
  });

  await t.test("failed node", (child) => {
    const fixture = createFixture(child);
    rebindManual(fixture, (manual) => {
      manual.reviews[0].status = "fail";
      manual.reviews[0].notes = "Rendered pixels do not meet the required contrast.";
      manual.summary.verifiedPassNodes -= 1;
      manual.summary.failedNodes = 1;
    });
    const receipt = evaluateCompositeGate({
      repoRoot: fixture.repoRoot,
      manifestPath: fixture.manifestPath,
      now: NOW,
    });
    assert.equal(receipt.state, "blocked");
    assert(findingCodes(receipt).has("manual.disposition"));
    assert.equal(receipt.summary.manualFailures, 1);
  });
});

test("capped axe evidence and axe violations are never manually waivable", async (t) => {
  await t.test("capped incomplete rule", (child) => {
    const fixture = createFixture(child);
    rebindVisual(fixture, (visual) => {
      const axe = visual.engines[0].accessibility[0].axe;
      axe.incomplete[0].nodeCount = 2;
      axe.completeNodeEvidence = false;
      axe.incompleteNodeCount = 2;
    });
    const receipt = evaluateCompositeGate({
      repoRoot: fixture.repoRoot,
      manifestPath: fixture.manifestPath,
      now: NOW,
    });
    assert.equal(receipt.state, "blocked");
    assert(findingCodes(receipt).has("visual.axe_node_evidence"));
  });

  await t.test("automated violation", (child) => {
    const fixture = createFixture(child);
    rebindVisual(fixture, (visual) => {
      const axe = visual.engines[0].accessibility[0].axe;
      axe.violations = [
        {
          id: "button-name",
          impact: "critical",
          help: "Buttons must have discernible text",
          helpUrl: "https://example.test/axe/button-name",
          nodeCount: 1,
          nodes: [
            {
              target: [".unnamed-button"],
              failureSummary: "Element does not have inner text.",
            },
          ],
        },
      ];
      axe.violationRuleCount = 1;
      axe.violationNodeCount = 1;
    });
    const receipt = evaluateCompositeGate({
      repoRoot: fixture.repoRoot,
      manifestPath: fixture.manifestPath,
      now: NOW,
    });
    assert.equal(receipt.state, "blocked");
    assert(findingCodes(receipt).has("visual.axe_violations"));
  });

  await t.test("unknown incomplete rule", (child) => {
    const fixture = createFixture(child);
    rebindVisual(fixture, (visual) => {
      visual.engines[0].accessibility[0].axe.incomplete[0].id = "unknown-rule";
    });
    const receipt = evaluateCompositeGate({
      repoRoot: fixture.repoRoot,
      manifestPath: fixture.manifestPath,
      now: NOW,
    });
    assert.equal(receipt.state, "blocked");
    assert(
      findingCodes(receipt).has("visual.axe_incomplete_rule_not_reviewable"),
    );
  });
});

test("non-axe failures, stale evidence, hashes and current source all fail closed", async (t) => {
  await t.test("non-axe route failure", (child) => {
    const fixture = createFixture(child);
    rebindVisual(fixture, (visual) => {
      visual.engines[1].routes[0].pass = false;
    });
    const receipt = evaluateCompositeGate({
      repoRoot: fixture.repoRoot,
      manifestPath: fixture.manifestPath,
      now: NOW,
    });
    assert.equal(receipt.state, "blocked");
    assert(findingCodes(receipt).has("visual.non_axe_failures"));
  });

  await t.test("failed rendering geometry", (child) => {
    const fixture = createFixture(child);
    rebindVisual(fixture, (visual) => {
      const performance = visual.engines[0].performance.find(
        (item) => item.routeName === "investor",
      );
      performance.renderingGeometry.pass = false;
      performance.renderingGeometry.failureReasons = ["scroll-height:24>2"];
      performance.pass = false;
    });
    const receipt = evaluateCompositeGate({
      repoRoot: fixture.repoRoot,
      manifestPath: fixture.manifestPath,
      now: NOW,
    });
    assert.equal(receipt.state, "blocked");
    assert(findingCodes(receipt).has("visual.non_axe_failures"));
  });

  await t.test("visual hash mismatch", (child) => {
    const fixture = createFixture(child);
    fs.appendFileSync(fixture.visualPath, " \n", "utf8");
    const receipt = evaluateCompositeGate({
      repoRoot: fixture.repoRoot,
      manifestPath: fixture.manifestPath,
      now: NOW,
    });
    assert.equal(receipt.state, "blocked");
    assert(findingCodes(receipt).has("evidence.hash_mismatch"));
  });

  await t.test("current source drift", (child) => {
    const fixture = createFixture(child);
    fs.appendFileSync(path.join(fixture.websiteRoot, "index.html"), "<!-- drift -->\n");
    const receipt = evaluateCompositeGate({
      repoRoot: fixture.repoRoot,
      manifestPath: fixture.manifestPath,
      now: NOW,
    });
    assert.equal(receipt.state, "blocked");
    assert(findingCodes(receipt).has("source.current_mismatch"));
    assert(findingCodes(receipt).has("visual.source_mismatch"));
  });

  await t.test("stale evidence", (child) => {
    const fixture = createFixture(child);
    const receipt = evaluateCompositeGate({
      repoRoot: fixture.repoRoot,
      manifestPath: fixture.manifestPath,
      now: new Date("2026-07-28T18:00:00.000Z"),
    });
    assert.equal(receipt.state, "blocked");
    assert(findingCodes(receipt).has("freshness.stale_evidence"));
  });
});

test("final-release manifest cannot shrink the required engine scope", (t) => {
  const fixture = createFixture(t);
  const manifest = readJson(fixture.manifestPath);
  manifest.scope.engines = ["chromium"];
  writeJson(fixture.manifestPath, manifest);
  const receipt = evaluateCompositeGate({
    repoRoot: fixture.repoRoot,
    manifestPath: fixture.manifestPath,
    now: NOW,
  });
  assert.equal(receipt.state, "blocked");
  assert(findingCodes(receipt).has("manifest.scope"));
});

test("canonical manifest policy cannot be caller-weakened", (t) => {
  const fixture = createFixture(t);
  const manifest = readJson(fixture.manifestPath);
  manifest.policy.requireZeroAxeViolations = false;
  writeJson(fixture.manifestPath, manifest);
  const receipt = evaluateCompositeGate({
    repoRoot: fixture.repoRoot,
    manifestPath: fixture.manifestPath,
    now: NOW,
  });
  assert.equal(receipt.state, "blocked");
  assert(findingCodes(receipt).has("manifest.policy"));
});

test("deferred-render geometry policy must remain bound to the visual receipt", (t) => {
  const fixture = createFixture(t);
  rebindVisual(fixture, (visual) => {
    visual.policies.deferredRenderGeometry = {
      ...visual.policies.deferredRenderGeometry,
      epsilonPx: 24,
    };
  });
  const receipt = evaluateCompositeGate({
    repoRoot: fixture.repoRoot,
    manifestPath: fixture.manifestPath,
    now: NOW,
  });
  assert.equal(receipt.state, "blocked");
  assert(findingCodes(receipt).has("visual.deferred_render_geometry_policy"));
});

test("each rendering-geometry result must use the canonical method and policy", (t) => {
  const fixture = createFixture(t);
  rebindVisual(fixture, (visual) => {
    const performance = visual.engines[0].performance.find(
      (item) => item.routeName === "research",
    );
    performance.renderingGeometry.method = "unbound geometry probe";
  });
  const receipt = evaluateCompositeGate({
    repoRoot: fixture.repoRoot,
    manifestPath: fixture.manifestPath,
    now: NOW,
  });
  assert.equal(receipt.state, "blocked");
  assert(findingCodes(receipt).has("visual.non_axe_failures"));
});

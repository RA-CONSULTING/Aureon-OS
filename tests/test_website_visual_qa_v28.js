"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const test = require("node:test");

const {
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
  parseCli,
  safeDiagnosticText,
  safeDiagnosticUrl,
  sha256File,
  snapshotWebsiteTree,
} = require("../tools/aureon_website_visual_qa_v28.js");

function expectedEditorialSurface(overrides = {}) {
  return {
    asset_id: "substack-ai-evidence",
    route_scope: "/",
    destination_path: "website/index.html",
    surface_id: "home-ai-evidence-question",
    public_post_url:
      "https://garyleckey.substack.com/p/when-does-an-ai-look-aliveand-what",
    variants: [
      {
        role: "large",
        path: "website/assets/images/research/substack/ai-evidence-1200.webp",
        sha256: "A".repeat(64),
        media_type: "image/webp",
        width: 1200,
        height: 675,
      },
      {
        role: "small",
        path: "website/assets/images/research/substack/ai-evidence-720.webp",
        sha256: "B".repeat(64),
        media_type: "image/webp",
        width: 720,
        height: 405,
      },
    ],
    alt: "Concept-system editorial illustration; not measured data.",
    caption: "Concept illustration; not measured data.",
    credit: "Provider-delivered editorial asset.",
    route_asset_capsule_sha256: "C".repeat(64),
    expected_binding_sha256: "D".repeat(64),
    observation_sha256: "E".repeat(64),
    surface_binding_sha256: "F".repeat(64),
    ...overrides,
  };
}

function observedEditorialSurface(overrides = {}) {
  const base = {
    surfaceId: "home-ai-evidence-question",
    visible: true,
    pictureCount: 1,
    imageCount: 1,
    anchorCount: 1,
    anchorUrls: [
      "https://garyleckey.substack.com/p/when-does-an-ai-look-aliveand-what",
    ],
    figcaptionCount: 1,
    nestedSurfaceCount: 0,
    hasSurfaceAncestor: false,
    caption: "Concept illustration; not measured data.",
    captionVisible: true,
    creditMatchCount: 1,
    creditVisible: true,
    image: {
      src: "http://127.0.0.1:4173/assets/images/research/substack/ai-evidence-1200.webp",
      currentSrc:
        "http://127.0.0.1:4173/assets/images/research/substack/ai-evidence-1200.webp",
      alt: "Concept-system editorial illustration; not measured data.",
      declaredWidth: 1200,
      declaredHeight: 675,
      complete: true,
      naturalWidth: 1200,
      naturalHeight: 675,
      renderedWidth: 640,
      renderedHeight: 360,
      visible: true,
    },
    sources: [
      {
        media: "(max-width: 720px)",
        srcset:
          "http://127.0.0.1:4173/assets/images/research/substack/ai-evidence-720.webp",
      },
    ],
  };
  return {
    ...base,
    ...overrides,
    image: { ...base.image, ...(overrides.image || {}) },
    sources: overrides.sources || base.sources,
  };
}

test("editorial surface observations require the exact provenance-bound surface", () => {
  const expected = expectedEditorialSurface();
  const result = assessEditorialSurfaceObservations(
    [observedEditorialSurface()],
    "http://127.0.0.1:4173/",
    [expected],
  );

  assert.equal(result.pass, true);
  assert.equal(result.surfaceCount, 1);
  assert.deepEqual(result.failures, []);
  assert.deepEqual(result.expectedSurfaces, [expected]);
  assert.equal(result.expectedSurfacesSha256, canonicalJsonSha256([expected]));
  assert.equal(
    result.observedSurfaces[0].image.srcPath,
    "/assets/images/research/substack/ai-evidence-1200.webp",
  );
  assert(!JSON.stringify(result).includes('"currentSrc":'));
  assert(!JSON.stringify(result).includes('"srcset":'));
});

test("editorial surface observations reject hidden, duplicated, remote, or mislinked media", () => {
  const expected = expectedEditorialSurface({ surface_id: "duplicate-surface" });
  const unsafe = observedEditorialSurface({
    surfaceId: "duplicate-surface",
    visible: false,
    anchorUrls: ["https://example.test/not-the-bound-post"],
    caption: "",
    captionVisible: false,
    creditMatchCount: 0,
    creditVisible: false,
    image: {
      src: "https://cdn.example.test/unbound.webp",
      currentSrc: "data:image/webp;base64,AAAA",
      alt: "",
      complete: false,
      naturalWidth: 0,
      naturalHeight: 0,
      renderedWidth: 0,
      renderedHeight: 0,
      visible: false,
    },
    sources: [{ media: "", srcset: "blob:https://example.test/unbound" }],
  });
  const result = assessEditorialSurfaceObservations(
    [unsafe, unsafe],
    "http://127.0.0.1:4173/",
    [expected],
  );

  assert.equal(result.pass, false);
  assert.deepEqual(result.duplicateSurfaceIds, ["duplicate-surface"]);
  assert(result.failures.some((item) => item.endsWith(":surface-id-unique")));
  assert(result.failures.some((item) => item.endsWith(":image-current-src-path")));
  assert(result.failures.some((item) => item.endsWith(":public-post-url")));
  assert(!JSON.stringify(result).includes("cdn.example.test"));
  assert(!JSON.stringify(result).includes("base64"));
});

test("editorial surface observations require exact empty and non-empty sets", () => {
  const expected = expectedEditorialSurface();
  const empty = assessEditorialSurfaceObservations(
    [],
    "http://127.0.0.1:4173/",
    [],
  );
  assert.equal(empty.pass, true);

  const missing = assessEditorialSurfaceObservations(
    [],
    "http://127.0.0.1:4173/",
    [expected],
  );
  assert.equal(missing.pass, false);
  assert(missing.failures.includes("home-ai-evidence-question:surface-missing"));

  const unexpected = assessEditorialSurfaceObservations(
    [observedEditorialSurface()],
    "http://127.0.0.1:4173/",
    [],
  );
  assert.equal(unexpected.pass, false);
  assert(unexpected.failures.includes("home-ai-evidence-question:surface-unexpected"));
});

test("editorial surface audit rejects URL tokens and never persists raw URL material", () => {
  const result = assessEditorialSurfaceObservations(
    [
      observedEditorialSurface({
        image: {
          src: "http://127.0.0.1:4173/assets/images/research/substack/ai-evidence-1200.webp?token=private",
          currentSrc:
            "http://operator:secret@127.0.0.1:4173/assets/images/research/substack/ai-evidence-1200.webp#private",
        },
        sources: [
          {
            srcset:
              "http://127.0.0.1:4173/assets/images/research/substack/ai-evidence-720.webp?signature=private",
          },
        ],
      }),
    ],
    "http://127.0.0.1:4173/",
    [expectedEditorialSurface()],
  );
  const persisted = JSON.stringify(result);
  assert.equal(result.pass, false);
  assert(!persisted.includes("token"));
  assert(!persisted.includes("signature"));
  assert(!persisted.includes("operator"));
  assert(!persisted.includes("secret"));
  assert(!persisted.includes("#private"));
});

test("diagnostic URLs retain routing evidence without credentials or URL secrets", () => {
  assert.equal(
    safeDiagnosticUrl(
      "https://operator:secret@example.test/assets/image.webp?token=private#fragment",
    ),
    "https://example.test/assets/image.webp",
  );
  assert.equal(
    safeDiagnosticUrl("data:image/webp;base64,PRIVATE"),
    "data://redacted",
  );
  assert.equal(safeDiagnosticUrl("not a url"), "invalid-url");
  assert.equal(
    safeDiagnosticText(
      "failed https://operator:secret@example.test/a.webp?token=private#fragment",
    ),
    "failed https://example.test/a.webp",
  );
});

test("CLI defaults to a fail-closed three-engine request", () => {
  const options = parseCli([], {});
  assert.deepEqual(options.engines, DEFAULT_ENGINES);
  assert.equal(options.engineSelectionExplicit, false);
});

test("CLI records a deliberate single-engine selection", () => {
  const options = parseCli(
    ["--engines=chromium", "--routes=home,research", "--viewports=reflow,desktop"],
    {},
  );
  assert.deepEqual(options.engines, ["chromium"]);
  assert.equal(options.engineSelectionExplicit, true);
  assert.deepEqual(options.routeNames, ["home", "research"]);
  assert.deepEqual(options.viewportNames, ["reflow", "desktop"]);
});

test("CLI rejects external audit targets containing URL secrets or path substitution", () => {
  assert.throws(
    () => parseCli(["--base-url=https://operator:secret@example.test"], {}),
    /credential-free/,
  );
  assert.throws(
    () => parseCli(["--base-url=https://example.test/root?token=private"], {}),
    /credential-free/,
  );
  assert.equal(
    parseCli(["--base-url=https://example.test"], {}).baseUrl,
    "https://example.test",
  );
});

test("mandatory screenshot scope captures the desktop investor brief", () => {
  const desktop = SCREENSHOT_CAPTURE_SCOPE.find((item) => item.viewportName === "desktop");
  assert.deepEqual(desktop.routeNames, ["home", "funding", "investor", "publications", "research"]);
});

test("deferred-render geometry is pass-through only when the optimisation is absent", () => {
  const notApplicable = evaluateDeferredRenderGeometry({
    status: "NOT_APPLICABLE",
    support: { contentVisibility: true, containIntrinsicSize: true },
    candidateCount: 0,
    excluded: { displayNone: 0, outOfFlow: 0, nested: 0 },
    document: { scrollHeight: 1200, scrollWidth: 1440, clientWidth: 1440 },
    candidates: [],
  });
  assert.equal(notApplicable.pass, true);
  assert.equal(notApplicable.status, "NOT_APPLICABLE");

  const unsupported = evaluateDeferredRenderGeometry({
    status: "NOT_SUPPORTED",
    support: { contentVisibility: false, containIntrinsicSize: false },
    candidateCount: 0,
    excluded: { displayNone: 0, outOfFlow: 0, nested: 0 },
    document: { scrollHeight: 1200, scrollWidth: 1440, clientWidth: 1440 },
    candidates: [],
  });
  assert.equal(unsupported.pass, true);
  assert.equal(unsupported.status, "NOT_SUPPORTED");
});

test("deferred-render geometry fails closed for a changed reserved layout", () => {
  const before = {
    status: "RAN",
    support: { contentVisibility: true, containIntrinsicSize: true },
    candidateCount: 1,
    excluded: { displayNone: 0, outOfFlow: 0, nested: 0 },
    document: { scrollHeight: 3000, scrollWidth: 1440, clientWidth: 1440 },
    candidates: [
      {
        key: "id:portfolio-economics",
        tag: "section",
        id: "portfolio-economics",
        computedContainIntrinsicSize: "auto 900px",
        beforeOrAfterDocumentTop: 900,
        height: 900,
      },
    ],
  };
  const stable = evaluateDeferredRenderGeometry(
    before,
    {
      ...before,
      document: { scrollHeight: 3002, scrollWidth: 1440, clientWidth: 1440 },
      candidates: [{ ...before.candidates[0], beforeOrAfterDocumentTop: 902, height: 898 }],
    },
  );
  assert.equal(stable.pass, true);
  assert.equal(stable.deltas.scrollHeightPx, DEFERRED_RENDER_GEOMETRY_POLICY.epsilonPx);

  const shifted = evaluateDeferredRenderGeometry(
    before,
    {
      ...before,
      document: { scrollHeight: 3003, scrollWidth: 1443, clientWidth: 1440 },
      candidates: [{ ...before.candidates[0], beforeOrAfterDocumentTop: 904, height: 896 }],
    },
  );
  assert.equal(shifted.pass, false);
  assert(shifted.failureReasons.some((reason) => reason.startsWith("scroll-height:")));
  assert(shifted.failureReasons.includes("horizontal-overflow:after"));
  assert(shifted.failureReasons.includes("candidate-geometry:id:portfolio-economics"));
});

test("deferred-render geometry fails closed for changed candidate identity or excess scope", () => {
  const policy = { ...DEFERRED_RENDER_GEOMETRY_POLICY, candidateLimit: 1 };
  const before = {
    status: "RAN",
    support: { contentVisibility: true, containIntrinsicSize: true },
    candidateCount: 2,
    excluded: { displayNone: 0, outOfFlow: 0, nested: 0 },
    document: { scrollHeight: 3000, scrollWidth: 1440, clientWidth: 1440 },
    candidates: [
      {
        key: "id:first",
        tag: "section",
        id: "first",
        computedContainIntrinsicSize: "auto 300px",
        beforeOrAfterDocumentTop: 900,
        height: 300,
      },
      {
        key: "id:second",
        tag: "section",
        id: "second",
        computedContainIntrinsicSize: "auto 300px",
        beforeOrAfterDocumentTop: 1200,
        height: 300,
      },
    ],
  };
  const result = evaluateDeferredRenderGeometry(
    before,
    {
      ...before,
      candidateCount: 1,
      candidates: [before.candidates[0]],
    },
    policy,
  );
  assert.equal(result.pass, false);
  assert(result.failureReasons.includes("candidate-limit:2>1"));
  assert(result.failureReasons.includes("candidate-count:2->1"));
  assert(result.failureReasons.includes("candidate-missing:id:second"));
});

test("deferred-render geometry fails closed when a bounded reveal cannot settle", () => {
  const snapshot = {
    status: "RAN",
    support: { contentVisibility: true, containIntrinsicSize: true },
    candidateCount: 1,
    excluded: { displayNone: 0, outOfFlow: 0, nested: 0 },
    document: { scrollHeight: 3000, scrollWidth: 1440, clientWidth: 1440 },
    candidates: [
      {
        key: "id:research-register",
        tag: "section",
        id: "research-register",
        computedContainIntrinsicSize: "auto 900px",
        beforeOrAfterDocumentTop: 900,
        height: 900,
      },
    ],
  };
  const result = evaluateDeferredRenderGeometry(
    snapshot,
    snapshot,
    DEFERRED_RENDER_GEOMETRY_POLICY,
    { completed: false, sweeps: 8, maxSweeps: 8, finalScrollHeight: 5000 },
  );
  assert.equal(result.pass, false);
  assert(result.failureReasons.includes("reveal-incomplete:8/8"));
});

test("website tree hash is deterministic and changes with source bytes", () => {
  const temporary = fs.mkdtempSync(path.join(os.tmpdir(), "aureon-visual-qa-"));
  try {
    fs.mkdirSync(path.join(temporary, "nested"));
    fs.writeFileSync(path.join(temporary, "index.html"), "alpha\n", "utf8");
    fs.writeFileSync(path.join(temporary, "nested", "style.css"), "beta\n", "utf8");
    const first = snapshotWebsiteTree(temporary);
    const second = snapshotWebsiteTree(temporary);
    assert.equal(first.sha256, second.sha256);
    assert.equal(first.fileCount, 2);
    assert.equal(first.files.length, 2);
    fs.writeFileSync(path.join(temporary, "index.html"), "changed\n", "utf8");
    const changed = snapshotWebsiteTree(temporary);
    assert.notEqual(first.sha256, changed.sha256);
  } finally {
    fs.rmSync(temporary, { recursive: true, force: true });
  }
});

test("website tree inventory uses locale-independent lexical path ordering", () => {
  const temporary = fs.mkdtempSync(path.join(os.tmpdir(), "aureon-visual-qa-sort-"));
  try {
    fs.mkdirSync(path.join(temporary, "fonts"));
    fs.writeFileSync(path.join(temporary, "fonts", "ibm-plex-600.woff2"), "font", "utf8");
    fs.writeFileSync(path.join(temporary, "fonts", "LICENSES"), "licence", "utf8");
    fs.writeFileSync(path.join(temporary, "index.html"), "home", "utf8");
    const snapshot = snapshotWebsiteTree(temporary);
    assert.deepEqual(snapshot.files.map((file) => file.path), [
      "fonts/LICENSES",
      "fonts/ibm-plex-600.woff2",
      "index.html",
    ]);
  } finally {
    fs.rmSync(temporary, { recursive: true, force: true });
  }
});

test("website tree snapshot rejects hardlinked public files", () => {
  const temporary = fs.mkdtempSync(path.join(os.tmpdir(), "aureon-visual-qa-link-"));
  try {
    const first = path.join(temporary, "index.html");
    fs.writeFileSync(first, "home", "utf8");
    fs.linkSync(first, path.join(temporary, "alias.html"));
    assert.throws(() => snapshotWebsiteTree(temporary), /hardlinked file/);
  } finally {
    fs.rmSync(temporary, { recursive: true, force: true });
  }
});

test("file hashing records exact screenshot bytes", () => {
  const temporary = fs.mkdtempSync(path.join(os.tmpdir(), "aureon-shot-hash-"));
  try {
    const target = path.join(temporary, "shot.png");
    fs.writeFileSync(target, Buffer.from([0x89, 0x50, 0x4e, 0x47]));
    assert.equal(
      sha256File(target),
      "0f4636c78f65d3639ece5a064b5ae753e3408614a14fb18ab4d7540d2c248543",
    );
  } finally {
    fs.rmSync(temporary, { recursive: true, force: true });
  }
});

test("performance budgets fail closed at and beyond static thresholds", () => {
  const passing = evaluatePerformance({
    ttfbMs: PERFORMANCE_BUDGETS.ttfbMs,
    domContentLoadedMs: PERFORMANCE_BUDGETS.domContentLoadedMs,
    loadEventMs: PERFORMANCE_BUDGETS.loadEventMs,
    lcpMs: null,
    cls: PERFORMANCE_BUDGETS.cls,
    requestCount: PERFORMANCE_BUDGETS.requestCount,
    transferProxyBytes: PERFORMANCE_BUDGETS.transferProxyBytes,
    longTaskTotalMs: PERFORMANCE_BUDGETS.longTaskTotalMs,
  });
  assert.equal(passing.pass, true);

  const failing = evaluatePerformance({
    ttfbMs: PERFORMANCE_BUDGETS.ttfbMs + 0.1,
    domContentLoadedMs: 1,
    loadEventMs: 1,
    lcpMs: 1,
    cls: 0,
    requestCount: 1,
    transferProxyBytes: 1,
    longTaskTotalMs: 0,
  });
  assert.equal(failing.pass, false);
  assert.equal(failing.checks.ttfb.pass, false);
});

test("expected browser navigation cancellations are not resource failures", () => {
  const request = (errorText, resourceType = "image") => ({
    failure: () => ({ errorText }),
    resourceType: () => resourceType,
  });
  assert.equal(isExpectedClientCancellation(request("Load request cancelled")), true);
  assert.equal(isExpectedClientCancellation(request("net::ERR_ABORTED", "script")), true);
  assert.equal(isExpectedClientCancellation(request("NS_BINDING_ABORTED", "stylesheet")), true);
  assert.equal(isExpectedClientCancellation(request("Load request cancelled", "document")), false);
  assert.equal(isExpectedClientCancellation(request("net::ERR_CONNECTION_RESET")), false);
});

test("axe evidence requires every reported node and no unresolved rules", () => {
  const complete = assessAxeEvidence({
    violations: [],
    incomplete: [],
  });
  assert.equal(complete.completeNodeEvidence, true);
  assert.equal(complete.pass, true);

  const unresolved = assessAxeEvidence({
    violations: [],
    incomplete: [
      {
        id: "color-contrast",
        nodeCount: 2,
        nodes: [{ target: [".one"] }, { target: [".two"] }],
      },
    ],
  });
  assert.equal(unresolved.completeNodeEvidence, true);
  assert.equal(unresolved.incompleteNodeCount, 2);
  assert.equal(unresolved.pass, false);
});

test("axe evidence fails closed when a node list is capped", () => {
  const capped = assessAxeEvidence({
    violations: [],
    incomplete: [
      {
        id: "color-contrast",
        nodeCount: 25,
        nodes: Array.from({ length: 20 }, (_, index) => ({
          target: [`.node-${index}`],
        })),
      },
    ],
  });
  assert.equal(capped.completeNodeEvidence, false);
  assert.equal(capped.pass, false);
});

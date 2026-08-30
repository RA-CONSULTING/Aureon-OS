#!/usr/bin/env node
"use strict";

/*
 * A non-gating diagnostic for a staged or canonical public-site tree.
 *
 * It runs a self-hosted Chromium observation of /research/ while injecting
 * timing markers at runtime only. It never modifies the source tree, does not
 * create a candidate, and writes append-only evidence only below
 * artifacts/website-operator/research-hydration-attribution/.
 */

const crypto = require("node:crypto");
const fs = require("node:fs");
const path = require("node:path");

const {
  loadPlaywright,
  snapshotWebsiteTree,
  startStaticServer,
} = require("./aureon_website_visual_qa_v28.js");

const REPO_ROOT = path.resolve(__dirname, "..");
const DEFAULT_SOURCE_ROOT = path.join(REPO_ROOT, "website");
const DEFAULT_OUTPUT_ROOT = path.join(
  REPO_ROOT,
  "artifacts",
  "website-operator",
  "research-hydration-attribution",
);
const TRACE_MARKER_PREFIX = "aureon-attribution:";
const RECEIPT_SCHEMA = "aureon.research-hydration-attribution.v1";
const MINIMIZED_TRACE_SCHEMA = "aureon.research-hydration-minimized-trace.v1";
const PROTOCOL_VERSION = "aureon.research-hydration-attribution.protocol.v2";
const ROUTE = "/research/";
const VIEWPORT = Object.freeze({ width: 1440, height: 1000 });
const MARKER_WINDOW_US = 50_000;
const MAX_RUNTIME_EVENTS = 512;
const MAX_MINIMIZED_TRACE_EVENTS = 1_200;
const MAX_RAW_TRACE_BYTES = 24 * 1024 * 1024;
const REQUIRED_SOURCE_FILES = Object.freeze([
  "research/index.html",
  "script.js",
  "data/research.json",
  "data/research-catalogue.json",
]);
const HYDRATION_TARGETS = Object.freeze([
  Object.freeze({ selector: "[data-research]", id: "research-register-hydration" }),
  Object.freeze({ selector: "[data-research-profiles]", id: "research-profiles-hydration" }),
  Object.freeze({ selector: "[data-research-notes]", id: "research-notes-hydration" }),
  Object.freeze({
    selector: [
      "[data-research-catalogue-recent]",
      "[data-research-catalogue-orcid-role]",
      "[data-research-catalogue-zenodo-role]",
      "[data-research-catalogue-review-posture]",
      "[data-research-catalogue-translation-gate]",
      "[data-research-catalogue-boundary]",
    ].join(", "),
    id: "research-catalogue-hydration",
  }),
]);

function usage() {
  return `Usage:
  node tools/aureon_research_hydration_attribution.js [options]

Options:
  --source-root PATH  Read-only website tree to observe. Defaults to website/.
  --output-root PATH  New artifact directory below
                        artifacts/website-operator/research-hydration-attribution/.
  --wait-ms NUMBER    Post-load observation period (0-10000; default 800).
  --help              Show this help.

This is an analysis-only, single Chromium capture. It is not a performance
gate and cannot promote, package, or deploy a site candidate.
`;
}

function takeValue(argv, index, argument) {
  const equals = argument.indexOf("=");
  if (equals >= 0) return [argument.slice(equals + 1), index];
  if (index + 1 >= argv.length) throw new Error(`${argument} requires a value`);
  return [argv[index + 1], index + 1];
}

function parseCli(argv = []) {
  const options = {
    sourceRoot: DEFAULT_SOURCE_ROOT,
    outputRoot: "",
    waitMs: 800,
    help: false,
  };
  for (let index = 0; index < argv.length; index += 1) {
    const argument = argv[index];
    if (argument === "--help" || argument === "-h") {
      options.help = true;
      continue;
    }
    if (argument === "--source-root" || argument.startsWith("--source-root=")) {
      const [value, nextIndex] = takeValue(argv, index, argument);
      options.sourceRoot = value;
      index = nextIndex;
      continue;
    }
    if (argument === "--output-root" || argument.startsWith("--output-root=")) {
      const [value, nextIndex] = takeValue(argv, index, argument);
      options.outputRoot = value;
      index = nextIndex;
      continue;
    }
    if (argument === "--wait-ms" || argument.startsWith("--wait-ms=")) {
      const [value, nextIndex] = takeValue(argv, index, argument);
      options.waitMs = Number(value);
      index = nextIndex;
      continue;
    }
    throw new Error(`Unknown option: ${argument}`);
  }
  if (!Number.isInteger(options.waitMs) || options.waitMs < 0 || options.waitMs > 10_000) {
    throw new Error("--wait-ms must be an integer from 0 to 10000");
  }
  return options;
}

function utcStamp(date = new Date()) {
  return date.toISOString().replace(/[-:.]/g, "").replace("Z", "Z");
}

function isWithin(child, parent) {
  const relative = path.relative(parent, child);
  return relative === "" || (!relative.startsWith("..") && !path.isAbsolute(relative));
}

function existingRealPath(value, label) {
  try {
    return fs.realpathSync.native(value);
  } catch (error) {
    throw new Error(`${label} must exist and resolve without a link escape: ${value}`);
  }
}

function assertNoExistingSymlinkComponents(root, target, label) {
  const resolvedRoot = path.resolve(root);
  const resolvedTarget = path.resolve(target);
  if (!isWithin(resolvedTarget, resolvedRoot)) {
    throw new Error(`${label} escapes its allowed root.`);
  }
  const relative = path.relative(resolvedRoot, resolvedTarget);
  let current = resolvedRoot;
  for (const part of relative.split(path.sep).filter(Boolean)) {
    current = path.join(current, part);
    if (!fs.existsSync(current)) break;
    if (fs.lstatSync(current).isSymbolicLink()) {
      throw new Error(`${label} may not traverse a symbolic link: ${current}`);
    }
  }
}

function controlledOutputRoot(repoRoot) {
  const resolvedRepo = existingRealPath(path.resolve(repoRoot), "Repository root");
  const requestedRoot = path.join(
    path.resolve(repoRoot),
    "artifacts",
    "website-operator",
    "research-hydration-attribution",
  );
  assertNoExistingSymlinkComponents(path.resolve(repoRoot), requestedRoot, "Output root");
  fs.mkdirSync(requestedRoot, { recursive: true });
  assertNoExistingSymlinkComponents(path.resolve(repoRoot), requestedRoot, "Output root");
  const resolvedOutput = existingRealPath(requestedRoot, "Output root");
  if (!isWithin(resolvedOutput, resolvedRepo)) {
    throw new Error("Research attribution output root escaped the resolved repository.");
  }
  return resolvedOutput;
}

function resolveRunDirectory(value, {
  repoRoot = REPO_ROOT,
  stamp = utcStamp(),
} = {}) {
  const allowedRoot = controlledOutputRoot(repoRoot);
  const candidate = value
    ? path.resolve(repoRoot, value)
    : path.join(allowedRoot, `${stamp}-research-hydration-attribution`);
  if (!isWithin(candidate, allowedRoot) || candidate === allowedRoot || path.dirname(candidate) !== allowedRoot) {
    throw new Error(`Output directory must be a new child of ${allowedRoot}`);
  }
  assertNoExistingSymlinkComponents(allowedRoot, candidate, "Output directory");
  if (fs.existsSync(candidate)) {
    throw new Error(`Output directory already exists: ${candidate}`);
  }
  return candidate;
}

function materializeRunDirectory(candidate, { repoRoot = REPO_ROOT } = {}) {
  const allowedRoot = controlledOutputRoot(repoRoot);
  if (
    !isWithin(candidate, allowedRoot)
    || candidate === allowedRoot
    || path.dirname(candidate) !== allowedRoot
  ) {
    throw new Error(`Output directory must be a new child of ${allowedRoot}`);
  }
  fs.mkdirSync(candidate);
  assertNoExistingSymlinkComponents(allowedRoot, candidate, "Output directory");
  const resolved = existingRealPath(candidate, "Output directory");
  if (path.dirname(resolved) !== allowedRoot) {
    throw new Error("Output directory escaped the controlled artifact root.");
  }
  return resolved;
}

function ensureSourceRoot(sourceRoot, { repoRoot = REPO_ROOT } = {}) {
  const logicalRepo = path.resolve(repoRoot);
  const resolvedRepo = existingRealPath(logicalRepo, "Repository root");
  const requested = path.resolve(logicalRepo, sourceRoot);
  if (!isWithin(requested, logicalRepo)) {
    throw new Error("Research attribution source must remain inside this repository.");
  }
  assertNoExistingSymlinkComponents(logicalRepo, requested, "Research attribution source");
  const resolved = existingRealPath(requested, "Research attribution source");
  if (!isWithin(resolved, resolvedRepo)) {
    throw new Error("Research attribution source escaped the resolved repository.");
  }
  const canonical = existingRealPath(path.join(logicalRepo, "website"), "Canonical website source");
  const candidatesLogical = path.join(logicalRepo, "artifacts", "website-candidates");
  const candidates = fs.existsSync(candidatesLogical)
    ? existingRealPath(candidatesLogical, "Candidate artifact root")
    : "";
  const isCanonical = resolved === canonical;
  const isStagedCandidate = Boolean(
    candidates
      && isWithin(resolved, candidates)
      && resolved !== candidates
      && path.basename(resolved) === "website"
      && path.relative(candidates, resolved).split(path.sep).filter(Boolean).length === 2,
  );
  if (!isCanonical && !isStagedCandidate) {
    throw new Error(
      "Research attribution may observe only canonical website/ or a staged artifacts/website-candidates/*/website tree.",
    );
  }
  for (const relative of REQUIRED_SOURCE_FILES) {
    const file = path.join(resolved, relative);
    if (!fs.existsSync(file) || fs.lstatSync(file).isSymbolicLink() || !fs.statSync(file).isFile()) {
      throw new Error(`Expected website source file is missing: ${file}`);
    }
  }
  return resolved;
}

function selectedSourceBinding(sourceRoot, snapshot) {
  const selected = REQUIRED_SOURCE_FILES.map((relative) => {
    const file = snapshot.files.find((entry) => entry.path === relative);
    if (!file) throw new Error(`Snapshot does not contain required source file: ${relative}`);
    return { path: relative, sha256: file.sha256, bytes: file.bytes };
  });
  return {
    root: sourceRoot,
    tree_sha256: snapshot.sha256,
    file_count: snapshot.fileCount,
    total_bytes: snapshot.totalBytes,
    selected_files: selected,
  };
}

function classifyHydrationTarget(matches) {
  for (const target of HYDRATION_TARGETS) {
    if (matches(target.selector)) return target.id;
  }
  return "";
}

/*
 * This function is serialised into the browser with Playwright's
 * context.addInitScript. It must remain self-contained: it is runtime-only
 * instrumentation and never becomes part of a served website file.
 */
function attributionInitScript(config = {}) {
  const markerPrefix = typeof config.markerPrefix === "string" ? config.markerPrefix : "aureon-attribution:invalid:";
  const maxRuntimeEvents = Number.isInteger(config.maxRuntimeEvents)
    ? config.maxRuntimeEvents
    : 512;
  const targets = [
    { selector: "[data-research]", id: "research-register-hydration" },
    { selector: "[data-research-profiles]", id: "research-profiles-hydration" },
    { selector: "[data-research-notes]", id: "research-notes-hydration" },
    {
      selector: [
        "[data-research-catalogue-recent]",
        "[data-research-catalogue-orcid-role]",
        "[data-research-catalogue-zenodo-role]",
        "[data-research-catalogue-review-posture]",
        "[data-research-catalogue-translation-gate]",
        "[data-research-catalogue-boundary]",
      ].join(", "),
      id: "research-catalogue-hydration",
    },
  ];
  let recordedEventCount = 0;
  const record = (name) => {
    if (recordedEventCount >= maxRuntimeEvents) {
      return;
    }
    recordedEventCount += 1;
    const fullName = `${markerPrefix}${name}`;
    try {
      performance.mark(fullName);
    } catch {
      // Missing User Timing leaves no trace marker and therefore fails coverage.
    }
  };
  const classify = (element) => {
    if (!element || element.nodeType !== Node.ELEMENT_NODE || typeof element.matches !== "function") return "";
    for (const target of targets) {
      if (element.matches(target.selector)) return target.id;
    }
    return "";
  };
  const resourceKey = (raw) => {
    if (!raw) return "";
    let parsed;
    try {
      parsed = new URL(raw, location.href);
    } catch {
      return "";
    }
    if (parsed.origin !== location.origin) return "";
    const pathname = parsed.pathname;
    if (pathname.endsWith("/data/research.json")) return "research-json";
    if (pathname.endsWith("/data/research-catalogue.json")) return "research-catalogue-json";
    return "";
  };
  const describeTarget = (node) => {
    if (!node) return "";
    const element = node.nodeType === Node.ELEMENT_NODE ? node : node.parentElement;
    if (!element) return "";
    const direct = classify(element);
    if (direct) return direct;
    return typeof element.closest === "function" ? classify(element.closest("[data-research], [data-research-profiles], [data-research-notes], [data-research-catalogue-recent], [data-research-catalogue-orcid-role], [data-research-catalogue-zenodo-role], [data-research-catalogue-review-posture], [data-research-catalogue-translation-gate], [data-research-catalogue-boundary]")) : "";
  };

  record("document-start");
  if (typeof PerformanceObserver === "function") {
    try {
      new PerformanceObserver((entries) => {
        for (const entry of entries.getEntries()) {
          const key = resourceKey(entry.name);
          if (!key) continue;
          record(`resource:${key}:complete`);
        }
      }).observe({ type: "resource", buffered: true });
    } catch {
      record("resource-observer-unavailable");
    }
  }
  const mutationObserver = new MutationObserver((records) => {
    // Parser construction happens while readyState is loading. It is not a
    // client render and is deliberately excluded, while the observer itself
    // begins early enough to observe a deferred-script render before DCL.
    if (document.readyState === "loading") return;
    const grouped = new Map();
    for (const item of records) {
      const id = describeTarget(item.target);
      if (!id) continue;
      const current = grouped.get(id) || { mutation_count: 0, added_nodes: 0, removed_nodes: 0 };
      current.mutation_count += 1;
      current.added_nodes += item.addedNodes?.length || 0;
      current.removed_nodes += item.removedNodes?.length || 0;
      grouped.set(id, current);
    }
    for (const id of grouped.keys()) {
      // MutationObserver reports delivery after a mutation batch, not the
      // exact DOM-write timestamp. Preserve that distinction in the marker.
      record(`${id}:mutation-observer-delivery`);
      requestAnimationFrame(() => {
        record(`${id}:raf-1`);
        requestAnimationFrame(() => record(`${id}:raf-2`));
      });
    }
  });
  mutationObserver.observe(document, { childList: true, subtree: true, characterData: true });
  record("mutation-observer-active");
  const installResizeObserver = () => {
    if (typeof ResizeObserver !== "function") return;
    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const label = entry.target.id ? `id:${entry.target.id}` : "unnamed-research-section";
        record(`section-resize:${label}`);
      }
    });
    document.querySelectorAll("main section[id], main section[class*='research']").forEach((section) => observer.observe(section));
  };
  document.addEventListener("readystatechange", () => {
    if (document.readyState !== "loading") record("dynamic-observation-ready");
  });
  document.addEventListener("DOMContentLoaded", () => record("dom-content-loaded"), { once: true });
  document.addEventListener("DOMContentLoaded", installResizeObserver, { once: true });
  globalThis.addEventListener("load", () => record("window-load"), { once: true });
  // The recorder remains private to this init-script closure. The driver reads
  // only nonce-scoped User Timing marks at capture time; ordinary site code
  // cannot call the recorder or forge its event metadata directly.
}

function traceMarkerEvents(traceEvents, markerPrefix = TRACE_MARKER_PREFIX) {
  return traceEvents
    .filter((event) => typeof event.name === "string" && event.name.startsWith(markerPrefix))
    .map((event) => ({
      name: event.name,
      timestamp_us: Number(event.ts),
      phase: event.ph || "",
      pid: event.pid,
      tid: event.tid,
    }))
    .filter((event) => Number.isFinite(event.timestamp_us))
    .sort((left, right) => left.timestamp_us - right.timestamp_us);
}

function documentLayoutEvents(traceEvents) {
  return traceEvents
    .filter((event) => event.name === "Layout" && event.ph === "X" && Number(event.dur) > 0)
    .map((event) => {
      const beginData = event.args?.beginData || {};
      const start = Number(event.ts);
      const duration = Number(event.dur);
      const dirty = Number(beginData.dirtyObjects);
      const total = Number(beginData.totalObjects);
      const layoutRoots = Array.isArray(event.args?.endData?.layoutRoots)
        ? event.args.endData.layoutRoots
        : [];
      return {
        start_us: start,
        end_us: start + duration,
        duration_ms: Number((duration / 1000).toFixed(3)),
        dirty_objects: Number.isFinite(dirty) ? dirty : null,
        total_objects: Number.isFinite(total) ? total : null,
        full_document: Boolean(
          Number.isFinite(dirty) && Number.isFinite(total) && total > 0 && dirty === total,
        ),
        document_root: layoutRoots.some((root) => root && root.nodeName === "#document"),
        partial_layout: beginData.partialLayout === true,
        pid: event.pid,
        tid: event.tid,
      };
    })
    .sort((left, right) => right.duration_ms - left.duration_ms);
}

function markerRelation(marker, layout, windowUs = MARKER_WINDOW_US) {
  if (marker.timestamp_us >= layout.start_us && marker.timestamp_us <= layout.end_us) return "within-layout";
  if (marker.timestamp_us < layout.start_us && layout.start_us - marker.timestamp_us <= windowUs) {
    return "precedes-within-window";
  }
  return "outside-window";
}

function correlateHydration(
  traceEvents,
  { markerPrefix = TRACE_MARKER_PREFIX, windowUs = MARKER_WINDOW_US } = {},
) {
  const markers = traceMarkerEvents(traceEvents, markerPrefix);
  const layouts = documentLayoutEvents(traceEvents);
  const documentRootLayouts = layouts.filter((layout) => layout.document_root);
  const fullLayouts = documentRootLayouts.filter((layout) => layout.full_document);
  const hydrationMarkers = markers.filter((marker) => HYDRATION_TARGETS.some((target) => marker.name.startsWith(`${markerPrefix}${target.id}:`)));
  const chronologicalLayouts = [...documentRootLayouts].sort((left, right) => left.start_us - right.start_us);
  const initialLayout = chronologicalLayouts[0] || null;
  const firstHydrationMarker = hydrationMarkers[0] || null;
  let initialLayoutFinding = {
    state: "inconclusive",
    limitation: "Trace association is temporal and does not identify a source function or prove causation.",
  };
  if (initialLayout && firstHydrationMarker) {
    initialLayoutFinding = {
      state: initialLayout.end_us <= firstHydrationMarker.timestamp_us
        ? "initial-document-layout-precedes-observed-hydration"
        : "initial-document-layout-overlaps-observed-hydration",
      initial_layout: initialLayout,
      first_observed_hydration_marker: firstHydrationMarker.name,
      limitation: "Trace association is temporal and does not identify a source function or prove causation.",
    };
  }
  const hypotheses = HYDRATION_TARGETS.map((target) => {
    const prefix = `${markerPrefix}${target.id}:`;
    const targetMarkers = markers.filter((marker) => marker.name.startsWith(prefix));
    const correlations = documentRootLayouts.flatMap((layout) => targetMarkers
      .map((marker) => ({ marker, relation: markerRelation(marker, layout, windowUs), layout }))
      .filter((item) => item.relation !== "outside-window"));
    let state = "inconclusive";
    if (targetMarkers.length && documentRootLayouts.length) {
      state = correlations.length ? "temporally-correlated" : "not-correlated-in-capture";
    }
    return {
      id: target.id,
      state,
      marker_count: targetMarkers.length,
      document_root_layout_count: documentRootLayouts.length,
      full_document_layout_count: fullLayouts.length,
      correlations: correlations.map((item) => ({
        marker: item.marker.name,
        relation: item.relation,
        marker_to_layout_start_ms: Number(
          ((item.layout.start_us - item.marker.timestamp_us) / 1000).toFixed(3),
        ),
        layout_kind: item.layout.full_document ? "full-document" : "document-root-partial",
        layout_duration_ms: item.layout.duration_ms,
        layout_dirty_objects: item.layout.dirty_objects,
        layout_total_objects: item.layout.total_objects,
      })),
      limitation: "A temporal relationship in one instrumented capture does not prove causation.",
    };
  });
  return {
    marker_count: markers.length,
    markers,
    layout_count: layouts.length,
    document_root_layout_count: documentRootLayouts.length,
    full_document_layout_count: fullLayouts.length,
    longest_layouts: layouts.slice(0, 12),
    initial_document_layout_finding: initialLayoutFinding,
    hypotheses,
  };
}

function attributionCoverage({
  correlation,
  observed,
  route,
  runtimeMessages,
  markerPrefix,
  traceTruncated = false,
}) {
  const markerNames = new Set(correlation.markers.map((marker) => marker.name));
  const observedMarkerNames = new Set(
    Array.isArray(observed.events) ? observed.events.map((event) => event.name) : [],
  );
  const expectedResources = ["research-json", "research-catalogue-json"];
  const expectedTargets = HYDRATION_TARGETS.map((target) => target.id);
  const missingResources = expectedResources.filter(
    (id) => !markerNames.has(`${markerPrefix}resource:${id}:complete`),
  );
  const missingTargets = expectedTargets.filter(
    (id) => !markerNames.has(`${markerPrefix}${id}:mutation-observer-delivery`),
  );
  const expectedRuntimeMarks = [
    ...expectedResources.map((id) => `${markerPrefix}resource:${id}:complete`),
    ...expectedTargets.map((id) => `${markerPrefix}${id}:mutation-observer-delivery`),
    `${markerPrefix}capture-complete`,
  ];
  const missingRuntimeMarks = expectedRuntimeMarks.filter(
    (name) => !observedMarkerNames.has(name),
  );
  const observedCounts = {
    register_rows: Number(observed.register_rows) > 0,
    profile_cards: Number(observed.profile_cards) > 0,
    note_cards: Number(observed.note_cards) > 0,
    catalogue_records: Number(observed.catalogue_records) > 0,
  };
  const missingObservedCounts = Object.entries(observedCounts)
    .filter(([, present]) => !present)
    .map(([key]) => key);
  const routeSuccess = route.status >= 200 && route.status < 300 && route.same_origin === true;
  const runtimeClean = runtimeMessages.page_error_count === 0
    && Number(runtimeMessages.console_counts.error || 0) === 0;
  const layoutEvidence = correlation.document_root_layout_count > 0;
  const observerLogComplete = observed.events_truncated !== true;
  return {
    route_success: routeSuccess,
    route_status: route.status,
    same_origin: route.same_origin,
    runtime_clean: runtimeClean,
    expected_resources: expectedResources,
    missing_resources: missingResources,
    expected_targets: expectedTargets,
    missing_targets: missingTargets,
    missing_runtime_marks: missingRuntimeMarks,
    missing_observed_counts: missingObservedCounts,
    observer_log_complete: observerLogComplete,
    minimized_trace_complete: traceTruncated !== true,
    document_root_layout_count: correlation.document_root_layout_count,
    passed: routeSuccess
      && runtimeClean
      && layoutEvidence
      && missingResources.length === 0
      && missingTargets.length === 0
      && missingRuntimeMarks.length === 0
      && missingObservedCounts.length === 0
      && observerLogComplete
      && traceTruncated !== true,
  };
}

function minimizedTrace(traceEvents, markerPrefix) {
  const relevantNames = new Set(["Layout", "UpdateLayoutTree", "PrePaint", "Paint"]);
  const relevant = traceEvents
    .filter((event) => relevantNames.has(event.name) || (
      typeof event.name === "string" && event.name.startsWith(markerPrefix)
    ))
    .sort((left, right) => Number(left.ts) - Number(right.ts));
  const retained = relevant
    .slice(0, MAX_MINIMIZED_TRACE_EVENTS)
    .map((event) => {
      const row = {
        name: event.name,
        ph: event.ph || "",
        ts: Number(event.ts),
        dur: Number(event.dur || 0),
        pid: event.pid,
        tid: event.tid,
      };
      if (event.name === "Layout") {
        const beginData = event.args?.beginData || {};
        const layoutRoots = Array.isArray(event.args?.endData?.layoutRoots)
          ? event.args.endData.layoutRoots.map((root) => ({ nodeName: root?.nodeName || "" }))
          : [];
        row.args = {
          beginData: {
            dirtyObjects: beginData.dirtyObjects,
            totalObjects: beginData.totalObjects,
            partialLayout: beginData.partialLayout === true,
          },
          endData: { layoutRoots },
        };
      }
      return row;
    });
  return {
    schema: MINIMIZED_TRACE_SCHEMA,
    marker_prefix: markerPrefix,
    original_event_count: traceEvents.length,
    relevant_event_count: relevant.length,
    retained_event_count: retained.length,
    event_limit: MAX_MINIMIZED_TRACE_EVENTS,
    trace_truncated: relevant.length > MAX_MINIMIZED_TRACE_EVENTS,
    redaction: "Only timing, layout-count, thread and nonce-bound marker metadata are retained; URLs, text and arbitrary CDP arguments are removed.",
    traceEvents: retained,
  };
}

async function readTraceStream(cdp, handle, maxBytes = MAX_RAW_TRACE_BYTES) {
  let value = "";
  let byteCount = 0;
  try {
    for (;;) {
      const chunk = await cdp.send("IO.read", { handle });
      const data = chunk.data || "";
      byteCount += Buffer.byteLength(data, "utf8");
      if (byteCount > maxBytes) {
        throw new Error(`Chromium trace exceeded the ${maxBytes}-byte diagnostic safety cap.`);
      }
      value += data;
      if (chunk.eof) break;
    }
    return value;
  } finally {
    await cdp.send("IO.close", { handle }).catch(() => undefined);
  }
}

async function captureAttribution({ baseUrl, waitMs }) {
  const { playwright, source: playwrightSource } = loadPlaywright();
  const browser = await playwright.chromium.launch({ headless: true });
  const browserVersion = browser.version();
  const context = await browser.newContext({ viewport: VIEWPORT });
  const markerPrefix = `${TRACE_MARKER_PREFIX}${crypto.randomBytes(12).toString("hex")}:`;
  await context.addInitScript(attributionInitScript, {
    markerPrefix,
    maxRuntimeEvents: MAX_RUNTIME_EVENTS,
  });
  const page = await context.newPage();
  const cdp = await context.newCDPSession(page);
  const consoleCounts = {};
  let pageErrorCount = 0;
  page.on("console", (message) => {
    const type = String(message.type() || "unknown");
    consoleCounts[type] = Number(consoleCounts[type] || 0) + 1;
  });
  page.on("pageerror", () => {
    pageErrorCount += 1;
  });
  const tracingComplete = new Promise((resolve) => cdp.once("Tracing.tracingComplete", resolve));
  await cdp.send("Tracing.start", {
    categories: "devtools.timeline,disabled-by-default-devtools.timeline,blink.user_timing",
    options: "record-as-much-as-possible",
    transferMode: "ReturnAsStream",
  });
  let observed = { events: [] };
  let rawTrace = "";
  let route = { status: 0, same_origin: false };
  try {
    const response = await page.goto(`${baseUrl}${ROUTE}?attribution=research-hydration`, { waitUntil: "load" });
    const finalUrl = new URL(page.url());
    const expectedOrigin = new URL(baseUrl).origin;
    route = {
      status: Number(response?.status() || 0),
      same_origin: finalUrl.origin === expectedOrigin,
    };
    await page.waitForTimeout(waitMs);
    observed = await page.evaluate(({ prefix, maxRuntimeEvents }) => {
      try {
        performance.mark(`${prefix}capture-complete`);
      } catch {
        // Trace markers are supplemental to the structured observer snapshot.
      }
      const marks = performance.getEntriesByType("mark")
        .filter((entry) => entry.name.startsWith(prefix))
        .map((entry) => ({
          name: entry.name,
          time_ms: Number(Number(entry.startTime).toFixed(3)),
        }));
      return {
        events: marks.slice(0, maxRuntimeEvents),
        events_truncated: marks.length >= maxRuntimeEvents,
        register_rows: document.querySelectorAll("[data-research] tr").length,
        profile_cards: document.querySelectorAll("[data-research-profiles] > *").length,
        note_cards: document.querySelectorAll("[data-research-notes] > *").length,
        catalogue_records: document.querySelectorAll("[data-research-catalogue-recent] > *").length,
      };
    }, { prefix: markerPrefix, maxRuntimeEvents: MAX_RUNTIME_EVENTS });
  } finally {
    try {
      await cdp.send("Tracing.end");
      const completion = await tracingComplete;
      rawTrace = await readTraceStream(cdp, completion.stream);
    } finally {
      await context.close();
      await browser.close();
    }
  }
  return {
    raw_trace: rawTrace,
    observed,
    route,
    runtime_messages: {
      console_counts: consoleCounts,
      page_error_count: pageErrorCount,
    },
    marker_prefix: markerPrefix,
    playwright_source: playwrightSource,
    browser_version: browserVersion,
  };
}

function sha256(value) {
  return crypto.createHash("sha256").update(value).digest("hex");
}

function writeExclusive(filePath, contents) {
  fs.writeFileSync(filePath, contents, { encoding: "utf8", flag: "wx" });
}

async function runAttribution(options = {}) {
  const paths = options.paths || {};
  const repoRoot = path.resolve(paths.repoRoot || REPO_ROOT);
  const sourceRoot = ensureSourceRoot(options.sourceRoot || DEFAULT_SOURCE_ROOT, { repoRoot });
  const outputRoot = resolveRunDirectory(options.outputRoot || "", {
    ...paths,
    repoRoot,
  });
  const sourceBefore = snapshotWebsiteTree(sourceRoot);
  const runtime = await startStaticServer(sourceRoot);
  let capture;
  try {
    capture = await captureAttribution({ baseUrl: runtime.baseUrl, waitMs: options.waitMs ?? 800 });
  } finally {
    await new Promise((resolve) => runtime.server.close(resolve));
  }
  const sourceAfter = snapshotWebsiteTree(sourceRoot);
  const stable = sourceBefore.sha256 === sourceAfter.sha256;
  const parsedTrace = JSON.parse(capture.raw_trace);
  const traceEvents = Array.isArray(parsedTrace.traceEvents) ? parsedTrace.traceEvents : [];
  const correlation = correlateHydration(traceEvents, { markerPrefix: capture.marker_prefix });
  const minimized = minimizedTrace(traceEvents, capture.marker_prefix);
  const coverage = attributionCoverage({
    correlation,
    observed: capture.observed,
    route: capture.route,
    runtimeMessages: capture.runtime_messages,
    markerPrefix: capture.marker_prefix,
    traceTruncated: minimized.trace_truncated,
  });
  const analysisState = stable && coverage.passed ? "complete" : "incomplete";
  const minimizedTraceContents = `${JSON.stringify(minimized, null, 2)}\n`;
  const materializedOutputRoot = materializeRunDirectory(outputRoot, { repoRoot });
  const tracePath = path.join(materializedOutputRoot, "research-hydration.trace.json");
  const receiptPath = path.join(materializedOutputRoot, "AUREON_RESEARCH_HYDRATION_ATTRIBUTION.json");
  const receipt = {
    schema: RECEIPT_SCHEMA,
    observed_at: new Date().toISOString(),
    state: analysisState,
    analysis_only: true,
    release_eligible: false,
    package_authority: "none",
    deployment_authority: "none",
    authority: {
      scope: "read-only staged or canonical research-route runtime attribution",
      canonical_website_mutation: "never",
      candidate_creation: "none",
      release_eligibility: false,
      package_authority: "none",
      deployment_authority: "none",
      credential_access: "none",
    },
    target: {
      route: ROUTE,
      viewport: VIEWPORT,
      browser: "chromium",
      self_hosted: true,
      response: capture.route,
      source_root: sourceRoot,
      source_before: selectedSourceBinding(sourceRoot, sourceBefore),
      source_after_tree_sha256: sourceAfter.sha256,
      source_stable: stable,
    },
    instrumentation: {
      protocol_version: PROTOCOL_VERSION,
      protocol_sha256: sha256(fs.readFileSync(__filename)),
      marker_prefix: capture.marker_prefix,
      post_load_wait_ms: options.waitMs ?? 800,
      playwright_source: capture.playwright_source,
      browser_version: capture.browser_version,
      capture_count: 1,
      method: "nonce-bound same-origin resource, early mutation-observer delivery, and resize observations correlated to minimized Chromium Layout trace events",
      non_gating: true,
      caveat: "Instrumentation changes the diagnostic runtime and is not performance-budget evidence; a single capture is an investigative hint only.",
    },
    observed: capture.observed,
    runtime_messages: capture.runtime_messages,
    coverage,
    correlation,
    trace: {
      path: path.relative(repoRoot, tracePath).split(path.sep).join("/"),
      schema: MINIMIZED_TRACE_SCHEMA,
      sha256: sha256(minimizedTraceContents),
      original_event_count: traceEvents.length,
      relevant_event_count: minimized.relevant_event_count,
      retained_event_count: minimized.retained_event_count,
      trace_truncated: minimized.trace_truncated,
      raw_trace_persisted: false,
    },
    next_step: analysisState === "complete"
      ? "Treat this single capture only as an investigative hint. Do not use it as causal proof, a gate override, or sufficient evidence for a remediation work order; corroborate with a separately scoped investigation."
      : "Do not infer a cause or create a successor candidate; repair the diagnostic evidence first.",
  };
  writeExclusive(tracePath, minimizedTraceContents);
  writeExclusive(receiptPath, `${JSON.stringify(receipt, null, 2)}\n`);
  return { receipt, receiptPath, tracePath };
}

async function main(argv = process.argv.slice(2)) {
  const options = parseCli(argv);
  if (options.help) {
    process.stdout.write(usage());
    return 0;
  }
  const result = await runAttribution(options);
  process.stdout.write(`${JSON.stringify({
    state: result.receipt.state,
    receipt: result.receiptPath,
    trace: result.tracePath,
  }, null, 2)}\n`);
  return result.receipt.state === "complete" ? 0 : 1;
}

module.exports = {
  DEFAULT_OUTPUT_ROOT,
  DEFAULT_SOURCE_ROOT,
  HYDRATION_TARGETS,
  MARKER_WINDOW_US,
  ROUTE,
  TRACE_MARKER_PREFIX,
  VIEWPORT,
  attributionCoverage,
  attributionInitScript,
  classifyHydrationTarget,
  correlateHydration,
  documentLayoutEvents,
  ensureSourceRoot,
  minimizedTrace,
  materializeRunDirectory,
  parseCli,
  resolveRunDirectory,
  runAttribution,
  traceMarkerEvents,
  usage,
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

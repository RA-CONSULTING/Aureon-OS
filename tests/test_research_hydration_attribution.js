"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const test = require("node:test");

const {
  TRACE_MARKER_PREFIX,
  attributionCoverage,
  classifyHydrationTarget,
  correlateHydration,
  ensureSourceRoot,
  minimizedTrace,
  parseCli,
  resolveRunDirectory,
} = require("../tools/aureon_research_hydration_attribution.js");

test("the attribution CLI is single-capture and bounds its wait period", () => {
  const defaults = parseCli([]);
  assert.equal(defaults.waitMs, 800);
  assert.equal(parseCli(["--wait-ms=0"]).waitMs, 0);
  assert.throws(() => parseCli(["--wait-ms=10001"]), /0 to 10000/);
  assert.throws(() => parseCli(["--unexpected"]), /Unknown option/);
});

test("hydration target classification is limited to known research containers", () => {
  assert.equal(
    classifyHydrationTarget((selector) => selector === "[data-research]"),
    "research-register-hydration",
  );
  assert.equal(
    classifyHydrationTarget((selector) => selector.includes("data-research-catalogue-recent")),
    "research-catalogue-hydration",
  );
  assert.equal(classifyHydrationTarget(() => false), "");
});

test("correlation reports temporal evidence without making a causal claim", () => {
  const events = [
    {
      name: "Layout",
      ph: "X",
      ts: 100_000,
      dur: 120_000,
      pid: 1,
      tid: 2,
      args: {
        beginData: { dirtyObjects: 790, totalObjects: 790, partialLayout: false },
        endData: { layoutRoots: [{ nodeName: "#document" }] },
      },
    },
    {
      name: `${TRACE_MARKER_PREFIX}research-register-hydration:mutation-observer-delivery`,
      ph: "I",
      ts: 95_000,
      pid: 1,
      tid: 2,
    },
    {
      name: `${TRACE_MARKER_PREFIX}research-profiles-hydration:mutation-observer-delivery`,
      ph: "I",
      ts: 150_000,
      pid: 1,
      tid: 2,
    },
  ];
  const result = correlateHydration(events);
  const register = result.hypotheses.find((item) => item.id === "research-register-hydration");
  const profiles = result.hypotheses.find((item) => item.id === "research-profiles-hydration");
  const notes = result.hypotheses.find((item) => item.id === "research-notes-hydration");
  assert.equal(register.state, "temporally-correlated");
  assert.equal(profiles.state, "temporally-correlated");
  assert.equal(notes.state, "inconclusive");
  assert.match(register.limitation, /does not prove causation/);
  assert.equal(result.longest_layouts[0].full_document, true);
  assert.equal(result.longest_layouts[0].document_root, true);
  assert.equal(
    result.initial_document_layout_finding.state,
    "initial-document-layout-overlaps-observed-hydration",
  );
  assert.equal(result.longest_layouts[0].dirty_objects, 790);
  assert.equal(register.correlations[0].layout_kind, "full-document");
  assert.equal(register.correlations[0].marker_to_layout_start_ms, 5);
});

test("coverage rejects a marker-only capture and requires complete bounded evidence", () => {
  const prefix = `${TRACE_MARKER_PREFIX}${"a".repeat(24)}:`;
  const marker = (name, ts) => ({ name: `${prefix}${name}`, ph: "I", ts, pid: 1, tid: 1 });
  const trace = [
    {
      name: "Layout",
      ph: "X",
      ts: 100_000,
      dur: 25_000,
      pid: 1,
      tid: 1,
      args: {
        beginData: { dirtyObjects: 100, totalObjects: 100, partialLayout: false },
        endData: { layoutRoots: [{ nodeName: "#document" }] },
      },
    },
    marker("document-start", 50_000),
  ];
  const incomplete = attributionCoverage({
    correlation: correlateHydration(trace, { markerPrefix: prefix }),
    observed: { events: [], events_truncated: false, register_rows: 1, profile_cards: 1, note_cards: 1, catalogue_records: 1 },
    route: { status: 200, same_origin: true },
    runtimeMessages: { console_counts: {}, page_error_count: 0 },
    markerPrefix: prefix,
  });
  assert.equal(incomplete.passed, false);
  assert.deepEqual(incomplete.missing_resources, ["research-json", "research-catalogue-json"]);

  const completeTrace = [
    trace[0],
    marker("resource:research-json:complete", 75_000),
    marker("resource:research-catalogue-json:complete", 76_000),
    marker("research-register-hydration:mutation-observer-delivery", 90_000),
    marker("research-profiles-hydration:mutation-observer-delivery", 91_000),
    marker("research-notes-hydration:mutation-observer-delivery", 92_000),
    marker("research-catalogue-hydration:mutation-observer-delivery", 93_000),
  ];
  const runtimeEvents = completeTrace
    .filter((event) => event.name.startsWith(prefix))
    .map((event, index) => ({ name: event.name, time_ms: index }));
  runtimeEvents.push({ name: `${prefix}capture-complete`, time_ms: 100 });
  const complete = attributionCoverage({
    correlation: correlateHydration(completeTrace, { markerPrefix: prefix }),
    observed: {
      events: runtimeEvents,
      events_truncated: false,
      register_rows: 1,
      profile_cards: 1,
      note_cards: 1,
      catalogue_records: 1,
    },
    route: { status: 200, same_origin: true },
    runtimeMessages: { console_counts: {}, page_error_count: 0 },
    markerPrefix: prefix,
  });
  assert.equal(complete.passed, true);
  assert.deepEqual(complete.missing_runtime_marks, []);
});

test("the persisted trace is minimized and removes arbitrary URL-bearing arguments", () => {
  const prefix = `${TRACE_MARKER_PREFIX}${"b".repeat(24)}:`;
  const minimized = minimizedTrace([
    { name: "ResourceSendRequest", ph: "I", ts: 1, args: { url: "https://private.example/secret" } },
    {
      name: "Layout",
      ph: "X",
      ts: 2,
      dur: 3,
      pid: 1,
      tid: 1,
      args: {
        beginData: { dirtyObjects: 2, totalObjects: 2, partialLayout: false },
        endData: { layoutRoots: [{ nodeName: "#document", url: "https://private.example/secret" }] },
      },
    },
    { name: `${prefix}capture-complete`, ph: "I", ts: 4, pid: 1, tid: 1 },
  ], prefix);
  assert.equal(minimized.traceEvents.length, 2);
  assert.doesNotMatch(JSON.stringify(minimized), /https:\/\//);
  assert.equal(minimized.trace_truncated, false);
});

function writeAttributionSite(root) {
  for (const relative of [
    "research/index.html",
    "script.js",
    "data/research.json",
    "data/research-catalogue.json",
  ]) {
    const target = path.join(root, relative);
    fs.mkdirSync(path.dirname(target), { recursive: true });
    fs.writeFileSync(target, "fixture\n", "utf8");
  }
}

test("attribution source policy permits only canonical or direct staged website trees", () => {
  const temporary = fs.mkdtempSync(path.join(os.tmpdir(), "aureon-attribution-source-"));
  const canonical = path.join(temporary, "website");
  const staged = path.join(temporary, "artifacts", "website-candidates", "candidate-a", "website");
  const nested = path.join(temporary, "artifacts", "website-candidates", "candidate-a", "nested", "website");
  const untrusted = path.join(temporary, "untrusted");
  writeAttributionSite(canonical);
  writeAttributionSite(staged);
  writeAttributionSite(nested);
  writeAttributionSite(untrusted);
  assert.equal(ensureSourceRoot(canonical, { repoRoot: temporary }), canonical);
  assert.equal(ensureSourceRoot(staged, { repoRoot: temporary }), staged);
  assert.throws(() => ensureSourceRoot(nested, { repoRoot: temporary }), /only canonical website/);
  assert.throws(() => ensureSourceRoot(untrusted, { repoRoot: temporary }), /only canonical website/);
  fs.rmSync(temporary, { recursive: true, force: true });
});

test("attribution artifacts cannot be routed outside their controlled root", () => {
  const temporary = fs.mkdtempSync(path.join(os.tmpdir(), "aureon-attribution-"));
  const root = path.join(temporary, "artifacts", "website-operator", "research-hydration-attribution");
  const result = resolveRunDirectory("artifacts/website-operator/research-hydration-attribution/run-a", {
    repoRoot: temporary,
  });
  assert.equal(result, path.join(root, "run-a"));
  assert.throws(
    () => resolveRunDirectory("outside", { repoRoot: temporary }),
    /must be a new child/,
  );
  fs.mkdirSync(path.join(root, "exists"), { recursive: true });
  assert.throws(
    () => resolveRunDirectory("artifacts/website-operator/research-hydration-attribution/exists", {
      repoRoot: temporary,
    }),
    /already exists/,
  );
  fs.rmSync(temporary, { recursive: true, force: true });
});

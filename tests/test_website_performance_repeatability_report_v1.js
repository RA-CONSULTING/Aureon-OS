"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const test = require("node:test");

const {
  CANONICAL_ROUTE_MATRIX,
  METRIC_RULES,
  REPORT_SCHEMA,
  RepeatabilityReportError,
  buildRepeatabilityReport,
  median,
  parseCli,
} = require("../tools/aureon_website_performance_repeatability_report_v1.js");
const { PERFORMANCE_BUDGETS } = require("../tools/aureon_website_visual_qa_v28.js");

function makeChecks(metrics) {
  return {
    ttfb: { value: metrics.ttfbMs, budget: PERFORMANCE_BUDGETS.ttfbMs, pass: metrics.ttfbMs <= 800 },
    domContentLoaded: {
      value: metrics.domContentLoadedMs,
      budget: PERFORMANCE_BUDGETS.domContentLoadedMs,
      pass: metrics.domContentLoadedMs <= 2500,
    },
    loadEvent: {
      value: metrics.loadEventMs,
      budget: PERFORMANCE_BUDGETS.loadEventMs,
      pass: metrics.loadEventMs <= 3500,
    },
    lcp: { value: metrics.lcpMs, budget: PERFORMANCE_BUDGETS.lcpMs, measurable: true, pass: metrics.lcpMs <= 2500 },
    cls: { value: metrics.cls, budget: PERFORMANCE_BUDGETS.cls, measurable: true, pass: metrics.cls <= 0.1 },
    requestCount: {
      value: metrics.requestCount,
      budget: PERFORMANCE_BUDGETS.requestCount,
      pass: metrics.requestCount <= 80,
    },
    transferProxyBytes: {
      value: metrics.transferProxyBytes,
      budget: PERFORMANCE_BUDGETS.transferProxyBytes,
      pass: metrics.transferProxyBytes <= 3000000,
    },
    longTaskTotal: {
      value: metrics.longTaskTotalMs,
      budget: PERFORMANCE_BUDGETS.longTaskTotalMs,
      measurable: true,
      pass: metrics.longTaskTotalMs <= 300,
    },
  };
}

function makeReceipt({ sourceHash = "A".repeat(64), investorLongTask = 100, version = "149.0.7827.55" } = {}) {
  const performance = CANONICAL_ROUTE_MATRIX.map((route) => {
    const longTaskTotalMs = route.name === "investor" ? investorLongTask : 100;
    const metrics = {
      ttfbMs: 100,
      domContentLoadedMs: 200,
      loadEventMs: 300,
      lcpMs: 400,
      cls: 0.01,
      requestCount: 10,
      transferProxyBytes: 1000,
      longTaskTotalMs,
      observerSupport: { "layout-shift": true, "largest-contentful-paint": true, longtask: true },
    };
    return {
      routeName: route.name,
      route: route.route,
      metrics,
      budgets: PERFORMANCE_BUDGETS,
      checks: makeChecks(metrics),
      pass: longTaskTotalMs <= PERFORMANCE_BUDGETS.longTaskTotalMs,
    };
  });
  return {
    schema: "aureon-website-visual-qa-v28.3",
    generatedAt: "2026-07-28T10:00:00.000Z",
    status: investorLongTask <= PERFORMANCE_BUDGETS.longTaskTotalMs ? "PASS" : "FAIL",
    selfHosted: true,
    selectedRoutes: CANONICAL_ROUTE_MATRIX,
    policies: { performanceBudgets: PERFORMANCE_BUDGETS },
    sourceBinding: {
      before: { sha256: sourceHash, fileCount: 172, totalBytes: 19000000 },
      after: { sha256: sourceHash },
      stable: true,
      servedFromHashedSource: true,
    },
    engines: [
      {
        engine: "chromium",
        status: investorLongTask <= PERFORMANCE_BUDGETS.longTaskTotalMs ? "PASS" : "FAIL",
        browserVersion: version,
        performance,
      },
    ],
  };
}

function writeReceipt(root, name, payload) {
  const target = path.join(root, name);
  fs.writeFileSync(target, `${JSON.stringify(payload, null, 2)}\n`, "utf8");
  return target;
}

test("CLI requires an explicit 3-5 receipt diagnostic set and output", () => {
  assert.deepEqual(
    parseCli(["--receipt", "one.json", "--receipt", "two.json", "--receipt", "three.json", "--output", "out.json"]),
    { receipts: ["one.json", "two.json", "three.json"], output: "out.json", help: false },
  );
  assert.throws(
    () => parseCli(["--receipt", "one.json", "--receipt", "two.json", "--output", "out.json"]),
    RepeatabilityReportError,
  );
});

test("same-source report exposes raw variability without release authority", () => {
  const temporary = fs.mkdtempSync(path.join(os.tmpdir(), "aureon-repeatability-"));
  try {
    const inputs = [
      writeReceipt(temporary, "one.json", makeReceipt({ investorLongTask: 100 })),
      writeReceipt(temporary, "two.json", makeReceipt({ investorLongTask: 500 })),
      writeReceipt(temporary, "three.json", makeReceipt({ investorLongTask: 250 })),
    ];
    const report = buildRepeatabilityReport(inputs, new Date("2026-07-28T11:00:00.000Z"));
    const investor = report.routes.find((route) => route.name === "investor");
    const longTask = investor.metrics.find((metric) => metric.id === "long-task-total");
    assert.equal(report.schema, REPORT_SCHEMA);
    assert.equal(report.state, "diagnostic-only");
    assert.equal(report.authority.release_eligible, false);
    assert.equal(Object.hasOwn(report, "pass"), false);
    assert.deepEqual(longTask.samples.map((sample) => sample.value), [100, 500, 250]);
    assert.equal(longTask.within_budget_count, 2);
    assert.equal(longTask.over_budget_count, 1);
    assert.equal(longTask.minimum, 100);
    assert.equal(longTask.median, 250);
    assert.equal(longTask.maximum, 500);
    assert.equal(longTask.range, 400);
  } finally {
    fs.rmSync(temporary, { recursive: true, force: true });
  }
});

test("repeatability analysis rejects mixed source bindings", () => {
  const temporary = fs.mkdtempSync(path.join(os.tmpdir(), "aureon-repeatability-source-"));
  try {
    const inputs = [
      writeReceipt(temporary, "one.json", makeReceipt()),
      writeReceipt(temporary, "two.json", makeReceipt()),
      writeReceipt(temporary, "three.json", makeReceipt({ sourceHash: "B".repeat(64) })),
    ];
    assert.throws(() => buildRepeatabilityReport(inputs), /different source trees or inventories/);
  } finally {
    fs.rmSync(temporary, { recursive: true, force: true });
  }
});

test("median is exact for odd and even sample counts", () => {
  assert.equal(median([3, 1, 2]), 2);
  assert.equal(median([10, 2, 4, 8]), 6);
  assert.equal(METRIC_RULES.length, 8);
});

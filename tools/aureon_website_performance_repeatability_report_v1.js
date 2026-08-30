#!/usr/bin/env node
"use strict";

/*
 * A diagnostic companion to the V28 visual QA receipt. It deliberately reads
 * completed receipts only: it does not launch browsers, change the website,
 * change a performance budget, or produce release authority. Its job is to
 * make a small, exact set of same-source measurements inspectable when a
 * single strict receipt detects a potentially non-repeatable result.
 */

const crypto = require("node:crypto");
const fs = require("node:fs");
const path = require("node:path");

const { PERFORMANCE_BUDGETS } = require("./aureon_website_visual_qa_v28.js");

const VISUAL_QA_SCHEMA = "aureon-website-visual-qa-v28.3";
const REPORT_SCHEMA = "aureon-website-performance-repeatability-report.v1";
const MIN_RECEIPTS = 3;
const MAX_RECEIPTS = 5;
const CHROMIUM_ENGINE = "chromium";

const CANONICAL_ROUTE_MATRIX = Object.freeze([
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

const METRIC_RULES = Object.freeze([
  { id: "ttfb", metric: "ttfbMs", check: "ttfb", budget: "ttfbMs" },
  {
    id: "dom-content-loaded",
    metric: "domContentLoadedMs",
    check: "domContentLoaded",
    budget: "domContentLoadedMs",
  },
  { id: "load-event", metric: "loadEventMs", check: "loadEvent", budget: "loadEventMs" },
  { id: "lcp", metric: "lcpMs", check: "lcp", budget: "lcpMs", measurable: true },
  { id: "cls", metric: "cls", check: "cls", budget: "cls", measurable: true },
  {
    id: "request-count",
    metric: "requestCount",
    check: "requestCount",
    budget: "requestCount",
  },
  {
    id: "transfer-proxy-bytes",
    metric: "transferProxyBytes",
    check: "transferProxyBytes",
    budget: "transferProxyBytes",
  },
  {
    id: "long-task-total",
    metric: "longTaskTotalMs",
    check: "longTaskTotal",
    budget: "longTaskTotalMs",
    measurable: true,
    observer: "longtask",
  },
]);

class RepeatabilityReportError extends Error {}

function usage() {
  return `Usage:
  node tools/aureon_website_performance_repeatability_report_v1.js \\
    --receipt PATH --receipt PATH --receipt PATH [--receipt PATH] [--receipt PATH] \\
    --output PATH

Create a diagnostic-only repeatability report from 3-5 completed V28.3
Visual QA receipts for the exact same self-hosted website tree and Chromium
browser major version. Every input receipt remains independently authoritative:
this report cannot change a budget, mark a release as eligible, or waive an
individual failing receipt.
`;
}

function parseCli(argv) {
  const options = { receipts: [], output: "", help: false };
  for (let index = 0; index < argv.length; index += 1) {
    const argument = argv[index];
    if (argument === "--help" || argument === "-h") {
      options.help = true;
      continue;
    }
    const inlineReceipt = argument.match(/^--receipt=(.+)$/);
    if (inlineReceipt) {
      options.receipts.push(inlineReceipt[1]);
      continue;
    }
    const inlineOutput = argument.match(/^--output=(.+)$/);
    if (inlineOutput) {
      options.output = inlineOutput[1];
      continue;
    }
    if (argument === "--receipt" || argument === "--output") {
      const value = argv[index + 1];
      if (!value || value.startsWith("--")) {
        throw new RepeatabilityReportError(`${argument} requires a path.`);
      }
      if (argument === "--receipt") {
        options.receipts.push(value);
      } else {
        options.output = value;
      }
      index += 1;
      continue;
    }
    throw new RepeatabilityReportError(`Unknown argument: ${argument}`);
  }
  if (options.help) return options;
  if (options.receipts.length < MIN_RECEIPTS || options.receipts.length > MAX_RECEIPTS) {
    throw new RepeatabilityReportError(
      `Provide ${MIN_RECEIPTS}-${MAX_RECEIPTS} --receipt inputs; received ${options.receipts.length}.`,
    );
  }
  if (!options.output) {
    throw new RepeatabilityReportError("--output is required for a diagnostic receipt.");
  }
  return options;
}

function stableStringify(value) {
  if (Array.isArray(value)) {
    return `[${value.map((item) => stableStringify(item)).join(",")}]`;
  }
  if (value && typeof value === "object") {
    return `{${Object.keys(value)
      .sort()
      .map((key) => `${JSON.stringify(key)}:${stableStringify(value[key])}`)
      .join(",")}}`;
  }
  return JSON.stringify(value);
}

function sha256File(filePath) {
  return crypto.createHash("sha256").update(fs.readFileSync(filePath)).digest("hex").toUpperCase();
}

function readJson(filePath) {
  const resolved = path.resolve(filePath);
  if (!fs.statSync(resolved).isFile()) {
    throw new RepeatabilityReportError(`Receipt is not a file: ${resolved}`);
  }
  try {
    return { path: resolved, payload: JSON.parse(fs.readFileSync(resolved, "utf8")) };
  } catch (error) {
    throw new RepeatabilityReportError(`Could not parse receipt ${resolved}: ${error.message}`);
  }
}

function isPlainObject(value) {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

function requireObject(value, label) {
  if (!isPlainObject(value)) {
    throw new RepeatabilityReportError(`${label} must be an object.`);
  }
  return value;
}

function requireString(value, label) {
  if (typeof value !== "string" || !value.trim()) {
    throw new RepeatabilityReportError(`${label} must be a non-empty string.`);
  }
  return value;
}

function requireFiniteNumber(value, label) {
  if (!Number.isFinite(value) || value < 0) {
    throw new RepeatabilityReportError(`${label} must be a non-negative finite number.`);
  }
  return value;
}

function browserMajor(version) {
  const match = requireString(version, "Chromium browserVersion").match(/^(\d+)(?:\.\d+){1,3}$/);
  if (!match) {
    throw new RepeatabilityReportError(`Unsupported Chromium browserVersion: ${version}`);
  }
  return Number(match[1]);
}

function median(values) {
  if (!Array.isArray(values) || values.length === 0) {
    throw new RepeatabilityReportError("Cannot calculate a median without samples.");
  }
  const ordered = [...values].sort((left, right) => left - right);
  const middle = Math.floor(ordered.length / 2);
  return ordered.length % 2 === 1 ? ordered[middle] : (ordered[middle - 1] + ordered[middle]) / 2;
}

function validatePerformanceRecord(record, expectedRoute, budgets, receiptPath) {
  const prefix = `${receiptPath}: Chromium performance record for ${expectedRoute.name}`;
  requireObject(record, prefix);
  if (record.routeName !== expectedRoute.name || record.route !== expectedRoute.route) {
    throw new RepeatabilityReportError(`${prefix} does not match the canonical route matrix.`);
  }
  if (stableStringify(record.budgets) !== stableStringify(budgets)) {
    throw new RepeatabilityReportError(`${prefix} has a different performance budget binding.`);
  }
  const metrics = requireObject(record.metrics, `${prefix}.metrics`);
  const checks = requireObject(record.checks, `${prefix}.checks`);
  const observerSupport = requireObject(metrics.observerSupport, `${prefix}.metrics.observerSupport`);
  const normalized = {};
  for (const rule of METRIC_RULES) {
    const value = requireFiniteNumber(metrics[rule.metric], `${prefix}.metrics.${rule.metric}`);
    const check = requireObject(checks[rule.check], `${prefix}.checks.${rule.check}`);
    if (check.value !== value || check.budget !== budgets[rule.budget]) {
      throw new RepeatabilityReportError(`${prefix} has mismatched ${rule.id} evidence.`);
    }
    if (rule.measurable && check.measurable !== true) {
      throw new RepeatabilityReportError(`${prefix} has unsupported ${rule.id} evidence.`);
    }
    if (rule.observer && observerSupport[rule.observer] !== true) {
      throw new RepeatabilityReportError(`${prefix} lacks ${rule.observer} observer support.`);
    }
    const withinBudget = value <= budgets[rule.budget];
    if (check.pass !== withinBudget) {
      throw new RepeatabilityReportError(`${prefix} has inconsistent ${rule.id} check evidence.`);
    }
    normalized[rule.id] = value;
  }
  return normalized;
}

function validateReceipt(filePath) {
  const receipt = readJson(filePath);
  const payload = requireObject(receipt.payload, `${receipt.path} root`);
  if (payload.schema !== VISUAL_QA_SCHEMA) {
    throw new RepeatabilityReportError(`${receipt.path} is not a ${VISUAL_QA_SCHEMA} receipt.`);
  }
  if (payload.selfHosted !== true) {
    throw new RepeatabilityReportError(`${receipt.path} was not self-hosted from a local source tree.`);
  }
  const sourceBinding = requireObject(payload.sourceBinding, `${receipt.path}.sourceBinding`);
  const before = requireObject(sourceBinding.before, `${receipt.path}.sourceBinding.before`);
  const after = requireObject(sourceBinding.after, `${receipt.path}.sourceBinding.after`);
  const sourceSha256 = requireString(before.sha256, `${receipt.path}.sourceBinding.before.sha256`).toUpperCase();
  if (!/^[A-F0-9]{64}$/.test(sourceSha256)) {
    throw new RepeatabilityReportError(`${receipt.path} has an invalid source SHA-256.`);
  }
  if (
    sourceBinding.stable !== true ||
    sourceBinding.servedFromHashedSource !== true ||
    String(after.sha256 || "").toUpperCase() !== sourceSha256
  ) {
    throw new RepeatabilityReportError(`${receipt.path} does not bind a stable self-hosted source tree.`);
  }
  const source = {
    sha256: sourceSha256,
    fileCount: requireFiniteNumber(before.fileCount, `${receipt.path}.sourceBinding.before.fileCount`),
    totalBytes: requireFiniteNumber(before.totalBytes, `${receipt.path}.sourceBinding.before.totalBytes`),
  };
  const policies = requireObject(payload.policies, `${receipt.path}.policies`);
  const budgets = requireObject(policies.performanceBudgets, `${receipt.path}.policies.performanceBudgets`);
  if (stableStringify(budgets) !== stableStringify(PERFORMANCE_BUDGETS)) {
    throw new RepeatabilityReportError(`${receipt.path} does not use the immutable V28 performance budgets.`);
  }
  if (stableStringify(payload.selectedRoutes) !== stableStringify(CANONICAL_ROUTE_MATRIX)) {
    throw new RepeatabilityReportError(`${receipt.path} has an incomplete or non-canonical route matrix.`);
  }
  if (!Array.isArray(payload.engines)) {
    throw new RepeatabilityReportError(`${receipt.path}.engines must be an array.`);
  }
  const chromium = payload.engines.find((engine) => engine?.engine === CHROMIUM_ENGINE);
  if (!chromium || !Array.isArray(chromium.performance)) {
    throw new RepeatabilityReportError(`${receipt.path} lacks a Chromium performance matrix.`);
  }
  if (chromium.performance.length !== CANONICAL_ROUTE_MATRIX.length) {
    throw new RepeatabilityReportError(`${receipt.path} has an incomplete Chromium performance matrix.`);
  }
  const recordsByRoute = new Map();
  for (const record of chromium.performance) {
    if (!record || recordsByRoute.has(record.routeName)) {
      throw new RepeatabilityReportError(`${receipt.path} has duplicate or invalid Chromium route evidence.`);
    }
    recordsByRoute.set(record.routeName, record);
  }
  const records = {};
  for (const expectedRoute of CANONICAL_ROUTE_MATRIX) {
    const record = recordsByRoute.get(expectedRoute.name);
    if (!record) {
      throw new RepeatabilityReportError(`${receipt.path} lacks ${expectedRoute.name} performance evidence.`);
    }
    records[expectedRoute.name] = validatePerformanceRecord(
      record,
      expectedRoute,
      budgets,
      receipt.path,
    );
  }
  return {
    inputPath: receipt.path,
    sha256: sha256File(receipt.path),
    generatedAt: requireString(payload.generatedAt, `${receipt.path}.generatedAt`),
    visualQaStatus: requireString(payload.status, `${receipt.path}.status`),
    chromiumStatus: requireString(chromium.status, `${receipt.path}.chromium.status`),
    browserVersion: requireString(chromium.browserVersion, `${receipt.path}.chromium.browserVersion`),
    browserMajor: browserMajor(chromium.browserVersion),
    source,
    budgets,
    records,
  };
}

function aggregateMetric(receipts, route, rule) {
  const budget = PERFORMANCE_BUDGETS[rule.budget];
  const samples = receipts.map((receipt) => {
    const value = receipt.records[route.name][rule.id];
    return {
      receipt_sha256: receipt.sha256,
      generated_at: receipt.generatedAt,
      value,
      within_budget: value <= budget,
    };
  });
  const values = samples.map((sample) => sample.value);
  const withinBudgetCount = samples.filter((sample) => sample.within_budget).length;
  const minimum = Math.min(...values);
  const maximum = Math.max(...values);
  return {
    id: rule.id,
    metric: rule.metric,
    budget,
    samples,
    sample_count: samples.length,
    within_budget_count: withinBudgetCount,
    over_budget_count: samples.length - withinBudgetCount,
    minimum,
    median: median(values),
    maximum,
    range: maximum - minimum,
  };
}

function buildRepeatabilityReport(receiptPaths, now = new Date()) {
  if (!Array.isArray(receiptPaths) || receiptPaths.length < MIN_RECEIPTS || receiptPaths.length > MAX_RECEIPTS) {
    throw new RepeatabilityReportError(
      `Repeatability analysis needs ${MIN_RECEIPTS}-${MAX_RECEIPTS} receipt paths.`,
    );
  }
  const receipts = receiptPaths.map((filePath) => validateReceipt(filePath));
  const first = receipts[0];
  for (const receipt of receipts.slice(1)) {
    if (stableStringify(receipt.source) !== stableStringify(first.source)) {
      throw new RepeatabilityReportError("Input receipts bind different source trees or inventories.");
    }
    if (stableStringify(receipt.budgets) !== stableStringify(first.budgets)) {
      throw new RepeatabilityReportError("Input receipts use different performance budgets.");
    }
    if (receipt.browserMajor !== first.browserMajor) {
      throw new RepeatabilityReportError("Input receipts use different Chromium browser major versions.");
    }
  }
  return {
    schema: REPORT_SCHEMA,
    generated_at: new Date(now).toISOString(),
    state: "diagnostic-only",
    authority: {
      scope: "receipt-only performance repeatability measurement",
      website_mutation: "none",
      performance_budget_change: "none",
      release_eligible: false,
      deployment_authority: "none",
      failed_receipt_waiver: "never",
      policy: "Every individual Visual QA receipt remains fail-closed under its unchanged release policy.",
    },
    method: {
      visual_qa_schema: VISUAL_QA_SCHEMA,
      chromium_engine: CHROMIUM_ENGINE,
      chromium_browser_major: first.browserMajor,
      receipt_count: receipts.length,
      canonical_route_matrix: CANONICAL_ROUTE_MATRIX,
      performance_budgets: PERFORMANCE_BUDGETS,
      unsupported_metric_policy: "Refuse unsupported or non-measurable metric evidence.",
    },
    source_binding: {
      ...first.source,
      self_hosted: true,
      stable_for_every_input: true,
    },
    input_receipts: receipts.map((receipt) => ({
      path: receipt.inputPath,
      sha256: receipt.sha256,
      generated_at: receipt.generatedAt,
      visual_qa_status: receipt.visualQaStatus,
      chromium_status: receipt.chromiumStatus,
      chromium_browser_version: receipt.browserVersion,
    })),
    routes: CANONICAL_ROUTE_MATRIX.map((route) => ({
      ...route,
      metrics: METRIC_RULES.map((rule) => aggregateMetric(receipts, route, rule)),
    })),
    interpretation_boundary: [
      "Raw samples and descriptive statistics identify variability; they do not diagnose a route-local cause.",
      "A median, range, or within-budget count cannot make any failed Visual QA receipt acceptable.",
      "Candidate acceptance, package authority, and deployment remain outside this report.",
    ],
  };
}

function writeReport(report, outputPath) {
  const resolved = path.resolve(outputPath);
  fs.mkdirSync(path.dirname(resolved), { recursive: true });
  fs.writeFileSync(resolved, `${JSON.stringify(report, null, 2)}\n`, "utf8");
  return resolved;
}

function main(argv = process.argv.slice(2)) {
  const options = parseCli(argv);
  if (options.help) {
    process.stdout.write(usage());
    return 0;
  }
  const report = buildRepeatabilityReport(options.receipts);
  const output = writeReport(report, options.output);
  process.stdout.write(`DIAGNOSTIC_ONLY\n${output}\n`);
  return 0;
}

module.exports = {
  CANONICAL_ROUTE_MATRIX,
  MAX_RECEIPTS,
  METRIC_RULES,
  MIN_RECEIPTS,
  REPORT_SCHEMA,
  RepeatabilityReportError,
  aggregateMetric,
  buildRepeatabilityReport,
  median,
  parseCli,
  sha256File,
  usage,
  validateReceipt,
  writeReport,
};

if (require.main === module) {
  try {
    process.exitCode = main();
  } catch (error) {
    process.stderr.write(`${error.stack || error.message}\n`);
    process.exitCode = 1;
  }
}

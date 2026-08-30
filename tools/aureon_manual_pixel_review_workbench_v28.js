"use strict";

/*
 * Prepare, but never approve, a source-bound manual pixel-review template.
 *
 * Axe may leave color-contrast nodes incomplete when a rendered background is
 * gradient-, image-, or pseudo-element-dependent.  This workbench makes the
 * complete node set inspectable by a named reviewer.  It deliberately writes
 * every node as `unreviewed`; a human must inspect and amend a copy before the
 * composite release gate can ever pass.
 */

const crypto = require("node:crypto");
const fs = require("node:fs");
const path = require("node:path");

const {
  MANUAL_REVIEW_SCHEMA,
  VISUAL_RECEIPT_SCHEMA,
  collectIncompleteNodes,
} = require("./aureon_visual_release_gate_v28.js");

const RELEASE_ID_PATTERN = /^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$/;
const SHA256_PATTERN = /^[a-f0-9]{64}$/;
const TEMPLATE_BASENAME_PATTERN = /^AUREON_WEBSITE_MANUAL_PIXEL_REVIEW_TEMPLATE_[A-Za-z0-9._-]+\.json$/;

function usage() {
  return [
    "Usage:",
    "  node tools/aureon_manual_pixel_review_workbench_v28.js \\",
    "    --visual docs/audits/AUREON_WEBSITE_VISUAL_QA_<UTC>_V28.json \\",
    "    --release-id <immutable-release-id> \\",
    "    --reviewer <named-technical-reviewer> \\",
    "    --output docs/audits/AUREON_WEBSITE_MANUAL_PIXEL_REVIEW_TEMPLATE_<UTC>_V28.json",
    "",
    "The output is deliberately an all-unreviewed template. It is not a manual",
    "review receipt, cannot pass the composite gate, and must not be relabelled",
    "as a completed review without genuine pixel inspection.",
    "",
  ].join("\n");
}

function canonicalTimestamp(value) {
  if (typeof value !== "string" || !/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$/.test(value)) {
    return false;
  }
  const milliseconds = Date.parse(value);
  return Number.isFinite(milliseconds) && new Date(milliseconds).toISOString() === value;
}

function sha256File(filePath) {
  return crypto.createHash("sha256").update(fs.readFileSync(filePath)).digest("hex");
}

function relativeInsideRepo(repoRoot, candidate, label) {
  const root = path.resolve(repoRoot);
  const resolved = path.resolve(root, candidate);
  const relative = path.relative(root, resolved);
  if (!relative || relative.startsWith("..") || path.isAbsolute(relative)) {
    throw new Error(`${label} must be a file inside the repository`);
  }
  return { absolute: resolved, relative: relative.split(path.sep).join("/") };
}

function readJson(filePath, label) {
  try {
    return JSON.parse(fs.readFileSync(filePath, "utf8"));
  } catch (error) {
    throw new Error(`${label} must be readable UTF-8 JSON: ${error.message}`);
  }
}

function assertVisualReceipt(visual, visualReference) {
  if (visual?.schema !== VISUAL_RECEIPT_SCHEMA) {
    throw new Error(`Visual receipt must use ${VISUAL_RECEIPT_SCHEMA}`);
  }
  if (!canonicalTimestamp(visual.generatedAt)) {
    throw new Error("Visual receipt generatedAt must be a canonical UTC timestamp");
  }
  const before = visual?.sourceBinding?.before?.sha256;
  const after = visual?.sourceBinding?.after?.sha256;
  if (
    visual?.sourceBinding?.stable !== true ||
    !SHA256_PATTERN.test(before || "") ||
    before !== after
  ) {
    throw new Error("Visual receipt must bind one stable SHA-256 website tree");
  }
  if (!visualReference.relative.startsWith("docs/audits/") || !visualReference.relative.endsWith(".json")) {
    throw new Error("Visual receipt must be a JSON receipt inside docs/audits/");
  }
  return before;
}

function buildManualReviewTemplate({
  repoRoot,
  visualPath,
  releaseId,
  reviewer,
  generatedAt = new Date().toISOString(),
}) {
  if (!RELEASE_ID_PATTERN.test(releaseId || "")) {
    throw new Error("--release-id must be an immutable identifier using letters, digits, dots, underscores, or hyphens");
  }
  if (typeof reviewer !== "string" || !reviewer.trim()) {
    throw new Error("--reviewer must identify the named technical reviewer");
  }
  if (!canonicalTimestamp(generatedAt)) {
    throw new Error("Template generatedAt must be a canonical UTC timestamp");
  }
  const visualReference = relativeInsideRepo(repoRoot, visualPath, "--visual");
  if (!fs.existsSync(visualReference.absolute) || !fs.statSync(visualReference.absolute).isFile()) {
    throw new Error(`Visual receipt is missing: ${visualReference.relative}`);
  }
  const visual = readJson(visualReference.absolute, "Visual receipt");
  const websiteTreeSha256 = assertVisualReceipt(visual, visualReference);
  if (Date.parse(generatedAt) < Date.parse(visual.generatedAt)) {
    throw new Error("Template timestamp must not predate the visual receipt");
  }

  const expectedNodes = collectIncompleteNodes(visual);
  const nodeIds = new Set();
  for (const node of expectedNodes) {
    if (nodeIds.has(node.nodeId)) {
      throw new Error(`Visual receipt contains duplicate incomplete-node identity: ${node.nodeId}`);
    }
    nodeIds.add(node.nodeId);
  }
  const reviews = expectedNodes.map((node) => ({
    nodeId: node.nodeId,
    engine: node.engine,
    routeName: node.routeName,
    route: node.route,
    ruleId: node.ruleId,
    impact: node.impact,
    target: node.target,
    failureSummary: node.failureSummary,
    status: "unreviewed",
    reviewedAt: null,
    notes: "",
  }));

  return {
    schema: MANUAL_REVIEW_SCHEMA,
    releaseId,
    generatedAt,
    reviewer: {
      name: reviewer.trim(),
      method: "manual-pixel-inspection",
    },
    visualReceipt: {
      path: visualReference.relative,
      sha256: sha256File(visualReference.absolute),
      generatedAt: visual.generatedAt,
    },
    websiteTreeSha256,
    summary: {
      expectedIncompleteNodes: reviews.length,
      reviewedNodes: 0,
      verifiedPassNodes: 0,
      notApplicableNodes: 0,
      failedNodes: 0,
      unreviewedNodes: reviews.length,
    },
    reviews,
  };
}

function writeTemplate(repoRoot, output, template) {
  const reference = relativeInsideRepo(repoRoot, output, "--output");
  if (!reference.relative.startsWith("docs/audits/")) {
    throw new Error("--output must stay inside docs/audits/");
  }
  if (!TEMPLATE_BASENAME_PATTERN.test(path.basename(reference.relative))) {
    throw new Error("--output must use an AUREON_WEBSITE_MANUAL_PIXEL_REVIEW_TEMPLATE_*.json filename");
  }
  if (fs.existsSync(reference.absolute)) {
    throw new Error(`Refusing to overwrite pixel-review template: ${reference.relative}`);
  }
  fs.mkdirSync(path.dirname(reference.absolute), { recursive: true });
  fs.writeFileSync(reference.absolute, `${JSON.stringify(template, null, 2)}\n`, {
    encoding: "utf8",
    flag: "wx",
  });
  return reference;
}

function parseCli(argv = process.argv.slice(2)) {
  const options = {
    repoRoot: process.cwd(),
    visual: null,
    releaseId: null,
    reviewer: null,
    output: null,
    help: false,
  };
  const takeValue = (argument, index) => {
    const equals = argument.indexOf("=");
    if (equals !== -1) return [argument.slice(equals + 1), index];
    const value = argv[index + 1];
    if (!value || value.startsWith("--")) throw new Error(`${argument} requires a value`);
    return [value, index + 1];
  };
  for (let index = 0; index < argv.length; index += 1) {
    const argument = argv[index];
    if (argument === "--help" || argument === "-h") {
      options.help = true;
      continue;
    }
    if (["--visual", "--release-id", "--reviewer", "--output", "--repo-root"].some((name) => argument === name || argument.startsWith(`${name}=`))) {
      const [value, nextIndex] = takeValue(argument, index);
      if (argument === "--visual" || argument.startsWith("--visual=")) options.visual = value;
      if (argument === "--release-id" || argument.startsWith("--release-id=")) options.releaseId = value;
      if (argument === "--reviewer" || argument.startsWith("--reviewer=")) options.reviewer = value;
      if (argument === "--output" || argument.startsWith("--output=")) options.output = value;
      if (argument === "--repo-root" || argument.startsWith("--repo-root=")) options.repoRoot = path.resolve(value);
      index = nextIndex;
      continue;
    }
    throw new Error(`Unknown argument: ${argument}`);
  }
  if (!options.help) {
    for (const field of ["visual", "releaseId", "reviewer", "output"]) {
      if (!options[field]) throw new Error(`--${field === "releaseId" ? "release-id" : field} is required`);
    }
  }
  return options;
}

function main(argv = process.argv.slice(2)) {
  const options = parseCli(argv);
  if (options.help) {
    process.stdout.write(usage());
    return 0;
  }
  const template = buildManualReviewTemplate({
    repoRoot: options.repoRoot,
    visualPath: options.visual,
    releaseId: options.releaseId,
    reviewer: options.reviewer,
  });
  const output = writeTemplate(options.repoRoot, options.output, template);
  process.stdout.write(
    `${JSON.stringify(
      {
        state: "template-created-not-reviewed",
        output: output.relative,
        sourceTreeSha256: template.websiteTreeSha256,
        expectedIncompleteNodes: template.summary.expectedIncompleteNodes,
        reviewedNodes: 0,
        unreviewedNodes: template.summary.unreviewedNodes,
      },
      null,
      2,
    )}\n`,
  );
  return 0;
}

module.exports = {
  TEMPLATE_BASENAME_PATTERN,
  buildManualReviewTemplate,
  canonicalTimestamp,
  parseCli,
  writeTemplate,
};

if (require.main === module) {
  try {
    process.exitCode = main();
  } catch (error) {
    process.stderr.write(`${error.stack || error.message}\n`);
    process.exitCode = 1;
  }
}

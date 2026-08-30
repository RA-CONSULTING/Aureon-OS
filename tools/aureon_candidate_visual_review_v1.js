"use strict";

/*
 * Capture visual-review evidence for one already-staged V30+ website
 * candidate.  This is deliberately not the canonical V28 release gate: it
 * cannot write website/, package a release, access credentials, or deploy.
 * Canonical V28 audit/manual/composite evidence remains mandatory after an
 * owner-controlled promotion.
 */

const fs = require("node:fs");
const path = require("node:path");

const {
  collectIncompleteNodes,
} = require("./aureon_visual_release_gate_v28.js");
const {
  canonicalJsonSha256,
  parseCli: parseVisualQaCli,
  runVisualQa,
  sha256File,
  validateEditorialSurfaceExpectationBinding,
} = require("./aureon_website_visual_qa_v28.js");

const CANDIDATE_SCHEMA = "aureon.design-candidate.v1";
const CAPTURE_SCHEMA = "aureon.design-candidate-visual-capture.v1";
const MANUAL_TEMPLATE_SCHEMA = "aureon.design-candidate-manual-pixel-review.v1";
const CANDIDATE_ROOT = ["artifacts", "website-candidates"];
const SHA256_PATTERN = /^[a-f0-9]{64}$/i;

function usage() {
  return [
    "Usage:",
    "  node tools/aureon_candidate_visual_review_v1.js \\",
    "    --candidate-receipt artifacts/website-candidates/<run-id>/candidate.v1.json \\",
    "    --reviewer <named-technical-reviewer> [--engines chromium,firefox,webkit]",
    "",
    "Runs the existing strict visual QA against only the staged candidate tree",
    "and writes screenshots, a visual receipt, a non-approved manual-review",
    "template, and a capture receipt beneath that candidate artifact root.",
    "It creates no canonical website change and grants no release, package,",
    "credential, promotion, or deployment authority.",
  ].join("\n");
}

function canonicalRelative(value, label) {
  if (typeof value !== "string" || !value.trim()) {
    throw new Error(`${label} must be a non-empty repository-relative path`);
  }
  const normalized = value.replace(/\\/g, "/").replace(/^\/+/, "");
  const pieces = normalized.split("/");
  if (!pieces.length || pieces.some((part) => !part || part === "." || part === "..")) {
    throw new Error(`${label} is not a safe repository-relative path`);
  }
  return pieces.join("/");
}

function resolveInside(root, relative, label) {
  const normalized = canonicalRelative(relative, label);
  const candidate = path.resolve(root, ...normalized.split("/"));
  const absoluteRoot = path.resolve(root);
  const relativeToRoot = path.relative(absoluteRoot, candidate);
  if (relativeToRoot.startsWith("..") || path.isAbsolute(relativeToRoot)) {
    throw new Error(`${label} escapes the repository`);
  }
  return { absolute: candidate, relative: normalized };
}

function assertUnlinkedPathInside(root, target, label, expectedType) {
  const absoluteRoot = path.resolve(root);
  const absoluteTarget = path.resolve(target);
  const relative = path.relative(absoluteRoot, absoluteTarget);
  if (relative.startsWith("..") || path.isAbsolute(relative)) {
    throw new Error(`${label} escapes the repository`);
  }
  let current = absoluteRoot;
  for (const part of relative.split(path.sep).filter(Boolean)) {
    current = path.join(current, part);
    if (!fs.existsSync(current)) throw new Error(`${label} is missing: ${current}`);
    if (fs.lstatSync(current).isSymbolicLink()) {
      throw new Error(`${label} may not traverse a symbolic link or reparse point.`);
    }
  }
  const stats = fs.lstatSync(absoluteTarget);
  if (
    (expectedType === "file" && !stats.isFile()) ||
    (expectedType === "directory" && !stats.isDirectory())
  ) {
    throw new Error(`${label} is not a regular ${expectedType}.`);
  }
  if (expectedType === "file" && stats.nlink !== 1) {
    throw new Error(`${label} may not be hardlinked.`);
  }
  const realRoot = fs.realpathSync.native(absoluteRoot);
  const realTarget = fs.realpathSync.native(absoluteTarget);
  const realRelative = path.relative(realRoot, realTarget);
  if (realRelative.startsWith("..") || path.isAbsolute(realRelative)) {
    throw new Error(`${label} resolves outside the repository.`);
  }
  return realTarget;
}

function readJson(filePath, label) {
  try {
    const value = JSON.parse(fs.readFileSync(filePath, "utf8"));
    if (!value || Array.isArray(value) || typeof value !== "object") {
      throw new Error("expected one object");
    }
    return value;
  } catch (error) {
    throw new Error(`${label} must be readable UTF-8 JSON: ${error.message}`);
  }
}

function writeNewJson(filePath, value, label) {
  if (fs.existsSync(filePath)) {
    throw new Error(`Refusing to overwrite ${label}: ${filePath}`);
  }
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
  fs.writeFileSync(filePath, `${JSON.stringify(value, null, 2)}\n`, {
    encoding: "utf8",
    flag: "wx",
  });
}

function extractEditorialSurfaceExpectationBinding(receipt) {
  const checks = Array.isArray(receipt?.checks) ? receipt.checks : [];
  const surfaceChecks = checks.filter(
    (item) =>
      item &&
      !Array.isArray(item) &&
      typeof item === "object" &&
      item.id === "trusted-editorial-surface-replay",
  );
  if (surfaceChecks.length !== 1 || surfaceChecks[0].passed !== true) {
    throw new Error(
      "Candidate receipt must contain exactly one passed trusted editorial surface replay check.",
    );
  }
  const evidence = surfaceChecks[0].evidence;
  if (!evidence || Array.isArray(evidence) || typeof evidence !== "object") {
    throw new Error("Trusted editorial surface replay check lacks evidence.");
  }
  const expectations = evidence.expected_surfaces;
  const expectationsSha256 = evidence.expected_surfaces_sha256;
  if (evidence.required === false) {
    if (
      evidence.verification_state !== "not-required-text-only" ||
      !Array.isArray(expectations) ||
      expectations.length !== 0 ||
      expectationsSha256 !== ""
    ) {
      throw new Error(
        "Text-only candidate editorial evidence must bind an empty surface set.",
      );
    }
  } else if (evidence.required === true) {
    if (
      evidence.verification_state !== "verified-local-candidate" ||
      !Array.isArray(expectations) ||
      expectations.length === 0 ||
      !/^[a-f0-9]{64}$/i.test(String(expectationsSha256 || "")) ||
      canonicalJsonSha256(expectations) !== String(expectationsSha256).toUpperCase()
    ) {
      throw new Error(
        "Binary candidate editorial evidence must bind its non-empty verified surface set.",
      );
    }
  } else {
    throw new Error("Trusted editorial surface replay evidence must declare binary necessity.");
  }
  const validated = validateEditorialSurfaceExpectationBinding(
    expectations,
    expectationsSha256,
  );
  return {
    required: evidence.required,
    editorialSurfaceExpectations: validated.expectations,
    editorialSurfaceExpectationsSha256: validated.sha256,
  };
}

function candidateLayout(repoRoot, candidateReceiptPath) {
  const receiptReference = resolveInside(repoRoot, candidateReceiptPath, "--candidate-receipt");
  const receiptRealPath = assertUnlinkedPathInside(
    repoRoot,
    receiptReference.absolute,
    "Candidate receipt",
    "file",
  );
  const receipt = readJson(receiptReference.absolute, "Candidate receipt");
  if (receipt.schema !== CANDIDATE_SCHEMA || receipt.passed !== true || receipt.state !== "validated-local") {
    throw new Error("Candidate receipt must be a locally validated staged candidate.");
  }
  const candidate = receipt.candidate;
  if (!candidate || typeof candidate !== "object") {
    throw new Error("Candidate receipt must declare a candidate layout.");
  }
  const candidateRootReference = resolveInside(repoRoot, candidate.root, "Candidate root");
  const candidateWebsiteReference = resolveInside(repoRoot, candidate.website_path, "Candidate website");
  const candidateRootParts = candidateRootReference.relative.split("/");
  if (
    candidateRootParts.length !== 3 ||
    candidateRootParts[0] !== CANDIDATE_ROOT[0] ||
    candidateRootParts[1] !== CANDIDATE_ROOT[1] ||
    !/^[a-z0-9][a-z0-9._-]{2,80}$/.test(candidateRootParts[2])
  ) {
    throw new Error("Candidate receipt root must be one deterministic staged candidate directory.");
  }
  if (
    candidateWebsiteReference.relative !== `${candidateRootReference.relative}/website` ||
    !fs.existsSync(candidateWebsiteReference.absolute)
  ) {
    throw new Error("Candidate receipt website path must be the staged candidate's website directory.");
  }
  if (receiptReference.relative !== `${candidateRootReference.relative}/candidate.v1.json`) {
    throw new Error("Candidate receipt must use the deterministic candidate.v1.json artifact path.");
  }
  if (!SHA256_PATTERN.test(String(candidate.tree_sha256 || ""))) {
    throw new Error("Candidate receipt must declare its candidate-control tree SHA-256.");
  }
  const candidateRootRealPath = assertUnlinkedPathInside(
    repoRoot,
    candidateRootReference.absolute,
    "Candidate root",
    "directory",
  );
  const candidateWebsiteRealPath = assertUnlinkedPathInside(
    repoRoot,
    candidateWebsiteReference.absolute,
    "Candidate website",
    "directory",
  );
  if (
    path.dirname(candidateWebsiteRealPath) !== candidateRootRealPath ||
    path.dirname(receiptRealPath) !== candidateRootRealPath
  ) {
    throw new Error(
      "Candidate receipt and website must resolve as direct children of the deterministic candidate root.",
    );
  }
  const editorialSurfaceBinding = extractEditorialSurfaceExpectationBinding(receipt);
  return {
    receipt,
    receiptReference,
    candidateRootReference,
    candidateWebsiteReference,
    editorialSurfaceBinding,
  };
}

function prepareCandidateVisualRoot(repoRoot, candidateRootReference) {
  const visualRoot = path.join(candidateRootReference.absolute, "visual-review");
  if (!fs.existsSync(visualRoot)) fs.mkdirSync(visualRoot, { recursive: false });
  const visualRealPath = assertUnlinkedPathInside(
    repoRoot,
    visualRoot,
    "Candidate visual-review root",
    "directory",
  );
  const candidateRealPath = fs.realpathSync.native(candidateRootReference.absolute);
  if (path.dirname(visualRealPath) !== candidateRealPath) {
    throw new Error(
      "Candidate visual-review root must resolve as a direct child of the candidate root.",
    );
  }
  return visualRoot;
}

function buildManualTemplate({ layout, visualPath, visualAbsolute, visual, reviewer, generatedAt }) {
  const nodes = collectIncompleteNodes(visual);
  const reviews = nodes.map((node) => ({
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
    schema: MANUAL_TEMPLATE_SCHEMA,
    generatedAt,
    candidateReceipt: {
      path: layout.receiptReference.relative,
      sha256: sha256File(layout.receiptReference.absolute),
    },
    candidate: {
      root: layout.candidateRootReference.relative,
      websitePath: layout.candidateWebsiteReference.relative,
      controlTreeSha256: layout.receipt.candidate.tree_sha256,
    },
    reviewer: {
      name: reviewer,
      method: "manual-pixel-inspection",
    },
    visualReceipt: {
      path: visualPath,
      sha256: sha256File(visualAbsolute),
      generatedAt: visual.generatedAt,
      sourceTreeSha256: visual.sourceBinding.before.sha256,
    },
    summary: {
      expectedIncompleteNodes: reviews.length,
      reviewedNodes: 0,
      verifiedPassNodes: 0,
      notApplicableNodes: 0,
      failedNodes: 0,
      unreviewedNodes: reviews.length,
    },
    reviews,
    authority: {
      release_eligible: false,
      package_authority: "none",
      deployment_authority: "none",
      canonical_promotion_authority: "owner-controlled",
    },
  };
}

function parseCli(argv = process.argv.slice(2)) {
  const options = {
    repoRoot: path.resolve(__dirname, ".."),
    candidateReceipt: null,
    reviewer: null,
    qaArgs: [],
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
      throw new Error("Candidate visual evidence must be self-hosted; --base-url is not permitted.");
    }
    if (argument === "--candidate-receipt" || argument.startsWith("--candidate-receipt=")) {
      const [value, nextIndex] = takeValue(argument, index);
      options.candidateReceipt = value;
      index = nextIndex;
      continue;
    }
    if (argument === "--reviewer" || argument.startsWith("--reviewer=")) {
      const [value, nextIndex] = takeValue(argument, index);
      options.reviewer = value.trim();
      index = nextIndex;
      continue;
    }
    if (argument === "--repo-root" || argument.startsWith("--repo-root=")) {
      const [value, nextIndex] = takeValue(argument, index);
      options.repoRoot = path.resolve(value);
      index = nextIndex;
      continue;
    }
    if (["--engines", "--routes", "--viewports"].some((name) => argument === name || argument.startsWith(`${name}=`))) {
      const [value, nextIndex] = takeValue(argument, index);
      const name = argument.slice(0, argument.indexOf("=") >= 0 ? argument.indexOf("=") : argument.length);
      options.qaArgs.push(name, value);
      index = nextIndex;
      continue;
    }
    throw new Error(`Unknown argument: ${argument}`);
  }
  if (!options.help) {
    if (!options.candidateReceipt) throw new Error("--candidate-receipt is required");
    if (!options.reviewer) throw new Error("--reviewer must identify the named technical reviewer");
  }
  return options;
}

async function main(argv = process.argv.slice(2)) {
  const options = parseCli(argv);
  if (options.help) {
    process.stdout.write(`${usage()}\n`);
    return 0;
  }
  const layout = candidateLayout(options.repoRoot, options.candidateReceipt);
  const qaOptions = parseVisualQaCli(options.qaArgs);
  const visualRoot = prepareCandidateVisualRoot(
    options.repoRoot,
    layout.candidateRootReference,
  );
  const result = await runVisualQa(qaOptions, {
    sourceRoot: layout.candidateWebsiteReference.absolute,
    outputRoot: visualRoot,
    editorialSurfaceExpectations:
      layout.editorialSurfaceBinding.editorialSurfaceExpectations,
    editorialSurfaceExpectationsSha256:
      layout.editorialSurfaceBinding.editorialSurfaceExpectationsSha256,
  });
  const visualReference = path.relative(options.repoRoot, result.jsonPath).split(path.sep).join("/");
  const visual = result.report;
  const stamp = visual.generatedAt.replace(/[-:.]/g, "");
  const templatePath = path.join(
    visualRoot,
    `AUREON_CANDIDATE_MANUAL_PIXEL_REVIEW_TEMPLATE_${stamp}.json`,
  );
  const template = buildManualTemplate({
    layout,
    visualPath: visualReference,
    visualAbsolute: result.jsonPath,
    visual,
    reviewer: options.reviewer,
    generatedAt: new Date().toISOString(),
  });
  writeNewJson(templatePath, template, "candidate manual pixel-review template");
  const capturePath = path.join(visualRoot, `AUREON_CANDIDATE_VISUAL_CAPTURE_${stamp}.json`);
  const capture = {
    schema: CAPTURE_SCHEMA,
    generatedAt: new Date().toISOString(),
    state: result.report.status === "PASS" ? "captured-local-pass" : "captured-local-fail",
    candidateReceipt: {
      path: layout.receiptReference.relative,
      sha256: sha256File(layout.receiptReference.absolute),
    },
    candidate: {
      root: layout.candidateRootReference.relative,
      websitePath: layout.candidateWebsiteReference.relative,
      controlTreeSha256: layout.receipt.candidate.tree_sha256,
    },
    visualReceipt: {
      path: visualReference,
      sha256: sha256File(result.jsonPath),
      status: result.report.status,
      sourceTreeSha256: result.report.sourceBinding.before.sha256,
      screenshotCount: result.report.screenshotIntegrity.count,
      screenshotsStable: result.report.screenshotIntegrity.pass,
    },
    manualPixelReviewTemplate: {
      path: path.relative(options.repoRoot, templatePath).split(path.sep).join("/"),
      sha256: sha256File(templatePath),
      unreviewedNodeCount: template.summary.unreviewedNodes,
    },
    authority: {
      release_eligible: false,
      package_authority: "none",
      deployment_authority: "none",
      canonical_promotion_authority: "owner-controlled",
    },
  };
  writeNewJson(capturePath, capture, "candidate visual capture receipt");
  process.stdout.write(
    `${JSON.stringify(
      {
        state: capture.state,
        visualReceipt: capture.visualReceipt.path,
        manualPixelReviewTemplate: capture.manualPixelReviewTemplate.path,
        captureReceipt: path.relative(options.repoRoot, capturePath).split(path.sep).join("/"),
        release_eligible: false,
        deployment_authority: "none",
      },
      null,
      2,
    )}\n`,
  );
  return result.exitCode;
}

module.exports = {
  CAPTURE_SCHEMA,
  CANDIDATE_SCHEMA,
  MANUAL_TEMPLATE_SCHEMA,
  candidateLayout,
  extractEditorialSurfaceExpectationBinding,
  parseCli,
  prepareCandidateVisualRoot,
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

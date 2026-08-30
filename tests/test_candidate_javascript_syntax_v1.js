"use strict";

const assert = require("assert");
const fs = require("fs");
const os = require("os");
const path = require("path");

const tool = require("../tools/aureon_candidate_javascript_syntax_v1.js");

let passed = 0;

function test(name, callback) {
  try {
    callback();
    passed += 1;
  } catch (error) {
    error.message = `${name}: ${error.message}`;
    throw error;
  }
}

function write(target, value) {
  fs.mkdirSync(path.dirname(target), { recursive: true });
  fs.writeFileSync(target, value);
}

function fixture() {
  const repo = fs.mkdtempSync(path.join(os.tmpdir(), "aureon-candidate-js-"));
  fs.mkdirSync(path.join(repo, "website"), { recursive: true });
  const root = path.join(
    repo,
    "artifacts",
    "website-candidates",
    "javascript-qa-run",
    "website"
  );
  fs.mkdirSync(root, { recursive: true });
  write(path.join(root, "script.js"), '"use strict";\nconst shared = true;\n');
  write(
    path.join(root, "funding", "funding-status.js"),
    '"use strict";\n(() => { const funding = "bounded"; })();\n'
  );
  write(
    path.join(root, "live", "live.js"),
    '"use strict";\n(() => { const live = "read-only"; })();\n'
  );
  write(path.join(root, "index.html"), "<!doctype html><title>Candidate</title>\n");
  return {
    repo,
    root,
    cleanup() {
      fs.rmSync(repo, { recursive: true, force: true });
    },
  };
}

function boundaryCode(callback) {
  assert.throws(
    callback,
    (error) =>
      error instanceof tool.CandidateJavaScriptBoundaryError &&
      typeof error.code === "string"
  );
}

test("parses exactly the three bound scripts deterministically", () => {
  const item = fixture();
  try {
    const before = tool.snapshotTree(item.root);
    const first = tool.auditCandidateJavaScript(item.root, item.repo);
    const second = tool.auditCandidateJavaScript(item.root, item.repo);
    assert.deepStrictEqual(first, second);
    assert.strictEqual(tool.canonicalJson(first), tool.canonicalJson(second));
    assert.strictEqual(first.schema, tool.SCHEMA);
    assert.strictEqual(first.decision.status, "pass");
    assert.strictEqual(first.bindings.length, 3);
    assert.deepStrictEqual(
      first.bindings.map((binding) => binding.path),
      tool.REQUIRED_PATHS
    );
    assert.strictEqual(first.source.tree_sha256, before.tree_sha256);
    assert.strictEqual(first.source.root.includes(item.repo), false);
    assert.strictEqual(first.authority.release_eligible, false);
    assert.ok(
      first.limitations.includes("v28-composite-visual-release-gate-not-satisfied")
    );
    assert.deepStrictEqual(tool.snapshotTree(item.root), before);
  } finally {
    item.cleanup();
  }
});

test("malformed JavaScript is a hash-only finding and is never executed", () => {
  const item = fixture();
  try {
    const sentinel = path.join(item.repo, "must-not-exist");
    const malformed =
      `require("fs").writeFileSync(${JSON.stringify(sentinel)}, "executed");\n` +
      "function broken( {\n";
    write(path.join(item.root, "script.js"), malformed);
    const receipt = tool.auditCandidateJavaScript(item.root, item.repo);
    assert.strictEqual(receipt.decision.status, "blocked");
    assert.strictEqual(receipt.decision.failure_count, 1);
    assert.strictEqual(receipt.failures[0].code, "javascript-syntax-error");
    assert.strictEqual(receipt.failures[0].path, "script.js");
    assert.strictEqual(fs.existsSync(sentinel), false);
    const output = tool.canonicalJson(receipt);
    assert.strictEqual(output.includes("writeFileSync"), false);
    assert.strictEqual(output.includes(sentinel), false);
    assert.strictEqual(output.includes(item.repo), false);
  } finally {
    item.cleanup();
  }
});

test("reduced-motion reachability remains outside the syntax-only adapter", () => {
  const item = fixture();
  try {
    const sentinel = path.join(item.repo, "dead-branch-must-not-exist");
    write(
      path.join(item.root, "script.js"),
      `if (1 > 2) {\n` +
        `  require("fs").writeFileSync(${JSON.stringify(sentinel)}, "executed");\n` +
        `  if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {}\n` +
        `}\n`
    );
    const receipt = tool.auditCandidateJavaScript(item.root, item.repo);
    assert.strictEqual(receipt.decision.status, "pass");
    assert.strictEqual(receipt.bindings.length, 3);
    assert.strictEqual(fs.existsSync(sentinel), false);
    assert.ok(
      receipt.limitations.includes(
        "syntax-parse-only-javascript-is-not-executed"
      )
    );
  } finally {
    item.cleanup();
  }
});

test("missing required scripts fail the trust boundary", () => {
  const item = fixture();
  try {
    fs.unlinkSync(path.join(item.root, "live", "live.js"));
    boundaryCode(() => tool.auditCandidateJavaScript(item.root, item.repo));
  } finally {
    item.cleanup();
  }
});

test("an extra malformed JavaScript file fails the reviewed tree boundary", () => {
  const item = fixture();
  try {
    write(path.join(item.root, "extra.js"), "function malformed( {\n");
    assert.throws(
      () => tool.auditCandidateJavaScript(item.root, item.repo),
      (error) => error.code === "unreviewed-javascript-tree"
    );
  } finally {
    item.cleanup();
  }
});

test("invalid UTF-8 fails the trust boundary", () => {
  const item = fixture();
  try {
    fs.writeFileSync(path.join(item.root, "script.js"), Buffer.from([0xff, 0xfe]));
    assert.throws(
      () => tool.auditCandidateJavaScript(item.root, item.repo),
      (error) => error.code === "javascript-invalid-utf8"
    );
  } finally {
    item.cleanup();
  }
});

test("hard links fail closed", () => {
  const item = fixture();
  try {
    fs.linkSync(
      path.join(item.root, "script.js"),
      path.join(item.root, "hardlink.js")
    );
    assert.throws(
      () => tool.auditCandidateJavaScript(item.root, item.repo),
      (error) => error.code === "candidate-tree-hardlink"
    );
  } finally {
    item.cleanup();
  }
});

test("symbolic links or junctions fail closed when supported", () => {
  const item = fixture();
  try {
    const link = path.join(item.root, "linked");
    try {
      fs.symlinkSync(path.join(item.root, "funding"), link, "junction");
    } catch (_error) {
      return;
    }
    assert.throws(
      () => tool.auditCandidateJavaScript(item.root, item.repo),
      (error) => error.code === "candidate-tree-link-or-reparse"
    );
  } finally {
    item.cleanup();
  }
});

test("canonical, traversal, UNC, URL and file URL roots are rejected", () => {
  const item = fixture();
  try {
    for (const value of [
      path.join(item.repo, "website"),
      "../website",
      "\\\\server\\share\\website",
      "file:///tmp/website",
      "https://example.test/website",
    ]) {
      boundaryCode(() => tool.auditCandidateJavaScript(value, item.repo));
    }
  } finally {
    item.cleanup();
  }
});

test("nested or work-order staging layouts are rejected", () => {
  const item = fixture();
  try {
    const nested = path.join(
      item.repo,
      "artifacts",
      "website-candidates",
      "run",
      "nested",
      "website"
    );
    fs.mkdirSync(nested, { recursive: true });
    boundaryCode(() => tool.auditCandidateJavaScript(nested, item.repo));
    const workOrder = path.join(
      item.repo,
      "artifacts",
      "website-candidates",
      "work-orders",
      "website"
    );
    fs.mkdirSync(workOrder, { recursive: true });
    boundaryCode(() => tool.auditCandidateJavaScript(workOrder, item.repo));
  } finally {
    item.cleanup();
  }
});

test("CLI grammar accepts only the fixed ordered scripts", () => {
  assert.strictEqual(
    tool.parseCli(["C:\\candidate", ...tool.REQUIRED_PATHS]),
    "C:\\candidate"
  );
  for (const argv of [
    ["C:\\candidate", "script.js"],
    [
      "C:\\candidate",
      "funding/funding-status.js",
      "script.js",
      "live/live.js",
    ],
    ["C:\\candidate", ...tool.REQUIRED_PATHS, "--output", "report.json"],
    ["C:\\candidate", "script.js", "script.js", "live/live.js"],
    ["C:\\candidate", ...tool.REQUIRED_PATHS.slice(0, 2), "../outside.js"],
  ]) {
    assert.throws(
      () => tool.parseCli(argv),
      (error) => error.code === "cli-contract-invalid"
    );
  }
});

test("invalid receipts are deterministic and privacy-minimised", () => {
  const first = tool.invalidReceipt("cli-contract-invalid");
  const second = tool.invalidReceipt("cli-contract-invalid");
  assert.deepStrictEqual(first, second);
  assert.strictEqual(first.decision.status, "invalid");
  assert.strictEqual(first.source.root, "");
  assert.strictEqual(tool.canonicalJson(first).includes("generated_at"), false);
});

test("implementation contains no subprocess, filesystem writer or network client", () => {
  const source = fs.readFileSync(
    path.join(__dirname, "..", "tools", "aureon_candidate_javascript_syntax_v1.js"),
    "utf8"
  );
  for (const forbidden of [
    /require\(["']child_process["']\)/,
    /\b(?:exec|execFile|spawn|fork)Sync?\s*\(/,
    /\bfs\.(?:writeFile|appendFile|createWriteStream|rename|unlink|rm)\w*\s*\(/,
    /\bfetch\s*\(/,
    /require\(["'](?:http|https|net|tls|dgram)["']\)/,
  ]) {
    assert.strictEqual(forbidden.test(source), false, String(forbidden));
  }
});

process.stdout.write(
  `${JSON.stringify({ schema: "aureon.node-test-result.v1", passed })}\n`
);

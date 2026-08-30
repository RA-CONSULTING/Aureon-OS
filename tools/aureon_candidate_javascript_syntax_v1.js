#!/usr/bin/env node
"use strict";

/*
 * Read-only JavaScript syntax evidence for one sealed website candidate.
 *
 * The adapter parses, but never executes, exactly:
 *   script.js
 *   funding/funding-status.js
 *   live/live.js
 *
 * It performs no writes, network access, dynamic imports, or child-process
 * execution.  stdout is one canonical, privacy-minimised JSON line.
 */

const crypto = require("crypto");
const fs = require("fs");
const path = require("path");
const vm = require("vm");
const { TextDecoder } = require("util");

const SCHEMA = "aureon.design-candidate-javascript-syntax.v1";
const REQUIRED_PATHS = Object.freeze([
  "script.js",
  "funding/funding-status.js",
  "live/live.js",
]);
const AUTHORITY = Object.freeze({
  canonical_website_mutation: "none",
  candidate_mutation: "none",
  credential_access: "none",
  deployment_authority: "none",
  package_authority: "none",
  release_eligible: false,
  release_authority: "WebsiteOperator owner gate only",
});
const LIMITATIONS = Object.freeze([
  "syntax-parse-only-javascript-is-not-executed",
  "browser-runtime-behaviour-not-tested",
  "v28-composite-visual-release-gate-not-satisfied",
  "endpoint-tree-stability-is-not-a-continuous-filesystem-sandbox",
]);
const RUN_ID = /^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$/;
const URI = /^[A-Za-z][A-Za-z0-9+.-]*:\/\//;

class CandidateJavaScriptBoundaryError extends Error {
  constructor(code) {
    super(code);
    this.name = "CandidateJavaScriptBoundaryError";
    this.code = code;
  }
}

function stableValue(value) {
  if (Array.isArray(value)) return value.map(stableValue);
  if (value && typeof value === "object") {
    return Object.fromEntries(
      Object.keys(value)
        .sort()
        .map((key) => [key, stableValue(value[key])])
    );
  }
  return value;
}

function canonicalJson(value) {
  return JSON.stringify(stableValue(value));
}

function sha256Bytes(value) {
  return crypto.createHash("sha256").update(value).digest("hex").toUpperCase();
}

function jsonSha256(value) {
  return sha256Bytes(Buffer.from(canonicalJson(value), "utf8"));
}

function isLinkOrReparse(target) {
  let details;
  try {
    details = fs.lstatSync(target);
  } catch (_error) {
    throw new CandidateJavaScriptBoundaryError("filesystem-entry-unreadable");
  }
  return details.isSymbolicLink();
}

function validateCandidateRoot(raw, repositoryRoot) {
  if (typeof raw !== "string" || !raw || raw.includes("\0")) {
    throw new CandidateJavaScriptBoundaryError("candidate-root-invalid");
  }
  if (!path.isAbsolute(raw)) {
    throw new CandidateJavaScriptBoundaryError("candidate-root-not-absolute");
  }
  if (URI.test(raw) || raw.startsWith("\\\\") || raw.startsWith("//")) {
    throw new CandidateJavaScriptBoundaryError("candidate-root-uri-or-unc");
  }
  let root;
  let repo;
  try {
    root = fs.realpathSync.native(raw);
    repo = fs.realpathSync.native(repositoryRoot);
  } catch (_error) {
    throw new CandidateJavaScriptBoundaryError("candidate-root-unresolvable");
  }
  const staging = path.join(repo, "artifacts", "website-candidates");
  const relative = path.relative(staging, root);
  const parts = relative.split(path.sep);
  if (
    !relative ||
    relative.startsWith(`..${path.sep}`) ||
    path.isAbsolute(relative) ||
    parts.length !== 2 ||
    parts[1] !== "website" ||
    parts[0] === "work-orders" ||
    !RUN_ID.test(parts[0])
  ) {
    throw new CandidateJavaScriptBoundaryError("candidate-root-layout-invalid");
  }
  if (root === fs.realpathSync.native(path.join(repo, "website"))) {
    throw new CandidateJavaScriptBoundaryError("canonical-website-root-rejected");
  }
  for (const target of [staging, path.dirname(root), root]) {
    if (isLinkOrReparse(target) || !fs.statSync(target).isDirectory()) {
      throw new CandidateJavaScriptBoundaryError("candidate-root-link-or-reparse");
    }
  }
  return { repo, root, relative: path.relative(repo, root).replaceAll("\\", "/") };
}

function boundedFiles(root) {
  const directories = [root];
  const files = [];
  const realRoot = fs.realpathSync.native(root);
  const foldedPaths = new Map();
  while (directories.length) {
    const directory = directories.pop();
    let entries;
    try {
      entries = fs.readdirSync(directory, { withFileTypes: true }).sort((a, b) =>
        a.name < b.name ? -1 : a.name > b.name ? 1 : 0
      );
    } catch (_error) {
      throw new CandidateJavaScriptBoundaryError("candidate-tree-unreadable");
    }
    const siblings = new Set();
    for (const entry of entries) {
      if (
        entry.name !== entry.name.normalize("NFC") ||
        entry.name.trim() !== entry.name ||
        [...entry.name].some((character) => {
          const code = character.codePointAt(0);
          return code < 32 || code === 127;
        }) ||
        entry.name.includes("\\")
      ) {
        throw new CandidateJavaScriptBoundaryError(
          "candidate-tree-path-name-invalid"
        );
      }
      const foldedName = entry.name.toLowerCase();
      if (siblings.has(foldedName)) {
        throw new CandidateJavaScriptBoundaryError("candidate-tree-casefold-collision");
      }
      siblings.add(foldedName);
      const absolute = path.join(directory, entry.name);
      if (isLinkOrReparse(absolute)) {
        throw new CandidateJavaScriptBoundaryError("candidate-tree-link-or-reparse");
      }
      let real;
      let details;
      try {
        real = fs.realpathSync.native(absolute);
        details = fs.lstatSync(absolute);
      } catch (_error) {
        throw new CandidateJavaScriptBoundaryError("candidate-tree-unreadable");
      }
      const escaped = path.relative(realRoot, real);
      if (escaped.startsWith(`..${path.sep}`) || path.isAbsolute(escaped)) {
        throw new CandidateJavaScriptBoundaryError("candidate-tree-path-escape");
      }
      const relative = path.relative(root, absolute).replaceAll("\\", "/");
      const folded = relative.toLowerCase();
      if (foldedPaths.has(folded) && foldedPaths.get(folded) !== relative) {
        throw new CandidateJavaScriptBoundaryError("candidate-tree-casefold-collision");
      }
      foldedPaths.set(folded, relative);
      if (details.isDirectory()) {
        directories.push(absolute);
      } else if (details.isFile()) {
        if (Number(details.nlink) !== 1) {
          throw new CandidateJavaScriptBoundaryError("candidate-tree-hardlink");
        }
        files.push(absolute);
      } else {
        throw new CandidateJavaScriptBoundaryError("candidate-tree-special-file");
      }
    }
  }
  return files.sort((left, right) => {
    const a = path.relative(root, left).replaceAll("\\", "/");
    const b = path.relative(root, right).replaceAll("\\", "/");
    return a < b ? -1 : a > b ? 1 : 0;
  });
}

function snapshotTree(root) {
  const rows = boundedFiles(root).map((absolute) => {
    const before = fs.statSync(absolute);
    const bytes = fs.readFileSync(absolute);
    const after = fs.statSync(absolute);
    if (
      before.size !== after.size ||
      before.mtimeMs !== after.mtimeMs ||
      before.ino !== after.ino
    ) {
      throw new CandidateJavaScriptBoundaryError("candidate-tree-mutated-during-read");
    }
    return {
      bytes: Number(after.size),
      path: path.relative(root, absolute).replaceAll("\\", "/"),
      sha256: sha256Bytes(bytes),
    };
  });
  return {
    tree_sha256: jsonSha256(rows),
    file_count: rows.length,
    total_bytes: rows.reduce((sum, item) => sum + item.bytes, 0),
    files: rows,
  };
}

function decodeUtf8(bytes) {
  if (bytes.length >= 3 && bytes[0] === 0xef && bytes[1] === 0xbb && bytes[2] === 0xbf) {
    throw new CandidateJavaScriptBoundaryError("javascript-invalid-utf8");
  }
  if (bytes.includes(0)) {
    throw new CandidateJavaScriptBoundaryError("javascript-invalid-utf8");
  }
  try {
    return new TextDecoder("utf-8", { fatal: true }).decode(bytes);
  } catch (_error) {
    throw new CandidateJavaScriptBoundaryError("javascript-invalid-utf8");
  }
}

function syntaxLine(error, relative) {
  if (Number.isInteger(error.lineNumber) && error.lineNumber > 0) return error.lineNumber;
  const escaped = relative.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const match = new RegExp(`${escaped}:(\\d+)`).exec(String(error.stack || ""));
  return match ? Number(match[1]) : 0;
}

function auditCandidateJavaScript(candidateRoot, repositoryRoot = path.resolve(__dirname, "..")) {
  const validated = validateCandidateRoot(candidateRoot, repositoryRoot);
  const before = snapshotTree(validated.root);
  const observedScripts = before.files
    .map((item) => item.path)
    .filter((relative) => relative.toLowerCase().endsWith(".js"))
    .sort();
  const reviewedScripts = [...REQUIRED_PATHS].sort();
  if (canonicalJson(observedScripts) !== canonicalJson(reviewedScripts)) {
    throw new CandidateJavaScriptBoundaryError("unreviewed-javascript-tree");
  }
  const manifest = new Map(before.files.map((item) => [item.path, item]));
  const bindings = [];
  const failures = [];
  for (const relative of REQUIRED_PATHS) {
    const row = manifest.get(relative);
    if (!row) {
      throw new CandidateJavaScriptBoundaryError("required-javascript-file-missing");
    }
    const absolute = path.join(validated.root, ...relative.split("/"));
    if (isLinkOrReparse(absolute) || !fs.statSync(absolute).isFile()) {
      throw new CandidateJavaScriptBoundaryError("required-javascript-file-invalid");
    }
    const bytes = fs.readFileSync(absolute);
    if (sha256Bytes(bytes) !== row.sha256 || bytes.length !== row.bytes) {
      throw new CandidateJavaScriptBoundaryError("javascript-file-mutated-during-read");
    }
    const source = decodeUtf8(bytes);
    bindings.push({ path: relative, sha256: row.sha256, bytes: row.bytes });
    try {
      new vm.Script(source, { filename: relative, displayErrors: false });
    } catch (error) {
      const line = syntaxLine(error, relative);
      const code = "javascript-syntax-error";
      failures.push({
        code,
        path: relative,
        line,
        evidence_hash: jsonSha256({
          code,
          error_type: String(error && error.name ? error.name : "SyntaxError"),
          line,
          path: relative,
        }),
      });
    }
  }
  const after = snapshotTree(validated.root);
  if (canonicalJson(before) !== canonicalJson(after)) {
    throw new CandidateJavaScriptBoundaryError("candidate-tree-mutated-during-audit");
  }
  failures.sort((left, right) =>
    left.path !== right.path
      ? left.path < right.path
        ? -1
        : 1
      : left.line - right.line
  );
  return {
    schema: SCHEMA,
    source: {
      root: validated.relative,
      tree_sha256: before.tree_sha256,
      file_count: before.file_count,
      total_bytes: before.total_bytes,
    },
    bindings,
    failures,
    decision: {
      status: failures.length ? "blocked" : "pass",
      failure_count: failures.length,
      failure_set_sha256: jsonSha256(failures),
    },
    limitations: LIMITATIONS,
    authority: AUTHORITY,
  };
}

function invalidReceipt(code) {
  const failures = [
    {
      code,
      path: ".",
      line: 0,
      evidence_hash: jsonSha256({ code }),
    },
  ];
  return {
    schema: SCHEMA,
    source: { root: "", tree_sha256: "", file_count: 0, total_bytes: 0 },
    bindings: [],
    failures,
    decision: {
      status: "invalid",
      failure_count: 1,
      failure_set_sha256: jsonSha256(failures),
    },
    limitations: LIMITATIONS,
    authority: AUTHORITY,
  };
}

function parseCli(argv) {
  if (
    argv.length !== 4 ||
    argv[1] !== REQUIRED_PATHS[0] ||
    argv[2] !== REQUIRED_PATHS[1] ||
    argv[3] !== REQUIRED_PATHS[2]
  ) {
    throw new CandidateJavaScriptBoundaryError("cli-contract-invalid");
  }
  return argv[0];
}

function main(argv = process.argv.slice(2)) {
  let receipt;
  try {
    if (process.env.NODE_OPTIONS) {
      throw new CandidateJavaScriptBoundaryError("node-options-environment-rejected");
    }
    const root = parseCli(argv);
    receipt = auditCandidateJavaScript(root);
  } catch (error) {
    const code =
      error instanceof CandidateJavaScriptBoundaryError
        ? error.code
        : "unexpected-static-parser-boundary";
    receipt = invalidReceipt(code);
    process.stdout.write(`${canonicalJson(receipt)}\n`);
    return 3;
  }
  process.stdout.write(`${canonicalJson(receipt)}\n`);
  return receipt.decision.status === "pass" ? 0 : 2;
}

module.exports = Object.freeze({
  AUTHORITY,
  LIMITATIONS,
  REQUIRED_PATHS,
  SCHEMA,
  CandidateJavaScriptBoundaryError,
  auditCandidateJavaScript,
  canonicalJson,
  invalidReceipt,
  jsonSha256,
  parseCli,
  snapshotTree,
  validateCandidateRoot,
});

if (require.main === module) {
  process.exitCode = main();
}

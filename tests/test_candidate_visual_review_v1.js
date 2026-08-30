"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const test = require("node:test");

const {
  CANDIDATE_SCHEMA,
  candidateLayout,
  extractEditorialSurfaceExpectationBinding,
  parseCli,
  prepareCandidateVisualRoot,
} = require("../tools/aureon_candidate_visual_review_v1.js");
const {
  canonicalJsonSha256,
} = require("../tools/aureon_website_visual_qa_v28.js");

function fixture(t) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "aureon-candidate-visual-"));
  t.after(() => fs.rmSync(root, { recursive: true, force: true }));
  const candidateRoot = path.join(root, "artifacts", "website-candidates", "fixture-review");
  fs.mkdirSync(path.join(candidateRoot, "website"), { recursive: true });
  fs.writeFileSync(path.join(candidateRoot, "website", "index.html"), "<!doctype html>\n", "utf8");
  const receiptPath = path.join(candidateRoot, "candidate.v1.json");
  fs.writeFileSync(
    receiptPath,
    `${JSON.stringify({
      schema: CANDIDATE_SCHEMA,
      state: "validated-local",
      passed: true,
      candidate: {
        root: "artifacts/website-candidates/fixture-review",
        website_path: "artifacts/website-candidates/fixture-review/website",
        tree_sha256: "A".repeat(64),
      },
      checks: [
        {
          id: "trusted-editorial-surface-replay",
          passed: true,
          evidence: {
            required: false,
            verification_state: "not-required-text-only",
            expected_surfaces: [],
            expected_surfaces_sha256: "",
          },
        },
      ],
    })}\n`,
    "utf8",
  );
  return { root, receiptPath };
}

test("candidate visual runner accepts only deterministic staged receipt layout", (t) => {
  const { root, receiptPath } = fixture(t);
  const layout = candidateLayout(root, path.relative(root, receiptPath));
  assert.equal(layout.candidateRootReference.relative, "artifacts/website-candidates/fixture-review");
  assert.equal(
    layout.candidateWebsiteReference.relative,
    "artifacts/website-candidates/fixture-review/website",
  );
  assert.deepEqual(layout.editorialSurfaceBinding, {
    required: false,
    editorialSurfaceExpectations: [],
    editorialSurfaceExpectationsSha256: "",
  });
});

test("candidate visual runner refuses external targets and base-url substitution", () => {
  assert.throws(
    () => parseCli(["--candidate-receipt", "candidate.v1.json", "--reviewer", "Reviewer", "--base-url", "https://example.test"]),
    /self-hosted/,
  );
  assert.throws(
    () => parseCli(["--candidate-receipt", "candidate.v1.json", "--reviewer", "Reviewer", "--website-root", "website"]),
    /Unknown argument/,
  );
});

test("candidate visual runner rejects a hardlinked candidate receipt", (t) => {
  const { root, receiptPath } = fixture(t);
  const secondName = path.join(root, "receipt-hardlink.json");
  fs.linkSync(receiptPath, secondName);
  assert.throws(
    () => candidateLayout(root, path.relative(root, receiptPath)),
    /hardlinked/,
  );
});

test("candidate visual runner rejects a linked candidate website", (t) => {
  const { root, receiptPath } = fixture(t);
  const website = path.join(
    root,
    "artifacts",
    "website-candidates",
    "fixture-review",
    "website",
  );
  const external = path.join(root, "external-website");
  fs.mkdirSync(external);
  fs.writeFileSync(path.join(external, "index.html"), "<!doctype html>\n", "utf8");
  fs.rmSync(website, { recursive: true });
  try {
    fs.symlinkSync(external, website, process.platform === "win32" ? "junction" : "dir");
  } catch (error) {
    if (["EPERM", "EACCES", "ENOSYS"].includes(error.code)) {
      t.skip(`Directory links are unavailable: ${error.code}`);
      return;
    }
    throw error;
  }
  assert.throws(
    () => candidateLayout(root, path.relative(root, receiptPath)),
    /symbolic link|reparse point/,
  );
});

test("candidate visual runner rejects a linked visual-review output root", (t) => {
  const { root, receiptPath } = fixture(t);
  const layout = candidateLayout(root, path.relative(root, receiptPath));
  const external = path.join(root, "external-visual-review");
  fs.mkdirSync(external);
  const visualRoot = path.join(layout.candidateRootReference.absolute, "visual-review");
  try {
    fs.symlinkSync(
      external,
      visualRoot,
      process.platform === "win32" ? "junction" : "dir",
    );
  } catch (error) {
    if (["EPERM", "EACCES", "ENOSYS"].includes(error.code)) {
      t.skip(`Directory links are unavailable: ${error.code}`);
      return;
    }
    throw error;
  }
  assert.throws(
    () => prepareCandidateVisualRoot(root, layout.candidateRootReference),
    /symbolic link|reparse point/,
  );
});

function binaryExpectation() {
  return {
    asset_id: "substack-ai-evidence",
    route_scope: "/",
    destination_path: "website/index.html",
    surface_id: "home-ai-evidence-question",
    public_post_url: "https://garyleckey.substack.com/p/exact-evidence-question",
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
    alt: "Exact editorial alt text.",
    caption: "Exact editorial caption.",
    credit: "Exact editorial credit.",
    route_asset_capsule_sha256: "C".repeat(64),
    expected_binding_sha256: "D".repeat(64),
    observation_sha256: "E".repeat(64),
    surface_binding_sha256: "F".repeat(64),
  };
}

test("candidate visual runner extracts one exact passed binary surface replay", () => {
  const expectations = [binaryExpectation()];
  const binding = extractEditorialSurfaceExpectationBinding({
    checks: [
      {
        id: "trusted-editorial-surface-replay",
        passed: true,
        evidence: {
          required: true,
          verification_state: "verified-local-candidate",
          expected_surfaces: expectations,
          expected_surfaces_sha256: canonicalJsonSha256(expectations),
        },
      },
    ],
  });
  assert.equal(binding.required, true);
  assert.deepEqual(binding.editorialSurfaceExpectations, expectations);
  assert.equal(
    binding.editorialSurfaceExpectationsSha256,
    canonicalJsonSha256(expectations),
  );
});

test("candidate visual runner rejects absent, duplicate, failed, or tampered replay evidence", () => {
  assert.throws(
    () => extractEditorialSurfaceExpectationBinding({ checks: [] }),
    /exactly one passed/,
  );
  const textCheck = {
    id: "trusted-editorial-surface-replay",
    passed: true,
    evidence: {
      required: false,
      verification_state: "not-required-text-only",
      expected_surfaces: [],
      expected_surfaces_sha256: "",
    },
  };
  assert.throws(
    () =>
      extractEditorialSurfaceExpectationBinding({
        checks: [textCheck, textCheck],
      }),
    /exactly one passed/,
  );
  assert.throws(
    () =>
      extractEditorialSurfaceExpectationBinding({
        checks: [{ ...textCheck, passed: false }],
      }),
    /exactly one passed/,
  );
  assert.throws(
    () =>
      extractEditorialSurfaceExpectationBinding({
        checks: [
          {
            id: "trusted-editorial-surface-replay",
            passed: true,
            evidence: {
              required: true,
              verification_state: "verified-local-candidate",
              expected_surfaces: [binaryExpectation()],
              expected_surfaces_sha256: "C".repeat(64),
            },
          },
        ],
      }),
    /bind its non-empty verified surface set/,
  );
});

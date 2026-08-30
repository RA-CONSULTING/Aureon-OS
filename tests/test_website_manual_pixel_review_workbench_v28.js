"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const test = require("node:test");

const {
  buildManualReviewTemplate,
  parseCli,
  writeTemplate,
} = require("../tools/aureon_manual_pixel_review_workbench_v28.js");
const {
  VISUAL_RECEIPT_SCHEMA,
} = require("../tools/aureon_visual_release_gate_v28.js");

function writeVisual(repoRoot) {
  const directory = path.join(repoRoot, "docs", "audits");
  fs.mkdirSync(directory, { recursive: true });
  const visual = {
    schema: VISUAL_RECEIPT_SCHEMA,
    generatedAt: "2026-07-26T21:15:11.743Z",
    sourceBinding: {
      before: { sha256: "a".repeat(64) },
      after: { sha256: "a".repeat(64) },
      stable: true,
    },
    engines: [
      {
        engine: "chromium",
        accessibility: [
          {
            routeName: "home",
            route: "/",
            axe: {
              incomplete: [
                {
                  id: "color-contrast",
                  impact: "serious",
                  nodes: [
                    {
                      target: [".proof-card"],
                      failureSummary: "Background cannot be determined.",
                    },
                  ],
                },
              ],
            },
          },
        ],
      },
    ],
  };
  const relative = "docs/audits/AUREON_WEBSITE_VISUAL_QA_20260726T211511743Z_V28.json";
  fs.writeFileSync(path.join(repoRoot, relative), `${JSON.stringify(visual, null, 2)}\n`);
  return relative;
}

test("workbench produces an all-unreviewed, source-bound template", () => {
  const repoRoot = fs.mkdtempSync(path.join(os.tmpdir(), "aureon-pixel-workbench-"));
  try {
    const visual = writeVisual(repoRoot);
    const template = buildManualReviewTemplate({
      repoRoot,
      visualPath: visual,
      releaseId: "v29-3-candidate",
      reviewer: "Technical reviewer",
      generatedAt: "2026-07-26T21:30:00.000Z",
    });

    assert.equal(template.summary.expectedIncompleteNodes, 1);
    assert.equal(template.summary.reviewedNodes, 0);
    assert.equal(template.summary.unreviewedNodes, 1);
    assert.equal(template.reviews[0].status, "unreviewed");
    assert.equal(template.reviews[0].reviewedAt, null);
    assert.equal(template.reviews[0].notes, "");
    assert.equal(template.visualReceipt.path, visual);
    assert.equal(template.websiteTreeSha256, "a".repeat(64));
  } finally {
    fs.rmSync(repoRoot, { recursive: true, force: true });
  }
});

test("workbench refuses unsafe or completed-review-shaped output names", () => {
  const repoRoot = fs.mkdtempSync(path.join(os.tmpdir(), "aureon-pixel-output-"));
  try {
    const template = { schema: "fixture" };
    assert.throws(
      () => writeTemplate(repoRoot, "docs/audits/AUREON_WEBSITE_MANUAL_PIXEL_REVIEW_20260726T220000Z_V28.json", template),
      /TEMPLATE/,
    );
    assert.throws(
      () => writeTemplate(repoRoot, "../outside.json", template),
      /inside the repository/,
    );
    const output = writeTemplate(
      repoRoot,
      "docs/audits/AUREON_WEBSITE_MANUAL_PIXEL_REVIEW_TEMPLATE_20260726T220000Z_V28.json",
      template,
    );
    assert.equal(output.relative.startsWith("docs/audits/"), true);
    assert.throws(() => writeTemplate(repoRoot, output.relative, template), /Refusing to overwrite/);
  } finally {
    fs.rmSync(repoRoot, { recursive: true, force: true });
  }
});

test("workbench CLI requires every source-bound review input", () => {
  assert.throws(() => parseCli([]), /--visual is required/);
  const options = parseCli([
    "--visual=docs/audits/visual.json",
    "--release-id=v29-3-candidate",
    "--reviewer=Technical reviewer",
    "--output=docs/audits/AUREON_WEBSITE_MANUAL_PIXEL_REVIEW_TEMPLATE_20260726T220000Z_V28.json",
  ]);
  assert.equal(options.releaseId, "v29-3-candidate");
  assert.equal(options.reviewer, "Technical reviewer");
});

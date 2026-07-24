/**
 * Live-data flow — proves the shell actually surfaces REAL backend data.
 *
 * The shell-smoke spec asserts the app survives with NO backend (honest empty
 * states). This spec is the complement: with the operator's `/api/*` surface
 * mocked to realistic fixtures, the Overview must render those live values — and
 * with the backend gone, it must fall back to the honest "gateway offline" copy
 * plus the app-wide offline banner. Together they pin the whole data path
 * (proxy → fetch → render) and guarantee no fabrication either way.
 */

import { test, expect, type Page } from "@playwright/test";

const STATUS = {
  status: "healthy",
  domains_reachable: 38,
  domains_total: 38,
  product_domains: {
    trading: { status: "healthy", reachable: 6, total: 6 },
    research: { status: "healthy", reachable: 3, total: 3 },
  },
  note: "test fixture",
};

const AUTOMATION = {
  index_pct: 42.5,
  label: "Emerging",
  dimensions: {
    connectivity: { pct: 51.2, weight: 1, detail: "x" },
    integration: { pct: 33.0, weight: 1, detail: "x" },
  },
  journey: [{ ts: 1, index_pct: 40 }, { ts: 2, index_pct: 42.5 }],
  truth_status: "real_derived",
};

const ORGANISM = {
  available: true,
  connectome: { nodes: 1282, baton_linked: 101, touched: 15, woven: 5, coverage_pct: 1.17 },
};

const PULSE = {
  ok: true,
  status: "healthy",
  providers: [{ name: "a" }, { name: "b" }],
  switchboard: { enabled: 6, total: 15, armed: 1 },
  organism: {
    ...ORGANISM,
    unification: { blended: { coherence_gamma: 0.536, available: true } },
  },
};

async function mockLiveBackend(page: Page) {
  await page.route("**/api/status", (r) => r.fulfill({ json: STATUS }));
  await page.route("**/api/automation", (r) => r.fulfill({ json: AUTOMATION }));
  await page.route("**/api/organism", (r) => r.fulfill({ json: ORGANISM }));
  await page.route("**/api/pulse", (r) => r.fulfill({ json: PULSE }));
  await page.route("**/api/billing/status", (r) =>
    r.fulfill({ json: { configured: true, metering: { sink: "memory", flushed: 0, pending: 0 } } }),
  );
}

test("Overview renders REAL backend values when the operator is live", async ({ page }) => {
  await mockLiveBackend(page);
  await page.goto("/", { waitUntil: "domcontentloaded" });

  // the real automation index flows through to the headline metric
  await expect(page.getByText("42.5%")).toBeVisible({ timeout: 15_000 });
  await expect(page.getByText("Emerging")).toBeVisible();

  // the real platform-health status renders (not the "gateway offline" fallback)
  await expect(page.getByText("healthy").first()).toBeVisible();
  await expect(page.getByText(/Gateway offline/i)).toHaveCount(0);

  // backend is live → the app-wide offline banner must NOT appear
  await expect(page.getByText(/Operator backend offline/i)).toHaveCount(0);

  // the top-bar LiveVitals strip surfaces real /api/pulse numbers
  const vitals = page.getByLabel("live operator vitals");
  await expect(vitals).toContainText("providers");
  await expect(vitals).toContainText("6/15");     // switchboard enabled/total
  await expect(vitals).toContainText("1.2%");     // organism coverage_pct 1.17 -> 1.2%
});

test("Overview degrades honestly (no fabrication) when the backend is down", async ({ page }) => {
  // every backend call fails at the transport layer — the gateway is unreachable
  await page.route("**/api/**", (r) => r.abort());
  await page.goto("/", { waitUntil: "domcontentloaded" });

  // honest empty copy instead of numbers
  await expect(page.getByText(/Gateway offline/i).first()).toBeVisible({ timeout: 15_000 });
  // and the explicit app-wide offline banner
  await expect(page.getByText(/Operator backend offline/i)).toBeVisible();
});

test("War Room surfaces REAL HNC coherence from the operator pulse", async ({ page }) => {
  await mockLiveBackend(page);
  await page.goto("/trading/war-room", { waitUntil: "domcontentloaded" });

  // coherence_gamma 0.536 -> "HNC coherence 53.6%" badge, sourced from /api/pulse
  await expect(page.getByText(/HNC coherence 53\.6%/i)).toBeVisible({ timeout: 15_000 });
});

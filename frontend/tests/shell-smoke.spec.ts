/**
 * Shell smoke — the unified shell renders honestly with NO backend.
 *
 * The dev server has no operator/gateway behind it, so these assertions are
 * deliberately backend-independent: every shell route must mount its chrome
 * (sidebar), must NOT hit the per-route error boundary (a real crash), and must
 * never scroll the body horizontally. `live:true` pages are expected to show an
 * empty / "gateway offline" state — that is honest, not a failure — so we only
 * assert the shell survived, not that live data arrived.
 */

import { test, expect, type Page } from "@playwright/test";

// A representative slice of the 24 shell routes: the new/honest surfaces plus a
// heavy trading dashboard (WarRoom) and the billing page.
const ROUTES = [
  { path: "/", label: "Overview" },
  { path: "/ops/connections", label: "Connections" },
  { path: "/cognition/metacognition", label: "Metacognition" },
  { path: "/cognition/providers", label: "Providers" },
  { path: "/platform/billing", label: "Billing & Support" },
  { path: "/trading/war-room", label: "War Room" },
];

async function noHorizontalScroll(page: Page) {
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
  );
  // allow a 2px rounding tolerance
  expect(overflow, "body must not scroll horizontally").toBeLessThanOrEqual(2);
}

for (const route of ROUTES) {
  test(`shell route ${route.path} mounts without crashing`, async ({ page }) => {
    await page.goto(route.path, { waitUntil: "domcontentloaded" });

    // The shell chrome (sidebar) is always present — the app mounted. The
    // Overview nav link is in the sidebar on every route.
    await expect(page.getByRole("link", { name: "Overview" }).first()).toBeVisible({ timeout: 15_000 });

    // The per-route error boundary must NOT have fired (that would mean the
    // dashboard threw). Its copy is "<name> failed to render".
    await expect(page.getByText(/failed to render/i)).toHaveCount(0);

    await noHorizontalScroll(page);
  });
}

test("sidebar navigation switches routes", async ({ page }) => {
  await page.goto("/", { waitUntil: "domcontentloaded" });
  // Click a stable nav entry and confirm the URL changed to its route.
  await page.getByRole("link", { name: /Connections/i }).first().click();
  await expect(page).toHaveURL(/\/ops\/connections/);
  await expect(page.getByText(/failed to render/i)).toHaveCount(0);
});

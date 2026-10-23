import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./tests",
  timeout: 30_000,
  expect: { timeout: 10_000 },
  use: {
    baseURL: "http://127.0.0.1:8081",
    trace: "retain-on-failure",
  },
  webServer: {
    // The package script named dev stays quarantined: package.json routes
    // it through `unavailable` (exit 2) so a script name cannot start a
    // venue or a preview. The shell specs need a static Vite server only.
    command: "npx vite --host 127.0.0.1 --port 8081",
    url: "http://127.0.0.1:8081",
    reuseExistingServer: true,
    timeout: 120_000,
  },
  projects: [
    {
      name: "chromium",
      use: {
        ...devices["Desktop Chrome"],
        // Portable browser resolution: CI installs chromium via the Playwright
        // action; a sandboxed/pinned environment can point at its own build with
        // PW_CHROMIUM_PATH (e.g. /opt/pw-browsers/chromium-1194/chrome-linux/chrome).
        launchOptions: process.env.PW_CHROMIUM_PATH
          ? { executablePath: process.env.PW_CHROMIUM_PATH }
          : {},
      },
    },
  ],
});

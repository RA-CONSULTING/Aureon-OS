import { expect, test } from "@playwright/test";

test("unified console opens as a categorized operations dashboard", async ({ page }) => {
  await page.goto("/", { waitUntil: "domcontentloaded" });

  await expect(page.getByRole("heading", { name: "Aureon Unified Autonomous Console" })).toBeVisible();
  await expect(page.getByTestId("operator-briefing")).toBeVisible();
  await expect(page.getByText("Operator Brief")).toBeVisible();
  await expect(page.getByTestId("data-freshness-panel")).toBeVisible();
  await expect(page.getByText("Data Freshness")).toBeVisible();
  await expect(page.getByText(/runtime 2\.5s/)).toBeVisible();
  await expect(page.getByTestId("dashboard-content-overview")).toBeVisible();
  await expect(page.getByRole("tab", { name: /Overview/ })).toHaveAttribute("data-state", "active");
  await expect(page.getByRole("heading", { name: "Organism Pulse" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Runtime Mirror" })).toBeVisible();
  await expect(page.getByText("Human Coding Cockpit")).not.toBeVisible();

  await page.getByTestId("dashboard-tab-inventory").click();
  await expect(page).toHaveURL(/#inventory$/);
  await expect(page.getByText("Work Order Filters")).toBeVisible();
  await expect(page.getByText("Source Surface Filters")).toBeVisible();

  await page.getByRole("button", { name: "Blocked" }).click();
  await expect(page.getByText("Frontend Evolution Queue")).toBeVisible();
});

test("coding cockpit exposes the capability forge quality lane", async ({ page }) => {
  await page.goto("/", { waitUntil: "domcontentloaded" });
  await page.getByTestId("dashboard-tab-coding").click();

  await expect(page.getByText("Aureon Coding Organism")).toBeVisible();
  await expect(page.getByText("Human Coding Cockpit")).toBeVisible();
  await expect(page.getByText("Autonomous Coding Capability Gates", { exact: true })).toBeVisible();
  await expect(page.getByText("Autonomous Self-Run Loop", { exact: true })).toBeVisible();
  await expect(page.getByText("Autonomous Job Executor", { exact: true })).toBeVisible();
  await expect(page.getByText("Queue depth", { exact: true }).first()).toBeVisible();
  await expect(page.getByText("Active Job", { exact: true })).toBeVisible();
  await expect(page.getByText("Proof Checklist", { exact: true })).toBeVisible();
  await expect(page.getByText("Evolution Queue 584 Certification", { exact: true })).toBeVisible();
  await expect(page.getByText(/processed \d+\/\d+/).first()).toBeVisible();
  await expect(page.getByText("Outcome Buckets", { exact: true })).toBeVisible();
  await expect(page.getByText("Live Queue Runtime Patches", { exact: true })).toBeVisible();
  await expect(page.getByText("Moved from queue", { exact: true })).toBeVisible();
  await expect(page.getByText("Active Runtime Patches", { exact: true })).toBeVisible();
  await expect(page.getByText("Queue Movement", { exact: true })).toBeVisible();
  await expect(page.getByText("Materialized Repo Code", { exact: true })).toBeVisible();
  await expect(page.getByText(/code materialized \d+/).first()).toBeVisible();
  await expect(page.getByText("Local Capability Forge", { exact: true })).toBeVisible();
  await expect(page.getByText("Quality Checks")).toBeVisible();
  await expect(page.getByText("Client Approval Controls")).toBeVisible();
  await expect(page.getByText("Capability Stress Audit", { exact: true })).toBeVisible();
  await expect(page.getByText("Complex Build Stress Certification", { exact: true })).toBeVisible();
  await expect(page.getByText(/cases \d+\/\d+/).first()).toBeVisible();
  await expect(page.getByText("Aureon Self-Fix SWOT", { exact: true })).toBeVisible();
  await expect(page.getByText(/audit (autonomous_safe|pending|passed|failed|waiting)/).first()).toBeVisible();
  await expect(page.getByText("Selected Repairs", { exact: true })).toBeVisible();
  await expect(page.getByText("Ollama Cognitive Handshake")).toBeVisible();
  await expect(page.getByText("Ollama reachable")).toBeVisible();
  await expect(page.getByText("Handshake Proof")).toBeVisible();
  await expect(page.getByText("Metacognitive Creative Process Guardian")).toBeVisible();
  await expect(page.getByText(/HNC\/Auris (ready|held|waiting)/).first()).toBeVisible();
  await expect(page.getByText("Scope Of Works", { exact: true })).toBeVisible();
  await expect(page.getByText("Work Journal: Prompt To Finished Files", { exact: true })).toBeVisible();
});

test("trading cockpit shows the Capital GOLD intelligence company", async ({ page }) => {
  await page.goto("/#trading", { waitUntil: "domcontentloaded" });

  await expect(page.getByTestId("dashboard-content-trading")).toBeVisible();
  await expect(page.getByTestId("gold-capital-intelligence-console")).toBeVisible();
  await expect(page.getByText("Gold Capital Intelligence Company", { exact: true })).toBeVisible();
  await expect(page.getByText("target GOLD", { exact: true })).toBeVisible();
  await expect(page.getByText(/live trade blocked|live trade allowed/).first()).toBeVisible();
  await expect(page.getByText("Price Energy Thesis", { exact: true })).toBeVisible();
  await expect(page.getByText("3p Profit Floor Gate", { exact: true })).toBeVisible();
  await expect(page.getByText("minimum move", { exact: true })).toBeVisible();
  await expect(page.getByText("Blocking Truth", { exact: true })).toBeVisible();
  await expect(page.getByText("GOLD Live Stream Command Deck", { exact: true })).toBeVisible();
  await expect(page.getByText("Capital Data Profile", { exact: true })).toBeVisible();
  await expect(page.getByText("Live Stream Channels", { exact: true })).toBeVisible();
  await expect(page.getByText("Chart Analytics And HNC Feedback", { exact: true })).toBeVisible();
  await expect(page.getByText("What Happens Next", { exact: true })).toBeVisible();
  await expect(page.getByText("GOLD Margin Signal Action Loop", { exact: true })).toBeVisible();
  await expect(page.getByText("Signal To Action Pipeline", { exact: true })).toBeVisible();
  await expect(page.getByText("Margin Intent", { exact: true })).toBeVisible();
  await expect(page.getByText("HNC/Auris Node Feedback", { exact: true })).toBeVisible();
  await expect(page.getByText("GOLD Process Logic Flow Guard", { exact: true })).toBeVisible();
  await expect(page.getByText("Gate Sequence", { exact: true })).toBeVisible();
  await expect(page.getByText("Authority Leak Checks", { exact: true })).toBeVisible();
  await expect(page.getByText("Flow Violations", { exact: true })).toBeVisible();
  await expect(page.getByText("GOLD Data Sensemaking Router", { exact: true })).toBeVisible();
  await expect(page.getByText("Source Routes", { exact: true })).toBeVisible();
  await expect(page.getByText("Meaning Packets", { exact: true })).toBeVisible();
  await expect(page.getByText("Driver Placement", { exact: true })).toBeVisible();
  await expect(page.getByText("Verified Real Data Gate", { exact: true })).toBeVisible();
  await expect(page.getByText("Only fresh verified market/runtime evidence can unlock action.").or(page.getByText(/No fake/))).toBeVisible();
  await expect(page.getByText("GOLD Fresh Signal Validation", { exact: true })).toBeVisible();
  await expect(page.getByText("Ticker Source Mesh", { exact: true })).toBeVisible();
  await expect(page.getByText("Projection Intervals", { exact: true })).toBeVisible();
  await expect(page.getByText("HNC/Auris Action Gate", { exact: true })).toBeVisible();
  await expect(page.getByText("Fresh-Proof Blockers", { exact: true })).toBeVisible();
  await expect(page.getByText("GOLD Evolving Projection Path", { exact: true })).toBeVisible();
  await expect(page.getByText("Second-To-Month Horizon Ladder", { exact: true })).toBeVisible();
  await expect(page.getByText("Projection Path Blockers", { exact: true })).toBeVisible();
  await expect(page.getByText("GOLD Dynamic Market Edge Stream", { exact: true })).toBeVisible();
  await expect(page.getByText("Streaming Edge Lanes", { exact: true })).toBeVisible();
  await expect(page.getByText("Edge Trigger Map", { exact: true })).toBeVisible();
  await expect(page.getByText("Edge Blockers", { exact: true })).toBeVisible();
  await expect(page.getByText("GOLD HNC History Future Bridge", { exact: true })).toBeVisible();
  await expect(page.getByText("Historical Analogs", { exact: true })).toBeVisible();
  await expect(page.getByText("Future Windows", { exact: true }).first()).toBeVisible();
  await expect(page.getByText("History Future Blockers", { exact: true })).toBeVisible();
  await expect(page.getByText("GOLD Creative Dream Hypothesis Engine", { exact: true })).toBeVisible();
  await expect(page.getByText("Dream Bank", { exact: true })).toBeVisible();
  await expect(page.getByText("Validation Queue", { exact: true })).toBeVisible();
  await expect(page.getByText("Dream Blockers", { exact: true })).toBeVisible();
  await expect(page.getByText("GOLD Probability Projection Forecast", { exact: true })).toBeVisible();
  await expect(page.getByText("Truth Discipline", { exact: true })).toBeVisible();
  await expect(page.getByText("Probability Forecast Claims", { exact: true })).toBeVisible();
  await expect(page.getByText("Contradiction Checks", { exact: true })).toBeVisible();
  await expect(page.getByText("HNC/Auris Quantum Probability Route", { exact: true })).toBeVisible();
  await expect(page.getByText("Auris Nodes", { exact: true })).toBeVisible();
  await expect(page.getByText("Lambda", { exact: true })).toBeVisible();
  await expect(page.getByText("Quantum", { exact: true })).toBeVisible();
  await expect(page.getByText("Probability", { exact: true })).toBeVisible();
  await expect(page.getByText("HFT Speed And Validated Predictions Gate", { exact: true })).toBeVisible();
  await expect(page.getByText("validated predictions required", { exact: true })).toBeVisible();
  await expect(page.getByText("Fresh Predictions", { exact: true })).toBeVisible();
  await expect(page.getByText("Correct Validated", { exact: true })).toBeVisible();
  await expect(page.getByText("Gold Historical Stress Test", { exact: true })).toBeVisible();
  await expect(page.getByText("Validated Rows", { exact: true })).toBeVisible();
  await expect(page.getByText("Historical Hit Rate", { exact: true })).toBeVisible();
  await expect(page.getByText("Stress Scenarios", { exact: true }).first()).toBeVisible();
  await expect(page.getByText("Gold Action Command", { exact: true })).toBeVisible();
  await expect(page.getByText("who", { exact: true }).first()).toBeVisible();
  await expect(page.getByText("what", { exact: true }).first()).toBeVisible();
  await expect(page.getByText("when", { exact: true }).first()).toBeVisible();
  await expect(page.getByText("act", { exact: true }).first()).toBeVisible();
  await expect(page.getByText("three p floor", { exact: true }).first()).toBeVisible();
  await expect(page.getByText("Gold Shadow Trading Focus", { exact: true })).toBeVisible();
  await expect(page.getByText("gold and gold energy only", { exact: true })).toBeVisible();
  await expect(page.getByText("Excluded Generic Shadows", { exact: true })).toBeVisible();
  await expect(page.getByText("Oil and energy stress lane", { exact: true })).toBeVisible();
  await expect(page.getByText("Capital GOLD snapshot", { exact: true })).toBeVisible();
  await expect(page.getByText("Gold Intelligence Coverage", { exact: true })).toBeVisible();
  await expect(page.getByText("Gold Market Universe", { exact: true })).toBeVisible();
  await expect(page.getByText("Gold Swarm Intelligence", { exact: true })).toBeVisible();
  await expect(page.getByText("Crypto Liquidity Rotation Reader", { exact: true })).toBeVisible();
  await expect(page.getByText("Geopolitical Sentiment Reader", { exact: true })).toBeVisible();
  await expect(page.getByText("Gold Agent Coding Support", { exact: true })).toBeVisible();
  await expect(page.getByText("Agent Chat Lanes", { exact: true })).toBeVisible();
  await expect(page.getByText("Agent Tool Lanes", { exact: true })).toBeVisible();
  await expect(page.getByText("Gold Monitor Targets", { exact: true })).toBeVisible();
  await expect(page.getByText("Coding organism job lane", { exact: true })).toBeVisible();
  await expect(page.getByText("Gold Priority Workbench", { exact: true })).toBeVisible();
  await expect(page.getByText("Forecast Artifacts", { exact: true })).toBeVisible();
  await expect(page.getByText("Open forecast dashboard", { exact: true })).toBeVisible();
  await expect(page.getByText("refresh capital gold quote and ohlc", { exact: true })).toBeVisible();
  await expect(page.getByText("Historical Signal Lab", { exact: true })).toBeVisible();
  await expect(page.getByText("Cross-Asset Lead/Lag", { exact: true }).first()).toBeVisible();
  await expect(page.getByText("Order-Book Pressure Replay", { exact: true }).first()).toBeVisible();
  await expect(page.getByText("Chart/OHLC Replay", { exact: true }).first()).toBeVisible();
  await expect(page.getByText("Gold Exchange Optimization", { exact: true })).toBeVisible();
  await expect(page.getByText("Related Asset Watchlists", { exact: true })).toBeVisible();
  await expect(page.getByText("Dynamic Monitor Contracts", { exact: true })).toBeVisible();
  await expect(page.getByText("primary gold target venue", { exact: true }).first()).toBeVisible();
  await expect(page.getByText("Gold Margin Trader Unity", { exact: true })).toBeVisible();
  await expect(page.getByText("Unified Margin Brain", { exact: true }).first()).toBeVisible();
  await expect(page.getByText("Dynamic Margin Sizer", { exact: true }).first()).toBeVisible();
  await expect(page.getByText("shadow before live", { exact: true }).first()).toBeVisible();
  await expect(page.getByText("Margin Surface Map", { exact: true })).toBeVisible();
  await expect(page.getByText("Cross-Market Gold Drivers", { exact: true })).toBeVisible();
  await expect(page.getByText("Crypto liquidity and safe-haven rotation", { exact: true })).toBeVisible();
  await expect(page.getByText("Stocks, indices, ETFs, and VIX", { exact: true })).toBeVisible();
  await expect(page.getByText("Geopolitics, news, and sentiment", { exact: true })).toBeVisible();
  await expect(page.getByText("Tool Activation Plan", { exact: true })).toBeVisible();
});

test("phi chat submits through the cockpit and displays response quality", async ({ page }) => {
  await page.route("http://127.0.0.1:13002/api/phi-bridge/chat", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        ok: true,
        status: "phi_bridge_chat_replied",
        generated_at: new Date().toISOString(),
        reply:
          "I can see the coding cockpit as the live client-job lane.\n\nStatus: coding_organism_ready; scope: ready_for_client; route clean; tests passed/ready; handover looks ready; blocking snags: 0.",
        reply_source: "aureon_operator_compiler",
        model: "aureon-operator-compiler-v1",
        latency_ms: 1,
        response_quality: {
          score: 1,
          passed: true,
          compiler_applied: false,
          snags: [],
        },
        dynamic_prompt_filter: {
          filter_mode: "clear_operator_fast",
          lane: "chat",
          task_family: "system_health",
          source_packets: [],
          hnc_auris_report: { auris_voice_filter: { accepted: true } },
          handover_ready: true,
        },
      }),
    });
  });

  await page.goto("/", { waitUntil: "domcontentloaded" });
  await page.getByTestId("dashboard-tab-coding").click();
  await page.getByTestId("phi-chat-input").fill("What can you see in the coding cockpit right now?");
  await page.getByTestId("phi-chat-submit").click();

  await expect(page.getByText("I can see the coding cockpit as the live client-job lane.").first()).toBeVisible();
  await expect(page.getByText("quality 100%")).toBeVisible();
  await expect(page.getByText("operator compiled")).not.toBeVisible();
});

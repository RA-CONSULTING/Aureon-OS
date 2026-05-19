#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const webRoot = path.resolve(__dirname, "..");
const repoRoot = path.resolve(webRoot, "..", "..", "..");

function parseArgs(argv) {
  const parsed = {
    mode: "plan",
    model: "aureon-architect",
    responseStyle: "safe",
    swarmRoute: "direct",
    context: [],
    task: "",
  };
  const rest = [];
  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index];
    if (arg === "--mode") parsed.mode = argv[++index] || parsed.mode;
    else if (arg === "--model") parsed.model = argv[++index] || parsed.model;
    else if (arg === "--response-style") parsed.responseStyle = argv[++index] || parsed.responseStyle;
    else if (arg === "--swarm-route") parsed.swarmRoute = argv[++index] || parsed.swarmRoute;
    else if (arg === "--context") parsed.context.push(argv[++index] || "");
    else rest.push(arg);
  }
  parsed.task = rest.join(" ").trim();
  return parsed;
}

function resolveContext(reference) {
  const value = String(reference || "").trim();
  if (!value) return null;
  if (value.startsWith("@gary/")) {
    const candidate = path.resolve(repoRoot, value.slice("@gary/".length));
    return candidate.startsWith(repoRoot) ? candidate : null;
  }
  const candidate = path.resolve(webRoot, value);
  return candidate.startsWith(webRoot) ? candidate : null;
}

function summarizeContext(contextRefs) {
  const rows = [];
  for (const ref of contextRefs.slice(0, 12)) {
    const resolved = resolveContext(ref);
    if (!resolved || !fs.existsSync(resolved) || !fs.statSync(resolved).isFile()) {
      rows.push({ ref, status: "missing" });
      continue;
    }
    const text = fs.readFileSync(resolved, "utf8").slice(0, 1200);
    rows.push({
      ref,
      status: "present",
      bytes: fs.statSync(resolved).size,
      hint: text.split(/\r?\n/).slice(0, 2).join(" ").slice(0, 180),
    });
  }
  return rows;
}

function main() {
  const parsed = parseArgs(process.argv.slice(2));
  if (!parsed.task) {
    console.error("Missing task text.");
    process.exit(2);
  }
  const contextRows = summarizeContext(parsed.context);
  const safeExecutionNote = [
    "This local CLI planner does not place trades, reveal credentials, deploy cloud resources, or bypass MURGE terminal/sandbox guards.",
    "Use the reviewed Aureon runtime/executor for live trading paths and the guarded terminal for local commands.",
  ].join(" ");
  const output = [
    `# Aureon Local ${parsed.mode === "plan" ? "Plan" : "Guarded Request"}`,
    "",
    `Model: ${parsed.model}`,
    `Swarm route: ${parsed.swarmRoute}`,
    `Response style: ${parsed.responseStyle}`,
    "",
    "## Goal",
    parsed.task,
    "",
    "## Unity Wiring",
    "- Check Aureon supervisor status at /api/aureon/supervisor.",
    "- Keep Flameborn UI as the operator face for chat, capability status, classroom observers, terminal guard state, and MURGE activation state.",
    "- Route organism events through ThoughtBus/Mycelium artifacts when runtime producers emit them.",
    "- Leave live broker mutation to the existing reviewed Aureon executor/runtime gates.",
    "",
    "## Suggested Next Steps",
    "1. Refresh the supervisor and capability cards.",
    "2. Inspect blockers surfaced by the UI before enabling any guarded local action.",
    "3. Use the terminal or sandbox only when their MURGE activation gates report enabled and local-only.",
    "4. Verify generated artifacts and tests before treating a new bridge as trusted.",
    "",
    "## Context Evidence",
    ...contextRows.map((row) => `- ${row.ref}: ${row.status}${row.bytes ? ` (${row.bytes} bytes)` : ""}${row.hint ? ` - ${row.hint}` : ""}`),
    "",
    "## Boundary",
    safeExecutionNote,
  ].join("\n");
  process.stdout.write(`${output}\n`);
}

main();

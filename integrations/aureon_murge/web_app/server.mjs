import http from "node:http";
import fs from "node:fs";
import path from "node:path";
import { spawn } from "node:child_process";
import { randomUUID } from "node:crypto";
import { fileURLToPath } from "node:url";
import Docker from "dockerode";
import pty from "node-pty";
import { WebSocketServer } from "ws";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

function loadEnvFile(envPath) {
  if (!fs.existsSync(envPath)) return;

  const lines = fs.readFileSync(envPath, "utf8").split(/\r?\n/);
  for (const line of lines) {
    const match = line.match(/^(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)=(.*)$/);
    if (!match || process.env[match[1]]) continue;
    let value = match[2].trim().replace(/^["']|["']$/g, "");
    value = value.replace(/\$([A-Za-z_][A-Za-z0-9_]*)/g, (_, name) => process.env[name] || "");
    process.env[match[1]] = value;
  }
}

loadEnvFile(path.join(__dirname, ".env"));
loadEnvFile(path.join(process.env.HOME || "", ".config/gemini/env"));

const LOCAL_HOME = process.env.HOME || process.env.USERPROFILE || process.cwd();
const DEFAULT_AUREON_ROOT = path.resolve(__dirname, "..", "..", "..");
const DEFAULT_AUREON_PHI_BASE_URL = "http://127.0.0.1:13002";
const DEFAULT_AUREON_TERMINAL_STATE_URL = "http://127.0.0.1:8791/api/terminal-state";
const DEFAULT_AUREON_FLIGHT_TEST_URL = "http://127.0.0.1:8791/api/flight-test";
const DEFAULT_AUREON_REBOOT_ADVICE_URL = "http://127.0.0.1:8791/api/reboot-advice";

const PORT = process.env.PORT || 4173;
const HOST = process.env.HOST || "127.0.0.1";
const OPENROUTER_API_KEY = process.env.OPENROUTER_API_KEY || "";
const OPENAI_API_KEY = process.env.OPENAI_API_KEY || "";
const GEMINI_API_KEY = process.env.GEMINI_API_KEY || process.env.GOOGLE_API_KEY || "";
const XAI_API_KEY = process.env.XAI_API_KEY || "";
const XAI_ALLOW_PAID = String(process.env.XAI_ALLOW_PAID || "false").toLowerCase() === "true";
const HF_TOKEN = process.env.HF_TOKEN || process.env.HUGGINGFACE_API_KEY || "";
const AUREON_API_BASE_URL = String(
  process.env.AUREON_API_BASE_URL || process.env.AUREON_PHI_BASE_URL || DEFAULT_AUREON_PHI_BASE_URL,
).replace(/\/+$/, "");
const AUREON_API_KEY = process.env.AUREON_API_KEY || "";
const AUREON_CHAT_PATH = process.env.AUREON_CHAT_PATH || "/api/phi-bridge/chat";
const AUREON_TERMINAL_STATE_URL = process.env.AUREON_TERMINAL_STATE_URL || DEFAULT_AUREON_TERMINAL_STATE_URL;
const AUREON_FLIGHT_TEST_URL = process.env.AUREON_FLIGHT_TEST_URL || DEFAULT_AUREON_FLIGHT_TEST_URL;
const AUREON_REBOOT_ADVICE_URL = process.env.AUREON_REBOOT_ADVICE_URL || DEFAULT_AUREON_REBOOT_ADVICE_URL;
const AUREON_PHI_STATUS_URL = process.env.AUREON_PHI_STATUS_URL || `${AUREON_API_BASE_URL}/api/phi-bridge/status`;
const AUREON_CHAT_TIMEOUT_MS = Math.max(3000, Number(process.env.AUREON_CHAT_TIMEOUT_MS || 18000));
const AUREON_VAULT_PATH = process.env.AUREON_VAULT_PATH || path.join(__dirname, "logs", "aureon-vault");
const GARY_AUREON_ROOT = process.env.GARY_AUREON_ROOT || DEFAULT_AUREON_ROOT || path.join(LOCAL_HOME, "aureon-trading");
const MURGE_HOST_TERMINAL_GATE = String(process.env.MURGE_HOST_TERMINAL_ENABLED || "false").toLowerCase();
const LOCAL_TERMINAL_ENABLED = ["1", "true", "yes", "on", "enabled"].includes(MURGE_HOST_TERMINAL_GATE)
  && String(process.env.LOCAL_TERMINAL_ENABLED || "true").toLowerCase() !== "false";
const LOCAL_TERMINAL_CWD = process.env.LOCAL_TERMINAL_CWD || __dirname;
const TERMINAL_ALLOW_REMOTE = String(process.env.TERMINAL_ALLOW_REMOTE || "false").toLowerCase() === "true";
const TERMINAL_TRUSTED_ORIGINS = String(process.env.TERMINAL_TRUSTED_ORIGINS || "")
  .split(",")
  .map((value) => value.trim())
  .filter(Boolean);
const MURGE_SANDBOX_GATE = String(process.env.MURGE_SANDBOX_ENABLED || "false").toLowerCase();
const SANDBOX_TERMINAL_ENABLED = ["1", "true", "yes", "on", "enabled"].includes(MURGE_SANDBOX_GATE)
  && String(process.env.SANDBOX_TERMINAL_ENABLED || "true").toLowerCase() !== "false";
const PROVIDER_API_ENABLED = ["1", "true", "yes", "on", "enabled"].includes(
  String(process.env.MURGE_PROVIDER_API_ENABLED || "false").toLowerCase()
);
const CLOUDFLARE_ENABLED = ["1", "true", "yes", "on", "enabled"].includes(
  String(process.env.MURGE_CLOUDFLARE_ENABLED || "false").toLowerCase()
);
const SANDBOX_IMAGE = process.env.SANDBOX_IMAGE || "flameborn-runtime:24.04";
const SANDBOX_WORKSPACE_ROOT = process.env.SANDBOX_WORKSPACE_ROOT || path.join(__dirname, "logs", "sandbox-workspaces");
const SANDBOX_LOG_DIR = process.env.SANDBOX_LOG_DIR || path.join(__dirname, "logs", "sandbox-sessions");
const SANDBOX_MEMORY_BYTES = Number(process.env.SANDBOX_MEMORY_BYTES || 1024 * 1024 * 1024);
const SANDBOX_NANO_CPUS = Number(process.env.SANDBOX_NANO_CPUS || 1_000_000_000);
const SANDBOX_COMMAND_TIMEOUT_MS = Number(process.env.SANDBOX_COMMAND_TIMEOUT_MS || 120_000);
const LOCAL_AUREON_CLI_ENABLED = String(process.env.LOCAL_AUREON_CLI_ENABLED || "true").toLowerCase() !== "false";
const LOCAL_AUREON_CLI_SCRIPT = path.join(__dirname, "scripts", "aureon_cli.mjs");
const WORLD_DATA_BRIDGE_SCRIPT = path.join(__dirname, "scripts", "world_data_bridge.py");
const DEFAULT_LOCAL_AUREON_CONTEXTS = [
  "package.json",
  "server.mjs",
  "script.js",
  "index.html",
  "style.css",
  "workers/index.mjs",
  "scripts/aureon_cli.mjs",
  "@gary/SYSTEM_OVERVIEW.md",
  "@gary/aureon/vault/voice/whole_knowledge_voice.py",
  "@gary/aureon/autonomous/aureon_coding_agent_skill_base.py",
  "@gary/aureon/core/goal_execution_engine.py",
];
const AUREON_SYSTEM_FILES = [
  {
    key: "wholeKnowledgeVoice",
    label: "Whole Knowledge Voice",
    relativePath: "aureon/vault/voice/whole_knowledge_voice.py",
    purpose: "human-readable voice artifacts from vault and runtime evidence",
  },
  {
    key: "codingSkillBase",
    label: "Coding Agent Skill Base",
    relativePath: "aureon/autonomous/aureon_coding_agent_skill_base.py",
    purpose: "repo capability map, coder roles, and learning/work-order evidence",
  },
  {
    key: "goalExecutionEngine",
    label: "Goal Execution Engine",
    relativePath: "aureon/core/goal_execution_engine.py",
    purpose: "multi-step goal decomposition, execution, and validation loop",
  },
  {
    key: "repoSelfRepair",
    label: "Repo Self Repair",
    relativePath: "aureon/autonomous/aureon_repo_self_repair.py",
    purpose: "repair planning and validation for repository tasks",
  },
  {
    key: "unifiedUiBuilder",
    label: "Unified UI Builder",
    relativePath: "aureon/autonomous/aureon_unified_ui_builder.py",
    purpose: "generated console and UI evolution path",
  },
  {
    key: "repoExplorerService",
    label: "Repo Explorer Service",
    relativePath: "aureon/autonomous/aureon_repo_explorer_service.py",
    purpose: "README-listed read-only repo search and file inspection surface",
  },
  {
    key: "localTaskQueue",
    label: "Local Task Queue",
    relativePath: "aureon/autonomous/aureon_local_task_queue.py",
    purpose: "README-listed operator and agent task queue for visible local goals",
  },
  {
    key: "voiceCommandBridge",
    label: "Voice Command Bridge",
    relativePath: "aureon/autonomous/aureon_voice_command_bridge.py",
    purpose: "README-listed bridge from text or speech intents into task, code, repo, and desktop queues",
  },
  {
    key: "safeCodeControl",
    label: "Safe Code Control",
    relativePath: "aureon/autonomous/aureon_safe_code_control.py",
    purpose: "README-listed code proposal queue with review-first behavior",
  },
  {
    key: "queenCodeBridge",
    label: "Queen Code Bridge",
    relativePath: "aureon/autonomous/aureon_queen_code_bridge.py",
    purpose: "README-listed bridge from Queen/ThoughtBus code events into safe code proposals",
  },
  {
    key: "mindThoughtActionHub",
    label: "Mind Thought Action Hub",
    relativePath: "aureon/autonomous/aureon_mind_thought_action_hub.py",
    purpose: "README-listed thought and action state surface for cognition/agent routing",
  },
  {
    key: "llmAdapter",
    label: "LLM Adapter",
    relativePath: "aureon/inhouse_ai/llm_adapter.py",
    purpose: "README-listed local LLM and AureonBrain fallback abstraction",
  },
  {
    key: "skillExecutorBridge",
    label: "Skill Executor Bridge",
    relativePath: "aureon/vault/voice/skill_executor_bridge.py",
    purpose: "README-listed skill execution artifact bridge for validated capabilities",
  },
];
const OPENROUTER_FALLBACK_MODELS = [
  "openrouter/free",
  "google/gemma-4-31b-it:free",
  "google/gemma-4-26b-a4b-it:free",
  "meta-llama/llama-3.1-8b-instruct:free",
  "mistralai/mistral-7b-instruct:free",
];
const HF_FREE_MODELS = [
  "Qwen/Qwen2.5-7B-Instruct",
  "HuggingFaceH4/zephyr-7b-beta",
  "microsoft/Phi-3-mini-4k-instruct",
];
const FREE_MODE_PROVIDERS = new Set(["gemini", "openrouter", "aureon"]);
const CLASSROOM_MEMORY_FILE = path.join(__dirname, "logs", "classroom-memory.json");
const OBSERVATION_DEPTH_LIMITS = {
  shallow: 900,
  standard: 1800,
  deep: 3200,
};

const docker = new Docker({ socketPath: process.env.DOCKER_SOCKET || "/var/run/docker.sock" });
const sandboxSessions = new Map();

const mimeTypes = {
  ".html": "text/html; charset=utf-8",
  ".js": "application/javascript; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".svg": "image/svg+xml",
};

function securityHeaders(extra = {}) {
  return {
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
    "Cross-Origin-Opener-Policy": "same-origin",
    ...extra,
  };
}

function sendJson(res, code, payload) {
  res.writeHead(code, securityHeaders({ "Content-Type": "application/json; charset=utf-8" }));
  res.end(JSON.stringify(payload));
}

async function fetchJsonWithTimeout(url, timeoutMs = 2500) {
  const startedAt = Date.now();
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(url, { signal: controller.signal });
    const text = await response.text();
    let data = null;
    try {
      data = text ? JSON.parse(text) : null;
    } catch {
      data = { raw: text.slice(0, 2000) };
    }
    return {
      ok: response.ok,
      statusCode: response.status,
      url,
      data,
      roundTripMs: Date.now() - startedAt,
    };
  } catch (error) {
    return {
      ok: false,
      statusCode: null,
      url,
      data: null,
      error: error?.name === "AbortError" ? `timeout after ${timeoutMs}ms` : error?.message || String(error),
      roundTripMs: Date.now() - startedAt,
    };
  } finally {
    clearTimeout(timer);
  }
}

function normalizeArray(value) {
  if (Array.isArray(value)) return value.filter((item) => item !== null && item !== undefined);
  if (value && typeof value === "object") return Object.values(value).filter((item) => item !== null && item !== undefined);
  if (value === null || value === undefined || value === "") return [];
  return [value];
}

function safeBoolean(value) {
  return value === true || value === "true" || value === 1 || value === "1";
}

class EventBus {
  constructor() {
    this.listeners = new Map();
  }

  subscribe(eventName, listener) {
    const listeners = this.listeners.get(eventName) || [];
    listeners.push(listener);
    this.listeners.set(eventName, listeners);
  }

  publish(eventName, payload) {
    const listeners = this.listeners.get(eventName) || [];
    for (const listener of listeners) {
      Promise.resolve(listener(payload)).catch(() => {});
    }
  }
}

const contextBus = new EventBus();
let classroomMemory = loadClassroomMemory();

contextBus.subscribe("conversation.mirrored", (event) => {
  classroomMemory.events.push({
    id: event.id,
    sessionId: event.sessionId,
    createdAt: event.createdAt,
    provider: event.conversation?.provider,
    model: event.conversation?.model,
    depth: event.depth,
  });
  classroomMemory.events = classroomMemory.events.slice(-200);
  persistClassroomMemory();
});

function loadClassroomMemory() {
  try {
    if (!fs.existsSync(CLASSROOM_MEMORY_FILE)) return emptyClassroomMemory();
    return { ...emptyClassroomMemory(), ...JSON.parse(fs.readFileSync(CLASSROOM_MEMORY_FILE, "utf8")) };
  } catch {
    return emptyClassroomMemory();
  }
}

function emptyClassroomMemory() {
  return {
    events: [],
    reflections: [],
    summaries: [],
    patterns: [],
    inconsistencies: [],
    workflows: [],
    analytics: {
      mirroredEvents: 0,
      observerRuns: 0,
      estimatedTokens: 0,
      lastUpdated: null,
    },
  };
}

function persistClassroomMemory() {
  fs.mkdirSync(path.dirname(CLASSROOM_MEMORY_FILE), { recursive: true });
  fs.writeFileSync(CLASSROOM_MEMORY_FILE, JSON.stringify(classroomMemory, null, 2));
}

function readJsonBody(req, res, maxBytes = 1_000_000) {
  return new Promise((resolve, reject) => {
    let body = "";
    let aborted = false;

    req.on("aborted", () => {
      aborted = true;
      reject(new Error("Request aborted."));
    });
    req.on("error", reject);
    req.on("data", (chunk) => {
      body += chunk;
      if (body.length > maxBytes && !aborted) {
        aborted = true;
        req.destroy();
        reject(new Error("Payload jest za duży."));
      }
    });
    req.on("end", () => {
      if (aborted) return;
      try {
        resolve(JSON.parse(body || "{}"));
      } catch {
        reject(new Error("Nieprawidłowy JSON."));
      }
    });
  });
}

function runProcessCapture(command, args, options = {}) {
  return new Promise((resolve, reject) => {
    const child = spawn(command, args, {
      cwd: options.cwd || __dirname,
      env: options.env || process.env,
      stdio: ["ignore", "pipe", "pipe"],
    });

    let stdout = "";
    let stderr = "";
    const timeoutMs = Number(options.timeoutMs || 60000);
    const timer = setTimeout(() => {
      child.kill("SIGTERM");
      reject(new Error(`CLI timeout after ${timeoutMs} ms`));
    }, timeoutMs);

    child.stdout.on("data", (chunk) => {
      stdout += chunk.toString("utf8");
    });
    child.stderr.on("data", (chunk) => {
      stderr += chunk.toString("utf8");
    });
    child.on("error", (error) => {
      clearTimeout(timer);
      reject(error);
    });
    child.on("close", (code) => {
      clearTimeout(timer);
      resolve({ code, stdout, stderr });
    });
  });
}

function runShellCapture(command, options = {}) {
  return new Promise((resolve, reject) => {
    const shell = hostShellForCommand(command);
    const child = spawn(shell.command, shell.args, {
      cwd: options.cwd || __dirname,
      env: options.env || process.env,
      stdio: ["ignore", "pipe", "pipe"],
    });

    let stdout = "";
    let stderr = "";
    let truncated = false;
    const maxBytes = Number(options.maxBytes || 80_000);
    const startedAt = Date.now();
    const timeoutMs = Number(options.timeoutMs || 30_000);
    const timer = setTimeout(() => {
      child.kill("SIGTERM");
      reject(new Error(`Terminal timeout after ${timeoutMs} ms`));
    }, timeoutMs);
    const collect = (current, chunk) => {
      if (current.length >= maxBytes) {
        truncated = true;
        return current;
      }
      const next = current + chunk.toString("utf8");
      if (next.length > maxBytes) {
        truncated = true;
        return `${next.slice(0, maxBytes)}\n[output truncated]`;
      }
      return next;
    };

    child.stdout.on("data", (chunk) => {
      stdout = collect(stdout, chunk);
    });
    child.stderr.on("data", (chunk) => {
      stderr = collect(stderr, chunk);
    });
    child.on("error", (error) => {
      clearTimeout(timer);
      reject(error);
    });
    child.on("close", (code) => {
      clearTimeout(timer);
      resolve({
        code,
        stdout,
        stderr,
        truncated,
        durationMs: Date.now() - startedAt,
      });
    });
  });
}

function hostShellForCommand(command) {
  if (process.platform === "win32") {
    const configured = process.env.MURGE_WINDOWS_SHELL || process.env.ComSpec || "powershell.exe";
    const shellName = path.basename(configured).toLowerCase();
    if (shellName.includes("powershell") || shellName === "pwsh.exe" || shellName === "pwsh") {
      return {
        command: configured,
        args: ["-NoLogo", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", command],
      };
    }
    return { command: configured, args: ["/d", "/s", "/c", command] };
  }
  const configured = process.env.SHELL || "/bin/bash";
  return { command: configured, args: ["-lc", command] };
}

function isLocalRequest(req) {
  const address = req.socket?.remoteAddress || "";
  return address === "127.0.0.1" || address === "::1" || address === "::ffff:127.0.0.1";
}

function allowTerminalRequest(req) {
  return TERMINAL_ALLOW_REMOTE || isLocalRequest(req);
}

function isTrustedTerminalOrigin(req) {
  const origin = req.headers.origin;
  if (!origin) return true;
  try {
    const parsed = new URL(origin);
    const normalized = parsed.origin;
    if (TERMINAL_TRUSTED_ORIGINS.includes(normalized)) return true;
    if (TERMINAL_ALLOW_REMOTE && TERMINAL_TRUSTED_ORIGINS.length === 0) return true;
    const hostOk = parsed.hostname === "127.0.0.1" || parsed.hostname === "localhost" || parsed.hostname === "::1";
    const portOk = !parsed.port || parsed.port === String(PORT);
    return hostOk && portOk;
  } catch {
    return false;
  }
}

function analyzeTerminalCommand(command, approved = false) {
  const value = String(command || "").trim();
  const lower = value.toLowerCase();
  if (!value) {
    return { allowed: false, reason: "Empty command." };
  }
  const forbidden = [
    /\brm\s+-[^;\n]*rf\s+\/(?:\s|$)/,
    /\bmkfs(?:\.|\s|$)/,
    /\bdd\s+if=/,
    /\bshutdown\b/,
    /\breboot\b/,
    /\bpoweroff\b/,
    /:\s*\(\s*\)\s*\{\s*:\s*\|\s*:\s*&\s*\}/,
  ];
  if (forbidden.some((pattern) => pattern.test(lower))) {
    return { allowed: false, reason: "Command is blocked by the local terminal safety guard." };
  }
  if (/(^|[;&|]\s*)sudo(\s|$)/.test(lower) || /(^|\s)su(\s|$)/.test(lower)) {
    return {
      allowed: false,
      copyOnly: true,
      reason: "sudo/su commands are copy-only in the web terminal. Run them in the real terminal so password prompts and privileges stay visible.",
    };
  }
  const approvalNeeded = [
    /\brm\s+/,
    /\bmv\s+/,
    /\bchmod\s+/,
    /\bchown\s+/,
    /\bgit\s+reset\b/,
    /\bgit\s+checkout\b/,
    /\bgit\s+clean\b/,
    /\bapt(?:-get)?\s+/,
    /\bnpm\s+(?:install|update|audit\s+fix)\b/,
    /\bpip(?:3)?\s+install\b/,
    /\|\s*(?:bash|sh)\b/,
    /\b(?:bash|sh)\s+<\s*\(/,
  ];
  if (!approved && approvalNeeded.some((pattern) => pattern.test(lower))) {
    return {
      allowed: false,
      approvalRequired: true,
      reason: "This command can change files, packages, or repository state. Tick approval before running it.",
    };
  }
  return { allowed: true, reason: "approved" };
}

function sandboxLog(sessionId, entry) {
  fs.mkdirSync(SANDBOX_LOG_DIR, { recursive: true });
  const logPath = path.join(SANDBOX_LOG_DIR, `${sessionId}.jsonl`);
  fs.appendFileSync(logPath, `${JSON.stringify({ ...entry, timestamp: new Date().toISOString() })}\n`);
}

function safeSessionId(input) {
  const value = String(input || "").trim();
  if (/^[a-zA-Z0-9_-]{8,80}$/.test(value)) return value;
  return `session-${randomUUID()}`;
}

async function dockerStatus() {
  const status = {
    enabled: SANDBOX_TERMINAL_ENABLED,
    socket: process.env.DOCKER_SOCKET || "/var/run/docker.sock",
    dockerAvailable: false,
    dockerCliAvailable: false,
    image: SANDBOX_IMAGE,
    imageAvailable: false,
    workspaceRoot: SANDBOX_WORKSPACE_ROOT,
  };
  if (!SANDBOX_TERMINAL_ENABLED) {
    status.error = "Sandbox terminal is disabled by MURGE_SANDBOX_ENABLED.";
    return status;
  }
  try {
    await docker.ping();
    status.dockerAvailable = true;
  } catch (error) {
    status.error = error.message;
    return status;
  }
  try {
    await docker.getImage(SANDBOX_IMAGE).inspect();
    status.imageAvailable = true;
  } catch {
    status.imageAvailable = false;
  }
  try {
    await runProcessCapture("docker", ["--version"], { timeoutMs: 5000 });
    status.dockerCliAvailable = true;
  } catch {
    status.dockerCliAvailable = false;
  }
  return status;
}

async function ensureSandboxSession(rawSessionId) {
  const sessionId = safeSessionId(rawSessionId);
  const existing = sandboxSessions.get(sessionId);
  if (existing?.containerId) {
    try {
      const container = docker.getContainer(existing.containerId);
      const info = await container.inspect();
      if (info.State?.Running) return { ...existing, container };
    } catch {
      sandboxSessions.delete(sessionId);
    }
  }

  const status = await dockerStatus();
  if (!status.enabled) throw new Error("Sandbox terminal is disabled.");
  if (!status.dockerAvailable) throw new Error(`Docker daemon unavailable: ${status.error || "not running"}`);
  if (!status.imageAvailable) throw new Error(`Sandbox image missing: ${SANDBOX_IMAGE}. Run scripts/setup_sandbox_runtime.sh first.`);

  fs.mkdirSync(SANDBOX_WORKSPACE_ROOT, { recursive: true });
  const workspace = path.join(SANDBOX_WORKSPACE_ROOT, sessionId);
  fs.mkdirSync(workspace, { recursive: true });
  const container = await docker.createContainer({
    Image: SANDBOX_IMAGE,
    name: `flameborn-${sessionId}`.slice(0, 63),
    Tty: true,
    OpenStdin: true,
    Cmd: ["sleep", "infinity"],
    WorkingDir: "/workspace",
    User: "coder",
    Labels: {
      "flameborn.session": sessionId,
      "flameborn.runtime": "sandbox",
    },
    HostConfig: {
      Binds: [`${workspace}:/workspace`],
      Memory: SANDBOX_MEMORY_BYTES,
      NanoCpus: SANDBOX_NANO_CPUS,
      NetworkMode: "bridge",
      AutoRemove: false,
    },
  });
  await container.start();
  const session = {
    id: sessionId,
    containerId: container.id,
    workspace,
    createdAt: new Date().toISOString(),
    subscribers: new Set(),
    ptyProcess: null,
  };
  sandboxSessions.set(sessionId, session);
  sandboxLog(sessionId, { event: "container_started", containerId: container.id, workspace });
  return { ...session, container };
}

async function runSandboxCommand(sessionId, command, approved = false) {
  const safety = analyzeTerminalCommand(command, approved);
  if (!safety.allowed) {
    sandboxLog(sessionId, { event: "command_blocked", command, safety });
    return { ok: false, blocked: true, command, safety };
  }
  const session = await ensureSandboxSession(sessionId);
  const exec = await session.container.exec({
    Cmd: ["bash", "-lc", command],
    AttachStdout: true,
    AttachStderr: true,
    User: "coder",
    WorkingDir: "/workspace",
  });
  const startedAt = Date.now();
  const stream = await exec.start({ hijack: true, stdin: false });
  let stdout = "";
  let stderr = "";
  const maxBytes = 120_000;
  const timer = setTimeout(() => {
    try {
      stream.destroy(new Error("timeout"));
    } catch {}
  }, SANDBOX_COMMAND_TIMEOUT_MS);

  await new Promise((resolve, reject) => {
    session.container.modem.demuxStream(stream, {
      write(chunk) {
        if (stdout.length < maxBytes) stdout += chunk.toString("utf8");
      },
    }, {
      write(chunk) {
        if (stderr.length < maxBytes) stderr += chunk.toString("utf8");
      },
    });
    stream.on("end", resolve);
    stream.on("close", resolve);
    stream.on("error", reject);
  }).finally(() => clearTimeout(timer));

  const inspect = await exec.inspect();
  const result = {
    ok: inspect.ExitCode === 0,
    blocked: false,
    sessionId: session.id,
    containerId: session.containerId,
    command,
    cwd: "/workspace",
    exitCode: inspect.ExitCode,
    stdout,
    stderr,
    durationMs: Date.now() - startedAt,
    safety,
  };
  sandboxLog(session.id, { event: "command_result", ...result });
  return result;
}

function normalizeLocalContextPaths(input) {
  const items = Array.isArray(input) ? input : [];
  const safe = [];
  for (const item of items) {
    const value = String(item || "").trim();
    if (!value) continue;
    const normalized = path.normalize(value);
    if (normalized.startsWith("@gary/")) {
      const relativeGary = normalized.slice("@gary/".length);
      const absGary = path.resolve(GARY_AUREON_ROOT, relativeGary);
      if (!absGary.startsWith(path.resolve(GARY_AUREON_ROOT))) continue;
      if (!fs.existsSync(absGary) || !fs.statSync(absGary).isFile()) continue;
      safe.push(`@gary/${relativeGary}`);
      continue;
    }
    const relative = normalized.replace(/^(\.\.[/\\])+/, "");
    const abs = path.resolve(__dirname, relative);
    if (!abs.startsWith(__dirname)) continue;
    if (!fs.existsSync(abs) || !fs.statSync(abs).isFile()) continue;
    safe.push(relative);
  }
  return safe.slice(0, 12);
}

function resolveContextPath(reference) {
  const value = String(reference || "").trim();
  if (value.startsWith("@gary/")) {
    return path.resolve(GARY_AUREON_ROOT, value.slice("@gary/".length));
  }
  return path.resolve(__dirname, value);
}

function getAureonSystemCapabilities() {
  const rootExists = fs.existsSync(GARY_AUREON_ROOT);
  const systems = AUREON_SYSTEM_FILES.map((entry) => {
    const absolutePath = path.join(GARY_AUREON_ROOT, entry.relativePath);
    const exists = rootExists && fs.existsSync(absolutePath);
    const stats = exists ? fs.statSync(absolutePath) : null;
    return {
      ...entry,
      exists,
      path: absolutePath,
      updatedAt: stats ? stats.mtime.toISOString() : null,
    };
  });
  return {
    root: GARY_AUREON_ROOT,
    rootExists,
    detected: systems.filter((item) => item.exists).length,
    total: systems.length,
    systems,
  };
}

function readPublicArtifact(relativePath) {
  const artifactPath = path.resolve(DEFAULT_AUREON_ROOT, relativePath);
  if (!artifactPath.startsWith(DEFAULT_AUREON_ROOT) || !fs.existsSync(artifactPath)) {
    return { exists: false, path: artifactPath, data: null, updatedAt: null };
  }
  const stats = fs.statSync(artifactPath);
  try {
    return {
      exists: true,
      path: artifactPath,
      updatedAt: stats.mtime.toISOString(),
      data: JSON.parse(fs.readFileSync(artifactPath, "utf8")),
    };
  } catch (error) {
    return {
      exists: true,
      path: artifactPath,
      updatedAt: stats.mtime.toISOString(),
      data: null,
      error: error.message,
    };
  }
}

async function buildSupervisorSnapshot(timeoutMs = 1200) {
  const [terminalState, flightTest, phiBridge] = await Promise.all([
    fetchJsonWithTimeout(AUREON_TERMINAL_STATE_URL, timeoutMs),
    fetchJsonWithTimeout(AUREON_FLIGHT_TEST_URL, timeoutMs),
    fetchJsonWithTimeout(AUREON_PHI_STATUS_URL, timeoutMs),
  ]);
  const systems = getAureonSystemCapabilities();
  const fabric = readPublicArtifact("frontend/public/aureon_live_trade_signal_fabric.json");
  const fabricStress = readPublicArtifact("frontend/public/aureon_live_trade_signal_fabric_stress_audit.json");
  const murgeActivation = readPublicArtifact("frontend/public/aureon_murge_runtime_activation_stress_audit.json");
  const flamebornFullCapability = readPublicArtifact("frontend/public/aureon_flameborn_full_capability_stress_audit.json");
  const terminalPayload = terminalState.data || {};
  const exchangePlan = terminalPayload.exchange_action_plan || {};
  const liveGates = {
    orderIntentPublishEnabled: safeBoolean(exchangePlan.order_intent_publish_enabled),
    executorEnabled: safeBoolean(exchangePlan.executor_enabled),
    liveEnabled: safeBoolean(exchangePlan.live_enabled),
    realOrdersDisabled: safeBoolean(exchangePlan.real_orders_disabled),
    exchangeMutationsDisabled: safeBoolean(exchangePlan.exchange_mutations_disabled),
    tradePathState: exchangePlan.trade_path_state || "unknown",
  };
  const globalBlockers = normalizeArray(exchangePlan.global_blockers).map(String);
  const flightChecks = flightTest.data?.checks && typeof flightTest.data.checks === "object" ? flightTest.data.checks : {};
  const artifactRows = [
    {
      id: "live_signal_fabric",
      label: "Live Signal Fabric",
      exists: fabric.exists,
      status: fabric.data?.status || "artifact_missing",
      updatedAt: fabric.updatedAt,
      path: fabric.path,
    },
    {
      id: "live_signal_fabric_stress",
      label: "Live Signal Fabric Stress",
      exists: fabricStress.exists,
      status: fabricStress.data?.status || "artifact_missing",
      updatedAt: fabricStress.updatedAt,
      path: fabricStress.path,
    },
    {
      id: "murge_runtime_activation",
      label: "MURGE Runtime Activation",
      exists: murgeActivation.exists,
      status: murgeActivation.data?.status || "artifact_missing",
      updatedAt: murgeActivation.updatedAt,
      path: murgeActivation.path,
    },
    {
      id: "flameborn_full_capability_stress",
      label: "Flameborn Full Launch Proof",
      exists: flamebornFullCapability.exists,
      status: flamebornFullCapability.data?.status || "artifact_missing",
      updatedAt: flamebornFullCapability.updatedAt,
      path: flamebornFullCapability.path,
    },
  ];
  const liveCapabilityRows = [
    {
      id: "aureon_supervisor_terminal_state",
      label: "Aureon Supervisor Terminal State",
      status: terminalState.ok ? "connected" : "unreachable",
      endpoint: AUREON_TERMINAL_STATE_URL,
      generatedAt: terminalPayload.generated_at || null,
      roundTripMs: terminalState.roundTripMs,
    },
    {
      id: "phi_bridge_chat",
      label: "Phi Bridge Chat",
      status: phiBridge.ok ? "connected" : "unreachable",
      endpoint: AUREON_PHI_STATUS_URL,
      mode: phiBridge.data?.status || phiBridge.data?.mode || null,
      roundTripMs: phiBridge.roundTripMs,
    },
    {
      id: "murge_flameborn_web",
      label: "Flameborn Web Shell",
      status: "serving_localhost",
      endpoint: `http://${HOST}:${PORT}/`,
      localOnly: HOST === "127.0.0.1" || HOST === "localhost" || HOST === "::1",
    },
    {
      id: "thoughtbus_mycelium_visibility",
      label: "ThoughtBus + Mycelium Visibility",
      status: fabric.data?.summary?.thoughtbus_receiving || fabric.data?.summary?.mycelium_receiving ? "receiving" : "artifact_visible",
      thoughtbusReceiving: Boolean(fabric.data?.summary?.thoughtbus_receiving),
      myceliumReceiving: Boolean(fabric.data?.summary?.mycelium_receiving),
    },
  ];
  const blockers = [
    terminalState.ok ? null : "aureon_terminal_state_unreachable",
    phiBridge.ok ? null : "aureon_phi_bridge_unreachable",
    ...globalBlockers,
  ].filter(Boolean);
  return {
    status: terminalState.ok || phiBridge.ok ? "aureon_supervisor_connected" : "aureon_supervisor_attention",
    generatedAt: new Date().toISOString(),
    localOnly: HOST === "127.0.0.1" || HOST === "localhost" || HOST === "::1",
    supervisorConnected: terminalState.ok,
    phiBridgeConnected: phiBridge.ok,
    noTradingGateBypass: true,
    endpoints: {
      terminalState: AUREON_TERMINAL_STATE_URL,
      flightTest: AUREON_FLIGHT_TEST_URL,
      rebootAdvice: AUREON_REBOOT_ADVICE_URL,
      phiBridge: AUREON_PHI_STATUS_URL,
    },
    liveGates,
    flightChecks,
    globalBlockers,
    blockers,
    systems,
    liveCapabilityRows,
    artifactRows,
    terminalStateProof: {
      ok: terminalState.ok,
      statusCode: terminalState.statusCode,
      roundTripMs: terminalState.roundTripMs,
      generatedAt: terminalPayload.generated_at || null,
      status: terminalPayload.status || null,
    },
    phiBridgeProof: {
      ok: phiBridge.ok,
      statusCode: phiBridge.statusCode,
      roundTripMs: phiBridge.roundTripMs,
      status: phiBridge.data?.status || null,
      available: phiBridge.data?.available ?? null,
    },
  };
}

function serveFile(req, res) {
  const requestUrl = new URL(req.url || "/", `http://${req.headers.host || "127.0.0.1"}`);
  const requestedPath = requestUrl.pathname === "/" ? "/index.html" : requestUrl.pathname;
  const safePath = path.normalize(requestedPath).replace(/^(\.\.[/\\])+/, "");
  const filePath = path.join(__dirname, safePath);

  if (!filePath.startsWith(__dirname)) {
    res.writeHead(403);
    res.end("Forbidden");
    return;
  }

  fs.readFile(filePath, (err, data) => {
    if (err) {
      res.writeHead(404);
      res.end("Not found");
      return;
    }
    const ext = path.extname(filePath).toLowerCase();
    res.writeHead(200, securityHeaders({ "Content-Type": mimeTypes[ext] || "application/octet-stream" }));
    res.end(data);
  });
}

async function handleChat(req, res) {
  if (!PROVIDER_API_ENABLED) {
    sendJson(res, 403, {
      error: {
        message: "Provider API calls are disabled by MURGE_PROVIDER_API_ENABLED during local activation.",
      },
    });
    req.resume();
    return;
  }
  let body = "";
  let aborted = false;

  req.on("aborted", () => {
    aborted = true;
  });

  req.on("error", () => {
    if (!res.writableEnded) {
      sendJson(res, 400, { error: { message: "Nie udało się odczytać żądania." } });
    }
  });

  req.on("data", (chunk) => {
    body += chunk;
    if (body.length > 1_000_000 && !aborted) {
      aborted = true;
      req.destroy();
      if (!res.writableEnded) {
        sendJson(res, 413, { error: { message: "Payload jest za duży." } });
      }
    }
  });
  req.on("end", async () => {
    if (aborted || res.writableEnded) return;
    try {
      const parsed = JSON.parse(body || "{}");
      const provider = parsed.provider || "gemini";
      const result = await callProvider(provider, parsed);
      sendJson(res, 200, result);
    } catch (err) {
      sendJson(res, 500, { error: { message: `Błąd serwera: ${err.message}` } });
    }
  });
}

async function handleAssistantCli(req, res) {
  let body = "";
  let aborted = false;

  req.on("aborted", () => {
    aborted = true;
  });

  req.on("error", () => {
    if (!res.writableEnded) {
      sendJson(res, 400, { error: { message: "Nie udało się odczytać żądania." } });
    }
  });

  req.on("data", (chunk) => {
    body += chunk;
    if (body.length > 1_000_000 && !aborted) {
      aborted = true;
      req.destroy();
      if (!res.writableEnded) {
        sendJson(res, 413, { error: { message: "Payload jest za duży." } });
      }
    }
  });

  req.on("end", async () => {
    if (aborted || res.writableEnded) return;
    try {
      const parsed = JSON.parse(body || "{}");
      const result = await runLocalAureonCli(parsed);
      sendJson(res, 200, result);
    } catch (err) {
      sendJson(res, 500, { error: { message: `Błąd lokalnego CLI: ${err.message}` } });
    }
  });
}

async function callProvider(provider, parsed) {
  enforceAccessMode(provider, parsed);
  if (provider === "gemini") return callGemini(parsed);
  if (provider === "huggingface") return callHuggingFace(parsed);
  if (provider === "grok") return callGrok(parsed);
  if (provider === "openai") return callOpenAI(parsed);
  if (provider === "aureon") return callAureonBrain(parsed);
  return callOpenRouter(parsed);
}

async function runLocalAureonCli(parsed) {
  if (!LOCAL_AUREON_CLI_ENABLED) {
    throw new Error("Local Aureon CLI bridge is disabled.");
  }
  const task = String(parsed.task || parsed.message || "").trim();
  if (!task) {
    throw new Error("Missing task text.");
  }
  const mode = String(parsed.mode || "plan").trim() || "plan";
  const model = String(parsed.model || "aureon-architect").trim() || "aureon-architect";
  const responseStyle = String(parsed.responseStyle || "safe").trim().toLowerCase() === "raw" ? "raw" : "safe";
  const swarmRoute = ["direct", "queen", "council", "architect", "scout", "vault"].includes(String(parsed.swarmRoute || "").trim().toLowerCase())
    ? String(parsed.swarmRoute || "").trim().toLowerCase()
    : "direct";
  const contextPaths = normalizeLocalContextPaths(
    Array.isArray(parsed.contextPaths) && parsed.contextPaths.length
      ? parsed.contextPaths
      : DEFAULT_LOCAL_AUREON_CONTEXTS,
  );

  const args = [LOCAL_AUREON_CLI_SCRIPT, "--mode", mode, "--model", model, "--response-style", responseStyle, "--swarm-route", swarmRoute];
  for (const ctx of contextPaths) {
    args.push("--context", ctx);
  }
  args.push(task);

  const result = await runProcessCapture(process.execPath, args, {
    cwd: __dirname,
    timeoutMs: Number(parsed.timeoutMs || 60000),
  });

  const reply = (result.stdout || "").trim();
  if (!reply) {
    throw new Error((result.stderr || "").trim() || "Aureon CLI returned no output.");
  }
  return {
    provider: "aureon",
    model,
    mode: "local-cli",
    reply,
    responseStyle,
    swarmRoute,
    stderr: (result.stderr || "").trim() || null,
    exitCode: result.code,
    contextPaths,
    localOnly: true,
  };
}

function enforceAccessMode(provider, parsed) {
  const mode = String(parsed.accessMode || "free").toLowerCase();
  if (mode !== "free") return;

  if (!FREE_MODE_PROVIDERS.has(provider)) {
    throw new Error(
      `Tryb FREE blokuje providera ${provider}. Przelacz na NORMAL, jesli chcesz uzyc tego providera.`,
    );
  }

  const model = String(parsed.model || "");
  if (provider === "gemini" && model.toLowerCase().includes("pro")) {
    throw new Error("Tryb FREE blokuje modele Gemini Pro. Uzyj Gemini Flash.");
  }
  if (provider === "openrouter" && model && model !== "openrouter/free" && !model.endsWith(":free")) {
    throw new Error("Tryb FREE blokuje platne modele OpenRouter. Uzyj modelu z koncowka :free.");
  }
}

async function parseJsonResponse(response) {
  const raw = await response.text();
  try {
    return raw ? JSON.parse(raw) : {};
  } catch {
    return { error: { message: raw || "Nieprawidłowa odpowiedź API." } };
  }
}

function commonMessages(parsed) {
  return [
    { role: "system", content: parsed.rolePrompt || "Jesteś pomocnym asystentem." },
    { role: "user", content: parsed.message || "" },
  ];
}

async function callOpenRouter(parsed) {
  const apiKey = OPENROUTER_API_KEY || parsed.apiKey;
  if (!apiKey) throw new Error("Brak klucza OpenRouter API.");

  const requestedModel = parsed.model || "openrouter/free";
  const modelQueue = [
    requestedModel,
    ...OPENROUTER_FALLBACK_MODELS.filter((model) => model !== requestedModel),
  ];
  const tried = [];
  let lastError = "Błąd OpenRouter API.";

  for (const model of modelQueue) {
    tried.push(model);
    const response = await fetch("https://openrouter.ai/api/v1/chat/completions", {
      method: "POST",
      headers: {
        Authorization: `Bearer ${apiKey}`,
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost",
        "X-Title": "flAmeBornLLC LLM Academy",
      },
      body: JSON.stringify({
        model,
        messages: commonMessages(parsed),
        temperature: Number(parsed.temperature ?? 0.7),
        max_tokens: Number(parsed.max_tokens ?? 2000),
      }),
    });

    const data = await parseJsonResponse(response);
    if (!response.ok) {
      lastError = data?.error?.message || "Błąd OpenRouter API.";
      if (shouldRetryOpenRouter(lastError)) continue;
      throw new Error(lastError);
    }

    const reply = data?.choices?.[0]?.message?.content;
    if (!reply) {
      lastError = "Brak odpowiedzi modelu OpenRouter.";
      continue;
    }

    return {
      provider: "openrouter",
      model,
      reply,
      requestedModel,
      fallbackUsed: model !== requestedModel,
      triedModels: tried,
    };
  }

  throw new Error(`${lastError} Przetestowane modele: ${tried.join(", ")}`);
}

function shouldRetryOpenRouter(message) {
  const normalized = String(message || "").toLowerCase();
  return (
    normalized.includes("at capacity") ||
    normalized.includes("capacity") ||
    normalized.includes("please try a different model") ||
    normalized.includes("rate limit") ||
    normalized.includes("temporarily unavailable") ||
    normalized.includes("over capacity")
  );
}

async function callOpenAI(parsed) {
  const apiKey = OPENAI_API_KEY || parsed.apiKey;
  if (!apiKey) throw new Error("Brak klucza OPENAI_API_KEY.");

  const response = await fetch("https://api.openai.com/v1/chat/completions", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${apiKey}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      model: parsed.model || "gpt-4o-mini",
      messages: commonMessages(parsed),
      temperature: Number(parsed.temperature ?? 0.7),
      max_tokens: Number(parsed.max_tokens ?? 2000),
    }),
  });

  const data = await parseJsonResponse(response);
  if (!response.ok) throw new Error(data?.error?.message || "Błąd OpenAI API.");
  const reply = data?.choices?.[0]?.message?.content;
  if (!reply) throw new Error("Brak odpowiedzi modelu OpenAI.");
  return { provider: "openai", model: parsed.model, reply };
}

async function callGemini(parsed) {
  const apiKey = GEMINI_API_KEY || parsed.apiKey;
  if (!apiKey) throw new Error("Brak klucza GEMINI_API_KEY.");

  const model = String(parsed.model || "gemini-2.5-flash").replace(/^models\//, "");
  const response = await fetch(
    `https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent?key=${apiKey}`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        systemInstruction: {
          parts: [{ text: parsed.rolePrompt || "Jesteś pomocnym asystentem." }],
        },
        contents: [
          {
            role: "user",
            parts: [{ text: parsed.message || "" }],
          },
        ],
        generationConfig: {
          temperature: Number(parsed.temperature ?? 0.7),
          maxOutputTokens: Number(parsed.max_tokens ?? 2000),
        },
      }),
    },
  );

  const data = await parseJsonResponse(response);
  if (!response.ok) {
    const message = data?.error?.message || "Błąd Gemini API.";
    throw new Error(message);
  }

  const parts = data?.candidates?.[0]?.content?.parts || [];
  const reply = parts.map((part) => part.text || "").join("").trim();
  if (!reply) throw new Error("Brak odpowiedzi modelu Gemini.");
  return { provider: "gemini", model, reply };
}

async function callGrok(parsed) {
  if (!XAI_API_KEY && !parsed.apiKey) throw new Error("Brak klucza XAI_API_KEY.");
  if (!XAI_ALLOW_PAID) {
    throw new Error(
      "Grok API: brak darmowych modeli API. Tryb free-only jest aktywny (XAI_ALLOW_PAID=false).",
    );
  }

  const apiKey = XAI_API_KEY || parsed.apiKey;
  const model = parsed.model || "grok-3-mini";
  const response = await fetch("https://api.x.ai/v1/chat/completions", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${apiKey}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      model,
      messages: commonMessages(parsed),
      temperature: Number(parsed.temperature ?? 0.7),
      max_tokens: Number(parsed.max_tokens ?? 2000),
    }),
  });

  const data = await parseJsonResponse(response);
  if (!response.ok) throw new Error(data?.error?.message || "Błąd Grok/xAI API.");
  const reply = data?.choices?.[0]?.message?.content;
  if (!reply) throw new Error("Brak odpowiedzi modelu Grok.");
  return { provider: "grok", model, reply };
}

async function callHuggingFace(parsed) {
  const token = HF_TOKEN || parsed.apiKey;
  if (!token) throw new Error("Brak klucza HF_TOKEN / HUGGINGFACE_API_KEY.");

  const model = parsed.model || HF_FREE_MODELS[0];
  if (!HF_FREE_MODELS.includes(model)) {
    throw new Error("Model Hugging Face poza listą free-only w tej aplikacji.");
  }

  const response = await fetch("https://router.huggingface.co/v1/chat/completions", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      model,
      messages: commonMessages(parsed),
      temperature: Number(parsed.temperature ?? 0.7),
      max_tokens: Number(parsed.max_tokens ?? 1200),
    }),
  });

  const data = await parseJsonResponse(response);
  if (!response.ok) throw new Error(data?.error?.message || "Błąd Hugging Face API.");
  const reply = data?.choices?.[0]?.message?.content;
  if (!reply) throw new Error("Brak odpowiedzi modelu Hugging Face.");
  return { provider: "huggingface", model, reply };
}

async function callAureonBrain(parsed) {
  const model = parsed.model || "aureon-brain";
  const message = parsed.message || "";
  const rolePrompt = parsed.rolePrompt || "You are Aureon Brain inside flAmeBornLLC LLM Academy.";
  const voice = aureonVoiceForModel(model);
  const includeConnectionFact = /connected|connection|bridge|status|połącz|polacz|połączenie|polaczenie/i.test(message);
  const routedMessage = [
    "Context: this request is routed from flAmeBorn LLM Academy through the Aureon Phi Bridge.",
    includeConnectionFact
      ? "Connection fact: if asked whether Aureon is connected to flAmeBorn LLM Academy, the correct technical answer is yes."
      : "",
    `Human asks: ${message}`,
    "Answer directly in natural language. No trading signals, no JSON, no status report unless asked.",
  ].filter(Boolean).join("\n");
  const vaultRecord = writeAureonVaultRecord({
    type: "chat",
    model,
    message,
    rolePrompt,
    createdAt: new Date().toISOString(),
  });

  if (!AUREON_API_BASE_URL) {
    return buildAureonLocalFallback(model, vaultRecord, null);
  }

  try {
    const controller = new AbortController();
    let timer = null;
    const timeoutPromise = new Promise((_, reject) => {
      timer = setTimeout(() => {
        controller.abort();
        const timeoutError = new Error(`Aureon Brain timeout after ${AUREON_CHAT_TIMEOUT_MS} ms.`);
        timeoutError.name = "AbortError";
        reject(timeoutError);
      }, AUREON_CHAT_TIMEOUT_MS);
    });
    const response = await Promise.race([
      fetch(`${AUREON_API_BASE_URL}${AUREON_CHAT_PATH}`, {
        method: "POST",
        signal: controller.signal,
        headers: {
          "Content-Type": "application/json",
          ...(AUREON_API_KEY ? { Authorization: `Bearer ${AUREON_API_KEY}` } : {}),
        },
        body: JSON.stringify({
          text: routedMessage,
          message: routedMessage,
          voice,
          fast: true,
          peer_id: "flameborn-academy",
          model,
          provider: "aureon",
          rolePrompt,
          context: {
            app: "flAmeBornLLC LLM Academy",
            mode: "aureon-vault-voice",
            voice,
            vaultRecord,
            classroom: "observer-compatible",
          },
        }),
      }),
      timeoutPromise,
    ]).finally(() => clearTimeout(timer));

    const data = await parseJsonResponse(response);
    if (!response.ok) {
      return buildAureonLocalFallback(
        model,
        vaultRecord,
        data?.error?.message || data?.error || "Błąd Aureon Brain API.",
      );
    }

    const reply = extractAureonReply(data);
    if (!reply) {
      return buildAureonLocalFallback(model, vaultRecord, "Aureon Brain nie zwrócił tekstowej odpowiedzi.");
    }
    return {
      provider: "aureon",
      model,
      reply,
      bridgeConnected: true,
      vaultRecord,
      rawStatus: data.status || data.mode || null,
    };
  } catch (error) {
    return buildAureonLocalFallback(model, vaultRecord, error?.message || "Błąd połączenia z Aureon Brain.");
  }
}

function aureonVoiceForModel(model = "") {
  const normalized = String(model || "").toLowerCase();
  if (normalized.includes("council")) return "council";
  if (normalized.includes("architect")) return "architect";
  if (normalized.includes("lover")) return "lover";
  if (normalized.includes("miner")) return "miner";
  if (normalized.includes("scout")) return "scout";
  if (normalized.includes("vault")) return "vault";
  return "queen";
}

function extractAureonReply(data) {
  if (!data || typeof data !== "object") return "";
  if (typeof data.reply === "string") return data.reply;
  if (typeof data.response === "string") return data.response;
  if (typeof data.text === "string") return data.text;
  if (typeof data.message === "string") return data.message;
  if (typeof data.message?.content === "string") return data.message.content;
  if (typeof data.utterance?.response?.text === "string") return data.utterance.response.text;
  if (typeof data.utterance?.statement?.text === "string") return data.utterance.statement.text;
  if (typeof data.statement?.text === "string") return data.statement.text;
  if (typeof data.result?.text === "string") return data.result.text;
  if (typeof data.result === "string") return data.result;
  return "";
}

function writeAureonVaultRecord(record) {
  try {
    fs.mkdirSync(AUREON_VAULT_PATH, { recursive: true });
    const day = new Date().toISOString().slice(0, 10);
    const dailyDir = path.join(AUREON_VAULT_PATH, "daily");
    const sessionDir = path.join(AUREON_VAULT_PATH, "sessions");
    fs.mkdirSync(dailyDir, { recursive: true });
    fs.mkdirSync(sessionDir, { recursive: true });
    const safeText = String(record.message || "").replace(/\s+/g, " ").trim();
    const mdPath = path.join(dailyDir, `${day}.md`);
    const jsonlPath = path.join(sessionDir, `${day}.jsonl`);
    fs.appendFileSync(
      mdPath,
      [
        `\n## ${record.createdAt} - ${record.type}`,
        `- model: ${record.model}`,
        `- source: flAmeBornLLC LLM Academy`,
        `- note: ${safeText.slice(0, 1200) || "(empty)"}`,
        "",
      ].join("\n"),
    );
    fs.appendFileSync(jsonlPath, `${JSON.stringify(record)}\n`);
    return { mode: "filesystem-vault", path: mdPath };
  } catch (error) {
    return { mode: "vault-write-failed", error: error.message };
  }
}

function buildAureonLocalFallback(model, vaultRecord, bridgeError) {
  const reply = [
    AUREON_API_BASE_URL
      ? "Aureon supervisor is wired, but the live chat bridge did not return a text response in time."
      : "Aureon Brain bridge is prepared but no live Aureon endpoint is configured yet.",
    "I recorded this turn into the local Aureon vault memory so the organism keeps the context.",
    AUREON_API_BASE_URL
      ? "Check the Phi bridge model/runtime if you need live generated text instead of the vault fallback."
      : "Set AUREON_API_BASE_URL to the local Aureon bridge to activate live chat.",
  ].join(" ");

  return {
    provider: "aureon",
    model,
    reply,
    bridgeConnected: false,
    vaultRecord,
    architecture: aureonArchitectureStatus(),
    bridgeError: bridgeError || null,
  };
}

function aureonArchitectureStatus() {
  return {
    obsidianBridge: {
      mode: AUREON_API_BASE_URL ? "external-aureon" : "local-filesystem-vault",
      vaultPath: AUREON_API_BASE_URL ? null : AUREON_VAULT_PATH,
    },
    ollamaFallback: {
      mode: "external-aureon-managed",
      expectedEndpoint: "Aureon OpenMultiAgent / Ollama fallback behind Gary bridge",
    },
    queenLayer: {
      mode: AUREON_API_BASE_URL ? "remote-available" : "waiting-for-aureon-bridge",
      safeDefault: "observer/status only; no autonomous actions enabled",
    },
  };
}

async function handleAureonStatus(res) {
  const supervisor = await buildSupervisorSnapshot();
  sendJson(res, 200, {
    provider: "aureon",
    configured: Boolean(AUREON_API_BASE_URL),
    baseUrlConfigured: Boolean(AUREON_API_BASE_URL),
    baseUrl: AUREON_API_BASE_URL,
    chatPath: AUREON_CHAT_PATH,
    localBridgeEnabled: true,
    supervisorConnected: supervisor.supervisorConnected,
    phiBridgeConnected: supervisor.phiBridgeConnected,
    tradePathState: supervisor.liveGates.tradePathState,
    activation: {
      localOnly: HOST === "127.0.0.1" || HOST === "localhost" || HOST === "::1",
      hostTerminalEnabled: LOCAL_TERMINAL_ENABLED,
      sandboxEnabled: SANDBOX_TERMINAL_ENABLED,
      providerApiEnabled: PROVIDER_API_ENABLED,
      cloudflareEnabled: CLOUDFLARE_ENABLED,
      noTradingGateBypass: true,
    },
    architecture: aureonArchitectureStatus(),
    supervisor: {
      status: supervisor.status,
      blockers: supervisor.blockers,
      liveGates: supervisor.liveGates,
      liveCapabilityRows: supervisor.liveCapabilityRows,
      artifactRows: supervisor.artifactRows,
    },
  });
}

async function handleAureonSystems(res) {
  const supervisor = await buildSupervisorSnapshot(3000);
  sendJson(res, 200, {
    provider: "aureon",
    capabilities: supervisor.systems,
    liveCapabilityRows: supervisor.liveCapabilityRows,
    artifactRows: supervisor.artifactRows,
    liveGates: supervisor.liveGates,
    noTradingGateBypass: true,
  });
}

async function handleAureonSupervisor(res) {
  sendJson(res, 200, await buildSupervisorSnapshot(3000));
}

async function handleAureonFullCapabilityStress(res) {
  const artifact = readPublicArtifact("frontend/public/aureon_flameborn_full_capability_stress_audit.json");
  if (!artifact.exists || !artifact.data) {
    sendJson(res, 404, {
      status: "artifact_missing",
      path: artifact.path,
      error: artifact.error || "Flameborn full capability stress artifact has not been generated.",
    });
    return;
  }
  sendJson(res, 200, artifact.data);
}

async function handleAureonChat(req, res) {
  try {
    const parsed = await readJsonBody(req, res);
    const result = await callAureonBrain({
      ...parsed,
      provider: "aureon",
      model: parsed.model || "aureon-brain",
    });
    sendJson(res, 200, result);
  } catch (err) {
    if (!res.writableEnded) {
      sendJson(res, 500, { error: { message: `Aureon bridge error: ${err.message}` } });
    }
  }
}

function buildMetacognitionSnapshot() {
  const events = classroomMemory.events.slice(-12);
  const reflections = classroomMemory.reflections.slice(-20);
  const patterns = classroomMemory.patterns.slice(-12);
  const inconsistencies = classroomMemory.inconsistencies.slice(-12);
  const workflows = classroomMemory.workflows.slice(-12);
  const latestEvent = events.at(-1) || null;
  const latestReflection = reflections.at(-1) || null;
  const providerCounts = new Map();

  for (const event of events) {
    const provider = String(event.provider || "unknown");
    providerCounts.set(provider, (providerCounts.get(provider) || 0) + 1);
  }

  const dominantProvider = [...providerCounts.entries()].sort((a, b) => b[1] - a[1])[0]?.[0] || "none";
  const instabilityRatio = events.length ? inconsistencies.length / events.length : 0;
  const stabilityIndex = Math.max(0, Math.min(100, Math.round((1 - instabilityRatio) * 100)));
  const providerChurn = providerCounts.size >= 4 ? "High provider switching detected across the recent window." : null;
  const unresolvedFailures = inconsistencies.length >= 3 ? "Repeated failures or quota/path problems remain unresolved." : null;
  const aureonFocus = workflows.some((item) => String(item).toLowerCase().includes("aureon"))
    ? "Aureon integration remains a dominant workflow in the current session."
    : null;
  const guidance = [
    unresolvedFailures ? "Resolve the latest failing route or provider quota before expanding integrations." : "No persistent failure cluster detected in the recent window.",
    providerChurn ? "Reduce provider churn if you need tighter reproducibility for tests and logs." : "Provider selection looks stable enough for iterative work.",
    aureonFocus ? "Keep Aureon changes isolated behind local toggles and explicit validation." : "No Aureon-dominant drift detected in the active workflow.",
  ];

  return {
    source: "local-heuristic-inspired-by-queen-metacognition",
    latestEvent,
    latestReflection,
    stabilityIndex,
    dominantProvider,
    insightCount: reflections.length,
    patterns: patterns.slice(-4),
    inconsistencies: inconsistencies.slice(-4),
    workflows: workflows.slice(-4),
    insights: [providerChurn, unresolvedFailures, aureonFocus].filter(Boolean),
    guidance,
    updatedAt: classroomMemory.analytics.lastUpdated || new Date().toISOString(),
  };
}

function handleMetacognition(res) {
  sendJson(res, 200, {
    monitor: buildMetacognitionSnapshot(),
  });
}

async function handleResearchFeed(req, res) {
  try {
    const requestUrl = new URL(req.url || "/api/research/feed", `http://${req.headers.host || "127.0.0.1"}`);
    const query = String(requestUrl.searchParams.get("q") || "neutrino phenomenology JAX TPU reproducible research").trim();
    const limit = Math.max(1, Math.min(6, Number.parseInt(requestUrl.searchParams.get("limit") || "3", 10) || 3));
    if (!fs.existsSync(WORLD_DATA_BRIDGE_SCRIPT)) {
      throw new Error("world_data_bridge.py is missing.");
    }
    const result = await runProcessCapture("python3", [
      WORLD_DATA_BRIDGE_SCRIPT,
      "--gary-root",
      GARY_AUREON_ROOT,
      "--query",
      query,
      "--limit",
      String(limit),
    ], {
      timeoutMs: 45_000,
    });
    if (result.code !== 0) {
      throw new Error(result.stderr.trim() || "world data bridge failed");
    }
    const payload = JSON.parse(result.stdout || "{}");
    sendJson(res, 200, {
      provider: "aureon-open-research",
      feed: payload,
    });
  } catch (err) {
    sendJson(res, 500, { error: { message: err.message } });
  }
}

function handleTerminalStatus(req, res) {
  if (!allowTerminalRequest(req)) {
    sendJson(res, 403, { error: { message: "Local terminal is available only from localhost." } });
    return;
  }
  sendJson(res, 200, {
    enabled: LOCAL_TERMINAL_ENABLED,
    cwd: LOCAL_TERMINAL_CWD,
    shell: process.platform === "win32"
      ? (process.env.MURGE_WINDOWS_SHELL || process.env.ComSpec || "powershell.exe")
      : (process.env.SHELL || "/bin/bash"),
    sudoMode: "copy-only",
    remoteAccess: TERMINAL_ALLOW_REMOTE,
    trustedOrigins: TERMINAL_TRUSTED_ORIGINS,
    guardedActivation: true,
  });
}

async function handleTerminalRun(req, res) {
  if (!allowTerminalRequest(req)) {
    sendJson(res, 403, { error: { message: "Local terminal is available only from localhost." } });
    return;
  }
  if (!isTrustedTerminalOrigin(req)) {
    sendJson(res, 403, { error: { message: "Terminal origin is not trusted." } });
    return;
  }
  if (!LOCAL_TERMINAL_ENABLED) {
    sendJson(res, 403, { error: { message: "Local terminal is disabled." } });
    return;
  }
  try {
    const parsed = await readJsonBody(req, res, 120_000);
    const command = String(parsed.command || "").trim();
    const approved = parsed.approved === true;
    const safety = analyzeTerminalCommand(command, approved);
    if (!safety.allowed) {
      sendJson(res, 200, {
        ok: false,
        blocked: true,
        command,
        cwd: LOCAL_TERMINAL_CWD,
        safety,
      });
      return;
    }
    const result = await runShellCapture(command, {
      cwd: LOCAL_TERMINAL_CWD,
      timeoutMs: Math.max(5_000, Math.min(120_000, Number(parsed.timeoutMs || 30_000))),
    });
    sendJson(res, 200, {
      ok: result.code === 0,
      blocked: false,
      command,
      cwd: LOCAL_TERMINAL_CWD,
      exitCode: result.code,
      stdout: result.stdout,
      stderr: result.stderr,
      truncated: result.truncated,
      durationMs: result.durationMs,
      safety,
    });
  } catch (err) {
    sendJson(res, 500, { error: { message: err.message } });
  }
}

async function handleSandboxStatus(req, res) {
  if (!allowTerminalRequest(req)) {
    sendJson(res, 403, { error: { message: "Sandbox terminal is available only from localhost." } });
    return;
  }
  const status = await dockerStatus();
  sendJson(res, 200, {
    ...status,
    enabled: SANDBOX_TERMINAL_ENABLED,
    remoteAccess: TERMINAL_ALLOW_REMOTE,
    trustedOrigins: TERMINAL_TRUSTED_ORIGINS,
    guardedActivation: true,
  });
}

async function handleSandboxRun(req, res) {
  if (!allowTerminalRequest(req)) {
    sendJson(res, 403, { error: { message: "Sandbox terminal is available only from localhost." } });
    return;
  }
  if (!isTrustedTerminalOrigin(req)) {
    sendJson(res, 403, { error: { message: "Sandbox origin is not trusted." } });
    return;
  }
  if (!SANDBOX_TERMINAL_ENABLED) {
    sendJson(res, 403, { error: { message: "Sandbox terminal is disabled by MURGE_SANDBOX_ENABLED." } });
    return;
  }
  try {
    const parsed = await readJsonBody(req, res, 120_000);
    const sessionId = safeSessionId(parsed.sessionId || "default-sandbox");
    const command = String(parsed.command || "").trim();
    const approved = parsed.approved === true;
    if (!command) throw new Error("Missing sandbox command.");
    const result = await runSandboxCommand(sessionId, command, approved);
    sendJson(res, 200, result);
  } catch (err) {
    sendJson(res, 500, { error: { message: err.message } });
  }
}

async function handleClassroomObserve(req, res) {
  try {
    const event = await readJsonBody(req, res, 750_000);
    const result = processClassroomEvent(event);
    sendJson(res, 200, result);
  } catch (err) {
    sendJson(res, 400, { error: { message: err.message } });
  }
}

function handleClassroomState(res) {
  sendJson(res, 200, {
    memory: classroomMemory,
    analytics: classroomMemory.analytics,
  });
}

function handleClassroomReplay(res) {
  sendJson(res, 200, {
    events: classroomMemory.events.slice(-100),
    reflections: classroomMemory.reflections.slice(-100),
    memory: {
      summaries: classroomMemory.summaries.slice(-50),
      patterns: classroomMemory.patterns.slice(-50),
      inconsistencies: classroomMemory.inconsistencies.slice(-50),
      workflows: classroomMemory.workflows.slice(-50),
    },
  });
}

function processClassroomEvent(event) {
  const safeEvent = normalizeClassroomEvent(event);
  contextBus.publish("conversation.mirrored", safeEvent);

  const observers = safeEvent.observers
    .filter((observer) => observer.enabled !== false)
    .map((observer) => runObserver(observer, safeEvent));
  const memory = buildObservationMemory(safeEvent);
  const tokenCost = estimateTokens(`${safeEvent.conversation.user} ${safeEvent.conversation.assistant}`);

  classroomMemory.reflections.push(...observers.map((observer) => ({
    observerId: observer.id,
    role: observer.role,
    reflection: observer.latestReflection,
    createdAt: observer.lastRunAt,
  })));
  classroomMemory.summaries.push(...memory.summaries);
  classroomMemory.patterns.push(...memory.patterns);
  classroomMemory.inconsistencies.push(...memory.inconsistencies);
  classroomMemory.workflows.push(...memory.workflows);
  classroomMemory.reflections = classroomMemory.reflections.slice(-200);
  classroomMemory.summaries = classroomMemory.summaries.slice(-200);
  classroomMemory.patterns = classroomMemory.patterns.slice(-200);
  classroomMemory.inconsistencies = classroomMemory.inconsistencies.slice(-200);
  classroomMemory.workflows = classroomMemory.workflows.slice(-200);
  classroomMemory.analytics = {
    mirroredEvents: classroomMemory.analytics.mirroredEvents + 1,
    observerRuns: classroomMemory.analytics.observerRuns + observers.length,
    estimatedTokens: classroomMemory.analytics.estimatedTokens + tokenCost,
    lastUpdated: new Date().toISOString(),
  };
  persistClassroomMemory();

  return {
    eventId: safeEvent.id,
    observers,
    memory,
    analytics: {
      estimatedTokens: tokenCost,
      mirroredEvents: classroomMemory.analytics.mirroredEvents,
      observerRuns: classroomMemory.analytics.observerRuns,
      lastUpdated: classroomMemory.analytics.lastUpdated,
    },
  };
}

function normalizeClassroomEvent(event) {
  const depth = ["shallow", "standard", "deep"].includes(event.depth) ? event.depth : "standard";
  const limit = OBSERVATION_DEPTH_LIMITS[depth];
  const conversation = event.conversation || {};

  return {
    id: String(event.id || `evt-${Date.now()}`),
    sessionId: String(event.sessionId || "default-session"),
    createdAt: event.createdAt || new Date().toISOString(),
    depth,
    observers: Array.isArray(event.observers) ? event.observers.slice(0, 8) : [],
    conversation: {
      user: truncateText(conversation.user || "", Math.floor(limit * 0.45)),
      assistant: truncateText(conversation.assistant || "", Math.floor(limit * 0.55)),
      provider: String(conversation.provider || "unknown"),
      model: String(conversation.model || "unknown"),
      accessMode: String(conversation.accessMode || "free"),
    },
  };
}

function runObserver(observer, event) {
  const text = `${event.conversation.user}\n${event.conversation.assistant}`;
  const memory = buildObservationMemory(event);
  const now = new Date().toISOString();
  const preset = observer.preset || "memory";
  let reflection = "Context observed.";

  if (preset === "gemma") {
    reflection = [
      memory.summaries[0],
      memory.patterns[0] ? `Pattern: ${memory.patterns[0]}` : null,
      memory.workflows[0] ? `Workflow: ${memory.workflows[0]}` : null,
    ].filter(Boolean).join(" ");
  } else if (preset === "logic") {
    reflection = memory.inconsistencies[0] || "No contradiction detected; keep monitoring assumptions.";
  } else if (preset === "code") {
    reflection = memory.patterns[0] || "No new implementation pattern detected in this turn.";
  } else if (preset === "workflow") {
    reflection = memory.workflows[0] || "Workflow continuity preserved; no new action chain found.";
  } else if (preset === "memory") {
    reflection = memory.summaries[0] || "Session context compacted.";
  } else if (preset === "aureon") {
    reflection = [
      "Aureon Queen observer mapped the turn into vault-compatible memory.",
      memory.workflows[0] ? `Workflow: ${memory.workflows[0]}` : null,
      memory.patterns[0] ? `Pattern: ${memory.patterns[0]}` : null,
    ].filter(Boolean).join(" ");
  }

  return {
    id: observer.id,
    role: observer.role,
    model: observer.model || "local-heuristic",
    state: "idle",
    tokenUsage: Number(observer.tokenUsage || 0) + estimateTokens(text),
    latestReflection: reflection,
    memoryItems: Number(observer.memoryItems || 0) + 1,
    lastRunAt: now,
  };
}

function buildObservationMemory(event) {
  const text = `${event.conversation.user}\n${event.conversation.assistant}`;
  const lower = text.toLowerCase();
  return {
    summaries: [truncateText(text.replace(/\s+/g, " "), 240)].filter(Boolean),
    patterns: [
      includesAny(lower, ["api", "token", "secret"]) ? "Provider credential and secret-management workflow detected." : null,
      includesAny(lower, ["deploy", "wrangler", "worker", "cloudflare"]) ? "Cloud deployment workflow detected." : null,
      includesAny(lower, ["script", "server.mjs", "index.mjs", "endpoint"]) ? "Application integration pattern detected." : null,
      includesAny(lower, ["aureon", "queen", "obsidian", "ollama", "vault"]) ? "Aureon brain/vault integration pattern detected." : null,
    ].filter(Boolean),
    inconsistencies: [
      includesAny(lower, ["404", "nie dziala", "does not work"]) ? "A route or external dashboard path failed and needs alternate verification." : null,
      includesAny(lower, ["quota", "limit", "billing"]) ? "Provider limit or billing condition may affect reproducibility." : null,
    ].filter(Boolean),
    workflows: [
      includesAny(lower, ["cloudflare", "workers.dev"]) ? "Cloudflare Workers publication path is active." : null,
      includesAny(lower, ["gemini", "openrouter", "huggingface", "grok", "openai"]) ? "Multi-provider model orchestration path is active." : null,
      includesAny(lower, ["aureon", "queen", "obsidian", "ollama", "vault"]) ? "Aureon Brain integration path is active: vault memory, Queen observer, Ollama fallback." : null,
      includesAny(lower, ["test", "sprawdz", "verify"]) ? "Verification-first workflow is active." : null,
    ].filter(Boolean),
  };
}

function includesAny(text, needles) {
  return needles.some((needle) => text.includes(needle));
}

function estimateTokens(text) {
  return Math.ceil(String(text || "").length / 4);
}

function truncateText(text, maxLength) {
  const value = String(text || "").trim();
  return value.length > maxLength ? `${value.slice(0, maxLength - 1)}…` : value;
}

const server = http.createServer((req, res) => {
  if (req.method === "POST" && req.url === "/api/chat") {
    handleChat(req, res);
    return;
  }
  if (req.method === "POST" && req.url === "/api/aureon/chat") {
    handleAureonChat(req, res);
    return;
  }
  if (req.method === "POST" && req.url === "/api/assistant/cli") {
    handleAssistantCli(req, res);
    return;
  }
  if (req.method === "POST" && req.url === "/api/classroom/observe") {
    handleClassroomObserve(req, res);
    return;
  }
  if (req.method === "GET" && req.url === "/api/classroom/state") {
    handleClassroomState(res);
    return;
  }
  if (req.method === "GET" && req.url === "/api/classroom/replay") {
    handleClassroomReplay(res);
    return;
  }
  if (req.method === "GET" && req.url === "/api/aureon/status") {
    handleAureonStatus(res).catch((error) => sendJson(res, 500, { error: { message: error.message } }));
    return;
  }
  if (req.method === "GET" && req.url === "/api/aureon/systems") {
    handleAureonSystems(res).catch((error) => sendJson(res, 500, { error: { message: error.message } }));
    return;
  }
  if (req.method === "GET" && req.url === "/api/aureon/capabilities") {
    handleAureonSystems(res).catch((error) => sendJson(res, 500, { error: { message: error.message } }));
    return;
  }
  if (req.method === "GET" && req.url === "/api/aureon/supervisor") {
    handleAureonSupervisor(res).catch((error) => sendJson(res, 500, { error: { message: error.message } }));
    return;
  }
  if (req.method === "GET" && req.url === "/api/aureon/full-capability-stress") {
    handleAureonFullCapabilityStress(res).catch((error) => sendJson(res, 500, { error: { message: error.message } }));
    return;
  }
  if (req.method === "GET" && req.url.startsWith("/api/research/feed")) {
    handleResearchFeed(req, res);
    return;
  }
  if (req.method === "GET" && req.url === "/api/metacognition") {
    handleMetacognition(res);
    return;
  }
  if (req.method === "GET" && req.url === "/api/terminal/status") {
    handleTerminalStatus(req, res);
    return;
  }
  if (req.method === "POST" && req.url === "/api/terminal/run") {
    handleTerminalRun(req, res);
    return;
  }
  if (req.method === "GET" && req.url === "/api/sandbox/status") {
    handleSandboxStatus(req, res);
    return;
  }
  if (req.method === "POST" && req.url === "/api/sandbox/run") {
    handleSandboxRun(req, res);
    return;
  }
  if (req.method === "GET" || req.method === "HEAD") {
    serveFile(req, res);
    return;
  }
  res.writeHead(405);
  res.end("Method not allowed");
});

const terminalWss = new WebSocketServer({ noServer: true });

function sendWsJson(ws, payload) {
  if (ws.readyState === 1) {
    ws.send(JSON.stringify(payload));
  }
}

async function attachSandboxTerminal(ws, req) {
  if (!allowTerminalRequest(req) || !isTrustedTerminalOrigin(req)) {
    sendWsJson(ws, { type: "error", message: "Sandbox terminal websocket is local-only." });
    ws.close();
    return;
  }
  if (!SANDBOX_TERMINAL_ENABLED) {
    sendWsJson(ws, { type: "error", message: "Sandbox terminal is disabled by MURGE_SANDBOX_ENABLED." });
    ws.close();
    return;
  }
  const requestUrl = new URL(req.url || "/", `http://${req.headers.host || "127.0.0.1"}`);
  const sessionId = safeSessionId(requestUrl.searchParams.get("sessionId") || "default-sandbox");
  const status = await dockerStatus();
  if (!status.dockerAvailable || !status.imageAvailable || !status.dockerCliAvailable) {
    sendWsJson(ws, {
      type: "error",
      message: !status.dockerAvailable
        ? `Docker daemon unavailable: ${status.error || "not running"}`
        : !status.imageAvailable
          ? `Sandbox image missing: ${SANDBOX_IMAGE}`
          : "Docker CLI is required for PTY streaming.",
      status,
    });
    ws.close();
    return;
  }

  const session = await ensureSandboxSession(sessionId);
  let liveSession = sandboxSessions.get(session.id);
  liveSession.subscribers.add(ws);
  sendWsJson(ws, {
    type: "attached",
    sessionId: session.id,
    containerId: session.containerId,
    cwd: "/workspace",
  });

  if (!liveSession.ptyProcess) {
    liveSession.ptyProcess = pty.spawn("docker", ["exec", "-it", "--user", "coder", session.containerId, "bash", "-l"], {
      name: "xterm-256color",
      cols: 100,
      rows: 28,
      cwd: __dirname,
      env: process.env,
    });
    sandboxLog(session.id, { event: "pty_started", containerId: session.containerId });
    liveSession.ptyProcess.onData((data) => {
      for (const subscriber of liveSession.subscribers) {
        if (subscriber.readyState === 1) {
          subscriber.send(data);
        }
      }
    });
    liveSession.ptyProcess.onExit(({ exitCode, signal }) => {
      sandboxLog(session.id, { event: "pty_exit", exitCode, signal });
      liveSession.ptyProcess = null;
      for (const subscriber of liveSession.subscribers) {
        sendWsJson(subscriber, { type: "exit", exitCode, signal });
      }
    });
  }

  ws.on("message", (message) => {
    const text = message.toString("utf8");
    try {
      const event = JSON.parse(text);
      if (event.type === "resize") {
        liveSession.ptyProcess?.resize(Number(event.cols || 100), Number(event.rows || 28));
        return;
      }
      if (event.type === "ping") {
        sendWsJson(ws, { type: "pong", at: Date.now() });
        return;
      }
      if (event.type === "input") {
        liveSession.ptyProcess?.write(String(event.data || ""));
        return;
      }
    } catch {
      liveSession.ptyProcess?.write(text);
    }
  });
  ws.on("close", () => {
    liveSession.subscribers.delete(ws);
    sandboxLog(session.id, { event: "ws_detached", subscribers: liveSession.subscribers.size });
  });
}

terminalWss.on("connection", (ws, req) => {
  attachSandboxTerminal(ws, req).catch((error) => {
    sendWsJson(ws, { type: "error", message: error.message });
    ws.close();
  });
});

server.on("upgrade", (req, socket, head) => {
  const requestUrl = new URL(req.url || "/", `http://${req.headers.host || "127.0.0.1"}`);
  if (requestUrl.pathname !== "/ws/sandbox-terminal") {
    socket.destroy();
    return;
  }
  if (!allowTerminalRequest(req) || !isTrustedTerminalOrigin(req)) {
    socket.write("HTTP/1.1 403 Forbidden\r\n\r\n");
    socket.destroy();
    return;
  }
  terminalWss.handleUpgrade(req, socket, head, (ws) => {
    terminalWss.emit("connection", ws, req);
  });
});

server.listen(PORT, HOST, () => {
  console.log(`flAmeBornLLC / LLM Academy running: http://${HOST}:${PORT}`);
});

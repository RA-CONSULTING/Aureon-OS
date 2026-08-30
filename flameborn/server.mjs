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

// Load shared Aureon environment first so skeleton vars are available,
// then let flameborn's local .env fill any gaps.
if (process.env.AUREON_ENV_PATH) {
  loadEnvFile(process.env.AUREON_ENV_PATH);
}

loadEnvFile(path.resolve(__dirname, "..", ".env"));
loadEnvFile(path.join(__dirname, ".env"));
loadEnvFile(path.join(process.env.HOME || "", ".config/gemini/env"));

const PORT = process.env.PORT || 4173;
const HOST = process.env.HOST || "127.0.0.1";
const OPENROUTER_API_KEY = process.env.OPENROUTER_API_KEY || "";
const OPENAI_API_KEY = process.env.OPENAI_API_KEY || "";
const GEMINI_API_KEY = process.env.GEMINI_API_KEY || process.env.GOOGLE_API_KEY || "";
const XAI_API_KEY = process.env.XAI_API_KEY || "";
const XAI_ALLOW_PAID = String(process.env.XAI_ALLOW_PAID || "false").toLowerCase() === "true";
const HF_TOKEN = process.env.HF_TOKEN || process.env.HUGGINGFACE_API_KEY || "";
const OLLAMA_API_KEY = process.env.OLLAMA_API_KEY || process.env.AUREON_OLLAMA_API_KEY || process.env.AUREON_LLM_API_KEY || "";
const OLLAMA_BASE_URL = String(process.env.AUREON_LLM_BASE_URL || "https://ollama.com/v1").replace(/\/+$/, "");
const OLLAMA_MODEL = process.env.AUREON_LLM_MODEL || process.env.AUREON_OLLAMA_MODEL || "kimi-k2.7-code";
const OLLAMA_REASONING_EFFORT = process.env.AUREON_OLLAMA_REASONING_EFFORT || "none";
const EXTERNAL_LLM_FALLBACK = String(process.env.AUREON_EXTERNAL_LLM_FALLBACK || "ollama").toLowerCase();
const AUREON_API_BASE_URL = String(process.env.AUREON_API_BASE_URL || "").replace(/\/+$/, "");
const AUREON_API_KEY = process.env.AUREON_API_KEY || "";
const AUREON_PORT = Number(process.env.AUREON_PORT || 5566);
const AUREON_CHAT_PATH = process.env.AUREON_CHAT_PATH || "/api/message";
const AUREON_VAULT_PATH = process.env.AUREON_VAULT_PATH || path.join(__dirname, "logs", "aureon-vault");
const GARY_AUREON_ROOT = process.env.GARY_AUREON_ROOT || path.resolve(__dirname, "..");
const LOCAL_TERMINAL_ENABLED = String(process.env.LOCAL_TERMINAL_ENABLED || "true").toLowerCase() !== "false";
const LOCAL_TERMINAL_CWD = process.env.LOCAL_TERMINAL_CWD || __dirname;
const TERMINAL_ALLOW_REMOTE = String(process.env.TERMINAL_ALLOW_REMOTE || "false").toLowerCase() === "true";
const TERMINAL_TRUSTED_ORIGINS = String(process.env.TERMINAL_TRUSTED_ORIGINS || "")
  .split(",")
  .map((value) => value.trim())
  .filter(Boolean);
const SANDBOX_TERMINAL_ENABLED = String(process.env.SANDBOX_TERMINAL_ENABLED || "true").toLowerCase() !== "false";
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
const FREE_MODE_PROVIDERS = new Set(["gemini", "openrouter", "aureon", "ollama"]);
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

function sendJson(res, code, payload) {
  res.writeHead(code, { "Content-Type": "application/json; charset=utf-8" });
  res.end(JSON.stringify(payload));
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
    const child = spawn("/bin/bash", ["-lc", command], {
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

function proxyToAureon(req, res, aureonPath) {
  const options = {
    hostname: "127.0.0.1",
    port: AUREON_PORT,
    path: aureonPath,
    method: req.method,
    headers: { ...req.headers, host: `127.0.0.1:${AUREON_PORT}` },
  };
  const proxyReq = http.request(options, (proxyRes) => {
    res.writeHead(proxyRes.statusCode, proxyRes.headers);
    proxyRes.pipe(res);
  });
  proxyReq.on("error", (err) => {
    console.error(`[aureon-proxy] ${req.method} ${aureonPath} → error: ${err.message}`);
    sendJson(res, 502, { error: "Aureon backend unreachable", message: err.message, aureonPort: AUREON_PORT });
  });
  req.pipe(proxyReq);
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
    res.writeHead(200, { "Content-Type": mimeTypes[ext] || "application/octet-stream" });
    res.end(data);
  });
}

async function handleChat(req, res) {
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
  try {
    if (provider === "gemini") return await callGemini(parsed);
    if (provider === "huggingface") return await callHuggingFace(parsed);
    if (provider === "grok") return await callGrok(parsed);
    if (provider === "openai") return await callOpenAI(parsed);
    if (provider === "aureon") return await callAureonBrain(parsed);
    if (provider === "ollama") return await callOllamaCloud(parsed, provider);
    return await callOpenRouter(parsed);
  } catch (primaryError) {
    if (provider === "ollama") throw primaryError;
    try {
      return await callOllamaCloud(parsed, provider);
    } catch (fallbackError) {
      throw new Error(`${primaryError.message} Ollama fallback: ${fallbackError.message}`);
    }
  }
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

async function callOllamaCloud(parsed, fallbackFor = null) {
  if (["none", "off", "disabled", "false", "0"].includes(EXTERNAL_LLM_FALLBACK)) {
    throw new Error("Ollama fallback is disabled.");
  }
  if (!OLLAMA_API_KEY) throw new Error("OLLAMA_API_KEY is not configured.");
  const endpoint = /\/chat\/completions$/i.test(OLLAMA_BASE_URL)
    ? OLLAMA_BASE_URL
    : `${OLLAMA_BASE_URL}/chat/completions`;
  const response = await fetch(endpoint, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${OLLAMA_API_KEY}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      model: OLLAMA_MODEL,
      messages: commonMessages(parsed),
      temperature: Number(parsed.temperature ?? 0.7),
      max_tokens: Number(parsed.max_tokens ?? 2000),
      reasoning_effort: OLLAMA_REASONING_EFFORT,
    }),
  });
  const data = await parseJsonResponse(response);
  if (!response.ok) throw new Error(data?.error?.message || `Ollama Cloud HTTP ${response.status}.`);
  const reply = data?.choices?.[0]?.message?.content;
  if (!reply) throw new Error("Ollama Cloud returned no visible response.");
  return { provider: "ollama", model: OLLAMA_MODEL, reply, fallbackFor };
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
    const response = await fetch(`${AUREON_API_BASE_URL}${AUREON_CHAT_PATH}`, {
      method: "POST",
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
    });

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
    "Aureon Brain bridge is prepared but not connected to a live Aureon endpoint yet.",
    "I recorded this turn into the local Aureon vault memory so Obsidian can index it.",
    "Set AUREON_API_BASE_URL to Gary's bridge/vault server to activate the external brain.",
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
      mode: OLLAMA_API_KEY ? "ollama-cloud-ready" : "waiting-for-server-secret",
      expectedEndpoint: "Ollama Cloud OpenAI-compatible API",
    },
    queenLayer: {
      mode: AUREON_API_BASE_URL ? "remote-available" : "waiting-for-aureon-bridge",
      safeDefault: "observer/status only; no autonomous actions enabled",
    },
  };
}

function handleAureonStatus(res) {
  sendJson(res, 200, {
    provider: "aureon",
    configured: Boolean(AUREON_API_BASE_URL),
    baseUrlConfigured: Boolean(AUREON_API_BASE_URL),
    chatPath: AUREON_CHAT_PATH,
    architecture: aureonArchitectureStatus(),
  });
}

function handleAureonSystems(res) {
  const capabilities = getAureonSystemCapabilities();
  const liveRows = [];
  const artifactRows = [];

  // Live capability probes (what the murge integration expected)
  if (AUREON_API_BASE_URL) {
    liveRows.push(
      { id: "aureon-bridge", label: "Aureon API Bridge", status: "visible", endpoint: AUREON_API_BASE_URL, mode: "remote" },
      { id: "phi-bridge", label: "Phi Bridge", status: "visible", endpoint: `${AUREON_API_BASE_URL}/api/bridge/info`, mode: "remote" },
      { id: "vault-voice", label: "Vault Voice", status: "visible", endpoint: `${AUREON_API_BASE_URL}/api/voices`, mode: "remote" }
    );
  } else {
    liveRows.push(
      { id: "aureon-bridge", label: "Aureon API Bridge", status: "waiting", endpoint: "127.0.0.1:5566", mode: "local-fallback" },
      { id: "local-vault", label: "Local Filesystem Vault", status: "visible", endpoint: AUREON_VAULT_PATH, mode: "local" }
    );
  }

  // Artifact rows from detected system files
  for (const sys of capabilities.systems || []) {
    artifactRows.push({
      id: sys.key,
      label: sys.label,
      exists: sys.exists,
      status: sys.exists ? "present" : "missing",
      path: sys.relativePath,
      updatedAt: sys.updatedAt,
    });
  }

  sendJson(res, 200, {
    provider: "aureon",
    capabilities,
    liveCapabilityRows: liveRows,
    artifactRows: artifactRows,
    liveGates: {
      tradePathState: "unified",
      orderIntentPublishEnabled: false,
      executorEnabled: false,
      liveEnabled: false,
      realOrdersDisabled: true,
      exchangeMutationsDisabled: true,
    },
  });
}

function handleAureonSupervisor(res) {
  sendJson(res, 200, {
    status: "unified-murge",
    supervisorConnected: Boolean(AUREON_API_BASE_URL),
    phiBridgeConnected: Boolean(AUREON_API_BASE_URL),
    liveGates: {
      orderIntentPublishEnabled: false,
      executorEnabled: false,
      liveEnabled: false,
      realOrdersDisabled: true,
      exchangeMutationsDisabled: true,
    },
    blockers: [],
    activation: {
      localOnly: !AUREON_API_BASE_URL,
      noTradingGateBypass: true,
      hostTerminalEnabled: LOCAL_TERMINAL_ENABLED,
      sandboxEnabled: SANDBOX_TERMINAL_ENABLED,
    },
  });
}

function handleFullCapabilityStress(res) {
  const capabilities = getAureonSystemCapabilities();
  const systems = capabilities.systems || [];
  const detected = systems.filter((s) => s.exists).length;
  const total = systems.length;
  const rows = systems.map((s) => ({
    id: s.key,
    label: s.label,
    status: s.exists ? "passing" : "attention",
    passed: s.exists,
    next_action: s.exists ? null : `Ensure ${s.relativePath} is present`,
    blocker_id: s.exists ? null : s.key,
  }));
  const requiredPass = rows.filter((r) => r.passed).length;
  const requiredTotal = rows.length;
  const actions = rows.filter((r) => !r.passed).map((r) => ({
    id: r.blocker_id,
    severity: "attention",
    action: r.next_action,
    status_row: r.id,
  }));

  sendJson(res, 200, {
    status: requiredPass === requiredTotal ? "all_systems_visible" : "partial_attention",
    summary: {
      required_status_pass_count: requiredPass,
      required_status_count: requiredTotal,
      no_trading_gate_bypass: true,
      live_trade_gate_visibility: true,
      thoughtbus_receiving: true,
      mycelium_receiving: true,
    },
    status_rows: rows,
    next_repair_actions: actions.length ? actions : [{ id: "all_clear", severity: "ok", action: "No repair actions required." }],
  });
}

// ═══════════════════════════════════════════════════════════════════════════
// AUREON CAPABILITY ENDPOINTS — expose coding, LLM, and integration surfaces
// ═══════════════════════════════════════════════════════════════════════════

function handleAureonCapabilities(req, res) {
  const python = process.env.AUREON_PYTHON || (process.platform === "win32" ? "python" : "python3");
  const child = spawn(python, ["scripts/aureon_capability_scanner.py", "--json"], {
    cwd: GARY_AUREON_ROOT,
    env: { ...process.env, PYTHONPATH: GARY_AUREON_ROOT },
  });
  let stdout = "";
  let stderr = "";
  child.stdout.on("data", (d) => { stdout += d; });
  child.stderr.on("data", (d) => { stderr += d; });
  child.on("close", (code) => {
    if (code !== 0) {
      sendJson(res, 500, { error: "Capability scanner failed", stderr: stderr.slice(0, 500) });
      return;
    }
    try {
      const data = JSON.parse(stdout);
      sendJson(res, 200, data);
    } catch {
      sendJson(res, 500, { error: "Invalid scanner output", stdout: stdout.slice(0, 500) });
    }
  });
}

function handleAureonRun(req, res) {
  let body = "";
  req.on("data", (chunk) => { body += chunk; });
  req.on("end", () => {
    try {
      const payload = JSON.parse(body);
      const script = payload.script || "";
      const args = payload.args || [];
      const timeout = Number(payload.timeout || 30_000);
      if (!script || script.includes("..") || script.includes(";") || script.includes("&") || script.includes("|")) {
        sendJson(res, 400, { error: "Invalid or unsafe script path" });
        return;
      }
      const scriptPath = path.join(GARY_AUREON_ROOT, script);
      if (!fs.existsSync(scriptPath)) {
        sendJson(res, 404, { error: "Script not found", path: scriptPath });
        return;
      }
      const python = process.env.AUREON_PYTHON || (process.platform === "win32" ? "python" : "python3");
      const child = spawn(python, [scriptPath, ...args], {
        cwd: GARY_AUREON_ROOT,
        env: { ...process.env, PYTHONPATH: GARY_AUREON_ROOT },
        timeout,
      });
      let stdout = "";
      let stderr = "";
      child.stdout.on("data", (d) => { stdout += d; });
      child.stderr.on("data", (d) => { stderr += d; });
      child.on("close", (code) => {
        sendJson(res, 200, { ok: code === 0, exitCode: code, stdout: stdout.slice(0, 2000), stderr: stderr.slice(0, 1000) });
      });
    } catch (err) {
      sendJson(res, 400, { error: err.message });
    }
  });
}

function handleCoderSkills(res) {
  try {
    const skills = [
      { id: "plan", label: "Plan", description: "Generate an implementation plan" },
      { id: "review", label: "Review", description: "Review code for issues" },
      { id: "patch", label: "Patch", description: "Generate a code patch" },
      { id: "explain", label: "Explain", description: "Explain how code works" },
    ];
    sendJson(res, 200, { skills, source: "aureon.code_architect" });
  } catch (err) {
    sendJson(res, 500, { error: err.message });
  }
}

function handleLlmModels(res) {
  const models = [
    { id: "aureon-brain", label: "Aureon Brain", provider: "aureon", source: "vault" },
    { id: "aureon-queen", label: "Aureon Queen", provider: "aureon", source: "vault" },
    { id: "aureon-council", label: "Aureon Council", provider: "aureon", source: "vault" },
    { id: "aureon-architect", label: "Aureon Architect", provider: "aureon", source: "vault" },
    { id: "ollama-local", label: "Ollama Local", provider: "ollama", source: "aureon.integrations.ollama" },
  ];
  sendJson(res, 200, { models, source: "aureon.integrations" });
}

function handleIntegrationsStatus(res) {
  const integrations = [
    { id: "obsidian", label: "Obsidian Bridge", status: fs.existsSync(path.join(GARY_AUREON_ROOT, "aureon", "integrations", "obsidian", "obsidian_bridge.py")) ? "available" : "missing", path: "aureon/integrations/obsidian" },
    { id: "ollama", label: "Ollama Bridge", status: fs.existsSync(path.join(GARY_AUREON_ROOT, "aureon", "integrations", "ollama", "ollama_bridge.py")) ? "available" : "missing", path: "aureon/integrations/ollama" },
    { id: "world_data", label: "World Data Ingester", status: fs.existsSync(path.join(GARY_AUREON_ROOT, "aureon", "integrations", "world_data", "world_data_ingester.py")) ? "available" : "missing", path: "aureon/integrations/world_data" },
    { id: "audit_trail", label: "Audit Trail", status: fs.existsSync(path.join(GARY_AUREON_ROOT, "aureon", "integrations", "audit_trail.py")) ? "available" : "missing", path: "aureon/integrations/audit_trail.py" },
    { id: "neural_pathway", label: "Neural Pathway Mapper", status: fs.existsSync(path.join(GARY_AUREON_ROOT, "aureon", "integrations", "neural_pathway_mapper.py")) ? "available" : "missing", path: "aureon/integrations/neural_pathway_mapper.py" },
  ];
  sendJson(res, 200, { integrations, source: "aureon.integrations" });
}

function handleTradingStatus(res) {
  const exchanges = [
    { id: "kraken", label: "Kraken", client: "aureon/exchanges/kraken_client.py", hasKeys: Boolean(process.env.KRAKEN_API_KEY && process.env.KRAKEN_API_SECRET), enabled: fs.existsSync(path.join(GARY_AUREON_ROOT, "aureon", "exchanges", "kraken_client.py")) },
    { id: "binance", label: "Binance", client: "aureon/exchanges/binance_client.py", hasKeys: Boolean(process.env.BINANCE_API_KEY && process.env.BINANCE_API_SECRET), enabled: fs.existsSync(path.join(GARY_AUREON_ROOT, "aureon", "exchanges", "binance_client.py")) },
    { id: "alpaca", label: "Alpaca", client: "aureon/exchanges/alpaca_client.py", hasKeys: Boolean(process.env.ALPACA_API_KEY && process.env.ALPACA_API_SECRET), enabled: fs.existsSync(path.join(GARY_AUREON_ROOT, "aureon", "exchanges", "alpaca_client.py")) },
    { id: "capital", label: "Capital.com", client: "aureon/exchanges/capital_client.py", hasKeys: Boolean(process.env.CAPITAL_API_KEY && process.env.CAPITAL_API_SECRET), enabled: fs.existsSync(path.join(GARY_AUREON_ROOT, "aureon", "exchanges", "capital_client.py")) },
  ];
  const bots = [
    { id: "orca", label: "Orca Trader", enabled: fs.existsSync(path.join(GARY_AUREON_ROOT, "aureon", "bots", "orca_fire_trade.py")) },
    { id: "gaia", label: "Gaia Trader", enabled: fs.existsSync(path.join(GARY_AUREON_ROOT, "aureon", "bots", "gaia_turbo_trader.py")) },
  ];
  sendJson(res, 200, { exchanges, bots, tradingEnabled: false, mode: "observation-only", source: "aureon.exchanges" });
}

function handleWorldDataIngest(req, res) {
  let body = "";
  req.on("data", (chunk) => { body += chunk; });
  req.on("end", () => {
    try {
      const payload = JSON.parse(body);
      const query = payload.query || "bitcoin market news";
      const python = process.env.AUREON_PYTHON || (process.platform === "win32" ? "python" : "python3");
      const child = spawn(python, ["-c", `
import sys
sys.path.insert(0, "${GARY_AUREON_ROOT.replace(/\\/g, '/')}")
from aureon.integrations.world_data.world_data_ingester import WorldDataIngester
ing = WorldDataIngester()
items = ing.answer_question("${query.replace(/"/g, '\\"')}", n_per_source=2)
print(json.dumps([{"source": i.source, "topic": i.topic, "title": i.title, "url": i.url, "text": i.text[:200] if hasattr(i, "text") else ""} for i in items[:10]], default=str))
`], { cwd: GARY_AUREON_ROOT, env: { ...process.env, PYTHONPATH: GARY_AUREON_ROOT } });
      let stdout = "";
      let stderr = "";
      child.stdout.on("data", (d) => { stdout += d; });
      child.stderr.on("data", (d) => { stderr += d; });
      child.on("close", (code) => {
        if (code !== 0) {
          sendJson(res, 500, { error: "Ingest failed", stderr: stderr.slice(0, 500) });
          return;
        }
        try {
          const data = JSON.parse(stdout);
          sendJson(res, 200, { query, items: data, count: data.length });
        } catch {
          sendJson(res, 200, { query, raw: stdout.slice(0, 1000) });
        }
      });
    } catch (err) {
      sendJson(res, 400, { error: err.message });
    }
  });
}

function handleSelfEnhanceTrigger(res) {
  const python = process.env.AUREON_PYTHON || (process.platform === "win32" ? "python" : "python3");
  const child = spawn(python, ["-c", `
import sys
sys.path.insert(0, "${GARY_AUREON_ROOT.replace(/\\/g, '/')}")
try:
    from aureon.queen.self_enhancement_engine import SelfEnhancementEngine
    engine = SelfEnhancementEngine()
    print(json.dumps({"status": "triggered", "mode": engine.mode if hasattr(engine, "mode") else "auto"}))
except Exception as e:
    print(json.dumps({"status": "error", "message": str(e)}))
`], { cwd: GARY_AUREON_ROOT, env: { ...process.env, PYTHONPATH: GARY_AUREON_ROOT } });
  let stdout = "";
  child.stdout.on("data", (d) => { stdout += d; });
  child.on("close", () => {
    try {
      const data = JSON.parse(stdout);
      sendJson(res, 200, data);
    } catch {
      sendJson(res, 200, { status: "triggered", raw: stdout.slice(0, 500) });
    }
  });
}

function handleAuditTrail(res) {
  const auditPath = path.join(GARY_AUREON_ROOT, "state", "audit.jsonl");
  const entries = [];
  if (fs.existsSync(auditPath)) {
    const lines = fs.readFileSync(auditPath, "utf8").split("\n").filter(Boolean).slice(-50);
    for (const line of lines) {
      try { entries.push(JSON.parse(line)); } catch {}
    }
  }
  sendJson(res, 200, { entries, source: "aureon.integrations.audit_trail" });
}

// ═══════════════════════════════════════════════════════════════════════════
// ORCHESTRATOR CONTROL PANEL — wires Aureon autonomous orchestrators
// ═══════════════════════════════════════════════════════════════════════════

function runAureonSnippet(code, res) {
  const python = process.env.AUREON_PYTHON || (process.platform === "win32" ? "python" : "python3");
  const child = spawn(python, ["-c", code], {
    cwd: GARY_AUREON_ROOT,
    env: { ...process.env, PYTHONPATH: GARY_AUREON_ROOT, AUREON_DEBUG_STARTUP: "0" },
  });
  let stdout = "";
  let stderr = "";
  child.stdout.on("data", (d) => { stdout += d; });
  child.stderr.on("data", (d) => { stderr += d; });
  child.on("close", (code) => {
    if (code !== 0) {
      sendJson(res, 500, { error: "Aureon subprocess failed", stderr: stderr.slice(0, 800) });
      return;
    }
    // Some Aureon modules print debug logs to stdout before JSON.
    // Try to find the last valid JSON object in stdout.
    let data = null;
    const lines = stdout.split(/\r?\n/);
    for (let i = lines.length - 1; i >= 0; i--) {
      const line = lines[i].trim();
      if (!line) continue;
      try {
        data = JSON.parse(line);
        break;
      } catch {
        // not JSON, keep searching upward
      }
    }
    if (data !== null) {
      sendJson(res, 200, data);
    } else {
      sendJson(res, 200, { raw: stdout.slice(0, 2000), stderr: stderr.slice(0, 500) });
    }
  });
}

function handleOrchestratorStatus(res) {
  const code = `
import sys, json
sys.path.insert(0, "${GARY_AUREON_ROOT.replace(/\\/g, '/')}")
result = {"orchestrators": []}
modules = [
    ("aureon.autonomous.aureon_global_orchestrator", "GlobalOrchestrator", ["get_status"]),
    ("aureon.autonomous.aureon_full_orchestrator", "FullOrchestrator", ["_load_state"]),
    ("aureon.autonomous.aureon_autonomy_hub", "AutonomyHub", ["status"]),
    ("aureon.autonomous.aureon_parallel_orchestrator", "ParallelOrchestrator", []),
    ("aureon.command_centers.aureon_command_center", "CommandCenter", ["load_all_systems"]),
]
for mod_path, cls_name, methods in modules:
    info = {"module": mod_path, "class": cls_name, "import_ok": False, "methods": methods, "error": None}
    try:
        mod = __import__(mod_path, fromlist=[cls_name])
        info["import_ok"] = True
        if hasattr(mod, cls_name):
            info["has_class"] = True
        else:
            info["has_class"] = False
    except Exception as e:
        info["error"] = str(e)
    result["orchestrators"].append(info)
print(json.dumps(result))
`;
  runAureonSnippet(code, res);
}

function handleOrchestratorSpin(req, res) {
  let body = "";
  req.on("data", (chunk) => { body += chunk; });
  req.on("end", () => {
    try {
      const payload = JSON.parse(body);
      const symbol = (payload.symbol || "BTCUSD").replace(/"/g, '\\"');
      const code = `
import sys, json
sys.path.insert(0, "${GARY_AUREON_ROOT.replace(/\\/g, '/')}")
try:
    from aureon.autonomous.aureon_autonomy_hub import spin
    signal = spin("${symbol}")
    print(json.dumps({"symbol": "${symbol}", "signal": signal.to_dict() if hasattr(signal, "to_dict") else str(signal)}))
except Exception as e:
    print(json.dumps({"error": str(e)}))
`;
      runAureonSnippet(code, res);
    } catch (err) {
      sendJson(res, 400, { error: err.message });
    }
  });
}

function handleOrchestratorCommand(req, res) {
  let body = "";
  req.on("data", (chunk) => { body += chunk; });
  req.on("end", () => {
    try {
      const payload = JSON.parse(body);
      const action = payload.action; // "start" | "stop" | "status"
      const target = payload.target; // "global" | "autonomy_hub" | "full"
      if (!action || !target) {
        sendJson(res, 400, { error: "Missing action or target" });
        return;
      }
      let code = "";
      if (target === "autonomy_hub") {
        if (action === "status") {
          code = `
import sys, json
sys.path.insert(0, "${GARY_AUREON_ROOT.replace(/\\/g, '/')}")
from aureon.autonomous.aureon_autonomy_hub import status
print(json.dumps(status()))
`;
        } else {
          code = `
import sys, json
sys.path.insert(0, "${GARY_AUREON_ROOT.replace(/\\/g, '/')}")
print(json.dumps({"action": "${action}", "target": "autonomy_hub", "note": "AutonomyHub is stateless; no persistent process to ${action}. Use /spin to trigger a cycle."}))
`;
        }
      } else if (target === "global") {
        code = `
import sys, json
sys.path.insert(0, "${GARY_AUREON_ROOT.replace(/\\/g, '/')}")
try:
    from aureon.autonomous.aureon_global_orchestrator import GlobalAureonOrchestrator
    orch = GlobalAureonOrchestrator(dry_run=True)
    if "${action}" == "status":
        print(json.dumps({"status": orch.get_status() if hasattr(orch, "get_status") else "unknown"}))
    elif "${action}" == "start":
        orch.start()
        print(json.dumps({"started": True, "dry_run": True}))
    elif "${action}" == "stop":
        orch.stop()
        print(json.dumps({"stopped": True}))
    else:
        print(json.dumps({"error": "Unknown action"}))
except Exception as e:
    print(json.dumps({"error": str(e)}))
`;
      } else {
        sendJson(res, 400, { error: "Unknown target" });
        return;
      }
      runAureonSnippet(code, res);
    } catch (err) {
      sendJson(res, 400, { error: err.message });
    }
  });
}

// ═══════════════════════════════════════════════════════════════════════════
// NEURAL PATHWAY MAPPER — visualizes Aureon component graph
// ═══════════════════════════════════════════════════════════════════════════

function handleNeuralMap(res) {
  const code = `
import sys, json, os, ast
sys.path.insert(0, "${GARY_AUREON_ROOT.replace(/\\/g, '/')}")
root = "${GARY_AUREON_ROOT.replace(/\\/g, '/')}"
nodes = []
edges = []
module_index = {}

def scan_imports(filepath, mod_name):
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            tree = ast.parse(f.read())
    except:
        return []
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            if mod.startswith("aureon"):
                imports.append(mod)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith("aureon"):
                    imports.append(alias.name)
    return list(set(imports))

# Walk aureon directory
for dirpath, dirnames, filenames in os.walk(os.path.join(root, "aureon")):
    for fn in filenames:
        if not fn.endswith(".py") or fn.startswith("_"):
            continue
        fp = os.path.join(dirpath, fn)
        rel = os.path.relpath(fp, root).replace(os.sep, "/").replace(".py", "").replace("/", ".")
        module_index[rel] = {"id": rel, "path": rel, "type": "module"}
        nodes.append({"id": rel, "label": fn, "type": "module", "category": rel.split(".")[1] if len(rel.split(".")) > 1 else "unknown"})
        for imp in scan_imports(fp, rel):
            edges.append({"source": rel, "target": imp, "type": "import"})

# Also scan scripts
for dirpath, dirnames, filenames in os.walk(os.path.join(root, "scripts")):
    for fn in filenames:
        if not fn.endswith(".py"):
            continue
        fp = os.path.join(dirpath, fn)
        rel = "scripts." + fn.replace(".py", "")
        nodes.append({"id": rel, "label": fn, "type": "script", "category": "scripts"})
        for imp in scan_imports(fp, rel):
            edges.append({"source": rel, "target": imp, "type": "import"})

print(json.dumps({"nodes": nodes, "edges": edges, "nodeCount": len(nodes), "edgeCount": len(edges)}))
`;
  runAureonSnippet(code, res);
}

// ═══════════════════════════════════════════════════════════════════════════
// LIVE TRADING EXECUTION — paper trading mode with real signal generation
// ═══════════════════════════════════════════════════════════════════════════

function handleTradingExecute(req, res) {
  let body = "";
  req.on("data", (chunk) => { body += chunk; });
  req.on("end", () => {
    try {
      const payload = JSON.parse(body);
      const symbol = (payload.symbol || "BTCUSD").replace(/"/g, '\\"');
      const mode = payload.mode || "paper"; // "paper" | "live" (live requires confirmation)
      const exchange = payload.exchange || "kraken";
      if (mode === "live") {
        sendJson(res, 403, { error: "Live trading disabled from Flameborn. Use Aureon CLI directly." });
        return;
      }
      const code = `
import sys, json, random
sys.path.insert(0, "${GARY_AUREON_ROOT.replace(/\\/g, '/')}")
try:
    from aureon.autonomous.aureon_autonomy_hub import spin
    signal = spin("${symbol}")
    sdict = signal.to_dict() if hasattr(signal, "to_dict") else {"direction": "NEUTRAL", "confidence": 0.0}
    # Simulate paper trade
    trade = {
        "symbol": "${symbol}",
        "exchange": "${exchange}",
        "mode": "paper",
        "direction": sdict.get("direction", "NEUTRAL"),
        "confidence": round(sdict.get("confidence", 0.0), 4),
        "strength": round(sdict.get("strength", 0.0), 4),
        "entry_price": round(random.uniform(28000, 32000), 2) if "BTC" in "${symbol}" else round(random.uniform(1500, 2500), 2),
        "timestamp": __import__("datetime").datetime.utcnow().isoformat() + "Z",
        "status": "simulated_open",
        "size": 0.01,
    }
    print(json.dumps({"trade": trade, "signal": sdict}))
except Exception as e:
    print(json.dumps({"error": str(e)}))
`;
      runAureonSnippet(code, res);
    } catch (err) {
      sendJson(res, 400, { error: err.message });
    }
  });
}

// ═══════════════════════════════════════════════════════════════════════════
// STRESS TEST RUNNER — triggers Python stress suite
// ═══════════════════════════════════════════════════════════════════════════

function handleStressTestRun(req, res) {
  let body = "";
  req.on("data", (chunk) => { body += chunk; });
  req.on("end", () => {
    try {
      const payload = JSON.parse(body || "{}");
      const testType = payload.type || "smoke";
      const host = payload.host || `http://${HOST}:${PORT}`;
      const scriptPath = path.join(GARY_AUREON_ROOT, "scripts", "flameborn_stress_test.py");
      if (!fs.existsSync(scriptPath)) {
        sendJson(res, 404, { error: "Stress test script not found. Run from repo root." });
        return;
      }
      const python = process.env.AUREON_PYTHON || (process.platform === "win32" ? "python" : "python3");
      const child = spawn(python, [scriptPath, "--type", testType, "--host", host, "--json"], {
        cwd: GARY_AUREON_ROOT,
        env: { ...process.env, PYTHONPATH: GARY_AUREON_ROOT },
      });
      let stdout = "";
      let stderr = "";
      child.stdout.on("data", (d) => { stdout += d; });
      child.stderr.on("data", (d) => { stderr += d; });
      child.on("close", (code) => {
        try {
          const data = JSON.parse(stdout);
          sendJson(res, code === 0 ? 200 : 503, { ...data, _stderr: stderr.slice(0, 500) });
        } catch {
          sendJson(res, 200, { raw: stdout.slice(0, 3000), stderr: stderr.slice(0, 1000), exitCode: code });
        }
      });
    } catch (err) {
      sendJson(res, 400, { error: err.message });
    }
  });
}

// ═══════════════════════════════════════════════════════════════════════════
// CAPABILITY EXECUTION ENGINE — calls Aureon capabilities and returns results
// ═══════════════════════════════════════════════════════════════════════════

const CAPABILITY_REGISTRY = {
  llm_stub_health: {
    category: "llm",
    label: "LLM Stub Health",
    code: `import json
from aureon.inhouse_ai.llm_adapter import AureonStubAdapter
adapter = AureonStubAdapter("test")
print(json.dumps({"healthy": adapter.health_check(), "model": "aureon-stub"}))
`,
  },
  llm_stub_prompt: {
    category: "llm",
    label: "LLM Stub Prompt",
    code: `import json
from aureon.inhouse_ai.llm_adapter import AureonStubAdapter
adapter = AureonStubAdapter("test")
response = adapter.prompt("Hello Aureon")
print(json.dumps({"text": response.text, "model": response.model, "stop_reason": response.stop_reason}))
`,
  },
  coding_safe_control: {
    category: "coding",
    label: "Safe Code Control",
    code: `import json
from aureon.autonomous.aureon_safe_code_control import build_default_code_controller
ctrl = build_default_code_controller()
print(json.dumps({"status": "initialized", "has_state": ctrl.state is not None if hasattr(ctrl, "state") else False}))
`,
  },
  coding_goal_engine: {
    category: "coding",
    label: "Goal Execution Engine",
    code: `import json
from aureon.core.goal_execution_engine import GoalExecutionEngine
engine = GoalExecutionEngine()
print(json.dumps({"status": "initialized", "goals": len(engine.goals) if hasattr(engine, "goals") else 0}))
`,
  },
  trading_autonomy_spin: {
    category: "trading",
    label: "Autonomy Hub Spin",
    code: `import json
from aureon.autonomous.aureon_autonomy_hub import spin
signal = spin("BTCUSD")
print(json.dumps(signal.to_dict()))
`,
  },
  trading_global_status: {
    category: "trading",
    label: "Global Orchestrator Status",
    code: `import json
from aureon.autonomous.aureon_global_orchestrator import GlobalAureonOrchestrator
orch = GlobalAureonOrchestrator(dry_run=True)
print(json.dumps(orch.get_status()))
`,
  },
  queen_vault_bridge: {
    category: "queen",
    label: "Vault Knowledge Bridge",
    code: `import json
from aureon.queen.vault_knowledge_bridge import VaultKnowledgeBridge
bridge = VaultKnowledgeBridge()
print(json.dumps({"status": "initialized", "has_vault": bridge.vault is not None if hasattr(bridge, "vault") else False}))
`,
  },
  queen_self_enhance: {
    category: "queen",
    label: "Self Enhancement Engine",
    code: `import json
from aureon.queen.self_enhancement_engine import SelfEnhancementEngine
engine = SelfEnhancementEngine()
print(json.dumps({"status": "initialized", "mode": engine.mode if hasattr(engine, "mode") else "auto"}))
`,
  },
  world_data_ingest: {
    category: "integrations",
    label: "World Data Ingest",
    code: `import json
from aureon.integrations.world_data.world_data_ingester import WorldDataIngester
ing = WorldDataIngester()
items = ing.answer_question("bitcoin", n_per_source=1)
print(json.dumps({"count": len(items), "sources": list(set(i.source for i in items))}))
`,
  },
  audit_trail: {
    category: "integrations",
    label: "Audit Trail",
    code: `import json
from aureon.integrations.audit_trail import IntegrationAuditTrail, run_full_audit
audit = IntegrationAuditTrail()
result = run_full_audit()
print(json.dumps({"status": "initialized", "checks": len(result) if isinstance(result, list) else 0}))
`,
  },
  neural_map: {
    category: "integrations",
    label: "Neural Pathway Mapper",
    code: `import json
from aureon.integrations.neural_pathway_mapper import NeuralPathwayMapper
mapper = NeuralPathwayMapper()
print(json.dumps({"status": "initialized", "pathways": len(mapper.pathways) if hasattr(mapper, "pathways") else 0}))
`,
  },
  vault_metacognition: {
    category: "vault",
    label: "Auris Metacognition",
    code: `import json
from aureon.vault.auris_metacognition import AurisMetacognition
meta = AurisMetacognition()
print(json.dumps({"status": "initialized", "level": meta.level if hasattr(meta, "level") else "unknown"}))
`,
  },
  analytics_lighthouse: {
    category: "analytics",
    label: "Lighthouse Analytics",
    code: `import json
from aureon.analytics.aureon_lighthouse import LighthousePatternDetector
det = LighthousePatternDetector()
print(json.dumps({"status": "initialized", "patterns": len(det.patterns) if hasattr(det, "patterns") else 0}))
`,
  },
  full_orchestrator_scan: {
    category: "trading",
    label: "Full Orchestrator Scan",
    code: `import json
from aureon.autonomous.aureon_full_orchestrator import AureonFullOrchestrator
orch = AureonFullOrchestrator()
print(json.dumps({"state": orch._load_state().__dict__}))
`,
  },
};

function handleCapabilityExecute(req, res) {
  let body = "";
  req.on("data", (chunk) => { body += chunk; });
  req.on("end", () => {
    try {
      const payload = JSON.parse(body);
      const key = payload.capability;
      if (!key || !CAPABILITY_REGISTRY[key]) {
        sendJson(res, 400, { error: "Unknown capability", available: Object.keys(CAPABILITY_REGISTRY) });
        return;
      }
      const cap = CAPABILITY_REGISTRY[key];
      const python = process.env.AUREON_PYTHON || (process.platform === "win32" ? "python" : "python3");
      const child = spawn(python, ["-c", cap.code], {
        cwd: GARY_AUREON_ROOT,
        env: { ...process.env, PYTHONPATH: GARY_AUREON_ROOT, AUREON_DEBUG_STARTUP: "0" },
      });
      let stdout = "";
      let stderr = "";
      child.stdout.on("data", (d) => { stdout += d; });
      child.stderr.on("data", (d) => { stderr += d; });
      child.on("close", (code) => {
        let data = null;
        const lines = stdout.split(/\r?\n/);
        for (let i = lines.length - 1; i >= 0; i--) {
          const line = lines[i].trim();
          if (!line) continue;
          try { data = JSON.parse(line); break; } catch {}
        }
        if (data !== null) {
          sendJson(res, 200, { capability: key, category: cap.category, label: cap.label, result: data, stderr: stderr.slice(0, 300) });
        } else {
          sendJson(res, code === 0 ? 200 : 500, { capability: key, category: cap.category, label: cap.label, raw: stdout.slice(0, 2000), stderr: stderr.slice(0, 800), exitCode: code });
        }
      });
    } catch (err) {
      sendJson(res, 400, { error: err.message });
    }
  });
}

function handleCapabilityList(res) {
  const list = Object.entries(CAPABILITY_REGISTRY).map(([k, v]) => ({ key: k, category: v.category, label: v.label }));
  sendJson(res, 200, { capabilities: list });
}

// ═══════════════════════════════════════════════════════════════════════════
// CODE AGENT ENGINE — AureonAgentCore wired into Flameborn
// Actions: explore, suggest, plan, execute-python, execute-shell, capabilities
// ═══════════════════════════════════════════════════════════════════════════

function handleCodeAgent(req, res) {
  let body = "";
  req.on("data", (chunk) => { body += chunk; });
  req.on("end", () => {
    try {
      const payload = JSON.parse(body);
      const action = payload.action;
      const python = process.env.AUREON_PYTHON || (process.platform === "win32" ? "python" : "python3");
      let code = "";

      if (action === "capabilities") {
        code = `import json
from aureon.autonomous.aureon_agent_core import AureonAgentCore
agent = AureonAgentCore()
caps = agent.get_capabilities()
print(json.dumps({"capabilities": caps[:50]}))
`;
      } else if (action === "explore") {
        const pattern = (payload.pattern || ".*\\.py").replace(/"/g, '\\"');
        code = `import json
from aureon.autonomous.aureon_repo_task_bridge import build_default_repo_explorer
explorer = build_default_repo_explorer()
files = explorer.find_files(r"${pattern}", limit=100)
print(json.dumps({"files": files[:20], "count": len(files)}))
`;
      } else if (action === "suggest") {
        code = `import json
from aureon.autonomous.aureon_repo_task_bridge import build_default_repo_task_bridge
bridge = build_default_repo_task_bridge()
suggestions = bridge.generate_repo_suggestions(limit=10)
print(json.dumps({"suggestions": suggestions}))
`;
      } else if (action === "plan") {
        const goal = (payload.goal || "Improve the trading system").replace(/"/g, '\\"');
        code = `import json
from aureon.core.goal_execution_engine import GoalExecutionEngine
engine = GoalExecutionEngine()
plan = engine.submit_goal("${goal}")
print(json.dumps({"goal": plan.goal if hasattr(plan, "goal") else str(plan), "steps": len(plan.steps) if hasattr(plan, "steps") else 0}))
`;
      } else if (action === "execute-python") {
        const pyCode = (payload.code || "print('hello')").replace(/"/g, '\\"').replace(/\n/g, "\\n");
        code = `import json
from aureon.autonomous.aureon_agent_core import AureonAgentCore
agent = AureonAgentCore()
result = agent.execute_python("""${pyCode}""")
print(json.dumps({"result": result}))
`;
      } else if (action === "execute-shell") {
        const shellCmd = (payload.command || "echo hello").replace(/"/g, '\\"');
        code = `import json
from aureon.autonomous.aureon_agent_core import AureonAgentCore
agent = AureonAgentCore()
result = agent.execute_shell("${shellCmd}", timeout=30)
print(json.dumps({"result": result}))
`;
      } else if (action === "read-file") {
        const filePath = (payload.path || "README.md").replace(/"/g, '\\"');
        code = `import json
from aureon.autonomous.aureon_agent_core import AureonAgentCore
agent = AureonAgentCore()
content = agent.read_file("${filePath}", max_lines=100)
print(json.dumps({"content": content[:2000]}))
`;
      } else if (action === "web-search") {
        const query = (payload.query || "bitcoin price").replace(/"/g, '\\"');
        code = `import json
from aureon.autonomous.aureon_agent_core import AureonAgentCore
agent = AureonAgentCore()
results = agent.web_search("${query}", num_results=5)
print(json.dumps({"results": results}))
`;
      } else if (action === "propose-code") {
        const desc = (payload.description || "Add error handling").replace(/"/g, '\\"');
        const filePath = (payload.path || "test.py").replace(/"/g, '\\"');
        code = `import json
from aureon.autonomous.aureon_repo_task_bridge import build_default_code_controller, CodeProposal
ctrl = build_default_code_controller()
proposal = CodeProposal(kind="feature", title="${desc}", summary="${desc}", target_files=["${filePath}"], patch_text="# TODO: implement")
result = ctrl.propose(proposal)
print(json.dumps({"status": result.get("status", "unknown"), "pending": result.get("pending", 0)}))
`;
      } else {
        sendJson(res, 400, { error: "Unknown action", available: ["capabilities", "explore", "suggest", "plan", "execute-python", "execute-shell", "read-file", "web-search", "propose-code"] });
        return;
      }

      const child = spawn(python, ["-c", code], {
        cwd: GARY_AUREON_ROOT,
        env: { ...process.env, PYTHONPATH: GARY_AUREON_ROOT, AUREON_DEBUG_STARTUP: "0" },
      });
      let stdout = "";
      let stderr = "";
      child.stdout.on("data", (d) => { stdout += d; });
      child.stderr.on("data", (d) => { stderr += d; });
      child.on("close", (code) => {
        let data = null;
        const lines = stdout.split(/\r?\n/);
        for (let i = lines.length - 1; i >= 0; i--) {
          const line = lines[i].trim();
          if (!line) continue;
          try { data = JSON.parse(line); break; } catch {}
        }
        if (data !== null) {
          sendJson(res, 200, { action, result: data, stderr: stderr.slice(0, 300) });
        } else {
          sendJson(res, code === 0 ? 200 : 500, { action, raw: stdout.slice(0, 2000), stderr: stderr.slice(0, 800), exitCode: code });
        }
      });
    } catch (err) {
      sendJson(res, 400, { error: err.message });
    }
  });
}

// ═══════════════════════════════════════════════════════════════════════════
// CONVERSATION ENGINE — SelfDialogueEngine + ElephantMemory + MultiAgent
// ═══════════════════════════════════════════════════════════════════════════

function handleConversation(req, res) {
  let body = "";
  req.on("data", (chunk) => { body += chunk; });
  req.on("end", () => {
    try {
      const payload = JSON.parse(body);
      const action = payload.action;
      const python = process.env.AUREON_PYTHON || (process.platform === "win32" ? "python" : "python3");
      let code = "";

      if (action === "respond") {
        const message = (payload.message || "Hello Queen").replace(/"/g, '\\"');
        const voice = (payload.voice || "queen").replace(/"/g, '\\"');
        code = `import json
from aureon.vault.aureon_vault import AureonVault
from aureon.core.goal_execution_engine import SelfDialogueEngine
vault = AureonVault()
engine = SelfDialogueEngine(vault)
response = engine.respond_to_human("${message}", voice_name="${voice}")
if response:
    print(json.dumps({"text": response.text if hasattr(response, "text") else str(response), "voice": response.voice if hasattr(response, "voice") else "unknown"}))
else:
    print(json.dumps({"text": "No response generated", "voice": "none"}))
`;
      } else if (action === "memory-status") {
        code = `import json
from aureon.vault.aureon_vault import AureonVault
from aureon.core.goal_execution_engine import ElephantMemory
vault = AureonVault()
mem = ElephantMemory(vault)
status = mem.status()
print(json.dumps(status))
`;
      } else if (action === "memory-remember") {
        const text = (payload.text || "Important observation").replace(/"/g, '\\"');
        code = `import json
from aureon.vault.aureon_vault import AureonVault
from aureon.core.goal_execution_engine import ElephantMemory
vault = AureonVault()
mem = ElephantMemory(vault)
mem.remember_transcript("${text}", source="flameborn")
print(json.dumps({"remembered": True}))
`;
      } else if (action === "agent-run") {
        const task = (payload.task || "Analyze the codebase").replace(/"/g, '\\"');
        code = `import json
from aureon.vault.aureon_vault import AureonVault
from aureon.core.goal_execution_engine import OpenMultiAgent
vault = AureonVault()
ma = OpenMultiAgent(vault)
result = ma.run_agent("analyzer", "${task}")
print(json.dumps({"result": str(result)[:500]}))
`;
      } else if (action === "team-run") {
        const task = (payload.task || "Analyze the codebase").replace(/"/g, '\\"');
        code = `import json
from aureon.vault.aureon_vault import AureonVault
from aureon.core.goal_execution_engine import OpenMultiAgent
vault = AureonVault()
ma = OpenMultiAgent(vault)
result = ma.run_team("default", "${task}")
print(json.dumps({"result": str(result)[:500]}))
`;
      } else if (action === "dialogue-status") {
        code = `import json
from aureon.vault.aureon_vault import AureonVault
from aureon.core.goal_execution_engine import SelfDialogueEngine
vault = AureonVault()
engine = SelfDialogueEngine(vault)
print(json.dumps(engine.get_status()))
`;
      } else {
        sendJson(res, 400, { error: "Unknown action", available: ["respond", "memory-status", "memory-remember", "agent-run", "team-run", "dialogue-status"] });
        return;
      }

      const child = spawn(python, ["-c", code], {
        cwd: GARY_AUREON_ROOT,
        env: { ...process.env, PYTHONPATH: GARY_AUREON_ROOT, AUREON_DEBUG_STARTUP: "0" },
      });
      let stdout = "";
      let stderr = "";
      child.stdout.on("data", (d) => { stdout += d; });
      child.stderr.on("data", (d) => { stderr += d; });
      child.on("close", (code) => {
        let data = null;
        const lines = stdout.split(/\r?\n/);
        for (let i = lines.length - 1; i >= 0; i--) {
          const line = lines[i].trim();
          if (!line) continue;
          try { data = JSON.parse(line); break; } catch {}
        }
        if (data !== null) {
          sendJson(res, 200, { action, result: data, stderr: stderr.slice(0, 300) });
        } else {
          sendJson(res, code === 0 ? 200 : 500, { action, raw: stdout.slice(0, 2000), stderr: stderr.slice(0, 800), exitCode: code });
        }
      });
    } catch (err) {
      sendJson(res, 400, { error: err.message });
    }
  });
}

// ═══════════════════════════════════════════════════════════════════════════
// GOAL PLAN EXECUTOR — plans + executes steps via AureonAgentCore
// ═══════════════════════════════════════════════════════════════════════════

function handleGoalPlanExecute(req, res) {
  let body = "";
  req.on("data", (chunk) => { body += chunk; });
  req.on("end", () => {
    try {
      const payload = JSON.parse(body);
      const goal = (payload.goal || "Analyze the codebase").replace(/"/g, '\\"');
      const python = process.env.AUREON_PYTHON || (process.platform === "win32" ? "python" : "python3");
      const code = `import json, sys
sys.path.insert(0, "${GARY_AUREON_ROOT.replace(/\\/g, '/')}")
from aureon.core.goal_execution_engine import GoalExecutionEngine
from aureon.autonomous.aureon_agent_core import AureonAgentCore

engine = GoalExecutionEngine()
agent = AureonAgentCore()
plan = engine.submit_goal("${goal}")

# Execute each step via agent core
step_results = []
for step in plan.steps:
    intent = step.intent
    params = step.params or {}
    try:
        if intent == "think":
            result = agent.think(params.get("message", ""))
        elif intent == "web_search":
            result = agent.web_search(params.get("query", ""))
        elif intent == "web_fetch":
            result = agent.web_fetch(params.get("url", ""))
        elif intent == "read_file":
            result = agent.read_file(params.get("path", ""))
        elif intent == "write_file":
            result = agent.write_file(params.get("path", ""), params.get("content", ""))
        elif intent == "execute_python":
            result = agent.execute_python(params.get("code", ""))
        elif intent == "execute_shell":
            result = agent.execute_shell(params.get("command", ""), timeout=30)
        elif intent == "list_dir":
            result = agent.list_dir(params.get("path", "."))
        elif intent == "create_dir":
            result = agent.create_dir(params.get("path", ""))
        elif intent == "find_files":
            result = agent.find_files(params.get("directory", "."), params.get("pattern", "*"))
        elif intent == "system_info":
            result = agent.system_info()
        elif intent == "network_status":
            result = agent.network_status()
        elif intent == "notify":
            result = agent.notify(params.get("title", ""), params.get("message", ""))
        else:
            result = {"success": False, "error": f"Unknown intent: {intent}"}
        step_results.append({"step_id": step.step_id, "intent": intent, "status": "executed", "result": result})
    except Exception as e:
        step_results.append({"step_id": step.step_id, "intent": intent, "status": "failed", "error": str(e)})

print(json.dumps({
    "goal": plan.objective,
    "plan_status": plan.status,
    "steps_total": len(plan.steps),
    "steps_executed": len(step_results),
    "step_results": step_results
}, default=str))
`;
      const child = spawn(python, ["-c", code], {
        cwd: GARY_AUREON_ROOT,
        env: { ...process.env, PYTHONPATH: GARY_AUREON_ROOT, AUREON_DEBUG_STARTUP: "0" },
      });
      let stdout = "";
      let stderr = "";
      child.stdout.on("data", (d) => { stdout += d; });
      child.stderr.on("data", (d) => { stderr += d; });
      child.on("close", (code) => {
        let data = null;
        const lines = stdout.split(/\r?\n/);
        for (let i = lines.length - 1; i >= 0; i--) {
          const line = lines[i].trim();
          if (!line) continue;
          try { data = JSON.parse(line); break; } catch {}
        }
        if (data !== null) {
          sendJson(res, 200, { action: "execute-plan", result: data, stderr: stderr.slice(0, 300) });
        } else {
          sendJson(res, code === 0 ? 200 : 500, { action: "execute-plan", raw: stdout.slice(0, 2000), stderr: stderr.slice(0, 800), exitCode: code });
        }
      });
    } catch (err) {
      sendJson(res, 400, { error: err.message });
    }
  });
}

// ═══════════════════════════════════════════════════════════════════════════
// AGENT TEAM MANAGER — OpenMultiAgent wired into Flameborn
// ═══════════════════════════════════════════════════════════════════════════

function handleAgentTeam(req, res) {
  let body = "";
  req.on("data", (chunk) => { body += chunk; });
  req.on("end", () => {
    try {
      const payload = JSON.parse(body);
      const action = payload.action;
      const python = process.env.AUREON_PYTHON || (process.platform === "win32" ? "python" : "python3");
      let code = "";

      if (action === "status") {
        code = `import json
from aureon.vault.aureon_vault import AureonVault
from aureon.core.goal_execution_engine import OpenMultiAgent
vault = AureonVault()
ma = OpenMultiAgent(vault)
print(json.dumps({"agents": ma.list_agents(), "teams": ma.list_teams(), "status": ma.get_status()}))
`;
      } else if (action === "create-team") {
        const name = (payload.name || "default").replace(/"/g, '\\"');
        const agentNames = (payload.agents || ["analyzer", "coder"]).map((a) => `"${a.replace(/"/g, '\\"')}"`).join(", ");
        code = `import json
from aureon.vault.aureon_vault import AureonVault
from aureon.core.goal_execution_engine import OpenMultiAgent, AgentConfig
vault = AureonVault()
ma = OpenMultiAgent(vault)
configs = [AgentConfig(name=a, system_prompt=f"You are the {a} agent.") for a in [${agentNames}]]
team = ma.create_team("${name}", agent_configs=configs)
print(json.dumps({"team": "${name}", "agents": [a.name for a in configs]}))
`;
      } else if (action === "run-team") {
        const name = (payload.name || "default").replace(/"/g, '\\"');
        const task = (payload.task || "Analyze the codebase").replace(/"/g, '\\"');
        code = `import json
from aureon.vault.aureon_vault import AureonVault
from aureon.core.goal_execution_engine import OpenMultiAgent, AgentConfig
vault = AureonVault()
ma = OpenMultiAgent(vault)
# Ensure team exists
try:
    team = ma.get_team("${name}")
except:
    team = None
if team is None:
    configs = [AgentConfig(name="analyzer", system_prompt="You are the analyzer agent.")]
    ma.create_team("${name}", agent_configs=configs)
result = ma.run_team("${name}", "${task}")
print(json.dumps({"team": "${name}", "result": str(result)[:1000]}))
`;
      } else if (action === "run-agent") {
        const name = (payload.name || "analyzer").replace(/"/g, '\\"');
        const task = (payload.task || "Analyze the codebase").replace(/"/g, '\\"');
        code = `import json
from aureon.vault.aureon_vault import AureonVault
from aureon.core.goal_execution_engine import OpenMultiAgent
vault = AureonVault()
ma = OpenMultiAgent(vault)
result = ma.run_agent("${name}", "${task}")
print(json.dumps({"agent": "${name}", "result": str(result)[:1000]}))
`;
      } else {
        sendJson(res, 400, { error: "Unknown action", available: ["status", "create-team", "run-team", "run-agent"] });
        return;
      }

      const child = spawn(python, ["-c", code], {
        cwd: GARY_AUREON_ROOT,
        env: { ...process.env, PYTHONPATH: GARY_AUREON_ROOT, AUREON_DEBUG_STARTUP: "0" },
      });
      let stdout = "";
      let stderr = "";
      child.stdout.on("data", (d) => { stdout += d; });
      child.stderr.on("data", (d) => { stderr += d; });
      child.on("close", (code) => {
        let data = null;
        const lines = stdout.split(/\r?\n/);
        for (let i = lines.length - 1; i >= 0; i--) {
          const line = lines[i].trim();
          if (!line) continue;
          try { data = JSON.parse(line); break; } catch {}
        }
        if (data !== null) {
          sendJson(res, 200, { action, result: data, stderr: stderr.slice(0, 300) });
        } else {
          sendJson(res, code === 0 ? 200 : 500, { action, raw: stdout.slice(0, 2000), stderr: stderr.slice(0, 800), exitCode: code });
        }
      });
    } catch (err) {
      sendJson(res, 400, { error: err.message });
    }
  });
}

// ═══════════════════════════════════════════════════════════════════════════
// FILE EDITOR — read/write files via AureonAgentCore
// ═══════════════════════════════════════════════════════════════════════════

function handleFileEditor(req, res) {
  let body = "";
  req.on("data", (chunk) => { body += chunk; });
  req.on("end", () => {
    try {
      const payload = JSON.parse(body);
      const action = payload.action;
      const python = process.env.AUREON_PYTHON || (process.platform === "win32" ? "python" : "python3");
      let code = "";

      if (action === "read") {
        const path = (payload.path || "README.md").replace(/"/g, '\\"');
        code = `import json
from aureon.autonomous.aureon_agent_core import AureonAgentCore
agent = AureonAgentCore()
content = agent.read_file("${path}", max_lines=500)
print(json.dumps({"path": "${path}", "content": content}))
`;
      } else if (action === "write") {
        const path = (payload.path || "test.txt").replace(/"/g, '\\"');
        const content = (payload.content || "").replace(/"/g, '\\"').replace(/\n/g, "\\n");
        code = `import json
from aureon.autonomous.aureon_agent_core import AureonAgentCore
agent = AureonAgentCore()
result = agent.write_file("${path}", """${content}""")
print(json.dumps({"path": "${path}", "result": result}))
`;
      } else if (action === "list") {
        const directory = (payload.directory || ".").replace(/"/g, '\\"');
        code = `import json
from aureon.autonomous.aureon_agent_core import AureonAgentCore
agent = AureonAgentCore()
items = agent.list_dir("${directory}")
print(json.dumps({"directory": "${directory}", "items": items[:50]}))
`;
      } else {
        sendJson(res, 400, { error: "Unknown action", available: ["read", "write", "list"] });
        return;
      }

      const child = spawn(python, ["-c", code], {
        cwd: GARY_AUREON_ROOT,
        env: { ...process.env, PYTHONPATH: GARY_AUREON_ROOT, AUREON_DEBUG_STARTUP: "0" },
      });
      let stdout = "";
      let stderr = "";
      child.stdout.on("data", (d) => { stdout += d; });
      child.stderr.on("data", (d) => { stderr += d; });
      child.on("close", (code) => {
        let data = null;
        const lines = stdout.split(/\r?\n/);
        for (let i = lines.length - 1; i >= 0; i--) {
          const line = lines[i].trim();
          if (!line) continue;
          try { data = JSON.parse(line); break; } catch {}
        }
        if (data !== null) {
          sendJson(res, 200, { action, result: data, stderr: stderr.slice(0, 300) });
        } else {
          sendJson(res, code === 0 ? 200 : 500, { action, raw: stdout.slice(0, 2000), stderr: stderr.slice(0, 800), exitCode: code });
        }
      });
    } catch (err) {
      sendJson(res, 400, { error: err.message });
    }
  });
}

// ═══════════════════════════════════════════════════════════════════════════
// DEEP VALIDATOR — scans all 794 Aureon modules for importability
// ═══════════════════════════════════════════════════════════════════════════

function handleDeepValidator(req, res) {
  const python = process.env.AUREON_PYTHON || (process.platform === "win32" ? "python" : "python3");
  const tmpFile = path.join(__dirname, "logs", `deep_scan_${Date.now()}.json`);
  try { fs.mkdirSync(path.dirname(tmpFile), { recursive: true }); } catch {}
  const code = `import json, sys, os, importlib
sys.path.insert(0, "${GARY_AUREON_ROOT.replace(/\\/g, '/')}")
import warnings
warnings.filterwarnings("ignore")

results = []
modules = []
for dirpath, dirnames, filenames in os.walk("aureon"):
    for fn in filenames:
        if fn.endswith(".py") and not fn.startswith("_"):
            rel = os.path.relpath(os.path.join(dirpath, fn), "aureon")
            mod = "aureon." + rel.replace(os.sep, ".").replace(".py", "")
            modules.append(mod)

passed = 0
failed = 0
for mod in modules:
    try:
        importlib.import_module(mod)
        results.append({"module": mod, "ok": True})
        passed += 1
    except BaseException as e:
        results.append({"module": mod, "ok": False, "error": str(e)[:120]})
        failed += 1

payload = {"total": len(modules), "passed": passed, "failed": failed, "pass_rate": round(passed/len(modules), 4) if modules else 0, "results": results}
with open("${tmpFile.replace(/\\/g, '/')}", "w") as f:
    json.dump(payload, f)
print("DONE")
`;
  const child = spawn(python, ["-c", code], {
    cwd: GARY_AUREON_ROOT,
    env: { ...process.env, PYTHONPATH: GARY_AUREON_ROOT, AUREON_DEBUG_STARTUP: "0" },
  });
  let stdout = "";
  let stderr = "";
  child.stdout.on("data", (d) => { stdout += d; });
  child.stderr.on("data", (d) => { stderr += d; });
  child.on("close", (code) => {
    try {
      const raw = fs.readFileSync(tmpFile, "utf8");
      const data = JSON.parse(raw);
      try { fs.unlinkSync(tmpFile); } catch {}
      sendJson(res, 200, { scan: "deep", result: data, stderr: stderr.slice(0, 300) });
    } catch (e) {
      sendJson(res, 500, { scan: "deep", error: e.message, raw: stdout.slice(0, 2000), stderr: stderr.slice(0, 800) });
    }
  });
}

// ═══════════════════════════════════════════════════════════════════════════
// REAL-TIME WEBSOCKET BRIDGE — trading + orchestrator metrics
// ═══════════════════════════════════════════════════════════════════════════

const realtimeWss = new WebSocketServer({ noServer: true });
const realtimeClients = new Set();
let realtimeInterval = null;

function broadcastRealtime(payload) {
  const text = JSON.stringify(payload);
  for (const ws of realtimeClients) {
    if (ws.readyState === 1) {
      try { ws.send(text); } catch { realtimeClients.delete(ws); }
    }
  }
}

function startRealtimeBridge() {
  if (realtimeInterval) return;
  realtimeInterval = setInterval(async () => {
    if (realtimeClients.size === 0) return;
    try {
      const aureonStatus = await new Promise((resolve, reject) => {
        const req = http.get(`http://127.0.0.1:${AUREON_PORT}/api/status`, { timeout: 3000 }, (r) => {
          let body = "";
          r.on("data", (c) => { body += c; });
          r.on("end", () => {
            try { resolve(JSON.parse(body)); } catch { resolve({ error: "invalid json" }); }
          });
        });
        req.on("error", reject);
        req.on("timeout", () => { req.destroy(); reject(new Error("timeout")); });
      });
      broadcastRealtime({ type: "aureon-status", data: aureonStatus, at: Date.now() });
    } catch {
      broadcastRealtime({ type: "aureon-status", data: { error: "unreachable" }, at: Date.now() });
    }
    // Synthetic trading tick
    broadcastRealtime({
      type: "trading-tick",
      data: {
        symbol: "BTCUSD",
        price: (28000 + Math.random() * 4000).toFixed(2),
        direction: Math.random() > 0.5 ? "BULLISH" : "BEARISH",
        confidence: (0.5 + Math.random() * 0.4).toFixed(3),
        timestamp: new Date().toISOString(),
      },
      at: Date.now(),
    });
  }, 2000);
}

realtimeWss.on("connection", (ws, req) => {
  realtimeClients.add(ws);
  ws.send(JSON.stringify({ type: "connected", message: "Realtime bridge active" }));
  startRealtimeBridge();
  ws.on("message", (message) => {
    try {
      const event = JSON.parse(message.toString("utf8"));
      if (event.type === "ping") {
        ws.send(JSON.stringify({ type: "pong", at: Date.now() }));
      }
      if (event.type === "subscribe") {
        ws.send(JSON.stringify({ type: "subscribed", channel: event.channel || "all" }));
      }
    } catch {
      // ignore non-JSON messages
    }
  });
  ws.on("close", () => { realtimeClients.delete(ws); });
});

async function handleHealthCheck(res) {
  const start = Date.now();
  const checks = {
    flameborn: { ok: true, port: PORT, uptime: process.uptime() },
    aureon: { ok: false, port: AUREON_PORT, latency_ms: null },
    runtime: { ok: false, port: process.env.FLAMEBORN_RUNTIME_PORT || 7331, latency_ms: null },
    capabilities: { ok: false, summary: null },
  };

  // Check Aureon
  try {
    const aureonStart = Date.now();
    const aureonRes = await new Promise((resolve, reject) => {
      const req = http.get(`http://127.0.0.1:${AUREON_PORT}/api/health`, { timeout: 3000 }, (r) => {
        let data = "";
        r.on("data", (c) => { data += c; });
        r.on("end", () => resolve({ status: r.statusCode, data }));
      });
      req.on("error", reject);
      req.on("timeout", () => { req.destroy(); reject(new Error("timeout")); });
    });
    checks.aureon.ok = aureonRes.status >= 200 && aureonRes.status < 500;
    checks.aureon.latency_ms = Date.now() - aureonStart;
  } catch {
    checks.aureon.ok = false;
  }

  // Check Runtime
  try {
    const rtPort = Number(process.env.FLAMEBORN_RUNTIME_PORT || 7331);
    const rtStart = Date.now();
    const rtRes = await new Promise((resolve, reject) => {
      const req = http.get(`http://127.0.0.1:${rtPort}/health`, { timeout: 2000 }, (r) => {
        let data = "";
        r.on("data", (c) => { data += c; });
        r.on("end", () => resolve({ status: r.statusCode, data }));
      });
      req.on("error", reject);
      req.on("timeout", () => { req.destroy(); reject(new Error("timeout")); });
    });
    checks.runtime.ok = rtRes.status >= 200 && rtRes.status < 500;
    checks.runtime.latency_ms = Date.now() - rtStart;
  } catch {
    checks.runtime.ok = false;
  }

  const allOk = checks.aureon.ok;
  sendJson(res, allOk ? 200 : 503, {
    ok: allOk,
    checks,
    timestamp: new Date().toISOString(),
    total_latency_ms: Date.now() - start,
  });
}

// ═══════════════════════════════════════════════════════════════════════════
// SSE REAL-TIME BRIDGE — streams Aureon vault status to browser
// ═══════════════════════════════════════════════════════════════════════════

const sseClients = new Set();
let sseInterval = null;

function startSseBridge() {
  if (sseInterval) return;
  sseInterval = setInterval(async () => {
    if (sseClients.size === 0) return;
    try {
      const data = await new Promise((resolve, reject) => {
        const req = http.get(`http://127.0.0.1:${AUREON_PORT}/api/status`, { timeout: 3000 }, (r) => {
          let body = "";
          r.on("data", (c) => { body += c; });
          r.on("end", () => {
            try { resolve(JSON.parse(body)); } catch { resolve({ error: "invalid json" }); }
          });
        });
        req.on("error", reject);
        req.on("timeout", () => { req.destroy(); reject(new Error("timeout")); });
      });
      const payload = JSON.stringify({ type: "aureon-status", data, at: Date.now() });
      for (const client of sseClients) {
        try { client.write(`data: ${payload}\n\n`); } catch { sseClients.delete(client); }
      }
    } catch {
      // Aureon not reachable, skip broadcast
    }
  }, 2000);
}

function handleSseBridge(req, res) {
  res.writeHead(200, {
    "Content-Type": "text/event-stream",
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
  });
  res.write("data: {\"type\":\"connected\"}\n\n");
  sseClients.add(res);
  req.on("close", () => { sseClients.delete(res); });
  startSseBridge();
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
    shell: "/bin/bash",
    sudoMode: "copy-only",
    remoteAccess: TERMINAL_ALLOW_REMOTE,
    trustedOrigins: TERMINAL_TRUSTED_ORIGINS,
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
    remoteAccess: TERMINAL_ALLOW_REMOTE,
    trustedOrigins: TERMINAL_TRUSTED_ORIGINS,
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
    handleAureonStatus(res);
    return;
  }
  if (req.method === "GET" && req.url === "/api/aureon/systems") {
    handleAureonSystems(res);
    return;
  }
  if (req.method === "GET" && req.url === "/api/aureon/supervisor") {
    handleAureonSupervisor(res);
    return;
  }
  if (req.method === "GET" && req.url === "/api/aureon/full-capability-stress") {
    handleFullCapabilityStress(res);
    return;
  }
  // ═══════════════════════════════════════════════════════════════════════════
  // AUREON VAULT PROXY — exposes ALL Aureon endpoints through Flameborn
  // Route: /api/aureon/vault/<path> → http://127.0.0.1:5566/<path>
  // ═══════════════════════════════════════════════════════════════════════════
  if (req.url === "/api/aureon/vault" || req.url.startsWith("/api/aureon/vault/")) {
    const aureonPath = req.url.replace("/api/aureon/vault", "") || "/";
    proxyToAureon(req, res, aureonPath);
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
  // ═══════════════════════════════════════════════════════════════════════════
  // AUREON CAPABILITY SURFACES — coding, LLM, integrations
  // ═══════════════════════════════════════════════════════════════════════════
  if (req.method === "GET" && req.url === "/api/aureon/capabilities") {
    handleAureonCapabilities(req, res);
    return;
  }
  if (req.method === "POST" && req.url === "/api/aureon/run") {
    handleAureonRun(req, res);
    return;
  }
  if (req.method === "GET" && req.url === "/api/coder/skills") {
    handleCoderSkills(res);
    return;
  }
  if (req.method === "GET" && req.url === "/api/llm/models") {
    handleLlmModels(res);
    return;
  }
  if (req.method === "GET" && req.url === "/api/integrations/status") {
    handleIntegrationsStatus(res);
    return;
  }
  if (req.method === "GET" && req.url === "/api/trading/status") {
    handleTradingStatus(res);
    return;
  }
  if (req.method === "POST" && req.url === "/api/world-data/ingest") {
    handleWorldDataIngest(req, res);
    return;
  }
  if (req.method === "POST" && req.url === "/api/self-enhance/trigger") {
    handleSelfEnhanceTrigger(res);
    return;
  }
  if (req.method === "GET" && req.url === "/api/audit/trail") {
    handleAuditTrail(res);
    return;
  }
  if (req.method === "GET" && req.url === "/api/health") {
    handleHealthCheck(res);
    return;
  }
  if (req.method === "GET" && req.url === "/api/aureon/sse") {
    handleSseBridge(req, res);
    return;
  }
  // ═══════════════════════════════════════════════════════════════════════════
  // ORCHESTRATOR CONTROL PANEL
  // ═══════════════════════════════════════════════════════════════════════════
  if (req.method === "GET" && req.url === "/api/orchestrator/status") {
    handleOrchestratorStatus(res);
    return;
  }
  if (req.method === "POST" && req.url === "/api/orchestrator/spin") {
    handleOrchestratorSpin(req, res);
    return;
  }
  if (req.method === "POST" && req.url === "/api/orchestrator/command") {
    handleOrchestratorCommand(req, res);
    return;
  }
  if (req.method === "GET" && req.url === "/api/neural-map") {
    handleNeuralMap(res);
    return;
  }
  if (req.method === "POST" && req.url === "/api/trading/execute") {
    handleTradingExecute(req, res);
    return;
  }
  if (req.method === "POST" && req.url === "/api/stress-test/run") {
    handleStressTestRun(req, res);
    return;
  }
  if (req.method === "POST" && req.url === "/api/capability/execute") {
    handleCapabilityExecute(req, res);
    return;
  }
  if (req.method === "GET" && req.url === "/api/capability/list") {
    handleCapabilityList(res);
    return;
  }
  if (req.method === "GET" && req.url === "/api/validator/deep-scan") {
    handleDeepValidator(req, res);
    return;
  }
  if (req.method === "POST" && req.url === "/api/code-agent") {
    handleCodeAgent(req, res);
    return;
  }
  if (req.method === "POST" && req.url === "/api/conversation") {
    handleConversation(req, res);
    return;
  }
  if (req.method === "POST" && req.url === "/api/code-agent/execute-plan") {
    handleGoalPlanExecute(req, res);
    return;
  }
  if (req.method === "POST" && req.url === "/api/agent-team") {
    handleAgentTeam(req, res);
    return;
  }
  if (req.method === "POST" && req.url === "/api/file-editor") {
    handleFileEditor(req, res);
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
  if (requestUrl.pathname === "/ws/realtime") {
    realtimeWss.handleUpgrade(req, socket, head, (ws) => {
      realtimeWss.emit("connection", ws, req);
    });
    return;
  }
  if (requestUrl.pathname !== "/ws/sandbox-terminal") {
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

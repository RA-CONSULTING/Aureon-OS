import express from 'express';
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { randomUUID } from 'node:crypto';
import { spawn } from 'node:child_process';
import Docker from 'dockerode';
import pty from 'node-pty';
import { WebSocketServer, WebSocket } from 'ws';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const ROOT_DIR = path.resolve(__dirname, '..');
const HOST = process.env.FLAMEBORN_RUNTIME_HOST || '127.0.0.1';
const PORT = Number(process.env.FLAMEBORN_RUNTIME_PORT || 7331);
const ALLOW_REMOTE = process.env.FLAMEBORN_RUNTIME_ALLOW_REMOTE === 'true';
const HOST_TERMINAL_ENABLED = ['1', 'true', 'yes', 'on', 'enabled'].includes(
  String(process.env.MURGE_HOST_TERMINAL_ENABLED || process.env.FLAMEBORN_RUNTIME_HOST_TERMINAL_ENABLED || 'false').toLowerCase()
);
const SANDBOX_ENABLED = ['1', 'true', 'yes', 'on', 'enabled'].includes(
  String(process.env.MURGE_SANDBOX_ENABLED || process.env.FLAMEBORN_RUNTIME_SANDBOX_ENABLED || 'false').toLowerCase()
);
const TRUSTED_ORIGINS = String(process.env.FLAMEBORN_RUNTIME_TRUSTED_ORIGINS || '')
  .split(',')
  .map((value) => value.trim())
  .filter(Boolean);
const SANDBOX_IMAGE = process.env.SANDBOX_IMAGE || 'flameborn-runtime:24.04';
const SANDBOX_WORKSPACE_ROOT = process.env.SANDBOX_WORKSPACE_ROOT || path.join(ROOT_DIR, 'logs', 'sandbox-workspaces');
const SANDBOX_LOG_DIR = process.env.SANDBOX_LOG_DIR || path.join(ROOT_DIR, 'logs', 'sandbox-sessions');
const SANDBOX_MEMORY_BYTES = Number(process.env.SANDBOX_MEMORY_BYTES || 2 * 1024 * 1024 * 1024);
const SANDBOX_NANO_CPUS = Number(process.env.SANDBOX_NANO_CPUS || 1_500_000_000);
const SANDBOX_COMMAND_TIMEOUT_MS = Number(process.env.SANDBOX_COMMAND_TIMEOUT_MS || 30000);
const docker = new Docker({ socketPath: process.env.DOCKER_SOCKET || '/var/run/docker.sock' });
const terminalSessions = new Map();
const sandboxSessions = new Map();

const app = express();
app.disable('x-powered-by');
app.use(express.json({ limit: '1mb' }));
app.use((req, res, next) => {
  const origin = req.headers.origin;
  if (isTrustedOrigin(req, origin)) {
    res.setHeader('Access-Control-Allow-Origin', origin || '*');
    res.setHeader('Vary', 'Origin');
  }
  res.setHeader('Access-Control-Allow-Methods', 'GET,POST,OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
  if (req.method === 'OPTIONS') {
    res.status(204).end();
    return;
  }
  next();
});

function isLocalRequest(req) {
  const address = req.socket?.remoteAddress || '';
  return address === '127.0.0.1' || address === '::1' || address === '::ffff:127.0.0.1';
}

function isTrustedOrigin(req, origin = req?.headers?.origin) {
  if (!origin) return true;
  try {
    const parsed = new URL(origin);
    if (TRUSTED_ORIGINS.includes(parsed.origin)) return true;
    const hostOk = ['127.0.0.1', 'localhost', '::1'].includes(parsed.hostname);
    return hostOk;
  } catch {
    return false;
  }
}

function allowRequest(req) {
  return ALLOW_REMOTE || isLocalRequest(req);
}

function safeSessionId(input) {
  const value = String(input || '').trim();
  if (/^[a-zA-Z0-9_-]{4,80}$/.test(value)) return value;
  return `session-${randomUUID()}`;
}

function runProcessCapture(command, args, options = {}) {
  return new Promise((resolve, reject) => {
    const child = spawn(command, args, {
      cwd: options.cwd || ROOT_DIR,
      env: options.env || process.env,
      stdio: ['ignore', 'pipe', 'pipe'],
    });

    let stdout = '';
    let stderr = '';
    const timeoutMs = Number(options.timeoutMs || 30000);
    const timer = setTimeout(() => {
      child.kill('SIGTERM');
      reject(new Error(`Process timeout after ${timeoutMs} ms`));
    }, timeoutMs);

    child.stdout.on('data', (chunk) => {
      stdout += chunk.toString('utf8');
    });
    child.stderr.on('data', (chunk) => {
      stderr += chunk.toString('utf8');
    });
    child.on('error', (error) => {
      clearTimeout(timer);
      reject(error);
    });
    child.on('close', (code) => {
      clearTimeout(timer);
      resolve({ code, stdout, stderr });
    });
  });
}

function runShellCapture(command, options = {}) {
  return new Promise((resolve, reject) => {
    const shell = hostShellForCommand(command);
    const child = spawn(shell.command, shell.args, {
      cwd: options.cwd || ROOT_DIR,
      env: options.env || process.env,
      stdio: ['ignore', 'pipe', 'pipe'],
    });

    let stdout = '';
    let stderr = '';
    let truncated = false;
    const maxBytes = Number(options.maxBytes || 80000);
    const startedAt = Date.now();
    const timeoutMs = Number(options.timeoutMs || 30000);
    const timer = setTimeout(() => {
      child.kill('SIGTERM');
      reject(new Error(`Terminal timeout after ${timeoutMs} ms`));
    }, timeoutMs);

    const collect = (current, chunk) => {
      if (current.length >= maxBytes) {
        truncated = true;
        return current;
      }
      const next = current + chunk.toString('utf8');
      if (next.length > maxBytes) {
        truncated = true;
        return `${next.slice(0, maxBytes)}\n[output truncated]`;
      }
      return next;
    };

    child.stdout.on('data', (chunk) => {
      stdout = collect(stdout, chunk);
    });
    child.stderr.on('data', (chunk) => {
      stderr = collect(stderr, chunk);
    });
    child.on('error', (error) => {
      clearTimeout(timer);
      reject(error);
    });
    child.on('close', (code) => {
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
  if (process.platform === 'win32') {
    const configured = process.env.MURGE_WINDOWS_SHELL || process.env.ComSpec || 'powershell.exe';
    const shellName = path.basename(configured).toLowerCase();
    if (shellName.includes('powershell') || shellName === 'pwsh.exe' || shellName === 'pwsh') {
      return {
        command: configured,
        args: ['-NoLogo', '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass', '-Command', command],
      };
    }
    return { command: configured, args: ['/d', '/s', '/c', command] };
  }
  const configured = process.env.SHELL || '/bin/bash';
  return { command: configured, args: ['-lc', command] };
}

function analyzeTerminalCommand(command, approved = false) {
  const value = String(command || '').trim();
  const lower = value.toLowerCase();
  if (!value) return { allowed: false, reason: 'Empty command.' };

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
    return { allowed: false, reason: 'Command is blocked by the runtime safety guard.' };
  }
  if (/(^|[;&|]\s*)sudo(\s|$)/.test(lower) || /(^|\s)su(\s|$)/.test(lower)) {
    return {
      allowed: false,
      copyOnly: true,
      reason: 'sudo/su commands are copy-only in the web terminal. Run them in the real terminal so password prompts and privileges stay visible.',
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
      reason: 'This command can change files, packages, or repository state. Tick approval before running it.',
    };
  }
  return { allowed: true, reason: 'approved' };
}

function runtimeLog(sessionId, entry) {
  fs.mkdirSync(SANDBOX_LOG_DIR, { recursive: true });
  const logPath = path.join(SANDBOX_LOG_DIR, `${sessionId}.jsonl`);
  fs.appendFileSync(logPath, `${JSON.stringify({ ...entry, timestamp: new Date().toISOString() })}\n`);
}

async function dockerStatus() {
  const status = {
    enabled: SANDBOX_ENABLED,
    socket: process.env.DOCKER_SOCKET || '/var/run/docker.sock',
    dockerAvailable: false,
    dockerCliAvailable: false,
    image: SANDBOX_IMAGE,
    imageAvailable: false,
    workspaceRoot: SANDBOX_WORKSPACE_ROOT,
    companionOrigin: `http://${HOST}:${PORT}`,
  };
  if (!SANDBOX_ENABLED) {
    status.error = 'Sandbox runtime is disabled by MURGE_SANDBOX_ENABLED.';
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
    await runProcessCapture('docker', ['--version'], { timeoutMs: 5000 });
    status.dockerCliAvailable = true;
  } catch {
    status.dockerCliAvailable = false;
  }
  return status;
}

async function ensureSandboxSession(rawSessionId) {
  const sessionId = safeSessionId(rawSessionId);
  if (!SANDBOX_ENABLED) throw new Error('Sandbox runtime is disabled by MURGE_SANDBOX_ENABLED.');
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
  if (!status.dockerAvailable) throw new Error(`Docker daemon unavailable: ${status.error || 'not running'}`);
  if (!status.imageAvailable) throw new Error(`Sandbox image missing: ${SANDBOX_IMAGE}. Run npm run sandbox:build first.`);

  fs.mkdirSync(SANDBOX_WORKSPACE_ROOT, { recursive: true });
  const workspace = path.join(SANDBOX_WORKSPACE_ROOT, sessionId);
  fs.mkdirSync(workspace, { recursive: true });
  const container = await docker.createContainer({
    Image: SANDBOX_IMAGE,
    name: `flameborn-${sessionId}`.slice(0, 63),
    Tty: true,
    OpenStdin: true,
    Cmd: ['sleep', 'infinity'],
    WorkingDir: '/workspace',
    User: 'coder',
    Labels: {
      'flameborn.session': sessionId,
      'flameborn.runtime': 'sandbox',
    },
    HostConfig: {
      Binds: [`${workspace}:/workspace`],
      Memory: SANDBOX_MEMORY_BYTES,
      NanoCpus: SANDBOX_NANO_CPUS,
      NetworkMode: 'bridge',
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
  runtimeLog(sessionId, { event: 'container_started', containerId: container.id, workspace });
  return { ...session, container };
}

async function runSandboxCommand(sessionId, command, approved = false) {
  const safety = analyzeTerminalCommand(command, approved);
  if (!safety.allowed) {
    runtimeLog(sessionId, { event: 'command_blocked', command, safety });
    return { ok: false, blocked: true, command, safety };
  }
  const session = await ensureSandboxSession(sessionId);
  const exec = await session.container.exec({
    Cmd: ['bash', '-lc', command],
    AttachStdout: true,
    AttachStderr: true,
    User: 'coder',
    WorkingDir: '/workspace',
  });
  const startedAt = Date.now();
  const stream = await exec.start({ hijack: true, stdin: false });
  let stdout = '';
  let stderr = '';
  const maxBytes = 120000;
  const timer = setTimeout(() => {
    try {
      stream.destroy(new Error('timeout'));
    } catch {}
  }, SANDBOX_COMMAND_TIMEOUT_MS);

  await new Promise((resolve, reject) => {
    session.container.modem.demuxStream(
      stream,
      { write(chunk) { if (stdout.length < maxBytes) stdout += chunk.toString('utf8'); } },
      { write(chunk) { if (stderr.length < maxBytes) stderr += chunk.toString('utf8'); } }
    );
    stream.on('end', resolve);
    stream.on('close', resolve);
    stream.on('error', reject);
  }).finally(() => clearTimeout(timer));

  const inspect = await exec.inspect();
  const result = {
    ok: inspect.ExitCode === 0,
    blocked: false,
    sessionId: session.id,
    containerId: session.containerId,
    command,
    cwd: '/workspace',
    exitCode: inspect.ExitCode,
    stdout,
    stderr,
    durationMs: Date.now() - startedAt,
    safety,
  };
  runtimeLog(session.id, { event: 'command_result', ...result });
  return result;
}

function sendWsJson(ws, payload) {
  if (ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify(payload));
}

function broadcast(session, payload) {
  for (const client of session.subscribers) {
    if (client.readyState === WebSocket.OPEN) {
      client.send(typeof payload === 'string' ? payload : JSON.stringify(payload));
    }
  }
}

function shellQuote(value) {
  return `'${String(value).replaceAll("'", "'\\''")}'`;
}

function ensureLocalPtySession(rawSessionId) {
  if (!HOST_TERMINAL_ENABLED) throw new Error('Host terminal PTY is disabled by MURGE_HOST_TERMINAL_ENABLED.');
  const sessionId = safeSessionId(rawSessionId || 'default-terminal');
  const existing = terminalSessions.get(sessionId);
  if (existing?.ptyProcess) return existing;

  const shell = process.platform === 'win32'
    ? (process.env.MURGE_WINDOWS_SHELL || process.env.ComSpec || 'powershell.exe')
    : (process.env.SHELL || '/bin/bash');
  const shellName = path.basename(shell);
  const shellArgs = shellName === 'bash'
    ? ['--noprofile', '--norc', '-i']
    : shellName === 'zsh'
      ? ['-f']
      : shellName.toLowerCase().includes('powershell') || shellName.toLowerCase() === 'pwsh.exe'
        ? ['-NoLogo', '-NoProfile']
        : shellName.toLowerCase() === 'cmd.exe'
          ? ['/d']
      : [];
  const ptyProcess = pty.spawn(shell, shellArgs, {
    name: 'xterm-color',
    cols: 120,
    rows: 32,
    cwd: ROOT_DIR,
    env: { ...process.env, PWD: ROOT_DIR, FLAMEBORN_PROJECT_ROOT: ROOT_DIR },
  });
  const session = {
    id: sessionId,
    ptyProcess,
    subscribers: new Set(),
    cwd: ROOT_DIR,
    createdAt: new Date().toISOString(),
  };
  ptyProcess.onData((data) => broadcast(session, data));
  ptyProcess.onExit(({ exitCode, signal }) => {
    broadcast(session, `\r\n[terminal exited code=${exitCode} signal=${signal}]\r\n`);
    terminalSessions.delete(sessionId);
  });
  setTimeout(() => {
    if (!ptyProcess.killed) ptyProcess.write(`cd ${shellQuote(ROOT_DIR)}\n`);
  }, 100);
  terminalSessions.set(sessionId, session);
  runtimeLog(sessionId, { event: 'local_pty_started', cwd: ROOT_DIR });
  return session;
}

async function ensureSandboxPtySession(rawSessionId) {
  const session = await ensureSandboxSession(rawSessionId || 'default-sandbox');
  const existing = sandboxSessions.get(session.id);
  if (existing?.ptyProcess) return existing;
  const ptyProcess = pty.spawn('docker', ['exec', '-it', session.containerId, 'bash', '-l'], {
    name: 'xterm-color',
    cols: 120,
    rows: 32,
    cwd: ROOT_DIR,
    env: process.env,
  });
  existing.ptyProcess = ptyProcess;
  ptyProcess.onData((data) => broadcast(existing, data));
  ptyProcess.onExit(({ exitCode, signal }) => {
    broadcast(existing, `\r\n[sandbox terminal exited code=${exitCode} signal=${signal}]\r\n`);
    existing.ptyProcess = null;
  });
  runtimeLog(session.id, { event: 'sandbox_pty_started', containerId: session.containerId });
  return existing;
}

app.get('/health', (_req, res) => {
  res.json({
    ok: true,
    service: 'flameborn-runtime',
    port: PORT,
    root: ROOT_DIR,
    localOnly: !ALLOW_REMOTE,
    guardedActivation: true,
  });
});

app.get('/api/runtime/info', (_req, res) => {
  res.json({
    name: 'flameborn-runtime',
    host: HOST,
    port: PORT,
    root: ROOT_DIR,
    capabilities: {
      terminalRest: HOST_TERMINAL_ENABLED,
      terminalWs: HOST_TERMINAL_ENABLED,
      sandboxRest: SANDBOX_ENABLED,
      sandboxWs: SANDBOX_ENABLED,
      docker: SANDBOX_ENABLED,
      sudoCopyOnly: true,
      guardedActivation: true,
      noTradingGateBypass: true,
    },
  });
});

app.get('/api/terminal/status', (req, res) => {
  if (!allowRequest(req)) return res.status(403).json({ error: { message: 'Terminal is local-only.' } });
  return res.json({
    enabled: HOST_TERMINAL_ENABLED,
    cwd: ROOT_DIR,
    runtimeOrigin: `http://${HOST}:${PORT}`,
    remoteAccess: ALLOW_REMOTE,
    trustedOrigins: TRUSTED_ORIGINS,
    shell: process.platform === 'win32' ? (process.env.MURGE_WINDOWS_SHELL || process.env.ComSpec || 'powershell.exe') : (process.env.SHELL || '/bin/bash'),
  });
});

app.post('/api/terminal/run', async (req, res) => {
  if (!allowRequest(req)) return res.status(403).json({ error: { message: 'Terminal is local-only.' } });
  if (!isTrustedOrigin(req)) return res.status(403).json({ error: { message: 'Origin is not trusted for terminal execution.' } });
  if (!HOST_TERMINAL_ENABLED) return res.status(403).json({ error: { message: 'Host terminal is disabled by MURGE_HOST_TERMINAL_ENABLED.' } });

  const command = String(req.body?.command || '').trim();
  const approved = Boolean(req.body?.approved);
  const timeoutMs = Number(req.body?.timeoutMs || 30000);
  const safety = analyzeTerminalCommand(command, approved);
  if (!safety.allowed) {
    return res.json({ ok: false, blocked: true, command, cwd: ROOT_DIR, safety });
  }
  try {
    const result = await runShellCapture(command, { cwd: ROOT_DIR, timeoutMs });
    return res.json({ ok: result.code === 0, blocked: false, command, cwd: ROOT_DIR, safety, ...result });
  } catch (error) {
    return res.status(500).json({ error: { message: error.message } });
  }
});

app.get('/api/sandbox/status', async (req, res) => {
  if (!allowRequest(req)) return res.status(403).json({ error: { message: 'Sandbox is local-only.' } });
  try {
    const status = await dockerStatus();
    status.enabled = SANDBOX_ENABLED;
    status.remoteAccess = ALLOW_REMOTE;
    status.trustedOrigins = TRUSTED_ORIGINS;
    res.json(status);
  } catch (error) {
    res.status(500).json({ error: { message: error.message } });
  }
});

app.post('/api/sandbox/run', async (req, res) => {
  if (!allowRequest(req)) return res.status(403).json({ error: { message: 'Sandbox is local-only.' } });
  if (!isTrustedOrigin(req)) return res.status(403).json({ error: { message: 'Origin is not trusted for sandbox execution.' } });
  if (!SANDBOX_ENABLED) return res.status(403).json({ error: { message: 'Sandbox is disabled by MURGE_SANDBOX_ENABLED.' } });
  const sessionId = safeSessionId(req.body?.sessionId || 'default-sandbox');
  const command = String(req.body?.command || '').trim();
  const approved = Boolean(req.body?.approved);
  try {
    const result = await runSandboxCommand(sessionId, command, approved);
    res.json(result);
  } catch (error) {
    res.status(500).json({ error: { message: error.message } });
  }
});

const server = http.createServer(app);
const wss = new WebSocketServer({ noServer: true });

server.on('upgrade', async (req, socket, head) => {
  const requestUrl = new URL(req.url || '/', `http://${req.headers.host || `${HOST}:${PORT}`}`);
  if (!allowRequest(req) || !isTrustedOrigin(req)) {
    socket.write('HTTP/1.1 403 Forbidden\r\n\r\n');
    socket.destroy();
    return;
  }
  if (!['/ws/terminal', '/ws/sandbox-terminal'].includes(requestUrl.pathname)) {
    socket.destroy();
    return;
  }
  wss.handleUpgrade(req, socket, head, (ws) => {
    ws.pathName = requestUrl.pathname;
    ws.sessionId = safeSessionId(requestUrl.searchParams.get('sessionId'));
    wss.emit('connection', ws, req);
  });
});

wss.on('connection', async (ws, req) => {
  try {
    const pathName = ws.pathName;
  if (pathName === '/ws/terminal') {
      if (!HOST_TERMINAL_ENABLED) {
        sendWsJson(ws, { type: 'error', message: 'Host terminal PTY is disabled by MURGE_HOST_TERMINAL_ENABLED.' });
        ws.close();
        return;
      }
      const session = ensureLocalPtySession(ws.sessionId);
      session.subscribers.add(ws);
      sendWsJson(ws, { type: 'attached', sessionId: session.id, cwd: ROOT_DIR, mode: 'host-pty' });
      ws.on('message', (raw) => {
        try {
          const payload = JSON.parse(String(raw || '{}'));
          if (payload.type === 'input') session.ptyProcess.write(String(payload.data || ''));
          if (payload.type === 'resize') session.ptyProcess.resize(Number(payload.cols || 120), Number(payload.rows || 32));
        } catch {}
      });
      ws.on('close', () => session.subscribers.delete(ws));
      return;
    }

    if (!SANDBOX_ENABLED) {
      sendWsJson(ws, { type: 'error', message: 'Sandbox terminal is disabled by MURGE_SANDBOX_ENABLED.' });
      ws.close();
      return;
    }
    const status = await dockerStatus();
    if (!status.dockerAvailable || !status.imageAvailable || !status.dockerCliAvailable) {
      sendWsJson(ws, {
        type: 'error',
        message: !status.dockerAvailable
          ? `Docker daemon unavailable: ${status.error || 'not running'}`
          : !status.imageAvailable
            ? `Sandbox image missing: ${SANDBOX_IMAGE}`
            : 'Docker CLI is required for PTY streaming.',
        status,
      });
      ws.close();
      return;
    }
    const session = await ensureSandboxPtySession(ws.sessionId);
    session.subscribers.add(ws);
    sendWsJson(ws, { type: 'attached', sessionId: session.id, containerId: session.containerId, cwd: '/workspace', mode: 'sandbox-pty' });
    ws.on('message', (raw) => {
      try {
        const payload = JSON.parse(String(raw || '{}'));
        if (payload.type === 'input') session.ptyProcess?.write(String(payload.data || ''));
        if (payload.type === 'resize') session.ptyProcess?.resize(Number(payload.cols || 120), Number(payload.rows || 32));
      } catch {}
    });
    ws.on('close', () => session.subscribers.delete(ws));
  } catch (error) {
    sendWsJson(ws, { type: 'error', message: error.message });
    ws.close();
  }
});

server.listen(PORT, HOST, () => {
  console.log(`flameborn-runtime listening on http://${HOST}:${PORT}`);
});

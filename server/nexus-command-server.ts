#!/usr/bin/env tsx
import 'dotenv/config';
import http from 'http';
import cors from 'cors';
import express from 'express';
import { WebSocketServer, WebSocket } from 'ws';
import { createHash, timingSafeEqual } from 'crypto';

const DEFAULT_HOST = '127.0.0.1';
const MAX_JSON_BODY = '8kb';
const MAX_WS_PAYLOAD_BYTES = 16 * 1024;
const MIN_SECRET_BYTES = 32;

class SafeCommandError extends Error {
  constructor(readonly code: string, readonly status: number = 400) {
    super(code);
    this.name = 'SafeCommandError';
  }
}

function boundedInteger(
  value: unknown,
  fallback: number,
  minimum: number,
  maximum: number,
  code: string,
): number {
  const candidate = value === undefined || value === null || value === '' ? fallback : value;
  if (typeof candidate !== 'number' && typeof candidate !== 'string') {
    throw new SafeCommandError(code);
  }
  const parsed = typeof candidate === 'number' ? candidate : Number(candidate);
  if (!Number.isSafeInteger(parsed) || parsed < minimum || parsed > maximum) {
    throw new SafeCommandError(code);
  }
  return parsed;
}

function configuredHost(value: string | undefined): string {
  const host = String(value || DEFAULT_HOST).trim();
  if (!host || host.length > 253 || !/^[A-Za-z0-9.:[\]_-]+$/.test(host)) {
    throw new Error('nexus_command_host_invalid');
  }
  return host;
}

function isLoopbackHost(value: string): boolean {
  const host = value.trim().toLowerCase().replace(/^\[(.*)\]$/, '$1');
  return host === '127.0.0.1' || host === '::1' || host === 'localhost';
}

function configuredSocketPath(value: string | undefined): string {
  const socketPath = String(value || '/command-stream').trim();
  if (!/^\/[A-Za-z0-9/_-]{1,127}$/.test(socketPath)) {
    throw new Error('nexus_command_socket_path_invalid');
  }
  return socketPath;
}

function configuredOrigins(value: string | undefined): ReadonlySet<string> {
  const rawOrigins = String(value || '').split(',').map((item) => item.trim()).filter(Boolean);
  if (rawOrigins.length > 32) {
    throw new Error('nexus_command_cors_allowlist_too_large');
  }
  const origins = new Set<string>();
  for (const rawOrigin of rawOrigins) {
    if (rawOrigin.length > 2048) {
      throw new Error('nexus_command_cors_origin_invalid');
    }
    let parsed: URL;
    try {
      parsed = new URL(rawOrigin);
    } catch {
      throw new Error('nexus_command_cors_origin_invalid');
    }
    if (!['http:', 'https:'].includes(parsed.protocol) || parsed.origin !== rawOrigin) {
      throw new Error('nexus_command_cors_origin_invalid');
    }
    origins.add(parsed.origin);
  }
  return origins;
}

const HOST = configuredHost(process.env.NEXUS_COMMAND_HOST);
const PORT = boundedInteger(process.env.NEXUS_COMMAND_PORT, 8790, 1, 65535, 'nexus_command_port_invalid');
const SOCKET_PATH = configuredSocketPath(process.env.NEXUS_COMMAND_SOCKET_PATH);
const COMMAND_SECRET = String(process.env.NEXUS_COMMAND_SECRET || '');
const COMMAND_SECRET_BYTES = Buffer.byteLength(COMMAND_SECRET, 'utf8');
const COMMAND_SECRET_STRONG = COMMAND_SECRET_BYTES >= MIN_SECRET_BYTES && COMMAND_SECRET_BYTES <= 4096;
const COMMAND_SECRET_DIGEST = createHash('sha256').update(COMMAND_SECRET, 'utf8').digest();
const DUMMY_SECRET_DIGEST = createHash('sha256').update('aureon-nexus-no-command-secret', 'utf8').digest();
const LOOPBACK_BIND = isLoopbackHost(HOST);
const ALLOWED_ORIGINS = configuredOrigins(process.env.NEXUS_COMMAND_CORS_ORIGINS);

if (COMMAND_SECRET && !COMMAND_SECRET_STRONG) {
  throw new Error('nexus_command_secret_must_be_at_least_32_bytes');
}
if (!LOOPBACK_BIND && !COMMAND_SECRET_STRONG) {
  throw new Error('nexus_command_remote_bind_requires_strong_auth');
}

function bearerToken(header: unknown): string {
  if (typeof header !== 'string' || header.length > 8192 || !header.startsWith('Bearer ')) {
    return '';
  }
  return header.slice('Bearer '.length).trim();
}

function hasValidCommandSecret(header: unknown): boolean {
  const candidateDigest = createHash('sha256').update(bearerToken(header), 'utf8').digest();
  const expectedDigest = COMMAND_SECRET_STRONG ? COMMAND_SECRET_DIGEST : DUMMY_SECRET_DIGEST;
  return COMMAND_SECRET_STRONG && timingSafeEqual(candidateDigest, expectedDigest);
}

function fixedError(res: express.Response, status: number, code: string) {
  return res.status(status).json({ success: false, error: code });
}

function requireCommandAuthorization(
  req: express.Request,
  res: express.Response,
  next: express.NextFunction,
) {
  if (!COMMAND_SECRET_STRONG) {
    return fixedError(res, 503, 'command_auth_not_configured');
  }
  if (!hasValidCommandSecret(req.headers.authorization)) {
    return fixedError(res, 401, 'command_auth_required');
  }
  return next();
}

function requireReadAuthorizationOffLoopback(
  req: express.Request,
  res: express.Response,
  next: express.NextFunction,
) {
  if (LOOPBACK_BIND) {
    return next();
  }
  return requireCommandAuthorization(req, res, next);
}

function requireJsonCommandBody(
  req: express.Request,
  res: express.Response,
  next: express.NextFunction,
) {
  if (!req.is('application/json')) {
    return fixedError(res, 415, 'application_json_required');
  }
  return next();
}

const app = express();
app.disable('x-powered-by');
app.use((req, res, next) => {
  const origin = req.headers.origin;
  if (typeof origin === 'string' && !ALLOWED_ORIGINS.has(origin)) {
    return fixedError(res, 403, 'origin_not_allowed');
  }
  return next();
});
app.use(cors({
  origin(origin, callback) {
    if (!origin) {
      callback(null, true);
      return;
    }
    callback(null, ALLOWED_ORIGINS.has(origin));
  },
  methods: ['GET', 'POST'],
  allowedHeaders: ['Authorization', 'Content-Type'],
  credentials: false,
  maxAge: 600,
}));
app.use(express.json({ limit: MAX_JSON_BODY, strict: true, type: 'application/json' }));

const httpServer = http.createServer(app);
const wss = new WebSocketServer({ noServer: true, maxPayload: MAX_WS_PAYLOAD_BYTES });

const clients = new Map<WebSocket, boolean>();

function snapshot(_includeCommandDetails: boolean = false) {
  return {
    streaming: false,
    intervalMs: null,
    clients: clients.size,
    activeCommand: null,
    commandHistory: [],
    lastTick: null,
    commandEffectsEnabled: false,
    protectionStatus: 'HOLD_PLUMBER_HNC_MAGIC_STAR_BRIDGE_REQUIRED',
  };
}

function broadcastStatus() {
  for (const [client, authorized] of clients) {
    if (client.readyState === WebSocket.OPEN) {
      client.send(JSON.stringify({ type: 'system_status', payload: snapshot(authorized) }));
    }
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function handleCommand(type: string, payload?: Record<string, unknown>) {
  const supported = new Set(['start_stream', 'stop_stream', 'run_nexus', 'stop_active_command']);
  if (!supported.has(type)) {
    throw new SafeCommandError('unsupported_command');
  }
  const body = payload === undefined ? {} : payload;
  if (!isRecord(body) || Object.keys(body).length > 8) {
    throw new SafeCommandError('command_payload_invalid');
  }
  return {
    success: false,
    status: 'HOLD',
    reasonCode: 'plumber_hnc_magic_star_bridge_required',
    command: type,
    inputAdmitted: false,
    effectAttempted: false,
  };
}

function respondCommandError(res: express.Response, error: unknown) {
  if (error instanceof SafeCommandError) {
    return fixedError(res, error.status, error.code);
  }
  console.error('Nexus command request failed.');
  return fixedError(res, 500, 'command_failed');
}

function respondCommandHold(
  res: express.Response,
  type: string,
  payload?: Record<string, unknown>,
) {
  try {
    return res.status(423).json(handleCommand(type, payload));
  } catch (error) {
    return respondCommandError(res, error);
  }
}

app.get('/health', requireReadAuthorizationOffLoopback, (_req, res) => {
  res.json({ ok: true, status: snapshot(false) });
});

app.get('/api/command-center/status', requireReadAuthorizationOffLoopback, (req, res) => {
  res.json(snapshot(hasValidCommandSecret(req.headers.authorization)));
});

app.post(
  '/api/command-center/stream/start',
  requireCommandAuthorization,
  requireJsonCommandBody,
  (req, res) => {
    return respondCommandHold(res, 'start_stream', req.body);
  },
);

app.post('/api/command-center/stream/stop', requireCommandAuthorization, (_req, res) => {
  return respondCommandHold(res, 'stop_stream', {});
});

app.post(
  '/api/command-center/nexus/run',
  requireCommandAuthorization,
  requireJsonCommandBody,
  (req, res) => {
    return respondCommandHold(res, 'run_nexus', req.body);
  },
);

app.post('/api/command-center/nexus/stop', requireCommandAuthorization, (_req, res) => {
  return respondCommandHold(res, 'stop_active_command', {});
});

app.use((_error: unknown, _req: express.Request, res: express.Response, _next: express.NextFunction) => {
  return fixedError(res, 400, 'invalid_json_body');
});

function rejectUpgrade(socket: import('net').Socket, status: number, reason: string) {
  socket.write(`HTTP/1.1 ${status} ${reason}\r\nConnection: close\r\n\r\n`);
  socket.destroy();
}

httpServer.on('upgrade', (request, socket, head) => {
  const origin = request.headers.origin;
  if (typeof origin === 'string' && !ALLOWED_ORIGINS.has(origin)) {
    rejectUpgrade(socket, 403, 'Forbidden');
    return;
  }

  let requestPath = '';
  try {
    requestPath = new URL(request.url || '/', 'http://127.0.0.1').pathname;
  } catch {
    rejectUpgrade(socket, 404, 'Not Found');
    return;
  }
  if (requestPath !== SOCKET_PATH) {
    rejectUpgrade(socket, 404, 'Not Found');
    return;
  }
  if (!LOOPBACK_BIND && !hasValidCommandSecret(request.headers.authorization)) {
    rejectUpgrade(socket, 401, 'Unauthorized');
    return;
  }

  wss.handleUpgrade(request, socket, head, (webSocket) => {
    wss.emit('connection', webSocket, request);
  });
});

wss.on('connection', (socket, request) => {
  const handshakeAuthorized = hasValidCommandSecret(request.headers.authorization);
  clients.set(socket, handshakeAuthorized);
  socket.send(JSON.stringify({ type: 'system_status', payload: snapshot(handshakeAuthorized) }));

  socket.on('message', (raw) => {
    try {
      const parsed = JSON.parse(raw.toString());
      if (parsed?.type === 'ping') {
        socket.send(JSON.stringify({ type: 'pong', ts: Date.now() }));
        return;
      }
      if (parsed?.type === 'status_request') {
        socket.send(JSON.stringify({
          type: 'system_status',
          payload: snapshot(clients.get(socket) === true),
        }));
        return;
      }
      if (parsed?.type === 'command') {
        const messageAuthorized = hasValidCommandSecret(parsed.authorization);
        if (clients.get(socket) !== true && !messageAuthorized) {
          socket.send(JSON.stringify({ type: 'command_response', error: 'command_auth_required' }));
          return;
        }
        clients.set(socket, true);
        if (typeof parsed.command !== 'string' || parsed.command.length > 64) {
          throw new SafeCommandError('unsupported_command');
        }
        const response = handleCommand(parsed.command, parsed.payload);
        socket.send(JSON.stringify({ type: 'command_response', payload: response }));
      }
    } catch (error) {
      const code = error instanceof SafeCommandError ? error.code : 'invalid_command_message';
      socket.send(JSON.stringify({ type: 'command_response', error: code }));
    }
  });

  socket.on('close', () => {
    clients.delete(socket);
    broadcastStatus();
  });
  socket.on('error', () => {
    clients.delete(socket);
  });
});

httpServer.listen(PORT, HOST, () => {
  console.log(`Nexus Command Server listening on http://${HOST}:${PORT}`);
  console.log(`WebSocket stream available at ws://${HOST}:${PORT}${SOCKET_PATH}`);
});

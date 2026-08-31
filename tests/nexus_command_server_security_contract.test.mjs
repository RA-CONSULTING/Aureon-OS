import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';

const source = readFileSync(
  new URL('../server/nexus-command-server.ts', import.meta.url),
  'utf8',
);

function section(start, end) {
  const startIndex = source.indexOf(start);
  assert.notEqual(startIndex, -1, `missing section start: ${start}`);
  const endIndex = source.indexOf(end, startIndex + start.length);
  assert.notEqual(endIndex, -1, `missing section end: ${end}`);
  return source.slice(startIndex, endIndex);
}

test('Nexus command server is loopback-first and remote bind fails closed', () => {
  assert.match(source, /const DEFAULT_HOST = '127\.0\.0\.1';/);
  assert.match(source, /const HOST = configuredHost\(process\.env\.NEXUS_COMMAND_HOST\);/);
  assert.match(
    source,
    /if \(!LOOPBACK_BIND && !COMMAND_SECRET_STRONG\) \{\s*throw new Error\('nexus_command_remote_bind_requires_strong_auth'\);/,
  );
  assert.match(source, /httpServer\.listen\(PORT, HOST,/);
});

test('HTTP and WebSocket command paths require the same constant-time bearer secret', () => {
  const verifier = section('function hasValidCommandSecret(', 'function fixedError(');
  assert.match(verifier, /createHash\('sha256'\)/);
  assert.match(verifier, /timingSafeEqual\(candidateDigest, expectedDigest\)/);
  assert.match(source, /const MIN_SECRET_BYTES = 32;/);

  for (const route of [
    '/api/command-center/stream/start',
    '/api/command-center/stream/stop',
    '/api/command-center/nexus/run',
    '/api/command-center/nexus/stop',
  ]) {
    assert.match(
      source,
      new RegExp(
        `app\\.post\\([\\s\\S]{0,80}?'${route.replaceAll('/', '\\/')}'[\\s\\S]{0,80}?requireCommandAuthorization,`,
      ),
      `${route} must be guarded before its handler`,
    );
  }

  const websocketCommands = section("if (parsed?.type === 'command')", "    } catch (error) {");
  assert.ok(
    websocketCommands.indexOf('hasValidCommandSecret(parsed.authorization)') <
      websocketCommands.indexOf('handleCommand(parsed.command, parsed.payload)'),
    'WebSocket authorization must dominate command dispatch',
  );
  assert.match(source, /!LOOPBACK_BIND && !hasValidCommandSecret\(request\.headers\.authorization\)/);
});

test('read-only exposure, origins, and payloads are bounded', () => {
  assert.match(source, /app\.get\('\/health', requireReadAuthorizationOffLoopback,/);
  assert.match(
    source,
    /app\.get\('\/api\/command-center\/status', requireReadAuthorizationOffLoopback,/,
  );
  assert.match(source, /ALLOWED_ORIGINS\.has\(origin\)/);
  assert.doesNotMatch(source, /app\.use\(cors\(\)\)/);
  assert.match(source, /express\.json\(\{ limit: MAX_JSON_BODY, strict: true/);
  assert.match(source, /requireJsonCommandBody/);
  assert.match(source, /new WebSocketServer\(\{ noServer: true, maxPayload: MAX_WS_PAYLOAD_BYTES \}\)/);
  assert.match(source, /Object\.keys\(body\)\.length > 8/);
  assert.match(source, /parsed\.command\.length > 64/);
  assert.match(source, /const supported = new Set\(/);
});

test('network responses use fixed error codes and never reflect exception text', () => {
  assert.doesNotMatch(source, /error instanceof Error \? error\.message/);
  assert.doesNotMatch(source, /json\([^\n]*error\.message/);
  assert.doesNotMatch(source, /command_response'[^\n]*error\.message/);
  assert.match(source, /return fixedError\(res, 500, 'command_failed'\);/);
  assert.match(source, /: 'invalid_command_message';/);
  assert.match(source, /error: 'command_auth_required'/);
});

test('all command effects remain on explicit HNC and Magic-Star HOLD', () => {
  const handler = section('function handleCommand(', 'function respondCommandError(');
  assert.match(handler, /status: 'HOLD'/);
  assert.match(handler, /reasonCode: 'plumber_hnc_magic_star_bridge_required'/);
  assert.match(handler, /inputAdmitted: false/);
  assert.match(handler, /effectAttempted: false/);
  assert.doesNotMatch(source, /from 'child_process'/);
  assert.doesNotMatch(source, /\bspawn\s*\(/);
  assert.doesNotMatch(source, /\.kill\s*\(/);
  assert.match(source, /res\.status\(423\)\.json\(handleCommand/);
});

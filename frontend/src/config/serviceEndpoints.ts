/**
 * Operator, market-status, and frontend-bridge URLs.
 * Defaults match the local boot. VITE_* overrides them when those ports are taken.
 */

function vite(name: string): string {
  const value = (import.meta.env as Record<string, string | undefined>)[name];
  return typeof value === "string" ? value.trim() : "";
}

function trimSlash(url: string): string {
  return url.replace(/\/$/, "");
}

export const operatorPort = vite("VITE_OPERATOR_PORT") || "8790";
export const marketStatusPort = vite("VITE_MARKET_STATUS_PORT") || "8791";
export const bridgePort = vite("VITE_BRIDGE_PORT") || "8787";

export const operatorBase = trimSlash(vite("VITE_OPERATOR_URL") || `http://127.0.0.1:${operatorPort}`);
export const marketStatusBase = trimSlash(
  vite("VITE_MARKET_STATUS_URL") || `http://127.0.0.1:${marketStatusPort}`,
);
export const bridgeHttpBase = trimSlash(vite("VITE_BRIDGE_HTTP_URL") || `http://127.0.0.1:${bridgePort}`);
export const bridgeWsUrl = vite("VITE_BRIDGE_WS_URL") || `ws://127.0.0.1:${bridgePort}`;

export const gatewayHealthUrl = `${operatorBase}/healthz`;
export const marketStatusHealthUrl = `${marketStatusBase}/healthz`;

export const terminalStateUrls = [
  `${marketStatusBase}/api/terminal-state`,
  `${operatorBase}/api/terminal-state`,
];

export const envCredentialUrls = [
  `${marketStatusBase}/api/env-credentials`,
  `${operatorBase}/api/env-credentials`,
];

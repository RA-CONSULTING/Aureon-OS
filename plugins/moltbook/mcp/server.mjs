import readline from "node:readline";
import { pathToFileURL } from "node:url";

import { createRuntime } from "../src/core.mjs";

const PROTOCOL_VERSION = "2024-11-05";

function jsonRpcError(id, code, message) {
  return {
    jsonrpc: "2.0",
    id: id ?? null,
    error: { code, message },
  };
}

export function createJsonRpcHandler(runtime = createRuntime()) {
  return async function handle(request) {
    if (request === null || typeof request !== "object" || Array.isArray(request)) {
      return jsonRpcError(null, -32600, "Invalid Request");
    }

    const hasId = Object.hasOwn(request, "id");
    const id = hasId ? request.id : null;
    if (typeof request.method !== "string") {
      return hasId ? jsonRpcError(id, -32600, "Invalid Request") : undefined;
    }

    if (request.method.startsWith("notifications/")) return undefined;

    if (request.method === "initialize") {
      return {
        jsonrpc: "2.0",
        id,
        result: {
          protocolVersion: PROTOCOL_VERSION,
          capabilities: { tools: { listChanged: false } },
          serverInfo: { name: "aureon-moltbook", version: "0.1.0" },
        },
      };
    }

    if (request.method === "ping") {
      return { jsonrpc: "2.0", id, result: {} };
    }

    if (request.method === "tools/list") {
      return {
        jsonrpc: "2.0",
        id,
        result: { tools: runtime.listTools() },
      };
    }

    if (request.method === "tools/call") {
      const params = request.params;
      if (
        params === null ||
        typeof params !== "object" ||
        Array.isArray(params) ||
        typeof params.name !== "string"
      ) {
        return jsonRpcError(id, -32602, "Invalid params");
      }
      const toolResult = await runtime.callTool(params.name, params.arguments ?? {});
      return {
        jsonrpc: "2.0",
        id,
        result: {
          content: [{ type: "text", text: JSON.stringify(toolResult) }],
          structuredContent: toolResult,
          isError: !toolResult.ok,
        },
      };
    }

    return hasId ? jsonRpcError(id, -32601, "Method not found") : undefined;
  };
}

export function startStdio({
  input = process.stdin,
  output = process.stdout,
  runtime = createRuntime(),
} = {}) {
  const handle = createJsonRpcHandler(runtime);
  const lines = readline.createInterface({ input, crlfDelay: Infinity });

  lines.on("line", async (line) => {
    let request;
    try {
      request = JSON.parse(line);
    } catch {
      output.write(`${JSON.stringify(jsonRpcError(null, -32700, "Parse error"))}\n`);
      return;
    }

    let response;
    try {
      response = await handle(request);
    } catch {
      response = jsonRpcError(request?.id, -32603, "Internal error");
    }
    if (response !== undefined) output.write(`${JSON.stringify(response)}\n`);
  });

  return lines;
}

const isEntrypoint =
  typeof process.argv[1] === "string" && import.meta.url === pathToFileURL(process.argv[1]).href;

if (isEntrypoint) startStdio();

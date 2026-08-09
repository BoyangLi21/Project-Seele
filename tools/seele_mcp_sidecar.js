"use strict";

// Project SEELE's Forge 1.20.1 adapter for the Gemini Minecraft MCP workflow.
// It intentionally uses only Node built-ins so Codex can launch it directly.

const fs = require("fs");
const http = require("http");
const path = require("path");

const DEFAULT_BRIDGE_URL = "http://127.0.0.1:7766";
const TOKEN_FILE_NAME = "projectseele-mcp-token.txt";

const VECTOR_SCHEMA = {
  oneOf: [
    { type: "array", items: { type: "integer" }, minItems: 3, maxItems: 3 },
    {
      type: "object",
      properties: { x: { type: "integer" }, y: { type: "integer" }, z: { type: "integer" } },
      required: ["x", "y", "z"],
    },
  ],
};

const CUBOID_SCHEMA = {
  type: "object",
  properties: {
    from: VECTOR_SCHEMA,
    to: VECTOR_SCHEMA,
    block: { type: "string", description: "Block id/state or palette key." },
    hollow: { type: "boolean", default: false },
  },
  required: ["from", "to"],
};

const BLOCK_SCHEMA = {
  type: "object",
  properties: {
    pos: VECTOR_SCHEMA,
    block: { type: "string", description: "Block id/state or palette key." },
  },
  required: ["pos", "block"],
};

const PLAN_SCHEMA = {
  type: "object",
  description: "Structured voxel plan. Preview it before execution.",
  properties: {
    summary: { type: "string" },
    coordMode: { type: "string", enum: ["relative", "absolute"], default: "relative" },
    origin: VECTOR_SCHEMA,
    rotation: { type: "integer", enum: [0, 90, 180, 270], default: 0 },
    palette: { type: "object", additionalProperties: { type: "string" } },
    clearVolumes: { type: "array", items: CUBOID_SCHEMA },
    cuboids: { type: "array", items: CUBOID_SCHEMA },
    blocks: { type: "array", items: BLOCK_SCHEMA },
    steps: {
      type: "array",
      items: {
        type: "object",
        properties: {
          label: { type: "string" },
          clearVolumes: { type: "array", items: CUBOID_SCHEMA },
          cuboids: { type: "array", items: CUBOID_SCHEMA },
          blocks: { type: "array", items: BLOCK_SCHEMA },
        },
      },
    },
  },
};

const TOOLS = {
  minecraft_session: {
    description: "Read the active Project SEELE player, dimension, coordinates, game mode, and write-policy state.",
    method: "GET",
    endpoint: "/v1/session",
    inputSchema: { type: "object", properties: {} },
    annotations: { readOnlyHint: true, destructiveHint: false },
  },
  minecraft_seele_status: {
    description: "Read Project SEELE world-role and MCP safety status. Check this before proposing any mutation.",
    method: "GET",
    endpoint: "/v1/tools/seele_status",
    inputSchema: { type: "object", properties: {} },
    annotations: { readOnlyHint: true, destructiveHint: false },
  },
  minecraft_buildsite: {
    description: "Sample terrain around the active player. Surface dy values are relative to the player's current block Y.",
    method: "POST",
    endpoint: "/v1/tools/buildsite",
    inputSchema: {
      type: "object",
      properties: { radius: { type: "integer", minimum: 4, maximum: 64, default: 24 } },
    },
    annotations: { readOnlyHint: true, destructiveHint: false },
  },
  minecraft_capture_view: {
    description: "Capture the active player's current rendered world view as a PNG for visual inspection. This never moves the player or camera; position the view in game before calling it.",
    method: "POST",
    endpoint: "/v1/tools/capture_view",
    inputSchema: {
      type: "object",
      properties: {
        viewLabel: {
          type: "string",
          description: "A short label such as front-three-quarter, port-side, dining-room, or roof-detail.",
          maxLength: 96,
        },
        width: { type: "integer", minimum: 160, maximum: 960, default: 640 },
        height: { type: "integer", minimum: 90, maximum: 540, default: 360 },
      },
    },
    annotations: { readOnlyHint: true, destructiveHint: false },
  },
  minecraft_preview_build_plan: {
    description: "Compile and validate a voxel plan without changing the world. Save planId and execute that exact preview.",
    method: "POST",
    endpoint: "/v1/actions/preview_build_plan",
    inputSchema: { type: "object", properties: { plan: PLAN_SCHEMA }, required: ["plan"] },
    annotations: { readOnlyHint: true, destructiveHint: false },
  },
  minecraft_execute_build_plan: {
    description: "Queue a staged, reversible build. Prefer executePlanId from a reviewed preview. Generic writes are rejected in protected SEELE saves.",
    method: "POST",
    endpoint: "/v1/actions/execute_build_plan",
    inputSchema: {
      type: "object",
      properties: { executePlanId: { type: "string" }, plan: PLAN_SCHEMA },
      anyOf: [{ required: ["executePlanId"] }, { required: ["plan"] }],
    },
    annotations: { readOnlyHint: false, destructiveHint: true, idempotentHint: false },
  },
  minecraft_batch_status: {
    description: "Poll the active or specified staged build/undo job until status is complete or failed.",
    method: "POST",
    endpoint: "/v1/tools/batch_status",
    inputSchema: {
      type: "object",
      properties: { jobId: { type: "string" } },
    },
    annotations: { readOnlyHint: true, destructiveHint: false },
  },
  minecraft_undo_last_batch: {
    description: "Queue restoration of every block and block-entity state changed by the last completed MCP build.",
    method: "POST",
    endpoint: "/v1/actions/undo",
    inputSchema: { type: "object", properties: {} },
    annotations: { readOnlyHint: false, destructiveHint: true, idempotentHint: false },
  },
};

const GUIDE = `# Project SEELE MCP workflow

This is a Forge 1.20.1 compatibility bridge inspired by gemini-minecraft's MCP workflow.

1. Call minecraft_session and minecraft_seele_status.
2. If genericMcpMutationAllowed is false, do not try to write. Project SEELE facility, recovery, and frozen-preview saves require the repository's MAP_EDITING_PROTOCOL.md and approved deterministic patches.
3. In a disposable development world, call minecraft_buildsite before terrain-sensitive construction.
4. Translate the user's natural-language brief into dimensions, orientation, functional zones, palette, structural modules, and acceptance criteria. A named fictional building may be interpreted as a Minecraft-scale reconstruction; state important assumptions instead of inventing false precision.
   - For a named real or fictional landmark, research multiple exterior and interior reference views before planning when web/image search is available. Prefer canonical or official descriptive sources, keep source URLs, separate verified features from inference, and never copy or redistribute official art assets.
5. Create a structured plan with palette, cuboids, blocks, and optional steps.
   - Prefer frame-and-infill construction: foundation, silhouette/frame, floors, envelope, circulation, detail, and lighting.
   - Use cuboids for large surfaces and repeated modules, and explicit blocks only for details. Do not issue /fill, /clone, /summon, /data, or arbitrary game commands.
   - Large projects must be split into spatial or construction-stage batches that stay independently inspectable and reversible.
   - Multi-storey buildings must have usable floor heights, entrances, interior space, and vertical circulation.
   - Avoid giant solid masses and uniformly flat facades. Use a primary silhouette, secondary structural rhythm, and tertiary details such as setbacks, ribs, window bands, eaves, recesses, or diagonal braces.
   - Record overall bounds, entrance direction, floor heights, symmetry axes, module spacing, material roles, and approximate block count before execution.
6. Call minecraft_preview_build_plan and inspect resolvedOrigin, bounds, materials, blockCount, and previewBlocks. Reject plans with bad proportions, inaccessible interiors, accidental solid fill, unsafe terrain intersection, or limits exceeded.
7. If the user explicitly asked to build in a disposable development world, that request is approval after safety checks. Ask only when a consequential ambiguity would materially change the result.
8. Execute the exact cached preview using executePlanId.
9. Poll minecraft_batch_status until complete. Report each major stage. Use minecraft_undo_last_batch if the result is unwanted, then correct and preview again rather than building over an error.
10. For visual quality gates, have the player frame a useful exterior or interior angle, then call minecraft_capture_view. Compare silhouette, proportions, color blocking, openings, circulation, and signature details against the reference manifest. Capture at least front three-quarter, side/rear, and one interior view for large reference builds, and apply only scoped, previewed correction batches.

Relative plan coordinates are anchored at the active player's block position plus origin. Absolute mode requires an explicit world origin. Rotation is around the Y axis. Block strings may include state properties, for example minecraft:oak_stairs[facing=north,half=bottom,shape=straight,waterlogged=false].
`;

function parseArgs(argv) {
  const result = {};
  for (let index = 0; index < argv.length; index += 1) {
    const item = argv[index];
    if (!item.startsWith("--")) continue;
    const name = item.slice(2);
    if (name === "self-test" || name === "debug") {
      result[name] = true;
    } else if (index + 1 < argv.length) {
      result[name] = argv[++index];
    }
  }
  return result;
}

function firstNonBlank(...values) {
  for (const value of values) {
    if (typeof value === "string" && value.trim()) return value.trim();
  }
  return "";
}

class BridgeClient {
  constructor(bridgeUrl, explicitToken, tokenFile, projectRoot, debug) {
    this.bridgeUrl = bridgeUrl.replace(/\/$/, "");
    this.explicitToken = explicitToken;
    this.tokenFile = tokenFile;
    this.projectRoot = projectRoot;
    this.debug = debug;
  }

  log(message) {
    if (this.debug) process.stderr.write(`[seele-mcp] ${message}\n`);
  }

  resolveToken() {
    if (this.explicitToken) return this.explicitToken;
    const candidates = [];
    if (this.tokenFile) candidates.push(this.tokenFile);
    candidates.push(path.join(this.projectRoot, "run", "config", TOKEN_FILE_NAME));
    candidates.push(path.join(this.projectRoot, "config", TOKEN_FILE_NAME));
    for (const candidate of candidates) {
      try {
        const value = fs.readFileSync(candidate, "utf8").trim();
        if (value) return value;
      } catch (_) {
        // The integrated server creates the token on first world start.
      }
    }
    return "";
  }

  request(method, endpoint, body, authenticated = true) {
    return new Promise((resolve) => {
      const target = new URL(`${this.bridgeUrl}${endpoint}`);
      const payload = body == null ? null : Buffer.from(JSON.stringify(body), "utf8");
      const headers = { Accept: "application/json" };
      if (payload) {
        headers["Content-Type"] = "application/json; charset=utf-8";
        headers["Content-Length"] = String(payload.length);
      }
      if (authenticated) {
        const token = this.resolveToken();
        if (!token) {
          resolve({ error: { code: "TOKEN_NOT_READY", message: "Start a Project SEELE world once so the local MCP token file can be created." } });
          return;
        }
        headers.Authorization = `Bearer ${token}`;
      }
      const request = http.request(
        {
          hostname: target.hostname,
          port: target.port || 80,
          path: `${target.pathname}${target.search}`,
          method,
          headers,
          timeout: 20000,
        },
        (response) => {
          const chunks = [];
          response.on("data", (chunk) => chunks.push(chunk));
          response.on("end", () => {
            const raw = Buffer.concat(chunks).toString("utf8");
            try {
              resolve(raw ? JSON.parse(raw) : {});
            } catch (_) {
              resolve({ error: { code: "INVALID_BRIDGE_RESPONSE", message: raw || `HTTP ${response.statusCode}` } });
            }
          });
        }
      );
      request.on("timeout", () => request.destroy(new Error("Bridge request timed out.")));
      request.on("error", (error) => resolve({ error: { code: "BRIDGE_UNAVAILABLE", message: error.message } }));
      if (payload) request.write(payload);
      request.end();
    });
  }

  async callTool(name, args) {
    const tool = TOOLS[name];
    if (!tool) return { error: { code: "UNKNOWN_TOOL", message: `Unknown tool: ${name}` } };
    const health = await this.request("GET", "/v1/health", null, false);
    if (health.error) return health;
    if (health.enabled === false) {
      return { error: { code: "BRIDGE_DISABLED", message: "Run /seele mcp enable inside the active Project SEELE world." } };
    }
    return this.request(tool.method, tool.endpoint, args || {}, true);
  }
}

function toolResult(requestId, payload) {
  const isError = Boolean(payload && payload.error);
  const imageBase64 = !isError && payload && typeof payload.imageBase64 === "string"
    ? payload.imageBase64
    : "";
  const metadata = imageBase64 ? { ...payload } : payload;
  if (imageBase64) delete metadata.imageBase64;
  const content = [{ type: "text", text: JSON.stringify(metadata) }];
  if (imageBase64) {
    content.push({ type: "image", data: imageBase64, mimeType: payload.mimeType || "image/png" });
  }
  return {
    jsonrpc: "2.0",
    id: requestId,
    result: {
      isError,
      content,
      structuredContent: metadata,
    },
  };
}

async function handleRequest(client, request) {
  const id = request.id;
  const method = request.method || "";
  const params = request.params || {};
  if (method.startsWith("notifications/")) return null;
  if (method === "initialize") {
    return {
      jsonrpc: "2.0",
      id,
      result: {
        protocolVersion: params.protocolVersion || "2025-06-18",
        capabilities: { tools: {}, resources: {} },
        serverInfo: { name: "project-seele-minecraft", version: "0.1.0" },
        instructions: "Inspect session/status first. Preview every build, execute the cached planId, poll status, and never bypass protected SEELE world policy.",
      },
    };
  }
  if (method === "ping") return { jsonrpc: "2.0", id, result: {} };
  if (method === "tools/list") {
    return {
      jsonrpc: "2.0",
      id,
      result: {
        tools: Object.entries(TOOLS).map(([name, tool]) => ({
          name,
          description: tool.description,
          inputSchema: tool.inputSchema,
          annotations: tool.annotations,
        })),
      },
    };
  }
  if (method === "tools/call") {
    const name = params.name || "";
    if (!TOOLS[name]) {
      return { jsonrpc: "2.0", id, error: { code: -32602, message: `Unknown tool: ${name}` } };
    }
    return toolResult(id, await client.callTool(name, params.arguments || {}));
  }
  if (method === "resources/list") {
    return {
      jsonrpc: "2.0",
      id,
      result: {
        resources: [{
          uri: "minecraft://project-seele/mcp-guide",
          name: "Project SEELE MCP build guide",
          description: "Safe inspection, preview, staged execution, and undo workflow.",
          mimeType: "text/markdown",
        }],
      },
    };
  }
  if (method === "resources/read") {
    if (params.uri !== "minecraft://project-seele/mcp-guide") {
      return { jsonrpc: "2.0", id, error: { code: -32602, message: `Unknown resource: ${params.uri || ""}` } };
    }
    return {
      jsonrpc: "2.0",
      id,
      result: { contents: [{ uri: params.uri, mimeType: "text/markdown", text: GUIDE }] },
    };
  }
  return { jsonrpc: "2.0", id, error: { code: -32601, message: `Method not found: ${method}` } };
}

function createParser(onMessage) {
  let buffer = Buffer.alloc(0);
  return (chunk) => {
    buffer = Buffer.concat([buffer, chunk]);
    while (buffer.length > 0) {
      const text = buffer.toString("utf8");
      if (/^Content-Length\s*:/i.test(text)) {
        let headerEnd = buffer.indexOf("\r\n\r\n");
        let separatorLength = 4;
        if (headerEnd < 0) {
          headerEnd = buffer.indexOf("\n\n");
          separatorLength = 2;
        }
        if (headerEnd < 0) return;
        const header = buffer.slice(0, headerEnd).toString("utf8");
        const match = header.match(/content-length\s*:\s*(\d+)/i);
        if (!match) {
          buffer = buffer.slice(headerEnd + separatorLength);
          continue;
        }
        const length = Number(match[1]);
        const start = headerEnd + separatorLength;
        if (buffer.length < start + length) return;
        const body = buffer.slice(start, start + length).toString("utf8");
        buffer = buffer.slice(start + length);
        try { onMessage(JSON.parse(body), "framed"); } catch (_) { /* ignore malformed frames */ }
        continue;
      }
      const newline = buffer.indexOf("\n");
      if (newline < 0) return;
      const line = buffer.slice(0, newline).toString("utf8").trim();
      buffer = buffer.slice(newline + 1);
      if (!line) continue;
      try { onMessage(JSON.parse(line), "bare"); } catch (_) { /* ignore malformed lines */ }
    }
  };
}

function writeMessage(message, style) {
  const payload = Buffer.from(JSON.stringify(message), "utf8");
  if (style === "bare") {
    process.stdout.write(payload);
    process.stdout.write("\n");
  } else {
    process.stdout.write(`Content-Length: ${payload.length}\r\n\r\n`);
    process.stdout.write(payload);
  }
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  if (args["self-test"]) {
    process.stdout.write(JSON.stringify({ ok: true, tools: Object.keys(TOOLS), guide: GUIDE.length }) + "\n");
    return;
  }
  const projectRoot = path.resolve(firstNonBlank(args["project-root"], process.env.SEELE_PROJECT_ROOT, path.resolve(__dirname, "..")));
  const bridgeUrl = firstNonBlank(args["bridge-url"], process.env.SEELE_MCP_BRIDGE_URL, DEFAULT_BRIDGE_URL);
  const explicitToken = firstNonBlank(args["bridge-token"], process.env.SEELE_MCP_TOKEN, "");
  const tokenFile = firstNonBlank(args["token-file"], process.env.SEELE_MCP_TOKEN_FILE, "");
  const client = new BridgeClient(bridgeUrl, explicitToken, tokenFile, projectRoot, Boolean(args.debug));
  let transportStyle = "framed";
  const parser = createParser((request, style) => {
    transportStyle = style || transportStyle;
    Promise.resolve(handleRequest(client, request))
      .then((response) => { if (response != null) writeMessage(response, transportStyle); })
      .catch((error) => {
        if (request.id != null) {
          writeMessage({ jsonrpc: "2.0", id: request.id, error: { code: -32603, message: error.message } }, transportStyle);
        }
      });
  });
  process.stdin.on("data", parser);
  process.stdin.on("end", () => process.exit(0));
  process.stdin.resume();
}

main().catch((error) => {
  process.stderr.write(`[seele-mcp] fatal: ${error.stack || error.message}\n`);
  process.exit(1);
});

#!/usr/bin/env node

/**
 * Compact, redacting Streamable HTTP client for the user's chrome-mcp server.
 *
 * This is intentionally a one-shot CLI. It never persists MCP responses, browser
 * state, endpoint URLs, or credentials. Keep site workflows in their recipe;
 * this helper only bypasses an unreliable Grok tool-discovery meta-layer.
 */

import { createHmac, randomBytes, timingSafeEqual } from "node:crypto";
import { homedir } from "node:os";
import { readdir, realpath, stat } from "node:fs/promises";
import { basename, dirname, join, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const DEFAULT_ENDPOINT = "http://127.0.0.1:12306/mcp";
const DEFAULT_TIMEOUT_MS = 60_000;
const DEFAULT_MAX_OUTPUT_BYTES = 24_000;
const MIN_OUTPUT_BYTES = 1_024;
const MAX_OUTPUT_BYTES = 262_144;
const MAX_STRING_CHARS = 1_200;
const MAX_ARRAY_ITEMS = 80;
const MAX_OBJECT_KEYS = 120;
const MAX_DEPTH = 14;
const SAFE_CALL_ARGUMENTS = new Map([
  ["chrome_navigate", new Set(["url", "tabId", "newWindow"])],
  ["chrome_read_page", new Set(["tabId", "selector", "textQuery", "types", "includeCoordinates"])],
  ["chrome_switch_tab", new Set(["tabId"])],
  ["chrome_computer", new Set([
    "tabId", "action", "selector", "coordinates", "x", "y", "text", "keys", "key", "delay",
    "duration", "ms",
  ])],
  ["chrome_handle_download", new Set([
    "filenameContains", "directory", "lookbackMs", "waitForComplete",
  ])],
  ["chrome_click_element", new Set([
    "tabId", "selector", "selectorType", "coordinates", "x", "y", "waitForNavigation", "timeout",
  ])],
  ["chrome_fill_or_select", new Set(["tabId", "selector", "value"])],
  ["chrome_keyboard", new Set(["tabId", "keys", "selector", "delay"])],
  ["chrome_screenshot", new Set(["tabId", "selector", "storeBase64", "savePng", "fullPage"])],
]);
const MUTATING_BROWSER_TOOLS = new Set([
  "chrome_navigate", "chrome_switch_tab", "chrome_computer", "chrome_click_element",
  "chrome_fill_or_select", "chrome_keyboard",
]);
const TAB_SCOPED_SAFE_TOOLS = new Set([
  "chrome_navigate", "chrome_read_page", "chrome_switch_tab", "chrome_computer",
  "chrome_click_element", "chrome_fill_or_select", "chrome_keyboard", "chrome_screenshot",
]);

export const EXIT = Object.freeze({
  OK: 0,
  USAGE: 2,
  DEPENDENCY: 3,
  CONNECTION: 4,
  TOOL_NOT_FOUND: 5,
  TOOL_CALL: 6,
  INTERNAL: 7,
});

const SENSITIVE_KEY = /^(?:auth(?:orization)?(?:[-_]?(?:token|code|header))?|proxy[-_]?authorization|cookie|set[-_]?cookie|headers?|request[-_]?headers|response[-_]?headers|password|passwd|pwd|secret(?:[-_]?(?:key|token))?|client[-_]?secret|api[-_]?key|apikey|access[-_]?token|refresh[-_]?token|id[-_]?token|token|jwt|credentials?|(?:csrf|xsrf)(?:[-_]?(?:token|key))?|session(?:[-_]?(?:id|token|key))?|mcp[-_]?session[-_]?id|signature|sig|x[-_]?amz[-_]?(?:signature|security[-_]?token|credential)|aws[-_]?access[-_]?key[-_]?id|key[-_]?pair[-_]?id|value|input[-_]?value|html|html[-_]?content|inner[-_]?html|outer[-_]?html)$/i;
const URL_VALUE_KEY = /(?:^|[-_])(?:url|uri|href|link)$/i;
const CAMEL_URL_VALUE_KEY = /(?:Url|URI|Href)$/;
const URL_IN_TEXT = /\b(?:https?|wss?):\/\/[^\s"'<>]+/gi;
const SENSITIVE_URL_PARAMETER = /(?:^|[-_])(?:auth|authorization|token|session|signature|sig|credential|secret|key|x[-_]?amz)(?:$|[-_])/i;
const BASE64_LIKE = /^(?:[A-Za-z0-9+/]{4}){20,}(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?$/;
const LONG_HEX = /^(?:[A-Fa-f0-9]{2}){40,}$/;
const JWT_LIKE = /^eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+(?:\.[A-Za-z0-9_-]+)?$/;

function decodeUrlComponentCapped(value) {
  let decoded = String(value ?? "");
  for (let iteration = 0; iteration < 3; iteration += 1) {
    try {
      const next = decodeURIComponent(decoded);
      if (next === decoded) break;
      decoded = next;
    } catch {
      break;
    }
  }
  return decoded;
}

function urlParameterKeyIsSensitive(key) {
  const decoded = decodeUrlComponentCapped(key);
  const separatedCamelCase = decoded.replace(/([a-z0-9])([A-Z])/g, "$1-$2");
  const compact = separatedCamelCase.replace(/[^A-Za-z0-9]/g, "").toLowerCase();
  return SENSITIVE_URL_PARAMETER.test(separatedCamelCase)
    || /^(?:auth(?:orization)?(?:token|code|header)?|proxyauthorization|password|passwd|pwd|secret(?:key|token)?|clientsecret|apikey|accesstoken|refreshtoken|idtoken|token|jwt|credential|credentials|session(?:id|token|key|state)?|mcpsessionid|signature|sig|xamz(?:signature|securitytoken|credential)|awsaccesskeyid|keypairid|oauthverifier|samlresponse|assertion|ticket|code|key)$/.test(compact);
}

function textHasSensitiveParameterAssignment(value) {
  const decoded = decodeUrlComponentCapped(value);
  const fragmentParameter = /(?:^|[?&#;])([^=?&#;]+)=/g;
  let match;
  while ((match = fragmentParameter.exec(decoded)) !== null) {
    if (urlParameterKeyIsSensitive(match[1])) return true;
  }
  const structuredParameter = /(?:^|[,{])\s*["']?([^"'{}:,=\s]+)["']?\s*[:=]/g;
  while ((match = structuredParameter.exec(decoded)) !== null) {
    if (urlParameterKeyIsSensitive(match[1])) return true;
  }
  return false;
}

function urlHasSensitiveParameters(parsed) {
  for (const [key, value] of parsed.searchParams.entries()) {
    if (urlParameterKeyIsSensitive(key) || textHasSensitiveParameterAssignment(value)) {
      return true;
    }
  }
  return textHasSensitiveParameterAssignment(parsed.hash.slice(1));
}

class CliError extends Error {
  constructor(message, exitCode, details = {}) {
    super(message);
    this.name = "CliError";
    this.exitCode = exitCode;
    this.details = details;
  }
}

function validateSafeCall(tool, args) {
  const allowedArguments = SAFE_CALL_ARGUMENTS.get(tool);
  if (!allowedArguments) {
    throw new CliError(
      `call rejects non-allowlisted chrome-mcp tool: ${String(tool)}`,
      EXIT.USAGE,
    );
  }
  const unexpected = Object.keys(args).filter((key) => !allowedArguments.has(key));
  if (unexpected.length > 0) {
    throw new CliError(
      `call ${tool} rejects unsupported arguments: ${unexpected.sort().join(", ")}`,
      EXIT.USAGE,
    );
  }
  if (tool === "chrome_computer" && args.action === "double_click") {
    throw new CliError(
      "legacy-safe helper refuses non-atomic double_click; use one independently verified click at a time",
      EXIT.TOOL_CALL,
      { retryable: false, effect_state: "not_started", state_check_required: false },
    );
  }
  if (TAB_SCOPED_SAFE_TOOLS.has(tool)
    && (!Number.isSafeInteger(args.tabId) || args.tabId < 1)) {
    throw new CliError(`${tool} requires a positive integer tabId`, EXIT.USAGE);
  }
  if (tool === "chrome_navigate") {
    let parsed;
    try {
      parsed = new URL(args.url);
    } catch {
      throw new CliError("chrome_navigate requires a valid URL", EXIT.USAGE);
    }
    if (!["http:", "https:"].includes(parsed.protocol) || parsed.username || parsed.password) {
      throw new CliError(
        "chrome_navigate accepts only credential-free HTTP(S) URLs",
        EXIT.USAGE,
      );
    }
    if (urlHasSensitiveParameters(parsed)) {
      throw new CliError(
        "chrome_navigate refuses signed or credential-bearing URL parameters",
        EXIT.USAGE,
      );
    }
  }
}

function usage() {
  return `Usage:
  chrome_mcp_client.mjs list-tools [--max-output-bytes N]
  chrome_mcp_client.mjs schema TOOL [--max-output-bytes N]
  chrome_mcp_client.mjs tabs --url-contains STR [--max-output-bytes N]
  chrome_mcp_client.mjs call SAFE_TOOL --args-json JSON [--max-output-bytes N]
  chrome_mcp_client.mjs exact-text --text TEXT --scope-selector CSS --tab-id N
  chrome_mcp_client.mjs exact-selector-click --text TEXT --scope-selector CSS --selector CSS --tab-id N
  chrome_mcp_client.mjs self-test

Connection:
  --endpoint URL               Override ARIS_CHROME_MCP_URL or ${DEFAULT_ENDPOINT}
  --timeout-ms N               Request timeout (default ${DEFAULT_TIMEOUT_MS})

Output and exit codes:
  JSON is recursively redacted and capped (default ${DEFAULT_MAX_OUTPUT_BYTES} bytes).
  0=success, 2=usage, 3=dependency, 4=connection/protocol,
  5=tool not found, 6=tool invocation error, 7=internal error.`;
}

function parsePositiveInteger(value, label, { min = 1, max = Number.MAX_SAFE_INTEGER } = {}) {
  if (!/^\d+$/.test(value ?? "")) {
    throw new CliError(`${label} must be an integer`, EXIT.USAGE);
  }
  const parsed = Number(value);
  if (!Number.isSafeInteger(parsed) || parsed < min || parsed > max) {
    throw new CliError(`${label} must be between ${min} and ${max}`, EXIT.USAGE);
  }
  return parsed;
}

function takeOption(tokens, index, name) {
  const value = tokens[index + 1];
  if (value === undefined || value.startsWith("--")) {
    throw new CliError(`${name} requires a value`, EXIT.USAGE);
  }
  return value;
}

export function parseArgs(argv, env = process.env) {
  if (argv.length === 0 || argv.includes("--help") || argv.includes("-h")) {
    return { command: "help" };
  }

  const command = argv[0];
  if (![
    "list-tools", "schema", "tabs", "call", "exact-text", "exact-selector-click", "self-test",
  ].includes(command)) {
    throw new CliError(`unknown command: ${command}`, EXIT.USAGE);
  }

  let endpoint = env.ARIS_CHROME_MCP_URL || DEFAULT_ENDPOINT;
  let timeoutMs = DEFAULT_TIMEOUT_MS;
  let maxOutputBytes = parsePositiveInteger(
    env.ARIS_MCP_MAX_OUTPUT_BYTES || String(DEFAULT_MAX_OUTPUT_BYTES),
    "ARIS_MCP_MAX_OUTPUT_BYTES",
    { min: MIN_OUTPUT_BYTES, max: MAX_OUTPUT_BYTES },
  );
  let tool;
  let argsJson;
  let urlContains;
  let exactText;
  let scopeSelector = "body";
  let targetSelector;
  let tabId;
  const positional = [];

  for (let index = 1; index < argv.length; index += 1) {
    const token = argv[index];
    if (token === "--endpoint") {
      endpoint = takeOption(argv, index, token);
      index += 1;
    } else if (token === "--timeout-ms") {
      timeoutMs = parsePositiveInteger(takeOption(argv, index, token), token, {
        min: 100,
        max: 600_000,
      });
      index += 1;
    } else if (token === "--max-output-bytes") {
      maxOutputBytes = parsePositiveInteger(takeOption(argv, index, token), token, {
        min: MIN_OUTPUT_BYTES,
        max: MAX_OUTPUT_BYTES,
      });
      index += 1;
    } else if (token === "--args-json") {
      argsJson = takeOption(argv, index, token);
      index += 1;
    } else if (token === "--url-contains") {
      urlContains = takeOption(argv, index, token);
      index += 1;
    } else if (token === "--text") {
      exactText = takeOption(argv, index, token);
      index += 1;
    } else if (token === "--scope-selector") {
      scopeSelector = takeOption(argv, index, token);
      index += 1;
    } else if (token === "--selector") {
      targetSelector = takeOption(argv, index, token);
      index += 1;
    } else if (token === "--tab-id") {
      tabId = parsePositiveInteger(takeOption(argv, index, token), token);
      index += 1;
    } else if (token.startsWith("--")) {
      throw new CliError(`unknown option: ${token}`, EXIT.USAGE);
    } else {
      positional.push(token);
    }
  }

  if (command === "self-test") {
    if (argv.length !== 1) {
      throw new CliError("self-test takes no arguments", EXIT.USAGE);
    }
    return { command, maxOutputBytes };
  }

  try {
    const parsedEndpoint = new URL(endpoint);
    if (!["http:", "https:"].includes(parsedEndpoint.protocol)) {
      throw new Error("unsupported protocol");
    }
  } catch {
    throw new CliError("MCP endpoint must be a valid HTTP(S) URL", EXIT.USAGE);
  }

  const exactTextOptionsUsed = exactText !== undefined
    || scopeSelector !== "body"
    || targetSelector !== undefined
    || tabId !== undefined;

  if (command === "list-tools") {
    if (
      positional.length !== 0
      || argsJson !== undefined
      || urlContains !== undefined
      || exactTextOptionsUsed
    ) {
      throw new CliError("list-tools takes no tool or operation arguments", EXIT.USAGE);
    }
  } else if (command === "schema") {
    if (
      positional.length !== 1
      || argsJson !== undefined
      || urlContains !== undefined
      || exactTextOptionsUsed
    ) {
      throw new CliError("schema requires exactly one TOOL", EXIT.USAGE);
    }
    [tool] = positional;
  } else if (command === "tabs") {
    if (
      positional.length !== 0
      || argsJson !== undefined
      || !urlContains?.trim()
      || exactTextOptionsUsed
    ) {
      throw new CliError("tabs requires --url-contains STR", EXIT.USAGE);
    }
  } else if (command === "call") {
    if (
      positional.length !== 1
      || argsJson === undefined
      || urlContains !== undefined
      || exactTextOptionsUsed
    ) {
      throw new CliError("call requires TOOL and --args-json JSON", EXIT.USAGE);
    }
    [tool] = positional;
  } else if (["exact-text", "exact-selector-click"].includes(command)) {
    if (positional.length !== 0 || argsJson !== undefined || urlContains !== undefined) {
      throw new CliError(`${command} accepts only its named options`, EXIT.USAGE);
    }
    exactText = exactText?.replace(/\s+/g, " ").trim();
    scopeSelector = scopeSelector.trim();
    if (!exactText || exactText.length > 200) {
      throw new CliError(`${command} requires --text with 1 to 200 characters`, EXIT.USAGE);
    }
    if (!scopeSelector || scopeSelector.length > 500) {
      throw new CliError("--scope-selector must contain 1 to 500 characters", EXIT.USAGE);
    }
    if (tabId === undefined) {
      throw new CliError(`${command} requires --tab-id for deterministic legacy targeting`, EXIT.USAGE);
    }
    if (command === "exact-selector-click") {
      targetSelector = targetSelector?.trim();
      if (!targetSelector || targetSelector.length > 500) {
        throw new CliError(
          "exact-selector-click requires --selector with 1 to 500 characters",
          EXIT.USAGE,
        );
      }
    } else if (targetSelector !== undefined) {
      throw new CliError("exact-text does not accept --selector", EXIT.USAGE);
    }
  }

  let toolArgs;
  if (command === "call") {
    try {
      toolArgs = JSON.parse(argsJson);
    } catch {
      throw new CliError("--args-json must be valid JSON", EXIT.USAGE);
    }
    if (toolArgs === null || Array.isArray(toolArgs) || typeof toolArgs !== "object") {
      throw new CliError("--args-json must decode to a JSON object", EXIT.USAGE);
    }
    validateSafeCall(tool, toolArgs);
  }

  return {
    command,
    endpoint,
    timeoutMs,
    maxOutputBytes,
    tool,
    toolArgs,
    urlContains,
    exactText,
    scopeSelector,
    targetSelector,
    tabId,
  };
}

export function stripUrlQuery(rawUrl) {
  if (typeof rawUrl !== "string") return rawUrl;
  try {
    const parsed = new URL(rawUrl);
    parsed.username = "";
    parsed.password = "";
    parsed.search = "";
    parsed.hash = "";
    return parsed.toString();
  } catch {
    const marker = rawUrl.search(/[?#]/);
    return marker === -1 ? rawUrl : rawUrl.slice(0, marker);
  }
}

function redactInlineSecrets(value) {
  return value
    .replace(/\b(Bearer\s+)[A-Za-z0-9._~+/=-]+/gi, "$1[REDACTED]")
    .replace(
      /\b(authorization|auth(?:token|code)|proxy-authorization|cookie|set-cookie|password|passwd|api[_-]?key|access[_-]?token|refresh[_-]?token|token|secret|session(?:[_-]?id|token)?|csrf(?:token)?|xsrf(?:token)?)\s*[:=]\s*([^\s,;]+)/gi,
      "$1=[REDACTED]",
    );
}

function stripEmbeddedUrlQuery(value) {
  const withoutAbsoluteQueries = value.replace(URL_IN_TEXT, (match) => {
    const trailing = match.match(/[),.;!?]+$/)?.[0] ?? "";
    const url = trailing ? match.slice(0, -trailing.length) : match;
    return `${stripUrlQuery(url)}${trailing}`;
  });
  return withoutAbsoluteQueries.replace(
    /(^|[\s"'(=:])((?:\/|\.\/|\.\.\/)[^\s"'<>]+)/g,
    (match, prefix, relativeUrl) => `${prefix}${stripUrlQuery(relativeUrl)}`,
  );
}

function sanitizeString(value, depth, seen) {
  if (JWT_LIKE.test(value)) return `[REDACTED_JWT length=${value.length}]`;
  if (BASE64_LIKE.test(value) || LONG_HEX.test(value)) {
    return `[REDACTED_ENCODED_STRING length=${value.length}]`;
  }
  if (/^data:[^,]{0,200};base64,/i.test(value)) {
    return `[REDACTED_DATA_URL length=${value.length}]`;
  }

  const trimmed = value.trim();
  if (/<(?:!doctype|html|head|body|input|a|div|span|script|form|meta)\b/i.test(trimmed)) {
    return `[REDACTED_HTML_CONTENT length=${value.length}]`;
  }
  if (trimmed.length >= 2 && trimmed.length <= 1_000_000 && /^(?:\{|\[)/.test(trimmed)) {
    try {
      const parsed = JSON.parse(trimmed);
      return JSON.stringify(sanitizeDeep(parsed, depth + 1, seen));
    } catch {
      // Ordinary browser text often begins with punctuation. Fall through.
    }
  }

  const sanitized = stripEmbeddedUrlQuery(redactInlineSecrets(value));
  if (sanitized.length > MAX_STRING_CHARS) {
    const preview = sanitized.slice(0, Math.floor(MAX_STRING_CHARS / 2));
    return `${preview}…[TRUNCATED_LONG_STRING original_chars=${sanitized.length}]`;
  }
  return sanitized;
}

export function sanitizeDeep(value, depth = 0, seen = new WeakSet()) {
  if (value === null || value === undefined || typeof value === "boolean" || typeof value === "number") {
    return value;
  }
  if (typeof value === "bigint") return value.toString();
  if (typeof value === "string") return sanitizeString(value, depth, seen);
  if (typeof value !== "object") return String(value);
  if (depth >= MAX_DEPTH) return "[TRUNCATED_MAX_DEPTH]";
  if (seen.has(value)) return "[REDACTED_CIRCULAR]";
  seen.add(value);

  if (Array.isArray(value)) {
    const items = value.slice(0, MAX_ARRAY_ITEMS).map((item) => sanitizeDeep(item, depth + 1, seen));
    if (value.length > MAX_ARRAY_ITEMS) {
      items.push(`[TRUNCATED_ARRAY omitted=${value.length - MAX_ARRAY_ITEMS}]`);
    }
    return items;
  }

  const output = {};
  const entries = Object.entries(value);
  const namedSensitiveField = entries.some(
    ([key, item]) => /^(?:name|key|header)$/i.test(key) && typeof item === "string" && SENSITIVE_KEY.test(item),
  );
  for (const [key, item] of entries.slice(0, MAX_OBJECT_KEYS)) {
    if (SENSITIVE_KEY.test(key)) {
      output[key] = "[REDACTED_SENSITIVE_FIELD]";
    } else if (namedSensitiveField && /^(?:value|content|data)$/i.test(key)) {
      output[key] = "[REDACTED_SENSITIVE_FIELD]";
    } else if ((URL_VALUE_KEY.test(key) || CAMEL_URL_VALUE_KEY.test(key)) && typeof item === "string") {
      output[key] = sanitizeString(stripUrlQuery(item), depth + 1, seen);
    } else {
      output[key] = sanitizeDeep(item, depth + 1, seen);
    }
  }
  if (entries.length > MAX_OBJECT_KEYS) {
    output._truncated_keys = entries.length - MAX_OBJECT_KEYS;
  }
  return output;
}

export function serializeCapped(value, maxBytes = DEFAULT_MAX_OUTPUT_BYTES) {
  const sanitized = sanitizeDeep(value);
  const serialized = JSON.stringify(sanitized);
  const originalBytes = Buffer.byteLength(serialized, "utf8");
  if (originalBytes <= maxBytes) return serialized;

  let previewChars = Math.max(64, maxBytes - 320);
  while (previewChars >= 0) {
    const preview = serialized.slice(0, previewChars);
    const wrapper = JSON.stringify({
      truncated: true,
      original_bytes: originalBytes,
      preview,
    });
    if (Buffer.byteLength(wrapper, "utf8") <= maxBytes) return wrapper;
    previewChars = Math.floor(previewChars * 0.8) - 1;
  }
  return JSON.stringify({ truncated: true, original_bytes: originalBytes });
}

function emit(value, maxOutputBytes) {
  process.stdout.write(`${serializeCapped(value, maxOutputBytes)}\n`);
}

function errorMessage(error) {
  const raw = error instanceof Error ? error.message : String(error);
  return sanitizeDeep(raw);
}

function toolResultErrorMessage(result) {
  const messages = (result?.content ?? [])
    .filter((item) => item?.type === "text" && typeof item.text === "string")
    .map((item) => item.text)
    .slice(0, 3);
  return messages.length > 0 ? sanitizeDeep(messages.join("; ")) : "server returned isError=true";
}

function toolResultTexts(result) {
  return (result?.content ?? [])
    .filter((item) => item?.type === "text" && typeof item.text === "string")
    .map((item) => item.text);
}

export function isExtensionToolMissing(result, toolName) {
  if (!result?.isError) return false;
  const expected = `Tool ${toolName} not found`;
  return toolResultTexts(result).some((text) => text.includes(expected));
}

function successfulTextResult(payload, compatibility) {
  return {
    content: [{ type: "text", text: JSON.stringify(payload) }],
    isError: false,
    _meta: { "aris.compatibility": compatibility },
  };
}

async function rawToolCall(client, name, args, timeoutMs) {
  try {
    return await client.callTool({ name, arguments: args }, undefined, { timeout: timeoutMs });
  } catch (error) {
    throw new CliError(
      `chrome-mcp tool invocation failed: ${errorMessage(error)}`,
      EXIT.TOOL_CALL,
      MUTATING_BROWSER_TOOLS.has(name)
        ? { retryable: false, effect_state: "unknown", state_check_required: true }
        : {},
    );
  }
}

async function closeWithin(closeOperation, timeoutMs) {
  let timer;
  try {
    await Promise.race([
      Promise.resolve().then(closeOperation),
      new Promise((_, reject) => {
        timer = setTimeout(() => reject(new Error("bounded close timeout")), timeoutMs);
        timer.unref?.();
      }),
    ]);
  } finally {
    if (timer) clearTimeout(timer);
  }
}

async function connectClient(endpoint, timeoutMs) {
  let Client;
  let StreamableHTTPClientTransport;
  const sdkRoots = [
    process.env.ARIS_MCP_SDK_ROOT,
    join(homedir(), "node_modules", "@modelcontextprotocol", "sdk"),
    join(dirname(dirname(process.execPath)), "lib", "node_modules", "@modelcontextprotocol", "sdk"),
    join(
      dirname(dirname(process.execPath)),
      "lib",
      "node_modules",
      "mcp-chrome-bridge",
      "node_modules",
      "@modelcontextprotocol",
      "sdk",
    ),
    "/opt/homebrew/lib/node_modules/mcp-chrome-bridge/node_modules/@modelcontextprotocol/sdk",
    "/usr/local/lib/node_modules/mcp-chrome-bridge/node_modules/@modelcontextprotocol/sdk",
  ].filter(Boolean);

  try {
    ({ Client } = await import("@modelcontextprotocol/sdk/client/index.js"));
    ({ StreamableHTTPClientTransport } = await import(
      "@modelcontextprotocol/sdk/client/streamableHttp.js"
    ));
  } catch {
    for (const root of new Set(sdkRoots)) {
      try {
        ({ Client } = await import(pathToFileURL(join(root, "dist", "esm", "client", "index.js"))));
        ({ StreamableHTTPClientTransport } = await import(
          pathToFileURL(join(root, "dist", "esm", "client", "streamableHttp.js"))
        ));
        break;
      } catch {
        Client = undefined;
        StreamableHTTPClientTransport = undefined;
      }
    }
  }
  if (!Client || !StreamableHTTPClientTransport) {
    throw new CliError(
      "@modelcontextprotocol/sdk is unavailable in this Node.js environment",
      EXIT.DEPENDENCY,
    );
  }

  const client = new Client(
    { name: "aris-chrome-mcp-client", version: "1.0.0" },
    { capabilities: {} },
  );
  const transport = new StreamableHTTPClientTransport(new URL(endpoint));
  try {
    await client.connect(transport, { timeout: timeoutMs });
  } catch (error) {
    try {
      await closeWithin(() => transport.close(), 1_000);
    } catch {
      // Preserve the original connection failure.
    }
    throw new CliError(`chrome-mcp connection failed: ${errorMessage(error)}`, EXIT.CONNECTION);
  }
  return { client, transport };
}

async function listAllTools(client, timeoutMs) {
  const tools = [];
  const deadline = Date.now() + timeoutMs;
  const seenCursors = new Set();
  let cursor;
  for (let page = 0; page < 32; page += 1) {
    const remaining = deadline - Date.now();
    if (remaining < 100) {
      throw new CliError("chrome-mcp tools/list exceeded its total timeout", EXIT.CONNECTION);
    }
    const result = await client.listTools(cursor ? { cursor } : undefined, { timeout: remaining });
    tools.push(...(result.tools ?? []));
    cursor = result.nextCursor;
    if (!cursor) return tools;
    if (seenCursors.has(cursor)) {
      throw new CliError("chrome-mcp tools/list repeated a cursor", EXIT.CONNECTION);
    }
    seenCursors.add(cursor);
  }
  throw new CliError("chrome-mcp tools/list exceeded 32 pages", EXIT.CONNECTION);
}

function parseTextPayload(text) {
  if (typeof text !== "string") return undefined;
  try {
    return JSON.parse(text);
  } catch {
    return undefined;
  }
}

function resultPayloads(result) {
  const payloads = [];
  if (result?.structuredContent !== undefined) payloads.push(result.structuredContent);
  for (const content of result?.content ?? []) {
    if (content?.type === "text") {
      const parsed = parseTextPayload(content.text);
      if (parsed !== undefined) payloads.push(parsed);
    }
  }
  return payloads;
}

function collectTabs(value, inheritedWindowId, output, seen) {
  if (value === null || typeof value !== "object" || seen.has(value)) return;
  seen.add(value);
  if (Array.isArray(value)) {
    for (const item of value) collectTabs(item, inheritedWindowId, output, seen);
    return;
  }

  const containerWindowId = value.windowId ?? (Array.isArray(value.tabs) ? value.id : undefined);
  const windowId = containerWindowId ?? inheritedWindowId;
  const tabId = value.tabId ?? (typeof value.url === "string" ? value.id : undefined);
  if (typeof value.url === "string" && tabId !== undefined) {
    output.push({
      tabId,
      windowId: value.windowId ?? windowId ?? null,
      active: Boolean(value.active),
      url: stripUrlQuery(value.url),
    });
  }

  for (const item of Object.values(value)) collectTabs(item, windowId, output, seen);
}

function collectRawTabs(value, inheritedWindowId, output, seen) {
  if (value === null || typeof value !== "object" || seen.has(value)) return;
  seen.add(value);
  if (Array.isArray(value)) {
    for (const item of value) collectRawTabs(item, inheritedWindowId, output, seen);
    return;
  }

  const containerWindowId = value.windowId ?? (Array.isArray(value.tabs) ? value.id : undefined);
  const windowId = containerWindowId ?? inheritedWindowId;
  const tabId = value.tabId ?? (typeof value.url === "string" ? value.id : undefined);
  if (typeof value.url === "string" && tabId !== undefined) {
    output.push({
      tabId,
      windowId: value.windowId ?? windowId ?? null,
      active: Boolean(value.active),
      url: value.url,
    });
  }

  for (const item of Object.values(value)) collectRawTabs(item, windowId, output, seen);
}

function extractRawTabs(result) {
  const candidates = [];
  for (const payload of resultPayloads(result)) {
    collectRawTabs(payload, undefined, candidates, new WeakSet());
  }
  const unique = new Map();
  for (const tab of candidates) {
    unique.set(`${String(tab.windowId)}:${String(tab.tabId)}`, tab);
  }
  return [...unique.values()];
}

function collectWindowFocusStates(value, output, seen) {
  if (value === null || typeof value !== "object" || seen.has(value)) return;
  seen.add(value);
  if (Array.isArray(value)) {
    for (const item of value) collectWindowFocusStates(item, output, seen);
    return;
  }
  if (Array.isArray(value.tabs)) {
    const windowId = value.windowId ?? value.id;
    if (windowId !== undefined && windowId !== null && typeof value.focused === "boolean") {
      output.set(String(windowId), value.focused);
    }
  }
  for (const item of Object.values(value)) collectWindowFocusStates(item, output, seen);
}

function extractWindowFocusStates(result) {
  const output = new Map();
  for (const payload of resultPayloads(result)) {
    collectWindowFocusStates(payload, output, new WeakSet());
  }
  return output;
}

export function extractMatchingTabs(result, urlContains) {
  const candidates = [];
  for (const payload of resultPayloads(result)) {
    collectRawTabs(payload, undefined, candidates, new WeakSet());
  }
  const unique = new Map();
  for (const tab of candidates) {
    if (!tab.url.includes(urlContains)) continue;
    const key = `${String(tab.windowId)}:${String(tab.tabId)}`;
    unique.set(key, { ...tab, url: stripUrlQuery(tab.url) });
  }
  return [...unique.values()];
}

const LEGACY_COMPATIBILITY = "chrome_extension_0_0_6";
const COMPATIBLE_MODERN_TOOLS = new Set([
  "chrome_read_page",
  "chrome_switch_tab",
  "chrome_computer",
  "chrome_handle_download",
]);

function withCompatibilityMeta(result, operation) {
  return {
    ...result,
    _meta: {
      ...(result?._meta ?? {}),
      "aris.compatibility": LEGACY_COMPATIBILITY,
      "aris.compatibility_operation": operation,
    },
  };
}

function assertToolSuccess(result, toolName) {
  const semanticFailure = toolResultReportsSemanticFailure(result);
  if (result?.isError || semanticFailure) {
    throw new CliError(
      result?.isError
        ? `chrome-mcp tool returned an error: ${toolResultErrorMessage(result)}`
        : `chrome-mcp tool reported semantic failure: ${String(toolName ?? "unknown")}`,
      EXIT.TOOL_CALL,
      MUTATING_BROWSER_TOOLS.has(toolName)
        ? { retryable: false, effect_state: "unknown", state_check_required: true }
        : {},
    );
  }
  return result;
}

async function ensureTabActive(client, tabId, timeoutMs, { requireUniqueHttpUrl }) {
  if (tabId === undefined || tabId === null) {
    return { requestedTabId: null, alreadyActive: true, rawUrl: undefined };
  }

  const before = assertToolSuccess(await rawToolCall(client, "get_windows_and_tabs", {}, timeoutMs));
  const rawTabs = extractRawTabs(before);
  const target = rawTabs.find((tab) => String(tab.tabId) === String(tabId));
  if (!target) {
    throw new CliError(`legacy chrome-mcp could not find tabId ${String(tabId)}`, EXIT.TOOL_CALL);
  }
  const windowFocusStates = extractWindowFocusStates(before);
  if (requireUniqueHttpUrl && !/^https?:\/\//i.test(target.url)) {
    throw new CliError(
      `legacy chrome-mcp cannot safely target a non-HTTP(S) tabId ${String(tabId)}`,
      EXIT.TOOL_CALL,
    );
  }
  const exactUrlMatches = rawTabs.filter((tab) => tab.url === target.url);
  if (requireUniqueHttpUrl && exactUrlMatches.length !== 1) {
    throw new CliError(
      "legacy chrome-mcp cannot safely target a tab whose exact URL is duplicated",
      EXIT.TOOL_CALL,
    );
  }
  const targetWindowFocus = windowFocusStates.get(String(target.windowId));
  if (!target.active || targetWindowFocus === false) {
    throw new CliError(
      `target_tab_not_foreground: bring tabId ${String(tabId)} to the front in Chrome and retry; legacy chrome-mcp will not navigate another active tab to imitate a tab switch`,
      EXIT.TOOL_CALL,
    );
  }
  if (windowFocusStates.size > 0 && targetWindowFocus !== true) {
    throw new CliError(
      `target_tab_focus_telemetry_missing: chrome-mcp reports window focus for other windows but not tabId ${String(tabId)}`,
      EXIT.TOOL_CALL,
    );
  }
  return {
    requestedTabId: target.tabId,
    actualTabId: target.tabId,
    alreadyActive: true,
    rawUrl: target.url,
    windowFocusTelemetry: targetWindowFocus === true ? "verified" : "unsupported",
  };
}

async function ensureLegacyTabActive(client, tabId, timeoutMs) {
  const target = await ensureTabActive(
    client,
    tabId,
    timeoutMs,
    { requireUniqueHttpUrl: true },
  );
  if (!target.rawUrl) return target;
  const parsed = new URL(target.rawUrl);
  if (urlHasSensitiveParameters(parsed)) {
    throw new CliError(
      "legacy chrome-mcp refuses URL-targeted compatibility operations on a signed or credential-bearing URL",
      EXIT.TOOL_CALL,
    );
  }
  return target;
}

function toolResultReportsSemanticFailure(result) {
  if (result?.success === false || result?.activated === false) return true;
  return resultPayloads(result).some(
    (payload) => payload
      && typeof payload === "object"
      && !Array.isArray(payload)
      && (payload.success === false || payload.activated === false),
  );
}

function findNestedStringField(value, field, seen = new WeakSet()) {
  if (value === null || typeof value !== "object" || seen.has(value)) return undefined;
  seen.add(value);
  if (typeof value[field] === "string") return value[field];
  for (const item of Object.values(value)) {
    const found = findNestedStringField(item, field, seen);
    if (found !== undefined) return found;
  }
  return undefined;
}

function remainingTimeout(deadline, operation) {
  const remaining = deadline - Date.now();
  if (remaining < 100) {
    throw new CliError(`${operation} exceeded its total timeout`, EXIT.TOOL_CALL);
  }
  return remaining;
}

export function buildLegacyExactTextScript({ text, scopeSelector, markerId, nonce, hmacKeyHex }) {
  const exactTextLiteral = JSON.stringify(text);
  const scopeSelectorLiteral = JSON.stringify(scopeSelector ?? "body");
  const markerIdLiteral = JSON.stringify(markerId);
  const nonceLiteral = JSON.stringify(nonce);
  const hmacKeyHexLiteral = JSON.stringify(hmacKeyHex);
  return `(async () => {
    const markerId = ${markerIdLiteral};
    const nonce = ${nonceLiteral};
    const hmacKeyHex = ${hmacKeyHexLiteral};
    if (document.getElementById(markerId)) return;
    const marker = document.createElement("div");
    marker.id = markerId;
    marker.hidden = true;
    marker.setAttribute("aria-hidden", "true");
    (document.body || document.documentElement).appendChild(marker);
    const emit = async (payload) => {
      const signedPayload = { ...payload, nonce };
      const canonical = JSON.stringify(signedPayload);
      const keyBytes = Uint8Array.from(
        hmacKeyHex.match(/.{2}/g).map((pair) => Number.parseInt(pair, 16)),
      );
      const key = await crypto.subtle.importKey(
        "raw", keyBytes, { name: "HMAC", hash: "SHA-256" }, false, ["sign"],
      );
      const signatureBytes = new Uint8Array(
        await crypto.subtle.sign("HMAC", key, new TextEncoder().encode(canonical)),
      );
      let binary = "";
      for (const byte of signatureBytes) binary += String.fromCharCode(byte);
      const signature = btoa(binary).replaceAll("+", "-").replaceAll("/", "_").replace(/=+$/, "");
      marker.setAttribute(
        "data-aris-result",
        encodeURIComponent(JSON.stringify({ payload: signedPayload, signature })),
      );
    };
    const normalize = (value) => String(value ?? "").replace(/\\s+/g, " ").trim();
    const exactText = normalize(${exactTextLiteral});
    let scopes;
    try {
      scopes = [...document.querySelectorAll(${scopeSelectorLiteral})];
    } catch {
      await emit({ status: "invalid_scope_selector" });
      return;
    }
    if (scopes.length !== 1) {
      await emit({
        status: scopes.length === 0 ? "scope_not_found" : "ambiguous_scope",
        scope_count: scopes.length,
      });
      return;
    }
    const scope = scopes[0];
    const descendants = [...scope.querySelectorAll("*")];
    if (descendants.length > 10000) {
      await emit({ status: "scan_limit_exceeded", scanned_nodes: descendants.length + 1 });
      return;
    }
    const excludedTags = new Set(["SCRIPT", "STYLE", "NOSCRIPT", "META", "HEAD"]);
    const scanDeadline = performance.now() + 200;
    const candidates = [];
    const rendered = (element) => {
      const rect = element.getBoundingClientRect();
      if (rect.width <= 0 || rect.height <= 0) return false;
      for (let current = element; current; current = current.parentElement) {
        const style = getComputedStyle(current);
        if (style.display === "none"
          || style.visibility === "hidden"
          || style.visibility === "collapse"
          || Number.parseFloat(style.opacity || "1") <= 0
          || style.pointerEvents === "none"
          || current.hidden
          || current.inert
          || current.getAttribute?.("aria-hidden") === "true") {
          return false;
        }
      }
      return true;
    };
    for (const element of [scope, ...descendants]) {
      if (performance.now() > scanDeadline) {
        await emit({ status: "scan_limit_exceeded", scanned_nodes: descendants.length + 1 });
        return;
      }
      if (excludedTags.has(element.tagName) || normalize(element.textContent) !== exactText) continue;
      if (!rendered(element)) continue;
      candidates.push(element);
      if (candidates.length > 64) {
        await emit({ status: "too_many_candidates", candidate_count: candidates.length });
        return;
      }
    }
    const deepest = candidates.filter(
      (candidate) => !candidates.some(
        (other) => other !== candidate && candidate.contains(other),
      ),
    );
    const base = {
      candidate_count: candidates.length,
      deepest_candidate_count: deepest.length,
      scanned_nodes: descendants.length + 1,
    };
    if (deepest.length !== 1) {
      await emit({ ...base, status: deepest.length === 0 ? "target_not_found" : "ambiguous_target" });
      return;
    }
    const exactTarget = deepest[0];
    const interactiveSelector = [
      "a[href]", "button", "input", "select", "textarea", "label", "[onclick]",
      "[role='button']", "[role='link']", "[role='menuitem']", "[role='option']",
      "[role='tab']", "[tabindex]",
    ].join(",");
    let actionTarget = exactTarget.closest?.(interactiveSelector);
    if (actionTarget && !scope.contains(actionTarget)) actionTarget = undefined;
    let semanticInteractive = Boolean(actionTarget);
    if (!actionTarget) {
      for (let current = exactTarget; current && scope.contains(current); current = current.parentElement) {
        if (getComputedStyle(current).cursor === "pointer") {
          actionTarget = current;
          semanticInteractive = true;
          break;
        }
      }
    }
    actionTarget ||= exactTarget;
    const disabledAncestor = actionTarget.closest?.("[disabled],[aria-disabled='true'],[inert]");
    if (disabledAncestor || actionTarget.matches?.(":disabled")) {
      await emit({ ...base, status: "target_disabled" });
      return;
    }
    if (!rendered(actionTarget)) {
      await emit({ ...base, status: "target_not_rendered" });
      return;
    }
    const beforeRect = actionTarget.getBoundingClientRect();
    const initiallyInViewport = beforeRect.bottom > 0
      && beforeRect.right > 0
      && beforeRect.top < window.innerHeight
      && beforeRect.left < window.innerWidth;
    actionTarget.scrollIntoView({ block: "center", inline: "nearest" });
    const afterRect = actionTarget.getBoundingClientRect();
    const inViewport = afterRect.bottom > 0
      && afterRect.right > 0
      && afterRect.top < window.innerHeight
      && afterRect.left < window.innerWidth;
    if (!inViewport || !rendered(actionTarget)) {
      await emit({ ...base, status: "target_not_in_viewport" });
      return;
    }
    const centerX = Math.min(Math.max(afterRect.left + afterRect.width / 2, 1), window.innerWidth - 1);
    const centerY = Math.min(Math.max(afterRect.top + afterRect.height / 2, 1), window.innerHeight - 1);
    const hit = document.elementFromPoint(centerX, centerY);
    if (!hit || (hit !== actionTarget && !actionTarget.contains(hit))) {
      await emit({ ...base, status: "target_obscured" });
      return;
    }
    await emit({
      ...base,
      status: "ready",
      target_tag: exactTarget.tagName.toLowerCase(),
      action_target_tag: actionTarget.tagName.toLowerCase(),
      semantic_interactive: semanticInteractive,
      initially_in_viewport: initiallyInViewport,
      before_top: Math.round(beforeRect.top),
      after_scroll_top: Math.round(afterRect.top),
      viewport_height: window.innerHeight,
    });
  })();`;
}

export function buildLegacyExactSelectorClickScript({ text, scopeSelector, targetSelector }) {
  const exactTextLiteral = JSON.stringify(text);
  const scopeSelectorLiteral = JSON.stringify(scopeSelector ?? "body");
  const targetSelectorLiteral = JSON.stringify(targetSelector);
  return `(() => {
    const normalize = (value) => String(value ?? "").replace(/\\s+/g, " ").trim();
    const exactText = normalize(${exactTextLiteral});
    let scopes;
    let targets;
    try {
      scopes = [...document.querySelectorAll(${scopeSelectorLiteral})];
      targets = [...document.querySelectorAll(${targetSelectorLiteral})];
    } catch {
      throw new Error("aris_exact_selector_click_invalid_selector");
    }
    if (scopes.length !== 1) throw new Error("aris_exact_selector_click_scope_not_unique");
    if (targets.length !== 1) throw new Error("aris_exact_selector_click_target_not_unique");
    const scope = scopes[0];
    const exactTarget = targets[0];
    if (!scope.contains(exactTarget)) throw new Error("aris_exact_selector_click_outside_scope");
    if (normalize(exactTarget.textContent) !== exactText) {
      throw new Error("aris_exact_selector_click_text_mismatch");
    }
    const rendered = (element) => {
      const rect = element.getBoundingClientRect();
      if (rect.width <= 0 || rect.height <= 0) return false;
      for (let current = element; current; current = current.parentElement) {
        const style = getComputedStyle(current);
        if (style.display === "none"
          || style.visibility === "hidden"
          || style.visibility === "collapse"
          || Number.parseFloat(style.opacity || "1") <= 0
          || style.pointerEvents === "none"
          || current.hidden
          || current.inert
          || current.getAttribute?.("aria-hidden") === "true") return false;
      }
      return true;
    };
    const interactiveSelector = [
      "a[href]", "button", "input", "select", "textarea", "label", "[onclick]",
      "[role='button']", "[role='link']", "[role='menuitem']", "[role='option']",
      "[role='tab']", "[tabindex]",
    ].join(",");
    let actionTarget = exactTarget.closest?.(interactiveSelector);
    if (actionTarget && !scope.contains(actionTarget)) actionTarget = undefined;
    if (!actionTarget) {
      for (let current = exactTarget; current && scope.contains(current); current = current.parentElement) {
        if (getComputedStyle(current).cursor === "pointer") {
          actionTarget = current;
          break;
        }
      }
    }
    actionTarget ||= exactTarget;
    const disabledAncestor = actionTarget.closest?.("[disabled],[aria-disabled='true'],[inert]");
    if (disabledAncestor || actionTarget.matches?.(":disabled")) {
      throw new Error("aris_exact_selector_click_target_disabled");
    }
    if (!rendered(actionTarget)) throw new Error("aris_exact_selector_click_target_not_rendered");
    actionTarget.scrollIntoView({ block: "center", inline: "nearest" });
    const rect = actionTarget.getBoundingClientRect();
    const inViewport = rect.bottom > 0 && rect.right > 0
      && rect.top < window.innerHeight && rect.left < window.innerWidth;
    if (!inViewport || !rendered(actionTarget)) {
      throw new Error("aris_exact_selector_click_target_not_in_viewport");
    }
    const centerX = Math.min(Math.max(rect.left + rect.width / 2, 1), window.innerWidth - 1);
    const centerY = Math.min(Math.max(rect.top + rect.height / 2, 1), window.innerHeight - 1);
    const hit = document.elementFromPoint(centerX, centerY);
    if (!hit || (hit !== actionTarget && !actionTarget.contains(hit))) {
      throw new Error("aris_exact_selector_click_target_obscured");
    }
    if (!(actionTarget instanceof HTMLElement) || typeof HTMLElement.prototype.click !== "function") {
      throw new Error("aris_exact_selector_click_target_not_html");
    }
    HTMLElement.prototype.click.call(actionTarget);
  })();`;
}

function projectLegacyExactTextPayload(payload, nonce) {
  const statuses = new Set([
    "ready", "invalid_scope_selector", "scope_not_found", "ambiguous_scope",
    "scan_limit_exceeded", "too_many_candidates", "target_not_found", "ambiguous_target",
    "target_disabled", "target_not_rendered", "target_not_in_viewport", "target_obscured",
  ]);
  if (!payload || payload.nonce !== nonce || !statuses.has(payload.status)) {
    throw new CliError("legacy exact-text evidence failed nonce/schema validation", EXIT.TOOL_CALL);
  }
  const projected = { status: payload.status };
  const boundedInteger = (key, minimum, maximum) => {
    const value = payload[key];
    if (value === undefined) return;
    if (!Number.isInteger(value) || value < minimum || value > maximum) {
      throw new CliError(`legacy exact-text evidence has invalid ${key}`, EXIT.TOOL_CALL);
    }
    projected[key] = value;
  };
  boundedInteger("scope_count", 0, 10_001);
  boundedInteger("candidate_count", 0, 65);
  boundedInteger("deepest_candidate_count", 0, 65);
  boundedInteger("scanned_nodes", 0, 10_001);
  if (payload.status === "ready") {
    for (const key of ["target_tag", "action_target_tag"]) {
      if (typeof payload[key] !== "string" || !/^[a-z][a-z0-9-]{0,31}$/.test(payload[key])) {
        throw new CliError(`legacy exact-text evidence has invalid ${key}`, EXIT.TOOL_CALL);
      }
      projected[key] = payload[key];
    }
    if (typeof payload.semantic_interactive !== "boolean"
      || typeof payload.initially_in_viewport !== "boolean") {
      throw new CliError("legacy exact-text evidence has invalid boolean fields", EXIT.TOOL_CALL);
    }
    projected.semantic_interactive = payload.semantic_interactive;
    projected.initially_in_viewport = payload.initially_in_viewport;
    boundedInteger("before_top", -10_000_000, 10_000_000);
    boundedInteger("after_scroll_top", -10_000_000, 10_000_000);
    boundedInteger("viewport_height", 1, 100_000);
  }
  return projected;
}

function verifyLegacyExactTextEnvelope(envelope, hmacKeyHex) {
  if (!envelope
    || typeof envelope !== "object"
    || Array.isArray(envelope)
    || !envelope.payload
    || typeof envelope.signature !== "string"
    || !/^[A-Za-z0-9_-]{43}$/.test(envelope.signature)) {
    throw new CliError("legacy exact-text evidence has no valid signed envelope", EXIT.TOOL_CALL);
  }
  const expected = createHmac("sha256", Buffer.from(hmacKeyHex, "hex"))
    .update(JSON.stringify(envelope.payload), "utf8")
    .digest();
  let actual;
  try {
    actual = Buffer.from(envelope.signature, "base64url");
  } catch {
    throw new CliError("legacy exact-text evidence has an invalid signature", EXIT.TOOL_CALL);
  }
  if (actual.length !== expected.length || !timingSafeEqual(actual, expected)) {
    throw new CliError("legacy exact-text evidence signature mismatch", EXIT.TOOL_CALL);
  }
  return envelope.payload;
}

export async function legacyExactTextOperation(client, args, timeoutMs) {
  const deadline = Date.now() + timeoutMs;
  const nonce = randomBytes(12).toString("hex");
  const hmacKeyHex = randomBytes(32).toString("hex");
  const markerId = `aris-mcp-exact-text-${nonce}`;
  const markerIdLiteral = JSON.stringify(markerId);
  const activation = await ensureLegacyTabActive(
    client,
    args.tabId,
    remainingTimeout(deadline, "legacy exact-text"),
  );
  const jsScript = buildLegacyExactTextScript({
    text: args.text,
    scopeSelector: args.scopeSelector,
    markerId,
    nonce,
    hmacKeyHex,
  });
  assertToolSuccess(
    await rawToolCall(
      client,
      "chrome_inject_script",
      compactDefined({ url: activation.rawUrl, type: "MAIN", jsScript }),
      remainingTimeout(deadline, "legacy exact-text"),
    ),
  );
  await new Promise((resolvePromise) => setTimeout(resolvePromise, 75));

  let cleanupUrl = activation.rawUrl;
  try {
    const evidenceActivation = await ensureLegacyTabActive(
      client,
      args.tabId,
      remainingTimeout(deadline, "legacy exact-text"),
    );
    cleanupUrl = evidenceActivation.rawUrl;
    const evidenceResult = assertToolSuccess(
      await rawToolCall(
        client,
        "chrome_get_web_content",
        {
          url: evidenceActivation.rawUrl,
          selector: `#${markerId}`,
          htmlContent: true,
          textContent: false,
        },
        remainingTimeout(deadline, "legacy exact-text"),
      ),
    );
    const htmlContent = resultPayloads(evidenceResult)
      .map((candidate) => findNestedStringField(candidate, "htmlContent"))
      .find((value) => value !== undefined);
    const encoded = htmlContent?.match(/data-aris-result="([^"]+)"/)?.[1];
    if (!encoded) {
      throw new CliError("legacy exact-text operation produced no scoped evidence", EXIT.TOOL_CALL);
    }
    const decodedEnvelope = JSON.parse(decodeURIComponent(encoded.replaceAll("&amp;", "&")));
    const authenticatedPayload = verifyLegacyExactTextEnvelope(decodedEnvelope, hmacKeyHex);
    const publicPayload = projectLegacyExactTextPayload(authenticatedPayload, nonce);
    if (publicPayload.status !== "ready") {
      throw new CliError(
        `legacy exact-text target is not ready (status=${publicPayload.status}, candidates=${String(publicPayload.deepest_candidate_count ?? "unknown")})`,
        EXIT.TOOL_CALL,
      );
    }
    return {
      ...publicPayload,
      compatibility: LEGACY_COMPATIBILITY,
      operation: "exact_text_inspect_and_scroll",
      acceptance_evidence: false,
      next_step: "re-read the foreground tab with chrome_read_page before any native click",
    };
  } finally {
    const cleanupScript = `(() => {
      const marker = document.getElementById(${markerIdLiteral});
      marker?.remove();
    })();`;
    try {
      assertToolSuccess(
        await rawToolCall(
          client,
          "chrome_inject_script",
          compactDefined({ url: cleanupUrl, type: "MAIN", jsScript: cleanupScript }),
          Math.max(100, Math.min(1_000, deadline - Date.now())),
        ),
      );
    } catch {
      // Navigation can remove the temporary marker before cleanup.
    }
  }
}

export async function legacyExactSelectorClickOperation(client, args, timeoutMs) {
  const activation = await ensureLegacyTabActive(client, args.tabId, timeoutMs);
  const jsScript = buildLegacyExactSelectorClickScript({
    text: args.text,
    scopeSelector: args.scopeSelector,
    targetSelector: args.targetSelector,
  });
  assertToolSuccess(
    await rawToolCall(
      client,
      "chrome_inject_script",
      { url: activation.rawUrl, type: "MAIN", jsScript },
      timeoutMs,
    ),
    "chrome_inject_script",
  );
  return {
    success: true,
    compatibility: LEGACY_COMPATIBILITY,
    operation: "exact_selector_click",
    effect_state: "attempted",
    acceptance_evidence: false,
    state_check_required: true,
    next_step: "reacquire the route-specific tab and independently read the expected post-click state",
  };
}

async function activateTargetTab(client, tools, tabId, timeoutMs) {
  if (tabId === undefined || tabId === null) return { mode: "current_active_tab" };
  if (tools.some((tool) => tool.name === "chrome_switch_tab")) {
    const modern = await rawToolCall(client, "chrome_switch_tab", { tabId }, timeoutMs);
    if (!modern?.isError) {
      if (toolResultReportsSemanticFailure(modern)) {
        throw new CliError(
          "chrome_switch_tab reported semantic failure",
          EXIT.TOOL_CALL,
          { retryable: false, effect_state: "unknown", state_check_required: true },
        );
      }
      let verified;
      try {
        verified = await ensureTabActive(
          client,
          tabId,
          timeoutMs,
          { requireUniqueHttpUrl: false },
        );
      } catch (error) {
        throw new CliError(
          `chrome_switch_tab post-state verification failed: ${String(errorMessage(error))}`,
          EXIT.TOOL_CALL,
          { retryable: false, effect_state: "unknown", state_check_required: true },
        );
      }
      return { mode: "modern_switch_tab", ...verified };
    }
    if (!isExtensionToolMissing(modern, "chrome_switch_tab")) {
      assertToolSuccess(modern, "chrome_switch_tab");
    }
  }
  const activation = await ensureLegacyTabActive(client, tabId, timeoutMs);
  return { mode: LEGACY_COMPATIBILITY, ...activation };
}

function compactDefined(object) {
  return Object.fromEntries(Object.entries(object).filter(([, value]) => value !== undefined));
}

async function legacyReadPage(client, args, timeoutMs) {
  await ensureLegacyTabActive(client, args.tabId, timeoutMs);
  const legacyArgs = compactDefined({
    textQuery: args.textQuery,
    selector: args.selector,
    includeCoordinates: args.includeCoordinates ?? false,
    types: args.types,
  });
  const result = assertToolSuccess(
    await rawToolCall(client, "chrome_get_interactive_elements", legacyArgs, timeoutMs),
  );
  return withCompatibilityMeta(result, "chrome_read_page->chrome_get_interactive_elements");
}

async function legacySwitchTab(client, args, timeoutMs) {
  const activation = await ensureLegacyTabActive(client, args.tabId, timeoutMs);
  return successfulTextResult(
    { success: true, tabId: activation.actualTabId, activated: true },
    LEGACY_COMPATIBILITY,
  );
}

function coordinateFromArgs(args) {
  if (args.coordinates) return args.coordinates;
  if (Number.isFinite(args.x) && Number.isFinite(args.y)) return { x: args.x, y: args.y };
  return undefined;
}

async function legacyComputer(client, args, timeoutMs) {
  await ensureLegacyTabActive(client, args.tabId, timeoutMs);
  const action = args.action;
  let result;
  let invokedTool;
  if (["left_click", "click"].includes(action)) {
    invokedTool = "chrome_click_element";
    result = await rawToolCall(
      client,
      invokedTool,
      compactDefined({ selector: args.selector, coordinates: coordinateFromArgs(args) }),
      timeoutMs,
    );
  } else if (action === "double_click") {
    throw new CliError(
      "legacy chrome-mcp refuses non-atomic double_click; use one independently verified click at a time",
      EXIT.TOOL_CALL,
      { retryable: false, effect_state: "not_started", state_check_required: false },
    );
  } else if (["fill", "type"].includes(action) && args.selector && args.text !== undefined) {
    invokedTool = "chrome_fill_or_select";
    result = await rawToolCall(
      client,
      invokedTool,
      { selector: args.selector, value: args.text },
      timeoutMs,
    );
  } else if (["type", "key"].includes(action)) {
    invokedTool = "chrome_keyboard";
    const keys = args.keys ?? args.text ?? args.key;
    result = await rawToolCall(
      client,
      invokedTool,
      compactDefined({ keys, selector: args.selector, delay: args.delay }),
      timeoutMs,
    );
  } else if (action === "screenshot") {
    invokedTool = "chrome_screenshot";
    result = await rawToolCall(
      client,
      invokedTool,
      compactDefined({ selector: args.selector, storeBase64: false, savePng: false, fullPage: false }),
      timeoutMs,
    );
  } else if (action === "wait") {
    const waitMs = Math.min(Math.max(Number(args.duration ?? args.ms ?? 500), 0), 10_000);
    await new Promise((resolvePromise) => setTimeout(resolvePromise, waitMs));
    return successfulTextResult({ success: true, waitedMs: waitMs }, LEGACY_COMPATIBILITY);
  } else {
    throw new CliError(
      `legacy chrome-mcp does not support chrome_computer action: ${String(action)}`,
      EXIT.TOOL_CALL,
    );
  }
  return withCompatibilityMeta(
    assertToolSuccess(result, invokedTool),
    `chrome_computer:${String(action)}`,
  );
}

async function waitForLegacyDownload(client, args, timeoutMs) {
  const filenameContains = typeof args.filenameContains === "string" ? args.filenameContains.trim() : "";
  if (!filenameContains) {
    throw new CliError(
      "legacy download fallback requires a non-empty filenameContains filter",
      EXIT.USAGE,
    );
  }

  // Prove that the shared Chrome bridge is still live, but never expose its tab inventory here.
  assertToolSuccess(await rawToolCall(client, "get_windows_and_tabs", {}, timeoutMs));
  const downloadsDir = resolve(homedir(), "Downloads");
  if (args.directory !== undefined && resolve(args.directory) !== downloadsDir) {
    throw new CliError("legacy download fallback is restricted to the user's Downloads directory", EXIT.USAGE);
  }
  const lookbackMs = Math.min(Math.max(Number(args.lookbackMs ?? 120_000), 0), 600_000);
  const deadline = Date.now() + timeoutMs;
  const threshold = Date.now() - lookbackMs;
  const sizes = new Map();

  while (Date.now() <= deadline) {
    const names = await readdir(downloadsDir);
    for (const name of names) {
      if (!name.includes(filenameContains) || name.endsWith(".crdownload")) continue;
      const path = join(downloadsDir, name);
      const info = await stat(path);
      if (!info.isFile() || info.mtimeMs < threshold) continue;
      const previousSize = sizes.get(path);
      sizes.set(path, info.size);
      if (args.waitForComplete === false || previousSize === info.size) {
        return successfulTextResult(
          {
            success: true,
            filename: basename(path),
            size: info.size,
            state: "completed",
            completion: "fallback_directory_increment",
          },
          LEGACY_COMPATIBILITY,
        );
      }
    }
    await new Promise((resolvePromise) => setTimeout(resolvePromise, 500));
  }
  throw new CliError("legacy download fallback timed out waiting for the filtered file", EXIT.TOOL_CALL);
}

async function legacyCompatibilityCall(client, name, args, timeoutMs) {
  if (name === "chrome_read_page") return legacyReadPage(client, args, timeoutMs);
  if (name === "chrome_switch_tab") return legacySwitchTab(client, args, timeoutMs);
  if (name === "chrome_computer") return legacyComputer(client, args, timeoutMs);
  if (name === "chrome_handle_download") return waitForLegacyDownload(client, args, timeoutMs);
  throw new CliError(`chrome-mcp tool not found: ${name}`, EXIT.TOOL_NOT_FOUND);
}

export async function callToolWithCompatibility(client, tools, name, args, timeoutMs) {
  validateSafeCall(name, args);
  const advertised = tools.some((tool) => tool.name === name);

  if (name === "chrome_switch_tab") {
    const activation = await activateTargetTab(client, tools, args.tabId, timeoutMs);
    return successfulTextResult(
      {
        success: true,
        tabId: activation.actualTabId ?? args.tabId,
        activated: true,
        activationMode: activation.mode,
      },
      activation.mode,
    );
  }

  if (name === "chrome_navigate") {
    const activation = await activateTargetTab(client, tools, args.tabId, timeoutMs);
    const compatibleArgs = { ...args };
    if (activation.mode !== "modern_switch_tab") delete compatibleArgs.tabId;
    const result = assertToolSuccess(
      await rawToolCall(client, name, compatibleArgs, timeoutMs),
      name,
    );
    return activation.mode === LEGACY_COMPATIBILITY
      ? withCompatibilityMeta(result, "chrome_navigate:active-tab")
      : result;
  }

  if (["chrome_click_element", "chrome_fill_or_select", "chrome_keyboard", "chrome_screenshot"].includes(name)) {
    const activation = await activateTargetTab(client, tools, args.tabId, timeoutMs);
    let compatibleArgs = { ...args };
    if (activation.mode !== "modern_switch_tab") delete compatibleArgs.tabId;
    if (name === "chrome_click_element") {
      if (args.selectorType && args.selectorType !== "css") {
        throw new CliError("legacy chrome-mcp click fallback supports CSS selectors only", EXIT.TOOL_CALL);
      }
      if (args.ref && !args.selector && !args.coordinates) {
        throw new CliError("legacy chrome-mcp click fallback cannot resolve modern element refs", EXIT.TOOL_CALL);
      }
      compatibleArgs = compactDefined({
        tabId: activation.mode === "modern_switch_tab" ? args.tabId : undefined,
        selector: args.selector,
        coordinates: coordinateFromArgs(args),
        waitForNavigation: args.waitForNavigation,
        timeout: args.timeout,
      });
    } else if (name === "chrome_fill_or_select") {
      if (!args.selector) {
        throw new CliError("legacy chrome-mcp fill fallback requires a CSS selector", EXIT.TOOL_CALL);
      }
      compatibleArgs = compactDefined({
        tabId: activation.mode === "modern_switch_tab" ? args.tabId : undefined,
        selector: args.selector,
        value: args.value,
      });
    }
    const result = assertToolSuccess(
      await rawToolCall(client, name, compatibleArgs, timeoutMs),
      name,
    );
    return activation.mode === LEGACY_COMPATIBILITY
      ? withCompatibilityMeta(result, `${name}:active-tab`)
      : result;
  }

  if (advertised) {
    const direct = await rawToolCall(client, name, args, timeoutMs);
    if (!direct?.isError) return assertToolSuccess(direct, name);
    if (!isExtensionToolMissing(direct, name)) assertToolSuccess(direct, name);
  }
  if (COMPATIBLE_MODERN_TOOLS.has(name)) {
    return legacyCompatibilityCall(client, name, args, timeoutMs);
  }
  if (!advertised) throw new CliError(`chrome-mcp tool not found: ${name}`, EXIT.TOOL_NOT_FOUND);
  throw new CliError(`chrome-mcp tool returned an error: ${name}`, EXIT.TOOL_CALL);
}

function runSelfTest() {
  const fixture = {
    password: "do-not-print-password",
    nested: {
      access_token: "do-not-print-token",
      url: "https://example.test/file.pdf?X-Amz-Signature=do-not-print-signature#fragment",
      signed_url: "/download/file.pdf?X-Amz-Signature=do-not-print-relative-signature",
      header: { name: "Authorization", value: "do-not-print-header" },
      serialized: JSON.stringify({ cookie: "do-not-print-cookie", keep: "yes" }),
      encoded: "Q".repeat(160),
      long: "visible ".repeat(400),
    },
  };
  const rendered = serializeCapped(fixture, 4_096);
  const forbidden = [
    "do-not-print-password",
    "do-not-print-token",
    "do-not-print-signature",
    "do-not-print-cookie",
    "do-not-print-relative-signature",
    "do-not-print-header",
    "X-Amz-Signature",
  ];
  const passed = forbidden.every((needle) => !rendered.includes(needle))
    && rendered.includes("[REDACTED_SENSITIVE_FIELD]")
    && rendered.includes("[REDACTED_ENCODED_STRING")
    && rendered.includes("[TRUNCATED_LONG_STRING")
    && Buffer.byteLength(rendered, "utf8") <= 4_096;
  if (!passed) throw new CliError("redaction self-test failed", EXIT.INTERNAL);
  return { ok: true, checks: ["deep-redaction", "url-query-removal", "encoded-string", "long-string", "output-cap"] };
}

async function execute(options) {
  if (options.command === "self-test") return runSelfTest();

  const { client, transport } = await connectClient(options.endpoint, options.timeoutMs);
  try {
    if (options.command === "tabs") {
      const result = assertToolSuccess(
        await rawToolCall(client, "get_windows_and_tabs", {}, options.timeoutMs),
      );
      const windowFocusStates = extractWindowFocusStates(result);
      const tabs = extractMatchingTabs(result, options.urlContains).map((tab) => ({
        ...tab,
        windowFocused: windowFocusStates.get(String(tab.windowId)) ?? null,
        windowFocusTelemetry: windowFocusStates.has(String(tab.windowId))
          ? "supported"
          : "unsupported",
      }));
      return { ok: true, count: tabs.length, tabs };
    }

    if (options.command === "exact-text") {
      const result = await legacyExactTextOperation(
        client,
        {
          text: options.exactText,
          scopeSelector: options.scopeSelector,
          tabId: options.tabId,
        },
        options.timeoutMs,
      );
      return { ok: true, operation: "exact-text", result };
    }

    if (options.command === "exact-selector-click") {
      const result = await legacyExactSelectorClickOperation(
        client,
        {
          text: options.exactText,
          scopeSelector: options.scopeSelector,
          targetSelector: options.targetSelector,
          tabId: options.tabId,
        },
        options.timeoutMs,
      );
      return { ok: true, operation: "exact-selector-click", result };
    }

    let tools;
    try {
      tools = await listAllTools(client, options.timeoutMs);
    } catch (error) {
      throw new CliError(`chrome-mcp tools/list failed: ${errorMessage(error)}`, EXIT.CONNECTION);
    }

    if (options.command === "list-tools") {
      return {
        ok: true,
        count: tools.length,
        tools: tools.map((tool) => ({
          name: tool.name,
          description: tool.description ? tool.description.slice(0, 240) : undefined,
        })),
      };
    }

    if (options.command === "schema") {
      const tool = tools.find((candidate) => candidate.name === options.tool);
      if (!tool) throw new CliError(`chrome-mcp tool not found: ${options.tool}`, EXIT.TOOL_NOT_FOUND);
      return {
        ok: true,
        name: tool.name,
        description: tool.description,
        inputSchema: tool.inputSchema,
      };
    }

    const result = await callToolWithCompatibility(
      client,
      tools,
      options.tool,
      options.toolArgs,
      options.timeoutMs,
    );
    return { ok: true, tool: options.tool, result };
  } finally {
    try {
      await closeWithin(() => client.close(), 1_000);
    } catch {
      try {
        await closeWithin(() => transport.close(), 1_000);
      } catch {
        // One-shot client: shutdown errors do not invalidate a completed call.
      }
    }
  }
}

export async function main(argv = process.argv.slice(2), env = process.env) {
  let options;
  try {
    options = parseArgs(argv, env);
    if (options.command === "help") {
      process.stdout.write(`${usage()}\n`);
      return EXIT.OK;
    }
    const result = await execute(options);
    emit(result, options.maxOutputBytes);
    return EXIT.OK;
  } catch (error) {
    const exitCode = error instanceof CliError ? error.exitCode : EXIT.INTERNAL;
    const maxOutputBytes = options?.maxOutputBytes ?? DEFAULT_MAX_OUTPUT_BYTES;
    emit(
      {
        ok: false,
        error: errorMessage(error),
        exit_code: exitCode,
        ...(error instanceof CliError ? error.details : {}),
      },
      maxOutputBytes,
    );
    return exitCode;
  }
}

const invokedPath = process.argv[1] ? await realpath(resolve(process.argv[1])).catch(() => "") : "";
const modulePath = await realpath(fileURLToPath(import.meta.url)).catch(() => "");
if (modulePath && invokedPath === modulePath) {
  process.exitCode = await main();
}

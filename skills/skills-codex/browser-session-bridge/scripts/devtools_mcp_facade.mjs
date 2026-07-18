#!/usr/bin/env node

/**
 * ARIS' deliberately small stdio MCP facade for chrome-devtools-mcp.
 *
 * The child MCP remains private.  This process exposes only fixed semantic
 * operations, projects every response into an ARIS-owned shape, and keeps raw
 * page ids, snapshot UIDs, signed URLs, credentials, and child output out of
 * the caller-visible protocol.
 */

import { createHash, randomBytes } from "node:crypto";
import { constants as fsConstants, createReadStream, existsSync } from "node:fs";
import {
  copyFile,
  lstat,
  mkdir,
  readFile,
  readdir,
  realpath,
  stat,
  unlink,
  writeFile,
} from "node:fs/promises";
import { homedir } from "node:os";
import {
  basename,
  dirname,
  extname,
  isAbsolute,
  join,
  relative,
  resolve,
  sep,
} from "node:path";
import { execFile, spawn } from "node:child_process";
import { fileURLToPath } from "node:url";

const SERVER_NAME = "aris-devtools-safe-facade";
const SERVER_VERSION = "0.1.0";
const DEFAULT_PROTOCOL_VERSION = "2025-06-18";
const CHILD_TIMEOUT_MS = 70_000;
const MAX_PUBLIC_STRING = 500;
const MAX_INSPECT_ELEMENTS = 240;
const MAX_INSPECT_PUBLIC_CHARS = 24_000;
const MAX_TAB_RESULTS = 50;
const PARTIAL_SUFFIXES = [".crdownload", ".part", ".partial", ".download", ".tmp"];
const PROFILE_LOCK_NAME = "aris-external-profile.lock.json";
const DEFAULT_DEBUGGING_PORT = 39813;
const FIXED_PDF_DOWNLOAD_SCRIPT = `() => {
  if (!document.body) return { triggered: false };
  let downloadUrl = null;
  if (String(document.contentType || "").toLowerCase() === "application/pdf") {
    downloadUrl = new URL(window.location.href);
  } else {
    const hostname = String(window.location.hostname || "").toLowerCase();
    const wrapperPath = window.location.pathname.startsWith("/doi/pdf/")
      || window.location.pathname.startsWith("/doi/epdf/");
    if ((hostname === "onlinelibrary.wiley.com" || hostname.endsWith(".onlinelibrary.wiley.com"))
      && wrapperPath) {
      const candidates = Array.from(document.querySelectorAll("iframe[src]"))
        .map((frame) => {
          try {
            return new URL(frame.src, window.location.href);
          } catch {
            return null;
          }
        })
        .filter((url) => url
          && url.origin === window.location.origin
          && url.pathname.startsWith("/doi/pdfdirect/"));
      if (candidates.length === 1) downloadUrl = candidates[0];
    }
  }
  if (!downloadUrl) return { triggered: false };
  const link = document.createElement("a");
  link.href = downloadUrl.href;
  link.download = "document.pdf";
  link.rel = "noopener";
  document.body.appendChild(link);
  link.click();
  link.remove();
  return { triggered: true };
}`;
const FIXED_CNKI_CHALLENGE_PROBE_SCRIPT = `() => {
  const hostname = String(window.location.hostname || "").toLowerCase();
  const applicable = hostname === "cnki.net" || hostname.endsWith(".cnki.net");
  if (!applicable) {
    return { applicable: false, present: false, rendered: false, blocking: false };
  }
  const viewportWidth = Math.max(0, window.innerWidth || document.documentElement.clientWidth || 0);
  const viewportHeight = Math.max(0, window.innerHeight || document.documentElement.clientHeight || 0);
  const matches = ["#tcaptcha_transform_dy", "#tCaptchaDyMainWrap"]
    .flatMap((selector) => Array.from(document.querySelectorAll(selector)));
  const rectFor = (element) => element.getBoundingClientRect();
  const renderedInViewport = (element) => {
    const style = window.getComputedStyle(element);
    const rect = rectFor(element);
    const opacity = Number.parseFloat(style.opacity || "1");
    return style.display !== "none"
      && style.visibility !== "hidden"
      && style.visibility !== "collapse"
      && Number.isFinite(opacity)
      && opacity > 0
      && rect.width > 0
      && rect.height > 0
      && rect.right > 0
      && rect.bottom > 0
      && rect.left < viewportWidth
      && rect.top < viewportHeight;
  };
  const renderedMatches = matches.filter(renderedInViewport);
  const intended = ["input.search-input", ".brief h1", "#pdfDown", ".btn-dlpdf a"]
    .flatMap((selector) => Array.from(document.querySelectorAll(selector)))
    .filter(renderedInViewport);
  const surfaces = [];
  for (const element of renderedMatches) {
    let cursor = element;
    for (let depth = 0; cursor && depth < 5; depth += 1, cursor = cursor.parentElement) {
      if (cursor === document.body || cursor === document.documentElement) break;
      if (!surfaces.includes(cursor) && renderedInViewport(cursor)) surfaces.push(cursor);
    }
  }
  const topElementObstructs = intended.some((target) => {
    const rect = rectFor(target);
    const x = Math.min(Math.max(rect.left + rect.width / 2, 0), Math.max(viewportWidth - 1, 0));
    const y = Math.min(Math.max(rect.top + rect.height / 2, 0), Math.max(viewportHeight - 1, 0));
    const top = document.elementFromPoint(x, y);
    return Boolean(top && surfaces.some((surface) => surface === top || surface.contains(top)));
  });
  const viewportArea = Math.max(1, viewportWidth * viewportHeight);
  const modalSurface = surfaces.some((surface) => {
    const style = window.getComputedStyle(surface);
    const rect = rectFor(surface);
    const area = Math.max(0, rect.width) * Math.max(0, rect.height);
    return style.pointerEvents !== "none"
      && (style.position === "fixed" || style.position === "absolute")
      && area >= viewportArea * 0.05;
  });
  return {
    applicable: true,
    present: matches.length > 0,
    rendered: renderedMatches.length > 0,
    blocking: renderedMatches.length > 0 && (topElementObstructs || modalSurface),
  };
}`;
const FIXED_ACTIVE_EDITABLE_VALUE_SCRIPT = `() => {
  const marker = "aris-active-editable-value-v1";
  void marker;
  const pinKey = Symbol.for("aris.safe-facade.editable-pin.v1");
  const element = document.activeElement;
  if (!element || element === document.body || element === document.documentElement) {
    delete globalThis[pinKey];
    return { available: false, sensitive: false, value: "" };
  }
  const tag = String(element.tagName || "").toLowerCase();
  const type = String(element.getAttribute?.("type") || "").toLowerCase();
  const autocomplete = String(element.getAttribute?.("autocomplete") || "").toLowerCase();
  const descriptors = [
    type,
    autocomplete,
    element.getAttribute?.("name"),
    element.getAttribute?.("id"),
    element.getAttribute?.("aria-label"),
    element.getAttribute?.("placeholder"),
  ].filter((value) => typeof value === "string").join(" ").toLowerCase();
  const sensitive = type === "password"
    || type === "hidden"
    || /(?:password|passwd|pwd|credential|username|user[ _-]?name|e-?mail|phone|mobile|one[ _-]?time|otp|verification[ _-]?code|账号|账户|用户名|邮箱|手机号|密码|验证码)/i.test(descriptors);
  if (sensitive) {
    delete globalThis[pinKey];
    return { available: false, sensitive: true, value: "" };
  }
  const editable = tag === "input"
    || tag === "textarea"
    || tag === "select"
    || element.isContentEditable === true;
  if (!editable) {
    delete globalThis[pinKey];
    return { available: false, sensitive: false, value: "" };
  }
  const value = element.isContentEditable === true
    ? String(element.textContent || "")
    : String(element.value ?? "");
  if (value.length > 10000) {
    delete globalThis[pinKey];
    return { available: false, sensitive: false, value: "" };
  }
  globalThis[pinKey] = element;
  return { available: true, sensitive: false, value };
}`;
const FIXED_PINNED_EDITABLE_VALUE_SCRIPT = `() => {
  const marker = "aris-pinned-editable-value-v1";
  void marker;
  const pinKey = Symbol.for("aris.safe-facade.editable-pin.v1");
  const element = globalThis[pinKey];
  delete globalThis[pinKey];
  if (!element || !document.contains(element)) {
    return { available: false, sensitive: false, value: "" };
  }
  const tag = String(element.tagName || "").toLowerCase();
  const type = String(element.getAttribute?.("type") || "").toLowerCase();
  const autocomplete = String(element.getAttribute?.("autocomplete") || "").toLowerCase();
  const descriptors = [
    type,
    autocomplete,
    element.getAttribute?.("name"),
    element.getAttribute?.("id"),
    element.getAttribute?.("aria-label"),
    element.getAttribute?.("placeholder"),
  ].filter((value) => typeof value === "string").join(" ").toLowerCase();
  const sensitive = type === "password"
    || type === "hidden"
    || /(?:password|passwd|pwd|credential|username|user[ _-]?name|e-?mail|phone|mobile|one[ _-]?time|otp|verification[ _-]?code|账号|账户|用户名|邮箱|手机号|密码|验证码)/i.test(descriptors);
  if (sensitive) return { available: false, sensitive: true, value: "" };
  const editable = tag === "input"
    || tag === "textarea"
    || tag === "select"
    || element.isContentEditable === true;
  if (!editable) return { available: false, sensitive: false, value: "" };
  const value = element.isContentEditable === true
    ? String(element.textContent || "")
    : String(element.value ?? "");
  if (value.length > 10000) return { available: false, sensitive: false, value: "" };
  return { available: true, sensitive: false, value };
}`;
const REQUIRED_CHILD_TOOLS = new Set([
  "list_pages",
  "select_page",
  "navigate_page",
  "take_snapshot",
  "click",
  "fill",
  "press_key",
  "wait_for",
  "evaluate_script",
]);
const REQUIRED_CHILD_PROPERTIES = new Map([
  ["list_pages", []],
  ["select_page", ["pageId", "bringToFront"]],
  ["navigate_page", ["type", "url", "timeout"]],
  ["take_snapshot", ["verbose"]],
  ["click", ["uid", "dblClick", "includeSnapshot"]],
  ["fill", ["uid", "value", "includeSnapshot"]],
  ["press_key", ["key", "includeSnapshot"]],
  ["wait_for", ["text", "timeout"]],
  ["evaluate_script", ["function", "args", "filePath", "dialogAction"]],
]);

const SENSITIVE_PARAMETER = /^(?:auth(?:orization)?(?:token|code|header)?|password|passwd|pwd|secret(?:key|token)?|clientsecret|apikey|accesstoken|refreshtoken|idtoken|token|jwt|credential|credentials|session(?:id|token|key|state)?|signature|sig|xamz(?:signature|securitytoken|credential)|awsaccesskeyid|keypairid|oauthverifier|samlresponse|assertion|ticket|code|key)$/i;
const SENSITIVE_ASSIGNMENT = /\b(authorization|auth(?:token|code)|cookie|set-cookie|password|passwd|pwd|api[_-]?key|access[_-]?token|refresh[_-]?token|id[_-]?token|token|secret|session(?:[_-]?(?:id|token|key))?|csrf(?:token)?|xsrf(?:token)?)\s*[:=]\s*([^\s,;]+)/gi;
const ABSOLUTE_URL = /\bhttps?:\/\/[^\s"'<>]+/gi;
const JWT_LIKE = /\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+(?:\.[A-Za-z0-9_-]+)?\b/g;
const LONG_TOKEN = /\b[A-Za-z0-9+/_=-]{80,}\b/g;
const CHALLENGE_SIGNAL = /(?:verify (?:that )?you are human|checking your browser|security verification|cloudflare|turnstile|captcha|not a robot|human verification|验证(?:您|你)?是(?:否)?真人|人机验证|安全验证)/i;
const SLIDER_SIGNAL = /(?:slider|slide to verify|drag (?:the )?(?:slider|puzzle)|滑块|拖动.*验证)/i;
const IMAGE_SIGNAL = /(?:select all images|image captcha|图像验证码|图片验证码|选择.*图片)/i;
const PRESS_HOLD_SIGNAL = /(?:press and hold|按住|长按)/i;
const SAFE_KEYS = new Set([
  "Enter",
  "Tab",
  "Escape",
  "ArrowUp",
  "ArrowDown",
  "ArrowLeft",
  "ArrowRight",
  "PageUp",
  "PageDown",
  "Home",
  "End",
]);

class FacadeError extends Error {
  constructor(code, details = {}) {
    super(code);
    this.name = "FacadeError";
    this.code = code;
    this.details = details;
  }
}

function opaque(prefix) {
  return `${prefix}_${randomBytes(18).toString("base64url")}`;
}

function sleep(ms) {
  return new Promise((resolvePromise) => setTimeout(resolvePromise, ms));
}

function sha256File(path) {
  return new Promise((resolvePromise, rejectPromise) => {
    const hash = createHash("sha256");
    const stream = createReadStream(path);
    stream.on("error", rejectPromise);
    stream.on("data", (chunk) => hash.update(chunk));
    stream.on("end", () => resolvePromise(hash.digest("hex")));
  });
}

function sha256Text(value) {
  return createHash("sha256").update(value, "utf8").digest("hex");
}

function decodeCapped(value) {
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

function normalizedParameterKey(value) {
  return decodeCapped(value)
    .replace(/([a-z0-9])([A-Z])/g, "$1-$2")
    .replace(/[^A-Za-z0-9]/g, "")
    .toLowerCase();
}

function parameterIsSensitive(value) {
  return SENSITIVE_PARAMETER.test(normalizedParameterKey(value));
}

function textHasSensitiveAssignment(value) {
  const decoded = decodeCapped(value);
  const matcher = /(?:^|[?&#;,{])\s*["']?([^"'{}:,=?&#;\s]+)["']?\s*[:=]/g;
  let match;
  while ((match = matcher.exec(decoded)) !== null) {
    if (parameterIsSensitive(match[1])) return true;
  }
  return false;
}

export function urlHasSensitiveParameters(parsed) {
  for (const [key, value] of parsed.searchParams.entries()) {
    if (parameterIsSensitive(key) || textHasSensitiveAssignment(value)) return true;
  }
  return textHasSensitiveAssignment(parsed.hash.slice(1));
}

export function stripUrlDetails(rawUrl) {
  if (typeof rawUrl !== "string") return "";
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

function safePublicString(value, maxLength = MAX_PUBLIC_STRING) {
  let projected = String(value ?? "")
    .replace(JWT_LIKE, "[REDACTED_CREDENTIAL]")
    .replace(LONG_TOKEN, "[REDACTED_CREDENTIAL]")
    .replace(SENSITIVE_ASSIGNMENT, "$1=[REDACTED]")
    .replace(ABSOLUTE_URL, (match) => {
      const punctuation = match.match(/[),.;!?]+$/)?.[0] ?? "";
      const url = punctuation ? match.slice(0, -punctuation.length) : match;
      return `${stripUrlDetails(url)}${punctuation}`;
    });
  if (projected.length > maxLength) {
    projected = `${projected.slice(0, maxLength)}…[TRUNCATED]`;
  }
  return projected;
}

function safeHttpUrl(value) {
  let parsed;
  try {
    parsed = new URL(value);
  } catch {
    throw new FacadeError("invalid_navigation_url");
  }
  if (!["http:", "https:"].includes(parsed.protocol) || parsed.username || parsed.password) {
    throw new FacadeError("invalid_navigation_url");
  }
  if (urlHasSensitiveParameters(parsed)) {
    throw new FacadeError("signed_or_credential_url_rejected");
  }
  return parsed.toString();
}

function expandHomePath(value) {
  if (value === "~") return homedir();
  if (typeof value === "string" && value.startsWith("~/")) {
    return join(homedir(), value.slice(2));
  }
  return value;
}

function agentBrowserConfigPaths(env = process.env) {
  const configHome = env.MY_AGENT_BROWSER_HOME
    ? resolve(expandHomePath(env.MY_AGENT_BROWSER_HOME))
    : join(homedir(), ".config", "agent-skills", "my-agent-browser");
  return {
    configHome,
    configFile: join(configHome, "config.json"),
    lockFile: join(configHome, PROFILE_LOCK_NAME),
  };
}

export async function loadAgentBrowserConfig(env = process.env) {
  const paths = agentBrowserConfigPaths(env);
  let parsed = {};
  try {
    parsed = JSON.parse(await readFile(paths.configFile, "utf8"));
  } catch (error) {
    if (error?.code !== "ENOENT") throw new FacadeError("browser_config_invalid");
  }
  if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
    throw new FacadeError("browser_config_invalid");
  }
  const browser = parsed.browser && typeof parsed.browser === "object" && !Array.isArray(parsed.browser)
    ? parsed.browser
    : {};
  return { paths, config: parsed, browser };
}

function parseExternalBrowserUrl(rawUrl) {
  if (!rawUrl) return null;
  let parsed;
  try {
    parsed = new URL(rawUrl);
  } catch {
    throw new FacadeError("external_browser_url_invalid");
  }
  if (parsed.protocol !== "http:" || parsed.username || parsed.password
    || parsed.search || parsed.hash || parsed.pathname !== "/"
    || !["127.0.0.1", "localhost", "[::1]"].includes(parsed.hostname)) {
    throw new FacadeError("external_browser_url_invalid");
  }
  const port = Number(parsed.port);
  if (!Number.isSafeInteger(port) || port < 1024 || port > 65535) {
    throw new FacadeError("external_browser_url_invalid");
  }
  return { origin: parsed.origin, port };
}

export async function connectionMode(env = process.env) {
  const loaded = await loadAgentBrowserConfig(env);
  const external = parseExternalBrowserUrl(loaded.browser.browserUrl);
  if (external) {
    const configuredPort = Number(loaded.browser.debuggingPort ?? external.port);
    if (configuredPort !== external.port) throw new FacadeError("external_browser_port_mismatch");
    return {
      mode: "external_browser_url",
      external,
      loaded,
    };
  }
  return { mode: "managed_launch", external: null, loaded };
}

export async function probeDevtoolsEndpoint(origin, timeoutMs = 2_000) {
  const external = parseExternalBrowserUrl(origin);
  if (!external) throw new FacadeError("external_browser_url_invalid");
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(`${external.origin}/json/version`, {
      method: "GET",
      redirect: "error",
      cache: "no-store",
      signal: controller.signal,
    });
    if (!response.ok) throw new FacadeError("external_browser_unavailable");
    const declaredLength = Number(response.headers.get("content-length") ?? 0);
    if (Number.isFinite(declaredLength) && declaredLength > 65_536) {
      throw new FacadeError("external_browser_probe_invalid");
    }
    const rawBody = await response.text();
    if (rawBody.length > 65_536) throw new FacadeError("external_browser_probe_invalid");
    let body;
    try {
      body = JSON.parse(rawBody);
    } catch {
      throw new FacadeError("external_browser_probe_invalid");
    }
    if (!body || typeof body.Browser !== "string" || typeof body.webSocketDebuggerUrl !== "string") {
      throw new FacadeError("external_browser_probe_invalid");
    }
    let websocket;
    try {
      websocket = new URL(body.webSocketDebuggerUrl);
    } catch {
      throw new FacadeError("external_browser_probe_invalid");
    }
    if (!["ws:", "wss:"].includes(websocket.protocol)
      || !["127.0.0.1", "localhost", "[::1]"].includes(websocket.hostname)
      || Number(websocket.port) !== external.port) {
      throw new FacadeError("external_browser_probe_invalid");
    }
    return true;
  } catch (error) {
    if (error instanceof FacadeError) throw error;
    throw new FacadeError("external_browser_unavailable");
  } finally {
    clearTimeout(timer);
  }
}

function execFileText(command, args, timeout = 3_000) {
  return new Promise((resolvePromise, rejectPromise) => {
    execFile(command, args, { encoding: "utf8", timeout }, (error, stdout) => {
      if (error) rejectPromise(error);
      else resolvePromise(String(stdout ?? ""));
    });
  });
}

function pidAlive(pid) {
  try {
    process.kill(pid, 0);
    return true;
  } catch {
    return false;
  }
}

function findChromeExecutable() {
  const candidates = process.platform === "darwin"
    ? [
      "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
      "/Applications/Chromium.app/Contents/MacOS/Chromium",
      "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    ]
    : process.platform === "win32"
      ? [
        join(process.env.PROGRAMFILES || "C:\\Program Files", "Google", "Chrome", "Application", "chrome.exe"),
        join(process.env.LOCALAPPDATA || "", "Google", "Chrome", "Application", "chrome.exe"),
      ]
      : ["/usr/bin/google-chrome", "/usr/bin/google-chrome-stable", "/usr/bin/chromium"];
  return candidates.find((candidate) => candidate && existsSync(candidate)) ?? null;
}

export function buildProfileChromeArgs({ port, profileDir, viewport = "maximized" }) {
  if (!Number.isSafeInteger(port) || port < 1024 || port > 65535) {
    throw new FacadeError("profile_port_invalid");
  }
  if (!isAbsolute(profileDir)) throw new FacadeError("profile_directory_invalid");
  const args = [
    `--remote-debugging-port=${port}`,
    `--user-data-dir=${profileDir}`,
    "--no-first-run",
    "--no-default-browser-check",
    "--hide-crash-restore-bubble",
  ];
  if (viewport === "maximized") args.push("--start-maximized");
  else if (typeof viewport === "string" && /^\d{3,4}x\d{3,4}$/.test(viewport)) {
    args.push(`--window-size=${viewport.replace("x", ",")}`);
  }
  return args;
}

export function processCommandMatchesProfile(commandLine, lock) {
  if (typeof commandLine !== "string" || !lock) return false;
  const escapedPortArg = `--remote-debugging-port=${lock.port}`.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const escapedProfileArg = `--user-data-dir=${lock.profileDir}`.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const executableMatches = commandLine.startsWith(`${lock.executable} `)
    || commandLine.startsWith(`"${lock.executable}" `);
  return executableMatches
    && new RegExp(`(?:^|\\s)${escapedPortArg}(?:\\s|$)`).test(commandLine)
    && new RegExp(`(?:^|\\s)${escapedProfileArg}(?:\\s|$)`).test(commandLine);
}

async function listenerPids(port) {
  if (process.platform === "win32") return [];
  try {
    const output = await execFileText("lsof", ["-nP", `-iTCP:${port}`, "-sTCP:LISTEN", "-t"]);
    return output.split(/\r?\n/)
      .map((line) => Number(line.trim()))
      .filter((pid) => Number.isSafeInteger(pid) && pid > 1);
  } catch {
    return [];
  }
}

async function readProfileLock(lockFile) {
  let info;
  try {
    info = await lstat(lockFile);
  } catch (error) {
    if (error?.code === "ENOENT") return null;
    throw new FacadeError("profile_lock_invalid");
  }
  if (!info.isFile() || info.isSymbolicLink()) throw new FacadeError("profile_lock_invalid");
  try {
    const lock = JSON.parse(await readFile(lockFile, "utf8"));
    if (!lock || lock.version !== 1 || !Number.isSafeInteger(lock.pid) || lock.pid < 2
      || !Number.isSafeInteger(lock.port) || typeof lock.profileDir !== "string"
      || typeof lock.executable !== "string") {
      throw new Error("shape");
    }
    return lock;
  } catch (error) {
    if (error instanceof FacadeError) throw error;
    throw new FacadeError("profile_lock_invalid");
  }
}

async function profileRuntimeSpec(env = process.env) {
  const loaded = await loadAgentBrowserConfig(env);
  const port = Number(loaded.browser.debuggingPort ?? DEFAULT_DEBUGGING_PORT);
  if (!Number.isSafeInteger(port) || port < 1024 || port > 65535) {
    throw new FacadeError("profile_port_invalid");
  }
  const configuredProfile = expandHomePath(
    loaded.browser.userDataDir || join(loaded.paths.configHome, "user-data"),
  );
  const unresolvedProfileDir = resolve(configuredProfile);
  const profileDir = await realpath(unresolvedProfileDir).catch(() => unresolvedProfileDir);
  if (profileDir === resolve(homedir()) || profileDir === resolve("/")) {
    throw new FacadeError("profile_directory_invalid");
  }
  const external = parseExternalBrowserUrl(loaded.browser.browserUrl);
  if (external && external.port !== port) throw new FacadeError("external_browser_port_mismatch");
  return {
    loaded,
    port,
    profileDir,
    viewport: loaded.browser.viewport || "maximized",
  };
}

export async function profileStatus(env = process.env) {
  const spec = await profileRuntimeSpec(env);
  const lock = await readProfileLock(spec.loaded.paths.lockFile);
  if (!lock) {
    return { ok: true, running: false, verified: false, reason: "lock_absent" };
  }
  if (lock.port !== spec.port || lock.profileDir !== spec.profileDir || !pidAlive(lock.pid)) {
    return { ok: true, running: false, verified: false, reason: "lock_state_mismatch" };
  }
  let commandLine = "";
  try {
    commandLine = process.platform === "win32"
      ? ""
      : (await execFileText("ps", ["-p", String(lock.pid), "-o", "command="])).trim();
  } catch {
    return { ok: true, running: false, verified: false, reason: "process_inspection_failed" };
  }
  if (!processCommandMatchesProfile(commandLine, lock)) {
    return { ok: true, running: false, verified: false, reason: "process_args_mismatch" };
  }
  const listeners = await listenerPids(lock.port);
  if (listeners.length !== 1 || listeners[0] !== lock.pid) {
    return { ok: true, running: false, verified: false, reason: "listener_owner_mismatch" };
  }
  try {
    await probeDevtoolsEndpoint(`http://127.0.0.1:${lock.port}`);
  } catch {
    return { ok: true, running: false, verified: false, reason: "devtools_probe_failed" };
  }
  return {
    ok: true,
    running: true,
    verified: true,
    pid: lock.pid,
    port: lock.port,
    profile: "dedicated_persistent",
  };
}

export async function profileStart(env = process.env) {
  const spec = await profileRuntimeSpec(env);
  const existingLock = await readProfileLock(spec.loaded.paths.lockFile);
  if (existingLock) {
    const status = await profileStatus(env);
    if (status.verified) return { ...status, already_running: true };
    throw new FacadeError("profile_lock_requires_manual_review");
  }
  if ((await listenerPids(spec.port)).length > 0) throw new FacadeError("unmanaged_profile_port_in_use");
  const executable = findChromeExecutable();
  if (!executable) throw new FacadeError("chrome_executable_unavailable");
  await mkdir(spec.loaded.paths.configHome, { recursive: true });
  await mkdir(spec.profileDir, { recursive: true });
  const canonicalProfile = await realpath(spec.profileDir);
  const args = buildProfileChromeArgs({
    port: spec.port,
    profileDir: canonicalProfile,
    viewport: spec.viewport,
  });
  const child = spawn(executable, args, { detached: true, stdio: "ignore" });
  child.unref();
  const lock = {
    version: 1,
    pid: child.pid,
    port: spec.port,
    profileDir: canonicalProfile,
    executable,
    createdAt: new Date().toISOString(),
  };
  try {
    await writeFile(spec.loaded.paths.lockFile, `${JSON.stringify(lock)}\n`, {
      encoding: "utf8",
      mode: 0o600,
      flag: "wx",
    });
  } catch {
    try { process.kill(child.pid, "SIGTERM"); } catch {}
    throw new FacadeError("profile_lock_create_failed");
  }
  const deadline = Date.now() + 15_000;
  while (Date.now() < deadline) {
    const status = await profileStatus(env);
    if (status.verified) return { ...status, started: true };
    if (!pidAlive(child.pid)) break;
    await sleep(250);
  }
  throw new FacadeError("profile_start_unverified", { manual_review_required: true });
}

export async function profileStop(env = process.env) {
  const spec = await profileRuntimeSpec(env);
  const lock = await readProfileLock(spec.loaded.paths.lockFile);
  if (!lock) return { ok: true, stopped: false, reason: "lock_absent" };
  const status = await profileStatus(env);
  if (!status.verified || status.pid !== lock.pid || status.port !== lock.port) {
    throw new FacadeError("profile_stop_refused_unverified_owner");
  }
  process.kill(lock.pid, "SIGTERM");
  const deadline = Date.now() + 8_000;
  while (Date.now() < deadline && pidAlive(lock.pid)) await sleep(200);
  if (pidAlive(lock.pid)) throw new FacadeError("profile_stop_timeout");
  if ((await listenerPids(lock.port)).length > 0) throw new FacadeError("profile_listener_still_present");
  await unlink(spec.loaded.paths.lockFile);
  return { ok: true, stopped: true, pid: lock.pid, port: lock.port };
}

function assertPlainObject(value) {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    throw new FacadeError("invalid_arguments");
  }
}

function assertExactKeys(value, allowed, required = []) {
  assertPlainObject(value);
  if (Object.keys(value).some((key) => !allowed.includes(key))) {
    throw new FacadeError("unsupported_argument");
  }
  if (required.some((key) => !Object.hasOwn(value, key))) {
    throw new FacadeError("missing_argument");
  }
}

function assertOpaque(value, prefix) {
  if (typeof value !== "string" || !new RegExp(`^${prefix}_[A-Za-z0-9_-]{20,}$`).test(value)) {
    throw new FacadeError("invalid_opaque_reference");
  }
  return value;
}

function boundedString(value, { min = 1, max = 500 } = {}) {
  if (typeof value !== "string" || value.length < min || value.length > max || value.includes("\0")) {
    throw new FacadeError("invalid_string_argument");
  }
  return value;
}

function boundedTimeout(value, fallback, { min = 100, max = 60_000 } = {}) {
  if (value === undefined) return fallback;
  if (!Number.isSafeInteger(value) || value < min || value > max) {
    throw new FacadeError("invalid_timeout");
  }
  return value;
}

function resultTexts(result) {
  return (result?.content ?? [])
    .filter((item) => item?.type === "text" && typeof item.text === "string")
    .map((item) => item.text);
}

function fixedScriptPayload(result, expectedKeys) {
  const sortedExpected = [...expectedKeys].sort();
  for (const text of resultTexts(result)) {
    for (const match of text.matchAll(/```json\s*([\s\S]*?)```/gi)) {
      try {
        const payload = JSON.parse(match[1]);
        if (payload && typeof payload === "object" && !Array.isArray(payload)) {
          const keys = Object.keys(payload).sort();
          if (keys.length === sortedExpected.length
            && keys.every((key, index) => key === sortedExpected[index])) {
            return payload;
          }
        }
      } catch {
        // Ignore malformed child projection; fail closed below.
      }
    }
  }
  return null;
}

function assertChildSuccess(result, operation, { mutation = false } = {}) {
  if (!result || result.isError) {
    throw new FacadeError("browser_operation_failed", {
      operation,
      ...(mutation ? { effect_state: "unknown", state_check_required: true } : {}),
    });
  }
  return result;
}

function parseTextPageLine(line) {
  const match = line.match(/^(\d+):\s+(.+?)(?:\s+\[selected\])?(?:\s+isolatedContext=.*)?$/);
  if (!match) return null;
  const id = Number(match[1]);
  const selected = /\[selected\](?:\s|$)/.test(line);
  const label = match[2].replace(/\s+\[selected\]$/, "");
  let rawUrl = "";
  let title = "";
  const parenthesized = label.match(/^(.*)\((https?:\/\/.*|about:blank)\)$/);
  if (parenthesized) {
    title = parenthesized[1].trim();
    rawUrl = parenthesized[2];
  } else if (/^(?:https?:\/\/|about:blank$)/.test(label)) {
    rawUrl = label;
  }
  if (!Number.isSafeInteger(id) || !rawUrl) return null;
  return { id, rawUrl, title, selected };
}

export function projectPages(result) {
  const structured = result?.structuredContent?.pages;
  const pages = [];
  if (Array.isArray(structured)) {
    for (const page of structured) {
      if (!Number.isSafeInteger(page?.id) || typeof page?.url !== "string") continue;
      pages.push({
        id: page.id,
        rawUrl: page.url,
        title: typeof page.title === "string" ? page.title : "",
        selected: page.selected === true,
      });
    }
  }
  if (pages.length === 0) {
    let inPages = false;
    for (const text of resultTexts(result)) {
      for (const line of text.split(/\r?\n/)) {
        if (line === "## Pages") {
          inPages = true;
          continue;
        }
        if (inPages && line.startsWith("## ")) {
          inPages = false;
          continue;
        }
        if (!inPages) continue;
        const parsed = parseTextPageLine(line);
        if (parsed) pages.push(parsed);
      }
    }
  }
  const unique = new Map();
  for (const page of pages) unique.set(page.id, page);
  return [...unique.values()];
}

function parseSnapshotLine(line) {
  const match = line.match(/^\s*uid=([^\s]+)\s+([^\s]+)(?:\s+"((?:\\.|[^"])*)")?(.*)$/);
  if (!match) return null;
  let name = match[3] ?? "";
  try {
    name = JSON.parse(`"${name}"`);
  } catch {
    // Keep the already bounded raw accessibility label.
  }
  const tail = match[4] ?? "";
  const states = {};
  for (const state of ["checked", "disabled", "expanded", "focusable", "focused", "required", "selected"]) {
    const stateMatch = tail.match(new RegExp(`(?:^|\\s)${state}(?:=\"([^\"]*)\")?(?:\\s|$)`));
    if (stateMatch) states[state] = stateMatch[1] ?? true;
  }
  return {
    rawUid: match[1],
    role: match[2],
    rawName: String(name),
    name: safePublicString(name),
    states,
    challengeText: `${String(name)} ${tail}`,
    credentialTarget: /(?:password|passcode|passwd|密码|口令)/i.test(`${String(name)} ${tail}`)
      || /(?:^|\s)protected(?:\s|$)/i.test(tail),
  };
}

export function parseSnapshot(result) {
  const elements = [];
  for (const text of resultTexts(result)) {
    for (const line of text.split(/\r?\n/)) {
      const element = parseSnapshotLine(line);
      if (element) elements.push(element);
    }
  }
  if (elements.length === 0) throw new FacadeError("snapshot_unavailable");
  return elements;
}

function classifyChallenge(elements) {
  const combined = elements.map((element) => element.challengeText).join("\n");
  const checkboxElements = elements.filter((element) => element.role.toLowerCase() === "checkbox");
  const sliders = elements.filter((element) => element.role.toLowerCase() === "slider");
  const hasGeneralSignal = CHALLENGE_SIGNAL.test(combined);
  const hasSlider = sliders.length > 0 || SLIDER_SIGNAL.test(combined);
  const hasImage = IMAGE_SIGNAL.test(combined);
  const hasPressHold = PRESS_HOLD_SIGNAL.test(combined);

  if (hasPressHold) return { observed: true, kind: "press_hold", supported: false };
  if (hasSlider) return { observed: true, kind: "slider", supported: false };
  if (hasImage) return { observed: true, kind: "image", supported: false };
  if (hasGeneralSignal && checkboxElements.length === 1) {
    return { observed: true, kind: "checkbox", supported: true, rawUid: checkboxElements[0].rawUid };
  }
  if (hasGeneralSignal || checkboxElements.some((item) => CHALLENGE_SIGNAL.test(item.challengeText))) {
    return { observed: true, kind: "unknown", supported: false };
  }
  return { observed: false, kind: "none", supported: false };
}

function publicElement(element, elementRef) {
  return {
    element_ref: elementRef,
    role: safePublicString(element.role, 80),
    name: element.name,
    ...(Object.keys(element.states).length > 0 ? { states: element.states } : {}),
  };
}

function childCommand(env = process.env) {
  if (env.ARIS_DEVTOOLS_MCP_TEST_MODE === "1" && env.ARIS_DEVTOOLS_MCP_TEST_CHILD_JSON) {
    let parsed;
    try {
      parsed = JSON.parse(env.ARIS_DEVTOOLS_MCP_TEST_CHILD_JSON);
    } catch {
      throw new FacadeError("invalid_test_child_configuration");
    }
    if (!Array.isArray(parsed) || parsed.length === 0 || parsed.some((item) => typeof item !== "string")) {
      throw new FacadeError("invalid_test_child_configuration");
    }
    return { command: parsed[0], args: parsed.slice(1) };
  }

  const launcherCandidates = [
    join(homedir(), ".agents", "skills", "my-agent-browser", "scripts", "start-mcp.js"),
    join(homedir(), ".codex", "skills", "my-agent-browser", "scripts", "start-mcp.js"),
  ];
  const launcher = launcherCandidates.find((candidate) => existsSync(candidate));
  if (launcher) return { command: process.execPath, args: [launcher] };

  return {
    command: "chrome-devtools-mcp",
    args: [
      `--userDataDir=${join(homedir(), ".config", "agent-skills", "my-agent-browser", "user-data")}`,
      "--no-category-network",
      "--no-category-performance",
      "--no-category-emulation",
      "--no-performance-crux",
      "--no-usage-statistics",
      "--redact-network-headers",
      "--experimental-structured-content",
    ],
  };
}

class ChildMcpClient {
  constructor(env = process.env) {
    this.env = env;
    this.child = null;
    this.buffer = "";
    this.nextId = 1;
    this.pending = new Map();
    this.initialized = null;
    this.serverInfo = null;
    this.tools = null;
  }

  async start() {
    if (this.initialized) return this.initialized;
    this.initialized = this.#start();
    return this.initialized;
  }

  async #start() {
    const spec = childCommand(this.env);
    this.child = spawn(spec.command, spec.args, {
      cwd: process.cwd(),
      env: { ...this.env },
      stdio: ["pipe", "pipe", "pipe"],
    });
    this.child.stdout.setEncoding("utf8");
    this.child.stdout.on("data", (chunk) => this.#consume(chunk));
    // The child disclaimer/debug channel is intentionally not forwarded.
    this.child.stderr.on("data", () => {});
    this.child.on("error", () => this.#failAll(new FacadeError("browser_child_unavailable")));
    this.child.on("exit", () => this.#failAll(new FacadeError("browser_child_exited")));

    const initialized = await this.request("initialize", {
      protocolVersion: DEFAULT_PROTOCOL_VERSION,
      capabilities: {},
      clientInfo: { name: SERVER_NAME, version: SERVER_VERSION },
    });
    this.serverInfo = initialized?.serverInfo ?? {};
    this.notify("notifications/initialized", {});
    const listed = await this.request("tools/list", {});
    this.tools = Array.isArray(listed?.tools) ? listed.tools : [];
    const names = new Set(this.tools.map((tool) => tool?.name).filter(Boolean));
    const missing = [...REQUIRED_CHILD_TOOLS].filter((name) => !names.has(name));
    if (missing.length > 0) throw new FacadeError("browser_child_schema_incompatible");
    for (const [name, requiredProperties] of REQUIRED_CHILD_PROPERTIES.entries()) {
      const definition = this.tools.find((tool) => tool?.name === name);
      const properties = definition?.inputSchema?.properties;
      if (!properties || requiredProperties.some((property) => !Object.hasOwn(properties, property))) {
        throw new FacadeError("browser_child_schema_incompatible");
      }
    }
    return true;
  }

  #consume(chunk) {
    this.buffer += chunk;
    const lines = this.buffer.split("\n");
    this.buffer = lines.pop() ?? "";
    for (const line of lines) {
      if (!line.trim()) continue;
      let message;
      try {
        message = JSON.parse(line);
      } catch {
        continue;
      }
      if (message.id !== undefined && (message.result !== undefined || message.error !== undefined)) {
        const pending = this.pending.get(String(message.id));
        if (!pending) continue;
        this.pending.delete(String(message.id));
        clearTimeout(pending.timer);
        if (message.error) pending.reject(new FacadeError("browser_child_protocol_error"));
        else pending.resolve(message.result);
      } else if (message.id !== undefined && message.method) {
        this.child?.stdin.write(`${JSON.stringify({
          jsonrpc: "2.0",
          id: message.id,
          error: { code: -32601, message: "Method not supported" },
        })}\n`);
      }
    }
  }

  #failAll(error) {
    for (const pending of this.pending.values()) {
      clearTimeout(pending.timer);
      pending.reject(error);
    }
    this.pending.clear();
  }

  request(method, params, timeoutMs = CHILD_TIMEOUT_MS) {
    if (!this.child?.stdin?.writable) return Promise.reject(new FacadeError("browser_child_unavailable"));
    const id = this.nextId++;
    return new Promise((resolvePromise, rejectPromise) => {
      const timer = setTimeout(() => {
        this.pending.delete(String(id));
        rejectPromise(new FacadeError("browser_child_timeout"));
      }, timeoutMs);
      this.pending.set(String(id), { resolve: resolvePromise, reject: rejectPromise, timer });
      this.child.stdin.write(`${JSON.stringify({ jsonrpc: "2.0", id, method, params })}\n`);
    });
  }

  notify(method, params) {
    if (this.child?.stdin?.writable) {
      this.child.stdin.write(`${JSON.stringify({ jsonrpc: "2.0", method, params })}\n`);
    }
  }

  async callTool(name, args, timeoutMs = CHILD_TIMEOUT_MS) {
    await this.start();
    return this.request("tools/call", { name, arguments: args }, timeoutMs);
  }

  close() {
    try {
      this.child?.kill("SIGTERM");
    } catch {
      // Best effort during process shutdown.
    }
  }
}

function tool(name, description, inputSchema) {
  return {
    name,
    description,
    inputSchema: { type: "object", additionalProperties: false, ...inputSchema },
  };
}

const PUBLIC_TOOLS = Object.freeze([
  tool("aris_health", "Check the private Chrome DevTools child and safe facade contract.", { properties: {} }),
  tool("aris_tabs", "Find HTTP(S) tabs or an exact about:blank bootstrap tab by a query-free stable URL substring. Claim one exact match, or the sole currently selected match when duplicates exist.", {
    properties: { url_contains: { type: "string", minLength: 3, maxLength: 300 } },
    required: ["url_contains"],
  }),
  tool("aris_select", "Select the single tab represented by a fresh opaque page reference and create one page lease.", {
    properties: { page_ref: { type: "string" } },
    required: ["page_ref"],
  }),
  tool("aris_navigate", "Navigate the leased page to a credential-free HTTP(S) URL. initScript is never supported.", {
    properties: { lease_id: { type: "string" }, url: { type: "string" } },
    required: ["lease_id", "url"],
  }),
  tool("aris_inspect", "Create a fresh accessibility snapshot and opaque element references. Any prior snapshot becomes stale.", {
    properties: {
      lease_id: { type: "string" },
      text_query: { type: "string", minLength: 1, maxLength: 200 },
    },
    required: ["lease_id"],
  }),
  tool("aris_click", "Perform one semantic click using an element reference from the current snapshot.", {
    properties: {
      lease_id: { type: "string" },
      snapshot_id: { type: "string" },
      element_ref: { type: "string" },
      challenge_observed: { type: "boolean" },
      action_time_confirmation: { type: "boolean" },
      challenge_token: { type: "string" },
    },
    required: ["lease_id", "snapshot_id", "element_ref"],
  }),
  tool("aris_fill", "Fill one non-credential input and return only boolean value-match evidence; the supplied or observed text is never echoed.", {
    properties: {
      lease_id: { type: "string" },
      snapshot_id: { type: "string" },
      element_ref: { type: "string" },
      text: { type: "string", minLength: 1, maxLength: 10000 },
    },
    required: ["lease_id", "snapshot_id", "element_ref", "text"],
  }),
  tool("aris_key", "Press one allowlisted key after a fresh inspection, with boolean continuity evidence for a preceding verified fill; arbitrary typing and press-hold are unavailable.", {
    properties: { lease_id: { type: "string" }, key: { type: "string" } },
    required: ["lease_id", "key"],
  }),
  tool("aris_wait", "Wait for one text marker, then require a new inspection before any element action.", {
    properties: {
      lease_id: { type: "string" },
      text: { type: "string", minLength: 1, maxLength: 300 },
      timeout_ms: { type: "integer", minimum: 100, maximum: 60000 },
    },
    required: ["lease_id", "text"],
  }),
  tool("aris_challenge_state", "Observe and classify a visible challenge from a fresh accessibility snapshot. Only one checkbox can be eligible.", {
    properties: { lease_id: { type: "string" } },
    required: ["lease_id"],
  }),
  tool("aris_trigger_element_download", "Atomically snapshot ~/Downloads and click one fresh non-challenge link or button, returning only an opaque download baseline.", {
    properties: {
      lease_id: { type: "string" },
      snapshot_id: { type: "string" },
      element_ref: { type: "string" },
    },
    required: ["lease_id", "snapshot_id", "element_ref"],
  }),
  tool("aris_trigger_loaded_pdf_download", "Trigger one browser download from the selected loaded HTTP(S) PDF or allowlisted same-origin Wiley PDF wrapper using a fixed, non-user-programmable action and create its download baseline.", {
    properties: { lease_id: { type: "string" } },
    required: ["lease_id"],
  }),
  tool("aris_download_baseline", "Create an opaque inventory baseline of regular files directly in ~/Downloads.", { properties: {} }),
  tool("aris_download_wait", "Wait for one new, stable, non-partial file in ~/Downloads relative to an opaque baseline.", {
    properties: {
      baseline_id: { type: "string" },
      filename_contains: { type: "string", minLength: 1, maxLength: 160 },
      timeout_ms: { type: "integer", minimum: 100, maximum: 60000 },
    },
    required: ["baseline_id", "filename_contains"],
  }),
  tool("aris_copy_download", "Copy a verified download once into this workspace under .aris/; existing destinations fail closed.", {
    properties: {
      download_ref: { type: "string" },
      destination: { type: "string", pattern: "^\\.aris/" },
    },
    required: ["download_ref", "destination"],
  }),
]);

export class SafeDevtoolsFacade {
  constructor({ env = process.env, cwd = process.cwd(), child = null } = {}) {
    this.env = env;
    this.cwd = resolve(cwd);
    this.child = child ?? new ChildMcpClient(env);
    this.discovery = null;
    this.lease = null;
    this.activeSnapshot = null;
    this.lastFillProof = null;
    this.baselines = new Map();
    this.downloads = new Map();
  }

  async #runFixedScript(script, operation, { mutation = false } = {}) {
    if (script !== FIXED_PDF_DOWNLOAD_SCRIPT
      && script !== FIXED_CNKI_CHALLENGE_PROBE_SCRIPT
      && script !== FIXED_ACTIVE_EDITABLE_VALUE_SCRIPT
      && script !== FIXED_PINNED_EDITABLE_VALUE_SCRIPT) {
      throw new FacadeError("fixed_script_not_allowlisted");
    }
    return assertChildSuccess(
      await this.child.callTool("evaluate_script", { function: script }),
      operation,
      { mutation },
    );
  }

  async #activeEditableValueProof() {
    const result = await this.#runFixedScript(
      FIXED_ACTIVE_EDITABLE_VALUE_SCRIPT,
      "active_editable_value_confirmation",
    );
    const payload = fixedScriptPayload(result, ["available", "sensitive", "value"]);
    if (!payload
      || typeof payload.available !== "boolean"
      || typeof payload.sensitive !== "boolean"
      || typeof payload.value !== "string"
      || payload.value.length > 10_000
      || (payload.available && payload.sensitive)
      || (!payload.available && payload.value !== "")) {
      throw new FacadeError("editable_value_confirmation_unavailable");
    }
    if (!payload.available || payload.sensitive) return null;
    return { sha256: sha256Text(payload.value), length: payload.value.length };
  }

  async #pinnedEditableValueProof() {
    const result = await this.#runFixedScript(
      FIXED_PINNED_EDITABLE_VALUE_SCRIPT,
      "pinned_editable_value_confirmation",
    );
    const payload = fixedScriptPayload(result, ["available", "sensitive", "value"]);
    if (!payload
      || typeof payload.available !== "boolean"
      || typeof payload.sensitive !== "boolean"
      || typeof payload.value !== "string"
      || payload.value.length > 10_000
      || (payload.available && payload.sensitive)
      || (!payload.available && payload.value !== "")) {
      throw new FacadeError("editable_value_confirmation_unavailable");
    }
    if (!payload.available || payload.sensitive) return null;
    return { sha256: sha256Text(payload.value), length: payload.value.length };
  }

  async #cnkiChallengeGeometry(rawUrl) {
    let parsed;
    try {
      parsed = new URL(rawUrl);
    } catch {
      return null;
    }
    const hostname = parsed.hostname.toLowerCase();
    if (hostname !== "cnki.net" && !hostname.endsWith(".cnki.net")) return null;
    const result = await this.#runFixedScript(
      FIXED_CNKI_CHALLENGE_PROBE_SCRIPT,
      "cnki_challenge_geometry",
    );
    const payload = fixedScriptPayload(
      result,
      ["applicable", "present", "rendered", "blocking"],
    );
    if (!payload
      || payload.applicable !== true
      || [payload.present, payload.rendered, payload.blocking].some(
        (value) => typeof value !== "boolean",
      )
      || (payload.blocking && !payload.rendered)
      || (payload.rendered && !payload.present)) {
      throw new FacadeError("challenge_geometry_unavailable");
    }
    return payload;
  }

  async #listPages() {
    const result = assertChildSuccess(await this.child.callTool("list_pages", {}), "list_pages");
    const pages = projectPages(result).filter(
      (page) => /^https?:\/\//i.test(page.rawUrl) || page.rawUrl === "about:blank",
    );
    if (pages.length === 0) throw new FacadeError("no_http_pages_visible");
    return pages;
  }

  async #verifiedLease(leaseId) {
    assertOpaque(leaseId, "lease");
    if (!this.lease || this.lease.id !== leaseId) throw new FacadeError("page_lease_stale");
    const pages = await this.#listPages();
    const matchingId = pages.filter((page) => page.id === this.lease.pageId);
    if (matchingId.length !== 1 || !matchingId[0].selected) {
      this.#invalidateBrowserState();
      throw new FacadeError("page_lease_not_selected");
    }
    const target = matchingId[0];
    if (pages.filter((page) => page.rawUrl === target.rawUrl).length !== 1) {
      this.#invalidateBrowserState();
      throw new FacadeError("page_lease_not_unique");
    }
    if (!this.#fillProofMatchesPage(target)) this.#clearFillProof();
    this.lease.rawUrl = target.rawUrl;
    return target;
  }

  #invalidateSnapshot() {
    this.activeSnapshot = null;
  }

  #invalidateBrowserState() {
    this.lease = null;
    this.discovery = null;
    this.activeSnapshot = null;
    this.lastFillProof = null;
  }


  #clearFillProof() {
    this.lastFillProof = null;
  }

  #fillProofMatchesPage(page) {
    return Boolean(this.lastFillProof
      && this.lastFillProof.pageId === page.id
      && this.lastFillProof.rawUrl === page.rawUrl);
  }

  #requireSnapshot(args) {
    assertOpaque(args.snapshot_id, "snapshot");
    assertOpaque(args.element_ref, "element");
    const snapshot = this.activeSnapshot;
    if (!snapshot || snapshot.id !== args.snapshot_id || snapshot.leaseId !== args.lease_id) {
      throw new FacadeError("snapshot_stale");
    }
    const target = snapshot.elements.get(args.element_ref);
    if (!target) throw new FacadeError("element_reference_stale");
    return { snapshot, target };
  }

  async #takeSnapshot(leaseId, { query = null, challengeOnly = false } = {}) {
    const targetPage = await this.#verifiedLease(leaseId);
    this.#invalidateSnapshot();
    const result = assertChildSuccess(
      await this.child.callTool("take_snapshot", { verbose: false }),
      "take_snapshot",
    );
    const parsed = parseSnapshot(result);
    let challenge = classifyChallenge(parsed);
    const cnkiGeometry = await this.#cnkiChallengeGeometry(targetPage.rawUrl);
    if (cnkiGeometry) {
      if (cnkiGeometry.present && cnkiGeometry.rendered && cnkiGeometry.blocking) {
        challenge = {
          observed: true,
          kind: "slider",
          supported: false,
          renderedGeometryVerified: true,
        };
      } else if (cnkiGeometry.present
        && ["slider", "unknown"].includes(challenge.kind)) {
        challenge = {
          observed: false,
          kind: "none",
          supported: false,
          renderedGeometryVerified: true,
        };
      } else {
        challenge = { ...challenge, renderedGeometryVerified: true };
      }
    }
    const snapshotId = opaque("snapshot");
    const refs = new Map();
    const publicItems = [];
    let publicCharacters = 0;
    let truncated = false;
    const normalizedQuery = query?.toLocaleLowerCase();

    for (const element of parsed) {
      const matchesQuery = !normalizedQuery
        || element.rawName.toLocaleLowerCase().includes(normalizedQuery)
        || element.role.toLocaleLowerCase().includes(normalizedQuery);
      const isChallengeTarget = challenge.rawUid && element.rawUid === challenge.rawUid;
      if ((!challengeOnly && !matchesQuery) || (challengeOnly && !isChallengeTarget)) continue;
      if (publicItems.length >= MAX_INSPECT_ELEMENTS) {
        truncated = true;
        break;
      }
      const elementRef = opaque("element");
      const projected = publicElement(element, elementRef);
      const projectedCharacters = projected.name.length + projected.role.length + 80;
      if (publicCharacters + projectedCharacters > MAX_INSPECT_PUBLIC_CHARS) {
        truncated = true;
        break;
      }
      refs.set(elementRef, element);
      publicItems.push(projected);
      publicCharacters += projectedCharacters;
    }

    let challengeState = { ...challenge };
    if (challenge.supported && challenge.rawUid) {
      const entry = [...refs.entries()].find(([, element]) => element.rawUid === challenge.rawUid);
      if (!entry && challengeOnly) throw new FacadeError("challenge_target_unavailable");
      if (entry) {
        challengeState = {
          ...challenge,
          elementRef: entry[0],
          token: opaque("challenge"),
        };
      }
    }
    this.activeSnapshot = {
      id: snapshotId,
      leaseId,
      elements: refs,
      challenge: challengeState,
    };
    return { snapshotId, publicItems, challenge: challengeState, totalParsed: parsed.length, truncated };
  }

  async #downloadsDirectory() {
    const requested = resolve(homedir(), "Downloads");
    let canonical;
    try {
      canonical = await realpath(requested);
    } catch {
      throw new FacadeError("downloads_directory_unavailable");
    }
    return { requested, canonical };
  }

  async #downloadInventory() {
    const downloads = await this.#downloadsDirectory();
    const entries = new Map();
    const names = await readdir(downloads.requested);
    for (const name of names) {
      if (name !== basename(name) || name.includes("\0")) continue;
      const candidate = join(downloads.requested, name);
      let info;
      try {
        info = await lstat(candidate);
      } catch {
        continue;
      }
      if (!info.isFile() || info.isSymbolicLink()) continue;
      let canonical;
      try {
        canonical = await realpath(candidate);
      } catch {
        continue;
      }
      if (dirname(canonical) !== downloads.canonical) continue;
      entries.set(name, {
        name,
        path: canonical,
        size: info.size,
        mtimeMs: info.mtimeMs,
        ino: info.ino,
        dev: info.dev,
      });
    }
    return { downloads, entries };
  }

  async #assertSafeDestination(destination) {
    boundedString(destination, { min: 7, max: 500 });
    if (isAbsolute(destination) || destination.includes("\0") || destination.includes("\\")
      || /[?#]/.test(destination) || textHasSensitiveAssignment(destination)) {
      throw new FacadeError("copy_destination_rejected");
    }
    const normalizedParts = destination.split("/");
    if (normalizedParts[0] !== ".aris" || normalizedParts.length < 2
      || normalizedParts.some((part) => !part || part === "." || part === ".."
        || textHasSensitiveAssignment(part))) {
      throw new FacadeError("copy_destination_rejected");
    }

    const workspace = await realpath(this.env.ARIS_WORKSPACE_ROOT || this.cwd).catch(() => null);
    if (!workspace) throw new FacadeError("workspace_unavailable");
    const arisRoot = join(workspace, ".aris");
    await mkdir(arisRoot, { recursive: true });
    const canonicalAris = await realpath(arisRoot);
    if (relative(workspace, canonicalAris).startsWith(`..${sep}`) || canonicalAris === workspace) {
      throw new FacadeError("copy_destination_rejected");
    }

    const target = resolve(workspace, destination);
    const targetRelative = relative(canonicalAris, target);
    if (!targetRelative || targetRelative === ".." || targetRelative.startsWith(`..${sep}`) || isAbsolute(targetRelative)) {
      throw new FacadeError("copy_destination_rejected");
    }

    let cursor = canonicalAris;
    for (const part of targetRelative.split(sep).slice(0, -1)) {
      cursor = join(cursor, part);
      try {
        const info = await lstat(cursor);
        if (info.isSymbolicLink() || !info.isDirectory()) throw new FacadeError("copy_destination_rejected");
      } catch (error) {
        if (error instanceof FacadeError) throw error;
        if (error?.code !== "ENOENT") throw new FacadeError("copy_destination_rejected");
        await mkdir(cursor);
      }
    }
    const canonicalParent = await realpath(dirname(target));
    const parentRelative = relative(canonicalAris, canonicalParent);
    if (parentRelative === ".." || parentRelative.startsWith(`..${sep}`) || isAbsolute(parentRelative)) {
      throw new FacadeError("copy_destination_rejected");
    }
    return { target, destination: normalizedParts.join("/") };
  }

  async call(name, args = {}) {
    switch (name) {
      case "aris_health": {
        assertExactKeys(args, []);
        const connection = await connectionMode(this.env);
        if (connection.mode === "external_browser_url") {
          await probeDevtoolsEndpoint(connection.external.origin);
        }
        await this.child.start();
        let browserTransportVerified = false;
        if (connection.mode === "external_browser_url") {
          assertChildSuccess(
            await this.child.callTool("list_pages", {}),
            "external_browser_health_check",
          );
          browserTransportVerified = true;
        }
        return {
          ok: true,
          safe_facade: true,
          adapter: "grok_chrome_devtools_mcp",
          facade: SERVER_NAME,
          mcp_server: "browser",
          implementation: "chrome-devtools-mcp",
          profile_mode: "dedicated_persistent",
          version: SERVER_VERSION,
          child: {
            name: safePublicString(this.child.serverInfo?.name || "chrome_devtools", 80),
            version: safePublicString(this.child.serverInfo?.version || "unknown", 40),
          },
          semantic_tools: PUBLIC_TOOLS.length,
          legacy_http_dependency: false,
          connection_mode: connection.mode,
          browser_transport_verified: browserTransportVerified,
          external_browser_lifecycle: connection.mode === "external_browser_url"
            ? "not_owned_not_stopped"
            : "managed_by_launcher",
        };
      }
      case "aris_tabs": {
        assertExactKeys(args, ["url_contains"], ["url_contains"]);
        const filter = boundedString(args.url_contains, { min: 3, max: 300 });
        if (/[?#]/.test(filter) || textHasSensitiveAssignment(filter)) {
          throw new FacadeError("tab_filter_must_be_query_free");
        }
        const pages = await this.#listPages();
        const matches = pages.filter((page) => page.rawUrl.includes(filter));
        const selectedMatches = matches.filter((page) => page.selected);
        const claim = matches.length === 1
          ? matches[0]
          : selectedMatches.length === 1
            ? selectedMatches[0]
            : null;
        const selectionBasis = matches.length === 1
          ? "only_match"
          : claim
            ? "only_selected_match"
            : null;
        const discoveryId = opaque("discovery");
        const orderedMatches = claim && matches.length > 1
          ? [claim, ...matches.filter((page) => page.id !== claim.id)]
          : matches;
        const publicMatches = orderedMatches.slice(0, MAX_TAB_RESULTS).map((page) => ({
          url: stripUrlDetails(page.rawUrl),
          title: safePublicString(page.title, 160),
          selected: page.selected,
        }));
        this.discovery = null;
        if (claim) {
          const pageRef = opaque("page");
          publicMatches[0].page_ref = pageRef;
          this.discovery = {
            id: discoveryId,
            pageRef,
            filter,
            page: claim,
            selectionBasis,
          };
        }
        return {
          ok: true,
          match_count: matches.length,
          selected_match_count: selectedMatches.length,
          unique: claim !== null,
          ...(selectionBasis ? { selection_basis: selectionBasis } : {}),
          matches: publicMatches,
          truncated: matches.length > publicMatches.length,
          ...(!claim ? { next_action: "narrow_url_contains_or_focus_one_match" } : {}),
        };
      }
      case "aris_select": {
        assertExactKeys(args, ["page_ref"], ["page_ref"]);
        assertOpaque(args.page_ref, "page");
        const discovery = this.discovery;
        if (!discovery || discovery.pageRef !== args.page_ref) throw new FacadeError("page_reference_stale");
        const pages = await this.#listPages();
        const matches = pages.filter((page) => page.rawUrl.includes(discovery.filter));
        const selectedMatches = matches.filter((page) => page.selected);
        const verifiedMatches = discovery.selectionBasis === "only_selected_match"
          ? selectedMatches
          : matches;
        if (verifiedMatches.length !== 1
          || verifiedMatches[0].id !== discovery.page.id
          || verifiedMatches[0].rawUrl !== discovery.page.rawUrl) {
          this.#invalidateBrowserState();
          throw new FacadeError("page_reference_no_longer_unique");
        }
        assertChildSuccess(
          await this.child.callTool("select_page", { pageId: verifiedMatches[0].id, bringToFront: true }),
          "select_page",
          { mutation: true },
        );
        const after = await this.#listPages();
        const selected = after.filter((page) => page.id === verifiedMatches[0].id && page.selected);
        if (selected.length !== 1 || after.filter((page) => page.rawUrl === selected[0].rawUrl).length !== 1) {
          this.#invalidateBrowserState();
          throw new FacadeError("page_selection_unverified");
        }
        const leaseId = opaque("lease");
        this.lease = {
          id: leaseId,
          pageId: selected[0].id,
          rawUrl: selected[0].rawUrl,
          challengeClickConsumed: false,
        };
        if (!this.#fillProofMatchesPage(selected[0])) this.#clearFillProof();
        this.discovery = null;
        this.#invalidateSnapshot();
        return { ok: true, lease_id: leaseId, selected: true, url: stripUrlDetails(selected[0].rawUrl) };
      }
      case "aris_navigate": {
        assertExactKeys(args, ["lease_id", "url"], ["lease_id", "url"]);
        await this.#verifiedLease(args.lease_id);
        const url = safeHttpUrl(boundedString(args.url, { min: 8, max: 4000 }));
        this.#invalidateSnapshot();
        this.#clearFillProof();
        const result = await this.child.callTool("navigate_page", {
          type: "url",
          url,
          timeout: 60_000,
        });
        assertChildSuccess(result, "navigate_page", { mutation: true });
        if (this.lease) this.lease.challengeClickConsumed = false;
        return { ok: true, effect_state: "attempted", state_check_required: true, url: stripUrlDetails(url) };
      }
      case "aris_inspect": {
        assertExactKeys(args, ["lease_id", "text_query"], ["lease_id"]);
        const query = args.text_query === undefined
          ? null
          : boundedString(args.text_query, { min: 1, max: 200 });
        const snapshot = await this.#takeSnapshot(args.lease_id, { query });
        return {
          ok: true,
          snapshot_id: snapshot.snapshotId,
          element_count: snapshot.publicItems.length,
          truncated: snapshot.truncated,
          query_applied: query !== null,
          elements: snapshot.publicItems,
        };
      }
      case "aris_click": {
        assertExactKeys(
          args,
          ["lease_id", "snapshot_id", "element_ref", "challenge_observed", "action_time_confirmation", "challenge_token"],
          ["lease_id", "snapshot_id", "element_ref"],
        );
        await this.#verifiedLease(args.lease_id);
        const { snapshot, target } = this.#requireSnapshot(args);
        const challenge = snapshot.challenge;
        const challengeFieldsPresent = args.challenge_observed !== undefined
          || args.action_time_confirmation !== undefined
          || args.challenge_token !== undefined;
        const targetIsChallenge = challenge?.observed && challenge.elementRef === args.element_ref;
        if (challenge?.observed && !targetIsChallenge) throw new FacadeError("challenge_blocks_other_clicks");
        if (targetIsChallenge) {
          if (!challenge.supported || challenge.kind !== "checkbox") {
            throw new FacadeError("unsupported_challenge_type");
          }
          if (this.lease?.challengeClickConsumed) throw new FacadeError("challenge_click_already_consumed");
          if (args.challenge_observed !== true || args.action_time_confirmation !== true
            || args.challenge_token !== challenge.token) {
            throw new FacadeError("challenge_action_confirmation_required");
          }
          this.lease.challengeClickConsumed = true;
        } else if (challengeFieldsPresent) {
          throw new FacadeError("challenge_flags_not_allowed_for_ordinary_click");
        }
        if (["slider", "image", "press_hold"].some((signal) => target.challengeText.toLowerCase().includes(signal))) {
          throw new FacadeError("unsupported_challenge_type");
        }
        this.#invalidateSnapshot();
        this.#clearFillProof();
        const result = await this.child.callTool("click", {
          uid: target.rawUid,
          dblClick: false,
          includeSnapshot: false,
        });
        assertChildSuccess(result, "click", { mutation: true });
        return {
          ok: true,
          effect_state: "attempted",
          state_check_required: true,
          ...(targetIsChallenge ? { challenge_checkbox_clicked_once: true } : {}),
        };
      }
      case "aris_fill": {
        assertExactKeys(args, ["lease_id", "snapshot_id", "element_ref", "text"], ["lease_id", "snapshot_id", "element_ref", "text"]);
        const page = await this.#verifiedLease(args.lease_id);
        const text = boundedString(args.text, { min: 1, max: 10_000 });
        const { snapshot, target } = this.#requireSnapshot(args);
        if (snapshot.challenge?.observed) throw new FacadeError("challenge_blocks_fill");
        if (target.credentialTarget) throw new FacadeError("credential_fill_rejected");
        if (["checkbox", "radio", "switch", "slider"].includes(target.role.toLowerCase())) {
          throw new FacadeError("fill_target_rejected");
        }
        this.#invalidateSnapshot();
        this.#clearFillProof();
        const result = await this.child.callTool("fill", {
          uid: target.rawUid,
          value: text,
          includeSnapshot: false,
        });
        assertChildSuccess(result, "fill", { mutation: true });
        const observed = await this.#activeEditableValueProof();
        const expected = { sha256: sha256Text(text), length: text.length };
        const valueMatchesSupplied = Boolean(observed
          && observed.sha256 === expected.sha256
          && observed.length === expected.length);
        if (valueMatchesSupplied) {
          this.lastFillProof = {
            ...expected,
            pageId: page.id,
            rawUrl: page.rawUrl,
          };
        }
        return {
          ok: true,
          effect_state: "attempted",
          state_check_required: true,
          characters_supplied: text.length,
          value_confirmation_available: observed !== null,
          value_matches_supplied: valueMatchesSupplied,
        };
      }
      case "aris_key": {
        assertExactKeys(args, ["lease_id", "key"], ["lease_id", "key"]);
        const page = await this.#verifiedLease(args.lease_id);
        const key = boundedString(args.key, { min: 1, max: 40 });
        if (!SAFE_KEYS.has(key)) throw new FacadeError("key_not_allowlisted");
        if (!this.activeSnapshot || this.activeSnapshot.leaseId !== args.lease_id) {
          throw new FacadeError("fresh_inspection_required");
        }
        if (this.activeSnapshot.challenge?.observed && key === "Enter") {
          throw new FacadeError("challenge_keyboard_activation_rejected");
        }
        const fillProof = this.#fillProofMatchesPage(page) ? this.lastFillProof : null;
        const before = fillProof ? await this.#activeEditableValueProof() : null;
        const matchesBefore = Boolean(fillProof
          && before
          && before.sha256 === fillProof.sha256
          && before.length === fillProof.length);
        if (fillProof && !matchesBefore) throw new FacadeError("fill_value_changed_before_key");
        this.#invalidateSnapshot();
        const result = await this.child.callTool("press_key", { key, includeSnapshot: false });
        assertChildSuccess(result, "press_key", { mutation: true });
        const after = fillProof ? await this.#pinnedEditableValueProof() : null;
        const matchesAfter = Boolean(fillProof
          && after
          && after.sha256 === fillProof.sha256
          && after.length === fillProof.length);
        if (fillProof && !matchesAfter) this.#clearFillProof();
        return {
          ok: true,
          effect_state: "attempted",
          state_check_required: true,
          key,
          ...(fillProof ? {
            value_confirmation_available_before_key: before !== null,
            value_matches_last_fill_before_key: matchesBefore,
            value_confirmation_available_after_key: after !== null,
            value_matches_last_fill_after_key: matchesAfter,
          } : {}),
        };
      }
      case "aris_wait": {
        assertExactKeys(args, ["lease_id", "text", "timeout_ms"], ["lease_id", "text"]);
        await this.#verifiedLease(args.lease_id);
        const text = boundedString(args.text, { min: 1, max: 300 });
        const timeoutMs = boundedTimeout(args.timeout_ms, 15_000);
        this.#invalidateSnapshot();
        this.#clearFillProof();
        const result = await this.child.callTool("wait_for", { text: [text], timeout: timeoutMs }, timeoutMs + 5_000);
        assertChildSuccess(result, "wait_for");
        return { ok: true, found: true, fresh_inspection_required: true };
      }
      case "aris_challenge_state": {
        assertExactKeys(args, ["lease_id"], ["lease_id"]);
        const snapshot = await this.#takeSnapshot(args.lease_id, { challengeOnly: true });
        const challenge = snapshot.challenge;
        if (!challenge.observed) {
          return {
            ok: true,
            observed: false,
            kind: "none",
            supported: false,
            snapshot_id: snapshot.snapshotId,
            ...(challenge.renderedGeometryVerified
              ? { rendered_geometry_verified: true }
              : {}),
          };
        }
        const eligible = challenge.supported && !this.lease?.challengeClickConsumed && challenge.elementRef;
        return {
          ok: true,
          observed: true,
          kind: challenge.kind,
          supported: challenge.supported,
          ...(challenge.renderedGeometryVerified
            ? { rendered_geometry_verified: true }
            : {}),
          action_time_confirmation_required: challenge.supported,
          ...(eligible ? {
            snapshot_id: snapshot.snapshotId,
            element_ref: challenge.elementRef,
            challenge_token: challenge.token,
            click_budget: 1,
          } : {
            snapshot_id: snapshot.snapshotId,
            click_budget: 0,
          }),
        };
      }
      case "aris_trigger_element_download": {
        assertExactKeys(
          args,
          ["lease_id", "snapshot_id", "element_ref"],
          ["lease_id", "snapshot_id", "element_ref"],
        );
        await this.#verifiedLease(args.lease_id);
        const { snapshot, target } = this.#requireSnapshot(args);
        if (snapshot.challenge?.observed) throw new FacadeError("challenge_blocks_download_trigger");
        if (!new Set(["button", "link"]).has(target.role.toLowerCase())
          || target.credentialTarget
          || ["slider", "image", "press and hold"].some(
            (signal) => target.challengeText.toLowerCase().includes(signal),
          )) {
          throw new FacadeError("download_trigger_target_rejected");
        }
        const inventory = await this.#downloadInventory();
        const createdAt = Date.now();
        this.#invalidateSnapshot();
        this.#clearFillProof();
        assertChildSuccess(
          await this.child.callTool("click", {
            uid: target.rawUid,
            dblClick: false,
            includeSnapshot: false,
          }),
          "trigger_element_download",
          { mutation: true },
        );
        const baselineId = opaque("baseline");
        this.baselines.set(baselineId, {
          id: baselineId,
          createdAt,
          entries: inventory.entries,
          consumed: false,
        });
        return {
          ok: true,
          effect_state: "attempted",
          state_check_required: true,
          baseline_id: baselineId,
          click_budget_consumed: 1,
        };
      }
      case "aris_trigger_loaded_pdf_download": {
        assertExactKeys(args, ["lease_id"], ["lease_id"]);
        const target = await this.#verifiedLease(args.lease_id);
        let parsed;
        try {
          parsed = new URL(target.rawUrl);
        } catch {
          throw new FacadeError("loaded_pdf_url_rejected");
        }
        const pathLower = decodeCapped(parsed.pathname).toLowerCase();
        const isDirectPdfPath = pathLower.endsWith(".pdf");
        const isWileyWrapper = (parsed.hostname === "onlinelibrary.wiley.com"
          || parsed.hostname.endsWith(".onlinelibrary.wiley.com"))
          && (pathLower.startsWith("/doi/pdf/") || pathLower.startsWith("/doi/epdf/"));
        if (!/^https?:$/.test(parsed.protocol)
          || parsed.username || parsed.password
          || (!isDirectPdfPath && !isWileyWrapper)) {
          throw new FacadeError("loaded_pdf_url_rejected");
        }
        const inventory = await this.#downloadInventory();
        const createdAt = Date.now();
        this.#invalidateSnapshot();
        this.#clearFillProof();
        const result = await this.#runFixedScript(
          FIXED_PDF_DOWNLOAD_SCRIPT,
          "trigger_loaded_pdf_download",
          { mutation: true },
        );
        const payload = fixedScriptPayload(result, ["triggered"]);
        if (!payload || payload.triggered !== true) {
          throw new FacadeError("loaded_pdf_not_ready", {
            effect_state: "unknown",
            state_check_required: true,
          });
        }
        const baselineId = opaque("baseline");
        this.baselines.set(baselineId, {
          id: baselineId,
          createdAt,
          entries: inventory.entries,
          consumed: false,
        });
        return {
          ok: true,
          effect_state: "attempted",
          state_check_required: true,
          baseline_id: baselineId,
          expected_format: "pdf",
          filename_policy: "server_controlled",
        };
      }
      case "aris_download_baseline": {
        assertExactKeys(args, []);
        const inventory = await this.#downloadInventory();
        const baselineId = opaque("baseline");
        this.baselines.set(baselineId, {
          id: baselineId,
          createdAt: Date.now(),
          entries: inventory.entries,
          consumed: false,
        });
        return { ok: true, baseline_id: baselineId, scope: "~/Downloads", opaque: true };
      }
      case "aris_download_wait": {
        assertExactKeys(args, ["baseline_id", "filename_contains", "timeout_ms"], ["baseline_id", "filename_contains"]);
        assertOpaque(args.baseline_id, "baseline");
        const baseline = this.baselines.get(args.baseline_id);
        if (!baseline || baseline.consumed) throw new FacadeError("download_baseline_stale");
        const filter = boundedString(args.filename_contains, { min: 1, max: 160 });
        if (filter !== basename(filter) || /[\\/*?\[\]]/.test(filter) || textHasSensitiveAssignment(filter)) {
          throw new FacadeError("download_filter_rejected");
        }
        const timeoutMs = boundedTimeout(args.timeout_ms, 30_000);
        const pollMs = boundedTimeout(Number(this.env.ARIS_DEVTOOLS_DOWNLOAD_POLL_MS || 500), 500, { min: 10, max: 2_000 });
        const deadline = Date.now() + timeoutMs;
        const stability = new Map();
        while (Date.now() <= deadline) {
          const inventory = await this.#downloadInventory();
          const names = [...inventory.entries.keys()];
          const candidates = [];
          for (const entry of inventory.entries.values()) {
            if (!entry.name.includes(filter) || PARTIAL_SUFFIXES.some((suffix) => entry.name.endsWith(suffix))) continue;
            if (names.some((name) => PARTIAL_SUFFIXES.some((suffix) => name === `${entry.name}${suffix}`))) continue;
            const before = baseline.entries.get(entry.name);
            const changed = !before
              || before.size !== entry.size
              || before.mtimeMs !== entry.mtimeMs
              || before.ino !== entry.ino
              || before.dev !== entry.dev;
            if (!changed || entry.mtimeMs < baseline.createdAt - 2_000) continue;
            const signature = `${entry.size}:${entry.mtimeMs}:${entry.ino}:${entry.dev}`;
            const previous = stability.get(entry.name);
            stability.set(entry.name, { signature, samples: previous?.signature === signature ? previous.samples + 1 : 1 });
            if (stability.get(entry.name).samples >= 2) candidates.push(entry);
          }
          if (candidates.length > 1) throw new FacadeError("download_match_not_unique");
          if (candidates.length === 1) {
            const entry = candidates[0];
            const downloadRef = opaque("download");
            this.downloads.set(downloadRef, { ...entry, copied: false });
            baseline.consumed = true;
            return {
              ok: true,
              download_ref: downloadRef,
              filename: safePublicString(entry.name, 180),
              size: entry.size,
              state: "stable_complete",
            };
          }
          await sleep(pollMs);
        }
        throw new FacadeError("download_wait_timeout");
      }
      case "aris_copy_download": {
        assertExactKeys(args, ["download_ref", "destination"], ["download_ref", "destination"]);
        assertOpaque(args.download_ref, "download");
        const download = this.downloads.get(args.download_ref);
        if (!download || download.copied) throw new FacadeError("download_reference_stale");
        const sourceInfo = await lstat(download.path).catch(() => null);
        if (!sourceInfo?.isFile() || sourceInfo.isSymbolicLink()
          || sourceInfo.size !== download.size
          || sourceInfo.mtimeMs !== download.mtimeMs
          || sourceInfo.ino !== download.ino
          || sourceInfo.dev !== download.dev) {
          throw new FacadeError("download_source_changed");
        }
        const downloads = await this.#downloadsDirectory();
        const sourceCanonical = await realpath(download.path);
        if (dirname(sourceCanonical) !== downloads.canonical) throw new FacadeError("download_source_rejected");
        const destination = await this.#assertSafeDestination(args.destination);
        if (await lstat(destination.target).then(() => true).catch((error) => {
          if (error?.code === "ENOENT") return false;
          throw new FacadeError("copy_destination_rejected");
        })) {
          throw new FacadeError("copy_collision");
        }
        await copyFile(sourceCanonical, destination.target, fsConstants.COPYFILE_EXCL);
        const copiedBefore = await stat(destination.target, { bigint: true });
        if (!copiedBefore.isFile() || copiedBefore.size !== BigInt(download.size)) {
          throw new FacadeError("copy_verification_failed");
        }
        const sha256 = await sha256File(destination.target);
        const copiedAfter = await stat(destination.target, { bigint: true });
        if (!copiedAfter.isFile()
          || copiedAfter.size !== copiedBefore.size
          || copiedAfter.mtimeNs !== copiedBefore.mtimeNs
          || copiedAfter.ino !== copiedBefore.ino
          || copiedAfter.dev !== copiedBefore.dev) {
          throw new FacadeError("copy_verification_failed");
        }
        const sizeBytes = Number(copiedAfter.size);
        if (!Number.isSafeInteger(sizeBytes) || sizeBytes < 1) {
          throw new FacadeError("copy_verification_failed");
        }
        const format = extname(destination.target).slice(1).toLowerCase();
        if (!/^(?:pdf|csv|xlsx|zip)$/.test(format)) {
          throw new FacadeError("copy_format_rejected");
        }
        download.copied = true;
        return {
          ok: true,
          destination: destination.destination,
          format,
          size_bytes: sizeBytes,
          // JSON numbers cannot represent current epoch nanoseconds exactly.
          mtime_ns: copiedAfter.mtimeNs.toString(),
          sha256,
          collision_policy: "fail",
        };
      }
      default:
        throw new FacadeError("tool_not_exposed");
    }
  }

  close() {
    this.child.close?.();
  }
}

function toolResult(payload, isError = false) {
  return {
    content: [{ type: "text", text: JSON.stringify(payload) }],
    ...(isError ? { isError: true } : {}),
  };
}

function publicError(error) {
  if (error instanceof FacadeError) {
    return {
      ok: false,
      error: error.code,
      ...error.details,
    };
  }
  return { ok: false, error: "internal_facade_error" };
}

export async function runServer({ input = process.stdin, output = process.stdout, env = process.env } = {}) {
  const facade = new SafeDevtoolsFacade({ env, cwd: env.ARIS_WORKSPACE_ROOT || process.cwd() });
  input.setEncoding("utf8");
  let buffer = "";
  let serializedCalls = Promise.resolve();

  const send = (message) => output.write(`${JSON.stringify(message)}\n`);
  const handle = async (message) => {
    if (!message || message.jsonrpc !== "2.0" || message.id === undefined) return;
    if (message.method === "initialize") {
      send({
        jsonrpc: "2.0",
        id: message.id,
        result: {
          protocolVersion: message.params?.protocolVersion || DEFAULT_PROTOCOL_VERSION,
          capabilities: { tools: { listChanged: false } },
          serverInfo: { name: SERVER_NAME, version: SERVER_VERSION },
        },
      });
      return;
    }
    if (message.method === "ping") {
      send({ jsonrpc: "2.0", id: message.id, result: {} });
      return;
    }
    if (message.method === "tools/list") {
      send({ jsonrpc: "2.0", id: message.id, result: { tools: PUBLIC_TOOLS } });
      return;
    }
    if (message.method === "tools/call") {
      const name = message.params?.name;
      const args = message.params?.arguments ?? {};
      try {
        const result = await facade.call(name, args);
        send({ jsonrpc: "2.0", id: message.id, result: toolResult(result) });
      } catch (error) {
        send({ jsonrpc: "2.0", id: message.id, result: toolResult(publicError(error), true) });
      }
      return;
    }
    send({
      jsonrpc: "2.0",
      id: message.id,
      error: { code: -32601, message: "Method not found" },
    });
  };

  input.on("data", (chunk) => {
    buffer += chunk;
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";
    for (const line of lines) {
      if (!line.trim()) continue;
      let message;
      try {
        message = JSON.parse(line);
      } catch {
        continue;
      }
      if (message.method === "notifications/initialized" || message.method === "notifications/cancelled") continue;
      serializedCalls = serializedCalls.then(() => handle(message), () => handle(message));
    }
  });
  input.on("end", () => facade.close());
  return facade;
}

export async function runProfileCli(argv = process.argv.slice(2), env = process.env) {
  if (argv.length !== 2 || argv[0] !== "profile" || !["start", "status", "stop"].includes(argv[1])) {
    process.stdout.write(`${JSON.stringify({
      ok: false,
      error: "usage",
      usage: "devtools_mcp_facade.mjs profile start|status|stop",
    })}\n`);
    return 2;
  }
  try {
    let result;
    if (argv[1] === "start") result = await profileStart(env);
    else if (argv[1] === "status") result = await profileStatus(env);
    else result = await profileStop(env);
    process.stdout.write(`${JSON.stringify(result)}\n`);
    return 0;
  } catch (error) {
    process.stdout.write(`${JSON.stringify(publicError(error))}\n`);
    return 1;
  }
}

const invoked = process.argv[1]
  ? await realpath(resolve(process.argv[1])).catch(() => resolve(process.argv[1]))
  : "";
const modulePath = await realpath(fileURLToPath(import.meta.url)).catch(() => resolve(fileURLToPath(import.meta.url)));
if (invoked === modulePath) {
  if (process.argv[2] === "profile") {
    process.exitCode = await runProfileCli();
  } else {
    await runServer();
  }
}

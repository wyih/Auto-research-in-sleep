#!/usr/bin/env node

import { appendFileSync, mkdirSync, writeFileSync } from "node:fs";
import { homedir } from "node:os";
import { join } from "node:path";

const logPath = process.env.ARIS_FAKE_CHILD_LOG || "";
let buffer = "";
let selectedPage = Number(process.env.ARIS_FAKE_SELECTED_PAGE ?? "1");
let mode = "ordinary";
let activeValue = "";
let pinnedValue = "";

const requiredToolProperties = {
  list_pages: [],
  select_page: ["pageId", "bringToFront"],
  navigate_page: ["type", "url", "timeout"],
  take_snapshot: ["verbose"],
  click: ["uid", "dblClick", "includeSnapshot"],
  fill: ["uid", "value", "includeSnapshot"],
  press_key: ["key", "includeSnapshot"],
  wait_for: ["text", "timeout"],
  evaluate_script: ["function", "args", "filePath", "dialogAction"],
};

const tools = [
  ...Object.keys(requiredToolProperties),
  // Deliberately advertised by the fake child: the facade must never expose these raw tools.
  "fill_form",
  "drag",
  "upload_file",
  "list_network_requests",
  "take_memory_snapshot",
].map((name) => ({
  name,
  inputSchema: {
    type: "object",
    properties: Object.fromEntries((requiredToolProperties[name] ?? []).map((property) => [property, {}])),
  },
}));

function log(message) {
  if (logPath) appendFileSync(logPath, `${JSON.stringify(message)}\n`, "utf8");
}

function send(message) {
  process.stdout.write(`${JSON.stringify(message)}\n`);
}

function pagesResult() {
  let pages;
  if (process.env.ARIS_FAKE_IDENTICAL_URL_DUP) {
    const duplicateUrl = process.env.ARIS_FAKE_IDENTICAL_URL_DUP === "1"
      ? "https://data.csmar.com/sdownload.html"
      : "https://example.test/duplicate";
    // Three same-URL siblings; none selected by default.
    pages = [
      {
        id: 11,
        url: duplicateUrl,
        title: "CSMAR",
        selected: selectedPage === 11,
      },
      {
        id: 12,
        url: duplicateUrl,
        title: "CSMAR",
        selected: selectedPage === 12,
      },
      {
        id: 13,
        url: duplicateUrl,
        title: "CSMAR",
        selected: selectedPage === 13,
      },
      {
        id: 3,
        url: "about:blank",
        title: "about:blank",
        selected: selectedPage === 3,
      },
    ];
  } else {
    pages = [
      {
        id: 1,
        url: mode === "ordinary"
          ? "https://example.test/paper?sessionId=RAW-QUERY-SECRET"
          : mode === "pdf"
            ? "https://assets.example.test/session/main.pdf?X-Amz-Signature=RAW-PDF-SECRET"
            : mode.startsWith("cnki-")
              ? `https://kns.cnki.net/kns8s/search/${mode.slice(5)}`
              : mode === "wiley-wrapper"
                ? "https://onlinelibrary.wiley.com/doi/pdf/10.1111/test"
            : `https://example.test/${mode}?token=RAW-CHALLENGE-QUERY`,
        title: "Research paper token=RAW-TITLE-SECRET",
        selected: selectedPage === 1,
      },
      {
        id: 2,
        url: "https://other.test/home?apiKey=OTHER-QUERY-SECRET",
        title: "Other",
        selected: selectedPage === 2,
      },
      {
        id: 3,
        url: "about:blank",
        title: "about:blank",
        selected: selectedPage === 3,
      },
    ];
  }
  return {
    content: [{
      type: "text",
      text: `## Pages\n${pages.map((page) => `${page.id}: ${page.title} (${page.url})${page.selected ? " [selected]" : ""}`).join("\n")}`,
    }],
    structuredContent: { pages },
  };
}

function snapshotResult() {
  let snapshot;
  if (process.env.ARIS_FAKE_LARGE_SNAPSHOT === "1" && mode === "ordinary") {
    snapshot = `## Latest page snapshot\nuid=11_0 RootWebArea "Large"\n${Array.from(
      { length: 500 },
      (_, index) => `  uid=11_${index + 1} StaticText "row-${index}-${"x".repeat(600)}"`,
    ).join("\n")}`;
  } else if (mode === "checkbox") {
    snapshot = `## Latest page snapshot
uid=7_0 RootWebArea "Security verification"
  uid=7_1 StaticText "Verify you are human with Cloudflare Turnstile"
  uid=7_2 checkbox "Verify you are human" focusable`;
  } else if (mode === "slider") {
    snapshot = `## Latest page snapshot
uid=8_0 RootWebArea "安全验证"
  uid=8_1 StaticText "请拖动滑块完成验证"
  uid=8_2 slider "滑块" focusable`;
  } else if (mode === "image") {
    snapshot = `## Latest page snapshot
uid=9_0 RootWebArea "CAPTCHA"
  uid=9_1 StaticText "Select all images with bicycles"
  uid=9_2 button "Submit"`;
  } else if (mode === "press-hold") {
    snapshot = `## Latest page snapshot
uid=10_0 RootWebArea "Security verification"
  uid=10_1 button "Press and hold" focusable`;
  } else if (mode.startsWith("cnki-")) {
    snapshot = `## Latest page snapshot
uid=12_0 RootWebArea "CNKI search"
  uid=12_1 StaticText "拖动下方拼图完成验证"
  uid=12_2 slider "滑块" focusable
  uid=12_3 textbox "中文文献、外文文献" focusable`;
  } else {
    snapshot = `## Latest page snapshot
uid=5_0 RootWebArea "Paper"
  uid=5_1 button "View PDF"
  uid=5_2 textbox "Email" focusable required value="INPUT-VALUE-SECRET"
  uid=5_3 StaticText "password=STATIC-PASSWORD-SECRET"
  uid=5_4 link "Download https://example.test/file.pdf?X-Amz-Signature=SNAPSHOT-QUERY-SECRET"
  uid=5_5 textbox "Password" focusable protected value="PASSWORD-FIELD-SECRET"
  uid=5_6 textbox "Start date" focusable value="2026-06-30"
  uid=5_7 StaticText "\uE618"
  uid=5_8 StaticText "未下载"
  uid=5_9 StaticText " 压缩完成"`;
  }
  return { content: [{ type: "text", text: snapshot }] };
}

function handle(message) {
  if (message.method === "notifications/initialized") return;
  if (message.id === undefined) return;
  if (message.method === "initialize") {
    send({
      jsonrpc: "2.0",
      id: message.id,
      result: {
        protocolVersion: message.params?.protocolVersion || "2025-06-18",
        capabilities: { tools: {} },
        serverInfo: { name: "chrome_devtools", version: "1.6.0-test" },
      },
    });
    return;
  }
  if (message.method === "tools/list") {
    send({ jsonrpc: "2.0", id: message.id, result: { tools } });
    return;
  }
  if (message.method !== "tools/call") {
    send({ jsonrpc: "2.0", id: message.id, error: { code: -32601, message: "unknown" } });
    return;
  }

  log(message.params);
  const name = message.params?.name;
  const args = message.params?.arguments ?? {};
  if (name === "list_pages") {
    send({ jsonrpc: "2.0", id: message.id, result: pagesResult() });
  } else if (name === "select_page") {
    selectedPage = args.pageId;
    send({ jsonrpc: "2.0", id: message.id, result: pagesResult() });
  } else if (name === "navigate_page") {
    activeValue = "";
    pinnedValue = "";
    if (String(args.url).includes("challenge-checkbox")) mode = "checkbox";
    else if (String(args.url).includes("challenge-slider")) mode = "slider";
    else if (String(args.url).includes("challenge-image")) mode = "image";
    else if (String(args.url).includes("challenge-press-hold")) mode = "press-hold";
    else if (String(args.url).includes("kns.cnki.net") && String(args.url).includes("hidden")) mode = "cnki-hidden";
    else if (String(args.url).includes("kns.cnki.net") && String(args.url).includes("nonblocking")) mode = "cnki-nonblocking";
    else if (String(args.url).includes("kns.cnki.net") && String(args.url).includes("visible")) mode = "cnki-visible";
    else if (String(args.url).includes("onlinelibrary.wiley.com/doi/pdf/")) mode = "wiley-wrapper";
    else if (String(args.url).includes(".pdf")) mode = "pdf";
    else mode = "ordinary";
    send({
      jsonrpc: "2.0",
      id: message.id,
      result: { content: [{ type: "text", text: `Successfully navigated to ${args.url}` }] },
    });
  } else if (name === "take_snapshot") {
    send({ jsonrpc: "2.0", id: message.id, result: snapshotResult() });
  } else if (name === "fill" && args.value === "TRIGGER-RAW-ERROR") {
    send({
      jsonrpc: "2.0",
      id: message.id,
      result: {
        isError: true,
        content: [{
          type: "text",
          text: "password=CHILD-ERROR-SECRET https://private.test/fail?token=CHILD-QUERY-SECRET",
        }],
      },
    });
  } else if (name === "evaluate_script"
    && String(args.function || "").includes("aris-icon-font-leaf-click-v1")) {
    send({
      jsonrpc: "2.0",
      id: message.id,
      result: {
        content: [{
          type: "text",
          text: "Script ran on page and returned:\n```json\n{\"clicked\":true}\n```",
        }],
      },
    });
  } else if (name === "evaluate_script"
    && String(args.function || "").includes("aris-active-editable-value-v1")) {
    pinnedValue = activeValue;
    send({
      jsonrpc: "2.0",
      id: message.id,
      result: {
        content: [{
          type: "text",
          text: `Script ran on page and returned:\n\`\`\`json\n${JSON.stringify({
            available: true,
            sensitive: false,
            value: activeValue,
          })}\n\`\`\``,
        }],
      },
    });
  } else if (name === "evaluate_script"
    && String(args.function || "").includes("aris-pinned-editable-value-v1")) {
    const value = pinnedValue;
    pinnedValue = "";
    send({
      jsonrpc: "2.0",
      id: message.id,
      result: {
        content: [{
          type: "text",
          text: `Script ran on page and returned:\n\`\`\`json\n${JSON.stringify({
            available: true,
            sensitive: false,
            value,
          })}\n\`\`\``,
        }],
      },
    });
  } else if (name === "evaluate_script" && ["pdf", "wiley-wrapper"].includes(mode)) {
    const downloads = join(homedir(), "Downloads");
    mkdirSync(downloads, { recursive: true });
    writeFileSync(
      join(downloads, mode === "pdf" ? "1-s2.0-TEST-main.pdf" : "wiley-wrapper.pdf"),
      Buffer.from("%PDF-1.7\nfixed semantic download\n%%EOF"),
    );
    send({
      jsonrpc: "2.0",
      id: message.id,
      result: {
        content: [{
          type: "text",
          text: "Script ran on page and returned:\n```json\n{\"triggered\":true}\n```",
        }],
      },
    });
  } else if (name === "evaluate_script" && mode.startsWith("cnki-")) {
    const geometry = mode === "cnki-visible"
      ? { applicable: true, present: true, rendered: true, blocking: true }
      : mode === "cnki-nonblocking"
        ? { applicable: true, present: true, rendered: true, blocking: false }
        : { applicable: true, present: true, rendered: false, blocking: false };
    send({
      jsonrpc: "2.0",
      id: message.id,
      result: {
        content: [{
          type: "text",
          text: `Script ran on page and returned:\n\`\`\`json\n${JSON.stringify(geometry)}\n\`\`\``,
        }],
      },
    });
  } else if (["click", "fill", "press_key", "wait_for"].includes(name)) {
    if (name === "fill") activeValue = String(args.value ?? "");
    if (name === "press_key" && args.key === "Enter") activeValue = "";
    send({
      jsonrpc: "2.0",
      id: message.id,
      result: { content: [{ type: "text", text: `RAW CHILD SUCCESS ${JSON.stringify(args)}` }] },
    });
  } else {
    send({
      jsonrpc: "2.0",
      id: message.id,
      result: { isError: true, content: [{ type: "text", text: "unsupported fake tool" }] },
    });
  }
}

process.stdin.setEncoding("utf8");
process.stdin.on("data", (chunk) => {
  buffer += chunk;
  const lines = buffer.split("\n");
  buffer = lines.pop() ?? "";
  for (const line of lines) {
    if (!line.trim()) continue;
    try {
      handle(JSON.parse(line));
    } catch {
      // Invalid client input is irrelevant to the facade integration fixture.
    }
  }
});

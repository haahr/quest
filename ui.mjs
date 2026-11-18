// The page's prompt (docs/wasm.md section 6.5): a line editor with history
// and completion, the transcript, and the buttons, over a PageSession
// (page.mjs) that the REPL's loop (repl.mjs) drives as the native REPL's
// does, a line at a time.
//
// The page's query may give:
//     path=URL   a URL prefix to import from, mounted at /remote/N (repeated)
//     load=PATH  a file for -i to run first, such as /remote/0/main.quest
//     args=A B   the program's arguments, system.args after <repl>
//
// Lines typed or pasted while an input runs wait their turn, as typing ahead
// does at a terminal. Ctrl-C, or the button, interrupts the input running,
// which ends the worker and replays the session; at the prompt it discards
// the phrase in progress.

import {load, PageSession} from "./page.mjs?v=4169e34e9755dfa3";
import {Transcript} from "./transcript.mjs?v=4169e34e9755dfa3";
import {requestLine, decodeRecord} from "./session.mjs?v=4169e34e9755dfa3";

const $ = id => document.getElementById(id);
const transcript = $("transcript"), console_ = $("console"), input = $("input"), promptLabel = $("prompt"),
  status = $("status");
const query = new URLSearchParams(location.search);
const options = {
  prefixes: query.getAll("path"),
  load: query.get("load") || undefined,
  args: (query.get("args") || "").split(/\s+/).filter(Boolean),
  // ?jit=0 interprets each input
  jit: query.get("jit") !== "0",
};

// What the native REPL would have written, for comparing with a transcript's
// golden by hand (window.quest.written)
const written = {stdout: "", stderr: ""};

// The transcript and the prompt's line after it scroll together, as at a
// terminal
const shown = new Transcript(transcript, console_);
const toEnd = () => { console_.scrollTop = console_.scrollHeight; };
function append(text, kind) { shown.append(text, kind); }

// Shows a display's bundle, {MIMETYPE: DATA}, in the transcript after the
// text before it: HTML, an image, or else its plain text
function show(bundle) {
  shown.flush();
  const div = document.createElement("div");
  div.className = "display";
  const image = Object.keys(bundle).find(t => t.startsWith("image/") && t !== "image/svg+xml");
  if (bundle["text/html"] !== undefined) {
    // In a frame of its own, sandboxed without scripts, as tall as its content
    const frame = document.createElement("iframe");
    frame.sandbox = "allow-same-origin";
    frame.srcdoc = bundle["text/html"];
    frame.onload = () => {
      const body = frame.contentDocument?.body;
      // The body's margin below it, and the frame's border
      if (body) frame.style.height = `${body.getBoundingClientRect().bottom + 24}px`;
    };
    div.append(frame);
  } else if (bundle["image/svg+xml"] !== undefined || image) {
    // An image runs no script, SVG's included
    const img = document.createElement("img");
    img.src = image ? `data:${image};base64,${bundle[image]}`
      : `data:image/svg+xml;charset=utf-8,${encodeURIComponent(bundle["image/svg+xml"])}`;
    div.append(img);
  } else {
    div.textContent = bundle["text/plain"] ?? JSON.stringify(bundle);
    div.style.whiteSpace = "pre-wrap";
  }
  transcript.append(div);
  toEnd();
}

let loaded = null, session = null, repl = null;
let prompt = ">>  ";
// The lines submitted that the REPL has not yet taken, and whether drain is
// taking them
const pending = [];
let draining = false;
// The lines submitted that are not blank, and the one the arrow keys are at
// (history.length past the last)
const history = [];
let historyAt = 0;

function setPrompt(text) {
  prompt = text;
  written.stdout += text;
  promptLabel.textContent = text;
}

// Starts a session whose files are files (a MemoryMount's entries), or the
// default, an empty /work, when undefined; then the prompt is ready
async function begin(files) {
  session = new PageSession(loaded, {
    ...options, files,
    stdout: t => { written.stdout += t; append(t, "out"); },
    stderr: t => { written.stderr += t; append(t, "err"); },
    display: show,
    exited: s => {
      append(`[the session ended with status ${s}]\n`, "note");
      input.disabled = true;
      $("interrupt").disabled = true;
      status.textContent = "Ended";
    },
  });
  repl = session.repl(t => { written.stdout += t; append(t, "out"); }, t => { written.stderr += t; append(t, "err"); },
                      setPrompt);
  const began = performance.now();
  await session.start();
  if (session.status !== null) return;
  const t = loaded.timings;
  status.textContent = `Ready: fetched ${t.fetched} ms, compiled ${t.compiled} ms, started ` +
    `${Math.round(performance.now() - began)} ms`;
  repl.begin();
  input.disabled = false;
  $("interrupt").disabled = false;
  $("restart").disabled = false;
  input.focus();
}

// Gives the lines pending to the REPL one at a time, each shown after the
// prompt it answers, until none is left or the session ends
async function drain() {
  draining = true;
  while (pending.length > 0 && session.status === null) {
    const line = pending.shift();
    append(prompt, "input");
    append(line + "\n", "input");
    const began = performance.now();
    await repl.line(line);
    // after the session ended, its status stays "Ended"
    if (session.status === null) status.textContent = `Last input: ${Math.round(performance.now() - began)} ms`;
  }
  draining = false;
}

// Queues lines, as typed or pasted, for drain
function submit(lines) {
  for (const line of lines) {
    if (line.trim() !== "") history.push(line);
    pending.push(line);
  }
  historyAt = history.length;
  if (!draining) drain();
}

// Ctrl-C: ends the input running, and drops the lines typed ahead; at the
// prompt, drops the phrase in progress instead
async function interrupt() {
  if (session.busy()) {
    pending.length = 0;
    status.textContent = "Interrupting: replaying the session…";
    await session.interrupt();
    status.textContent = `Interrupted; replayed in ${session.timings.replay} ms`;
  } else {
    append(prompt + input.value + "^C\n", "input");
    input.value = "";
    repl.discard();
    setPrompt(repl.prompt());
  }
}

// The byte offset of a string's end, as the protocol counts
const byteLength = s => new TextEncoder().encode(s).length;

// Tab: asks the session to complete the word at the cursor, given the
// phrase so far, and puts in what all its matches begin with, listing them
// if there are several
async function complete() {
  if (session.busy() || pending.length > 0) return;
  const before = repl.lines.map(l => l + "\n").join("");
  const code = before + input.value;
  const cursor = byteLength(before + input.value.slice(0, input.selectionStart));
  const records = (await session.request(requestLine({complete: code, cursor}))).map(decodeRecord);
  const r = records.find(x => "matches" in x);
  if (!r || r.matches.length === 0) return;
  // Offsets in bytes of code, made offsets in the input's characters
  const bytes = new TextEncoder().encode(code);
  const chars = n => new TextDecoder().decode(bytes.subarray(0, n)).length - before.length;
  const start = chars(r.start), end = chars(r.end);
  let common = r.matches[0];
  for (const m of r.matches) while (!m.startsWith(common)) common = common.slice(0, -1);
  if (r.matches.length > 1) append(r.matches.join("  ") + "\n", "note");
  input.value = input.value.slice(0, start) + common + input.value.slice(end);
  input.selectionStart = input.selectionEnd = start + common.length;
}

$("line").addEventListener("submit", e => {
  e.preventDefault();
  const line = input.value;
  input.value = "";
  submit([line]);
  // the line echoed, and the prompt's line after it, in view
  shown.settled().then(toEnd);
});

// A click in the transcript types at the prompt, unless it selects text
console_.addEventListener("click", () => {
  if (!input.disabled && getSelection().isCollapsed) input.focus({preventScroll: true});
});

input.addEventListener("paste", e => {
  const text = e.clipboardData.getData("text/plain");
  if (!text.includes("\n")) return;
  e.preventDefault();
  const at = input.selectionStart;
  const lines = (input.value.slice(0, at) + text + input.value.slice(input.selectionEnd)).replace(/\r\n?/g, "\n")
    .split("\n");
  input.value = lines.pop();
  submit(lines);
});

input.addEventListener("keydown", e => {
  if (e.ctrlKey && e.key === "c" && input.selectionStart === input.selectionEnd) {
    e.preventDefault();
    interrupt();
  } else if (e.key === "ArrowUp" && historyAt > 0) {
    e.preventDefault();
    input.value = history[--historyAt];
  } else if (e.key === "ArrowDown" && historyAt < history.length) {
    e.preventDefault();
    historyAt++;
    input.value = historyAt < history.length ? history[historyAt] : "";
  } else if (e.key === "Tab") {
    e.preventDefault();
    complete();
  }
});

// The circled i shows and hides the note about Quest and the browsers the
// page runs in
function showSupport(shown) {
  $("support").hidden = !shown;
  $("info").setAttribute("aria-expanded", String(shown));
  if (shown) console_.scrollTop = 0;
}
$("info").addEventListener("click", () => showSupport($("support").hidden));
$("interrupt").addEventListener("click", () => { interrupt(); input.focus(); });
$("restart").addEventListener("click", async () => {
  // the old session's request and queue answered, so that drain returns
  session.close();
  pending.length = 0;
  shown.clear();
  written.stdout = written.stderr = "";
  input.disabled = true;
  status.textContent = "Restarting…";
  await begin(session.files.entries);
});

window.quest = {written, pending, get session() { return session; }, get loaded() { return loaded; },
                get repl() { return repl; }, get draining() { return draining; }};

// A prefix or a file to load from another origin than the page's is the
// link's choice, not the user's: the page asks first, since a program from
// there can read what the page's origin serves (docs/wasm.md section 6.5).
// A prefix of the page's own origin needs no answer.
function crossOrigin() {
  const others = [...options.prefixes, ...(options.load && /^[a-z]+:/i.test(options.load) ? [options.load] : [])]
    .filter(p => new URL(p, location.href).origin !== location.origin);
  return others;
}

try {
  const others = crossOrigin();
  if (others.length > 0 && !confirm(`This page was asked to load Quest code from ${others.join(", ")}, ` +
                                    "which is another site. Load it?")) {
    options.prefixes = options.prefixes.filter(p => new URL(p, location.href).origin === location.origin);
    if (options.load && options.load.startsWith("/remote/")) options.load = undefined;
    append("Loading from another site was declined.\n", "note");
  }
  loaded = await load();
  status.textContent = "Starting the session…";
  await begin(undefined);
} catch (e) {
  status.textContent = "Failed to start";
  // the note says which browsers have what the page needs
  showSupport(true);
  append(String(e.stack || e) + "\n", "err");
  // most likely an engine without what the driver's modules use
  append("The page needs WebAssembly's garbage collection, tail calls, and exceptions (exnref), which recent " +
         "Chrome, Firefox, and Safari have.\n", "err");
}

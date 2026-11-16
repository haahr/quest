// The REPL's transcripts (tests/repl) run in the page (docs/wasm-plan.md steps
// 12 and 14), each in a session of its own, against their goldens, as
// tests/self-hosted/wasm_session.py runs them in node: the page that
// tools/wasm-page/build --tests writes, check.html, shows the outcome, and
// window.questCheck holds it. The inputs are compiled by the JIT, or with
// check.html?jit=0 interpreted.
//
// Each transcript's lines go to the REPL's loop as if typed, a line at a
// time; tests/repl is the session's URL prefix /remote/0, so that an @load
// directive's file is /remote/0/FILE. The paths the driver writes are made
// those the native transcripts show.

import {load, PageSession} from "./page.mjs";
import {Transcript} from "./transcript.mjs";

const jit = new URLSearchParams(location.search).get("jit") !== "0";
const mode = jit ? "jit" : "interpreted";

// The transcripts a page does not reproduce in each mode, each with its
// reason, as in tests/self-hosted/wasm_session.py; under the JIT, those
// marked @skip-phase: jit too
const pendingTranscripts = {
  interpreted: {
    stack_overflow: "the frames' count depends on the call limit (QUEST_CALL_LIMIT)",
  },
  jit: {
    earlier_function_error: "a traceback is the raise site only (decision 12)",
    module_errors: "a traceback is the raise site only (decision 12)",
  },
}[mode];

// A directive's text, as tests' comments give it: (* @NAME: TEXT *)
const directive = (text, name) => text.match(new RegExp(`\\(\\*\\s*@${name}:\\s*([^*]+?)\\s*\\*\\)`, "i"))?.[1];

// The paths of the page's session, as the native transcripts write theirs
function nativePaths(text) {
  return text.replaceAll("/remote/0/", "tests/repl/").replaceAll("/quest/lib", "lib")
    .replaceAll("/quest", "<root>").replaceAll("/work", "<scratch>");
}

async function transcript(loaded, name, source) {
  const loadFile = directive(source, "load");
  const args = (directive(source, "args") || "").split(/\s+/).filter(Boolean);
  const env = {};
  for (const item of (directive(source, "env") || "").split(/\s+/).filter(Boolean)) {
    const at = item.indexOf("=");
    env[item.slice(0, at)] = item.slice(at + 1);
  }
  let stdout = "", stderr = "", exit = 0;
  const session = new PageSession(loaded, {
    jit, args, env, load: loadFile && `/remote/0/${loadFile}`, prefixes: [new URL("tests/repl/", location.href).href],
    stdout: t => { stdout += t; }, stderr: t => { stderr += t; }, exited: s => { exit = s; },
  });
  const repl = session.repl(t => { stdout += t; }, t => { stderr += t; });
  const began = performance.now();
  await session.start();
  if (session.status === null) {
    repl.begin();
    const lines = source.split("\n");
    if (lines[lines.length - 1] === "") lines.pop();
    for (const line of lines) {
      if (session.status !== null) break;
      await repl.line(line);
    }
    if (session.status === null) repl.end();
  }
  session.worker?.terminate();
  return {text: nativePaths(`--- stdout\n${stdout}--- stderr\n${stderr}--- exit ${exit}\n`),
          time: Math.round(performance.now() - began)};
}

const out = document.getElementById("results");
const say = (text, kind = "") => {
  const line = document.createElement("div");
  line.className = kind;
  line.textContent = text;
  out.append(line);
};

const result = {passed: 0, failed: [], pending: Object.keys(pendingTranscripts), done: false};
window.questCheck = result;
try {
  const loaded = await load();
  say(`Loaded: ${JSON.stringify(loaded.timings)} ms; archives ${JSON.stringify(loaded.sizes)} bytes`);
  const names = await (await fetch("tests/transcripts.json")).json();
  say(`Mode: ${mode}`);
  for (const name of names) {
    if (name in pendingTranscripts) { say(`[PENDING] ${name}: ${pendingTranscripts[name]}`, "note"); continue; }
    const source = await (await fetch(`tests/repl/${name}.quest`)).text();
    if (jit && /\b(jit)\b/.test(directive(source, "skip-phase") || "")) {
      result.pending.push(name);
      say(`[PENDING] ${name}: marked @skip-phase: jit`, "note");
      continue;
    }
    const expected = await (await fetch(`tests/golden/repl/${name}.out`)).text();
    const {text, time} = await transcript(loaded, name, source);
    if (text === expected) {
      result.passed++;
      say(`[PASS] ${name} (${time} ms)`, "pass");
    } else {
      result.failed.push({name, expected, actual: text});
      say(`[FAIL] ${name}\n--- expected\n${expected}--- actual\n${text}`, "fail");
    }
  }
  // A program printing in a loop, a write at a time: 20,000 lines of 41
  // bytes into a transcript, in under a second (docs/wasm-plan.md step 30)
  const flood = document.createElement("div");
  flood.style.cssText = "height: 10em; overflow: auto; white-space: pre";
  document.body.append(flood);
  const t = new Transcript(flood);
  const began = performance.now();
  for (let i = 0; i < 20000; i++) t.append(`line ${String(i).padStart(5, "0")} of the flood of output.....\n`, "out");
  await t.settled();
  flood.scrollTop = flood.scrollHeight;
  const took = Math.round(performance.now() - began);
  flood.remove();
  if (took < 1000) {
    result.passed++;
    say(`[PASS] 20,000 lines into the transcript (${took} ms)`, "pass");
  } else {
    result.failed.push({name: "flood", expected: "under 1000 ms", actual: `${took} ms`});
    say(`[FAIL] 20,000 lines into the transcript took ${took} ms`, "fail");
  }
  say(`${result.passed} passed, ${result.failed.length} failed, ${result.pending.length} pending`);
} catch (e) {
  result.error = String(e.stack || e);
  say(result.error, "fail");
}
result.done = true;
// For a browser run by tools/wasm-page/build --check: the outcome posted to
// the server the page came from, which any browser can do, headless or not
// (a static server refuses it, which is no matter), and logged to the console
const outcome = `questCheck: ${mode}: ${result.passed} passed, ${result.failed.length} failed` +
  `${result.failed.map(f => ` ${f.name}`).join("")}${result.error ? `; ${result.error}` : ""}`;
console.log(outcome);
fetch("outcome", {method: "POST", body: outcome}).catch(() => {});

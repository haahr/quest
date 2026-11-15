// The REPL's transcripts (tests/repl) run in the page (docs/wasm-plan.md step
// 12), each in a session of its own, against their goldens, as
// tests/self-hosted/wasm_session.py runs them in node: the page that
// tools/wasm-page/build --tests writes, check.html, shows the outcome, and
// window.questCheck holds it.
//
// Each transcript's lines go to the REPL's loop as if typed, a line at a
// time; tests/repl is the session's URL prefix /remote/0, so that an @load
// directive's file is /remote/0/FILE. The paths the driver writes are made
// those the native transcripts show.

import {load, PageSession} from "./page.mjs";

// The transcripts a page does not reproduce, each with its reason, as in
// tests/self-hosted/wasm_session.py
const pendingTranscripts = {
  stack_overflow: "the frames' count depends on the call limit (QUEST_CALL_LIMIT)",
};

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
    args, env, load: loadFile && `/remote/0/${loadFile}`, prefixes: [new URL("tests/repl/", location.href).href],
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
  for (const name of names) {
    if (name in pendingTranscripts) { say(`[PENDING] ${name}: ${pendingTranscripts[name]}`, "note"); continue; }
    const source = await (await fetch(`tests/repl/${name}.quest`)).text();
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
  say(`${result.passed} passed, ${result.failed.length} failed, ${result.pending.length} pending`);
} catch (e) {
  result.error = String(e.stack || e);
  say(result.error, "fail");
}
result.done = true;
// For a browser run headless, which logs the console
console.log(`questCheck: ${result.passed} passed, ${result.failed.length} failed` +
            `${result.failed.map(f => ` ${f.name}`).join("")}${result.error ? `; ${result.error}` : ""}`);

// Checks a page that tools/wasm-page/build wrote (docs/wasm-plan.md step 12)
// in node, without a browser: its archives unpacked and the driver's modules
// compiled as the page does (page.mjs's load), and its worker's session
// (worker.mjs's serve) run in this thread, with a URL prefix read from a
// directory rather than a server. tests/self-hosted/wasm_session.py runs it.
//
//     node wasm_page.mjs PAGE TESTS_REPL
//
// PAGE is the page's directory; TESTS_REPL is tests/repl, the URL prefix
// /remote/0, whose files/functions.quest -i runs first. Writes each problem
// found, and exits 1 if there were any.

import fs from "node:fs";
import path from "node:path";
import {pathToFileURL} from "node:url";

const [page, tests] = process.argv.slice(2);
const load = name => import(pathToFileURL(path.join(page, name)).href);
const {unpack} = await load("archive.mjs");
const {serve} = await load("worker.mjs");
const {MemoryMount} = await load("host.mjs");
const {requestLine, decodeRecord} = await load("session.mjs");

const problems = [];
const expect = (what, got, want) => {
  if (JSON.stringify(got) !== JSON.stringify(want)) {
    problems.push(`${what}: got ${JSON.stringify(got)}, wanted ${JSON.stringify(want)}`);
  }
};

const driver = await unpack(new Uint8Array(fs.readFileSync(path.join(page, "driver.qar.gz"))));
const lib = await unpack(new Uint8Array(fs.readFileSync(path.join(page, "lib.qar.gz"))));
const compile = name => new WebAssembly.Module(driver.get(name));
const modules = {
  runtime: compile("runtime.wasm"), program: compile("program.wasm"),
  units: [...driver.keys()].filter(n => n.startsWith("units/")).map(n => ({name: n.slice(6), module: compile(n)})),
};
expect("the library's archive has list's interface", lib.has("list.int.quest"), true);

// A prefix read from the directory tests: what a server would give
const prefix = "https://example.test/repl/";
const fetched = [];
const get = url => {
  fetched.push(url);
  const file = path.join(tests, url.slice(prefix.length));
  return fs.existsSync(file) && fs.statSync(file).isFile() ? new Uint8Array(fs.readFileSync(file)) : null;
};

// A session as the page starts one: the worker's messages, and the page's
// copy of its files, which each change it posts is made to
function start(files, committed) {
  const messages = [];
  const copy = new MemoryMount(files);
  const post = m => {
    messages.push(m);
    if (m.change) { const [op, ...args] = m.change; copy[op](...args); }
  };
  const handle = serve({
    modules, lib, files, committed, prefixes: [prefix],
    args: ["--no-jit", "-i", "/remote/0/files/functions.quest", "one"],
    env: {QUEST_HOME: "/quest", QUEST_KERNEL: "1", PWD: "/work"},
  }, post, get);
  const text = kind => messages.filter(m => m[kind]).map(m => new TextDecoder().decode(m[kind])).join("");
  const execute = code => {
    const at = messages.length;
    handle({line: requestLine({execute: code})});
    const reply = messages.slice(at).find(m => m.records);
    return {records: reply.records.map(decodeRecord), committed: reply.committed, messages: messages.slice(at)};
  };
  return {messages, copy, text, execute};
}

const first = start(new Map([["work", null]]), []);
expect("the session starts", first.messages.some(m => m.started), true);
expect("-i runs the file from the URL prefix", first.text("stdout"), "\"loaded\" : String\n");
expect("the prefix's file is fetched", fetched.includes(prefix + "files/functions.quest"), true);
expect("a function the file defined", first.execute("add1(100)").records.map(r => r.result), ["101 : Int", undefined]);
first.execute("let kept = 7");
first.execute('import writer: Writer\nlet w = writer.file("note.txt")\nwriter.putString(w "hi")\nwriter.close(w)');
expect("a file written is in the page's copy", new TextDecoder().decode(first.copy.read("work/note.txt")), "hi");
const shown = first.execute('import io/display: io/Display\ndisplay.html("<p>hi</p>")').messages
  .filter(m => m.record).map(m => new TextDecoder().decode(m.record)).join("");
expect("a display is a record", shown.includes('{"display":{"text/html":"<p>hi</p>"'), true);
expect("a failure does not commit", first.execute("1 / 0").records.at(-1), {done: "error"});
const {committed} = first.execute("kept + 1");

// A new worker, as after an interrupt: the page's files and the inputs that
// committed, replayed without their output
const second = start(first.copy.entries, committed);
expect("a replay writes nothing", second.text("stdout"), "\"loaded\" : String\n");
expect("the bindings after a replay", second.execute("kept + add1(1)").records.map(r => r.result), ["9 : Int", undefined]);
expect("the files after a replay", second.execute('import reader: Reader\nreader.getString(reader.file("note.txt") 2)')
  .records.map(r => r.result), ['"hi" : String', undefined]);

for (const p of problems) console.log(p);
console.log(`wasm page: ${problems.length} problems`);
process.exit(problems.length > 0 ? 1 : 0);

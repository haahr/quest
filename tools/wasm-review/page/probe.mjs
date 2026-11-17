// Drives the page's own UI (ui.mjs) for the review's probes
const $ = id => document.getElementById(id);
const input = $("input"), form = $("line"), transcript = $("transcript"), status = $("status");
const log = (...a) => console.log("PROBE: " + a.map(x => typeof x === "string" ? x.replaceAll("\n", "\\n") : JSON.stringify(x)).join(" "));
const sleep = ms => new Promise(r => setTimeout(r, ms));
const until = async (f, ms = 30000) => { const t = performance.now(); while (!f()) { if (performance.now() - t > ms) return false; await sleep(10); } return true; };
const idle = () => window.quest.session && !window.quest.draining && !window.quest.session.busy() && window.quest.pending.length === 0;
const type = line => { input.value = line; form.dispatchEvent(new Event("submit", {cancelable: true, bubbles: true})); };
const run = async (line, ms) => { const at = transcript.textContent.length; type(line); await sleep(0); const ok = await until(idle, ms); return (ok ? "" : "[TIMEOUT] ") + transcript.textContent.slice(at); };
const which = new URLSearchParams(location.search).get("probe");
window.onerror = (m) => log("window.onerror", String(m));
window.addEventListener("unhandledrejection", e => log("unhandledrejection", String(e.reason)));
try {
  if (!(await until(() => !input.disabled, 60000))) throw new Error("the page did not start: " + status.textContent + transcript.textContent);
  log("started", status.textContent, "isolated:", String(self.crossOriginIsolated));
  if (which === "basic") {
    log(await run("1 + 1"));
    log(await run("import writer: Writer"));
    log(await run('writer.putString(writer.output "<img src=x onerror=\\"window.pwned=1\\"><b>bold</b>\\n")'));
    log(await run('"<script>window.pwned=2</' + 'script>"'));
    log(await run('exception Bad : String end'));
    log(await run('raise Bad with "<img src=x onerror=window.pwned=3>" end'));
    log(await run('let <b>x = 1'));
    log(await run('import io/display: io/Display'));
    log(await run('display.html("<p id=p>hi</p><script>parent.pwned=4</' + 'script><img src=x onerror=\\"parent.pwned=5\\"><a href=\\"javascript:parent.pwned=6\\" id=a>l</a>")'));
    await sleep(500);
    log("img elements in transcript:", transcript.querySelectorAll("img").length, "b:", transcript.querySelectorAll("b").length,
        "iframes:", transcript.querySelectorAll("iframe").length, "pwned:", String(window.pwned));
    const frame = transcript.querySelector("iframe");
    log("frame sandbox:", frame?.getAttribute("sandbox"), "frame doc reachable from page:", String(!!frame?.contentDocument));
    log(await run('display.svg("<svg xmlns=\\"http://www.w3.org/2000/svg\\" onload=\\"parent.pwned=7\\"><script>parent.pwned=8</' + 'script></svg>")'));
    await sleep(300);
    log("pwned after svg:", String(window.pwned));
    log(await run("let h = array of 0 end"));
    // type ahead while busy
    type("let rec spin(n: Int acc: Int): Int = if n is 0 then acc else spin(n - 1 acc + 1) end");
    type("spin(200000000 0)"); type("h[0] := 5"); type("h");
    await until(idle);
    log("type-ahead:", transcript.textContent.slice(-160));
  } else if (which === "restart") {
    log(await run("let a = 1"));
    type("while true do ok end");
    await sleep(500);
    log("busy:", String(window.quest.session.busy()), "restart disabled:", String($("restart").disabled));
    $("restart").click();
    const ok = await until(() => status.textContent.startsWith("Ready"), 20000);
    log("restarted:", String(ok), status.textContent, "draining:", String(window.quest.draining), "input disabled:", String(input.disabled));
    type("1 + 1");
    await sleep(3000);
    log("after typing 1 + 1 post-restart, transcript:", JSON.stringify(transcript.textContent), "pending:", window.quest.pending.length, "draining:", String(window.quest.draining));
  } else if (which === "interrupt") {
    log("at start:", JSON.stringify(transcript.textContent));
    log(await run("let a = 41"));
    log(await run("import writer: Writer"));
    log(await run('writer.putString(writer.output "printed by a committed input\\n")'));
    type("while true do ok end"); type("a + 1000");
    await sleep(500);
    $("interrupt").click();
    await sleep(50);
    await until(idle);
    log("after interrupt:", JSON.stringify(transcript.textContent.slice(-300)), status.textContent);
    log(await run("a + 1"));
    // interrupt at the prompt, mid-phrase
    type("let b =");
    await sleep(50);
    await until(idle);
    $("interrupt").click();
    await sleep(100);
    log(await run("a + 2"));
    // exit
    log(await run("import system: System"));
    log(await run("system.sysexit(3)"));
    log("after exit:", status.textContent, "input disabled:", String(input.disabled), "restart disabled:", String($("restart").disabled));
  } else if (which === "output") {
    log(await run("import writer: Writer"));
    log(await run('let rec lp(n: Int): Int = if n is 0 then 0 else begin writer.putString(writer.output "0123456789012345678901234567890123456789\\n") lp(n - 1) end end'));
    for (const n of [2000, 20000, 100000]) {
      const t = performance.now();
      const at = transcript.textContent.length;
      type(`lp(${n})`);
      let worst = 0, last = performance.now();
      const ok = await until(() => { const now = performance.now(); worst = Math.max(worst, now - last); last = now; return idle(); }, 120000);
      log(`lp(${n}):`, ok ? "done" : "TIMEOUT", Math.round(performance.now() - t), "ms; transcript grew", transcript.textContent.length - at, "chars; longest main-thread stall", Math.round(worst), "ms; spans", transcript.children.length);
      if (!ok) break;
    }
    log(await run('import stringOp = string : StringOp'));
    const t = performance.now();
    const out = await run('writer.putString(writer.output stringOp.new(20000000 \'y\'))', 60000);
    log("one write of 20 MB:", out.length, Math.round(performance.now() - t), "ms");
  } else if (which === "oom") {
    log(await run("let keep = 1"));
    log(await run("let rec grow(a: Array(Array(Int)) i: Int): Int = if i is extent a then i else begin a[i] := array of(1000000 i) grow(a i + 1) end end"));
    const t = performance.now();
    const out = await run("grow(array of(100000 array of 0 end) 0)", 120000);
    log("grow:", out.slice(0, 300), Math.round(performance.now() - t), "ms", status.textContent);
    log("then:", (await run("keep", 10000)).slice(0, 200), status.textContent);
  }
} catch (e) {
  log("probe failed:", String(e.stack || e));
}
console.log("PROBE-DONE");

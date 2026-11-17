// More probes of the page's own UI
const $ = id => document.getElementById(id);
const input = $("input"), form = $("line"), transcript = $("transcript"), status = $("status");
const log = (...a) => console.log("PROBE: " + a.map(x => typeof x === "string" ? x.replaceAll("\n", "\\n") : JSON.stringify(x)).join(" "));
const sleep = ms => new Promise(r => setTimeout(r, ms));
const until = async (f, ms = 30000) => { const t = performance.now(); while (!f()) { if (performance.now() - t > ms) return false; await sleep(10); } return true; };
const idle = () => window.quest.session && !window.quest.draining && !window.quest.session.busy() && window.quest.pending.length === 0;
const type = line => { input.value = line; form.dispatchEvent(new Event("submit", {cancelable: true, bubbles: true})); };
const run = async (line, ms) => { const at = transcript.textContent.length; type(line); await sleep(20); const ok = await until(idle, ms); return (ok ? "" : "[TIMEOUT] ") + transcript.textContent.slice(at); };
const which = new URLSearchParams(location.search).get("probe");
window.onerror = (m) => log("window.onerror", String(m));
window.addEventListener("unhandledrejection", e => log("unhandledrejection", String(e.reason)));
try {
  if (!(await until(() => !input.disabled, 60000))) throw new Error("the page did not start: " + status.textContent + transcript.textContent);
  log("started", status.textContent);
  if (which === "output") {
    await run("import writer: Writer");
    await run('let rec lp(n: Int): Int = if n is 0 then 0 else begin writer.putString(writer.output "0123456789012345678901234567890123456789\\n") lp(n - 1) end end');
    const timed = async (label, line, ms = 60000) => {
      const t = performance.now();
      const at = transcript.textContent.length;
      type(line);
      await sleep(20);
      const ok = await until(idle, ms);
      log(label, line.slice(0, 40), ok ? "done" : "TIMEOUT", Math.round(performance.now() - t), "ms; transcript grew", transcript.textContent.length - at);
    };
    await timed("visible:", "lp(500)");
    await timed("visible:", "lp(1000)");
    await timed("visible:", "lp(2000)");
    await timed("visible:", "lp(4000)");
    transcript.style.display = "none";
    await timed("transcript hidden (no layout):", "lp(4000)");
    await timed("transcript hidden (no layout):", "lp(20000)");
    transcript.style.display = "";
    await run("import stringOp = string : StringOp");
    await timed("one write:", 'writer.putString(writer.output stringOp.new(2000000 \'y\'))');
    // interrupt during a flood: how long until the button's click takes effect
    type("lp(4000)");
    await sleep(300);
    const t = performance.now();
    $("interrupt").click();
    await sleep(20);
    await until(idle, 60000);
    log("interrupt during a flood took", Math.round(performance.now() - t), "ms", status.textContent);
  } else if (which === "oom") {
    log(await run("let keep = 1"));
    log(await run("let rec grow(a: Array(Array(Int)) i: Int): Int = if i is extent a then i else begin a[i] := array of(1000000 i) grow(a i + 1) end end"));
    const t = performance.now();
    const out = await run("grow(array of(100000 array of 0 end) 0)", 60000);
    log("grow:", out.slice(0, 300), Math.round(performance.now() - t), "ms", status.textContent, "busy:", String(window.quest.session.busy()), "session status:", String(window.quest.session.status));
    $("interrupt").click();
    await sleep(3000);
    log("after an interrupt:", transcript.textContent.slice(-200), status.textContent);
    log("then:", (await run("keep", 10000)).slice(0, 200), status.textContent);
  } else if (which === "restartidle") {
    log(await run("let a = 1"));
    log(await run('import writer: Writer'));
    log(await run('let w = writer.file("kept.txt")'));
    log(await run('writer.putString(w "x")'));
    log(await run('writer.close(w)'));
    $("restart").click();
    await sleep(100);
    await until(() => status.textContent.startsWith("Ready"), 20000);
    log(await run("a"));
    log(await run('import system: System'));
    log(await run('system.listDirectory(".")'));
  }
} catch (e) {
  log("probe failed:", String(e.stack || e));
}
console.log("PROBE-DONE");

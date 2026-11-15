// The worker of the page (docs/wasm-plan.md step 12): a Session
// (session.mjs) of the driver's modules, which the page compiled and passes
// in, over a Host (host.mjs) whose files are mounts of these kinds:
//
//     /            the session's own files, in memory, the current directory
//                  /work; each change is posted to the page, which keeps a
//                  copy that a worker started after an interrupt begins with
//     /quest/lib   the library's archive, read only (QUEST_HOME is /quest)
//     /remote/N    the page's Nth URL prefix, fetched by synchronous request
//
// The page posts one message to start the session, with what it needs, then
// one for each request, {line}; the worker posts the driver's writes as they
// are made ({stdout}, {stderr}, {record}: bytes), then {started} or
// {exited: STATUS}, and for each request {records, committed}.

import {Errno, E, MemoryMount, UrlMount} from "./host.mjs";
import {Session, Exited} from "./session.mjs";

export const home = "/quest";
export const cwd = "/work";

// A synchronous GET of url: its bytes, or null if the server has none
function getSync(url) {
  const request = new XMLHttpRequest();
  request.open("GET", url, false);
  request.responseType = "arraybuffer";
  try {
    request.send();
  } catch (e) {
    throw new Errno(E.IO, `${url}: ${e}`);
  }
  if (request.status === 200) return new Uint8Array(request.response);
  if (request.status === 404) return null;
  throw new Errno(E.IO, `${url}: ${request.status} ${request.statusText}`);
}

// The mounts of a session: start, as the page posts it
export function mounts(start, post, get = getSync) {
  const table = {
    "/": new MemoryMount(start.files, false, change => post({change})),
    [home + "/lib"]: new MemoryMount(start.lib, true),
  };
  start.prefixes.forEach((prefix, i) => { table[`/remote/${i}`] = new UrlMount(prefix, get); });
  return table;
}

// Serves a session in a worker: start is the page's first message, post
// sends a message to the page. Gives the function that takes each later
// message.
export function serve(start, post, get = getSync) {
  const session = new Session({
    modules: start.modules, args: start.args, env: start.env, cwd, mounts: mounts(start, post, get),
    stdout: b => post({stdout: b}), stderr: b => post({stderr: b}), record: b => post({record: b}),
  });
  try {
    session.start();
    // A worker started after an interrupt: the inputs that committed, again
    session.committed = start.committed;
    if (start.committed.length > 0) session.replay();
    post({started: true});
  } catch (e) {
    if (e instanceof Exited) post({exited: e.status}); else post({failed: String(e.stack || e)});
    return () => {};
  }
  return ({line}) => {
    try {
      const records = session.request(line);
      post({records, committed: session.committed});
    } catch (e) {
      if (e instanceof Exited) post({exited: e.status}); else post({failed: String(e.stack || e)});
    }
  };
}

// In a worker, the first message starts the session
if (typeof WorkerGlobalScope !== "undefined" && self instanceof WorkerGlobalScope) {
  let handle = null;
  self.onmessage = ({data}) => {
    if (handle === null) handle = serve(data, message => self.postMessage(message));
    else handle(data);
  };
}

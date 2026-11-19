// The host of a session (docs/wasm.md sections 4.4 and 6.1): the part of WASI's
// first preview that the runtime module imports, implemented in JavaScript
// over a table of mounts, for node and for a page alike.
//
// Every path is absolute inside the host. A mount serves the files under its
// path; the longest mount whose path is a prefix of a file's serves it. A
// mount is an object with these methods, each given the path relative to the
// mount's ("" for the mount itself), each throwing an Errno to fail:
//
//     stat(rel)          {type: "file" | "directory", size, mtimeNs} or null
//     read(rel)          a file's bytes, a Uint8Array
//     write(rel, bytes)  replaces a file's bytes, making it if need be
//     list(rel)          a directory's names
//     mkdir(rel), unlink(rel), rmdir(rel), rename(rel, toRel)
//
// A file opened to read is read whole when it is opened; one opened to create
// or truncate is written whole, all it holds so far, after each write to it
// (Host's open). Two paths are streams, not files: /dev/fd/3, whose reads
// give the requests the host queued (requests), and /dev/fd/4, whose writes
// are the session's records (onRecord), as the kernel's descriptors are
// natively (docs/jupyter-kernel.md section 2).

// Whether e is an engine's stack overflow, which no standard names: V8's and
// JavaScriptCore's RangeError, SpiderMonkey's InternalError, "too much
// recursion" (docs/wasm.md section 6.3). A host function that makes the
// errors it catches error numbers lets this one through, so that the input
// fails as natively rather than see a file missing
export function isStackOverflow(e) {
  return e instanceof RangeError || (e?.name === "InternalError" && /recursion/i.test(String(e.message)));
}

// A failure a mount or a call gives: code is one of E's WASI error numbers,
// which makeImports's wrapper returns as the call's result
export class Errno extends Error {
  constructor(code, what) { super(what || `errno ${code}`); this.code = code; }
}

// WASI's numbers for the errors the host gives
export const E = {BADF: 8, EXIST: 20, INVAL: 28, IO: 29, ISDIR: 31, NOENT: 44, NOSYS: 52, NOTDIR: 54,
                  NOTEMPTY: 55, NOTSUP: 58, PERM: 63, ROFS: 69, ACCES: 2, XDEV: 75};

// Ends a run: proc_exit throws it, and whoever called into the instance
// catches it
export class Exit {
  constructor(code) { this.code = code; }
}

const encoder = new TextEncoder();

// path's parts, with . and .. resolved, joined to an absolute path
export function normalize(path) {
  const parts = [];
  for (const part of path.split("/")) {
    if (part === "" || part === ".") continue;
    if (part === "..") parts.pop(); else parts.push(part);
  }
  return "/" + parts.join("/");
}

// A mount over a directory tree held in memory: a Map from each path relative
// to the mount ("" the mount's own) to a Uint8Array for a file or null for a
// directory. readOnly refuses every change. files gives the entries to start
// with, the same map (a Map or an object), or a file's text as a string; a
// change made is also given to changed, as the method's name and arguments,
// so that a copy elsewhere (a page's, of a worker's files) can make it too.
export class MemoryMount {
  constructor(files = {}, readOnly = false, changed = null) {
    this.entries = new Map([["", null]]);
    this.readOnly = readOnly;
    this.changed = changed;
    this.time = BigInt(Date.now()) * 1000000n;
    for (const [rel, bytes] of files instanceof Map ? files : Object.entries(files)) {
      const parts = rel.split("/");
      for (let i = 1; i < parts.length; i++) this.entries.set(parts.slice(0, i).join("/"), null);
      if (rel !== "") this.entries.set(rel, typeof bytes === "string" ? encoder.encode(bytes) : bytes);
    }
  }
  // The directory that holds rel, "" for one at the top
  parent(rel) { return rel.includes("/") ? rel.slice(0, rel.lastIndexOf("/")) : ""; }
  // Refuses a change to a read-only mount (ROFS, a read-only file system)
  changing() { if (this.readOnly) throw new Errno(E.ROFS); }
  // Tells changed of a change made
  made(...change) { if (this.changed) this.changed(change); }
  stat(rel) {
    if (!this.entries.has(rel)) return null;
    const e = this.entries.get(rel);
    return e === null ? {type: "directory", size: 0, mtimeNs: this.time}
                      : {type: "file", size: e.length, mtimeNs: this.time};
  }
  read(rel) {
    const e = this.entries.get(rel);
    if (e === undefined) throw new Errno(E.NOENT);
    if (e === null) throw new Errno(E.ISDIR);
    return e;
  }
  write(rel, bytes) {
    this.changing();
    if (this.entries.get(this.parent(rel)) !== null) throw new Errno(E.NOENT);
    if (this.entries.get(rel) === null) throw new Errno(E.ISDIR);
    this.entries.set(rel, bytes);
    this.made("write", rel, bytes);
  }
  list(rel) {
    if (this.entries.get(rel) !== null) throw new Errno(this.entries.has(rel) ? E.NOTDIR : E.NOENT);
    const prefix = rel === "" ? "" : rel + "/";
    const names = [];
    for (const key of this.entries.keys()) {
      if (key !== "" && key.startsWith(prefix) && !key.slice(prefix.length).includes("/") && key !== rel) {
        names.push(key.slice(prefix.length));
      }
    }
    return names;
  }
  mkdir(rel) {
    this.changing();
    if (this.entries.has(rel)) throw new Errno(E.EXIST);
    if (this.entries.get(this.parent(rel)) !== null) throw new Errno(E.NOENT);
    this.entries.set(rel, null);
    this.made("mkdir", rel);
  }
  unlink(rel) {
    this.changing();
    const e = this.entries.get(rel);
    if (e === undefined) throw new Errno(E.NOENT);
    if (e === null) throw new Errno(E.ISDIR);
    this.entries.delete(rel);
    this.made("unlink", rel);
  }
  rmdir(rel) {
    this.changing();
    if (this.entries.get(rel) !== null) throw new Errno(this.entries.has(rel) ? E.NOTDIR : E.NOENT);
    if (this.list(rel).length > 0) throw new Errno(E.NOTEMPTY);
    this.entries.delete(rel);
    this.made("rmdir", rel);
  }
  // As a file system renames: not into itself; a directory onto an empty
  // directory only, a file onto a file only; what was at the target replaced
  rename(rel, toRel) {
    this.changing();
    if (!this.entries.has(rel)) throw new Errno(E.NOENT);
    if (this.entries.get(this.parent(toRel)) !== null) throw new Errno(E.NOENT);
    if (rel === toRel) return;
    const prefix = rel + "/";
    const isDirectory = this.entries.get(rel) === null;
    if (isDirectory && toRel.startsWith(prefix)) throw new Errno(E.INVAL);
    if (this.entries.has(toRel)) {
      const target = this.entries.get(toRel);
      if (isDirectory && target !== null) throw new Errno(E.NOTDIR);
      if (!isDirectory && target === null) throw new Errno(E.ISDIR);
      if (target === null) {
        for (const key of this.entries.keys()) if (key.startsWith(toRel + "/")) throw new Errno(E.NOTEMPTY);
      }
      this.entries.delete(toRel);
    }
    for (const [key, value] of [...this.entries]) {
      if (key === rel || key.startsWith(prefix)) {
        this.entries.delete(key);
        this.entries.set(toRel + key.slice(rel.length), value);
      }
    }
    this.made("rename", rel, toRel);
  }
  // No symlinks, so none to read (INVAL, as for a file that is not one), and
  // one time for every entry
  symlink() { this.changing(); throw new Errno(E.NOTSUP); }
  readlink(rel) { throw new Errno(this.entries.has(rel) ? E.INVAL : E.NOENT); }
  utimes() { this.changing(); throw new Errno(E.NOTSUP); }
}

// A mount over a URL prefix, read only (docs/wasm.md section 5.2): a
// file's path relative to the mount, appended to the prefix, is the URL it is
// fetched from, at most once. get(url) fetches synchronously, giving the
// bytes, or null when the server has no such file; any other failure throws
// an Errno. A page's worker gets with a synchronous XMLHttpRequest, which
// fetch cannot be. The mount itself is a directory, and so is nothing else:
// a server lists no directory, and so lists nothing here.
export class UrlMount {
  constructor(prefix, get) {
    this.prefix = prefix.endsWith("/") ? prefix : prefix + "/";
    this.get = get;
    this.fetched = new Map();
  }
  fetch(rel) {
    if (!this.fetched.has(rel)) this.fetched.set(rel, this.get(this.prefix + rel));
    return this.fetched.get(rel);
  }
  stat(rel) {
    if (rel === "") return {type: "directory", size: 0, mtimeNs: 0n};
    const bytes = this.fetch(rel);
    return bytes === null ? null : {type: "file", size: bytes.length, mtimeNs: 0n};
  }
  read(rel) {
    const bytes = rel === "" ? undefined : this.fetch(rel);
    if (bytes === undefined) throw new Errno(E.ISDIR);
    if (bytes === null) throw new Errno(E.NOENT);
    return bytes;
  }
  list(rel) {
    if (rel !== "") throw new Errno(this.fetch(rel) === null ? E.NOENT : E.NOTDIR);
    return [];
  }
  write() { throw new Errno(E.ROFS); }
  mkdir() { throw new Errno(E.ROFS); }
  unlink() { throw new Errno(E.ROFS); }
  rmdir() { throw new Errno(E.ROFS); }
  rename() { throw new Errno(E.ROFS); }
  symlink() { throw new Errno(E.ROFS); }
  readlink(rel) { throw new Errno(this.fetch(rel) === null ? E.NOENT : E.INVAL); }
  utimes() { throw new Errno(E.ROFS); }
}

// A mount over node's files under root, given node's fs module (so that this
// file imports nothing of node's, and loads in a page)
export class NodeMount {
  constructor(fs, root) { this.fs = fs; this.root = root === "/" ? "" : root; }
  // rel's path in node's file system
  real(rel) { return rel === "" ? (this.root || "/") : this.root + "/" + rel; }
  // f's result, a failure of node's (an Error whose code is ENOENT and the
  // like) made the Errno WASI names, but a stack overflow let through
  call(f) {
    try {
      return f();
    } catch (e) {
      if (isStackOverflow(e)) throw e;
      const codes = {ENOENT: E.NOENT, ENOTDIR: E.NOTDIR, EEXIST: E.EXIST, EISDIR: E.ISDIR, ENOTEMPTY: E.NOTEMPTY,
                     EACCES: E.ACCES, EPERM: E.PERM, EINVAL: E.INVAL, EXDEV: E.XDEV, ENOTSUP: E.NOTSUP};
      if (e.code in codes) throw new Errno(codes[e.code]);
      throw new Errno(E.IO, String(e));
    }
  }
  // null, not an error, for a file missing, as a mount's stat gives; a
  // symlink's own, not what it names, when follow is false
  stat(rel, follow = true) {
    let s;
    try {
      s = (follow ? this.fs.statSync : this.fs.lstatSync)(this.real(rel), {bigint: true});
    } catch (e) {
      if (isStackOverflow(e)) throw e;
      if (e.code === "ENOENT" || e.code === "ENOTDIR") return null;
      throw new Errno(E.IO, String(e));
    }
    return {type: s.isDirectory() ? "directory" : s.isSymbolicLink() ? "symlink" : "file", size: Number(s.size),
            mtimeNs: s.mtimeNs,
            atimeNs: s.atimeNs, ctimeNs: s.ctimeNs};
  }
  read(rel) { return this.call(() => new Uint8Array(this.fs.readFileSync(this.real(rel)))); }
  write(rel, bytes) { this.call(() => this.fs.writeFileSync(this.real(rel), bytes)); }
  list(rel) { return this.call(() => this.fs.readdirSync(this.real(rel))); }
  mkdir(rel) { this.call(() => this.fs.mkdirSync(this.real(rel))); }
  unlink(rel) { this.call(() => this.fs.unlinkSync(this.real(rel))); }
  rmdir(rel) { this.call(() => this.fs.rmdirSync(this.real(rel))); }
  rename(rel, toRel) { this.call(() => this.fs.renameSync(this.real(rel), this.real(toRel))); }
  symlink(target, rel) { this.call(() => this.fs.symlinkSync(target, this.real(rel))); }
  readlink(rel) { return this.call(() => this.fs.readlinkSync(this.real(rel), {encoding: "buffer"})); }
  // node takes seconds, as Numbers, which hold whole microseconds since the
  // epoch exactly
  utimes(rel, atimeNs, mtimeNs) {
    this.call(() => this.fs.utimesSync(this.real(rel), Number(atimeNs) / 1e9, Number(mtimeNs) / 1e9));
  }
}

// The host. options:
//   args, env           the program's arguments and environment (an object)
//   cwd                 the directory . names, absolute
//   mounts              {path: mount}
//   onStdout, onStderr  called with each write's bytes to descriptors 1 and 2
//   onRecord            called with each write's bytes to /dev/fd/4
export class Host {
  constructor(options) {
    this.args = options.args || [];
    this.env = options.env || {};
    this.cwd = normalize(options.cwd || "/");
    this.mounts = Object.entries(options.mounts || {})
      .map(([path, mount]) => ({path: normalize(path), mount}))
      .sort((a, b) => b.path.length - a.path.length);
    this.onStdout = options.onStdout || (() => {});
    this.onStderr = options.onStderr || (() => {});
    this.onRecord = options.onRecord || (() => {});
    this.requests = [];
    this.memory = null;
    // The descriptors: 0 to 2 the standard streams, 3 and 4 the directories
    // opened for / and ., then what is opened
    this.fds = new Map([
      [0, {kind: "input"}], [1, {kind: "output", write: b => this.onStdout(b)}],
      [2, {kind: "output", write: b => this.onStderr(b)}],
      [3, {kind: "preopen", path: "/", name: "/"}], [4, {kind: "preopen", path: this.cwd, name: "."}],
    ]);
    this.nextFd = 5;
    this.wasiImport = this.makeImports();
  }

  // The runtime module's instance, whose memory the calls read and write
  attach(instance) { this.memory = instance.exports.memory; }

  // A request the next read of /dev/fd/3 gives, with its newline
  queue(line) { this.requests.push(encoder.encode(line + "\n")); }

  // The mount that serves path, and path relative to it: the first of the
  // mounts, which are sorted longest path first, whose path is path or a
  // prefix of it that ends at a slash. Throws NOENT when none is (no mount at
  // /).
  mountOf(path) {
    for (const {path: at, mount} of this.mounts) {
      if (path === at) return {mount, rel: ""};
      if (at === "/" ) return {mount, rel: path.slice(1)};
      if (path.startsWith(at + "/")) return {mount, rel: path.slice(at.length + 1)};
    }
    throw new Errno(E.NOENT);
  }
  // What is at path, as a mount's stat gives it, or null for nothing; a
  // symlink's own when follow is false
  stat(path, follow = true) {
    // A mount's own path is a directory, though no mount above holds it
    for (const {path: at} of this.mounts) {
      if (at !== path && at.startsWith(path === "/" ? "/" : path + "/")) {
        const {mount, rel} = this.mountOf(path);
        const s = mount.stat(rel);
        return s || {type: "directory", size: 0, mtimeNs: 0n};
      }
    }
    const {mount, rel} = this.mountOf(path);
    return mount.stat(rel, follow);
  }
  // The names in the directory path: its mount's, if it has the directory,
  // and the first name of each mount below it, so that /quest lists lib where
  // only /quest/lib is mounted
  list(path) {
    const {mount, rel} = this.mountOf(path);
    let names;
    try {
      names = mount.list(rel);
    } catch (e) {
      names = [];
      if (!(e instanceof Errno) || e.code !== E.NOENT) throw e;
    }
    // Mounts directly under path
    const prefix = path === "/" ? "/" : path + "/";
    for (const {path: at} of this.mounts) {
      if (at.startsWith(prefix) && at !== path) {
        const name = at.slice(prefix.length).split("/")[0];
        if (!names.includes(name)) names.push(name);
      }
    }
    return names;
  }

  // ------------------------------------------------------------------------
  // Memory

  view() { return new DataView(this.memory.buffer); }
  bytes(at, n) { return new Uint8Array(this.memory.buffer, at, n); }
  string(at, n) { return new TextDecoder().decode(this.bytes(at, n)); }
  // The path at (at, n), relative to the directory fd
  path(fd, at, n) {
    const d = this.fds.get(fd);
    if (!d || d.kind !== "preopen" && d.kind !== "directory") throw new Errno(E.BADF);
    const rel = this.string(at, n);
    return normalize(rel.startsWith("/") ? rel : d.path + "/" + rel);
  }
  // The NUL-terminated strings items, at pointers and their bytes at buffer
  putStrings(items, pointers, buffer) {
    const v = this.view();
    let at = buffer;
    items.forEach((s, i) => {
      const b = encoder.encode(s);
      v.setUint32(pointers + 4 * i, at, true);
      this.bytes(at, b.length).set(b);
      v.setUint8(at + b.length, 0);
      at += b.length + 1;
    });
  }
  // The count of items, at countAt, and the bytes putStrings takes for them,
  // at sizeAt, as args_sizes_get and environ_sizes_get give them, so that
  // the runtime can allocate the space before it asks for the strings
  sizes(items, countAt, sizeAt) {
    const v = this.view();
    v.setUint32(countAt, items.length, true);
    v.setUint32(sizeAt, items.reduce((n, s) => n + encoder.encode(s).length + 1, 0), true);
  }
  environment() { return Object.entries(this.env).map(([k, v]) => `${k}=${v}`); }

  // ------------------------------------------------------------------------
  // The calls, each giving its errno

  // The functions the runtime imports as wasi_snapshot_preview1. Each gives
  // 0, or the code of an Errno it throws; anything else thrown (an Exit, a
  // stack overflow) goes on to whoever called into the instance. Each
  // argument named at or into is an address in the runtime's memory.
  makeImports() {
    const call = f => (...args) => {
      try {
        return f(...args) || 0;
      } catch (e) {
        if (e instanceof Errno) return e.code;
        throw e;
      }
    };
    return {
      args_sizes_get: call((c, s) => this.sizes(this.args, c, s)),
      args_get: call((p, b) => this.putStrings(this.args, p, b)),
      environ_sizes_get: call((c, s) => this.sizes(this.environment(), c, s)),
      environ_get: call((p, b) => this.putStrings(this.environment(), p, b)),
      // A preopen's prestat: tag 0, a directory, then its name's length
      fd_prestat_get: call((fd, at) => {
        const d = this.fds.get(fd);
        if (!d || d.kind !== "preopen") throw new Errno(E.BADF);
        const v = this.view();
        v.setUint8(at, 0);
        v.setUint32(at + 4, encoder.encode(d.name).length, true);
      }),
      fd_prestat_dir_name: call((fd, at, n) => {
        const d = this.fds.get(fd);
        if (!d || d.kind !== "preopen") throw new Errno(E.BADF);
        this.bytes(at, n).set(encoder.encode(d.name).slice(0, n));
      }),
      path_open: call((dirfd, dirflags, at, n, oflags, rights, inheriting, fdflags, into) => {
        const path = this.path(dirfd, at, n);
        const d = this.open(path, oflags);
        const fd = this.nextFd++;
        this.fds.set(fd, d);
        this.view().setUint32(into, fd, true);
      }),
      // Into count buffers, each an address and a length at iovs; a short
      // read ends it, as the data available has run out
      fd_read: call((fd, iovs, count, into) => {
        const d = this.fds.get(fd);
        if (!d) throw new Errno(E.BADF);
        const v = this.view();
        let total = 0;
        for (let i = 0; i < count; i++) {
          const at = v.getUint32(iovs + 8 * i, true);
          const n = v.getUint32(iovs + 8 * i + 4, true);
          const got = this.read(d, n);
          this.bytes(at, got.length).set(got);
          total += got.length;
          if (got.length < n) break;
        }
        this.view().setUint32(into, total, true);
      }),
      fd_write: call((fd, iovs, count, into) => {
        const d = this.fds.get(fd);
        if (!d || !d.write) throw new Errno(E.BADF);
        const v = this.view();
        let total = 0;
        for (let i = 0; i < count; i++) {
          const at = v.getUint32(iovs + 8 * i, true);
          const n = v.getUint32(iovs + 8 * i + 4, true);
          if (n > 0) d.write(this.bytes(at, n).slice());
          total += n;
        }
        this.view().setUint32(into, total, true);
      }),
      fd_close: call(fd => {
        const d = this.fds.get(fd);
        if (!d) throw new Errno(E.BADF);
        this.fds.delete(fd);
        if (d.close) d.close();
      }),
      // The entries from index cookie on, as many as n bytes hold, each a
      // dirent of 24 bytes and then its name. A dirent holds the next entry's
      // cookie at 0, an inode number at 8 (the index here too), the name's
      // length at 16, and its type at 20 (0, unknown). The last entry is cut
      // off where the buffer ends, as WASI has it: a caller that gets a full
      // buffer reads again for the rest.
      fd_readdir: call((fd, at, n, cookie, into) => {
        const d = this.fds.get(fd);
        if (!d || d.kind !== "directory") throw new Errno(E.BADF);
        const v = this.view();
        let used = 0;
        for (let i = Number(cookie); i < d.names.length && used < n; i++) {
          const name = encoder.encode(d.names[i]);
          const entry = new Uint8Array(24 + name.length);
          const ev = new DataView(entry.buffer);
          ev.setBigUint64(0, BigInt(i + 1), true);
          ev.setBigUint64(8, BigInt(i + 1), true);
          ev.setUint32(16, name.length, true);
          ev.setUint8(20, 0);
          entry.set(name, 24);
          const take = Math.min(entry.length, n - used);
          this.bytes(at + used, take).set(entry.subarray(0, take));
          used += take;
        }
        v.setUint32(into, used, true);
      }),
      // os/time's clocks (docs/time-plan.md section 4): 0 the wall clock, 1
      // the monotonic one, 2 the process's CPU time, which only node has
      // (ENOSYS elsewhere, for which the runtime reads the monotonic clock);
      // each as nanoseconds, a u64 at into
      clock_time_get: call((id, precision, into) => {
        let ns;
        if (id === 0) {
          ns = BigInt(Math.round(performance.timeOrigin * 1000)) * 1000n + BigInt(Math.round(performance.now() * 1e6));
        } else if (id === 1) {
          ns = BigInt(Math.round(performance.now() * 1e6));
        } else if ((id === 2 || id === 3) && typeof process !== "undefined" && process.cpuUsage) {
          const u = process.cpuUsage();
          ns = BigInt(u.user + u.system) * 1000n;
        } else {
          throw new Errno(E.NOSYS);
        }
        this.view().setBigUint64(into, ns, true);
      }),
      // os/time's sleep: one subscription, to a clock, relative, its timeout
      // at 24; it waits, and writes the one event (its userdata, errno 0, type
      // 0) and the count. Atomics.wait needs a SharedArrayBuffer, which a page
      // has only when cross-origin isolated, so without one it waits on the
      // clock, in the page's worker
      poll_oneoff: call((subscriptions, events, count, into) => {
        const v = this.view();
        if (count !== 1 || v.getUint8(subscriptions + 8) !== 0) throw new Errno(E.INVAL);
        const ms = Number(v.getBigUint64(subscriptions + 24, true)) / 1e6;
        if (ms > 0) {
          if (typeof SharedArrayBuffer !== "undefined") {
            Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, ms);
          } else {
            const until = performance.now() + ms;
            while (performance.now() < until) { /* waits */ }
          }
        }
        v.setBigUint64(events, v.getBigUint64(subscriptions, true), true);
        v.setUint16(events + 8, 0, true);
        v.setUint8(events + 10, 0);
        v.setUint32(into, 1, true);
      }),
      // A filestat of 64 bytes: the device and inode at 0 and 8, left 0; the
      // file's type at 16 (3 a directory, 4 a regular file); the link count
      // at 24; the size at 32; and the times of access, modification, and
      // status change at 40, 48, and 56, in nanoseconds
      path_filestat_get: call((fd, flags, at, n, into) => {
        const s = this.stat(this.path(fd, at, n), (flags & 1) !== 0);
        if (!s) throw new Errno(E.NOENT);
        const v = this.view();
        for (let i = 0; i < 64; i += 8) v.setBigUint64(into + i, 0n, true);
        v.setUint8(into + 16, s.type === "directory" ? 3 : s.type === "symlink" ? 7 : 4);
        v.setBigUint64(into + 24, 1n, true);
        v.setBigUint64(into + 32, BigInt(s.size), true);
        v.setBigUint64(into + 40, BigInt(s.atimeNs ?? s.mtimeNs), true);
        v.setBigUint64(into + 48, BigInt(s.mtimeNs), true);
        v.setBigUint64(into + 56, BigInt(s.ctimeNs ?? s.mtimeNs), true);
      }),
      path_create_directory: call((fd, at, n) => {
        const path = this.path(fd, at, n);
        const {mount, rel} = this.mountOf(path);
        if (rel === "") throw new Errno(E.EXIST);
        mount.mkdir(rel);
      }),
      path_unlink_file: call((fd, at, n) => {
        const {mount, rel} = this.mountOf(this.path(fd, at, n));
        mount.unlink(rel);
      }),
      path_remove_directory: call((fd, at, n) => {
        const {mount, rel} = this.mountOf(this.path(fd, at, n));
        mount.rmdir(rel);
      }),
      path_rename: call((fd, at, n, fd2, at2, n2) => {
        const from = this.mountOf(this.path(fd, at, n));
        const to = this.mountOf(this.path(fd2, at2, n2));
        if (from.mount !== to.mount) throw new Errno(E.ACCES);
        // a mount's own path, or one holding a mount, is not the mount's to
        // move (/quest, which holds /quest/lib)
        const source = this.path(fd, at, n);
        if (this.mounts.some(m => m.path !== "/" && (m.path === source || m.path.startsWith(source + "/")))) {
          throw new Errno(E.ACCES);
        }
        from.mount.rename(from.rel, to.rel);
      }),
      // A symlink at (at2, n2) in fd2 whose target is the text at (at, n)
      path_symlink: call((at, n, fd, at2, n2) => {
        const {mount, rel} = this.mountOf(this.path(fd, at2, n2));
        mount.symlink(this.string(at, n), rel);
      }),
      // The symlink's target, up to size bytes of it at buffer, and how many
      // at into
      path_readlink: call((fd, at, n, buffer, size, into) => {
        const {mount, rel} = this.mountOf(this.path(fd, at, n));
        const target = mount.readlink(rel);
        const k = Math.min(target.length, size);
        this.bytes(buffer, k).set(target.subarray(0, k));
        this.view().setUint32(into, k, true);
      }),
      // Both times set (fst_flags 1 and 4), nanoseconds since the epoch
      path_filestat_set_times: call((fd, flags, at, n, atim, mtim, which) => {
        if ((which & 5) !== 5) throw new Errno(E.NOTSUP);
        const {mount, rel} = this.mountOf(this.path(fd, at, n));
        if (!this.stat(this.path(fd, at, n), (flags & 1) !== 0)) throw new Errno(E.NOENT);
        mount.utimes(rel, BigInt(atim), BigInt(mtim));
      }),
      proc_exit: code => { throw new Exit(code); },
    };
  }

  // The descriptor path_open makes for path, given WASI's oflags (1 create,
  // 2 directory, 4 exclusive, 8 truncate; exclusive refuses anything at
  // path, a symlink included): a
  // stream, a directory with its names listed now, a file opened to read,
  // read whole now, or a file opened to create or truncate, written whole
  // after each write (below). A file opened with neither has no write, and a
  // write to it fails (BADF).
  open(path, oflags) {
    const create = (oflags & 1) !== 0, directory = (oflags & 2) !== 0, truncate = (oflags & 8) !== 0;
    if (path === "/dev/fd/3") return {kind: "requests"};
    if (path === "/dev/fd/4") {
      // the driver's kernel opens it when it holds its session for the
      // host's requests, before its _start ends (session.mjs's start)
      this.serving = true;
      return {kind: "output", write: b => this.onRecord(b)};
    }
    if ((oflags & 4) !== 0 && create && this.stat(path, false)) throw new Errno(E.EXIST);
    const s = this.stat(path);
    if (directory) {
      if (!s) throw new Errno(E.NOENT);
      if (s.type !== "directory") throw new Errno(E.NOTDIR);
      return {kind: "directory", path, names: [".", "..", ...this.list(path)]};
    }
    if (s && s.type === "directory") {
      if (create || truncate) throw new Errno(E.ISDIR);
      return {kind: "directory", path, names: [".", "..", ...this.list(path)]};
    }
    if (!s && !create) throw new Errno(E.NOENT);
    const {mount, rel} = this.mountOf(path);
    if (create || truncate) {
      // Made now, so that it exists while open, and written through with
      // each write, so that what a flush gives the file is in it, as
      // natively. The core's writers give WASI a file's bytes 64 KB at a
      // time, so each write copies what the file has so far, once for each
      // 64 KB
      const file = {kind: "file", bytes: new Uint8Array(0), at: 0, data: new Uint8Array(0)};
      if (!s || truncate) mount.write(rel, new Uint8Array(0));
      file.write = b => {
        const all = new Uint8Array(file.bytes.length + b.length);
        all.set(file.bytes);
        all.set(b, file.bytes.length);
        file.bytes = all;
        mount.write(rel, all);
      };
      file.close = () => {};
      return file;
    }
    return {kind: "file", data: mount.read(rel), at: 0};
  }

  // Up to n bytes from the descriptor d: fewer at a file's end, and none from
  // the requests when none is queued, or from standard input, which a session
  // has none of
  read(d, n) {
    if (d.kind === "file") {
      const got = d.data.subarray(d.at, d.at + n);
      d.at += got.length;
      return got;
    }
    if (d.kind === "requests") {
      if (this.requests.length === 0) return new Uint8Array(0);
      const first = this.requests[0];
      const got = first.subarray(0, n);
      if (got.length === first.length) this.requests.shift(); else this.requests[0] = first.subarray(n);
      return got;
    }
    if (d.kind === "input") return new Uint8Array(0);
    throw new Errno(E.BADF);
  }
}

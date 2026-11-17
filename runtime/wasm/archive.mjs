// The archives a page fetches (docs/wasm.md sections 5.1 and 5.2): the
// driver's modules, and the library's sources, each one file fetched once
// rather than a request for each of its members. tools/wasm-page/build.py
// writes them.
//
// An archive is "QAR1", the length of its index as four bytes, little-endian,
// the index, a JSON list of [NAME, SIZE] in order, and then the members' bytes
// one after another. The file is compressed with gzip, which a page undoes
// itself (DecompressionStream), so that any static server can serve it; a
// server that sends it with a Content-Encoding has undone it already.

const magic = "QAR1";

// bytes (a Uint8Array) without its gzip, if it has one
export async function gunzip(bytes) {
  if (bytes.length < 2 || bytes[0] !== 0x1f || bytes[1] !== 0x8b) return bytes;
  const stream = new Blob([bytes]).stream().pipeThrough(new DecompressionStream("gzip"));
  return new Uint8Array(await new Response(stream).arrayBuffer());
}

// The members of an archive's bytes, compressed or not: a Map from each name
// to its bytes, in the archive's order
export async function unpack(bytes) {
  const data = await gunzip(bytes);
  if (new TextDecoder().decode(data.subarray(0, 4)) !== magic) throw new Error("not an archive of a Quest page");
  const length = new DataView(data.buffer, data.byteOffset + 4, 4).getUint32(0, true);
  const index = JSON.parse(new TextDecoder().decode(data.subarray(8, 8 + length)));
  const members = new Map();
  let at = 8 + length;
  for (const [name, size] of index) {
    members.set(name, data.subarray(at, at + size));
    at += size;
  }
  return members;
}

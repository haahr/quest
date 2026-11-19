# Digests: `util/digest`

The second of [future-libraries.md](future-libraries.md)'s "written already" libraries: SHA-256 and CRC-32 for
programs, in Quest alone, so alike on every target, the browser included. The compiler's own SHA-256,
`questlang/common/sha256`, becomes a wrapper over it, and every digest the compiler writes stays as it is.

## 1. What the compiler has and needs

`questlang/common/sha256` exports one function, `hexDigest(text: String): String`, SHA-256 in lowercase hexadecimal.
It matches what the bootstrap gets from `hashlib.sha256(text.encode("utf-8")).hexdigest()`: the bootstrap holds
source text as characters one per byte, so a character above 127 is hashed as two bytes, its UTF-8 encoding. Five
places call it:

| Caller | Hashes | Uses |
|---|---|---|
| `questlang/repr/digests` `printedUncached` | a type's printed text, or a byte 1 and its parts' digests | all 64 digits |
| `questlang/repr/digests` `textDigest` | a text | the first 16 |
| `questlang/repr/layout` `shapeTag` | a layout tag longer than 64 characters | the first 16 |
| `questlang/modules/artifacts/fingerprint` | an interface's ABI version, name, and sorted lines | all 64 |
| `questlang/build/compilerrunner` | the runtime's source names and texts, joined | the first 24 |

All of them hash a String they have just built by concatenation; the last joins whole files only to hash them.

## 2. The interface

```quest
interface Digest
import
    word: Word
export
    (* =========================================================================
     * Digests (Digest)
     *
     * Cryptographic and checksum digests of byte strings. A String's
     * characters are its bytes, 0 to 255, each hashed as one byte: no text
     * encoding is applied. A digest state takes bytes in pieces and gives
     * the same result as one call on their concatenation:
     *
     *     let d = digest.sha256()
     *     digest.add(d "abc")
     *     digest.add(d "def")
     *     digest.hex(digest.finish(d)) = digest.sha256Hex("abcdef")
     *
     * finish leaves the state empty, as new, so it can be reused.
     * ====================================================================== *)

    (* A digest state: an algorithm and the bytes added since it was made or
     * last finished *)
    T::TYPE

    (* A new SHA-256 state (FIPS 180-4) *)
    sha256(): T

    (* The number of bytes finish returns: 32 for SHA-256 *)
    size(d: T): Int

    (* Add the bytes of text *)
    add(d: T text: String): Ok

    (* Add the substring of text of the given size at start; raises
     * string.error, as string.getSub does, if it is not within text *)
    addSub(d: T text: String start: Int size: Int): Ok

    (* Add one byte, the character c *)
    addChar(d: T c: Char): Ok

    (* The digest of the bytes added, as a String of size(d) bytes, after
     * which d is empty *)
    finish(d: T): String

    (* bytes in lowercase hexadecimal, two digits a byte, most significant
     * first *)
    hex(bytes: String): String

    (* The SHA-256 of text, as 32 bytes and as 64 hexadecimal digits *)
    sha256Of(text: String): String
    sha256Hex(text: String): String

    (* CRC-32 of text (IEEE 802.3, as zlib, gzip, zip, and PNG compute it),
     * from 0 to 2^32 - 1 *)
    crc32(text: String): Int

    (* The CRC-32 continued with text from crc, the CRC-32 of the bytes so
     * far: crc32Add(0 text) = crc32(text), and
     * crc32Add(crc32(a) b) = crc32(a <> b) *)
    crc32Add(crc: Int text: String): Int
end
```

## 3. Decisions

1. **Bytes, not text.** The library hashes a String's bytes as they are, as `hashlib` hashes `bytes` and every other
   language's library does, so that a digest of a file read by `os/path.readText` is the file's digest (as
   `sha256sum` prints it). The compiler's UTF-8 step is the bootstrap's way of reading source, not a property of
   SHA-256, so it stays in the compiler (§4).
2. **One state type, chosen at creation.** `digest.T`, made by `sha256()`, rather than a type and a set of functions
   for each algorithm. SHA-1 or SHA-512 later adds a constructor and nothing else; code that hashes a stream takes a
   `digest.T` and works with any of them. The state keeps one 64-byte block and the running hash, never the whole
   message, so streaming large inputs costs no memory.
3. **finish empties the state,** as `stringBuilder.toString` empties a builder, rather than leaving it unusable or
   finished twice.
4. **Raw digests and hex apart.** `finish` and `sha256Of` give bytes, for programs that compare digests, store them,
   or encode them otherwise (base64, as tools/jupyter/install.py does); `hex` turns any bytes into digits, and
   `sha256Hex` is the one-call form the compiler and most programs want.
5. **CRC-32 as an Int, continued by value.** A checksum is a number and is usually written as one; Int holds 32 bits
   exactly. `crc32Add` threads the value, as zlib's `crc32(crc, buf)` does, so it needs no state type.
6. **No FNV.** `util/hash.string` is already 64-bit FNV-1a, for hash tables. A stable, documented FNV would duplicate
   it; if programs need one that is promised not to change, that is a sentence in `util/hash`'s documentation, not a
   second library.
7. **No HMAC, SHA-1, or MD5 now.** HMAC is a dozen lines over `digest.T` when something needs it; SHA-1 and MD5 only
   for compatibility with formats that use them (git objects, old checksums), and nothing in the tree does.

## 4. The compiler

`questlang/common/sha256` keeps its interface, `hexDigest(text: String): String`, and its comment, so no caller
changes. Its module becomes the UTF-8 step and a call:

```quest
let hexDigest(text: String): String =
    begin
        (* The bootstrap hashes text.encode("utf-8") of characters that are
         * bytes, so a byte above 127 is two: 192 + c / 64, 128 + c % 64 *)
        let d = digest.sha256()
        for i = 0 upto {stringOp.length(text) - 1} do
            let c = ascii.val(stringOp.getChar(text i))
            if c < 128 then
                digest.addChar(d ascii.char(c))
            else
                digest.addChar(d ascii.char(192 + {c / 64}))
                digest.addChar(d ascii.char(128 + {c % 64}))
            end
        end
        digest.hex(digest.finish(d))
    end
```

The loop could add runs of ASCII with `addSub` instead of byte by byte, if profiles show it. For ASCII text,
`hexDigest(t)` equals `digest.sha256Hex(t)`.

Later, and only if it pays, `compilerrunner` can add each file to one state instead of joining them first; its key
would change, which only rebuilds the runtime cache once.

The bootstrap keeps `hashlib`, under the two-compilers policy: the shared goldens that hold digests check that both
compilers still agree.

## 5. Tests

- `tests/source/stdlib/digest_operations.quest`, with a behavior golden: SHA-256 of "", "abc", the 56-byte "abcdbcdecdef…"
  message, and a million "a"s (FIPS 180-4's and NIST's vectors); messages of 55, 56, 63, 64, and 65 bytes, where the
  padding crosses a block; bytes above 127 and NUL; the same messages added in pieces of every size from 1 to 70;
  `finish` twice in a row (the second the empty message's); CRC-32 of "" (0) and "123456789" (3421780262), and
  `crc32Add` across a split.
- The compiler's own goldens, unchanged, which show `hexDigest` still gives what it did.
- The same test through the wasm backend, since the library is Quest alone and must agree there.

## 6. Steps

1. `lib/util/digest.int.quest` and `.mod.quest`, the test, and libraries.md §1.12. SHA-256 on 32-bit values kept in
   Ints, as `questlang/common/sha256` does now, buffered by block.
2. `questlang/common/sha256` over `util/digest`, as §4 shows; the compiler's goldens and tools/check must pass
   unchanged. Measure a driver build before and after: SHA-256 is on the type-digest path.
3. Remove Digests from future-libraries.md.

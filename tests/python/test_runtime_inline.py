"""The runtime's inline helpers have external definitions too (runtime/quest_inline.c, docs/arm64.md section 7.5):
every Q_INLINE function of quest_runtime.h is a global symbol of the runtime, and code compiled without the header,
as native code is, can call it."""

from __future__ import annotations

from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "bootstrap" / "python"))

from quest.codegen.c.compiler_runner import (
    RUNTIME_SOURCES,
    base_c_flags,
    detect_gc_flags,
    find_c_compiler,
    get_runtime_dir,
    link_objects,
    runtime_objects,
)

# A Q_INLINE definition's name: the identifier before its parameter list
_DEFINITION = re.compile(r"^Q_INLINE\s+[^(]*?\b(\w+)\s*\(", re.MULTILINE)

# A program that calls helpers through prototypes of its own, without the
# runtime's header, and prints what they return
_CALLER = r"""
#include <stdint.h>
#include <stdio.h>
#include <stdbool.h>
#include <stddef.h>

int64_t quest_int_div_at(int64_t a, int64_t b, const char *loc);
int64_t quest_int_mod_at(int64_t a, int64_t b, const char *loc);
int64_t quest_int_abs(int64_t n);
double quest_real_add_at(double a, double b, const char *loc);
uint64_t quest_word_rotate(uint64_t w, int64_t count);
bool quest_is_proxy(const void *p);
void *quest_alloc(size_t size);

int main(void) {
    int64_t min = INT64_MIN;
    printf("%lld\n", (long long)quest_int_div_at(min, -1, NULL));
    printf("%lld\n", (long long)quest_int_mod_at(min, -1, NULL));
    printf("%lld\n", (long long)quest_int_div_at(-7, 2, NULL));
    printf("%lld\n", (long long)quest_int_abs(-5));
    printf("%lld\n", (long long)(quest_int_abs(min) == min));
    printf("%.1f\n", quest_real_add_at(1.5, 2.0, NULL));
    printf("%llu\n", (unsigned long long)quest_word_rotate(1, 63));
    printf("%d %d\n", (int)quest_is_proxy((const void *)1), (int)quest_is_proxy((const void *)8));
    int64_t *p = (int64_t *)quest_alloc(16);
    printf("%d\n", p != NULL && p[0] == 0 && p[1] == 0);
    return 0;
}
"""

_EXPECTED = "\n".join([
    str(-(2**63)), "0", "-3", "5", "1", "3.5", str(2**63), "1 0", "1",
]) + "\n"


def inline_helpers() -> set[str]:
    """The names of the header's Q_INLINE functions."""
    return set(_DEFINITION.findall((get_runtime_dir() / "quest_runtime.h").read_text()))


def defined_symbols(obj: str) -> set[str]:
    """The global symbols obj defines, without Darwin's leading underscore."""
    out = subprocess.run(["nm", "-g", "-U", obj], check=True, stdout=subprocess.PIPE, text=True).stdout
    names = set()
    for line in out.splitlines():
        parts = line.split()
        if len(parts) == 3 and parts[1] in ("T", "t"):
            names.add(parts[2][1:] if sys.platform == "darwin" else parts[2])
    return names


class TestRuntimeInline(unittest.TestCase):
    def setUp(self) -> None:
        self.compiler = find_c_compiler()

    def test_the_runtime_is_built_with_quest_inline(self) -> None:
        self.assertIn("quest_inline.c", RUNTIME_SOURCES)

    def test_the_header_has_inline_helpers(self) -> None:
        helpers = inline_helpers()
        # A sample of each family: integers, reals, words, proxies, allocation
        for name in ("quest_int_div_at", "quest_real_add_at", "quest_word_rotate", "quest_unproxy", "quest_alloc"):
            self.assertIn(name, helpers)
        self.assertGreater(len(helpers), 80)

    def test_every_inline_helper_has_an_external_definition(self) -> None:
        # With and without the collector, whose allocation helpers differ
        modes = [True] if detect_gc_flags() == ["-DQUEST_NOGC"] else [True, False]
        for nogc in modes:
            with self.subTest(nogc=nogc):
                objects = runtime_objects(self.compiler, nogc=nogc)
                inline_obj = next(o for o in objects if Path(o).name == "quest_inline.o")
                missing = inline_helpers() - defined_symbols(inline_obj)
                self.assertEqual(missing, set(), f"helpers without external definitions: {sorted(missing)}")

    def test_code_without_the_header_calls_them(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "caller.c"
            src.write_text(_CALLER)
            obj = Path(tmp) / "caller.o"
            subprocess.run([self.compiler, *base_c_flags(self.compiler), "-c", str(src), "-o", str(obj)], check=True)
            binary = link_objects([obj], Path(tmp) / "caller", nogc=True, compiler_path=self.compiler)
            result = subprocess.run([str(binary)], stdout=subprocess.PIPE, text=True, timeout=30)
            self.assertEqual(result.returncode, 0)
            self.assertEqual(result.stdout, _EXPECTED)


if __name__ == "__main__":
    unittest.main()

"""Unit tests of the C runtime's read-only strings: a string whose header has
Q_HEADER_READONLY set (by quest_string_freeze, as the self-hosted interpreter
marks its literals) raises string.error on string.setChar and string.setSub,
and is otherwise a string; the bit survives collections, and other strings
stay writable (docs/extensions.md, String Literals)."""

import os
import sys
import tempfile
import unittest
from pathlib import Path

# Ensure bootstrap/python is in sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "bootstrap", "python"))

from quest.build.compiler_runner import compile_c_source, run_binary

C_PROGRAM = r"""
#include "quest_runtime.h"
#include <stdio.h>
#include <string.h>

static QString *frozen, *plain, *source;
static const QRootEntry roots[] = { { (void *)&frozen, 1 }, { (void *)&plain, 1 }, { (void *)&source, 1 },
                                    { NULL, 0 } };

static void check(const char *what, bool ok) { printf("%s: %s\n", what, ok ? "ok" : "wrong"); }

static bool equal(const QString *s, const char *bytes) {
    return s->length == (int64_t)strlen(bytes) && memcmp(s->data, bytes, (size_t)s->length) == 0;
}

/* Whether f raises exc */
static bool raises(const QException *exc, void (*f)(void)) {
    QExceptionHandler handler;
    handler.prev = quest_current_exception_handler;
    handler.resume = NULL;
    handler.catches = NULL;
    handler.n_catches = Q_CATCH_ALL;
    quest_current_exception_handler = &handler;
    if (Q_SETJMP(handler.env_jmp) == 0) {
        f();
        quest_current_exception_handler = handler.prev;
        return false;
    }
    quest_current_exception_handler = handler.prev;
    return quest_current_exception.exc == exc;
}

static void set_char_frozen(void) { quest_string_set_char(frozen, 0, 'X'); }
static void set_sub_frozen(void) { quest_string_set_sub(frozen, 1, source, 0, 2); }
static void set_char_plain(void) { quest_string_set_char(plain, 0, 'X'); }
static void set_sub_plain(void) { quest_string_set_sub(plain, 1, source, 0, 2); }

int main(int argc, char **argv) {
    quest_gc_init();
    quest_register_roots(roots);
    quest_builtins_init(argc, argv);
    frozen = quest_string_new("abcd", 4);
    plain = quest_string_new("abcd", 4);
    source = quest_string_new("XY", 2);
    quest_string_freeze(frozen);

    check("frozen is read-only", quest_is_readonly(frozen));
    check("plain is not", !quest_is_readonly(plain));
    check("setChar on frozen raises", raises(&quest_exc_string_error, set_char_frozen));
    check("setSub on frozen raises", raises(&quest_exc_string_error, set_sub_frozen));
    check("frozen unchanged", equal(frozen, "abcd"));
    check("frozen reads", quest_string_get_char(frozen, 2) == 'c' && equal(quest_string_get_sub(frozen, 1, 2), "bc"));
    check("a copy of frozen is writable", !quest_is_readonly(quest_string_get_sub(frozen, 0, 4)));
    check("setChar on plain", !raises(&quest_exc_string_error, set_char_plain) && equal(plain, "Xbcd"));
    check("setSub on plain", !raises(&quest_exc_string_error, set_sub_plain) && equal(plain, "XXYd"));

    /* The collector rewrites only its own byte of the header */
    quest_gc_collect();
    quest_gc_collect();
    check("frozen after collections", quest_is_readonly(frozen) && equal(frozen, "abcd"));
    check("plain after collections", !quest_is_readonly(plain));
    return 0;
}
"""


class TestRuntimeReadonly(unittest.TestCase):
    def test_frozen_strings_raise_on_writes(self):
        with tempfile.TemporaryDirectory() as directory:
            bin_path = Path(directory) / "readonly"
            compile_c_source(C_PROGRAM, output_path=bin_path)
            proc = run_binary(bin_path)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(proc.stdout.splitlines(), [
            "frozen is read-only: ok",
            "plain is not: ok",
            "setChar on frozen raises: ok",
            "setSub on frozen raises: ok",
            "frozen unchanged: ok",
            "frozen reads: ok",
            "a copy of frozen is writable: ok",
            "setChar on plain: ok",
            "setSub on plain: ok",
            "frozen after collections: ok",
            "plain after collections: ok",
        ])


if __name__ == "__main__":
    unittest.main()

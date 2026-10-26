"""Unit tests that the C runtime's characters are bytes, as in Typeful
Programming: the primitives pass bytes above 127 through unchanged, as the
interpreter's builtins do (test_builtins.TestByteCharacters)."""

import os
import sys
import tempfile
import unittest
from pathlib import Path

# Ensure bootstrap/python is in sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "bootstrap", "python"))

from quest.codegen.c.compiler_runner import compile_c_source, run_binary

C_PROGRAM = r"""
#include "quest_runtime.h"
#include "quest_serialization.h"
#include <stdio.h>
#include <stdlib.h>

static const char *file_name;
static QReader *rd;

static void check(const char *what, bool ok) { printf("%s: %s\n", what, ok ? "ok" : "wrong"); }

static bool equal(const QString *s, const char *bytes) {
    return s->length == (int64_t)strlen(bytes) && memcmp(s->data, bytes, (size_t)s->length) == 0;
}

static void open_file(const char *content) {
    FILE *f = fopen(file_name, "wb");
    fputs(content, f);
    fclose(f);
    rd = quest_reader_file(quest_string_new(file_name, (int64_t)strlen(file_name)));
}

static void ascii_char(void) { quest_ascii_char(256); }

/* Whether f raises exc */
static bool raises(const QException *exc, void (*f)(void)) {
    QExceptionHandler handler;
    handler.prev = quest_current_exception_handler;
    handler.catches = NULL;
    handler.n_catches = Q_CATCH_ALL;
    quest_current_exception_handler = &handler;
    if (setjmp(handler.env_jmp) == 0) {
        f();
        quest_current_exception_handler = handler.prev;
        return false;
    }
    quest_current_exception_handler = handler.prev;
    return quest_current_exception.exc == exc;
}

static void intern(void) { quest_dynamic_intern(rd); }

/* Whether dynamic.extern of the document's value writes it */
static bool extern_writes(const char *document) {
    char out_name[1024];
    snprintf(out_name, sizeof(out_name), "%s.out", file_name);
    QWriter *w = quest_writer_file(quest_string_new(out_name, (int64_t)strlen(out_name)));
    quest_dynamic_extern(w, quest_dynamic_intern(rd));
    quest_writer_close(w);
    char buf[1024] = { 0 };
    FILE *f = fopen(out_name, "rb");
    fread(buf, 1, sizeof(buf) - 1, f);
    fclose(f);
    return strcmp(buf, document) == 0;
}

int main(int argc, char **argv) {
    quest_gc_init();
    quest_builtins_init(argc, argv);
    file_name = argv[1];

    check("ascii.char(255)", quest_ascii_val(quest_ascii_char(255)) == 255);
    check("ascii.char(256)", raises(&quest_exc_ascii_error, ascii_char));

    open_file("a\xc3\xa9\xff");
    check("reader.getChar", quest_reader_get_char(rd) == 'a');
    check("reader.getString", equal(quest_reader_get_string(rd, 3), "\xc3\xa9\xff"));

    /* A byte above 127 is read raw or as a \u escape, and written as a \u escape */
    open_file("{\"quest\":1,\"types\":[],\"type\":\"String\",\"value\":\"\\u00e9\xc3\xa9\xff\"}");
    check("dynamic.intern and extern",
          extern_writes("{\"quest\":1,\"types\":[],\"type\":\"String\",\"value\":\"\\u00e9\\u00c3\\u00a9\\u00ff\"}"));
    open_file("{\"quest\":1,\"types\":[],\"type\":\"String\",\"value\":\"\\u0100\"}");
    check("dynamic.intern of \\u0100", raises(&quest_exc_dynamic_error, intern));

    setenv("QUEST_TEST_BYTES", "na\xc3\xafve", 1);
    check("system.getEnv", equal(quest_system_getenv(quest_string_new("QUEST_TEST_BYTES", 16)), "na\xc3\xafve"));
    check("system.args", equal((QString *)quest_system_args->data[2].p, "caf\xc3\xa9"));
    return 0;
}
"""


class TestRuntimeBytes(unittest.TestCase):
    def test_bytes_pass_through(self):
        with tempfile.TemporaryDirectory() as directory:
            bin_path = Path(directory) / "bytes"
            compile_c_source(C_PROGRAM, output_path=bin_path)
            proc = run_binary(bin_path, args=[str(Path(directory) / "input.txt"), "caf\u00e9"])
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(proc.stdout.splitlines(), [
            "ascii.char(255): ok",
            "ascii.char(256): ok",
            "reader.getChar: ok",
            "reader.getString: ok",
            "dynamic.intern and extern: ok",
            "dynamic.intern of \\u0100: ok",
            "system.getEnv: ok",
            "system.args: ok",
        ])


if __name__ == "__main__":
    unittest.main()

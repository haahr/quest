"""Unit tests that the C runtime's characters are ASCII, as in Typeful Programming: the primitives that would produce
another character raise their module's error, as the interpreter's builtins do (test_builtins.TestAsciiCharacters)."""

import os
import subprocess
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

/* Runs f, which must raise exc; prints what it is checking and whether it passed */
static void expect(const char *what, const QException *exc, void (*f)(void)) {
    QExceptionHandler handler;
    handler.prev = quest_current_exception_handler;
    handler.catches = NULL;
    handler.n_catches = Q_CATCH_ALL;
    quest_current_exception_handler = &handler;
    if (setjmp(handler.env_jmp) == 0) {
        f();
        quest_current_exception_handler = handler.prev;
        printf("%s: no exception\n", what);
    } else {
        quest_current_exception_handler = handler.prev;
        printf("%s: %s\n", what, quest_current_exception.exc == exc ? "ok" : quest_current_exception.exc->name);
    }
}

static void write_file(const char *content) {
    FILE *f = fopen(file_name, "wb");
    fputs(content, f);
    fclose(f);
}

static void open_file(const char *content) {
    write_file(content);
    rd = quest_reader_file(quest_string_new(file_name, (int64_t)strlen(file_name)));
}

static void ascii_char(void) { quest_ascii_char(128); }
static void get_char(void) { quest_reader_get_char(rd); }
static void get_string(void) { quest_reader_get_string(rd, 3); }
static void intern(void) { quest_dynamic_intern(rd); }
static void getenv_value(void) { quest_system_getenv(quest_string_new("QUEST_TEST_NON_ASCII", 20)); }
static void args(void) {
    char *argv[] = { "program", "caf\xc3\xa9", NULL };
    quest_system_init(2, argv);
}

int main(int argc, char **argv) {
    quest_gc_init();
    quest_builtins_init(argc, argv);
    file_name = argv[1];

    if (quest_ascii_char(127) != 127) printf("ascii.char(127) is wrong\n");
    expect("ascii.char(128)", &quest_exc_ascii_error, ascii_char);

    open_file("a\xc3\xa9");
    if (quest_reader_get_char(rd) != 'a') printf("reader.getChar is wrong\n");
    if (!quest_reader_more(rd)) printf("reader.more is wrong\n");
    expect("reader.getChar", &quest_exc_reader_error, get_char);

    open_file("ab\xff");
    expect("reader.getString", &quest_exc_reader_error, get_string);

    open_file("{\"quest\":1,\"types\":[],\"type\":\"String\",\"value\":\"\\u00e9\"}");
    expect("dynamic.intern of \\u00e9", &quest_exc_dynamic_error, intern);
    open_file("{\"quest\":1,\"types\":[],\"type\":\"String\",\"value\":\"\xc3\xa9\"}");
    expect("dynamic.intern of a non-ASCII byte", &quest_exc_dynamic_error, intern);

    setenv("QUEST_TEST_NON_ASCII", "caf\xc3\xa9", 1);
    expect("system.getEnv", &quest_exc_system_error, getenv_value);
    expect("system.args", &quest_exc_system_error, args);
    return 0;
}
"""


class TestRuntimeAscii(unittest.TestCase):
    def test_non_ascii_raises(self):
        with tempfile.TemporaryDirectory() as directory:
            bin_path = Path(directory) / "ascii"
            compile_c_source(C_PROGRAM, output_path=bin_path)
            proc = run_binary(bin_path, args=[str(Path(directory) / "input.txt")])
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(proc.stdout.splitlines(), [
            "ascii.char(128): ok",
            "reader.getChar: ok",
            "reader.getString: ok",
            "dynamic.intern of \\u00e9: ok",
            "dynamic.intern of a non-ASCII byte: ok",
            "system.getEnv: ok",
            "system.args: ok",
        ])


if __name__ == "__main__":
    unittest.main()

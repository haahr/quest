"""The Quest language server (docs/lsp.md section 10), driven through its
protocol as an editor drives it: tests/python/lsp_client.py starts
`./quest lsp` (or `quest lsp` with the quest QUEST_LSP_COMPILER names), on
documents in a scratch directory that import the standard library. Each test
checks what a request answers, not its whole text, since paths and the order
of some lists vary."""

import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from lsp_client import Client, uri_of  # noqa: E402

PROGRAM = """import util/maybe : util/Maybe

(* Twice n *)
let twice(n: Int): Int = n * 2
let x: Int = twice(21)
let y = maybe.some(x)
"""

INTERFACE = """interface Shapes export
    (* A circle's area *)
    area(r: Real): Real
    sides(n: Int): Int
end
"""

MODULE = """module shapes : Shapes export
    let area(r: Real): Real = r
    let sides(n: Int): Int = if n < 3 then "few" else n end
end
"""


def line_of(text: str, needle: str, nth: int = 0) -> tuple:
    """The 0-based line and UTF-16 column of the nth occurrence of needle"""
    at = -1
    for _ in range(nth + 1):
        at = text.index(needle, at + 1)
    before = text[:at]
    line = before.count("\n")
    column = len(before[before.rfind("\n") + 1:].encode("utf-16-le")) // 2
    return line, column


class LanguageServerTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.quest = os.environ.get("QUEST_LSP_COMPILER", str(ROOT_DIR / "quest"))
        # Builds the stages first, if they are stale, so that no test's
        # server waits for the build
        built = subprocess.run([cls.quest, "-e", "1"], capture_output=True, text=True)
        if built.returncode != 0:
            raise RuntimeError(f"quest did not build:\n{built.stdout}{built.stderr}")

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def setUp(self):
        self.work = Path(tempfile.mkdtemp(dir=self.tmp.name))
        env = dict(os.environ, QUEST_HOME=str(ROOT_DIR))
        self.client = Client([self.quest, "lsp"], env=env, cwd=str(self.work))
        self.addCleanup(self._stop)

    def _stop(self):
        self.client.dispose()

    def start(self, encodings=("utf-16",)) -> dict:
        return self.client.initialize(self.work, encodings, {"buildDir": str(self.work / "cache")})

    def write(self, name: str, text: str) -> Path:
        path = self.work / name
        path.write_text(text)
        return path

    def open(self, name: str, text: str) -> str:
        return self.client.open(self.work / name, text)

    def test_lifecycle(self):
        refused = self.client.request("textDocument/hover", {})
        self.assertEqual(refused["error"]["code"], -32002)
        result = self.start()
        capabilities = result["capabilities"]
        self.assertEqual(capabilities["positionEncoding"], "utf-16")
        for name in ("hoverProvider", "definitionProvider", "referencesProvider", "documentSymbolProvider",
                     "documentFormattingProvider", "documentHighlightProvider"):
            self.assertTrue(capabilities[name], name)
        self.assertEqual(capabilities["completionProvider"]["triggerCharacters"], ["."])
        self.assertEqual(self.client.request("no/such/method", {})["error"]["code"], -32601)
        self.assertEqual(self.client.close(), 0)

    def test_exit_without_shutdown_fails(self):
        self.start()
        self.client.notify("exit", None)
        self.assertEqual(self.client.process.wait(timeout=30), 1)

    def test_utf8_positions(self):
        self.assertEqual(self.start(("utf-8", "utf-16"))["capabilities"]["positionEncoding"], "utf-8")
        text = 'let s = "éé"\nlet n: Int = s\n'
        uri = self.open("u.quest", text)
        diagnostics = self.client.diagnostics(uri)
        self.assertEqual(len(diagnostics), 1)
        self.assertEqual(diagnostics[0]["range"]["start"], {"line": 1, "character": 13})
        self.client.close()

    def test_diagnostics_appear_and_clear(self):
        self.start()
        text = 'let a: Int = "no"\nlet b = undefinedName + 1\n'
        uri = self.open("d.quest", text)
        diagnostics = self.client.diagnostics(uri)
        messages = [d["message"] for d in diagnostics]
        self.assertEqual(len(messages), 2, messages)
        self.assertIn("Type mismatch", messages[0])
        self.assertIn("Undefined variable 'undefinedName'", messages[1])
        self.assertEqual(diagnostics[0]["range"]["start"], {"line": 0, "character": 13})
        self.assertEqual(diagnostics[0]["severity"], 1)
        self.client.change(uri, "let a: Int = 1\nlet b = a + 1\n", 2)
        self.assertEqual(self.client.diagnostics(uri), [])
        self.client.close()

    def test_utf16_columns(self):
        self.start()
        text = 'let s = "\U0001F600é"; let n: Int = s\n'
        uri = self.open("w.quest", text)
        diagnostics = self.client.diagnostics(uri)
        self.assertEqual(len(diagnostics), 1)
        self.assertEqual(diagnostics[0]["range"]["start"], {"line": 0, "character": line_of(text, "s\n")[1]})
        self.client.close()

    def test_navigation(self):
        self.start()
        uri = self.open("n.quest", PROGRAM)
        self.assertEqual(self.client.diagnostics(uri), [])
        line, column = line_of(PROGRAM, "twice", 1)
        hover = self.client.at("textDocument/hover", uri, line, column + 1)["contents"]["value"]
        self.assertIn("twice", hover)
        self.assertIn("Int", hover)
        self.assertIn("Twice n", hover)
        definition = self.client.at("textDocument/definition", uri, line, column)
        self.assertEqual(definition, [{"uri": uri, "range": {"start": {"line": 3, "character": 4},
                                                              "end": {"line": 3, "character": 9}}}])
        references = self.client.at("textDocument/references", uri, 3, 5, context={"includeDeclaration": True})
        self.assertEqual(sorted(r["range"]["start"]["line"] for r in references), [3, 4])
        without = self.client.at("textDocument/references", uri, 3, 5, context={"includeDeclaration": False})
        self.assertEqual([r["range"]["start"]["line"] for r in without], [4])
        highlights = self.client.at("textDocument/documentHighlight", uri, 3, 5)
        self.assertEqual(len(highlights), 2)
        # A member of an imported module: its interface's declaration
        line, column = line_of(PROGRAM, "some")
        hover = self.client.at("textDocument/hover", uri, line, column)["contents"]["value"]
        self.assertIn("maybe.some", hover)
        self.assertIn("Construct a some option value", hover)
        definition = self.client.at("textDocument/definition", uri, line, column)
        self.assertEqual(len(definition), 1)
        self.assertTrue(definition[0]["uri"].endswith("/lib/util/maybe.int.quest"), definition)
        maybe_text = (ROOT_DIR / "lib" / "util" / "maybe.int.quest").read_text()
        self.assertEqual(definition[0]["range"]["start"]["line"], line_of(maybe_text, "    some:")[0])
        # The module's name: its interface
        line, column = line_of(PROGRAM, "maybe.some")
        definition = self.client.at("textDocument/definition", uri, line, column)
        self.assertTrue(definition[0]["uri"].endswith("/lib/util/maybe.int.quest"), definition)
        self.client.close()

    def test_symbols(self):
        self.start()
        uri = self.open("n.quest", PROGRAM)
        symbols = self.client.result("textDocument/documentSymbol", {"textDocument": {"uri": uri}})
        self.assertEqual([(s["name"], s["kind"]) for s in symbols], [("twice", 12), ("x", 13), ("y", 13)])
        self.assertEqual(symbols[0]["selectionRange"]["start"], {"line": 3, "character": 4})
        self.write("shapes.int.quest", INTERFACE)
        iuri = self.open("shapes.int.quest", INTERFACE)
        symbols = self.client.result("textDocument/documentSymbol", {"textDocument": {"uri": iuri}})
        self.assertEqual(symbols[0]["name"], "Shapes")
        self.assertEqual([c["name"] for c in symbols[0]["children"]], ["area", "sides"])
        self.assertEqual(symbols[0]["children"][1]["selectionRange"]["start"], {"line": 3, "character": 4})
        self.client.close()

    def test_completion(self):
        self.start()
        uri = self.open("n.quest", PROGRAM)
        self.client.diagnostics(uri)
        typing = PROGRAM + "let z = maybe.is"
        self.client.change(uri, typing, 2)
        line, column = line_of(typing, "maybe.is")
        items = self.client.at("textDocument/completion", uri, line, column + len("maybe.is"))["items"]
        labels = [i["label"] for i in items]
        self.assertIn("isSome", labels)
        self.assertIn("isNone", labels)
        self.assertNotIn("some", labels)
        typing = PROGRAM + "let z = tw"
        self.client.change(uri, typing, 3)
        line, column = line_of(typing, "= tw")
        items = self.client.at("textDocument/completion", uri, line, column + 4)["items"]
        self.assertEqual([i["label"] for i in items if i["label"] == "twice"], ["twice"])
        self.client.close()

    def test_formatting(self):
        self.start()
        text = "let a   =  1\nlet b=a\n"
        uri = self.open("f.quest", text)
        edits = self.client.result("textDocument/formatting", {"textDocument": {"uri": uri}, "options": {}})
        expected = subprocess.run([self.quest, "fmt"], input=text, capture_output=True, text=True,
                                  env=dict(os.environ, QUEST_HOME=str(ROOT_DIR))).stdout
        self.assertEqual(len(edits), 1)
        self.assertEqual(edits[0]["newText"], expected)
        self.assertEqual(edits[0]["range"]["start"], {"line": 0, "character": 0})
        formatted = self.open("g.quest", expected)
        self.assertEqual(self.client.result("textDocument/formatting",
                                            {"textDocument": {"uri": formatted}, "options": {}}), [])
        self.client.close()

    def test_unit_errors_and_imports(self):
        """A module's failed member is reported, its other members still
        known; an error in an imported module is shown at its import, and in
        its own file"""
        self.start()
        self.write("shapes.int.quest", INTERFACE)
        self.write("shapes.mod.quest", MODULE)
        muri = self.open("shapes.mod.quest", MODULE)
        diagnostics = self.client.diagnostics(muri)
        self.assertEqual(len(diagnostics), 1, diagnostics)
        self.assertEqual(diagnostics[0]["range"]["start"]["line"], 2)
        line, column = line_of(MODULE, "= r")
        column += 2
        hover = self.client.at("textDocument/hover", muri, line, column)["contents"]["value"]
        self.assertIn("Real", hover)
        # Inside the member that failed: what checked before it failed
        line, column = line_of(MODULE, "n < 3")
        hover = self.client.at("textDocument/hover", muri, line, column)
        self.assertIsNotNone(hover)
        self.assertIn("Int", hover["contents"]["value"])
        program = "import shapes : Shapes\nlet a: Real = shapes.area(2.0)\n"
        puri = self.open("p.quest", program)
        self.assertEqual(self.client.diagnostics(puri), [])
        line, column = line_of(program, "area")
        hover = self.client.at("textDocument/hover", puri, line, column)["contents"]["value"]
        self.assertIn("A circle's area", hover)
        definition = self.client.at("textDocument/definition", puri, line, column)
        self.assertEqual(definition[0]["uri"], uri_of(self.work / "shapes.int.quest"))
        self.assertEqual(definition[0]["range"]["start"], {"line": 2, "character": 4})
        self.client.close()

    def test_overlay_is_seen_by_importers(self):
        """An open interface's unsaved text is what a program importing it
        is checked against"""
        self.start()
        self.write("shapes.int.quest", INTERFACE)
        iuri = self.open("shapes.int.quest", INTERFACE)
        program = "import shapes : Shapes\nlet n: Int = shapes.sides(4)\n"
        puri = self.open("p.quest", program)
        self.assertEqual(self.client.diagnostics(puri), [])
        self.client.change(iuri, INTERFACE.replace("sides(n: Int): Int", "sides(n: Int): Bool"), 2)
        self.client.request("textDocument/hover", {"textDocument": {"uri": puri},
                                                   "position": {"line": 0, "character": 0}})
        diagnostics = self.client.diagnostics(puri)
        self.assertEqual(len(diagnostics), 1, diagnostics)
        self.assertIn("Bool", diagnostics[0]["message"])
        self.client.close()

    def test_syntax_recovery(self):
        """A syntax error cuts out its declaration: later declarations are
        still checked, and uses of the cut one are not undefined"""
        self.start()
        text = "let a(n: Int): Int = n +\nlet b: Int = a(1)\nlet c: Int = \"no\"\nlet d = (\nlet e: Bool = 1\n"
        uri = self.open("s.quest", text)
        diagnostics = self.client.diagnostics(uri)
        lines = [d["range"]["start"]["line"] for d in diagnostics]
        messages = [d["message"] for d in diagnostics]
        self.assertIn(2, lines, messages)
        self.assertIn(4, lines, messages)
        self.assertTrue(any("Unexpected token" in m for m in messages), messages)
        self.assertFalse(any("Undefined" in m or "questLspBroken" in m for m in messages), messages)
        module = MODULE.replace("= r\n", "= r +\n").replace('"few"', "1")
        self.write("shapes.int.quest", INTERFACE)
        muri = self.open("shapes.mod.quest", module)
        diagnostics = self.client.diagnostics(muri)
        # Where the parser sees it: the next member, the one before being incomplete
        self.assertEqual([d["range"]["start"]["line"] for d in diagnostics], [2], diagnostics)
        line, column = line_of(module, "n < 3")
        hover = self.client.at("textDocument/hover", muri, line, column)
        self.assertIn("Int", hover["contents"]["value"])
        self.client.close()

    def test_grammar_keywords_are_the_tokenizer_s(self):
        """The VS Code grammar names the keywords the Pygments lexer does,
        which are the tokenizer's"""
        grammar = json.loads((ROOT_DIR / "tools" / "vscode" / "syntaxes" / "quest.tmLanguage.json").read_text())
        words = set()
        for pattern in grammar["patterns"]:
            name = pattern.get("name", "")
            if name in ("keyword.other.quest", "storage.type.quest", "constant.language.quest"):
                words.update(re.search(r"\(([^)]*)\)", pattern["match"]).group(1).split("|"))
        sys.path.insert(0, str(ROOT_DIR / "tools" / "jupyter"))
        try:
            source = (ROOT_DIR / "tools" / "jupyter" / "quest_lexer.py").read_text()
            lexer_words = set()
            for group in ("TYPE_KEYWORDS", "VALUE_KEYWORDS", "CONSTANTS"):
                body = re.search(group + r" = \((.*?)\)\n", source, re.S).group(1)
                lexer_words.update(re.findall(r'"([^"]+)"', body))
        finally:
            sys.path.pop(0)
        self.assertEqual(words, lexer_words)


if __name__ == "__main__":
    unittest.main()

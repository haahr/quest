"""A Pygments lexer for Quest (docs/syntax.md section 2), which nbconvert uses
to highlight a notebook's Quest cells when it exports one
(docs/jupyter-kernel.md section 6). tools/jupyter/install installs it as a
Pygments plugin named quest, in a wheel it builds; the kernel names it as its
pygments_lexer. Its keywords are the tokenizer's (questlang/syntax/tokenizer),
which tests/self-hosted/jupyter_kernel.py checks."""

from __future__ import annotations

from pygments.lexer import RegexLexer, bygroups, words
from pygments.token import Comment, Keyword, Name, Number, Operator, Punctuation, String, Text, Whitespace

# The tokenizer's keywords: the kind and type levels', capitalized, and the
# value level's
TYPE_KEYWORDS = (
    "TYPE", "POWER", "ALL", "DEF", "All", "Array", "Auto", "Def", "Exception", "Fun", "Let", "Option", "Out", "Rec",
    "Record", "Tuple", "Var", "Variant",
)
VALUE_KEYWORDS = (
    "and", "andif", "array", "as", "auto", "begin", "case", "do", "downto", "else", "elsif", "end", "exception", "exit",
    "export", "extent", "external", "false", "for", "fun", "if", "import", "inspect", "interface", "is", "isnot",
    "let", "loop", "module", "not", "of", "ok", "option", "ordinal", "orif", "out", "raise", "rec", "record", "then",
    "true", "try", "tuple", "unsound", "upto", "var", "variant", "when", "while", "with",
)
CONSTANTS = ("true", "false", "ok")


class QuestLexer(RegexLexer):
    name = "Quest"
    aliases = ["quest"]
    filenames = ["*.quest"]
    mimetypes = ["text/x-quest"]

    escape = r'\\(?:[nt"\'\\]|x[0-9A-Fa-f]{1,2}|[0-9]{1,3})'

    tokens = {
        "root": [
            (r"\s+", Whitespace),
            (r"\(\*", Comment.Multiline, "comment"),
            (r'"', String.Double, "string"),
            (r"'(?:" + escape + r"|[^'\\])'", String.Char),
            (r"~?0[xX][0-9A-Fa-f]+", Number.Hex),
            (r"~?[0-9]+(?:\.[0-9]+(?:[eE][+-]?[0-9]+)?|[eE][+-]?[0-9]+)", Number.Float),
            (r"~?[0-9]+", Number.Integer),
            # A binding's name, after let (and rec or var)
            (r"(let)(\s+)(rec\s+|var\s+)?([A-Za-z][A-Za-z0-9]*)",
             bygroups(Keyword, Whitespace, Keyword, Name.Function)),
            (words(CONSTANTS, suffix=r"\b"), Keyword.Constant),
            (words(TYPE_KEYWORDS, suffix=r"\b"), Keyword.Type),
            (words(VALUE_KEYWORDS, suffix=r"\b"), Keyword),
            (r"[A-Z][A-Za-z0-9]*", Name.Class),
            (r"[A-Za-z][A-Za-z0-9]*", Name),
            (r"[!@#$%&*_+=\-|\\`:<>/?^~]+", Operator),
            (r"[(){}\[\];,.]", Punctuation),
            (r".", Text),
        ],
        "comment": [
            (r"\(\*", Comment.Multiline, "#push"),
            (r"\*\)", Comment.Multiline, "#pop"),
            (r"[^(*]+", Comment.Multiline),
            (r"[(*]", Comment.Multiline),
        ],
        "string": [
            (escape, String.Escape),
            (r'"', String.Double, "#pop"),
            (r'[^"\\]+', String.Double),
            (r"\\", String.Double),
        ],
    }


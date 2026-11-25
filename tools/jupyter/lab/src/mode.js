// Quest for CodeMirror 6, as a stream parser (StreamLanguage's legacy mode
// interface): the tokens to color, and the indentation of a new line. It
// imports nothing, so that test.mjs can run it under plain Node; index.js wraps
// it for JupyterLab (docs/jupyter-kernel.md section 6).
//
// The tokens are those of tools/jupyter/quest_lexer.py, whose keywords are the
// tokenizer's; tests/self-hosted/jupyter_kernel.py checks that the lists here
// are the lexer's.

// The tokenizer's keywords: the kind and type levels', capitalized, and the
// value level's
export const TYPE_KEYWORDS = [
    "TYPE", "POWER", "ALL", "DEF", "All", "Array", "Auto", "Def", "Exception", "Fun", "Let", "Option", "Out", "Rec",
    "Record", "Tuple", "Var", "Variant",
];
export const VALUE_KEYWORDS = [
    "and", "andif", "array", "as", "auto", "begin", "case", "do", "downto", "else", "elsif", "end", "exception", "exit",
    "export", "extent", "external", "false", "for", "fun", "if", "import", "inspect", "interface", "is", "isnot",
    "let", "loop", "module", "not", "of", "ok", "option", "ordinal", "orif", "out", "raise", "rec", "record", "then",
    "true", "try", "tuple", "unsound", "upto", "var", "variant", "when", "while", "with",
];
export const CONSTANTS = ["true", "false", "ok"];

const typeKeywords = new Set(TYPE_KEYWORDS);
const valueKeywords = new Set(VALUE_KEYWORDS);
const constants = new Set(CONSTANTS);

// The keywords that open a construct closed by end. option, variant, and array
// are not among them: their constructs take an of, which opens them, as it
// does a listfix call (f of a b end).
const OPENERS = new Set([
    "begin", "case", "exception", "for", "if", "inspect", "interface", "loop", "module", "of", "raise", "record",
    "try", "tuple", "while", "auto", "Auto", "Option", "Record", "Tuple", "Variant",
]);
// The types in which a tag's with opens its fields' signature, closed by its
// own end (some with val: A end). Elsewhere a with continues its construct
// (option tag of T with ... end, when tag with x then).
const OPTION_TYPES = new Set(["Option", "Variant"]);
const BRACKETS = {"(": ")", "[": "]", "{": "}"};
const CLOSERS = new Set(Object.values(BRACKETS));

// Tokens that, ending a line, put the next one level deeper than it: a let's
// body after its =, and an arm's after its then or else
const CONTINUES = new Set(["=", ":=", "then", "do", "else"]);

// Whether a line starting with text continues the phrase before it: an infix
// operator, or a keyword that is one. ~ starts a negative literal, not one.
const LEADING_WORDS = new Set(["andif", "orif", "is", "isnot", "as"]);
function leads(text) {
    return LEADING_WORDS.has(text) || (OPERATOR.test(text) && !text.startsWith("~"));
}

// quest fmt's indentation unit (docs/formatter.md section 1.2), and the
// continuation inside brackets, twice it
export const UNIT = 4;
const CONTINUATION = 2 * UNIT;

const ESCAPE = String.raw`\\(?:[nt"'\\]|x[0-9A-Fa-f]{1,2}|[0-9]{1,3})`;
const CHAR = new RegExp(`'(?:${ESCAPE}|[^'\\\\])'`);
const HEX = /~?0[xX][0-9A-Fa-f]+/;
const REAL = /~?[0-9]+(?:\.[0-9]+(?:[eE][+-]?[0-9]+)?|[eE][+-]?[0-9]+)/;
const INT = /~?[0-9]+/;
const WORD = /[A-Za-z][A-Za-z0-9]*/;
const OPERATOR = /[!@#$%&*_+=\-|\\`:<>/?^~]+/;

function startState() {
    return {
        comment: 0,         // the depth of nested comments the line starts in
        stack: [],          // the open constructs: {kind, indent}, indent their line's
        lineIndent: 0,      // the indentation of the last line with code
        fresh: true,        // no code yet on this line
        last: null,         // the last code token's text
        led: false,         // the last line with code started with an operator
        depth: 0,           // the stack's depth at that line's start
        condition: false,   // in an if's, elsif's, or while's condition
        fun: -1,            // the stack's depth at the last line's last fun, or -1
        first: false,       // the token just read is its line's first
        line: 0,            // the number of the line being read
        def: false,         // the next name is a binding's
    };
}

function copyState(s) {
    return {...s, stack: s.stack.slice()};
}

// The end of a comment, at depth state.comment
function comment(stream, state) {
    while (!stream.eol()) {
        if (stream.match("(*")) {
            state.comment++;
        } else if (stream.match("*)")) {
            if (--state.comment === 0) {
                break;
            }
        } else {
            stream.next();
        }
    }
    return "comment";
}

// Records a code token: its line's indentation, the first time, and its text
function code(stream, state, text) {
    state.first = state.fresh;
    if (state.fresh) {
        state.lineIndent = stream.indentation();
        state.led = leads(text);
        state.depth = state.stack.length;
        state.fun = -1;
        state.fresh = false;
    }
    state.last = text;
    if (text === "if" || text === "elsif" || text === "while") {
        state.condition = true;
    } else if (text === "then" || text === "do") {
        state.condition = false;
    }
}

function popKeyword(state) {
    const top = state.stack[state.stack.length - 1];
    if (top && top.kind === "arm") {
        state.stack.pop();
    }
    const next = state.stack[state.stack.length - 1];
    if (next && !BRACKETS[next.kind]) {
        state.stack.pop();
    }
}

// A case's or an inspect's when or else starts an arm, which the next one ends
function arm(state) {
    const top = state.stack[state.stack.length - 1];
    if (top && top.kind === "arm") {
        state.stack.pop();
    }
    const next = state.stack[state.stack.length - 1];
    if (next && (next.kind === "case" || next.kind === "inspect")) {
        state.stack.push({kind: "arm", indent: state.lineIndent});
    }
}

// Reads a token, and notes when a fun's body has begun on the fun's line: a
// token past its parameters that no result type holds
function token(stream, state) {
    const style = tokenBase(stream, state);
    if (state.fun >= 0 && state.stack.length === state.fun && state.last !== "fun" && (
        style === "number" || style === "string" || style === "atom"
        || (style === "operator" && state.last !== ":" && state.last !== "::")
        || (style === "keyword" && valueKeywords.has(state.last)))) {
        state.fun = -1;
    }
    return style;
}

function tokenBase(stream, state) {
    if (stream.sol()) {
        state.fresh = true;
        state.line++;
    }
    if (state.comment > 0) {
        return comment(stream, state);
    }
    if (stream.eatSpace()) {
        return null;
    }
    if (stream.match("(*")) {
        state.comment = 1;
        return comment(stream, state);
    }
    if (stream.peek() === '"') {
        code(stream, state, '""');
        stream.next();
        let ch;
        while ((ch = stream.next()) != null) {
            if (ch === "\\") {
                stream.next();
            } else if (ch === '"') {
                break;
            }
        }
        return "string";
    }
    let m;
    if ((m = stream.match(CHAR))) {
        code(stream, state, m[0]);
        return "string";
    }
    if ((m = stream.match(HEX)) || (m = stream.match(REAL)) || (m = stream.match(INT))) {
        code(stream, state, m[0]);
        state.def = false;
        return "number";
    }
    if ((m = stream.match(WORD))) {
        const word = m[0];
        code(stream, state, word);
        if (word === "fun") {
            state.fun = state.stack.length;
        }
        if (word === "let" || word === "Let") {
            state.def = true;
            return "keyword";
        }
        if (state.def && (word === "rec" || word === "var")) {
            return "keyword";
        }
        const def = state.def;
        state.def = false;
        const top = state.stack[state.stack.length - 1];
        // array of(n x) is a call, with no end
        const call = word === "of" && stream.peek() === "(";
        if ((OPENERS.has(word) && !call) || (word === "with" && top && OPTION_TYPES.has(top.kind))) {
            state.stack.push({kind: word, indent: state.lineIndent, first: state.first});
        } else if (word === "when" || word === "else") {
            arm(state);
        } else if (word === "end") {
            popKeyword(state);
        }
        if (constants.has(word)) {
            return "atom";
        }
        if (typeKeywords.has(word) || valueKeywords.has(word)) {
            return "keyword";
        }
        if (def) {
            return "def";
        }
        return /^[A-Z]/.test(word) ? "typeName" : "variableName";
    }
    if ((m = stream.match(OPERATOR))) {
        code(stream, state, m[0]);
        return "operator";
    }
    const ch = stream.next();
    code(stream, state, ch);
    if (BRACKETS[ch]) {
        state.stack.push({kind: ch, indent: state.lineIndent, line: state.line});
        return "bracket";
    }
    if (CLOSERS.has(ch)) {
        const top = state.stack[state.stack.length - 1];
        if (top && BRACKETS[top.kind] === ch) {
            state.stack.pop();
            // A line that closes a bracket opened above continues the
            // opener's line, as a long signature's last line does
            if (top.line !== state.line) {
                state.lineIndent = top.indent;
            }
        }
        return "bracket";
    }
    return ";,.".includes(ch) ? "punctuation" : null;
}

// The column a line starting with textAfter goes at, as quest fmt lays it out
// (docs/formatter.md section 2):
// - one level inside the innermost open construct, or two inside a bracket,
//   where its closer goes too;
// - its end, elsif, and else at its line's column (a level in for an if that
//   began after its line's start), a try's when there too, but a case's or an
//   inspect's arms a level deeper, and a unit's import and export at the
//   unit's column;
// - a level deeper than the line above, when that line ends in =, then, do,
//   or else, for a let's body or a case arm's, or ends a fun's signature;
// - for a line starting with an operator, which continues the phrase above it
//   (section 2.0), a level deeper than its line, or two in a condition, or at
//   the column of a continuation above it that opened nothing.
// Returns null in a comment, which CodeMirror then indents as the line above.
export function indent(state, textAfter) {
    if (state.comment > 0) {
        return null;
    }
    const first = /^\s*([A-Za-z][A-Za-z0-9]*|[!@#$%&*_+=\-|\\`:<>/?^~]+)?/.exec(textAfter)[1];
    const declared = first && /^\s*[^\sA-Za-z0-9]+\(/.test(textAfter);
    if (first && leads(first) && !declared && state.last !== null) {
        if (state.led && state.stack.length <= state.depth) {
            return state.lineIndent;
        }
        return state.lineIndent + (state.condition ? CONTINUATION : UNIT);
    }
    const m = /^\s*(end|elsif|else|when|import|export|[)\]}])?(?![A-Za-z0-9])/.exec(textAfter);
    const word = m && m[1];
    let top = state.stack[state.stack.length - 1];
    if (top && top.kind === "arm" && word === "end") {
        top = state.stack[state.stack.length - 2];
    }
    let column = 0;
    if (top) {
        const arms = top.kind === "case" || top.kind === "inspect";
        // An if that starts after its line's start, its first arm on that
        // line, keeps its other arms a level in
        const inner = top.kind === "if" && !top.first ? UNIT : 0;
        if (CLOSERS.has(word)) {
            column = top.indent + CONTINUATION;
        } else if (word === "end") {
            column = top.indent + inner;
        } else if (top.kind === "arm" && (word === "else" || word === "when")) {
            column = top.indent;
        } else if (word === "elsif" || word === "else" || word === "when") {
            column = arms ? top.indent + UNIT : top.indent + inner;
        } else if ((word === "import" || word === "export") && (top.kind === "module" || top.kind === "interface")) {
            column = top.indent;
        } else {
            column = top.indent + (BRACKETS[top.kind] ? CONTINUATION : UNIT);
        }
    }
    // A fun whose parameters and result type ended the line above has its
    // body below it
    if (!word && state.fun === state.stack.length) {
        return state.lineIndent + UNIT;
    }
    // After a condition of several lines, the body goes by the construct
    if (!word && CONTINUES.has(state.last) && !state.led) {
        column = Math.max(column, state.lineIndent + UNIT);
    }
    return column;
}

export const quest = {
    name: "quest",
    startState,
    copyState,
    token,
    indent,
    blankLine(state) {
        state.fresh = true;
        state.line++;
    },
    languageData: {
        commentTokens: {block: {open: "(*", close: "*)"}},
        // Typing the last letter of one of these reindents its line
        indentOnInput: /^\s*(?:end|elsif|else|when|import|export|andif|orif|[)\]}]|[!@#$%&*_+=\-|\\`:<>/?^]+)$/,
        closeBrackets: {brackets: ["(", "[", "{", '"']},
    },
};

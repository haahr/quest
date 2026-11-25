// Tests src/mode.js under plain Node, with a string stream of its own in
// place of CodeMirror's: the styles of a line's tokens, and the column
// indent() gives each line of formatted samples (docs/jupyter-kernel.md
// section 7). tests/self-hosted/jupyter_kernel.py runs it.
//
//     node test.mjs                 the tests
//     node test.mjs --scan FILE...  each line of formatted files whose
//                                   indentation indent() would not give

import {readFileSync} from "node:fs";
import {indent, quest} from "./src/mode.js";

// CodeMirror's StringStream, as much of it as mode.js uses
class Stream {
    constructor(string) {
        this.string = string;
        this.pos = 0;
    }
    sol() { return this.pos === 0; }
    eol() { return this.pos >= this.string.length; }
    peek() { return this.string.charAt(this.pos) || undefined; }
    next() { return this.pos < this.string.length ? this.string.charAt(this.pos++) : undefined; }
    eatSpace() {
        const start = this.pos;
        while (/\s/.test(this.string.charAt(this.pos))) {
            this.pos++;
        }
        return this.pos > start;
    }
    match(pattern) {
        if (typeof pattern === "string") {
            if (this.string.startsWith(pattern, this.pos)) {
                this.pos += pattern.length;
                return true;
            }
            return false;
        }
        const m = this.string.slice(this.pos).match(pattern);
        if (m && m.index === 0) {
            this.pos += m[0].length;
            return m;
        }
        return null;
    }
    indentation() { return /^ */.exec(this.string)[0].length; }
}

// Runs one line through the mode, returning its tokens' [text, style] pairs
function line(state, text) {
    const tokens = [];
    if (/^\s*$/.test(text)) {
        quest.blankLine(state);
        return tokens;
    }
    const stream = new Stream(text);
    while (!stream.eol()) {
        const start = stream.pos;
        const style = quest.token(stream, state);
        if (stream.pos === start) {
            throw new Error(`no progress at ${start} in ${JSON.stringify(text)}`);
        }
        if (style) {
            tokens.push([text.slice(start, stream.pos), style]);
        }
    }
    return tokens;
}

// The lines of text whose indentation indent() would not give, as
// [line number, expected, given]
function misindented(text) {
    const state = quest.startState();
    const wrong = [];
    text.split("\n").forEach((t, i) => {
        if (!/^\s*$/.test(t)) {
            const want = /^ */.exec(t)[0].length;
            const got = indent(quest.copyState(state), t.trimStart());
            if (got !== null && got !== want) {
                wrong.push([i + 1, want, got]);
            }
        }
        line(state, t);
    });
    return wrong;
}

let failures = 0;
function check(name, got, want) {
    const a = JSON.stringify(got);
    const b = JSON.stringify(want);
    if (a !== b) {
        failures++;
        console.log(`FAIL ${name}\n  got  ${a}\n  want ${b}`);
    }
}

if (process.argv[2] === "--scan") {
    let lines = 0;
    let wrong = 0;
    for (const file of process.argv.slice(3)) {
        const text = readFileSync(file, "utf8");
        lines += text.split("\n").filter((t) => !/^\s*$/.test(t)).length;
        for (const [n, want, got] of misindented(text)) {
            wrong++;
            console.log(`${file}:${n}: at ${want}, indent() gives ${got}`);
        }
    }
    console.log(`${wrong} of ${lines} lines misindented`);
    process.exit(0);
}

// Styles
const state = quest.startState();
check("let", line(state, 'let rec f(x: Int): Bool = not(x = 0) (* a (* nested *) comment *)'), [
    ["let", "keyword"], ["rec", "keyword"], ["f", "def"], ["(", "bracket"], ["x", "variableName"],
    [":", "operator"], ["Int", "typeName"], [")", "bracket"], [":", "operator"], ["Bool", "typeName"],
    ["=", "operator"], ["not", "keyword"], ["(", "bracket"], ["x", "variableName"], ["=", "operator"],
    ["0", "number"], [")", "bracket"], ["(* a (* nested *) comment *)", "comment"],
]);
check("literals", line(state, `"a\\"b" 'c' '\\n' ~0x1F 2.5e3 true ok`), [
    ['"a\\"b"', "string"], ["'c'", "string"], ["'\\n'", "string"], ["~0x1F", "number"], ["2.5e3", "number"],
    ["true", "atom"], ["ok", "atom"],
]);
check("types", line(state, "Let T = Fun(A::TYPE) Option none end"), [
    ["Let", "keyword"], ["T", "def"], ["=", "operator"], ["Fun", "keyword"], ["(", "bracket"],
    ["A", "typeName"], ["::", "operator"], ["TYPE", "keyword"], [")", "bracket"], ["Option", "keyword"],
    ["none", "variableName"], ["end", "keyword"],
]);
const multi = quest.startState();
line(multi, "(* a comment");
check("comment across lines", line(multi, "  still *) x"), [["  still *)", "comment"], ["x", "variableName"]]);

// Indentation, of text laid out as quest fmt lays it out
const samples = {
    module: `module maybe : Maybe export
    let error: Exception = exception error: Ok end

    Let T = Fun(A::TYPE) Option
        none
        some with val: A end
    end

    let unwrap(A::TYPE)(o: T(A)): A =
        if o?some then
            o!some.val
        elsif o?none then
            raise error end
        else
            raise error
            end
        end
end`,
    program: `let n =
    3
let total = var(0)
for i = 0 upto n - 1 do
    while {total > 10} do
        total := total - 1
    end
    total := total + i
end
let s = f of
    1
    2
end
let g(x: Int): Int =
    begin
        x
    end`,
    cases: `let toInt(v: Value): Int =
    case v
        when jNumber with x then
            x.n
        when jNull then 0
        else
            raise error end
    end
let r =
    try
        g(1)
    when e then 2
    else 3
    end`,
    brackets: `let x = f(a
        b)
let y = tuple
    let a = [1
            2]
end`,
    arms: `let print(v: Value): Ok =
    case v
        when jArray with x then
            sb.char(b '[')
            sb.char(b ']')
        when jNull then
            sb.str(b "null")
        else
            ok
    end`,
    continuations: `let isComment = {j < m}
    andif {{i >= n}
        orif {a < b}}
    andif c
while {b < n} andif {c is 0}
        andif {d
                orif e} do
    b := b + 1
end
let total = a
    + b
    + c`,
    funs: `let elemAt = fun(o: Int): maybe.T(Elem)
    begin
        o
    end
let kept = vector.filter(toks fun(t: Token): Bool
    t.ok)
let neg = fun(a: Int): Int 0 - a
let rec check(
        t: Type offset: Int
        ): Ok =
    ok
let m = if a then b
    else c end`,
    interface: `interface Maybe import
    iter : Iter
export
    Let T(A::TYPE) <: Object
    let unwrap(A::TYPE)(o: T(A)): A
    <+>(a: T b: T): T
end`,
};
for (const [name, text] of Object.entries(samples)) {
    check(`indent ${name}`, misindented(text), []);
}

// Inside a comment the mode leaves the column to CodeMirror
const open = quest.startState();
line(open, "(* open");
check("indent in a comment", indent(open, "x"), null);

if (failures > 0) {
    console.log(`${failures} failed`);
    process.exit(1);
}
console.log("mode tests passed");

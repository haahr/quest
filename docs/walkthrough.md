# The Life of argmax: A Walk Through the Quest Compiler

This document follows one small Quest program through every phase of the compiler, from the characters of its
source file to the C code that runs it. At each phase it says what the phase is for, shows what the phase produces
for the program, and explains what changed. It is written for a reader who knows Python but not compilers, and not
languages like ML or Haskell whose type systems Quest resembles.

The program is in [examples/argmax/](../examples/argmax/). Every phase's output can be reproduced with

```
./quest --stop-after PHASE examples/argmax/argmax.quest
```

where PHASE is one of the names in the section headings. The outputs below are excerpts: `...` on a line of its own
stands for lines left out, and `...` within a line for text left out. A test (`tests/python/test_walkthrough.py`)
checks every excerpt against what the compiler prints today, so they cannot drift from it unnoticed.

---

## 1. The Program

### 1.1. argmax

`argmax` finds the position of the largest element of an array, and the element there. In Python it might be

```python
def argmax(a: list[E], key: Callable[[E], K], is_greater: Callable[[K, K], bool]) -> tuple[int, E]:
    if not a:
        raise Empty
    best, best_key = 0, key(a[0])
    for i in range(1, len(a)):
        k = key(a[i])
        if is_greater(k, best_key):
            best, best_key = i, k
    return best, a[best]
```

Like Python's `max(a, key=...)`, it takes a `key` function that turns each element into the thing to compare. Unlike
`max`, it also takes the comparison, `isGreater`, since Quest has no single `>` that works on every type: integers
are compared with `>`, reals with `>>`, and strings with a library function. Two types vary from one use of `argmax`
to another: `E`, the type of the array's elements, and `K`, the type the key function returns.

Here it is in Quest, as [examples/argmax/argmax.quest](../examples/argmax/argmax.quest) has it:

<!-- excerpt: examples/argmax/argmax.quest source -->
```quest
(* @echo *)
(* argmax: the first element of an array whose key is greatest *)

import arrayOp: ArrayOp;
import string: StringOp;
import scoring: Scoring;

exception empty: Ok end;

let argmax(E::TYPE K::TYPE)(
           a: Array(E)
           key: All(e: E) K
           isGreater: All(x: K y: K) Bool): Tuple index: Int element: E end =
    begin
        let n = arrayOp.size(:E a);
        if n is 0 then raise empty end end;
        let var best = 0;
        let var bestKey = key(a[0]);
        for i = 1 upto n - 1 do
            let k = key(a[i]);
            if isGreater(k bestKey) then
                best := i;
                bestKey := k
            end
        end;
        tuple let index = best let element = a[best] end
    end;
```

Reading it as a Python programmer:

- **Comments** are `(* ... *)`. The first line, `(* @echo *)`, is a directive to the test runner, which asks it to
  run the program with `--echo` (§1.4). The compiler sees only a comment.
- **`import arrayOp: ArrayOp`** is like `import arrayop as arrayOp`, except that it names the *interface* the module
  must have, `ArrayOp`. An interface lists what a module provides and the types of those things, much as a Python
  `.pyi` stub file does, but the compiler insists on it.
- **`exception empty: Ok end`** makes a new exception. In Quest an exception is a value, like any other, bound to the
  name `empty`; Python's closest equivalent would be `empty = Exception()`. `Ok` is the type of "no interesting
  value", like Python's `None`: raising `empty` carries no extra information.
- **`let argmax(E::TYPE K::TYPE)(...)`** defines a function with *two* parameter lists. The first takes types: `E`
  and `K` are parameters whose values are types (`::TYPE` says so), as the type variables of a Python generic
  function are, except that in Quest they are real parameters, which the caller supplies or the compiler works out.
  The second list takes the values. Writing the type parameters first, in a list of their own, is the usual Quest
  style.
- **`a: Array(E)`** is an array of `E`s. Quest arrays have a fixed length.
- **`key: All(e: E) K`** is the type of a function from an `E` to a `K`, like `Callable[[E], K]`. Quest writes it
  `All(e: E) K` in source, and the compiler prints the same type as `Fun(e: E): K`, as below. The parameter name
  `e` is documentation; any function of one `E` returning a `K` will do.
- **`: Tuple index: Int element: E end`** is the result type, a tuple with two named components, like a
  `NamedTuple`.
- **`begin ... end`** is a block, whose phrases are separated by `;`. Its value is its last phrase's, so the block
  ends with the tuple it returns: Quest has no `return` statement.
- **`let n = ...`** names a value that never changes, and **`let var best = 0`** a variable that may, assigned with
  `:=`.
- **`arrayOp.size(:E a)`** calls the library's `size` with the type argument `E` (the leading `:` marks a type) and
  the array `a`.
- **`n is 0`** compares for equality. Quest's `=` only binds names.
- **`for i = 1 upto n - 1 do ... end`** runs `i` from 1 to `n - 1` *inclusive*, like `range(1, n)`.
- **`if ... then ... end`** with no `else` does nothing when the condition is false.

### 1.2. The longest string

<!-- excerpt: examples/argmax/argmax.quest source -->
```quest
...
(* The longest string *)
let words = array of "pear" "fig" "banana" "kiwi" end;
let longest = argmax(words string.length {>});
...
```

The key is `string.length`, the library function giving a string's length, and the comparison is `{>}`, integer
`>` written as a value (the braces make an operator into an ordinary function value, like Python's
`operator.gt`). The call gives no types: the compiler works out from the arguments that `E` is `String` and `K` is
`Int` (§6.1). The result is `tuple index=2 element="banana" end`.

### 1.3. The best candidate

The second use ranks candidates by a scoring function that argmax.quest never sees the inside of. The function is
declared by an interface, [examples/argmax/scoring.int.quest](../examples/argmax/scoring.int.quest):

<!-- excerpt: examples/argmax/scoring.int.quest source -->
```quest
(* A scoring function known only by its signature *)
interface Scoring export
    Def Candidate = Tuple name: String years: Int rating: Real end
    score(c: Candidate): Real
end;
```

`Def Candidate = ...` gives a type a name for everyone who imports the interface, and `score(c: Candidate): Real` is
the signature of a function the module must provide. Elsewhere, a module implements the interface. The one in
[examples/argmax/scoring.mod.quest](../examples/argmax/scoring.mod.quest) is a placeholder, so the example can run:

<!-- excerpt: examples/argmax/scoring.mod.quest source -->
```quest
module scoring: Scoring export
    Let Candidate = Tuple name: String years: Int rating: Real end;
    let score(c: Candidate): Real = c.rating
end;
```

This is the reason to use a module: the program depends only on the interface. The module is compiled on its own
(§14), and replacing it with a real scoring function needs no change to argmax.quest, nor recompiling it, as long
as the interface stays the same.

The program uses it like this:

<!-- excerpt: examples/argmax/argmax.quest source -->
```quest
...
(* The best-scoring candidate *)
let candidates = array of
    tuple let name = "Ada" let years = 12 let rating = 4.5 end
    tuple let name = "Grace" let years = 30 let rating = 4.9 end
end;
let best = argmax(candidates scoring.score {>>});
```

Each `tuple let ... end` makes a tuple whose components are named as the `let`s inside it name them. The scores are
`Real`s, so the comparison is `{>>}`, real `>`. Here `E` is the candidates' tuple type and `K` is `Real`.

### 1.4. Running it

`./quest` runs a program with the interpreter. `--echo` prints each top-level phrase, its type, and its value, as
an interactive session would:

<!-- excerpt: examples/argmax/argmax.quest interpret --echo -->
```
exception empty
let argmax:All(E :: TYPE K :: TYPE) Fun(a: Array(E) key: Fun(e: E): K isGreater: Fun(x: K y: K): Bool): Tuple index: Int element: E end = <fun>
let words:Array(String) = array of "pear" "fig" "banana" "kiwi" end
let longest:Tuple index: Int element: String end = tuple index=2 element="banana" end
let candidates:Array(Tuple name: String years: Int rating: Real end) = array of tuple name="Ada" years=12 rating=4.5 end tuple name="Grace" years=30 rating=4.9 end end
let best:Tuple index: Int element: Tuple name: String years: Int rating: Real end end = tuple index=1 element=tuple name="Grace" years=30 rating=4.9 end end
```

`argmax`'s type, `All(E :: TYPE K :: TYPE) Fun(...): ...`, reads "for all types `E` and `K`, a function from ... to
...". `best`'s type spells the candidate tuple out in full rather than calling it `Scoring_Candidate`, which is how a program that imports
`Scoring` names its `Candidate`. Nothing in the program says that `candidates` holds `Candidate`s: its type
is worked out from the tuples written in it, so it is the tuple type itself, and so is `E`. The two types are the
same type, since Quest compares types by their structure, not their names; writing
`let candidates: Array(Scoring_Candidate) = ...` would make the name appear.

---

## 2. The Phases at a Glance

A compiler is a series of translations, each from one representation of the program to another that is a little
closer to the machine. Quest's are:

| Phase | Input | Output | What it does |
|---|---|---|---|
| `tokenize` | text | tokens | splits the text into words and symbols |
| `parse` | tokens | syntax tree | finds the program's grammatical structure |
| `desugar` | syntax tree | core syntax tree | rewrites shorthand forms into basic ones |
| `typecheck` | core syntax tree | typed tree | works out every expression's type, and rejects programs whose types don't fit |
| `ir_core` | typed tree | IR | flattens the tree into simple steps (the *intermediate representation*) |
| `ir_specialized` | IR | IR | makes copies of generic functions for the types they are used at |
| `ir_closed` | IR | IR | moves every function to the top level, packaging what it uses |
| `ir_represented` | IR | IR | decides how each value is stored, and converts between storage forms |
| `ir_described` | IR | IR | turns types needed while running into data |
| `codegen_c` | IR | C source | prints the IR as C |

After `typecheck` the road forks. The interpreter (`interpret`) runs the typed tree directly. The compiler goes on
through the IR to C, which a C compiler (clang or gcc) turns into a native program. Each phase's output is checked
before the next phase starts, so a mistake in the compiler tends to be caught where it is made.

The sections below follow the longest-string use through each phase, and turn to the candidate use where it differs.

---

## 3. tokenize: From Characters to Tokens

The tokenizer (also called a *lexer* or *scanner*) reads the text a character at a time and groups the characters
into **tokens**, the words of the language: names, keywords, numbers, strings, and punctuation. It drops spaces,
newlines, and comments. Each token records where it came from, so that later phases can say where an error is.

<!-- excerpt: examples/argmax/argmax.quest tokenize -->
```
4:1     KW_IMPORT       import
4:8     IDENT           arrayOp
4:15    COLON           :
4:17    IDENT           ArrayOp
4:24    SEMICOLON       ;
...
10:1    KW_LET          let
10:5    IDENT           argmax
10:11   LPAREN          (
10:12   IDENT           E
10:13   COLON_COLON     ::
10:15   KW_TYPE         TYPE
10:20   IDENT           K
10:21   COLON_COLON     ::
10:23   KW_TYPE         TYPE
10:27   RPAREN          )
10:28   LPAREN          (
11:12   IDENT           a
11:13   COLON           :
11:15   KW_ARRAY_TYPE   Array
...
31:1    KW_LET          let
31:5    IDENT           longest
31:13   EQUAL           =
31:15   IDENT           argmax
31:21   LPAREN          (
31:22   IDENT           words
31:28   IDENT           string
31:34   DOT             .
31:35   IDENT           length
31:42   LBRACE          {
31:43   SYMBOLIC_INFIX  >
31:44   RBRACE          }
31:45   RPAREN          )
31:46   SEMICOLON       ;
...
```

Each line is one token: its line and column, its kind, and its text. The first token is on line 4, since lines 1 to
3 hold only comments and a blank line. `let` is a keyword (`KW_LET`), while `argmax` and `string` are identifiers
(`IDENT`), names the program chose. `::` is a single token, not two colons. The tokenizer knows nothing of
meaning: it does not know that `E` will be a type or that `string.length` is a function.

---

## 4. parse: From Tokens to a Syntax Tree

The parser finds the grammatical structure in the stream of tokens, as a reader finds subject, verb, and object in a
sentence. Its output is a **syntax tree**: each construct of the program becomes a node, with the constructs inside
it as its children. Python's `ast` module produces the same kind of thing for Python (`ast.dump(ast.parse(...))`).

Here is the call that finds the longest word:

<!-- excerpt: examples/argmax/argmax.quest parse -->
```
...
    (LetValueBinding
      :name 'longest'
      :value (ExprApp
        :func (ExprId 'argmax')
        :args (
          (ExprId 'words')
          (ExprSelect
            :target (ExprId 'string')
            :field 'length'
          )
          (ExprId '>')
        )
      )
    )
...
```

A `let` binding (`LetValueBinding`) of the name `longest` to an application (`ExprApp`, a call) of `argmax` to three
arguments: the name `words`, the selection (`ExprSelect`) of `length` from `string`, and the name `>`. The braces of
`{>}` have done their job, making `>` an ordinary name, and are gone.

The definition of `argmax` shows a tree several levels deep. The parser has already turned `let argmax(...)(...) =
body` into the binding of a name to a function value, as Python's `def f(x): ...` is in effect `f = lambda x: ...`.
The function (`ExprFun`) has the type parameters and its body is another function, which has the value parameters
and the block:

<!-- excerpt: examples/argmax/argmax.quest parse -->
```
...
    (LetValueBinding
      :name 'argmax'
      :value (ExprFun
        :body (ExprFun
          :params (
            (FormalParam
              :name 'a'
              :type_annot (TypeArray
                :element_type (TypePath ('E'))
              )
              :mode VALUE
            )
...
          :body (ExprBlock
            :bindings (
              (LetValueBinding
                :name 'n'
                :value (ExprApp
                  :func (ExprSelect
                    :target (ExprId 'arrayOp')
                    :field 'size'
                  )
                  :args (
                    (TypeArgument
                      :type_val (TypePath ('E'))
                    )
                    (ExprId 'a')
                  )
                )
              )
              (ExprStmt
                :expr (ExprIf
                  :cond (ExprInfix
                    :left (ExprId 'n')
                    :op 'is'
                    :right (ExprInt 0 '0')
                  )
                  :then_branch (ExprRaise
                    :exc (ExprId 'empty')
                  )
                )
              )
...
        :type_params (
          (TypeFormal
            :name 'E'
            :bound (KindType)
          )
          (TypeFormal
            :name 'K'
            :bound (KindType)
          )
        )
...
```

The tree records structure, not meaning. Nothing yet says that `n` is an integer, that `arrayOp` has a `size`, or
even that the names used are defined.

---

## 5. desugar: Removing Shorthand

*Syntactic sugar* is shorthand: a form a programmer may write that means the same as a longer combination of other
forms. The desugarer rewrites the sugar into those other forms, so that the phases after it have fewer kinds of
node to handle. For example, Quest's `a andif b` (Python's `a and b`) becomes `if a then b else false end`, and
a function definition with one parameter list, `let f(x: Int): Int = x`, becomes the binding of a name to a function
value, `let f = fun(x: Int): Int x`.

This program uses none of the sugar the desugarer handles, so its output is the same as the parser's. (argmax's
definition, with two parameter lists, is one the parser itself builds as nested functions, as §4 showed.) That is
common: most phases leave unchanged the parts of a program they have no business with.

---

## 6. typecheck: Working Out Types

The type checker works out the type of every expression, checks that each is used as its type allows, and rejects
the program if not: passing a string where an integer is expected, calling something that isn't a function,
selecting a field that doesn't exist. Python checks such things only while the program runs, and only on the lines
that run; a tool like mypy checks them beforehand, as Quest's type checker does, but Quest's checks are part of the
language: a program that fails them does not run.

Its output is a **typed tree**: the tree again, with each node labeled by its type, names resolved to what they name,
and implicit steps made explicit. Here is the beginning of argmax's body:

<!-- excerpt: examples/argmax/argmax.quest typecheck -->
```
...
    (TypedLetValue 'argmax' :type All(E :: TYPE K :: TYPE) Fun(a: Array(E) key: Fun(e: E): K isGreater: Fun(x: K y: K): Bool): Tuple index: Int element: E end
...
        :body (TypedBlock :type Tuple index: Int element: E end
          :bindings (
            (TypedLetValue 'n' :type Int
              :value (TypedApp :type Int
                :func (TypedTypeApp [E] :type Fun(a: Array(E)): Int
                  :func (TypedSelect 'size' :type All(A :: TYPE) Fun(a: Array(A)): Int
                    :target (TypedVar 'arrayOp' :type Module 'arrayOp')))
                :args (
                  (TypedVar 'a' :type Array(E))
                )))
...
```

Things to notice:

- Every node has a type: `n` is an `Int`, and the block's value is the result tuple.
- `arrayOp.size` has the type `All(A :: TYPE) Fun(a: Array(A)): Int`: it is generic too. The call
  `arrayOp.size(:E a)` became two steps. First a **type application** (`TypedTypeApp [E]`) supplies `E` for `A`,
  giving an ordinary function of type `Fun(a: Array(E)): Int`; then an application (`TypedApp`) calls that with `a`.
- `E` and `K` are not any particular types here. Inside `argmax` they stand for whatever types a caller will supply,
  so the checker allows only what works for *every* type: `a[0]` can be passed to `key`, because both are about
  `E`, but `a[0] + 1` would be rejected, since not every `E` is a number.

Reading a variable declared with `let var` is made explicit too:

<!-- excerpt: examples/argmax/argmax.quest typecheck -->
```
...
                  :result (TypedIf :type Ok
                    :cond (TypedApp :type Bool
                      :func (TypedVar 'isGreater' :type Fun(x: K y: K): Bool)
                      :args (
                        (TypedVar 'k' :type K)
                        (TypedDerefCell :type K
                          :target (TypedVar 'bestKey' :type Var(K)))
                      ))
...
```

`bestKey` has the type `Var(K)`, a variable holding a `K`, and using its value is a step of its own,
`TypedDerefCell`, reading what the variable holds now.

### 6.1. Inferring the type arguments

The call `argmax(words string.length {>})` names no types, but `argmax` needs two. The type checker works them out,
a step called **type inference**: it matches each parameter's type against its argument's type and solves for the
unknowns.

- `a: Array(E)` against `words`, an `Array(String)`, gives `E = String`.
- `key: Fun(e: E): K` against `string.length`, a `Fun(string: String): Int`, agrees on `E` and gives `K = Int`.
- `isGreater: Fun(x: K y: K): Bool` against `>`, a `Fun(a: Int b: Int): Bool`, agrees on `K`.

The checker then writes the type arguments in, as if the program had said `argmax(:String :Int ...)`:

<!-- excerpt: examples/argmax/argmax.quest typecheck -->
```
...
    (TypedLetValue 'longest' :type Tuple index: Int element: String end
      :value (TypedApp :type Tuple index: Int element: String end
        :func (TypedTypeApp [String Int] :type Fun(a: Array(String) key: Fun(e: String): Int isGreater: Fun(x: Int y: Int): Bool): Tuple index: Int element: String end
          :func (TypedVar 'argmax' :type All(E :: TYPE K :: TYPE) Fun(...): Tuple index: Int element: E end))
        :args (
          (TypedVar 'words' :type Array(String))
          (TypedSelect 'length' :type Fun(string: String): Int
            :target (TypedVar 'string' :type Module 'string'))
          (TypedVar '>' :type Fun(a: Int b: Int): Bool)
        )))
...
```

The parameter names in function types don't have to agree: `string.length` names its parameter `string` and `key`'s
type says `e`, and the types match all the same. For the candidates, the same matching gives `E` the candidate
tuple type and `K = Real`:

<!-- excerpt: examples/argmax/argmax.quest typecheck -->
```
...
        :func (TypedTypeApp [Tuple name: String years: Int rating: Real end Real] :type ...
...
          (TypedSelect 'score' :type Fun(c: Candidate): Real
            :target (TypedVar 'scoring' :type Module 'scoring'))
          (TypedVar '>>' :type Fun(a: Real b: Real): Bool)
...
```

Here `score` takes a `Candidate` and the array holds the tuple type written out. Since `Candidate` is a name for
exactly that tuple type, they match.

### 6.2. The interpreter

The typed tree is complete enough to run. The interpreter (`interpret`) walks it, evaluating each node: a call
evaluates its arguments and then the function's body with the parameters bound to them, much as Python's own
interpreter does with its bytecode. It is the simplest way to run a Quest program, and it serves as the reference
the compiled code is tested against: every test program runs both ways, and must print the same.

The rest of this document follows the other path.

---

## 7. ir_core: The Intermediate Representation

The phases from here on work on the **intermediate representation** (IR), a form designed to be easy to transform
rather than easy to write. Its two main features:

- **One step at a time.** Every intermediate result gets a name. Where the source says `if isGreater(k bestKey)`,
  the IR first computes the condition into a temporary, then tests it. Temporaries are named `%1`, `%2`, ...
- **Every name is unique.** Two different variables that the source happens to give the same name are told apart by
  a suffix: the loop's `i` and a copy of it, `i.1`; argmax's local `best` and the top-level `best`, `best.1`.

Lowering, the step from the typed tree to the IR, also turns high-level constructs into lower-level ones: the `for`
loop becomes a general `loop` with an explicit test and `break`, and the library's `arrayOp.size` becomes the
primitive operation `prim extent`, which reads an array's length directly.

<!-- excerpt: examples/argmax/argmax.quest ir_core -->
```
...
main {
  let empty: Exception = exception empty
  funs {
    fun argmax [E::TYPE K::TYPE](a: Array(E), key: Fun(e: E): K, isGreater: Fun(x: K y: K): Bool): Tuple index: Int element: E end {
      let n: Int = prim extent(a)
      let %1: Bool = prim is(n, 0)
      if %1 {
        raise empty
      }
      var best: Int = 0
      let %2: E = index(a, 0)
      let %3: K = call key(%2)
      var bestKey: K = %3
      let %4: Int = prim -(n, 1)
      var i: Int = 1
      loop L1 {
        let %5: Bool = prim <=(i, %4)
        if %5 {
          let i.1: Int = i
          let %6: E = index(a, i.1)
          let k: K = call key(%6)
          let %7: Bool = call isGreater(k, bestKey)
          if %7 {
            best := i.1
            bestKey := k
          }
          let %8: Int = prim +(i, 1)
          i := %8
        } else {
          break L1
        }
      }
      let index: Int = best
      let element: E = index(a, best)
      let %9: Tuple index: Int element: E end = tuple(index, element)
      return %9
    }
  }
  let words: Array(String) = array("pear", "fig", "banana", "kiwi")
  let %10: Fun(string: String): Int = member string.length
  let %11: Fun(a: Int b: Int): Bool = builtin >
  let longest: Tuple index: Int element: String end = call argmax [String Int](words, %10, %11)
...
```

The whole function now fits on a screen and reads almost like Python written one operation per line. The program's
top-level phrases are the body of `main`. `argmax` sits in a `funs` group, the IR's way of defining functions
(possibly several that call one another). The type parameters are still there, in square brackets, and so are the
type arguments of the call: `call argmax [String Int](...)`. The `for` loop's variable `i` is copied into `i.1` at
the start of each pass, because in Quest each pass of a loop has its own `i`, which a function made inside the loop
could keep.

---

## 8. ir_specialized: Copies for Each Use

A generic function must work for any type. Compiled to machine code, that means it must handle every value the same
way, whether it is an integer, a real, or a pointer to a string, which costs time: values must be packed into a
common form before the call and unpacked after. **Specialization** avoids this by making a copy of the function for
the particular types a call supplies, in which `E` and `K` are replaced by those types. The call then goes to the
copy. Python has nothing like this, since it never compiles to machine code; C++ templates and Rust generics are
always specialized this way.

Quest specializes selectively, where it helps most. One of its rules is that a function returning a tuple that
involves its type parameters is specialized, since a tuple's layout in memory depends on the types of its
components. `argmax` returns `Tuple index: Int element: E end`, so both calls get copies:

<!-- excerpt: examples/argmax/argmax.quest ir_specialized -->
```
...
    fun argmax_spec(a.1: Array(String), key.1: Fun(e: String): Int, isGreater.1: Fun(x: Int y: Int): Bool): Tuple index: Int element: String end {
      let n.1: Int = prim extent(a.1)
...
      var best.1: Int = 0
      let %11: String = index(a.1, 0)
      let %12: Int = call key.1(%11)
      var bestKey.1: Int = %12
...
      let %18: Tuple index: Int element: String end = tuple(index.1, element.1)
      return %18
    }
    fun argmax_spec.1(a.2: Array(Tuple name: String years: Int rating: Real end), key.2: Fun(e: Tuple name: String years: Int rating: Real end): Real, isGreater.2: Fun(x: Real y: Real): Bool): Tuple index: Int element: Tuple name: String years: Int rating: Real end end {
...
  let longest: Tuple index: Int element: String end = call argmax_spec(words, %28, %29)
...
  let best.3: Tuple index: Int element: Tuple name: String years: Int rating: Real end end = call argmax_spec.1(candidates, %32, %33)
...
```

`argmax_spec` is `argmax` for strings and integers: it has no type parameters, and every `E` has become `String`
and every `K` `Int`. `argmax_spec.1` is the copy for candidates and reals. The calls no longer pass types. The
original, generic `argmax` stays too, though nothing calls it now. The copies have fresh names for
all their variables (`best.1`, `%11`), since every name in the IR is unique, so the temporaries of `main` are
renumbered too.

§12 shows what happens to a call that is not specialized.

---

## 9. ir_closed: Functions to the Top Level

Quest functions can be defined inside other functions, and can use the variables of the functions around them, as
Python's nested functions and lambdas can. C cannot do this: its functions are all defined at the top level and see
only their parameters and global variables. **Closure conversion** bridges the gap. It moves every function to the
top level and gives each a **closure**: a pair of the function and an *environment*, a record of the variables it
uses from around it (its *captures*). Python does the same thing at run time; a nested function's `__closure__`
holds its captures.

`argmax` is defined at the top level and uses no local variables from outside itself (`empty` is a global), so its
closures capture nothing, `{}`:

<!-- excerpt: examples/argmax/argmax.quest ir_closed -->
```
...
fun argmax_spec(a.1: Array(String), key.1: Fun(e: String): Int, isGreater.1: Fun(x: Int y: Int): Bool): Tuple index: Int element: String end {
...
main {
  let empty: Exception = exception empty
  let argmax.1: All(E :: TYPE K :: TYPE) Fun(...): Tuple index: Int element: E end = closure argmax {}
  let argmax_spec.2: Fun(a: Array(String) key: Fun(e: String): Int isGreater: Fun(x: Int y: Int): Bool): Tuple index: Int element: String end = closure argmax_spec {}
...
  let longest: Tuple index: Int element: String end = call argmax_spec.2(words, %1, %2)
...
```

The functions now come before `main` rather than inside it, and `main` makes a closure for each. Every function
value in compiled Quest is a closure, so `key` and `isGreater`, which argmax receives as arguments, are closures too,
and calling one calls its function with its environment.

---

## 10. ir_represented: How Values Are Stored

So far a value has had a type, but no decision has been made about how it is laid out in memory. The **represent**
pass makes those decisions, following the rules of Quest's run-time system:

- `Int`, `Real`, `Bool`, and `Char` are stored directly, as C's 64-bit integers, doubles, and so on.
- Strings, tuples, arrays, and closures are stored as pointers to memory allocated for them.
- A value whose type is a type parameter, like `E` inside the generic `argmax`, must be stored in a form that works
  for every type. That form is a **word**, 64 bits that can hold an integer, a real, or a pointer, as a C union.
  An array's elements are stored as words too, whatever their type, so that one array layout serves all.

Wherever a value is stored one way and used another, the pass inserts a **conversion** (`convert`), each with a
*plan* saying how. In the specialized program there is nothing to do: every call now goes to a copy whose
parameters have exactly the types of its arguments, so no value changes form, and the output is the same as
closure conversion's. Specialization has removed the conversions this pass would otherwise insert. §12 shows them.

---

## 11. ir_described: Types as Data

Some operations need to know a type while the program runs: printing a value with `--echo`, checking a value of
Quest's `Dynamic` type, and code that must handle values of a type parameter. For these, the compiler builds
**type descriptors**, data structures in the compiled program that describe a type (its kind, its size, its
components). Python keeps such information on every object (`type(x)`); compiled Quest keeps it only where it is
needed.

The **describe** pass gives each use of a type at run time its descriptor. In particular, every type parameter of a
function becomes an ordinary parameter holding a descriptor, so the generic `argmax` takes two more:

<!-- excerpt: examples/argmax/argmax.quest ir_described -->
```
...
fun argmax [E::TYPE K::TYPE](descriptor_E: descriptor, descriptor_K: descriptor, a: Array(E), key: Fun(e: E): K, isGreater: Fun(x: K y: K): Bool): Tuple index: Int element: E end {
...
```

The specialized copies have no type parameters, so they take no descriptors.

---

## 12. Detour: A Call That Is Not Specialized

If `argmax` returned only the element, its result type would be `E` instead of a tuple, and Quest's rules would not
specialize it: every call would go to the one generic function. [examples/argmax/element.quest](../examples/argmax/element.quest)
is that version, with only the longest-string use:

<!-- excerpt: examples/argmax/element.quest source -->
```quest
...
let argmax(E::TYPE K::TYPE)(
           a: Array(E)
           key: All(e: E) K
           isGreater: All(x: K y: K) Bool): E =
...
        a[best]
    end;

let words = array of "pear" "fig" "banana" "kiwi" end;
let longest = argmax(words string.length {>});
```

Here the represent and describe passes have work to do. After them, the call looks like this:

<!-- excerpt: examples/argmax/element.quest ir_described -->
```
...
static descriptor(String)
static descriptor(Int)
fun argmax [E::TYPE K::TYPE](descriptor_E: descriptor, descriptor_K: descriptor, a: Array(E), key: Fun(e: E): K, isGreater: Fun(x: K y: K): Bool): E {
...
  let %1: Fun(string: String): Int = member string.length
  let %2: Fun(a: Int b: Int): Bool = builtin >
  let %3: Fun(e: E): K = convert(%1, adapt)
  let %4: Fun(x: K y: K): Bool = convert(%2, adapt)
  let longest: E = call argmax.1 [descriptor(String), descriptor(Int)](words, %3, %4)
  let longest.1: String = convert(longest, unbox)
...
```

Three things were added:

- **Adapters.** The generic `argmax` calls `key` with a word and expects a word back, but `string.length` takes a
  string pointer and returns an integer. The plan `adapt` wraps it in a small function that converts the arguments
  from words, calls `string.length`, and converts its result to a word. The same goes for `>`.
- **Unboxing.** The result comes back as a word, and the plan `unbox` turns it into the string pointer that
  `longest` holds.
- **Descriptors.** The type arguments are now values: `descriptor(String)` and `descriptor(Int)`, static descriptors
  built into the program (listed at the top), passed where the type arguments were.

This is the cost specialization avoids, and the generated C below shows it in full. Passing descriptors is
Quest's rule for every generic function, even one like `argmax` that never looks at them, because Quest cannot
always know in advance which generic code will need its types at run time.

---

## 13. codegen_c: Printing C

The last phase prints the IR as C. By now every decision has been made, so this phase only spells them out: a C
`struct` for each tuple layout, a C function for each IR function, a C statement for each IR step. The C is meant to
be readable, and keeps the source's names with prefixes that say what they are: `qf_` for a Quest function, `l_` for
a local variable, `g_` for a global.

A tuple becomes a `struct`, with its components in order, `_0`, `_1`, .... The result of `argmax_spec` and a
candidate:

<!-- excerpt: examples/argmax/argmax.quest codegen_c -->
```c
...
struct QTuple_Int_String {
    QInt _0;
    QString * _1;
};
...
struct QTuple_String_Int_Real {
    QString * _0;
    QInt _1;
    QReal _2;
};
...
```

`QInt` and `QReal` are C's 64-bit integer and double, and a string is a pointer to a `QString`. The generic
`argmax`'s result has a `QVal`, the word of §10, where the element goes:

<!-- excerpt: examples/argmax/argmax.quest codegen_c -->
```c
...
struct QTuple_Int_QVal {
    QInt _0;
    QVal _1;
};
...
```

Here is `argmax_spec`, the copy for strings, in full except for its declarations of local variables:

<!-- excerpt: examples/argmax/argmax.quest codegen_c -->
```c
...
static Q_UNUSED QTuple_Int_String * qf_argmax_spec(void *_raw_env, QArray * l_a_2, QClosure * l_key_2, QClosure * l_isGreater_2) {
...
    l_n_2 = ((l_a_2)->length);
    l_t_10 = ((l_n_2) == (0LL));
    if (l_t_10) {
        quest_raise_at(g_empty, Q_OK_VAL, "examples/argmax/argmax.quest:16:24");
    }
    l_best_2 = 0LL;
    quest_check_array_bounds_at(l_a_2, 0LL, "examples/argmax/argmax.quest:18:31");
    l_t_11 = ((QString *)((l_a_2->data[0LL]).p));
    l_t_12 = ((QInt (*)(void *, QString *))(l_key_2->fn))(l_key_2->env, l_t_11);
    l_bestKey_2 = l_t_12;
    l_t_13 = ((l_n_2) - (1LL));
    l_i_3 = 1LL;
    for (;;) {
        l_t_14 = ((l_i_3) <= (l_t_13));
        if (l_t_14) {
            l_i_4 = l_i_3;
            quest_check_array_bounds_at(l_a_2, l_i_4, "examples/argmax/argmax.quest:20:25");
            l_t_15 = ((QString *)((l_a_2->data[l_i_4]).p));
            l_k_2 = ((QInt (*)(void *, QString *))(l_key_2->fn))(l_key_2->env, l_t_15);
            l_t_16 = ((QBool (*)(void *, QInt, QInt))(l_isGreater_2->fn))(l_isGreater_2->env, l_k_2, l_bestKey_2);
            if (l_t_16) {
                l_best_2 = l_i_4;
                l_bestKey_2 = l_k_2;
            }
            l_t_17 = ((l_i_3) + (1LL));
            l_i_3 = l_t_17;
        } else {
            goto L1_break;
        }
    }
    L1_break:;
    l_index_2 = l_best_2;
    quest_check_array_bounds_at(l_a_2, l_best_2, "examples/argmax/argmax.quest:26:46");
    l_element_2 = ((QString *)((l_a_2->data[l_best_2]).p));
    _t2 = (QTuple_Int_String *)quest_alloc(sizeof(QTuple_Int_String));
    _t2->_0 = l_index_2;
    _t2->_1 = l_element_2;
    l_t_18 = _t2;
    return l_t_18;
}
...
```

It follows the IR line for line. Some details:

- Every C function takes `_raw_env` first, the environment of the closure it was called through (§9). This one
  ignores it.
- `raise empty` calls the run-time system's `quest_raise_at`, passing where in the source the `raise` is, for the
  error message if nothing catches it.
- Every index into an array is checked first (`quest_check_array_bounds_at`), as Python checks `a[i]`.
- An array's elements are words (§10), so reading one takes the pointer out of the word, `.p`, and casts it to
  a `QString *`.
- Calling a closure calls its function pointer, `fn`, with its environment, `env`, first. The function pointer is
  cast to the function's C type, which the closure's Quest type fixes: `key` is called as a function from a string
  to an integer.
- The result tuple is allocated with `quest_alloc`, which allocates garbage-collected memory: as in Python, memory
  is reclaimed automatically when nothing refers to it any more.

`main` runs the top-level phrases in order. The two calls go straight to the copies, with `NULL` for the
environment, since the closures capture nothing. `scoring.score` is read from the module `scoring`, which is a record
in compiled code:

<!-- excerpt: examples/argmax/argmax.quest codegen_c -->
```c
...
int main(int argc, char **argv) {
...
    qv_mod_examples__argmax__scoring_init();
...
    g_t = (*((QClosure * *)((char *)qm_string.val + ((const OffsetDict_record_4992fba5350da421 *)qm_string.dict)->offset_length)));
    g_t_2 = (&qv_sym_gt_closure);
    g_longest = qf_argmax_spec(NULL, g_words, g_t, g_t_2);
...
    g_t_5 = (*((QClosure * *)((char *)qm_examples__argmax__scoring.val + ((const OffsetDict_record_271b3b37693c17ee *)qm_examples__argmax__scoring.dict)->offset_score)));
    g_t_6 = (&qv_sym_gt_gt_closure);
    g_best = qf_argmax_spec_2(NULL, g_candidates, g_t_5, g_t_6);
    return 0;
}
```

A module's members are fields of a record, and reading a field goes through the record's *offset table*, which says
where in the record each field is. That indirection is what lets the module be compiled separately: argmax.quest
knows only the interface, and finds `score` wherever the module put it.

### 13.1. The unspecialized call in C

In element.quest (§12), the adapter that lets the generic `argmax` call `string.length` is a C function of its own:

<!-- excerpt: examples/argmax/element.quest codegen_c -->
```c
...
static Q_UNUSED QVal qa_adapt(void *_raw_env, QVal qa_0) {
    QClosure *orig = (QClosure *)_raw_env;
    QInt _t2;
    _t2 = ((QInt (*)(void *, QString *))(orig->fn))(orig->env, ((QString *)(qa_0.p)));
    return ((QVal){ .i = (int64_t)(_t2) });
}
...
    _t3 = (QClosure *)quest_alloc(sizeof(QClosure));
    _t3->fn = (void *)qa_adapt;
    _t3->env = (void *)(g_t);
    g_t_3 = _t3;
...
    g_longest = qf_argmax(NULL, &quest_type_String, &quest_type_Int, g_words, g_t_3, g_t_4);
    g_longest_2 = ((QString *)(g_longest.p));
...
```

The adapter is itself a closure, whose environment is the original closure, `string.length`: it unwraps its word
argument into a string pointer, calls the original, and wraps the integer result in a word. The call passes the
descriptors of `String` and `Int` before the arguments, and the result is unwrapped from its word. Every call of
`key` and `isGreater` inside `argmax` goes through an adapter, which is the time specialization saves.

---

## 14. Building and Running

`./quest -o argmax examples/argmax/argmax.quest` builds a program. The driver finds what argmax.quest imports and
compiles each module on its own, from its own source, into an object file: the library's `arrayOp` and `string`,
and `scoring`. It checks each against the interface the program imported it by, then compiles argmax.quest to C and
the C to an object file with the system's C compiler, and links them all together with the run-time system. A
module compiled once is reused until its source changes. Replacing scoring.mod.quest with a real scoring function
recompiles only it, and relinks.

`--stop-after run_c_compiled` builds the program and runs it. With `--echo`, compiled code prints just as the
interpreter did in §1.4:

<!-- excerpt: examples/argmax/argmax.quest run_c_compiled --echo -->
```
...
let longest:Tuple index: Int element: String end = tuple index=2 element="banana" end
...
let best:Tuple index: Int element: Tuple name: String years: Int rating: Real end end = tuple index=1 element=tuple name="Grace" years=30 rating=4.9 end end
```

That the two agree is what the test suite checks for every test program, and for this example too.

---

## 15. Further Reading

- [pipeline.md](pipeline.md): the phases and the driver's options.
- [syntax.md](syntax.md) and [type-system.md](type-system.md): the language.
- [ir.md](ir.md): the IR and its passes in full, including the rules for specialization (§8.1) and representations
  (§4.2).
- [c-representation.md](c-representation.md): how values are laid out in compiled code, and type descriptors.
- [modules.md](modules.md) and [build-process.md](build-process.md): interfaces, modules, and separate compilation.
- [interpreter.md](interpreter.md): the interpreter.

"""Writes the probes of docs/wasm.md (their results are in section 9) as
WebAssembly text, NAME.wat here for each; build.sh assembles them, run.mjs,
stack.mjs, and limits.mjs run them in node, and wt.sh and wtlimits.sh in
wasmtime. Each measures a choice of the value representation (section 2) on
shapes the compiler uses: a tuple as a slot array or a flat struct (tuples);
an array of eqref or of i64, at a known type (arrays) and through another
module's generic get and set (vec, called by user); a parameter of its
precise type or an eqref cast on entry (vec and user); the stack's depth with
many locals and few (stack); and each engine's largest array (limits)."""
import os
HERE = os.path.dirname(os.path.abspath(__file__))
# The types the probes share, a subset of section 2's. $boxInt holds an Int
# too wide for an i31ref. $tuple is decision 1's tuple, its components in a
# slot array, and $tup4 the flat struct of four fields it is measured against.
# $arrayEq and $arrayI64 are an array of eqref or of i64 elements, the two
# subtypes of $array that vec tells apart by a cast.
PRELUDE = '''
 (rec
  (type $boxInt (struct (field i64)))
  (type $slots (array (mut eqref)))
  (type $i64s (array (mut i64)))
  (type $bytes (array (mut i8)))
  (type $obj (sub (struct (field $hash (mut i32)))))
  (type $tuple (sub final $obj (struct (field $hash (mut i32)) (field $slots (ref $slots)))))
  (type $tup4 (sub final $obj (struct (field $hash (mut i32)) (field $f0 (mut eqref)) (field $f1 (mut eqref)) (field $f2 (mut eqref)) (field $f3 (mut eqref)))))
  (type $array (sub $obj (struct (field $hash (mut i32)))))
  (type $arrayEq (sub final $array (struct (field $hash (mut i32)) (field $elems (ref $slots)))))
  (type $arrayI64 (sub final $array (struct (field $hash (mut i32)) (field $elems (ref $i64s)))))
  (type $string (sub final $obj (struct (field $hash (mut i32)) (field $len i32))))
 )
'''
def box(x):
    """Text for x, an i64 expression, as an eqref (section 2.2): an i31ref if
    the value equals the sign extension of its low 31 bits (shifted left 33
    and back), else a $boxInt. The function must declare an i64 local $bx."""
    return f'''(block (result eqref) (local.set $bx {x})
      (if (result eqref) (i64.eq (i64.shr_s (i64.shl (local.get $bx) (i64.const 33)) (i64.const 33)) (local.get $bx))
        (then (ref.i31 (i32.wrap_i64 (local.get $bx))))
        (else (struct.new $boxInt (local.get $bx)))))'''
def unbox(x):
    """Text for x, an eqref expression made by box, as an i64: an i31ref's
    value, sign-extended, or else the $boxInt's field"""
    return f'''(block $done (result i64)
        (block $isbox (result eqref)
          (br $done (i64.extend_i32_s (i31.get_s (br_on_cast_fail $isbox eqref (ref i31) {x})))))
        (struct.get $boxInt 0 (ref.cast (ref $boxInt))))'''

def tuples():
    """The tuples probe (section 9.1): buildA and buildB make a complete
    binary tree of depth d, each node a tuple of a kind (d itself), a span,
    and two children (i31 zeros at the leaves); walkA and walkB sum the kinds
    and spans. A's tuples are $tuple, B's $tup4. With big, a node's span is
    id * 2^32 + d, full-width as a merged file's span is, and so boxed;
    without, it is id, which fits 31 bits. runA and runB build a tree builds
    times, then walk the last one walks times and return the walks' sum."""
    def variant(v):
        if v == 'A':
            ty = '$tuple'
            mk = lambda k, s, l, r: f'(struct.new $tuple (i32.const 0) (array.new_fixed $slots 4 {k} {s} {l} {r}))'
            get = lambda t, i: f'(array.get $slots (struct.get $tuple $slots {t}) (i32.const {i}))'
        else:
            ty = '$tup4'
            mk = lambda k, s, l, r: f'(struct.new $tup4 (i32.const 0) {k} {s} {l} {r})'
            get = lambda t, i: f'(struct.get $tup4 $f{i} {t})'
        span = '(select (i64.or (i64.shl (local.get $id) (i64.const 32)) (local.get $d)) (local.get $id) (local.get $big))'
        left = f'(call $build{v} (i64.sub (local.get $d) (i64.const 1)) (i64.shl (local.get $id) (i64.const 1)) (local.get $big))'
        right = f'(call $build{v} (i64.sub (local.get $d) (i64.const 1)) (i64.or (i64.shl (local.get $id) (i64.const 1)) (i64.const 1)) (local.get $big))'
        zero = '(ref.i31 (i32.const 0))'
        return f'''
 (func $build{v} (export "build{v}") (param $d i64) (param $id i64) (param $big i32) (result eqref)
   (local $bx i64) (local $k eqref) (local $s eqref)
   (local.set $k {box('(local.get $d)')})
   (local.set $s {box(span)})
   (if (result eqref) (i64.eqz (local.get $d))
     (then {mk('(local.get $k)', '(local.get $s)', zero, zero)})
     (else {mk('(local.get $k)', '(local.get $s)', left, right)})))
 (func $walk{v} (export "walk{v}") (param $e eqref) (result i64)
   (local $t (ref {ty})) (local $k i64)
   (local.set $t (ref.cast (ref {ty}) (local.get $e)))
   (local.set $k {unbox(get('(local.get $t)', 0))})
   (i64.add (i64.add (local.get $k) {unbox(get('(local.get $t)', 1))})
     (if (result i64) (i64.eqz (local.get $k)) (then (i64.const 0))
       (else (i64.add (call $walk{v} {get('(local.get $t)', 2)}) (call $walk{v} {get('(local.get $t)', 3)}))))))
 (func (export "run{v}") (param $d i64) (param $big i32) (param $builds i32) (param $walks i32) (result i64)
   (local $t eqref) (local $acc i64)
   (loop $b (local.set $t (call $build{v} (local.get $d) (i64.const 1) (local.get $big)))
     (br_if $b (i32.gt_s (local.tee $builds (i32.sub (local.get $builds) (i32.const 1))) (i32.const 0))))
   (if (local.get $walks) (then
   (loop $w (local.set $acc (i64.add (local.get $acc) (call $walk{v} (local.get $t))))
     (br_if $w (i32.gt_s (local.tee $walks (i32.sub (local.get $walks) (i32.const 1))) (i32.const 0))))))
   (local.get $acc))'''
    return f'(module {PRELUDE} {variant("A")} {variant("B")})'

# The value stored at index i: i, which fits 31 bits, or with $big, i times
# an odd 64-bit constant, full-width as a Word hash is
VAL = '(select (i64.mul (local.get $i) (i64.const 0x9E3779B97F4A7C15)) (local.get $i) (local.get $big))'

def arrays():
    """The arrays probe at a known element type (section 9.2): fillEq and
    fillI make an array of n elements of VAL, as eqref (boxing those that do
    not fit 31 bits, decision 2) or as i64; sumEq and sumI add them up.
    runEq and runI fill an array fills times, then sum the last one sums
    times."""
    def runner(v, ty, fill, summ):
        return f'''
 (func (export "run{v}") (param $n i32) (param $big i32) (param $fills i32) (param $sums i32) (result i64)
   (local $a (ref null {ty})) (local $acc i64)
   (loop $b (local.set $a (call {fill} (local.get $n) (local.get $big)))
     (br_if $b (i32.gt_s (local.tee $fills (i32.sub (local.get $fills) (i32.const 1))) (i32.const 0))))
   (if (local.get $sums) (then
   (loop $w (local.set $acc (i64.add (local.get $acc) (call {summ} (ref.as_non_null (local.get $a)))))
     (br_if $w (i32.gt_s (local.tee $sums (i32.sub (local.get $sums) (i32.const 1))) (i32.const 0))))))
   (local.get $acc))'''
    return f'''(module {PRELUDE}
 (func $fillEq (param $n i32) (param $big i32) (result (ref $slots))
   (local $a (ref $slots)) (local $i i64) (local $bx i64)
   (local.set $a (array.new_default $slots (local.get $n)))
   (loop $l (array.set $slots (local.get $a) (i32.wrap_i64 (local.get $i)) {box(VAL)})
     (br_if $l (i64.lt_u (local.tee $i (i64.add (local.get $i) (i64.const 1))) (i64.extend_i32_u (local.get $n)))))
   (local.get $a))
 (func $sumEq (param $a (ref $slots)) (result i64)
   (local $i i32) (local $acc i64)
   (loop $l (local.set $acc (i64.add (local.get $acc) {unbox('(array.get $slots (local.get $a) (local.get $i))')}))
     (br_if $l (i32.lt_u (local.tee $i (i32.add (local.get $i) (i32.const 1))) (array.len (local.get $a)))))
   (local.get $acc))
 (func $fillI (param $n i32) (param $big i32) (result (ref $i64s))
   (local $a (ref $i64s)) (local $i i64)
   (local.set $a (array.new_default $i64s (local.get $n)))
   (loop $l (array.set $i64s (local.get $a) (i32.wrap_i64 (local.get $i)) {VAL})
     (br_if $l (i64.lt_u (local.tee $i (i64.add (local.get $i) (i64.const 1))) (i64.extend_i32_u (local.get $n)))))
   (local.get $a))
 (func $sumI (param $a (ref $i64s)) (result i64)
   (local $i i32) (local $acc i64)
   (loop $l (local.set $acc (i64.add (local.get $acc) (array.get $i64s (local.get $a) (local.get $i))))
     (br_if $l (i32.lt_u (local.tee $i (i32.add (local.get $i) (i32.const 1))) (array.len (local.get $a)))))
   (local.get $acc))
 {runner('Eq', '$slots', '$fillEq', '$sumEq')}
 {runner('I', '$i64s', '$fillI', '$sumI')}
)'''

def vec():
    """The module that user calls, standing for a generic vector in another
    unit (sections 9.2 and 9.3). U arrays are $arrayEq ("uniform"), T arrays
    $arrayI64 ("typed"); getT and setT find which by a cast, and for a typed
    array box what they return and unbox what they are given. Every get and
    set checks its index, trapping (unreachable) when it is out of bounds.
    fPrecise and fCast read a field of a string, a tuple, and an array, given
    at their own types or as eqrefs that are cast on entry (decision 3)."""
    bounds = lambda s: f'(if (i64.ge_u (local.get $i) (i64.extend_i32_u (array.len (local.get {s})))) (then (unreachable)))'
    tcast = '(br_on_cast_fail $eq (ref $array) (ref $arrayI64) (ref.cast (ref $array) (local.get $a)))'
    lens = '''(i64.extend_i32_u (i32.add (struct.get $string $len (local.get $s))
     (i32.add (array.len (struct.get $tuple $slots (local.get $t))) (array.len (struct.get $arrayEq $elems (local.get $a))))))'''
    return f'''(module {PRELUDE}
 (func (export "newU") (param $n i32) (result eqref) (struct.new $arrayEq (i32.const 0) (array.new_default $slots (local.get $n))))
 (func (export "newT") (param $n i32) (result eqref) (struct.new $arrayI64 (i32.const 0) (array.new_default $i64s (local.get $n))))
 (func (export "getU") (param $a eqref) (param $i i64) (result eqref)
   (local $s (ref $slots))
   (local.set $s (struct.get $arrayEq $elems (ref.cast (ref $arrayEq) (local.get $a))))
   {bounds('$s')}
   (array.get $slots (local.get $s) (i32.wrap_i64 (local.get $i))))
 (func (export "setU") (param $a eqref) (param $i i64) (param $x eqref)
   (local $s (ref $slots))
   (local.set $s (struct.get $arrayEq $elems (ref.cast (ref $arrayEq) (local.get $a))))
   {bounds('$s')}
   (array.set $slots (local.get $s) (i32.wrap_i64 (local.get $i)) (local.get $x)))
 (func (export "getT") (param $a eqref) (param $i i64) (result eqref)
   (local $s (ref $slots)) (local $t (ref $i64s)) (local $bx i64)
   (block $eq (result (ref $array))
     (local.set $t (struct.get $arrayI64 $elems {tcast}))
     {bounds('$t')}
     (return {box('(array.get $i64s (local.get $t) (i32.wrap_i64 (local.get $i)))')}))
   (local.set $s (struct.get $arrayEq $elems (ref.cast (ref $arrayEq))))
   {bounds('$s')}
   (array.get $slots (local.get $s) (i32.wrap_i64 (local.get $i))))
 (func (export "setT") (param $a eqref) (param $i i64) (param $x eqref)
   (local $s (ref $slots)) (local $t (ref $i64s))
   (block $eq (result (ref $array))
     (local.set $t (struct.get $arrayI64 $elems {tcast}))
     {bounds('$t')}
     (array.set $i64s (local.get $t) (i32.wrap_i64 (local.get $i)) {unbox('(local.get $x)')})
     (return))
   (local.set $s (struct.get $arrayEq $elems (ref.cast (ref $arrayEq))))
   {bounds('$s')}
   (array.set $slots (local.get $s) (i32.wrap_i64 (local.get $i)) (local.get $x)))
 (func (export "mkString") (result eqref) (struct.new $string (i32.const 0) (i32.const 5)))
 (func (export "mkTuple") (result eqref) (struct.new $tuple (i32.const 0) (array.new_default $slots (i32.const 3))))
 (func (export "fPrecise") (param $s (ref $string)) (param $t (ref $tuple)) (param $a (ref $arrayEq)) (result i64)
   {lens})
 (func (export "fCast") (param $es eqref) (param $et eqref) (param $ea eqref) (result i64)
   (local $s (ref $string)) (local $t (ref $tuple)) (local $a (ref $arrayEq))
   (local.set $s (ref.cast (ref $string) (local.get $es)))
   (local.set $t (ref.cast (ref $tuple) (local.get $et)))
   (local.set $a (ref.cast (ref $arrayEq) (local.get $ea)))
   {lens})
)'''

def user():
    """The module that calls vec through imports, as code in another unit
    would: runU and runT set every element of an n-element array fills
    times, then get them all sums times and return their sum; callPrecise
    and callCast call fPrecise or fCast n times."""
    def run(v):
        return f'''
 (func (export "run{v}") (param $n i32) (param $big i32) (param $fills i32) (param $sums i32) (result i64)
   (local $a eqref) (local $i i64) (local $acc i64) (local $bx i64)
   (local.set $a (call $new{v} (local.get $n)))
   (loop $b
     (local.set $i (i64.const 0))
     (loop $l (call $set{v} (local.get $a) (local.get $i) {box(VAL)})
       (br_if $l (i64.lt_u (local.tee $i (i64.add (local.get $i) (i64.const 1))) (i64.extend_i32_u (local.get $n)))))
     (br_if $b (i32.gt_s (local.tee $fills (i32.sub (local.get $fills) (i32.const 1))) (i32.const 0))))
   (if (local.get $sums) (then
   (loop $w
     (local.set $i (i64.const 0))
     (loop $l (local.set $acc (i64.add (local.get $acc) {unbox('(call $get'+v+' (local.get $a) (local.get $i))')}))
       (br_if $l (i64.lt_u (local.tee $i (i64.add (local.get $i) (i64.const 1))) (i64.extend_i32_u (local.get $n)))))
     (br_if $w (i32.gt_s (local.tee $sums (i32.sub (local.get $sums) (i32.const 1))) (i32.const 0))))))
   (local.get $acc))'''
    imp = ''.join(f'''
 (import "vec" "new{v}" (func $new{v} (param i32) (result eqref)))
 (import "vec" "get{v}" (func $get{v} (param eqref i64) (result eqref)))
 (import "vec" "set{v}" (func $set{v} (param eqref i64 eqref)))''' for v in 'UT')
    nn = lambda x: f'(ref.as_non_null (local.get {x}))'
    return f'''(module {PRELUDE} {imp}
 (import "vec" "mkString" (func $mkString (result eqref)))
 (import "vec" "mkTuple" (func $mkTuple (result eqref)))
 (import "vec" "fPrecise" (func $fPrecise (param (ref $string) (ref $tuple) (ref $arrayEq)) (result i64)))
 (import "vec" "fCast" (func $fCast (param eqref eqref eqref) (result i64)))
 {run('U')} {run('T')}
 (func (export "callPrecise") (param $n i32) (result i64)
   (local $s (ref null $string)) (local $t (ref null $tuple)) (local $a (ref null $arrayEq)) (local $acc i64)
   (local.set $s (ref.cast (ref $string) (call $mkString))) (local.set $t (ref.cast (ref $tuple) (call $mkTuple)))
   (local.set $a (ref.cast (ref $arrayEq) (call $newU (i32.const 7))))
   (loop $l (local.set $acc (i64.add (local.get $acc) (call $fPrecise {nn('$s')} {nn('$t')} {nn('$a')})))
     (br_if $l (i32.gt_s (local.tee $n (i32.sub (local.get $n) (i32.const 1))) (i32.const 0))))
   (local.get $acc))
 (func (export "callCast") (param $n i32) (result i64)
   (local $s eqref) (local $t eqref) (local $a eqref) (local $acc i64)
   (local.set $s (call $mkString)) (local.set $t (call $mkTuple)) (local.set $a (call $newU (i32.const 7)))
   (loop $l (local.set $acc (i64.add (local.get $acc) (call $fCast (local.get $s) (local.get $t) (local.get $a))))
     (br_if $l (i32.gt_s (local.tee $n (i32.sub (local.get $n) (i32.const 1))) (i32.const 0))))
   (local.get $acc))
)'''

def stack(nlocals=40):
    """The stack probe (section 9.4): recursive functions, each counting its
    calls in the exported global depth, so that stack.mjs can read how deep
    it went before the engine's RangeError. distinct has nlocals i64 locals,
    each computed from the one before; reused does the same steps in two
    locals; small has no locals. In distinct and reused, n and acc are live
    across the recursive call."""
    out = []
    for reuse, nm in ((False, 'distinct'), (True, 'reused')):
        name = (lambda i: f'$l{i % 2}') if reuse else (lambda i: f'$l{i}')
        decl = ' '.join(f'(local $l{i} i64)' for i in range(2 if reuse else nlocals))
        steps = [f'(local.set {name(0)} (i64.add (i64.mul (local.get $n) (i64.const 3)) (i64.const 1)))']
        for i in range(1, nlocals):
            steps.append(f'(local.set {name(i)} (i64.xor (i64.rotl (local.get {name(i-1)}) (i64.const 7)) (i64.add (local.get $n) (i64.const {i}))))')
        body = '\n   '.join(steps)
        out.append(f'''
 (func ${nm} (export "{nm}") (param $n i64) (result i64) {decl} (local $acc i64)
   (global.set $depth (i32.add (global.get $depth) (i32.const 1)))
   (if (i64.eqz (local.get $n)) (then (return (i64.const 0))))
   {body}
   (local.set $acc (local.get {name(nlocals - 1)}))
   (i64.add (local.get $acc) (i64.add (local.get $n) (call ${nm} (i64.sub (local.get $n) (i64.const 1))))))''')
    out.append('''
 (func $small (export "small") (param $n i64) (result i64)
   (global.set $depth (i32.add (global.get $depth) (i32.const 1)))
   (if (i64.eqz (local.get $n)) (then (return (i64.const 0))))
   (i64.add (local.get $n) (call $small (i64.sub (local.get $n) (i64.const 1)))))''')
    return f'''(module (global $depth (export "depth") (mut i32) (i32.const 0)) {''.join(out)})'''

def limits():
    """The limits probe (section 9.4): newEq, newI64, and newI8 make an array
    of n elements of each kind and return its length, for limits.mjs and
    wtlimits.sh to find by bisection the largest n that does not trap"""
    return f'''(module {PRELUDE}
 (func (export "newEq") (param i32) (result i32) (array.len (array.new_default $slots (local.get 0))))
 (func (export "newI64") (param i32) (result i32) (array.len (array.new_default $i64s (local.get 0))))
 (func (export "newI8") (param i32) (result i32) (array.len (array.new_default $bytes (local.get 0)))))'''

for name, f in (('tuples', tuples), ('arrays', arrays), ('vec', vec), ('user', user), ('stack', stack), ('limits', limits)):
    open(os.path.join(HERE, name + '.wat'), 'w').write(f())

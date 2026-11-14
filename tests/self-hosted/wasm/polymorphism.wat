(module $main
  (rec
    (type $obj (sub (struct (field $hash (mut i32)))))
    (type $boxInt (struct (field $value i64)))
    (type $boxReal (struct (field $value f64)))
    (type $slots (array (mut eqref)))
    (type $bytes (array (mut i8)))
    (type $i32s (array (mut i32)))
    (type $tupleLike (sub $obj (struct (field $hash (mut i32)))))
    (type $tuple (sub $tupleLike (struct (field $hash (mut i32)) (field $slots (ref $slots)))))
    (type $option (sub final $tuple (struct (field $hash (mut i32)) (field $slots (ref $slots)) (field $tag i32))))
    (type $string (sub final $obj (struct (field $hash (mut i32)) (field $length i32) (field $bytes (ref $bytes)))))
    (type $array (sub final $obj (struct (field $hash (mut i32)) (field $elems (ref $slots)))))
    (type $varBox (struct (field $tag i32) (field $payload eqref)))
    (type $clos (sub $obj (struct (field $hash (mut i32)))))
    (type $record (sub final $obj (struct (field $hash (mut i32)) (field $layout eqref) (field $slots (ref $slots)))))
    (type $dict (struct (field $indices (ref $i32s))))
    (type $recBox (struct (field $payload (ref $record)) (field $dict (ref $dict))))
    (type $exception (sub final $obj (struct (field $hash (mut i32)) (field $name (ref $string)))))
    (type $raised (struct (field $exception (ref $exception)) (field $payload eqref) (field $site eqref) (field $text eqref) (field $kind i32) (field $desc eqref)))
  )
  (type (func (param eqref eqref) (result eqref)))
  (type (func (param eqref i32) (result eqref)))
  (type (func (param i64) (result eqref)))
  (type (func (param i32) (result eqref)))
  (type (func (param eqref eqref eqref eqref i32 eqref)))
  (type (func (param eqref eqref)))
  (type (func (param eqref) (result i64)))
  (type (func (param eqref i32)))
  (type (func (param eqref i64) (result i32)))
  (type (func (param eqref i64 i32) (result eqref)))
  (type (func (param i64 i32) (result eqref)))
  (type (func (param eqref i64 i64) (result eqref)))
  (type (func (param eqref i64 eqref i64 i64) (result eqref)))
  (type (func (param eqref eqref) (result i32)))
  (type (func (param eqref) (result eqref)))
  (type (func (param eqref)))
  (type (func))
  (type (func (param (ref $clos) eqref eqref) (result eqref)))
  (type (func (param (ref $clos) i64) (result eqref)))
  (type (func (param (ref $clos) i64 eqref i64 i64) (result eqref)))
  (type (func (param (ref $clos) eqref i64 eqref eqref) (result eqref)))
  (type (func (param (ref $clos) eqref i64 i64 eqref) (result eqref)))
  (type (func (param (ref $clos) eqref eqref eqref eqref) (result eqref)))
  (type (func (param (ref $clos) eqref eqref eqref) (result i64)))
  (type (func (param (ref $clos) eqref i32 eqref eqref) (result eqref)))
  (type (func (param (ref $clos) i64) (result i32)))
  (type (func (param (ref $clos) eqref) (result i32)))
  (type (func (param (ref $clos) i64) (result i64)))
  (type (func (param (ref $clos) eqref) (result eqref)))
  (type $closU1 (sub $clos (struct (field $hash (mut i32)) (field $uniform (ref 46)))))
  (type (sub $closU1 (struct (field $hash (mut i32)) (field $uniform (ref 46)) (field $native (ref 43)))))
  (type $pos.closure (sub final 48 (struct (field $hash (mut i32)) (field $uniform (ref 46)) (field $native (ref 43)))))
  (type (sub $closU1 (struct (field $hash (mut i32)) (field $uniform (ref 46)) (field $native (ref 44)))))
  (type $nonEmpty.closure (sub final 50 (struct (field $hash (mut i32)) (field $uniform (ref 46)) (field $native (ref 44)))))
  (type (sub $closU1 (struct (field $hash (mut i32)) (field $uniform (ref 46)) (field $native (ref 45)))))
  (type $f.closure (sub final 52 (struct (field $hash (mut i32)) (field $uniform (ref 46)) (field $native (ref 45)))))
  (type $qa_adapt.closure (sub final 52 (struct (field $hash (mut i32)) (field $uniform (ref 46)) (field $native (ref 45)) (field $c0 (mut eqref)))))
  (type (sub $closU1 (struct (field $hash (mut i32)) (field $uniform (ref 46)) (field $native (ref 46)))))
  (type $f.closure.1 (sub final 55 (struct (field $hash (mut i32)) (field $uniform (ref 46)) (field $native (ref 46)))))
  (type $qa_adapt.closure.1 (sub final 55 (struct (field $hash (mut i32)) (field $uniform (ref 46)) (field $native (ref 46)) (field $c0 (mut eqref)))))
  (type $qa_adapt.closure.2 (sub final 50 (struct (field $hash (mut i32)) (field $uniform (ref 46)) (field $native (ref 44)))))
  (type $qa_adapt.closure.3 (sub final 50 (struct (field $hash (mut i32)) (field $uniform (ref 46)) (field $native (ref 44)))))
  (type $qa_adapt.closure.4 (sub final 55 (struct (field $hash (mut i32)) (field $uniform (ref 46)) (field $native (ref 46)))))
  (type $qa_adapt.closure.5 (sub final 55 (struct (field $hash (mut i32)) (field $uniform (ref 46)) (field $native (ref 46)))))
  (import "quest.runtime" "exception:int.error" (global $int.error (ref $exception)))
  (import "quest.runtime" "exception:real.error" (global $real.error (ref $exception)))
  (import "quest.runtime" "exception:word.error" (global $word.error (ref $exception)))
  (import "quest.runtime" "exception:string.error" (global $string.error (ref $exception)))
  (import "quest.runtime" "exception:arrayOp.error" (global $arrayOp.error (ref $exception)))
  (import "quest.runtime" "exception:variant.tagMismatch" (global $variant.tagMismatch (ref $exception)))
  (import "quest.runtime" "exception:ascii.error" (global $ascii.error (ref $exception)))
  (import "quest.runtime" "exception:dynamic.error" (global $dynamic.error (ref $exception)))
  (import "quest.runtime" "exception:writer.error" (global $writer.error (ref $exception)))
  (import "quest.runtime" "exception:reader.error" (global $reader.error (ref $exception)))
  (import "quest.runtime" "exception:system.error" (global $system.error (ref $exception)))
  (import "units/gen" "record.payload" (global (mut eqref)))
  (import "units/gen" "record.dict" (global (mut eqref)))
  (import "writer" "record.payload" (global (mut eqref)))
  (import "writer" "record.dict" (global (mut eqref)))
  (import "string" "record.payload" (global (mut eqref)))
  (import "string" "record.dict" (global (mut eqref)))
  (import "conv" "record.payload" (global (mut eqref)))
  (import "conv" "record.dict" (global (mut eqref)))
  (import "quest.runtime" "putString" (func $putString (type 18)))
  (import "quest.runtime" "putChar" (func $putChar (type 19)))
  (import "quest.runtime" "concat" (func $concat (type 18)))
  (import "quest.runtime" "convInt" (func $convInt (type 20)))
  (import "quest.runtime" "convBool" (func $convBool (type 21)))
  (import "quest.runtime" "convChar" (func $convChar (type 21)))
  (import "quest.runtime" "raise" (func $raise (type 22)))
  (import "quest.runtime" "uncaught" (func $uncaught (type 23)))
  (import "quest.runtime" "decimal" (func $decimal (type 20)))
  (import "quest.runtime" "hex" (func $hex (type 20)))
  (import "quest.runtime" "escaped" (func $escaped (type 19)))
  (import "quest.runtime" "boxInt" (func $boxInt (type 20)))
  (import "quest.runtime" "unboxInt" (func $unboxInt (type 24)))
  (import "quest.runtime" "fatal" (func $fatal (type 25)))
  (import "quest.runtime" "stringGetChar" (func $stringGetChar (type 26)))
  (import "quest.runtime" "stringSetChar" (func $stringSetChar (type 27)))
  (import "quest.runtime" "stringNew" (func $stringNew (type 28)))
  (import "quest.runtime" "stringGetSub" (func $stringGetSub (type 29)))
  (import "quest.runtime" "stringSetSub" (func $stringSetSub (type 30)))
  (import "quest.runtime" "stringEqual" (func $stringEqual (type 31)))
  (import "quest.runtime" "exceptionOf" (func $exceptionOf (type 32)))
  (import "quest.runtime" "payloadOf" (func $payloadOf (type 32)))
  (import "quest.runtime" "error" (tag $error (type 33)))
  (import "units/gen" "init" (func $units/gen.init (type 34)))
  (import "writer" "init" (func $writer.init (type 34)))
  (import "string" "init" (func $string.init (type 34)))
  (import "conv" "init" (func $conv.init (type 34)))
  (import "wasm/print" "init" (func $wasm/print.init (type 34)))
  (import "wasm/print" "show" (func $wasm/print.show (type 35)))
  (import "wasm/core" "init" (func $wasm/core.init (type 34)))
  (import "wasm/core" "base" (func $wasm/core.base (type 36)))
  (import "wasm/core" "newDesc" (func $wasm/core.newDesc (type 37)))
  (import "wasm/core" "setPart" (func $wasm/core.setPart (type 38)))
  (import "wasm/core" "setText" (func $wasm/core.setText (type 39)))
  (import "wasm/core" "instantiate" (func $wasm/core.instantiate (type 35)))
  (import "wasm/print" "echo" (func $wasm/print.echo (type 40)))
  (import "units/gen" "count" (func $units/gen.count (type 41)))
  (import "units/gen" "pick" (func $units/gen.pick (type 42)))
  (import "units/gen" "twice" (func $units/gen.twice (type 35)))
  (import "units/gen" "pair" (func $units/gen.pair (type 40)))
  (global $noClosure (ref $clos) i32.const 0 struct.new $clos)
  (global $quest_type_Int (mut eqref) ref.null none)
  (global $quest_type_Real (mut eqref) ref.null none)
  (global $quest_type_Bool (mut eqref) ref.null none)
  (global $quest_type_Char (mut eqref) ref.null none)
  (global $quest_type_String (mut eqref) ref.null none)
  (global $quest_type_Ok (mut eqref) ref.null none)
  (global $quest_type_Word (mut eqref) ref.null none)
  (global $quest_type_EmptyTuple (mut eqref) ref.null none)
  (global $quest_type_bound_vars (mut eqref) ref.null none)
  (global $QTuple_Int_String_c1d595445c9f41f3 (mut eqref) ref.null none)
  (global $pos.static (ref $pos.closure) i32.const 0 ref.func $pos.uniform ref.func $pos struct.new $pos.closure)
  (global $nonEmpty.static (ref $nonEmpty.closure) i32.const 0 ref.func $nonEmpty.uniform ref.func $nonEmpty struct.new $nonEmpty.closure)
  (global $f.static (ref $f.closure) i32.const 0 ref.func $f.uniform ref.func $f struct.new $f.closure)
  (global $f.static.1 (ref $f.closure.1) i32.const 0 ref.func $f.1 ref.func $f.1 struct.new $f.closure.1)
  (global $qa_adapt.static (ref $qa_adapt.closure.2) i32.const 0 ref.func $qa_adapt.uniform ref.func $qa_adapt struct.new $qa_adapt.closure.2)
  (global $qa_adapt.static.1 (ref $qa_adapt.closure.3) i32.const 0 ref.func $qa_adapt.uniform.1 ref.func $qa_adapt.1 struct.new $qa_adapt.closure.3)
  (global $qa_adapt.static.2 (ref $qa_adapt.closure.4) i32.const 0 ref.func $qa_adapt.2 ref.func $qa_adapt.2 struct.new $qa_adapt.closure.4)
  (global $qa_adapt.static.3 (ref $qa_adapt.closure.5) i32.const 0 ref.func $qa_adapt.4 ref.func $qa_adapt.4 struct.new $qa_adapt.closure.5)
  (export "_start" (func $_start))
  (elem declare func $pos.uniform $pos $nonEmpty.uniform $nonEmpty $f.uniform $f $f.1 $qa_adapt.uniform $qa_adapt $qa_adapt.uniform.1 $qa_adapt.1 $qa_adapt.2 $qa_adapt.uniform.2 $qa_adapt.3 $qa_adapt.4 $qa_adapt.5)
  (func $pos (type 43) (param $closure (ref $clos)) (param $n i64) (result i32)
    (local $v i32)
    local.get $n
    i64.const 0
    i64.gt_s
    local.set $v
    local.get $v
    return
    unreachable
  )
  (func $nonEmpty (type 44) (param $closure (ref $clos)) (param $s eqref) (result i32)
    (local $v i64)
    (local $v.1 i32)
    local.get $s
    ref.cast (ref $string)
    struct.get $string $length
    i64.extend_i32_u
    local.set $v
    local.get $v
    i64.const 0
    i64.gt_s
    local.set $v.1
    local.get $v.1
    return
    unreachable
  )
  (func $f (type 45) (param $closure (ref $clos)) (param $n i64) (result i64)
    (local $v i64)
    local.get $n
    i64.const 3
    i64.mul
    local.set $v
    local.get $v
    return
    unreachable
  )
  (func $f.1 (type 46) (param $closure (ref $clos)) (param $s eqref) (result eqref)
    (local $v eqref)
    local.get $s
    i32.const 0
    i32.const 1
    i32.const 0
    i32.const 1
    array.new_data $bytes $strings
    struct.new $string
    call $concat
    local.set $v
    local.get $v
    return
    unreachable
  )
  (func $qa_adapt (type 44) (param $closure (ref $clos)) (param $x eqref) (result i32)
    (local $orig eqref)
    (local $x.1 i64)
    global.get $pos.static
    local.set $orig
    local.get $x
    call $unboxInt
    local.set $x.1
    global.get $noClosure
    local.get $x.1
    return_call $pos
    unreachable
  )
  (func $qa_adapt.1 (type 44) (param $closure (ref $clos)) (param $x eqref) (result i32)
    (local $orig eqref)
    (local $x.1 eqref)
    global.get $nonEmpty.static
    local.set $orig
    local.get $x
    local.set $x.1
    global.get $noClosure
    local.get $x.1
    return_call $nonEmpty
    unreachable
  )
  (func $qa_adapt.2 (type 46) (param $closure (ref $clos)) (param $x eqref) (result eqref)
    (local $orig eqref)
    (local $x.1 i64)
    (local $r i64)
    (local $r.1 eqref)
    global.get $f.static
    local.set $orig
    local.get $x
    call $unboxInt
    local.set $x.1
    global.get $noClosure
    local.get $x.1
    call $f
    local.set $r
    local.get $r
    call $boxInt
    local.set $r.1
    local.get $r.1
    return
    unreachable
  )
  (func $qa_adapt.3 (type 45) (param $closure (ref $clos)) (param $x i64) (result i64)
    (local $orig eqref)
    (local $x.1 eqref)
    (local $t eqref)
    (local $r eqref)
    (local $r.1 i64)
    local.get $closure
    ref.cast (ref $qa_adapt.closure)
    struct.get $qa_adapt.closure $c0
    local.set $orig
    local.get $x
    call $boxInt
    local.set $x.1
    local.get $orig
    local.set $t
    local.get $t
    ref.test (ref 55)
    if (result eqref)
      local.get $t
      ref.cast (ref $clos)
      local.get $x.1
      local.get $t
      ref.cast (ref 55)
      struct.get 55 $native
      call_ref 46
    else
      local.get $t
      ref.cast (ref $clos)
      local.get $x.1
      local.get $t
      ref.cast (ref $closU1)
      struct.get $closU1 $uniform
      call_ref 46
    end
    local.set $r
    local.get $r
    call $unboxInt
    local.set $r.1
    local.get $r.1
    return
    unreachable
  )
  (func $qa_adapt.4 (type 46) (param $closure (ref $clos)) (param $x eqref) (result eqref)
    (local $orig eqref)
    (local $x.1 eqref)
    (local $r eqref)
    (local $r.1 eqref)
    global.get $f.static.1
    local.set $orig
    local.get $x
    local.set $x.1
    global.get $noClosure
    local.get $x.1
    call $f.1
    local.set $r
    local.get $r
    local.set $r.1
    local.get $r.1
    return
    unreachable
  )
  (func $qa_adapt.5 (type 46) (param $closure (ref $clos)) (param $x eqref) (result eqref)
    (local $orig eqref)
    (local $x.1 eqref)
    (local $t eqref)
    (local $r eqref)
    (local $r.1 eqref)
    local.get $closure
    ref.cast (ref $qa_adapt.closure.1)
    struct.get $qa_adapt.closure.1 $c0
    local.set $orig
    local.get $x
    local.set $x.1
    local.get $orig
    local.set $t
    local.get $t
    ref.test (ref 55)
    if (result eqref)
      local.get $t
      ref.cast (ref $clos)
      local.get $x.1
      local.get $t
      ref.cast (ref 55)
      struct.get 55 $native
      call_ref 46
    else
      local.get $t
      ref.cast (ref $clos)
      local.get $x.1
      local.get $t
      ref.cast (ref $closU1)
      struct.get $closU1 $uniform
      call_ref 46
    end
    local.set $r
    local.get $r
    local.set $r.1
    local.get $r.1
    return
    unreachable
  )
  (func $main (type 34)
    (local $pos eqref)
    (local $nonEmpty eqref)
    (local $v eqref)
    (local $pos.1 eqref)
    (local $v.1 i64)
    (local $v.2 eqref)
    (local $v.3 eqref)
    (local $v.4 eqref)
    (local $v.5 eqref)
    (local $v.6 eqref)
    (local $nonEmpty.1 eqref)
    (local $v.7 i64)
    (local $v.8 eqref)
    (local $v.9 eqref)
    (local $v.10 eqref)
    (local $v.11 eqref)
    (local $v.12 eqref)
    (local $v.13 eqref)
    (local $v.14 eqref)
    (local $v.15 eqref)
    (local $v.16 eqref)
    (local $v.17 eqref)
    (local $v.18 eqref)
    (local $v.19 eqref)
    (local $v.20 eqref)
    (local $v.21 eqref)
    (local $v.22 eqref)
    (local $v.23 i64)
    (local $v.24 i64)
    (local $v.25 eqref)
    (local $v.26 eqref)
    (local $v.27 eqref)
    (local $v.28 eqref)
    (local $f eqref)
    (local $f.1 eqref)
    (local $v.29 eqref)
    (local $v.30 eqref)
    (local $v.31 eqref)
    (local $t eqref)
    (local $v.32 i64)
    (local $v.33 eqref)
    (local $v.34 eqref)
    (local $v.35 eqref)
    (local $v.36 eqref)
    (local $f.2 eqref)
    (local $f.3 eqref)
    (local $v.37 eqref)
    (local $v.38 eqref)
    (local $v.39 eqref)
    (local $t.1 eqref)
    (local $v.40 eqref)
    (local $v.41 eqref)
    (local $v.42 eqref)
    (local $v.43 eqref)
    (local $v.44 eqref)
    (local $v.45 eqref)
    (local $p eqref)
    (local $p.1 eqref)
    (local $p.2 eqref)
    (local $v.46 i64)
    (local $v.47 eqref)
    (local $v.48 eqref)
    (local $v.49 eqref)
    (local $v.50 eqref)
    (local $v.51 eqref)
    (local $v.52 eqref)
    (local $v.53 eqref)
    (local $bad eqref)
    call $wasm/core.init
    call $wasm/print.init
    call $descriptors
    call $units/gen.init
    call $writer.init
    call $string.init
    call $conv.init
    global.get $pos.static
    local.set $pos
    global.get $nonEmpty.static
    local.set $nonEmpty
    i32.const 0
    i64.const 1
    call $boxInt
    i64.const -2
    call $boxInt
    i64.const 3
    call $boxInt
    array.new_fixed $slots 3
    struct.new $array
    local.set $v
    global.get $qa_adapt.static
    local.set $pos.1
    global.get $noClosure
    global.get $quest_type_Int
    local.get $v
    local.get $pos.1
    call $units/gen.count
    local.set $v.1
    local.get $v.1
    call $convInt
    local.set $v.2
    i32.const 1
    ref.i31
    local.set $v.3
    local.get $v.2
    i32.const 0
    i32.const 1
    i32.const 47
    i32.const 1
    array.new_data $bytes $strings
    struct.new $string
    call $concat
    local.set $v.4
    local.get $v.3
    local.get $v.4
    call $putString
    local.set $v.5
    i32.const 0
    i32.const 0
    i32.const 1
    i32.const 48
    i32.const 1
    array.new_data $bytes $strings
    struct.new $string
    i32.const 0
    i32.const 0
    i32.const 49
    i32.const 0
    array.new_data $bytes $strings
    struct.new $string
    i32.const 0
    i32.const 1
    i32.const 49
    i32.const 1
    array.new_data $bytes $strings
    struct.new $string
    i32.const 0
    i32.const 1
    i32.const 50
    i32.const 1
    array.new_data $bytes $strings
    struct.new $string
    array.new_fixed $slots 4
    struct.new $array
    local.set $v.6
    global.get $qa_adapt.static.1
    local.set $nonEmpty.1
    global.get $noClosure
    global.get $quest_type_String
    local.get $v.6
    local.get $nonEmpty.1
    call $units/gen.count
    local.set $v.7
    local.get $v.7
    call $convInt
    local.set $v.8
    i32.const 1
    ref.i31
    local.set $v.9
    local.get $v.8
    i32.const 0
    i32.const 1
    i32.const 51
    i32.const 1
    array.new_data $bytes $strings
    struct.new $string
    call $concat
    local.set $v.10
    local.get $v.9
    local.get $v.10
    call $putString
    local.set $v.11
    i32.const 0
    i32.const 3
    i32.const 52
    i32.const 3
    array.new_data $bytes $strings
    struct.new $string
    local.set $v.12
    i32.const 0
    i32.const 2
    i32.const 55
    i32.const 2
    array.new_data $bytes $strings
    struct.new $string
    local.set $v.13
    global.get $noClosure
    global.get $quest_type_String
    i32.const 1
    local.get $v.12
    local.get $v.13
    call $units/gen.pick
    local.set $v.14
    local.get $v.14
    local.set $v.15
    local.get $v.15
    local.set $v.16
    i32.const 1
    ref.i31
    local.set $v.17
    local.get $v.16
    i32.const 0
    i32.const 1
    i32.const 57
    i32.const 1
    array.new_data $bytes $strings
    struct.new $string
    call $concat
    local.set $v.18
    local.get $v.17
    local.get $v.18
    call $putString
    local.set $v.19
    i64.const 1
    call $boxInt
    local.set $v.20
    i64.const 2000000000000
    call $boxInt
    local.set $v.21
    global.get $noClosure
    global.get $quest_type_Int
    i32.const 0
    local.get $v.20
    local.get $v.21
    call $units/gen.pick
    local.set $v.22
    local.get $v.22
    call $unboxInt
    local.set $v.23
    local.get $v.23
    local.set $v.24
    local.get $v.24
    call $convInt
    local.set $v.25
    i32.const 1
    ref.i31
    local.set $v.26
    local.get $v.25
    i32.const 0
    i32.const 1
    i32.const 58
    i32.const 1
    array.new_data $bytes $strings
    struct.new $string
    call $concat
    local.set $v.27
    local.get $v.26
    local.get $v.27
    call $putString
    local.set $v.28
    global.get $f.static
    local.set $f
    global.get $qa_adapt.static.2
    local.set $f.1
    global.get $noClosure
    global.get $quest_type_Int
    local.get $f.1
    call $units/gen.twice
    local.set $v.29
    i32.const 0
    ref.func $qa_adapt.uniform.2
    ref.func $qa_adapt.3
    local.get $v.29
    struct.new $qa_adapt.closure
    local.set $v.30
    local.get $v.30
    local.set $v.31
    local.get $v.31
    local.set $t
    local.get $t
    ref.test (ref 52)
    if (result i64)
      local.get $t
      ref.cast (ref $clos)
      i64.const 5
      local.get $t
      ref.cast (ref 52)
      struct.get 52 $native
      call_ref 45
    else
      local.get $t
      ref.cast (ref $clos)
      i64.const 5
      call $boxInt
      local.get $t
      ref.cast (ref $closU1)
      struct.get $closU1 $uniform
      call_ref 46
      call $unboxInt
    end
    local.set $v.32
    local.get $v.32
    call $convInt
    local.set $v.33
    i32.const 1
    ref.i31
    local.set $v.34
    local.get $v.33
    i32.const 0
    i32.const 1
    i32.const 59
    i32.const 1
    array.new_data $bytes $strings
    struct.new $string
    call $concat
    local.set $v.35
    local.get $v.34
    local.get $v.35
    call $putString
    local.set $v.36
    global.get $f.static.1
    local.set $f.2
    global.get $qa_adapt.static.3
    local.set $f.3
    global.get $noClosure
    global.get $quest_type_String
    local.get $f.3
    call $units/gen.twice
    local.set $v.37
    i32.const 0
    ref.func $qa_adapt.5
    ref.func $qa_adapt.5
    local.get $v.37
    struct.new $qa_adapt.closure.1
    local.set $v.38
    local.get $v.38
    local.set $v.39
    local.get $v.39
    local.set $t.1
    local.get $t.1
    ref.test (ref 55)
    if (result eqref)
      local.get $t.1
      ref.cast (ref $clos)
      i32.const 0
      i32.const 2
      i32.const 60
      i32.const 2
      array.new_data $bytes $strings
      struct.new $string
      local.get $t.1
      ref.cast (ref 55)
      struct.get 55 $native
      call_ref 46
    else
      local.get $t.1
      ref.cast (ref $clos)
      i32.const 0
      i32.const 2
      i32.const 62
      i32.const 2
      array.new_data $bytes $strings
      struct.new $string
      local.get $t.1
      ref.cast (ref $closU1)
      struct.get $closU1 $uniform
      call_ref 46
    end
    local.set $v.40
    i32.const 1
    ref.i31
    local.set $v.41
    local.get $v.40
    i32.const 0
    i32.const 1
    i32.const 64
    i32.const 1
    array.new_data $bytes $strings
    struct.new $string
    call $concat
    local.set $v.42
    local.get $v.41
    local.get $v.42
    call $putString
    local.set $v.43
    i64.const 7
    call $boxInt
    local.set $v.44
    i32.const 0
    i32.const 5
    i32.const 65
    i32.const 5
    array.new_data $bytes $strings
    struct.new $string
    local.set $v.45
    global.get $noClosure
    global.get $quest_type_Int
    global.get $quest_type_String
    local.get $v.44
    local.get $v.45
    call $units/gen.pair
    local.set $p
    local.get $p
    local.set $p.1
    local.get $p.1
    local.set $p.2
    local.get $p.2
    ref.cast (ref $tuple)
    struct.get $tuple $slots
    i32.const 0
    array.get $slots
    call $unboxInt
    local.set $v.46
    local.get $v.46
    call $convInt
    local.set $v.47
    local.get $p.2
    ref.cast (ref $tuple)
    struct.get $tuple $slots
    i32.const 1
    array.get $slots
    local.set $v.48
    i32.const 0
    i32.const 1
    i32.const 70
    i32.const 1
    array.new_data $bytes $strings
    struct.new $string
    local.get $v.48
    call $concat
    local.set $v.49
    local.get $v.47
    local.get $v.49
    call $concat
    local.set $v.50
    i32.const 1
    ref.i31
    local.set $v.51
    local.get $v.50
    i32.const 0
    i32.const 1
    i32.const 71
    i32.const 1
    array.new_data $bytes $strings
    struct.new $string
    call $concat
    local.set $v.52
    local.get $v.51
    local.get $v.52
    call $putString
    local.set $v.53
    i32.const 0
    i32.const 0
    i32.const 3
    i32.const 72
    i32.const 3
    array.new_data $bytes $strings
    struct.new $string
    struct.new $exception
    local.set $bad
    local.get $bad
    local.get $p.2
    i32.const 0
    i32.const 115
    i32.const 75
    i32.const 115
    array.new_data $bytes $strings
    struct.new $string
    i32.const 0
    i32.const 35
    i32.const 190
    i32.const 35
    array.new_data $bytes $strings
    struct.new $string
    i32.const 9
    global.get $QTuple_Int_String_c1d595445c9f41f3
    call $raise
    unreachable
  )
  (func $_start (type 34)
    (local $t (ref null $raised))
    block $uncaught (result eqref)
      try_table (catch $error $uncaught)
        call $main
      end
      return
    end
    ref.cast (ref $raised)
    local.tee $t
    local.get $t
    struct.get $raised $desc
    ref.is_null
    if (result eqref)
      ref.null none
    else
      call $wasm/print.init
      global.get $noClosure
      local.get $t
      struct.get $raised $payload
      local.get $t
      struct.get $raised $desc
      call $wasm/print.show
    end
    call $uncaught
  )
  (func $descriptors (type 34)
    global.get $noClosure
    i64.const 1
    call $wasm/core.base
    global.set $quest_type_Int
    global.get $noClosure
    i64.const 2
    call $wasm/core.base
    global.set $quest_type_Real
    global.get $noClosure
    i64.const 3
    call $wasm/core.base
    global.set $quest_type_Bool
    global.get $noClosure
    i64.const 4
    call $wasm/core.base
    global.set $quest_type_Char
    global.get $noClosure
    i64.const 5
    call $wasm/core.base
    global.set $quest_type_String
    global.get $noClosure
    i64.const 6
    call $wasm/core.base
    global.set $quest_type_Ok
    global.get $noClosure
    i64.const 7
    call $wasm/core.base
    global.set $quest_type_Word
    global.get $noClosure
    i64.const 9
    call $wasm/core.base
    global.set $quest_type_EmptyTuple
    global.get $noClosure
    i64.const 17
    call $wasm/core.base
    global.set $quest_type_bound_vars
    global.get $noClosure
    i64.const 9
    i32.const 0
    i32.const 35
    i32.const 1
    i32.const 35
    array.new_data $bytes $strings
    struct.new $string
    i64.const 2
    i64.const 0
    call $wasm/core.newDesc
    global.set $QTuple_Int_String_c1d595445c9f41f3
    global.get $noClosure
    global.get $QTuple_Int_String_c1d595445c9f41f3
    i64.const 0
    global.get $quest_type_Int
    i32.const 0
    i32.const 5
    i32.const 36
    i32.const 5
    array.new_data $bytes $strings
    struct.new $string
    call $wasm/core.setPart
    drop
    global.get $noClosure
    global.get $QTuple_Int_String_c1d595445c9f41f3
    i64.const 1
    global.get $quest_type_String
    i32.const 0
    i32.const 6
    i32.const 41
    i32.const 6
    array.new_data $bytes $strings
    struct.new $string
    call $wasm/core.setPart
    drop
  )
  (func $pos.uniform (type 46) (param $closure (ref $clos)) (param $a0 eqref) (result eqref)
    local.get $closure
    local.get $a0
    call $unboxInt
    call $pos
    ref.i31
  )
  (func $nonEmpty.uniform (type 46) (param $closure (ref $clos)) (param $a0 eqref) (result eqref)
    local.get $closure
    local.get $a0
    call $nonEmpty
    ref.i31
  )
  (func $f.uniform (type 46) (param $closure (ref $clos)) (param $a0 eqref) (result eqref)
    local.get $closure
    local.get $a0
    call $unboxInt
    call $f
    call $boxInt
  )
  (func $qa_adapt.uniform (type 46) (param $closure (ref $clos)) (param $a0 eqref) (result eqref)
    local.get $closure
    local.get $a0
    call $qa_adapt
    ref.i31
  )
  (func $qa_adapt.uniform.1 (type 46) (param $closure (ref $clos)) (param $a0 eqref) (result eqref)
    local.get $closure
    local.get $a0
    call $qa_adapt.1
    ref.i31
  )
  (func $qa_adapt.uniform.2 (type 46) (param $closure (ref $clos)) (param $a0 eqref) (result eqref)
    local.get $closure
    local.get $a0
    call $unboxInt
    call $qa_adapt.3
    call $boxInt
  )
  (data $strings "!Tuple first: Int second: String endfirstsecond\0aabc\0ayesno\0a\0a\0ahihi\0aseven \0abad/Users/haahr/Dropbox/Paul/src/quest/.claude/worktrees/wasm-plan-opus/tests/self-hosted/wasm/polymorphism.quest:22:1Tuple first: Int second: String end")
)


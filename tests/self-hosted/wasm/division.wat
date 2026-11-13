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
  )
  (type (func (param eqref eqref) (result eqref)))
  (type (func (param eqref i32) (result eqref)))
  (type (func (param i64) (result eqref)))
  (type (func (param i32) (result eqref)))
  (type (func (param eqref eqref)))
  (type (func (param eqref)))
  (type (func (param eqref) (result i64)))
  (type (func (param eqref i32)))
  (type (func (param eqref i64) (result i32)))
  (type (func (param eqref i64 i32) (result eqref)))
  (type (func (param i64 i32) (result eqref)))
  (type (func (param eqref i64 i64) (result eqref)))
  (type (func (param eqref i64 eqref i64 i64) (result eqref)))
  (type (func (param eqref eqref) (result i32)))
  (type (func))
  (import "quest.runtime" "putString" (func $putString (type 16)))
  (import "quest.runtime" "putChar" (func $putChar (type 17)))
  (import "quest.runtime" "concat" (func $concat (type 16)))
  (import "quest.runtime" "convInt" (func $convInt (type 18)))
  (import "quest.runtime" "convBool" (func $convBool (type 19)))
  (import "quest.runtime" "convChar" (func $convChar (type 19)))
  (import "quest.runtime" "fail" (func $fail (type 20)))
  (import "quest.runtime" "uncaught" (func $uncaught (type 21)))
  (import "quest.runtime" "decimal" (func $decimal (type 18)))
  (import "quest.runtime" "hex" (func $hex (type 18)))
  (import "quest.runtime" "escaped" (func $escaped (type 17)))
  (import "quest.runtime" "boxInt" (func $boxInt (type 18)))
  (import "quest.runtime" "unboxInt" (func $unboxInt (type 22)))
  (import "quest.runtime" "fatal" (func $fatal (type 23)))
  (import "quest.runtime" "stringGetChar" (func $stringGetChar (type 24)))
  (import "quest.runtime" "stringSetChar" (func $stringSetChar (type 25)))
  (import "quest.runtime" "stringNew" (func $stringNew (type 26)))
  (import "quest.runtime" "stringGetSub" (func $stringGetSub (type 27)))
  (import "quest.runtime" "stringSetSub" (func $stringSetSub (type 28)))
  (import "quest.runtime" "stringEqual" (func $stringEqual (type 29)))
  (import "quest.runtime" "error" (tag $error (type 21)))
  (global $noClosure (ref $clos) i32.const 0 struct.new $clos)
  (export "_start" (func $_start))
  (func $main (type 30)
    (local $v eqref)
    (local $v.1 eqref)
    (local $v.2 eqref)
    (local $v.3 eqref)
    (local $v.4 eqref)
    (local $v.5 eqref)
    (local $v.6 eqref)
    (local $v.7 eqref)
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
    (local $v.23 eqref)
    (local $v.24 eqref)
    (local $v.25 eqref)
    (local $v.26 eqref)
    (local $v.27 eqref)
    (local $v.28 eqref)
    (local $v.29 eqref)
    (local $v.30 eqref)
    (local $v.31 eqref)
    (local $v.32 eqref)
    (local $v.33 eqref)
    (local $v.34 eqref)
    (local $v.35 eqref)
    (local $v.36 eqref)
    (local $v.37 eqref)
    (local $v.38 eqref)
    (local $v.39 eqref)
    (local $v.40 eqref)
    (local $v.41 eqref)
    (local $v.42 eqref)
    (local $v.43 eqref)
    (local $v.44 eqref)
    (local $v.45 eqref)
    (local $v.46 eqref)
    (local $v.47 eqref)
    (local $v.48 eqref)
    (local $v.49 eqref)
    (local $v.50 eqref)
    (local $v.51 eqref)
    (local $v.52 eqref)
    (local $v.53 eqref)
    (local $v.54 eqref)
    (local $v.55 eqref)
    (local $v.56 eqref)
    (local $v.57 eqref)
    (local $v.58 eqref)
    (local $v.59 eqref)
    (local $v.60 eqref)
    (local $v.61 eqref)
    (local $v.62 eqref)
    (local $v.63 eqref)
    (local $v.64 eqref)
    (local $v.65 eqref)
    (local $v.66 eqref)
    (local $v.67 eqref)
    (local $v.68 eqref)
    (local $v.69 eqref)
    (local $v.70 eqref)
    (local $v.71 eqref)
    (local $v.72 eqref)
    (local $v.73 eqref)
    (local $v.74 eqref)
    (local $v.75 eqref)
    (local $v.76 eqref)
    (local $v.77 eqref)
    (local $v.78 eqref)
    (local $v.79 eqref)
    (local $v.80 i64)
    (local $v.81 eqref)
    (local $v.82 i64)
    (local $v.83 eqref)
    (local $v.84 eqref)
    (local $v.85 eqref)
    (local $v.86 eqref)
    (local $v.87 eqref)
    (local $v.88 eqref)
    (local $v.89 eqref)
    (local $v.90 eqref)
    (local $v.91 eqref)
    (local $v.92 eqref)
    (local $s eqref)
    (local $v.93 eqref)
    (local $v.94 eqref)
    (local $v.95 eqref)
    i64.const 7
    call $convInt
    local.set $v
    i64.const 2
    call $convInt
    local.set $v.1
    i64.const 3
    call $convInt
    local.set $v.2
    i64.const 1
    call $convInt
    local.set $v.3
    i32.const 0
    i32.const 12
    i32.const 0
    i32.const 12
    array.new_data $bytes $strings
    struct.new $string
    local.get $v.3
    call $concat
    local.set $v.4
    local.get $v.2
    local.get $v.4
    call $concat
    local.set $v.5
    i32.const 0
    i32.const 3
    i32.const 12
    i32.const 3
    array.new_data $bytes $strings
    struct.new $string
    local.get $v.5
    call $concat
    local.set $v.6
    local.get $v.1
    local.get $v.6
    call $concat
    local.set $v.7
    i32.const 0
    i32.const 3
    i32.const 15
    i32.const 3
    array.new_data $bytes $strings
    struct.new $string
    local.get $v.7
    call $concat
    local.set $v.8
    local.get $v
    local.get $v.8
    call $concat
    local.set $v.9
    i32.const 1
    ref.i31
    local.set $v.10
    local.get $v.9
    i32.const 0
    i32.const 1
    i32.const 18
    i32.const 1
    array.new_data $bytes $strings
    struct.new $string
    call $concat
    local.set $v.11
    local.get $v.10
    local.get $v.11
    call $putString
    local.set $v.12
    i64.const -7
    call $convInt
    local.set $v.13
    i64.const 2
    call $convInt
    local.set $v.14
    i64.const -3
    call $convInt
    local.set $v.15
    i64.const -1
    call $convInt
    local.set $v.16
    i32.const 0
    i32.const 12
    i32.const 19
    i32.const 12
    array.new_data $bytes $strings
    struct.new $string
    local.get $v.16
    call $concat
    local.set $v.17
    local.get $v.15
    local.get $v.17
    call $concat
    local.set $v.18
    i32.const 0
    i32.const 3
    i32.const 31
    i32.const 3
    array.new_data $bytes $strings
    struct.new $string
    local.get $v.18
    call $concat
    local.set $v.19
    local.get $v.14
    local.get $v.19
    call $concat
    local.set $v.20
    i32.const 0
    i32.const 3
    i32.const 34
    i32.const 3
    array.new_data $bytes $strings
    struct.new $string
    local.get $v.20
    call $concat
    local.set $v.21
    local.get $v.13
    local.get $v.21
    call $concat
    local.set $v.22
    i32.const 1
    ref.i31
    local.set $v.23
    local.get $v.22
    i32.const 0
    i32.const 1
    i32.const 37
    i32.const 1
    array.new_data $bytes $strings
    struct.new $string
    call $concat
    local.set $v.24
    local.get $v.23
    local.get $v.24
    call $putString
    local.set $v.25
    i64.const 7
    call $convInt
    local.set $v.26
    i64.const -2
    call $convInt
    local.set $v.27
    i64.const -3
    call $convInt
    local.set $v.28
    i64.const 1
    call $convInt
    local.set $v.29
    i32.const 0
    i32.const 12
    i32.const 38
    i32.const 12
    array.new_data $bytes $strings
    struct.new $string
    local.get $v.29
    call $concat
    local.set $v.30
    local.get $v.28
    local.get $v.30
    call $concat
    local.set $v.31
    i32.const 0
    i32.const 3
    i32.const 50
    i32.const 3
    array.new_data $bytes $strings
    struct.new $string
    local.get $v.31
    call $concat
    local.set $v.32
    local.get $v.27
    local.get $v.32
    call $concat
    local.set $v.33
    i32.const 0
    i32.const 3
    i32.const 53
    i32.const 3
    array.new_data $bytes $strings
    struct.new $string
    local.get $v.33
    call $concat
    local.set $v.34
    local.get $v.26
    local.get $v.34
    call $concat
    local.set $v.35
    i32.const 1
    ref.i31
    local.set $v.36
    local.get $v.35
    i32.const 0
    i32.const 1
    i32.const 56
    i32.const 1
    array.new_data $bytes $strings
    struct.new $string
    call $concat
    local.set $v.37
    local.get $v.36
    local.get $v.37
    call $putString
    local.set $v.38
    i64.const -9223372036854775808
    call $convInt
    local.set $v.39
    i64.const -1
    call $convInt
    local.set $v.40
    i64.const -9223372036854775808
    call $convInt
    local.set $v.41
    i64.const 0
    call $convInt
    local.set $v.42
    i32.const 0
    i32.const 12
    i32.const 57
    i32.const 12
    array.new_data $bytes $strings
    struct.new $string
    local.get $v.42
    call $concat
    local.set $v.43
    local.get $v.41
    local.get $v.43
    call $concat
    local.set $v.44
    i32.const 0
    i32.const 3
    i32.const 69
    i32.const 3
    array.new_data $bytes $strings
    struct.new $string
    local.get $v.44
    call $concat
    local.set $v.45
    local.get $v.40
    local.get $v.45
    call $concat
    local.set $v.46
    i32.const 0
    i32.const 3
    i32.const 72
    i32.const 3
    array.new_data $bytes $strings
    struct.new $string
    local.get $v.46
    call $concat
    local.set $v.47
    local.get $v.39
    local.get $v.47
    call $concat
    local.set $v.48
    i32.const 1
    ref.i31
    local.set $v.49
    local.get $v.48
    i32.const 0
    i32.const 1
    i32.const 75
    i32.const 1
    array.new_data $bytes $strings
    struct.new $string
    call $concat
    local.set $v.50
    local.get $v.49
    local.get $v.50
    call $putString
    local.set $v.51
    i64.const -9223372036854775808
    call $convInt
    local.set $v.52
    i64.const 1
    call $convInt
    local.set $v.53
    i64.const -9223372036854775808
    call $convInt
    local.set $v.54
    i64.const 0
    call $convInt
    local.set $v.55
    i32.const 0
    i32.const 12
    i32.const 76
    i32.const 12
    array.new_data $bytes $strings
    struct.new $string
    local.get $v.55
    call $concat
    local.set $v.56
    local.get $v.54
    local.get $v.56
    call $concat
    local.set $v.57
    i32.const 0
    i32.const 3
    i32.const 88
    i32.const 3
    array.new_data $bytes $strings
    struct.new $string
    local.get $v.57
    call $concat
    local.set $v.58
    local.get $v.53
    local.get $v.58
    call $concat
    local.set $v.59
    i32.const 0
    i32.const 3
    i32.const 91
    i32.const 3
    array.new_data $bytes $strings
    struct.new $string
    local.get $v.59
    call $concat
    local.set $v.60
    local.get $v.52
    local.get $v.60
    call $concat
    local.set $v.61
    i32.const 1
    ref.i31
    local.set $v.62
    local.get $v.61
    i32.const 0
    i32.const 1
    i32.const 94
    i32.const 1
    array.new_data $bytes $strings
    struct.new $string
    call $concat
    local.set $v.63
    local.get $v.62
    local.get $v.63
    call $putString
    local.set $v.64
    i64.const 0
    call $convInt
    local.set $v.65
    i64.const -1
    call $convInt
    local.set $v.66
    i64.const 0
    call $convInt
    local.set $v.67
    i64.const 0
    call $convInt
    local.set $v.68
    i32.const 0
    i32.const 12
    i32.const 95
    i32.const 12
    array.new_data $bytes $strings
    struct.new $string
    local.get $v.68
    call $concat
    local.set $v.69
    local.get $v.67
    local.get $v.69
    call $concat
    local.set $v.70
    i32.const 0
    i32.const 3
    i32.const 107
    i32.const 3
    array.new_data $bytes $strings
    struct.new $string
    local.get $v.70
    call $concat
    local.set $v.71
    local.get $v.66
    local.get $v.71
    call $concat
    local.set $v.72
    i32.const 0
    i32.const 3
    i32.const 110
    i32.const 3
    array.new_data $bytes $strings
    struct.new $string
    local.get $v.72
    call $concat
    local.set $v.73
    local.get $v.65
    local.get $v.73
    call $concat
    local.set $v.74
    i32.const 1
    ref.i31
    local.set $v.75
    local.get $v.74
    i32.const 0
    i32.const 1
    i32.const 113
    i32.const 1
    array.new_data $bytes $strings
    struct.new $string
    call $concat
    local.set $v.76
    local.get $v.75
    local.get $v.76
    call $putString
    local.set $v.77
    i64.const 1
    call $convInt
    local.set $v.78
    i64.const 0
    call $convInt
    local.set $v.79
    i64.const 0
    i64.eqz
    if
      i32.const 0
      i32.const 9
      i32.const 114
      i32.const 9
      array.new_data $bytes $strings
      struct.new $string
      i32.const 0
      i32.const 111
      i32.const 123
      i32.const 111
      array.new_data $bytes $strings
      struct.new $string
      call $fail
      unreachable
    end
    i64.const 0
    i64.const -1
    i64.eq
    if (result i64)
      i64.const 0
      i64.const 1
      i64.sub
    else
      i64.const 1
      i64.const 0
      i64.div_s
    end
    local.set $v.80
    local.get $v.80
    call $convInt
    local.set $v.81
    i64.const 0
    i64.eqz
    if
      i32.const 0
      i32.const 9
      i32.const 234
      i32.const 9
      array.new_data $bytes $strings
      struct.new $string
      i32.const 0
      i32.const 111
      i32.const 243
      i32.const 111
      array.new_data $bytes $strings
      struct.new $string
      call $fail
      unreachable
    end
    i64.const 0
    i64.const -1
    i64.eq
    if (result i64)
      i64.const 0
    else
      i64.const 1
      i64.const 0
      i64.rem_s
    end
    local.set $v.82
    local.get $v.82
    call $convInt
    local.set $v.83
    i32.const 0
    i32.const 12
    i32.const 354
    i32.const 12
    array.new_data $bytes $strings
    struct.new $string
    local.get $v.83
    call $concat
    local.set $v.84
    local.get $v.81
    local.get $v.84
    call $concat
    local.set $v.85
    i32.const 0
    i32.const 3
    i32.const 366
    i32.const 3
    array.new_data $bytes $strings
    struct.new $string
    local.get $v.85
    call $concat
    local.set $v.86
    local.get $v.79
    local.get $v.86
    call $concat
    local.set $v.87
    i32.const 0
    i32.const 3
    i32.const 369
    i32.const 3
    array.new_data $bytes $strings
    struct.new $string
    local.get $v.87
    call $concat
    local.set $v.88
    local.get $v.78
    local.get $v.88
    call $concat
    local.set $v.89
    i32.const 1
    ref.i31
    local.set $v.90
    local.get $v.89
    i32.const 0
    i32.const 1
    i32.const 372
    i32.const 1
    array.new_data $bytes $strings
    struct.new $string
    call $concat
    local.set $v.91
    local.get $v.90
    local.get $v.91
    call $putString
    local.set $v.92
    i32.const 0
    i32.const 11
    i32.const 373
    i32.const 11
    array.new_data $bytes $strings
    struct.new $string
    local.set $s
    i32.const 1
    ref.i31
    local.set $v.93
    local.get $s
    i32.const 0
    i32.const 1
    i32.const 384
    i32.const 1
    array.new_data $bytes $strings
    struct.new $string
    call $concat
    local.set $v.94
    local.get $v.93
    local.get $v.94
    call $putString
    local.set $v.95
  )
  (func $_start (type 30)
    block $uncaught (result eqref)
      try_table (catch $error $uncaught)
        call $main
      end
      return
    end
    call $uncaught
  )
  (data $strings ", remainder  =  / \0a, remainder  =  / \0a, remainder  =  / \0a, remainder  =  / \0a, remainder  =  / \0a, remainder  =  / \0aint.error/Users/haahr/Dropbox/Paul/src/quest/.claude/worktrees/wasm-plan-opus/tests/self-hosted/wasm/division.quest:6:94int.error/Users/haahr/Dropbox/Paul/src/quest/.claude/worktrees/wasm-plan-opus/tests/self-hosted/wasm/division.quest:7:17, remainder  =  / \0anot reached\0a")
)


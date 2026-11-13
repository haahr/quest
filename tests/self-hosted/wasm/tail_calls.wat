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
  (type (func (param (ref $clos) i64 i64) (result i64)))
  (type (func (param (ref $clos) i64) (result i32)))
  (type (func (param (ref $clos) eqref eqref) (result eqref)))
  (type $closU2 (sub $clos (struct (field $hash (mut i32)) (field $uniform (ref 33)))))
  (type (sub $closU2 (struct (field $hash (mut i32)) (field $uniform (ref 33)) (field $native (ref 31)))))
  (type $sum.closure (sub final 35 (struct (field $hash (mut i32)) (field $uniform (ref 33)) (field $native (ref 31)))))
  (type (func (param (ref $clos) eqref) (result eqref)))
  (type $closU1 (sub $clos (struct (field $hash (mut i32)) (field $uniform (ref 37)))))
  (type (sub $closU1 (struct (field $hash (mut i32)) (field $uniform (ref 37)) (field $native (ref 32)))))
  (type $isEven.closure (sub final 39 (struct (field $hash (mut i32)) (field $uniform (ref 37)) (field $native (ref 32)))))
  (type $isOdd.closure (sub final 39 (struct (field $hash (mut i32)) (field $uniform (ref 37)) (field $native (ref 32)))))
  (type $count.closure (sub final 35 (struct (field $hash (mut i32)) (field $uniform (ref 33)) (field $native (ref 31)))))
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
  (global $sum.static (ref $sum.closure) i32.const 0 ref.func $sum.uniform ref.func $sum struct.new $sum.closure)
  (global $sum.1 (mut eqref) ref.null none)
  (global $isEven.static (ref $isEven.closure) i32.const 0 ref.func $isEven.uniform ref.func $isEven struct.new $isEven.closure)
  (global $isEven.1 (mut eqref) ref.null none)
  (global $isOdd.static (ref $isOdd.closure) i32.const 0 ref.func $isOdd.uniform ref.func $isOdd struct.new $isOdd.closure)
  (global $isOdd.1 (mut eqref) ref.null none)
  (global $count.static (ref $count.closure) i32.const 0 ref.func $count.uniform ref.func $count struct.new $count.closure)
  (global $count.1 (mut eqref) ref.null none)
  (export "_start" (func $_start))
  (elem declare func $sum.uniform $sum $isEven.uniform $isEven $isOdd.uniform $isOdd $count.uniform $count)
  (func $sum (type 31) (param $closure (ref $clos)) (param $n i64) (param $acc i64) (result i64)
    (local $v i32)
    (local $v.1 i64)
    (local $v.2 i64)
    local.get $n
    i64.const 0
    i64.eq
    local.set $v
    local.get $v
    if
      local.get $acc
      return
    else
      local.get $n
      i64.const 1
      i64.sub
      local.set $v.1
      local.get $acc
      local.get $n
      i64.add
      local.set $v.2
      global.get $noClosure
      local.get $v.1
      local.get $v.2
      return_call $sum
    end
    unreachable
  )
  (func $isEven (type 32) (param $closure (ref $clos)) (param $n i64) (result i32)
    (local $v i32)
    (local $v.1 i64)
    local.get $n
    i64.const 0
    i64.eq
    local.set $v
    local.get $v
    if
      i32.const 1
      return
    else
      local.get $n
      i64.const 1
      i64.sub
      local.set $v.1
      global.get $noClosure
      local.get $v.1
      return_call $isOdd
    end
    unreachable
  )
  (func $isOdd (type 32) (param $closure (ref $clos)) (param $n i64) (result i32)
    (local $v i32)
    (local $v.1 i64)
    local.get $n
    i64.const 0
    i64.eq
    local.set $v
    local.get $v
    if
      i32.const 0
      return
    else
      local.get $n
      i64.const 1
      i64.sub
      local.set $v.1
      global.get $noClosure
      local.get $v.1
      return_call $isEven
    end
    unreachable
  )
  (func $count (type 31) (param $closure (ref $clos)) (param $n i64) (param $acc i64) (result i64)
    (local $v i64)
    (local $v.1 i32)
    (local $step i64)
    (local $v.2 i32)
    (local $v.3 i64)
    (local $v.4 i64)
    block $k4.after
      block $k4 (result i64)
        i64.const 3
        i64.eqz
        if
          i32.const 0
          i32.const 9
          i32.const 0
          i32.const 9
          array.new_data $bytes $strings
          struct.new $string
          i32.const 0
          i32.const 114
          i32.const 9
          i32.const 114
          array.new_data $bytes $strings
          struct.new $string
          call $fail
          unreachable
        end
        i64.const 3
        i64.const -1
        i64.eq
        if (result i64)
          i64.const 0
        else
          local.get $n
          i64.const 3
          i64.rem_s
        end
        local.set $v
        local.get $v
        i64.const 0
        i64.eq
        local.set $v.1
        local.get $v.1
        if
          i64.const 2
          br $k4
        else
          i64.const 1
          br $k4
        end
        br $k4.after
      end
      local.set $step
      local.get $n
      i64.const 0
      i64.le_s
      local.set $v.2
      local.get $v.2
      if
        local.get $acc
        return
      else
        local.get $n
        local.get $step
        i64.sub
        local.set $v.3
        local.get $acc
        i64.const 1
        i64.add
        local.set $v.4
        global.get $noClosure
        local.get $v.3
        local.get $v.4
        return_call $count
      end
    end
    unreachable
  )
  (func $main (type 30)
    (local $v i64)
    (local $v.1 eqref)
    (local $v.2 eqref)
    (local $v.3 eqref)
    (local $v.4 eqref)
    (local $v.5 i64)
    (local $v.6 eqref)
    (local $v.7 eqref)
    (local $v.8 eqref)
    (local $v.9 eqref)
    (local $v.10 i32)
    (local $v.11 eqref)
    (local $v.12 eqref)
    (local $v.13 eqref)
    (local $v.14 eqref)
    (local $v.15 i32)
    (local $v.16 eqref)
    (local $v.17 eqref)
    (local $v.18 eqref)
    (local $v.19 eqref)
    (local $v.20 i64)
    (local $v.21 eqref)
    (local $v.22 eqref)
    (local $v.23 eqref)
    (local $v.24 eqref)
    (local $v.25 i64)
    (local $v.26 eqref)
    (local $v.27 eqref)
    (local $v.28 eqref)
    (local $v.29 eqref)
    global.get $sum.static
    global.set $sum.1
    global.get $isEven.static
    global.set $isEven.1
    global.get $isOdd.static
    global.set $isOdd.1
    global.get $count.static
    global.set $count.1
    global.get $noClosure
    i64.const 1000000
    i64.const 0
    call $sum
    local.set $v
    local.get $v
    call $convInt
    local.set $v.1
    i32.const 1
    ref.i31
    local.set $v.2
    local.get $v.1
    i32.const 0
    i32.const 1
    i32.const 123
    i32.const 1
    array.new_data $bytes $strings
    struct.new $string
    call $concat
    local.set $v.3
    local.get $v.2
    local.get $v.3
    call $putString
    local.set $v.4
    global.get $noClosure
    i64.const 10
    i64.const 0
    call $sum
    local.set $v.5
    local.get $v.5
    call $convInt
    local.set $v.6
    i32.const 1
    ref.i31
    local.set $v.7
    local.get $v.6
    i32.const 0
    i32.const 1
    i32.const 124
    i32.const 1
    array.new_data $bytes $strings
    struct.new $string
    call $concat
    local.set $v.8
    local.get $v.7
    local.get $v.8
    call $putString
    local.set $v.9
    global.get $noClosure
    i64.const 1000001
    call $isEven
    local.set $v.10
    local.get $v.10
    call $convBool
    local.set $v.11
    i32.const 1
    ref.i31
    local.set $v.12
    local.get $v.11
    i32.const 0
    i32.const 1
    i32.const 125
    i32.const 1
    array.new_data $bytes $strings
    struct.new $string
    call $concat
    local.set $v.13
    local.get $v.12
    local.get $v.13
    call $putString
    local.set $v.14
    global.get $noClosure
    i64.const 7
    call $isOdd
    local.set $v.15
    local.get $v.15
    call $convBool
    local.set $v.16
    i32.const 1
    ref.i31
    local.set $v.17
    local.get $v.16
    i32.const 0
    i32.const 1
    i32.const 126
    i32.const 1
    array.new_data $bytes $strings
    struct.new $string
    call $concat
    local.set $v.18
    local.get $v.17
    local.get $v.18
    call $putString
    local.set $v.19
    global.get $noClosure
    i64.const 3000000
    i64.const 0
    call $count
    local.set $v.20
    local.get $v.20
    call $convInt
    local.set $v.21
    i32.const 1
    ref.i31
    local.set $v.22
    local.get $v.21
    i32.const 0
    i32.const 1
    i32.const 127
    i32.const 1
    array.new_data $bytes $strings
    struct.new $string
    call $concat
    local.set $v.23
    local.get $v.22
    local.get $v.23
    call $putString
    local.set $v.24
    global.get $noClosure
    i64.const 10
    i64.const 0
    call $count
    local.set $v.25
    local.get $v.25
    call $convInt
    local.set $v.26
    i32.const 1
    ref.i31
    local.set $v.27
    local.get $v.26
    i32.const 0
    i32.const 1
    i32.const 128
    i32.const 1
    array.new_data $bytes $strings
    struct.new $string
    call $concat
    local.set $v.28
    local.get $v.27
    local.get $v.28
    call $putString
    local.set $v.29
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
  (func $sum.uniform (type 33) (param $closure (ref $clos)) (param $a0 eqref) (param $a1 eqref) (result eqref)
    local.get $closure
    local.get $a0
    call $unboxInt
    local.get $a1
    call $unboxInt
    call $sum
    call $boxInt
  )
  (func $isEven.uniform (type 37) (param $closure (ref $clos)) (param $a0 eqref) (result eqref)
    local.get $closure
    local.get $a0
    call $unboxInt
    call $isEven
    ref.i31
  )
  (func $isOdd.uniform (type 37) (param $closure (ref $clos)) (param $a0 eqref) (result eqref)
    local.get $closure
    local.get $a0
    call $unboxInt
    call $isOdd
    ref.i31
  )
  (func $count.uniform (type 33) (param $closure (ref $clos)) (param $a0 eqref) (param $a1 eqref) (result eqref)
    local.get $closure
    local.get $a0
    call $unboxInt
    local.get $a1
    call $unboxInt
    call $count
    call $boxInt
  )
  (data $strings "int.error/Users/haahr/Dropbox/Paul/src/quest/.claude/worktrees/wasm-plan-opus/tests/self-hosted/wasm/tail_calls.quest:11:24\0a\0a\0a\0a\0a\0a")
)


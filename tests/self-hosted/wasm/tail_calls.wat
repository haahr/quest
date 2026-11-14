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
  (type (func (param i64) (result i64)))
  (type (func (param i64 i64)))
  (type (func (param i64)))
  (type (func (param i64 i64) (result eqref)))
  (type (func (param eqref i64)))
  (type (func (param i64 i64) (result i64)))
  (type (func (param i64 i64 i64) (result i64)))
  (type (func (param i64 i64 i64 i64 i64 i64 i64 i64 i64) (result i64)))
  (type (func (param i64 i64 i64 i64) (result i64)))
  (type (func (param i64 i64 i64 i64 i64) (result i64)))
  (type (func (param i64 i64 i64 i64 i64 i64) (result i64)))
  (type (func (param eqref)))
  (type (func))
  (type (func (param (ref $clos) eqref eqref) (result eqref)))
  (type (func (param (ref $clos) i32) (result eqref)))
  (type (func (param (ref $clos) i64 i64) (result i64)))
  (type (func (param (ref $clos) i64) (result i32)))
  (type $closU2 (sub $clos (struct (field $hash (mut i32)) (field $uniform (ref 46)))))
  (type (sub $closU2 (struct (field $hash (mut i32)) (field $uniform (ref 46)) (field $native (ref 48)))))
  (type $sum.closure (sub final 51 (struct (field $hash (mut i32)) (field $uniform (ref 46)) (field $native (ref 48)))))
  (type (func (param (ref $clos) eqref) (result eqref)))
  (type $closU1 (sub $clos (struct (field $hash (mut i32)) (field $uniform (ref 53)))))
  (type (sub $closU1 (struct (field $hash (mut i32)) (field $uniform (ref 53)) (field $native (ref 49)))))
  (type $isEven.closure (sub final 55 (struct (field $hash (mut i32)) (field $uniform (ref 53)) (field $native (ref 49)))))
  (type $isOdd.closure (sub final 55 (struct (field $hash (mut i32)) (field $uniform (ref 53)) (field $native (ref 49)))))
  (type $count.closure (sub final 51 (struct (field $hash (mut i32)) (field $uniform (ref 46)) (field $native (ref 48)))))
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
  (import "quest.runtime" "exception:value.error" (global $value.error (ref $exception)))
  (import "quest.runtime" "exception:readline.error" (global $readline.error (ref $exception)))
  (import "writer" "record.payload" (global (mut eqref)))
  (import "writer" "record.dict" (global (mut eqref)))
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
  (import "quest.runtime" "memLoad8" (func $memLoad8 (type 33)))
  (import "quest.runtime" "memStore8" (func $memStore8 (type 34)))
  (import "quest.runtime" "memLoad32" (func $memLoad32 (type 33)))
  (import "quest.runtime" "memStore32" (func $memStore32 (type 34)))
  (import "quest.runtime" "memLoad64" (func $memLoad64 (type 33)))
  (import "quest.runtime" "memStore64" (func $memStore64 (type 34)))
  (import "quest.runtime" "memEnsure" (func $memEnsure (type 35)))
  (import "quest.runtime" "memToString" (func $memToString (type 36)))
  (import "quest.runtime" "stringToMem" (func $stringToMem (type 37)))
  (import "quest.runtime" "wasi:args_sizes_get" (func $wasi:args_sizes_get (type 38)))
  (import "quest.runtime" "wasi:args_get" (func $wasi:args_get (type 38)))
  (import "quest.runtime" "wasi:environ_sizes_get" (func $wasi:environ_sizes_get (type 38)))
  (import "quest.runtime" "wasi:environ_get" (func $wasi:environ_get (type 38)))
  (import "quest.runtime" "wasi:fd_prestat_get" (func $wasi:fd_prestat_get (type 38)))
  (import "quest.runtime" "wasi:fd_prestat_dir_name" (func $wasi:fd_prestat_dir_name (type 39)))
  (import "quest.runtime" "wasi:path_open" (func $wasi:path_open (type 40)))
  (import "quest.runtime" "wasi:fd_read" (func $wasi:fd_read (type 41)))
  (import "quest.runtime" "wasi:fd_close" (func $wasi:fd_close (type 33)))
  (import "quest.runtime" "wasi:path_filestat_get" (func $wasi:path_filestat_get (type 42)))
  (import "quest.runtime" "wasi:path_create_directory" (func $wasi:path_create_directory (type 39)))
  (import "quest.runtime" "wasi:path_unlink_file" (func $wasi:path_unlink_file (type 39)))
  (import "quest.runtime" "wasi:path_remove_directory" (func $wasi:path_remove_directory (type 39)))
  (import "quest.runtime" "wasi:path_rename" (func $wasi:path_rename (type 43)))
  (import "quest.runtime" "wasi:fd_readdir" (func $wasi:fd_readdir (type 42)))
  (import "quest.runtime" "error" (tag $error (type 44)))
  (import "writer" "init" (func $writer.init (type 45)))
  (import "conv" "init" (func $conv.init (type 45)))
  (import "wasm/print" "init" (func $wasm/print.init (type 45)))
  (import "wasm/print" "show" (func $wasm/print.show (type 46)))
  (import "conv" "bool" (func $conv.bool (type 47)))
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
  (func $sum (type 48) (param $closure (ref $clos)) (param $n i64) (param $acc i64) (result i64)
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
  (func $isEven (type 49) (param $closure (ref $clos)) (param $n i64) (result i32)
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
  (func $isOdd (type 49) (param $closure (ref $clos)) (param $n i64) (result i32)
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
  (func $count (type 48) (param $closure (ref $clos)) (param $n i64) (param $acc i64) (result i64)
    (local $v i64)
    (local $v.1 i32)
    (local $v.4 i64)
    block $k4.after
      block $k4 (result i64)
        i64.const 3
        i64.eqz
        if
          global.get $int.error
          i32.const 0
          ref.i31
          i32.const 0
          i32.const 114
          i32.const 0
          i32.const 114
          array.new_data $bytes $strings
          struct.new $string
          i32.const 0
          i32.const 0
          i32.const 114
          i32.const 0
          array.new_data $bytes $strings
          struct.new $string
          i32.const 0
          ref.null none
          call $raise
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
      local.set $v
      local.get $n
      i64.const 0
      i64.le_s
      local.set $v.1
      local.get $v.1
      if
        local.get $acc
        return
      else
        local.get $n
        local.get $v
        i64.sub
        local.set $v
        local.get $acc
        i64.const 1
        i64.add
        local.set $v.4
        global.get $noClosure
        local.get $v
        local.get $v.4
        return_call $count
      end
    end
    unreachable
  )
  (func $main (type 45)
    (local $v i64)
    (local $v.1 eqref)
    (local $v.2 eqref)
    (local $v.10 i32)
    call $writer.init
    call $conv.init
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
    i32.const 114
    i32.const 1
    array.new_data $bytes $strings
    struct.new $string
    call $concat
    local.set $v.1
    local.get $v.2
    local.get $v.1
    call $putString
    local.set $v.1
    global.get $noClosure
    i64.const 10
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
    i32.const 115
    i32.const 1
    array.new_data $bytes $strings
    struct.new $string
    call $concat
    local.set $v.1
    local.get $v.2
    local.get $v.1
    call $putString
    local.set $v.1
    global.get $noClosure
    i64.const 1000001
    call $isEven
    local.set $v.10
    global.get $noClosure
    local.get $v.10
    call $conv.bool
    local.set $v.1
    i32.const 1
    ref.i31
    local.set $v.2
    local.get $v.1
    i32.const 0
    i32.const 1
    i32.const 116
    i32.const 1
    array.new_data $bytes $strings
    struct.new $string
    call $concat
    local.set $v.1
    local.get $v.2
    local.get $v.1
    call $putString
    local.set $v.1
    global.get $noClosure
    i64.const 7
    call $isOdd
    local.set $v.10
    global.get $noClosure
    local.get $v.10
    call $conv.bool
    local.set $v.1
    i32.const 1
    ref.i31
    local.set $v.2
    local.get $v.1
    i32.const 0
    i32.const 1
    i32.const 117
    i32.const 1
    array.new_data $bytes $strings
    struct.new $string
    call $concat
    local.set $v.1
    local.get $v.2
    local.get $v.1
    call $putString
    local.set $v.1
    global.get $noClosure
    i64.const 3000000
    i64.const 0
    call $count
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
    i32.const 118
    i32.const 1
    array.new_data $bytes $strings
    struct.new $string
    call $concat
    local.set $v.1
    local.get $v.2
    local.get $v.1
    call $putString
    local.set $v.1
    global.get $noClosure
    i64.const 10
    i64.const 0
    call $count
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
    i32.const 119
    i32.const 1
    array.new_data $bytes $strings
    struct.new $string
    call $concat
    local.set $v.1
    local.get $v.2
    local.get $v.1
    call $putString
    local.set $v.1
  )
  (func $_start (type 45)
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
  (func $sum.uniform (type 46) (param $closure (ref $clos)) (param $a0 eqref) (param $a1 eqref) (result eqref)
    local.get $closure
    local.get $a0
    call $unboxInt
    local.get $a1
    call $unboxInt
    call $sum
    call $boxInt
  )
  (func $isEven.uniform (type 53) (param $closure (ref $clos)) (param $a0 eqref) (result eqref)
    local.get $closure
    local.get $a0
    call $unboxInt
    call $isEven
    ref.i31
  )
  (func $isOdd.uniform (type 53) (param $closure (ref $clos)) (param $a0 eqref) (result eqref)
    local.get $closure
    local.get $a0
    call $unboxInt
    call $isOdd
    ref.i31
  )
  (func $count.uniform (type 46) (param $closure (ref $clos)) (param $a0 eqref) (param $a1 eqref) (result eqref)
    local.get $closure
    local.get $a0
    call $unboxInt
    local.get $a1
    call $unboxInt
    call $count
    call $boxInt
  )
  (data $strings "/Users/haahr/Dropbox/Paul/src/quest/.claude/worktrees/wasm-plan-opus/tests/self-hosted/wasm/tail_calls.quest:11:24\0a\0a\0a\0a\0a\0a")
)


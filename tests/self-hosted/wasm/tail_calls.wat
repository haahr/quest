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
    (type $proxy (sub final $tupleLike (struct (field $hash (mut i32)) (field $state eqref))))
    (type $string (sub final $obj (struct (field $hash (mut i32)) (field $length i32) (field $bytes (ref $bytes)))))
    (type $array (sub final $obj (struct (field $hash (mut i32)) (field $elems (ref $slots)))))
    (type $varBox (struct (field $tag i32) (field $payload eqref)))
    (type $clos (sub $obj (struct (field $hash (mut i32)))))
    (type $auto (sub final $obj (struct (field $hash (mut i32)) (field $desc eqref) (field $payload eqref))))
    (type $record (sub final $obj (struct (field $hash (mut i32)) (field $layout eqref) (field $slots (ref $slots)))))
    (type $dict (struct (field $indices (ref $i32s)) (field $stored eqref)))
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
  (type (func (param i32)))
  (type (func (result eqref)))
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
  (type (func (param (ref $clos) eqref) (result eqref)))
  (type (func (param (ref $clos) eqref) (result i64)))
  (type (func (param (ref $clos) eqref i64) (result eqref)))
  (type (func (param (ref $clos) i32) (result eqref)))
  (type (func (param (ref $clos)) (result eqref)))
  (type (func (param (ref $clos) i64 i64) (result i64)))
  (type (func (param (ref $clos) i64) (result i32)))
  (type $closU2 (sub $clos (struct (field $hash (mut i32)) (field $uniform (ref 50)))))
  (type (sub $closU2 (struct (field $hash (mut i32)) (field $uniform (ref 50)) (field $native (ref 56)))))
  (type $sum.closure (sub final 59 (struct (field $hash (mut i32)) (field $uniform (ref 50)) (field $native (ref 56)))))
  (type $closU1 (sub $clos (struct (field $hash (mut i32)) (field $uniform (ref 51)))))
  (type (sub $closU1 (struct (field $hash (mut i32)) (field $uniform (ref 51)) (field $native (ref 57)))))
  (type $isEven.closure (sub final 62 (struct (field $hash (mut i32)) (field $uniform (ref 51)) (field $native (ref 57)))))
  (type $isOdd.closure (sub final 62 (struct (field $hash (mut i32)) (field $uniform (ref 51)) (field $native (ref 57)))))
  (type $count.closure (sub final 59 (struct (field $hash (mut i32)) (field $uniform (ref 50)) (field $native (ref 56)))))
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
  (import "quest.runtime" "putString" (func $putString (type 20)))
  (import "quest.runtime" "putChar" (func $putChar (type 21)))
  (import "quest.runtime" "concat" (func $concat (type 20)))
  (import "quest.runtime" "convInt" (func $convInt (type 22)))
  (import "quest.runtime" "convBool" (func $convBool (type 23)))
  (import "quest.runtime" "convChar" (func $convChar (type 23)))
  (import "quest.runtime" "raise" (func $raise (type 24)))
  (import "quest.runtime" "uncaught" (func $uncaught (type 25)))
  (import "quest.runtime" "decimal" (func $decimal (type 22)))
  (import "quest.runtime" "hex" (func $hex (type 22)))
  (import "quest.runtime" "escaped" (func $escaped (type 21)))
  (import "quest.runtime" "boxInt" (func $boxInt (type 22)))
  (import "quest.runtime" "unboxInt" (func $unboxInt (type 26)))
  (import "quest.runtime" "fatal" (func $fatal (type 27)))
  (import "quest.runtime" "stringGetChar" (func $stringGetChar (type 28)))
  (import "quest.runtime" "stringSetChar" (func $stringSetChar (type 29)))
  (import "quest.runtime" "stringNew" (func $stringNew (type 30)))
  (import "quest.runtime" "stringGetSub" (func $stringGetSub (type 31)))
  (import "quest.runtime" "stringSetSub" (func $stringSetSub (type 32)))
  (import "quest.runtime" "stringEqual" (func $stringEqual (type 33)))
  (import "quest.runtime" "exceptionOf" (func $exceptionOf (type 34)))
  (import "quest.runtime" "payloadOf" (func $payloadOf (type 34)))
  (import "quest.runtime" "raisedText" (func $raisedText (type 20)))
  (import "quest.runtime" "holdFatal" (func $holdFatal (type 35)))
  (import "quest.runtime" "fatalReport" (func $fatalReport (type 36)))
  (import "quest.runtime" "memLoad8" (func $memLoad8 (type 37)))
  (import "quest.runtime" "memStore8" (func $memStore8 (type 38)))
  (import "quest.runtime" "memLoad32" (func $memLoad32 (type 37)))
  (import "quest.runtime" "memStore32" (func $memStore32 (type 38)))
  (import "quest.runtime" "memLoad64" (func $memLoad64 (type 37)))
  (import "quest.runtime" "memStore64" (func $memStore64 (type 38)))
  (import "quest.runtime" "memEnsure" (func $memEnsure (type 39)))
  (import "quest.runtime" "memToString" (func $memToString (type 40)))
  (import "quest.runtime" "stringToMem" (func $stringToMem (type 41)))
  (import "quest.runtime" "wasi:args_sizes_get" (func $wasi:args_sizes_get (type 42)))
  (import "quest.runtime" "wasi:args_get" (func $wasi:args_get (type 42)))
  (import "quest.runtime" "wasi:environ_sizes_get" (func $wasi:environ_sizes_get (type 42)))
  (import "quest.runtime" "wasi:environ_get" (func $wasi:environ_get (type 42)))
  (import "quest.runtime" "wasi:fd_prestat_get" (func $wasi:fd_prestat_get (type 42)))
  (import "quest.runtime" "wasi:fd_prestat_dir_name" (func $wasi:fd_prestat_dir_name (type 43)))
  (import "quest.runtime" "wasi:path_open" (func $wasi:path_open (type 44)))
  (import "quest.runtime" "wasi:fd_read" (func $wasi:fd_read (type 45)))
  (import "quest.runtime" "wasi:fd_close" (func $wasi:fd_close (type 37)))
  (import "quest.runtime" "wasi:path_filestat_get" (func $wasi:path_filestat_get (type 46)))
  (import "quest.runtime" "wasi:path_create_directory" (func $wasi:path_create_directory (type 43)))
  (import "quest.runtime" "wasi:path_unlink_file" (func $wasi:path_unlink_file (type 43)))
  (import "quest.runtime" "wasi:path_remove_directory" (func $wasi:path_remove_directory (type 43)))
  (import "quest.runtime" "wasi:path_rename" (func $wasi:path_rename (type 47)))
  (import "quest.runtime" "wasi:fd_readdir" (func $wasi:fd_readdir (type 46)))
  (import "quest.runtime" "error" (tag $error (type 48)))
  (import "writer" "init" (func $writer.init (type 49)))
  (import "conv" "init" (func $conv.init (type 49)))
  (import "wasm/print" "init" (func $wasm/print.init (type 49)))
  (import "wasm/print" "show" (func $wasm/print.show (type 50)))
  (import "wasm/core" "unproxy" (func $wasm/core.unproxy (type 51)))
  (import "wasm/core" "proxyTag" (func $wasm/core.proxyTag (type 52)))
  (import "wasm/core" "proxyElement" (func $wasm/core.proxyElement (type 53)))
  (import "wasm/core" "proxyOptionElement" (func $wasm/core.proxyOptionElement (type 53)))
  (import "wasm/core" "proxyOptionPayload" (func $wasm/core.proxyOptionPayload (type 51)))
  (import "wasm/core" "writerPutString" (func $wasm/core.writerPutString (type 50)))
  (import "conv" "bool" (func $conv.bool (type 54)))
  (import "wasm/core" "flushWriters" (func $wasm/core.flushWriters (type 55)))
  (import "wasm/core" "init" (func $wasm/core.init (type 49)))
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
  (func $sum (type 56) (param $closure (ref $clos)) (param $n i64) (param $acc i64) (result i64)
    (local $v i32)
    (local $v.1 i64)
    (local $v.2 i64)
    loop $<self>
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
        local.set $acc
        local.set $n
        local.set $closure
        br $<self>
      end
    end
    unreachable
  )
  (func $isEven (type 57) (param $closure (ref $clos)) (param $n i64) (result i32)
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
  (func $isOdd (type 57) (param $closure (ref $clos)) (param $n i64) (result i32)
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
  (func $count (type 56) (param $closure (ref $clos)) (param $n i64) (param $acc i64) (result i64)
    (local $v i64)
    (local $v.1 i32)
    (local $v.4 i64)
    loop $<self>
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
            i32.const 0
            array.new_default $bytes
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
          local.set $acc
          local.set $n
          local.set $closure
          br $<self>
        end
      end
    end
    unreachable
  )
  (func $main (type 49)
    (local $v i64)
    (local $v.1 eqref)
    (local $v.2 eqref)
    (local $v.10 i32)
    call $wasm/core.init
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
    local.tee $v.2
    ref.test (ref i31)
    if (result eqref)
      local.get $v.2
      local.get $v.1
      call $putString
    else
      global.get $noClosure
      local.get $v.2
      local.get $v.1
      call $wasm/core.writerPutString
    end
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
    local.tee $v.2
    ref.test (ref i31)
    if (result eqref)
      local.get $v.2
      local.get $v.1
      call $putString
    else
      global.get $noClosure
      local.get $v.2
      local.get $v.1
      call $wasm/core.writerPutString
    end
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
    local.tee $v.2
    ref.test (ref i31)
    if (result eqref)
      local.get $v.2
      local.get $v.1
      call $putString
    else
      global.get $noClosure
      local.get $v.2
      local.get $v.1
      call $wasm/core.writerPutString
    end
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
    local.tee $v.2
    ref.test (ref i31)
    if (result eqref)
      local.get $v.2
      local.get $v.1
      call $putString
    else
      global.get $noClosure
      local.get $v.2
      local.get $v.1
      call $wasm/core.writerPutString
    end
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
    local.tee $v.2
    ref.test (ref i31)
    if (result eqref)
      local.get $v.2
      local.get $v.1
      call $putString
    else
      global.get $noClosure
      local.get $v.2
      local.get $v.1
      call $wasm/core.writerPutString
    end
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
    local.tee $v.2
    ref.test (ref i31)
    if (result eqref)
      local.get $v.2
      local.get $v.1
      call $putString
    else
      global.get $noClosure
      local.get $v.2
      local.get $v.1
      call $wasm/core.writerPutString
    end
    local.set $v.1
  )
  (func $_start (type 49)
    (local $t (ref null $raised))
    block $uncaught (result eqref)
      try_table (catch $error $uncaught)
        call $main
        global.get $noClosure
        call $wasm/core.flushWriters
        drop
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
    global.get $noClosure
    call $wasm/core.flushWriters
    drop
    call $uncaught
  )
  (func $unboxInt.1 (type 26) (param $e eqref) (result i64)
    block $small (result (ref i31))
      local.get $e
      br_on_cast $small eqref (ref i31)
      ref.cast (ref $boxInt)
      struct.get $boxInt $value
      return
    end
    i31.get_s
    i64.extend_i32_s
  )
  (func $boxInt.1 (type 22) (param $n i64) (result eqref)
    local.get $n
    i64.const 1073741824
    i64.add
    i64.const 2147483648
    i64.lt_u
    if (result eqref)
      local.get $n
      i32.wrap_i64
      ref.i31
    else
      local.get $n
      struct.new $boxInt
    end
  )
  (func $sum.uniform (type 50) (param $closure (ref $clos)) (param $a0 eqref) (param $a1 eqref) (result eqref)
    local.get $closure
    local.get $a0
    call $unboxInt.1
    local.get $a1
    call $unboxInt.1
    call $sum
    call $boxInt.1
  )
  (func $isEven.uniform (type 51) (param $closure (ref $clos)) (param $a0 eqref) (result eqref)
    local.get $closure
    local.get $a0
    call $unboxInt.1
    call $isEven
    ref.i31
  )
  (func $isOdd.uniform (type 51) (param $closure (ref $clos)) (param $a0 eqref) (result eqref)
    local.get $closure
    local.get $a0
    call $unboxInt.1
    call $isOdd
    ref.i31
  )
  (func $count.uniform (type 50) (param $closure (ref $clos)) (param $a0 eqref) (param $a1 eqref) (result eqref)
    local.get $closure
    local.get $a0
    call $unboxInt.1
    local.get $a1
    call $unboxInt.1
    call $count
    call $boxInt.1
  )
  (data $strings "/Users/haahr/Dropbox/Paul/src/quest/.claude/worktrees/wasm-plan-opus/tests/self-hosted/wasm/tail_calls.quest:11:24\0a\0a\0a\0a\0a\0a")
)


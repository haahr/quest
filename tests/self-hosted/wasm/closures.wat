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
  (type (func (param eqref eqref eqref eqref eqref eqref eqref) (result eqref)))
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
  (type (func (param i64 i64 i64 i64 i64 i64 i64) (result i64)))
  (type (func (param eqref)))
  (type (func))
  (type (func (param (ref $clos) eqref eqref) (result eqref)))
  (type (func (param (ref $clos) eqref) (result eqref)))
  (type (func (param (ref $clos) eqref) (result i64)))
  (type (func (param (ref $clos) eqref i64) (result eqref)))
  (type (func (param (ref $clos)) (result eqref)))
  (type (func (param (ref $clos) i64) (result i64)))
  (type (func (param (ref $clos) i64 eqref) (result i64)))
  (type $closU1 (sub $clos (struct (field $hash (mut i32)) (field $uniform (ref 53)))))
  (type (sub $closU1 (struct (field $hash (mut i32)) (field $uniform (ref 53)) (field $native (ref 57)))))
  (type $f.closure (sub final 60 (struct (field $hash (mut i32)) (field $uniform (ref 53)) (field $native (ref 57)))))
  (type $closU2 (sub $clos (struct (field $hash (mut i32)) (field $uniform (ref 52)))))
  (type (sub $closU2 (struct (field $hash (mut i32)) (field $uniform (ref 52)) (field $native (ref 58)))))
  (type $countDown.closure (sub final 63 (struct (field $hash (mut i32)) (field $uniform (ref 52)) (field $native (ref 58)))))
  (type (func (param (ref $clos) i64 i64) (result i64)))
  (type (sub $closU2 (struct (field $hash (mut i32)) (field $uniform (ref 52)) (field $native (ref 65)))))
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
  (import "string" "record.payload" (global (mut eqref)))
  (import "string" "record.dict" (global (mut eqref)))
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
  (import "quest.runtime" "concatN" (func $concatN (type 37)))
  (import "quest.runtime" "memLoad8" (func $memLoad8 (type 38)))
  (import "quest.runtime" "memStore8" (func $memStore8 (type 39)))
  (import "quest.runtime" "memLoad32" (func $memLoad32 (type 38)))
  (import "quest.runtime" "memStore32" (func $memStore32 (type 39)))
  (import "quest.runtime" "memLoad64" (func $memLoad64 (type 38)))
  (import "quest.runtime" "memStore64" (func $memStore64 (type 39)))
  (import "quest.runtime" "memEnsure" (func $memEnsure (type 40)))
  (import "quest.runtime" "memToString" (func $memToString (type 41)))
  (import "quest.runtime" "stringToMem" (func $stringToMem (type 42)))
  (import "quest.runtime" "wasi:args_sizes_get" (func $wasi:args_sizes_get (type 43)))
  (import "quest.runtime" "wasi:args_get" (func $wasi:args_get (type 43)))
  (import "quest.runtime" "wasi:environ_sizes_get" (func $wasi:environ_sizes_get (type 43)))
  (import "quest.runtime" "wasi:environ_get" (func $wasi:environ_get (type 43)))
  (import "quest.runtime" "wasi:fd_prestat_get" (func $wasi:fd_prestat_get (type 43)))
  (import "quest.runtime" "wasi:fd_prestat_dir_name" (func $wasi:fd_prestat_dir_name (type 44)))
  (import "quest.runtime" "wasi:path_open" (func $wasi:path_open (type 45)))
  (import "quest.runtime" "wasi:fd_read" (func $wasi:fd_read (type 46)))
  (import "quest.runtime" "wasi:fd_close" (func $wasi:fd_close (type 38)))
  (import "quest.runtime" "wasi:path_filestat_get" (func $wasi:path_filestat_get (type 47)))
  (import "quest.runtime" "wasi:path_create_directory" (func $wasi:path_create_directory (type 44)))
  (import "quest.runtime" "wasi:path_unlink_file" (func $wasi:path_unlink_file (type 44)))
  (import "quest.runtime" "wasi:path_remove_directory" (func $wasi:path_remove_directory (type 44)))
  (import "quest.runtime" "wasi:path_rename" (func $wasi:path_rename (type 48)))
  (import "quest.runtime" "wasi:fd_readdir" (func $wasi:fd_readdir (type 47)))
  (import "quest.runtime" "wasi:clock_time_get" (func $wasi:clock_time_get (type 44)))
  (import "quest.runtime" "wasi:poll_oneoff" (func $wasi:poll_oneoff (type 46)))
  (import "quest.runtime" "wasi:path_symlink" (func $wasi:path_symlink (type 47)))
  (import "quest.runtime" "wasi:path_readlink" (func $wasi:path_readlink (type 48)))
  (import "quest.runtime" "wasi:path_filestat_set_times" (func $wasi:path_filestat_set_times (type 49)))
  (import "quest.runtime" "error" (tag $error (type 50)))
  (import "writer" "init" (func $writer.init (type 51)))
  (import "conv" "init" (func $conv.init (type 51)))
  (import "string" "init" (func $string.init (type 51)))
  (import "wasm/print" "init" (func $wasm/print.init (type 51)))
  (import "wasm/print" "show" (func $wasm/print.show (type 52)))
  (import "wasm/core" "unproxy" (func $wasm/core.unproxy (type 53)))
  (import "wasm/core" "proxyTag" (func $wasm/core.proxyTag (type 54)))
  (import "wasm/core" "proxyElement" (func $wasm/core.proxyElement (type 55)))
  (import "wasm/core" "proxyOptionElement" (func $wasm/core.proxyOptionElement (type 55)))
  (import "wasm/core" "proxyOptionPayload" (func $wasm/core.proxyOptionPayload (type 53)))
  (import "wasm/core" "writerPutString" (func $wasm/core.writerPutString (type 52)))
  (import "wasm/core" "flushWriters" (func $wasm/core.flushWriters (type 56)))
  (import "wasm/core" "init" (func $wasm/core.init (type 51)))
  (global $noClosure (ref $clos) i32.const 0 struct.new $clos)
  (global $f.static (ref $f.closure) i32.const 0 ref.func $f.uniform ref.func $f struct.new $f.closure)
  (global $literal (mut eqref) ref.null none)
  (global $literal.1 (mut eqref) ref.null none)
  (global $literal.2 (mut eqref) ref.null none)
  (global $literal.3 (mut eqref) ref.null none)
  (global $literal.4 (mut eqref) ref.null none)
  (global $countDown.static (ref $countDown.closure) i32.const 0 ref.func $countDown.uniform ref.func $countDown struct.new $countDown.closure)
  (global $countDown.1 (mut eqref) ref.null none)
  (global $literal.5 (mut eqref) ref.null none)
  (global $literal.6 (mut eqref) ref.null none)
  (global $literal.7 (mut eqref) ref.null none)
  (global $literal.8 (mut eqref) ref.null none)
  (global $literal.9 (mut eqref) ref.null none)
  (global $builtin+.static (ref 66) i32.const 0 ref.func $builtin+.uniform ref.func $builtin+ struct.new 66)
  (global $builtin-.static (ref 66) i32.const 0 ref.func $builtin-.uniform ref.func $builtin- struct.new 66)
  (export "_start" (func $_start))
  (elem declare func $f.uniform $f $countDown.uniform $countDown $builtin+ $builtin+.uniform $builtin- $builtin-.uniform)
  (func $f (type 57) (param $closure (ref $clos)) (param $x i64) (result i64)
    (local $v i64)
    local.get $x
    i64.const 5
    i64.add
    local.set $v
    local.get $v
    return
    unreachable
  )
  (func $countDown (type 58) (param $closure (ref $clos)) (param $n i64) (param $k eqref) (result i64)
    (local $v i32)
    (local $t eqref)
    (local $v.1 i64)
    loop $<self>
      local.get $n
      i64.const 0
      i64.eq
      local.set $v
      local.get $v
      if
        local.get $k
        local.set $t
        local.get $t
        ref.test (ref 60)
        if
          local.get $t
          ref.cast (ref $clos)
          i64.const 0
          local.get $t
          ref.cast (ref 60)
          struct.get 60 $native
          return_call_ref 57
        else
          local.get $t
          ref.cast (ref $clos)
          i64.const 0
          call $boxInt.1
          local.get $t
          ref.cast (ref $closU1)
          struct.get $closU1 $uniform
          call_ref 53
          call $unboxInt.1
          return
        end
      else
        local.get $n
        i64.const 1
        i64.sub
        local.set $v.1
        global.get $noClosure
        local.get $v.1
        local.get $k
        local.set $k
        local.set $n
        local.set $closure
        br $<self>
      end
    end
    unreachable
  )
  (func $main (type 51)
    (local $f eqref)
    (local $v eqref)
    (local $v.1 eqref)
    (local $x i64)
    (local $n i64)
    (local $f.2 eqref)
    (local $x.1 i64)
    (local $n.1 i64)
    (local $v.2 i32)
    (local $t eqref)
    call $wasm/core.init
    call $writer.init
    call $conv.init
    call $string.init
    global.get $f.static
    local.set $f
    i64.const 15
    call $convInt
    local.set $v
    i64.const 17
    call $convInt
    local.set $v.1
    block $contified7.after
      block $contified7 (result i64)
        local.get $f
        local.set $f
        i64.const 0
        local.set $x
        i64.const 1000000
        local.set $n
        block $contified6.exit
          loop $contified6
            local.get $f
            local.set $f.2
            local.get $x
            local.set $x.1
            local.get $n
            local.set $n.1
            local.get $n.1
            i64.const 0
            i64.eq
            local.set $v.2
            local.get $v.2
            if
              local.get $x.1
              br $contified7
            else
              local.get $f.2
              local.set $t
              local.get $t
              ref.test (ref 60)
              if (result i64)
                local.get $t
                ref.cast (ref $clos)
                local.get $x.1
                local.get $t
                ref.cast (ref 60)
                struct.get 60 $native
                call_ref 57
              else
                local.get $t
                ref.cast (ref $clos)
                local.get $x.1
                call $boxInt.1
                local.get $t
                ref.cast (ref $closU1)
                struct.get $closU1 $uniform
                call_ref 53
                call $unboxInt.1
              end
              local.set $x.1
              local.get $n.1
              i64.const 1
              i64.sub
              local.set $n.1
              local.get $f.2
              local.set $f
              local.get $x.1
              local.set $x
              local.get $n.1
              local.set $n
              br $contified6
            end
            br $contified6
          end
        end
        br $contified7.after
      end
      local.set $x
      local.get $x
      call $convInt
      local.set $f
      local.get $v
      global.get $literal
      ref.is_null
      if
        i32.const 1073741824
        i32.const 1
        i32.const 0
        i32.const 1
        array.new_data $bytes $strings
        struct.new $string
        global.set $literal
      end
      global.get $literal
      local.get $v.1
      global.get $literal
      ref.is_null
      if
        i32.const 1073741824
        i32.const 1
        i32.const 1
        i32.const 1
        array.new_data $bytes $strings
        struct.new $string
        global.set $literal
      end
      global.get $literal
      local.get $f
      ref.null eq
      ref.null eq
      call $concatN
      local.set $f
      i32.const 1
      ref.i31
      local.set $v
      local.get $f
      global.get $literal.1
      ref.is_null
      if
        i32.const 1073741824
        i32.const 1
        i32.const 2
        i32.const 1
        array.new_data $bytes $strings
        struct.new $string
        global.set $literal.1
      end
      global.get $literal.1
      call $concat
      local.set $f
      local.get $v
      local.tee $v
      ref.test (ref i31)
      if (result eqref)
        local.get $v
        local.get $f
        call $putString
      else
        global.get $noClosure
        local.get $v
        local.get $f
        call $wasm/core.writerPutString
      end
      local.set $f
      i32.const 0
      global.get $literal.2
      ref.is_null
      if
        i32.const 1073741824
        i32.const 1
        i32.const 3
        i32.const 1
        array.new_data $bytes $strings
        struct.new $string
        global.set $literal.2
      end
      global.get $literal.2
      global.get $literal.3
      ref.is_null
      if
        i32.const 1073741824
        i32.const 2
        i32.const 4
        i32.const 2
        array.new_data $bytes $strings
        struct.new $string
        global.set $literal.3
      end
      global.get $literal.3
      global.get $literal.4
      ref.is_null
      if
        i32.const 1073741824
        i32.const 3
        i32.const 6
        i32.const 3
        array.new_data $bytes $strings
        struct.new $string
        global.set $literal.4
      end
      global.get $literal.4
      array.new_fixed $slots 3
      struct.new $array
      local.set $f
      i64.const 0
      local.set $x
      local.get $f
      ref.cast (ref $array)
      struct.get $array $elems
      array.len
      i64.extend_i32_u
      local.set $n
      local.get $n
      i64.const 1
      i64.sub
      local.set $n
      i64.const 0
      local.set $x.1
      local.get $x.1
      local.get $n
      i64.le_s
      local.set $v.2
      local.get $v.2
      if
        block $L1_1.exit
          loop $L1_1
            local.get $x.1
            local.set $n.1
            local.get $n.1
            local.get $f
            ref.cast (ref $array)
            struct.get $array $elems
            array.len
            i64.extend_i32_u
            i64.lt_u
            i32.eqz
            if
              global.get $arrayOp.error
              i32.const 0
              ref.i31
              i32.const 0
              i32.const 43
              i32.const 9
              i32.const 43
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
            local.get $f
            ref.cast (ref $array)
            struct.get $array $elems
            local.get $n.1
            i32.wrap_i64
            array.get $slots
            local.set $v
            local.get $v
            ref.cast (ref $string)
            struct.get $string $length
            i64.extend_i32_u
            local.set $n.1
            local.get $x
            local.get $n.1
            i64.add
            local.set $n.1
            local.get $n.1
            local.set $x
            local.get $x.1
            local.get $n
            i64.eq
            local.set $v.2
            local.get $v.2
            if
              br $L1_1.exit
            else
            end
            local.get $x.1
            i64.const 1
            i64.add
            local.set $n.1
            local.get $n.1
            local.set $x.1
            br $L1_1
          end
        end
      else
      end
      local.get $x
      local.set $x
      local.get $x
      call $convInt
      local.set $f
      i32.const 1
      ref.i31
      local.set $v
      local.get $f
      global.get $literal.1
      ref.is_null
      if
        i32.const 1073741824
        i32.const 1
        i32.const 52
        i32.const 1
        array.new_data $bytes $strings
        struct.new $string
        global.set $literal.1
      end
      global.get $literal.1
      call $concat
      local.set $f
      local.get $v
      local.tee $v
      ref.test (ref i31)
      if (result eqref)
        local.get $v
        local.get $f
        call $putString
      else
        global.get $noClosure
        local.get $v
        local.get $f
        call $wasm/core.writerPutString
      end
      local.set $f
      i64.const 13
      call $convInt
      local.set $f
      i64.const 106
      call $convInt
      local.set $v
      local.get $f
      global.get $literal
      ref.is_null
      if
        i32.const 1073741824
        i32.const 1
        i32.const 53
        i32.const 1
        array.new_data $bytes $strings
        struct.new $string
        global.set $literal
      end
      global.get $literal
      local.get $v
      ref.null eq
      ref.null eq
      ref.null eq
      ref.null eq
      call $concatN
      local.set $f
      i32.const 1
      ref.i31
      local.set $v
      local.get $f
      global.get $literal.1
      ref.is_null
      if
        i32.const 1073741824
        i32.const 1
        i32.const 54
        i32.const 1
        array.new_data $bytes $strings
        struct.new $string
        global.set $literal.1
      end
      global.get $literal.1
      call $concat
      local.set $f
      local.get $v
      local.tee $v
      ref.test (ref i31)
      if (result eqref)
        local.get $v
        local.get $f
        call $putString
      else
        global.get $noClosure
        local.get $v
        local.get $f
        call $wasm/core.writerPutString
      end
      local.set $f
      global.get $countDown.static
      global.set $countDown.1
      block $contified9.after
        block $contified9 (result i64)
          i64.const 1000000
          local.set $x
          block $contified8.exit
            loop $contified8
              local.get $x
              local.set $n
              local.get $n
              i64.const 0
              i64.eq
              local.set $v.2
              local.get $v.2
              if
                i64.const 1
                br $contified9
              else
                local.get $n
                i64.const 1
                i64.sub
                local.set $n
                local.get $n
                local.set $x
                br $contified8
              end
              br $contified8
            end
          end
          br $contified9.after
        end
        local.set $x
        local.get $x
        call $convInt
        local.set $f
        i32.const 1
        ref.i31
        local.set $v
        local.get $f
        global.get $literal.1
        ref.is_null
        if
          i32.const 1073741824
          i32.const 1
          i32.const 55
          i32.const 1
          array.new_data $bytes $strings
          struct.new $string
          global.set $literal.1
        end
        global.get $literal.1
        call $concat
        local.set $f
        local.get $v
        local.tee $v
        ref.test (ref i31)
        if (result eqref)
          local.get $v
          local.get $f
          call $putString
        else
          global.get $noClosure
          local.get $v
          local.get $f
          call $wasm/core.writerPutString
        end
        local.set $f
        global.get $literal.5
        ref.is_null
        if
          i32.const 1073741824
          i32.const 3
          i32.const 56
          i32.const 3
          array.new_data $bytes $strings
          struct.new $string
          global.set $literal.5
        end
        global.get $literal.5
        local.set $f
        local.get $f
        global.get $literal.6
        ref.is_null
        if
          i32.const 1073741824
          i32.const 1
          i32.const 59
          i32.const 1
          array.new_data $bytes $strings
          struct.new $string
          global.set $literal.6
        end
        global.get $literal.6
        call $concat
        local.set $f
        global.get $literal.7
        ref.is_null
        if
          i32.const 1073741824
          i32.const 2
          i32.const 60
          i32.const 2
          array.new_data $bytes $strings
          struct.new $string
          global.set $literal.7
        end
        global.get $literal.7
        local.set $v
        local.get $f
        global.get $literal.8
        ref.is_null
        if
          i32.const 1073741824
          i32.const 1
          i32.const 62
          i32.const 1
          array.new_data $bytes $strings
          struct.new $string
          global.set $literal.8
        end
        global.get $literal.8
        local.get $v
        global.get $literal.9
        ref.is_null
        if
          i32.const 1073741824
          i32.const 1
          i32.const 63
          i32.const 1
          array.new_data $bytes $strings
          struct.new $string
          global.set $literal.9
        end
        global.get $literal.9
        ref.null eq
        ref.null eq
        ref.null eq
        call $concatN
        local.set $f
        i32.const 1
        ref.i31
        local.set $v
        local.get $f
        global.get $literal.1
        ref.is_null
        if
          i32.const 1073741824
          i32.const 1
          i32.const 64
          i32.const 1
          array.new_data $bytes $strings
          struct.new $string
          global.set $literal.1
        end
        global.get $literal.1
        call $concat
        local.set $f
        local.get $v
        local.tee $v
        ref.test (ref i31)
        if (result eqref)
          local.get $v
          local.get $f
          call $putString
        else
          global.get $noClosure
          local.get $v
          local.get $f
          call $wasm/core.writerPutString
        end
        local.set $f
        global.get $builtin+.static
        local.set $f
        i32.const 0
        i64.const 1
        call $boxInt.1
        i64.const 2
        call $boxInt.1
        i64.const 3
        call $boxInt.1
        i64.const 4
        call $boxInt.1
        array.new_fixed $slots 4
        struct.new $array
        local.set $v
        i64.const 0
        local.set $x
        local.get $v
        ref.cast (ref $array)
        struct.get $array $elems
        array.len
        i64.extend_i32_u
        local.set $n
        local.get $n
        i64.const 1
        i64.sub
        local.set $n
        i64.const 0
        local.set $x.1
        local.get $x.1
        local.get $n
        i64.le_s
        local.set $v.2
        local.get $v.2
        if
          block $L2_4.exit
            loop $L2_4
              local.get $x.1
              local.set $n.1
              local.get $n.1
              local.get $v
              ref.cast (ref $array)
              struct.get $array $elems
              array.len
              i64.extend_i32_u
              i64.lt_u
              i32.eqz
              if
                global.get $arrayOp.error
                i32.const 0
                ref.i31
                i32.const 0
                i32.const 43
                i32.const 65
                i32.const 43
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
              local.get $v
              ref.cast (ref $array)
              struct.get $array $elems
              local.get $n.1
              i32.wrap_i64
              array.get $slots
              call $unboxInt.1
              local.set $n.1
              local.get $f
              local.set $v.1
              local.get $v.1
              ref.test (ref 66)
              if (result i64)
                local.get $v.1
                ref.cast (ref $clos)
                local.get $x
                local.get $n.1
                local.get $v.1
                ref.cast (ref 66)
                struct.get 66 $native
                call_ref 65
              else
                local.get $v.1
                ref.cast (ref $clos)
                local.get $x
                call $boxInt.1
                local.get $n.1
                call $boxInt.1
                local.get $v.1
                ref.cast (ref $closU2)
                struct.get $closU2 $uniform
                call_ref 52
                call $unboxInt.1
              end
              local.set $n.1
              local.get $n.1
              local.set $x
              local.get $x.1
              local.get $n
              i64.eq
              local.set $v.2
              local.get $v.2
              if
                br $L2_4.exit
              else
              end
              local.get $x.1
              i64.const 1
              i64.add
              local.set $n.1
              local.get $n.1
              local.set $x.1
              br $L2_4
            end
          end
        else
        end
        local.get $x
        local.set $x
        local.get $x
        call $convInt
        local.set $f
        global.get $builtin-.static
        local.set $v
        i32.const 0
        i64.const 1
        call $boxInt.1
        i64.const 2
        call $boxInt.1
        i64.const 3
        call $boxInt.1
        i64.const 4
        call $boxInt.1
        array.new_fixed $slots 4
        struct.new $array
        local.set $v.1
        i64.const 100
        local.set $x
        local.get $v.1
        ref.cast (ref $array)
        struct.get $array $elems
        array.len
        i64.extend_i32_u
        local.set $n
        local.get $n
        i64.const 1
        i64.sub
        local.set $n
        i64.const 0
        local.set $x.1
        local.get $x.1
        local.get $n
        i64.le_s
        local.set $v.2
        local.get $v.2
        if
          block $L2_5.exit
            loop $L2_5
              local.get $x.1
              local.set $n.1
              local.get $n.1
              local.get $v.1
              ref.cast (ref $array)
              struct.get $array $elems
              array.len
              i64.extend_i32_u
              i64.lt_u
              i32.eqz
              if
                global.get $arrayOp.error
                i32.const 0
                ref.i31
                i32.const 0
                i32.const 43
                i32.const 108
                i32.const 43
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
              local.get $v.1
              ref.cast (ref $array)
              struct.get $array $elems
              local.get $n.1
              i32.wrap_i64
              array.get $slots
              call $unboxInt.1
              local.set $n.1
              local.get $v
              local.set $f.2
              local.get $f.2
              ref.test (ref 66)
              if (result i64)
                local.get $f.2
                ref.cast (ref $clos)
                local.get $x
                local.get $n.1
                local.get $f.2
                ref.cast (ref 66)
                struct.get 66 $native
                call_ref 65
              else
                local.get $f.2
                ref.cast (ref $clos)
                local.get $x
                call $boxInt.1
                local.get $n.1
                call $boxInt.1
                local.get $f.2
                ref.cast (ref $closU2)
                struct.get $closU2 $uniform
                call_ref 52
                call $unboxInt.1
              end
              local.set $n.1
              local.get $n.1
              local.set $x
              local.get $x.1
              local.get $n
              i64.eq
              local.set $v.2
              local.get $v.2
              if
                br $L2_5.exit
              else
              end
              local.get $x.1
              i64.const 1
              i64.add
              local.set $n.1
              local.get $n.1
              local.set $x.1
              br $L2_5
            end
          end
        else
        end
        local.get $x
        local.set $x
        local.get $x
        call $convInt
        local.set $v
        local.get $f
        global.get $literal
        ref.is_null
        if
          i32.const 1073741824
          i32.const 1
          i32.const 151
          i32.const 1
          array.new_data $bytes $strings
          struct.new $string
          global.set $literal
        end
        global.get $literal
        local.get $v
        ref.null eq
        ref.null eq
        ref.null eq
        ref.null eq
        call $concatN
        local.set $f
        i32.const 1
        ref.i31
        local.set $v
        local.get $f
        global.get $literal.1
        ref.is_null
        if
          i32.const 1073741824
          i32.const 1
          i32.const 152
          i32.const 1
          array.new_data $bytes $strings
          struct.new $string
          global.set $literal.1
        end
        global.get $literal.1
        call $concat
        local.set $f
        local.get $v
        local.tee $v
        ref.test (ref i31)
        if (result eqref)
          local.get $v
          local.get $f
          call $putString
        else
          global.get $noClosure
          local.get $v
          local.get $f
          call $wasm/core.writerPutString
        end
        local.set $f
      end
    end
  )
  (func $_start (type 51)
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
  (func $f.uniform (type 53) (param $closure (ref $clos)) (param $a0 eqref) (result eqref)
    local.get $closure
    local.get $a0
    call $unboxInt.1
    call $f
    call $boxInt.1
  )
  (func $countDown.uniform (type 52) (param $closure (ref $clos)) (param $a0 eqref) (param $a1 eqref) (result eqref)
    local.get $closure
    local.get $a0
    call $unboxInt.1
    local.get $a1
    call $countDown
    call $boxInt.1
  )
  (func $builtin+ (type 65) (param $closure (ref $clos)) (param $a i64) (param $b i64) (result i64)
    local.get $a
    local.get $b
    i64.add
  )
  (func $builtin+.uniform (type 52) (param $closure (ref $clos)) (param $a eqref) (param $b eqref) (result eqref)
    local.get $closure
    local.get $a
    call $unboxInt.1
    local.get $b
    call $unboxInt.1
    call $builtin+
    call $boxInt.1
  )
  (func $builtin- (type 65) (param $closure (ref $clos)) (param $a i64) (param $b i64) (result i64)
    local.get $a
    local.get $b
    i64.sub
  )
  (func $builtin-.uniform (type 52) (param $closure (ref $clos)) (param $a eqref) (param $b eqref) (result eqref)
    local.get $closure
    local.get $a
    call $unboxInt.1
    local.get $b
    call $unboxInt.1
    call $builtin-
    call $boxInt.1
  )
  (data $strings "  \0aabbccctests/self-hosted/wasm/closures.quest:17:55\0a \0a\0ayes!no<>\0atests/self-hosted/wasm/closures.quest:31:50tests/self-hosted/wasm/closures.quest:31:50 \0a")
)


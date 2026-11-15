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
  (type (func (param (ref $clos) i64) (result i64)))
  (type (func (param (ref $clos) i64 eqref) (result i64)))
  (type (func (param (ref $clos) eqref) (result eqref)))
  (type $closU1 (sub $clos (struct (field $hash (mut i32)) (field $uniform (ref 49)))))
  (type (sub $closU1 (struct (field $hash (mut i32)) (field $uniform (ref 49)) (field $native (ref 47)))))
  (type $f.closure (sub final 51 (struct (field $hash (mut i32)) (field $uniform (ref 49)) (field $native (ref 47)))))
  (type $closU2 (sub $clos (struct (field $hash (mut i32)) (field $uniform (ref 46)))))
  (type (sub $closU2 (struct (field $hash (mut i32)) (field $uniform (ref 46)) (field $native (ref 48)))))
  (type $countDown.closure (sub final 54 (struct (field $hash (mut i32)) (field $uniform (ref 46)) (field $native (ref 48)))))
  (type (func (param (ref $clos) i64 i64) (result i64)))
  (type (sub $closU2 (struct (field $hash (mut i32)) (field $uniform (ref 46)) (field $native (ref 56)))))
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
  (import "quest.runtime" "raisedText" (func $raisedText (type 18)))
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
  (import "string" "init" (func $string.init (type 45)))
  (import "wasm/print" "init" (func $wasm/print.init (type 45)))
  (import "wasm/print" "show" (func $wasm/print.show (type 46)))
  (global $noClosure (ref $clos) i32.const 0 struct.new $clos)
  (global $f.static (ref $f.closure) i32.const 0 ref.func $f.uniform ref.func $f struct.new $f.closure)
  (global $countDown.static (ref $countDown.closure) i32.const 0 ref.func $countDown.uniform ref.func $countDown struct.new $countDown.closure)
  (global $countDown.1 (mut eqref) ref.null none)
  (global $builtin+.static (ref 57) i32.const 0 ref.func $builtin+.uniform ref.func $builtin+ struct.new 57)
  (global $builtin-.static (ref 57) i32.const 0 ref.func $builtin-.uniform ref.func $builtin- struct.new 57)
  (export "_start" (func $_start))
  (elem declare func $f.uniform $f $countDown.uniform $countDown $builtin+ $builtin+.uniform $builtin- $builtin-.uniform)
  (func $f (type 47) (param $closure (ref $clos)) (param $x i64) (result i64)
    (local $v i64)
    local.get $x
    i64.const 5
    i64.add
    local.set $v
    local.get $v
    return
    unreachable
  )
  (func $countDown (type 48) (param $closure (ref $clos)) (param $n i64) (param $k eqref) (result i64)
    (local $v i32)
    (local $t eqref)
    (local $v.1 i64)
    local.get $n
    i64.const 0
    i64.eq
    local.set $v
    local.get $v
    if
      local.get $k
      local.set $t
      local.get $t
      ref.test (ref 51)
      if
        local.get $t
        ref.cast (ref $clos)
        i64.const 0
        local.get $t
        ref.cast (ref 51)
        struct.get 51 $native
        return_call_ref 47
      else
        local.get $t
        ref.cast (ref $clos)
        i64.const 0
        call $boxInt
        local.get $t
        ref.cast (ref $closU1)
        struct.get $closU1 $uniform
        call_ref 49
        call $unboxInt
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
      return_call $countDown
    end
    unreachable
  )
  (func $main (type 45)
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
              ref.test (ref 51)
              if (result i64)
                local.get $t
                ref.cast (ref $clos)
                local.get $x.1
                local.get $t
                ref.cast (ref 51)
                struct.get 51 $native
                call_ref 47
              else
                local.get $t
                ref.cast (ref $clos)
                local.get $x.1
                call $boxInt
                local.get $t
                ref.cast (ref $closU1)
                struct.get $closU1 $uniform
                call_ref 49
                call $unboxInt
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
      i32.const 0
      i32.const 1
      i32.const 0
      i32.const 1
      array.new_data $bytes $strings
      struct.new $string
      local.get $f
      call $concat
      local.set $f
      local.get $v.1
      local.get $f
      call $concat
      local.set $f
      i32.const 0
      i32.const 1
      i32.const 1
      i32.const 1
      array.new_data $bytes $strings
      struct.new $string
      local.get $f
      call $concat
      local.set $f
      local.get $v
      local.get $f
      call $concat
      local.set $f
      i32.const 1
      ref.i31
      local.set $v
      local.get $f
      i32.const 0
      i32.const 1
      i32.const 2
      i32.const 1
      array.new_data $bytes $strings
      struct.new $string
      call $concat
      local.set $f
      local.get $v
      local.get $f
      call $putString
      local.set $f
      i32.const 0
      i32.const 0
      i32.const 1
      i32.const 3
      i32.const 1
      array.new_data $bytes $strings
      struct.new $string
      i32.const 0
      i32.const 2
      i32.const 4
      i32.const 2
      array.new_data $bytes $strings
      struct.new $string
      i32.const 0
      i32.const 3
      i32.const 6
      i32.const 3
      array.new_data $bytes $strings
      struct.new $string
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
              i32.const 112
              i32.const 9
              i32.const 112
              array.new_data $bytes $strings
              struct.new $string
              i32.const 0
              i32.const 0
              i32.const 121
              i32.const 0
              array.new_data $bytes $strings
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
      i32.const 0
      i32.const 1
      i32.const 121
      i32.const 1
      array.new_data $bytes $strings
      struct.new $string
      call $concat
      local.set $f
      local.get $v
      local.get $f
      call $putString
      local.set $f
      i64.const 13
      call $convInt
      local.set $f
      i64.const 106
      call $convInt
      local.set $v
      i32.const 0
      i32.const 1
      i32.const 122
      i32.const 1
      array.new_data $bytes $strings
      struct.new $string
      local.get $v
      call $concat
      local.set $v
      local.get $f
      local.get $v
      call $concat
      local.set $f
      i32.const 1
      ref.i31
      local.set $v
      local.get $f
      i32.const 0
      i32.const 1
      i32.const 123
      i32.const 1
      array.new_data $bytes $strings
      struct.new $string
      call $concat
      local.set $f
      local.get $v
      local.get $f
      call $putString
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
        i32.const 0
        i32.const 1
        i32.const 124
        i32.const 1
        array.new_data $bytes $strings
        struct.new $string
        call $concat
        local.set $f
        local.get $v
        local.get $f
        call $putString
        local.set $f
        i32.const 0
        i32.const 3
        i32.const 125
        i32.const 3
        array.new_data $bytes $strings
        struct.new $string
        local.set $f
        local.get $f
        i32.const 0
        i32.const 1
        i32.const 128
        i32.const 1
        array.new_data $bytes $strings
        struct.new $string
        call $concat
        local.set $f
        i32.const 0
        i32.const 2
        i32.const 129
        i32.const 2
        array.new_data $bytes $strings
        struct.new $string
        local.set $v
        local.get $v
        i32.const 0
        i32.const 1
        i32.const 131
        i32.const 1
        array.new_data $bytes $strings
        struct.new $string
        call $concat
        local.set $v
        i32.const 0
        i32.const 1
        i32.const 132
        i32.const 1
        array.new_data $bytes $strings
        struct.new $string
        local.get $v
        call $concat
        local.set $v
        local.get $f
        local.get $v
        call $concat
        local.set $f
        i32.const 1
        ref.i31
        local.set $v
        local.get $f
        i32.const 0
        i32.const 1
        i32.const 133
        i32.const 1
        array.new_data $bytes $strings
        struct.new $string
        call $concat
        local.set $f
        local.get $v
        local.get $f
        call $putString
        local.set $f
        global.get $builtin+.static
        local.set $f
        i32.const 0
        i64.const 1
        call $boxInt
        i64.const 2
        call $boxInt
        i64.const 3
        call $boxInt
        i64.const 4
        call $boxInt
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
                i32.const 112
                i32.const 134
                i32.const 112
                array.new_data $bytes $strings
                struct.new $string
                i32.const 0
                i32.const 0
                i32.const 246
                i32.const 0
                array.new_data $bytes $strings
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
              call $unboxInt
              local.set $n.1
              local.get $f
              local.set $v.1
              local.get $v.1
              ref.test (ref 57)
              if (result i64)
                local.get $v.1
                ref.cast (ref $clos)
                local.get $x
                local.get $n.1
                local.get $v.1
                ref.cast (ref 57)
                struct.get 57 $native
                call_ref 56
              else
                local.get $v.1
                ref.cast (ref $clos)
                local.get $x
                call $boxInt
                local.get $n.1
                call $boxInt
                local.get $v.1
                ref.cast (ref $closU2)
                struct.get $closU2 $uniform
                call_ref 46
                call $unboxInt
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
        call $boxInt
        i64.const 2
        call $boxInt
        i64.const 3
        call $boxInt
        i64.const 4
        call $boxInt
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
                i32.const 112
                i32.const 246
                i32.const 112
                array.new_data $bytes $strings
                struct.new $string
                i32.const 0
                i32.const 0
                i32.const 358
                i32.const 0
                array.new_data $bytes $strings
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
              call $unboxInt
              local.set $n.1
              local.get $v
              local.set $f.2
              local.get $f.2
              ref.test (ref 57)
              if (result i64)
                local.get $f.2
                ref.cast (ref $clos)
                local.get $x
                local.get $n.1
                local.get $f.2
                ref.cast (ref 57)
                struct.get 57 $native
                call_ref 56
              else
                local.get $f.2
                ref.cast (ref $clos)
                local.get $x
                call $boxInt
                local.get $n.1
                call $boxInt
                local.get $f.2
                ref.cast (ref $closU2)
                struct.get $closU2 $uniform
                call_ref 46
                call $unboxInt
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
        i32.const 0
        i32.const 1
        i32.const 358
        i32.const 1
        array.new_data $bytes $strings
        struct.new $string
        local.get $v
        call $concat
        local.set $v
        local.get $f
        local.get $v
        call $concat
        local.set $f
        i32.const 1
        ref.i31
        local.set $v
        local.get $f
        i32.const 0
        i32.const 1
        i32.const 359
        i32.const 1
        array.new_data $bytes $strings
        struct.new $string
        call $concat
        local.set $f
        local.get $v
        local.get $f
        call $putString
        local.set $f
      end
    end
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
  (func $f.uniform (type 49) (param $closure (ref $clos)) (param $a0 eqref) (result eqref)
    local.get $closure
    local.get $a0
    call $unboxInt
    call $f
    call $boxInt
  )
  (func $countDown.uniform (type 46) (param $closure (ref $clos)) (param $a0 eqref) (param $a1 eqref) (result eqref)
    local.get $closure
    local.get $a0
    call $unboxInt
    local.get $a1
    call $countDown
    call $boxInt
  )
  (func $builtin+ (type 56) (param $closure (ref $clos)) (param $a i64) (param $b i64) (result i64)
    local.get $a
    local.get $b
    i64.add
  )
  (func $builtin+.uniform (type 46) (param $closure (ref $clos)) (param $a eqref) (param $b eqref) (result eqref)
    local.get $closure
    local.get $a
    call $unboxInt
    local.get $b
    call $unboxInt
    call $builtin+
    call $boxInt
  )
  (func $builtin- (type 56) (param $closure (ref $clos)) (param $a i64) (param $b i64) (result i64)
    local.get $a
    local.get $b
    i64.sub
  )
  (func $builtin-.uniform (type 46) (param $closure (ref $clos)) (param $a eqref) (param $b eqref) (result eqref)
    local.get $closure
    local.get $a
    call $unboxInt
    local.get $b
    call $unboxInt
    call $builtin-
    call $boxInt
  )
  (data $strings "  \0aabbccc/Users/haahr/Dropbox/Paul/src/quest/.claude/worktrees/wasm-plan-opus/tests/self-hosted/wasm/closures.quest:17:55\0a \0a\0ayes!no><\0a/Users/haahr/Dropbox/Paul/src/quest/.claude/worktrees/wasm-plan-opus/tests/self-hosted/wasm/closures.quest:31:50/Users/haahr/Dropbox/Paul/src/quest/.claude/worktrees/wasm-plan-opus/tests/self-hosted/wasm/closures.quest:31:50 \0a")
)


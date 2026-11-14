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
  (type (func (param (ref $clos) i64) (result eqref)))
  (type (func (param (ref $clos) i64 eqref i64 i64) (result eqref)))
  (type (func (param (ref $clos) eqref i64 eqref eqref) (result eqref)))
  (type (func (param (ref $clos) eqref i64 i64 eqref) (result eqref)))
  (type (func (param (ref $clos) i32) (result eqref)))
  (type (func (param (ref $clos) i64 i64) (result i64 i64)))
  (type (func (param eqref) (result (ref $option))))
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
  (import "wasm/core" "init" (func $wasm/core.init (type 45)))
  (import "wasm/core" "base" (func $wasm/core.base (type 47)))
  (import "wasm/core" "newDesc" (func $wasm/core.newDesc (type 48)))
  (import "wasm/core" "setPart" (func $wasm/core.setPart (type 49)))
  (import "wasm/core" "setText" (func $wasm/core.setText (type 50)))
  (import "wasm/core" "instantiate" (func $wasm/core.instantiate (type 46)))
  (import "conv" "bool" (func $conv.bool (type 51)))
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
  (global $QRecord_name_String_x_Int_y_Int (mut eqref) ref.null none)
  (global $QTuple_Int_90c1d29a40761138 (mut eqref) ref.null none)
  (global $QTuple_Int_Int_586d0a3b5f6d6e01 (mut eqref) ref.null none)
  (global $QTuple_Int_bf55836b2befd5ab (mut eqref) ref.null none)
  (global $QTuple_Int_742e411bebefcd67 (mut eqref) ref.null none)
  (global $QOption_circle_QTuple_In_54aeab0eecb1911c_af955c1b1c25c023 (mut eqref) ref.null none)
  (global $QOption_none_some_QTuple_Int_end_9e75d53e4132c43a (mut eqref) ref.null none)
  (global $divide.1 (mut eqref) ref.null none)
  (global $dict (ref $dict) i32.const 0 i32.const 1 i32.const 2 array.new_fixed $i32s 3 struct.new $dict)
  (export "_start" (func $_start))
  (func $divide (type 52) (param $closure (ref $clos)) (param $n i64) (param $d i64) (result i64 i64)
    (local $v i32)
    (local $v.2 i64)
    (local $v.1 i64)
    local.get $n
    local.get $d
    i64.lt_s
    local.set $v
    local.get $v
    if
      i64.const 0
      local.get $n
      local.set $v.2
      local.set $v.1
      local.get $v.1
      local.get $v.2
      return
    else
      local.get $n
      local.get $d
      i64.sub
      local.set $v.2
      global.get $noClosure
      local.get $v.2
      local.get $d
      call $divide
      local.set $v.2
      local.set $v.1
      local.get $v.1
      local.set $v.1
      local.get $v.1
      i64.const 1
      i64.add
      local.set $v.1
      local.get $v.2
      local.set $v.2
      local.get $v.1
      local.get $v.2
      local.set $v.2
      local.set $v.1
      local.get $v.1
      local.get $v.2
      return
    end
    unreachable
  )
  (func $main (type 45)
    (local $v eqref)
    (local $t (ref null $slots))
    (local $v.2 eqref)
    (local $v.4 eqref)
    (local $v.5 eqref)
    (local $v.7 i64)
    (local $i i64)
    (local $v.9 i32)
    (local $i.1 i64)
    (local $t.3 (ref null $option))
    (local $v.12 i64)
    (local $v.48 eqref)
    (local $t.22 i32)
    (local $t.33 (ref null $recBox))
    (local $t.37 eqref)
    (local $t.38 eqref)
    call $wasm/core.init
    call $descriptors
    call $writer.init
    call $conv.init
    call $string.init
    i32.const 0
    i64.const 2
    call $boxInt
    array.new_fixed $slots 1
    struct.new $tuple
    local.set $v
    i32.const 0
    i32.const 1
    array.new_default $slots
    local.tee $t
    i32.const 0
    local.get $v
    ref.cast (ref $tuple)
    struct.get $tuple $slots
    i32.const 0
    i32.const 1
    array.copy $slots $slots
    local.get $t
    ref.as_non_null
    i32.const 0
    struct.new $option
    local.set $v
    i32.const 0
    i64.const 5
    call $boxInt
    array.new_fixed $slots 1
    struct.new $tuple
    local.set $v.2
    i32.const 0
    i32.const 1
    array.new_default $slots
    local.tee $t
    i32.const 0
    local.get $v.2
    ref.cast (ref $tuple)
    struct.get $tuple $slots
    i32.const 0
    i32.const 1
    array.copy $slots $slots
    local.get $t
    ref.as_non_null
    i32.const 3
    struct.new $option
    local.set $v.2
    i32.const 0
    array.new_fixed $slots 0
    i32.const 1
    struct.new $option
    local.set $v.4
    i32.const 0
    i64.const 7
    call $boxInt
    i64.const 1000000000000
    call $boxInt
    array.new_fixed $slots 2
    struct.new $tuple
    local.set $v.5
    i32.const 0
    i32.const 2
    array.new_default $slots
    local.tee $t
    i32.const 0
    local.get $v.5
    ref.cast (ref $tuple)
    struct.get $tuple $slots
    i32.const 0
    i32.const 2
    array.copy $slots $slots
    local.get $t
    ref.as_non_null
    i32.const 2
    struct.new $option
    local.set $v.5
    i32.const 0
    local.get $v
    local.get $v.2
    local.get $v.4
    local.get $v.5
    array.new_fixed $slots 4
    struct.new $array
    local.set $v
    local.get $v
    ref.cast (ref $array)
    struct.get $array $elems
    array.len
    i64.extend_i32_u
    local.set $v.7
    local.get $v.7
    i64.const 1
    i64.sub
    local.set $v.7
    i64.const 0
    local.set $i
    local.get $i
    local.get $v.7
    i64.le_s
    local.set $v.9
    local.get $v.9
    if
      block $L1.exit
        loop $L1
          local.get $i
          local.set $i.1
          local.get $i.1
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
            i32.const 114
            i32.const 280
            i32.const 114
            array.new_data $bytes $strings
            struct.new $string
            i32.const 0
            i32.const 0
            i32.const 394
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
          local.get $i.1
          i32.wrap_i64
          array.get $slots
          local.set $v.2
          block $inlined1.after
            block $inlined1 (result i64)
              local.get $v.2
              block (type 53)
                br_on_cast 0 eqref (ref $option)
                drop
                i32.const 0
                i32.const 51
                i32.const 394
                i32.const 51
                array.new_data $bytes $strings
                struct.new $string
                i32.const 1
                call $fatal
                unreachable
              end
              local.set $t.3
              block
                block
                  block
                    block
                      block
                        block
                          local.get $t.3
                          struct.get $option $tag
                          br_table 0 3 2 1 4
                        end
                        local.get $t.3
                        local.set $v.2
                        local.get $v.2
                        ref.cast (ref $tuple)
                        struct.get $tuple $slots
                        i32.const 0
                        array.get $slots
                        call $unboxInt
                        local.set $i.1
                        local.get $v.2
                        ref.cast (ref $tuple)
                        struct.get $tuple $slots
                        i32.const 0
                        array.get $slots
                        call $unboxInt
                        local.set $v.12
                        local.get $i.1
                        local.get $v.12
                        i64.mul
                        local.set $i.1
                        i64.const 3
                        local.get $i.1
                        i64.mul
                        local.set $i.1
                        local.get $i.1
                        br $inlined1
                      end
                      local.get $t.3
                      local.set $v.2
                      local.get $v.2
                      ref.cast (ref $tuple)
                      struct.get $tuple $slots
                      i32.const 0
                      array.get $slots
                      call $unboxInt
                      local.set $i.1
                      local.get $v.2
                      ref.cast (ref $tuple)
                      struct.get $tuple $slots
                      i32.const 0
                      array.get $slots
                      call $unboxInt
                      local.set $v.12
                      local.get $i.1
                      local.get $v.12
                      i64.mul
                      local.set $i.1
                      local.get $i.1
                      br $inlined1
                    end
                    local.get $t.3
                    local.set $v.2
                    local.get $v.2
                    ref.cast (ref $tuple)
                    struct.get $tuple $slots
                    i32.const 0
                    array.get $slots
                    call $unboxInt
                    local.set $i.1
                    local.get $v.2
                    ref.cast (ref $tuple)
                    struct.get $tuple $slots
                    i32.const 1
                    array.get $slots
                    call $unboxInt
                    local.set $v.12
                    local.get $i.1
                    local.get $v.12
                    i64.add
                    local.set $i.1
                    local.get $i.1
                    br $inlined1
                  end
                  i64.const 0
                  br $inlined1
                end
                global.get $variant.tagMismatch
                i32.const 0
                ref.i31
                i32.const 0
                i32.const 0
                i32.const 445
                i32.const 0
                array.new_data $bytes $strings
                struct.new $string
                i32.const 0
                i32.const 0
                i32.const 445
                i32.const 0
                array.new_data $bytes $strings
                struct.new $string
                i32.const 0
                ref.null none
                call $raise
                unreachable
              end
              br $inlined1.after
            end
            local.set $i.1
            local.get $i.1
            call $convInt
            local.set $v.2
            i32.const 1
            ref.i31
            local.set $v.4
            local.get $v.2
            i32.const 0
            i32.const 1
            i32.const 445
            i32.const 1
            array.new_data $bytes $strings
            struct.new $string
            call $concat
            local.set $v.2
            local.get $v.4
            local.get $v.2
            call $putString
            local.set $v.2
            local.get $i
            local.get $v.7
            i64.eq
            local.set $v.9
            local.get $v.9
            if
              br $L1.exit
            else
            end
            local.get $i
            i64.const 1
            i64.add
            local.set $i.1
            local.get $i.1
            local.set $i
          end
          br $L1
        end
      end
    else
    end
    i64.const 3
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
      i32.const 114
      i32.const 446
      i32.const 114
      array.new_data $bytes $strings
      struct.new $string
      i32.const 0
      i32.const 0
      i32.const 560
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
    i64.const 3
    i32.wrap_i64
    array.get $slots
    local.set $v.2
    local.get $v.2
    block (type 53)
      br_on_cast 0 eqref (ref $option)
      drop
      i32.const 0
      i32.const 51
      i32.const 560
      i32.const 51
      array.new_data $bytes $strings
      struct.new $string
      i32.const 1
      call $fatal
      unreachable
    end
    struct.get $option $tag
    i32.const 2
    i32.ne
    if
      global.get $variant.tagMismatch
      i32.const 0
      ref.i31
      i32.const 0
      i32.const 114
      i32.const 611
      i32.const 114
      array.new_data $bytes $strings
      struct.new $string
      i32.const 0
      i32.const 0
      i32.const 725
      i32.const 0
      array.new_data $bytes $strings
      struct.new $string
      i32.const 0
      ref.null none
      call $raise
      unreachable
    end
    i32.const 0
    i32.const 3
    array.new_default $slots
    local.set $t
    local.get $t
    i32.const 0
    i32.const 3
    ref.i31
    array.set $slots
    local.get $t
    i32.const 1
    local.get $v.2
    block (type 53)
      br_on_cast 0 eqref (ref $option)
      drop
      i32.const 0
      i32.const 51
      i32.const 725
      i32.const 51
      array.new_data $bytes $strings
      struct.new $string
      i32.const 1
      call $fatal
      unreachable
    end
    struct.get $option $slots
    i32.const 0
    i32.const 2
    array.copy $slots $slots
    local.get $t
    ref.as_non_null
    struct.new $tuple
    local.set $v.2
    local.get $v.2
    ref.cast (ref $tuple)
    struct.get $tuple $slots
    i32.const 1
    array.get $slots
    call $unboxInt
    local.set $v.7
    local.get $v.7
    call $convInt
    local.set $v.4
    local.get $v.2
    ref.cast (ref $tuple)
    struct.get $tuple $slots
    i32.const 2
    array.get $slots
    call $unboxInt
    local.set $v.7
    local.get $v.7
    call $convInt
    local.set $v.2
    i32.const 0
    i32.const 1
    i32.const 776
    i32.const 1
    array.new_data $bytes $strings
    struct.new $string
    local.get $v.2
    call $concat
    local.set $v.2
    local.get $v.4
    local.get $v.2
    call $concat
    local.set $v.2
    i32.const 1
    ref.i31
    local.set $v.4
    local.get $v.2
    i32.const 0
    i32.const 1
    i32.const 777
    i32.const 1
    array.new_data $bytes $strings
    struct.new $string
    call $concat
    local.set $v.2
    local.get $v.4
    local.get $v.2
    call $putString
    local.set $v.2
    i64.const 2
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
      i32.const 114
      i32.const 778
      i32.const 114
      array.new_data $bytes $strings
      struct.new $string
      i32.const 0
      i32.const 0
      i32.const 892
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
    i64.const 2
    i32.wrap_i64
    array.get $slots
    local.set $v.2
    i32.const 0
    array.new_fixed $slots 0
    i32.const 1
    struct.new $option
    local.set $v.4
    local.get $v.2
    local.set $v.2
    local.get $v.4
    local.set $v.4
    local.get $v.2
    local.get $v.4
    ref.eq
    if (result i32)
      i32.const 1
    else
      local.get $v.2
      ref.cast (ref $option)
      struct.get $option $tag
      local.tee $v.9
      local.get $v.4
      ref.cast (ref $option)
      struct.get $option $tag
      i32.eq
      if (result i32)
        local.get $v.9
        local.set $v.9
        block (result i32)
          block
            block
              block
                block
                  local.get $v.9
                  br_table 0 1 2 3 3
                end
                i32.const 0
                br 3
              end
              i32.const 1
              br 2
            end
            i32.const 0
            br 1
          end
          i32.const 0
          br 0
        end
      else
        i32.const 0
      end
    end
    local.set $v.9
    global.get $noClosure
    local.get $v.9
    call $conv.bool
    local.set $v.2
    i64.const 0
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
      i32.const 114
      i32.const 892
      i32.const 114
      array.new_data $bytes $strings
      struct.new $string
      i32.const 0
      i32.const 0
      i32.const 1006
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
    i64.const 0
    i32.wrap_i64
    array.get $slots
    local.set $v.4
    local.get $v.4
    block (type 53)
      br_on_cast 0 eqref (ref $option)
      drop
      i32.const 0
      i32.const 51
      i32.const 1006
      i32.const 51
      array.new_data $bytes $strings
      struct.new $string
      i32.const 1
      call $fatal
      unreachable
    end
    struct.get $option $tag
    i32.const 0
    i32.eq
    local.set $v.9
    global.get $noClosure
    local.get $v.9
    call $conv.bool
    local.set $v.4
    i64.const 1
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
      i32.const 114
      i32.const 1057
      i32.const 114
      array.new_data $bytes $strings
      struct.new $string
      i32.const 0
      i32.const 0
      i32.const 1171
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
    i64.const 1
    i32.wrap_i64
    array.get $slots
    local.set $v.5
    local.get $v.5
    block (type 53)
      br_on_cast 0 eqref (ref $option)
      drop
      i32.const 0
      i32.const 51
      i32.const 1171
      i32.const 51
      array.new_data $bytes $strings
      struct.new $string
      i32.const 1
      call $fatal
      unreachable
    end
    struct.get $option $tag
    local.set $v.9
    block (result i32)
      block
        block
          block
            block
              local.get $v.9
              br_table 0 1 2 3 3
            end
            i32.const 0
            br 3
          end
          i32.const 2
          br 2
        end
        i32.const 3
        br 1
      end
      i32.const 1
      br 0
    end
    i64.extend_i32_u
    local.set $v.7
    local.get $v.7
    call $convInt
    local.set $v.5
    i64.const 0
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
      i32.const 114
      i32.const 1222
      i32.const 114
      array.new_data $bytes $strings
      struct.new $string
      i32.const 0
      i32.const 0
      i32.const 1336
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
    i64.const 0
    i32.wrap_i64
    array.get $slots
    local.set $v.48
    i64.const 1
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
      i32.const 114
      i32.const 1336
      i32.const 114
      array.new_data $bytes $strings
      struct.new $string
      i32.const 0
      i32.const 0
      i32.const 1450
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
    i64.const 1
    i32.wrap_i64
    array.get $slots
    local.set $v
    local.get $v.48
    local.set $v.48
    local.get $v
    local.set $v
    local.get $v.48
    local.get $v
    ref.eq
    if (result i32)
      i32.const 1
    else
      local.get $v.48
      ref.cast (ref $option)
      struct.get $option $tag
      local.tee $v.9
      local.get $v
      ref.cast (ref $option)
      struct.get $option $tag
      i32.eq
      if (result i32)
        local.get $v.9
        local.set $v.9
        block (result i32)
          block
            block
              block
                block
                  local.get $v.9
                  br_table 0 1 2 3 3
                end
                i32.const 0
                br 3
              end
              i32.const 1
              br 2
            end
            i32.const 0
            br 1
          end
          i32.const 0
          br 0
        end
      else
        i32.const 0
      end
    end
    local.set $v.9
    global.get $noClosure
    local.get $v.9
    call $conv.bool
    local.set $v
    i32.const 0
    i32.const 1
    i32.const 1450
    i32.const 1
    array.new_data $bytes $strings
    struct.new $string
    local.get $v
    call $concat
    local.set $v
    local.get $v.5
    local.get $v
    call $concat
    local.set $v
    i32.const 0
    i32.const 1
    i32.const 1451
    i32.const 1
    array.new_data $bytes $strings
    struct.new $string
    local.get $v
    call $concat
    local.set $v
    local.get $v.4
    local.get $v
    call $concat
    local.set $v
    i32.const 0
    i32.const 1
    i32.const 1452
    i32.const 1
    array.new_data $bytes $strings
    struct.new $string
    local.get $v
    call $concat
    local.set $v
    local.get $v.2
    local.get $v
    call $concat
    local.set $v
    i32.const 1
    ref.i31
    local.set $v.2
    local.get $v
    i32.const 0
    i32.const 1
    i32.const 1453
    i32.const 1
    array.new_data $bytes $strings
    struct.new $string
    call $concat
    local.set $v
    local.get $v.2
    local.get $v
    call $putString
    local.set $v
    i32.const 0
    i64.const 2
    i64.const 3
    i64.lt_u
    i32.eqz
    if
      i32.const 0
      i32.const 15
      i32.const 1454
      i32.const 15
      array.new_data $bytes $strings
      struct.new $string
      i64.const 2
      call $decimal
      call $concat
      i32.const 0
      i32.const 154
      i32.const 1469
      i32.const 154
      array.new_data $bytes $strings
      struct.new $string
      call $concat
      i32.const 1
      call $fatal
      unreachable
    end
    array.new_fixed $slots 0
    i64.const 2
    i32.wrap_i64
    local.set $v.9
    block (result i32)
      block
        block
          block
            local.get $v.9
            br_table 0 1 2 2
          end
          i32.const 2
          br 2
        end
        i32.const 0
        br 1
      end
      i32.const 1
      br 0
    end
    struct.new $option
    local.set $v
    local.get $v
    block (type 53)
      br_on_cast 0 eqref (ref $option)
      drop
      i32.const 0
      i32.const 51
      i32.const 1623
      i32.const 51
      array.new_data $bytes $strings
      struct.new $string
      i32.const 1
      call $fatal
      unreachable
    end
    struct.get $option $tag
    i32.const 1
    i32.eq
    local.set $v.9
    global.get $noClosure
    local.get $v.9
    call $conv.bool
    local.set $v.2
    local.get $v
    block (type 53)
      br_on_cast 0 eqref (ref $option)
      drop
      i32.const 0
      i32.const 51
      i32.const 1674
      i32.const 51
      array.new_data $bytes $strings
      struct.new $string
      i32.const 1
      call $fatal
      unreachable
    end
    struct.get $option $tag
    local.set $v.9
    block (result i32)
      block
        block
          block
            local.get $v.9
            br_table 0 1 2 2
          end
          i32.const 1
          br 2
        end
        i32.const 2
        br 1
      end
      i32.const 0
      br 0
    end
    i64.extend_i32_u
    local.set $v.7
    local.get $v.7
    call $convInt
    local.set $v
    i32.const 0
    i32.const 1
    i32.const 1725
    i32.const 1
    array.new_data $bytes $strings
    struct.new $string
    local.get $v
    call $concat
    local.set $v
    local.get $v.2
    local.get $v
    call $concat
    local.set $v
    i32.const 1
    ref.i31
    local.set $v.2
    local.get $v
    i32.const 0
    i32.const 1
    i32.const 1726
    i32.const 1
    array.new_data $bytes $strings
    struct.new $string
    call $concat
    local.set $v
    local.get $v.2
    local.get $v
    call $putString
    local.set $v
    i32.const 0
    i64.const 4
    call $boxInt
    array.new_fixed $slots 1
    struct.new $tuple
    local.set $v
    i32.const 0
    i32.const 1
    array.new_default $slots
    local.tee $t
    i32.const 0
    local.get $v
    ref.cast (ref $tuple)
    struct.get $tuple $slots
    i32.const 0
    i32.const 1
    array.copy $slots $slots
    local.get $t
    ref.as_non_null
    i32.const 1
    struct.new $option
    local.set $v
    i32.const 0
    i64.const 4
    call $boxInt
    array.new_fixed $slots 1
    struct.new $tuple
    local.set $v.2
    i32.const 0
    i32.const 1
    array.new_default $slots
    local.tee $t
    i32.const 0
    local.get $v.2
    ref.cast (ref $tuple)
    struct.get $tuple $slots
    i32.const 0
    i32.const 1
    array.copy $slots $slots
    local.get $t
    ref.as_non_null
    i32.const 1
    struct.new $option
    local.set $v.2
    i32.const 0
    i64.const 5
    call $boxInt
    array.new_fixed $slots 1
    struct.new $tuple
    local.set $v.4
    i32.const 0
    i32.const 1
    array.new_default $slots
    local.tee $t
    i32.const 0
    local.get $v.4
    ref.cast (ref $tuple)
    struct.get $tuple $slots
    i32.const 0
    i32.const 1
    array.copy $slots $slots
    local.get $t
    ref.as_non_null
    i32.const 1
    struct.new $option
    local.set $v.4
    local.get $v
    local.set $v.5
    local.get $v.2
    local.set $v.2
    local.get $v.5
    local.get $v.2
    ref.eq
    if (result i32)
      i32.const 1
    else
      local.get $v.5
      ref.cast (ref $option)
      struct.get $option $tag
      local.tee $v.9
      local.get $v.2
      ref.cast (ref $option)
      struct.get $option $tag
      i32.eq
      if (result i32)
        local.get $v.9
        local.set $t.22
        block (result i32)
          block
            block
              local.get $t.22
              br_table 0 1 1
            end
            i32.const 1
            br 1
          end
          i32.const 0
          br 0
        end
        local.get $v.9
        i32.const 1
        i32.eq
        if (result i32)
          local.get $v.5
          ref.cast (ref $option)
          struct.get $option $slots
          i32.const 0
          array.get $slots
          local.get $v.2
          ref.cast (ref $option)
          struct.get $option $slots
          i32.const 0
          array.get $slots
          local.set $v.2
          local.set $v.5
          local.get $v.5
          call $unboxInt
          local.get $v.2
          call $unboxInt
          i64.eq
        else
          i32.const 0
        end
        i32.or
      else
        i32.const 0
      end
    end
    local.set $v.9
    global.get $noClosure
    local.get $v.9
    call $conv.bool
    local.set $v.2
    local.get $v
    local.set $v
    local.get $v.4
    local.set $v.4
    local.get $v
    local.get $v.4
    ref.eq
    if (result i32)
      i32.const 1
    else
      local.get $v
      ref.cast (ref $option)
      struct.get $option $tag
      local.tee $v.9
      local.get $v.4
      ref.cast (ref $option)
      struct.get $option $tag
      i32.eq
      if (result i32)
        local.get $v.9
        local.set $t.22
        block (result i32)
          block
            block
              local.get $t.22
              br_table 0 1 1
            end
            i32.const 1
            br 1
          end
          i32.const 0
          br 0
        end
        local.get $v.9
        i32.const 1
        i32.eq
        if (result i32)
          local.get $v
          ref.cast (ref $option)
          struct.get $option $slots
          i32.const 0
          array.get $slots
          local.get $v.4
          ref.cast (ref $option)
          struct.get $option $slots
          i32.const 0
          array.get $slots
          local.set $v
          local.set $v.4
          local.get $v.4
          call $unboxInt
          local.get $v
          call $unboxInt
          i64.eq
        else
          i32.const 0
        end
        i32.or
      else
        i32.const 0
      end
    end
    local.set $v.9
    global.get $noClosure
    local.get $v.9
    call $conv.bool
    local.set $v
    i32.const 0
    i32.const 1
    i32.const 1727
    i32.const 1
    array.new_data $bytes $strings
    struct.new $string
    local.get $v
    call $concat
    local.set $v
    local.get $v.2
    local.get $v
    call $concat
    local.set $v
    i32.const 1
    ref.i31
    local.set $v.2
    local.get $v
    i32.const 0
    i32.const 1
    i32.const 1728
    i32.const 1
    array.new_data $bytes $strings
    struct.new $string
    call $concat
    local.set $v
    local.get $v.2
    local.get $v
    call $putString
    local.set $v
    i32.const 0
    i32.const 3
    i32.const 1729
    i32.const 3
    array.new_data $bytes $strings
    struct.new $string
    local.set $v
    i32.const 0
    i64.const 1
    call $boxInt
    local.get $v
    i32.const 99
    ref.i31
    array.new_fixed $slots 3
    struct.new $tuple
    local.set $v
    local.get $v
    ref.cast (ref $tuple)
    struct.get $tuple $slots
    i32.const 1
    array.get $slots
    local.set $v.2
    local.get $v.2
    i32.const 0
    i32.const 1
    i32.const 1732
    i32.const 1
    array.new_data $bytes $strings
    struct.new $string
    call $concat
    local.set $v.2
    local.get $v
    ref.cast (ref $tuple)
    struct.get $tuple $slots
    i32.const 1
    local.get $v.2
    array.set $slots
    i64.const 1
    call $convInt
    local.set $v.2
    local.get $v
    ref.cast (ref $tuple)
    struct.get $tuple $slots
    i32.const 1
    array.get $slots
    local.set $v
    i32.const 0
    i32.const 1
    i32.const 1733
    i32.const 1
    array.new_data $bytes $strings
    struct.new $string
    i32.const 99
    call $convChar
    i32.const 39
    call $escaped
    call $concat
    i32.const 0
    i32.const 1
    i32.const 1734
    i32.const 1
    array.new_data $bytes $strings
    struct.new $string
    call $concat
    local.set $v.4
    local.get $v
    local.get $v.4
    call $concat
    local.set $v
    local.get $v.2
    local.get $v
    call $concat
    local.set $v
    i32.const 1
    ref.i31
    local.set $v.2
    local.get $v
    i32.const 0
    i32.const 1
    i32.const 1735
    i32.const 1
    array.new_data $bytes $strings
    struct.new $string
    call $concat
    local.set $v
    local.get $v.2
    local.get $v
    call $putString
    local.set $v
    global.get $noClosure
    global.set $divide.1
    global.get $noClosure
    i64.const 47
    i64.const 5
    call $divide
    local.set $v.7
    local.set $i
    global.get $noClosure
    i64.const 100
    i64.const 7
    call $divide
    local.set $i.1
    local.set $v.12
    local.get $i
    local.set $i
    local.get $i
    call $convInt
    local.set $v
    local.get $v.7
    local.set $v.7
    local.get $v.7
    call $convInt
    local.set $v.2
    local.get $v.12
    local.set $v.7
    local.get $v.7
    call $convInt
    local.set $v.4
    local.get $i.1
    local.set $v.7
    local.get $v.7
    call $convInt
    local.set $v.5
    i32.const 0
    i32.const 1
    i32.const 1736
    i32.const 1
    array.new_data $bytes $strings
    struct.new $string
    local.get $v.5
    call $concat
    local.set $v.5
    local.get $v.4
    local.get $v.5
    call $concat
    local.set $v.4
    i32.const 0
    i32.const 1
    i32.const 1737
    i32.const 1
    array.new_data $bytes $strings
    struct.new $string
    local.get $v.4
    call $concat
    local.set $v.4
    local.get $v.2
    local.get $v.4
    call $concat
    local.set $v.2
    i32.const 0
    i32.const 1
    i32.const 1738
    i32.const 1
    array.new_data $bytes $strings
    struct.new $string
    local.get $v.2
    call $concat
    local.set $v.2
    local.get $v
    local.get $v.2
    call $concat
    local.set $v
    i32.const 1
    ref.i31
    local.set $v.2
    local.get $v
    i32.const 0
    i32.const 1
    i32.const 1739
    i32.const 1
    array.new_data $bytes $strings
    struct.new $string
    call $concat
    local.set $v
    local.get $v.2
    local.get $v
    call $putString
    local.set $v
    i64.const 5
    i64.const 0
    i64.lt_s
    if
      global.get $arrayOp.error
      i32.const 0
      ref.i31
      i32.const 0
      i32.const 113
      i32.const 1740
      i32.const 113
      array.new_data $bytes $strings
      struct.new $string
      i32.const 0
      i32.const 0
      i32.const 1853
      i32.const 0
      array.new_data $bytes $strings
      struct.new $string
      i32.const 0
      ref.null none
      call $raise
      unreachable
    end
    i64.const 5
    i64.const 134217720
    i64.gt_s
    if
      i32.const 0
      i32.const 63
      i32.const 1853
      i32.const 63
      array.new_data $bytes $strings
      struct.new $string
      i32.const 70
      call $fatal
      unreachable
    end
    i32.const 0
    i64.const 0
    call $boxInt
    i64.const 5
    i32.wrap_i64
    array.new $slots
    struct.new $array
    local.set $v
    i64.const 0
    local.set $v.7
    local.get $v.7
    i64.const 4
    i64.le_s
    local.set $v.9
    local.get $v.9
    if
      block $L2.exit
        loop $L2
          local.get $v.7
          local.set $i
          local.get $i
          local.get $i
          i64.mul
          local.set $i.1
          local.get $i
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
            i32.const 114
            i32.const 1916
            i32.const 114
            array.new_data $bytes $strings
            struct.new $string
            i32.const 0
            i32.const 0
            i32.const 2030
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
          local.get $i
          i32.wrap_i64
          local.get $i.1
          call $boxInt
          array.set $slots
          local.get $v.7
          i64.const 4
          i64.eq
          local.set $v.9
          local.get $v.9
          if
            br $L2.exit
          else
          end
          local.get $v.7
          i64.const 1
          i64.add
          local.set $i
          local.get $i
          local.set $v.7
          br $L2
        end
      end
    else
    end
    i64.const 4
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
      i32.const 114
      i32.const 2030
      i32.const 114
      array.new_data $bytes $strings
      struct.new $string
      i32.const 0
      i32.const 0
      i32.const 2144
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
    i64.const 4
    i32.wrap_i64
    array.get $slots
    call $unboxInt
    local.set $v.7
    local.get $v.7
    call $convInt
    local.set $v.2
    local.get $v
    ref.cast (ref $array)
    struct.get $array $elems
    array.len
    i64.extend_i32_u
    local.set $v.7
    local.get $v.7
    call $convInt
    local.set $v.4
    i32.const 0
    i32.const 1
    i32.const 2144
    i32.const 1
    array.new_data $bytes $strings
    struct.new $string
    local.get $v.4
    call $concat
    local.set $v.4
    local.get $v.2
    local.get $v.4
    call $concat
    local.set $v.2
    i32.const 1
    ref.i31
    local.set $v.4
    local.get $v.2
    i32.const 0
    i32.const 1
    i32.const 2145
    i32.const 1
    array.new_data $bytes $strings
    struct.new $string
    call $concat
    local.set $v.2
    local.get $v.4
    local.get $v.2
    call $putString
    local.set $v.2
    i64.const 3
    i32.const 120
    call $stringNew
    local.set $v.2
    local.get $v.2
    i64.const 1
    i32.const 121
    call $stringSetChar
    drop
    i32.const 0
    i32.const 6
    i32.const 2146
    i32.const 6
    array.new_data $bytes $strings
    struct.new $string
    i64.const 2
    i64.const 3
    call $stringGetSub
    local.set $v.4
    i32.const 0
    i32.const 2
    i32.const 2152
    i32.const 2
    array.new_data $bytes $strings
    struct.new $string
    i32.const 0
    i32.const 2
    i32.const 2154
    i32.const 2
    array.new_data $bytes $strings
    struct.new $string
    call $stringEqual
    local.set $v.9
    global.get $noClosure
    local.get $v.9
    call $conv.bool
    local.set $v.5
    i32.const 0
    i32.const 3
    i32.const 2156
    i32.const 3
    array.new_data $bytes $strings
    struct.new $string
    i64.const 2
    call $stringGetChar
    local.set $v.9
    i32.const 0
    i32.const 1
    i32.const 2159
    i32.const 1
    array.new_data $bytes $strings
    struct.new $string
    local.get $v.9
    call $convChar
    i32.const 39
    call $escaped
    call $concat
    i32.const 0
    i32.const 1
    i32.const 2160
    i32.const 1
    array.new_data $bytes $strings
    struct.new $string
    call $concat
    local.set $v.48
    i32.const 0
    i32.const 1
    i32.const 2161
    i32.const 1
    array.new_data $bytes $strings
    struct.new $string
    local.get $v.48
    call $concat
    local.set $v.48
    local.get $v.5
    local.get $v.48
    call $concat
    local.set $v.5
    i32.const 0
    i32.const 1
    i32.const 2162
    i32.const 1
    array.new_data $bytes $strings
    struct.new $string
    local.get $v.5
    call $concat
    local.set $v.5
    local.get $v.4
    local.get $v.5
    call $concat
    local.set $v.4
    i32.const 0
    i32.const 1
    i32.const 2163
    i32.const 1
    array.new_data $bytes $strings
    struct.new $string
    local.get $v.4
    call $concat
    local.set $v.4
    local.get $v.2
    local.get $v.4
    call $concat
    local.set $v.2
    i32.const 1
    ref.i31
    local.set $v.4
    local.get $v.2
    i32.const 0
    i32.const 1
    i32.const 2164
    i32.const 1
    array.new_data $bytes $strings
    struct.new $string
    call $concat
    local.set $v.2
    local.get $v.4
    local.get $v.2
    call $putString
    local.set $v.2
    i32.const 0
    ref.null none
    i32.const 0
    i32.const 1
    i32.const 2165
    i32.const 1
    array.new_data $bytes $strings
    struct.new $string
    i64.const 3
    call $boxInt
    i64.const 4
    call $boxInt
    array.new_fixed $slots 3
    struct.new $record
    global.get $dict
    local.set $v.2
    ref.cast (ref $record)
    local.get $v.2
    ref.cast (ref $dict)
    struct.new $recBox
    local.set $v.2
    local.get $v.2
    ref.cast (ref $recBox)
    local.tee $t.33
    struct.get $recBox $payload
    local.get $t.33
    struct.get $recBox $dict
    local.set $v.4
    local.set $v.5
    local.get $v.5
    local.get $v.4
    local.set $v.48
    ref.cast (ref $record)
    struct.get $record $slots
    local.get $v.48
    ref.cast (ref $dict)
    struct.get $dict $indices
    i32.const 2
    array.get $i32s
    array.get $slots
    call $unboxInt
    local.set $v.7
    local.get $v.7
    i64.const 10
    i64.add
    local.set $v.7
    local.get $v.5
    local.get $v.4
    local.set $v.48
    ref.cast (ref $record)
    struct.get $record $slots
    local.get $v.48
    ref.cast (ref $dict)
    struct.get $dict $indices
    i32.const 2
    array.get $i32s
    local.get $v.7
    call $boxInt
    array.set $slots
    local.get $v.5
    local.get $v.4
    local.set $v.48
    ref.cast (ref $record)
    struct.get $record $slots
    local.get $v.48
    ref.cast (ref $dict)
    struct.get $dict $indices
    i32.const 0
    array.get $i32s
    array.get $slots
    local.set $v.48
    local.get $v.5
    local.get $v.4
    local.set $t.37
    ref.cast (ref $record)
    struct.get $record $slots
    local.get $t.37
    ref.cast (ref $dict)
    struct.get $dict $indices
    i32.const 1
    array.get $i32s
    array.get $slots
    call $unboxInt
    local.set $v.7
    local.get $v.7
    call $convInt
    local.set $t.37
    local.get $v.5
    local.get $v.4
    local.set $t.38
    ref.cast (ref $record)
    struct.get $record $slots
    local.get $t.38
    ref.cast (ref $dict)
    struct.get $dict $indices
    i32.const 2
    array.get $i32s
    array.get $slots
    call $unboxInt
    local.set $v.7
    local.get $v.7
    call $convInt
    local.set $t.38
    i32.const 0
    i32.const 1
    i32.const 2166
    i32.const 1
    array.new_data $bytes $strings
    struct.new $string
    local.get $t.38
    call $concat
    local.set $t.38
    local.get $t.37
    local.get $t.38
    call $concat
    local.set $t.37
    i32.const 0
    i32.const 1
    i32.const 2167
    i32.const 1
    array.new_data $bytes $strings
    struct.new $string
    local.get $t.37
    call $concat
    local.set $t.37
    local.get $v.48
    local.get $t.37
    call $concat
    local.set $v.48
    i32.const 1
    ref.i31
    local.set $t.37
    local.get $v.48
    i32.const 0
    i32.const 1
    i32.const 2168
    i32.const 1
    array.new_data $bytes $strings
    struct.new $string
    call $concat
    local.set $v.48
    local.get $t.37
    local.get $v.48
    call $putString
    local.set $v.48
    i32.const 0
    ref.null none
    i32.const 0
    i32.const 1
    i32.const 2169
    i32.const 1
    array.new_data $bytes $strings
    struct.new $string
    i64.const 1
    call $boxInt
    i64.const 1
    call $boxInt
    array.new_fixed $slots 3
    struct.new $record
    global.get $dict
    local.set $v.48
    ref.cast (ref $record)
    local.get $v.48
    ref.cast (ref $dict)
    struct.new $recBox
    local.set $v.48
    local.get $v.48
    ref.cast (ref $recBox)
    local.tee $t.33
    struct.get $recBox $payload
    local.get $t.33
    struct.get $recBox $dict
    local.set $t.37
    local.set $t.37
    i32.const 0
    local.get $v.2
    local.get $v.48
    array.new_fixed $slots 2
    struct.new $array
    local.set $v.2
    i64.const 1
    local.get $v.2
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
      i32.const 113
      i32.const 2170
      i32.const 113
      array.new_data $bytes $strings
      struct.new $string
      i32.const 0
      i32.const 0
      i32.const 2283
      i32.const 0
      array.new_data $bytes $strings
      struct.new $string
      i32.const 0
      ref.null none
      call $raise
      unreachable
    end
    local.get $v.2
    ref.cast (ref $array)
    struct.get $array $elems
    i64.const 1
    i32.wrap_i64
    array.get $slots
    local.set $v.48
    local.get $v.48
    ref.cast (ref $recBox)
    local.tee $t.33
    struct.get $recBox $payload
    local.get $t.33
    struct.get $recBox $dict
    local.set $v.48
    local.set $t.37
    local.get $t.37
    local.get $v.48
    local.set $v.48
    ref.cast (ref $record)
    struct.get $record $slots
    local.get $v.48
    ref.cast (ref $dict)
    struct.get $dict $indices
    i32.const 0
    array.get $i32s
    array.get $slots
    local.set $v.48
    i64.const 1
    local.get $v.2
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
      i32.const 114
      i32.const 2283
      i32.const 114
      array.new_data $bytes $strings
      struct.new $string
      i32.const 0
      i32.const 0
      i32.const 2397
      i32.const 0
      array.new_data $bytes $strings
      struct.new $string
      i32.const 0
      ref.null none
      call $raise
      unreachable
    end
    local.get $v.2
    ref.cast (ref $array)
    struct.get $array $elems
    i64.const 1
    i32.wrap_i64
    array.get $slots
    local.set $v.2
    local.get $v.2
    ref.cast (ref $recBox)
    local.tee $t.33
    struct.get $recBox $payload
    local.get $t.33
    struct.get $recBox $dict
    local.set $v.2
    local.set $t.37
    local.get $t.37
    local.get $v.2
    local.set $v.2
    local.set $t.37
    local.get $t.37
    local.get $v.2
    local.set $t.38
    ref.cast (ref $record)
    struct.get $record $slots
    local.get $t.38
    ref.cast (ref $dict)
    struct.get $dict $indices
    i32.const 1
    array.get $i32s
    array.get $slots
    call $unboxInt
    local.set $v.7
    local.get $t.37
    local.get $v.2
    local.set $t.38
    ref.cast (ref $record)
    struct.get $record $slots
    local.get $t.38
    ref.cast (ref $dict)
    struct.get $dict $indices
    i32.const 1
    array.get $i32s
    array.get $slots
    call $unboxInt
    local.set $i
    local.get $t.37
    local.get $v.2
    local.set $t.38
    ref.cast (ref $record)
    struct.get $record $slots
    local.get $t.38
    ref.cast (ref $dict)
    struct.get $dict $indices
    i32.const 2
    array.get $i32s
    array.get $slots
    call $unboxInt
    local.set $i.1
    local.get $t.37
    local.get $v.2
    local.set $v.2
    ref.cast (ref $record)
    struct.get $record $slots
    local.get $v.2
    ref.cast (ref $dict)
    struct.get $dict $indices
    i32.const 2
    array.get $i32s
    array.get $slots
    call $unboxInt
    local.set $v.12
    local.get $i.1
    local.get $v.12
    i64.mul
    local.set $i.1
    local.get $i
    local.get $i.1
    i64.add
    local.set $i
    local.get $v.7
    local.get $i
    i64.mul
    local.set $v.7
    local.get $v.7
    call $convInt
    local.set $v.2
    local.get $v.5
    local.get $v.4
    local.set $t.37
    ref.cast (ref $record)
    struct.get $record $slots
    local.get $t.37
    ref.cast (ref $dict)
    struct.get $dict $indices
    i32.const 1
    array.get $i32s
    array.get $slots
    call $unboxInt
    local.set $v.7
    local.get $v.5
    local.get $v.4
    local.set $t.37
    ref.cast (ref $record)
    struct.get $record $slots
    local.get $t.37
    ref.cast (ref $dict)
    struct.get $dict $indices
    i32.const 1
    array.get $i32s
    array.get $slots
    call $unboxInt
    local.set $i
    local.get $v.5
    local.get $v.4
    local.set $t.37
    ref.cast (ref $record)
    struct.get $record $slots
    local.get $t.37
    ref.cast (ref $dict)
    struct.get $dict $indices
    i32.const 2
    array.get $i32s
    array.get $slots
    call $unboxInt
    local.set $i.1
    local.get $v.5
    local.get $v.4
    local.set $t.37
    ref.cast (ref $record)
    struct.get $record $slots
    local.get $t.37
    ref.cast (ref $dict)
    struct.get $dict $indices
    i32.const 2
    array.get $i32s
    array.get $slots
    call $unboxInt
    local.set $v.12
    local.get $i.1
    local.get $v.12
    i64.mul
    local.set $i.1
    local.get $i
    local.get $i.1
    i64.add
    local.set $i
    local.get $v.7
    local.get $i
    i64.mul
    local.set $v.7
    local.get $v.7
    call $convInt
    local.set $t.37
    i32.const 0
    i32.const 1
    i32.const 2397
    i32.const 1
    array.new_data $bytes $strings
    struct.new $string
    local.get $t.37
    call $concat
    local.set $t.37
    local.get $v.2
    local.get $t.37
    call $concat
    local.set $v.2
    local.get $v.48
    local.get $v.2
    call $concat
    local.set $v.2
    i32.const 1
    ref.i31
    local.set $v.48
    local.get $v.2
    i32.const 0
    i32.const 1
    i32.const 2398
    i32.const 1
    array.new_data $bytes $strings
    struct.new $string
    call $concat
    local.set $v.2
    local.get $v.48
    local.get $v.2
    call $putString
    local.set $v.2
    local.get $v.5
    local.get $v.4
    local.set $v.2
    ref.cast (ref $record)
    struct.get $record $slots
    local.get $v.2
    ref.cast (ref $dict)
    struct.get $dict $indices
    i32.const 0
    array.get $i32s
    array.get $slots
    local.set $v.2
    i64.const 9
    call $convInt
    local.set $v.4
    local.get $v.2
    local.get $v.4
    call $concat
    local.set $v.2
    i32.const 1
    ref.i31
    local.set $v.4
    local.get $v.2
    i32.const 0
    i32.const 1
    i32.const 2399
    i32.const 1
    array.new_data $bytes $strings
    struct.new $string
    call $concat
    local.set $v.2
    local.get $v.4
    local.get $v.2
    call $putString
    local.set $v.2
    i64.const 5
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
      i32.const 114
      i32.const 2400
      i32.const 114
      array.new_data $bytes $strings
      struct.new $string
      i32.const 0
      i32.const 0
      i32.const 2514
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
    i64.const 5
    i32.wrap_i64
    array.get $slots
    call $unboxInt
    local.set $v.7
    local.get $v.7
    call $convInt
    local.set $v
    i32.const 1
    ref.i31
    local.set $v.2
    local.get $v
    i32.const 0
    i32.const 1
    i32.const 2514
    i32.const 1
    array.new_data $bytes $strings
    struct.new $string
    call $concat
    local.set $v
    local.get $v.2
    local.get $v
    call $putString
    local.set $v
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
  (func $descriptors (type 45)
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
    i64.const 10
    i32.const 0
    i32.const 41
    i32.const 0
    i32.const 41
    array.new_data $bytes $strings
    struct.new $string
    i64.const 3
    i64.const 0
    call $wasm/core.newDesc
    global.set $QRecord_name_String_x_Int_y_Int
    global.get $noClosure
    i64.const 9
    i32.const 0
    i32.const 16
    i32.const 41
    i32.const 16
    array.new_data $bytes $strings
    struct.new $string
    i64.const 1
    i64.const 0
    call $wasm/core.newDesc
    global.set $QTuple_Int_90c1d29a40761138
    global.get $noClosure
    i64.const 9
    i32.const 0
    i32.const 23
    i32.const 57
    i32.const 23
    array.new_data $bytes $strings
    struct.new $string
    i64.const 2
    i64.const 0
    call $wasm/core.newDesc
    global.set $QTuple_Int_Int_586d0a3b5f6d6e01
    global.get $noClosure
    i64.const 9
    i32.const 0
    i32.const 19
    i32.const 80
    i32.const 19
    array.new_data $bytes $strings
    struct.new $string
    i64.const 1
    i64.const 0
    call $wasm/core.newDesc
    global.set $QTuple_Int_bf55836b2befd5ab
    global.get $noClosure
    i64.const 9
    i32.const 0
    i32.const 16
    i32.const 99
    i32.const 16
    array.new_data $bytes $strings
    struct.new $string
    i64.const 1
    i64.const 0
    call $wasm/core.newDesc
    global.set $QTuple_Int_742e411bebefcd67
    global.get $noClosure
    i64.const 11
    i32.const 0
    i32.const 83
    i32.const 115
    i32.const 83
    array.new_data $bytes $strings
    struct.new $string
    i64.const 4
    i64.const 0
    call $wasm/core.newDesc
    global.set $QOption_circle_QTuple_In_54aeab0eecb1911c_af955c1b1c25c023
    global.get $noClosure
    i64.const 11
    i32.const 0
    i32.const 38
    i32.const 198
    i32.const 38
    array.new_data $bytes $strings
    struct.new $string
    i64.const 2
    i64.const 0
    call $wasm/core.newDesc
    global.set $QOption_none_some_QTuple_Int_end_9e75d53e4132c43a
    global.get $noClosure
    global.get $QRecord_name_String_x_Int_y_Int
    i64.const 0
    global.get $quest_type_String
    i32.const 0
    i32.const 4
    i32.const 236
    i32.const 4
    array.new_data $bytes $strings
    struct.new $string
    call $wasm/core.setPart
    drop
    global.get $noClosure
    global.get $QRecord_name_String_x_Int_y_Int
    i64.const 1
    global.get $quest_type_Int
    i32.const 0
    i32.const 1
    i32.const 240
    i32.const 1
    array.new_data $bytes $strings
    struct.new $string
    call $wasm/core.setPart
    drop
    global.get $noClosure
    global.get $QRecord_name_String_x_Int_y_Int
    i64.const 2
    global.get $quest_type_Int
    i32.const 0
    i32.const 1
    i32.const 241
    i32.const 1
    array.new_data $bytes $strings
    struct.new $string
    call $wasm/core.setPart
    drop
    global.get $noClosure
    global.get $QTuple_Int_90c1d29a40761138
    i64.const 0
    global.get $quest_type_Int
    i32.const 0
    i32.const 1
    i32.const 242
    i32.const 1
    array.new_data $bytes $strings
    struct.new $string
    call $wasm/core.setPart
    drop
    global.get $noClosure
    global.get $QTuple_Int_Int_586d0a3b5f6d6e01
    i64.const 0
    global.get $quest_type_Int
    i32.const 0
    i32.const 1
    i32.const 243
    i32.const 1
    array.new_data $bytes $strings
    struct.new $string
    call $wasm/core.setPart
    drop
    global.get $noClosure
    global.get $QTuple_Int_Int_586d0a3b5f6d6e01
    i64.const 1
    global.get $quest_type_Int
    i32.const 0
    i32.const 1
    i32.const 244
    i32.const 1
    array.new_data $bytes $strings
    struct.new $string
    call $wasm/core.setPart
    drop
    global.get $noClosure
    global.get $QTuple_Int_bf55836b2befd5ab
    i64.const 0
    global.get $quest_type_Int
    i32.const 0
    i32.const 4
    i32.const 245
    i32.const 4
    array.new_data $bytes $strings
    struct.new $string
    call $wasm/core.setPart
    drop
    global.get $noClosure
    global.get $QTuple_Int_742e411bebefcd67
    i64.const 0
    global.get $quest_type_Int
    i32.const 0
    i32.const 1
    i32.const 249
    i32.const 1
    array.new_data $bytes $strings
    struct.new $string
    call $wasm/core.setPart
    drop
    global.get $noClosure
    global.get $QOption_circle_QTuple_In_54aeab0eecb1911c_af955c1b1c25c023
    i64.const 0
    global.get $QTuple_Int_90c1d29a40761138
    i32.const 0
    i32.const 6
    i32.const 250
    i32.const 6
    array.new_data $bytes $strings
    struct.new $string
    call $wasm/core.setPart
    drop
    global.get $noClosure
    global.get $QOption_circle_QTuple_In_54aeab0eecb1911c_af955c1b1c25c023
    i64.const 1
    global.get $noClosure
    i64.const 0
    call $wasm/core.base
    i32.const 0
    i32.const 5
    i32.const 256
    i32.const 5
    array.new_data $bytes $strings
    struct.new $string
    call $wasm/core.setPart
    drop
    global.get $noClosure
    global.get $QOption_circle_QTuple_In_54aeab0eecb1911c_af955c1b1c25c023
    i64.const 2
    global.get $QTuple_Int_Int_586d0a3b5f6d6e01
    i32.const 0
    i32.const 5
    i32.const 261
    i32.const 5
    array.new_data $bytes $strings
    struct.new $string
    call $wasm/core.setPart
    drop
    global.get $noClosure
    global.get $QOption_circle_QTuple_In_54aeab0eecb1911c_af955c1b1c25c023
    i64.const 3
    global.get $QTuple_Int_bf55836b2befd5ab
    i32.const 0
    i32.const 6
    i32.const 266
    i32.const 6
    array.new_data $bytes $strings
    struct.new $string
    call $wasm/core.setPart
    drop
    global.get $noClosure
    global.get $QOption_none_some_QTuple_Int_end_9e75d53e4132c43a
    i64.const 0
    global.get $noClosure
    i64.const 0
    call $wasm/core.base
    i32.const 0
    i32.const 4
    i32.const 272
    i32.const 4
    array.new_data $bytes $strings
    struct.new $string
    call $wasm/core.setPart
    drop
    global.get $noClosure
    global.get $QOption_none_some_QTuple_Int_end_9e75d53e4132c43a
    i64.const 1
    global.get $QTuple_Int_742e411bebefcd67
    i32.const 0
    i32.const 4
    i32.const 276
    i32.const 4
    array.new_data $bytes $strings
    struct.new $string
    call $wasm/core.setPart
    drop
  )
  (data $strings "Record x: Int var y: Int name: String endTuple r: Int endTuple x: Int y: Int endTuple side: Int endTuple v: Int endOption circle: Tuple r: Int end empty point: Tuple x: Int y: Int end square: Tup...Option none some: Tuple v: Int end endnamexyrxysidevcircleemptypointsquarenonesome/Users/haahr/Dropbox/Paul/src/quest/.claude/worktrees/wasm-plan-opus/tests/self-hosted/wasm/aggregates.quest:25:55wasm: a proxy, which this backend does not yet run\0a\0a/Users/haahr/Dropbox/Paul/src/quest/.claude/worktrees/wasm-plan-opus/tests/self-hosted/wasm/aggregates.quest:26:10wasm: a proxy, which this backend does not yet run\0a/Users/haahr/Dropbox/Paul/src/quest/.claude/worktrees/wasm-plan-opus/tests/self-hosted/wasm/aggregates.quest:26:10wasm: a proxy, which this backend does not yet run\0a \0a/Users/haahr/Dropbox/Paul/src/quest/.claude/worktrees/wasm-plan-opus/tests/self-hosted/wasm/aggregates.quest:28:15/Users/haahr/Dropbox/Paul/src/quest/.claude/worktrees/wasm-plan-opus/tests/self-hosted/wasm/aggregates.quest:28:75wasm: a proxy, which this backend does not yet run\0a/Users/haahr/Dropbox/Paul/src/quest/.claude/worktrees/wasm-plan-opus/tests/self-hosted/wasm/aggregates.quest:29:25wasm: a proxy, which this backend does not yet run\0a/Users/haahr/Dropbox/Paul/src/quest/.claude/worktrees/wasm-plan-opus/tests/self-hosted/wasm/aggregates.quest:29:57/Users/haahr/Dropbox/Paul/src/quest/.claude/worktrees/wasm-plan-opus/tests/self-hosted/wasm/aggregates.quest:29:70   \0aOption ordinal  out of bounds (0 <= ordinal < 3)\0a  at /Users/haahr/Dropbox/Paul/src/quest/.claude/worktrees/wasm-plan-opus/tests/self-hosted/wasm/aggregates.quest:31:13\0awasm: a proxy, which this backend does not yet run\0awasm: a proxy, which this backend does not yet run\0a \0a \0atwo!''\0a   \0a/Users/haahr/Dropbox/Paul/src/quest/.claude/worktrees/wasm-plan-opus/tests/self-hosted/wasm/aggregates.quest:54:9quest: out of memory: an array of more than 134217720 elements\0a/Users/haahr/Dropbox/Paul/src/quest/.claude/worktrees/wasm-plan-opus/tests/self-hosted/wasm/aggregates.quest:55:21/Users/haahr/Dropbox/Paul/src/quest/.claude/worktrees/wasm-plan-opus/tests/self-hosted/wasm/aggregates.quest:56:14 \0aabcdefabababc''   \0ap  \0aq/Users/haahr/Dropbox/Paul/src/quest/.claude/worktrees/wasm-plan-opus/tests/self-hosted/wasm/aggregates.quest:68:5/Users/haahr/Dropbox/Paul/src/quest/.claude/worktrees/wasm-plan-opus/tests/self-hosted/wasm/aggregates.quest:68:33 \0a\0a/Users/haahr/Dropbox/Paul/src/quest/.claude/worktrees/wasm-plan-opus/tests/self-hosted/wasm/aggregates.quest:71:14\0a")
)


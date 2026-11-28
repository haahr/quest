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
  (type (func (param (ref $clos) i64) (result eqref)))
  (type (func (param (ref $clos) i64 eqref i64 i64) (result eqref)))
  (type (func (param (ref $clos) eqref i64 eqref eqref) (result eqref)))
  (type (func (param (ref $clos) eqref i64 i64 eqref) (result eqref)))
  (type (func (param (ref $clos) eqref i64 i64) (result eqref)))
  (type (func (param (ref $clos) eqref eqref i64 eqref) (result eqref)))
  (type (func (param (ref $clos) eqref eqref eqref) (result eqref)))
  (type (func (param (ref $clos) eqref eqref) (result i32)))
  (type (func (param (ref $clos) eqref i64 eqref) (result eqref)))
  (type (func (param (ref $clos) eqref eqref eqref) (result i32)))
  (type (func (param (ref $clos) eqref i64) (result i64)))
  (type (func (param (ref $clos) eqref eqref i64) (result i64)))
  (type (func (param (ref $clos) eqref eqref eqref i64) (result eqref)))
  (type (func (param (ref $clos) eqref eqref i64 i64) (result eqref)))
  (type (func (param (ref $clos) i32) (result eqref)))
  (type (func (param (ref $clos)) (result eqref)))
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
  (import "wasm/core" "init" (func $wasm/core.init (type 51)))
  (import "wasm/core" "base" (func $wasm/core.base (type 56)))
  (import "wasm/core" "newDesc" (func $wasm/core.newDesc (type 57)))
  (import "wasm/core" "setPart" (func $wasm/core.setPart (type 58)))
  (import "wasm/core" "setText" (func $wasm/core.setText (type 59)))
  (import "wasm/core" "setFlags" (func $wasm/core.setFlags (type 60)))
  (import "wasm/core" "boundVar" (func $wasm/core.boundVar (type 56)))
  (import "wasm/core" "instantiate" (func $wasm/core.instantiate (type 52)))
  (import "wasm/core" "viewDict" (func $wasm/core.viewDict (type 52)))
  (import "wasm/core" "storedField" (func $wasm/core.storedField (type 61)))
  (import "wasm/core" "convert" (func $wasm/core.convert (type 62)))
  (import "wasm/core" "isSubtype" (func $wasm/core.isSubtype (type 63)))
  (import "wasm/core" "registerAbstract" (func $wasm/core.registerAbstract (type 64)))
  (import "wasm/core" "valIs" (func $wasm/core.valIs (type 65)))
  (import "wasm/core" "viewMap" (func $wasm/core.viewMap (type 52)))
  (import "wasm/core" "viewIndex" (func $wasm/core.viewIndex (type 66)))
  (import "wasm/core" "viewPart" (func $wasm/core.viewPart (type 64)))
  (import "wasm/core" "viewRecordSlot" (func $wasm/core.viewRecordSlot (type 67)))
  (import "wasm/core" "viewRecordField" (func $wasm/core.viewRecordField (type 68)))
  (import "wasm/core" "viewOptionComponent" (func $wasm/core.viewOptionComponent (type 69)))
  (import "wasm/core" "viewOptionPayload" (func $wasm/core.viewOptionPayload (type 52)))
  (import "conv" "int" (func $conv.int (type 56)))
  (import "wasm/core" "writerPutString" (func $wasm/core.writerPutString (type 52)))
  (import "conv" "bool" (func $conv.bool (type 70)))
  (import "conv" "char" (func $conv.char (type 70)))
  (import "wasm/core" "flushWriters" (func $wasm/core.flushWriters (type 71)))
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
  (global $QT_record_b1b4b5a1b1aaf0d2 (mut eqref) ref.null none)
  (global $QTuple_Int_90c1d29a40761138 (mut eqref) ref.null none)
  (global $QTuple_Int_Int_586d0a3b5f6d6e01 (mut eqref) ref.null none)
  (global $QTuple_Int_bf55836b2befd5ab (mut eqref) ref.null none)
  (global $QTuple_Int_742e411bebefcd67 (mut eqref) ref.null none)
  (global $QOption_circle_QTuple_In_54aeab0eecb1911c_af955c1b1c25c023 (mut eqref) ref.null none)
  (global $QOption_none_some_QTuple_Int_end_9e75d53e4132c43a (mut eqref) ref.null none)
  (global $literal (mut eqref) ref.null none)
  (global $literal.1 (mut eqref) ref.null none)
  (global $literal.2 (mut eqref) ref.null none)
  (global $literal.3 (mut eqref) ref.null none)
  (global $divide.1 (mut eqref) ref.null none)
  (global $literal.4 (mut eqref) ref.null none)
  (global $literal.5 (mut eqref) ref.null none)
  (global $literal.6 (mut eqref) ref.null none)
  (global $literal.7 (mut eqref) ref.null none)
  (global $dict (ref $dict) i32.const 0 i32.const 1 i32.const 2 array.new_fixed $i32s 3 ref.null none struct.new $dict)
  (global $literal.8 (mut eqref) ref.null none)
  (export "_start" (func $_start))
  (func $divide (type 72) (param $closure (ref $clos)) (param $n i64) (param $d i64) (result i64 i64)
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
  (func $main (type 51)
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
    (local $v.17 i64)
    (local $v.45 eqref)
    (local $t.39 (ref null $recBox))
    (local $t.43 eqref)
    (local $t.44 eqref)
    call $wasm/core.init
    call $descriptors
    call $writer.init
    call $conv.init
    call $string.init
    i32.const 0
    i64.const 2
    call $boxInt.1
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
    call $boxInt.1
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
    call $boxInt.1
    i64.const 1000000000000
    call $boxInt.1
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
            i32.const 45
            i32.const 280
            i32.const 45
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
          local.get $i.1
          i32.wrap_i64
          array.get $slots
          local.set $v.2
          block $inlined1.after
            block $inlined1 (result i64)
              local.get $v.2
              local.tee $v.2
              block (type 73)
                br_on_cast 0 eqref (ref $option)
                local.set $v.4
                global.get $noClosure
                local.get $v.4
                call $wasm/core.unproxy
                ref.cast (ref $option)
              end
              local.set $t.3
              block
                block
                  block
                    block
                      block
                        block
                          local.get $v.2
                          local.tee $v.2
                          ref.test (ref $option)
                          if (result i32)
                            local.get $v.2
                            ref.cast (ref $option)
                            struct.get $option $tag
                          else
                            global.get $noClosure
                            local.get $v.2
                            call $wasm/core.proxyTag
                            i32.wrap_i64
                          end
                          br_table 0 3 2 1 4
                        end
                        local.get $t.3
                        local.set $v.2
                        local.get $v.2
                        ref.cast (ref $tuple)
                        struct.get $tuple $slots
                        i32.const 0
                        array.get $slots
                        call $unboxInt.1
                        local.set $i.1
                        local.get $i.1
                        local.get $i.1
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
                      call $unboxInt.1
                      local.set $i.1
                      local.get $i.1
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
                    call $unboxInt.1
                    local.set $i.1
                    local.get $v.2
                    ref.cast (ref $tuple)
                    struct.get $tuple $slots
                    i32.const 1
                    array.get $slots
                    call $unboxInt.1
                    local.set $v.17
                    local.get $i.1
                    local.get $v.17
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
                i32.const 0
                array.new_default $bytes
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
              br $inlined1.after
            end
            local.set $i.1
            global.get $noClosure
            local.get $i.1
            call $conv.int
            local.set $v.2
            i32.const 1
            ref.i31
            local.set $v.4
            local.get $v.2
            global.get $literal
            ref.is_null
            if
              i32.const 1073741824
              i32.const 1
              i32.const 325
              i32.const 1
              array.new_data $bytes $strings
              struct.new $string
              global.set $literal
            end
            global.get $literal
            call $concat
            local.set $v.2
            local.get $v.4
            local.tee $v.4
            ref.test (ref i31)
            if (result eqref)
              local.get $v.4
              local.get $v.2
              call $putString
            else
              global.get $noClosure
              local.get $v.4
              local.get $v.2
              call $wasm/core.writerPutString
            end
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
      i32.const 45
      i32.const 326
      i32.const 45
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
    i64.const 3
    i32.wrap_i64
    array.get $slots
    local.set $v.2
    local.get $v.2
    local.tee $v.4
    ref.test (ref $option)
    if (result i32)
      local.get $v.4
      ref.cast (ref $option)
      struct.get $option $tag
    else
      global.get $noClosure
      local.get $v.4
      call $wasm/core.proxyTag
      i32.wrap_i64
    end
    i32.const 2
    i32.ne
    if
      global.get $variant.tagMismatch
      i32.const 0
      ref.i31
      i32.const 0
      i32.const 45
      i32.const 371
      i32.const 45
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
    block (type 73)
      br_on_cast 0 eqref (ref $option)
      local.set $v.2
      global.get $noClosure
      local.get $v.2
      call $wasm/core.unproxy
      ref.cast (ref $option)
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
    call $unboxInt.1
    local.set $v.7
    global.get $noClosure
    local.get $v.7
    call $conv.int
    local.set $v.4
    local.get $v.2
    ref.cast (ref $tuple)
    struct.get $tuple $slots
    i32.const 2
    array.get $slots
    call $unboxInt.1
    local.set $v.7
    global.get $noClosure
    local.get $v.7
    call $conv.int
    local.set $v.2
    local.get $v.4
    global.get $literal.1
    ref.is_null
    if
      i32.const 1073741824
      i32.const 1
      i32.const 416
      i32.const 1
      array.new_data $bytes $strings
      struct.new $string
      global.set $literal.1
    end
    global.get $literal.1
    local.get $v.2
    ref.null eq
    ref.null eq
    ref.null eq
    ref.null eq
    call $concatN
    local.set $v.2
    i32.const 1
    ref.i31
    local.set $v.4
    local.get $v.2
    global.get $literal
    ref.is_null
    if
      i32.const 1073741824
      i32.const 1
      i32.const 417
      i32.const 1
      array.new_data $bytes $strings
      struct.new $string
      global.set $literal
    end
    global.get $literal
    call $concat
    local.set $v.2
    local.get $v.4
    local.tee $v.4
    ref.test (ref i31)
    if (result eqref)
      local.get $v.4
      local.get $v.2
      call $putString
    else
      global.get $noClosure
      local.get $v.4
      local.get $v.2
      call $wasm/core.writerPutString
    end
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
      i32.const 45
      i32.const 418
      i32.const 45
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
    i64.const 2
    i32.wrap_i64
    array.get $slots
    local.set $v.2
    i32.const 0
    array.new_fixed $slots 0
    i32.const 1
    struct.new $option
    local.set $v.4
    global.get $noClosure
    global.get $QOption_circle_QTuple_In_54aeab0eecb1911c_af955c1b1c25c023
    local.get $v.2
    local.get $v.4
    call $wasm/core.valIs
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
      i32.const 45
      i32.const 463
      i32.const 45
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
    i64.const 0
    i32.wrap_i64
    array.get $slots
    local.set $v.4
    local.get $v.4
    local.tee $v.4
    ref.test (ref $option)
    if (result i32)
      local.get $v.4
      ref.cast (ref $option)
      struct.get $option $tag
    else
      global.get $noClosure
      local.get $v.4
      call $wasm/core.proxyTag
      i32.wrap_i64
    end
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
      i32.const 45
      i32.const 508
      i32.const 45
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
    i64.const 1
    i32.wrap_i64
    array.get $slots
    local.set $v.5
    local.get $v.5
    local.tee $v.5
    ref.test (ref $option)
    if (result i32)
      local.get $v.5
      ref.cast (ref $option)
      struct.get $option $tag
    else
      global.get $noClosure
      local.get $v.5
      call $wasm/core.proxyTag
      i32.wrap_i64
    end
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
    global.get $noClosure
    local.get $v.7
    call $conv.int
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
      i32.const 45
      i32.const 553
      i32.const 45
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
    i64.const 0
    i32.wrap_i64
    array.get $slots
    local.set $v.45
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
      i32.const 45
      i32.const 598
      i32.const 45
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
    i64.const 1
    i32.wrap_i64
    array.get $slots
    local.set $v
    global.get $noClosure
    global.get $QOption_circle_QTuple_In_54aeab0eecb1911c_af955c1b1c25c023
    local.get $v.45
    local.get $v
    call $wasm/core.valIs
    local.set $v.9
    global.get $noClosure
    local.get $v.9
    call $conv.bool
    local.set $v
    local.get $v.2
    global.get $literal.1
    ref.is_null
    if
      i32.const 1073741824
      i32.const 1
      i32.const 643
      i32.const 1
      array.new_data $bytes $strings
      struct.new $string
      global.set $literal.1
    end
    global.get $literal.1
    local.get $v.4
    global.get $literal.1
    ref.is_null
    if
      i32.const 1073741824
      i32.const 1
      i32.const 644
      i32.const 1
      array.new_data $bytes $strings
      struct.new $string
      global.set $literal.1
    end
    global.get $literal.1
    local.get $v.5
    global.get $literal.1
    ref.is_null
    if
      i32.const 1073741824
      i32.const 1
      i32.const 645
      i32.const 1
      array.new_data $bytes $strings
      struct.new $string
      global.set $literal.1
    end
    global.get $literal.1
    local.get $v
    call $concatN
    local.set $v
    i32.const 1
    ref.i31
    local.set $v.2
    local.get $v
    global.get $literal
    ref.is_null
    if
      i32.const 1073741824
      i32.const 1
      i32.const 646
      i32.const 1
      array.new_data $bytes $strings
      struct.new $string
      global.set $literal
    end
    global.get $literal
    call $concat
    local.set $v
    local.get $v.2
    local.tee $v.2
    ref.test (ref i31)
    if (result eqref)
      local.get $v.2
      local.get $v
      call $putString
    else
      global.get $noClosure
      local.get $v.2
      local.get $v
      call $wasm/core.writerPutString
    end
    local.set $v
    i32.const 0
    i64.const 2
    i64.const 3
    i64.lt_u
    i32.eqz
    if
      i32.const 0
      i32.const 15
      i32.const 647
      i32.const 15
      array.new_data $bytes $strings
      struct.new $string
      i64.const 2
      call $decimal
      call $concat
      i32.const 0
      i32.const 85
      i32.const 662
      i32.const 85
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
    local.tee $v.2
    ref.test (ref $option)
    if (result i32)
      local.get $v.2
      ref.cast (ref $option)
      struct.get $option $tag
    else
      global.get $noClosure
      local.get $v.2
      call $wasm/core.proxyTag
      i32.wrap_i64
    end
    i32.const 1
    i32.eq
    local.set $v.9
    global.get $noClosure
    local.get $v.9
    call $conv.bool
    local.set $v.2
    local.get $v
    local.tee $v
    ref.test (ref $option)
    if (result i32)
      local.get $v
      ref.cast (ref $option)
      struct.get $option $tag
    else
      global.get $noClosure
      local.get $v
      call $wasm/core.proxyTag
      i32.wrap_i64
    end
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
    global.get $noClosure
    local.get $v.7
    call $conv.int
    local.set $v
    local.get $v.2
    global.get $literal.1
    ref.is_null
    if
      i32.const 1073741824
      i32.const 1
      i32.const 747
      i32.const 1
      array.new_data $bytes $strings
      struct.new $string
      global.set $literal.1
    end
    global.get $literal.1
    local.get $v
    ref.null eq
    ref.null eq
    ref.null eq
    ref.null eq
    call $concatN
    local.set $v
    i32.const 1
    ref.i31
    local.set $v.2
    local.get $v
    global.get $literal
    ref.is_null
    if
      i32.const 1073741824
      i32.const 1
      i32.const 748
      i32.const 1
      array.new_data $bytes $strings
      struct.new $string
      global.set $literal
    end
    global.get $literal
    call $concat
    local.set $v
    local.get $v.2
    local.tee $v.2
    ref.test (ref i31)
    if (result eqref)
      local.get $v.2
      local.get $v
      call $putString
    else
      global.get $noClosure
      local.get $v.2
      local.get $v
      call $wasm/core.writerPutString
    end
    local.set $v
    i32.const 0
    i64.const 4
    call $boxInt.1
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
    call $boxInt.1
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
    call $boxInt.1
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
    global.get $noClosure
    global.get $QOption_none_some_QTuple_Int_end_9e75d53e4132c43a
    local.get $v
    local.get $v.2
    call $wasm/core.valIs
    local.set $v.9
    global.get $noClosure
    local.get $v.9
    call $conv.bool
    local.set $v.2
    global.get $noClosure
    global.get $QOption_none_some_QTuple_Int_end_9e75d53e4132c43a
    local.get $v
    local.get $v.4
    call $wasm/core.valIs
    local.set $v.9
    global.get $noClosure
    local.get $v.9
    call $conv.bool
    local.set $v
    local.get $v.2
    global.get $literal.1
    ref.is_null
    if
      i32.const 1073741824
      i32.const 1
      i32.const 749
      i32.const 1
      array.new_data $bytes $strings
      struct.new $string
      global.set $literal.1
    end
    global.get $literal.1
    local.get $v
    ref.null eq
    ref.null eq
    ref.null eq
    ref.null eq
    call $concatN
    local.set $v
    i32.const 1
    ref.i31
    local.set $v.2
    local.get $v
    global.get $literal
    ref.is_null
    if
      i32.const 1073741824
      i32.const 1
      i32.const 750
      i32.const 1
      array.new_data $bytes $strings
      struct.new $string
      global.set $literal
    end
    global.get $literal
    call $concat
    local.set $v
    local.get $v.2
    local.tee $v.2
    ref.test (ref i31)
    if (result eqref)
      local.get $v.2
      local.get $v
      call $putString
    else
      global.get $noClosure
      local.get $v.2
      local.get $v
      call $wasm/core.writerPutString
    end
    local.set $v
    global.get $literal.2
    ref.is_null
    if
      i32.const 1073741824
      i32.const 3
      i32.const 751
      i32.const 3
      array.new_data $bytes $strings
      struct.new $string
      global.set $literal.2
    end
    global.get $literal.2
    local.set $v
    i32.const 0
    i64.const 1
    call $boxInt.1
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
    global.get $literal.3
    ref.is_null
    if
      i32.const 1073741824
      i32.const 1
      i32.const 754
      i32.const 1
      array.new_data $bytes $strings
      struct.new $string
      global.set $literal.3
    end
    global.get $literal.3
    call $concat
    local.set $v.2
    local.get $v
    ref.cast (ref $tuple)
    struct.get $tuple $slots
    i32.const 1
    local.get $v.2
    array.set $slots
    global.get $noClosure
    i64.const 1
    call $conv.int
    local.set $v.2
    local.get $v
    ref.cast (ref $tuple)
    struct.get $tuple $slots
    i32.const 1
    array.get $slots
    local.set $v
    global.get $noClosure
    i32.const 99
    call $conv.char
    local.set $v.4
    local.get $v.2
    local.get $v
    local.get $v.4
    ref.null eq
    ref.null eq
    ref.null eq
    ref.null eq
    call $concatN
    local.set $v
    i32.const 1
    ref.i31
    local.set $v.2
    local.get $v
    global.get $literal
    ref.is_null
    if
      i32.const 1073741824
      i32.const 1
      i32.const 755
      i32.const 1
      array.new_data $bytes $strings
      struct.new $string
      global.set $literal
    end
    global.get $literal
    call $concat
    local.set $v
    local.get $v.2
    local.tee $v.2
    ref.test (ref i31)
    if (result eqref)
      local.get $v.2
      local.get $v
      call $putString
    else
      global.get $noClosure
      local.get $v.2
      local.get $v
      call $wasm/core.writerPutString
    end
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
    local.set $v.17
    local.get $i
    local.set $i
    global.get $noClosure
    local.get $i
    call $conv.int
    local.set $v
    local.get $v.7
    local.set $v.7
    global.get $noClosure
    local.get $v.7
    call $conv.int
    local.set $v.2
    local.get $v.17
    local.set $v.7
    global.get $noClosure
    local.get $v.7
    call $conv.int
    local.set $v.4
    local.get $i.1
    local.set $v.7
    global.get $noClosure
    local.get $v.7
    call $conv.int
    local.set $v.5
    local.get $v
    global.get $literal.1
    ref.is_null
    if
      i32.const 1073741824
      i32.const 1
      i32.const 756
      i32.const 1
      array.new_data $bytes $strings
      struct.new $string
      global.set $literal.1
    end
    global.get $literal.1
    local.get $v.2
    global.get $literal.1
    ref.is_null
    if
      i32.const 1073741824
      i32.const 1
      i32.const 757
      i32.const 1
      array.new_data $bytes $strings
      struct.new $string
      global.set $literal.1
    end
    global.get $literal.1
    local.get $v.4
    global.get $literal.1
    ref.is_null
    if
      i32.const 1073741824
      i32.const 1
      i32.const 758
      i32.const 1
      array.new_data $bytes $strings
      struct.new $string
      global.set $literal.1
    end
    global.get $literal.1
    local.get $v.5
    call $concatN
    local.set $v
    i32.const 1
    ref.i31
    local.set $v.2
    local.get $v
    global.get $literal
    ref.is_null
    if
      i32.const 1073741824
      i32.const 1
      i32.const 759
      i32.const 1
      array.new_data $bytes $strings
      struct.new $string
      global.set $literal
    end
    global.get $literal
    call $concat
    local.set $v
    local.get $v.2
    local.tee $v.2
    ref.test (ref i31)
    if (result eqref)
      local.get $v.2
      local.get $v
      call $putString
    else
      global.get $noClosure
      local.get $v.2
      local.get $v
      call $wasm/core.writerPutString
    end
    local.set $v
    i64.const 5
    i64.const 0
    i64.lt_s
    if
      global.get $arrayOp.error
      i32.const 0
      ref.i31
      i32.const 0
      i32.const 44
      i32.const 760
      i32.const 44
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
    i64.const 5
    i64.const 134217720
    i64.gt_s
    if
      i32.const 0
      i32.const 63
      i32.const 804
      i32.const 63
      array.new_data $bytes $strings
      struct.new $string
      i32.const 70
      call $fatal
      unreachable
    end
    i32.const 0
    i64.const 0
    call $boxInt.1
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
            i32.const 45
            i32.const 867
            i32.const 45
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
          local.get $i
          i32.wrap_i64
          local.get $i.1
          call $boxInt.1
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
      i32.const 45
      i32.const 912
      i32.const 45
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
    i64.const 4
    i32.wrap_i64
    array.get $slots
    call $unboxInt.1
    local.set $v.7
    global.get $noClosure
    local.get $v.7
    call $conv.int
    local.set $v.2
    local.get $v
    ref.cast (ref $array)
    struct.get $array $elems
    array.len
    i64.extend_i32_u
    local.set $v.7
    global.get $noClosure
    local.get $v.7
    call $conv.int
    local.set $v.4
    local.get $v.2
    global.get $literal.1
    ref.is_null
    if
      i32.const 1073741824
      i32.const 1
      i32.const 957
      i32.const 1
      array.new_data $bytes $strings
      struct.new $string
      global.set $literal.1
    end
    global.get $literal.1
    local.get $v.4
    ref.null eq
    ref.null eq
    ref.null eq
    ref.null eq
    call $concatN
    local.set $v.2
    i32.const 1
    ref.i31
    local.set $v.4
    local.get $v.2
    global.get $literal
    ref.is_null
    if
      i32.const 1073741824
      i32.const 1
      i32.const 958
      i32.const 1
      array.new_data $bytes $strings
      struct.new $string
      global.set $literal
    end
    global.get $literal
    call $concat
    local.set $v.2
    local.get $v.4
    local.tee $v.4
    ref.test (ref i31)
    if (result eqref)
      local.get $v.4
      local.get $v.2
      call $putString
    else
      global.get $noClosure
      local.get $v.4
      local.get $v.2
      call $wasm/core.writerPutString
    end
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
    global.get $literal.4
    ref.is_null
    if
      i32.const 1073741824
      i32.const 6
      i32.const 959
      i32.const 6
      array.new_data $bytes $strings
      struct.new $string
      global.set $literal.4
    end
    global.get $literal.4
    i64.const 2
    i64.const 3
    call $stringGetSub
    local.set $v.4
    global.get $literal.5
    ref.is_null
    if
      i32.const 1073741824
      i32.const 2
      i32.const 965
      i32.const 2
      array.new_data $bytes $strings
      struct.new $string
      global.set $literal.5
    end
    global.get $literal.5
    global.get $literal.5
    ref.is_null
    if
      i32.const 1073741824
      i32.const 2
      i32.const 967
      i32.const 2
      array.new_data $bytes $strings
      struct.new $string
      global.set $literal.5
    end
    global.get $literal.5
    call $stringEqual
    local.set $v.9
    global.get $noClosure
    local.get $v.9
    call $conv.bool
    local.set $v.5
    global.get $literal.6
    ref.is_null
    if
      i32.const 1073741824
      i32.const 3
      i32.const 969
      i32.const 3
      array.new_data $bytes $strings
      struct.new $string
      global.set $literal.6
    end
    global.get $literal.6
    i64.const 2
    call $stringGetChar
    local.set $v.9
    global.get $noClosure
    local.get $v.9
    call $conv.char
    local.set $v.45
    local.get $v.2
    global.get $literal.1
    ref.is_null
    if
      i32.const 1073741824
      i32.const 1
      i32.const 972
      i32.const 1
      array.new_data $bytes $strings
      struct.new $string
      global.set $literal.1
    end
    global.get $literal.1
    local.get $v.4
    global.get $literal.1
    ref.is_null
    if
      i32.const 1073741824
      i32.const 1
      i32.const 973
      i32.const 1
      array.new_data $bytes $strings
      struct.new $string
      global.set $literal.1
    end
    global.get $literal.1
    local.get $v.5
    global.get $literal.1
    ref.is_null
    if
      i32.const 1073741824
      i32.const 1
      i32.const 974
      i32.const 1
      array.new_data $bytes $strings
      struct.new $string
      global.set $literal.1
    end
    global.get $literal.1
    local.get $v.45
    call $concatN
    local.set $v.2
    i32.const 1
    ref.i31
    local.set $v.4
    local.get $v.2
    global.get $literal
    ref.is_null
    if
      i32.const 1073741824
      i32.const 1
      i32.const 975
      i32.const 1
      array.new_data $bytes $strings
      struct.new $string
      global.set $literal
    end
    global.get $literal
    call $concat
    local.set $v.2
    local.get $v.4
    local.tee $v.4
    ref.test (ref i31)
    if (result eqref)
      local.get $v.4
      local.get $v.2
      call $putString
    else
      global.get $noClosure
      local.get $v.4
      local.get $v.2
      call $wasm/core.writerPutString
    end
    local.set $v.2
    i32.const 0
    global.get $QT_record_b1b4b5a1b1aaf0d2
    global.get $literal.7
    ref.is_null
    if
      i32.const 1073741824
      i32.const 1
      i32.const 976
      i32.const 1
      array.new_data $bytes $strings
      struct.new $string
      global.set $literal.7
    end
    global.get $literal.7
    i64.const 3
    call $boxInt.1
    i64.const 4
    call $boxInt.1
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
    local.tee $t.39
    struct.get $recBox $payload
    local.get $t.39
    struct.get $recBox $dict
    local.set $v.4
    local.set $v.5
    local.get $v.5
    local.get $v.4
    local.set $v.45
    ref.cast (ref $record)
    struct.get $record $slots
    local.get $v.45
    ref.cast (ref $dict)
    struct.get $dict $indices
    i32.const 2
    array.get $i32s
    array.get $slots
    call $unboxInt.1
    local.set $v.7
    local.get $v.7
    i64.const 10
    i64.add
    local.set $v.7
    local.get $v.5
    local.get $v.4
    local.set $v.45
    ref.cast (ref $record)
    struct.get $record $slots
    local.get $v.45
    ref.cast (ref $dict)
    struct.get $dict $indices
    i32.const 2
    array.get $i32s
    local.get $v.7
    call $boxInt.1
    array.set $slots
    local.get $v.5
    local.get $v.4
    local.set $v.45
    ref.cast (ref $record)
    struct.get $record $slots
    local.get $v.45
    ref.cast (ref $dict)
    struct.get $dict $indices
    i32.const 0
    array.get $i32s
    array.get $slots
    local.set $v.45
    local.get $v.5
    local.get $v.4
    local.set $t.43
    ref.cast (ref $record)
    struct.get $record $slots
    local.get $t.43
    ref.cast (ref $dict)
    struct.get $dict $indices
    i32.const 1
    array.get $i32s
    array.get $slots
    call $unboxInt.1
    local.set $v.7
    global.get $noClosure
    local.get $v.7
    call $conv.int
    local.set $t.43
    local.get $v.5
    local.get $v.4
    local.set $t.44
    ref.cast (ref $record)
    struct.get $record $slots
    local.get $t.44
    ref.cast (ref $dict)
    struct.get $dict $indices
    i32.const 2
    array.get $i32s
    array.get $slots
    call $unboxInt.1
    local.set $v.7
    global.get $noClosure
    local.get $v.7
    call $conv.int
    local.set $t.44
    local.get $v.45
    global.get $literal.1
    ref.is_null
    if
      i32.const 1073741824
      i32.const 1
      i32.const 977
      i32.const 1
      array.new_data $bytes $strings
      struct.new $string
      global.set $literal.1
    end
    global.get $literal.1
    local.get $t.43
    global.get $literal.1
    ref.is_null
    if
      i32.const 1073741824
      i32.const 1
      i32.const 978
      i32.const 1
      array.new_data $bytes $strings
      struct.new $string
      global.set $literal.1
    end
    global.get $literal.1
    local.get $t.44
    ref.null eq
    ref.null eq
    call $concatN
    local.set $v.45
    i32.const 1
    ref.i31
    local.set $t.43
    local.get $v.45
    global.get $literal
    ref.is_null
    if
      i32.const 1073741824
      i32.const 1
      i32.const 979
      i32.const 1
      array.new_data $bytes $strings
      struct.new $string
      global.set $literal
    end
    global.get $literal
    call $concat
    local.set $v.45
    local.get $t.43
    local.tee $t.43
    ref.test (ref i31)
    if (result eqref)
      local.get $t.43
      local.get $v.45
      call $putString
    else
      global.get $noClosure
      local.get $t.43
      local.get $v.45
      call $wasm/core.writerPutString
    end
    local.set $v.45
    i32.const 0
    global.get $QT_record_b1b4b5a1b1aaf0d2
    global.get $literal.8
    ref.is_null
    if
      i32.const 1073741824
      i32.const 1
      i32.const 980
      i32.const 1
      array.new_data $bytes $strings
      struct.new $string
      global.set $literal.8
    end
    global.get $literal.8
    i64.const 1
    call $boxInt.1
    i64.const 1
    call $boxInt.1
    array.new_fixed $slots 3
    struct.new $record
    global.get $dict
    local.set $v.45
    ref.cast (ref $record)
    local.get $v.45
    ref.cast (ref $dict)
    struct.new $recBox
    local.set $v.45
    local.get $v.45
    ref.cast (ref $recBox)
    local.tee $t.39
    struct.get $recBox $payload
    local.get $t.39
    struct.get $recBox $dict
    local.set $t.43
    local.set $t.43
    i32.const 0
    local.get $v.2
    local.get $v.45
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
      i32.const 44
      i32.const 981
      i32.const 44
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
    local.get $v.2
    ref.cast (ref $array)
    struct.get $array $elems
    i64.const 1
    i32.wrap_i64
    array.get $slots
    local.set $v.45
    local.get $v.45
    ref.cast (ref $recBox)
    local.tee $t.39
    struct.get $recBox $payload
    local.get $t.39
    struct.get $recBox $dict
    local.set $v.45
    local.set $t.43
    local.get $t.43
    local.get $v.45
    local.set $v.45
    ref.cast (ref $record)
    struct.get $record $slots
    local.get $v.45
    ref.cast (ref $dict)
    struct.get $dict $indices
    i32.const 0
    array.get $i32s
    array.get $slots
    local.set $v.45
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
      i32.const 45
      i32.const 1025
      i32.const 45
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
    local.get $v.2
    ref.cast (ref $array)
    struct.get $array $elems
    i64.const 1
    i32.wrap_i64
    array.get $slots
    local.set $v.2
    local.get $v.2
    ref.cast (ref $recBox)
    local.tee $t.39
    struct.get $recBox $payload
    local.get $t.39
    struct.get $recBox $dict
    local.set $v.2
    local.set $t.43
    local.get $t.43
    local.get $v.2
    local.set $t.44
    ref.cast (ref $record)
    struct.get $record $slots
    local.get $t.44
    ref.cast (ref $dict)
    struct.get $dict $indices
    i32.const 1
    array.get $i32s
    array.get $slots
    call $unboxInt.1
    local.set $v.7
    local.get $t.43
    local.get $v.2
    local.set $t.44
    ref.cast (ref $record)
    struct.get $record $slots
    local.get $t.44
    ref.cast (ref $dict)
    struct.get $dict $indices
    i32.const 1
    array.get $i32s
    array.get $slots
    call $unboxInt.1
    local.set $i
    local.get $t.43
    local.get $v.2
    local.set $t.44
    ref.cast (ref $record)
    struct.get $record $slots
    local.get $t.44
    ref.cast (ref $dict)
    struct.get $dict $indices
    i32.const 2
    array.get $i32s
    array.get $slots
    call $unboxInt.1
    local.set $i.1
    local.get $t.43
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
    call $unboxInt.1
    local.set $v.17
    local.get $i.1
    local.get $v.17
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
    global.get $noClosure
    local.get $v.7
    call $conv.int
    local.set $v.2
    local.get $v.5
    local.get $v.4
    local.set $t.43
    ref.cast (ref $record)
    struct.get $record $slots
    local.get $t.43
    ref.cast (ref $dict)
    struct.get $dict $indices
    i32.const 1
    array.get $i32s
    array.get $slots
    call $unboxInt.1
    local.set $v.7
    local.get $v.5
    local.get $v.4
    local.set $t.43
    ref.cast (ref $record)
    struct.get $record $slots
    local.get $t.43
    ref.cast (ref $dict)
    struct.get $dict $indices
    i32.const 1
    array.get $i32s
    array.get $slots
    call $unboxInt.1
    local.set $i
    local.get $v.5
    local.get $v.4
    local.set $t.43
    ref.cast (ref $record)
    struct.get $record $slots
    local.get $t.43
    ref.cast (ref $dict)
    struct.get $dict $indices
    i32.const 2
    array.get $i32s
    array.get $slots
    call $unboxInt.1
    local.set $i.1
    local.get $v.5
    local.get $v.4
    local.set $t.43
    ref.cast (ref $record)
    struct.get $record $slots
    local.get $t.43
    ref.cast (ref $dict)
    struct.get $dict $indices
    i32.const 2
    array.get $i32s
    array.get $slots
    call $unboxInt.1
    local.set $v.17
    local.get $i.1
    local.get $v.17
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
    global.get $noClosure
    local.get $v.7
    call $conv.int
    local.set $t.43
    local.get $v.45
    local.get $v.2
    global.get $literal.1
    ref.is_null
    if
      i32.const 1073741824
      i32.const 1
      i32.const 1070
      i32.const 1
      array.new_data $bytes $strings
      struct.new $string
      global.set $literal.1
    end
    global.get $literal.1
    local.get $t.43
    ref.null eq
    ref.null eq
    ref.null eq
    call $concatN
    local.set $v.2
    i32.const 1
    ref.i31
    local.set $v.45
    local.get $v.2
    global.get $literal
    ref.is_null
    if
      i32.const 1073741824
      i32.const 1
      i32.const 1071
      i32.const 1
      array.new_data $bytes $strings
      struct.new $string
      global.set $literal
    end
    global.get $literal
    call $concat
    local.set $v.2
    local.get $v.45
    local.tee $v.45
    ref.test (ref i31)
    if (result eqref)
      local.get $v.45
      local.get $v.2
      call $putString
    else
      global.get $noClosure
      local.get $v.45
      local.get $v.2
      call $wasm/core.writerPutString
    end
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
    global.get $noClosure
    i64.const 9
    call $conv.int
    local.set $v.4
    local.get $v.2
    local.get $v.4
    call $concat
    local.set $v.2
    i32.const 1
    ref.i31
    local.set $v.4
    local.get $v.2
    global.get $literal
    ref.is_null
    if
      i32.const 1073741824
      i32.const 1
      i32.const 1072
      i32.const 1
      array.new_data $bytes $strings
      struct.new $string
      global.set $literal
    end
    global.get $literal
    call $concat
    local.set $v.2
    local.get $v.4
    local.tee $v.4
    ref.test (ref i31)
    if (result eqref)
      local.get $v.4
      local.get $v.2
      call $putString
    else
      global.get $noClosure
      local.get $v.4
      local.get $v.2
      call $wasm/core.writerPutString
    end
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
      i32.const 45
      i32.const 1073
      i32.const 45
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
    i64.const 5
    i32.wrap_i64
    array.get $slots
    call $unboxInt.1
    local.set $v.7
    global.get $noClosure
    local.get $v.7
    call $conv.int
    local.set $v
    i32.const 1
    ref.i31
    local.set $v.2
    local.get $v
    global.get $literal
    ref.is_null
    if
      i32.const 1073741824
      i32.const 1
      i32.const 1118
      i32.const 1
      array.new_data $bytes $strings
      struct.new $string
      global.set $literal
    end
    global.get $literal
    call $concat
    local.set $v
    local.get $v.2
    local.tee $v.2
    ref.test (ref i31)
    if (result eqref)
      local.get $v.2
      local.get $v
      call $putString
    else
      global.get $noClosure
      local.get $v.2
      local.get $v
      call $wasm/core.writerPutString
    end
    local.set $v
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
  (func $descriptors (type 51)
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
    global.set $QT_record_b1b4b5a1b1aaf0d2
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
    global.get $QT_record_b1b4b5a1b1aaf0d2
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
    global.get $QT_record_b1b4b5a1b1aaf0d2
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
    global.get $QT_record_b1b4b5a1b1aaf0d2
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
    global.get $QT_record_b1b4b5a1b1aaf0d2
    i64.const 2
    i64.const 1
    call $wasm/core.setFlags
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
  (data $strings "Record x: Int var y: Int name: String endTuple r: Int endTuple x: Int y: Int endTuple side: Int endTuple v: Int endOption circle: Tuple r: Int end empty point: Tuple x: Int y: Int end square: Tup...Option none some: Tuple v: Int end endnamexyrxysidevcircleemptypointsquarenonesometests/self-hosted/wasm/aggregates.quest:25:55\0atests/self-hosted/wasm/aggregates.quest:26:10tests/self-hosted/wasm/aggregates.quest:26:10 \0atests/self-hosted/wasm/aggregates.quest:28:15tests/self-hosted/wasm/aggregates.quest:28:75tests/self-hosted/wasm/aggregates.quest:29:25tests/self-hosted/wasm/aggregates.quest:29:57tests/self-hosted/wasm/aggregates.quest:29:70   \0aOption ordinal  out of bounds (0 <= ordinal < 3)\0a  at tests/self-hosted/wasm/aggregates.quest:31:13\0a \0a \0atwo!\0a   \0atests/self-hosted/wasm/aggregates.quest:54:9quest: out of memory: an array of more than 134217720 elements\0atests/self-hosted/wasm/aggregates.quest:55:21tests/self-hosted/wasm/aggregates.quest:56:14 \0aabcdefabababc   \0ap  \0aqtests/self-hosted/wasm/aggregates.quest:68:5tests/self-hosted/wasm/aggregates.quest:68:33 \0a\0atests/self-hosted/wasm/aggregates.quest:71:14\0a")
)


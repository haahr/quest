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
  (type (func (param (ref $clos) i64) (result i64)))
  (type $closU1 (sub $clos (struct (field $hash (mut i32)) (field $uniform (ref 51)))))
  (type (sub $closU1 (struct (field $hash (mut i32)) (field $uniform (ref 51)) (field $native (ref 69)))))
  (type $tries.closure (sub final 71 (struct (field $hash (mut i32)) (field $uniform (ref 51)) (field $native (ref 69)))))
  (type $tries.closure.1 (sub final 71 (struct (field $hash (mut i32)) (field $uniform (ref 51)) (field $native (ref 69)))))
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
  (import "int" "record.payload" (global (mut eqref)))
  (import "int" "record.dict" (global (mut eqref)))
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
  (import "int" "init" (func $int.init (type 49)))
  (import "wasm/print" "init" (func $wasm/print.init (type 49)))
  (import "wasm/print" "show" (func $wasm/print.show (type 50)))
  (import "wasm/core" "unproxy" (func $wasm/core.unproxy (type 51)))
  (import "wasm/core" "proxyTag" (func $wasm/core.proxyTag (type 52)))
  (import "wasm/core" "proxyElement" (func $wasm/core.proxyElement (type 53)))
  (import "wasm/core" "proxyOptionElement" (func $wasm/core.proxyOptionElement (type 53)))
  (import "wasm/core" "proxyOptionPayload" (func $wasm/core.proxyOptionPayload (type 51)))
  (import "wasm/core" "init" (func $wasm/core.init (type 49)))
  (import "wasm/core" "base" (func $wasm/core.base (type 54)))
  (import "wasm/core" "newDesc" (func $wasm/core.newDesc (type 55)))
  (import "wasm/core" "setPart" (func $wasm/core.setPart (type 56)))
  (import "wasm/core" "setText" (func $wasm/core.setText (type 57)))
  (import "wasm/core" "setFlags" (func $wasm/core.setFlags (type 58)))
  (import "wasm/core" "boundVar" (func $wasm/core.boundVar (type 54)))
  (import "wasm/core" "instantiate" (func $wasm/core.instantiate (type 50)))
  (import "wasm/core" "viewDict" (func $wasm/core.viewDict (type 50)))
  (import "wasm/core" "storedField" (func $wasm/core.storedField (type 59)))
  (import "wasm/core" "convert" (func $wasm/core.convert (type 60)))
  (import "wasm/core" "isSubtype" (func $wasm/core.isSubtype (type 61)))
  (import "wasm/core" "registerAbstract" (func $wasm/core.registerAbstract (type 62)))
  (import "wasm/core" "valIs" (func $wasm/core.valIs (type 63)))
  (import "wasm/core" "viewMap" (func $wasm/core.viewMap (type 50)))
  (import "wasm/core" "viewIndex" (func $wasm/core.viewIndex (type 64)))
  (import "wasm/core" "viewPart" (func $wasm/core.viewPart (type 62)))
  (import "wasm/core" "viewRecordSlot" (func $wasm/core.viewRecordSlot (type 65)))
  (import "wasm/core" "viewRecordField" (func $wasm/core.viewRecordField (type 66)))
  (import "wasm/core" "viewOptionComponent" (func $wasm/core.viewOptionComponent (type 67)))
  (import "wasm/core" "viewOptionPayload" (func $wasm/core.viewOptionPayload (type 50)))
  (import "conv" "bool" (func $conv.bool (type 68)))
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
  (global $stop (mut eqref) ref.null none)
  (global $tries.static (ref $tries.closure) i32.const 0 ref.func $tries.uniform ref.func $tries struct.new $tries.closure)
  (global $tries.2 (mut eqref) ref.null none)
  (global $tries.static.1 (ref $tries.closure.1) i32.const 0 ref.func $tries.uniform.1 ref.func $tries.1 struct.new $tries.closure.1)
  (global $tries.3 (mut eqref) ref.null none)
  (export "_start" (func $_start))
  (elem declare func $tries.uniform $tries $tries.uniform.1 $tries.1)
  (func $tries (type 69) (param $closure (ref $clos)) (param $i i64) (result i64)
    (local $v i32)
    (local $v.1 i64)
    (local $e eqref)
    local.get $i
    i64.const 3
    i64.ge_s
    local.set $v
    local.get $v
    if
      global.get $stop
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
    else
      block
        block (result eqref)
          try_table (catch $error 0)
            local.get $i
            i64.const 1
            i64.add
            local.set $v.1
            global.get $noClosure
            local.get $v.1
            call $tries
            local.set $v.1
            local.get $v.1
            return
          end
          unreachable
        end
        local.set $e
        local.get $e
        call $exceptionOf
        global.get $stop
        call $exceptionOf
        ref.eq
        local.set $v
        local.get $v
        if
          local.get $i
          return
        else
          local.get $e
          throw $error
        end
      end
    end
    unreachable
  )
  (func $tries.1 (type 69) (param $closure (ref $clos)) (param $i i64) (result i64)
    (local $v i32)
    (local $v.1 i64)
    (local $e eqref)
    local.get $i
    i64.const 50
    i64.ge_s
    local.set $v
    local.get $v
    if
      global.get $stop
      i32.const 0
      ref.i31
      i32.const 0
      i32.const 114
      i32.const 114
      i32.const 114
      array.new_data $bytes $strings
      struct.new $string
      i32.const 0
      i32.const 0
      i32.const 228
      i32.const 0
      array.new_data $bytes $strings
      struct.new $string
      i32.const 0
      ref.null none
      call $raise
      unreachable
    else
      block
        block (result eqref)
          try_table (catch $error 0)
            local.get $i
            i64.const 1
            i64.add
            local.set $v.1
            global.get $noClosure
            local.get $v.1
            call $tries.1
            local.set $v.1
            local.get $v.1
            return
          end
          unreachable
        end
        local.set $e
        local.get $e
        call $exceptionOf
        global.get $stop
        call $exceptionOf
        ref.eq
        local.set $v
        local.get $v
        if
          local.get $i
          return
        else
          local.get $e
          throw $error
        end
      end
    end
    unreachable
  )
  (func $main (type 49)
    (local $bad eqref)
    (local $other eqref)
    (local $named eqref)
    (local $e eqref)
    (local $v i32)
    (local $x i64)
    (local $v.4 eqref)
    (local $e.2 eqref)
    (local $i i64)
    (local $i.1 i64)
    call $wasm/core.init
    call $descriptors
    call $writer.init
    call $conv.init
    call $int.init
    i32.const 0
    i32.const 0
    i32.const 3
    i32.const 228
    i32.const 3
    array.new_data $bytes $strings
    struct.new $string
    struct.new $exception
    local.set $bad
    i32.const 0
    i32.const 0
    i32.const 5
    i32.const 231
    i32.const 5
    array.new_data $bytes $strings
    struct.new $string
    struct.new $exception
    local.set $other
    i32.const 0
    i32.const 0
    i32.const 5
    i32.const 236
    i32.const 5
    array.new_data $bytes $strings
    struct.new $string
    struct.new $exception
    local.set $named
    block $k2.after
      block $k2 (result i64)
        block
          block (result eqref)
            try_table (catch $error 0)
              local.get $bad
              i64.const 5
              call $boxInt
              i32.const 0
              i32.const 114
              i32.const 241
              i32.const 114
              array.new_data $bytes $strings
              struct.new $string
              i32.const 0
              i32.const 3
              i32.const 355
              i32.const 3
              array.new_data $bytes $strings
              struct.new $string
              i32.const 1
              ref.null none
              call $raise
              unreachable
            end
            unreachable
          end
          local.set $e
          local.get $e
          call $exceptionOf
          local.get $bad
          call $exceptionOf
          ref.eq
          local.set $v
          local.get $v
          if
            local.get $e
            call $payloadOf
            call $unboxInt
            local.set $x
            local.get $x
            i64.const 10
            i64.mul
            local.set $x
            local.get $x
            br $k2
          else
            local.get $e
            call $exceptionOf
            local.get $other
            call $exceptionOf
            ref.eq
            local.set $v
            local.get $v
            if
              i64.const 0
              br $k2
            else
              local.get $e
              throw $error
            end
          end
        end
        br $k2.after
      end
      local.set $x
      local.get $x
      call $convInt
      local.set $e
      i32.const 1
      ref.i31
      local.set $v.4
      local.get $e
      i32.const 0
      i32.const 1
      i32.const 358
      i32.const 1
      array.new_data $bytes $strings
      struct.new $string
      call $concat
      local.set $e
      local.get $v.4
      local.get $e
      call $putString
      local.set $e
      block $inlined1.after
        block $inlined1 (result i64)
          global.get $int.error
          local.set $e
          block
            block (result eqref)
              try_table (catch $error 0)
                i64.const 0
                i64.eqz
                if
                  global.get $int.error
                  i32.const 0
                  ref.i31
                  i32.const 0
                  i32.const 114
                  i32.const 359
                  i32.const 114
                  array.new_data $bytes $strings
                  struct.new $string
                  i32.const 0
                  i32.const 0
                  i32.const 473
                  i32.const 0
                  array.new_data $bytes $strings
                  struct.new $string
                  i32.const 0
                  ref.null none
                  call $raise
                  unreachable
                end
                i64.const 0
                i64.const -1
                i64.eq
                if (result i64)
                  i64.const 0
                  i64.const 100
                  i64.sub
                else
                  i64.const 100
                  i64.const 0
                  i64.div_s
                end
                local.set $x
                local.get $x
                br $inlined1
              end
              unreachable
            end
            local.set $v.4
            local.get $v.4
            call $exceptionOf
            local.get $e
            call $exceptionOf
            ref.eq
            local.set $v
            local.get $v
            if
              i64.const -1
              br $inlined1
            else
              local.get $v.4
              throw $error
            end
          end
          br $inlined1.after
        end
        local.set $x
        local.get $x
        call $convInt
        local.set $e
        block $inlined2.after
          block $inlined2 (result i64)
            global.get $int.error
            local.set $v.4
            block
              block (result eqref)
                try_table (catch $error 0)
                  i64.const 25
                  br $inlined2
                end
                unreachable
              end
              local.set $e.2
              local.get $e.2
              call $exceptionOf
              local.get $v.4
              call $exceptionOf
              ref.eq
              local.set $v
              local.get $v
              if
                i64.const -1
                br $inlined2
              else
                local.get $e.2
                throw $error
              end
            end
            br $inlined2.after
          end
          local.set $x
          local.get $x
          call $convInt
          local.set $v.4
          i32.const 0
          i32.const 1
          i32.const 473
          i32.const 1
          array.new_data $bytes $strings
          struct.new $string
          local.get $v.4
          call $concat
          local.set $v.4
          local.get $e
          local.get $v.4
          call $concat
          local.set $e
          i32.const 1
          ref.i31
          local.set $v.4
          local.get $e
          i32.const 0
          i32.const 1
          i32.const 474
          i32.const 1
          array.new_data $bytes $strings
          struct.new $string
          call $concat
          local.set $e
          local.get $v.4
          local.get $e
          call $putString
          local.set $e
          block $inlined3.after
            block $inlined3 (result i64)
              block
                block (result eqref)
                  try_table (catch $error 0)
                    local.get $other
                    i32.const 0
                    ref.i31
                    i32.const 0
                    i32.const 114
                    i32.const 475
                    i32.const 114
                    array.new_data $bytes $strings
                    struct.new $string
                    i32.const 0
                    i32.const 0
                    i32.const 589
                    i32.const 0
                    array.new_data $bytes $strings
                    struct.new $string
                    i32.const 0
                    ref.null none
                    call $raise
                    unreachable
                  end
                  unreachable
                end
                local.set $e
                i64.const 7
                br $inlined3
              end
              br $inlined3.after
            end
            local.set $x
            local.get $x
            call $convInt
            local.set $e
            i32.const 1
            ref.i31
            local.set $v.4
            local.get $e
            i32.const 0
            i32.const 1
            i32.const 589
            i32.const 1
            array.new_data $bytes $strings
            struct.new $string
            call $concat
            local.set $e
            local.get $v.4
            local.get $e
            call $putString
            local.set $e
            block $inlined6.after
              block $inlined6 (result i64)
                block
                  block (result eqref)
                    try_table (catch $error 0)
                      block
                        block (result eqref)
                          try_table (catch $error 0)
                            local.get $bad
                            i64.const 9
                            call $boxInt
                            i32.const 0
                            i32.const 114
                            i32.const 590
                            i32.const 114
                            array.new_data $bytes $strings
                            struct.new $string
                            i32.const 0
                            i32.const 3
                            i32.const 704
                            i32.const 3
                            array.new_data $bytes $strings
                            struct.new $string
                            i32.const 1
                            ref.null none
                            call $raise
                            unreachable
                          end
                          unreachable
                        end
                        local.set $e
                        local.get $e
                        call $exceptionOf
                        local.get $other
                        call $exceptionOf
                        ref.eq
                        local.set $v
                        local.get $v
                        if
                          i64.const 0
                          br $inlined6
                        else
                          local.get $e
                          throw $error
                        end
                      end
                      br 2
                    end
                    unreachable
                  end
                  local.set $e
                  local.get $e
                  call $exceptionOf
                  local.get $bad
                  call $exceptionOf
                  ref.eq
                  local.set $v
                  local.get $v
                  if
                    local.get $e
                    call $payloadOf
                    call $unboxInt
                    local.set $x
                    local.get $x
                    i64.const 1000
                    i64.add
                    local.set $x
                    local.get $x
                    br $inlined6
                  else
                    local.get $e
                    throw $error
                  end
                end
                br $inlined6.after
              end
              local.set $x
              local.get $x
              call $convInt
              local.set $e
              i32.const 1
              ref.i31
              local.set $v.4
              local.get $e
              i32.const 0
              i32.const 1
              i32.const 707
              i32.const 1
              array.new_data $bytes $strings
              struct.new $string
              call $concat
              local.set $e
              local.get $v.4
              local.get $e
              call $putString
              local.set $e
              i64.const 0
              local.set $x
              i64.const 1
              local.set $i
              local.get $i
              i64.const 10
              i64.le_s
              local.set $v
              local.get $v
              if
                block $L1.exit
                  loop $L1
                    local.get $i
                    local.set $i.1
                    block $k7.after
                      block $k7 (result i64)
                        block
                          block (result eqref)
                            try_table (catch $error 0)
                              block $inlined7.after
                                block $inlined7 (result i64)
                                  local.get $i.1
                                  i64.const 3
                                  i64.gt_s
                                  local.set $v
                                  local.get $v
                                  if
                                    local.get $bad
                                    local.get $i.1
                                    call $boxInt
                                    i32.const 0
                                    i32.const 114
                                    i32.const 708
                                    i32.const 114
                                    array.new_data $bytes $strings
                                    struct.new $string
                                    i32.const 0
                                    i32.const 3
                                    i32.const 822
                                    i32.const 3
                                    array.new_data $bytes $strings
                                    struct.new $string
                                    i32.const 1
                                    ref.null none
                                    call $raise
                                    unreachable
                                  else
                                    local.get $i.1
                                    br $inlined7
                                  end
                                  br $inlined7.after
                                end
                                local.set $i.1
                                local.get $i.1
                                br $k7
                              end
                              br 2
                            end
                            unreachable
                          end
                          local.set $e
                          local.get $e
                          call $exceptionOf
                          local.get $bad
                          call $exceptionOf
                          ref.eq
                          local.set $v
                          local.get $v
                          if
                            i64.const 100
                            br $k7
                          else
                            local.get $e
                            throw $error
                          end
                        end
                        br $k7.after
                      end
                      local.set $i.1
                      local.get $x
                      local.get $i.1
                      i64.add
                      local.set $i.1
                      local.get $i.1
                      local.set $x
                      local.get $i
                      i64.const 10
                      i64.eq
                      local.set $v
                      local.get $v
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
              local.get $x
              call $convInt
              local.set $bad
              i32.const 1
              ref.i31
              local.set $e
              local.get $bad
              i32.const 0
              i32.const 1
              i32.const 825
              i32.const 1
              array.new_data $bytes $strings
              struct.new $string
              call $concat
              local.set $bad
              local.get $e
              local.get $bad
              call $putString
              local.set $bad
              local.get $other
              call $exceptionOf
              local.get $other
              call $exceptionOf
              ref.eq
              local.set $v
              global.get $noClosure
              local.get $v
              call $conv.bool
              local.set $bad
              i32.const 1
              ref.i31
              local.set $other
              local.get $bad
              i32.const 0
              i32.const 1
              i32.const 826
              i32.const 1
              array.new_data $bytes $strings
              struct.new $string
              call $concat
              local.set $bad
              local.get $other
              local.get $bad
              call $putString
              local.set $bad
              i32.const 0
              i32.const 0
              i32.const 4
              i32.const 827
              i32.const 4
              array.new_data $bytes $strings
              struct.new $string
              struct.new $exception
              global.set $stop
              global.get $tries.static
              global.set $tries.2
              global.get $noClosure
              i64.const 0
              call $tries
              local.set $x
              local.get $x
              call $convInt
              local.set $bad
              global.get $tries.static.1
              global.set $tries.3
              global.get $noClosure
              i64.const 0
              call $tries.1
              local.set $x
              local.get $x
              call $convInt
              local.set $other
              i32.const 0
              i32.const 1
              i32.const 831
              i32.const 1
              array.new_data $bytes $strings
              struct.new $string
              local.get $other
              call $concat
              local.set $other
              local.get $bad
              local.get $other
              call $concat
              local.set $bad
              i32.const 1
              ref.i31
              local.set $other
              local.get $bad
              i32.const 0
              i32.const 1
              i32.const 832
              i32.const 1
              array.new_data $bytes $strings
              struct.new $string
              call $concat
              local.set $bad
              local.get $other
              local.get $bad
              call $putString
              local.set $bad
              local.get $named
              i32.const 0
              i32.const 7
              i32.const 833
              i32.const 7
              array.new_data $bytes $strings
              struct.new $string
              i32.const 0
              i32.const 113
              i32.const 840
              i32.const 113
              array.new_data $bytes $strings
              struct.new $string
              i32.const 0
              i32.const 6
              i32.const 953
              i32.const 6
              array.new_data $bytes $strings
              struct.new $string
              i32.const 4
              ref.null none
              call $raise
              unreachable
            end
          end
        end
      end
    end
  )
  (func $_start (type 49)
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
  (func $descriptors (type 49)
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
  )
  (func $tries.uniform (type 51) (param $closure (ref $clos)) (param $a0 eqref) (result eqref)
    local.get $closure
    local.get $a0
    call $unboxInt
    call $tries
    call $boxInt
  )
  (func $tries.uniform.1 (type 51) (param $closure (ref $clos)) (param $a0 eqref) (result eqref)
    local.get $closure
    local.get $a0
    call $unboxInt
    call $tries.1
    call $boxInt
  )
  (data $strings "/Users/haahr/Dropbox/Paul/src/quest/.claude/worktrees/wasm-plan-opus/tests/self-hosted/wasm/exceptions.quest:32:28/Users/haahr/Dropbox/Paul/src/quest/.claude/worktrees/wasm-plan-opus/tests/self-hosted/wasm/exceptions.quest:32:28badothernamed/Users/haahr/Dropbox/Paul/src/quest/.claude/worktrees/wasm-plan-opus/tests/self-hosted/wasm/exceptions.quest:10:36Int\0a/Users/haahr/Dropbox/Paul/src/quest/.claude/worktrees/wasm-plan-opus/tests/self-hosted/wasm/exceptions.quest:13:26 \0a/Users/haahr/Dropbox/Paul/src/quest/.claude/worktrees/wasm-plan-opus/tests/self-hosted/wasm/exceptions.quest:15:20\0a/Users/haahr/Dropbox/Paul/src/quest/.claude/worktrees/wasm-plan-opus/tests/self-hosted/wasm/exceptions.quest:10:36Int\0a/Users/haahr/Dropbox/Paul/src/quest/.claude/worktrees/wasm-plan-opus/tests/self-hosted/wasm/exceptions.quest:10:36Int\0a\0astop \0athe end/Users/haahr/Dropbox/Paul/src/quest/.claude/worktrees/wasm-plan-opus/tests/self-hosted/wasm/exceptions.quest:36:1String")
)


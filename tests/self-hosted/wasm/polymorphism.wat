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
  (type (func (param (ref $clos) eqref eqref eqref) (result i64)))
  (type (func (param (ref $clos) eqref i32 eqref eqref) (result eqref)))
  (type (func (param (ref $clos) eqref eqref eqref eqref) (result eqref)))
  (type (func (param (ref $clos)) (result eqref)))
  (type (func (param (ref $clos) i64) (result i32)))
  (type (func (param (ref $clos) eqref) (result i32)))
  (type (func (param (ref $clos) i64) (result i64)))
  (type $closU1 (sub $clos (struct (field $hash (mut i32)) (field $uniform (ref 51)))))
  (type (sub $closU1 (struct (field $hash (mut i32)) (field $uniform (ref 51)) (field $native (ref 72)))))
  (type $pos.closure (sub final 76 (struct (field $hash (mut i32)) (field $uniform (ref 51)) (field $native (ref 72)))))
  (type (sub $closU1 (struct (field $hash (mut i32)) (field $uniform (ref 51)) (field $native (ref 74)))))
  (type $f.closure (sub final 78 (struct (field $hash (mut i32)) (field $uniform (ref 51)) (field $native (ref 74)))))
  (type $qa_adapt.closure (sub final 78 (struct (field $hash (mut i32)) (field $uniform (ref 51)) (field $native (ref 74)) (field $c0 (mut eqref)))))
  (type (sub $closU1 (struct (field $hash (mut i32)) (field $uniform (ref 51)) (field $native (ref 51)))))
  (type (sub $closU1 (struct (field $hash (mut i32)) (field $uniform (ref 51)) (field $native (ref 73)))))
  (type $nonEmpty.closure (sub final 82 (struct (field $hash (mut i32)) (field $uniform (ref 51)) (field $native (ref 73)))))
  (type $qa_adapt.closure.1 (sub final 82 (struct (field $hash (mut i32)) (field $uniform (ref 51)) (field $native (ref 73)))))
  (type $qa_adapt.closure.2 (sub final 81 (struct (field $hash (mut i32)) (field $uniform (ref 51)) (field $native (ref 51)))))
  (type $f.closure.1 (sub final 81 (struct (field $hash (mut i32)) (field $uniform (ref 51)) (field $native (ref 51)))))
  (type (func (param eqref) (result (ref $tuple))))
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
  (import "units/gen" "record.payload" (global (mut eqref)))
  (import "units/gen" "record.dict" (global (mut eqref)))
  (import "writer" "record.payload" (global (mut eqref)))
  (import "writer" "record.dict" (global (mut eqref)))
  (import "string" "record.payload" (global (mut eqref)))
  (import "string" "record.dict" (global (mut eqref)))
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
  (import "units/gen" "init" (func $units/gen.init (type 49)))
  (import "writer" "init" (func $writer.init (type 49)))
  (import "string" "init" (func $string.init (type 49)))
  (import "conv" "init" (func $conv.init (type 49)))
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
  (import "units/gen" "count" (func $units/gen.count (type 68)))
  (import "wasm/core" "writerPutString" (func $wasm/core.writerPutString (type 50)))
  (import "units/gen" "pick" (func $units/gen.pick (type 69)))
  (import "units/gen" "twice" (func $units/gen.twice (type 50)))
  (import "units/gen" "pair" (func $units/gen.pair (type 70)))
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
  (global $QTuple_Int_String_c1d595445c9f41f3 (mut eqref) ref.null none)
  (global $pos.static (ref $pos.closure) i32.const 0 ref.func $pos.uniform ref.func $pos struct.new $pos.closure)
  (global $f.static (ref $f.closure) i32.const 0 ref.func $f.uniform ref.func $f struct.new $f.closure)
  (global $nonEmpty.static (ref $nonEmpty.closure) i32.const 0 ref.func $nonEmpty.uniform ref.func $nonEmpty struct.new $nonEmpty.closure)
  (global $qa_adapt.static (ref $qa_adapt.closure.1) i32.const 0 ref.func $qa_adapt.uniform ref.func $qa_adapt struct.new $qa_adapt.closure.1)
  (global $qa_adapt.static.1 (ref $qa_adapt.closure.2) i32.const 0 ref.func $qa_adapt.1 ref.func $qa_adapt.1 struct.new $qa_adapt.closure.2)
  (global $f.static.1 (ref $f.closure.1) i32.const 0 ref.func $f.1 ref.func $f.1 struct.new $f.closure.1)
  (export "_start" (func $_start))
  (elem declare func $pos.uniform $pos $f.uniform $f $nonEmpty.uniform $nonEmpty $qa_adapt.uniform $qa_adapt $qa_adapt.1 $qa_adapt.uniform.1 $qa_adapt.2 $f.1)
  (func $pos (type 72) (param $closure (ref $clos)) (param $n i64) (result i32)
    (local $v i32)
    local.get $n
    i64.const 0
    i64.gt_s
    local.set $v
    local.get $v
    return
    unreachable
  )
  (func $nonEmpty (type 73) (param $closure (ref $clos)) (param $s eqref) (result i32)
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
  (func $f (type 74) (param $closure (ref $clos)) (param $n i64) (result i64)
    (local $v i64)
    local.get $n
    i64.const 3
    i64.mul
    local.set $v
    local.get $v
    return
    unreachable
  )
  (func $f.1 (type 51) (param $closure (ref $clos)) (param $s eqref) (result eqref)
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
  (func $qa_adapt (type 73) (param $closure (ref $clos)) (param $x eqref) (result i32)
    (local $orig eqref)
    (local $x.1 i64)
    global.get $pos.static
    local.set $orig
    local.get $x
    call $unboxInt.1
    local.set $x.1
    global.get $noClosure
    local.get $x.1
    return_call $pos
    unreachable
  )
  (func $qa_adapt.1 (type 51) (param $closure (ref $clos)) (param $x eqref) (result eqref)
    (local $orig eqref)
    (local $x.1 i64)
    global.get $f.static
    local.set $orig
    local.get $x
    call $unboxInt.1
    local.set $x.1
    global.get $noClosure
    local.get $x.1
    call $f
    local.set $x.1
    local.get $x.1
    call $boxInt.1
    local.set $orig
    local.get $orig
    return
    unreachable
  )
  (func $qa_adapt.2 (type 74) (param $closure (ref $clos)) (param $x i64) (result i64)
    (local $orig eqref)
    (local $x.1 eqref)
    (local $r.1 i64)
    local.get $closure
    ref.cast (ref $qa_adapt.closure)
    struct.get $qa_adapt.closure $c0
    local.set $orig
    local.get $x
    call $boxInt.1
    local.set $x.1
    local.get $orig
    local.set $orig
    local.get $orig
    ref.test (ref 81)
    if (result eqref)
      local.get $orig
      ref.cast (ref $clos)
      local.get $x.1
      local.get $orig
      ref.cast (ref 81)
      struct.get 81 $native
      call_ref 51
    else
      local.get $orig
      ref.cast (ref $clos)
      local.get $x.1
      local.get $orig
      ref.cast (ref $closU1)
      struct.get $closU1 $uniform
      call_ref 51
    end
    local.set $orig
    local.get $orig
    call $unboxInt.1
    local.set $r.1
    local.get $r.1
    return
    unreachable
  )
  (func $main (type 49)
    (local $pos eqref)
    (local $v eqref)
    (local $pos.1 eqref)
    (local $v.1 i64)
    call $wasm/core.init
    call $descriptors
    call $units/gen.init
    call $writer.init
    call $string.init
    call $conv.init
    global.get $pos.static
    local.set $pos
    global.get $nonEmpty.static
    local.set $pos
    i32.const 0
    i64.const 1
    call $boxInt.1
    i64.const -2
    call $boxInt.1
    i64.const 3
    call $boxInt.1
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
    local.set $v
    i32.const 1
    ref.i31
    local.set $pos.1
    local.get $v
    i32.const 0
    i32.const 1
    i32.const 47
    i32.const 1
    array.new_data $bytes $strings
    struct.new $string
    call $concat
    local.set $v
    local.get $pos.1
    local.tee $pos.1
    ref.test (ref i31)
    if (result eqref)
      local.get $pos.1
      local.get $v
      call $putString
    else
      global.get $noClosure
      local.get $pos.1
      local.get $v
      call $wasm/core.writerPutString
    end
    local.set $v
    i32.const 0
    i32.const 0
    i32.const 1
    i32.const 48
    i32.const 1
    array.new_data $bytes $strings
    struct.new $string
    i32.const 0
    i32.const 0
    i32.const 0
    array.new_default $bytes
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
    local.set $v
    global.get $noClosure
    global.get $quest_type_String
    local.get $v
    local.get $pos
    call $units/gen.count
    local.set $v.1
    local.get $v.1
    call $convInt
    local.set $pos
    i32.const 1
    ref.i31
    local.set $v
    local.get $pos
    i32.const 0
    i32.const 1
    i32.const 51
    i32.const 1
    array.new_data $bytes $strings
    struct.new $string
    call $concat
    local.set $pos
    local.get $v
    local.tee $v
    ref.test (ref i31)
    if (result eqref)
      local.get $v
      local.get $pos
      call $putString
    else
      global.get $noClosure
      local.get $v
      local.get $pos
      call $wasm/core.writerPutString
    end
    local.set $pos
    i32.const 0
    i32.const 3
    i32.const 52
    i32.const 3
    array.new_data $bytes $strings
    struct.new $string
    local.set $pos
    i32.const 0
    i32.const 2
    i32.const 55
    i32.const 2
    array.new_data $bytes $strings
    struct.new $string
    local.set $v
    global.get $noClosure
    global.get $quest_type_String
    i32.const 1
    local.get $pos
    local.get $v
    call $units/gen.pick
    local.set $pos
    local.get $pos
    local.set $pos
    local.get $pos
    local.set $pos
    i32.const 1
    ref.i31
    local.set $v
    local.get $pos
    i32.const 0
    i32.const 1
    i32.const 57
    i32.const 1
    array.new_data $bytes $strings
    struct.new $string
    call $concat
    local.set $pos
    local.get $v
    local.tee $v
    ref.test (ref i31)
    if (result eqref)
      local.get $v
      local.get $pos
      call $putString
    else
      global.get $noClosure
      local.get $v
      local.get $pos
      call $wasm/core.writerPutString
    end
    local.set $pos
    i64.const 1
    call $boxInt.1
    local.set $pos
    i64.const 2000000000000
    call $boxInt.1
    local.set $v
    global.get $noClosure
    global.get $quest_type_Int
    i32.const 0
    local.get $pos
    local.get $v
    call $units/gen.pick
    local.set $pos
    local.get $pos
    call $unboxInt.1
    local.set $v.1
    local.get $v.1
    local.set $v.1
    local.get $v.1
    call $convInt
    local.set $pos
    i32.const 1
    ref.i31
    local.set $v
    local.get $pos
    i32.const 0
    i32.const 1
    i32.const 58
    i32.const 1
    array.new_data $bytes $strings
    struct.new $string
    call $concat
    local.set $pos
    local.get $v
    local.tee $v
    ref.test (ref i31)
    if (result eqref)
      local.get $v
      local.get $pos
      call $putString
    else
      global.get $noClosure
      local.get $v
      local.get $pos
      call $wasm/core.writerPutString
    end
    local.set $pos
    global.get $f.static
    local.set $pos
    global.get $qa_adapt.static.1
    local.set $pos
    global.get $noClosure
    global.get $quest_type_Int
    local.get $pos
    call $units/gen.twice
    local.set $pos
    i32.const 0
    ref.func $qa_adapt.uniform.1
    ref.func $qa_adapt.2
    local.get $pos
    struct.new $qa_adapt.closure
    local.set $pos
    local.get $pos
    local.set $pos
    local.get $pos
    local.set $pos
    local.get $pos
    ref.test (ref 78)
    if (result i64)
      local.get $pos
      ref.cast (ref $clos)
      i64.const 5
      local.get $pos
      ref.cast (ref 78)
      struct.get 78 $native
      call_ref 74
    else
      local.get $pos
      ref.cast (ref $clos)
      i64.const 5
      call $boxInt.1
      local.get $pos
      ref.cast (ref $closU1)
      struct.get $closU1 $uniform
      call_ref 51
      call $unboxInt.1
    end
    local.set $v.1
    local.get $v.1
    call $convInt
    local.set $pos
    i32.const 1
    ref.i31
    local.set $v
    local.get $pos
    i32.const 0
    i32.const 1
    i32.const 59
    i32.const 1
    array.new_data $bytes $strings
    struct.new $string
    call $concat
    local.set $pos
    local.get $v
    local.tee $v
    ref.test (ref i31)
    if (result eqref)
      local.get $v
      local.get $pos
      call $putString
    else
      global.get $noClosure
      local.get $v
      local.get $pos
      call $wasm/core.writerPutString
    end
    local.set $pos
    global.get $f.static.1
    local.set $pos
    global.get $noClosure
    global.get $quest_type_String
    local.get $pos
    call $units/gen.twice
    local.set $pos
    local.get $pos
    local.set $pos
    local.get $pos
    ref.test (ref 81)
    if (result eqref)
      local.get $pos
      ref.cast (ref $clos)
      i32.const 0
      i32.const 2
      i32.const 60
      i32.const 2
      array.new_data $bytes $strings
      struct.new $string
      local.get $pos
      ref.cast (ref 81)
      struct.get 81 $native
      call_ref 51
    else
      local.get $pos
      ref.cast (ref $clos)
      i32.const 0
      i32.const 2
      i32.const 62
      i32.const 2
      array.new_data $bytes $strings
      struct.new $string
      local.get $pos
      ref.cast (ref $closU1)
      struct.get $closU1 $uniform
      call_ref 51
    end
    local.set $pos
    i32.const 1
    ref.i31
    local.set $v
    local.get $pos
    i32.const 0
    i32.const 1
    i32.const 64
    i32.const 1
    array.new_data $bytes $strings
    struct.new $string
    call $concat
    local.set $pos
    local.get $v
    local.tee $v
    ref.test (ref i31)
    if (result eqref)
      local.get $v
      local.get $pos
      call $putString
    else
      global.get $noClosure
      local.get $v
      local.get $pos
      call $wasm/core.writerPutString
    end
    local.set $pos
    i64.const 7
    call $boxInt.1
    local.set $pos
    i32.const 0
    i32.const 5
    i32.const 65
    i32.const 5
    array.new_data $bytes $strings
    struct.new $string
    local.set $v
    global.get $noClosure
    global.get $quest_type_Int
    global.get $quest_type_String
    local.get $pos
    local.get $v
    call $units/gen.pair
    local.set $pos
    local.get $pos
    block (type 87)
      br_on_cast 0 eqref (ref $tuple)
      local.set $pos
      global.get $noClosure
      local.get $pos
      call $wasm/core.unproxy
      ref.cast (ref $tuple)
    end
    local.set $pos
    local.get $pos
    local.set $pos
    local.get $pos
    ref.cast (ref $tuple)
    struct.get $tuple $slots
    i32.const 0
    array.get $slots
    call $unboxInt.1
    local.set $v.1
    local.get $v.1
    call $convInt
    local.set $v
    local.get $pos
    ref.cast (ref $tuple)
    struct.get $tuple $slots
    i32.const 1
    array.get $slots
    local.set $pos.1
    i32.const 0
    i32.const 1
    i32.const 70
    i32.const 1
    array.new_data $bytes $strings
    struct.new $string
    local.get $pos.1
    call $concat
    local.set $pos.1
    local.get $v
    local.get $pos.1
    call $concat
    local.set $v
    i32.const 1
    ref.i31
    local.set $pos.1
    local.get $v
    i32.const 0
    i32.const 1
    i32.const 71
    i32.const 1
    array.new_data $bytes $strings
    struct.new $string
    call $concat
    local.set $v
    local.get $pos.1
    local.tee $pos.1
    ref.test (ref i31)
    if (result eqref)
      local.get $pos.1
      local.get $v
      call $putString
    else
      global.get $noClosure
      local.get $pos.1
      local.get $v
      call $wasm/core.writerPutString
    end
    local.set $v
    i32.const 0
    i32.const 0
    i32.const 3
    i32.const 72
    i32.const 3
    array.new_data $bytes $strings
    struct.new $string
    struct.new $exception
    local.set $v
    local.get $v
    local.get $pos
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
  (func $pos.uniform (type 51) (param $closure (ref $clos)) (param $a0 eqref) (result eqref)
    local.get $closure
    local.get $a0
    call $unboxInt.1
    call $pos
    ref.i31
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
  (func $f.uniform (type 51) (param $closure (ref $clos)) (param $a0 eqref) (result eqref)
    local.get $closure
    local.get $a0
    call $unboxInt.1
    call $f
    call $boxInt.1
  )
  (func $nonEmpty.uniform (type 51) (param $closure (ref $clos)) (param $a0 eqref) (result eqref)
    local.get $closure
    local.get $a0
    call $nonEmpty
    ref.i31
  )
  (func $qa_adapt.uniform (type 51) (param $closure (ref $clos)) (param $a0 eqref) (result eqref)
    local.get $closure
    local.get $a0
    call $qa_adapt
    ref.i31
  )
  (func $qa_adapt.uniform.1 (type 51) (param $closure (ref $clos)) (param $a0 eqref) (result eqref)
    local.get $closure
    local.get $a0
    call $unboxInt.1
    call $qa_adapt.2
    call $boxInt.1
  )
  (data $strings "!Tuple first: Int second: String endfirstsecond\0aabc\0ayesno\0a\0a\0ahihi\0aseven \0abad/Users/haahr/Dropbox/Paul/src/quest/.claude/worktrees/wasm-plan-opus/tests/self-hosted/wasm/polymorphism.quest:22:1Tuple first: Int second: String end")
)


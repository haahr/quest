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
  (type (func (param (ref $clos) eqref i64) (result i64)))
  (type (func (param (ref $clos) eqref i64 eqref) (result eqref)))
  (type (func (param (ref $clos) eqref eqref i64) (result i64)))
  (type (func (param (ref $clos) eqref eqref eqref i64) (result eqref)))
  (type (func (param (ref $clos) eqref eqref i64 i64) (result eqref)))
  (type (func (param (ref $clos) eqref eqref eqref) (result i64)))
  (type (func (param (ref $clos) eqref i32 eqref eqref) (result eqref)))
  (type (func (param (ref $clos) eqref eqref eqref eqref) (result eqref)))
  (type (func (param (ref $clos) i64) (result i32)))
  (type (func (param (ref $clos) eqref) (result i32)))
  (type (func (param (ref $clos) i64) (result i64)))
  (type $closU1 (sub $clos (struct (field $hash (mut i32)) (field $uniform (ref 49)))))
  (type (sub $closU1 (struct (field $hash (mut i32)) (field $uniform (ref 49)) (field $native (ref 68)))))
  (type $pos.closure (sub final 72 (struct (field $hash (mut i32)) (field $uniform (ref 49)) (field $native (ref 68)))))
  (type (sub $closU1 (struct (field $hash (mut i32)) (field $uniform (ref 49)) (field $native (ref 69)))))
  (type $nonEmpty.closure (sub final 74 (struct (field $hash (mut i32)) (field $uniform (ref 49)) (field $native (ref 69)))))
  (type (sub $closU1 (struct (field $hash (mut i32)) (field $uniform (ref 49)) (field $native (ref 70)))))
  (type $f.closure (sub final 76 (struct (field $hash (mut i32)) (field $uniform (ref 49)) (field $native (ref 70)))))
  (type $qa_adapt.closure (sub final 76 (struct (field $hash (mut i32)) (field $uniform (ref 49)) (field $native (ref 70)) (field $c0 (mut eqref)))))
  (type (sub $closU1 (struct (field $hash (mut i32)) (field $uniform (ref 49)) (field $native (ref 49)))))
  (type $f.closure.1 (sub final 79 (struct (field $hash (mut i32)) (field $uniform (ref 49)) (field $native (ref 49)))))
  (type $qa_adapt.closure.1 (sub final 79 (struct (field $hash (mut i32)) (field $uniform (ref 49)) (field $native (ref 49)) (field $c0 (mut eqref)))))
  (type $qa_adapt.closure.2 (sub final 74 (struct (field $hash (mut i32)) (field $uniform (ref 49)) (field $native (ref 69)))))
  (type $qa_adapt.closure.3 (sub final 74 (struct (field $hash (mut i32)) (field $uniform (ref 49)) (field $native (ref 69)))))
  (type $qa_adapt.closure.4 (sub final 79 (struct (field $hash (mut i32)) (field $uniform (ref 49)) (field $native (ref 49)))))
  (type $qa_adapt.closure.5 (sub final 79 (struct (field $hash (mut i32)) (field $uniform (ref 49)) (field $native (ref 49)))))
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
  (import "quest.runtime" "memLoad8" (func $memLoad8 (type 35)))
  (import "quest.runtime" "memStore8" (func $memStore8 (type 36)))
  (import "quest.runtime" "memLoad32" (func $memLoad32 (type 35)))
  (import "quest.runtime" "memStore32" (func $memStore32 (type 36)))
  (import "quest.runtime" "memLoad64" (func $memLoad64 (type 35)))
  (import "quest.runtime" "memStore64" (func $memStore64 (type 36)))
  (import "quest.runtime" "memEnsure" (func $memEnsure (type 37)))
  (import "quest.runtime" "memToString" (func $memToString (type 38)))
  (import "quest.runtime" "stringToMem" (func $stringToMem (type 39)))
  (import "quest.runtime" "wasi:args_sizes_get" (func $wasi:args_sizes_get (type 40)))
  (import "quest.runtime" "wasi:args_get" (func $wasi:args_get (type 40)))
  (import "quest.runtime" "wasi:environ_sizes_get" (func $wasi:environ_sizes_get (type 40)))
  (import "quest.runtime" "wasi:environ_get" (func $wasi:environ_get (type 40)))
  (import "quest.runtime" "wasi:fd_prestat_get" (func $wasi:fd_prestat_get (type 40)))
  (import "quest.runtime" "wasi:fd_prestat_dir_name" (func $wasi:fd_prestat_dir_name (type 41)))
  (import "quest.runtime" "wasi:path_open" (func $wasi:path_open (type 42)))
  (import "quest.runtime" "wasi:fd_read" (func $wasi:fd_read (type 43)))
  (import "quest.runtime" "wasi:fd_close" (func $wasi:fd_close (type 35)))
  (import "quest.runtime" "wasi:path_filestat_get" (func $wasi:path_filestat_get (type 44)))
  (import "quest.runtime" "wasi:path_create_directory" (func $wasi:path_create_directory (type 41)))
  (import "quest.runtime" "wasi:path_unlink_file" (func $wasi:path_unlink_file (type 41)))
  (import "quest.runtime" "wasi:path_remove_directory" (func $wasi:path_remove_directory (type 41)))
  (import "quest.runtime" "wasi:path_rename" (func $wasi:path_rename (type 45)))
  (import "quest.runtime" "wasi:fd_readdir" (func $wasi:fd_readdir (type 44)))
  (import "quest.runtime" "error" (tag $error (type 46)))
  (import "units/gen" "init" (func $units/gen.init (type 47)))
  (import "writer" "init" (func $writer.init (type 47)))
  (import "string" "init" (func $string.init (type 47)))
  (import "conv" "init" (func $conv.init (type 47)))
  (import "wasm/print" "init" (func $wasm/print.init (type 47)))
  (import "wasm/print" "show" (func $wasm/print.show (type 48)))
  (import "wasm/core" "unproxy" (func $wasm/core.unproxy (type 49)))
  (import "wasm/core" "proxyTag" (func $wasm/core.proxyTag (type 50)))
  (import "wasm/core" "proxyElement" (func $wasm/core.proxyElement (type 51)))
  (import "wasm/core" "proxyOptionElement" (func $wasm/core.proxyOptionElement (type 51)))
  (import "wasm/core" "proxyOptionPayload" (func $wasm/core.proxyOptionPayload (type 49)))
  (import "wasm/core" "init" (func $wasm/core.init (type 47)))
  (import "wasm/core" "base" (func $wasm/core.base (type 52)))
  (import "wasm/core" "newDesc" (func $wasm/core.newDesc (type 53)))
  (import "wasm/core" "setPart" (func $wasm/core.setPart (type 54)))
  (import "wasm/core" "setText" (func $wasm/core.setText (type 55)))
  (import "wasm/core" "setFlags" (func $wasm/core.setFlags (type 56)))
  (import "wasm/core" "instantiate" (func $wasm/core.instantiate (type 48)))
  (import "wasm/core" "viewDict" (func $wasm/core.viewDict (type 48)))
  (import "wasm/core" "storedField" (func $wasm/core.storedField (type 57)))
  (import "wasm/core" "convert" (func $wasm/core.convert (type 58)))
  (import "wasm/core" "isSubtype" (func $wasm/core.isSubtype (type 59)))
  (import "wasm/core" "viewMap" (func $wasm/core.viewMap (type 48)))
  (import "wasm/core" "viewIndex" (func $wasm/core.viewIndex (type 60)))
  (import "wasm/core" "viewPart" (func $wasm/core.viewPart (type 61)))
  (import "wasm/core" "viewRecordSlot" (func $wasm/core.viewRecordSlot (type 62)))
  (import "wasm/core" "viewRecordField" (func $wasm/core.viewRecordField (type 63)))
  (import "wasm/core" "viewOptionComponent" (func $wasm/core.viewOptionComponent (type 64)))
  (import "wasm/core" "viewOptionPayload" (func $wasm/core.viewOptionPayload (type 48)))
  (import "units/gen" "count" (func $units/gen.count (type 65)))
  (import "units/gen" "pick" (func $units/gen.pick (type 66)))
  (import "units/gen" "twice" (func $units/gen.twice (type 48)))
  (import "units/gen" "pair" (func $units/gen.pair (type 67)))
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
  (global $nonEmpty.static (ref $nonEmpty.closure) i32.const 0 ref.func $nonEmpty.uniform ref.func $nonEmpty struct.new $nonEmpty.closure)
  (global $f.static (ref $f.closure) i32.const 0 ref.func $f.uniform ref.func $f struct.new $f.closure)
  (global $f.static.1 (ref $f.closure.1) i32.const 0 ref.func $f.1 ref.func $f.1 struct.new $f.closure.1)
  (global $qa_adapt.static (ref $qa_adapt.closure.2) i32.const 0 ref.func $qa_adapt.uniform ref.func $qa_adapt struct.new $qa_adapt.closure.2)
  (global $qa_adapt.static.1 (ref $qa_adapt.closure.3) i32.const 0 ref.func $qa_adapt.uniform.1 ref.func $qa_adapt.1 struct.new $qa_adapt.closure.3)
  (global $qa_adapt.static.2 (ref $qa_adapt.closure.4) i32.const 0 ref.func $qa_adapt.2 ref.func $qa_adapt.2 struct.new $qa_adapt.closure.4)
  (global $qa_adapt.static.3 (ref $qa_adapt.closure.5) i32.const 0 ref.func $qa_adapt.4 ref.func $qa_adapt.4 struct.new $qa_adapt.closure.5)
  (export "_start" (func $_start))
  (elem declare func $pos.uniform $pos $nonEmpty.uniform $nonEmpty $f.uniform $f $f.1 $qa_adapt.uniform $qa_adapt $qa_adapt.uniform.1 $qa_adapt.1 $qa_adapt.2 $qa_adapt.uniform.2 $qa_adapt.3 $qa_adapt.4 $qa_adapt.5)
  (func $pos (type 68) (param $closure (ref $clos)) (param $n i64) (result i32)
    (local $v i32)
    local.get $n
    i64.const 0
    i64.gt_s
    local.set $v
    local.get $v
    return
    unreachable
  )
  (func $nonEmpty (type 69) (param $closure (ref $clos)) (param $s eqref) (result i32)
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
  (func $f (type 70) (param $closure (ref $clos)) (param $n i64) (result i64)
    (local $v i64)
    local.get $n
    i64.const 3
    i64.mul
    local.set $v
    local.get $v
    return
    unreachable
  )
  (func $f.1 (type 49) (param $closure (ref $clos)) (param $s eqref) (result eqref)
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
  (func $qa_adapt (type 69) (param $closure (ref $clos)) (param $x eqref) (result i32)
    (local $orig eqref)
    (local $x.1 i64)
    global.get $pos.static
    local.set $orig
    local.get $x
    call $unboxInt
    local.set $x.1
    global.get $noClosure
    local.get $x.1
    return_call $pos
    unreachable
  )
  (func $qa_adapt.1 (type 69) (param $closure (ref $clos)) (param $x eqref) (result i32)
    (local $orig eqref)
    global.get $nonEmpty.static
    local.set $orig
    local.get $x
    local.set $orig
    global.get $noClosure
    local.get $orig
    return_call $nonEmpty
    unreachable
  )
  (func $qa_adapt.2 (type 49) (param $closure (ref $clos)) (param $x eqref) (result eqref)
    (local $orig eqref)
    (local $x.1 i64)
    global.get $f.static
    local.set $orig
    local.get $x
    call $unboxInt
    local.set $x.1
    global.get $noClosure
    local.get $x.1
    call $f
    local.set $x.1
    local.get $x.1
    call $boxInt
    local.set $orig
    local.get $orig
    return
    unreachable
  )
  (func $qa_adapt.3 (type 70) (param $closure (ref $clos)) (param $x i64) (result i64)
    (local $orig eqref)
    (local $x.1 eqref)
    (local $r.1 i64)
    local.get $closure
    ref.cast (ref $qa_adapt.closure)
    struct.get $qa_adapt.closure $c0
    local.set $orig
    local.get $x
    call $boxInt
    local.set $x.1
    local.get $orig
    local.set $orig
    local.get $orig
    ref.test (ref 79)
    if (result eqref)
      local.get $orig
      ref.cast (ref $clos)
      local.get $x.1
      local.get $orig
      ref.cast (ref 79)
      struct.get 79 $native
      call_ref 49
    else
      local.get $orig
      ref.cast (ref $clos)
      local.get $x.1
      local.get $orig
      ref.cast (ref $closU1)
      struct.get $closU1 $uniform
      call_ref 49
    end
    local.set $orig
    local.get $orig
    call $unboxInt
    local.set $r.1
    local.get $r.1
    return
    unreachable
  )
  (func $qa_adapt.4 (type 49) (param $closure (ref $clos)) (param $x eqref) (result eqref)
    (local $orig eqref)
    global.get $f.static.1
    local.set $orig
    local.get $x
    local.set $orig
    global.get $noClosure
    local.get $orig
    call $f.1
    local.set $orig
    local.get $orig
    local.set $orig
    local.get $orig
    return
    unreachable
  )
  (func $qa_adapt.5 (type 49) (param $closure (ref $clos)) (param $x eqref) (result eqref)
    (local $orig eqref)
    (local $x.1 eqref)
    local.get $closure
    ref.cast (ref $qa_adapt.closure.1)
    struct.get $qa_adapt.closure.1 $c0
    local.set $orig
    local.get $x
    local.set $x.1
    local.get $orig
    local.set $orig
    local.get $orig
    ref.test (ref 79)
    if (result eqref)
      local.get $orig
      ref.cast (ref $clos)
      local.get $x.1
      local.get $orig
      ref.cast (ref 79)
      struct.get 79 $native
      call_ref 49
    else
      local.get $orig
      ref.cast (ref $clos)
      local.get $x.1
      local.get $orig
      ref.cast (ref $closU1)
      struct.get $closU1 $uniform
      call_ref 49
    end
    local.set $orig
    local.get $orig
    local.set $orig
    local.get $orig
    return
    unreachable
  )
  (func $main (type 47)
    (local $pos eqref)
    (local $pos.1 eqref)
    (local $v.1 i64)
    (local $v.48 eqref)
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
    call $boxInt
    i64.const -2
    call $boxInt
    i64.const 3
    call $boxInt
    array.new_fixed $slots 3
    struct.new $array
    local.set $pos
    global.get $qa_adapt.static
    local.set $pos.1
    global.get $noClosure
    global.get $quest_type_Int
    local.get $pos
    local.get $pos.1
    call $units/gen.count
    local.set $v.1
    local.get $v.1
    call $convInt
    local.set $pos
    i32.const 1
    ref.i31
    local.set $pos.1
    local.get $pos
    i32.const 0
    i32.const 1
    i32.const 47
    i32.const 1
    array.new_data $bytes $strings
    struct.new $string
    call $concat
    local.set $pos
    local.get $pos.1
    local.get $pos
    call $putString
    local.set $pos
    i32.const 0
    i32.const 0
    i32.const 1
    i32.const 48
    i32.const 1
    array.new_data $bytes $strings
    struct.new $string
    i32.const 0
    i32.const 0
    i32.const 49
    i32.const 0
    array.new_data $bytes $strings
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
    local.set $pos
    global.get $qa_adapt.static.1
    local.set $pos.1
    global.get $noClosure
    global.get $quest_type_String
    local.get $pos
    local.get $pos.1
    call $units/gen.count
    local.set $v.1
    local.get $v.1
    call $convInt
    local.set $pos
    i32.const 1
    ref.i31
    local.set $pos.1
    local.get $pos
    i32.const 0
    i32.const 1
    i32.const 51
    i32.const 1
    array.new_data $bytes $strings
    struct.new $string
    call $concat
    local.set $pos
    local.get $pos.1
    local.get $pos
    call $putString
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
    local.set $pos.1
    global.get $noClosure
    global.get $quest_type_String
    i32.const 1
    local.get $pos
    local.get $pos.1
    call $units/gen.pick
    local.set $pos
    local.get $pos
    local.set $pos
    local.get $pos
    local.set $pos
    i32.const 1
    ref.i31
    local.set $pos.1
    local.get $pos
    i32.const 0
    i32.const 1
    i32.const 57
    i32.const 1
    array.new_data $bytes $strings
    struct.new $string
    call $concat
    local.set $pos
    local.get $pos.1
    local.get $pos
    call $putString
    local.set $pos
    i64.const 1
    call $boxInt
    local.set $pos
    i64.const 2000000000000
    call $boxInt
    local.set $pos.1
    global.get $noClosure
    global.get $quest_type_Int
    i32.const 0
    local.get $pos
    local.get $pos.1
    call $units/gen.pick
    local.set $pos
    local.get $pos
    call $unboxInt
    local.set $v.1
    local.get $v.1
    local.set $v.1
    local.get $v.1
    call $convInt
    local.set $pos
    i32.const 1
    ref.i31
    local.set $pos.1
    local.get $pos
    i32.const 0
    i32.const 1
    i32.const 58
    i32.const 1
    array.new_data $bytes $strings
    struct.new $string
    call $concat
    local.set $pos
    local.get $pos.1
    local.get $pos
    call $putString
    local.set $pos
    global.get $f.static
    local.set $pos
    global.get $qa_adapt.static.2
    local.set $pos
    global.get $noClosure
    global.get $quest_type_Int
    local.get $pos
    call $units/gen.twice
    local.set $pos
    i32.const 0
    ref.func $qa_adapt.uniform.2
    ref.func $qa_adapt.3
    local.get $pos
    struct.new $qa_adapt.closure
    local.set $pos
    local.get $pos
    local.set $pos
    local.get $pos
    local.set $pos
    local.get $pos
    ref.test (ref 76)
    if (result i64)
      local.get $pos
      ref.cast (ref $clos)
      i64.const 5
      local.get $pos
      ref.cast (ref 76)
      struct.get 76 $native
      call_ref 70
    else
      local.get $pos
      ref.cast (ref $clos)
      i64.const 5
      call $boxInt
      local.get $pos
      ref.cast (ref $closU1)
      struct.get $closU1 $uniform
      call_ref 49
      call $unboxInt
    end
    local.set $v.1
    local.get $v.1
    call $convInt
    local.set $pos
    i32.const 1
    ref.i31
    local.set $pos.1
    local.get $pos
    i32.const 0
    i32.const 1
    i32.const 59
    i32.const 1
    array.new_data $bytes $strings
    struct.new $string
    call $concat
    local.set $pos
    local.get $pos.1
    local.get $pos
    call $putString
    local.set $pos
    global.get $f.static.1
    local.set $pos
    global.get $qa_adapt.static.3
    local.set $pos
    global.get $noClosure
    global.get $quest_type_String
    local.get $pos
    call $units/gen.twice
    local.set $pos
    i32.const 0
    ref.func $qa_adapt.5
    ref.func $qa_adapt.5
    local.get $pos
    struct.new $qa_adapt.closure.1
    local.set $pos
    local.get $pos
    local.set $pos
    local.get $pos
    local.set $pos
    local.get $pos
    ref.test (ref 79)
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
      ref.cast (ref 79)
      struct.get 79 $native
      call_ref 49
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
      call_ref 49
    end
    local.set $pos
    i32.const 1
    ref.i31
    local.set $pos.1
    local.get $pos
    i32.const 0
    i32.const 1
    i32.const 64
    i32.const 1
    array.new_data $bytes $strings
    struct.new $string
    call $concat
    local.set $pos
    local.get $pos.1
    local.get $pos
    call $putString
    local.set $pos
    i64.const 7
    call $boxInt
    local.set $pos
    i32.const 0
    i32.const 5
    i32.const 65
    i32.const 5
    array.new_data $bytes $strings
    struct.new $string
    local.set $pos.1
    global.get $noClosure
    global.get $quest_type_Int
    global.get $quest_type_String
    local.get $pos
    local.get $pos.1
    call $units/gen.pair
    local.set $pos
    local.get $pos
    block (type 86)
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
    call $unboxInt
    local.set $v.1
    local.get $v.1
    call $convInt
    local.set $pos.1
    local.get $pos
    ref.cast (ref $tuple)
    struct.get $tuple $slots
    i32.const 1
    array.get $slots
    local.set $v.48
    i32.const 0
    i32.const 1
    i32.const 70
    i32.const 1
    array.new_data $bytes $strings
    struct.new $string
    local.get $v.48
    call $concat
    local.set $v.48
    local.get $pos.1
    local.get $v.48
    call $concat
    local.set $pos.1
    i32.const 1
    ref.i31
    local.set $v.48
    local.get $pos.1
    i32.const 0
    i32.const 1
    i32.const 71
    i32.const 1
    array.new_data $bytes $strings
    struct.new $string
    call $concat
    local.set $pos.1
    local.get $v.48
    local.get $pos.1
    call $putString
    local.set $pos.1
    i32.const 0
    i32.const 0
    i32.const 3
    i32.const 72
    i32.const 3
    array.new_data $bytes $strings
    struct.new $string
    struct.new $exception
    local.set $pos.1
    local.get $pos.1
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
  (func $_start (type 47)
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
  (func $descriptors (type 47)
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
  (func $pos.uniform (type 49) (param $closure (ref $clos)) (param $a0 eqref) (result eqref)
    local.get $closure
    local.get $a0
    call $unboxInt
    call $pos
    ref.i31
  )
  (func $nonEmpty.uniform (type 49) (param $closure (ref $clos)) (param $a0 eqref) (result eqref)
    local.get $closure
    local.get $a0
    call $nonEmpty
    ref.i31
  )
  (func $f.uniform (type 49) (param $closure (ref $clos)) (param $a0 eqref) (result eqref)
    local.get $closure
    local.get $a0
    call $unboxInt
    call $f
    call $boxInt
  )
  (func $qa_adapt.uniform (type 49) (param $closure (ref $clos)) (param $a0 eqref) (result eqref)
    local.get $closure
    local.get $a0
    call $qa_adapt
    ref.i31
  )
  (func $qa_adapt.uniform.1 (type 49) (param $closure (ref $clos)) (param $a0 eqref) (result eqref)
    local.get $closure
    local.get $a0
    call $qa_adapt.1
    ref.i31
  )
  (func $qa_adapt.uniform.2 (type 49) (param $closure (ref $clos)) (param $a0 eqref) (result eqref)
    local.get $closure
    local.get $a0
    call $unboxInt
    call $qa_adapt.3
    call $boxInt
  )
  (data $strings "!Tuple first: Int second: String endfirstsecond\0aabc\0ayesno\0a\0a\0ahihi\0aseven \0abad/Users/haahr/Dropbox/Paul/src/quest/.claude/worktrees/wasm-plan-opus/tests/self-hosted/wasm/polymorphism.quest:22:1Tuple first: Int second: String end")
)


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
  (type (func (param eqref)))
  (type (func))
  (type (func (param (ref $clos) eqref eqref) (result eqref)))
  (type (func (param (ref $clos) i64) (result i64)))
  (type (func (param (ref $clos) i64 eqref) (result i64)))
  (type (func (param (ref $clos) eqref) (result eqref)))
  (type $closU1 (sub $clos (struct (field $hash (mut i32)) (field $uniform (ref 38)))))
  (type (sub $closU1 (struct (field $hash (mut i32)) (field $uniform (ref 38)) (field $native (ref 36)))))
  (type $f.closure (sub final 40 (struct (field $hash (mut i32)) (field $uniform (ref 38)) (field $native (ref 36)))))
  (type $closU2 (sub $clos (struct (field $hash (mut i32)) (field $uniform (ref 35)))))
  (type (sub $closU2 (struct (field $hash (mut i32)) (field $uniform (ref 35)) (field $native (ref 37)))))
  (type $countDown.closure (sub final 43 (struct (field $hash (mut i32)) (field $uniform (ref 35)) (field $native (ref 37)))))
  (type (func (param (ref $clos) i64 i64) (result i64)))
  (type (sub $closU2 (struct (field $hash (mut i32)) (field $uniform (ref 35)) (field $native (ref 45)))))
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
  (import "quest.runtime" "error" (tag $error (type 33)))
  (import "writer" "init" (func $writer.init (type 34)))
  (import "conv" "init" (func $conv.init (type 34)))
  (import "string" "init" (func $string.init (type 34)))
  (import "wasm/print" "init" (func $wasm/print.init (type 34)))
  (import "wasm/print" "show" (func $wasm/print.show (type 35)))
  (global $noClosure (ref $clos) i32.const 0 struct.new $clos)
  (global $f.static (ref $f.closure) i32.const 0 ref.func $f.uniform ref.func $f struct.new $f.closure)
  (global $countDown.static (ref $countDown.closure) i32.const 0 ref.func $countDown.uniform ref.func $countDown struct.new $countDown.closure)
  (global $countDown.1 (mut eqref) ref.null none)
  (global $builtin+.static (ref 46) i32.const 0 ref.func $builtin+.uniform ref.func $builtin+ struct.new 46)
  (global $builtin-.static (ref 46) i32.const 0 ref.func $builtin-.uniform ref.func $builtin- struct.new 46)
  (export "_start" (func $_start))
  (elem declare func $f.uniform $f $countDown.uniform $countDown $builtin+ $builtin+.uniform $builtin- $builtin-.uniform)
  (func $f (type 36) (param $closure (ref $clos)) (param $x i64) (result i64)
    (local $v i64)
    local.get $x
    i64.const 5
    i64.add
    local.set $v
    local.get $v
    return
    unreachable
  )
  (func $countDown (type 37) (param $closure (ref $clos)) (param $n i64) (param $k eqref) (result i64)
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
      ref.test (ref 40)
      if
        local.get $t
        ref.cast (ref $clos)
        i64.const 0
        local.get $t
        ref.cast (ref 40)
        struct.get 40 $native
        return_call_ref 36
      else
        local.get $t
        ref.cast (ref $clos)
        i64.const 0
        call $boxInt
        local.get $t
        ref.cast (ref $closU1)
        struct.get $closU1 $uniform
        call_ref 38
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
  (func $main (type 34)
    (local $f eqref)
    (local $v eqref)
    (local $v.1 eqref)
    (local $f.1 eqref)
    (local $x i64)
    (local $n i64)
    (local $f.2 eqref)
    (local $x.1 i64)
    (local $n.1 i64)
    (local $v.2 i32)
    (local $t eqref)
    (local $v.3 i64)
    (local $v.4 i64)
    (local $v.5 i64)
    (local $v.6 eqref)
    (local $v.7 eqref)
    (local $v.8 eqref)
    (local $v.9 eqref)
    (local $v.10 eqref)
    (local $v.11 eqref)
    (local $v.12 eqref)
    (local $v.13 eqref)
    (local $names eqref)
    (local $t.1 i64)
    (local $v.14 i64)
    (local $v.15 i64)
    (local $i i64)
    (local $v.16 i32)
    (local $i.1 i64)
    (local $v.17 eqref)
    (local $v.18 i64)
    (local $v.19 i64)
    (local $v.20 i32)
    (local $v.21 i64)
    (local $v.22 i64)
    (local $v.23 eqref)
    (local $v.24 eqref)
    (local $v.25 eqref)
    (local $v.26 eqref)
    (local $v.27 eqref)
    (local $v.28 eqref)
    (local $v.29 eqref)
    (local $v.30 eqref)
    (local $v.31 eqref)
    (local $v.32 eqref)
    (local $v.33 eqref)
    (local $n.2 i64)
    (local $n.3 i64)
    (local $v.34 i32)
    (local $v.35 i64)
    (local $v.36 i64)
    (local $v.37 eqref)
    (local $v.38 eqref)
    (local $v.39 eqref)
    (local $v.40 eqref)
    (local $s eqref)
    (local $v.41 eqref)
    (local $s.1 eqref)
    (local $v.42 eqref)
    (local $v.43 eqref)
    (local $v.44 eqref)
    (local $v.45 eqref)
    (local $v.46 eqref)
    (local $v.47 eqref)
    (local $v.48 eqref)
    (local $v.49 eqref)
    (local $r i64)
    (local $v.50 i64)
    (local $v.51 i64)
    (local $i.2 i64)
    (local $v.52 i32)
    (local $i.3 i64)
    (local $v.53 i64)
    (local $t.2 eqref)
    (local $v.54 i64)
    (local $v.55 i32)
    (local $v.56 i64)
    (local $v.57 i64)
    (local $v.58 eqref)
    (local $v.59 eqref)
    (local $v.60 eqref)
    (local $r.1 i64)
    (local $v.61 i64)
    (local $v.62 i64)
    (local $i.4 i64)
    (local $v.63 i32)
    (local $i.5 i64)
    (local $v.64 i64)
    (local $t.3 eqref)
    (local $v.65 i64)
    (local $v.66 i32)
    (local $v.67 i64)
    (local $v.68 i64)
    (local $v.69 eqref)
    (local $v.70 eqref)
    (local $v.71 eqref)
    (local $v.72 eqref)
    (local $v.73 eqref)
    (local $v.74 eqref)
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
        local.set $f.1
        i64.const 0
        local.set $x
        i64.const 1000000
        local.set $n
        block $contified6.exit
          loop $contified6
            local.get $f.1
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
              ref.test (ref 40)
              if (result i64)
                local.get $t
                ref.cast (ref $clos)
                local.get $x.1
                local.get $t
                ref.cast (ref 40)
                struct.get 40 $native
                call_ref 36
              else
                local.get $t
                ref.cast (ref $clos)
                local.get $x.1
                call $boxInt
                local.get $t
                ref.cast (ref $closU1)
                struct.get $closU1 $uniform
                call_ref 38
                call $unboxInt
              end
              local.set $v.3
              local.get $n.1
              i64.const 1
              i64.sub
              local.set $v.4
              local.get $f.2
              local.set $f.1
              local.get $v.3
              local.set $x
              local.get $v.4
              local.set $n
              br $contified6
            end
            br $contified6
          end
        end
        br $contified7.after
      end
      local.set $v.5
      local.get $v.5
      call $convInt
      local.set $v.6
      i32.const 0
      i32.const 1
      i32.const 0
      i32.const 1
      array.new_data $bytes $strings
      struct.new $string
      local.get $v.6
      call $concat
      local.set $v.7
      local.get $v.1
      local.get $v.7
      call $concat
      local.set $v.8
      i32.const 0
      i32.const 1
      i32.const 1
      i32.const 1
      array.new_data $bytes $strings
      struct.new $string
      local.get $v.8
      call $concat
      local.set $v.9
      local.get $v
      local.get $v.9
      call $concat
      local.set $v.10
      i32.const 1
      ref.i31
      local.set $v.11
      local.get $v.10
      i32.const 0
      i32.const 1
      i32.const 2
      i32.const 1
      array.new_data $bytes $strings
      struct.new $string
      call $concat
      local.set $v.12
      local.get $v.11
      local.get $v.12
      call $putString
      local.set $v.13
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
      local.set $names
      i64.const 0
      local.set $t.1
      local.get $names
      ref.cast (ref $array)
      struct.get $array $elems
      array.len
      i64.extend_i32_u
      local.set $v.14
      local.get $v.14
      i64.const 1
      i64.sub
      local.set $v.15
      i64.const 0
      local.set $i
      local.get $i
      local.get $v.15
      i64.le_s
      local.set $v.16
      local.get $v.16
      if
        block $L1_1.exit
          loop $L1_1
            local.get $i
            local.set $i.1
            local.get $i.1
            local.get $names
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
            local.get $names
            ref.cast (ref $array)
            struct.get $array $elems
            local.get $i.1
            i32.wrap_i64
            array.get $slots
            local.set $v.17
            local.get $v.17
            ref.cast (ref $string)
            struct.get $string $length
            i64.extend_i32_u
            local.set $v.18
            local.get $t.1
            local.get $v.18
            i64.add
            local.set $v.19
            local.get $v.19
            local.set $t.1
            local.get $i
            local.get $v.15
            i64.eq
            local.set $v.20
            local.get $v.20
            if
              br $L1_1.exit
            else
            end
            local.get $i
            i64.const 1
            i64.add
            local.set $v.21
            local.get $v.21
            local.set $i
            br $L1_1
          end
        end
      else
      end
      local.get $t.1
      local.set $v.22
      local.get $v.22
      call $convInt
      local.set $v.23
      i32.const 1
      ref.i31
      local.set $v.24
      local.get $v.23
      i32.const 0
      i32.const 1
      i32.const 121
      i32.const 1
      array.new_data $bytes $strings
      struct.new $string
      call $concat
      local.set $v.25
      local.get $v.24
      local.get $v.25
      call $putString
      local.set $v.26
      i64.const 13
      call $convInt
      local.set $v.27
      i64.const 106
      call $convInt
      local.set $v.28
      i32.const 0
      i32.const 1
      i32.const 122
      i32.const 1
      array.new_data $bytes $strings
      struct.new $string
      local.get $v.28
      call $concat
      local.set $v.29
      local.get $v.27
      local.get $v.29
      call $concat
      local.set $v.30
      i32.const 1
      ref.i31
      local.set $v.31
      local.get $v.30
      i32.const 0
      i32.const 1
      i32.const 123
      i32.const 1
      array.new_data $bytes $strings
      struct.new $string
      call $concat
      local.set $v.32
      local.get $v.31
      local.get $v.32
      call $putString
      local.set $v.33
      global.get $countDown.static
      global.set $countDown.1
      block $contified9.after
        block $contified9 (result i64)
          i64.const 1000000
          local.set $n.2
          block $contified8.exit
            loop $contified8
              local.get $n.2
              local.set $n.3
              local.get $n.3
              i64.const 0
              i64.eq
              local.set $v.34
              local.get $v.34
              if
                i64.const 1
                br $contified9
              else
                local.get $n.3
                i64.const 1
                i64.sub
                local.set $v.35
                local.get $v.35
                local.set $n.2
                br $contified8
              end
              br $contified8
            end
          end
          br $contified9.after
        end
        local.set $v.36
        local.get $v.36
        call $convInt
        local.set $v.37
        i32.const 1
        ref.i31
        local.set $v.38
        local.get $v.37
        i32.const 0
        i32.const 1
        i32.const 124
        i32.const 1
        array.new_data $bytes $strings
        struct.new $string
        call $concat
        local.set $v.39
        local.get $v.38
        local.get $v.39
        call $putString
        local.set $v.40
        i32.const 0
        i32.const 3
        i32.const 125
        i32.const 3
        array.new_data $bytes $strings
        struct.new $string
        local.set $s
        local.get $s
        i32.const 0
        i32.const 1
        i32.const 128
        i32.const 1
        array.new_data $bytes $strings
        struct.new $string
        call $concat
        local.set $v.41
        i32.const 0
        i32.const 2
        i32.const 129
        i32.const 2
        array.new_data $bytes $strings
        struct.new $string
        local.set $s.1
        local.get $s.1
        i32.const 0
        i32.const 1
        i32.const 131
        i32.const 1
        array.new_data $bytes $strings
        struct.new $string
        call $concat
        local.set $v.42
        i32.const 0
        i32.const 1
        i32.const 132
        i32.const 1
        array.new_data $bytes $strings
        struct.new $string
        local.get $v.42
        call $concat
        local.set $v.43
        local.get $v.41
        local.get $v.43
        call $concat
        local.set $v.44
        i32.const 1
        ref.i31
        local.set $v.45
        local.get $v.44
        i32.const 0
        i32.const 1
        i32.const 133
        i32.const 1
        array.new_data $bytes $strings
        struct.new $string
        call $concat
        local.set $v.46
        local.get $v.45
        local.get $v.46
        call $putString
        local.set $v.47
        global.get $builtin+.static
        local.set $v.48
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
        local.set $v.49
        i64.const 0
        local.set $r
        local.get $v.49
        ref.cast (ref $array)
        struct.get $array $elems
        array.len
        i64.extend_i32_u
        local.set $v.50
        local.get $v.50
        i64.const 1
        i64.sub
        local.set $v.51
        i64.const 0
        local.set $i.2
        local.get $i.2
        local.get $v.51
        i64.le_s
        local.set $v.52
        local.get $v.52
        if
          block $L2_4.exit
            loop $L2_4
              local.get $i.2
              local.set $i.3
              local.get $i.3
              local.get $v.49
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
              local.get $v.49
              ref.cast (ref $array)
              struct.get $array $elems
              local.get $i.3
              i32.wrap_i64
              array.get $slots
              call $unboxInt
              local.set $v.53
              local.get $v.48
              local.set $t.2
              local.get $t.2
              ref.test (ref 46)
              if (result i64)
                local.get $t.2
                ref.cast (ref $clos)
                local.get $r
                local.get $v.53
                local.get $t.2
                ref.cast (ref 46)
                struct.get 46 $native
                call_ref 45
              else
                local.get $t.2
                ref.cast (ref $clos)
                local.get $r
                call $boxInt
                local.get $v.53
                call $boxInt
                local.get $t.2
                ref.cast (ref $closU2)
                struct.get $closU2 $uniform
                call_ref 35
                call $unboxInt
              end
              local.set $v.54
              local.get $v.54
              local.set $r
              local.get $i.2
              local.get $v.51
              i64.eq
              local.set $v.55
              local.get $v.55
              if
                br $L2_4.exit
              else
              end
              local.get $i.2
              i64.const 1
              i64.add
              local.set $v.56
              local.get $v.56
              local.set $i.2
              br $L2_4
            end
          end
        else
        end
        local.get $r
        local.set $v.57
        local.get $v.57
        call $convInt
        local.set $v.58
        global.get $builtin-.static
        local.set $v.59
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
        local.set $v.60
        i64.const 100
        local.set $r.1
        local.get $v.60
        ref.cast (ref $array)
        struct.get $array $elems
        array.len
        i64.extend_i32_u
        local.set $v.61
        local.get $v.61
        i64.const 1
        i64.sub
        local.set $v.62
        i64.const 0
        local.set $i.4
        local.get $i.4
        local.get $v.62
        i64.le_s
        local.set $v.63
        local.get $v.63
        if
          block $L2_5.exit
            loop $L2_5
              local.get $i.4
              local.set $i.5
              local.get $i.5
              local.get $v.60
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
              local.get $v.60
              ref.cast (ref $array)
              struct.get $array $elems
              local.get $i.5
              i32.wrap_i64
              array.get $slots
              call $unboxInt
              local.set $v.64
              local.get $v.59
              local.set $t.3
              local.get $t.3
              ref.test (ref 46)
              if (result i64)
                local.get $t.3
                ref.cast (ref $clos)
                local.get $r.1
                local.get $v.64
                local.get $t.3
                ref.cast (ref 46)
                struct.get 46 $native
                call_ref 45
              else
                local.get $t.3
                ref.cast (ref $clos)
                local.get $r.1
                call $boxInt
                local.get $v.64
                call $boxInt
                local.get $t.3
                ref.cast (ref $closU2)
                struct.get $closU2 $uniform
                call_ref 35
                call $unboxInt
              end
              local.set $v.65
              local.get $v.65
              local.set $r.1
              local.get $i.4
              local.get $v.62
              i64.eq
              local.set $v.66
              local.get $v.66
              if
                br $L2_5.exit
              else
              end
              local.get $i.4
              i64.const 1
              i64.add
              local.set $v.67
              local.get $v.67
              local.set $i.4
              br $L2_5
            end
          end
        else
        end
        local.get $r.1
        local.set $v.68
        local.get $v.68
        call $convInt
        local.set $v.69
        i32.const 0
        i32.const 1
        i32.const 358
        i32.const 1
        array.new_data $bytes $strings
        struct.new $string
        local.get $v.69
        call $concat
        local.set $v.70
        local.get $v.58
        local.get $v.70
        call $concat
        local.set $v.71
        i32.const 1
        ref.i31
        local.set $v.72
        local.get $v.71
        i32.const 0
        i32.const 1
        i32.const 359
        i32.const 1
        array.new_data $bytes $strings
        struct.new $string
        call $concat
        local.set $v.73
        local.get $v.72
        local.get $v.73
        call $putString
        local.set $v.74
      end
    end
  )
  (func $_start (type 34)
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
  (func $f.uniform (type 38) (param $closure (ref $clos)) (param $a0 eqref) (result eqref)
    local.get $closure
    local.get $a0
    call $unboxInt
    call $f
    call $boxInt
  )
  (func $countDown.uniform (type 35) (param $closure (ref $clos)) (param $a0 eqref) (param $a1 eqref) (result eqref)
    local.get $closure
    local.get $a0
    call $unboxInt
    local.get $a1
    call $countDown
    call $boxInt
  )
  (func $builtin+ (type 45) (param $closure (ref $clos)) (param $a i64) (param $b i64) (result i64)
    local.get $a
    local.get $b
    i64.add
  )
  (func $builtin+.uniform (type 35) (param $closure (ref $clos)) (param $a eqref) (param $b eqref) (result eqref)
    local.get $closure
    local.get $a
    call $unboxInt
    local.get $b
    call $unboxInt
    call $builtin+
    call $boxInt
  )
  (func $builtin- (type 45) (param $closure (ref $clos)) (param $a i64) (param $b i64) (result i64)
    local.get $a
    local.get $b
    i64.sub
  )
  (func $builtin-.uniform (type 35) (param $closure (ref $clos)) (param $a eqref) (param $b eqref) (result eqref)
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


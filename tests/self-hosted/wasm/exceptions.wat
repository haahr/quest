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
  (type (func (param (ref $clos) i64) (result eqref)))
  (type (func (param (ref $clos) i64 eqref i64 i64) (result eqref)))
  (type (func (param (ref $clos) eqref i64 eqref eqref) (result eqref)))
  (type (func (param (ref $clos) eqref i64 i64 eqref) (result eqref)))
  (type (func (param (ref $clos) eqref eqref eqref eqref) (result eqref)))
  (type (func (param (ref $clos) i64) (result i64)))
  (type (func (param (ref $clos) eqref) (result eqref)))
  (type $closU1 (sub $clos (struct (field $hash (mut i32)) (field $uniform (ref 42)))))
  (type (sub $closU1 (struct (field $hash (mut i32)) (field $uniform (ref 42)) (field $native (ref 41)))))
  (type $tries.closure (sub final 44 (struct (field $hash (mut i32)) (field $uniform (ref 42)) (field $native (ref 41)))))
  (type $tries.closure.1 (sub final 44 (struct (field $hash (mut i32)) (field $uniform (ref 42)) (field $native (ref 41)))))
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
  (import "wasm/print" "init" (func $wasm/print.init (type 34)))
  (import "wasm/print" "show" (func $wasm/print.show (type 35)))
  (import "wasm/core" "init" (func $wasm/core.init (type 34)))
  (import "wasm/core" "base" (func $wasm/core.base (type 36)))
  (import "wasm/core" "newDesc" (func $wasm/core.newDesc (type 37)))
  (import "wasm/core" "setPart" (func $wasm/core.setPart (type 38)))
  (import "wasm/core" "setText" (func $wasm/core.setText (type 39)))
  (import "wasm/core" "instantiate" (func $wasm/core.instantiate (type 35)))
  (import "wasm/print" "echo" (func $wasm/print.echo (type 40)))
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
  (func $tries (type 41) (param $closure (ref $clos)) (param $i i64) (result i64)
    (local $v i32)
    (local $v.1 i64)
    (local $v.2 i64)
    (local $e eqref)
    (local $v.3 i32)
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
            local.set $v.2
            local.get $v.2
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
        local.set $v.3
        local.get $v.3
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
  (func $tries.1 (type 41) (param $closure (ref $clos)) (param $i i64) (result i64)
    (local $v i32)
    (local $v.1 i64)
    (local $v.2 i64)
    (local $e eqref)
    (local $v.3 i32)
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
            local.set $v.2
            local.get $v.2
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
        local.set $v.3
        local.get $v.3
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
  (func $main (type 34)
    (local $bad eqref)
    (local $other eqref)
    (local $named eqref)
    (local $e eqref)
    (local $v i32)
    (local $x i64)
    (local $v.1 i64)
    (local $v.2 i32)
    (local $r i64)
    (local $v.3 eqref)
    (local $v.4 eqref)
    (local $v.5 eqref)
    (local $v.6 eqref)
    (local $v.7 eqref)
    (local $v.8 i64)
    (local $e.1 eqref)
    (local $v.9 i32)
    (local $v.10 i64)
    (local $v.11 eqref)
    (local $v.12 eqref)
    (local $e.2 eqref)
    (local $v.13 i32)
    (local $v.14 i64)
    (local $v.15 eqref)
    (local $v.16 eqref)
    (local $v.17 eqref)
    (local $v.18 eqref)
    (local $v.19 eqref)
    (local $v.20 eqref)
    (local $e.3 eqref)
    (local $v.21 i64)
    (local $v.22 eqref)
    (local $v.23 eqref)
    (local $v.24 eqref)
    (local $v.25 eqref)
    (local $e.4 eqref)
    (local $v.26 i32)
    (local $e.5 eqref)
    (local $v.27 i32)
    (local $x.1 i64)
    (local $v.28 i64)
    (local $v.29 i64)
    (local $v.30 eqref)
    (local $v.31 eqref)
    (local $v.32 eqref)
    (local $v.33 eqref)
    (local $caught i64)
    (local $i i64)
    (local $v.34 i32)
    (local $i.1 i64)
    (local $v.35 i32)
    (local $v.36 i64)
    (local $e.6 eqref)
    (local $v.37 i32)
    (local $r.1 i64)
    (local $v.38 i64)
    (local $v.39 i32)
    (local $v.40 i64)
    (local $v.41 eqref)
    (local $v.42 eqref)
    (local $v.43 eqref)
    (local $v.44 eqref)
    (local $v.45 i32)
    (local $v.46 eqref)
    (local $v.47 eqref)
    (local $v.48 eqref)
    (local $v.49 eqref)
    (local $v.50 i64)
    (local $v.51 eqref)
    (local $v.52 i64)
    (local $v.53 eqref)
    (local $v.54 eqref)
    (local $v.55 eqref)
    (local $v.56 eqref)
    (local $v.57 eqref)
    (local $v.58 eqref)
    call $wasm/core.init
    call $wasm/print.init
    call $descriptors
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
            local.set $v.1
            local.get $v.1
            br $k2
          else
            local.get $e
            call $exceptionOf
            local.get $other
            call $exceptionOf
            ref.eq
            local.set $v.2
            local.get $v.2
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
      local.set $r
      local.get $r
      call $convInt
      local.set $v.3
      i32.const 1
      ref.i31
      local.set $v.4
      local.get $v.3
      i32.const 0
      i32.const 1
      i32.const 358
      i32.const 1
      array.new_data $bytes $strings
      struct.new $string
      call $concat
      local.set $v.5
      local.get $v.4
      local.get $v.5
      call $putString
      local.set $v.6
      block $inlined1.after
        block $inlined1 (result i64)
          global.get $int.error
          local.set $v.7
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
                local.set $v.8
                local.get $v.8
                br $inlined1
              end
              unreachable
            end
            local.set $e.1
            local.get $e.1
            call $exceptionOf
            local.get $v.7
            call $exceptionOf
            ref.eq
            local.set $v.9
            local.get $v.9
            if
              i64.const -1
              br $inlined1
            else
              local.get $e.1
              throw $error
            end
          end
          br $inlined1.after
        end
        local.set $v.10
        local.get $v.10
        call $convInt
        local.set $v.11
        block $inlined2.after
          block $inlined2 (result i64)
            global.get $int.error
            local.set $v.12
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
              local.get $v.12
              call $exceptionOf
              ref.eq
              local.set $v.13
              local.get $v.13
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
          local.set $v.14
          local.get $v.14
          call $convInt
          local.set $v.15
          i32.const 0
          i32.const 1
          i32.const 473
          i32.const 1
          array.new_data $bytes $strings
          struct.new $string
          local.get $v.15
          call $concat
          local.set $v.16
          local.get $v.11
          local.get $v.16
          call $concat
          local.set $v.17
          i32.const 1
          ref.i31
          local.set $v.18
          local.get $v.17
          i32.const 0
          i32.const 1
          i32.const 474
          i32.const 1
          array.new_data $bytes $strings
          struct.new $string
          call $concat
          local.set $v.19
          local.get $v.18
          local.get $v.19
          call $putString
          local.set $v.20
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
                local.set $e.3
                i64.const 7
                br $inlined3
              end
              br $inlined3.after
            end
            local.set $v.21
            local.get $v.21
            call $convInt
            local.set $v.22
            i32.const 1
            ref.i31
            local.set $v.23
            local.get $v.22
            i32.const 0
            i32.const 1
            i32.const 589
            i32.const 1
            array.new_data $bytes $strings
            struct.new $string
            call $concat
            local.set $v.24
            local.get $v.23
            local.get $v.24
            call $putString
            local.set $v.25
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
                        local.set $e.4
                        local.get $e.4
                        call $exceptionOf
                        local.get $other
                        call $exceptionOf
                        ref.eq
                        local.set $v.26
                        local.get $v.26
                        if
                          i64.const 0
                          br $inlined6
                        else
                          local.get $e.4
                          throw $error
                        end
                      end
                      br 2
                    end
                    unreachable
                  end
                  local.set $e.5
                  local.get $e.5
                  call $exceptionOf
                  local.get $bad
                  call $exceptionOf
                  ref.eq
                  local.set $v.27
                  local.get $v.27
                  if
                    local.get $e.5
                    call $payloadOf
                    call $unboxInt
                    local.set $x.1
                    local.get $x.1
                    i64.const 1000
                    i64.add
                    local.set $v.28
                    local.get $v.28
                    br $inlined6
                  else
                    local.get $e.5
                    throw $error
                  end
                end
                br $inlined6.after
              end
              local.set $v.29
              local.get $v.29
              call $convInt
              local.set $v.30
              i32.const 1
              ref.i31
              local.set $v.31
              local.get $v.30
              i32.const 0
              i32.const 1
              i32.const 707
              i32.const 1
              array.new_data $bytes $strings
              struct.new $string
              call $concat
              local.set $v.32
              local.get $v.31
              local.get $v.32
              call $putString
              local.set $v.33
              i64.const 0
              local.set $caught
              i64.const 1
              local.set $i
              local.get $i
              i64.const 10
              i64.le_s
              local.set $v.34
              local.get $v.34
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
                                  local.set $v.35
                                  local.get $v.35
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
                                local.set $v.36
                                local.get $v.36
                                br $k7
                              end
                              br 2
                            end
                            unreachable
                          end
                          local.set $e.6
                          local.get $e.6
                          call $exceptionOf
                          local.get $bad
                          call $exceptionOf
                          ref.eq
                          local.set $v.37
                          local.get $v.37
                          if
                            i64.const 100
                            br $k7
                          else
                            local.get $e.6
                            throw $error
                          end
                        end
                        br $k7.after
                      end
                      local.set $r.1
                      local.get $caught
                      local.get $r.1
                      i64.add
                      local.set $v.38
                      local.get $v.38
                      local.set $caught
                      local.get $i
                      i64.const 10
                      i64.eq
                      local.set $v.39
                      local.get $v.39
                      if
                        br $L1.exit
                      else
                      end
                      local.get $i
                      i64.const 1
                      i64.add
                      local.set $v.40
                      local.get $v.40
                      local.set $i
                    end
                    br $L1
                  end
                end
              else
              end
              local.get $caught
              call $convInt
              local.set $v.41
              i32.const 1
              ref.i31
              local.set $v.42
              local.get $v.41
              i32.const 0
              i32.const 1
              i32.const 825
              i32.const 1
              array.new_data $bytes $strings
              struct.new $string
              call $concat
              local.set $v.43
              local.get $v.42
              local.get $v.43
              call $putString
              local.set $v.44
              local.get $other
              call $exceptionOf
              local.get $other
              call $exceptionOf
              ref.eq
              local.set $v.45
              local.get $v.45
              call $convBool
              local.set $v.46
              i32.const 1
              ref.i31
              local.set $v.47
              local.get $v.46
              i32.const 0
              i32.const 1
              i32.const 826
              i32.const 1
              array.new_data $bytes $strings
              struct.new $string
              call $concat
              local.set $v.48
              local.get $v.47
              local.get $v.48
              call $putString
              local.set $v.49
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
              local.set $v.50
              local.get $v.50
              call $convInt
              local.set $v.51
              global.get $tries.static.1
              global.set $tries.3
              global.get $noClosure
              i64.const 0
              call $tries.1
              local.set $v.52
              local.get $v.52
              call $convInt
              local.set $v.53
              i32.const 0
              i32.const 1
              i32.const 831
              i32.const 1
              array.new_data $bytes $strings
              struct.new $string
              local.get $v.53
              call $concat
              local.set $v.54
              local.get $v.51
              local.get $v.54
              call $concat
              local.set $v.55
              i32.const 1
              ref.i31
              local.set $v.56
              local.get $v.55
              i32.const 0
              i32.const 1
              i32.const 832
              i32.const 1
              array.new_data $bytes $strings
              struct.new $string
              call $concat
              local.set $v.57
              local.get $v.56
              local.get $v.57
              call $putString
              local.set $v.58
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
  (func $descriptors (type 34)
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
  (func $tries.uniform (type 42) (param $closure (ref $clos)) (param $a0 eqref) (result eqref)
    local.get $closure
    local.get $a0
    call $unboxInt
    call $tries
    call $boxInt
  )
  (func $tries.uniform.1 (type 42) (param $closure (ref $clos)) (param $a0 eqref) (result eqref)
    local.get $closure
    local.get $a0
    call $unboxInt
    call $tries.1
    call $boxInt
  )
  (data $strings "/Users/haahr/Dropbox/Paul/src/quest/.claude/worktrees/wasm-plan-opus/tests/self-hosted/wasm/exceptions.quest:32:28/Users/haahr/Dropbox/Paul/src/quest/.claude/worktrees/wasm-plan-opus/tests/self-hosted/wasm/exceptions.quest:32:28badothernamed/Users/haahr/Dropbox/Paul/src/quest/.claude/worktrees/wasm-plan-opus/tests/self-hosted/wasm/exceptions.quest:10:36Int\0a/Users/haahr/Dropbox/Paul/src/quest/.claude/worktrees/wasm-plan-opus/tests/self-hosted/wasm/exceptions.quest:13:26 \0a/Users/haahr/Dropbox/Paul/src/quest/.claude/worktrees/wasm-plan-opus/tests/self-hosted/wasm/exceptions.quest:15:20\0a/Users/haahr/Dropbox/Paul/src/quest/.claude/worktrees/wasm-plan-opus/tests/self-hosted/wasm/exceptions.quest:10:36Int\0a/Users/haahr/Dropbox/Paul/src/quest/.claude/worktrees/wasm-plan-opus/tests/self-hosted/wasm/exceptions.quest:10:36Int\0a\0astop \0athe end/Users/haahr/Dropbox/Paul/src/quest/.claude/worktrees/wasm-plan-opus/tests/self-hosted/wasm/exceptions.quest:36:1String")
)


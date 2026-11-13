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
  )
  (type (func (param eqref eqref) (result eqref)))
  (type (func (param eqref i32) (result eqref)))
  (type (func (param i64) (result eqref)))
  (type (func (param i32) (result eqref)))
  (type (func (param eqref eqref)))
  (type (func (param eqref)))
  (type (func (param eqref) (result i64)))
  (type (func (param eqref i32)))
  (type (func (param eqref i64) (result i32)))
  (type (func (param eqref i64 i32) (result eqref)))
  (type (func (param i64 i32) (result eqref)))
  (type (func (param eqref i64 i64) (result eqref)))
  (type (func (param eqref i64 eqref i64 i64) (result eqref)))
  (type (func (param eqref eqref) (result i32)))
  (type (func))
  (type (func (param i64 i64) (result i64 i64)))
  (type (func (param eqref) (result (ref $option))))
  (import "quest.runtime" "putString" (func $putString (type 16)))
  (import "quest.runtime" "putChar" (func $putChar (type 17)))
  (import "quest.runtime" "concat" (func $concat (type 16)))
  (import "quest.runtime" "convInt" (func $convInt (type 18)))
  (import "quest.runtime" "convBool" (func $convBool (type 19)))
  (import "quest.runtime" "convChar" (func $convChar (type 19)))
  (import "quest.runtime" "fail" (func $fail (type 20)))
  (import "quest.runtime" "uncaught" (func $uncaught (type 21)))
  (import "quest.runtime" "decimal" (func $decimal (type 18)))
  (import "quest.runtime" "hex" (func $hex (type 18)))
  (import "quest.runtime" "escaped" (func $escaped (type 17)))
  (import "quest.runtime" "boxInt" (func $boxInt (type 18)))
  (import "quest.runtime" "unboxInt" (func $unboxInt (type 22)))
  (import "quest.runtime" "fatal" (func $fatal (type 23)))
  (import "quest.runtime" "stringGetChar" (func $stringGetChar (type 24)))
  (import "quest.runtime" "stringSetChar" (func $stringSetChar (type 25)))
  (import "quest.runtime" "stringNew" (func $stringNew (type 26)))
  (import "quest.runtime" "stringGetSub" (func $stringGetSub (type 27)))
  (import "quest.runtime" "stringSetSub" (func $stringSetSub (type 28)))
  (import "quest.runtime" "stringEqual" (func $stringEqual (type 29)))
  (import "quest.runtime" "error" (tag $error (type 21)))
  (global $divide.1 (mut eqref) ref.null none)
  (global $dict (ref $dict) i32.const 0 i32.const 1 i32.const 2 array.new_fixed $i32s 3 struct.new $dict)
  (export "_start" (func $_start))
  (func $divide (type 31) (param $n i64) (param $d i64) (result i64 i64)
    (local $v i32)
    (local $v.1 i64)
    (local $v.2 i64)
    (local $v.3 i64)
    (local $t i64)
    (local $t.1 i64)
    (local $v.4 i64)
    (local $q i64)
    (local $r i64)
    (local $v.5 i64)
    (local $v.6 i64)
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
      local.set $v.3
      local.get $v.3
      local.get $d
      call $divide
      local.set $t.1
      local.set $t
      local.get $t
      local.set $v.4
      local.get $v.4
      i64.const 1
      i64.add
      local.set $q
      local.get $t.1
      local.set $r
      local.get $q
      local.get $r
      local.set $v.6
      local.set $v.5
      local.get $v.5
      local.get $v.6
      return
    end
    unreachable
  )
  (func $main (type 30)
    (local $v eqref)
    (local $t (ref null $slots))
    (local $v.1 eqref)
    (local $v.2 eqref)
    (local $t.1 (ref null $slots))
    (local $v.3 eqref)
    (local $v.4 eqref)
    (local $v.5 eqref)
    (local $t.2 (ref null $slots))
    (local $v.6 eqref)
    (local $shapes eqref)
    (local $v.7 i64)
    (local $v.8 i64)
    (local $i i64)
    (local $v.9 i32)
    (local $i.1 i64)
    (local $v.10 eqref)
    (local $t.3 (ref null $option))
    (local $c eqref)
    (local $v.11 i64)
    (local $v.12 i64)
    (local $v.13 i64)
    (local $v.14 i64)
    (local $q eqref)
    (local $v.15 i64)
    (local $v.16 i64)
    (local $v.17 i64)
    (local $p eqref)
    (local $v.18 i64)
    (local $v.19 i64)
    (local $v.20 i64)
    (local $v.21 i64)
    (local $v.22 eqref)
    (local $v.23 eqref)
    (local $v.24 eqref)
    (local $v.25 eqref)
    (local $v.26 i32)
    (local $v.27 i64)
    (local $v.28 eqref)
    (local $t.4 (ref null $slots))
    (local $pt eqref)
    (local $v.29 i64)
    (local $v.30 eqref)
    (local $v.31 i64)
    (local $v.32 eqref)
    (local $v.33 eqref)
    (local $v.34 eqref)
    (local $v.35 eqref)
    (local $v.36 eqref)
    (local $v.37 eqref)
    (local $v.38 eqref)
    (local $v.39 eqref)
    (local $t.5 eqref)
    (local $t.6 eqref)
    (local $t.7 i32)
    (local $t.8 i32)
    (local $v.40 i32)
    (local $v.41 eqref)
    (local $v.42 eqref)
    (local $v.43 i32)
    (local $v.44 eqref)
    (local $v.45 eqref)
    (local $t.9 i32)
    (local $v.46 i64)
    (local $v.47 eqref)
    (local $v.48 eqref)
    (local $v.49 eqref)
    (local $t.10 eqref)
    (local $t.11 eqref)
    (local $t.12 i32)
    (local $t.13 i32)
    (local $v.50 i32)
    (local $v.51 eqref)
    (local $v.52 eqref)
    (local $v.53 eqref)
    (local $v.54 eqref)
    (local $v.55 eqref)
    (local $v.56 eqref)
    (local $v.57 eqref)
    (local $v.58 eqref)
    (local $v.59 eqref)
    (local $v.60 eqref)
    (local $t.14 i32)
    (local $light eqref)
    (local $v.61 i32)
    (local $v.62 eqref)
    (local $t.15 i32)
    (local $v.63 i64)
    (local $v.64 eqref)
    (local $v.65 eqref)
    (local $v.66 eqref)
    (local $v.67 eqref)
    (local $v.68 eqref)
    (local $v.69 eqref)
    (local $v.70 eqref)
    (local $t.16 (ref null $slots))
    (local $m eqref)
    (local $v.71 eqref)
    (local $t.17 (ref null $slots))
    (local $n eqref)
    (local $v.72 eqref)
    (local $t.18 (ref null $slots))
    (local $o eqref)
    (local $t.19 eqref)
    (local $t.20 eqref)
    (local $t.21 i32)
    (local $t.22 i32)
    (local $t.23 eqref)
    (local $t.24 eqref)
    (local $v.73 i32)
    (local $v.74 eqref)
    (local $t.25 eqref)
    (local $t.26 eqref)
    (local $t.27 i32)
    (local $t.28 i32)
    (local $t.29 eqref)
    (local $t.30 eqref)
    (local $v.75 i32)
    (local $v.76 eqref)
    (local $v.77 eqref)
    (local $v.78 eqref)
    (local $v.79 eqref)
    (local $v.80 eqref)
    (local $v.81 eqref)
    (local $b eqref)
    (local $t.31 eqref)
    (local $v.82 eqref)
    (local $v.83 eqref)
    (local $v.84 eqref)
    (local $v.85 eqref)
    (local $v.86 eqref)
    (local $v.87 eqref)
    (local $v.88 eqref)
    (local $v.89 eqref)
    (local $v.90 eqref)
    (local $v.91 eqref)
    (local $qr i64)
    (local $qr.1 i64)
    (local $qr2 i64)
    (local $qr2.1 i64)
    (local $v.92 i64)
    (local $v.93 eqref)
    (local $v.94 i64)
    (local $v.95 eqref)
    (local $v.96 i64)
    (local $v.97 eqref)
    (local $v.98 i64)
    (local $v.99 eqref)
    (local $v.100 eqref)
    (local $v.101 eqref)
    (local $v.102 eqref)
    (local $v.103 eqref)
    (local $v.104 eqref)
    (local $v.105 eqref)
    (local $v.106 eqref)
    (local $v.107 eqref)
    (local $v.108 eqref)
    (local $a eqref)
    (local $i.2 i64)
    (local $v.109 i32)
    (local $i.3 i64)
    (local $v.110 i64)
    (local $v.111 i32)
    (local $v.112 i64)
    (local $v.113 i64)
    (local $v.114 eqref)
    (local $v.115 i64)
    (local $v.116 eqref)
    (local $v.117 eqref)
    (local $v.118 eqref)
    (local $v.119 eqref)
    (local $v.120 eqref)
    (local $v.121 eqref)
    (local $str eqref)
    (local $v.122 eqref)
    (local $v.123 i32)
    (local $v.124 eqref)
    (local $v.125 i32)
    (local $v.126 eqref)
    (local $v.127 eqref)
    (local $v.128 eqref)
    (local $v.129 eqref)
    (local $v.130 eqref)
    (local $v.131 eqref)
    (local $v.132 eqref)
    (local $v.133 eqref)
    (local $v.134 eqref)
    (local $v.135 eqref)
    (local $t.32 eqref)
    (local $p_box eqref)
    (local $t.33 (ref null $recBox))
    (local $p.1 eqref)
    (local $p.2 eqref)
    (local $t.34 eqref)
    (local $v.136 i64)
    (local $v.137 i64)
    (local $t.35 eqref)
    (local $t.36 eqref)
    (local $v.138 eqref)
    (local $t.37 eqref)
    (local $v.139 i64)
    (local $v.140 eqref)
    (local $t.38 eqref)
    (local $v.141 i64)
    (local $v.142 eqref)
    (local $v.143 eqref)
    (local $v.144 eqref)
    (local $v.145 eqref)
    (local $v.146 eqref)
    (local $v.147 eqref)
    (local $v.148 eqref)
    (local $v.149 eqref)
    (local $t.39 eqref)
    (local $box eqref)
    (local $t.40 (ref null $recBox))
    (local $v.150 eqref)
    (local $v.151 eqref)
    (local $ps eqref)
    (local $box.1 eqref)
    (local $t.41 (ref null $recBox))
    (local $v.152 eqref)
    (local $v.153 eqref)
    (local $t.42 eqref)
    (local $v.154 eqref)
    (local $box.2 eqref)
    (local $t.43 (ref null $recBox))
    (local $v.155 eqref)
    (local $v.156 eqref)
    (local $q.1 eqref)
    (local $q.2 eqref)
    (local $t.44 eqref)
    (local $v.157 i64)
    (local $t.45 eqref)
    (local $v.158 i64)
    (local $t.46 eqref)
    (local $v.159 i64)
    (local $t.47 eqref)
    (local $v.160 i64)
    (local $v.161 i64)
    (local $v.162 i64)
    (local $v.163 i64)
    (local $v.164 eqref)
    (local $t.48 eqref)
    (local $v.165 i64)
    (local $t.49 eqref)
    (local $v.166 i64)
    (local $t.50 eqref)
    (local $v.167 i64)
    (local $t.51 eqref)
    (local $v.168 i64)
    (local $v.169 i64)
    (local $v.170 i64)
    (local $v.171 i64)
    (local $v.172 eqref)
    (local $v.173 eqref)
    (local $v.174 eqref)
    (local $v.175 eqref)
    (local $v.176 eqref)
    (local $v.177 eqref)
    (local $v.178 eqref)
    (local $t.52 eqref)
    (local $v.179 eqref)
    (local $v.180 eqref)
    (local $v.181 eqref)
    (local $v.182 eqref)
    (local $v.183 eqref)
    (local $v.184 eqref)
    (local $v.185 i64)
    (local $v.186 eqref)
    (local $v.187 eqref)
    (local $v.188 eqref)
    (local $v.189 eqref)
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
    local.set $v.1
    i32.const 0
    i64.const 5
    call $boxInt
    array.new_fixed $slots 1
    struct.new $tuple
    local.set $v.2
    i32.const 0
    i32.const 1
    array.new_default $slots
    local.tee $t.1
    i32.const 0
    local.get $v.2
    ref.cast (ref $tuple)
    struct.get $tuple $slots
    i32.const 0
    i32.const 1
    array.copy $slots $slots
    local.get $t.1
    ref.as_non_null
    i32.const 3
    struct.new $option
    local.set $v.3
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
    local.tee $t.2
    i32.const 0
    local.get $v.5
    ref.cast (ref $tuple)
    struct.get $tuple $slots
    i32.const 0
    i32.const 2
    array.copy $slots $slots
    local.get $t.2
    ref.as_non_null
    i32.const 2
    struct.new $option
    local.set $v.6
    i32.const 0
    local.get $v.1
    local.get $v.3
    local.get $v.4
    local.get $v.6
    array.new_fixed $slots 4
    struct.new $array
    local.set $shapes
    local.get $shapes
    ref.cast (ref $array)
    struct.get $array $elems
    array.len
    i64.extend_i32_u
    local.set $v.7
    local.get $v.7
    i64.const 1
    i64.sub
    local.set $v.8
    i64.const 0
    local.set $i
    local.get $i
    local.get $v.8
    i64.le_s
    local.set $v.9
    local.get $v.9
    if
      block $L1.exit
        loop $L1
          local.get $i
          local.set $i.1
          local.get $i.1
          local.get $shapes
          ref.cast (ref $array)
          struct.get $array $elems
          array.len
          i64.extend_i32_u
          i64.lt_u
          i32.eqz
          if
            i32.const 0
            i32.const 13
            i32.const 0
            i32.const 13
            array.new_data $bytes $strings
            struct.new $string
            i32.const 0
            i32.const 114
            i32.const 13
            i32.const 114
            array.new_data $bytes $strings
            struct.new $string
            call $fail
            unreachable
          end
          local.get $shapes
          ref.cast (ref $array)
          struct.get $array $elems
          local.get $i.1
          i32.wrap_i64
          array.get $slots
          local.set $v.10
          block $inlined1.after
            block $inlined1 (result i64)
              local.get $v.10
              block (type 32)
                br_on_cast 0 eqref (ref $option)
                drop
                i32.const 0
                i32.const 51
                i32.const 127
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
                        local.set $c
                        local.get $c
                        ref.cast (ref $tuple)
                        struct.get $tuple $slots
                        i32.const 0
                        array.get $slots
                        call $unboxInt
                        local.set $v.11
                        local.get $c
                        ref.cast (ref $tuple)
                        struct.get $tuple $slots
                        i32.const 0
                        array.get $slots
                        call $unboxInt
                        local.set $v.12
                        local.get $v.11
                        local.get $v.12
                        i64.mul
                        local.set $v.13
                        i64.const 3
                        local.get $v.13
                        i64.mul
                        local.set $v.14
                        local.get $v.14
                        br $inlined1
                      end
                      local.get $t.3
                      local.set $q
                      local.get $q
                      ref.cast (ref $tuple)
                      struct.get $tuple $slots
                      i32.const 0
                      array.get $slots
                      call $unboxInt
                      local.set $v.15
                      local.get $q
                      ref.cast (ref $tuple)
                      struct.get $tuple $slots
                      i32.const 0
                      array.get $slots
                      call $unboxInt
                      local.set $v.16
                      local.get $v.15
                      local.get $v.16
                      i64.mul
                      local.set $v.17
                      local.get $v.17
                      br $inlined1
                    end
                    local.get $t.3
                    local.set $p
                    local.get $p
                    ref.cast (ref $tuple)
                    struct.get $tuple $slots
                    i32.const 0
                    array.get $slots
                    call $unboxInt
                    local.set $v.18
                    local.get $p
                    ref.cast (ref $tuple)
                    struct.get $tuple $slots
                    i32.const 1
                    array.get $slots
                    call $unboxInt
                    local.set $v.19
                    local.get $v.18
                    local.get $v.19
                    i64.add
                    local.set $v.20
                    local.get $v.20
                    br $inlined1
                  end
                  i64.const 0
                  br $inlined1
                end
                i32.const 0
                i32.const 19
                i32.const 178
                i32.const 19
                array.new_data $bytes $strings
                struct.new $string
                i32.const 0
                i32.const 0
                i32.const 197
                i32.const 0
                array.new_data $bytes $strings
                struct.new $string
                call $fail
                unreachable
              end
              br $inlined1.after
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
            i32.const 197
            i32.const 1
            array.new_data $bytes $strings
            struct.new $string
            call $concat
            local.set $v.24
            local.get $v.23
            local.get $v.24
            call $putString
            local.set $v.25
            local.get $i
            local.get $v.8
            i64.eq
            local.set $v.26
            local.get $v.26
            if
              br $L1.exit
            else
            end
            local.get $i
            i64.const 1
            i64.add
            local.set $v.27
            local.get $v.27
            local.set $i
          end
          br $L1
        end
      end
    else
    end
    i64.const 3
    local.get $shapes
    ref.cast (ref $array)
    struct.get $array $elems
    array.len
    i64.extend_i32_u
    i64.lt_u
    i32.eqz
    if
      i32.const 0
      i32.const 13
      i32.const 198
      i32.const 13
      array.new_data $bytes $strings
      struct.new $string
      i32.const 0
      i32.const 114
      i32.const 211
      i32.const 114
      array.new_data $bytes $strings
      struct.new $string
      call $fail
      unreachable
    end
    local.get $shapes
    ref.cast (ref $array)
    struct.get $array $elems
    i64.const 3
    i32.wrap_i64
    array.get $slots
    local.set $v.28
    local.get $v.28
    block (type 32)
      br_on_cast 0 eqref (ref $option)
      drop
      i32.const 0
      i32.const 51
      i32.const 325
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
      i32.const 0
      i32.const 19
      i32.const 376
      i32.const 19
      array.new_data $bytes $strings
      struct.new $string
      i32.const 0
      i32.const 114
      i32.const 395
      i32.const 114
      array.new_data $bytes $strings
      struct.new $string
      call $fail
      unreachable
    end
    i32.const 0
    i32.const 3
    array.new_default $slots
    local.set $t.4
    local.get $t.4
    i32.const 0
    i32.const 3
    ref.i31
    array.set $slots
    local.get $t.4
    i32.const 1
    local.get $v.28
    block (type 32)
      br_on_cast 0 eqref (ref $option)
      drop
      i32.const 0
      i32.const 51
      i32.const 509
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
    local.get $t.4
    ref.as_non_null
    struct.new $tuple
    local.set $pt
    local.get $pt
    ref.cast (ref $tuple)
    struct.get $tuple $slots
    i32.const 1
    array.get $slots
    call $unboxInt
    local.set $v.29
    local.get $v.29
    call $convInt
    local.set $v.30
    local.get $pt
    ref.cast (ref $tuple)
    struct.get $tuple $slots
    i32.const 2
    array.get $slots
    call $unboxInt
    local.set $v.31
    local.get $v.31
    call $convInt
    local.set $v.32
    i32.const 0
    i32.const 1
    i32.const 560
    i32.const 1
    array.new_data $bytes $strings
    struct.new $string
    local.get $v.32
    call $concat
    local.set $v.33
    local.get $v.30
    local.get $v.33
    call $concat
    local.set $v.34
    i32.const 1
    ref.i31
    local.set $v.35
    local.get $v.34
    i32.const 0
    i32.const 1
    i32.const 561
    i32.const 1
    array.new_data $bytes $strings
    struct.new $string
    call $concat
    local.set $v.36
    local.get $v.35
    local.get $v.36
    call $putString
    local.set $v.37
    i64.const 2
    local.get $shapes
    ref.cast (ref $array)
    struct.get $array $elems
    array.len
    i64.extend_i32_u
    i64.lt_u
    i32.eqz
    if
      i32.const 0
      i32.const 13
      i32.const 562
      i32.const 13
      array.new_data $bytes $strings
      struct.new $string
      i32.const 0
      i32.const 114
      i32.const 575
      i32.const 114
      array.new_data $bytes $strings
      struct.new $string
      call $fail
      unreachable
    end
    local.get $shapes
    ref.cast (ref $array)
    struct.get $array $elems
    i64.const 2
    i32.wrap_i64
    array.get $slots
    local.set $v.38
    i32.const 0
    array.new_fixed $slots 0
    i32.const 1
    struct.new $option
    local.set $v.39
    local.get $v.38
    local.set $t.5
    local.get $v.39
    local.set $t.6
    local.get $t.5
    local.get $t.6
    ref.eq
    if (result i32)
      i32.const 1
    else
      local.get $t.5
      ref.cast (ref $option)
      struct.get $option $tag
      local.tee $t.7
      local.get $t.6
      ref.cast (ref $option)
      struct.get $option $tag
      i32.eq
      if (result i32)
        local.get $t.7
        local.set $t.8
        block (result i32)
          block
            block
              block
                block
                  local.get $t.8
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
    local.set $v.40
    local.get $v.40
    call $convBool
    local.set $v.41
    i64.const 0
    local.get $shapes
    ref.cast (ref $array)
    struct.get $array $elems
    array.len
    i64.extend_i32_u
    i64.lt_u
    i32.eqz
    if
      i32.const 0
      i32.const 13
      i32.const 689
      i32.const 13
      array.new_data $bytes $strings
      struct.new $string
      i32.const 0
      i32.const 114
      i32.const 702
      i32.const 114
      array.new_data $bytes $strings
      struct.new $string
      call $fail
      unreachable
    end
    local.get $shapes
    ref.cast (ref $array)
    struct.get $array $elems
    i64.const 0
    i32.wrap_i64
    array.get $slots
    local.set $v.42
    local.get $v.42
    block (type 32)
      br_on_cast 0 eqref (ref $option)
      drop
      i32.const 0
      i32.const 51
      i32.const 816
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
    local.set $v.43
    local.get $v.43
    call $convBool
    local.set $v.44
    i64.const 1
    local.get $shapes
    ref.cast (ref $array)
    struct.get $array $elems
    array.len
    i64.extend_i32_u
    i64.lt_u
    i32.eqz
    if
      i32.const 0
      i32.const 13
      i32.const 867
      i32.const 13
      array.new_data $bytes $strings
      struct.new $string
      i32.const 0
      i32.const 114
      i32.const 880
      i32.const 114
      array.new_data $bytes $strings
      struct.new $string
      call $fail
      unreachable
    end
    local.get $shapes
    ref.cast (ref $array)
    struct.get $array $elems
    i64.const 1
    i32.wrap_i64
    array.get $slots
    local.set $v.45
    local.get $v.45
    block (type 32)
      br_on_cast 0 eqref (ref $option)
      drop
      i32.const 0
      i32.const 51
      i32.const 994
      i32.const 51
      array.new_data $bytes $strings
      struct.new $string
      i32.const 1
      call $fatal
      unreachable
    end
    struct.get $option $tag
    local.set $t.9
    block (result i32)
      block
        block
          block
            block
              local.get $t.9
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
    local.set $v.46
    local.get $v.46
    call $convInt
    local.set $v.47
    i64.const 0
    local.get $shapes
    ref.cast (ref $array)
    struct.get $array $elems
    array.len
    i64.extend_i32_u
    i64.lt_u
    i32.eqz
    if
      i32.const 0
      i32.const 13
      i32.const 1045
      i32.const 13
      array.new_data $bytes $strings
      struct.new $string
      i32.const 0
      i32.const 114
      i32.const 1058
      i32.const 114
      array.new_data $bytes $strings
      struct.new $string
      call $fail
      unreachable
    end
    local.get $shapes
    ref.cast (ref $array)
    struct.get $array $elems
    i64.const 0
    i32.wrap_i64
    array.get $slots
    local.set $v.48
    i64.const 1
    local.get $shapes
    ref.cast (ref $array)
    struct.get $array $elems
    array.len
    i64.extend_i32_u
    i64.lt_u
    i32.eqz
    if
      i32.const 0
      i32.const 13
      i32.const 1172
      i32.const 13
      array.new_data $bytes $strings
      struct.new $string
      i32.const 0
      i32.const 114
      i32.const 1185
      i32.const 114
      array.new_data $bytes $strings
      struct.new $string
      call $fail
      unreachable
    end
    local.get $shapes
    ref.cast (ref $array)
    struct.get $array $elems
    i64.const 1
    i32.wrap_i64
    array.get $slots
    local.set $v.49
    local.get $v.48
    local.set $t.10
    local.get $v.49
    local.set $t.11
    local.get $t.10
    local.get $t.11
    ref.eq
    if (result i32)
      i32.const 1
    else
      local.get $t.10
      ref.cast (ref $option)
      struct.get $option $tag
      local.tee $t.12
      local.get $t.11
      ref.cast (ref $option)
      struct.get $option $tag
      i32.eq
      if (result i32)
        local.get $t.12
        local.set $t.13
        block (result i32)
          block
            block
              block
                block
                  local.get $t.13
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
    local.set $v.50
    local.get $v.50
    call $convBool
    local.set $v.51
    i32.const 0
    i32.const 1
    i32.const 1299
    i32.const 1
    array.new_data $bytes $strings
    struct.new $string
    local.get $v.51
    call $concat
    local.set $v.52
    local.get $v.47
    local.get $v.52
    call $concat
    local.set $v.53
    i32.const 0
    i32.const 1
    i32.const 1300
    i32.const 1
    array.new_data $bytes $strings
    struct.new $string
    local.get $v.53
    call $concat
    local.set $v.54
    local.get $v.44
    local.get $v.54
    call $concat
    local.set $v.55
    i32.const 0
    i32.const 1
    i32.const 1301
    i32.const 1
    array.new_data $bytes $strings
    struct.new $string
    local.get $v.55
    call $concat
    local.set $v.56
    local.get $v.41
    local.get $v.56
    call $concat
    local.set $v.57
    i32.const 1
    ref.i31
    local.set $v.58
    local.get $v.57
    i32.const 0
    i32.const 1
    i32.const 1302
    i32.const 1
    array.new_data $bytes $strings
    struct.new $string
    call $concat
    local.set $v.59
    local.get $v.58
    local.get $v.59
    call $putString
    local.set $v.60
    i32.const 0
    i64.const 2
    i64.const 3
    i64.lt_u
    i32.eqz
    if
      i32.const 0
      i32.const 15
      i32.const 1303
      i32.const 15
      array.new_data $bytes $strings
      struct.new $string
      i64.const 2
      call $decimal
      call $concat
      i32.const 0
      i32.const 154
      i32.const 1318
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
    local.set $t.14
    block (result i32)
      block
        block
          block
            local.get $t.14
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
    local.set $light
    local.get $light
    block (type 32)
      br_on_cast 0 eqref (ref $option)
      drop
      i32.const 0
      i32.const 51
      i32.const 1472
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
    local.set $v.61
    local.get $v.61
    call $convBool
    local.set $v.62
    local.get $light
    block (type 32)
      br_on_cast 0 eqref (ref $option)
      drop
      i32.const 0
      i32.const 51
      i32.const 1523
      i32.const 51
      array.new_data $bytes $strings
      struct.new $string
      i32.const 1
      call $fatal
      unreachable
    end
    struct.get $option $tag
    local.set $t.15
    block (result i32)
      block
        block
          block
            local.get $t.15
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
    local.set $v.63
    local.get $v.63
    call $convInt
    local.set $v.64
    i32.const 0
    i32.const 1
    i32.const 1574
    i32.const 1
    array.new_data $bytes $strings
    struct.new $string
    local.get $v.64
    call $concat
    local.set $v.65
    local.get $v.62
    local.get $v.65
    call $concat
    local.set $v.66
    i32.const 1
    ref.i31
    local.set $v.67
    local.get $v.66
    i32.const 0
    i32.const 1
    i32.const 1575
    i32.const 1
    array.new_data $bytes $strings
    struct.new $string
    call $concat
    local.set $v.68
    local.get $v.67
    local.get $v.68
    call $putString
    local.set $v.69
    i32.const 0
    i64.const 4
    call $boxInt
    array.new_fixed $slots 1
    struct.new $tuple
    local.set $v.70
    i32.const 0
    i32.const 1
    array.new_default $slots
    local.tee $t.16
    i32.const 0
    local.get $v.70
    ref.cast (ref $tuple)
    struct.get $tuple $slots
    i32.const 0
    i32.const 1
    array.copy $slots $slots
    local.get $t.16
    ref.as_non_null
    i32.const 1
    struct.new $option
    local.set $m
    i32.const 0
    i64.const 4
    call $boxInt
    array.new_fixed $slots 1
    struct.new $tuple
    local.set $v.71
    i32.const 0
    i32.const 1
    array.new_default $slots
    local.tee $t.17
    i32.const 0
    local.get $v.71
    ref.cast (ref $tuple)
    struct.get $tuple $slots
    i32.const 0
    i32.const 1
    array.copy $slots $slots
    local.get $t.17
    ref.as_non_null
    i32.const 1
    struct.new $option
    local.set $n
    i32.const 0
    i64.const 5
    call $boxInt
    array.new_fixed $slots 1
    struct.new $tuple
    local.set $v.72
    i32.const 0
    i32.const 1
    array.new_default $slots
    local.tee $t.18
    i32.const 0
    local.get $v.72
    ref.cast (ref $tuple)
    struct.get $tuple $slots
    i32.const 0
    i32.const 1
    array.copy $slots $slots
    local.get $t.18
    ref.as_non_null
    i32.const 1
    struct.new $option
    local.set $o
    local.get $m
    local.set $t.19
    local.get $n
    local.set $t.20
    local.get $t.19
    local.get $t.20
    ref.eq
    if (result i32)
      i32.const 1
    else
      local.get $t.19
      ref.cast (ref $option)
      struct.get $option $tag
      local.tee $t.21
      local.get $t.20
      ref.cast (ref $option)
      struct.get $option $tag
      i32.eq
      if (result i32)
        local.get $t.21
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
        local.get $t.21
        i32.const 1
        i32.eq
        if (result i32)
          local.get $t.19
          ref.cast (ref $option)
          struct.get $option $slots
          i32.const 0
          array.get $slots
          local.get $t.20
          ref.cast (ref $option)
          struct.get $option $slots
          i32.const 0
          array.get $slots
          local.set $t.24
          local.set $t.23
          local.get $t.23
          call $unboxInt
          local.get $t.24
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
    local.set $v.73
    local.get $v.73
    call $convBool
    local.set $v.74
    local.get $m
    local.set $t.25
    local.get $o
    local.set $t.26
    local.get $t.25
    local.get $t.26
    ref.eq
    if (result i32)
      i32.const 1
    else
      local.get $t.25
      ref.cast (ref $option)
      struct.get $option $tag
      local.tee $t.27
      local.get $t.26
      ref.cast (ref $option)
      struct.get $option $tag
      i32.eq
      if (result i32)
        local.get $t.27
        local.set $t.28
        block (result i32)
          block
            block
              local.get $t.28
              br_table 0 1 1
            end
            i32.const 1
            br 1
          end
          i32.const 0
          br 0
        end
        local.get $t.27
        i32.const 1
        i32.eq
        if (result i32)
          local.get $t.25
          ref.cast (ref $option)
          struct.get $option $slots
          i32.const 0
          array.get $slots
          local.get $t.26
          ref.cast (ref $option)
          struct.get $option $slots
          i32.const 0
          array.get $slots
          local.set $t.30
          local.set $t.29
          local.get $t.29
          call $unboxInt
          local.get $t.30
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
    local.set $v.75
    local.get $v.75
    call $convBool
    local.set $v.76
    i32.const 0
    i32.const 1
    i32.const 1576
    i32.const 1
    array.new_data $bytes $strings
    struct.new $string
    local.get $v.76
    call $concat
    local.set $v.77
    local.get $v.74
    local.get $v.77
    call $concat
    local.set $v.78
    i32.const 1
    ref.i31
    local.set $v.79
    local.get $v.78
    i32.const 0
    i32.const 1
    i32.const 1577
    i32.const 1
    array.new_data $bytes $strings
    struct.new $string
    call $concat
    local.set $v.80
    local.get $v.79
    local.get $v.80
    call $putString
    local.set $v.81
    i32.const 0
    i32.const 3
    i32.const 1578
    i32.const 3
    array.new_data $bytes $strings
    struct.new $string
    local.set $b
    i32.const 0
    i64.const 1
    call $boxInt
    local.get $b
    i32.const 99
    ref.i31
    array.new_fixed $slots 3
    struct.new $tuple
    local.set $t.31
    local.get $t.31
    ref.cast (ref $tuple)
    struct.get $tuple $slots
    i32.const 1
    array.get $slots
    local.set $v.82
    local.get $v.82
    i32.const 0
    i32.const 1
    i32.const 1581
    i32.const 1
    array.new_data $bytes $strings
    struct.new $string
    call $concat
    local.set $v.83
    local.get $t.31
    ref.cast (ref $tuple)
    struct.get $tuple $slots
    i32.const 1
    local.get $v.83
    array.set $slots
    i64.const 1
    call $convInt
    local.set $v.84
    local.get $t.31
    ref.cast (ref $tuple)
    struct.get $tuple $slots
    i32.const 1
    array.get $slots
    local.set $v.85
    i32.const 0
    i32.const 1
    i32.const 1582
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
    i32.const 1583
    i32.const 1
    array.new_data $bytes $strings
    struct.new $string
    call $concat
    local.set $v.86
    local.get $v.85
    local.get $v.86
    call $concat
    local.set $v.87
    local.get $v.84
    local.get $v.87
    call $concat
    local.set $v.88
    i32.const 1
    ref.i31
    local.set $v.89
    local.get $v.88
    i32.const 0
    i32.const 1
    i32.const 1584
    i32.const 1
    array.new_data $bytes $strings
    struct.new $string
    call $concat
    local.set $v.90
    local.get $v.89
    local.get $v.90
    call $putString
    local.set $v.91
    i32.const 0
    struct.new $clos
    global.set $divide.1
    i64.const 47
    i64.const 5
    call $divide
    local.set $qr.1
    local.set $qr
    i64.const 100
    i64.const 7
    call $divide
    local.set $qr2.1
    local.set $qr2
    local.get $qr
    local.set $v.92
    local.get $v.92
    call $convInt
    local.set $v.93
    local.get $qr.1
    local.set $v.94
    local.get $v.94
    call $convInt
    local.set $v.95
    local.get $qr2
    local.set $v.96
    local.get $v.96
    call $convInt
    local.set $v.97
    local.get $qr2.1
    local.set $v.98
    local.get $v.98
    call $convInt
    local.set $v.99
    i32.const 0
    i32.const 1
    i32.const 1585
    i32.const 1
    array.new_data $bytes $strings
    struct.new $string
    local.get $v.99
    call $concat
    local.set $v.100
    local.get $v.97
    local.get $v.100
    call $concat
    local.set $v.101
    i32.const 0
    i32.const 1
    i32.const 1586
    i32.const 1
    array.new_data $bytes $strings
    struct.new $string
    local.get $v.101
    call $concat
    local.set $v.102
    local.get $v.95
    local.get $v.102
    call $concat
    local.set $v.103
    i32.const 0
    i32.const 1
    i32.const 1587
    i32.const 1
    array.new_data $bytes $strings
    struct.new $string
    local.get $v.103
    call $concat
    local.set $v.104
    local.get $v.93
    local.get $v.104
    call $concat
    local.set $v.105
    i32.const 1
    ref.i31
    local.set $v.106
    local.get $v.105
    i32.const 0
    i32.const 1
    i32.const 1588
    i32.const 1
    array.new_data $bytes $strings
    struct.new $string
    call $concat
    local.set $v.107
    local.get $v.106
    local.get $v.107
    call $putString
    local.set $v.108
    i64.const 5
    i64.const 0
    i64.lt_s
    if
      i32.const 0
      i32.const 13
      i32.const 1589
      i32.const 13
      array.new_data $bytes $strings
      struct.new $string
      i32.const 0
      i32.const 113
      i32.const 1602
      i32.const 113
      array.new_data $bytes $strings
      struct.new $string
      call $fail
      unreachable
    end
    i64.const 5
    i64.const 134217720
    i64.gt_s
    if
      i32.const 0
      i32.const 63
      i32.const 1715
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
    local.set $a
    i64.const 0
    local.set $i.2
    local.get $i.2
    i64.const 4
    i64.le_s
    local.set $v.109
    local.get $v.109
    if
      block $L2.exit
        loop $L2
          local.get $i.2
          local.set $i.3
          local.get $i.3
          local.get $i.3
          i64.mul
          local.set $v.110
          local.get $i.3
          local.get $a
          ref.cast (ref $array)
          struct.get $array $elems
          array.len
          i64.extend_i32_u
          i64.lt_u
          i32.eqz
          if
            i32.const 0
            i32.const 13
            i32.const 1778
            i32.const 13
            array.new_data $bytes $strings
            struct.new $string
            i32.const 0
            i32.const 114
            i32.const 1791
            i32.const 114
            array.new_data $bytes $strings
            struct.new $string
            call $fail
            unreachable
          end
          local.get $a
          ref.cast (ref $array)
          struct.get $array $elems
          local.get $i.3
          i32.wrap_i64
          local.get $v.110
          call $boxInt
          array.set $slots
          local.get $i.2
          i64.const 4
          i64.eq
          local.set $v.111
          local.get $v.111
          if
            br $L2.exit
          else
          end
          local.get $i.2
          i64.const 1
          i64.add
          local.set $v.112
          local.get $v.112
          local.set $i.2
          br $L2
        end
      end
    else
    end
    i64.const 4
    local.get $a
    ref.cast (ref $array)
    struct.get $array $elems
    array.len
    i64.extend_i32_u
    i64.lt_u
    i32.eqz
    if
      i32.const 0
      i32.const 13
      i32.const 1905
      i32.const 13
      array.new_data $bytes $strings
      struct.new $string
      i32.const 0
      i32.const 114
      i32.const 1918
      i32.const 114
      array.new_data $bytes $strings
      struct.new $string
      call $fail
      unreachable
    end
    local.get $a
    ref.cast (ref $array)
    struct.get $array $elems
    i64.const 4
    i32.wrap_i64
    array.get $slots
    call $unboxInt
    local.set $v.113
    local.get $v.113
    call $convInt
    local.set $v.114
    local.get $a
    ref.cast (ref $array)
    struct.get $array $elems
    array.len
    i64.extend_i32_u
    local.set $v.115
    local.get $v.115
    call $convInt
    local.set $v.116
    i32.const 0
    i32.const 1
    i32.const 2032
    i32.const 1
    array.new_data $bytes $strings
    struct.new $string
    local.get $v.116
    call $concat
    local.set $v.117
    local.get $v.114
    local.get $v.117
    call $concat
    local.set $v.118
    i32.const 1
    ref.i31
    local.set $v.119
    local.get $v.118
    i32.const 0
    i32.const 1
    i32.const 2033
    i32.const 1
    array.new_data $bytes $strings
    struct.new $string
    call $concat
    local.set $v.120
    local.get $v.119
    local.get $v.120
    call $putString
    local.set $v.121
    i64.const 3
    i32.const 120
    call $stringNew
    local.set $str
    local.get $str
    i64.const 1
    i32.const 121
    call $stringSetChar
    drop
    i32.const 0
    i32.const 6
    i32.const 2034
    i32.const 6
    array.new_data $bytes $strings
    struct.new $string
    i64.const 2
    i64.const 3
    call $stringGetSub
    local.set $v.122
    i32.const 0
    i32.const 2
    i32.const 2040
    i32.const 2
    array.new_data $bytes $strings
    struct.new $string
    i32.const 0
    i32.const 2
    i32.const 2042
    i32.const 2
    array.new_data $bytes $strings
    struct.new $string
    call $stringEqual
    local.set $v.123
    local.get $v.123
    call $convBool
    local.set $v.124
    i32.const 0
    i32.const 3
    i32.const 2044
    i32.const 3
    array.new_data $bytes $strings
    struct.new $string
    i64.const 2
    call $stringGetChar
    local.set $v.125
    i32.const 0
    i32.const 1
    i32.const 2047
    i32.const 1
    array.new_data $bytes $strings
    struct.new $string
    local.get $v.125
    call $convChar
    i32.const 39
    call $escaped
    call $concat
    i32.const 0
    i32.const 1
    i32.const 2048
    i32.const 1
    array.new_data $bytes $strings
    struct.new $string
    call $concat
    local.set $v.126
    i32.const 0
    i32.const 1
    i32.const 2049
    i32.const 1
    array.new_data $bytes $strings
    struct.new $string
    local.get $v.126
    call $concat
    local.set $v.127
    local.get $v.124
    local.get $v.127
    call $concat
    local.set $v.128
    i32.const 0
    i32.const 1
    i32.const 2050
    i32.const 1
    array.new_data $bytes $strings
    struct.new $string
    local.get $v.128
    call $concat
    local.set $v.129
    local.get $v.122
    local.get $v.129
    call $concat
    local.set $v.130
    i32.const 0
    i32.const 1
    i32.const 2051
    i32.const 1
    array.new_data $bytes $strings
    struct.new $string
    local.get $v.130
    call $concat
    local.set $v.131
    local.get $str
    local.get $v.131
    call $concat
    local.set $v.132
    i32.const 1
    ref.i31
    local.set $v.133
    local.get $v.132
    i32.const 0
    i32.const 1
    i32.const 2052
    i32.const 1
    array.new_data $bytes $strings
    struct.new $string
    call $concat
    local.set $v.134
    local.get $v.133
    local.get $v.134
    call $putString
    local.set $v.135
    i32.const 0
    ref.null none
    i32.const 0
    i32.const 1
    i32.const 2053
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
    local.set $t.32
    ref.cast (ref $record)
    local.get $t.32
    ref.cast (ref $dict)
    struct.new $recBox
    local.set $p_box
    local.get $p_box
    ref.cast (ref $recBox)
    local.tee $t.33
    struct.get $recBox $payload
    local.get $t.33
    struct.get $recBox $dict
    local.set $p.2
    local.set $p.1
    local.get $p.1
    local.get $p.2
    local.set $t.34
    ref.cast (ref $record)
    struct.get $record $slots
    local.get $t.34
    ref.cast (ref $dict)
    struct.get $dict $indices
    i32.const 2
    array.get $i32s
    array.get $slots
    call $unboxInt
    local.set $v.136
    local.get $v.136
    i64.const 10
    i64.add
    local.set $v.137
    local.get $p.1
    local.get $p.2
    local.set $t.35
    ref.cast (ref $record)
    struct.get $record $slots
    local.get $t.35
    ref.cast (ref $dict)
    struct.get $dict $indices
    i32.const 2
    array.get $i32s
    local.get $v.137
    call $boxInt
    array.set $slots
    local.get $p.1
    local.get $p.2
    local.set $t.36
    ref.cast (ref $record)
    struct.get $record $slots
    local.get $t.36
    ref.cast (ref $dict)
    struct.get $dict $indices
    i32.const 0
    array.get $i32s
    array.get $slots
    local.set $v.138
    local.get $p.1
    local.get $p.2
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
    local.set $v.139
    local.get $v.139
    call $convInt
    local.set $v.140
    local.get $p.1
    local.get $p.2
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
    local.set $v.141
    local.get $v.141
    call $convInt
    local.set $v.142
    i32.const 0
    i32.const 1
    i32.const 2054
    i32.const 1
    array.new_data $bytes $strings
    struct.new $string
    local.get $v.142
    call $concat
    local.set $v.143
    local.get $v.140
    local.get $v.143
    call $concat
    local.set $v.144
    i32.const 0
    i32.const 1
    i32.const 2055
    i32.const 1
    array.new_data $bytes $strings
    struct.new $string
    local.get $v.144
    call $concat
    local.set $v.145
    local.get $v.138
    local.get $v.145
    call $concat
    local.set $v.146
    i32.const 1
    ref.i31
    local.set $v.147
    local.get $v.146
    i32.const 0
    i32.const 1
    i32.const 2056
    i32.const 1
    array.new_data $bytes $strings
    struct.new $string
    call $concat
    local.set $v.148
    local.get $v.147
    local.get $v.148
    call $putString
    local.set $v.149
    i32.const 0
    ref.null none
    i32.const 0
    i32.const 1
    i32.const 2057
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
    local.set $t.39
    ref.cast (ref $record)
    local.get $t.39
    ref.cast (ref $dict)
    struct.new $recBox
    local.set $box
    local.get $box
    ref.cast (ref $recBox)
    local.tee $t.40
    struct.get $recBox $payload
    local.get $t.40
    struct.get $recBox $dict
    local.set $v.151
    local.set $v.150
    i32.const 0
    local.get $p_box
    local.get $box
    array.new_fixed $slots 2
    struct.new $array
    local.set $ps
    i64.const 1
    local.get $ps
    ref.cast (ref $array)
    struct.get $array $elems
    array.len
    i64.extend_i32_u
    i64.lt_u
    i32.eqz
    if
      i32.const 0
      i32.const 13
      i32.const 2058
      i32.const 13
      array.new_data $bytes $strings
      struct.new $string
      i32.const 0
      i32.const 113
      i32.const 2071
      i32.const 113
      array.new_data $bytes $strings
      struct.new $string
      call $fail
      unreachable
    end
    local.get $ps
    ref.cast (ref $array)
    struct.get $array $elems
    i64.const 1
    i32.wrap_i64
    array.get $slots
    local.set $box.1
    local.get $box.1
    ref.cast (ref $recBox)
    local.tee $t.41
    struct.get $recBox $payload
    local.get $t.41
    struct.get $recBox $dict
    local.set $v.153
    local.set $v.152
    local.get $v.152
    local.get $v.153
    local.set $t.42
    ref.cast (ref $record)
    struct.get $record $slots
    local.get $t.42
    ref.cast (ref $dict)
    struct.get $dict $indices
    i32.const 0
    array.get $i32s
    array.get $slots
    local.set $v.154
    i64.const 1
    local.get $ps
    ref.cast (ref $array)
    struct.get $array $elems
    array.len
    i64.extend_i32_u
    i64.lt_u
    i32.eqz
    if
      i32.const 0
      i32.const 13
      i32.const 2184
      i32.const 13
      array.new_data $bytes $strings
      struct.new $string
      i32.const 0
      i32.const 114
      i32.const 2197
      i32.const 114
      array.new_data $bytes $strings
      struct.new $string
      call $fail
      unreachable
    end
    local.get $ps
    ref.cast (ref $array)
    struct.get $array $elems
    i64.const 1
    i32.wrap_i64
    array.get $slots
    local.set $box.2
    local.get $box.2
    ref.cast (ref $recBox)
    local.tee $t.43
    struct.get $recBox $payload
    local.get $t.43
    struct.get $recBox $dict
    local.set $v.156
    local.set $v.155
    local.get $v.155
    local.get $v.156
    local.set $q.2
    local.set $q.1
    local.get $q.1
    local.get $q.2
    local.set $t.44
    ref.cast (ref $record)
    struct.get $record $slots
    local.get $t.44
    ref.cast (ref $dict)
    struct.get $dict $indices
    i32.const 1
    array.get $i32s
    array.get $slots
    call $unboxInt
    local.set $v.157
    local.get $q.1
    local.get $q.2
    local.set $t.45
    ref.cast (ref $record)
    struct.get $record $slots
    local.get $t.45
    ref.cast (ref $dict)
    struct.get $dict $indices
    i32.const 1
    array.get $i32s
    array.get $slots
    call $unboxInt
    local.set $v.158
    local.get $q.1
    local.get $q.2
    local.set $t.46
    ref.cast (ref $record)
    struct.get $record $slots
    local.get $t.46
    ref.cast (ref $dict)
    struct.get $dict $indices
    i32.const 2
    array.get $i32s
    array.get $slots
    call $unboxInt
    local.set $v.159
    local.get $q.1
    local.get $q.2
    local.set $t.47
    ref.cast (ref $record)
    struct.get $record $slots
    local.get $t.47
    ref.cast (ref $dict)
    struct.get $dict $indices
    i32.const 2
    array.get $i32s
    array.get $slots
    call $unboxInt
    local.set $v.160
    local.get $v.159
    local.get $v.160
    i64.mul
    local.set $v.161
    local.get $v.158
    local.get $v.161
    i64.add
    local.set $v.162
    local.get $v.157
    local.get $v.162
    i64.mul
    local.set $v.163
    local.get $v.163
    call $convInt
    local.set $v.164
    local.get $p.1
    local.get $p.2
    local.set $t.48
    ref.cast (ref $record)
    struct.get $record $slots
    local.get $t.48
    ref.cast (ref $dict)
    struct.get $dict $indices
    i32.const 1
    array.get $i32s
    array.get $slots
    call $unboxInt
    local.set $v.165
    local.get $p.1
    local.get $p.2
    local.set $t.49
    ref.cast (ref $record)
    struct.get $record $slots
    local.get $t.49
    ref.cast (ref $dict)
    struct.get $dict $indices
    i32.const 1
    array.get $i32s
    array.get $slots
    call $unboxInt
    local.set $v.166
    local.get $p.1
    local.get $p.2
    local.set $t.50
    ref.cast (ref $record)
    struct.get $record $slots
    local.get $t.50
    ref.cast (ref $dict)
    struct.get $dict $indices
    i32.const 2
    array.get $i32s
    array.get $slots
    call $unboxInt
    local.set $v.167
    local.get $p.1
    local.get $p.2
    local.set $t.51
    ref.cast (ref $record)
    struct.get $record $slots
    local.get $t.51
    ref.cast (ref $dict)
    struct.get $dict $indices
    i32.const 2
    array.get $i32s
    array.get $slots
    call $unboxInt
    local.set $v.168
    local.get $v.167
    local.get $v.168
    i64.mul
    local.set $v.169
    local.get $v.166
    local.get $v.169
    i64.add
    local.set $v.170
    local.get $v.165
    local.get $v.170
    i64.mul
    local.set $v.171
    local.get $v.171
    call $convInt
    local.set $v.172
    i32.const 0
    i32.const 1
    i32.const 2311
    i32.const 1
    array.new_data $bytes $strings
    struct.new $string
    local.get $v.172
    call $concat
    local.set $v.173
    local.get $v.164
    local.get $v.173
    call $concat
    local.set $v.174
    local.get $v.154
    local.get $v.174
    call $concat
    local.set $v.175
    i32.const 1
    ref.i31
    local.set $v.176
    local.get $v.175
    i32.const 0
    i32.const 1
    i32.const 2312
    i32.const 1
    array.new_data $bytes $strings
    struct.new $string
    call $concat
    local.set $v.177
    local.get $v.176
    local.get $v.177
    call $putString
    local.set $v.178
    local.get $p.1
    local.get $p.2
    local.set $t.52
    ref.cast (ref $record)
    struct.get $record $slots
    local.get $t.52
    ref.cast (ref $dict)
    struct.get $dict $indices
    i32.const 0
    array.get $i32s
    array.get $slots
    local.set $v.179
    i64.const 9
    call $convInt
    local.set $v.180
    local.get $v.179
    local.get $v.180
    call $concat
    local.set $v.181
    i32.const 1
    ref.i31
    local.set $v.182
    local.get $v.181
    i32.const 0
    i32.const 1
    i32.const 2313
    i32.const 1
    array.new_data $bytes $strings
    struct.new $string
    call $concat
    local.set $v.183
    local.get $v.182
    local.get $v.183
    call $putString
    local.set $v.184
    i64.const 5
    local.get $a
    ref.cast (ref $array)
    struct.get $array $elems
    array.len
    i64.extend_i32_u
    i64.lt_u
    i32.eqz
    if
      i32.const 0
      i32.const 13
      i32.const 2314
      i32.const 13
      array.new_data $bytes $strings
      struct.new $string
      i32.const 0
      i32.const 114
      i32.const 2327
      i32.const 114
      array.new_data $bytes $strings
      struct.new $string
      call $fail
      unreachable
    end
    local.get $a
    ref.cast (ref $array)
    struct.get $array $elems
    i64.const 5
    i32.wrap_i64
    array.get $slots
    call $unboxInt
    local.set $v.185
    local.get $v.185
    call $convInt
    local.set $v.186
    i32.const 1
    ref.i31
    local.set $v.187
    local.get $v.186
    i32.const 0
    i32.const 1
    i32.const 2441
    i32.const 1
    array.new_data $bytes $strings
    struct.new $string
    call $concat
    local.set $v.188
    local.get $v.187
    local.get $v.188
    call $putString
    local.set $v.189
  )
  (func $_start (type 30)
    block $uncaught (result eqref)
      try_table (catch $error $uncaught)
        call $main
      end
      return
    end
    call $uncaught
  )
  (data $strings "arrayOp.error/Users/haahr/Dropbox/Paul/src/quest/.claude/worktrees/wasm-plan-opus/tests/self-hosted/wasm/aggregates.quest:25:55wasm: a proxy, which this backend does not yet run\0avariant.tagMismatch\0aarrayOp.error/Users/haahr/Dropbox/Paul/src/quest/.claude/worktrees/wasm-plan-opus/tests/self-hosted/wasm/aggregates.quest:26:10wasm: a proxy, which this backend does not yet run\0avariant.tagMismatch/Users/haahr/Dropbox/Paul/src/quest/.claude/worktrees/wasm-plan-opus/tests/self-hosted/wasm/aggregates.quest:26:10wasm: a proxy, which this backend does not yet run\0a \0aarrayOp.error/Users/haahr/Dropbox/Paul/src/quest/.claude/worktrees/wasm-plan-opus/tests/self-hosted/wasm/aggregates.quest:28:15arrayOp.error/Users/haahr/Dropbox/Paul/src/quest/.claude/worktrees/wasm-plan-opus/tests/self-hosted/wasm/aggregates.quest:28:75wasm: a proxy, which this backend does not yet run\0aarrayOp.error/Users/haahr/Dropbox/Paul/src/quest/.claude/worktrees/wasm-plan-opus/tests/self-hosted/wasm/aggregates.quest:29:25wasm: a proxy, which this backend does not yet run\0aarrayOp.error/Users/haahr/Dropbox/Paul/src/quest/.claude/worktrees/wasm-plan-opus/tests/self-hosted/wasm/aggregates.quest:29:57arrayOp.error/Users/haahr/Dropbox/Paul/src/quest/.claude/worktrees/wasm-plan-opus/tests/self-hosted/wasm/aggregates.quest:29:70   \0aOption ordinal  out of bounds (0 <= ordinal < 3)\0a  at /Users/haahr/Dropbox/Paul/src/quest/.claude/worktrees/wasm-plan-opus/tests/self-hosted/wasm/aggregates.quest:31:13\0awasm: a proxy, which this backend does not yet run\0awasm: a proxy, which this backend does not yet run\0a \0a \0atwo!''\0a   \0aarrayOp.error/Users/haahr/Dropbox/Paul/src/quest/.claude/worktrees/wasm-plan-opus/tests/self-hosted/wasm/aggregates.quest:54:9quest: out of memory: an array of more than 134217720 elements\0aarrayOp.error/Users/haahr/Dropbox/Paul/src/quest/.claude/worktrees/wasm-plan-opus/tests/self-hosted/wasm/aggregates.quest:55:21arrayOp.error/Users/haahr/Dropbox/Paul/src/quest/.claude/worktrees/wasm-plan-opus/tests/self-hosted/wasm/aggregates.quest:56:14 \0aabcdefabababc''   \0ap  \0aqarrayOp.error/Users/haahr/Dropbox/Paul/src/quest/.claude/worktrees/wasm-plan-opus/tests/self-hosted/wasm/aggregates.quest:68:5arrayOp.error/Users/haahr/Dropbox/Paul/src/quest/.claude/worktrees/wasm-plan-opus/tests/self-hosted/wasm/aggregates.quest:68:33 \0a\0aarrayOp.error/Users/haahr/Dropbox/Paul/src/quest/.claude/worktrees/wasm-plan-opus/tests/self-hosted/wasm/aggregates.quest:71:14\0a")
)


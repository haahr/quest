#!/bin/sh
# Times the probes in wasmtime: wall-clock seconds for each process, compilation included (about 0.02 s).
cd "$(dirname "$0")" || exit 1
W="wasmtime run -W gc=y,function-references=y,tail-call=y -C collector=copying"
t() {
  label=$1; shift
  s=$( /usr/bin/time -p sh -c '"$@" >/dev/null 2>&1' sh "$@" 2>&1 | awk '/real/ {print $2}')
  printf '%-62s %s\n' "$label" "$s"
}
for big in 0 1; do
  for v in A B; do
    t "tuples $v big=$big: build 5 times" $W --invoke run$v tuples.wasm 20 $big 5 0
    t "tuples $v big=$big: build once, walk 10 times" $W --invoke run$v tuples.wasm 20 $big 1 10
  done
done
for big in 0 1; do
  for v in Eq I; do
    t "arrays $v big=$big: fill 20 times" $W --invoke run$v arrays.wasm 1000000 $big 20 0
    t "arrays $v big=$big: fill once, sum 100 times" $W --invoke run$v arrays.wasm 1000000 $big 1 100
  done
done
for big in 0 1; do
  for v in U T; do
    t "vector $v big=$big: set all 20 times" $W --preload vec=vec.wasm --invoke run$v user.wasm 1000000 $big 20 0
    t "vector $v big=$big: set once, get all 50 times" $W --preload vec=vec.wasm --invoke run$v user.wasm 1000000 $big 1 50
  done
done
t "casts: precise, 100M calls" $W --preload vec=vec.wasm --invoke callPrecise user.wasm 100000000
t "casts: eqref and cast, 100M calls" $W --preload vec=vec.wasm --invoke callCast user.wasm 100000000

#!/bin/sh
# The largest array of each element kind that wasmtime will make, by bisection (a process for each try).
cd "$(dirname "$0")" || exit 1
W="wasmtime run -W gc=y,function-references=y -C collector=copying"
for f in newEq newI64 newI8; do
  lo=0; hi=2147483647; why=
  while [ "$lo" -lt "$hi" ]; do
    mid=$(( (lo + hi + 1) / 2 ))
    if out=$($W --invoke $f limits.wasm $mid 2>&1 >/dev/null); then lo=$mid; else hi=$((mid - 1)); why=$(echo "$out" | grep -v warning | tail -1); fi
  done
  echo "$f $lo $why"
done

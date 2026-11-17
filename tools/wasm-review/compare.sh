#!/bin/sh
# compare.sh NAME...: for each NAME.quest in the current directory, runs it
# compiled by arm64, and by the wasm backend in wasmtime and in node, and
# reports whether the three outputs (with the exit status) are the same.
# The outputs are left in NAME.native, NAME.wt, and NAME.node, and the builds
# in b/, so run it in a scratch directory, never in the tree. NAME.in, if
# there, is each run's standard input. T is each run's limit in seconds (60),
# FLAGS more options for the driver (--echo).
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
Q=$ROOT/quest
TO="perl -e alarm(shift);exec(@ARGV) ${T:-60}"
status=0
for p in "$@"; do
  in=/dev/null; [ -f "$p.in" ] && in=$p.in
  $TO "$Q" $FLAGS --stop-after run_c_compiled --build-dir b/n "$p.quest" < "$in" > "$p.native" 2>&1
  echo "exit $?" >> "$p.native"
  $TO "$Q" --backend wasm $FLAGS --stop-after run_c_compiled --build-dir b/w "$p.quest" < "$in" > "$p.wt" 2>&1
  echo "exit $?" >> "$p.wt"
  $TO "$Q" --backend wasm --wasm-engine node $FLAGS --stop-after run_c_compiled --build-dir b/w "$p.quest" \
    < "$in" > "$p.node" 2>&1
  echo "exit $?" >> "$p.node"
  if cmp -s "$p.native" "$p.wt" && cmp -s "$p.native" "$p.node"; then
    echo "== $p: same ($(wc -l < "$p.native" | tr -d ' ') lines)"
  else
    status=1
    echo "== $p: DIFFER (native < > wasmtime)"
    diff "$p.native" "$p.wt" | cut -c1-400 | head -40
    cmp -s "$p.wt" "$p.node" || { echo "-- wasmtime < > node:"; diff "$p.wt" "$p.node" | cut -c1-400 | head -10; }
  fi
done
exit $status

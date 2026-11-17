#!/bin/sh
# run.sh OUT GENERATOR [FROM TO]: writes GENERATOR's documents (handwritten.py
# or mutations.py) into OUT/docs, and reads each with read.quest compiled by
# arm64, and by the wasm backend in wasmtime and in node. A document can end a
# run (a trap, a fatal error, or the limit of T seconds, 30), so each target
# is started again after such a one, which gets a line "N: <DIED ...>". The
# lines are left in OUT/all.native, all.wt, and all.node, and the differences
# in all.diff.wt (native against wasmtime) and all.diff.node (wasmtime
# against node).
HERE=$(cd "$(dirname "$0")" && pwd)
ROOT=$(cd "$HERE/../../.." && pwd)
. "$HERE/../../python.sh"
out=$1
mkdir -p "$out/u" && cp "$HERE"/u/*.quest "$out/u/" && cp "$HERE/read.quest" "$out/" && cd "$out" || exit 1
count=$("$PY" "$HERE/$2" docs) || exit 1
first=${3:-0}
last=${4:-$((count - 1))}
TO="perl -e alarm(shift);exec(@ARGV) ${T:-30}"
for target in native wt node; do
  case $target in
    native) flags=""; bd=b/n ;;
    wt) flags="--backend wasm"; bd=b/w ;;
    node) flags="--backend wasm --wasm-engine node"; bd=b/w ;;
  esac
  : > all.$target
  from=$first
  while [ "$from" -le "$last" ]; do
    echo "$from $last " > loop.in
    $TO "$ROOT/quest" $flags --stop-after run_c_compiled --build-dir $bd read.quest < loop.in > loop.out 2>&1
    code=$?
    grep -a '^[0-9][0-9]*: ' loop.out | cut -c1-600 > loop.lines
    if grep -aq '^done ' loop.out; then cat loop.lines >> all.$target; break; fi
    # The run ended early: the last numbered line is the document that ended it.
    died=$(tail -1 loop.lines | sed 's/:.*//')
    [ -z "$died" ] && died=$from
    sed '$d' loop.lines >> all.$target
    why=$(grep -a 'error\|trap\|RangeError\|RuntimeError' loop.out | head -2 | tr '\n' ' ' | cut -c1-200)
    echo "$died: <DIED exit $code> $why" >> all.$target
    from=$((died + 1))
  done
done
diff all.native all.wt > all.diff.wt
diff all.wt all.node > all.diff.node
echo "documents $first to $last: native $(wc -l < all.native | tr -d ' ') lines," \
  "wasmtime $(wc -l < all.wt | tr -d ' '), node $(wc -l < all.node | tr -d ' ')"
echo "differing lines: native/wasmtime $(grep -c '^<' all.diff.wt), wasmtime/node $(grep -c '^<' all.diff.node)"
grep -a DIED all.native all.wt all.node | cut -c1-200 | head -30

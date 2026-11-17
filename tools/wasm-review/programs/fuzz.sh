#!/bin/sh
# fuzz.sh OUT FIRST LAST [FUNCTIONS SIZE]: for each seed from FIRST to LAST,
# writes gen.py's random program as OUT/rSEED.quest and compares its three
# runs (../compare.sh). FUNCTIONS (6) and SIZE (60 statements a function) are
# gen.py's; 3 and 400 give functions with several hundred variables each.
HERE=$(cd "$(dirname "$0")" && pwd)
. "$HERE/../../python.sh"
out=$1
mkdir -p "$out/u" && cp "$HERE"/u/*.quest "$out/u/" && cd "$out" || exit 1
seed=$2
status=0
while [ "$seed" -le "$3" ]; do
  "$PY" "$HERE/gen.py" "$seed" "${4:-6}" "${5:-60}" > "r$seed.quest"
  sh "$HERE/../compare.sh" "r$seed" || status=1
  seed=$((seed + 1))
done
exit $status

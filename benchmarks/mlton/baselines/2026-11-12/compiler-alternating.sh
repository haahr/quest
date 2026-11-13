#!/bin/zsh
# How benchmarks.md §22 timed compilers against each other: each compiler named
# (a stage 2 binary, copied out of .build/quest-stages*/stage2 at its commit)
# compiles the driver through arm64 at -j 1 (or -j 8) from an empty build
# directory, the compilers alternating for three rounds, after the load has
# stayed under 5 for three minutes. Prints each compiler, real, and user time.
# Run from the root of the tree whose driver is compiled.
#   compiler-alternating.sh [-j N] QUEST...
J=1; if [ "$1" = -j ]; then J=$2; shift 2; fi
T=$(mktemp -d)
for r in 1 2 3; do for q in "$@"; do
  rm -rf $T/b
  QUEST_HOME=$PWD /usr/bin/time -p $q -j $J --backend arm64 --build-dir $T/b -o $T/q questlang/driver/main.quest \
    2> $T/t > /dev/null
  echo "$q $(awk '/^real/{r=$2}/^user/{u=$2}END{print r, u}' $T/t)"
done; done | sort
rm -rf "${T:?}"

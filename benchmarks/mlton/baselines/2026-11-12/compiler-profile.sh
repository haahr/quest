#!/bin/zsh
# Times and samples the C-built and arm64-built compilers compiling the driver
# through arm64 at -j 1 from an empty build directory (benchmarks.md §21.4 item 5).
S=/private/tmp/claude-501/-Users-haahr-Dropbox-Paul-src-quest--claude-worktrees-busy-lehmann-a8b5df/af2067a2-6a39-467d-85b2-fdc296114b49/scratchpad
P=$S/prof
cd /Users/haahr/Dropbox/Paul/src/quest/.claude/worktrees/busy-lehmann-a8b5df
export QUEST_HOME=$PWD
typeset -A Q; Q=(c $PWD/.build/quest-stages-c/stage2/quest arm64 $PWD/.build/quest-stages/stage2/quest)
cp $Q[c] $P/quest-c; cp $Q[arm64] $P/quest-arm64
$S/idle.sh 3 >> $P/log
for r in 1 2 3; do for b in c arm64; do
  rm -rf $P/b; echo "time $b round $r" >> $P/times.txt
  /usr/bin/time -l $P/quest-$b -j 1 --backend arm64 --build-dir $P/b -o $P/q questlang/driver/main.quest 2>> $P/times.txt >/dev/null
done; done
for r in 1 2; do for b in c arm64; do
  rm -rf $P/b; mkdir -p $P/samples-$b
  DYLD_INSERT_LIBRARIES=$P/pcprof.dylib PCPROF_OUT=$P/samples-$b/r$r PCPROF_INTERVAL_US=1000 \
    $P/quest-$b -j 1 --backend arm64 --build-dir $P/b -o $P/q questlang/driver/main.quest > /dev/null 2>&1
done; done
echo done >> $P/log

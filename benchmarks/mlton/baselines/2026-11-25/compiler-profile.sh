#!/bin/zsh
# Times and samples the ssac-built and arm64-built compilers compiling the
# driver through arm64 at -j 1 from an empty build directory (§21.5's script,
# with ssac in C's place). Run under tools/exclusive.
P=/private/tmp/claude-501/-Users-haahr-Dropbox-Paul-src-quest--claude-worktrees-fresh-main/441490cd-f5de-4bec-a7e7-c8a7d31929a1/scratchpad/prof
cd /Users/haahr/Dropbox/Paul/src/quest/.claude/worktrees/fresh-main
export QUEST_HOME=$PWD
uptime > $P/log
rm -f $P/times.txt
for r in 1 2 3; do for b in ssac arm64; do
  rm -rf $P/b; echo "time $b round $r" >> $P/times.txt
  /usr/bin/time -l $P/quest-$b -j 1 --backend arm64 --build-dir $P/b -o $P/q questlang/driver/main.quest 2>> $P/times.txt >/dev/null
done; done
for r in 1 2; do for b in ssac arm64; do
  rm -rf $P/b; mkdir -p $P/samples-$b
  DYLD_INSERT_LIBRARIES=$P/pcprof.dylib PCPROF_OUT=$P/samples-$b/r$r PCPROF_INTERVAL_US=1000 \
    $P/quest-$b -j 1 --backend arm64 --build-dir $P/b -o $P/q questlang/driver/main.quest > /dev/null 2>&1
done; done
uptime >> $P/log
echo done >> $P/log

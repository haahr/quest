#!/bin/zsh
# The compiler as C and as arm64 build it, at the tip: each stage 2's own build, then each compiling the driver from an
# empty build directory at -j 8 and -j 1, three rounds alternating; then the suite through C, whole, at scale 0.25.
S=/private/tmp/claude-501/-Users-haahr-Dropbox-Paul-src-quest--claude-worktrees-busy-lehmann-a8b5df/af2067a2-6a39-467d-85b2-fdc296114b49/scratchpad
R=$S/results; mkdir -p $R
cd /Users/haahr/Dropbox/Paul/src/quest/.claude/worktrees/busy-lehmann-a8b5df
export QUEST_JOBS=8 QUEST_HOME=$PWD
P=/opt/homebrew/bin/python3.11
D=questlang/driver/main.quest
idle() { $S/idle.sh 3 > /dev/null; echo "$1 $(date +%T) load $(sysctl -n vm.loadavg)" >> $R/log; }
echo "commit $(git rev-parse --short=8 HEAD)" >> $R/log
rm -rf .build/quest-stages .build/quest-stages-arm64
./quest --help > /dev/null 2>&1; QUEST_BACKEND=arm64 ./quest --help > /dev/null 2>&1
ST1=.build/quest-stages/stage1/quest
idle "stage2 builds"
for r in 1 2; do for b in c arm64; do
  rm -rf $S/s2; /usr/bin/time -l $ST1 -j 8 --backend $b --build-dir $S/s2/b -o $S/s2/q $D 2>> $R/stage2-$b.txt > /dev/null
done; done
typeset -A Q; Q=(c .build/quest-stages/stage2/quest arm64 .build/quest-stages-arm64/stage2/quest)
idle "driver builds"
for r in 1 2 3; do for j in 8 1; do for b in c arm64; do
  rm -rf $S/drv; echo "round $r -j $j" >> $R/driver-$b.txt
  /usr/bin/time -l $Q[$b] -j $j --build-dir $S/drv/b -o $S/drv/q $D 2>> $R/driver-$b.txt > /dev/null
done; done; done
idle "c suite"
$P benchmarks/mlton/run.py time --clean --whole-program --scale 0.25 --backend c --timeout 3600 \
  --results $R/quest-c-whole.jsonl > $R/quest-c-whole.txt 2>&1
echo done >> $R/log

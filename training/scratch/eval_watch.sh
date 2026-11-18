#!/bin/bash
# One line of eval status per poll.
#
# Exit code carries the signal: 0 when the report exists, 9 while the job is
# still writing. Report the highest batch mark (the N in "[eval] N/1125"), not
# the number of such lines — counting lines understates completion and made an
# earlier status line read 16 when 128 rows were done.
R=/projects/u6vs/hnc-organism/runs/eval-base.json
L=/projects/u6vs/hnc-organism/logs/aureon-eval-base-7719095.out

if [ -f "$R" ]; then
    echo "REPORT_READY bytes=$(stat -c %s "$R")"
    exit 0
fi

rows=$(awk '/^\[eval\] [0-9]+\//{split($2,a,"/"); n=a[1]} END{print n+0}' "$L" 2>/dev/null)
q=$(timeout 10 squeue -j 7719095 -h -o '%T %M' 2>/dev/null)
echo "progress rows=${rows:-0}/1125 job=[${q:-squeue-empty}]"
exit 9

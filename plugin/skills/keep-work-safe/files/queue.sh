#!/usr/bin/env bash
# A queue that is safe to run again. Each line of the jobs file is one job:
#
#   <name> <the command, with {out} where the output file goes>
#
#   bash queue.sh jobs.txt work-folder
#
# A job counts as done only when its command exits 0. Its output is written to a
# .part file first and renamed, so a half-written file is never taken for a whole
# one. After a restart, run the same command again: finished jobs are skipped.
set -u
jobs_file=$1
work=$2
mkdir -p "$work"
failed=0
while read -r name cmd; do
  [ -n "$name" ] || continue
  if [ -f "$work/$name.done" ]; then
    echo "skip $name (done)"
    continue
  fi
  part="$work/$name.part.mp4"
  rm -f "$part"
  echo "run  $name"
  # </dev/null matters: ffmpeg reads stdin, and would eat the rest of the jobs file.
  if bash -c "${cmd//\{out\}/$part}" </dev/null >"$work/$name.log" 2>&1; then
    mv "$part" "$work/$name.mp4"
    date > "$work/$name.done"
    echo "done $name"
  else
    echo "FAIL $name, see $work/$name.log"
    failed=$((failed + 1))
  fi
done < "$jobs_file"
echo "QUEUE-END failed=$failed"
[ "$failed" = 0 ]

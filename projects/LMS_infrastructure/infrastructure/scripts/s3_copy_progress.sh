#!/usr/bin/env bash
# Live progress of the one-off Azure -> S3 copy task (lms-staging-s3-copy).
# Reads only object counts/sizes from the bucket and the task's status and
# summary log lines; no file names, settings or secrets are printed.
#
#   scripts/s3_copy_progress.sh            # refresh every 60 s, Ctrl+C to stop
#   INTERVAL=30 scripts/s3_copy_progress.sh
set -uo pipefail
export AWS_REGION=${AWS_REGION:-eu-west-2}
BUCKET=${BUCKET:-lms-staging-files-824892928722}
CLUSTER=lms-staging-cluster
TOTAL_FILES=${TOTAL_FILES:-276080}          # from the dry run
TOTAL_BYTES=${TOTAL_BYTES:-312888002109}    # 313 GB
INTERVAL=${INTERVAL:-60}
LOG_GROUP=/ecs/lms-staging/api

task_arn() {
  aws ecs list-tasks --cluster $CLUSTER --family lms-staging-s3-copy --desired-status RUNNING \
    --query 'taskArns[0]' --output text 2>/dev/null | grep -v None ||
  aws ecs list-tasks --cluster $CLUSTER --family lms-staging-s3-copy --desired-status STOPPED \
    --query 'taskArns[0]' --output text 2>/dev/null
}

start_ts=$(date +%s); start_bytes=""; prev_ts=""; prev_bytes=""

# Before the copy task exists there is nothing to measure: wait for it
while true; do
  TASK=$(task_arn)
  [ -n "$TASK" ] && [ "$TASK" != "None" ] && break
  printf '\r%s  waiting for the copy task to start (checking every 15 s)...' "$(date +%H:%M:%S)"
  sleep 15
done
echo

while true; do
  # Full listing (all pages): object count and total size
  read -r files bytes < <(aws s3 ls "s3://$BUCKET" --recursive --summarize 2>/dev/null |
    awk '/Total Objects:/{o=$3} /Total Size:/{s=$3} END{print o+0, s+0}')
  files=${files:-0}; bytes=${bytes:-0}; now=$(date +%s)
  [ -z "$start_bytes" ] && start_bytes=$bytes && start_files=$files && start_ts=$now

  # All copy tasks (the copy may be split across several in parallel)
  running=$(aws ecs list-tasks --cluster $CLUSTER --family lms-staging-s3-copy --desired-status RUNNING --query 'length(taskArns)' --output text 2>/dev/null)
  running=${running:-0}; extra=""
  if [ "$running" -gt 0 ]; then status="$running running"; else status="all stopped"; fi
  TASK=$(task_arn)

  python3 -I - "$files" "$bytes" "$TOTAL_FILES" "$TOTAL_BYTES" "$now" "$start_ts" "$start_bytes" "${prev_ts:-}" "${prev_bytes:-}" "$status$extra" "$start_files" "${prev_files:-}" <<'EOF'
import sys, datetime
f, b, tf, tb, now, s_ts, s_b, p_ts, p_b, status, s_f, p_f = (sys.argv[1:] + ["", ""])[:12]
f, b, tf, tb, now, s_ts, s_b = int(f), int(float(b)), int(tf), int(tb), int(now), int(s_ts), int(float(s_b))
gb = lambda x: x / 1e9
pct = 100 * b / tb if tb else 0
bar = "#" * int(pct / 2.5) + "-" * (40 - int(pct / 2.5))
print("\033[2J\033[H", end="")
print(f"Azure -> S3 copy   {datetime.datetime.now():%H:%M:%S}   task: {status}")
print(f"[{bar}] {pct:5.1f}%")
print(f"files : {f:,} / {tf:,}  ({100*f/tf:.1f}%)")
print(f"data  : {gb(b):,.1f} / {gb(tb):,.1f} GB")
avg = (b - s_b) / (now - s_ts) if now > s_ts else 0
cur = (b - int(float(p_b))) / (now - int(p_ts)) if p_ts and now > int(p_ts) else 0
print(f"speed : now {cur/1e6:,.1f} MB/s   average {avg/1e6:,.1f} MB/s (since this window opened)")
el = now - s_ts
fr_avg = (f - int(s_f or f)) / el if el > 0 else 0
fr_now = (f - int(p_f)) / (now - int(p_ts)) if p_f and p_ts and now > int(p_ts) else 0
print(f"files/s: now {fr_now:,.1f}   average {fr_avg:,.1f}")
def fmt(sec):
    h, m = divmod(int(sec // 60), 60)
    eta = datetime.datetime.now() + datetime.timedelta(seconds=sec)
    return f"about {h} h {m:02d} min, around {eta:%H:%M}"
if b >= tb and f >= tf:
    print("left  : nothing - all files are in S3 (wait for the task to show STOPPED, exit code 0)")
elif avg > 0 and fr_avg > 0:
    by_data = (tb - b) / avg if b < tb else 0
    by_files = (tf - f) / fr_avg if f < tf else 0
    print(f"left  : {gb(max(tb-b,0)):,.1f} GB and {max(tf-f,0):,} files")
    print(f"finish: {fmt(max(by_data, by_files))}  (the slower of: data {fmt(by_data)} / file count {fmt(by_files)})")
else:
    print("left  : measuring speed... (needs two samples)")
EOF
  echo; echo "containers finished (latest 8):"
  aws logs filter-log-events --log-group-name $LOG_GROUP --log-stream-name-prefix s3-copy/worker/ \
    --start-time $(( (start_ts - 86400) * 1000 )) --filter-pattern '?listed ?Traceback ?CommandError' \
    --query 'events[].message' --output text 2>/dev/null | tr '\t' '\n' | grep -v '^$' | tail -8 | cut -c1-150
  if [ "$running" -eq 0 ]; then echo; echo "All copy tasks have stopped."; break; fi
  prev_ts=$now; prev_bytes=$bytes; prev_files=$files
  sleep "$INTERVAL"
done

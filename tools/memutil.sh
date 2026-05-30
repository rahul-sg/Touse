#!/usr/bin/env bash
# memutil.sh — sample resident memory of a process tree by command-line pattern.
#
# Use cases (this repo):
#   tools/memutil.sh bulk_train_prophet     # Prophet bulk trainer (parent + workers)
#   tools/memutil.sh train_lgbm             # LightGBM training run
#   tools/memutil.sh 'uvicorn app.main'     # backend dev server
#
# What it does well that the original script didn't:
#   - matches against the full command line (`pgrep -f`), so Python scripts
#     show up under their filename, not just "python"
#   - sums RSS across the WHOLE process tree (joblib/multiprocessing pools
#     spawn worker processes that the original script missed)
#   - tracks peak + average and prints a summary when the target exits
#   - works on macOS and Linux (no `top -l`)
#   - exits cleanly when the matched process disappears
#
# Flags:
#   -i SECS   sample interval (default 2)
#   -o FILE   also write CSV (timestamp_iso,total_rss_mb,n_procs) for graphing
#   -m       only print the matched processes once and exit (debug)

set -euo pipefail

INTERVAL=2
CSV=""
DEBUG_MATCH=0

while getopts ":i:o:m" opt; do
    case "$opt" in
        i) INTERVAL="$OPTARG" ;;
        o) CSV="$OPTARG" ;;
        m) DEBUG_MATCH=1 ;;
        \?) echo "unknown flag: -$OPTARG" >&2; exit 2 ;;
    esac
done
shift $((OPTIND - 1))

if [ $# -lt 1 ]; then
    echo "usage: $(basename "$0") [-i SECS] [-o CSV] [-m] <pattern>" >&2
    echo "  pattern matches the full command line (regex via pgrep -f)" >&2
    exit 1
fi
PATTERN="$1"

# Cross-platform RSS lookup: ps -o rss= returns KB on macOS and Linux.
# Returns total RSS (MB) and process count, summed over all matching PIDs.
sample() {
    # shellcheck disable=SC2155
    local pids=$(pgrep -f "$PATTERN" 2>/dev/null || true)
    if [ -z "$pids" ]; then
        echo "0 0"
        return
    fi
    # ps -p accepts a comma-separated list; -o rss= prints kilobytes.
    # shellcheck disable=SC2086
    local pid_csv=$(echo $pids | tr ' ' ',')
    local total_kb=$(ps -p "$pid_csv" -o rss= 2>/dev/null | awk '{s+=$1} END {print s+0}')
    local n=$(echo "$pids" | wc -l | tr -d ' ')
    awk -v kb="$total_kb" -v n="$n" 'BEGIN {printf "%.1f %d\n", kb/1024, n}'
}

# Debug: show what matched then exit
if [ "$DEBUG_MATCH" -eq 1 ]; then
    echo "Matching processes for pattern: $PATTERN"
    pgrep -fl "$PATTERN" || echo "  (none)"
    exit 0
fi

# Wait up to 10s for the target to appear
WAITED=0
while [ -z "$(pgrep -f "$PATTERN" 2>/dev/null || true)" ]; do
    if [ "$WAITED" -ge 10 ]; then
        echo "memutil: no process matches pattern: $PATTERN" >&2
        exit 1
    fi
    sleep 1
    WAITED=$((WAITED + 1))
done

echo "Tracking pattern: $PATTERN   (interval: ${INTERVAL}s)"
echo "$(date '+%H:%M:%S')  total_rss_mb  n_procs"
echo "----------------------------------------"

[ -n "$CSV" ] && echo "timestamp_iso,total_rss_mb,n_procs" > "$CSV"

peak=0
sum=0
samples=0
start_ts=$(date +%s)

# Sample until the matched process tree disappears for 2 consecutive ticks
empty_ticks=0
while true; do
    read -r mb n <<< "$(sample)"
    if [ "$n" -eq 0 ]; then
        empty_ticks=$((empty_ticks + 1))
        if [ "$empty_ticks" -ge 2 ]; then
            break
        fi
        sleep "$INTERVAL"
        continue
    fi
    empty_ticks=0

    printf "%s  %12.1f  %7d\n" "$(date '+%H:%M:%S')" "$mb" "$n"
    [ -n "$CSV" ] && echo "$(date -u +%Y-%m-%dT%H:%M:%SZ),$mb,$n" >> "$CSV"

    # Track peak + running sum (use awk for float math)
    peak=$(awk -v p="$peak" -v m="$mb" 'BEGIN {print (m > p) ? m : p}')
    sum=$(awk -v s="$sum" -v m="$mb" 'BEGIN {printf "%.3f", s + m}')
    samples=$((samples + 1))

    sleep "$INTERVAL"
done

end_ts=$(date +%s)
duration=$((end_ts - start_ts))

echo "----------------------------------------"
echo "Process tree exited."
if [ "$samples" -gt 0 ]; then
    avg=$(awk -v s="$sum" -v n="$samples" 'BEGIN {printf "%.1f", s/n}')
    echo "Summary:"
    echo "  duration:  ${duration}s"
    echo "  samples:   ${samples}"
    echo "  peak RSS:  ${peak} MB"
    echo "  avg  RSS:  ${avg} MB"
else
    echo "No samples collected."
fi

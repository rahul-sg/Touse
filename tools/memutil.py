#!/usr/bin/env python3
"""memutil.py — process-tree memory sampler with real statistics.

Cross-platform Python version of tools/memutil.sh, intended for monitoring
the project's ML training scripts (which spawn multiprocessing worker pools
that the original bash script silently missed):

    python tools/memutil.py bulk_train_prophet
    python tools/memutil.py train_lgbm
    python tools/memutil.py 'uvicorn app.main' --interval 5 --csv mem.csv

What this gives you that the bash version doesn't:
    - per-process breakdown (parent vs each Pool worker) at exit
    - true percentiles (p50/p95) instead of just peak/avg
    - system memory pressure context (RAM used %, swap used %)
    - tracks short-lived workers via psutil's child enumeration

Dependency: psutil (already in the project's backend requirements indirectly
via several deps; install standalone with `pip install psutil` if missing).
"""
from __future__ import annotations

import argparse
import csv
import re
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

try:
    import psutil
except ImportError:
    sys.exit("memutil.py requires psutil. Install with: pip install psutil")


def find_matching_pids(pattern: re.Pattern[str]) -> list[psutil.Process]:
    """Return all running processes whose full command line matches `pattern`.

    Excludes the monitor itself so we don't accidentally include this script's
    own line (it's running with 'memutil.py' in argv).
    """
    self_pid = psutil.Process().pid
    matches = []
    for p in psutil.process_iter(["pid", "cmdline"]):
        if p.info["pid"] == self_pid:
            continue
        cmdline = " ".join(p.info.get("cmdline") or [])
        if not cmdline:
            continue
        if pattern.search(cmdline):
            matches.append(p)
    return matches


def collect_tree_memory(roots: list[psutil.Process]) -> tuple[float, int, dict[int, float]]:
    """Sum RSS (MB) across roots + all their descendants.

    Returns (total_mb, n_processes, per_pid_mb).
    Disappeared processes are silently skipped — normal during pool worker
    churn or right before exit.
    """
    seen: set[int] = set()
    per_pid: dict[int, float] = {}
    total_kb = 0.0

    for root in roots:
        try:
            procs = [root, *root.children(recursive=True)]
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
        for p in procs:
            if p.pid in seen:
                continue
            seen.add(p.pid)
            try:
                rss = p.memory_info().rss
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
            total_kb += rss / 1024
            per_pid[p.pid] = rss / (1024 * 1024)
    return total_kb / 1024, len(seen), per_pid


def fmt_mb(mb: float) -> str:
    if mb >= 1024:
        return f"{mb / 1024:.2f} GB"
    return f"{mb:.1f} MB"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Sample memory of a process tree by command-line pattern.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("pattern", help="regex matched against full cmdline (case-sensitive)")
    parser.add_argument("-i", "--interval", type=float, default=2.0,
                        help="seconds between samples (default: 2)")
    parser.add_argument("-o", "--csv", type=Path, default=None,
                        help="also write CSV (timestamp,total_mb,n_procs,sys_used_pct,swap_used_pct)")
    parser.add_argument("--wait", type=int, default=10,
                        help="seconds to wait for the target to appear (default: 10)")
    parser.add_argument("--list", action="store_true",
                        help="just list matching processes and exit")
    args = parser.parse_args()

    try:
        pattern = re.compile(args.pattern)
    except re.error as exc:
        sys.exit(f"invalid regex: {exc}")

    if args.list:
        for p in find_matching_pids(pattern):
            cmd = " ".join(p.cmdline()[:6])
            print(f"  pid {p.pid:>6}  {cmd}")
        return 0

    # Wait for the target to appear
    waited = 0
    while not (roots := find_matching_pids(pattern)):
        if waited >= args.wait:
            sys.exit(f"no process matches pattern: {args.pattern}")
        time.sleep(1)
        waited += 1

    print(f"Tracking pattern: {args.pattern}   (interval: {args.interval}s)")
    sys_mem = psutil.virtual_memory()
    print(f"System: {fmt_mb(sys_mem.total / (1024*1024))} total RAM")
    print(f"{'time':10s}  {'total':>10s}  {'n':>4s}  {'sys%':>6s}  {'swap%':>6s}")
    print("-" * 50)

    csv_writer = None
    csv_fp = None
    if args.csv:
        csv_fp = open(args.csv, "w", newline="")
        csv_writer = csv.writer(csv_fp)
        csv_writer.writerow(["timestamp_iso", "total_mb", "n_procs",
                             "sys_used_pct", "swap_used_pct"])

    samples_mb: list[float] = []
    samples_n: list[int] = []
    final_per_pid: dict[int, float] = {}
    start = time.monotonic()
    empty_ticks = 0

    try:
        while True:
            roots = find_matching_pids(pattern)
            mb, n, per_pid = collect_tree_memory(roots)
            if n == 0:
                empty_ticks += 1
                if empty_ticks >= 2:
                    break
                time.sleep(args.interval)
                continue
            empty_ticks = 0

            sys_mem = psutil.virtual_memory()
            swap = psutil.swap_memory()
            now = datetime.now().strftime("%H:%M:%S")
            print(f"{now:10s}  {fmt_mb(mb):>10s}  {n:>4d}  "
                  f"{sys_mem.percent:>5.1f}%  {swap.percent:>5.1f}%")

            if csv_writer:
                csv_writer.writerow([
                    datetime.now(timezone.utc).isoformat(timespec="seconds"),
                    f"{mb:.1f}", n,
                    f"{sys_mem.percent:.1f}", f"{swap.percent:.1f}",
                ])
                csv_fp.flush()

            samples_mb.append(mb)
            samples_n.append(n)
            final_per_pid = per_pid  # snapshot last reading for the breakdown
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\n(interrupted)")
    finally:
        if csv_fp:
            csv_fp.close()

    duration = time.monotonic() - start
    print("-" * 50)
    if not samples_mb:
        print("No samples collected.")
        return 0

    peak = max(samples_mb)
    avg = statistics.fmean(samples_mb)
    p50 = statistics.median(samples_mb)
    p95 = (statistics.quantiles(samples_mb, n=20)[-1]
           if len(samples_mb) >= 2 else peak)
    print("Process tree exited.")
    print()
    print(f"Duration:    {duration:.1f}s")
    print(f"Samples:     {len(samples_mb)}")
    print(f"Peak RSS:    {fmt_mb(peak)}")
    print(f"Avg  RSS:    {fmt_mb(avg)}")
    print(f"p50  RSS:    {fmt_mb(p50)}")
    print(f"p95  RSS:    {fmt_mb(p95)}")
    print(f"Peak procs:  {max(samples_n)}")
    if final_per_pid:
        print("\nLast-seen per-process breakdown:")
        for pid, pmb in sorted(final_per_pid.items(), key=lambda x: -x[1])[:10]:
            print(f"  pid {pid:>6}: {fmt_mb(pmb)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

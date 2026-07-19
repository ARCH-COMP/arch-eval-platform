#!/usr/bin/env python3
"""ARCH per-instance harness — runs ON the node (stdlib only, like VNN's node scripts).

The harness owns timing: for each instance it runs the tool's ``prepare_instance.sh``
then ``run_instance.sh``, measuring wall-clock and enforcing the optional per-instance
timeout. The tool self-reports only its *verdict* (and any category-specific numbers)
by writing a small header+row CSV to the ``results_file`` path passed as the last
argument to ``run_instance.sh``. The harness merges that with its measured time into
one ``results.csv`` row:

    benchmark, instance, <tool-reported extra columns...>, prepare_time, result, time

where ``time`` is the harness wall-clock (canonical) and the tool's extras (e.g. the
AINNCS CORA breakdown ``time_*``) ride along as columns. All instances.csv columns are
passed, in file order, to ``prepare_instance.sh``/``run_instance.sh`` (tools ignore the
ones they don't need). A ``timeout`` column caps that instance; absent/blank/``inf`` =
no cap.
"""
import csv
import json
import os
import signal
import subprocess
import sys
import tempfile
import time

#: Safety cap on prepare (mirrors VNN's 10 min); the per-instance run timeout is the
#: category's own, from the instances.csv ``timeout`` column (or uncapped).
PREPARE_CAP_SECONDS = 600

BENCHMARK_COLUMN = "benchmark"
INSTANCE_COLUMN = "instance"
TIMEOUT_COLUMN = "timeout"
RESULT_COLUMN = "result"
NO_CAP = {"", "inf", "infinity", "none", "-1"}


def _parse_timeout(value):
    """Seconds as a float, or ``None`` for no cap."""
    if value is None:
        return None
    v = str(value).strip().lower()
    if v in NO_CAP:
        return None
    try:
        t = float(v)
    except ValueError:
        return None
    return t if t > 0 else None


def _timed_run(cmd, cwd, timeout):
    """Run ``cmd`` to completion or until ``timeout`` seconds. Returns
    ``(elapsed_seconds, timed_out, returncode)``. Kills the whole process group on
    timeout so a tool's grandchildren don't outlive it."""
    start = time.monotonic()
    proc = subprocess.Popen(
        cmd, cwd=cwd, start_new_session=True,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    timed_out = False
    try:
        proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        proc.communicate()
    return time.monotonic() - start, timed_out, proc.returncode


def _read_tool_result(path):
    """The tool's self-reported ``(result, extra)`` from its header+row CSV. ``extra``
    preserves the tool's column order, minus ``result``. Missing/empty file → unknown."""
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        return "", {}
    with open(path, newline="") as fh:
        reader = csv.DictReader(fh)
        row = next(reader, None)
        if row is None:
            return "", {}
        result = (row.get(RESULT_COLUMN) or "").strip()
        extra = {k: (v or "").strip() for k, v in row.items()
                 if k is not None and k != RESULT_COLUMN}
    return result, extra


def run_instance(tool_dir, version, category, values, timeout):
    """Run one instance: prepare (capped at ``PREPARE_CAP_SECONDS``) then run (capped at
    ``timeout``). The tool scripts are called as ``<version> <category> <col1..colN>``
    (the instances.csv columns in file order — ``benchmark``, ``instance``, …), with the
    results file appended for the run. Returns ``{prepare_time, result, time, extra}``."""
    prep_elapsed, prep_to, prep_rc = _timed_run(
        [os.path.join(tool_dir, "prepare_instance.sh"), version, category, *values],
        tool_dir, PREPARE_CAP_SECONDS,
    )
    if prep_to or prep_rc != 0:
        # A failed prepare skips the instance (rule-compliant: it scores as unsolved).
        return {"prepare_time": round(prep_elapsed, 4), "result": "prepare_failed",
                "time": 0.0, "extra": {}}

    fd, res_path = tempfile.mkstemp(suffix=".csv")
    os.close(fd)
    try:
        run_elapsed, run_to, run_rc = _timed_run(
            [os.path.join(tool_dir, "run_instance.sh"), version, category, *values, res_path],
            tool_dir, timeout,
        )
        if run_to:
            result, extra = "timeout", {}
        else:
            result, extra = _read_tool_result(res_path)
            if not result:
                result = "unknown" if run_rc == 0 else "error"
        return {"prepare_time": round(prep_elapsed, 4), "result": result,
                "time": round(run_elapsed, 4), "extra": extra}
    finally:
        os.unlink(res_path)


def _read_instances(path):
    with open(path, newline="") as fh:
        reader = csv.reader(fh)
        header = [h.strip() for h in next(reader)]
        rows = [{col: val.strip() for col, val in zip(header, raw)}
                for raw in reader if any(c.strip() for c in raw)]
    return header, rows


def run_benchmark(repo_dir, benchmark_name, tool_dir, out_csv, version, category):
    """Run every instance of ``benchmark_name`` (from ``repo_dir/instances.csv``) and
    write ``out_csv``. The output header is stable within the benchmark: the union of
    tool-reported extra columns (first-seen order) sits between the identifiers and the
    harness timings."""
    header, rows = _read_instances(os.path.join(repo_dir, "instances.csv"))
    target = [r for r in rows if r.get(BENCHMARK_COLUMN) == benchmark_name]

    extra_cols = []
    results = []
    for r in target:
        values = [r[c] for c in header]
        out = run_instance(tool_dir, version, category, values, _parse_timeout(r.get(TIMEOUT_COLUMN)))
        for k in out["extra"]:
            if k not in extra_cols:
                extra_cols.append(k)
        results.append((r, out))

    out_header = [BENCHMARK_COLUMN, INSTANCE_COLUMN] + extra_cols + ["prepare_time", RESULT_COLUMN, "time"]
    with open(out_csv, "w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(out_header)
        for r, out in results:
            writer.writerow(
                [r.get(BENCHMARK_COLUMN, ""), r.get(INSTANCE_COLUMN, "")]
                + [out["extra"].get(c, "") for c in extra_cols]
                + [out["prepare_time"], out["result"], out["time"]]
            )
    return out_csv


def main(argv):
    if len(argv) >= 8 and argv[1] == "benchmark":
        run_benchmark(argv[2], argv[3], argv[4], argv[5], argv[6], argv[7])
        return 0
    if len(argv) >= 7 and argv[1] == "instance":
        out = run_instance(argv[2], argv[3], argv[4], argv[6:], _parse_timeout(argv[5]))
        print(json.dumps(out))
        return 0
    sys.stderr.write(
        "usage: harness.py benchmark <repo_dir> <benchmark_name> <tool_dir> <out_csv> <version> <category>\n"
        "       harness.py instance  <tool_dir> <version> <category> <timeout|inf> <col1> [col2 ...]\n"
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

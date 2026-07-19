"""The node-side ARCH harness (arch_comp/scripts/harness.py): timing, timeout, and
results.csv assembly, exercised against fake tool scripts. No Django/DB needed."""
import csv
import os
import subprocess
import sys

import arch_comp

HARNESS = os.path.join(os.path.dirname(arch_comp.__file__), "scripts", "harness.py")


def _script(path, body):
    with open(path, "w", newline="\n") as fh:
        fh.write(body)
    os.chmod(path, 0o755)


def _tool(dir_, run_body, prepare_body="#!/bin/sh\nexit 0\n"):
    os.makedirs(dir_, exist_ok=True)
    _script(os.path.join(dir_, "prepare_instance.sh"), prepare_body)
    _script(os.path.join(dir_, "run_instance.sh"), run_body)
    return dir_


def _repo(dir_, instances_csv):
    os.makedirs(dir_, exist_ok=True)
    with open(os.path.join(dir_, "instances.csv"), "w", newline="\n") as fh:
        fh.write(instances_csv)
    return dir_


def _run_benchmark(repo, name, tool, out, version="v1", category="AINNCS"):
    subprocess.run([sys.executable, HARNESS, "benchmark", repo, name, tool, out, version, category],
                   check=True)
    with open(out, newline="") as fh:
        return list(csv.DictReader(fh))


# A tool that self-reports a verdict + a CORA-style breakdown to its results file
# (the last argument), like AINNCS.
VERIFYING_TOOL = (
    "#!/bin/sh\n"
    'for a in "$@"; do last="$a"; done\n'
    'printf "result,time_verification\\nverified,0.42\\n" > "$last"\n'
)


def test_records_result_and_harness_wall_clock(tmp_path):
    repo = _repo(tmp_path / "repo", "benchmark,instance\nACC,a1\nACC,a2\nOTHER,x\n")
    tool = _tool(tmp_path / "tool", VERIFYING_TOOL)
    out = str(tmp_path / "results.csv")

    rows = _run_benchmark(repo, "ACC", tool, out)

    assert [r["instance"] for r in rows] == ["a1", "a2"]  # OTHER benchmark excluded
    assert all(r["result"] == "verified" for r in rows)
    # Harness owns `time` (wall-clock, >= 0); tool's breakdown rides along as a column.
    assert all(float(r["time"]) >= 0.0 for r in rows)
    assert rows[0]["time_verification"] == "0.42"
    assert "prepare_time" in rows[0]


# A tool that echoes the arguments it received back into the results file, to check the
# harness passes them as <version> <category> <benchmark> <instance> ... <results_file>.
ECHO_TOOL = (
    "#!/bin/sh\n"
    'for a in "$@"; do last="$a"; done\n'
    'printf "result,seen_version,seen_category,seen_benchmark,seen_instance\\n" > "$last"\n'
    'printf "unknown,%s,%s,%s,%s\\n" "$1" "$2" "$3" "$4" >> "$last"\n'
)


def test_forwards_version_category_then_columns(tmp_path):
    repo = _repo(tmp_path / "repo", "benchmark,instance\nACC,a1\n")
    tool = _tool(tmp_path / "tool", ECHO_TOOL)
    out = str(tmp_path / "results.csv")
    (row,) = _run_benchmark(repo, "ACC", tool, out, version="v1", category="AINNCS")
    assert row["seen_version"] == "v1"
    assert row["seen_category"] == "AINNCS"
    assert row["seen_benchmark"] == "ACC"
    assert row["seen_instance"] == "a1"


def test_optional_timeout_column_caps_the_run(tmp_path):
    slow_tool = (
        "#!/bin/sh\n"
        'for a in "$@"; do last="$a"; done\n'
        'sleep 2\n'
        'printf "result\\nverified\\n" > "$last"\n'
    )
    repo = _repo(tmp_path / "repo", "benchmark,instance,timeout\nACC,slow,0.5\n")
    tool = _tool(tmp_path / "tool", slow_tool)
    out = str(tmp_path / "results.csv")

    (row,) = _run_benchmark(repo, "ACC", tool, out)
    assert row["result"] == "timeout"
    assert float(row["time"]) < 2.0  # killed at the cap, not after the full sleep


def test_no_timeout_column_runs_uncapped(tmp_path):
    repo = _repo(tmp_path / "repo", "benchmark,instance\nACC,a1\n")
    tool = _tool(tmp_path / "tool", VERIFYING_TOOL)
    out = str(tmp_path / "results.csv")
    (row,) = _run_benchmark(repo, "ACC", tool, out)
    assert row["result"] == "verified"


def test_prepare_failure_is_recorded(tmp_path):
    repo = _repo(tmp_path / "repo", "benchmark,instance\nACC,a1\n")
    tool = _tool(tmp_path / "tool", VERIFYING_TOOL, prepare_body="#!/bin/sh\nexit 1\n")
    out = str(tmp_path / "results.csv")
    (row,) = _run_benchmark(repo, "ACC", tool, out)
    assert row["result"] == "prepare_failed"
    assert float(row["time"]) == 0.0

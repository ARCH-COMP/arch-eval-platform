#!/usr/bin/env bash
# Node-side ARCH harness: run every instance of one benchmark and write results.csv.
# Usage: run_benchmark.sh <repo_dir> <benchmark_name> <tool_dir> <out_csv>
#   repo_dir  checkout of the category's benchmarks repo (holds instances.csv + data)
#   tool_dir  checkout of the tool (holds prepare_instance.sh / run_instance.sh)
set -euo pipefail
exec python3 "$(dirname "$0")/harness.py" benchmark "$@"

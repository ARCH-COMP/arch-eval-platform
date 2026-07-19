#!/usr/bin/env bash
# Node-side ARCH harness: run a single instance (debugging / parity with the contract).
# Prints {prepare_time, result, time, extra} as JSON.
# Usage: run_single_instance.sh <tool_dir> <timeout|inf> <col1> [col2 ...]
set -euo pipefail
exec python3 "$(dirname "$0")/harness.py" instance "$@"

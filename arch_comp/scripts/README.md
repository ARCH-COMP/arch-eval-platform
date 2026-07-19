# ARCH-COMP node scripts

- `arch/` — backend-side SSH wrappers fired by the step handlers (`_ping("arch", …)`).
  Each SSHes into `ubuntu@<node>`, does its work, and POSTs back to
  `${ROOT_URL}/update/<task_id>/success|failure`.
  - `install_tool.sh` — clone the tool, run its `install_tool.sh <version>`.
  - `load_benchmark.sh` — clone a category's central repo (its `instances.csv` is read back
    and fanned into benchmarks).
  - `run_benchmark.sh` — ship `harness.py`, clone the benchmarks repo, run the benchmark's
    instances, write `results_<benchmark_id>.csv`.
- `harness.py` — the node-side per-instance harness (stdlib). Loops a benchmark's instances,
  running the tool's `prepare_instance.sh` / `run_instance.sh` (`<version> <category> <benchmark>
  <instance> …`), owning timing + the optional per-instance timeout, and assembling `results.csv`.

Node bootstrapping is provided by core (`comp_eval_platform/scripts/docker/bootstrap_node.sh`).

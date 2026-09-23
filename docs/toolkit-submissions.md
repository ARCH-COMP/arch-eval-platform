# Toolkit submissions

An ARCH tool is a Git repository plus a worker base image, revision, script directory,
category, and selected benchmarks. Start from the
[example toolkit](https://github.com/ARCH-COMP/example_toolkit).

## Required repository interface

The script directory must provide:

- `install_tool.sh` — called once as `install_tool.sh v1`;
- `prepare_instance.sh` — called before an instance;
- `run_instance.sh` — runs an instance and writes the result file it is given.

The default interface version is `v1`. A tool may carry another explicit interface
version in plugin metadata; submissions without one use `v1`.

For every row selected from the category's `instances.csv`, the harness calls:

```text
prepare_instance.sh v1 <category> <benchmark> <instance> [extra columns...]
run_instance.sh     v1 <category> <benchmark> <instance> [extra columns...] <result-file> <figures-dir>
```

Extra arguments follow the CSV header order after the required `benchmark` and `instance`
columns. The result-file path is the second-to-last `run_instance.sh` argument and the
figures directory is last. Write the result CSV to the former and optional plots or other
figures to the latter.

A non-zero preparation exit skips that instance. When an instance includes a `timeout`
value, the harness applies it as a wall-clock limit to `run_instance.sh`; an omitted
timeout leaves the instance uncapped at the harness layer. Core task backstops still apply.

## Result file

The result file is CSV with a header. At minimum it must contain a `result` column. The
generic parser understands `instance`, `result`, and `time`; the harness owns canonical
wall-clock timing.

Typical values are:

- `verified`
- `falsified`
- `unknown`
- `error`
- `timeout`

AINNCS may additionally report the category timing fields documented in
[Categories and results](categories-and-results.md). Category-specific values are stored as
result metadata while the harness time remains the normalized `time`.

## Reproducibility

Submit an immutable commit hash. The current ARCH installation handler does not backfill a
branch or tag with the resolved checkout SHA, so a moving ref is not sufficient for strict
reproducibility. The worker image is also part of the submission contract: Docker
deployments require a Docker image reference, while an AWS deployment requires a compatible
AMI and additional deployment infrastructure.

## Operational guidance

- Keep scripts non-interactive and fail with a useful exit status.
- Do not place credentials or licenses in the repository. Use the deployment's approved
  secret/licensing process.
- Avoid root execution unless installation genuinely requires it.
- Write enough diagnostic output for the live step log, but do not print secrets.
- Test against the example benchmark/tool contracts before a competition run.

# Architecture and pipelines

ARCH-COMP is a competition plugin for the shared evaluation platform. The repository
contains the `arch_comp` Django app, ARCH-specific scripts and result parsing, deployment
configuration, tests, and a pinned `core` submodule. The frontend, users, task state
machine, worker lifecycle, APIs, and scheduler come from core.

## ARCH-specific responsibilities

- define the fixed category axis;
- validate ARCH tool and benchmark submissions;
- load a category's central `instances.csv` into benchmark and instance rows;
- build tool-run and category-load step graphs;
- run the ARCH tool interface on a worker;
- parse category-specific results and build ARCH scoreboards;
- contribute ARCH branding and participant guides to the shared frontend.

## Tool run pipeline

For a submitted tool the plugin creates:

```text
Create Submission
  -> Assign Worker
  -> Install Tool
  -> Run Benchmark (one step for each selected published benchmark)
  -> Shutdown
```

The create step records the submission. Assignment is the shared core worker operation.
Installation clones the tool at its recorded revision and invokes its install script. Each
benchmark step invokes the ARCH harness for that benchmark's ordered instances, collects
the resulting CSV, parses it through the category specification, and stores normalized
results. Shutdown releases the worker even after a terminal outcome.

A tool belongs to exactly one ARCH category. Its submitted benchmark IDs restrict the run
to that subset. The shared browser form currently infers the category from selected
benchmark IDs rather than sending it separately. A non-empty selection preserves the ARCH
category. An empty browser selection is stored under `default` and runs no ARCH category
benchmarks; the plugin's "all published benchmarks in this category" fallback applies only
when another API path preserves the ARCH category.

## Benchmark-load pipeline

ARCH benchmark submissions represent a whole category repository rather than one named
benchmark:

```text
Create Submission
  -> Assign Worker
  -> Load Benchmarks
  -> Shutdown
```

The load step clones the submitted repository and revision, reads its root
`instances.csv`, and fans distinct `benchmark` values into durable `Benchmark` rows. The
exact resolved Git revision is stored when available.

Loading is a full replacement for the category. Existing benchmark instances are replaced,
and benchmarks omitted by the new CSV are deleted. A category therefore mirrors the
submitted repository revision after a successful load.

## Worker and callback model

ARCH handlers start shell wrappers under `arch_comp/scripts/arch`. The wrappers perform
work on the assigned worker and report completion to the shared callback endpoints. Live
logs and partial result rows are polled through core while the task is active.

Compute behavior is not ARCH-specific. The provided Compose stack uses `local_docker`;
`remote_docker` can place containers on a separate worker machine. See the core
[compute-backend documentation](https://github.com/TUMcps/core-eval-platform/blob/main/docs/compute-backends.md).

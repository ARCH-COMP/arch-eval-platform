# ARCH-COMP platform documentation

This directory documents the current ARCH-COMP plugin. It replaces the legacy
submission-system wiki; it does not describe the retired ZIP/queue/object-storage
application.

## Start here

- [Architecture and pipelines](architecture-and-pipelines.md)
- [Toolkit submissions](toolkit-submissions.md)
- [Benchmark submissions](benchmark-submissions.md)
- [Categories and results](categories-and-results.md)
- [Operations](operations.md)

## Historical and migration

- [Migration from the legacy system](history/migration-from-legacy.md)

Participant-facing copies of the tool and benchmark instructions are rendered inside the
application from `arch_comp/guides.py`; the documents here provide the deeper contracts.

Shared accounts, roles, task state, scheduling, callbacks, compute backends, runtime
settings, security, and backup boundaries are documented by the
[core evaluation platform](https://github.com/TUMcps/core-eval-platform/tree/main/docs).

## Scope

This repository documents ARCH-COMP-specific behavior: fixed categories,
category benchmark repositories, tool script arguments, result parsing, category scoring,
and ARCH step handlers. Shared platform behavior is documented in core.

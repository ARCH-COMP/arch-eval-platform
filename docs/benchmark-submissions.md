# Benchmark submissions

ARCH-COMP uses one benchmark repository per category. A submission names the category,
repository, and Git revision; it does not create only one benchmark. Start from the
[example benchmark repository](https://github.com/ARCH-COMP/example_benchmark).

## Repository layout

The repository root must contain `instances.csv`. Its header must include `benchmark` and
`instance`; keeping them first is recommended for readability but is not required.
The optional `group` column assigns each benchmark to a competition-defined group:

```csv
benchmark,instance,group
TORA,reach,default
TORA,remain,default
VCAS,worst-19.5,default
```

- `benchmark` groups rows into the selectable benchmark unit.
- `instance` identifies the case within that benchmark.
- `group` is optional benchmark metadata. Missing and blank values use `default`; all
  rows for one benchmark must name the same configured group. It is not passed to tool
  scripts.
- additional columns contain category-specific inputs passed to the tool scripts;
- an optional `timeout` column sets the per-instance wall-clock cap in seconds when it is a
  positive number. Blank, invalid, zero, and negative values are currently treated as
  uncapped by the harness.

Rows must have the same number of fields as the header. Blank rows are ignored. Benchmark
and instance names must be unique within the constraints of the generated catalog.

Networks, models, specifications, and other files referenced by the rows live in the same
repository. Their detailed layout is category-specific; tool scripts interpret the ordered
row values.

## Load semantics

A successful load:

1. clones the repository at the requested ref on a worker;
2. records the resolved commit when available;
3. parses `instances.csv`;
4. creates or updates one published benchmark for every distinct `benchmark` value,
   assigning its optional `group` (or `default`);
5. replaces each benchmark's instances in CSV order;
6. removes category benchmarks no longer present in the CSV.

Because loading is destructive replacement at the category level, review a changed CSV
before submitting it. The task history remains available, but removed catalog rows are not
kept as parallel active versions.

The ordered execution header is stored on the benchmark because JSON object key order is
not used as an execution contract. The reserved `group` column is omitted from that header
and from instance values; remaining instance values are stored by column name.

## Validation checklist

- The category is one of the plugin's configured categories.
- `instances.csv` exists at the repository root.
- The header includes `benchmark` and `instance` exactly.
- Every `group` value is configured by the competition, and is consistent within a
  benchmark.
- Every data row matches the header width.
- Referenced assets exist at the submitted revision; the loader does not verify them.
- Optional timeout values are positive numbers.
- No credential, license secret, private key, or unpublished sensitive data is committed.

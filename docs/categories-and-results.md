# Categories and results

## Fixed categories

The current plugin seeds three categories:

- `AFF`
- `NLN`
- `AINNCS`

Every tool targets one category, and every category load replaces the benchmarks for that
category. The category axis is defined by the plugin's central list, and AINNCS has the
only category-specific result parser in the current implementation.

## Parsing

The generic category parser reads a headered `results.csv` and normalizes:

| Field | Meaning |
| --- | --- |
| `instance` | Instance name used to associate the row with the catalog |
| `result` | Tool verdict |
| `time` | Harness-measured wall-clock time |

AINNCS also accepts these self-reported timing values in result metadata:

- `time_random`
- `time_violation`
- `time_reachable`
- `time_verification`

Missing or non-numeric timing values become null. The tool's breakdown does not replace the
harness-measured normalized time.

## Run summary

After each benchmark finishes, the plugin stores normalized per-instance results and freezes
a verdict tally onto the step payload for the details page. ARCH does not currently run a
separate counterexample-validation step. A task's downloadable bundle may contain the raw
result CSV, run log, and any collected figures.

## Scoreboard

Scoreboards operate on organizer-managed tracks. For every tool/category pair, the current
scorer reports:

- number of solved results;
- sum of normalized result time.

`unknown`, `error`, `timeout`, and `falsified` do not count as solved. Rows are ordered by
category, descending solved count, then ascending total time.

This is the current platform aggregation, not a replacement for any category's official
competition rules. The current scorer contains no additional category-specific official
formula beyond the aggregation described above.

# arch-comp

The **ARCH-COMP** variant of [comp-eval-platform](../comp-eval-platform), professionalized
onto the same structured rung as VNN: an ARCH tool defines a Docker base image,
the engine clones the tool into it, installs + activates the license, then runs
each benchmark's instances.

The variant is:
- `arch_comp/competition.py` — the six seams.
- `arch_comp/categories.py` — **per-category** specs (result fields + parser),
  the ARCH-specific axis. `ArchCompetition` dispatches parsing/scoring by a
  submission's category. Ships `default` + `AINNCS` (CORA timing breakdown).
- `arch_comp/steps.py` — step handlers (create / install / run_benchmark).
- `deploy/` — settings (`ACTIVE_COMPETITION="arch"`) + `manage.py`.

Adding a category = a new `CategorySpec` subclass; adding a competition = a repo
like this. No core changes.

## Test
```bash
docker run --rm -v "<core>:/core" -v "$PWD:/arch" -w /arch python:3.11-slim \
  sh -c "pip install -q -e '/core[dev]' -e /arch && pytest"
```

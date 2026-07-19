"""Load an ARCH category's benchmarks from a central ``instances.csv``.

Unlike VNN (one repo per benchmark), an ARCH category ships a single repo whose
``instances.csv`` lists every benchmark and instance. Submitting a benchmark set is
therefore just naming ``(category, repository, hash)``: we clone that ref, read the
CSV, and fan it out into one ``Benchmark`` per distinct ``benchmark`` value, each
owning its rows as ``Instance``s.

Columns beyond ``benchmark``/``instance`` are category-specific and carried through
verbatim, in file order, to ``prepare_instance.sh``/``run_instance.sh``. Since jsonb
does not preserve dict key order, the ordered header lives once on
``Benchmark.extra["columns"]``; per-instance values are addressed by name in
``Instance.spec``. A ``timeout`` column, if present, caps that instance; absent, the
instance runs uncapped.
"""
import csv
import io
import os
import subprocess
import tempfile

from django.core.exceptions import ValidationError
from django.db import transaction

INSTANCES_FILE = "instances.csv"
BENCHMARK_COLUMN = "benchmark"
INSTANCE_COLUMN = "instance"
TIMEOUT_COLUMN = "timeout"


def parse_instances_csv(text: str):
    """Return ``(header, rows)`` for an ``instances.csv``, where ``rows`` is a list of
    ``{column: value}`` dicts. Requires the ``benchmark`` and ``instance`` columns and
    preserves column order in ``header``."""
    reader = csv.reader(io.StringIO(text))
    try:
        header = [h.strip() for h in next(reader)]
    except StopIteration:
        raise ValidationError(f"{INSTANCES_FILE} is empty.")
    for required in (BENCHMARK_COLUMN, INSTANCE_COLUMN):
        if required not in header:
            raise ValidationError(
                f"{INSTANCES_FILE} must have a '{required}' column; header is {header}."
            )
    rows = []
    for raw in reader:
        if not any(cell.strip() for cell in raw):
            continue  # tolerate blank lines
        if len(raw) != len(header):
            raise ValidationError(
                f"{INSTANCES_FILE} row {raw} has {len(raw)} fields, expected {len(header)}."
            )
        rows.append({col: val.strip() for col, val in zip(header, raw)})
    return header, rows


def group_by_benchmark(rows):
    """``{benchmark_name: [row, ...]}`` in first-seen order."""
    groups = {}
    for row in rows:
        groups.setdefault(row[BENCHMARK_COLUMN], []).append(row)
    return groups


@transaction.atomic
def load_benchmarks_from_csv(*, category, repository, ref, owner, csv_text):
    """Create/refresh ``category``'s benchmarks from ``instances.csv`` text. Re-loading
    replaces each benchmark's instances, so pointing a category at a new hash is
    idempotent. Loaded benchmarks are published (selectable at tool-submission time)."""
    from comp_eval_platform.core.models import Benchmark, Instance

    header, rows = parse_instances_csv(csv_text)
    benchmarks = []
    for name, group in group_by_benchmark(rows).items():
        benchmark, _ = Benchmark.objects.update_or_create(
            category=category, name=name,
            defaults={
                "owner": owner, "repository": repository, "hash": ref,
                "published": True, "extra": {"columns": header},
            },
        )
        benchmark.instances.all().delete()
        Instance.objects.bulk_create([
            Instance(benchmark=benchmark, name=row[INSTANCE_COLUMN], spec=row, order=i)
            for i, row in enumerate(group)
        ])
        benchmarks.append(benchmark)
    return benchmarks


def load_benchmarks_from_repo(*, category, repository, ref, owner):
    """Clone ``repository`` at ``ref``, read its ``instances.csv``, and load it."""
    with tempfile.TemporaryDirectory() as tmp:
        _clone_at_ref(repository, ref, tmp)
        path = os.path.join(tmp, INSTANCES_FILE)
        if not os.path.exists(path):
            raise ValidationError(f"{repository}@{ref} has no {INSTANCES_FILE}.")
        with open(path, encoding="utf-8") as fh:
            csv_text = fh.read()
    return load_benchmarks_from_csv(
        category=category, repository=repository, ref=ref, owner=owner, csv_text=csv_text,
    )


def _clone_at_ref(repository, ref, dest):
    """Fetch ``repository`` at ``ref`` into ``dest`` (non-interactive)."""
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0")
    try:
        subprocess.run(["git", "clone", "--quiet", repository, dest],
                       check=True, env=env, capture_output=True, text=True)
        subprocess.run(["git", "-C", dest, "checkout", "--quiet", ref],
                       check=True, env=env, capture_output=True, text=True)
    except subprocess.CalledProcessError as exc:
        raise ValidationError(f"Could not fetch {repository}@{ref}: {exc.stderr or exc}")

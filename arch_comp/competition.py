"""The ARCH-COMP variant: the six seams.

Professionalized onto the same structured rung as VNN — an ARCH tool defines a
Docker base image, we clone the tool into it, run install/license, then run each
benchmark's instances via a per-instance script. What stays ARCH-specific is the
**per-category** parsing/scoring, dispatched via categories.py.
"""
import os

from django.core.exceptions import ValidationError

from comp_eval_platform.competitions import Competition
from comp_eval_platform.core.models.execution import SHUTDOWN_KIND
from comp_eval_platform.results import Presentation, Scoreboard

from . import kinds
from .categories import get_category_spec


class ArchCompetition(Competition):
    name = "arch"
    display_name = "ARCH-COMP"

    # (1) Submission spec + validation ------------------------------------
    def validate_submission(self, submission) -> None:
        from comp_eval_platform.core.models import Tool

        if isinstance(submission, Tool):
            if not submission.base_image:
                raise ValidationError("An ARCH-COMP tool must define a Docker base image.")
        else:  # Benchmark
            if not submission.instances.exists():
                raise ValidationError("An ARCH-COMP benchmark must define at least one instance.")

    # (2) Step-graph builder ----------------------------------------------
    def build_steps(self, task) -> list:
        from comp_eval_platform.core.models import Benchmark, TaskStep

        order = 0

        def add(kind, *, run_as_root=True, **payload):
            nonlocal order
            step = TaskStep.objects.create(
                task=task, kind=kind, order=order, run_as_root=run_as_root, payload=payload,
            )
            order += 1
            return step

        steps = []
        if task.tool is not None:
            steps += [add(kinds.CREATE), add("assign"), add(kinds.INSTALL)]
            benchmarks = Benchmark.objects.filter(
                category=task.tool.category, published=True,
            ).order_by("name")
            for b in benchmarks:
                steps.append(add(kinds.RUN_BENCHMARK, benchmark_id=str(b.id)))
            steps.append(add(SHUTDOWN_KIND))
        else:
            steps += [add(kinds.CREATE), add("assign"),
                      add(kinds.RUN_BENCHMARK, benchmark_id=str(task.benchmark.id)),
                      add(SHUTDOWN_KIND)]
        return steps

    # (3) Node scripts + I/O contract -------------------------------------
    def script_root(self) -> str:
        return os.path.join(os.path.dirname(__file__), "scripts")

    # (4) Result parsing → normalized records (per category) --------------
    def parse_results(self, run, artifacts_dir: str) -> list:
        category = run.tool.category.name if run.tool else "default"
        return get_category_spec(category).parse(artifacts_dir)

    # (5) Scoring (category-aware) ----------------------------------------
    def score(self, track) -> Scoreboard:
        from collections import defaultdict

        from comp_eval_platform.core.models import Result

        benchmark_ids = track.benchmarks.values_list("id", flat=True)
        agg = defaultdict(lambda: {"solved": 0, "time": 0.0})
        for r in Result.objects.filter(benchmark_id__in=benchmark_ids).select_related("tool", "category"):
            key = (r.tool.name, r.category.name)
            row = agg[key]
            row["tool"], row["category"] = r.tool.name, r.category.name
            if r.result and r.result.lower() not in ("unknown", "error", "timeout", "falsified"):
                row["solved"] += 1
            row["time"] += r.time or 0.0
        return Scoreboard(
            columns=["tool", "category", "solved", "time"],
            rows=sorted(agg.values(), key=lambda x: (x["category"], -x["solved"], x["time"])),
        )

    # (6) Presentation / export -------------------------------------------
    def presentation(self) -> Presentation:
        return Presentation(
            result_columns=["instance", "result", "time"],
            submission_fields=[{"name": "base_image", "type": "text"}],
            score_columns=["tool", "category", "solved", "time"],
        )

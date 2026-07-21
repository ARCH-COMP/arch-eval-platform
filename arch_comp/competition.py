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
from comp_eval_platform.results import Branding, Landing, Presentation, Scoreboard

from . import kinds
from .categories import get_category_spec
from .guides import benchmark_guide, toolkit_guide


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

    def ensure_categories(self) -> None:
        """Seed ARCH's fixed category axis (AFF/NLN/AINNCS) so it's selectable on the
        benchmark form before any load. Idempotent."""
        from .categories import ensure_categories

        ensure_categories()

    def load_benchmarks(self, *, category_name, repository, ref, owner) -> list:
        """Fan a category's central ``instances.csv`` (at ``repository@ref``) into one
        Benchmark per distinct benchmark, each owning its instances."""
        from .benchmarks import load_benchmarks_from_repo
        from .categories import ensure_categories

        cats = ensure_categories()
        if category_name not in cats:
            raise ValidationError(
                f"Unknown ARCH category {category_name!r}; expected one of {sorted(cats)}."
            )
        return load_benchmarks_from_repo(
            category=cats[category_name], repository=repository, ref=ref, owner=owner,
        )

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
            )
            # A tool enters the subset of its category's benchmarks it opted into
            # (tool.extra["benchmarks"] = list of ids); absent selection = enter all.
            selected = task.tool.extra.get("benchmarks")
            if selected:
                benchmarks = benchmarks.filter(id__in=selected)
            for b in benchmarks.order_by("name"):
                steps.append(add(kinds.RUN_BENCHMARK, benchmark_id=str(b.id)))
            steps.append(add(SHUTDOWN_KIND))
        else:
            # A benchmark submission loads a whole category from one central repo. The
            # clone + read happens on a worker (it may grow to do more than parse a CSV),
            # then LOAD fans instances.csv into this category's benchmarks.
            extra = task.extra or {}
            steps += [add(kinds.CREATE), add("assign"),
                      add(kinds.LOAD, category_id=str(task.category_id),
                          repository=extra.get("repository", ""), hash=extra.get("hash", "")),
                      add(SHUTDOWN_KIND)]
        return steps

    # (3) Node scripts + I/O contract -------------------------------------
    def script_root(self) -> str:
        return os.path.join(os.path.dirname(__file__), "scripts")

    def assets_dir(self) -> str:
        return os.path.join(os.path.dirname(__file__), "assets")

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
            branding=Branding(
                # Gradient's leading color, so all primary accents match the navbar.
                primary_color="#2563eb",
                # Blue -> turquoise navbar gradient (teal end kept deep enough for
                # legible white nav text).
                navbar_gradient="linear-gradient(135deg, #2563eb 0%, #0d9488 100%)",
                # Reachable-set figure (5-dim linear example) whose sets are filled
                # with the navbar's blue->turquoise gradient; square, no axis/legend.
                hero_image="/api/competition/assets/hero.svg",
                hero_max_width=312,  # ~90% of VNN's rendered hero height (the tight-cropped plot has no padding of its own)
                favicon="/api/competition/assets/favicon.png",  # the gradient swirl on VNN's grey
            ),
            landing=Landing(
                tagline="ARCH-COMP is a friendly competition for verifying continuous and hybrid "
                        "systems across categories, including systems controlled by neural networks.",
                links=[
                    {"label": "Main Website", "url": "https://arch-comp.github.io/"},
                    {"label": "GitHub", "url": "https://github.com/ARCH-COMP"},
                ],
                contacts=["nico.holzinger@tum.de", "tobias.ladner@tum.de"],
                related={
                    "text": "Interested in verifying standalone neural networks? Check out VNN-COMP!",
                    "label": "Visit VNN-COMP",
                    "url": "https://vnn-comp.github.io/",
                },
            ),
            guides={"toolkit": toolkit_guide(), "benchmark": benchmark_guide()},
        )

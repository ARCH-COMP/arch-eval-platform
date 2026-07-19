"""The how-to copy for ARCH-COMP's two submission pages.

Kept out of ``competition.py``, which is the seam wiring rather than prose. The
shell renders these; it knows nothing about categories, instances.csv, or our
scripts. The toolkit pipeline below stays in step with
``ArchCompetition.build_steps`` — the steps a submitter watches on the detail page,
under the same names.
"""
from comp_eval_platform.results import Guide

TOOL_SKELETON = "https://github.com/ARCH-COMP/example_toolkit"
BENCHMARK_SKELETON = "https://github.com/ARCH-COMP/example_benchmark"

# A tool's results file for an AINNCS instance: the verdict plus the CORA breakdown.
_RESULTS_FILE = """result,time_random,time_violation,time_reachable,time_verification
verified,0.10,0.20,0.30,0.60"""

_INSTANCES_CSV = """benchmark,instance
TORA,reach
TORA,remain
VCAS,worst-19.5"""


def toolkit_guide() -> Guide:
    return Guide(
        intro="How a tool submission is installed and run. To submit one, or to look at "
              "submissions that already ran, use the submissions page.",
        pipeline=[
            {
                "title": "Create submission",
                "details": [
                    "The submission is recorded with what you chose on the form: the repository "
                    "and commit, the Docker base image, the category you enter, and the benchmarks "
                    "of that category you run against. Nothing runs on a worker yet, so this step "
                    "passes immediately.",
                    "That record fixes everything the pipeline does afterwards, which is what makes "
                    "a run reproducible — the commit is resolved and stored even if you submitted a "
                    "branch rather than a hash.",
                ],
            },
            {
                "title": "Assign worker",
                "details": [
                    "The task waits for a worker and attaches it — an AWS instance or a Docker "
                    "container, depending on how the deployment is configured. Every later step "
                    "reaches the worker over SSH either way.",
                    "This is the queueing stage you see before any repository work starts.",
                ],
            },
            {
                "title": "Install tool",
                "details": [
                    "Your repository is cloned at the submitted commit into the base image you "
                    "named, and `install_tool.sh v1` runs to install the tool, its dependencies, "
                    "and to activate any licence.",
                    "Installs are retried rather than failed outright, since a network hiccup is "
                    "not a broken submission.",
                ],
            },
            {
                "title": "Run benchmark",
                "details": [
                    "One step per selected benchmark, so a benchmark that fails does not take the "
                    "others with it. For each instance the worker runs `prepare_instance.sh v1 "
                    "<category> <benchmark> <instance>` and then `run_instance.sh v1 <category> "
                    "<benchmark> <instance> <out>` — every column of the instance's `instances.csv` "
                    "row, in file order, with the results file appended.",
                    "The harness owns timing: it measures wall-clock time and enforces the "
                    "per-instance timeout (the `timeout` column in `instances.csv`, if the category "
                    "sets one; otherwise the run is uncapped). A nonzero exit from "
                    "`prepare_instance.sh` skips that instance.",
                    "Each instance's verdict and its measured time land in a `results.csv` you can "
                    "read on the submission page while it fills up.",
                ],
            },
            {
                "title": "Shutdown",
                "details": [
                    "The worker is terminated once every benchmark has run. The submission page "
                    "stays available afterwards, so the logs and results can be read later — but "
                    "the worker itself is gone.",
                ],
            },
        ],
        sections=[
            {
                "heading": "What your repository must contain",
                "blocks": [
                    {"type": "text", "text":
                        f"The [tool skeleton repository]({TOOL_SKELETON}) is the minimal layout the "
                        "submission system runs. Its scripts have their argument parsing in place "
                        "and `TODO`s where your logic goes, and they run end-to-end as-is (a 1 s "
                        "stand-in run that writes a valid `unknown` result), so you can use it as a "
                        "test tool before filling it in."},
                    {"type": "bullets", "items": [
                        "`install_tool.sh` — installs the tool, once per worker. Called as "
                        "`install_tool.sh v1`; the argument is the interface version.",
                        "`prepare_instance.sh` — called before each instance as `prepare_instance.sh "
                        "v1 <category> <benchmark> <instance>` (plus any further `instances.csv` "
                        "columns, in order). A nonzero exit skips the instance.",
                        "`run_instance.sh` — runs one instance as `run_instance.sh v1 <category> "
                        "<benchmark> <instance> <out>` (further columns before `<out>`, which is "
                        "always the last argument) and writes its verdict to `<out>`.",
                    ]},
                    {"type": "note", "text":
                        "The interface version is the first argument and the category the second, so "
                        "one repository can serve several categories, and the harness — not your "
                        "script — measures the time and enforces the timeout."},
                ],
            },
            {
                "heading": "Reporting results",
                "blocks": [
                    {"type": "text", "text":
                        "`run_instance.sh` writes its results file as a header row plus one data "
                        "row. It must contain a `result` column (`verified`, `falsified`, "
                        "`unknown`, or `error`). A category may read extra self-reported columns: "
                        "AINNCS reads the CORA timing breakdown."},
                    {"type": "code", "code": _RESULTS_FILE},
                    {"type": "note", "text":
                        "The canonical `time` on the scoreboard is the harness wall-clock, not a "
                        "self-reported number; the breakdown is recorded alongside it as extra "
                        "columns."},
                ],
            },
            {
                "heading": "Categories",
                "blocks": [
                    {"type": "text", "text":
                        "Each tool enters one category (AFF, NLN, AINNCS, …) and runs on the "
                        "benchmarks of that category you select — unlike a competition where every "
                        "tool runs everything. The category name is passed to every script, so a "
                        "single repository can target more than one."},
                ],
            },
        ],
    )


def benchmark_guide() -> Guide:
    return Guide(
        intro="How a category's benchmarks are provided. ARCH-COMP uses one repository per "
              "category — not one per benchmark — with a single `instances.csv` over all of them.",
        pipeline=[
            {
                "title": "Provide the source",
                "details": [
                    "You give the category, the benchmarks repository, and a commit hash. That is "
                    "the whole submission: the benchmarks themselves live in the repository.",
                ],
            },
            {
                "title": "Load instances.csv",
                "details": [
                    "The platform reads `instances.csv` at that commit — the one file that lists "
                    "every benchmark and instance in the category.",
                ],
            },
            {
                "title": "Create benchmarks",
                "details": [
                    "The rows are fanned out into one benchmark per distinct `benchmark` value, "
                    "each owning its instances. Loading a newer commit for the same category "
                    "replaces them, so the set stays in step with the repository.",
                ],
            },
            {
                "title": "Available to tools",
                "details": [
                    "The loaded benchmarks become selectable when a tool is submitted in that "
                    "category, and organizers can group them into evaluation tracks.",
                ],
            },
        ],
        sections=[
            {
                "heading": "What your repository must contain",
                "blocks": [
                    {"type": "text", "text":
                        f"The [benchmark skeleton repository]({BENCHMARK_SKELETON}) is the minimal "
                        "layout the loader reads. At its core is `instances.csv`, one row per "
                        "instance, with `benchmark` and `instance` as the first two columns:"},
                    {"type": "code", "code": _INSTANCES_CSV},
                    {"type": "bullets", "items": [
                        "`benchmark` — groups instances into a benchmark, the unit a tool selects.",
                        "`instance` — the case within that benchmark.",
                        "Any further columns are passed, in file order, to the tool's "
                        "`prepare_instance.sh` / `run_instance.sh`.",
                        "`timeout` (optional column) — a per-instance wall-clock cap in seconds, "
                        "enforced by the harness. Omit the column to leave instances uncapped.",
                    ]},
                    {"type": "note", "text":
                        "The networks, dynamics, and specification files your benchmarks reference "
                        "live in the same repository; the tool's scripts locate them by the "
                        "`benchmark` and `instance` names. The layout is category-specific."},
                ],
            },
        ],
    )

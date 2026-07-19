"""ARCH-COMP plugin: the six seams + the per-category axis (ACTIVE_COMPETITION=arch)."""
import uuid

import pytest

pytestmark = pytest.mark.django_db


def _user():
    from comp_eval_platform.core.models import User

    return User.objects.create_user(email=f"{uuid.uuid4().hex[:8]}@x.test", password="pw", enabled=True)


def test_active_competition_is_arch():
    from comp_eval_platform.competitions import get_competition

    assert get_competition().name == "arch"


def test_validate_tool_requires_base_image():
    from django.core.exceptions import ValidationError

    from comp_eval_platform.competitions import get_competition
    from comp_eval_platform.core.models import Category, Tool

    comp = get_competition()
    cat = Category.objects.create(name="AINNCS")
    bad = Tool.objects.create(owner=_user(), category=cat, name="t", base_image="")
    with pytest.raises(ValidationError):
        comp.validate_submission(bad)
    ok = Tool.objects.create(owner=_user(), category=cat, name="t2", base_image="ubuntu:22.04")
    comp.validate_submission(ok)


def test_build_steps_graph():
    from comp_eval_platform.competitions import get_competition
    from comp_eval_platform.core.models import Benchmark, Category, Task, Tool

    from arch_comp import kinds

    cat = Category.objects.create(name="AINNCS")
    tool = Tool.objects.create(owner=_user(), category=cat, name="cora", base_image="cora:latest")
    Benchmark.objects.create(owner=_user(), category=cat, name="ACC", published=True)
    Benchmark.objects.create(owner=_user(), category=cat, name="Airplane", published=True)

    task = Task.objects.create(owner=tool.owner, tool=tool)
    get_competition().build_steps(task)

    assert list(task.step_set.order_by("order").values_list("kind", flat=True)) == [
        kinds.CREATE, "assign", kinds.INSTALL,
        kinds.RUN_BENCHMARK, kinds.RUN_BENCHMARK,
        "shutdown",
    ]


def test_ensure_categories_seeds_the_fixed_axis():
    """The benchmark form calls this so ARCH's categories are selectable before any load."""
    from comp_eval_platform.competitions import get_competition
    from comp_eval_platform.core.models import Category

    assert not Category.objects.exists()
    get_competition().ensure_categories()
    assert set(Category.objects.values_list("name", flat=True)) == {"AFF", "NLN", "AINNCS"}
    get_competition().ensure_categories()  # idempotent
    assert Category.objects.count() == 3


def test_build_steps_category_load():
    """A benchmark submission is a per-category load: no benchmark name, a worker step
    that carries the repo/hash/category so the node clone + CSV read can run there."""
    from comp_eval_platform.competitions import get_competition
    from comp_eval_platform.core.models import Category, Task

    from arch_comp import kinds

    cat = Category.objects.create(name="AINNCS")
    task = Task.objects.create(owner=_user(), category=cat,
                               extra={"repository": "https://x/r", "hash": "abc"})
    get_competition().build_steps(task)

    assert list(task.step_set.order_by("order").values_list("kind", flat=True)) == [
        kinds.CREATE, "assign", kinds.LOAD, "shutdown",
    ]
    load = task.step_set.get(kind=kinds.LOAD)
    assert load.payload == {"category_id": str(cat.id), "repository": "https://x/r", "hash": "abc"}


def test_load_benchmarks_overwrite_prunes_dropped():
    """Re-loading a category mirrors the CSV: a benchmark dropped from it is removed."""
    from arch_comp.benchmarks import load_benchmarks_from_csv
    from comp_eval_platform.core.models import Benchmark, Category

    cat = Category.objects.create(name="AINNCS")
    owner = _user()
    load_benchmarks_from_csv(category=cat, repository="r", ref="1", owner=owner,
                             csv_text="benchmark,instance\nACC,a1\nTORA,t1\n")
    assert set(Benchmark.objects.filter(category=cat).values_list("name", flat=True)) == {"ACC", "TORA"}

    load_benchmarks_from_csv(category=cat, repository="r", ref="2", owner=owner,
                             csv_text="benchmark,instance\nACC,a1\nACC,a2\n")
    assert set(Benchmark.objects.filter(category=cat).values_list("name", flat=True)) == {"ACC"}
    assert Benchmark.objects.get(category=cat, name="ACC").instances.count() == 2


def test_load_handler_loads_category_from_node(monkeypatch):
    """The load step reads instances.csv back off the node and records the exact sha."""
    import comp_eval_platform.compute.shell as shell
    from comp_eval_platform.core.models import Benchmark, Category, Task, TaskStep

    from arch_comp import kinds
    from arch_comp import steps as arch_steps

    cat = Category.objects.create(name="AINNCS")
    task = Task.objects.create(owner=_user(), category=cat, extra={"repository": "r", "hash": ""})
    step = TaskStep.objects.create(task=task, kind=kinds.LOAD, order=0,
                                   payload={"category_id": str(cat.id), "repository": "r", "hash": ""})

    monkeypatch.setattr(arch_steps, "_node_ip", lambda t: "1.2.3.4")
    monkeypatch.setattr(shell, "node_exec",
                        lambda ip, cmd, **k: "benchmark,instance\nACC,a1\n" if "cat " in cmd else "deadbeef")

    step.handler.on_marked_done()

    b = Benchmark.objects.get(category=cat, name="ACC")
    assert b.published and b.hash == "deadbeef"  # sha from the node, not the empty submitted hash


def test_run_handler_parses_and_stores_results(monkeypatch):
    """The run step reads the node's harness results.csv back and stores per-instance
    Results, parsed by the tool's category (AINNCS keeps the CORA breakdown as extra)."""
    import comp_eval_platform.compute.shell as shell
    from comp_eval_platform.core.models import (
        Benchmark, Category, Instance, Result, Task, TaskStep, Tool,
    )
    from comp_eval_platform.core.steps import StepHandler

    from arch_comp import kinds

    cat = Category.objects.create(name="AINNCS")
    tool = Tool.objects.create(owner=_user(), category=cat, name="cora", base_image="cora")
    b = Benchmark.objects.create(owner=_user(), category=cat, name="ACC", published=True)
    Instance.objects.create(benchmark=b, name="acc_1", spec={}, order=0)
    task = Task.objects.create(owner=tool.owner, tool=tool)
    step = TaskStep.objects.create(task=task, kind=kinds.RUN_BENCHMARK, order=0,
                                   payload={"benchmark_id": str(b.id)})

    # collect_results (core) reads the node over self.node_ip; give it one.
    monkeypatch.setattr(StepHandler, "node_ip", property(lambda self: "1.2.3.4"))
    monkeypatch.setattr(shell, "node_exec", lambda ip, cmd, **k:
                        "benchmark,instance,time_verification,prepare_time,result,time\n"
                        "ACC,acc_1,0.42,0.01,verified,0.85\n")

    step.handler.on_marked_done()

    r = Result.objects.get(task=task, benchmark=b)
    assert r.result == "verified" and r.time == 0.85
    assert r.instance.name == "acc_1"
    assert r.extra.get("time_verification") == 0.42  # CORA breakdown kept as extra


def test_overview_labels_category_task_by_category():
    """A per-category benchmark task shows its category (not a name) + repo on the overview."""
    from comp_eval_platform.core.models import Category, Task
    from comp_eval_platform.core.serializers import TaskListSerializer

    cat = Category.objects.create(name="AINNCS")
    task = Task.objects.create(owner=_user(), category=cat, extra={"repository": "https://x/r"})
    data = TaskListSerializer(task).data
    assert data["name"] == "AINNCS"
    assert data["repository"] == "https://x/r"


def test_build_steps_respects_selected_benchmarks():
    """A tool runs only the benchmarks it opted into (tool.extra['benchmarks'])."""
    from comp_eval_platform.competitions import get_competition
    from comp_eval_platform.core.models import Benchmark, Category, Task, Tool

    from arch_comp import kinds

    cat = Category.objects.create(name="AINNCS")
    acc = Benchmark.objects.create(owner=_user(), category=cat, name="ACC", published=True)
    Benchmark.objects.create(owner=_user(), category=cat, name="Airplane", published=True)
    tora = Benchmark.objects.create(owner=_user(), category=cat, name="TORA", published=True)

    tool = Tool.objects.create(owner=_user(), category=cat, name="cora", base_image="cora",
                               extra={"benchmarks": [str(acc.id), str(tora.id)]})
    task = Task.objects.create(owner=tool.owner, tool=tool)
    get_competition().build_steps(task)

    run_steps = task.step_set.filter(kind=kinds.RUN_BENCHMARK).order_by("order")
    assert [s.payload["benchmark_id"] for s in run_steps] == [str(acc.id), str(tora.id)]


def test_category_registry_has_specialized_and_default():
    from arch_comp.categories import get_category_spec, registered_categories

    assert set(registered_categories()) >= {"default", "AINNCS"}
    # Unknown category falls back to default.
    assert get_category_spec("NLN").category_name == "default"
    assert get_category_spec("AINNCS").category_name == "AINNCS"


def test_parse_results_dispatches_per_category(tmp_path):
    """AINNCS parses the CORA timing breakdown into extra; default parses result+time."""
    from comp_eval_platform.competitions import get_competition
    from comp_eval_platform.core.models import Category, Task, Tool

    comp = get_competition()

    # AINNCS run
    ainncs = Category.objects.create(name="AINNCS")
    tool_a = Tool.objects.create(owner=_user(), category=ainncs, name="cora", base_image="cora")
    task_a = Task.objects.create(owner=tool_a.owner, tool=tool_a)
    # Harness results.csv: canonical wall-clock `time` plus the tool's CORA breakdown.
    (tmp_path / "results.csv").write_text(
        "benchmark,instance,time_random,time_violation,time_reachable,time_verification,prepare_time,result,time\n"
        "ACC,acc_1,0.1,0.2,0.3,0.6,0.05,verified,0.85\n"
    )
    recs = comp.parse_results(task_a, str(tmp_path))
    assert len(recs) == 1
    assert recs[0].instance == "acc_1" and recs[0].result == "verified"
    assert recs[0].time == 0.85  # harness wall-clock, not the self-reported breakdown
    assert recs[0].extra == {"time_random": 0.1, "time_violation": 0.2,
                             "time_reachable": 0.3, "time_verification": 0.6}

    # default category run
    other = Category.objects.create(name="NLN")
    tool_b = Tool.objects.create(owner=_user(), category=other, name="tool", base_image="img")
    task_b = Task.objects.create(owner=tool_b.owner, tool=tool_b)
    d2 = tmp_path / "d2"
    d2.mkdir()
    (d2 / "results.csv").write_text("instance,result,time\nx,holds,1.2\n")
    recs2 = comp.parse_results(task_b, str(d2))
    assert recs2[0].extra == {} and recs2[0].time == 1.2


def test_score_is_category_aware():
    from comp_eval_platform.competitions import get_competition
    from comp_eval_platform.core.models import Benchmark, Category, Result, Task, Tool, Track

    u = _user()
    cat = Category.objects.create(name="AINNCS")
    tool = Tool.objects.create(owner=u, category=cat, name="cora", base_image="cora")
    bench = Benchmark.objects.create(owner=u, category=cat, name="ACC", published=True)
    task = Task.objects.create(owner=u, tool=tool)
    Result.objects.create(task=task, tool=tool, benchmark=bench, category=cat, result="verified", time=1.0)
    Result.objects.create(task=task, tool=tool, benchmark=bench, category=cat, result="unknown", time=2.0)

    track = Track.objects.create(name="main")
    track.benchmarks.add(bench)

    board = get_competition().score(track)
    assert board.columns == ["tool", "category", "solved", "time"]
    assert board.rows == [{"tool": "cora", "category": "AINNCS", "solved": 1, "time": 3.0}]


def test_guides_cover_both_submission_pages():
    """The shell asks for these two by name and falls back to neutral copy without them,
    which would quietly drop every ARCH-specific instruction from the info pages."""
    from comp_eval_platform.competitions import get_competition

    guides = get_competition().presentation().guides
    assert set(guides) == {"toolkit", "benchmark"}
    for g in guides.values():
        assert g.intro and g.pipeline and g.sections
        assert all(s["title"] and s["details"] for s in g.pipeline)


def test_guides_link_the_github_skeleton_repos():
    """The guides point submitters at the example repos on GitHub, not at zip assets."""
    from comp_eval_platform.competitions import get_competition

    prose = repr(get_competition().presentation().guides)
    assert "https://github.com/ARCH-COMP/example_toolkit" in prose
    assert "https://github.com/ARCH-COMP/example_benchmark" in prose

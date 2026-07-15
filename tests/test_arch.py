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
    (tmp_path / "results.csv").write_text(
        "instance,result,time_random,time_violation,time_reachable,time_verification\n"
        "acc_1,verified,0.1,0.2,0.3,0.6\n"
    )
    recs = comp.parse_results(task_a, str(tmp_path))
    assert len(recs) == 1
    assert recs[0].instance == "acc_1" and recs[0].result == "verified"
    assert recs[0].time == 0.6
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

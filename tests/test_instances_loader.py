"""Loading an ARCH category's benchmarks from a central instances.csv."""
import uuid

import pytest
from django.core.exceptions import ValidationError

pytestmark = pytest.mark.django_db

# The real AINNCS instances.csv (github.com/ARCH-COMP/archcomp2026_benchmarks_ainncs).
AINNCS_CSV = """benchmark,instance
Unicycle,reach
ACC,safe-distance
TORA,remain
TORA,reach-tanh
TORA,reach-sigmoid
Single Pendulum,reach
Double Pendulum,less-robust
Double Pendulum,more-robust
Airplane,continuous
VCAS,middle-19.5
VCAS,middle-22.5
VCAS,middle-25.5
VCAS,middle-28.5
VCAS,worst-19.5
VCAS,worst-22.5
VCAS,worst-25.5
VCAS,worst-28.5
Attitude Control,avoid
QUAD,reach
Docking,constraint
NAV,standard
NAV,robust
CartPole,reach
"""


def _user():
    from comp_eval_platform.core.models import User

    return User.objects.create_user(email=f"{uuid.uuid4().hex[:8]}@x.test", password="pw", enabled=True)


def test_parse_groups_rows_by_benchmark():
    from arch_comp.benchmarks import group_by_benchmark, parse_instances_csv

    header, rows = parse_instances_csv(AINNCS_CSV)
    assert header == ["benchmark", "instance"]
    assert len(rows) == 23
    groups = group_by_benchmark(rows)
    assert len(groups) == 12  # distinct benchmarks (23 instances)
    assert len(groups["VCAS"]) == 8
    assert len(groups["TORA"]) == 3
    assert len(groups["CartPole"]) == 1
    # first-seen order preserved
    assert list(groups)[0] == "Unicycle"
    assert [r["instance"] for r in groups["TORA"]] == ["remain", "reach-tanh", "reach-sigmoid"]


def test_parse_requires_benchmark_and_instance_columns():
    from arch_comp.benchmarks import parse_instances_csv

    with pytest.raises(ValidationError):
        parse_instances_csv("benchmark,foo\nACC,x\n")
    with pytest.raises(ValidationError):
        parse_instances_csv("")


def test_load_from_csv_creates_benchmarks_and_ordered_instances():
    from arch_comp.categories import ensure_categories
    from arch_comp.benchmarks import load_benchmarks_from_csv
    from comp_eval_platform.core.models import Instance

    cat = ensure_categories()["AINNCS"]
    owner = _user()
    benchmarks = load_benchmarks_from_csv(
        category=cat, repository="https://github.com/ARCH-COMP/archcomp2026_benchmarks_ainncs",
        ref="abc123", owner=owner, csv_text=AINNCS_CSV,
    )
    assert len(benchmarks) == 12
    by_name = {b.name: b for b in benchmarks}

    tora = by_name["TORA"]
    assert tora.category == cat and tora.published is True
    assert tora.hash == "abc123"
    assert tora.repository.endswith("archcomp2026_benchmarks_ainncs")
    # Ordered header carried on the benchmark (jsonb-order-safe).
    assert tora.extra["columns"] == ["benchmark", "instance"]

    insts = list(Instance.objects.filter(benchmark=tora).order_by("order"))
    assert [i.name for i in insts] == ["remain", "reach-tanh", "reach-sigmoid"]
    assert insts[0].spec == {"benchmark": "TORA", "instance": "remain"}
    # Positional args a harness would pass, reconstructed via the ordered header.
    assert [insts[0].spec[c] for c in tora.extra["columns"]] == ["TORA", "remain"]


def test_timeout_column_is_optional():
    from arch_comp.categories import ensure_categories
    from arch_comp.benchmarks import load_benchmarks_from_csv
    from comp_eval_platform.core.models import Instance

    cat = ensure_categories()["AINNCS"]
    with_to = "benchmark,instance,timeout\nACC,safe-distance,300\n"
    (bench,) = load_benchmarks_from_csv(
        category=cat, repository="r", ref="h", owner=_user(), csv_text=with_to,
    )
    inst = Instance.objects.get(benchmark=bench)
    assert inst.spec.get("timeout") == "300"
    assert bench.extra["columns"] == ["benchmark", "instance", "timeout"]

    # Absent timeout column -> no per-instance cap.
    cat2 = ensure_categories()["NLN"]
    (bench2,) = load_benchmarks_from_csv(
        category=cat2, repository="r", ref="h", owner=_user(),
        csv_text="benchmark,instance\nX,y\n",
    )
    assert Instance.objects.get(benchmark=bench2).spec.get("timeout") is None


def test_reload_replaces_instances():
    from arch_comp.categories import ensure_categories
    from arch_comp.benchmarks import load_benchmarks_from_csv
    from comp_eval_platform.core.models import Benchmark, Instance

    cat = ensure_categories()["AINNCS"]
    owner = _user()
    load_benchmarks_from_csv(category=cat, repository="r", ref="v1", owner=owner,
                             csv_text="benchmark,instance\nACC,a\nACC,b\n")
    load_benchmarks_from_csv(category=cat, repository="r", ref="v2", owner=owner,
                             csv_text="benchmark,instance\nACC,a\n")

    acc = Benchmark.objects.get(category=cat, name="ACC")
    assert acc.hash == "v2"
    assert [i.name for i in Instance.objects.filter(benchmark=acc)] == ["a"]


def test_ensure_categories_seeds_arch_axis():
    from arch_comp.categories import ARCH_CATEGORIES, ensure_categories
    from comp_eval_platform.core.models import Category

    cats = ensure_categories()
    assert set(cats) == set(ARCH_CATEGORIES) == {"AFF", "NLN", "AINNCS"}
    # AINNCS seeds its CORA-style result columns; a plain category gets the default.
    assert Category.objects.get(name="AINNCS").result_fields == [
        "result", "time_random", "time_violation", "time_reachable", "time_verification",
    ]
    assert Category.objects.get(name="NLN").result_fields == ["result", "time"]


def test_competition_rejects_unknown_category():
    from comp_eval_platform.competitions import get_competition

    with pytest.raises(ValidationError):
        get_competition().load_benchmarks(
            category_name="NOPE", repository="r", ref="h", owner=_user(),
        )

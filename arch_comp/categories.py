"""Per-category specialization — the ARCH-specific axis.

Each ARCH category (AINNCS, AFF, NLN, …) has its own result columns and its own
way of turning a run's node output into normalized records. This generalizes the
old ARCH ``parser_factory[category][tool]`` into a registry of ``CategorySpec``s,
which ``ArchCompetition`` dispatches to based on a submission's category. VNN never
needed this (one implicit category); it is the seam that makes ARCH's many
heterogeneous categories fit the same engine.
"""
import csv
import os

from comp_eval_platform.results import ResultRecord

#: ARCH-COMP's fixed category axis. Every tool/benchmark targets exactly one of
#: these — unlike VNN's tracks, where every tool runs all of them. This is the
#: single central list; add a category here (and, if it has bespoke result columns,
#: a CategorySpec below) to make it selectable.
ARCH_CATEGORIES = ["AFF", "NLN", "AINNCS"]

_CATEGORY_SPECS: dict = {}


def ensure_categories() -> dict:
    """Get-or-create a ``Category`` row for each name in ``ARCH_CATEGORIES``, seeding
    its ``result_fields`` from the matching spec (default columns for those without a
    bespoke spec). Idempotent. Returns {name: Category}."""
    from comp_eval_platform.core.models import Category

    cats = {}
    for name in ARCH_CATEGORIES:
        spec = get_category_spec(name)
        cats[name], _ = Category.objects.get_or_create(
            name=name, defaults={"result_fields": list(spec.result_fields)},
        )
    return cats


def register_category(cls):
    _CATEGORY_SPECS[cls.category_name] = cls
    return cls


def get_category_spec(name: str) -> "CategorySpec":
    """The spec for ``name``, falling back to the generic default."""
    return _CATEGORY_SPECS.get(name, _CATEGORY_SPECS["default"])()


def registered_categories() -> dict:
    return dict(_CATEGORY_SPECS)


def _f(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


class CategorySpec:
    """Base: read ``results.csv`` (with a header) into normalized records. Override
    ``result_fields`` / ``_record`` for a category's extra columns."""

    category_name = "default"
    #: Extra normalized columns this category reports (presentation hint).
    result_fields = ["result", "time"]

    def parse(self, artifacts_dir: str) -> list:
        path = os.path.join(artifacts_dir, "results.csv")
        records = []
        if not os.path.exists(path):
            return records
        with open(path, newline="") as fh:
            for row in csv.DictReader(fh):
                records.append(self._record(row))
        return records

    def _record(self, row: dict) -> ResultRecord:
        return ResultRecord(
            instance=(row.get("instance") or "").strip(),
            result=(row.get("result") or "").strip(),
            time=_f(row.get("time")),
        )


@register_category
class DefaultCategory(CategorySpec):
    category_name = "default"


@register_category
class AinncsCategory(CategorySpec):
    """AINNCS reports the CORA-style timing breakdown (the fields the old
    cora_parser recovered), now per instance."""

    category_name = "AINNCS"
    result_fields = ["result", "time_random", "time_violation", "time_reachable", "time_verification"]

    def _record(self, row: dict) -> ResultRecord:
        # The harness owns the canonical wall-clock ``time``; the tool's CORA timing
        # breakdown is self-reported and rides along as ``extra``.
        breakdown = {k: _f(row.get(k)) for k in self.result_fields if k != "result"}
        return ResultRecord(
            instance=(row.get("instance") or "").strip(),
            result=(row.get("result") or "").strip(),
            time=_f(row.get("time")),
            extra=breakdown,
        )

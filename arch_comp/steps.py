"""ARCH-COMP step handlers. Same structured shape as VNN (fire a node script; the
node curls back /update/<id>/…); the ARCH-specific parsing on completion dispatches
per category via the competition's ``parse_results``."""
from comp_eval_platform.compute.shell import _ping
from comp_eval_platform.core.steps import StepHandler, register_step_handler

from . import kinds


def _node_ip(task):
    node = task.node
    return node.ip if node is not None else None


@register_step_handler
class ArchCreateHandler(StepHandler):
    kind = kinds.CREATE

    def execute(self):
        self.task.step_succeeded(check_status=False)

    def status_check(self):
        return


@register_step_handler
class ArchInstallHandler(StepHandler):
    """Clone the tool into its base image, run install + license activation."""

    kind = kinds.INSTALL

    def execute(self):
        ip = _node_ip(self.task)
        if ip is None:
            self.task.step_failed(check_status=False)
            return
        _ping("arch", "install_tool.sh", {
            "benchmark_ip": ip,
            "task_id": str(self.task.id),
            "base_image": self.task.tool.base_image,
            "repository": self.task.tool.repository,
        })

    def retry_until_success(self) -> bool:
        return True


@register_step_handler
class ArchLoadHandler(StepHandler):
    """Load a category's benchmarks from its central repo. The node clones the repo at
    the submitted ref (room to grow into more than a CSV read); on completion we pull
    its ``instances.csv`` back and fan it into this category's benchmarks."""

    kind = kinds.LOAD
    node_log_path = "logs/load.log"  # load_benchmark.sh tees the clone here

    def execute(self):
        ip = _node_ip(self.task)
        if ip is None:
            self.task.step_failed(check_status=False)
            return
        _ping("arch", "load_benchmark.sh", {
            "benchmark_ip": ip,
            "task_id": str(self.task.id),
            "repository": self.step.payload.get("repository", ""),
            "hash": self.step.payload.get("hash", ""),
        })

    def retry_until_success(self) -> bool:
        return True  # clones are flaky (network); retry rather than fail the task

    def on_marked_done(self):
        """Read the cloned ``instances.csv`` off the node and load the category. The
        node is still up (shutdown runs next). Records the exact commit for
        reproducibility when the submission gave no hash."""
        from comp_eval_platform.compute.shell import node_exec
        from comp_eval_platform.core.models import Category

        from .benchmarks import CLONE_DIR, INSTANCES_FILE, load_benchmarks_from_csv

        ip = _node_ip(self.task)
        category = Category.objects.filter(id=self.step.payload.get("category_id")).first()
        if ip is None or category is None:
            return
        csv_text = node_exec(ip, f"cat {CLONE_DIR}/{INSTANCES_FILE} 2>/dev/null")
        if not csv_text.strip():
            self._append_log(f"no {INSTANCES_FILE} found on the node; nothing loaded")
            return
        sha = node_exec(ip, f"git -C {CLONE_DIR} rev-parse HEAD 2>/dev/null").strip()
        benchmarks = load_benchmarks_from_csv(
            category=category, repository=self.step.payload.get("repository", ""),
            ref=sha or self.step.payload.get("hash", ""), owner=self.task.owner, csv_text=csv_text,
        )
        self._append_log(f"loaded {len(benchmarks)} benchmark(s) for category {category.name}")

    def _append_log(self, line: str):
        self.step.set_log(((self.step.logs or "") + f"\n[load] {line}").strip())


@register_step_handler
class ArchRunBenchmarkHandler(StepHandler):
    kind = kinds.RUN_BENCHMARK

    def _benchmark(self):
        from comp_eval_platform.core.models import Benchmark

        return Benchmark.objects.filter(id=self.step.payload.get("benchmark_id")).first()

    def execute(self):
        ip = _node_ip(self.task)
        if ip is None:
            self.task.step_failed(check_status=False)
            return
        b = self._benchmark()
        _ping("arch", "run_benchmark.sh", {
            "benchmark_ip": ip,
            "task_id": str(self.task.id),
            "benchmark_name": b.name if b else "",
        })

    def can_abort_benchmark(self) -> bool:
        return True

    def abort_benchmark(self):
        self.task.step_succeeded(check_status=False)

    def on_marked_done(self):
        from comp_eval_platform.competitions import get_competition
        from comp_eval_platform.core.models import Instance, Result

        b = self._benchmark()
        artifacts = self._fetch_artifacts()
        if b is None or artifacts is None:
            return
        records = get_competition().parse_results(self.task, artifacts)
        instances = {i.name: i for i in Instance.objects.filter(benchmark=b)}
        Result.store(self.task, self.task.tool, b, b.category, records, instances_by_name=instances)

    def _fetch_artifacts(self):
        # Placeholder for SCP-from-node results collection; returns None until wired.
        return None

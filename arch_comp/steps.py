"""ARCH-COMP step handlers. Same structured shape as VNN (fire a node script; the
node curls back /update/<id>/…); the ARCH-specific parsing on completion dispatches
per category via the competition's ``parse_results``."""
from comp_eval_platform.compute.shell import _ping
from comp_eval_platform.core.steps import StepHandler, register_step_handler

from . import kinds


#: ARCH tool-interface version passed as the first arg to a tool's scripts. A tool may
#: pin one via ``tool.extra["version"]``; else the current default.
INTERFACE_VERSION = "v1"


def _node_ip(task):
    node = task.node
    return node.ip if node is not None else None


def _version(tool) -> str:
    return ((tool.extra if tool else {}) or {}).get("version") or INTERFACE_VERSION


@register_step_handler
class ArchCreateHandler(StepHandler):
    kind = kinds.CREATE

    def execute(self):
        self.task.step_succeeded(check_status=False)

    def status_check(self):
        return


@register_step_handler
class ArchInstallHandler(StepHandler):
    """Clone the tool onto the node and run its ``install_tool.sh <version>``."""

    kind = kinds.INSTALL
    node_log_path = "logs/install.log"  # install_tool.sh tees the run here

    def execute(self):
        ip = _node_ip(self.task)
        if ip is None:
            self.task.step_failed(check_status=False)
            return
        tool = self.task.tool
        # Generic install (clone tool + run its install_tool.sh) is a core script; the
        # tool is cloned to /home/ubuntu/tool, where run_benchmark.sh looks for it.
        _ping("node", "install_tool.sh", {
            "benchmark_ip": ip,
            "task_id": str(self.task.id),
            "repository": tool.repository,
            "hash": tool.hash or "",
            "script_dir": tool.script_dir or ".",
            "version": _version(tool),
            "run_as_root": str(self.step.run_as_root).lower(),
            "tool_dir": "tool",
        })

    def retry_until_success(self) -> bool:
        return True  # installs are flaky (network); retry rather than fail the task


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
    """Run one benchmark's instances with the installed tool. The node-side harness
    loops the benchmark's instances (prepare/run_instance per the ARCH contract, timing
    each), writing a results.csv keyed by benchmark id (benchmark names may have spaces).
    On completion the results are read back, parsed per category, and stored."""

    kind = kinds.RUN_BENCHMARK

    def _benchmark(self):
        from comp_eval_platform.core.models import Benchmark

        return Benchmark.objects.filter(id=self.step.payload.get("benchmark_id")).first()

    @property
    def node_log_path(self):
        """run_benchmark.sh tees each benchmark's run to its own log (keyed by id)."""
        b = self._benchmark()
        return f"logs/run_{b.id}.log" if b else None

    def execute(self):
        ip = _node_ip(self.task)
        if ip is None:
            self.task.step_failed(check_status=False)
            return
        b = self._benchmark()
        if b is None:
            self.task.step_succeeded(check_status=False)
            return
        tool = self.task.tool
        _ping("arch", "run_benchmark.sh", {
            "benchmark_ip": ip,
            "task_id": str(self.task.id),
            "benchmark_id": str(b.id),
            "benchmark_name": b.name,
            "category": b.category.name,
            "version": _version(tool),
            "script_dir": (tool.script_dir if tool else ".") or ".",
            "repository": b.repository,
            "hash": b.hash or "",
        })

    def can_abort_benchmark(self) -> bool:
        return True

    def abort_benchmark(self):
        """Stop the node-side run (best-effort) and move on to the next benchmark."""
        from comp_eval_platform.compute.shell import node_exec

        ip = _node_ip(self.task)
        b = self._benchmark()
        if ip is not None and b is not None:
            node_exec(ip, f"tmux kill-session -t run_{b.id} 2>/dev/null; true")
        self.task.step_succeeded(check_status=False)

    def on_marked_done(self):
        """Fetch the node's results.csv, parse per category, and persist Result rows."""
        import shutil

        from comp_eval_platform.competitions import get_competition
        from comp_eval_platform.core.models import Instance, Result

        b = self._benchmark()
        if b is None:
            return
        # Result collection (fetch results.csv → temp dir) is generic core behavior.
        artifacts = self.collect_results(f"/home/ubuntu/logs/results_{b.id}.csv")
        if artifacts is None:
            return
        try:
            records = get_competition().parse_results(self.task, artifacts)
            instances = {i.name: i for i in Instance.objects.filter(benchmark=b)}
            Result.store(self.task, self.task.tool, b, b.category, records, instances_by_name=instances)
        finally:
            shutil.rmtree(artifacts, ignore_errors=True)

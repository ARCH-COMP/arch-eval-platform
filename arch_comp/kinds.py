"""Step kinds this variant contributes (core provides 'assign' and 'shutdown')."""

CREATE = "arch_create"
INSTALL = "arch_install"  # clone tool into its base image, run install + license
RUN_BENCHMARK = "run_benchmark"  # counted by Task.effective_timeout_hours

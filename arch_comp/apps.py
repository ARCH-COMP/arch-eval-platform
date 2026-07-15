from django.apps import AppConfig


class ArchCompConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "arch_comp"
    label = "arch_comp"
    verbose_name = "ARCH-COMP"

    def ready(self):
        from comp_eval_platform.competitions import register

        from . import categories  # noqa: F401  (registers category specs)
        from . import steps  # noqa: F401  (registers step handlers)
        from .competition import ArchCompetition

        register(ArchCompetition)

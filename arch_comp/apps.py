from django.apps import AppConfig


class ArchCompConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "arch_comp"
    label = "arch_comp"
    verbose_name = "ARCH-COMP"

    def ready(self):
        from comp_eval_platform.competitions import register
        from django.urls import include, path
        from comp_eval_platform import urls as root_urls

        from . import categories  # noqa: F401  (registers category specs)
        from . import steps  # noqa: F401  (registers step handlers)
        from .competition import ArchCompetition

        root_urls.urlpatterns.append(path("api/arch/", include("arch_comp.urls")))
        register(ArchCompetition)


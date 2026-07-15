"""ARCH-COMP deployment settings: select the competition + install its plugin."""
from comp_eval_platform.settings import *  # noqa: F401,F403

ACTIVE_COMPETITION = "arch"
INSTALLED_APPS += ["arch_comp"]  # noqa: F405

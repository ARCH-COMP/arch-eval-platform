"""Test settings for the ARCH variant: core's sqlite test settings + this plugin."""
from comp_eval_platform.settings_test import *  # noqa: F401,F403

ACTIVE_COMPETITION = "arch"
INSTALLED_APPS += ["arch_comp"]  # noqa: F405

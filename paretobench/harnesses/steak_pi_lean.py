"""Steak Pi run lean: the steak-pi arm the way `steak-pi run --lean` runs it (Steak Pi 0.28.5 and later).

It adds `--exclude-tools ultraterm_subagents,ultraterm_hub,todo` (dispatch, hub and todo tools off) and sets the
child environment variable STEAK_PI_WORK_RULES_BRIEF=1, which is what `steak-pi run --lean` passes. Before ParetoBench
0.4.0 the arm excluded only `ultraterm_subagents,todo` and set no variable.
"""
from . import steak_pi

name = "steak-pi-lean"
family = "pi"
LEAN = ["--exclude-tools", "ultraterm_subagents,ultraterm_hub,todo"]
LEAN_ENV = {"STEAK_PI_WORK_RULES_BRIEF": "1"}

parse = steak_pi.parse
after_run = steak_pi.after_run
setup_lane = steak_pi.setup_lane
validate = steak_pi.validate


def version(ex):
    return steak_pi.version(ex) + " lean"


def build_command(ex, mcfg, prompt, lane, model_patch=None, extra_patches=()):
    argv, env = steak_pi.build_command(ex, mcfg, prompt, lane, model_patch, extra_patches)
    return argv[:-1] + LEAN + argv[-1:], {**env, **LEAN_ENV}  # the prompt stays last

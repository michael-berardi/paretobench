"""Steak Pi run lean: the steak-pi arm without the dispatch and todo tools."""
from . import steak_pi

name = "steak-pi-lean"
family = "pi"
LEAN = ["--exclude-tools", "ultraterm_subagents,todo"]

parse = steak_pi.parse
after_run = steak_pi.after_run
setup_lane = steak_pi.setup_lane
validate = steak_pi.validate


def version(ex):
    return steak_pi.version(ex) + " lean"


def build_command(ex, mcfg, prompt, lane, model_patch=None, extra_patches=()):
    argv, env = steak_pi.build_command(ex, mcfg, prompt, lane, model_patch, extra_patches)
    return argv[:-1] + LEAN + argv[-1:], env  # the prompt stays last

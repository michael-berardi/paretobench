"""Steak DSH long-work profile: the steak-dsh arm plus the bundle's long.patch.yml."""
import os

from ..config import PBError
from . import steak_dsh

name = "steak-dsh-long"
family = "dsh"

setup_lane = steak_dsh.setup_lane
parse = steak_dsh.parse
after_run = steak_dsh.after_run


def _long(ex):
    p = os.path.join(os.path.dirname(steak_dsh._patch(ex)), "long.patch.yml")
    if not os.path.isfile(p):
        raise PBError("steak-dsh-long-patch-missing",
                      f"{p} (needs a Steak DSH bundle that ships long.patch.yml)")
    return p


def validate(mcfg, ex):
    steak_dsh.validate(mcfg, ex)
    _long(ex)


def version(ex):
    return steak_dsh.version(ex) + " long"


def build_command(ex, mcfg, prompt, lane, model_patch=None, extra_patches=()):
    return steak_dsh.build_command(ex, mcfg, prompt, lane, model_patch,
                                   extra_patches=(_long(ex),) + tuple(extra_patches))

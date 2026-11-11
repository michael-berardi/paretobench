"""Steak DSH: the same stock dsh build plus the Steak DSH bundle patch."""
import json
import os

from ..config import PBError
from . import dsh

name = "steak-dsh"
family = "dsh"

setup_lane = dsh.setup_lane
parse = dsh.parse
after_run = dsh.after_run


def _patch(ex):
    p = ex.get("steak_dsh_patch") or ""
    if not os.path.isfile(p):
        raise PBError("steak-dsh-patch-missing", f"{p or '(not set)'} (set PB_STEAK_DSH_PATCH to the bundle patch)")
    return p


def validate(mcfg, ex):
    dsh.validate(mcfg, ex)
    _patch(ex)
    if os.environ.get("PB_STEAK_DSH_ENV"):
        try:
            env = json.loads(os.environ["PB_STEAK_DSH_ENV"])
            assert isinstance(env, dict) and all(isinstance(v, str) for v in env.values())
        except Exception:
            raise PBError("bad-steak-dsh-env", "PB_STEAK_DSH_ENV must be a JSON object of string values")


def version(ex):
    return f"{dsh.version(ex)} steak-dsh"


def build_command(ex, mcfg, prompt, lane, model_patch=None, extra_patches=()):
    argv, env = dsh.build_command(ex, mcfg, prompt, lane, model_patch,
                                  extra_patches=( _patch(ex),) + tuple(extra_patches))
    if os.environ.get("PB_STEAK_DSH_ENV"):
        env.update(json.loads(os.environ["PB_STEAK_DSH_ENV"]))
    return argv, env

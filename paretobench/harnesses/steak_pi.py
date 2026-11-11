"""Steak Pi: the same raw pi binary and model args as stock pi, but the agent dir
loads the Steak Pi package and extensions are not disabled."""
import json
import os

from ..config import PBError
from . import pi

name = "steak-pi"
family = "pi"
EXTRA_FLAGS = []  # no -ne: the Steak Pi package is loaded through settings.json

parse = pi.parse
after_run = pi.after_run


def setup_lane(ex, mcfg, work, slot, lane_name):
    return pi.make_agent_dir(ex, work, slot, lane_name, packages(ex))


def packages(ex):
    return [ex["steak_pi_package"]]


def _validate_package(ex):
    pkg = ex.get("steak_pi_package") or ""
    if not os.path.isfile(os.path.join(pkg, "package.json")):
        raise PBError("steak-pi-package-missing",
                      f"{pkg or '(not set)'} (set PB_STEAK_PI_PACKAGE to the Steak Pi package directory)")


def validate(mcfg, ex):  # noqa: F811  (pi validation plus the package check)
    pi.validate(mcfg, ex)
    _validate_package(ex)


def version(ex):
    _validate_package(ex)
    v = pi.version(ex)
    try:
        with open(os.path.join(ex["steak_pi_package"], "package.json")) as f:
            pv = json.load(f).get("version", "")
    except (OSError, ValueError):
        pv = ""
    return f"{v} steak-pi {pv}".strip()


def model_args(mcfg):
    # steak_pi_extra holds steak-pi-only flags (e.g. paid-route pinning) so the stock
    # pi arm gets exactly the same model args without flags it does not understand.
    return list(mcfg["pi"]) + list(mcfg.get("steak_pi_extra", []))


def build_command(ex, mcfg, prompt, lane, model_patch=None, extra_patches=()):
    argv = [ex["pi_bin"], "-p", "--mode", "json", "--no-session"] + model_args(mcfg) + [prompt]
    return argv, {"PI_CODING_AGENT_DIR": lane["agent_dir"]}

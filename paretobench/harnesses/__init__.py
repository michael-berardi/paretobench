"""Harness adapters. Each adapter builds the exact command line for one coding-agent
harness, parses its event stream into usage, and never sees an API key: keys are added
to the child environment by the runner only.

Adapter interface (used by paretobench.runner and by the tests):
  validate(mcfg, ex)                     raise PBError before anything runs
  version(ex)                            version string, no model call
  setup_lane(ex, mcfg, work, slot)       per-lane dirs (agent dir / harness home)
  build_command(ex, mcfg, prompt, lane, model_patch=None, extra_patches=())
                                         -> (argv, env_extra) with no key in argv
  parse(rc, out, err, scrub)             -> (usage, text); raises RunFail on failure
  after_run(lane)                        per-run cleanup (e.g. dsh sessions)
"""
import importlib

# Old arm names in legacy steak-dsh bench rows map to canonical harness names.
ARM_MAP = {"dsh": "dsh", "sdsh": "steak-dsh", "sp": "steak-pi", "cc": "claude-code", "pi": "pi"}
_MODULES = {"pi": "pi", "steak-pi": "steak_pi", "claude-code": "claude_code",
            "dsh": "dsh", "steak-dsh": "steak_dsh",
            "steak-pi-lean": "steak_pi_lean", "steak-dsh-long": "steak_dsh_long"}


class RunFail(Exception):
    def __init__(self, msg, out="", err=""):
        super().__init__(msg)
        self.out, self.err = out, err


def get_adapter(name):
    if name not in _MODULES:
        from ..config import PBError
        raise PBError("unknown-harness", f"'{name}' (harnesses: {', '.join(_MODULES)})")
    return importlib.import_module("." + _MODULES[name], __name__)


def events_of(out):
    ev = []
    for line in (out or "").splitlines():
        if line.startswith("{"):
            try:
                import json
                ev.append(json.loads(line))
            except ValueError:
                pass
    return ev


def empty_usage():
    return dict(i=0, cr=0, cw=0, o=0, reasoning=0, turns=0, tools=0)

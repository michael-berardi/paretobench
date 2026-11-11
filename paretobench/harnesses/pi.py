"""Stock Pi: the raw pi binary, no extensions (-ne), an agent dir with no packages."""
import json
import os
import shutil
import subprocess

from ..config import PBError
from . import RunFail, events_of, empty_usage

name = "pi"
family = "pi"
EXTRA_FLAGS = ["-ne"]


def packages(ex):
    return []  # stock: settings.json lists no packages


def validate(mcfg, ex):
    if not ex.get("pi_bin") or not os.path.isfile(ex["pi_bin"]):
        raise PBError("pi-bin-missing", f"{ex.get('pi_bin') or '(not found)'} (set PB_PI_BIN)")
    if not isinstance(mcfg.get("pi"), list):
        raise PBError("harness-unavailable-for-model", "model has no 'pi' model args")
    if not os.path.isfile(os.path.join(ex["pi_agent_dir"], "auth.json")):
        raise PBError("pi-agent-dir-missing", f"{ex['pi_agent_dir']}/auth.json (set PB_PI_AGENT_DIR)")


def version(ex):
    return subprocess.run([ex["pi_bin"], "--version"], capture_output=True, text=True,
                          timeout=60).stdout.strip()


def setup_lane(ex, mcfg, work, slot, lane_name):
    return make_agent_dir(ex, work, slot, lane_name, packages(ex))


def make_agent_dir(ex, work, slot, lane_name, pkgs):
    ad = os.path.join(work, "agents", f"{lane_name}-{slot}")
    if not os.path.isdir(ad):
        os.makedirs(ad)
        shutil.copy(os.path.join(ex["pi_agent_dir"], "auth.json"), ad)
        shutil.copy(os.path.join(ex["pi_agent_dir"], "models.json"), ad)
        with open(os.path.join(ad, "settings.json"), "w") as f:
            json.dump({"quietStartup": True, "packages": list(pkgs)}, f)
    return {"agent_dir": ad}


def model_args(mcfg):
    return list(mcfg["pi"])


def build_command(ex, mcfg, prompt, lane, model_patch=None, extra_patches=()):
    argv = [ex["pi_bin"], "-p", "--mode", "json", "--no-session"] + EXTRA_FLAGS + model_args(mcfg) + [prompt]
    return argv, {"PI_CODING_AGENT_DIR": lane["agent_dir"]}


def parse(rc, out, err, scrub):
    ends = [e for e in events_of(out) if e.get("type") == "agent_end"]
    if rc != 0 or not ends:
        raise RunFail(f"pi exit {rc}, agent_end events {len(ends)}: {scrub(err or '')[-200:]}", out, err)
    u = empty_usage()
    text = ""
    assistants = [m for m in ends[-1].get("messages", []) if m.get("role") == "assistant"]
    # Pi exits 0 when the provider refuses the request (dead route, bad key, quota): the last assistant
    # message then carries stopReason "error". That is the harness failing to run, not a wrong answer.
    if assistants and assistants[-1].get("stopReason") == "error":
        why = str(assistants[-1].get("errorMessage") or "no error message")
        raise RunFail(f"pi provider error: {scrub(why)[:300]}", out, err)
    if not assistants:
        raise RunFail("pi produced no assistant message", out, err)
    for m in assistants:
        x = m.get("usage") or {}
        u["i"] += x.get("input", 0)  # uncached input
        u["cr"] += x.get("cacheRead", 0)
        u["cw"] += x.get("cacheWrite", 0)
        u["o"] += x.get("output", 0)
        u["reasoning"] += x.get("reasoning", 0)
        u["turns"] += 1
        for c in m.get("content", []):
            if c.get("type") in ("toolCall", "tool_call", "tool_use"):
                u["tools"] += 1
        t = "".join(c.get("text", "") for c in m.get("content", []) if c.get("type") == "text")
        text = t or text
    return u, text


def after_run(lane):
    pass

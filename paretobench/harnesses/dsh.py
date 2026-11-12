"""Stock DeepSeek Harness (dsh), headless, no changes beyond the generated model patch."""
import os
import shutil
import subprocess
import tempfile

from ..config import PBError
from . import RunFail, events_of, empty_usage

name = "dsh"
family = "dsh"
needs_key = True  # the runner puts the model's key into the child environment


def validate(mcfg, ex):
    if not ex.get("dsh_bin") or not os.path.isfile(ex["dsh_bin"]):
        raise PBError("dsh-bin-missing", f"{ex.get('dsh_bin') or '(not found)'} (set PB_DSH_BIN)")
    d = mcfg.get("dsh")
    if not isinstance(d, dict) or not d.get("provider") or not d.get("model") or not d.get("route"):
        raise PBError("harness-unavailable-for-model", "model has no dsh route")
    k = mcfg.get("key") or {}
    if not k.get("auth") or not k.get("env"):
        raise PBError("key-config-missing", "model needs key.auth and key.env for dsh harnesses")


def version(ex):
    with tempfile.TemporaryDirectory(prefix="pb-version-") as home:
        env = {**os.environ, "DSH_HOME": home, "DSH_TELEMETRY_MODE": "DISABLED"}
        return subprocess.run([ex["dsh_bin"], "--version"], capture_output=True, text=True,
                              timeout=60, env=env).stdout.strip()


def setup_lane(ex, mcfg, work, slot, lane_name):
    home = os.path.join(work, "homes", f"{lane_name}-{slot}")
    os.makedirs(home, exist_ok=True)
    return {"home": home}


def build_command(ex, mcfg, prompt, lane, model_patch=None, extra_patches=()):
    if not model_patch:
        raise PBError("model-patch-missing", "dsh harnesses need the generated model patch")
    argv = [ex["dsh_bin"], "headless", "--patch", model_patch]
    for p in extra_patches:
        argv += ["--patch", p]
    argv += ["--json", "--permission-mode", "workspace-write", "--approval-policy", "never", prompt]
    return argv, {"DSH_HOME": lane["home"], "DSH_TELEMETRY_MODE": "DISABLED"}


def parse(rc, out, err, scrub):
    u = empty_usage()
    final = None
    for e in events_of(out):
        if e.get("type") == "status" and e.get("phase") == "step_end":
            x = e.get("usage") or {}
            u["i"] += x.get("inputTokens", 0)  # uncached input
            u["cr"] += x.get("cacheReadTokens", 0)
            u["cw"] += x.get("cacheWriteTokens", 0)
            u["o"] += x.get("outputTokens", 0)
            u["reasoning"] += x.get("reasoningTokens", 0)
        elif e.get("type") == "status" and e.get("phase") == "step_start":
            u["turns"] += 1
        elif e.get("type") == "tool_call":
            u["tools"] += 1
        elif e.get("type") == "final":
            final = e
    reason = ((final or {}).get("reason") or {}).get("kind")
    if rc != 0 or reason != "completed":
        raise RunFail(f"dsh exit {rc}, final reason {reason!r}: {scrub(err or '')[-200:]}", out, err)
    return u, (final or {}).get("text", "")


def after_run(lane):
    shutil.rmtree(os.path.join(lane["home"], "sessions"), ignore_errors=True)

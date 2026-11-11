"""Claude Code, stock config. Claude models only."""
import json
import os
import subprocess

from ..config import PBError
from . import RunFail, empty_usage

name = "claude-code"
family = "claude"


def validate(mcfg, ex):
    if not ex.get("claude_bin") or not os.path.isfile(ex["claude_bin"]):
        raise PBError("claude-bin-missing", f"{ex.get('claude_bin') or '(not found)'} (set PB_CLAUDE_BIN or put claude on PATH)")
    if not isinstance(mcfg.get("claude"), list):
        raise PBError("harness-unavailable-for-model", "model has no 'claude' model args")


def version(ex):
    return subprocess.run([ex["claude_bin"], "--version"], capture_output=True, text=True,
                          timeout=60).stdout.strip()


def setup_lane(ex, mcfg, work, slot, lane_name):
    return {}


def build_command(ex, mcfg, prompt, lane, model_patch=None, extra_patches=()):
    argv = [ex["claude_bin"], "-p"] + list(mcfg["claude"]) + [
        "--no-session-persistence", "--setting-sources", "", "--disable-slash-commands",
        "--strict-mcp-config", "--no-chrome", "--permission-mode", "acceptEdits",
        "--allowedTools", "Bash,Read,Edit,Write,Glob,Grep", "--output-format", "json", prompt]
    return argv, {}


def parse(rc, out, err, scrub):
    try:
        j = json.loads(out)
    except ValueError:
        j = None
    if rc != 0 or not isinstance(j, dict) or "usage" not in j:
        raise RunFail(f"claude exit {rc}: {scrub(err or '')[-200:]}", out, err)
    x = j["usage"]
    u = empty_usage()
    u.update(i=x.get("input_tokens", 0), cr=x.get("cache_read_input_tokens", 0),
             cw=x.get("cache_creation_input_tokens", 0), o=x.get("output_tokens", 0),
             reasoning=None, turns=j.get("num_turns"), tools=None)
    return u, j.get("result", "")


def after_run(lane):
    pass

"""Codex CLI, stock, headless, on the same model route as the dsh-family arms.

Command: `<codex> exec --json --skip-git-repo-check --ephemeral <prompt>`. Each lane gets its own CODEX_HOME that
holds only a generated config.toml (model, provider route, reasoning effort, approvals never, workspace-write
sandbox), so no user config, rules, AGENTS.md or login is loaded. The config is built from the model entry's `dsh`
object (route baseURL and apiKeyEnv, model, reasoningEffort): a model that can run the dsh arms can run this one with
no new config keys. The key is never written to the config; the runner puts it in the child environment under
the route's apiKeyEnv (this adapter sets needs_key).

Usage: Codex counts cached tokens inside input_tokens, so uncached input = input_tokens - cached_input_tokens.
Codex reports usage per user turn, not per model request, so the request count is not available: turns is
tools + 1, a LOWER BOUND on model requests (see docs/METHODOLOGY.md).
"""
import json
import os
import subprocess

from ..config import PBError
from . import RunFail, empty_usage, events_of

name = "codex"
family = "codex"
needs_key = True
PROVIDER = "bench"
NON_TOOL_ITEMS = ("agent_message", "reasoning", "error", "todo_list")


def _route(mcfg):
    d = mcfg.get("dsh")
    if (not isinstance(d, dict) or not d.get("model") or not isinstance(d.get("route"), dict)
            or not d["route"].get("baseURL")):
        raise PBError("harness-unavailable-for-model", "codex needs the model's dsh object (model, route.baseURL)")
    k = mcfg.get("key") or {}
    if not k.get("auth") or not k.get("env"):
        raise PBError("key-config-missing", "model needs key.auth and key.env for codex")
    env_key = d["route"].get("apiKeyEnv") or k["env"]
    if env_key != k["env"]:
        raise PBError("key-config-mismatch", "dsh.route.apiKeyEnv and key.env must name the same variable")
    return d, env_key


def validate(mcfg, ex):
    _route(mcfg)
    if not ex.get("codex_bin") or not os.path.isfile(ex["codex_bin"]):
        raise PBError("codex-bin-missing", f"{ex.get('codex_bin') or '(not found)'} (set PB_CODEX_BIN)")


def version(ex):
    if not ex.get("codex_bin") or not os.path.isfile(ex["codex_bin"]):
        raise PBError("codex-bin-missing", f"{ex.get('codex_bin') or '(not found)'} (set PB_CODEX_BIN)")
    return subprocess.run([ex["codex_bin"], "--version"], capture_output=True, text=True,
                          timeout=60).stdout.strip()


def wire_effort(d):
    """The effort value to send. The model's own route may spell a level differently on the wire (its
    reasoningEfforts map, for example off -> none); Codex passes the value through, so the wire spelling is used."""
    effort = d.get("reasoningEffort") or "medium"
    for model in d["route"].get("models") or []:
        if isinstance(model, dict) and model.get("id") == d["model"]:
            mapped = (model.get("reasoningEfforts") or {}).get(effort)
            if isinstance(mapped, str) and mapped:
                return mapped
    return effort


def config_toml(mcfg):
    d, env_key = _route(mcfg)
    return f'''model = {json.dumps(d["model"])}
model_provider = {json.dumps(PROVIDER)}
model_reasoning_effort = {json.dumps(wire_effort(d))}
approval_policy = "never"
sandbox_mode = "workspace-write"

[model_providers.{PROVIDER}]
name = {json.dumps(PROVIDER)}
base_url = {json.dumps(d["route"]["baseURL"])}
env_key = {json.dumps(env_key)}
wire_api = "responses"
'''


def setup_lane(ex, mcfg, work, slot, lane_name):
    home = os.path.join(work, "codex-homes", f"{lane_name}-{slot}")
    os.makedirs(home, exist_ok=True)
    with open(os.path.join(home, "config.toml"), "w") as f:
        f.write(config_toml(mcfg))
    return {"codex_home": home}


def build_command(ex, mcfg, prompt, lane, model_patch=None, extra_patches=()):
    argv = [ex["codex_bin"], "exec", "--json", "--skip-git-repo-check", "--ephemeral", prompt]
    return argv, {"CODEX_HOME": lane["codex_home"]}


def parse(rc, out, err, scrub):
    u = empty_usage()
    text = ""
    done = False
    tools = 0
    for e in events_of(out):
        t = e.get("type")
        if t == "turn.completed":
            done = True
            x = e.get("usage") or {}
            cached = x.get("cached_input_tokens", 0) or 0
            u["i"] += max(0, (x.get("input_tokens", 0) or 0) - cached)
            u["cr"] += cached
            u["cw"] += x.get("cache_write_input_tokens", 0) or 0
            u["o"] += x.get("output_tokens", 0) or 0
            u["reasoning"] += x.get("reasoning_output_tokens", 0) or 0
        elif t == "item.completed":
            it = e.get("item") or {}
            kind = it.get("type")
            if kind == "agent_message":
                text = it.get("text") or text
            elif kind not in NON_TOOL_ITEMS:
                tools += 1
    if rc != 0 or not done:
        raise RunFail(f"codex exit {rc}, turn.completed {done}: {scrub(err or '')[-200:]}", out, err)
    u["tools"] = tools
    u["turns"] = tools + 1  # lower bound: usage is per user turn, not per model request
    return u, text


def after_run(lane):
    pass

"""Configuration loading and validation. Python 3 stdlib only.

The real models file is $PARETOBENCH_CONFIG or ~/.config/paretobench/models.json.
Machine-specific executable paths live in ~/.config/paretobench/env (KEY=VALUE lines),
never in the repo. Keys are read from the Pi agent auth store at run time and are
never printed, stored in rows, or passed on a command line.
"""
import hashlib
import json
import os
import shutil

HARNESS_NAMES = ("pi", "steak-pi", "claude-code", "dsh", "steak-dsh", "steak-pi-lean", "steak-dsh-long", "codex")
LEGACY_TASK_SET = "legacy-steak-dsh-bench"
TOKEN_KEYS = ("i", "cr", "cw", "o")
# Used when every rate for a model is 0 (flat plan): weighted tokens instead of dollars.
WEIGHTS = {"i": 1.0, "cr": 0.1, "cw": 1.25, "o": 4.0}

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class PBError(Exception):
    """An error with a machine-readable name: str(e) is the human-readable cause."""

    def __init__(self, name, msg):
        super().__init__(msg)
        self.name = name


# Task sets selectable with --task-set. The default (short) set is never changed by adding another.
DEFAULT_TASK_SET = "short"
TASK_SETS = {"short": "tasks", "long-v1": "tasks-long"}
# Hard per-run timeout when --timeout is not given: the short set keeps 600 s; long sets read budgets.json.
DEFAULT_TIMEOUT = 600


def tasks_dir(task_set=None):
    """Directory of a task set. The short set is $PARETOBENCH_TASKS or <repo>/tasks. Another set is
    $PARETOBENCH_TASKS_<NAME> (name upper-cased, '-' as '_') or the sibling folder of the short set."""
    task_set = task_set or DEFAULT_TASK_SET
    if task_set not in TASK_SETS:
        raise PBError("unknown-task-set", f"'{task_set}' (task sets: {', '.join(TASK_SETS)})")
    short = os.environ.get("PARETOBENCH_TASKS") or os.path.join(REPO_ROOT, TASK_SETS[DEFAULT_TASK_SET])
    if task_set == DEFAULT_TASK_SET:
        d, hint = short, "PARETOBENCH_TASKS"
    else:
        hint = "PARETOBENCH_TASKS_" + task_set.upper().replace("-", "_")
        d = os.environ.get(hint) or os.path.join(os.path.dirname(os.path.abspath(short)), TASK_SETS[task_set])
    if not os.path.isdir(d):
        raise PBError("tasks-dir-missing", f"{d} (set {hint} to the tasks directory)")
    return d


def task_budgets(d):
    """Per-task hard timeouts in seconds from <tasks dir>/budgets.json ({"default": s, "L6": s}); {} if none."""
    p = os.path.join(d, "budgets.json")
    if not os.path.isfile(p):
        return {}
    try:
        with open(p) as f:
            b = json.load(f)
        assert isinstance(b, dict) and all(isinstance(v, int) and v > 0 for v in b.values())
    except Exception:
        raise PBError("budgets-file-invalid", f"{p}: must be an object of task id or 'default' -> seconds")
    return b


def config_dir():
    return os.path.expanduser("~/.config/paretobench")


def load_env_file(path=None):
    """Load KEY=VALUE lines from ~/.config/paretobench/env when present.

    Existing environment variables win. Values are never printed.
    """
    path = path or os.path.join(config_dir(), "env")
    if not os.path.isfile(path):
        return
    with open(path) as f:
        for n, line in enumerate(f, 1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                raise PBError("bad-env-file", f"{path} line {n}: expected KEY=VALUE")
            k, v = line.split("=", 1)
            k, v = k.strip(), v.strip().strip('"').strip("'")
            if not k:
                raise PBError("bad-env-file", f"{path} line {n}: empty key")
            os.environ.setdefault(k, os.path.expanduser(v))


def models_path():
    return os.path.expanduser(os.environ.get("PARETOBENCH_CONFIG")
                              or os.path.join(config_dir(), "models.json"))


def load_models(path=None):
    path = path or models_path()
    if not os.path.isfile(path):
        raise PBError("models-config-missing",
                      f"{path} (copy configs/models.example.json there and fill in routes, "
                      f"or set PARETOBENCH_CONFIG)")
    try:
        with open(path) as f:
            models = json.load(f)
    except ValueError as e:
        raise PBError("models-config-invalid", f"{path}: {e}")
    validate_models(models)
    return models


def _need(cond, name, msg):
    if not cond:
        raise PBError(name, msg)


def validate_models(models):
    """Check the models config schema. Raises PBError with a named cause."""
    _need(isinstance(models, dict) and models, "models-config-invalid",
          "models config must be a non-empty JSON object keyed by model name")
    for key, m in models.items():
        w = f"model '{key}'"
        _need(isinstance(m, dict), "models-config-invalid", f"{w}: entry must be an object")
        rates = m.get("rates")
        _need(isinstance(rates, dict) and all(isinstance(rates.get(k), (int, float))
                                              and rates.get(k) >= 0 for k in TOKEN_KEYS),
              "models-config-invalid", f"{w}: rates must have numeric i, cr, cw, o >= 0")
        hs = m.get("harnesses")
        _need(isinstance(hs, list) and hs and all(h in HARNESS_NAMES for h in hs)
              and len(set(hs)) == len(hs),
              "models-config-invalid",
              f"{w}: harnesses must be a non-empty list of {', '.join(HARNESS_NAMES)} without duplicates")
        for h in hs:
            if h in ("pi", "steak-pi", "steak-pi-lean"):
                _need(isinstance(m.get("pi"), list) and all(isinstance(a, str) for a in m["pi"]),
                      "models-config-invalid", f"{w}: harness '{h}' needs a 'pi' list of model args")
            elif h in ("dsh", "steak-dsh", "steak-dsh-long", "codex"):
                d = m.get("dsh")
                _need(isinstance(d, dict) and isinstance(d.get("provider"), str)
                      and isinstance(d.get("model"), str) and isinstance(d.get("route"), dict),
                      "models-config-invalid",
                      f"{w}: harness '{h}' needs a 'dsh' object with provider, model and route")
                k = m.get("key")
                _need(isinstance(k, dict) and isinstance(k.get("auth"), str) and isinstance(k.get("env"), str),
                      "models-config-invalid", f"{w}: harness '{h}' needs key.auth and key.env")
            elif h == "claude-code":
                _need(isinstance(m.get("claude"), list) and all(isinstance(a, str) for a in m["claude"]),
                      "models-config-invalid", f"{w}: harness 'claude-code' needs a 'claude' list of model args")
        if "steak_pi_extra" in m:
            _need(isinstance(m["steak_pi_extra"], list) and all(isinstance(a, str) for a in m["steak_pi_extra"]),
                  "models-config-invalid", f"{w}: steak_pi_extra must be a list of strings")
    return True


def validate_tasks(d=None):
    """Check that the task set is complete and well formed. Raises PBError."""
    d = d or tasks_dir()
    tf = os.path.join(d, "tasks.json")
    _need(os.path.isfile(tf), "tasks-file-missing", tf)
    try:
        with open(tf) as f:
            tasks = json.load(f)
    except ValueError as e:
        raise PBError("tasks-file-invalid", f"{tf}: {e}")
    _need(isinstance(tasks, dict) and tasks
          and all(isinstance(k, str) and isinstance(v, str) and v.strip() for k, v in tasks.items()),
          "tasks-file-invalid", f"{tf}: must be a non-empty object of task id -> prompt string")
    for rel in ("checks/check.py", "gen_fixture.py"):
        _need(os.path.isfile(os.path.join(d, rel)), "task-file-missing", os.path.join(d, rel))
    _need(os.path.isdir(os.path.join(d, "fixture")), "task-file-missing", os.path.join(d, "fixture"))
    for t in tasks:
        _need(os.path.isfile(os.path.join(d, "reference", t + ".py")),
              "reference-missing", f"{d}/reference/{t}.py (every task needs a reference solution)")
    return tasks


def task_set_hash(d=None):
    """Hash of tasks.json + checks + fixture + generator, so results from different
    task sets are never mixed. Stable across machines (relative paths, sorted)."""
    d = d or tasks_dir()
    files = ["tasks.json", "gen_fixture.py"]
    # a task set may keep generator helpers (gen_*.py) and a budgets.json beside the generator
    for n in sorted(os.listdir(d)):
        if (n.startswith("gen_") and n.endswith(".py") and n != "gen_fixture.py") or n == "budgets.json":
            files.append(n)
    for sub in ("checks", "fixture"):
        for root, dirs, names in os.walk(os.path.join(d, sub)):
            dirs[:] = sorted(x for x in dirs if x != "__pycache__")
            for n in sorted(names):
                if n.endswith(".pyc"):
                    continue
                files.append(os.path.relpath(os.path.join(root, n), d))
    h = hashlib.sha256()
    for rel in sorted(files):
        with open(os.path.join(d, rel), "rb") as f:
            data = f.read()
        h.update(rel.encode() + b"\0" + data + b"\0")
    return h.hexdigest()[:16]


def resolve_executables():
    """Executable paths from env with PATH defaults. No machine-specific path here."""
    load_env_file()
    return {
        "pi_bin": os.path.expanduser(os.environ.get("PB_PI_BIN") or shutil.which("pi") or ""),
        "dsh_bin": os.path.expanduser(os.environ.get("PB_DSH_BIN") or shutil.which("dsh") or ""),
        "claude_bin": os.path.expanduser(os.environ.get("PB_CLAUDE_BIN") or shutil.which("claude") or ""),
        "codex_bin": os.path.expanduser(os.environ.get("PB_CODEX_BIN") or shutil.which("codex") or ""),
        "steak_pi_package": os.path.expanduser(os.environ.get("PB_STEAK_PI_PACKAGE") or ""),
        "steak_dsh_patch": os.path.expanduser(os.environ.get("PB_STEAK_DSH_PATCH") or ""),
        "pi_agent_dir": os.path.expanduser(os.environ.get("PB_PI_AGENT_DIR") or "~/.pi/agent"),
    }


def load_auth_key(agent_dir, auth_name):
    """Read one api_key entry from the Pi agent auth store. Never printed."""
    path = os.path.join(agent_dir, "auth.json")
    try:
        with open(path) as f:
            entry = json.load(f)[auth_name]
        assert entry.get("type") == "api_key" and entry.get("key")
    except Exception:
        raise PBError("auth-entry-missing", f"no api_key entry '{auth_name}' in {path}")
    return entry["key"]


# --- cost helpers (one rate table per model, applied to every harness) ---

def all_zero(rates):
    return all(rates.get(k, 0) == 0 for k in TOKEN_KEYS)


def cost(row, rates):
    return sum(row.get(k, 0) * rates.get(k, 0) for k in TOKEN_KEYS)


def weighted(row):
    return sum(row.get(k, 0) * WEIGHTS[k] for k in TOKEN_KEYS)


def total_input(row):
    return row.get("i", 0) + row.get("cr", 0) + row.get("cw", 0)


def metric(row, rates):
    """Dollars from the one rate table, or weighted tokens when all rates are 0."""
    return weighted(row) if all_zero(rates) else cost(row, rates)


def metric_label(rates):
    return "weighted tokens" if all_zero(rates) else "cost $"


# --- tiny YAML emitter (stdlib only; enough for the dsh model patch) ---

def _yscalar(v):
    if v is True:
        return "true"
    if v is False:
        return "false"
    if v is None:
        return "null"
    if isinstance(v, (int, float)):
        return json.dumps(v)
    return json.dumps(str(v))  # JSON double-quoted strings are valid YAML scalars


def _emit(v, ind):
    pad = "  " * ind
    out = []
    if isinstance(v, dict):
        for k, val in v.items():
            if isinstance(val, dict) and val:
                out.append(f"{pad}{k}:")
                out.extend(_emit(val, ind + 1))
            elif isinstance(val, list) and val:
                out.append(f"{pad}{k}:")
                out.extend(_emit(val, ind + 1))
            elif isinstance(val, dict):
                out.append(f"{pad}{k}: {{}}")
            elif isinstance(val, list):
                out.append(f"{pad}{k}: []")
            else:
                out.append(f"{pad}{k}: {_yscalar(val)}")
    elif isinstance(v, list):
        for item in v:
            if isinstance(item, dict) and item:
                lines = _emit(item, ind + 1)
                out.append(pad + "- " + lines[0][len(pad) + 2:])
                out.extend(lines[1:])
            else:
                out.append(f"{pad}- {_yscalar(item)}")
    return out


def to_yaml(obj):
    return "\n".join(_emit(obj, 0)) + "\n"

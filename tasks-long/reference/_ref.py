"""Tool-step layer for the scripted reference solutions: every call is one step an agent would take
(read, search, edit, write, run a command, list a folder). The count is printed as STEPS=<n> on exit and
compared by `pb selftest --task-set long-v1` with steps.json."""
import atexit
import os
import re
import subprocess
import sys

STEPS = 0


def _n():
    global STEPS
    STEPS += 1


def ls(path="."):
    _n()
    return sorted(os.listdir(path))


def read(path):
    _n()
    with open(path, newline="") as f:
        return f.read()


def grep(pattern, path=".", include=".py"):
    """[(file, line number, line)] for every match."""
    _n()
    rx, out = re.compile(pattern), []
    for dp, dns, fns in os.walk(path):
        dns[:] = sorted(d for d in dns if d != "__pycache__")
        for fn in sorted(fns):
            if include and not fn.endswith(include):
                continue
            p = os.path.join(dp, fn)
            with open(p, errors="replace") as f:
                for i, line in enumerate(f, 1):
                    if rx.search(line):
                        out.append((os.path.relpath(p, path).replace(os.sep, "/"), i, line.rstrip("\n")))
    return out


def edit(path, old, new, count=1):
    _n()
    with open(path, newline="") as f:
        text = f.read()
    assert text.count(old) == count, f"{path}: expected {count} of {old!r}, found {text.count(old)}"
    with open(path, "w", newline="") as f:
        f.write(text.replace(old, new))


def edit_re(path, pattern, repl):
    _n()
    with open(path, newline="") as f:
        text = f.read()
    new, k = re.subn(pattern, repl, text)
    assert k, f"{path}: pattern not found"
    with open(path, "w", newline="") as f:
        f.write(new)
    return k


def write(path, text):
    _n()
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", newline="") as f:
        f.write(text)


def sh(cmd, ok=(0,)):
    _n()
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, env=env)
    assert r.returncode in ok, f"{cmd!r} exited {r.returncode}: {(r.stdout + r.stderr)[-400:]}"
    return r


def say(text):
    """The agent's final reply (not a tool step): the runner stores it as ans.txt."""
    with open("ans.txt", "w") as f:
        f.write(text)


atexit.register(lambda: print(f"STEPS={STEPS}", file=sys.stderr))

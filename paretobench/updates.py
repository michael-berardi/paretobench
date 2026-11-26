"""Release notices, `paretobench update` and opt-in automatic updates (stdlib only).

The check is one anonymous GET of this project's public GitHub "latest release" record, at
most once per 24 h, on a background thread. State is one small cache file (check time,
latest version, skip, last notice, last automatic-install failure); the user's switches live
in settings.json next to the models config. PARETOBENCH_UPDATE_API points the check at a
local server for tests and manual proofs.
"""
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

from . import __version__
from . import config as C

REPO_SLUG = "michael-berardi/paretobench"  # the slug scripts/install.sh and install.ps1 download from
RELEASE_API = f"https://api.github.com/repos/{REPO_SLUG}/releases/latest"
GIT_SOURCE = f"git+https://github.com/{REPO_SLUG}"  # PyPI's "paretobench" is an unrelated project
HEADERS = {"User-Agent": "paretobench-update-check", "Accept": "application/vnd.github+json"}
CHECK_INTERVAL = 24 * 60 * 60
HTTP_TIMEOUT = 4
PREVIOUS_MAX_AGE = 7 * 24 * 60 * 60
LOG_TAIL = 64 * 1024
BUNDLE, SUMS = "paretobench.tar.gz", "SHA256SUMS"
AGENT_ENV = ("CLAUDECODE", "CODEX_SANDBOX")  # agent shells: the host shows its own notices
VERSION_RE = re.compile(r"v?(\d+)\.(\d+)\.(\d+)")
MANAGERS = ("uv", "pipx", "pip")
CACHE_DEFAULTS = {"checked_at": 0, "latest_version": "", "last_error": "", "skipped_version": "",
                  "notified_version": "", "notified_at": 0, "auto_failed_version": "", "auto_error": ""}
SETTINGS_DEFAULTS = {"check_automatically": True, "auto_install": False, "auto_asked": False}


def _clean(value, limit=200):
    return re.sub(r"[\x00-\x1f\x7f]", " ", str(value)).strip()[:limit]


def _is_tty(stream):
    try:
        return bool(stream.isatty())
    except (AttributeError, ValueError, OSError):
        return False


# --- state files -------------------------------------------------------------------------

def cache_path(env=None):
    env = os.environ if env is None else env
    if env.get("PARETOBENCH_UPDATE_CACHE"):
        return os.path.expanduser(env["PARETOBENCH_UPDATE_CACHE"])
    if os.name == "nt":
        base = os.path.join(env.get("LOCALAPPDATA") or os.path.expanduser("~"), "paretobench", "Cache")
    elif sys.platform == "darwin":
        base = os.path.expanduser("~/Library/Caches/paretobench")
    else:
        base = os.path.join(env.get("XDG_CACHE_HOME") or os.path.expanduser("~/.cache"), "paretobench")
    return os.path.join(base, "updates.json")


def log_path(env=None):
    return os.path.join(os.path.dirname(cache_path(env)), "auto-update.log")


def settings_path(env=None):
    env = os.environ if env is None else env
    return os.path.expanduser(env.get("PARETOBENCH_SETTINGS") or os.path.join(C.config_dir(), "settings.json"))


def _read_json(path):
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _write_json(path, data):
    """Atomic write; mkstemp creates the file with mode 0600."""
    folder = os.path.dirname(os.path.abspath(path))
    os.makedirs(folder, mode=0o700, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".updates-", suffix=".tmp", dir=folder)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, sort_keys=True)
            f.write("\n")
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def read_cache(path=None):
    data = _read_json(path or cache_path())
    out = {}
    for key, default in CACHE_DEFAULTS.items():
        value = data.get(key)
        if isinstance(default, str):
            ok = isinstance(value, str)
        else:
            ok = isinstance(value, (int, float)) and not isinstance(value, bool)
        out[key] = value if ok else default
    return out


def write_cache(cache, path=None):
    _write_json(path or cache_path(), cache)


def read_settings(path=None):
    data = _read_json(path or settings_path())
    return {k: data[k] if isinstance(data.get(k), bool) else v for k, v in SETTINGS_DEFAULTS.items()}


def write_settings(changes, path=None):
    settings = read_settings(path)
    settings.update(changes)
    _write_json(path or settings_path(), settings)
    return settings


# --- versions and the release record -----------------------------------------------------

def version_tuple(value):
    """Only stable x.y.z (optionally v-prefixed) versions count; anything else is None."""
    m = VERSION_RE.fullmatch(str(value or "").strip())
    return tuple(int(n) for n in m.groups()) if m else None


def is_newer(version, current=__version__):
    a, b = version_tuple(version), version_tuple(current)
    return bool(a and b and a > b)


def stable_version(release):
    """x.y.z of a published stable release, or '' for drafts, prereleases and odd tags."""
    if release.get("draft") or release.get("prerelease"):
        return ""
    t = version_tuple(release.get("tag_name"))
    return "%d.%d.%d" % t if t else ""


def release_notes(release, limit=5):
    """The first lines of the release notes, without headings, images or control characters."""
    lines = []
    for raw in str(release.get("body") or "").splitlines():
        line = _clean(" ".join(raw.split()))
        if line.startswith("#"):
            continue
        line = line.lstrip("*-> ").strip()
        if line and not line.startswith("!"):
            lines.append(line)
        if len(lines) == limit:
            break
    return lines


def _get_json(url, headers, timeout):
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=timeout) as r:
        raw = r.read(1024 * 1024 + 1)
    if len(raw) > 1024 * 1024:
        raise ValueError("the release record is larger than 1 MiB")
    return json.loads(raw.decode("utf-8"))


def _cause(error):
    if isinstance(error, C.PBError):
        return f"{error.name}: {error}"
    if isinstance(error, urllib.error.HTTPError):
        try:
            error.close()
        except Exception:
            pass
        return f"HTTP {error.code}"
    if isinstance(error, TimeoutError) or isinstance(getattr(error, "reason", None), TimeoutError):
        return f"timed out after {HTTP_TIMEOUT} s"
    if isinstance(error, urllib.error.URLError):
        return "network error: " + _clean(error.reason)
    if isinstance(error, json.JSONDecodeError):
        return "the release record is not valid JSON"
    return _clean(error) or type(error).__name__


def check(force=False, fetch=None, env=None, path=None):
    """Refresh the cache at most once per CHECK_INTERVAL (always with force).

    Returns (cache, release); release is None when no request was made or it failed, and the
    cause is then in cache["last_error"]. The slot is claimed before the request, so a process
    that exits mid-request does not cause a second request that day.
    """
    env = os.environ if env is None else env
    path = path or cache_path(env)
    cache = read_cache(path)
    if not force and 0 <= time.time() - cache["checked_at"] < CHECK_INTERVAL:
        return cache, None
    cache.update(checked_at=time.time(), last_error="the check did not finish before the command exited")
    write_cache(cache, path)
    release = None
    try:
        release = (fetch or _get_json)(env.get("PARETOBENCH_UPDATE_API") or RELEASE_API,
                                       dict(HEADERS), HTTP_TIMEOUT)
        if not isinstance(release, dict):
            raise ValueError("the release record is not a JSON object")
        cache.update(latest_version=stable_version(release), last_error="")
    except Exception as error:
        release = None
        cache["last_error"] = _cause(error)
    write_cache(cache, path)
    return cache, release


# --- the notice ---------------------------------------------------------------------------

def notice_allowed(env=None, stdout=None, stderr=None, settings=None):
    """Off for non-terminals, CI, agent shells, the env opt-out and the settings switch."""
    env = os.environ if env is None else env
    if env.get("PARETOBENCH_NO_UPDATE_CHECK", "").strip() not in ("", "0"):
        return False
    if env.get("CI", "").strip().lower() not in ("", "0", "false"):
        return False
    if any(env.get(k) for k in AGENT_ENV):
        return False
    if not (_is_tty(sys.stdout if stdout is None else stdout) and _is_tty(sys.stderr if stderr is None else stderr)):
        return False
    return (settings or read_settings(settings_path(env)))["check_automatically"]


def start_background_check(fetch=None, env=None, path=None):
    """Run the daily check on a daemon thread while the command runs."""
    def work():
        try:
            check(fetch=fetch, env=env, path=path)
        except Exception:
            pass  # a check never breaks the command it accompanies
    thread = threading.Thread(target=work, name="paretobench-update-check", daemon=True)
    thread.start()
    return thread, time.monotonic() + HTTP_TIMEOUT


def finish_background_check(state, show=True, stderr=None, path=None, settings_file=None, kind=None,
                            spawn=None):
    """After the command: wait out the rest of the check's timeout at most, then maybe notify."""
    thread, deadline = state
    thread.join(max(0.0, deadline - time.monotonic()))
    if not show:
        return False
    try:
        return show_notice(stderr=stderr, path=path, settings_file=settings_file, kind=kind, spawn=spawn)
    except Exception:
        return False


def manager_command(kind, version):
    """The upgrade command for a package-manager install, pinned to this repo's release tag."""
    spec = f"{GIT_SOURCE}@v{version}"
    if kind == "uv":
        return ["uv", "tool", "install", "--force", spec]
    if kind == "pipx":
        return ["pipx", "install", "--force", spec]
    if kind == "pip":
        return [sys.executable, "-m", "pip", "install", "--upgrade", spec]
    return None


def upgrade_hint(kind, version):
    if kind in ("uv", "pipx"):
        return " ".join(manager_command(kind, version))
    if kind == "source":
        return "git pull"
    return "paretobench update"  # installer bundle, and pip (it runs this interpreter's pip)


def notice_lines(version, kind, current=__version__):
    return (f"paretobench {version} available (you have {current}) · run: {upgrade_hint(kind, version)}",
            "turn on automatic updates: paretobench update --auto on · skip: paretobench update --skip")


def show_notice(stderr=None, path=None, settings_file=None, kind=None, spawn=None):
    """Once per day per version, never for a skipped one. With auto on, install instead."""
    stderr = sys.stderr if stderr is None else stderr
    path = path or cache_path()
    cache = read_cache(path)
    version = cache["latest_version"]
    if not is_newer(version) or version == cache["skipped_version"]:
        return False
    now = time.time()
    if cache["notified_version"] == version and 0 <= now - cache["notified_at"] < CHECK_INTERVAL:
        return False
    kind = kind or detect_install_kind()[0]
    auto = (read_settings(settings_file)["auto_install"] and kind != "source"
            and cache["auto_failed_version"] != version)
    cache.update(notified_version=version, notified_at=now)
    write_cache(cache, path)
    if auto:
        (spawn or start_auto_install)()
        print(f"paretobench {version} is installing in the background; it applies on the next start.",
              file=stderr)
        return "auto"
    first, second = notice_lines(version, kind)
    if os.name != "nt" and not os.environ.get("NO_COLOR"):
        second = f"\x1b[2m{second}\x1b[0m"
    print(first, file=stderr)
    print(second, file=stderr)
    return True


def start_auto_install(env=None, popen=None):
    """Detached `update --background`; its log is rewritten per run, so it stays one small file."""
    env = os.environ if env is None else env
    log = log_path(env)
    os.makedirs(os.path.dirname(log), mode=0o700, exist_ok=True)
    cmd = [sys.executable, "-m", "paretobench.cli", "update", "--background"]
    kwargs = {"stdin": subprocess.DEVNULL, "stderr": subprocess.STDOUT, "cwd": os.path.dirname(log)}
    if os.name == "nt":
        # CREATE_NO_WINDOW | BELOW_NORMAL_PRIORITY_CLASS | CREATE_NEW_PROCESS_GROUP
        kwargs["creationflags"] = 0x08000000 | 0x00004000 | 0x00000200
    else:
        kwargs["start_new_session"] = True
    with open(log, "w", encoding="utf-8") as handle:
        (popen or subprocess.Popen)(cmd, stdout=handle, **kwargs)
    return cmd


# --- install kinds, verified install, rollback --------------------------------------------

def detect_install_kind(module_file=None):
    """('installer', app dir) for the install.sh/install.ps1 bundle, (manager, '') for uv tool,
    pipx and pip installs, ('source', checkout dir) for anything else."""
    path = os.path.realpath(module_file or __file__)
    parts = [p.lower() for p in re.split(r"[\\/]+", path)]
    if "site-packages" in parts or "dist-packages" in parts:
        if "pipx" in parts:
            return "pipx", ""
        if "uv" in parts and "tools" in parts:
            return "uv", ""
        return "pip", ""
    root = os.path.dirname(os.path.dirname(path))
    bundle = (os.path.basename(root).lower() == "app"
              and os.path.isfile(os.path.join(root, "tasks", "tasks.json"))
              and not os.path.exists(os.path.join(root, "pyproject.toml"))
              and not os.path.exists(os.path.join(root, ".git")))
    return ("installer" if bundle else "source"), root


def _bundle_version(app_dir):
    try:
        with open(os.path.join(app_dir, "paretobench", "__init__.py"), encoding="utf-8") as f:
            m = re.search(r'^__version__ = "([^"]+)"', f.read(), re.M)
    except OSError:
        return ""
    return m.group(1) if m else ""


def _download(url, dest):
    u = urllib.parse.urlsplit(url)
    if not (u.scheme == "https" or (u.scheme == "http" and u.hostname in ("127.0.0.1", "localhost", "::1"))):
        raise C.PBError("asset-url-invalid", f"release assets must come over https, not {u.scheme or 'no'} scheme")
    request = urllib.request.Request(url, headers={"User-Agent": HEADERS["User-Agent"]})
    with urllib.request.urlopen(request, timeout=30) as r, open(dest, "wb") as f:
        total = 0
        while chunk := r.read(65536):
            total += len(chunk)
            if total > 64 * 1024 * 1024:
                raise C.PBError("asset-too-large", "a release asset is larger than 64 MiB")
            f.write(chunk)


def _checksum_for(text, name):
    for line in text.splitlines():
        parts = line.split()
        if len(parts) >= 2 and parts[1].lstrip("*") == name:
            return parts[0].lower()
    return ""


def install_bundle(release, app_dir, version, download=None):
    """Verify SHA256SUMS before unpacking, check the new copy starts, then swap keeping one
    `<app>.previous`. The staging folder is removed on success and on failure."""
    assets = {a.get("name"): a.get("browser_download_url") for a in release.get("assets") or []
              if isinstance(a, dict)}
    if not (isinstance(assets.get(BUNDLE), str) and isinstance(assets.get(SUMS), str)):
        raise C.PBError("release-assets-missing", f"the release has no {BUNDLE} and {SUMS}")
    fetch = download or _download
    home = os.path.dirname(os.path.abspath(app_dir))
    previous = app_dir + ".previous"
    stage = tempfile.mkdtemp(prefix=".app.new-", dir=home)
    try:
        bundle, sums, src = (os.path.join(stage, n) for n in (BUNDLE, SUMS, "src"))
        fetch(assets[BUNDLE], bundle)
        fetch(assets[SUMS], sums)
        with open(sums, encoding="utf-8", errors="replace") as f:
            want = _checksum_for(f.read(), BUNDLE)
        if not want:
            raise C.PBError("checksum-missing", f"no checksum for {BUNDLE} in {SUMS}")
        with open(bundle, "rb") as f:
            if hashlib.sha256(f.read()).hexdigest() != want:
                raise C.PBError("checksum-mismatch", f"SHA-256 mismatch for {BUNDLE}; nothing was installed")
        os.mkdir(src)
        with tarfile.open(bundle, "r:gz") as archive:
            members = archive.getmembers()
            for m in members:
                name = m.name.replace("\\", "/")
                if name.startswith("/") or ".." in name.split("/") or not (m.isfile() or m.isdir()):
                    raise C.PBError("unsafe-release-archive", f"unsafe entry in {BUNDLE}: {_clean(name)}")
            try:
                archive.extractall(src, members=members, filter="data")
            except TypeError:  # Python 3.11 before 3.11.4 has no filter; members are checked above
                archive.extractall(src, members=members)
        found = _bundle_version(src)
        if found != version or not os.path.isfile(os.path.join(src, "tasks", "tasks.json")):
            raise C.PBError("release-invalid", f"the download is not paretobench {version} (found {found or 'none'})")
        env = dict(os.environ, PYTHONPATH=src, PARETOBENCH_TASKS=os.path.join(src, "tasks"),
                   PARETOBENCH_NO_UPDATE_CHECK="1")
        started = subprocess.run([sys.executable, "-m", "paretobench.cli", "--version"], cwd=src, env=env,
                                 capture_output=True, text=True, timeout=30)
        if started.returncode != 0 or started.stdout.strip() != f"paretobench {version}":
            raise C.PBError("release-start-failed", _clean((started.stderr or started.stdout).strip(), 300))
        if os.path.isdir(previous) and not os.path.islink(previous):
            shutil.rmtree(previous)
        elif os.path.lexists(previous):
            os.unlink(previous)
        if os.path.isdir(app_dir):
            os.replace(app_dir, previous)
            os.utime(previous)  # the seven-day bound counts from the swap
        try:
            os.replace(src, app_dir)
        except OSError:
            if os.path.isdir(previous) and not os.path.exists(app_dir):
                os.replace(previous, app_dir)
            raise
    finally:
        shutil.rmtree(stage, ignore_errors=True)
    return app_dir


def rollback_install(app_dir):
    previous, failed = app_dir + ".previous", app_dir + ".failed"
    if not os.path.isdir(previous):
        raise C.PBError("no-rollback", f"no previous release at {previous} (it is removed once the new one "
                                       "has run successfully, or after seven days)")
    shutil.rmtree(failed, ignore_errors=True)
    if os.path.isdir(app_dir):
        os.replace(app_dir, failed)
    try:
        os.replace(previous, app_dir)
    except OSError:
        if os.path.isdir(failed):
            os.replace(failed, app_dir)
        raise
    shutil.rmtree(failed, ignore_errors=True)
    return _bundle_version(app_dir)


def prune_rollback(ran_ok, module_file=None, now=None):
    """Remove `<app>.previous` once the new version has run a command successfully, or after
    seven days at most. Never raises."""
    try:
        kind, app_dir = detect_install_kind(module_file)
        previous = app_dir + ".previous"
        if kind != "installer" or not os.path.isdir(previous):
            return False
        age = (time.time() if now is None else now) - os.stat(previous).st_mtime
        new_version_ran = ran_ok and _bundle_version(app_dir) == __version__
        if new_version_ran or age > PREVIOUS_MAX_AGE:
            shutil.rmtree(previous, ignore_errors=True)
            return True
    except Exception:
        pass
    return False


# --- `paretobench update` -----------------------------------------------------------------

def _ask(question, default_yes, stderr, ask):
    print(question, end=" ", file=stderr, flush=True)
    try:
        answer = (ask or input)().strip().lower()
    except EOFError:
        answer = ""
    return default_yes if not answer else answer in ("y", "yes")


def _record_auto_failure(path, version, cause):
    cache = read_cache(path)
    cache.update(auto_failed_version=version, auto_error=cause, notified_version="", notified_at=0)
    write_cache(cache, path)


def run_update(args, *, fetch=None, env=None, cache_file=None, settings_file=None, install_kind=None,
               installer=None, runner=None, ask=None, stdin=None, stdout=None, stderr=None):
    """`paretobench update [--check | --skip | --auto on|off|status | --rollback]`."""
    out = sys.stdout if stdout is None else stdout
    err = sys.stderr if stderr is None else stderr
    env = os.environ if env is None else env
    path = cache_file or cache_path(env)
    settings_file = settings_file or settings_path(env)

    if args.auto:
        if args.auto != "status":
            write_settings({"auto_install": args.auto == "on", "auto_asked": True}, settings_file)
        if args.auto == "off" and os.path.exists(log_path(env)):
            os.unlink(log_path(env))
        s = read_settings(settings_file)
        print(f"install updates automatically: {'on' if s['auto_install'] else 'off'}", file=out)
        print(f"check for updates automatically: {'on' if s['check_automatically'] else 'off'}", file=out)
        print(f"version {__version__}", file=out)
        return 0

    if args.check:
        cache, release = check(force=True, fetch=fetch, env=env, path=path)
        if cache["auto_error"]:
            print(f"last automatic install failed: {cache['auto_error']}", file=err)
        if release is None:
            print(f"paretobench update --check failed: {cache['last_error']}", file=err)
            return 1
        if is_newer(cache["latest_version"]):
            print(f"paretobench {cache['latest_version']} available (you have {__version__})", file=out)
            return 10
        print(f"paretobench {__version__} is current", file=out)
        return 0

    if args.skip:
        cache = read_cache(path)
        if not is_newer(cache["latest_version"]):
            cache, release = check(force=True, fetch=fetch, env=env, path=path)
            if release is None:
                print(f"paretobench update --skip failed: {cache['last_error']}", file=err)
                return 1
        version = cache["latest_version"]
        if not is_newer(version):
            print(f"paretobench {__version__} is current; nothing to skip", file=out)
            return 0
        cache["skipped_version"] = version
        write_cache(cache, path)
        print(f"skipped {version}; a newer release will notify again", file=out)
        return 0

    kind, app_dir = install_kind or detect_install_kind()
    if args.rollback:
        if kind != "installer":
            print(f"paretobench update --rollback: only the installer's bundle keeps a previous release "
                  f"(this is a {kind} install)", file=err)
            return 1
        try:
            restored = rollback_install(app_dir)
        except (C.PBError, OSError) as error:
            print(f"paretobench update --rollback: {_cause(error)}", file=err)
            return 1
        print(f"rolled back to paretobench {restored or 'the previous release'}", file=out)
        return 0

    background = getattr(args, "background", False)
    cache, release = check(force=True, fetch=fetch, env=env, path=path)
    if release is None:
        print(f"paretobench update failed: {cache['last_error']}", file=err)
        return 1
    version = cache["latest_version"]
    if not is_newer(version):
        print(f"paretobench {__version__} is current", file=out)
        return 0
    print(f"paretobench {__version__} → {version}", file=out)
    for line in release_notes(release):
        print(f"  {line}", file=out)
    if kind == "source":
        print(f"this is a source checkout ({app_dir}); update it with: git pull", file=err)
        return 1
    cmd = manager_command(kind, version)
    if cmd:
        print(f"{kind} install; running: {' '.join(cmd)}", file=out)
    interactive = not (background or args.yes) and _is_tty(sys.stdin if stdin is None else stdin) and _is_tty(err)
    if interactive and not _ask(f"Install {version} now? [Y/n]", True, err, ask):
        print("not installed", file=out)
        return 0
    try:
        if cmd:
            capture = {"capture_output": True, "text": True} if background else {}
            done = (runner or subprocess.run)(cmd, check=False, **capture)
            if background:
                print(((done.stdout or "") + (done.stderr or ""))[-LOG_TAIL:], file=out)
            if done.returncode:
                raise C.PBError("upgrade-failed", f"{cmd[0]} exited with {done.returncode}")
        else:
            (installer or install_bundle)(release, app_dir, version)
    except Exception as error:
        cause = _cause(error)
        if background:
            _record_auto_failure(path, version, cause)
        print(f"paretobench update failed: {cause}; {__version__} is unchanged", file=err)
        return 1
    cache = read_cache(path)
    cache.update(auto_failed_version="", auto_error="")
    write_cache(cache, path)
    print(f"paretobench {version} installed; it applies on the next start", file=out)
    s = read_settings(settings_file)
    if interactive and not (s["auto_install"] or s["auto_asked"]):
        turn_on = _ask("Install future updates automatically? [y/N]", False, err, ask)
        write_settings({"auto_install": turn_on, "auto_asked": True}, settings_file)
        if turn_on:
            print("automatic updates on; turn off with: paretobench update --auto off", file=out)
    return 0
